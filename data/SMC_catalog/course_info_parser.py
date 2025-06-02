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
SMC_CATALOG_PATH = "data/SMC_catalog/253-SMCschedule.pdf"
# Accounting department is on pages 13 and 14
ACCOUNTING_PAGES_0_INDEXED = [12, 13]  # Pages 13 and 14

# Visual characteristics for course titles - Updated based on PRINT_SPAN_INFO output
COURSE_TITLE_FONT_PATTERN = 'ITCFranklinGothicStd-Dem' 
MIN_COURSE_TITLE_SIZE = 7.8 # Target size is ~7.96
MAX_COURSE_TITLE_SIZE = 8.2
COURSE_TITLE_COLOR = 0  # Black

# Regex to identify lines that start with a course code like "ACCTG 1,"
# This is general, but for accounting, we expect ACCTG.
COURSE_CODE_PREFIX_RE = re.compile(r"^([A-Z]{2,5}\s*\d{1,3}[A-Z]?)[.,]\s*(.+)$") # Capture code and title separately
UNITS_LINE_RE = re.compile(r"^(\d{1,2}(?:\.\d)?)\s+UNITS?$", re.IGNORECASE) # Capture the number of units

# --- Temporary Debug Flag ---
PRINT_SPAN_INFO = True # Set to True for debugging
DEBUG_VERBOSE = True # Additional debugging

def parse_course_info(title_text, units_text=None):
    """Parse a course title and units into structured data."""
    match = COURSE_CODE_PREFIX_RE.match(title_text.strip())
    if not match:
        return None
    
    course_letters = match.group(1).strip()
    course_title = match.group(2).strip()
    
    # Extract units from units_text if provided
    units = None
    if units_text:
        units_match = UNITS_LINE_RE.match(units_text.strip())
        if units_match:
            units = float(units_match.group(1))
    
    return {
        "course_letters": course_letters,
        "course_title": course_title,
        "units": units
    }

def extract_accounting_courses_from_page(doc: fitz.Document, page_num_0_indexed: int) -> list[dict]:
    """Extract accounting course information from a specific page."""
    extracted_courses = []
    
    try:
        page = doc.load_page(page_num_0_indexed)
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE)

        for block in page_dict.get("blocks", []):
            if block.get("type") == 0:  # Text block
                current_accumulated_title_parts = []
                current_units_text = None
                start_of_title_bbox = None
                block_lines = block.get("lines", [])

                for line in block_lines:
                    line_spans = line.get("spans", [])
                    if not line_spans:
                        # Empty line - process any accumulated title
                        if current_accumulated_title_parts:
                            title_text = " ".join(current_accumulated_title_parts).replace("  ", " ").strip()
                            if title_text.upper().startswith("ACCTG"):
                                course_info = parse_course_info(title_text, current_units_text)
                                if course_info:
                                    extracted_courses.append(course_info)
                            current_accumulated_title_parts = []
                            current_units_text = None
                            start_of_title_bbox = None
                        continue

                    # Collect styled text from this line
                    styled_text_from_line_parts = []
                    line_has_any_target_style = False

                    for span in line_spans:
                        span_font = span.get("font", "")
                        span_size = span.get("size", 0)
                        span_color = span.get("color", 0)
                        span_text = span.get("text", "")
                        
                        # Check if span matches our target style
                        font_matches = span_font == COURSE_TITLE_FONT_PATTERN
                        size_matches = abs(span_size - 7.96) < 0.3
                        color_matches = span_color == COURSE_TITLE_COLOR
                        
                        is_target_style_span = font_matches and size_matches and color_matches
                        
                        if is_target_style_span:
                            styled_text_from_line_parts.append(span_text)
                            line_has_any_target_style = True
                    
                    full_styled_text_this_line = "".join(styled_text_from_line_parts).strip()
                    is_units_line = bool(UNITS_LINE_RE.match(full_styled_text_this_line))

                    if line_has_any_target_style:
                        if is_units_line:
                            # This is a units line - store it for the current course
                            current_units_text = full_styled_text_this_line
                        else:
                            # This is course title text - accumulate it
                            if not current_accumulated_title_parts:
                                start_of_title_bbox = line_spans[0].get("bbox") if line_spans else None
                            current_accumulated_title_parts.append(full_styled_text_this_line)
                    else:
                        # Line breaks the sequence - process any accumulated title
                        if current_accumulated_title_parts:
                            title_text = " ".join(current_accumulated_title_parts).replace("  ", " ").strip()
                            if title_text.upper().startswith("ACCTG"):
                                course_info = parse_course_info(title_text, current_units_text)
                                if course_info:
                                    extracted_courses.append(course_info)
                            current_accumulated_title_parts = []
                            current_units_text = None
                            start_of_title_bbox = None
                
                # Process any pending title at the end of the block
                if current_accumulated_title_parts:
                    title_text = " ".join(current_accumulated_title_parts).replace("  ", " ").strip()
                    if title_text.upper().startswith("ACCTG"):
                        course_info = parse_course_info(title_text, current_units_text)
                        if course_info:
                            extracted_courses.append(course_info)

        return extracted_courses

    except Exception as e:
        print(f"Error processing page {page_num_0_indexed + 1}: {e}")
        return []

def save_courses_to_json(courses, filename=None):
    """Save courses data to a JSON file."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"smc_accounting_courses_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(courses, f, indent=2, ensure_ascii=False)
        return filename
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        return None

if __name__ == "__main__":
    print("SMC Accounting Course Parser")
    print("=" * 40)
    
    # Check for PDF file
    if not os.path.exists(SMC_CATALOG_PATH):
        user_workspace_root = "/home/jparker/TransferAI"
        abs_path_SMC_CATALOG_PATH = os.path.join(user_workspace_root, SMC_CATALOG_PATH)
        if os.path.exists(abs_path_SMC_CATALOG_PATH):
            SMC_CATALOG_PATH = abs_path_SMC_CATALOG_PATH
            print(f"Found PDF: {SMC_CATALOG_PATH}")
        else:
            print(f"Error: PDF file not found.")
            exit(1)
    else:
        print(f"Found PDF: {SMC_CATALOG_PATH}")

    doc = None
    all_accounting_courses = []
    
    try:
        doc = fitz.open(SMC_CATALOG_PATH)
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
            # Save to JSON (preserve PDF order, no sorting)
            filename = save_courses_to_json(unique_courses)
            if filename:
                print(f"\n✅ Successfully extracted {len(unique_courses)} accounting courses")
                print(f"📁 Saved to: {filename}")
                
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
