"""
Configuration and schema definitions
"""

from .canvas_schemas import *
from .lms_schemas import *

# Define explicitly what should be exported when using 'from config import *'
__all__ = [
    # From canvas_schemas
    'CANVAS_NAMESPACES', 'IMS_CC_NAMESPACES', 'QTI_NAMESPACES', 
    'CANVAS_RESOURCE_TYPES', 'CANVAS_PATHS', 'MANIFEST_PATHS',
    
    # From lms_schemas
    'CANVAS_QUESTION_TYPE_MAP', 'CANVAS_STATUS_MAP', 
    'DEFAULT_QUIZ_SETTINGS', 'DEFAULT_ASSIGNMENT_SETTINGS'
]
