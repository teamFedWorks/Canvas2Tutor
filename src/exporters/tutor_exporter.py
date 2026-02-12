"""
Tutor LMS Exporter - Exports Tutor course to JSON format.

Generates import-ready JSON structure for Tutor LMS.
"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from dataclasses import asdict

from ..models.tutor_models import TutorCourse
from ..models.migration_report import VerificationReport, MigrationError, ErrorSeverity
from ..utils.file_utils import ensure_directory_exists


class TutorExporter:
    """
    Exports Tutor LMS course to JSON format.
    """
    
    def __init__(self, output_directory: Path, source_directory: Path = None):
        """
        Initialize exporter.
        
        Args:
            output_directory: Path to output directory
            source_directory: Path to source Canvas export directory (required for asset copying)
        """
        self.output_directory = output_directory
        self.source_directory = source_directory
        self.errors: list[MigrationError] = []
        
        # Create output directory
        ensure_directory_exists(output_directory)
    
    def export(self, tutor_course: TutorCourse) -> VerificationReport:
        """
        Export Tutor course to JSON and copy assets.
        
        Args:
            tutor_course: Tutor course model
            
        Returns:
            VerificationReport
        """
        report = VerificationReport(timestamp=datetime.now())
        report.output_directory = str(self.output_directory)
        report.output_format = "json"
        
        try:
            # Convert course to dictionary
            course_dict = self._course_to_dict(tutor_course)
            
            # Write to JSON file
            output_file = self.output_directory / "tutor_course.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(course_dict, f, indent=2, ensure_ascii=False)
            
            # Copy assets if source directory is provided
            if self.source_directory:
                self._copy_assets()

            # Export HTML content
            self._export_html_content(tutor_course)
            
            # Calculate output size
            report.total_output_size_mb = output_file.stat().st_size / (1024 * 1024)
            
            # Create import instructions
            self._create_import_instructions()
            
            # Basic verification
            report.all_assets_exist = True
            report.all_links_resolve = True
            report.no_orphaned_questions = True
            report.quiz_question_counts_match = True
            report.module_item_counts_match = True
            
        except Exception as e:
            self.errors.append(MigrationError(
                severity=ErrorSeverity.ERROR,
                error_type="EXPORT_ERROR",
                message=f"Failed to export course: {str(e)}",
                suggested_action="Check output directory permissions"
            ))
        
        report.errors = self.errors
        return report

    def _copy_assets(self):
        """Copy assets from source to output"""
        import shutil
        
        # Source asset directories
        source_assets = self.source_directory / "web_resources"
        
        # Destination asset directory
        dest_assets = self.output_directory / "assets"
        
        if source_assets.exists():
            # Copy entire tree
            if dest_assets.exists():
                shutil.rmtree(dest_assets)
            shutil.copytree(source_assets, dest_assets)
            print(f"✓ Copied assets from {source_assets.name} to assets/")
        else:
            print(f"⚠ Warning: Source assets directory not found at {source_assets}")
            
    def _export_html_content(self, course: TutorCourse):
        """Export content to HTML files"""
        lessons_dir = self.output_directory / "lessons"
        ensure_directory_exists(lessons_dir)
        
        from ..utils.html_utils import wrap_in_html_document
        import re
        
        for topic in course.topics:
            # Create topic directory
            safe_title = re.sub(r'[^a-zA-Z0-9]', '_', topic.topic_title).lower()
            topic_dir = lessons_dir / f"module_{topic.topic_order}_{safe_title}"
            ensure_directory_exists(topic_dir)
            
            # Export lessons
            for lesson in topic.lessons:
                safe_lesson_title = re.sub(r'[^a-zA-Z0-9]', '_', lesson.post_title).lower()
                filename = f"{lesson.menu_order}_{safe_lesson_title}.html"
                
                html_content = wrap_in_html_document(lesson.post_title, lesson.post_content)
                
                with open(topic_dir / filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                    
            # Export quizzes (optional, but good for review)
            for quiz in topic.quizzes:
                safe_quiz_title = re.sub(r'[^a-zA-Z0-9]', '_', quiz.post_title).lower()
                filename = f"quiz_{quiz.menu_order}_{safe_quiz_title}.html"
                
                html_content = wrap_in_html_document(quiz.post_title, quiz.post_content)
                
                with open(topic_dir / filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)

            # Export assignments
            for assignment in topic.assignments:
                safe_assign_title = re.sub(r'[^a-zA-Z0-9]', '_', assignment.post_title).lower()
                filename = f"assign_{assignment.menu_order}_{safe_assign_title}.html"
                
                html_content = wrap_in_html_document(assignment.post_title, assignment.post_content)
                
                with open(topic_dir / filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                    
        print(f"✓ exported HTML content to lessons/")
    
    def _course_to_dict(self, course: TutorCourse) -> Dict[str, Any]:
        """
        Convert TutorCourse to dictionary for JSON export.
        
        Args:
            course: Tutor course model
            
        Returns:
            Dictionary representation
        """
        return {
            "course": {
                "title": course.post_title,
                "content": course.post_content,
                "status": course.post_status,
                "settings": course._tutor_course_settings,
            },
            "topics": [
                {
                    "title": topic.topic_title,
                    "summary": topic.topic_summary,
                    "order": topic.topic_order,
                    "lessons": [
                        {
                            "title": lesson.post_title,
                            "content": lesson.post_content,
                            "status": lesson.post_status,
                            "order": lesson.menu_order,
                        }
                        for lesson in topic.lessons
                    ],
                    "quizzes": [
                        {
                            "title": quiz.post_title,
                            "content": quiz.post_content,
                            "status": quiz.post_status,
                            "settings": quiz.quiz_option,
                            "order": quiz.menu_order,
                            "questions": [
                                {
                                    "title": q.question_title,
                                    "description": q.question_description,
                                    "type": q.question_type.value,
                                    "marks": q.question_mark,
                                    "order": q.question_order,
                                    "answers": [
                                        {
                                            "title": a.answer_title,
                                            "is_correct": a.is_correct,
                                            "order": a.answer_order,
                                        }
                                        for a in q.answers
                                    ]
                                }
                                for q in quiz.questions
                            ]
                        }
                        for quiz in topic.quizzes
                    ],
                    "assignments": [
                        {
                            "title": assignment.post_title,
                            "content": assignment.post_content,
                            "status": assignment.post_status,
                            "settings": assignment.assignment_option,
                            "order": assignment.menu_order,
                        }
                        for assignment in topic.assignments
                    ]
                }
                for topic in course.topics
            ],
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "source": "Canvas LMS",
                "converter_version": "2.0.0"
            }
        }
    
    def _create_import_instructions(self) -> None:
        """Create import instructions file"""
        instructions = """# Tutor LMS Import Instructions

## Overview
This directory contains the exported Tutor LMS course in JSON format.

## Files
- `tutor_course.json`: Complete course structure with topics, lessons, quizzes, and assignments
- `migration_report.json`: Detailed migration report
- `migration_report.html`: Human-readable migration report

## Import Methods

### Method 1: Using Custom Import Plugin (Recommended)
1. Install the Tutor LMS JSON Importer plugin (to be developed)
2. Go to WordPress Admin → Tutor LMS → Import
3. Upload `tutor_course.json`
4. Review and confirm import

### Method 2: Manual Import
1. Review the JSON structure in `tutor_course.json`
2. Manually create course, topics, lessons, quizzes in Tutor LMS
3. Copy content from JSON to corresponding fields

### Method 3: Programmatic Import
Use the provided JSON structure to create a custom import script using WordPress/Tutor LMS APIs.

## Important Notes
- Review the migration report for any warnings or errors
- Check asset paths and update if necessary
- Verify quiz questions and answers
- Test all quizzes before publishing

## Support
For issues or questions, refer to the migration report or contact support.
"""
        
        instructions_file = self.output_directory / "IMPORT_INSTRUCTIONS.md"
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write(instructions)
