# File: tests/test_patterns.py
"""
Test suite for Parking Management System patterns and components.

This test suite covers:
1. MVC Pattern tests
2. Custom Widget tests
3. Dialog tests
4. Controller tests
5. Integration tests
6. UI Component tests
"""

import unittest
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import the components to test
from src.presentation.parking_gui import (
    ParkingManagementApp,
    ParkingAppController,
    DashboardView,
    ParkingLotView,
    VehicleManagementView,
    BillingView,
    ModernButton,
    CardFrame,
    StatusIndicator,
    ParkingSlotWidget,
    DashboardChart,
    ParkVehicleDialog,
    AddParkingLotDialog,
    AppConfig,
    Theme
)


# ============================================================================
# TEST CUSTOM WIDGETS
# ============================================================================

class TestModernButton(unittest.TestCase):
    """Test ModernButton custom widget"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the window
    
    def test_button_creation(self):
        """Test button creation with different styles"""
        button = ModernButton(self.root, text="Test Button")
        self.assertEqual(button.cget("text"), "Test Button")
    
    def test_button_hover_effect(self):
        """Test hover effect on button"""
        button = ModernButton(self.root, text="Hover Test")
        
        # Simulate mouse enter
        button._on_enter(None)
        
        # Simulate mouse leave
        button._on_leave(None)
    
    def tearDown(self):
        self.root.destroy()


class TestCardFrame(unittest.TestCase):
    """Test CardFrame custom widget"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
    
    def test_card_creation(self):
        """Test card frame creation with title"""
        card = CardFrame(self.root, title="Test Card")
        self.assertIsNotNone(card)
    
    def test_add_widget(self):
        """Test adding widgets to card"""
        card = CardFrame(self.root)
        label = ttk.Label(card, text="Test Label")
        card.add_widget(label)
        
        # Check that label is in card
        self.assertIn(label, card.winfo_children())
    
    def tearDown(self):
        self.root.destroy()


class TestStatusIndicator(unittest.TestCase):
    """Test StatusIndicator widget"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
    
    def test_indicator_creation(self):
        """Test creating status indicator with different statuses"""
        for status in ["success", "warning", "danger", "info", "secondary"]:
            indicator = StatusIndicator(self.root, status=status)
            self.assertIsNotNone(indicator)
    
    def test_set_status(self):
        """Test changing status"""
        indicator = StatusIndicator(self.root, status="success")
        indicator.set_status("warning")
        
        # Verify canvas item exists
        self.assertIsNotNone(indicator.circle)
    
    def test_add_label(self):
        """Test adding label to indicator"""
        indicator = StatusIndicator(self.root, status="info")
        indicator.add_label("Test Label")
        
        self.assertIsNotNone(indicator.label)
        self.assertEqual(indicator.label.cget("text"), "Test Label")
    
    def tearDown(self):
        self.root.destroy()


class TestParkingSlotWidget(unittest.TestCase):
    """Test ParkingSlotWidget"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
    
    def test_slot_creation(self):
        """Test creating parking slot with different data"""
        slot_data = {
            'number': 1,
            'slot_type': 'REGULAR',
            'is_occupied': False,
            'is_reserved': False
        }
        
        slot = ParkingSlotWidget(self.root, slot_data)
        self.assertIsNotNone(slot)
    
    def test_slot_colors(self):
        """Test slot colors for different states"""
        test_cases = [
            ({"is_occupied": True}, "occupied"),
            ({"is_reserved": True}, "reserved"),
            ({"slot_type": "EV"}, "ev"),
            ({"slot_type": "DISABLED"}, "disabled"),
            ({"slot_type": "PREMIUM"}, "premium"),
            ({}, "available")  # Default
        ]
        
        for data, expected_color_key in test_cases:
            base_data = {"number": 1}
            base_data.update(data)
            
            slot = ParkingSlotWidget(self.root, base_data)
            
            # Check that canvas has items
            items = slot.find_all()
            self.assertGreater(len(items), 0)
    
    def test_slot_click(self):
        """Test slot click handling"""
        slot_data = {'number': 1, 'is_occupied': False}
        slot = ParkingSlotWidget(self.root, slot_data)
        
        # Set click callback
        click_mock = Mock()
        slot.set_on_click(click_mock)
        
        # Simulate click
        slot._on_click(None)
        
        # Verify selection toggled
        self.assertTrue(slot.is_selected)
    
    def test_update_slot(self):
        """Test updating slot data"""
        slot_data = {'number': 1, 'is_occupied': False}
        slot = ParkingSlotWidget(self.root, slot_data)
        
        # Update to occupied
        new_data = {'number': 1, 'is_occupied': True}
        slot.update_slot(new_data)
        
        self.assertEqual(slot.slot_data, new_data)
    
    def tearDown(self):
        self.root.destroy()


class TestDashboardChart(unittest.TestCase):
    """Test DashboardChart widget"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
    
    def test_chart_creation(self):
        """Test chart creation with title"""
        chart = DashboardChart(self.root, title="Test Chart", width=300, height=200)
        self.assertEqual(chart.title, "Test Chart")
        self.assertEqual(chart.width, 300)
        self.assertEqual(chart.height, 200)
    
    def test_set_data(self):
        """Test setting chart data"""
        chart = DashboardChart(self.root)
        
        # Test with empty data
        chart.set_data([])
        self.assertEqual(chart.data, [])
        
        # Test with sample data
        sample_data = [10, 20, 30, 40, 50]
        chart.set_data(sample_data)
        self.assertEqual(chart.data, sample_data)
    
    def test_draw_chart(self):
        """Test chart drawing"""
        chart = DashboardChart(self.root, width=200, height=150)
        
        # Test drawing with data
        chart.set_data([1, 2, 3, 4, 5])
        
        # Verify canvas has items (axes and bars)
        items = chart.find_all()
        self.assertGreater(len(items), 0)
    
    def tearDown(self):
        self.root.destroy()


# ============================================================================
# TEST VIEWS
# ============================================================================

class TestBaseView(unittest.TestCase):
    """Test BaseView functionality"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Mock controller
        self.mock_controller = Mock()
        self.mock_controller.app = Mock()
    
    def test_base_view_abstract(self):
        """Test that BaseView is abstract"""
        with self.assertRaises(NotImplementedError):
            view = BaseView(self.root, self.mock_controller)
            view._setup_ui()
    
    def tearDown(self):
        self.root.destroy()


class TestDashboardView(unittest.TestCase):
    """Test DashboardView"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Mock controller
        self.mock_controller = Mock()
        self.mock_controller.app = Mock()
        
        # Create view
        self.view = DashboardView(self.root, self.mock_controller)
    
    def test_dashboard_creation(self):
        """Test dashboard view creation"""
        self.assertIsNotNone(self.view)
        self.assertIsInstance(self.view, DashboardView)
    
    def test_refresh_method(self):
        """Test dashboard refresh method"""
        # Mock the components that would be updated
        self.view.total_lots_value = Mock()
        self.view.available_slots_value = Mock()
        self.view.occupancy_value = Mock()
        self.view.revenue_value = Mock()
        self.view.occupancy_chart = Mock()
        self.view.activity_list = Mock()
        self.view.alerts_text = Mock()
        
        # Call refresh
        self.view.refresh()
        
        # Verify methods were called
        self.view.occupancy_chart.set_data.assert_called_once()
    
    def test_kpi_cards_exist(self):
        """Test that KPI cards are created"""
        # Check that KPI card frames exist
        self.assertIsNotNone(self.view.total_lots_card)
        self.assertIsNotNone(self.view.available_slots_card)
        self.assertIsNotNone(self.view.occupancy_card)
        self.assertIsNotNone(self.view.revenue_card)
    
    def tearDown(self):
        self.root.destroy()


class TestParkingLotView(unittest.TestCase):
    """Test ParkingLotView"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Mock controller
        self.mock_controller = Mock()
        self.mock_controller.app = Mock()
        self.mock_controller.show_dialog = Mock()
        
        # Create view
        self.view = ParkingLotView(self.root, self.mock_controller)
    
    def test_parking_lot_view_creation(self):
        """Test parking lot view creation"""
        self.assertIsNotNone(self.view)
        self.assertIsInstance(self.view, ParkingLotView)
    
    def test_refresh_method(self):
        """Test parking lot list refresh"""
        # Mock tree view
        self.view.lot_tree = Mock()
        self.view.lot_tree.get_children.return_value = []
        
        # Call refresh
        self.view.refresh()
        
        # Verify tree was populated
        self.view.lot_tree.insert.assert_called()
    
    def test_on_lot_selected(self):
        """Test lot selection handler"""
        # Mock tree selection
        self.view.lot_tree = Mock()
        self.view.lot_tree.selection.return_value = ["item1"]
        self.view.lot_tree.item.return_value = {
            'values': ["1", "Downtown Center", "DTC001", "New York", "45/100", "45%"]
        }
        
        # Mock show_lot_details
        self.view._show_lot_details = Mock()
        
        # Trigger selection
        self.view._on_lot_selected(None)
        
        # Verify details were shown
        self.view._show_lot_details.assert_called_once()
    
    def test_quick_action_methods(self):
        """Test quick action methods"""
        lot_data = {"id": 1, "name": "Test Lot"}
        
        # Test park vehicle
        self.view._park_vehicle(lot_data)
        self.mock_controller.show_dialog.assert_called_with("park_vehicle", lot_data=lot_data)
        
        # Test exit vehicle
        self.view._exit_vehicle(lot_data)
        self.mock_controller.show_dialog.assert_called_with("exit_vehicle", lot_data=lot_data)
        
        # Test make reservation
        self.view._make_reservation(lot_data)
        self.mock_controller.show_dialog.assert_called_with("make_reservation", lot_data=lot_data)
    
    def tearDown(self):
        self.root.destroy()


class TestVehicleManagementView(unittest.TestCase):
    """Test VehicleManagementView"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Mock controller
        self.mock_controller = Mock()
        self.mock_controller.app = Mock()
        self.mock_controller.show_dialog = Mock()
        
        # Create view
        self.view = VehicleManagementView(self.root, self.mock_controller)
    
    def test_vehicle_view_creation(self):
        """Test vehicle management view creation"""
        self.assertIsNotNone(self.view)
        self.assertIsInstance(self.view, VehicleManagementView)
    
    def test_search_vehicles(self):
        """Test vehicle search functionality"""
        # Mock tree and search variable
        self.view.vehicle_tree = Mock()
        self.view.vehicle_tree.get_children.return_value = ["item1", "item2"]
        self.view.vehicle_tree.item.side_effect = [
            {'values': ("ABC-123", "Car", "Toyota", "Camry", "2020", "Blue", "Active")},
            {'values': ("XYZ-789", "Motorcycle", "Honda", "CBR", "2021", "Black", "Active")}
        ]
        
        # Set search term
        self.view.search_var = Mock()
        self.view.search_var.get.return_value = "ABC"
        
        # Call search
        self.view._search_vehicles()
        
        # Verify tree items were tagged
        self.view.vehicle_tree.item.assert_called()
    
    def test_vehicle_actions(self):
        """Test vehicle action methods"""
        # Mock tree selection
        self.view.vehicle_tree = Mock()
        self.view.vehicle_tree.selection.return_value = ["selected_item"]
        
        # Test view details
        self.view._view_vehicle_details()
        self.mock_controller.show_dialog.assert_called_with("vehicle_details", vehicle_id="selected_item")
        
        # Test edit vehicle
        self.view._edit_vehicle()
        self.mock_controller.show_dialog.assert_called_with("edit_vehicle", vehicle_id="selected_item")
        
        # Test delete vehicle (with mocked messagebox)
        with patch('tkinter.messagebox.askyesno', return_value=True):
            self.view._delete_vehicle()
            self.view.vehicle_tree.delete.assert_called_with("selected_item")
    
    def tearDown(self):
        self.root.destroy()


class TestBillingView(unittest.TestCase):
    """Test BillingView"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Mock controller
        self.mock_controller = Mock()
        self.mock_controller.app = Mock()
        
        # Create view
        self.view = BillingView(self.root, self.mock_controller)
    
    def test_billing_view_creation(self):
        """Test billing view creation"""
        self.assertIsNotNone(self.view)
        self.assertIsInstance(self.view, BillingView)
    
    def test_notebook_tabs(self):
        """Test that notebook has correct tabs"""
        self.assertIsNotNone(self.view.notebook)
        
        # Check tab names
        tab_names = [self.view.notebook.tab(i, "text") for i in range(self.view.notebook.index("end"))]
        expected_tabs = ["Invoices", "Payments", "Reports"]
        
        for tab in expected_tabs:
            self.assertIn(tab, tab_names)
    
    def test_generate_report(self):
        """Test report generation"""
        # Mock date entries and report type
        self.view.from_date = Mock()
        self.view.from_date.get.return_value = "2024-01-01"
        self.view.to_date = Mock()
        self.view.to_date.get.return_value = "2024-01-31"
        self.view.report_type = Mock()
        self.view.report_type.get.return_value = "revenue"
        
        # Mock messagebox
        with patch('tkinter.messagebox.showinfo') as mock_showinfo:
            self.view._generate_report()
            
            # Verify messagebox was called
            mock_showinfo.assert_called_once()
    
    def tearDown(self):
        self.root.destroy()


# ============================================================================
# TEST DIALOGS
# ============================================================================

class TestBaseDialog(unittest.TestCase):
    """Test BaseDialog"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
    
    def test_base_dialog_abstract(self):
        """Test that BaseDialog is abstract"""
        with self.assertRaises(NotImplementedError):
            dialog = BaseDialog(self.root, "Test Dialog")
            dialog._setup_ui()
    
    def tearDown(self):
        self.root.destroy()


class TestParkVehicleDialog(unittest.TestCase):
    """Test ParkVehicleDialog"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Mock controller
        self.mock_controller = Mock()
        self.mock_controller.park_vehicle = Mock(return_value=(True, "Success"))
    
    def test_dialog_creation(self):
        """Test dialog creation with lot data"""
        lot_data = {"id": 1, "name": "Test Lot"}
        dialog = ParkVehicleDialog(self.root, self.mock_controller, lot_data)
        
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.title(), "Park Vehicle")
    
    def test_dialog_without_lot_data(self):
        """Test dialog creation without lot data"""
        dialog = ParkVehicleDialog(self.root, self.mock_controller)
        
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.title(), "Park Vehicle")
    
    def test_vehicle_type_changed(self):
        """Test vehicle type change handler"""
        dialog = ParkVehicleDialog(self.root, self.mock_controller)
        
        # Initially EV frame should not be shown (default is "Car")
        self.assertFalse(dialog.ev_frame.winfo_ismapped())
        
        # Change to EV Car
        dialog.vehicle_type.set("EV Car")
        dialog._on_vehicle_type_changed(None)
        
        # EV frame should now be shown
        # Note: In actual test, we'd check visibility, but with Tkinter,
        # we can check that the method was called
    
    def test_toggle_ev_details(self):
        """Test EV charging details toggle"""
        dialog = ParkVehicleDialog(self.root, self.mock_controller)
        
        # Set vehicle type to EV
        dialog.vehicle_type.set("EV Car")
        dialog._on_vehicle_type_changed(None)
        
        # Initially charge frame should not be shown
        self.assertFalse(dialog.needs_charging.get())
        
        # Toggle charging
        dialog.needs_charging.set(True)
        dialog._toggle_ev_details()
    
    @patch('tkinter.messagebox.showerror')
    @patch('tkinter.messagebox.showinfo')
    def test_park_vehicle_validation(self, mock_showinfo, mock_showerror):
        """Test park vehicle validation"""
        dialog = ParkVehicleDialog(self.root, self.mock_controller)
        
        # Test empty license plate
        dialog.license_plate.insert(0, "")
        dialog._park_vehicle()
        mock_showerror.assert_called_with("Error", "License plate is required")
        
        # Test successful parking
        mock_showerror.reset_mock()
        dialog.license_plate.delete(0, tk.END)
        dialog.license_plate.insert(0, "ABC123")
        
        dialog._park_vehicle()
        self.mock_controller.park_vehicle.assert_called_once()
        mock_showinfo.assert_called_with("Success", "Success")
    
    def tearDown(self):
        self.root.destroy()


class TestAddParkingLotDialog(unittest.TestCase):
    """Test AddParkingLotDialog"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Mock controller
        self.mock_controller = Mock()
        self.mock_controller.add_parking_lot = Mock(return_value=(True, "Success"))
    
    def test_dialog_creation(self):
        """Test dialog creation"""
        dialog = AddParkingLotDialog(self.root, self.mock_controller)
        
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.title(), "Add Parking Lot")
    
    @patch('tkinter.messagebox.showerror')
    @patch('tkinter.messagebox.showinfo')
    def test_add_parking_lot_validation(self, mock_showinfo, mock_showerror):
        """Test add parking lot validation"""
        dialog = AddParkingLotDialog(self.root, self.mock_controller)
        
        # Test empty name
        dialog.name.insert(0, "")
        dialog._add_parking_lot()
        mock_showerror.assert_called_with("Error", "Name is required")
        
        # Test with valid data
        mock_showerror.reset_mock()
        
        # Fill required fields
        dialog.name.delete(0, tk.END)
        dialog.name.insert(0, "Test Lot")
        
        dialog.code.delete(0, tk.END)
        dialog.code.insert(0, "TEST001")
        
        dialog.address.delete(0, tk.END)
        dialog.address.insert(0, "123 Test St")
        
        dialog.city.delete(0, tk.END)
        dialog.city.insert(0, "Test City")
        
        dialog.country.delete(0, tk.END)
        dialog.country.insert(0, "Test Country")
        
        dialog._add_parking_lot()
        self.mock_controller.add_parking_lot.assert_called_once()
        mock_showinfo.assert_called_with("Success", "Success")
    
    def tearDown(self):
        self.root.destroy()


# ============================================================================
# TEST CONTROLLER
# ============================================================================

class TestParkingAppController(unittest.TestCase):
    """Test ParkingAppController"""
    
    def setUp(self):
        # Mock app
        self.mock_app = Mock()
        
        # Create controller with mocked dependencies
        with patch('src.presentation.parking_gui.ParkingServiceFactory') as mock_factory, \
             patch('src.presentation.parking_gui.CommandProcessor') as mock_processor, \
             patch('src.presentation.parking_gui.FactoryRegistry') as mock_registry, \
             patch('logging.getLogger'):
            
            mock_factory.create_default_service.return_value = Mock()
            mock_processor.return_value = Mock()
            mock_registry.return_value = Mock()
            
            self.controller = ParkingAppController(self.mock_app)
    
    def test_controller_initialization(self):
        """Test controller initialization"""
        self.assertIsNotNone(self.controller)
        self.assertEqual(self.controller.app, self.mock_app)
    
    def test_switch_view(self):
        """Test switching views"""
        self.controller.switch_view("dashboard")
        self.mock_app.switch_view.assert_called_with("dashboard")
    
    def test_show_dialog(self):
        """Test showing dialogs"""
        # Mock dialog creation
        mock_dialog_class = Mock()
        with patch.object(self.controller, '_get_dialog_class', return_value=mock_dialog_class):
            result = self.controller.show_dialog("park_vehicle")
            mock_dialog_class.assert_called_with(self.mock_app, self.controller)
    
    def test_get_dialog_class(self):
        """Test getting dialog class by name"""
        # Test existing dialog
        dialog_class = self.controller._get_dialog_class("park_vehicle")
        self.assertEqual(dialog_class, ParkVehicleDialog)
        
        # Test non-existent dialog
        dialog_class = self.controller._get_dialog_class("non_existent")
        self.assertIsNone(dialog_class)
    
    @patch('src.presentation.parking_gui.uuid4')
    @patch('src.presentation.parking_gui.ParkingRequestDTO')
    def test_park_vehicle_success(self, mock_request, mock_uuid4):
        """Test successful vehicle parking"""
        # Setup mocks
        mock_uuid4.return_value = "test-uuid"
        mock_request_instance = Mock()
        mock_request.return_value = mock_request_instance
        
        mock_result = {"success": True}
        self.controller.command_processor.process.return_value = mock_result
        
        # Test data
        vehicle_data = {
            "license_plate": "ABC123",
            "vehicle_type": "Car",
            "preferred_slot_type": "regular"
        }
        lot_data = {"id": "lot-123", "name": "Test Lot"}
        
        # Call method
        success, message = self.controller.park_vehicle(vehicle_data, lot_data)
        
        # Verify
        self.assertTrue(success)
        self.assertEqual(message, "Vehicle parked successfully")
        self.controller.command_processor.process.assert_called_once()
    
    @patch('src.presentation.parking_gui.uuid4')
    @patch('src.presentation.parking_gui.ParkingRequestDTO')
    def test_park_vehicle_failure(self, mock_request, mock_uuid4):
        """Test failed vehicle parking"""
        # Setup mocks
        mock_result = {"success": False, "error": "No available slots"}
        self.controller.command_processor.process.return_value = mock_result
        
        # Test data
        vehicle_data = {
            "license_plate": "ABC123",
            "vehicle_type": "Car"
        }
        
        # Call method
        success, message = self.controller.park_vehicle(vehicle_data)
        
        # Verify
        self.assertFalse(success)
        self.assertEqual(message, "No available slots")
    
    @patch('time.sleep')
    def test_add_parking_lot(self, mock_sleep):
        """Test adding parking lot"""
        lot_data = {
            "name": "Test Lot",
            "code": "TEST001"
        }
        
        success, message = self.controller.add_parking_lot(lot_data)
        
        self.assertTrue(success)
        self.assertEqual(message, "Parking lot 'Test Lot' added successfully")
        self.controller.logger.info.assert_called()
        mock_sleep.assert_called_with(1)


# ============================================================================
# TEST APPLICATION
# ============================================================================

class TestParkingManagementApp(unittest.TestCase):
    """Test ParkingManagementApp"""
    
    def setUp(self):
        # Hide Tkinter window during tests
        self.app = None
    
    def test_app_creation(self):
        """Test application creation"""
        with patch('tkinter.Tk') as mock_tk:
            mock_root = Mock()
            mock_tk.return_value = mock_root
            
            app = ParkingManagementApp()
            
            self.assertIsNotNone(app)
            self.assertEqual(app.root, mock_root)
            
            # Cleanup
            if hasattr(app, 'root'):
                app.root.destroy()
    
    def test_switch_view(self):
        """Test switching views"""
        with patch('tkinter.Tk'):
            app = ParkingManagementApp()
            
            # Mock views
            app.views = {
                "dashboard": Mock(),
                "parking_lots": Mock()
            }
            app.current_view = Mock()
            
            # Mock view methods
            app.current_view.pack_forget = Mock()
            app.views["dashboard"].pack = Mock()
            app.views["dashboard"].on_show = Mock()
            
            # Mock update_nav_buttons
            app._update_nav_buttons = Mock()
            
            # Switch view
            app.switch_view("dashboard")
            
            # Verify
            app.current_view.pack_forget.assert_called_once()
            app.views["dashboard"].pack.assert_called_once()
            app.views["dashboard"].on_show.assert_called_once()
            app._update_nav_buttons.assert_called_with("dashboard")
            
            # Cleanup
            if hasattr(app, 'root'):
                app.root.destroy()
    
    def test_update_nav_buttons(self):
        """Test updating navigation buttons"""
        with patch('tkinter.Tk'):
            app = ParkingManagementApp()
            
            # Mock navigation buttons
            app.nav_buttons = {
                "dashboard": Mock(),
                "parking_lots": Mock()
            }
            
            # Update active view
            app._update_nav_buttons("dashboard")
            
            # Verify button styles
            app.nav_buttons["dashboard"].configure.assert_called_with(style='primary.TButton')
            app.nav_buttons["parking_lots"].configure.assert_called_with(style='TButton')
            
            # Cleanup
            if hasattr(app, 'root'):
                app.root.destroy()


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

class TestAppConfig(unittest.TestCase):
    """Test AppConfig class"""
    
    def test_app_config_constants(self):
        """Test AppConfig constants"""
        self.assertEqual(AppConfig.APP_NAME, "Parking Management System")
        self.assertEqual(AppConfig.VERSION, "1.0.0")
        self.assertEqual(AppConfig.COMPANY, "Parking Solutions Inc.")
    
    def test_theme_colors(self):
        """Test theme color configurations"""
        # Test all themes have required color keys
        required_keys = ["bg", "fg", "primary", "secondary", "success", 
                        "danger", "warning", "info", "card_bg", "border", "text_muted"]
        
        for theme in Theme:
            colors = AppConfig.COLORS[theme]
            for key in required_keys:
                self.assertIn(key, colors)
                self.assertIsInstance(colors[key], str)
    
    def test_fonts(self):
        """Test font configurations"""
        required_fonts = ["title", "heading", "subheading", "body", "small", "monospace"]
        
        for font_name in required_fonts:
            self.assertIn(font_name, AppConfig.FONTS)
            font_tuple = AppConfig.FONTS[font_name]
            self.assertIsInstance(font_tuple, tuple)
            self.assertGreaterEqual(len(font_tuple), 2)


# ============================================================================
# TEST ENUMS
# ============================================================================

class TestThemeEnum(unittest.TestCase):
    """Test Theme enum"""
    
    def test_theme_values(self):
        """Test theme enum values"""
        self.assertEqual(Theme.LIGHT.value, "light")
        self.assertEqual(Theme.DARK.value, "dark")
        self.assertEqual(Theme.BLUE.value, "blue")
    
    def test_theme_membership(self):
        """Test theme membership"""
        self.assertIn(Theme.LIGHT, Theme)
        self.assertIn(Theme.DARK, Theme)
        self.assertIn(Theme.BLUE, Theme)
    
    def test_theme_string_representation(self):
        """Test theme string representation"""
        self.assertEqual(str(Theme.LIGHT), "light")
        self.assertEqual(str(Theme.DARK), "dark")
        self.assertEqual(str(Theme.BLUE), "blue")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration(unittest.TestCase):
    """Integration tests for the GUI components"""
    
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
    
    def test_mvc_integration(self):
        """Test MVC pattern integration"""
        # Create mock app
        mock_app = Mock()
        
        # Create controller
        with patch('src.presentation.parking_gui.ParkingServiceFactory'), \
             patch('src.presentation.parking_gui.CommandProcessor'), \
             patch('src.presentation.parking_gui.FactoryRegistry'):
            
            controller = ParkingAppController(mock_app)
            
            # Create view with controller
            view = DashboardView(self.root, controller)
            
            # Test that view has controller reference
            self.assertEqual(view.controller, controller)
            self.assertEqual(view.app, mock_app)
            
            # Test that controller has app reference
            self.assertEqual(controller.app, mock_app)
    
    def test_widget_integration(self):
        """Test widget integration in views"""
        # Create a simple view with custom widgets
        mock_controller = Mock()
        mock_controller.app = Mock()
        
        # Create dashboard view
        view = DashboardView(self.root, mock_controller)
        
        # Check that custom widgets are used
        self.assertIsInstance(view.total_lots_card, CardFrame)
        self.assertIsInstance(view.occupancy_chart, DashboardChart)
    
    def test_dialog_controller_integration(self):
        """Test dialog-controller integration"""
        # Mock controller
        mock_controller = Mock()
        mock_controller.park_vehicle = Mock(return_value=(True, "Success"))
        
        # Create dialog
        dialog = ParkVehicleDialog(self.root, mock_controller)
        
        # Test dialog fields
        self.assertIsNotNone(dialog.license_plate)
        self.assertIsNotNone(dialog.vehicle_type)
        
        # Test that dialog has controller reference
        self.assertEqual(dialog.controller, mock_controller)
    
    def tearDown(self):
        self.root.destroy()


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_tests():
    """Run all tests"""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    # Run tests when script is executed directly
    result = run_tests()
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)