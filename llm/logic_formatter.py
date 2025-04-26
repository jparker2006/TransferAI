from typing import List, Dict, Tuple, Union
import json
from textwrap import indent
from llama_index_client import Document
import re

def extract_honors_info_from_logic(logic_block):
    """
    Extracts honors course information from a logic block.
    Returns a dictionary with lists of honors and non-honors courses.
    """
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

def render_logic_str(metadata: dict) -> str:
    """
    Render the logic block representing UC-to-CCC course articulation.
    For each path, shows required courses in an easy-to-read format.
    """
    if metadata.get("no_articulation", False) or metadata.get("logic_block", {}).get("no_articulation", False):
        return "❌ This course must be completed at UCSD."

    def resolve_logic_block(block) -> List[str]:
        """Recursively resolve logic block into readable strings."""
        if not block:
            return []

        if block.get("type") == "OR":
            options = []
            for i, option in enumerate(block.get("courses", [])):
                label = f"Option {chr(65 + i)}"
                resolved = resolve_logic_block(option)
                if resolved:
                    if len(resolved) == 1:
                        options.append(f"* {label}: {resolved[0]}")
                    else:
                        options.append(f"* {label}:")
                        options.extend([f"  {item}" for item in resolved])
            return options
        elif block.get("type") == "AND":
            parts = []
            for course in block.get("courses", []):
                parts.extend(resolve_logic_block(course))
            if parts:
                return [" AND ".join(parts)]
            return []
        elif "course_letters" in block:
            code = block.get("course_letters", "").strip()
            if block.get("honors"):
                code += " (Honors)"
            return [code] if code else []
        elif isinstance(block, list):
            if len(block) == 1:
                return resolve_logic_block(block[0])
            if len(block) > 1 and "course_letters" in block[0]:
                codes = [item.get("course_letters", "") for item in block if "course_letters" in item]
                return [f"* {codes[0]}"]
        return []

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
    
    # Add honors requirement warning if needed
    if is_honors_required(block):
        honors_note += "\n\n⚠️ Important: Only honors courses will satisfy this requirement."

    return "\n".join(rendered) + honors_note


def render_group_summary(docs: List) -> str:
    """
    Render a group-level summary of UC-to-CCC course articulation across all sections.
    Uses direct instructional language and clear structure to guide students.
    Ensures each UC course in the group is covered fully. Works with nested logic.
    """
    if not docs:
        return "⚠️ No articulation documents found for this group."

    docs = sorted(docs, key=lambda d: (d.metadata.get("section", ""), d.metadata.get("uc_course", "")))

    section_map = {}
    has_multi_course_uc = False

    # Shared metadata
    group_id = docs[0].metadata.get("group", "")
    group_title = docs[0].metadata.get("group_title", "")
    group_type = docs[0].metadata.get("group_logic_type", "")
    n_courses = docs[0].metadata.get("n_courses")

    # Create a strong header with clear group identification
    header = f"# Group {group_id}{f': {group_title}' if group_title else ''}\n\n"
    
    # Add a clear instruction block based on group type
    if group_type == "choose_one_section":
        instruction = (
            f"**COMPLETE ONE FULL SECTION**: Choose exactly ONE section (A, B, etc.) "
            f"and complete ALL UC courses within that section only. Do not mix courses between sections.\n\n"
        )
    elif group_type == "all_required":
        instruction = (
            f"**COMPLETE ALL COURSES**: You must satisfy EVERY UC course listed below. "
            f"Each course has its own articulation options.\n\n"
        )
    elif group_type == "select_n_courses" and n_courses:
        instruction = (
            f"**SELECT {n_courses} COURSE{'S' if n_courses > 1 else ''}**: Choose exactly {n_courses} "
            f"UC course{'s' if n_courses > 1 else ''} from the list below and complete the articulation requirements "
            f"for {'each' if n_courses > 1 else 'that course'}.\n\n"
        )
    else:
        instruction = "**FOLLOW THE REQUIREMENTS BELOW**: Complete the articulation requirements as specified.\n\n"

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

        # Use render_logic_v2 if available, else fallback to render_logic_str
        try:
            # Use the enhanced renderer that includes UC titles and better formatting
            logic_str = render_logic_v2(metadata).strip()
        except:
            # Fallback to the older renderer
        logic_str = render_logic_str(metadata).strip()

        # Format final output block per course - don't duplicate UC course title since render_logic_v2 includes it
        if "❌" in logic_str and "must be completed at UCSD" in logic_str:
            # For courses that must be taken at UCSD, use a distinctive format
            if not "##" in logic_str:  # If render_logic_v2 didn't add a header
                full_entry = f"## {uc_course}{f' – {uc_title}' if uc_title else ''}\n\n❌ **This course must be completed at UCSD.**"
        else:
                full_entry = logic_str
        else:
            # For normal articulation courses
            if not "##" in logic_str:  # If render_logic_v2 didn't add a header
                full_entry = f"## {uc_course}{f' – {uc_title}' if uc_title else ''}\n\n{logic_str}"
            else:
                full_entry = logic_str

        # Append to section or flat list
        if group_type == "choose_one_section":
            section_map.setdefault(section_id, []).append((uc_course, full_entry))
        else:
            course_entries.append((uc_course, full_entry))

    # Format display
    rendered_sections = []

    if group_type == "choose_one_section":
        for section_id, entries in sorted(section_map.items()):
            sorted_blocks = sorted(entries, key=lambda x: x[0])
            section_body = "\n\n".join([block for _, block in sorted_blocks])
            
            # Add clear section header and instruction
            section_header = f"## SECTION {section_id}\n\n"
            section_instruction = f"**Complete ALL of these UC courses using the articulation options listed:**\n\n"
            rendered_sections.append(f"{section_header}{section_instruction}{section_body}")
    else:
        # Sort by course name like "CSE 20", "MATH 18", etc.
        sorted_blocks = sorted(course_entries, key=lambda x: x[0])
        rendered_sections = [block for _, block in sorted_blocks]

    # Footer with summary and important warnings
    footer = []
    
    # Direct instructions for completing the requirements
    if group_type == "choose_one_section":
        footer.append(
            f"## What You Need To Do\n\n"
            f"1. Choose **exactly ONE section** from above (A, B, etc.)\n"
            f"2. Within your chosen section, complete **ALL UC courses** listed\n"
            f"3. For each UC course, follow one complete articulation option\n"
            f"4. **Do not mix** courses between different sections"
        )
    elif group_type == "all_required":
        footer.append(
            f"## What You Need To Do\n\n"
            f"1. Complete **ALL UC courses** listed above\n"
            f"2. For each UC course, follow one complete articulation option\n"
            f"3. You can choose different articulation options for different UC courses"
        )
    elif group_type == "select_n_courses" and n_courses:
        footer.append(
            f"## What You Need To Do\n\n"
            f"1. Select **exactly {n_courses}** UC course{'s' if n_courses > 1 else ''} from the list above\n"
            f"2. For each selected UC course, follow one complete articulation option\n"
            f"3. You can choose any {n_courses} course{'s' if n_courses > 1 else ''} from the list"
        )

    # Important notes section
    notes = []

    if has_multi_course_uc:
        notes.append("⚠️ Some options require **multiple CCC courses** to satisfy a single UC course. You must complete ALL courses listed in these options.")
        
    if notes:
        footer.append(f"## Important Notes\n\n" + "\n".join(notes))

    # Combine all sections
    result = header + instruction + "\n\n" + "\n\n".join(rendered_sections)
    
    # Add footer if we have any footer items
    if footer:
        result += "\n\n" + "\n\n".join(footer)
        
    return result

def explain_if_satisfied(logic_block, selected_courses, selected_options=None, indent_level=0, honors_pairs=None, detect_all_redundant=False):
    """
    Determine if the selected CCC courses satisfy any full articulation path
    in the logic_block. Returns True if satisfied, or False with clear breakdown of missing courses.
    
    Args:
        logic_block: The logic block representing the UC course articulation
        selected_courses: List of CCC courses to check
        selected_options: Optional list of pre-selected options to check
        indent_level: Indentation level for formatting output
        honors_pairs: Optional dictionary of honors/non-honors equivalent pairs
        detect_all_redundant: If True, detect redundant courses even if they aren't in the logic block
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
    
    # Check for redundant courses two ways:
    # 1. Within the logic block structure
    redundant_groups = detect_redundant_courses(selected_courses, logic_block)
    
    # 2. Using pattern matching if requested (for courses not in the logic block)
    if detect_all_redundant:
        # Create a minimal logic block for pattern matching only
        pattern_logic_block = {"type": "OR", "courses": []}
        pattern_redundant = detect_redundant_courses(selected_courses, pattern_logic_block)
        
        # Merge the results, avoiding duplicates
        existing_groups = {frozenset(group) for group in redundant_groups}
        for group in pattern_redundant:
            if frozenset(group) not in existing_groups:
                redundant_groups.append(group)
                existing_groups.add(frozenset(group))
    
    redundant_note = ""
    if redundant_groups:
        redundant_note = "\n\n⚠️ **Redundant courses detected**:\n"
        for group in redundant_groups:
            redundant_note += f"- Courses **{', '.join(group)}** are equivalent. Only one is needed.\n"

    # Track if any option is satisfied to report redundancy
    any_option_satisfied = False
    satisfied_options = []
    best_partial_match = None
    best_partial_percentage = 0
    
    # For better partial match visualization
    partial_matches = []

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

        # Complete match - all required courses are in selected_set
        if required.issubset(selected_set):
            any_option_satisfied = True
            satisfied_options.append((label, sorted(matched)))
        # Partial match - calculate percentage complete
        elif matched:
            match_percentage = len(matched) / len(required) * 100
            partial_matches.append({
                "label": label,
                "matched": sorted(matched),
                "missing": sorted(missing),
                "percentage": match_percentage,
                "required": sorted(required)
            })
            
            # Track the best partial match
            if match_percentage > best_partial_percentage:
                best_partial_percentage = match_percentage
                best_partial_match = {
                    "label": label,
                    "matched": sorted(matched),
                    "missing": sorted(missing),
                    "percentage": match_percentage
                }
                
            # Add to overall missing courses
        all_missing_courses.update(missing)

            # Add formatted feedback
            feedback_lines.append(f"{label}: ⚠️ **Partial match ({int(match_percentage)}%)** — " + 
                                   f"Matched: {', '.join(sorted(matched))} ➡️ " +
                                   f"Still missing: **{', '.join(sorted(missing))}**")
        else:
            all_missing_courses.update(missing)
            feedback_lines.append(f"{label}: 🚫 No matching courses taken — requires: {', '.join(sorted(required))}")

    # After checking all options, return the appropriate result
    if any_option_satisfied:
        # Format the success message
        if len(satisfied_options) == 1:
            label, matched = satisfied_options[0]
            success_msg = f"✅ **Complete match!** Satisfies {label} with: {', '.join(matched)}"
        else:
            success_msg = "✅ **Complete match!** Satisfies multiple options:\n"
            for label, matched in satisfied_options:
                success_msg += f"- {label}: {', '.join(matched)}\n"
            
        # Add redundant course info if applicable
        if redundant_note:
            success_msg += redundant_note
        return True, success_msg

    # If no options were fully satisfied but we have partial matches
    if partial_matches:
        # Sort by highest percentage complete
        partial_matches.sort(key=lambda x: x["percentage"], reverse=True)
        best_match = partial_matches[0]
        
        # Create a progress bar for visualization (10 characters wide)
        progress_chars = int(best_match["percentage"] / 10)
        progress_bar = "█" * progress_chars + "░" * (10 - progress_chars)
        
        # Format the partial match message
        partial_msg = f"⚠️ **Partial match ({int(best_match['percentage'])}%)** [{progress_bar}]\n\n"
        partial_msg += f"**Best option: {best_match['label']}**\n"
        partial_msg += f"✓ Matched: {', '.join(best_match['matched'])}\n"
        partial_msg += f"✗ Missing: **{', '.join(best_match['missing'])}**\n\n"
        
        # Add details about other potential options
        if len(partial_matches) > 1:
            partial_msg += "Other partial matches:\n"
            for i, match in enumerate(partial_matches[1:3]):  # Show up to 3 alternatives
                partial_msg += f"- {match['label']} ({int(match['percentage'])}%): Missing {', '.join(match['missing'])}\n"
        
        # Add redundant course info if applicable
        if redundant_note:
            partial_msg += redundant_note
            
        return False, partial_msg

    # If no options were satisfied at all
    summary = "❌ **No complete or partial matches found.**"
    if all_missing_courses:
        summary += f"\n\nYou need at least one of these course combinations:"
        for i, line in enumerate(feedback_lines):
            if "requires" in line:
                option, requirements = line.split("requires:")
                summary += f"\n- {requirements.strip()}"
    
    # Add redundant course info to the failure summary
    if redundant_note:
        summary += redundant_note

    return False, summary
    
def is_articulation_satisfied(logic_block, selected_courses, honors_pairs=None):
    """
    Validates if CCC courses satisfy a UC course articulation requirement.
    
    Args:
        logic_block: The logic block representing the UC course articulation
        selected_courses: List of CCC courses to validate against the articulation
        honors_pairs: Optional dictionary of honors/non-honors equivalent pairs
    
    Returns:
        Dictionary with:
        - is_satisfied: Boolean indicating if articulation is satisfied
        - explanation: String explaining validation result
        - missing: List of course types or specific courses still needed
        - satisfied_options: List of satisfied articulation options
        - selected_courses: The courses that were used in the validation
    """
    # Initialize result structure
    result = {
        'is_satisfied': False,
        'explanation': '',
        'missing': [],
        'satisfied_options': [],
        'selected_courses': selected_courses.copy() if selected_courses else []
    }
    
    # Handle edge cases
    if not logic_block:
        result['explanation'] = "No articulation data available for this course."
        return result
    
    if logic_block.get("no_articulation", False):
        result['explanation'] = "This UC course has no CCC articulation available."
        return result
    
    # Use existing explain_if_satisfied function to check satisfaction
    is_satisfied, explanation = explain_if_satisfied(logic_block, selected_courses, honors_pairs=honors_pairs)
    
    # Parse the explanation to determine if articulation is satisfied
    if is_satisfied:
        result['is_satisfied'] = True
        result['explanation'] = explanation
        
        # Extract satisfied options
        # Example format: "Requirement satisfied with: CIS 22A, CIS 22B"
        match = re.search(r"with:\s*([A-Z0-9, ]+)", explanation, re.IGNORECASE)
        if match:
            satisfied_with = match.group(1).strip()
            result['satisfied_options'] = [course.strip() for course in satisfied_with.split(',')]
    else:
        result['is_satisfied'] = False
        result['explanation'] = explanation
        
        # Extract missing requirements
        # Example format: "Requirement not satisfied. Still missing: CIS 22A or CIS 29"
        missing_match = re.search(r"missing:\s*([A-Z0-9, ]+)", explanation, re.IGNORECASE)
        if missing_match:
            missing_courses = missing_match.group(1).strip()
            result['missing'] = [course.strip() for course in missing_courses.split(',')]
    
    # Check if honors are required but not provided
    if is_honors_required(logic_block):
        honors_provided = any(course.endswith('H') for course in selected_courses)
        if not honors_provided:
            if not result['missing']:
                result['missing'] = ["Honors version required"]
            else:
                result['missing'] = ["Honors version of " + course for course in result['missing']]
            
            if result['is_satisfied']:
                # Update to not satisfied if honors requirement was missed
                result['is_satisfied'] = False
                result['explanation'] += " However, an honors course is required."
    
    return result

def render_combo_validation(validations, satisfying_courses=None):
    """
    Visualizes validation results for multiple UC courses.
    
    Args:
        validations: Dictionary mapping UC course codes to validation result dicts
                    Each validation dict should have 'is_satisfied' and 'explanation' fields
        satisfying_courses: Optional dictionary mapping UC courses to lists of CCC courses
                           that satisfy them
    
    Returns:
        A formatted validation summary as a string
    """
    if not validations:
        return "No validation results to display."
    
    # Sort UC courses for consistent output
    uc_courses = sorted(validations.keys())
    
    # Table header
    table = ["| UC Course | Status | Missing Courses | Satisfied By |"]
    table.append("|----------|--------|----------------|-------------|")
    
    # Track overall status
    all_satisfied = True
    
    # Build table rows
    for uc in uc_courses:
        validation = validations[uc]
        is_satisfied = validation.get('is_satisfied', False)
        explanation = validation.get('explanation', '')
        
        if not is_satisfied:
            all_satisfied = False
            # Extract missing courses from the explanation
            missing_match = re.search(r"missing:\s*([A-Z0-9, ]+)", explanation, re.IGNORECASE)
            missing = missing_match.group(1) if missing_match else "N/A"
            status = "❌"
            satisfied_by = "None"
        else:
            missing = "None"
            status = "✅"
            # Get list of satisfying courses
            if satisfying_courses and uc in satisfying_courses:
                satisfied_by = ", ".join(satisfying_courses[uc])
            else:
                # Extract satisfying courses from explanation
                match = re.search(r"with:\s*([A-Z0-9, ]+)", explanation, re.IGNORECASE)
                satisfied_by = match.group(1) if match else "N/A"
        
        table.append(f"| {uc} | {status} | {missing} | {satisfied_by} |")
    
    # Summary line
    if all_satisfied:
        summary = "✅ All UC course requirements are satisfied."
    else:
        summary = "❌ Some UC course requirements are not satisfied."
    
    return summary + "\n\n" + "\n".join(table)

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

def explain_honors_equivalence(course1, course2):
    """
    Returns standardized phrasing for honors/non-honors equivalence.
    Always lists the honors course first for consistency.
    
    Args:
        course1: First course code (e.g., "MATH 1A")
        course2: Second course code (e.g., "MATH 1AH")
        
    Returns:
        Standardized explanation string
    """
    def normalize(course):
        return course.strip().upper()
    
    def is_honors(course):
        return course.endswith("H")
    
    norm_course1 = normalize(course1)
    norm_course2 = normalize(course2)
    
    # Always put honors course first
    if is_honors(norm_course2) and not is_honors(norm_course1):
        honors_course, regular_course = norm_course2, norm_course1
    else:
        honors_course, regular_course = norm_course1, norm_course2
    
    return f"{honors_course} and {regular_course} are equivalent for UC transfer credit. You may choose either."

def get_uc_courses_satisfied_by_ccc(ccc_course, all_docs):
    """
    Return UC courses that are satisfied by this CCC course **alone**.
    Only includes options where this course appears alone in an AND block.
    """
    matched_uc_courses = set()

    for doc in all_docs:
        logic_blocks = doc.metadata.get("logic_block", [])
        if isinstance(logic_blocks, dict):
            logic_blocks = [logic_blocks]

        for block in logic_blocks:
            if block.get("type") != "OR":
                continue

            for and_option in block.get("courses", []):
                if and_option.get("type") != "AND":
                    continue

                course_list = and_option.get("courses", [])
                if (
                    len(course_list) == 1 and
                    course_list[0].get("course_letters", "").strip().upper() == ccc_course.strip().upper()
                ):
                    matched_uc_courses.add(doc.metadata.get("uc_course", ""))

    return sorted(matched_uc_courses)

def get_uc_courses_requiring_ccc_combo(ccc_course, all_docs):
    contributing_uc_courses = set()

    for doc in all_docs:
        logic_blocks = doc.metadata.get("logic_block", [])
        if isinstance(logic_blocks, dict):
            logic_blocks = [logic_blocks]

        for block in logic_blocks:
            if block.get("type") != "OR":
                continue

            for and_option in block.get("courses", []):
                if and_option.get("type") != "AND":
                    continue

                course_list = and_option.get("courses", [])
                if any(
                    course.get("course_letters", "").strip().upper() == ccc_course.strip().upper()
                    for course in course_list
                ) and len(course_list) > 1:
                    contributing_uc_courses.add(doc.metadata.get("uc_course", ""))

    return sorted(contributing_uc_courses)

def count_uc_matches(ccc_course, docs):
    """
    Counts and lists all UC courses satisfied by this CCC course.
    
    Args:
        ccc_course: A CCC course code (e.g., "CIS 36A")
        docs: List of Document objects containing articulation logic
        
    Returns:
        Tuple of (count of direct matches, list of direct matches, list of combination matches)
        Where combination matches shows courses where this CCC is part of a combination
        but not counted as a direct match.
    """
    # Find UC courses where this CCC course is a direct match
    direct_matches = get_uc_courses_satisfied_by_ccc(ccc_course, docs)
    
    # Find UC courses where this CCC course is part of a combination
    contributing_matches = get_uc_courses_requiring_ccc_combo(ccc_course, docs)
    
    # Remove any overlap (courses that are both direct matches and combo matches)
    # We only want to show unique contribution matches
    contributing_only = [uc for uc in contributing_matches if uc not in direct_matches]
    
    return (len(direct_matches), direct_matches, contributing_only)

def render_binary_response(is_satisfied, explanation, course=None):
    """
    Renders a standardized binary (yes/no) response with enhanced visual formatting.
    
    Args:
        is_satisfied: Boolean indicating whether the requirement is satisfied
        explanation: Explanation text to include after the header
        course: Optional UC course code to include in the header
        
    Returns:
        Formatted response string with standardized header and explanation
    """
    # Create a visually distinctive header
    if is_satisfied:
        header = "# ✅ Yes, based on official articulation"
    else:
        header = "# ❌ No, based on verified articulation logic"
    
    # Add course information if provided
    if course:
        header += f" - {course}"
    
    # Format the explanation with markdown for better readability
    formatted_explanation = explanation
    
    # Add highlighting to key terms in the explanation
    key_terms = [
        "satisfies", "satisfied", "missing", "required", "honors", 
        "articulation", "option", "course", "section", "Group"
    ]
    
    for term in key_terms:
        if term in formatted_explanation and term not in ["the", "and", "or", "with"]:
            formatted_explanation = formatted_explanation.replace(
                f" {term} ", f" **{term}** "
            )
    
    # Ensure proper spacing between sections
    if not formatted_explanation.startswith("\n"):
        formatted_explanation = "\n\n" + formatted_explanation
    
    # For binary yes/no questions with just a course name, provide a clearer answer
    if course and explanation.strip() == "":
        if is_satisfied:
            formatted_explanation = f"\n\nYes, {course} is satisfied by the articulation options shown above."
        else:
            formatted_explanation = f"\n\nNo, {course} has no articulation at this institution and must be completed at UCSD."
        
    return f"{header}{formatted_explanation}"

def detect_redundant_courses(selected_courses, logic_block):
    """
    Detects redundant courses (courses that satisfy the same requirement).
    Returns a list of groups of redundant courses.
    
    A course is considered redundant when:
    1. It appears in the same articulation path as another course (same option group)
    2. It's an honors/non-honors pair (e.g., COURSE vs COURSE+H)
    """
    if not logic_block or not isinstance(logic_block, dict) or not selected_courses:
        return []

    # Normalize the selected courses
    selected_courses = [c.upper().strip() for c in selected_courses]
    
    # Initialize redundant groups
    redundant_groups = []
    
    # First pass: Extract course options from logic block
    course_options = {}
    
    if logic_block.get("type") == "OR":
        for i, option in enumerate(logic_block.get("courses", [])):
            # Process AND blocks with single courses (direct equivalents)
            if isinstance(option, dict) and option.get("type") == "AND" and len(option.get("courses", [])) == 1:
                course = option["courses"][0].get("course_letters", "").upper().strip()
                if course:
                    course_options.setdefault(course, []).append(i)
    
    # Second pass: Find courses that satisfy the same options
    course_groups = {}
    for course, options in course_options.items():
        if course in selected_courses:
            option_key = tuple(sorted(options))
            course_groups.setdefault(option_key, []).append(course)
    
    # Add redundant courses from common option groups
    for courses in course_groups.values():
        if len(courses) > 1:
            redundant_groups.append(sorted(courses))
    
    # Third pass: Look for honors/non-honors pairs not caught by option matching
    # Create a set of courses we've already identified as redundant
    already_grouped = {course for group in redundant_groups for course in group}
    
    # Check each pair of selected courses
    for i, course1 in enumerate(selected_courses):
        if course1 in already_grouped:
            continue
            
        for j in range(i+1, len(selected_courses)):
            course2 = selected_courses[j]
            if course2 in already_grouped:
                continue
                
            # Check if this is an honors/non-honors pair
            if (course2 == course1 + "H") or (course1 == course2 + "H"):
                # One is the honors version of the other
                redundant_groups.append(sorted([course1, course2]))
                already_grouped.add(course1)
                already_grouped.add(course2)
                break
    
    return redundant_groups

def is_honors_required(logic_block):
    """
    Returns True if only honors options exist in articulation logic.
    If any non-honors option is available, honors are not required.
    """
    if not logic_block:
        return False
    
    # Check for no articulation
    if logic_block.get("no_articulation", False):
        return False
        
    # Convert single block to list if needed
    blocks = [logic_block] if isinstance(logic_block, dict) else logic_block
        
    all_options_require_honors = True
    has_options = False
    
    # For each OR block
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "OR":
            continue
            
        # Check each option (usually AND blocks)
        for option in block.get("courses", []):
            has_options = True
            if not isinstance(option, dict) or option.get("type") != "AND":
                continue
                
            # Check if this option contains any non-honors courses
            option_courses = option.get("courses", [])
            if not option_courses:
                continue
                
            # If ANY course in this option is non-honors, then honors are not required for this option
            if any(not course.get("honors", False) for course in option_courses if isinstance(course, dict)):
                all_options_require_honors = False
                break
                
        if not all_options_require_honors:
            break
            
    # Only return True if there are options and all require honors
    return has_options and all_options_require_honors

def summarize_logic_blocks(logic_block):
    """
    Generates quick metadata summaries for articulation logic.
    
    Args:
        logic_block: A logic block dictionary structure
        
    Returns:
        Dictionary with metadata about the articulation logic:
        - option_count: Number of distinct articulation options
        - multi_course_options: Count of options requiring multiple CCC courses
        - honors_required: Whether only honors courses satisfy the requirement
        - has_honors_options: Whether any honors courses are present in options
        - min_courses_required: Minimum number of CCC courses needed
    """
    if not logic_block or not isinstance(logic_block, dict):
        return {
            "option_count": 0,
            "multi_course_options": 0,
            "honors_required": False,
            "has_honors_options": False,
            "min_courses_required": 0,
            "no_articulation": True
        }
    
    # Check if there's no articulation available
    if logic_block.get("no_articulation", False):
        return {
            "option_count": 0,
            "multi_course_options": 0,
            "honors_required": False,
            "has_honors_options": False,
            "min_courses_required": 0,
            "no_articulation": True
        }
    
    option_count = 0
    multi_course_options = 0
    min_course_count = float('inf')
    honors_courses_found = False
    
    # Process the logic block
    if logic_block.get("type") == "OR":
        for option in logic_block.get("courses", []):
            option_count += 1
            
            if isinstance(option, dict) and option.get("type") == "AND":
                courses = option.get("courses", [])
                course_count = len(courses)
                
                # Track multi-course options
                if course_count > 1:
                    multi_course_options += 1
                
                # Track minimum course count
                if course_count < min_course_count:
                    min_course_count = course_count
                
                # Check for honors courses
                for course in courses:
                    if isinstance(course, dict) and course.get("honors", False):
                        honors_courses_found = True
    
    # Determine if only honors courses are accepted
    honors_required = is_honors_required(logic_block)
    
    # Adjust minimum course count for edge cases
    if min_course_count == float('inf'):
        min_course_count = 0
    
    return {
        "option_count": option_count,
        "multi_course_options": multi_course_options,
        "honors_required": honors_required,
        "has_honors_options": honors_courses_found,
        "min_courses_required": min_course_count,
        "no_articulation": False
    }

# Backward-compatible alias for default rendering
render_logic = render_logic_str

def render_logic_v2(metadata):
    """
    Enhanced version of render_logic_str with more concise formatting.
    Groups options better and makes the UC course more prominent.
    Includes clear labeling for complete vs. partial options.
    """
    # Handle no articulation case
    if metadata.get("no_articulation", False) or metadata.get("logic_block", {}).get("no_articulation", False):
        reason = metadata.get("no_articulation_reason", "No articulation available")
        return f"❌ This course must be completed at UCSD.\n\nReason: {reason}"
    
    # Get UC course info for header
    uc_course = metadata.get("uc_course", "")
    uc_title = metadata.get("uc_title", "")
    
    # Add a prominent header with UC course info
    header = f"## {uc_course}{f' – {uc_title}' if uc_title else ''}\n\n"
    
    block = metadata.get("logic_block", {})
    options = []
    summary = summarize_logic_blocks(block)
    
    # Start with a quick summary 
    options_summary = f"**Available Options**: {summary['option_count']} "
    options_summary += f"({summary['multi_course_options']} requiring multiple courses)\n"
    
    if block.get("type") == "OR":
        # Group options based on course count
        single_course_options = []
        multi_course_options = []
        
        for i, option in enumerate(block.get("courses", [])):
            label = f"Option {chr(65 + i)}"
            
            if isinstance(option, dict) and option.get("type") == "AND":
                courses = option.get("courses", [])
                
                # Handle multi-course options
                if len(courses) > 1:
                    course_codes = [c.get("course_letters", "UNKNOWN") for c in courses]
                    multi_course_options.append(
                        f"**{label} (✅ Complete option)**: {', '.join(course_codes)} (complete all)"
                    )
                # Handle single-course options
                elif courses:
                    course = courses[0]
                    is_honors = course.get("honors", False)
                    code = course.get("course_letters", "UNKNOWN")
                    honor_indicator = " (honors)" if is_honors else ""
                    single_course_options.append(
                        f"**{label} (✅ Complete option)**: {code}{honor_indicator}"
                    )
        
        # Add single-course options section if any exist
        if single_course_options:
            options.append("### Single Course Options:")
            options.extend(single_course_options)
        
        # Add multi-course options section if any exist
        if multi_course_options:
            if single_course_options:
                options.append("\n### Multiple Course Options:")
            else:
                options.append("### Multiple Course Options:")
            options.extend(multi_course_options)
    
    # Extract honors information from the logic block
    honors_info = extract_honors_info_from_logic(block)
    
    # Format the result with the new hierarchical structure
    result = header + options_summary + "\n" + "\n".join(options)
    
    # Add special notes section for honors and requirements
    notes = []
    
    # Add honors notes if applicable
    if honors_info["honors_courses"]:
        notes.append(f"🔹 Honors courses accepted: {', '.join(honors_info['honors_courses'])}")
    if honors_info["non_honors_courses"]:
        notes.append(f"🔹 Non-honors courses also accepted: {', '.join(honors_info['non_honors_courses'])}")
    
    # Add honors requirement warning if needed
    if is_honors_required(block):
        notes.append("\n⚠️ **Important**: Only honors courses will satisfy this requirement")
    
    # Add notes section if we have any notes
    if notes:
        result += "\n\n### Notes:\n" + "\n".join(notes)
    
    return result