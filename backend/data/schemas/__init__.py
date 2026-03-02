"""
SQLAlchemy ORM schemas/models for parking management system.
"""

import uuid
from datetime import datetime, time
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    Enum,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates

from utils.helpers import generate_uuid7, get_current_time
from .base import BaseModel, TenantModel, AuditModel, VersionedModel


class Organization(TenantModel):
    """Organization/tenant model."""
    
    __tablename__ = 'organizations'
    
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    tax_id = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(JSONB, default={}, nullable=True)
    
    # Relationships
    parking_lots = relationship("ParkingLot", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    vehicles = relationship("Vehicle", back_populates="organization")
    rates = relationship("Rate", back_populates="organization", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Organization id={self.id} name={self.name} code={self.code}>"


class User(BaseModel):
    """User model for authentication and authorization."""
    
    __tablename__ = 'users'
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(50), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    preferences = Column(JSONB, default={}, nullable=True)
    
    # Foreign keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user")
    vehicles = relationship("Vehicle", back_populates="owner")
    parking_sessions_created = relationship("ParkingSession", foreign_keys="ParkingSession.created_by_id", back_populates="created_by_user")
    parking_sessions_ended = relationship("ParkingSession", foreign_keys="ParkingSession.ended_by_id", back_populates="ended_by_user")
    payments_processed = relationship("Payment", foreign_keys="Payment.processed_by_id", back_populates="processed_by_user")
    notifications = relationship("Notification", back_populates="user")
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format."""
        if email and '@' not in email:
            raise ValueError("Invalid email format")
        return email.lower()
    
    def __repr__(self):
        return f"<User id={self.id} username={self.username} email={self.email}>"


class Role(BaseModel):
    """Role model for RBAC."""
    
    __tablename__ = 'roles'
    
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(500), nullable=True)
    permissions = Column(JSONB, default=[], nullable=False)  # List of permission strings
    is_system_role = Column(Boolean, default=False, nullable=False)  # Cannot modify system roles
    
    # Relationships
    users = relationship("UserRole", back_populates="role")
    
    def __repr__(self):
        return f"<Role id={self.id} name={self.name}>"


class UserRole(BaseModel):
    """User-role association model."""
    
    __tablename__ = 'user_roles'
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")
    organization = relationship("Organization")
    
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', 'organization_id', name='uq_user_role_org'),
    )
    
    def __repr__(self):
        return f"<UserRole user_id={self.user_id} role_id={self.role_id}>"


class ParkingLot(TenantModel):
    """Parking lot model."""
    
    __tablename__ = 'parking_lots'
    
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Location
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False)
    postal_code = Column(String(20), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Contact
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    
    # Operating hours
    opening_time = Column(Time, nullable=True)
    closing_time = Column(Time, nullable=True)
    is_24h = Column(Boolean, default=False, nullable=False)
    
    # Capacity
    total_spaces = Column(Integer, nullable=False)
    available_spaces = Column(Integer, nullable=False)
    reserved_spaces = Column(Integer, default=0, nullable=False)
    
    # Pricing
    currency = Column(String(3), default='USD', nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String(50), default='operational', nullable=False)  # operational, maintenance, closed
    
    # Configuration
    settings = Column(JSONB, default={}, nullable=True)
    
    # Foreign keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    manager_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="parking_lots")
    manager = relationship("User", foreign_keys=[manager_id])
    levels = relationship("ParkingLevel", back_populates="parking_lot", cascade="all, delete-orphan")
    entrances = relationship("EntranceExit", back_populates="parking_lot", cascade="all, delete-orphan")
    cameras = relationship("Camera", back_populates="parking_lot", cascade="all, delete-orphan")
    gates = relationship("Gate", back_populates="parking_lot", cascade="all, delete-orphan")
    sensors = relationship("Sensor", back_populates="parking_lot", cascade="all, delete-orphan")
    rates = relationship("Rate", back_populates="parking_lot")
    parking_sessions = relationship("ParkingSession", back_populates="parking_lot")
    reservations = relationship("Reservation", back_populates="parking_lot")
    blacklisted_vehicles = relationship("BlacklistedVehicle", back_populates="parking_lot")
    
    __table_args__ = (
        UniqueConstraint('organization_id', 'code', name='uq_organization_lot_code'),
        Index('ix_parking_lots_status', 'status'),
        Index('ix_parking_lots_location', 'city', 'state', 'country'),
    )
    
    @validates('total_spaces', 'available_spaces')
    def validate_spaces(self, key, value):
        """Validate space counts."""
        if key == 'available_spaces' and value > self.total_spaces:
            raise ValueError("Available spaces cannot exceed total spaces")
        if value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    def __repr__(self):
        return f"<ParkingLot id={self.id} name={self.name} code={self.code}>"


class ParkingLevel(BaseModel):
    """Parking level/floor model."""
    
    __tablename__ = 'parking_levels'
    
    level_number = Column(Integer, nullable=False)
    name = Column(String(100), nullable=True)
    code = Column(String(50), nullable=False)
    total_spaces = Column(Integer, nullable=False)
    available_spaces = Column(Integer, nullable=False)
    reserved_spaces = Column(Integer, default=0, nullable=False)
    height_limit = Column(Float, nullable=True)  # in meters
    weight_limit = Column(Float, nullable=True)  # in kg
    is_covered = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(JSONB, default={}, nullable=True)
    
    # Foreign keys
    parking_lot_id = Column(UUID(as_uuid=True), ForeignKey('parking_lots.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    parking_lot = relationship("ParkingLot", back_populates="levels")
    spaces = relationship("ParkingSpace", back_populates="level", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('parking_lot_id', 'level_number', name='uq_lot_level_number'),
        UniqueConstraint('parking_lot_id', 'code', name='uq_lot_level_code'),
    )
    
    @validates('total_spaces', 'available_spaces')
    def validate_spaces(self, key, value):
        """Validate space counts."""
        if key == 'available_spaces' and value > self.total_spaces:
            raise ValueError("Available spaces cannot exceed total spaces")
        if value < 0:
            raise ValueError(f"{key} cannot be negative")
        return value
    
    def __repr__(self):
        return f"<ParkingLevel id={self.id} level={self.level_number} lot_id={self.parking_lot_id}>"


class ParkingSpace(BaseModel):
    """Individual parking space model."""
    
    __tablename__ = 'parking_spaces'
    
    space_number = Column(String(50), nullable=False)
    space_type = Column(String(50), nullable=False)  # regular, handicapped, electric, compact, motorcycle, bus
    status = Column(String(50), default='available', nullable=False)  # available, occupied, reserved, maintenance
    is_covered = Column(Boolean, default=False, nullable=False)
    is_reserved = Column(Boolean, default=False, nullable=False)
    is_handicapped = Column(Boolean, default=False, nullable=False)
    is_electric = Column(Boolean, default=False, nullable=False)
    charging_capacity = Column(Float, nullable=True)  # in kW for electric spots
    width = Column(Float, nullable=True)  # in meters
    length = Column(Float, nullable=True)  # in meters
    height_limit = Column(Float, nullable=True)  # in meters
    current_vehicle_id = Column(UUID(as_uuid=True), nullable=True)
    sensor_id = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    settings = Column(JSONB, default={}, nullable=True)
    
    # Foreign keys
    level_id = Column(UUID(as_uuid=True), ForeignKey('parking_levels.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    level = relationship("ParkingLevel", back_populates="spaces")
    current_session = relationship("ParkingSession", uselist=False, back_populates="parking_space")
    reservations = relationship("Reservation", back_populates="parking_space")
    sensor_data = relationship("SensorData", back_populates="parking_space")
    
    __table_args__ = (
        UniqueConstraint('level_id', 'space_number', name='uq_level_space_number'),
        Index('ix_parking_spaces_status', 'status'),
        Index('ix_parking_spaces_type', 'space_type'),
        Index('ix_parking_spaces_sensor_id', 'sensor_id'),
    )
    
    def __repr__(self):
        return f"<ParkingSpace id={self.id} number={self.space_number} status={self.status}>"


class EntranceExit(BaseModel):
    """Parking lot entrance/exit points."""
    
    __tablename__ = 'entrance_exits'
    
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False)
    type = Column(String(20), nullable=False)  # entrance, exit, both
    is_active = Column(Boolean, default=True, nullable=False)
    has_gate = Column(Boolean, default=True, nullable=False)
    has_camera = Column(Boolean, default=True, nullable=False)
    has_ticket_dispenser = Column(Boolean, default=False, nullable=False)
    has_payment_terminal = Column(Boolean, default=False, nullable=False)
    
    # Foreign keys
    parking_lot_id = Column(UUID(as_uuid=True), ForeignKey('parking_lots.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    parking_lot = relationship("ParkingLot", back_populates="entrances")
    gates = relationship("Gate", back_populates="entrance_exit")
    cameras = relationship("Camera", back_populates="entrance_exit")
    
    __table_args__ = (
        UniqueConstraint('parking_lot_id', 'code', name='uq_lot_entrance_code'),
    )
    
    def __repr__(self):
        return f"<EntranceExit id={self.id} name={self.name} type={self.type}>"


class Gate(BaseModel):
    """Gate controller model."""
    
    __tablename__ = 'gates'
    
    name = Column(String(100), nullable=False)
    gate_type = Column(String(50), nullable=False)  # entrance, exit
    status = Column(String(50), default='closed', nullable=False)  # open, closed, opening, closing, maintenance
    control_mode = Column(String(50), default='automatic', nullable=False)  # automatic, manual, remote
    last_activity = Column(DateTime(timezone=True), nullable=True)
    
    # Foreign keys
    parking_lot_id = Column(UUID(as_uuid=True), ForeignKey('parking_lots.id', ondelete='CASCADE'), nullable=False)
    entrance_exit_id = Column(UUID(as_uuid=True), ForeignKey('entrance_exits.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    parking_lot = relationship("ParkingLot", back_populates="gates")
    entrance_exit = relationship("EntranceExit", back_populates="gates")
    events = relationship("GateEvent", back_populates="gate")
    
    def __repr__(self):
        return f"<Gate id={self.id} name={self.name} status={self.status}>"


class Camera(BaseModel):
    """Surveillance camera model."""
    
    __tablename__ = 'cameras'
    
    name = Column(String(100), nullable=False)
    camera_type = Column(String(50), nullable=False)  # entrance, exit, overview, lpr
    ip_address = Column(String(50), nullable=True)
    rtsp_url = Column(String(500), nullable=True)
    status = Column(String(50), default='active', nullable=False)  # active, inactive, maintenance
    last_online = Column(DateTime(timezone=True), nullable=True)
    settings = Column(JSONB, default={}, nullable=True)
    
    # Foreign keys
    parking_lot_id = Column(UUID(as_uuid=True), ForeignKey('parking_lots.id', ondelete='CASCADE'), nullable=False)
    entrance_exit_id = Column(UUID(as_uuid=True), ForeignKey('entrance_exits.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    parking_lot = relationship("ParkingLot", back_populates="cameras")
    entrance_exit = relationship("EntranceExit", back_populates="cameras")
    events = relationship("CameraEvent", back_populates="camera")
    images = relationship("CameraImage", back_populates="camera")
    
    def __repr__(self):
        return f"<Camera id={self.id} name={self.name} type={self.camera_type}>"


class Sensor(BaseModel):
    """Parking sensor model."""
    
    __tablename__ = 'sensors'
    
    sensor_id = Column(String(100), unique=True, nullable=False)
    sensor_type = Column(String(50), nullable=False)  # ultrasonic, magnetic, camera, radar
    status = Column(String(50), default='active', nullable=False)
    battery_level = Column(Integer, nullable=True)  # percentage
    last_reading = Column(DateTime(timezone=True), nullable=True)
    firmware_version = Column(String(50), nullable=True)
    settings = Column(JSONB, default={}, nullable=True)
    
    # Foreign keys
    parking_lot_id = Column(UUID(as_uuid=True), ForeignKey('parking_lots.id', ondelete='CASCADE'), nullable=False)
    current_space_id = Column(UUID(as_uuid=True), ForeignKey('parking_spaces.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    parking_lot = relationship("ParkingLot", back_populates="sensors")
    parking_space = relationship("ParkingSpace", foreign_keys=[current_space_id])
    data = relationship("SensorData", back_populates="sensor", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Sensor id={self.id} sensor_id={self.sensor_id} type={self.sensor_type}>"


class SensorData(BaseModel):
    """Sensor reading data."""
    
    __tablename__ = 'sensor_data'
    
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    is_occupied = Column(Boolean, nullable=True)
    
    # Foreign keys
    sensor_id = Column(UUID(as_uuid=True), ForeignKey('sensors.id', ondelete='CASCADE'), nullable=False)
    parking_space_id = Column(UUID(as_uuid=True), ForeignKey('parking_spaces.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    sensor = relationship("Sensor", back_populates="data")
    parking_space = relationship("ParkingSpace", back_populates="sensor_data")
    
    __table_args__ = (
        Index('ix_sensor_data_sensor_timestamp', 'sensor_id', 'timestamp'),
    )


class Vehicle(BaseModel):
    """Vehicle model."""
    
    __tablename__ = 'vehicles'
    
    license_plate = Column(String(20), nullable=False, index=True)
    license_plate_normalized = Column(String(20), nullable=False, index=True)
    license_plate_state = Column(String(50), nullable=True)
    license_plate_country = Column(String(3), nullable=True)
    make = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    color = Column(String(50), nullable=True)
    year = Column(Integer, nullable=True)
    vehicle_type = Column(String(50), default='car', nullable=False)  # car, motorcycle, truck, bus, van
    height = Column(Float, nullable=True)  # in meters
    length = Column(Float, nullable=True)  # in meters
    width = Column(Float, nullable=True)  # in meters
    weight = Column(Float, nullable=True)  # in kg
    is_electric = Column(Boolean, default=False, nullable=False)
    is_handicapped = Column(Boolean, default=False, nullable=False)
    is_resident = Column(Boolean, default=False, nullable=False)
    registration_number = Column(String(100), nullable=True)
    registration_expiry = Column(Date, nullable=True)
    insurance_company = Column(String(200), nullable=True)
    insurance_policy = Column(String(100), nullable=True)
    insurance_expiry = Column(Date, nullable=True)
    image_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Foreign keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="vehicles")
    owner = relationship("User", back_populates="vehicles")
    parking_sessions = relationship("ParkingSession", back_populates="vehicle")
    reservations = relationship("Reservation", back_populates="vehicle")
    blacklist_entries = relationship("BlacklistedVehicle", back_populates="vehicle")
    
    __table_args__ = (
        UniqueConstraint('organization_id', 'license_plate', name='uq_org_license_plate'),
        Index('ix_vehicles_owner_id', 'owner_id'),
        Index('ix_vehicles_type', 'vehicle_type'),
    )
    
    @validates('license_plate')
    def normalize_license_plate(self, key, value):
        """Normalize license plate to uppercase."""
        if value:
            value = value.upper().strip()
        return value
    
    def __repr__(self):
        return f"<Vehicle id={self.id} plate={self.license_plate}>"


class Rate(TenantModel):
    """Parking rate model."""
    
    __tablename__ = 'rates'
    
    name = Column(String(200), nullable=False)
    rate_type = Column(String(50), nullable=False)  # hourly, daily, weekly, monthly, flat, progressive
    vehicle_types = Column(JSONB, nullable=False)  # List of vehicle types this rate applies to
    time_rules = Column(JSONB, nullable=True)  # Time-based rules (days of week, hours)
    
    # Rate structure
    base_rate = Column(Float, nullable=False)  # Base amount
    rate_unit = Column(String(20), default='hour', nullable=False)  # hour, minute, day, week, month
    currency = Column(String(3), default='USD', nullable=False)
    
    # Progressive rates (for progressive rate type)
    tiers = Column(JSONB, nullable=True)  # List of {min_time, max_time, rate}
    
    # Flat rates (for flat rate type)
    flat_amount = Column(Float, nullable=True)
    max_duration = Column(Integer, nullable=True)  # in minutes
    
    # Grace periods
    grace_period_minutes = Column(Integer, default=15, nullable=False)
    
    # Applicability
    is_active = Column(Boolean, default=True, nullable=False)
    is_weekend_rate = Column(Boolean, default=False, nullable=False)
    is_holiday_rate = Column(Boolean, default=False, nullable=False)
    is_special_event_rate = Column(Boolean, default=False, nullable=False)
    
    # Validity period
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    
    # Foreign keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    parking_lot_id = Column(UUID(as_uuid=True), ForeignKey('parking_lots.id', ondelete='CASCADE'), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="rates")
    parking_lot = relationship("ParkingLot", back_populates="rates")
    
    __table_args__ = (
        Index('ix_rates_organization_active', 'organization_id', 'is_active'),
        Index('ix_rates_validity', 'valid_from', 'valid_to'),
    )
    
    def __repr__(self):
        return f"<Rate id={self.id} name={self.name} type={self.rate_type}>"


class ParkingSession(BaseModel):
    """Parking session model."""
    
    __tablename__ = 'parking_sessions'
    
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    ticket_number = Column(String(100), unique=True, nullable=True, index=True)
    
    # Timing
    entry_time = Column(DateTime(timezone=True), nullable=False, index=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    expected_exit_time = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    
    # Status
    status = Column(String(50), default='active', nullable=False, index=True)  # active, completed, cancelled, expired
    is_grace_period = Column(Boolean, default=False, nullable=False)
    grace_period_ends = Column(DateTime(timezone=True), nullable=True)
    
    # Entry details
    entry_method = Column(String(50), nullable=False)  # ticket, rfid, lpr, mobile
    entry_gate_id = Column(UUID(as_uuid=True), nullable=True)
    entry_camera_id = Column(UUID(as_uuid=True), nullable=True)
    entry_image_url = Column(String(500), nullable=True)
    entry_lpr_confidence = Column(Float, nullable=True)
    entry_lpr_plate = Column(String(20), nullable=True)
    
    # Exit details
    exit_method = Column(String(50), nullable=True)
    exit_gate_id = Column(UUID(as_uuid=True), nullable=True)
    exit_camera_id = Column(UUID(as_uuid=True), nullable=True)
    exit_image_url = Column(String(500), nullable=True)
    exit_lpr_confidence = Column(Float, nullable=True)
    exit_lpr_plate = Column(String(20), nullable=True)
    
    # Billing
    rate_id = Column(UUID(as_uuid=True), nullable=True)
    rate_applied = Column(JSONB, nullable=True)  # Snapshot of rate at entry
    base_amount = Column(Float, nullable=True)
    tax_amount = Column(Float, nullable=True)
    discount_amount = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=True)
    currency = Column(String(3), default='USD', nullable=False)
    
    # Payment
    payment_status = Column(String(50), default='pending', nullable=False)
    payment_time = Column(DateTime(timezone=True), nullable=True)
    payment_method = Column(String(50), nullable=True)
    
    # Foreign keys
    parking_lot_id = Column(UUID(as_uuid=True), ForeignKey('parking_lots.id', ondelete='CASCADE'), nullable=False)
    parking_space_id = Column(UUID(as_uuid=True), ForeignKey('parking_spaces.id', ondelete='SET NULL'), nullable=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='SET NULL'), nullable=True)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='SET NULL'), nullable=True)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    ended_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    parking_lot = relationship("ParkingLot", back_populates="parking_sessions")
    parking_space = relationship("ParkingSpace", back_populates="current_session")
    vehicle = relationship("Vehicle", back_populates="parking_sessions")
    reservation = relationship("Reservation", back_populates="parking_session")
    created_by_user = relationship("User", foreign_keys=[created_by_id], back_populates="parking_sessions_created")
    ended_by_user = relationship("User", foreign_keys=[ended_by_id], back_populates="parking_sessions_ended")
    payments = relationship("Payment", back_populates="parking_session")
    
    __table_args__ = (
        Index('ix_parking_sessions_lot_status', 'parking_lot_id', 'status'),
        Index('ix_parking_sessions_vehicle', 'vehicle_id', 'entry_time'),
        Index('ix_parking_sessions_date_range', 'entry_time', 'exit_time'),
    )
    
    def calculate_duration(self):
        """Calculate session duration in minutes."""
        if self.exit_time:
            delta = self.exit_time - self.entry_time
            self.duration_minutes = int(delta.total_seconds() / 60)
        return self.duration_minutes
    
    def __repr__(self):
        return f"<ParkingSession id={self.id} session_id={self.session_id} status={self.status}>"


class Reservation(BaseModel):
    """Parking reservation model."""
    
    __tablename__ = 'reservations'
    
    reservation_number = Column(String(100), unique=True, nullable=False, index=True)
    
    # Timing
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    check_in_time = Column(DateTime(timezone=True), nullable=True)
    check_out_time = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status = Column(String(50), default='confirmed', nullable=False)  # confirmed, checked_in, completed, cancelled, no_show
    cancellation_time = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(500), nullable=True)
    
    # Customer
    customer_name = Column(String(200), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_phone = Column(String(50), nullable=True)
    
    # Vehicle
    vehicle_license_plate = Column(String(20), nullable=False)
    
    # Billing
    rate_id = Column(UUID(as_uuid=True), nullable=True)
    rate_applied = Column(JSONB, nullable=True)
    base_amount = Column(Float, nullable=False)
    tax_amount = Column(Float, nullable=True)
    discount_amount = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=False)
    deposit_amount = Column(Float, nullable=True)
    currency = Column(String(3), default='USD', nullable=False)
    
    # Payment
    payment_status = Column(String(50), default='pending', nullable=False)
    payment_time = Column(DateTime(timezone=True), nullable=True)
    
    # Foreign keys
    parking_lot_id = Column(UUID(as_uuid=True), ForeignKey('parking_lots.id', ondelete='CASCADE'), nullable=False)
    parking_space_id = Column(UUID(as_uuid=True), ForeignKey('parking_spaces.id', ondelete='SET NULL'), nullable=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='SET NULL'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    parking_lot = relationship("ParkingLot", back_populates="reservations")
    parking_space = relationship("ParkingSpace", back_populates="reservations")
    vehicle = relationship("Vehicle", back_populates="reservations")
    user = relationship("User", foreign_keys=[user_id])
    parking_session = relationship("ParkingSession", back_populates="reservation", uselist=False)
    
    __table_args__ = (
        Index('ix_reservations_lot_time_range', 'parking_lot_id', 'start_time', 'end_time'),
        Index('ix_reservations_space_time', 'parking_space_id', 'start_time', 'end_time'),
        Index('ix_reservations_user', 'user_id', 'start_time'),
    )
    
    @validates('end_time')
    def validate_end_time(self, key, end_time):
        """Validate that end time is after start time."""
        if hasattr(self, 'start_time') and self.start_time and end_time <= self.start_time:
            raise ValueError("End time must be after start time")
        return end_time
    
    def __repr__(self):
        return f"<Reservation id={self.id} number={self.reservation_number} status={self.status}>"


class Payment(BaseModel):
    """Payment model."""
    
    __tablename__ = 'payments'
    
    payment_number = Column(String(100), unique=True, nullable=False, index=True)
    transaction_id = Column(String(200), nullable=True, index=True)
    
    # Amount
    amount = Column(Float, nullable=False)
    tax_amount = Column(Float, nullable=True)
    tip_amount = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(3), default='USD', nullable=False)
    
    # Payment details
    payment_method = Column(String(50), nullable=False)  # cash, credit_card, debit_card, mobile_payment, etc.
    payment_status = Column(String(50), default='pending', nullable=False)
    payment_time = Column(DateTime(timezone=True), nullable=True)
    
    # Card details (encrypted/partial)
    card_last_four = Column(String(4), nullable=True)
    card_brand = Column(String(50), nullable=True)
    card_expiry = Column(String(10), nullable=True)
    
    # Transaction details
    authorization_code = Column(String(200), nullable=True)
    response_code = Column(String(50), nullable=True)
    response_message = Column(String(500), nullable=True)
    
    # Refund details
    refund_amount = Column(Float, nullable=True)
    refund_time = Column(DateTime(timezone=True), nullable=True)
    refund_reason = Column(String(500), nullable=True)
    refund_transaction_id = Column(String(200), nullable=True)
    
    # Foreign keys
    parking_session_id = Column(UUID(as_uuid=True), ForeignKey('parking_sessions.id', ondelete='SET NULL'), nullable=True)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='SET NULL'), nullable=True)
    processed_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    parking_session = relationship("ParkingSession", back_populates="payments")
    reservation = relationship("Reservation")
    processed_by_user = relationship("User", foreign_keys=[processed_by_id], back_populates="payments_processed")
    
    __table_args__ = (
        Index('ix_payments_session', 'parking_session_id'),
        Index('ix_payments_reservation', 'reservation_id'),
        Index('ix_payments_transaction', 'transaction_id'),
    )
    
    def __repr__(self):
        return f"<Payment id={self.id} number={self.payment_number} amount={self.total_amount} status={self.payment_status}>"


class BlacklistedVehicle(TenantModel):
    """Blacklisted vehicles model."""
    
    __tablename__ = 'blacklisted_vehicles'
    
    license_plate = Column(String(20), nullable=False)
    license_plate_normalized = Column(String(20), nullable=False, index=True)
    reason = Column(String(500), nullable=False)
    blacklist_type = Column(String(50), default='permanent', nullable=False)  # temporary, permanent
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Foreign keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    parking_lot_id = Column(UUID(as_uuid=True), ForeignKey('parking_lots.id', ondelete='CASCADE'), nullable=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=True)
    added_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    organization = relationship("Organization")
    parking_lot = relationship("ParkingLot", back_populates="blacklisted_vehicles")
    vehicle = relationship("Vehicle", back_populates="blacklist_entries")
    added_by = relationship("User", foreign_keys=[added_by_id])
    
    __table_args__ = (
        UniqueConstraint('organization_id', 'license_plate_normalized', name='uq_org_blacklist_plate'),
        Index('ix_blacklist_plate_lot', 'license_plate_normalized', 'parking_lot_id'),
    )
    
    def __repr__(self):
        return f"<BlacklistedVehicle id={self.id} plate={self.license_plate}>"


class Notification(BaseModel):
    """Notification model."""
    
    __tablename__ = 'notifications'
    
    notification_type = Column(String(50), nullable=False, index=True)  # email, sms, push, in_app
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(String(20), default='normal', nullable=False)  # low, normal, high, urgent
    status = Column(String(50), default='pending', nullable=False)  # pending, sent, delivered, read, failed
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    __table_args__ = (
        Index('ix_notifications_user_status', 'user_id', 'status'),
        Index('ix_notifications_created_at', 'created_at'),
    )


class ActivityLog(AuditModel):
    """Activity log for audit trail."""
    
    __tablename__ = 'activity_logs'
    
    # Additional fields beyond AuditModel
    details = Column(JSONB, nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="activity_logs")
    
    __table_args__ = (
        Index('ix_activity_logs_user_time', 'user_id', 'created_at'),
        Index('ix_activity_logs_entity', 'entity_type', 'entity_id'),
        Index('ix_activity_logs_action_time', 'action', 'created_at'),
    )


class CameraEvent(BaseModel):
    """Camera events (motion detection, LPR, etc.)."""
    
    __tablename__ = 'camera_events'
    
    event_type = Column(String(50), nullable=False)  # motion, lpr, object_detected, etc.
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    image_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    confidence = Column(Float, nullable=True)
    metadata = Column(JSONB, nullable=True)  # Additional event data
    
    # LPR specific
    detected_plate = Column(String(20), nullable=True)
    plate_confidence = Column(Float, nullable=True)
    plate_image_url = Column(String(500), nullable=True)
    
    # Foreign keys
    camera_id = Column(UUID(as_uuid=True), ForeignKey('cameras.id', ondelete='CASCADE'), nullable=False)
    parking_session_id = Column(UUID(as_uuid=True), ForeignKey('parking_sessions.id', ondelete='SET NULL'), nullable=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    camera = relationship("Camera", back_populates="events")
    
    __table_args__ = (
        Index('ix_camera_events_camera_time', 'camera_id', 'timestamp'),
        Index('ix_camera_events_plate', 'detected_plate'),
    )


class CameraImage(BaseModel):
    """Camera images captured."""
    
    __tablename__ = 'camera_images'
    
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    image_url = Column(String(500), nullable=False)
    image_type = Column(String(50), nullable=False)  # full, cropped, thumbnail
    file_size = Column(Integer, nullable=True)  # in bytes
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    format = Column(String(20), nullable=True)
    
    # Foreign keys
    camera_id = Column(UUID(as_uuid=True), ForeignKey('cameras.id', ondelete='CASCADE'), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey('camera_events.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    camera = relationship("Camera", back_populates="images")
    event = relationship("CameraEvent", foreign_keys=[event_id])
    
    __table_args__ = (
        Index('ix_camera_images_camera_time', 'camera_id', 'timestamp'),
    )


class GateEvent(BaseModel):
    """Gate events (open, close, etc.)."""
    
    __tablename__ = 'gate_events'
    
    event_type = Column(String(50), nullable=False)  # open, close, open_request, close_request, error
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    result = Column(String(50), nullable=False)  # success, failure
    error_message = Column(Text, nullable=True)
    trigger_method = Column(String(50), nullable=False)  # manual, automatic, remote, sensor
    metadata = Column(JSONB, nullable=True)
    
    # Foreign keys
    gate_id = Column(UUID(as_uuid=True), ForeignKey('gates.id', ondelete='CASCADE'), nullable=False)
    triggered_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    gate = relationship("Gate", back_populates="events")
    triggered_by = relationship("User", foreign_keys=[triggered_by_id])
    
    __table_args__ = (
        Index('ix_gate_events_gate_time', 'gate_id', 'timestamp'),
    )


# Export all models for easy import
__all__ = [
    'Organization',
    'User',
    'Role',
    'UserRole',
    'ParkingLot',
    'ParkingLevel',
    'ParkingSpace',
    'EntranceExit',
    'Gate',
    'Camera',
    'Sensor',
    'SensorData',
    'Vehicle',
    'Rate',
    'ParkingSession',
    'Reservation',
    'Payment',
    'BlacklistedVehicle',
    'Notification',
    'ActivityLog',
    'CameraEvent',
    'CameraImage',
    'GateEvent',
]