"""
TransferAI Articulation Package - Validators

This module provides the core validation logic for determining if course selections
satisfy articulation requirements. It handles complex nested logic structures (AND/OR)
and provides detailed explanations for why requirements are or are not satisfied.

Key Functions:
- is_articulation_satisfied: Determines if selected courses satisfy requirements
- explain_if_satisfied: Provides a detailed explanation of validation results
- validate_combo_against_group: Validates courses against group-level requirements

The validators prioritize accuracy and detailed explanation generation to help
users understand exactly how their course selections match articulation requirements.
"""

import re
from typing import List, Dict, Tuple, Union, Any, Optional, Set
from .models import LogicBlock, ValidationResult, CourseOption


def is_articulation_satisfied(
    logic_block: Union[LogicBlock, Dict[str, Any]], 
    selected_courses: List[str],
    honors_pairs: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Determine if selected courses satisfy a logic block.
    
    This is the core validation function that traverses a logic block structure
    and checks if the selected courses satisfy the requirements according to
    the AND/OR logic. It handles nested logic structures recursively.
    
    Args:
        logic_block: A LogicBlock or dict representing articulation requirements
        selected_courses: List of selected course codes to validate
        honors_pairs: Optional mapping of honors to non-honors course equivalents
        
    Returns:
        Dict containing validation results with the following keys:
        - is_satisfied: Boolean indicating if requirements are fully satisfied
        - explanation: Detailed explanation of validation results
        - satisfied_options: List of satisfied articulation options
        - missing_courses: Dictionary mapping options to missing courses
        - redundant_courses: List of redundant/unnecessary courses
        - match_percentage: Overall match percentage across all options
    
    Example:
        >>> logic_block = {"type": "OR", "courses": [
        ...     {"type": "AND", "courses": [{"course_letters": "MATH 1A"}]},
        ...     {"type": "AND", "courses": [{"course_letters": "MATH 1AH"}]}
        ... ]}
        >>> result = is_articulation_satisfied(logic_block, ["MATH 1A"])
        >>> result["is_satisfied"]
        True
    """
    # Ensure logic_block is in a consistent format
    if isinstance(logic_block, LogicBlock):
        logic_block_dict = logic_block.dict()
    else:
        logic_block_dict = logic_block
    
    # For empty logic or dictionary with no_articulation=True, nothing satisfies
    if not logic_block_dict or not isinstance(logic_block_dict, dict) or logic_block_dict.get("no_articulation", False):
        return {
            "is_satisfied": False,
            "explanation": "❌ This course must be completed at UCSD.",
            "satisfied_options": [],
            "missing_courses": {},
            "redundant_courses": [],
            "match_percentage": 0
        }

    # Initialize result structure
    result = {
        'is_satisfied': False,
        'explanation': '',
        'satisfied_options': [],
        'missing_courses': {},
        'redundant_courses': [],
        'match_percentage': 0
    }
    
    # Use explain_if_satisfied to check satisfaction and get detailed explanation
    from .detectors import is_honors_required
    is_satisfied, explanation, redundant_courses = explain_if_satisfied(
        logic_block_dict, selected_courses, honors_pairs=honors_pairs
    )
    
    # Parse the explanation to determine if articulation is satisfied
    if is_satisfied:
        result['is_satisfied'] = True
        result['explanation'] = explanation
        
        # Extract satisfied options from the explanation
        # Example format: "Complete match! Satisfies Option A with: CIS 22A, CIS 22B"
        match = re.search(r"with:\s*([A-Z0-9, ]+)", explanation, re.IGNORECASE)
        if match:
            satisfied_with = match.group(1).strip()
            result['satisfied_options'] = [course.strip() for course in satisfied_with.split(',')]
    else:
        result['is_satisfied'] = False
        result['explanation'] = explanation
        
        # Extract missing requirements from the explanation
        # Example format: "Missing: CIS 22A or CIS 29"
        missing_match = re.search(r"Missing:\s*\*\*([A-Z0-9, ]+)\*\*", explanation, re.IGNORECASE)
        if missing_match:
            missing_courses = missing_match.group(1).strip()
            result['missing_courses'] = {course.strip(): [] for course in missing_courses.split(',')}
    
    # Check if honors are required but not provided
    if is_honors_required(logic_block_dict):
        honors_provided = any(course.upper().strip().endswith('H') for course in selected_courses)
        if not honors_provided:
            if not result['missing_courses']:
                result['missing_courses'] = {"Honors version required": []}
            else:
                result['missing_courses'] = {"Honors version of " + course: [] 
                                           for course in result['missing_courses']}
            
            if result['is_satisfied']:
                # Update to not satisfied if honors requirement was missed
                result['is_satisfied'] = False
                result['explanation'] += " However, an honors course is required."
    
    # Calculate match percentage
    if result['is_satisfied']:
        result['match_percentage'] = 100
    else:
        # If we have partial matches, extract the percentage from the explanation
        partial_match = re.search(r"Partial match \((\d+)%\)", explanation)
        if partial_match:
            result['match_percentage'] = int(partial_match.group(1))
        else:
            result['match_percentage'] = 0
    
    # Store any redundant courses detected
    if redundant_courses:
        result['redundant_courses'] = redundant_courses
    
    return result


def explain_if_satisfied(
    logic_block: Union[LogicBlock, Dict[str, Any]],
    selected_courses: List[str],
    selected_options: Optional[Dict[str, List[str]]] = None,
    indent_level: int = 0,
    honors_pairs: Optional[Dict[str, str]] = None,
    detect_all_redundant: bool = False
) -> Tuple[bool, str, List[List[str]]]:
    """
    Generate detailed explanation of validation results.
    
    This function validates requirements and produces a human-readable explanation
    of whether requirements are satisfied, which courses satisfy which requirements,
    and what requirements are missing.
    
    Args:
        logic_block: A LogicBlock or dict representing articulation requirements
        selected_courses: List of selected course codes to validate
        selected_options: Optional mapping of selected options for tracking paths
        indent_level: Current indentation level for nested explanations
        honors_pairs: Optional mapping of honors to non-honors course equivalents
        detect_all_redundant: Whether to detect all redundant courses
        
    Returns:
        Tuple containing:
        - Boolean indicating if requirements are satisfied
        - Formatted explanation string detailing the validation results
        - List of redundant course groups
    
    Example:
        >>> is_satisfied, explanation, redundant = explain_if_satisfied(
        ...     logic_block, ["MATH 1A", "MATH 1B"]
        ... )
        >>> is_satisfied
        True
        >>> "MATH 1A" in explanation
        True
    """
    # Ensure logic_block is a dict for consistent handling
    if isinstance(logic_block, LogicBlock):
        logic_block_dict = logic_block.dict()
    else:
        logic_block_dict = logic_block
    
    # Normalize selected courses to uppercase for consistent comparison
    selected_set = {c.upper().strip() for c in selected_courses}
    redundant_courses = []

    # Validate the logic block structure
    if not logic_block_dict or not isinstance(logic_block_dict, dict):
        return False, "⚠️ No articulation logic available.", []

    block_type = logic_block_dict.get("type", "OR")
    options = logic_block_dict.get("courses", [])

    # Ensure we have a valid OR block with options
    if block_type != "OR" or not isinstance(options, list) or not options:
        return False, "⚠️ Invalid or empty articulation structure.", []

    # Initialize tracking variables
    all_missing_courses = set()
    feedback_lines = []
    
    # Import detect_redundant_courses here to avoid circular imports
    from .detectors import detect_redundant_courses
    
    # Check for redundant courses using the detector
    redundant_groups = detect_redundant_courses(selected_courses, logic_block_dict)
    
    # Check for additional redundant courses using pattern matching if requested
    if detect_all_redundant:
        # Create a minimal logic block for pattern matching
        pattern_logic_block = {"type": "OR", "courses": []}
        pattern_redundant = detect_redundant_courses(selected_courses, pattern_logic_block)
        
        # Merge the results, avoiding duplicates
        existing_groups = {frozenset(group) for group in redundant_groups}
        for group in pattern_redundant:
            if frozenset(group) not in existing_groups:
                redundant_groups.append(group)
                existing_groups.add(frozenset(group))
    
    # Format explanation for redundant courses if any found
    redundant_note = ""
    if redundant_groups:
        redundant_note = "\n\n⚠️ **Redundant courses detected**:\n"
        for group in redundant_groups:
            redundant_note += f"- Courses **{', '.join(group)}** are equivalent. Only one is needed.\n"

    # Track if any option is satisfied and collect details about partial matches
    any_option_satisfied = False
    satisfied_options = []
    best_partial_match = None
    best_partial_percentage = 0
    partial_matches = []

    # Analyze each option (AND block) in the OR block
    for i, option in enumerate(options):
        label = f"Option {chr(65 + i)}"

        # Ensure valid AND path
        if not isinstance(option, dict) or option.get("type") != "AND":
            feedback_lines.append(f"{label}: ⚠️ Skipped (invalid format).")
            continue

        # Extract required courses for this option
        required = {c.get("course_letters", "").upper() for c in option.get("courses", []) if "course_letters" in c}
        
        # Compare with selected courses
        missing = required - selected_set
        matched = required & selected_set

        # Skip empty options
        if not required:
            feedback_lines.append(f"{label}: ⚠️ Empty option — no courses required?")
            continue

        # Complete match - all required courses are selected
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

            # Add formatted feedback for this partial match
            feedback_lines.append(f"{label}: ⚠️ **Partial match ({int(match_percentage)}%)** — " + 
                                   f"Matched: {', '.join(sorted(matched))} ➡️ " +
                                   f"Still missing: **{', '.join(sorted(missing))}**")
        # No match - all courses are missing
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
        return True, success_msg, redundant_groups

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
            
        return False, partial_msg, redundant_groups

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

    return False, summary, redundant_groups


def validate_combo_against_group(
    ccc_courses: List[str],
    group_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate a set of courses against a complete group.
    
    This function checks if a combination of community college courses satisfies
    the requirements for a group, taking into account the group's logic type
    (choose_one_section, all_required, select_n_courses).
    
    Args:
        ccc_courses: List of community college course codes
        group_data: Dictionary containing group structure and requirements
        
    Returns:
        Dict containing validation results with the following keys:
        - is_fully_satisfied: Boolean indicating if group requirements are fully met
        - partially_satisfied: Boolean indicating if requirements are partially met
        - satisfied_uc_courses: List of UC courses satisfied by the provided CCC courses
        - required_count: Number of courses required (for select_n_courses)
        - satisfied_count: Number of courses satisfied
        - satisfied_section_id: Section ID that is satisfied (for choose_one_section)
        - validation_by_section: Detailed validation results for each section
    
    Example:
        >>> group = {"group_logic_type": "all_required", "sections": [...]}
        >>> results = validate_combo_against_group(["MATH 1A", "MATH 1B"], group)
        >>> results["is_fully_satisfied"]
        True
    """
    import json
    
    # Normalize all CCC courses to uppercase for consistent matching
    ccc_set = {c.upper() for c in ccc_courses}
    
    # Extract key group properties
    logic_type = group_data.get("logic_type", "")
    n_courses = group_data.get("n_courses", 0)
    
    # Initialize tracking variables
    satisfied_uc_courses = []
    unsatisfied_uc_courses = []
    section_matches = {}  # section_id → list of matched UC courses

    # Iterate through each section in the group
    for section in group_data.get("sections", []):
        section_id = section.get("section_id", "default")

        # Check each UC course in this section
        for uc_course in section.get("uc_courses", []):
            uc_name = uc_course.get("name")

            # Safely parse logic_blocks (may be JSON string)
            logic_blocks = uc_course.get("logic_blocks", [])
            if isinstance(logic_blocks, str):
                try:
                    logic_blocks = json.loads(logic_blocks)
                except json.JSONDecodeError:
                    logic_blocks = []

            # Check if any of the logic blocks are satisfied
            matched = False
            for block in logic_blocks:
                if not isinstance(block, dict):
                    continue

                # Direct AND block
                if block.get("type") == "AND":
                    required_courses = set(
                        course.get("course_letters", course.get("name", "")).upper().strip()
                        for course in block.get("courses", [])
                    )
                    if required_courses.issubset(ccc_set):
                        matched = True
                        break

                # OR block containing AND options
                elif block.get("type") == "OR":
                    for subblock in block.get("courses", []):
                        if subblock.get("type") == "AND":
                            required = set(
                                course.get("course_letters", course.get("name", "")).upper().strip()
                                for course in subblock.get("courses", [])
                            )
                            if required.issubset(ccc_set):
                                matched = True
                                break
                    if matched:
                        break

            # Track whether this UC course is satisfied
            if matched:
                satisfied_uc_courses.append(uc_name)
                section_matches.setdefault(section_id, []).append(uc_name)
            else:
                unsatisfied_uc_courses.append(uc_name)

    # Count how many UC courses are satisfied
    satisfied_count = len(satisfied_uc_courses)
    fully_satisfied = False

    # Determine if group requirements are fully satisfied based on logic type
    if logic_type == "all_required":
        fully_satisfied = (len(unsatisfied_uc_courses) == 0)
    elif logic_type == "select_n_courses":
        fully_satisfied = (satisfied_count >= n_courses)
    elif logic_type == "choose_one_section":
        # Must match ALL UC courses from ONE section only
        sections_with_all_courses = [
            sid for sid, matched_courses in section_matches.items()
            if len(matched_courses) == len([
                uc for sec in group_data.get("sections", []) if sec.get("section_id") == sid
                for uc in sec.get("uc_courses", [])
            ])
        ]
        fully_satisfied = len(sections_with_all_courses) == 1
        
        # If we found exactly one satisfied section, update the satisfied_section_id
        if fully_satisfied:
            section_id = sections_with_all_courses[0]

    # Construct the result dictionary
    return {
        "is_fully_satisfied": fully_satisfied,
        "partially_satisfied": satisfied_count > 0 and not fully_satisfied,
        "satisfied_uc_courses": satisfied_uc_courses,
        "unsatisfied_uc_courses": unsatisfied_uc_courses,
        "required_count": n_courses,
        "satisfied_count": satisfied_count,
        "satisfied_section_id": section_id if logic_type == "choose_one_section" and fully_satisfied else None,
        "validation_by_section": section_matches
    }


def validate_uc_courses_against_group_sections(
    user_uc_courses: List[str],
    group_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate user-selected UC courses against group requirements.
    
    This function checks if a set of UC courses satisfies all the requirements
    for a given group, factoring in the group's logic type and section structure.
    This is useful for answering questions like "Does taking CSE 8A and CSE 8B
    satisfy the programming requirement?"
    
    Args:
        user_uc_courses: List of UC course codes specified by the user
        group_data: Dictionary containing group structure and requirements
        
    Returns:
        Dict containing validation results with the following keys:
        - is_fully_satisfied: Boolean indicating if all courses are satisfied in one section
        - satisfied_section_id: Section ID where the courses are satisfied
        - missing_uc_courses: List of UC courses that cannot be satisfied
        - matched_ccc_courses: Dict mapping UC courses to their CCC equivalents
    
    Example:
        >>> results = validate_uc_courses_against_group_sections(
        ...     ["CSE 8A", "CSE 8B"],
        ...     group_data
        ... )
        >>> results["is_fully_satisfied"]
        True
    """
    import json

    # Normalize all user-specified UC courses to uppercase
    user_uc_courses = set(c.upper().strip() for c in user_uc_courses)
    sections = group_data.get("sections", [])

    # Iterate through each section to see if it contains all specified UC courses
    for section in sections:
        section_id = section.get("section_id", "default")
        
        # Get all UC courses in this section that match the user's selection
        uc_courses_in_section = {
            uc["name"].upper().strip(): uc.get("logic_blocks", [])
            for uc in section.get("uc_courses", [])
            if uc.get("name", "").upper().strip() in user_uc_courses
        }

        # If this section doesn't contain all requested UC courses, skip it
        if len(uc_courses_in_section) != len(user_uc_courses):
            continue

        # Track matches for each UC course in this section
        matched_ccc_courses = {}
        missing_uc_courses = []
        is_fully_satisfied = True

        # Check each UC course to see if it has a valid articulation path
        for uc_name, logic_blocks in uc_courses_in_section.items():
            # Normalize logic_blocks into a list of dicts
            if isinstance(logic_blocks, str):
                try:
                    logic_blocks = json.loads(logic_blocks)
                except json.JSONDecodeError:
                    logic_blocks = []
            elif isinstance(logic_blocks, dict):
                logic_blocks = [logic_blocks]
            elif not isinstance(logic_blocks, list):
                logic_blocks = []

            # Track whether this UC course has a valid articulation
            satisfied = False
            ccc_options = []

            # Check each logic block
            for block in logic_blocks:
                if not isinstance(block, dict):
                    continue

                # Simple AND block
                if block.get("type") == "AND":
                    ccc_list = [
                        course.get("course_letters", course.get("name", "")).upper().strip()
                        for course in block.get("courses", [])
                    ]
                    satisfied = True
                    ccc_options.append(ccc_list)
                    break

                # OR block with AND options
                elif block.get("type") == "OR":
                    for subblock in block.get("courses", []):
                        if subblock.get("type") == "AND":
                            ccc_list = [
                                course.get("course_letters", course.get("name", "")).upper().strip()
                                for course in subblock.get("courses", [])
                            ]
                            satisfied = True
                            ccc_options.append(ccc_list)
                            break
                    if satisfied:
                        break

            # Record this UC course as satisfied or not
            if satisfied:
                matched_ccc_courses[uc_name] = ccc_options[0] if ccc_options else []
            else:
                missing_uc_courses.append(uc_name)
                is_fully_satisfied = False

        # If all UC courses in this section are satisfied, return success
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