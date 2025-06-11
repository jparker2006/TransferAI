# This script will be responsible for parsing detailed course information
# from the SMC course catalog PDF. It will use the department and page
# information (from smc_department_headers.json) to locate and extract
# data for each course, including course code, title, units, description,
# prerequisites, and transferability.

import fitz  # PyMuPDF
import re
import os
import json
from datetime import datetime

# --- Constants ---
# Assumes the script is run from the workspace root or paths are adjusted accordingly.
# The user's workspace root is /home/jparker/TransferAI
SMC_CATALOG_PATH_RELATIVE = "data/SMC_catalog/253-SMCschedule.pdf" # Relative to workspace root
ABSOLUTE_TARGET_JSON_PATH = "/home/jparker/TransferAI/data/SMC_catalog/course_data/accounting_courses.json"

# Accounting department is on pages 13 and 14
ACCOUNTING_PAGES_0_INDEXED = [12, 13]  # Pages 13 and 14

# Visual characteristics for course titles - Updated based on PRINT_SPAN_INFO output
COURSE_TITLE_FONT_PATTERN = 'ITCFranklinGothicStd-Dem' 
MIN_COURSE_TITLE_SIZE = 7.8 # Target size is ~7.96
MAX_COURSE_TITLE_SIZE = 8.2
COURSE_TITLE_COLOR = 0  # Black

# Font characteristics for course descriptions 
# Adjusted based on hypothesis - CONFIRM WITH DEBUG FROM ACCTG 1's ACTUAL DESCRIPTION LINES
DESCRIPTION_FONT_NAME = 'Calibri' # Sticking with Calibri for now as ACCTG 17 worked.
                                  # If ACCTG 1 uses TimesNewRoman or other, this MUST change.
DESCRIPTION_FONT_SIZE_TARGET = 7.2 # Slightly more general than 7.27
DESCRIPTION_FONT_SIZE_TOLERANCE = 0.4 # Slightly wider tolerance
DESCRIPTION_TEXT_COLOR = 0 

# Regex to identify lines that start with a course code like "ACCTG 1,"
# This is general, but for accounting, we expect ACCTG.
COURSE_CODE_PREFIX_RE = re.compile(r"^([A-Z]{2,5}\s*\d{1,3}[A-Z]?)[.,]\s*(.+)$") # Capture code and title separately
UNITS_LINE_RE = re.compile(r"^(\d{1,2}(?:\.\d)?)\s+UNITS?$", re.IGNORECASE) # Capture the number of units

# Regex for lines that typically end a description
DESCRIPTION_END_MARKERS_RE = re.compile(
    r"^(?:Prerequisite(?:s)?:|Advisory:|•\s*Prerequisite(?:s)?:|•\s*Advisory:|C-ID:|Course(?:s)? Note:|Note:|Hours:|Topics include)", 
    re.IGNORECASE
)
TRANSFER_LINE_RE = re.compile(r"Transfer:.*UC.*CSU|Transfer:.*CSU|Transfer:.*UC", re.IGNORECASE)

# --- Temporary Debug Flag ---
PRINT_SPAN_INFO = True # Set to True for debugging
DEBUG_VERBOSE = True # Additional debugging

def is_schedule_line(text: str) -> bool:
    """Check if a line appears to be a class schedule item rather than a description."""
    text = text.strip()
    # Regex for typical time patterns, e.g., "8:00a.m.-9:50a.m.", "6:00p.m.", "Arrange-X.X Hours"
    time_pattern = r"(\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.|am|pm)?(?:\s*-\s*\d{1,2}:\d{2}\s*(?:a\.m\.|p\.m\.|am|pm)?)?|Arrange-\d{1,2}(?:\.\d)?\s+Hours)"
    # Regex for days of the week patterns, possibly combined with instructor initials/names
    days_pattern = r"^(?:[MWFTSU]|(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)|(?:TBA)|(?:ONLINE))(?:\s+[A-Z]{1,2}\s*[A-Z]?)?(?:\s+[A-Za-z]+(?:\s+[A-Z]\.?)?)?$"
    # Regex for section numbers or typical schedule codes (e.g., 4-digit number, possibly with letters, often at start)
    section_code_pattern = r"^\d{4}[A-Z]?(\s|$)"
    # Regex for typical instructor name patterns (e.g., Smith J A, Doe John R)
    instructor_pattern = r"^[A-Z][a-z']+(?:\s+[A-Z][a-z']+)?(?:\s+[A-Z](?:\s?[A-Z])?){1,2}$"
    
    # Keywords often found in schedule lines
    schedule_keywords = [
        "ONLINE", "ON GROUND", "HYBRID", "Room", "TBA", "Staff", "Flexible",
        "meets for", "weeks", "section modality is", "hours per week",
        "LEC", "LAB", "ACT"
    ]

    if text.lower().startswith("transfer:"):
        return True
    if re.search(time_pattern, text, re.IGNORECASE):
        return True
    if re.match(days_pattern, text):
        return True
    if re.match(instructor_pattern, text) and len(text.split()) <= 4: # Avoid matching short descriptive sentences
        return True
    if re.match(section_code_pattern, text):
        # Further check if it looks like a course code itself (e.g. ACCTG 101) to avoid false positives
        if COURSE_CODE_PREFIX_RE.match(text):
            return False # It is a course code, not a schedule line
        return True
        
    for keyword in schedule_keywords:
        if keyword.lower() in text.lower():
            return True
    # Very short lines with mostly numbers/symbols might also be schedule details
    if len(text) < 15 and re.search(r"[\d\W]", text) and not re.search(r"[a-z]{3,}", text, re.IGNORECASE):
        if any(day in text for day in ["M", "T", "W", "Th", "F", "S", "Su"]) and re.search(r"\d", text):
            return True # Looks like Days + Number, likely schedule

    return False

def parse_course_info(title_text, units_text=None):
    """Parse a course title and units into structured data."""
    # Check for units suffix in the title_text itself, e.g., "ADVANCED EXCEL FOR ACCOUNTING 3 UNITS"
    units_from_title_match = re.search(r"\s+(\d{1,2}(?:\.\d)?)\s+UNITS?$", title_text, re.IGNORECASE)
    parsed_units = None
    cleaned_title_text = title_text.strip()

    if units_from_title_match:
        parsed_units = float(units_from_title_match.group(1))
        # Remove the units part from the title
        cleaned_title_text = title_text[:units_from_title_match.start()].strip()
        if DEBUG_VERBOSE:
            print(f"    [DEBUG] parse_course_info: Extracted units {parsed_units} from title suffix. Cleaned title: '{cleaned_title_text}'")

    match = COURSE_CODE_PREFIX_RE.match(cleaned_title_text)
    if not match:
        if DEBUG_VERBOSE:
            print(f"    [DEBUG] parse_course_info: COURSE_CODE_PREFIX_RE did not match cleaned title: '{cleaned_title_text}'")
        return None
    
    course_letters = match.group(1).strip()
    course_title = match.group(2).strip()
    
    # If units were passed as a separate argument and not found in title, use argument
    if units_text and parsed_units is None:
        units_match_arg = UNITS_LINE_RE.match(units_text.strip())
        if units_match_arg:
            parsed_units = float(units_match_arg.group(1))
            if DEBUG_VERBOSE:
                print(f"    [DEBUG] parse_course_info: Used units {parsed_units} from units_text argument.")
    
    return {
        "course_letters": course_letters,
        "course_title": course_title,
        "units": parsed_units # This will be None if no units were found in title or argument
    }

def extract_accounting_courses_from_page(doc: fitz.Document, page_num_0_indexed: int) -> list[dict]:
    """Extract accounting course information from a specific page."""
    extracted_courses = []
    
    try:
        page = doc.load_page(page_num_0_indexed)
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE)

        active_course_details = None # Holds the course being actively processed (title, units parsed)
        description_accumulator = [] # Accumulates lines for the active_course_s description
        page_courses_final = [] # Final list of courses for this page

        # State machine: "IDENTIFYING_TITLE", "COLLECTING_DESCRIPTION"
        current_state = "IDENTIFYING_TITLE"

        for block_idx, block in enumerate(page_dict.get("blocks", [])):
            if block.get("type") == 0:  # Text block
                block_lines = block.get("lines", [])
                for line_idx, line in enumerate(block_lines):
                    line_spans = line.get("spans", [])
                    raw_line_text = "".join([s.get("text", "") for s in line_spans]).strip()
                    
                    # --- Try to identify a new course title (Always active for IDENTIFYING_TITLE state) ---
                    # This logic attempts to detect a course title based on styling and content.
                    styled_text_parts_for_title = []
                    is_target_style_line = False
                    for span in line_spans:
                        if span.get("font", "") == COURSE_TITLE_FONT_PATTERN and \
                           abs(span.get("size", 0) - 7.96) < 0.3 and \
                           span.get("color", 0) == COURSE_TITLE_COLOR:
                            styled_text_parts_for_title.append(span.get("text", ""))
                            is_target_style_line = True 
                        else:
                            # If part of the line is not target style, it might not be a pure title line
                            # For simplicity now, if any span is not target, we might reconsider it as full title
                            # but let's accumulate styled parts first.
                            pass 

                    potential_title_text = "".join(styled_text_parts_for_title).strip()
                    is_course_code_line = COURSE_CODE_PREFIX_RE.match(potential_title_text)
                    is_units_line_styled = UNITS_LINE_RE.match(potential_title_text)
                    
                    # Preemptive check for end markers if collecting description
                    if current_state == "COLLECTING_DESCRIPTION" and active_course_details:
                        if DESCRIPTION_END_MARKERS_RE.search(raw_line_text) or (is_course_code_line and raw_line_text != active_course_details.get("course_letters")):
                            if DEBUG_VERBOSE:
                                print(f"  [DEBUG] Description end marker '{raw_line_text[:30]}...' or new course found for {active_course_details['course_letters']}.")
                            if description_accumulator:
                                active_course_details["description"] = " ".join(description_accumulator).replace("  ", " ").strip()
                                if DEBUG_VERBOSE:
                                    print(f"    [DEBUG] Finalized description for {active_course_details['course_letters']}: '{active_course_details['description'][:50]}...'")
                            page_courses_final.append(active_course_details) # Add completed course
                            active_course_details = None
                            description_accumulator = []
                            current_state = "IDENTIFYING_TITLE" # Reset state
                            # Fall through to process this line as a potential new title if it is_course_code_line

                    # --- State: IDENTIFYING_TITLE ---
                    if current_state == "IDENTIFYING_TITLE":
                        if is_target_style_line and is_course_code_line:
                            parsed_info = parse_course_info(potential_title_text, None) 
                            if parsed_info and parsed_info["course_letters"].upper().startswith("ACCTG"):
                                if active_course_details: 
                                    # Finalize any previously active course before starting new one
                                    if description_accumulator:
                                        active_course_details["description"] = " ".join(description_accumulator).replace("  ", " ").replace(" \n ", "\n").strip()
                                    else:
                                        active_course_details["description"] = ""
                                    page_courses_final.append(active_course_details)
                                    if DEBUG_VERBOSE:
                                        print(f"  [DEBUG] Finalized (due to new title) {active_course_details.get('course_letters')} with desc: '{active_course_details.get('description', '')[:30]}...'")
                                
                                active_course_details = parsed_info
                                description_accumulator = [] 
                                
                                if DEBUG_VERBOSE:
                                    print(f"  [DEBUG] Identified Course Initial: {active_course_details['course_letters']} - '{active_course_details['course_title']}'. Looking for continued title/units.")

                                # Greedily consume subsequent styled lines as part of the title if they match style
                                # and are not new course codes or units lines for a *different* course.
                                next_line_idx_offset = 1
                                while True:
                                    if line_idx + next_line_idx_offset < len(block_lines):
                                        next_line_obj = block_lines[line_idx + next_line_idx_offset]
                                        next_line_spans = next_line_obj.get("spans", [])
                                        next_line_raw_text = "".join([s.get("text", "") for s in next_line_spans]).strip()
                                        
                                        is_next_styled = False
                                        next_styled_parts = []
                                        for span in next_line_spans:
                                            if span.get("font", "") == COURSE_TITLE_FONT_PATTERN and \
                                               abs(span.get("size", 0) - 7.96) < 0.3 and \
                                               span.get("color", 0) == COURSE_TITLE_COLOR:
                                                next_styled_parts.append(span.get("text", ""))
                                                is_next_styled = True
                                            else:
                                                is_next_styled = False # Whole line must be styled title font
                                                break
                                        
                                        potential_next_title_part = "".join(next_styled_parts).strip()

                                        if is_next_styled and potential_next_title_part and \
                                           not COURSE_CODE_PREFIX_RE.match(potential_next_title_part) and \
                                           not UNITS_LINE_RE.match(potential_next_title_part):
                                            active_course_details['course_title'] += " " + potential_next_title_part
                                            if DEBUG_VERBOSE:
                                                print(f"    [DEBUG] Appended to title: '{potential_next_title_part}'. New title: '{active_course_details['course_title']}'")
                                            # Mark this line as "consumed" by incrementing outer loop's effective index indirectly
                                            # This is tricky; direct manipulation of `line_idx` in inner loop is bad.
                                            # Simplest for now is to rely on the outer loop to advance and re-evaluate.
                                            # A better way would be to use a `consumed_until_idx` for the outer loop.
                                            # For now, this just gathers. The outer loop will process it again and skip via state.
                                            # We need a way to truly skip it in the outer loop.
                                            # Let's assume for now the state change handles it; if not, refine skipping.
                                            next_line_idx_offset += 1 # Look at the line after this one
                                        else:
                                            break # Not a styled continuation of the title
                                    else:
                                        break # No more lines in block
                                
                                current_state = "COLLECTING_DESCRIPTION" 
                                if DEBUG_VERBOSE:
                                     print(f"  [DEBUG] Finalized Title: {active_course_details['course_letters']} - '{active_course_details['course_title']}'. State: {current_state}")
                                # We continue to the next line in the outer loop. If title lines were consumed,
                                # their re-evaluation should ideally be handled by state or explicit skip. 
                                # The current `continue` here is for the initial title finding line.
                                continue 
                    
                    # --- State: COLLECTING_DESCRIPTION (and refining active_course_details) ---
                    if current_state == "COLLECTING_DESCRIPTION" and active_course_details:
                        # First, determine if the current line predominantly matches description font style
                        is_description_font_line = False
                        num_desc_font_spans = 0
                        num_total_text_spans = 0

                        if line_spans: 
                            for span_idx, span_val in enumerate(line_spans):
                                if span_val.get("text", "").strip(): # Count only spans with actual text
                                    num_total_text_spans +=1
                                    # DEBUG: Print span info for lines being considered in COLLECTING_DESCRIPTION state
                                    # This will help us see the font of ACCTG 1's actual description.
                                    if DEBUG_VERBOSE:
                                        print(f"      [SPAN_CHECK] Line: '{raw_line_text[:30]}...', Span {span_idx}: F='{span_val.get('font')}', S={span_val.get('size'):.2f}, C={span_val.get('color')}, Txt='{span_val.get('text')[:20]}...'")
                                    
                                    if span_val.get("font", "") == DESCRIPTION_FONT_NAME and \
                                       abs(span_val.get("size", 0) - DESCRIPTION_FONT_SIZE_TARGET) < DESCRIPTION_FONT_SIZE_TOLERANCE and \
                                       span_val.get("color", 0) == DESCRIPTION_TEXT_COLOR:
                                        num_desc_font_spans += 1
                            
                            if num_total_text_spans > 0 and (num_desc_font_spans / num_total_text_spans) > 0.6:
                                is_description_font_line = True
                                if DEBUG_VERBOSE and raw_line_text.strip():
                                    print(f"        [DEBUG] Line '{raw_line_text[:30]}...' MATCHED description font criteria.")
                            elif DEBUG_VERBOSE and raw_line_text.strip() and num_total_text_spans > 0 : # Only print if it had text and didn't match
                                print(f"        [DEBUG] Line '{raw_line_text[:30]}...' DID NOT match description font. DescSpans: {num_desc_font_spans}/{num_total_text_spans}.")

                        # Check for Units for the active course (often title-styled)
                        if is_target_style_line and is_units_line_styled and not active_course_details.get("units"):
                            units_match = UNITS_LINE_RE.match(potential_title_text)
                            if units_match:
                                active_course_details["units"] = float(units_match.group(1))
                                if DEBUG_VERBOSE:
                                    print(f"    [DEBUG] Added units {active_course_details['units']} for {active_course_details['course_letters']}")
                                continue 
                        
                        # Now, handle description accumulation or termination
                        # A line that is NOT description font OR is an end marker might terminate current description.
                        if not is_description_font_line or DESCRIPTION_END_MARKERS_RE.search(raw_line_text):
                            # If it's an end marker, and we have accumulated description, finalize.
                            # Or, if font changes AND it's not just an empty line (which we allow).
                            if (DESCRIPTION_END_MARKERS_RE.search(raw_line_text) or (not is_description_font_line and raw_line_text)) \
                               and active_course_details and description_accumulator:
                                if DEBUG_VERBOSE:
                                    print(f"  [DEBUG] Font change or end marker '{raw_line_text[:30]}...' detected for {active_course_details['course_letters']}.")
                                final_desc = " ".join(description_accumulator).replace("  ", " ").replace(" \n ", "\n").strip()
                                active_course_details["description"] = final_desc
                                page_courses_final.append(active_course_details) 
                                if DEBUG_VERBOSE:
                                    print(f"    [DEBUG] Finalized description (font/marker) for {active_course_details['course_letters']}: '{final_desc[:50]}...'")
                                active_course_details = None
                                description_accumulator = []
                                current_state = "IDENTIFYING_TITLE"
                                # Re-evaluate current line as a potential new title if it was an end marker that is also a title
                                if is_course_code_line and is_target_style_line: # current line might start a new course
                                    # This will be handled by the next iteration of the outer loop with state IDENTIFYING_TITLE
                                    pass 
                                else:
                                    continue # Line processed as end of description, not a new title itself
                        
                        # If, after all checks, we are still in COLLECTING_DESCRIPTION and it IS a description font line:
                        if current_state == "COLLECTING_DESCRIPTION" and active_course_details and is_description_font_line:
                            if not is_schedule_line(raw_line_text): # Filter out schedule lines even if they match font (unlikely for narrative)
                                if raw_line_text: # Avoid adding empty strings from purely empty lines
                                    description_accumulator.append(raw_line_text)
                                    if DEBUG_VERBOSE:
                                        print(f"    [DEBUG] Potential desc line (font match) for {active_course_details['course_letters']}: '{raw_line_text[:70]}...'")
                                        for s_idx, s_val in enumerate(line_spans):
                                            print(f"      [DEBUG] Span {s_idx}: F='{s_val.get('font')}', S={s_val.get('size'):.2f}, C={s_val.get('color')}, Txt='{s_val.get('text')[:30]}...'")
                                elif description_accumulator: # Allow empty lines if already accumulating (paragraph break)
                                    description_accumulator.append("\n")
                            elif DEBUG_VERBOSE and raw_line_text:
                                print(f"    [DEBUG] Filtered schedule line (though matched desc font) for {active_course_details.get('course_letters', 'N/A')}: '{raw_line_text[:50]}...'")
                        elif current_state == "COLLECTING_DESCRIPTION" and active_course_details and not raw_line_text and description_accumulator:
                            # Handle empty lines if they are not explicitly font-matched but we are in middle of description
                            description_accumulator.append("\n")
                            if DEBUG_VERBOSE:
                                print(f"    [DEBUG] Added newline for potential paragraph break for {active_course_details['course_letters']}")

            # --- End of lines in a block ---
            # If collecting description for a course and block ends, description might continue or end.
            # Handled by new course detection or end of page.

        # --- End of all blocks on a page ---
        if active_course_details: # If a course was active at end of page, finalize it
            if DEBUG_VERBOSE:
                print(f"  [DEBUG] Finalizing course {active_course_details['course_letters']} at end of page.")
            
            final_description = ""
            if description_accumulator:
                final_description = " ".join(description_accumulator).replace("  ", " ").replace(" \n ", "\n").strip()
                if DEBUG_VERBOSE:
                    print(f"    [DEBUG] Finalized description (end of page) for {active_course_details['course_letters']}: '{final_description[:50]}...'")
            active_course_details["description"] = final_description # Always add description key

            page_courses_final.append(active_course_details)
            active_course_details = None # Reset for safety
            description_accumulator = []
            current_state = "IDENTIFYING_TITLE"
        
        if DEBUG_VERBOSE:
            print(f"[DEBUG] Page {page_num_0_indexed + 1} processing done. Final course count for page: {len(page_courses_final)}")       
        return page_courses_final

    except Exception as e:
        print(f"Error processing page {page_num_0_indexed + 1}: {e}")
        return []

def save_courses_to_json(courses, filename: str):
    """Save courses data to a JSON file. Expects filename to be a complete absolute path."""
    print(f"DEBUG: save_courses_to_json received filename: {filename}") # Debug print
    try:
        # Ensure the directory exists
        output_dir = os.path.dirname(filename)
        print(f"DEBUG: output_dir calculated as: {output_dir}") # Debug print
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(courses, f, indent=2, ensure_ascii=False)
        return filename
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        return None

if __name__ == "__main__":
    print("SMC Accounting Course Parser")
    print("=" * 40)
    
    # Explicitly define the workspace root for input PDF path resolution.
    user_workspace_root = "/home/jparker/TransferAI"

    # Construct absolute path for the input PDF.
    absolute_pdf_input_path = os.path.join(user_workspace_root, SMC_CATALOG_PATH_RELATIVE)

    if not os.path.exists(absolute_pdf_input_path):
        # Fallback check: if the script is run from a location where the relative path works directly
        if os.path.exists(SMC_CATALOG_PATH_RELATIVE):
            print(f"Found PDF via relative path: {SMC_CATALOG_PATH_RELATIVE}, but will use absolute path if possible.")
            # Prefer to use the fully resolved path if it was correctly constructed
            # This case implies user_workspace_root might not be the CWD's parent in the expected way,
            # but the file is still found. For opening, it's safer to use what's found.
            pdf_to_open = SMC_CATALOG_PATH_RELATIVE 
        else:
            print(f"Error: PDF file not found at {absolute_pdf_input_path} or {SMC_CATALOG_PATH_RELATIVE} (relative to CWD).")
            print(f"Please ensure {SMC_CATALOG_PATH_RELATIVE} exists relative to {user_workspace_root} or current directory.")
            exit(1)
    else:
        print(f"Found PDF: {absolute_pdf_input_path}")
        pdf_to_open = absolute_pdf_input_path

    doc = None
    all_accounting_courses = []
    
    try:
        doc = fitz.open(pdf_to_open) # Use the determined path to open the PDF
        print(f"Processing {len(doc)} total pages...")
        
        for page_num_0_idx in ACCOUNTING_PAGES_0_INDEXED:
            print(f"Extracting courses from page {page_num_0_idx + 1}...")
            page_courses = extract_accounting_courses_from_page(doc, page_num_0_idx)
            if page_courses:
                print(f"  Found {len(page_courses)} courses")
                all_accounting_courses.extend(page_courses)
            else:
                print(f"  No courses found")

        # Remove duplicates based on course_letters
        unique_courses = []
        seen_codes = set()
        for course in all_accounting_courses:
            if course["course_letters"] not in seen_codes:
                unique_courses.append(course)
                seen_codes.add(course["course_letters"])

        if unique_courses:
            # Save to JSON using the predefined absolute path
            saved_filename = save_courses_to_json(unique_courses, filename=ABSOLUTE_TARGET_JSON_PATH)
            if saved_filename:
                print(f"\n✅ Successfully extracted {len(unique_courses)} accounting courses")
                print(f"📁 Saved to: {saved_filename}") # This will print the ABSOLUTE_TARGET_JSON_PATH
                
                # Preview first few courses
                print(f"\nPreview (first 3 courses):")
                for i, course in enumerate(unique_courses[:3]):
                    units_str = f"{course['units']} units" if course['units'] else "units TBD"
                    print(f"  {i+1}. {course['course_letters']}: {course['course_title']} ({units_str})")
                
                if len(unique_courses) > 3:
                    print(f"  ... and {len(unique_courses) - 3} more courses")
            else:
                print("❌ Failed to save JSON file")
        else:
            print("❌ No accounting courses found")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if doc:
            doc.close()
            print("\nProcessing complete.")