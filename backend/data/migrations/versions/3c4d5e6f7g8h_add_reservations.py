# parking-management/data/migrations/versions/3c4d5e6f7g8h_add_reservations.py

"""Add comprehensive reservations system

Revision ID: 3c4d5e6f7g8h
Revises: 2b3c4d5e6f7g
Create Date: 2024-01-25 09:00:00.123456

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime, timedelta
import logging
import json

# Configure logging
logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '3c4d5e6f7g8h'
down_revision: Union[str, None] = '2b3c4d5e6f7g'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define table names
RESERVATIONS_TABLE = 'reservations'
RESERVATION_HISTORY_TABLE = 'reservation_history'
RESERVATION_ATTENDEES_TABLE = 'reservation_attendees'
RESERVATION_ADDONS_TABLE = 'reservation_addons'
RESERVATION_PAYMENTS_TABLE = 'reservation_payments'
RESERVATION_REMINDERS_TABLE = 'reservation_reminders'
RESERVATION_RECURRING_TABLE = 'reservation_recurring'
RESERVATION_BLACKOUT_TABLE = 'reservation_blackout_dates'
RESERVATION_WAITLIST_TABLE = 'reservation_waitlist'
RESERVATION_FEEDBACK_TABLE = 'reservation_feedback'
RESERVATION_NOTIFICATIONS_TABLE = 'reservation_notifications'

# Define ENUM types for PostgreSQL
reservation_status_enum = sa.Enum(
    'draft', 'pending', 'confirmed', 'checked_in', 'checked_out',
    'completed', 'cancelled', 'no_show', 'expired', 'modified',
    'refunded', 'disputed',
    name='reservation_status'
)

payment_status_enum = sa.Enum(
    'pending', 'authorized', 'paid', 'partially_paid', 'refunded',
    'partially_refunded', 'failed', 'cancelled', 'disputed',
    name='payment_status'
)

payment_method_enum = sa.Enum(
    'credit_card', 'debit_card', 'paypal', 'apple_pay', 'google_pay',
    'bank_transfer', 'cash', 'voucher', 'gift_card', 'corporate',
    name='payment_method'
)

recurring_frequency_enum = sa.Enum(
    'daily', 'weekly', 'bi_weekly', 'monthly', 'quarterly', 'yearly',
    'weekdays', 'weekends', 'custom',
    name='recurring_frequency'
)

attendee_status_enum = sa.Enum(
    'pending', 'confirmed', 'checked_in', 'cancelled', 'no_show',
    name='attendee_status'
)

notification_type_enum = sa.Enum(
    'confirmation', 'reminder', 'modification', 'cancellation',
    'check_in', 'check_out', 'feedback', 'payment_receipt',
    'waitlist_confirmation', 'blackout_alert',
    name='notification_type'
)

notification_channel_enum = sa.Enum(
    'email', 'sms', 'push', 'whatsapp', 'in_app',
    name='notification_channel'
)

feedback_rating_enum = sa.Enum(
    '1', '2', '3', '4', '5',
    name='feedback_rating'
)

addon_type_enum = sa.Enum(
    'ev_charging', 'car_wash', 'valet', 'detailing', 'tire_inflation',
    'luggage_storage', 'bike_rack', 'roof_rack', 'special_assistance',
    name='addon_type'
)


def upgrade() -> None:
    """
    Upgrade migration - creates comprehensive reservations system
    """
    logger.info(f"Starting migration {revision}: Add reservations system")
    
    # Create ENUM types first (PostgreSQL specific)
    if op.get_context().dialect.name == 'postgresql':
        enums = [
            reservation_status_enum, payment_status_enum, payment_method_enum,
            recurring_frequency_enum, attendee_status_enum, notification_type_enum,
            notification_channel_enum, feedback_rating_enum, addon_type_enum
        ]
        for enum in enums:
            enum.create(op.get_bind(), checkfirst=True)
        logger.info("Created ENUM types")
    
    # Create enhanced reservations table
    logger.info("Creating enhanced reservations table")
    op.create_table(
        RESERVATIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('reservation_number', sa.String(50), nullable=False, unique=True),
        sa.Column('external_reference', sa.String(100), unique=True),
        sa.Column('qr_code', sa.Text),
        sa.Column('barcode', sa.String(255)),
        sa.Column('qr_code_data', sa.Text),
        
        # Core relationships
        sa.Column('spot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True)),
        sa.Column('rate_id', postgresql.UUID(as_uuid=True)),
        
        # Customer information (for guest reservations)
        sa.Column('is_guest', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('guest_email', sa.String(255)),
        sa.Column('guest_phone', sa.String(20)),
        sa.Column('guest_first_name', sa.String(100)),
        sa.Column('guest_last_name', sa.String(100)),
        sa.Column('guest_company', sa.String(200)),
        
        # Reservation details
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reservation_type', sa.String(50), nullable=False),  # standard, vip, event, monthly
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('flexible_timing', sa.Boolean, server_default='false'),
        sa.Column('flexible_window_minutes', sa.Integer),
        sa.Column('actual_check_in', sa.DateTime(timezone=True)),
        sa.Column('actual_check_out', sa.DateTime(timezone=True)),
        sa.Column('duration_minutes', sa.Integer),
        sa.Column('buffer_time_before', sa.Integer, server_default='0'),
        sa.Column('buffer_time_after', sa.Integer, server_default='0'),
        
        # Vehicle information
        sa.Column('license_plate', sa.String(20)),
        sa.Column('vehicle_make', sa.String(100)),
        sa.Column('vehicle_model', sa.String(100)),
        sa.Column('vehicle_color', sa.String(50)),
        sa.Column('vehicle_type', sa.String(20)),
        sa.Column('vehicle_length_cm', sa.Integer),
        sa.Column('vehicle_height_cm', sa.Integer),
        sa.Column('vehicle_notes', sa.Text),
        
        # Pricing
        sa.Column('base_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(10, 2), server_default='0'),
        sa.Column('discount_amount', sa.Numeric(10, 2), server_default='0'),
        sa.Column('addons_amount', sa.Numeric(10, 2), server_default='0'),
        sa.Column('fees_amount', sa.Numeric(10, 2), server_default='0'),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('tax_rate', sa.Numeric(5, 2)),
        sa.Column('tax_details', postgresql.JSONB),
        
        # Discounts
        sa.Column('discount_code', sa.String(50)),
        sa.Column('discount_type', sa.String(20)),  # percentage, fixed
        sa.Column('discount_value', sa.Numeric(10, 2)),
        sa.Column('promotion_id', sa.String(100)),
        
        # Payment
        sa.Column('payment_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('payment_method', sa.String(50)),
        sa.Column('payment_token', sa.String(255)),
        sa.Column('payment_intent_id', sa.String(255)),
        sa.Column('payment_receipt_url', sa.String(500)),
        sa.Column('requires_deposit', sa.Boolean, server_default='false'),
        sa.Column('deposit_amount', sa.Numeric(10, 2)),
        sa.Column('deposit_paid', sa.Boolean, server_default='false'),
        sa.Column('balance_due', sa.Numeric(10, 2)),
        sa.Column('balance_due_date', sa.DateTime(timezone=True)),
        
        # Cancellation
        sa.Column('cancellation_reason', sa.Text),
        sa.Column('cancelled_at', sa.DateTime(timezone=True)),
        sa.Column('cancelled_by', postgresql.UUID(as_uuid=True)),
        sa.Column('cancellation_fee', sa.Numeric(10, 2)),
        sa.Column('refund_amount', sa.Numeric(10, 2)),
        sa.Column('refund_id', sa.String(255)),
        sa.Column('refunded_at', sa.DateTime(timezone=True)),
        
        # Modification tracking
        sa.Column('modified_count', sa.Integer, server_default='0'),
        sa.Column('last_modified_at', sa.DateTime(timezone=True)),
        sa.Column('original_start_time', sa.DateTime(timezone=True)),
        sa.Column('original_end_time', sa.DateTime(timezone=True)),
        sa.Column('modification_history', postgresql.JSONB),
        
        # Check-in/out
        sa.Column('check_in_code', sa.String(50)),
        sa.Column('check_in_method', sa.String(50)),  # qr, manual, app, gate
        sa.Column('check_in_by', postgresql.UUID(as_uuid=True)),
        sa.Column('check_in_gate', sa.String(50)),
        sa.Column('check_in_image_url', sa.String(500)),
        sa.Column('check_out_method', sa.String(50)),
        sa.Column('check_out_by', postgresql.UUID(as_uuid=True)),
        sa.Column('check_out_gate', sa.String(50)),
        sa.Column('check_out_image_url', sa.String(500)),
        
        # Additional services
        sa.Column('addons', postgresql.JSONB),
        sa.Column('special_requests', sa.Text),
        sa.Column('access_instructions', sa.Text),
        sa.Column('has_valet', sa.Boolean, server_default='false'),
        sa.Column('valet_key_location', sa.String(255)),
        
        # Recurring reservations
        sa.Column('is_recurring', sa.Boolean, server_default='false'),
        sa.Column('recurring_id', postgresql.UUID(as_uuid=True)),
        sa.Column('recurring_sequence', sa.Integer),
        
        # Event/Group reservations
        sa.Column('is_group_reservation', sa.Boolean, server_default='false'),
        sa.Column('group_id', sa.String(100)),
        sa.Column('group_name', sa.String(200)),
        sa.Column('group_size', sa.Integer),
        
        # Corporate/Company
        sa.Column('is_corporate', sa.Boolean, server_default='false'),
        sa.Column('company_name', sa.String(200)),
        sa.Column('company_id', sa.String(100)),
        sa.Column('cost_center', sa.String(100)),
        sa.Column('po_number', sa.String(100)),
        
        # Notifications
        sa.Column('reminder_sent', sa.Boolean, server_default='false'),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True)),
        sa.Column('reminder_count', sa.Integer, server_default='0'),
        sa.Column('confirmation_sent', sa.Boolean, server_default='false'),
        sa.Column('confirmation_sent_at', sa.DateTime(timezone=True)),
        
        # Metadata
        sa.Column('source', sa.String(50)),  # web, mobile, api, walk-in
        sa.Column('source_channel', sa.String(50)),
        sa.Column('campaign_source', sa.String(100)),
        sa.Column('booking_agent', sa.String(200)),
        sa.Column('booking_agent_id', sa.String(100)),
        sa.Column('commission_rate', sa.Numeric(5, 2)),
        sa.Column('commission_amount', sa.Numeric(10, 2)),
        
        # Notes
        sa.Column('internal_notes', sa.Text),
        sa.Column('customer_notes', sa.Text),
        sa.Column('staff_notes', sa.Text),
        
        # JSON fields for flexibility
        sa.Column('custom_fields', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        
        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True)),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        
        # Indexes
        sa.Index('ix_reservations_number', 'reservation_number', unique=True),
        sa.Index('ix_reservations_external_ref', 'external_reference', unique=True),
        sa.Index('ix_reservations_spot_id', 'spot_id'),
        sa.Index('ix_reservations_user_id', 'user_id'),
        sa.Index('ix_reservations_vehicle_id', 'vehicle_id'),
        sa.Index('ix_reservations_status', 'status'),
        sa.Index('ix_reservations_time_range', 'start_time', 'end_time'),
        sa.Index('ix_reservations_license_plate', 'license_plate'),
        sa.Index('ix_reservations_guest_email', 'guest_email'),
        sa.Index('ix_reservations_payment_status', 'payment_status'),
        sa.Index('ix_reservations_group_id', 'group_id'),
        sa.Index('ix_reservations_recurring_id', 'recurring_id'),
        sa.Index('ix_reservations_created_at', 'created_at'),
        sa.Index('ix_reservations_deleted_at', 'deleted_at'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['spot_id'], ['parking_spots.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rate_id'], ['parking_rates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['cancelled_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['check_in_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['check_out_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Enhanced reservations table with comprehensive booking management'),
        
        # Partition by month
        postgresql_partition_by='RANGE (start_time)',
    )
    
    # Create reservation history table
    logger.info("Creating reservation history table")
    op.create_table(
        RESERVATION_HISTORY_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('previous_status', sa.String(20)),
        sa.Column('new_status', sa.String(20)),
        sa.Column('changes', postgresql.JSONB),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('performed_by', postgresql.UUID(as_uuid=True)),
        sa.Column('performed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('metadata', postgresql.JSONB),
        
        # Indexes
        sa.Index('ix_res_history_reservation', 'reservation_id'),
        sa.Index('ix_res_history_performed_at', 'performed_at'),
        sa.Index('ix_res_history_action', 'action'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['reservation_id'], [f'{RESERVATIONS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['performed_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Audit history for all reservation actions'),
        
        # Partition by month
        postgresql_partition_by='RANGE (performed_at)',
    )
    
    # Create reservation attendees table (for group bookings)
    logger.info("Creating reservation attendees table")
    op.create_table(
        RESERVATION_ATTENDEES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name', sa.String(100)),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(20)),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True)),
        sa.Column('license_plate', sa.String(20)),
        sa.Column('vehicle_make', sa.String(100)),
        sa.Column('vehicle_model', sa.String(100)),
        sa.Column('vehicle_color', sa.String(50)),
        sa.Column('spot_id', postgresql.UUID(as_uuid=True)),
        sa.Column('status', sa.String(20), nullable=False, server_default='confirmed'),
        sa.Column('checked_in_at', sa.DateTime(timezone=True)),
        sa.Column('checked_out_at', sa.DateTime(timezone=True)),
        sa.Column('qr_code', sa.Text),
        sa.Column('access_code', sa.String(50)),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_attendees_reservation', 'reservation_id'),
        sa.Index('ix_attendees_email', 'email'),
        sa.Index('ix_attendees_license', 'license_plate'),
        sa.Index('ix_attendees_status', 'status'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['reservation_id'], [f'{RESERVATIONS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['spot_id'], ['parking_spots.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Attendees for group reservations'),
    )
    
    # Create reservation addons table
    logger.info("Creating reservation addons table")
    op.create_table(
        RESERVATION_ADDONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('addon_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('quantity', sa.Integer, nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('total_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(10, 2), server_default='0'),
        sa.Column('currency', sa.String(3), server_default='USD'),
        sa.Column('scheduled_time', sa.DateTime(timezone=True)),
        sa.Column('completed_time', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('provider', sa.String(200)),
        sa.Column('provider_contact', sa.String(100)),
        sa.Column('provider_notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_addons_reservation', 'reservation_id'),
        sa.Index('ix_addons_type', 'addon_type'),
        sa.Index('ix_addons_status', 'status'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['reservation_id'], [f'{RESERVATIONS_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Add-on services for reservations'),
    )
    
    # Create reservation payments table
    logger.info("Creating reservation payments table")
    op.create_table(
        RESERVATION_PAYMENTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_number', sa.String(50), nullable=False, unique=True),
        sa.Column('transaction_id', sa.String(255), unique=True),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('payment_type', sa.String(50), nullable=False),  # deposit, full, partial, refund
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('provider', sa.String(100)),  # stripe, paypal, etc.
        sa.Column('provider_response', postgresql.JSONB),
        sa.Column('card_last4', sa.String(4)),
        sa.Column('card_brand', sa.String(50)),
        sa.Column('card_expiry', sa.String(7)),
        sa.Column('billing_name', sa.String(200)),
        sa.Column('billing_address', sa.Text),
        sa.Column('billing_city', sa.String(100)),
        sa.Column('billing_state', sa.String(50)),
        sa.Column('billing_zip', sa.String(20)),
        sa.Column('billing_country', sa.String(2)),
        sa.Column('receipt_url', sa.String(500)),
        sa.Column('receipt_number', sa.String(100)),
        sa.Column('refund_reason', sa.Text),
        sa.Column('refunded_by', postgresql.UUID(as_uuid=True)),
        sa.Column('refunded_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_payments_reservation', 'reservation_id'),
        sa.Index('ix_payments_transaction', 'transaction_id'),
        sa.Index('ix_payments_status', 'status'),
        sa.Index('ix_payments_method', 'payment_method'),
        sa.Index('ix_payments_created_at', 'created_at'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['reservation_id'], [f'{RESERVATIONS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['refunded_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Payment transactions for reservations'),
    )
    
    # Create reservation reminders table
    logger.info("Creating reservation reminders table")
    op.create_table(
        RESERVATION_REMINDERS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reminder_type', sa.String(50), nullable=False),  # email, sms, push
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('retry_count', sa.Integer, server_default='0'),
        sa.Column('last_error', sa.Text),
        sa.Column('template', sa.String(255)),
        sa.Column('subject', sa.String(255)),
        sa.Column('content', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_reminders_reservation', 'reservation_id'),
        sa.Index('ix_reminders_scheduled', 'scheduled_for'),
        sa.Index('ix_reminders_status', 'status'),
        sa.Index('ix_reminders_type', 'reminder_type'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['reservation_id'], [f'{RESERVATIONS_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Scheduled reminders for reservations'),
    )
    
    # Create recurring reservations table
    logger.info("Creating recurring reservations table")
    op.create_table(
        RESERVATION_RECURRING_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('parent_reservation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('frequency', sa.String(20), nullable=False),
        sa.Column('interval_count', sa.Integer, server_default='1'),
        sa.Column('weekdays', postgresql.ARRAY(sa.Integer)),  # 0-6 for Sunday-Saturday
        sa.Column('monthly_option', sa.String(20)),  # day_of_month, weekday_of_month
        sa.Column('start_date', sa.Date, nullable=False),
        sa.Column('end_date', sa.Date),
        sa.Column('end_after_occurrences', sa.Integer),
        sa.Column('occurrences_created', sa.Integer, server_default='0'),
        sa.Column('max_occurrences', sa.Integer),
        sa.Column('excluded_dates', postgresql.ARRAY(sa.Date)),
        sa.Column('next_scheduled_date', sa.Date),
        sa.Column('last_processed_date', sa.Date),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('cancelled_at', sa.DateTime(timezone=True)),
        sa.Column('cancellation_reason', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_recurring_parent', 'parent_reservation_id'),
        sa.Index('ix_recurring_active', 'is_active'),
        sa.Index('ix_recurring_next', 'next_scheduled_date'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['parent_reservation_id'], [f'{RESERVATIONS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Recurring reservation patterns'),
    )
    
    # Create blackout dates table
    logger.info("Creating blackout dates table")
    op.create_table(
        RESERVATION_BLACKOUT_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('spot_id', postgresql.UUID(as_uuid=True)),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True)),
        sa.Column('reason', sa.String(200), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_recurring', sa.Boolean, server_default='false'),
        sa.Column('recurring_pattern', postgresql.JSONB),
        sa.Column('affects_reservations', sa.Boolean, server_default='true'),
        sa.Column('affected_reservations', postgresql.JSONB),
        sa.Column('notification_sent', sa.Boolean, server_default='false'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_blackout_spot', 'spot_id'),
        sa.Index('ix_blackout_zone', 'zone_id'),
        sa.Index('ix_blackout_dates', 'start_date', 'end_date'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['spot_id'], ['parking_spots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['zone_id'], ['parking_zones.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Blackout dates when parking is unavailable'),
    )
    
    # Create waitlist table
    logger.info("Creating waitlist table")
    op.create_table(
        RESERVATION_WAITLIST_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('spot_id', postgresql.UUID(as_uuid=True)),
        sa.Column('zone_id', postgresql.UUID(as_uuid=True)),
        sa.Column('spot_type', sa.String(20)),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('flexible_dates', sa.Boolean, server_default='false'),
        sa.Column('flexible_window_days', sa.Integer),
        sa.Column('preferred_times', postgresql.JSONB),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('contact_phone', sa.String(20)),
        sa.Column('status', sa.String(20), server_default='active'),  # active, notified, converted, expired
        sa.Column('priority', sa.Integer, server_default='0'),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('notified_at', sa.DateTime(timezone=True)),
        sa.Column('converted_reservation_id', postgresql.UUID(as_uuid=True)),
        sa.Column('notes', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_waitlist_user', 'user_id'),
        sa.Index('ix_waitlist_spot', 'spot_id'),
        sa.Index('ix_waitlist_zone', 'zone_id'),
        sa.Index('ix_waitlist_dates', 'start_date', 'end_date'),
        sa.Index('ix_waitlist_status', 'status'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['spot_id'], ['parking_spots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['zone_id'], ['parking_zones.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['converted_reservation_id'], [f'{RESERVATIONS_TABLE}.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Waitlist for unavailable parking spots'),
    )
    
    # Create feedback table
    logger.info("Creating feedback table")
    op.create_table(
        RESERVATION_FEEDBACK_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('rating', sa.Integer, nullable=False),
        sa.Column('review_title', sa.String(200)),
        sa.Column('review_text', sa.Text),
        sa.Column('pros', sa.Text),
        sa.Column('cons', sa.Text),
        sa.Column('would_recommend', sa.Boolean),
        sa.Column('would_return', sa.Boolean),
        sa.Column('categories', postgresql.JSONB),  # cleanliness, staff, value, etc.
        sa.Column('tags', postgresql.ARRAY(sa.String)),
        sa.Column('images', postgresql.ARRAY(sa.String)),
        sa.Column('staff_response', sa.Text),
        sa.Column('staff_responded_by', postgresql.UUID(as_uuid=True)),
        sa.Column('staff_responded_at', sa.DateTime(timezone=True)),
        sa.Column('is_public', sa.Boolean, server_default='true'),
        sa.Column('is_verified', sa.Boolean, server_default='false'),
        sa.Column('helpful_count', sa.Integer, server_default='0'),
        sa.Column('reported_count', sa.Integer, server_default='0'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_feedback_reservation', 'reservation_id'),
        sa.Index('ix_feedback_user', 'user_id'),
        sa.Index('ix_feedback_rating', 'rating'),
        sa.Index('ix_feedback_created', 'created_at'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['reservation_id'], [f'{RESERVATIONS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['staff_responded_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Customer feedback and ratings for reservations'),
    )
    
    # Create notifications table
    logger.info("Creating notifications table")
    op.create_table(
        RESERVATION_NOTIFICATIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('recipient', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(255)),
        sa.Column('content', sa.Text),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('sent_at', sa.DateTime(timezone=True)),
        sa.Column('delivered_at', sa.DateTime(timezone=True)),
        sa.Column('opened_at', sa.DateTime(timezone=True)),
        sa.Column('clicked_at', sa.DateTime(timezone=True)),
        sa.Column('failed_at', sa.DateTime(timezone=True)),
        sa.Column('failure_reason', sa.Text),
        sa.Column('retry_count', sa.Integer, server_default='0'),
        sa.Column('provider_response', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_notifications_reservation', 'reservation_id'),
        sa.Index('ix_notifications_type', 'notification_type'),
        sa.Index('ix_notifications_status', 'status'),
        sa.Index('ix_notifications_created', 'created_at'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['reservation_id'], [f'{RESERVATIONS_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Notification tracking for reservation communications'),
    )
    
    # Create functions and triggers
    logger.info("Creating database functions and triggers")
    
    # Function to generate reservation number
    op.execute("""
    CREATE OR REPLACE FUNCTION generate_reservation_number()
    RETURNS TRIGGER AS $$
    DECLARE
        seq_num INTEGER;
        year_prefix TEXT;
    BEGIN
        year_prefix := TO_CHAR(CURRENT_DATE, 'YYYY');
        
        SELECT COALESCE(MAX(SUBSTRING(reservation_number FROM 9)::INTEGER), 0) + 1
        INTO seq_num
        FROM reservations
        WHERE reservation_number LIKE 'RES-' || year_prefix || '-%';
        
        NEW.reservation_number := 'RES-' || year_prefix || '-' || LPAD(seq_num::TEXT, 6, '0');
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for reservation number
    op.execute("""
    CREATE TRIGGER generate_reservation_number_trigger
        BEFORE INSERT ON reservations
        FOR EACH ROW
        WHEN (NEW.reservation_number IS NULL)
        EXECUTE FUNCTION generate_reservation_number();
    """)
    
    # Function to check spot availability
    op.execute("""
    CREATE OR REPLACE FUNCTION check_spot_availability(
        p_spot_id UUID,
        p_start_time TIMESTAMP WITH TIME ZONE,
        p_end_time TIMESTAMP WITH TIME ZONE,
        p_exclude_reservation_id UUID DEFAULT NULL
    ) RETURNS BOOLEAN AS $$
    DECLARE
        conflict_count INTEGER;
    BEGIN
        SELECT COUNT(*)
        INTO conflict_count
        FROM reservations
        WHERE spot_id = p_spot_id
            AND status IN ('confirmed', 'checked_in')
            AND id != COALESCE(p_exclude_reservation_id, '00000000-0000-0000-0000-000000000000'::UUID)
            AND tstzrange(start_time, end_time) && tstzrange(p_start_time, p_end_time);
        
        RETURN conflict_count = 0;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Function to calculate reservation price
    op.execute("""
    CREATE OR REPLACE FUNCTION calculate_reservation_price(
        p_spot_id UUID,
        p_start_time TIMESTAMP WITH TIME ZONE,
        p_end_time TIMESTAMP WITH TIME ZONE,
        p_discount_code TEXT DEFAULT NULL
    ) RETURNS TABLE (
        base_amount NUMERIC,
        tax_amount NUMERIC,
        total_amount NUMERIC,
        rate_applied NUMERIC,
        rate_type TEXT
    ) AS $$
    DECLARE
        v_spot RECORD;
        v_rate RECORD;
        v_duration_hours NUMERIC;
        v_duration_days NUMERIC;
    BEGIN
        -- Get spot details
        SELECT * INTO v_spot FROM parking_spots WHERE id = p_spot_id;
        
        -- Calculate duration
        v_duration_hours := EXTRACT(EPOCH FROM (p_end_time - p_start_time)) / 3600;
        v_duration_days := CEIL(v_duration_hours / 24);
        
        -- Find applicable rate
        SELECT * INTO v_rate
        FROM parking_rates
        WHERE (spot_id = p_spot_id OR spot_type = v_spot.spot_type)
            AND effective_from <= p_start_time
            AND (effective_to IS NULL OR effective_to >= p_end_time)
            AND is_active = true
        ORDER BY priority DESC, created_at DESC
        LIMIT 1;
        
        -- Calculate base amount
        IF v_rate.unit = 'hour' THEN
            base_amount := v_rate.base_rate * v_duration_hours;
            rate_type := 'hourly';
        ELSIF v_rate.unit = 'day' THEN
            base_amount := v_rate.base_rate * v_duration_days;
            rate_type := 'daily';
        ELSE
            base_amount := v_rate.base_rate;
            rate_type := 'fixed';
        END IF;
        
        -- Apply discount if code provided
        IF p_discount_code IS NOT NULL THEN
            -- Discount logic would go here
            NULL;
        END IF;
        
        -- Calculate tax
        tax_amount := base_amount * 0.10; -- 10% tax rate example
        total_amount := base_amount + tax_amount;
        rate_applied := v_rate.base_rate;
        
        RETURN NEXT;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Function to handle no-shows
    op.execute("""
    CREATE OR REPLACE FUNCTION process_no_shows()
    RETURNS VOID AS $$
    BEGIN
        UPDATE reservations
        SET status = 'no_show',
            updated_at = CURRENT_TIMESTAMP
        WHERE status = 'confirmed'
            AND start_time < CURRENT_TIMESTAMP - INTERVAL '30 minutes'
            AND actual_check_in IS NULL;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Function to expire pending reservations
    op.execute("""
    CREATE OR REPLACE FUNCTION expire_pending_reservations()
    RETURNS VOID AS $$
    BEGIN
        UPDATE reservations
        SET status = 'expired',
            updated_at = CURRENT_TIMESTAMP
        WHERE status = 'pending'
            AND created_at < CURRENT_TIMESTAMP - INTERVAL '30 minutes';
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create views
    logger.info("Creating views")
    
    # View for reservation summary
    op.execute("""
    CREATE OR REPLACE VIEW v_reservation_summary AS
    SELECT 
        r.id,
        r.reservation_number,
        r.status,
        r.start_time,
        r.end_time,
        r.total_amount,
        r.currency,
        r.payment_status,
        ps.spot_number,
        pz.name as zone_name,
        COALESCE(u.email, r.guest_email) as customer_email,
        COALESCE(u.first_name || ' ' || u.last_name, 
                r.guest_first_name || ' ' || r.guest_last_name) as customer_name,
        r.license_plate,
        r.created_at
    FROM reservations r
    JOIN parking_spots ps ON r.spot_id = ps.id
    JOIN parking_zones pz ON ps.zone_id = pz.id
    LEFT JOIN users u ON r.user_id = u.id;
    """)
    
    # View for daily occupancy forecast
    op.execute("""
    CREATE OR REPLACE VIEW v_daily_occupancy_forecast AS
    SELECT 
        DATE(start_time) as date,
        COUNT(*) as total_reservations,
        COUNT(DISTINCT spot_id) as spots_reserved,
        SUM(total_amount) as projected_revenue,
        COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as confirmed,
        COUNT(CASE WHEN status = 'checked_in' THEN 1 END) as checked_in,
        COUNT(CASE WHEN payment_status = 'paid' THEN 1 END) as paid
    FROM reservations
    WHERE start_time >= CURRENT_DATE
        AND start_time < CURRENT_DATE + INTERVAL '30 days'
        AND status NOT IN ('cancelled', 'expired', 'no_show')
    GROUP BY DATE(start_time)
    ORDER BY date;
    """)
    
    # Create materialized view for analytics
    op.execute("""
    CREATE MATERIALIZED VIEW mv_reservation_analytics AS
    SELECT 
        DATE_TRUNC('day', created_at) as day,
        COUNT(*) as total_bookings,
        AVG(total_amount) as avg_booking_value,
        SUM(total_amount) as revenue,
        COUNT(DISTINCT user_id) as unique_customers,
        COUNT(CASE WHEN is_guest THEN 1 END) as guest_bookings,
        COUNT(CASE WHEN is_recurring THEN 1 END) as recurring_bookings,
        COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancellations,
        COUNT(CASE WHEN status = 'no_show' THEN 1 END) as no_shows,
        AVG(EXTRACT(EPOCH FROM (end_time - start_time))/3600) as avg_duration_hours,
        MODE() WITHIN GROUP (ORDER BY vehicle_type) as most_common_vehicle,
        MODE() WITHIN GROUP (ORDER BY source) as most_common_source
    FROM reservations
    WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY DATE_TRUNC('day', created_at)
    ORDER BY day DESC;
    """)
    
    # Create indexes on materialized view
    op.create_index('idx_mv_res_analytics_day', 'mv_reservation_analytics', ['day'])
    
    # Create scheduled job for no-show processing (PostgreSQL pg_cron if available)
    if op.get_context().dialect.name == 'postgresql':
        try:
            op.execute("""
            SELECT cron.schedule(
                'process-no-shows',
                '*/15 * * * *',
                $$SELECT process_no_shows()$$
            );
            """)
            logger.info("Scheduled no-show processing job")
        except:
            logger.warning("pg_cron extension not available, skipping job scheduling")
    
    # Insert sample data
    logger.info("Inserting sample reservation data")
    
    # Get a spot ID
    spot_result = op.get_bind().execute("""
        SELECT id FROM parking_spots WHERE status = 'available' LIMIT 1
    """).first()
    
    if spot_result:
        spot_id = spot_result[0]
        
        # Get user ID
        user_result = op.get_bind().execute("""
            SELECT id FROM users WHERE username = 'admin' LIMIT 1
        """).first()
        
        if user_result:
            user_id = user_result[0]
            
            # Create sample reservations
            sample_reservations = [
                {
                    'start': datetime.now() + timedelta(days=1, hours=10),
                    'end': datetime.now() + timedelta(days=1, hours=14),
                    'status': 'confirmed',
                    'amount': 20.00
                },
                {
                    'start': datetime.now() + timedelta(days=2, hours=9),
                    'end': datetime.now() + timedelta(days=2, hours=17),
                    'status': 'confirmed',
                    'amount': 40.00
                },
                {
                    'start': datetime.now() - timedelta(days=1, hours=8),
                    'end': datetime.now() - timedelta(days=1, hours=12),
                    'status': 'completed',
                    'amount': 20.00
                }
            ]
            
            for res in sample_reservations:
                res_id = uuid.uuid4()
                op.execute(f"""
                INSERT INTO reservations (
                    id, spot_id, user_id, status, start_time, end_time,
                    base_amount, total_amount, currency, payment_status,
                    license_plate, vehicle_make, vehicle_model,
                    created_at, updated_at
                ) VALUES (
                    '{res_id}',
                    '{spot_id}',
                    '{user_id}',
                    '{res["status"]}',
                    '{res["start"]}',
                    '{res["end"]}',
                    {res["amount"]},
                    {res["amount"]},
                    'USD',
                    'paid',
                    'ABC123',
                    'Toyota',
                    'Camry',
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                );
                """)
                
                # Add history entry
                op.execute(f"""
                INSERT INTO reservation_history (
                    id, reservation_id, action, previous_status, new_status,
                    performed_by, performed_at
                ) VALUES (
                    gen_random_uuid(),
                    '{res_id}',
                    'CREATE',
                    NULL,
                    '{res["status"]}',
                    '{user_id}',
                    CURRENT_TIMESTAMP
                );
                """)
    
    # Create partitions
    logger.info("Creating partitions for high-volume tables")
    
    # Create partitions for reservations (monthly for next 12 months)
    for i in range(12):
        month_date = datetime.now().replace(day=1) + timedelta(days=30*i)
        month_str = month_date.strftime('%Y_%m')
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS reservations_{month_str} 
        PARTITION OF reservations
        FOR VALUES FROM ('{month_date.strftime('%Y-%m-%d')}') 
        TO ('{next_month.strftime('%Y-%m-%d')}');
        """)
        
        # Create partition for history
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS reservation_history_{month_str} 
        PARTITION OF reservation_history
        FOR VALUES FROM ('{month_date.strftime('%Y-%m-%d')}') 
        TO ('{next_month.strftime('%Y-%m-%d')}');
        """)
    
    # Grant permissions
    if op.get_context().dialect.name == 'postgresql':
        op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;")
        op.execute("GRANT INSERT, UPDATE, DELETE ON reservations, reservation_attendees, reservation_addons TO app_user;")
        op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;")
    
    logger.info(f"Migration {revision} completed successfully")


def downgrade() -> None:
    """
    Downgrade migration - removes reservations system
    """
    logger.info(f"Starting downgrade of migration {revision}")
    
    # Drop triggers first
    logger.info("Dropping triggers")
    op.execute("DROP TRIGGER IF EXISTS generate_reservation_number_trigger ON reservations;")
    
    # Drop functions
    logger.info("Dropping functions")
    functions_to_drop = [
        'generate_reservation_number()',
        'check_spot_availability(uuid, timestamptz, timestamptz, uuid)',
        'calculate_reservation_price(uuid, timestamptz, timestamptz, text)',
        'process_no_shows()',
        'expire_pending_reservations()'
    ]
    for func in functions_to_drop:
        op.execute(f"DROP FUNCTION IF EXISTS {func} CASCADE;")
    
    # Drop views and materialized views
    logger.info("Dropping views")
    op.execute("DROP VIEW IF EXISTS v_reservation_summary CASCADE;")
    op.execute("DROP VIEW IF EXISTS v_daily_occupancy_forecast CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_reservation_analytics CASCADE;")
    
    # Drop tables in reverse order
    tables_to_drop = [
        RESERVATION_NOTIFICATIONS_TABLE,
        RESERVATION_FEEDBACK_TABLE,
        RESERVATION_WAITLIST_TABLE,
        RESERVATION_BLACKOUT_TABLE,
        RESERVATION_RECURRING_TABLE,
        RESERVATION_REMINDERS_TABLE,
        RESERVATION_PAYMENTS_TABLE,
        RESERVATION_ADDONS_TABLE,
        RESERVATION_ATTENDEES_TABLE,
        RESERVATION_HISTORY_TABLE,
        RESERVATIONS_TABLE,
    ]
    
    for table in tables_to_drop:
        logger.info(f"Dropping {table} table")
        op.drop_table(table)
    
    # Drop ENUM types
    if op.get_context().dialect.name == 'postgresql':
        enums_to_drop = [
            'reservation_status', 'payment_status', 'payment_method',
            'recurring_frequency', 'attendee_status', 'notification_type',
            'notification_channel', 'feedback_rating', 'addon_type'
        ]
        for enum in enums_to_drop:
            logger.info(f"Dropping {enum} enum")
            op.execute(f"DROP TYPE IF EXISTS {enum} CASCADE;")
    
    # Drop partitions
    logger.info("Dropping partitions")
    for i in range(12):
        month_date = datetime.now().replace(day=1) + timedelta(days=30*i)
        month_str = month_date.strftime('%Y_%m')
        op.execute(f"DROP TABLE IF EXISTS reservations_{month_str} CASCADE;")
        op.execute(f"DROP TABLE IF EXISTS reservation_history_{month_str} CASCADE;")
    
    logger.info(f"Downgrade of migration {revision} completed successfully")


def validate_reservation_data() -> dict:
    """
    Validate reservation data quality after migration
    """
    logger.info("Validating reservation data quality")
    
    connection = op.get_bind()
    results = {}
    
    # Check for overlapping reservations
    result = connection.execute("""
        SELECT COUNT(*)
        FROM reservations r1
        JOIN reservations r2 ON r1.spot_id = r2.spot_id
        WHERE r1.id < r2.id
            AND r1.status IN ('confirmed', 'checked_in')
            AND r2.status IN ('confirmed', 'checked_in')
            AND tstzrange(r1.start_time, r1.end_time) && tstzrange(r2.start_time, r2.end_time);
    """)
    results['overlapping_reservations'] = result.scalar()
    
    # Check for reservations without payments
    result = connection.execute("""
        SELECT COUNT(*)
        FROM reservations r
        LEFT JOIN reservation_payments rp ON r.id = rp.reservation_id
        WHERE rp.id IS NULL
            AND r.status IN ('confirmed', 'checked_in', 'completed')
            AND r.total_amount > 0;
    """)
    results['reservations_without_payments'] = result.scalar()
    
    # Check for past reservations that are still pending
    result = connection.execute("""
        SELECT COUNT(*)
        FROM reservations
        WHERE status = 'pending'
            AND start_time < CURRENT_TIMESTAMP;
    """)
    results['stale_pending_reservations'] = result.scalar()
    
    # Check for no-shows that weren't processed
    result = connection.execute("""
        SELECT COUNT(*)
        FROM reservations
        WHERE status = 'confirmed'
            AND start_time < CURRENT_TIMESTAMP - INTERVAL '1 hour'
            AND actual_check_in IS NULL;
    """)
    results['unprocessed_no_shows'] = result.scalar()
    
    # Validate pricing calculations
    result = connection.execute("""
        SELECT COUNT(*)
        FROM reservations
        WHERE total_amount != COALESCE(base_amount, 0) + COALESCE(tax_amount, 0) 
            + COALESCE(addons_amount, 0) - COALESCE(discount_amount, 0);
    """)
    results['incorrect_pricing'] = result.scalar()
    
    logger.info(f"Validation results: {results}")
    return results


def post_upgrade_hook():
    """Hook to run after successful upgrade"""
    logger.info("Running post-upgrade hooks for reservations migration")
    
    # Validate the migration
    validation_results = validate_reservation_data()
    
    # Refresh materialized view
    op.execute("REFRESH MATERIALIZED VIEW mv_reservation_analytics;")
    
    # Log any issues
    for key, value in validation_results.items():
        if value > 0:
            logger.warning(f"Validation issue - {key}: {value}")
    
    # Send notification (if configured)
    logger.info("Reservations system migration completed successfully")
    
    # Log summary statistics
    connection = op.get_bind()
    stats = connection.execute("""
        SELECT 
            COUNT(*) as total_reservations,
            COUNT(DISTINCT user_id) as unique_users,
            SUM(total_amount) as total_revenue,
            COUNT(CASE WHEN status = 'confirmed' THEN 1 END) as active_reservations
        FROM reservations
    """).first()
    
    if stats:
        logger.info(f"Reservation Summary: {stats.total_reservations} total reservations, "
                   f"{stats.active_reservations} active, ${stats.total_revenue} revenue")


# Register the post-upgrade hook
if hasattr(op, 'register_post_upgrade_hook'):
    op.register_post_upgrade_hook(post_upgrade_hook)


# Add table comments
def add_table_comments():
    """Add detailed comments to tables for documentation"""
    op.execute(f"""
    COMMENT ON TABLE {RESERVATIONS_TABLE} IS 'Comprehensive reservation system for parking spots with support for guest bookings, recurring reservations, and group bookings.';
    COMMENT ON TABLE {RESERVATION_HISTORY_TABLE} IS 'Audit trail for all reservation changes and status updates.';
    COMMENT ON TABLE {RESERVATION_ATTENDEES_TABLE} IS 'Individual attendees for group reservations with their own check-in/out tracking.';
    COMMENT ON TABLE {RESERVATION_ADDONS_TABLE} IS 'Additional services and add-ons purchased with reservations.';
    COMMENT ON TABLE {RESERVATION_PAYMENTS_TABLE} IS 'Payment transactions including deposits, full payments, and refunds.';
    COMMENT ON TABLE {RESERVATION_REMINDERS_TABLE} IS 'Scheduled notifications and reminders for upcoming reservations.';
    COMMENT ON TABLE {RESERVATION_RECURRING_TABLE} IS 'Recurring reservation patterns for regular customers.';
    COMMENT ON TABLE {RESERVATION_BLACKOUT_TABLE} IS 'Blackout dates when spots are unavailable for booking.';
    COMMENT ON TABLE {RESERVATION_WAITLIST_TABLE} IS 'Customer waitlist for popular times and spots.';
    COMMENT ON TABLE {RESERVATION_FEEDBACK_TABLE} IS 'Customer feedback and ratings after reservation completion.';
    COMMENT ON TABLE {RESERVATION_NOTIFICATIONS_TABLE} IS 'Delivery tracking for all customer notifications.';
    """)