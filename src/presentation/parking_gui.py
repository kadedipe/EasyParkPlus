# File: src/presentation/parking_gui.py
"""
Parking Management System GUI

A modern, feature-rich desktop application for managing parking operations.
Built with Tkinter for maximum compatibility and ease of deployment.

Key Features:
1. Real-time parking lot visualization
2. Vehicle entry/exit management
3. EV charging station monitoring
4. Reservation system
5. Billing and invoicing
6. Reporting and analytics dashboard
7. User management and authentication
8. Real-time notifications and alerts

Architecture:
- MVC Pattern (Model-View-Controller)
- Modern Tkinter with ttk and custom styling
- Async operations for real-time updates
- Plugin system for extensibility
- Theme support (light/dark mode)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json
import threading
import queue
import asyncio
from dataclasses import dataclass, asdict
from enum import Enum
from uuid import UUID
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.application.parking_service import ParkingService, ParkingServiceFactory
from src.application.commands import CommandProcessor, ParkVehicleCommand, ExitVehicleCommand
from src.application.dtos import *
from src.infrastructure.factories import FactoryRegistry
from src.infrastructure.messaging import MessageBus, EventType, DomainEvent


# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

class Theme(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    BLUE = "blue"


class AppConfig:
    """Application configuration"""
    APP_NAME = "Parking Management System"
    VERSION = "1.0.0"
    COMPANY = "Parking Solutions Inc."
    
    # Window settings
    DEFAULT_WIDTH = 1400
    DEFAULT_HEIGHT = 800
    MIN_WIDTH = 1000
    MIN_HEIGHT = 600
    
    # Colors
    COLORS = {
        Theme.LIGHT: {
            "bg": "#f0f0f0",
            "fg": "#333333",
            "primary": "#007acc",
            "secondary": "#6c757d",
            "success": "#28a745",
            "danger": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8",
            "card_bg": "#ffffff",
            "border": "#dee2e6",
            "text_muted": "#6c757d"
        },
        Theme.DARK: {
            "bg": "#2b2b2b",
            "fg": "#ffffff",
            "primary": "#0d6efd",
            "secondary": "#6c757d",
            "success": "#198754",
            "danger": "#dc3545",
            "warning": "#ffc107",
            "info": "#0dcaf0",
            "card_bg": "#363636",
            "border": "#495057",
            "text_muted": "#adb5bd"
        },
        Theme.BLUE: {
            "bg": "#1a1a2e",
            "fg": "#e6e6e6",
            "primary": "#0f3460",
            "secondary": "#16213e",
            "success": "#4e9f3d",
            "danger": "#e94560",
            "warning": "#ff9a3c",
            "info": "#1e6f5c",
            "card_bg": "#16213e",
            "border": "#0f3460",
            "text_muted": "#8a8a8a"
        }
    }
    
    # Fonts
    FONTS = {
        "title": ("Segoe UI", 16, "bold"),
        "heading": ("Segoe UI", 14, "bold"),
        "subheading": ("Segoe UI", 12, "bold"),
        "body": ("Segoe UI", 10),
        "small": ("Segoe UI", 9),
        "monospace": ("Consolas", 10)
    }


# ============================================================================
# CUSTOM WIDGETS
# ============================================================================

class ModernButton(ttk.Button):
    """Modern styled button"""
    
    def __init__(self, parent, **kwargs):
        style = kwargs.pop('style', 'primary')
        super().__init__(parent, **kwargs)
        
        # Apply custom styling
        self.configure(
            cursor="hand2",
            padding=(12, 6)
        )
        
        # Add hover effect
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _on_enter(self, event):
        self.configure(style='Accent.TButton')
    
    def _on_leave(self, event):
        self.configure(style='TButton')


class CardFrame(ttk.Frame):
    """Card-style frame with shadow effect"""
    
    def __init__(self, parent, title: str = "", **kwargs):
        super().__init__(parent, **kwargs)
        self.title = title
        
        # Configure style
        self.configure(
            relief="solid",
            borderwidth=1,
            padding=10
        )
        
        # Add title if provided
        if title:
            title_label = ttk.Label(
                self,
                text=title,
                font=AppConfig.FONTS["subheading"]
            )
            title_label.pack(anchor="w", pady=(0, 10))
    
    def add_widget(self, widget, **pack_args):
        """Add widget to card with default packing"""
        default_pack = {"fill": "x", "padx": 5, "pady": 5}
        default_pack.update(pack_args)
        widget.pack(**default_pack)


class StatusIndicator(ttk.Frame):
    """Status indicator with color coding"""
    
    COLORS = {
        "success": "#28a745",
        "warning": "#ffc107",
        "danger": "#dc3545",
        "info": "#17a2b8",
        "secondary": "#6c757d"
    }
    
    def __init__(self, parent, status: str = "info", size: int = 12, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Create colored circle
        self.canvas = tk.Canvas(
            self,
            width=size,
            height=size,
            highlightthickness=0,
            bg=self.cget('bg')
        )
        self.canvas.pack()
        
        # Draw circle
        self.circle = self.canvas.create_oval(
            2, 2, size-2, size-2,
            fill=self.COLORS.get(status, "#6c757d"),
            outline=""
        )
        
        # Label for text
        self.label = None
    
    def set_status(self, status: str):
        """Update status color"""
        color = self.COLORS.get(status, "#6c757d")
        self.canvas.itemconfig(self.circle, fill=color)
    
    def add_label(self, text: str):
        """Add text label next to indicator"""
        if self.label:
            self.label.destroy()
        
        self.label = ttk.Label(self, text=text)
        self.label.pack(side="left", padx=(5, 0))


class ParkingSlotWidget(tk.Canvas):
    """Visual representation of a parking slot"""
    
    COLORS = {
        "available": "#28a745",    # Green
        "occupied": "#dc3545",     # Red
        "reserved": "#ffc107",     # Yellow
        "ev": "#17a2b8",           # Blue
        "disabled": "#6c757d",     # Gray
        "premium": "#9c27b0"       # Purple
    }
    
    def __init__(self, parent, slot_data: Dict[str, Any], size: int = 60, **kwargs):
        super().__init__(
            parent,
            width=size,
            height=size,
            highlightthickness=1,
            highlightbackground="#dee2e6",
            **kwargs
        )
        
        self.slot_data = slot_data
        self.size = size
        self.is_selected = False
        
        # Draw slot
        self._draw_slot()
        
        # Bind click events
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _draw_slot(self):
        """Draw the parking slot visualization"""
        self.delete("all")
        
        # Determine color based on status
        if self.slot_data.get('is_occupied'):
            color = self.COLORS["occupied"]
        elif self.slot_data.get('is_reserved'):
            color = self.COLORS["reserved"]
        elif self.slot_data.get('slot_type') == 'EV':
            color = self.COLORS["ev"]
        elif self.slot_data.get('slot_type') == 'DISABLED':
            color = self.COLORS["disabled"]
        elif self.slot_data.get('slot_type') == 'PREMIUM':
            color = self.COLORS["premium"]
        else:
            color = self.COLORS["available"]
        
        # Draw background
        padding = 2
        self.create_rectangle(
            padding, padding,
            self.size - padding, self.size - padding,
            fill=color,
            outline="",
            tags="background"
        )
        
        # Draw selection border if selected
        if self.is_selected:
            self.create_rectangle(
                0, 0,
                self.size, self.size,
                outline="#007acc",
                width=2,
                tags="selection"
            )
        
        # Add slot number
        slot_number = self.slot_data.get('number', '')
        self.create_text(
            self.size // 2,
            self.size // 2,
            text=str(slot_number),
            fill="white" if self.slot_data.get('is_occupied') else "black",
            font=("Segoe UI", 10, "bold"),
            tags="text"
        )
        
        # Add small indicator for EV slots
        if self.slot_data.get('slot_type') == 'EV':
            self.create_text(
                self.size // 2,
                self.size - 10,
                text="⚡",
                font=("Segoe UI", 8),
                tags="ev_indicator"
            )
    
    def _on_click(self, event):
        """Handle click event"""
        self.is_selected = not self.is_selected
        self._draw_slot()
        
        # Trigger callback if set
        if hasattr(self, 'on_click_callback'):
            self.on_click_callback(self.slot_data)
    
    def _on_enter(self, event):
        """Handle mouse enter"""
        self.configure(cursor="hand2")
    
    def _on_leave(self, event):
        """Handle mouse leave"""
        self.configure(cursor="")
    
    def set_on_click(self, callback: Callable):
        """Set click callback"""
        self.on_click_callback = callback
    
    def update_slot(self, slot_data: Dict[str, Any]):
        """Update slot data and redraw"""
        self.slot_data = slot_data
        self._draw_slot()


class DashboardChart(tk.Canvas):
    """Simple chart for dashboard"""
    
    def __init__(self, parent, title: str = "", width: int = 300, height: int = 200, **kwargs):
        super().__init__(parent, width=width, height=height, **kwargs)
        self.title = title
        self.width = width
        self.height = height
        self.data = []
        
        # Draw chart
        self._draw_chart()
    
    def _draw_chart(self):
        """Draw the chart"""
        self.delete("all")
        
        # Draw title
        if self.title:
            self.create_text(
                self.width // 2,
                15,
                text=self.title,
                font=AppConfig.FONTS["subheading"],
                fill="#333333"
            )
        
        # Draw chart area
        chart_left = 40
        chart_right = self.width - 20
        chart_top = 40
        chart_bottom = self.height - 40
        chart_width = chart_right - chart_left
        chart_height = chart_bottom - chart_top
        
        # Draw axes
        self.create_line(chart_left, chart_bottom, chart_right, chart_bottom, fill="#666666")  # X-axis
        self.create_line(chart_left, chart_top, chart_left, chart_bottom, fill="#666666")     # Y-axis
        
        # Draw data if available
        if self.data:
            max_value = max(self.data)
            bar_width = chart_width / len(self.data)
            
            for i, value in enumerate(self.data):
                x1 = chart_left + i * bar_width + 5
                x2 = x1 + bar_width - 10
                y1 = chart_bottom - (value / max_value) * chart_height if max_value > 0 else chart_bottom
                y2 = chart_bottom
                
                # Draw bar
                self.create_rectangle(x1, y1, x2, y2, fill="#007acc", outline="")
                
                # Draw value label
                self.create_text(
                    (x1 + x2) // 2,
                    y1 - 10,
                    text=str(value),
                    font=AppConfig.FONTS["small"],
                    fill="#333333"
                )
    
    def set_data(self, data: List[float]):
        """Set chart data and redraw"""
        self.data = data
        self._draw_chart()


# ============================================================================
# VIEWS (Screens)
# ============================================================================

class BaseView(ttk.Frame):
    """Base class for all views"""
    
    def __init__(self, parent, controller, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.app = controller.app
        
        # Setup view
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI elements - to be implemented by subclasses"""
        raise NotImplementedError
    
    def refresh(self):
        """Refresh view data"""
        pass
    
    def on_show(self):
        """Called when view is shown"""
        pass
    
    def on_hide(self):
        """Called when view is hidden"""
        pass


class DashboardView(BaseView):
    """Dashboard view showing overview and KPIs"""
    
    def _setup_ui(self):
        # Create main container
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_frame = ttk.Frame(self.main_container)
        header_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(
            header_frame,
            text="Dashboard",
            font=AppConfig.FONTS["title"]
        ).pack(side="left")
        
        # Refresh button
        ttk.Button(
            header_frame,
            text="Refresh",
            command=self.refresh,
            cursor="hand2"
        ).pack(side="right")
        
        # KPI Cards
        kpi_frame = ttk.Frame(self.main_container)
        kpi_frame.pack(fill="x", pady=(0, 20))
        
        # KPI 1: Total Parking Lots
        self.total_lots_card = CardFrame(kpi_frame, title="Parking Lots")
        self.total_lots_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.total_lots_value = ttk.Label(
            self.total_lots_card,
            text="0",
            font=("Segoe UI", 24, "bold"),
            foreground=AppConfig.COLORS[Theme.LIGHT]["primary"]
        )
        self.total_lots_value.pack(pady=10)
        
        ttk.Label(
            self.total_lots_card,
            text="Total Parking Lots",
            foreground=AppConfig.COLORS[Theme.LIGHT]["text_muted"]
        ).pack()
        
        # KPI 2: Available Slots
        self.available_slots_card = CardFrame(kpi_frame, title="Available Slots")
        self.available_slots_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.available_slots_value = ttk.Label(
            self.available_slots_card,
            text="0",
            font=("Segoe UI", 24, "bold"),
            foreground=AppConfig.COLORS[Theme.LIGHT]["success"]
        )
        self.available_slots_value.pack(pady=10)
        
        ttk.Label(
            self.available_slots_card,
            text="Slots Available",
            foreground=AppConfig.COLORS[Theme.LIGHT]["text_muted"]
        ).pack()
        
        # KPI 3: Occupancy Rate
        self.occupancy_card = CardFrame(kpi_frame, title="Occupancy Rate")
        self.occupancy_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.occupancy_value = ttk.Label(
            self.occupancy_card,
            text="0%",
            font=("Segoe UI", 24, "bold"),
            foreground=AppConfig.COLORS[Theme.LIGHT]["warning"]
        )
        self.occupancy_value.pack(pady=10)
        
        self.occupancy_progress = ttk.Progressbar(
            self.occupancy_card,
            length=100,
            mode='determinate'
        )
        self.occupancy_progress.pack(pady=5)
        
        # KPI 4: Revenue Today
        self.revenue_card = CardFrame(kpi_frame, title="Revenue Today")
        self.revenue_card.pack(side="left", fill="both", expand=True)
        
        self.revenue_value = ttk.Label(
            self.revenue_card,
            text="$0.00",
            font=("Segoe UI", 24, "bold"),
            foreground=AppConfig.COLORS[Theme.LIGHT]["info"]
        )
        self.revenue_value.pack(pady=10)
        
        ttk.Label(
            self.revenue_card,
            text="Total Revenue",
            foreground=AppConfig.COLORS[Theme.LIGHT]["text_muted"]
        ).pack()
        
        # Charts and Recent Activity
        charts_frame = ttk.Frame(self.main_container)
        charts_frame.pack(fill="both", expand=True)
        
        # Occupancy Chart
        chart_card = CardFrame(charts_frame, title="Occupancy Trend")
        chart_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.occupancy_chart = DashboardChart(chart_card, width=300, height=200)
        self.occupancy_chart.pack(pady=10)
        
        # Recent Activity
        activity_card = CardFrame(charts_frame, title="Recent Activity")
        activity_card.pack(side="left", fill="both", expand=True)
        
        # Activity list
        self.activity_list = tk.Listbox(
            activity_card,
            height=10,
            bg="white",
            relief="flat",
            font=AppConfig.FONTS["body"]
        )
        self.activity_list.pack(fill="both", expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(activity_card)
        scrollbar.pack(side="right", fill="y")
        self.activity_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.activity_list.yview)
        
        # Alerts Panel
        alerts_frame = ttk.Frame(self.main_container)
        alerts_frame.pack(fill="x", pady=(20, 0))
        
        alerts_card = CardFrame(alerts_frame, title="System Alerts")
        alerts_card.pack(fill="both", expand=True)
        
        self.alerts_text = scrolledtext.ScrolledText(
            alerts_card,
            height=6,
            bg="white",
            relief="flat",
            font=AppConfig.FONTS["monospace"]
        )
        self.alerts_text.pack(fill="both", expand=True, pady=5)
        self.alerts_text.config(state="disabled")
        
        # Initial refresh
        self.refresh()
    
    def refresh(self):
        """Refresh dashboard data"""
        # Simulate data loading
        self.total_lots_value.config(text="12")
        self.available_slots_value.config(text="356")
        self.occupancy_value.config(text="74%")
        self.occupancy_progress.config(value=74)
        self.revenue_value.config(text="$1,245.50")
        
        # Update chart
        self.occupancy_chart.set_data([65, 70, 68, 74, 72, 75, 74])
        
        # Update activity list
        self.activity_list.delete(0, tk.END)
        activities = [
            "08:30 - Vehicle ABC123 entered Lot A",
            "09:15 - Vehicle XYZ789 exited Lot B",
            "10:00 - EV charging session started",
            "11:30 - Reservation confirmed for Lot C",
            "12:45 - Payment received for invoice INV001",
            "14:20 - New parking lot added: Downtown Center"
        ]
        for activity in activities:
            self.activity_list.insert(tk.END, activity)
        
        # Update alerts
        self.alerts_text.config(state="normal")
        self.alerts_text.delete(1.0, tk.END)
        self.alerts_text.insert(tk.END, "No critical alerts at this time.")
        self.alerts_text.config(state="disabled")


class ParkingLotView(BaseView):
    """Parking lot management view"""
    
    def _setup_ui(self):
        # Create main container with paned window
        self.main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Left panel: Parking lot list
        left_panel = ttk.Frame(self.main_paned)
        self.main_paned.add(left_panel, weight=1)
        
        # Parking lot list header
        list_header = ttk.Frame(left_panel)
        list_header.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            list_header,
            text="Parking Lots",
            font=AppConfig.FONTS["heading"]
        ).pack(side="left")
        
        # Add buttons
        button_frame = ttk.Frame(list_header)
        button_frame.pack(side="right")
        
        ttk.Button(
            button_frame,
            text="Add New",
            command=self._add_parking_lot,
            cursor="hand2"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            button_frame,
            text="Refresh",
            command=self.refresh,
            cursor="hand2"
        ).pack(side="left")
        
        # Parking lot list
        self.lot_list_frame = CardFrame(left_panel)
        self.lot_list_frame.pack(fill="both", expand=True)
        
        # Treeview for parking lots
        columns = ("id", "name", "code", "city", "slots", "occupancy")
        self.lot_tree = ttk.Treeview(
            self.lot_list_frame,
            columns=columns,
            show="headings",
            height=15
        )
        
        # Configure columns
        self.lot_tree.heading("id", text="ID")
        self.lot_tree.heading("name", text="Name")
        self.lot_tree.heading("code", text="Code")
        self.lot_tree.heading("city", text="City")
        self.lot_tree.heading("slots", text="Slots")
        self.lot_tree.heading("occupancy", text="Occupancy")
        
        self.lot_tree.column("id", width=50, anchor="center")
        self.lot_tree.column("name", width=150)
        self.lot_tree.column("code", width=80, anchor="center")
        self.lot_tree.column("city", width=100)
        self.lot_tree.column("slots", width=80, anchor="center")
        self.lot_tree.column("occupancy", width=100, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.lot_list_frame)
        scrollbar.pack(side="right", fill="y")
        self.lot_tree.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.lot_tree.yview)
        
        self.lot_tree.pack(fill="both", expand=True)
        
        # Bind selection event
        self.lot_tree.bind("<<TreeviewSelect>>", self._on_lot_selected)
        
        # Right panel: Parking lot details
        right_panel = ttk.Frame(self.main_paned)
        self.main_paned.add(right_panel, weight=2)
        
        # Details header
        details_header = ttk.Frame(right_panel)
        details_header.pack(fill="x", pady=(0, 10))
        
        self.details_title = ttk.Label(
            details_header,
            text="Select a Parking Lot",
            font=AppConfig.FONTS["heading"]
        )
        self.details_title.pack(side="left")
        
        # Details content
        self.details_container = ttk.Frame(right_panel)
        self.details_container.pack(fill="both", expand=True)
        
        # Initial message
        self._show_initial_message()
        
        # Load initial data
        self.refresh()
    
    def _show_initial_message(self):
        """Show initial message when no lot is selected"""
        for widget in self.details_container.winfo_children():
            widget.destroy()
        
        message = ttk.Label(
            self.details_container,
            text="Select a parking lot from the list to view details",
            font=AppConfig.FONTS["body"],
            foreground=AppConfig.COLORS[Theme.LIGHT]["text_muted"]
        )
        message.pack(expand=True)
    
    def _show_lot_details(self, lot_data: Dict[str, Any]):
        """Show parking lot details"""
        for widget in self.details_container.winfo_children():
            widget.destroy()
        
        # Update title
        self.details_title.config(text=f"Parking Lot: {lot_data.get('name', 'Unknown')}")
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.details_container)
        notebook.pack(fill="both", expand=True)
        
        # Tab 1: Overview
        overview_tab = ttk.Frame(notebook)
        notebook.add(overview_tab, text="Overview")
        
        self._create_overview_tab(overview_tab, lot_data)
        
        # Tab 2: Slot Map
        map_tab = ttk.Frame(notebook)
        notebook.add(map_tab, text="Slot Map")
        
        self._create_slot_map_tab(map_tab, lot_data)
        
        # Tab 3: Statistics
        stats_tab = ttk.Frame(notebook)
        notebook.add(stats_tab, text="Statistics")
        
        self._create_statistics_tab(stats_tab, lot_data)
        
        # Tab 4: Settings
        settings_tab = ttk.Frame(notebook)
        notebook.add(settings_tab, text="Settings")
        
        self._create_settings_tab(settings_tab, lot_data)
    
    def _create_overview_tab(self, parent, lot_data: Dict[str, Any]):
        """Create overview tab"""
        # Basic info frame
        basic_info = CardFrame(parent, title="Basic Information")
        basic_info.pack(fill="x", pady=(0, 10))
        
        # Create grid for info
        info_grid = ttk.Frame(basic_info)
        info_grid.pack(fill="x")
        
        # Add info rows
        infos = [
            ("Code:", lot_data.get('code', 'N/A')),
            ("City:", lot_data.get('city', 'N/A')),
            ("Total Slots:", str(lot_data.get('total_slots', 0))),
            ("Available:", str(lot_data.get('available_slots', 0))),
            ("Occupancy:", f"{lot_data.get('occupancy_rate', 0):.1%}"),
            ("Hourly Rate:", f"${lot_data.get('hourly_rate', 0):.2f}")
        ]
        
        for i, (label, value) in enumerate(infos):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(info_grid, text=label, font=AppConfig.FONTS["body"]).grid(
                row=row, column=col, sticky="w", padx=(0, 5), pady=2
            )
            ttk.Label(info_grid, text=value, font=AppConfig.FONTS["body"], foreground="#007acc").grid(
                row=row, column=col+1, sticky="w", pady=2
            )
        
        # Quick actions
        actions_frame = CardFrame(parent, title="Quick Actions")
        actions_frame.pack(fill="x", pady=(0, 10))
        
        action_buttons = ttk.Frame(actions_frame)
        action_buttons.pack(fill="x")
        
        actions = [
            ("🚗 Park Vehicle", self._park_vehicle),
            ("🚪 Exit Vehicle", self._exit_vehicle),
            ("⚡ Start Charging", self._start_charging),
            ("📅 Make Reservation", self._make_reservation)
        ]
        
        for text, command in actions:
            btn = ModernButton(
                action_buttons,
                text=text,
                command=lambda cmd=command: cmd(lot_data),
                style="primary"
            )
            btn.pack(side="left", padx=(0, 10))
        
        # Recent activity
        activity_frame = CardFrame(parent, title="Recent Activity")
        activity_frame.pack(fill="both", expand=True)
        
        activity_text = scrolledtext.ScrolledText(
            activity_frame,
            height=8,
            bg="white",
            relief="flat"
        )
        activity_text.pack(fill="both", expand=True, pady=5)
        
        # Add sample activity
        activity_text.insert(tk.END, "No recent activity")
        activity_text.config(state="disabled")
    
    def _create_slot_map_tab(self, parent, lot_data: Dict[str, Any]):
        """Create slot map visualization"""
        # Filter and search
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(filter_frame, text="Filter by:").pack(side="left", padx=(0, 5))
        
        filter_var = tk.StringVar(value="all")
        ttk.Combobox(
            filter_frame,
            textvariable=filter_var,
            values=["All", "Available", "Occupied", "EV", "Disabled", "Premium"],
            state="readonly",
            width=15
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            filter_frame,
            text="Apply",
            command=lambda: self._apply_filter(filter_var.get())
        ).pack(side="left")
        
        # Slot map container
        map_container = ttk.Frame(parent)
        map_container.pack(fill="both", expand=True)
        
        # Create canvas for slots
        canvas_frame = ttk.Frame(map_container)
        canvas_frame.pack(fill="both", expand=True)
        
        # Add scrollbars
        canvas = tk.Canvas(canvas_frame, bg="white")
        scroll_y = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scroll_x = ttk.Scrollbar(canvas_frame, orient="horizontal", command=canvas.xview)
        
        canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        # Create frame inside canvas for slots
        slots_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=slots_frame, anchor="nw")
        
        # Create sample slots
        self._create_sample_slots(slots_frame)
        
        # Pack everything
        scroll_x.pack(side="bottom", fill="x")
        scroll_y.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # Update scroll region
        slots_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
    
    def _create_sample_slots(self, parent):
        """Create sample parking slots"""
        # Sample slot data
        sample_slots = []
        for i in range(1, 101):
            slot_type = "REGULAR"
            if i % 10 == 0:
                slot_type = "EV"
            elif i % 7 == 0:
                slot_type = "PREMIUM"
            elif i % 5 == 0:
                slot_type = "DISABLED"
            
            is_occupied = i % 3 == 0
            is_reserved = i % 11 == 0
            
            sample_slots.append({
                'number': i,
                'slot_type': slot_type,
                'is_occupied': is_occupied,
                'is_reserved': is_reserved,
                'features': []
            })
        
        # Create slot widgets
        for i, slot_data in enumerate(sample_slots):
            row = i // 10
            col = i % 10
            
            slot_widget = ParkingSlotWidget(parent, slot_data, size=50)
            slot_widget.grid(row=row, column=col, padx=2, pady=2)
            
            # Add click handler
            slot_widget.set_on_click(lambda data=slot_data: self._on_slot_click(data))
    
    def _create_statistics_tab(self, parent, lot_data: Dict[str, Any]):
        """Create statistics tab"""
        # Statistics cards
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill="x", pady=(0, 20))
        
        # Daily statistics
        daily_card = CardFrame(stats_frame, title="Daily Statistics")
        daily_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        stats = [
            ("Vehicles In:", "124"),
            ("Vehicles Out:", "118"),
            ("Revenue:", "$1,245.50"),
            ("Avg. Stay:", "2.3 hours")
        ]
        
        for label, value in stats:
            stat_frame = ttk.Frame(daily_card)
            stat_frame.pack(fill="x", pady=2)
            
            ttk.Label(stat_frame, text=label).pack(side="left")
            ttk.Label(
                stat_frame,
                text=value,
                font=AppConfig.FONTS["body"],
                foreground="#007acc"
            ).pack(side="right")
        
        # Hourly occupancy
        hourly_card = CardFrame(stats_frame, title="Hourly Occupancy")
        hourly_card.pack(side="left", fill="both", expand=True)
        
        chart = DashboardChart(hourly_card, width=200, height=150)
        chart.pack(pady=10)
        chart.set_data([30, 45, 60, 75, 80, 85, 90, 95, 90, 80, 70, 60])
        
        # Reports section
        reports_frame = CardFrame(parent, title="Reports")
        reports_frame.pack(fill="both", expand=True)
        
        # Report buttons
        report_buttons = ttk.Frame(reports_frame)
        report_buttons.pack(fill="x", pady=10)
        
        reports = [
            ("Daily Report", self._generate_daily_report),
            ("Monthly Report", self._generate_monthly_report),
            ("Occupancy Report", self._generate_occupancy_report),
            ("Revenue Report", self._generate_revenue_report)
        ]
        
        for text, command in reports:
            btn = ttk.Button(
                report_buttons,
                text=text,
                command=command,
                cursor="hand2"
            )
            btn.pack(side="left", padx=(0, 10))
    
    def _create_settings_tab(self, parent, lot_data: Dict[str, Any]):
        """Create settings tab"""
        # Settings form
        form_frame = CardFrame(parent, title="Parking Lot Settings")
        form_frame.pack(fill="both", expand=True)
        
        # Form fields
        fields = [
            ("Name:", "name", lot_data.get('name', '')),
            ("Hourly Rate:", "hourly_rate", str(lot_data.get('hourly_rate', 0))),
            ("Max Stay (hours):", "max_stay", "24"),
            ("Grace Period (min):", "grace_period", "15")
        ]
        
        self.settings_vars = {}
        
        for label, field, value in fields:
            field_frame = ttk.Frame(form_frame)
            field_frame.pack(fill="x", pady=5)
            
            ttk.Label(field_frame, text=label, width=20).pack(side="left")
            
            if field == "name":
                var = tk.StringVar(value=value)
                entry = ttk.Entry(field_frame, textvariable=var)
            else:
                var = tk.DoubleVar(value=float(value) if value else 0)
                entry = ttk.Entry(field_frame, textvariable=var)
            
            entry.pack(side="left", fill="x", expand=True)
            self.settings_vars[field] = var
        
        # Save button
        save_frame = ttk.Frame(form_frame)
        save_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(
            save_frame,
            text="Save Changes",
            command=self._save_settings,
            cursor="hand2"
        ).pack(side="right")
    
    def _on_lot_selected(self, event):
        """Handle parking lot selection"""
        selection = self.lot_tree.selection()
        if selection:
            item = self.lot_tree.item(selection[0])
            lot_data = item['values']
            
            # Convert to dictionary
            lot_dict = {
                'id': lot_data[0],
                'name': lot_data[1],
                'code': lot_data[2],
                'city': lot_data[3],
                'total_slots': int(lot_data[4].split('/')[1]),
                'available_slots': int(lot_data[4].split('/')[0]),
                'occupancy_rate': float(lot_data[5].strip('%')) / 100,
                'hourly_rate': 5.00
            }
            
            self._show_lot_details(lot_dict)
    
    def _apply_filter(self, filter_type):
        """Apply filter to slot map"""
        messagebox.showinfo("Filter", f"Applying filter: {filter_type}")
    
    def _on_slot_click(self, slot_data):
        """Handle slot click"""
        messagebox.showinfo(
            "Slot Details",
            f"Slot {slot_data['number']}\n"
            f"Type: {slot_data['slot_type']}\n"
            f"Status: {'Occupied' if slot_data['is_occupied'] else 'Available'}"
        )
    
    def _add_parking_lot(self):
        """Open add parking lot dialog"""
        self.controller.show_dialog("add_parking_lot")
    
    def _park_vehicle(self, lot_data):
        """Open park vehicle dialog"""
        self.controller.show_dialog("park_vehicle", lot_data=lot_data)
    
    def _exit_vehicle(self, lot_data):
        """Open exit vehicle dialog"""
        self.controller.show_dialog("exit_vehicle", lot_data=lot_data)
    
    def _start_charging(self, lot_data):
        """Open start charging dialog"""
        self.controller.show_dialog("start_charging", lot_data=lot_data)
    
    def _make_reservation(self, lot_data):
        """Open make reservation dialog"""
        self.controller.show_dialog("make_reservation", lot_data=lot_data)
    
    def _generate_daily_report(self):
        """Generate daily report"""
        messagebox.showinfo("Report", "Daily report generated")
    
    def _generate_monthly_report(self):
        """Generate monthly report"""
        messagebox.showinfo("Report", "Monthly report generated")
    
    def _generate_occupancy_report(self):
        """Generate occupancy report"""
        messagebox.showinfo("Report", "Occupancy report generated")
    
    def _generate_revenue_report(self):
        """Generate revenue report"""
        messagebox.showinfo("Report", "Revenue report generated")
    
    def _save_settings(self):
        """Save parking lot settings"""
        messagebox.showinfo("Settings", "Settings saved successfully")
    
    def refresh(self):
        """Refresh parking lot list"""
        # Clear existing items
        for item in self.lot_tree.get_children():
            self.lot_tree.delete(item)
        
        # Add sample data
        sample_lots = [
            ("1", "Downtown Center", "DTC001", "New York", "45/100", "45%"),
            ("2", "Mall Parking", "MALL002", "Los Angeles", "120/200", "60%"),
            ("3", "Airport Parking", "AIR003", "Chicago", "300/500", "60%"),
            ("4", "Hospital Parking", "HOSP004", "Houston", "80/150", "53%"),
            ("5", "University Lot", "UNIV005", "Phoenix", "60/100", "60%"),
            ("6", "Business Park", "BIZ006", "Philadelphia", "90/120", "75%"),
            ("7", "Shopping Plaza", "SHOP007", "San Antonio", "110/200", "55%"),
            ("8", "Convention Center", "CONV008", "San Diego", "200/300", "67%"),
            ("9", "Stadium Parking", "STAD009", "Dallas", "500/800", "63%"),
            ("10", "Marina Parking", "MAR010", "San Jose", "40/80", "50%")
        ]
        
        for lot in sample_lots:
            self.lot_tree.insert("", "end", values=lot)


class VehicleManagementView(BaseView):
    """Vehicle management view"""
    
    def _setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(
            header_frame,
            text="Vehicle Management",
            font=AppConfig.FONTS["title"]
        ).pack(side="left")
        
        # Search and filter
        search_frame = ttk.Frame(header_frame)
        search_frame.pack(side="right")
        
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(
            search_frame,
            textvariable=self.search_var,
            width=30
        )
        search_entry.pack(side="left", padx=(0, 10))
        search_entry.bind("<Return>", lambda e: self._search_vehicles())
        
        ttk.Button(
            search_frame,
            text="Search",
            command=self._search_vehicles,
            cursor="hand2"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            search_frame,
            text="Add Vehicle",
            command=self._add_vehicle,
            cursor="hand2"
        ).pack(side="left")
        
        # Vehicle list
        list_frame = CardFrame(main_frame, title="Registered Vehicles")
        list_frame.pack(fill="both", expand=True)
        
        # Create treeview
        columns = ("license_plate", "type", "make", "model", "year", "color", "status")
        self.vehicle_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=15
        )
        
        # Configure columns
        self.vehicle_tree.heading("license_plate", text="License Plate")
        self.vehicle_tree.heading("type", text="Type")
        self.vehicle_tree.heading("make", text="Make")
        self.vehicle_tree.heading("model", text="Model")
        self.vehicle_tree.heading("year", text="Year")
        self.vehicle_tree.heading("color", text="Color")
        self.vehicle_tree.heading("status", text="Status")
        
        self.vehicle_tree.column("license_plate", width=120)
        self.vehicle_tree.column("type", width=100)
        self.vehicle_tree.column("make", width=100)
        self.vehicle_tree.column("model", width=100)
        self.vehicle_tree.column("year", width=80, anchor="center")
        self.vehicle_tree.column("color", width=80)
        self.vehicle_tree.column("status", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.vehicle_tree.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.vehicle_tree.yview)
        
        self.vehicle_tree.pack(fill="both", expand=True)
        
        # Bind selection event
        self.vehicle_tree.bind("<<TreeviewSelect>>", self._on_vehicle_selected)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        actions = [
            ("View Details", self._view_vehicle_details),
            ("Edit", self._edit_vehicle),
            ("Delete", self._delete_vehicle),
            ("Park History", self._view_park_history),
            ("Refresh", self.refresh)
        ]
        
        for text, command in actions:
            btn = ttk.Button(
                button_frame,
                text=text,
                command=command,
                cursor="hand2"
            )
            btn.pack(side="left", padx=(0, 10))
        
        # Load initial data
        self.refresh()
    
    def _search_vehicles(self):
        """Search vehicles"""
        search_term = self.search_var.get().lower()
        if not search_term:
            self.refresh()
            return
        
        # Filter existing items
        for item in self.vehicle_tree.get_children():
            values = self.vehicle_tree.item(item)['values']
            if any(search_term in str(value).lower() for value in values):
                self.vehicle_tree.item(item, tags=('matched',))
            else:
                self.vehicle_tree.item(item, tags=())
        
        # Configure tag for matched items
        self.vehicle_tree.tag_configure('matched', background='#e8f4fd')
    
    def _add_vehicle(self):
        """Open add vehicle dialog"""
        self.controller.show_dialog("add_vehicle")
    
    def _view_vehicle_details(self):
        """View vehicle details"""
        selection = self.vehicle_tree.selection()
        if selection:
            self.controller.show_dialog("vehicle_details", vehicle_id=selection[0])
    
    def _edit_vehicle(self):
        """Edit vehicle"""
        selection = self.vehicle_tree.selection()
        if selection:
            self.controller.show_dialog("edit_vehicle", vehicle_id=selection[0])
    
    def _delete_vehicle(self):
        """Delete vehicle"""
        selection = self.vehicle_tree.selection()
        if selection:
            if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this vehicle?"):
                # Delete logic here
                self.vehicle_tree.delete(selection[0])
                messagebox.showinfo("Success", "Vehicle deleted successfully")
    
    def _view_park_history(self):
        """View parking history"""
        selection = self.vehicle_tree.selection()
        if selection:
            self.controller.show_dialog("park_history", vehicle_id=selection[0])
    
    def _on_vehicle_selected(self, event):
        """Handle vehicle selection"""
        pass
    
    def refresh(self):
        """Refresh vehicle list"""
        # Clear existing items
        for item in self.vehicle_tree.get_children():
            self.vehicle_tree.delete(item)
        
        # Add sample data
        sample_vehicles = [
            ("ABC-123", "Car", "Toyota", "Camry", "2020", "Blue", "Active"),
            ("EV-456", "EV Car", "Tesla", "Model 3", "2022", "Red", "Charging"),
            ("XYZ-789", "Motorcycle", "Honda", "CBR", "2021", "Black", "Active"),
            ("TRK-001", "Truck", "Ford", "F-150", "2019", "White", "Active"),
            ("BUS-002", "Bus", "Mercedes", "Sprinter", "2020", "Silver", "Active"),
            ("EV-003", "EV Car", "Nissan", "Leaf", "2021", "Blue", "Active"),
            ("MC-004", "Motorcycle", "Yamaha", "MT-07", "2022", "Yellow", "Active"),
            ("CAR-005", "Car", "BMW", "3 Series", "2021", "Black", "Parked"),
            ("EV-006", "EV Truck", "Rivian", "R1T", "2023", "Green", "Active"),
            ("VAN-007", "Van", "Chevrolet", "Express", "2018", "White", "Active")
        ]
        
        for vehicle in sample_vehicles:
            self.vehicle_tree.insert("", "end", values=vehicle)


class BillingView(BaseView):
    """Billing and invoicing view"""
    
    def _setup_ui(self):
        # Main container with notebook
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Create notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Invoices tab
        invoices_tab = ttk.Frame(self.notebook)
        self.notebook.add(invoices_tab, text="Invoices")
        self._create_invoices_tab(invoices_tab)
        
        # Payments tab
        payments_tab = ttk.Frame(self.notebook)
        self.notebook.add(payments_tab, text="Payments")
        self._create_payments_tab(payments_tab)
        
        # Reports tab
        reports_tab = ttk.Frame(self.notebook)
        self.notebook.add(reports_tab, text="Reports")
        self._create_reports_tab(reports_tab)
    
    def _create_invoices_tab(self, parent):
        """Create invoices tab"""
        # Header
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            header_frame,
            text="Invoices",
            font=AppConfig.FONTS["heading"]
        ).pack(side="left")
        
        # Action buttons
        button_frame = ttk.Frame(header_frame)
        button_frame.pack(side="right")
        
        ttk.Button(
            button_frame,
            text="Create Invoice",
            command=self._create_invoice,
            cursor="hand2"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            button_frame,
            text="Refresh",
            command=self.refresh,
            cursor="hand2"
        ).pack(side="left")
        
        # Invoice list
        list_frame = CardFrame(parent)
        list_frame.pack(fill="both", expand=True)
        
        # Create treeview
        columns = ("invoice_id", "date", "customer", "amount", "status", "due_date")
        self.invoice_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=15
        )
        
        # Configure columns
        self.invoice_tree.heading("invoice_id", text="Invoice #")
        self.invoice_tree.heading("date", text="Date")
        self.invoice_tree.heading("customer", text="Customer")
        self.invoice_tree.heading("amount", text="Amount")
        self.invoice_tree.heading("status", text="Status")
        self.invoice_tree.heading("due_date", text="Due Date")
        
        self.invoice_tree.column("invoice_id", width=100)
        self.invoice_tree.column("date", width=100)
        self.invoice_tree.column("customer", width=150)
        self.invoice_tree.column("amount", width=100)
        self.invoice_tree.column("status", width=100)
        self.invoice_tree.column("due_date", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.invoice_tree.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.invoice_tree.yview)
        
        self.invoice_tree.pack(fill="both", expand=True)
        
        # Bind double-click event
        self.invoice_tree.bind("<Double-1>", self._view_invoice_details)
    
    def _create_payments_tab(self, parent):
        """Create payments tab"""
        # Header
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            header_frame,
            text="Payments",
            font=AppConfig.FONTS["heading"]
        ).pack(side="left")
        
        # Payment list
        list_frame = CardFrame(parent)
        list_frame.pack(fill="both", expand=True)
        
        # Create treeview
        columns = ("payment_id", "date", "invoice", "amount", "method", "status")
        self.payment_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=15
        )
        
        # Configure columns
        self.payment_tree.heading("payment_id", text="Payment #")
        self.payment_tree.heading("date", text="Date")
        self.payment_tree.heading("invoice", text="Invoice")
        self.payment_tree.heading("amount", text="Amount")
        self.payment_tree.heading("method", text="Method")
        self.payment_tree.heading("status", text="Status")
        
        self.payment_tree.column("payment_id", width=100)
        self.payment_tree.column("date", width=100)
        self.payment_tree.column("invoice", width=100)
        self.payment_tree.column("amount", width=100)
        self.payment_tree.column("method", width=100)
        self.payment_tree.column("status", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        self.payment_tree.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.payment_tree.yview)
        
        self.payment_tree.pack(fill="both", expand=True)
    
    def _create_reports_tab(self, parent):
        """Create reports tab"""
        # Reports frame
        reports_frame = ttk.Frame(parent)
        reports_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(
            reports_frame,
            text="Financial Reports",
            font=AppConfig.FONTS["heading"]
        ).pack(anchor="w", pady=(0, 20))
        
        # Report cards
        cards_frame = ttk.Frame(reports_frame)
        cards_frame.pack(fill="x", pady=(0, 20))
        
        # Daily revenue
        daily_card = CardFrame(cards_frame, title="Daily Revenue")
        daily_card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.daily_revenue_chart = DashboardChart(daily_card, width=200, height=150)
        self.daily_revenue_chart.pack(pady=10)
        
        # Monthly revenue
        monthly_card = CardFrame(cards_frame, title="Monthly Revenue")
        monthly_card.pack(side="left", fill="both", expand=True)
        
        self.monthly_revenue_chart = DashboardChart(monthly_card, width=200, height=150)
        self.monthly_revenue_chart.pack(pady=10)
        
        # Report generation
        report_frame = CardFrame(reports_frame, title="Generate Reports")
        report_frame.pack(fill="both", expand=True)
        
        # Date range
        date_frame = ttk.Frame(report_frame)
        date_frame.pack(fill="x", pady=10)
        
        ttk.Label(date_frame, text="From:").pack(side="left", padx=(0, 5))
        self.from_date = ttk.Entry(date_frame, width=12)
        self.from_date.pack(side="left", padx=(0, 20))
        self.from_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        ttk.Label(date_frame, text="To:").pack(side="left", padx=(0, 5))
        self.to_date = ttk.Entry(date_frame, width=12)
        self.to_date.pack(side="left")
        self.to_date.insert(0, datetime.now().strftime("%Y-%m-%d"))
        
        # Report types
        type_frame = ttk.Frame(report_frame)
        type_frame.pack(fill="x", pady=10)
        
        self.report_type = tk.StringVar(value="revenue")
        
        report_types = [
            ("Revenue Report", "revenue"),
            ("Occupancy Report", "occupancy"),
            ("Vehicle Report", "vehicle"),
            ("Customer Report", "customer")
        ]
        
        for text, value in report_types:
            rb = ttk.Radiobutton(
                type_frame,
                text=text,
                variable=self.report_type,
                value=value
            )
            rb.pack(side="left", padx=(0, 20))
        
        # Generate button
        ttk.Button(
            report_frame,
            text="Generate Report",
            command=self._generate_report,
            cursor="hand2"
        ).pack(pady=10)
    
    def _create_invoice(self):
        """Create new invoice"""
        self.controller.show_dialog("create_invoice")
    
    def _view_invoice_details(self, event):
        """View invoice details"""
        selection = self.invoice_tree.selection()
        if selection:
            self.controller.show_dialog("invoice_details", invoice_id=selection[0])
    
    def _generate_report(self):
        """Generate report"""
        from_date = self.from_date.get()
        to_date = self.to_date.get()
        report_type = self.report_type.get()
        
        messagebox.showinfo(
            "Report Generated",
            f"{report_type.title()} report generated for {from_date} to {to_date}"
        )
    
    def refresh(self):
        """Refresh billing data"""
        # Clear existing items
        for item in self.invoice_tree.get_children():
            self.invoice_tree.delete(item)
        
        for item in self.payment_tree.get_children():
            self.payment_tree.delete(item)
        
        # Add sample invoices
        sample_invoices = [
            ("INV-001", "2024-01-15", "John Doe", "$25.50", "Paid", "2024-01-30"),
            ("INV-002", "2024-01-16", "Jane Smith", "$18.75", "Pending", "2024-01-31"),
            ("INV-003", "2024-01-17", "Acme Corp", "$152.30", "Paid", "2024-02-01"),
            ("INV-004", "2024-01-18", "Bob Johnson", "$32.00", "Overdue", "2024-01-25"),
            ("INV-005", "2024-01-19", "Tech Solutions", "$87.45", "Paid", "2024-02-05")
        ]
        
        for invoice in sample_invoices:
            self.invoice_tree.insert("", "end", values=invoice)
        
        # Add sample payments
        sample_payments = [
            ("PAY-001", "2024-01-16", "INV-001", "$25.50", "Credit Card", "Completed"),
            ("PAY-002", "2024-01-17", "INV-003", "$152.30", "Bank Transfer", "Completed"),
            ("PAY-003", "2024-01-20", "INV-005", "$87.45", "Credit Card", "Completed")
        ]
        
        for payment in sample_payments:
            self.payment_tree.insert("", "end", values=payment)
        
        # Update charts
        self.daily_revenue_chart.set_data([1250, 1320, 1410, 1480, 1560, 1620, 1245])
        self.monthly_revenue_chart.set_data([12500, 13200, 14100, 14800, 15600, 16200])


# ============================================================================
# DIALOGS
# ============================================================================

class BaseDialog(tk.Toplevel):
    """Base class for dialogs"""
    
    def __init__(self, parent, title: str, width: int = 500, height: int = 400):
        super().__init__(parent)
        
        self.title(title)
        self.geometry(f"{width}x{height}")
        self.resizable(False, False)
        
        # Center on screen
        self.transient(parent)
        self.grab_set()
        
        # Make modal
        self.focus_set()
        
        # Setup UI
        self._setup_ui()
        
        # Center window
        self.center_on_screen()
        
        # Bind escape to close
        self.bind("<Escape>", lambda e: self.destroy())
    
    def center_on_screen(self):
        """Center dialog on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def _setup_ui(self):
        """Setup UI elements - to be implemented by subclasses"""
        raise NotImplementedError


class ParkVehicleDialog(BaseDialog):
    """Dialog for parking a vehicle"""
    
    def __init__(self, parent, controller, lot_data: Dict[str, Any] = None):
        self.controller = controller
        self.lot_data = lot_data
        super().__init__(parent, "Park Vehicle", 600, 500)
    
    def _setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        ttk.Label(
            main_frame,
            text="Park Vehicle",
            font=AppConfig.FONTS["heading"]
        ).pack(anchor="w", pady=(0, 20))
        
        if self.lot_data:
            ttk.Label(
                main_frame,
                text=f"Parking Lot: {self.lot_data.get('name')}",
                font=AppConfig.FONTS["body"]
            ).pack(anchor="w", pady=(0, 10))
        
        # Form
        form_frame = CardFrame(main_frame)
        form_frame.pack(fill="both", expand=True)
        
        # License Plate
        ttk.Label(form_frame, text="License Plate *").pack(anchor="w", pady=(5, 0))
        self.license_plate = ttk.Entry(form_frame)
        self.license_plate.pack(fill="x", pady=(0, 15))
        
        # Vehicle Type
        ttk.Label(form_frame, text="Vehicle Type *").pack(anchor="w", pady=(5, 0))
        self.vehicle_type = ttk.Combobox(
            form_frame,
            values=["Car", "EV Car", "Motorcycle", "Truck", "Bus", "Van"],
            state="readonly"
        )
        self.vehicle_type.set("Car")
        self.vehicle_type.pack(fill="x", pady=(0, 15))
        
        # Vehicle Details (optional)
        details_frame = ttk.LabelFrame(form_frame, text="Vehicle Details (Optional)", padding=10)
        details_frame.pack(fill="x", pady=(0, 15))
        
        # Make and Model
        make_model_frame = ttk.Frame(details_frame)
        make_model_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(make_model_frame, text="Make:").pack(side="left", padx=(0, 5))
        self.make = ttk.Entry(make_model_frame, width=20)
        self.make.pack(side="left", padx=(0, 20))
        
        ttk.Label(make_model_frame, text="Model:").pack(side="left", padx=(0, 5))
        self.model = ttk.Entry(make_model_frame, width=20)
        self.model.pack(side="left")
        
        # Color
        ttk.Label(details_frame, text="Color:").pack(anchor="w", pady=(5, 0))
        self.color = ttk.Entry(details_frame, width=20)
        self.color.pack(anchor="w", pady=(0, 5))
        
        # Disabled Permit
        self.disabled_permit = tk.BooleanVar()
        ttk.Checkbutton(
            details_frame,
            text="Disabled Permit",
            variable=self.disabled_permit
        ).pack(anchor="w", pady=(5, 0))
        
        # EV Charging (only for EV vehicles)
        self.ev_frame = ttk.LabelFrame(form_frame, text="EV Charging", padding=10)
        
        self.needs_charging = tk.BooleanVar()
        ttk.Checkbutton(
            self.ev_frame,
            text="Needs Charging",
            variable=self.needs_charging,
            command=self._toggle_ev_details
        ).pack(anchor="w")
        
        self.charge_frame = ttk.Frame(self.ev_frame)
        
        ttk.Label(self.charge_frame, text="Current Charge (%):").pack(side="left", padx=(0, 5))
        self.current_charge = ttk.Spinbox(
            self.charge_frame,
            from_=0,
            to=100,
            width=10
        )
        self.current_charge.pack(side="left")
        
        ttk.Label(self.charge_frame, text="Target Charge (%):").pack(side="left", padx=(20, 5))
        self.target_charge = ttk.Spinbox(
            self.charge_frame,
            from_=0,
            to=100,
            width=10
        )
        self.target_charge.pack(side="left")
        
        # Parking Preferences
        ttk.Label(form_frame, text="Parking Preferences").pack(anchor="w", pady=(10, 0))
        
        pref_frame = ttk.Frame(form_frame)
        pref_frame.pack(fill="x", pady=(5, 0))
        
        self.preferred_type = tk.StringVar(value="Any")
        ttk.Label(pref_frame, text="Slot Type:").pack(side="left", padx=(0, 5))
        ttk.Combobox(
            pref_frame,
            textvariable=self.preferred_type,
            values=["Any", "Regular", "Premium", "EV", "Disabled"],
            state="readonly",
            width=15
        ).pack(side="left")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy,
            cursor="hand2"
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            button_frame,
            text="Park Vehicle",
            command=self._park_vehicle,
            style="primary.TButton",
            cursor="hand2"
        ).pack(side="right")
        
        # Bind vehicle type change
        self.vehicle_type.bind("<<ComboboxSelected>>", self._on_vehicle_type_changed)
    
    def _on_vehicle_type_changed(self, event):
        """Handle vehicle type change"""
        if self.vehicle_type.get() == "EV Car":
            self.ev_frame.pack(fill="x", pady=(0, 15))
        else:
            self.ev_frame.pack_forget()
    
    def _toggle_ev_details(self):
        """Toggle EV charging details"""
        if self.needs_charging.get():
            self.charge_frame.pack(fill="x", pady=(10, 0))
        else:
            self.charge_frame.pack_forget()
    
    def _park_vehicle(self):
        """Park vehicle"""
        # Validate inputs
        license_plate = self.license_plate.get().strip()
        if not license_plate:
            messagebox.showerror("Error", "License plate is required")
            return
        
        vehicle_type = self.vehicle_type.get()
        if not vehicle_type:
            messagebox.showerror("Error", "Vehicle type is required")
            return
        
        # Prepare data
        data = {
            "license_plate": license_plate,
            "vehicle_type": vehicle_type,
            "make": self.make.get().strip(),
            "model": self.model.get().strip(),
            "color": self.color.get().strip(),
            "disabled_permit": self.disabled_permit.get(),
            "preferred_slot_type": self.preferred_type.get().lower()
        }
        
        if vehicle_type == "EV Car" and self.needs_charging.get():
            data["requires_charging"] = True
            data["current_charge"] = self.current_charge.get()
            data["target_charge"] = self.target_charge.get()
        
        # Call controller to park vehicle
        success, message = self.controller.park_vehicle(data, self.lot_data)
        
        if success:
            messagebox.showinfo("Success", message)
            self.destroy()
        else:
            messagebox.showerror("Error", message)


class AddParkingLotDialog(BaseDialog):
    """Dialog for adding a new parking lot"""
    
    def __init__(self, parent, controller):
        self.controller = controller
        super().__init__(parent, "Add Parking Lot", 700, 600)
    
    def _setup_ui(self):
        # Main container with scrollbar
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True)
        
        # Create canvas with scrollbar
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # Content
        content_frame = ttk.Frame(scrollable_frame, padding=20)
        content_frame.pack(fill="both", expand=True)
        
        # Title
        ttk.Label(
            content_frame,
            text="Add New Parking Lot",
            font=AppConfig.FONTS["heading"]
        ).pack(anchor="w", pady=(0, 20))
        
        # Basic Information
        basic_frame = CardFrame(content_frame, title="Basic Information")
        basic_frame.pack(fill="x", pady=(0, 20))
        
        # Name
        ttk.Label(basic_frame, text="Name *").pack(anchor="w", pady=(5, 0))
        self.name = ttk.Entry(basic_frame)
        self.name.pack(fill="x", pady=(0, 10))
        
        # Code
        ttk.Label(basic_frame, text="Code *").pack(anchor="w", pady=(5, 0))
        self.code = ttk.Entry(basic_frame)
        self.code.pack(fill="x", pady=(0, 10))
        
        # Description
        ttk.Label(basic_frame, text="Description").pack(anchor="w", pady=(5, 0))
        self.description = tk.Text(basic_frame, height=4)
        self.description.pack(fill="x", pady=(0, 10))
        
        # Location Information
        location_frame = CardFrame(content_frame, title="Location Information")
        location_frame.pack(fill="x", pady=(0, 20))
        
        # Address
        ttk.Label(location_frame, text="Address *").pack(anchor="w", pady=(5, 0))
        self.address = ttk.Entry(location_frame)
        self.address.pack(fill="x", pady=(0, 10))
        
        # City, State, Country
        city_frame = ttk.Frame(location_frame)
        city_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(city_frame, text="City *").pack(side="left", padx=(0, 5))
        self.city = ttk.Entry(city_frame, width=20)
        self.city.pack(side="left", padx=(0, 20))
        
        ttk.Label(city_frame, text="State").pack(side="left", padx=(0, 5))
        self.state = ttk.Entry(city_frame, width=15)
        self.state.pack(side="left", padx=(0, 20))
        
        ttk.Label(city_frame, text="Country *").pack(side="left", padx=(0, 5))
        self.country = ttk.Entry(city_frame, width=15)
        self.country.pack(side="left")
        
        # Postal Code
        ttk.Label(location_frame, text="Postal Code").pack(anchor="w", pady=(5, 0))
        self.postal_code = ttk.Entry(location_frame, width=15)
        self.postal_code.pack(anchor="w", pady=(0, 10))
        
        # Capacity and Slots
        capacity_frame = CardFrame(content_frame, title="Capacity and Slots")
        capacity_frame.pack(fill="x", pady=(0, 20))
        
        # Total Capacity
        ttk.Label(capacity_frame, text="Total Capacity *").pack(anchor="w", pady=(5, 0))
        self.total_capacity = ttk.Spinbox(
            capacity_frame,
            from_=1,
            to=1000,
            width=10
        )
        self.total_capacity.pack(anchor="w", pady=(0, 15))
        
        # Slot Distribution
        ttk.Label(capacity_frame, text="Slot Distribution").pack(anchor="w", pady=(5, 0))
        
        dist_frame = ttk.Frame(capacity_frame)
        dist_frame.pack(fill="x", pady=(0, 10))
        
        # Regular Slots
        ttk.Label(dist_frame, text="Regular:").pack(side="left", padx=(0, 5))
        self.regular_slots = ttk.Spinbox(
            dist_frame,
            from_=0,
            to=1000,
            width=8
        )
        self.regular_slots.pack(side="left", padx=(0, 20))
        
        # Premium Slots
        ttk.Label(dist_frame, text="Premium:").pack(side="left", padx=(0, 5))
        self.premium_slots = ttk.Spinbox(
            dist_frame,
            from_=0,
            to=1000,
            width=8
        )
        self.premium_slots.pack(side="left", padx=(0, 20))
        
        # EV Slots
        ttk.Label(dist_frame, text="EV:").pack(side="left", padx=(0, 5))
        self.ev_slots = ttk.Spinbox(
            dist_frame,
            from_=0,
            to=1000,
            width=8
        )
        self.ev_slots.pack(side="left", padx=(0, 20))
        
        # Disabled Slots
        ttk.Label(dist_frame, text="Disabled:").pack(side="left", padx=(0, 5))
        self.disabled_slots = ttk.Spinbox(
            dist_frame,
            from_=0,
            to=1000,
            width=8
        )
        self.disabled_slots.pack(side="left")
        
        # Pricing
        pricing_frame = CardFrame(content_frame, title="Pricing")
        pricing_frame.pack(fill="x", pady=(0, 20))
        
        # Hourly Rates
        rates_frame = ttk.Frame(pricing_frame)
        rates_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(rates_frame, text="Regular Rate ($/hr):").pack(side="left", padx=(0, 5))
        self.regular_rate = ttk.Entry(rates_frame, width=10)
        self.regular_rate.insert(0, "5.00")
        self.regular_rate.pack(side="left", padx=(0, 20))
        
        ttk.Label(rates_frame, text="Premium Rate ($/hr):").pack(side="left", padx=(0, 5))
        self.premium_rate = ttk.Entry(rates_frame, width=10)
        self.premium_rate.insert(0, "10.00")
        self.premium_rate.pack(side="left", padx=(0, 20))
        
        ttk.Label(rates_frame, text="EV Rate ($/hr):").pack(side="left", padx=(0, 5))
        self.ev_rate = ttk.Entry(rates_frame, width=10)
        self.ev_rate.insert(0, "7.50")
        self.ev_rate.pack(side="left")
        
        # Operating Hours
        hours_frame = CardFrame(content_frame, title="Operating Hours")
        hours_frame.pack(fill="x", pady=(0, 20))
        
        # Weekday hours
        weekday_frame = ttk.Frame(hours_frame)
        weekday_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(weekday_frame, text="Weekdays:").pack(side="left", padx=(0, 5))
        self.weekday_open = ttk.Entry(weekday_frame, width=8)
        self.weekday_open.insert(0, "6:00")
        self.weekday_open.pack(side="left", padx=(0, 5))
        
        ttk.Label(weekday_frame, text="to").pack(side="left", padx=(0, 5))
        self.weekday_close = ttk.Entry(weekday_frame, width=8)
        self.weekday_close.insert(0, "22:00")
        self.weekday_close.pack(side="left")
        
        # Weekend hours
        weekend_frame = ttk.Frame(hours_frame)
        weekend_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(weekend_frame, text="Weekends:").pack(side="left", padx=(0, 5))
        self.weekend_open = ttk.Entry(weekend_frame, width=8)
        self.weekend_open.insert(0, "8:00")
        self.weekend_open.pack(side="left", padx=(0, 5))
        
        ttk.Label(weekend_frame, text="to").pack(side="left", padx=(0, 5))
        self.weekend_close = ttk.Entry(weekend_frame, width=8)
        self.weekend_close.insert(0, "20:00")
        self.weekend_close.pack(side="left")
        
        # Contact Information
        contact_frame = CardFrame(content_frame, title="Contact Information")
        contact_frame.pack(fill="x", pady=(0, 20))
        
        # Email
        ttk.Label(contact_frame, text="Email").pack(anchor="w", pady=(5, 0))
        self.email = ttk.Entry(contact_frame)
        self.email.pack(fill="x", pady=(0, 10))
        
        # Phone
        ttk.Label(contact_frame, text="Phone").pack(anchor="w", pady=(5, 0))
        self.phone = ttk.Entry(contact_frame)
        self.phone.pack(fill="x", pady=(0, 10))
        
        # Buttons
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self.destroy,
            cursor="hand2"
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            button_frame,
            text="Add Parking Lot",
            command=self._add_parking_lot,
            style="primary.TButton",
            cursor="hand2"
        ).pack(side="right")
    
    def _add_parking_lot(self):
        """Add parking lot"""
        # Validate inputs
        name = self.name.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        
        code = self.code.get().strip()
        if not code:
            messagebox.showerror("Error", "Code is required")
            return
        
        address = self.address.get().strip()
        if not address:
            messagebox.showerror("Error", "Address is required")
            return
        
        city = self.city.get().strip()
        if not city:
            messagebox.showerror("Error", "City is required")
            return
        
        country = self.country.get().strip()
        if not country:
            messagebox.showerror("Error", "Country is required")
            return
        
        # Prepare data
        data = {
            "name": name,
            "code": code,
            "description": self.description.get("1.0", "end-1c").strip(),
            "address": address,
            "city": city,
            "state": self.state.get().strip(),
            "country": country,
            "postal_code": self.postal_code.get().strip(),
            "total_capacity": int(self.total_capacity.get()),
            "slot_distribution": {
                "regular": int(self.regular_slots.get()),
                "premium": int(self.premium_slots.get()),
                "ev": int(self.ev_slots.get()),
                "disabled": int(self.disabled_slots.get())
            },
            "pricing": {
                "regular": float(self.regular_rate.get()),
                "premium": float(self.premium_rate.get()),
                "ev": float(self.ev_rate.get())
            },
            "operating_hours": {
                "weekday": f"{self.weekday_open.get()} to {self.weekday_close.get()}",
                "weekend": f"{self.weekend_open.get()} to {self.weekend_close.get()}"
            },
            "contact": {
                "email": self.email.get().strip(),
                "phone": self.phone.get().strip()
            }
        }
        
        # Call controller to add parking lot
        success, message = self.controller.add_parking_lot(data)
        
        if success:
            messagebox.showinfo("Success", message)
            self.destroy()
        else:
            messagebox.showerror("Error", message)


# ============================================================================
# CONTROLLER
# ============================================================================

class ParkingAppController:
    """Main application controller"""
    
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize services
        self._init_services()
        
        # Current view
        self.current_view = None
    
    def _init_services(self):
        """Initialize application services"""
        try:
            # Create parking service
            self.parking_service = ParkingServiceFactory.create_default_service()
            
            # Create command processor
            self.command_processor = CommandProcessor(self.parking_service)
            
            # Initialize factory registry
            self.factory_registry = FactoryRegistry()
            
            self.logger.info("Services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            messagebox.showerror(
                "Initialization Error",
                f"Failed to initialize application services:\n{str(e)}"
            )
            raise
    
    def switch_view(self, view_name: str):
        """Switch to a different view"""
        self.app.switch_view(view_name)
    
    def show_dialog(self, dialog_name: str, **kwargs):
        """Show a dialog"""
        dialog_class = self._get_dialog_class(dialog_name)
        if dialog_class:
            dialog = dialog_class(self.app, self, **kwargs)
            return dialog
        else:
            self.logger.error(f"Unknown dialog: {dialog_name}")
            return None
    
    def _get_dialog_class(self, dialog_name: str):
        """Get dialog class by name"""
        dialogs = {
            "park_vehicle": ParkVehicleDialog,
            "add_parking_lot": AddParkingLotDialog,
            # Add more dialogs here
        }
        return dialogs.get(dialog_name)
    
    def park_vehicle(self, vehicle_data: Dict[str, Any], lot_data: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Park a vehicle"""
        try:
            # Create parking request
            request = ParkingRequestDTO(
                license_plate=vehicle_data["license_plate"],
                vehicle_type=vehicle_data["vehicle_type"],
                parking_lot_id=lot_data["id"] if lot_data else uuid4(),
                preferences={
                    "preferred_slot_type": vehicle_data.get("preferred_slot_type", "any")
                }
            )
            
            # Create command
            command = ParkVehicleCommand(request, executed_by="gui_user")
            
            # Execute command
            result = self.command_processor.process(command)
            
            if result.get("success"):
                return True, "Vehicle parked successfully"
            else:
                return False, result.get("error", "Unknown error")
                
        except Exception as e:
            self.logger.error(f"Error parking vehicle: {e}")
            return False, f"Error: {str(e)}"
    
    def add_parking_lot(self, lot_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Add a parking lot"""
        try:
            # In a real implementation, this would create the parking lot
            # For now, just simulate success
            
            self.logger.info(f"Adding parking lot: {lot_data['name']}")
            
            # Simulate processing delay
            import time
            time.sleep(1)
            
            return True, f"Parking lot '{lot_data['name']}' added successfully"
            
        except Exception as e:
            self.logger.error(f"Error adding parking lot: {e}")
            return False, f"Error: {str(e)}"


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class ParkingManagementApp:
    """Main application class"""
    
    def __init__(self):
        # Create main window
        self.root = tk.Tk()
        self.root.title(f"{AppConfig.APP_NAME} v{AppConfig.VERSION}")
        self.root.geometry(f"{AppConfig.DEFAULT_WIDTH}x{AppConfig.DEFAULT_HEIGHT}")
        self.root.minsize(AppConfig.MIN_WIDTH, AppConfig.MIN_HEIGHT)
        
        # Set window icon
        self._set_window_icon()
        
        # Configure styles
        self._configure_styles()
        
        # Initialize controller
        self.controller = ParkingAppController(self)
        
        # Setup UI
        self._setup_ui()
        
        # Start with dashboard view
        self.switch_view("dashboard")
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _set_window_icon(self):
        """Set window icon"""
        try:
            # Try to load icon file
            icon_path = Path(__file__).parent / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(icon_path)
        except:
            pass  # Icon not essential
    
    def _configure_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        
        # Configure theme
        style.theme_use('clam')
        
        # Configure colors
        colors = AppConfig.COLORS[Theme.LIGHT]
        
        # Configure button styles
        style.configure(
            'TButton',
            padding=6,
            relief="flat",
            background=colors["primary"],
            foreground=colors["fg"]
        )
        
        style.configure(
            'primary.TButton',
            background=colors["primary"],
            foreground="white",
            font=AppConfig.FONTS["body"]
        )
        
        style.map(
            'primary.TButton',
            background=[('active', colors["primary"]), ('pressed', colors["primary"])],
            relief=[('pressed', 'sunken'), ('!pressed', 'flat')]
        )
        
        # Configure entry styles
        style.configure(
            'TEntry',
            fieldbackground="white",
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"]
        )
        
        # Configure frame styles
        style.configure(
            'Card.TFrame',
            background=colors["card_bg"],
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"],
            relief="solid",
            borderwidth=1
        )
        
        # Configure label styles
        style.configure(
            'Title.TLabel',
            font=AppConfig.FONTS["title"],
            foreground=colors["fg"]
        )
        
        style.configure(
            'Heading.TLabel',
            font=AppConfig.FONTS["heading"],
            foreground=colors["fg"]
        )
    
    def _setup_ui(self):
        """Setup main UI"""
        # Configure grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        # Create sidebar
        self._create_sidebar()
        
        # Create main content area
        self._create_content_area()
        
        # Create status bar
        self._create_status_bar()
        
        # Create menu
        self._create_menu()
    
    def _create_sidebar(self):
        """Create sidebar with navigation"""
        sidebar = ttk.Frame(self.root, width=200)
        sidebar.grid(row=0, column=0, sticky="nswe")
        sidebar.grid_propagate(False)
        
        # Logo/Title
        logo_frame = ttk.Frame(sidebar, padding=10)
        logo_frame.pack(fill="x")
        
        ttk.Label(
            logo_frame,
            text="PMS",
            font=("Segoe UI", 20, "bold"),
            foreground=AppConfig.COLORS[Theme.LIGHT]["primary"]
        ).pack()
        
        ttk.Label(
            logo_frame,
            text="Parking Management",
            font=AppConfig.FONTS["small"],
            foreground=AppConfig.COLORS[Theme.LIGHT]["text_muted"]
        ).pack()
        
        # Navigation
        nav_frame = ttk.Frame(sidebar)
        nav_frame.pack(fill="x", padx=10, pady=20)
        
        # Navigation items
        nav_items = [
            ("📊 Dashboard", "dashboard"),
            ("🅿️ Parking Lots", "parking_lots"),
            ("🚗 Vehicles", "vehicles"),
            ("⚡ Charging", "charging"),
            ("📅 Reservations", "reservations"),
            ("💰 Billing", "billing"),
            ("👥 Customers", "customers"),
            ("📈 Reports", "reports"),
            ("⚙️ Settings", "settings")
        ]
        
        self.nav_buttons = {}
        
        for text, view_name in nav_items:
            btn = ModernButton(
                nav_frame,
                text=text,
                command=lambda v=view_name: self.switch_view(v),
                style="TButton"
            )
            btn.pack(fill="x", pady=2)
            self.nav_buttons[view_name] = btn
        
        # Separator
        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=10, pady=10)
        
        # Quick actions
        quick_frame = ttk.Frame(sidebar)
        quick_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(
            quick_frame,
            text="Quick Actions",
            font=AppConfig.FONTS["subheading"]
        ).pack(anchor="w", pady=(0, 10))
        
        quick_actions = [
            ("🚗 Park Vehicle", lambda: self.controller.show_dialog("park_vehicle")),
            ("📅 New Reservation", lambda: print("New Reservation")),
            ("🧾 Create Invoice", lambda: print("Create Invoice")),
            ("📊 View Reports", lambda: print("View Reports"))
        ]
        
        for text, command in quick_actions:
            btn = ttk.Button(
                quick_frame,
                text=text,
                command=command,
                cursor="hand2"
            )
            btn.pack(fill="x", pady=2)
    
    def _create_content_area(self):
        """Create main content area"""
        self.content_frame = ttk.Frame(self.root)
        self.content_frame.grid(row=0, column=1, sticky="nswe", padx=20, pady=20)
        
        # Create views
        self.views = {}
        
        # Dashboard view
        self.views["dashboard"] = DashboardView(self.content_frame, self.controller)
        
        # Parking lots view
        self.views["parking_lots"] = ParkingLotView(self.content_frame, self.controller)
        
        # Vehicle management view
        self.views["vehicles"] = VehicleManagementView(self.content_frame, self.controller)
        
        # Billing view
        self.views["billing"] = BillingView(self.content_frame, self.controller)
        
        # Placeholder views for other sections
        for view_name in ["charging", "reservations", "customers", "reports", "settings"]:
            self.views[view_name] = ttk.Frame(self.content_frame)
            label = ttk.Label(
                self.views[view_name],
                text=f"{view_name.title()} View",
                font=AppConfig.FONTS["title"]
            )
            label.pack(expand=True)
    
    def _create_status_bar(self):
        """Create status bar"""
        status_bar = ttk.Frame(self.root, relief="sunken")
        status_bar.grid(row=1, column=0, columnspan=2, sticky="we")
        
        # Left side: Status
        ttk.Label(
            status_bar,
            text="Ready",
            font=AppConfig.FONTS["small"]
        ).pack(side="left", padx=10)
        
        # Center: Last update
        self.last_update_label = ttk.Label(
            status_bar,
            text=f"Last update: {datetime.now().strftime('%H:%M:%S')}",
            font=AppConfig.FONTS["small"]
        )
        self.last_update_label.pack(side="left", padx=10)
        
        # Right side: User info
        user_frame = ttk.Frame(status_bar)
        user_frame.pack(side="right", padx=10)
        
        ttk.Label(
            user_frame,
            text="👤 Admin",
            font=AppConfig.FONTS["small"]
        ).pack(side="left", padx=(0, 10))
        
        # Update timer
        self._update_status_bar()
    
    def _create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Theme", menu=theme_menu)
        
        self.theme_var = tk.StringVar(value=Theme.LIGHT.value)
        for theme in Theme:
            theme_menu.add_radiobutton(
                label=theme.value.title(),
                variable=self.theme_var,
                value=theme.value,
                command=self._change_theme
            )
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Import Data", command=self._import_data)
        tools_menu.add_command(label="Export Data", command=self._export_data)
        tools_menu.add_separator()
        tools_menu.add_command(label="System Logs", command=self._show_logs)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self._show_documentation)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _update_status_bar(self):
        """Update status bar information"""
        current_time = datetime.now().strftime('%H:%M:%S')
        self.last_update_label.config(text=f"Last update: {current_time}")
        
        # Schedule next update
        self.root.after(1000, self._update_status_bar)
    
    def switch_view(self, view_name: str):
        """Switch to a different view"""
        # Hide current view
        if self.current_view:
            self.current_view.pack_forget()
        
        # Show new view
        if view_name in self.views:
            self.current_view = self.views[view_name]
            self.current_view.pack(fill="both", expand=True)
            
            # Call on_show method if available
            if hasattr(self.current_view, 'on_show'):
                self.current_view.on_show()
            
            # Update navigation button states
            self._update_nav_buttons(view_name)
    
    def _update_nav_buttons(self, active_view: str):
        """Update navigation button states"""
        for view_name, button in self.nav_buttons.items():
            if view_name == active_view:
                button.configure(style='primary.TButton')
            else:
                button.configure(style='TButton')
    
    def _change_theme(self):
        """Change application theme"""
        theme = Theme(self.theme_var.get())
        colors = AppConfig.COLORS[theme]
        
        # Update root background
        self.root.configure(bg=colors["bg"])
        
        # Update styles would go here
        # In a full implementation, this would update all widget colors
    
    def _import_data(self):
        """Import data from file"""
        filename = filedialog.askopenfilename(
            title="Import Data",
            filetypes=[
                ("CSV files", "*.csv"),
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            try:
                # Import logic here
                messagebox.showinfo("Import", f"Data imported from {filename}")
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import data: {e}")
    
    def _export_data(self):
        """Export data to file"""
        filename = filedialog.asksaveasfilename(
            title="Export Data",
            defaultextension=".json",
            filetypes=[
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            try:
                # Export logic here
                messagebox.showinfo("Export", f"Data exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export data: {e}")
    
    def _show_logs(self):
        """Show system logs"""
        log_window = tk.Toplevel(self.root)
        log_window.title("System Logs")
        log_window.geometry("800x600")
        
        text = scrolledtext.ScrolledText(log_window, wrap=tk.WORD)
        text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add sample logs
        text.insert(tk.END, "System logs will appear here...\n\n")
        text.insert(tk.END, f"Application started at {datetime.now()}\n")
        text.insert(tk.END, "All systems operational\n")
        
        text.config(state="disabled")
    
    def _show_documentation(self):
        """Show documentation"""
        messagebox.showinfo(
            "Documentation",
            "Parking Management System Documentation\n\n"
            "This application helps manage parking operations including:\n"
            "• Vehicle entry and exit\n"
            "• Parking slot allocation\n"
            "• EV charging management\n"
            "• Billing and invoicing\n"
            "• Reporting and analytics\n\n"
            "For detailed documentation, please visit our website."
        )
    
    def _show_about(self):
        """Show about dialog"""
        about_text = f"""
{AppConfig.APP_NAME} v{AppConfig.VERSION}

A comprehensive parking management solution
for modern parking facilities.

Developed by {AppConfig.COMPANY}

Features:
• Real-time parking lot monitoring
• EV charging station management
• Reservation system
• Billing and payment processing
• Reporting and analytics
• User management

© 2024 {AppConfig.COMPANY}. All rights reserved.
"""
        
        messagebox.showinfo("About", about_text)
    
    def on_closing(self):
        """Handle window closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            # Cleanup resources
            self.root.destroy()
    
    def run(self):
        """Run the application"""
        # Center window on screen
        self.root.eval('tk::PlaceWindow . center')
        
        # Start main loop
        self.root.mainloop()


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run application
    app = ParkingManagementApp()
    app.run()


if __name__ == "__main__":
    main()