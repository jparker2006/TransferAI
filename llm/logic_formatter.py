from typing import List, Dict, Tuple, Union
import json
from textwrap import indent

def render_logic_str(metadata: dict) -> str:
    uc_course = metadata.get("uc_course", "Unknown").strip()
    uc_title = metadata.get("uc_title", "")
    group_type = metadata.get("group_logic_type", "").lower()

    if metadata.get("no_articulation", False) or metadata.get("logic_block", {}).get("no_articulation", False):
        # print(f"[DEBUG] {uc_course} marked as no articulation.")
        return "❌ This course must be completed at UCSD."

    block = metadata.get("logic_block", {})
    options = block.get("courses", [])

    # if not options:
    #     print(f"[DEBUG] No articulation options found for {uc_course}")

    rendered_paths = []

    for i, option in enumerate(options):
        label = f"Option {chr(65 + i)}"

        if isinstance(option, str):
            rendered_paths.append(f"* {label}: {option}")

        elif isinstance(option, dict) and option.get("type") == "AND":
            course_list = option.get("courses", [])
            course_codes = [c.get("course_letters", "UNKNOWN") for c in course_list]
            if len(course_codes) > 1:
                rendered_paths.append(f"* {label}: " + ", ".join(course_codes) + " (complete all)")
            elif course_codes:
                rendered_paths.append(f"* {label}: {course_codes[0]}")
            else:
                rendered_paths.append(f"* {label}: No valid courses listed.")

        else:
            rendered_paths.append(f"* {label}: ⚠️ Invalid option format.")

    # Final debug
    # print(f"[DEBUG] Rendered logic for {uc_course}: {len(rendered_paths)} option(s)")
    header = f"📘 {uc_course} – {uc_title}"
    return f"{header}\n" + "\n".join(rendered_paths)


def render_group_summary(docs: List) -> str:
    """
    Render a group-level summary of UC-to-CCC course articulation across all sections.
    Ensures each UC course in the group is covered fully. Works with nested logic.
    """
    if not docs:
        return "⚠️ No articulation documents found for this group."

    docs = sorted(docs, key=lambda d: (d.metadata.get("section", ""), d.metadata.get("uc_course", "")))

    section_map = {}
    all_course_blocks = []
    has_multi_course_uc = False

    # Shared metadata
    group_id = docs[0].metadata.get("group", "")
    group_title = docs[0].metadata.get("group_title", "")
    group_type = docs[0].metadata.get("group_logic_type", "")
    n_courses = docs[0].metadata.get("n_courses")

    course_entries = []

    for doc in docs:
        metadata = doc.metadata
        section_id = metadata.get("section", "A") or "A"
        uc_course = metadata.get("uc_course", "Unknown")
        uc_title = metadata.get("uc_title", "")
        logic_block = metadata.get("logic_block", {})

        # Track if any multi-course CCC articulation exists
        for option in logic_block.get("courses", []):
            if isinstance(option, dict) and option.get("type") == "AND" and len(option.get("courses", [])) > 1:
                has_multi_course_uc = True

        # Render logic
        logic_str = render_logic_str(metadata).strip()

        # Format final output block per course
        if "❌" in logic_str:
            full_entry = f"**{uc_course} – {uc_title}**\n❌ This course must be completed at UCSD."
        else:
            full_entry = f"**{uc_course} – {uc_title}**\n{logic_str}"

        # Append to section or flat list
        if group_type == "choose_one_section":
            section_map.setdefault(section_id, []).append((uc_course, full_entry))
        else:
            course_entries.append((uc_course, full_entry))

    # Format display
    rendered_sections = []

    if group_type == "choose_one_section":
        for section_id, entries in section_map.items():
            sorted_blocks = sorted(entries, key=lambda x: x[0])
            section_body = "\n\n".join([block for _, block in sorted_blocks])
            rendered_sections.append(f"🔹 Section {section_id}\n{section_body}")
    else:
        # Sort by course name like "CSE 20", "MATH 18", etc.
        sorted_blocks = sorted(course_entries, key=lambda x: x[0])
        rendered_sections = [block for _, block in sorted_blocks]

    # Footer
    footer = []
    if group_type == "choose_one_section":
        footer.append(
            f"✅ To satisfy Group {group_id}, complete **all UC courses in exactly ONE full section** listed above (e.g., A or B). "
            "Do not mix UC or CCC courses between sections. Follow the articulation options listed for each UC course."
        )
    elif group_type == "all_required":
        footer.append(
            f"✅ To satisfy Group {group_id}, **every UC course listed above must be satisfied individually.** "
            "Each UC course may have multiple CCC articulation options — follow the logic shown."
        )
    elif group_type == "select_n_courses" and n_courses:
        footer.append(
            f"✅ To satisfy Group {group_id}, complete **exactly {n_courses} full UC course(s)** from the list above. "
            "Each UC course has its own articulation options — follow the logic shown for each course."
        )

    if has_multi_course_uc:
        footer.append("⚠️ Some UC courses require **multiple CCC courses**. You must complete every course listed in the selected option.")

    return "\n\n".join(rendered_sections + footer)


def explain_if_satisfied(selected_courses: List[str], logic_block: dict) -> Tuple[bool, str]:
    """
    Determine if the selected CCC courses satisfy any full articulation path
    in the logic_block. Provides detailed option-level feedback.
    
    Returns:
        (True, message)  — if a full Option is satisfied
        (False, message) — with structured explanation of partial/missing courses
    """
    if not logic_block or not isinstance(logic_block, dict):
        return False, "⚠️ No articulation logic available."

    selected_set = {c.upper().strip() for c in selected_courses}
    block_type = logic_block.get("type", "OR")
    options = logic_block.get("courses", [])

    if block_type != "OR" or not isinstance(options, list) or not options:
        return False, "⚠️ Invalid or empty articulation structure."

    feedback = []

    for i, option in enumerate(options):
        label = f"Option {chr(65 + i)}"

        # Validate that this is a standard AND bundle
        if not isinstance(option, dict) or option.get("type") != "AND":
            feedback.append(f"{label}: ⚠️ Skipped (invalid format).")
            continue

        course_entries = option.get("courses", [])
        required_courses = {c.get("course_letters", "").upper() for c in course_entries if "course_letters" in c}
        missing = required_courses - selected_set
        matched = required_courses & selected_set

        if required_courses.issubset(selected_set):
            return True, f"✅ Satisfies {label} with: {', '.join(sorted(matched))}"
        elif matched:
            feedback.append(f"{label}: ❗ Partial match – missing: {', '.join(sorted(missing))}")
        else:
            feedback.append(f"{label}: 🚫 No matching courses taken.")

    return False, "❌ No complete option satisfied.\n" + "\n".join(feedback)


def get_course_summary(metadata: dict) -> str:
    """
    Returns a short summary of UC course + equivalent CCC options.
    """
    uc = metadata.get("uc_course", "Unknown").strip(":")
    ccc = metadata.get("ccc_courses")
    if not ccc:
        # Try extracting from logic_block
        ccc = set()
        block = metadata.get("logic_block", {})
        for option in block.get("courses", []):
            if isinstance(option, list):
                for c in option:
                    ccc.add(c.get("course_letters", "UNKNOWN"))
            else:
                ccc.add(option.get("course_letters", "UNKNOWN"))
        ccc = sorted(ccc)

    logic_desc = render_logic_str(metadata)
    return f"UC Course: {uc}\nCCC Equivalent(s): {', '.join(ccc) or 'None'}\nLogic:\n{logic_desc}"


# Backward-compatible alias for default rendering
render_logic = render_logic_str
