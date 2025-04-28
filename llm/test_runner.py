"""
Test Runner Module for TransferAI

This module provides functionality for automated testing of the TransferAI system.
It includes:

1. Predefined test prompts covering a variety of articulation cases
2. Functions to run tests in batches or individually
3. Support for running specific tests by number or prompt text
4. Simple command-line interface for test selection

The test suite covers basic course equivalency, multi-course logic, honors variants,
validation-style prompts, and edge cases to ensure TransferAI provides accurate
articulation information.
"""

import os
import time
import sys
import argparse
from typing import List, Dict, Any, Tuple, Optional, Union

# Fix the import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import the new TransferAIEngine from the refactored architecture
from llm.engine.transfer_engine import TransferAIEngine
from llm.engine.config import Config

# Set up models for testing
from llama_index.core.settings import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama

# Configure embeddings and LLM model
embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
Settings.embed_model = embed_model

# Create the Ollama LLM instance for deepseekr1:1.5b
llm_model = Ollama(model="deepseek-r1:1.5b", request_timeout=30.0)
Settings.llm = llm_model  # Set default LLM for LlamaIndex

# 🔍 High-coverage prompt-based articulation test suite (De Anza → UCSD)
# Includes edge cases, multi-course logic, honors variants, and validation-style prompts

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

def initialize_engine() -> TransferAIEngine:
    """Initialize and configure a TransferAIEngine instance with the LLM model."""
    # Create a configuration with the LLM model
    config = Config()
    config.update(
        llm_model="deepseek-r1:1.5b",
        verbosity="STANDARD",
        debug_mode=True
    )
    
    # Create engine with the configuration
    engine = TransferAIEngine(config=config)
    
    # Load documents and initialize handlers
    engine.load()
    print("Engine initialized with deepseek-r1:1.5b model")
    return engine

def run_test_by_index(index: int) -> str:
    """
    Run a specific test by its index in the test_prompts list.
    
    Args:
        index: The 1-based index of the test to run
        
    Returns:
        The response from TransferAI
    """
    if index < 1 or index > len(test_prompts):
        return f"Error: Test index must be between 1 and {len(test_prompts)}"
        
    prompt = test_prompts[index-1]
    print(f"\n===== Test {index}: {prompt} =====")
    
    engine = initialize_engine()
    response = engine.handle_query(prompt)
    
    if response:
        print(response.strip())
    else:
        print("No response received")
        
    print("=" * 60 + "\n")
    return response if response else ""

def run_test_by_prompt(prompt: str) -> str:
    """
    Run a test with a custom prompt.
    
    Args:
        prompt: The prompt text to test
        
    Returns:
        The response from TransferAI
    """
    print(f"\n===== Custom Test: {prompt} =====")
    
    engine = initialize_engine()
    response = engine.handle_query(prompt)
    
    if response:
        print(response.strip())
    else:
        print("No response received")
        
    print("=" * 60 + "\n")
    return response if response else ""

def run_batch_tests(start_idx: int = 0, count: int = 5) -> List[Dict[str, Any]]:
    """
    Run a batch of test prompts and return the results.
    
    Args:
        start_idx: Starting index in the test_prompts list (0-based)
        count: Number of tests to run
        
    Returns:
        A list of result dictionaries
    """
    engine = initialize_engine()
    print(f"\n🧪 Running test batch ({start_idx+1}-{min(start_idx+count, len(test_prompts))})...\n")
    results = []
    
    end_idx = min(start_idx + count, len(test_prompts))
    for i in range(start_idx, end_idx):
        prompt = test_prompts[i]
        print(f"===== Test {i+1}: {prompt} =====")
        
        response = engine.handle_query(prompt)
        if response:
            print(response.strip())
            results.append({
                "test_num": i+1,
                "prompt": prompt,
                "response": response.strip()
            })
        else:
            print("No response received")
            results.append({
                "test_num": i+1,
                "prompt": prompt,
                "response": "No response"
            })
            
        print("=" * 60 + "\n")
    
    return results

def list_available_tests() -> None:
    """Print all available tests with their indices."""
    print("\nAvailable Tests:")
    print("-" * 80)
    for i, prompt in enumerate(test_prompts, 1):
        print(f"{i:2d}. {prompt}")
    print("-" * 80)

def check_ollama_service():
    """Check if Ollama service is running and deepseek-r1:1.5b is available."""
    import subprocess
    import json
    
    try:
        # Check if Ollama service is running
        process = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if process.returncode != 0:
            print("⚠️ WARNING: Ollama service may not be running")
            print("Start Ollama with: ollama serve")
            return False
            
        # Check if the deepseek-r1:1.5b model is available
        if "deepseek-r1:1.5b" not in process.stdout:
            print("⚠️ WARNING: deepseek-r1:1.5b model not found in Ollama")
            print("Please install the model with: ollama pull deepseek-r1:1.5b")
            return False
            
        return True
    except Exception as e:
        print(f"⚠️ WARNING: Error checking Ollama service: {str(e)}")
        return False

def main() -> None:
    """Command-line interface for running tests."""
    # First check if Ollama service is running with the right model
    check_ollama_service()
    
    parser = argparse.ArgumentParser(description="TransferAI Test Runner")
    
    # Create mutually exclusive group for test selection
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-t", "--test", type=int, help="Run a specific test by number")
    group.add_argument("-p", "--prompt", type=str, help="Run a custom test prompt")
    group.add_argument("-b", "--batch", type=int, nargs=2, metavar=("START", "COUNT"),
                      help="Run a batch of tests starting at START and running COUNT tests")
    group.add_argument("-l", "--list", action="store_true", help="List all available tests")
    
    args = parser.parse_args()
    
    if args.list:
        list_available_tests()
    elif args.test:
        run_test_by_index(args.test)
    elif args.prompt:
        run_test_by_prompt(args.prompt)
    elif args.batch:
        run_batch_tests(args.batch[0]-1, args.batch[1])  # Convert to 0-based index
    else:
        # No arguments provided, show help
        list_available_tests()
        print("\nRun a specific test with: python test_runner.py -t <test_number>")
        print("Run a custom prompt with: python test_runner.py -p \"Your prompt here\"")
        print("Run a batch of tests with: python test_runner.py -b <start> <count>")

if __name__ == "__main__":
    main()
