from typing import List, Dict, Tuple, Union
import json
from textwrap import indent
from llama_index_client import Document

def render_logic_str(metadata: dict) -> str:
    """
    Renders articulation logic as a markdown list of options.
    Handles recursive OR/AND blocks, strings, and single-course dicts.
    Adds honors note with real CCC course examples.
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

    def extract_honors_info_from_logic(logic_block):
        all_courses = set()
        honors_courses = set()
        non_honors_courses = set()

        def recurse(block):
            if isinstance(block, dict):
                if block.get("type") in {"AND", "OR"} and isinstance(block.get("courses"), list):
                    for course in block["courses"]:
                        recurse(course)
                elif "course_letters" in block:
                    code = block.get("course_letters", "").strip()
                    if code:
                        all_courses.add(code)
                        if block.get("honors"):
                            honors_courses.add(code)
                        else:
                            non_honors_courses.add(code)
            elif isinstance(block, list):
                for item in block:
                    recurse(item)

        recurse(logic_block)
        return {
            "honors_courses": sorted(honors_courses),
            "non_honors_courses": sorted(non_honors_courses),
        }

    block = metadata.get("logic_block", {})
    rendered = resolve_logic_block(block)

    if not rendered:
        return "❌ This course must be completed at UCSD."

    honors_info = extract_honors_info_from_logic(block)
    honors_list = honors_info["honors_courses"]
    non_honors_list = honors_info["non_honors_courses"]

    honors_note = ""
    if honors_list:
        honors_note += f"\n\n🔹 Honors courses accepted: {', '.join(honors_list)}."
    if non_honors_list:
        honors_note += f"\n🔹 Non-honors courses also accepted: {', '.join(non_honors_list)}."

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

def find_uc_courses_satisfied_by(ccc_course: str, all_docs: List[Document]) -> List[Document]:
    """
    Reverse-match: Find all UC courses whose logic includes the given CCC course.
    Searches deeply inside all nested logic blocks.
    """
    matches = []

    ccc_norm = ccc_course.strip().upper()

    def logic_contains_course(block):
        logic_type = block.get("type")
        courses = block.get("courses", [])

        if isinstance(courses, list):
            for entry in courses:
                if isinstance(entry, dict):
                    if entry.get("type") in {"AND", "OR"}:
                        if logic_contains_course(entry):  # recursive dive
                            return True
                    elif entry.get("course_letters", "").strip().upper() == ccc_norm:
                        return True
        return False

    for doc in all_docs:
        logic = doc.metadata.get("logic_block", {})
        if logic_contains_course(logic):
            matches.append(doc)

    return matches


# New in v1.2
def validate_combo_against_group(ccc_courses, group_data):
    """
    Given a list of CCC course names and a group_data object (from ASSIST), 
    check whether the combo satisfies the group's UC course articulation logic.
    
    Returns a dictionary with validation results.
    """
    user_courses = set(c.upper().strip() for c in ccc_courses)
    logic_type = group_data.get("logic_type")
    n_required = group_data.get("n_courses", 1) if logic_type == "select_n_courses" else None

    satisfied_uc_courses = []
    unsatisfied_uc_courses = []
    section_matches = {}  # section_id → list of matched UC courses

    for section in group_data.get("sections", []):
        section_id = section.get("section_id", "default")

        for uc_course in section.get("uc_courses", []):
            uc_name = uc_course.get("name")

            # ✅ Safely parse logic_blocks (may be JSON string)
            logic_blocks = uc_course.get("logic_blocks", [])
            if isinstance(logic_blocks, str):
                try:
                    logic_blocks = json.loads(logic_blocks)
                except json.JSONDecodeError:
                    logic_blocks = []

            matched = False
            for block in logic_blocks:
                if not isinstance(block, dict):
                    continue

                if block.get("type") == "AND":
                    required_courses = set(
                        course.get("course_letters", course["name"]).upper().strip()
                        for course in block.get("courses", [])
                    )
                    if required_courses.issubset(user_courses):
                        matched = True
                        break

                elif block.get("type") == "OR":
                    for subblock in block.get("courses", []):
                        if subblock.get("type") == "AND":
                            required = set(
                                course.get("course_letters", course["name"]).upper().strip()
                                for course in subblock.get("courses", [])
                            )
                            if required.issubset(user_courses):
                                matched = True
                                break
                    if matched:
                        break

            if matched:
                satisfied_uc_courses.append(uc_name)
                section_matches.setdefault(section_id, []).append(uc_name)
            else:
                unsatisfied_uc_courses.append(uc_name)

    satisfied_count = len(satisfied_uc_courses)
    fully_satisfied = False

    if logic_type == "all_required":
        fully_satisfied = (len(unsatisfied_uc_courses) == 0)
    elif logic_type == "select_n_courses":
        fully_satisfied = (satisfied_count >= n_required)
    elif logic_type == "choose_one_section":
        # ✅ Must match ALL UC courses from ONE section only
        sections_with_all_courses = [
            sid for sid, matched_courses in section_matches.items()
            if len(matched_courses) == len([
                uc for sec in group_data.get("sections", []) if sec.get("section_id") == sid
                for uc in sec.get("uc_courses", [])
            ])
        ]
        fully_satisfied = len(sections_with_all_courses) == 1

    return {
        "is_fully_satisfied": fully_satisfied,
        "partially_satisfied": satisfied_count > 0 and not fully_satisfied,
        "satisfied_uc_courses": satisfied_uc_courses,
        "unsatisfied_uc_courses": unsatisfied_uc_courses,
        "required_count": n_required,
        "satisfied_count": satisfied_count
    }


def include_binary_explanation(response_text: str, satisfied: bool, validation_summary: str) -> str:
    """
    Prepends a binary summary to the LLM's full response.
    """
    header = f"{'✅ Yes' if satisfied else '❌ No'}, based on the official articulation logic.\n"
    return header + "\n" + validation_summary.strip() + "\n\n" + response_text.strip()

# New in v1.3

def validate_uc_courses_against_group_sections(user_uc_courses, group_data):
    """
    Given a list of UC course names and a group_data object (from ASSIST),
    validate whether all UC courses are satisfied together under one section.

    Returns a dictionary summarizing:
    - is_fully_satisfied: bool
    - satisfied_section_id: section where match was found
    - missing_uc_courses: list
    - matched_ccc_courses: dict mapping UC course → CCC match list
    """
    import json

    user_uc_courses = set(c.upper().strip() for c in user_uc_courses)
    sections = group_data.get("sections", [])

    for section in sections:
        section_id = section.get("section_id", "default")
        uc_courses_in_section = {
            uc["name"].upper().strip(): uc.get("logic_blocks", [])
            for uc in section.get("uc_courses", [])
            if uc.get("name", "").upper().strip() in user_uc_courses
        }

        if len(uc_courses_in_section) != len(user_uc_courses):
            continue  # This section doesn't contain all requested UC courses

        matched_ccc_courses = {}
        missing_uc_courses = []
        is_fully_satisfied = True

        for uc_name, logic_blocks in uc_courses_in_section.items():
            # ✅ Normalize logic_blocks into a list of dicts
            if isinstance(logic_blocks, str):
                try:
                    logic_blocks = json.loads(logic_blocks)
                except json.JSONDecodeError:
                    logic_blocks = []

            elif isinstance(logic_blocks, dict):
                logic_blocks = [logic_blocks]

            elif not isinstance(logic_blocks, list):
                logic_blocks = []

            satisfied = False
            ccc_options = []


            for block in logic_blocks:
                if not isinstance(block, dict):
                    continue

                if block.get("type") == "AND":
                    ccc_list = [
                        course.get("course_letters", course["name"]).upper().strip()
                        for course in block.get("courses", [])
                    ]
                    satisfied = True
                    ccc_options.append(ccc_list)
                    break

                elif block.get("type") == "OR":
                    for subblock in block.get("courses", []):
                        if subblock.get("type") == "AND":
                            ccc_list = [
                                course.get("course_letters", course["name"]).upper().strip()
                                for course in subblock.get("courses", [])
                            ]
                            satisfied = True
                            ccc_options.append(ccc_list)
                            break
                    if satisfied:
                        break

            if satisfied:
                matched_ccc_courses[uc_name] = ccc_options[0] if ccc_options else []
            else:
                missing_uc_courses.append(uc_name)
                is_fully_satisfied = False

        if is_fully_satisfied:
            return {
                "is_fully_satisfied": True,
                "satisfied_section_id": section_id,
                "missing_uc_courses": [],
                "matched_ccc_courses": matched_ccc_courses
            }

    # No single section satisfies all requested UC courses
    return {
        "is_fully_satisfied": False,
        "satisfied_section_id": None,
        "missing_uc_courses": list(user_uc_courses),
        "matched_ccc_courses": {}
    }


def is_honors_pair_equivalent(or_block, course1, course2):
    """
    Returns True if course1 and course2 are an honors/non-honors pair that
    are the ONLY two articulation options in a single OR block.
    This prevents over-triggering and limits scope to Test 20-style questions.
    """
    def normalize(c):
        return c.strip().lower()

    c1 = normalize(course1)
    c2 = normalize(course2)

    if not or_block or or_block.get("type") != "OR":
        return False

    # Must only have two AND options in OR block
    if len(or_block.get("courses", [])) != 2:
        return False

    found = set()
    for and_block in or_block.get("courses", []):
        if and_block.get("type") != "AND" or len(and_block.get("courses", [])) != 1:
            return False
        course = and_block["courses"][0]
        found.add(normalize(course.get("course_letters", "")))

    return c1 in found and c2 in found




# Backward-compatible alias for default rendering
render_logic = render_logic_str