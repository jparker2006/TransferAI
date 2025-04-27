#!/usr/bin/env python3
"""
TransferAI Unit Test Runner

This script runs the unit test suite for the TransferAI articulation package.
It prioritizes the module-specific tests for the new architecture.
"""

import unittest
import os
import sys
import warnings

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Filter out deprecation warnings from legacy tests
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Define the test directory
TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")

def run_tests():
    """Run all unit tests with a focus on the articulation package tests."""
    
    # Create a test loader
    loader = unittest.TestLoader()
    
    # The primary module-specific test files to run first
    primary_test_files = [
        "test_articulation_models.py",
        "test_articulation_validators.py", 
        "test_articulation_renderers.py",
        "test_articulation_formatters.py",
        "test_articulation_analyzers.py",
        "test_articulation_detectors.py",
        "test_migration.py"
    ]
    
    # Create a test suite for primary tests
    primary_suite = unittest.TestSuite()
    
    # Add primary tests to the suite
    for test_file in primary_test_files:
        test_path = os.path.join(TEST_DIR, test_file)
        if os.path.exists(test_path):
            suite = loader.discover(TEST_DIR, pattern=test_file)
            primary_suite.addTest(suite)
    
    # Run all other tests using discovery
    # full_suite = loader.discover(TEST_DIR)
    
    # Create a test runner
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Run the tests
    print("=== Running Primary Articulation Tests ===")
    primary_result = runner.run(primary_suite)
    
    # print("\n=== Running All Tests ===")
    # full_result = runner.run(full_suite)
    
    # Return a failure code if any test failed
    return 0 if primary_result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests()) 