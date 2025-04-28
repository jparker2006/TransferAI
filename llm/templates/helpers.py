"""
Template Helper Functions for TransferAI

This module contains utility functions to support template rendering, including:
- Course code extraction and enrichment
- Template context preparation
- String formatting utilities
"""

import re
from typing import List, Dict, Any, Optional

# We need to import the course title and description functions from document_loader
# This is why we'll keep the imports relative to avoid circular imports
from ..document_loader import get_course_title, get_course_description


def extract_course_codes(rendered_logic: str) -> List[str]:
    """
    Extract course codes from rendered logic text.
    
    This helper function identifies all course codes in the rendered articulation
    logic to allow for enrichment with accurate course descriptions.
    
    Args:
        rendered_logic: The rendered articulation logic text
        
    Returns:
        A list of unique course codes found in the text
    """
    # Create a pattern that properly handles different course code formats
    # including honors courses with 'H' suffix
    
    # First pass: find all potential course codes with departments and course numbers
    base_pattern = r'([A-Z]{2,4})[\s-]+([0-9]{1,3}[A-Z]{0,2}(?:H)?)'
    matches = re.findall(base_pattern, rendered_logic)
    
    # Process matches to format properly and handle special cases
    course_codes = []
    for dept, num in matches:
        # Format the course code consistently
        code = f"{dept} {num}"
        
        # Check if this is a real course by looking up the title
        # This helps filter out false positives
        if get_course_title(code):
            course_codes.append(code)
    
    # Remove duplicates and return
    return list(set(course_codes))


def enrich_with_descriptions(rendered_logic: str) -> str:
    """
    Enrich rendered logic with accurate course descriptions.
    
    This function identifies course codes in the rendered logic and adds
    accurate titles from the articulation data source.
    
    Args:
        rendered_logic: The original rendered articulation logic
        
    Returns:
        Enriched logic with accurate course descriptions
    """
    # Extract course codes using our improved extractor
    course_codes = extract_course_codes(rendered_logic)
    
    # Create a list of lines to process individually
    lines = rendered_logic.split('\n')
    enriched_lines = []
    
    for line in lines:
        # Process each line separately for better control
        enriched_line = line
        
        # Sort codes by length (longest first) to avoid partial matches
        # (e.g., avoid matching "CIS 26B" in "CIS 26BH")
        for code in sorted(course_codes, key=len, reverse=True):
            # Skip if code is not in this line
            if code not in enriched_line:
                continue
                
            # Get the course title
            title = get_course_title(code)
            if not title:
                continue
                
            # Check if code is already enriched with description
            if f"{code} ({title})" in enriched_line:
                continue
                
            # Handle different cases based on the course code
            
            # Case 1: Honors course with (Honors) suffix
            if code.endswith('H') and f"{code} (Honors)" in enriched_line:
                # Replace without adding duplicate description
                # We'll keep the (Honors) notation as is
                continue
                
            # Case 2: Regular course or honors course without suffix
            # Use word boundaries to ensure we're only replacing the full course code
            pattern = rf'\b{re.escape(code)}\b(?!\s*\()'
            replacement = f"{code} ({title})"
            enriched_line = re.sub(pattern, replacement, enriched_line)
        
        enriched_lines.append(enriched_line)
    
    return '\n'.join(enriched_lines)


def prepare_course_context(
    rendered_logic: str,
    user_question: str,
    uc_course: str = "Unknown",
    uc_course_title: str = "",
    is_no_articulation: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Prepare context for course template rendering.
    
    Args:
        rendered_logic: The rendered articulation logic text
        user_question: The user's question
        uc_course: The UC course code
        uc_course_title: The UC course title
        is_no_articulation: Whether the course has no articulation
        **kwargs: Additional context variables
        
    Returns:
        A dictionary with prepared context variables
    """
    # Create context with required fields
    context = {
        "user_question": user_question.strip(),
        "uc_course": uc_course,
        "uc_course_title": uc_course_title,
        "enriched_logic": enrich_with_descriptions(rendered_logic)
    }
    
    # Add any additional context variables
    context.update(kwargs)
    
    return context


def prepare_group_context(
    rendered_logic: str,
    user_question: str,
    group_id: str = "Unknown",
    group_title: str = "",
    group_logic_type: str = "",
    n_courses: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Prepare context for group template rendering.
    
    Args:
        rendered_logic: The rendered articulation logic text
        user_question: The user's question
        group_id: The group ID
        group_title: The group title
        group_logic_type: The group logic type
        n_courses: The number of courses required (for select_n_courses)
        **kwargs: Additional context variables
        
    Returns:
        A dictionary with prepared context variables
    """
    from .group_templates import LOGIC_TYPE_EXPLANATIONS
    
    # Format group label
    group_label = f"Group {group_id}" if group_id else "this group"
    
    # Format group title string
    group_title_str = f": {group_title}" if group_title else ""
    
    # Get logic type explanation
    logic_type = group_logic_type or "default"
    if logic_type == "select_n_courses" and n_courses is not None:
        logic_explanation = LOGIC_TYPE_EXPLANATIONS.get(logic_type).format(n_courses=n_courses)
    else:
        logic_explanation = LOGIC_TYPE_EXPLANATIONS.get(logic_type, LOGIC_TYPE_EXPLANATIONS["default"])
    
    # Format logic hint
    logic_hint = f"To satisfy {group_label}, you must complete {logic_explanation}."
    
    # Create context with required fields
    context = {
        "user_question": user_question.strip(),
        "group_id": group_id,
        "group_title_str": group_title_str,
        "group_label": group_label,
        "logic_type": logic_type,
        "logic_hint": logic_hint,
        "enriched_logic": enrich_with_descriptions(rendered_logic)
    }
    
    # Add any additional context variables
    context.update(kwargs)
    
    return context
