"""
Discussion Parser - Parses Canvas discussion topics.

Extracts discussion prompts from discussion XML files (imsdt_xmlv1p1).
"""

from pathlib import Path
from typing import List, Optional

from models.canvas_models import CanvasDiscussion, WorkflowState
from models.migration_report import MigrationError, ErrorSeverity
from utils.xml_utils import parse_xml_file, find_element, get_element_text
from utils.html_utils import clean_html


class DiscussionParser:
    """
    Parses Canvas discussion XML files.
    """
    
    def __init__(self, course_directory: Path):
        """
        Initialize discussion parser.
        
        Args:
            course_directory: Path to Canvas course export directory
        """
        self.course_directory = course_directory
        self.errors: List[MigrationError] = []
    
    def parse_discussion(self, xml_file: Path) -> Optional[CanvasDiscussion]:
        """
        Parse a single discussion XML file.
        
        Args:
            xml_file: Path to discussion XML file
            
        Returns:
            CanvasDiscussion object or None if parsing fails
        """
        try:
            root = parse_xml_file(xml_file)
            if root is None:
                self.errors.append(MigrationError(
                    severity=ErrorSeverity.ERROR,
                    error_type="DISCUSSION_PARSE_ERROR",
                    message=f"Failed to parse discussion file: {xml_file.name}",
                    file_path=str(xml_file)
                ))
                return None
            
            # The root is usually <topic>
            # Extract title and text (body)
            title = get_element_text(find_element(root, './/title', {}), xml_file.stem)
            
            # Canvas discussions store prompt in <text>
            body_elem = find_element(root, './/text', {})
            body = ""
            if body_elem is not None:
                body = clean_html(get_element_text(body_elem, ""))
            else:
                body = "<p>Discussion prompt - see course instructions.</p>"
            
            discussion = CanvasDiscussion(
                title=title,
                identifier=xml_file.stem,
                body=body,
                workflow_state=WorkflowState.ACTIVE,
                source_file=str(xml_file)
            )
            
            return discussion
            
        except Exception as e:
            self.errors.append(MigrationError(
                severity=ErrorSeverity.ERROR,
                error_type="DISCUSSION_PARSE_ERROR",
                message=f"Unexpected error parsing discussion: {str(e)}",
                file_path=str(xml_file)
            ))
            return None

    def find_all_discussions(self) -> List[CanvasDiscussion]:
        """
        Find and parse all discussions in the course directory.
        Since discussions can be referenced by resources, we typically 
        parse them when identified by the manifest.
         However, many Canvas exports put them in a dedicated folder or root.
        """
        # This is a helper if we want to bulk-parse, 
        # but orchestration usually happens via manifest identifiers.
        discussions = []
        # Support common Canvas folders if they exist
        discussion_dirs = ["discussion_topics", "course_settings"]
        for d in discussion_dirs:
            target = self.course_directory / d
            if target.exists():
                for xml_file in target.glob("*.xml"):
                    # Basic heuristic: check if it looks like a discussion
                    # (Or we just trust the manifest identification)
                    disc = self.parse_discussion(xml_file)
                    if disc:
                        discussions.append(disc)
        return discussions
