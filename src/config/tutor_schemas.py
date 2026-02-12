"""
Tutor LMS schema definitions.

This module contains WordPress post types, meta keys, and schema definitions
for Tutor LMS.
"""

# Tutor LMS post types
TUTOR_POST_TYPES = {
    'COURSE': 'courses',
    'LESSON': 'lesson',
    'QUIZ': 'tutor_quiz',
    'QUESTION': 'tutor_question',
    'ASSIGNMENT': 'tutor_assignments',
    'TOPIC': 'topics',  # Topics are stored as course meta, not posts
}

# Tutor LMS meta keys
TUTOR_META_KEYS = {
    # Course meta
    'COURSE_SETTINGS': '_tutor_course_settings',
    'COURSE_DURATION': '_tutor_course_duration',
    'COURSE_LEVEL': '_tutor_course_level',
    'COURSE_BENEFITS': '_tutor_course_benefits',
    'COURSE_REQUIREMENTS': '_tutor_course_requirements',
    'COURSE_TARGET_AUDIENCE': '_tutor_course_target_audience',
    'COURSE_MATERIAL_INCLUDES': '_tutor_course_material_includes',
    'MAXIMUM_STUDENTS': '_tutor_course_maximum_students',
    
    # Lesson meta
    'LESSON_VIDEO_SOURCE': '_tutor_lesson_video_source',
    'LESSON_VIDEO': '_video',
    'LESSON_ATTACHMENTS': '_tutor_attachments',
    
    # Quiz meta
    'QUIZ_OPTION': '_tutor_quiz_option',
    'QUIZ_QUESTIONS': '_tutor_quiz_questions',
    
    # Question meta
    'QUESTION_TYPE': 'tutor_question_type',
    'QUESTION_MARK': 'tutor_question_mark',
    'QUESTION_SETTINGS': 'tutor_question_settings',
    'QUESTION_ANSWERS': 'tutor_question_answers',
    'QUESTION_ANSWER_EXPLANATION': 'tutor_question_answer_explanation',
    
    # Assignment meta
    'ASSIGNMENT_OPTION': '_tutor_assignment_option',
}

# Tutor quiz settings structure
TUTOR_QUIZ_SETTINGS = {
    'time_limit': {
        'time_value': 0,
        'time_type': 'minutes',  # minutes, hours, days, weeks
    },
    'hide_quiz_time_display': False,
    'attempts_allowed': 10,
    'passing_grade': 80,
    'max_questions_for_answer': 10,
    'quiz_auto_start': False,
    'question_layout_view': 'single_question',  # single_question, question_pagination, question_below_each_other
    'questions_order': 'rand',  # rand, sorting, asc, desc
    'hide_question_number_overview': False,
    'short_answer_characters_limit': 200,
    'open_ended_answer_characters_limit': 500,
    'feedback_mode': 'default',  # default, reveal, retry
}

# Tutor assignment settings structure
TUTOR_ASSIGNMENT_SETTINGS = {
    'total_mark': 10,
    'pass_mark': 5,
    'upload_files_limit': 1,
    'upload_file_size_limit': 2,  # MB
    'time_duration': {
        'value': 0,
        'time': 'weeks',  # minutes, hours, days, weeks
    },
    'attachments': [],
}

# Tutor question types
TUTOR_QUESTION_TYPES = {
    'MULTIPLE_CHOICE': 'multiple_choice',
    'TRUE_FALSE': 'true_false',
    'FILL_IN_BLANK': 'fill_in_the_blank',
    'OPEN_ENDED': 'open_ended',
    'SHORT_ANSWER': 'short_answer',
    'MATCHING': 'matching',
    'IMAGE_MATCHING': 'image_matching',
    'IMAGE_ANSWERING': 'image_answering',
    'ORDERING': 'ordering',
}

# Canvas to Tutor question type mapping
QUESTION_TYPE_MAPPING = {
    'multiple_choice_question': 'multiple_choice',
    'true_false_question': 'true_false',
    'essay_question': 'open_ended',
    'short_answer_question': 'short_answer',
    'fill_in_multiple_blanks_question': 'fill_in_the_blank',
    'matching_question': 'matching',
    'numerical_question': 'short_answer',  # Fallback
    'calculated_question': 'open_ended',  # Fallback - requires manual review
    'multiple_answers_question': 'multiple_choice',  # Multiple correct answers
    'file_upload_question': 'open_ended',  # Fallback
    'text_only_question': None,  # Skip - not a question
    'multiple_dropdowns_question': 'multiple_choice',  # Fallback
    'formula_question': 'open_ended',  # Fallback - requires manual review
    'categorization_question': 'matching',  # Fallback
    'ordering_question': 'ordering',
}

# WordPress post status values
WP_POST_STATUS = {
    'PUBLISH': 'publish',
    'DRAFT': 'draft',
    'PENDING': 'pending',
    'PRIVATE': 'private',
    'TRASH': 'trash',
}

# Canvas to WordPress status mapping
CANVAS_TO_WP_STATUS = {
    'active': 'publish',
    'unpublished': 'draft',
    'deleted': 'trash',
}
