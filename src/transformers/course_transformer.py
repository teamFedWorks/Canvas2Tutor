"""
Course Transformer - Transforms Canvas course to Custom LMS course.

Orchestrates all transformation logic between Canvas IMS-CC models and 
our native LMS MongoDB schema.
"""

from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime

from ..models.canvas_models import (
    CanvasCourse,
    CanvasModule,
    CanvasPage,
    CanvasAssignment,
    CanvasQuiz,
    CanvasQuestion,
    QuestionType
)
from ..models.lms_models import (
    LmsCourse,
    LmsModule,
    LmsLesson,
    LmsQuiz,
    LmsQuestion,
    LmsAssignment,
    LmsQuestionAnswer,
    LmsQuestionType,
    LmsStatus
)
from ..models.migration_report import (
    TransformationReport, 
    MigrationError, 
    ErrorSeverity
)
from ..config.lms_schemas import (
    CANVAS_QUESTION_TYPE_MAP,
    CANVAS_STATUS_MAP,
    DEFAULT_QUIZ_SETTINGS,
    DEFAULT_ASSIGNMENT_SETTINGS
)
from ..observability.logger import get_logger

logger = get_logger(__name__)


class CourseTransformer:
    """
    Transforms Canvas course to Custom LMS course.
    """
    
    def __init__(self):
        """Initialize transformer"""
        self.errors: List[MigrationError] = []
        self.question_type_counts: Dict[str, int] = {}
        
        # Tracking to avoid duplicate entries for items that might be 
        # referenced both in a module and in the course root
        self.processed_assignments: Set[str] = set()
        self.processed_pages: Set[str] = set()
        self.processed_quizzes: Set[str] = set()
    
    def transform(self, canvas_course: CanvasCourse) -> Tuple[LmsCourse, TransformationReport]:
        """
        Transform Canvas course to Custom LMS course.
        
        Args:
            canvas_course: Canvas course model
            
        Returns:
            Tuple of (LmsCourse, TransformationReport)
        """
        logger.info("Starting course transformation", extra={
            "course_title": canvas_course.title,
            "canvas_id": canvas_course.identifier
        })
        
        report = TransformationReport(timestamp=datetime.now())
        
        # Create LMS course
        lms_course = LmsCourse(
            title=canvas_course.title,
            description=f"Course imported from Canvas: {canvas_course.title}",
            status=LmsStatus(CANVAS_STATUS_MAP.get(canvas_course.workflow_state.value, 'published')),
            canvas_course_id=canvas_course.identifier,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Transform modules
        for module in canvas_course.modules:
            lms_module = self._transform_module(module, canvas_course)
            if lms_module:
                lms_course.modules.append(lms_module)
                report.topics_created += 1  # Still using 'topics_created' for report consistency
        
        # Process orphaned content (content not explicitly in any module)
        self._handle_orphaned_content(lms_course, canvas_course, report)
        
        # Final aggregation for report
        for module in lms_course.modules:
            report.lessons_created += len(module.lessons)
            report.quizzes_created += len(module.quizzes)
            report.assignments_created += len(module.assignments)
            for quiz in module.quizzes:
                report.questions_created += len(quiz.questions)
        
        report.question_type_mappings = self.question_type_counts
        report.errors = self.errors
        
        logger.info("Course transformation complete", extra={
            "modules": report.topics_created,
            "lessons": report.lessons_created,
            "quizzes": report.quizzes_created,
            "assignments": report.assignments_created
        })
        
        return lms_course, report
    
    def _transform_module(self, module: CanvasModule, canvas_course: CanvasCourse) -> LmsModule:
        """Transform Canvas module to LMS module"""
        lms_module = LmsModule(
            title=module.title,
            order=module.position,
            canvas_id=module.identifier
        )
        
        # Transform module items
        for item in module.items:
            if item.content_type == 'page':
                page = self._find_page(canvas_course, item)
                if page:
                    lesson = self._transform_page_to_lesson(page, item.position or 0)
                    lms_module.lessons.append(lesson)
            
            elif item.content_type == 'quiz':
                quiz = self._find_quiz(canvas_course, item)
                if quiz:
                    lms_quiz = self._transform_quiz(quiz, item.position or 0)
                    lms_module.quizzes.append(lms_quiz)
            
            elif item.content_type == 'assignment':
                assignment = self._find_assignment(canvas_course, item)
                if assignment:
                    lms_assignment = self._transform_assignment(assignment, item.position or 0)
                    lms_module.assignments.append(lms_assignment)
        
        return lms_module
    
    def _handle_orphaned_content(
        self, 
        lms_course: LmsCourse, 
        canvas_course: CanvasCourse, 
        report: TransformationReport
    ):
        """Find and group content that wasn't linked to any module."""
        
        # 1. Orphaned Assignments
        orphaned_assignments = [
            a for a in canvas_course.assignments 
            if a.identifier not in self.processed_assignments
        ]
        if orphaned_assignments:
            module = LmsModule(title="Additional Assignments", order=len(lms_course.modules) + 1)
            for i, assignment in enumerate(orphaned_assignments):
                module.assignments.append(self._transform_assignment(assignment, i))
            lms_course.modules.append(module)
            logger.info("Created recovery module for orphaned assignments", extra={"count": len(orphaned_assignments)})

        # 2. Orphaned Pages
        orphaned_pages = [
            p for p in canvas_course.pages
            if p.identifier not in self.processed_pages
        ]
        if orphaned_pages:
            module = LmsModule(title="Additional Lessons", order=len(lms_course.modules) + 1)
            for i, page in enumerate(orphaned_pages):
                module.lessons.append(self._transform_page_to_lesson(page, i))
            lms_course.modules.append(module)
            logger.info("Created recovery module for orphaned pages", extra={"count": len(orphaned_pages)})

        # 3. Orphaned Quizzes
        orphaned_quizzes = [
            q for q in canvas_course.quizzes
            if q.identifier not in self.processed_quizzes
        ]
        if orphaned_quizzes:
            module = LmsModule(title="Additional Quizzes", order=len(lms_course.modules) + 1)
            for i, quiz in enumerate(orphaned_quizzes):
                module.quizzes.append(self._transform_quiz(quiz, i))
            lms_course.modules.append(module)
            logger.info("Created recovery module for orphaned quizzes", extra={"count": len(orphaned_quizzes)})

    def _find_page(self, course: CanvasCourse, item) -> Optional[CanvasPage]:
        """Find page by identifier or file reference"""
        for page in course.pages:
            if page.identifier == item.identifier:
                return page
            if item.content_file and page.source_file and item.content_file in page.source_file:
                return page
        return None
    
    def _find_quiz(self, course: CanvasCourse, item) -> Optional[CanvasQuiz]:
        """Find quiz by identifier or file reference"""
        for quiz in course.quizzes:
            if quiz.identifier == item.identifier:
                return quiz
            if item.content_file and quiz.source_file and item.content_file in quiz.source_file:
                return quiz
        return None
    
    def _find_assignment(self, course: CanvasCourse, item) -> Optional[CanvasAssignment]:
        """Find assignment by identifier or file reference"""
        for assignment in course.assignments:
            if assignment.identifier == item.identifier:
                return assignment
            if item.content_file and assignment.source_file and item.content_file in assignment.source_file:
                return assignment
        return None
    
    def _transform_page_to_lesson(self, page: CanvasPage, order: int) -> LmsLesson:
        """Transform Canvas page to LMS lesson"""
        lesson = LmsLesson(
            title=page.title,
            content=page.body,  # Asset path rewriting happens in AssetUploader stage
            status=LmsStatus(CANVAS_STATUS_MAP.get(page.workflow_state.value, 'published')),
            order=order,
            canvas_id=page.identifier
        )
        self.processed_pages.add(page.identifier)
        return lesson
    
    def _transform_quiz(self, quiz: CanvasQuiz, order: int) -> LmsQuiz:
        """Transform Canvas quiz to LMS quiz"""
        lms_quiz = LmsQuiz(
            title=quiz.title,
            description=quiz.description,
            status=LmsStatus(CANVAS_STATUS_MAP.get(quiz.workflow_state.value, 'published')),
            time_limit_minutes=quiz.time_limit,
            attempts_allowed=quiz.allowed_attempts,
            passing_grade_pct=DEFAULT_QUIZ_SETTINGS['passing_grade_pct'],
            order=order,
            canvas_id=quiz.identifier
        )
        
        for i, question in enumerate(quiz.questions):
            lms_question = self._transform_question(question, i)
            if lms_question:
                lms_quiz.questions.append(lms_question)
        
        self.processed_quizzes.add(quiz.identifier)
        return lms_quiz
    
    def _transform_question(self, question: CanvasQuestion, order: int) -> Optional[LmsQuestion]:
        """Transform Canvas question to LMS question"""
        canvas_type = question.question_type.value
        lms_type_str = CANVAS_QUESTION_TYPE_MAP.get(canvas_type)
        
        self.question_type_counts[canvas_type] = self.question_type_counts.get(canvas_type, 0) + 1
        
        if lms_type_str is None:
            logger.warning("Unsupported question type", extra={
                "type": canvas_type,
                "question": question.title,
                "canvas_id": question.identifier
            })
            self.errors.append(MigrationError(
                severity=ErrorSeverity.WARNING,
                error_type="UNSUPPORTED_QUESTION_TYPE",
                message=f"Question type '{canvas_type}' not supported by target LMS",
                canvas_entity_id=question.identifier
            ))
            return None
        
        lms_question = LmsQuestion(
            title=question.title,
            text=question.question_text,
            question_type=LmsQuestionType(lms_type_str),
            points=question.points_possible,
            order=order,
            canvas_id=question.identifier,
            correct_feedback=question.correct_feedback,
            incorrect_feedback=question.incorrect_feedback,
            general_feedback=question.general_feedback
        )
        
        # Transform answers
        for j, answer in enumerate(question.answers):
            lms_answer = LmsQuestionAnswer(
                text=answer.text,
                is_correct=(answer.weight >= 100),
                order=j,
                feedback=answer.feedback,
                match_text=answer.match_id
            )
            lms_question.answers.append(lms_answer)
        
        return lms_question
    
    def _transform_assignment(self, assignment: CanvasAssignment, order: int) -> LmsAssignment:
        """Transform Canvas assignment to LMS assignment"""
        lms_assignment = LmsAssignment(
            title=assignment.title,
            description=assignment.description,
            status=LmsStatus(CANVAS_STATUS_MAP.get(assignment.workflow_state.value, 'published')),
            points_possible=assignment.points_possible,
            passing_points=assignment.points_possible * 0.6,
            due_at=assignment.due_at,
            unlock_at=assignment.unlock_at,
            lock_at=assignment.lock_at,
            order=order,
            canvas_id=assignment.identifier,
            submission_types=[
                # Map Canvas submission types to our enum
                # (Simple mapping for now)
                # ...
            ]
        )
        
        # Default settings
        lms_assignment.max_file_uploads = DEFAULT_ASSIGNMENT_SETTINGS['max_file_uploads']
        lms_assignment.max_file_size_mb = DEFAULT_ASSIGNMENT_SETTINGS['max_file_size_mb']
        
        self.processed_assignments.add(assignment.identifier)
        return lms_assignment
