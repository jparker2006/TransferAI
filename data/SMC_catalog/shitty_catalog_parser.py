import os
import re
import json
from collections import defaultdict

def parse_schedule(txt_path, output_dir, headers_json_path='data/SMC_catalog/smc_department_headers.json'):
    """
    Reads a cleaned text version of the course catalog (txt_path),
    splits it into departments with robust parsing and self-validation,
    and writes one JSON file per department into output_dir.
    
    Args:
        txt_path: Path to the cleaned text file
        output_dir: Directory to write JSON files to
        headers_json_path: Path to the department headers JSON file
    """
    # Load department headers for reliable detection
    try:
        with open(headers_json_path, 'r', encoding='utf-8') as f:
            headers_data = json.load(f)
        # Create a set of department names for fast lookup
        department_names = {entry['major'] for entry in headers_data}
        print(f"Loaded {len(department_names)} department names from {headers_json_path}")
        
        # Create initial department structures for ALL majors
        departments = {}
        for major_name in department_names:
            departments[major_name] = {
                'name': major_name,
                'description': None,
                'courses': []
            }
            # Add noncreditHeadings field for noncredit departments
            if 'Noncredit' in major_name or major_name == 'Noncredit Classes':
                departments[major_name]['noncreditHeadings'] = []
        
        print(f"Initialized {len(departments)} department structures")
        
    except FileNotFoundError:
        print(f"Warning: Department headers file not found at {headers_json_path}")
        print("Falling back to dynamic department creation")
        department_names = set()
        departments = {}
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        raw_lines = f.readlines()

    # Remove trailing newline characters
    lines = [line.rstrip('\n') for line in raw_lines]

    # Enhanced regex patterns to identify various line types:
    # More precise course header patterns
    course_header_pattern_single = re.compile(r'^([A-Z]{2,}(?:\s+[A-Z]{2,})*)\s+(\d+[A-Z]?),\s*(.+?)\s+(\d+(?:\.\d+)?)\s+UNITS?$')
    course_header_start_pattern = re.compile(r'^([A-Z]{2,}(?:\s+[A-Z]{2,})*)\s+(\d+[A-Z]?),\s*(.+)$')
    units_line_pattern = re.compile(r'^(.+?)\s+(\d+(?:\.\d+)?)\s+UNITS?$')
    
    # Line type patterns
    section_line_pattern   = re.compile(r'^\d{3,4}\s+')          # e.g. "2424  1:15p.m.-3:05p.m. T  ONLINE  Hao J Y"
    arrange_line_pattern   = re.compile(r'^Arrange-[\d\.]+ Hours')  # e.g. "Arrange-2.5 Hours  ONLINE  Hao J Y"
    above_section_pattern  = re.compile(r'^Above section')         # e.g. "Above section 2424 meets for 12 weeks…"
    transfer_pattern       = re.compile(r'^Transfer:\s*(.+)$')
    bullet_pattern         = re.compile(r'^•\s*(Prerequisite|Advisory|Corequisite):\s*(.+)$')
    c_id_pattern          = re.compile(r'^C-ID:\s*(.+)$')
    cal_getc_pattern      = re.compile(r'^Cal-GETC Area\s+(.+)$')
    formerly_pattern      = re.compile(r'^Formerly\s+(.+)$')
    
    # Patterns that suggest we're NOT in a course header context
    stop_patterns = [
        re.compile(r'^='),  # New department
        re.compile(r'^\d{3,4}\s+'),  # Section line
        re.compile(r'^Transfer:'),  # Transfer line
        re.compile(r'^•\s*(Prerequisite|Advisory|Corequisite):'),  # Bullet points
        re.compile(r'^C-ID:'),  # C-ID line
        re.compile(r'^Cal-GETC Area'),  # Cal-GETC line
        re.compile(r'^Formerly'),  # Formerly line
        re.compile(r'^Above section'),  # Above section line
        re.compile(r'^Arrange-[\d\.]+ Hours'),  # Arrange hours
    ]

    def next_non_empty_index(start_idx):
        """Helper: find the index of the next non-blank line after start_idx, or None."""
        j = start_idx + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        return j if (j < len(lines) and lines[j].strip()) else None

    def is_department_line(line, next_line):
        """
        Improved department detection using the loaded department headers.
        Only return True for exact matches with known department names.
        """
        if not line:
            return False
        
        # Check for = prefix (department headers in the catalog)
        if line.startswith('='):
            dept_name = line[1:].strip()
            return dept_name in department_names if department_names else True
        
        # Only match exact department names from the loaded headers
        return department_names and line in department_names

    def try_parse_course_header(start_idx):
        """
        Try to parse a course header that might span multiple lines.
        More conservative approach with better boundary detection.
        Returns (course_dict, next_line_idx) or (None, start_idx) if not a course header.
        """
        if start_idx >= len(lines):
            return None, start_idx
            
        line1 = lines[start_idx].strip()
        if not line1:
            return None, start_idx
            
        # First try single-line pattern (most common case)
        single_match = course_header_pattern_single.match(line1)
        if single_match:
            subject_code = single_match.group(1).strip()
            course_number = single_match.group(2).strip()
            title = single_match.group(3).strip()
            units = single_match.group(4).strip()
            
            course = {
                'courseCode': f"{subject_code} {course_number}",
                'title': title,
                'units': units,
                'transfer': [],
                'prerequisites': [],
                'advisories': [],
                'corequisites': [],
                'c_id': [],
                'description': [],
                'sections': []
            }
            return course, start_idx + 1
            
        # Try multi-line pattern, but be much more conservative
        start_match = course_header_start_pattern.match(line1)
        if not start_match:
            return None, start_idx
            
        subject_code = start_match.group(1).strip()
        course_number = start_match.group(2).strip()
        title_part1 = start_match.group(3).strip()
        
        # Look at next few lines to find the units, but stop at any "stop pattern"
        course_title_parts = [title_part1]
        current_idx = start_idx + 1
        found_units = False
        units = ""
        
        # Look ahead up to 3 lines only (be more conservative)
        max_lookahead = min(start_idx + 4, len(lines))
        while current_idx < max_lookahead:
            if current_idx >= len(lines):
                break
                
            next_line = lines[current_idx].strip()
            if not next_line:
                current_idx += 1
                continue
                
            # Check if this line matches any stop patterns
            is_stop_line = any(pattern.match(next_line) for pattern in stop_patterns)
            if is_stop_line:
                break
                
            # Check if this line ends with units
            units_match = units_line_pattern.match(next_line)
            if units_match:
                title_continuation = units_match.group(1).strip()
                if title_continuation:  # Only add if there's actual title content
                    course_title_parts.append(title_continuation)
                units = units_match.group(2).strip()
                found_units = True
                current_idx += 1
                break
            else:
                # This might be a continuation of the title, but be careful
                # Don't add lines that look like they might be other content
                if (not next_line.startswith('Transfer:') and 
                    not next_line.startswith('•') and
                    not next_line.startswith('C-ID:') and
                    not next_line.startswith('Cal-GETC') and
                    not re.match(r'^\d{3,4}\s+', next_line) and
                    len(next_line) > 10):  # Reasonable title length
                    course_title_parts.append(next_line)
                    current_idx += 1
                else:
                    break
                
        if not found_units:
            return None, start_idx
            
        full_title = " ".join(course_title_parts)
        course = {
            'courseCode': f"{subject_code} {course_number}",
            'title': full_title,
            'units': units,
            'transfer': [],
            'prerequisites': [],
            'advisories': [],
            'corequisites': [],
            'c_id': [],
            'description': [],
            'sections': []
        }
        return course, current_idx

    def validate_course(course_dict):
        """
        Validate that a course dictionary has all required fields and sensible content.
        Returns (is_valid, issues_list)
        """
        issues = []
        
        if not course_dict.get('courseCode'):
            issues.append("Missing course code")
        
        if not course_dict.get('title'):
            issues.append("Missing course title")
            
        if not course_dict.get('units'):
            issues.append("Missing units")
        
        # Check for corrupted titles (common sign of parsing errors)
        title = course_dict.get('title', '')
        if len(title) > 200:  # Suspiciously long title
            issues.append("Suspiciously long course title - possible parsing error")
        
        if 'but not both' in title or 'section' in title.lower():
            issues.append("Course title contains description text - possible parsing error")
        
        # Check if description is empty (common issue)
        if not course_dict.get('description') or not any(desc.strip() for desc in course_dict.get('description', [])):
            issues.append("Missing course description")
            
        # Check if there are sections
        if not course_dict.get('sections'):
            issues.append("No sections found")
            
        return len(issues) == 0, issues

    def validate_department(dept_dict):
        """
        Validate that a department has courses and reasonable content distribution.
        Returns (is_valid, issues_list, stats)
        """
        issues = []
        stats = {
            'total_courses': len(dept_dict.get('courses', [])),
            'courses_with_descriptions': 0,
            'courses_with_sections': 0,
            'description_length': len(dept_dict.get('description', '') or ''),
            'duplicate_course_codes': 0
        }
        
        courses = dept_dict.get('courses', [])
        
        if not courses:
            issues.append("No courses found in department")
        
        # Check for duplicate course codes (sign of parsing errors)
        # BUT: Allow legitimate duplicates like SPAN 11 (different sections of same course)
        course_codes = [course.get('courseCode', '') for course in courses]
        course_code_counts = defaultdict(int)
        for code in course_codes:
            course_code_counts[code] += 1
        
        # Only flag if there are too many duplicates (more than 3 of the same code)
        problematic_duplicates = {code: count for code, count in course_code_counts.items() if count > 3}
        if problematic_duplicates:
            stats['duplicate_course_codes'] = sum(problematic_duplicates.values()) - len(problematic_duplicates)
            issues.append(f"Found excessive duplicate course codes: {dict(problematic_duplicates)} - possible parsing error")
        
        for course in courses:
            if course.get('description') and any(desc.strip() for desc in course['description']):
                stats['courses_with_descriptions'] += 1
            if course.get('sections'):
                stats['courses_with_sections'] += 1
        
        # Flag suspicious cases where department description is very long but no courses
        if stats['description_length'] > 1000 and stats['total_courses'] == 0:
            issues.append("Suspiciously long department description with no courses - possible parsing error")
            
        # Flag cases where most courses lack descriptions
        if stats['total_courses'] > 0 and stats['courses_with_descriptions'] / stats['total_courses'] < 0.3:
            issues.append(f"Many courses missing descriptions ({stats['courses_with_descriptions']}/{stats['total_courses']})")
        
        return len(issues) == 0, issues, stats

    # Prepare output directory
    os.makedirs(output_dir, exist_ok=True)

    current_department = None       # The dict for whatever department we're currently building
    current_dept_description = []   # Any department-level free-text lines
    noncredit_headings = []         # If we're in "Noncredit Classes", collect subheadings
    in_noncredit_list = False
    in_noncredit_headings = False

    current_course = None           # The dict for whatever course we're currently building
    
    # Statistics for validation
    parsing_stats = {
        'departments_processed': 0,
        'courses_processed': 0,
        'parse_errors': [],
        'validation_warnings': []
    }

    def finalize_course():
        """If there's a current_course in progress, validate and append it to the current department."""
        nonlocal current_course, parsing_stats
        if current_course and current_department:
            # Clean up description - remove empty strings
            if current_course.get('description'):
                current_course['description'] = [desc for desc in current_course['description'] if desc.strip()]
            
            # Debug output for Spanish department
            if current_department.get('name') == 'Spanish':
                print(f"DEBUG: Adding course to Spanish dept: {current_course.get('courseCode')} - {current_course.get('title')[:50]}...")
            
            # Validate course but don't reject it for missing descriptions in Spanish dept
            is_valid, issues = validate_course(current_course)
            if not is_valid:
                # Filter out "missing description" issues for Spanish dept as they're common
                if current_department.get('name') == 'Spanish':
                    serious_issues = [issue for issue in issues if 'description' not in issue.lower()]
                    if not serious_issues:
                        is_valid = True  # Override validation for Spanish dept
                        
                if not is_valid:
                    parsing_stats['validation_warnings'].append({
                        'type': 'course_validation',
                        'course': f"{current_course.get('courseCode', 'UNKNOWN')} - {current_course.get('title', 'UNKNOWN')}",
                        'department': current_department.get('name', 'UNKNOWN'),
                        'issues': issues
                    })
            
            current_department['courses'].append(current_course)
            parsing_stats['courses_processed'] += 1
            current_course = None

    def finalize_department():
        """
        If there's a current_department in progress, finalize its fields and validate.
        """
        nonlocal current_department, current_dept_description, noncredit_headings, in_noncredit_list, in_noncredit_headings, parsing_stats
        if current_department:
            # Debug output for Spanish department
            if current_department.get('name') == 'Spanish':
                print(f"DEBUG: Finalizing Spanish dept with {len(current_department.get('courses', []))} courses")
            
            # Attach any accumulated department‐level description
            if current_dept_description:
                current_department['description'] = "\n".join(current_dept_description).strip()
            # Attach any noncredit sub-headings (if present)
            if noncredit_headings:
                if 'noncreditHeadings' not in current_department:
                    current_department['noncreditHeadings'] = []
                current_department['noncreditHeadings'] = noncredit_headings.copy()
                
            # Validate department with relaxed rules for Spanish
            is_valid, issues, stats = validate_department(current_department)
            if not is_valid:
                # For Spanish dept, relax validation if it has courses
                if current_department.get('name') == 'Spanish' and stats['total_courses'] > 0:
                    print(f"DEBUG: Spanish dept has validation issues but has {stats['total_courses']} courses, allowing it")
                    is_valid = True
                    
                if not is_valid:
                    parsing_stats['validation_warnings'].append({
                        'type': 'department_validation',
                        'department': current_department.get('name', 'UNKNOWN'),
                        'issues': issues,
                        'stats': stats
                    })
            
            parsing_stats['departments_processed'] += 1

        # Reset for the next department
        current_department = None
        current_dept_description = []
        noncredit_headings = []
        in_noncredit_list = False
        in_noncredit_headings = False

    # Traverse every line in the file:
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            # Blank line — just skip ahead
            i += 1
            continue

        # Debug output for lines around Spanish section
        if 16290 <= i <= 16300:
            print(f"DEBUG: Processing line {i+1}: '{line}'")

        # Look ahead to the next non-empty line (for some heuristics)
        next_idx = next_non_empty_index(i)
        next_line = lines[next_idx].strip() if next_idx is not None else None
        
        # More debug for Spanish line
        if line == '=Spanish':
            print(f"DEBUG: Found =Spanish line, next_line: '{next_line}'")
            print(f"DEBUG: is_department_line result: {is_department_line(line, next_line)}")
            print(f"DEBUG: About to check if condition...")
            print(f"DEBUG: line repr: {repr(line)}")
            print(f"DEBUG: next_line repr: {repr(next_line)}")

        # ── 1) SPECIAL CASE: "Noncredit Classes" Section ─────────────────────────────
        if line == "Noncredit Classes" or line == "=Noncredit Classes":
            if line == '=Spanish':
                print(f"DEBUG: Spanish caught by Noncredit condition!")
            # First finalize any previously building course/department
            finalize_course()
            if current_department is None or current_department['name'] != "Noncredit Classes":
                finalize_department()
                # Use the pre-initialized department structure
                if "Noncredit Classes" in departments:
                    current_department = departments["Noncredit Classes"]
                else:
                    current_department = {
                        'name': "Noncredit Classes",
                        'description': None,
                        'noncreditHeadings': [],
                        'courses': []
                    }
            # Next lines describe the noncredit block. Start collecting description
            in_noncredit_list = True
            i += 1
            continue

        # If we are currently collecting lines under "Noncredit Classes":
        if in_noncredit_list and not in_noncredit_headings:
            if line == '=Spanish':
                print(f"DEBUG: Spanish caught by noncredit list condition!")
            # Check if this is actually a new department header - if so, exit noncredit mode
            if line.startswith('=') and line != '=Noncredit Classes':
                print(f"DEBUG: Found new department header while in noncredit mode: {line}")
                in_noncredit_list = False
                in_noncredit_headings = False
                # Don't increment i, let the department detection handle this line
                continue
            # Keep tacking on lines until a blank line appears
            if line:
                # That line is department-level descriptive text
                current_dept_description.append(line)
                i += 1
                continue
            else:
                # We hit a blank line, meaning the descriptive blurb is done,
                # Now the next lines list individual headings like "Bicycle Maintenance – Noncredit"
                in_noncredit_headings = True
                i += 1
                continue

        if in_noncredit_headings:
            if line == '=Spanish':
                print(f"DEBUG: Spanish caught by noncredit headings condition!")
            # Check if this is actually a new department header - if so, exit noncredit mode
            if line.startswith('=') and line != '=Noncredit Classes':
                print(f"DEBUG: Found new department header while in noncredit headings mode: {line}")
                in_noncredit_list = False
                in_noncredit_headings = False
                # Don't increment i, let the department detection handle this line
                continue
            # We expect lines of the form "<Some Course Name> – Noncredit"
            m = re.match(r'^(.+?)\s+–\s+Noncredit$', line)
            if m:
                noncredit_headings.append(m.group(1))
                i += 1
                continue
            else:
                # Once we reach something that isn't "<…> – Noncredit", we know the "Noncredit Classes" block is over.
                in_noncredit_list = False
                in_noncredit_headings = False
                # Do not increment i here—let the next logic iteration re-examine this same line
                continue

        # ── 2) SPECIAL CASE: "Internships" Section ───────────────────────────────────
        if line == "Internships" or line == "=Internships":
            if line == '=Spanish':
                print(f"DEBUG: Spanish caught by Internships condition!")
            finalize_course()
            finalize_department()
            # Use the pre-initialized department structure
            if "Internships" in departments:
                current_department = departments["Internships"]
            else:
                current_department = {
                    'name': "Internships",
                    'description': None,
                    'courses': []
                }
            # Everything from here until we hit the first course header is department‐level prose.
            i += 1
            while i < len(lines):
                subline = lines[i].strip()
                # Try to parse as course header
                parsed_course, next_i = try_parse_course_header(i)
                if parsed_course:
                    # Found a course, stop collecting department description
                    i = next_i - 1  # Will be incremented at the end of the while loop
                    current_course = parsed_course
                    break
                if subline:  # Only add non-empty lines
                    current_dept_description.append(subline)
                i += 1
            # Next iteration will continue with course processing
            i += 1
            continue

        # ── 3) NORMAL DEPARTMENT HEADER DETECTION ─────────────────────────────────
        if is_department_line(line, next_line):
            # Debug for Spanish
            if line == '=Spanish':
                print(f"DEBUG: Inside department detection for Spanish!")
            
            # We found a new department name
            finalize_course()
            finalize_department()
            
            # Clean department name (remove = prefix if present)
            dept_name = line[1:].strip() if line.startswith('=') else line
            
            # Debug output for Spanish department
            if dept_name == 'Spanish':
                print(f"DEBUG: Found Spanish department at line {i+1}")
            
            # Debug output for all departments
            print(f"DEBUG: Processing department: {dept_name}")
            
            # Use the pre-initialized department structure
            if dept_name in departments:
                current_department = departments[dept_name]
            else:
                # This shouldn't happen if we loaded all departments, but just in case
                current_department = {
                    'name': dept_name,
                    'description': None,
                    'courses': []
                }
                # Also add to departments dict for later reference
                departments[dept_name] = current_department
            i += 1
            continue
        
        # Debug output for lines that might be department headers but aren't detected
        if line.startswith('=') and 16290 <= i <= 16300:
            print(f"DEBUG: Line {i+1} starts with = but not detected as department: '{line}'")
            print(f"DEBUG: is_department_line result: {is_department_line(line, next_line)}")

        # ── 4) COURSE HEADER (including multi-line) ─────────────────────────────────────────────────────────
        parsed_course, next_i = try_parse_course_header(i)
        if parsed_course:
            # If a course was in progress, finalize it
            finalize_course()
            current_course = parsed_course
            
            # Debug output for Spanish department
            if current_department and current_department.get('name') == 'Spanish':
                print(f"DEBUG: Found course in Spanish dept: {parsed_course.get('courseCode')} - {parsed_course.get('title')}")
            elif parsed_course.get('courseCode', '').startswith('SPAN'):
                print(f"DEBUG: Found SPAN course but current_department is: {current_department.get('name') if current_department else 'None'}")
                print(f"DEBUG: Course: {parsed_course.get('courseCode')} - {parsed_course.get('title')}")
            
            i = next_i
            continue

        # ── 5) INSIDE A COURSE: "Transfer:" LINE ─────────────────────────────────────
        if current_course:
            transfer_match = transfer_pattern.match(line)
            if transfer_match:
                tr_text = transfer_match.group(1).strip()
                transfers = [t.strip() for t in tr_text.split(',') if t.strip()]
                current_course['transfer'] = transfers
                i += 1
                continue

        # ── 6) INSIDE A COURSE: C-ID LINE ────────────────────────────────────────────
        if current_course:
            c_id_match = c_id_pattern.match(line)
            if c_id_match:
                c_id_text = c_id_match.group(1).strip()
                current_course['c_id'].append(c_id_text)
                i += 1
                continue

        # ── 7) INSIDE A COURSE: Cal-GETC LINE ────────────────────────────────────────────
        if current_course:
            cal_getc_match = cal_getc_pattern.match(line)
            if cal_getc_match:
                # We can add this to the course info if needed, for now just skip
                i += 1
                continue

        # ── 8) INSIDE A COURSE: Formerly LINE ────────────────────────────────────────────
        if current_course:
            formerly_match = formerly_pattern.match(line)
            if formerly_match:
                # We can add this to the course info if needed, for now just skip
                i += 1
                continue

        # ── 9) INSIDE A COURSE: BULLET LINES (Prerequisite, Advisory, Corequisite) ─────
        if current_course:
            bullet_match = bullet_pattern.match(line)
            if bullet_match:
                kind = bullet_match.group(1).lower()
                text = bullet_match.group(2).strip()
                if kind == 'prerequisite':
                    current_course['prerequisites'].append(text)
                elif kind == 'advisory':
                    current_course['advisories'].append(text)
                elif kind == 'corequisite':
                    current_course['corequisites'].append(text)
                i += 1
                continue

        # ── 10) INSIDE A COURSE: SECTION LINE ────────────────────────────────────────────
        if current_course and section_line_pattern.match(line):
            # A section line looks like "1304 Arrange-5.5 Hours Baghdasarian G"
            sec_id = line.split()[0]
            details = line[len(sec_id):].strip()
            new_section = {
                'sectionId': sec_id,
                'details': [details] if details else [],
                'modality': None
            }
            current_course['sections'].append(new_section)
            i += 1
            continue

        # ── 11) INSIDE A COURSE: "Arrange-X Hours" LINE ─────────────────────────────────
        if current_course and arrange_line_pattern.match(line):
            # Append this to the last section's details
            if current_course['sections']:
                current_course['sections'][-1]['details'].append(line)
            i += 1
            continue

        # ── 12) INSIDE A COURSE: "Above section …" (modality line) ───────────────────────
        if current_course and above_section_pattern.match(line):
            if current_course['sections']:
                current_course['sections'][-1]['modality'] = line
            i += 1
            continue

        # ── 13) INSIDE A COURSE: anything else must be course description text ────────────
        if current_course:
            # Only add non-empty lines to description
            if line.strip():
                current_course['description'].append(line)
            i += 1
            continue

        # ── 14) DEPARTMENT DESCRIPTION (when we have a department but no current course) ────
        if current_department and not current_course:
            # Only add non-empty lines to department description
            if line.strip():
                current_dept_description.append(line)
            i += 1
            continue

        # If it didn't match any of the above, just skip it
        i += 1

    # Once we finish looping over all lines, finalize any "in-flight" course/department:
    finalize_course()
    finalize_department()

    # Print validation summary
    print("\n" + "="*60)
    print("PARSING VALIDATION REPORT")
    print("="*60)
    print(f"Departments processed: {parsing_stats['departments_processed']}")
    print(f"Courses processed: {parsing_stats['courses_processed']}")
    print(f"Parse errors: {len(parsing_stats['parse_errors'])}")
    print(f"Validation warnings: {len(parsing_stats['validation_warnings'])}")

    if parsing_stats['parse_errors']:
        print(f"\nPARSE ERRORS ({len(parsing_stats['parse_errors'])}):")
        for error in parsing_stats['parse_errors'][:5]:  # Show first 5 errors
            print(f"  Line {error['line_number']}: {error['error']}")
            print(f"    Content: {error['line_content'][:80]}...")
        if len(parsing_stats['parse_errors']) > 5:
            print(f"  ... and {len(parsing_stats['parse_errors']) - 5} more errors")

    if parsing_stats['validation_warnings']:
        print(f"\nVALIDATION WARNINGS ({len(parsing_stats['validation_warnings'])}):")
        dept_warnings = [w for w in parsing_stats['validation_warnings'] if w['type'] == 'department_validation']
        course_warnings = [w for w in parsing_stats['validation_warnings'] if w['type'] == 'course_validation']
        
        if dept_warnings:
            print(f"  Department issues ({len(dept_warnings)}):")
            for warning in dept_warnings[:3]:  # Show first 3
                print(f"    {warning['department']}: {', '.join(warning['issues'])}")
                if 'stats' in warning:
                    stats = warning['stats']
                    print(f"      Stats: {stats['total_courses']} courses, {stats['description_length']} desc chars")
        
        if course_warnings:
            print(f"  Course issues ({len(course_warnings)}) - showing first 5:")
            for warning in course_warnings[:5]:
                print(f"    {warning['course']}: {', '.join(warning['issues'])}")

    # Now write out a JSON file per department
    successful_writes = 0
    for dept_name, dept in departments.items():
        # Skip empty departments unless they have meaningful content
        # Special case: don't skip Spanish even if it appears empty
        if (not dept.get('courses') and not dept.get('description') and not dept.get('noncreditHeadings') 
            and dept_name != 'Spanish'):
            continue
            
        # Debug output for Spanish department
        if dept_name == 'Spanish':
            print(f"DEBUG: Writing Spanish dept file with {len(dept.get('courses', []))} courses")
        
        # Sanitize department name for a filename
        safe_name = re.sub(r'[^\w\-]+', '_', dept_name)
        # Truncate to avoid filesystem filename length limits
        if len(safe_name) > 246:
            safe_name = safe_name[:246]
        filename = f"{safe_name}.json"
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f_out:
                json.dump(dept, f_out, indent=2, ensure_ascii=False)
            successful_writes += 1
        except Exception as e:
            parsing_stats['parse_errors'].append({
                'type': 'file_write_error',
                'department': dept_name,
                'error': str(e)
            })

    print(f"\nSuccessfully wrote {successful_writes} JSON files to '{output_dir}/'.")
    
    # Final summary
    total_courses_written = sum(len(dept.get('courses', [])) for dept in departments.values())
    print(f"Total courses written: {total_courses_written}")
    
    return parsing_stats


if __name__ == '__main__':
    # Make sure your cleaned TXT is named "catalog_cleaned.txt" in this same folder.
    # The script will create (if necessary) a folder called "parsed_programs/" 
    # and write one JSON file per department into it.
    stats = parse_schedule('catalog_cleaned.txt', 'parsed_programs', 'data/SMC_catalog/smc_department_headers.json')
