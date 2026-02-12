"""
Typed data models for Tutor LMS entities.

These models represent the target Tutor LMS structure for migration.
All models use dataclasses for type safety and validation.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class TutorContentDripType(Enum):
    """Tutor content drip types"""
    NONE = "none"
    UNLOCK_BY_DATE = "unlock_by_date"
    AFTER_DAYS = "after_days"
    AFTER_FINISHING_PREREQUISITES = "after_finishing_prerequisites"


class TutorQuestionType(Enum):
    """Tutor LMS question types"""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_IN_BLANK = "fill_in_the_blank"
    OPEN_ENDED = "open_ended"  # Essay questions
    SHORT_ANSWER = "short_answer"
    MATCHING = "matching"
    IMAGE_MATCHING = "image_matching"
    IMAGE_ANSWERING = "image_answering"
    ORDERING = "ordering"


@dataclass
class TutorQuestionAnswer:
    """
    Represents a possible answer for a Tutor question.
    """
    answer_title: str  # HTML content
    is_correct: bool = False
    answer_view_format: str = "text"  # text, image
    answer_two_gap_match: Optional[str] = None  # For matching questions
    belongs_question_id: Optional[int] = None
    belongs_question_type: Optional[str] = None
    answer_order: int = 0
    
    # Feedback
    image_id: Optional[int] = None
    answer_explanation: Optional[str] = None


@dataclass
class TutorQuestion:
    """
    Represents a Tutor LMS quiz question.
    """
    question_title: str
    question_description: str  # HTML content
    question_type: TutorQuestionType
    
    # Grading
    question_mark: float = 1.0
    
    # Answers
    answers: List[TutorQuestionAnswer] = field(default_factory=list)
    
    # Settings
    question_settings: Dict[str, Any] = field(default_factory=dict)
    answer_explanation: Optional[str] = None
    
    # Metadata
    question_order: int = 0
    
    # Source reference (for traceability)
    source_canvas_id: Optional[str] = None


@dataclass
class TutorQuiz:
    """
    Represents a Tutor LMS quiz.
    """
    post_title: str
    post_content: str  # HTML description
    post_status: str = "publish"  # publish, draft
    
    # Quiz settings
    quiz_option: Dict[str, Any] = field(default_factory=dict)
    # Common quiz_option fields:
    # - time_limit: Dict with value and time_type
    # - attempts_allowed: int
    # - passing_grade: int (percentage)
    # - max_questions_for_answer: int
    # - quiz_auto_start: bool
    # - question_layout_view: str (single_question, question_pagination, question_below_each_other)
    # - questions_order: str (rand, sorting)
    # - hide_question_number_overview: bool
    # - short_answer_characters_limit: int
    # - feedback_mode: str (default, reveal, retry)
    
    # Questions
    questions: List[TutorQuestion] = field(default_factory=list)
    
    # Metadata
    menu_order: int = 0
    
    # Source reference
    source_canvas_id: Optional[str] = None


@dataclass
class TutorLesson:
    """
    Represents a Tutor LMS lesson.
    """
    post_title: str
    post_content: str  # HTML content
    post_status: str = "publish"  # publish, draft
    
    # Lesson settings
    _tutor_lesson_video_source: str = "html5"
    video: Dict[str, Any] = field(default_factory=dict)
    
    # Attachments
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    menu_order: int = 0
    
    # Source reference
    source_canvas_id: Optional[str] = None


@dataclass
class TutorAssignment:
    """
    Represents a Tutor LMS assignment.
    """
    post_title: str
    post_content: str  # HTML description
    post_status: str = "publish"  # publish, draft
    
    # Assignment settings
    assignment_option: Dict[str, Any] = field(default_factory=dict)
    # Common assignment_option fields:
    # - total_mark: float
    # - pass_mark: float
    # - upload_files_limit: int
    # - upload_file_size_limit: int (MB)
    # - time_duration: Dict with value and time
    # - attachments: List
    
    # Metadata
    menu_order: int = 0
    
    # Source reference
    source_canvas_id: Optional[str] = None


@dataclass
class TutorTopic:
    """
    Represents a Tutor LMS topic (module/section).
    Topics contain lessons, quizzes, and assignments.
    """
    topic_title: str
    topic_summary: str = ""
    
    # Topic order
    topic_order: int = 0
    
    # Content items (lessons, quizzes, assignments)
    # These are stored as references (IDs) in actual Tutor LMS
    # For migration, we store the actual objects
    lessons: List[TutorLesson] = field(default_factory=list)
    quizzes: List[TutorQuiz] = field(default_factory=list)
    assignments: List[TutorAssignment] = field(default_factory=list)
    
    # Source reference
    source_canvas_id: Optional[str] = None


@dataclass
class TutorCourse:
    """
    Represents a complete Tutor LMS course.
    This is the root data model for the migration output.
    """
    post_title: str
    post_content: str  # Course description
    post_status: str = "publish"  # publish, draft
    
    # Course settings
    _tutor_course_settings: Dict[str, Any] = field(default_factory=dict)
    # Common settings:
    # - maximum_students: int
    # - course_duration: int (hours)
    # - course_level: str (beginner, intermediate, expert)
    # - course_benefits: str
    # - course_requirements: str
    # - course_target_audience: str
    # - course_material_includes: str
    
    # Course structure
    topics: List[TutorTopic] = field(default_factory=list)
    
    # Standalone quizzes (not in topics)
    standalone_quizzes: List[TutorQuiz] = field(default_factory=list)
    
    # Metadata
    _thumbnail_id: Optional[int] = None
    
    # Source reference
    source_canvas_course_id: Optional[str] = None
    
    def get_content_counts(self) -> Dict[str, int]:
        """Get counts of all content types"""
        lesson_count = sum(len(topic.lessons) for topic in self.topics)
        quiz_count = sum(len(topic.quizzes) for topic in self.topics) + len(self.standalone_quizzes)
        assignment_count = sum(len(topic.assignments) for topic in self.topics)
        question_count = sum(
            len(quiz.questions) 
            for topic in self.topics 
            for quiz in topic.quizzes
        ) + sum(len(quiz.questions) for quiz in self.standalone_quizzes)
        
        return {
            "topics": len(self.topics),
            "lessons": lesson_count,
            "quizzes": quiz_count,
            "assignments": assignment_count,
            "questions": question_count,
        }


@dataclass
class TutorAsset:
    """
    Represents a media asset (image, video, file) for Tutor LMS.
    """
    source_path: str  # Original path in Canvas export
    destination_path: str  # Path in Tutor LMS assets directory
    file_type: str  # image, video, document, etc.
    mime_type: Optional[str] = None
    
    # WordPress attachment metadata
    post_title: Optional[str] = None
    post_content: Optional[str] = None
    
    # File info
    file_size: Optional[int] = None
    
    # Reference tracking
    referenced_by: List[str] = field(default_factory=list)  # List of content IDs that reference this asset
