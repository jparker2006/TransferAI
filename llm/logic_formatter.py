from typing import List, Dict, Tuple, Union
import json
from textwrap import indent

def render_logic_str(metadata: dict) -> str:
    """
    Renders articulation logic as a markdown list of options.
    Handles recursive OR/AND blocks, strings, and single-course dicts.
    Adds honors note if any honors course appears.
    """
    if metadata.get("no_articulation", False) or metadata.get("logic_block", {}).get("no_articulation", False):
        return "❌ This course must be completed at UCSD."

    honors_found = False

    def resolve_logic_block(block) -> List[str]:
        """Recursively resolve logic blocks and format course paths."""
        nonlocal honors_found
        logic_type = block.get("type")
        raw_options = block.get("courses", [])

        if logic_type == "OR":
            rendered_options = []
            for i, option in enumerate(raw_options):
                label = f"Option {chr(65 + i)}"
                if isinstance(option, dict) and option.get("type") == "AND":
                    course_list = option.get("courses", [])
                    codes = []
                    for c in course_list:
                        if isinstance(c, dict):
                            if c.get("honors", False):
                                honors_found = True
                            codes.append(c.get("course_letters", "UNKNOWN"))
                    if len(codes) > 1:
                        rendered_options.append(f"* {label}: {', '.join(codes)} (complete all)")
                    elif codes:
                        rendered_options.append(f"* {label}: {codes[0]}")
                elif isinstance(option, dict) and option.get("type") == "OR":
                    nested_block = resolve_logic_block(option)
                    rendered_options.extend([f"* {label}.{i+1}: {line[2:]}" for i, line in enumerate(nested_block)])
                elif isinstance(option, dict) and option.get("course_letters"):
                    if option.get("honors", False):
                        honors_found = True
                    rendered_options.append(f"* {label}: {option['course_letters']}")
                elif isinstance(option, str):
                    rendered_options.append(f"* {label}: {option.strip()}")
            return rendered_options
        elif logic_type == "AND":
            codes = []
            for c in raw_options:
                if isinstance(c, dict):
                    if c.get("honors", False):
                        honors_found = True
                    codes.append(c.get("course_letters", "UNKNOWN"))
            if len(codes) > 1:
                return [f"* {' + '.join(codes)} (complete all)"]
            elif codes:
                return [f"* {codes[0]}"]
        return []

    block = metadata.get("logic_block", {})
    rendered = resolve_logic_block(block)

    if not rendered:
        return "❌ This course must be completed at UCSD."

    honors_note = "\n\n🔹 You may choose the honors or non-honors version." if honors_found else ""
    return "\n".join(rendered) + honors_note


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

        # Render logic (do NOT include course title inside render_logic_str)
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
    in the logic_block. Returns True if satisfied, or False with clear breakdown of missing courses.
    """
    if not logic_block or not isinstance(logic_block, dict):
        return False, "⚠️ No articulation logic available."

    selected_set = {c.upper().strip() for c in selected_courses}
    block_type = logic_block.get("type", "OR")
    options = logic_block.get("courses", [])

    if block_type != "OR" or not isinstance(options, list) or not options:
        return False, "⚠️ Invalid or empty articulation structure."

    all_missing_courses = set()
    feedback_lines = []

    for i, option in enumerate(options):
        label = f"Option {chr(65 + i)}"

        # Ensure valid AND path
        if not isinstance(option, dict) or option.get("type") != "AND":
            feedback_lines.append(f"{label}: ⚠️ Skipped (invalid format).")
            continue

        required = {c.get("course_letters", "").upper() for c in option.get("courses", []) if "course_letters" in c}
        missing = required - selected_set
        matched = required & selected_set

        if not required:
            feedback_lines.append(f"{label}: ⚠️ Empty option — no courses required?")
            continue

        if required.issubset(selected_set):
            return True, f"✅ Satisfies {label} with: {', '.join(sorted(matched))}"

        all_missing_courses.update(missing)

        if matched:
            feedback_lines.append(f"{label}: ❗ Partial match — missing: {', '.join(sorted(missing))}")
        else:
            feedback_lines.append(f"{label}: 🚫 No matching courses taken — requires: {', '.join(sorted(required))}")

    summary = "❌ No complete option satisfied."
    if all_missing_courses:
        summary += f"\nYou are missing: {', '.join(sorted(all_missing_courses))}"

    return False, summary + "\n\n" + "\n".join(feedback_lines)

def get_course_summary(metadata: dict) -> str:
    """
    Returns a short summary of UC course + equivalent CCC options.
    """
    uc = metadata.get("uc_course", "Unknown").strip(":")
    ccc_set = set()

    # First try the top-level "ccc_courses" list
    top_level_cccs = metadata.get("ccc_courses", [])
    if isinstance(top_level_cccs, list):
        for c in top_level_cccs:
            if isinstance(c, dict):
                ccc_set.add(c.get("course_letters", "UNKNOWN"))
            elif isinstance(c, str):
                ccc_set.add(c)
    else:
        # fallback is logic_block
        block = metadata.get("logic_block", {})
        for option in block.get("courses", []):
            if isinstance(option, dict) and option.get("type") == "AND":
                for course in option.get("courses", []):
                    ccc_set.add(course.get("course_letters", "UNKNOWN"))
            elif isinstance(option, dict):
                ccc_set.add(option.get("course_letters", "UNKNOWN"))
            elif isinstance(option, str):
                ccc_set.add(option)

    ccc_list = sorted(ccc_set)
    logic_desc = render_logic_str(metadata)

    return f"UC Course: {uc}\nCCC Equivalent(s): {', '.join(ccc_list) or 'None'}\nLogic:\n{logic_desc}"

# Backward-compatible alias for default rendering
render_logic = render_logic_str