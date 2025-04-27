"""
Test Runner Module for TransferAI

This module provides functionality for automated testing of the TransferAI system.
It includes:

1. Predefined test prompts covering a variety of articulation cases
2. Functions to run tests in batches or individually
3. Result saving and reporting capabilities
4. Regression test cases to ensure system stability across versions

The test suite covers basic course equivalency, multi-course logic, honors variants,
validation-style prompts, and edge cases to ensure TransferAI provides accurate
articulation information.
"""

import os
import time
import sys
from typing import List, Dict, Any, Tuple

# Fix the import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm.main import TransferAIEngine

# 🔍 High-coverage prompt-based articulation test suite (De Anza → UCSD)
# Includes edge cases, multi-course logic, honors variants, and validation-style prompts

OG_test_prompts = [
    "Which De Anza courses satisfy CSE 8A at UCSD?",
    "Do I need to take both CIS 36A and CIS 36B to get credit for CSE 11?",
    "What De Anza courses are required to satisfy Group 2 for Computer Science at UCSD?",
    "How many science courses do I need to transfer for UCSD Computer Science under Group 3?",
    "Does De Anza have an equivalent for CSE 21 at UCSD?",
    "What De Anza courses count for CSE 30 at UC San Diego?",
    "What De Anza classes satisfy BILD 1 for UCSD transfer?",
]


test_prompts = [
    "Which De Anza courses satisfy CSE 8A at UCSD?",
    "Which courses satisfy CSE 8B?",
    "Which courses satisfy CSE 11?",
    "Do I need to take both CIS 36A and CIS 36B to get credit for CSE 11?",
    "Can I take CIS 22A and CIS 36B to satisfy anything in Group 1?",
    "Can I mix CIS 22A and CIS 35A for Group 1 at UCSD?",  # invalid cross-section
    "If I complete CSE 8A and 8B, is that one full path?",
    "What are all valid De Anza combinations to satisfy Group 1 at UCSD?",
    "What De Anza courses are required to satisfy Group 2 for Computer Science at UCSD?",
    "Which courses count for CSE 12 at UCSD?",
    "What satisfies MATH 18 for UCSD transfer?",
    "Does MATH 2BH satisfy MATH 18?",
    "Can I take MATH 2B instead of MATH 2BH for MATH 18?",
    "Is CSE 21 articulated from De Anza?",  # no articulation
    "Can I complete just CIS 21JA and 21JB to satisfy CSE 30?",
    "Does CSE 15L have any articulation?",
    "How can I satisfy CSE 30 using De Anza classes?",
    "Does MATH 1CH and 1DH count for MATH 20C?",
    "What De Anza classes satisfy MATH 20C at UCSD?",
    "Is there a difference between MATH 1A and MATH 1AH for transfer credit?",
    "Which courses satisfy MATH 20A and 20B?",
    "List all options for CSE 30 at UCSD from De Anza.",
    "What are my options for fulfilling Group 3 science requirements for CS at UCSD?",
    "What courses count for BILD 1?",
    "Can I take BIOL 6A and 6B only to satisfy BILD 1?",
    "How many science courses do I need to transfer for UCSD Computer Science under Group 3?",
    "Can I satisfy Group 3 with CHEM 1A and PHYS 4A?",
    "Does PHYS 4A articulate to UCSD?",
    "Does BILD 2 require the same BIOL series as BILD 1?",
    "What De Anza courses are required for CHEM 6A and 6B?",
    "If I took CIS 36A, can it satisfy more than one UCSD course?",
    "Are any honors courses required for the CS transfer path from De Anza to UCSD?",
    # New test cases for v1.4 features
    "Does CSE 12 require honors courses at De Anza?",
    "Can I take both MATH 1A and MATH 1AH for MATH 20A?",
    "Which UC courses can I satisfy with CIS 36A?",
    "Does CIS 22C satisfy CSE 12?",
]



regression_tests = [
    "Which De Anza courses satisfy CSE 8A at UCSD?",              # CIS 36A alone is valid
    "Which courses satisfy CSE 11?",                              # Needs CIS 36A + CIS 36B (make sure prompt still builds!)
    "Do I need to take both CIS 36A and CIS 36B to get credit for CSE 11?",  # LLM required
    "If I complete CSE 8A and 8B, is that one full path?",        # Should NOT trigger R31 logic
    "Can I take CIS 22A and CIS 36B to satisfy anything in Group 1?",  # Group logic, unrelated
    "If I took CIS 36A, can it satisfy more than one UCSD course?",  # ✅ We just fixed this!
    # New v1.4 regression tests
    "Does CSE 12 require honors courses at De Anza?", # Should say no, honors not required for CSE 12
    "Can I take both MATH 1A and MATH 1AH for MATH 20A?", # Should detect redundant courses
]




def run_batch_tests(start_idx: int = 0, batch_size: int = 5, output_file: str = None) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Run a batch of test prompts and collect the results.
    
    This function initializes the TransferAI engine, processes a subset of test_prompts
    from start_idx to start_idx+batch_size, and captures the responses.
    
    Args:
        start_idx: Starting index in the test_prompts list.
        batch_size: Number of tests to run in this batch.
        output_file: Optional file path to save results to. If provided, results are appended.
        
    Returns:
        A tuple containing the ending index and a list of result dictionaries with:
        - test_num: Test number
        - prompt: The test prompt
        - response: TransferAI's response
        - timestamp: When the test was run
        
    Example:
        >>> end_idx, results = run_batch_tests(0, 5, "results.txt")
        >>> print(f"Ran tests 1-{end_idx} with {len(results)} results")
    """
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    
    print(f"🧪 Running TransferAI test batch {start_idx//batch_size + 1}...\n")
    all_results = []
    
    end_idx = min(start_idx + batch_size, len(test_prompts))
    for i in range(start_idx, end_idx):
        prompt = test_prompts[i]
        print(f"===== Test {i+1}: {prompt} =====")
        
        # Store result in a dictionary
        result = {
            "test_num": i+1,
            "prompt": prompt,
            "response": "",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        response = engine.handle_query(prompt)
        if response:
            print(response.strip())
            result["response"] = response.strip()
        print("=" * 60 + "\n")
        all_results.append(result)
    
    # If output file is provided, append results
    if output_file:
        with open(output_file, 'a') as f:
            f.write(f"🧪 Running TransferAI test batch {start_idx//batch_size + 1}...\n\n")
            for result in all_results:
                f.write(f"===== Test {result['test_num']}: {result['prompt']} =====\n")
                f.write(result['response'] + "\n")
                f.write("=" * 60 + "\n\n")
    
    return end_idx, all_results

def run_all_tests_and_save(output_file: str = "llm/testing/TransferAI v1.5.txt") -> List[Dict[str, Any]]:
    """
    Run all tests and save the results to a file for regression testing.
    
    This function runs all test prompts in batches, saves the results to the specified
    output file, and adds summary statistics.
    
    Args:
        output_file: Path where test results should be saved.
        
    Returns:
        A list of all test result dictionaries.
        
    Example:
        >>> results = run_all_tests_and_save("test_results.txt")
        >>> print(f"Completed {len(results)} tests")
    """
    # Create/clear the output file
    with open(output_file, 'w') as f:
        f.write(f"🧮 TransferAI v1.4 Test Suite Results - {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    # Run tests in batches of 5
    start_idx = 0
    all_results = []
    
    while start_idx < len(test_prompts):
        end_idx, batch_results = run_batch_tests(start_idx, 5, output_file)
        start_idx = end_idx
        all_results.extend(batch_results)
        
        # Small delay to avoid overwhelming the model
        time.sleep(2)
    
    # Add summary metrics at the end
    with open(output_file, 'a') as f:
        f.write("\n\n🧮 Final TransferAI v1.4 Test Suite Stats\n\n")
        f.write(f"Total Tests: {len(all_results)}\n")
        f.write(f"Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"✅ All test results saved to {output_file}")
    return all_results

def run_specific_test(test_prompt: str, output_file: str = None) -> str:
    """
    Run a single specific test prompt and optionally save the result.
    
    This function initializes the TransferAI engine, processes a single test prompt,
    and returns the response.
    
    Args:
        test_prompt: The specific prompt to test with TransferAI.
        output_file: Optional file path to append the result to.
        
    Returns:
        The response from TransferAI for the given prompt.
        
    Example:
        >>> response = run_specific_test("Does CSE 12 require honors courses?")
        >>> print(response)
    """
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    print(f"🧪 Running specific test...\n")
    
    print(f"===== Test: {test_prompt} =====")
    response = engine.handle_query(test_prompt)
    
    if response:
        print(response.strip())
        
        # If output file is provided, append result
        if output_file:
            with open(output_file, 'a') as f:
                f.write(f"===== Specific Test: {test_prompt} =====\n")
                f.write(response.strip() + "\n")
                f.write("=" * 60 + "\n\n")
    
    print("=" * 60 + "\n")
    return response if response else ""

if __name__ == "__main__":
    # Create the testing directory if it doesn't exist
    os.makedirs("llm/testing", exist_ok=True)
    
    # Run tests in smaller batches and save results
    output_file = "llm/testing/TransferAI v1.5.txt"
    run_all_tests_and_save(output_file)
    
    # You can also run specific tests like this:
    # run_specific_test("Does CSE 12 require honors courses at De Anza?", output_file)
