# parking-management/data/migrations/models/parking_spot.py

"""
Parking Spot model for parking management system.

This module defines the ParkingSpot model and related classes for managing
individual parking spots, zones, rates, sensors, maintenance, and occupancy tracking.
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
from datetime import datetime, date, timedelta
import logging
from typing import Optional, List, Dict, Any, Tuple
from geopy.distance import distance

# Configure logging
logger = logging.getLogger(__name__)

# Create base class
Base = declarative_base()


class SpotType(str, enum.Enum):
    """Enum for parking spot types."""
    STANDARD = 'standard'
    COMPACT = 'compact'
    HANDICAPPED = 'handicapped'
    ELECTRIC = 'electric'
    MOTORCYCLE = 'motorcycle'
    BUS = 'bus'
    TRUCK = 'truck'
    VIP = 'vip'
    STAFF = 'staff'
    VISITOR = 'visitor'


class SpotStatus(str, enum.Enum):
    """Enum for parking spot status."""
    AVAILABLE = 'available'
    OCCUPIED = 'occupied'
    RESERVED = 'reserved'
    MAINTENANCE = 'maintenance'
    OUT_OF_SERVICE = 'out_of_service'
    BLOCKED = 'blocked'


class ZoneType(str, enum.Enum):
    """Enum for parking zone types."""
    INDOOR = 'indoor'
    OUTDOOR = 'outdoor'
    COVERED = 'covered'
    ROOFTOP = 'rooftop'
    UNDERGROUND = 'underground'


class SensorType(str, enum.Enum):
    """Enum for sensor types."""
    ULTRASONIC = 'ultrasonic'
    CAMERA = 'camera'
    MAGNETIC = 'magnetic'
    LASER = 'laser'
    RADAR = 'radar'


class SensorStatus(str, enum.Enum):
    """Enum for sensor status."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    FAULTY = 'faulty'
    CALIBRATING = 'calibrating'
    OFFLINE = 'offline'


class MaintenanceType(str, enum.Enum):
    """Enum for maintenance types."""
    CLEANING = 'cleaning'
    REPAIR = 'repair'
    INSPECTION = 'inspection'
    UPGRADE = 'upgrade'
    EMERGENCY = 'emergency'


class MaintenanceStatus(str, enum.Enum):
    """Enum for maintenance status."""
    SCHEDULED = 'scheduled'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    DELAYED = 'delayed'


class ParkingZone(Base):
    """
    Parking zones/areas within the facility.
    
    Represents a logical grouping of parking spots with shared characteristics,
    such as location, type, and operating hours.
    """
    
    __tablename__ = 'parking_zones'
    __table_args__ = (
        Index('ix_zones_code', 'code', unique=True),
        Index('ix_zones_name', 'name'),
        Index('ix_zones_type_active', 'zone_type', 'is_active'),
        Index('ix_zones_location', 'latitude', 'longitude'),
        Index('ix_zones_is_active', 'is_active'),
        {'comment': 'Parking zones/areas within the facility'}
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
    # BASIC INFORMATION
    # =========================================================================
    name = Column(
        String(100),
        nullable=False,
        comment='Zone display name'
    )
    
    code = Column(
        String(20),
        nullable=False,
        unique=True,
        comment='Unique zone code (e.g., GFA, FFC, VIP)'
    )
    
    description = Column(
        Text,
        comment='Zone description'
    )
    
    zone_type = Column(
        String(20),
        nullable=False,
        server_default='outdoor',
        comment='Type of zone: indoor, outdoor, covered, rooftop, underground'
    )
    
    floor = Column(
        Integer,
        comment='Floor number (if multi-level)'
    )
    
    section = Column(
        String(10),
        comment='Section identifier within floor'
    )
    
    # =========================================================================
    # CAPACITY AND COUNTS
    # =========================================================================
    total_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Total number of spots in zone'
    )
    
    available_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Number of currently available spots'
    )
    
    reserved_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Number of currently reserved spots'
    )
    
    occupied_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Number of currently occupied spots'
    )
    
    maintenance_spots = Column(
        Integer,
        nullable=False,
        server_default='0',
        comment='Number of spots under maintenance'
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
        comment='Physical address of zone'
    )
    
    entrance_coordinates = Column(
        JSONB,
        comment='Coordinates of entrance(s)'
    )
    
    exit_coordinates = Column(
        JSONB,
        comment='Coordinates of exit(s)'
    )
    
    # =========================================================================
    # OPERATING HOURS
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
        server_default='false',
        comment='Whether zone is open 24/7'
    )
    
    # =========================================================================
    # FEATURES AND AMENITIES
    # =========================================================================
    has_ev_charging = Column(
        Boolean,
        server_default='false',
        comment='Whether zone has EV charging stations'
    )
    
    has_car_wash = Column(
        Boolean,
        server_default='false',
        comment='Whether zone has car wash service'
    )
    
    has_security = Column(
        Boolean,
        server_default='false',
        comment='Whether zone has security cameras/patrol'
    )
    
    has_roof = Column(
        Boolean,
        server_default='false',
        comment='Whether zone has roof cover'
    )
    
    # =========================================================================
    # RESTRICTIONS
    # =========================================================================
    max_height_cm = Column(
        Integer,
        comment='Maximum vehicle height allowed (cm)'
    )
    
    max_width_cm = Column(
        Integer,
        comment='Maximum vehicle width allowed (cm)'
    )
    
    max_length_cm = Column(
        Integer,
        comment='Maximum vehicle length allowed (cm)'
    )
    
    max_weight_kg = Column(
        Integer,
        comment='Maximum vehicle weight allowed (kg)'
    )
    
    # =========================================================================
    # MEDIA
    # =========================================================================
    image_url = Column(
        String(500),
        comment='URL to zone image'
    )
    
    floor_plan_url = Column(
        String(500),
        comment='URL to zone floor plan'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    is_active = Column(
        Boolean,
        nullable=False,
        server_default='true',
        comment='Whether zone is active'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional flexible metadata'
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
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    spots = relationship(
        'ParkingSpot',
        back_populates='zone',
        cascade='all, delete-orphan',
        lazy='dynamic',
        comment='Parking spots in this zone'
    )
    
    rates = relationship(
        'ParkingRate',
        back_populates='zone',
        cascade='all, delete-orphan',
        comment='Rate configurations for this zone'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def utilization_rate(self) -> float:
        """Calculate current utilization rate (occupied / total)."""
        if self.total_spots == 0:
            return 0.0
        return (self.occupied_spots / self.total_spots) * 100
    
    @hybrid_property
    def is_open_now(self) -> bool:
        """Check if zone is currently open."""
        if self.is_24_hours:
            return True
        
        now = datetime.now().time()
        if self.opening_time and self.closing_time:
            if self.opening_time <= self.closing_time:
                # Normal hours (e.g., 8:00-18:00)
                return self.opening_time <= now <= self.closing_time
            else:
                # Overnight hours (e.g., 22:00-06:00)
                return now >= self.opening_time or now <= self.closing_time
        
        return False
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def update_counts(self) -> Dict[str, int]:
        """
        Update spot counts based on current spot statuses.
        
        Returns:
            Dictionary with updated counts
        """
        from sqlalchemy import func
        
        counts = object_session(self).query(
            func.count(ParkingSpot.id).label('total'),
            func.sum(case([(ParkingSpot.status == 'available', 1)], else_=0)).label('available'),
            func.sum(case([(ParkingSpot.status == 'occupied', 1)], else_=0)).label('occupied'),
            func.sum(case([(ParkingSpot.status == 'reserved', 1)], else_=0)).label('reserved'),
            func.sum(case([(ParkingSpot.status == 'maintenance', 1)], else_=0)).label('maintenance')
        ).filter(ParkingSpot.zone_id == self.id).first()
        
        if counts:
            self.total_spots = counts.total or 0
            self.available_spots = counts.available or 0
            self.occupied_spots = counts.occupied or 0
            self.reserved_spots = counts.reserved or 0
            self.maintenance_spots = counts.maintenance or 0
        
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
    ) -> List['ParkingSpot']:
        """
        Get available spots matching criteria.
        
        Args:
            spot_type: Type of spot required
            vehicle_type: Type of vehicle
            features: Required features (e.g., {'has_ev_charger': True})
            
        Returns:
            List of available parking spots
        """
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert zone to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'zone_type': self.zone_type,
            'floor': self.floor,
            'section': self.section,
            'total_spots': self.total_spots,
            'available_spots': self.available_spots,
            'reserved_spots': self.reserved_spots,
            'occupied_spots': self.occupied_spots,
            'maintenance_spots': self.maintenance_spots,
            'utilization_rate': self.utilization_rate,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'address': self.address,
            'opening_time': self.opening_time.isoformat() if self.opening_time else None,
            'closing_time': self.closing_time.isoformat() if self.closing_time else None,
            'is_24_hours': self.is_24_hours,
            'is_open_now': self.is_open_now,
            'has_ev_charging': self.has_ev_charging,
            'has_car_wash': self.has_car_wash,
            'has_security': self.has_security,
            'has_roof': self.has_roof,
            'max_height_cm': self.max_height_cm,
            'max_width_cm': self.max_width_cm,
            'max_length_cm': self.max_length_cm,
            'max_weight_kg': self.max_weight_kg,
            'image_url': self.image_url,
            'floor_plan_url': self.floor_plan_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ParkingZone(id={self.id}, code={self.code}, name={self.name})>"


class ParkingSpot(Base):
    """
    Individual parking spots.
    
    Represents a single parking spot with its properties, current status,
    and real-time occupancy information.
    """
    
    __tablename__ = 'parking_spots'
    __table_args__ = (
        UniqueConstraint('zone_id', 'spot_number', name='uq_spot_zone_number'),
        Index('ix_spots_status', 'status'),
        Index('ix_spots_type', 'spot_type'),
        Index('ix_spots_vehicle_type', 'vehicle_type'),
        Index('ix_spots_current_vehicle', 'current_vehicle_id'),
        Index('ix_spots_current_session', 'current_session_id'),
        Index('ix_spots_sensor', 'sensor_id'),
        Index('ix_spots_coordinates', 'coordinates_x', 'coordinates_y'),
        Index('ix_spots_is_active', 'is_active'),
        Index('ix_spots_status_type', 'status', 'spot_type'),
        Index('ix_spots_current_occupancy', 'status', 'current_vehicle_id', 'current_session_id'),
        Index('ix_spots_available_search', 'zone_id', 'spot_type', 'status',
              postgresql_where=text("status = 'available'")),
        Index('ix_spots_ev_charger', 'has_ev_charger', 'ev_charger_type',
              postgresql_where=text("has_ev_charger = true")),
        Index('ix_spots_handicapped', 'is_handicapped',
              postgresql_where=text("is_handicapped = true")),
        CheckConstraint(
            "status IN ('available', 'occupied', 'reserved', 'maintenance', 'out_of_service', 'blocked')",
            name='ck_spots_status'
        ),
        CheckConstraint(
            "spot_type IN ('standard', 'compact', 'handicapped', 'electric', 'motorcycle', 'bus', 'truck', 'vip', 'staff', 'visitor')",
            name='ck_spots_type'
        ),
        {'comment': 'Individual parking spots'}
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
    # ZONE RELATIONSHIP
    # =========================================================================
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_zones.id', ondelete='CASCADE'),
        nullable=False,
        comment='Parent zone ID'
    )
    
    spot_number = Column(
        String(20),
        nullable=False,
        comment='Spot number/identifier within zone'
    )
    
    # =========================================================================
    # LOCATION WITHIN ZONE
    # =========================================================================
    level = Column(
        String(10),
        comment='Level within zone (if multi-level)'
    )
    
    row = Column(
        String(10),
        comment='Row identifier'
    )
    
    column = Column(
        String(10),
        comment='Column identifier'
    )
    
    coordinates_x = Column(
        Float,
        comment='X coordinate on floor plan'
    )
    
    coordinates_y = Column(
        Float,
        comment='Y coordinate on floor plan'
    )
    
    coordinates_z = Column(
        Float,
        comment='Z coordinate on floor plan (for 3D)'
    )
    
    # =========================================================================
    # SPOT CHARACTERISTICS
    # =========================================================================
    spot_type = Column(
        String(20),
        nullable=False,
        server_default='standard',
        comment='Type of parking spot'
    )
    
    status = Column(
        String(20),
        nullable=False,
        server_default='available',
        comment='Current spot status'
    )
    
    vehicle_type = Column(
        String(20),
        comment='Type of vehicle this spot is optimized for'
    )
    
    # =========================================================================
    # DIMENSIONS
    # =========================================================================
    width_cm = Column(
        Integer,
        comment='Spot width in centimeters'
    )
    
    length_cm = Column(
        Integer,
        comment='Spot length in centimeters'
    )
    
    height_cm = Column(
        Integer,
        comment='Spot height in centimeters'
    )
    
    max_weight_kg = Column(
        Integer,
        comment='Maximum vehicle weight in kg'
    )
    
    # =========================================================================
    # FEATURES
    # =========================================================================
    has_ev_charger = Column(
        Boolean,
        server_default='false',
        comment='Whether spot has EV charger'
    )
    
    ev_charger_type = Column(
        String(50),
        comment='Type of EV charger (Level 1, Level 2, DC Fast)'
    )
    
    ev_charger_power_kw = Column(
        Float,
        comment='Charger power in kW'
    )
    
    has_sensor = Column(
        Boolean,
        server_default='false',
        comment='Whether spot has occupancy sensor'
    )
    
    sensor_id = Column(
        String(100),
        comment='Sensor identifier'
    )
    
    is_handicapped = Column(
        Boolean,
        server_default='false',
        comment='Whether spot is handicapped accessible'
    )
    
    is_covered = Column(
        Boolean,
        server_default='false',
        comment='Whether spot is covered'
    )
    
    is_near_elevator = Column(
        Boolean,
        server_default='false',
        comment='Whether spot is near elevator'
    )
    
    is_near_entrance = Column(
        Boolean,
        server_default='false',
        comment='Whether spot is near entrance'
    )
    
    # =========================================================================
    # CURRENT OCCUPANCY
    # =========================================================================
    current_vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='SET NULL'),
        comment='Currently parked vehicle ID'
    )
    
    current_session_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_sessions.id', ondelete='SET NULL'),
        comment='Current parking session ID'
    )
    
    current_reservation_id = Column(
        UUID(as_uuid=True),
        ForeignKey('reservations.id', ondelete='SET NULL'),
        comment='Current reservation ID'
    )
    
    # =========================================================================
    # RATES (OVERRIDE ZONE RATES)
    # =========================================================================
    hourly_rate = Column(
        Numeric(10, 2),
        comment='Override hourly rate'
    )
    
    daily_rate = Column(
        Numeric(10, 2),
        comment='Override daily rate'
    )
    
    monthly_rate = Column(
        Numeric(10, 2),
        comment='Override monthly rate'
    )
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    last_occupied_at = Column(
        DateTime(timezone=True),
        comment='Timestamp when spot was last occupied'
    )
    
    last_vacated_at = Column(
        DateTime(timezone=True),
        comment='Timestamp when spot was last vacated'
    )
    
    occupancy_count_today = Column(
        Integer,
        server_default='0',
        comment='Number of occupancies today'
    )
    
    total_occupancy_count = Column(
        Integer,
        server_default='0',
        comment='Total number of occupancies'
    )
    
    # =========================================================================
    # MEDIA
    # =========================================================================
    image_url = Column(
        String(500),
        comment='URL to spot image'
    )
    
    # =========================================================================
    # NOTES AND STATUS
    # =========================================================================
    notes = Column(
        Text,
        comment='Additional notes about spot'
    )
    
    is_active = Column(
        Boolean,
        nullable=False,
        server_default='true',
        comment='Whether spot is active'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional flexible metadata'
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
    zone = relationship(
        'ParkingZone',
        back_populates='spots',
        comment='Parent zone'
    )
    
    current_vehicle = relationship(
        'Vehicle',
        foreign_keys=[current_vehicle_id],
        comment='Currently parked vehicle'
    )
    
    current_session = relationship(
        'ParkingSession',
        foreign_keys=[current_session_id],
        comment='Current parking session'
    )
    
    current_reservation = relationship(
        'Reservation',
        foreign_keys=[current_reservation_id],
        comment='Current reservation'
    )
    
    sensors = relationship(
        'SpotSensor',
        back_populates='spot',
        cascade='all, delete-orphan',
        comment='Sensors monitoring this spot'
    )
    
    maintenance_records = relationship(
        'SpotMaintenance',
        back_populates='spot',
        cascade='all, delete-orphan',
        comment='Maintenance records for this spot'
    )
    
    occupancy_history = relationship(
        'SpotOccupancyHistory',
        back_populates='spot',
        cascade='all, delete-orphan',
        comment='Historical occupancy records'
    )
    
    rates = relationship(
        'ParkingRate',
        foreign_keys='ParkingRate.spot_id',
        cascade='all, delete-orphan',
        comment='Spot-specific rates'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def is_occupied(self) -> bool:
        """Check if spot is currently occupied."""
        return self.status == 'occupied'
    
    @hybrid_property
    def is_available(self) -> bool:
        """Check if spot is currently available."""
        return self.status == 'available'
    
    @hybrid_property
    def is_reserved(self) -> bool:
        """Check if spot is currently reserved."""
        return self.status == 'reserved'
    
    @hybrid_property
    def current_occupancy_duration(self) -> Optional[int]:
        """Get current occupancy duration in minutes."""
        if self.is_occupied and self.last_occupied_at:
            delta = datetime.now(self.last_occupied_at.tzinfo) - self.last_occupied_at
            return int(delta.total_seconds() / 60)
        return None
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def occupy(
        self,
        vehicle_id: uuid.UUID,
        session_id: uuid.UUID,
        reservation_id: Optional[uuid.UUID] = None
    ) -> None:
        """
        Mark spot as occupied.
        
        Args:
            vehicle_id: ID of parked vehicle
            session_id: ID of parking session
            reservation_id: ID of reservation (if applicable)
        """
        self.status = 'occupied'
        self.current_vehicle_id = vehicle_id
        self.current_session_id = session_id
        self.current_reservation_id = reservation_id
        self.last_occupied_at = datetime.now()
        
        # Update occupancy counts
        self.occupancy_count_today += 1
        self.total_occupancy_count += 1
        
        # Create occupancy history record
        history = SpotOccupancyHistory(
            spot_id=self.id,
            session_id=session_id,
            status='occupied',
            vehicle_id=vehicle_id,
            start_time=self.last_occupied_at
        )
        object_session(self).add(history)
    
    def vacate(self) -> None:
        """Mark spot as vacated."""
        if self.is_occupied:
            self.last_vacated_at = datetime.now()
            self.status = 'available'
            
            # Update occupancy history
            history = object_session(self).query(SpotOccupancyHistory).filter(
                SpotOccupancyHistory.spot_id == self.id,
                SpotOccupancyHistory.end_time.is_(None)
            ).first()
            
            if history:
                history.end_time = self.last_vacated_at
                history.duration_minutes = int(
                    (history.end_time - history.start_time).total_seconds() / 60
                )
        
        self.current_vehicle_id = None
        self.current_session_id = None
        self.current_reservation_id = None
    
    def reserve(self, reservation_id: uuid.UUID) -> None:
        """
        Mark spot as reserved.
        
        Args:
            reservation_id: ID of reservation
        """
        self.status = 'reserved'
        self.current_reservation_id = reservation_id
    
    def release_reservation(self) -> None:
        """Release a reservation without occupying."""
        if self.status == 'reserved':
            self.status = 'available'
            self.current_reservation_id = None
    
    def start_maintenance(self, maintenance_id: uuid.UUID) -> None:
        """
        Mark spot as under maintenance.
        
        Args:
            maintenance_id: ID of maintenance record
        """
        self.status = 'maintenance'
        self.notes = f"Under maintenance: {maintenance_id}"
    
    def end_maintenance(self) -> None:
        """End maintenance period."""
        if self.status == 'maintenance':
            self.status = 'available'
            self.notes = None
    
    def check_availability(
        self,
        start_time: datetime,
        end_time: datetime,
        exclude_reservation_id: Optional[uuid.UUID] = None
    ) -> bool:
        """
        Check if spot is available for a time range.
        
        Args:
            start_time: Start of desired time range
            end_time: End of desired time range
            exclude_reservation_id: Reservation to exclude from check
            
        Returns:
            True if spot is available
        """
        from models.reservation import Reservation
        
        # Check current status
        if self.status not in ['available', 'reserved']:
            return False
        
        # Check for conflicting reservations
        query = object_session(self).query(Reservation).filter(
            Reservation.spot_id == self.id,
            Reservation.status.in_(['confirmed', 'checked_in']),
            Reservation.start_time < end_time,
            Reservation.end_time > start_time
        )
        
        if exclude_reservation_id:
            query = query.filter(Reservation.id != exclude_reservation_id)
        
        return query.count() == 0
    
    def get_current_rate(
        self,
        vehicle_type: Optional[str] = None,
        check_time: Optional[datetime] = None
    ) -> Optional['ParkingRate']:
        """
        Get applicable rate for current time.
        
        Args:
            vehicle_type: Type of vehicle
            check_time: Time to check (defaults to now)
            
        Returns:
            Applicable rate or None
        """
        if check_time is None:
            check_time = datetime.now()
        
        # Check spot-specific rates first
        rate = object_session(self).query(ParkingRate).filter(
            ParkingRate.spot_id == self.id,
            ParkingRate.vehicle_type == vehicle_type if vehicle_type else True,
            ParkingRate.effective_from <= check_time,
            or_(
                ParkingRate.effective_to.is_(None),
                ParkingRate.effective_to >= check_time
            ),
            ParkingRate.is_active == True
        ).order_by(ParkingRate.priority.desc()).first()
        
        if rate:
            return rate
        
        # Fall back to zone rates
        return object_session(self).query(ParkingRate).filter(
            ParkingRate.zone_id == self.zone_id,
            ParkingRate.spot_type == self.spot_type,
            ParkingRate.vehicle_type == vehicle_type if vehicle_type else True,
            ParkingRate.effective_from <= check_time,
            or_(
                ParkingRate.effective_to.is_(None),
                ParkingRate.effective_to >= check_time
            ),
            ParkingRate.is_active == True
        ).order_by(ParkingRate.priority.desc()).first()
    
    def calculate_parking_cost(
        self,
        start_time: datetime,
        end_time: datetime,
        vehicle_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate parking cost for a time range.
        
        Args:
            start_time: Parking start time
            end_time: Parking end time
            vehicle_type: Type of vehicle
            
        Returns:
            Dictionary with cost breakdown
        """
        rate = self.get_current_rate(vehicle_type, start_time)
        
        if not rate:
            return {
                'base_amount': 0,
                'tax_amount': 0,
                'total_amount': 0,
                'currency': 'USD',
                'rate_applied': None,
                'rate_type': None
            }
        
        duration_hours = (end_time - start_time).total_seconds() / 3600
        duration_days = duration_hours / 24
        
        # Calculate base amount based on rate unit
        if rate.unit == 'hour':
            base_amount = rate.base_rate * duration_hours
            rate_type = 'hourly'
        elif rate.unit == 'day':
            base_amount = rate.base_rate * max(1, round(duration_days))
            rate_type = 'daily'
        elif rate.unit == 'week':
            base_amount = rate.base_rate * max(1, round(duration_days / 7))
            rate_type = 'weekly'
        elif rate.unit == 'month':
            base_amount = rate.base_rate * max(1, round(duration_days / 30))
            rate_type = 'monthly'
        else:
            base_amount = rate.base_rate
            rate_type = 'fixed'
        
        # Apply weekend/night rates if applicable
        if rate.has_weekend_rate and start_time.weekday() >= 5:  # Saturday or Sunday
            base_amount = rate.weekend_rate * duration_hours
        elif rate.has_night_rate:
            # Check if time falls within night hours
            night_start = rate.night_start_time
            night_end = rate.night_end_time
            if night_start and night_end:
                time = start_time.time()
                if night_start <= time <= night_end:
                    base_amount = rate.night_rate * duration_hours
        
        # Apply maximum cap
        if rate.has_maximum_cap and base_amount > rate.maximum_cap_amount:
            base_amount = rate.maximum_cap_amount
        
        # Calculate tax
        tax_rate = 0.10  # 10% default
        tax_amount = base_amount * tax_rate
        total_amount = base_amount + tax_amount
        
        return {
            'base_amount': round(base_amount, 2),
            'tax_amount': round(tax_amount, 2),
            'total_amount': round(total_amount, 2),
            'currency': rate.currency,
            'rate_applied': float(rate.base_rate),
            'rate_type': rate_type,
            'rate_id': str(rate.id),
            'duration_hours': round(duration_hours, 2)
        }
    
    def to_dict(self, include_zone: bool = False) -> Dict[str, Any]:
        """Convert spot to dictionary."""
        data = {
            'id': str(self.id),
            'zone_id': str(self.zone_id),
            'spot_number': self.spot_number,
            'level': self.level,
            'row': self.row,
            'column': self.column,
            'coordinates': {
                'x': self.coordinates_x,
                'y': self.coordinates_y,
                'z': self.coordinates_z
            } if any([self.coordinates_x, self.coordinates_y]) else None,
            'spot_type': self.spot_type,
            'status': self.status,
            'vehicle_type': self.vehicle_type,
            'dimensions': {
                'width_cm': self.width_cm,
                'length_cm': self.length_cm,
                'height_cm': self.height_cm
            } if any([self.width_cm, self.length_cm]) else None,
            'max_weight_kg': self.max_weight_kg,
            'features': {
                'has_ev_charger': self.has_ev_charger,
                'ev_charger_type': self.ev_charger_type,
                'ev_charger_power_kw': self.ev_charger_power_kw,
                'is_handicapped': self.is_handicapped,
                'is_covered': self.is_covered,
                'is_near_elevator': self.is_near_elevator,
                'is_near_entrance': self.is_near_entrance
            },
            'current_vehicle_id': str(self.current_vehicle_id) if self.current_vehicle_id else None,
            'current_session_id': str(self.current_session_id) if self.current_session_id else None,
            'current_reservation_id': str(self.current_reservation_id) if self.current_reservation_id else None,
            'rates': {
                'hourly': float(self.hourly_rate) if self.hourly_rate else None,
                'daily': float(self.daily_rate) if self.daily_rate else None,
                'monthly': float(self.monthly_rate) if self.monthly_rate else None
            },
            'occupancy': {
                'last_occupied_at': self.last_occupied_at.isoformat() if self.last_occupied_at else None,
                'last_vacated_at': self.last_vacated_at.isoformat() if self.last_vacated_at else None,
                'current_duration_minutes': self.current_occupancy_duration,
                'occupancy_count_today': self.occupancy_count_today,
                'total_occupancy_count': self.total_occupancy_count
            },
            'image_url': self.image_url,
            'notes': self.notes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_zone and self.zone:
            data['zone'] = self.zone.to_dict()
        
        return data
    
    def __repr__(self) -> str:
        return f"<ParkingSpot(id={self.id}, zone={self.zone_id}, number={self.spot_number}, status={self.status})>"


class ParkingRate(Base):
    """
    Parking rate configurations.
    
    Defines pricing for parking spots based on various factors including
    spot type, vehicle type, time of day, and duration.
    """
    
    __tablename__ = 'parking_rates'
    __table_args__ = (
        Index('ix_rates_zone_type', 'zone_id', 'spot_type'),
        Index('ix_rates_vehicle_type', 'vehicle_type'),
        Index('ix_rates_effective_date', 'effective_from', 'effective_to'),
        Index('ix_rates_is_active', 'is_active'),
        {'comment': 'Parking rate configurations'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_zones.id', ondelete='CASCADE'),
        comment='Zone this rate applies to (null for all zones)'
    )
    
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='CASCADE'),
        comment='Specific spot this rate applies to'
    )
    
    spot_type = Column(
        String(20),
        comment='Spot type this rate applies to'
    )
    
    vehicle_type = Column(
        String(20),
        comment='Vehicle type this rate applies to'
    )
    
    rate_type = Column(
        String(20),
        nullable=False,
        comment='Type of rate: hourly, daily, weekly, monthly, yearly, event'
    )
    
    name = Column(
        String(100),
        nullable=False,
        comment='Rate name'
    )
    
    description = Column(
        Text,
        comment='Rate description'
    )
    
    # Rate details
    base_rate = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Base rate amount'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        server_default='USD',
        comment='Currency code'
    )
    
    unit = Column(
        String(20),
        nullable=False,
        comment='Billing unit: hour, day, week, month, year'
    )
    
    min_units = Column(
        Integer,
        server_default='1',
        comment='Minimum number of units'
    )
    
    max_units = Column(
        Integer,
        comment='Maximum number of units'
    )
    
    grace_period_minutes = Column(
        Integer,
        server_default='15',
        comment='Grace period in minutes'
    )
    
    # Capping
    has_maximum_cap = Column(
        Boolean,
        server_default='false',
        comment='Whether there is a maximum cap'
    )
    
    maximum_cap_amount = Column(
        Numeric(10, 2),
        comment='Maximum amount for the period'
    )
    
    maximum_cap_period = Column(
        String(20),
        comment='Period for maximum cap: day, week, month'
    )
    
    # Special rates
    has_weekend_rate = Column(
        Boolean,
        server_default='false',
        comment='Whether weekend rate applies'
    )
    
    weekend_rate = Column(
        Numeric(10, 2),
        comment='Weekend rate'
    )
    
    has_night_rate = Column(
        Boolean,
        server_default='false',
        comment='Whether night rate applies'
    )
    
    night_rate = Column(
        Numeric(10, 2),
        comment='Night rate'
    )
    
    night_start_time = Column(
        Time,
        comment='Night rate start time'
    )
    
    night_end_time = Column(
        Time,
        comment='Night rate end time'
    )
    
    # Validity
    effective_from = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Rate effective from this time'
    )
    
    effective_to = Column(
        DateTime(timezone=True),
        comment='Rate effective until this time'
    )
    
    priority = Column(
        Integer,
        server_default='0',
        comment='Priority for rate selection (higher = more priority)'
    )
    
    # Status
    is_active = Column(
        Boolean,
        nullable=False,
        server_default='true',
        comment='Whether rate is active'
    )
    
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # Audit
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Relationships
    zone = relationship('ParkingZone', back_populates='rates')
    spot = relationship('ParkingSpot', back_populates='rates')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rate to dictionary."""
        return {
            'id': str(self.id),
            'zone_id': str(self.zone_id) if self.zone_id else None,
            'spot_id': str(self.spot_id) if self.spot_id else None,
            'spot_type': self.spot_type,
            'vehicle_type': self.vehicle_type,
            'rate_type': self.rate_type,
            'name': self.name,
            'description': self.description,
            'base_rate': float(self.base_rate),
            'currency': self.currency,
            'unit': self.unit,
            'min_units': self.min_units,
            'max_units': self.max_units,
            'grace_period_minutes': self.grace_period_minutes,
            'has_maximum_cap': self.has_maximum_cap,
            'maximum_cap_amount': float(self.maximum_cap_amount) if self.maximum_cap_amount else None,
            'maximum_cap_period': self.maximum_cap_period,
            'has_weekend_rate': self.has_weekend_rate,
            'weekend_rate': float(self.weekend_rate) if self.weekend_rate else None,
            'has_night_rate': self.has_night_rate,
            'night_rate': float(self.night_rate) if self.night_rate else None,
            'night_start_time': self.night_start_time.isoformat() if self.night_start_time else None,
            'night_end_time': self.night_end_time.isoformat() if self.night_end_time else None,
            'effective_from': self.effective_from.isoformat() if self.effective_from else None,
            'effective_to': self.effective_to.isoformat() if self.effective_to else None,
            'priority': self.priority,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ParkingRate(id={self.id}, name={self.name}, rate={self.base_rate})>"


class SpotSensor(Base):
    """
    IoT sensors monitoring parking spot occupancy.
    
    Tracks physical sensors installed at parking spots for real-time
    occupancy detection and monitoring.
    """
    
    __tablename__ = 'spot_sensors'
    __table_args__ = (
        Index('ix_sensors_spot', 'spot_id'),
        Index('ix_sensors_serial', 'serial_number', unique=True),
        Index('ix_sensors_mac', 'mac_address'),
        Index('ix_sensors_status', 'status'),
        Index('ix_sensors_type', 'sensor_type'),
        Index('ix_sensors_last_comm', 'last_communication'),
        {'comment': 'IoT sensors for spot occupancy detection'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='CASCADE'),
        nullable=False
    )
    
    sensor_type = Column(
        String(50),
        nullable=False,
        comment='Type of sensor'
    )
    
    sensor_model = Column(
        String(100),
        comment='Sensor model'
    )
    
    manufacturer = Column(
        String(100),
        comment='Sensor manufacturer'
    )
    
    serial_number = Column(
        String(100),
        unique=True,
        comment='Sensor serial number'
    )
    
    firmware_version = Column(
        String(50),
        comment='Firmware version'
    )
    
    hardware_version = Column(
        String(50),
        comment='Hardware version'
    )
    
    ip_address = Column(
        String(45),
        comment='IP address of sensor'
    )
    
    mac_address = Column(
        String(17),
        comment='MAC address'
    )
    
    status = Column(
        String(20),
        nullable=False,
        server_default='active',
        comment='Sensor status'
    )
    
    battery_level = Column(
        Integer,
        comment='Battery level percentage'
    )
    
    last_communication = Column(
        DateTime(timezone=True),
        comment='Last communication timestamp'
    )
    
    last_calibration = Column(
        DateTime(timezone=True),
        comment='Last calibration timestamp'
    )
    
    reading_frequency_seconds = Column(
        Integer,
        server_default='5',
        comment='Reading frequency in seconds'
    )
    
    current_value = Column(
        Float,
        comment='Current sensor reading value'
    )
    
    current_status = Column(
        String(20),
        comment='Current detected status (occupied/available)'
    )
    
    accuracy_percent = Column(
        Float,
        comment='Sensor accuracy percentage'
    )
    
    temperature_celsius = Column(
        Float,
        comment='Sensor temperature reading'
    )
    
    error_count = Column(
        Integer,
        server_default='0',
        comment='Number of errors'
    )
    
    last_error = Column(
        Text,
        comment='Last error message'
    )
    
    last_error_time = Column(
        DateTime(timezone=True),
        comment='Last error timestamp'
    )
    
    maintenance_due = Column(
        DateTime(timezone=True),
        comment='Maintenance due date'
    )
    
    calibration_due = Column(
        DateTime(timezone=True),
        comment='Calibration due date'
    )
    
    configuration = Column(
        JSONB,
        comment='Sensor configuration'
    )
    
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    installed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Installation timestamp'
    )
    
    installed_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who installed sensor'
    )
    
    removed_at = Column(
        DateTime(timezone=True),
        comment='Removal timestamp'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    spot = relationship('ParkingSpot', back_populates='sensors')
    
    def record_reading(self, value: float, status: str) -> None:
        """
        Record a sensor reading.
        
        Args:
            value: Sensor reading value
            status: Detected status (occupied/available)
        """
        self.current_value = value
        self.current_status = status
        self.last_communication = datetime.now()
    
    def report_error(self, error_message: str) -> None:
        """
        Report sensor error.
        
        Args:
            error_message: Error description
        """
        self.error_count += 1
        self.last_error = error_message
        self.last_error_time = datetime.now()
        self.status = 'faulty'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sensor to dictionary."""
        return {
            'id': str(self.id),
            'spot_id': str(self.spot_id),
            'sensor_type': self.sensor_type,
            'sensor_model': self.sensor_model,
            'manufacturer': self.manufacturer,
            'serial_number': self.serial_number,
            'firmware_version': self.firmware_version,
            'status': self.status,
            'battery_level': self.battery_level,
            'last_communication': self.last_communication.isoformat() if self.last_communication else None,
            'current_value': self.current_value,
            'current_status': self.current_status,
            'accuracy_percent': self.accuracy_percent,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
            'maintenance_due': self.maintenance_due.isoformat() if self.maintenance_due else None,
            'installed_at': self.installed_at.isoformat() if self.installed_at else None,
            'removed_at': self.removed_at.isoformat() if self.removed_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SpotSensor(id={self.id}, type={self.sensor_type}, serial={self.serial_number})>"


class SpotMaintenance(Base):
    """
    Maintenance schedule and history for parking spots.
    
    Tracks maintenance activities, schedules, and costs for parking spots.
    """
    
    __tablename__ = 'spot_maintenance'
    __table_args__ = (
        Index('ix_maintenance_spot', 'spot_id'),
        Index('ix_maintenance_status', 'status'),
        Index('ix_maintenance_type', 'maintenance_type'),
        Index('ix_maintenance_schedule', 'scheduled_start', 'scheduled_end'),
        Index('ix_maintenance_assigned', 'assigned_to'),
        {'comment': 'Maintenance records for parking spots'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='CASCADE'),
        nullable=False
    )
    
    maintenance_type = Column(
        String(50),
        nullable=False,
        comment='Type of maintenance'
    )
    
    status = Column(
        String(20),
        nullable=False,
        server_default='scheduled',
        comment='Maintenance status'
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
    
    scheduled_start = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Scheduled start time'
    )
    
    scheduled_end = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Scheduled end time'
    )
    
    actual_start = Column(
        DateTime(timezone=True),
        comment='Actual start time'
    )
    
    actual_end = Column(
        DateTime(timezone=True),
        comment='Actual end time'
    )
    
    estimated_duration_minutes = Column(
        Integer,
        comment='Estimated duration in minutes'
    )
    
    actual_duration_minutes = Column(
        Integer,
        comment='Actual duration in minutes'
    )
    
    assigned_to = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='Staff assigned to maintenance'
    )
    
    vendor_name = Column(
        String(200),
        comment='External vendor name'
    )
    
    vendor_contact = Column(
        String(100),
        comment='Vendor contact information'
    )
    
    cost_estimate = Column(
        Numeric(10, 2),
        comment='Estimated cost'
    )
    
    actual_cost = Column(
        Numeric(10, 2),
        comment='Actual cost'
    )
    
    parts_used = Column(
        JSONB,
        comment='Parts used in maintenance'
    )
    
    notes = Column(
        Text,
        comment='Maintenance notes'
    )
    
    completion_notes = Column(
        Text,
        comment='Completion notes'
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
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL')
    )
    
    completed_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL')
    )
    
    metadata = Column(
        JSONB,
        server_default='{}'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    spot = relationship('ParkingSpot', back_populates='maintenance_records')
    assignee = relationship('User', foreign_keys=[assigned_to])
    creator = relationship('User', foreign_keys=[created_by])
    completer = relationship('User', foreign_keys=[completed_by])
    
    def start(self) -> None:
        """Start maintenance."""
        self.status = 'in_progress'
        self.actual_start = datetime.now()
    
    def complete(self) -> None:
        """Complete maintenance."""
        self.status = 'completed'
        self.actual_end = datetime.now()
        if self.actual_start:
            delta = self.actual_end - self.actual_start
            self.actual_duration_minutes = int(delta.total_seconds() / 60)
    
    def cancel(self, reason: str) -> None:
        """Cancel maintenance."""
        self.status = 'cancelled'
        self.notes = f"Cancelled: {reason}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert maintenance record to dictionary."""
        return {
            'id': str(self.id),
            'spot_id': str(self.spot_id),
            'maintenance_type': self.maintenance_type,
            'status': self.status,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'scheduled_start': self.scheduled_start.isoformat() if self.scheduled_start else None,
            'scheduled_end': self.scheduled_end.isoformat() if self.scheduled_end else None,
            'actual_start': self.actual_start.isoformat() if self.actual_start else None,
            'actual_end': self.actual_end.isoformat() if self.actual_end else None,
            'estimated_duration_minutes': self.estimated_duration_minutes,
            'actual_duration_minutes': self.actual_duration_minutes,
            'assigned_to': str(self.assigned_to) if self.assigned_to else None,
            'vendor_name': self.vendor_name,
            'cost_estimate': float(self.cost_estimate) if self.cost_estimate else None,
            'actual_cost': float(self.actual_cost) if self.actual_cost else None,
            'follow_up_required': self.follow_up_required,
            'follow_up_date': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SpotMaintenance(id={self.id}, spot={self.spot_id}, type={self.maintenance_type})>"


class SpotOccupancyHistory(Base):
    """
    Historical record of spot occupancy.
    
    Tracks when spots were occupied, by which vehicles, and for how long.
    Used for analytics, reporting, and auditing.
    """
    
    __tablename__ = 'spot_occupancy_history'
    __table_args__ = (
        Index('ix_occupancy_history_spot', 'spot_id'),
        Index('ix_occupancy_history_session', 'session_id'),
        Index('ix_occupancy_history_time_range', 'start_time', 'end_time'),
        Index('ix_occupancy_history_vehicle', 'vehicle_id'),
        Index('ix_occupancy_history_license', 'license_plate'),
        Index('ix_occupancy_history_spot_time', 'spot_id', 'start_time'),
        {'comment': 'Historical occupancy records'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='CASCADE'),
        nullable=False
    )
    
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_sessions.id', ondelete='SET NULL'),
        comment='Associated parking session'
    )
    
    status = Column(
        String(20),
        nullable=False,
        comment='Status during this period'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='SET NULL'),
        comment='Vehicle that occupied the spot'
    )
    
    license_plate = Column(
        String(20),
        comment='License plate at time of occupancy'
    )
    
    start_time = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Occupancy start time'
    )
    
    end_time = Column(
        DateTime(timezone=True),
        comment='Occupancy end time'
    )
    
    duration_minutes = Column(
        Integer,
        comment='Occupancy duration in minutes'
    )
    
    sensor_id = Column(
        UUID(as_uuid=True),
        ForeignKey('spot_sensors.id', ondelete='SET NULL'),
        comment='Sensor that detected this occupancy'
    )
    
    sensor_value = Column(
        Float,
        comment='Sensor reading at start'
    )
    
    confidence = Column(
        Float,
        comment='Confidence level of detection'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    spot = relationship('ParkingSpot', back_populates='occupancy_history')
    session = relationship('ParkingSession')
    vehicle = relationship('Vehicle')
    sensor = relationship('SpotSensor')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert history record to dictionary."""
        return {
            'id': str(self.id),
            'spot_id': str(self.spot_id),
            'session_id': str(self.session_id) if self.session_id else None,
            'status': self.status,
            'vehicle_id': str(self.vehicle_id) if self.vehicle_id else None,
            'license_plate': self.license_plate,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_minutes': self.duration_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SpotOccupancyHistory(id={self.id}, spot={self.spot_id}, start={self.start_time})>"


# =========================================================================
# EVENT LISTENERS
# =========================================================================

@event.listens_for(ParkingSpot, 'after_insert')
@event.listens_for(ParkingSpot, 'after_update')
@event.listens_for(ParkingSpot, 'after_delete')
def update_zone_counts(mapper, connection, target):
    """
    Update zone spot counts when spots change.
    """
    if target.zone_id:
        # This would typically be handled by a database trigger
        # For ORM-level, we'd need to execute an update statement
        connection.execute(
            ParkingZone.__table__.update().where(
                ParkingZone.id == target.zone_id
            ).values(
                total_spots=select(func.count(ParkingSpot.id)).where(
                    ParkingSpot.zone_id == target.zone_id
                ),
                available_spots=select(func.count(ParkingSpot.id)).where(
                    ParkingSpot.zone_id == target.zone_id,
                    ParkingSpot.status == 'available'
                ),
                occupied_spots=select(func.count(ParkingSpot.id)).where(
                    ParkingSpot.zone_id == target.zone_id,
                    ParkingSpot.status == 'occupied'
                ),
                reserved_spots=select(func.count(ParkingSpot.id)).where(
                    ParkingSpot.zone_id == target.zone_id,
                    ParkingSpot.status == 'reserved'
                ),
                maintenance_spots=select(func.count(ParkingSpot.id)).where(
                    ParkingSpot.zone_id == target.zone_id,
                    ParkingSpot.status == 'maintenance'
                ),
                updated_at=func.now()
            )
        )


@event.listens_for(ParkingSpot, 'before_update')
def record_occupancy_change(mapper, connection, target):
    """
    Record occupancy changes in history.
    """
    # Get old values
    old_status = mapper.get_history(target, 'status').deleted[0] if mapper.get_history(target, 'status').deleted else None
    new_status = target.status