-- Parking Management System Database Schema
-- Initialize database with tables, indexes, and initial data

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('user', 'admin', 'operator')),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    INDEX idx_users_email (email),
    INDEX idx_users_role (role)
);

-- Parking lots table
CREATE TABLE parking_lots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    total_spaces INTEGER NOT NULL,
    available_spaces INTEGER NOT NULL,
    hourly_rate DECIMAL(10,2) NOT NULL,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_parking_lots_location (latitude, longitude),
    INDEX idx_parking_lots_active (is_active)
);

-- Parking spaces table
CREATE TABLE parking_spaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parking_lot_id UUID REFERENCES parking_lots(id) ON DELETE CASCADE,
    space_number VARCHAR(50) NOT NULL,
    space_type VARCHAR(50) DEFAULT 'regular' CHECK (space_type IN ('regular', 'disabled', 'ev_charging', 'reserved')),
    is_available BOOLEAN DEFAULT TRUE,
    sensor_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(parking_lot_id, space_number),
    INDEX idx_parking_spaces_lot (parking_lot_id),
    INDEX idx_parking_spaces_available (is_available)
);

-- Reservations table
CREATE TABLE reservations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    parking_space_id UUID REFERENCES parking_spaces(id) ON DELETE CASCADE,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'cancelled', 'no_show')),
    total_amount DECIMAL(10,2),
    payment_status VARCHAR(50) DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'refunded', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_time > start_time),
    INDEX idx_reservations_user (user_id),
    INDEX idx_reservations_time (start_time, end_time),
    INDEX idx_reservations_status (status)
);

-- Payments table
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reservation_id UUID REFERENCES reservations(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    payment_method VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(255) UNIQUE,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'refunded')),
    gateway_response JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_payments_user (user_id),
    INDEX idx_payments_status (status),
    INDEX idx_payments_created (created_at)
);

-- Notifications table
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('email', 'sms', 'push')),
    subject VARCHAR(255),
    message TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'delivered')),
    sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_notifications_user (user_id),
    INDEX idx_notifications_status (status),
    INDEX idx_notifications_created (created_at)
);

-- Sensor data table
CREATE TABLE sensor_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    parking_space_id UUID REFERENCES parking_spaces(id) ON DELETE CASCADE,
    sensor_id VARCHAR(100) NOT NULL,
    is_occupied BOOLEAN NOT NULL,
    battery_level INTEGER,
    signal_strength INTEGER,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_sensor_data_space (parking_space_id),
    INDEX idx_sensor_data_time (recorded_at),
    INDEX idx_sensor_data_occupied (is_occupied)
);

-- Create admin user (password: Admin123!)
INSERT INTO users (email, password_hash, first_name, last_name, role, is_verified)
VALUES (
    'admin@parking.com',
    crypt('Admin123!', gen_salt('bf')),
    'System',
    'Administrator',
    'admin',
    TRUE
);

-- Create function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parking_lots_updated_at BEFORE UPDATE ON parking_lots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parking_spaces_updated_at BEFORE UPDATE ON parking_spaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reservations_updated_at BEFORE UPDATE ON reservations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create view for available parking spaces
CREATE VIEW available_parking_spaces AS
SELECT 
    ps.*,
    pl.name as parking_lot_name,
    pl.address,
    pl.hourly_rate
FROM parking_spaces ps
JOIN parking_lots pl ON ps.parking_lot_id = pl.id
WHERE ps.is_available = TRUE
AND pl.is_active = TRUE;

-- Create materialized view for parking lot statistics
CREATE MATERIALIZED VIEW parking_lot_stats AS
SELECT 
    pl.id,
    pl.name,
    COUNT(ps.id) as total_spaces,
    SUM(CASE WHEN ps.is_available THEN 1 ELSE 0 END) as available_spaces,
    pl.hourly_rate
FROM parking_lots pl
LEFT JOIN parking_spaces ps ON pl.id = ps.parking_lot_id
GROUP BY pl.id, pl.name, pl.hourly_rate;

-- Create index on materialized view
CREATE UNIQUE INDEX idx_parking_lot_stats_id ON parking_lot_stats(id);

-- Refresh materialized view function
CREATE OR REPLACE FUNCTION refresh_parking_lot_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY parking_lot_stats;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO parking_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO parking_user;