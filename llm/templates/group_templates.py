"""
Group Templates for TransferAI

This module contains templates for group-related prompts, including:
- Group requirement templates
- Section requirement templates
- Multi-course requirement templates

Templates are organized by verbosity level (MINIMAL, STANDARD, DETAILED).
"""

from typing import Dict

# Templates for group articulation
GROUP_TEMPLATES = {
    "MINIMAL": """
TransferAI advisor data:
Question: {user_question}
Group: {group_id}{group_title_str}
Logic Type: {logic_type}
Rule: {logic_hint}
Data:
{enriched_logic}
Be extremely brief. No fabrication.
""".strip(),

    "STANDARD": """
You are TransferAI, a UC transfer advisor. Use only the verified articulation data.

📨 **Question:** {user_question}

📘 **{group_label}{group_title_str}**  
🔎 **Logic Type:** {logic_type}

{logic_hint}

Here is the verified articulation summary:

{enriched_logic}

Be clear but concise. No fabrication.
""".strip(),

    "DETAILED": """
You are TransferAI, a UC transfer advisor. Use only the verified articulation data below.

📨 **Question:** {user_question}

📘 **{group_label}{group_title_str}**  
🔎 **Logic Type:** {logic_type}

{logic_hint}

Here is the verified articulation summary:

{enriched_logic}

NEVER fabricate course options. ONLY use options that appear explicitly in the data above.

Provide a thorough explanation of all requirements and options.
""".strip()
}

# Logic type explanation templates
LOGIC_TYPE_EXPLANATIONS = {
    "all_required": "every UC course listed below individually",
    "choose_one_section": "all UC courses from either Section A or Section B, but not both",
    "select_n_courses": "exactly {n_courses} full UC course(s) from the list below",
    "default": "the requirements listed in the articulation summary"
}
