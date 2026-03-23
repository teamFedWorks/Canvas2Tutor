"""
Custom LMS Domain Models

Typed dataclasses for the custom MERN-based LMS MongoDB schema.
These replace all TutorLMS-specific models.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class LmsStatus(Enum):
    """Content publication status."""
    PUBLISHED = "published"
    DRAFT = "draft"
    ARCHIVED = "archived"


class LmsQuestionType(Enum):
    """Supported LMS question types."""
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    FILL_IN_BLANK = "fill_in_blank"
    MATCHING = "matching"
    ORDERING = "ordering"


class LmsSubmissionType(Enum):
    """Assignment submission types."""
    TEXT = "text"
    FILE_UPLOAD = "file_upload"
    URL = "url"
    NONE = "none"


# ---------------------------------------------------------------------------
# Question & Answer
# ---------------------------------------------------------------------------

@dataclass
class LmsQuestionAnswer:
    """
    A single answer choice for an LMS question.
    """
    text: str                              # HTML-safe answer text
    is_correct: bool = False
    order: int = 0
    feedback: Optional[str] = None         # Per-answer feedback HTML

    # For matching questions only
    match_text: Optional[str] = None


@dataclass
class LmsQuestion:
    """
    Represents a quiz question in the custom LMS.
    """
    title: str
    text: str                              # HTML question body
    question_type: LmsQuestionType
    points: float = 1.0
    order: int = 0

    answers: List[LmsQuestionAnswer] = field(default_factory=list)

    # Feedback
    correct_feedback: Optional[str] = None
    incorrect_feedback: Optional[str] = None
    general_feedback: Optional[str] = None

    # Source traceability
    canvas_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Quiz
# ---------------------------------------------------------------------------

@dataclass
class LmsQuiz:
    """
    Represents a quiz / assessment in the custom LMS.
    """
    title: str
    description: str = ""                  # HTML description
    status: LmsStatus = LmsStatus.PUBLISHED

    # Settings
    time_limit_minutes: Optional[int] = None
    attempts_allowed: int = 1
    passing_grade_pct: int = 60
    shuffle_questions: bool = False
    show_correct_answers: bool = True

    questions: List[LmsQuestion] = field(default_factory=list)

    # Position within module
    order: int = 0

    # Source traceability
    canvas_id: Optional[str] = None

    def get_total_points(self) -> float:
        return sum(q.points for q in self.questions)


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

@dataclass
class LmsAssignment:
    """
    Represents an assignment in the custom LMS.
    """
    title: str
    description: str = ""                  # HTML description
    status: LmsStatus = LmsStatus.PUBLISHED

    # Grading
    points_possible: float = 100.0
    passing_points: float = 60.0           # 60% default pass mark

    # Submission
    submission_types: List[LmsSubmissionType] = field(default_factory=list)
    allowed_file_extensions: List[str] = field(default_factory=list)
    max_file_uploads: int = 1
    max_file_size_mb: int = 10

    # Timing
    due_at: Optional[datetime] = None
    unlock_at: Optional[datetime] = None
    lock_at: Optional[datetime] = None

    # Position within module
    order: int = 0

    # Source traceability
    canvas_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Lesson
# ---------------------------------------------------------------------------

@dataclass
class LmsLesson:
    """
    Represents a lesson (wiki page) in the custom LMS.
    """
    title: str
    content: str = ""                      # Full HTML content
    status: LmsStatus = LmsStatus.PUBLISHED

    # Assets referenced in this lesson (S3 CDN URLs after upload)
    asset_urls: List[str] = field(default_factory=list)

    # Position within module
    order: int = 0

    # Source traceability
    canvas_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

@dataclass
class LmsModule:
    """
    Represents a course module (section / unit) in the custom LMS.
    Contains lessons, quizzes, and assignments in order.
    """
    title: str
    order: int = 0
    description: str = ""

    lessons: List[LmsLesson] = field(default_factory=list)
    quizzes: List[LmsQuiz] = field(default_factory=list)
    assignments: List[LmsAssignment] = field(default_factory=list)

    # Source traceability
    canvas_id: Optional[str] = None

    def get_item_count(self) -> int:
        return len(self.lessons) + len(self.quizzes) + len(self.assignments)


# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------

@dataclass
class LmsCourse:
    """
    Root document for a custom LMS course.
    Maps directly to the 'courses' MongoDB collection.
    """
    title: str
    description: str = ""
    status: LmsStatus = LmsStatus.PUBLISHED

    # Instructor / author reference (ObjectId string from your Node.js user service)
    instructor_id: Optional[str] = None

    # Hierarchy
    modules: List[LmsModule] = field(default_factory=list)

    # Metadata
    image_url: Optional[str] = None
    difficulty_level: str = "all_levels"   # beginner, intermediate, advanced, all_levels
    categories: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Source traceability (used for idempotent upserts)
    canvas_course_id: Optional[str] = None

    def get_content_counts(self) -> Dict[str, int]:
        """Return a summary of all content items in this course."""
        lessons = sum(len(m.lessons) for m in self.modules)
        quizzes = sum(len(m.quizzes) for m in self.modules)
        assignments = sum(len(m.assignments) for m in self.modules)
        questions = sum(
            len(q.questions)
            for m in self.modules
            for q in m.quizzes
        )
        return {
            "modules": len(self.modules),
            "lessons": lessons,
            "quizzes": quizzes,
            "assignments": assignments,
            "questions": questions,
        }
