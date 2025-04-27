"""
Logic Formatter Module for TransferAI

This module is the core component responsible for processing articulation logic and
generating human-readable representations of course requirements. It handles:

1. Validating if selected courses satisfy articulation requirements
2. Rendering articulation logic as formatted text for display
3. Processing complex logic combinations (AND/OR) with nested hierarchies
4. Handling special cases like honors courses and no-articulation situations
5. Providing detailed explanations of articulation validation results

ADAPTER NOTICE: As part of the v1.5 refactoring, this module now implements the adapter
pattern to maintain backward compatibility while delegating to the new modular articulation
package. All functions maintain their original signatures to ensure no breaking changes.

DEPRECATED: This module is maintained for backward compatibility only.
New code should import directly from the articulation package instead:

    from articulation import is_articulation_satisfied
    from articulation.validators import validate_combo_against_group
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
    """
    Determine if selected CCC courses satisfy an articulation requirement.
    
    Performs a structured validation of the articulation logic against the provided
    courses, handling complex logic patterns (AND/OR), honors course equivalents,
    and providing detailed feedback on satisfied and missing requirements.
    
    Args:
        logic_block: Dictionary containing articulation logic structure.
        selected_courses: List of CCC course codes to validate.
        honors_pairs: Optional dictionary mapping honors courses to non-honors equivalents.
        
    Returns:
        A dictionary with the following keys:
        - is_satisfied: Boolean indicating if the requirements are fully satisfied.
        - explanation: Detailed explanation of validation results.
        - satisfied_options: List of satisfied articulation options.
        - missing_courses: Dictionary mapping options to their missing courses.
        - redundant_courses: List of redundant/unnecessary courses.
        - match_percentage: Overall match percentage across all options.
    """
    return art_is_articulation_satisfied(logic_block, selected_courses, honors_pairs)

def explain_if_satisfied(logic_block, selected_courses, selected_options=None, indent_level=0, honors_pairs=None, detect_all_redundant=False):
    """
    Check if selected CCC courses satisfy an articulation logic block and explain the result.
    
    Provides a detailed explanation of whether and how selected courses satisfy articulation
    requirements, including which paths are satisfied, which courses are missing, and whether
    redundant courses are present.
    
    Args:
        logic_block: The articulation logic structure to check against.
        selected_courses: List of CCC course codes selected by the student.
        selected_options: Optional list of pre-selected options to consider.
        indent_level: Current indentation level for formatting nested output.
        honors_pairs: Dictionary mapping honors courses to their non-honors equivalents.
        detect_all_redundant: If True, identify all redundant courses, not just the first found.
        
    Returns:
        A tuple containing:
        - Boolean indicating if requirements are satisfied
        - Formatted explanation string detailing the validation results
        - List of redundant courses (if any)
    """
    return art_explain_if_satisfied(logic_block, selected_courses, selected_options, indent_level, honors_pairs, detect_all_redundant)

# Rendering functions
def render_logic_str(metadata: Dict[str, Any]) -> str:
    """
    Render articulation logic block into human-readable text format.
    
    Converts complex nested logic structures into a clear, hierarchical representation
    with labeled options, AND/OR relationships, and honors course indicators.
    
    Args:
        metadata: Dictionary containing articulation data with a 'logic_block' key
                 and optional 'no_articulation' flag.
                 
    Returns:
        A formatted string representing the articulation options, with proper
        hierarchical structure, option labels, and honors course information.
        If no articulation exists, returns a message indicating the course
        must be completed at UCSD.
    """
    return art_render_logic_str(metadata)

def render_logic(metadata: Dict[str, Any]) -> str:
    """Backward-compatible alias for render_logic_str."""
    return art_render_logic_str(metadata)

def render_logic_v2(metadata):
    """
    Enhanced version of render_logic_str with more concise formatting.
    Groups options better and makes the UC course more prominent.
    Includes clear labeling for complete vs. partial options.
    """
    return art_render_logic_v2(metadata)

def render_group_summary(docs: List) -> str:
    """
    Render a group-level summary of UC-to-CCC course articulation across all sections.
    
    Creates a comprehensive, structured summary of all articulation options within a group,
    organized by sections and UC courses. The output includes clear instructions based on
    the group logic type and detailed articulation options for each UC course.
    
    Args:
        docs: List of articulation documents belonging to the same group.
        
    Returns:
        A formatted string with group information, instructions, and articulation options
        structured hierarchically by section and UC course.
    """
    return art_render_group_summary(docs)

def render_combo_validation(validations, satisfying_courses=None):
    """
    Visualizes validation results for multiple UC courses.
    
    Args:
        validations: Dictionary mapping UC course codes to validation result dicts
                    Each validation dict should have 'is_satisfied' and 'explanation' fields
        satisfying_courses: Optional dictionary mapping UC courses to lists of CCC courses
                           that satisfy them
    
    Returns:
        A formatted validation summary as a string
    """
    return art_render_combo_validation(validations, satisfying_courses)

def render_binary_response(is_satisfied, explanation, course=None):
    """
    Renders a standardized binary (yes/no) response with enhanced visual formatting.
    
    Creates a professional, visually distinctive response for binary questions
    (e.g., "Does X satisfy Y?") with consistent formatting, appropriate emoji
    indicators, and highlighting of key terms.
    
    Args:
        is_satisfied: Boolean indicating whether the requirement is satisfied.
        explanation: Explanation text to include after the header.
        course: Optional UC course code to include in the header.
        
    Returns:
        Formatted response string with standardized header and explanation.
    """
    return art_render_binary_response(is_satisfied, explanation, course)

# Formatting functions
def include_binary_explanation(response_text: str, satisfied: bool, validation_summary: str) -> str:
    """
    Prepends a binary summary to the LLM's full response.
    """
    return art_include_binary_explanation(response_text, satisfied, validation_summary)

def get_course_summary(metadata: dict) -> str:
    """
    Returns a short summary of UC course + equivalent CCC options.
    """
    return art_get_course_summary(metadata)

# Analysis functions
def extract_honors_info_from_logic(logic_block: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Extract honors and non-honors course information from a logic block.
    
    Traverses the nested structure of a logic block to separate honors and non-honors
    courses into separate lists for easier processing and presentation.
    
    Args:
        logic_block: A dictionary containing the articulation logic structure with
                   nested AND/OR blocks and course information.
        
    Returns:
        A dictionary with two keys:
        - 'honors_courses': A sorted list of honors course codes
        - 'non_honors_courses': A sorted list of non-honors course codes
    """
    return art_extract_honors_info_from_logic(logic_block)

def count_uc_matches(ccc_course, docs):
    """
    Counts and lists all UC courses satisfied by this CCC course.
    
    Identifies both direct matches (where the CCC course alone satisfies a UC course)
    and contribution matches (where the CCC course is part of a combination).
    
    Args:
        ccc_course: A CCC course code (e.g., "CIS 36A")
        docs: List of Document objects containing articulation logic
        
    Returns:
        Tuple of (count of direct matches, list of direct matches, list of contribution matches)
        Where contribution matches shows courses where this CCC is part of a combination
        but not counted as a direct match.
    """
    return art_count_uc_matches(ccc_course, docs)

def summarize_logic_blocks(logic_block):
    """
    Generates quick metadata summaries for articulation logic.
    
    Args:
        logic_block: A logic block dictionary structure
        
    Returns:
        Dictionary with metadata about the articulation logic:
        - option_count: Number of distinct articulation options
        - multi_course_options: Count of options requiring multiple CCC courses
        - honors_required: Whether only honors courses satisfy the requirement
        - has_honors_options: Whether any honors courses are present in options
        - min_courses_required: Minimum number of CCC courses needed
    """
    return art_summarize_logic_blocks(logic_block)

# Detector functions
def is_honors_required(logic_block):
    """
    Determines if only honors courses will satisfy an articulation requirement.
    
    Analyzes the articulation logic to check if only honors-designated courses
    are valid options, or if non-honors courses are also acceptable.
    
    Args:
        logic_block: The articulation logic structure to analyze.
        
    Returns:
        Boolean indicating if only honors courses will satisfy the requirement.
        Returns False if any non-honors option exists or if there is no articulation.
    """
    return art_is_honors_required(logic_block)

def detect_redundant_courses(selected_courses, logic_block):
    """
    Detects redundant courses (courses that satisfy the same requirement).
    
    Identifies courses in a student's selection that are redundant because they:
    1. Satisfy the same articulation path options
    2. Are honors/non-honors variants of the same course (e.g., MATH 1A vs MATH 1AH)
    
    Args:
        selected_courses: List of CCC course codes selected by the student.
        logic_block: The articulation logic structure to check against.
        
    Returns:
        A list of lists, where each inner list represents a group of redundant courses.
        For example, if MATH 1A and MATH 1AH are redundant, they would be grouped together.
    """
    return art_detect_redundant_courses(selected_courses, logic_block)

def is_honors_pair_equivalent(or_block, course1, course2):
    """
    Check if two courses form an honors/non-honors pair in the logic block.
    
    Determines if two courses represent the honors and non-honors variants of the
    same course, where they are offered as separate options in the articulation logic.
    
    Args:
        or_block: The articulation logic block (usually type "OR") to check.
        course1: First course code to check.
        course2: Second course code to check.
        
    Returns:
        Boolean indicating if the courses are honors/non-honors variants of the same course.
    """
    return art_is_honors_pair_equivalent(or_block, course1, course2)

def explain_honors_equivalence(course1, course2):
    """
    Generate an explanation of the honors equivalence between two courses.
    
    Creates a formatted explanation string about how honors and non-honors
    variants of the same course are equivalent for articulation purposes.
    
    Args:
        course1: First course code (either honors or non-honors).
        course2: Second course code (opposite honors status of course1).
        
    Returns:
        A formatted string explaining the honors equivalence relationship.
    """
    return art_explain_honors_equivalence(course1, course2)

def validate_logic_block(course_code: str, logic_block: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    Validate a course against articulation logic requirements.
    
    Recursively traverses the logic block structure to determine if the given 
    course code satisfies any of the articulation requirements. The function 
    handles different logic structures (AND/OR), honors designations, and 
    maintains lists of matched and unmatched requirements.
    
    Args:
        course_code: The course code to validate against the articulation requirements.
        logic_block: A dictionary representing the nested logic structure of articulation
                     requirements, containing 'type' keys with values 'AND' or 'OR', and
                     'courses' lists of sub-requirements.
    
    Returns:
        A tuple containing:
        - Boolean indicating whether the course satisfied the requirements
        - List of matched courses/requirements
        - List of unmatched courses/requirements that were needed
    """
    return art_validate_logic_block(course_code, logic_block)

# Group validation functions
def validate_combo_against_group(ccc_courses, group_data):
    """
    Validate a combination of CCC courses against a group's articulation requirements.
    
    Checks if the provided CCC courses satisfy the requirements for a particular group,
    taking into account group logic type (e.g., select_n_courses, choose_one_section)
    and handling multi-section groups appropriately.
    
    Args:
        ccc_courses: List of CCC course codes to validate.
        group_data: Dictionary containing group articulation data with sections and UC courses.
        
    Returns:
        A dictionary with validation results including:
        - is_fully_satisfied: Boolean indicating if group requirements are fully met.
        - partially_satisfied: Boolean indicating if requirements are partially met.
        - satisfied_uc_courses: List of UC courses satisfied by the provided CCC courses.
        - required_count: Number of courses required (for select_n_courses).
        - satisfied_count: Number of courses satisfied.
        - satisfied_section_id: Section ID that is satisfied (for choose_one_section).
        - validation_by_section: Detailed validation results for each section.
    """
    return art_validate_combo_against_group(ccc_courses, group_data)

def validate_uc_courses_against_group_sections(user_uc_courses, group_data):
    """
    Given a list of UC course names and a group_data object (from ASSIST),
    validate whether all UC courses are satisfied together under one section.

    Returns a dictionary summarizing:
    - is_fully_satisfied: bool
    - satisfied_section_id: section where match was found
    - missing_uc_courses: list
    - matched_ccc_courses: dict mapping UC course → CCC match list
    """
    return art_validate_uc_courses_against_group_sections(user_uc_courses, group_data)

# Course finder functions
def find_uc_courses_satisfied_by(ccc_course: str, all_docs: List[Document]) -> List[Document]:
    """
    Reverse-match: Find all UC courses whose logic includes the given CCC course.
    Searches deeply inside all nested logic blocks.
    """
    from articulation.analyzers import find_uc_courses_satisfied_by as art_find_uc_courses_satisfied_by
    return art_find_uc_courses_satisfied_by(ccc_course, all_docs)

def get_uc_courses_satisfied_by_ccc(ccc_course, all_docs):
    """
    Find UC courses that can be directly satisfied by a single CCC course.
    
    Identifies UC courses where the specified CCC course alone can satisfy the
    articulation requirement without needing additional courses.
    
    Args:
        ccc_course: The CCC course code to check (e.g., "CIS 22A").
        all_docs: List of articulation documents to search through.
        
    Returns:
        A sorted list of UC course codes that can be satisfied by the given CCC course.
    """
    return art_get_uc_courses_satisfied_by_ccc(ccc_course, all_docs)

def get_uc_courses_requiring_ccc_combo(ccc_course, all_docs):
    """
    Find UC courses where the given CCC course is part of a multi-course combination.
    
    Identifies UC courses where the specified CCC course contributes to satisfying
    the articulation requirement but must be combined with additional courses.
    
    Args:
        ccc_course: The CCC course code to check (e.g., "CIS 22A").
        all_docs: List of articulation documents to search through.
        
    Returns:
        A sorted list of UC course codes where the given CCC course is part of a 
        multi-course combination requirement.
    """
    return art_get_uc_courses_requiring_ccc_combo(ccc_course, all_docs)