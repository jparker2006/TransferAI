from enum import Enum


class PromptType(Enum):
    COURSE_EQUIVALENCY = "course_equivalency"
    GROUP_LOGIC = "group_logic"
    ADMISSION_RULE = "admission_rule"


def build_course_prompt(logic: str, user_question: str, uc_course: str = "Unknown") -> str:
    return f"""
The student asked:
"{user_question}"

You are answering a question about UC course articulation from De Anza College to UC San Diego.

UC Course: {uc_course}

Articulation Logic (from ASSIST.org):
{logic}

🧠 Reasoning Instructions:
- ONLY use the articulation logic above.
- DO NOT list all options unless the student explicitly asks.
- If specific courses are mentioned, explain if ALL are required, if ONE is enough, or if NONE qualify.
- Do NOT speculate. If a course isn’t in the logic, respond: "I don't have that information."
""".strip()


def build_group_prompt(group_logic: str, user_question: str, group_id: str = "Unknown") -> str:
    return f"""
The student asked:
"{user_question}"

This question is about satisfying articulation Group {group_id} at UC San Diego.

Group Articulation Logic:
{group_logic}

🧠 Instructions:
- Use only the articulation logic above.
- Indicate whether the listed course(s) fully satisfy any of the options in Group {group_id}.
- Respond with clarity and logic. If not listed, say: "I don’t have that information."
""".strip()


def build_admission_prompt(*args, **kwargs):
    # Placeholder for future support
    return "Admission logic prompt handling not yet implemented."


def build_prompt(logic: str, user_question: str, uc_course: str = "Unknown", prompt_type: PromptType = PromptType.COURSE_EQUIVALENCY) -> str:
    if prompt_type == PromptType.GROUP_LOGIC:
        return build_group_prompt(logic, user_question, uc_course)
    elif prompt_type == PromptType.ADMISSION_RULE:
        return build_admission_prompt()
    else:
        return build_course_prompt(logic, user_question, uc_course)
