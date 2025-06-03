import json
import re
import os

def is_cross_reference_entry(course_id, title, catalog_text, match_position):
    """
    Determine if this is a cross-reference entry (mapping table) rather than an actual course.
    Cross-reference entries typically appear in mapping tables and don't have units.
    """
    # Look at surrounding context
    context_start = max(0, match_position - 200)
    context_end = min(len(catalog_text), match_position + 100)
    context = catalog_text[context_start:context_end]
    
    # Check for specific patterns that indicate cross-reference entries
    cross_ref_indicators = [
        "Common Course Number and Name",
        "Former Course Number and Name"
    ]
    
    for indicator in cross_ref_indicators:
        if indicator in context:
            return True
    
    # Check if the title contains another course ID (cross-reference pattern)
    # Like "Introduction to Public Speaking COM ST 11, Elements of Public Speaking"
    # This pattern specifically indicates a cross-reference table entry
    if re.search(r'[A-Z]{2,}(?:\s+[A-Z]+)?\s+\d+[A-Z]?,', title):
        return True
        
    return False

def is_combined_course_entry(course_id, partial_title):
    """
    Check if this is a combined course entry that ends with "WITH" and should be skipped
    because the actual course definition with units comes next.
    """
    return partial_title.strip().upper().endswith("WITH")

def is_incomplete_course_list(course_id, partial_title):
    """
    Check if this appears to be an incomplete course list or reference.
    Be more specific to avoid over-filtering.
    """
    title = partial_title.strip()
    
    # Very specific patterns for incomplete entries
    # Pattern 1: Just numbers and periods like "29."
    if re.match(r'^\d+\.\s*$', title):
        return True
    
    # Pattern 2: Lists of course numbers like "2C (or 3, 3C & 4, 4C), 7, 8,"
    if re.match(r'^[\d\w\(\),\s&]+,\s*$', title) and not re.search(r'[A-Z]{3,}', title):
        return True
    
    return False

def parse_courses_for_department(catalog_text, department_info, global_added_course_ids):
    """
    Parses courses for a specific department from the catalog text,
    handling multiple course letter aliases, multi-line course entries, and improved unit finding.
    Special handling for Independent Studies which has cross-departmental 88A/88B/88C courses.
    Enhanced to skip cross-reference entries, combined course entries, and incomplete lists.
    Now prioritizes complete entries with units over incomplete ones.

    Args:
        catalog_text (str): The full text of the SMC catalog.
        department_info (dict): A dictionary containing department details,
                                including department_info['resolved_course_letters'].
        global_added_course_ids (set): Global set to prevent duplicates across all departments.

    Returns:
        list: A list of dictionaries, where each dictionary represents a course
              and contains 'title', 'course_id', and 'units'.
    """
    courses = []
    
    # Special handling for Independent Studies
    if department_info.get('major') == "Independent Studies":
        # Use a specialized regex for Independent Studies courses
        independent_studies_regex = re.compile(
            r"^([A-Z]{2,}(?:\s[A-Z]+)?\s+88[ABC])" + # Group 1: Course ID (e.g., HIST 88A, ARTS 88B)
            r",\s+" +                               # Comma and space
            r"(.+)$",                              # Group 2: Title (rest of first line)
            re.MULTILINE
        )
        
        course_candidates = {}  # Track multiple instances of the same course
        
        for match in independent_studies_regex.finditer(catalog_text):
            course_id = match.group(1).strip()
            partial_title = match.group(2).strip()
            
            # Skip if already processed globally (but track for prioritization)
            if course_id in global_added_course_ids and course_id not in course_candidates:
                continue
            
            # Skip cross-reference entries
            if is_cross_reference_entry(course_id, partial_title, catalog_text, match.start()):
                continue
            
            # For Independent Studies, the title usually includes "INDEPENDENT STUDIES IN [SUBJECT]"
            # Check if units are in the partial title (single-line format)
            single_line_units_match = re.search(r'(.+?)\s+(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s+UNITS?)\s*$', partial_title, re.IGNORECASE)
            
            if single_line_units_match:
                complete_title = single_line_units_match.group(1).strip()
                units_text = single_line_units_match.group(2).strip()
            else:
                # Multi-line format: search for continuation with enhanced unit detection
                line_end = catalog_text.find('\n', match.end())
                if line_end == -1:
                    line_end = len(catalog_text)
                
                search_start = line_end + 1
                search_end = min(len(catalog_text), search_start + 250)  # Expanded window for Independent Studies
                continuation_text = catalog_text[search_start:search_end]
                
                # Stop at next course entry
                next_course_pattern = r'^[A-Z]{2,}(?:\s[A-Z]+)?\s+[\w.-]+,'
                next_course_match = re.search(next_course_pattern, continuation_text, re.MULTILINE)
                if next_course_match:
                    continuation_text = continuation_text[:next_course_match.start()]
                
                continuation_lines = continuation_text.split('\n')[:4]  # Check up to 4 lines
                complete_title = partial_title
                units_text = None
                
                for line in continuation_lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Enhanced unit detection patterns
                    # Pattern 1: Title continuation with units at end
                    line_with_units_match = re.match(r'^(.+?)\s+(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s+UNITS?)\s*$', line, re.IGNORECASE)
                    if line_with_units_match:
                        title_continuation = line_with_units_match.group(1).strip()
                        units_text = line_with_units_match.group(2).strip()
                        complete_title = f"{partial_title} {title_continuation}".strip()
                        break
                    
                    # Pattern 2: Units only on line
                    units_only_match = re.match(r'^(\d+(?:\.-)?(?:-\d+(?:\.\d+)?)?\s+UNITS?)\s*$', line, re.IGNORECASE)
                    if units_only_match:
                        units_text = units_only_match.group(1).strip()
                        break
                    
                    # Pattern 3: Units embedded anywhere in line
                    embedded_units_match = re.search(r'(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s+UNITS?)', line, re.IGNORECASE)
                    if embedded_units_match:
                        units_text = embedded_units_match.group(1).strip()
                        # Remove units from line to get remaining title content
                        line_without_units = re.sub(r'\s*\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s+UNITS?\s*', ' ', line, flags=re.IGNORECASE).strip()
                        if line_without_units:
                            complete_title = f"{partial_title} {line_without_units}".strip()
                        break
                    
                    # Pattern 4: Title continuation without units (keep looking)
                    if re.match(r'^[A-Za-z\s&,():-]+$', line) and not re.search(r'\d+\s+UNITS?', line, re.IGNORECASE):
                        complete_title = f"{partial_title} {line}".strip()
                        continue
                    
                    # If we hit a line that doesn't match our patterns, stop searching
                    break
            
            complete_title = re.sub(r'\s+', ' ', complete_title)
            
            candidate = {
                "title": complete_title,
                "course_id": course_id,
                "units": units_text
            }
            
            # Store or update candidate, preferring entries with units
            if course_id not in course_candidates:
                course_candidates[course_id] = candidate
            elif units_text and not course_candidates[course_id]['units']:
                # Replace with better candidate that has units
                course_candidates[course_id] = candidate
        
        # Add final candidates to courses list
        for course_id, candidate in course_candidates.items():
            if course_id not in global_added_course_ids:
                courses.append(candidate)
                global_added_course_ids.add(course_id)
        
        return courses

    # Regular department processing with candidate prioritization
    course_candidates = {}  # Track multiple instances of the same course
    
    for letter_alias in department_info.get('resolved_course_letters', []):
        course_letter_pattern = re.escape(letter_alias).replace("\\ ", r"\s+")
        
        # Updated regex to handle multi-line course entries
        # Pattern: COURSE_ID, PARTIAL_TITLE (on first line)
        # Followed by: TITLE_CONTINUATION UNITS (on subsequent lines within a reasonable window)
        course_start_regex = re.compile(
            r"^(" + course_letter_pattern + r"\s+[\w.-]+)" + # Group 1: Course ID
            r",\s+" +                                        # Comma and space
            r"(.+)$",                                        # Group 2: Partial title (rest of first line)
            re.MULTILINE
        )

        for match in course_start_regex.finditer(catalog_text):
            course_id = match.group(1).strip()
            partial_title = match.group(2).strip()
            
            # Skip cross-reference entries (mapping tables)
            if is_cross_reference_entry(course_id, partial_title, catalog_text, match.start()):
                continue
            
            # Skip combined course entries that end with "WITH"
            if is_combined_course_entry(course_id, partial_title):
                continue
                
            # Skip incomplete course lists/references
            if is_incomplete_course_list(course_id, partial_title):
                continue
            
            # Check if units are already in the partial title (single-line format)
            single_line_units_match = re.search(r'(.+?)\s+(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s+UNITS?)\s*$', partial_title, re.IGNORECASE)
            
            if single_line_units_match:
                # Single-line format: title and units are on the same line
                complete_title = single_line_units_match.group(1).strip()
                units_text = single_line_units_match.group(2).strip()
            else:
                # Multi-line format: need to search for continuation with enhanced unit detection
                # Find the end of the current line and start scanning subsequent lines
                line_end = catalog_text.find('\n', match.end())
                if line_end == -1:
                    line_end = len(catalog_text)
                
                # Define a more precise window to search for title continuation
                # Look ahead but stop at the next course entry or major section
                search_start = line_end + 1
                search_end = min(len(catalog_text), search_start + 400)  # Expanded window
                continuation_text = catalog_text[search_start:search_end]
                
                # Stop the search window at the next course entry to avoid cross-contamination
                next_course_pattern = r'^[A-Z]{2,}(?:\s[A-Z]+)?\s+[\w.-]+,'
                next_course_match = re.search(next_course_pattern, continuation_text, re.MULTILINE)
                if next_course_match:
                    # Truncate the search window to just before the next course
                    continuation_text = continuation_text[:next_course_match.start()]
                
                # Look for continuation lines that complete the title and contain units
                # Expanded to check more lines for better unit detection
                continuation_lines = continuation_text.split('\n')[:5]  # Check up to 5 lines
                
                complete_title = partial_title
                units_text = None
                
                for line in continuation_lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Enhanced unit detection patterns
                    # Pattern 1: Title continuation with units at end
                    line_with_units_match = re.match(r'^(.+?)\s+(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s+UNITS?)\s*$', line, re.IGNORECASE)
                    if line_with_units_match:
                        title_continuation = line_with_units_match.group(1).strip()
                        units_text = line_with_units_match.group(2).strip()
                        complete_title = f"{partial_title} {title_continuation}".strip()
                        break
                    
                    # Pattern 2: Units only on line
                    units_only_match = re.match(r'^(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s+UNITS?)\s*$', line, re.IGNORECASE)
                    if units_only_match:
                        units_text = units_only_match.group(1).strip()
                        break
                    
                    # Pattern 3: Units embedded anywhere in line (new pattern)
                    embedded_units_match = re.search(r'(\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s+UNITS?)', line, re.IGNORECASE)
                    if embedded_units_match:
                        units_text = embedded_units_match.group(1).strip()
                        # Remove units from line to get remaining title content
                        line_without_units = re.sub(r'\s*\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?\s+UNITS?\s*', ' ', line, flags=re.IGNORECASE).strip()
                        if line_without_units:
                            complete_title = f"{partial_title} {line_without_units}".strip()
                        break
                    
                    # Pattern 4: Title continuation without units (keep looking)
                    if re.match(r'^[A-Za-z\s&,():-]+$', line) and not re.search(r'\d+\s+UNITS?', line, re.IGNORECASE):
                        complete_title = f"{partial_title} {line}".strip()
                        continue
                    
                    # If we hit a line that doesn't match our patterns, stop searching
                    break
            
            # Clean up any extra whitespace in the complete title
            complete_title = re.sub(r'\s+', ' ', complete_title)
            
            candidate = {
                "title": complete_title,
                "course_id": course_id,
                "units": units_text
            }
            
            # Store or update candidate, preferring entries with units
            if course_id not in course_candidates:
                course_candidates[course_id] = candidate
            elif units_text and not course_candidates[course_id]['units']:
                # Replace with better candidate that has units
                course_candidates[course_id] = candidate

    # Add final candidates to courses list (with global deduplication)
    for course_id, candidate in course_candidates.items():
        if course_id not in global_added_course_ids:
            courses.append(candidate)
            global_added_course_ids.add(course_id)

    return courses

def main():
    """
    Main function to load data, parse courses for all departments,
    and save the results into a 'course_data' subdirectory.
    This script assumes it is run from within the 'data/SMC_catalog/' directory.
    """
    try:
        with open("smc_department_headers.json", 'r') as f:
            departments_data = json.load(f)
    except FileNotFoundError:
        print("Error: smc_department_headers.json not found in the current directory.")
        print("Please ensure this script is run from the 'data/SMC_catalog/' directory.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode smc_department_headers.json.")
        return

    try:
        with open("SMC_catalog.txt", 'r') as f:
            catalog_text = f.read()
    except FileNotFoundError:
        print("Error: SMC_catalog.txt not found in the current directory.")
        print("Please ensure this script is run from the 'data/SMC_catalog/' directory.")
        return

    output_dir = "course_data"
    os.makedirs(output_dir, exist_ok=True)

    total_courses_parsed = 0
    global_added_course_ids = set()  # Global deduplication set
    all_parsed_courses = []  # Collect all courses for final output

    for dept_entry in departments_data:
        # Work on a copy to add resolved_course_letters
        current_dept_info = dept_entry.copy()
        primary_course_letter = current_dept_info.get('course_letters')
        major_name = current_dept_info.get('major')

        if not major_name:
            print(f"Skipping department due to missing 'major': {current_dept_info}")
            continue

        # Handle different department types
        if major_name == "Independent Studies":
            # Special case: Independent Studies has courses from multiple departments with 88A/88B/88C numbering
            # Find all department prefixes that have Independent Studies courses (88A, 88B, or 88C)
            independent_studies_regex = re.compile(r"^([A-Z]{2,}(?:\s[A-Z]+)?)\s+88[ABC],\s+INDEPENDENT\s+STUDIES", re.MULTILINE | re.IGNORECASE)
            independent_matches = independent_studies_regex.findall(catalog_text)
            
            # Get unique department prefixes for Independent Studies
            resolved_letters = list(set(independent_matches))
            if not resolved_letters:
                print(f"Warning: No Independent Studies courses found with 88A/88B/88C pattern")
                resolved_letters = []  # Will result in no courses found, which is appropriate
            
        elif not primary_course_letter:
            print(f"Skipping department due to missing 'course_letters': {current_dept_info}")
            continue
        else:
            # Standard department processing
            resolved_letters = [primary_course_letter]
            note = current_dept_info.get('note', '')
            
            if note:
                # Handle different note formats
                if "also has a course letter" in note:
                    # Legacy format: extract aliases before the keyword phrase
                    text_before_keyword = note.split("also has a course letter", 1)[0]
                    potential_aliases = re.findall(r"\b([A-Z]{2,}(?:\s[A-Z]{1,})?)\b", text_before_keyword)
                    for alias in potential_aliases:
                        if alias not in resolved_letters:
                            resolved_letters.append(alias)
                elif note and not note.startswith("A bunch of"):
                    # Simple comma-delimited format: "ERTHSC" or "ANATMY, BOTANY, MCRBIO, NUTR, PHYS, ZOOL"
                    # Split by comma and clean up each alias
                    note_aliases = [alias.strip() for alias in note.split(',') if alias.strip()]
                    for alias in note_aliases:
                        # Validate that it looks like a course code (all caps, possibly with spaces)
                        if re.match(r'^[A-Z]{2,}(?:\s[A-Z]+)?$', alias) and alias not in resolved_letters:
                            resolved_letters.append(alias)
        
        current_dept_info['resolved_course_letters'] = resolved_letters

        print(f"Parsing courses for: {major_name} (using {', '.join(resolved_letters) if resolved_letters else 'NO COURSE LETTERS'})")
        department_courses = parse_courses_for_department(catalog_text, current_dept_info, global_added_course_ids)

        if department_courses:
            all_parsed_courses.extend(department_courses)
            total_courses_parsed += len(department_courses)
            print(f"  Successfully parsed {len(department_courses)} new courses for {major_name}.")
        else:
            print(f"  No new courses found for {major_name}.")
    
    # Now create individual department files based on logical department ownership
    department_course_groups = {}
    
    for course in all_parsed_courses:
        course_id = course['course_id']
        # Extract department prefix from course_id
        dept_prefix_match = re.match(r'^([A-Z]{2,}(?:\s[A-Z]+)?)', course_id)
        if dept_prefix_match:
            dept_prefix = dept_prefix_match.group(1)
            
            # Map department prefix back to logical department (including aliases)
            major_for_course = None
            
            # First check if this prefix is a primary course letter
            for dept_entry in departments_data:
                if dept_entry.get('course_letters') == dept_prefix:
                    major_for_course = dept_entry.get('major')
                    break
            
            # If not found as primary, check if it's an alias in note fields
            if not major_for_course:
                for dept_entry in departments_data:
                    note = dept_entry.get('note', '')
                    if note:
                        # Check both comma-delimited and "also has" formats
                        if "also has a course letter" in note:
                            text_before_keyword = note.split("also has a course letter", 1)[0]
                            potential_aliases = re.findall(r"\b([A-Z]{2,}(?:\s[A-Z]{1,})?)\b", text_before_keyword)
                            # Check for exact match or prefix match (e.g., STAT matches STAT C)
                            for alias in potential_aliases:
                                if dept_prefix == alias or dept_prefix.startswith(alias + " "):
                                    major_for_course = dept_entry.get('major')
                                    break
                            if major_for_course:
                                break
                        else:
                            # Simple comma-delimited format
                            note_aliases = [alias.strip() for alias in note.split(',') if alias.strip()]
                            for alias in note_aliases:
                                # Check for exact match or prefix match (e.g., STAT matches STAT C)
                                if dept_prefix == alias or dept_prefix.startswith(alias + " "):
                                    major_for_course = dept_entry.get('major')
                                    break
                            if major_for_course:
                                break
            
            # Special case for Independent Studies courses
            if not major_for_course and "88" in course_id:
                major_for_course = "Independent Studies"
            
            # Default fallback if no mapping found
            if not major_for_course:
                major_for_course = dept_prefix.lower().replace(' ', '_')
            
            if major_for_course not in department_course_groups:
                department_course_groups[major_for_course] = []
            department_course_groups[major_for_course].append(course)
    
    # Write individual department files
    for major_name, courses in department_course_groups.items():
        major_filename_part = major_name.lower().replace(' ', '_').replace('/', '_').replace('-', '_')
        output_filename = os.path.join(output_dir, f"{major_filename_part}_courses.json")
        
        with open(output_filename, 'w') as outfile:
            json.dump(courses, outfile, indent=4)
        print(f"  Saved {len(courses)} courses to {output_filename}")
    
    print(f"\nFinished parsing. Total unique courses parsed: {total_courses_parsed}")
    print(f"Total unique course IDs: {len(global_added_course_ids)}")
    print(f"Courses saved across {len(department_course_groups)} department files.")

if __name__ == "__main__":
    main() 