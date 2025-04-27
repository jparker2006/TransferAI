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
from llm.prompt_builder import build_prompt, PromptType
from llm.main import TransferAIEngine

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

if __name__ == "__main__":
    # Uncomment the test you want to run
    # run_test_case_9()
    run_test_case_15()
    run_test_case_25() 