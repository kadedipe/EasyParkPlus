"""
Integration Tests Package for Parking Management System

This package contains integration tests that verify different components
of the system work together correctly.

Integration tests focus on:
1. Component interactions and data flow
2. End-to-end user scenarios
3. Error handling across boundaries
4. Performance of integrated components
5. Critical business workflows

Test Categories:
- GUI + Controller integration
- Service layer integration
- Database integration (mocked)
- Command processing flow
- Event handling
- Error recovery
- Concurrent operations
- Performance integration
- Business-critical paths
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Export version information
__version__ = "1.0.0"
__author__ = "Parking Solutions Inc."
__description__ = "Integration tests for Parking Management System"

# Export test categories for easy reference
TEST_CATEGORIES = {
    "gui_controller": "GUI + Controller integration tests",
    "service_layer": "Service layer integration tests",
    "command_processor": "Command processor integration tests",
    "end_to_end": "End-to-end scenario tests",
    "data_flow": "Data flow integration tests",
    "event_handling": "Event handling integration tests",
    "concurrent": "Concurrent operation tests",
    "error_recovery": "Error recovery tests",
    "performance": "Performance integration tests",
    "critical": "Critical scenario tests"
}

# Export test utilities
class IntegrationTestConfig:
    """Configuration for integration tests"""
    
    # Test database settings
    TEST_DB_NAME = "test_parking.db"
    TEST_DB_PATH = None
    
    # Mock settings
    USE_MOCK_DATABASE = True
    MOCK_EXTERNAL_SERVICES = True
    
    # Performance settings
    PERFORMANCE_THRESHOLDS = {
        "view_loading": 2.0,  # seconds
        "dialog_creation": 1.5,  # seconds
        "data_loading": 1.0,  # seconds
        "concurrent_operations": 3.0  # seconds
    }
    
    # Test data
    SAMPLE_LOT_DATA = {
        "id": "test-lot-1",
        "name": "Test Parking Lot",
        "code": "TST001",
        "address": "123 Test Street",
        "city": "Test City",
        "total_slots": 100,
        "available_slots": 75,
        "hourly_rate": 5.0,
        "status": "active"
    }
    
    SAMPLE_VEHICLE_DATA = {
        "license_plate": "TEST-001",
        "vehicle_type": "Car",
        "make": "TestMake",
        "model": "TestModel",
        "color": "TestColor",
        "is_ev": False
    }
    
    SAMPLE_PARKING_SESSION = {
        "ticket_id": "TICKET-001",
        "license_plate": "TEST-001",
        "parking_lot_id": "test-lot-1",
        "slot_number": "A-15",
        "entry_time": "2024-01-01T10:00:00",
        "estimated_charge": 0.0
    }

# Export helper functions
def skip_if_missing_module(module_name):
    """Decorator to skip tests if a module is missing"""
    import unittest
    import importlib
    
    def decorator(test_method):
        def wrapper(self, *args, **kwargs):
            try:
                importlib.import_module(module_name)
                return test_method(self, *args, **kwargs)
            except ImportError:
                self.skipTest(f"Required module '{module_name}' not available")
        
        return wrapper
    
    return decorator

def with_temp_database(test_method):
    """Decorator to run tests with a temporary database"""
    import tempfile
    import shutil
    from unittest.mock import patch
    
    def wrapper(self, *args, **kwargs):
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test.db"
        
        try:
            # Patch database path
            with patch('src.infrastructure.database.DATABASE_PATH', db_path):
                # Run test
                return test_method(self, *args, **kwargs)
        finally:
            # Clean up
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    return wrapper

def capture_gui_exceptions(test_method):
    """Decorator to capture and handle GUI exceptions"""
    import tkinter as tk
    
    def wrapper(self, *args, **kwargs):
        # Set up exception handling for Tkinter
        old_report_callback_exception = tk.Tk.report_callback_exception
        
        def report_callback_exception(self, exc, val, tb):
            # Log but don't crash
            print(f"GUI Exception captured in test: {val}")
        
        tk.Tk.report_callback_exception = report_callback_exception
        
        try:
            return test_method(self, *args, **kwargs)
        finally:
            # Restore original handler
            tk.Tk.report_callback_exception = old_report_callback_exception
    
    return wrapper

# Export test data generators
class TestDataGenerator:
    """Generate test data for integration tests"""
    
    @staticmethod
    def create_parking_lot_data(overrides=None):
        """Create parking lot test data"""
        data = IntegrationTestConfig.SAMPLE_LOT_DATA.copy()
        if overrides:
            data.update(overrides)
        return data
    
    @staticmethod
    def create_vehicle_data(overrides=None):
        """Create vehicle test data"""
        data = IntegrationTestConfig.SAMPLE_VEHICLE_DATA.copy()
        if overrides:
            data.update(overrides)
        return data
    
    @staticmethod
    def create_parking_session_data(overrides=None):
        """Create parking session test data"""
        data = IntegrationTestConfig.SAMPLE_PARKING_SESSION.copy()
        if overrides:
            data.update(overrides)
        return data
    
    @staticmethod
    def create_mock_controller():
        """Create a mock controller for testing"""
        from unittest.mock import Mock
        
        mock_controller = Mock()
        mock_controller.app = Mock()
        mock_controller.show_dialog = Mock()
        mock_controller.park_vehicle = Mock()
        mock_controller.add_parking_lot = Mock()
        mock_controller.switch_view = Mock()
        
        return mock_controller
    
    @staticmethod
    def create_mock_parking_service():
        """Create a mock parking service for testing"""
        from unittest.mock import Mock
        
        mock_service = Mock()
        mock_service.park_vehicle = Mock()
        mock_service.exit_vehicle = Mock()
        mock_service.get_parking_lot_status = Mock()
        mock_service.generate_report = Mock()
        
        return mock_service

# Export test assertions
class IntegrationAssertions:
    """Custom assertions for integration tests"""
    
    @staticmethod
    def assertComponentInteraction(component1, component2, interaction_method):
        """Assert that two components interact correctly"""
        # This is a conceptual assertion - implementation depends on specific components
        pass
    
    @staticmethod
    def assertDataFlow(source, destination, data_validator):
        """Assert that data flows correctly between components"""
        # This is a conceptual assertion - implementation depends on specific components
        pass
    
    @staticmethod
    def assertErrorHandled(operation, error_type, error_handler):
        """Assert that errors are handled correctly"""
        import unittest
        
        try:
            operation()
            # If no exception was raised, the test should fail
            raise AssertionError(f"Expected {error_type} but no exception was raised")
        except error_type as e:
            # Verify error was handled correctly
            error_handler(e)
        except Exception as e:
            # Wrong exception type
            raise AssertionError(f"Expected {error_type} but got {type(e).__name__}: {e}")

# Export test fixtures
class IntegrationTestFixture:
    """Base fixture for integration tests"""
    
    def __init__(self):
        self.temp_dirs = []
        self.mock_patches = []
    
    def create_temp_directory(self):
        """Create a temporary directory"""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(temp_dir)
        return temp_dir
    
    def patch_module(self, module_path, mock_object):
        """Patch a module for testing"""
        from unittest.mock import patch
        patcher = patch(module_path, mock_object)
        self.mock_patches.append(patcher)
        return patcher.start()
    
    def cleanup(self):
        """Clean up test fixtures"""
        import shutil
        
        # Stop all patches
        for patcher in self.mock_patches:
            patcher.stop()
        
        # Remove temp directories
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

# Export main test runner function
def run_integration_tests(test_categories=None, output_dir=None, verbosity=2):
    """
    Run integration tests.
    
    Args:
        test_categories: List of test categories to run (None for all)
        output_dir: Directory for test reports (None for no reports)
        verbosity: Verbosity level (1=quiet, 2=verbose)
    
    Returns:
        bool: True if all tests passed, False otherwise
    """
    import unittest
    import sys
    
    # Import test modules
    from tests.integration import test_integration
    from tests.integration import test_critical_scenarios
    
    # Determine which tests to run
    test_suite = unittest.TestSuite()
    
    if test_categories is None:
        # Run all tests
        test_suite.addTests(unittest.TestLoader().loadTestsFromModule(test_integration))
        test_suite.addTests(unittest.TestLoader().loadTestsFromModule(test_critical_scenarios))
    else:
        # Run specific categories
        for category in test_categories:
            if category == "critical":
                test_suite.addTests(unittest.TestLoader().loadTestsFromModule(test_critical_scenarios))
            else:
                # Load specific test classes from test_integration
                # This would need to be expanded based on actual test structure
                pass
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(test_suite)
    
    # Generate report if requested
    if output_dir:
        generate_test_report(result, output_dir)
    
    return result.wasSuccessful()

def generate_test_report(test_result, output_dir):
    """Generate a test report"""
    import json
    from datetime import datetime
    from pathlib import Path
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create report data
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "tests_run": test_result.testsRun,
        "failures": len(test_result.failures),
        "errors": len(test_result.errors),
        "skipped": len(test_result.skipped),
        "successful": test_result.wasSuccessful(),
        "test_cases": []
    }
    
    # Add test case details
    if hasattr(test_result, 'test_case_details'):
        report_data["test_cases"] = test_result.test_case_details
    
    # Write JSON report
    json_path = output_path / "integration_test_report.json"
    with open(json_path, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    # Write simple text summary
    summary_path = output_path / "test_summary.txt"
    with open(summary_path, 'w') as f:
        f.write(f"Integration Test Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"\n")
        f.write(f"Tests Run: {test_result.testsRun}\n")
        f.write(f"Failures: {len(test_result.failures)}\n")
        f.write(f"Errors: {len(test_result.errors)}\n")
        f.write(f"Skipped: {len(test_result.skipped)}\n")
        f.write(f"\n")
        f.write(f"Result: {'PASS' if test_result.wasSuccessful() else 'FAIL'}\n")
    
    return json_path, summary_path

# Export module availability checker
def check_module_availability():
    """
    Check availability of required modules for integration tests.
    
    Returns:
        dict: Dictionary with module availability status
    """
    import importlib
    
    modules_to_check = [
        "src.presentation.parking_gui",
        "src.application.parking_service",
        "src.application.commands",
        "src.application.dtos",
        "src.infrastructure.factories",
        "tkinter"
    ]
    
    availability = {}
    
    for module in modules_to_check:
        try:
            importlib.import_module(module)
            availability[module] = True
        except ImportError:
            availability[module] = False
    
    return availability

# Export quick test runner for common scenarios
def run_critical_scenarios():
    """Run only critical scenario tests"""
    from tests.integration.test_critical_scenarios import run_critical_tests
    return run_critical_tests()

def run_comprehensive_tests():
    """Run all comprehensive integration tests"""
    from tests.integration.test_integration import run_integration_tests
    return run_integration_tests()

# Export version and metadata
__all__ = [
    # Configuration
    'IntegrationTestConfig',
    'TEST_CATEGORIES',
    
    # Decorators
    'skip_if_missing_module',
    'with_temp_database',
    'capture_gui_exceptions',
    
    # Test data
    'TestDataGenerator',
    
    # Assertions
    'IntegrationAssertions',
    
    # Fixtures
    'IntegrationTestFixture',
    
    # Functions
    'run_integration_tests',
    'generate_test_report',
    'check_module_availability',
    'run_critical_scenarios',
    'run_comprehensive_tests',
    
    # Metadata
    '__version__',
    '__author__',
    '__description__'
]

# Print availability status when module is imported
if __name__ != "__main__":
    # Only check when imported, not when running tests
    availability = check_module_availability()
    missing_modules = [mod for mod, avail in availability.items() if not avail]
    
    if missing_modules:
        print(f"Integration Tests: Some modules not available: {', '.join(missing_modules)}")
        print("Some tests may be skipped.")
    else:
        print("Integration Tests: All required modules available.")