# parking-management/data/migrations/versions/2b3c4d5e6f7g_add_parking_spots.py

"""Add parking spots and related tables

Revision ID: 2b3c4d5e6f7g
Revises: 1a2b3c4d5e6f
Create Date: 2024-01-20 14:30:00.123456

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
revision: str = '2b3c4d5e6f7g'
down_revision: Union[str, None] = '1a2b3c4d5e6f'  # Depends on users table
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define table names
PARKING_ZONES_TABLE = 'parking_zones'
PARKING_SPOTS_TABLE = 'parking_spots'
PARKING_RATES_TABLE = 'parking_rates'
PARKING_SESSIONS_TABLE = 'parking_sessions'
PARKING_RESERVATIONS_TABLE = 'parking_reservations'
SPOT_MAINTENANCE_TABLE = 'spot_maintenance'
SPOT_SENSORS_TABLE = 'spot_sensors'
SPOT_OCCUPANCY_HISTORY_TABLE = 'spot_occupancy_history'
PARKING_RATE_HISTORY_TABLE = 'parking_rate_history'

# Define ENUM types for PostgreSQL
spot_type_enum = sa.Enum(
    'standard', 'compact', 'handicapped', 'electric', 'motorcycle', 
    'bus', 'truck', 'vip', 'staff', 'visitor', 
    name='spot_type'
)
spot_status_enum = sa.Enum(
    'available', 'occupied', 'reserved', 'maintenance', 
    'out_of_service', 'blocked', 
    name='spot_status'
)
zone_type_enum = sa.Enum(
    'indoor', 'outdoor', 'covered', 'rooftop', 'underground',
    name='zone_type'
)
rate_type_enum = sa.Enum(
    'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'event',
    name='rate_type'
)
vehicle_type_enum = sa.Enum(
    'car', 'motorcycle', 'truck', 'bus', 'van', 'ev', 'handicapped',
    name='vehicle_type'
)
session_status_enum = sa.Enum(
    'active', 'completed', 'cancelled', 'extended', 'expired',
    name='session_status'
)
reservation_status_enum = sa.Enum(
    'pending', 'confirmed', 'checked_in', 'checked_out', 
    'cancelled', 'no_show', 'expired',
    name='reservation_status'
)
maintenance_type_enum = sa.Enum(
    'cleaning', 'repair', 'inspection', 'upgrade', 'emergency',
    name='maintenance_type'
)
maintenance_status_enum = sa.Enum(
    'scheduled', 'in_progress', 'completed', 'cancelled', 'delayed',
    name='maintenance_status'
)
sensor_type_enum = sa.Enum(
    'ultrasonic', 'camera', 'magnetic', 'laser', 'radar',
    name='sensor_type'
)
sensor_status_enum = sa.Enum(
    'active', 'inactive', 'faulty', 'calibrating', 'offline',
    name='sensor_status'
)


def upgrade() -> None:
    """
    Upgrade migration - creates parking spots and related tables
    """
    logger.info(f"Starting migration {revision}: Add parking spots")
    
    # Create ENUM types first (PostgreSQL specific)
    if op.get_context().dialect.name == 'postgresql':
        for enum in [spot_type_enum, spot_status_enum, zone_type_enum, rate_type_enum,
                     vehicle_type_enum, session_status_enum, reservation_status_enum,
                     maintenance_type_enum, maintenance_status_enum, sensor_type_enum,
                     sensor_status_enum]:
            enum.create(op.get_bind(), checkfirst=True)
        logger.info("Created ENUM types")
    
    # Create parking zones table
    logger.info("Creating parking zones table")
    op.create_table(
        PARKING_ZONES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(20), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('zone_type', sa.String(20), nullable=False, server_default='outdoor'),
        sa.Column('floor', sa.Integer),
        sa.Column('section', sa.String(10)),
        sa.Column('total_spots', sa.Integer, nullable=False, server_default='0'),
        sa.Column('available_spots', sa.Integer, nullable=False, server_default='0'),
        sa.Column('reserved_spots', sa.Integer, nullable=False, server_default='0'),
        sa.Column('occupied_spots', sa.Integer, nullable=False, server_default='0'),
        sa.Column('maintenance_spots', sa.Integer, nullable=False, server_default='0'),
        sa.Column('latitude', sa.Numeric(10, 8)),
        sa.Column('longitude', sa.Numeric(11, 8)),
        sa.Column('address', sa.String(255)),
        sa.Column('entrance_coordinates', postgresql.JSONB),
        sa.Column('exit_coordinates', postgresql.JSONB),
        sa.Column('opening_time', sa.Time),
        sa.Column('closing_time', sa.Time),
        sa.Column('is_24_hours', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('has_ev_charging', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('has_car_wash', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('has_security', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('has_roof', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('max_height_cm', sa.Integer),
        sa.Column('max_width_cm', sa.Integer),
        sa.Column('max_length_cm', sa.Integer),
        sa.Column('max_weight_kg', sa.Integer),
        sa.Column('image_url', sa.String(500)),
        sa.Column('floor_plan_url', sa.String(500)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_zones_code', 'code', unique=True),
        sa.Index('ix_zones_name', 'name'),
        sa.Index('ix_zones_type', 'zone_type'),
        sa.Index('ix_zones_location', 'latitude', 'longitude'),
        sa.Index('ix_zones_is_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Parking zones/areas within the parking facility'),
    )
    
    # Create parking spots table
    logger.info("Creating parking spots table")
    op.create_table(
        PARKING_SPOTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('spot_number', sa.String(20), nullable=False),
        sa.Column('level', sa.String(10)),
        sa.Column('row', sa.String(10)),
        sa.Column('column', sa.String(10)),
        sa.Column('spot_type', sa.String(20), nullable=False, server_default='standard'),
        sa.Column('status', sa.String(20), nullable=False, server_default='available'),
        sa.Column('vehicle_type', sa.String(20)),
        sa.Column('current_vehicle_id', postgresql.UUID(as_uuid=True)),
        sa.Column('current_session_id', postgresql.UUID(as_uuid=True)),
        sa.Column('current_reservation_id', postgresql.UUID(as_uuid=True)),
        sa.Column('coordinates_x', sa.Float),
        sa.Column('coordinates_y', sa.Float),
        sa.Column('coordinates_z', sa.Float),
        sa.Column('width_cm', sa.Integer),
        sa.Column('length_cm', sa.Integer),
        sa.Column('height_cm', sa.Integer),
        sa.Column('max_weight_kg', sa.Integer),
        sa.Column('has_ev_charger', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('ev_charger_type', sa.String(50)),
        sa.Column('ev_charger_power_kw', sa.Float),
        sa.Column('has_sensor', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('sensor_id', sa.String(100)),
        sa.Column('is_handicapped', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_covered', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_near_elevator', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_near_entrance', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('hourly_rate', sa.Numeric(10, 2)),
        sa.Column('daily_rate', sa.Numeric(10, 2)),
        sa.Column('monthly_rate', sa.Numeric(10, 2)),
        sa.Column('minimum_duration_minutes', sa.Integer, server_default='0'),
        sa.Column('maximum_duration_minutes', sa.Integer),
        sa.Column('last_occupied_at', sa.DateTime(timezone=True)),
        sa.Column('last_vacated_at', sa.DateTime(timezone=True)),
        sa.Column('occupancy_count_today', sa.Integer, server_default='0'),
        sa.Column('total_occupancy_count', sa.Integer, server_default='0'),
        sa.Column('image_url', sa.String(500)),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_spots_zone_spot', 'zone_id', 'spot_number', unique=True),
        sa.Index('ix_spots_status', 'status'),
        sa.Index('ix_spots_type', 'spot_type'),
        sa.Index('ix_spots_vehicle_type', 'vehicle_type'),
        sa.Index('ix_spots_current_vehicle', 'current_vehicle_id'),
        sa.Index('ix_spots_current_session', 'current_session_id'),
        sa.Index('ix_spots_sensor', 'sensor_id'),
        sa.Index('ix_spots_coordinates', 'coordinates_x', 'coordinates_y'),
        sa.Index('ix_spots_is_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['zone_id'], [f'{PARKING_ZONES_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Individual parking spots with their properties and current status'),
    )
    
    # Create parking rates table
    logger.info("Creating parking rates table")
    op.create_table(
        PARKING_RATES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True)),
        sa.Column('spot_type', sa.String(20)),
        sa.Column('vehicle_type', sa.String(20)),
        sa.Column('rate_type', sa.String(20), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('base_rate', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('unit', sa.String(20), nullable=False),  # hour, day, week, month, year
        sa.Column('min_units', sa.Integer, server_default='1'),
        ca.Column('max_units', sa.Integer),
        sa.Column('grace_period_minutes', sa.Integer, server_default='15'),
        sa.Column('has_maximum_cap', sa.Boolean, server_default='false'),
        sa.Column('maximum_cap_amount', sa.Numeric(10, 2)),
        sa.Column('maximum_cap_period', sa.String(20)),  # day, week, month
        sa.Column('has_weekend_rate', sa.Boolean, server_default='false'),
        sa.Column('weekend_rate', sa.Numeric(10, 2)),
        sa.Column('has_night_rate', sa.Boolean, server_default='false'),
        sa.Column('night_rate', sa.Numeric(10, 2)),
        sa.Column('night_start_time', sa.Time),
        sa.Column('night_end_time', sa.Time),
        sa.Column('has_holiday_rate', sa.Boolean, server_default='false'),
        sa.Column('holiday_rate', sa.Numeric(10, 2)),
        sa.Column('holiday_dates', postgresql.ARRAY(sa.Date)),
        sa.Column('requires_membership', sa.Boolean, server_default='false'),
        sa.Column('membership_types', postgresql.ARRAY(sa.String)),
        sa.Column('is_tax_inclusive', sa.Boolean, server_default='true'),
        sa.Column('tax_rate', sa.Numeric(5, 2)),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True)),
        sa.Column('priority', sa.Integer, server_default='0'),
        sa.Column('conditions', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_rates_zone_type', 'zone_id', 'spot_type'),
        sa.Index('ix_rates_vehicle_type', 'vehicle_type'),
        sa.Index('ix_rates_effective_date', 'effective_from', 'effective_to'),
        sa.Index('ix_rates_is_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['zone_id'], [f'{PARKING_ZONES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Parking rate configurations for different zones, spot types, and vehicles'),
    )
    
    # Create parking sessions table
    logger.info("Creating parking sessions table")
    op.create_table(
        PARKING_SESSIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('spot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True)),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True)),
        sa.Column('session_number', sa.String(50), nullable=False, unique=True),
        sa.Column('license_plate', sa.String(20)),
        sa.Column('vehicle_type', sa.String(20)),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True)),
        sa.Column('expected_end_time', sa.DateTime(timezone=True)),
        sa.Column('duration_minutes', sa.Integer),
        sa.Column('billed_duration_minutes', sa.Integer),
        sa.Column('grace_period_minutes', sa.Integer, server_default='15'),
        sa.Column('rate_id', postgresql.UUID(as_uuid=True)),
        sa.Column('rate_applied', sa.Numeric(10, 2)),
        sa.Column('base_amount', sa.Numeric(10, 2)),
        sa.Column('tax_amount', sa.Numeric(10, 2)),
        sa.Column('discount_amount', sa.Numeric(10, 2)),
        sa.Column('total_amount', sa.Numeric(10, 2)),
        sa.Column('currency', sa.String(3), server_default='USD'),
        sa.Column('payment_status', sa.String(20), server_default='pending'),
        sa.Column('payment_method', sa.String(50)),
        sa.Column('payment_id', sa.String(100)),
        sa.Column('ticket_number', sa.String(100)),
        sa.Column('qr_code', sa.Text),
        sa.Column('barcode', sa.String(255)),
        sa.Column('entry_gate', sa.String(50)),
        sa.Column('exit_gate', sa.String(50)),
        sa.Column('entry_image_url', sa.String(500)),
        sa.Column('exit_image_url', sa.String(500)),
        sa.Column('check_in_by', postgresql.UUID(as_uuid=True)),
        sa.Column('check_out_by', postgresql.UUID(as_uuid=True)),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_sessions_number', 'session_number', unique=True),
        sa.Index('ix_sessions_spot', 'spot_id'),
        sa.Index('ix_sessions_vehicle', 'vehicle_id'),
        sa.Index('ix_sessions_user', 'user_id'),
        sa.Index('ix_sessions_license_plate', 'license_plate'),
        sa.Index('ix_sessions_status', 'status'),
        sa.Index('ix_sessions_start_time', 'start_time'),
        sa.Index('ix_sessions_end_time', 'end_time'),
        sa.Index('ix_sessions_payment_status', 'payment_status'),
        sa.Index('ix_sessions_ticket', 'ticket_number'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['spot_id'], [f'{PARKING_SPOTS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reservation_id'], [f'{PARKING_RESERVATIONS_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rate_id'], [f'{PARKING_RATES_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['check_in_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['check_out_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Parking sessions tracking vehicle entries and exits'),
        
        # Partition by month
        postgresql_partition_by='RANGE (start_time)',
    )
    
    # Create parking reservations table
    logger.info("Creating parking reservations table")
    op.create_table(
        PARKING_RESERVATIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('spot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True)),
        sa.Column('reservation_number', sa.String(50), nullable=False, unique=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='confirmed'),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('check_in_time', sa.DateTime(timezone=True)),
        sa.Column('check_out_time', sa.DateTime(timezone=True)),
        sa.Column('duration_minutes', sa.Integer),
        sa.Column('license_plate', sa.String(20)),
        sa.Column('vehicle_type', sa.String(20)),
        sa.Column('customer_name', sa.String(200)),
        sa.Column('customer_email', sa.String(255)),
        sa.Column('customer_phone', sa.String(20)),
        sa.Column('rate_id', postgresql.UUID(as_uuid=True)),
        sa.Column('rate_applied', sa.Numeric(10, 2)),
        sa.Column('base_amount', sa.Numeric(10, 2)),
        sa.Column('tax_amount', sa.Numeric(10, 2)),
        sa.Column('discount_amount', sa.Numeric(10, 2)),
        sa.Column('total_amount', sa.Numeric(10, 2)),
        sa.Column('currency', sa.String(3), server_default='USD'),
        sa.Column('payment_status', sa.String(20), server_default='pending'),
        sa.Column('payment_method', sa.String(50)),
        sa.Column('payment_id', sa.String(100)),
        sa.Column('deposit_amount', sa.Numeric(10, 2)),
        sa.Column('deposit_paid', sa.Boolean, server_default='false'),
        sa.Column('cancellation_reason', sa.Text),
        sa.Column('cancelled_at', sa.DateTime(timezone=True)),
        sa.Column('cancelled_by', postgresql.UUID(as_uuid=True)),
        sa.Column('reminder_sent', sa.Boolean, server_default='false'),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True)),
        sa.Column('special_requests', sa.Text),
        sa.Column('qr_code', sa.Text),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_reservations_number', 'reservation_number', unique=True),
        sa.Index('ix_reservations_spot', 'spot_id'),
        sa.Index('ix_reservations_user', 'user_id'),
        sa.Index('ix_reservations_status', 'status'),
        sa.Index('ix_reservations_time_range', 'start_time', 'end_time'),
        sa.Index('ix_reservations_license_plate', 'license_plate'),
        sa.Index('ix_reservations_customer_email', 'customer_email'),
        sa.Index('ix_reservations_payment_status', 'payment_status'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['spot_id'], [f'{PARKING_SPOTS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rate_id'], [f'{PARKING_RATES_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['cancelled_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Parking spot reservations made by users'),
    )
    
    # Create spot maintenance table
    logger.info("Creating spot maintenance table")
    op.create_table(
        SPOT_MAINTENANCE_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('spot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('maintenance_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='scheduled'),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('priority', sa.String(20), server_default='medium'),
        sa.Column('scheduled_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual_start', sa.DateTime(timezone=True)),
        sa.Column('actual_end', sa.DateTime(timezone=True)),
        sa.Column('estimated_duration_minutes', sa.Integer),
        sa.Column('actual_duration_minutes', sa.Integer),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True)),
        sa.Column('vendor_name', sa.String(200)),
        sa.Column('vendor_contact', sa.String(100)),
        sa.Column('cost_estimate', sa.Numeric(10, 2)),
        sa.Column('actual_cost', sa.Numeric(10, 2)),
        sa.Column('parts_used', postgresql.JSONB),
        sa.Column('notes', sa.Text),
        sa.Column('completion_notes', sa.Text),
        sa.Column('follow_up_required', sa.Boolean, server_default='false'),
        sa.Column('follow_up_date', sa.DateTime(timezone=True)),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('completed_by', postgresql.UUID(as_uuid=True)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_maintenance_spot', 'spot_id'),
        sa.Index('ix_maintenance_status', 'status'),
        sa.Index('ix_maintenance_type', 'maintenance_type'),
        sa.Index('ix_maintenance_schedule', 'scheduled_start', 'scheduled_end'),
        sa.Index('ix_maintenance_assigned', 'assigned_to'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['spot_id'], [f'{PARKING_SPOTS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['completed_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Maintenance schedule and history for parking spots'),
    )
    
    # Create spot sensors table
    logger.info("Creating spot sensors table")
    op.create_table(
        SPOT_SENSORS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('spot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sensor_type', sa.String(50), nullable=False),
        sa.Column('sensor_model', sa.String(100)),
        sa.Column('manufacturer', sa.String(100)),
        sa.Column('serial_number', sa.String(100), unique=True),
        sa.Column('firmware_version', sa.String(50)),
        sa.Column('hardware_version', sa.String(50)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('mac_address', sa.String(17)),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('battery_level', sa.Integer),
        sa.Column('last_communication', sa.DateTime(timezone=True)),
        sa.Column('last_calibration', sa.DateTime(timezone=True)),
        sa.Column('reading_frequency_seconds', sa.Integer, server_default='5'),
        sa.Column('current_value', sa.Float),
        sa.Column('current_status', sa.String(20)),  # occupied, available, etc.
        sa.Column('accuracy_percent', sa.Float),
        sa.Column('temperature_celsius', sa.Float),
        sa.Column('error_count', sa.Integer, server_default='0'),
        sa.Column('last_error', sa.Text),
        sa.Column('last_error_time', sa.DateTime(timezone=True)),
        sa.Column('maintenance_due', sa.DateTime(timezone=True)),
        sa.Column('calibration_due', sa.DateTime(timezone=True)),
        sa.Column('configuration', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('installed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('installed_by', postgresql.UUID(as_uuid=True)),
        sa.Column('removed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_sensors_spot', 'spot_id'),
        sa.Index('ix_sensors_serial', 'serial_number', unique=True),
        sa.Index('ix_sensors_mac', 'mac_address'),
        sa.Index('ix_sensors_status', 'status'),
        sa.Index('ix_sensors_type', 'sensor_type'),
        sa.Index('ix_sensors_last_comm', 'last_communication'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['spot_id'], [f'{PARKING_SPOTS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['installed_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('IoT sensors monitoring parking spot occupancy'),
    )
    
    # Create spot occupancy history table
    logger.info("Creating spot occupancy history table")
    op.create_table(
        SPOT_OCCUPANCY_HISTORY_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('spot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True)),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True)),
        sa.Column('license_plate', sa.String(20)),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True)),
        sa.Column('duration_minutes', sa.Integer),
        sa.Column('sensor_id', postgresql.UUID(as_uuid=True)),
        sa.Column('sensor_value', sa.Float),
        sa.Column('confidence', sa.Float),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_occupancy_history_spot', 'spot_id'),
        sa.Index('ix_occupancy_history_session', 'session_id'),
        sa.Index('ix_occupancy_history_time_range', 'start_time', 'end_time'),
        sa.Index('ix_occupancy_history_vehicle', 'vehicle_id'),
        sa.Index('ix_occupancy_history_license', 'license_plate'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['spot_id'], [f'{PARKING_SPOTS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], [f'{PARKING_SESSIONS_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sensor_id'], [f'{SPOT_SENSORS_TABLE}.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Historical record of spot occupancy over time'),
        
        # Partition by month
        postgresql_partition_by='RANGE (start_time)',
    )
    
    # Create parking rate history table
    logger.info("Creating parking rate history table")
    op.create_table(
        PARKING_RATE_HISTORY_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('rate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(20), nullable=False),  # create, update, delete
        sa.Column('old_values', postgresql.JSONB),
        sa.Column('new_values', postgresql.JSONB),
        sa.Column('changed_by', postgresql.UUID(as_uuid=True)),
        sa.Column('reason', sa.String(255)),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_rate_history_rate', 'rate_id'),
        sa.Index('ix_rate_history_date', 'effective_date'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['rate_id'], [f'{PARKING_RATES_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('History of changes to parking rates'),
    )
    
    # Create triggers and functions
    logger.info("Creating database functions and triggers")
    
    # Function to update spot counts in zone
    op.execute("""
    CREATE OR REPLACE FUNCTION update_zone_counts()
    RETURNS TRIGGER AS $$
    DECLARE
        zone_record RECORD;
    BEGIN
        -- Get the zone for this spot
        SELECT * INTO zone_record FROM parking_zones WHERE id = NEW.zone_id;
        
        -- Update zone counts
        WITH spot_counts AS (
            SELECT 
                zone_id,
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'available' THEN 1 END) as available,
                COUNT(CASE WHEN status = 'occupied' THEN 1 END) as occupied,
                COUNT(CASE WHEN status = 'reserved' THEN 1 END) as reserved,
                COUNT(CASE WHEN status = 'maintenance' THEN 1 END) as maintenance
            FROM parking_spots
            WHERE zone_id = NEW.zone_id AND is_active = true
            GROUP BY zone_id
        )
        UPDATE parking_zones z
        SET 
            total_spots = COALESCE(s.total, 0),
            available_spots = COALESCE(s.available, 0),
            occupied_spots = COALESCE(s.occupied, 0),
            reserved_spots = COALESCE(s.reserved, 0),
            maintenance_spots = COALESCE(s.maintenance, 0),
            updated_at = CURRENT_TIMESTAMP
        FROM spot_counts s
        WHERE z.id = s.zone_id;
        
        IF TG_OP = 'DELETE' THEN
            -- Handle delete case
            WITH spot_counts AS (
                SELECT 
                    zone_id,
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'available' THEN 1 END) as available,
                    COUNT(CASE WHEN status = 'occupied' THEN 1 END) as occupied,
                    COUNT(CASE WHEN status = 'reserved' THEN 1 END) as reserved,
                    COUNT(CASE WHEN status = 'maintenance' THEN 1 END) as maintenance
                FROM parking_spots
                WHERE zone_id = OLD.zone_id AND is_active = true
                GROUP BY zone_id
            )
            UPDATE parking_zones z
            SET 
                total_spots = COALESCE(s.total, 0),
                available_spots = COALESCE(s.available, 0),
                occupied_spots = COALESCE(s.occupied, 0),
                reserved_spots = COALESCE(s.reserved, 0),
                maintenance_spots = COALESCE(s.maintenance, 0),
                updated_at = CURRENT_TIMESTAMP
            FROM spot_counts s
            WHERE z.id = s.zone_id;
        END IF;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for updating zone counts
    op.execute("""
    CREATE TRIGGER update_zone_counts_trigger
        AFTER INSERT OR UPDATE OR DELETE ON parking_spots
        FOR EACH ROW
        EXECUTE FUNCTION update_zone_counts();
    """)
    
    # Function to record occupancy history
    op.execute("""
    CREATE OR REPLACE FUNCTION record_occupancy_history()
    RETURNS TRIGGER AS $$
    BEGIN
        IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND OLD.status != NEW.status) THEN
            IF NEW.status = 'occupied' THEN
                -- End previous occupancy if exists
                UPDATE spot_occupancy_history
                SET end_time = NEW.updated_at,
                    duration_minutes = EXTRACT(EPOCH FROM (NEW.updated_at - start_time)) / 60
                WHERE spot_id = NEW.id AND end_time IS NULL;
                
                -- Start new occupancy
                INSERT INTO spot_occupancy_history (
                    id, spot_id, status, start_time, vehicle_id, license_plate
                ) VALUES (
                    gen_random_uuid(), 
                    NEW.id, 
                    NEW.status, 
                    NEW.updated_at,
                    NEW.current_vehicle_id,
                    (SELECT license_plate FROM vehicles WHERE id = NEW.current_vehicle_id)
                );
            ELSIF NEW.status IN ('available', 'reserved', 'maintenance') AND 
                  (OLD.status = 'occupied' OR OLD.status IS NULL) THEN
                -- End current occupancy
                UPDATE spot_occupancy_history
                SET end_time = NEW.updated_at,
                    duration_minutes = EXTRACT(EPOCH FROM (NEW.updated_at - start_time)) / 60
                WHERE spot_id = NEW.id AND end_time IS NULL;
            END IF;
        END IF;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for occupancy history
    op.execute("""
    CREATE TRIGGER record_occupancy_history_trigger
        AFTER INSERT OR UPDATE OF status ON parking_spots
        FOR EACH ROW
        EXECUTE FUNCTION record_occupancy_history();
    """)
    
    # Function to check spot availability
    op.execute("""
    CREATE OR REPLACE FUNCTION check_spot_availability(
        p_zone_id UUID,
        p_spot_type VARCHAR,
        p_start_time TIMESTAMP,
        p_end_time TIMESTAMP
    ) RETURNS TABLE (
        spot_id UUID,
        spot_number VARCHAR,
        status VARCHAR
    ) AS $$
    BEGIN
        RETURN QUERY
        SELECT 
            ps.id,
            ps.spot_number,
            ps.status
        FROM parking_spots ps
        WHERE ps.zone_id = p_zone_id
            AND ps.spot_type = p_spot_type
            AND ps.is_active = true
            AND ps.status = 'available'
            AND NOT EXISTS (
                SELECT 1 
                FROM parking_reservations pr
                WHERE pr.spot_id = ps.id
                    AND pr.status IN ('confirmed', 'checked_in')
                    AND pr.start_time < p_end_time
                    AND pr.end_time > p_start_time
            )
        ORDER BY ps.spot_number;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create view for current occupancy status
    op.execute("""
    CREATE OR REPLACE VIEW v_current_occupancy AS
    SELECT 
        pz.name as zone_name,
        pz.code as zone_code,
        ps.spot_number,
        ps.spot_type,
        ps.status,
        ps.current_vehicle_id,
        v.license_plate,
        v.vehicle_type,
        ps.current_session_id,
        ps.current_reservation_id,
        ps.last_occupied_at,
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ps.last_occupied_at)) / 60 as minutes_occupied
    FROM parking_spots ps
    JOIN parking_zones pz ON ps.zone_id = pz.id
    LEFT JOIN vehicles v ON ps.current_vehicle_id = v.id
    WHERE ps.is_active = true
    ORDER BY pz.code, ps.spot_number;
    """)
    
    # Create materialized view for occupancy statistics
    op.execute("""
    CREATE MATERIALIZED VIEW mv_occupancy_stats AS
    SELECT 
        DATE_TRUNC('hour', start_time) as hour,
        COUNT(DISTINCT spot_id) as unique_spots_used,
        COUNT(*) as total_occupancies,
        AVG(duration_minutes) as avg_duration_minutes,
        SUM(duration_minutes) as total_minutes,
        COUNT(DISTINCT vehicle_id) as unique_vehicles,
        COUNT(DISTINCT license_plate) as unique_license_plates
    FROM spot_occupancy_history
    WHERE start_time >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY DATE_TRUNC('hour', start_time)
    ORDER BY hour DESC;
    """)
    
    # Create index on materialized view
    op.create_index('idx_mv_occupancy_stats_hour', 'mv_occupancy_stats', ['hour'])
    
    # Insert initial data
    logger.info("Inserting initial parking zones and spots")
    
    # Insert main parking zones
    zones = [
        {
            'id': uuid.uuid4(),
            'name': 'Ground Floor - A',
            'code': 'GFA',
            'zone_type': 'outdoor',
            'floor': 0,
            'section': 'A',
            'total_spots': 50,
            'has_ev_charging': True,
            'has_security': True,
            'opening_time': '00:00',
            'closing_time': '23:59',
            'is_24_hours': True
        },
        {
            'id': uuid.uuid4(),
            'name': 'Ground Floor - B',
            'code': 'GFB',
            'zone_type': 'outdoor',
            'floor': 0,
            'section': 'B',
            'total_spots': 50,
            'has_ev_charging': False,
            'has_security': True,
            'opening_time': '00:00',
            'closing_time': '23:59',
            'is_24_hours': True
        },
        {
            'id': uuid.uuid4(),
            'name': 'First Floor - Covered',
            'code': 'FFC',
            'zone_type': 'covered',
            'floor': 1,
            'section': 'C',
            'total_spots': 40,
            'has_ev_charging': True,
            'has_roof': True,
            'max_height_cm': 200,
            'opening_time': '06:00',
            'closing_time': '22:00',
            'is_24_hours': False
        },
        {
            'id': uuid.uuid4(),
            'name': 'VIP Section',
            'code': 'VIP',
            'zone_type': 'indoor',
            'floor': 2,
            'section': 'VIP',
            'total_spots': 20,
            'has_ev_charging': True,
            'has_security': True,
            'has_roof': True,
            'opening_time': '00:00',
            'closing_time': '23:59',
            'is_24_hours': True
        },
        {
            'id': uuid.uuid4(),
            'name': 'Motorcycle Parking',
            'code': 'MOTO',
            'zone_type': 'outdoor',
            'floor': 0,
            'section': 'M',
            'total_spots': 30,
            'has_roof': True,
            'max_width_cm': 100,
            'max_length_cm': 250,
            'opening_time': '00:00',
            'closing_time': '23:59',
            'is_24_hours': True
        }
    ]
    
    for zone in zones:
        op.execute(f"""
        INSERT INTO parking_zones (
            id, name, code, zone_type, floor, section, total_spots,
            has_ev_charging, has_security, has_roof, max_height_cm,
            max_width_cm, max_length_cm, opening_time, closing_time,
            is_24_hours, created_at, updated_at
        ) VALUES (
            '{zone["id"]}',
            '{zone["name"]}',
            '{zone["code"]}',
            '{zone["zone_type"]}',
            {zone.get("floor", 0)},
            '{zone.get("section", "")}',
            {zone["total_spots"]},
            {zone.get("has_ev_charging", False)},
            {zone.get("has_security", False)},
            {zone.get("has_roof", False)},
            {zone.get("max_height_cm", "NULL")},
            {zone.get("max_width_cm", "NULL")},
            {zone.get("max_length_cm", "NULL")},
            '{zone.get("opening_time", "00:00")}',
            '{zone.get("closing_time", "23:59")}',
            {zone.get("is_24_hours", True)},
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        );
        """)
        
        # Create parking spots for each zone
        for spot_num in range(1, zone['total_spots'] + 1):
            spot_id = uuid.uuid4()
            spot_number = f"{zone['code']}-{str(spot_num).zfill(3)}"
            
            # Determine spot type based on zone and position
            if zone['code'] == 'VIP':
                spot_type = 'vip'
            elif zone['code'] == 'MOTO':
                spot_type = 'motorcycle'
            elif spot_num % 10 == 0:  # Every 10th spot is handicapped
                spot_type = 'handicapped'
            elif spot_num % 5 == 0:  # Every 5th spot has EV charging
                spot_type = 'electric'
            else:
                spot_type = 'standard'
            
            op.execute(f"""
            INSERT INTO parking_spots (
                id, zone_id, spot_number, spot_type, status,
                has_ev_charger, is_handicapped, is_covered,
                coordinates_x, coordinates_y,
                width_cm, length_cm, height_cm,
                created_at, updated_at
            ) VALUES (
                '{spot_id}',
                '{zone["id"]}',
                '{spot_number}',
                '{spot_type}',
                'available',
                {spot_type == 'electric'},
                {spot_type == 'handicapped'},
                {zone['zone_type'] in ['covered', 'indoor']},
                {spot_num % 10},
                {spot_num // 10},
                250,
                500,
                {zone.get('max_height_cm', 300)},
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            );
            """)
    
    # Insert default parking rates
    logger.info("Inserting default parking rates")
    
    rates = [
        # Standard rates
        {
            'name': 'Standard Hourly',
            'rate_type': 'hourly',
            'base_rate': 5.00,
            'unit': 'hour',
            'max_units': 24,
            'grace_period_minutes': 15
        },
        {
            'name': 'Standard Daily',
            'rate_type': 'daily',
            'base_rate': 30.00,
            'unit': 'day',
            'max_units': 30,
            'grace_period_minutes': 30
        },
        {
            'name': 'Standard Monthly',
            'rate_type': 'monthly',
            'base_rate': 300.00,
            'unit': 'month',
            'max_units': 12,
            'grace_period_minutes': 60
        },
        # EV charging rates
        {
            'name': 'EV Charging Hourly',
            'rate_type': 'hourly',
            'base_rate': 7.50,
            'unit': 'hour',
            'spot_type': 'electric',
            'max_units': 24,
            'grace_period_minutes': 15
        },
        # Handicapped rates
        {
            'name': 'Handicapped Hourly',
            'rate_type': 'hourly',
            'base_rate': 3.00,
            'unit': 'hour',
            'spot_type': 'handicapped',
            'max_units': 24,
            'grace_period_minutes': 30
        },
        # VIP rates
        {
            'name': 'VIP Hourly',
            'rate_type': 'hourly',
            'base_rate': 10.00,
            'unit': 'hour',
            'spot_type': 'vip',
            'max_units': 24,
            'grace_period_minutes': 15
        },
        # Motorcycle rates
        {
            'name': 'Motorcycle Hourly',
            'rate_type': 'hourly',
            'base_rate': 2.50,
            'unit': 'hour',
            'spot_type': 'motorcycle',
            'max_units': 24,
            'grace_period_minutes': 15
        }
    ]
    
    for rate in rates:
        rate_id = uuid.uuid4()
        spot_type = rate.get('spot_type', 'standard')
        
        op.execute(f"""
        INSERT INTO parking_rates (
            id, name, rate_type, spot_type, base_rate, currency,
            unit, max_units, grace_period_minutes, effective_from,
            is_active, created_at, updated_at
        ) VALUES (
            '{rate_id}',
            '{rate["name"]}',
            '{rate["rate_type"]}',
            '{spot_type}',
            {rate["base_rate"]},
            'USD',
            '{rate["unit"]}',
            {rate.get("max_units", "NULL")},
            {rate["grace_period_minutes"]},
            CURRENT_TIMESTAMP,
            true,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        );
        """)
    
    # Create partitions for parking sessions (monthly for next 12 months)
    logger.info("Creating monthly partitions for parking sessions")
    for i in range(12):
        month_date = datetime.now().replace(day=1) + timedelta(days=30*i)
        month_str = month_date.strftime('%Y_%m')
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS parking_sessions_{month_str} 
        PARTITION OF parking_sessions
        FOR VALUES FROM ('{month_date.strftime('%Y-%m-%d')}') 
        TO ('{next_month.strftime('%Y-%m-%d')}');
        """)
    
    # Create partitions for occupancy history
    logger.info("Creating monthly partitions for occupancy history")
    for i in range(12):
        month_date = datetime.now().replace(day=1) + timedelta(days=30*i)
        month_str = month_date.strftime('%Y_%m')
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS spot_occupancy_history_{month_str} 
        PARTITION OF spot_occupancy_history
        FOR VALUES FROM ('{month_date.strftime('%Y-%m-%d')}') 
        TO ('{next_month.strftime('%Y-%m-%d')}');
        """)
    
    # Grant permissions
    if op.get_context().dialect.name == 'postgresql':
        op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;")
        op.execute("GRANT INSERT, UPDATE, DELETE ON parking_spots, parking_sessions, parking_reservations TO app_user;")
        op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;")
    
    logger.info(f"Migration {revision} completed successfully")


def downgrade() -> None:
    """
    Downgrade migration - removes parking spots and related tables
    """
    logger.info(f"Starting downgrade of migration {revision}")
    
    # Drop triggers first
    logger.info("Dropping triggers")
    op.execute("DROP TRIGGER IF EXISTS update_zone_counts_trigger ON parking_spots;")
    op.execute("DROP TRIGGER IF EXISTS record_occupancy_history_trigger ON parking_spots;")
    
    # Drop functions
    logger.info("Dropping functions")
    op.execute("DROP FUNCTION IF EXISTS update_zone_counts() CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS record_occupancy_history() CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS check_spot_availability(uuid, varchar, timestamp, timestamp) CASCADE;")
    
    # Drop views and materialized views
    logger.info("Dropping views")
    op.execute("DROP VIEW IF EXISTS v_current_occupancy CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_occupancy_stats CASCADE;")
    
    # Drop tables in reverse order
    tables_to_drop = [
        PARKING_RATE_HISTORY_TABLE,
        SPOT_OCCUPANCY_HISTORY_TABLE,
        SPOT_SENSORS_TABLE,
        SPOT_MAINTENANCE_TABLE,
        PARKING_RESERVATIONS_TABLE,
        PARKING_SESSIONS_TABLE,
        PARKING_RATES_TABLE,
        PARKING_SPOTS_TABLE,
        PARKING_ZONES_TABLE,
    ]
    
    for table in tables_to_drop:
        logger.info(f"Dropping {table} table")
        op.drop_table(table)
    
    # Drop ENUM types (PostgreSQL specific)
    if op.get_context().dialect.name == 'postgresql':
        enums_to_drop = [
            'spot_type', 'spot_status', 'zone_type', 'rate_type',
            'vehicle_type', 'session_status', 'reservation_status',
            'maintenance_type', 'maintenance_status', 'sensor_type',
            'sensor_status'
        ]
        for enum in enums_to_drop:
            logger.info(f"Dropping {enum} enum")
            op.execute(f"DROP TYPE IF EXISTS {enum} CASCADE;")
    
    # Drop partitions
    logger.info("Dropping partitions")
    for i in range(12):
        month_date = datetime.now().replace(day=1) + timedelta(days=30*i)
        month_str = month_date.strftime('%Y_%m')
        op.execute(f"DROP TABLE IF EXISTS parking_sessions_{month_str} CASCADE;")
        op.execute(f"DROP TABLE IF EXISTS spot_occupancy_history_{month_str} CASCADE;")
    
    logger.info(f"Downgrade of migration {revision} completed successfully")


def validate_parking_data() -> dict:
    """
    Validate parking data quality after migration
    """
    logger.info("Validating parking data quality")
    
    connection = op.get_bind()
    results = {}
    
    # Check for spots without zones
    result = connection.execute("""
        SELECT COUNT(*) 
        FROM parking_spots 
        WHERE zone_id NOT IN (SELECT id FROM parking_zones)
    """)
    results['spots_without_zones'] = result.scalar()
    
    # Check for inconsistent zone counts
    result = connection.execute("""
        SELECT COUNT(*) 
        FROM parking_zones z
        WHERE z.total_spots != (
            SELECT COUNT(*) 
            FROM parking_spots s 
            WHERE s.zone_id = z.id AND s.is_active = true
        )
    """)
    results['zones_with_inconsistent_counts'] = result.scalar()
    
    # Check for duplicate spot numbers in same zone
    result = connection.execute("""
        SELECT zone_id, spot_number, COUNT(*) 
        FROM parking_spots 
        GROUP BY zone_id, spot_number 
        HAVING COUNT(*) > 1
    """)
    results['duplicate_spot_numbers'] = result.rowcount
    
    # Check for spots with invalid status
    result = connection.execute("""
        SELECT COUNT(*) 
        FROM parking_spots 
        WHERE status NOT IN ('available', 'occupied', 'reserved', 'maintenance', 'out_of_service')
    """)
    results['invalid_status'] = result.scalar()
    
    # Check for expired rates
    result = connection.execute("""
        SELECT COUNT(*) 
        FROM parking_rates 
        WHERE effective_to < CURRENT_DATE AND is_active = true
    """)
    results['expired_active_rates'] = result.scalar()
    
    logger.info(f"Validation results: {results}")
    return results


def create_sample_reservations():
    """
    Create sample reservations for testing
    """
    logger.info("Creating sample reservations")
    
    # Get a spot ID
    result = op.get_bind().execute("""
        SELECT id FROM parking_spots WHERE status = 'available' LIMIT 1
    """).first()
    
    if result:
        spot_id = result[0]
        user_id = op.get_bind().execute(
            "SELECT id FROM users WHERE username = 'admin'"
        ).scalar()
        
        reservation_id = uuid.uuid4()
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        op.execute(f"""
        INSERT INTO parking_reservations (
            id, spot_id, user_id, reservation_number, status,
            start_time, end_time, customer_name, customer_email,
            customer_phone, created_at, updated_at
        ) VALUES (
            '{reservation_id}',
            '{spot_id}',
            '{user_id}',
            'RES{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'confirmed',
            '{start_time}',
            '{end_time}',
            'John Doe',
            'john@example.com',
            '+1234567890',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        );
        """)


def post_upgrade_hook():
    """Hook to run after successful upgrade"""
    logger.info("Running post-upgrade hooks for parking spots migration")
    
    # Validate the migration
    validation_results = validate_parking_data()
    
    # Create sample data for testing (optional)
    if validation_results.get('spots_without_zones', 0) == 0:
        create_sample_reservations()
    
    # Log any issues
    for key, value in validation_results.items():
        if value > 0:
            logger.warning(f"Validation issue - {key}: {value}")
    
    logger.info("Post-upgrade hooks completed")


# Register the post-upgrade hook
if hasattr(op, 'register_post_upgrade_hook'):
    op.register_post_upgrade_hook(post_upgrade_hook)


# Add table comments
def add_table_comments():
    """Add detailed comments to tables for documentation"""
    op.execute(f"""
    COMMENT ON TABLE {PARKING_ZONES_TABLE} IS 'Parking zones/areas within the facility. Each zone can have multiple spots and specific characteristics.';
    COMMENT ON TABLE {PARKING_SPOTS_TABLE} IS 'Individual parking spots with real-time status tracking, dimensions, and features.';
    COMMENT ON TABLE {PARKING_RATES_TABLE} IS 'Flexible rate configuration supporting different pricing models, time periods, and vehicle types.';
    COMMENT ON TABLE {PARKING_SESSIONS_TABLE} IS 'Active and historical parking sessions with billing information and entry/exit tracking.';
    COMMENT ON TABLE {PARKING_RESERVATIONS_TABLE} IS 'User reservations for parking spots with payment and check-in/out tracking.';
    COMMENT ON TABLE {SPOT_MAINTENANCE_TABLE} IS 'Maintenance schedules, work orders, and history for parking spots.';
    COMMENT ON TABLE {SPOT_SENSORS_TABLE} IS 'IoT sensor configuration, status, and real-time readings for occupancy detection.';
    COMMENT ON TABLE {SPOT_OCCUPANCY_HISTORY_TABLE} IS 'Historical record of spot occupancy for analytics and reporting.';
    COMMENT ON TABLE {PARKING_RATE_HISTORY_TABLE} IS 'Audit trail for rate changes to track pricing history.';
    """)