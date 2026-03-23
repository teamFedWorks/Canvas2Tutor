"""
MongoDB Uploader - Direct LMS Database Writer

Handles bulk writing of LmsCourse models into five MongoDB collections:
courses, modules, lessons, quizzes, assignments.
Also manages the 'migration_jobs' tracking collection.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pymongo
from pymongo import UpdateOne, ASCENDING
from bson import ObjectId

from ..models.lms_models import LmsCourse, LmsModule, LmsLesson, LmsQuiz, LmsAssignment
from ..config.mongodb_config import MongoDBConfig
from ..observability.logger import get_logger

logger = get_logger(__name__)


class MongoDBUploader:
    """
    Directly writes LMS course data to MongoDB collections.
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
        self.col_modules = self.db['modules']
        self.col_lessons = self.db['lessons']
        self.col_quizzes = self.db['quizzes']
        self.col_assignments = self.db['assignments']
        self.col_jobs = self.db['migration_jobs']

        self._ensure_indexes()

    def _ensure_indexes(self):
        """Build essential indexes for performance and uniqueness."""
        try:
            # course_id used as shard key or lookup key in sub-collections
            self.col_courses.create_index([("canvasCourseId", ASCENDING)], unique=True)
            self.col_modules.create_index([("courseId", ASCENDING), ("order", ASCENDING)])
            self.col_lessons.create_index([("moduleId", ASCENDING), ("order", ASCENDING)])
            self.col_quizzes.create_index([("moduleId", ASCENDING), ("order", ASCENDING)])
            self.col_assignments.create_index([("moduleId", ASCENDING), ("order", ASCENDING)])
            
            # Job monitoring
            self.col_jobs.create_index([("startedAt", ASCENDING)])
            logger.info("MongoDB indexes verified/created")
        except Exception as e:
            logger.error("Failed to create indexes", extra={"error": str(e)})

    def write_lms_course(self, course: LmsCourse, task_id: str) -> bool:
        """
        Performs an idempotent bulk write of the entire course structure.
        """
        logger.info("Writing course to MongoDB", extra={
            "task_id": task_id,
            "title": course.title,
            "canvas_id": course.canvas_course_id
        })

        try:
            # 1. UPSERT the main course document
            course_doc = {
                "title": course.title,
                "description": course.description,
                "status": course.status.value,
                "canvasCourseId": course.canvas_course_id,
                "instructorId": course.instructor_id,
                "difficulty": course.difficulty_level,
                "categories": course.categories,
                "updatedAt": datetime.utcnow()
            }
            
            result = self.col_courses.update_one(
                {"canvasCourseId": course.canvas_course_id},
                {"$set": course_doc, "$setOnInsert": {"createdAt": datetime.utcnow()}},
                upsert=True
            )
            
            # Retrieve the course _id (either from existing or new)
            if result.upserted_id:
                course_id = result.upserted_id
            else:
                existing = self.col_courses.find_one({"canvasCourseId": course.canvas_course_id}, {"_id": 1})
                if not existing:
                    # Fallback case if update somehow didn't yield a doc
                    logger.error("Course document not found after upsert", extra={"canvas_id": course.canvas_course_id})
                    return False
                course_id = existing["_id"]

            # 2. CLEAR existing sub-items for this course to ensure clean overwrite
            # Since we use courseId as a foreign key, we delete all items linked to this courseId
            # before re-inserting the new versions.
            self.col_modules.delete_many({"courseId": course_id})
            self.col_lessons.delete_many({"courseId": course_id})
            self.col_quizzes.delete_many({"courseId": course_id})
            self.col_assignments.delete_many({"courseId": course_id})
            
            # 3. Process modules and their contents
            all_lessons = []
            all_quizzes = []
            all_assignments = []
            
            for m_index, module in enumerate(course.modules):
                module_id = ObjectId()
                module_doc = {
                    "_id": module_id,
                    "courseId": course_id,
                    "title": module.title,
                    "order": module.order or m_index,
                    "canvasId": module.canvas_id
                }
                self.col_modules.insert_one(module_doc)

                # Collect sub-items
                for lesson in module.lessons:
                    all_lessons.append({
                        "moduleId": module_id,
                        "courseId": course_id,
                        "title": lesson.title,
                        "content": lesson.content,
                        "status": lesson.status.value,
                        "order": lesson.order,
                        "assetUrls": lesson.asset_urls,
                        "canvasId": lesson.canvas_id
                    })
                
                for quiz in module.quizzes:
                    all_quizzes.append({
                        "moduleId": module_id,
                        "courseId": course_id,
                        "title": quiz.title,
                        "description": quiz.description,
                        "settings": {
                            "timeLimit": quiz.time_limit_minutes,
                            "attempts": quiz.attempts_allowed,
                            "passingGrade": quiz.passing_grade_pct
                        },
                        "questions": [self._question_to_dict(q) for q in quiz.questions],
                        "status": quiz.status.value,
                        "order": quiz.order,
                        "canvasId": quiz.canvas_id
                    })

                for assign in module.assignments:
                    all_assignments.append({
                        "moduleId": module_id,
                        "courseId": course_id,
                        "title": assign.title,
                        "description": assign.description,
                        "points": assign.points_possible,
                        "dueAt": assign.due_at,
                        "submissionTypes": [t.value for t in assign.submission_types],
                        "status": assign.status.value,
                        "order": assign.order,
                        "canvasId": assign.canvas_id
                    })

            # Batch insert sub-items
            if all_lessons:
                self.col_lessons.insert_many(all_lessons)
            
            if all_quizzes:
                self.col_quizzes.insert_many(all_quizzes)
                
            if all_assignments:
                self.col_assignments.insert_many(all_assignments)

            logger.info("Successfully wrote course items to MongoDB", extra={
                "course_id": str(course_id),
                "modules": len(course.modules),
                "lessons": len(all_lessons),
                "quizzes": len(all_quizzes),
                "assignments": len(all_assignments)
            })
            
            return True

        except Exception as e:
            logger.error("Failed to write to MongoDB", extra={"error": str(e), "task_id": task_id})
            return False

    def _question_to_dict(self, q) -> Dict[str, Any]:
        """Convert LmsQuestion model to dict for MongoDB embedding."""
        return {
            "title": q.title,
            "text": q.text,
            "type": q.question_type.value,
            "points": q.points,
            "order": q.order,
            "canvasId": q.canvas_id,
            "answers": [
                {
                    "text": a.text,
                    "isCorrect": a.is_correct,
                    "order": a.order,
                    "feedback": a.feedback,
                    "matchText": a.match_text
                } for a in q.answers
            ],
            "feedback": {
                "correct": q.correct_feedback,
                "incorrect": q.incorrect_feedback,
                "general": q.general_feedback
            }
        }

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
