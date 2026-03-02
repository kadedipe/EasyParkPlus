# parking-management/data/migrations/versions/8h9i0j1k2l3m_add_indexes.py

"""Add comprehensive performance indexes

Revision ID: 8h9i0j1k2l3m
Revises: 7g8h9i0j1k2l
Create Date: 2024-04-01 11:00:00.123456

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import logging

# Configure logging
logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '8h9i0j1k2l3m'
down_revision: Union[str, None] = '7g8h9i0j1k2l'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade migration - creates comprehensive performance indexes
    """
    logger.info(f"Starting migration {revision}: Add performance indexes")
    
    # ==================== USERS TABLE INDEXES ====================
    logger.info("Creating indexes for users table")
    
    # Basic lookup indexes
    op.create_index('idx_users_email_lookup', 'users', ['email'], unique=True, if_not_exists=True)
    op.create_index('idx_users_username_lookup', 'users', ['username'], unique=True, if_not_exists=True)
    op.create_index('idx_users_phone_lookup', 'users', ['phone_number'], if_not_exists=True)
    
    # Status and filtering indexes
    op.create_index('idx_users_status_active', 'users', ['status', 'deleted_at'], if_not_exists=True)
    op.create_index('idx_users_created_month', 'users', [sa.text("date_trunc('month', created_at)")], if_not_exists=True)
    op.create_index('idx_users_last_login', 'users', ['last_login_at'], if_not_exists=True)
    
    # Composite indexes for common queries
    op.create_index('idx_users_email_status', 'users', ['email', 'status'], if_not_exists=True)
    op.create_index('idx_users_name_search', 'users', ['first_name', 'last_name'], if_not_exists=True)
    
    # Partial indexes for active users
    op.create_index('idx_users_active_recent', 'users', ['last_login_at'], 
                   postgresql_where=sa.text("status = 'active'"), if_not_exists=True)
    
    # ==================== VEHICLES TABLE INDEXES ====================
    logger.info("Creating indexes for vehicles table")
    
    # License plate indexes (critical for lookups)
    op.create_index('idx_vehicles_license_plate_composite', 'vehicles', 
                   ['license_plate', 'license_plate_state'], if_not_exists=True)
    op.create_index('idx_vehicles_license_plate_gin', 'vehicles', 
                   [sa.text("license_plate gin_trgm_ops")], postgresql_using='gin', if_not_exists=True)
    
    # VIN indexes
    op.create_index('idx_vehicles_vin_lookup', 'vehicles', ['vin'], unique=True, if_not_exists=True)
    op.create_index('idx_vehicles_vin_gin', 'vehicles', [sa.text("vin gin_trgm_ops")], 
                   postgresql_using='gin', if_not_exists=True)
    
    # RFID and transponder indexes
    op.create_index('idx_vehicles_rfid_lookup', 'vehicles', ['rfid_tag'], if_not_exists=True)
    op.create_index('idx_vehicles_transponder_lookup', 'vehicles', ['transponder_id'], if_not_exists=True)
    
    # User relationship indexes
    op.create_index('idx_vehicles_user_status', 'vehicles', ['user_id', 'status'], if_not_exists=True)
    op.create_index('idx_vehicles_user_recent', 'vehicles', ['user_id', 'last_parking_at'], if_not_exists=True)
    
    # Status and compliance indexes
    op.create_index('idx_vehicles_compliance', 'vehicles', 
                   ['registration_expiry', 'insurance_expiry', 'inspection_expiry'], if_not_exists=True)
    op.create_index('idx_vehicles_expired', 'vehicles', 
                   ['registration_expiry', 'insurance_expiry'], 
                   postgresql_where=sa.text("status = 'active'"), if_not_exists=True)
    
    # Blacklist and stolen indexes
    op.create_index('idx_vehicles_blacklist', 'vehicles', ['is_blacklisted', 'blacklisted_at'], if_not_exists=True)
    op.create_index('idx_vehicles_stolen', 'vehicles', ['is_stolen', 'stolen_reported_at'], if_not_exists=True)
    
    # Vehicle characteristics indexes
    op.create_index('idx_vehicles_type_make', 'vehicles', ['vehicle_type', 'make_id'], if_not_exists=True)
    op.create_index('idx_vehicles_color_search', 'vehicles', ['color'], if_not_exists=True)
    
    # ==================== PARKING ZONES INDEXES ====================
    logger.info("Creating indexes for parking_zones table")
    
    op.create_index('idx_zones_code_lookup', 'parking_zones', ['code'], unique=True, if_not_exists=True)
    op.create_index('idx_zones_type_active', 'parking_zones', ['zone_type', 'is_active'], if_not_exists=True)
    op.create_index('idx_zones_location', 'parking_zones', ['latitude', 'longitude'], if_not_exists=True)
    op.create_index('idx_zones_floor_section', 'parking_zones', ['floor', 'section'], if_not_exists=True)
    
    # ==================== PARKING SPOTS INDEXES ====================
    logger.info("Creating indexes for parking_spots table")
    
    # Core lookup indexes
    op.create_index('idx_spots_zone_number', 'parking_spots', ['zone_id', 'spot_number'], unique=True, if_not_exists=True)
    op.create_index('idx_spots_status_type', 'parking_spots', ['status', 'spot_type'], if_not_exists=True)
    
    # Current status indexes
    op.create_index('idx_spots_current_occupancy', 'parking_spots', 
                   ['status', 'current_vehicle_id', 'current_session_id'], if_not_exists=True)
    op.create_index('idx_spots_current_reservation', 'parking_spots', ['current_reservation_id'], if_not_exists=True)
    
    # Availability search indexes
    op.create_index('idx_spots_available_search', 'parking_spots', 
                   ['zone_id', 'spot_type', 'status'], 
                   postgresql_where=sa.text("status = 'available'"), if_not_exists=True)
    
    # EV charging indexes
    op.create_index('idx_spots_ev_charger', 'parking_spots', 
                   ['has_ev_charger', 'ev_charger_type'], 
                   postgresql_where=sa.text("has_ev_charger = true"), if_not_exists=True)
    
    # Handicapped spots
    op.create_index('idx_spots_handicapped', 'parking_spots', ['is_handicapped'], 
                   postgresql_where=sa.text("is_handicapped = true"), if_not_exists=True)
    
    # ==================== RESERVATIONS TABLE INDEXES ====================
    logger.info("Creating indexes for reservations table")
    
    # Core lookup indexes
    op.create_index('idx_reservations_number_lookup', 'reservations', ['reservation_number'], unique=True, if_not_exists=True)
    op.create_index('idx_reservations_external_ref', 'reservations', ['external_reference'], if_not_exists=True)
    op.create_index('idx_reservations_qr_code', 'reservations', ['qr_code'], if_not_exists=True)
    
    # Time-based indexes for availability queries
    op.create_index('idx_reservations_time_range', 'reservations', 
                   ['start_time', 'end_time'], if_not_exists=True)
    op.create_index('idx_reservations_active_times', 'reservations', 
                   ['spot_id', 'start_time', 'end_time'], 
                   postgresql_where=sa.text("status IN ('confirmed', 'checked_in')"), if_not_exists=True)
    
    # Status and filtering indexes
    op.create_index('idx_reservations_status_composite', 'reservations', 
                   ['status', 'start_time'], if_not_exists=True)
    op.create_index('idx_reservations_user_status', 'reservations', 
                   ['user_id', 'status', 'start_time'], if_not_exists=True)
    op.create_index('idx_reservations_vehicle_status', 'reservations', 
                   ['vehicle_id', 'status'], if_not_exists=True)
    
    # Check-in/out indexes
    op.create_index('idx_reservations_check_in', 'reservations', 
                   ['actual_check_in', 'status'], if_not_exists=True)
    op.create_index('idx_reservations_check_out', 'reservations', 
                   ['actual_check_out', 'status'], if_not_exists=True)
    
    # Payment related indexes
    op.create_index('idx_reservations_payment', 'reservations', 
                   ['payment_status', 'total_amount'], if_not_exists=True)
    op.create_index('idx_reservations_unpaid', 'reservations', 
                   ['payment_status', 'end_time'], 
                   postgresql_where=sa.text("payment_status != 'paid'"), if_not_exists=True)
    
    # Recurring reservations
    op.create_index('idx_reservations_recurring', 'reservations', 
                   ['is_recurring', 'recurring_id'], if_not_exists=True)
    
    # Guest reservations
    op.create_index('idx_reservations_guest_email', 'reservations', ['guest_email'], if_not_exists=True)
    op.create_index('idx_reservations_guest_phone', 'reservations', ['guest_phone'], if_not_exists=True)
    
    # ==================== PAYMENTS TABLE INDEXES ====================
    logger.info("Creating indexes for payments table")
    
    # Core lookup indexes
    op.create_index('idx_payments_number_lookup', 'payments', ['payment_number'], unique=True, if_not_exists=True)
    op.create_index('idx_payments_external_id', 'payments', ['external_id'], if_not_exists=True)
    op.create_index('idx_payments_provider_id', 'payments', ['provider_payment_id'], if_not_exists=True)
    
    # Relationship indexes
    op.create_index('idx_payments_user_reservation', 'payments', 
                   ['user_id', 'reservation_id'], if_not_exists=True)
    op.create_index('idx_payments_subscription', 'payments', ['subscription_id'], if_not_exists=True)
    
    # Status and time indexes
    op.create_index('idx_payments_status_date', 'payments', 
                   ['status', 'paid_at'], if_not_exists=True)
    op.create_index('idx_payments_date_range', 'payments', 
                   ['created_at', 'paid_at'], if_not_exists=True)
    
    # Amount and currency indexes for reporting
    op.create_index('idx_payments_amount_currency', 'payments', 
                   ['amount', 'currency'], if_not_exists=True)
    op.create_index('idx_payments_daily_revenue', 'payments', 
                   [sa.text("date_trunc('day', paid_at)"), 'currency'], 
                   postgresql_where=sa.text("status = 'paid'"), if_not_exists=True)
    
    # Refund tracking
    op.create_index('idx_payments_refunded', 'payments', 
                   ['amount_refunded'], 
                   postgresql_where=sa.text("amount_refunded > 0"), if_not_exists=True)
    
    # ==================== PARKING SESSIONS TABLE INDEXES ====================
    logger.info("Creating indexes for parking_sessions table")
    
    # Core lookup indexes
    op.create_index('idx_sessions_number_lookup', 'parking_sessions', ['session_number'], unique=True, if_not_exists=True)
    op.create_index('idx_sessions_ticket_number', 'parking_sessions', ['ticket_number'], if_not_exists=True)
    
    # Active sessions
    op.create_index('idx_sessions_active', 'parking_sessions', 
                   ['status', 'start_time'], 
                   postgresql_where=sa.text("status = 'active'"), if_not_exists=True)
    
    # Vehicle tracking
    op.create_index('idx_sessions_vehicle_active', 'parking_sessions', 
                   ['vehicle_id', 'status'], if_not_exists=True)
    op.create_index('idx_sessions_license_active', 'parking_sessions', 
                   ['license_plate', 'status'], if_not_exists=True)
    
    # Spot occupancy
    op.create_index('idx_sessions_spot_active', 'parking_sessions', 
                   ['spot_id', 'status'], if_not_exists=True)
    op.create_index('idx_sessions_spot_history', 'parking_sessions', 
                   ['spot_id', 'start_time', 'end_time'], if_not_exists=True)
    
    # Time-based analytics
    op.create_index('idx_sessions_duration', 'parking_sessions', 
                   ['duration_minutes'], if_not_exists=True)
    op.create_index('idx_sessions_hourly', 'parking_sessions', 
                   [sa.text("date_trunc('hour', start_time)")], if_not_exists=True)
    
    # ==================== VEHICLE VIOLATIONS TABLE INDEXES ====================
    logger.info("Creating indexes for vehicle_violations table")
    
    op.create_index('idx_violations_number_lookup', 'vehicle_violations', ['violation_number'], unique=True, if_not_exists=True)
    op.create_index('idx_violations_vehicle_unpaid', 'vehicle_violations', 
                   ['vehicle_id', 'paid'], if_not_exists=True)
    op.create_index('idx_violations_license_unpaid', 'vehicle_violations', 
                   ['license_plate', 'paid'], if_not_exists=True)
    op.create_index('idx_violations_type_severity', 'vehicle_violations', 
                   ['violation_type', 'severity'], if_not_exists=True)
    op.create_index('idx_violations_date_range', 'vehicle_violations', 
                   ['timestamp'], if_not_exists=True)
    op.create_index('idx_violations_disputed', 'vehicle_violations', 
                   ['disputed', 'dispute_resolved_at'], if_not_exists=True)
    
    # ==================== NOTIFICATIONS TABLE INDEXES ====================
    logger.info("Creating indexes for notifications table")
    
    # Core lookup indexes
    op.create_index('idx_notifications_number_lookup', 'notifications', ['notification_number'], unique=True, if_not_exists=True)
    op.create_index('idx_notifications_tracking', 'notifications', ['tracking_id'], if_not_exists=True)
    op.create_index('idx_notifications_provider_msg', 'notifications', ['provider_message_id'], if_not_exists=True)
    
    # Recipient indexes
    op.create_index('idx_notifications_recipient_email', 'notifications', 
                   ['recipient_email', 'created_at'], if_not_exists=True)
    op.create_index('idx_notifications_recipient_phone', 'notifications', 
                   ['recipient_phone', 'created_at'], if_not_exists=True)
    op.create_index('idx_notifications_user_channel', 'notifications', 
                   ['user_id', 'channel', 'created_at'], if_not_exists=True)
    
    # Status and delivery
    op.create_index('idx_notifications_status_type', 'notifications', 
                   ['status', 'notification_type'], if_not_exists=True)
    op.create_index('idx_notifications_pending', 'notifications', 
                   ['status', 'priority', 'created_at'], 
                   postgresql_where=sa.text("status = 'pending'"), if_not_exists=True)
    op.create_index('idx_notifications_failed', 'notifications', 
                   ['status', 'retry_count', 'next_retry_at'], 
                   postgresql_where=sa.text("status = 'failed'"), if_not_exists=True)
    
    # Engagement tracking
    op.create_index('idx_notifications_opened', 'notifications', 
                   ['opened_at'], 
                   postgresql_where=sa.text("opened_at IS NOT NULL"), if_not_exists=True)
    op.create_index('idx_notifications_clicked', 'notifications', 
                   ['clicked_at'], 
                   postgresql_where=sa.text("clicked_at IS NOT NULL"), if_not_exists=True)
    
    # ==================== NOTIFICATION QUEUE INDEXES ====================
    logger.info("Creating indexes for notification_queue table")
    
    op.create_index('idx_queue_processing', 'notification_queue', 
                   ['scheduled_for', 'locked_until', 'priority'], if_not_exists=True)
    op.create_index('idx_queue_ready', 'notification_queue', 
                   ['scheduled_for'], 
                   postgresql_where=sa.text("scheduled_for <= CURRENT_TIMESTAMP AND locked_until IS NULL"), 
                   if_not_exists=True)
    
    # ==================== AUDIT LOGS INDEXES ====================
    logger.info("Creating indexes for audit_events table")
    
    op.create_index('idx_audit_events_composite_search', 'audit_events', 
                   ['created_at', 'category', 'action', 'user_id'], if_not_exists=True)
    op.create_index('idx_audit_events_resource_search', 'audit_events', 
                   ['resource_type', 'resource_id', 'created_at'], if_not_exists=True)
    op.create_index('idx_audit_events_ip_search', 'audit_events', 
                   ['ip_address', 'created_at'], if_not_exists=True)
    op.create_index('idx_audit_events_security', 'audit_events', 
                   ['severity', 'status', 'created_at'], 
                   postgresql_where=sa.text("severity IN ('ERROR', 'CRITICAL', 'ALERT')"), if_not_exists=True)
    
    # ==================== VEHICLE ACCESS HISTORY INDEXES ====================
    logger.info("Creating indexes for vehicle_access_history table")
    
    op.create_index('idx_access_history_vehicle_time', 'vehicle_access_history', 
                   ['vehicle_id', 'timestamp'], if_not_exists=True)
    op.create_index('idx_access_history_plate_time', 'vehicle_access_history', 
                   ['matched_plate', 'timestamp'], if_not_exists=True)
    op.create_index('idx_access_history_gate_time', 'vehicle_access_history', 
                   ['gate_id', 'timestamp'], if_not_exists=True)
    op.create_index('idx_access_history_denied', 'vehicle_access_history', 
                   ['access_type', 'timestamp'], 
                   postgresql_where=sa.text("access_type = 'denied'"), if_not_exists=True)
    
    # ==================== VEHICLE LOCATION HISTORY INDEXES ====================
    logger.info("Creating indexes for vehicle_location_history table")
    
    op.create_index('idx_location_history_vehicle_time', 'vehicle_location_history', 
                   ['vehicle_id', 'timestamp'], if_not_exists=True)
    op.create_index('idx_location_history_spatial', 'vehicle_location_history', 
                   [sa.text("latitude"), sa.text("longitude")], if_not_exists=True)
    op.create_index('idx_location_history_recent', 'vehicle_location_history', 
                   ['timestamp'], 
                   postgresql_where=sa.text("timestamp > CURRENT_TIMESTAMP - INTERVAL '7 days'"), 
                   if_not_exists=True)
    
    # ==================== DISCOUNT CODES INDEXES ====================
    logger.info("Creating indexes for payment_discount_codes table")
    
    op.create_index('idx_discount_codes_lookup', 'payment_discount_codes', 
                   ['code', 'is_active', 'valid_from', 'valid_to'], if_not_exists=True)
    op.create_index('idx_discount_codes_usage', 'payment_discount_codes', 
                   ['usage_count', 'usage_limit'], 
                   postgresql_where=sa.text("usage_limit IS NOT NULL"), if_not_exists=True)
    
    # ==================== SUBSCRIPTIONS INDEXES ====================
    logger.info("Creating indexes for payment_subscriptions table")
    
    op.create_index('idx_subscriptions_active_renewal', 'payment_subscriptions', 
                   ['status', 'current_period_end'], if_not_exists=True)
    op.create_index('idx_subscriptions_user_active', 'payment_subscriptions', 
                   ['user_id', 'status'], if_not_exists=True)
    op.create_index('idx_subscriptions_provider', 'payment_subscriptions', 
                   ['provider_subscription_id'], if_not_exists=True)
    
    # ==================== JSONB GIN INDEXES ====================
    logger.info("Creating GIN indexes for JSONB columns")
    
    # Users table JSONB indexes
    op.create_index('idx_users_metadata_gin', 'users', ['metadata'], postgresql_using='gin', if_not_exists=True)
    op.create_index('idx_users_preferences_gin', 'users', ['preferences'], postgresql_using='gin', if_not_exists=True)
    
    # Vehicles table JSONB indexes
    op.create_index('idx_vehicles_metadata_gin', 'vehicles', ['metadata'], postgresql_using='gin', if_not_exists=True)
    op.create_index('idx_vehicles_custom_fields_gin', 'vehicles', ['custom_fields'], postgresql_using='gin', if_not_exists=True)
    
    # Reservations table JSONB indexes
    op.create_index('idx_reservations_metadata_gin', 'reservations', ['metadata'], postgresql_using='gin', if_not_exists=True)
    op.create_index('idx_reservations_custom_fields_gin', 'reservations', ['custom_fields'], postgresql_using='gin', if_not_exists=True)
    op.create_index('idx_reservations_addons_gin', 'reservations', ['addons'], postgresql_using='gin', if_not_exists=True)
    
    # Payments table JSONB indexes
    op.create_index('idx_payments_metadata_gin', 'payments', ['metadata'], postgresql_using='gin', if_not_exists=True)
    op.create_index('idx_payments_provider_response_gin', 'payments', ['provider_response'], postgresql_using='gin', if_not_exists=True)
    
    # Notifications table JSONB indexes
    op.create_index('idx_notifications_metadata_gin', 'notifications', ['metadata'], postgresql_using='gin', if_not_exists=True)
    op.create_index('idx_notifications_template_data_gin', 'notifications', ['template_data'], postgresql_using='gin', if_not_exists=True)
    
    # Audit events table JSONB indexes
    op.create_index('idx_audit_events_changes_gin', 'audit_events', ['changes'], postgresql_using='gin', if_not_exists=True)
    op.create_index('idx_audit_events_metadata_gin', 'audit_events', ['metadata'], postgresql_using='gin', if_not_exists=True)
    op.create_index('idx_audit_events_request_gin', 'audit_events', ['request_params', 'request_body'], postgresql_using='gin', if_not_exists=True)
    
    # ==================== FULL-TEXT SEARCH INDEXES ====================
    logger.info("Creating full-text search indexes")
    
    # Enable pg_trgm extension if not exists
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
    
    # Users table search
    op.create_index('idx_users_name_trgm', 'users', 
                   [sa.text("first_name || ' ' || last_name gin_trgm_ops")], 
                   postgresql_using='gin', if_not_exists=True)
    op.create_index('idx_users_email_trgm', 'users', 
                   [sa.text("email gin_trgm_ops")], 
                   postgresql_using='gin', if_not_exists=True)
    
    # Vehicles table search
    op.create_index('idx_vehicles_license_plate_trgm', 'vehicles', 
                   [sa.text("license_plate gin_trgm_ops")], 
                   postgresql_using='gin', if_not_exists=True)
    op.create_index('idx_vehicles_vin_trgm', 'vehicles', 
                   [sa.text("vin gin_trgm_ops")], 
                   postgresql_using='gin', if_not_exists=True)
    
    # ==================== EXPRESSION INDEXES ====================
    logger.info("Creating expression indexes")
    
    # Users - lowercase email for case-insensitive search
    op.create_index('idx_users_email_lower', 'users', 
                   [sa.text("lower(email)")], unique=True, if_not_exists=True)
    
    # Vehicles - lowercase license plate for case-insensitive search
    op.create_index('idx_vehicles_license_plate_lower', 'vehicles', 
                   [sa.text("lower(license_plate)")], if_not_exists=True)
    
    # Reservations - date-only index for daily aggregates
    op.create_index('idx_reservations_start_date', 'reservations', 
                   [sa.text("date_trunc('day', start_time)")], if_not_exists=True)
    
    # Payments - month index for revenue reporting
    op.create_index('idx_payments_paid_month', 'payments', 
                   [sa.text("date_trunc('month', paid_at)")], 
                   postgresql_where=sa.text("status = 'paid'"), if_not_exists=True)
    
    # ==================== PARTIAL INDEXES FOR COMMON QUERIES ====================
    logger.info("Creating partial indexes for common queries")
    
    # Active vehicles with expiring documents
    op.create_index('idx_vehicles_expiring_30_days', 'vehicles', 
                   ['registration_expiry', 'insurance_expiry'], 
                   postgresql_where=sa.text(
                       "status = 'active' AND "
                       "(registration_expiry BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days' "
                       "OR insurance_expiry BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days')"
                   ), if_not_exists=True)
    
    # Current active reservations
    op.create_index('idx_reservations_current', 'reservations', 
                   ['spot_id', 'end_time'], 
                   postgresql_where=sa.text(
                       "status IN ('confirmed', 'checked_in') "
                       "AND start_time <= CURRENT_TIMESTAMP "
                       "AND end_time >= CURRENT_TIMESTAMP"
                   ), if_not_exists=True)
    
    # Upcoming reservations (next 24 hours)
    op.create_index('idx_reservations_upcoming_24h', 'reservations', 
                   ['start_time', 'status'], 
                   postgresql_where=sa.text(
                       "status = 'confirmed' "
                       "AND start_time BETWEEN CURRENT_TIMESTAMP AND CURRENT_TIMESTAMP + INTERVAL '24 hours'"
                   ), if_not_exists=True)
    
    # Overdue payments
    op.create_index('idx_payments_overdue', 'payments', 
                   ['created_at'], 
                   postgresql_where=sa.text(
                       "status = 'pending' "
                       "AND created_at < CURRENT_TIMESTAMP - INTERVAL '7 days'"
                   ), if_not_exists=True)
    
    # Unread notifications
    op.create_index('idx_notifications_unread', 'notifications', 
                   ['user_id', 'created_at'], 
                   postgresql_where=sa.text(
                       "opened_at IS NULL AND status = 'delivered'"
                   ), if_not_exists=True)
    
    # ==================== COVERING INDEXES ====================
    logger.info("Creating covering indexes for frequent queries")
    
    # Covering index for reservation lookup with common fields
    op.create_index('idx_reservations_covering_lookup', 'reservations', 
                   ['reservation_number', 'status', 'start_time', 'end_time', 'user_id', 'spot_id'], 
                   if_not_exists=True)
    
    # Covering index for payment lookup
    op.create_index('idx_payments_covering_lookup', 'payments', 
                   ['payment_number', 'status', 'amount', 'paid_at', 'user_id', 'reservation_id'], 
                   if_not_exists=True)
    
    # Covering index for vehicle lookup
    op.create_index('idx_vehicles_covering_lookup', 'vehicles', 
                   ['license_plate', 'license_plate_state', 'status', 'vehicle_type', 'user_id'], 
                   if_not_exists=True)
    
    # ==================== CONCURRENT INDEX CREATION ====================
    # Note: For production, you might want to create indexes CONCURRENTLY
    # This would need to be done outside of a transaction
    
    logger.info(f"Migration {revision} completed successfully")


def downgrade() -> None:
    """
    Downgrade migration - removes all indexes
    """
    logger.info(f"Starting downgrade of migration {revision}")
    
    # List of all indexes to drop
    indexes_to_drop = [
        # Users table indexes
        'idx_users_email_lookup',
        'idx_users_username_lookup',
        'idx_users_phone_lookup',
        'idx_users_status_active',
        'idx_users_created_month',
        'idx_users_last_login',
        'idx_users_email_status',
        'idx_users_name_search',
        'idx_users_active_recent',
        'idx_users_metadata_gin',
        'idx_users_preferences_gin',
        'idx_users_name_trgm',
        'idx_users_email_trgm',
        'idx_users_email_lower',
        
        # Vehicles table indexes
        'idx_vehicles_license_plate_composite',
        'idx_vehicles_license_plate_gin',
        'idx_vehicles_vin_lookup',
        'idx_vehicles_vin_gin',
        'idx_vehicles_rfid_lookup',
        'idx_vehicles_transponder_lookup',
        'idx_vehicles_user_status',
        'idx_vehicles_user_recent',
        'idx_vehicles_compliance',
        'idx_vehicles_expired',
        'idx_vehicles_blacklist',
        'idx_vehicles_stolen',
        'idx_vehicles_type_make',
        'idx_vehicles_color_search',
        'idx_vehicles_metadata_gin',
        'idx_vehicles_custom_fields_gin',
        'idx_vehicles_license_plate_trgm',
        'idx_vehicles_vin_trgm',
        'idx_vehicles_license_plate_lower',
        'idx_vehicles_expiring_30_days',
        'idx_vehicles_covering_lookup',
        
        # Parking zones indexes
        'idx_zones_code_lookup',
        'idx_zones_type_active',
        'idx_zones_location',
        'idx_zones_floor_section',
        
        # Parking spots indexes
        'idx_spots_zone_number',
        'idx_spots_status_type',
        'idx_spots_current_occupancy',
        'idx_spots_current_reservation',
        'idx_spots_available_search',
        'idx_spots_ev_charger',
        'idx_spots_handicapped',
        
        # Reservations indexes
        'idx_reservations_number_lookup',
        'idx_reservations_external_ref',
        'idx_reservations_qr_code',
        'idx_reservations_time_range',
        'idx_reservations_active_times',
        'idx_reservations_status_composite',
        'idx_reservations_user_status',
        'idx_reservations_vehicle_status',
        'idx_reservations_check_in',
        'idx_reservations_check_out',
        'idx_reservations_payment',
        'idx_reservations_unpaid',
        'idx_reservations_recurring',
        'idx_reservations_guest_email',
        'idx_reservations_guest_phone',
        'idx_reservations_metadata_gin',
        'idx_reservations_custom_fields_gin',
        'idx_reservations_addons_gin',
        'idx_reservations_start_date',
        'idx_reservations_current',
        'idx_reservations_upcoming_24h',
        'idx_reservations_covering_lookup',
        
        # Payments indexes
        'idx_payments_number_lookup',
        'idx_payments_external_id',
        'idx_payments_provider_id',
        'idx_payments_user_reservation',
        'idx_payments_subscription',
        'idx_payments_status_date',
        'idx_payments_date_range',
        'idx_payments_amount_currency',
        'idx_payments_daily_revenue',
        'idx_payments_refunded',
        'idx_payments_metadata_gin',
        'idx_payments_provider_response_gin',
        'idx_payments_paid_month',
        'idx_payments_overdue',
        'idx_payments_covering_lookup',
        
        # Parking sessions indexes
        'idx_sessions_number_lookup',
        'idx_sessions_ticket_number',
        'idx_sessions_active',
        'idx_sessions_vehicle_active',
        'idx_sessions_license_active',
        'idx_sessions_spot_active',
        'idx_sessions_spot_history',
        'idx_sessions_duration',
        'idx_sessions_hourly',
        
        # Vehicle violations indexes
        'idx_violations_number_lookup',
        'idx_violations_vehicle_unpaid',
        'idx_violations_license_unpaid',
        'idx_violations_type_severity',
        'idx_violations_date_range',
        'idx_violations_disputed',
        
        # Notifications indexes
        'idx_notifications_number_lookup',
        'idx_notifications_tracking',
        'idx_notifications_provider_msg',
        'idx_notifications_recipient_email',
        'idx_notifications_recipient_phone',
        'idx_notifications_user_channel',
        'idx_notifications_status_type',
        'idx_notifications_pending',
        'idx_notifications_failed',
        'idx_notifications_opened',
        'idx_notifications_clicked',
        'idx_notifications_metadata_gin',
        'idx_notifications_template_data_gin',
        'idx_notifications_unread',
        
        # Notification queue indexes
        'idx_queue_processing',
        'idx_queue_ready',
        
        # Audit events indexes
        'idx_audit_events_composite_search',
        'idx_audit_events_resource_search',
        'idx_audit_events_ip_search',
        'idx_audit_events_security',
        'idx_audit_events_changes_gin',
        'idx_audit_events_metadata_gin',
        'idx_audit_events_request_gin',
        
        # Vehicle access history indexes
        'idx_access_history_vehicle_time',
        'idx_access_history_plate_time',
        'idx_access_history_gate_time',
        'idx_access_history_denied',
        
        # Vehicle location history indexes
        'idx_location_history_vehicle_time',
        'idx_location_history_spatial',
        'idx_location_history_recent',
        
        # Discount codes indexes
        'idx_discount_codes_lookup',
        'idx_discount_codes_usage',
        
        # Subscriptions indexes
        'idx_subscriptions_active_renewal',
        'idx_subscriptions_user_active',
        'idx_subscriptions_provider',
    ]
    
    # Drop each index if it exists
    for index_name in indexes_to_drop:
        try:
            op.execute(f"DROP INDEX IF EXISTS {index_name}")
            logger.debug(f"Dropped index {index_name}")
        except Exception as e:
            logger.warning(f"Could not drop index {index_name}: {e}")
    
    logger.info(f"Downgrade of migration {revision} completed successfully")


def validate_indexes() -> dict:
    """
    Validate that all indexes were created successfully
    """
    logger.info("Validating indexes")
    
    connection = op.get_bind()
    results = {}
    
    # Query to get all indexes
    indexes = connection.execute("""
        SELECT 
            schemaname,
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname;
    """).fetchall()
    
    results['total_indexes'] = len(indexes)
    
    # Group by table
    tables = {}
    for idx in indexes:
        table = idx.tablename
        if table not in tables:
            tables[table] = []
        tables[table].append(idx.indexname)
    
    results['indexes_by_table'] = {table: len(indices) for table, indices in tables.items()}
    
    # Check for duplicate indexes
    duplicate_check = connection.execute("""
        SELECT 
            tablename,
            indexdef,
            COUNT(*) as count
        FROM pg_indexes
        WHERE schemaname = 'public'
        GROUP BY tablename, indexdef
        HAVING COUNT(*) > 1;
    """).fetchall()
    
    results['duplicate_indexes'] = len(duplicate_check)
    
    # Check for unused indexes (if pg_stat_user_indexes is available)
    try:
        unused = connection.execute("""
            SELECT 
                indexrelid::regclass as index_name,
                idx_scan as scans
            FROM pg_stat_user_indexes
            WHERE idx_scan = 0
            ORDER BY idx_scan;
        """).fetchall()
        
        results['unused_indexes'] = len(unused)
    except:
        results['unused_indexes'] = 'Could not check (pg_stat_user_indexes not available)'
    
    logger.info(f"Validation results: {results}")
    return results


def post_upgrade_hook():
    """Hook to run after successful upgrade"""
    logger.info("Running post-upgrade hooks for indexes migration")
    
    # Validate indexes
    validation_results = validate_indexes()
    
    # Analyze tables to update statistics
    logger.info("Analyzing tables to update statistics")
    op.execute("ANALYZE")
    
    # Log index statistics
    logger.info(f"Total indexes created: {validation_results.get('total_indexes', 0)}")
    
    for table, count in validation_results.get('indexes_by_table', {}).items():
        logger.info(f"  - {table}: {count} indexes")
    
    if validation_results.get('duplicate_indexes', 0) > 0:
        logger.warning(f"Found {validation_results['duplicate_indexes']} potential duplicate indexes")
    
    logger.info("Indexes migration completed successfully")


# Register the post-upgrade hook
if hasattr(op, 'register_post_upgrade_hook'):
    op.register_post_upgrade_hook(post_upgrade_hook)


def add_index_comments():
    """Add comments to indexes for documentation"""
    # This would need to be done through PostgreSQL COMMENT statements
    # Example: COMMENT ON INDEX idx_users_email_lookup IS 'Fast lookup by email address';
    pass