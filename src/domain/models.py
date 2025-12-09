# File: src/domain/models.py
"""
Domain Models for Parking Management System
Following Domain-Driven Design (DDD) principles with rich domain models

This module contains:
1. Value Objects: Immutable objects with no identity, only values
2. Entities: Objects with identity and lifecycle
3. Enums: Type enumerations for domain concepts
4. Domain Events: Events representing business occurrences

All models include validation and business logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import re
import uuid
from enum import Enum
import json


# ============================================================================
# DOMAIN PRIMITIVES / VALUE OBJECTS
# ============================================================================

@dataclass(frozen=True)  # Value objects are immutable
class LicensePlate:
    """
    Value Object: License plate number with validation
    Represents the unique identifier for a vehicle
    """
    value: str
    
    def __post_init__(self):
        """Validate license plate after initialization"""
        if not self.value:
            raise ValueError("License plate cannot be empty")
        
        # Remove whitespace and convert to uppercase
        object.__setattr__(self, 'value', self.value.strip().upper())
        
        # Basic validation - could be enhanced for specific regions
        if len(self.value) < 2 or len(self.value) > 10:
            raise ValueError(f"License plate must be 2-10 characters, got: {self.value}")
        
        # Alphanumeric with possible spaces and hyphens
        if not re.match(r'^[A-Z0-9\s\-]+$', self.value):
            raise ValueError(f"License plate can only contain letters, numbers, spaces, and hyphens: {self.value}")
    
    def __str__(self) -> str:
        return self.value
    
    def format_for_display(self) -> str:
        """Format license plate for display purposes"""
        return f"🪪 {self.value}"


@dataclass(frozen=True)
class Location:
    """
    Value Object: Physical location with address and coordinates
    Immutable and validated
    """
    address: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    
    def __post_init__(self):
        """Validate location data"""
        if not self.address or len(self.address.strip()) < 5:
            raise ValueError("Address must be at least 5 characters")
        
        if not self.city or len(self.city.strip()) < 2:
            raise ValueError("City must be at least 2 characters")
        
        if not self.state or len(self.state.strip()) != 2:
            raise ValueError("State must be 2-character code")
        
        # Basic zip code validation (US format)
        if not re.match(r'^\d{5}(-\d{4})?$', self.zip_code):
            raise ValueError(f"Invalid zip code format: {self.zip_code}")
        
        # Coordinate validation if provided
        if self.latitude is not None:
            if not -90 <= self.latitude <= 90:
                raise ValueError(f"Latitude must be between -90 and 90: {self.latitude}")
        
        if self.longitude is not None:
            if not -180 <= self.longitude <= 180:
                raise ValueError(f"Longitude must be between -180 and 180: {self.longitude}")
    
    def __str__(self) -> str:
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"
    
    def get_coordinates(self) -> Optional[Tuple[float, float]]:
        """Get coordinates as tuple if available"""
        if self.latitude is not None and self.longitude is not None:
            return (self.latitude, self.longitude)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip_code": self.zip_code,
            "country": self.country,
            "latitude": self.latitude,
            "longitude": self.longitude
        }


@dataclass(frozen=True)
class Capacity:
    """
    Value Object: Parking capacity with validation
    Ensures non-negative values and valid ratios
    """
    regular: int
    ev: int
    disabled: int = 0
    premium: int = 0
    
    def __post_init__(self):
        """Validate capacity values"""
        if self.regular < 0 or self.ev < 0 or self.disabled < 0 or self.premium < 0:
            raise ValueError("Capacity values cannot be negative")
        
        total = self.total_capacity()
        if total == 0:
            raise ValueError("Total capacity must be greater than 0")
        
        # Ensure reasonable ratios (business rule)
        if self.ev > total * 0.5:  # EV slots shouldn't exceed 50% of total
            raise ValueError(f"EV slots ({self.ev}) exceed 50% of total capacity ({total})")
    
    def total_capacity(self) -> int:
        """Calculate total capacity"""
        return self.regular + self.ev + self.disabled + self.premium
    
    def get_by_type(self, slot_type: 'SlotType') -> int:
        """Get capacity for specific slot type"""
        if slot_type == SlotType.REGULAR:
            return self.regular
        elif slot_type == SlotType.EV:
            return self.ev
        elif slot_type == SlotType.DISABLED:
            return self.disabled
        elif slot_type == SlotType.PREMIUM:
            return self.premium
        else:
            return 0
    
    def __str__(self) -> str:
        parts = []
        if self.regular > 0:
            parts.append(f"{self.regular} regular")
        if self.ev > 0:
            parts.append(f"{self.ev} EV")
        if self.disabled > 0:
            parts.append(f"{self.disabled} disabled")
        if self.premium > 0:
            parts.append(f"{self.premium} premium")
        return f"Capacity: {', '.join(parts)}"


@dataclass(frozen=True)
class Money:
    """
    Value Object: Monetary amount with currency
    Provides arithmetic operations with validation
    """
    amount: Decimal
    currency: str = "USD"
    
    def __post_init__(self):
        """Validate money amount"""
        if self.amount < Decimal('0'):
            raise ValueError("Money amount cannot be negative")
        
        if len(self.currency) != 3:
            raise ValueError(f"Currency must be 3-letter code: {self.currency}")
    
    def __add__(self, other: 'Money') -> 'Money':
        """Add two money amounts (same currency only)"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} to {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        """Subtract money amounts (same currency only)"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        result = self.amount - other.amount
        if result < Decimal('0'):
            raise ValueError("Result cannot be negative")
        return Money(result, self.currency)
    
    def __mul__(self, multiplier: Decimal) -> 'Money':
        """Multiply money by a decimal"""
        if multiplier < Decimal('0'):
            raise ValueError("Multiplier cannot be negative")
        return Money(self.amount * multiplier, self.currency)
    
    def format(self) -> str:
        """Format money for display"""
        return f"${self.amount:.2f} {self.currency}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "amount": float(self.amount),
            "currency": self.currency
        }


@dataclass(frozen=True)
class TimeRange:
    """
    Value Object: Time range with start and end times
    Provides duration calculation and validation
    """
    start_time: datetime
    end_time: datetime
    
    def __post_init__(self):
        """Validate time range"""
        if self.end_time <= self.start_time:
            raise ValueError("End time must be after start time")
    
    @property
    def duration(self) -> timedelta:
        """Calculate duration of time range"""
        return self.end_time - self.start_time
    
    @property
    def duration_minutes(self) -> float:
        """Get duration in minutes"""
        return self.duration.total_seconds() / 60
    
    @property
    def duration_hours(self) -> float:
        """Get duration in hours"""
        return self.duration.total_seconds() / 3600
    
    def is_within(self, other: 'TimeRange') -> bool:
        """Check if this time range is completely within another"""
        return self.start_time >= other.start_time and self.end_time <= other.end_time
    
    def overlaps(self, other: 'TimeRange') -> bool:
        """Check if this time range overlaps with another"""
        return (self.start_time < other.end_time and 
                self.end_time > other.start_time)
    
    def __str__(self) -> str:
        start_str = self.start_time.strftime("%Y-%m-%d %H:%M")
        end_str = self.end_time.strftime("%Y-%m-%d %H:%M")
        return f"{start_str} to {end_str} ({self.duration_hours:.1f} hours)"


# ============================================================================
# ENUMS FOR DOMAIN TYPES
# ============================================================================

class VehicleType(Enum):
    """
    Enumeration of vehicle types
    Each type may have different parking requirements and rates
    """
    CAR = "car"                     # Standard passenger car
    MOTORCYCLE = "motorcycle"       # Motorcycle or scooter
    TRUCK = "truck"                 # Pickup truck or van
    BUS = "bus"                     # Bus or large vehicle
    EV_CAR = "ev_car"               # Electric car
    EV_MOTORCYCLE = "ev_motorcycle" # Electric motorcycle
    EV_TRUCK = "ev_truck"           # Electric truck
    
    @property
    def is_electric(self) -> bool:
        """Check if vehicle type is electric"""
        return self.value.startswith('ev_')
    
    @property
    def base_type(self) -> 'VehicleType':
        """Get the base (non-EV) vehicle type"""
        if self.is_electric:
            return VehicleType(self.value[3:])  # Remove 'ev_' prefix
        return self
    
    def get_parking_rate_multiplier(self) -> Decimal:
        """Get parking rate multiplier for this vehicle type"""
        multipliers = {
            VehicleType.CAR: Decimal('1.0'),
            VehicleType.MOTORCYCLE: Decimal('0.5'),  # 50% discount for motorcycles
            VehicleType.TRUCK: Decimal('1.5'),       # 50% premium for trucks
            VehicleType.BUS: Decimal('2.0'),         # 100% premium for buses
            VehicleType.EV_CAR: Decimal('0.9'),      # 10% discount for EVs
            VehicleType.EV_MOTORCYCLE: Decimal('0.45'),  # 55% total discount
            VehicleType.EV_TRUCK: Decimal('1.35'),   # 15% total discount
        }
        return multipliers.get(self, Decimal('1.0'))
    
    def __str__(self) -> str:
        """Human-readable string representation"""
        names = {
            VehicleType.CAR: "Car",
            VehicleType.MOTORCYCLE: "Motorcycle",
            VehicleType.TRUCK: "Truck",
            VehicleType.BUS: "Bus",
            VehicleType.EV_CAR: "Electric Car",
            VehicleType.EV_MOTORCYCLE: "Electric Motorcycle",
            VehicleType.EV_TRUCK: "Electric Truck",
        }
        return names.get(self, self.value.replace('_', ' ').title())


class SlotType(Enum):
    """
    Enumeration of parking slot types
    Different types have different features and restrictions
    """
    REGULAR = "regular"      # Standard parking slot
    EV = "ev"                # Electric vehicle charging slot
    DISABLED = "disabled"    # Accessible parking
    PREMIUM = "premium"      # Premium/covered parking
    RESERVED = "reserved"    # Reserved for specific users
    
    @property
    def hourly_rate(self) -> Money:
        """Get hourly rate for this slot type"""
        rates = {
            SlotType.REGULAR: Money(Decimal('5.00')),
            SlotType.EV: Money(Decimal('7.00')),      # Premium for charging
            SlotType.DISABLED: Money(Decimal('3.00')), # Discount for accessibility
            SlotType.PREMIUM: Money(Decimal('10.00')), # Premium for covered
            SlotType.RESERVED: Money(Decimal('8.00')), # Surcharge for reservation
        }
        return rates.get(self, Money(Decimal('5.00')))
    
    def can_accommodate(self, vehicle_type: VehicleType) -> bool:
        """
        Check if this slot type can accommodate the given vehicle type
        Business rule: EVs can use EV slots, regular slots (if allowed), but not disabled/reserved
        """
        if self == SlotType.DISABLED:
            # Only regular vehicles in disabled spots (special permit logic would be elsewhere)
            return vehicle_type in [VehicleType.CAR, VehicleType.EV_CAR]
        
        if self == SlotType.RESERVED:
            # Reserved slots have specific rules (handled by reservation system)
            return False
        
        if vehicle_type.is_electric:
            # EVs can use EV slots and regular slots
            return self in [SlotType.EV, SlotType.REGULAR, SlotType.PREMIUM]
        
        # Regular vehicles can use regular, premium, but not EV slots
        return self in [SlotType.REGULAR, SlotType.PREMIUM]
    
    def __str__(self) -> str:
        """Human-readable string representation"""
        names = {
            SlotType.REGULAR: "Regular",
            SlotType.EV: "EV Charging",
            SlotType.DISABLED: "Disabled",
            SlotType.PREMIUM: "Premium",
            SlotType.RESERVED: "Reserved",
        }
        return names.get(self, self.value.title())


class ChargerType(Enum):
    """
    Enumeration of EV charger types
    Different types have different power levels and connectors
    """
    LEVEL_1 = "level_1"        # 120V AC, ~1.4 kW
    LEVEL_2 = "level_2"        # 240V AC, ~7-19 kW
    DC_FAST = "dc_fast"        # 480V DC, ~50-350 kW
    TESLA = "tesla"            # Tesla Supercharger
    CHADEMO = "chademo"        # CHAdeMO standard
    CCS = "ccs"                # Combined Charging System
    
    @property
    def typical_power_kw(self) -> float:
        """Get typical power output in kilowatts"""
        powers = {
            ChargerType.LEVEL_1: 1.4,
            ChargerType.LEVEL_2: 7.2,
            ChargerType.DC_FAST: 50.0,
            ChargerType.TESLA: 150.0,
            ChargerType.CHADEMO: 50.0,
            ChargerType.CCS: 150.0,
        }
        return powers.get(self, 0.0)
    
    @property
    def charge_time_hours(self, battery_size_kwh: float = 60.0) -> float:
        """Estimate charge time for given battery size"""
        if self.typical_power_kw == 0:
            return 0.0
        return battery_size_kwh / self.typical_power_kw
    
    def is_compatible(self, vehicle_type: VehicleType) -> bool:
        """Check if charger is compatible with vehicle type"""
        if not vehicle_type.is_electric:
            return False
        
        # Business rules for charger compatibility
        compatibility = {
            VehicleType.EV_CAR: [ChargerType.LEVEL_1, ChargerType.LEVEL_2, 
                                ChargerType.DC_FAST, ChargerType.TESLA, 
                                ChargerType.CHADEMO, ChargerType.CCS],
            VehicleType.EV_MOTORCYCLE: [ChargerType.LEVEL_1, ChargerType.LEVEL_2],
            VehicleType.EV_TRUCK: [ChargerType.LEVEL_2, ChargerType.DC_FAST, 
                                  ChargerType.CCS],
        }
        
        return self in compatibility.get(vehicle_type, [])


class ParkingStatus(Enum):
    """
    Enumeration of parking session statuses
    """
    ACTIVE = "active"          # Currently parked
    COMPLETED = "completed"    # Parking session ended
    OVERDUE = "overdue"        # Exceeded allowed time
    RESERVED = "reserved"      # Slot is reserved
    MAINTENANCE = "maintenance" # Slot under maintenance


# ============================================================================
# DOMAIN ENTITIES
# ============================================================================

class Entity:
    """
    Base class for all domain entities
    Provides common functionality for entities with identity
    """
    
    def __init__(self, id: Optional[str] = None):
        self._id = id or str(uuid.uuid4())
    
    @property
    def id(self) -> str:
        """Get entity ID"""
        return self._id
    
    def __eq__(self, other: object) -> bool:
        """Entities are equal if they have the same ID and type"""
        if not isinstance(other, Entity):
            return False
        return self.id == other.id and type(self) == type(other)
    
    def __hash__(self) -> int:
        """Hash based on ID and type"""
        return hash((self.id, type(self).__name__))
    
    def __repr__(self) -> str:
        """Representation for debugging"""
        return f"{type(self).__name__}(id={self.id})"


class Vehicle(Entity):
    """
    Entity: Represents a vehicle with identity and attributes
    Core domain entity with business behavior
    """
    
    def __init__(
        self,
        license_plate: LicensePlate,
        make: str,
        model: str,
        year: int,
        color: str,
        vehicle_type: VehicleType,
        id: Optional[str] = None
    ):
        super().__init__(id)
        self.license_plate = license_plate
        self.make = make
        self.model = model
        self.year = year
        self.color = color
        self.vehicle_type = vehicle_type
        self._validate()
    
    def _validate(self) -> None:
        """Validate vehicle attributes"""
        if not self.make or len(self.make.strip()) < 2:
            raise ValueError("Vehicle make must be at least 2 characters")
        
        if not self.model or len(self.model.strip()) < 1:
            raise ValueError("Vehicle model cannot be empty")
        
        current_year = datetime.now().year
        if self.year < 1900 or self.year > current_year + 1:  # Allow next year for new models
            raise ValueError(f"Vehicle year must be between 1900 and {current_year + 1}")
        
        if not self.color or len(self.color.strip()) < 3:
            raise ValueError("Vehicle color must be at least 3 characters")
    
    @property
    def description(self) -> str:
        """Get human-readable vehicle description"""
        return f"{self.year} {self.make} {self.model} ({self.color})"
    
    @property
    def display_name(self) -> str:
        """Get display name for UI"""
        return f"{self.make} {self.model} - {self.license_plate}"
    
    def get_parking_rate_multiplier(self) -> Decimal:
        """Get parking rate multiplier based on vehicle type"""
        return self.vehicle_type.get_parking_rate_multiplier()
    
    def can_park_in(self, slot_type: SlotType) -> bool:
        """Check if vehicle can park in given slot type"""
        return slot_type.can_accommodate(self.vehicle_type)
    
    def is_electric(self) -> bool:
        """Check if vehicle is electric"""
        return self.vehicle_type.is_electric
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "license_plate": self.license_plate.value,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "color": self.color,
            "vehicle_type": self.vehicle_type.value,
            "description": self.description,
            "is_electric": self.is_electric()
        }
    
    def __str__(self) -> str:
        return f"{self.description} [{self.license_plate}]"


class ElectricVehicle(Vehicle):
    """
    Entity: Electric Vehicle with charging capabilities
    Extends Vehicle with EV-specific behavior
    """
    
    def __init__(
        self,
        license_plate: LicensePlate,
        make: str,
        model: str,
        year: int,
        color: str,
        vehicle_type: VehicleType,  # Should be EV type
        battery_capacity_kwh: float,
        current_charge_kwh: float,
        max_charge_rate_kw: float,
        id: Optional[str] = None
    ):
        # Ensure vehicle type is electric
        if not vehicle_type.is_electric:
            raise ValueError(f"ElectricVehicle must have electric vehicle type, got {vehicle_type}")
        
        super().__init__(license_plate, make, model, year, color, vehicle_type, id)
        
        self.battery_capacity_kwh = battery_capacity_kwh
        self.current_charge_kwh = current_charge_kwh
        self.max_charge_rate_kw = max_charge_rate_kw
        self._validate_ev()
    
    def _validate_ev(self) -> None:
        """Validate EV-specific attributes"""
        if self.battery_capacity_kwh <= 0:
            raise ValueError("Battery capacity must be positive")
        
        if self.current_charge_kwh < 0:
            raise ValueError("Current charge cannot be negative")
        
        if self.current_charge_kwh > self.battery_capacity_kwh:
            raise ValueError("Current charge cannot exceed battery capacity")
        
        if self.max_charge_rate_kw <= 0:
            raise ValueError("Max charge rate must be positive")
    
    @property
    def charge_percentage(self) -> float:
        """Get current charge as percentage (0-100)"""
        if self.battery_capacity_kwh == 0:
            return 0.0
        return (self.current_charge_kwh / self.battery_capacity_kwh) * 100.0
    
    @property
    def range_estimate_km(self) -> float:
        """Estimate range in kilometers based on charge"""
        # Typical EV efficiency: 6 km per kWh
        efficiency = 6.0  # km per kWh
        return self.current_charge_kwh * efficiency
    
    def charge(self, energy_kwh: float, charger_power_kw: float) -> Tuple[float, float]:
        """
        Add charge to vehicle
        Returns: (energy_added_kwh, time_taken_hours)
        """
        if energy_kwh <= 0:
            raise ValueError("Energy to add must be positive")
        
        if charger_power_kw <= 0:
            raise ValueError("Charger power must be positive")
        
        # Limit by charger power and vehicle max charge rate
        effective_power_kw = min(charger_power_kw, self.max_charge_rate_kw)
        
        # Calculate available capacity
        available_capacity = self.battery_capacity_kwh - self.current_charge_kwh
        
        # Don't exceed available capacity
        energy_to_add = min(energy_kwh, available_capacity)
        
        # Calculate time required
        if effective_power_kw == 0:
            time_hours = 0.0
        else:
            time_hours = energy_to_add / effective_power_kw
        
        # Update charge
        self.current_charge_kwh += energy_to_add
        
        return energy_to_add, time_hours
    
    def discharge(self, energy_kwh: float) -> float:
        """
        Remove charge from vehicle (simulating usage)
        Returns: actual energy removed
        """
        if energy_kwh <= 0:
            raise ValueError("Energy to remove must be positive")
        
        # Don't go below 0
        energy_to_remove = min(energy_kwh, self.current_charge_kwh)
        self.current_charge_kwh -= energy_to_remove
        
        return energy_to_remove
    
    def get_charge_time_hours(self, target_percentage: float, charger_power_kw: float) -> float:
        """
        Calculate time to reach target charge percentage
        """
        if target_percentage < 0 or target_percentage > 100:
            raise ValueError("Target percentage must be between 0 and 100")
        
        if charger_power_kw <= 0:
            raise ValueError("Charger power must be positive")
        
        target_charge_kwh = (target_percentage / 100.0) * self.battery_capacity_kwh
        charge_needed_kwh = target_charge_kwh - self.current_charge_kwh
        
        if charge_needed_kwh <= 0:
            return 0.0
        
        effective_power_kw = min(charger_power_kw, self.max_charge_rate_kw)
        if effective_power_kw == 0:
            return float('inf')
        
        return charge_needed_kwh / effective_power_kw
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with EV-specific fields"""
        base_dict = super().to_dict()
        ev_dict = {
            "battery_capacity_kwh": self.battery_capacity_kwh,
            "current_charge_kwh": self.current_charge_kwh,
            "charge_percentage": self.charge_percentage,
            "max_charge_rate_kw": self.max_charge_rate_kw,
            "range_estimate_km": self.range_estimate_km
        }
        base_dict.update(ev_dict)
        return base_dict
    
    def __str__(self) -> str:
        base_str = super().__str__()
        return f"{base_str} 🔋 {self.charge_percentage:.1f}%"


class ParkingSlot(Entity):
    """
    Entity: Individual parking space with specific type and state
    Has identity (slot number) and lifecycle (occupied/vacant)
    """
    
    def __init__(
        self,
        number: int,
        slot_type: SlotType,
        floor_level: int = 1,
        section: Optional[str] = None,
        features: Optional[List[str]] = None,
        id: Optional[str] = None
    ):
        super().__init__(id)
        self.number = number
        self.slot_type = slot_type
        self.floor_level = floor_level
        self.section = section
        self.features = features or []
        self.is_occupied = False
        self.current_vehicle_id: Optional[str] = None
        self.occupancy_start_time: Optional[datetime] = None
        
        self._validate()
    
    def _validate(self) -> None:
        """Validate slot attributes"""
        if self.number <= 0:
            raise ValueError("Slot number must be positive")
        
        if self.floor_level < 1:
            raise ValueError("Floor level must be at least 1")
        
        # Validate features based on slot type
        if self.slot_type == SlotType.EV and "charging" not in self.features:
            self.features.append("charging")
        
        if self.slot_type == SlotType.DISABLED and "accessible" not in self.features:
            self.features.append("accessible")
    
    @property
    def display_name(self) -> str:
        """Get display name for UI"""
        section_str = f" ({self.section})" if self.section else ""
        return f"Slot {self.number}{section_str} - {self.slot_type}"
    
    @property
    def location_code(self) -> str:
        """Get location code for identification"""
        section_code = self.section[:2].upper() if self.section else "XX"
        return f"L{self.floor_level:02d}{section_code}{self.number:03d}"
    
    @property
    def hourly_rate(self) -> Money:
        """Get hourly rate for this slot"""
        return self.slot_type.hourly_rate
    
    def occupy(self, vehicle_id: str) -> None:
        """
        Occupy the slot with a vehicle
        Raises: ValueError if slot is already occupied
        """
        if self.is_occupied:
            raise ValueError(f"Slot {self.number} is already occupied")
        
        self.is_occupied = True
        self.current_vehicle_id = vehicle_id
        self.occupancy_start_time = datetime.now()
    
    def vacate(self) -> Optional[TimeRange]:
        """
        Vacate the slot
        Returns: TimeRange of occupancy if was occupied, None otherwise
        """
        if not self.is_occupied:
            return None
        
        end_time = datetime.now()
        time_range = None
        
        if self.occupancy_start_time:
            time_range = TimeRange(self.occupancy_start_time, end_time)
        
        self.is_occupied = False
        self.current_vehicle_id = None
        self.occupancy_start_time = None
        
        return time_range
    
    def get_occupancy_duration(self) -> Optional[timedelta]:
        """Get current occupancy duration if occupied"""
        if not self.is_occupied or not self.occupancy_start_time:
            return None
        
        return datetime.now() - self.occupancy_start_time
    
    def calculate_fee(self, duration: Optional[timedelta] = None) -> Money:
        """
        Calculate parking fee for given duration
        If duration not provided, uses current occupancy duration
        """
        if duration is None:
            duration = self.get_occupancy_duration()
            if duration is None:
                return Money(Decimal('0.00'))
        
        hours = duration.total_seconds() / 3600
        # Minimum 1 hour charge
        billable_hours = max(1.0, hours)
        
        # Calculate base fee
        base_fee = self.hourly_rate * Decimal(str(billable_hours))
        
        # Round to nearest 0.25 for business rules
        fee_amount = (base_fee.amount * Decimal('4')).quantize(Decimal('1')) / Decimal('4')
        
        return Money(fee_amount, self.hourly_rate.currency)
    
    def can_accommodate_vehicle(self, vehicle: Vehicle) -> bool:
        """Check if this slot can accommodate the given vehicle"""
        return self.slot_type.can_accommodate(vehicle.vehicle_type)
    
    def has_feature(self, feature: str) -> bool:
        """Check if slot has specific feature"""
        return feature.lower() in [f.lower() for f in self.features]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        duration = self.get_occupancy_duration()
        duration_hours = duration.total_seconds() / 3600 if duration else 0.0
        
        return {
            "id": self.id,
            "number": self.number,
            "slot_type": self.slot_type.value,
            "floor_level": self.floor_level,
            "section": self.section,
            "features": self.features,
            "location_code": self.location_code,
            "is_occupied": self.is_occupied,
            "current_vehicle_id": self.current_vehicle_id,
            "occupancy_start_time": self.occupancy_start_time.isoformat() 
                if self.occupancy_start_time else None,
            "occupancy_duration_hours": duration_hours,
            "hourly_rate": self.hourly_rate.to_dict()
        }
    
    def __str__(self) -> str:
        status = "🟢 Occupied" if self.is_occupied else "🔴 Available"
        return f"{self.display_name} - {status}"


# ============================================================================
# DOMAIN SERVICES (Stateless services that operate on multiple entities)
# ============================================================================

class ParkingFeeCalculator:
    """
    Domain Service: Calculates parking fees based on business rules
    Stateless service that operates on slots and time ranges
    """
    
    @staticmethod
    def calculate_fee(
        slot: ParkingSlot,
        time_range: TimeRange,
        vehicle: Optional[Vehicle] = None
    ) -> Money:
        """
        Calculate parking fee for given slot and time range
        Includes business rules for discounts, premiums, etc.
        """
        # Base calculation from slot
        base_fee = slot.calculate_fee(time_range.duration)
        
        # Apply vehicle-specific multiplier
        if vehicle:
            multiplier = vehicle.get_parking_rate_multiplier()
            adjusted_amount = base_fee.amount * multiplier
            base_fee = Money(adjusted_amount, base_fee.currency)
        
        # Apply time-based rules
        base_fee = ParkingFeeCalculator._apply_time_based_rules(base_fee, time_range)
        
        # Apply slot feature premiums
        base_fee = ParkingFeeCalculator._apply_feature_premiums(base_fee, slot)
        
        return base_fee
    
    @staticmethod
    def _apply_time_based_rules(fee: Money, time_range: TimeRange) -> Money:
        """Apply time-based business rules to fee"""
        # Example rule: First hour discount
        if time_range.duration_hours <= 1:
            # 10% discount for first hour
            discount = fee.amount * Decimal('0.10')
            fee = Money(fee.amount - discount, fee.currency)
        
        # Example rule: Evening premium (6 PM to 6 AM)
        start_hour = time_range.start_time.hour
        if 18 <= start_hour or start_hour < 6:
            # 20% premium for evening/overnight
            premium = fee.amount * Decimal('0.20')
            fee = Money(fee.amount + premium, fee.currency)
        
        return fee
    
    @staticmethod
    def _apply_feature_premiums(fee: Money, slot: ParkingSlot) -> Money:
        """Apply premiums for slot features"""
        premium_multiplier = Decimal('1.0')
        
        if slot.has_feature("covered"):
            premium_multiplier += Decimal('0.15')  # 15% premium for covered
        
        if slot.has_feature("camera"):
            premium_multiplier += Decimal('0.05')   # 5% premium for security camera
        
        if slot.has_feature("valet"):
            premium_multiplier += Decimal('0.25')   # 25% premium for valet service
        
        adjusted_amount = fee.amount * premium_multiplier
        return Money(adjusted_amount, fee.currency)
    
    @staticmethod
    def calculate_ev_charging_fee(
        energy_kwh: float,
        charger_type: ChargerType,
        time_of_day: datetime
    ) -> Money:
        """
        Calculate EV charging fee based on energy, charger type, and time
        """
        # Base rate per kWh
        base_rate_per_kwh = Decimal('0.30')  # $0.30 per kWh
        
        # Charger type multiplier
        charger_multipliers = {
            ChargerType.LEVEL_1: Decimal('1.0'),
            ChargerType.LEVEL_2: Decimal('1.2'),
            ChargerType.DC_FAST: Decimal('1.5'),
            ChargerType.TESLA: Decimal('1.8'),
            ChargerType.CHADEMO: Decimal('1.5'),
            ChargerType.CCS: Decimal('1.5'),
        }
        
        multiplier = charger_multipliers.get(charger_type, Decimal('1.0'))
        
        # Time of day adjustment (peak vs off-peak)
        hour = time_of_day.hour
        if 8 <= hour < 20:  # Peak hours: 8 AM to 8 PM
            multiplier *= Decimal('1.25')  # 25% peak surcharge
        else:  # Off-peak hours
            multiplier *= Decimal('0.75')  # 25% off-peak discount
        
        # Calculate fee
        fee_amount = Decimal(str(energy_kwh)) * base_rate_per_kwh * multiplier
        return Money(fee_amount)


class VehicleFactory:
    """
    Factory for creating Vehicle and ElectricVehicle instances
    Encapsulates complex creation logic
    """
    
    @staticmethod
    def create_vehicle(
        license_plate: str,
        make: str,
        model: str,
        year: int,
        color: str,
        vehicle_type_str: str
    ) -> Vehicle:
        """
        Create a Vehicle instance from string parameters
        """
        # Create value objects
        plate = LicensePlate(license_plate)
        
        # Convert string to enum
        try:
            vehicle_type = VehicleType(vehicle_type_str)
        except ValueError:
            raise ValueError(f"Invalid vehicle type: {vehicle_type_str}")
        
        # Create appropriate vehicle type
        if vehicle_type.is_electric:
            # Default EV parameters (would come from user input in real system)
            battery_capacity = 60.0  # kWh
            current_charge = 30.0    # kWh (50%)
            max_charge_rate = 7.2    # kW (Level 2)
            
            return ElectricVehicle(
                license_plate=plate,
                make=make,
                model=model,
                year=year,
                color=color,
                vehicle_type=vehicle_type,
                battery_capacity_kwh=battery_capacity,
                current_charge_kwh=current_charge,
                max_charge_rate_kw=max_charge_rate
            )
        else:
            return Vehicle(
                license_plate=plate,
                make=make,
                model=model,
                year=year,
                color=color,
                vehicle_type=vehicle_type
            )
    
    @staticmethod
    def create_vehicle_from_dict(data: Dict[str, Any]) -> Vehicle:
        """
        Create Vehicle instance from dictionary
        Useful for deserialization
        """
        required_fields = ['license_plate', 'make', 'model', 'year', 'color', 'vehicle_type']
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Handle optional EV fields
        if data['vehicle_type'].startswith('ev_'):
            ev_fields = ['battery_capacity_kwh', 'current_charge_kwh', 'max_charge_rate_kw']
            for field in ev_fields:
                if field not in data:
                    raise ValueError(f"EV vehicle missing field: {field}")
            
            return ElectricVehicle(
                license_plate=LicensePlate(data['license_plate']),
                make=data['make'],
                model=data['model'],
                year=data['year'],
                color=data['color'],
                vehicle_type=VehicleType(data['vehicle_type']),
                battery_capacity_kwh=data['battery_capacity_kwh'],
                current_charge_kwh=data['current_charge_kwh'],
                max_charge_rate_kw=data['max_charge_rate_kw']
            )
        else:
            return Vehicle(
                license_plate=LicensePlate(data['license_plate']),
                make=data['make'],
                model=data['model'],
                year=data['year'],
                color=data['color'],
                vehicle_type=VehicleType(data['vehicle_type'])
            )


# ============================================================================
# DOMAIN EVENTS (for event-driven architecture)
# ============================================================================

class DomainEvent(ABC):
    """
    Base class for all domain events
    Events represent something that happened in the domain
    """
    
    def __init__(self):
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.version = "1.0"
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__} at {self.timestamp}"


class VehicleParkedEvent(DomainEvent):
    """Event raised when a vehicle is parked"""
    
    def __init__(
        self,
        parking_lot_id: str,
        slot_id: str,
        vehicle_id: str,
        license_plate: str,
        vehicle_type: VehicleType,
        timestamp: Optional[datetime] = None
    ):
        super().__init__()
        self.parking_lot_id = parking_lot_id
        self.slot_id = slot_id
        self.vehicle_id = vehicle_id
        self.license_plate = license_plate
        self.vehicle_type = vehicle_type
        if timestamp:
            self.timestamp = timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": "vehicle.parked",
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "data": {
                "parking_lot_id": self.parking_lot_id,
                "slot_id": self.slot_id,
                "vehicle_id": self.vehicle_id,
                "license_plate": self.license_plate,
                "vehicle_type": self.vehicle_type.value,
                "is_electric": self.vehicle_type.is_electric
            }
        }


class VehicleLeftEvent(DomainEvent):
    """Event raised when a vehicle leaves"""
    
    def __init__(
        self,
        parking_lot_id: str,
        slot_id: str,
        vehicle_id: str,
        license_plate: str,
        entry_time: datetime,
        exit_time: datetime,
        duration_minutes: float,
        fee_amount: Optional[Decimal] = None
    ):
        super().__init__()
        self.parking_lot_id = parking_lot_id
        self.slot_id = slot_id
        self.vehicle_id = vehicle_id
        self.license_plate = license_plate
        self.entry_time = entry_time
        self.exit_time = exit_time
        self.duration_minutes = duration_minutes
        self.fee_amount = fee_amount
    
    def to_dict(self) -> Dict[str, Any]:
        data = {
            "parking_lot_id": self.parking_lot_id,
            "slot_id": self.slot_id,
            "vehicle_id": self.vehicle_id,
            "license_plate": self.license_plate,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat(),
            "duration_minutes": self.duration_minutes
        }
        
        if self.fee_amount is not None:
            data["fee_amount"] = float(self.fee_amount)
            data["fee_currency"] = "USD"
        
        return {
            "event_type": "vehicle.left",
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "data": data
        }


class EVChargingStartedEvent(DomainEvent):
    """Event raised when EV charging starts"""
    
    def __init__(
        self,
        vehicle_id: str,
        license_plate: str,
        slot_id: str,
        charger_type: ChargerType,
        initial_charge_percentage: float,
        target_charge_percentage: float
    ):
        super().__init__()
        self.vehicle_id = vehicle_id
        self.license_plate = license_plate
        self.slot_id = slot_id
        self.charger_type = charger_type
        self.initial_charge_percentage = initial_charge_percentage
        self.target_charge_percentage = target_charge_percentage
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": "ev.charging.started",
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "data": {
                "vehicle_id": self.vehicle_id,
                "license_plate": self.license_plate,
                "slot_id": self.slot_id,
                "charger_type": self.charger_type.value,
                "charger_power_kw": self.charger_type.typical_power_kw,
                "initial_charge_percentage": self.initial_charge_percentage,
                "target_charge_percentage": self.target_charge_percentage
            }
        }


class EVChargingCompletedEvent(DomainEvent):
    """Event raised when EV charging completes"""
    
    def __init__(
        self,
        vehicle_id: str,
        license_plate: str,
        slot_id: str,
        charger_type: ChargerType,
        energy_delivered_kwh: float,
        charging_time_minutes: float,
        fee_amount: Decimal
    ):
        super().__init__()
        self.vehicle_id = vehicle_id
        self.license_plate = license_plate
        self.slot_id = slot_id
        self.charger_type = charger_type
        self.energy_delivered_kwh = energy_delivered_kwh
        self.charging_time_minutes = charging_time_minutes
        self.fee_amount = fee_amount
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": "ev.charging.completed",
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "data": {
                "vehicle_id": self.vehicle_id,
                "license_plate": self.license_plate,
                "slot_id": self.slot_id,
                "charger_type": self.charger_type.value,
                "energy_delivered_kwh": self.energy_delivered_kwh,
                "charging_time_minutes": self.charging_time_minutes,
                "fee_amount": float(self.fee_amount),
                "fee_currency": "USD"
            }
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def validate_parking_duration(duration_hours: float, max_hours: float = 24.0) -> bool:
    """
    Validate parking duration against business rules
    Returns: True if valid, False otherwise
    """
    if duration_hours <= 0:
        return False
    
    if duration_hours > max_hours:
        return False
    
    # Additional business rules could be added here
    return True


def generate_slot_numbers(
    start: int,
    count: int,
    slot_type: SlotType,
    floor_level: int = 1
) -> List[ParkingSlot]:
    """
    Generate a list of parking slots with sequential numbers
    Useful for initializing parking lots
    """
    slots = []
    for i in range(count):
        slot_number = start + i
        
        # Add features based on slot type
        features = []
        if slot_type == SlotType.EV:
            features = ["charging", "ev_only"]
        elif slot_type == SlotType.DISABLED:
            features = ["accessible", "wide"]
        elif slot_type == SlotType.PREMIUM:
            features = ["covered", "camera", "wide"]
        
        slot = ParkingSlot(
            number=slot_number,
            slot_type=slot_type,
            floor_level=floor_level,
            features=features
        )
        slots.append(slot)
    
    return slots


def calculate_optimal_slot_distribution(
    total_capacity: int,
    ev_percentage: float = 0.2,
    disabled_percentage: float = 0.05,
    premium_percentage: float = 0.1
) -> Capacity:
    """
    Calculate optimal slot distribution based on percentages
    Returns: Capacity object with calculated values
    """
    ev_slots = int(total_capacity * ev_percentage)
    disabled_slots = int(total_capacity * disabled_percentage)
    premium_slots = int(total_capacity * premium_percentage)
    regular_slots = total_capacity - ev_slots - disabled_slots - premium_slots
    
    return Capacity(
        regular=regular_slots,
        ev=ev_slots,
        disabled=disabled_slots,
        premium=premium_slots
    )


# ============================================================================
# TESTS AND VALIDATION (for demonstration)
# ============================================================================

def test_domain_models():
    """Test function to demonstrate domain model functionality"""
    print("🧪 Testing Domain Models...")
    print("=" * 60)
    
    # Test Value Objects
    try:
        plate = LicensePlate("ABC-123")
        print(f"✅ LicensePlate: {plate}")
        
        location = Location(
            address="123 Main St",
            city="Tech City",
            state="CA",
            zip_code="12345",
            latitude=37.7749,
            longitude=-122.4194
        )
        print(f"✅ Location: {location}")
        
        capacity = Capacity(regular=50, ev=10, disabled=5, premium=5)
        print(f"✅ {capacity}")
        
        money = Money(Decimal("25.50"))
        print(f"✅ Money: {money.format()}")
        
        time_range = TimeRange(
            start_time=datetime(2024, 1, 15, 10, 0),
            end_time=datetime(2024, 1, 15, 12, 30)
        )
        print(f"✅ TimeRange: {time_range}")
        
    except ValueError as e:
        print(f"❌ Value Object Error: {e}")
    
    # Test Entities
    try:
        vehicle = Vehicle(
            license_plate=LicensePlate("TESLA-1"),
            make="Tesla",
            model="Model 3",
            year=2023,
            color="Red",
            vehicle_type=VehicleType.EV_CAR
        )
        print(f"✅ Vehicle: {vehicle}")
        print(f"   Can park in EV slot: {vehicle.can_park_in(SlotType.EV)}")
        print(f"   Rate multiplier: {vehicle.get_parking_rate_multiplier()}")
        
        ev = ElectricVehicle(
            license_plate=LicensePlate("EV-001"),
            make="Tesla",
            model="Model S",
            year=2023,
            color="Blue",
            vehicle_type=VehicleType.EV_CAR,
            battery_capacity_kwh=100,
            current_charge_kwh=50,
            max_charge_rate_kw=11
        )
        print(f"✅ ElectricVehicle: {ev}")
        print(f"   Charge: {ev.charge_percentage:.1f}%")
        print(f"   Range: {ev.range_estimate_km:.1f} km")
        
        slot = ParkingSlot(
            number=101,
            slot_type=SlotType.EV,
            floor_level=1,
            features=["charging", "covered"]
        )
        print(f"✅ ParkingSlot: {slot}")
        print(f"   Hourly rate: {slot.hourly_rate.format()}")
        print(f"   Can accommodate EV: {slot.can_accommodate_vehicle(ev)}")
        
    except ValueError as e:
        print(f"❌ Entity Error: {e}")
    
    # Test Domain Services
    try:
        fee = ParkingFeeCalculator.calculate_fee(slot, time_range, vehicle)
        print(f"✅ Parking Fee: {fee.format()}")
        
        charging_fee = ParkingFeeCalculator.calculate_ev_charging_fee(
            energy_kwh=30,
            charger_type=ChargerType.DC_FAST,
            time_of_day=datetime(2024, 1, 15, 14, 0)
        )
        print(f"✅ Charging Fee: {charging_fee.format()}")
        
    except Exception as e:
        print(f"❌ Service Error: {e}")
    
    print("=" * 60)
    print("✅ Domain Models Test Complete")


if __name__ == "__main__":
    # Run tests if module is executed directly
    test_domain_models()