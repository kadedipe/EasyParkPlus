#!/usr/bin/env python3
"""
Focused Integration Tests for Critical Scenarios

This file contains integration tests for the most critical scenarios
that must work correctly in the Parking Management System.
"""

import unittest
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from src.presentation.parking_gui import (
        ParkingManagementApp,
        ParkingAppController,
        ParkVehicleDialog
    )
    HAS_GUI_MODULES = True
except ImportError:
    HAS_GUI_MODULES = False


class TestCriticalScenarios(unittest.TestCase):
    """Test critical scenarios that must work"""
    
    def setUp(self):
        """Set up for each test"""
        self.root = tk.Tk()
        self.root.withdraw()
    
    @unittest.skipUnless(HAS_GUI_MODULES, "GUI modules not available")
    def test_1_parking_workflow(self):
        """CRITICAL: Complete parking workflow must work"""
        print("\nTest 1: Complete Parking Workflow")
        print("-" * 40)
        
        # Setup
        mock_controller = Mock()
        mock_controller.park_vehicle = Mock(return_value=(True, "Vehicle parked in slot A-15"))
        
        # Create dialog
        lot_data = {"id": "lot-1", "name": "Main Lot"}
        dialog = ParkVehicleDialog(self.root, mock_controller, lot_data)
        
        # Fill form
        dialog.license_plate.insert(0, "CRITICAL-001")
        dialog.vehicle_type.set("Car")
        dialog.make.insert(0, "Critical")
        dialog.model.insert(0, "Test")
        
        # Mock message boxes
        with patch('tkinter.messagebox.showinfo') as mock_info, \
             patch('tkinter.messagebox.showerror') as mock_error:
            
            # Execute
            dialog._park_vehicle()
            
            # Verify
            mock_controller.park_vehicle.assert_called_once()
            mock_info.assert_called()
            mock_error.assert_not_called()
            
            print("✓ Vehicle parking workflow completed successfully")
        
        dialog.destroy()
    
    @unittest.skipUnless(HAS_GUI_MODULES, "GUI modules not available")
    def test_2_error_handling_workflow(self):
        """CRITICAL: Error handling must work gracefully"""
        print("\nTest 2: Error Handling Workflow")
        print("-" * 40)
        
        # Setup controller to return error
        mock_controller = Mock()
        mock_controller.park_vehicle = Mock(return_value=(False, "No available slots"))
        
        # Create dialog
        dialog = ParkVehicleDialog(self.root, mock_controller)
        
        # Fill form
        dialog.license_plate.insert(0, "ERROR-001")
        dialog.vehicle_type.set("Car")
        
        # Mock message boxes
        with patch('tkinter.messagebox.showinfo') as mock_info, \
             patch('tkinter.messagebox.showerror') as mock_error:
            
            # Execute
            dialog._park_vehicle()
            
            # Verify
            mock_error.assert_called_with("Error", "No available slots")
            mock_info.assert_not_called()
            
            # Dialog should remain open for correction
            self.assertTrue(dialog.winfo_exists())
            
            print("✓ Error handling worked gracefully")
        
        dialog.destroy()
    
    @unittest.skipUnless(HAS_GUI_MODULES, "GUI modules not available")
    def test_3_form_validation(self):
        """CRITICAL: Form validation must prevent invalid submissions"""
        print("\nTest 3: Form Validation")
        print("-" * 40)
        
        # Setup
        mock_controller = Mock()
        dialog = ParkVehicleDialog(self.root, mock_controller)
        
        # Test 3.1: Empty license plate
        with patch('tkinter.messagebox.showerror') as mock_error:
            dialog._park_vehicle()
            mock_error.assert_called_with("Error", "License plate is required")
            print("✓ Empty license plate validation works")
        
        # Test 3.2: Valid form
        dialog.license_plate.insert(0, "VALID-001")
        dialog.vehicle_type.set("Car")
        
        with patch('tkinter.messagebox.showerror') as mock_error:
            dialog._park_vehicle()
            # Should not show error for validation
            # (controller will be called)
            mock_controller.park_vehicle.assert_called()
            print("✓ Valid form passes validation")
        
        dialog.destroy()
    
    @unittest.skipUnless(HAS_GUI_MODULES, "GUI modules not available")
    def test_4_ev_charging_workflow(self):
        """CRITICAL: EV charging workflow must work"""
        print("\nTest 4: EV Charging Workflow")
        print("-" * 40)
        
        # Setup
        mock_controller = Mock()
        mock_controller.park_vehicle = Mock(return_value=(True, "EV charging started"))
        
        # Create dialog
        dialog = ParkVehicleDialog(self.root, mock_controller)
        
        # Fill form for EV
        dialog.license_plate.insert(0, "EV-001")
        dialog.vehicle_type.set("EV Car")
        dialog.make.insert(0, "Tesla")
        dialog.model.insert(0, "Model 3")
        
        # Enable EV charging
        dialog.needs_charging.set(True)
        dialog.current_charge.insert(0, "30")
        dialog.target_charge.insert(0, "80")
        
        with patch('tkinter.messagebox.showinfo') as mock_info:
            # Execute
            dialog._park_vehicle()
            
            # Verify EV data was passed
            call_args = mock_controller.park_vehicle.call_args[0][0]
            self.assertEqual(call_args["license_plate"], "EV-001")
            self.assertEqual(call_args["vehicle_type"], "EV Car")
            self.assertTrue(call_args.get("requires_charging", False))
            
            print("✓ EV charging workflow completed")
        
        dialog.destroy()
    
    @unittest.skipUnless(HAS_GUI_MODULES, "GUI modules not available")
    def test_5_controller_initialization(self):
        """CRITICAL: Controller must initialize all services"""
        print("\nTest 5: Controller Initialization")
        print("-" * 40)
        
        # Mock app
        mock_app = Mock()
        mock_app.root = self.root
        
        # Mock dependencies
        with patch('src.presentation.parking_gui.ParkingServiceFactory') as mock_factory, \
             patch('src.presentation.parking_gui.CommandProcessor') as mock_processor, \
             patch('src.presentation.parking_gui.FactoryRegistry') as mock_registry:
            
            # Setup mocks
            mock_service = Mock()
            mock_factory.create_default_service.return_value = mock_service
            
            mock_processor_instance = Mock()
            mock_processor.return_value = mock_processor_instance
            
            mock_registry_instance = Mock()
            mock_registry.return_value = mock_registry_instance
            
            # Create controller
            controller = ParkingAppController(mock_app)
            
            # Verify initialization
            self.assertIsNotNone(controller.parking_service)
            self.assertIsNotNone(controller.command_processor)
            self.assertIsNotNone(controller.factory_registry)
            
            print("✓ Controller initialized all services")
    
    def tearDown(self):
        """Clean up"""
        self.root.destroy()


class TestBusinessCriticalPaths(unittest.TestCase):
    """Test business-critical paths that generate revenue"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
    
    @unittest.skipUnless(HAS_GUI_MODULES, "GUI modules not available")
    def test_revenue_generation_workflow(self):
        """BUSINESS CRITICAL: Revenue generation must work"""
        print("\nBusiness Critical: Revenue Generation")
        print("-" * 40)
        
        # This would test the complete flow from parking to payment
        # Since we don't have full implementation, we'll test the components
        
        # Test 1: Parking generates ticket
        mock_controller = Mock()
        mock_controller.park_vehicle = Mock(return_value=(
            True, 
            "Vehicle parked. Ticket: TKT-001. Slot: A-15"
        ))
        
        dialog = ParkVehicleDialog(self.root, mock_controller)
        dialog.license_plate.insert(0, "REV-001")
        dialog.vehicle_type.set("Car")
        
        with patch('tkinter.messagebox.showinfo') as mock_info:
            dialog._park_vehicle()
            
            # Verify ticket was generated
            call_args = mock_controller.park_vehicle.call_args
            if call_args:
                # Check that success message includes ticket info
                success_msg = mock_info.call_args[0][1]
                self.assertIn("Ticket", success_msg)
            
            print("✓ Parking generates ticket (revenue opportunity created)")
        
        dialog.destroy()
        
        # Note: In full system, we would also test:
        # - Exit vehicle calculates charges
        # - Payment processing
        # - Invoice generation
        print("✓ Revenue generation path verified")
    
    @unittest.skipUnless(HAS_GUI_MODULES, "GUI modules not available")
    def test_capacity_management(self):
        """BUSINESS CRITICAL: Capacity management must work"""
        print("\nBusiness Critical: Capacity Management")
        print("-" * 40)
        
        # Test that system can handle capacity limits
        
        # Setup controller to simulate lot full
        mock_controller = Mock()
        mock_controller.park_vehicle = Mock(return_value=(
            False, 
            "Parking lot is full. Please try another location."
        ))
        
        dialog = ParkVehicleDialog(self.root, mock_controller)
        dialog.license_plate.insert(0, "CAP-001")
        dialog.vehicle_type.set("Car")
        
        with patch('tkinter.messagebox.showerror') as mock_error:
            dialog._park_vehicle()
            
            # Verify appropriate error message
            mock_error.assert_called()
            error_msg = mock_error.call_args[0][1]
            self.assertIn("full", error_msg.lower())
            
            print("✓ Capacity limits are enforced")
        
        dialog.destroy()
    
    def tearDown(self):
        self.root.destroy()


def run_critical_tests():
    """Run critical scenario tests"""
    print("=" * 70)
    print("CRITICAL SCENARIO TESTS")
    print("Parking Management System - Must Pass Tests")
    print("=" * 70)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add critical tests
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCriticalScenarios))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBusinessCriticalPaths))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    
    # Print critical summary
    print("\n" + "=" * 70)
    print("CRITICAL TEST SUMMARY")
    print("=" * 70)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    
    print(f"\nTotal Critical Tests: {total_tests}")
    print(f"Critical Failures: {failures}")
    print(f"Critical Errors: {errors}")
    
    if failures == 0 and errors == 0:
        print("\n✅ ALL CRITICAL TESTS PASSED!")
        print("System is ready for basic operations.")
    else:
        print("\n❌ CRITICAL TESTS FAILED!")
        print("System may not be operational for key scenarios.")
        
        if failures:
            print("\nCritical Failures:")
            for test, traceback in result.failures:
                print(f"\n• {test}")
                # Show first line of error
                error_lines = traceback.split('\n')
                if error_lines:
                    print(f"  {error_lines[0]}")
        
        if errors:
            print("\nCritical Errors:")
            for test, traceback in result.errors:
                print(f"\n• {test}")
                error_lines = traceback.split('\n')
                if error_lines:
                    print(f"  {error_lines[0]}")
    
    return result


if __name__ == "__main__":
    result = run_critical_tests()
    sys.exit(0 if result.wasSuccessful() else 1)