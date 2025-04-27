#!/usr/bin/env python3
"""
Test script to verify course description enrichment in prompts.
"""

import os
import sys
import re

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix prompt_builder import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm"))

# Import the necessary components
from llm.document_loader import get_course_title
from llm.prompt_builder import _extract_course_codes, _enrich_with_descriptions

# Sample rendered logic that includes CIS 21JB
sample_logic = """
* Option A: CIS 21JA AND CIS 21JB AND CIS 26B
* Option B: CIS 21JA AND CIS 21JB AND CIS 26BH (Honors)
"""

# Print original titles from document_loader
print("=== Course Titles from document_loader ===")
print(f"CIS 21JA: {get_course_title('CIS 21JA')}")
print(f"CIS 21JB: {get_course_title('CIS 21JB')}")
print(f"CIS 26B: {get_course_title('CIS 26B')}")
print(f"CIS 26BH: {get_course_title('CIS 26BH')}")
print()

# Extract course codes to see what's being detected
print("=== Extracted Course Codes ===")
course_codes = _extract_course_codes(sample_logic)
print(course_codes)
print()

# Manual implementation of enrichment logic to debug
print("=== Manual Enrichment ===")
for code in course_codes:
    title = get_course_title(code)
    if title:
        print(f"{code}: {title}")

print()
print("=== Original Logic ===")
print(sample_logic.strip())
print()
print("=== Enriched Logic ===")
enriched_logic = _enrich_with_descriptions(sample_logic)
print(enriched_logic.strip())

# Add targeted debug for Option B
print("\n=== Debug Option B specifically ===")
option_b_line = "* Option B: CIS 21JA AND CIS 21JB AND CIS 26BH (Honors)"

print("Testing CIS 21JA placement:")
cis_21ja_title = get_course_title('CIS 21JA')
pattern = r'(^|\s|:)(CIS 21JA)(?!\s*\([^)]*\))'
replacement = r'\1\2 (' + cis_21ja_title + ')'
new_line = re.sub(pattern, replacement, option_b_line)
print(f"Result: {new_line}")

print("\nTesting CIS 21JB placement:")
cis_21jb_title = get_course_title('CIS 21JB')
pattern = r'(^|\s|:)(CIS 21JB)(?!\s*\([^)]*\))'
replacement = r'\1\2 (' + cis_21jb_title + ')'
new_line = re.sub(pattern, replacement, option_b_line)
print(f"Result: {new_line}")

# Test explicit option B enrichment
print("\n=== Manual Enrichment of Option B ===")
option_b = "* Option B: CIS 21JA AND CIS 21JB AND CIS 26BH (Honors)"
option_b = option_b.replace(
    "CIS 21JA", 
    f"CIS 21JA ({get_course_title('CIS 21JA')})"
)
option_b = option_b.replace(
    "CIS 21JB", 
    f"CIS 21JB ({get_course_title('CIS 21JB')})"
)
print(option_b) 