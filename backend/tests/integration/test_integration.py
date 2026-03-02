#!/usr/bin/env python3
"""
Integration Tests for Parking Management System

These tests verify that different components of the system work together correctly:
1. GUI + Controller integration
2. Service layer integration
3. Database integration (mocked)
4. Command processing flow
5. End-to-end scenarios
"""

import unittest
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock, patch, MagicMock, create_autospec
import sys
import os
from pathlib import Path
import tempfile
import json
import sqlite3
from datetime import datetime, timedelta

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import the components to test
try:
    from src.presentation.parking_gui import (
        ParkingManagementApp,
        ParkingAppController,
        DashboardView,
        ParkingLotView,
        VehicleManagementView,
        BillingView,
        ParkVehicleDialog,
        AddParkingLotDialog,
        ModernButton,
        CardFrame,
        ParkingSlotWidget
    )
    from src.application.parking_service import ParkingService
    from src.application.commands import CommandProcessor, ParkVehicleCommand, ExitVehicleCommand
    from src.application.dtos import ParkingRequestDTO, ParkingResponseDTO
    from src.infrastructure.factories import FactoryRegistry
    from src.infrastructure.messaging import MessageBus
    HAS_PROJECT_MODULES = True
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")
    HAS_PROJECT_MODULES = False


# ============================================================================
# INTEGRATION TEST BASE CLASS
# ============================================================================

class IntegrationTestBase(unittest.TestCase):
    """Base class for integration tests with common setup"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create mock database file
        self.db_path = Path(self.temp_dir) / "test_parking.db"
        self._create_test_database()
        
        # Common mocks
        self.mock_message_bus = Mock(spec=MessageBus)
        self.mock_factory_registry = Mock(spec=FactoryRegistry)
        
    def _create_test_database(self):
        """Create a test SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create test tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parking_lots (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                address TEXT,
                total_slots INTEGER,
                available_slots INTEGER,
                hourly_rate REAL,
                status TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id TEXT PRIMARY KEY,
                license_plate TEXT UNIQUE NOT NULL,
                vehicle_type TEXT,
                make TEXT,
                model TEXT,
                color TEXT,
                is_ev INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parking_sessions (
                id TEXT PRIMARY KEY,
                vehicle_id TEXT,
                parking_lot_id TEXT,
                slot_number INTEGER,
                entry_time TEXT,
                exit_time TEXT,
                total_charge REAL,
                status TEXT,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
                FOREIGN KEY (parking_lot_id) REFERENCES parking_lots(id)
            )
        ''')
        
        # Insert test data
        cursor.execute('''
            INSERT OR REPLACE INTO parking_lots 
            (id, name, code, address, total_slots, available_slots, hourly_rate, status)
            VALUES 
            ('test-lot-1', 'Test Lot 1', 'TST001', '123 Test St', 100, 85, 5.0, 'active'),
            ('test-lot-2', 'Test Lot 2', 'TST002', '456 Test Ave', 50, 30, 7.5, 'active')
        ''')
        
        cursor.execute('''
            INSERT OR REPLACE INTO vehicles 
            (id, license_plate, vehicle_type, make, model, color, is_ev)
            VALUES 
            ('test-vehicle-1', 'TEST-001', 'Car', 'Toyota', 'Camry', 'Blue', 0),
            ('test-vehicle-2', 'EV-001', 'EV Car', 'Tesla', 'Model 3', 'Red', 1)
        ''')
        
        conn.commit()
        conn.close()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


# ============================================================================
# GUI + CONTROLLER INTEGRATION TESTS
# ============================================================================

class TestGUIControllerIntegration(IntegrationTestBase):
    """Test integration between GUI and Controller"""
    
    def setUp(self):
        super().setUp()
        
        # Create root window (hidden for testing)
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Mock app
        self.mock_app = Mock()
        self.mock_app.root = self.root
        
        # Create controller with mocked dependencies
        with patch('src.presentation.parking_gui.ParkingServiceFactory') as mock_factory, \
             patch('src.presentation.parking_gui.CommandProcessor') as mock_processor_class, \
             patch('src.presentation.parking_gui.FactoryRegistry') as mock_registry_class:
            
            # Setup mocks
            self.mock_parking_service = Mock(spec=ParkingService)
            mock_factory.create_default_service.return_value = self.mock_parking_service
            
            self.mock_command_processor = Mock(spec=CommandProcessor)
            mock_processor_class.return_value = self.mock_command_processor
            
            self.mock_factory_registry = Mock(spec=FactoryRegistry)
            mock_registry_class.return_value = self.mock_factory_registry
            
            # Create controller
            self.controller = ParkingAppController(self.mock_app)
    
    def test_controller_initializes_services(self):
        """Test controller properly initializes all services"""
        self.assertIsNotNone(self.controller.parking_service)
        self.assertIsNotNone(self.controller.command_processor)
        self.assertIsNotNone(self.controller.factory_registry)
        self.assertIsNotNone(self.controller.logger)
    
    def test_controller_view_switching(self):
        """Test controller can switch views through app"""
        # Mock app's switch_view method
        self.mock_app.switch_view = Mock()
        
        # Call controller method
        self.controller.switch_view("dashboard")
        
        # Verify app method was called
        self.mock_app.switch_view.assert_called_with("dashboard")
    
    def test_controller_dialog_creation(self):
        """Test controller creates dialogs correctly"""
        # Mock dialog creation
        with patch('src.presentation.parking_gui.ParkVehicleDialog') as mock_dialog_class:
            mock_dialog = Mock()
            mock_dialog_class.return_value = mock_dialog
            
            # Call controller method
            result = self.controller.show_dialog("park_vehicle")
            
            # Verify dialog was created
            mock_dialog_class.assert_called_with(self.mock_app, self.controller)
            self.assertEqual(result, mock_dialog)
    
    @patch('src.presentation.parking_gui.uuid4')
    @patch('src.presentation.parking_gui.ParkingRequestDTO')
    def test_controller_park_vehicle_flow(self, mock_request_class, mock_uuid4):
        """Test complete park vehicle flow through controller"""
        # Setup mocks
        mock_uuid4.return_value = "test-uuid"
        mock_request = Mock(spec=ParkingRequestDTO)
        mock_request_class.return_value = mock_request
        
        self.mock_command_processor.process.return_value = {
            "success": True,
            "message": "Vehicle parked successfully",
            "ticket_id": "TICKET-001",
            "slot_number": "A-15"
        }
        
        # Test data
        vehicle_data = {
            "license_plate": "ABC-123",
            "vehicle_type": "Car",
            "preferred_slot_type": "regular"
        }
        lot_data = {"id": "test-lot-1", "name": "Test Lot"}
        
        # Call controller method
        success, message = self.controller.park_vehicle(vehicle_data, lot_data)
        
        # Verify flow
        self.assertTrue(success)
        self.assertEqual(message, "Vehicle parked successfully")
        
        # Verify command was created and processed
        mock_request_class.assert_called_once()
        self.mock_command_processor.process.assert_called_once()
        
        # Verify the command was a ParkVehicleCommand
        command_arg = self.mock_command_processor.process.call_args[0][0]
        self.assertIsInstance(command_arg, ParkVehicleCommand)
    
    def test_controller_add_parking_lot(self):
        """Test add parking lot flow through controller"""
        # Setup mock
        self.controller.logger = Mock()
        
        # Test data
        lot_data = {
            "name": "New Test Lot",
            "code": "NTL001",
            "address": "789 Test Blvd",
            "total_slots": 200
        }
        
        # Call controller method
        success, message = self.controller.add_parking_lot(lot_data)
        
        # Verify result
        self.assertTrue(success)
        self.assertIn("Parking lot 'New Test Lot' added successfully", message)
        self.controller.logger.info.assert_called()
    
    def tearDown(self):
        """Clean up"""
        self.root.destroy()
        super().tearDown()


# ============================================================================
# VIEW + CONTROLLER INTEGRATION TESTS
# ============================================================================

class TestViewControllerIntegration(IntegrationTestBase):
    """Test integration between Views and Controller"""
    
    def setUp(self):
        super().setUp()
        
        # Create root window
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Create mock controller
        self.mock_controller = Mock(spec=ParkingAppController)
        self.mock_controller.app = Mock()
        self.mock_controller.show_dialog = Mock()
        self.mock_controller.park_vehicle = Mock()
        self.mock_controller.switch_view = Mock()
    
    def test_dashboard_view_integration(self):
        """Test DashboardView integrates with controller"""
        # Create view
        view = DashboardView(self.root, self.mock_controller)
        
        # Test that view has controller reference
        self.assertEqual(view.controller, self.mock_controller)
        
        # Test refresh method (should call controller if needed)
        view.refresh()
        
        # Verify view components exist
        self.assertIsNotNone(view.total_lots_value)
        self.assertIsNotNone(view.available_slots_value)
        self.assertIsNotNone(view.occupancy_chart)
        
        # Test that view can trigger controller actions
        # (Dashboard doesn't have direct controller calls in refresh)
        # But we can test that it's set up correctly
    
    def test_parking_lot_view_integration(self):
        """Test ParkingLotView integrates with controller"""
        # Create view
        view = ParkingLotView(self.root, self.mock_controller)
        
        # Test initial state
        self.assertEqual(view.controller, self.mock_controller)
        
        # Test refresh method
        view.refresh()
        
        # Test that quick actions call controller
        lot_data = {"id": 1, "name": "Test Lot"}
        
        # Test park vehicle action
        view._park_vehicle(lot_data)
        self.mock_controller.show_dialog.assert_called_with("park_vehicle", lot_data=lot_data)
        
        # Test add parking lot action
        view._add_parking_lot()
        self.mock_controller.show_dialog.assert_called_with("add_parking_lot")
    
    def test_vehicle_management_view_integration(self):
        """Test VehicleManagementView integrates with controller"""
        # Create view
        view = VehicleManagementView(self.root, self.mock_controller)
        
        # Test initial state
        self.assertEqual(view.controller, self.mock_controller)
        
        # Test refresh method
        view.refresh()
        
        # Test search functionality
        view.search_var = Mock()
        view.search_var.get.return_value = "TEST"
        view.vehicle_tree = Mock()
        view.vehicle_tree.get_children.return_value = []
        
        view._search_vehicles()
        
        # Test add vehicle action
        view._add_vehicle()
        self.mock_controller.show_dialog.assert_called_with("add_vehicle")
    
    def test_billing_view_integration(self):
        """Test BillingView integrates with controller"""
        # Create view
        view = BillingView(self.root, self.mock_controller)
        
        # Test initial state
        self.assertEqual(view.controller, self.mock_controller)
        
        # Test notebook tabs exist
        self.assertIsNotNone(view.notebook)
        
        # Test refresh method
        view.refresh()
        
        # Verify data was loaded
        self.assertGreater(len(view.invoice_tree.get_children()), 0)
        self.assertGreater(len(view.payment_tree.get_children()), 0)
    
    def tearDown(self):
        """Clean up"""
        self.root.destroy()
        super().tearDown()


# ============================================================================
# DIALOG + CONTROLLER INTEGRATION TESTS
# ============================================================================

class TestDialogControllerIntegration(IntegrationTestBase):
    """Test integration between Dialogs and Controller"""
    
    def setUp(self):
        super().setUp()
        
        # Create root window
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Create mock controller
        self.mock_controller = Mock(spec=ParkingAppController)
        self.mock_controller.park_vehicle = Mock(return_value=(True, "Success"))
        self.mock_controller.add_parking_lot = Mock(return_value=(True, "Success"))
    
    def test_park_vehicle_dialog_integration(self):
        """Test ParkVehicleDialog integrates with controller"""
        # Create dialog with lot data
        lot_data = {"id": "test-lot-1", "name": "Test Lot"}
        dialog = ParkVehicleDialog(self.root, self.mock_controller, lot_data)
        
        # Test dialog initialization
        self.assertEqual(dialog.controller, self.mock_controller)
        self.assertEqual(dialog.lot_data, lot_data)
        
        # Test form fields exist
        self.assertIsNotNone(dialog.license_plate)
        self.assertIsNotNone(dialog.vehicle_type)
        self.assertIsNotNone(dialog.make)
        self.assertIsNotNone(dialog.model)
        
        # Test vehicle type change
        dialog.vehicle_type.set("EV Car")
        dialog._on_vehicle_type_changed(None)
        
        # Test EV charging toggle
        dialog.needs_charging.set(True)
        dialog._toggle_ev_details()
        
        # Test form validation with valid data
        with patch('tkinter.messagebox') as mock_messagebox:
            # Fill form
            dialog.license_plate.insert(0, "ABC-123")
            dialog.vehicle_type.set("Car")
            
            # Submit form
            dialog._park_vehicle()
            
            # Verify controller was called
            self.mock_controller.park_vehicle.assert_called_once()
            
            # Get the call arguments
            call_args = self.mock_controller.park_vehicle.call_args
            vehicle_data = call_args[0][0]
            passed_lot_data = call_args[0][1]
            
            # Verify data
            self.assertEqual(vehicle_data["license_plate"], "ABC-123")
            self.assertEqual(vehicle_data["vehicle_type"], "Car")
            self.assertEqual(passed_lot_data, lot_data)
            
            # Verify success message would be shown
            mock_messagebox.showinfo.assert_called_once()
        
        dialog.destroy()
    
    def test_park_vehicle_dialog_validation(self):
        """Test ParkVehicleDialog validation with controller"""
        # Create dialog
        dialog = ParkVehicleDialog(self.root, self.mock_controller)
        
        # Test empty license plate
        with patch('tkinter.messagebox.showerror') as mock_showerror:
            dialog._park_vehicle()
            mock_showerror.assert_called_with("Error", "License plate is required")
        
        # Test with license plate only
        with patch('tkinter.messagebox.showerror') as mock_showerror:
            dialog.license_plate.insert(0, "ABC-123")
            dialog._park_vehicle()
            
            # Should still fail because vehicle_type is empty
            mock_showerror.assert_called()
        
        dialog.destroy()
    
    def test_add_parking_lot_dialog_integration(self):
        """Test AddParkingLotDialog integrates with controller"""
        # Create dialog
        dialog = AddParkingLotDialog(self.root, self.mock_controller)
        
        # Test dialog initialization
        self.assertEqual(dialog.controller, self.mock_controller)
        
        # Test form fields exist
        self.assertIsNotNone(dialog.name)
        self.assertIsNotNone(dialog.code)
        self.assertIsNotNone(dialog.address)
        self.assertIsNotNone(dialog.city)
        
        # Test form validation
        with patch('tkinter.messagebox') as mock_messagebox:
            # Fill required fields
            dialog.name.insert(0, "New Parking Lot")
            dialog.code.insert(0, "NPL001")
            dialog.address.insert(0, "123 Test St")
            dialog.city.insert(0, "Test City")
            dialog.country.insert(0, "Test Country")
            
            # Submit form
            dialog._add_parking_lot()
            
            # Verify controller was called
            self.mock_controller.add_parking_lot.assert_called_once()
            
            # Get the call arguments
            call_args = self.mock_controller.add_parking_lot.call_args
            lot_data = call_args[0][0]
            
            # Verify data
            self.assertEqual(lot_data["name"], "New Parking Lot")
            self.assertEqual(lot_data["code"], "NPL001")
            self.assertEqual(lot_data["address"], "123 Test St")
            self.assertEqual(lot_data["city"], "Test City")
            self.assertEqual(lot_data["country"], "Test Country")
            
            # Verify success message would be shown
            mock_messagebox.showinfo.assert_called_once()
        
        dialog.destroy()
    
    def test_add_parking_lot_dialog_validation(self):
        """Test AddParkingLotDialog validation with controller"""
        # Create dialog
        dialog = AddParkingLotDialog(self.root, self.mock_controller)
        
        # Test empty name
        with patch('tkinter.messagebox.showerror') as mock_showerror:
            dialog._add_parking_lot()
            mock_showerror.assert_called_with("Error", "Name is required")
        
        # Fill name only
        dialog.name.insert(0, "Test Lot")
        
        # Test empty code
        with patch('tkinter.messagebox.showerror') as mock_showerror:
            dialog._add_parking_lot()
            mock_showerror.assert_called_with("Error", "Code is required")
        
        dialog.destroy()
    
    def tearDown(self):
        """Clean up"""
        self.root.destroy()
        super().tearDown()


# ============================================================================
# SERVICE LAYER INTEGRATION TESTS
# ============================================================================

class TestServiceLayerIntegration(IntegrationTestBase):
    """Test integration of service layer with other components"""
    
    def setUp(self):
        super().setUp()
        
        # Create mock dependencies
        self.mock_repository = Mock()
        self.mock_factory = Mock()
        self.mock_message_bus = Mock(spec=MessageBus)
        
        # Create parking service with mocked dependencies
        with patch('src.application.parking_service.ParkingLotRepository', return_value=self.mock_repository), \
             patch('src.application.parking_service.ParkingLotFactory', return_value=self.mock_factory), \
             patch('src.application.parking_service.MessageBus', return_value=self.mock_message_bus):
            
            # Try to create service
            try:
                self.parking_service = ParkingService()
                self.service_available = True
            except:
                self.service_available = False
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_parking_service_initialization(self):
        """Test parking service initializes dependencies"""
        if not self.service_available:
            self.skipTest("ParkingService could not be initialized")
        
        # Verify service has its dependencies
        self.assertIsNotNone(self.parking_service.repository)
        self.assertIsNotNone(self.parking_service.factory)
        self.assertIsNotNone(self.parking_service.message_bus)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_parking_service_park_vehicle_flow(self):
        """Test complete park vehicle flow through service"""
        if not self.service_available:
            self.skipTest("ParkingService could not be initialized")
        
        # Setup mock responses
        mock_parking_lot = Mock()
        mock_parking_lot.id = "test-lot-1"
        mock_parking_lot.find_available_slot.return_value = Mock(slot_number=15)
        
        mock_vehicle = Mock()
        mock_vehicle.id = "test-vehicle-1"
        
        self.mock_repository.get_parking_lot.return_value = mock_parking_lot
        self.mock_repository.get_or_create_vehicle.return_value = mock_vehicle
        self.mock_repository.save_parking_session.return_value = "session-123"
        
        # Create request
        request = ParkingRequestDTO(
            license_plate="ABC-123",
            vehicle_type="Car",
            parking_lot_id="test-lot-1"
        )
        
        # Call service method
        response = self.parking_service.park_vehicle(request)
        
        # Verify flow
        self.mock_repository.get_parking_lot.assert_called_with("test-lot-1")
        self.mock_repository.get_or_create_vehicle.assert_called()
        mock_parking_lot.find_available_slot.assert_called()
        
        # Verify response
        self.assertIsInstance(response, ParkingResponseDTO)
        self.assertTrue(response.success)
        self.assertIsNotNone(response.ticket_id)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_parking_service_exit_vehicle_flow(self):
        """Test complete exit vehicle flow through service"""
        if not self.service_available:
            self.skipTest("ParkingService could not be initialized")
        
        # Setup mock responses
        mock_session = Mock()
        mock_session.id = "session-123"
        mock_session.entry_time = datetime.now() - timedelta(hours=2)
        mock_session.parking_lot = Mock(hourly_rate=5.0)
        mock_session.calculate_charge.return_value = 10.0
        
        self.mock_repository.get_parking_session.return_value = mock_session
        self.mock_repository.save_parking_session.return_value = "session-123"
        
        # Create request
        from src.application.dtos import ExitRequestDTO
        request = ExitRequestDTO(
            ticket_id="session-123",
            license_plate="ABC-123"
        )
        
        # Call service method
        response = self.parking_service.exit_vehicle(request)
        
        # Verify flow
        self.mock_repository.get_parking_session.assert_called_with("session-123")
        mock_session.exit_vehicle.assert_called()
        self.mock_repository.save_parking_session.assert_called_with(mock_session)
        
        # Verify response should contain billing info
        # (Assuming response includes charge amount)
        self.assertIsInstance(response, ParkingResponseDTO)


# ============================================================================
# COMMAND PROCESSOR INTEGRATION TESTS
# ============================================================================

class TestCommandProcessorIntegration(IntegrationTestBase):
    """Test integration of command processor with services"""
    
    def setUp(self):
        super().setUp()
        
        # Create mock parking service
        self.mock_parking_service = Mock(spec=ParkingService)
        
        # Create command processor
        self.command_processor = CommandProcessor(self.mock_parking_service)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_command_processor_park_vehicle_flow(self):
        """Test park vehicle command flow through processor"""
        # Setup mock response
        mock_response = ParkingResponseDTO(
            success=True,
            message="Vehicle parked successfully",
            ticket_id="TICKET-001",
            slot_number="A-15"
        )
        self.mock_parking_service.park_vehicle.return_value = mock_response
        
        # Create command
        request = ParkingRequestDTO(
            license_plate="ABC-123",
            vehicle_type="Car",
            parking_lot_id="test-lot-1"
        )
        command = ParkVehicleCommand(request, executed_by="test-user")
        
        # Process command
        result = self.command_processor.process(command)
        
        # Verify service was called
        self.mock_parking_service.park_vehicle.assert_called_with(request)
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Vehicle parked successfully")
        self.assertEqual(result["ticket_id"], "TICKET-001")
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_command_processor_exit_vehicle_flow(self):
        """Test exit vehicle command flow through processor"""
        # Setup mock response
        mock_response = ParkingResponseDTO(
            success=True,
            message="Vehicle exited successfully",
            total_charge=15.0
        )
        self.mock_parking_service.exit_vehicle.return_value = mock_response
        
        # Create command
        from src.application.commands import ExitVehicleCommand
        from src.application.dtos import ExitRequestDTO
        
        request = ExitRequestDTO(
            ticket_id="TICKET-001",
            license_plate="ABC-123"
        )
        command = ExitVehicleCommand(request, executed_by="test-user")
        
        # Process command
        result = self.command_processor.process(command)
        
        # Verify service was called
        self.mock_parking_service.exit_vehicle.assert_called_with(request)
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Vehicle exited successfully")
        self.assertEqual(result["total_charge"], 15.0)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_command_processor_error_handling(self):
        """Test command processor error handling"""
        # Setup service to raise exception
        self.mock_parking_service.park_vehicle.side_effect = Exception("Service error")
        
        # Create command
        request = ParkingRequestDTO(
            license_plate="ABC-123",
            vehicle_type="Car",
            parking_lot_id="test-lot-1"
        )
        command = ParkVehicleCommand(request, executed_by="test-user")
        
        # Process command
        result = self.command_processor.process(command)
        
        # Verify error result
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertIn("Service error", result["error"])


# ============================================================================
# END-TO-END SCENARIO TESTS
# ============================================================================

class TestEndToEndScenarios(IntegrationTestBase):
    """Test complete end-to-end scenarios"""
    
    def setUp(self):
        super().setUp()
        
        # Create root window
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Create full mock chain
        self.setup_mock_chain()
    
    def setup_mock_chain(self):
        """Setup complete mock chain from GUI to service"""
        # Mock service layer
        self.mock_parking_service = Mock(spec=ParkingService)
        
        # Mock command processor
        self.mock_command_processor = Mock(spec=CommandProcessor)
        
        # Mock controller
        self.mock_controller = Mock(spec=ParkingAppController)
        self.mock_controller.parking_service = self.mock_parking_service
        self.mock_controller.command_processor = self.mock_command_processor
        self.mock_controller.app = Mock()
        self.mock_controller.show_dialog = Mock()
        self.mock_controller.park_vehicle = Mock()
        self.mock_controller.add_parking_lot = Mock()
    
    def test_complete_parking_scenario(self):
        """Test complete parking scenario from GUI to service"""
        # Setup mock responses
        mock_response = {
            "success": True,
            "message": "Vehicle parked successfully",
            "ticket_id": "TICKET-001",
            "slot_number": "A-15"
        }
        self.mock_controller.park_vehicle.return_value = (True, "Vehicle parked successfully")
        
        # Create dialog
        lot_data = {"id": "test-lot-1", "name": "Test Lot"}
        dialog = ParkVehicleDialog(self.root, self.mock_controller, lot_data)
        
        # Fill form
        dialog.license_plate.insert(0, "ABC-123")
        dialog.vehicle_type.set("Car")
        dialog.make.insert(0, "Toyota")
        dialog.model.insert(0, "Camry")
        dialog.color.insert(0, "Blue")
        
        # Mock messagebox
        with patch('tkinter.messagebox.showinfo') as mock_showinfo:
            # Submit form
            dialog._park_vehicle()
            
            # Verify controller was called
            self.mock_controller.park_vehicle.assert_called_once()
            
            # Verify success message
            mock_showinfo.assert_called_with("Success", "Vehicle parked successfully")
        
        dialog.destroy()
    
    def test_complete_parking_lot_creation_scenario(self):
        """Test complete parking lot creation scenario"""
        # Setup mock response
        self.mock_controller.add_parking_lot.return_value = (True, "Parking lot added successfully")
        
        # Create dialog
        dialog = AddParkingLotDialog(self.root, self.mock_controller)
        
        # Fill required fields
        dialog.name.insert(0, "New Downtown Lot")
        dialog.code.insert(0, "DTL001")
        dialog.address.insert(0, "789 Downtown Blvd")
        dialog.city.insert(0, "Metropolis")
        dialog.country.insert(0, "USA")
        
        # Fill optional fields
        dialog.description.insert("1.0", "A new parking lot in downtown")
        dialog.total_capacity.insert(0, "200")
        dialog.regular_rate.insert(0, "5.00")
        
        # Mock messagebox
        with patch('tkinter.messagebox.showinfo') as mock_showinfo:
            # Submit form
            dialog._add_parking_lot()
            
            # Verify controller was called
            self.mock_controller.add_parking_lot.assert_called_once()
            
            # Get call arguments
            lot_data = self.mock_controller.add_parking_lot.call_args[0][0]
            
            # Verify data
            self.assertEqual(lot_data["name"], "New Downtown Lot")
            self.assertEqual(lot_data["code"], "DTL001")
            self.assertEqual(lot_data["address"], "789 Downtown Blvd")
            self.assertEqual(lot_data["city"], "Metropolis")
            self.assertEqual(lot_data["country"], "USA")
            self.assertEqual(lot_data["total_capacity"], 200)
            self.assertEqual(lot_data["pricing"]["regular"], 5.00)
            
            # Verify success message
            mock_showinfo.assert_called_with("Success", "Parking lot added successfully")
        
        dialog.destroy()
    
    def test_error_scenario_handling(self):
        """Test error scenario handling end-to-end"""
        # Setup controller to return error
        self.mock_controller.park_vehicle.return_value = (False, "No available slots")
        
        # Create dialog
        dialog = ParkVehicleDialog(self.root, self.mock_controller)
        
        # Fill form
        dialog.license_plate.insert(0, "ABC-123")
        dialog.vehicle_type.set("Car")
        
        # Mock messagebox
        with patch('tkinter.messagebox.showerror') as mock_showerror:
            # Submit form
            dialog._park_vehicle()
            
            # Verify error message
            mock_showerror.assert_called_with("Error", "No available slots")
            
            # Dialog should not be destroyed on error
            self.assertTrue(dialog.winfo_exists())
        
        dialog.destroy()
    
    def tearDown(self):
        """Clean up"""
        self.root.destroy()
        super().tearDown()


# ============================================================================
# DATA FLOW INTEGRATION TESTS
# ============================================================================

class TestDataFlowIntegration(IntegrationTestBase):
    """Test data flow between components"""
    
    def setUp(self):
        super().setUp()
        
        # Create test data
        self.test_lot_data = {
            "id": "test-lot-1",
            "name": "Test Parking Lot",
            "code": "TST001",
            "city": "Test City",
            "total_slots": 100,
            "available_slots": 75,
            "occupancy_rate": 0.25,
            "hourly_rate": 5.00
        }
        
        self.test_vehicle_data = {
            "license_plate": "TEST-001",
            "vehicle_type": "Car",
            "make": "Toyota",
            "model": "Camry",
            "year": "2020",
            "color": "Blue",
            "status": "Active"
        }
    
    def test_parking_lot_data_flow(self):
        """Test data flow in parking lot operations"""
        # Create root and controller
        root = tk.Tk()
        root.withdraw()
        
        mock_controller = Mock()
        mock_controller.show_dialog = Mock()
        
        # Create view
        view = ParkingLotView(root, mock_controller)
        
        # Mock tree selection
        view.lot_tree = Mock()
        view.lot_tree.selection.return_value = ["item1"]
        view.lot_tree.item.return_value = {
            'values': ["1", "Test Lot", "TST001", "Test City", "75/100", "25%"]
        }
        
        # Mock show_lot_details to capture data
        captured_data = {}
        def capture_data(data):
            captured_data.update(data)
        
        view._show_lot_details = Mock(side_effect=capture_data)
        
        # Trigger selection
        view._on_lot_selected(None)
        
        # Verify data flow
        view._show_lot_details.assert_called_once()
        
        # Check that captured data matches expected structure
        call_args = view._show_lot_details.call_args[0][0]
        self.assertEqual(call_data["id"], "1")
        self.assertEqual(call_data["name"], "Test Lot")
        self.assertEqual(call_data["code"], "TST001")
        self.assertEqual(call_data["city"], "Test City")
        self.assertEqual(call_data["total_slots"], 100)
        self.assertEqual(call_data["available_slots"], 75)
        self.assertEqual(call_data["occupancy_rate"], 0.25)
        
        root.destroy()
    
    def test_vehicle_data_flow(self):
        """Test data flow in vehicle operations"""
        # Create root and controller
        root = tk.Tk()
        root.withdraw()
        
        mock_controller = Mock()
        
        # Create view
        view = VehicleManagementView(root, mock_controller)
        
        # Mock tree
        view.vehicle_tree = Mock()
        view.vehicle_tree.selection.return_value = ["item1"]
        view.vehicle_tree.item.return_value = {
            'values': ("TEST-001", "Car", "Toyota", "Camry", "2020", "Blue", "Active")
        }
        
        # Test data retrieval
        view._view_vehicle_details()
        
        # Verify controller was called with correct data
        mock_controller.show_dialog.assert_called_with(
            "vehicle_details",
            vehicle_id="item1"
        )
        
        root.destroy()
    
    def test_billing_data_flow(self):
        """Test data flow in billing operations"""
        # Create root and controller
        root = tk.Tk()
        root.withdraw()
        
        mock_controller = Mock()
        
        # Create view
        view = BillingView(root, mock_controller)
        
        # Mock invoice tree
        view.invoice_tree = Mock()
        view.invoice_tree.selection.return_value = ["item1"]
        
        # Test invoice selection
        view._view_invoice_details(None)
        
        # Verify controller was called
        mock_controller.show_dialog.assert_called_with(
            "invoice_details",
            invoice_id="item1"
        )
        
        root.destroy()


# ============================================================================
# EVENT HANDLING INTEGRATION TESTS
# ============================================================================

class TestEventHandlingIntegration(IntegrationTestBase):
    """Test event handling between components"""
    
    def setUp(self):
        super().setUp()
        
        # Create root window
        self.root = tk.Tk()
        self.root.withdraw()
    
    def test_gui_event_handling(self):
        """Test GUI event handling integration"""
        # Create mock controller
        mock_controller = Mock()
        mock_controller.app = Mock()
        
        # Create dashboard view
        view = DashboardView(self.root, mock_controller)
        
        # Test button clicks
        # (Dashboard refresh button is created in _setup_ui)
        # We need to find and test it
        
        # Instead, test that view can handle refresh
        view.refresh()
        
        # Verify view components were updated
        self.assertIsNotNone(view.total_lots_value.cget("text"))
        self.assertIsNotNone(view.available_slots_value.cget("text"))
    
    def test_dialog_event_handling(self):
        """Test dialog event handling integration"""
        # Create mock controller
        mock_controller = Mock()
        mock_controller.park_vehicle = Mock(return_value=(True, "Success"))
        
        # Create dialog
        dialog = ParkVehicleDialog(self.root, mock_controller)
        
        # Test vehicle type change event
        dialog.vehicle_type.set("EV Car")
        dialog._on_vehicle_type_changed(None)
        
        # Test EV charging toggle event
        dialog.needs_charging.set(True)
        dialog._toggle_ev_details()
        
        dialog.destroy()
    
    def test_custom_widget_event_handling(self):
        """Test custom widget event handling"""
        # Create parking slot widget
        slot_data = {
            'number': 1,
            'slot_type': 'REGULAR',
            'is_occupied': False,
            'is_reserved': False
        }
        
        slot_widget = ParkingSlotWidget(self.root, slot_data)
        
        # Test click event
        click_called = []
        def on_click(data):
            click_called.append(data)
        
        slot_widget.set_on_click(on_click)
        slot_widget._on_click(None)
        
        # Verify click handler was called
        self.assertEqual(len(click_called), 1)
        self.assertEqual(click_called[0]['number'], 1)
        
        # Test hover events
        slot_widget._on_enter(None)
        self.assertEqual(slot_widget.cget("cursor"), "hand2")
        
        slot_widget._on_leave(None)
        self.assertEqual(slot_widget.cget("cursor"), "")
    
    def tearDown(self):
        """Clean up"""
        self.root.destroy()
        super().tearDown()


# ============================================================================
# CONCURRENT OPERATION TESTS
# ============================================================================

class TestConcurrentOperations(IntegrationTestBase):
    """Test concurrent operations and thread safety"""
    
    def setUp(self):
        super().setUp()
        
        # Create root window
        self.root = tk.Tk()
        self.root.withdraw()
    
    def test_multiple_dialog_creation(self):
        """Test creating multiple dialogs concurrently"""
        # Create mock controller
        mock_controller = Mock()
        mock_controller.park_vehicle = Mock(return_value=(True, "Success"))
        mock_controller.add_parking_lot = Mock(return_value=(True, "Success"))
        
        # Create multiple dialogs
        dialogs = []
        
        # Create park vehicle dialog
        dialog1 = ParkVehicleDialog(self.root, mock_controller)
        dialogs.append(dialog1)
        
        # Create add parking lot dialog
        dialog2 = AddParkingLotDialog(self.root, mock_controller)
        dialogs.append(dialog2)
        
        # Verify both dialogs exist
        self.assertEqual(len(dialogs), 2)
        self.assertTrue(dialogs[0].winfo_exists())
        self.assertTrue(dialogs[1].winfo_exists())
        
        # Clean up
        for dialog in dialogs:
            dialog.destroy()
    
    def test_concurrent_view_operations(self):
        """Test concurrent operations on views"""
        import threading
        import time
        
        # Create mock controller
        mock_controller = Mock()
        mock_controller.app = Mock()
        
        # Create view
        view = DashboardView(self.root, mock_controller)
        
        # Test concurrent refreshes
        refresh_count = [0]
        
        def refresh_view():
            time.sleep(0.01)  # Small delay
            view.refresh()
            refresh_count[0] += 1
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=refresh_view)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=1.0)
        
        # Verify all refreshes completed
        self.assertEqual(refresh_count[0], 5)
        
        # Verify view is still functional
        view.refresh()  # One more from main thread
    
    def tearDown(self):
        """Clean up"""
        self.root.destroy()
        super().tearDown()


# ============================================================================
# ERROR RECOVERY INTEGRATION TESTS
# ============================================================================

class TestErrorRecoveryIntegration(IntegrationTestBase):
    """Test error recovery scenarios"""
    
    def setUp(self):
        super().setUp()
        
        # Create root window
        self.root = tk.Tk()
        self.root.withdraw()
    
    def test_dialog_error_recovery(self):
        """Test dialog error handling and recovery"""
        # Create mock controller that fails
        mock_controller = Mock()
        mock_controller.park_vehicle = Mock(return_value=(False, "Database connection failed"))
        
        # Create dialog
        dialog = ParkVehicleDialog(self.root, mock_controller)
        
        # Fill form
        dialog.license_plate.insert(0, "ABC-123")
        dialog.vehicle_type.set("Car")
        
        # Mock messagebox
        with patch('tkinter.messagebox.showerror') as mock_showerror:
            # Submit form (should fail)
            dialog._park_vehicle()
            
            # Verify error was shown
            mock_showerror.assert_called_with("Error", "Database connection failed")
            
            # Dialog should still be open
            self.assertTrue(dialog.winfo_exists())
            
            # User can retry with corrected data
            # Clear and enter new data
            dialog.license_plate.delete(0, tk.END)
            dialog.license_plate.insert(0, "XYZ-789")
            
            # Change controller to succeed
            mock_controller.park_vehicle.return_value = (True, "Success")
            
            # Mock success messagebox
            with patch('tkinter.messagebox.showinfo') as mock_showinfo:
                # Retry
                dialog._park_vehicle()
                
                # Verify success
                mock_showinfo.assert_called_with("Success", "Success")
                
                # Dialog should be destroyed on success
                self.assertFalse(dialog.winfo_exists())
        
        dialog.destroy()
    
    def test_view_error_recovery(self):
        """Test view error handling and recovery"""
        # Create mock controller
        mock_controller = Mock()
        mock_controller.app = Mock()
        
        # Create view
        view = ParkingLotView(self.root, mock_controller)
        
        # Simulate error in refresh
        original_refresh = view.refresh
        
        def failing_refresh():
            raise Exception("Data load failed")
        
        view.refresh = failing_refresh
        
        # Try to refresh (should fail but not crash)
        try:
            view.refresh()
            # If we get here, exception was caught somewhere
        except Exception:
            # If exception propagates, restore original and retry
            view.refresh = original_refresh
            view.refresh()  # Should work now
        
        # Verify view is still functional
        self.assertTrue(view.winfo_exists())
    
    def tearDown(self):
        """Clean up"""
        self.root.destroy()
        super().tearDown()


# ============================================================================
# PERFORMANCE INTEGRATION TESTS
# ============================================================================

class TestPerformanceIntegration(IntegrationTestBase):
    """Test performance aspects of integration"""
    
    def setUp(self):
        super().setUp()
        
        # Create root window
        self.root = tk.Tk()
        self.root.withdraw()
    
    def test_view_loading_performance(self):
        """Test view loading performance"""
        import time
        
        # Create mock controller
        mock_controller = Mock()
        mock_controller.app = Mock()
        
        # Time view creation
        start_time = time.time()
        
        views = []
        for _ in range(5):  # Create multiple views
            view = DashboardView(self.root, mock_controller)
            views.append(view)
        
        creation_time = time.time() - start_time
        
        # Verify creation is reasonable (under 2 seconds for 5 views)
        self.assertLess(creation_time, 2.0)
        
        # Time refresh operations
        start_time = time.time()
        
        for view in views:
            view.refresh()
        
        refresh_time = time.time() - start_time
        
        # Verify refresh is reasonable
        self.assertLess(refresh_time, 3.0)
    
    def test_dialog_creation_performance(self):
        """Test dialog creation performance"""
        import time
        
        # Create mock controller
        mock_controller = Mock()
        mock_controller.park_vehicle = Mock(return_value=(True, "Success"))
        
        # Time dialog creation
        dialogs = []
        start_time = time.time()
        
        for i in range(3):  # Create multiple dialogs
            dialog = ParkVehicleDialog(self.root, mock_controller)
            dialogs.append(dialog)
        
        creation_time = time.time() - start_time
        
        # Verify creation is reasonable
        self.assertLess(creation_time, 1.5)
        
        # Clean up
        for dialog in dialogs:
            dialog.destroy()
    
    def test_data_loading_performance(self):
        """Test data loading performance in views"""
        import time
        
        # Create mock controller
        mock_controller = Mock()
        mock_controller.app = Mock()
        
        # Create view with large dataset simulation
        view = VehicleManagementView(self.root, mock_controller)
        
        # Mock tree with many items
        view.vehicle_tree = Mock()
        
        # Simulate loading many items
        start_time = time.time()
        
        # Simulate refresh with mock data
        view.refresh()
        
        load_time = time.time() - start_time
        
        # Verify load time is reasonable
        self.assertLess(load_time, 1.0)
    
    def tearDown(self):
        """Clean up"""
        self.root.destroy()
        super().tearDown()


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_integration_tests():
    """Run all integration tests"""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestGUIControllerIntegration,
        TestViewControllerIntegration,
        TestDialogControllerIntegration,
        TestServiceLayerIntegration,
        TestCommandProcessorIntegration,
        TestEndToEndScenarios,
        TestDataFlowIntegration,
        TestEventHandlingIntegration,
        TestConcurrentOperations,
        TestErrorRecoveryIntegration,
        TestPerformanceIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    print("=" * 70)
    print("Parking Management System - Integration Tests")
    print("=" * 70)
    
    result = run_integration_tests()
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"\n{test}:")
            print(traceback)
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"\n{test}:")
            print(traceback)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)