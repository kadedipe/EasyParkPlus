#!/usr/bin/env python3
"""
Test Runner for Domain Layer Unit Tests

This script runs all domain layer unit tests and provides detailed reporting.
"""

import unittest
import sys
import os
import argparse
from datetime import datetime
from io import StringIO


class TestRunner:
    """Custom test runner with enhanced reporting"""
    
    def __init__(self, verbosity=2, failfast=False, buffer=True):
        self.verbosity = verbosity
        self.failfast = failfast
        self.buffer = buffer
        self.results = None
        self.start_time = None
        self.end_time = None
        
    def run_tests(self, test_suite):
        """Run the test suite and return results"""
        self.start_time = datetime.now()
        
        # Create test runner
        runner = unittest.TextTestRunner(
            verbosity=self.verbosity,
            failfast=self.failfast,
            buffer=self.buffer,
            descriptions=True,
            resultclass=unittest.TextTestResult
        )
        
        # Run tests
        self.results = runner.run(test_suite)
        self.end_time = datetime.now()
        
        return self.results
    
    def get_summary(self):
        """Get summary of test results"""
        if not self.results:
            return None
        
        duration = self.end_time - self.start_time if self.end_time else None
        
        summary = {
            'total': self.results.testsRun,
            'failed': len(self.results.failures),
            'errors': len(self.results.errors),
            'skipped': len(self.results.skipped),
            'expected_failures': len(self.results.expectedFailures),
            'unexpected_successes': len(self.results.unexpectedSuccesses),
            'successful': self.results.testsRun - len(self.results.failures) - len(self.results.errors),
            'duration': duration.total_seconds() if duration else 0,
            'start_time': self.start_time,
            'end_time': self.end_time,
        }
        
        return summary
    
    def print_detailed_report(self):
        """Print detailed test report"""
        summary = self.get_summary()
        if not summary:
            print("No test results available")
            return
        
        print("\n" + "="*80)
        print("DOMAIN LAYER UNIT TESTS - DETAILED REPORT")
        print("="*80)
        
        # Summary
        print(f"\n📊 SUMMARY:")
        print(f"  Total tests run:      {summary['total']}")
        print(f"  Successful:           {summary['successful']}")
        print(f"  Failed:               {summary['failed']}")
        print(f"  Errors:               {summary['errors']}")
        print(f"  Skipped:              {summary['skipped']}")
        print(f"  Duration:             {summary['duration']:.3f} seconds")
        print(f"  Start time:           {summary['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  End time:             {summary['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Success rate
        if summary['total'] > 0:
            success_rate = (summary['successful'] / summary['total']) * 100
            print(f"  Success rate:         {success_rate:.1f}%")
        
        # Test categories
        print(f"\n🧪 TEST CATEGORIES:")
        print(f"  • TestParkingLot      - Parking lot entity tests")
        print(f"  • TestVehicle         - Vehicle entity tests")
        print(f"  • TestParkingSession  - Parking session entity tests")
        print(f"  • TestValueObjects    - Value object tests")
        
        # Failed tests details
        if self.results.failures or self.results.errors:
            print(f"\n❌ FAILURES AND ERRORS:")
            
            for i, (test, traceback) in enumerate(self.results.failures, 1):
                print(f"\n  Failure {i}: {test.id()}")
                print(f"  {traceback.splitlines()[-1]}")
            
            for i, (test, traceback) in enumerate(self.results.errors, 1):
                print(f"\n  Error {i}: {test.id()}")
                print(f"  {traceback.splitlines()[-1]}")
        
        # Skipped tests
        if self.results.skipped:
            print(f"\n⚠️  SKIPPED TESTS:")
            for i, (test, reason) in enumerate(self.results.skipped, 1):
                print(f"  {i}. {test.id()}: {reason}")
        
        print("\n" + "="*80)
        
        # Overall status
        if summary['failed'] == 0 and summary['errors'] == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print(f"❌ TESTS FAILED: {summary['failed']} failures, {summary['errors']} errors")
        print("="*80 + "\n")
    
    def export_results(self, format='text', filename=None):
        """Export test results to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"test_results_{timestamp}.{format}"
        
        summary = self.get_summary()
        
        if format.lower() == 'text':
            with open(filename, 'w') as f:
                f.write(f"Test Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*60}\n")
                f.write(f"Total tests: {summary['total']}\n")
                f.write(f"Successful:  {summary['successful']}\n")
                f.write(f"Failed:      {summary['failed']}\n")
                f.write(f"Errors:      {summary['errors']}\n")
                f.write(f"Duration:    {summary['duration']:.3f} seconds\n")
                f.write(f"{'='*60}\n")
            
            print(f"Results exported to: {filename}")
        
        elif format.lower() == 'json':
            import json
            results_data = {
                'timestamp': datetime.now().isoformat(),
                'summary': summary,
                'failures': [str(test) for test, _ in self.results.failures] if self.results.failures else [],
                'errors': [str(test) for test, _ in self.results.errors] if self.results.errors else [],
            }
            
            with open(filename, 'w') as f:
                json.dump(results_data, f, indent=2, default=str)
            
            print(f"Results exported to: {filename}")
        
        else:
            print(f"Unsupported format: {format}")


def load_test_suite():
    """Load all test cases from the module"""
    # Import test cases from the current module
    from domain_unit_tests import (
        TestParkingLot,
        TestVehicle,
        TestParkingSession,
        TestValueObjects
    )
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    loader = unittest.TestLoader()
    
    suite.addTests(loader.loadTestsFromTestCase(TestParkingLot))
    suite.addTests(loader.loadTestsFromTestCase(TestVehicle))
    suite.addTests(loader.loadTestsFromTestCase(TestParkingSession))
    suite.addTests(loader.loadTestsFromTestCase(TestValueObjects))
    
    return suite


def run_specific_tests(test_names):
    """Run specific test methods"""
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    # Import test cases
    from domain_unit_tests import (
        TestParkingLot,
        TestVehicle,
        TestParkingSession,
        TestValueObjects
    )
    
    # Map test class names to classes
    test_classes = {
        'TestParkingLot': TestParkingLot,
        'TestVehicle': TestVehicle,
        'TestParkingSession': TestParkingSession,
        'TestValueObjects': TestValueObjects
    }
    
    for test_name in test_names:
        if '.' in test_name:
            # Specific test method (TestClass.test_method)
            parts = test_name.split('.')
            if len(parts) == 2:
                class_name, method_name = parts
                if class_name in test_classes:
                    test_class = test_classes[class_name]
                    suite.addTest(test_class(method_name))
                else:
                    print(f"Warning: Unknown test class: {class_name}")
            else:
                print(f"Warning: Invalid test format: {test_name}. Use 'ClassName.methodName'")
        else:
            # Whole test class
            if test_name in test_classes:
                suite.addTests(loader.loadTestsFromTestCase(test_classes[test_name]))
            else:
                print(f"Warning: Unknown test class: {test_name}")
    
    return suite


def main():
    """Main function to run tests"""
    parser = argparse.ArgumentParser(
        description='Run domain layer unit tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all tests
  %(prog)s -v 1                     # Run with minimal verbosity
  %(prog)s -f                       # Stop on first failure
  %(prog)s -t TestParkingLot        # Run only ParkingLot tests
  %(prog)s -t TestVehicle.test_vehicle_creation  # Run specific test
  %(prog)s -t TestParkingLot -t TestVehicle  # Run multiple test classes
  %(prog)s --export json            # Export results to JSON
        """
    )
    
    parser.add_argument(
        '-v', '--verbosity',
        type=int,
        choices=[0, 1, 2],
        default=2,
        help='Verbosity level (0=quiet, 1=normal, 2=verbose)'
    )
    
    parser.add_argument(
        '-f', '--failfast',
        action='store_true',
        help='Stop on first failure'
    )
    
    parser.add_argument(
        '-b', '--no-buffer',
        action='store_false',
        dest='buffer',
        default=True,
        help='Disable output buffering'
    )
    
    parser.add_argument(
        '-t', '--test',
        action='append',
        dest='tests',
        help='Run specific test(s). Format: ClassName or ClassName.methodName'
    )
    
    parser.add_argument(
        '--export',
        choices=['text', 'json'],
        help='Export results to file'
    )
    
    parser.add_argument(
        '--output',
        help='Output file name for exported results'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available tests'
    )
    
    args = parser.parse_args()
    
    # List available tests
    if args.list:
        print("Available test classes:")
        print("  TestParkingLot")
        print("  TestVehicle")
        print("  TestParkingSession")
        print("  TestValueObjects")
        print("\nAvailable test methods:")
        
        test_cases = [
            ('TestParkingLot', [
                'test_parking_lot_creation',
                'test_occupancy_calculation',
                'test_find_available_slot'
            ]),
            ('TestVehicle', [
                'test_vehicle_creation',
                'test_vehicle_validation'
            ]),
            ('TestParkingSession', [
                'test_parking_session_creation',
                'test_charge_calculation_edge_cases'
            ]),
            ('TestValueObjects', [
                'test_money_value_object',
                'test_address_value_object',
                'test_time_range_value_object'
            ])
        ]
        
        for class_name, methods in test_cases:
            print(f"\n  {class_name}:")
            for method in methods:
                print(f"    • {method}")
        return 0
    
    try:
        # Create test suite
        if args.tests:
            test_suite = run_specific_tests(args.tests)
            print(f"Running specific tests: {', '.join(args.tests)}")
        else:
            test_suite = load_test_suite()
            print("Running all domain layer unit tests...")
        
        # Create and configure test runner
        runner = TestRunner(
            verbosity=args.verbosity,
            failfast=args.failfast,
            buffer=args.buffer
        )
        
        # Run tests
        results = runner.run_tests(test_suite)
        
        # Print detailed report
        runner.print_detailed_report()
        
        # Export results if requested
        if args.export:
            runner.export_results(format=args.export, filename=args.output)
        
        # Return appropriate exit code
        if results.failures or results.errors:
            return 1
        return 0
        
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure the test module is in the same directory or Python path.")
        return 2
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    # First, let's ensure the test module is available
    # If running from a different directory, we need to import it properly
    try:
        # Try to import the tests module
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import domain_unit_tests
    except ImportError:
        print("Note: Running tests directly from the test file...")
        # We'll use exec to load the test code
        with open(__file__.replace('test_runner.py', 'domain_unit_tests.py'), 'r') as f:
            exec(f.read(), globals())
    
    sys.exit(main())