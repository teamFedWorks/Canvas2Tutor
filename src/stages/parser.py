"""
Stage 2: Semantic Parsing

Orchestrates all parsers to build complete Canvas course model.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime

from ..models.canvas_models import CanvasCourse
from ..models.migration_report import ParseReport, MigrationError
from ..parsers.manifest_parser import ManifestParser
from ..parsers.page_parser import PageParser
from ..parsers.assignment_parser import AssignmentParser
from ..parsers.quiz_parser import QuizParser
from ..parsers.orphaned_content_handler import OrphanedContentHandler
from ..parsers.pptx_parser import PptxParser


class Parser:
    """
    Stage 2: Semantic Parsing
    
    Orchestrates all parsers to build complete CanvasCourse model.
    """
    
    def __init__(self, course_directory: Path):
        """
        Initialize parser.
        
        Args:
            course_directory: Path to Canvas course export directory
        """
        self.course_directory = course_directory
        
        # Initialize all parsers
        self.manifest_parser = ManifestParser(course_directory)
        self.page_parser = PageParser(course_directory)
        self.assignment_parser = AssignmentParser(course_directory)
        self.quiz_parser = QuizParser(course_directory)
        self.orphaned_handler = OrphanedContentHandler(course_directory)
        self.pptx_parser = PptxParser(course_directory)
    
    def parse(self) -> tuple[Optional[CanvasCourse], ParseReport]:
        """
        Parse the entire Canvas course.
        
        Returns:
            Tuple of (CanvasCourse object or None, ParseReport)
        """
        report = ParseReport(timestamp=datetime.now())
        
        # Step 1: Parse manifest (single source of truth)
        course = self.manifest_parser.parse()
        if course is None:
            report.errors.extend(self.manifest_parser.errors)
            return None, report
        
        # Step 2: Parse pages
        pages = self.page_parser.parse_all_pages()
        
        # Determine referenced_files set for orphan check later
        referenced_files = set()
        if course.resources:
            # Use hrefs for file path checking
            referenced_files = set(r.href for r in course.resources.values() if r.href)
            
            # ADDITIONAL STEP: Process PPTX files referenced in manifest resources
            for res_id, resource in course.resources.items():
                if resource.type and 'webcontent' in resource.type.lower():
                    if resource.href and resource.href.lower().endswith('.pptx'):
                        # This is a PPTX file that should be converted to a page
                        file_path = self.course_directory / resource.href
                        if file_path.exists():
                            print(f"  Converting PPTX resource: {resource.href}")
                            # Use the resource ID so it matches the identifierref in modules
                            pptx_page = self.pptx_parser.parse_pptx(file_path, identifier=res_id)
                            if pptx_page:
                                pages.append(pptx_page)
        
        course.pages = pages
        report.pages_parsed = len(pages)
        report.errors.extend(self.page_parser.errors)
        report.errors.extend(self.pptx_parser.errors)
        
        # Step 3: Parse assignments
        assignments = self.assignment_parser.find_all_assignments()
        course.assignments = assignments
        report.assignments_parsed = len(assignments)
        report.errors.extend(self.assignment_parser.errors)
        
        # Step 4: Parse quizzes
        quizzes = self.quiz_parser.find_all_quizzes()
        course.quizzes = quizzes
        report.quizzes_parsed = len(quizzes)
        
        # Count questions
        total_questions = sum(len(quiz.questions) for quiz in quizzes)
        report.questions_parsed = total_questions
        
        report.errors.extend(self.quiz_parser.errors)
        report.errors.extend(self.quiz_parser.question_parser.errors)
        
        # Step 5: Process orphaned content (XML, HTML files not in manifest)
        print("  Processing orphaned XML/HTML files...")
        referenced_files = set(course.resources.keys())
        orphaned_pages = self.orphaned_handler.process_all_orphaned_content(referenced_files)
        
        # Add orphaned pages to course
        course.pages.extend(orphaned_pages)
        report.pages_parsed += len(orphaned_pages)
        report.errors.extend(self.orphaned_handler.errors)
        
        return course, report
