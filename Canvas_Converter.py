"""
Production Canvas → Tutor LMS Migration Pipeline

This is the main entry point for the migration pipeline.
Orchestrates all 5 stages of the migration process.
"""

import sys
import time
from pathlib import Path
from typing import Optional

from src.models.migration_report import MigrationReport, ReportStatus
from src.stages.validator import Validator
from src.stages.parser import Parser
from src.transformers.course_transformer import CourseTransformer
from src.exporters.tutor_exporter import TutorExporter
from src.exporters.report_generator import ReportGenerator


class MigrationPipeline:
    """
    Main migration pipeline orchestrator.
    
    Executes all 5 stages:
    1. Validation & Inventory
    2. Semantic Parsing
    3. Content Resolution (integrated into transformer)
    4. Tutor LMS Transformation
    5. Export & Verification
    """
    
    def __init__(self, course_directory: Path, output_directory: Optional[Path] = None):
        """
        Initialize migration pipeline.
        
        Args:
            course_directory: Path to Canvas course export directory
            output_directory: Path to output directory (default: course_dir/tutor_lms_output)
        """
        self.course_directory = Path(course_directory)
        
        if output_directory is None:
            self.output_directory = self.course_directory / "tutor_lms_output"
        else:
            self.output_directory = Path(output_directory)
        
        self.output_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize report
        self.report = MigrationReport(
            status=ReportStatus.SUCCESS,
            source_directory=str(self.course_directory),
            output_directory=str(self.output_directory)
        )
    
    def run(self) -> MigrationReport:
        """
        Execute the complete migration pipeline.
        
        Returns:
            MigrationReport with results
        """
        start_time = time.time()
        
        print("=" * 80)
        print("CANVAS → TUTOR LMS MIGRATION PIPELINE v2.0")
        print("=" * 80)
        print()
        
        try:
            # Stage 1: Validation & Inventory
            print("[1/5] Validating Canvas export structure...")
            validation_report = self._stage_1_validate()
            self.report.validation_report = validation_report
            
            if not validation_report.passed:
                print("❌ Validation failed. See report for details.")
                self.report.status = ReportStatus.FAILURE
                return self._finalize_report(start_time)
            
            print(f"✓ Validation passed")
            print(f"  - Found {validation_report.inventory.pages} pages")
            print(f"  - Found {validation_report.inventory.modules} modules")
            print()
            
            # Stage 2: Semantic Parsing
            print("[2/5] Parsing Canvas content...")
            canvas_course, parse_report = self._stage_2_parse()
            self.report.parse_report = parse_report
            
            if canvas_course is None:
                print("❌ Parsing failed. See report for details.")
                self.report.status = ReportStatus.FAILURE
                return self._finalize_report(start_time)
            
            self.report.source_course_title = canvas_course.title
            self.report.source_content_counts = canvas_course.get_content_counts()
            
            print(f"✓ Parsed course: {canvas_course.title}")
            print(f"  - Modules: {len(canvas_course.modules)}")
            print(f"  - Pages: {len(canvas_course.pages)}")
            print(f"  - Assignments: {len(canvas_course.assignments)}")
            print(f"  - Quizzes: {len(canvas_course.quizzes)}")
            print()
            
            # Stage 3 & 4: Transformation (includes content resolution)
            print("[3/5] Transforming to Tutor LMS format...")
            tutor_course, transformation_report = self._stage_4_transform(canvas_course)
            self.report.transformation_report = transformation_report
            
            self.report.migrated_content_counts = tutor_course.get_content_counts()
            
            print(f"✓ Transformed to Tutor LMS")
            print(f"  - Topics: {len(tutor_course.topics)}")
            print(f"  - Lessons: {transformation_report.lessons_created}")
            print(f"  - Quizzes: {transformation_report.quizzes_created}")
            print(f"  - Questions: {transformation_report.questions_created}")
            print()
            
            # Stage 5: Export & Verification
            print("[4/5] Exporting to JSON...")
            verification_report = self._stage_5_export(tutor_course)
            self.report.verification_report = verification_report
            
            print(f"✓ Exported to {self.output_directory}")
            print(f"  - Output size: {verification_report.total_output_size_mb:.2f} MB")
            print()
            
            # Generate reports
            print("[5/5] Generating migration reports...")
            self._generate_reports()
            
            print("✓ Reports generated")
            print()
            
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            self.report.status = ReportStatus.FAILURE
            import traceback
            traceback.print_exc()
        
        return self._finalize_report(start_time)
    
    def _stage_1_validate(self):
        """Stage 1: Validation & Inventory"""
        validator = Validator(self.course_directory)
        return validator.validate()
    
    def _stage_2_parse(self):
        """Stage 2: Semantic Parsing"""
        parser = Parser(self.course_directory)
        return parser.parse()
    
    def _stage_4_transform(self, canvas_course):
        """Stage 4: Tutor LMS Transformation"""
        transformer = CourseTransformer()
        return transformer.transform(canvas_course)
    
    def _stage_5_export(self, tutor_course):
        """Stage 5: Export & Verification"""
        exporter = TutorExporter(self.output_directory, self.course_directory)
        return exporter.export(tutor_course)
    
    def _generate_reports(self):
        """Generate migration reports"""
        report_generator = ReportGenerator(self.output_directory)
        report_generator.generate(self.report)
    
    def _finalize_report(self, start_time: float) -> MigrationReport:
        """Finalize and return migration report"""
        self.report.execution_time_seconds = time.time() - start_time
        self.report.aggregate_errors()
        
        print("=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print(f"Status: {self.report.status.value.upper()}")
        print(f"Errors: {self.report.total_errors}")
        print(f"Warnings: {self.report.total_warnings}")
        print(f"Execution time: {self.report.execution_time_seconds:.2f}s")
        print()
        print(f"Output directory: {self.output_directory}")
        print(f"  - tutor_course.json")
        print(f"  - migration_report.json")
        print(f"  - migration_report.html")
        print(f"  - IMPORT_INSTRUCTIONS.md")
        print("=" * 80)
        
        return self.report


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python Canvas_Converter.py <course_directory> [output_directory]")
        print()
        print("Example:")
        print("  python Canvas_Converter.py ./cs-2000")
        print("  python Canvas_Converter.py ./cs-2000 ./output")
        sys.exit(1)
    
    course_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    pipeline = MigrationPipeline(course_dir, output_dir)
    report = pipeline.run()
    
    # Exit with error code if migration failed
    if report.status == ReportStatus.FAILURE:
        sys.exit(1)


if __name__ == "__main__":
    main()
