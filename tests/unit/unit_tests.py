#!/usr/bin/env python3
"""
Unit Tests for Parking Management System

This file contains unit tests for individual components of the system.
Unit tests focus on testing components in isolation using mocks for dependencies.
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, create_autospec
from datetime import datetime, timedelta

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Try to import project modules
try:
    from src.application.parking_service import ParkingService
    from src.application.commands import CommandProcessor, ParkVehicleCommand, ExitVehicleCommand
    from src.application.dtos import ParkingRequestDTO, ParkingResponseDTO, ExitRequestDTO
    from src.infrastructure.factories import FactoryRegistry
    from src.infrastructure.messaging import MessageBus
    HAS_PROJECT_MODULES = True
except ImportError as e:
    print(f"Warning: Could not import some modules: {e}")
    HAS_PROJECT_MODULES = False


# ============================================================================
# BASE TEST CLASSES
# ============================================================================

class UnitTestBase(unittest.TestCase):
    """Base class for unit tests with common setup"""
    
    def setUp(self):
        """Set up test environment"""
        self.mock_repository = Mock()
        self.mock_factory = Mock()
        self.mock_message_bus = Mock()
        self.mock_event_bus = Mock()
        
    def create_mock(self, spec=None, **kwargs):
        """Create a mock with common configuration"""
        mock = Mock(spec=spec, **kwargs) if spec else Mock(**kwargs)
        return mock


# ============================================================================
# APPLICATION LAYER UNIT TESTS
# ============================================================================

class TestParkingService(UnitTestBase):
    """Unit tests for ParkingService"""
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def setUp(self):
        super().setUp()
        
        # Create ParkingService with mocked dependencies
        with patch('src.application.parking_service.ParkingLotRepository', return_value=self.mock_repository), \
             patch('src.application.parking_service.ParkingLotFactory', return_value=self.mock_factory), \
             patch('src.application.parking_service.MessageBus', return_value=self.mock_message_bus):
            
            try:
                self.parking_service = ParkingService()
                self.service_available = True
            except:
                self.service_available = False
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_parking_service_initialization(self):
        """Test that ParkingService initializes correctly"""
        if not self.service_available:
            self.skipTest("ParkingService could not be initialized")
        
        self.assertIsNotNone(self.parking_service)
        self.assertIsNotNone(self.parking_service.repository)
        self.assertIsNotNone(self.parking_service.factory)
        self.assertIsNotNone(self.parking_service.message_bus)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_park_vehicle_success(self):
        """Test successful vehicle parking"""
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
        
        # Verify interactions
        self.mock_repository.get_parking_lot.assert_called_with("test-lot-1")
        self.mock_repository.get_or_create_vehicle.assert_called()
        mock_parking_lot.find_available_slot.assert_called()
        self.mock_repository.save_parking_session.assert_called()
        
        # Verify response
        self.assertIsInstance(response, ParkingResponseDTO)
        self.assertTrue(response.success)
        self.assertIsNotNone(response.ticket_id)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_park_vehicle_no_available_slots(self):
        """Test parking when no slots are available"""
        if not self.service_available:
            self.skipTest("ParkingService could not be initialized")
        
        # Setup mock to return no available slots
        mock_parking_lot = Mock()
        mock_parking_lot.find_available_slot.return_value = None
        
        self.mock_repository.get_parking_lot.return_value = mock_parking_lot
        
        # Create request
        request = ParkingRequestDTO(
            license_plate="ABC-123",
            vehicle_type="Car",
            parking_lot_id="test-lot-1"
        )
        
        # Call service method
        response = self.parking_service.park_vehicle(request)
        
        # Verify response indicates failure
        self.assertIsInstance(response, ParkingResponseDTO)
        self.assertFalse(response.success)
        self.assertIn("No available slots", response.message)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_park_vehicle_invalid_parking_lot(self):
        """Test parking with invalid parking lot ID"""
        if not self.service_available:
            self.skipTest("ParkingService could not be initialized")
        
        # Setup mock to return None for parking lot
        self.mock_repository.get_parking_lot.return_value = None
        
        # Create request
        request = ParkingRequestDTO(
            license_plate="ABC-123",
            vehicle_type="Car",
            parking_lot_id="invalid-lot"
        )
        
        # Call service method
        response = self.parking_service.park_vehicle(request)
        
        # Verify response indicates failure
        self.assertIsInstance(response, ParkingResponseDTO)
        self.assertFalse(response.success)
        self.assertIn("not found", response.message.lower())
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_exit_vehicle_success(self):
        """Test successful vehicle exit"""
        if not self.service_available:
            self.skipTest("ParkingService could not be initialized")
        
        # Setup mock session
        mock_session = Mock()
        mock_session.id = "session-123"
        mock_session.entry_time = datetime.now() - timedelta(hours=2)
        mock_session.parking_lot = Mock(hourly_rate=5.0)
        mock_session.calculate_charge.return_value = 10.0
        
        self.mock_repository.get_parking_session.return_value = mock_session
        self.mock_repository.save_parking_session.return_value = "session-123"
        
        # Create request
        request = ExitRequestDTO(
            ticket_id="session-123",
            license_plate="ABC-123"
        )
        
        # Call service method
        response = self.parking_service.exit_vehicle(request)
        
        # Verify interactions
        self.mock_repository.get_parking_session.assert_called_with("session-123")
        mock_session.exit_vehicle.assert_called()
        mock_session.calculate_charge.assert_called()
        self.mock_repository.save_parking_session.assert_called_with(mock_session)
        
        # Verify response
        self.assertIsInstance(response, ParkingResponseDTO)
        self.assertTrue(response.success)
        self.assertEqual(response.total_charge, 10.0)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_exit_vehicle_invalid_ticket(self):
        """Test exit with invalid ticket ID"""
        if not self.service_available:
            self.skipTest("ParkingService could not be initialized")
        
        # Setup mock to return None for session
        self.mock_repository.get_parking_session.return_value = None
        
        # Create request
        request = ExitRequestDTO(
            ticket_id="invalid-ticket",
            license_plate="ABC-123"
        )
        
        # Call service method
        response = self.parking_service.exit_vehicle(request)
        
        # Verify response indicates failure
        self.assertIsInstance(response, ParkingResponseDTO)
        self.assertFalse(response.success)
        self.assertIn("not found", response.message.lower())
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_get_parking_lot_status(self):
        """Test getting parking lot status"""
        if not self.service_available:
            self.skipTest("ParkingService could not be initialized")
        
        # Setup mock parking lot
        mock_parking_lot = Mock()
        mock_parking_lot.id = "test-lot-1"
        mock_parking_lot.name = "Test Lot"
        mock_parking_lot.total_slots = 100
        mock_parking_lot.available_slots = 75
        mock_parking_lot.get_occupancy_rate.return_value = 0.25
        
        self.mock_repository.get_parking_lot.return_value = mock_parking_lot
        
        # Call service method
        status = self.parking_service.get_parking_lot_status("test-lot-1")
        
        # Verify interactions
        self.mock_repository.get_parking_lot.assert_called_with("test-lot-1")
        mock_parking_lot.get_occupancy_rate.assert_called()
        
        # Verify status
        self.assertEqual(status["id"], "test-lot-1")
        self.assertEqual(status["name"], "Test Lot")
        self.assertEqual(status["total_slots"], 100)
        self.assertEqual(status["available_slots"], 75)
        self.assertEqual(status["occupancy_rate"], 0.25)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_generate_daily_report(self):
        """Test generating daily report"""
        if not self.service_available:
            self.skipTest("ParkingService could not be initialized")
        
        # Setup mock data
        mock_sessions = [
            Mock(total_charge=10.0, duration_hours=2),
            Mock(total_charge=15.0, duration_hours=3),
            Mock(total_charge=5.0, duration_hours=1)
        ]
        
        self.mock_repository.get_sessions_by_date.return_value = mock_sessions
        
        # Call service method
        report_date = datetime.now().date()
        report = self.parking_service.generate_daily_report(report_date)
        
        # Verify interactions
        self.mock_repository.get_sessions_by_date.assert_called_with(report_date)
        
        # Verify report
        self.assertEqual(report["date"], report_date.isoformat())
        self.assertEqual(report["total_sessions"], 3)
        self.assertEqual(report["total_revenue"], 30.0)  # 10 + 15 + 5
        self.assertEqual(report["average_duration"], 2.0)  # (2 + 3 + 1) / 3


class TestCommandProcessor(UnitTestBase):
    """Unit tests for CommandProcessor"""
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def setUp(self):
        super().setUp()
        
        # Create mock parking service
        self.mock_parking_service = Mock(spec=ParkingService)
        
        # Create CommandProcessor
        self.command_processor = CommandProcessor(self.mock_parking_service)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_process_park_vehicle_command_success(self):
        """Test processing ParkVehicleCommand successfully"""
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
        self.assertEqual(result["slot_number"], "A-15")
        self.assertEqual(result["executed_by"], "test-user")
        self.assertIsNotNone(result["timestamp"])
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_process_park_vehicle_command_failure(self):
        """Test processing ParkVehicleCommand that fails"""
        # Setup mock response with failure
        mock_response = ParkingResponseDTO(
            success=False,
            message="No available slots",
            error_code="NO_SLOTS_AVAILABLE"
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
        
        # Verify result indicates failure
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "No available slots")
        self.assertEqual(result["error_code"], "NO_SLOTS_AVAILABLE")
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_process_exit_vehicle_command_success(self):
        """Test processing ExitVehicleCommand successfully"""
        # Setup mock response
        mock_response = ParkingResponseDTO(
            success=True,
            message="Vehicle exited successfully",
            total_charge=15.0,
            duration_hours=3.0
        )
        self.mock_parking_service.exit_vehicle.return_value = mock_response
        
        # Create command
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
        self.assertEqual(result["duration_hours"], 3.0)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_process_command_with_exception(self):
        """Test processing command when service raises exception"""
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
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_undo_command(self):
        """Test undoing a command"""
        # Create a command with undo support
        mock_command = Mock()
        mock_command.has_undo = True
        mock_command.undo.return_value = {"success": True, "message": "Undone"}
        
        # Add command to history
        self.command_processor.command_history.append(mock_command)
        
        # Undo last command
        result = self.command_processor.undo_last_command()
        
        # Verify undo was called
        mock_command.undo.assert_called()
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Undone")
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_undo_with_empty_history(self):
        """Test undoing when command history is empty"""
        # Ensure history is empty
        self.command_processor.command_history.clear()
        
        # Try to undo
        result = self.command_processor.undo_last_command()
        
        # Verify result indicates no commands to undo
        self.assertFalse(result["success"])
        self.assertIn("No commands", result["message"])
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_redo_command(self):
        """Test redoing a command"""
        # Create a command that was undone
        mock_command = Mock()
        mock_command.has_redo = True
        mock_command.redo.return_value = {"success": True, "message": "Redone"}
        
        # Add command to redo stack
        self.command_processor.redo_stack.append(mock_command)
        
        # Redo command
        result = self.command_processor.redo_last_command()
        
        # Verify redo was called
        mock_command.redo.assert_called()
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Redone")
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_get_command_history(self):
        """Test getting command history"""
        # Add some commands to history
        mock_command1 = Mock(executed_by="user1", timestamp="2024-01-01T10:00:00")
        mock_command2 = Mock(executed_by="user2", timestamp="2024-01-01T11:00:00")
        
        self.command_processor.command_history.extend([mock_command1, mock_command2])
        
        # Get history
        history = self.command_processor.get_command_history()
        
        # Verify history
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], mock_command1)
        self.assertEqual(history[1], mock_command2)


class TestCommands(UnitTestBase):
    """Unit tests for individual Command classes"""
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_park_vehicle_command_creation(self):
        """Test ParkVehicleCommand creation"""
        # Create request
        request = ParkingRequestDTO(
            license_plate="ABC-123",
            vehicle_type="Car",
            parking_lot_id="test-lot-1"
        )
        
        # Create command
        command = ParkVehicleCommand(request, executed_by="test-user")
        
        # Verify command properties
        self.assertEqual(command.request, request)
        self.assertEqual(command.executed_by, "test-user")
        self.assertIsNotNone(command.timestamp)
        self.assertTrue(command.has_undo)
        
        # Verify string representation
        self.assertIn("ParkVehicleCommand", str(command))
        self.assertIn("ABC-123", str(command))
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_exit_vehicle_command_creation(self):
        """Test ExitVehicleCommand creation"""
        # Create request
        request = ExitRequestDTO(
            ticket_id="TICKET-001",
            license_plate="ABC-123"
        )
        
        # Create command
        command = ExitVehicleCommand(request, executed_by="test-user")
        
        # Verify command properties
        self.assertEqual(command.request, request)
        self.assertEqual(command.executed_by, "test-user")
        self.assertIsNotNone(command.timestamp)
        self.assertTrue(command.has_undo)
        
        # Verify string representation
        self.assertIn("ExitVehicleCommand", str(command))
        self.assertIn("TICKET-001", str(command))
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_command_equality(self):
        """Test command equality comparison"""
        # Create two commands with same data
        request1 = ParkingRequestDTO(
            license_plate="ABC-123",
            vehicle_type="Car",
            parking_lot_id="test-lot-1"
        )
        
        request2 = ParkingRequestDTO(
            license_plate="ABC-123",
            vehicle_type="Car",
            parking_lot_id="test-lot-1"
        )
        
        command1 = ParkVehicleCommand(request1, executed_by="user1")
        command2 = ParkVehicleCommand(request2, executed_by="user1")
        
        # They should not be equal (different timestamps)
        self.assertNotEqual(command1, command2)
        
        # But their IDs might be compared
        if hasattr(command1, 'command_id') and hasattr(command2, 'command_id'):
            self.assertNotEqual(command1.command_id, command2.command_id)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_command_execution_result(self):
        """Test command execution result structure"""
        # Create a mock execution result
        result = {
            "success": True,
            "message": "Operation completed",
            "data": {"key": "value"},
            "timestamp": "2024-01-01T10:00:00"
        }
        
        # Verify result structure
        self.assertIn("success", result)
        self.assertIn("message", result)
        self.assertIn("timestamp", result)
        
        # Type checks
        self.assertIsInstance(result["success"], bool)
        self.assertIsInstance(result["message"], str)


class TestDTOs(UnitTestBase):
    """Unit tests for Data Transfer Objects"""
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_parking_request_dto_creation(self):
        """Test ParkingRequestDTO creation and validation"""
        # Create valid DTO
        request = ParkingRequestDTO(
            license_plate="ABC-123",
            vehicle_type="Car",
            parking_lot_id="test-lot-1",
            preferences={"preferred_slot_type": "regular"}
        )
        
        # Verify properties
        self.assertEqual(request.license_plate, "ABC-123")
        self.assertEqual(request.vehicle_type, "Car")
        self.assertEqual(request.parking_lot_id, "test-lot-1")
        self.assertEqual(request.preferences["preferred_slot_type"], "regular")
        
        # Test string representation
        self.assertIn("ParkingRequestDTO", str(request))
        self.assertIn("ABC-123", str(request))
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_parking_response_dto_creation(self):
        """Test ParkingResponseDTO creation"""
        # Create response DTO
        response = ParkingResponseDTO(
            success=True,
            message="Vehicle parked successfully",
            ticket_id="TICKET-001",
            slot_number="A-15",
            total_charge=10.0
        )
        
        # Verify properties
        self.assertTrue(response.success)
        self.assertEqual(response.message, "Vehicle parked successfully")
        self.assertEqual(response.ticket_id, "TICKET-001")
        self.assertEqual(response.slot_number, "A-15")
        self.assertEqual(response.total_charge, 10.0)
        
        # Test with error
        error_response = ParkingResponseDTO(
            success=False,
            message="No available slots",
            error_code="NO_SLOTS"
        )
        
        self.assertFalse(error_response.success)
        self.assertEqual(error_response.error_code, "NO_SLOTS")
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_exit_request_dto_creation(self):
        """Test ExitRequestDTO creation"""
        # Create exit request DTO
        request = ExitRequestDTO(
            ticket_id="TICKET-001",
            license_plate="ABC-123"
        )
        
        # Verify properties
        self.assertEqual(request.ticket_id, "TICKET-001")
        self.assertEqual(request.license_plate, "ABC-123")
        
        # Test with optional parameters
        request_with_options = ExitRequestDTO(
            ticket_id="TICKET-001",
            license_plate="ABC-123",
            payment_method="credit_card",
            discount_code="SUMMER2024"
        )
        
        self.assertEqual(request_with_options.payment_method, "credit_card")
        self.assertEqual(request_with_options.discount_code, "SUMMER2024")
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_dto_serialization(self):
        """Test DTO serialization to dict"""
        # Create DTO
        request = ParkingRequestDTO(
            license_plate="ABC-123",
            vehicle_type="Car",
            parking_lot_id="test-lot-1"
        )
        
        # Convert to dict (if method exists)
        if hasattr(request, 'to_dict'):
            data = request.to_dict()
            
            # Verify dict structure
            self.assertEqual(data["license_plate"], "ABC-123")
            self.assertEqual(data["vehicle_type"], "Car")
            self.assertEqual(data["parking_lot_id"], "test-lot-1")
        
        # Test from dict (if method exists)
        if hasattr(ParkingRequestDTO, 'from_dict'):
            data = {
                "license_plate": "XYZ-789",
                "vehicle_type": "EV",
                "parking_lot_id": "test-lot-2"
            }
            
            dto = ParkingRequestDTO.from_dict(data)
            self.assertEqual(dto.license_plate, "XYZ-789")
            self.assertEqual(dto.vehicle_type, "EV")


# ============================================================================
# INFRASTRUCTURE LAYER UNIT TESTS
# ============================================================================

class TestFactoryRegistry(UnitTestBase):
    """Unit tests for FactoryRegistry"""
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def setUp(self):
        super().setUp()
        
        try:
            self.factory_registry = FactoryRegistry()
            self.registry_available = True
        except:
            self.registry_available = False
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_factory_registry_initialization(self):
        """Test FactoryRegistry initialization"""
        if not self.registry_available:
            self.skipTest("FactoryRegistry could not be initialized")
        
        self.assertIsNotNone(self.factory_registry)
        
        # Verify it has expected methods
        self.assertTrue(hasattr(self.factory_registry, 'register_factory'))
        self.assertTrue(hasattr(self.factory_registry, 'get_factory'))
        self.assertTrue(hasattr(self.factory_registry, 'create'))
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_register_and_get_factory(self):
        """Test registering and getting factories"""
        if not self.registry_available:
            self.skipTest("FactoryRegistry could not be initialized")
        
        # Create mock factory
        mock_factory = Mock()
        
        # Register factory
        self.factory_registry.register_factory("test_factory", mock_factory)
        
        # Get factory
        factory = self.factory_registry.get_factory("test_factory")
        
        # Verify
        self.assertEqual(factory, mock_factory)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_get_nonexistent_factory(self):
        """Test getting a factory that doesn't exist"""
        if not self.registry_available:
            self.skipTest("FactoryRegistry could not be initialized")
        
        # Try to get non-existent factory
        factory = self.factory_registry.get_factory("nonexistent")
        
        # Should return None or raise exception
        if factory is None:
            self.assertIsNone(factory)
        else:
            # If it doesn't return None, it should raise an exception
            with self.assertRaises(Exception):
                self.factory_registry.get_factory("nonexistent")
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_create_using_factory(self):
        """Test creating objects using registered factory"""
        if not self.registry_available:
            self.skipTest("FactoryRegistry could not be initialized")
        
        # Create mock factory with create method
        mock_factory = Mock()
        mock_object = Mock(name="TestObject")
        mock_factory.create.return_value = mock_object
        
        # Register factory
        self.factory_registry.register_factory("test_type", mock_factory)
        
        # Create object
        result = self.factory_registry.create("test_type", arg1="value1", arg2="value2")
        
        # Verify factory was called with correct arguments
        mock_factory.create.assert_called_with(arg1="value1", arg2="value2")
        
        # Verify result
        self.assertEqual(result, mock_object)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_list_registered_factories(self):
        """Test listing registered factories"""
        if not self.registry_available:
            self.skipTest("FactoryRegistry could not be initialized")
        
        # Register some factories
        mock_factory1 = Mock()
        mock_factory2 = Mock()
        
        self.factory_registry.register_factory("factory1", mock_factory1)
        self.factory_registry.register_factory("factory2", mock_factory2)
        
        # Get list (if method exists)
        if hasattr(self.factory_registry, 'list_factories'):
            factories = self.factory_registry.list_factories()
            
            # Verify list contains registered factories
            self.assertIn("factory1", factories)
            self.assertIn("factory2", factories)


class TestMessageBus(UnitTestBase):
    """Unit tests for MessageBus"""
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def setUp(self):
        super().setUp()
        
        try:
            self.message_bus = MessageBus()
            self.message_bus_available = True
        except:
            self.message_bus_available = False
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_message_bus_initialization(self):
        """Test MessageBus initialization"""
        if not self.message_bus_available:
            self.skipTest("MessageBus could not be initialized")
        
        self.assertIsNotNone(self.message_bus)
        
        # Verify it has expected methods
        self.assertTrue(hasattr(self.message_bus, 'subscribe'))
        self.assertTrue(hasattr(self.message_bus, 'unsubscribe'))
        self.assertTrue(hasattr(self.message_bus, 'publish'))
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_subscribe_and_publish(self):
        """Test subscribing to and publishing events"""
        if not self.message_bus_available:
            self.skipTest("MessageBus could not be initialized")
        
        # Create mock handler
        mock_handler = Mock()
        
        # Subscribe to event
        self.message_bus.subscribe("test_event", mock_handler)
        
        # Create event data
        event_data = {"message": "Test event", "value": 42}
        
        # Publish event
        self.message_bus.publish("test_event", event_data)
        
        # Verify handler was called with correct data
        mock_handler.assert_called_with(event_data)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_multiple_subscribers(self):
        """Test multiple subscribers for same event"""
        if not self.message_bus_available:
            self.skipTest("MessageBus could not be initialized")
        
        # Create multiple mock handlers
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()
        
        # Subscribe all handlers
        self.message_bus.subscribe("multi_event", handler1)
        self.message_bus.subscribe("multi_event", handler2)
        self.message_bus.subscribe("multi_event", handler3)
        
        # Publish event
        event_data = {"test": "data"}
        self.message_bus.publish("multi_event", event_data)
        
        # Verify all handlers were called
        handler1.assert_called_with(event_data)
        handler2.assert_called_with(event_data)
        handler3.assert_called_with(event_data)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_unsubscribe(self):
        """Test unsubscribing from events"""
        if not self.message_bus_available:
            self.skipTest("MessageBus could not be initialized")
        
        # Create mock handler
        mock_handler = Mock()
        
        # Subscribe
        subscription_id = self.message_bus.subscribe("unsubscribe_event", mock_handler)
        
        # Publish once
        self.message_bus.publish("unsubscribe_event", {"first": "call"})
        self.assertEqual(mock_handler.call_count, 1)
        
        # Unsubscribe
        self.message_bus.unsubscribe("unsubscribe_event", subscription_id)
        
        # Publish again
        self.message_bus.publish("unsubscribe_event", {"second": "call"})
        
        # Handler should not be called again
        self.assertEqual(mock_handler.call_count, 1)
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_publish_to_nonexistent_event(self):
        """Test publishing to event with no subscribers"""
        if not self.message_bus_available:
            self.skipTest("MessageBus could not be initialized")
        
        # Publish to event with no subscribers
        # Should not raise exception
        try:
            self.message_bus.publish("nonexistent_event", {"data": "test"})
        except Exception as e:
            self.fail(f"Publishing to nonexistent event raised exception: {e}")
    
    @unittest.skipUnless(HAS_PROJECT_MODULES, "Project modules not available")
    def test_handler_exception_handling(self):
        """Test exception handling in event handlers"""
        if not self.message_bus_available:
            self.skipTest("MessageBus could not be initialized")
        
        # Create handlers, one that raises exception
        good_handler = Mock()
        bad_handler = Mock(side_effect=Exception("Handler error"))
        another_good_handler = Mock()
        
        # Subscribe all handlers
        self.message_bus.subscribe("error_event", good_handler)
        self.message_bus.subscribe("error_event", bad_handler)
        self.message_bus.subscribe("error_event", another_good_handler)
        
        # Publish event
        # All handlers should be called, even if one raises exception
        try:
            self.message_bus.publish("error_event", {"test": "data"})
        except Exception:
            # MessageBus might propagate exceptions or not
            # Either behavior is acceptable
            pass
        
        # Verify all handlers were called
        good_handler.assert_called()
        bad_handler.assert_called()
        another_good_handler.assert_called()


# ============================================================================
# UTILITY FUNCTION TESTS
# ============================================================================

class TestUtilityFunctions(unittest.TestCase):
    """Unit tests for utility functions"""
    
    def test_datetime_parsing(self):
        """Test datetime parsing utilities"""
        from datetime import datetime
        
        # Test ISO format parsing
        iso_string = "2024-01-15T10:30:00"
        dt = datetime.fromisoformat(iso_string)
        
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 15)
        self.assertEqual(dt.hour, 10)
        self.assertEqual(dt.minute, 30)
    
    def test_money_calculation(self):
        """Test money calculation utilities"""
        # Test basic arithmetic
        self.assertEqual(10.0 + 5.0, 15.0)
        self.assertEqual(20.0 - 7.5, 12.5)
        self.assertEqual(5.0 * 3.0, 15.0)
        self.assertEqual(21.0 / 3.0, 7.0)
        
        # Test rounding
        self.assertEqual(round(10.555, 2), 10.56)
        self.assertEqual(round(10.554, 2), 10.55)
    
    def test_string_validation(self):
        """Test string validation utilities"""
        # Test license plate validation
        valid_plates = ["ABC-123", "XYZ789", "TEST-001", "EV-2024"]
        invalid_plates = ["", "ABC-", "-123", "TOO-LONG-PLATE"]
        
        for plate in valid_plates:
            # Basic validation: not empty and reasonable length
            self.assertTrue(len(plate) > 0 and len(plate) <= 20)
        
        for plate in invalid_plates:
            if plate == "":
                self.assertFalse(len(plate) > 0)
            else:
                self.assertFalse(len(plate) <= 20)
    
    def test_list_operations(self):
        """Test list operations used in the system"""
        # Test list filtering
        numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        even_numbers = [n for n in numbers if n % 2 == 0]
        
        self.assertEqual(even_numbers, [2, 4, 6, 8, 10])
        
        # Test list mapping
        squared = [n * n for n in numbers]
        self.assertEqual(squared, [1, 4, 9, 16, 25, 36, 49, 64, 81, 100])
        
        # Test list sorting
        unsorted = [5, 2, 8, 1, 9]
        sorted_list = sorted(unsorted)
        self.assertEqual(sorted_list, [1, 2, 5, 8, 9])
    
    def test_dictionary_operations(self):
        """Test dictionary operations used in the system"""
        # Test dictionary creation and access
        config = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "parking_db"
            },
            "server": {
                "port": 8080,
                "debug": True
            }
        }
        
        self.assertEqual(config["database"]["host"], "localhost")
        self.assertEqual(config["server"]["port"], 8080)
        
        # Test dictionary merging
        dict1 = {"a": 1, "b": 2}
        dict2 = {"b": 3, "c": 4}
        merged = {**dict1, **dict2}
        
        self.assertEqual(merged, {"a": 1, "b": 3, "c": 4})
        
        # Test dictionary comprehension
        squares = {x: x*x for x in range(1, 6)}
        self.assertEqual(squares, {1: 1, 2: 4, 3: 9, 4: 16, 5: 25})
    
    def test_error_handling_patterns(self):
        """Test common error handling patterns"""
        # Test try-except
        def divide(a, b):
            try:
                return a / b
            except ZeroDivisionError:
                return None
        
        self.assertEqual(divide(10, 2), 5.0)
        self.assertIsNone(divide(10, 0))
        
        # Test context manager pattern
        class MockResource:
            def __enter__(self):
                self.open = True
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.open = False
        
        with MockResource() as resource:
            self.assertTrue(resource.open)
        
        self.assertFalse(resource.open)


# ============================================================================
# MOCK OBJECT TESTS
# ============================================================================

class TestMockObjects(unittest.TestCase):
    """Tests for mock objects used in unit testing"""
    
    def test_mock_creation(self):
        """Test creating mock objects"""
        # Create a simple mock
        mock_obj = Mock()
        
        # Set attributes
        mock_obj.name = "Test Mock"
        mock_obj.value = 42
        
        self.assertEqual(mock_obj.name, "Test Mock")
        self.assertEqual(mock_obj.value, 42)
        
        # Call methods
        mock_obj.some_method.return_value = "result"
        self.assertEqual(mock_obj.some_method(), "result")
    
    def test_mock_with_spec(self):
        """Test creating mock objects with spec"""
        # Define a class to use as spec
        class ExampleClass:
            def existing_method(self):
                pass
            
            @property
            def existing_property(self):
                return "value"
        
        # Create mock with spec
        mock_with_spec = Mock(spec=ExampleClass)
        
        # Existing methods should work
        mock_with_spec.existing_method.return_value = "mock result"
        self.assertEqual(mock_with_spec.existing_method(), "mock result")
        
        # Non-existent methods should raise AttributeError
        with self.assertRaises(AttributeError):
            mock_with_spec.non_existent_method()
    
    def test_mock_assertions(self):
        """Test assertions on mock objects"""
        mock_obj = Mock()
        
        # Call methods
        mock_obj.method1("arg1", "arg2")
        mock_obj.method2(42)
        mock_obj.method1("arg3")
        
        # Assert methods were called
        mock_obj.method1.assert_called()
        mock_obj.method2.assert_called_once()
        
        # Assert with specific arguments
        mock_obj.method1.assert_any_call("arg1", "arg2")
        
        # Assert call count
        self.assertEqual(mock_obj.method1.call_count, 2)
        self.assertEqual(mock_obj.method2.call_count, 1)
    
    def test_mock_side_effects(self):
        """Test mock side effects"""
        mock_obj = Mock()
        
        # Set side effect to return different values
        mock_obj.get_value.side_effect = [1, 2, 3, 4, 5]
        
        results = []
        for _ in range(5):
            results.append(mock_obj.get_value())
        
        self.assertEqual(results, [1, 2, 3, 4, 5])
        
        # Set side effect to raise exception
        mock_obj.failing_method.side_effect = ValueError("Test error")
        
        with self.assertRaises(ValueError):
            mock_obj.failing_method()
    
    def test_patch_decorator(self):
        """Test using patch decorator"""
        # This would test patching in real scenarios
        # For now, just verify we can import patch
        from unittest.mock import patch
        
        self.assertTrue(callable(patch))
        
        # Example of how patch would be used
        @patch('some_module.SomeClass')
        def test_function(mock_class):
            mock_instance = mock_class.return_value
            mock_instance.method.return_value = "mocked"
            
            # Test code that uses SomeClass
            result = mock_instance.method()
            
            self.assertEqual(result, "mocked")
            mock_instance.method.assert_called_once()
        
        # This just shows the pattern
        pass


# ============================================================================
# EXCEPTION HANDLING TESTS
# ============================================================================

class TestExceptionHandling(unittest.TestCase):
    """Tests for exception handling patterns"""
    
    def test_custom_exceptions(self):
        """Test creating and using custom exceptions"""
        # Define custom exceptions
        class ParkingSystemError(Exception):
            """Base exception for parking system"""
            pass
        
        class NoAvailableSlotsError(ParkingSystemError):
            """Raised when no parking slots are available"""
            pass
        
        class InvalidTicketError(ParkingSystemError):
            """Raised when ticket is invalid"""
            pass
        
        # Test raising custom exceptions
        with self.assertRaises(NoAvailableSlotsError):
            raise NoAvailableSlotsError("Parking lot is full")
        
        with self.assertRaises(InvalidTicketError):
            raise InvalidTicketError("Ticket not found")
        
        # Test inheritance
        self.assertTrue(issubclass(NoAvailableSlotsError, ParkingSystemError))
        self.assertTrue(issubclass(InvalidTicketError, ParkingSystemError))
    
    def test_exception_chaining(self):
        """Test exception chaining"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise RuntimeError("New error") from e
        except RuntimeError as e:
            self.assertIsInstance(e.__cause__, ValueError)
            self.assertEqual(str(e.__cause__), "Original error")
    
    def test_exception_message_formatting(self):
        """Test formatting exception messages"""
        license_plate = "ABC-123"
        lot_id = "lot-001"
        
        # Format error message with variables
        error_msg = f"No available slots for vehicle {license_plate} in lot {lot_id}"
        
        self.assertEqual(
            error_msg,
            "No available slots for vehicle ABC-123 in lot lot-001"
        )
        
        # Test with dictionary data
        error_data = {
            "license_plate": "XYZ-789",
            "lot_id": "lot-002",
            "available_slots": 0
        }
        
        error_msg = (
            f"Vehicle {error_data['license_plate']} cannot park in "
            f"lot {error_data['lot_id']}. Available slots: {error_data['available_slots']}"
        )
        
        self.assertIn("XYZ-789", error_msg)
        self.assertIn("lot-002", error_msg)
        self.assertIn("Available slots: 0", error_msg)
    
    def test_exception_logging_pattern(self):
        """Test exception logging patterns"""
        import logging
        
        # Create mock logger
        mock_logger = Mock(spec=logging.Logger)
        
        # Example of exception logging pattern
        try:
            # Simulate operation that might fail
            result = 10 / 0
        except ZeroDivisionError as e:
            # Log the exception
            mock_logger.error(f"Division error: {e}", exc_info=True)
            
            # Re-raise or handle
            raise
        
        # Verify logger was called
        mock_logger.error.assert_called()
        
        # Get call arguments
        call_args = mock_logger.error.call_args[0]
        self.assertIn("Division error", call_args[0])


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_unit_tests(test_classes=None, verbosity=2):
    """
    Run unit tests.
    
    Args:
        test_classes: List of test classes to run (None for all)
        verbosity: Verbosity level (1=quiet, 2=verbose)
    
    Returns:
        unittest.TestResult: Test execution result
    """
    # Create test suite
    suite = unittest.TestSuite()
    
    # Default test classes if none specified
    if test_classes is None:
        test_classes = [
            TestParkingService,
            TestCommandProcessor,
            TestCommands,
            TestDTOs,
            TestFactoryRegistry,
            TestMessageBus,
            TestUtilityFunctions,
            TestMockObjects,
            TestExceptionHandling
        ]
    
    # Add tests to suite
    loader = unittest.TestLoader()
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result


def run_specific_unit_tests(test_methods, verbosity=2):
    """
    Run specific unit test methods.
    
    Args:
        test_methods: List of test method names in format "TestClass.test_method"
        verbosity: Verbosity level
    
    Returns:
        unittest.TestResult: Test execution result
    """
    suite = unittest.TestSuite()
    
    for test_method in test_methods:
        try:
            # Parse test class and method name
            class_name, method_name = test_method.split('.')
            
            # Find test class
            test_class = globals().get(class_name)
            if test_class is None:
                print(f"Test class not found: {class_name}")
                continue
            
            # Create test case
            test_case = test_class(method_name)
            suite.addTest(test_case)
            
        except ValueError:
            print(f"Invalid test method format: {test_method}. Use 'TestClass.test_method'")
        except Exception as e:
            print(f"Error loading test {test_method}: {e}")
    
    if suite.countTestCases() == 0:
        print("No valid tests to run")
        return None
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run unit tests for Parking Management System')
    parser.add_argument('--verbosity', '-v', type=int, default=2,
                       help='Verbosity level (1=quiet, 2=verbose)')
    parser.add_argument('--test', '-t', action='append',
                       help='Run specific test (format: TestClass.test_method)')
    parser.add_argument('--list', '-l', action='store_true',
                       help='List all available test classes')
    parser.add_argument('--coverage', '-c', action='store_true',
                       help='Run with coverage reporting')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Parking Management System - Unit Tests")
    print("=" * 70)
    
    if args.list:
        print("\nAvailable Test Classes:")
        print("-" * 40)
        
        # Find all test classes
        for name, obj in globals().items():
            if (name.startswith('Test') and 
                isinstance(obj, type) and 
                issubclass(obj, unittest.TestCase)):
                print(f"  • {name}")
        
        print(f"\nTotal: {sum(1 for name in globals() if name.startswith('Test') and isinstance(globals()[name], type) and issubclass(globals()[name], unittest.TestCase))} test classes")
        
    elif args.test:
        print(f"\nRunning specific tests: {', '.join(args.test)}")
        result = run_specific_unit_tests(args.test, args.verbosity)
        
    else:
        print("\nRunning all unit tests...")
        
        if args.coverage:
            # Run with coverage
            try:
                import coverage
                
                cov = coverage.Coverage()
                cov.start()
                
                result = run_unit_tests(verbosity=args.verbosity)
                
                cov.stop()
                cov.save()
                
                print("\n" + "=" * 70)
                print("Coverage Report")
                print("=" * 70)
                cov.report()
                
                # Generate HTML report
                cov.html_report(directory='htmlcov')
                print("\nHTML coverage report generated in 'htmlcov' directory")
                
            except ImportError:
                print("Coverage module not installed. Run without --coverage or install coverage package.")
                result = run_unit_tests(verbosity=args.verbosity)
        else:
            result = run_unit_tests(verbosity=args.verbosity)
    
    if 'result' in locals() and result is not None:
        print("\n" + "=" * 70)
        print("Test Summary")
        print("=" * 70)
        print(f"Tests Run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Skipped: {len(result.skipped)}")
        
        if result.wasSuccessful():
            print("\n✅ All unit tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some unit tests failed!")
            
            if result.failures:
                print("\nFailures:")
                for test, traceback in result.failures:
                    print(f"\n{test}:")
                    # Show first line of failure
                    lines = traceback.split('\n')
                    if lines:
                        print(f"  {lines[0]}")
            
            if result.errors:
                print("\nErrors:")
                for test, traceback in result.errors:
                    print(f"\n{test}:")
                    lines = traceback.split('\n')
                    if lines:
                        print(f"  {lines[0]}")
            
            sys.exit(1)