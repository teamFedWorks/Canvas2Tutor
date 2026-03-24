"""
ZIP Adapter - Handles ingestion from local Canvas export ZIP files.
"""

import tempfile
import zipfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from core.stages.package_validator import PackageValidator
from utils.format_detector import FormatDetector, ExportFormat
from parsers.imscc_parser import IMSCCParser
from parsers.canvas_export_parser import CanvasExportParser
from models.canvas_models import CanvasCourse
from observability.logger import get_logger

logger = get_logger(__name__)

class ZipAdapter:
    """
    Adapter for processing local Canvas ZIP exports (IMSCC/ZIP).
    """

    def __init__(self):
        self.validator = PackageValidator()

    def load(self, payload: Dict[str, Any]) -> CanvasCourse:
        """
        Loads and parses a course from a local ZIP file.
        Payload expected: {"zip_path": Path}
        """
        zip_path = Path(payload["zip_path"])
        if not zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        # 1. Validation
        is_valid, msg = self.validator.validate_zip(zip_path)
        if not is_valid:
            raise ValueError(f"Invalid ZIP package: {msg}")

        # 2. Extract to temp
        extract_dir = Path(tempfile.mkdtemp(prefix="lms_zip_extract_"))
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # 3. Detect & Parse
            fmt = FormatDetector.detect(extract_dir)
            if fmt == ExportFormat.UNKNOWN:
                raise ValueError("Unknown export format in ZIP.")

            parser = IMSCCParser(extract_dir) if fmt == ExportFormat.IMSCC else CanvasExportParser(extract_dir)
            
            # The parsers currently return dictionaries or objects? 
            # IngestionWorker used parser.parse().
            # Most parsers in this repo seem to return CanvasCourse or a dict that needs transformation.
            # Looking at ingestion_worker.py:73, it returns parsed_data.
            
            canvas_course = parser.parse()
            if isinstance(canvas_course, dict) and "error" in canvas_course:
                raise ValueError(canvas_course["error"])
                
            # If it's already a CanvasCourse, good. If not, we might need a step here.
            # But according to models/canvas_models.py, it should be a CanvasCourse.
            
            # Record the source directory for asset uploader
            if hasattr(canvas_course, 'source_directory'):
                canvas_course.source_directory = str(extract_dir)
                
            return canvas_course

        except Exception as e:
            if extract_dir.exists():
                shutil.rmtree(extract_dir)
            raise e
        # Note: extract_dir cleanup should happen after the whole pipeline runs 
        # because AssetUploader needs the files. 
        # We'll need to handle cleanup in the IngestionWorker.
