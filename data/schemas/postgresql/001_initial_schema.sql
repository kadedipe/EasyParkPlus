-- 001_initial_schema.sql
-- Initial PostgreSQL schema for Parking Management System
-- This script creates all tables with proper constraints, indexes, and relationships

-- Enable UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable JSONB support (already enabled in PostgreSQL 9.4+)

-- =====================================================
-- ORGANIZATION AND USER MANAGEMENT TABLES
-- =====================================================

-- Organizations table (multi-tenant support)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    tenant_id UUID, -- For multi-tenant support within the same organization
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    tax_id VARCHAR(50),
    website VARCHAR(255),
    logo_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    settings JSONB DEFAULT '{}'::jsonb
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(50),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at TIMESTAMP WITH TIME ZONE,
    last_login_ip VARCHAR(50),
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    preferences JSONB DEFAULT '{}'::jsonb,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL
);

-- Roles table for RBAC
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(500),
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_system_role BOOLEAN NOT NULL DEFAULT FALSE
);

-- User-Role association table
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT uq_user_role_org UNIQUE (user_id, role_id, organization_id)
);

-- =====================================================
-- PARKING INFRASTRUCTURE TABLES
-- =====================================================

-- Parking lots table
CREATE TABLE parking_lots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    tenant_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) NOT NULL,
    description TEXT,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    country VARCHAR(100) NOT NULL,
    postal_code VARCHAR(20),
    latitude FLOAT,
    longitude FLOAT,
    phone VARCHAR(50),
    email VARCHAR(255),
    opening_time TIME,
    closing_time TIME,
    is_24h BOOLEAN NOT NULL DEFAULT FALSE,
    total_spaces INTEGER NOT NULL,
    available_spaces INTEGER NOT NULL,
    reserved_spaces INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(50) NOT NULL DEFAULT 'operational',
    settings JSONB DEFAULT '{}'::jsonb,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    manager_id UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT uq_organization_lot_code UNIQUE (organization_id, code),
    CONSTRAINT check_available_spaces CHECK (available_spaces <= total_spaces AND available_spaces >= 0),
    CONSTRAINT check_reserved_spaces CHECK (reserved_spaces >= 0)
);

-- Parking levels/floors
CREATE TABLE parking_levels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    level_number INTEGER NOT NULL,
    name VARCHAR(100),
    code VARCHAR(50) NOT NULL,
    total_spaces INTEGER NOT NULL,
    available_spaces INTEGER NOT NULL,
    reserved_spaces INTEGER NOT NULL DEFAULT 0,
    height_limit FLOAT,
    weight_limit FLOAT,
    is_covered BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    settings JSONB DEFAULT '{}'::jsonb,
    parking_lot_id UUID NOT NULL REFERENCES parking_lots(id) ON DELETE CASCADE,
    CONSTRAINT uq_lot_level_number UNIQUE (parking_lot_id, level_number),
    CONSTRAINT uq_lot_level_code UNIQUE (parking_lot_id, code),
    CONSTRAINT check_level_available_spaces CHECK (available_spaces <= total_spaces AND available_spaces >= 0),
    CONSTRAINT check_level_reserved_spaces CHECK (reserved_spaces >= 0)
);

-- Individual parking spaces
CREATE TABLE parking_spaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    space_number VARCHAR(50) NOT NULL,
    space_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'available',
    is_covered BOOLEAN NOT NULL DEFAULT FALSE,
    is_reserved BOOLEAN NOT NULL DEFAULT FALSE,
    is_handicapped BOOLEAN NOT NULL DEFAULT FALSE,
    is_electric BOOLEAN NOT NULL DEFAULT FALSE,
    charging_capacity FLOAT,
    width FLOAT,
    length FLOAT,
    height_limit FLOAT,
    current_vehicle_id UUID,
    sensor_id VARCHAR(100),
    notes TEXT,
    settings JSONB DEFAULT '{}'::jsonb,
    level_id UUID NOT NULL REFERENCES parking_levels(id) ON DELETE CASCADE,
    CONSTRAINT uq_level_space_number UNIQUE (level_id, space_number),
    CONSTRAINT check_space_type CHECK (space_type IN ('regular', 'handicapped', 'electric', 'compact', 'motorcycle', 'bus'))
);

-- Entrance/Exit points
CREATE TABLE entrance_exits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) NOT NULL,
    type VARCHAR(20) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    has_gate BOOLEAN NOT NULL DEFAULT TRUE,
    has_camera BOOLEAN NOT NULL DEFAULT TRUE,
    has_ticket_dispenser BOOLEAN NOT NULL DEFAULT FALSE,
    has_payment_terminal BOOLEAN NOT NULL DEFAULT FALSE,
    parking_lot_id UUID NOT NULL REFERENCES parking_lots(id) ON DELETE CASCADE,
    CONSTRAINT uq_lot_entrance_code UNIQUE (parking_lot_id, code),
    CONSTRAINT check_entrance_type CHECK (type IN ('entrance', 'exit', 'both'))
);

-- =====================================================
-- HARDWARE/DEVICES TABLES
-- =====================================================

-- Gates
CREATE TABLE gates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    name VARCHAR(100) NOT NULL,
    gate_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'closed',
    control_mode VARCHAR(50) NOT NULL DEFAULT 'automatic',
    last_activity TIMESTAMP WITH TIME ZONE,
    parking_lot_id UUID NOT NULL REFERENCES parking_lots(id) ON DELETE CASCADE,
    entrance_exit_id UUID REFERENCES entrance_exits(id) ON DELETE SET NULL,
    CONSTRAINT check_gate_type CHECK (gate_type IN ('entrance', 'exit')),
    CONSTRAINT check_gate_status CHECK (status IN ('open', 'closed', 'opening', 'closing', 'maintenance')),
    CONSTRAINT check_control_mode CHECK (control_mode IN ('automatic', 'manual', 'remote'))
);

-- Cameras
CREATE TABLE cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    name VARCHAR(100) NOT NULL,
    camera_type VARCHAR(50) NOT NULL,
    ip_address VARCHAR(50),
    rtsp_url VARCHAR(500),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    last_online TIMESTAMP WITH TIME ZONE,
    settings JSONB DEFAULT '{}'::jsonb,
    parking_lot_id UUID NOT NULL REFERENCES parking_lots(id) ON DELETE CASCADE,
    entrance_exit_id UUID REFERENCES entrance_exits(id) ON DELETE SET NULL,
    CONSTRAINT check_camera_type CHECK (camera_type IN ('entrance', 'exit', 'overview', 'lpr'))
);

-- Sensors
CREATE TABLE sensors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    sensor_id VARCHAR(100) NOT NULL UNIQUE,
    sensor_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    battery_level INTEGER,
    last_reading TIMESTAMP WITH TIME ZONE,
    firmware_version VARCHAR(50),
    settings JSONB DEFAULT '{}'::jsonb,
    parking_lot_id UUID NOT NULL REFERENCES parking_lots(id) ON DELETE CASCADE,
    current_space_id UUID REFERENCES parking_spaces(id) ON DELETE SET NULL,
    CONSTRAINT check_sensor_type CHECK (sensor_type IN ('ultrasonic', 'magnetic', 'camera', 'radar')),
    CONSTRAINT check_battery_level CHECK (battery_level BETWEEN 0 AND 100)
);

-- Sensor data readings
CREATE TABLE sensor_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    value FLOAT NOT NULL,
    unit VARCHAR(20),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    is_occupied BOOLEAN,
    sensor_id UUID NOT NULL REFERENCES sensors(id) ON DELETE CASCADE,
    parking_space_id UUID REFERENCES parking_spaces(id) ON DELETE SET NULL
);

-- =====================================================
-- VEHICLE MANAGEMENT TABLES
-- =====================================================

-- Vehicles
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    license_plate VARCHAR(20) NOT NULL,
    license_plate_normalized VARCHAR(20) NOT NULL,
    license_plate_state VARCHAR(50),
    license_plate_country VARCHAR(3),
    make VARCHAR(100),
    model VARCHAR(100),
    color VARCHAR(50),
    year INTEGER,
    vehicle_type VARCHAR(50) NOT NULL DEFAULT 'car',
    height FLOAT,
    length FLOAT,
    width FLOAT,
    weight FLOAT,
    is_electric BOOLEAN NOT NULL DEFAULT FALSE,
    is_handicapped BOOLEAN NOT NULL DEFAULT FALSE,
    is_resident BOOLEAN NOT NULL DEFAULT FALSE,
    registration_number VARCHAR(100),
    registration_expiry DATE,
    insurance_company VARCHAR(200),
    insurance_policy VARCHAR(100),
    insurance_expiry DATE,
    image_url VARCHAR(500),
    notes TEXT,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT uq_org_license_plate UNIQUE (organization_id, license_plate),
    CONSTRAINT check_vehicle_type CHECK (vehicle_type IN ('car', 'motorcycle', 'truck', 'bus', 'van'))
);

-- Blacklisted vehicles
CREATE TABLE blacklisted_vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    tenant_id UUID NOT NULL,
    license_plate VARCHAR(20) NOT NULL,
    license_plate_normalized VARCHAR(20) NOT NULL,
    reason VARCHAR(500) NOT NULL,
    blacklist_type VARCHAR(50) NOT NULL DEFAULT 'permanent',
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    parking_lot_id UUID REFERENCES parking_lots(id) ON DELETE CASCADE,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE CASCADE,
    added_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT uq_org_blacklist_plate UNIQUE (organization_id, license_plate_normalized),
    CONSTRAINT check_blacklist_type CHECK (blacklist_type IN ('temporary', 'permanent'))
);

-- =====================================================
-- PRICING AND BILLING TABLES
-- =====================================================

-- Parking rates
CREATE TABLE rates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    tenant_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    rate_type VARCHAR(50) NOT NULL,
    vehicle_types JSONB NOT NULL,
    time_rules JSONB,
    base_rate FLOAT NOT NULL,
    rate_unit VARCHAR(20) NOT NULL DEFAULT 'hour',
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    tiers JSONB,
    flat_amount FLOAT,
    max_duration INTEGER,
    grace_period_minutes INTEGER NOT NULL DEFAULT 15,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_weekend_rate BOOLEAN NOT NULL DEFAULT FALSE,
    is_holiday_rate BOOLEAN NOT NULL DEFAULT FALSE,
    is_special_event_rate BOOLEAN NOT NULL DEFAULT FALSE,
    valid_from DATE,
    valid_to DATE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    parking_lot_id UUID REFERENCES parking_lots(id) ON DELETE CASCADE,
    CONSTRAINT check_rate_type CHECK (rate_type IN ('hourly', 'daily', 'weekly', 'monthly', 'flat', 'progressive')),
    CONSTRAINT check_rate_unit CHECK (rate_unit IN ('hour', 'minute', 'day', 'week', 'month')),
    CONSTRAINT check_base_rate_positive CHECK (base_rate >= 0),
    CONSTRAINT check_flat_amount_positive CHECK (flat_amount >= 0)
);

-- Payments
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    payment_number VARCHAR(100) NOT NULL UNIQUE,
    transaction_id VARCHAR(200),
    amount FLOAT NOT NULL,
    tax_amount FLOAT,
    tip_amount FLOAT,
    total_amount FLOAT NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    payment_time TIMESTAMP WITH TIME ZONE,
    card_last_four VARCHAR(4),
    card_brand VARCHAR(50),
    card_expiry VARCHAR(10),
    authorization_code VARCHAR(200),
    response_code VARCHAR(50),
    response_message VARCHAR(500),
    refund_amount FLOAT,
    refund_time TIMESTAMP WITH TIME ZONE,
    refund_reason VARCHAR(500),
    refund_transaction_id VARCHAR(200),
    parking_session_id UUID,
    reservation_id UUID,
    processed_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT check_payment_amounts CHECK (total_amount >= amount AND total_amount >= 0),
    CONSTRAINT check_payment_method CHECK (payment_method IN ('cash', 'credit_card', 'debit_card', 'mobile_payment'))
);

-- =====================================================
-- PARKING OPERATIONS TABLES
-- =====================================================

-- Parking sessions
CREATE TABLE parking_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    session_id VARCHAR(100) NOT NULL UNIQUE,
    ticket_number VARCHAR(100) UNIQUE,
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_time TIMESTAMP WITH TIME ZONE,
    expected_exit_time TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    is_grace_period BOOLEAN NOT NULL DEFAULT FALSE,
    grace_period_ends TIMESTAMP WITH TIME ZONE,
    entry_method VARCHAR(50) NOT NULL,
    entry_gate_id UUID,
    entry_camera_id UUID,
    entry_image_url VARCHAR(500),
    entry_lpr_confidence FLOAT,
    entry_lpr_plate VARCHAR(20),
    exit_method VARCHAR(50),
    exit_gate_id UUID,
    exit_camera_id UUID,
    exit_image_url VARCHAR(500),
    exit_lpr_confidence FLOAT,
    exit_lpr_plate VARCHAR(20),
    rate_id UUID,
    rate_applied JSONB,
    base_amount FLOAT,
    tax_amount FLOAT,
    discount_amount FLOAT,
    total_amount FLOAT,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    payment_time TIMESTAMP WITH TIME ZONE,
    payment_method VARCHAR(50),
    parking_lot_id UUID NOT NULL REFERENCES parking_lots(id) ON DELETE CASCADE,
    parking_space_id UUID REFERENCES parking_spaces(id) ON DELETE SET NULL,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE SET NULL,
    reservation_id UUID,
    created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ended_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT check_session_status CHECK (status IN ('active', 'completed', 'cancelled', 'expired')),
    CONSTRAINT check_entry_method CHECK (entry_method IN ('ticket', 'rfid', 'lpr', 'mobile')),
    CONSTRAINT check_exit_time CHECK (exit_time IS NULL OR exit_time >= entry_time)
);

-- Reservations
CREATE TABLE reservations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    reservation_number VARCHAR(100) NOT NULL UNIQUE,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    check_in_time TIMESTAMP WITH TIME ZONE,
    check_out_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) NOT NULL DEFAULT 'confirmed',
    cancellation_time TIMESTAMP WITH TIME ZONE,
    cancellation_reason VARCHAR(500),
    customer_name VARCHAR(200) NOT NULL,
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),
    vehicle_license_plate VARCHAR(20) NOT NULL,
    rate_id UUID,
    rate_applied JSONB,
    base_amount FLOAT NOT NULL,
    tax_amount FLOAT,
    discount_amount FLOAT,
    total_amount FLOAT NOT NULL,
    deposit_amount FLOAT,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending',
    payment_time TIMESTAMP WITH TIME ZONE,
    parking_lot_id UUID NOT NULL REFERENCES parking_lots(id) ON DELETE CASCADE,
    parking_space_id UUID REFERENCES parking_spaces(id) ON DELETE SET NULL,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT check_reservation_status CHECK (status IN ('confirmed', 'checked_in', 'completed', 'cancelled', 'no_show')),
    CONSTRAINT check_reservation_times CHECK (end_time > start_time)
);

-- Add foreign key for parking_session_id in payments after both tables exist
ALTER TABLE payments 
    ADD CONSTRAINT fk_payments_parking_session 
    FOREIGN KEY (parking_session_id) REFERENCES parking_sessions(id) ON DELETE SET NULL,
    ADD CONSTRAINT fk_payments_reservation 
    FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE SET NULL;

-- Add foreign key for reservation_id in parking_sessions
ALTER TABLE parking_sessions 
    ADD CONSTRAINT fk_parking_sessions_reservation 
    FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE SET NULL;

-- =====================================================
-- MONITORING AND EVENTS TABLES
-- =====================================================

-- Camera events
CREATE TABLE camera_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    image_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    confidence FLOAT,
    metadata JSONB,
    detected_plate VARCHAR(20),
    plate_confidence FLOAT,
    plate_image_url VARCHAR(500),
    camera_id UUID NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    parking_session_id UUID REFERENCES parking_sessions(id) ON DELETE SET NULL,
    vehicle_id UUID REFERENCES vehicles(id) ON DELETE SET NULL,
    CONSTRAINT check_event_type CHECK (event_type IN ('motion', 'lpr', 'object_detected'))
);

-- Camera images
CREATE TABLE camera_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    image_type VARCHAR(50) NOT NULL,
    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    format VARCHAR(20),
    camera_id UUID NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    event_id UUID REFERENCES camera_events(id) ON DELETE SET NULL,
    CONSTRAINT check_image_type CHECK (image_type IN ('full', 'cropped', 'thumbnail'))
);

-- Gate events
CREATE TABLE gate_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    event_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    result VARCHAR(50) NOT NULL,
    error_message TEXT,
    trigger_method VARCHAR(50) NOT NULL,
    metadata JSONB,
    gate_id UUID NOT NULL REFERENCES gates(id) ON DELETE CASCADE,
    triggered_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT check_gate_event_type CHECK (event_type IN ('open', 'close', 'open_request', 'close_request', 'error')),
    CONSTRAINT check_gate_result CHECK (result IN ('success', 'failure')),
    CONSTRAINT check_trigger_method CHECK (trigger_method IN ('manual', 'automatic', 'remote', 'sensor'))
);

-- =====================================================
-- NOTIFICATIONS AND LOGGING TABLES
-- =====================================================

-- Notifications
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT check_notification_type CHECK (notification_type IN ('email', 'sms', 'push', 'in_app')),
    CONSTRAINT check_priority CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    CONSTRAINT check_notification_status CHECK (status IN ('pending', 'sent', 'delivered', 'read', 'failed'))
);

-- Activity logs (audit trail)
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    old_values TEXT,
    new_values TEXT,
    user_agent VARCHAR(500),
    ip_address VARCHAR(50),
    request_id VARCHAR(100),
    details JSONB,
    session_id VARCHAR(100),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Organizations indexes
CREATE INDEX ix_organizations_created_at ON organizations(created_at);
CREATE INDEX ix_organizations_updated_at ON organizations(updated_at);
CREATE INDEX ix_organizations_deleted_at ON organizations(deleted_at);
CREATE INDEX ix_organizations_tenant_id ON organizations(tenant_id);
CREATE INDEX ix_organizations_code ON organizations(code);
CREATE INDEX ix_organizations_is_active ON organizations(is_active);

-- Users indexes
CREATE INDEX ix_users_created_at ON users(created_at);
CREATE INDEX ix_users_updated_at ON users(updated_at);
CREATE INDEX ix_users_deleted_at ON users(deleted_at);
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_username ON users(username);
CREATE INDEX ix_users_organization_id ON users(organization_id);
CREATE INDEX ix_users_is_active ON users(is_active);

-- Roles indexes
CREATE INDEX ix_roles_created_at ON roles(created_at);
CREATE INDEX ix_roles_updated_at ON roles(updated_at);
CREATE INDEX ix_roles_deleted_at ON roles(deleted_at);
CREATE INDEX ix_roles_name ON roles(name);

-- User roles indexes
CREATE INDEX ix_user_roles_created_at ON user_roles(created_at);
CREATE INDEX ix_user_roles_updated_at ON user_roles(updated_at);
CREATE INDEX ix_user_roles_deleted_at ON user_roles(deleted_at);
CREATE INDEX ix_user_roles_user_id ON user_roles(user_id);
CREATE INDEX ix_user_roles_role_id ON user_roles(role_id);
CREATE INDEX ix_user_roles_organization_id ON user_roles(organization_id);

-- Parking lots indexes
CREATE INDEX ix_parking_lots_created_at ON parking_lots(created_at);
CREATE INDEX ix_parking_lots_updated_at ON parking_lots(updated_at);
CREATE INDEX ix_parking_lots_deleted_at ON parking_lots(deleted_at);
CREATE INDEX ix_parking_lots_tenant_id ON parking_lots(tenant_id);
CREATE INDEX ix_parking_lots_code ON parking_lots(code);
CREATE INDEX ix_parking_lots_status ON parking_lots(status);
CREATE INDEX ix_parking_lots_city ON parking_lots(city);
CREATE INDEX ix_parking_lots_state ON parking_lots(state);
CREATE INDEX ix_parking_lots_country ON parking_lots(country);
CREATE INDEX ix_parking_lots_organization_id ON parking_lots(organization_id);
CREATE INDEX ix_parking_lots_manager_id ON parking_lots(manager_id);

-- Parking levels indexes
CREATE INDEX ix_parking_levels_created_at ON parking_levels(created_at);
CREATE INDEX ix_parking_levels_updated_at ON parking_levels(updated_at);
CREATE INDEX ix_parking_levels_deleted_at ON parking_levels(deleted_at);
CREATE INDEX ix_parking_levels_parking_lot_id ON parking_levels(parking_lot_id);
CREATE INDEX ix_parking_levels_code ON parking_levels(code);

-- Parking spaces indexes
CREATE INDEX ix_parking_spaces_created_at ON parking_spaces(created_at);
CREATE INDEX ix_parking_spaces_updated_at ON parking_spaces(updated_at);
CREATE INDEX ix_parking_spaces_deleted_at ON parking_spaces(deleted_at);
CREATE INDEX ix_parking_spaces_status ON parking_spaces(status);
CREATE INDEX ix_parking_spaces_type ON parking_spaces(space_type);
CREATE INDEX ix_parking_spaces_sensor_id ON parking_spaces(sensor_id);
CREATE INDEX ix_parking_spaces_level_id ON parking_spaces(level_id);

-- Entrance exits indexes
CREATE INDEX ix_entrance_exits_created_at ON entrance_exits(created_at);
CREATE INDEX ix_entrance_exits_updated_at ON entrance_exits(updated_at);
CREATE INDEX ix_entrance_exits_deleted_at ON entrance_exits(deleted_at);
CREATE INDEX ix_entrance_exits_parking_lot_id ON entrance_exits(parking_lot_id);
CREATE INDEX ix_entrance_exits_code ON entrance_exits(code);

-- Gates indexes
CREATE INDEX ix_gates_created_at ON gates(created_at);
CREATE INDEX ix_gates_updated_at ON gates(updated_at);
CREATE INDEX ix_gates_deleted_at ON gates(deleted_at);
CREATE INDEX ix_gates_parking_lot_id ON gates(parking_lot_id);
CREATE INDEX ix_gates_entrance_exit_id ON gates(entrance_exit_id);
CREATE INDEX ix_gates_status ON gates(status);

-- Cameras indexes
CREATE INDEX ix_cameras_created_at ON cameras(created_at);
CREATE INDEX ix_cameras_updated_at ON cameras(updated_at);
CREATE INDEX ix_cameras_deleted_at ON cameras(deleted_at);
CREATE INDEX ix_cameras_parking_lot_id ON cameras(parking_lot_id);
CREATE INDEX ix_cameras_entrance_exit_id ON cameras(entrance_exit_id);
CREATE INDEX ix_cameras_status ON cameras(status);

-- Sensors indexes
CREATE INDEX ix_sensors_created_at ON sensors(created_at);
CREATE INDEX ix_sensors_updated_at ON sensors(updated_at);
CREATE INDEX ix_sensors_deleted_at ON sensors(deleted_at);
CREATE INDEX ix_sensors_sensor_id ON sensors(sensor_id);
CREATE INDEX ix_sensors_parking_lot_id ON sensors(parking_lot_id);
CREATE INDEX ix_sensors_current_space_id ON sensors(current_space_id);
CREATE INDEX ix_sensors_status ON sensors(status);

-- Sensor data indexes
CREATE INDEX ix_sensor_data_created_at ON sensor_data(created_at);
CREATE INDEX ix_sensor_data_updated_at ON sensor_data(updated_at);
CREATE INDEX ix_sensor_data_deleted_at ON sensor_data(deleted_at);
CREATE INDEX ix_sensor_data_timestamp ON sensor_data(timestamp);
CREATE INDEX ix_sensor_data_sensor_timestamp ON sensor_data(sensor_id, timestamp);
CREATE INDEX ix_sensor_data_parking_space_id ON sensor_data(parking_space_id);

-- Vehicles indexes
CREATE INDEX ix_vehicles_created_at ON vehicles(created_at);
CREATE INDEX ix_vehicles_updated_at ON vehicles(updated_at);
CREATE INDEX ix_vehicles_deleted_at ON vehicles(deleted_at);
CREATE INDEX ix_vehicles_license_plate ON vehicles(license_plate);
CREATE INDEX ix_vehicles_license_plate_normalized ON vehicles(license_plate_normalized);
CREATE INDEX ix_vehicles_owner_id ON vehicles(owner_id);
CREATE INDEX ix_vehicles_type ON vehicles(vehicle_type);
CREATE INDEX ix_vehicles_organization_id ON vehicles(organization_id);

-- Blacklisted vehicles indexes
CREATE INDEX ix_blacklisted_vehicles_created_at ON blacklisted_vehicles(created_at);
CREATE INDEX ix_blacklisted_vehicles_updated_at ON blacklisted_vehicles(updated_at);
CREATE INDEX ix_blacklisted_vehicles_deleted_at ON blacklisted_vehicles(deleted_at);
CREATE INDEX ix_blacklisted_vehicles_tenant_id ON blacklisted_vehicles(tenant_id);
CREATE INDEX ix_blacklisted_vehicles_license_plate_normalized ON blacklisted_vehicles(license_plate_normalized);
CREATE INDEX ix_blacklisted_vehicles_plate_lot ON blacklisted_vehicles(license_plate_normalized, parking_lot_id);
CREATE INDEX ix_blacklisted_vehicles_organization_id ON blacklisted_vehicles(organization_id);
CREATE INDEX ix_blacklisted_vehicles_parking_lot_id ON blacklisted_vehicles(parking_lot_id);
CREATE INDEX ix_blacklisted_vehicles_vehicle_id ON blacklisted_vehicles(vehicle_id);
CREATE INDEX ix_blacklisted_vehicles_is_active ON blacklisted_vehicles(is_active);

-- Rates indexes
CREATE INDEX ix_rates_created_at ON rates(created_at);
CREATE INDEX ix_rates_updated_at ON rates(updated_at);
CREATE INDEX ix_rates_deleted_at ON rates(deleted_at);
CREATE INDEX ix_rates_tenant_id ON rates(tenant_id);
CREATE INDEX ix_rates_organization_active ON rates(organization_id, is_active);
CREATE INDEX ix_rates_validity ON rates(valid_from, valid_to);
CREATE INDEX ix_rates_parking_lot_id ON rates(parking_lot_id);

-- Payments indexes
CREATE INDEX ix_payments_created_at ON payments(created_at);
CREATE INDEX ix_payments_updated_at ON payments(updated_at);
CREATE INDEX ix_payments_deleted_at ON payments(deleted_at);
CREATE INDEX ix_payments_payment_number ON payments(payment_number);
CREATE INDEX ix_payments_transaction_id ON payments(transaction_id);
CREATE INDEX ix_payments_session ON payments(parking_session_id);
CREATE INDEX ix_payments_reservation ON payments(reservation_id);
CREATE INDEX ix_payments_payment_status ON payments(payment_status);
CREATE INDEX ix_payments_payment_time ON payments(payment_time);
CREATE INDEX ix_payments_processed_by_id ON payments(processed_by_id);

-- Parking sessions indexes
CREATE INDEX ix_parking_sessions_created_at ON parking_sessions(created_at);
CREATE INDEX ix_parking_sessions_updated_at ON parking_sessions(updated_at);
CREATE INDEX ix_parking_sessions_deleted_at ON parking_sessions(deleted_at);
CREATE INDEX ix_parking_sessions_session_id ON parking_sessions(session_id);
CREATE INDEX ix_parking_sessions_ticket_number ON parking_sessions(ticket_number);
CREATE INDEX ix_parking_sessions_entry_time ON parking_sessions(entry_time);
CREATE INDEX ix_parking_sessions_status ON parking_sessions(status);
CREATE INDEX ix_parking_sessions_lot_status ON parking_sessions(parking_lot_id, status);
CREATE INDEX ix_parking_sessions_vehicle ON parking_sessions(vehicle_id, entry_time);
CREATE INDEX ix_parking_sessions_date_range ON parking_sessions(entry_time, exit_time);
CREATE INDEX ix_parking_sessions_parking_space_id ON parking_sessions(parking_space_id);
CREATE INDEX ix_parking_sessions_reservation_id ON parking_sessions(reservation_id);
CREATE INDEX ix_parking_sessions_created_by_id ON parking_sessions(created_by_id);
CREATE INDEX ix_parking_sessions_ended_by_id ON parking_sessions(ended_by_id);

-- Reservations indexes
CREATE INDEX ix_reservations_created_at ON reservations(created_at);
CREATE INDEX ix_reservations_updated_at ON reservations(updated_at);
CREATE INDEX ix_reservations_deleted_at ON reservations(deleted_at);
CREATE INDEX ix_reservations_reservation_number ON reservations(reservation_number);
CREATE INDEX ix_reservations_start_time ON reservations(start_time);
CREATE INDEX ix_reservations_end_time ON reservations(end_time);
CREATE INDEX ix_reservations_status ON reservations(status);
CREATE INDEX ix_reservations_lot_time_range ON reservations(parking_lot_id, start_time, end_time);
CREATE INDEX ix_reservations_space_time ON reservations(parking_space_id, start_time, end_time);
CREATE INDEX ix_reservations_user ON reservations(user_id, start_time);
CREATE INDEX ix_reservations_vehicle_id ON reservations(vehicle_id);

-- Camera events indexes
CREATE INDEX ix_camera_events_created_at ON camera_events(created_at);
CREATE INDEX ix_camera_events_updated_at ON camera_events(updated_at);
CREATE INDEX ix_camera_events_deleted_at ON camera_events(deleted_at);
CREATE INDEX ix_camera_events_timestamp ON camera_events(timestamp);
CREATE INDEX ix_camera_events_camera_time ON camera_events(camera_id, timestamp);
CREATE INDEX ix_camera_events_plate ON camera_events(detected_plate);
CREATE INDEX ix_camera_events_parking_session_id ON camera_events(parking_session_id);
CREATE INDEX ix_camera_events_vehicle_id ON camera_events(vehicle_id);

-- Camera images indexes
CREATE INDEX ix_camera_images_created_at ON camera_images(created_at);
CREATE INDEX ix_camera_images_updated_at ON camera_images(updated_at);
CREATE INDEX ix_camera_images_deleted_at ON camera_images(deleted_at);
CREATE INDEX ix_camera_images_timestamp ON camera_images(timestamp);
CREATE INDEX ix_camera_images_camera_time ON camera_images(camera_id, timestamp);
CREATE INDEX ix_camera_images_event_id ON camera_images(event_id);

-- Gate events indexes
CREATE INDEX ix_gate_events_created_at ON gate_events(created_at);
CREATE INDEX ix_gate_events_updated_at ON gate_events(updated_at);
CREATE INDEX ix_gate_events_deleted_at ON gate_events(deleted_at);
CREATE INDEX ix_gate_events_timestamp ON gate_events(timestamp);
CREATE INDEX ix_gate_events_gate_time ON gate_events(gate_id, timestamp);
CREATE INDEX ix_gate_events_triggered_by_id ON gate_events(triggered_by_id);

-- Notifications indexes
CREATE INDEX ix_notifications_created_at ON notifications(created_at);
CREATE INDEX ix_notifications_updated_at ON notifications(updated_at);
CREATE INDEX ix_notifications_deleted_at ON notifications(deleted_at);
CREATE INDEX ix_notifications_type ON notifications(notification_type);
CREATE INDEX ix_notifications_user_status ON notifications(user_id, status);
CREATE INDEX ix_notifications_priority ON notifications(priority);
CREATE INDEX ix_notifications_status ON notifications(status);

-- Activity logs indexes
CREATE INDEX ix_activity_logs_created_at ON activity_logs(created_at);
CREATE INDEX ix_activity_logs_updated_at ON activity_logs(updated_at);
CREATE INDEX ix_activity_logs_deleted_at ON activity_logs(deleted_at);
CREATE INDEX ix_activity_logs_action ON activity_logs(action);
CREATE INDEX ix_activity_logs_entity_type ON activity_logs(entity_type);
CREATE INDEX ix_activity_logs_entity_id ON activity_logs(entity_id);
CREATE INDEX ix_activity_logs_user_time ON activity_logs(user_id, created_at);
CREATE INDEX ix_activity_logs_entity ON activity_logs(entity_type, entity_id);
CREATE INDEX ix_activity_logs_action_time ON activity_logs(action, created_at);
CREATE INDEX ix_activity_logs_request_id ON activity_logs(request_id);

-- =====================================================
-- FUNCTIONS AND TRIGGERS
-- =====================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for all tables to update updated_at
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND table_name NOT LIKE 'pg_%'
    LOOP
        EXECUTE format('
            CREATE TRIGGER update_%I_updated_at
                BEFORE UPDATE ON %I
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        ', t, t);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to increment version on update
CREATE OR REPLACE FUNCTION increment_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for all tables to increment version
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND table_name NOT LIKE 'pg_%'
    LOOP
        EXECUTE format('
            CREATE TRIGGER increment_%I_version
                BEFORE UPDATE ON %I
                FOR EACH ROW
                EXECUTE FUNCTION increment_version();
        ', t, t);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to update parking space status based on sensor data
CREATE OR REPLACE FUNCTION update_parking_space_from_sensor()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_occupied IS NOT NULL THEN
        UPDATE parking_spaces 
        SET status = CASE 
            WHEN NEW.is_occupied = true THEN 'occupied'
            ELSE 'available'
        END,
        updated_at = CURRENT_TIMESTAMP,
        version = version + 1
        WHERE id = NEW.parking_space_id;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_space_from_sensor
    AFTER INSERT ON sensor_data
    FOR EACH ROW
    EXECUTE FUNCTION update_parking_space_from_sensor();

-- Function to update parking lot available spaces
CREATE OR REPLACE FUNCTION update_parking_lot_available_spaces()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' OR TG_OP = 'UPDATE' THEN
        IF NEW.status = 'occupied' AND (OLD IS NULL OR OLD.status != 'occupied') THEN
            UPDATE parking_levels 
            SET available_spaces = available_spaces - 1,
                version = version + 1
            WHERE id = NEW.level_id;
            
            UPDATE parking_lots 
            SET available_spaces = available_spaces - 1,
                version = version + 1
            WHERE id = (SELECT parking_lot_id FROM parking_levels WHERE id = NEW.level_id);
        ELSIF NEW.status = 'available' AND OLD.status = 'occupied' THEN
            UPDATE parking_levels 
            SET available_spaces = available_spaces + 1,
                version = version + 1
            WHERE id = NEW.level_id;
            
            UPDATE parking_lots 
            SET available_spaces = available_spaces + 1,
                version = version + 1
            WHERE id = (SELECT parking_lot_id FROM parking_levels WHERE id = NEW.level_id);
        END IF;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_lot_spaces
    AFTER INSERT OR UPDATE OF status ON parking_spaces
    FOR EACH ROW
    EXECUTE FUNCTION update_parking_lot_available_spaces();

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================

COMMENT ON TABLE organizations IS 'Organizations/tenants using the parking management system';
COMMENT ON TABLE users IS 'System users with authentication details';
COMMENT ON TABLE roles IS 'Roles for role-based access control';
COMMENT ON TABLE user_roles IS 'Many-to-many relationship between users and roles';
COMMENT ON TABLE parking_lots IS 'Parking facilities managed by organizations';
COMMENT ON TABLE parking_levels IS 'Levels/floors within parking lots';
COMMENT ON TABLE parking_spaces IS 'Individual parking spots with type and status';
COMMENT ON TABLE entrance_exits IS 'Entry and exit points of parking lots';
COMMENT ON TABLE gates IS 'Physical gate controllers';
COMMENT ON TABLE cameras IS 'Surveillance and LPR cameras';
COMMENT ON TABLE sensors IS 'Parking occupancy sensors';
COMMENT ON TABLE sensor_data IS 'Historical sensor readings';
COMMENT ON TABLE vehicles IS 'Vehicle registry with details';
COMMENT ON TABLE blacklisted_vehicles IS 'Vehicles banned from parking';
COMMENT ON TABLE rates IS 'Parking rate configurations';
COMMENT ON TABLE payments IS 'Payment transactions';
COMMENT ON TABLE parking_sessions IS 'Active and historical parking sessions';
COMMENT ON TABLE reservations IS 'Advance parking bookings';
COMMENT ON TABLE camera_events IS 'Events detected by cameras';
COMMENT ON TABLE camera_images IS 'Images captured by cameras';
COMMENT ON TABLE gate_events IS 'Gate open/close events';
COMMENT ON TABLE notifications IS 'User notifications';
COMMENT ON TABLE activity_logs IS 'Audit trail of system activities';

-- =====================================================
-- INITIAL DATA (OPTIONAL)
-- =====================================================

-- Insert default system roles
INSERT INTO roles (id, name, description, permissions, is_system_role, created_by) VALUES
    (uuid_generate_v7(), 'super_admin', 'Super administrator with full system access', 
     '["*"]'::jsonb, TRUE, NULL),
    (uuid_generate_v7(), 'org_admin', 'Organization administrator', 
     '["users:read", "users:write", "parking:read", "parking:write", "reports:read", "settings:write"]'::jsonb, 
     TRUE, NULL),
    (uuid_generate_v7(), 'parking_attendant', 'Parking lot attendant', 
     '["parking:read", "parking:write", "sessions:read", "sessions:write", "payments:read"]'::jsonb, 
     TRUE, NULL),
    (uuid_generate_v7(), 'finance_user', 'Finance department user', 
     '["payments:read", "payments:write", "reports:read", "reports:export"]'::jsonb, 
     TRUE, NULL),
    (uuid_generate_v7(), 'auditor', 'Auditor with read-only access', 
     '["*:read"]'::jsonb, TRUE, NULL),
    (uuid_generate_v7(), 'resident', 'Parking resident', 
     '["vehicles:read", "vehicles:write", "reservations:read", "reservations:write", "payments:read"]'::jsonb, 
     TRUE, NULL);

-- Create a function to generate UUID v7 (time-ordered UUIDs)
CREATE OR REPLACE FUNCTION uuid_generate_v7()
RETURNS UUID
AS $$
BEGIN
  RETURN uuid_generate_v7(); -- Uses pgcrypto extension
END;
$$ LANGUAGE plpgsql;

COMMIT;