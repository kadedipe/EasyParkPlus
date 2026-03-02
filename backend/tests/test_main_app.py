# File: tests/test_main_app.py
"""
Main application tests and integration tests.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tkinter as tk
import sys

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from src.presentation.parking_gui import main, ParkingManagementApp


class TestMainFunction(unittest.TestCase):
    """Test main application function"""
    
    @patch('src.presentation.parking_gui.ParkingManagementApp')
    @patch('src.presentation.parking_gui.logging.basicConfig')
    def test_main_function(self, mock_logging_config, mock_app_class):
        """Test main() function execution"""
        # Mock the app instance
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        
        # Call main
        main()
        
        # Verify logging was configured
        mock_logging_config.assert_called_once()
        
        # Verify app was created and run
        mock_app_class.assert_called_once()
        mock_app.run.assert_called_once()


class TestApplicationLifecycle(unittest.TestCase):
    """Test application lifecycle"""
    
    def setUp(self):
        self.app = None
    
    def test_app_initialization(self):
        """Test application initialization"""
        with patch('tkinter.Tk') as mock_tk, \
             patch('src.presentation.parking_gui.ParkingAppController') as mock_controller_class:
            
            mock_root = Mock()
            mock_tk.return_value = mock_root
            
            mock_controller = Mock()
            mock_controller_class.return_value = mock_controller
            
            # Create app
            app = ParkingManagementApp()
            
            # Verify initialization
            self.assertEqual(app.root, mock_root)
            mock_controller_class.assert_called_with(app)
            self.assertEqual(app.controller, mock_controller)
            
            # Cleanup
            if hasattr(app, 'root'):
                app.root.destroy()
    
    def test_app_cleanup(self):
        """Test application cleanup on close"""
        with patch('tkinter.Tk') as mock_tk, \
             patch('tkinter.messagebox.askokcancel', return_value=True):
            
            mock_root = Mock()
            mock_tk.return_value = mock_root
            
            app = ParkingManagementApp()
            app.on_closing()
            
            # Verify window would be destroyed
            # (Actual destruction happens in Tkinter mainloop)
            
            # Cleanup
            if hasattr(app, 'root'):
                app.root.destroy()


class TestErrorHandling(unittest.TestCase):
    """Test error handling in the application"""
    
    def test_service_initialization_error(self):
        """Test handling of service initialization errors"""
        with patch('tkinter.Tk') as mock_tk, \
             patch('tkinter.messagebox.showerror') as mock_showerror, \
             patch('src.presentation.parking_gui.ParkingServiceFactory.create_default_service', 
                   side_effect=Exception("Service init failed")):
            
            mock_root = Mock()
            mock_tk.return_value = mock_root
            
            # This should show an error but not crash
            try:
                app = ParkingManagementApp()
                # Cleanup if app was created
                if hasattr(app, 'root'):
                    app.root.destroy()
            except:
                pass  # App might fail to initialize, which is expected
            
            # Error message should have been shown
            mock_showerror.assert_called_once()
    
    def test_dialog_error_handling(self):
        """Test error handling in dialogs"""
        # Test that dialogs handle errors gracefully
        # (e.g., invalid input, service errors)
        
        with patch('tkinter.Tk') as mock_tk:
            mock_root = Mock()
            mock_tk.return_value = mock_root
            
            # Mock controller with failing park_vehicle
            mock_controller = Mock()
            mock_controller.park_vehicle.return_value = (False, "Service unavailable")
            
            # Create dialog
            from src.presentation.parking_gui import ParkVehicleDialog
            dialog = ParkVehicleDialog(mock_root, mock_controller)
            
            # Test with error response
            with patch('tkinter.messagebox.showerror') as mock_showerror:
                # Set up test data
                dialog.license_plate.insert(0, "ABC123")
                
                # Trigger park with error
                dialog._park_vehicle()
                
                # Should show error
                mock_showerror.assert_called_once()
            
            # Cleanup
            dialog.destroy()


if __name__ == "__main__":
    unittest.main(verbosity=2)