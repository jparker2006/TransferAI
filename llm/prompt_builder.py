"""
Prompt Builder Module for TransferAI

This module is responsible for constructing prompts for the LLM based on articulation data.
It provides functions to create tailored prompts for different query types:

1. Course-specific articulation queries
2. Group-level articulation queries

The module ensures that prompts maintain a consistent professional tone, include all
necessary context, and provide clear instructions to the LLM about how to format responses.

DEPRECATED: This module is being replaced by the new llm.services.prompt_service module.
Use that module instead for new code.
"""

import warnings

# Display a deprecation warning
warnings.warn(
    "The prompt_builder module is deprecated and will be removed in future versions. "
    "Use llm.services.prompt_service instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import the replacement implementation for backward compatibility
from llm.services.prompt_service import build_prompt, PromptType, VerbosityLevel, PromptService

# Keep the original implementation for backward compatibility
from enum import Enum, auto
from typing import Optional, Union, Dict, List, Any
import re
import sys
import os
import random
import yaml
# import langchain
from pydantic import BaseModel
from collections import defaultdict
import logging
from textwrap import dedent
from pathlib import Path

# Add the parent directory to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.document_loader import get_course_title, get_course_description

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    Enumeration of verbosity levels for controlling response length and detail.
    
    MINIMAL: Brief, direct responses with minimal explanation
    STANDARD: Balanced responses with moderate explanation
    DETAILED: Thorough responses with extensive explanation
    """
    MINIMAL = auto()
    STANDARD = auto()
    DETAILED = auto()


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
        verbosity: The desired level of detail in responses.
        
    Returns:
        A formatted prompt string for the LLM.
        
    Note:
        Group-level phrasing is excluded per design requirement R3.
    """
    # Enrich the rendered logic with accurate course descriptions
    enriched_logic = _enrich_with_descriptions(rendered_logic)

    if is_no_articulation or "❌ This course must be completed at UCSD." in rendered_logic:
        # Simplified prompt for no articulation case
        if verbosity == VerbosityLevel.MINIMAL:
            return f"""
TransferAI advisor data:
Question: {user_question.strip()}
UC Course: {uc_course} – {uc_course_title}  
> This course must be completed at UC San Diego.
Be extremely brief.
""".strip()
        else:
            return f"""
You are TransferAI, a UC transfer advisor. Use only the verified articulation data below.

📨 **Question:** {user_question.strip()}

🎓 **UC Course:** {uc_course} – {uc_course_title}  

> This course must be completed at UC San Diego.

Follow official policy only. Be concise.
""".strip()

    # Base prompt with course info and question - simplified for all verbosity levels
    if verbosity == VerbosityLevel.MINIMAL:
        # Ultra-concise version for MINIMAL verbosity
        base_prompt = f"""
TransferAI advisor data:
Question: {user_question.strip()}
UC Course: {uc_course} – {uc_course_title}  
Options:
{enriched_logic.strip()}
""".strip()
        
        return f"{base_prompt}\nBe extremely brief."
    elif verbosity == VerbosityLevel.STANDARD:
        base_prompt = f"""
You are TransferAI, a UC transfer advisor. Use only the verified articulation data.

📨 **Question:** {user_question.strip()}

🎓 **UC Course:** {uc_course} – {uc_course_title}  

To satisfy this UC course requirement, you must complete one of the following De Anza course options:

{enriched_logic.strip()}
""".strip()
        
        return f"{base_prompt}\nBe clear but concise."
    else:  # DETAILED
        base_prompt = f"""
You are TransferAI, a UC transfer advisor. Use only the verified articulation data below.

📨 **Question:** {user_question.strip()}

🎓 **UC Course:** {uc_course} – {uc_course_title}  

To satisfy this UC course requirement, you must complete one of the following De Anza course options:

{enriched_logic.strip()}
""".strip()
        
        return f"{base_prompt}\nProvide a complete explanation of the requirements and options."


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
        verbosity: The desired level of detail in responses.
        
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

    if logic_type == "all_required":
        group_logic_explanation = "every UC course listed below individually"
    elif logic_type == "choose_one_section":
        group_logic_explanation = "all UC courses from either Section A or Section B, but not both"
    elif logic_type == "select_n_courses":
        group_logic_explanation = f"exactly {n_courses} full UC course(s) from the list below"
    else:
        group_logic_explanation = "the requirements listed in the articulation summary"

    # Simplified logic hint based on group logic type
    logic_hint = f"To satisfy {group_label}, you must complete {group_logic_explanation}."

    # Base prompt with group info and question - significantly simplified
    if verbosity == VerbosityLevel.MINIMAL:
        # Ultra-concise version for MINIMAL verbosity
        base_prompt = f"""
TransferAI advisor data:
Question: {user_question.strip()}
Group: {group_id}{': ' + group_title if group_title else ''}
Logic Type: {logic_type}
Rule: {logic_hint}
Data:
{enriched_logic.strip()}
""".strip()
        
        return f"{base_prompt}\nBe extremely brief. No fabrication."
    elif verbosity == VerbosityLevel.STANDARD:
        base_prompt = f"""
You are TransferAI, a UC transfer advisor. Use only the verified articulation data.

📨 **Question:** {user_question.strip()}

📘 **{group_label}{': ' + group_title if group_title else ''}**  
🔎 **Logic Type:** {logic_type}

{logic_hint}

Here is the verified articulation summary:

{enriched_logic.strip()}
""".strip()
        
        return f"{base_prompt}\nBe clear but concise. No fabrication."
    else:  # DETAILED
        base_prompt = f"""
You are TransferAI, a UC transfer advisor. Use only the verified articulation data below.

📨 **Question:** {user_question.strip()}

📘 **{group_label}{': ' + group_title if group_title else ''}**  
🔎 **Logic Type:** {logic_type}

{logic_hint}

Here is the verified articulation summary:

{enriched_logic.strip()}

NEVER fabricate course options. ONLY use options that appear explicitly in the data above.
""".strip()
        
        return f"{base_prompt}\nProvide a thorough explanation of all requirements and options."


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
        verbosity: The desired level of detail in responses.
        
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
    logger.info(f"Building prompt with verbosity level: {verbosity.value}")
    
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

def _get_system_instructions(verbosity: VerbosityLevel) -> str:
    """Get system instructions based on verbosity level."""
    base_instructions = """
    You are TransferAI, an expert on course articulation between California community colleges and 
    University of California campuses.
    """
    
    if verbosity == VerbosityLevel.MINIMAL:
        return dedent(base_instructions + """
        Provide extremely concise answers focused only on essential information.
        """).strip()
    
    elif verbosity == VerbosityLevel.DETAILED:
        return dedent(base_instructions + """
        Provide comprehensive answers with detailed explanations.
        """).strip()
    
    # Default STANDARD verbosity
    return dedent(base_instructions + """
    Provide clear and helpful answers with appropriate level of detail.
    """).strip()

def _get_formatting_instructions(verbosity: VerbosityLevel) -> str:
    """Get formatting instructions based on verbosity level."""
    base_formatting = """
    RESPONSE FORMATTING:
    - Use clear yes/no answers when appropriate
    - Format lists consistently
    """
    
    if verbosity == VerbosityLevel.MINIMAL:
        return dedent(base_formatting + """
        - Be exceptionally brief
        - Omit introductions and conclusions
        - Use bullet points for lists
        """).strip()
    
    elif verbosity == VerbosityLevel.DETAILED:
        return dedent(base_formatting + """
        - Provide thorough explanations
        - Explain any nuances
        - Use structured sections when appropriate
        """).strip()
    
    # Default STANDARD verbosity
    return dedent(base_formatting + """
    - Balance brevity with clarity
    - Include just enough context
    """).strip()

class PromptBuilder:
    def __init__(self, verbosity: Union[VerbosityLevel, str] = VerbosityLevel.STANDARD):
        self.verbosity = self._normalize_verbosity(verbosity)
        # Initialize other attributes as needed
        
    def _normalize_verbosity(self, verbosity: Union[VerbosityLevel, str]) -> VerbosityLevel:
        """Convert string verbosity to enum if needed and validate"""
        if isinstance(verbosity, str):
            try:
                return VerbosityLevel[verbosity.upper()]
            except KeyError:
                logger.warning(f"Invalid verbosity level: {verbosity}. Using STANDARD.")
                return VerbosityLevel.STANDARD
        elif isinstance(verbosity, VerbosityLevel):
            return verbosity
        else:
            logger.warning(f"Invalid verbosity type: {type(verbosity)}. Using STANDARD.")
            return VerbosityLevel.STANDARD
    
    def set_verbosity(self, verbosity: Union[VerbosityLevel, str]) -> None:
        """Update the verbosity level"""
        self.verbosity = self._normalize_verbosity(verbosity)
        
    def build_prompt(self, query: str, documents: List[Dict[str, Any]], **kwargs) -> str:
        """
        Build a prompt based on the query, documents, and verbosity level
        """
        # Base structure common to all verbosity levels
        prompt = self._build_base_prompt(query, documents)
        
        # Add additional context based on verbosity
        if self.verbosity == VerbosityLevel.MINIMAL:
            prompt = self._add_minimal_context(prompt)
        elif self.verbosity == VerbosityLevel.STANDARD:
            prompt = self._add_standard_context(prompt)
        elif self.verbosity == VerbosityLevel.DETAILED:
            prompt = self._add_detailed_context(prompt)
            
        return prompt
    
    def _build_base_prompt(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """
        Build the base prompt structure needed for all verbosity levels
        """
        # Base prompt logic here
        # This should include the essential information needed regardless of verbosity
        prompt = f"Query: {query}\n\n"
        prompt += "Context Documents:\n"
        
        for i, doc in enumerate(documents):
            prompt += f"Document {i+1}: {doc.get('title', 'Untitled')}\n"
            # Add minimal document content
            
        return prompt
    
    def _add_minimal_context(self, prompt: str) -> str:
        """
        Add minimal context to the prompt - just enough for basic functionality
        """
        prompt += "\nInstructions for Minimal Response:\n"
        prompt += "- Provide direct answers without elaboration\n"
        
        return prompt
    
    def _add_standard_context(self, prompt: str) -> str:
        """
        Add standard context to the prompt - balanced verbosity
        """
        prompt += "\nInstructions for Standard Response:\n"
        prompt += "- Balance conciseness with necessary explanation\n"
        
        return prompt
    
    def _add_detailed_context(self, prompt: str) -> str:
        """
        Add detailed context to the prompt - comprehensive explanation
        """
        prompt += "\nInstructions for Detailed Response:\n"
        prompt += "- Provide comprehensive explanations\n"
        
        return prompt
    
    # Additional methods can be implemented as needed

# Example usage
if __name__ == "__main__":
    builder = PromptBuilder(verbosity=VerbosityLevel.STANDARD)
    prompt = builder.build_prompt("Sample query", [{"title": "Sample document"}])
    print(prompt)