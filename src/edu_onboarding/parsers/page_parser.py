"""
Page Parser - Parses Canvas wiki pages.

Extracts page content from wiki_content/*.xml files.
"""

from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..models.canvas_models import CanvasPage, WorkflowState
from ..models.migration_report import MigrationError, ErrorSeverity
from ..utils.xml_utils import parse_xml_file, find_element, get_element_text
from ..utils.html_utils import clean_html, get_inner_html


class PageParser:
    """
    Parses Canvas page XML files.
    """
    
    def __init__(self, course_directory: Path):
        """
        Initialize page parser.
        
        Args:
            course_directory: Path to Canvas course export directory
        """
        self.course_directory = course_directory
        self.wiki_content_dir = course_directory / "wiki_content"
        self.errors: List[MigrationError] = []
    
    def parse_page(self, page_file: Path) -> Optional[CanvasPage]:
        """
        Parse a single page XML file.
        
        Args:
            page_file: Path to page XML file
            
        Returns:
            CanvasPage object or None if parsing fails
        """
        try:
            root = parse_xml_file(page_file)
            if root is None:
                self.errors.append(MigrationError(
                    severity=ErrorSeverity.ERROR,
                    error_type="PAGE_PARSE_ERROR",
                    message=f"Failed to parse page file: {page_file.name}",
                    file_path=str(page_file)
                ))
                return None
            
            # Extract page data
            title = self._extract_title(root, page_file)
            body = self._extract_body(root)
            workflow_state = self._extract_workflow_state(root)
            
            page = CanvasPage(
                title=title,
                identifier=page_file.stem,
                body=body,
                workflow_state=workflow_state,
                source_file=str(page_file)
            )
            
            return page
            
        except Exception as e:
            self.errors.append(MigrationError(
                severity=ErrorSeverity.ERROR,
                error_type="PAGE_PARSE_ERROR",
                message=f"Unexpected error parsing page: {str(e)}",
                file_path=str(page_file)
            ))
            return None
    
    def _extract_title(self, root, page_file: Path) -> str:
        """Extract page title"""
        title_elem = find_element(root, './/title', {})
        if title_elem is not None:
            return get_element_text(title_elem, page_file.stem)
        return page_file.stem
    
    def _extract_body(self, root) -> str:
        """Extract page body HTML"""
        body_elem = find_element(root, './/body', {})
        if body_elem is not None:
            # Get inner HTML
            body_html = get_inner_html(body_elem)
            return clean_html(body_html)
        
        # Fallback: try text element
        text_elem = find_element(root, './/text', {})
        if text_elem is not None:
            return clean_html(get_element_text(text_elem, ""))
        
        return ""
    
    def _extract_workflow_state(self, root) -> WorkflowState:
        """Extract workflow state"""
        state_elem = find_element(root, './/workflow_state', {})
        if state_elem is not None:
            state_text = get_element_text(state_elem, "active").lower()
            if state_text == "unpublished":
                return WorkflowState.UNPUBLISHED
            elif state_text == "deleted":
                return WorkflowState.DELETED
        return WorkflowState.ACTIVE
    
    def parse_all_pages(self) -> List[CanvasPage]:
        """
        Parse all pages in wiki_content directory.
        
        Returns:
            List of CanvasPage objects
        """
        pages = []
        
        if not self.wiki_content_dir.exists():
            return pages
        
        for page_file in self.wiki_content_dir.glob("*.xml"):
            page = self.parse_page(page_file)
            if page:
                pages.append(page)
        
        return pages
