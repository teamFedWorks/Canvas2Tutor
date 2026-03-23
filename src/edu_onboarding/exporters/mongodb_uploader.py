"""
MongoDB Uploader - Direct LMS Database Writer

Handles writing of LmsCourse models into the 'courses' collection
using a nested curriculum structure that matches the MERN LMS backend.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pymongo
from pymongo import ASCENDING
from bson import ObjectId

from ..models.lms_models import LmsCourse, LmsModule, LmsLesson, LmsQuiz, LmsAssignment
from ..config.mongodb_config import MongoDBConfig
from ..observability.logger import get_logger

logger = get_logger(__name__)


class MongoDBUploader:
    """
    Directly writes LMS course data to the MongoDB 'courses' collection.
    Matches the nested schema expected by CourseModel.js.
    """

    def __init__(self, config: Optional[MongoDBConfig] = None):
        """
        Initialize connection to MongoDB using external configuration.
        """
        self.config = config or MongoDBConfig()
        self.client = pymongo.MongoClient(self.config.mongodb_uri)
        self.db = self.client[self.config.database_name]
        
        # Collections
        self.col_courses = self.db['courses']
        self.col_jobs = self.db['migration_jobs']

        self._ensure_indexes()

    def _ensure_indexes(self):
        """Build essential indexes for performance and uniqueness."""
        try:
            # course_id used as shard key or lookup key
            self.col_courses.create_index([("canvasCourseId", ASCENDING)], unique=True)
            self.col_courses.create_index([("slug", ASCENDING)], unique=False)
            
            # Job monitoring
            self.col_jobs.create_index([("startedAt", ASCENDING)])
            logger.info("MongoDB indexes verified/created")
        except Exception as e:
            logger.error("Failed to create indexes", extra={"error": str(e)})

    def write_lms_course(self, course: LmsCourse, task_id: str) -> bool:
        """
        Performs an idempotent upsert of the entire course structure.
        """
        logger.info("Writing course to MongoDB", extra={
            "task_id": task_id,
            "title": course.title,
            "canvas_id": course.canvas_course_id
        })

        try:
            # 1. Prepare nested curriculum
            curriculum = []
            for m_index, module in enumerate(course.modules):
                items = []
                
                # Merge lessons, quizzes, assignments into a single 'items' list
                # Each item needs a 'type' discriminator and a 'slug'
                
                for lesson in module.lessons:
                    items.append({
                        "title": lesson.title,
                        "slug": self._slugify(lesson.title),
                        "type": "Lesson",
                        "content": lesson.content,
                        "attachments": [{"name": url.split('/')[-1], "url": url} for url in lesson.asset_urls],
                        "settings": {
                            "isPublished": (lesson.status.value == "Published")
                        }
                        # Position handled via order if needed, but array order is usually sufficient
                    })
                
                for quiz in module.quizzes:
                    items.append({
                        "title": quiz.title,
                        "slug": self._slugify(quiz.title),
                        "type": "Quiz",
                        "quizConfig": {
                            "timeLimit": quiz.time_limit_minutes or 0,
                            "attemptsAllowed": quiz.attempts_allowed,
                            "passingGrade": quiz.passing_grade_pct,
                            "shuffleQuestions": quiz.shuffle_questions,
                            "showCorrectAnswers": quiz.show_correct_answers
                        },
                        "questions": [self._question_to_dict(q) for q in quiz.questions],
                        "settings": {
                            "isPublished": (quiz.status.value == "Published")
                        }
                    })

                for assign in module.assignments:
                    items.append({
                        "title": assign.title,
                        "slug": self._slugify(assign.title),
                        "type": "Assignment",
                        "instructions": assign.description,
                        "assignmentConfig": {
                            "totalPoints": assign.points_possible,
                            "minPassPoints": assign.passing_points,
                            "fileUploadLimit": assign.max_file_uploads,
                            "maxFileSizeMB": assign.max_file_size_mb,
                            "deadline": assign.due_at.isoformat() if assign.due_at else None
                        },
                        "settings": {
                            "isPublished": (assign.status.value == "Published")
                        }
                    })

                # Sort items by their original 'order' if provided, otherwise preserve transformer order
                # items.sort(key=lambda x: x.get('order', 0))

                curriculum.append({
                    "title": module.title,
                    "summary": module.description or "",
                    "isPublished": True,
                    "items": items
                })

            # 2. Build the main course document
            course_doc = {
                "title": course.title,
                "description": course.description,
                "status": course.status.value,
                "canvasCourseId": course.canvas_course_id,
                "courseCode": course.course_code or "DEFAULT",
                "slug": course.slug or self._slugify(course.title),
                "difficultyLevel": course.difficulty_level,
                "categories": course.categories,
                "updatedAt": datetime.utcnow(),
                "curriculum": curriculum
            }
            
            # Handle tenancy IDs (convert to ObjectId if possible)
            if course.university:
                try:
                    course_doc["university"] = ObjectId(course.university)
                except:
                    course_doc["university"] = course.university
            
            if course.author_id:
                try:
                    course_doc["authorId"] = ObjectId(course.author_id)
                except:
                    course_doc["authorId"] = course.author_id

            # 3. UPSERT the main course document
            self.col_courses.update_one(
                {"canvasCourseId": course.canvas_course_id},
                {"$set": course_doc, "$setOnInsert": {"createdAt": datetime.utcnow()}},
                upsert=True
            )
            
            logger.info("Successfully upserted nested course to MongoDB", extra={
                "title": course.title,
                "modules": len(course.modules)
            })
            
            return True

        except Exception as e:
            logger.error("Failed to write to MongoDB", extra={"error": str(e), "task_id": task_id})
            return False

    def _question_to_dict(self, q) -> Dict[str, Any]:
        """Convert LmsQuestion model to dict for MongoDB embedding."""
        return {
            "title": q.title,
            "type": q.question_type.value,
            "points": q.points,
            "explanation": q.general_feedback,
            "options": [
                {
                    "text": a.text,
                    "isCorrect": a.is_correct,
                    "feedback": a.feedback
                } for a in q.answers
            ]
        }

    def _slugify(self, text: str) -> str:
        """Fallback slug generator for DB write."""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        return re.sub(r'[-\s]+', '-', text).strip('-')

    # -----------------------------------------------------------------------
    # Job Management
    # -----------------------------------------------------------------------

    def create_job(self, task_id: str, s3_key: Optional[str] = None):
        """Initialize a migration job record."""
        job = {
            "_id": task_id,
            "status": "processing",
            "s3Key": s3_key,
            "startedAt": datetime.utcnow(),
            "logs": [],
            "progress": 0
        }
        self.col_jobs.update_one({"_id": task_id}, {"$set": job}, upsert=True)

    def update_job_status(self, task_id: str, status: str, log_msg: Optional[str] = None, progress: Optional[int] = None):
        """Update existing job status, log, and progress."""
        update: Dict[str, Any] = {"$set": {"status": status}}
        if progress is not None:
            update["$set"]["progress"] = progress
            
        if log_msg:
            # Append log with timestamp
            log_entry = f"[{datetime.utcnow().isoformat()}] {log_msg}"
            update["$push"] = {"logs": log_entry}
        
        if status in ("completed", "failed"):
            update["$set"]["completedAt"] = datetime.utcnow()

        self.col_jobs.update_one({"_id": task_id}, update)

    def get_job(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job record."""
        return self.col_jobs.find_one({"_id": task_id})


def upload_to_mongodb(course: LmsCourse, task_id: str) -> bool:
    """
    Convenience wrapper for the pipeline orchestrator.
    """
    uploader = MongoDBUploader()
    return uploader.write_lms_course(course, task_id)
