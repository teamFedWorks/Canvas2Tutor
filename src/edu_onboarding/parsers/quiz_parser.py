"""
Quiz Parser - Parses Canvas quizzes/assessments.

Extracts quiz data from assessment XML files.
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..models.canvas_models import CanvasQuiz, WorkflowState
from ..models.migration_report import MigrationError, ErrorSeverity
from ..utils.xml_utils import parse_xml_file, find_element, find_elements, get_element_text, get_element_attribute
from ..utils.html_utils import clean_html
from .question_parser import QuestionParser


class QuizParser:
    """
    Parses Canvas quiz/assessment XML files.
    """
    
    def __init__(self, course_directory: Path):
        """
        Initialize quiz parser.
        
        Args:
            course_directory: Path to Canvas course export directory
        """
        self.course_directory = course_directory
        self.question_parser = QuestionParser(course_directory)
        self.errors: List[MigrationError] = []
    
    def parse_quiz(self, quiz_dir: Path) -> Optional[CanvasQuiz]:
        """
        Parse a quiz from its directory.
        
        Args:
            quiz_dir: Path to quiz directory
            
        Returns:
            CanvasQuiz object or None if parsing fails
        """
        # Look for assessment XML files
        assessment_file = quiz_dir / "assessment_meta.xml"
        if not assessment_file.exists():
            assessment_file = quiz_dir / "assessment.xml"
        
        if not assessment_file.exists():
            return None
        
        try:
            root = parse_xml_file(assessment_file)
            if root is None:
                self.errors.append(MigrationError(
                    severity=ErrorSeverity.ERROR,
                    error_type="QUIZ_PARSE_ERROR",
                    message=f"Failed to parse quiz: {quiz_dir.name}",
                    file_path=str(assessment_file)
                ))
                return None
            
            # Extract quiz metadata
            title = self._extract_title(root, quiz_dir)
            description = self._extract_description(root)
            quiz_type = get_element_text(find_element(root, './/quiz_type', {}), "assignment")
            points_possible = float(get_element_text(find_element(root, './/points_possible', {}), "0"))
            time_limit = self._extract_time_limit(root)
            allowed_attempts = int(get_element_text(find_element(root, './/allowed_attempts', {}), "1"))
            
            # Parse questions
            questions = self.question_parser.parse_questions_from_quiz(quiz_dir)
            
            quiz = CanvasQuiz(
                title=title,
                identifier=quiz_dir.name,
                description=description,
                quiz_type=quiz_type,
                points_possible=points_possible,
                time_limit=time_limit,
                allowed_attempts=allowed_attempts,
                questions=questions,
                workflow_state=WorkflowState.ACTIVE,
                source_file=str(assessment_file)
            )
            
            return quiz
            
        except Exception as e:
            self.errors.append(MigrationError(
                severity=ErrorSeverity.ERROR,
                error_type="QUIZ_PARSE_ERROR",
                message=f"Unexpected error parsing quiz: {str(e)}",
                file_path=str(assessment_file)
            ))
            return None
    
    def _extract_title(self, root, quiz_dir: Path) -> str:
        """Extract quiz title"""
        title_elem = find_element(root, './/title', {})
        if title_elem is not None:
            return get_element_text(title_elem, quiz_dir.name)
        return quiz_dir.name
    
    def _extract_description(self, root) -> str:
        """Extract quiz description"""
        desc_elem = find_element(root, './/description', {})
        if desc_elem is not None:
            return clean_html(get_element_text(desc_elem, ""))
        return ""
    
    def _extract_time_limit(self, root) -> Optional[int]:
        """Extract time limit in minutes"""
        time_elem = find_element(root, './/time_limit', {})
        if time_elem is not None:
            try:
                return int(get_element_text(time_elem, "0"))
            except ValueError:
                pass
        return None
    
    def find_all_quizzes(self) -> List[CanvasQuiz]:
        """
        Find and parse all quizzes in course directory.
        
        Returns:
            List of CanvasQuiz objects
        """
        quizzes = []
        
        # Check non_cc_assessments directory
        assessments_dir = self.course_directory / "non_cc_assessments"
        if assessments_dir.exists():
            for quiz_dir in assessments_dir.iterdir():
                if quiz_dir.is_dir():
                    quiz = self.parse_quiz(quiz_dir)
                    if quiz:
                        quizzes.append(quiz)
        
        # Also check for quiz directories in root
        for item in self.course_directory.iterdir():
            if item.is_dir() and item.name != "non_cc_assessments":
                if (item / "assessment_meta.xml").exists() or (item / "assessment.xml").exists():
                    quiz = self.parse_quiz(item)
                    if quiz:
                        quizzes.append(quiz)
        
        return quizzes
