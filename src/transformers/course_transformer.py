"""
Course Transformer - Maps CanvasCourse models to LmsCourse (MERN LMS) models.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from models.canvas_models import CanvasCourse, CanvasModule, CanvasModuleItem, CanvasPage, CanvasQuiz, CanvasAssignment
from models.lms_models import (
    LmsCourse, LmsCurriculumModule, LmsCurriculumItem, LmsQuizConfig, 
    LmsAssignmentConfig, LmsGradeSettings, LmsStatus, LmsItemType
)
from models.migration_report import TransformationReport
from observability.logger import get_logger

logger = get_logger(__name__)


class CourseTransformer:
    """
    Transforms parsed Canvas data into the custom LMS domain models.
    Ensures alignment with the backend's nested database schema.
    """

    def transform(
        self, 
        canvas_course: CanvasCourse, 
        university_id: Optional[str] = None, 
        author_id: Optional[str] = None,
        course_code: Optional[str] = None
    ) -> tuple[LmsCourse, TransformationReport]:
        """
        Orchestrates transformation from CanvasCourse to LmsCourse.
        """
        report = TransformationReport()
        logger.info("[CourseTransformer] Starting transformation", extra={"course": canvas_course.title})

        slug = self._slugify(canvas_course.title)
        import os
        lms_course = LmsCourse(
            university=university_id or os.getenv("DEFAULT_UNIVERSITY_ID", "000000000000000000000000"),
            authorId=author_id or os.getenv("DEFAULT_AUTHOR_ID", "000000000000000000000000"),
            authorName="Admin SFC",  # Default for imported courses
            title=canvas_course.title,
            slug=slug,
            courseUrl=slug,
            courseCode=course_code or "IMPORTED",
            department="Imported",
            shortDescription=f"{canvas_course.title} — imported from Canvas LMS",
            description=f"Imported Course: {canvas_course.title}",
            canvas_course_id=canvas_course.identifier
        )

        # Build lookup maps for fast access to content items
        pages_map = {p.identifier: p for p in canvas_course.pages}
        quizzes_map = {q.identifier: q for q in canvas_course.quizzes}
        assignments_map = {a.identifier: a for a in canvas_course.assignments}

        # Process Modules
        for c_module in canvas_course.modules:
            lms_module = self._transform_module(c_module, pages_map, quizzes_map, assignments_map, report)
            lms_course.curriculum.append(lms_module)

        logger.info("[CourseTransformer] Transformation complete", extra={
            "modules": len(lms_course.curriculum),
            "errors": len(report.errors)
        })

        return lms_course, report

    def _transform_module(
        self, 
        c_module: CanvasModule, 
        pages_map: Dict[str, CanvasPage],
        quizzes_map: Dict[str, CanvasQuiz],
        assignments_map: Dict[str, CanvasAssignment],
        report: TransformationReport
    ) -> LmsCurriculumModule:
        """Transforms a Canvas module to a curriculum module."""
        lms_module = LmsCurriculumModule(
            title=c_module.title,
            summary="",
            _canvasId=c_module.identifier
        )

        for item in c_module.items:
            lms_item = self._transform_item(item, pages_map, quizzes_map, assignments_map, report)
            if lms_item:
                lms_module.items.append(lms_item)

        return lms_module

    def _transform_item(
        self, 
        c_item: CanvasModuleItem,
        pages_map: Dict[str, CanvasPage],
        quizzes_map: Dict[str, CanvasQuiz],
        assignments_map: Dict[str, CanvasAssignment],
        report: TransformationReport
    ) -> Optional[LmsCurriculumItem]:
        """Maps a Canvas module item to a unified LmsCurriculumItem."""
        base_item = LmsCurriculumItem(
            title=c_item.title,
            slug=self._slugify(c_item.title),
            _canvasId=c_item.identifier,
            type="Lesson" # Default
        )

        if c_item.content_type == 'page' and c_item.identifier in pages_map:
            page = pages_map[c_item.identifier]
            base_item.type = "Lesson"
            base_item.content = page.body
            return base_item
            
        elif c_item.content_type == 'quiz' and c_item.identifier in quizzes_map:
            quiz = quizzes_map[c_item.identifier]
            base_item.type = "Quiz"
            base_item.content = quiz.description
            base_item.quizConfig = LmsQuizConfig(
                gradeSettings=LmsGradeSettings(maxScore=100.0), # Fallback
                timeLimit=quiz.time_limit or 60,
                attemptsAllowed=quiz.allowed_attempts,
                showCorrectAnswers=quiz.show_correct_answers
            )
            return base_item
            
        elif c_item.content_type == 'assignment' and c_item.identifier in assignments_map:
            assign = assignments_map[c_item.identifier]
            base_item.type = "Assignment"
            base_item.content = assign.description
            base_item.assignmentConfig = LmsAssignmentConfig(
                gradeSettings=LmsGradeSettings(maxScore=assign.points_possible or 100.0),
                type="Individual"
            )
            return base_item

        return None

    def _slugify(self, text: str) -> str:
        """Standard slug generator."""
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        return re.sub(r'[-\s]+', '-', text).strip('-')
