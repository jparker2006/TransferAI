import fitz  # PyMuPDF, replaces pdfplumber
import re
from collections import defaultdict
import json # Added for JSON output

# Path to your PDF file
SMC_CATALOG_PATH = "/home/jparker/TransferAI/data/SMC_catalog/253-SMCschedule.pdf"

# Page range to scan (1-indexed, inclusive)
START_PAGE_NUM_1_INDEXED = 13
END_PAGE_NUM_1_INDEXED = 103  # Restored to full range

def extract_all_department_headers(pdf_path: str, start_page: int, end_page: int) -> dict[str, list[int]]:
    """
    Extracts ALL department headers using ONLY visual characteristics, leveraging PyMuPDF.
    Trust the PDF formatting - if it matches color, font, and size criteria, it's a header.
    """
    print(f"\n{'='*80}")
    print(f"PYMUPDF-BASED HEADER EXTRACTION - TRUST THE PDF FORMATTING")
    # CORRECTED HEADER_COLOR_INT based on debugging output from PyMuPDF
    HEADER_COLOR_INT = 21668  # This was 0x54a4 in hex, identified from 'Astronomy' span
    HEADER_FONT_PATTERN = "Gotham-Bold" # Font name should contain this pattern
    MIN_HEADER_SIZE = 17.0
    MAX_HEADER_SIZE = 19.0
    print(f"Looking for: Color {HEADER_COLOR_INT} (Hex: {hex(HEADER_COLOR_INT)}), Font containing '{HEADER_FONT_PATTERN}', Size {MIN_HEADER_SIZE}-{MAX_HEADER_SIZE}")
    print(f"Pages: {start_page}-{end_page}")
    print(f"{'='*80}")
    
    all_raw_headers = []  # Store all raw headers for smart reconstruction
    
    try:
        doc = fitz.open(pdf_path)
        for page_num_0_indexed in range(start_page - 1, min(end_page, len(doc))):
            current_page_1_indexed = page_num_0_indexed + 1
            page_headers_texts_for_print = [] # For the print statement per page
            
            # Removed DEBUGGING section here

            try:
                page = doc.load_page(page_num_0_indexed)
                # Use get_text("dict") for detailed structure including blocks, lines, and spans
                # Default flags for "dict" are usually good (includes whitespace and ligature preservation)
                page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE)

                for block in page_dict.get("blocks", []):
                    if block.get("type") == 0:  # 0 indicates a text block
                        for line in block.get("lines", []):
                            line_header_text_parts = [] # Collect parts of a header from spans in this line
                            relevant_spans_in_line = [] # Store spans that make up the current line header

                            # Sort spans by their horizontal position (x0) to ensure correct text order
                            sorted_spans = sorted(line.get("spans", []), key=lambda s: s.get("bbox", [0,0,0,0])[0])

                            for span in sorted_spans:
                                span_text = span.get("text", "")
                                span_font = span.get("font", "")
                                span_size = span.get("size", 0)
                                span_color = span.get("color", 0)
                                
                                # Check if the span matches the visual characteristics of a header
                                is_header_span = (
                                    span_color == HEADER_COLOR_INT and
                                    HEADER_FONT_PATTERN in span_font and
                                    MIN_HEADER_SIZE <= span_size <= MAX_HEADER_SIZE
                                )
                                
                                if is_header_span:
                                    line_header_text_parts.append(span_text)
                                    relevant_spans_in_line.append(span)
                            
                            # If header parts were found in this line, reconstruct the full line header text
                            if line_header_text_parts and relevant_spans_in_line:
                                reconstructed_line_text = "".join(line_header_text_parts).strip()
                                if reconstructed_line_text: # Ensure it's not empty after stripping
                                    # Use the line's bounding box for y_position and x_position
                                    line_bbox = line.get("bbox", (0,0,0,0))
                                    all_raw_headers.append({
                                        'text': reconstructed_line_text,
                                        'page': current_page_1_indexed,
                                        'y_position': line_bbox[1],  # top y-coordinate of the line
                                        'x_position': line_bbox[0],   # left x-coordinate of the line
                                        'page_dict': page_dict  # Store page_dict for later description extraction
                                    })
                                    page_headers_texts_for_print.append(reconstructed_line_text)
            except Exception as e_page:
                print(f"Error processing page {current_page_1_indexed}: {e_page}")
                continue # Continue to the next page

            if page_headers_texts_for_print:
                print(f"Page {current_page_1_indexed}: Found {len(page_headers_texts_for_print)} headers: {', '.join([h[:15] + '...' if len(h) > 15 else h for h in page_headers_texts_for_print[:3]])}{'...' if len(page_headers_texts_for_print) > 3 else ''}")
            else:
                print(f"Page {current_page_1_indexed}: No headers found")
        
        doc.close()
                    
    except FileNotFoundError:
        print(f"\nError: The PDF file was not found at '{pdf_path}'. Please check the path.")
        return {}
    except Exception as e:
        print(f"\nError processing PDF with PyMuPDF: {e}")
        return {} # Return empty if there's a global error
    
    # Now apply smart reconstruction to the raw headers collected by PyMuPDF
    print(f"\n{'='*80}")
    print("SMART RECONSTRUCTION OF FRAGMENTED HEADERS (POST-PYMUPDF)")
    print(f"{'='*80}")
    
    reconstructed_headers_list = smart_reconstruct_headers(all_raw_headers) # Renamed to avoid confusion
    
    # Convert to final format: dict of department names to list of page numbers
    final_department_headers = defaultdict(list) # Renamed for clarity
    for header_info in reconstructed_headers_list:
        clean_name = header_info['clean_name']
        # Ensure pages is a list, as smart_reconstruct_headers might return single page or list
        pages_for_header = header_info['pages']
        if not isinstance(pages_for_header, list):
            pages_for_header = [pages_for_header]

        if clean_name: # Ensure there's a name after cleaning
            final_department_headers[clean_name].extend(pages_for_header)
    
    # Remove duplicate page numbers and sort them for each department
    final_headers_output = { # Renamed for clarity
        name: sorted(list(set(pages)))
        for name, pages in final_department_headers.items()
    }
    
    return final_headers_output

def smart_reconstruct_headers(raw_headers):
    """
    Intelligently reconstructs department names from fragmented headers.
    Uses proximity and common patterns to merge related fragments, including multi-line names.
    """
    print(f"Processing {len(raw_headers)} raw headers...")
    
    if not raw_headers:
        return []

    page_headers = defaultdict(list)
    for header in raw_headers:
        page_headers[header['page']].append(header)
    
    reconstructed = []
    
    Y_THRESHOLD_FOR_SEMANTIC_MERGE = 25.0 
    MAX_Y_DISTANCE_FOR_CHAIN_CONTINUATION = Y_THRESHOLD_FOR_SEMANTIC_MERGE + 15 # e.g., 40

    for page_num, headers_on_page in sorted(page_headers.items()):
        print(f"  Processing page {page_num} with {len(headers_on_page)} raw headers...")
        
        sorted_page_headers = sorted(headers_on_page, key=lambda h: (h['y_position'], h['x_position']))
        
        globally_merged_indices_on_page = set()

        for i in range(len(sorted_page_headers)):
            if i in globally_merged_indices_on_page:
                continue
            
            current_header_info = sorted_page_headers[i]
            combined_text_parts = [current_header_info['text']]
            # current_y and current_x are for the starting header of the chain (H_i)
            current_start_y = current_header_info['y_position'] 
            current_start_x = current_header_info['x_position']
            last_merged_header_info = current_header_info # Tracks the last piece added to the chain
            
            indices_in_this_merge_pass = {i}

            for j in range(i + 1, len(sorted_page_headers)):
                if j in globally_merged_indices_on_page: # If H_j was already part of another chain
                    continue

                next_header_info = sorted_page_headers[j]
                
                # Distance from the *last successfully merged part of the current chain*
                y_distance_from_last_in_chain = abs(next_header_info['y_position'] - last_merged_header_info['y_position'])
                
                # If H_j is too far down from the last piece of our chain, this chain cannot extend further.
                if y_distance_from_last_in_chain > MAX_Y_DISTANCE_FOR_CHAIN_CONTINUATION:
                    break 

                # x_distance relative to the last merged header in chain for alignment check
                x_distance_from_last_in_chain = abs(next_header_info['x_position'] - last_merged_header_info['x_position'])
                # x-position of the starting header of the chain (H_i) for indentation relative to start
                # OR x-position of last_merged_header for stricter local alignment.
                # Using last_merged_header_info['x_position'] for local alignment check.
                alignment_check_x = last_merged_header_info['x_position']

                is_direct_continuation = (
                    y_distance_from_last_in_chain <= 22 and 
                    (x_distance_from_last_in_chain < 50 or 
                     (next_header_info['x_position'] > alignment_check_x - 10 and 
                      next_header_info['x_position'] < alignment_check_x + 70))
                )
                
                accumulated_text_for_semantic_check = ' '.join(combined_text_parts)
                can_semantically_merge = should_merge_headers(accumulated_text_for_semantic_check, next_header_info['text'])

                should_perform_merge = False
                if is_direct_continuation:
                    should_perform_merge = True
                elif can_semantically_merge and y_distance_from_last_in_chain < Y_THRESHOLD_FOR_SEMANTIC_MERGE:
                    should_perform_merge = True

                if should_perform_merge:
                    print(f"    Merging (Page {page_num}): '{' '.join(combined_text_parts)}' + '{next_header_info['text']}' (y_dist: {y_distance_from_last_in_chain:.1f}, x_dist: {x_distance_from_last_in_chain:.1f}, direct: {is_direct_continuation}, semantic: {can_semantically_merge}, semantic_dist_ok: {y_distance_from_last_in_chain < Y_THRESHOLD_FOR_SEMANTIC_MERGE if can_semantically_merge else 'N/A'})")
                    combined_text_parts.append(next_header_info['text'])
                    indices_in_this_merge_pass.add(j) 
                    last_merged_header_info = next_header_info # Update for the next iteration of j
                # If not merging, we simply continue the j loop to check the next H_j against the current chain.
                # The old `else: break` was removed here.
            
            if len(combined_text_parts) > 0:
                 globally_merged_indices_on_page.update(indices_in_this_merge_pass)

            final_combined_text = ' '.join(combined_text_parts)
            clean_name = clean_header_text(final_combined_text)
            
            if clean_name and not is_fragment_noise(clean_name):
                reconstructed.append({
                    'clean_name': clean_name,
                    'pages': [page_num], 
                    'original_fragments': len(combined_text_parts),
                    'y_position': current_header_info['y_position'],
                    'page_dict': current_header_info.get('page_dict')  # For description extraction
                })
                if len(combined_text_parts) > 1:
                    print(f"    Created multi-line/merged department (Page {page_num}): '{clean_name}'")
            
    # Consolidate pages for identical clean_names that might have been processed separately
    final_consolidated_headers = defaultdict(lambda: {'pages': set(), 'original_fragments': 0, 'y_position': None, 'page_dict': None})
    for item in reconstructed:
        final_consolidated_headers[item['clean_name']]['pages'].add(item['pages'][0])
        final_consolidated_headers[item['clean_name']]['original_fragments'] = max(
            final_consolidated_headers[item['clean_name']]['original_fragments'], 
            item['original_fragments']
        )
        # Store first occurrence info for description extraction
        if final_consolidated_headers[item['clean_name']]['y_position'] is None:
            final_consolidated_headers[item['clean_name']]['y_position'] = item['y_position']
            final_consolidated_headers[item['clean_name']]['page_dict'] = item['page_dict']

    output_list = []
    for name, data in final_consolidated_headers.items():
        output_list.append({
            'clean_name': name,
            'pages': sorted(list(data['pages'])),
            'original_fragments': data['original_fragments'],
            'y_position': data['y_position'],
            'page_dict': data['page_dict']
        })

    return sorted(output_list, key=lambda x: x['clean_name'])

def extract_enhanced_department_info(headers_with_context):
    """Extract course letters for departments using the reconstructed headers."""
    enhanced_info = {}
    
    # Group headers by page for boundary detection
    page_headers = {}
    for header_info in headers_with_context:
        for page in header_info['pages']:
            if page not in page_headers:
                page_headers[page] = []
            page_headers[page].append({
                'name': header_info['clean_name'],
                'y_position': header_info['y_position'],
                'page_dict': header_info['page_dict']
            })
    
    # Sort headers by Y position on each page
    for page in page_headers:
        page_headers[page].sort(key=lambda x: x['y_position'])
    
    for header_info in headers_with_context:
        dept_name = header_info['clean_name']
        pages = header_info['pages']
        y_position = header_info['y_position']
        page_dict = header_info['page_dict']
        
        # Extract course letters with proper boundaries
        course_letters = ""
        
        if page_dict and y_position:
            # Find the next department boundary for course letter extraction
            current_page = pages[0]  # Use first page where this department appears
            next_dept_y = None
            
            if current_page in page_headers:
                current_dept_headers = page_headers[current_page]
                for i, header in enumerate(current_dept_headers):
                    if header['name'] == dept_name and header['y_position'] == y_position:
                        if i + 1 < len(current_dept_headers):
                            next_dept_y = current_dept_headers[i + 1]['y_position']
                        break
            
            course_letters = extract_course_letters_from_department_area(
                page_dict, 
                {'y_position': y_position, 'clean_name': dept_name}, 
                next_dept_y
            )
        
        enhanced_info[dept_name] = {
            'pages': pages,
            'course_letters': course_letters
        }
    
    return enhanced_info

def extract_course_letters_from_department_area(page_dict, header_info, next_dept_y=None):
    """Extract course letter prefixes from course titles within a specific department's bounded area."""
    header_y = header_info['y_position']
    dept_name = header_info.get('clean_name', '')
    
    # First, try to guess the likely course prefix based on department name
    likely_prefixes = guess_course_prefix_from_department_name(dept_name)
    
    # Define search boundaries - be more conservative
    MIN_COURSE_DISTANCE = 30   # increased minimum distance to avoid header area
    if next_dept_y:
        MAX_COURSE_DISTANCE = min(next_dept_y - header_y - 15, 120)  # More conservative max distance
    else:
        MAX_COURSE_DISTANCE = 120  # reduced fallback distance
    
    # Ensure we have a reasonable search area
    if MAX_COURSE_DISTANCE < MIN_COURSE_DISTANCE:
        return ""
    
    # Course code regex (from course_info_parser.py)
    COURSE_CODE_RE = re.compile(r"^([A-Z]{2,5})\s*\d{1,3}[A-Z]?[.,]\s*(.+)$")
    
    # Look for course codes within the bounded department area
    found_courses = []
    
    for block in page_dict.get("blocks", []):
        if block.get("type") == 0:  # Text block
            for line in block.get("lines", []):
                line_bbox = line.get("bbox", (0,0,0,0))
                line_y = line_bbox[1]
                
                # Only look within this department's bounded area
                if (line_y > header_y + MIN_COURSE_DISTANCE and 
                    line_y < header_y + MAX_COURSE_DISTANCE):
                    
                    line_text_parts = []
                    is_course_line = False
                    
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        span_font = span.get("font", "")
                        span_size = span.get("size", 0)
                        span_color = span.get("color", 0)
                        
                        # Check if this matches course title characteristics
                        is_course_span = (
                            span_font == 'ITCFranklinGothicStd-Dem' and
                            abs(span_size - 7.96) < 0.3 and
                            span_color == 0
                        )
                        
                        if is_course_span:
                            line_text_parts.append(span_text)
                            is_course_line = True
                    
                    if is_course_line:
                        line_text = "".join(line_text_parts).strip()
                        match = COURSE_CODE_RE.match(line_text)
                        if match:
                            prefix = match.group(1).strip()
                            distance_from_header = line_y - header_y
                            
                            # Prioritize courses that match expected prefixes
                            priority = 0
                            if prefix in likely_prefixes:
                                priority = 1000 - distance_from_header  # High priority for matching prefix
                            elif distance_from_header <= 60:
                                priority = 500 - distance_from_header   # Medium priority for close courses
                            
                            if priority > 0:  # Only add courses with some priority
                                found_courses.append({
                                    'prefix': prefix,
                                    'line_text': line_text,
                                    'y_position': line_y,
                                    'distance_from_header': distance_from_header,
                                    'priority': priority
                                })
    
    # If we found courses, take the highest priority one
    if found_courses:
        found_courses.sort(key=lambda x: x['priority'], reverse=True)
        best_course = found_courses[0]
        
        # Only return if it's a good match
        if best_course['priority'] >= 400:  # Reasonable threshold
            return best_course['prefix']
    
    # If no clear course found, return empty string
    return ""

def guess_course_prefix_from_department_name(dept_name):
    """Guess likely course prefixes based on department name."""
    dept_upper = dept_name.upper()
    likely_prefixes = set()
    
    # Common department to course prefix mappings
    mappings = {
        'ACCOUNTING': {'ACCTG'},
        'ADMINISTRATION OF JUSTICE': {'ADMIN', 'AJ'},
        'AMERICAN SIGN LANGUAGE': {'ASL'},
        'ANIMATION': {'ANIM'},
        'ANTHROPOLOGY': {'ANTHRO', 'ANTH'},
        'AQUACULTURE': {'AQUA'},
        'ARABIC': {'ARAB'},
        'ARCHITECTURE': {'ARCH', 'ARC'},
        'ART': {'ART'},
        'ART HISTORY': {'AHIS', 'ART'},
        'ASTRONOMY': {'ASTRO', 'ASTR'},
        'AUTOMOTIVE TECHNOLOGY': {'AUTO'},
        'BIOLOGICAL SCIENCES': {'BIOL'},
        'BUSINESS': {'BUS'},
        'CHEMISTRY': {'CHEM'},
        'CHINESE': {'CHIN'},
        'COMMUNICATION STUDIES': {'COMM'},
        'COMPUTER INFORMATION SYSTEMS': {'CIS'},
        'COMPUTER SCIENCE': {'CS'},
        'COSMETOLOGY': {'COSM'},
        'COUNSELING': {'COUNS'},
        'DANCE': {'DANCE'},
        'EARLY CHILDHOOD EDUCATION': {'ECE'},
        'ECONOMICS': {'ECON'},
        'EDUCATION': {'EDUC'},
        'ENGINEERING': {'ENGR'},
        'ENGLISH': {'ENGL'},
        'ESL': {'ESL'},
        'ENTERTAINMENT TECHNOLOGY': {'ET'},
        'ENVIRONMENTAL STUDIES': {'ENVRN'},
        'ETHNIC STUDIES': {'ETHST'},
        'FASHION DESIGN': {'FASHN'},
        'FILM STUDIES': {'FILM'},
        'FRENCH': {'FREN'},
        'GAME DESIGN': {'GAME'},
        'GEOGRAPHY': {'GEOG'},
        'GEOLOGY': {'GEOL'},
        'GERMAN': {'GERM'},
        'GLOBAL STUDIES': {'GLST'},
        'GRAPHIC DESIGN': {'GRAPH'},
        'HEALTH': {'HEALTH'},
        'HEBREW': {'HEBR'},
        'HISTORY': {'HIST'},
        'HUMANITIES': {'HUM'},
        'INTERACTION DESIGN': {'IXD'},
        'INTERIOR ARCHITECTURAL DESIGN': {'IARC'},
        'ITALIAN': {'ITAL'},
        'JAPANESE': {'JAPAN'},
        'JOURNALISM': {'JOURN'},
        'KINESIOLOGY': {'KIN'},
        'KOREAN': {'KOR'},
        'LIBRARY STUDIES': {'LIBR'},
        'LINGUISTICS': {'LING'},
        'MATHEMATICS': {'MATH'},
        'MEDIA STUDIES': {'MEDIA'},
        'MUSIC': {'MUSIC'},
        'NURSING': {'NURSNG'},
        'OFFICE TECHNOLOGY': {'OFFIC'},
        'PERSIAN': {'PERS'},
        'PHILOSOPHY': {'PHILO'},
        'PHOTOGRAPHY': {'PHOTO'},
        'PHYSICS': {'PHYS'},
        'POLITICAL SCIENCE': {'POLSC'},
        'PSYCHOLOGY': {'PSYCH'},
        'REAL ESTATE': {'RE'},
        'RELIGIOUS STUDIES': {'RELS'},
        'RESPIRATORY CARE': {'RC'},
        'RUSSIAN': {'RUSS'},
        'SCIENCE': {'SCI'},
        'SOCIOLOGY': {'SOC'},
        'SPANISH': {'SPAN'},
        'SUSTAINABLE MATERIALS MANAGEMENT': {'SMM'},
        'SUSTAINABILITY SYSTEMS': {'SST'},
        'THEATRE ARTS': {'THTR'},
        'URBAN STUDIES': {'URBAN'},
        'WOMEN\'S, GENDER, AND SEXUALITY STUDIES': {'WGS'}
    }
    
    # Look for exact matches first
    for dept_key, prefixes in mappings.items():
        if dept_key in dept_upper:
            likely_prefixes.update(prefixes)
    
    # Look for partial matches
    if 'PHYSICAL EDUCATION' in dept_upper:
        likely_prefixes.add('KIN')
    if 'KINESIOLOGY' in dept_upper:
        likely_prefixes.add('KIN')
    if 'ENGLISH' in dept_upper and 'COMPOSITION' in dept_upper:
        likely_prefixes.add('ENGL')
    if 'CREATIVE WRITING' in dept_upper:
        likely_prefixes.add('ENGL')
    
    return likely_prefixes

def find_primary_course_prefix(course_letters_set):
    """Find the most common or primary course prefix from a set."""
    if not course_letters_set:
        return ""
    
    # Convert to list and return the first (alphabetically) if multiple
    prefixes = sorted(list(course_letters_set))
    
    # Simple heuristic: return the shortest prefix (usually the primary department code)
    return min(prefixes, key=len) if prefixes else ""

def should_merge_headers(current_text: str, next_text: str) -> bool:
    """
    Determine if two headers should be SEMANTICALLY merged.
    This is a helper for the main spatial merging logic.
    Inputs are raw text, uppercasing done internally for comparisons.
    """
    current_text_upper = current_text.upper()
    next_text_upper = next_text.upper()

    # 1. Specific, known multi-word department patterns (PREFIX, [POSSIBLE_SECOND_WORDS])
    #    These are generally reliable. Ensure patterns are for the START of the next_text_upper.
    merge_patterns = [
        ('AUTOMOTIVE', ['TECHNOLOGY']),
        ('COMPUTER', ['SCIENCE', 'INFORMATION', 'SYSTEMS']),
        ('POLITICAL', ['SCIENCE']),
        ('ENVIRONMENTAL', ['STUDIES', 'SCIENCE']),
        ('BIOLOGICAL', ['SCIENCES']),
        ('HEALTH', ['SCIENCES', 'EDUCATION', 'OCCUPATIONS', '– NONCREDIT']),
        ('PHYSICAL', ['EDUCATION', 'SCIENCE']),
        ('DIGITAL', ['MEDIA', 'ARTS', 'POST-PRODUCTION']),
        ('GRAPHIC', ['DESIGN', 'ARTS']),
        ('GAME', ['DESIGN', 'DEVELOPMENT']),
        ('FASHION', ['DESIGN', 'MERCHANDISING']),
        ('FASHION DESIGN AND', ['MERCHANDISING']),
        ('INTERIOR', ['DESIGN', 'ARCHITECTURAL', 'ARCHITECTURE']),
        ('INTERIOR ARCHITECTURAL', ['DESIGN']),
        ('INTERACTION', ['DESIGN']),
        ('LIBRARY', ['STUDIES', 'SCIENCE']),
        ('MEDIA', ['STUDIES', 'ARTS']),
        ('FILM', ['STUDIES', 'PRODUCTION']),
        ('ETHNIC', ['STUDIES']),
        ('RELIGIOUS', ['STUDIES']),
        ('URBAN', ['STUDIES', 'PLANNING']),
        ('GLOBAL', ['STUDIES', 'POLICY']),
        ('AMERICAN', ['SIGN', 'STUDIES']),
        ('AMERICAN SIGN', ['LANGUAGE']),
        ('EARLY', ['CHILDHOOD']),
        ('EARLY CHILDHOOD', ['EDUCATION', 'EDUCATION – NONCREDIT']),
        ('REAL', ['ESTATE']),
        ('RESPIRATORY', ['CARE', 'THERAPY']),
        ('OFFICE', ['TECHNOLOGY', 'ADMINISTRATION']),
        ('ENTERTAINMENT', ['TECHNOLOGY', 'ARTS', 'MANAGEMENT']),
        ('ENGLISH', ['COMPOSITION', 'LITERATURE', 'LANGUAGE', 'AS A SECOND LANGUAGE', '– CREATIVE', '– LITERATURE']),
        ('ENGLISH COMPOSITION –', ['GROUP A', 'GROUP B']),
        ('ENGLISH – CREATIVE', ['WRITING']),
        ('BUSINESS', ['ADMINISTRATION', 'MANAGEMENT', 'ECONOMICS', '– NONCREDIT']),
        ('THEATRE', ['ARTS', 'PERFORMANCE', 'PRODUCTION']),
        ('ADMINISTRATION', ['OF']),
        ('ADMINISTRATION OF', ['JUSTICE']),
        ('KINESIOLOGY/PHYSICAL', ['EDUCATION', 'EDUCATION:', 'EDUCATION–', 'EDUCATION: AQUATICS', 'EDUCATION: FITNESS', 'EDUCATION: INDIVIDUAL', 'EDUCATION: TEAM']),
        ('KINESIOLOGY/PHYSICAL EDUCATION:', ['AQUATICS', 'FITNESS', 'INDIVIDUAL', 'TEAM', 'COMBATIVES']),
        ('KINESIOLOGY/PHYSICAL EDUCATION: INDIVIDUAL', ['SPORTS']),
        ('KINESIOLOGY/PHYSICAL EDUCATION: TEAM', ['SPORTS']),
        ('KINESIOLOGY/', ['PHYSICAL EDUCATION:', 'PHYSICAL EDUCATION', 'PHYSICAL EDUCATION –']),
        ('COUNSELING:', ['DISABLED', 'STUDENT', 'DISABLED STUDENT SERVICES', 'DISABLED STUDENT SERVICES – NONCREDIT']),
        ('COUNSELING', [': DISABLED', ': STUDENT SERVICES', 'DISABLED STUDENT SERVICES', 'DISABLED STUDENT SERVICES – NONCREDIT']),
        ('COUNSELING: DISABLED', ['STUDENT SERVICES', 'STUDENT SERVICES – NONCREDIT']),
        ('COUNSELING: DISABLED STUDENT SERVICES', ['– NONCREDIT']),
        ('DISABLED', ['STUDENT SERVICES']),
        ('STUDENT', ['SERVICES']),
        ('MUSIC:', ['APPRECIATION', 'THEORY', 'APPRECIATION AND HISTORY', 'THEORY, PERFORMANCE, AND APPLICATION']),
        ('MUSIC', [': APPRECIATION AND HISTORY', ': THEORY, PERFORMANCE, AND APPLICATION']),
        ('MUSIC: APPRECIATION', ['AND HISTORY']),
        ('MUSIC: THEORY,', ['PERFORMANCE, AND APPLICATION', 'PERFORMANCE, AND']), # Note the comma in prefix
        ('MUSIC: THEORY, PERFORMANCE, AND', ['APPLICATION']),
        ('SCIENCE', ['– GENERAL', '– GENERAL STUDIES']),
        ('SCIENCE – GENERAL', ['STUDIES']),
        ('WOMEN\'S, GENDER, AND', ['SEXUALITY STUDIES']), # Escaped apostrophe
        ('WOMEN\'S', ['GENDER, AND SEXUALITY STUDIES', 'GENDER AND SEXUALITY STUDIES']), # Escaped apostrophe
        ('ESL – ENGLISH AS A', ['SECOND LANGUAGE']),
        ('ENGLISH AS A', ['SECOND LANGUAGE']),
        ('CREATIVE', ['WRITING']),
        ('BICYCLE', ['MAINTENANCE', 'MAINTENANCE – NONCREDIT']),
        ('BICYCLE MAINTENANCE', ['– NONCREDIT']),
        ('DANCE:', ['TECHNIQUE AND PERFORMANCE', 'APPRECIATION', 'APPRECIATION AND HISTORY']),
        ('DANCE', [': TECHNIQUE AND PERFORMANCE', ': APPRECIATION', ': APPRECIATION AND HISTORY']),
        ('DANCE: TECHNIQUE AND', ['PERFORMANCE']),
        ('SUSTAINABILITY SYSTEMS', ['AND TECHNOLOGY – NONCREDIT', 'AND TECHNOLOGY']),
        ('SUSTAINABILITY SYSTEMS AND TECHNOLOGY', ['– NONCREDIT']),
        ('PROFESSIONAL COURSES', ['IN KINESIOLOGY/ PHYSICAL EDUCATION', 'IN KINESIOLOGY/']),
        ('PROFESSIONAL COURSES IN KINESIOLOGY/', ['PHYSICAL EDUCATION'])
    ]

    for prefix, continuations in merge_patterns:
        is_prefix_match = False
        if current_text_upper == prefix:
            is_prefix_match = True
        
        if is_prefix_match:
            for cont_start in continuations:
                if next_text_upper.startswith(cont_start):
                    if len(cont_start) <= 2 and not prefix.endswith(("--", ":")): # Check for tuple of suffixes
                         if prefix.endswith("GROUP") or prefix.endswith("LEVEL"):
                            return True
                    else:
                        return True
    
    if current_text_upper.endswith(" –") and next_text_upper == "NONCREDIT":
            return True
    
    is_single_word_current = " " not in current_text_upper
    is_known_prefix_exact = any(pattern_tuple[0] == current_text_upper for pattern_tuple in merge_patterns)
    
    if is_single_word_current and not is_known_prefix_exact:
        return False
        
    return False

def combine_multi_line_headers(headers):
    """
    Combine multiple headers that span multiple lines into a single department name.
    """
    combined_text = ""
    
    for header in headers:
        text = header['text'].strip()
        if text:
            if combined_text and not combined_text.endswith(' '):
                combined_text += " "
            combined_text += text
    
    return combined_text

def is_obvious_noise(text):
    """Check if text fragment is obvious noise that should be ignored."""
    text = text.strip().upper()
    
    # Skip very short fragments that are likely noise
    if len(text) < 2:
        return True
    
    # Skip common noise patterns
    noise_patterns = [
        'NONCREDIT', 'CH', 'UNIT', 'UNITS', 'GROUP', 'SECTION',
        'PAGE', 'CONTINUED', 'SEE', 'ALSO', 'NOTE', 'NOTES'
    ]
    
    return text in noise_patterns

def is_fragment_noise(clean_name):
    """Check if a cleaned name is likely just noise/fragment."""
    if not clean_name or len(clean_name.strip()) < 3:
        return True
    
    name_upper = clean_name.upper().strip()
    
    # Skip obvious non-department fragments
    noise_indicators = [
        'GROUP A', 'GROUP B', 'SECTION', 'CONTINUED', 'NONCREDIT CLASSES',
        'AND HISTORY', 'AND TECHNOLOGY', 'PERFORMANCE,AND', 'POST-PRODUCTION'
    ]
    
    return name_upper in noise_indicators

def clean_header_text(raw_text: str) -> str:
    """
    MINIMAL cleaning - only remove obvious noise, preserve everything else.
    Trust that if it was formatted as a header, it probably IS a header.
    """
    if not raw_text or len(raw_text.strip()) < 2:
        return ""
    
    text = raw_text.strip()
    
    # Remove only obvious noise patterns
    # Remove trailing punctuation and symbols (but be careful with hyphens in names or "– Noncredit")
    # Keep '–' if followed by Noncredit, otherwise can remove trailing ones.
    if not "– NONCREDIT" in text.upper(): # Check before stripping trailing punctuation
        text = re.sub(r'[.,:;!?–-]+$', '', text)
    else: # If "– Noncredit" is present, only strip other trailing punctuation cautiously
        text = re.sub(r'[.,:;!?]+$', '', text) # Avoid stripping the hyphen in "– Noncredit"
    
    # Remove obvious course codes at the end (e.g., "ART 10A")
    text = re.sub(r'\s+[A-Z]{2,5}\s*\d{1,4}[A-Z]?$', '', text)
    
    # DO NOT Remove "Noncredit" suffix if present. This was the bug.
    # text = re.sub(r'\s*[-–]?\s*Noncredit$', '', text, flags=re.IGNORECASE)
    
    # Clean up spacing
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Skip if it's just noise after initial cleaning
    if len(text) < 2 or text.isdigit() or text.upper() == "NONCREDIT": # Avoid standalone "Noncredit"
        # Check for "X – Noncredit" or "X-Noncredit" which is valid
        if not ("– NONCREDIT" in text.upper() or "-NONCREDIT" in text.upper()):
            return ""
    
    # Apply smart capitalization
    return format_department_name_simple(text)

def format_department_name_simple(text: str) -> str:
    """
    Simple formatting - proper capitalization, handling common acronyms and conjunctions.
    Special care for '– Noncredit'.
    """
    if not text:
        return ""
    
    text = text.strip()

    # Preserve "– Noncredit" capitalization by temporarily replacing it
    noncredit_marker = "___NONCREDIT_MARKER___"
    # Handle variations of Noncredit spacing
    text = re.sub(r'[-–]\s*Noncredit', noncredit_marker, text, flags=re.IGNORECASE)
    
    # General title casing for all words first
    words = text.split(' ')
    cased_words = []
    for word_idx, word in enumerate(words):
        if word == noncredit_marker: # Skip marker from title casing for now
            cased_words.append(word)
            continue
        
        # Handle words with hyphens or slashes internally before general title case for the word
        if '-' in word and word != noncredit_marker:
            parts = word.split('-')
            # Capitalize each part of hyphenated word unless it's a small word (and not first part of hyphen)
            cased_hyphen_parts = []
            for i, p in enumerate(parts):
                if i > 0 and p.lower() in ['a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'in', 'nor', 'of', 'on', 'or', 'the', 'to', 'up', 'with', 'via']:
                    cased_hyphen_parts.append(p.lower())
                else:
                    cased_hyphen_parts.append(p.capitalize())
            cased_words.append('-'.join(cased_hyphen_parts))
        elif '/' in word and word != noncredit_marker:
            parts = word.split('/')
            cased_slash_parts = [p.capitalize() for p in parts] # Simple capitalize for slash parts
            cased_words.append('/'.join(cased_slash_parts))
        else:
            cased_words.append(word.capitalize()) # Standard capitalize for standalone words
    
    text = ' '.join(cased_words)

    # Acronyms and specific capitalizations (applied after initial casing)
    # Using regex with word boundaries for robustness.
    acronym_replacements = {
        r'\bUcla\b': 'UCLA', r'\bUsc\b': 'USC', r'\bCsu\b': 'CSU', r'\bUc\b': 'UC',
        r'\bEsl\b': 'ESL', r'\bGis\b': 'GIS',
        # r'\bIt\b': 'IT', # Avoid "ITalian" -> "ITalian", "It" is too common.
                         # If "IT" is a department, it's usually "Information Technology".
    }
    for pattern, replacement in acronym_replacements.items():
        # Need to be careful with regex flags if text might have mixed case from above
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Lowercase articles, prepositions, and conjunctions (unless they are the first word or follow a colon)
    words = text.split(' ')
    final_words = []
    if not words:
        return ""
    
    final_words.append(words[0]) # First word remains as is
    
    small_words_to_lowercase = ['A', 'An', 'And', 'As', 'At', 'But', 'By', 'For', 'In', 'Nor', 'Of', 'On', 'Or', 'The', 'To', 'Up', 'With', 'Via']
    # Convert to lowercase for matching, as words in list are capitalized from previous step
    for i in range(1, len(words)):
        current_word = words[i]
        # If previous word ends with a colon, or current word is the marker, keep its current case.
        if final_words[-1].endswith(':') or current_word == noncredit_marker:
             final_words.append(current_word)
        elif current_word.capitalize() in small_words_to_lowercase: # Match against capitalized small words
            final_words.append(current_word.lower())
        else:
            final_words.append(current_word) # Already correctly cased or an acronym

    text = ' '.join(final_words)
    
    # Restore "– Noncredit" with correct capitalization
    text = text.replace(noncredit_marker, "– Noncredit")
    
    # Final check for "ITalian" just in case, convert "It" to "It" if it became "IT"
    text = text.replace("ITalian", "Italian")
    text = text.replace("Group a", "Group A")
    text = text.replace("It S", "It's") # Common OCR or split error

    return text.strip()

if __name__ == "__main__":
    print("🎯 DEPARTMENT COURSE LETTER EXTRACTION")
    print("Strategy: FOCUS ON ACCURATE COURSE LETTER DETECTION")
    print("- Extract department headers correctly")
    print("- Smart course letter detection with priority-based matching")
    print(f"{'='*80}")
    
    # Step 1: Extract headers using original working logic
    headers = extract_all_department_headers(SMC_CATALOG_PATH, START_PAGE_NUM_1_INDEXED, END_PAGE_NUM_1_INDEXED)
    
    # Step 2: Get enhanced context for descriptions and course letters
    print(f"\n{'='*80}")
    print("COURSE LETTER EXTRACTION PHASE")
    print(f"{'='*80}")
    
    # Re-run the extraction to get context for enhancements
    try:
        doc = fitz.open(SMC_CATALOG_PATH)
        all_raw_headers = []
        
        for page_num_0_indexed in range(START_PAGE_NUM_1_INDEXED - 1, min(END_PAGE_NUM_1_INDEXED, len(doc))):
            current_page_1_indexed = page_num_0_indexed + 1
            try:
                page = doc.load_page(page_num_0_indexed)
                page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE)

                for block in page_dict.get("blocks", []):
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            line_header_text_parts = []
                            sorted_spans = sorted(line.get("spans", []), key=lambda s: s.get("bbox", [0,0,0,0])[0])

                            for span in sorted_spans:
                                span_text = span.get("text", "")
                                span_font = span.get("font", "")
                                span_size = span.get("size", 0)
                                span_color = span.get("color", 0)
                                
                                is_header_span = (
                                    span_color == 21668 and
                                    "Gotham-Bold" in span_font and
                                    17.0 <= span_size <= 19.0
                                )
                                
                                if is_header_span:
                                    line_header_text_parts.append(span_text)
                            
                            if line_header_text_parts:
                                reconstructed_line_text = "".join(line_header_text_parts).strip()
                                if reconstructed_line_text:
                                    line_bbox = line.get("bbox", (0,0,0,0))
                                    all_raw_headers.append({
                                        'text': reconstructed_line_text,
                                        'page': current_page_1_indexed,
                                        'y_position': line_bbox[1],
                                        'x_position': line_bbox[0],
                                        'page_dict': page_dict
                                    })
            except Exception as e_page:
                continue
        
        doc.close()
        
        # Reconstruct headers with context
        reconstructed_headers_with_context = smart_reconstruct_headers(all_raw_headers)
        
        # Extract enhanced information with proper boundaries
        enhanced_dept_info = extract_enhanced_department_info(reconstructed_headers_with_context)
        
    except Exception as e:
        print(f"Error during enhancement phase: {e}")
        enhanced_dept_info = {}
    
    print(f"\n{'='*80}")
    # ---- ENHANCED JSON OUTPUT ----
    json_output_list = []
    if headers:
        sorted_dept_names = sorted(headers.keys())
        for dept_name in sorted_dept_names:
            pages = headers[dept_name]
            for page_num in pages:
                # Get enhanced info if available
                enhanced_info = enhanced_dept_info.get(dept_name, {'course_letters': ''})
                
                json_output_list.append({
                    "major": dept_name,
                    "pageNumber": page_num,
                    "course_letters": enhanced_info['course_letters']
                })
        
        output_file_path = "smc_department_headers_enhanced.json"
        try:
            with open(output_file_path, 'w') as f:
                json.dump(json_output_list, f, indent=4, ensure_ascii=False)
            print(f"📚 Department course letters saved to: {output_file_path}")
            print(f"Total entries in JSON: {len(json_output_list)}")
            print(f"Total unique departments found: {len(headers)}")
            
            # Preview first few entries
            print(f"\nPreview (first 5 departments):")
            for i, dept_name in enumerate(sorted_dept_names[:5]):
                enhanced_info = enhanced_dept_info.get(dept_name, {'course_letters': ''})
                print(f"  {i+1}. {dept_name}")
                print(f"     Course Letters: {enhanced_info['course_letters'] or '(none found)'}")
                print(f"     Pages: {headers[dept_name]}")

        except IOError as e:
            print(f"Error writing JSON to file: {e}")

    else:
        print("No department information found to save to JSON.")

    print(f"\n{'='*80}")
    print("✅ COURSE LETTER EXTRACTION COMPLETE!")
    print(f"{'='*80}")
