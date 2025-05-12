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
        
        # Complete A or B type structure
        if conjunction == "Or" and selection_type == "Complete":
            return "choose_one_section", None
            
        # Complete all sections
        if conjunction == "And" and selection_type == "Complete":
            return "all_required", None
            
        # Select N courses
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
    # Handle empty articulation
    if not articulation or "items" not in articulation:
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
            if isinstance(cross, dict) and "course" in cross:
                cross_course = cross["course"]
                if "prefix" in cross_course and "courseNumber" in cross_course:
                    cross_listed_texts.append(f"Same as {cross_course['prefix']} {cross_course['courseNumber']}")
        
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
            if advisement.get("type") == "NFollowing" and advisement.get("selectionType") == "Select":
                amount = int(float(advisement.get("amount", 1)))
                return "select_n_courses", amount
    
    # Check for OR row relationships
    # If a section has multiple rows with "OR" between them, it might be a "select_n_courses" type
    rows = section.get("rows", [])
    
    # In many cases, if there are multiple courses but no other indicators,
    # all courses in the section are required
    if len(rows) > 1:
        # Look for OR indicators between rows
        for row in rows:
            if row.get("conjunction") == "Or":
                return "select_one_course", None
    
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
    
    Args:
        group_asset: The requirement group asset from ASSIST JSON
        
    Returns:
        Tuple of (logic_type, n_value) where n_value is only set for count-based types
    """
    # First check the group's own advisements
    advisements = group_asset.get("advisements", [])
    for advisement in advisements:
        advisement_type = advisement.get("type")
        
        if advisement_type == "NFollowing" and advisement.get("selectionType") == "Select":
            amount = int(float(advisement.get("amount", 1)))
            return "select_n_courses", amount
    
    # If the group itself has no advisements, check its sections
    for section in group_asset.get("sections", []):
        section_advisements = section.get("advisements", [])
        for advisement in section_advisements:
            if advisement.get("type") == "NFollowing" and advisement.get("selectionType") == "Select":
                # If we find this in a section, the group should be "select_n_courses"
                amount = int(float(advisement.get("amount", 1)))
                return "select_n_courses", amount
    
    # Check if there's a single section with multiple courses and selection indicators
    if len(group_asset.get("sections", [])) == 1:
        section = group_asset["sections"][0]
        # Analyze the section's courses for selection patterns
        logic_type, n_value = analyze_section_courses(section)
        if logic_type:
            return logic_type, n_value
    
    return None, None


def generate_group_title(group_logic_type: str, n_courses: Optional[int] = None, instruction_text: str = "") -> str:
    """
    Generate a descriptive group title based on logic type.
    
    Args:
        group_logic_type: The type of logic for the group
        n_courses: Number of courses to select (for select_n_courses type)
        instruction_text: Original instruction text
        
    Returns:
        A human-readable group title
    """
    if group_logic_type == "select_n_courses" and n_courses is not None:
        return f"Select {n_courses} courses from the following."
    elif group_logic_type == "choose_one_section":
        return "Complete one of the following sections"
    elif group_logic_type == "all_required":
        return "All of the following UC courses are required"
    else:
        # Use original text as fallback
        return instruction_text if instruction_text else "Complete the following requirements"


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
    
    # Parse articulations
    articulations_json = result.get("articulations", "[]")
    articulations = json.loads(articulations_json) if isinstance(articulations_json, str) else articulations_json
    
    # Extract general advice from general text assets
    for asset in template_assets:
        if asset.get("type") == "GeneralText":
            content = asset.get("content", "")
            # Clean HTML tags, preserving paragraph structure
            content = clean_html(content)
            
            if rag_data["general_advice"]:
                rag_data["general_advice"] += "\n\n" + content
            else:
                rag_data["general_advice"] = content
    
    # Process requirement groups
    group_counter = 1
    
    for asset in template_assets:
        if asset.get("type") == "RequirementGroup":
            # Extract group information
            group_id = str(group_counter)
            group_counter += 1
            
            # Get group instruction
            instruction = None
            instruction_text = "Complete the following requirements"  # Default
            
            if "instruction" in asset and asset["instruction"]:
                # Keep the raw instruction object for inference
                instruction = asset["instruction"]
                
                # Also create a human-readable instruction text
                if "conjunction" in asset["instruction"]:
                    conjunction = asset["instruction"].get("conjunction", "")
                    selection_type = asset["instruction"].get("selectionType", "")
                    
                    if conjunction == "Or":
                        instruction_text = "Complete one of the following sections"
                    elif conjunction == "And":
                        instruction_text = "Complete all of the following sections"
                    
                    if selection_type == "Select":
                        amount = asset["instruction"].get("amount", 1)
                        instruction_text = f"Select {amount} course(s) from the following"
            
            # If no instruction found, look at sections
            sections = asset.get("sections", [])
            section_count = len(sections)
            
            # Determine group logic type using both the raw instruction object and our text version
            group_logic_type, n_courses = infer_group_logic_type(instruction, section_count, asset.get("advisements", []))
            
            # Special case: if instruction contains "Complete one of the following sections"
            if "Complete one of the following sections" in instruction_text:
                group_logic_type = "choose_one_section"
            
            # Process the group's advisements for additional logic information
            adv_logic_type, adv_n_value = process_group_advisements(asset)
            
            # If advisements provided a specific logic type, use it
            if adv_logic_type:
                group_logic_type = adv_logic_type
                n_courses = adv_n_value
                
            # Generate a proper group title based on the logic type
            group_title = generate_group_title(group_logic_type, n_courses, instruction_text)
            
            # Create group structure
            group_obj = {
                "group_id": group_id,
                "group_title": group_title,
                "group_logic_type": group_logic_type,
                "sections": []
            }
            
            # If it's select_n_courses, add n_courses
            if group_logic_type == "select_n_courses" and n_courses is not None:
                group_obj["n_courses"] = n_courses
            
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
                            uc_course_title = title

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
                
                # Sort the collected UC courses based on their row's position attribute
                uc_courses_to_sort.sort(key=lambda x: x["position"])
                
                # Populate the section's uc_courses list with the sorted courses
                for sorted_item in uc_courses_to_sort:
                    section_obj["uc_courses"].append(sorted_item["course_obj"])
                
                # Add section to group
                group_obj["sections"].append(section_obj)
            
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