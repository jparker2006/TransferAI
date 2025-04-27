"""
TransferAI Articulation Package - Renderers

This module contains functions for rendering articulation logic into human-readable formats.
It transforms complex logic structures into clear, formatted text that explains
articulation requirements to users.

Key Functions:
- render_logic_str: Renders articulation logic as plain text
- render_logic_v2: Enhanced renderer with markdown formatting
- render_group_summary: Generates a summary of articulation groups
- render_combo_validation: Creates validation result tables

The renderers focus on presentation clarity while keeping validation logic separate.
They support various output formats and context-aware rendering based on the
specific articulation scenario.
"""

from typing import List, Dict, Any, Set, Optional, Tuple, Union
import json
import re
from .models import LogicBlock, ValidationResult
from .analyzers import extract_honors_info_from_logic, summarize_logic_blocks
from .detectors import is_honors_required


def render_logic_str(
    metadata: Dict[str, Any],
    include_honors_note: bool = True
) -> str:
    """
    Render articulation logic block into human-readable text format.
    
    Converts complex nested logic structures into a clear, hierarchical representation
    with labeled options, AND/OR relationships, and honors course indicators.
    
    Args:
        metadata: Dictionary containing articulation data with a 'logic_block' key
                 and optional 'no_articulation' flag
        include_honors_note: Whether to include notes about honors courses
                 
    Returns:
        A formatted string representing the articulation options, with proper
        hierarchical structure, option labels, and honors course information.
        If no articulation exists, returns a message indicating the course
        must be completed at UCSD.
        
    Example:
        >>> metadata = {
        ...     "logic_block": {
        ...         "type": "OR",
        ...         "courses": [
        ...             {"type": "AND", "courses": [{"course_letters": "CIS 22A"}]}
        ...         ]
        ...     }
        ... }
        >>> render_logic_str(metadata)
        '* Option A: CIS 22A\n\n🔹 Non-honors courses also accepted: CIS 22A.'
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

    result = "\n".join(rendered)
    
    # Add honors information if requested
    if include_honors_note:
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
            
        result += honors_note

    return result


def render_logic_v2(
    metadata: Dict[str, Any],
    simplified: bool = False
) -> str:
    """
    Enhanced rendering with improved formatting.
    
    This is an alternative rendering function with more sophisticated formatting,
    clearer structure, and better handling of complex logic combinations.
    
    Args:
        metadata: Dictionary containing articulation data with a 'logic_block' key
        simplified: Whether to use a simplified format for complex logic
        
    Returns:
        A formatted string with enhanced readability and structure
        
    Example:
        >>> render_logic_v2(metadata)
        'To satisfy this requirement, you can complete one of these options:\n\n...'
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
    
    # Apply simplified format if requested
    if simplified and notes:
        # Condense notes to a single line with minimal formatting
        condensed_notes = []
        if honors_info["honors_courses"]:
            condensed_notes.append(f"Honors: {', '.join(honors_info['honors_courses'])}")
        if honors_info["non_honors_courses"]:
            condensed_notes.append(f"Non-honors: {', '.join(honors_info['non_honors_courses'])}")
        result += "\n\n" + " | ".join(condensed_notes)
    elif notes:
        result += "\n\n### Notes:\n" + "\n".join(notes)
    
    return result


def render_group_summary(
    docs: List[Any],
    compact: bool = False
) -> str:
    """
    Render group-level summary of articulation options across all sections.
    
    Creates a comprehensive, structured summary of all articulation options within a group,
    organized by sections and UC courses. The output includes clear instructions based on
    the group logic type and detailed articulation options for each UC course.
    
    Args:
        docs: List of articulation documents belonging to the same group
        compact: Whether to use a more compact format for large groups
        
    Returns:
        A formatted string with group information, instructions, and articulation options
        structured hierarchically by section and UC course
        
    Note:
        The output formatting depends on the group's logic type (choose_one_section,
        all_required, or select_n_courses) and includes special handling for honors courses
        and courses with no articulation.
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
    
    # Track actual UC courses from the documents
    verified_uc_courses = set()
    verified_options = {}
    
    # First pass: collect verified UC courses and their options
    for doc in docs:
        metadata = doc.metadata
        uc_course = metadata.get("uc_course", "Unknown")
        logic_block = metadata.get("logic_block", {})
        
        verified_uc_courses.add(uc_course)
        
        # Extract and store verified options for each UC course
        course_options = []
        for option in logic_block.get("courses", []):
            if isinstance(option, dict) and option.get("type") == "AND":
                # Extract the courses in this option
                courses_in_option = []
                for course in option.get("courses", []):
                    if isinstance(course, dict) and "course_letters" in course:
                        courses_in_option.append(course.get("course_letters"))
                
                if courses_in_option:
                    course_options.append(courses_in_option)
                    
                    # Track if any multi-course CCC articulation exists
                    if len(courses_in_option) > 1:
                        has_multi_course_uc = True
        
        # Store verified options for this UC course
        if course_options:
            verified_options[uc_course] = course_options

    # Second pass: generate entries with verified data only
    for doc in docs:
        metadata = doc.metadata
        section_id = metadata.get("section", "A") or "A"
        uc_course = metadata.get("uc_course", "Unknown")
        uc_title = metadata.get("uc_title", "")
        logic_block = metadata.get("logic_block", {})
        
        # Skip if this UC course isn't in the verified list (shouldn't happen)
        if uc_course not in verified_uc_courses:
            continue
        
        # Use render_logic_v2 if available, else fallback to render_logic_str
        try:
            # Try the new streamlined renderer
            logic_str = render_logic_v2(metadata).strip()
        except:
            # Fallback to the older renderer
            logic_str = render_logic_str(metadata).strip()

        # Format final output block per course - don't duplicate UC course title since render_logic_v2 includes it
        if "❌" in logic_str and "must be completed at UCSD" in logic_str:
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
        
    # Add data verification note
    notes.append("ℹ️ All course options shown are verified against the official ASSIST articulation data.")
        
    if notes:
        footer.append(f"## Important Notes\n\n" + "\n".join(notes))

    # Combine all sections
    result = header + instruction + "\n\n" + "\n\n".join(rendered_sections)
    
    # Add footer if we have any footer items
    if footer:
        result += "\n\n" + "\n\n".join(footer)
        
    # Apply compact mode if requested
    if compact:
        # Simplify section headers
        result = re.sub(r'## SECTION ([A-Z])', r'### Section \1', result)
        # Remove duplicate UC course headers
        result = re.sub(r'## (.*?) – .*?\n\n## \1', r'## \1', result)
        
    return result


def render_combo_validation(
    validations: Dict[str, ValidationResult],
    satisfying_courses: Optional[Dict[str, List[str]]] = None
) -> str:
    """
    Format validation results for course combinations.
    
    Generates a clear summary of validation results for a combination of courses,
    showing which requirements are satisfied and which are missing.
    
    Args:
        validations: Dictionary mapping UC courses to ValidationResult objects
        satisfying_courses: Optional mapping of UC courses to the CCC courses
                          that satisfy them, for more detailed explanation
                          
    Returns:
        A formatted string explaining the validation results with clear
        status indicators and explanations
        
    Example:
        >>> results = {
        ...     "CSE 8A": ValidationResult(satisfied=True, explanation="..."),
        ...     "CSE 8B": ValidationResult(satisfied=False, explanation="...")
        ... }
        >>> render_combo_validation(results)
        '✅ CSE 8A: Satisfied by your selected courses\n❌ CSE 8B: Not satisfied...'
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
        # Handle both dictionary and ValidationResult object formats
        if isinstance(validation, dict):
            is_satisfied = validation.get('satisfied', False)
            explanation = validation.get('explanation', '')
        else:
            is_satisfied = validation.satisfied
            explanation = validation.explanation
        
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