"""
WebLink Parser - Parses Canvas external web links.

Extracts external URLs from web link XML files (imswl_xmlv1p1).
"""

from pathlib import Path
from typing import List, Optional

from models.canvas_models import CanvasWebLink
from models.migration_report import MigrationError, ErrorSeverity
from utils.xml_utils import parse_xml_file, find_element, get_element_text, get_element_attribute


class WebLinkParser:
    """
    Parses Canvas web link XML files.
    """
    
    def __init__(self, course_directory: Path):
        """
        Initialize web link parser.
        
        Args:
            course_directory: Path to Canvas course export directory
        """
        self.course_directory = course_directory
        self.errors: List[MigrationError] = []
    
    def parse_weblink(self, xml_file: Path) -> Optional[CanvasWebLink]:
        """
        Parse a single web link XML file.
        
        Args:
            xml_file: Path to web link XML file
            
        Returns:
            CanvasWebLink object or None if parsing fails
        """
        try:
            root = parse_xml_file(xml_file)
            if root is None:
                self.errors.append(MigrationError(
                    severity=ErrorSeverity.ERROR,
                    error_type="WEBLINK_PARSE_ERROR",
                    message=f"Failed to parse web link file: {xml_file.name}",
                    file_path=str(xml_file)
                ))
                return None
            
            # The root is usually <webLink>
            # Extract title and URL
            title = get_element_text(find_element(root, './/title', {}), xml_file.stem)
            
            # URL can be in <url href="..."> or just <url>...</url>
            url_elem = find_element(root, './/url', {})
            url = ""
            if url_elem is not None:
                url = get_element_attribute(url_elem, 'href')
                if not url:
                    url = get_element_text(url_elem, "")
            
            if not url:
                return None
            
            weblink = CanvasWebLink(
                title=title,
                identifier=xml_file.stem,
                url=url.strip(),
                source_file=str(xml_file)
            )
            
            return weblink
            
        except Exception as e:
            self.errors.append(MigrationError(
                severity=ErrorSeverity.ERROR,
                error_type="WEBLINK_PARSE_ERROR",
                message=f"Unexpected error parsing web link: {str(e)}",
                file_path=str(xml_file)
            ))
            return None
