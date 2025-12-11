# File: tests/coverage_report.py
#!/usr/bin/env python3
"""
Generate test coverage report for Parking Management System.
Requires: pip install coverage
"""

import coverage
import unittest
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))


def generate_coverage_report():
    """Generate test coverage report"""
    
    # Start coverage
    cov = coverage.Coverage(
        source=['src'],
        omit=['*/tests/*', '*/__pycache__/*']
    )
    cov.start()
    
    try:
        # Run tests
        from tests.run_tests import run_all_tests
        run_all_tests()
    finally:
        # Stop coverage
        cov.stop()
        cov.save()
    
    # Generate reports
    print("\n" + "="*60)
    print("Test Coverage Report")
    print("="*60)
    
    # Console report
    print("\nConsole Report:")
    cov.report()
    
    # HTML report
    print("\nGenerating HTML report...")
    cov.html_report(directory='htmlcov')
    print("HTML report generated in 'htmlcov' directory")
    
    # XML report (for CI/CD)
    print("\nGenerating XML report...")
    cov.xml_report(outfile='coverage.xml')
    print("XML report generated as 'coverage.xml'")


if __name__ == "__main__":
    generate_coverage_report()