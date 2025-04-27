#!/usr/bin/env python3
"""
Simple test runner for TransferAI test cases.
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Fix articulation module import
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm"))

# Import the necessary components
from llm.prompt_builder import build_prompt, PromptType, VerbosityLevel
from llm.main import TransferAIEngine


def run_test_case_7():
    """Run test case 7 to test group prompt handling."""
    print("🧪 Running test case 7...\n")
    
    test_prompt = "If I complete CSE 8A and 8B, is that one full path?"
    print(f"===== Test 7: {test_prompt} =====")
    
    # Initialize the engine
    engine = TransferAIEngine()
    engine.configure(verbosity=VerbosityLevel.MINIMAL)  # Set MINIMAL verbosity
    engine.load()
    
    # Run the query
    response = engine.handle_query(test_prompt)
    
    if response:
        print(response.strip())
    else:
        print("No direct response (LLM response was returned)")
    
    print("=" * 60 + "\n")

def run_test_case_8():
    """Run test case 8 to test group prompt handling."""
    print("🧪 Running test case 8...\n")
    
    test_prompt = "What are all valid De Anza combinations to satisfy Group 1 at UCSD?"
    print(f"===== Test 8: {test_prompt} =====")
    
    # Initialize the engine
    engine = TransferAIEngine()
    engine.configure(verbosity=VerbosityLevel.MINIMAL)  # Set MINIMAL verbosity
    engine.load()
    
    # Run the query
    response = engine.handle_query(test_prompt)
    
    if response:
        print(response.strip())
    else:
        print("No direct response (LLM response was returned)")
    
    print("=" * 60 + "\n")

def run_test_case_9():
    """Run test case 9 to test group prompt handling."""
    print("🧪 Running test case 9...\n")
    
    test_prompt = "What De Anza courses are required to satisfy Group 2 for Computer Science at UCSD?"
    print(f"===== Test 9: {test_prompt} =====")
    
    # Initialize the engine
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    
    # Run the query
    response = engine.handle_query(test_prompt)
    
    if response:
        print(response.strip())
    else:
        print("No direct response (LLM response was returned)")
    
    print("=" * 60 + "\n")

def run_test_case_13():
    """Run test case 13 to test standardized honors course notation."""
    print("🧪 Running test case 13...\n")
    
    test_prompt = "Do I need to take honors courses to satisfy Group 2 at UCSD? Can I take MATH, CIS, or CSE courses?"
    print(f"===== Test 13: {test_prompt} =====")
    
    # Initialize the engine
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    
    # Run the query
    response = engine.handle_query(test_prompt)
    
    if response:
        print(response.strip())
    else:
        print("No direct response (LLM response was returned)")
    
    print("=" * 60 + "\n")

def run_test_case_15():
    """Run test case 15 to test partial match explanation improvements."""
    print("🧪 Running test case 15...\n")
    
    test_prompt = "Can I complete just CIS 21JA and 21JB to satisfy CSE 30?"
    print(f"===== Test 15: {test_prompt} =====")
    
    # Initialize the engine
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    
    # Run the query
    response = engine.handle_query(test_prompt)
    
    if response:
        print(response.strip())
    else:
        print("No direct response (LLM response was returned)")
    
    print("=" * 60 + "\n")

def run_test_case_17():
    """Run test case 17 to test course description accuracy."""
    print("🧪 Running test case 17...\n")
    
    test_prompt = "How can I satisfy CSE 30 using De Anza classes?"
    print(f"===== Test 17: {test_prompt} =====")
    
    # Initialize the engine
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    
    # Run the query
    response = engine.handle_query(test_prompt)
    
    if response:
        print(response.strip())
    else:
        print("No direct response (LLM response was returned)")
    
    print("=" * 60 + "\n")

def run_test_case_20():
    """Run test case 20 to test honors notation with single-course query."""
    print("🧪 Running test case 20...\n")
    
    test_prompt = "Can I take MATH 2BH to satisfy MATH 18 at UCSD?"
    print(f"===== Test 20: {test_prompt} =====")
    
    # Initialize the engine
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    
    # Run the query
    response = engine.handle_query(test_prompt)
    
    if response:
        print(response.strip())
    else:
        print("No direct response (LLM response was returned)")
    
    print("=" * 60 + "\n")

def run_test_case_22():
    """Run test case 22 to test response verbosity."""
    print("🧪 Running test case 22...\n")
    
    test_prompt = "Can I take MATH 1A and MATH 1B to satisfy MATH 10A and 10B at UCSD?"
    print(f"===== Test 22: {test_prompt} =====")
    
    # Initialize the engine
    engine = TransferAIEngine()
    engine.configure(verbosity=VerbosityLevel.MINIMAL)  # Set MINIMAL verbosity
    engine.load()
    
    # Run the query
    response = engine.handle_query(test_prompt)
    
    if response:
        print(response.strip())
    else:
        print("No direct response (LLM response was returned)")
    
    print("=" * 60 + "\n")

def run_test_case_25():
    """Run test case 25 to test another partial match scenario."""
    print("🧪 Running test case 25...\n")
    
    test_prompt = "Can I take BIOL 6A and 6B only to satisfy BILD 1?"
    print(f"===== Test 25: {test_prompt} =====")
    
    # Initialize the engine
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    
    # Run the query
    response = engine.handle_query(test_prompt)
    
    if response:
        print(response.strip())
    else:
        print("No direct response (LLM response was returned)")
    
    print("=" * 60 + "\n")

def run_test_case_34():
    """Run test case 34 to test honors notation in complex articulation cases."""
    print("🧪 Running test case 34...\n")
    
    test_prompt = "What's the difference between MATH 2B and MATH 2BH for transfer to UCSD?"
    print(f"===== Test 34: {test_prompt} =====")
    
    # Initialize the engine
    engine = TransferAIEngine()
    engine.configure()
    engine.load()
    
    # Run the query
    response = engine.handle_query(test_prompt)
    
    if response:
        print(response.strip())
    else:
        print("No direct response (LLM response was returned)")
    
    print("=" * 60 + "\n")

if __name__ == "__main__":
    # Get test case number from command line args
    if len(sys.argv) > 1:
        test_num = sys.argv[1]
        if test_num == "7":
            run_test_case_7()
        elif test_num == "8":
            run_test_case_8()
        elif test_num == "9":
            run_test_case_9()
        elif test_num == "13":
            run_test_case_13()
        elif test_num == "15":
            run_test_case_15()
        elif test_num == "17":
            run_test_case_17()
        elif test_num == "20":
            run_test_case_20()
        elif test_num == "22":
            run_test_case_22()
        elif test_num == "25":
            run_test_case_25()
        elif test_num == "34":
            run_test_case_34()
        else:
            print(f"Unknown test case: {test_num}")
            print("Available tests: 7, 8, 9, 13, 15, 17, 20, 22, 25, 34")
    else:
        # Run all tests if no specific test is requested
        run_test_case_15()
        run_test_case_25() 