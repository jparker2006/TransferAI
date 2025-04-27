"""
TransferAI Legacy Compatibility Module

This module provides backward compatibility with the original monolithic 
logic_formatter.py by importing and re-exporting all functions from the new
modular articulation package.

DEPRECATED: This module is maintained for backward compatibility only.
New code should import directly from the articulation package instead:

    from articulation import is_articulation_satisfied
    from articulation.validators import validate_combo_against_group
    
This is part of the v1.5 refactoring to improve maintainability and testability.

The original functions all maintain their exact signatures to ensure no breaking
changes when upgrading existing code. As the refactoring is completed, this file
will replace the original logic_formatter.py.
"""

import warnings
from typing import List, Dict, Tuple, Union, Any, Optional, Set
from llama_index_client import Document  # Required for some function signatures

# Import from new modules with aliases to avoid circular references
from articulation.validators import (
    is_articulation_satisfied as art_is_articulation_satisfied,
    explain_if_satisfied as art_explain_if_satisfied,
    validate_combo_against_group as art_validate_combo_against_group,
    validate_uc_courses_against_group_sections as art_validate_uc_courses_against_group_sections,
)

from articulation.detectors import (
    validate_logic_block as art_validate_logic_block,
)

from articulation.renderers import (
    render_logic_str as art_render_logic_str,
    render_logic_v2 as art_render_logic_v2,
    render_group_summary as art_render_group_summary,
    render_combo_validation as art_render_combo_validation,
)

from articulation.formatters import (
    render_binary_response as art_render_binary_response,
    include_binary_explanation as art_include_binary_explanation,
    get_course_summary as art_get_course_summary,
)

from articulation.analyzers import (
    extract_honors_info_from_logic as art_extract_honors_info_from_logic,
    count_uc_matches as art_count_uc_matches,
    summarize_logic_blocks as art_summarize_logic_blocks,
    get_uc_courses_satisfied_by_ccc as art_get_uc_courses_satisfied_by_ccc,
    get_uc_courses_requiring_ccc_combo as art_get_uc_courses_requiring_ccc_combo,
)

from articulation.detectors import (
    is_honors_required as art_is_honors_required,
    detect_redundant_courses as art_detect_redundant_courses,
    is_honors_pair_equivalent as art_is_honors_pair_equivalent,
    explain_honors_equivalence as art_explain_honors_equivalence,
)

# Emit deprecation warning on import
warnings.warn(
    "logic_formatter.py is deprecated. Use the articulation package instead.", 
    DeprecationWarning,
    stacklevel=2
)

# Re-export functions with original signatures

# Core validation functions
def is_articulation_satisfied(logic_block, selected_courses, honors_pairs=None):
    """Determine if selected courses satisfy an articulation requirement."""
    return art_is_articulation_satisfied(logic_block, selected_courses, honors_pairs)

def explain_if_satisfied(logic_block, selected_courses, selected_options=None, indent_level=0, honors_pairs=None, detect_all_redundant=False):
    """Check if selected courses satisfy an articulation logic block and explain the result."""
    return art_explain_if_satisfied(logic_block, selected_courses, selected_options, indent_level, honors_pairs, detect_all_redundant)

# Rendering functions
def render_logic_str(metadata: Dict[str, Any]) -> str:
    """Render articulation logic block into human-readable text format."""
    return art_render_logic_str(metadata)

def render_logic(metadata: Dict[str, Any]) -> str:
    """Backward-compatible alias for render_logic_str."""
    return art_render_logic_str(metadata)

def render_logic_v2(metadata):
    """Enhanced version of render_logic_str with more concise formatting."""
    return art_render_logic_v2(metadata)

def render_group_summary(docs: List) -> str:
    """Render a group-level summary of UC-to-CCC course articulation across all sections."""
    return art_render_group_summary(docs)

def render_combo_validation(validations, satisfying_courses=None):
    """Visualizes validation results for multiple UC courses."""
    return art_render_combo_validation(validations, satisfying_courses)

def render_binary_response(is_satisfied, explanation, course=None):
    """Renders a standardized binary (yes/no) response with enhanced visual formatting."""
    return art_render_binary_response(is_satisfied, explanation, course)

# Formatting functions
def include_binary_explanation(response_text: str, satisfied: bool, validation_summary: str) -> str:
    """Prepends a binary summary to the LLM's full response."""
    return art_include_binary_explanation(response_text, satisfied, validation_summary)

def get_course_summary(metadata: dict) -> str:
    """Returns a short summary of UC course + equivalent CCC options."""
    return art_get_course_summary(metadata)

# Analysis functions
def extract_honors_info_from_logic(logic_block: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extract honors and non-honors course information from a logic block."""
    return art_extract_honors_info_from_logic(logic_block)

def count_uc_matches(ccc_course, docs):
    """Counts and lists all UC courses satisfied by this CCC course."""
    return art_count_uc_matches(ccc_course, docs)

def summarize_logic_blocks(logic_block):
    """Generates quick metadata summaries for articulation logic."""
    return art_summarize_logic_blocks(logic_block)

# Detector functions
def is_honors_required(logic_block):
    """Determines if only honors courses will satisfy an articulation requirement."""
    return art_is_honors_required(logic_block)

def detect_redundant_courses(selected_courses, logic_block):
    """Detects redundant courses (courses that satisfy the same requirement)."""
    return art_detect_redundant_courses(selected_courses, logic_block)

def is_honors_pair_equivalent(or_block, course1, course2):
    """Check if two courses form an honors/non-honors pair in the logic block."""
    return art_is_honors_pair_equivalent(or_block, course1, course2)

def explain_honors_equivalence(course1, course2):
    """Generate an explanation of the honors equivalence between two courses."""
    return art_explain_honors_equivalence(course1, course2)

def validate_logic_block(course_code: str, logic_block: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """Validate a course against articulation logic requirements."""
    return art_validate_logic_block(course_code, logic_block)

# Group validation functions
def validate_combo_against_group(ccc_courses, group_data):
    """Validate a combination of CCC courses against a group's articulation requirements."""
    return art_validate_combo_against_group(ccc_courses, group_data)

def validate_uc_courses_against_group_sections(user_uc_courses, group_data):
    """Validate whether all UC courses are satisfied together under one section."""
    return art_validate_uc_courses_against_group_sections(user_uc_courses, group_data)

# Course finder functions
def find_uc_courses_satisfied_by(ccc_course: str, all_docs: List[Document]) -> List[Document]:
    """Find all UC courses whose logic includes the given CCC course."""
    # This function may need custom implementation if it's not fully migrated
    from articulation.analyzers import find_uc_courses_satisfied_by as art_find_uc_courses_satisfied_by
    return art_find_uc_courses_satisfied_by(ccc_course, all_docs)

def get_uc_courses_satisfied_by_ccc(ccc_course, all_docs):
    """Find UC courses that can be directly satisfied by a single CCC course."""
    return art_get_uc_courses_satisfied_by_ccc(ccc_course, all_docs)

def get_uc_courses_requiring_ccc_combo(ccc_course, all_docs):
    """Find UC courses where the given CCC course is part of a multi-course combination."""
    return art_get_uc_courses_requiring_ccc_combo(ccc_course, all_docs) 