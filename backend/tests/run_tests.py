# File: tests/run_tests.py
#!/usr/bin/env python3
"""
Test runner for Parking Management System tests.
"""

import unittest
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))


def run_all_tests():
    """Run all test suites"""
    # Discover all tests in the tests directory
    test_loader = unittest.TestLoader()
    
    # Pattern to match test files
    test_pattern = 'test_*.py'
    
    # Start directory
    start_dir = str(Path(__file__).parent)
    
    # Discover tests
    test_suite = test_loader.discover(start_dir, pattern=test_pattern)
    
    # Run tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    return result


def run_specific_test(test_name):
    """Run a specific test module or test case"""
    test_loader = unittest.TestLoader()
    
    if '.' in test_name:
        # Specific test case
        module_name, test_case = test_name.split('.', 1)
        module = __import__(f'tests.{module_name}', fromlist=[test_case])
        test_class = getattr(module, test_case)
        test_suite = test_loader.loadTestsFromTestCase(test_class)
    else:
        # Entire test module
        module = __import__(f'tests.{test_name}', fromlist=['*'])
        test_suite = test_loader.loadTestsFromModule(module)
    
    test_runner = unittest.TextTestRunner(verbosity=2)
    return test_runner.run(test_suite)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        result = run_specific_test(test_name)
    else:
        # Run all tests
        result = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)