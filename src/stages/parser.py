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
        Initialize the master Parser.
        
        This constructor sets up the specialized sub-parsers responsible for
        handling different types of Canvas content.
        
        Args:
            course_directory: The root folder containing the unzipped Canvas export.
        """
        self.course_directory = course_directory
        
        # Initialize specialized parsers for each content type.
        # manifest_parser: Reads the main course structure (the map).
        self.manifest_parser = ManifestParser(course_directory)
        
        # page_parser: Handles wiki pages and general text content.
        self.page_parser = PageParser(course_directory)
        
        # assignment_parser: Parses assignment settings and descriptions.
        self.assignment_parser = AssignmentParser(course_directory)
        
        # quiz_parser: Handles complex quiz structures and questions.
        self.quiz_parser = QuizParser(course_directory)
        
        # orphaned_handler: Finds files that exist but aren't listed in the manifest.
        self.orphaned_handler = OrphanedContentHandler(course_directory)
        
        # pptx_parser: A specialized tool for converting PowerPoint XML to HTML pages.
        self.pptx_parser = PptxParser(course_directory)
    
    def parse(self) -> tuple[Optional[CanvasCourse], ParseReport]:
        """
        Orchestrate the parsing of all course components.
        
        This method follows a logical flow: first reading the manifest to build
         the course skeleton, then filling it with content from assignments,
         pages, quizzes, and loose files.
        
        Returns:
            A tuple containing (The built CanvasCourse object, A detailed ParseReport).
        """
        report = ParseReport(timestamp=datetime.now())
        
        # Step 1: Parse manifest (the single source of truth for course structure).
        # This tells us what modules exist and what items belong to them.
        course = self.manifest_parser.parse()
        if course is None:
            # If the manifest is missing or broken, we can't build the course.
            report.errors.extend(self.manifest_parser.errors)
            return None, report
        
        # Step 2: Parse wiki pages.
        # We extract content from all XML files identified as 'pages' in the manifest.
        pages = self.page_parser.parse_all_pages()
        
        # Determine referenced_files set for orphan check later.
        # This helps us differentiate between 'expected' files and 'extra' files.
        referenced_files = set()
        if course.resources:
            # Map out every file the manifest knows about.
            referenced_files = set(r.href for r in course.resources.values() if r.href)
            
            # ADDITIONAL STEP: Process PPTX files.
            # Canvas often exports PowerPoints as XML. We convert these to standard HTML pages.
            for res_id, resource in course.resources.items():
                if resource.type and 'webcontent' in resource.type.lower():
                    if resource.href and resource.href.lower().endswith('.pptx'):
                        file_path = self.course_directory / resource.href
                        if file_path.exists():
                            print(f"  Converting PPTX resource: {resource.href}")
                            # Link the converted page to its original manifest identifier.
                            pptx_page = self.pptx_parser.parse_pptx(file_path, identifier=res_id)
                            if pptx_page:
                                pages.append(pptx_page)
        
        course.pages = pages
        report.pages_parsed = len(pages)
        report.errors.extend(self.page_parser.errors)
        report.errors.extend(self.pptx_parser.errors)
        
        # Step 3: Parse assignments.
        # Assignments are usually in their own subfolders with metadata and instructions.
        assignments = self.assignment_parser.find_all_assignments()
        course.assignments = assignments
        report.assignments_parsed = len(assignments)
        report.errors.extend(self.assignment_parser.errors)
        
        # Step 4: Parse quizzes.
        # Quizzes involve complex QTI-compliant question parsing.
        quizzes = self.quiz_parser.find_all_quizzes()
        course.quizzes = quizzes
        report.quizzes_parsed = len(quizzes)
        
        # Track the total number of questions extracted across all quizzes.
        total_questions = sum(len(quiz.questions) for quiz in quizzes)
        report.questions_parsed = total_questions
        
        report.errors.extend(self.quiz_parser.errors)
        report.errors.extend(self.quiz_parser.question_parser.errors)
        
        # Step 5: Process orphaned content.
        # Sometimes there are files in the package that aren't mentioned in the manifest.
        # We find these (like loose slides or PDFs) and put them in a 'Recovered Content' module.
        print("  Processing orphaned XML/HTML files...")
        referenced_files = set(course.resources.keys())
        orphaned_pages = self.orphaned_handler.process_all_orphaned_content(referenced_files)
        
        # Merge discovered orphans into the main course pages collection.
        course.pages.extend(orphaned_pages)
        report.pages_parsed += len(orphaned_pages)
        report.errors.extend(self.orphaned_handler.errors)
        
        return course, report
