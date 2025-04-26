#!/usr/bin/env python3
"""
Run all unit tests for the TransferAI LLM implementation.
"""

import unittest
import sys
import os

# Add the current directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_all_tests():
    """Run all tests in the tests directory."""
    print("🧪 Running TransferAI LLM unit tests...")
    
    # Discover and run all tests in the tests directory
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests', pattern='test_*.py')
    
    # Run the tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Return exit code based on test success
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(run_all_tests()) 