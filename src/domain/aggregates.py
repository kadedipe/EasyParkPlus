# File: src/domain/aggregates.py
"""
Aggregate Roots for Parking Management System
Following Domain-Driven Design (DDD) Aggregate Pattern

Aggregates:
1. ParkingLot - Root aggregate for parking operations
2. ChargingStation - Root aggregate for EV charging
3. ParkingSession - Root aggregate for billing and tracking

Key Concepts:
- Aggregate Roots enforce business invariants
- Entities within aggregates are accessed through the root
- Domain events are raised for important state changes
- All modifications go through aggregate root methods
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Tuple, Any
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import logging

from .models import (
    Entity, ParkingSlot, Vehicle, ElectricVehicle,
    LicensePlate, Location, Capacity, Money, TimeRange,
    VehicleType, SlotType, ChargerType, ParkingStatus,
    VehicleParkedEvent, VehicleLeftEvent, EVChargingStartedEvent,
    EVChargingCompletedEvent, DomainEvent,
    ParkingFeeCalculator, validate_parking_duration
)


# ============================================================================
# BASE AGGREGATE ROOT
# ============================================================================

class AggregateRoot(Entity):
    """
    Base class for all aggregate roots
    Provides domain event collection and versioning
    """
    
    def __init__(self, id: Optional[str] = None):
        super().__init__(id)
        self._version: int = 1
        self._changes: List[DomainEvent] = []
        self._logger = logging.getLogger(self.__class__.__name__)
    
    @property
    def version(self) -> int:
        """Get current aggregate version"""
        return self._version
    
    def _increment_version(self) -> None:
        """Increment version after state change"""
        self._version += 1
    
    def _add_domain_event(self, event: DomainEvent) -> None:
        """Add a domain event to the list of changes"""
        self._changes.append(event)
        self._logger.debug(f"Added domain event: {event.__class__.__name__}")
    
    def clear_events(self) -> List[DomainEvent]:
        """Clear and return all domain events"""
        events = self._changes.copy()
        self._changes.clear()
        return events
    
    @property
    def has_changes(self) -> bool:
        """Check if aggregate has pending domain events"""
        return len(self._changes) > 0
    
    def _validate_invariants(self) -> None:
        """Validate aggregate invariants - to be overridden by subclasses"""
        pass


# ============================================================================
# PARKING LOT AGGREGATE
# ============================================================================

@dataclass
class ParkingPolicies:
    """Value Object: Parking lot business policies"""
    max_stay_hours: float = 24.0
    ev_can_use_regular: bool = True
    allow_overstay: bool = False
    overstay_fee_multiplier: Decimal = Decimal('1.5')
    reservation_required: bool = False
    min_reservation_hours: float = 1.0
    
    def __post_init__(self):
        """Validate policy values"""
        if self.max_stay_hours <= 0:
            raise ValueError("Max stay hours must be positive")
        
        if self.overstay_fee_multiplier < Decimal('1.0'):
            raise ValueError("Overstay fee multiplier cannot be less than 1.0")
        
        if self.min_reservation_hours <= 0:
            raise ValueError("Min reservation hours must be positive")


class ParkingLot(AggregateRoot):
    """
    Aggregate Root: Parking Lot with slots and parking operations
    Enforces business rules and invariants for parking operations
    """
    
    def __init__(
        self,
        name: str,
        location: Location,
        capacity: Capacity,
        policies: Optional[ParkingPolicies] = None,
        id: Optional[str] = None
    ):
        super().__init__(id)
        self.name = name
        self.location = location
        self.capacity = capacity
        self.policies = policies or ParkingPolicies()
        
        # Internal state
        self._slots: Dict[str, ParkingSlot] = {}  # slot_id -> ParkingSlot
        self._occupied_slots: Set[str] = set()    # Set of occupied slot IDs
        self._slot_numbers: Dict[int, str] = {}   # slot_number -> slot_id
        self._vehicle_to_slot: Dict[str, str] = {}  # vehicle_id -> slot_id
        
        # Statistics
        self.total_parking_sessions: int = 0
        self.total_revenue: Money = Money(Decimal('0.00'))
        self.creation_date: datetime = datetime.now()
        self.last_updated: datetime = self.creation_date
        
        # Initialize slots based on capacity
        self._initialize_slots()
        self._validate_invariants()
        
        self._logger.info(f"Created ParkingLot: {self.name} (ID: {self.id})")
    
    def _initialize_slots(self) -> None:
        """Initialize parking slots based on capacity"""
        slot_number = 1
        
        # Create regular slots
        for _ in range(self.capacity.regular):
            self._create_slot(slot_number, SlotType.REGULAR)
            slot_number += 1
        
        # Create EV slots
        for _ in range(self.capacity.ev):
            self._create_slot(slot_number, SlotType.EV)
            slot_number += 1
        
        # Create disabled slots
        for _ in range(self.capacity.disabled):
            self._create_slot(slot_number, SlotType.DISABLED)
            slot_number += 1
        
        # Create premium slots
        for _ in range(self.capacity.premium):
            self._create_slot(slot_number, SlotType.PREMIUM)
            slot_number += 1
        
        self._logger.debug(f"Initialized {len(self._slots)} slots")
    
    def _create_slot(self, number: int, slot_type: SlotType) -> str:
        """Create a parking slot and add to internal collections"""
        slot = ParkingSlot(
            number=number,
            slot_type=slot_type,
            floor_level=1  # Could be parameterized
        )
        
        self._slots[slot.id] = slot
        self._slot_numbers[number] = slot.id
        
        return slot.id
    
    def _validate_invariants(self) -> None:
        """Validate aggregate invariants"""
        # Invariant 1: Slot count must match capacity
        total_slots = len(self._slots)
        expected_slots = self.capacity.total_capacity()
        
        if total_slots != expected_slots:
            raise ValueError(
                f"Slot count mismatch: {total_slots} slots, "
                f"expected {expected_slots} from capacity"
            )
        
        # Invariant 2: Occupied slots must be valid slots
        for slot_id in self._occupied_slots:
            if slot_id not in self._slots:
                raise ValueError(f"Occupied slot {slot_id} not found in slots")
        
        # Invariant 3: Vehicle to slot mapping must be consistent
        for vehicle_id, slot_id in self._vehicle_to_slot.items():
            if slot_id not in self._occupied_slots:
                raise ValueError(
                    f"Vehicle {vehicle_id} mapped to non-occupied slot {slot_id}"
                )
        
        # Invariant 4: Slot numbers must be unique
        if len(self._slot_numbers) != total_slots:
            raise ValueError("Duplicate slot numbers detected")
        
        self._logger.debug("All parking lot invariants satisfied")
    
    # ========================================================================
    # PUBLIC BUSINESS METHODS
    # ========================================================================
    
    def park_vehicle(
        self,
        vehicle: Vehicle,
        preferred_slot_type: Optional[SlotType] = None
    ) -> Tuple[str, str]:
        """
        Park a vehicle in the lot
        Returns: (slot_id, ticket_number)
        Raises: ValueError if no suitable slot available
        """
        self._logger.info(f"Parking vehicle: {vehicle.license_plate}")
        
        # Check if vehicle is already parked
        if vehicle.id in self._vehicle_to_slot:
            raise ValueError(f"Vehicle {vehicle.license_plate} is already parked")
        
        # Find suitable slot
        slot = self._find_suitable_slot(vehicle, preferred_slot_type)
        if not slot:
            raise ValueError(f"No suitable slot available for {vehicle.vehicle_type}")
        
        # Occupy the slot
        slot.occupy(vehicle.id)
        self._occupied_slots.add(slot.id)
        self._vehicle_to_slot[vehicle.id] = slot.id
        
        # Generate ticket
        ticket_number = self._generate_ticket_number()
        
        # Update statistics
        self.total_parking_sessions += 1
        self.last_updated = datetime.now()
        self._increment_version()
        
        # Raise domain event
        event = VehicleParkedEvent(
            parking_lot_id=self.id,
            slot_id=slot.id,
            vehicle_id=vehicle.id,
            license_plate=vehicle.license_plate.value,
            vehicle_type=vehicle.vehicle_type
        )
        self._add_domain_event(event)
        
        self._logger.info(
            f"Vehicle {vehicle.license_plate} parked in slot {slot.number} "
            f"(Ticket: {ticket_number})"
        )
        
        return slot.id, ticket_number
    
    def leave_slot(
        self,
        slot_id: str,
        vehicle_id: Optional[str] = None
    ) -> Tuple[Optional[Money], Optional[TimeRange]]:
        """
        Remove vehicle from slot
        Returns: (fee, time_range) if vehicle was parked, (None, None) otherwise
        """
        if slot_id not in self._slots:
            raise ValueError(f"Slot {slot_id} not found")
        
        slot = self._slots[slot_id]
        
        if not slot.is_occupied:
            self._logger.warning(f"Slot {slot.number} is not occupied")
            return None, None
        
        # Verify vehicle if provided
        if vehicle_id and slot.current_vehicle_id != vehicle_id:
            raise ValueError(
                f"Vehicle {vehicle_id} not found in slot {slot.number}. "
                f"Slot contains: {slot.current_vehicle_id}"
            )
        
        # Get actual vehicle ID
        actual_vehicle_id = slot.current_vehicle_id
        if not actual_vehicle_id:
            self._logger.error(f"Slot {slot.number} marked occupied but has no vehicle ID")
            return None, None
        
        # Vacate the slot
        time_range = slot.vacate()
        self._occupied_slots.remove(slot.id)
        
        if actual_vehicle_id in self._vehicle_to_slot:
            del self._vehicle_to_slot[actual_vehicle_id]
        
        # Calculate fee if we have time range
        fee = None
        if time_range:
            # Check for overstay
            duration_hours = time_range.duration_hours
            if duration_hours > self.policies.max_stay_hours:
                self._logger.warning(
                    f"Vehicle overstayed by {duration_hours - self.policies.max_stay_hours:.1f} hours"
                )
            
            # Calculate fee (in real system, would fetch vehicle from repository)
            fee = ParkingFeeCalculator.calculate_fee(slot, time_range)
            
            # Apply overstay penalty if applicable
            if (duration_hours > self.policies.max_stay_hours and 
                not self.policies.allow_overstay):
                penalty_multiplier = self.policies.overstay_fee_multiplier
                penalty_fee = Money(fee.amount * penalty_multiplier, fee.currency)
                
                self._logger.info(
                    f"Applied overstay penalty: {fee.format()} → {penalty_fee.format()}"
                )
                fee = penalty_fee
            
            # Update revenue
            self.total_revenue = self.total_revenue + fee
        
        self.last_updated = datetime.now()
        self._increment_version()
        
        # Raise domain event
        if time_range and actual_vehicle_id:
            # In real system, we would fetch license plate from vehicle repository
            license_plate = "UNKNOWN"  # Placeholder
            fee_amount = fee.amount if fee else None
            
            event = VehicleLeftEvent(
                parking_lot_id=self.id,
                slot_id=slot.id,
                vehicle_id=actual_vehicle_id,
                license_plate=license_plate,
                entry_time=time_range.start_time,
                exit_time=time_range.end_time,
                duration_minutes=time_range.duration_minutes,
                fee_amount=fee_amount
            )
            self._add_domain_event(event)
        
        self._logger.info(f"Vehicle left slot {slot.number}. Fee: {fee.format() if fee else 'None'}")
        
        return fee, time_range
    
    def find_available_slot(
        self,
        vehicle_type: VehicleType,
        slot_type: Optional[SlotType] = None
    ) -> Optional[ParkingSlot]:
        """
        Find an available slot for the given vehicle type
        Optionally filter by specific slot type
        """
        for slot in self._slots.values():
            if not slot.is_occupied and slot.can_accommodate_vehicle_type(vehicle_type):
                if slot_type is None or slot.slot_type == slot_type:
                    return slot
        return None
    
    def get_slot_by_number(self, slot_number: int) -> Optional[ParkingSlot]:
        """Get slot by its number"""
        slot_id = self._slot_numbers.get(slot_number)
        if slot_id:
            return self._slots.get(slot_id)
        return None
    
    def get_slot_by_vehicle(self, vehicle_id: str) -> Optional[ParkingSlot]:
        """Get slot containing the given vehicle"""
        slot_id = self._vehicle_to_slot.get(vehicle_id)
        if slot_id:
            return self._slots.get(slot_id)
        return None
    
    def get_vehicle_in_slot(self, slot_id: str) -> Optional[str]:
        """Get vehicle ID in the given slot"""
        slot = self._slots.get(slot_id)
        if slot and slot.is_occupied:
            return slot.current_vehicle_id
        return None
    
    # ========================================================================
    # INTERNAL HELPER METHODS
    # ========================================================================
    
    def _find_suitable_slot(
        self,
        vehicle: Vehicle,
        preferred_slot_type: Optional[SlotType] = None
    ) -> Optional[ParkingSlot]:
        """
        Find a suitable slot for the vehicle
        Implements business rules for slot allocation
        """
        # If preferred type specified, try that first
        if preferred_slot_type:
            slot = self.find_available_slot(vehicle.vehicle_type, preferred_slot_type)
            if slot:
                return slot
        
        # Business rule: EVs prefer EV slots but can use regular if allowed
        if vehicle.vehicle_type.is_electric:
            # Try EV slots first
            ev_slot = self.find_available_slot(vehicle.vehicle_type, SlotType.EV)
            if ev_slot:
                return ev_slot
            
            # If allowed, try regular slots
            if self.policies.ev_can_use_regular:
                regular_slot = self.find_available_slot(vehicle.vehicle_type, SlotType.REGULAR)
                if regular_slot:
                    return regular_slot
            
            return None
        
        # For non-EV vehicles
        return self.find_available_slot(vehicle.vehicle_type)
    
    def _generate_ticket_number(self) -> str:
        """Generate a unique ticket number"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8].upper()
        return f"TKT-{timestamp}-{unique_id}"
    
    # ========================================================================
    # QUERY METHODS (Read-only)
    # ========================================================================
    
    @property
    def total_slots(self) -> int:
        """Get total number of slots"""
        return len(self._slots)
    
    @property
    def occupied_slots(self) -> int:
        """Get number of occupied slots"""
        return len(self._occupied_slots)
    
    @property
    def available_slots(self) -> int:
        """Get number of available slots"""
        return self.total_slots - self.occupied_slots
    
    def get_occupancy_rate(self) -> float:
        """Calculate occupancy rate (0-100)"""
        if self.total_slots == 0:
            return 0.0
        return (self.occupied_slots / self.total_slots) * 100.0
    
    def get_slots_by_type(self, slot_type: SlotType) -> List[ParkingSlot]:
        """Get all slots of specific type"""
        return [slot for slot in self._slots.values() if slot.slot_type == slot_type]
    
    def get_available_slots_by_type(self, slot_type: SlotType) -> List[ParkingSlot]:
        """Get available slots of specific type"""
        return [
            slot for slot in self._slots.values()
            if slot.slot_type == slot_type and not slot.is_occupied
        ]
    
    def get_occupied_slots_by_type(self, slot_type: SlotType) -> List[ParkingSlot]:
        """Get occupied slots of specific type"""
        return [
            slot for slot in self._slots.values()
            if slot.slot_type == slot_type and slot.is_occupied
        ]
    
    def get_slot_status(self, slot_id: str) -> Dict[str, Any]:
        """Get detailed status of a slot"""
        slot = self._slots.get(slot_id)
        if not slot:
            raise ValueError(f"Slot {slot_id} not found")
        
        status = slot.to_dict()
        status["parking_lot_id"] = self.id
        status["parking_lot_name"] = self.name
        
        if slot.is_occupied and slot.current_vehicle_id:
            status["vehicle_id"] = slot.current_vehicle_id
            status["occupancy_duration"] = slot.get_occupancy_duration()
        
        return status
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report"""
        return {
            "parking_lot_id": self.id,
            "name": self.name,
            "location": self.location.to_dict(),
            "capacity": {
                "total": self.capacity.total_capacity(),
                "regular": self.capacity.regular,
                "ev": self.capacity.ev,
                "disabled": self.capacity.disabled,
                "premium": self.capacity.premium,
            },
            "occupancy": {
                "total_slots": self.total_slots,
                "occupied_slots": self.occupied_slots,
                "available_slots": self.available_slots,
                "occupancy_rate": self.get_occupancy_rate(),
                "by_type": {
                    slot_type.value: {
                        "total": len(self.get_slots_by_type(slot_type)),
                        "occupied": len(self.get_occupied_slots_by_type(slot_type)),
                        "available": len(self.get_available_slots_by_type(slot_type)),
                    }
                    for slot_type in SlotType
                }
            },
            "statistics": {
                "total_sessions": self.total_parking_sessions,
                "total_revenue": self.total_revenue.to_dict(),
                "creation_date": self.creation_date.isoformat(),
                "last_updated": self.last_updated.isoformat(),
            },
            "policies": {
                "max_stay_hours": self.policies.max_stay_hours,
                "ev_can_use_regular": self.policies.ev_can_use_regular,
                "allow_overstay": self.policies.allow_overstay,
                "overstay_fee_multiplier": float(self.policies.overstay_fee_multiplier),
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_vehicle_location(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Find where a specific vehicle is parked"""
        slot = self.get_slot_by_vehicle(vehicle_id)
        if not slot:
            return None
        
        return {
            "slot_id": slot.id,
            "slot_number": slot.number,
            "slot_type": slot.slot_type.value,
            "floor_level": slot.floor_level,
            "location_code": slot.location_code,
            "parked_since": slot.occupancy_start_time.isoformat() if slot.occupancy_start_time else None,
            "duration_minutes": slot.get_occupancy_duration().total_seconds() / 60 if slot.get_occupancy_duration() else None
        }
    
    # ========================================================================
    # MAINTENANCE OPERATIONS
    # ========================================================================
    
    def close_slot(self, slot_id: str, reason: str = "Maintenance") -> None:
        """Close a slot for maintenance"""
        slot = self._slots.get(slot_id)
        if not slot:
            raise ValueError(f"Slot {slot_id} not found")
        
        if slot.is_occupied:
            raise ValueError(f"Cannot close occupied slot {slot.number}")
        
        # Add maintenance feature
        if "maintenance" not in slot.features:
            slot.features.append("maintenance")
        
        self.last_updated = datetime.now()
        self._increment_version()
        
        self._logger.info(f"Closed slot {slot.number} for {reason}")
    
    def reopen_slot(self, slot_id: str) -> None:
        """Reopen a closed slot"""
        slot = self._slots.get(slot_id)
        if not slot:
            raise ValueError(f"Slot {slot_id} not found")
        
        if "maintenance" in slot.features:
            slot.features.remove("maintenance")
        
        self.last_updated = datetime.now()
        self._increment_version()
        
        self._logger.info(f"Reopened slot {slot.number}")
    
    def update_policies(self, new_policies: ParkingPolicies) -> None:
        """Update parking lot policies"""
        self.policies = new_policies
        self.last_updated = datetime.now()
        self._increment_version()
        
        self._logger.info(f"Updated parking lot policies")
    
    # ========================================================================
    # SERIALIZATION
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregate to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location.to_dict(),
            "capacity": {
                "regular": self.capacity.regular,
                "ev": self.capacity.ev,
                "disabled": self.capacity.disabled,
                "premium": self.capacity.premium,
            },
            "policies": {
                "max_stay_hours": self.policies.max_stay_hours,
                "ev_can_use_regular": self.policies.ev_can_use_regular,
                "allow_overstay": self.policies.allow_overstay,
                "overstay_fee_multiplier": float(self.policies.overstay_fee_multiplier),
                "reservation_required": self.policies.reservation_required,
                "min_reservation_hours": self.policies.min_reservation_hours,
            },
            "statistics": {
                "total_slots": self.total_slots,
                "occupied_slots": self.occupied_slots,
                "total_sessions": self.total_parking_sessions,
                "total_revenue": self.total_revenue.to_dict(),
                "creation_date": self.creation_date.isoformat(),
                "last_updated": self.last_updated.isoformat(),
            },
            "version": self.version,
            "has_changes": self.has_changes,
        }
    
    def __str__(self) -> str:
        return f"ParkingLot: {self.name} ({self.occupied_slots}/{self.total_slots} occupied)"


# ============================================================================
# CHARGING STATION AGGREGATE
# ============================================================================

@dataclass
class ChargingConnector:
    """Entity within ChargingStation aggregate"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connector_type: ChargerType = ChargerType.LEVEL_2
    max_power_kw: float = 7.2
    is_available: bool = True
    current_session_id: Optional[str] = None
    current_power_kw: float = 0.0
    total_energy_delivered_kwh: float = 0.0
    total_sessions: int = 0
    
    def __post_init__(self):
        """Validate connector configuration"""
        if self.max_power_kw <= 0:
            raise ValueError("Max power must be positive")
        
        if self.current_power_kw < 0:
            raise ValueError("Current power cannot be negative")
        
        if self.total_energy_delivered_kwh < 0:
            raise ValueError("Total energy delivered cannot be negative")
    
    def start_session(self, session_id: str, requested_power_kw: float) -> None:
        """Start a charging session on this connector"""
        if not self.is_available:
            raise ValueError(f"Connector {self.id} is not available")
        
        if requested_power_kw > self.max_power_kw:
            raise ValueError(
                f"Requested power {requested_power_kw}kW exceeds "
                f"connector max {self.max_power_kw}kW"
            )
        
        self.is_available = False
        self.current_session_id = session_id
        self.current_power_kw = requested_power_kw
        self.total_sessions += 1
    
    def stop_session(self, energy_delivered_kwh: float) -> None:
        """Stop the current charging session"""
        if self.is_available:
            raise ValueError(f"Connector {self.id} is not in use")
        
        self.is_available = True
        self.current_session_id = None
        self.current_power_kw = 0.0
        self.total_energy_delivered_kwh += energy_delivered_kwh
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the connector"""
        return {
            "connector_id": self.id,
            "connector_type": self.connector_type.value,
            "max_power_kw": self.max_power_kw,
            "is_available": self.is_available,
            "current_session_id": self.current_session_id,
            "current_power_kw": self.current_power_kw,
            "total_energy_delivered_kwh": self.total_energy_delivered_kwh,
            "total_sessions": self.total_sessions,
        }
    
    def __str__(self) -> str:
        status = "🟢 Available" if self.is_available else "🔴 In Use"
        return f"Connector {self.id} ({self.connector_type.value}) - {status}"


class ChargingStation(AggregateRoot):
    """
    Aggregate Root: EV Charging Station
    Manages charging connectors and sessions
    """
    
    def __init__(
        self,
        name: str,
        location: Location,
        max_total_power_kw: float,
        parking_lot_id: Optional[str] = None,
        id: Optional[str] = None
    ):
        super().__init__(id)
        self.name = name
        self.location = location
        self.max_total_power_kw = max_total_power_kw
        self.parking_lot_id = parking_lot_id
        
        # Internal state
        self._connectors: Dict[str, ChargingConnector] = {}
        self._active_sessions: Set[str] = set()  # Set of active session IDs
        self.current_total_power_kw: float = 0.0
        self.status: str = "active"  # active, maintenance, offline
        
        # Statistics
        self.total_energy_delivered_kwh: float = 0.0
        self.total_sessions: int = 0
        self.total_revenue: Money = Money(Decimal('0.00'))
        self.creation_date: datetime = datetime.now()
        self.last_updated: datetime = self.creation_date
        
        self._validate_invariants()
        self._logger.info(f"Created ChargingStation: {self.name} (ID: {self.id})")
    
    def _validate_invariants(self) -> None:
        """Validate charging station invariants"""
        # Invariant 1: Current power cannot exceed max power
        if self.current_total_power_kw > self.max_total_power_kw:
            raise ValueError(
                f"Current power {self.current_total_power_kw}kW exceeds "
                f"max power {self.max_total_power_kw}kW"
            )
        
        # Invariant 2: Active sessions must be valid
        for session_id in self._active_sessions:
            # Check if session exists on a connector
            session_found = False
            for connector in self._connectors.values():
                if connector.current_session_id == session_id:
                    session_found = True
                    break
            
            if not session_found:
                raise ValueError(f"Active session {session_id} not found on any connector")
        
        self._logger.debug("All charging station invariants satisfied")
    
    # ========================================================================
    # CONNECTOR MANAGEMENT
    # ========================================================================
    
    def add_connector(
        self,
        connector_type: ChargerType,
        max_power_kw: Optional[float] = None
    ) -> str:
        """Add a new charging connector to the station"""
        if self.status != "active":
            raise ValueError(f"Cannot add connector while station is {self.status}")
        
        # Use typical power if not specified
        if max_power_kw is None:
            max_power_kw = connector_type.typical_power_kw
        
        connector = ChargingConnector(
            connector_type=connector_type,
            max_power_kw=max_power_kw
        )
        
        self._connectors[connector.id] = connector
        self.last_updated = datetime.now()
        self._increment_version()
        
        self._logger.info(f"Added {connector_type.value} connector {connector.id}")
        
        return connector.id
    
    def remove_connector(self, connector_id: str) -> None:
        """Remove a connector from the station"""
        connector = self._connectors.get(connector_id)
        if not connector:
            raise ValueError(f"Connector {connector_id} not found")
        
        if not connector.is_available:
            raise ValueError(f"Cannot remove connector {connector_id} while in use")
        
        del self._connectors[connector_id]
        self.last_updated = datetime.now()
        self._increment_version()
        
        self._logger.info(f"Removed connector {connector_id}")
    
    # ========================================================================
    # CHARGING OPERATIONS
    # ========================================================================
    
    def start_charging_session(
        self,
        vehicle_id: str,
        license_plate: str,
        connector_type: ChargerType,
        requested_power_kw: float,
        initial_charge_percentage: float
    ) -> Tuple[str, str]:  # Returns (session_id, connector_id)
        """Start a new charging session"""
        if self.status != "active":
            raise ValueError(f"Charging station is {self.status}")
        
        # Check power capacity
        available_power = self.max_total_power_kw - self.current_total_power_kw
        if requested_power_kw > available_power:
            raise ValueError(
                f"Insufficient power capacity. "
                f"Available: {available_power:.1f}kW, "
                f"Requested: {requested_power_kw:.1f}kW"
            )
        
        # Find available connector
        connector = self._find_available_connector(connector_type, requested_power_kw)
        if not connector:
            raise ValueError(
                f"No available {connector_type.value} connector "
                f"with {requested_power_kw:.1f}kW capacity"
            )
        
        # Create session
        session_id = str(uuid.uuid4())
        
        # Start session on connector
        connector.start_session(session_id, requested_power_kw)
        self._active_sessions.add(session_id)
        self.current_total_power_kw += requested_power_kw
        self.total_sessions += 1
        
        self.last_updated = datetime.now()
        self._increment_version()
        
        # Raise domain event
        event = EVChargingStartedEvent(
            vehicle_id=vehicle_id,
            license_plate=license_plate,
            slot_id=connector.id,
            charger_type=connector_type,
            initial_charge_percentage=initial_charge_percentage,
            target_charge_percentage=100.0  # Default to full charge
        )
        self._add_domain_event(event)
        
        self._logger.info(
            f"Started charging session {session_id} on connector {connector.id} "
            f"for vehicle {license_plate} at {requested_power_kw:.1f}kW"
        )
        
        return session_id, connector.id
    
    def stop_charging_session(
        self,
        session_id: str,
        energy_delivered_kwh: float
    ) -> Money:
        """Stop a charging session and calculate fee"""
        # Find connector with this session
        connector = None
        for c in self._connectors.values():
            if c.current_session_id == session_id:
                connector = c
                break
        
        if not connector:
            raise ValueError(f"No active session found with ID {session_id}")
        
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} is not active")
        
        # Calculate fee
        fee = ParkingFeeCalculator.calculate_ev_charging_fee(
            energy_kwh=energy_delivered_kwh,
            charger_type=connector.connector_type,
            time_of_day=datetime.now()
        )
        
        # Update statistics
        self.total_energy_delivered_kwh += energy_delivered_kwh
        self.total_revenue = self.total_revenue + fee
        
        # Stop session on connector
        connector.stop_session(energy_delivered_kwh)
        self._active_sessions.remove(session_id)
        self.current_total_power_kw -= connector.current_power_kw
        
        self.last_updated = datetime.now()
        self._increment_version()
        
        # Raise domain event
        # Note: In real system, we would have vehicle/license plate from session context
        event = EVChargingCompletedEvent(
            vehicle_id="UNKNOWN",  # Would come from session context
            license_plate="UNKNOWN",  # Would come from session context
            slot_id=connector.id,
            charger_type=connector.connector_type,
            energy_delivered_kwh=energy_delivered_kwh,
            charging_time_minutes=0.0,  # Would calculate from session duration
            fee_amount=fee.amount
        )
        self._add_domain_event(event)
        
        self._logger.info(
            f"Stopped charging session {session_id}. "
            f"Energy delivered: {energy_delivered_kwh:.1f}kWh, "
            f"Fee: {fee.format()}"
        )
        
        return fee
    
    def _find_available_connector(
        self,
        connector_type: ChargerType,
        min_power_kw: float
    ) -> Optional[ChargingConnector]:
        """Find available connector matching requirements"""
        for connector in self._connectors.values():
            if (connector.connector_type == connector_type and 
                connector.is_available and 
                connector.max_power_kw >= min_power_kw):
                return connector
        return None
    
    # ========================================================================
    # MAINTENANCE OPERATIONS
    # ========================================================================
    
    def set_maintenance_mode(self, enabled: bool = True) -> None:
        """Put station in or out of maintenance mode"""
        if enabled:
            if self._active_sessions:
                raise ValueError("Cannot enable maintenance mode with active sessions")
            self.status = "maintenance"
            self._logger.info("Charging station set to maintenance mode")
        else:
            self.status = "active"
            self._logger.info("Charging station set to active mode")
        
        self.last_updated = datetime.now()
        self._increment_version()
    
    def set_offline_mode(self, enabled: bool = True) -> None:
        """Put station in or out of offline mode"""
        if enabled:
            if self._active_sessions:
                raise ValueError("Cannot go offline with active sessions")
            self.status = "offline"
            self._logger.info("Charging station set to offline")
        else:
            self.status = "active"
            self._logger.info("Charging station set to online")
        
        self.last_updated = datetime.now()
        self._increment_version()
    
    # ========================================================================
    # QUERY METHODS
    # ========================================================================
    
    @property
    def total_connectors(self) -> int:
        """Get total number of connectors"""
        return len(self._connectors)
    
    @property
    def available_connectors(self) -> int:
        """Get number of available connectors"""
        return sum(1 for c in self._connectors.values() if c.is_available)
    
    @property
    def active_sessions_count(self) -> int:
        """Get number of active charging sessions"""
        return len(self._active_sessions)
    
    def get_available_power_kw(self) -> float:
        """Get available power capacity"""
        return self.max_total_power_kw - self.current_total_power_kw
    
    def get_connectors_by_type(self, connector_type: ChargerType) -> List[ChargingConnector]:
        """Get all connectors of specific type"""
        return [c for c in self._connectors.values() if c.connector_type == connector_type]
    
    def get_available_connectors_by_type(self, connector_type: ChargerType) -> List[ChargingConnector]:
        """Get available connectors of specific type"""
        return [
            c for c in self._connectors.values()
            if c.connector_type == connector_type and c.is_available
        ]
    
    def get_connector_status(self, connector_id: str) -> Dict[str, Any]:
        """Get detailed status of a connector"""
        connector = self._connectors.get(connector_id)
        if not connector:
            raise ValueError(f"Connector {connector_id} not found")
        
        status = connector.get_status()
        status["charging_station_id"] = self.id
        status["charging_station_name"] = self.name
        status["station_status"] = self.status
        
        return status
    
    def get_status_report(self) -> Dict[str, Any]:
        """Get comprehensive status report"""
        return {
            "charging_station_id": self.id,
            "name": self.name,
            "location": self.location.to_dict(),
            "parking_lot_id": self.parking_lot_id,
            "power": {
                "max_total_kw": self.max_total_power_kw,
                "current_usage_kw": self.current_total_power_kw,
                "available_kw": self.get_available_power_kw(),
            },
            "connectors": {
                "total": self.total_connectors,
                "available": self.available_connectors,
                "active_sessions": self.active_sessions_count,
                "by_type": {
                    charger_type.value: {
                        "total": len(self.get_connectors_by_type(charger_type)),
                        "available": len(self.get_available_connectors_by_type(charger_type)),
                    }
                    for charger_type in ChargerType
                },
                "list": [c.get_status() for c in self._connectors.values()],
            },
            "statistics": {
                "total_energy_delivered_kwh": self.total_energy_delivered_kwh,
                "total_sessions": self.total_sessions,
                "total_revenue": self.total_revenue.to_dict(),
                "creation_date": self.creation_date.isoformat(),
                "last_updated": self.last_updated.isoformat(),
            },
            "status": self.status,
            "timestamp": datetime.now().isoformat()
        }
    
    # ========================================================================
    # SERIALIZATION
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregate to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location.to_dict(),
            "parking_lot_id": self.parking_lot_id,
            "max_total_power_kw": self.max_total_power_kw,
            "current_total_power_kw": self.current_total_power_kw,
            "status": self.status,
            "statistics": {
                "total_connectors": self.total_connectors,
                "active_sessions": self.active_sessions_count,
                "total_energy_delivered_kwh": self.total_energy_delivered_kwh,
                "total_sessions": self.total_sessions,
                "total_revenue": self.total_revenue.to_dict(),
                "creation_date": self.creation_date.isoformat(),
                "last_updated": self.last_updated.isoformat(),
            },
            "version": self.version,
            "has_changes": self.has_changes,
        }
    
    def __str__(self) -> str:
        return f"ChargingStation: {self.name} ({self.active_sessions_count}/{self.total_connectors} active)"


# ============================================================================
# PARKING SESSION AGGREGATE (for billing and tracking)
# ============================================================================

class ParkingSession(AggregateRoot):
    """
    Aggregate Root: Parking Session
    Tracks a complete parking transaction from entry to exit
    Includes billing information and EV charging if applicable
    """
    
    def __init__(
        self,
        parking_lot_id: str,
        slot_id: str,
        vehicle_id: str,
        license_plate: str,
        vehicle_type: VehicleType,
        entry_time: Optional[datetime] = None,
        id: Optional[str] = None
    ):
        super().__init__(id)
        self.parking_lot_id = parking_lot_id
        self.slot_id = slot_id
        self.vehicle_id = vehicle_id
        self.license_plate = license_plate
        self.vehicle_type = vehicle_type
        
        # Session state
        self.entry_time = entry_time or datetime.now()
        self.exit_time: Optional[datetime] = None
        self.status: ParkingStatus = ParkingStatus.ACTIVE
        
        # Billing
        self.parking_fee: Optional[Money] = None
        self.charging_fee: Optional[Money] = None
        self.total_fee: Optional[Money] = None
        self.is_paid: bool = False
        self.payment_method: Optional[str] = None
        self.payment_time: Optional[datetime] = None
        
        # EV Charging (if applicable)
        self.is_ev: bool = vehicle_type.is_electric
        self.charging_session_id: Optional[str] = None
        self.energy_delivered_kwh: float = 0.0
        self.initial_charge_percentage: Optional[float] = None
        self.final_charge_percentage: Optional[float] = None
        
        # Additional metadata
        self.creation_date: datetime = datetime.now()
        self.last_updated: datetime = self.creation_date
        
        self._validate_invariants()
        self._logger.info(
            f"Created ParkingSession for {license_plate} at {self.entry_time}"
        )
    
    def _validate_invariants(self) -> None:
        """Validate parking session invariants"""
        # Invariant 1: Exit time must be after entry time if set
        if self.exit_time and self.exit_time <= self.entry_time:
            raise ValueError("Exit time must be after entry time")
        
        # Invariant 2: Paid sessions must have fees calculated
        if self.is_paid and not self.total_fee:
            raise ValueError("Paid session must have total fee calculated")
        
        # Invariant 3: EV charging data consistency
        if self.charging_session_id and not self.is_ev:
            raise ValueError("Non-EV session cannot have charging session")
        
        self._logger.debug("All parking session invariants satisfied")
    
    # ========================================================================
    # SESSION OPERATIONS
    # ========================================================================
    
    def complete_session(
        self,
        exit_time: datetime,
        parking_fee: Money,
        charging_fee: Optional[Money] = None
    ) -> None:
        """
        Complete the parking session with fees
        """
        if self.status != ParkingStatus.ACTIVE:
            raise ValueError(f"Cannot complete session with status {self.status}")
        
        if exit_time <= self.entry_time:
            raise ValueError("Exit time must be after entry time")
        
        self.exit_time = exit_time
        self.parking_fee = parking_fee
        self.charging_fee = charging_fee
        
        # Calculate total fee
        self.total_fee = parking_fee
        if charging_fee:
            self.total_fee = self.total_fee + charging_fee
        
        self.status = ParkingStatus.COMPLETED
        self.last_updated = datetime.now()
        self._increment_version()
        
        self._logger.info(
            f"Completed session for {self.license_plate}. "
            f"Total fee: {self.total_fee.format()}"
        )
    
    def mark_as_paid(
        self,
        payment_method: str,
        payment_time: Optional[datetime] = None
    ) -> None:
        """
        Mark the session as paid
        """
        if self.status != ParkingStatus.COMPLETED:
            raise ValueError(f"Cannot pay for session with status {self.status}")
        
        if not self.total_fee:
            raise ValueError("Cannot mark as paid without total fee")
        
        self.is_paid = True
        self.payment_method = payment_method
        self.payment_time = payment_time or datetime.now()
        self.last_updated = datetime.now()
        self._increment_version()
        
        self._logger.info(
            f"Marked session for {self.license_plate} as paid "
            f"via {payment_method}"
        )
    
    def add_charging_session(
        self,
        charging_session_id: str,
        initial_charge_percentage: float,
        final_charge_percentage: float,
        energy_delivered_kwh: float
    ) -> None:
        """
        Add EV charging information to the session
        """
        if not self.is_ev:
            raise ValueError("Cannot add charging to non-EV session")
        
        if self.status != ParkingStatus.ACTIVE:
            raise ValueError(f"Cannot add charging to session with status {self.status}")
        
        self.charging_session_id = charging_session_id
        self.initial_charge_percentage = initial_charge_percentage
        self.final_charge_percentage = final_charge_percentage
        self.energy_delivered_kwh = energy_delivered_kwh
        
        self.last_updated = datetime.now()
        self._increment_version()
        
        self._logger.info(
            f"Added charging to session: {energy_delivered_kwh:.1f}kWh delivered, "
            f"charge {initial_charge_percentage:.1f}% → {final_charge_percentage:.1f}%"
        )
    
    def mark_as_overdue(self) -> None:
        """Mark session as overdue (exceeded max stay)"""
        if self.status != ParkingStatus.ACTIVE:
            raise ValueError(f"Cannot mark non-active session as overdue")
        
        self.status = ParkingStatus.OVERDUE
        self.last_updated = datetime.now()
        self._increment_version()
        
        self._logger.warning(f"Marked session for {self.license_plate} as overdue")
    
    # ========================================================================
    # QUERY METHODS
    # ========================================================================
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Get session duration if completed"""
        if not self.exit_time:
            return None
        return self.exit_time - self.entry_time
    
    @property
    def duration_minutes(self) -> Optional[float]:
        """Get duration in minutes"""
        duration = self.duration
        if not duration:
            return None
        return duration.total_seconds() / 60
    
    @property
    def duration_hours(self) -> Optional[float]:
        """Get duration in hours"""
        duration = self.duration
        if not duration:
            return None
        return duration.total_seconds() / 3600
    
    def get_current_duration(self) -> timedelta:
        """Get current duration if session is still active"""
        if self.status != ParkingStatus.ACTIVE:
            return timedelta(0)
        return datetime.now() - self.entry_time
    
    def get_receipt_details(self) -> Dict[str, Any]:
        """Get receipt details for the session"""
        if not self.total_fee:
            raise ValueError("Session not completed, no receipt available")
        
        receipt = {
            "session_id": self.id,
            "license_plate": self.license_plate,
            "vehicle_type": self.vehicle_type.value,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "duration_hours": self.duration_hours,
            "parking_fee": self.parking_fee.to_dict() if self.parking_fee else None,
            "is_paid": self.is_paid,
            "payment_method": self.payment_method,
            "payment_time": self.payment_time.isoformat() if self.payment_time else None,
        }
        
        if self.is_ev:
            receipt["ev_charging"] = {
                "charging_session_id": self.charging_session_id,
                "initial_charge_percentage": self.initial_charge_percentage,
                "final_charge_percentage": self.final_charge_percentage,
                "energy_delivered_kwh": self.energy_delivered_kwh,
                "charging_fee": self.charging_fee.to_dict() if self.charging_fee else None,
            }
        
        receipt["total_fee"] = self.total_fee.to_dict()
        
        return receipt
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "id": self.id,
            "parking_lot_id": self.parking_lot_id,
            "slot_id": self.slot_id,
            "vehicle_id": self.vehicle_id,
            "license_plate": self.license_plate,
            "vehicle_type": self.vehicle_type.value,
            "is_ev": self.is_ev,
            "entry_time": self.entry_time.isoformat(),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "duration_hours": self.duration_hours,
            "status": self.status.value,
            "parking_fee": self.parking_fee.to_dict() if self.parking_fee else None,
            "charging_fee": self.charging_fee.to_dict() if self.charging_fee else None,
            "total_fee": self.total_fee.to_dict() if self.total_fee else None,
            "is_paid": self.is_paid,
            "payment_method": self.payment_method,
            "payment_time": self.payment_time.isoformat() if self.payment_time else None,
            "charging_session_id": self.charging_session_id,
            "energy_delivered_kwh": self.energy_delivered_kwh,
            "initial_charge_percentage": self.initial_charge_percentage,
            "final_charge_percentage": self.final_charge_percentage,
            "creation_date": self.creation_date.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "version": self.version,
        }
    
    def __str__(self) -> str:
        status_icons = {
            ParkingStatus.ACTIVE: "🟢",
            ParkingStatus.COMPLETED: "✅",
            ParkingStatus.OVERDUE: "⚠️",
            ParkingStatus.RESERVED: "📅",
            ParkingStatus.MAINTENANCE: "🔧",
        }
        
        icon = status_icons.get(self.status, "❓")
        duration = self.duration_hours or self.get_current_duration().total_seconds() / 3600
        
        return (
            f"{icon} ParkingSession: {self.license_plate} "
            f"({duration:.1f}h) - {self.status.value}"
        )


# ============================================================================
# AGGREGATE FACTORY
# ============================================================================

class AggregateFactory:
    """Factory for creating aggregates with proper initialization"""
    
    @staticmethod
    def create_parking_lot(
        name: str,
        address: str,
        city: str,
        state: str,
        zip_code: str,
        regular_slots: int,
        ev_slots: int = 0,
        disabled_slots: int = 0,
        premium_slots: int = 0,
        policies: Optional[ParkingPolicies] = None
    ) -> ParkingLot:
        """Create a new parking lot with given configuration"""
        location = Location(
            address=address,
            city=city,
            state=state,
            zip_code=zip_code
        )
        
        capacity = Capacity(
            regular=regular_slots,
            ev=ev_slots,
            disabled=disabled_slots,
            premium=premium_slots
        )
        
        return ParkingLot(
            name=name,
            location=location,
            capacity=capacity,
            policies=policies
        )
    
    @staticmethod
    def create_charging_station(
        name: str,
        address: str,
        city: str,
        state: str,
        zip_code: str,
        max_power_kw: float,
        parking_lot_id: Optional[str] = None,
        connector_configs: Optional[List[Tuple[ChargerType, float]]] = None
    ) -> ChargingStation:
        """Create a new charging station with optional connectors"""
        location = Location(
            address=address,
            city=city,
            state=state,
            zip_code=zip_code
        )
        
        station = ChargingStation(
            name=name,
            location=location,
            max_total_power_kw=max_power_kw,
            parking_lot_id=parking_lot_id
        )
        
        # Add configured connectors
        if connector_configs:
            for connector_type, max_power in connector_configs:
                station.add_connector(connector_type, max_power)
        
        return station


# ============================================================================
# TESTING
# ============================================================================

def test_aggregates():
    """Test function to demonstrate aggregate functionality"""
    import sys
    
    # Simple logging for test
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    print("🧪 Testing Aggregates...")
    print("=" * 60)
    
    try:
        # Test ParkingLot
        print("\n1. Testing ParkingLot Aggregate:")
        print("-" * 40)
        
        location = Location(
            address="123 Main St",
            city="Tech City",
            state="CA",
            zip_code="12345"
        )
        
        capacity = Capacity(regular=10, ev=3, disabled=2, premium=1)
        
        parking_lot = ParkingLot(
            name="Downtown Parking",
            location=location,
            capacity=capacity
        )
        
        print(f"✅ Created ParkingLot: {parking_lot.name}")
        print(f"   Total slots: {parking_lot.total_slots}")
        print(f"   Capacity: {capacity}")
        
        # Test status report
        status = parking_lot.get_status_report()
        print(f"✅ Status report generated")
        print(f"   Occupancy rate: {status['occupancy']['occupancy_rate']:.1f}%")
        
        # Test ChargingStation
        print("\n2. Testing ChargingStation Aggregate:")
        print("-" * 40)
        
        charging_station = ChargingStation(
            name="EV Charging Hub",
            location=location,
            max_total_power_kw=100.0,
            parking_lot_id=parking_lot.id
        )
        
        # Add connectors
        charging_station.add_connector(ChargerType.LEVEL_2, 7.2)
        charging_station.add_connector(ChargerType.DC_FAST, 50.0)
        charging_station.add_connector(ChargerType.TESLA, 150.0)
        
        print(f"✅ Created ChargingStation: {charging_station.name}")
        print(f"   Total connectors: {charging_station.total_connectors}")
        print(f"   Max power: {charging_station.max_total_power_kw}kW")
        
        # Test ParkingSession
        print("\n3. Testing ParkingSession Aggregate:")
        print("-" * 40)
        
        session = ParkingSession(
            parking_lot_id=parking_lot.id,
            slot_id="test-slot-123",
            vehicle_id="test-vehicle-456",
            license_plate="TEST-001",
            vehicle_type=VehicleType.EV_CAR
        )
        
        print(f"✅ Created ParkingSession: {session.license_plate}")
        print(f"   Status: {session.status.value}")
        print(f"   Is EV: {session.is_ev}")
        
        # Test domain events
        print("\n4. Testing Domain Events:")
        print("-" * 40)
        
        events = parking_lot.clear_events()
        print(f"✅ ParkingLot events: {len(events)} events")
        
        events = charging_station.clear_events()
        print(f"✅ ChargingStation events: {len(events)} events")
        
        print("\n✅ All aggregate tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)


if __name__ == "__main__":
    # Run tests if module is executed directly
    test_aggregates()