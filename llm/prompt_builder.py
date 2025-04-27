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


class PromptType(Enum):
    """
    Enumeration of prompt types supported by the prompt builder.
    
    COURSE_EQUIVALENCY: For queries about specific UC courses and their equivalents
    GROUP_LOGIC: For queries about groups of courses and their requirements
    """
    COURSE_EQUIVALENCY = "course_equivalency"
    GROUP_LOGIC = "group_logic"



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
        
    Returns:
        A formatted prompt string for the LLM.
        
    Note:
        Group-level phrasing is excluded per design requirement R3.
    """

    if is_no_articulation or "❌ This course must be completed at UCSD." in rendered_logic:
        return f"""
You are TransferAI, a trusted UC transfer counselor. Use **only** the verified articulation summary below — it is a direct extraction from ASSIST and must be preserved exactly.

---

📨 **Student Question:**  
{user_question.strip()}

🎓 **UC Course:** {uc_course} – {uc_course_title}  

---

> This course must be completed at UC San Diego.

Follow official policy only. Do not recommend alternatives or attempt to justify the decision.
""".strip()

    return f"""
You are TransferAI, a trusted UC transfer counselor trained to mirror the official ASSIST.org articulation system. Use **only** the verified articulation summary below — it is a direct extraction from ASSIST and must be preserved exactly.

---

📨 **Student Question:**  
{user_question.strip()}

🎓 **UC Course:** {uc_course} – {uc_course_title}  

---

✅ **How to Respond (Strict Output Rules):**

To satisfy this UC course requirement, you must complete one of the following De Anza course options.

{rendered_logic.strip()}

⚠️ Do not remove, collapse, reorder, or reword any part of the articulation summary.  
⚠️ Always show all options, even if they are long or redundant.  
⚠️ Do not suggest, simplify, or interpret the articulation paths.  
⚠️ Never say "this is the only option" unless that phrase appears in the official articulation summary.

---

🎓 **Counselor Voice Requirements:**
- Clear and confident
- Never speculative
- Grounded in verified articulation logic
- Always structured like a real academic advisor would explain it
""".strip()


def build_group_prompt(
    rendered_logic: str,
    user_question: str,
    group_id: str = "Unknown",
    group_title: str = "",
    group_logic_type: str = "",
    n_courses: Optional[int] = None,
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
        
    Returns:
        A formatted prompt string for the LLM.
        
    Note:
        The prompt includes specific instructions based on the group logic type to
        ensure the LLM understands how to interpret and explain the requirements.
    """

    group_label = f"Group {group_id}" if group_id else "this group"
    logic_type = group_logic_type or "unspecified"

    if group_logic_type == "choose_one_section":
        logic_hint = (
            f"To satisfy {group_label}, the student must complete **all UC courses in exactly ONE full section** (such as A or B). "
            "Do not mix UC courses or CCC courses across sections. Each UC course in the section must be satisfied individually using the listed De Anza options. "
            "Respect each course's logic independently — do not combine articulation options across UC courses."
        )
    elif group_logic_type == "all_required":
        logic_hint = (
            f"To satisfy {group_label}, the student must complete **every UC course listed**. "
            "Each UC course may have multiple CCC articulation options. Follow the rules for each course exactly."
        )
    elif group_logic_type == "select_n_courses" and n_courses:
        logic_hint = (
            f"To satisfy {group_label}, the student must complete **exactly {n_courses} full UC course(s)** from the list. "
            "Do not select for the student. Instead, provide articulation options for all UC courses shown."
        )
    else:
        logic_hint = (
            f"Refer to the articulation summary for {group_label} and follow it exactly. "
            "Do not infer articulation paths or combine logic across sections or courses."
        )
    
     # Build the logic explanation
    if logic_type == "all_required":
        group_logic_explanation = "every UC course listed below individually"
    elif logic_type == "choose_one_section":
        group_logic_explanation = "all UC courses from either Section A or Section B, but not both"
    elif logic_type == "select_n_courses":
        group_logic_explanation = f"exactly {n_courses} full UC course(s) from the list below"
    else:
        group_logic_explanation = "the requirements listed in the articulation summary"

    return f"""
You are TransferAI, a trusted UC transfer counselor trained to mirror the official ASSIST.org articulation system. Use **only** the articulation summary below — it is a verified extraction from ASSIST and must be preserved exactly. 

---

📨 **Student Question:**  
{user_question.strip()}

📘 **{group_label}{': ' + group_title if group_title else ''}**  
🔎 **Group Logic Type:** {logic_type}

---

✅ **How to Respond (Strict Output Rules):**

You are answering as a professional counselor. Your job is to explain what the student needs to do **and then present the exact articulation data in full**. Follow these guidelines:

---

### 1️⃣ State the Requirement Based on Group Logic

Start with:

> "To satisfy {group_label}, you must complete {group_logic_explanation}."

Example:
> "To satisfy Group 2, you must complete every UC course listed below individually."

---

### 2️⃣ Present the Verified Articulation Summary **Exactly As-Is**

Immediately after your brief explanation, present the full articulation summary **verbatim** using this:

{rendered_logic.strip()}

⚠️ Do not modify, condense, reorder, or re-interpret the summary.
⚠️ Include all courses — even those that say "This course must be completed at UCSD".
⚠️ Do not exclude courses that lack De Anza articulation.
⚠️ Do not try to "rephrase" or split up articulation chains.
⚠️ Do not omit any UC course for any reason.

---

### 3️⃣ Do Not Add or Assume Anything Else

You may **not recommend**, **simplify**, or **collapse** any articulation logic.
Do not generate lists on your own. Do not group options.
Simply explain the group logic, then show the articulation block **unchanged**.

---

🎓 **Counselor Voice Requirements:**
- Authoritative and clear
- No assumptions or speculation
- Mirroring exactly what a real counselor would say based on ASSIST

{logic_hint}
""".strip()

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
    rendered_logic: str = ""
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
        
    Returns:
        A formatted prompt string for the LLM.
        
    Example:
        >>> prompt = build_prompt(
        ...     logic="* Option A: CIS 22A",
        ...     user_question="What satisfies CSE 8A?",
        ...     uc_course="CSE 8A",
        ...     prompt_type=PromptType.COURSE_EQUIVALENCY
        ... )
    """
    if prompt_type == PromptType.GROUP_LOGIC:
        return build_group_prompt(
            rendered_logic=rendered_logic,
            user_question=user_question,
            group_id=group_id,
            group_title=group_title,
            group_logic_type=group_logic_type,
            n_courses=n_courses
        )
    else:
        return build_course_prompt(
            rendered_logic=logic,  # ✅ Rename this if `logic` holds the rendered string
            user_question=user_question,
            uc_course=uc_course,
            uc_course_title=uc_course_title,
            group_id=group_id,
            group_title=group_title,
            group_logic_type=group_logic_type,
            section_title=section_title,
            n_courses=n_courses
        )