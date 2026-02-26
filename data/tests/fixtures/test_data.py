"""Test data fixtures for parking management system tests."""

import pytest
import json
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Any, Optional, Union
from decimal import Decimal
import random
import string
from pathlib import Path

# Try to import models if available
try:
    from app.models import (
        User, ParkingSpot, Vehicle, Reservation,
        RecurringReservation, WaitlistEntry, ReservationHistory,
        ReservationNote, ReservationAddon, Payment
    )
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    # Create mock classes for testing
    class MockModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    User = MockModel
    ParkingSpot = MockModel
    Vehicle = MockModel
    Reservation = MockModel
    RecurringReservation = MockModel
    WaitlistEntry = MockModel
    ReservationHistory = MockModel
    ReservationNote = MockModel
    ReservationAddon = MockModel
    Payment = MockModel


# ============================================================================
# Basic Data Fixtures
# ============================================================================

@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Return sample user data."""
    return {
        'id': 5,
        'email': 'john.doe@example.com',
        'full_name': 'John Doe',
        'phone': '+1234567890',
        'is_active': True,
        'metadata': {
            'preferences': {
                'notifications': True,
                'newsletter': False
            }
        },
        'created_at': datetime(2023, 1, 1, 10, 0, 0),
        'updated_at': datetime(2023, 1, 1, 10, 0, 0)
    }


@pytest.fixture
def sample_parking_spot_data() -> Dict[str, Any]:
    """Return sample parking spot data."""
    return {
        'id': 4,
        'spot_number': 'A4',
        'spot_type': 'standard',
        'hourly_rate': 3.00,
        'is_active': True,
        'location_level': 1,
        'location_section': 'A',
        'features': ['near_elevator', 'covered'],
        'created_at': datetime(2023, 1, 1, 10, 0, 0)
    }


@pytest.fixture
def sample_ev_spot_data() -> Dict[str, Any]:
    """Return sample EV charging spot data."""
    return {
        'id': 22,
        'spot_number': 'C2',
        'spot_type': 'ev_charging',
        'hourly_rate': 3.00,
        'charging_fee': 1.00,
        'charger_type': 'Level 2',
        'charger_power': '7.2 kW',
        'is_active': True,
        'location_level': 2,
        'location_section': 'C',
        'features': ['ev_charging', 'covered'],
        'created_at': datetime(2023, 1, 1, 10, 0, 0)
    }


@pytest.fixture
def sample_vip_spot_data() -> Dict[str, Any]:
    """Return sample VIP parking spot data."""
    return {
        'id': 18,
        'spot_number': 'VIP1',
        'spot_type': 'vip',
        'hourly_rate': 8.00,
        'is_active': True,
        'location_level': 1,
        'location_section': 'VIP',
        'features': ['valet', 'covered', 'security_camera'],
        'created_at': datetime(2023, 1, 1, 10, 0, 0)
    }


@pytest.fixture
def sample_vehicle_data() -> Dict[str, Any]:
    """Return sample vehicle data."""
    return {
        'id': 101,
        'user_id': 5,
        'license_plate': 'ABC-1234',
        'vehicle_type': 'sedan',
        'make': 'Toyota',
        'model': 'Camry',
        'color': 'Silver',
        'is_ev': False,
        'created_at': datetime(2023, 1, 1, 10, 0, 0)
    }


@pytest.fixture
def sample_ev_vehicle_data() -> Dict[str, Any]:
    """Return sample electric vehicle data."""
    return {
        'id': 109,
        'user_id': 13,
        'license_plate': 'EV-2024',
        'vehicle_type': 'sedan',
        'make': 'Tesla',
        'model': 'Model 3',
        'color': 'White',
        'is_ev': True,
        'battery_capacity': 75,  # kWh
        'created_at': datetime(2023, 1, 1, 10, 0, 0)
    }


@pytest.fixture
def sample_reservation_data() -> Dict[str, Any]:
    """Return sample reservation data."""
    return {
        'id': 201,
        'user_id': 5,
        'spot_id': 4,
        'vehicle_id': 101,
        'confirmation_code': 'CONF-001-ABCD',
        'reservation_type': 'standard',
        'status': 'completed',
        'start_time': datetime(2023, 12, 10, 9, 0, 0),
        'end_time': datetime(2023, 12, 10, 17, 0, 0),
        'total_amount': 20.00,
        'payment_status': 'paid',
        'payment_id': 301,
        'special_requests': 'Near elevator please',
        'created_at': datetime(2023, 12, 1, 14, 30, 0),
        'confirmed_at': datetime(2023, 12, 1, 14, 35, 0),
        'checked_in_at': datetime(2023, 12, 10, 8, 45, 0),
        'checked_out_at': datetime(2023, 12, 10, 17, 15, 0),
        'completed_at': datetime(2023, 12, 10, 17, 15, 0),
        'metadata': {
            'source': 'mobile_app',
            'promo_code': 'WELCOME10',
            'customer_rating': 5
        }
    }


@pytest.fixture
def sample_ev_reservation_data() -> Dict[str, Any]:
    """Return sample EV charging reservation data."""
    return {
        'id': 208,
        'user_id': 13,
        'spot_id': 22,
        'vehicle_id': 109,
        'confirmation_code': 'CONF-008-CDEF',
        'reservation_type': 'ev_charging',
        'status': 'completed',
        'start_time': datetime(2023, 12, 27, 14, 0, 0),
        'end_time': datetime(2023, 12, 27, 18, 0, 0),
        'total_amount': 16.00,
        'charging_fee': 4.00,
        'energy_used_kwh': 32,
        'payment_status': 'paid',
        'payment_id': 308,
        'created_at': datetime(2023, 12, 21, 16, 30, 0),
        'confirmed_at': datetime(2023, 12, 21, 16, 35, 0),
        'checked_in_at': datetime(2023, 12, 27, 13, 55, 0),
        'checked_out_at': datetime(2023, 12, 27, 18, 5, 0),
        'completed_at': datetime(2023, 12, 27, 18, 5, 0),
        'metadata': {
            'charger_type': 'Level 2',
            'charge_start': datetime(2023, 12, 27, 14, 5, 0),
            'charge_end': datetime(2023, 12, 27, 17, 55, 0)
        }
    }


@pytest.fixture
def sample_vip_reservation_data() -> Dict[str, Any]:
    """Return sample VIP reservation data."""
    return {
        'id': 209,
        'user_id': 15,
        'spot_id': 18,
        'vehicle_id': 110,
        'confirmation_code': 'CONF-009-GHIJ',
        'reservation_type': 'vip',
        'status': 'completed',
        'start_time': datetime(2023, 12, 28, 19, 0, 0),
        'end_time': datetime(2023, 12, 28, 23, 30, 0),
        'total_amount': 40.00,
        'payment_status': 'paid',
        'payment_id': 309,
        'special_requests': 'Valet service needed',
        'created_at': datetime(2023, 12, 22, 10, 45, 0),
        'confirmed_at': datetime(2023, 12, 22, 10, 50, 0),
        'checked_in_at': datetime(2023, 12, 28, 18, 55, 0),
        'checked_out_at': datetime(2023, 12, 28, 23, 35, 0),
        'completed_at': datetime(2023, 12, 28, 23, 35, 0),
        'metadata': {
            'valet_id': 'VAL-123',
            'vehicle_location': 'Level 1, Row A'
        }
    }


@pytest.fixture
def sample_cancelled_reservation_data() -> Dict[str, Any]:
    """Return sample cancelled reservation data."""
    return {
        'id': 206,
        'user_id': 10,
        'spot_id': 4,
        'vehicle_id': 107,
        'confirmation_code': 'CONF-006-UVWX',
        'reservation_type': 'standard',
        'status': 'cancelled',
        'start_time': datetime(2023, 12, 23, 11, 0, 0),
        'end_time': datetime(2023, 12, 23, 15, 0, 0),
        'total_amount': 12.00,
        'payment_status': 'refunded',
        'payment_id': 306,
        'created_at': datetime(2023, 12, 19, 15, 45, 0),
        'confirmed_at': datetime(2023, 12, 19, 15, 50, 0),
        'cancelled_at': datetime(2023, 12, 22, 9, 30, 0),
        'cancellation_reason': 'Change of plans',
        'metadata': {
            'refund_amount': 12.00,
            'refund_processed_at': datetime(2023, 12, 22, 10, 0, 0)
        }
    }


@pytest.fixture
def sample_pending_reservation_data() -> Dict[str, Any]:
    """Return sample pending reservation data."""
    return {
        'id': 246,
        'user_id': 10,
        'spot_id': 8,
        'vehicle_id': 107,
        'confirmation_code': 'CONF-046-MNOP',
        'reservation_type': 'standard',
        'status': 'pending',
        'start_time': datetime(2024, 3, 15, 14, 0, 0),
        'end_time': datetime(2024, 3, 15, 18, 0, 0),
        'total_amount': 12.00,
        'payment_status': 'pending',
        'created_at': datetime(2024, 3, 14, 22, 30, 0),
        'metadata': {
            'payment_method': 'credit_card',
            'requires_verification': True
        }
    }


@pytest.fixture
def sample_recurring_reservation_data() -> Dict[str, Any]:
    """Return sample recurring reservation data."""
    return {
        'id': 1,
        'user_id': 5,
        'spot_id': 4,
        'vehicle_id': 101,
        'pattern_id': 'REC-001',
        'frequency': 'weekly',
        'start_date': date(2024, 1, 8),
        'end_date': date(2024, 3, 25),
        'start_time': time(9, 0),
        'end_time': time(17, 0),
        'days_of_week': [1, 3, 5],  # Monday, Wednesday, Friday
        'total_amount_per_occurrence': 24.00,
        'is_active': True,
        'created_at': datetime(2024, 1, 1, 10, 0, 0)
    }


@pytest.fixture
def sample_monthly_recurring_data() -> Dict[str, Any]:
    """Return sample monthly recurring reservation data."""
    return {
        'id': 3,
        'user_id': 15,
        'spot_id': 18,
        'vehicle_id': 110,
        'pattern_id': 'REC-003',
        'frequency': 'monthly',
        'start_date': date(2024, 1, 5),
        'end_date': date(2024, 6, 7),
        'start_time': time(19, 0),
        'end_time': time(23, 30),
        'day_of_month': 5,
        'total_amount_per_occurrence': 45.00,
        'is_active': True,
        'created_at': datetime(2023, 12, 15, 16, 45, 0)
    }


@pytest.fixture
def sample_waitlist_data() -> Dict[str, Any]:
    """Return sample waitlist entry data."""
    return {
        'id': 1,
        'user_id': 17,
        'spot_id': 18,
        'date_from': datetime(2024, 1, 20, 18, 0, 0),
        'date_to': datetime(2024, 1, 20, 22, 0, 0),
        'status': 'active',
        'position': 1,
        'created_at': datetime(2024, 1, 10, 9, 30, 0)
    }


@pytest.fixture
def sample_notified_waitlist_data() -> Dict[str, Any]:
    """Return sample notified waitlist entry data."""
    return {
        'id': 4,
        'user_id': 5,
        'spot_id': 4,
        'date_from': datetime(2024, 1, 25, 9, 0, 0),
        'date_to': datetime(2024, 1, 25, 17, 0, 0),
        'status': 'notified',
        'position': 1,
        'notified_at': datetime(2024, 1, 18, 10, 30, 0),
        'created_at': datetime(2024, 1, 10, 8, 15, 0)
    }


@pytest.fixture
def sample_reservation_history_data() -> List[Dict[str, Any]]:
    """Return sample reservation history data."""
    return [
        {
            'id': 1,
            'reservation_id': 201,
            'status': 'pending',
            'changed_at': datetime(2023, 12, 1, 14, 30, 0),
            'changed_by': 'system'
        },
        {
            'id': 2,
            'reservation_id': 201,
            'status': 'confirmed',
            'changed_at': datetime(2023, 12, 1, 14, 35, 0),
            'changed_by': 'system'
        },
        {
            'id': 3,
            'reservation_id': 201,
            'status': 'checked_in',
            'changed_at': datetime(2023, 12, 10, 8, 45, 0),
            'changed_by': 'gate'
        },
        {
            'id': 4,
            'reservation_id': 201,
            'status': 'completed',
            'changed_at': datetime(2023, 12, 10, 17, 15, 0),
            'changed_by': 'gate'
        }
    ]


@pytest.fixture
def sample_reservation_note_data() -> List[Dict[str, Any]]:
    """Return sample reservation note data."""
    return [
        {
            'id': 1,
            'reservation_id': 201,
            'user_id': 5,
            'note': 'Customer requested parking near elevator due to mobility issues',
            'is_private': False,
            'created_at': datetime(2023, 12, 1, 14, 35, 0)
        },
        {
            'id': 2,
            'reservation_id': 201,
            'user_id': 3,
            'note': 'Assigned spot 4 - near elevator',
            'is_private': True,
            'created_at': datetime(2023, 12, 1, 14, 40, 0)
        },
        {
            'id': 3,
            'reservation_id': 209,
            'user_id': 15,
            'note': 'VIP customer - anniversary celebration, please ensure spot is clean',
            'is_private': True,
            'created_at': datetime(2023, 12, 22, 10, 50, 0)
        }
    ]


@pytest.fixture
def sample_reservation_addon_data() -> List[Dict[str, Any]]:
    """Return sample reservation addon data."""
    return [
        {
            'id': 1,
            'reservation_id': 209,
            'addon_type': 'valet',
            'quantity': 1,
            'unit_price': 15.00,
            'total_price': 15.00,
            'created_at': datetime(2023, 12, 22, 10, 50, 0)
        },
        {
            'id': 2,
            'reservation_id': 217,
            'addon_type': 'valet',
            'quantity': 1,
            'unit_price': 15.00,
            'total_price': 15.00,
            'created_at': datetime(2024, 1, 8, 15, 25, 0)
        },
        {
            'id': 3,
            'reservation_id': 217,
            'addon_type': 'car_wash',
            'quantity': 1,
            'unit_price': 25.00,
            'total_price': 25.00,
            'created_at': datetime(2024, 1, 8, 15, 25, 0)
        }
    ]


@pytest.fixture
def sample_payment_data() -> Dict[str, Any]:
    """Return sample payment data."""
    return {
        'id': 301,
        'reservation_id': 201,
        'amount': 20.00,
        'status': 'completed',
        'payment_method': 'credit_card',
        'transaction_id': 'ch_123456789',
        'card_last4': '4242',
        'created_at': datetime(2023, 12, 1, 14, 35, 0),
        'metadata': {
            'receipt_url': 'https://payments.example.com/receipt/123'
        }
    }


# ============================================================================
# Model Instance Fixtures
# ============================================================================

@pytest.fixture
def sample_user(sample_user_data) -> User:
    """Return a sample User model instance."""
    return User(**sample_user_data)


@pytest.fixture
def sample_parking_spot(sample_parking_spot_data) -> ParkingSpot:
    """Return a sample ParkingSpot model instance."""
    return ParkingSpot(**sample_parking_spot_data)


@pytest.fixture
def sample_ev_spot(sample_ev_spot_data) -> ParkingSpot:
    """Return a sample EV ParkingSpot model instance."""
    return ParkingSpot(**sample_ev_spot_data)


@pytest.fixture
def sample_vip_spot(sample_vip_spot_data) -> ParkingSpot:
    """Return a sample VIP ParkingSpot model instance."""
    return ParkingSpot(**sample_vip_spot_data)


@pytest.fixture
def sample_vehicle(sample_vehicle_data) -> Vehicle:
    """Return a sample Vehicle model instance."""
    return Vehicle(**sample_vehicle_data)


@pytest.fixture
def sample_ev_vehicle(sample_ev_vehicle_data) -> Vehicle:
    """Return a sample EV Vehicle model instance."""
    return Vehicle(**sample_ev_vehicle_data)


@pytest.fixture
def sample_reservation(sample_reservation_data) -> Reservation:
    """Return a sample Reservation model instance."""
    return Reservation(**sample_reservation_data)


@pytest.fixture
def sample_ev_reservation(sample_ev_reservation_data) -> Reservation:
    """Return a sample EV Reservation model instance."""
    return Reservation(**sample_ev_reservation_data)


@pytest.fixture
def sample_vip_reservation(sample_vip_reservation_data) -> Reservation:
    """Return a sample VIP Reservation model instance."""
    return Reservation(**sample_vip_reservation_data)


@pytest.fixture
def sample_cancelled_reservation(sample_cancelled_reservation_data) -> Reservation:
    """Return a sample cancelled Reservation model instance."""
    return Reservation(**sample_cancelled_reservation_data)


@pytest.fixture
def sample_pending_reservation(sample_pending_reservation_data) -> Reservation:
    """Return a sample pending Reservation model instance."""
    return Reservation(**sample_pending_reservation_data)


@pytest.fixture
def sample_recurring_reservation(sample_recurring_reservation_data) -> RecurringReservation:
    """Return a sample RecurringReservation model instance."""
    return RecurringReservation(**sample_recurring_reservation_data)


@pytest.fixture
def sample_monthly_recurring(sample_monthly_recurring_data) -> RecurringReservation:
    """Return a sample monthly RecurringReservation model instance."""
    return RecurringReservation(**sample_monthly_recurring_data)


@pytest.fixture
def sample_waitlist_entry(sample_waitlist_data) -> WaitlistEntry:
    """Return a sample WaitlistEntry model instance."""
    return WaitlistEntry(**sample_waitlist_data)


@pytest.fixture
def sample_notified_waitlist(sample_notified_waitlist_data) -> WaitlistEntry:
    """Return a sample notified WaitlistEntry model instance."""
    return WaitlistEntry(**sample_notified_waitlist_data)


@pytest.fixture
def sample_history_entries(sample_reservation_history_data) -> List[ReservationHistory]:
    """Return sample ReservationHistory model instances."""
    return [ReservationHistory(**data) for data in sample_reservation_history_data]


@pytest.fixture
def sample_note_entries(sample_reservation_note_data) -> List[ReservationNote]:
    """Return sample ReservationNote model instances."""
    return [ReservationNote(**data) for data in sample_reservation_note_data]


@pytest.fixture
def sample_addon_entries(sample_reservation_addon_data) -> List[ReservationAddon]:
    """Return sample ReservationAddon model instances."""
    return [ReservationAddon(**data) for data in sample_reservation_addon_data]


@pytest.fixture
def sample_payment(sample_payment_data) -> Payment:
    """Return a sample Payment model instance."""
    return Payment(**sample_payment_data)


# ============================================================================
# Collection Fixtures
# ============================================================================

@pytest.fixture
def sample_users_list() -> List[Dict[str, Any]]:
    """Return a list of sample users."""
    return [
        {
            'id': 5,
            'email': 'john.doe@example.com',
            'full_name': 'John Doe',
            'phone': '+1234567890',
            'is_active': True
        },
        {
            'id': 7,
            'email': 'jane.smith@example.com',
            'full_name': 'Jane Smith',
            'phone': '+1234567891',
            'is_active': True
        },
        {
            'id': 8,
            'email': 'bob.johnson@example.com',
            'full_name': 'Bob Johnson',
            'phone': '+1234567892',
            'is_active': True
        },
        {
            'id': 9,
            'email': 'alice.williams@example.com',
            'full_name': 'Alice Williams',
            'phone': '+1234567893',
            'is_active': False
        }
    ]


@pytest.fixture
def sample_spots_list() -> List[Dict[str, Any]]:
    """Return a list of sample parking spots."""
    return [
        {
            'id': 4,
            'spot_number': 'A4',
            'spot_type': 'standard',
            'hourly_rate': 3.00,
            'is_active': True
        },
        {
            'id': 12,
            'spot_number': 'B12',
            'spot_type': 'standard',
            'hourly_rate': 3.00,
            'is_active': True
        },
        {
            'id': 18,
            'spot_number': 'VIP1',
            'spot_type': 'vip',
            'hourly_rate': 8.00,
            'is_active': True
        },
        {
            'id': 22,
            'spot_number': 'C2',
            'spot_type': 'ev_charging',
            'hourly_rate': 3.00,
            'charging_fee': 1.00,
            'is_active': True
        }
    ]


@pytest.fixture
def sample_vehicles_list() -> List[Dict[str, Any]]:
    """Return a list of sample vehicles."""
    return [
        {
            'id': 101,
            'user_id': 5,
            'license_plate': 'ABC-1234',
            'vehicle_type': 'sedan',
            'is_ev': False
        },
        {
            'id': 102,
            'user_id': 7,
            'license_plate': 'XYZ-5678',
            'vehicle_type': 'suv',
            'is_ev': False
        },
        {
            'id': 109,
            'user_id': 13,
            'license_plate': 'EV-2024',
            'vehicle_type': 'sedan',
            'is_ev': True
        }
    ]


@pytest.fixture
def sample_reservations_list() -> List[Dict[str, Any]]:
    """Return a list of sample reservations."""
    return [
        {
            'id': 201,
            'user_id': 5,
            'spot_id': 4,
            'status': 'completed',
            'start_time': datetime(2023, 12, 10, 9, 0, 0),
            'end_time': datetime(2023, 12, 10, 17, 0, 0),
            'total_amount': 20.00
        },
        {
            'id': 202,
            'user_id': 7,
            'spot_id': 12,
            'status': 'completed',
            'start_time': datetime(2023, 12, 15, 10, 30, 0),
            'end_time': datetime(2023, 12, 15, 14, 30, 0),
            'total_amount': 12.00
        },
        {
            'id': 215,
            'user_id': 20,
            'spot_id': 5,
            'status': 'checked_in',
            'start_time': datetime(2024, 1, 15, 8, 0, 0),
            'end_time': datetime(2024, 1, 15, 17, 0, 0),
            'total_amount': 27.00
        },
        {
            'id': 218,
            'user_id': 5,
            'spot_id': 4,
            'status': 'confirmed',
            'start_time': datetime(2024, 1, 20, 9, 0, 0),
            'end_time': datetime(2024, 1, 20, 17, 0, 0),
            'total_amount': 24.00
        }
    ]


# ============================================================================
# Factory Fixtures
# ============================================================================

@pytest.fixture
def user_factory():
    """Factory for creating user instances with custom data."""
    
    def _create_user(**kwargs):
        base_data = {
            'id': random.randint(1000, 9999),
            'email': f"user{random.randint(1, 999)}@example.com",
            'full_name': f"Test User {random.randint(1, 999)}",
            'phone': f"+1{random.randint(1000000000, 9999999999)}",
            'is_active': True,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        base_data.update(kwargs)
        return User(**base_data) if MODELS_AVAILABLE else base_data
    
    return _create_user


@pytest.fixture
def parking_spot_factory():
    """Factory for creating parking spot instances with custom data."""
    
    def _create_spot(**kwargs):
        spot_types = ['standard', 'vip', 'ev_charging', 'oversize', 'disabled']
        spot_type = kwargs.get('spot_type', random.choice(spot_types))
        
        base_data = {
            'id': random.randint(100, 999),
            'spot_number': f"{random.choice(string.ascii_uppercase)}{random.randint(1, 99)}",
            'spot_type': spot_type,
            'hourly_rate': random.choice([2.50, 3.00, 3.50, 4.00, 5.00, 8.00]),
            'is_active': True,
            'location_level': random.randint(1, 5),
            'location_section': random.choice(['A', 'B', 'C', 'D', 'VIP']),
            'created_at': datetime.now()
        }
        
        if spot_type == 'ev_charging':
            base_data.update({
                'charging_fee': random.choice([0.50, 0.75, 1.00]),
                'charger_type': random.choice(['Level 1', 'Level 2', 'DC Fast']),
                'charger_power': random.choice(['3.3 kW', '7.2 kW', '50 kW', '150 kW'])
            })
        
        base_data.update(kwargs)
        return ParkingSpot(**base_data) if MODELS_AVAILABLE else base_data
    
    return _create_spot


@pytest.fixture
def vehicle_factory():
    """Factory for creating vehicle instances with custom data."""
    
    def _create_vehicle(**kwargs):
        makes = ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'Tesla', 'BMW', 'Mercedes']
        models = ['Camry', 'Civic', 'F-150', 'Model 3', 'X5', 'C-Class']
        colors = ['Red', 'Blue', 'Silver', 'Black', 'White', 'Gray']
        
        is_ev = kwargs.get('is_ev', random.choice([True, False]))
        
        base_data = {
            'id': random.randint(1000, 9999),
            'user_id': random.randint(1, 100),
            'license_plate': f"{''.join(random.choices(string.ascii_uppercase, k=3))}-{random.randint(100, 999)}",
            'vehicle_type': random.choice(['sedan', 'suv', 'truck', 'hatchback', 'coupe']),
            'make': random.choice(makes),
            'model': random.choice(models),
            'color': random.choice(colors),
            'is_ev': is_ev,
            'created_at': datetime.now()
        }
        
        if is_ev:
            base_data.update({
                'battery_capacity': random.choice([50, 60, 75, 85, 100])
            })
        
        base_data.update(kwargs)
        return Vehicle(**base_data) if MODELS_AVAILABLE else base_data
    
    return _create_vehicle


@pytest.fixture
def reservation_factory():
    """Factory for creating reservation instances with custom data."""
    
    def _create_reservation(**kwargs):
        statuses = ['pending', 'confirmed', 'checked_in', 'completed', 'cancelled', 'no_show']
        types = ['standard', 'vip', 'ev_charging', 'oversize']
        
        start_time = kwargs.get('start_time', datetime.now() + timedelta(days=random.randint(1, 30)))
        end_time = kwargs.get('end_time', start_time + timedelta(hours=random.randint(2, 8)))
        
        # Calculate duration in hours
        duration = (end_time - start_time).total_seconds() / 3600
        
        # Base rate calculation
        spot_type = kwargs.get('reservation_type', random.choice(types))
        hourly_rate = {
            'standard': 3.00,
            'vip': 8.00,
            'ev_charging': 3.00,
            'oversize': 5.00
        }.get(spot_type, 3.00)
        
        total_amount = duration * hourly_rate
        
        # Add charging fee if applicable
        charging_fee = None
        if spot_type == 'ev_charging':
            charging_fee = duration * 1.00  # $1 per hour charging fee
            total_amount += charging_fee
        
        base_data = {
            'id': random.randint(1000, 9999),
            'user_id': random.randint(1, 100),
            'spot_id': random.randint(1, 50),
            'vehicle_id': random.randint(1, 100),
            'confirmation_code': f"CONF-{random.randint(100, 999)}-{''.join(random.choices(string.ascii_uppercase, k=4))}",
            'reservation_type': spot_type,
            'status': random.choice(statuses),
            'start_time': start_time,
            'end_time': end_time,
            'total_amount': round(total_amount, 2),
            'payment_status': random.choice(['pending', 'paid', 'failed', 'refunded']),
            'created_at': datetime.now() - timedelta(days=random.randint(1, 10)),
            'metadata': {}
        }
        
        if charging_fee:
            base_data['charging_fee'] = round(charging_fee, 2)
            base_data['energy_used_kwh'] = random.randint(20, 50)
        
        # Add timestamps based on status
        if base_data['status'] in ['confirmed', 'checked_in', 'completed', 'cancelled']:
            base_data['confirmed_at'] = base_data['created_at'] + timedelta(minutes=random.randint(5, 60))
        
        if base_data['status'] in ['checked_in', 'completed']:
            base_data['checked_in_at'] = base_data['start_time'] - timedelta(minutes=random.randint(5, 30))
        
        if base_data['status'] == 'completed':
            base_data['checked_out_at'] = base_data['end_time'] + timedelta(minutes=random.randint(5, 30))
            base_data['completed_at'] = base_data['checked_out_at']
        
        if base_data['status'] == 'cancelled':
            base_data['cancelled_at'] = base_data['start_time'] - timedelta(days=random.randint(1, 3))
            base_data['cancellation_reason'] = random.choice([
                'Change of plans', 'Weather', 'Emergency', 'Duplicate booking'
            ])
        
        base_data.update(kwargs)
        return Reservation(**base_data) if MODELS_AVAILABLE else base_data
    
    return _create_reservation


@pytest.fixture
def recurring_reservation_factory():
    """Factory for creating recurring reservation instances."""
    
    def _create_recurring(**kwargs):
        frequencies = ['daily', 'weekly', 'monthly', 'weekdays']
        frequency = kwargs.get('frequency', random.choice(frequencies))
        
        base_data = {
            'id': random.randint(1, 100),
            'user_id': random.randint(1, 100),
            'spot_id': random.randint(1, 50),
            'vehicle_id': random.randint(1, 100),
            'pattern_id': f"REC-{random.randint(100, 999)}",
            'frequency': frequency,
            'start_date': date.today() + timedelta(days=random.randint(1, 30)),
            'end_date': date.today() + timedelta(days=random.randint(60, 180)),
            'start_time': time(random.randint(8, 10), 0),
            'end_time': time(random.randint(16, 18), 0),
            'total_amount_per_occurrence': round(random.uniform(15, 50), 2),
            'is_active': random.choice([True, False]),
            'created_at': datetime.now() - timedelta(days=random.randint(1, 30))
        }
        
        if frequency == 'weekly':
            base_data['days_of_week'] = random.sample(range(7), k=random.randint(2, 5))
        elif frequency == 'monthly':
            base_data['day_of_month'] = random.randint(1, 28)
        elif frequency == 'weekdays':
            base_data['days_of_week'] = [1, 2, 3, 4, 5]  # Monday to Friday
        
        base_data.update(kwargs)
        return RecurringReservation(**base_data) if MODELS_AVAILABLE else base_data
    
    return _create_recurring


@pytest.fixture
def waitlist_factory():
    """Factory for creating waitlist entries."""
    
    def _create_waitlist(**kwargs):
        base_data = {
            'id': random.randint(1, 1000),
            'user_id': random.randint(1, 100),
            'spot_id': random.randint(1, 50),
            'date_from': datetime.now() + timedelta(days=random.randint(1, 14)),
            'date_to': datetime.now() + timedelta(days=random.randint(1, 14), hours=random.randint(2, 8)),
            'status': random.choice(['active', 'notified', 'expired', 'converted']),
            'position': random.randint(1, 10),
            'created_at': datetime.now() - timedelta(days=random.randint(1, 10))
        }
        
        if base_data['status'] == 'notified':
            base_data['notified_at'] = base_data['created_at'] + timedelta(days=random.randint(1, 5))
        
        base_data.update(kwargs)
        return WaitlistEntry(**base_data) if MODELS_AVAILABLE else base_data
    
    return _create_waitlist


@pytest.fixture
def addon_factory():
    """Factory for creating reservation addons."""
    
    def _create_addon(**kwargs):
        addon_types = ['valet', 'car_wash', 'champagne', 'flowers', 'charging', 'security']
        addon_type = kwargs.get('addon_type', random.choice(addon_types))
        
        prices = {
            'valet': 15.00,
            'car_wash': 25.00,
            'champagne': 35.00,
            'flowers': 20.00,
            'charging': 5.00,
            'security': 10.00
        }
        
        unit_price = prices.get(addon_type, 10.00)
        quantity = kwargs.get('quantity', random.randint(1, 3))
        
        base_data = {
            'id': random.randint(1, 1000),
            'reservation_id': random.randint(100, 999),
            'addon_type': addon_type,
            'quantity': quantity,
            'unit_price': unit_price,
            'total_price': unit_price * quantity,
            'created_at': datetime.now() - timedelta(days=random.randint(1, 10))
        }
        
        base_data.update(kwargs)
        return ReservationAddon(**base_data) if MODELS_AVAILABLE else base_data
    
    return _create_addon


# ============================================================================
# Time-based Fixtures
# ============================================================================

@pytest.fixture
def current_time() -> datetime:
    """Return current datetime."""
    return datetime.now()


@pytest.fixture
def yesterday() -> datetime:
    """Return yesterday's datetime."""
    return datetime.now() - timedelta(days=1)


@pytest.fixture
def tomorrow() -> datetime:
    """Return tomorrow's datetime."""
    return datetime.now() + timedelta(days=1)


@pytest.fixture
def next_week() -> datetime:
    """Return datetime one week from now."""
    return datetime.now() + timedelta(days=7)


@pytest.fixture
def next_month() -> datetime:
    """Return datetime one month from now."""
    return datetime.now() + timedelta(days=30)


@pytest.fixture
def last_month() -> datetime:
    """Return datetime one month ago."""
    return datetime.now() - timedelta(days=30)


@pytest.fixture
def business_hours_start() -> time:
    """Return business hours start time (9 AM)."""
    return time(9, 0)


@pytest.fixture
def business_hours_end() -> time:
    """Return business hours end time (5 PM)."""
    return time(17, 0)


@pytest.fixture
def evening_hours_start() -> time:
    """Return evening hours start time (6 PM)."""
    return time(18, 0)


@pytest.fixture
def evening_hours_end() -> time:
    """Return evening hours end time (10 PM)."""
    return time(22, 0)


# ============================================================================
# Scenario-based Fixtures
# ============================================================================

@pytest.fixture
def peak_hour_scenario() -> Dict[str, Any]:
    """Return data for peak hour testing scenario."""
    return {
        'peak_hours': [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
        'occupancy_rates': {
            8: 0.8, 9: 0.9, 10: 0.95, 11: 0.95, 12: 0.9,
            13: 0.85, 14: 0.8, 15: 0.75, 16: 0.7, 17: 0.6
        },
        'average_wait_time': 15,  # minutes
        'price_multiplier': 1.5
    }


@pytest.fixture
def holiday_scenario() -> Dict[str, Any]:
    """Return data for holiday testing scenario."""
    return {
        'holiday_dates': [
            date(2024, 1, 1),   # New Year's Day
            date(2024, 12, 25),  # Christmas
            date(2024, 7, 4),    # Independence Day
        ],
        'occupancy_rate': 0.3,  # Lower occupancy on holidays
        'special_hours': {
            'open': time(10, 0),
            'close': time(18, 0)
        }
    }


@pytest.fixture
def event_scenario() -> Dict[str, Any]:
    """Return data for special event testing scenario."""
    return {
        'event_name': 'Concert at Arena',
        'event_date': date(2024, 3, 15),
        'event_time': time(19, 30),
        'impacted_spots': [4, 5, 6, 7, 8, 9, 10],
        'expected_demand': 'high',
        'price_surge': 2.0,
        'booking_window': 30,  # days before event
        'average_duration': 4  # hours
    }


@pytest.fixture
def weather_scenario() -> Dict[str, Any]:
    """Return data for weather impact testing scenario."""
    return {
        'weather_types': {
            'sunny': {'occupancy_factor': 1.0, 'cancellation_factor': 0.05},
            'rainy': {'occupancy_factor': 0.7, 'cancellation_factor': 0.15},
            'snowy': {'occupancy_factor': 0.5, 'cancellation_factor': 0.25},
            'storm': {'occupancy_factor': 0.3, 'cancellation_factor': 0.4}
        },
        'preferred_spots': ['covered', 'indoor']
    }


# ============================================================================
# JSON Data Fixtures
# ============================================================================

@pytest.fixture
def seed_data_path() -> Path:
    """Return path to seed data file."""
    return Path(__file__).parent / "seed_data.json"


@pytest.fixture
def seed_data(seed_data_path) -> Dict[str, Any]:
    """Load and return seed data from JSON file."""
    if seed_data_path.exists():
        with open(seed_data_path, 'r') as f:
            return json.load(f)
    else:
        # Return empty dict if file doesn't exist
        return {}


@pytest.fixture
def seed_reservations(seed_data) -> List[Dict[str, Any]]:
    """Return reservations from seed data."""
    return seed_data.get('reservations', [])


@pytest.fixture
def seed_recurring(seed_data) -> List[Dict[str, Any]]:
    """Return recurring reservations from seed data."""
    return seed_data.get('recurring_reservations', [])


@pytest.fixture
def seed_waitlist(seed_data) -> List[Dict[str, Any]]:
    """Return waitlist entries from seed data."""
    return seed_data.get('waitlist', [])


@pytest.fixture
def seed_metadata(seed_data) -> Dict[str, Any]:
    """Return metadata from seed data."""
    return seed_data.get('metadata', {})


# ============================================================================
# Helper Function Fixtures
# ============================================================================

@pytest.fixture
def generate_confirmation_code() -> str:
    """Generate a random confirmation code."""
    return f"CONF-{random.randint(100, 999)}-{''.join(random.choices(string.ascii_uppercase, k=4))}"


@pytest.fixture
def generate_license_plate() -> str:
    """Generate a random license plate."""
    return f"{''.join(random.choices(string.ascii_uppercase, k=3))}-{random.randint(100, 999)}"


@pytest.fixture
def calculate_parking_cost() -> callable:
    """Calculate parking cost based on spot type and duration."""
    
    def _calculate(spot_type: str, start: datetime, end: datetime, 
                   has_addons: bool = False) -> Dict[str, float]:
        rates = {
            'standard': 3.00,
            'vip': 8.00,
            'ev_charging': 3.00,
            'oversize': 5.00,
            'disabled': 2.50
        }
        
        hours = (end - start).total_seconds() / 3600
        base_cost = hours * rates.get(spot_type, 3.00)
        
        addon_costs = 0
        if has_addons:
            if spot_type == 'vip':
                addon_costs += 15.00  # valet
            if spot_type == 'ev_charging':
                addon_costs += hours * 1.00  # charging fee
        
        return {
            'hours': round(hours, 1),
            'base_cost': round(base_cost, 2),
            'addon_costs': round(addon_costs, 2),
            'total_cost': round(base_cost + addon_costs, 2)
        }
    
    return _calculate


@pytest.fixture
def validate_reservation_overlap() -> callable:
    """Check if two reservations overlap."""
    
    def _validate(res1_start: datetime, res1_end: datetime,
                  res2_start: datetime, res2_end: datetime) -> bool:
        return (res1_start < res2_end and res2_start < res1_end)
    
    return _validate


@pytest.fixture
def generate_time_slots() -> callable:
    """Generate time slots for a given date range."""
    
    def _generate(start_date: date, end_date: date, 
                  slot_duration: int = 60) -> List[Dict[str, datetime]]:
        slots = []
        current = datetime.combine(start_date, time(0, 0))
        end = datetime.combine(end_date + timedelta(days=1), time(0, 0))
        
        while current < end:
            slot_end = current + timedelta(minutes=slot_duration)
            slots.append({
                'start': current,
                'end': slot_end
            })
            current = slot_end
        
        return slots
    
    return _generate