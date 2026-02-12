"""
Canvas LMS XML schema definitions and namespaces.

This module contains all XML namespaces, element paths, and schema definitions
used in Canvas IMS-CC exports.
"""

# IMS Common Cartridge Namespaces
IMS_CC_NAMESPACES = {
    'imscc': 'http://www.imsglobal.org/xsd/imsccv1p1/imscp_v1p1',
    'imsmd': 'http://ltsc.ieee.org/xsd/imsccv1p1/LOM/manifest',
    'imsqti': 'http://www.imsglobal.org/xsd/imsqti_v2p1',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}

# Canvas-specific namespaces
CANVAS_NAMESPACES = {
    **IMS_CC_NAMESPACES,
    'canvas': 'http://canvas.instructure.com/xsd/cccv1p0',
}

# QTI (Question & Test Interoperability) namespaces
QTI_NAMESPACES = {
    'qti': 'http://www.imsglobal.org/xsd/imsqti_v2p1',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}

# Canvas resource types
CANVAS_RESOURCE_TYPES = {
    'WEBCONTENT': 'webcontent',
    'ASSIGNMENT': 'assignment',
    'ASSESSMENT': 'imsqti_xmlv1p2/imscc_xmlv1p1/assessment',
    'QUESTION_BANK': 'imsqti_xmlv1p2/imscc_xmlv1p1/question-bank',
    'DISCUSSION': 'imsdt_xmlv1p1',
    'WEB_LINK': 'imswl_xmlv1p1',
}

# Canvas file paths
CANVAS_PATHS = {
    'MANIFEST': 'imsmanifest.xml',
    'COURSE_SETTINGS': 'course_settings/course_settings.xml',
    'MODULE_META': 'course_settings/module_meta.xml',
    'ASSIGNMENT_SETTINGS': 'assignment_settings.xml',
    'WIKI_CONTENT': 'wiki_content',
    'WEB_RESOURCES': 'web_resources',
    'NON_CC_ASSESSMENTS': 'non_cc_assessments',
}

# Canvas XML element paths (XPath)
MANIFEST_PATHS = {
    'ORGANIZATION': './/imscc:organization',
    'ITEM': './/imscc:item',
    'RESOURCE': './/imscc:resource',
    'FILE': './/imscc:file',
    'METADATA': './/imsmd:lom',
    'TITLE': './/imscc:title',
}

# Assignment XML structure
ASSIGNMENT_PATHS = {
    'TITLE': './/title',
    'DESCRIPTION': './/description',
    'POINTS_POSSIBLE': './/points_possible',
    'GRADING_TYPE': './/grading_type',
    'SUBMISSION_TYPES': './/submission_types',
    'DUE_AT': './/due_at',
    'WORKFLOW_STATE': './/workflow_state',
}

# Quiz/Assessment XML structure
ASSESSMENT_PATHS = {
    'TITLE': './/qti:assessment/qti:title',
    'DESCRIPTION': './/qti:assessment/qti:rubric',
    'ITEM': './/qti:item',
    'TIME_LIMIT': './/qti:duration',
    'ALLOWED_ATTEMPTS': './/qti:maxattempts',
}

# Question XML structure
QUESTION_PATHS = {
    'ITEM_BODY': './/qti:itemBody',
    'RESPONSE_DECLARATION': './/qti:responseDeclaration',
    'OUTCOME_DECLARATION': './/qti:outcomeDeclaration',
    'RESPONSE_PROCESSING': './/qti:responseProcessing',
    'FEEDBACK': './/qti:modalFeedback',
}

# Canvas question type identifiers
CANVAS_QUESTION_TYPES = {
    'choice': 'multiple_choice_question',
    'true_false': 'true_false_question',
    'essay': 'essay_question',
    'short_answer': 'short_answer_question',
    'fill_in_blank': 'fill_in_multiple_blanks_question',
    'matching': 'matching_question',
    'numerical': 'numerical_question',
    'calculated': 'calculated_question',
    'multiple_answers': 'multiple_answers_question',
    'file_upload': 'file_upload_question',
    'text_only': 'text_only_question',
}

# Required files for valid IMS-CC structure
REQUIRED_IMSCC_FILES = [
    'imsmanifest.xml',
]

# System XML files (not content)
SYSTEM_XML_FILES = {
    'imsmanifest.xml',
    'course_settings.xml',
    'module_meta.xml',
    'assignment_settings.xml',
    'syllabus.html',
}
