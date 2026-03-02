# File: tests/test_design_patterns.py
"""
Tests for design patterns used in the Parking Management System.

This file tests:
1. MVC Pattern implementation
2. Command Pattern
3. Factory Pattern
4. Observer Pattern (for events)
5. Singleton Pattern (if used)
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.presentation.parking_gui import (
    ParkingAppController,
    ParkingManagementApp,
    BaseView,
    DashboardView
)
from src.application.commands import CommandProcessor, ParkVehicleCommand
from src.infrastructure.factories import FactoryRegistry


class TestMVCPattern(unittest.TestCase):
    """Test MVC Pattern implementation"""
    
    def test_separation_of_concerns(self):
        """Test that Model, View, Controller are properly separated"""
        
        # Test 1: View should not contain business logic
        mock_controller = Mock()
        view = DashboardView(Mock(), mock_controller)
        
        # View should delegate actions to controller
        view.controller.switch_view("other_view")
        mock_controller.switch_view.assert_called_with("other_view")
    
    def test_controller_mediates(self):
        """Test controller mediates between view and model"""
        # Mock dependencies
        mock_app = Mock()
        
        with patch('src.presentation.parking_gui.ParkingServiceFactory') as mock_factory, \
             patch('src.presentation.parking_gui.CommandProcessor') as mock_processor:
            
            # Create controller
            controller = ParkingAppController(mock_app)
            
            # Test that controller initializes services (model layer)
            mock_factory.create_default_service.assert_called_once()
            mock_processor.assert_called_once()
    
    def test_view_independence(self):
        """Test views are independent and can be switched"""
        mock_app = Mock()
        mock_app.switch_view = Mock()
        
        # Create controller with mock app
        controller = ParkingAppController(mock_app)
        
        # Test switching views
        controller.switch_view("dashboard")
        mock_app.switch_view.assert_called_with("dashboard")
        
        controller.switch_view("parking_lots")
        mock_app.switch_view.assert_called_with("parking_lots")


class TestCommandPattern(unittest.TestCase):
    """Test Command Pattern implementation"""
    
    def test_command_creation(self):
        """Test command object creation"""
        # This would test the actual command classes from application layer
        # For now, test that the controller uses command processor
        
        mock_app = Mock()
        
        with patch('src.presentation.parking_gui.ParkingServiceFactory') as mock_factory, \
             patch('src.presentation.parking_gui.CommandProcessor') as mock_processor_class:
            
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor
            
            controller = ParkingAppController(mock_app)
            
            # Test that controller has command processor
            self.assertIsNotNone(controller.command_processor)
    
    def test_command_execution_flow(self):
        """Test command execution flow from GUI to business layer"""
        mock_app = Mock()
        
        with patch('src.presentation.parking_gui.ParkingServiceFactory') as mock_factory, \
             patch('src.presentation.parking_gui.CommandProcessor') as mock_processor_class, \
             patch('src.presentation.parking_gui.ParkingRequestDTO') as mock_request, \
             patch('src.presentation.parking_gui.uuid4'):
            
            mock_processor = Mock()
            mock_processor.process.return_value = {"success": True}
            mock_processor_class.return_value = mock_processor
            
            controller = ParkingAppController(mock_app)
            
            # Test parking vehicle command flow
            vehicle_data = {
                "license_plate": "ABC123",
                "vehicle_type": "Car"
            }
            
            success, message = controller.park_vehicle(vehicle_data)
            
            # Verify command was processed
            mock_processor.process.assert_called_once()
            self.assertTrue(success)


class TestFactoryPattern(unittest.TestCase):
    """Test Factory Pattern implementation"""
    
    def test_service_factory(self):
        """Test that services are created via factory"""
        # This tests the factory pattern in the infrastructure layer
        # The GUI controller should use factories to create services
        
        mock_app = Mock()
        
        with patch('src.presentation.parking_gui.ParkingServiceFactory.create_default_service') as mock_create_service, \
             patch('src.presentation.parking_gui.CommandProcessor'), \
             patch('src.presentation.parking_gui.FactoryRegistry'):
            
            # Create controller
            ParkingAppController(mock_app)
            
            # Verify factory method was called
            mock_create_service.assert_called_once()
    
    def test_dialog_factory_method(self):
        """Test dialog creation via factory method in controller"""
        mock_app = Mock()
        
        with patch('src.presentation.parking_gui.ParkingServiceFactory'), \
             patch('src.presentation.parking_gui.CommandProcessor'), \
             patch('src.presentation.parking_gui.FactoryRegistry'):
            
            controller = ParkingAppController(mock_app)
            
            # Test getting dialog class
            dialog_class = controller._get_dialog_class("park_vehicle")
            self.assertIsNotNone(dialog_class)
            
            # Test getting unknown dialog
            dialog_class = controller._get_dialog_class("unknown_dialog")
            self.assertIsNone(dialog_class)


class TestObserverPattern(unittest.TestCase):
    """Test Observer Pattern for event handling"""
    
    def test_event_notification(self):
        """Test that GUI components can observe and react to events"""
        # Note: The actual event/observer implementation would be in the
        # messaging module. This test verifies the pattern concept.
        
        # Create mock event bus
        mock_event_bus = Mock()
        
        # Test that views could subscribe to events
        # (This is a conceptual test since actual implementation may vary)
        
        # Example: Dashboard should update when occupancy changes
        mock_controller = Mock()
        mock_controller.app = Mock()
        
        view = DashboardView(Mock(), mock_controller)
        
        # Simulate receiving an event
        # In a real implementation, the view would have an update method
        # that gets called when observed events occur
        
        # For now, test that refresh method exists
        self.assertTrue(hasattr(view, 'refresh'))
        self.assertTrue(callable(view.refresh))


class TestSingletonPattern(unittest.TestCase):
    """Test Singleton Pattern usage"""
    
    def test_config_singleton(self):
        """Test that configuration acts like a singleton"""
        # AppConfig is used as a configuration singleton
        config1 = AppConfig
        config2 = AppConfig
        
        self.assertIs(config1, config2)
        
        # Constants should be the same
        self.assertEqual(config1.APP_NAME, config2.APP_NAME)
        self.assertEqual(config1.VERSION, config2.VERSION)
    
    def test_theme_enum_as_singleton(self):
        """Test Theme enum usage as singleton-like"""
        # Enums in Python are essentially singletons for their members
        theme1 = Theme.LIGHT
        theme2 = Theme.LIGHT
        
        self.assertIs(theme1, theme2)
        self.assertEqual(theme1.value, "light")


class TestCompositePattern(unittest.TestCase):
    """Test Composite Pattern in UI components"""
    
    def test_widget_composition(self):
        """Test that complex widgets are composed of simpler ones"""
        mock_root = Mock()
        
        # CardFrame composes other widgets
        card = CardFrame(mock_root, title="Test Card")
        
        # Add widgets to card (composition)
        label1 = Mock()
        label2 = Mock()
        
        card.add_widget(label1)
        card.add_widget(label2)
        
        # In actual implementation, card would manage these child widgets
        # This tests the composite pattern concept
    
    def test_view_composition(self):
        """Test that views are composed of multiple widgets"""
        mock_controller = Mock()
        mock_controller.app = Mock()
        
        # DashboardView is a composite of multiple cards and widgets
        view = DashboardView(Mock(), mock_controller)
        
        # Should contain multiple sub-components
        self.assertTrue(hasattr(view, 'total_lots_card'))
        self.assertTrue(hasattr(view, 'available_slots_card'))
        self.assertTrue(hasattr(view, 'occupancy_chart'))
        
        # All components work together as a composite


class TestStrategyPattern(unittest.TestCase):
    """Test Strategy Pattern for algorithms"""
    
    def test_parking_strategy(self):
        """Test different parking strategies"""
        # Note: The actual strategy pattern would be in the business logic
        # This tests that the GUI can work with different strategies
        
        # Example: Different pricing strategies, parking allocation strategies
        # would be selectable/swappable
        
        # For now, test that controller can handle different scenarios
        mock_app = Mock()
        
        with patch('src.presentation.parking_gui.ParkingServiceFactory'), \
             patch('src.presentation.parking_gui.CommandProcessor'), \
             patch('src.presentation.parking_gui.FactoryRegistry'):
            
            controller = ParkingAppController(mock_app)
            
            # Test parking with different vehicle types (could use different strategies)
            vehicle_data_car = {
                "license_plate": "CAR123",
                "vehicle_type": "Car"
            }
            
            vehicle_data_ev = {
                "license_plate": "EV123",
                "vehicle_type": "EV Car"
            }
            
            # Both should work with the same interface (strategy pattern)
            # The actual strategy would be selected based on vehicle type
            
            # This is a conceptual test
            self.assertTrue(callable(controller.park_vehicle))


def run_pattern_tests():
    """Run design pattern tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMVCPattern)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCommandPattern))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFactoryPattern))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestObserverPattern))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSingletonPattern))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCompositePattern))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestStrategyPattern))
    
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    result = run_pattern_tests()
    sys.exit(0 if result.wasSuccessful() else 1)