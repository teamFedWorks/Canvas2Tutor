import os
import shutil
import tempfile
import zipfile
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

from ..validation.package_validator import PackageValidator
from ..detection.format_detector import FormatDetector, ExportFormat
from ..parsers.imscc_parser import IMSCCParser
from ..parsers.canvas_export_parser import CanvasExportParser
from ..transformers.course_transformer import CourseTransformer
from ..assets.asset_uploader import AssetUploader
from ..exporters.mongodb_exporter import MongoDBExporter
from ..utils.logger import get_logger

logger = get_logger(__name__)

class IngestionWorker:
    """
    Orchestrates the hardened ingestion pipeline.
    """

    def __init__(self, s3_bucket: str, cdn_url: str):
        self.s3_bucket = s3_bucket
        self.cdn_url = cdn_url
        self.validator = PackageValidator()
        self.exporter = MongoDBExporter()

    def process_package(self, zip_path: Path, university_id: str, author_id: str, program_name: str = None) -> Dict[str, Any]:
        """
        Runs the pipeline for a single course package with full hardening and intelligent onboarding.
        """
        task_id = str(uuid.uuid4())
        logger.log("INFO", "Starting intelligent ingestion task", 
                   task_id=task_id, 
                   filename=zip_path.name)
        
        # 1. Idempotency Check (Package Checksum)
        checksum = self.validator.calculate_checksum(zip_path)
        existing_job = self.exporter.find_by_checksum(checksum)
        
        if existing_job and existing_job.get('status') == 'completed':
            return {
                "status": "success", 
                "course_id": existing_job.get('course_id'), 
                "message": "This file was already imported.",
                "reused": True
            }

        self.exporter.track_job(task_id, checksum, "processing")

        # 2. Security Validation
        is_valid, msg = self.validator.validate_zip(zip_path)
        if not is_valid:
            self.exporter.track_job(task_id, checksum, "failed")
            return {"status": "failed", "error": msg}

        # 3. Extract to temp directory
        extract_dir = Path(tempfile.mkdtemp(prefix="lms_ingest_"))
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # 4. Detect Format & Parse
            fmt = FormatDetector.detect(extract_dir)
            if fmt == ExportFormat.UNKNOWN:
                self.exporter.track_job(task_id, checksum, "failed")
                return {"status": "failed", "error": "Unknown format."}

            parser = IMSCCParser(extract_dir) if fmt == ExportFormat.IMSCC else CanvasExportParser(extract_dir)
            parsed_data = parser.parse()
            
            if "error" in parsed_data:
                self.exporter.track_job(task_id, checksum, "failed")
                return {"status": "failed", "error": parsed_data["error"]}

            # 5. Intelligent Program Discovery
            # Use provided program_name or derive it (e.g., from filename or fallback)
            final_program_name = program_name or self._discover_program_name(zip_path, parsed_data)
            program_id = self.exporter.get_or_create_program(university_id, final_program_name)

            # 6. Logical Deduplication (Title + Program)
            course_title = parsed_data.get("title", "Untitled Course")
            existing_course_id = self.exporter.check_logical_duplicate(university_id, program_id, course_title)
            
            if existing_course_id:
                logger.log("INFO", "Course already exists in program", course_id=existing_course_id)
                self.exporter.track_job(task_id, checksum, "completed", course_id=existing_course_id)
                return {
                    "status": "success", 
                    "course_id": existing_course_id, 
                    "message": f"Course '{course_title}' already exists in this program.",
                    "logical_duplicate": True
                }

            # 7. Transform
            transformer = CourseTransformer()
            transformed_course = transformer.transform(parsed_data, university_id, program_id, author_id)

            # 8. Process Assets
            uploader = AssetUploader(extract_dir, self.s3_bucket, self.cdn_url)
            uploader.process_course_assets(transformed_course)

            # 9. Export
            course_id = self.exporter.export(transformed_course)

            # Mark job complete
            self.exporter.track_job(task_id, checksum, "completed", course_id=course_id)

            return {
                "status": "success",
                "course_id": course_id,
                "course_data": transformed_course, # Return full data for UI editing
                "program_name": final_program_name,
                "format": fmt.value,
                "task_id": task_id
            }

        except Exception as e:
            logger.log("ERROR", "Pipeline crash", task_id=task_id, error=str(e))
            self.exporter.track_job(task_id, checksum, "failed")
            return {"status": "failed", "error": f"Internal pipeline error: {str(e)}"}
        finally:
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            self.exporter.close()

    def _discover_program_name(self, zip_path: Path, parsed_data: Dict[str, Any]) -> str:
        """
        Tries to guess the program name if not provided.
        """
        # Strategy A: Check filename prefix (e.g. BSCS_Algo.zip)
        filename = zip_path.name
        if "_" in filename:
            return filename.split("_")[0].upper()
        
        # Strategy B: Fallback to a general program
        return "General Onboarding"
