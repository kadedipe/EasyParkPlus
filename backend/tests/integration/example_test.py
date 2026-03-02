
Now let me create a simple example test file to demonstrate usage:

```python
# This would be saved as tests/integration/example_test.py
"""
Example Integration Test

This file demonstrates how to write integration tests using the
provided utilities and patterns.
"""

import unittest
from unittest.mock import Mock, patch
import tkinter as tk

# Import utilities from our package
from tests.integration import (
    skip_if_missing_module,
    with_temp_database,
    TestDataGenerator,
    IntegrationTestConfig
)


class ExampleIntegrationTest(unittest.TestCase):
    """Example integration test demonstrating best practices"""
    
    def setUp(self):
        """Set up test environment"""
        # Create root window (hidden for testing)
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Generate test data
        self.lot_data = TestDataGenerator.create_parking_lot_data()
        self.vehicle_data = TestDataGenerator.create_vehicle_data()
        
        # Create mock controller
        self.mock_controller = TestDataGenerator.create_mock_controller()
    
    @skip_if_missing_module("src.presentation.parking_gui")
    def test_example_gui_integration(self):
        """Example: Test GUI component integration"""
        # Import inside test to skip if module not available
        from src.presentation.parking_gui import DashboardView
        
        # Create view
        view = DashboardView(self.root, self.mock_controller)
        
        # Test view initialization
        self.assertIsNotNone(view)
        self.assertEqual(view.controller, self.mock_controller)
        
        # Test refresh functionality
        view.refresh()
        
        # Verify data was loaded
        self.assertIsNotNone(view.total_lots_value.cget("text"))
    
    @skip_if_missing_module("src.application.parking_service")
    def test_example_service_integration(self):
        """Example: Test service layer integration"""
        # Mock the service and its dependencies
        with patch('src.application.parking_service.ParkingLotRepository') as mock_repo, \
             patch('src.application.parking_service.MessageBus') as mock_bus:
            
            # Setup mocks
            mock_repo_instance = Mock()
            mock_repo.return_value = mock_repo_instance
            
            mock_bus_instance = Mock()
            mock_bus.return_value = mock_bus_instance
            
            # Import and create service
            from src.application.parking_service import ParkingService
            service = ParkingService()
            
            # Test service initialization
            self.assertIsNotNone(service.repository)
            self.assertIsNotNone(service.message_bus)
    
    @with_temp_database
    def test_example_database_integration(self):
        """Example: Test database integration with temp database"""
        # This test runs with a temporary database
        # The database is created and cleaned up automatically
        
        # Test database operations
        import sqlite3
        from pathlib import Path
        
        # The database path is patched by the decorator
        # In a real test, you would use the actual database module
        db_path = Path("test.db")  # This is patched by the decorator
        
        # Create and test database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create test table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        
        # Insert test data
        cursor.execute("INSERT INTO test_table (name) VALUES (?)", ("Test",))
        conn.commit()
        
        # Query data
        cursor.execute("SELECT * FROM test_table")
        results = cursor.fetchall()
        
        # Verify
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1], "Test")
        
        conn.close()
    
    def test_example_performance(self):
        """Example: Performance integration test"""
        import time
        
        # Start timing
        start_time = time.time()
        
        # Perform operation
        time.sleep(0.1)  # Simulate work
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Verify performance threshold
        max_duration = IntegrationTestConfig.PERFORMANCE_THRESHOLDS["data_loading"]
        self.assertLess(duration, max_duration,
                       f"Operation took {duration:.2f}s, max is {max_duration}s")
    
    def test_example_error_handling(self):
        """Example: Error handling integration test"""
        from tests.integration import IntegrationAssertions
        
        def operation_that_fails():
            raise ValueError("Test error")
        
        def handle_error(error):
            # Verify error was handled correctly
            self.assertIsInstance(error, ValueError)
            self.assertEqual(str(error), "Test error")
        
        # Use custom assertion
        IntegrationAssertions.assertErrorHandled(
            operation_that_fails,
            ValueError,
            handle_error
        )
    
    def tearDown(self):
        """Clean up test environment"""
        self.root.destroy()


if __name__ == "__main__":
    unittest.main()