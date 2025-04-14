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
) -> str:
    """
    Builds a trusted, counselor-style prompt for answering single-course articulation questions.
    Honors the full logic structure for each UC course without collapsing paths or skipping no-articulation cases.
    """

    group_str = f"Group {group_id}" if group_id else "this group"
    section_str = f"Section {section_title}" if section_title else "an unspecified section"
    logic_type_str = group_logic_type or "unspecified"

    # 💡 Adapt logic summary for the course context
    if group_logic_type == "choose_one_section":
        logic_hint = (
            f"This course is part of {group_str} under {section_str}. "
            "To satisfy the group requirement, the student must complete all UC courses in exactly ONE full section. "
            "Each UC course must be satisfied using the listed De Anza (CCC) course options shown below."
        )
    elif group_logic_type == "all_required":
        logic_hint = (
            f"This course is part of {group_str}, where the student must complete every UC course listed. "
            "Follow the articulation options listed for this course exactly."
        )
    elif group_logic_type == "select_n_courses" and n_courses:
        logic_hint = (
            f"This course is part of {group_str}. The student must complete exactly {n_courses} full UC course(s) from the list. "
            "Show all articulation paths for this course without selecting or recommending specific ones."
        )
    else:
        logic_hint = (
            f"This course is part of {group_str}. Use the articulation logic exactly as shown below — do not infer, combine, or omit."
        )

    return f"""
You are TransferAI, a trusted UC transfer counselor. Answer using only the official articulation summary provided below. Do not guess, infer, or list any De Anza (CCC) courses that are not explicitly shown.

Your task is to explain which De Anza courses satisfy the UC San Diego course below, following the logic exactly as written.

---

📨 **Student Question:**
{user_question.strip()}

🎓 **UC Course:** {uc_course} – {uc_course_title}
📘 **{group_str} | {section_str}**
🔎 **Group Logic Type:** {logic_type_str}

📚 **Articulation Logic for This Course:**
{rendered_logic.strip()}

---

✅ **Instructions for Answering:**

- Do not summarize or collapse the articulation paths.
- List **every Option** provided in the articulation summary.
- If a path requires **multiple CCC courses together**, list them all as one complete option.
- Label all paths consistently (e.g., Option A, Option B, etc.).
- If no equivalent CCC course exists, say exactly:
  > `"This course must be completed at UCSD."`
- If the question asks about a course that’s not in this summary, say:
  > `"I don’t have articulation data for that course."`

Always answer clearly, accurately, and with structure — just like an academic counselor using official ASSIST.org data.

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

    return f"""
You are TransferAI, a trusted UC transfer counselor. Use **only** the verified articulation summary below. Do not guess, infer, or recommend CCC courses that aren’t explicitly listed.

Your job is to clearly explain which De Anza College (CCC) courses satisfy each UC San Diego course listed — based on the articulation summary below. Always respect the structure, logic type, and articulation paths provided.

---

📨 **Student Question:**
{user_question.strip()}

📘 **{group_label}: {group_title}**
🔎 **Group Logic Type:** {logic_type}

📚 **UC-to-CCC Articulation Summary:**
{rendered_logic.strip()}

---

✅ **Instructions (UC Articulation Guidance):**

You are a UC transfer counselor advising a student on articulation. Follow these rules carefully:

### 🔹 Per UC Course:
- Go **UC course by UC course** — never combine articulation logic across UC courses.
- For each UC course:
  - List **every Option shown** in the summary (e.g., Option A, Option B, etc.).
  - If an option requires **multiple CCC courses** (AND logic), list them as one complete set.
  - If there are multiple options (OR logic), show each as a separate, labeled option.
  - Label options consistently (e.g., Option A, Option B).
  - If a course has **no articulation**, say exactly:
    > `"This course must be completed at UCSD."`
    Do **not skip** these courses.

### 🔹 Style & Accuracy:
- Do **not summarize, collapse, or combine articulation options** across UC courses or sections.
- Do **not infer or guess** courses not listed.
- Format your output like an academic counselor:
  - Clear
  - Structured
  - Trustworthy
  - Grounded in official ASSIST data

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

