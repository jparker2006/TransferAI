def render_logic_str(metadata: dict) -> str:
    """
    Render logic_structure into natural language explanation based on group logic type.
    Provides clear labeling for each pathway using 'Option A', 'Option B', etc.
    """
    if metadata.get("no_articulation", False):
        return "No articulated course satisfies this UC requirement."

    logic = metadata.get("logic_structure", [])
    group_type = metadata.get("group_logic_type", "").lower()
    n_required = metadata.get("n_courses", None)

    if not logic:
        return "No articulation logic available."

    rendered_paths = []
    for i, path in enumerate(logic):
        label = f"Option {chr(65 + i)}"  # Option A, B, C...
        course_codes = [c.get("course_letters", "UNKNOWN") for c in path]

        if len(course_codes) > 1:
            explanation = f"{label}: ALL of {', '.join(course_codes)}"
        else:
            explanation = f"{label}: {course_codes[0]}"

        rendered_paths.append(explanation)

    if group_type == "choose_one_section":
        header = "Complete ONE of the following options:"
    elif group_type == "all_required":
        header = "All of the following options are required:"
    elif group_type == "select_n_courses" and n_required:
        header = f"Select {n_required} of the following options:"
    else:
        header = "Equivalent course options:"

    return header + "\n" + "\n".join(rendered_paths)


def render_logic_tokens(metadata: dict) -> list:
    """
    Returns structured logic format:
    [
        {"type": "AND", "courses": ["CIS 36A", "CIS 36B"]},
        {"type": "OR", "courses": ["CIS 35A"]}
    ]
    """
    logic = metadata.get("logic_structure", [])
    if not logic:
        return []

    formatted = []
    for path in logic:
        course_codes = [c.get("course_letters", "UNKNOWN") for c in path]
        logic_type = "AND" if len(course_codes) > 1 else "OR"
        formatted.append({"type": logic_type, "courses": course_codes})

    return formatted


def explain_if_satisfied(selected_courses: list[str], logic_structure: list[list[dict]]) -> tuple[bool, str]:
    """
    Returns (True, explanation) if selected courses satisfy the logic.
    """
    selected_set = set(course.upper() for course in selected_courses)
    for i, path in enumerate(logic_structure):
        required = set(c.get("course_letters", "").upper() for c in path)
        if required.issubset(selected_set):
            label = f"Option {chr(65 + i)}"
            return True, f"✅ Satisfies {label} with: {', '.join(sorted(required))}"
    return False, "❌ No valid path fully satisfied by the selected courses."


def get_course_summary(metadata: dict) -> str:
    """
    Returns a brief summary of UC + CCC course mapping.
    """
    uc = metadata.get("uc_course", "Unknown")
    ccc = metadata.get("ccc_courses", [])
    logic_desc = render_logic_str(metadata)
    return f"UC Course: {uc}\nCCC Equivalent(s): {', '.join(ccc) or 'None'}\nLogic:\n{logic_desc}"


# Backward-compatible alias
render_logic = render_logic_str
