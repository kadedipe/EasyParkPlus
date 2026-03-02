# parking-management/data/migrations/models/vehicle.py

"""
Vehicle model for parking management system.

This module defines the Vehicle model and related classes for managing
vehicle information, registrations, insurance, inspections, maintenance,
violations, and enforcement.
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
import re
from datetime import datetime, date, timedelta
import logging
from typing import Optional, List, Dict, Any, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Create base class
Base = declarative_base()


class VehicleStatus(str, enum.Enum):
    """Enum for vehicle status."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'
    BANNED = 'banned'
    PENDING_VERIFICATION = 'pending_verification'
    ARCHIVED = 'archived'
    DELETED = 'deleted'


class VehicleType(str, enum.Enum):
    """Enum for vehicle types."""
    CAR = 'car'
    SUV = 'suv'
    TRUCK = 'truck'
    VAN = 'van'
    MOTORCYCLE = 'motorcycle'
    SCOOTER = 'scooter'
    BICYCLE = 'bicycle'
    EV = 'ev'
    HYBRID = 'hybrid'
    LUXURY = 'luxury'
    CLASSIC = 'classic'
    COMMERCIAL = 'commercial'
    EMERGENCY = 'emergency'
    GOVERNMENT = 'government'
    DIPLOMATIC = 'diplomatic'
    RENTAL = 'rental'
    RIDESHARE = 'rideshare'


class VehicleClass(str, enum.Enum):
    """Enum for vehicle classes."""
    COMPACT = 'compact'
    MIDSIZE = 'midsize'
    FULLSIZE = 'fullsize'
    ECONOMY = 'economy'
    PREMIUM = 'premium'
    LUXURY = 'luxury'
    SPORTS = 'sports'
    OFF_ROAD = 'off_road'
    COMMERCIAL_LIGHT = 'commercial_light'
    COMMERCIAL_HEAVY = 'commercial_heavy'


class FuelType(str, enum.Enum):
    """Enum for fuel types."""
    GASOLINE = 'gasoline'
    DIESEL = 'diesel'
    ELECTRIC = 'electric'
    HYBRID = 'hybrid'
    PLUG_IN_HYBRID = 'plug_in_hybrid'
    HYDROGEN = 'hydrogen'
    CNG = 'cng'
    LPG = 'lpg'
    ETHANOL = 'ethanol'


class TransmissionType(str, enum.Enum):
    """Enum for transmission types."""
    MANUAL = 'manual'
    AUTOMATIC = 'automatic'
    CVT = 'cvt'
    SEMI_AUTOMATIC = 'semi_automatic'
    DUAL_CLUTCH = 'dual_clutch'


class DriveType(str, enum.Enum):
    """Enum for drive types."""
    FWD = 'fwd'
    RWD = 'rwd'
    AWD = 'awd'
    FOUR_WD = '4wd'
    FOUR_X_FOUR = '4x4'


class RegistrationStatus(str, enum.Enum):
    """Enum for registration status."""
    CURRENT = 'current'
    EXPIRED = 'expired'
    PENDING = 'pending'
    SUSPENDED = 'suspended'
    REVOKED = 'revoked'
    RENEWAL_DUE = 'renewal_due'


class InsuranceStatus(str, enum.Enum):
    """Enum for insurance status."""
    ACTIVE = 'active'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'
    PENDING = 'pending'
    LAPSED = 'lapsed'


class InspectionStatus(str, enum.Enum):
    """Enum for inspection status."""
    PASSED = 'passed'
    FAILED = 'failed'
    PENDING = 'pending'
    SCHEDULED = 'scheduled'
    WAIVED = 'waived'


class ViolationType(str, enum.Enum):
    """Enum for violation types."""
    EXPIRED_METER = 'expired_meter'
    NO_PERMIT = 'no_permit'
    HANDICAP_VIOLATION = 'handicap_violation'
    FIRE_LANE = 'fire_lane'
    LOADING_ZONE = 'loading_zone'
    RESERVED_SPOT = 'reserved_spot'
    OVERTIME_PARKING = 'overtime_parking'
    IMPROPER_PARKING = 'improper_parking'
    EXPIRED_REGISTRATION = 'expired_registration'
    NO_INSURANCE = 'no_insurance'
    STOLEN_VEHICLE = 'stolen_vehicle'
    SUSPICIOUS = 'suspicious'


class ViolationSeverity(str, enum.Enum):
    """Enum for violation severity."""
    WARNING = 'warning'
    MINOR = 'minor'
    MODERATE = 'moderate'
    SEVERE = 'severe'
    CRITICAL = 'critical'


class AlertType(str, enum.Enum):
    """Enum for alert types."""
    STOLEN = 'stolen'
    SUSPICIOUS = 'suspicious'
    WANTED = 'wanted'
    AMBER_ALERT = 'amber_alert'
    SILVER_ALERT = 'silver_alert'
    OUTSTANDING_WARRANT = 'outstanding_warrant'
    UNPAID_TICKETS = 'unpaid_tickets'
    EXPIRED_REGISTRATION = 'expired_registration'
    EXPIRED_INSURANCE = 'expired_insurance'
    MAINTENANCE_DUE = 'maintenance_due'
    INSPECTION_DUE = 'inspection_due'


class AlertPriority(str, enum.Enum):
    """Enum for alert priority."""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'
    EMERGENCY = 'emergency'


class AccessMethod(str, enum.Enum):
    """Enum for access methods."""
    RFID = 'rfid'
    LICENSE_PLATE = 'license_plate'
    QR_CODE = 'qr_code'
    BARCODE = 'barcode'
    MANUAL_ENTRY = 'manual_entry'
    MOBILE_APP = 'mobile_app'
    FACIAL_RECOGNITION = 'facial_recognition'
    BLUETOOTH = 'bluetooth'
    WIFI = 'wifi'


class OwnershipType(str, enum.Enum):
    """Enum for ownership types."""
    OWNER = 'owner'
    LESSEE = 'lessee'
    RENTER = 'renter'
    COMPANY = 'company'
    FLEET = 'fleet'
    GOVERNMENT = 'government'


class VehicleMake(Base):
    """
    Vehicle manufacturers reference table.
    
    Stores information about vehicle makes/manufacturers.
    """
    
    __tablename__ = 'vehicle_makes'
    __table_args__ = (
        Index('ix_vehicle_makes_name', 'name', unique=True),
        Index('ix_vehicle_makes_is_active', 'is_active'),
        {'comment': 'Vehicle manufacturers reference'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    name = Column(
        String(100),
        nullable=False,
        unique=True,
        comment='Make name (e.g., toyota, honda)'
    )
    
    display_name = Column(
        String(100),
        nullable=False,
        comment='Display name (e.g., Toyota, Honda)'
    )
    
    country = Column(
        String(100),
        comment='Country of origin'
    )
    
    founded_year = Column(
        Integer,
        comment='Year founded'
    )
    
    website = Column(
        String(255),
        comment='Official website'
    )
    
    logo_url = Column(
        String(500),
        comment='URL to manufacturer logo'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether make is active'
    )
    
    is_popular = Column(
        Boolean,
        server_default='false',
        comment='Whether make is popular'
    )
    
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
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
    models = relationship(
        'VehicleModel',
        back_populates='make',
        cascade='all, delete-orphan',
        comment='Models for this make'
    )
    
    vehicles = relationship(
        'Vehicle',
        back_populates='make_info',
        comment='Vehicles of this make'
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert make to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'display_name': self.display_name,
            'country': self.country,
            'founded_year': self.founded_year,
            'website': self.website,
            'logo_url': self.logo_url,
            'is_popular': self.is_popular,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleMake(id={self.id}, name={self.name})>"


class VehicleModel(Base):
    """
    Vehicle models reference table.
    
    Stores information about specific vehicle models.
    """
    
    __tablename__ = 'vehicle_models'
    __table_args__ = (
        UniqueConstraint('make_id', 'name', name='uq_vehicle_model_make_name'),
        Index('ix_vehicle_models_type', 'vehicle_type'),
        Index('ix_vehicle_models_is_active', 'is_active'),
        {'comment': 'Vehicle models reference'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    make_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicle_makes.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the make'
    )
    
    name = Column(
        String(100),
        nullable=False,
        comment='Model name (e.g., camry, civic)'
    )
    
    display_name = Column(
        String(100),
        nullable=False,
        comment='Display name (e.g., Camry, Civic)'
    )
    
    vehicle_type = Column(
        String(50),
        comment='Type of vehicle'
    )
    
    vehicle_class = Column(
        String(50),
        comment='Class of vehicle'
    )
    
    start_year = Column(
        Integer,
        comment='Production start year'
    )
    
    end_year = Column(
        Integer,
        comment='Production end year (if discontinued)'
    )
    
    fuel_types = Column(
        ARRAY(String(50)),
        comment='Available fuel types'
    )
    
    transmission_types = Column(
        ARRAY(String(50)),
        comment='Available transmission types'
    )
    
    drive_types = Column(
        ARRAY(String(50)),
        comment='Available drive types'
    )
    
    engine_sizes = Column(
        ARRAY(String(20)),
        comment='Available engine sizes'
    )
    
    length_mm = Column(
        Integer,
        comment='Length in millimeters'
    )
    
    width_mm = Column(
        Integer,
        comment='Width in millimeters'
    )
    
    height_mm = Column(
        Integer,
        comment='Height in millimeters'
    )
    
    weight_kg = Column(
        Integer,
        comment='Weight in kilograms'
    )
    
    image_url = Column(
        String(500),
        comment='URL to model image'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether model is active'
    )
    
    is_popular = Column(
        Boolean,
        server_default='false',
        comment='Whether model is popular'
    )
    
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
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
    make = relationship('VehicleMake', back_populates='models')
    vehicles = relationship('Vehicle', back_populates='model_info')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'id': str(self.id),
            'make_id': str(self.make_id),
            'make_name': self.make.display_name if self.make else None,
            'name': self.name,
            'display_name': self.display_name,
            'vehicle_type': self.vehicle_type,
            'vehicle_class': self.vehicle_class,
            'start_year': self.start_year,
            'end_year': self.end_year,
            'fuel_types': self.fuel_types,
            'transmission_types': self.transmission_types,
            'drive_types': self.drive_types,
            'engine_sizes': self.engine_sizes,
            'dimensions': {
                'length_mm': self.length_mm,
                'width_mm': self.width_mm,
                'height_mm': self.height_mm,
                'weight_kg': self.weight_kg,
            } if any([self.length_mm, self.width_mm]) else None,
            'image_url': self.image_url,
            'is_popular': self.is_popular,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleModel(id={self.id}, name={self.name})>"


class VehicleType(Base):
    """
    Vehicle type classifications.
    
    Defines vehicle types and their characteristics for parking rules.
    """
    
    __tablename__ = 'vehicle_types'
    __table_args__ = (
        Index('ix_vehicle_types_name', 'name', unique=True),
        Index('ix_vehicle_types_category', 'category'),
        Index('ix_vehicle_types_is_active', 'is_active'),
        {'comment': 'Vehicle type classifications'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    name = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Type name (e.g., car, suv, truck)'
    )
    
    display_name = Column(
        String(50),
        nullable=False,
        comment='Display name (e.g., Car, SUV, Truck)'
    )
    
    description = Column(
        Text,
        comment='Type description'
    )
    
    category = Column(
        String(50),
        comment='Category (passenger, commercial, motorcycle)'
    )
    
    default_height_cm = Column(
        Integer,
        comment='Default height in centimeters'
    )
    
    default_width_cm = Column(
        Integer,
        comment='Default width in centimeters'
    )
    
    default_length_cm = Column(
        Integer,
        comment='Default length in centimeters'
    )
    
    default_weight_kg = Column(
        Integer,
        comment='Default weight in kilograms'
    )
    
    requires_special_spot = Column(
        Boolean,
        server_default='false',
        comment='Whether requires special spot type'
    )
    
    special_spot_types = Column(
        ARRAY(String(50)),
        comment='Required spot types'
    )
    
    max_parking_duration_hours = Column(
        Integer,
        comment='Maximum parking duration in hours'
    )
    
    rate_multiplier = Column(
        Numeric(3, 2),
        server_default='1.0',
        comment='Rate multiplier for this type'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether type is active'
    )
    
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert type to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category,
            'default_dimensions': {
                'height_cm': self.default_height_cm,
                'width_cm': self.default_width_cm,
                'length_cm': self.default_length_cm,
                'weight_kg': self.default_weight_kg,
            } if any([self.default_height_cm, self.default_width_cm]) else None,
            'requires_special_spot': self.requires_special_spot,
            'special_spot_types': self.special_spot_types,
            'max_parking_duration_hours': self.max_parking_duration_hours,
            'rate_multiplier': float(self.rate_multiplier) if self.rate_multiplier else 1.0,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleType(id={self.id}, name={self.name})>"


class Vehicle(Base):
    """
    Main vehicles table with comprehensive vehicle information.
    
    Tracks all vehicles registered in the system with their details,
    compliance status, and usage history.
    """
    
    __tablename__ = 'vehicles'
    __table_args__ = (
        # Primary indexes
        Index('ix_vehicles_number', 'vehicle_number', unique=True),
        Index('ix_vehicles_vin', 'vin', unique=True),
        Index('ix_vehicles_rfid', 'rfid_tag', unique=True),
        Index('ix_vehicles_transponder', 'transponder_id', unique=True),
        
        # Foreign key indexes
        Index('ix_vehicles_user_id', 'user_id'),
        Index('ix_vehicles_make_id', 'make_id'),
        Index('ix_vehicles_model_id', 'model_id'),
        
        # License plate indexes
        Index('ix_vehicles_license_plate', 'license_plate'),
        Index('ix_vehicles_license_plate_composite', 'license_plate', 'license_plate_state'),
        Index('ix_vehicles_license_plate_gin', text("license_plate gin_trgm_ops"), postgresql_using='gin'),
        
        # VIN indexes
        Index('ix_vehicles_vin_gin', text("vin gin_trgm_ops"), postgresql_using='gin'),
        
        # Status indexes
        Index('ix_vehicles_status', 'status'),
        Index('ix_vehicles_type', 'vehicle_type'),
        Index('ix_vehicles_color', 'color'),
        
        # Compliance indexes
        Index('ix_vehicles_compliance', 'registration_expiry', 'insurance_expiry', 'inspection_expiry'),
        Index('ix_vehicles_registration_expiry', 'registration_expiry'),
        Index('ix_vehicles_insurance_expiry', 'insurance_expiry'),
        Index('ix_vehicles_inspection_expiry', 'inspection_expiry'),
        
        # Enforcement indexes
        Index('ix_vehicles_is_blacklisted', 'is_blacklisted'),
        Index('ix_vehicles_is_stolen', 'is_stolen'),
        
        # Time-based indexes
        Index('ix_vehicles_created_at', 'created_at'),
        Index('ix_vehicles_last_parking_at', 'last_parking_at'),
        
        # Composite indexes for common queries
        Index('ix_vehicles_user_status', 'user_id', 'status'),
        Index('ix_vehicles_type_make', 'vehicle_type', 'make_id'),
        
        # Partial indexes
        Index('ix_vehicles_expired', 'registration_expiry', 'insurance_expiry',
              postgresql_where=text("status = 'active'")),
        Index('ix_vehicles_expiring_30_days', 'registration_expiry', 'insurance_expiry',
              postgresql_where=text(
                  "status = 'active' AND "
                  "(registration_expiry BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days' "
                  "OR insurance_expiry BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days')"
              )),
        
        # Covering index for common lookups
        Index('ix_vehicles_covering_lookup', 'license_plate', 'license_plate_state', 
              'status', 'vehicle_type', 'user_id'),
        
        # Check constraints
        CheckConstraint(
            "status IN ('active', 'inactive', 'suspended', 'banned', 'pending_verification', 'archived', 'deleted')",
            name='ck_vehicles_status'
        ),
        CheckConstraint(
            "ownership_type IN ('owner', 'lessee', 'renter', 'company', 'fleet', 'government')",
            name='ck_vehicles_ownership'
        ),
        CheckConstraint(
            "fuel_type IN ('gasoline', 'diesel', 'electric', 'hybrid', 'plug_in_hybrid', 'hydrogen', 'cng', 'lpg', 'ethanol')",
            name='ck_vehicles_fuel_type'
        ),
        CheckConstraint(
            "transmission_type IN ('manual', 'automatic', 'cvt', 'semi_automatic', 'dual_clutch')",
            name='ck_vehicles_transmission'
        ),
        CheckConstraint(
            "drive_type IN ('fwd', 'rwd', 'awd', '4wd', '4x4')",
            name='ck_vehicles_drive_type'
        ),
        CheckConstraint(
            "LENGTH(vin) = 17 OR vin IS NULL",
            name='ck_vehicles_vin_length'
        ),
        
        # Table comment
        {'comment': 'Main vehicles table with comprehensive vehicle information'}
    )
    
    # =========================================================================
    # PRIMARY KEY AND IDENTIFIERS
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_number = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Unique human-readable vehicle number'
    )
    
    # =========================================================================
    # OWNER RELATIONSHIP
    # =========================================================================
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle owner'
    )
    
    ownership_type = Column(
        String(50),
        nullable=False,
        server_default='owner',
        comment='Type of ownership (owner, lessee, company, etc.)'
    )
    
    company_id = Column(
        String(100),
        comment='Company identifier for fleet/corporate vehicles'
    )
    
    # =========================================================================
    # LICENSE PLATE
    # =========================================================================
    license_plate = Column(
        String(20),
        nullable=False,
        comment='License plate number'
    )
    
    license_plate_state = Column(
        String(50),
        comment='State or province of issuance'
    )
    
    license_plate_country = Column(
        String(2),
        comment='Country of issuance (ISO 3166-1 alpha-2)'
    )
    
    license_plate_issue_date = Column(
        Date,
        comment='Date when plate was issued'
    )
    
    license_plate_expiry_date = Column(
        Date,
        comment='Expiry date of plate registration'
    )
    
    license_plate_type = Column(
        String(50),
        comment='Type of plate (standard, personalized, temporary)'
    )
    
    # =========================================================================
    # VEHICLE IDENTIFICATION
    # =========================================================================
    vin = Column(
        String(17),
        unique=True,
        comment='Vehicle Identification Number'
    )
    
    make_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicle_makes.id', ondelete='SET NULL'),
        comment='ID of vehicle make'
    )
    
    model_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicle_models.id', ondelete='SET NULL'),
        comment='ID of vehicle model'
    )
    
    vehicle_type = Column(
        String(50),
        nullable=False,
        comment='Type of vehicle'
    )
    
    vehicle_class = Column(
        String(50),
        comment='Class of vehicle'
    )
    
    year = Column(
        Integer,
        comment='Model year'
    )
    
    trim = Column(
        String(100),
        comment='Trim level'
    )
    
    color = Column(
        String(50),
        comment='Primary color'
    )
    
    color_code = Column(
        String(10),
        comment='Color code (hex)'
    )
    
    secondary_color = Column(
        String(50),
        comment='Secondary color'
    )
    
    # =========================================================================
    # PHYSICAL CHARACTERISTICS
    # =========================================================================
    length_cm = Column(
        Integer,
        comment='Length in centimeters'
    )
    
    width_cm = Column(
        Integer,
        comment='Width in centimeters'
    )
    
    height_cm = Column(
        Integer,
        comment='Height in centimeters'
    )
    
    weight_kg = Column(
        Integer,
        comment='Weight in kilograms'
    )
    
    wheelbase_cm = Column(
        Integer,
        comment='Wheelbase in centimeters'
    )
    
    ground_clearance_cm = Column(
        Integer,
        comment='Ground clearance in centimeters'
    )
    
    number_of_axles = Column(
        Integer,
        server_default='2',
        comment='Number of axles'
    )
    
    number_of_wheels = Column(
        Integer,
        server_default='4',
        comment='Number of wheels'
    )
    
    # =========================================================================
    # PROPULSION
    # =========================================================================
    fuel_type = Column(
        String(50),
        comment='Type of fuel'
    )
    
    fuel_capacity_liters = Column(
        Float,
        comment='Fuel capacity in liters'
    )
    
    fuel_efficiency_city = Column(
        Float,
        comment='City fuel efficiency (L/100km)'
    )
    
    fuel_efficiency_highway = Column(
        Float,
        comment='Highway fuel efficiency (L/100km)'
    )
    
    fuel_efficiency_combined = Column(
        Float,
        comment='Combined fuel efficiency (L/100km)'
    )
    
    battery_capacity_kwh = Column(
        Float,
        comment='Battery capacity in kWh (for EVs)'
    )
    
    electric_range_km = Column(
        Integer,
        comment='Electric range in kilometers'
    )
    
    emissions_rating = Column(
        String(20),
        comment='Emissions rating (Euro standard, etc.)'
    )
    
    # =========================================================================
    # DRIVETRAIN
    # =========================================================================
    transmission_type = Column(
        String(50),
        comment='Type of transmission'
    )
    
    transmission_speeds = Column(
        Integer,
        comment='Number of transmission speeds'
    )
    
    drive_type = Column(
        String(20),
        comment='Type of drive (FWD, RWD, AWD, etc.)'
    )
    
    engine_type = Column(
        String(100),
        comment='Engine type'
    )
    
    engine_displacement_cc = Column(
        Integer,
        comment='Engine displacement in cubic centimeters'
    )
    
    horsepower = Column(
        Integer,
        comment='Horsepower'
    )
    
    # =========================================================================
    # FEATURES
    # =========================================================================
    has_sunroof = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle has sunroof'
    )
    
    has_convertible = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle is convertible'
    )
    
    has_third_row = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle has third row seating'
    )
    
    has_tow_hitch = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle has tow hitch'
    )
    
    towing_capacity_kg = Column(
        Integer,
        comment='Towing capacity in kilograms'
    )
    
    has_roof_rack = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle has roof rack'
    )
    
    roof_rack_type = Column(
        String(50),
        comment='Type of roof rack'
    )
    
    has_bike_rack = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle has bike rack'
    )
    
    has_ski_rack = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle has ski rack'
    )
    
    # =========================================================================
    # EV SPECIFIC
    # =========================================================================
    has_ev_charger = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle has EV charger'
    )
    
    ev_charger_type = Column(
        String(50),
        comment='Type of EV charger (Level 1, Level 2, DC Fast)'
    )
    
    ev_charger_port = Column(
        String(50),
        comment='Charger port type (J1772, CCS, CHAdeMO, Tesla)'
    )
    
    ev_charger_power_kw = Column(
        Float,
        comment='Charger power in kW'
    )
    
    # =========================================================================
    # ACCESS AND IDENTIFICATION
    # =========================================================================
    has_rfid = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle has RFID tag'
    )
    
    rfid_tag = Column(
        String(100),
        unique=True,
        comment='RFID tag identifier'
    )
    
    has_transponder = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle has transponder'
    )
    
    transponder_id = Column(
        String(100),
        unique=True,
        comment='Transponder identifier'
    )
    
    has_permit = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle has parking permit'
    )
    
    permit_number = Column(
        String(100),
        comment='Permit number'
    )
    
    permit_expiry = Column(
        Date,
        comment='Permit expiry date'
    )
    
    permit_type = Column(
        String(50),
        comment='Type of permit'
    )
    
    permit_zone = Column(
        String(50),
        comment='Permitted zone'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    status = Column(
        String(20),
        nullable=False,
        server_default='active',
        comment='Current vehicle status'
    )
    
    is_verified = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle is verified'
    )
    
    verified_at = Column(
        DateTime(timezone=True),
        comment='When vehicle was verified'
    )
    
    verified_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who verified vehicle'
    )
    
    is_blacklisted = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle is blacklisted'
    )
    
    blacklisted_at = Column(
        DateTime(timezone=True),
        comment='When vehicle was blacklisted'
    )
    
    blacklisted_reason = Column(
        Text,
        comment='Reason for blacklisting'
    )
    
    is_stolen = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle is reported stolen'
    )
    
    stolen_reported_at = Column(
        DateTime(timezone=True),
        comment='When theft was reported'
    )
    
    stolen_recovered_at = Column(
        DateTime(timezone=True),
        comment='When vehicle was recovered'
    )
    
    # =========================================================================
    # USAGE STATISTICS
    # =========================================================================
    total_parking_sessions = Column(
        Integer,
        server_default='0',
        comment='Total number of parking sessions'
    )
    
    total_parking_duration_minutes = Column(
        Integer,
        server_default='0',
        comment='Total parking duration in minutes'
    )
    
    total_parking_amount = Column(
        Numeric(10, 2),
        server_default='0',
        comment='Total parking amount paid'
    )
    
    last_parking_at = Column(
        DateTime(timezone=True),
        comment='Timestamp of last parking'
    )
    
    last_parking_spot = Column(
        String(50),
        comment='Last parking spot used'
    )
    
    last_parking_zone = Column(
        String(100),
        comment='Last parking zone used'
    )
    
    average_parking_duration = Column(
        Integer,
        comment='Average parking duration in minutes'
    )
    
    favorite_zone = Column(
        String(100),
        comment='Most frequently used zone'
    )
    
    favorite_time = Column(
        Time,
        comment='Most frequent parking time'
    )
    
    # =========================================================================
    # COMPLIANCE
    # =========================================================================
    registration_status = Column(
        String(50),
        comment='Registration status'
    )
    
    registration_expiry = Column(
        Date,
        comment='Registration expiry date'
    )
    
    insurance_status = Column(
        String(50),
        comment='Insurance status'
    )
    
    insurance_expiry = Column(
        Date,
        comment='Insurance expiry date'
    )
    
    inspection_status = Column(
        String(50),
        comment='Inspection status'
    )
    
    inspection_expiry = Column(
        Date,
        comment='Inspection expiry date'
    )
    
    # =========================================================================
    # ALERTS AND FLAGS
    # =========================================================================
    has_active_alerts = Column(
        Boolean,
        server_default='false',
        comment='Whether vehicle has active alerts'
    )
    
    alert_count = Column(
        Integer,
        server_default='0',
        comment='Number of active alerts'
    )
    
    violation_count = Column(
        Integer,
        server_default='0',
        comment='Number of violations'
    )
    
    unpaid_violations = Column(
        Integer,
        server_default='0',
        comment='Number of unpaid violations'
    )
    
    unpaid_amount = Column(
        Numeric(10, 2),
        server_default='0',
        comment='Total unpaid amount'
    )
    
    # =========================================================================
    # NOTES AND METADATA
    # =========================================================================
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    special_instructions = Column(
        Text,
        comment='Special instructions for this vehicle'
    )
    
    tags = Column(
        ARRAY(String(50)),
        comment='Custom tags'
    )
    
    custom_fields = Column(
        JSONB,
        comment='Custom fields'
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
    owner = relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='vehicles',
        comment='Vehicle owner'
    )
    
    make_info = relationship(
        'VehicleMake',
        foreign_keys=[make_id],
        back_populates='vehicles',
        comment='Vehicle make information'
    )
    
    model_info = relationship(
        'VehicleModel',
        foreign_keys=[model_id],
        back_populates='vehicles',
        comment='Vehicle model information'
    )
    
    verifier = relationship(
        'User',
        foreign_keys=[verified_by],
        comment='User who verified vehicle'
    )
    
    creator = relationship(
        'User',
        foreign_keys=[created_by],
        comment='User who created record'
    )
    
    updater = relationship(
        'User',
        foreign_keys=[updated_by],
        comment='User who last updated record'
    )
    
    registrations = relationship(
        'VehicleRegistration',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Registration records'
    )
    
    insurance_policies = relationship(
        'VehicleInsurance',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Insurance policies'
    )
    
    inspections = relationship(
        'VehicleInspection',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Inspection records'
    )
    
    maintenance_records = relationship(
        'VehicleMaintenance',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Maintenance records'
    )
    
    images = relationship(
        'VehicleImage',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Vehicle images'
    )
    
    documents = relationship(
        'VehicleDocument',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Vehicle documents'
    )
    
    violations = relationship(
        'VehicleViolation',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Parking violations'
    )
    
    access_history = relationship(
        'VehicleAccessHistory',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Access history'
    )
    
    location_history = relationship(
        'VehicleLocationHistory',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Location history'
    )
    
    preferences = relationship(
        'VehiclePreference',
        back_populates='vehicle',
        uselist=False,
        cascade='all, delete-orphan',
        comment='Vehicle preferences'
    )
    
    alerts = relationship(
        'VehicleAlert',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Vehicle alerts'
    )
    
    devices = relationship(
        'VehicleDevice',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='IoT devices'
    )
    
    ownership_history = relationship(
        'VehicleOwnershipHistory',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Ownership history'
    )
    
    tag_assignments = relationship(
        'VehicleTagAssignment',
        back_populates='vehicle',
        cascade='all, delete-orphan',
        comment='Tag assignments'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def is_expired_registration(self) -> bool:
        """Check if registration is expired."""
        if not self.registration_expiry:
            return False
        return self.registration_expiry < date.today()
    
    @hybrid_property
    def is_expired_insurance(self) -> bool:
        """Check if insurance is expired."""
        if not self.insurance_expiry:
            return False
        return self.insurance_expiry < date.today()
    
    @hybrid_property
    def is_expired_inspection(self) -> bool:
        """Check if inspection is expired."""
        if not self.inspection_expiry:
            return False
        return self.inspection_expiry < date.today()
    
    @hybrid_property
    def is_compliant(self) -> bool:
        """Check if vehicle is fully compliant."""
        return not (self.is_expired_registration or 
                   self.is_expired_insurance or 
                   self.is_expired_inspection)
    
    @hybrid_property
    def display_name(self) -> str:
        """Get display name for vehicle."""
        parts = []
        if self.year:
            parts.append(str(self.year))
        if self.make_info:
            parts.append(self.make_info.display_name)
        if self.model_info:
            parts.append(self.model_info.display_name)
        if self.color:
            parts.append(self.color)
        
        if parts:
            return ' '.join(parts)
        return self.license_plate
    
    @hybrid_property
    def requires_attention(self) -> bool:
        """Check if vehicle requires attention."""
        return (self.is_expired_registration or
                self.is_expired_insurance or
                self.is_expired_inspection or
                self.is_blacklisted or
                self.is_stolen or
                self.unpaid_violations > 0)
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @validates('vin')
    def validate_vin(self, key, vin):
        """Validate VIN format (17 characters, alphanumeric)."""
        if vin is None:
            return vin
        
        vin = vin.upper().strip()
        
        # VIN should be 17 characters, alphanumeric, excluding I, O, Q
        if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin):
            raise ValueError('Invalid VIN format: must be 17 alphanumeric characters (excluding I, O, Q)')
        
        return vin
    
    @validates('license_plate')
    def validate_license_plate(self, key, plate):
        """Validate license plate format."""
        if plate:
            plate = plate.upper().strip()
        return plate
    
    @validates('year')
    def validate_year(self, key, year):
        """Validate year is reasonable."""
        if year:
            current_year = datetime.now().year
            if year < 1900 or year > current_year + 1:
                raise ValueError(f'Year must be between 1900 and {current_year + 1}')
        return year
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def verify(self, user_id: uuid.UUID) -> None:
        """
        Mark vehicle as verified.
        
        Args:
            user_id: ID of user performing verification
        """
        self.is_verified = True
        self.verified_at = datetime.now()
        self.verified_by = user_id
    
    def blacklist(self, reason: str, user_id: Optional[uuid.UUID] = None) -> None:
        """
        Add vehicle to blacklist.
        
        Args:
            reason: Reason for blacklisting
            user_id: ID of user performing action
        """
        self.is_blacklisted = True
        self.blacklisted_at = datetime.now()
        self.blacklisted_reason = reason
        self.status = 'suspended'
        self.updated_by = user_id
    
    def remove_from_blacklist(self, user_id: Optional[uuid.UUID] = None) -> None:
        """Remove vehicle from blacklist."""
        self.is_blacklisted = False
        self.blacklisted_at = None
        self.blacklisted_reason = None
        self.status = 'active'
        self.updated_by = user_id
    
    def report_stolen(self, user_id: Optional[uuid.UUID] = None) -> None:
        """Report vehicle as stolen."""
        self.is_stolen = True
        self.stolen_reported_at = datetime.now()
        self.status = 'suspended'
        self.updated_by = user_id
        
        # Create alert
        alert = VehicleAlert(
            vehicle_id=self.id,
            alert_type='stolen',
            priority='critical',
            title='Vehicle Reported Stolen',
            description=f'Vehicle with license plate {self.license_plate} reported stolen',
            issued_at=datetime.now(),
            is_active=True,
            requires_action=True,
            created_by=user_id
        )
        object_session(self).add(alert)
    
    def mark_recovered(self, user_id: Optional[uuid.UUID] = None) -> None:
        """Mark stolen vehicle as recovered."""
        self.is_stolen = False
        self.stolen_recovered_at = datetime.now()
        self.status = 'active'
        self.updated_by = user_id
        
        # Resolve alerts
        for alert in self.alerts:
            if alert.alert_type == 'stolen' and alert.is_active:
                alert.resolve('Vehicle recovered', user_id)
    
    def update_compliance_status(self) -> Dict[str, Any]:
        """
        Update compliance status based on latest records.
        
        Returns:
            Dictionary with updated statuses
        """
        # Get latest registration
        latest_reg = object_session(self).query(VehicleRegistration).filter(
            VehicleRegistration.vehicle_id == self.id
        ).order_by(VehicleRegistration.expiry_date.desc()).first()
        
        if latest_reg:
            self.registration_status = latest_reg.status
            self.registration_expiry = latest_reg.expiry_date
        
        # Get latest insurance
        latest_ins = object_session(self).query(VehicleInsurance).filter(
            VehicleInsurance.vehicle_id == self.id
        ).order_by(VehicleInsurance.expiry_date.desc()).first()
        
        if latest_ins:
            self.insurance_status = latest_ins.status
            self.insurance_expiry = latest_ins.expiry_date
        
        # Get latest inspection
        latest_insp = object_session(self).query(VehicleInspection).filter(
            VehicleInspection.vehicle_id == self.id
        ).order_by(VehicleInspection.expiry_date.desc()).first()
        
        if latest_insp:
            self.inspection_status = latest_insp.status
            self.inspection_expiry = latest_insp.expiry_date
        
        return {
            'registration': {
                'status': self.registration_status,
                'expiry': self.registration_expiry.isoformat() if self.registration_expiry else None
            },
            'insurance': {
                'status': self.insurance_status,
                'expiry': self.insurance_expiry.isoformat() if self.insurance_expiry else None
            },
            'inspection': {
                'status': self.inspection_status,
                'expiry': self.inspection_expiry.isoformat() if self.inspection_expiry else None
            }
        }
    
    def add_violation(
        self,
        violation_type: str,
        severity: str,
        description: str,
        fine_amount: float,
        location: Optional[str] = None,
        evidence_urls: Optional[List[str]] = None,
        issued_by: Optional[uuid.UUID] = None
    ) -> 'VehicleViolation':
        """
        Add a parking violation to the vehicle.
        
        Args:
            violation_type: Type of violation
            severity: Severity level
            description: Violation description
            fine_amount: Fine amount
            location: Location of violation
            evidence_urls: URLs to evidence images
            issued_by: ID of officer who issued violation
            
        Returns:
            Created VehicleViolation instance
        """
        from models.vehicle import VehicleViolation
        
        violation = VehicleViolation(
            vehicle_id=self.id,
            violation_type=violation_type,
            severity=severity,
            description=description,
            location=location,
            timestamp=datetime.now(),
            fine_amount=fine_amount,
            evidence_urls=evidence_urls,
            officer_id=str(issued_by) if issued_by else None,
            created_by=issued_by
        )
        
        object_session(self).add(violation)
        
        # Update vehicle violation counts
        self.violation_count += 1
        self.unpaid_violations += 1
        self.unpaid_amount = float(self.unpaid_amount) + fine_amount
        
        return violation
    
    def record_access(
        self,
        access_method: str,
        access_type: str,
        gate_id: Optional[str] = None,
        confidence: Optional[float] = None,
        image_url: Optional[str] = None,
        session_id: Optional[uuid.UUID] = None
    ) -> 'VehicleAccessHistory':
        """
        Record vehicle access attempt.
        
        Args:
            access_method: Method of access
            access_type: Type of access (entry, exit, denied)
            gate_id: ID of gate
            confidence: Confidence level for plate recognition
            image_url: URL to access image
            session_id: ID of parking session
            
        Returns:
            Created VehicleAccessHistory instance
        """
        from models.vehicle import VehicleAccessHistory
        
        access = VehicleAccessHistory(
            vehicle_id=self.id,
            access_method=access_method,
            access_type=access_type,
            gate_id=gate_id,
            timestamp=datetime.now(),
            image_url=image_url,
            confidence=confidence,
            matched_plate=self.license_plate,
            session_id=session_id
        )
        
        object_session(self).add(access)
        
        return access
    
    def update_statistics(self) -> None:
        """Update vehicle statistics based on parking sessions."""
        from models.parking import ParkingSession
        
        stats = object_session(self).query(
            func.count(ParkingSession.id).label('total_sessions'),
            func.sum(ParkingSession.duration_minutes).label('total_duration'),
            func.sum(ParkingSession.total_amount).label('total_amount'),
            func.max(ParkingSession.start_time).label('last_parking')
        ).filter(ParkingSession.vehicle_id == self.id).first()
        
        if stats:
            self.total_parking_sessions = stats.total_sessions or 0
            self.total_parking_duration_minutes = stats.total_duration or 0
            self.total_parking_amount = stats.total_amount or 0
            self.last_parking_at = stats.last_parking
            
            if self.total_parking_sessions > 0:
                self.average_parking_duration = int(
                    self.total_parking_duration_minutes / self.total_parking_sessions
                )
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert vehicle to dictionary."""
        data = {
            'id': str(self.id),
            'vehicle_number': self.vehicle_number,
            'user_id': str(self.user_id),
            'ownership_type': self.ownership_type,
            'license_plate': self.license_plate,
            'license_plate_state': self.license_plate_state,
            'license_plate_country': self.license_plate_country,
            'license_plate_expiry': self.license_plate_expiry_date.isoformat() if self.license_plate_expiry_date else None,
            'vin': self.vin,
            'make': self.make_info.display_name if self.make_info else None,
            'model': self.model_info.display_name if self.model_info else None,
            'vehicle_type': self.vehicle_type,
            'vehicle_class': self.vehicle_class,
            'year': self.year,
            'trim': self.trim,
            'color': self.color,
            'secondary_color': self.secondary_color,
            'display_name': self.display_name,
            'dimensions': {
                'length_cm': self.length_cm,
                'width_cm': self.width_cm,
                'height_cm': self.height_cm,
                'weight_kg': self.weight_kg,
            } if any([self.length_cm, self.width_cm]) else None,
            'propulsion': {
                'fuel_type': self.fuel_type,
                'fuel_capacity_liters': self.fuel_capacity_liters,
                'battery_capacity_kwh': self.battery_capacity_kwh,
                'electric_range_km': self.electric_range_km,
            } if any([self.fuel_type, self.battery_capacity_kwh]) else None,
            'features': {
                'has_ev_charger': self.has_ev_charger,
                'ev_charger_type': self.ev_charger_type,
                'has_sunroof': self.has_sunroof,
                'has_tow_hitch': self.has_tow_hitch,
                'towing_capacity_kg': self.towing_capacity_kg,
                'has_roof_rack': self.has_roof_rack,
            },
            'access': {
                'has_rfid': self.has_rfid,
                'rfid_tag': self.rfid_tag,
                'has_transponder': self.has_transponder,
                'transponder_id': self.transponder_id,
                'has_permit': self.has_permit,
                'permit_number': self.permit_number,
                'permit_expiry': self.permit_expiry.isoformat() if self.permit_expiry else None,
                'permit_type': self.permit_type,
                'permit_zone': self.permit_zone,
            },
            'status': self.status,
            'is_verified': self.is_verified,
            'is_blacklisted': self.is_blacklisted,
            'is_stolen': self.is_stolen,
            'compliance': {
                'registration_status': self.registration_status,
                'registration_expiry': self.registration_expiry.isoformat() if self.registration_expiry else None,
                'is_expired_registration': self.is_expired_registration,
                'insurance_status': self.insurance_status,
                'insurance_expiry': self.insurance_expiry.isoformat() if self.insurance_expiry else None,
                'is_expired_insurance': self.is_expired_insurance,
                'inspection_status': self.inspection_status,
                'inspection_expiry': self.inspection_expiry.isoformat() if self.inspection_expiry else None,
                'is_expired_inspection': self.is_expired_inspection,
                'is_compliant': self.is_compliant,
            },
            'statistics': {
                'total_parking_sessions': self.total_parking_sessions,
                'total_parking_duration_minutes': self.total_parking_duration_minutes,
                'total_parking_amount': float(self.total_parking_amount) if self.total_parking_amount else 0,
                'last_parking_at': self.last_parking_at.isoformat() if self.last_parking_at else None,
                'last_parking_spot': self.last_parking_spot,
                'last_parking_zone': self.last_parking_zone,
                'average_parking_duration': self.average_parking_duration,
                'favorite_zone': self.favorite_zone,
            },
            'enforcement': {
                'violation_count': self.violation_count,
                'unpaid_violations': self.unpaid_violations,
                'unpaid_amount': float(self.unpaid_amount) if self.unpaid_amount else 0,
                'has_active_alerts': self.has_active_alerts,
                'alert_count': self.alert_count,
            },
            'notes': self.notes,
            'special_instructions': self.special_instructions,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data.update({
                'custom_fields': self.custom_fields,
                'metadata': self.metadata,
                'blacklisted_reason': self.blacklisted_reason,
                'stolen_reported_at': self.stolen_reported_at.isoformat() if self.stolen_reported_at else None,
                'stolen_recovered_at': self.stolen_recovered_at.isoformat() if self.stolen_recovered_at else None,
            })
        
        return data
    
    def __repr__(self) -> str:
        return f"<Vehicle(id={self.id}, plate={self.license_plate}, vin={self.vin})>"


class VehicleRegistration(Base):
    """
    Vehicle registration history.
    
    Tracks registration details and history for vehicles.
    """
    
    __tablename__ = 'vehicle_registrations'
    __table_args__ = (
        Index('ix_vehicle_reg_vehicle', 'vehicle_id'),
        Index('ix_vehicle_reg_number', 'registration_number'),
        Index('ix_vehicle_reg_expiry', 'expiry_date'),
        Index('ix_vehicle_reg_status', 'status'),
        {'comment': 'Vehicle registration records'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    registration_number = Column(
        String(100),
        nullable=False,
        comment='Registration document number'
    )
    
    jurisdiction = Column(
        String(100),
        comment='Issuing jurisdiction (DMV, DOT, etc.)'
    )
    
    state = Column(
        String(50),
        comment='State of registration'
    )
    
    country = Column(
        String(2),
        comment='Country of registration'
    )
    
    issue_date = Column(
        Date,
        comment='Date of issue'
    )
    
    effective_date = Column(
        Date,
        comment='Effective date of registration'
    )
    
    expiry_date = Column(
        Date,
        comment='Expiry date'
    )
    
    status = Column(
        String(50),
        nullable=False,
        comment='Registration status'
    )
    
    class_type = Column(
        String(50),
        comment='Registration class'
    )
    
    reg_type = Column(
        String(50),
        comment='Registration type'
    )
    
    weight_class = Column(
        String(50),
        comment='Weight class'
    )
    
    passenger_capacity = Column(
        Integer,
        comment='Passenger capacity'
    )
    
    commercial_use = Column(
        Boolean,
        server_default='false',
        comment='Whether for commercial use'
    )
    
    hazardous_materials = Column(
        Boolean,
        server_default='false',
        comment='Whether transports hazardous materials'
    )
    
    registered_owner_name = Column(
        String(255),
        comment='Name of registered owner'
    )
    
    registered_owner_address = Column(
        Text,
        comment='Address of registered owner'
    )
    
    lienholder_name = Column(
        String(255),
        comment='Name of lienholder'
    )
    
    lienholder_address = Column(
        Text,
        comment='Address of lienholder'
    )
    
    registration_document_url = Column(
        String(500),
        comment='URL to registration document'
    )
    
    verified = Column(
        Boolean,
        server_default='false',
        comment='Whether registration is verified'
    )
    
    verified_at = Column(
        DateTime(timezone=True),
        comment='When registration was verified'
    )
    
    verified_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who verified registration'
    )
    
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
    vehicle = relationship('Vehicle', back_populates='registrations')
    verifier = relationship('User', foreign_keys=[verified_by])
    creator = relationship('User', foreign_keys=[created_by])
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if registration is expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registration to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'registration_number': self.registration_number,
            'jurisdiction': self.jurisdiction,
            'state': self.state,
            'country': self.country,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'status': self.status,
            'is_expired': self.is_expired,
            'class_type': self.class_type,
            'commercial_use': self.commercial_use,
            'registered_owner_name': self.registered_owner_name,
            'verified': self.verified,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleRegistration(id={self.id}, number={self.registration_number})>"


class VehicleInsurance(Base):
    """
    Vehicle insurance policies.
    
    Tracks insurance policies, coverage, and expiry dates.
    """
    
    __tablename__ = 'vehicle_insurance'
    __table_args__ = (
        Index('ix_vehicle_ins_vehicle', 'vehicle_id'),
        Index('ix_vehicle_ins_policy', 'policy_number'),
        Index('ix_vehicle_ins_expiry', 'expiry_date'),
        Index('ix_vehicle_ins_status', 'status'),
        {'comment': 'Vehicle insurance policies'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    policy_number = Column(
        String(100),
        nullable=False,
        comment='Insurance policy number'
    )
    
    provider = Column(
        String(255),
        nullable=False,
        comment='Insurance provider name'
    )
    
    provider_phone = Column(
        String(20),
        comment='Provider phone number'
    )
    
    provider_email = Column(
        String(255),
        comment='Provider email'
    )
    
    agent_name = Column(
        String(255),
        comment='Insurance agent name'
    )
    
    agent_phone = Column(
        String(20),
        comment='Agent phone number'
    )
    
    coverage_type = Column(
        String(100),
        comment='Type of coverage'
    )
    
    coverage_amount = Column(
        Numeric(10, 2),
        comment='Coverage amount'
    )
    
    deductible = Column(
        Numeric(10, 2),
        comment='Deductible amount'
    )
    
    liability_coverage = Column(
        Numeric(10, 2),
        comment='Liability coverage amount'
    )
    
    comprehensive_coverage = Column(
        Numeric(10, 2),
        comment='Comprehensive coverage amount'
    )
    
    collision_coverage = Column(
        Numeric(10, 2),
        comment='Collision coverage amount'
    )
    
    uninsured_motorist = Column(
        Numeric(10, 2),
        comment='Uninsured motorist coverage'
    )
    
    medical_payments = Column(
        Numeric(10, 2),
        comment='Medical payments coverage'
    )
    
    effective_date = Column(
        Date,
        nullable=False,
        comment='Policy effective date'
    )
    
    expiry_date = Column(
        Date,
        nullable=False,
        comment='Policy expiry date'
    )
    
    status = Column(
        String(50),
        nullable=False,
        comment='Policy status'
    )
    
    premium_amount = Column(
        Numeric(10, 2),
        comment='Premium amount'
    )
    
    premium_frequency = Column(
        String(20),
        comment='Premium payment frequency'
    )
    
    insured_name = Column(
        String(255),
        comment='Name of insured'
    )
    
    insured_address = Column(
        Text,
        comment='Address of insured'
    )
    
    additional_drivers = Column(
        JSONB,
        comment='Additional drivers on policy'
    )
    
    excluded_drivers = Column(
        JSONB,
        comment='Excluded drivers'
    )
    
    policy_document_url = Column(
        String(500),
        comment='URL to policy document'
    )
    
    proof_of_insurance_url = Column(
        String(500),
        comment='URL to proof of insurance'
    )
    
    verified = Column(
        Boolean,
        server_default='false',
        comment='Whether insurance is verified'
    )
    
    verified_at = Column(
        DateTime(timezone=True),
        comment='When insurance was verified'
    )
    
    verified_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who verified insurance'
    )
    
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
    vehicle = relationship('Vehicle', back_populates='insurance_policies')
    verifier = relationship('User', foreign_keys=[verified_by])
    creator = relationship('User', foreign_keys=[created_by])
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if insurance is expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert insurance to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'policy_number': self.policy_number,
            'provider': self.provider,
            'provider_phone': self.provider_phone,
            'coverage_type': self.coverage_type,
            'coverage_amount': float(self.coverage_amount) if self.coverage_amount else None,
            'deductible': float(self.deductible) if self.deductible else None,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'status': self.status,
            'is_expired': self.is_expired,
            'premium_amount': float(self.premium_amount) if self.premium_amount else None,
            'insured_name': self.insured_name,
            'verified': self.verified,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleInsurance(id={self.id}, policy={self.policy_number})>"


class VehicleInspection(Base):
    """
    Vehicle inspection records.
    
    Tracks safety and emissions inspections for vehicles.
    """
    
    __tablename__ = 'vehicle_inspections'
    __table_args__ = (
        Index('ix_vehicle_insp_vehicle', 'vehicle_id'),
        Index('ix_vehicle_insp_number', 'inspection_number'),
        Index('ix_vehicle_insp_date', 'inspection_date'),
        Index('ix_vehicle_insp_status', 'status'),
        {'comment': 'Vehicle inspection records'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    inspection_number = Column(
        String(100),
        nullable=False,
        comment='Inspection certificate number'
    )
    
    inspection_type = Column(
        String(100),
        comment='Type of inspection (safety, emissions, annual)'
    )
    
    inspector_name = Column(
        String(255),
        comment='Name of inspector'
    )
    
    inspector_id = Column(
        String(100),
        comment='Inspector license/ID number'
    )
    
    inspection_facility = Column(
        String(255),
        comment='Name of inspection facility'
    )
    
    inspection_date = Column(
        Date,
        nullable=False,
        comment='Date of inspection'
    )
    
    expiry_date = Column(
        Date,
        comment='Expiry date of inspection'
    )
    
    status = Column(
        String(50),
        nullable=False,
        comment='Inspection status'
    )
    
    result = Column(
        String(50),
        comment='Inspection result (pass, fail, conditional)'
    )
    
    odometer_reading = Column(
        Integer,
        comment='Odometer reading at inspection'
    )
    
    emissions_result = Column(
        String(100),
        comment='Emissions test result'
    )
    
    emissions_value = Column(
        Float,
        comment='Emissions measurement value'
    )
    
    safety_items = Column(
        JSONB,
        comment='Safety inspection items'
    )
    
    failed_items = Column(
        JSONB,
        comment='Failed inspection items'
    )
    
    warnings = Column(
        JSONB,
        comment='Warnings noted'
    )
    
    recommendations = Column(
        Text,
        comment='Recommendations'
    )
    
    corrective_actions = Column(
        Text,
        comment='Corrective actions required'
    )
    
    certificate_number = Column(
        String(100),
        comment='Certificate number'
    )
    
    certificate_url = Column(
        String(500),
        comment='URL to certificate'
    )
    
    report_url = Column(
        String(500),
        comment='URL to inspection report'
    )
    
    images = Column(
        ARRAY(String(500)),
        comment='URLs to inspection images'
    )
    
    verified = Column(
        Boolean,
        server_default='false',
        comment='Whether inspection is verified'
    )
    
    verified_at = Column(
        DateTime(timezone=True),
        comment='When inspection was verified'
    )
    
    verified_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who verified inspection'
    )
    
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
    vehicle = relationship('Vehicle', back_populates='inspections')
    verifier = relationship('User', foreign_keys=[verified_by])
    creator = relationship('User', foreign_keys=[created_by])
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if inspection is expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert inspection to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'inspection_number': self.inspection_number,
            'inspection_type': self.inspection_type,
            'inspector_name': self.inspector_name,
            'inspection_facility': self.inspection_facility,
            'inspection_date': self.inspection_date.isoformat() if self.inspection_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'status': self.status,
            'result': self.result,
            'is_expired': self.is_expired,
            'odometer_reading': self.odometer_reading,
            'emissions_result': self.emissions_result,
            'failed_items': self.failed_items,
            'recommendations': self.recommendations,
            'certificate_number': self.certificate_number,
            'certificate_url': self.certificate_url,
            'verified': self.verified,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleInspection(id={self.id}, number={self.inspection_number})>"


class VehicleMaintenance(Base):
    """
    Vehicle maintenance records.
    
    Tracks maintenance history, services, and costs for vehicles.
    """
    
    __tablename__ = 'vehicle_maintenance'
    __table_args__ = (
        Index('ix_vehicle_maint_vehicle', 'vehicle_id'),
        Index('ix_vehicle_maint_date', 'service_date'),
        Index('ix_vehicle_maint_type', 'maintenance_type'),
        Index('ix_vehicle_maint_next', 'next_service_due'),
        {'comment': 'Vehicle maintenance records'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    maintenance_type = Column(
        String(100),
        nullable=False,
        comment='Type of maintenance'
    )
    
    service_date = Column(
        Date,
        nullable=False,
        comment='Date of service'
    )
    
    service_provider = Column(
        String(255),
        comment='Name of service provider'
    )
    
    mechanic_name = Column(
        String(255),
        comment='Name of mechanic'
    )
    
    odometer_reading = Column(
        Integer,
        comment='Odometer reading at service'
    )
    
    description = Column(
        Text,
        comment='Description of work performed'
    )
    
    items_serviced = Column(
        JSONB,
        comment='Items serviced'
    )
    
    parts_replaced = Column(
        JSONB,
        comment='Parts replaced'
    )
    
    labor_hours = Column(
        Float,
        comment='Labor hours'
    )
    
    labor_cost = Column(
        Numeric(10, 2),
        comment='Labor cost'
    )
    
    parts_cost = Column(
        Numeric(10, 2),
        comment='Parts cost'
    )
    
    tax_amount = Column(
        Numeric(10, 2),
        comment='Tax amount'
    )
    
    total_cost = Column(
        Numeric(10, 2),
        comment='Total cost'
    )
    
    invoice_number = Column(
        String(100),
        comment='Invoice number'
    )
    
    invoice_url = Column(
        String(500),
        comment='URL to invoice'
    )
    
    receipt_url = Column(
        String(500),
        comment='URL to receipt'
    )
    
    warranty_until = Column(
        Date,
        comment='Warranty expiration date'
    )
    
    next_service_due = Column(
        Date,
        comment='Next service due date'
    )
    
    next_service_odometer = Column(
        Integer,
        comment='Next service due odometer'
    )
    
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
    vehicle = relationship('Vehicle', back_populates='maintenance_records')
    creator = relationship('User', foreign_keys=[created_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert maintenance record to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'maintenance_type': self.maintenance_type,
            'service_date': self.service_date.isoformat() if self.service_date else None,
            'service_provider': self.service_provider,
            'odometer_reading': self.odometer_reading,
            'description': self.description,
            'items_serviced': self.items_serviced,
            'parts_replaced': self.parts_replaced,
            'labor_hours': self.labor_hours,
            'labor_cost': float(self.labor_cost) if self.labor_cost else None,
            'parts_cost': float(self.parts_cost) if self.parts_cost else None,
            'tax_amount': float(self.tax_amount) if self.tax_amount else None,
            'total_cost': float(self.total_cost) if self.total_cost else None,
            'invoice_number': self.invoice_number,
            'invoice_url': self.invoice_url,
            'warranty_until': self.warranty_until.isoformat() if self.warranty_until else None,
            'next_service_due': self.next_service_due.isoformat() if self.next_service_due else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleMaintenance(id={self.id}, type={self.maintenance_type})>"


class VehicleImage(Base):
    """
    Vehicle images.
    
    Stores images of vehicles for identification and verification.
    """
    
    __tablename__ = 'vehicle_images'
    __table_args__ = (
        Index('ix_vehicle_images_vehicle', 'vehicle_id'),
        Index('ix_vehicle_images_type', 'image_type'),
        Index('ix_vehicle_images_primary', 'is_primary'),
        {'comment': 'Vehicle images'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    image_type = Column(
        String(50),
        comment='Type of image (front, rear, side, interior, license_plate)'
    )
    
    image_url = Column(
        String(500),
        nullable=False,
        comment='URL to full-size image'
    )
    
    thumbnail_url = Column(
        String(500),
        comment='URL to thumbnail image'
    )
    
    title = Column(
        String(255),
        comment='Image title'
    )
    
    description = Column(
        Text,
        comment='Image description'
    )
    
    is_primary = Column(
        Boolean,
        server_default='false',
        comment='Whether this is the primary image'
    )
    
    is_verified = Column(
        Boolean,
        server_default='false',
        comment='Whether image is verified'
    )
    
    verified_at = Column(
        DateTime(timezone=True),
        comment='When image was verified'
    )
    
    verified_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who verified image'
    )
    
    capture_date = Column(
        DateTime(timezone=True),
        comment='When image was captured'
    )
    
    capture_location = Column(
        String(255),
        comment='Where image was captured'
    )
    
    metadata = Column(
        JSONB,
        comment='Image metadata (EXIF, etc.)'
    )
    
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
    vehicle = relationship('Vehicle', back_populates='images')
    verifier = relationship('User', foreign_keys=[verified_by])
    creator = relationship('User', foreign_keys=[created_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert image to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'image_type': self.image_type,
            'image_url': self.image_url,
            'thumbnail_url': self.thumbnail_url,
            'title': self.title,
            'description': self.description,
            'is_primary': self.is_primary,
            'is_verified': self.is_verified,
            'capture_date': self.capture_date.isoformat() if self.capture_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleImage(id={self.id}, type={self.image_type})>"


class VehicleDocument(Base):
    """
    Vehicle documents.
    
    Stores documents related to vehicles (title, registration, insurance, etc.).
    """
    
    __tablename__ = 'vehicle_documents'
    __table_args__ = (
        Index('ix_vehicle_docs_vehicle', 'vehicle_id'),
        Index('ix_vehicle_docs_type', 'document_type'),
        Index('ix_vehicle_docs_expiry', 'expiry_date'),
        Index('ix_vehicle_docs_verified', 'is_verified'),
        {'comment': 'Vehicle documents'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    document_type = Column(
        String(100),
        nullable=False,
        comment='Type of document (title, registration, insurance, etc.)'
    )
    
    document_name = Column(
        String(255),
        comment='Document name'
    )
    
    document_number = Column(
        String(100),
        comment='Document number'
    )
    
    issue_date = Column(
        Date,
        comment='Date of issue'
    )
    
    expiry_date = Column(
        Date,
        comment='Expiry date'
    )
    
    issuing_authority = Column(
        String(255),
        comment='Issuing authority'
    )
    
    file_url = Column(
        String(500),
        nullable=False,
        comment='URL to document file'
    )
    
    file_type = Column(
        String(50),
        comment='File type (pdf, jpg, png, etc.)'
    )
    
    file_size = Column(
        Integer,
        comment='File size in bytes'
    )
    
    is_verified = Column(
        Boolean,
        server_default='false',
        comment='Whether document is verified'
    )
    
    verified_at = Column(
        DateTime(timezone=True),
        comment='When document was verified'
    )
    
    verified_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who verified document'
    )
    
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
    vehicle = relationship('Vehicle', back_populates='documents')
    verifier = relationship('User', foreign_keys=[verified_by])
    creator = relationship('User', foreign_keys=[created_by])
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if document is expired."""
        if not self.expiry_date:
            return False
        return self.expiry_date < date.today()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'document_type': self.document_type,
            'document_name': self.document_name,
            'document_number': self.document_number,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'is_expired': self.is_expired,
            'issuing_authority': self.issuing_authority,
            'file_url': self.file_url,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'is_verified': self.is_verified,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleDocument(id={self.id}, type={self.document_type})>"


class VehicleViolation(Base):
    """
    Parking violations associated with vehicles.
    
    Tracks parking tickets, fines, and disputes for vehicles.
    """
    
    __tablename__ = 'vehicle_violations'
    __table_args__ = (
        Index('ix_vehicle_violations_vehicle', 'vehicle_id'),
        Index('ix_vehicle_violations_number', 'violation_number', unique=True),
        Index('ix_vehicle_violations_timestamp', 'timestamp'),
        Index('ix_vehicle_violations_type', 'violation_type'),
        Index('ix_vehicle_violations_paid', 'paid'),
        Index('ix_vehicle_violations_vehicle_unpaid', 'vehicle_id', 'paid'),
        Index('ix_vehicle_violations_license_unpaid', 'license_plate', 'paid'),
        Index('ix_vehicle_violations_type_severity', 'violation_type', 'severity'),
        Index('ix_vehicle_violations_disputed', 'disputed', 'dispute_resolved_at'),
        {'comment': 'Parking violations for vehicles'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    violation_number = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Unique violation number'
    )
    
    violation_type = Column(
        String(50),
        nullable=False,
        comment='Type of violation'
    )
    
    severity = Column(
        String(20),
        nullable=False,
        comment='Severity level'
    )
    
    description = Column(
        Text,
        comment='Violation description'
    )
    
    location = Column(
        String(255),
        comment='Location of violation'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_zones.id', ondelete='SET NULL'),
        comment='Zone where violation occurred'
    )
    
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='SET NULL'),
        comment='Spot where violation occurred'
    )
    
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When violation occurred'
    )
    
    detected_by = Column(
        String(100),
        comment='How violation was detected (camera, officer, system)'
    )
    
    officer_id = Column(
        String(100),
        comment='ID of issuing officer'
    )
    
    officer_name = Column(
        String(255),
        comment='Name of issuing officer'
    )
    
    evidence_urls = Column(
        ARRAY(String(500)),
        comment='URLs to evidence images'
    )
    
    license_plate_image = Column(
        String(500),
        comment='URL to license plate image'
    )
    
    fine_amount = Column(
        Numeric(10, 2),
        comment='Fine amount'
    )
    
    currency = Column(
        String(3),
        server_default='USD',
        comment='Currency code'
    )
    
    paid = Column(
        Boolean,
        server_default='false',
        comment='Whether fine has been paid'
    )
    
    paid_at = Column(
        DateTime(timezone=True),
        comment='When fine was paid'
    )
    
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payments.id', ondelete='SET NULL'),
        comment='ID of payment'
    )
    
    disputed = Column(
        Boolean,
        server_default='false',
        comment='Whether violation is disputed'
    )
    
    dispute_reason = Column(
        Text,
        comment='Reason for dispute'
    )
    
    dispute_resolution = Column(
        Text,
        comment='Resolution of dispute'
    )
    
    dispute_resolved_at = Column(
        DateTime(timezone=True),
        comment='When dispute was resolved'
    )
    
    appeal_deadline = Column(
        DateTime(timezone=True),
        comment='Deadline to appeal'
    )
    
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
    vehicle = relationship('Vehicle', back_populates='violations')
    zone = relationship('ParkingZone')
    spot = relationship('ParkingSpot')
    payment = relationship('Payment')
    creator = relationship('User', foreign_keys=[created_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def pay(self, payment_id: uuid.UUID) -> None:
        """Mark violation as paid."""
        self.paid = True
        self.paid_at = datetime.now()
        self.payment_id = payment_id
        
        # Update vehicle
        self.vehicle.unpaid_violations -= 1
        self.vehicle.unpaid_amount = float(self.vehicle.unpaid_amount) - float(self.fine_amount)
    
    def dispute(self, reason: str) -> None:
        """Dispute violation."""
        self.disputed = True
        self.dispute_reason = reason
    
    def resolve_dispute(self, resolution: str, user_id: Optional[uuid.UUID] = None) -> None:
        """Resolve dispute."""
        self.disputed = False
        self.dispute_resolution = resolution
        self.dispute_resolved_at = datetime.now()
        self.updated_by = user_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'violation_number': self.violation_number,
            'violation_type': self.violation_type,
            'severity': self.severity,
            'description': self.description,
            'location': self.location,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'officer_name': self.officer_name,
            'fine_amount': float(self.fine_amount) if self.fine_amount else None,
            'currency': self.currency,
            'paid': self.paid,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'disputed': self.disputed,
            'dispute_reason': self.dispute_reason,
            'appeal_deadline': self.appeal_deadline.isoformat() if self.appeal_deadline else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleViolation(id={self.id}, number={self.violation_number})>"


class VehicleAccessHistory(Base):
    """
    History of vehicle access attempts.
    
    Tracks entry and exit attempts for vehicles at gates.
    """
    
    __tablename__ = 'vehicle_access_history'
    __table_args__ = (
        Index('ix_vehicle_access_vehicle', 'vehicle_id'),
        Index('ix_vehicle_access_timestamp', 'timestamp'),
        Index('ix_vehicle_access_method', 'access_method'),
        Index('ix_vehicle_access_gate', 'gate_id'),
        Index('ix_vehicle_access_vehicle_time', 'vehicle_id', 'timestamp'),
        Index('ix_vehicle_access_plate_time', 'matched_plate', 'timestamp'),
        Index('ix_vehicle_access_gate_time', 'gate_id', 'timestamp'),
        Index('ix_vehicle_access_denied', 'access_type', 'timestamp',
              postgresql_where=text("access_type = 'denied'")),
        {'comment': 'Vehicle access history'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    access_method = Column(
        String(50),
        nullable=False,
        comment='Method of access (rfid, plate, qr, etc.)'
    )
    
    access_type = Column(
        String(20),
        comment='Type of access (entry, exit, denied)'
    )
    
    gate_id = Column(
        String(100),
        comment='ID of gate'
    )
    
    gate_name = Column(
        String(255),
        comment='Name of gate'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_zones.id', ondelete='SET NULL'),
        comment='Zone accessed'
    )
    
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='SET NULL'),
        comment='Spot accessed'
    )
    
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_sessions.id', ondelete='SET NULL'),
        comment='Associated parking session'
    )
    
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Time of access'
    )
    
    image_url = Column(
        String(500),
        comment='URL to access image'
    )
    
    confidence = Column(
        Float,
        comment='Confidence level for plate recognition'
    )
    
    matched_plate = Column(
        String(20),
        comment='License plate that was matched'
    )
    
    matched_vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='SET NULL'),
        comment='ID of matched vehicle'
    )
    
    denied_reason = Column(
        String(255),
        comment='Reason for denial'
    )
    
    response_time_ms = Column(
        Integer,
        comment='Response time in milliseconds'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    vehicle = relationship('Vehicle', back_populates='access_history')
    zone = relationship('ParkingZone')
    spot = relationship('ParkingSpot')
    session = relationship('ParkingSession')
    matched_vehicle = relationship('Vehicle', foreign_keys=[matched_vehicle_id])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert access record to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'access_method': self.access_method,
            'access_type': self.access_type,
            'gate_id': self.gate_id,
            'gate_name': self.gate_name,
            'zone_id': str(self.zone_id) if self.zone_id else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'image_url': self.image_url,
            'confidence': self.confidence,
            'matched_plate': self.matched_plate,
            'denied_reason': self.denied_reason,
            'response_time_ms': self.response_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleAccessHistory(id={self.id}, method={self.access_method}, time={self.timestamp})>"


class VehicleLocationHistory(Base):
    """
    Historical GPS location data for vehicles.
    
    Tracks vehicle locations over time for analytics and tracking.
    """
    
    __tablename__ = 'vehicle_location_history'
    __table_args__ = (
        Index('ix_vehicle_location_vehicle', 'vehicle_id'),
        Index('ix_vehicle_location_timestamp', 'timestamp'),
        Index('ix_vehicle_location_coords', 'latitude', 'longitude'),
        Index('ix_vehicle_location_vehicle_time', 'vehicle_id', 'timestamp'),
        Index('ix_vehicle_location_recent', 'timestamp',
              postgresql_where=text("timestamp > CURRENT_TIMESTAMP - INTERVAL '7 days'")),
        {'comment': 'Vehicle location history'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    device_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicle_devices.id', ondelete='SET NULL'),
        comment='ID of tracking device'
    )
    
    latitude = Column(
        Numeric(10, 8),
        comment='Latitude coordinate'
    )
    
    longitude = Column(
        Numeric(11, 8),
        comment='Longitude coordinate'
    )
    
    altitude = Column(
        Float,
        comment='Altitude in meters'
    )
    
    speed = Column(
        Float,
        comment='Speed in km/h'
    )
    
    heading = Column(
        Float,
        comment='Heading in degrees'
    )
    
    accuracy = Column(
        Float,
        comment='Accuracy in meters'
    )
    
    source = Column(
        String(50),
        comment='Source of location (gps, wifi, cellular)'
    )
    
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Time of location'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_zones.id', ondelete='SET NULL'),
        comment='Zone at this location'
    )
    
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='SET NULL'),
        comment='Spot at this location'
    )
    
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_sessions.id', ondelete='SET NULL'),
        comment='Associated parking session'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    vehicle = relationship('Vehicle', back_populates='location_history')
    device = relationship('VehicleDevice')
    zone = relationship('ParkingZone')
    spot = relationship('ParkingSpot')
    session = relationship('ParkingSession')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert location record to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'altitude': self.altitude,
            'speed': self.speed,
            'heading': self.heading,
            'accuracy': self.accuracy,
            'source': self.source,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'zone_id': str(self.zone_id) if self.zone_id else None,
            'spot_id': str(self.spot_id) if self.spot_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleLocationHistory(id={self.id}, time={self.timestamp})>"


class VehiclePreference(Base):
    """
    User preferences for each vehicle.
    
    Stores per-vehicle preferences for automated features.
    """
    
    __tablename__ = 'vehicle_preferences'
    __table_args__ = (
        Index('ix_vehicle_prefs_vehicle', 'vehicle_id', unique=True),
        {'comment': 'Vehicle preferences'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        comment='ID of the vehicle'
    )
    
    preferred_parking_zones = Column(
        ARRAY(UUID(as_uuid=True)),
        comment='Preferred parking zones'
    )
    
    preferred_parking_types = Column(
        ARRAY(String(50)),
        comment='Preferred parking types'
    )
    
    avoid_areas = Column(
        ARRAY(String(255)),
        comment='Areas to avoid'
    )
    
    max_walking_distance = Column(
        Integer,
        comment='Maximum walking distance in meters'
    )
    
    preferred_entry_gates = Column(
        ARRAY(String(100)),
        comment='Preferred entry gates'
    )
    
    preferred_exit_gates = Column(
        ARRAY(String(100)),
        comment='Preferred exit gates'
    )
    
    notify_on_entry = Column(
        Boolean,
        server_default='true',
        comment='Whether to notify on entry'
    )
    
    notify_on_exit = Column(
        Boolean,
        server_default='true',
        comment='Whether to notify on exit'
    )
    
    notify_on_violation = Column(
        Boolean,
        server_default='true',
        comment='Whether to notify on violation'
    )
    
    notify_on_alert = Column(
        Boolean,
        server_default='true',
        comment='Whether to notify on alert'
    )
    
    auto_pay = Column(
        Boolean,
        server_default='false',
        comment='Whether to auto-pay parking'
    )
    
    default_payment_method_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payment_methods.id', ondelete='SET NULL'),
        comment='Default payment method'
    )
    
    auto_extend = Column(
        Boolean,
        server_default='false',
        comment='Whether to auto-extend parking'
    )
    
    max_extension_minutes = Column(
        Integer,
        comment='Maximum extension minutes'
    )
    
    reminder_minutes = Column(
        ARRAY(Integer),
        comment='Reminder minutes before expiry'
    )
    
    special_instructions = Column(
        Text,
        comment='Special instructions'
    )
    
    settings = Column(
        JSONB,
        comment='Additional settings'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
    vehicle = relationship('Vehicle', back_populates='preferences')
    default_payment_method = relationship('PaymentMethod')
    creator = relationship('User', foreign_keys=[created_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'preferred_parking_zones': [str(z) for z in self.preferred_parking_zones] if self.preferred_parking_zones else [],
            'preferred_parking_types': self.preferred_parking_types,
            'max_walking_distance': self.max_walking_distance,
            'preferred_entry_gates': self.preferred_entry_gates,
            'preferred_exit_gates': self.preferred_exit_gates,
            'notifications': {
                'on_entry': self.notify_on_entry,
                'on_exit': self.notify_on_exit,
                'on_violation': self.notify_on_violation,
                'on_alert': self.notify_on_alert,
            },
            'auto_pay': self.auto_pay,
            'default_payment_method_id': str(self.default_payment_method_id) if self.default_payment_method_id else None,
            'auto_extend': self.auto_extend,
            'max_extension_minutes': self.max_extension_minutes,
            'reminder_minutes': self.reminder_minutes,
            'special_instructions': self.special_instructions,
            'settings': self.settings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehiclePreference(id={self.id}, vehicle={self.vehicle_id})>"


class VehicleAlert(Base):
    """
    Alerts and notifications for vehicles.
    
    Tracks active alerts for vehicles (stolen, suspicious, etc.).
    """
    
    __tablename__ = 'vehicle_alerts'
    __table_args__ = (
        Index('ix_vehicle_alerts_vehicle', 'vehicle_id'),
        Index('ix_vehicle_alerts_plate', 'license_plate'),
        Index('ix_vehicle_alerts_type', 'alert_type'),
        Index('ix_vehicle_alerts_priority', 'priority'),
        Index('ix_vehicle_alerts_active', 'is_active'),
        Index('ix_vehicle_alerts_expires', 'expires_at'),
        {'comment': 'Vehicle alerts'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        comment='ID of the vehicle (if known)'
    )
    
    license_plate = Column(
        String(20),
        comment='License plate (if vehicle unknown)'
    )
    
    license_plate_state = Column(
        String(50),
        comment='License plate state'
    )
    
    alert_type = Column(
        String(50),
        nullable=False,
        comment='Type of alert'
    )
    
    priority = Column(
        String(20),
        nullable=False,
        comment='Alert priority'
    )
    
    title = Column(
        String(255),
        nullable=False,
        comment='Alert title'
    )
    
    description = Column(
        Text,
        comment='Alert description'
    )
    
    source = Column(
        String(100),
        comment='Source of alert (system, police, etc.)'
    )
    
    source_reference = Column(
        String(100),
        comment='Reference number from source'
    )
    
    issued_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When alert was issued'
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        comment='When alert expires'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether alert is active'
    )
    
    resolved_at = Column(
        DateTime(timezone=True),
        comment='When alert was resolved'
    )
    
    resolved_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who resolved alert'
    )
    
    resolution_notes = Column(
        Text,
        comment='Resolution notes'
    )
    
    requires_action = Column(
        Boolean,
        server_default='false',
        comment='Whether action is required'
    )
    
    action_taken = Column(
        Text,
        comment='Action taken'
    )
    
    notified_users = Column(
        ARRAY(UUID(as_uuid=True)),
        comment='Users who were notified'
    )
    
    notified_at = Column(
        DateTime(timezone=True),
        comment='When notifications were sent'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
        comment='User who created alert'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    vehicle = relationship('Vehicle', back_populates='alerts')
    resolver = relationship('User', foreign_keys=[resolved_by])
    creator = relationship('User', foreign_keys=[created_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def resolve(self, notes: str, user_id: Optional[uuid.UUID] = None) -> None:
        """Resolve alert."""
        self.is_active = False
        self.resolved_at = datetime.now()
        self.resolved_by = user_id
        self.resolution_notes = notes
        
        # Update vehicle
        if self.vehicle:
            self.vehicle.has_active_alerts = False
            self.vehicle.alert_count -= 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id) if self.vehicle_id else None,
            'license_plate': self.license_plate,
            'alert_type': self.alert_type,
            'priority': self.priority,
            'title': self.title,
            'description': self.description,
            'source': self.source,
            'source_reference': self.source_reference,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'requires_action': self.requires_action,
            'action_taken': self.action_taken,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleAlert(id={self.id}, type={self.alert_type}, active={self.is_active})>"


class VehicleDevice(Base):
    """
    IoT devices installed in vehicles.
    
    Tracks tracking devices, transponders, and other IoT devices.
    """
    
    __tablename__ = 'vehicle_devices'
    __table_args__ = (
        Index('ix_vehicle_devices_vehicle', 'vehicle_id'),
        Index('ix_vehicle_devices_device', 'device_id', unique=True),
        Index('ix_vehicle_devices_serial', 'serial_number', unique=True),
        Index('ix_vehicle_devices_status', 'status'),
        {'comment': 'IoT devices in vehicles'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    device_type = Column(
        String(50),
        nullable=False,
        comment='Type of device (tracker, beacon, transponder)'
    )
    
    device_id = Column(
        String(100),
        nullable=False,
        unique=True,
        comment='Unique device identifier'
    )
    
    device_name = Column(
        String(255),
        comment='Device name'
    )
    
    manufacturer = Column(
        String(255),
        comment='Device manufacturer'
    )
    
    model = Column(
        String(100),
        comment='Device model'
    )
    
    serial_number = Column(
        String(100),
        unique=True,
        comment='Device serial number'
    )
    
    firmware_version = Column(
        String(50),
        comment='Firmware version'
    )
    
    hardware_version = Column(
        String(50),
        comment='Hardware version'
    )
    
    battery_level = Column(
        Integer,
        comment='Battery level percentage'
    )
    
    last_ping = Column(
        DateTime(timezone=True),
        comment='Last communication timestamp'
    )
    
    last_location = Column(
        JSONB,
        comment='Last known location'
    )
    
    status = Column(
        String(50),
        server_default='active',
        comment='Device status'
    )
    
    activated_at = Column(
        DateTime(timezone=True),
        comment='When device was activated'
    )
    
    deactivated_at = Column(
        DateTime(timezone=True),
        comment='When device was deactivated'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
    vehicle = relationship('Vehicle', back_populates='devices')
    creator = relationship('User', foreign_keys=[created_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'device_type': self.device_type,
            'device_id': self.device_id,
            'device_name': self.device_name,
            'manufacturer': self.manufacturer,
            'model': self.model,
            'serial_number': self.serial_number,
            'firmware_version': self.firmware_version,
            'battery_level': self.battery_level,
            'last_ping': self.last_ping.isoformat() if self.last_ping else None,
            'status': self.status,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'deactivated_at': self.deactivated_at.isoformat() if self.deactivated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleDevice(id={self.id}, device_id={self.device_id})>"


class VehicleOwnershipHistory(Base):
    """
    History of vehicle ownership transfers.
    
    Tracks changes in vehicle ownership over time.
    """
    
    __tablename__ = 'vehicle_ownership_history'
    __table_args__ = (
        Index('ix_vehicle_ownership_vehicle', 'vehicle_id'),
        Index('ix_vehicle_ownership_prev', 'previous_owner_id'),
        Index('ix_vehicle_ownership_new', 'new_owner_id'),
        Index('ix_vehicle_ownership_date', 'transfer_date'),
        {'comment': 'Vehicle ownership history'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    previous_owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='ID of previous owner'
    )
    
    new_owner_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=False,
        comment='ID of new owner'
    )
    
    ownership_type = Column(
        String(50),
        comment='Type of ownership transfer'
    )
    
    transfer_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When transfer occurred'
    )
    
    transfer_reason = Column(
        String(255),
        comment='Reason for transfer (sale, gift, etc.)'
    )
    
    document_url = Column(
        String(500),
        comment='URL to transfer document'
    )
    
    verified = Column(
        Boolean,
        server_default='false',
        comment='Whether transfer is verified'
    )
    
    verified_at = Column(
        DateTime(timezone=True),
        comment='When transfer was verified'
    )
    
    verified_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who verified transfer'
    )
    
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created this record'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    vehicle = relationship('Vehicle', back_populates='ownership_history')
    previous_owner = relationship('User', foreign_keys=[previous_owner_id])
    new_owner = relationship('User', foreign_keys=[new_owner_id])
    verifier = relationship('User', foreign_keys=[verified_by])
    creator = relationship('User', foreign_keys=[created_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ownership record to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'previous_owner_id': str(self.previous_owner_id) if self.previous_owner_id else None,
            'new_owner_id': str(self.new_owner_id) if self.new_owner_id else None,
            'ownership_type': self.ownership_type,
            'transfer_date': self.transfer_date.isoformat() if self.transfer_date else None,
            'transfer_reason': self.transfer_reason,
            'verified': self.verified,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleOwnershipHistory(id={self.id}, date={self.transfer_date})>"


class VehicleTag(Base):
    """
    Custom tags for vehicle categorization.
    
    Provides flexible tagging system for vehicles.
    """
    
    __tablename__ = 'vehicle_tags'
    __table_args__ = (
        Index('ix_vehicle_tags_name', 'name', unique=True),
        Index('ix_vehicle_tags_category', 'category'),
        Index('ix_vehicle_tags_active', 'is_active'),
        {'comment': 'Custom tags for vehicles'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    name = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Tag name'
    )
    
    category = Column(
        String(50),
        comment='Tag category'
    )
    
    description = Column(
        Text,
        comment='Tag description'
    )
    
    color = Column(
        String(20),
        comment='Tag color for UI'
    )
    
    icon = Column(
        String(50),
        comment='Tag icon'
    )
    
    is_system = Column(
        Boolean,
        server_default='false',
        comment='Whether tag is system-defined'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether tag is active'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
    assignments = relationship('VehicleTagAssignment', back_populates='tag')
    creator = relationship('User', foreign_keys=[created_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tag to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'color': self.color,
            'icon': self.icon,
            'is_system': self.is_system,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleTag(id={self.id}, name={self.name})>"


class VehicleTagAssignment(Base):
    """
    Many-to-many relationship between vehicles and tags.
    
    Assigns tags to vehicles.
    """
    
    __tablename__ = 'vehicle_tag_assignments'
    __table_args__ = (
        Index('ix_vehicle_tag_assign_vehicle', 'vehicle_id'),
        Index('ix_vehicle_tag_assign_tag', 'tag_id'),
        Index('ix_vehicle_tag_assign_active', 'is_active'),
        UniqueConstraint('vehicle_id', 'tag_id', name='uq_vehicle_tag'),
        {'comment': 'Vehicle tag assignments'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the vehicle'
    )
    
    tag_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicle_tags.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the tag'
    )
    
    assigned_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='When tag was assigned'
    )
    
    assigned_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who assigned tag'
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        comment='When tag assignment expires'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether assignment is active'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    vehicle = relationship('Vehicle', back_populates='tag_assignments')
    tag = relationship('VehicleTag', back_populates='assignments')
    assigner = relationship('User', foreign_keys=[assigned_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tag assignment to dictionary."""
        return {
            'id': str(self.id),
            'vehicle_id': str(self.vehicle_id),
            'tag_id': str(self.tag_id),
            'tag_name': self.tag.name if self.tag else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
        }
    
    def __repr__(self) -> str:
        return f"<VehicleTagAssignment(vehicle={self.vehicle_id}, tag={self.tag_id})>"


# =========================================================================
# EVENT LISTENERS
# =========================================================================

@event.listens_for(Vehicle, 'before_insert')
def vehicle_before_insert(mapper, connection, target):
    """Generate vehicle number for new vehicles."""
    if not target.vehicle_number:
        date_str = datetime.now().strftime('%Y%m%d')
        
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(vehicle_number FROM 11)::INTEGER), 0) + 1
                FROM vehicles
                WHERE vehicle_number LIKE :pattern
            """),
            {'pattern': f'VEH-{date_str}-%'}
        )
        seq_num = result.scalar()
        
        target.vehicle_number = f"VEH-{date_str}-{seq_num:06d}"


@event.listens_for(VehicleViolation, 'before_insert')
def violation_before_insert(mapper, connection, target):
    """Generate violation number for new violations."""
    if not target.violation_number:
        date_str = datetime.now().strftime('%Y%m%d')
        
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(violation_number FROM 11)::INTEGER), 0) + 1
                FROM vehicle_violations
                WHERE violation_number LIKE :pattern
            """),
            {'pattern': f'VIO-{date_str}-%'}
        )
        seq_num = result.scalar()
        
        target.violation_number = f"VIO-{date_str}-{seq_num:06d}"


@event.listens_for(Vehicle, 'after_insert')
@event.listens_for(Vehicle, 'after_update')
def vehicle_after_save(mapper, connection, target):
    """Update vehicle statistics when saved."""
    # This would typically be handled by triggers or async jobs
    pass


@event.listens_for(VehicleViolation, 'after_insert')
def violation_after_insert(mapper, connection, target):
    """Update vehicle violation counts when new violation added."""
    connection.execute(
        text("""
            UPDATE vehicles
            SET violation_count = violation_count + 1,
                unpaid_violations = unpaid_violations + 1,
                unpaid_amount = unpaid_amount + :fine_amount
            WHERE id = :vehicle_id
        """),
        {'vehicle_id': target.vehicle_id, 'fine_amount': target.fine_amount}
    )


# =========================================================================
# FACTORY FUNCTIONS
# =========================================================================

def create_vehicle(
    user_id: uuid.UUID,
    license_plate: str,
    vehicle_type: str,
    make_id: Optional[uuid.UUID] = None,
    model_id: Optional[uuid.UUID] = None,
    year: Optional[int] = None,
    color: Optional[str] = None,
    vin: Optional[str] = None,
    **kwargs
) -> Vehicle:
    """
    Factory function to create a new vehicle.
    
    Args:
        user_id: ID of vehicle owner
        license_plate: License plate number
        vehicle_type: Type of vehicle
        make_id: ID of vehicle make
        model_id: ID of vehicle model
        year: Model year
        color: Vehicle color
        vin: Vehicle Identification Number
        **kwargs: Additional vehicle attributes
        
    Returns:
        New Vehicle instance
    """
    vehicle = Vehicle(
        user_id=user_id,
        license_plate=license_plate,
        vehicle_type=vehicle_type,
        make_id=make_id,
        model_id=model_id,
        year=year,
        color=color,
        vin=vin,
        **kwargs
    )
    
    return vehicle


def create_system_tags(session) -> List[VehicleTag]:
    """
    Create default system tags.
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        List of created tags
    """
    tags = [
        VehicleTag(
            name='vip',
            category='status',
            description='VIP Customer',
            color='gold',
            icon='star',
            is_system=True
        ),
        VehicleTag(
            name='frequent',
            category='behavior',
            description='Frequent Parker',
            color='green',
            icon='clock',
            is_system=True
        ),
        VehicleTag(
            name='handicap',
            category='access',
            description='Handicap Access',
            color='blue',
            icon='wheelchair',
            is_system=True
        ),
        VehicleTag(
            name='ev',
            category='vehicle',
            description='Electric Vehicle',
            color='green',
            icon='bolt',
            is_system=True
        ),
        VehicleTag(
            name='commercial',
            category='vehicle',
            description='Commercial Vehicle',
            color='orange',
            icon='truck',
            is_system=True
        ),
        VehicleTag(
            name='government',
            category='status',
            description='Government Vehicle',
            color='purple',
            icon='building',
            is_system=True
        ),
        VehicleTag(
            name='staff',
            category='status',
            description='Staff Vehicle',
            color='blue',
            icon='user',
            is_system=True
        ),
        VehicleTag(
            name='blacklisted',
            category='status',
            description='Blacklisted',
            color='red',
            icon='ban',
            is_system=True
        ),
    ]
    
    for tag in tags:
        existing = session.query(VehicleTag).filter_by(name=tag.name).first()
        if not existing:
            session.add(tag)
    
    session.commit()
    return tags


# =========================================================================
# EXPORTS
# =========================================================================

__all__ = [
    'Vehicle',
    'VehicleMake',
    'VehicleModel',
    'VehicleType',
    'VehicleRegistration',
    'VehicleInsurance',
    'VehicleInspection',
    'VehicleMaintenance',
    'VehicleImage',
    'VehicleDocument',
    'VehicleViolation',
    'VehicleAccessHistory',
    'VehicleLocationHistory',
    'VehiclePreference',
    'VehicleAlert',
    'VehicleDevice',
    'VehicleOwnershipHistory',
    'VehicleTag',
    'VehicleTagAssignment',
    'VehicleStatus',
    'VehicleType',
    'VehicleClass',
    'FuelType',
    'TransmissionType',
    'DriveType',
    'RegistrationStatus',
    'InsuranceStatus',
    'InspectionStatus',
    'ViolationType',
    'ViolationSeverity',
    'AlertType',
    'AlertPriority',
    'AccessMethod',
    'OwnershipType',
    'create_vehicle',
    'create_system_tags',
]