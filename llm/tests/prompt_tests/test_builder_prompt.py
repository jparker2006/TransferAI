"""
Prompt Builder Module for TransferAI

This module is responsible for constructing prompts for the LLM based on articulation data.
It provides functions to create tailored prompts for different query types:

1. Course-specific articulation queries
2. Group-level articulation queries

The module ensures that prompts maintain a consistent professional tone, include all
necessary context, and provide clear instructions to the LLM about how to format responses.
"""

from enum import Enum
from typing import Optional, Union, Dict, List, Any
import re
import sys
import os
import random
import yaml
# import langchain
from pydantic import BaseModel
from collections import defaultdict

# Add the parent directory to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.document_loader import get_course_title, get_course_description


class PromptType(Enum):
    """
    Enumeration of prompt types supported by the prompt builder.
    
    COURSE_EQUIVALENCY: For queries about specific UC courses and their equivalents
    GROUP_LOGIC: For queries about groups of courses and their requirements
    """
    COURSE_EQUIVALENCY = "course_equivalency"
    GROUP_LOGIC = "group_logic"


class VerbosityLevel(Enum):
    """
    Enumeration of verbosity levels for prompts.
    
    MINIMAL: Brief, concise responses with minimal explanations
    STANDARD: Balanced level of detail (default)
    DETAILED: Comprehensive responses with detailed explanations
    """
    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"


def _extract_course_codes(rendered_logic: str) -> List[str]:
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


def _enrich_with_descriptions(rendered_logic: str) -> str:
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
    course_codes = _extract_course_codes(rendered_logic)
    
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


def build_course_prompt(
    rendered_logic: str,
    user_question: str,
    uc_course: str = "Unknown",
    uc_course_title: str = "",
    group_id: str = "",
    group_title: str = "",
    group_logic_type: str = "",
    section_title: str = "",
    n_courses: Optional[int] = None,
    is_no_articulation: bool = False,
    verbosity: VerbosityLevel = VerbosityLevel.STANDARD,
) -> str:
    """
    Build a prompt for answering single-course articulation queries.
    
    Creates a structured prompt that includes the user's question, course information,
    and articulation logic in a format optimized for the LLM to produce a clear,
    counselor-like response.
    
    Args:
        rendered_logic: String representation of the articulation logic.
        user_question: The original user query.
        uc_course: UC course code (e.g., "CSE 8A").
        uc_course_title: Title of the UC course.
        group_id: Group identifier if applicable.
        group_title: Group title if applicable.
        group_logic_type: Type of logic for the group.
        section_title: Section title if applicable.
        n_courses: Number of courses required (for select_n_courses type).
        is_no_articulation: Flag indicating if the course has no articulation.
        verbosity: Controls the level of detail in the response.
        
    Returns:
        A formatted prompt string for the LLM.
        
    Note:
        Group-level phrasing is excluded per design requirement R3.
    """
    # Enrich the rendered logic with accurate course descriptions
    enriched_logic = _enrich_with_descriptions(rendered_logic)

    if is_no_articulation or "❌ This course must be completed at UCSD." in rendered_logic:
        return f"""
You are TransferAI, a trusted UC transfer counselor. Use **only** the verified articulation summary below.

📨 **Student Question:**  
{user_question.strip()}

🎓 **UC Course:** {uc_course} – {uc_course_title}  

> This course must be completed at UC San Diego.

Follow official policy only. Do not recommend alternatives.
""".strip()

    # Base prompt with essential information
    base_prompt = f"""
You are TransferAI, a trusted UC transfer counselor. Use **only** the verified articulation data below.

📨 **Student Question:**  
{user_question.strip()}

🎓 **UC Course:** {uc_course} – {uc_course_title}  

{enriched_logic.strip()}
""".strip()

    # Add instructions based on verbosity level
    if verbosity == VerbosityLevel.MINIMAL:
        # Minimal instructions for concise responses
        instructions = """
Be concise. Present only essential information in a clear, direct manner.
Do not add explanations beyond what's necessary to understand the options.
"""
    elif verbosity == VerbosityLevel.STANDARD:
        # Standard instructions for balanced responses
        instructions = """
✅ **Response Guidelines:**
- Present articulation options clearly and directly
- Show all options exactly as they appear in the data
- Do not simplify or interpret the articulation paths
"""
    else:  # DETAILED
        # Detailed instructions (similar to original but still reduced)
        instructions = """
✅ **How to Respond (Strict Output Rules):**

To satisfy this UC course requirement, you must complete one of the following De Anza course options.

⚠️ Do not remove, collapse, reorder, or reword any part of the articulation summary.  
⚠️ Always show all options, even if they are long or redundant.  
⚠️ Do not suggest, simplify, or interpret the articulation paths.

🎓 **Counselor Voice Requirements:**
- Clear and confident
- Grounded in verified articulation logic
"""

    return f"{base_prompt}\n\n{instructions.strip()}"


def build_group_prompt(
    rendered_logic: str,
    user_question: str,
    group_id: str = "Unknown",
    group_title: str = "",
    group_logic_type: str = "",
    n_courses: Optional[int] = None,
    verbosity: VerbosityLevel = VerbosityLevel.STANDARD,
) -> str:
    """
    Build a prompt for answering group-level articulation queries.
    
    Creates a structured prompt for queries about groups of courses, including specific
    instructions based on the group logic type (choose_one_section, all_required, 
    or select_n_courses).
    
    Args:
        rendered_logic: String representation of the group articulation logic.
        user_question: The original user query.
        group_id: Group identifier (e.g., "1", "2").
        group_title: Title of the group.
        group_logic_type: Type of logic for the group (e.g., "choose_one_section").
        n_courses: Number of courses required (for select_n_courses type).
        verbosity: Controls the level of detail in the response.
        
    Returns:
        A formatted prompt string for the LLM.
        
    Note:
        The prompt includes specific instructions based on the group logic type to
        ensure the LLM understands how to interpret and explain the requirements.
    """
    # Enrich the rendered logic with accurate course descriptions
    enriched_logic = _enrich_with_descriptions(rendered_logic)

    group_label = f"Group {group_id}" if group_id else "this group"
    logic_type = group_logic_type or "unspecified"

    # Create appropriate logic hint based on group logic type
    if group_logic_type == "choose_one_section":
        logic_hint = f"To satisfy {group_label}, complete all UC courses in exactly ONE section (A or B). Each course must be satisfied individually."
    elif group_logic_type == "all_required":
        logic_hint = f"To satisfy {group_label}, complete every UC course listed. Each course may have multiple options."
    elif group_logic_type == "select_n_courses" and n_courses:
        logic_hint = f"To satisfy {group_label}, complete exactly {n_courses} UC course(s) from the list."
    else:
        logic_hint = f"Refer to the articulation summary for {group_label} and follow it exactly."
    
    # Build the logic explanation
    if logic_type == "all_required":
        group_logic_explanation = "every UC course listed below individually"
    elif logic_type == "choose_one_section":
        group_logic_explanation = "all UC courses from either Section A or Section B, but not both"
    elif logic_type == "select_n_courses":
        group_logic_explanation = f"exactly {n_courses} full UC course(s) from the list below"
    else:
        group_logic_explanation = "the requirements listed in the articulation summary"

    # Base prompt with essential information
    base_prompt = f"""
You are TransferAI, a trusted UC transfer counselor. Use **only** the verified articulation data below.

📨 **Student Question:**  
{user_question.strip()}

📘 **{group_label}{': ' + group_title if group_title else ''}**  
🔎 **Group Logic Type:** {logic_type}

To satisfy {group_label}, you must complete {group_logic_explanation}.

{enriched_logic.strip()}
""".strip()

    # Add instructions based on verbosity level
    if verbosity == VerbosityLevel.MINIMAL:
        # Minimal instructions for concise responses
        instructions = f"""
{logic_hint}
Present only essential information clearly and directly.
Do not fabricate course options or add unnecessary explanations.
"""
    elif verbosity == VerbosityLevel.STANDARD:
        # Standard instructions for balanced responses
        instructions = f"""
{logic_hint}

✅ **Response Guidelines:**
- Present articulation options clearly and directly
- Do not modify, condense, or reinterpret the summary
- Include all courses as listed in the articulation data
- Never invent or fabricate course options
"""
    else:  # DETAILED
        # Detailed instructions (similar to original but reduced)
        instructions = f"""
{logic_hint}

✅ **Response Guidelines:**

1️⃣ State the requirement: To satisfy {group_label}, you must complete {group_logic_explanation}.

2️⃣ Present the articulation summary exactly as-is.

3️⃣ CRITICAL: DO NOT FABRICATE COURSE OPTIONS
- Never invent course options that aren't in the data
- Only present the exact options from the verified articulation data
- Always use the exact course titles provided in the summary

4️⃣ Do not recommend, simplify, or collapse any articulation logic
"""

    return f"{base_prompt}\n\n{instructions.strip()}"


def build_prompt(
    logic: str,
    user_question: str,
    uc_course: str = "Unknown",
    prompt_type: PromptType = PromptType.COURSE_EQUIVALENCY,
    uc_course_title: str = "",
    group_id: str = "",
    group_title: str = "",
    group_logic_type: str = "",
    section_title: str = "",
    n_courses: Optional[int] = None,
    rendered_logic: str = "",
    verbosity: VerbosityLevel = VerbosityLevel.STANDARD,
) -> str:
    """
    Main entry point for building prompts based on query type.
    
    This function routes to the appropriate prompt builder based on the prompt_type
    and forwards all relevant parameters.
    
    Args:
        logic: String representation of the articulation logic.
        user_question: The original user query.
        uc_course: UC course code.
        prompt_type: Type of prompt to build (COURSE_EQUIVALENCY or GROUP_LOGIC).
        uc_course_title: Title of the UC course.
        group_id: Group identifier if applicable.
        group_title: Group title if applicable.
        group_logic_type: Type of logic for the group.
        section_title: Section title if applicable.
        n_courses: Number of courses required (for select_n_courses type).
        rendered_logic: Alternative rendered logic string (used for group prompts).
        verbosity: Controls the level of detail in the response (MINIMAL, STANDARD, DETAILED).
        
    Returns:
        A formatted prompt string for the LLM.
        
    Example:
        >>> prompt = build_prompt(
        ...     logic="* Option A: CIS 22A",
        ...     user_question="What satisfies CSE 8A?",
        ...     uc_course="CSE 8A",
        ...     prompt_type=PromptType.COURSE_EQUIVALENCY,
        ...     verbosity=VerbosityLevel.MINIMAL
        ... )
    """
    if prompt_type == PromptType.GROUP_LOGIC:
        return build_group_prompt(
            rendered_logic=rendered_logic,
            user_question=user_question,
            group_id=group_id,
            group_title=group_title,
            group_logic_type=group_logic_type,
            n_courses=n_courses,
            verbosity=verbosity
        )
    else:
        return build_course_prompt(
            rendered_logic=logic,
            user_question=user_question,
            uc_course=uc_course,
            uc_course_title=uc_course_title,
            group_id=group_id,
            group_title=group_title,
            group_logic_type=group_logic_type,
            section_title=section_title,
            n_courses=n_courses,
            verbosity=verbosity
        )