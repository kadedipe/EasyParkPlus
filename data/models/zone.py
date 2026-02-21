# parking-management/data/migrations/models/zone.py

"""
Zone model for parking management system.

This module defines the Zone model and related classes for managing
parking zones, areas, levels, and their associated rules, capacities,
and operational characteristics.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Time,
    Text, ForeignKey, UniqueConstraint, Index, CheckConstraint,
    Numeric, JSON, Table, func, text, event, and_, or_
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, backref, validates, object_session
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declarative_base
import uuid
import enum
import math
from datetime import datetime, date, timedelta
import logging
from typing import Optional, List, Dict, Any, Tuple
import json

# Configure logging
logger = logging.getLogger(__name__)

# Create base class
Base = declarative_base()


class ZoneType(str, enum.Enum):
    """Enum for zone types."""
    INDOOR = 'indoor'
    OUTDOOR = 'outdoor'
    COVERED = 'covered'
    ROOFTOP = 'rooftop'
    UNDERGROUND = 'underground'
    MULTI_LEVEL = 'multi_level'
    SURFACE = 'surface'
    STRUCTURE = 'structure'
    VALET = 'valet'
    RESERVED = 'reserved'


class ZoneStatus(str, enum.Enum):
    """Enum for zone status."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    MAINTENANCE = 'maintenance'
    FULL = 'full'
    CLOSED = 'closed'
    UNDER_CONSTRUCTION = 'under_construction'


class AccessType(str, enum.Enum):
    """Enum for access types."""
    GATE = 'gate'
    BARRIER = 'barrier'
    RFID = 'rfid'
    LICENSE_PLATE = 'license_plate'
    TICKET = 'ticket'
    VALET = 'valet'
    RESERVATION = 'reservation'
    MEMBERSHIP = 'membership'


class EntryType(str, enum.Enum):
    """Enum for entry/exit types."""
    ENTRY = 'entry'
    EXIT = 'exit'
    BOTH = 'both'


class RestrictionType(str, enum.Enum):
    """Enum for restriction types."""
    HEIGHT = 'height'
    WIDTH = 'width'
    LENGTH = 'length'
    WEIGHT = 'weight'
    VEHICLE_TYPE = 'vehicle_type'
    HAZMAT = 'hazmat'
    ELECTRIC = 'electric'
    HANDICAP = 'handicap'
    VIP = 'vip'
    STAFF = 'staff'
    RESIDENT = 'resident'
    COMMERCIAL = 'commercial'


class OperatingDay(str, enum.Enum):
    """Enum for operating days."""
    MONDAY = 'monday'
    TUESDAY = 'tuesday'
    WEDNESDAY = 'wednesday'
    THURSDAY = 'thursday'
    FRIDAY = 'friday'
    SATURDAY = 'saturday'
    SUNDAY = 'sunday'
    HOLIDAY = 'holiday'
    SPECIAL = 'special'


class ZoneFeature(str, enum.Enum):
    """Enum for zone features."""
    EV_CHARGING = 'ev_charging'
    CAR_WASH = 'car_wash'
    SECURITY = 'security'
    COVERED = 'covered'
    HEATED = 'heated'
    LIGHTING = 'lighting'
    CCTV = 'cctv'
    VALET = 'valet'
    SHUTTLE = 'shuttle'
    BIKE_RACK = 'bike_rack'
    LUGGAGE_STORAGE = 'luggage_storage'
    RESTROOM = 'restroom'
    WAITING_AREA = 'waiting_area'


class ZoneLevel(Base):
    """
    Levels within a multi-level parking zone.
    
    Represents individual floors or levels within a parking structure.
    """
    
    __tablename__ = 'zone_levels'
    __table_args__ = (
        UniqueConstraint('zone_id', 'level_number', name='uq_zone_level_number'),
        UniqueConstraint('zone_id', 'level_code', name='uq_zone_level_code'),
        Index('ix_zone_levels_zone', 'zone_id'),
        Index('ix_zone_levels_level', 'level_number'),
        Index('ix_zone_levels_active', 'is_active'),
        
        # Table comment
        {'comment': 'Levels within multi-level parking zones'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('zones.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of parent zone'
    )
    
    # =========================================================================
    # LEVEL IDENTIFICATION
    # =========================================================================
    level_number = Column(
        Integer,
        nullable=False,
        comment='Level number (negative for basement levels)'
    )
    
    level_code = Column(
        String(20),
        nullable=False,
        comment='Level code (e.g., "B1", "L1", "L2", "R")'
    )
    
    name = Column(
        String(100),
        comment='Level name (e.g., "Basement 1", "First Floor", "Roof")'
    )
    
    description = Column(
        Text,
        comment='Level description'
    )
    
    # =========================================================================
    # LOCATION
    # =========================================================================
    elevation_meters = Column(
        Float,
        comment='Elevation in meters (relative to ground)'
    )
    
    floor_area_sqm = Column(
        Float,
        comment='Floor area in square meters'
    )
    
    ceiling_height_cm = Column(
        Integer,
        comment='Ceiling height in centimeters'
    )
    
    # =========================================================================
    # CAPACITY
    # =========================================================================
    total_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Total number of spots on this level'
    )
    
    available_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Currently available spots'
    )
    
    occupied_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Currently occupied spots'
    )
    
    reserved_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Currently reserved spots'
    )
    
    # =========================================================================
    # ACCESS
    # =========================================================================
    has_elevator = Column(
        Boolean,
        server_default='false',
        comment='Whether level has elevator access'
    )
    
    has_escalator = Column(
        Boolean,
        server_default='false',
        comment='Whether level has escalator access'
    )
    
    has_stairs = Column(
        Boolean,
        server_default='true',
        comment='Whether level has stair access'
    )
    
    has_ramp = Column(
        Boolean,
        server_default='false',
        comment='Whether level has ramp access'
    )
    
    # =========================================================================
    # FEATURES
    # =========================================================================
    has_ev_charging = Column(
        Boolean,
        server_default='false',
        comment='Whether level has EV charging'
    )
    
    has_covered_parking = Column(
        Boolean,
        server_default='true',
        comment='Whether parking is covered'
    )
    
    has_heated = Column(
        Boolean,
        server_default='false',
        comment='Whether level is heated'
    )
    
    has_security = Column(
        Boolean,
        server_default='false',
        comment='Whether level has security'
    )
    
    # =========================================================================
    # RESTRICTIONS
    # =========================================================================
    max_height_cm = Column(
        Integer,
        comment='Maximum vehicle height allowed (cm)'
    )
    
    max_weight_kg = Column(
        Integer,
        comment='Maximum vehicle weight allowed (kg)'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether level is active'
    )
    
    is_full = Column(
        Boolean,
        server_default='false',
        comment='Whether level is currently full'
    )
    
    status = Column(
        String(20),
        server_default='active',
        comment='Current level status'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    zone = relationship('Zone', back_populates='levels')
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def utilization_rate(self) -> float:
        """Calculate current utilization rate."""
        if self.total_spots == 0:
            return 0.0
        return (self.occupied_spots / self.total_spots) * 100
    
    @hybrid_property
    def display_name(self) -> str:
        """Get display name for level."""
        if self.name:
            return self.name
        return f"Level {self.level_code}"
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def update_counts(self) -> Dict[str, int]:
        """Update spot counts for this level."""
        from models.parking_spot import ParkingSpot
        
        counts = object_session(self).query(
            func.count(ParkingSpot.id).label('total'),
            func.sum(case([(ParkingSpot.status == 'available', 1)], else_=0)).label('available'),
            func.sum(case([(ParkingSpot.status == 'occupied', 1)], else_=0)).label('occupied'),
            func.sum(case([(ParkingSpot.status == 'reserved', 1)], else_=0)).label('reserved')
        ).filter(
            ParkingSpot.level_id == self.id,
            ParkingSpot.is_active == True
        ).first()
        
        if counts:
            self.total_spots = counts.total or 0
            self.available_spots = counts.available or 0
            self.occupied_spots = counts.occupied or 0
            self.reserved_spots = counts.reserved or 0
            self.is_full = self.available_spots == 0 and self.total_spots > 0
        
        return {
            'total': self.total_spots,
            'available': self.available_spots,
            'occupied': self.occupied_spots,
            'reserved': self.reserved_spots
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert level to dictionary."""
        return {
            'id': str(self.id),
            'zone_id': str(self.zone_id),
            'level_number': self.level_number,
            'level_code': self.level_code,
            'name': self.name,
            'description': self.description,
            'elevation_meters': self.elevation_meters,
            'floor_area_sqm': self.floor_area_sqm,
            'ceiling_height_cm': self.ceiling_height_cm,
            'capacity': {
                'total': self.total_spots,
                'available': self.available_spots,
                'occupied': self.occupied_spots,
                'reserved': self.reserved_spots,
                'utilization_rate': round(self.utilization_rate, 2)
            },
            'access': {
                'has_elevator': self.has_elevator,
                'has_escalator': self.has_escalator,
                'has_stairs': self.has_stairs,
                'has_ramp': self.has_ramp
            },
            'features': {
                'has_ev_charging': self.has_ev_charging,
                'has_covered_parking': self.has_covered_parking,
                'has_heated': self.has_heated,
                'has_security': self.has_security
            },
            'restrictions': {
                'max_height_cm': self.max_height_cm,
                'max_weight_kg': self.max_weight_kg
            },
            'is_active': self.is_active,
            'is_full': self.is_full,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ZoneLevel(id={self.id}, code={self.level_code})>"


class ZoneGate(Base):
    """
    Entry/exit gates for parking zones.
    
    Represents physical gates controlling access to zones.
    """
    
    __tablename__ = 'zone_gates'
    __table_args__ = (
        Index('ix_zone_gates_code', 'code', unique=True),
        Index('ix_zone_gates_zone', 'zone_id'),
        Index('ix_zone_gates_type', 'gate_type'),
        Index('ix_zone_gates_active', 'is_active'),
        
        # Table comment
        {'comment': 'Entry/exit gates for parking zones'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('zones.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of associated zone'
    )
    
    # =========================================================================
    # GATE IDENTIFICATION
    # =========================================================================
    code = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Unique gate code (e.g., "ENT-A", "EXIT-1")'
    )
    
    name = Column(
        String(100),
        nullable=False,
        comment='Gate name'
    )
    
    description = Column(
        Text,
        comment='Gate description'
    )
    
    # =========================================================================
    # GATE TYPE
    # =========================================================================
    gate_type = Column(
        String(20),
        nullable=False,
        comment='Type of gate (entry, exit, both)'
    )
    
    access_type = Column(
        String(20),
        nullable=False,
        server_default='gate',
        comment='Access control type'
    )
    
    # =========================================================================
    # LOCATION
    # =========================================================================
    latitude = Column(
        Numeric(10, 8),
        comment='Latitude coordinate'
    )
    
    longitude = Column(
        Numeric(11, 8),
        comment='Longitude coordinate'
    )
    
    address = Column(
        String(255),
        comment='Physical address of gate'
    )
    
    # =========================================================================
    # HARDWARE
    # =========================================================================
    controller_id = Column(
        String(100),
        comment='Hardware controller ID'
    )
    
    ip_address = Column(
        String(45),
        comment='IP address of gate controller'
    )
    
    mac_address = Column(
        String(17),
        comment='MAC address'
    )
    
    firmware_version = Column(
        String(50),
        comment='Firmware version'
    )
    
    # =========================================================================
    # OPERATIONAL
    # =========================================================================
    opening_time = Column(
        Time,
        comment='Opening time (if not 24/7)'
    )
    
    closing_time = Column(
        Time,
        comment='Closing time (if not 24/7)'
    )
    
    is_24_hours = Column(
        Boolean,
        server_default='true',
        comment='Whether gate is 24/7'
    )
    
    average_opening_time_ms = Column(
        Integer,
        comment='Average time to open in milliseconds'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether gate is active'
    )
    
    is_online = Column(
        Boolean,
        server_default='true',
        comment='Whether gate is online'
    )
    
    status = Column(
        String(20),
        server_default='operational',
        comment='Current gate status'
    )
    
    last_communication = Column(
        DateTime(timezone=True),
        comment='Last communication timestamp'
    )
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    total_entries = Column(
        Integer,
        server_default='0',
        comment='Total entries through this gate'
    )
    
    total_exits = Column(
        Integer,
        server_default='0',
        comment='Total exits through this gate'
    )
    
    peak_hourly_rate = Column(
        Integer,
        comment='Peak vehicles per hour'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    zone = relationship('Zone', back_populates='gates')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def record_entry(self) -> None:
        """Record a vehicle entry through this gate."""
        self.total_entries += 1
    
    def record_exit(self) -> None:
        """Record a vehicle exit through this gate."""
        self.total_exits += 1
    
    def is_open_now(self) -> bool:
        """Check if gate is currently open."""
        if not self.is_active or not self.is_online:
            return False
        
        if self.is_24_hours:
            return True
        
        now = datetime.now().time()
        if self.opening_time and self.closing_time:
            if self.opening_time <= self.closing_time:
                return self.opening_time <= now <= self.closing_time
            else:
                return now >= self.opening_time or now <= self.closing_time
        
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert gate to dictionary."""
        return {
            'id': str(self.id),
            'zone_id': str(self.zone_id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'gate_type': self.gate_type,
            'access_type': self.access_type,
            'location': {
                'latitude': float(self.latitude) if self.latitude else None,
                'longitude': float(self.longitude) if self.longitude else None,
                'address': self.address
            },
            'hardware': {
                'controller_id': self.controller_id,
                'ip_address': self.ip_address,
                'mac_address': self.mac_address,
                'firmware_version': self.firmware_version
            },
            'operational': {
                'opening_time': self.opening_time.isoformat() if self.opening_time else None,
                'closing_time': self.closing_time.isoformat() if self.closing_time else None,
                'is_24_hours': self.is_24_hours,
                'is_open_now': self.is_open_now(),
                'average_opening_time_ms': self.average_opening_time_ms
            },
            'status': {
                'is_active': self.is_active,
                'is_online': self.is_online,
                'status': self.status,
                'last_communication': self.last_communication.isoformat() if self.last_communication else None
            },
            'statistics': {
                'total_entries': self.total_entries,
                'total_exits': self.total_exits,
                'peak_hourly_rate': self.peak_hourly_rate
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ZoneGate(id={self.id}, code={self.code}, type={self.gate_type})>"


class ZoneRestriction(Base):
    """
    Restrictions for parking zones.
    
    Defines vehicle restrictions for zones (height, weight, type, etc.).
    """
    
    __tablename__ = 'zone_restrictions'
    __table_args__ = (
        Index('ix_zone_restrictions_zone', 'zone_id'),
        Index('ix_zone_restrictions_type', 'restriction_type'),
        
        # Table comment
        {'comment': 'Vehicle restrictions for parking zones'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('zones.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of associated zone'
    )
    
    # =========================================================================
    # RESTRICTION DETAILS
    # =========================================================================
    restriction_type = Column(
        String(20),
        nullable=False,
        comment='Type of restriction'
    )
    
    operator = Column(
        String(10),
        nullable=False,
        server_default='<=',
        comment='Comparison operator (<, <=, =, >=, >, in, not_in)'
    )
    
    value = Column(
        String(255),
        nullable=False,
        comment='Restriction value'
    )
    
    unit = Column(
        String(20),
        comment='Unit of measurement (cm, kg, etc.)'
    )
    
    description = Column(
        Text,
        comment='Restriction description'
    )
    
    # =========================================================================
    # APPLICABILITY
    # =========================================================================
    applies_to_all = Column(
        Boolean,
        server_default='true',
        comment='Whether restriction applies to all vehicles'
    )
    
    vehicle_types = Column(
        ARRAY(String(20)),
        comment='Specific vehicle types this applies to'
    )
    
    time_of_day_start = Column(
        Time,
        comment='Time-based restriction start'
    )
    
    time_of_day_end = Column(
        Time,
        comment='Time-based restriction end'
    )
    
    days_of_week = Column(
        ARRAY(String(10)),
        comment='Days this restriction applies'
    )
    
    # =========================================================================
    # ENFORCEMENT
    # =========================================================================
    is_enforced = Column(
        Boolean,
        server_default='true',
        comment='Whether restriction is enforced'
    )
    
    enforcement_method = Column(
        String(50),
        comment='How restriction is enforced'
    )
    
    penalty_amount = Column(
        Numeric(10, 2),
        comment='Penalty for violation'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether restriction is active'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    zone = relationship('Zone', back_populates='restrictions')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def check_compliance(self, vehicle: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Check if a vehicle complies with this restriction.
        
        Args:
            vehicle: Vehicle attributes dictionary
            
        Returns:
            Tuple of (is_compliant, message)
        """
        # Check if restriction applies to this vehicle type
        if not self.applies_to_all and self.vehicle_types:
            if vehicle.get('vehicle_type') not in self.vehicle_types:
                return True, None
        
        # Check time-based applicability
        if self.time_of_day_start and self.time_of_day_end:
            now = datetime.now().time()
            if self.time_of_day_start <= self.time_of_day_end:
                if not (self.time_of_day_start <= now <= self.time_of_day_end):
                    return True, None
            else:
                if not (now >= self.time_of_day_start or now <= self.time_of_day_end):
                    return True, None
        
        # Check day of week
        if self.days_of_week:
            today = datetime.now().strftime('%A').lower()
            if today not in self.days_of_week:
                return True, None
        
        # Get vehicle attribute based on restriction type
        attr_map = {
            'height': 'height_cm',
            'width': 'width_cm',
            'length': 'length_cm',
            'weight': 'weight_kg',
            'vehicle_type': 'vehicle_type',
        }
        
        vehicle_attr = attr_map.get(self.restriction_type)
        if not vehicle_attr or vehicle_attr not in vehicle:
            return True, None
        
        vehicle_value = vehicle[vehicle_attr]
        
        # Parse restriction value
        try:
            if self.restriction_type in ['height', 'width', 'length', 'weight']:
                restriction_value = float(self.value)
                vehicle_value = float(vehicle_value)
                
                if self.operator == '<':
                    is_compliant = vehicle_value < restriction_value
                elif self.operator == '<=':
                    is_compliant = vehicle_value <= restriction_value
                elif self.operator == '=':
                    is_compliant = vehicle_value == restriction_value
                elif self.operator == '>=':
                    is_compliant = vehicle_value >= restriction_value
                elif self.operator == '>':
                    is_compliant = vehicle_value > restriction_value
                else:
                    is_compliant = True
                
                if not is_compliant:
                    return False, f"Vehicle {self.restriction_type} {vehicle_value}{self.unit or ''} exceeds limit of {restriction_value}{self.unit or ''}"
            
            elif self.restriction_type == 'vehicle_type':
                restriction_values = [v.strip() for v in self.value.split(',')]
                if self.operator == 'in':
                    is_compliant = vehicle_value in restriction_values
                elif self.operator == 'not_in':
                    is_compliant = vehicle_value not in restriction_values
                else:
                    is_compliant = True
                
                if not is_compliant:
                    return False, f"Vehicle type '{vehicle_value}' not allowed in this zone"
            
        except (ValueError, TypeError):
            return True, None
        
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert restriction to dictionary."""
        return {
            'id': str(self.id),
            'zone_id': str(self.zone_id),
            'restriction_type': self.restriction_type,
            'operator': self.operator,
            'value': self.value,
            'unit': self.unit,
            'description': self.description,
            'applies_to_all': self.applies_to_all,
            'vehicle_types': self.vehicle_types,
            'time_of_day': {
                'start': self.time_of_day_start.isoformat() if self.time_of_day_start else None,
                'end': self.time_of_day_end.isoformat() if self.time_of_day_end else None
            },
            'days_of_week': self.days_of_week,
            'is_enforced': self.is_enforced,
            'penalty_amount': float(self.penalty_amount) if self.penalty_amount else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ZoneRestriction(id={self.id}, type={self.restriction_type})>"


class ZoneOperatingHours(Base):
    """
    Operating hours for parking zones.
    
    Defines when zones are open, including regular hours, holidays, and special events.
    """
    
    __tablename__ = 'zone_operating_hours'
    __table_args__ = (
        Index('ix_zone_hours_zone', 'zone_id'),
        Index('ix_zone_hours_day', 'day_of_week'),
        
        # Table comment
        {'comment': 'Operating hours for parking zones'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('zones.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of associated zone'
    )
    
    # =========================================================================
    # OPERATING SCHEDULE
    # =========================================================================
    day_of_week = Column(
        String(10),
        nullable=False,
        comment='Day of week this schedule applies to'
    )
    
    opening_time = Column(
        Time,
        nullable=False,
        comment='Opening time'
    )
    
    closing_time = Column(
        Time,
        nullable=False,
        comment='Closing time'
    )
    
    is_closed = Column(
        Boolean,
        server_default='false',
        comment='Whether zone is closed on this day'
    )
    
    # =========================================================================
    # SPECIAL DAYS
    # =========================================================================
    is_holiday = Column(
        Boolean,
        server_default='false',
        comment='Whether this is a holiday schedule'
    )
    
    holiday_name = Column(
        String(100),
        comment='Name of holiday'
    )
    
    holiday_date = Column(
        Date,
        comment='Specific date for holiday'
    )
    
    is_recurring_holiday = Column(
        Boolean,
        server_default='false',
        comment='Whether holiday recurs annually'
    )
    
    # =========================================================================
    # SPECIAL EVENT
    # =========================================================================
    is_special_event = Column(
        Boolean,
        server_default='false',
        comment='Whether this is a special event schedule'
    )
    
    event_name = Column(
        String(200),
        comment='Name of special event'
    )
    
    event_start_date = Column(
        Date,
        comment='Event start date'
    )
    
    event_end_date = Column(
        Date,
        comment='Event end date'
    )
    
    # =========================================================================
    # NOTES
    # =========================================================================
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    # =========================================================================
    # VALIDITY
    # =========================================================================
    valid_from = Column(
        Date,
        comment='Date from which this schedule is valid'
    )
    
    valid_to = Column(
        Date,
        comment='Date until which this schedule is valid'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether schedule is active'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    zone = relationship('Zone', back_populates='operating_hours')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def is_applicable_today(self) -> bool:
        """Check if this schedule applies today."""
        today = datetime.now().date()
        today_name = today.strftime('%A').lower()
        
        # Check date range
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_to and today > self.valid_to:
            return False
        
        # Check if regular schedule
        if not self.is_holiday and not self.is_special_event:
            return self.day_of_week == today_name
        
        # Check holiday
        if self.is_holiday and self.holiday_date:
            if self.is_recurring_holiday:
                # Check month and day only
                return (self.holiday_date.month == today.month and 
                       self.holiday_date.day == today.day)
            else:
                return self.holiday_date == today
        
        # Check special event
        if self.is_special_event:
            if self.event_start_date and self.event_end_date:
                return self.event_start_date <= today <= self.event_end_date
        
        return False
    
    def get_hours_for_date(self, date: datetime.date) -> Optional[Dict[str, Any]]:
        """Get operating hours for a specific date."""
        if self.is_applicable_today():
            return {
                'opening_time': self.opening_time,
                'closing_time': self.closing_time,
                'is_closed': self.is_closed
            }
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert operating hours to dictionary."""
        return {
            'id': str(self.id),
            'zone_id': str(self.zone_id),
            'day_of_week': self.day_of_week,
            'opening_time': self.opening_time.isoformat() if self.opening_time else None,
            'closing_time': self.closing_time.isoformat() if self.closing_time else None,
            'is_closed': self.is_closed,
            'is_holiday': self.is_holiday,
            'holiday_name': self.holiday_name,
            'holiday_date': self.holiday_date.isoformat() if self.holiday_date else None,
            'is_recurring_holiday': self.is_recurring_holiday,
            'is_special_event': self.is_special_event,
            'event_name': self.event_name,
            'event_start_date': self.event_start_date.isoformat() if self.event_start_date else None,
            'event_end_date': self.event_end_date.isoformat() if self.event_end_date else None,
            'notes': self.notes,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ZoneOperatingHours(id={self.id}, day={self.day_of_week})>"


class ZoneFeature(Base):
    """
    Features and amenities available in parking zones.
    
    Defines features available in each zone (EV charging, security, etc.).
    """
    
    __tablename__ = 'zone_features'
    __table_args__ = (
        Index('ix_zone_features_zone', 'zone_id'),
        Index('ix_zone_features_feature', 'feature'),
        UniqueConstraint('zone_id', 'feature', name='uq_zone_feature'),
        
        # Table comment
        {'comment': 'Features available in parking zones'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('zones.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of associated zone'
    )
    
    # =========================================================================
    # FEATURE DETAILS
    # =========================================================================
    feature = Column(
        String(50),
        nullable=False,
        comment='Feature name'
    )
    
    display_name = Column(
        String(100),
        comment='Display name for feature'
    )
    
    description = Column(
        Text,
        comment='Feature description'
    )
    
    # =========================================================================
    # QUANTITY/CAPACITY
    # =========================================================================
    quantity = Column(
        Integer,
        comment='Quantity available (e.g., number of EV chargers)'
    )
    
    capacity = Column(
        Integer,
        comment='Total capacity'
    )
    
    available = Column(
        Integer,
        comment='Currently available'
    )
    
    # =========================================================================
    # FEATURE DETAILS
    # =========================================================================
    details = Column(
        JSONB,
        comment='Feature-specific details'
    )
    
    # =========================================================================
    # COST
    # =========================================================================
    is_free = Column(
        Boolean,
        server_default='true',
        comment='Whether feature is free'
    )
    
    price = Column(
        Numeric(10, 2),
        comment='Price if not free'
    )
    
    price_unit = Column(
        String(20),
        comment='Pricing unit (per use, per hour, etc.)'
    )
    
    # =========================================================================
    # AVAILABILITY
    # =========================================================================
    requires_reservation = Column(
        Boolean,
        server_default='false',
        comment='Whether reservation is required'
    )
    
    requires_membership = Column(
        Boolean,
        server_default='false',
        comment='Whether membership is required'
    )
    
    membership_tiers = Column(
        ARRAY(String(50)),
        comment='Allowed membership tiers'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether feature is active'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    zone = relationship('Zone', back_populates='features')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feature to dictionary."""
        return {
            'id': str(self.id),
            'zone_id': str(self.zone_id),
            'feature': self.feature,
            'display_name': self.display_name or self.feature.replace('_', ' ').title(),
            'description': self.description,
            'quantity': self.quantity,
            'capacity': self.capacity,
            'available': self.available,
            'details': self.details,
            'pricing': {
                'is_free': self.is_free,
                'price': float(self.price) if self.price else None,
                'price_unit': self.price_unit
            },
            'availability': {
                'requires_reservation': self.requires_reservation,
                'requires_membership': self.requires_membership,
                'membership_tiers': self.membership_tiers
            },
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ZoneFeature(id={self.id}, feature={self.feature})>"


class ZoneOccupancyHistory(Base):
    """
    Historical occupancy data for zones.
    
    Tracks occupancy levels over time for analytics and forecasting.
    """
    
    __tablename__ = 'zone_occupancy_history'
    __table_args__ = (
        Index('ix_zone_occupancy_zone', 'zone_id'),
        Index('ix_zone_occupancy_time', 'timestamp'),
        Index('ix_zone_occupancy_zone_time', 'zone_id', 'timestamp'),
        
        # Table comment
        {'comment': 'Historical occupancy data for zones'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('zones.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of associated zone'
    )
    
    # =========================================================================
    # TIMESTAMP
    # =========================================================================
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Time of occupancy snapshot'
    )
    
    # =========================================================================
    # OCCUPANCY DATA
    # =========================================================================
    total_spots = Column(
        Integer,
        nullable=False,
        comment='Total spots at this time'
    )
    
    available_spots = Column(
        Integer,
        nullable=False,
        comment='Available spots at this time'
    )
    
    occupied_spots = Column(
        Integer,
        nullable=False,
        comment='Occupied spots at this time'
    )
    
    reserved_spots = Column(
        Integer,
        nullable=False,
        comment='Reserved spots at this time'
    )
    
    # =========================================================================
    # RATES
    # =========================================================================
    occupancy_rate = Column(
        Float,
        comment='Occupancy rate percentage'
    )
    
    utilization_rate = Column(
        Float,
        comment='Utilization rate percentage'
    )
    
    # =========================================================================
    # VEHICLE BREAKDOWN
    # =========================================================================
    vehicle_breakdown = Column(
        JSONB,
        comment='Breakdown by vehicle type'
    )
    
    # =========================================================================
    # REVENUE
    # =========================================================================
    revenue_generated = Column(
        Numeric(10, 2),
        comment='Revenue generated in this period'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    zone = relationship('Zone', back_populates='occupancy_history')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    @staticmethod
    def record_snapshot(session, zone_id: uuid.UUID) -> 'ZoneOccupancyHistory':
        """Record current occupancy snapshot for a zone."""
        from models.parking_spot import ParkingSpot
        
        zone = session.get(Zone, zone_id)
        if not zone:
            raise ValueError(f"Zone {zone_id} not found")
        
        # Get current counts
        counts = session.query(
            func.count(ParkingSpot.id).label('total'),
            func.sum(case([(ParkingSpot.status == 'available', 1)], else_=0)).label('available'),
            func.sum(case([(ParkingSpot.status == 'occupied', 1)], else_=0)).label('occupied'),
            func.sum(case([(ParkingSpot.status == 'reserved', 1)], else_=0)).label('reserved')
        ).filter(
            ParkingSpot.zone_id == zone_id,
            ParkingSpot.is_active == True
        ).first()
        
        total = counts.total or 0
        available = counts.available or 0
        occupied = counts.occupied or 0
        reserved = counts.reserved or 0
        
        # Get vehicle breakdown
        vehicle_counts = session.query(
            ParkingSpot.vehicle_type,
            func.count().label('count')
        ).filter(
            ParkingSpot.zone_id == zone_id,
            ParkingSpot.status == 'occupied',
            ParkingSpot.is_active == True
        ).group_by(ParkingSpot.vehicle_type).all()
        
        vehicle_breakdown = {vtype: count for vtype, count in vehicle_counts}
        
        snapshot = ZoneOccupancyHistory(
            zone_id=zone_id,
            timestamp=datetime.now(),
            total_spots=total,
            available_spots=available,
            occupied_spots=occupied,
            reserved_spots=reserved,
            occupancy_rate=(occupied / total * 100) if total > 0 else 0,
            utilization_rate=((occupied + reserved) / total * 100) if total > 0 else 0,
            vehicle_breakdown=vehicle_breakdown
        )
        
        session.add(snapshot)
        return snapshot
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert occupancy history to dictionary."""
        return {
            'id': str(self.id),
            'zone_id': str(self.zone_id),
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'spots': {
                'total': self.total_spots,
                'available': self.available_spots,
                'occupied': self.occupied_spots,
                'reserved': self.reserved_spots
            },
            'rates': {
                'occupancy': round(self.occupancy_rate, 2) if self.occupancy_rate else None,
                'utilization': round(self.utilization_rate, 2) if self.utilization_rate else None
            },
            'vehicle_breakdown': self.vehicle_breakdown,
            'revenue': float(self.revenue_generated) if self.revenue_generated else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ZoneOccupancyHistory(id={self.id}, zone={self.zone_id}, time={self.timestamp})>"


class ZoneMaintenance(Base):
    """
    Maintenance schedule for zones.
    
    Tracks maintenance activities, cleaning schedules, and repairs for zones.
    """
    
    __tablename__ = 'zone_maintenance'
    __table_args__ = (
        Index('ix_zone_maintenance_zone', 'zone_id'),
        Index('ix_zone_maintenance_date', 'scheduled_date'),
        Index('ix_zone_maintenance_status', 'status'),
        
        # Table comment
        {'comment': 'Maintenance schedule for zones'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('zones.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of associated zone'
    )
    
    # =========================================================================
    # MAINTENANCE DETAILS
    # =========================================================================
    maintenance_type = Column(
        String(50),
        nullable=False,
        comment='Type of maintenance'
    )
    
    title = Column(
        String(200),
        nullable=False,
        comment='Maintenance title'
    )
    
    description = Column(
        Text,
        comment='Detailed description'
    )
    
    priority = Column(
        String(20),
        server_default='medium',
        comment='Priority level'
    )
    
    # =========================================================================
    # SCHEDULE
    # =========================================================================
    scheduled_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Scheduled date/time'
    )
    
    scheduled_end_date = Column(
        DateTime(timezone=True),
        comment='Scheduled end date/time'
    )
    
    actual_start_date = Column(
        DateTime(timezone=True),
        comment='Actual start date/time'
    )
    
    actual_end_date = Column(
        DateTime(timezone=True),
        comment='Actual end date/time'
    )
    
    # =========================================================================
    # DURATION
    # =========================================================================
    estimated_duration_minutes = Column(
        Integer,
        comment='Estimated duration in minutes'
    )
    
    actual_duration_minutes = Column(
        Integer,
        comment='Actual duration in minutes'
    )
    
    # =========================================================================
    # IMPACT
    # =========================================================================
    affects_availability = Column(
        Boolean,
        server_default='true',
        comment='Whether maintenance affects spot availability'
    )
    
    affected_spots = Column(
        ARRAY(UUID(as_uuid=True)),
        comment='Specific spots affected'
    )
    
    closure_percentage = Column(
        Integer,
        comment='Percentage of zone closed'
    )
    
    # =========================================================================
    # ASSIGNMENT
    # =========================================================================
    assigned_to = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='Staff assigned to maintenance'
    )
    
    assigned_team = Column(
        String(100),
        comment='Team assigned'
    )
    
    vendor_name = Column(
        String(200),
        comment='External vendor name'
    )
    
    vendor_contact = Column(
        String(100),
        comment='Vendor contact information'
    )
    
    # =========================================================================
    # COSTS
    # =========================================================================
    estimated_cost = Column(
        Numeric(10, 2),
        comment='Estimated cost'
    )
    
    actual_cost = Column(
        Numeric(10, 2),
        comment='Actual cost'
    )
    
    cost_breakdown = Column(
        JSONB,
        comment='Cost breakdown'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    status = Column(
        String(20),
        server_default='scheduled',
        comment='Maintenance status'
    )
    
    completion_notes = Column(
        Text,
        comment='Notes upon completion'
    )
    
    follow_up_required = Column(
        Boolean,
        server_default='false',
        comment='Whether follow-up is required'
    )
    
    follow_up_date = Column(
        DateTime(timezone=True),
        comment='Follow-up date'
    )
    
    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================
    notifications_sent = Column(
        Boolean,
        server_default='false',
        comment='Whether notifications were sent'
    )
    
    notified_users = Column(
        ARRAY(UUID(as_uuid=True)),
        comment='Users notified'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created this record'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    zone = relationship('Zone', back_populates='maintenance')
    assignee = relationship('User', foreign_keys=[assigned_to])
    creator = relationship('User', foreign_keys=[created_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def start(self) -> None:
        """Start maintenance."""
        self.status = 'in_progress'
        self.actual_start_date = datetime.now()
    
    def complete(self, notes: Optional[str] = None) -> None:
        """Complete maintenance."""
        self.status = 'completed'
        self.actual_end_date = datetime.now()
        self.completion_notes = notes
        
        if self.actual_start_date:
            delta = self.actual_end_date - self.actual_start_date
            self.actual_duration_minutes = int(delta.total_seconds() / 60)
    
    def cancel(self, reason: str) -> None:
        """Cancel maintenance."""
        self.status = 'cancelled'
        self.completion_notes = f"Cancelled: {reason}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert maintenance to dictionary."""
        return {
            'id': str(self.id),
            'zone_id': str(self.zone_id),
            'maintenance_type': self.maintenance_type,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'schedule': {
                'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
                'scheduled_end_date': self.scheduled_end_date.isoformat() if self.scheduled_end_date else None,
                'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
                'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
                'estimated_duration_minutes': self.estimated_duration_minutes,
                'actual_duration_minutes': self.actual_duration_minutes
            },
            'impact': {
                'affects_availability': self.affects_availability,
                'affected_spots': [str(s) for s in self.affected_spots] if self.affected_spots else [],
                'closure_percentage': self.closure_percentage
            },
            'assignment': {
                'assigned_to': str(self.assigned_to) if self.assigned_to else None,
                'assigned_team': self.assigned_team,
                'vendor_name': self.vendor_name
            },
            'costs': {
                'estimated_cost': float(self.estimated_cost) if self.estimated_cost else None,
                'actual_cost': float(self.actual_cost) if self.actual_cost else None,
                'cost_breakdown': self.cost_breakdown
            },
            'status': self.status,
            'completion_notes': self.completion_notes,
            'follow_up_required': self.follow_up_required,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ZoneMaintenance(id={self.id}, type={self.maintenance_type})>"


class Zone(Base):
    """
    Main zone model for parking management.
    
    Represents a parking zone or area with its characteristics,
    capacity, operating hours, and associated resources.
    """
    
    __tablename__ = 'zones'
    __table_args__ = (
        # Primary indexes
        Index('ix_zones_code', 'code', unique=True),
        Index('ix_zones_name', 'name'),
        
        # Location indexes
        Index('ix_zones_location', 'latitude', 'longitude'),
        
        # Status indexes
        Index('ix_zones_type', 'zone_type'),
        Index('ix_zones_status', 'status'),
        Index('ix_zones_is_active', 'is_active'),
        
        # Composite indexes
        Index('ix_zones_type_active', 'zone_type', 'is_active'),
        
        # Partial indexes
        Index('ix_zones_24_hours', 'is_24_hours', postgresql_where=text("is_24_hours = true")),
        
        # Check constraints
        CheckConstraint(
            "zone_type IN ('indoor', 'outdoor', 'covered', 'rooftop', 'underground', "
            "'multi_level', 'surface', 'structure', 'valet', 'reserved')",
            name='ck_zones_type'
        ),
        CheckConstraint(
            "status IN ('active', 'inactive', 'maintenance', 'full', 'closed', 'under_construction')",
            name='ck_zones_status'
        ),
        CheckConstraint(
            "total_spots >= 0",
            name='ck_zones_total_spots_positive'
        ),
        CheckConstraint(
            "available_spots >= 0 AND available_spots <= total_spots",
            name='ck_zones_available_spots'
        ),
        
        # Table comment
        {'comment': 'Main parking zone model'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    # =========================================================================
    # ZONE IDENTIFICATION
    # =========================================================================
    code = Column(
        String(20),
        nullable=False,
        unique=True,
        comment='Unique zone code (e.g., "ZONE-A", "NORTH-1")'
    )
    
    name = Column(
        String(100),
        nullable=False,
        comment='Zone display name'
    )
    
    description = Column(
        Text,
        comment='Zone description'
    )
    
    zone_type = Column(
        String(20),
        nullable=False,
        server_default='outdoor',
        comment='Type of zone'
    )
    
    # =========================================================================
    # LOCATION
    # =========================================================================
    latitude = Column(
        Numeric(10, 8),
        comment='Latitude coordinate'
    )
    
    longitude = Column(
        Numeric(11, 8),
        comment='Longitude coordinate'
    )
    
    address = Column(
        String(255),
        comment='Physical address'
    )
    
    city = Column(
        String(100),
        comment='City'
    )
    
    state = Column(
        String(50),
        comment='State/province'
    )
    
    postal_code = Column(
        String(20),
        comment='Postal/ZIP code'
    )
    
    country = Column(
        String(2),
        server_default='US',
        comment='Country code'
    )
    
    # =========================================================================
    # PHYSICAL CHARACTERISTICS
    # =========================================================================
    total_area_sqm = Column(
        Float,
        comment='Total area in square meters'
    )
    
    levels_count = Column(
        Integer,
        server_default='1',
        comment='Number of levels'
    )
    
    has_multi_level = Column(
        Boolean,
        server_default='false',
        comment='Whether zone has multiple levels'
    )
    
    # =========================================================================
    # CAPACITY
    # =========================================================================
    total_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Total number of spots'
    )
    
    available_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Currently available spots'
    )
    
    occupied_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Currently occupied spots'
    )
    
    reserved_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Currently reserved spots'
    )
    
    maintenance_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Spots under maintenance'
    )
    
    # =========================================================================
    # CAPACITY BY TYPE
    # =========================================================================
    capacity_by_type = Column(
        JSONB,
        comment='Capacity breakdown by spot type'
    )
    
    # =========================================================================
    # OPERATING HOURS
    # =========================================================================
    opening_time = Column(
        Time,
        comment='Regular opening time'
    )
    
    closing_time = Column(
        Time,
        comment='Regular closing time'
    )
    
    is_24_hours = Column(
        Boolean,
        server_default='false',
        comment='Whether zone is open 24/7'
    )
    
    timezone = Column(
        String(50),
        server_default='UTC',
        comment='Timezone for operating hours'
    )
    
    # =========================================================================
    # ACCESS
    # =========================================================================
    entry_gates = Column(
        ARRAY(String(50)),
        comment='Entry gate identifiers'
    )
    
    exit_gates = Column(
        ARRAY(String(50)),
        comment='Exit gate identifiers'
    )
    
    access_instructions = Column(
        Text,
        comment='Instructions for accessing zone'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    status = Column(
        String(20),
        server_default='active',
        comment='Current zone status'
    )
    
    is_active = Column(
        Boolean,
        nullable=False,
        server_default='true',
        comment='Whether zone is active'
    )
    
    is_full = Column(
        Boolean,
        server_default='false',
        comment='Whether zone is currently full'
    )
    
    # =========================================================================
    # FEATURES
    # =========================================================================
    features_summary = Column(
        ARRAY(String(50)),
        comment='Summary of available features'
    )
    
    has_ev_charging = Column(
        Boolean,
        server_default='false',
        comment='Whether zone has EV charging'
    )
    
    has_car_wash = Column(
        Boolean,
        server_default='false',
        comment='Whether zone has car wash'
    )
    
    has_security = Column(
        Boolean,
        server_default='false',
        comment='Whether zone has security'
    )
    
    has_covered = Column(
        Boolean,
        server_default='false',
        comment='Whether zone is covered'
    )
    
    has_heated = Column(
        Boolean,
        server_default='false',
        comment='Whether zone is heated'
    )
    
    has_valet = Column(
        Boolean,
        server_default='false',
        comment='Whether zone offers valet'
    )
    
    # =========================================================================
    # MEDIA
    # =========================================================================
    image_url = Column(
        String(500),
        comment='URL to zone image'
    )
    
    map_url = Column(
        String(500),
        comment='URL to zone map'
    )
    
    virtual_tour_url = Column(
        String(500),
        comment='URL to virtual tour'
    )
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    average_occupancy_rate = Column(
        Float,
        comment='Average occupancy rate'
    )
    
    peak_hours = Column(
        JSONB,
        comment='Peak hours data'
    )
    
    daily_revenue_average = Column(
        Numeric(10, 2),
        comment='Average daily revenue'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    tags = Column(
        ARRAY(String(50)),
        comment='Custom tags'
    )
    
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created this record'
    )
    
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who last updated this record'
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        comment='Soft delete timestamp'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    levels = relationship(
        'ZoneLevel',
        back_populates='zone',
        cascade='all, delete-orphan',
        order_by='ZoneLevel.level_number',
        comment='Levels within this zone'
    )
    
    gates = relationship(
        'ZoneGate',
        back_populates='zone',
        cascade='all, delete-orphan',
        comment='Entry/exit gates'
    )
    
    restrictions = relationship(
        'ZoneRestriction',
        back_populates='zone',
        cascade='all, delete-orphan',
        comment='Vehicle restrictions'
    )
    
    operating_hours = relationship(
        'ZoneOperatingHours',
        back_populates='zone',
        cascade='all, delete-orphan',
        comment='Operating hours schedules'
    )
    
    features = relationship(
        'ZoneFeature',
        back_populates='zone',
        cascade='all, delete-orphan',
        comment='Zone features and amenities'
    )
    
    occupancy_history = relationship(
        'ZoneOccupancyHistory',
        back_populates='zone',
        cascade='all, delete-orphan',
        order_by='desc(ZoneOccupancyHistory.timestamp)',
        comment='Occupancy history'
    )
    
    maintenance = relationship(
        'ZoneMaintenance',
        back_populates='zone',
        cascade='all, delete-orphan',
        order_by='desc(ZoneMaintenance.scheduled_date)',
        comment='Maintenance records'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def utilization_rate(self) -> float:
        """Calculate current utilization rate (occupied + reserved) / total."""
        if self.total_spots == 0:
            return 0.0
        return ((self.occupied_spots + self.reserved_spots) / self.total_spots) * 100
    
    @hybrid_property
    def occupancy_rate(self) -> float:
        """Calculate current occupancy rate (occupied / total)."""
        if self.total_spots == 0:
            return 0.0
        return (self.occupied_spots / self.total_spots) * 100
    
    @hybrid_property
    def is_open_now(self) -> bool:
        """Check if zone is currently open."""
        if self.status != 'active' or not self.is_active:
            return False
        
        if self.is_24_hours:
            return True
        
        # Check regular hours
        if self.opening_time and self.closing_time:
            now = datetime.now().time()
            if self.opening_time <= self.closing_time:
                return self.opening_time <= now <= self.closing_time
            else:
                return now >= self.opening_time or now <= self.closing_time
        
        # Check operating hours schedules
        today_name = datetime.now().strftime('%A').lower()
        for hours in self.operating_hours:
            if hours.is_applicable_today() and not hours.is_closed:
                now = datetime.now().time()
                if hours.opening_time <= hours.closing_time:
                    if hours.opening_time <= now <= hours.closing_time:
                        return True
                else:
                    if now >= hours.opening_time or now <= hours.closing_time:
                        return True
        
        return False
    
    @hybrid_property
    def display_location(self) -> str:
        """Get display location string."""
        parts = []
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        return ', '.join(parts) if parts else self.address or ''
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @validates('code')
    def validate_code(self, key, code):
        """Validate zone code format."""
        if not code or len(code) < 2:
            raise ValueError('Zone code must be at least 2 characters')
        return code.upper()
    
    @validates('country')
    def validate_country(self, key, country):
        """Validate country code."""
        if country:
            return country.upper()
        return 'US'
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def update_counts(self) -> Dict[str, int]:
        """Update spot counts for this zone."""
        from models.parking_spot import ParkingSpot
        
        counts = object_session(self).query(
            func.count(ParkingSpot.id).label('total'),
            func.sum(case([(ParkingSpot.status == 'available', 1)], else_=0)).label('available'),
            func.sum(case([(ParkingSpot.status == 'occupied', 1)], else_=0)).label('occupied'),
            func.sum(case([(ParkingSpot.status == 'reserved', 1)], else_=0)).label('reserved'),
            func.sum(case([(ParkingSpot.status == 'maintenance', 1)], else_=0)).label('maintenance')
        ).filter(
            ParkingSpot.zone_id == self.id,
            ParkingSpot.is_active == True
        ).first()
        
        if counts:
            self.total_spots = counts.total or 0
            self.available_spots = counts.available or 0
            self.occupied_spots = counts.occupied or 0
            self.reserved_spots = counts.reserved or 0
            self.maintenance_spots = counts.maintenance or 0
            self.is_full = self.available_spots == 0 and self.total_spots > 0
        
        # Update capacity by type
        type_counts = object_session(self).query(
            ParkingSpot.spot_type,
            func.count().label('count')
        ).filter(
            ParkingSpot.zone_id == self.id,
            ParkingSpot.is_active == True
        ).group_by(ParkingSpot.spot_type).all()
        
        self.capacity_by_type = {t: c for t, c in type_counts}
        
        return {
            'total': self.total_spots,
            'available': self.available_spots,
            'occupied': self.occupied_spots,
            'reserved': self.reserved_spots,
            'maintenance': self.maintenance_spots
        }
    
    def get_available_spots(
        self,
        spot_type: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        features: Optional[Dict[str, bool]] = None
    ) -> List[Any]:
        """Get available spots matching criteria."""
        from models.parking_spot import ParkingSpot
        
        query = object_session(self).query(ParkingSpot).filter(
            ParkingSpot.zone_id == self.id,
            ParkingSpot.status == 'available',
            ParkingSpot.is_active == True
        )
        
        if spot_type:
            query = query.filter(ParkingSpot.spot_type == spot_type)
        
        if vehicle_type:
            query = query.filter(ParkingSpot.vehicle_type == vehicle_type)
        
        if features:
            for feature, value in features.items():
                if hasattr(ParkingSpot, feature):
                    query = query.filter(getattr(ParkingSpot, feature) == value)
        
        return query.all()
    
    def check_restrictions(self, vehicle: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check all restrictions against a vehicle."""
        violations = []
        for restriction in self.restrictions:
            if not restriction.is_active:
                continue
            
            compliant, message = restriction.check_compliance(vehicle)
            if not compliant:
                violations.append({
                    'restriction_id': str(restriction.id),
                    'restriction_type': restriction.restriction_type,
                    'message': message,
                    'penalty': float(restriction.penalty_amount) if restriction.penalty_amount else None
                })
        
        return violations
    
    def get_operating_hours_for_date(self, date: datetime.date) -> Optional[Dict[str, Any]]:
        """Get operating hours for a specific date."""
        # Check if date has specific operating hours
        for hours in self.operating_hours:
            result = hours.get_hours_for_date(date)
            if result:
                return result
        
        # Fall back to regular hours
        if self.is_24_hours:
            return {
                'opening_time': None,
                'closing_time': None,
                'is_closed': False
            }
        
        return {
            'opening_time': self.opening_time,
            'closing_time': self.closing_time,
            'is_closed': self.opening_time is None or self.closing_time is None
        }
    
    def calculate_distance(self, lat: float, lng: float) -> float:
        """Calculate distance from coordinates to zone."""
        if not self.latitude or not self.longitude:
            return float('inf')
        
        # Haversine formula
        R = 6371  # Earth's radius in kilometers
        
        lat1 = math.radians(float(self.latitude))
        lon1 = math.radians(float(self.longitude))
        lat2 = math.radians(lat)
        lon2 = math.radians(lng)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def record_occupancy_snapshot(self) -> ZoneOccupancyHistory:
        """Record current occupancy snapshot."""
        return ZoneOccupancyHistory.record_snapshot(object_session(self), self.id)
    
    def to_dict(self, include_details: bool = False) -> Dict[str, Any]:
        """Convert zone to dictionary."""
        data = {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'zone_type': self.zone_type,
            'location': {
                'latitude': float(self.latitude) if self.latitude else None,
                'longitude': float(self.longitude) if self.longitude else None,
                'address': self.address,
                'city': self.city,
                'state': self.state,
                'postal_code': self.postal_code,
                'country': self.country,
                'display': self.display_location
            },
            'physical': {
                'total_area_sqm': self.total_area_sqm,
                'levels_count': self.levels_count,
                'has_multi_level': self.has_multi_level
            },
            'capacity': {
                'total': self.total_spots,
                'available': self.available_spots,
                'occupied': self.occupied_spots,
                'reserved': self.reserved_spots,
                'maintenance': self.maintenance_spots,
                'utilization_rate': round(self.utilization_rate, 2),
                'occupancy_rate': round(self.occupancy_rate, 2),
                'by_type': self.capacity_by_type
            },
            'operating_hours': {
                'regular': {
                    'opening_time': self.opening_time.isoformat() if self.opening_time else None,
                    'closing_time': self.closing_time.isoformat() if self.closing_time else None,
                    'is_24_hours': self.is_24_hours
                },
                'is_open_now': self.is_open_now,
                'timezone': self.timezone
            },
            'access': {
                'entry_gates': self.entry_gates,
                'exit_gates': self.exit_gates,
                'instructions': self.access_instructions
            },
            'features': {
                'has_ev_charging': self.has_ev_charging,
                'has_car_wash': self.has_car_wash,
                'has_security': self.has_security,
                'has_covered': self.has_covered,
                'has_heated': self.has_heated,
                'has_valet': self.has_valet,
                'summary': self.features_summary
            },
            'media': {
                'image_url': self.image_url,
                'map_url': self.map_url,
                'virtual_tour_url': self.virtual_tour_url
            },
            'statistics': {
                'average_occupancy_rate': round(self.average_occupancy_rate, 2) if self.average_occupancy_rate else None,
                'peak_hours': self.peak_hours,
                'daily_revenue_average': float(self.daily_revenue_average) if self.daily_revenue_average else None
            },
            'status': {
                'current': self.status,
                'is_active': self.is_active,
                'is_full': self.is_full
            },
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_details:
            data['details'] = {
                'levels': [level.to_dict() for level in self.levels],
                'gates': [gate.to_dict() for gate in self.gates],
                'restrictions': [r.to_dict() for r in self.restrictions],
                'operating_hours_schedules': [h.to_dict() for h in self.operating_hours],
                'features_detail': [f.to_dict() for f in self.features],
                'maintenance': [m.to_dict() for m in self.maintenance[:5]] if self.maintenance else []
            }
        
        return data
    
    def __repr__(self) -> str:
        return f"<Zone(id={self.id}, code={self.code}, name={self.name})>"


# =========================================================================
# EVENT LISTENERS
# =========================================================================

@event.listens_for(Zone, 'before_insert')
def zone_before_insert(mapper, connection, target):
    """Generate zone code if not provided."""
    if not target.code:
        # Generate code based on name
        prefix = ''.join(word[0].upper() for word in target.name.split()[:2])
        
        # Get next sequence number
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(code FROM 4)::INTEGER), 0) + 1
                FROM zones
                WHERE code LIKE :pattern
            """),
            {'pattern': f'{prefix}%'}
        )
        seq_num = result.scalar()
        
        target.code = f"{prefix}{seq_num:03d}"


@event.listens_for(Zone, 'after_insert')
@event.listens_for(Zone, 'after_update')
def zone_after_save(mapper, connection, target):
    """Update zone statistics when saved."""
    # This would typically be handled by triggers or async jobs
    pass


@event.listens_for(ZoneLevel, 'after_insert')
@event.listens_for(ZoneLevel, 'after_update')
@event.listens_for(ZoneLevel, 'after_delete')
def zone_level_after_change(mapper, connection, target):
    """Update zone level count when levels change."""
    if target.zone_id:
        count = connection.execute(
            text("SELECT COUNT(*) FROM zone_levels WHERE zone_id = :zone_id"),
            {'zone_id': target.zone_id}
        ).scalar()
        
        connection.execute(
            text("""
                UPDATE zones
                SET levels_count = :count,
                    has_multi_level = :has_multi,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :zone_id
            """),
            {
                'zone_id': target.zone_id,
                'count': count,
                'has_multi': count > 1
            }
        )


# =========================================================================
# FACTORY FUNCTIONS
# =========================================================================

def create_zone(
    name: str,
    zone_type: str = 'outdoor',
    code: Optional[str] = None,
    **kwargs
) -> Zone:
    """
    Factory function to create a new zone.
    
    Args:
        name: Zone name
        zone_type: Type of zone
        code: Zone code (auto-generated if not provided)
        **kwargs: Additional zone attributes
        
    Returns:
        New Zone instance
    """
    zone = Zone(
        name=name,
        zone_type=zone_type,
        code=code,
        **kwargs
    )
    
    return zone


def create_standard_zones(session) -> List[Zone]:
    """
    Create standard parking zones.
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        List of created zones
    """
    zones = [
        Zone(
            code='GFA',
            name='Ground Floor A',
            description='Main ground floor parking area - Section A',
            zone_type='outdoor',
            total_spots=50,
            available_spots=50,
            is_24_hours=True,
            has_ev_charging=True,
            has_security=True,
            features_summary=['ev_charging', 'security', 'lighting']
        ),
        Zone(
            code='GFB',
            name='Ground Floor B',
            description='Main ground floor parking area - Section B',
            zone_type='outdoor',
            total_spots=50,
            available_spots=50,
            is_24_hours=True,
            has_security=True,
            features_summary=['security', 'lighting']
        ),
        Zone(
            code='FFC',
            name='First Floor Covered',
            description='Covered parking on first floor',
            zone_type='covered',
            total_spots=40,
            available_spots=40,
            opening_time=Time(6, 0),
            closing_time=Time(22, 0),
            has_ev_charging=True,
            has_covered=True,
            max_height_cm=200,
            features_summary=['ev_charging', 'covered', 'elevator']
        ),
        Zone(
            code='VIP',
            name='VIP Section',
            description='Exclusive VIP parking area',
            zone_type='reserved',
            total_spots=20,
            available_spots=20,
            is_24_hours=True,
            has_ev_charging=True,
            has_security=True,
            has_covered=True,
            has_valet=True,
            features_summary=['ev_charging', 'security', 'covered', 'valet', 'cctv']
        ),
        Zone(
            code='MOTO',
            name='Motorcycle Parking',
            description='Designated motorcycle parking area',
            zone_type='outdoor',
            total_spots=30,
            available_spots=30,
            is_24_hours=True,
            has_covered=True,
            features_summary=['covered', 'bike_rack']
        ),
        Zone(
            code='UNDR',
            name='Underground Parking',
            description='Underground parking level B1-B3',
            zone_type='underground',
            total_spots=120,
            available_spots=120,
            is_24_hours=True,
            has_ev_charging=True,
            has_security=True,
            has_heated=True,
            max_height_cm=210,
            features_summary=['ev_charging', 'security', 'heated', 'elevator', 'cctv']
        ),
    ]
    
    for zone in zones:
        existing = session.query(Zone).filter_by(code=zone.code).first()
        if not existing:
            session.add(zone)
    
    session.commit()
    return zones


# =========================================================================
# EXPORTS
# =========================================================================

__all__ = [
    # Main models
    'Zone',
    'ZoneLevel',
    'ZoneGate',
    'ZoneRestriction',
    'ZoneOperatingHours',
    'ZoneFeature',
    'ZoneOccupancyHistory',
    'ZoneMaintenance',
    
    # Enums
    'ZoneType',
    'ZoneStatus',
    'AccessType',
    'EntryType',
    'RestrictionType',
    'OperatingDay',
    'ZoneFeature',
    
    # Factory functions
    'create_zone',
    'create_standard_zones',
]