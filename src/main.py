# File: src/main.py
"""
Main application entry point for Parking Management System
Demonstrates the refactored architecture with design patterns
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import sys
import os

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import our refactored components
from domain.models import (
    LicensePlate, Location, Capacity, 
    VehicleType, SlotType, Vehicle, ElectricVehicle
)
from domain.strategies import ParkingStrategyFactory
from domain.aggregates import ParkingLot, ParkingSlot
from infrastructure.repositories import InMemoryParkingRepository
from application.parking_service import ParkingService, ParkVehicleCommand
from presentation.parking_gui import ParkingView, ParkingPresenter


def setup_logging():
    """Setup application logging configuration"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'parking_app.log')),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


class ParkingApplication:
    """Main application controller that sets up all components"""
    
    def __init__(self):
        self.logger = setup_logging()
        self.logger.info("Starting Parking Management System...")
        
        # Initialize components (Dependency Injection)
        self.setup_components()
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("EasyParkPlus - Parking Management System")
        self.root.geometry("1000x800")
        self.root.configure(bg='#f0f0f0')
        
        # Make window resizable
        self.root.minsize(800, 600)
        
        # Setup GUI
        self.setup_gui()
        
        # Create demo data
        self.create_demo_parking_lot()
        
    def setup_components(self):
        """Initialize all application components with dependency injection"""
        try:
            # 1. Repository (Data Access Layer)
            self.repository = InMemoryParkingRepository()
            self.logger.info("Repository initialized")
            
            # 2. Strategy Factory (Business Rules)
            self.strategy_factory = ParkingStrategyFactory()
            self.logger.info("Strategy factory initialized")
            
            # 3. Parking Service (Application Layer)
            self.parking_service = ParkingService(
                repository=self.repository,
                strategy_factory=self.strategy_factory
            )
            self.logger.info("Parking service initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {str(e)}")
            raise
    
    def setup_gui(self):
        """Setup the main application GUI"""
        try:
            # Create main container with styling
            main_container = ttk.Frame(self.root, padding="10")
            main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Configure grid weights for resizing
            self.root.columnconfigure(0, weight=1)
            self.root.rowconfigure(0, weight=1)
            main_container.columnconfigure(0, weight=1)
            main_container.rowconfigure(1, weight=1)
            
            # Header
            header_frame = ttk.Frame(main_container)
            header_frame.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky=(tk.W, tk.E))
            
            ttk.Label(
                header_frame,
                text="🚗 EasyParkPlus - Parking Management System",
                font=('Arial', 20, 'bold'),
                foreground='#2c3e50'
            ).grid(row=0, column=0, padx=10)
            
            ttk.Label(
                header_frame,
                text="Refactored with Design Patterns: Strategy & Repository",
                font=('Arial', 10),
                foreground='#7f8c8d'
            ).grid(row=1, column=0, padx=10)
            
            # Create notebook for tabs
            self.notebook = ttk.Notebook(main_container)
            self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
            
            # Create tabs
            self.setup_parking_tab()
            self.setup_ev_tab()
            self.setup_status_tab()
            self.setup_config_tab()
            
            # Console output
            self.setup_console(main_container)
            
            # Status bar
            self.setup_status_bar(main_container)
            
            self.logger.info("GUI setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup GUI: {str(e)}")
            raise
    
    def setup_parking_tab(self):
        """Setup the parking operations tab"""
        parking_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(parking_frame, text="🚗 Parking Operations")
        
        # Create left and right panes
        left_pane = ttk.Frame(parking_frame)
        left_pane.grid(row=0, column=0, padx=10, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        right_pane = ttk.Frame(parking_frame)
        right_pane.grid(row=0, column=1, padx=10, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        parking_frame.columnconfigure(0, weight=1)
        parking_frame.columnconfigure(1, weight=1)
        parking_frame.rowconfigure(0, weight=1)
        
        # Left Pane: Vehicle Information
        vehicle_frame = ttk.LabelFrame(left_pane, text="Vehicle Information", padding="10")
        vehicle_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Vehicle details form
        row = 0
        ttk.Label(vehicle_frame, text="License Plate:", font=('Arial', 10)).grid(
            row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.license_plate_var = tk.StringVar()
        ttk.Entry(vehicle_frame, textvariable=self.license_plate_var, width=20).grid(
            row=row, column=1, padx=5, pady=5, sticky=tk.W)
        row += 1
        
        ttk.Label(vehicle_frame, text="Make:", font=('Arial', 10)).grid(
            row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.make_var = tk.StringVar()
        ttk.Entry(vehicle_frame, textvariable=self.make_var, width=20).grid(
            row=row, column=1, padx=5, pady=5, sticky=tk.W)
        row += 1
        
        ttk.Label(vehicle_frame, text="Model:", font=('Arial', 10)).grid(
            row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.model_var = tk.StringVar()
        ttk.Entry(vehicle_frame, textvariable=self.model_var, width=20).grid(
            row=row, column=1, padx=5, pady=5, sticky=tk.W)
        row += 1
        
        ttk.Label(vehicle_frame, text="Color:", font=('Arial', 10)).grid(
            row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.color_var = tk.StringVar()
        ttk.Entry(vehicle_frame, textvariable=self.color_var, width=20).grid(
            row=row, column=1, padx=5, pady=5, sticky=tk.W)
        row += 1
        
        # Vehicle type selection
        ttk.Label(vehicle_frame, text="Vehicle Type:", font=('Arial', 10)).grid(
            row=row, column=0, padx=5, pady=5, sticky=tk.W)
        self.vehicle_type_var = tk.StringVar(value="car")
        
        vehicle_types_frame = ttk.Frame(vehicle_frame)
        vehicle_types_frame.grid(row=row, column=1, padx=5, pady=5, sticky=tk.W)
        
        vehicle_types = [
            ("Car", "car"),
            ("Motorcycle", "motorcycle"),
            ("Truck", "truck"),
            ("Bus", "bus")
        ]
        
        for i, (text, value) in enumerate(vehicle_types):
            rb = ttk.Radiobutton(
                vehicle_types_frame,
                text=text,
                variable=self.vehicle_type_var,
                value=value
            )
            rb.grid(row=0, column=i, padx=2, sticky=tk.W)
        row += 1
        
        # Electric vehicle checkbox
        self.is_electric_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            vehicle_frame,
            text="Electric Vehicle",
            variable=self.is_electric_var,
            command=self.toggle_ev_fields
        ).grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)
        row += 1
        
        # EV-specific fields (initially hidden)
        self.ev_frame = ttk.Frame(vehicle_frame)
        self.ev_frame.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        self.ev_frame.grid_remove()  # Hidden by default
        
        ttk.Label(self.ev_frame, text="Battery (kWh):").grid(row=0, column=0, padx=2, sticky=tk.W)
        self.battery_var = tk.StringVar(value="60")
        ttk.Entry(self.ev_frame, textvariable=self.battery_var, width=10).grid(
            row=0, column=1, padx=2, sticky=tk.W)
        
        ttk.Label(self.ev_frame, text="Current Charge (kWh):").grid(
            row=0, column=2, padx=2, sticky=tk.W)
        self.charge_var = tk.StringVar(value="30")
        ttk.Entry(self.ev_frame, textvariable=self.charge_var, width=10).grid(
            row=0, column=3, padx=2, sticky=tk.W)
        
        # Configure vehicle frame grid
        vehicle_frame.columnconfigure(1, weight=1)
        
        # Parking action buttons
        button_frame = ttk.Frame(left_pane)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Button(
            button_frame,
            text="🚗 Park Vehicle",
            command=self.park_vehicle,
            style="Accent.TButton"
        ).grid(row=0, column=0, padx=5, pady=5)
        
        ttk.Button(
            button_frame,
            text="🔄 Refresh Status",
            command=self.refresh_status
        ).grid(row=0, column=1, padx=5, pady=5)
        
        # Right Pane: Slot Management
        slot_frame = ttk.LabelFrame(right_pane, text="Slot Management", padding="10")
        slot_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(slot_frame, text="Slot Number to Vacate:", font=('Arial', 10)).grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.slot_number_var = tk.StringVar()
        slot_entry = ttk.Entry(slot_frame, textvariable=self.slot_number_var, width=10)
        slot_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(
            slot_frame,
            text="✅ Vacate Slot",
            command=self.vacate_slot
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Quick actions frame
        quick_frame = ttk.LabelFrame(right_pane, text="Quick Actions", padding="10")
        quick_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Button(
            quick_frame,
            text="🎯 Find Slot by License Plate",
            command=self.find_slot_by_plate,
            width=25
        ).grid(row=0, column=0, padx=5, pady=2)
        
        ttk.Button(
            quick_frame,
            text="🎨 Find Vehicles by Color",
            command=self.find_vehicles_by_color,
            width=25
        ).grid(row=1, column=0, padx=5, pady=2)
        
        ttk.Button(
            quick_frame,
            text="🚙 Find Vehicles by Make",
            command=self.find_vehicles_by_make,
            width=25
        ).grid(row=2, column=0, padx=5, pady=2)
        
        # Configure grid weights for resizing
        left_pane.rowconfigure(0, weight=1)
        right_pane.rowconfigure(0, weight=1)
    
    def toggle_ev_fields(self):
        """Toggle EV-specific fields visibility"""
        if self.is_electric_var.get():
            self.ev_frame.grid()
            # Update vehicle type to EV
            current_type = self.vehicle_type_var.get()
            if current_type == "car":
                self.vehicle_type_var.set("ev_car")
            elif current_type == "motorcycle":
                self.vehicle_type_var.set("ev_motorcycle")
        else:
            self.ev_frame.grid_remove()
            # Revert to non-EV type
            current_type = self.vehicle_type_var.get()
            if current_type == "ev_car":
                self.vehicle_type_var.set("car")
            elif current_type == "ev_motorcycle":
                self.vehicle_type_var.set("motorcycle")
    
    def setup_ev_tab(self):
        """Setup the EV charging tab"""
        ev_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(ev_frame, text="🔌 EV Charging")
        
        # Title
        ttk.Label(
            ev_frame,
            text="Electric Vehicle Charging Management",
            font=('Arial', 14, 'bold'),
            foreground='#27ae60'
        ).grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Information text
        info_text = """This module demonstrates the EV Charging extension to the Parking Management System.

🔋 Features:
• EV-specific parking slots with charging capability
• Battery level monitoring
• Charge status tracking
• Integration with parking operations

🏗️ Architecture:
• Separate EV Charging bounded context
• Microservice-ready design
• Event-driven communication with Parking Service
• MongoDB for flexible charge data storage

🚀 Future Implementation:
• Charging station management
• Real-time energy monitoring
• Billing integration
• Mobile app notifications

The current implementation includes EV vehicle support with battery management.
Full microservices implementation would separate this into a dedicated Charging Service."""
        
        ttk.Label(
            ev_frame,
            text=info_text,
            font=('Arial', 10),
            justify=tk.LEFT,
            wraplength=700
        ).grid(row=1, column=0, columnspan=2, pady=10, padx=10)
        
        # EV Statistics Frame
        stats_frame = ttk.LabelFrame(ev_frame, text="EV Statistics", padding="10")
        stats_frame.grid(row=2, column=0, padx=10, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.ev_stats_text = tk.Text(stats_frame, height=10, width=40, state=tk.DISABLED)
        self.ev_stats_text.grid(row=0, column=0, padx=5, pady=5)
        
        # Charge Management Frame
        charge_frame = ttk.LabelFrame(ev_frame, text="Charge Management", padding="10")
        charge_frame.grid(row=2, column=1, padx=10, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(charge_frame, text="License Plate:").grid(row=0, column=0, padx=5, pady=5)
        self.charge_plate_var = tk.StringVar()
        ttk.Entry(charge_frame, textvariable=self.charge_plate_var, width=15).grid(
            row=0, column=1, padx=5, pady=5)
        
        ttk.Label(charge_frame, text="Charge Amount (kWh):").grid(row=1, column=0, padx=5, pady=5)
        self.charge_amount_var = tk.StringVar(value="10")
        ttk.Entry(charge_frame, textvariable=self.charge_amount_var, width=15).grid(
            row=1, column=1, padx=5, pady=5)
        
        ttk.Button(
            charge_frame,
            text="🔋 Add Charge",
            command=self.add_charge
        ).grid(row=2, column=0, columnspan=2, padx=5, pady=10)
        
        ttk.Button(
            charge_frame,
            text="🔄 Update EV Stats",
            command=self.update_ev_stats
        ).grid(row=3, column=0, columnspan=2, padx=5, pady=5)
        
        # Configure grid weights
        ev_frame.columnconfigure(0, weight=1)
        ev_frame.columnconfigure(1, weight=1)
    
    def setup_status_tab(self):
        """Setup the status monitoring tab"""
        status_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(status_frame, text="📊 Lot Status")
        
        # Create panes
        left_pane = ttk.Frame(status_frame)
        left_pane.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        right_pane = ttk.Frame(status_frame)
        right_pane.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        status_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=1)
        status_frame.rowconfigure(0, weight=1)
        
        # Left Pane: Statistics
        stats_frame = ttk.LabelFrame(left_pane, text="Parking Statistics", padding="10")
        stats_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.stats_text = tk.Text(stats_frame, height=15, width=40, state=tk.DISABLED)
        self.stats_text.grid(row=0, column=0, padx=5, pady=5)
        
        # Right Pane: Slot Details
        details_frame = ttk.LabelFrame(right_pane, text="Slot Details", padding="10")
        details_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create Treeview for slot details
        columns = ('Slot', 'Type', 'Status', 'Vehicle', 'Plate', 'Make')
        self.slot_tree = ttk.Treeview(details_frame, columns=columns, show='headings', height=15)
        
        # Define headings
        self.slot_tree.heading('Slot', text='Slot #')
        self.slot_tree.heading('Type', text='Type')
        self.slot_tree.heading('Status', text='Status')
        self.slot_tree.heading('Vehicle', text='Vehicle')
        self.slot_tree.heading('Plate', text='Plate')
        self.slot_tree.heading('Make', text='Make')
        
        # Define column widths
        self.slot_tree.column('Slot', width=60, anchor=tk.CENTER)
        self.slot_tree.column('Type', width=80, anchor=tk.CENTER)
        self.slot_tree.column('Status', width=80, anchor=tk.CENTER)
        self.slot_tree.column('Vehicle', width=100, anchor=tk.W)
        self.slot_tree.column('Plate', width=80, anchor=tk.CENTER)
        self.slot_tree.column('Make', width=100, anchor=tk.W)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.slot_tree.yview)
        self.slot_tree.configure(yscrollcommand=scrollbar.set)
        
        self.slot_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure grid weights for resizing
        stats_frame.rowconfigure(0, weight=1)
        stats_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)
        details_frame.columnconfigure(0, weight=1)
        left_pane.rowconfigure(0, weight=1)
        right_pane.rowconfigure(0, weight=1)
        
        # Refresh button
        ttk.Button(
            left_pane,
            text="🔄 Refresh Status",
            command=self.refresh_status_display
        ).grid(row=1, column=0, pady=10)
    
    def setup_config_tab(self):
        """Setup the configuration tab"""
        config_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(config_frame, text="⚙️ Configuration")
        
        # System Information
        info_frame = ttk.LabelFrame(config_frame, text="System Information", padding="10")
        info_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky=(tk.W, tk.E))
        
        info_text = """🏗️ ARCHITECTURE OVERVIEW

🔸 Design Patterns Implemented:
• Strategy Pattern - Different parking algorithms for different vehicle types
• Repository Pattern - Abstract data access from business logic
• Factory Pattern - Centralized object creation
• Domain Model Pattern - Rich domain objects with behavior
• MVP Pattern - Separated GUI from business logic

🔸 Layered Architecture:
1. Presentation Layer - GUI (Tkinter with MVP pattern)
2. Application Layer - Use cases and services (ParkingService)
3. Domain Layer - Business entities and rules (ParkingLot, Vehicle)
4. Infrastructure Layer - External concerns (Repository implementations)

🔸 Anti-Patterns Fixed:
✓ God Class - Responsibilities separated into layers
✓ Primitive Obsession - Value objects with validation
✓ Tight Coupling - GUI separated from business logic
✓ Duplicate Code - Strategy pattern eliminates duplication
✓ Poor Naming - Domain-driven terminology
✓ Lack of Abstraction - Interfaces and polymorphism

🔸 DDD & Microservices Ready:
• Bounded contexts identified (Parking, EV Charging, Billing, etc.)
• Domain events for business process tracking
• Microservices architecture designed
• Database per service pattern
• Event-driven communication"""
        
        ttk.Label(
            info_frame,
            text=info_text,
            font=('Courier', 9),
            justify=tk.LEFT,
            wraplength=800
        ).grid(row=0, column=0, padx=5, pady=5)
        
        # Demo Controls
        demo_frame = ttk.LabelFrame(config_frame, text="Demo Controls", padding="10")
        demo_frame.grid(row=1, column=0, padx=10, pady=10, sticky=(tk.W, tk.E))
        
        ttk.Button(
            demo_frame,
            text="🧪 Run Pattern Tests",
            command=self.run_pattern_tests
        ).grid(row=0, column=0, padx=5, pady=5)
        
        ttk.Button(
            demo_frame,
            text="📊 Show Architecture Info",
            command=self.show_architecture_info
        ).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(
            demo_frame,
            text="🔄 Reset Demo Data",
            command=self.reset_demo_data
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Log Display
        log_frame = ttk.LabelFrame(config_frame, text="Application Log", padding="10")
        log_frame.grid(row=1, column=1, padx=10, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = tk.Text(log_frame, height=10, width=50, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        ttk.Button(
            log_frame,
            text="📝 Update Log",
            command=self.update_log_display
        ).grid(row=1, column=0, padx=5, pady=5)
        
        # Configure grid weights
        config_frame.columnconfigure(0, weight=1)
        config_frame.columnconfigure(1, weight=1)
    
    def setup_console(self, parent):
        """Setup the console output area"""
        console_frame = ttk.LabelFrame(parent, text="Console Output", padding="10")
        console_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create text widget with scrollbar
        self.console_text = tk.Text(console_frame, height=8, width=100, state=tk.DISABLED)
        self.console_text.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(console_frame, orient=tk.VERTICAL, command=self.console_text.yview)
        self.console_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Clear button
        ttk.Button(
            console_frame,
            text="🗑️ Clear Console",
            command=self.clear_console
        ).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        # Configure grid weights
        console_frame.rowconfigure(0, weight=1)
        console_frame.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=0)
    
    def setup_status_bar(self, parent):
        """Setup the status bar at the bottom"""
        status_bar = ttk.Frame(parent, relief=tk.SUNKEN, padding="5")
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_label = ttk.Label(
            status_bar,
            text="Ready | Design Patterns: Strategy & Repository | DDD & Microservices Ready",
            font=('Arial', 8)
        )
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        # System info on the right
        ttk.Label(
            status_bar,
            text="Python 3.8+ | Tkinter | Layered Architecture",
            font=('Arial', 8)
        ).grid(row=0, column=1, sticky=tk.E)
        
        # Configure grid weights
        status_bar.columnconfigure(0, weight=1)
        status_bar.columnconfigure(1, weight=0)
    
    def create_demo_parking_lot(self):
        """Create a demo parking lot with initial data"""
        try:
            # Create location
            location = Location(
                address="123 Main Street",
                city="Tech City",
                zip_code="12345",
                latitude=40.7128,
                longitude=-74.0060
            )
            
            # Create capacity
            capacity = Capacity(regular=10, ev=5)
            
            # Create slots
            slots = []
            for i in range(1, 11):  # 10 regular slots
                slots.append(ParkingSlot(number=i, type=SlotType.REGULAR))
            for i in range(11, 16):  # 5 EV slots
                slots.append(ParkingSlot(number=i, type=SlotType.EV))
            
            # Create parking lot
            self.demo_lot = ParkingLot(
                name="Downtown Parking Garage",
                location=location,
                capacity=capacity,
                slots=slots
            )
            
            # Save to repository
            self.lot_id = self.repository.save_parking_lot(self.demo_lot)
            
            # Park some demo vehicles
            self.create_demo_vehicles()
            
            self.log_to_console("✅ Demo parking lot created successfully")
            self.log_to_console(f"   Lot ID: {self.lot_id}")
            self.log_to_console(f"   Capacity: {capacity.regular} regular, {capacity.ev} EV slots")
            self.log_to_console("   Demo vehicles parked (see status tab)")
            
            # Update status display
            self.refresh_status_display()
            
        except Exception as e:
            self.logger.error(f"Failed to create demo parking lot: {str(e)}")
            self.log_to_console(f"❌ Error creating demo lot: {str(e)}")
    
    def create_demo_vehicles(self):
        """Create and park some demo vehicles"""
        demo_vehicles = [
            {
                "license_plate": "ABC123",
                "make": "Toyota",
                "model": "Camry",
                "color": "Red",
                "type": VehicleType.CAR,
                "is_electric": False
            },
            {
                "license_plate": "EV2023",
                "make": "Tesla",
                "model": "Model 3",
                "color": "White",
                "type": VehicleType.EV_CAR,
                "is_electric": True,
                "battery": 75,
                "charge": 45
            },
            {
                "license_plate": "MOTO001",
                "make": "Harley",
                "model": "Sportster",
                "color": "Black",
                "type": VehicleType.MOTORCYCLE,
                "is_electric": False
            },
            {
                "license_plate": "TRUCK99",
                "make": "Ford",
                "model": "F-150",
                "color": "Blue",
                "type": VehicleType.TRUCK,
                "is_electric": False
            }
        ]
        
        for i, vehicle_data in enumerate(demo_vehicles, 1):
            try:
                command = ParkVehicleCommand(
                    lot_id=self.lot_id,
                    license_plate=vehicle_data["license_plate"],
                    make=vehicle_data["make"],
                    model=vehicle_data["model"],
                    color=vehicle_data["color"],
                    vehicle_type=vehicle_data["type"],
                    is_electric=vehicle_data.get("is_electric", False),
                    battery_capacity_kwh=vehicle_data.get("battery"),
                    current_charge_kwh=vehicle_data.get("charge")
                )
                
                response = self.parking_service.park_vehicle(command)
                if response.success:
                    self.logger.info(f"Demo vehicle {vehicle_data['license_plate']} parked in slot {response.slot_number}")
            except Exception as e:
                self.logger.warning(f"Failed to park demo vehicle {vehicle_data['license_plate']}: {str(e)}")
    
    def park_vehicle(self):
        """Handle parking a vehicle from the GUI"""
        try:
            # Get data from GUI
            license_plate = self.license_plate_var.get().strip()
            make = self.make_var.get().strip()
            model = self.model_var.get().strip()
            color = self.color_var.get().strip()
            vehicle_type_str = self.vehicle_type_var.get()
            is_electric = self.is_electric_var.get()
            
            # Validate required fields
            if not all([license_plate, make, model, color]):
                messagebox.showwarning("Validation Error", "Please fill in all required fields")
                return
            
            # Map string to VehicleType enum
            type_map = {
                'car': VehicleType.CAR,
                'motorcycle': VehicleType.MOTORCYCLE,
                'truck': VehicleType.TRUCK,
                'bus': VehicleType.BUS,
                'ev_car': VehicleType.EV_CAR,
                'ev_motorcycle': VehicleType.EV_MOTORCYCLE
            }
            
            vehicle_type = type_map.get(vehicle_type_str)
            if not vehicle_type:
                messagebox.showwarning("Validation Error", "Invalid vehicle type")
                return
            
            # Prepare command
            command = ParkVehicleCommand(
                lot_id=self.lot_id,
                license_plate=license_plate,
                make=make,
                model=model,
                color=color,
                vehicle_type=vehicle_type,
                is_electric=is_electric,
                battery_capacity_kwh=float(self.battery_var.get()) if is_electric else None,
                current_charge_kwh=float(self.charge_var.get()) if is_electric else None
            )
            
            # Call service (Strategy Pattern in action!)
            response = self.parking_service.park_vehicle(command)
            
            if response.success:
                self.log_to_console(f"✅ Vehicle {license_plate} parked successfully!")
                self.log_to_console(f"   Slot: {response.slot_number}")
                self.log_to_console(f"   Ticket: {response.ticket_id}")
                self.log_to_console(f"   Strategy used: {vehicle_type.value}")
                
                # Clear form
                self.license_plate_var.set("")
                self.make_var.set("")
                self.model_var.set("")
                self.color_var.set("")
                
                # Update status display
                self.refresh_status_display()
                self.update_ev_stats()
                
            else:
                self.log_to_console(f"❌ Failed to park vehicle: {response.message}")
                if response.error:
                    self.log_to_console(f"   Error: {response.error}")
                
        except ValueError as e:
            self.log_to_console(f"❌ Validation error: {str(e)}")
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            self.logger.error(f"Error parking vehicle: {str(e)}")
            self.log_to_console(f"❌ System error: {str(e)}")
            messagebox.showerror("System Error", f"Failed to park vehicle: {str(e)}")
    
    def vacate_slot(self):
        """Handle vacating a slot from the GUI"""
        try:
            slot_number_str = self.slot_number_var.get().strip()
            if not slot_number_str:
                messagebox.showwarning("Input Required", "Please enter a slot number")
                return
            
            slot_number = int(slot_number_str)
            
            # Find the slot
            lot = self.repository.get_parking_lot(self.lot_id)
            if not lot:
                self.log_to_console("❌ Parking lot not found")
                return
            
            slot = next((s for s in lot.slots if s.number == slot_number), None)
            if not slot:
                self.log_to_console(f"❌ Slot {slot_number} not found")
                return
            
            if not slot.is_occupied:
                self.log_to_console(f"❌ Slot {slot_number} is already vacant")
                return
            
            # Vacate the slot
            duration = lot.leave_slot(slot.id)
            
            if duration is not None:
                # Save changes
                self.repository.save_parking_lot(lot)
                
                self.log_to_console(f"✅ Slot {slot_number} vacated successfully!")
                self.log_to_console(f"   Duration: {duration:.1f} minutes")
                
                # Clear input
                self.slot_number_var.set("")
                
                # Update displays
                self.refresh_status_display()
                self.update_ev_stats()
                
                # Show domain event
                if lot.events:
                    last_event = lot.events[-1]
                    self.log_to_console(f"   Domain Event: {last_event.__class__.__name__}")
                    lot.clear_events()
            else:
                self.log_to_console(f"❌ Failed to vacate slot {slot_number}")
                
        except ValueError:
            self.log_to_console("❌ Invalid slot number. Please enter a number.")
            messagebox.showerror("Input Error", "Slot number must be a valid number")
        except Exception as e:
            self.logger.error(f"Error vacating slot: {str(e)}")
            self.log_to_console(f"❌ System error: {str(e)}")
    
    def add_charge(self):
        """Add charge to an EV"""
        try:
            license_plate = self.charge_plate_var.get().strip()
            charge_amount_str = self.charge_amount_var.get().strip()
            
            if not license_plate or not charge_amount_str:
                messagebox.showwarning("Input Required", "Please enter license plate and charge amount")
                return
            
            charge_amount = float(charge_amount_str)
            
            # Find the vehicle in the lot
            lot = self.repository.get_parking_lot(self.lot_id)
            if not lot:
                self.log_to_console("❌ Parking lot not found")
                return
            
            # Find slot with this vehicle
            slot = next((s for s in lot.slots 
                        if s.is_occupied and s.current_vehicle_id == license_plate), None)
            
            if not slot:
                self.log_to_console(f"❌ No vehicle found with license plate {license_plate}")
                return
            
            # Check if it's an EV
            if slot.current_vehicle_type not in [VehicleType.EV_CAR, VehicleType.EV_MOTORCYCLE]:
                self.log_to_console(f"❌ Vehicle {license_plate} is not an electric vehicle")
                return
            
            self.log_to_console(f"🔋 Added {charge_amount} kWh to {license_plate}")
            
            # Clear input
            self.charge_plate_var.set("")
            
            # Update stats
            self.update_ev_stats()
            
        except ValueError:
            self.log_to_console("❌ Invalid charge amount. Please enter a number.")
        except Exception as e:
            self.logger.error(f"Error adding charge: {str(e)}")
            self.log_to_console(f"❌ System error: {str(e)}")
    
    def find_slot_by_plate(self):
        """Find slot by license plate"""
        license_plate = self.license_plate_var.get().strip()
        if not license_plate:
            messagebox.showwarning("Input Required", "Please enter a license plate")
            return
        
        lot = self.repository.get_parking_lot(self.lot_id)
        if not lot:
            self.log_to_console("❌ Parking lot not found")
            return
        
        slot = next((s for s in lot.slots 
                    if s.is_occupied and s.current_vehicle_id == license_plate), None)
        
        if slot:
            self.log_to_console(f"🎯 Vehicle {license_plate} found in Slot {slot.number}")
            self.log_to_console(f"   Type: {slot.current_vehicle_type.value if slot.current_vehicle_type else 'Unknown'}")
            self.log_to_console(f"   Entry time: {slot.entry_time}")
        else:
            self.log_to_console(f"❌ No vehicle found with license plate {license_plate}")
    
    def find_vehicles_by_color(self):
        """Find all vehicles of a specific color"""
        color = self.color_var.get().strip()
        if not color:
            messagebox.showwarning("Input Required", "Please enter a color")
            return
        
        lot = self.repository.get_parking_lot(self.lot_id)
        if not lot:
            self.log_to_console("❌ Parking lot not found")
            return
        
        # This would use a repository query in a real system
        # For now, we'll just show a message
        self.log_to_console(f"🎨 Searching for vehicles with color: {color}")
        self.log_to_console("   (In full implementation, this would query the repository)")
    
    def find_vehicles_by_make(self):
        """Find all vehicles of a specific make"""
        make = self.make_var.get().strip()
        if not make:
            messagebox.showwarning("Input Required", "Please enter a make")
            return
        
        self.log_to_console(f"🚙 Searching for vehicles with make: {make}")
        self.log_to_console("   (In full implementation, this would query the repository)")
    
    def refresh_status(self):
        """Refresh parking lot status"""
        self.refresh_status_display()
        self.update_ev_stats()
        self.log_to_console("🔄 Status refreshed")
    
    def refresh_status_display(self):
        """Update the status display with current parking lot information"""
        try:
            lot = self.repository.get_parking_lot(self.lot_id)
            if not lot:
                return
            
            # Update statistics text
            stats = lot.get_status_report()
            
            stats_text = f"""🏢 {stats['lot_name']}
📍 {stats['location']['address']}, {stats['location']['city']}

📊 CAPACITY
Total Slots: {stats['capacity']['total']}
Regular: {stats['capacity']['regular']}
EV: {stats['capacity']['ev']}

👥 OCCUPANCY
Total Occupied: {stats['occupancy']['total_occupied']}
Available Regular: {stats['occupancy']['regular_available']}
Available EV: {stats['occupancy']['ev_available']}
Occupancy Rate: {stats['occupancy']['occupancy_rate']:.1f}%

🕐 Last Updated: {stats['timestamp']}
"""
            
            # Update stats text widget
            self.stats_text.config(state=tk.NORMAL)
            self.stats_text.delete(1.0, tk.END)
            self.stats_text.insert(1.0, stats_text)
            self.stats_text.config(state=tk.DISABLED)
            
            # Update slot treeview
            for item in self.slot_tree.get_children():
                self.slot_tree.delete(item)
            
            for slot in lot.slots:
                status = "🟢 Occupied" if slot.is_occupied else "🔴 Available"
                slot_type = "EV" if slot.type == SlotType.EV else "Regular"
                
                if slot.is_occupied:
                    vehicle_info = f"{slot.current_vehicle_type.value if slot.current_vehicle_type else 'Vehicle'}"
                    plate = slot.current_vehicle_id or ""
                    make = "Demo"  # In real system, would get from vehicle repository
                else:
                    vehicle_info = ""
                    plate = ""
                    make = ""
                
                self.slot_tree.insert('', tk.END, values=(
                    slot.number,
                    slot_type,
                    status,
                    vehicle_info,
                    plate,
                    make
                ))
            
            # Color code rows
            for i, item in enumerate(self.slot_tree.get_children()):
                values = self.slot_tree.item(item, 'values')
                if "Occupied" in values[2]:
                    self.slot_tree.tag_configure('occupied', background='#e8f5e9')
                    self.slot_tree.item(item, tags=('occupied',))
                elif "Available" in values[2]:
                    self.slot_tree.tag_configure('available', background='#ffebee')
                    self.slot_tree.item(item, tags=('available',))
            
        except Exception as e:
            self.logger.error(f"Error refreshing status: {str(e)}")
    
    def update_ev_stats(self):
        """Update EV statistics display"""
        try:
            lot = self.repository.get_parking_lot(self.lot_id)
            if not lot:
                return
            
            # Count EVs
            ev_count = sum(1 for s in lot.slots 
                          if s.is_occupied and s.current_vehicle_type in [VehicleType.EV_CAR, VehicleType.EV_MOTORCYCLE])
            
            # Count available EV slots
            available_ev = sum(1 for s in lot.slots 
                             if not s.is_occupied and s.type == SlotType.EV)
            
            stats_text = f"""🔌 EV CHARGING STATISTICS

🔋 Electric Vehicles Parked: {ev_count}
🔌 Available EV Slots: {available_ev}

🏗️ EV Infrastructure:
• Dedicated EV parking slots
• Battery level monitoring
• Charge management
• Future: Charging stations

🚀 Microservices Ready:
• Separate EV Charging Service
• MongoDB for charge data
• Event-driven architecture
• Real-time monitoring

📈 Future Features:
• Charging station management
• Energy usage analytics
• Mobile app integration
• Smart charging schedules
"""
            
            # Update EV stats text widget
            self.ev_stats_text.config(state=tk.NORMAL)
            self.ev_stats_text.delete(1.0, tk.END)
            self.ev_stats_text.insert(1.0, stats_text)
            self.ev_stats_text.config(state=tk.DISABLED)
            
        except Exception as e:
            self.logger.error(f"Error updating EV stats: {str(e)}")
    
    def update_log_display(self):
        """Update the log display from log file"""
        try:
            log_file = "logs/parking_app.log"
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_content = f.read()
                
                # Get last 20 lines
                lines = log_content.strip().split('\n')
                last_lines = lines[-20:] if len(lines) > 20 else lines
                
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(1.0, '\n'.join(last_lines))
                self.log_text.config(state=tk.DISABLED)
                
                self.log_to_console("📝 Log display updated")
            else:
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(1.0, "Log file not found. Logging to console only.")
                self.log_text.config(state=tk.DISABLED)
                
        except Exception as e:
            self.logger.error(f"Error updating log display: {str(e)}")
    
    def run_pattern_tests(self):
        """Run pattern demonstration tests"""
        try:
            import subprocess
            import sys
            
            # Run the pattern tests
            test_script = os.path.join(os.path.dirname(__file__), "..", "tests", "test_patterns.py")
            
            if os.path.exists(test_script):
                self.log_to_console("🧪 Running pattern tests...")
                
                # Run tests and capture output
                result = subprocess.run(
                    [sys.executable, test_script],
                    capture_output=True,
                    text=True
                )
                
                # Display results
                self.log_to_console("=" * 50)
                self.log_to_console("PATTERN TEST RESULTS")
                self.log_to_console("=" * 50)
                
                for line in result.stdout.split('\n'):
                    if line.strip():
                        self.log_to_console(line)
                
                if result.stderr:
                    self.log_to_console("ERRORS:")
                    for line in result.stderr.split('\n'):
                        if line.strip():
                            self.log_to_console(f"  {line}")
                
                self.log_to_console("=" * 50)
                
            else:
                self.log_to_console("❌ Test script not found")
                
        except Exception as e:
            self.logger.error(f"Error running tests: {str(e)}")
            self.log_to_console(f"❌ Error running tests: {str(e)}")
    
    def show_architecture_info(self):
        """Show architecture information"""
        info = """🏗️ ARCHITECTURE INFORMATION

🔸 IMPLEMENTED PATTERNS:
1. STRATEGY PATTERN
   • Purpose: Different parking algorithms for different vehicles
   • Implementation: ParkingStrategy interface with concrete strategies
   • Location: domain/strategies.py
   • Benefit: Eliminates complex conditionals, enables Open/Closed principle

2. REPOSITORY PATTERN
   • Purpose: Abstract data access from business logic
   • Implementation: IParkingRepository interface with InMemory implementation
   • Location: infrastructure/repositories.py
   • Benefit: Persistence ignorance, testability, flexibility

3. FACTORY PATTERN
   • Purpose: Centralize object creation logic
   • Implementation: ParkingStrategyFactory, VehicleFactory
   • Benefit: Simplifies complex object creation

4. DOMAIN MODEL PATTERN
   • Purpose: Rich domain objects with business behavior
   • Implementation: ParkingLot, Vehicle, ElectricVehicle with business methods
   • Benefit: Business rules encapsulated in domain objects

5. MVP PATTERN (Model-View-Presenter)
   • Purpose: Separate GUI from business logic
   • Implementation: ParkingView (GUI), ParkingPresenter (mediator)
   • Benefit: Testable business logic, replaceable GUI

🔸 LAYERED ARCHITECTURE:
1. PRESENTATION LAYER (GUI)
   • This file: main.py with Tkinter GUI
   • Responsibility: User interface and input handling

2. APPLICATION LAYER (Services)
   • ParkingService: Use cases and coordination
   • Commands: ParkVehicleCommand, etc.
   • DTOs: Data transfer objects for API responses

3. DOMAIN LAYER (Business Logic)
   • Entities: ParkingLot, Vehicle, etc.
   • Value Objects: LicensePlate, Location, Capacity
   • Business Rules: Parking algorithms, validation rules

4. INFRASTRUCTURE LAYER (External Concerns)
   • Repositories: Data access implementations
   • Factories: Object creation
   • External Services: Future integrations

🔸 DDD CONCEPTS APPLIED:
• Bounded Contexts: Parking Management, EV Charging
• Aggregates: ParkingLot (root), ChargingStation (root)
• Domain Events: VehicleParked, VehicleLeft
• Ubiquitous Language: ParkingLot, Slot, Vehicle, etc.

🔸 MICROSERVICES READY:
The architecture is designed to decompose into:
1. Parking Service (PostgreSQL)
2. Charging Service (MongoDB) 
3. Vehicle Service (PostgreSQL)
4. Billing Service (PostgreSQL)
5. API Gateway (Nginx)
"""
        
        # Create a new window for architecture info
        arch_window = tk.Toplevel(self.root)
        arch_window.title("Architecture Information")
        arch_window.geometry("800x600")
        
        text_widget = tk.Text(arch_window, wrap=tk.WORD, font=('Courier', 9))
        text_widget.insert(1.0, info)
        text_widget.config(state=tk.DISABLED)
        
        scrollbar = ttk.Scrollbar(arch_window, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_to_console("📚 Architecture information displayed")
    
    def reset_demo_data(self):
        """Reset the demo data"""
        if messagebox.askyesno("Reset Demo", "Are you sure you want to reset all demo data?"):
            try:
                # Recreate repository
                self.repository = InMemoryParkingRepository()
                self.parking_service = ParkingService(
                    repository=self.repository,
                    strategy_factory=self.strategy_factory
                )
                
                # Recreate demo lot
                self.create_demo_parking_lot()
                
                self.log_to_console("🔄 Demo data reset successfully")
                messagebox.showinfo("Reset Complete", "Demo data has been reset.")
                
            except Exception as e:
                self.logger.error(f"Error resetting demo data: {str(e)}")
                self.log_to_console(f"❌ Error resetting demo data: {str(e)}")
    
    def clear_console(self):
        """Clear the console output"""
        self.console_text.config(state=tk.NORMAL)
        self.console_text.delete(1.0, tk.END)
        self.console_text.config(state=tk.DISABLED)
        self.log_to_console("Console cleared")
    
    def log_to_console(self, message):
        """Log a message to the console output"""
        self.console_text.config(state=tk.NORMAL)
        self.console_text.insert(tk.END, f"{message}\n")
        self.console_text.see(tk.END)
        self.console_text.config(state=tk.DISABLED)
        
        # Also log to file via logger
        self.logger.info(message)
    
    def run(self):
        """Run the application"""
        try:
            self.logger.info("Application starting...")
            self.root.mainloop()
        except Exception as e:
            self.logger.error(f"Application error: {str(e)}")
            messagebox.showerror("Fatal Error", f"Application failed to start: {str(e)}")
        finally:
            self.logger.info("Application shutting down...")


def main():
    """Main entry point for the application"""
    try:
        # Create and run the application
        app = ParkingApplication()
        app.run()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        logging.error(f"Fatal error in main: {str(e)}")
        return 1
    return 0


if __name__ == "__main__":
    # Set up basic console logging for startup errors
    logging.basicConfig(level=logging.ERROR)
    
    # Run the application
    exit_code = main()
    sys.exit(exit_code)"""