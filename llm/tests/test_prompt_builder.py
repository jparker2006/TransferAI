#!/usr/bin/env python3
"""
Test script for TransferAI prompt_builder.py functionality.
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
from llm.prompt_builder import (
    _extract_course_codes, 
    _enrich_with_descriptions, 
    build_course_prompt,
    build_group_prompt,
    VerbosityLevel
)

def test_extract_course_codes():
    """Test the course code extraction functionality."""
    print("\n=== Testing Course Code Extraction ===")
    
    test_cases = [
        {
            "name": "Basic Options",
            "input": "* Option A: CIS 21JA AND CIS 21JB AND CIS 26B\n* Option B: CIS 21JA AND CIS 21JB AND CIS 26BH (Honors)",
            "expected": ["CIS 21JA", "CIS 21JB", "CIS 26B", "CIS 26BH"]
        },
        {
            "name": "Multiple Formats",
            "input": "MATH 1A, MATH 1B, PHYS 4A and BIO 6A, BIO 6B, BIO 6C",
            "expected": ["MATH 1A", "MATH 1B", "PHYS 4A", "BIO 6A", "BIO 6B", "BIO 6C"]
        },
        {
            "name": "With Descriptions",
            "input": "CIS 21JA (Introduction to Assembly) AND CIS 21JB (Advanced Assembly)",
            "expected": ["CIS 21JA", "CIS 21JB"]
        },
        {
            "name": "Complex Format",
            "input": "Complete one of:\n- CIS 22A OR CIS 22AH\n- MATH 1C AND (MATH 1D OR MATH 2A)",
            "expected": ["CIS 22A", "CIS 22AH", "MATH 1C", "MATH 1D", "MATH 2A"]
        }
    ]
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Input: {test['input']}")
        
        result = _extract_course_codes(test['input'])
        result.sort()  # Sort for consistent comparison
        expected = sorted(test['expected'])
        
        print(f"Extracted: {result}")
        print(f"Expected:  {expected}")
        
        if set(result) == set(expected):
            print("✅ PASS")
        else:
            missing = [x for x in expected if x not in result]
            extra = [x for x in result if x not in expected]
            if missing:
                print(f"❌ FAIL - Missing codes: {missing}")
            if extra:
                print(f"❌ FAIL - Extra codes: {extra}")

def test_enrich_with_descriptions():
    """Test the enrichment with descriptions functionality."""
    print("\n=== Testing Course Description Enrichment ===")
    
    test_cases = [
        {
            "name": "Basic Enrichment",
            "input": "* Option A: CIS 21JA AND CIS 21JB AND CIS 26B",
            "expected_contains": [
                "CIS 21JA (Introduction to x86 Processor Assembly Language and Computer Architecture)",
                "CIS 21JB (Advanced x86 Processor Assembly Programming)",
                "CIS 26B (Advanced C Programming)"
            ]
        },
        {
            "name": "Skip Already Enriched",
            "input": "* Option A: CIS 21JA (Introduction to x86 Processor Assembly Language and Computer Architecture) AND CIS 21JB AND CIS 26B",
            "expected_contains": [
                "CIS 21JA (Introduction to x86 Processor Assembly Language and Computer Architecture)",
                "CIS 21JB (Advanced x86 Processor Assembly Programming)",
                "CIS 26B (Advanced C Programming)"
            ]
        },
        {
            "name": "With Honors Courses",
            "input": "* Option B: CIS 21JA AND CIS 21JB AND CIS 26BH (Honors)",
            "expected_contains": [
                "CIS 21JA (Introduction to x86 Processor Assembly Language and Computer Architecture)",
                "CIS 21JB (Advanced x86 Processor Assembly Programming)"
                # Note: CIS 26BH already has (Honors) so we won't add its description
            ]
        }
    ]
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"Input: {test['input']}")
        
        result = _enrich_with_descriptions(test['input'])
        print(f"Enriched: {result}")
        
        all_contained = True
        for expected_text in test['expected_contains']:
            if expected_text not in result:
                print(f"❌ FAIL - Missing: {expected_text}")
                all_contained = False
        
        if all_contained:
            print("✅ PASS")

def test_verbosity_levels():
    """Test the verbosity levels in prompt generation."""
    print("\n=== Testing Verbosity Levels ===")
    
    # Test data for course prompt
    course_data = {
        "rendered_logic": "* Option A: CIS 21JA AND CIS 21JB AND CIS 26B",
        "user_question": "How can I satisfy CSE 30?",
        "uc_course": "CSE 30",
        "uc_course_title": "Computer Organization and Systems Programming"
    }
    
    # Test data for group prompt
    group_data = {
        "rendered_logic": "* CSE 8A: CIS 22A\n* CSE 8B: CIS 36B",
        "user_question": "What courses do I need for Group 2?",
        "group_id": "2",
        "group_title": "Lower Division CSE",
        "group_logic_type": "all_required"
    }
    
    # Test course prompt with different verbosity levels
    print("\n--- Course Prompt Verbosity Tests ---")
    for level in VerbosityLevel:
        print(f"\nTesting {level.name} verbosity:")
        prompt = build_course_prompt(
            **course_data,
            verbosity=level
        )
        
        # Print excerpt to verify verbosity difference
        prompt_lines = prompt.split("\n")
        excerpt = "\n".join(prompt_lines[:5]) + "\n..."
        print(f"Prompt excerpt:\n{excerpt}")
        
        # Check verbosity-specific characteristics
        if level == VerbosityLevel.MINIMAL:
            assert "extremely concise" in prompt.lower(), "MINIMAL should emphasize extreme conciseness"
            print("✅ PASS - Contains 'extremely concise'")
        elif level == VerbosityLevel.STANDARD:
            assert "concise but clear" in prompt.lower(), "STANDARD should emphasize balance"
            print("✅ PASS - Contains 'concise but clear'")
        elif level == VerbosityLevel.DETAILED:
            assert "complete explanation" in prompt.lower(), "DETAILED should emphasize thoroughness"
            print("✅ PASS - Contains 'complete explanation'")
    
    # Test group prompt with different verbosity levels
    print("\n--- Group Prompt Verbosity Tests ---")
    for level in VerbosityLevel:
        print(f"\nTesting {level.name} verbosity:")
        prompt = build_group_prompt(
            **group_data,
            verbosity=level
        )
        
        # Print excerpt to verify verbosity difference
        prompt_lines = prompt.split("\n")
        excerpt = "\n".join(prompt_lines[:5]) + "\n..."
        print(f"Prompt excerpt:\n{excerpt}")
        
        # Check verbosity-specific characteristics
        if level == VerbosityLevel.MINIMAL:
            assert "extremely concise" in prompt.lower(), "MINIMAL should emphasize extreme conciseness"
            print("✅ PASS - Contains 'extremely concise'")
        elif level == VerbosityLevel.STANDARD:
            assert "concise but clear" in prompt.lower(), "STANDARD should emphasize balance"
            print("✅ PASS - Contains 'concise but clear'")
        elif level == VerbosityLevel.DETAILED:
            assert "complete explanation" in prompt.lower(), "DETAILED should emphasize thoroughness"
            print("✅ PASS - Contains 'complete explanation'")

def run_test_case_17():
    """Run test case 17 to verify that course descriptions are accurate."""
    print("\n=== Testing Prompt Building with Course Descriptions ===")
    
    # Sample data for CSE 30
    uc_course = "CSE 30"
    uc_course_title = "Computer Organization and Systems Programming"
    rendered_logic = """
* Option A: CIS 21JA AND CIS 21JB AND CIS 26B
* Option B: CIS 21JA AND CIS 21JB AND CIS 26BH (Honors)
"""
    user_question = "How can I satisfy CSE 30 using De Anza classes?"
    
    # Build the prompt
    prompt = build_course_prompt(
        rendered_logic=rendered_logic,
        user_question=user_question,
        uc_course=uc_course,
        uc_course_title=uc_course_title
    )
    
    # Check for course descriptions in the prompt
    print("\nChecking for correct course descriptions in prompt:")
    expected_descriptions = [
        "CIS 21JA (Introduction to x86 Processor Assembly Language and Computer Architecture)",
        "CIS 21JB (Advanced x86 Processor Assembly Programming)",
        "CIS 26B (Advanced C Programming)"
    ]
    
    all_present = True
    for desc in expected_descriptions:
        if desc in prompt:
            print(f"✅ Found: {desc}")
        else:
            print(f"❌ Missing: {desc}")
            all_present = False
    
    if all_present:
        print("\n✅ All course descriptions are correct")
    else:
        print("\n❌ Some course descriptions are missing or incorrect")
    
    # Display the full prompt for reference
    print("\nFull Prompt:")
    print("-" * 60)
    print(prompt)
    print("-" * 60)

def test_relative_prompt_lengths():
    """Test that verbosity levels actually affect prompt length."""
    print("\n=== Testing Relative Prompt Lengths ===")
    
    # Test data
    test_data = {
        "rendered_logic": "* Option A: CIS 21JA AND CIS 21JB AND CIS 26B",
        "user_question": "How can I satisfy CSE 30?",
        "uc_course": "CSE 30",
        "uc_course_title": "Computer Organization and Systems Programming"
    }
    
    # Generate prompts at different verbosity levels
    minimal_prompt = build_course_prompt(**test_data, verbosity=VerbosityLevel.MINIMAL)
    standard_prompt = build_course_prompt(**test_data, verbosity=VerbosityLevel.STANDARD)
    detailed_prompt = build_course_prompt(**test_data, verbosity=VerbosityLevel.DETAILED)
    
    # Calculate lengths
    min_len = len(minimal_prompt)
    std_len = len(standard_prompt)
    det_len = len(detailed_prompt)
    
    print(f"MINIMAL prompt length: {min_len} characters")
    print(f"STANDARD prompt length: {std_len} characters")
    print(f"DETAILED prompt length: {det_len} characters")
    
    # Verify relative lengths
    if min_len < std_len < det_len:
        print("✅ PASS - Verbosity levels properly affect prompt length")
    else:
        print("❌ FAIL - Verbosity levels don't consistently affect prompt length")
        if min_len >= std_len:
            print(f"  Issue: MINIMAL ({min_len}) should be shorter than STANDARD ({std_len})")
        if std_len >= det_len:
            print(f"  Issue: STANDARD ({std_len}) should be shorter than DETAILED ({det_len})")

if __name__ == "__main__":
    # Run all tests
    test_extract_course_codes()
    test_enrich_with_descriptions()
    test_verbosity_levels()
    run_test_case_17()
    test_relative_prompt_lengths() 