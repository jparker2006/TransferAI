#!/usr/bin/env python3
"""
TransferAI Unit Test Runner

This script runs the unit test suite for the TransferAI articulation package.
It prioritizes the module-specific tests for the new architecture and includes
tests for both articulation modules and services.
"""

import unittest
import os
import sys
import warnings
import argparse

# Improve path setup for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Add both the current directory and parent directory to sys.path
# This ensures both direct imports and llm.* imports will work
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)  # For imports like "from articulation import X"
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)   # For imports like "from llm.articulation import X"

# Filter out deprecation warnings from legacy tests
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Define the test directory
TEST_DIR = os.path.join(current_dir, "tests")

def discover_tests(directory, pattern=None):
    """Discover tests in the specified directory with optional pattern filtering."""
    loader = unittest.TestLoader()
    if pattern:
        return loader.discover(directory, pattern=pattern)
    else:
        return loader.discover(directory)

def run_tests(test_modules=None, verbosity=2):
    """
    Run unit tests with optional filtering by module.
    
    Args:
        test_modules: List of module names to run (articulation, services, repositories, or None for all)
        verbosity: Test runner verbosity level
    
    Returns:
        Exit code (0 for success, 1 for failures)
    """
    print(f"\n=== TransferAI Unit Tests ===")
    print(f"Python path: {sys.path[:2]}")  # Show first two paths for debugging
    
    # Create a test suite
    suite = unittest.TestSuite()
    
    # Define module directories and their test patterns
    module_specs = {
        "articulation": {
            "dir": os.path.join(TEST_DIR, "articulation"),
            "pattern": "test_articulation_*.py"
        },
        "services": {
            "dir": os.path.join(TEST_DIR, "services"),
            "pattern": "test_*.py"
        },
        "repositories": {
            "dir": os.path.join(TEST_DIR, "repositories"),
            "pattern": "test_*.py"
        }
    }
    
    # Determine which modules to test
    modules_to_test = test_modules or list(module_specs.keys())
    
    # Add tests for selected modules
    for module in modules_to_test:
        if module in module_specs:
            spec = module_specs[module]
            module_dir = spec["dir"]
            pattern = spec["pattern"]
            
            if os.path.exists(module_dir):
                print(f"\nDiscovering tests in {module} module...")
                try:
                    module_tests = discover_tests(module_dir, pattern)
                    suite.addTest(module_tests)
                    print(f"Added tests from {module} module")
                except Exception as e:
                    print(f"Error loading tests from {module}: {e}")
            else:
                print(f"Warning: Test directory {module_dir} does not exist")
    
    # Create a test runner
    runner = unittest.TextTestRunner(verbosity=verbosity)
    
    # Run the tests
    result = runner.run(suite)
    
    # Return a failure code if any test failed
    return 0 if result.wasSuccessful() else 1

def main():
    """Parse command-line arguments and run tests."""
    parser = argparse.ArgumentParser(description="Run TransferAI unit tests")
    parser.add_argument('--modules', nargs='+', 
                      choices=['articulation', 'services', 'repositories', 'all'],
                      help='Specify which modules to test')
    parser.add_argument('--verbose', '-v', action='count', default=1,
                      help='Increase verbosity (can be used multiple times)')
    
    args = parser.parse_args()
    
    # Handle module selection
    if args.modules:
        if 'all' in args.modules:
            modules = None  # Run all modules
        else:
            modules = args.modules
    else:
        modules = None  # Default: run all modules
    
    # Run tests with selected modules and verbosity
    return run_tests(modules, args.verbose + 1)

if __name__ == "__main__":
    sys.exit(main()) 