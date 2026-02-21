# parking-management/data/migrations/models/__init__.py

"""
Database models for parking management system.

This package contains all SQLAlchemy ORM models used in the parking management system.
Models are organized by domain and include comprehensive relationships, indexes,
and constraints.

Domain Areas:
- User Management: Users, roles, permissions, authentication
- Vehicle Management: Vehicles, makes, models, registrations, insurance
- Parking Management: Zones, spots, sensors, maintenance
- Reservation Management: Reservations, waitlist, blackout dates
- Payment Processing: Payments, refunds, subscriptions, invoices
- Notification System: Notifications, templates, preferences, webhooks
- Audit System: Audit logs, sessions, compliance tracking
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Time,
    Text, ForeignKey, UniqueConstraint, Index, CheckConstraint,
    Numeric, LargeBinary, BigInteger, SmallInteger, JSON, Table,
    func, text
)
from sqlalchemy.dialects.postgresql import (
    UUID, JSONB, ARRAY, INET, CIDR, MACADDR, TSVECTOR,
    BIT, VARBIT, BYTEA, TIMESTAMP
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import event
import uuid
from datetime import datetime, date, timedelta
import re
import hashlib
import hmac

# Create base class for all models
Base = declarative_base()

# Metadata for table creation and reflection
metadata = Base.metadata

# ============================================================================
# USER MANAGEMENT MODELS
# ============================================================================

class User(Base):
    """
    User accounts for the parking management system.
    Supports authentication, profile management, and role-based access control.
    """
    __tablename__ = 'users'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Authentication fields
    username = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    password_salt = Column(String(255))
    password_reset_token = Column(String(255), unique=True)
    password_reset_expires = Column(DateTime(timezone=True))
    password_changed_at = Column(DateTime(timezone=True))
    
    # Profile information
    first_name = Column(String(100))
    last_name = Column(String(100))
    middle_name = Column(String(100))
    preferred_name = Column(String(100))
    phone_number = Column(String(20), index=True)
    phone_number_verified = Column(Boolean, server_default='false')
    email_verified = Column(Boolean, server_default='false')
    avatar_url = Column(String(500))
    
    # Address
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    postal_code = Column(String(20))
    country = Column(String(2), server_default='US')
    
    # Status and verification
    status = Column(String(20), nullable=False, server_default='pending', index=True)
    is_active = Column(Boolean, nullable=False, server_default='true', index=True)
    is_verified = Column(Boolean, server_default='false')
    verified_at = Column(DateTime(timezone=True))
    verification_token = Column(String(255))
    verification_sent_at = Column(DateTime(timezone=True))
    
    # Security
    two_factor_enabled = Column(Boolean, server_default='false')
    two_factor_secret = Column(String(255))
    two_factor_backup_codes = Column(ARRAY(String(10)))
    last_login_at = Column(DateTime(timezone=True))
    last_login_ip = Column(String(45))
    last_login_ua = Column(String(500))
    login_attempts = Column(Integer, server_default='0')
    locked_until = Column(DateTime(timezone=True))
    
    # API access
    api_key = Column(String(255), unique=True)
    api_key_created_at = Column(DateTime(timezone=True))
    api_key_expires_at = Column(DateTime(timezone=True))
    api_key_last_used = Column(DateTime(timezone=True))
    
    # Role and permissions
    role = Column(String(50), server_default='user')
    permissions = Column(ARRAY(String(100)), server_default='{}')
    
    # Department/Organization
    department = Column(String(100))
    employee_id = Column(String(50), unique=True)
    company_id = Column(String(100))
    cost_center = Column(String(100))
    
    # Preferences
    preferences = Column(JSONB, server_default='{}')
    notification_preferences = Column(JSONB, server_default='{}')
    
    # Metadata
    metadata = Column(JSONB, server_default='{}')
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    deleted_at = Column(DateTime(timezone=True), index=True)
    deleted_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Relationships
    vehicles = relationship('Vehicle', back_populates='owner', foreign_keys='Vehicle.user_id')
    reservations = relationship('Reservation', back_populates='user')
    payments = relationship('Payment', back_populates='user')
    payment_methods = relationship('PaymentMethod', back_populates='user')
    notification_prefs = relationship('NotificationPreference', back_populates='user')
    notification_devices = relationship('NotificationDevice', back_populates='user')
    audit_logs = relationship('AuditEvent', back_populates='user')
    audit_sessions = relationship('AuditSession', back_populates='user')
    
    # Self-referential relationships for audit
    created_by_user = relationship('User', foreign_keys=[created_by], remote_side=[id])
    updated_by_user = relationship('User', foreign_keys=[updated_by], remote_side=[id])
    deleted_by_user = relationship('User', foreign_keys=[deleted_by], remote_side=[id])
    
    __table_args__ = (
        Index('ix_users_email_lower', func.lower(email)),
        Index('ix_users_username_lower', func.lower(username)),
        Index('ix_users_name_search', first_name, last_name),
        Index('ix_users_created_month', func.date_trunc('month', created_at)),
        Index('ix_users_active_recent', last_login_at, 
              postgresql_where=text("status = 'active'")),
        CheckConstraint(
            "status IN ('pending', 'active', 'inactive', 'suspended', 'locked', 'deleted')",
            name='ck_users_status'
        ),
        CheckConstraint(
            "role IN ('user', 'operator', 'manager', 'admin', 'super_admin')",
            name='ck_users_role'
        ),
    )
    
    @hybrid_property
    def full_name(self):
        """Get user's full name"""
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p)
    
    @hybrid_property
    def display_name(self):
        """Get display name (preferred name or full name)"""
        return self.preferred_name or self.full_name or self.username
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format"""
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            raise ValueError('Invalid email format')
        return email.lower()
    
    @validates('phone_number')
    def validate_phone(self, key, phone):
        """Validate phone number format"""
        if phone and not re.match(r'^\+?[1-9]\d{1,14}$', phone):
            raise ValueError('Invalid phone number format')
        return phone
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"


class Role(Base):
    """Roles for role-based access control"""
    __tablename__ = 'roles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255))
    permissions = Column(ARRAY(String(100)), server_default='{}')
    is_system = Column(Boolean, server_default='false')
    priority = Column(Integer, server_default='0')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Relationships
    users = relationship('User', secondary='user_roles', backref='roles_collection')
    
    __table_args__ = (
        Index('ix_roles_name', name, unique=True),
    )


class UserRole(Base):
    """Association table for users and roles"""
    __tablename__ = 'user_roles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    granted_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    granted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, server_default='true')
    
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uq_user_roles'),
        Index('ix_user_roles_user', 'user_id'),
        Index('ix_user_roles_role', 'role_id'),
    )


class Permission(Base):
    """Granular permissions for fine-grained access control"""
    __tablename__ = 'permissions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    description = Column(String(255))
    conditions = Column(JSONB)
    
    __table_args__ = (
        UniqueConstraint('resource', 'action', name='uq_permission'),
    )


# ============================================================================
# VEHICLE MANAGEMENT MODELS
# ============================================================================

class VehicleMake(Base):
    """Vehicle manufacturers reference table"""
    __tablename__ = 'vehicle_makes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    country = Column(String(100))
    founded_year = Column(Integer)
    website = Column(String(255))
    logo_url = Column(String(500))
    is_active = Column(Boolean, server_default='true')
    is_popular = Column(Boolean, server_default='false')
    metadata = Column(JSONB, server_default='{}')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    models = relationship('VehicleModel', back_populates='make', cascade='all, delete-orphan')
    vehicles = relationship('Vehicle', back_populates='make_info')
    
    __table_args__ = (
        Index('ix_vehicle_makes_name', name),
    )


class VehicleModel(Base):
    """Vehicle models reference table"""
    __tablename__ = 'vehicle_models'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    make_id = Column(UUID(as_uuid=True), ForeignKey('vehicle_makes.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=False)
    vehicle_type = Column(String(50))
    vehicle_class = Column(String(50))
    start_year = Column(Integer)
    end_year = Column(Integer)
    fuel_types = Column(ARRAY(String(50)))
    transmission_types = Column(ARRAY(String(50)))
    drive_types = Column(ARRAY(String(50)))
    engine_sizes = Column(ARRAY(String(20)))
    length_mm = Column(Integer)
    width_mm = Column(Integer)
    height_mm = Column(Integer)
    weight_kg = Column(Integer)
    image_url = Column(String(500))
    is_active = Column(Boolean, server_default='true')
    is_popular = Column(Boolean, server_default='false')
    metadata = Column(JSONB, server_default='{}')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    make = relationship('VehicleMake', back_populates='models')
    vehicles = relationship('Vehicle', back_populates='model_info')
    
    __table_args__ = (
        UniqueConstraint('make_id', 'name', name='uq_vehicle_model_make_name'),
        Index('ix_vehicle_models_type', 'vehicle_type'),
    )


class VehicleType(Base):
    """Vehicle type classifications"""
    __tablename__ = 'vehicle_types'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(50), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # passenger, commercial, motorcycle
    default_height_cm = Column(Integer)
    default_width_cm = Column(Integer)
    default_length_cm = Column(Integer)
    default_weight_kg = Column(Integer)
    requires_special_spot = Column(Boolean, server_default='false')
    special_spot_types = Column(ARRAY(String(50)))
    max_parking_duration_hours = Column(Integer)
    rate_multiplier = Column(Numeric(3, 2), server_default='1.0')
    is_active = Column(Boolean, server_default='true')
    metadata = Column(JSONB, server_default='{}')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_vehicle_types_category', 'category'),
    )


class Vehicle(Base):
    """
    Main vehicles table with comprehensive vehicle information.
    Tracks all vehicles registered in the system.
    """
    __tablename__ = 'vehicles'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_number = Column(String(50), nullable=False, unique=True)
    
    # Owner relationship
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    ownership_type = Column(String(50), nullable=False, server_default='owner')
    
    # License plate
    license_plate = Column(String(20), nullable=False, index=True)
    license_plate_state = Column(String(50))
    license_plate_country = Column(String(2))
    license_plate_issue_date = Column(Date)
    license_plate_expiry_date = Column(Date)
    
    # Vehicle identification
    vin = Column(String(17), unique=True, index=True)
    make_id = Column(UUID(as_uuid=True), ForeignKey('vehicle_makes.id', ondelete='SET NULL'))
    model_id = Column(UUID(as_uuid=True), ForeignKey('vehicle_models.id', ondelete='SET NULL'))
    vehicle_type = Column(String(50), index=True)
    vehicle_class = Column(String(50))
    year = Column(Integer)
    trim = Column(String(100))
    color = Column(String(50))
    color_code = Column(String(10))
    
    # Physical characteristics
    length_cm = Column(Integer)
    width_cm = Column(Integer)
    height_cm = Column(Integer)
    weight_kg = Column(Integer)
    wheelbase_cm = Column(Integer)
    
    # Propulsion
    fuel_type = Column(String(50))
    fuel_capacity_liters = Column(Float)
    battery_capacity_kwh = Column(Float)
    electric_range_km = Column(Integer)
    
    # Drivetrain
    transmission_type = Column(String(50))
    drive_type = Column(String(20))
    engine_displacement_cc = Column(Integer)
    horsepower = Column(Integer)
    
    # Features
    has_ev_charger = Column(Boolean, server_default='false')
    ev_charger_type = Column(String(50))
    has_sunroof = Column(Boolean, server_default='false')
    has_tow_hitch = Column(Boolean, server_default='false')
    towing_capacity_kg = Column(Integer)
    
    # Access and identification
    has_rfid = Column(Boolean, server_default='false')
    rfid_tag = Column(String(100), unique=True)
    has_transponder = Column(Boolean, server_default='false')
    transponder_id = Column(String(100), unique=True)
    has_permit = Column(Boolean, server_default='false')
    permit_number = Column(String(100))
    permit_expiry = Column(Date)
    
    # Status
    status = Column(String(20), nullable=False, server_default='active', index=True)
    is_verified = Column(Boolean, server_default='false')
    verified_at = Column(DateTime(timezone=True))
    verified_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Compliance
    registration_status = Column(String(50))
    registration_expiry = Column(Date, index=True)
    insurance_status = Column(String(50))
    insurance_expiry = Column(Date, index=True)
    inspection_status = Column(String(50))
    inspection_expiry = Column(Date)
    
    # Enforcement
    is_blacklisted = Column(Boolean, server_default='false', index=True)
    blacklisted_at = Column(DateTime(timezone=True))
    blacklisted_reason = Column(Text)
    is_stolen = Column(Boolean, server_default='false', index=True)
    stolen_reported_at = Column(DateTime(timezone=True))
    stolen_recovered_at = Column(DateTime(timezone=True))
    
    # Usage statistics
    total_parking_sessions = Column(Integer, server_default='0')
    total_parking_duration_minutes = Column(Integer, server_default='0')
    total_parking_amount = Column(Numeric(10, 2), server_default='0')
    last_parking_at = Column(DateTime(timezone=True))
    last_parking_spot = Column(String(50))
    
    # Violations
    violation_count = Column(Integer, server_default='0')
    unpaid_violations = Column(Integer, server_default='0')
    unpaid_amount = Column(Numeric(10, 2), server_default='0')
    
    # Notes and metadata
    notes = Column(Text)
    tags = Column(ARRAY(String(50)))
    custom_fields = Column(JSONB)
    metadata = Column(JSONB, server_default='{}')
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    owner = relationship('User', back_populates='vehicles', foreign_keys=[user_id])
    make_info = relationship('VehicleMake', back_populates='vehicles')
    model_info = relationship('VehicleModel', back_populates='vehicles')
    registrations = relationship('VehicleRegistration', back_populates='vehicle', cascade='all, delete-orphan')
    insurance_policies = relationship('VehicleInsurance', back_populates='vehicle', cascade='all, delete-orphan')
    inspections = relationship('VehicleInspection', back_populates='vehicle', cascade='all, delete-orphan')
    maintenance_records = relationship('VehicleMaintenance', back_populates='vehicle', cascade='all, delete-orphan')
    images = relationship('VehicleImage', back_populates='vehicle', cascade='all, delete-orphan')
    documents = relationship('VehicleDocument', back_populates='vehicle', cascade='all, delete-orphan')
    violations = relationship('VehicleViolation', back_populates='vehicle')
    access_history = relationship('VehicleAccessHistory', back_populates='vehicle')
    location_history = relationship('VehicleLocationHistory', back_populates='vehicle')
    preferences = relationship('VehiclePreference', back_populates='vehicle', uselist=False, cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('ix_vehicles_license_plate_composite', 'license_plate', 'license_plate_state'),
        Index('ix_vehicles_license_plate_gin', text("license_plate gin_trgm_ops"), postgresql_using='gin'),
        Index('ix_vehicles_vin_gin', text("vin gin_trgm_ops"), postgresql_using='gin'),
        Index('ix_vehicles_compliance', 'registration_expiry', 'insurance_expiry', 'inspection_expiry'),
        Index('ix_vehicles_expired', 'registration_expiry', 'insurance_expiry',
              postgresql_where=text("status = 'active'")),
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended', 'banned', 'pending_verification', 'archived')",
            name='ck_vehicles_status'
        ),
    )
    
    @hybrid_property
    def is_expired_registration(self):
        """Check if registration is expired"""
        return self.registration_expiry and self.registration_expiry < date.today()
    
    @hybrid_property
    def is_expired_insurance(self):
        """Check if insurance is expired"""
        return self.insurance_expiry and self.insurance_expiry < date.today()
    
    @validates('vin')
    def validate_vin(self, key, vin):
        """Validate VIN format (17 characters, alphanumeric)"""
        if vin and not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin.upper()):
            raise ValueError('Invalid VIN format')
        return vin.upper() if vin else vin
    
    def __repr__(self):
        return f"<Vehicle(id={self.id}, plate={self.license_plate}, vin={self.vin})>"


class VehicleRegistration(Base):
    """Vehicle registration history"""
    __tablename__ = 'vehicle_registrations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    registration_number = Column(String(100), nullable=False)
    jurisdiction = Column(String(100))
    state = Column(String(50))
    country = Column(String(2))
    issue_date = Column(Date)
    effective_date = Column(Date)
    expiry_date = Column(Date)
    status = Column(String(50), nullable=False)
    registered_owner_name = Column(String(255))
    registration_document_url = Column(String(500))
    verified = Column(Boolean, server_default='false')
    verified_at = Column(DateTime(timezone=True))
    verified_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='registrations')
    
    __table_args__ = (
        Index('ix_vehicle_reg_vehicle', 'vehicle_id'),
        Index('ix_vehicle_reg_expiry', 'expiry_date'),
    )


class VehicleInsurance(Base):
    """Vehicle insurance policies"""
    __tablename__ = 'vehicle_insurance'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    policy_number = Column(String(100), nullable=False)
    provider = Column(String(255), nullable=False)
    provider_phone = Column(String(20))
    coverage_type = Column(String(100))
    coverage_amount = Column(Numeric(10, 2))
    deductible = Column(Numeric(10, 2))
    effective_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    status = Column(String(50), nullable=False)
    premium_amount = Column(Numeric(10, 2))
    insured_name = Column(String(255))
    policy_document_url = Column(String(500))
    verified = Column(Boolean, server_default='false')
    verified_at = Column(DateTime(timezone=True))
    verified_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='insurance_policies')
    
    __table_args__ = (
        Index('ix_vehicle_ins_vehicle', 'vehicle_id'),
        Index('ix_vehicle_ins_expiry', 'expiry_date'),
    )


class VehicleInspection(Base):
    """Vehicle inspection records"""
    __tablename__ = 'vehicle_inspections'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    inspection_number = Column(String(100), nullable=False)
    inspection_type = Column(String(100))
    inspector_name = Column(String(255))
    inspection_facility = Column(String(255))
    inspection_date = Column(Date, nullable=False)
    expiry_date = Column(Date)
    status = Column(String(50), nullable=False)
    result = Column(String(50))
    odometer_reading = Column(Integer)
    certificate_number = Column(String(100))
    certificate_url = Column(String(500))
    verified = Column(Boolean, server_default='false')
    verified_at = Column(DateTime(timezone=True))
    verified_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='inspections')
    
    __table_args__ = (
        Index('ix_vehicle_insp_vehicle', 'vehicle_id'),
        Index('ix_vehicle_insp_date', 'inspection_date'),
    )


class VehicleMaintenance(Base):
    """Vehicle maintenance records"""
    __tablename__ = 'vehicle_maintenance'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    maintenance_type = Column(String(100), nullable=False)
    service_date = Column(Date, nullable=False)
    service_provider = Column(String(255))
    odometer_reading = Column(Integer)
    description = Column(Text)
    items_serviced = Column(JSONB)
    parts_replaced = Column(JSONB)
    total_cost = Column(Numeric(10, 2))
    invoice_url = Column(String(500))
    next_service_due = Column(Date)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='maintenance_records')
    
    __table_args__ = (
        Index('ix_vehicle_maint_vehicle', 'vehicle_id'),
        Index('ix_vehicle_maint_date', 'service_date'),
        Index('ix_vehicle_maint_next', 'next_service_due'),
    )


class VehicleImage(Base):
    """Vehicle images"""
    __tablename__ = 'vehicle_images'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    image_type = Column(String(50))
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))
    is_primary = Column(Boolean, server_default='false')
    is_verified = Column(Boolean, server_default='false')
    verified_at = Column(DateTime(timezone=True))
    verified_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='images')
    
    __table_args__ = (
        Index('ix_vehicle_images_vehicle', 'vehicle_id'),
    )


class VehicleDocument(Base):
    """Vehicle documents"""
    __tablename__ = 'vehicle_documents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    document_type = Column(String(100), nullable=False)
    document_name = Column(String(255))
    document_number = Column(String(100))
    issue_date = Column(Date)
    expiry_date = Column(Date)
    issuing_authority = Column(String(255))
    file_url = Column(String(500), nullable=False)
    is_verified = Column(Boolean, server_default='false')
    verified_at = Column(DateTime(timezone=True))
    verified_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='documents')
    
    __table_args__ = (
        Index('ix_vehicle_docs_vehicle', 'vehicle_id'),
        Index('ix_vehicle_docs_expiry', 'expiry_date'),
    )


class VehiclePreference(Base):
    """User preferences for each vehicle"""
    __tablename__ = 'vehicle_preferences'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False, unique=True)
    preferred_parking_zones = Column(ARRAY(UUID(as_uuid=True)))
    preferred_parking_types = Column(ARRAY(String(50)))
    max_walking_distance = Column(Integer)
    preferred_entry_gates = Column(ARRAY(String(100)))
    notify_on_entry = Column(Boolean, server_default='true')
    notify_on_exit = Column(Boolean, server_default='true')
    auto_pay = Column(Boolean, server_default='false')
    default_payment_method_id = Column(UUID(as_uuid=True), ForeignKey('payment_methods.id', ondelete='SET NULL'))
    auto_extend = Column(Boolean, server_default='false')
    max_extension_minutes = Column(Integer)
    reminder_minutes = Column(ARRAY(Integer))
    special_instructions = Column(Text)
    settings = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='preferences')
    default_payment_method = relationship('PaymentMethod')


class VehicleViolation(Base):
    """Parking violations associated with vehicles"""
    __tablename__ = 'vehicle_violations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    violation_number = Column(String(50), nullable=False, unique=True)
    violation_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    description = Column(Text)
    location = Column(String(255))
    zone_id = Column(UUID(as_uuid=True), ForeignKey('parking_zones.id', ondelete='SET NULL'))
    spot_id = Column(UUID(as_uuid=True), ForeignKey('parking_spots.id', ondelete='SET NULL'))
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    detected_by = Column(String(100))
    officer_id = Column(String(100))
    evidence_urls = Column(ARRAY(String(500)))
    fine_amount = Column(Numeric(10, 2))
    currency = Column(String(3), server_default='USD')
    paid = Column(Boolean, server_default='false', index=True)
    paid_at = Column(DateTime(timezone=True))
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.id', ondelete='SET NULL'))
    disputed = Column(Boolean, server_default='false')
    dispute_reason = Column(Text)
    dispute_resolved_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='violations')
    zone = relationship('ParkingZone')
    spot = relationship('ParkingSpot')
    payment = relationship('Payment')
    
    __table_args__ = (
        Index('ix_vehicle_violations_vehicle_unpaid', 'vehicle_id', 'paid'),
        Index('ix_vehicle_violations_type_severity', 'violation_type', 'severity'),
    )


class VehicleAccessHistory(Base):
    """History of vehicle access attempts"""
    __tablename__ = 'vehicle_access_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    access_method = Column(String(50), nullable=False)
    access_type = Column(String(20))  # entry, exit, denied
    gate_id = Column(String(100))
    gate_name = Column(String(255))
    zone_id = Column(UUID(as_uuid=True), ForeignKey('parking_zones.id', ondelete='SET NULL'))
    spot_id = Column(UUID(as_uuid=True), ForeignKey('parking_spots.id', ondelete='SET NULL'))
    session_id = Column(UUID(as_uuid=True), ForeignKey('parking_sessions.id', ondelete='SET NULL'))
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    image_url = Column(String(500))
    confidence = Column(Float)
    matched_plate = Column(String(20))
    denied_reason = Column(String(255))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='access_history')
    zone = relationship('ParkingZone')
    spot = relationship('ParkingSpot')
    session = relationship('ParkingSession')
    
    __table_args__ = (
        Index('ix_vehicle_access_vehicle_time', 'vehicle_id', 'timestamp'),
        Index('ix_vehicle_access_plate_time', 'matched_plate', 'timestamp'),
    )


class VehicleLocationHistory(Base):
    """Historical GPS location data for vehicles"""
    __tablename__ = 'vehicle_location_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey('vehicle_devices.id', ondelete='SET NULL'))
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    altitude = Column(Float)
    speed = Column(Float)
    heading = Column(Float)
    accuracy = Column(Float)
    source = Column(String(50))
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    zone_id = Column(UUID(as_uuid=True), ForeignKey('parking_zones.id', ondelete='SET NULL'))
    spot_id = Column(UUID(as_uuid=True), ForeignKey('parking_spots.id', ondelete='SET NULL'))
    session_id = Column(UUID(as_uuid=True), ForeignKey('parking_sessions.id', ondelete='SET NULL'))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='location_history')
    zone = relationship('ParkingZone')
    spot = relationship('ParkingSpot')
    session = relationship('ParkingSession')
    
    __table_args__ = (
        Index('ix_vehicle_location_vehicle_time', 'vehicle_id', 'timestamp'),
        Index('ix_vehicle_location_coords', 'latitude', 'longitude'),
    )


class VehicleDevice(Base):
    """IoT devices installed in vehicles"""
    __tablename__ = 'vehicle_devices'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    device_type = Column(String(50), nullable=False)
    device_id = Column(String(100), nullable=False, unique=True)
    device_name = Column(String(255))
    manufacturer = Column(String(255))
    model = Column(String(100))
    serial_number = Column(String(100), unique=True)
    firmware_version = Column(String(50))
    battery_level = Column(Integer)
    last_ping = Column(DateTime(timezone=True))
    last_location = Column(JSONB)
    status = Column(String(50), server_default='active')
    activated_at = Column(DateTime(timezone=True))
    deactivated_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    vehicle = relationship('Vehicle')
    location_history = relationship('VehicleLocationHistory', backref='device')
    
    __table_args__ = (
        Index('ix_vehicle_devices_vehicle', 'vehicle_id'),
        Index('ix_vehicle_devices_status', 'status'),
    )


# ============================================================================
# PARKING MANAGEMENT MODELS
# ============================================================================

class ParkingZone(Base):
    """Parking zones/areas within the facility"""
    __tablename__ = 'parking_zones'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, unique=True)
    description = Column(Text)
    zone_type = Column(String(20), nullable=False, server_default='outdoor')
    floor = Column(Integer)
    section = Column(String(10))
    
    # Capacity
    total_spots = Column(Integer, nullable=False, server_default='0')
    available_spots = Column(Integer, nullable=False, server_default='0')
    reserved_spots = Column(Integer, nullable=False, server_default='0')
    occupied_spots = Column(Integer, nullable=False, server_default='0')
    maintenance_spots = Column(Integer, nullable=False, server_default='0')
    
    # Location
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    address = Column(String(255))
    entrance_coordinates = Column(JSONB)
    exit_coordinates = Column(JSONB)
    
    # Operating hours
    opening_time = Column(Time)
    closing_time = Column(Time)
    is_24_hours = Column(Boolean, server_default='false')
    
    # Features
    has_ev_charging = Column(Boolean, server_default='false')
    has_car_wash = Column(Boolean, server_default='false')
    has_security = Column(Boolean, server_default='false')
    has_roof = Column(Boolean, server_default='false')
    
    # Restrictions
    max_height_cm = Column(Integer)
    max_width_cm = Column(Integer)
    max_length_cm = Column(Integer)
    max_weight_kg = Column(Integer)
    
    # Media
    image_url = Column(String(500))
    floor_plan_url = Column(String(500))
    
    # Status
    is_active = Column(Boolean, nullable=False, server_default='true')
    
    # Metadata
    metadata = Column(JSONB, server_default='{}')
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Relationships
    spots = relationship('ParkingSpot', back_populates='zone', cascade='all, delete-orphan')
    rates = relationship('ParkingRate', back_populates='zone')
    
    __table_args__ = (
        Index('ix_zones_code', 'code', unique=True),
        Index('ix_zones_type_active', 'zone_type', 'is_active'),
        Index('ix_zones_location', 'latitude', 'longitude'),
    )
    
    def __repr__(self):
        return f"<ParkingZone(id={self.id}, code={self.code}, name={self.name})>"


class ParkingSpot(Base):
    """Individual parking spots"""
    __tablename__ = 'parking_spots'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey('parking_zones.id', ondelete='CASCADE'), nullable=False)
    spot_number = Column(String(20), nullable=False)
    
    # Location within zone
    level = Column(String(10))
    row = Column(String(10))
    column = Column(String(10))
    coordinates_x = Column(Float)
    coordinates_y = Column(Float)
    coordinates_z = Column(Float)
    
    # Spot characteristics
    spot_type = Column(String(20), nullable=False, server_default='standard')
    status = Column(String(20), nullable=False, server_default='available', index=True)
    vehicle_type = Column(String(20))
    
    # Dimensions
    width_cm = Column(Integer)
    length_cm = Column(Integer)
    height_cm = Column(Integer)
    max_weight_kg = Column(Integer)
    
    # Features
    has_ev_charger = Column(Boolean, server_default='false')
    ev_charger_type = Column(String(50))
    ev_charger_power_kw = Column(Float)
    has_sensor = Column(Boolean, server_default='false')
    sensor_id = Column(String(100))
    is_handicapped = Column(Boolean, server_default='false')
    is_covered = Column(Boolean, server_default='false')
    is_near_elevator = Column(Boolean, server_default='false')
    is_near_entrance = Column(Boolean, server_default='false')
    
    # Current occupancy
    current_vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='SET NULL'))
    current_session_id = Column(UUID(as_uuid=True), ForeignKey('parking_sessions.id', ondelete='SET NULL'))
    current_reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='SET NULL'))
    
    # Rates (can override zone rates)
    hourly_rate = Column(Numeric(10, 2))
    daily_rate = Column(Numeric(10, 2))
    monthly_rate = Column(Numeric(10, 2))
    
    # Statistics
    last_occupied_at = Column(DateTime(timezone=True))
    last_vacated_at = Column(DateTime(timezone=True))
    occupancy_count_today = Column(Integer, server_default='0')
    total_occupancy_count = Column(Integer, server_default='0')
    
    # Status
    is_active = Column(Boolean, nullable=False, server_default='true')
    notes = Column(Text)
    metadata = Column(JSONB, server_default='{}')
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    zone = relationship('ParkingZone', back_populates='spots')
    current_vehicle = relationship('Vehicle', foreign_keys=[current_vehicle_id])
    current_session = relationship('ParkingSession', foreign_keys=[current_session_id])
    current_reservation = relationship('Reservation', foreign_keys=[current_reservation_id])
    sensors = relationship('SpotSensor', back_populates='spot', cascade='all, delete-orphan')
    maintenance_records = relationship('SpotMaintenance', back_populates='spot', cascade='all, delete-orphan')
    occupancy_history = relationship('SpotOccupancyHistory', back_populates='spot', cascade='all, delete-orphan')
    
    __table_args__ = (
        UniqueConstraint('zone_id', 'spot_number', name='uq_spot_zone_number'),
        Index('ix_spots_status_type', 'status', 'spot_type'),
        Index('ix_spots_current_occupancy', 'status', 'current_vehicle_id', 'current_session_id'),
        Index('ix_spots_available_search', 'zone_id', 'spot_type', 'status',
              postgresql_where=text("status = 'available'")),
        Index('ix_spots_ev_charger', 'has_ev_charger', 'ev_charger_type',
              postgresql_where=text("has_ev_charger = true")),
    )
    
    def __repr__(self):
        return f"<ParkingSpot(id={self.id}, zone={self.zone_id}, number={self.spot_number}, status={self.status})>"


class ParkingRate(Base):
    """Parking rate configurations"""
    __tablename__ = 'parking_rates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zone_id = Column(UUID(as_uuid=True), ForeignKey('parking_zones.id', ondelete='CASCADE'))
    spot_type = Column(String(20))
    vehicle_type = Column(String(20))
    rate_type = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Rate details
    base_rate = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, server_default='USD')
    unit = Column(String(20), nullable=False)  # hour, day, week, month, year
    min_units = Column(Integer, server_default='1')
    max_units = Column(Integer)
    grace_period_minutes = Column(Integer, server_default='15')
    
    # Capping
    has_maximum_cap = Column(Boolean, server_default='false')
    maximum_cap_amount = Column(Numeric(10, 2))
    maximum_cap_period = Column(String(20))
    
    # Special rates
    has_weekend_rate = Column(Boolean, server_default='false')
    weekend_rate = Column(Numeric(10, 2))
    has_night_rate = Column(Boolean, server_default='false')
    night_rate = Column(Numeric(10, 2))
    night_start_time = Column(Time)
    night_end_time = Column(Time)
    
    # Validity
    effective_from = Column(DateTime(timezone=True), nullable=False)
    effective_to = Column(DateTime(timezone=True))
    priority = Column(Integer, server_default='0')
    
    # Status
    is_active = Column(Boolean, nullable=False, server_default='true')
    metadata = Column(JSONB, server_default='{}')
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Relationships
    zone = relationship('ParkingZone', back_populates='rates')
    
    __table_args__ = (
        Index('ix_rates_zone_type', 'zone_id', 'spot_type'),
        Index('ix_rates_effective_date', 'effective_from', 'effective_to'),
    )


class ParkingSession(Base):
    """Parking sessions tracking vehicle entries and exits"""
    __tablename__ = 'parking_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_number = Column(String(50), nullable=False, unique=True)
    
    # Core relationships
    spot_id = Column(UUID(as_uuid=True), ForeignKey('parking_spots.id', ondelete='CASCADE'), nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='SET NULL'))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='SET NULL'))
    
    # Vehicle info (snapshot)
    license_plate = Column(String(20), index=True)
    vehicle_type = Column(String(20))
    
    # Session timing
    status = Column(String(20), nullable=False, server_default='active', index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True))
    expected_end_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)
    
    # Billing
    rate_id = Column(UUID(as_uuid=True), ForeignKey('parking_rates.id', ondelete='SET NULL'))
    rate_applied = Column(Numeric(10, 2))
    base_amount = Column(Numeric(10, 2))
    tax_amount = Column(Numeric(10, 2))
    discount_amount = Column(Numeric(10, 2))
    total_amount = Column(Numeric(10, 2))
    currency = Column(String(3), server_default='USD')
    payment_status = Column(String(20), server_default='pending')
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.id', ondelete='SET NULL'))
    
    # Access tracking
    entry_gate = Column(String(50))
    exit_gate = Column(String(50))
    entry_image_url = Column(String(500))
    exit_image_url = Column(String(500))
    check_in_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    check_out_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Metadata
    notes = Column(Text)
    metadata = Column(JSONB, server_default='{}')
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    spot = relationship('ParkingSpot', foreign_keys=[spot_id])
    vehicle = relationship('Vehicle', foreign_keys=[vehicle_id])
    user = relationship('User', foreign_keys=[user_id])
    reservation = relationship('Reservation', foreign_keys=[reservation_id])
    rate = relationship('ParkingRate', foreign_keys=[rate_id])
    payment = relationship('Payment', foreign_keys=[payment_id])
    
    __table_args__ = (
        Index('ix_sessions_active', 'status', 'start_time',
              postgresql_where=text("status = 'active'")),
        Index('ix_sessions_vehicle_active', 'vehicle_id', 'status'),
        Index('ix_sessions_spot_history', 'spot_id', 'start_time', 'end_time'),
    )


class SpotSensor(Base):
    """IoT sensors monitoring parking spot occupancy"""
    __tablename__ = 'spot_sensors'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spot_id = Column(UUID(as_uuid=True), ForeignKey('parking_spots.id', ondelete='CASCADE'), nullable=False)
    sensor_type = Column(String(50), nullable=False)
    sensor_model = Column(String(100))
    manufacturer = Column(String(100))
    serial_number = Column(String(100), unique=True)
    firmware_version = Column(String(50))
    ip_address = Column(String(45))
    mac_address = Column(String(17))
    status = Column(String(20), nullable=False, server_default='active')
    battery_level = Column(Integer)
    last_communication = Column(DateTime(timezone=True))
    current_value = Column(Float)
    current_status = Column(String(20))
    error_count = Column(Integer, server_default='0')
    last_error = Column(Text)
    
    installed_at = Column(DateTime(timezone=True), nullable=False)
    installed_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    removed_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    spot = relationship('ParkingSpot', back_populates='sensors')
    
    __table_args__ = (
        Index('ix_sensors_spot', 'spot_id'),
        Index('ix_sensors_status', 'status'),
    )


class SpotMaintenance(Base):
    """Maintenance schedule and history for parking spots"""
    __tablename__ = 'spot_maintenance'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spot_id = Column(UUID(as_uuid=True), ForeignKey('parking_spots.id', ondelete='CASCADE'), nullable=False)
    maintenance_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, server_default='scheduled')
    title = Column(String(200), nullable=False)
    description = Column(Text)
    priority = Column(String(20), server_default='medium')
    
    scheduled_start = Column(DateTime(timezone=True), nullable=False)
    scheduled_end = Column(DateTime(timezone=True), nullable=False)
    actual_start = Column(DateTime(timezone=True))
    actual_end = Column(DateTime(timezone=True))
    
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    vendor_name = Column(String(200))
    cost_estimate = Column(Numeric(10, 2))
    actual_cost = Column(Numeric(10, 2))
    notes = Column(Text)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    spot = relationship('ParkingSpot', back_populates='maintenance_records')
    assignee = relationship('User', foreign_keys=[assigned_to])
    
    __table_args__ = (
        Index('ix_maintenance_spot', 'spot_id'),
        Index('ix_maintenance_status', 'status'),
        Index('ix_maintenance_schedule', 'scheduled_start', 'scheduled_end'),
    )


class SpotOccupancyHistory(Base):
    """Historical record of spot occupancy"""
    __tablename__ = 'spot_occupancy_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spot_id = Column(UUID(as_uuid=True), ForeignKey('parking_spots.id', ondelete='CASCADE'), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey('parking_sessions.id', ondelete='SET NULL'))
    status = Column(String(20), nullable=False)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='SET NULL'))
    license_plate = Column(String(20))
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    spot = relationship('ParkingSpot', back_populates='occupancy_history')
    session = relationship('ParkingSession')
    vehicle = relationship('Vehicle')
    
    __table_args__ = (
        Index('ix_occupancy_history_spot_time', 'spot_id', 'start_time', 'end_time'),
        Index('ix_occupancy_history_time_range', 'start_time', 'end_time'),
    )


# ============================================================================
# RESERVATION MANAGEMENT MODELS
# ============================================================================

class Reservation(Base):
    """
    Parking spot reservations made by users.
    Supports recurring, group, and guest reservations.
    """
    __tablename__ = 'reservations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_number = Column(String(50), nullable=False, unique=True)
    external_reference = Column(String(100), unique=True)
    
    # Core relationships
    spot_id = Column(UUID(as_uuid=True), ForeignKey('parking_spots.id', ondelete='RESTRICT'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='SET NULL'))
    rate_id = Column(UUID(as_uuid=True), ForeignKey('parking_rates.id', ondelete='SET NULL'))
    
    # Customer information (for guest reservations)
    is_guest = Column(Boolean, server_default='false')
    guest_email = Column(String(255), index=True)
    guest_phone = Column(String(20))
    guest_first_name = Column(String(100))
    guest_last_name = Column(String(100))
    
    # Reservation details
    status = Column(String(20), nullable=False, server_default='pending', index=True)
    reservation_type = Column(String(50), nullable=False)  # standard, vip, event, monthly
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    flexible_timing = Column(Boolean, server_default='false')
    flexible_window_minutes = Column(Integer)
    
    # Check-in/out tracking
    actual_check_in = Column(DateTime(timezone=True))
    actual_check_out = Column(DateTime(timezone=True))
    duration_minutes = Column(Integer)
    check_in_code = Column(String(50))
    check_in_method = Column(String(50))
    check_in_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    check_out_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Vehicle information (snapshot)
    license_plate = Column(String(20))
    vehicle_make = Column(String(100))
    vehicle_model = Column(String(100))
    vehicle_color = Column(String(50))
    vehicle_type = Column(String(20))
    
    # Pricing
    base_amount = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), server_default='0')
    discount_amount = Column(Numeric(10, 2), server_default='0')
    addons_amount = Column(Numeric(10, 2), server_default='0')
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, server_default='USD')
    
    # Discounts
    discount_code = Column(String(50))
    discount_type = Column(String(20))
    discount_value = Column(Numeric(10, 2))
    
    # Payment
    payment_status = Column(String(20), nullable=False, server_default='pending', index=True)
    payment_method = Column(String(50))
    payment_intent_id = Column(String(255))
    requires_deposit = Column(Boolean, server_default='false')
    deposit_amount = Column(Numeric(10, 2))
    deposit_paid = Column(Boolean, server_default='false')
    
    # Cancellation
    cancellation_reason = Column(Text)
    cancelled_at = Column(DateTime(timezone=True))
    cancelled_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    cancellation_fee = Column(Numeric(10, 2))
    refund_amount = Column(Numeric(10, 2))
    
    # Modification tracking
    modified_count = Column(Integer, server_default='0')
    last_modified_at = Column(DateTime(timezone=True))
    modification_history = Column(JSONB)
    
    # Recurring reservations
    is_recurring = Column(Boolean, server_default='false')
    recurring_id = Column(UUID(as_uuid=True))
    recurring_sequence = Column(Integer)
    
    # Group reservations
    is_group_reservation = Column(Boolean, server_default='false')
    group_id = Column(String(100))
    group_name = Column(String(200))
    group_size = Column(Integer)
    
    # Notifications
    reminder_sent = Column(Boolean, server_default='false')
    reminder_sent_at = Column(DateTime(timezone=True))
    confirmation_sent = Column(Boolean, server_default='false')
    confirmation_sent_at = Column(DateTime(timezone=True))
    
    # Additional services
    addons = Column(JSONB)
    special_requests = Column(Text)
    access_instructions = Column(Text)
    
    # Source tracking
    source = Column(String(50))  # web, mobile, api, walk-in
    source_channel = Column(String(50))
    booking_agent = Column(String(200))
    
    # Metadata
    internal_notes = Column(Text)
    customer_notes = Column(Text)
    custom_fields = Column(JSONB)
    metadata = Column(JSONB, server_default='{}')
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Relationships
    spot = relationship('ParkingSpot', foreign_keys=[spot_id])
    user = relationship('User', back_populates='reservations', foreign_keys=[user_id])
    vehicle = relationship('Vehicle', foreign_keys=[vehicle_id])
    rate = relationship('ParkingRate', foreign_keys=[rate_id])
    payments = relationship('Payment', back_populates='reservation')
    attendees = relationship('ReservationAttendee', back_populates='reservation', cascade='all, delete-orphan')
    addon_items = relationship('ReservationAddon', back_populates='reservation', cascade='all, delete-orphan')
    feedback = relationship('ReservationFeedback', back_populates='reservation', uselist=False)
    
    __table_args__ = (
        Index('ix_reservations_time_range', 'start_time', 'end_time'),
        Index('ix_reservations_active_times', 'spot_id', 'start_time', 'end_time',
              postgresql_where=text("status IN ('confirmed', 'checked_in')")),
        Index('ix_reservations_user_status', 'user_id', 'status', 'start_time'),
        Index('ix_reservations_guest_email', 'guest_email'),
        Index('ix_reservations_unpaid', 'payment_status', 'end_time',
              postgresql_where=text("payment_status != 'paid'")),
        Index('ix_reservations_current', 'spot_id', 'end_time',
              postgresql_where=text(
                  "status IN ('confirmed', 'checked_in') "
                  "AND start_time <= CURRENT_TIMESTAMP "
                  "AND end_time >= CURRENT_TIMESTAMP"
              )),
    )
    
    @hybrid_property
    def is_active(self):
        """Check if reservation is currently active"""
        return (self.status in ['confirmed', 'checked_in'] and
                self.start_time <= datetime.now(self.start_time.tzinfo) <= self.end_time)
    
    @hybrid_property
    def is_upcoming(self):
        """Check if reservation is upcoming"""
        return self.status == 'confirmed' and self.start_time > datetime.now(self.start_time.tzinfo)
    
    def __repr__(self):
        return f"<Reservation(id={self.id}, number={self.reservation_number}, status={self.status})>"


class ReservationAttendee(Base):
    """Attendees for group reservations"""
    __tablename__ = 'reservation_attendees'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='CASCADE'), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100))
    email = Column(String(255))
    phone = Column(String(20))
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='SET NULL'))
    license_plate = Column(String(20))
    spot_id = Column(UUID(as_uuid=True), ForeignKey('parking_spots.id', ondelete='SET NULL'))
    status = Column(String(20), nullable=False, server_default='confirmed')
    checked_in_at = Column(DateTime(timezone=True))
    checked_out_at = Column(DateTime(timezone=True))
    qr_code = Column(Text)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    reservation = relationship('Reservation', back_populates='attendees')
    vehicle = relationship('Vehicle')
    spot = relationship('ParkingSpot')
    
    __table_args__ = (
        Index('ix_attendees_reservation', 'reservation_id'),
        Index('ix_attendees_email', 'email'),
    )


class ReservationAddon(Base):
    """Add-on services for reservations"""
    __tablename__ = 'reservation_addons'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='CASCADE'), nullable=False)
    addon_type = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    quantity = Column(Integer, nullable=False, server_default='1')
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)
    scheduled_time = Column(DateTime(timezone=True))
    completed_time = Column(DateTime(timezone=True))
    status = Column(String(20), server_default='pending')
    provider = Column(String(200))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    reservation = relationship('Reservation', back_populates='addon_items')
    
    __table_args__ = (
        Index('ix_addons_reservation', 'reservation_id'),
    )


class ReservationFeedback(Base):
    """Customer feedback and ratings for reservations"""
    __tablename__ = 'reservation_feedback'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='CASCADE'), nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    rating = Column(Integer, nullable=False)
    review_title = Column(String(200))
    review_text = Column(Text)
    pros = Column(Text)
    cons = Column(Text)
    would_recommend = Column(Boolean)
    categories = Column(JSONB)
    is_public = Column(Boolean, server_default='true')
    is_verified = Column(Boolean, server_default='false')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    reservation = relationship('Reservation', back_populates='feedback')
    user = relationship('User')


class ReservationWaitlist(Base):
    """Waitlist for unavailable parking spots"""
    __tablename__ = 'reservation_waitlist'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    spot_id = Column(UUID(as_uuid=True), ForeignKey('parking_spots.id', ondelete='CASCADE'))
    zone_id = Column(UUID(as_uuid=True), ForeignKey('parking_zones.id', ondelete='CASCADE'))
    spot_type = Column(String(20))
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(20))
    status = Column(String(20), server_default='active')
    priority = Column(Integer, server_default='0')
    notified_at = Column(DateTime(timezone=True))
    converted_reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='SET NULL'))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_waitlist_dates', 'start_date', 'end_date'),
        Index('ix_waitlist_status', 'status'),
    )


class ReservationBlackout(Base):
    """Blackout dates when parking is unavailable"""
    __tablename__ = 'reservation_blackout_dates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spot_id = Column(UUID(as_uuid=True), ForeignKey('parking_spots.id', ondelete='CASCADE'))
    zone_id = Column(UUID(as_uuid=True), ForeignKey('parking_zones.id', ondelete='CASCADE'))
    reason = Column(String(200), nullable=False)
    description = Column(Text)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    is_recurring = Column(Boolean, server_default='false')
    recurring_pattern = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    __table_args__ = (
        Index('ix_blackout_dates', 'start_date', 'end_date'),
    )


# ============================================================================
# PAYMENT PROCESSING MODELS
# ============================================================================

class Payment(Base):
    """
    Core payments table tracking all financial transactions.
    Supports multiple payment methods and providers.
    """
    __tablename__ = 'payments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_number = Column(String(50), nullable=False, unique=True)
    external_id = Column(String(255), unique=True)
    
    # Relationships
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), index=True)
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='SET NULL'))
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('payment_subscriptions.id', ondelete='SET NULL'))
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('payment_invoices.id', ondelete='SET NULL'))
    payment_method_id = Column(UUID(as_uuid=True), ForeignKey('payment_methods.id', ondelete='SET NULL'))
    
    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, server_default='USD')
    amount_refunded = Column(Numeric(10, 2), server_default='0')
    amount_net = Column(Numeric(10, 2))
    
    # Status
    status = Column(String(20), nullable=False, server_default='pending', index=True)
    payment_method_type = Column(String(50))
    provider = Column(String(50))
    transaction_type = Column(String(50), nullable=False)
    
    # Provider details
    provider_payment_id = Column(String(255))
    provider_transaction_id = Column(String(255))
    provider_charge_id = Column(String(255))
    provider_customer_id = Column(String(255))
    
    # Timing
    authorized_at = Column(DateTime(timezone=True))
    captured_at = Column(DateTime(timezone=True))
    paid_at = Column(DateTime(timezone=True), index=True)
    failed_at = Column(DateTime(timezone=True))
    cancelled_at = Column(DateTime(timezone=True))
    
    # Failure details
    failure_code = Column(String(100))
    failure_message = Column(Text)
    
    # Receipt
    receipt_number = Column(String(255))
    receipt_url = Column(String(500))
    receipt_sent = Column(Boolean, server_default='false')
    
    # Description and metadata
    description = Column(String(500))
    metadata = Column(JSONB, server_default='{}')
    
    # Audit
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Relationships
    user = relationship('User', back_populates='payments', foreign_keys=[user_id])
    reservation = relationship('Reservation', back_populates='payments')
    subscription = relationship('PaymentSubscription', back_populates='payments')
    invoice = relationship('PaymentInvoice', back_populates='payments')
    payment_method_rel = relationship('PaymentMethod', foreign_keys=[payment_method_id])
    refunds = relationship('PaymentRefund', back_populates='payment', cascade='all, delete-orphan')
    transactions = relationship('PaymentTransaction', back_populates='payment', cascade='all, delete-orphan')
    fees = relationship('PaymentFee', back_populates='payment', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('ix_payments_status_date', 'status', 'paid_at'),
        Index('ix_payments_amount_currency', 'amount', 'currency'),
        Index('ix_payments_daily_revenue', func.date_trunc('day', paid_at), 'currency',
              postgresql_where=text("status = 'paid'")),
    )
    
    def __repr__(self):
        return f"<Payment(id={self.id}, number={self.payment_number}, amount={self.amount}, status={self.status})>"


class PaymentMethod(Base):
    """Saved payment methods for users"""
    __tablename__ = 'payment_methods'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    payment_method_type = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=False)
    provider_payment_method_id = Column(String(255))
    provider_customer_id = Column(String(255))
    token = Column(String(255))
    
    # Card details
    card_last4 = Column(String(4))
    card_brand = Column(String(50))
    card_expiry_month = Column(Integer)
    card_expiry_year = Column(Integer)
    card_holder_name = Column(String(255))
    card_fingerprint = Column(String(255))
    
    # Bank account details
    bank_account_last4 = Column(String(4))
    bank_name = Column(String(255))
    
    # Billing address
    billing_address_line1 = Column(String(255))
    billing_city = Column(String(100))
    billing_state = Column(String(50))
    billing_postal_code = Column(String(20))
    billing_country = Column(String(2))
    
    # Status
    is_default = Column(Boolean, server_default='false')
    is_verified = Column(Boolean, server_default='false')
    is_active = Column(Boolean, server_default='true')
    
    # Metadata
    metadata = Column(JSONB, server_default='{}')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship('User', back_populates='payment_methods')
    
    __table_args__ = (
        Index('ix_payment_methods_user', 'user_id'),
        Index('ix_payment_methods_fingerprint', 'card_fingerprint'),
        Index('ix_payment_methods_default', 'is_default'),
    )


class PaymentRefund(Base):
    """Payment refunds and credits"""
    __tablename__ = 'payment_refunds'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.id', ondelete='CASCADE'), nullable=False)
    refund_number = Column(String(50), nullable=False, unique=True)
    provider_refund_id = Column(String(255))
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    reason = Column(String(255))
    status = Column(String(50), nullable=False)
    
    requested_at = Column(DateTime(timezone=True), nullable=False)
    processed_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    requires_approval = Column(Boolean, server_default='false')
    approved_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    approved_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Relationships
    payment = relationship('Payment', back_populates='refunds')
    
    __table_args__ = (
        Index('ix_refunds_payment', 'payment_id'),
        Index('ix_refunds_status', 'status'),
    )


class PaymentTransaction(Base):
    """Detailed transaction log for each payment"""
    __tablename__ = 'payment_transactions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.id', ondelete='CASCADE'), nullable=False)
    transaction_type = Column(String(50), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    provider_transaction_id = Column(String(255))
    status = Column(String(50), nullable=False)
    provider_response = Column(JSONB)
    error_code = Column(String(100))
    error_message = Column(Text)
    processed_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    payment = relationship('Payment', back_populates='transactions')


class PaymentFee(Base):
    """Fees associated with payments"""
    __tablename__ = 'payment_fees'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.id', ondelete='CASCADE'), nullable=False)
    fee_type = Column(String(50), nullable=False)
    description = Column(String(255))
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    percentage_rate = Column(Numeric(5, 2))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    payment = relationship('Payment', back_populates='fees')


class PaymentSubscription(Base):
    """Recurring subscriptions for regular parking"""
    __tablename__ = 'payment_subscriptions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    subscription_number = Column(String(50), nullable=False, unique=True)
    provider_subscription_id = Column(String(255))
    plan_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, index=True)
    
    interval = Column(String(20), nullable=False)
    interval_count = Column(Integer, server_default='1')
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    
    trial_period_days = Column(Integer)
    trial_start = Column(DateTime(timezone=True))
    trial_end = Column(DateTime(timezone=True))
    
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True), index=True)
    cancel_at_period_end = Column(Boolean, server_default='false')
    canceled_at = Column(DateTime(timezone=True))
    
    default_payment_method_id = Column(UUID(as_uuid=True), ForeignKey('payment_methods.id', ondelete='SET NULL'))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship('User')
    payments = relationship('Payment', back_populates='subscription')
    invoices = relationship('PaymentInvoice', back_populates='subscription')
    default_payment_method = relationship('PaymentMethod')
    
    __table_args__ = (
        Index('ix_subscriptions_user_active', 'user_id', 'status'),
        Index('ix_subscriptions_active_renewal', 'status', 'current_period_end'),
    )


class PaymentInvoice(Base):
    """Invoices for billing"""
    __tablename__ = 'payment_invoices'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String(50), nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey('payment_subscriptions.id', ondelete='SET NULL'))
    provider_invoice_id = Column(String(255))
    
    status = Column(String(50), nullable=False, index=True)
    amount_due = Column(Numeric(10, 2), nullable=False)
    amount_paid = Column(Numeric(10, 2), server_default='0')
    currency = Column(String(3), nullable=False)
    
    due_date = Column(DateTime(timezone=True))
    issued_date = Column(DateTime(timezone=True))
    paid_date = Column(DateTime(timezone=True))
    pdf_url = Column(String(500))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship('User')
    subscription = relationship('PaymentSubscription', back_populates='invoices')
    payments = relationship('Payment', back_populates='invoice')
    lines = relationship('PaymentInvoiceLine', back_populates='invoice', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('ix_invoices_user', 'user_id'),
        Index('ix_invoices_due_date', 'due_date'),
    )


class PaymentInvoiceLine(Base):
    """Line items for invoices"""
    __tablename__ = 'payment_invoice_lines'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey('payment_invoices.id', ondelete='CASCADE'), nullable=False)
    description = Column(String(500), nullable=False)
    quantity = Column(Integer, server_default='1')
    unit_price = Column(Numeric(10, 2), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    period_start = Column(DateTime(timezone=True))
    period_end = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    invoice = relationship('PaymentInvoice', back_populates='lines')


class PaymentDiscountCode(Base):
    """Discount codes and promotions"""
    __tablename__ = 'payment_discount_codes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    discount_type = Column(String(20), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    apply_to = Column(String(20), nullable=False)
    minimum_amount = Column(Numeric(10, 2))
    maximum_discount = Column(Numeric(10, 2))
    usage_limit = Column(Integer)
    usage_count = Column(Integer, server_default='0')
    per_user_limit = Column(Integer)
    first_time_only = Column(Boolean, server_default='false')
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_to = Column(DateTime(timezone=True))
    is_active = Column(Boolean, server_default='true')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    __table_args__ = (
        Index('ix_discount_codes_code', 'code'),
        Index('ix_discount_codes_valid', 'valid_from', 'valid_to'),
    )


# ============================================================================
# NOTIFICATION SYSTEM MODELS
# ============================================================================

class NotificationTemplate(Base):
    """Templates for different notification types"""
    __tablename__ = 'notification_templates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    notification_type = Column(String(50), nullable=False, index=True)
    channel = Column(String(50), nullable=False, index=True)
    template_type = Column(String(50), nullable=False)
    
    # Content
    subject = Column(String(255))
    preheader = Column(String(255))
    content_html = Column(Text)
    content_text = Column(Text)
    content_json = Column(JSONB)
    template_data = Column(JSONB)
    
    # Variables
    variables = Column(ARRAY(String(100)))
    required_variables = Column(ARRAY(String(100)))
    
    # Status
    is_active = Column(Boolean, server_default='true')
    is_system = Column(Boolean, server_default='false')
    version = Column(Integer, nullable=False, server_default='1')
    
    # Metadata
    metadata = Column(JSONB, server_default='{}')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    deleted_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('ix_notification_templates_code', 'code', unique=True),
    )


class Notification(Base):
    """
    Main notifications table tracking all outgoing notifications.
    Supports multiple channels and delivery tracking.
    """
    __tablename__ = 'notifications'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_number = Column(String(50), nullable=False, unique=True)
    external_id = Column(String(255), unique=True)
    
    # Recipient
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), index=True)
    recipient_email = Column(String(255), index=True)
    recipient_phone = Column(String(20), index=True)
    recipient_device_id = Column(UUID(as_uuid=True), ForeignKey('notification_devices.id', ondelete='SET NULL'))
    
    # Content
    notification_type = Column(String(50), nullable=False, index=True)
    channel = Column(String(50), nullable=False, index=True)
    priority = Column(String(20), nullable=False, server_default='normal')
    template_id = Column(UUID(as_uuid=True), ForeignKey('notification_templates.id', ondelete='SET NULL'))
    template_data = Column(JSONB)
    subject = Column(String(255))
    content_html = Column(Text)
    content_text = Column(Text)
    content_json = Column(JSONB)
    
    # Related entities
    reservation_id = Column(UUID(as_uuid=True), ForeignKey('reservations.id', ondelete='SET NULL'))
    payment_id = Column(UUID(as_uuid=True), ForeignKey('payments.id', ondelete='SET NULL'))
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey('vehicles.id', ondelete='SET NULL'))
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('notification_campaigns.id', ondelete='SET NULL'))
    
    # Status tracking
    status = Column(String(20), nullable=False, server_default='pending', index=True)
    queued_at = Column(DateTime(timezone=True))
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    opened_at = Column(DateTime(timezone=True))
    clicked_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    failure_reason = Column(Text)
    retry_count = Column(Integer, server_default='0')
    next_retry_at = Column(DateTime(timezone=True))
    
    # Provider details
    provider = Column(String(50))
    provider_message_id = Column(String(255))
    provider_response = Column(JSONB)
    
    # Tracking
    tracking_id = Column(String(100), index=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Batch info
    batch_id = Column(UUID(as_uuid=True), ForeignKey('notification_batches.id', ondelete='SET NULL'))
    
    # Metadata
    metadata = Column(JSONB, server_default='{}')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship('User', foreign_keys=[user_id])
    template = relationship('NotificationTemplate')
    reservation = relationship('Reservation')
    payment = relationship('Payment')
    vehicle = relationship('Vehicle')
    campaign = relationship('NotificationCampaign')
    batch = relationship('NotificationBatch')
    logs = relationship('NotificationLog', back_populates='notification', cascade='all, delete-orphan')
    attachments = relationship('NotificationAttachment', back_populates='notification', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('ix_notifications_status_type', 'status', 'notification_type'),
        Index('ix_notifications_pending', 'status', 'priority', 'created_at',
              postgresql_where=text("status = 'pending'")),
        Index('ix_notifications_failed', 'status', 'retry_count', 'next_retry_at',
              postgresql_where=text("status = 'failed'")),
    )
    
    def __repr__(self):
        return f"<Notification(id={self.id}, number={self.notification_number}, type={self.notification_type}, status={self.status})>"


class NotificationDevice(Base):
    """Registered devices for push notifications"""
    __tablename__ = 'notification_devices'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    device_type = Column(String(20), nullable=False)
    device_token = Column(String(500), nullable=False)
    device_name = Column(String(255))
    device_model = Column(String(100))
    os_version = Column(String(50))
    app_version = Column(String(50))
    push_token = Column(String(500))
    
    is_active = Column(Boolean, server_default='true')
    is_verified = Column(Boolean, server_default='false')
    last_active_at = Column(DateTime(timezone=True))
    failed_attempts = Column(Integer, server_default='0')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship('User', back_populates='notification_devices')
    
    __table_args__ = (
        Index('ix_notification_devices_user', 'user_id'),
        Index('ix_notification_devices_token', 'device_token'),
        Index('ix_notification_devices_active', 'is_active'),
    )


class NotificationPreference(Base):
    """User preferences for notification delivery"""
    __tablename__ = 'notification_preferences'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    notification_type = Column(String(50), nullable=False)
    channel = Column(String(50), nullable=False)
    enabled = Column(Boolean, nullable=False, server_default='true')
    frequency = Column(String(20), server_default='immediate')
    quiet_hours_start = Column(Time)
    quiet_hours_end = Column(Time)
    quiet_hours_timezone = Column(String(50))
    max_per_day = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship('User', back_populates='notification_prefs')
    
    __table_args__ = (
        UniqueConstraint('user_id', 'notification_type', 'channel', name='uq_user_notification_channel'),
        Index('ix_notification_prefs_user', 'user_id'),
    )


class NotificationCampaign(Base):
    """Marketing and notification campaigns"""
    __tablename__ = 'notification_campaigns'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    code = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    campaign_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, server_default='draft', index=True)
    
    # Schedule
    scheduled_start = Column(DateTime(timezone=True))
    scheduled_end = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Targeting
    target_audience = Column(JSONB)
    target_channels = Column(ARRAY(String(50)))
    
    # Content
    template_id = Column(UUID(as_uuid=True), ForeignKey('notification_templates.id', ondelete='SET NULL'))
    template_data = Column(JSONB)
    
    # Statistics
    total_recipients = Column(Integer, server_default='0')
    sent_count = Column(Integer, server_default='0')
    delivered_count = Column(Integer, server_default='0')
    opened_count = Column(Integer, server_default='0')
    clicked_count = Column(Integer, server_default='0')
    
    # Metadata
    metadata = Column(JSONB)
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Relationships
    template = relationship('NotificationTemplate')
    notifications = relationship('Notification', back_populates='campaign')
    recipients = relationship('NotificationCampaignRecipient', back_populates='campaign', cascade='all, delete-orphan')


class NotificationCampaignRecipient(Base):
    """Individual recipients of campaign notifications"""
    __tablename__ = 'notification_campaign_recipients'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('notification_campaigns.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    email = Column(String(255))
    phone = Column(String(20))
    notification_id = Column(UUID(as_uuid=True), ForeignKey('notifications.id', ondelete='SET NULL'))
    status = Column(String(20), server_default='pending')
    
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    opened_at = Column(DateTime(timezone=True))
    clicked_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    campaign = relationship('NotificationCampaign', back_populates='recipients')
    user = relationship('User')
    notification = relationship('Notification')
    
    __table_args__ = (
        Index('ix_campaign_recipients_campaign', 'campaign_id'),
        Index('ix_campaign_recipients_user', 'user_id'),
    )


class NotificationLog(Base):
    """Detailed logs of notification events"""
    __tablename__ = 'notification_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True), ForeignKey('notifications.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String(50), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    provider_response = Column(JSONB)
    error_code = Column(String(100))
    error_message = Column(Text)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    notification = relationship('Notification', back_populates='logs')
    
    __table_args__ = (
        Index('ix_notification_logs_notification', 'notification_id'),
        Index('ix_notification_logs_event', 'event_type'),
        Index('ix_notification_logs_timestamp', 'timestamp'),
    )


class NotificationAttachment(Base):
    """Attachments for notifications"""
    __tablename__ = 'notification_attachments'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True), ForeignKey('notifications.id', ondelete='CASCADE'), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100))
    file_size = Column(Integer)
    file_url = Column(String(500))
    content_id = Column(String(255))
    is_inline = Column(Boolean, server_default='false')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Relationships
    notification = relationship('Notification', back_populates='attachments')


class NotificationBatch(Base):
    """Batch processing groups for notifications"""
    __tablename__ = 'notification_batches'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_number = Column(String(50), nullable=False, unique=True)
    name = Column(String(255))
    total_count = Column(Integer, server_default='0')
    processed_count = Column(Integer, server_default='0')
    success_count = Column(Integer, server_default='0')
    failed_count = Column(Integer, server_default='0')
    status = Column(String(20), server_default='processing')
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    
    # Relationships
    notifications = relationship('Notification', back_populates='batch')


# ============================================================================
# AUDIT SYSTEM MODELS
# ============================================================================

class AuditSession(Base):
    """User session tracking for audit purposes"""
    __tablename__ = 'audit_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(255), nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))
    username = Column(String(255))
    email = Column(String(255))
    
    ip_address = Column(String(45), nullable=False)
    ip_location = Column(JSONB)
    user_agent = Column(String(500))
    device_type = Column(String(50))
    browser = Column(String(100))
    os = Column(String(100))
    
    session_start = Column(DateTime(timezone=True), nullable=False)
    session_end = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    is_active = Column(Boolean, server_default='true')
    
    auth_method = Column(String(50))
    mfa_used = Column(Boolean, server_default='false')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship('User', back_populates='audit_sessions')
    events = relationship('AuditEvent', back_populates='session')
    
    __table_args__ = (
        Index('ix_audit_sessions_user', 'user_id'),
        Index('ix_audit_sessions_ip', 'ip_address'),
        Index('ix_audit_sessions_start', 'session_start'),
    )


class AuditEvent(Base):
    """
    Main audit events table tracking all system actions.
    Provides comprehensive audit trail for compliance and security.
    """
    __tablename__ = 'audit_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(100), nullable=False, unique=True)
    correlation_id = Column(String(100), index=True)
    
    # Actor information
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), index=True)
    username = Column(String(255))
    email = Column(String(255))
    role = Column(String(100))
    session_id = Column(String(255), ForeignKey('audit_sessions.session_id', ondelete='SET NULL'))
    
    # Action details
    action = Column(String(50), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    severity = Column(String(20), nullable=False, server_default='INFO', index=True)
    
    # Resource details
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(255))
    resource_name = Column(String(255))
    
    # Request details
    request_id = Column(String(100))
    request_method = Column(String(10))
    request_url = Column(String(1000))
    request_headers = Column(JSONB)
    request_params = Column(JSONB)
    request_body = Column(JSONB)
    
    # Response details
    response_status = Column(Integer)
    response_headers = Column(JSONB)
    response_body = Column(JSONB)
    response_time_ms = Column(Integer)
    
    # IP and location
    ip_address = Column(String(45), nullable=False, index=True)
    ip_location = Column(JSONB)
    user_agent = Column(String(500))
    
    # Changes
    changes = Column(JSONB)
    before_state = Column(JSONB)
    after_state = Column(JSONB)
    
    # Compliance
    compliance_tags = Column(ARRAY(String(50)))
    sensitive_data = Column(Boolean, server_default='false')
    pii_present = Column(Boolean, server_default='false')
    
    # Metadata
    tags = Column(ARRAY(String(100)))
    metadata = Column(JSONB, server_default='{}')
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    
    # Relationships
    user = relationship('User', back_populates='audit_logs', foreign_keys=[user_id])
    session = relationship('AuditSession', back_populates='events')
    
    __table_args__ = (
        Index('ix_audit_events_composite_search', 'created_at', 'category', 'action', 'user_id'),
        Index('ix_audit_events_resource_search', 'resource_type', 'resource_id', 'created_at'),
        Index('ix_audit_events_security', 'severity', 'status', 'created_at',
              postgresql_where=text("severity IN ('ERROR', 'CRITICAL', 'ALERT')")),
        Index('ix_audit_events_changes_gin', changes, postgresql_using='gin'),
    )
    
    def __repr__(self):
        return f"<AuditEvent(id={self.event_id}, action={self.action}, user={self.username})>"


class AuditChange(Base):
    """Detailed field-level changes for audit"""
    __tablename__ = 'audit_changes'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(100), ForeignKey('audit_events.event_id', ondelete='CASCADE'), nullable=False)
    table_name = Column(String(255), nullable=False)
    record_id = Column(String(255), nullable=False)
    field_name = Column(String(255), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    data_type = Column(String(50))
    
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    __table_args__ = (
        Index('ix_audit_changes_event', 'event_id'),
        Index('ix_audit_changes_record', 'table_name', 'record_id'),
    )


# ============================================================================
# EXPORT ALL MODELS
# ============================================================================

__all__ = [
    # Base
    'Base',
    'metadata',
    
    # User Management
    'User',
    'Role',
    'UserRole',
    'Permission',
    
    # Vehicle Management
    'VehicleMake',
    'VehicleModel',
    'VehicleType',
    'Vehicle',
    'VehicleRegistration',
    'VehicleInsurance',
    'VehicleInspection',
    'VehicleMaintenance',
    'VehicleImage',
    'VehicleDocument',
    'VehiclePreference',
    'VehicleViolation',
    'VehicleAccessHistory',
    'VehicleLocationHistory',
    'VehicleDevice',
    
    # Parking Management
    'ParkingZone',
    'ParkingSpot',
    'ParkingRate',
    'ParkingSession',
    'SpotSensor',
    'SpotMaintenance',
    'SpotOccupancyHistory',
    
    # Reservation Management
    'Reservation',
    'ReservationAttendee',
    'ReservationAddon',
    'ReservationFeedback',
    'ReservationWaitlist',
    'ReservationBlackout',
    
    # Payment Processing
    'Payment',
    'PaymentMethod',
    'PaymentRefund',
    'PaymentTransaction',
    'PaymentFee',
    'PaymentSubscription',
    'PaymentInvoice',
    'PaymentInvoiceLine',
    'PaymentDiscountCode',
    
    # Notification System
    'NotificationTemplate',
    'Notification',
    'NotificationDevice',
    'NotificationPreference',
    'NotificationCampaign',
    'NotificationCampaignRecipient',
    'NotificationLog',
    'NotificationAttachment',
    'NotificationBatch',
    
    # Audit System
    'AuditSession',
    'AuditEvent',
    'AuditChange',
]


# ============================================================================
# EVENT LISTENERS AND HOOKS
# ============================================================================

@event.listens_for(User, 'before_insert')
def user_before_insert(mapper, connection, target):
    """Generate verification token for new users"""
    if not target.verification_token:
        target.verification_token = hashlib.sha256(
            f"{target.email}{datetime.utcnow().timestamp()}".encode()
        ).hexdigest()


@event.listens_for(Vehicle, 'before_insert')
def vehicle_before_insert(mapper, connection, target):
    """Auto-generate vehicle number if not provided"""
    if not target.vehicle_number:
        # This would normally be handled by database sequence
        pass


@event.listens_for(Reservation, 'before_update')
def reservation_before_update(mapper, connection, target):
    """Track modification count"""
    if target.id:
        # Get old values and increment modified_count
        target.modified_count += 1
        target.last_modified_at = func.now()


@event.listens_for(Payment, 'after_update')
def payment_after_update(mapper, connection, target):
    """Update related reservation payment status"""
    if target.reservation_id and target.status == 'paid':
        connection.execute(
            Reservation.__table__.update().where(Reservation.id == target.reservation_id).values(payment_status='paid')
        )