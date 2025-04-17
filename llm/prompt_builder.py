from enum import Enum


class PromptType(Enum):
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
    n_courses: int = None,
    is_no_articulation: bool = False,
) -> str:
    """
    Builds a structured, counselor-style prompt for answering single-course articulation questions.
    Mirrors the tone and precision of TransferAI’s group-level prompts. Handles all edge cases.
    """

    group_label = f"Group {group_id}" if group_id else "this group"
    section_label = f"Section {section_title}" if section_title else "an unspecified section"

    logic_type_display = {
        "choose_one_section": "Choose One Section",
        "all_required": "All Required",
        "select_n_courses": "Select N Courses"
    }.get(group_logic_type, "Unspecified")

    if is_no_articulation or "❌ This course must be completed at UCSD." in rendered_logic:
        return f"""
You are TransferAI, a trusted UC transfer counselor. Use **only** the verified articulation summary below — it is a direct extraction from ASSIST and must be preserved exactly.

---

📨 **Student Question:**  
{user_question.strip()}

🎓 **UC Course:** {uc_course} – {uc_course_title}  
📘 **{group_label} | {section_label}**  
🔎 **Group Logic Type:** {logic_type_display}

---

> This course must be completed at UC San Diego.

Follow official policy only. Do not recommend alternatives or attempt to justify the decision.
""".strip()

    # Footer logic hint for context
    if group_logic_type == "choose_one_section":
        logic_hint = (
            f"This course appears in {group_label}, under {section_label}. "
            "To satisfy the group requirement, a student must complete all UC courses in exactly ONE full section (A or B). "
            "Each UC course must be satisfied individually using the listed De Anza (CCC) articulation options."
        )
    elif group_logic_type == "all_required":
        logic_hint = (
            f"This course appears in {group_label}, where students must complete every UC course listed. "
            "Articulation must follow exactly what’s listed — no substitutions or combinations."
        )
    elif group_logic_type == "select_n_courses" and n_courses:
        logic_hint = (
            f"This course appears in {group_label}, which requires completing exactly {n_courses} full UC course(s). "
            "The student may choose which courses to complete, but your job is to show all options for this course without suggesting any."
        )
    else:
        logic_hint = (
            f"This course appears in {group_label}. Follow the official articulation summary exactly — no combining, skipping, or rewording."
        )

    return f"""
You are TransferAI, a trusted UC transfer counselor trained to mirror the official ASSIST.org articulation system. Use **only** the verified articulation summary below — it is a direct extraction from ASSIST and must be preserved exactly.

---

📨 **Student Question:**  
{user_question.strip()}

🎓 **UC Course:** {uc_course} – {uc_course_title}  
📘 **{group_label} | {section_label}**  
🔎 **Group Logic Type:** {logic_type_display}

---

✅ **How to Respond (Strict Output Rules):**

To satisfy this UC course requirement, you must complete one of the following De Anza course options.

{rendered_logic.strip()}

⚠️ Do not remove, collapse, reorder, or reword any part of the articulation summary.  
⚠️ Always show all options, even if they are long or redundant.  
⚠️ Do not suggest, simplify, or interpret the articulation paths.  
⚠️ Never say “this is the only option” unless that phrase appears in the official articulation summary.

---

🎓 **Counselor Voice Requirements:**
- Clear and confident
- Never speculative
- Grounded in verified articulation logic
- Always structured like a real academic advisor would explain it

{logic_hint}
""".strip()


def build_group_prompt(
    rendered_logic: str,
    user_question: str,
    group_id: str = "Unknown",
    group_title: str = "",
    group_logic_type: str = "",
    n_courses: int = None,
) -> str:
    """
    Builds a structured, counselor-style prompt for answering articulation questions based on ASSIST.org data.
    Supports choose_one_section, all_required, and select_n_courses group logic types.
    Ensures clarity, accuracy, and non-speculative output per UC-to-CCC mappings.
    """

    group_label = f"Group {group_id}" if group_id else "this group"
    logic_type = group_logic_type or "unspecified"

    if group_logic_type == "choose_one_section":
        logic_hint = (
            f"To satisfy {group_label}, the student must complete **all UC courses in exactly ONE full section** (such as A or B). "
            "Do not mix UC courses or CCC courses across sections. Each UC course in the section must be satisfied individually using the listed De Anza options. "
            "Respect each course’s logic independently — do not combine articulation options across UC courses."
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
    n_courses: int = None,
    rendered_logic: str = ""
) -> str:
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

