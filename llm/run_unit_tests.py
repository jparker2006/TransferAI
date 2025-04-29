#!/usr/bin/env python3
"""
TransferAI Unit Test Runner

This script runs all unit tests for the TransferAI system,
or specific test modules if specified.
"""

import os
import sys
import unittest
import argparse
import logging
import importlib.util
from typing import List, Optional

# Add the project root and llm directory to Python path for proper imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
llm_dir = os.path.join(project_root, "llm")
sys.path.insert(0, project_root)
sys.path.insert(0, llm_dir)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def discover_tests(test_dir: str, pattern: str = "test_*.py") -> unittest.TestSuite:
    """
    Discover tests in the specified directory.
    
    Args:
        test_dir: Directory to discover tests in
        pattern: Pattern to match test files
        
    Returns:
        Test suite containing all discovered tests
    """
    logger.info(f"Discovering all tests in {test_dir}...")
    
    if not os.path.exists(test_dir):
        logger.warning(f"Test directory not found: {test_dir}")
        return unittest.TestSuite()
    
    loader = unittest.defaultTestLoader
    suite = loader.discover(test_dir, pattern=pattern)
    
    # Explicitly discover tests in services directory with proper naming
    services_dir = os.path.join(test_dir, "services")
    if os.path.exists(services_dir):
        for file in os.listdir(services_dir):
            if file.startswith("test_") and file.endswith(".py"):
                module_name = f"llm.tests.services.{os.path.splitext(file)[0]}"
                try:
                    module = importlib.import_module(module_name)
                    test_suite = loader.loadTestsFromModule(module)
                    suite.addTests(test_suite)
                    logger.debug(f"Loaded tests from {module_name}")
                except Exception as e:
                    logger.error(f"Error loading module {module_name}: {str(e)}")
    
    return suite


def load_test_module(module_path: str) -> Optional[unittest.TestSuite]:
    """
    Load a test module from the specified path.
    
    Args:
        module_path: Dotted path to the test module
        
    Returns:
        Test suite for the module, or None if the module is not found
    """
    try:
        # Skip direct 'services.test_*' module imports - these are handled by our custom discovery
        if module_path.startswith("services.test_"):
            # Convert 'services.test_x' to 'llm.tests.services.test_x'
            module_name = f"llm.tests.{module_path}"
            logger.debug(f"Redirecting {module_path} to {module_name}")
        # Handle llm.tests prefix and direct module names
        elif module_path.startswith("llm.tests."):
            module_name = module_path
        elif module_path.startswith("tests."):
            module_name = f"llm.{module_path}"
        else:
            module_name = f"llm.tests.{module_path}"
        
        logger.debug(f"Trying to load module: {module_name}")
        
        # Try direct import first
        try:
            module = importlib.import_module(module_name)
            return unittest.defaultTestLoader.loadTestsFromModule(module)
        except ModuleNotFoundError:
            # Fall back to file-based loading if needed
            module_parts = module_name.split(".")
            if len(module_parts) > 1:
                rel_path = os.path.join(*module_parts[1:]) + ".py"
                abs_path = os.path.join(llm_dir, rel_path)
                
                if os.path.exists(abs_path):
                    spec = importlib.util.spec_from_file_location(module_name, abs_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    return unittest.defaultTestLoader.loadTestsFromModule(module)
            
            logger.warning(f"Test module not found: {module_name}")
            return None
            
    except Exception as e:
        logger.error(f"Error loading test module {module_path}: {str(e)}")
        return None


def run_tests(tests: List[str] = None, test_dir: str = None, verbosity: int = 1) -> bool:
    """
    Run the specified tests or discover and run all tests.
    
    Args:
        tests: List of test module paths to run
        test_dir: Directory to discover tests in, if tests is None
        verbosity: Verbosity level for test output
        
    Returns:
        True if all tests passed, False otherwise
    """
    logger.info("=== TransferAI Unit Tests ===")
    logger.info(f"Python path: {sys.path[:2]}")
    
    suite = unittest.TestSuite()
    
    # Determine test directory
    test_dir = test_dir or os.path.join(llm_dir, "tests")
    services_dir = os.path.join(test_dir, "services")
    
    # Flag to track if we need to add services tests manually
    include_services = True
    
    if tests:
        # Skip any service test direct references
        non_service_tests = [t for t in tests if not t.startswith("services.test_")]
        service_tests = [t for t in tests if t.startswith("services.test_")]
        
        if service_tests and not non_service_tests:
            # Only service tests were requested
            # Only load service tests
            include_services = True
            tests = []
        else:
            # Mixed or non-service tests
            tests = non_service_tests
            # Only include service tests if they were explicitly requested
            include_services = len(service_tests) > 0
        
        # Run specific non-service test modules
        for test_path in tests:
            test_suite = load_test_module(test_path)
            if test_suite:
                suite.addTests(test_suite)
    else:
        # Discover and run all non-service tests
        # We'll add services tests separately to avoid duplicates
        for root, dirs, files in os.walk(test_dir):
            # Skip the services directory - we'll handle it separately
            if "services" in dirs:
                dirs.remove("services")
                
            # Only process Python test files
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    rel_path = os.path.relpath(os.path.join(root, file), llm_dir)
                    module_name = os.path.splitext(rel_path)[0].replace(os.path.sep, ".")
                    try:
                        module = importlib.import_module(module_name)
                        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
                        logger.debug(f"Loaded tests from {module_name}")
                    except Exception as e:
                        logger.error(f"Error loading module {module_name}: {str(e)}")
    
    # Add service tests if requested or if running all tests
    if include_services and os.path.exists(services_dir):
        logger.info(f"Discovering service tests in {services_dir}...")
        for file in os.listdir(services_dir):
            if file.startswith("test_") and file.endswith(".py"):
                module_name = f"llm.tests.services.{os.path.splitext(file)[0]}"
                try:
                    module = importlib.import_module(module_name)
                    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
                    logger.debug(f"Loaded tests from {module_name}")
                except Exception as e:
                    logger.error(f"Error loading module {module_name}: {str(e)}")
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description="Run TransferAI unit tests")
    parser.add_argument("tests", nargs="*", help="Specific test modules to run")
    parser.add_argument("--test_dir", help="Directory to discover tests in")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    success = run_tests(
        tests=args.tests,
        test_dir=args.test_dir,
        verbosity=2 if args.verbose else 1
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 