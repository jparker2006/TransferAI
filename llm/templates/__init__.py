"""
TransferAI Templates Module

This module contains prompt templates and helper functions for template rendering.
"""

# Import key helper functions
from .helpers import (
    extract_course_codes,
    enrich_with_descriptions,
    prepare_course_context,
    prepare_group_context
)

# Import templates
from .course_templates import (
    COURSE_TEMPLATES,
    NO_ARTICULATION_TEMPLATES
)

from .group_templates import (
    GROUP_TEMPLATES,
    LOGIC_TYPE_EXPLANATIONS
)

__all__ = [
    # Helper functions
    'extract_course_codes',
    'enrich_with_descriptions',
    'prepare_course_context',
    'prepare_group_context',
    # Templates
    'COURSE_TEMPLATES',
    'NO_ARTICULATION_TEMPLATES',
    'GROUP_TEMPLATES',
    'LOGIC_TYPE_EXPLANATIONS'
]
