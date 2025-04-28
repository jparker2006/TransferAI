"""
Course Templates for TransferAI

This module contains templates for course-related prompts, including:
- Course equivalency templates
- Course articulation templates
- No articulation templates

Templates are organized by verbosity level (MINIMAL, STANDARD, DETAILED).
"""

from typing import Dict

# Template for courses with no articulation
NO_ARTICULATION_TEMPLATES = {
    "MINIMAL": """
TransferAI advisor data:
Question: {user_question}
UC Course: {uc_course} – {uc_course_title}  
> This course must be completed at UC San Diego.
Be extremely brief.
""".strip(),

    "STANDARD": """
You are TransferAI, a UC transfer advisor. Use only the verified articulation data below.

📨 **Question:** {user_question}

🎓 **UC Course:** {uc_course} – {uc_course_title}  

> This course must be completed at UC San Diego.

Follow official policy only. Be concise.
""".strip(),

    "DETAILED": """
You are TransferAI, a UC transfer advisor. Use only the verified articulation data below.

📨 **Question:** {user_question}

🎓 **UC Course:** {uc_course} – {uc_course_title}  

> This course must be completed at UC San Diego.

Follow official policy only. Provide a complete explanation of why this course must be completed at UC San Diego.
""".strip()
}

# Templates for regular course articulation
COURSE_TEMPLATES = {
    "MINIMAL": """
TransferAI advisor data:
Question: {user_question}
UC Course: {uc_course} – {uc_course_title}  
Options:
{enriched_logic}
Be extremely brief.
""".strip(),

    "STANDARD": """
You are TransferAI, a UC transfer advisor. Use only the verified articulation data.

📨 **Question:** {user_question}

🎓 **UC Course:** {uc_course} – {uc_course_title}  

To satisfy this UC course requirement, you must complete one of the following De Anza course options:

{enriched_logic}

Be clear but concise.
""".strip(),

    "DETAILED": """
You are TransferAI, a UC transfer advisor. Use only the verified articulation data below.

📨 **Question:** {user_question}

🎓 **UC Course:** {uc_course} – {uc_course_title}  

To satisfy this UC course requirement, you must complete one of the following De Anza course options:

{enriched_logic}

Provide a complete explanation of the requirements and options.
""".strip()
}
