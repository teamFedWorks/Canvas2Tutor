"""
Content parsers for Canvas entities
"""

from .manifest_parser import ManifestParser
from .page_parser import PageParser
from .assignment_parser import AssignmentParser
from .quiz_parser import QuizParser
from .discussion_parser import DiscussionParser
from .weblink_parser import WebLinkParser
from .question_parser import QuestionParser
from .orphaned_content_handler import OrphanedContentHandler
from .pptx_parser import PptxParser

__all__ = [
    'ManifestParser',
    'PageParser',
    'AssignmentParser',
    'QuizParser',
    'DiscussionParser',
    'WebLinkParser',
    'QuestionParser',
    'OrphanedContentHandler',
    'PptxParser',
]
