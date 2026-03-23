from typing import Dict, Any, List
from ..models.canvas_models import CanvasCourse, CanvasModule, CanvasPage, CanvasAssignment, CanvasQuiz, CanvasDiscussion, CanvasWebLink
from ..models.lms_models import LmsCourse, LmsModule, LmsLesson, LmsQuiz, LmsAssignment, LmsStatus, LmsQuestion, LmsQuestionType, LmsQuestionAnswer

class CourseTransformer:
    """
    Transforms parsed Canvas data into the MERN LMS MongoDB schema.
    """

    def transform(self, canvas_course: CanvasCourse, university_id: str, author_id: str) -> tuple[LmsCourse, Dict[str, Any]]:
        """
        Maps CanvasCourse intermediate representation to the final schema (Node.js compliant).
        Returns a tuple of (lms_course_object, report_dict).
        """
        title = canvas_course.title or "Untitled Course"
        
        lms_course = LmsCourse(
            title=title,
            description=canvas_course.description or "No description provided.",
            instructor_id=author_id,
            canvas_course_id=canvas_course.canvas_id,
            modules=[]
        )

        # Build maps for other content types
        page_map = {p.identifier: p for p in canvas_course.pages}
        assignment_map = {a.identifier: a for a in canvas_course.assignments}
        quiz_map = {q.identifier: q for q in canvas_course.quizzes}
        discussion_map = {d.identifier: d for d in canvas_course.discussions}
        weblink_map = {w.identifier: w for w in canvas_course.weblinks}

        for m_index, module in enumerate(canvas_course.modules):
            lms_module = LmsModule(
                title=module.title or "Untitled Module",
                description=module.description or "",
                order=m_index,
                canvas_id=module.identifier,
                lessons=[],
                quizzes=[],
                assignments=[]
            )

            for item_index, item in enumerate(module.items):
                # Resolve content based on type
                if item.content_type == 'page' and item.content_id in page_map:
                    page = page_map[item.content_id]
                    lms_module.lessons.append(LmsLesson(
                        title=page.title,
                        content=page.body,
                        order=item_index,
                        canvas_id=page.identifier
                    ))
                elif item.content_type == 'assignment' and item.content_id in assignment_map:
                    assign = assignment_map[item.content_id]
                    # Map Canvas submission types to LMS submission types
                    # (Simplified mapping for now)
                    lms_module.assignments.append(LmsAssignment(
                        title=assign.title,
                        description=assign.description,
                        points_possible=assign.points_possible,
                        due_at=assign.due_at,
                        order=item_index,
                        canvas_id=assign.identifier
                    ))
                elif item.content_type == 'quiz' and item.content_id in quiz_map:
                    quiz = quiz_map[item.content_id]
                    lms_quiz = LmsQuiz(
                        title=quiz.title,
                        description=quiz.description,
                        time_limit_minutes=quiz.time_limit_minutes,
                        attempts_allowed=quiz.attempts_allowed,
                        order=item_index,
                        canvas_id=quiz.identifier,
                        questions=[]
                    )
                    # Convert questions
                    for item_q_index, q in enumerate(quiz.questions):
                        lms_question = LmsQuestion(
                            title=q.title,
                            text=q.text,
                            question_type=self._map_question_type(q.question_type),
                            points=q.points,
                            order=item_q_index,
                            canvas_id=q.identifier,
                            answers=[]
                        )
                        for a_index, a in enumerate(q.answers):
                            lms_question.answers.append(LmsQuestionAnswer(
                                text=a.text,
                                is_correct=a.weight > 0,
                                order=a_index,
                                feedback=a.feedback
                            ))
                        lms_quiz.questions.append(lms_question)
                    
                    lms_module.quizzes.append(lms_quiz)
                elif item.content_type == 'discussion' and item.content_id in discussion_map:
                    disc = discussion_map[item.content_id]
                    # Discussions are represented as Lessons in the current LmsCourse model
                    # but we could add a specialized type or just use Lesson.
                    lms_module.lessons.append(LmsLesson(
                        title=disc.title,
                        content=disc.body,
                        order=item_index,
                        canvas_id=disc.identifier
                    ))
                elif item.content_type == 'webcontent' and item.content_id in weblink_map:
                    link = weblink_map[item.content_id]
                    lms_module.lessons.append(LmsLesson(
                        title=link.title,
                        content=f'<p>External Link: <a href="{link.url}">{link.title}</a></p>',
                        order=item_index,
                        canvas_id=link.identifier
                    ))

            lms_course.modules.append(lms_module)

        report = {
            "status": "success",
            "modules_transformed": len(lms_course.modules),
            "items_transformed": sum(m.get_item_count() for m in lms_course.modules)
        }

        return lms_course, report

    def _map_question_type(self, canvas_type) -> LmsQuestionType:
        """Maps Canvas question types to LMS question types."""
        from ..models.canvas_models import QuestionType
        mapping = {
            QuestionType.MULTIPLE_CHOICE: LmsQuestionType.MULTIPLE_CHOICE,
            QuestionType.TRUE_FALSE: LmsQuestionType.TRUE_FALSE,
            QuestionType.SHORT_ANSWER: LmsQuestionType.SHORT_ANSWER,
            QuestionType.ESSAY: LmsQuestionType.ESSAY,
            QuestionType.FILL_IN_BLANK: LmsQuestionType.FILL_IN_BLANK,
            QuestionType.MATCHING: LmsQuestionType.MATCHING,
            QuestionType.ORDERING: LmsQuestionType.ORDERING,
        }
        return mapping.get(canvas_type, LmsQuestionType.MULTIPLE_CHOICE)
