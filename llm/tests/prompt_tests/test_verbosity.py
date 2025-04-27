#!/usr/bin/env python3
"""
Test script to verify different verbosity levels in prompt templates.
"""

import os
import sys
import re

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix prompt_builder import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm"))

# Import the necessary components
from llm.prompt_builder import (
    build_course_prompt, 
    build_group_prompt,
    VerbosityLevel
)

def test_case_7_verbosity():
    """Test verbosity for test case 7: path completion question."""
    print("🧪 Analyzing test case 7 verbosity...\n")
    
    test_question = "If I complete CSE 8A and 8B, is that one full path?"
    
    # Generate prompts at different verbosity levels
    test_details = {
        "rendered_logic": "* CSE 8A: MATH 1A OR MATH 1AH (Honors)\n* CSE 8B: MATH 1B OR MATH 1BH (Honors)",
        "user_question": test_question,
        "group_id": "1",
        "group_title": "Lower Division CSE",
        "group_logic_type": "all_required"
    }
    
    minimal_prompt = build_group_prompt(
        **test_details,
        verbosity=VerbosityLevel.MINIMAL
    )
    
    standard_prompt = build_group_prompt(
        **test_details,
        verbosity=VerbosityLevel.STANDARD
    )
    
    detailed_prompt = build_group_prompt(
        **test_details,
        verbosity=VerbosityLevel.DETAILED
    )
    
    # Calculate prompt sizes
    min_size = len(minimal_prompt)
    std_size = len(standard_prompt)
    det_size = len(detailed_prompt)
    
    print(f"Test Case 7 - Path Completion Question")
    print(f"MINIMAL prompt size: {min_size} characters")
    print(f"STANDARD prompt size: {std_size} characters")
    print(f"DETAILED prompt size: {det_size} characters")
    print(f"Size reduction (DETAILED → MINIMAL): {100 - (min_size / det_size * 100):.1f}%")
    
    # Print Minimal prompt sample
    print("\nMINIMAL prompt (excerpt):")
    print("---")
    print("\n".join(minimal_prompt.split("\n")[:15]))
    print("...\n")
    
    return min_size < std_size < det_size

def test_case_8_verbosity():
    """Test verbosity for test case 8: group combinations question."""
    print("🧪 Analyzing test case 8 verbosity...\n")
    
    test_question = "What are all valid De Anza combinations to satisfy Group 1 at UCSD?"
    
    # Generate prompts at different verbosity levels
    test_details = {
        "rendered_logic": "Group 1 requires one full articulation path:\n* Section A: Math and Science\n  * MATH 1A OR MATH 1AH (Honors)\n  * MATH 1B OR MATH 1BH (Honors)\n  * PHYS 4A\n* Section B: Computer Science\n  * CIS 22A OR CIS 22AH (Honors)\n  * CIS 22B OR CIS 22BH (Honors)\n  * CIS 22C",
        "user_question": test_question,
        "group_id": "1",
        "group_title": "Lower Division Requirements",
        "group_logic_type": "choose_one_section"
    }
    
    minimal_prompt = build_group_prompt(
        **test_details,
        verbosity=VerbosityLevel.MINIMAL
    )
    
    standard_prompt = build_group_prompt(
        **test_details,
        verbosity=VerbosityLevel.STANDARD
    )
    
    detailed_prompt = build_group_prompt(
        **test_details,
        verbosity=VerbosityLevel.DETAILED
    )
    
    # Calculate prompt sizes
    min_size = len(minimal_prompt)
    std_size = len(standard_prompt)
    det_size = len(detailed_prompt)
    
    print(f"Test Case 8 - Group Combinations")
    print(f"MINIMAL prompt size: {min_size} characters")
    print(f"STANDARD prompt size: {std_size} characters")
    print(f"DETAILED prompt size: {det_size} characters")
    print(f"Size reduction (DETAILED → MINIMAL): {100 - (min_size / det_size * 100):.1f}%")
    
    # Print Minimal prompt sample
    print("\nMINIMAL prompt (excerpt):")
    print("---")
    print("\n".join(minimal_prompt.split("\n")[:15]))
    print("...\n")
    
    return min_size < std_size < det_size

def test_case_22_verbosity():
    """Test verbosity for test case 22: multiple course validation."""
    print("🧪 Analyzing test case 22 verbosity...\n")
    
    test_question = "Can I take MATH 1A and MATH 1B to satisfy MATH 10A and 10B at UCSD?"
    
    # Generate prompts at different verbosity levels
    test_details = {
        "rendered_logic": "* Option A: MATH 1A OR MATH 1AH (Honors)\n* Option B: MATH 1B OR MATH 1BH (Honors)",
        "user_question": test_question,
        "uc_course": "MATH 10A, MATH 10B",
        "uc_course_title": "Calculus I and Calculus II"
    }
    
    minimal_prompt = build_course_prompt(
        **test_details,
        verbosity=VerbosityLevel.MINIMAL
    )
    
    standard_prompt = build_course_prompt(
        **test_details,
        verbosity=VerbosityLevel.STANDARD
    )
    
    detailed_prompt = build_course_prompt(
        **test_details,
        verbosity=VerbosityLevel.DETAILED
    )
    
    # Calculate prompt sizes
    min_size = len(minimal_prompt)
    std_size = len(standard_prompt)
    det_size = len(detailed_prompt)
    
    print(f"Test Case 22 - Multiple Course Validation")
    print(f"MINIMAL prompt size: {min_size} characters")
    print(f"STANDARD prompt size: {std_size} characters")
    print(f"DETAILED prompt size: {det_size} characters")
    print(f"Size reduction (DETAILED → MINIMAL): {100 - (min_size / det_size * 100):.1f}%")
    
    # Print Minimal prompt sample
    print("\nMINIMAL prompt (excerpt):")
    print("---")
    print("\n".join(minimal_prompt.split("\n")[:15]))
    print("...\n")
    
    return min_size < std_size < det_size

def main():
    """Run all verbosity tests."""
    print("=== TransferAI Verbosity Test ===\n")
    
    test_results = {
        "Test 7": test_case_7_verbosity(),
        "Test 8": test_case_8_verbosity(),
        "Test 22": test_case_22_verbosity()
    }
    
    # Print summary
    print("\n=== Test Summary ===")
    all_passed = all(test_results.values())
    for test, passed in test_results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test}: {status}")
    
    if all_passed:
        print("\n✅ All verbosity tests passed!")
        print("Prompts show proper size reduction with lower verbosity levels.")
    else:
        print("\n❌ Some verbosity tests failed.")
        print("Some verbosity levels are not properly implemented.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 