"""
Asset Uploader Stage

Scans HTML content in the LmsCourse model, migrates both local 
file references and remote Canvas URLs to S3, and rewrites 
URLs to point to the S3 CDN.
"""

import os
import re
import requests
import tempfile
import shutil
from pathlib import Path
from typing import List, Set, Dict, Tuple, Optional
import boto3
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup

from models.lms_models import LmsCourse, LmsCurriculumModule, LmsCurriculumItem, LmsAttachment
from models.canvas_models import CanvasCourse
from config.lms_schemas import UPLOADABLE_EXTENSIONS, S3_KEY_TEMPLATE
from observability.logger import get_logger

logger = get_logger(__name__)


class AssetUploader:
    """
    Handles S3 uploads and HTML URL rewriting for course assets.
    Supports both local and remote (HTTP) source assets.
    """

    def __init__(
        self, 
        s3_bucket: str,
        course_id: str, 
        source_dir: Optional[Path] = None, 
        cdn_url: str = ""
    ):
        """
        Initialize the uploader.
        """
        self.course_id = course_id
        self.source_dir = source_dir
        self.s3_bucket = s3_bucket
        self.cdn_base_url = (cdn_url or os.getenv("CDN_URL", "")).rstrip('/')
        
        self.s3_client = boto3.client('s3')
        
        # Auth for remote Canvas assets
        self.api_token = os.getenv("CANVAS_API_TOKEN")
        
        # Track uploaded files
        self.uploaded_assets: Dict[str, str] = {}  # source -> s3_url
        
        self.stats = {"uploaded": 0, "skipped": 0, "failed": 0}

    def process_course_assets(self, lms_course: LmsCourse, canvas_course: Optional[CanvasCourse] = None) -> LmsCourse:
        """
        Full asset migration pass:
          1. Scan HTML content for embedded asset URLs and rewrite to S3.
          2. Upload all manifest webcontent file resources (PDFs, PPTXs, DOCXs, etc.)
             and attach them to the matching curriculum item.
        """
        logger.info(f"Starting asset migration for course {self.course_id}")

        # Pass 1: HTML-embedded assets (images, videos, linked files in content)
        for module in lms_course.curriculum:
            for item in module.items:
                item.content = self._process_html(item.content, item.attachments)

        # Pass 2: Manifest-declared file resources not embedded in HTML
        if canvas_course and canvas_course.resources and self.source_dir:
            self._upload_manifest_resources(lms_course, canvas_course)

        logger.info("Asset migration complete", extra=self.stats)
        return lms_course

    def _upload_manifest_resources(self, lms_course: LmsCourse, canvas_course: CanvasCourse) -> None:
        """
        Upload every webcontent file resource declared in the manifest that has
        an uploadable extension, then attach the S3 URL to the matching
        LmsCurriculumItem (matched via _content_ref == resource identifier).

        Matching strategy (in order):
          1. Exact _content_ref match (resource identifierref stored on item)
          2. Item title contains the filename stem (fuzzy title match)
          3. Attach to the module that contains the closest title match
          4. Last resort: first item of the first module
        """
        # Build lookup: resource_ref -> list of items (multiple items can share a resource)
        ref_map: Dict[str, List[LmsCurriculumItem]] = {}
        title_map: Dict[str, LmsCurriculumItem] = {}
        fallback_item: Optional[LmsCurriculumItem] = None

        for module in lms_course.curriculum:
            for item in module.items:
                for key in filter(None, [item._canvasId, getattr(item, '_content_ref', None)]):
                    ref_map.setdefault(key, []).append(item)
                title_key = re.sub(r'[^\w]', '', item.title.lower())
                title_map[title_key] = item
                if fallback_item is None:
                    fallback_item = item

        for res_id, resource in canvas_course.resources.items():
            if not resource.href:
                continue

            ext = Path(resource.href).suffix.lower()
            if ext not in UPLOADABLE_EXTENSIONS:
                continue

            local_file = self.source_dir / resource.href
            if not local_file.exists():
                self.stats["skipped"] += 1
                continue

            # Avoid re-uploading the same file, but still attach to the correct item
            cache_key = resource.href
            if cache_key in self.uploaded_assets:
                s3_url = self.uploaded_assets[cache_key]
            else:
                s3_url = self._perform_s3_upload(local_file, local_file.name)
                if s3_url:
                    self.uploaded_assets[cache_key] = s3_url

            if not s3_url:
                continue

            file_type = ext.upper().strip('.')
            attachment = LmsAttachment(
                name=local_file.name,
                url=s3_url,
                size=self._human_size(local_file),
                type=file_type
            )

            # --- Matching strategy ---
            target_items = ref_map.get(res_id, [])

            if not target_items:
                # Fuzzy title match on filename stem
                stem_key = re.sub(r'[^\w]', '', local_file.stem.lower())
                item = title_map.get(stem_key)
                if not item:
                    for key, candidate in title_map.items():
                        if stem_key and (stem_key in key or key in stem_key):
                            item = candidate
                            break
                target_items = [item] if item else ([fallback_item] if fallback_item else [])

            for target_item in target_items:
                if target_item and not any(a.url == s3_url for a in target_item.attachments):
                    target_item.attachments.append(attachment)

    def _human_size(self, path: Path) -> str:
        """Return a human-readable file size string."""
        try:
            size = path.stat().st_size
            for unit in ("B", "KB", "MB", "GB"):
                if size < 1024:
                    return f"{size:.1f}{unit}"
                size /= 1024
            return f"{size:.1f}TB"
        except Exception:
            return "0MB"

    def _process_html(self, html_content: str, asset_list: Optional[List[LmsAttachment]] = None) -> str:
        """
        Scan HTML for asset tags, migrate them to S3, and rewrite paths.
        Populates the attachments list with object metadata.
        """
        if not html_content or not isinstance(html_content, str):
            return html_content

        soup = BeautifulSoup(html_content, 'html.parser')
        modified = False

        tags_attrs = [
            ('img', 'src'), ('video', 'src'), ('source', 'src'),
            ('a', 'href'), ('iframe', 'src'), ('embed', 'src')
        ]

        for tag_name, attr in tags_attrs:
            for tag in soup.find_all(tag_name):
                url = tag.get(attr)
                if not url: continue

                # Determine if asset needs migration
                if self._should_migrate(url):
                    s3_url = self._migrate_asset(url)
                    if s3_url:
                        tag[attr] = s3_url
                        modified = True
                        
                        # Add to attachments if it's a link (downloadable)
                        if asset_list is not None and tag_name == 'a':
                            filename = os.path.basename(url.split('?')[0])
                            ext = os.path.splitext(filename)[1].upper().strip('.')
                            attachment = LmsAttachment(
                                name=tag.get_text() or filename,
                                url=s3_url,
                                size="0MB", # Known limitation without HEAD request
                                type=ext or "FILE"
                            )
                            asset_list.append(attachment)

        return str(soup) if modified else html_content

    def _should_migrate(self, url: str) -> bool:
        """Check if URL points to a local file or a remote Canvas asset."""
        if any(url.startswith(p) for p in ['data:', 'mailto:', '#']):
            return False
            
        # If it's on our CDN already, skip
        if self.cdn_base_url and url.startswith(self.cdn_base_url):
            return False
            
        # Remote HTTP assets
        if url.startswith('http'):
            # For now migrate all external images/media to pin them to our S3
            ext = os.path.splitext(url.split('?')[0])[1].lower()
            return ext in UPLOADABLE_EXTENSIONS
            
        # Local paths
        return True

    def _migrate_asset(self, path_or_url: str) -> Optional[str]:
        """Orchestrates asset migration from local or remote source."""
        if path_or_url in self.uploaded_assets:
            return self.uploaded_assets[path_or_url]

        if path_or_url.startswith('http'):
            return self._download_and_upload(path_or_url)
        else:
            return self._upload_local(path_or_url)

    def _download_and_upload(self, url: str) -> Optional[str]:
        """Download remote asset and upload to S3."""
        temp_file = Path(tempfile.mktemp())
        try:
            headers = {}
            if self.api_token and ('canvas' in url or 'sfc.edu' in url):
                headers["Authorization"] = f"Bearer {self.api_token}"
                
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(temp_file, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            
            # Upload to S3
            filename = os.path.basename(url.split('?')[0])
            s3_url = self._perform_s3_upload(temp_file, filename)
            
            self.uploaded_assets[url] = s3_url
            return s3_url
        except Exception as e:
            logger.error(f"Failed to migrate remote asset {url}: {e}")
            self.stats["failed"] += 1
            return None
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def _upload_local(self, relative_path: str) -> Optional[str]:
        """Upload local file from source_dir to S3."""
        if not self.source_dir:
            return None
            
        from urllib.parse import unquote
        clean_path = unquote(relative_path).split('?')[0].lstrip('/')
        local_file = self.source_dir / clean_path
        
        if not local_file.exists():
            self.stats["skipped"] += 1
            return None

        s3_url = self._perform_s3_upload(local_file, os.path.basename(clean_path))
        self.uploaded_assets[relative_path] = s3_url
        return s3_url

    def _perform_s3_upload(self, local_path: Path, filename: str) -> Optional[str]:
        """Generic S3 upload logic with timestamp prefix."""
        import time
        timestamp = int(time.time() * 1000)
        ts_filename = f"{timestamp}_{filename}"
        s3_key = S3_KEY_TEMPLATE.format(course_id=self.course_id, filename=ts_filename)
        try:
            content_type = self._guess_content_type(local_path)
            self.s3_client.upload_file(
                str(local_path), self.s3_bucket, s3_key,
                ExtraArgs={'ContentType': content_type}
            )
            final_url = f"{self.cdn_base_url}/{s3_key}" if self.cdn_base_url else f"https://{self.s3_bucket}.s3.amazonaws.com/{s3_key}"
            self.stats["uploaded"] += 1
            return final_url
        except ClientError as e:
            logger.error(f"S3 upload failed for {filename}: {e}")
            self.stats["failed"] += 1
            return None

    def _guess_content_type(self, path: Path) -> str:
        import mimetypes
        mtype, _ = mimetypes.guess_type(str(path))
        return mtype or 'application/octet-stream'
