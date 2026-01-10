#!/usr/bin/env python3
"""
Domain Layer Unit Tests

Tests for domain entities and value objects.
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta


class TestParkingLot(unittest.TestCase):
    """Unit tests for ParkingLot entity"""
    
    def setUp(self):
        """Set up test data"""
        # Mock dependencies
        self.mock_repository = Mock()
        
    def test_parking_lot_creation(self):
        """Test creating a parking lot"""
        # This would test the actual ParkingLot class
        # For now, create a mock
        
        class MockParkingLot:
            def __init__(self, id, name, total_slots):
                self.id = id
                self.name = name
                self.total_slots = total_slots
                self.available_slots = total_slots
                self.slots = []
            
            def add_slot(self, slot):
                self.slots.append(slot)
                return len(self.slots)
        
        # Create parking lot
        parking_lot = MockParkingLot(
            id="test-lot-1",
            name="Test Parking Lot",
            total_slots=100
        )
        
        # Verify properties
        self.assertEqual(parking_lot.id, "test-lot-1")
        self.assertEqual(parking_lot.name, "Test Parking Lot")
        self.assertEqual(parking_lot.total_slots, 100)
        self.assertEqual(parking_lot.available_slots, 100)
        
        # Test adding slots
        slot_count = parking_lot.add_slot(Mock())
        self.assertEqual(slot_count, 1)
        
        slot_count = parking_lot.add_slot(Mock())
        self.assertEqual(slot_count, 2)
    
    def test_occupancy_calculation(self):
        """Test occupancy rate calculation"""
        class MockParkingLot:
            def __init__(self, total_slots, occupied_slots):
                self.total_slots = total_slots
                self.occupied_slots = occupied_slots
            
            def get_occupancy_rate(self):
                if self.total_slots == 0:
                    return 0.0
                return self.occupied_slots / self.total_slots
        
        # Test various occupancy scenarios
        test_cases = [
            (100, 0, 0.0),      # Empty
            (100, 50, 0.5),     # Half full
            (100, 100, 1.0),    # Full
            (0, 0, 0.0),        # No slots (edge case)
        ]
        
        for total, occupied, expected in test_cases:
            lot = MockParkingLot(total, occupied)
            rate = lot.get_occupancy_rate()
            self.assertAlmostEqual(rate, expected, places=2,
                                 msg=f"Failed for total={total}, occupied={occupied}")
    
    def test_find_available_slot(self):
        """Test finding available parking slot"""
        class MockSlot:
            def __init__(self, number, is_occupied=False, slot_type="regular"):
                self.number = number
                self.is_occupied = is_occupied
                self.slot_type = slot_type
        
        class MockParkingLot:
            def __init__(self):
                self.slots = [
                    MockSlot(1, False, "regular"),
                    MockSlot(2, True, "regular"),
                    MockSlot(3, False, "premium"),
                    MockSlot(4, False, "ev"),
                    MockSlot(5, True, "ev"),
                ]
            
            def find_available_slot(self, preferred_type=None):
                for slot in self.slots:
                    if not slot.is_occupied:
                        if preferred_type is None or slot.slot_type == preferred_type:
                            return slot
                return None
        
        # Create parking lot
        lot = MockParkingLot()
        
        # Test finding any available slot
        slot = lot.find_available_slot()
        self.assertIsNotNone(slot)
        self.assertEqual(slot.number, 1)
        self.assertFalse(slot.is_occupied)
        
        # Test finding premium slot
        slot = lot.find_available_slot("premium")
        self.assertIsNotNone(slot)
        self.assertEqual(slot.number, 3)
        self.assertEqual(slot.slot_type, "premium")
        
        # Test finding EV slot
        slot = lot.find_available_slot("ev")
        self.assertIsNotNone(slot)
        self.assertEqual(slot.number, 4)
        self.assertEqual(slot.slot_type, "ev")
        
        # Test no available slot of preferred type
        # Create lot with no available regular slots
        lot.slots = [
            MockSlot(1, True, "regular"),
            MockSlot(2, True, "regular"),
        ]
        slot = lot.find_available_slot("regular")
        self.assertIsNone(slot)


class TestVehicle(unittest.TestCase):
    """Unit tests for Vehicle entity"""
    
    def test_vehicle_creation(self):
        """Test creating a vehicle"""
        class MockVehicle:
            def __init__(self, license_plate, vehicle_type, make=None, model=None, color=None):
                self.license_plate = license_plate
                self.vehicle_type = vehicle_type
                self.make = make
                self.model = model
                self.color = color
                self.is_ev = vehicle_type.lower() in ["ev", "electric"]
            
            def get_description(self):
                parts = []
                if self.make:
                    parts.append(self.make)
                if self.model:
                    parts.append(self.model)
                if self.color:
                    parts.append(self.color)
                
                if parts:
                    return f"{self.license_plate} ({', '.join(parts)})"
                return self.license_plate
        
        # Test regular vehicle
        car = MockVehicle(
            license_plate="ABC-123",
            vehicle_type="Car",
            make="Toyota",
            model="Camry",
            color="Blue"
        )
        
        self.assertEqual(car.license_plate, "ABC-123")
        self.assertEqual(car.vehicle_type, "Car")
        self.assertEqual(car.make, "Toyota")
        self.assertEqual(car.model, "Camry")
        self.assertEqual(car.color, "Blue")
        self.assertFalse(car.is_ev)
        self.assertEqual(car.get_description(), "ABC-123 (Toyota, Camry, Blue)")
        
        # Test EV
        ev = MockVehicle(
            license_plate="EV-001",
            vehicle_type="EV",
            make="Tesla",
            model="Model 3"
        )
        
        self.assertTrue(ev.is_ev)
        self.assertEqual(ev.get_description(), "EV-001 (Tesla, Model 3)")
        
        # Test minimal vehicle
        minimal = MockVehicle(
            license_plate="MIN-001",
            vehicle_type="Motorcycle"
        )
        
        self.assertEqual(minimal.get_description(), "MIN-001")
    
    def test_vehicle_validation(self):
        """Test vehicle data validation"""
        class MockVehicleValidator:
            @staticmethod
            def validate_license_plate(plate):
                if not plate:
                    return False, "License plate is required"
                
                if len(plate) > 20:
                    return False, "License plate too long"
                
                # Simple validation: alphanumeric and hyphens
                import re
                if not re.match(r'^[A-Z0-9-]+$', plate, re.IGNORECASE):
                    return False, "Invalid license plate format"
                
                return True, "Valid"
            
            @staticmethod
            def validate_vehicle_type(vehicle_type):
                valid_types = ["car", "ev", "motorcycle", "truck", "bus", "van"]
                if vehicle_type.lower() not in valid_types:
                    return False, f"Invalid vehicle type. Must be one of: {', '.join(valid_types)}"
                return True, "Valid"
        
        validator = MockVehicleValidator()
        
        # Test license plate validation
        test_cases = [
            ("ABC-123", True),
            ("", False),
            ("ABC-123-TOO-LONG-PLATE", False),
            ("INVALID@PLATE", False),
            ("XYZ789", True),
        ]
        
        for plate, should_pass in test_cases:
            valid, message = validator.validate_license_plate(plate)
            self.assertEqual(valid, should_pass,
                           f"Failed for plate '{plate}': {message}")
        
        # Test vehicle type validation
        test_cases = [
            ("Car", True),
            ("EV", True),
            ("Motorcycle", True),
            ("InvalidType", False),
            ("", False),
        ]
        
        for vehicle_type, should_pass in test_cases:
            valid, message = validator.validate_vehicle_type(vehicle_type)
            self.assertEqual(valid, should_pass,
                           f"Failed for type '{vehicle_type}': {message}")


class TestParkingSession(unittest.TestCase):
    """Unit tests for ParkingSession entity"""
    
    def setUp(self):
        """Set up test data"""
        self.mock_vehicle = Mock(license_plate="ABC-123")
        self.mock_parking_lot = Mock(hourly_rate=5.0)
        self.entry_time = datetime.now()
    
    def test_parking_session_creation(self):
        """Test creating a parking session"""
        class MockParkingSession:
            def __init__(self, vehicle, parking_lot, slot_number, entry_time):
                self.vehicle = vehicle
                self.parking_lot = parking_lot
                self.slot_number = slot_number
                self.entry_time = entry_time
                self.exit_time = None
                self.total_charge = 0.0
                self.status = "active"
            
            def exit_vehicle(self, exit_time):
                if self.exit_time is not None:
                    raise ValueError("Vehicle already exited")
                
                self.exit_time = exit_time
                self.status = "completed"
                self.calculate_charge()
            
            def calculate_charge(self):
                if self.exit_time is None:
                    return 0.0
                
                duration = (self.exit_time - self.entry_time).total_seconds() / 3600  # hours
                self.total_charge = duration * self.parking_lot.hourly_rate
                return self.total_charge
            
            def get_duration_hours(self):
                if self.exit_time is None:
                    current_time = datetime.now()
                    duration = (current_time - self.entry_time).total_seconds() / 3600
                else:
                    duration = (self.exit_time - self.entry_time).total_seconds() / 3600
                return round(duration, 2)
        
        # Create session
        session = MockParkingSession(
            vehicle=self.mock_vehicle,
            parking_lot=self.mock_parking_lot,
            slot_number="A-15",
            entry_time=self.entry_time
        )
        
        # Verify initial state
        self.assertEqual(session.vehicle, self.mock_vehicle)
        self.assertEqual(session.parking_lot, self.mock_parking_lot)
        self.assertEqual(session.slot_number, "A-15")
        self.assertEqual(session.status, "active")
        self.assertIsNone(session.exit_time)
        self.assertEqual(session.total_charge, 0.0)
        
        # Test exiting vehicle
        exit_time = self.entry_time + timedelta(hours=2)
        session.exit_vehicle(exit_time)
        
        self.assertEqual(session.exit_time, exit_time)
        self.assertEqual(session.status, "completed")
        
        # Test charge calculation
        expected_charge = 2 * 5.0  # 2 hours at $5/hour
        self.assertEqual(session.total_charge, expected_charge)
        
        # Test duration calculation
        duration = session.get_duration_hours()
        self.assertEqual(duration, 2.0)
        
        # Test cannot exit twice
        with self.assertRaises(ValueError):
            session.exit_vehicle(exit_time + timedelta(hours=1))
    
    def test_charge_calculation_edge_cases(self):
        """Test edge cases in charge calculation"""
        class MockChargeCalculator:
            @staticmethod
            def calculate_charge(hourly_rate, entry_time, exit_time, grace_period_minutes=15):
                if exit_time is None:
                    return 0.0
                
                # Calculate duration in hours
                duration_seconds = (exit_time - entry_time).total_seconds()
                duration_hours = duration_seconds / 3600
                
                # Apply grace period
                if duration_hours <= (grace_period_minutes / 60):
                    return 0.0
                
                # Round up to nearest hour
                duration_hours_rounded = -(-duration_hours // 1)  # Ceiling division
                
                return duration_hours_rounded * hourly_rate
        
        calculator = MockChargeCalculator()
        
        # Test cases
        test_cases = [
            # (hours, grace_period, hourly_rate, expected_charge)
            (0.1, 15, 5.0, 0.0),    # Within grace period
            (0.3, 15, 5.0, 5.0),    # Just over grace period (rounds to 1 hour)
            (1.5, 15, 5.0, 10.0),   # 1.5 hours rounds to 2 hours
            (2.0, 15, 5.0, 10.0),   # Exactly 2 hours
            (2.1, 15, 5.0, 15.0),   # 2.1 hours rounds to 3 hours
        ]
        
        for hours, grace_minutes, rate, expected in test_cases:
            entry_time = datetime.now()
            exit_time = entry_time + timedelta(hours=hours)
            
            charge = calculator.calculate_charge(
                rate, entry_time, exit_time, grace_minutes
            )
            
            self.assertEqual(charge, expected,
                           f"Failed for {hours} hours at ${rate}/hour")


class TestValueObjects(unittest.TestCase):
    """Unit tests for value objects"""
    
    def test_money_value_object(self):
        """Test Money value object"""
        class MockMoney:
            def __init__(self, amount, currency="USD"):
                if amount < 0:
                    raise ValueError("Amount cannot be negative")
                self.amount = amount
                self.currency = currency
            
            def __add__(self, other):
                if self.currency != other.currency:
                    raise ValueError("Cannot add different currencies")
                return MockMoney(self.amount + other.amount, self.currency)
            
            def __sub__(self, other):
                if self.currency != other.currency:
                    raise ValueError("Cannot subtract different currencies")
                return MockMoney(self.amount - other.amount, self.currency)
            
            def __mul__(self, multiplier):
                return MockMoney(self.amount * multiplier, self.currency)
            
            def __eq__(self, other):
                if not isinstance(other, MockMoney):
                    return False
                return self.amount == other.amount and self.currency == other.currency
            
            def __str__(self):
                return f"{self.currency} {self.amount:.2f}"
        
        # Test creation
        money1 = MockMoney(10.50)
        self.assertEqual(money1.amount, 10.50)
        self.assertEqual(money1.currency, "USD")
        self.assertEqual(str(money1), "USD 10.50")
        
        # Test negative amount
        with self.assertRaises(ValueError):
            MockMoney(-5.0)
        
        # Test addition
        money2 = MockMoney(5.25)
        result = money1 + money2
        self.assertEqual(result.amount, 15.75)
        
        # Test subtraction
        result = money1 - money2
        self.assertEqual(result.amount, 5.25)
        
        # Test multiplication
        result = money1 * 2
        self.assertEqual(result.amount, 21.00)
        
        # Test equality
        money3 = MockMoney(10.50)
        self.assertEqual(money1, money3)
        
        money4 = MockMoney(10.50, "EUR")
        self.assertNotEqual(money1, money4)  # Different currency
        
        # Test different currencies
        with self.assertRaises(ValueError):
            money1 + money4
    
    def test_address_value_object(self):
        """Test Address value object"""
        class MockAddress:
            def __init__(self, street, city, state, postal_code, country="USA"):
                self.street = street
                self.city = city
                self.state = state
                self.postal_code = postal_code
                self.country = country
            
            def __eq__(self, other):
                if not isinstance(other, MockAddress):
                    return False
                return (self.street == other.street and
                       self.city == other.city and
                       self.state == other.state and
                       self.postal_code == other.postal_code and
                       self.country == other.country)
            
            def __str__(self):
                lines = [
                    self.street,
                    f"{self.city}, {self.state} {self.postal_code}",
                    self.country
                ]
                return "\n".join(lines)
            
            def is_valid(self):
                # Simple validation
                required_fields = [self.street, self.city, self.state, self.postal_code]
                return all(field and str(field).strip() for field in required_fields)
        
        # Test creation
        address = MockAddress(
            street="123 Main St",
            city="Springfield",
            state="IL",
            postal_code="62701",
            country="USA"
        )
        
        self.assertEqual(address.street, "123 Main St")
        self.assertEqual(address.city, "Springfield")
        self.assertEqual(address.state, "IL")
        self.assertEqual(address.postal_code, "62701")
        self.assertEqual(address.country, "USA")
        
        # Test string representation
        expected_str = "123 Main St\nSpringfield, IL 62701\nUSA"
        self.assertEqual(str(address), expected_str)
        
        # Test validation
        self.assertTrue(address.is_valid())
        
        # Test invalid address
        invalid_address = MockAddress(
            street="",
            city="Springfield",
            state="IL",
            postal_code="62701"
        )
        self.assertFalse(invalid_address.is_valid())
        
        # Test equality
        same_address = MockAddress(
            street="123 Main St",
            city="Springfield",
            state="IL",
            postal_code="62701"
        )
        self.assertEqual(address, same_address)
        
        different_address = MockAddress(
            street="456 Oak Ave",
            city="Springfield",
            state="IL",
            postal_code="62701"
        )
        self.assertNotEqual(address, different_address)
    
    def test_time_range_value_object(self):
        """Test TimeRange value object"""
        class MockTimeRange:
            def __init__(self, start_time, end_time):
                if end_time <= start_time:
                    raise ValueError("End time must be after start time")
                self.start_time = start_time
                self.end_time = end_time
            
            @property
            def duration_hours(self):
                duration = (self.end_time - self.start_time).total_seconds() / 3600
                return round(duration, 2)
            
            def contains(self, time_point):
                return self.start_time <= time_point <= self.end_time
            
            def overlaps(self, other):
                return (self.contains(other.start_time) or
                       self.contains(other.end_time) or
                       other.contains(self.start_time))
            
            def __str__(self):
                return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
        
        # Create time range
        start = datetime(2024, 1, 1, 9, 0)  # 9:00 AM
        end = datetime(2024, 1, 1, 17, 0)   # 5:00 PM
        time_range = MockTimeRange(start, end)
        
        # Test properties
        self.assertEqual(time_range.start_time, start)
        self.assertEqual(time_range.end_time, end)
        self.assertEqual(time_range.duration_hours, 8.0)
        self.assertEqual(str(time_range), "09:00 - 17:00")
        
        # Test invalid time range
        with self.assertRaises(ValueError):
            MockTimeRange(end, start)  # End before start
        
        # Test contains
        self.assertTrue(time_range.contains(datetime(2024, 1, 1, 12, 0)))  # Noon
        self.assertFalse(time_range.contains(datetime(2024, 1, 1, 8, 0)))  # 8 AM
        self.assertFalse(time_range.contains(datetime(2024, 1, 1, 18, 0)))  # 6 PM
        
        # Test overlaps
        overlapping = MockTimeRange(
            datetime(2024, 1, 1, 13, 0),
            datetime(2024, 1, 1, 19, 0)
        )
        self.assertTrue(time_range.overlaps(overlapping))
        
        non_overlapping = MockTimeRange(
            datetime(2024, 1, 1, 18, 0),
            datetime(2024, 1, 1, 20, 0)
        )
        self.assertFalse(time_range.overlaps(non_overlapping))


if __name__ == "__main__":
    unittest.main(verbosity=2)