# File: src/application/dtos.py
"""
Data Transfer Objects (DTOs) for Parking Management System

This module defines DTOs for data transfer between layers:
1. Input DTOs - For receiving data from clients/API
2. Output DTOs - For sending data to clients/API
3. Internal DTOs - For communication between application services
4. Query DTOs - For complex query parameters

DTO Principles:
- Immutable where possible (frozen dataclasses)
- Validation at creation
- Clear separation between internal and external representations
- No business logic, only data
- Serialization/deserialization support
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union, Type, TypeVar
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
import json
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, validator, root_validator
from pydantic.dataclasses import dataclass as pydantic_dataclass
from pydantic import ConfigDict

# Type variable for DTO generics
T = TypeVar('T')


# ============================================================================
# BASE DTO CLASSES
# ============================================================================

class BaseDTO(BaseModel):
    """Base DTO with common functionality"""
    
    model_config = ConfigDict(
        from_attributes=True,  # Allow creation from ORM models
        populate_by_name=True,
        arbitrary_types_allowed=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: str(v),
            UUID: lambda v: str(v)
        }
    )
    
    def to_dict(self, exclude_none: bool = False, **kwargs) -> Dict[str, Any]:
        """Convert DTO to dictionary"""
        data = self.model_dump(**kwargs)
        if exclude_none:
            data = {k: v for k, v in data.items() if v is not None}
        return data
    
    def to_json(self, **kwargs) -> str:
        """Convert DTO to JSON string"""
        return self.model_dump_json(**kwargs)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseDTO':
        """Create DTO from dictionary"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseDTO':
        """Create DTO from JSON string"""
        data = json.loads(json_str)
        return cls(**data)


class PaginatedRequest(BaseDTO):
    """Base DTO for paginated requests"""
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$", description="Sort order (asc/desc)")


class PaginatedResponse(BaseDTO):
    """Base DTO for paginated responses"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# ============================================================================
# ENUM DTOs
# ============================================================================

class VehicleTypeDTO(str, Enum):
    """Vehicle type DTO"""
    CAR = "car"
    EV_CAR = "ev_car"
    MOTORCYCLE = "motorcycle"
    EV_MOTORCYCLE = "ev_motorcycle"
    TRUCK = "truck"
    EV_TRUCK = "ev_truck"
    BUS = "bus"


class SlotTypeDTO(str, Enum):
    """Parking slot type DTO"""
    REGULAR = "regular"
    PREMIUM = "premium"
    EV = "ev"
    DISABLED = "disabled"
    VALET = "valet"
    RESERVED = "reserved"


class ChargerTypeDTO(str, Enum):
    """Charger type DTO"""
    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    DC_FAST = "dc_fast"
    TESLA = "tesla"
    CHADEMO = "chademo"
    CCS = "ccs"


class ParkingStrategyTypeDTO(str, Enum):
    """Parking strategy type DTO"""
    STANDARD_CAR = "standard_car"
    ELECTRIC_CAR = "electric_car"
    MOTORCYCLE = "motorcycle"
    LARGE_VEHICLE = "large_vehicle"
    NEAREST_ENTRY = "nearest_entry"


class PricingStrategyTypeDTO(str, Enum):
    """Pricing strategy type DTO"""
    STANDARD = "standard"
    DYNAMIC = "dynamic"
    SUBSCRIPTION = "subscription"
    PEAK = "peak"
    OFF_PEAK = "off_peak"


class ChargingStrategyTypeDTO(str, Enum):
    """Charging strategy type DTO"""
    FAST = "fast"
    COST_OPTIMIZED = "cost_optimized"
    BALANCED = "balanced"


class PaymentMethodDTO(str, Enum):
    """Payment method DTO"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CASH = "cash"
    MOBILE_WALLET = "mobile_wallet"
    SUBSCRIPTION = "subscription"
    VOUCHER = "voucher"


class PaymentStatusDTO(str, Enum):
    """Payment status DTO"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class InvoiceStatusDTO(str, Enum):
    """Invoice status DTO"""
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class ReservationStatusDTO(str, Enum):
    """Reservation status DTO"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AlertSeverityDTO(str, Enum):
    """Alert severity DTO"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


# ============================================================================
# COMMON VALUE OBJECT DTOs
# ============================================================================

class MoneyDTO(BaseDTO):
    """Money value object DTO"""
    amount: Decimal = Field(ge=0, description="Amount")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Currency code (ISO 4217)")
    
    @validator('amount')
    def validate_amount(cls, v):
        """Validate amount precision"""
        # Ensure amount has at most 2 decimal places
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount cannot have more than 2 decimal places")
        return v


class TimeRangeDTO(BaseDTO):
    """Time range DTO"""
    start_time: datetime = Field(description="Start time")
    end_time: datetime = Field(description="End time")
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validate that end time is after start time"""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError("End time must be after start time")
        return v
    
    @property
    def duration_hours(self) -> float:
        """Calculate duration in hours"""
        duration = self.end_time - self.start_time
        return duration.total_seconds() / 3600


class LicensePlateDTO(BaseDTO):
    """License plate DTO"""
    number: str = Field(min_length=1, max_length=20, description="License plate number")
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2, description="Country code (ISO 3166-1 alpha-2)")
    state: Optional[str] = Field(default=None, min_length=2, max_length=3, description="State/province code")
    
    @validator('number')
    def validate_license_plate(cls, v):
        """Basic license plate validation"""
        # Remove whitespace and convert to uppercase
        v = v.strip().upper()
        
        # Basic alphanumeric check (can be customized per country)
        if not v.replace('-', '').replace(' ', '').isalnum():
            raise ValueError("License plate must be alphanumeric")
        
        return v
    
    def display(self) -> str:
        """Get display representation"""
        parts = []
        if self.country_code:
            parts.append(self.country_code)
        if self.state:
            parts.append(self.state)
        parts.append(self.number)
        return " ".join(parts)


class LocationDTO(BaseDTO):
    """Location DTO"""
    latitude: float = Field(ge=-90, le=90, description="Latitude")
    longitude: float = Field(ge=-180, le=180, description="Longitude")
    address: Optional[str] = Field(default=None, description="Street address")
    city: Optional[str] = Field(default=None, description="City")
    state: Optional[str] = Field(default=None, description="State/province")
    country: Optional[str] = Field(default=None, description="Country")
    postal_code: Optional[str] = Field(default=None, description="Postal code")


class ContactInfoDTO(BaseDTO):
    """Contact information DTO"""
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    mobile: Optional[str] = Field(default=None, description="Mobile number")
    
    @validator('email')
    def validate_email(cls, v):
        """Basic email validation"""
        if v and '@' not in v:
            raise ValueError("Invalid email address")
        return v


# ============================================================================
# VEHICLE DTOs
# ============================================================================

class VehicleBaseDTO(BaseDTO):
    """Base vehicle DTO"""
    license_plate: str = Field(description="License plate number")
    vehicle_type: VehicleTypeDTO = Field(description="Vehicle type")
    make: Optional[str] = Field(default=None, description="Vehicle make/brand")
    model: Optional[str] = Field(default=None, description="Vehicle model")
    year: Optional[int] = Field(default=None, ge=1900, le=2100, description="Manufacturing year")
    color: Optional[str] = Field(default=None, description="Vehicle color")
    disabled_permit: bool = Field(default=False, description="Has disability permit")


class VehicleCreateDTO(VehicleBaseDTO):
    """DTO for creating a vehicle"""
    pass


class VehicleUpdateDTO(BaseDTO):
    """DTO for updating a vehicle"""
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    color: Optional[str] = None
    disabled_permit: Optional[bool] = None


class ElectricVehicleDTO(VehicleBaseDTO):
    """Electric vehicle DTO"""
    battery_capacity_kwh: float = Field(gt=0, description="Battery capacity in kWh")
    max_charging_rate_kw: Optional[float] = Field(default=None, gt=0, description="Maximum charging rate in kW")
    compatible_chargers: List[ChargerTypeDTO] = Field(default_factory=list, description="Compatible charger types")
    
    @validator('vehicle_type')
    def validate_electric_type(cls, v):
        """Validate that vehicle type is electric"""
        if not v.value.startswith('ev_'):
            raise ValueError(f"Vehicle type {v} is not electric")
        return v


class VehicleDTO(VehicleBaseDTO):
    """Complete vehicle DTO"""
    id: UUID = Field(description="Vehicle ID")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    is_active: bool = Field(default=True, description="Is vehicle active")
    
    # Electric vehicle specific fields (optional)
    battery_capacity_kwh: Optional[float] = None
    max_charging_rate_kw: Optional[float] = None
    compatible_chargers: List[ChargerTypeDTO] = Field(default_factory=list)


# ============================================================================
# PARKING SLOT DTOs
# ============================================================================

class ParkingSlotBaseDTO(BaseDTO):
    """Base parking slot DTO"""
    number: int = Field(ge=1, description="Slot number")
    floor_level: int = Field(default=0, description="Floor level (0 for ground)")
    slot_type: SlotTypeDTO = Field(description="Slot type")
    vehicle_types: List[VehicleTypeDTO] = Field(default_factory=list, description="Compatible vehicle types")
    features: List[str] = Field(default_factory=list, description="Slot features (covered, camera, etc.)")
    is_reserved: bool = Field(default=False, description="Is slot reserved")
    
    @validator('features')
    def validate_features(cls, v):
        """Validate slot features"""
        valid_features = {"covered", "camera", "valet", "wide", "compact", "indoor", "outdoor"}
        invalid = [f for f in v if f not in valid_features]
        if invalid:
            raise ValueError(f"Invalid features: {invalid}. Valid features: {valid_features}")
        return v


class ParkingSlotCreateDTO(ParkingSlotBaseDTO):
    """DTO for creating a parking slot"""
    parking_lot_id: UUID = Field(description="Parking lot ID")


class ParkingSlotUpdateDTO(BaseDTO):
    """DTO for updating a parking slot"""
    slot_type: Optional[SlotTypeDTO] = None
    vehicle_types: Optional[List[VehicleTypeDTO]] = None
    features: Optional[List[str]] = None
    is_reserved: Optional[bool] = None
    is_active: Optional[bool] = None


class ParkingSlotDTO(ParkingSlotBaseDTO):
    """Complete parking slot DTO"""
    id: UUID = Field(description="Slot ID")
    parking_lot_id: UUID = Field(description="Parking lot ID")
    is_occupied: bool = Field(description="Is slot currently occupied")
    occupied_by: Optional[str] = Field(default=None, description="License plate of occupying vehicle")
    occupied_since: Optional[datetime] = Field(default=None, description="When slot was occupied")
    hourly_rate: MoneyDTO = Field(description="Hourly parking rate")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    is_active: bool = Field(default=True, description="Is slot active")


# ============================================================================
# PARKING LOT DTOs
# ============================================================================

class ParkingLotBaseDTO(BaseDTO):
    """Base parking lot DTO"""
    name: str = Field(min_length=1, max_length=100, description="Parking lot name")
    code: str = Field(min_length=1, max_length=20, description="Unique parking lot code")
    location: LocationDTO = Field(description="Parking lot location")
    total_capacity: int = Field(ge=1, description="Total parking capacity")
    description: Optional[str] = Field(default=None, description="Description")
    operating_hours: Optional[Dict[str, Any]] = Field(default=None, description="Operating hours")
    contact_info: Optional[ContactInfoDTO] = Field(default=None, description="Contact information")
    
    @validator('code')
    def validate_code(cls, v):
        """Validate parking lot code format"""
        v = v.strip().upper()
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Parking lot code must be alphanumeric with hyphens/underscores")
        return v


class ParkingLotCreateDTO(ParkingLotBaseDTO):
    """DTO for creating a parking lot"""
    slot_distribution: Dict[SlotTypeDTO, int] = Field(
        description="Number of slots by type"
    )
    
    @validator('slot_distribution')
    def validate_slot_distribution(cls, v, values):
        """Validate slot distribution matches total capacity"""
        if 'total_capacity' in values:
            total_slots = sum(v.values())
            if total_slots != values['total_capacity']:
                raise ValueError(f"Slot distribution total ({total_slots}) does not match total capacity ({values['total_capacity']})")
        return v


class ParkingLotUpdateDTO(BaseDTO):
    """DTO for updating a parking lot"""
    name: Optional[str] = None
    description: Optional[str] = None
    operating_hours: Optional[Dict[str, Any]] = None
    contact_info: Optional[ContactInfoDTO] = None
    is_active: Optional[bool] = None


class ParkingLotPoliciesDTO(BaseDTO):
    """Parking lot policies DTO"""
    ev_can_use_regular: bool = Field(default=True, description="EVs can use regular slots")
    motorcycles_per_slot: int = Field(default=2, ge=1, le=5, description="Max motorcycles per regular slot")
    max_parking_hours: Optional[int] = Field(default=None, ge=1, description="Maximum parking hours")
    grace_period_minutes: int = Field(default=15, ge=0, le=60, description="Grace period in minutes")
    overstay_penalty_rate: float = Field(default=1.5, ge=1.0, description="Overstay penalty rate multiplier")
    reservation_hold_minutes: int = Field(default=30, ge=0, le=120, description="Reservation hold time in minutes")


class ParkingLotDTO(ParkingLotBaseDTO):
    """Complete parking lot DTO"""
    id: UUID = Field(description="Parking lot ID")
    total_slots: int = Field(description="Total number of slots")
    occupied_slots: int = Field(description="Number of occupied slots")
    available_slots: int = Field(description="Number of available slots")
    occupancy_rate: float = Field(ge=0, le=1, description="Occupancy rate (0-1)")
    policies: ParkingLotPoliciesDTO = Field(description="Parking lot policies")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    is_active: bool = Field(default=True, description="Is parking lot active")


class ParkingLotStatusDTO(BaseDTO):
    """Parking lot status DTO"""
    parking_lot_id: UUID = Field(description="Parking lot ID")
    total_slots: int = Field(description="Total number of slots")
    occupied_slots: int = Field(description="Number of occupied slots")
    available_slots: int = Field(description="Number of available slots")
    occupancy_rate: float = Field(ge=0, le=1, description="Occupancy rate (0-1)")
    by_slot_type: Dict[str, Dict[str, int]] = Field(
        description="Slot occupancy by type"
    )
    by_vehicle_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Vehicle count by type"
    )
    recent_activity: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recent parking activity"
    )
    timestamp: datetime = Field(description="Status timestamp")


# ============================================================================
# CHARGING STATION DTOs
# ============================================================================

class ChargingStationBaseDTO(BaseDTO):
    """Base charging station DTO"""
    name: str = Field(min_length=1, max_length=100, description="Charging station name")
    code: str = Field(min_length=1, max_length=20, description="Unique station code")
    location: LocationDTO = Field(description="Station location")
    total_power_capacity_kw: float = Field(gt=0, description="Total power capacity in kW")
    description: Optional[str] = Field(default=None, description="Description")
    operating_hours: Optional[Dict[str, Any]] = Field(default=None, description="Operating hours")
    contact_info: Optional[ContactInfoDTO] = Field(default=None, description="Contact information")


class ChargingConnectorDTO(BaseDTO):
    """Charging connector DTO"""
    connector_id: str = Field(description="Connector ID")
    connector_type: ChargerTypeDTO = Field(description="Connector type")
    max_power_kw: float = Field(gt=0, description="Maximum power output in kW")
    is_available: bool = Field(description="Is connector available")
    occupied_by: Optional[str] = Field(default=None, description="License plate of occupying vehicle")
    occupied_since: Optional[datetime] = Field(default=None, description="When connector was occupied")
    hourly_rate: MoneyDTO = Field(description="Hourly charging rate")
    energy_rate_per_kwh: MoneyDTO = Field(description="Energy rate per kWh")


class ChargingStationCreateDTO(ChargingStationBaseDTO):
    """DTO for creating a charging station"""
    connectors: List[Dict[str, Any]] = Field(
        description="List of connectors with type and power"
    )
    parking_lot_id: Optional[UUID] = Field(default=None, description="Associated parking lot ID")


class ChargingStationUpdateDTO(BaseDTO):
    """DTO for updating a charging station"""
    name: Optional[str] = None
    description: Optional[str] = None
    operating_hours: Optional[Dict[str, Any]] = None
    contact_info: Optional[ContactInfoDTO] = None
    is_active: Optional[bool] = None


class ChargingStationDTO(ChargingStationBaseDTO):
    """Complete charging station DTO"""
    id: UUID = Field(description="Station ID")
    total_connectors: int = Field(description="Total number of connectors")
    available_connectors: int = Field(description="Number of available connectors")
    utilization_rate: float = Field(ge=0, le=1, description="Utilization rate (0-1)")
    connectors: List[ChargingConnectorDTO] = Field(
        default_factory=list,
        description="List of connectors"
    )
    parking_lot_id: Optional[UUID] = Field(default=None, description="Associated parking lot ID")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    is_active: bool = Field(default=True, description="Is station active")


# ============================================================================
# PARKING OPERATION DTOs
# ============================================================================

class ParkingRequestDTO(BaseDTO):
    """DTO for parking request"""
    license_plate: str = Field(description="License plate number")
    vehicle_type: VehicleTypeDTO = Field(description="Vehicle type")
    parking_lot_id: UUID = Field(description="Parking lot ID")
    entry_time: Optional[datetime] = Field(default=None, description="Entry time (defaults to now)")
    preferences: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Parking preferences"
    )
    customer_id: Optional[UUID] = Field(default=None, description="Customer ID")
    requires_charging: bool = Field(default=False, description="Requires EV charging")
    
    @validator('preferences')
    def validate_preferences(cls, v):
        """Validate parking preferences"""
        valid_keys = {
            "preferred_slot_type", "specific_slot", "force_allocation",
            "needs_charging", "priority_level", "duration_hours"
        }
        invalid = [k for k in v.keys() if k not in valid_keys]
        if invalid:
            raise ValueError(f"Invalid preference keys: {invalid}. Valid keys: {valid_keys}")
        return v


class ExitRequestDTO(BaseDTO):
    """DTO for exit request"""
    ticket_id: Optional[UUID] = Field(default=None, description="Parking ticket ID")
    license_plate: Optional[str] = Field(default=None, description="License plate number")
    parking_lot_id: UUID = Field(description="Parking lot ID")
    exit_time: Optional[datetime] = Field(default=None, description="Exit time (defaults to now)")
    
    @root_validator
    def validate_identifier(cls, values):
        """Validate that either ticket_id or license_plate is provided"""
        ticket_id = values.get('ticket_id')
        license_plate = values.get('license_plate')
        
        if not ticket_id and not license_plate:
            raise ValueError("Either ticket_id or license_plate must be provided")
        
        return values


class ParkingAllocationDTO(BaseDTO):
    """DTO for parking allocation result"""
    success: bool = Field(description="Allocation success")
    ticket_id: Optional[UUID] = Field(default=None, description="Parking ticket ID")
    slot_number: Optional[int] = Field(default=None, description="Allocated slot number")
    slot_type: Optional[SlotTypeDTO] = Field(default=None, description="Slot type")
    floor_level: Optional[int] = Field(default=None, description="Floor level")
    estimated_fee_per_hour: Optional[MoneyDTO] = Field(default=None, description="Estimated hourly fee")
    message: Optional[str] = Field(default=None, description="Result message")
    strategy_used: Optional[str] = Field(default=None, description="Strategy used for allocation")
    timestamp: Optional[datetime] = Field(default=None, description="Allocation timestamp")


class ParkingExitDTO(BaseDTO):
    """DTO for parking exit result"""
    success: bool = Field(description="Exit success")
    license_plate: Optional[str] = Field(default=None, description="License plate")
    slot_number: Optional[int] = Field(default=None, description="Slot number")
    duration_hours: Optional[float] = Field(default=None, ge=0, description="Parking duration in hours")
    total_fee: Optional[MoneyDTO] = Field(default=None, description="Total parking fee")
    invoice_id: Optional[UUID] = Field(default=None, description="Invoice ID")
    payment_required: bool = Field(default=False, description="Payment required")
    message: Optional[str] = Field(default=None, description="Result message")
    timestamp: Optional[datetime] = Field(default=None, description="Exit timestamp")


# ============================================================================
# CHARGING OPERATION DTOs
# ============================================================================

class ChargingRequestDTO(BaseDTO):
    """DTO for charging request"""
    license_plate: str = Field(description="License plate number")
    vehicle_type: VehicleTypeDTO = Field(description="Vehicle type")
    station_id: UUID = Field(description="Charging station ID")
    current_charge_percentage: float = Field(ge=0, le=100, description="Current battery charge percentage")
    target_charge_percentage: float = Field(ge=0, le=100, description="Target battery charge percentage")
    battery_capacity_kwh: float = Field(gt=0, description="Battery capacity in kWh")
    charging_strategy: ChargingStrategyTypeDTO = Field(default=ChargingStrategyTypeDTO.BALANCED, description="Charging strategy")
    customer_id: Optional[UUID] = Field(default=None, description="Customer ID")
    
    @validator('target_charge_percentage')
    def validate_target_charge(cls, v, values):
        """Validate target charge is greater than current charge"""
        if 'current_charge_percentage' in values and v <= values['current_charge_percentage']:
            raise ValueError("Target charge percentage must be greater than current charge")
        return v
    
    @validator('vehicle_type')
    def validate_electric_vehicle(cls, v):
        """Validate that vehicle type is electric"""
        if not v.value.startswith('ev_'):
            raise ValueError(f"Vehicle type {v} is not electric")
        return v


class ChargingSessionDTO(BaseDTO):
    """DTO for charging session result"""
    success: bool = Field(description="Session creation success")
    session_id: Optional[UUID] = Field(default=None, description="Charging session ID")
    connector_id: Optional[str] = Field(default=None, description="Allocated connector ID")
    connector_type: Optional[ChargerTypeDTO] = Field(default=None, description="Connector type")
    estimated_time_hours: Optional[float] = Field(default=None, gt=0, description="Estimated charging time in hours")
    estimated_cost: Optional[MoneyDTO] = Field(default=None, description="Estimated charging cost")
    message: Optional[str] = Field(default=None, description="Result message")
    strategy_used: Optional[ChargingStrategyTypeDTO] = Field(default=None, description="Strategy used")
    timestamp: Optional[datetime] = Field(default=None, description="Session creation timestamp")


class ChargingStopRequestDTO(BaseDTO):
    """DTO for stopping charging session"""
    session_id: UUID = Field(description="Charging session ID")
    station_id: UUID = Field(description="Charging station ID")
    stop_time: Optional[datetime] = Field(default=None, description="Stop time (defaults to now)")


class ChargingStopResultDTO(BaseDTO):
    """DTO for charging stop result"""
    success: bool = Field(description="Stop success")
    session_id: UUID = Field(description="Charging session ID")
    duration_hours: float = Field(ge=0, description="Charging duration in hours")
    energy_delivered_kwh: float = Field(ge=0, description="Energy delivered in kWh")
    total_cost: MoneyDTO = Field(description="Total charging cost")
    invoice_id: Optional[UUID] = Field(default=None, description="Invoice ID")
    message: Optional[str] = Field(default=None, description="Result message")
    timestamp: Optional[datetime] = Field(default=None, description="Stop timestamp")


# ============================================================================
# RESERVATION DTOs
# ============================================================================

class ReservationRequestDTO(BaseDTO):
    """DTO for reservation request"""
    license_plate: str = Field(description="License plate number")
    vehicle_type: VehicleTypeDTO = Field(description="Vehicle type")
    parking_lot_id: UUID = Field(description="Parking lot ID")
    start_time: datetime = Field(description="Reservation start time")
    end_time: datetime = Field(description="Reservation end time")
    preferred_slot_type: Optional[SlotTypeDTO] = Field(default=None, description="Preferred slot type")
    customer_id: Optional[UUID] = Field(default=None, description="Customer ID")
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validate reservation times"""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError("End time must be after start time")
        
        # Cannot reserve in the past
        if v < datetime.now():
            raise ValueError("Cannot make reservation in the past")
        
        return v
    
    @validator('start_time')
    def validate_start_time(cls, v):
        """Validate start time"""
        # Cannot reserve too far in the past
        if v < datetime.now():
            raise ValueError("Start time cannot be in the past")
        
        # Maximum reservation advance (e.g., 30 days)
        max_advance = timedelta(days=30)
        if v > datetime.now() + max_advance:
            raise ValueError(f"Cannot reserve more than {max_advance.days} days in advance")
        
        return v


class ReservationDTO(BaseDTO):
    """DTO for reservation result"""
    success: bool = Field(description="Reservation success")
    reservation_id: Optional[UUID] = Field(default=None, description="Reservation ID")
    slot_number: Optional[int] = Field(default=None, description="Reserved slot number")
    slot_type: Optional[SlotTypeDTO] = Field(default=None, description="Slot type")
    start_time: Optional[datetime] = Field(default=None, description="Reservation start time")
    end_time: Optional[datetime] = Field(default=None, description="Reservation end time")
    confirmation_code: Optional[str] = Field(default=None, description="Confirmation code")
    message: Optional[str] = Field(default=None, description="Result message")
    timestamp: Optional[datetime] = Field(default=None, description="Reservation timestamp")


class ReservationUpdateDTO(BaseDTO):
    """DTO for updating reservation"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    preferred_slot_type: Optional[SlotTypeDTO] = None
    
    @root_validator
    def validate_times(cls, values):
        """Validate time updates"""
        start_time = values.get('start_time')
        end_time = values.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise ValueError("End time must be after start time")
        
        return values


# ============================================================================
# BILLING & PAYMENT DTOs
# ============================================================================

class InvoiceItemDTO(BaseDTO):
    """Invoice item DTO"""
    description: str = Field(description="Item description")
    quantity: float = Field(ge=0, description="Quantity")
    unit_price: MoneyDTO = Field(description="Unit price")
    total: MoneyDTO = Field(description="Item total")
    service_type: str = Field(description="Service type (parking, charging, etc.)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class InvoiceCreateDTO(BaseDTO):
    """DTO for creating invoice"""
    customer_id: Optional[UUID] = Field(default=None, description="Customer ID")
    license_plate: str = Field(description="License plate")
    items: List[InvoiceItemDTO] = Field(min_length=1, description="Invoice items")
    due_date: Optional[datetime] = Field(default=None, description="Invoice due date")
    notes: Optional[str] = Field(default=None, description="Invoice notes")


class InvoiceDTO(BaseDTO):
    """Complete invoice DTO"""
    id: UUID = Field(description="Invoice ID")
    invoice_number: str = Field(description="Invoice number")
    customer_id: Optional[UUID] = Field(default=None, description="Customer ID")
    license_plate: str = Field(description="License plate")
    items: List[InvoiceItemDTO] = Field(description="Invoice items")
    subtotal: MoneyDTO = Field(description="Subtotal amount")
    tax: MoneyDTO = Field(description="Tax amount")
    total: MoneyDTO = Field(description="Total amount")
    status: InvoiceStatusDTO = Field(description="Invoice status")
    issue_date: datetime = Field(description="Issue date")
    due_date: Optional[datetime] = Field(default=None, description="Due date")
    paid_date: Optional[datetime] = Field(default=None, description="Payment date")
    notes: Optional[str] = Field(default=None, description="Invoice notes")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class PaymentRequestDTO(BaseDTO):
    """DTO for payment request"""
    invoice_id: UUID = Field(description="Invoice ID")
    amount: MoneyDTO = Field(description="Payment amount")
    payment_method: PaymentMethodDTO = Field(description="Payment method")
    payment_details: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Payment method details (card token, etc.)"
    )
    customer_id: Optional[UUID] = Field(default=None, description="Customer ID")


class PaymentDTO(BaseDTO):
    """Complete payment DTO"""
    id: UUID = Field(description="Payment ID")
    invoice_id: UUID = Field(description="Invoice ID")
    payment_number: str = Field(description="Payment number")
    amount: MoneyDTO = Field(description="Payment amount")
    payment_method: PaymentMethodDTO = Field(description="Payment method")
    status: PaymentStatusDTO = Field(description="Payment status")
    transaction_id: Optional[str] = Field(default=None, description="Transaction ID from payment gateway")
    payment_details: Optional[Dict[str, Any]] = Field(default=None, description="Payment method details")
    customer_id: Optional[UUID] = Field(default=None, description="Customer ID")
    processed_at: Optional[datetime] = Field(default=None, description="Processing timestamp")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


# ============================================================================
# CUSTOMER DTOs
# ============================================================================

class CustomerBaseDTO(BaseDTO):
    """Base customer DTO"""
    email: str = Field(description="Email address")
    first_name: str = Field(min_length=1, description="First name")
    last_name: str = Field(min_length=1, description="Last name")
    phone: Optional[str] = Field(default=None, description="Phone number")
    company: Optional[str] = Field(default=None, description="Company name")
    
    @validator('email')
    def validate_email(cls, v):
        """Basic email validation"""
        if '@' not in v:
            raise ValueError("Invalid email address")
        return v


class CustomerCreateDTO(CustomerBaseDTO):
    """DTO for creating customer"""
    password: Optional[str] = Field(default=None, min_length=8, description="Password (if creating user account)")


class CustomerUpdateDTO(BaseDTO):
    """DTO for updating customer"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerDTO(CustomerBaseDTO):
    """Complete customer DTO"""
    id: UUID = Field(description="Customer ID")
    customer_number: str = Field(description="Customer number")
    vehicles: List[VehicleDTO] = Field(default_factory=list, description="Customer vehicles")
    has_subscription: bool = Field(default=False, description="Has active subscription")
    subscription_tier: Optional[str] = Field(default=None, description="Subscription tier")
    total_spent: MoneyDTO = Field(default_factory=lambda: MoneyDTO(amount=Decimal('0'), currency="USD"), description="Total amount spent")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    is_active: bool = Field(default=True, description="Is customer active")


# ============================================================================
# MONITORING & ANALYTICS DTOs
# ============================================================================

class MetricDTO(BaseDTO):
    """Metric DTO"""
    name: str = Field(description="Metric name")
    value: float = Field(description="Metric value")
    timestamp: datetime = Field(description="Metric timestamp")
    source: Optional[str] = Field(default=None, description="Metric source")
    tags: Dict[str, str] = Field(default_factory=dict, description="Metric tags")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class AlertDTO(BaseDTO):
    """Alert DTO"""
    id: UUID = Field(description="Alert ID")
    title: str = Field(description="Alert title")
    message: str = Field(description="Alert message")
    severity: AlertSeverityDTO = Field(description="Alert severity")
    source: str = Field(description="Alert source")
    metric_name: Optional[str] = Field(default=None, description="Related metric name")
    threshold: Optional[float] = Field(default=None, description="Alert threshold")
    actual_value: Optional[float] = Field(default=None, description="Actual value that triggered alert")
    acknowledged: bool = Field(default=False, description="Is alert acknowledged")
    acknowledged_by: Optional[str] = Field(default=None, description="Who acknowledged the alert")
    acknowledged_at: Optional[datetime] = Field(default=None, description="When alert was acknowledged")
    created_at: datetime = Field(description="Creation timestamp")
    resolved_at: Optional[datetime] = Field(default=None, description="Resolution timestamp")


class DashboardDTO(BaseDTO):
    """Dashboard DTO"""
    parking_lot_id: UUID = Field(description="Parking lot ID")
    occupancy_rate: float = Field(ge=0, le=1, description="Current occupancy rate")
    revenue_today: MoneyDTO = Field(description="Revenue today")
    vehicles_in: int = Field(ge=0, description="Vehicles entered today")
    vehicles_out: int = Field(ge=0, description="Vehicles exited today")
    active_charging_sessions: int = Field(ge=0, description="Active charging sessions")
    available_slots: int = Field(ge=0, description="Available slots")
    recent_alerts: List[AlertDTO] = Field(default_factory=list, description="Recent alerts")
    hourly_occupancy: List[Dict[str, Any]] = Field(default_factory=list, description="Hourly occupancy data")
    top_vehicles: List[Dict[str, Any]] = Field(default_factory=list, description="Top frequent vehicles")
    timestamp: datetime = Field(description="Dashboard timestamp")


class ReportRequestDTO(BaseDTO):
    """DTO for report request"""
    report_type: str = Field(description="Report type")
    start_date: date = Field(description="Report start date")
    end_date: date = Field(description="Report end date")
    parking_lot_id: Optional[UUID] = Field(default=None, description="Parking lot ID")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Report filters")
    format: str = Field(default="json", pattern="^(json|csv|pdf)$", description="Report format")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range"""
        if 'start_date' in values and v < values['start_date']:
            raise ValueError("End date must be after start date")
        
        # Maximum report range (e.g., 1 year)
        max_range = 365
        if 'start_date' in values and (v - values['start_date']).days > max_range:
            raise ValueError(f"Report range cannot exceed {max_range} days")
        
        return v


# ============================================================================
# QUERY & FILTER DTOs
# ============================================================================

class ParkingSlotQueryDTO(PaginatedRequest):
    """DTO for parking slot queries"""
    parking_lot_id: Optional[UUID] = None
    slot_type: Optional[SlotTypeDTO] = None
    floor_level: Optional[int] = None
    is_occupied: Optional[bool] = None
    is_reserved: Optional[bool] = None
    vehicle_type: Optional[VehicleTypeDTO] = None
    features: Optional[List[str]] = None
    min_hourly_rate: Optional[Decimal] = None
    max_hourly_rate: Optional[Decimal] = None


class ParkingLotQueryDTO(PaginatedRequest):
    """DTO for parking lot queries"""
    name: Optional[str] = None
    code: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    min_capacity: Optional[int] = None
    max_capacity: Optional[int] = None
    has_ev_charging: Optional[bool] = None
    is_active: Optional[bool] = None


class InvoiceQueryDTO(PaginatedRequest):
    """DTO for invoice queries"""
    customer_id: Optional[UUID] = None
    license_plate: Optional[str] = None
    status: Optional[InvoiceStatusDTO] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    issue_date_from: Optional[date] = None
    issue_date_to: Optional[date] = None
    due_date_from: Optional[date] = None
    due_date_to: Optional[date] = None


class PaymentQueryDTO(PaginatedRequest):
    """DTO for payment queries"""
    invoice_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    payment_method: Optional[PaymentMethodDTO] = None
    status: Optional[PaymentStatusDTO] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    processed_date_from: Optional[date] = None
    processed_date_to: Optional[date] = None


class ReservationQueryDTO(PaginatedRequest):
    """DTO for reservation queries"""
    customer_id: Optional[UUID] = None
    license_plate: Optional[str] = None
    parking_lot_id: Optional[UUID] = None
    status: Optional[ReservationStatusDTO] = None
    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None
    end_date_from: Optional[date] = None
    end_date_to: Optional[date] = None


# ============================================================================
# RESPONSE DTOs
# ============================================================================

class SuccessResponseDTO(BaseDTO):
    """Standard success response DTO"""
    success: bool = Field(default=True, description="Success flag")
    message: str = Field(description="Success message")
    data: Optional[Any] = Field(default=None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ErrorResponseDTO(BaseDTO):
    """Standard error response DTO"""
    success: bool = Field(default=False, description="Success flag")
    error: str = Field(description="Error message")
    error_code: Optional[str] = Field(default=None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class ValidationErrorDTO(BaseDTO):
    """Validation error DTO"""
    success: bool = Field(default=False, description="Success flag")
    error: str = Field(default="Validation failed", description="Error message")
    errors: List[Dict[str, str]] = Field(description="Validation errors")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


# ============================================================================
# DTO FACTORY AND UTILITIES
# ============================================================================

class DTOFactory:
    """Factory for creating DTOs from various sources"""
    
    @staticmethod
    def create_parking_request(
        license_plate: str,
        vehicle_type: VehicleTypeDTO,
        parking_lot_id: UUID,
        **kwargs
    ) -> ParkingRequestDTO:
        """Create ParkingRequestDTO"""
        return ParkingRequestDTO(
            license_plate=license_plate,
            vehicle_type=vehicle_type,
            parking_lot_id=parking_lot_id,
            **kwargs
        )
    
    @staticmethod
    def create_charging_request(
        license_plate: str,
        vehicle_type: VehicleTypeDTO,
        station_id: UUID,
        current_charge: float,
        target_charge: float,
        battery_capacity: float,
        **kwargs
    ) -> ChargingRequestDTO:
        """Create ChargingRequestDTO"""
        return ChargingRequestDTO(
            license_plate=license_plate,
            vehicle_type=vehicle_type,
            station_id=station_id,
            current_charge_percentage=current_charge,
            target_charge_percentage=target_charge,
            battery_capacity_kwh=battery_capacity,
            **kwargs
        )
    
    @staticmethod
    def create_reservation_request(
        license_plate: str,
        vehicle_type: VehicleTypeDTO,
        parking_lot_id: UUID,
        start_time: datetime,
        end_time: datetime,
        **kwargs
    ) -> ReservationRequestDTO:
        """Create ReservationRequestDTO"""
        return ReservationRequestDTO(
            license_plate=license_plate,
            vehicle_type=vehicle_type,
            parking_lot_id=parking_lot_id,
            start_time=start_time,
            end_time=end_time,
            **kwargs
        )
    
    @staticmethod
    def create_money(amount: Union[Decimal, float, str], currency: str = "USD") -> MoneyDTO:
        """Create MoneyDTO"""
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        return MoneyDTO(amount=amount, currency=currency)
    
    @staticmethod
    def create_time_range(start_time: datetime, end_time: datetime) -> TimeRangeDTO:
        """Create TimeRangeDTO"""
        return TimeRangeDTO(start_time=start_time, end_time=end_time)


class DTOValidator:
    """Validator for DTOs"""
    
    @staticmethod
    def validate_dto(dto: BaseDTO) -> Tuple[bool, List[str]]:
        """Validate DTO and return (is_valid, errors)"""
        try:
            # Pydantic models are validated on creation
            # This is just for explicit validation calls
            return True, []
        except Exception as e:
            return False, [str(e)]
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_license_plate(plate: str, country_code: Optional[str] = None) -> bool:
        """Validate license plate format"""
        # Basic validation - can be extended per country
        plate = plate.strip().upper()
        return bool(plate) and len(plate) <= 20


# ============================================================================
# SERIALIZATION UTILITIES
# ============================================================================

class DTOSerializer:
    """Serializer for DTOs"""
    
    @staticmethod
    def serialize(dto: BaseDTO, **kwargs) -> str:
        """Serialize DTO to JSON"""
        return dto.to_json(**kwargs)
    
    @staticmethod
    def deserialize(json_str: str, dto_class: Type[T]) -> T:
        """Deserialize JSON to DTO"""
        return dto_class.from_json(json_str)
    
    @staticmethod
    def to_dict(dto: BaseDTO, exclude_none: bool = False, **kwargs) -> Dict[str, Any]:
        """Convert DTO to dictionary"""
        return dto.to_dict(exclude_none=exclude_none, **kwargs)
    
    @staticmethod
    def from_dict(data: Dict[str, Any], dto_class: Type[T]) -> T:
        """Create DTO from dictionary"""
        return dto_class.from_dict(data)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Example usage of DTOs"""
    
    # Create a parking request DTO
    parking_request = ParkingRequestDTO(
        license_plate="ABC-123",
        vehicle_type=VehicleTypeDTO.CAR,
        parking_lot_id=uuid4(),
        preferences={"preferred_slot_type": "premium"}
    )
    
    print(f"Parking Request: {parking_request.to_dict()}")
    
    # Create a money DTO
    money = MoneyDTO(amount=Decimal("15.75"), currency="USD")
    print(f"Money: {money.amount} {money.currency}")
    
    # Create a charging request DTO
    charging_request = ChargingRequestDTO(
        license_plate="EV-456",
        vehicle_type=VehicleTypeDTO.EV_CAR,
        station_id=uuid4(),
        current_charge_percentage=20.0,
        target_charge_percentage=80.0,
        battery_capacity_kwh=60.0,
        charging_strategy=ChargingStrategyTypeDTO.FAST
    )
    
    print(f"Charging Request: {charging_request.to_dict()}")
    
    # Serialize to JSON
    json_str = parking_request.to_json()
    print(f"JSON: {json_str}")
    
    # Deserialize from JSON
    deserialized = ParkingRequestDTO.from_json(json_str)
    print(f"Deserialized: {deserialized.license_plate}")
    
    # Create paginated query
    query = ParkingSlotQueryDTO(
        page=1,
        page_size=10,
        slot_type=SlotTypeDTO.EV,
        is_occupied=False
    )
    
    print(f"Query: Page {query.page}, Size {query.page_size}")
    
    # Create error response
    error_response = ErrorResponseDTO(
        error="Parking lot is full",
        error_code="PARKING_LOT_FULL",
        details={"parking_lot_id": str(uuid4()), "occupancy_rate": 1.0}
    )
    
    print(f"Error Response: {error_response.error}")


if __name__ == "__main__":
    example_usage()