from __future__ import annotations
import json
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import argparse
import urllib.parse
import uuid


def hash_id(s: str) -> str:
    """Generate a short hash ID for a string."""
    return hashlib.md5(s.encode("utf-8")).hexdigest()[:8]


def extract_course_letters_and_title(full_name: str) -> Tuple[str, str]:
    """Extract course code and title from a full course name."""
    parts = full_name.strip().split(" ", 2)
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}", parts[2] if len(parts) == 3 else ""
    return full_name.strip(), ""


def slugify(name: str) -> str:
    """Convert a string to a URL-friendly slug."""
    name = name.lower().replace('&', 'and')
    name = name.replace('.', '')  # Remove periods like in "B.S."
    name = re.sub(r'[^a-z0-9]+', '_', name)
    return re.sub(r'_+', '_', name).strip('_')


def infer_group_logic_type(instruction: Dict[str, Any], section_count: int, advisements: List[Dict[str, Any]] = None) -> Tuple[str, Optional[int]]:
    """
    Determine the logic type of a group based on its instruction and advisements.
    
    Args:
        instruction: The instruction object from the ASSIST JSON
        section_count: Number of sections in the group
        advisements: List of advisement objects
        
    Returns:
        Tuple of (logic_type, n_courses) where n_courses is only set for select_n_courses
    """
    # Check advisements first (highest priority)
    if advisements:
        for advisement in advisements:
            if advisement.get("type") == "NFollowing" and advisement.get("selectionType") == "Select":
                amount = int(float(advisement.get("amount", 1)))
                return "select_n_courses", amount
    
    # If we have a proper instruction object
    if isinstance(instruction, dict):
        conjunction = instruction.get("conjunction", "")
        selection_type = instruction.get("selectionType", "")
        
        # === Priority Check for Section Choice ===
        # If instruction implies choosing between alternatives ('Or') AND there are multiple sections,
        # infer 'choose_one_section' regardless of 'selectionType'.
        # This handles cases like "Select A or B" or "Complete A or B" structures with multiple sections.
        # Specifically target the common pattern where ASSIST uses Or/Select for section choices.
        if conjunction == "Or" and section_count > 1:
             # This could be refined later if ASSIST introduces "Select N sections"
             # but currently Or/Select with multiple sections means choose 1 section.
            if selection_type == "Select" or selection_type == "Complete":
                 return "choose_one_section", None # n_courses is None/irrelevant

        # --- Standard Instruction Checks (if not overridden by section choice) ---

        # Complete A or B type structure (typically only one section, handled above if > 1)
        if conjunction == "Or" and selection_type == "Complete" and section_count <= 1:
             # Should ideally not happen with section_count > 1 due to check above
             # If it's one section or less, treat as single section choice (or default)
            return "choose_one_section", None # Or maybe "all_required" if section_count == 1? Revisit if needed.

        # Complete all sections
        if conjunction == "And" and selection_type == "Complete":
            return "all_required", None

        # Select N courses (only if not already identified as choose_one_section)
        if selection_type == "Select":
            amount = int(float(instruction.get("amount", 1)))
            return "select_n_courses", amount
    
    # Legacy string-based inference as fallback
    if isinstance(instruction, str):
        instruction_text = instruction.lower()
        
        if "select" in instruction_text and "course" in instruction_text:
            # Try to extract the number
            match = re.search(r"select\s+(\d+)\s+courses?", instruction_text)
            if match:
                return "select_n_courses", int(match.group(1))
            return "select_n_courses", 1
            
        if "all required" in instruction_text or "required" in instruction_text:
            return "all_required", None
            
        if section_count >= 2 and "or" in instruction_text:
            return "choose_one_section", None
            
        if "complete" in instruction_text and "or" in instruction_text:
            return "choose_one_section", None
    
    # Safe fallback: one section = all required
    # If multiple sections exist but no clear instruction matched, default to all_required? Or choose_one_section?
    # Let's default to all_required for safety, as choose_one_section is explicitly checked above.
    if section_count == 1:
        return "all_required", None
    else:
        # If section_count > 1 and we got here, no clear instruction was found.
        # Defaulting to all_required might be safer than assuming a choice.
        # Re-evaluate if this causes issues.
        return "all_required", None


def infer_required_course_count(instruction: str) -> int:
    """Extract the number of required courses from an instruction."""
    match = re.search(r"select\s+(\d+)\s+courses?", instruction.lower())
    return int(match.group(1)) if match else 1


def extract_json_value(json_str: str, key: str) -> str:
    """Extract a value from a JSON string by key."""
    match = re.search(f'"{key}":"([^"]+)"', json_str)
    if match:
        return match.group(1)
    return ""


def parse_sending_articulation(articulation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the sending articulation section of an ASSIST JSON object.
    
    Args:
        articulation: The sending articulation section from ASSIST JSON
        
    Returns:
        Structured representation of the OR logic with nested AND groups
    """
    # Handle empty articulation or no articulated items
    if not articulation or "items" not in articulation or not articulation["items"]:
        reason = "No Course Articulated"  # Default reason
        specific_reason_text = articulation.get("noArticulationReason") if articulation else None
        
        if specific_reason_text and specific_reason_text.strip():
            reason = specific_reason_text.strip()
            
        return {
            "type": "OR", 
            "courses": [{
                "name": reason,
                "honors": False,
                "course_id": hash_id(reason), # Hash the reason for a consistent ID
                "course_letters": "N/A",
                "title": reason
            }],
            "no_articulation": True,
            "no_articulation_reason": reason # Store the specific or default reason
        }
    
    # First, check if we have course group conjunctions specified
    course_group_conjunctions = articulation.get("courseGroupConjunctions", [])
    
    # If we have AND conjunctions between course groups, we need to handle them specially
    if course_group_conjunctions:
        and_group_definitions = []
        
        # Map positions to create groups of items that should be joined with AND
        for conjunction in course_group_conjunctions:
            if conjunction.get("groupConjunction") == "And":
                begin_pos = conjunction.get("sendingCourseGroupBeginPosition", 0)
                end_pos = conjunction.get("sendingCourseGroupEndPosition", 0)
                # Only add valid ranges
                if end_pos >= begin_pos:
                    and_group_definitions.append((begin_pos, end_pos))
        
        # If we found valid AND group definitions, process them
        if and_group_definitions:
            or_paths = []
            
            for begin_pos, end_pos in and_group_definitions:
                # Collect all courses from the range of positions
                all_courses_in_and_group = []
                
                # Process each item in the specified position range
                for pos in range(begin_pos, end_pos + 1):  # +1 to include end position
                    for item in articulation["items"]:
                        if item.get("position") == pos and "items" in item:
                            # Extract courses from this course group
                            for course_data in item["items"]:
                                if "courseIdentifierParentId" not in course_data:
                                    continue
                                
                                # Extract course information
                                prefix = course_data.get("prefix", "")
                                number = course_data.get("courseNumber", "")
                                title = course_data.get("courseTitle", "")
                                full_name = f"{prefix} {number} {title}"
                                
                                # Determine if the course is an honors version
                                is_honors = "HONORS" in title.upper() or title.upper().endswith("H")
                                
                                # Create a standardized course object
                                course_letters = f"{prefix} {number}"
                                course_obj = {
                                    "name": full_name,
                                    "honors": is_honors,
                                    "course_id": hash_id(course_letters),
                                    "course_letters": course_letters,
                                    "title": title
                                }
                                
                                # Extract and add notes
                                ccc_note = extract_notes(course_data)
                                if ccc_note:
                                    course_obj["note"] = ccc_note
                                
                                all_courses_in_and_group.append(course_obj)
                
                # Create a single AND block containing all courses from this range
                if all_courses_in_and_group:
                    or_paths.append({
                        "type": "AND",
                        "courses": all_courses_in_and_group
                    })
            
            # If we have valid paths after processing conjunctions, return them
            if or_paths:
                return {
                    "type": "OR",
                    "courses": or_paths
                }
    
    # If no special conjunction processing happened, continue with the original logic
    # Start building the OR block for all possible paths
    or_paths = []
    
    # Process items in the exact order they appear in the ASSIST JSON
    for item in articulation["items"]:
        if "items" not in item:
            continue
            
        # This is an AND group (all courses in this item must be taken together).
        # Courses within this group need to be sorted by their own 'position' attribute
        # to match the display order on the ASSIST website.
        
        # Temporary list to hold course data along with their positions for sorting
        courses_to_sort = []
        
        # Iterate through each course definition within the current AND group item
        for course_data_from_json in item["items"]:
            if "courseIdentifierParentId" not in course_data_from_json:
                # Skip if essential course identifier is missing
                continue
                
            # Extract course information
            prefix = course_data_from_json.get("prefix", "")
            number = course_data_from_json.get("courseNumber", "")
            title = course_data_from_json.get("courseTitle", "")
            # Format course name consistently
            full_name = f"{prefix} {number} {title}"
            
            # Determine if the course is an honors version
            is_honors = "HONORS" in title.upper() or title.upper().endswith("H")
            
            # Create a standardized course object
            course_letters = f"{prefix} {number}"
            course_obj = {
                "name": full_name,
                "honors": is_honors,
                "course_id": hash_id(course_letters),
                "course_letters": course_letters,
                "title": title
            }
            
            # Extract and add notes for the CCC course
            ccc_note = extract_notes(course_data_from_json)
            if ccc_note:
                course_obj["note"] = ccc_note
            
            # Store the course object along with its 'position' from the JSON for sorting.
            # Default to a high number if 'position' is missing to place it at the end.
            courses_to_sort.append({
                "course_obj": course_obj,
                "position": course_data_from_json.get("position", 999) 
            })
        
        # Sort the courses within this AND group based on their 'position' attribute.
        courses_to_sort.sort(key=lambda c: c["position"])
        
        # Populate the final list of courses for this AND group using the sorted course objects.
        courses_in_group = [c["course_obj"] for c in courses_to_sort]
        
        # If we successfully extracted and sorted courses for this group, add them as an AND path.
        if courses_in_group:
            and_path = {
                "type": "AND",
                "courses": courses_in_group,
                "position": item.get("position", 999)  # Store position for sorting
            }
            or_paths.append(and_path)
    
    # If no valid paths were found, return "No Course Articulated"
    if not or_paths:
        return {
            "type": "OR",
            "courses": [{
                "name": "No Course Articulated",
                "honors": False,
                "course_id": hash_id("No Course Articulated"),
                "course_letters": "N/A",
                "title": "No Course Articulated"
            }],
            "no_articulation": True
        }
    
    # Sort OR paths by their position values to match ASSIST website display order
    or_paths.sort(key=lambda x: x.get("position", 999))
    
    # Remove the temporary position keys from the final output
    for path in or_paths:
        if "position" in path:
            del path["position"]
    
    # Return the final OR block with all possible paths, now sorted by position
    return {
        "type": "OR",
        "courses": or_paths
    }


def extract_notes(course_data: Dict[str, Any]) -> Optional[str]:
    """Extract course notes from attributes or other fields.
    Returns a single string with all notes concatenated, or None if no notes."""
    notes_list = []
    
    # Look for course attributes
    if "courseAttributes" in course_data and course_data["courseAttributes"]:
        for attr in course_data["courseAttributes"]:
            if isinstance(attr, dict) and "description" in attr:
                notes_list.append(attr["description"])
    
    # Look for visible cross-listed courses
    if "visibleCrossListedCourses" in course_data and course_data["visibleCrossListedCourses"]:
        cross_listed_texts = []
        for cross in course_data["visibleCrossListedCourses"]:
            # Handle both formats: direct course objects and those with a nested "course" key
            cross_course = None
            if isinstance(cross, dict):
                # Format 1: The cross-listed course info is directly in the object (as with POL SC 51)
                if "prefix" in cross or "courseNumber" in cross:
                    cross_course = cross
                # Format 2: The cross-listed course is in a nested "course" key (as with CSE courses)
                elif "course" in cross and isinstance(cross["course"], dict):
                    cross_course = cross["course"]
                    
            if cross_course:
                # Process the cross_course data regardless of which format it came from
                prefix_val = cross_course.get("prefix")
                number_val = cross_course.get("courseNumber")
                
                current_identifier_parts = []
                if prefix_val is not None:
                    prefix_str = str(prefix_val).strip()
                    if prefix_str: # Add only if not empty after stripping
                        current_identifier_parts.append(prefix_str)
                
                if number_val is not None:
                    number_str = str(number_val).strip()
                    if number_str: # Add only if not empty after stripping
                        current_identifier_parts.append(number_str)
                
                if current_identifier_parts: # Only if we have something to join
                    cross_listed_texts.append(f"Same as {' '.join(current_identifier_parts)}")
        
        if cross_listed_texts:
            notes_list.extend(cross_listed_texts)
    
    # If notes were found, join them into a single string
    if notes_list:
        return "; ".join(notes_list)
    
    return None


def clean_html(html_content: str) -> str:
    """
    Clean HTML content, removing tags while preserving paragraph breaks.
    """
    # Replace <p> and <br> tags with newlines
    content = re.sub(r'<(?:p|br)[^>]*>', '\n', html_content, flags=re.IGNORECASE)
    
    # Remove all remaining HTML tags
    content = re.sub(r'<[^>]+>', ' ', content)
    
    # Clean up multiple whitespace and newlines
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\n\s+', '\n', content)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Strip leading/trailing whitespace
    content = content.strip()
    
    return content


def extract_section_id(section: Dict[str, Any], fallback_id: int) -> str:
    """
    Extract the section ID from a section object.
    
    Args:
        section: The section object from ASSIST JSON
        fallback_id: Default ID to use if no section letter is found
        
    Returns:
        The section ID as a string
    """
    # Check for section letter in attributes
    if "attributes" in section and section["attributes"]:
        for attr in section["attributes"]:
            if isinstance(attr, dict) and attr.get("name") == "SectionLetter":
                return attr.get("value", str(fallback_id))
    
    # In some assets, position is used to determine section letter (A=0, B=1, etc.)
    position = section.get("position", fallback_id)
    
    # Convert position to letter (0=A, 1=B, etc.)
    if isinstance(position, int) and position < 26:
        return chr(65 + position)  # ASCII: A=65, B=66, etc.
    
    # Fallback
    return str(position)


def extract_section_title(section: Dict[str, Any], section_id: str) -> str:
    """
    Create a more descriptive section title.
    
    Args:
        section: The section object from ASSIST JSON
        section_id: The section ID already determined
        
    Returns:
        A formatted section title
    """
    # Check if there's a specific title in the section
    if "title" in section and section["title"]:
        return section["title"]
    
    # If no title, use the section ID with appropriate formatting
    return f"Section {section_id}"


def infer_section_logic_type(section: Dict[str, Any], advisements: List[Dict[str, Any]] = None) -> Tuple[str, Optional[int]]:
    """
    Determine the logic type for a section based on its structure and advisements.
    
    Args:
        section: The section object from ASSIST JSON
        advisements: List of advisement objects
        
    Returns:
        Tuple of (logic_type, n_courses) where n_courses is only set for select_n_courses
    """
    # Check advisements first (highest priority)
    if advisements:
        for advisement in advisements:
            # Check if it's an 'NFollowing' advisement specifying a number of courses
            if advisement.get("type") == "NFollowing" and advisement.get("amountUnitType") == "Course":
                amount = int(float(advisement.get("amount", 1)))
                # Regardless of selectionType ('Complete' or 'Select'), if it specifies N courses, it's a selection.
                return "select_n_courses", amount
    
    rows = section.get("rows", [])
    
    # Specific pattern check for History BA Section A like structures:
    # If a section contains a "Series" and also individual "Course" cells that are components of that Series,
    # it implies a choice between taking the full Series or one of the individual component paths.
    if len(rows) > 1: # Needs multiple rows to have a series and its components separately
        has_series_cell_in_section = False
        series_definition_courses = set() # Store course IDs (e.g., "HILD 2A") from a series definition
        individual_course_ids_in_section = set() # Store course IDs from individual Course cells

        for row in rows:
            for cell in row.get("cells", []):
                if cell.get("type") == "Series":
                    has_series_cell_in_section = True
                    series_data = cell.get("series", {})
                    for s_course in series_data.get("courses", []):
                        series_definition_courses.add(f"{s_course.get('prefix')} {s_course.get('courseNumber')}")
                elif cell.get("type") == "Course":
                    course_data = cell.get("course", {})
                    individual_course_ids_in_section.add(f"{course_data.get('prefix')} {course_data.get('courseNumber')}")
        
        if has_series_cell_in_section and series_definition_courses.intersection(individual_course_ids_in_section):
            # This pattern (Series + its components listed individually in other rows) suggests a choice.
            # The screenshot for History BA Section A implies "select 1" from these options.
            return "select_n_courses", 1

    # Check for OR row relationships (Review if this existing logic is sound, may need adjustment later)
    # The original comment noted this `row.get("conjunction")` logic might be for within-row.
    # For now, keeping it but acknowledging it might need to be revisited as it wasn't the cause of this specific bug.
    if len(rows) > 1:
        # Look for OR indicators between rows (this interpretation of row.conjunction needs verification)
        for row in rows:
            if row.get("conjunction") == "Or": # This 'conjunction' is usually for cells within a row
                return "select_n_courses", 1 # Changed "select_one_course" to standard "select_n_courses"
    
    # Default to "all required"
    return "all_required", None


def process_advisements(advisements: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[int]]:
    """
    Process advisements list to extract logical requirements.
    
    Args:
        advisements: List of advisement objects
        
    Returns:
        Tuple of (logic_type, n_value) where n_value is only set for count-based types
    """
    if not advisements:
        return None, None
        
    for advisement in advisements:
        advisement_type = advisement.get("type")
        
        if advisement_type == "NFollowing" and advisement.get("selectionType") == "Select":
            amount = int(float(advisement.get("amount", 1)))
            return "select_n_courses", amount
            
    return None, None


def analyze_section_courses(section: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    """
    Analyze the courses in a section to determine if there's a selection pattern.
    
    Args:
        section: The section object from ASSIST JSON
        
    Returns:
        Tuple of (logic_type, n_value) where n_value is only set for count-based types
    """
    rows = section.get("rows", [])
    course_count = 0
    
    # Count the number of courses in the section
    for row in rows:
        for cell in row.get("cells", []):
            if cell.get("type") == "Course":
                course_count += 1
    
    # If we have multiple courses, check for advisements that might indicate selection
    if course_count >= 2:
        for advisement in section.get("advisements", []):
            if advisement.get("type") == "NFollowing":
                amount = int(float(advisement.get("amount", 1)))
                return "select_n_courses", amount
    
    return None, None


def process_group_advisements(group_asset: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    """
    Process a requirement group's advisements to determine its overall logic type.
    Only group-level advisements or advisements/analysis from a single section (if group has only one)
    should determine the group logic here. For multi-section groups, this function should not
    infer group logic from sub-section advisements.
    """
    # First check the group's own advisements
    group_advisements = group_asset.get("advisements", [])
    for advisement in group_advisements:
        advisement_type = advisement.get("type")
        
        if advisement_type == "NFollowing" and advisement.get("selectionType") == "Select":
            amount = int(float(advisement.get("amount", 1)))
            return "select_n_courses", amount # Group-level advisement takes precedence
    
    # If the group itself has no overriding advisements, check its sections.
    # Only if the group has a SINGLE section can that section's advisements or analysis
    # potentially define the group's logic type here.
    sections = group_asset.get("sections", [])
    if len(sections) == 1:
        section = sections[0]
        # Check this single section's advisements
        section_advisements = section.get("advisements", [])
        for advisement in section_advisements:
            if advisement.get("type") == "NFollowing" and advisement.get("selectionType") == "Select":
                amount = int(float(advisement.get("amount", 1)))
                return "select_n_courses", amount # Single section's advisement defines group logic
        
        # If no overriding advisement from the single section, analyze its courses
        # (This primarily looks for "select_n_courses" patterns within the single section)
        logic_type, n_value = analyze_section_courses(section)
        if logic_type:
            return logic_type, n_value
    
    # For multi-section groups without a group-level "Select N" advisement,
    # or for single-section groups where the section itself didn't yield a clear selection logic,
    # return (None, None). This allows `infer_group_logic_type` (based on the group's main instruction)
    # to make the final determination for the group's logic type.
    # `infer_group_logic_type` often defaults to "all_required" for multi-section groups
    # if the group's main instruction isn't a specific selection type.
    return None, None


def generate_group_title(
    group_logic_type: str, 
    n_courses: Optional[int] = None, 
    instruction: Optional[Dict[str, Any]] = None,
    instruction_text: str = "", 
    is_recommended: bool = False,
    section_ids: Optional[List[str]] = None,
    has_explicit_instruction_for_title: bool = False
) -> Optional[str]:
    """
    Generate a descriptive group title based on logic type and context.
    
    Args:
        group_logic_type: The type of logic for the group
        n_courses: Number of courses to select (for select_n_courses type)
        instruction: The raw instruction object from the ASSIST JSON asset
        instruction_text: Original instruction text (less reliable for specific choices)
        is_recommended: Flag indicating if the group is recommended
        section_ids: List of section IDs for multi-section choice groups
        has_explicit_instruction_for_title: True if instruction implies a title
        
    Returns:
        A human-readable group title or None
    """
    # Highest priority: Recommended groups
    if is_recommended:
        return "Recommended but not required courses:"
        
    # Next priority: Check for explicit 'Or'/'Select' instruction structure
    if isinstance(instruction, dict) and instruction.get("conjunction") == "Or" and instruction.get("selectionType") == "Select":
        # Even if inferred as select_n_courses, this structure implies a choice between options/sections.
        # Generate a more specific title reflecting this choice.
        # TODO: Refine this further based on roadmap item 3 (logic inference)
        # If logic is confirmed 'choose_one_section', use section IDs. For now, use generic choice text.
        if group_logic_type == "choose_one_section" and section_ids and len(section_ids) > 1:
             # Sort section IDs for consistent ordering (e.g., A, B, C)
            sorted_section_ids = sorted(section_ids)
            return f"Complete Section { ' OR Section '.join(sorted_section_ids) }"
        else:
            # If it's inferred as select_n_courses but instruction implies OR choice
            plural = "option" if n_courses == 1 else "options" 
            number_word = "ONE" if n_courses == 1 else str(n_courses) if n_courses else "one" # Handle n_courses=None case
            # Use n_courses if available and > 1, otherwise default to "ONE" or "one"
            return f"Select {number_word} of the following {plural}:" # More specific choice title

    # Default logic based on inferred type if no specific instruction matched above
    if group_logic_type == "select_n_courses" and n_courses is not None:
        plural = "course" if n_courses == 1 else "courses"
        return f"Select {n_courses} {plural} from the following."
    elif group_logic_type == "choose_one_section":
        if section_ids and len(section_ids) > 1:
            # Sort section IDs for consistent ordering (e.g., A, B, C)
            sorted_section_ids = sorted(section_ids) 
            return f"Complete Section { ' OR Section '.join(sorted_section_ids) }"
        else:
            # Fallback if section IDs aren't available or only one section
            return "Complete one of the following sections" 
    elif group_logic_type == "all_required" and has_explicit_instruction_for_title: # Only return default if instruction implies it
        return "All of the following UC courses are required"
    
    # If no specific title could be generated based on logic or explicit instruction,
    # and no explicit title was found from assets, return None.
    # The original instruction_text might be too generic or misleading if used here directly as a fallback.
    return None


def generate_source_url(assist_json: Dict[str, Any], manual_url: Optional[str] = None, major_key: Optional[str] = None) -> str:
    """
    Generate a source URL for the articulation agreement.
    
    Args:
        assist_json: The JSON data from the ASSIST API
        manual_url: Optional manually specified URL to use as fallback
        major_key: Optional major key to use in the URL
        
    Returns:
        The source URL for the articulation agreement
    """
    if manual_url:
        return manual_url
        
    result = assist_json.get("result", {})
    
    # Extract necessary IDs
    academic_year_json = result.get("academicYear", "{}")
    sending_inst_json = result.get("sendingInstitution", "{}")
    receiving_inst_json = result.get("receivingInstitution", "{}")
    
    # Try to parse JSON strings if needed
    try:
        academic_year = json.loads(academic_year_json) if isinstance(academic_year_json, str) else academic_year_json
        sending_inst = json.loads(sending_inst_json) if isinstance(sending_inst_json, str) else sending_inst_json
        receiving_inst = json.loads(receiving_inst_json) if isinstance(receiving_inst_json, str) else receiving_inst_json
        
        year_id = academic_year.get("id", "")
        sending_id = sending_inst.get("id", "")
        receiving_id = receiving_inst.get("id", "")
        
        # Generate agreement key
        major_type = result.get("type", "Major")
        
        # If major_key is provided, use it; otherwise try to extract from the JSON
        if not major_key:
            major_key = result.get("id", "")
        
        # The viewByKey follows a pattern we can reconstruct
        # Use urllib.parse.quote to properly URL-encode the entire viewByKey
        view_by_key = f"{year_id}/{sending_id}/to/{receiving_id}/{major_type}/{major_key}"
        encoded_view_by_key = urllib.parse.quote(view_by_key, safe='')
        
        # Construct the URL
        return (f"https://assist.org/transfer/results?year={year_id}&institution={sending_id}"
                f"&agreement={receiving_id}&agreementType=to&viewAgreementsOptions=true"
                f"&view=agreement&viewBy=major&viewSendingAgreements=false"
                f"&viewByKey={encoded_view_by_key}")
    except Exception as e:
        # If there's any error in parsing, return a generic URL or empty string
        if manual_url:
            return manual_url
        return ""


def restructure_assist_for_rag(assist_json: Dict[str, Any], manual_source_url: Optional[str] = None, major_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Restructure ASSIST API JSON data into RAG format.
    
    Args:
        assist_json: The original ASSIST API JSON
        manual_source_url: Optional manually specified source URL
        major_key: Optional major key for source URL generation
        
    Returns:
        Dictionary in RAG format
    """
    # Extract basic info
    result = assist_json.get("result", {})
    if not result:
        raise ValueError("Invalid ASSIST JSON: missing 'result' field")
    
    # Extract institution names
    sending_inst_json = result.get("sendingInstitution", "{}")
    receiving_inst_json = result.get("receivingInstitution", "{}")
    sending_name = extract_json_value(sending_inst_json, "name")
    receiving_name = extract_json_value(receiving_inst_json, "name")
    
    # Extract catalog year
    catalog_year_json = result.get("catalogYear", "{}")
    catalog_begin = None
    catalog_end = None
    
    try:
        catalog_data = json.loads(catalog_year_json) if isinstance(catalog_year_json, str) else catalog_year_json
        catalog_begin = catalog_data.get("receivingCatalogYearBegin")
        catalog_end = catalog_data.get("receivingCatalogYearEnd")
    except:
        pass
    
    catalog_year = f"{catalog_begin}–{catalog_end}" if catalog_begin and catalog_end else "Unknown"
    
    # Start building RAG data
    rag_data = {
        "major": result.get("name", ""),
        "from": sending_name,
        "to": receiving_name,
        "source_url": generate_source_url(assist_json, manual_source_url, major_key),
        "catalog_year": catalog_year,
        "general_advice": "",
        "groups": []
    }
    
    # Parse template assets
    template_assets_json = result.get("templateAssets", "[]")
    template_assets = json.loads(template_assets_json) if isinstance(template_assets_json, str) else template_assets_json
    # Sort all assets by position once for easier lookup and correct sequencing
    template_assets.sort(
        key=lambda x: x.get("position") if isinstance(x.get("position"), int) else float('inf')
    )
    
    # Correctly identify the position of the group following a "RECOMMENDED" title
    recommended_group_positions = set()
    rec_title_index = -1
    # Find the index of the "RECOMMENDED" title in the *position-sorted* list
    for i, asset in enumerate(template_assets):
        if asset.get("type") == "RequirementTitle" and "RECOMMENDED" in asset.get("content", "").upper():
            rec_title_index = i
            break
    
    # If found, find the position of the *first* RequirementGroup *after* it in the sorted list
    if rec_title_index != -1:
        for i in range(rec_title_index + 1, len(template_assets)):
            next_asset = template_assets[i]
            if next_asset.get("type") == "RequirementGroup":
                # Found the group the title applies to based on position sequence
                group_pos = next_asset.get("position")
                if group_pos is not None:
                    recommended_group_positions.add(group_pos)
                break # Assume only one group is directly associated with this title

    # Parse articulations
    articulations_json = result.get("articulations", "[]")
    articulations = json.loads(articulations_json) if isinstance(articulations_json, str) else articulations_json
    
    # Extract general advice from general text assets (already sorted by position)
    for asset in template_assets:
        if asset.get("type") == "GeneralText":
            content = asset.get("content", "")
            # Clean HTML tags, preserving paragraph structure
            content = clean_html(content)
            
            if rag_data["general_advice"]:
                rag_data["general_advice"] += "\n\n" + content
            else:
                rag_data["general_advice"] = content
    
    group_counter = 1
    # current_overarching_title = None # Track the last seen overarching title - Replaced with temporary variable below
    last_seen_overarching_title = None # This will now be the persistent overarching title
    last_seen_requirement_title_asset: Optional[Dict[str, Any]] = None

    for asset_idx, asset in enumerate(template_assets): # Added enumerate for look-ahead/behind
        asset_type = asset.get("type")
        
        # Update General Advice (This part seems duplicated, might need cleanup later)
        # if asset_type == "GeneralText":
        #     content = asset.get("content", "")
        #     content = clean_html(content)
        #     if rag_data["general_advice"]:
        #         rag_data["general_advice"] += "\\n\\n" + content
        #     else:
        #         rag_data["general_advice"] = content
                
        # Check for Overarching Titles or other titles that might clear the context
        if asset_type == "RequirementTitle":
            title_content_original = asset.get("content", "")
            title_content_upper = title_content_original.upper()
            
            # Define keywords that identify a general, persistent overarching title
            # Exclude more specific titles like "RECOMMENDED"
            is_valid_overarching_candidate = \
                "RECOMMENDED" not in title_content_upper and \
                ("REQUIREMENTS" in title_content_upper or \
                 "DIVISION" in title_content_upper or \
                 "ELECTIVES" in title_content_upper or \
                 "ART MAKING" in title_content_upper or \
                 "ART HISTORY" in title_content_upper or \
                 "FOUNDATION LEVEL" in title_content_upper)

            if is_valid_overarching_candidate:
                last_seen_overarching_title = title_content_original # Set as the new persistent title
                last_seen_requirement_title_asset = asset # Store this title asset
            else:
                # If the title is not a general overarching one (e.g., it's "RECOMMENDED" or some other specific title)
                # it should clear any existing overarching title, so subsequent groups don't inherit it incorrectly.
                last_seen_overarching_title = None
                if "RECOMMENDED" not in title_content_upper: # Store non-overarching, non-recommended titles too
                    last_seen_requirement_title_asset = asset
                else: # Clear if it's "RECOMMENDED" as that's handled by is_recommended flag
                    last_seen_requirement_title_asset = None
            
        # Process Requirement Groups
        elif asset_type == "RequirementGroup":
            # RequirementGroup specific processing starts here
            group_id = str(group_counter)
            group_counter += 1
            
            # Determine if this group is recommended using the correctly identified position
            current_group_position = asset.get("position")
            is_recommended = current_group_position is not None and current_group_position in recommended_group_positions
            
            # Get group instruction
            instruction_object = None # Renamed from 'instruction' to avoid confusion
            instruction_text = "Complete the following requirements"  # Default
            
            if "instruction" in asset and asset["instruction"]:
                # Keep the raw instruction object for inference and title generation
                instruction_object = asset.get("instruction") # Use the raw instruction object
                
                # Also create a human-readable instruction text (as fallback)
                if isinstance(instruction_object, dict) and "conjunction" in instruction_object:
                    conjunction = instruction_object.get("conjunction", "")
                    selection_type = instruction_object.get("selectionType", "")
                    
                    # Generate a basic fallback text, might be overridden by generate_group_title later
                    if conjunction == "Or":
                        instruction_text = "Complete one of the following sections or courses"
                    elif conjunction == "And":
                        instruction_text = "Complete all of the following sections or courses"

                    if selection_type == "Select":
                        amount = instruction_object.get("amount", 1)
                        plural = "course" if amount == 1 else "courses"
                        instruction_text = f"Select {amount} {plural} from the following"
            
            # If no instruction found, look at sections
            sections = asset.get("sections", [])
            section_count = len(sections)
            
            # Determine group logic type using both the raw instruction object and our text version
            group_logic_type, n_courses_or_null = infer_group_logic_type(instruction_object, section_count, asset.get("advisements", []))
            
            # Special case: if instruction contains "Complete one of the following sections"
            # This check needs refinement later based on roadmap items 2 & 3
            # if "Complete one of the following sections" in instruction_text:
            #     group_logic_type = "choose_one_section"
            
            # Process the group's advisements for additional logic information
            adv_logic_type, adv_n_value = process_group_advisements(asset)
            
            # If advisements provided a specific logic type, use it (overrides instruction inference)
            if adv_logic_type:
                group_logic_type = adv_logic_type
                n_courses_or_null = adv_n_value # This might be n_courses or null depending on adv_logic_type
                
            # Extract the actual group title directly from the asset if present
            # Check if there's a RequirementTitle *at the same position* or immediately preceding this group
            # Find the specific RequirementTitle asset that matches this group's position context
            explicit_group_title_asset = None
            current_group_pos = asset.get("position")

            # Check if the last seen RequirementTitle is associated with this group
            if last_seen_requirement_title_asset:
                title_pos = last_seen_requirement_title_asset.get("position")
                title_content = last_seen_requirement_title_asset.get("content","").upper()
                # A title is associated if:
                # 1. It shares the same position.
                # 2. It immediately precedes the group (title_pos < current_group_pos) AND
                #    no other RequirementGroup or significant RequirementTitle came between them.
                #    This is simplified by checking if last_seen_requirement_title_asset is the most recent one.
                # 3. It's not a "RECOMMENDED" title, as that's handled by is_recommended.
                if "RECOMMENDED" not in title_content:
                    if title_pos == current_group_pos:
                        explicit_group_title_asset = last_seen_requirement_title_asset
                    else:
                        # Check if this group is the NEXT asset after the title, or if other groups are in between
                        # This requires looking at the original template_assets sequence.
                        # We assume if last_seen_requirement_title_asset was set, and we encounter a group,
                        # and it's not a "RECOMMENDED" title, it applies if positions are "close".
                        # For now, we'll consider any non-RECOMMENDED last_seen_requirement_title_asset
                        # as potentially applying if not cleared by another overarching title.
                        # The Art Studio case (FOUNDATION LEVEL) has title_pos == group_pos.
                        # If group_pos is N and title_pos is N-1, it could also apply.
                        # Let's refine association:
                        # An explicit title asset is one that is NOT an overarching title,
                        # and is either at the same position or we heuristically determine it's for this group.
                        # The `last_seen_requirement_title_asset` captures the *most recent* title.
                        # If it's not an overarching one (already handled by `last_seen_overarching_title`),
                        # and not "RECOMMENDED", it's a candidate for an explicit group title.

                        # Simpler approach: if a RequirementTitle was the immediately preceding asset in the sorted list
                        # or shares the same position, and it's not "RECOMMENDED".
                        if asset_idx > 0: # Ensure there is a preceding asset
                            preceding_asset = template_assets[asset_idx - 1]
                            if preceding_asset.get("type") == "RequirementTitle" and \
                               "RECOMMENDED" not in preceding_asset.get("content","").upper() and \
                               preceding_asset.get("position") < current_group_pos : # Must be before current group
                                # Check if no other group was between this title and current group
                                is_directly_associated = True
                                for i in range(template_assets.index(preceding_asset) + 1, asset_idx):
                                    if template_assets[i].get("type") == "RequirementGroup":
                                        is_directly_associated = False
                                        break
                                if is_directly_associated:
                                     explicit_group_title_asset = preceding_asset

                        if not explicit_group_title_asset and title_pos == current_group_pos: # Shared position
                             explicit_group_title_asset = last_seen_requirement_title_asset


            # Generate a proper group title based on the logic type and context
            # Prioritize explicit title if found, otherwise generate based on logic
            group_title = None
            if explicit_group_title_asset:
                 group_title = explicit_group_title_asset.get("content")
                 # Clear last_seen_requirement_title_asset if it was used as an explicit group title
                 # and was not an overarching title (which should persist).
                 # Overarching titles are handled by last_seen_overarching_title.
                 # If the explicit title was also an overarching candidate, it would have been stored there.
                 # This ensures a specific group title isn't mistakenly reused.
                 # if explicit_group_title_asset.get("content", "").upper() != last_seen_overarching_title_content_upper
                 # This logic is tricky; for now, if used, we assume it's consumed.
                 # Overarching titles will be re-applied from `last_seen_overarching_title` anyway.
                 # Test this carefully. The goal is: if FOUNDATION LEVEL is used, it shouldn't become overarching.
                 # The current overarching logic seems to handle this by checking specific keywords.

            if not group_title: # If no explicit title was directly associated
                 group_section_ids = [extract_section_id(s, idx) for idx, s in enumerate(sections)]
                 # Determine if the instruction itself implies a title should be generated
                 has_explicit_instruction_for_title = False
                 if isinstance(instruction_object, dict):
                     # If conjunction is Or/And with Select/Complete, it often implies a standard title
                     if instruction_object.get("conjunction") in ["Or", "And"] and \
                        instruction_object.get("selectionType") in ["Select", "Complete"]:
                         has_explicit_instruction_for_title = True
                 if not instruction_object and section_count == 1: # Single section group often implies "all required"
                      has_explicit_instruction_for_title = True


                 group_title = generate_group_title(
                     group_logic_type,
                     n_courses_or_null, # Pass the potentially null value
                     instruction_object, # Pass the raw instruction object
                     instruction_text,
                     is_recommended,
                     group_section_ids, # Pass section IDs for potential "Complete Section A OR B" title
                     has_explicit_instruction_for_title
                 )
            
            # Create group structure
            group_obj = {
                "group_id": group_id,
                "group_title": group_title, # Title generated above/extracted or None
                "group_logic_type": group_logic_type,
                "sections": []
            }

            # Add the last seen overarching title IF one is active and persistent
            # AND if the current group_title isn't already the same as the overarching title
            # (to avoid redundancy like "FOUNDATION LEVEL - REQUIRED COURSEWORK" as overarching
            #  and then again as group_title if it was an explicit title).
            #  However, an overarching title *should* apply even if the group title is e.g. "Select 2 courses".
            #  The problem is when the explicit group title *is* the overarching one.
            #  The `last_seen_overarching_title` logic should correctly set it based on keywords.
            #  If `group_title` was set from an explicit `RequirementTitle` that *was* also an
            #  overarching title (e.g. "FOUNDATION LEVEL..."), then `overarching_title` field might be redundant.
            #  Let's assume for now the `overarching_title` field is for broader context and can co-exist.
            if last_seen_overarching_title:
                 group_obj["overarching_title"] = last_seen_overarching_title
                 # DO NOT RESET last_seen_overarching_title here; it persists until a new RequirementTitle changes the context.

            # Add is_recommended flag if true
            if is_recommended:
                group_obj["is_recommended"] = True # Add the flag to the RAG output

            # Add n_courses or n_sections_to_choose based on logic type
            if group_logic_type == "select_n_courses" and n_courses_or_null is not None:
                group_obj["n_courses"] = n_courses_or_null
            elif group_logic_type == "choose_one_section":
                 # Assuming choose_one_section always means choose 1, unless specified otherwise later
                group_obj["n_sections_to_choose"] = 1
            # Note: 'n_courses' field is intentionally omitted for 'choose_one_section'

            # Process sections
            for section_idx, section in enumerate(sections):
                # Get section ID and title
                section_id = extract_section_id(section, section_idx)
                section_title = extract_section_title(section, section_id)
                
                # Determine section logic type
                section_logic_type, section_n_courses = infer_section_logic_type(
                    section, 
                    section.get("advisements", [])
                )
                
                # Create section object
                section_obj = {
                    "section_id": section_id,
                    "section_title": section_title,
                    "section_logic_type": section_logic_type,
                    "uc_courses": [] # Initialize as empty, will be populated with sorted courses
                }
                
                # If it's select_n_courses, add n_courses
                if section_logic_type == "select_n_courses" and section_n_courses is not None:
                    section_obj["n_courses"] = section_n_courses
                
                # Temporary list to hold UC course objects with their row positions for sorting
                uc_courses_to_sort = []
                
                # Process rows (these contain the UC courses)
                for row in section.get("rows", []):
                    # Get the position of the current row, which dictates UC course order
                    row_position = row.get("position", 999) # Default to 999 if no position
                    
                    for cell in row.get("cells", []):
                        if cell.get("type") == "Course":
                            course_data = cell.get("course", {})
                            
                            # Extract UC course information
                            prefix = course_data.get("prefix", "")
                            number = course_data.get("courseNumber", "")
                            title = course_data.get("courseTitle", "")
                            units = course_data.get("minUnits")
                            
                            uc_course_id = f"{prefix} {number}"
                            uc_course_title = title.strip() # Trim whitespace from UC course title

                            # Pass the entire cell to extract_notes, as visibleCrossListedCourses
                            # and courseAttributes are direct children of the cell object.
                            uc_note_from_cell = extract_notes(cell)

                            # Find the articulation for this UC course
                            articulation_data = None
                            cell_id = cell.get("id")
                            
                            for art_lookup in articulations: # Renamed 'articulation' to 'art_lookup' to avoid conflict
                                if isinstance(art_lookup, dict) and art_lookup.get("templateCellId") == cell_id:
                                    articulation_data = art_lookup
                                    break
                            
                            # Extract sending articulation (community college courses)
                            logic_block = {}
                            if articulation_data and "articulation" in articulation_data:
                                sending_articulation = articulation_data["articulation"].get("sendingArticulation", {})
                                logic_block = parse_sending_articulation(sending_articulation)
                            else:
                                # If there's no articulation data or it's empty, add no_articulation flag
                                logic_block = {
                                    "type": "OR",
                                    "courses": [{
                                        "name": "No Course Articulated",
                                        "honors": False,
                                        "course_id": hash_id("No Course Articulated"),
                                        "course_letters": "N/A",
                                        "title": "No Course Articulated"
                                    }],
                                    "no_articulation": True
                                }
                            
                            # Ensure empty logic blocks have no_articulation flag
                            if not logic_block or (isinstance(logic_block, dict) and not logic_block.get("courses")):
                                logic_block = {
                                    "type": "OR",
                                    "courses": [{
                                        "name": "No Course Articulated",
                                        "honors": False,
                                        "course_id": hash_id("No Course Articulated"),
                                        "course_letters": "N/A",
                                        "title": "No Course Articulated"
                                    }],
                                    "no_articulation": True
                                }
                            
                            # Create the UC course object
                            current_uc_course_obj = { # Renamed 'course_obj' to 'current_uc_course_obj'
                                "uc_course_id": uc_course_id,
                                "uc_course_title": uc_course_title,
                                "section_id": section_id, # Retain section context
                                "section_title": section_title, # Retain section context
                                "logic_block": logic_block
                            }
                            
                            # Add optional fields if present
                            if units is not None:
                                current_uc_course_obj["units"] = units
                            
                            # Add the extracted uc_note_from_cell if it exists
                            if uc_note_from_cell:
                                current_uc_course_obj["note"] = uc_note_from_cell
                            
                            # Add the created UC course object along with its row's position for sorting
                            uc_courses_to_sort.append({
                                "course_obj": current_uc_course_obj,
                                "position": row_position
                            })
                        elif cell.get("type") == "Series":
                            series_data = cell.get("series", {})
                            series_name_from_json = series_data.get("name", "Unknown Series") # e.g., "HILD 2A, HILD 2B, HILD 2C"
                            
                            # Create a uc_course_id from the parts for consistency if name is just a list
                            series_uc_id_parts = []
                            for s_course in sorted(series_data.get("courses", []), key=lambda x: x.get("position", 0)):
                                series_uc_id_parts.append(f"{s_course.get('prefix')} {s_course.get('courseNumber')}")
                            
                            # Use the explicit series name if it's not just a join of course numbers, otherwise use the joined parts
                            series_uc_id = series_name_from_json
                            if not series_name_from_json or set(series_name_from_json.split(", ")) == set(series_uc_id_parts):
                                series_uc_id = " + ".join(series_uc_id_parts) # e.g. "HILD 2A + HILD 2B + HILD 2C"

                            series_uc_title = f"Series: {series_name_from_json.strip()}" # Trim whitespace from series title as well
                            
                            # Extract articulation for this "Series" cell
                            articulation_data = None
                            cell_id = cell.get("id") # ID of the Series cell
                            for art_lookup in articulations: # Ensure 'articulations' is defined in this scope
                                if art_lookup.get("templateCellId") == cell_id:
                                    articulation_data = art_lookup
                                    break
                            
                            logic_block = {}
                            if articulation_data and "articulation" in articulation_data:
                                sending_articulation = articulation_data["articulation"].get("sendingArticulation", {})
                                logic_block = parse_sending_articulation(sending_articulation)
                            else:
                                logic_block = { "type": "OR", "courses": [{"name": "No Course Articulated", "honors": False, "course_id": hash_id("No Course Articulated"), "course_letters": "N/A", "title": "No Course Articulated"}], "no_articulation": True }

                            current_uc_course_obj = {
                                "uc_course_id": series_uc_id,
                                "uc_course_title": series_uc_title,
                                "_is_uc_series_requirement": True, 
                                "_series_definition": [
                                    {
                                        "course_letters": f"{s_c.get('prefix')} {s_c.get('courseNumber')}",
                                        "title": s_c.get('courseTitle')
                                    } for s_c in series_data.get("courses", [])
                                ],
                                "section_id": section_id,
                                "section_title": section_title,
                                "logic_block": logic_block
                            }
                            
                            uc_note_from_cell = extract_notes(cell)
                            if uc_note_from_cell:
                                current_uc_course_obj["note"] = uc_note_from_cell
                            
                            uc_courses_to_sort.append({
                                "course_obj": current_uc_course_obj,
                                "position": row_position 
                            })
                
                # Sort the collected UC courses based on their row's position attribute
                uc_courses_to_sort.sort(key=lambda x: x["position"])
                
                # Populate the section's uc_courses list with the sorted courses
                for sorted_item in uc_courses_to_sort:
                    section_obj["uc_courses"].append(sorted_item["course_obj"])
                
                # Add section to group
                group_obj["sections"].append(section_obj)
            
            # Sort sections alphabetically by section_id (A, B, C...)
            group_obj["sections"].sort(key=lambda x: x.get("section_id", ""))

            # Add group to RAG data
            rag_data["groups"].append(group_obj)
    
    return rag_data


def process_assist_json_file(file_path: Union[str, Path], manual_source_url: Optional[str] = None, major_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Process an ASSIST JSON file and convert it to RAG format.
    
    Args:
        file_path: Path to the ASSIST JSON file
        manual_source_url: Optional manually specified source URL
        major_key: Optional major key for source URL generation
        
    Returns:
        Dictionary in RAG format
    """
    # Load the JSON file
    with open(file_path, 'r', encoding='utf-8') as f:
        assist_data = json.load(f)
    
    # Convert to RAG format
    rag_data = restructure_assist_for_rag(assist_data, manual_source_url, major_key)
    
    return rag_data


def save_rag_json(rag_data: Dict[str, Any], output_path: Union[str, Path]) -> None:
    """
    Save RAG data to a JSON file.
    
    Args:
        rag_data: Dictionary in RAG format
        output_path: Path to save the output JSON
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(rag_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved RAG JSON to {output_path}")


if __name__ == "__main__":
    # Example usage
    parser = argparse.ArgumentParser(description="Convert ASSIST API JSON to RAG format.")
    parser.add_argument("input_file", help="Input ASSIST JSON file")
    parser.add_argument("output_file", help="Output RAG JSON file")
    parser.add_argument("--source-url", help="Manual source URL override")
    parser.add_argument("--major-key", help="Major key for source URL generation")
    
    args = parser.parse_args()
    
    rag_data = process_assist_json_file(args.input_file, args.source_url, args.major_key)
    save_rag_json(rag_data, args.output_file) 