-- 003_add_triggers.sql
-- Advanced triggers for parking management system
-- Handles data validation, audit logging, and business logic automation

-- =====================================================
-- UTILITY FUNCTIONS
-- =====================================================

-- Function to get current user ID from session (if applicable)
-- This would need to be integrated with your application's session management
CREATE OR REPLACE FUNCTION get_current_user_id()
RETURNS UUID AS $$
BEGIN
    -- This is a placeholder - in practice, you'd get this from a session variable
    -- For example, using a custom GUC setting:
    -- RETURN current_setting('app.current_user_id', TRUE)::UUID;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Function to get client IP address
CREATE OR REPLACE FUNCTION get_client_ip()
RETURNS TEXT AS $$
BEGIN
    -- Placeholder - implement based on your application
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- AUDIT TRIGGERS
-- =====================================================

-- Generic audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_function()
RETURNS TRIGGER AS $$
DECLARE
    v_old_values JSONB;
    v_new_values JSONB;
    v_user_id UUID;
    v_entity_type TEXT;
    v_action TEXT;
BEGIN
    -- Get current user
    v_user_id := get_current_user_id();
    
    -- Determine entity type from table name
    v_entity_type := TG_TABLE_NAME;
    
    IF TG_OP = 'INSERT' THEN
        v_action := 'INSERT';
        v_new_values := to_jsonb(NEW);
        v_old_values := NULL;
        
        INSERT INTO activity_logs (
            action,
            entity_type,
            entity_id,
            old_values,
            new_values,
            user_agent,
            ip_address,
            request_id,
            details,
            user_id,
            created_by,
            updated_by
        ) VALUES (
            v_action,
            v_entity_type,
            NEW.id,
            v_old_values,
            v_new_values,
            NULL, -- Would come from application context
            get_client_ip(),
            NULL, -- Would come from application context
            jsonb_build_object('schema', TG_TABLE_SCHEMA, 'operation', TG_OP),
            v_user_id,
            v_user_id,
            v_user_id
        );
        
    ELSIF TG_OP = 'UPDATE' THEN
        -- Only log if important fields changed
        IF NEW != OLD THEN
            v_action := 'UPDATE';
            v_old_values := to_jsonb(OLD);
            v_new_values := to_jsonb(NEW);
            
            INSERT INTO activity_logs (
                action,
                entity_type,
                entity_id,
                old_values,
                new_values,
                user_agent,
                ip_address,
                request_id,
                details,
                user_id,
                created_by,
                updated_by
            ) VALUES (
                v_action,
                v_entity_type,
                NEW.id,
                v_old_values,
                v_new_values,
                NULL,
                get_client_ip(),
                NULL,
                jsonb_build_object(
                    'changed_fields', (
                        SELECT jsonb_object_agg(key, value)
                        FROM jsonb_each(v_new_values)
                        WHERE v_old_values ? key 
                        AND v_old_values->>key != v_new_values->>key
                    ),
                    'schema', TG_TABLE_SCHEMA
                ),
                v_user_id,
                v_user_id,
                v_user_id
            );
        END IF;
        
    ELSIF TG_OP = 'DELETE' THEN
        v_action := 'DELETE';
        v_old_values := to_jsonb(OLD);
        v_new_values := NULL;
        
        INSERT INTO activity_logs (
            action,
            entity_type,
            entity_id,
            old_values,
            new_values,
            user_agent,
            ip_address,
            request_id,
            details,
            user_id,
            created_by,
            updated_by
        ) VALUES (
            v_action,
            v_entity_type,
            OLD.id,
            v_old_values,
            v_new_values,
            NULL,
            get_client_ip(),
            NULL,
            jsonb_build_object('schema', TG_TABLE_SCHEMA),
            v_user_id,
            v_user_id,
            v_user_id
        );
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers to main tables
CREATE TRIGGER audit_organizations_trigger
    AFTER INSERT OR UPDATE OR DELETE ON organizations
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_users_trigger
    AFTER INSERT OR UPDATE OR DELETE ON users
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_parking_lots_trigger
    AFTER INSERT OR UPDATE OR DELETE ON parking_lots
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_parking_sessions_trigger
    AFTER INSERT OR UPDATE OR DELETE ON parking_sessions
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_payments_trigger
    AFTER INSERT OR UPDATE OR DELETE ON payments
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

CREATE TRIGGER audit_vehicles_trigger
    AFTER INSERT OR UPDATE OR DELETE ON vehicles
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_function();

-- =====================================================
-- DATA VALIDATION TRIGGERS
-- =====================================================

-- Validate parking session before insert/update
CREATE OR REPLACE FUNCTION validate_parking_session()
RETURNS TRIGGER AS $$
DECLARE
    v_space_status VARCHAR(50);
    v_active_sessions INTEGER;
    v_lot_capacity INTEGER;
BEGIN
    -- Check if space exists and is available
    IF NEW.parking_space_id IS NOT NULL THEN
        SELECT status INTO v_space_status
        FROM parking_spaces
        WHERE id = NEW.parking_space_id;
        
        IF v_space_status != 'available' AND TG_OP = 'INSERT' THEN
            RAISE EXCEPTION 'Parking space % is not available (status: %)', 
                NEW.parking_space_id, v_space_status;
        END IF;
        
        -- Check if vehicle already has active session
        IF NEW.vehicle_id IS NOT NULL THEN
            SELECT COUNT(*) INTO v_active_sessions
            FROM parking_sessions
            WHERE vehicle_id = NEW.vehicle_id 
                AND status = 'active'
                AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::UUID);
            
            IF v_active_sessions > 0 THEN
                RAISE EXCEPTION 'Vehicle % already has an active parking session', 
                    NEW.vehicle_id;
            END IF;
        END IF;
    END IF;
    
    -- Validate entry/exit times
    IF NEW.exit_time IS NOT NULL AND NEW.exit_time <= NEW.entry_time THEN
        RAISE EXCEPTION 'Exit time must be after entry time';
    END IF;
    
    -- Validate grace period
    IF NEW.is_grace_period AND NEW.grace_period_ends IS NULL THEN
        RAISE EXCEPTION 'Grace period end time must be set when grace period is active';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_parking_session_trigger
    BEFORE INSERT OR UPDATE ON parking_sessions
    FOR EACH ROW EXECUTE FUNCTION validate_parking_session();

-- Validate reservation before insert/update
CREATE OR REPLACE FUNCTION validate_reservation()
RETURNS TRIGGER AS $$
DECLARE
    v_overlapping_reservations INTEGER;
    v_active_sessions INTEGER;
BEGIN
    -- Check for overlapping reservations for the same space
    IF NEW.parking_space_id IS NOT NULL THEN
        SELECT COUNT(*) INTO v_overlapping_reservations
        FROM reservations
        WHERE parking_space_id = NEW.parking_space_id
            AND status IN ('confirmed', 'checked_in')
            AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::UUID)
            AND tstzrange(NEW.start_time, NEW.end_time) && 
                tstzrange(start_time, end_time);
        
        IF v_overlapping_reservations > 0 THEN
            RAISE EXCEPTION 'Parking space % already has overlapping reservations', 
                NEW.parking_space_id;
        END IF;
    END IF;
    
    -- Validate check-in time
    IF NEW.check_in_time IS NOT NULL THEN
        IF NEW.check_in_time < NEW.start_time THEN
            RAISE EXCEPTION 'Check-in time cannot be before reservation start time';
        END IF;
        
        IF NEW.check_in_time > NEW.end_time THEN
            RAISE EXCEPTION 'Check-in time cannot be after reservation end time';
        END IF;
    END IF;
    
    -- Validate check-out time
    IF NEW.check_out_time IS NOT NULL THEN
        IF NEW.check_out_time > NEW.end_time THEN
            RAISE EXCEPTION 'Check-out time cannot be after reservation end time';
        END IF;
        
        IF NEW.check_in_time IS NOT NULL AND 
           NEW.check_out_time <= NEW.check_in_time THEN
            RAISE EXCEPTION 'Check-out time must be after check-in time';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_reservation_trigger
    BEFORE INSERT OR UPDATE ON reservations
    FOR EACH ROW EXECUTE FUNCTION validate_reservation();

-- =====================================================
-- BUSINESS LOGIC TRIGGERS
-- =====================================================

-- Update parking space status based on session changes
CREATE OR REPLACE FUNCTION update_space_from_session()
RETURNS TRIGGER AS $$
BEGIN
    -- Session started
    IF TG_OP = 'INSERT' AND NEW.status = 'active' THEN
        UPDATE parking_spaces 
        SET status = 'occupied',
            current_vehicle_id = NEW.vehicle_id,
            updated_at = CURRENT_TIMESTAMP,
            version = version + 1
        WHERE id = NEW.parking_space_id;
        
    -- Session ended
    ELSIF TG_OP = 'UPDATE' AND OLD.status = 'active' AND NEW.status = 'completed' THEN
        UPDATE parking_spaces 
        SET status = 'available',
            current_vehicle_id = NULL,
            updated_at = CURRENT_TIMESTAMP,
            version = version + 1
        WHERE id = NEW.parking_space_id;
        
    -- Session cancelled
    ELSIF TG_OP = 'UPDATE' AND OLD.status = 'active' AND NEW.status = 'cancelled' THEN
        UPDATE parking_spaces 
        SET status = 'available',
            current_vehicle_id = NULL,
            updated_at = CURRENT_TIMESTAMP,
            version = version + 1
        WHERE id = NEW.parking_space_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_space_from_session_trigger
    AFTER INSERT OR UPDATE OF status ON parking_sessions
    FOR EACH ROW
    WHEN (NEW.parking_space_id IS NOT NULL)
    EXECUTE FUNCTION update_space_from_session();

-- Calculate parking session duration and amount on exit
CREATE OR REPLACE FUNCTION calculate_session_billing()
RETURNS TRIGGER AS $$
DECLARE
    v_duration_minutes INTEGER;
    v_rate_record RECORD;
    v_base_amount FLOAT;
BEGIN
    -- Only calculate when session is being completed
    IF NEW.status = 'completed' AND OLD.status = 'active' THEN
        -- Calculate duration
        NEW.duration_minutes := EXTRACT(EPOCH FROM (NEW.exit_time - NEW.entry_time)) / 60;
        
        -- Get applicable rate
        IF NEW.rate_id IS NOT NULL THEN
            SELECT * INTO v_rate_record
            FROM rates
            WHERE id = NEW.rate_id AND is_active = true;
            
            -- Calculate amount based on rate type
            IF v_rate_record.rate_type = 'hourly' THEN
                NEW.base_amount := CEIL(NEW.duration_minutes / 60.0) * v_rate_record.base_rate;
            ELSIF v_rate_record.rate_type = 'flat' THEN
                NEW.base_amount := v_rate_record.flat_amount;
            ELSIF v_rate_record.rate_type = 'progressive' THEN
                -- Progressive rate calculation logic
                -- This is simplified - you'd need more complex logic here
                NEW.base_amount := v_rate_record.base_rate * CEIL(NEW.duration_minutes / 60.0);
            END IF;
            
            -- Apply taxes (assuming 10% tax rate - make configurable)
            NEW.tax_amount := NEW.base_amount * 0.10;
            NEW.total_amount := NEW.base_amount + COALESCE(NEW.tax_amount, 0) - COALESCE(NEW.discount_amount, 0);
            
            -- Store rate snapshot
            NEW.rate_applied := to_jsonb(v_rate_record);
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_session_billing_trigger
    BEFORE UPDATE OF status ON parking_sessions
    FOR EACH ROW
    WHEN (NEW.status = 'completed' AND OLD.status = 'active')
    EXECUTE FUNCTION calculate_session_billing();

-- Update parking lot statistics
CREATE OR REPLACE FUNCTION update_parking_lot_stats()
RETURNS TRIGGER AS $$
DECLARE
    v_lot_id UUID;
BEGIN
    -- Get lot ID from space or directly
    IF TG_TABLE_NAME = 'parking_spaces' THEN
        SELECT parking_lot_id INTO v_lot_id
        FROM parking_levels
        WHERE id = NEW.level_id;
    ELSE
        v_lot_id := NEW.parking_lot_id;
    END IF;
    
    -- Update lot statistics
    WITH lot_stats AS (
        SELECT
            COUNT(DISTINCT ps.id) FILTER (WHERE ps.status = 'active') as active_sessions,
            COUNT(DISTINCT r.id) FILTER (WHERE r.status IN ('confirmed', 'checked_in')) as active_reservations,
            COALESCE(SUM(p.total_amount) FILTER (WHERE p.payment_status = 'completed' AND p.payment_time >= CURRENT_DATE), 0) as today_revenue
        FROM parking_lots pl
        LEFT JOIN parking_sessions ps ON pl.id = ps.parking_lot_id
        LEFT JOIN reservations r ON pl.id = r.parking_lot_id
        LEFT JOIN payments p ON ps.id = p.parking_session_id
        WHERE pl.id = v_lot_id
        GROUP BY pl.id
    )
    UPDATE parking_lots
    SET 
        available_spaces = total_spaces - reserved_spaces - COALESCE(lot_stats.active_sessions, 0),
        settings = settings || jsonb_build_object(
            'stats', jsonb_build_object(
                'active_sessions', COALESCE(lot_stats.active_sessions, 0),
                'active_reservations', COALESCE(lot_stats.active_reservations, 0),
                'today_revenue', COALESCE(lot_stats.today_revenue, 0),
                'last_updated', CURRENT_TIMESTAMP
            )
        ),
        updated_at = CURRENT_TIMESTAMP,
        version = version + 1
    FROM lot_stats
    WHERE id = v_lot_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_lot_stats_from_session
    AFTER INSERT OR UPDATE OF status ON parking_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_parking_lot_stats();

CREATE TRIGGER update_lot_stats_from_reservation
    AFTER INSERT OR UPDATE OF status ON reservations
    FOR EACH ROW
    EXECUTE FUNCTION update_parking_lot_stats();

-- =====================================================
-- NOTIFICATION TRIGGERS
-- =====================================================

-- Create notifications for important events
CREATE OR REPLACE FUNCTION create_session_notifications()
RETURNS TRIGGER AS $$
DECLARE
    v_user_id UUID;
    v_message TEXT;
BEGIN
    -- Notify when session is about to expire (if expected exit time set)
    IF NEW.expected_exit_time IS NOT NULL 
       AND NEW.expected_exit_time - INTERVAL '15 minutes' <= CURRENT_TIMESTAMP
       AND NEW.expected_exit_time > CURRENT_TIMESTAMP
       AND NEW.status = 'active' THEN
        
        -- Get vehicle owner if exists
        SELECT owner_id INTO v_user_id
        FROM vehicles
        WHERE id = NEW.vehicle_id;
        
        IF v_user_id IS NOT NULL THEN
            v_message := format(
                'Your parking session for vehicle will expire in 15 minutes at %s',
                to_char(NEW.expected_exit_time, 'HH24:MI')
            );
            
            INSERT INTO notifications (
                notification_type,
                title,
                content,
                priority,
                status,
                user_id,
                created_by,
                updated_by
            ) VALUES (
                'push',
                'Parking Session Expiring Soon',
                v_message,
                'normal',
                'pending',
                v_user_id,
                get_current_user_id(),
                get_current_user_id()
            );
        END IF;
    END IF;
    
    -- Notify when session completed
    IF NEW.status = 'completed' AND OLD.status = 'active' AND NEW.total_amount IS NOT NULL THEN
        SELECT owner_id INTO v_user_id
        FROM vehicles
        WHERE id = NEW.vehicle_id;
        
        IF v_user_id IS NOT NULL THEN
            v_message := format(
                'Your parking session has ended. Total amount: %s %s',
                NEW.total_amount,
                NEW.currency
            );
            
            INSERT INTO notifications (
                notification_type,
                title,
                content,
                priority,
                status,
                user_id,
                created_by,
                updated_by
            ) VALUES (
                'push',
                'Parking Session Completed',
                v_message,
                'low',
                'pending',
                v_user_id,
                get_current_user_id(),
                get_current_user_id()
            );
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_session_notifications_trigger
    AFTER INSERT OR UPDATE ON parking_sessions
    FOR EACH ROW
    EXECUTE FUNCTION create_session_notifications();

-- Create notifications for reservations
CREATE OR REPLACE FUNCTION create_reservation_notifications()
RETURNS TRIGGER AS $$
DECLARE
    v_message TEXT;
BEGIN
    -- Notify for upcoming reservations
    IF NEW.status = 'confirmed' 
       AND NEW.start_time - INTERVAL '1 hour' <= CURRENT_TIMESTAMP
       AND NEW.start_time > CURRENT_TIMESTAMP THEN
        
        v_message := format(
            'Your reservation at %s starts in 1 hour',
            to_char(NEW.start_time, 'HH24:MI')
        );
        
        INSERT INTO notifications (
            notification_type,
            title,
            content,
            priority,
            status,
            user_id,
            created_by,
            updated_by
        ) VALUES (
            'push',
            'Upcoming Reservation',
            v_message,
            'normal',
            'pending',
            NEW.user_id,
            get_current_user_id(),
            get_current_user_id()
        );
    END IF;
    
    -- Notify for reservation check-in
    IF NEW.status = 'checked_in' AND OLD.status = 'confirmed' THEN
        INSERT INTO notifications (
            notification_type,
            title,
            content,
            priority,
            status,
            user_id,
            created_by,
            updated_by
        ) VALUES (
            'push',
            'Reservation Check-in',
            'You have successfully checked in to your reservation',
            'low',
            'pending',
            NEW.user_id,
            get_current_user_id(),
            get_current_user_id()
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_reservation_notifications_trigger
    AFTER INSERT OR UPDATE ON reservations
    FOR EACH ROW
    EXECUTE FUNCTION create_reservation_notifications();

-- =====================================================
-- BLACKLIST CHECK TRIGGERS
-- =====================================================

-- Check if vehicle is blacklisted before allowing entry
CREATE OR REPLACE FUNCTION check_vehicle_blacklist()
RETURNS TRIGGER AS $$
DECLARE
    v_blacklisted RECORD;
BEGIN
    -- Check if vehicle is blacklisted
    SELECT * INTO v_blacklisted
    FROM blacklisted_vehicles
    WHERE (vehicle_id = NEW.vehicle_id OR license_plate_normalized = (
        SELECT license_plate_normalized FROM vehicles WHERE id = NEW.vehicle_id
    ))
    AND is_active = true
    AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP);
    
    IF v_blacklisted.id IS NOT NULL THEN
        -- Log blacklist attempt
        INSERT INTO activity_logs (
            action,
            entity_type,
            entity_id,
            details,
            user_id,
            created_by,
            updated_by
        ) VALUES (
            'BLACKLIST_ATTEMPT',
            'parking_sessions',
            NEW.id,
            jsonb_build_object(
                'reason', v_blacklisted.reason,
                'blacklist_type', v_blacklisted.blacklist_type,
                'license_plate', v_blacklisted.license_plate
            ),
            get_current_user_id(),
            get_current_user_id(),
            get_current_user_id()
        );
        
        -- Prevent entry
        RAISE EXCEPTION 'Vehicle is blacklisted: %', v_blacklisted.reason;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_vehicle_blacklist_trigger
    BEFORE INSERT ON parking_sessions
    FOR EACH ROW
    WHEN (NEW.vehicle_id IS NOT NULL)
    EXECUTE FUNCTION check_vehicle_blacklist();

-- =====================================================
-- CAPACITY MANAGEMENT TRIGGERS
-- =====================================================

-- Prevent overbooking
CREATE OR REPLACE FUNCTION check_parking_capacity()
RETURNS TRIGGER AS $$
DECLARE
    v_lot_id UUID;
    v_total_spaces INTEGER;
    v_occupied_spaces INTEGER;
BEGIN
    -- Get lot ID
    IF TG_TABLE_NAME = 'parking_sessions' THEN
        v_lot_id := NEW.parking_lot_id;
    ELSIF TG_TABLE_NAME = 'reservations' THEN
        v_lot_id := NEW.parking_lot_id;
    END IF;
    
    -- Check capacity
    SELECT total_spaces INTO v_total_spaces
    FROM parking_lots
    WHERE id = v_lot_id;
    
    SELECT COUNT(*) INTO v_occupied_spaces
    FROM parking_sessions
    WHERE parking_lot_id = v_lot_id AND status = 'active';
    
    IF v_occupied_spaces >= v_total_spaces THEN
        RAISE EXCEPTION 'Parking lot is at full capacity';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_parking_capacity_session_trigger
    BEFORE INSERT ON parking_sessions
    FOR EACH ROW
    EXECUTE FUNCTION check_parking_capacity();

-- =====================================================
-- RATE MANAGEMENT TRIGGERS
-- =====================================================

-- Validate rate configuration
CREATE OR REPLACE FUNCTION validate_rate_config()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate rate type specific fields
    IF NEW.rate_type = 'flat' AND NEW.flat_amount IS NULL THEN
        RAISE EXCEPTION 'Flat rate type requires flat_amount to be set';
    END IF;
    
    IF NEW.rate_type = 'progressive' AND NEW.tiers IS NULL THEN
        RAISE EXCEPTION 'Progressive rate type requires tiers to be set';
    END IF;
    
    -- Validate date ranges
    IF NEW.valid_from IS NOT NULL AND NEW.valid_to IS NOT NULL 
       AND NEW.valid_from > NEW.valid_to THEN
        RAISE EXCEPTION 'Valid from date must be before valid to date';
    END IF;
    
    -- Ensure at least one vehicle type is specified
    IF jsonb_array_length(NEW.vehicle_types) = 0 THEN
        RAISE EXCEPTION 'At least one vehicle type must be specified';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_rate_config_trigger
    BEFORE INSERT OR UPDATE ON rates
    FOR EACH ROW EXECUTE FUNCTION validate_rate_config();

-- =====================================================
-- PAYMENT PROCESSING TRIGGERS
-- =====================================================

-- Validate and process payments
CREATE OR REPLACE FUNCTION process_payment()
RETURNS TRIGGER AS $$
DECLARE
    v_session RECORD;
BEGIN
    -- Update payment status timestamp
    IF NEW.payment_status = 'completed' AND OLD.payment_status != 'completed' THEN
        NEW.payment_time := CURRENT_TIMESTAMP;
        
        -- Update related parking session payment status
        IF NEW.parking_session_id IS NOT NULL THEN
            UPDATE parking_sessions
            SET payment_status = 'paid',
                payment_method = NEW.payment_method,
                payment_time = NEW.payment_time,
                updated_at = CURRENT_TIMESTAMP,
                version = version + 1
            WHERE id = NEW.parking_session_id;
        END IF;
        
        -- Update related reservation payment status
        IF NEW.reservation_id IS NOT NULL THEN
            UPDATE reservations
            SET payment_status = 'paid',
                payment_time = NEW.payment_time,
                updated_at = CURRENT_TIMESTAMP,
                version = version + 1
            WHERE id = NEW.reservation_id;
        END IF;
    END IF;
    
    -- Handle refunds
    IF NEW.refund_amount IS NOT NULL AND NEW.refund_time IS NULL THEN
        NEW.refund_time := CURRENT_TIMESTAMP;
        
        -- Log refund activity
        INSERT INTO activity_logs (
            action,
            entity_type,
            entity_id,
            details,
            user_id,
            created_by,
            updated_by
        ) VALUES (
            'REFUND',
            'payments',
            NEW.id,
            jsonb_build_object(
                'refund_amount', NEW.refund_amount,
                'refund_reason', NEW.refund_reason,
                'original_amount', NEW.total_amount
            ),
            get_current_user_id(),
            get_current_user_id(),
            get_current_user_id()
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER process_payment_trigger
    BEFORE UPDATE OF payment_status, refund_amount ON payments
    FOR EACH ROW
    EXECUTE FUNCTION process_payment();

-- =====================================================
-- MAINTENANCE AND CLEANUP TRIGGERS
-- =====================================================

-- Automatically expire no-show reservations
CREATE OR REPLACE FUNCTION expire_no_show_reservations()
RETURNS TRIGGER AS $$
BEGIN
    -- If reservation start time has passed and not checked in, mark as no-show
    IF NEW.start_time < CURRENT_TIMESTAMP 
       AND NEW.status = 'confirmed' 
       AND NEW.check_in_time IS NULL THEN
        NEW.status := 'no_show';
        NEW.updated_at := CURRENT_TIMESTAMP;
        NEW.version := NEW.version + 1;
        
        -- Release the parking space
        IF NEW.parking_space_id IS NOT NULL THEN
            UPDATE parking_spaces
            SET status = 'available',
                updated_at = CURRENT_TIMESTAMP,
                version = version + 1
            WHERE id = NEW.parking_space_id;
        END IF;
        
        -- Notify user
        INSERT INTO notifications (
            notification_type,
            title,
            content,
            priority,
            status,
            user_id,
            created_by,
            updated_by
        ) VALUES (
            'push',
            'Reservation Expired',
            'Your reservation has expired due to no-show',
            'normal',
            'pending',
            NEW.user_id,
            get_current_user_id(),
            get_current_user_id()
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER expire_no_show_reservations_trigger
    BEFORE UPDATE ON reservations
    FOR EACH ROW
    EXECUTE FUNCTION expire_no_show_reservations();

-- =====================================================
-- DATA INTEGRITY TRIGGERS
-- =====================================================

-- Ensure referential integrity for soft deletes
CREATE OR REPLACE FUNCTION check_soft_delete_references()
RETURNS TRIGGER AS $$
BEGIN
    -- When an organization is soft-deleted, also soft-delete related records
    IF TG_TABLE_NAME = 'organizations' AND NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL THEN
        UPDATE users SET deleted_at = NEW.deleted_at, updated_by = get_current_user_id()
        WHERE organization_id = NEW.id AND deleted_at IS NULL;
        
        UPDATE parking_lots SET deleted_at = NEW.deleted_at, updated_by = get_current_user_id()
        WHERE organization_id = NEW.id AND deleted_at IS NULL;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_soft_delete_references_trigger
    AFTER UPDATE OF deleted_at ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION check_soft_delete_references();

-- =====================================================
-- STATISTICS AND METRICS TRIGGERS
-- =====================================================

-- Update vehicle statistics
CREATE OR REPLACE FUNCTION update_vehicle_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE vehicles
        SET settings = settings || jsonb_build_object(
            'stats', jsonb_build_object(
                'total_sessions', 1,
                'last_session_date', CURRENT_TIMESTAMP,
                'total_paid', 0
            )
        )
        WHERE id = NEW.vehicle_id;
    ELSIF TG_OP = 'UPDATE' AND NEW.status = 'completed' AND OLD.status = 'active' THEN
        UPDATE vehicles
        SET settings = jsonb_set(
            settings,
            '{stats,total_sessions}',
            to_jsonb(COALESCE((settings->'stats'->>'total_sessions')::INTEGER, 0) + 1)
        )
        WHERE id = NEW.vehicle_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_vehicle_stats_trigger
    AFTER INSERT OR UPDATE ON parking_sessions
    FOR EACH ROW
    WHEN (NEW.vehicle_id IS NOT NULL)
    EXECUTE FUNCTION update_vehicle_stats();

-- =====================================================
-- ENCRYPTION AND DATA PROTECTION TRIGGERS
-- =====================================================

-- Mask sensitive data in logs
CREATE OR REPLACE FUNCTION mask_sensitive_data()
RETURNS TRIGGER AS $$
BEGIN
    -- Mask credit card numbers in activity logs
    IF TG_TABLE_NAME = 'activity_logs' AND NEW.entity_type = 'payments' THEN
        IF NEW.old_values IS NOT NULL AND NEW.old_values ? 'card_last_four' THEN
            NEW.old_values := NEW.old_values - 'card_last_four';
        END IF;
        
        IF NEW.new_values IS NOT NULL AND NEW.new_values ? 'card_last_four' THEN
            NEW.new_values := NEW.new_values - 'card_last_four';
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER mask_sensitive_data_trigger
    BEFORE INSERT ON activity_logs
    FOR EACH ROW
    EXECUTE FUNCTION mask_sensitive_data();

-- =====================================================
-- COMPLEX BUSINESS RULES TRIGGERS
-- =====================================================

-- Apply dynamic pricing based on demand
CREATE OR REPLACE FUNCTION apply_dynamic_pricing()
RETURNS TRIGGER AS $$
DECLARE
    v_occupancy_rate FLOAT;
    v_dynamic_multiplier FLOAT := 1.0;
BEGIN
    -- Calculate current occupancy rate
    SELECT (COUNT(*)::FLOAT / total_spaces) INTO v_occupancy_rate
    FROM parking_sessions ps
    CROSS JOIN parking_lots pl
    WHERE ps.parking_lot_id = NEW.parking_lot_id 
        AND ps.status = 'active'
    GROUP BY pl.total_spaces;
    
    -- Apply dynamic pricing based on occupancy
    IF v_occupancy_rate > 0.8 THEN
        v_dynamic_multiplier := 1.5; -- 50% surge pricing
    ELSIF v_occupancy_rate > 0.6 THEN
        v_dynamic_multiplier := 1.2; -- 20% increase
    ELSIF v_occupancy_rate < 0.3 THEN
        v_dynamic_multiplier := 0.8; -- 20% discount
    END IF;
    
    -- Apply multiplier to base rate
    IF NEW.rate_id IS NOT NULL THEN
        UPDATE rates
        SET base_rate = base_rate * v_dynamic_multiplier,
            updated_at = CURRENT_TIMESTAMP,
            version = version + 1
        WHERE id = NEW.rate_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: This trigger is commented out as it's an advanced feature
-- CREATE TRIGGER apply_dynamic_pricing_trigger
--     AFTER UPDATE OF status ON parking_sessions
--     FOR EACH ROW
--     WHEN (NEW.status = 'active')
--     EXECUTE FUNCTION apply_dynamic_pricing();

-- =====================================================
-- ERROR HANDLING AND LOGGING
-- =====================================================

-- Log trigger errors
CREATE OR REPLACE FUNCTION log_trigger_error()
RETURNS TRIGGER AS $$
BEGIN
    -- This is a wrapper that catches and logs errors from other triggers
    -- It would be used in combination with other triggers
    RETURN NEW;
EXCEPTION WHEN OTHERS THEN
    INSERT INTO activity_logs (
        action,
        entity_type,
        entity_id,
        details,
        created_by,
        updated_by
    ) VALUES (
        'TRIGGER_ERROR',
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        jsonb_build_object(
            'error', SQLERRM,
            'state', SQLSTATE,
            'trigger', TG_NAME,
            'operation', TG_OP
        ),
        get_current_user_id(),
        get_current_user_id()
    );
    
    RAISE;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGER STATUS AND MONITORING
-- =====================================================

-- Create view to monitor trigger status
CREATE OR REPLACE VIEW v_trigger_status AS
SELECT
    trigger_name,
    event_manipulation as event,
    event_object_table as table_name,
    action_timing as timing,
    action_statement as definition
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table, event_manipulation;

-- Create function to temporarily disable triggers (for maintenance)
CREATE OR REPLACE FUNCTION disable_triggers_for_table(p_table_name TEXT)
RETURNS void AS $$
BEGIN
    EXECUTE format('ALTER TABLE %I DISABLE TRIGGER ALL;', p_table_name);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION enable_triggers_for_table(p_table_name TEXT)
RETURNS void AS $$
BEGIN
    EXECUTE format('ALTER TABLE %I ENABLE TRIGGER ALL;', p_table_name);
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- DOCUMENTATION COMMENTS
-- =====================================================

COMMENT ON FUNCTION audit_trigger_function() IS 'Generic audit logging for all major tables';
COMMENT ON FUNCTION validate_parking_session() IS 'Validates parking session data before insert/update';
COMMENT ON FUNCTION calculate_session_billing() IS 'Calculates parking session duration and amount on exit';
COMMENT ON FUNCTION update_space_from_session() IS 'Updates parking space status based on session changes';
COMMENT ON FUNCTION check_vehicle_blacklist() IS 'Prevents blacklisted vehicles from entering';
COMMENT ON FUNCTION create_session_notifications() IS 'Creates notifications for session events';
COMMENT ON FUNCTION expire_no_show_reservations() IS 'Automatically expires no-show reservations';

-- =====================================================
-- ROLLBACK INSTRUCTIONS
-- =====================================================

/*
-- To rollback this migration, run:

-- Drop all triggers
DO $$
DECLARE
    trigger_record RECORD;
BEGIN
    FOR trigger_record IN 
        SELECT trigger_name, event_object_table as table_name
        FROM information_schema.triggers
        WHERE trigger_schema = 'public'
        AND trigger_name LIKE '%_trigger'
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS %I ON %I;', 
                      trigger_record.trigger_name, trigger_record.table_name);
    END LOOP;
END;
$$;

-- Drop all functions
DROP FUNCTION IF EXISTS get_current_user_id();
DROP FUNCTION IF EXISTS get_client_ip();
DROP FUNCTION IF EXISTS audit_trigger_function();
DROP FUNCTION IF EXISTS validate_parking_session();
DROP FUNCTION IF EXISTS validate_reservation();
DROP FUNCTION IF EXISTS update_space_from_session();
DROP FUNCTION IF EXISTS calculate_session_billing();
DROP FUNCTION IF EXISTS update_parking_lot_stats();
DROP FUNCTION IF EXISTS create_session_notifications();
DROP FUNCTION IF EXISTS create_reservation_notifications();
DROP FUNCTION IF EXISTS check_vehicle_blacklist();
DROP FUNCTION IF EXISTS check_parking_capacity();
DROP FUNCTION IF EXISTS validate_rate_config();
DROP FUNCTION IF EXISTS process_payment();
DROP FUNCTION IF EXISTS expire_no_show_reservations();
DROP FUNCTION IF EXISTS check_soft_delete_references();
DROP FUNCTION IF EXISTS update_vehicle_stats();
DROP FUNCTION IF EXISTS mask_sensitive_data();
DROP FUNCTION IF EXISTS apply_dynamic_pricing();
DROP FUNCTION IF EXISTS log_trigger_error();
DROP FUNCTION IF EXISTS disable_triggers_for_table(text);
DROP FUNCTION IF EXISTS enable_triggers_for_table(text);

-- Drop views
DROP VIEW IF EXISTS v_trigger_status;
*/

COMMIT;