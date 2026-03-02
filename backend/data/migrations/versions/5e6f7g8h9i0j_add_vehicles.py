# parking-management/data/migrations/versions/5e6f7g8h9i0j_add_vehicles.py

"""Add comprehensive vehicle management system

Revision ID: 5e6f7g8h9i0j
Revises: 4d5e6f7g8h9i
Create Date: 2024-02-15 14:00:00.123456

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '5e6f7g8h9i0j'
down_revision: Union[str, None] = '4d5e6f7g8h9i'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define table names
VEHICLES_TABLE = 'vehicles'
VEHICLE_MAKES_TABLE = 'vehicle_makes'
VEHICLE_MODELS_TABLE = 'vehicle_models'
VEHICLE_TYPES_TABLE = 'vehicle_types'
VEHICLE_REGISTRATIONS_TABLE = 'vehicle_registrations'
VEHICLE_INSURANCE_TABLE = 'vehicle_insurance'
VEHICLE_INSPECTIONS_TABLE = 'vehicle_inspections'
VEHICLE_MAINTENANCE_TABLE = 'vehicle_maintenance'
VEHICLE_IMAGES_TABLE = 'vehicle_images'
VEHICLE_DOCUMENTS_TABLE = 'vehicle_documents'
VEHICLE_TAGS_TABLE = 'vehicle_tags'
VEHICLE_TAG_ASSIGNMENTS_TABLE = 'vehicle_tag_assignments'
VEHICLE_OWNERSHIP_HISTORY_TABLE = 'vehicle_ownership_history'
VEHICLE_ACCESS_HISTORY_TABLE = 'vehicle_access_history'
VEHICLE_VIOLATIONS_TABLE = 'vehicle_violations'
VEHICLE_BLACKLIST_TABLE = 'vehicle_blacklist'
VEHICLE_ALERTS_TABLE = 'vehicle_alerts'
VEHICLE_PREFERENCES_TABLE = 'vehicle_preferences'
VEHICLE_DEVICES_TABLE = 'vehicle_devices'
VEHICLE_LOCATION_HISTORY_TABLE = 'vehicle_location_history'
VEHICLE_FUEL_HISTORY_TABLE = 'vehicle_fuel_history'
VEHICLE_WASH_HISTORY_TABLE = 'vehicle_wash_history'

# Define ENUM types for PostgreSQL
vehicle_status_enum = sa.Enum(
    'active', 'inactive', 'suspended', 'banned', 'pending_verification',
    'archived', 'deleted',
    name='vehicle_status'
)

vehicle_type_enum = sa.Enum(
    'car', 'suv', 'truck', 'van', 'motorcycle', 'scooter', 'bicycle',
    'ev', 'hybrid', 'luxury', 'classic', 'commercial', 'emergency',
    'government', 'diplomatic', 'rental', 'rideshare',
    name='vehicle_type'
)

vehicle_class_enum = sa.Enum(
    'compact', 'midsize', 'fullsize', 'economy', 'premium', 'luxury',
    'sports', 'off_road', 'commercial_light', 'commercial_heavy',
    name='vehicle_class'
)

fuel_type_enum = sa.Enum(
    'gasoline', 'diesel', 'electric', 'hybrid', 'plug_in_hybrid',
    'hydrogen', 'cng', 'lpg', 'ethanol',
    name='fuel_type'
)

transmission_type_enum = sa.Enum(
    'manual', 'automatic', 'cvt', 'semi_automatic', 'dual_clutch',
    name='transmission_type'
)

drive_type_enum = sa.Enum(
    'fwd', 'rwd', 'awd', '4wd', '4x4',
    name='drive_type'
)

registration_status_enum = sa.Enum(
    'current', 'expired', 'pending', 'suspended', 'revoked', 'renewal_due',
    name='registration_status'
)

insurance_status_enum = sa.Enum(
    'active', 'expired', 'cancelled', 'pending', 'lapsed',
    name='insurance_status'
)

inspection_status_enum = sa.Enum(
    'passed', 'failed', 'pending', 'scheduled', 'waived',
    name='inspection_status'
)

violation_type_enum = sa.Enum(
    'expired_meter', 'no_permit', 'handicap_violation', 'fire_lane',
    'loading_zone', 'reserved_spot', 'overtime_parking', 'improper_parking',
    'expired_registration', 'no_insurance', 'stolen_vehicle', 'suspicious',
    name='violation_type'
)

violation_severity_enum = sa.Enum(
    'warning', 'minor', 'moderate', 'severe', 'critical',
    name='violation_severity'
)

alert_type_enum = sa.Enum(
    'stolen', 'suspicious', 'wanted', 'amber_alert', 'silver_alert',
    'outstanding_warrant', 'unpaid_tickets', 'expired_registration',
    'expired_insurance', 'maintenance_due', 'inspection_due',
    name='alert_type'
)

alert_priority_enum = sa.Enum(
    'low', 'medium', 'high', 'critical', 'emergency',
    name='alert_priority'
)

access_method_enum = sa.Enum(
    'rfid', 'license_plate', 'qr_code', 'barcode', 'manual_entry',
    'mobile_app', 'facial_recognition', 'bluetooth', 'wifi',
    name='access_method'
)

ownership_type_enum = sa.Enum(
    'owner', 'lessee', 'renter', 'company', 'fleet', 'government',
    name='ownership_type'
)


def upgrade() -> None:
    """
    Upgrade migration - creates comprehensive vehicle management system
    """
    logger.info(f"Starting migration {revision}: Add vehicle management system")
    
    # Create ENUM types first (PostgreSQL specific)
    if op.get_context().dialect.name == 'postgresql':
        enums = [
            vehicle_status_enum, vehicle_type_enum, vehicle_class_enum,
            fuel_type_enum, transmission_type_enum, drive_type_enum,
            registration_status_enum, insurance_status_enum, inspection_status_enum,
            violation_type_enum, violation_severity_enum, alert_type_enum,
            alert_priority_enum, access_method_enum, ownership_type_enum
        ]
        for enum in enums:
            enum.create(op.get_bind(), checkfirst=True)
        logger.info("Created ENUM types")
    
    # Create vehicle makes table (reference data)
    logger.info("Creating vehicle makes table")
    op.create_table(
        VEHICLE_MAKES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('country', sa.String(100)),
        sa.Column('founded_year', sa.Integer),
        sa.Column('website', sa.String(255)),
        sa.Column('logo_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_popular', sa.Boolean, server_default='false'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_vehicle_makes_name', 'name', unique=True),
        sa.Index('ix_vehicle_makes_is_active', 'is_active'),
        
        # Table comments
        sa.Comment('Reference table for vehicle manufacturers'),
    )
    
    # Create vehicle models table (reference data)
    logger.info("Creating vehicle models table")
    op.create_table(
        VEHICLE_MODELS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('make_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('vehicle_type', sa.String(50)),
        sa.Column('vehicle_class', sa.String(50)),
        sa.Column('start_year', sa.Integer),
        sa.Column('end_year', sa.Integer),
        sa.Column('fuel_types', postgresql.ARRAY(sa.String(50))),
        sa.Column('transmission_types', postgresql.ARRAY(sa.String(50))),
        sa.Column('drive_types', postgresql.ARRAY(sa.String(50))),
        sa.Column('engine_sizes', postgresql.ARRAY(sa.String(20))),
        sa.Column('length_mm', sa.Integer),
        sa.Column('width_mm', sa.Integer),
        sa.Column('height_mm', sa.Integer),
        sa.Column('weight_kg', sa.Integer),
        sa.Column('image_url', sa.String(500)),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_popular', sa.Boolean, server_default='false'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_vehicle_models_make_name', 'make_id', 'name', unique=True),
        sa.Index('ix_vehicle_models_vehicle_type', 'vehicle_type'),
        sa.Index('ix_vehicle_models_is_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['make_id'], [f'{VEHICLE_MAKES_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Reference table for vehicle models'),
    )
    
    # Create vehicle types table (reference data)
    logger.info("Creating vehicle types table")
    op.create_table(
        VEHICLE_TYPES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('display_name', sa.String(50), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(50)),  # passenger, commercial, motorcycle
        sa.Column('default_height_cm', sa.Integer),
        sa.Column('default_width_cm', sa.Integer),
        sa.Column('default_length_cm', sa.Integer),
        sa.Column('default_weight_kg', sa.Integer),
        sa.Column('requires_special_spot', sa.Boolean, server_default='false'),
        sa.Column('special_spot_types', postgresql.ARRAY(sa.String(50))),
        sa.Column('max_parking_duration_hours', sa.Integer),
        sa.Column('rate_multiplier', sa.Numeric(3, 2), server_default='1.0'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_vehicle_types_name', 'name', unique=True),
        sa.Index('ix_vehicle_types_category', 'category'),
        sa.Index('ix_vehicle_types_is_active', 'is_active'),
        
        # Table comments
        sa.Comment('Reference table for vehicle types and their characteristics'),
    )
    
    # Create vehicles table (main table)
    logger.info("Creating vehicles table")
    op.create_table(
        VEHICLES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_number', sa.String(50), nullable=False, unique=True),
        
        # Owner/User relationship
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ownership_type', sa.String(50), nullable=False, server_default='owner'),
        sa.Column('company_id', sa.String(100)),  # For fleet/corporate vehicles
        
        # License plate
        sa.Column('license_plate', sa.String(20), nullable=False),
        sa.Column('license_plate_state', sa.String(50)),
        sa.Column('license_plate_country', sa.String(2)),
        sa.Column('license_plate_issue_date', sa.Date),
        sa.Column('license_plate_expiry_date', sa.Date),
        sa.Column('license_plate_type', sa.String(50)),  # standard, personalized, temporary
        
        # Vehicle identification
        sa.Column('vin', sa.String(17), unique=True),
        sa.Column('make_id', postgresql.UUID(as_uuid=True)),
        sa.Column('model_id', postgresql.UUID(as_uuid=True)),
        sa.Column('vehicle_type', sa.String(50), nullable=False),
        sa.Column('vehicle_class', sa.String(50)),
        sa.Column('year', sa.Integer),
        sa.Column('trim', sa.String(100)),
        sa.Column('color', sa.String(50)),
        sa.Column('color_code', sa.String(10)),  # Hex code
        sa.Column('secondary_color', sa.String(50)),
        
        # Physical characteristics
        sa.Column('length_cm', sa.Integer),
        sa.Column('width_cm', sa.Integer),
        sa.Column('height_cm', sa.Integer),
        sa.Column('weight_kg', sa.Integer),
        sa.Column('wheelbase_cm', sa.Integer),
        sa.Column('ground_clearance_cm', sa.Integer),
        sa.Column('number_of_axles', sa.Integer, server_default='2'),
        sa.Column('number_of_wheels', sa.Integer, server_default='4'),
        
        # Propulsion
        sa.Column('fuel_type', sa.String(50)),
        sa.Column('fuel_capacity_liters', sa.Float),
        sa.Column('fuel_efficiency_city', sa.Float),  # L/100km
        sa.Column('fuel_efficiency_highway', sa.Float),
        sa.Column('fuel_efficiency_combined', sa.Float),
        sa.Column('battery_capacity_kwh', sa.Float),
        sa.Column('electric_range_km', sa.Integer),
        sa.Column('emissions_rating', sa.String(20)),  # Euro standard, etc.
        
        # Drivetrain
        sa.Column('transmission_type', sa.String(50)),
        sa.Column('transmission_speeds', sa.Integer),
        sa.Column('drive_type', sa.String(20)),
        sa.Column('engine_type', sa.String(100)),
        sa.Column('engine_displacement_cc', sa.Integer),
        sa.Column('horsepower', sa.Integer),
        
        # Features
        sa.Column('has_sunroof', sa.Boolean, server_default='false'),
        sa.Column('has_convertible', sa.Boolean, server_default='false'),
        sa.Column('has_third_row', sa.Boolean, server_default='false'),
        sa.Column('has_tow_hitch', sa.Boolean, server_default='false'),
        sa.Column('towing_capacity_kg', sa.Integer),
        sa.Column('has_roof_rack', sa.Boolean, server_default='false'),
        sa.Column('roof_rack_type', sa.String(50)),
        sa.Column('has_bike_rack', sa.Boolean, server_default='false'),
        sa.Column('has_ski_rack', sa.Boolean, server_default='false'),
        
        # EV specific
        sa.Column('has_ev_charger', sa.Boolean, server_default='false'),
        sa.Column('ev_charger_type', sa.String(50)),  # Level 1, Level 2, DC Fast
        sa.Column('ev_charger_port', sa.String(50)),  # J1772, CCS, CHAdeMO, Tesla
        sa.Column('ev_charger_power_kw', sa.Float),
        
        # Access and identification
        sa.Column('has_rfid', sa.Boolean, server_default='false'),
        sa.Column('rfid_tag', sa.String(100), unique=True),
        sa.Column('has_transponder', sa.Boolean, server_default='false'),
        sa.Column('transponder_id', sa.String(100), unique=True),
        sa.Column('has_permit', sa.Boolean, server_default='false'),
        sa.Column('permit_number', sa.String(100)),
        sa.Column('permit_expiry', sa.Date),
        sa.Column('permit_type', sa.String(50)),
        sa.Column('permit_zone', sa.String(50)),
        
        # Status
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('is_verified', sa.Boolean, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True)),
        sa.Column('is_blacklisted', sa.Boolean, server_default='false'),
        sa.Column('blacklisted_at', sa.DateTime(timezone=True)),
        sa.Column('blacklisted_reason', sa.Text),
        sa.Column('is_stolen', sa.Boolean, server_default='false'),
        sa.Column('stolen_reported_at', sa.DateTime(timezone=True)),
        sa.Column('stolen_recovered_at', sa.DateTime(timezone=True)),
        
        # Usage statistics
        sa.Column('total_parking_sessions', sa.Integer, server_default='0'),
        sa.Column('total_parking_duration_minutes', sa.Integer, server_default='0'),
        sa.Column('total_parking_amount', sa.Numeric(10, 2), server_default='0'),
        sa.Column('last_parking_at', sa.DateTime(timezone=True)),
        sa.Column('last_parking_spot', sa.String(50)),
        sa.Column('last_parking_zone', sa.String(100)),
        sa.Column('average_parking_duration', sa.Integer),
        sa.Column('favorite_zone', sa.String(100)),
        sa.Column('favorite_time', sa.Time),
        
        # Compliance
        sa.Column('registration_status', sa.String(50)),
        sa.Column('registration_expiry', sa.Date),
        sa.Column('insurance_status', sa.String(50)),
        sa.Column('insurance_expiry', sa.Date),
        sa.Column('inspection_status', sa.String(50)),
        sa.Column('inspection_expiry', sa.Date),
        
        # Alerts and flags
        sa.Column('has_active_alerts', sa.Boolean, server_default='false'),
        sa.Column('alert_count', sa.Integer, server_default='0'),
        sa.Column('violation_count', sa.Integer, server_default='0'),
        sa.Column('unpaid_violations', sa.Integer, server_default='0'),
        sa.Column('unpaid_amount', sa.Numeric(10, 2), server_default='0'),
        
        # Notes and metadata
        sa.Column('notes', sa.Text),
        sa.Column('special_instructions', sa.Text),
        sa.Column('tags', postgresql.ARRAY(sa.String(50))),
        sa.Column('custom_fields', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        
        # Audit
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True)),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        
        # Indexes
        sa.Index('ix_vehicles_number', 'vehicle_number', unique=True),
        sa.Index('ix_vehicles_license_plate', 'license_plate', 'license_plate_state'),
        sa.Index('ix_vehicles_vin', 'vin', unique=True),
        sa.Index('ix_vehicles_user_id', 'user_id'),
        sa.Index('ix_vehicles_status', 'status'),
        sa.Index('ix_vehicles_type', 'vehicle_type'),
        sa.Index('ix_vehicles_make_model', 'make_id', 'model_id'),
        sa.Index('ix_vehicles_rfid', 'rfid_tag', unique=True),
        sa.Index('ix_vehicles_transponder', 'transponder_id', unique=True),
        sa.Index('ix_vehicles_is_blacklisted', 'is_blacklisted'),
        sa.Index('ix_vehicles_is_stolen', 'is_stolen'),
        sa.Index('ix_vehicles_registration_expiry', 'registration_expiry'),
        sa.Index('ix_vehicles_insurance_expiry', 'insurance_expiry'),
        sa.Index('ix_vehicles_created_at', 'created_at'),
        sa.Index('ix_vehicles_deleted_at', 'deleted_at'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['make_id'], [f'{VEHICLE_MAKES_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['model_id'], [f'{VEHICLE_MODELS_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Main vehicles table with comprehensive vehicle information'),
    )
    
    # Create vehicle registrations table
    logger.info("Creating vehicle registrations table")
    op.create_table(
        VEHICLE_REGISTRATIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('registration_number', sa.String(100), nullable=False),
        sa.Column('jurisdiction', sa.String(100)),  # DMV, DOT, etc.
        sa.Column('state', sa.String(50)),
        sa.Column('country', sa.String(2)),
        sa.Column('issue_date', sa.Date),
        sa.Column('effective_date', sa.Date),
        sa.Column('expiry_date', sa.Date),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('class', sa.String(50)),
        sa.Column('type', sa.String(50)),
        sa.Column('weight_class', sa.String(50)),
        sa.Column('passenger_capacity', sa.Integer),
        sa.Column('commercial_use', sa.Boolean, server_default='false'),
        sa.Column('hazardous_materials', sa.Boolean, server_default='false'),
        sa.Column('registered_owner_name', sa.String(255)),
        sa.Column('registered_owner_address', sa.Text),
        sa.Column('lienholder_name', sa.String(255)),
        sa.Column('lienholder_address', sa.Text),
        sa.Column('registration_document_url', sa.String(500)),
        sa.Column('verified', sa.Boolean, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True)),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_reg_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_reg_number', 'registration_number'),
        sa.Index('ix_vehicle_reg_expiry', 'expiry_date'),
        sa.Index('ix_vehicle_reg_status', 'status'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Vehicle registration history and details'),
    )
    
    # Create vehicle insurance table
    logger.info("Creating vehicle insurance table")
    op.create_table(
        VEHICLE_INSURANCE_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_number', sa.String(100), nullable=False),
        sa.Column('provider', sa.String(255), nullable=False),
        sa.Column('provider_phone', sa.String(20)),
        sa.Column('provider_email', sa.String(255)),
        sa.Column('agent_name', sa.String(255)),
        sa.Column('agent_phone', sa.String(20)),
        sa.Column('coverage_type', sa.String(100)),
        sa.Column('coverage_amount', sa.Numeric(10, 2)),
        sa.Column('deductible', sa.Numeric(10, 2)),
        sa.Column('liability_coverage', sa.Numeric(10, 2)),
        sa.Column('comprehensive_coverage', sa.Numeric(10, 2)),
        sa.Column('collision_coverage', sa.Numeric(10, 2)),
        sa.Column('uninsured_motorist', sa.Numeric(10, 2)),
        sa.Column('medical_payments', sa.Numeric(10, 2)),
        sa.Column('effective_date', sa.Date, nullable=False),
        sa.Column('expiry_date', sa.Date, nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('premium_amount', sa.Numeric(10, 2)),
        sa.Column('premium_frequency', sa.String(20)),  # monthly, yearly
        sa.Column('insured_name', sa.String(255)),
        sa.Column('insured_address', sa.Text),
        sa.Column('additional_drivers', postgresql.JSONB),
        sa.Column('excluded_drivers', postgresql.JSONB),
        sa.Column('policy_document_url', sa.String(500)),
        sa.Column('proof_of_insurance_url', sa.String(500)),
        sa.Column('verified', sa.Boolean, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True)),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_ins_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_ins_policy', 'policy_number'),
        sa.Index('ix_vehicle_ins_expiry', 'expiry_date'),
        sa.Index('ix_vehicle_ins_status', 'status'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Vehicle insurance policies and coverage details'),
    )
    
    # Create vehicle inspections table
    logger.info("Creating vehicle inspections table")
    op.create_table(
        VEHICLE_INSPECTIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('inspection_number', sa.String(100), nullable=False),
        sa.Column('inspection_type', sa.String(100)),  # safety, emissions, annual
        sa.Column('inspector_name', sa.String(255)),
        sa.Column('inspector_id', sa.String(100)),
        sa.Column('inspection_facility', sa.String(255)),
        sa.Column('inspection_date', sa.Date, nullable=False),
        sa.Column('expiry_date', sa.Date),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('result', sa.String(50)),  # pass, fail, conditional
        sa.Column('odometer_reading', sa.Integer),
        sa.Column('emissions_result', sa.String(100)),
        sa.Column('emissions_value', sa.Float),
        sa.Column('safety_items', postgresql.JSONB),
        sa.Column('failed_items', postgresql.JSONB),
        sa.Column('warnings', postgresql.JSONB),
        sa.Column('recommendations', sa.Text),
        sa.Column('corrective_actions', sa.Text),
        sa.Column('certificate_number', sa.String(100)),
        sa.Column('certificate_url', sa.String(500)),
        sa.Column('report_url', sa.String(500)),
        sa.Column('images', postgresql.ARRAY(sa.String(500))),
        sa.Column('verified', sa.Boolean, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True)),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_insp_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_insp_number', 'inspection_number'),
        sa.Index('ix_vehicle_insp_date', 'inspection_date'),
        sa.Index('ix_vehicle_insp_status', 'status'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Vehicle inspection records and results'),
    )
    
    # Create vehicle maintenance table
    logger.info("Creating vehicle maintenance table")
    op.create_table(
        VEHICLE_MAINTENANCE_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('maintenance_type', sa.String(100), nullable=False),
        sa.Column('service_date', sa.Date, nullable=False),
        sa.Column('service_provider', sa.String(255)),
        sa.Column('mechanic_name', sa.String(255)),
        sa.Column('odometer_reading', sa.Integer),
        sa.Column('description', sa.Text),
        sa.Column('items_serviced', postgresql.JSONB),
        sa.Column('parts_replaced', postgresql.JSONB),
        sa.Column('labor_hours', sa.Float),
        sa.Column('labor_cost', sa.Numeric(10, 2)),
        sa.Column('parts_cost', sa.Numeric(10, 2)),
        sa.Column('tax_amount', sa.Numeric(10, 2)),
        sa.Column('total_cost', sa.Numeric(10, 2)),
        sa.Column('invoice_number', sa.String(100)),
        sa.Column('invoice_url', sa.String(500)),
        sa.Column('receipt_url', sa.String(500)),
        sa.Column('warranty_until', sa.Date),
        sa.Column('next_service_due', sa.Date),
        sa.Column('next_service_odometer', sa.Integer),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_maint_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_maint_date', 'service_date'),
        sa.Index('ix_vehicle_maint_type', 'maintenance_type'),
        sa.Index('ix_vehicle_maint_next', 'next_service_due'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Vehicle maintenance history and upcoming services'),
    )
    
    # Create vehicle images table
    logger.info("Creating vehicle images table")
    op.create_table(
        VEHICLE_IMAGES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_type', sa.String(50)),  # front, rear, side, interior, license_plate
        sa.Column('image_url', sa.String(500), nullable=False),
        sa.Column('thumbnail_url', sa.String(500)),
        sa.Column('title', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('is_primary', sa.Boolean, server_default='false'),
        sa.Column('is_verified', sa.Boolean, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True)),
        sa.Column('capture_date', sa.DateTime(timezone=True)),
        sa.Column('capture_location', sa.String(255)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_images_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_images_type', 'image_type'),
        sa.Index('ix_vehicle_images_primary', 'is_primary'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Vehicle images and photos'),
    )
    
    # Create vehicle documents table
    logger.info("Creating vehicle documents table")
    op.create_table(
        VEHICLE_DOCUMENTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.String(100), nullable=False),  # title, registration, insurance, etc.
        sa.Column('document_name', sa.String(255)),
        sa.Column('document_number', sa.String(100)),
        sa.Column('issue_date', sa.Date),
        sa.Column('expiry_date', sa.Date),
        sa.Column('issuing_authority', sa.String(255)),
        sa.Column('file_url', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(50)),
        sa.Column('file_size', sa.Integer),
        sa.Column('is_verified', sa.Boolean, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True)),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_docs_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_docs_type', 'document_type'),
        sa.Index('ix_vehicle_docs_expiry', 'expiry_date'),
        sa.Index('ix_vehicle_docs_verified', 'is_verified'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Vehicle documents and files'),
    )
    
    # Create vehicle tags table (for custom categorization)
    logger.info("Creating vehicle tags table")
    op.create_table(
        VEHICLE_TAGS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('category', sa.String(50)),
        sa.Column('description', sa.Text),
        sa.Column('color', sa.String(20)),
        sa.Column('icon', sa.String(50)),
        sa.Column('is_system', sa.Boolean, server_default='false'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_tags_name', 'name', unique=True),
        sa.Index('ix_vehicle_tags_category', 'category'),
        sa.Index('ix_vehicle_tags_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Custom tags for vehicle categorization'),
    )
    
    # Create vehicle tag assignments table
    logger.info("Creating vehicle tag assignments table")
    op.create_table(
        VEHICLE_TAG_ASSIGNMENTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('metadata', postgresql.JSONB),
        
        # Indexes
        sa.Index('ix_vehicle_tag_assign_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_tag_assign_tag', 'tag_id'),
        sa.Index('ix_vehicle_tag_assign_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], [f'{VEHICLE_TAGS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='SET NULL'),
        
        # Unique constraint
        sa.UniqueConstraint('vehicle_id', 'tag_id', name='uq_vehicle_tag'),
        
        # Table comments
        sa.Comment('Many-to-many relationship between vehicles and tags'),
    )
    
    # Create vehicle ownership history table
    logger.info("Creating vehicle ownership history table")
    op.create_table(
        VEHICLE_OWNERSHIP_HISTORY_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('previous_owner_id', postgresql.UUID(as_uuid=True)),
        sa.Column('new_owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ownership_type', sa.String(50)),
        sa.Column('transfer_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('transfer_reason', sa.String(255)),
        sa.Column('document_url', sa.String(500)),
        sa.Column('verified', sa.Boolean, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('verified_by', postgresql.UUID(as_uuid=True)),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_ownership_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_ownership_prev', 'previous_owner_id'),
        sa.Index('ix_vehicle_ownership_new', 'new_owner_id'),
        sa.Index('ix_vehicle_ownership_date', 'transfer_date'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['previous_owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['new_owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('History of vehicle ownership transfers'),
    )
    
    # Create vehicle access history table
    logger.info("Creating vehicle access history table")
    op.create_table(
        VEHICLE_ACCESS_HISTORY_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('access_method', sa.String(50), nullable=False),
        sa.Column('access_type', sa.String(20)),  # entry, exit, denied
        sa.Column('gate_id', sa.String(100)),
        sa.Column('gate_name', sa.String(255)),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True)),
        sa.Column('spot_id', postgresql.UUID(as_uuid=True)),
        sa.Column('session_id', postgresql.UUID(as_uuid=True)),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('image_url', sa.String(500)),
        sa.Column('confidence', sa.Float),  # For plate recognition
        sa.Column('matched_plate', sa.String(20)),
        sa.Column('matched_vehicle_id', postgresql.UUID(as_uuid=True)),
        sa.Column('denied_reason', sa.String(255)),
        sa.Column('response_time_ms', sa.Integer),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_vehicle_access_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_access_timestamp', 'timestamp'),
        sa.Index('ix_vehicle_access_method', 'access_method'),
        sa.Index('ix_vehicle_access_gate', 'gate_id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['zone_id'], ['parking_zones.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['spot_id'], ['parking_spots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['parking_sessions.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('History of vehicle access attempts and entries'),
        
        # Partition by month
        postgresql_partition_by='RANGE (timestamp)',
    )
    
    # Create vehicle violations table
    logger.info("Creating vehicle violations table")
    op.create_table(
        VEHICLE_VIOLATIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('violation_number', sa.String(50), nullable=False, unique=True),
        sa.Column('violation_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('location', sa.String(255)),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True)),
        sa.Column('spot_id', postgresql.UUID(as_uuid=True)),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('detected_by', sa.String(100)),  # camera, officer, system
        sa.Column('officer_id', sa.String(100)),
        sa.Column('officer_name', sa.String(255)),
        sa.Column('evidence_urls', postgresql.ARRAY(sa.String(500))),
        sa.Column('license_plate_image', sa.String(500)),
        sa.Column('fine_amount', sa.Numeric(10, 2)),
        sa.Column('currency', sa.String(3), server_default='USD'),
        sa.Column('paid', sa.Boolean, server_default='false'),
        sa.Column('paid_at', sa.DateTime(timezone=True)),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('disputed', sa.Boolean, server_default='false'),
        sa.Column('dispute_reason', sa.Text),
        sa.Column('dispute_resolution', sa.Text),
        sa.Column('dispute_resolved_at', sa.DateTime(timezone=True)),
        sa.Column('appeal_deadline', sa.DateTime(timezone=True)),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_violations_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_violations_number', 'violation_number', unique=True),
        sa.Index('ix_vehicle_violations_timestamp', 'timestamp'),
        sa.Index('ix_vehicle_violations_type', 'violation_type'),
        sa.Index('ix_vehicle_violations_paid', 'paid'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['zone_id'], ['parking_zones.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['spot_id'], ['parking_spots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Parking violations associated with vehicles'),
    )
    
    # Create vehicle blacklist table
    logger.info("Creating vehicle blacklist table")
    op.create_table(
        VEHICLE_BLACKLIST_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True)),
        sa.Column('license_plate', sa.String(20)),
        sa.Column('license_plate_state', sa.String(50)),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('reason_code', sa.String(100)),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('listed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('listed_by', postgresql.UUID(as_uuid=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('is_permanent', sa.Boolean, server_default='false'),
        sa.Column('removed_at', sa.DateTime(timezone=True)),
        sa.Column('removed_by', postgresql.UUID(as_uuid=True)),
        sa.Column('removal_reason', sa.Text),
        sa.Column('source', sa.String(100)),  # system, court, law_enforcement
        sa.Column('reference_number', sa.String(100)),
        sa.Column('document_url', sa.String(500)),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_vehicle_blacklist_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_blacklist_plate', 'license_plate', 'license_plate_state'),
        sa.Index('ix_vehicle_blacklist_active', 'removed_at', 'expires_at'),
        sa.Index('ix_vehicle_blacklist_severity', 'severity'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['listed_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['removed_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Blacklisted vehicles with access restrictions'),
    )
    
    # Create vehicle alerts table
    logger.info("Creating vehicle alerts table")
    op.create_table(
        VEHICLE_ALERTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True)),
        sa.Column('license_plate', sa.String(20)),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('source', sa.String(100)),
        sa.Column('source_reference', sa.String(100)),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True)),
        sa.Column('resolution_notes', sa.Text),
        sa.Column('requires_action', sa.Boolean, server_default='false'),
        sa.Column('action_taken', sa.Text),
        sa.Column('notified_users', postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column('notified_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_alerts_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_alerts_plate', 'license_plate'),
        sa.Index('ix_vehicle_alerts_type', 'alert_type'),
        sa.Index('ix_vehicle_alerts_priority', 'priority'),
        sa.Index('ix_vehicle_alerts_active', 'is_active'),
        sa.Index('ix_vehicle_alerts_expires', 'expires_at'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Alerts and notifications for vehicles'),
    )
    
    # Create vehicle preferences table
    logger.info("Creating vehicle preferences table")
    op.create_table(
        VEHICLE_PREFERENCES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('preferred_parking_zones', postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column('preferred_parking_types', postgresql.ARRAY(sa.String(50))),
        sa.Column('avoid_areas', postgresql.ARRAY(sa.String(255))),
        sa.Column('max_walking_distance', sa.Integer),  # meters
        sa.Column('preferred_entry_gates', postgresql.ARRAY(sa.String(100))),
        sa.Column('preferred_exit_gates', postgresql.ARRAY(sa.String(100))),
        sa.Column('notify_on_entry', sa.Boolean, server_default='true'),
        sa.Column('notify_on_exit', sa.Boolean, server_default='true'),
        sa.Column('notify_on_violation', sa.Boolean, server_default='true'),
        sa.Column('notify_on_alert', sa.Boolean, server_default='true'),
        sa.Column('auto_pay', sa.Boolean, server_default='false'),
        sa.Column('default_payment_method_id', postgresql.UUID(as_uuid=True)),
        sa.Column('auto_extend', sa.Boolean, server_default='false'),
        sa.Column('max_extension_minutes', sa.Integer),
        sa.Column('reminder_minutes', postgresql.ARRAY(sa.Integer)),
        sa.Column('special_instructions', sa.Text),
        sa.Column('settings', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['default_payment_method_id'], ['payment_methods.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('User preferences for each vehicle'),
    )
    
    # Create vehicle devices table (for IoT devices in vehicles)
    logger.info("Creating vehicle devices table")
    op.create_table(
        VEHICLE_DEVICES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_type', sa.String(50), nullable=False),  # tracker, beacon, transponder
        sa.Column('device_id', sa.String(100), nullable=False, unique=True),
        sa.Column('device_name', sa.String(255)),
        sa.Column('manufacturer', sa.String(255)),
        sa.Column('model', sa.String(100)),
        sa.Column('serial_number', sa.String(100), unique=True),
        sa.Column('firmware_version', sa.String(50)),
        sa.Column('hardware_version', sa.String(50)),
        sa.Column('battery_level', sa.Integer),
        sa.Column('last_ping', sa.DateTime(timezone=True)),
        sa.Column('last_location', postgresql.JSONB),
        sa.Column('status', sa.String(50), server_default='active'),
        sa.Column('activated_at', sa.DateTime(timezone=True)),
        sa.Column('deactivated_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_devices_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_devices_device', 'device_id', unique=True),
        sa.Index('ix_vehicle_devices_serial', 'serial_number', unique=True),
        sa.Index('ix_vehicle_devices_status', 'status'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('IoT devices installed in vehicles'),
    )
    
    # Create vehicle location history table
    logger.info("Creating vehicle location history table")
    op.create_table(
        VEHICLE_LOCATION_HISTORY_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_id', postgresql.UUID(as_uuid=True)),
        sa.Column('latitude', sa.Numeric(10, 8)),
        sa.Column('longitude', sa.Numeric(11, 8)),
        sa.Column('altitude', sa.Float),
        sa.Column('speed', sa.Float),  # km/h
        sa.Column('heading', sa.Float),  # degrees
        sa.Column('accuracy', sa.Float),  # meters
        sa.Column('source', sa.String(50)),  # gps, wifi, cellular
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True)),
        sa.Column('spot_id', postgresql.UUID(as_uuid=True)),
        sa.Column('session_id', postgresql.UUID(as_uuid=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_vehicle_location_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_location_timestamp', 'timestamp'),
        sa.Index('ix_vehicle_location_coords', 'latitude', 'longitude'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['device_id'], [f'{VEHICLE_DEVICES_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['zone_id'], ['parking_zones.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['spot_id'], ['parking_spots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['parking_sessions.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Historical vehicle location tracking'),
        
        # Partition by month
        postgresql_partition_by='RANGE (timestamp)',
    )
    
    # Create vehicle fuel history table (for EV/fuel tracking)
    logger.info("Creating vehicle fuel history table")
    op.create_table(
        VEHICLE_FUEL_HISTORY_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fuel_type', sa.String(50), nullable=False),
        sa.Column('amount', sa.Float),  # liters or kWh
        sa.Column('cost', sa.Numeric(10, 2)),
        sa.Column('currency', sa.String(3), server_default='USD'),
        sa.Column('location', sa.String(255)),
        sa.Column('station_name', sa.String(255)),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('odometer_reading', sa.Integer),
        sa.Column('is_full_tank', sa.Boolean),
        sa.Column('fuel_efficiency', sa.Float),  # calculated after fill-up
        sa.Column('session_id', postgresql.UUID(as_uuid=True)),  # if charged during parking
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_fuel_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_fuel_timestamp', 'timestamp'),
        sa.Index('ix_vehicle_fuel_type', 'fuel_type'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['parking_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Fuel and charging history for vehicles'),
    )
    
    # Create vehicle wash history table
    logger.info("Creating vehicle wash history table")
    op.create_table(
        VEHICLE_WASH_HISTORY_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('wash_type', sa.String(50), nullable=False),  # basic, premium, detail
        sa.Column('provider', sa.String(255)),
        sa.Column('location', sa.String(255)),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cost', sa.Numeric(10, 2)),
        sa.Column('currency', sa.String(3), server_default='USD'),
        sa.Column('rating', sa.Integer),  # 1-5
        sa.Column('notes', sa.Text),
        sa.Column('images', postgresql.ARRAY(sa.String(500))),
        sa.Column('session_id', postgresql.UUID(as_uuid=True)),  # if washed during parking
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_vehicle_wash_vehicle', 'vehicle_id'),
        sa.Index('ix_vehicle_wash_timestamp', 'timestamp'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['vehicle_id'], [f'{VEHICLES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['parking_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Vehicle wash and detailing history'),
    )
    
    # Create functions and triggers
    logger.info("Creating database functions and triggers")
    
    # Function to generate vehicle number
    op.execute("""
    CREATE OR REPLACE FUNCTION generate_vehicle_number()
    RETURNS TRIGGER AS $$
    DECLARE
        seq_num INTEGER;
        year_prefix TEXT;
    BEGIN
        year_prefix := TO_CHAR(CURRENT_DATE, 'YYYY');
        
        SELECT COALESCE(MAX(SUBSTRING(vehicle_number FROM 10)::INTEGER), 0) + 1
        INTO seq_num
        FROM vehicles
        WHERE vehicle_number LIKE 'VEH-' || year_prefix || '-%';
        
        NEW.vehicle_number := 'VEH-' || year_prefix || '-' || LPAD(seq_num::TEXT, 6, '0');
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for vehicle number
    op.execute("""
    CREATE TRIGGER generate_vehicle_number_trigger
        BEFORE INSERT ON vehicles
        FOR EACH ROW
        WHEN (NEW.vehicle_number IS NULL)
        EXECUTE FUNCTION generate_vehicle_number();
    """)
    
    # Function to generate violation number
    op.execute("""
    CREATE OR REPLACE FUNCTION generate_violation_number()
    RETURNS TRIGGER AS $$
    DECLARE
        seq_num INTEGER;
        date_prefix TEXT;
    BEGIN
        date_prefix := TO_CHAR(CURRENT_DATE, 'YYYYMMDD');
        
        SELECT COALESCE(MAX(SUBSTRING(violation_number FROM 11)::INTEGER), 0) + 1
        INTO seq_num
        FROM vehicle_violations
        WHERE violation_number LIKE 'VIO-' || date_prefix || '-%';
        
        NEW.violation_number := 'VIO-' || date_prefix || '-' || LPAD(seq_num::TEXT, 6, '0');
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for violation number
    op.execute("""
    CREATE TRIGGER generate_violation_number_trigger
        BEFORE INSERT ON vehicle_violations
        FOR EACH ROW
        WHEN (NEW.violation_number IS NULL)
        EXECUTE FUNCTION generate_violation_number();
    """)
    
    # Function to update vehicle statistics
    op.execute("""
    CREATE OR REPLACE FUNCTION update_vehicle_statistics()
    RETURNS TRIGGER AS $$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            IF NEW.status = 'active' AND NEW.vehicle_id IS NOT NULL THEN
                UPDATE vehicles 
                SET 
                    total_parking_sessions = total_parking_sessions + 1,
                    total_parking_duration_minutes = total_parking_duration_minutes + 
                        EXTRACT(EPOCH FROM (NEW.end_time - NEW.start_time)) / 60,
                    total_parking_amount = total_parking_amount + NEW.total_amount,
                    last_parking_at = NEW.start_time,
                    last_parking_spot = (SELECT spot_number FROM parking_spots WHERE id = NEW.spot_id),
                    last_parking_zone = (SELECT name FROM parking_zones WHERE id = 
                        (SELECT zone_id FROM parking_spots WHERE id = NEW.spot_id))
                WHERE id = NEW.vehicle_id;
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for vehicle statistics
    op.execute("""
    CREATE TRIGGER update_vehicle_statistics_trigger
        AFTER INSERT ON parking_sessions
        FOR EACH ROW
        EXECUTE FUNCTION update_vehicle_statistics();
    """)
    
    # Function to check vehicle blacklist
    op.execute("""
    CREATE OR REPLACE FUNCTION check_vehicle_blacklist()
    RETURNS TRIGGER AS $$
    DECLARE
        v_blacklist RECORD;
    BEGIN
        -- Check if vehicle is blacklisted
        SELECT * INTO v_blacklist
        FROM vehicle_blacklist
        WHERE vehicle_id = NEW.vehicle_id
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            AND removed_at IS NULL;
        
        IF v_blacklist.id IS NOT NULL THEN
            -- Log access denial
            INSERT INTO vehicle_access_history (
                id, vehicle_id, access_method, access_type, gate_id,
                timestamp, denied_reason, metadata
            ) VALUES (
                gen_random_uuid(), NEW.vehicle_id, NEW.access_method, 'denied',
                NEW.gate_id, CURRENT_TIMESTAMP, 
                'Vehicle is blacklisted: ' || v_blacklist.reason,
                jsonb_build_object('blacklist_id', v_blacklist.id)
            );
            
            RETURN NULL; -- Prevent access
        END IF;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create views
    logger.info("Creating views")
    
    # View for active vehicles
    op.execute("""
    CREATE OR REPLACE VIEW v_active_vehicles AS
    SELECT 
        v.id,
        v.vehicle_number,
        v.license_plate,
        v.license_plate_state,
        v.vin,
        v.vehicle_type,
        vm.name as make,
        vmd.name as model,
        v.year,
        v.color,
        u.email as owner_email,
        u.first_name || ' ' || u.last_name as owner_name,
        v.status,
        v.is_blacklisted,
        v.is_stolen,
        v.registration_expiry,
        v.insurance_expiry,
        v.last_parking_at
    FROM vehicles v
    LEFT JOIN vehicle_makes vm ON v.make_id = vm.id
    LEFT JOIN vehicle_models vmd ON v.model_id = vmd.id
    LEFT JOIN users u ON v.user_id = u.id
    WHERE v.status = 'active' AND v.deleted_at IS NULL;
    """)
    
    # View for vehicle compliance
    op.execute("""
    CREATE OR REPLACE VIEW v_vehicle_compliance AS
    SELECT 
        v.id,
        v.license_plate,
        v.license_plate_state,
        v.registration_status,
        v.registration_expiry,
        v.insurance_status,
        v.insurance_expiry,
        v.inspection_status,
        v.inspection_expiry,
        CASE 
            WHEN v.registration_expiry < CURRENT_DATE THEN 'Expired Registration'
            WHEN v.insurance_expiry < CURRENT_DATE THEN 'Expired Insurance'
            WHEN v.inspection_expiry < CURRENT_DATE THEN 'Expired Inspection'
            ELSE 'Compliant'
        END as compliance_status,
        v.is_blacklisted,
        v.violation_count,
        v.unpaid_violations,
        v.unpaid_amount
    FROM vehicles v
    WHERE v.status = 'active';
    """)
    
    # View for vehicle summary
    op.execute("""
    CREATE OR REPLACE VIEW v_vehicle_summary AS
    SELECT 
        v.id,
        v.license_plate,
        v.vehicle_type,
        vm.name as make,
        vmd.name as model,
        v.year,
        v.color,
        COUNT(DISTINCT ps.id) as total_sessions,
        COALESCE(SUM(ps.total_amount), 0) as total_spent,
        MAX(ps.start_time) as last_parking,
        COUNT(DISTINCT vv.id) as total_violations,
        COALESCE(SUM(vv.fine_amount), 0) as total_fines,
        COUNT(DISTINCT va.id) as active_alerts
    FROM vehicles v
    LEFT JOIN vehicle_makes vm ON v.make_id = vm.id
    LEFT JOIN vehicle_models vmd ON v.model_id = vmd.id
    LEFT JOIN parking_sessions ps ON v.id = ps.vehicle_id
    LEFT JOIN vehicle_violations vv ON v.id = vv.vehicle_id AND vv.paid = false
    LEFT JOIN vehicle_alerts va ON v.id = va.vehicle_id AND va.is_active = true
    GROUP BY v.id, vm.name, vmd.name;
    """)
    
    # Create materialized view for vehicle analytics
    op.execute("""
    CREATE MATERIALIZED VIEW mv_vehicle_analytics AS
    SELECT 
        DATE_TRUNC('month', v.created_at) as month,
        v.vehicle_type,
        COUNT(*) as total_vehicles,
        COUNT(CASE WHEN v.status = 'active' THEN 1 END) as active_vehicles,
        COUNT(CASE WHEN v.is_blacklisted THEN 1 END) as blacklisted,
        COUNT(CASE WHEN v.is_stolen THEN 1 END) as stolen,
        AVG(EXTRACT(YEAR FROM AGE(CURRENT_DATE, MAKE_DATE(v.year, 1, 1)))) as avg_vehicle_age,
        COUNT(DISTINCT v.user_id) as unique_owners,
        MODE() WITHIN GROUP (ORDER BY vm.name) as most_common_make,
        MODE() WITHIN GROUP (ORDER BY v.color) as most_common_color,
        SUM(v.violation_count) as total_violations,
        SUM(v.unpaid_amount) as total_unpaid_fines
    FROM vehicles v
    LEFT JOIN vehicle_makes vm ON v.make_id = vm.id
    WHERE v.created_at >= CURRENT_DATE - INTERVAL '2 years'
    GROUP BY DATE_TRUNC('month', v.created_at), v.vehicle_type
    ORDER BY month DESC;
    """)
    
    # Create index on materialized view
    op.create_index('idx_mv_vehicle_month', 'mv_vehicle_analytics', ['month'])
    
    # Insert reference data
    logger.info("Inserting vehicle reference data")
    
    # Insert vehicle makes
    makes = [
        ('Toyota', 'Japan', 1937),
        ('Honda', 'Japan', 1948),
        ('Ford', 'USA', 1903),
        ('Chevrolet', 'USA', 1911),
        ('BMW', 'Germany', 1916),
        ('Mercedes-Benz', 'Germany', 1926),
        ('Audi', 'Germany', 1909),
        ('Volkswagen', 'Germany', 1937),
        ('Hyundai', 'South Korea', 1967),
        ('Kia', 'South Korea', 1944),
        ('Nissan', 'Japan', 1933),
        ('Mazda', 'Japan', 1920),
        ('Subaru', 'Japan', 1953),
        ('Lexus', 'Japan', 1989),
        ('Tesla', 'USA', 2003),
    ]
    
    for make_name, country, year in makes:
        op.execute(f"""
        INSERT INTO {VEHICLE_MAKES_TABLE} (
            id, name, display_name, country, founded_year, is_popular, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), '{make_name.lower()}', '{make_name}', '{country}', {year}, 
            {make_name in ['Toyota', 'Honda', 'Ford']}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        );
        """)
    
    # Insert vehicle types
    vehicle_types = [
        ('car', 'Car', 'passenger', 150, 180, 450, 1500, False, None, 24, 1.0),
        ('suv', 'SUV', 'passenger', 170, 200, 500, 2000, False, None, 24, 1.2),
        ('truck', 'Truck', 'commercial', 200, 220, 600, 3500, True, ARRAY['truck'], 12, 1.5),
        ('motorcycle', 'Motorcycle', 'motorcycle', 120, 80, 250, 300, True, ARRAY['motorcycle'], 24, 0.6),
        ('ev', 'Electric Vehicle', 'passenger', 150, 180, 450, 1800, True, ARRAY['electric'], 24, 1.1),
        ('van', 'Van', 'commercial', 190, 210, 550, 2500, True, ARRAY['van'], 12, 1.3),
    ]
    
    for vt in vehicle_types:
        op.execute(f"""
        INSERT INTO {VEHICLE_TYPES_TABLE} (
            id, name, display_name, category, default_height_cm, default_width_cm,
            default_length_cm, default_weight_kg, requires_special_spot,
            special_spot_types, max_parking_duration_hours, rate_multiplier,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(), '{vt[0]}', '{vt[1]}', '{vt[2]}', {vt[3]}, {vt[4]},
            {vt[5]}, {vt[6]}, {vt[7]}, '{vt[8]}'::text[] if vt[8] else NULL,
            {vt[9]}, {vt[10]}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        );
        """)
    
    # Insert system tags
    tags = [
        ('vip', 'status', 'VIP Customer', 'gold', 'star'),
        ('frequent', 'behavior', 'Frequent Parker', 'green', 'clock'),
        ('handicap', 'access', 'Handicap Access', 'blue', 'wheelchair'),
        ('ev', 'vehicle', 'Electric Vehicle', 'green', 'bolt'),
        ('commercial', 'vehicle', 'Commercial Vehicle', 'orange', 'truck'),
        ('government', 'status', 'Government Vehicle', 'purple', 'building'),
        ('staff', 'status', 'Staff Vehicle', 'blue', 'user'),
        ('blacklisted', 'status', 'Blacklisted', 'red', 'ban'),
    ]
    
    for tag_name, category, desc, color, icon in tags:
        op.execute(f"""
        INSERT INTO {VEHICLE_TAGS_TABLE} (
            id, name, category, description, color, icon, is_system, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), '{tag_name}', '{category}', '{desc}', '{color}', '{icon}',
            true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        );
        """)
    
    # Insert sample vehicles for admin user
    logger.info("Inserting sample vehicles")
    
    # Get admin user ID
    admin_result = op.get_bind().execute("SELECT id FROM users WHERE username = 'admin'").first()
    if admin_result:
        admin_id = admin_result[0]
        
        # Get make and model IDs
        toyota_id = op.get_bind().execute(
            f"SELECT id FROM {VEHICLE_MAKES_TABLE} WHERE name = 'toyota'"
        ).scalar()
        
        honda_id = op.get_bind().execute(
            f"SELECT id FROM {VEHICLE_MAKES_TABLE} WHERE name = 'honda'"
        ).scalar()
        
        # Insert sample vehicles
        sample_vehicles = [
            {
                'license_plate': 'ABC123',
                'state': 'CA',
                'make_id': toyota_id,
                'vehicle_type': 'car',
                'year': 2022,
                'color': 'Silver',
                'vin': '1HGCM82633A123456',
            },
            {
                'license_plate': 'XYZ789',
                'state': 'NY',
                'make_id': honda_id,
                'vehicle_type': 'suv',
                'year': 2023,
                'color': 'Blue',
                'vin': '2HGFG12869H123456',
            }
        ]
        
        for vehicle in sample_vehicles:
            vehicle_id = uuid.uuid4()
            op.execute(f"""
            INSERT INTO {VEHICLES_TABLE} (
                id, user_id, license_plate, license_plate_state, make_id,
                vehicle_type, year, color, vin, status, created_at, updated_at
            ) VALUES (
                '{vehicle_id}',
                '{admin_id}',
                '{vehicle["license_plate"]}',
                '{vehicle["state"]}',
                '{vehicle["make_id"]}',
                '{vehicle["vehicle_type"]}',
                {vehicle["year"]},
                '{vehicle["color"]}',
                '{vehicle["vin"]}',
                'active',
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            );
            """)
            
            # Add vehicle preferences
            op.execute(f"""
            INSERT INTO {VEHICLE_PREFERENCES_TABLE} (
                id, vehicle_id, auto_pay, notify_on_entry, notify_on_exit,
                reminder_minutes, created_at, updated_at
            ) VALUES (
                gen_random_uuid(),
                '{vehicle_id}',
                true,
                true,
                true,
                ARRAY[15, 30, 60],
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            );
            """)
    
    # Create partitions for high-volume tables
    logger.info("Creating partitions for vehicle tables")
    
    # Create partitions for access history (monthly for next 12 months)
    for i in range(12):
        month_date = datetime.now().replace(day=1) + timedelta(days=30*i)
        month_str = month_date.strftime('%Y_%m')
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS vehicle_access_history_{month_str} 
        PARTITION OF vehicle_access_history
        FOR VALUES FROM ('{month_date.strftime('%Y-%m-%d')}') 
        TO ('{next_month.strftime('%Y-%m-%d')}');
        """)
        
        # Create partition for location history
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS vehicle_location_history_{month_str} 
        PARTITION OF vehicle_location_history
        FOR VALUES FROM ('{month_date.strftime('%Y-%m-%d')}') 
        TO ('{next_month.strftime('%Y-%m-%d')}');
        """)
    
    # Grant permissions
    if op.get_context().dialect.name == 'postgresql':
        op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;")
        op.execute("GRANT INSERT, UPDATE, DELETE ON vehicles, vehicle_registrations, vehicle_insurance TO app_user;")
        op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;")
    
    logger.info(f"Migration {revision} completed successfully")


def downgrade() -> None:
    """
    Downgrade migration - removes vehicle management system
    """
    logger.info(f"Starting downgrade of migration {revision}")
    
    # Drop triggers first
    logger.info("Dropping triggers")
    triggers_to_drop = [
        'generate_vehicle_number_trigger',
        'generate_violation_number_trigger',
        'update_vehicle_statistics_trigger',
        'check_vehicle_blacklist_trigger'
    ]
    for trigger in triggers_to_drop:
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON vehicles CASCADE;")
    
    # Drop functions
    logger.info("Dropping functions")
    functions_to_drop = [
        'generate_vehicle_number()',
        'generate_violation_number()',
        'update_vehicle_statistics()',
        'check_vehicle_blacklist()'
    ]
    for func in functions_to_drop:
        op.execute(f"DROP FUNCTION IF EXISTS {func} CASCADE;")
    
    # Drop views and materialized views
    logger.info("Dropping views")
    op.execute("DROP VIEW IF EXISTS v_active_vehicles CASCADE;")
    op.execute("DROP VIEW IF EXISTS v_vehicle_compliance CASCADE;")
    op.execute("DROP VIEW IF EXISTS v_vehicle_summary CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_vehicle_analytics CASCADE;")
    
    # Drop tables in reverse order
    tables_to_drop = [
        VEHICLE_WASH_HISTORY_TABLE,
        VEHICLE_FUEL_HISTORY_TABLE,
        VEHICLE_LOCATION_HISTORY_TABLE,
        VEHICLE_DEVICES_TABLE,
        VEHICLE_PREFERENCES_TABLE,
        VEHICLE_ALERTS_TABLE,
        VEHICLE_BLACKLIST_TABLE,
        VEHICLE_VIOLATIONS_TABLE,
        VEHICLE_ACCESS_HISTORY_TABLE,
        VEHICLE_OWNERSHIP_HISTORY_TABLE,
        VEHICLE_TAG_ASSIGNMENTS_TABLE,
        VEHICLE_TAGS_TABLE,
        VEHICLE_DOCUMENTS_TABLE,
        VEHICLE_IMAGES_TABLE,
        VEHICLE_MAINTENANCE_TABLE,
        VEHICLE_INSPECTIONS_TABLE,
        VEHICLE_INSURANCE_TABLE,
        VEHICLE_REGISTRATIONS_TABLE,
        VEHICLES_TABLE,
        VEHICLE_MODELS_TABLE,
        VEHICLE_MAKES_TABLE,
        VEHICLE_TYPES_TABLE,
    ]
    
    for table in tables_to_drop:
        logger.info(f"Dropping {table} table")
        op.drop_table(table)
    
    # Drop ENUM types
    if op.get_context().dialect.name == 'postgresql':
        enums_to_drop = [
            'vehicle_status', 'vehicle_type', 'vehicle_class',
            'fuel_type', 'transmission_type', 'drive_type',
            'registration_status', 'insurance_status', 'inspection_status',
            'violation_type', 'violation_severity', 'alert_type',
            'alert_priority', 'access_method', 'ownership_type'
        ]
        for enum in enums_to_drop:
            logger.info(f"Dropping {enum} enum")
            op.execute(f"DROP TYPE IF EXISTS {enum} CASCADE;")
    
    # Drop partitions
    logger.info("Dropping partitions")
    for i in range(12):
        month_date = datetime.now().replace(day=1) + timedelta(days=30*i)
        month_str = month_date.strftime('%Y_%m')
        op.execute(f"DROP TABLE IF EXISTS vehicle_access_history_{month_str} CASCADE;")
        op.execute(f"DROP TABLE IF EXISTS vehicle_location_history_{month_str} CASCADE;")
    
    logger.info(f"Downgrade of migration {revision} completed successfully")


def validate_vehicle_data() -> dict:
    """
    Validate vehicle data quality after migration
    """
    logger.info("Validating vehicle data quality")
    
    connection = op.get_bind()
    results = {}
    
    # Check for duplicate license plates
    result = connection.execute("""
        SELECT license_plate, license_plate_state, COUNT(*)
        FROM vehicles
        WHERE deleted_at IS NULL
        GROUP BY license_plate, license_plate_state
        HAVING COUNT(*) > 1
    """)
    results['duplicate_license_plates'] = result.rowcount
    
    # Check for vehicles without users
    result = connection.execute("""
        SELECT COUNT(*)
        FROM vehicles v
        LEFT JOIN users u ON v.user_id = u.id
        WHERE u.id IS NULL AND v.deleted_at IS NULL
    """)
    results['vehicles_without_users'] = result.scalar()
    
    # Check for expired registrations
    result = connection.execute("""
        SELECT COUNT(*)
        FROM vehicles
        WHERE registration_expiry < CURRENT_DATE
            AND status = 'active'
            AND deleted_at IS NULL
    """)
    results['expired_registrations'] = result.scalar()
    
    # Check for expired insurance
    result = connection.execute("""
        SELECT COUNT(*)
        FROM vehicles
        WHERE insurance_expiry < CURRENT_DATE
            AND status = 'active'
            AND deleted_at IS NULL
    """)
    results['expired_insurance'] = result.scalar()
    
    # Check for vehicles with violations but not flagged
    result = connection.execute("""
        SELECT COUNT(DISTINCT vehicle_id)
        FROM vehicle_violations vv
        LEFT JOIN vehicles v ON vv.vehicle_id = v.id
        WHERE vv.paid = false
            AND (v.is_blacklisted = false OR v.is_blacklisted IS NULL)
    """)
    results['vehicles_with_unpaid_violations_not_blacklisted'] = result.scalar()
    
    logger.info(f"Validation results: {results}")
    return results


def post_upgrade_hook():
    """Hook to run after successful upgrade"""
    logger.info("Running post-upgrade hooks for vehicles migration")
    
    # Validate the migration
    validation_results = validate_vehicle_data()
    
    # Refresh materialized view
    op.execute("REFRESH MATERIALIZED VIEW mv_vehicle_analytics;")
    
    # Log any issues
    for key, value in validation_results.items():
        if value > 0:
            logger.warning(f"Validation issue - {key}: {value}")
    
    # Log summary statistics
    connection = op.get_bind()
    stats = connection.execute("""
        SELECT 
            COUNT(*) as total_vehicles,
            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_vehicles,
            COUNT(CASE WHEN is_blacklisted THEN 1 END) as blacklisted,
            COUNT(CASE WHEN is_stolen THEN 1 END) as stolen,
            COUNT(DISTINCT user_id) as unique_owners
        FROM vehicles
        WHERE deleted_at IS NULL
    """).first()
    
    if stats:
        logger.info(f"Vehicle Summary: {stats.total_vehicles} total vehicles, "
                   f"{stats.active_vehicles} active, {stats.blacklisted} blacklisted, "
                   f"{stats.unique_owners} unique owners")
    
    logger.info("Vehicles system migration completed successfully")


# Register the post-upgrade hook
if hasattr(op, 'register_post_upgrade_hook'):
    op.register_post_upgrade_hook(post_upgrade_hook)


# Add table comments
def add_table_comments():
    """Add detailed comments to tables for documentation"""
    op.execute(f"""
    COMMENT ON TABLE {VEHICLES_TABLE} IS 'Core vehicles table with comprehensive vehicle information including identification, characteristics, compliance status, and usage statistics.';
    COMMENT ON TABLE {VEHICLE_MAKES_TABLE} IS 'Reference table for vehicle manufacturers with metadata and popularity flags.';
    COMMENT ON TABLE {VEHICLE_MODELS_TABLE} IS 'Reference table for vehicle models linked to makes with detailed specifications.';
    COMMENT ON TABLE {VEHICLE_TYPES_TABLE} IS 'Vehicle type classifications with physical characteristics and parking requirements.';
    COMMENT ON TABLE {VEHICLE_REGISTRATIONS_TABLE} IS 'Vehicle registration history with jurisdictional details and document storage.';
    COMMENT ON TABLE {VEHICLE_INSURANCE_TABLE} IS 'Insurance policy details with coverage information and verification status.';
    COMMENT ON TABLE {VEHICLE_INSPECTIONS_TABLE} IS 'Inspection records including safety and emissions testing results.';
    COMMENT ON TABLE {VEHICLE_MAINTENANCE_TABLE} IS 'Maintenance history with costs, parts, and service records.';
    COMMENT ON TABLE {VEHICLE_IMAGES_TABLE} IS 'Vehicle images for identification and verification.';
    COMMENT ON TABLE {VEHICLE_DOCUMENTS_TABLE} IS 'Document storage for titles, registrations, and insurance proofs.';
    COMMENT ON TABLE {VEHICLE_TAGS_TABLE} IS 'Custom tagging system for vehicle categorization.';
    COMMENT ON TABLE {VEHICLE_TAG_ASSIGNMENTS_TABLE} IS 'Many-to-many relationship between vehicles and tags.';
    COMMENT ON TABLE {VEHICLE_OWNERSHIP_HISTORY_TABLE} IS 'Track ownership changes and transfer history.';
    COMMENT ON TABLE {VEHICLE_ACCESS_HISTORY_TABLE} IS 'Gate entry/exit attempts and access decisions.';
    COMMENT ON TABLE {VEHICLE_VIOLATIONS_TABLE} IS 'Parking violations with fine tracking and dispute management.';
    COMMENT ON TABLE {VEHICLE_BLACKLIST_TABLE} IS 'Blacklisted vehicles with reasons and expiration.';
    COMMENT ON TABLE {VEHICLE_ALERTS_TABLE} IS 'Active alerts including stolen vehicle notifications.';
    COMMENT ON TABLE {VEHICLE_PREFERENCES_TABLE} IS 'User preferences per vehicle for automated features.';
    COMMENT ON TABLE {VEHICLE_DEVICES_TABLE} IS 'IoT devices installed in vehicles for tracking.';
    COMMENT ON TABLE {VEHICLE_LOCATION_HISTORY_TABLE} IS 'Historical GPS location data for tracking.';
    COMMENT ON TABLE {VEHICLE_FUEL_HISTORY_TABLE} IS 'Fuel and charging records with efficiency calculations.';
    COMMENT ON TABLE {VEHICLE_WASH_HISTORY_TABLE} IS 'Wash and detailing service history.';
    """)