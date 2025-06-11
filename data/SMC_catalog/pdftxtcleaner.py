import re

def identify_page_numbers(text):
    """
    Identify potential page numbers by finding isolated numbers on their own lines
    """
    lines = text.split('\n')
    potential_page_numbers = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Check if line contains only a number (1-3 digits)
        if re.match(r'^\d{1,3}$', stripped):
            potential_page_numbers.append({
                'line_number': i,
                'page_number': int(stripped),
                'original_line': line
            })
    
    return potential_page_numbers

def validate_page_numbers(potential_pages, expected_start=13, expected_end=103):
    """
    Validate that the numbers are actually sequential page numbers
    """
    if not potential_pages:
        return [], []
    
    # Sort by page number
    sorted_pages = sorted(potential_pages, key=lambda x: x['page_number'])
    
    # Check for reasonable sequential pattern
    validated_pages = []
    rejected_pages = []
    
    for page in sorted_pages:
        num = page['page_number']
        # Page numbers should be in expected range and reasonably sequential
        if expected_start <= num <= expected_end:
            validated_pages.append(page)
        else:
            rejected_pages.append(page)
    
    # Check for major gaps that might indicate non-page numbers
    if len(validated_pages) > 1:
        for i in range(1, len(validated_pages)):
            gap = validated_pages[i]['page_number'] - validated_pages[i-1]['page_number']
            if gap > 10:  # Large gap might indicate these aren't page numbers
                print(f"Warning: Large gap ({gap}) between page {validated_pages[i-1]['page_number']} and {validated_pages[i]['page_number']}")
    
    return validated_pages, rejected_pages

def clean_course_catalog(text):
    """
    Clean up course catalog text by removing PDF copy-paste artifacts
    """
    lines = text.split('\n')
    
    # First, identify and validate page numbers
    potential_pages = identify_page_numbers(text)
    validated_pages, rejected_pages = validate_page_numbers(potential_pages)
    
    # Report what we found
    print(f"Found {len(potential_pages)} potential page numbers")
    print(f"Validated {len(validated_pages)} as actual page numbers")
    print(f"Rejected {len(rejected_pages)} as non-page numbers")
    
    if validated_pages:
        page_nums = [p['page_number'] for p in validated_pages]
        print(f"Page numbers to remove: {sorted(page_nums)}")
        print(f"Range: {min(page_nums)} to {max(page_nums)}")
    
    if rejected_pages:
        rejected_nums = [p['page_number'] for p in rejected_pages]
        print(f"Numbers NOT removed (likely course/section numbers): {rejected_nums}")
    
    # Get line numbers to skip (validated page numbers only)
    lines_to_skip = set(p['line_number'] for p in validated_pages)
    
    cleaned_lines = []
    footer_pattern = r'Go to bookstore\.smc\.edu.*?Fall 2025'
    vertical_text_patterns = [
        r'S C H E D U L E O F C L A S S E S',
        r'Fall 2025',
        r'^\s*[A-Z\s]{10,}\s*$'  # Long sequences of caps (likely vertical text)
    ]
    
    # Words/phrases that commonly get split across pages
    split_word_fixes = {
        'measure-\nment': 'measurement',
        'invest-\nment': 'investment',
        'develop-\nment': 'development',
        'manage-\nment': 'management',
        'require-\nment': 'requirement',
        'depart-\nment': 'department',
        'educa-\ntional': 'educational',
        'informa-\ntion': 'information',
        'administra-\ntion': 'administration'
    }
    
    skip_next = False
    
    for i, line in enumerate(lines):
        # Skip if marked from previous iteration
        if skip_next:
            skip_next = False
            continue
            
        # Remove only validated page numbers
        if i in lines_to_skip:
            continue
            
        # Remove footer text
        if re.search(footer_pattern, line, re.IGNORECASE):
            continue
            
        # Remove vertical text patterns
        should_skip = False
        for pattern in vertical_text_patterns:
            if re.search(pattern, line):
                should_skip = True
                break
        if should_skip:
            continue
            
        # Remove very short lines that are likely artifacts (but keep section numbers)
        if len(line.strip()) <= 2 and not line.strip().isdigit():
            continue
            
        # Clean up extra whitespace
        line = re.sub(r'\s+', ' ', line).strip()
        
        # Skip empty lines
        if not line:
            continue
            
        cleaned_lines.append(line)
    
    # Join lines back together
    cleaned_text = '\n'.join(cleaned_lines)
    
    # Fix split words across pages
    for split_word, fixed_word in split_word_fixes.items():
        cleaned_text = cleaned_text.replace(split_word, fixed_word)
    
    # Remove common PDF artifacts
    artifacts_to_remove = [
        r'Go to smc\.edu/searchclasses.*?semesters\.',
        r'SMC is offering on-ground, online, hybrid, and HyFlex classes for\s+(?:fall|summer) 2025\..*?dsps@smc\.edu\.'
    ]
    
    for pattern in artifacts_to_remove:
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.DOTALL | re.IGNORECASE)
    
    # Clean up multiple consecutive newlines
    cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)
    
    # Fix broken sentences that span across page breaks
    # Look for lowercase words at start of lines that should continue previous sentences
    lines = cleaned_text.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        if (i > 0 and 
            line and 
            line[0].islower() and 
            fixed_lines and 
            not fixed_lines[-1].endswith('.') and
            not fixed_lines[-1].endswith(':') and
            len(line.split()) < 8):  # Short continuation lines
            # Merge with previous line
            fixed_lines[-1] += ' ' + line
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)

# Example usage
def process_catalog_file(input_file, output_file):
    """
    Process a course catalog file and save the cleaned version
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        cleaned_content = clean_course_catalog(content)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"Cleaned catalog saved to {output_file}")
        
        # Print some stats
        original_lines = len(content.split('\n'))
        cleaned_lines = len(cleaned_content.split('\n'))
        print(f"Original lines: {original_lines}")
        print(f"Cleaned lines: {cleaned_lines}")
        print(f"Removed: {original_lines - cleaned_lines} lines")
        
    except FileNotFoundError:
        print(f"Error: Could not find file {input_file}")
    except Exception as e:
        print(f"Error processing file: {e}")

# If you want to test with your text directly:
def test_cleaning(sample_text):
    """
    Test the cleaning function with a sample
    """
    cleaned = clean_course_catalog(sample_text)
    print("ORIGINAL:")
    print(sample_text)
    print("\nCLEANED:")
    print(cleaned)
    return cleaned

def analyze_numbers_only(text):
    """
    Analyze all numbers in the text to help verify page number identification
    """
    potential_pages = identify_page_numbers(text)
    validated_pages, rejected_pages = validate_page_numbers(potential_pages)
    
    print("=== NUMBER ANALYSIS ===")
    print(f"Total isolated numbers found: {len(potential_pages)}")
    
    if potential_pages:
        all_nums = [p['page_number'] for p in potential_pages]
        print(f"All isolated numbers: {sorted(all_nums)}")
    
    if validated_pages:
        page_nums = sorted([p['page_number'] for p in validated_pages])
        print(f"\nNUMBERS TO REMOVE (validated page numbers):")
        print(f"Count: {len(page_nums)}")
        print(f"Range: {page_nums[0]} to {page_nums[-1]}")
        print(f"Numbers: {page_nums}")
        
        # Check for expected sequence
        expected = list(range(page_nums[0], page_nums[-1] + 1))
        missing = set(expected) - set(page_nums)
        if missing:
            print(f"Missing from sequence: {sorted(missing)}")
    
    if rejected_pages:
        rejected_nums = sorted([p['page_number'] for p in rejected_pages])
        print(f"\nNUMBERS PRESERVED (likely course/section numbers):")
        print(f"Count: {len(rejected_nums)}")
        print(f"Numbers: {rejected_nums}")
        
        # Show context for rejected numbers
        print("\nContext for preserved numbers:")
        lines = text.split('\n')
        for page in rejected_pages:
            line_num = page['line_number']
            start = max(0, line_num - 1)
            end = min(len(lines), line_num + 2)
            context = lines[start:end]
            print(f"  Number {page['page_number']} context:")
            for i, ctx_line in enumerate(context):
                marker = " -> " if start + i == line_num else "    "
                print(f"    {marker}{ctx_line}")
    
    return validated_pages, rejected_pages

# To use this script:
# 1. Save your pasted text to a file (e.g., 'catalog_raw.txt')
# 2. First analyze numbers: analyze_numbers_only(text) 
# 3. Then clean: process_catalog_file('catalog_raw.txt', 'catalog_cleaned.txt')

# Example workflow:
# with open('catalog_raw.txt', 'r') as f:
#     text = f.read()
# analyze_numbers_only(text)  # Review what will be removed
# process_catalog_file('catalog_raw.txt', 'catalog_cleaned.txt')  # Clean it