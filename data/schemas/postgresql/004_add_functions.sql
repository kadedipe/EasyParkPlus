-- 004_add_functions.sql
-- Advanced PostgreSQL functions for parking management system
-- Includes reporting, analytics, data management, and utility functions

-- =====================================================
-- UUID UTILITY FUNCTIONS
-- =====================================================

-- Generate UUID v7 (timestamp-based) for better indexing
CREATE OR REPLACE FUNCTION uuid_generate_v7()
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_timestamp TIMESTAMPTZ;
    v_seconds BIGINT;
    v_microseconds BIGINT;
    v_random BIGINT;
    v_uuid UUID;
BEGIN
    -- Get current timestamp
    v_timestamp := clock_timestamp();
    v_seconds := EXTRACT(EPOCH FROM v_timestamp)::BIGINT;
    v_microseconds := EXTRACT(MICROSECONDS FROM v_timestamp)::BIGINT;
    
    -- Combine timestamp and random bits
    v_random := (random() * 2^62)::BIGINT;
    
    -- Construct UUID v7 (time-based with random)
    v_uuid := encode(
        decode(
            lpad(to_hex((v_seconds << 28) | (v_microseconds << 16) | (v_random >> 48)), 16, '0') ||
            lpad(to_hex((v_random & (2^48-1))::BIGINT), 16, '0'),
            'hex'
        ),
        'hex'
    )::UUID;
    
    RETURN v_uuid;
END;
$$;

-- Generate UUID v7 with timestamp component for sorting
CREATE OR REPLACE FUNCTION uuid_to_timestamp(uuid_value UUID)
RETURNS TIMESTAMPTZ
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    hex_string TEXT;
    timestamp_bits BIGINT;
    seconds BIGINT;
    microseconds BIGINT;
BEGIN
    -- Extract timestamp from UUID v7
    hex_string := replace(uuid_value::TEXT, '-', '');
    timestamp_bits := ('x' || substring(hex_string, 1, 16))::BIT(64)::BIGINT;
    seconds := timestamp_bits >> 28;
    microseconds := (timestamp_bits >> 16) & (2^12-1);
    
    RETURN to_timestamp(seconds) + (microseconds * '1 microsecond'::INTERVAL);
END;
$$;

-- =====================================================
-- PARKING SESSION FUNCTIONS
-- =====================================================

-- Calculate parking fee based on duration and rate
CREATE OR REPLACE FUNCTION calculate_parking_fee(
    p_entry_time TIMESTAMPTZ,
    p_exit_time TIMESTAMPTZ,
    p_rate_id UUID,
    p_vehicle_type VARCHAR DEFAULT 'car'
)
RETURNS TABLE (
    duration_minutes INTEGER,
    base_amount NUMERIC(10,2),
    tax_amount NUMERIC(10,2),
    total_amount NUMERIC(10,2),
    rate_applied JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_duration INTERVAL;
    v_minutes INTEGER;
    v_rate RECORD;
    v_amount NUMERIC(10,2) := 0;
    v_tax_rate NUMERIC(5,2) := 10.00; -- Default 10% tax, could be configurable
BEGIN
    -- Calculate duration
    v_duration := p_exit_time - p_entry_time;
    v_minutes := EXTRACT(EPOCH FROM v_duration)::INTEGER / 60;
    
    -- Get rate details
    SELECT * INTO v_rate
    FROM rates
    WHERE id = p_rate_id 
      AND is_active = true
      AND p_vehicle_type = ANY(SELECT jsonb_array_elements_text(vehicle_types));
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No active rate found for vehicle type %', p_vehicle_type;
    END IF;
    
    -- Calculate amount based on rate type
    CASE v_rate.rate_type
        WHEN 'hourly' THEN
            v_amount := CEIL(v_minutes / 60.0) * v_rate.base_rate;
        WHEN 'daily' THEN
            v_amount := CEIL(v_minutes / (24.0 * 60)) * v_rate.base_rate;
        WHEN 'weekly' THEN
            v_amount := CEIL(v_minutes / (7.0 * 24 * 60)) * v_rate.base_rate;
        WHEN 'monthly' THEN
            v_amount := CEIL(v_minutes / (30.0 * 24 * 60)) * v_rate.base_rate;
        WHEN 'flat' THEN
            v_amount := v_rate.flat_amount;
        WHEN 'progressive' THEN
            -- Apply progressive tiered pricing
            SELECT rate INTO v_amount
            FROM jsonb_to_recordset(v_rate.tiers) AS x(min_time INTEGER, max_time INTEGER, rate NUMERIC)
            WHERE v_minutes BETWEEN min_time AND COALESCE(max_time, 999999)
            LIMIT 1;
            
            IF v_amount IS NULL THEN
                v_amount := v_rate.base_rate * CEIL(v_minutes / 60.0);
            END IF;
    END CASE;
    
    -- Apply any time-based multipliers (peak/off-peak)
    IF v_rate.time_rules IS NOT NULL THEN
        -- Check if current time is within peak hours
        IF EXISTS (
            SELECT 1 FROM jsonb_array_elements(v_rate.time_rules) AS rule
            WHERE (rule->>'day_of_week')::INT = EXTRACT(DOW FROM p_entry_time)
              AND (rule->>'start_hour')::INT <= EXTRACT(HOUR FROM p_entry_time)
              AND (rule->>'end_hour')::INT >= EXTRACT(HOUR FROM p_entry_time)
        ) THEN
            v_amount := v_amount * 1.2; -- 20% peak surcharge
        END IF;
    END IF;
    
    RETURN QUERY
    SELECT 
        v_minutes AS duration_minutes,
        ROUND(v_amount::NUMERIC, 2) AS base_amount,
        ROUND(v_amount * v_tax_rate / 100, 2) AS tax_amount,
        ROUND(v_amount * (1 + v_tax_rate/100), 2) AS total_amount,
        row_to_json(v_rate)::JSONB AS rate_applied;
END;
$$;

-- End parking session and calculate final amount
CREATE OR REPLACE FUNCTION end_parking_session(
    p_session_id UUID,
    p_exit_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    p_ended_by UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_session RECORD;
    v_calculation RECORD;
    v_result JSONB;
BEGIN
    -- Get session details
    SELECT * INTO v_session
    FROM parking_sessions
    WHERE id = p_session_id AND status = 'active';
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active parking session with ID % not found', p_session_id;
    END IF;
    
    -- Calculate fee
    SELECT * INTO v_calculation
    FROM calculate_parking_fee(
        v_session.entry_time,
        p_exit_time,
        v_session.rate_id,
        (SELECT vehicle_type FROM vehicles WHERE id = v_session.vehicle_id)
    );
    
    -- Update session
    UPDATE parking_sessions
    SET 
        exit_time = p_exit_time,
        duration_minutes = v_calculation.duration_minutes,
        base_amount = v_calculation.base_amount,
        tax_amount = v_calculation.tax_amount,
        total_amount = v_calculation.total_amount,
        rate_applied = v_calculation.rate_applied,
        status = 'completed',
        ended_by_id = COALESCE(p_ended_by, v_session.ended_by_id),
        updated_at = CURRENT_TIMESTAMP,
        version = version + 1
    WHERE id = p_session_id
    RETURNING to_jsonb(parking_sessions.*) INTO v_result;
    
    RETURN v_result;
END;
$$;

-- Get active parking sessions with details
CREATE OR REPLACE FUNCTION get_active_sessions(
    p_parking_lot_id UUID DEFAULT NULL,
    p_organization_id UUID DEFAULT NULL
)
RETURNS TABLE (
    session_id UUID,
    session_number VARCHAR(100),
    license_plate VARCHAR(20),
    vehicle_type VARCHAR(50),
    space_number VARCHAR(50),
    level_number INTEGER,
    entry_time TIMESTAMPTZ,
    duration_minutes INTEGER,
    estimated_amount NUMERIC(10,2),
    customer_name VARCHAR(200),
    customer_email VARCHAR(255)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ps.id AS session_id,
        ps.session_id AS session_number,
        v.license_plate,
        v.vehicle_type,
        psp.space_number,
        pl.level_number,
        ps.entry_time,
        EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ps.entry_time))::INTEGER / 60 AS duration_minutes,
        CASE 
            WHEN r.id IS NOT NULL THEN 
                (SELECT total_amount FROM calculate_parking_fee(ps.entry_time, CURRENT_TIMESTAMP, r.id, v.vehicle_type))
            ELSE NULL
        END AS estimated_amount,
        COALESCE(u.first_name || ' ' || u.last_name, r.customer_name) AS customer_name,
        COALESCE(u.email, r.customer_email) AS customer_email
    FROM parking_sessions ps
    JOIN vehicles v ON ps.vehicle_id = v.id
    JOIN parking_spaces psp ON ps.parking_space_id = psp.id
    JOIN parking_levels pl ON psp.level_id = pl.id
    LEFT JOIN rates r ON ps.rate_id = r.id
    LEFT JOIN users u ON v.owner_id = u.id
    WHERE ps.status = 'active'
      AND (p_parking_lot_id IS NULL OR ps.parking_lot_id = p_parking_lot_id)
      AND (p_organization_id IS NULL OR v.organization_id = p_organization_id)
    ORDER BY ps.entry_time;
END;
$$;

-- =====================================================
-- RESERVATION FUNCTIONS
-- =====================================================

-- Check space availability for reservation
CREATE OR REPLACE FUNCTION check_reservation_availability(
    p_parking_lot_id UUID,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ,
    p_vehicle_type VARCHAR DEFAULT NULL,
    p_preferred_space_id UUID DEFAULT NULL
)
RETURNS TABLE (
    space_id UUID,
    space_number VARCHAR(50),
    level_number INTEGER,
    is_available BOOLEAN,
    estimated_cost NUMERIC(10,2)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH available_spaces AS (
        SELECT 
            ps.id,
            ps.space_number,
            pl.level_number,
            ps.space_type
        FROM parking_spaces ps
        JOIN parking_levels pl ON ps.level_id = pl.id
        WHERE ps.status = 'available'
          AND pl.parking_lot_id = p_parking_lot_id
          AND (p_vehicle_type IS NULL OR ps.space_type = p_vehicle_type)
          AND NOT EXISTS (
              SELECT 1 FROM reservations r
              WHERE r.parking_space_id = ps.id
                AND r.status IN ('confirmed', 'checked_in')
                AND tstzrange(r.start_time, r.end_time) && tstzrange(p_start_time, p_end_time)
          )
          AND NOT EXISTS (
              SELECT 1 FROM parking_sessions ps2
              WHERE ps2.parking_space_id = ps.id
                AND ps2.status = 'active'
                AND tstzrange(ps2.entry_time, ps2.exit_time) && tstzrange(p_start_time, p_end_time)
          )
    )
    SELECT 
        aspace.id AS space_id,
        aspace.space_number,
        aspace.level_number,
        TRUE AS is_available,
        CASE 
            WHEN r.id IS NOT NULL THEN 
                (SELECT total_amount FROM calculate_parking_fee(p_start_time, p_end_time, r.id, p_vehicle_type))
            ELSE 0
        END AS estimated_cost
    FROM available_spaces aspace
    CROSS JOIN LATERAL (
        SELECT id FROM rates 
        WHERE parking_lot_id = p_parking_lot_id 
          AND is_active = true
          AND (p_vehicle_type IS NULL OR p_vehicle_type = ANY(SELECT jsonb_array_elements_text(vehicle_types)))
        LIMIT 1
    ) r
    
    UNION ALL
    
    -- If preferred space specified and available
    SELECT 
        ps.id AS space_id,
        ps.space_number,
        pl.level_number,
        FALSE AS is_available,
        0 AS estimated_cost
    FROM parking_spaces ps
    JOIN parking_levels pl ON ps.level_id = pl.id
    WHERE ps.id = p_preferred_space_id
      AND NOT EXISTS (
          SELECT 1 FROM available_spaces WHERE id = ps.id
      )
    LIMIT 1;
END;
$$;

-- Create reservation with payment
CREATE OR REPLACE FUNCTION create_reservation(
    p_parking_lot_id UUID,
    p_space_id UUID,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ,
    p_customer_name VARCHAR,
    p_customer_email VARCHAR,
    p_vehicle_plate VARCHAR,
    p_user_id UUID DEFAULT NULL,
    p_rate_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_reservation_id UUID;
    v_vehicle_id UUID;
    v_rate_id UUID;
    v_calculation RECORD;
    v_result JSONB;
BEGIN
    -- Check availability
    IF NOT EXISTS (
        SELECT 1 FROM check_reservation_availability(
            p_parking_lot_id, p_start_time, p_end_time, NULL, p_space_id
        ) WHERE space_id = p_space_id AND is_available = true
    ) THEN
        RAISE EXCEPTION 'Space is not available for the selected time period';
    END IF;
    
    -- Get or create vehicle
    SELECT id INTO v_vehicle_id
    FROM vehicles
    WHERE license_plate_normalized = UPPER(p_vehicle_plate)
    LIMIT 1;
    
    IF v_vehicle_id IS NULL AND p_user_id IS NOT NULL THEN
        INSERT INTO vehicles (
            license_plate,
            license_plate_normalized,
            owner_id,
            organization_id
        ) VALUES (
            p_vehicle_plate,
            UPPER(p_vehicle_plate),
            p_user_id,
            (SELECT organization_id FROM users WHERE id = p_user_id)
        ) RETURNING id INTO v_vehicle_id;
    END IF;
    
    -- Get rate
    IF p_rate_id IS NULL THEN
        SELECT id INTO v_rate_id
        FROM rates
        WHERE parking_lot_id = p_parking_lot_id 
          AND is_active = true
        LIMIT 1;
    ELSE
        v_rate_id := p_rate_id;
    END IF;
    
    -- Calculate cost
    SELECT * INTO v_calculation
    FROM calculate_parking_fee(p_start_time, p_end_time, v_rate_id);
    
    -- Create reservation
    INSERT INTO reservations (
        reservation_number,
        start_time,
        end_time,
        customer_name,
        customer_email,
        vehicle_license_plate,
        vehicle_id,
        user_id,
        parking_lot_id,
        parking_space_id,
        rate_id,
        base_amount,
        tax_amount,
        total_amount,
        currency,
        status,
        created_by,
        updated_by
    ) VALUES (
        'RES-' || to_char(CURRENT_TIMESTAMP, 'YYYYMMDD') || '-' || uuid_generate_v7(),
        p_start_time,
        p_end_time,
        p_customer_name,
        p_customer_email,
        p_vehicle_plate,
        v_vehicle_id,
        p_user_id,
        p_parking_lot_id,
        p_space_id,
        v_rate_id,
        v_calculation.base_amount,
        v_calculation.tax_amount,
        v_calculation.total_amount,
        'USD',
        'confirmed',
        p_user_id,
        p_user_id
    ) RETURNING to_jsonb(reservations.*) INTO v_result;
    
    RETURN v_result;
END;
$$;

-- =====================================================
-- REPORTING AND ANALYTICS FUNCTIONS
-- =====================================================

-- Generate daily revenue report
CREATE OR REPLACE FUNCTION get_daily_revenue(
    p_start_date DATE,
    p_end_date DATE,
    p_organization_id UUID DEFAULT NULL,
    p_parking_lot_id UUID DEFAULT NULL
)
RETURNS TABLE (
    revenue_date DATE,
    total_sessions BIGINT,
    total_revenue NUMERIC(10,2),
    avg_session_duration NUMERIC(10,2),
    peak_hour INTEGER,
    payment_method_breakdown JSONB,
    vehicle_type_breakdown JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH daily_stats AS (
        SELECT 
            DATE(ps.exit_time) AS rev_date,
            COUNT(*) AS sessions,
            SUM(ps.total_amount) AS revenue,
            AVG(ps.duration_minutes) AS avg_duration,
            MODE() WITHIN GROUP (ORDER BY EXTRACT(HOUR FROM ps.exit_time)) AS peak_hr,
            (
                SELECT jsonb_object_agg(pm, cnt)
                FROM (
                    SELECT p.payment_method, COUNT(*) AS cnt
                    FROM payments p
                    WHERE p.parking_session_id = ps.id
                    GROUP BY p.payment_method
                ) pm_counts
            ) AS pay_methods,
            (
                SELECT jsonb_object_agg(vt, cnt)
                FROM (
                    SELECT v.vehicle_type, COUNT(*) AS cnt
                    FROM vehicles v
                    WHERE v.id = ps.vehicle_id
                    GROUP BY v.vehicle_type
                ) vt_counts
            ) AS veh_types
        FROM parking_sessions ps
        LEFT JOIN vehicles v ON ps.vehicle_id = v.id
        WHERE ps.status = 'completed'
          AND ps.exit_time::DATE BETWEEN p_start_date AND p_end_date
          AND (p_organization_id IS NULL OR v.organization_id = p_organization_id)
          AND (p_parking_lot_id IS NULL OR ps.parking_lot_id = p_parking_lot_id)
        GROUP BY DATE(ps.exit_time)
    )
    SELECT 
        rev_date,
        sessions,
        COALESCE(revenue, 0) AS total_revenue,
        COALESCE(avg_duration, 0) AS avg_session_duration,
        peak_hr::INTEGER,
        COALESCE(pay_methods, '{}'::JSONB) AS payment_method_breakdown,
        COALESCE(veh_types, '{}'::JSONB) AS vehicle_type_breakdown
    FROM daily_stats
    ORDER BY rev_date;
END;
$$;

-- Get occupancy statistics
CREATE OR REPLACE FUNCTION get_occupancy_stats(
    p_parking_lot_id UUID,
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ,
    p_interval INTERVAL DEFAULT '1 hour'::INTERVAL
)
RETURNS TABLE (
    time_bucket TIMESTAMPTZ,
    active_sessions BIGINT,
    occupancy_rate NUMERIC(5,2),
    reserved_spots BIGINT,
    available_spots BIGINT,
    revenue_generated NUMERIC(10,2)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_total_spaces INTEGER;
BEGIN
    -- Get total spaces for the lot
    SELECT total_spaces INTO v_total_spaces
    FROM parking_lots
    WHERE id = p_parking_lot_id;
    
    RETURN QUERY
    WITH time_series AS (
        SELECT generate_series(
            p_start_date,
            p_end_date - p_interval,
            p_interval
        ) AS bucket_start
    ),
    occupancy AS (
        SELECT 
            ts.bucket_start,
            COUNT(DISTINCT ps.id) AS active_count,
            COUNT(DISTINCT r.id) AS reserved_count,
            COALESCE(SUM(p.total_amount), 0) AS revenue
        FROM time_series ts
        LEFT JOIN parking_sessions ps ON 
            ps.parking_lot_id = p_parking_lot_id
            AND ps.status = 'active'
            AND ps.entry_time <= ts.bucket_start + p_interval
            AND (ps.exit_time IS NULL OR ps.exit_time > ts.bucket_start)
        LEFT JOIN reservations r ON
            r.parking_lot_id = p_parking_lot_id
            AND r.status IN ('confirmed', 'checked_in')
            AND r.start_time <= ts.bucket_start + p_interval
            AND r.end_time > ts.bucket_start
        LEFT JOIN payments p ON
            p.parking_session_id = ps.id
            AND p.payment_status = 'completed'
            AND p.payment_time BETWEEN ts.bucket_start AND ts.bucket_start + p_interval
        GROUP BY ts.bucket_start
    )
    SELECT 
        o.bucket_start,
        o.active_count AS active_sessions,
        ROUND((o.active_count::NUMERIC / v_total_spaces) * 100, 2) AS occupancy_rate,
        o.reserved_count AS reserved_spots,
        v_total_spaces - o.active_count - o.reserved_count AS available_spots,
        o.revenue AS revenue_generated
    FROM occupancy o
    ORDER BY o.bucket_start;
END;
$$;

-- Generate monthly performance report
CREATE OR REPLACE FUNCTION get_monthly_performance(
    p_year INTEGER,
    p_month INTEGER,
    p_organization_id UUID DEFAULT NULL
)
RETURNS TABLE (
    lot_name VARCHAR(200),
    total_sessions BIGINT,
    total_revenue NUMERIC(10,2),
    avg_daily_occupancy NUMERIC(5,2),
    peak_occupancy_time TIME,
    revenue_per_space NUMERIC(10,2),
    utilization_rate NUMERIC(5,2),
    top_vehicle_types JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pl.name AS lot_name,
        COUNT(DISTINCT ps.id) AS total_sessions,
        COALESCE(SUM(ps.total_amount), 0) AS total_revenue,
        COALESCE(AVG(daily_occ.occupancy_rate), 0) AS avg_daily_occupancy,
        MODE() WITHIN GROUP (ORDER BY EXTRACT(HOUR FROM ps.entry_time)::TEXT)::TIME AS peak_occupancy_time,
        COALESCE(SUM(ps.total_amount) / NULLIF(pl.total_spaces, 0), 0) AS revenue_per_space,
        COALESCE(
            (COUNT(DISTINCT ps.id) * AVG(ps.duration_minutes) / 60.0) / 
            (pl.total_spaces * 24 * EXTRACT(DAY FROM DATE_TRUNC('month', MAKE_DATE(p_year, p_month, 1) + INTERVAL '1 month' - INTERVAL '1 day'))::INTEGER) * 100,
            0
        ) AS utilization_rate,
        (
            SELECT jsonb_object_agg(vt, cnt)
            FROM (
                SELECT v.vehicle_type, COUNT(*) AS cnt
                FROM vehicles v
                WHERE v.id = ps.vehicle_id
                GROUP BY v.vehicle_type
            ) vt_counts
        ) AS top_vehicle_types
    FROM parking_lots pl
    LEFT JOIN parking_sessions ps ON 
        ps.parking_lot_id = pl.id 
        AND EXTRACT(YEAR FROM ps.entry_time) = p_year
        AND EXTRACT(MONTH FROM ps.entry_time) = p_month
    LEFT JOIN LATERAL (
        SELECT AVG(occupancy_rate) AS occupancy_rate
        FROM get_occupancy_stats(
            pl.id,
            DATE_TRUNC('month', MAKE_DATE(p_year, p_month, 1)),
            DATE_TRUNC('month', MAKE_DATE(p_year, p_month, 1)) + INTERVAL '1 month',
            '1 day'::INTERVAL
        ) occ
    ) daily_occ ON true
    WHERE (p_organization_id IS NULL OR pl.organization_id = p_organization_id)
    GROUP BY pl.id, pl.name, pl.total_spaces
    ORDER BY total_revenue DESC;
END;
$$;

-- =====================================================
-- VEHICLE MANAGEMENT FUNCTIONS
-- =====================================================

-- Find vehicles by partial plate number
CREATE OR REPLACE FUNCTION search_vehicles(
    p_search_term TEXT,
    p_organization_id UUID DEFAULT NULL,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    vehicle_id UUID,
    license_plate VARCHAR(20),
    make VARCHAR(100),
    model VARCHAR(100),
    color VARCHAR(50),
    vehicle_type VARCHAR(50),
    owner_name VARCHAR(200),
    last_seen TIMESTAMPTZ,
    total_visits BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        v.id AS vehicle_id,
        v.license_plate,
        v.make,
        v.model,
        v.color,
        v.vehicle_type,
        COALESCE(u.first_name || ' ' || u.last_name, 'Unknown') AS owner_name,
        MAX(ps.entry_time) AS last_seen,
        COUNT(ps.id) AS total_visits
    FROM vehicles v
    LEFT JOIN users u ON v.owner_id = u.id
    LEFT JOIN parking_sessions ps ON v.id = ps.vehicle_id
    WHERE v.license_plate_normalized LIKE '%' || UPPER(p_search_term) || '%'
      AND (p_organization_id IS NULL OR v.organization_id = p_organization_id)
    GROUP BY v.id, v.license_plate, v.make, v.model, v.color, v.vehicle_type, u.first_name, u.last_name
    ORDER BY 
        CASE 
            WHEN v.license_plate_normalized = UPPER(p_search_term) THEN 0
            WHEN v.license_plate_normalized LIKE UPPER(p_search_term) || '%' THEN 1
            ELSE 2
        END,
        last_seen DESC NULLS LAST
    LIMIT p_limit;
END;
$$;

-- Get vehicle history
CREATE OR REPLACE FUNCTION get_vehicle_history(
    p_vehicle_id UUID,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    session_id UUID,
    entry_time TIMESTAMPTZ,
    exit_time TIMESTAMPTZ,
    duration_minutes INTEGER,
    parking_lot_name VARCHAR(200),
    space_number VARCHAR(50),
    total_amount NUMERIC(10,2),
    payment_status VARCHAR(50)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ps.id AS session_id,
        ps.entry_time,
        ps.exit_time,
        ps.duration_minutes,
        pl.name AS parking_lot_name,
        psp.space_number,
        ps.total_amount,
        ps.payment_status
    FROM parking_sessions ps
    JOIN parking_lots pl ON ps.parking_lot_id = pl.id
    JOIN parking_spaces psp ON ps.parking_space_id = psp.id
    WHERE ps.vehicle_id = p_vehicle_id
    ORDER BY ps.entry_time DESC
    LIMIT p_limit;
END;
$$;

-- =====================================================
-- PAYMENT AND BILLING FUNCTIONS
-- =====================================================

-- Process payment for parking session
CREATE OR REPLACE FUNCTION process_session_payment(
    p_session_id UUID,
    p_payment_method VARCHAR,
    p_amount NUMERIC,
    p_processed_by UUID DEFAULT NULL,
    p_card_last_four VARCHAR DEFAULT NULL,
    p_card_brand VARCHAR DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_session RECORD;
    v_payment_id UUID;
    v_result JSONB;
BEGIN
    -- Get session details
    SELECT * INTO v_session
    FROM parking_sessions
    WHERE id = p_session_id AND status = 'completed';
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Completed parking session with ID % not found', p_session_id;
    END IF;
    
    -- Verify amount
    IF p_amount < v_session.total_amount THEN
        RAISE EXCEPTION 'Payment amount (%) is less than session total (%)', 
            p_amount, v_session.total_amount;
    END IF;
    
    -- Create payment record
    INSERT INTO payments (
        payment_number,
        transaction_id,
        amount,
        tax_amount,
        total_amount,
        currency,
        payment_method,
        payment_status,
        payment_time,
        card_last_four,
        card_brand,
        parking_session_id,
        processed_by_id,
        created_by,
        updated_by
    ) VALUES (
        'PAY-' || to_char(CURRENT_TIMESTAMP, 'YYYYMMDD') || '-' || uuid_generate_v7(),
        'TXN-' || encode(gen_random_bytes(8), 'hex'),
        v_session.total_amount,
        v_session.tax_amount,
        v_session.total_amount,
        v_session.currency,
        p_payment_method,
        'completed',
        CURRENT_TIMESTAMP,
        p_card_last_four,
        p_card_brand,
        p_session_id,
        p_processed_by,
        p_processed_by,
        p_processed_by
    ) RETURNING id INTO v_payment_id;
    
    -- Update session payment status
    UPDATE parking_sessions
    SET payment_status = 'paid',
        payment_method = p_payment_method,
        payment_time = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP,
        version = version + 1
    WHERE id = p_session_id;
    
    -- Return payment details
    SELECT to_jsonb(p.*) INTO v_result
    FROM payments p
    WHERE p.id = v_payment_id;
    
    RETURN v_result;
END;
$$;

-- Generate invoice for parking session
CREATE OR REPLACE FUNCTION generate_invoice(
    p_session_id UUID
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_invoice JSONB;
BEGIN
    SELECT jsonb_build_object(
        'invoice_number', 'INV-' || to_char(CURRENT_TIMESTAMP, 'YYYYMMDD') || '-' || substring(p_session_id::TEXT, 1, 8),
        'issue_date', CURRENT_DATE,
        'due_date', CURRENT_DATE + INTERVAL '7 days',
        'session', row_to_json(ps.*),
        'vehicle', row_to_json(v.*),
        'parking_lot', row_to_json(pl.*),
        'organization', row_to_json(o.*),
        'payment', row_to_json(p.*),
        'items', jsonb_build_array(
            jsonb_build_object(
                'description', 'Parking fee for ' || ps.duration_minutes || ' minutes',
                'quantity', 1,
                'unit_price', ps.base_amount,
                'amount', ps.base_amount
            )
        ),
        'subtotal', ps.base_amount,
        'tax', ps.tax_amount,
        'total', ps.total_amount,
        'amount_due', CASE WHEN p.id IS NULL THEN ps.total_amount ELSE 0 END,
        'status', CASE WHEN p.id IS NOT NULL THEN 'paid' ELSE 'pending' END
    ) INTO v_invoice
    FROM parking_sessions ps
    JOIN vehicles v ON ps.vehicle_id = v.id
    JOIN parking_lots pl ON ps.parking_lot_id = pl.id
    JOIN organizations o ON pl.organization_id = o.id
    LEFT JOIN payments p ON ps.id = p.parking_session_id AND p.payment_status = 'completed'
    WHERE ps.id = p_session_id;
    
    RETURN v_invoice;
END;
$$;

-- =====================================================
-- MAINTENANCE AND CLEANUP FUNCTIONS
-- =====================================================

-- Clean up expired sessions and reservations
CREATE OR REPLACE FUNCTION cleanup_expired_records()
RETURNS TABLE (
    cleaned_type TEXT,
    records_affected BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_count BIGINT;
BEGIN
    -- Clean up expired temporary blacklist entries
    WITH deleted AS (
        DELETE FROM blacklisted_vehicles
        WHERE blacklist_type = 'temporary'
          AND expires_at < CURRENT_TIMESTAMP
          AND is_active = true
        RETURNING *
    )
    SELECT COUNT(*) INTO v_count FROM deleted;
    
    cleaned_type := 'expired_blacklist';
    records_affected := v_count;
    RETURN NEXT;
    
    -- Mark no-show reservations
    WITH updated AS (
        UPDATE reservations
        SET status = 'no_show',
            updated_at = CURRENT_TIMESTAMP,
            version = version + 1
        WHERE status = 'confirmed'
          AND start_time < CURRENT_TIMESTAMP - INTERVAL '30 minutes'
          AND check_in_time IS NULL
        RETURNING *
    )
    SELECT COUNT(*) INTO v_count FROM updated;
    
    cleaned_type := 'no_show_reservations';
    records_affected := v_count;
    RETURN NEXT;
    
    -- Release spaces from expired reservations
    WITH released AS (
        UPDATE parking_spaces ps
        SET status = 'available',
            current_vehicle_id = NULL,
            updated_at = CURRENT_TIMESTAMP,
            version = version + 1
        FROM reservations r
        WHERE r.parking_space_id = ps.id
          AND r.status = 'no_show'
          AND ps.status = 'reserved'
        RETURNING ps.*
    )
    SELECT COUNT(*) INTO v_count FROM released;
    
    cleaned_type := 'released_spaces';
    records_affected := v_count;
    RETURN NEXT;
END;
$$;

-- Archive old parking sessions
CREATE OR REPLACE FUNCTION archive_old_sessions(
    p_days_old INTEGER DEFAULT 365,
    p_batch_size INTEGER DEFAULT 1000
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_archived INTEGER := 0;
    v_batch_count INTEGER;
BEGIN
    -- Create archive table if not exists
    CREATE TABLE IF NOT EXISTS parking_sessions_archive (
        LIKE parking_sessions INCLUDING ALL,
        archived_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    
    LOOP
        WITH batch AS (
            SELECT id
            FROM parking_sessions
            WHERE status = 'completed'
              AND exit_time < CURRENT_TIMESTAMP - (p_days_old || ' days')::INTERVAL
              AND NOT EXISTS (
                  SELECT 1 FROM parking_sessions_archive 
                  WHERE parking_sessions_archive.id = parking_sessions.id
              )
            LIMIT p_batch_size
            FOR UPDATE SKIP LOCKED
        )
        INSERT INTO parking_sessions_archive
        SELECT ps.*, CURRENT_TIMESTAMP
        FROM parking_sessions ps
        JOIN batch b ON ps.id = b.id;
        
        GET DIAGNOSTICS v_batch_count = ROW_COUNT;
        v_archived := v_archived + v_batch_count;
        
        EXIT WHEN v_batch_count < p_batch_size;
    END LOOP;
    
    -- Delete archived sessions from main table
    DELETE FROM parking_sessions ps
    USING parking_sessions_archive psa
    WHERE ps.id = psa.id;
    
    RETURN v_archived;
END;
$$;

-- =====================================================
-- UTILITY AND HELPER FUNCTIONS
-- =====================================================

-- Normalize license plate
CREATE OR REPLACE FUNCTION normalize_license_plate(
    p_plate TEXT
)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    RETURN UPPER(REGEXP_REPLACE(p_plate, '[^A-Z0-9]', '', 'g'));
END;
$$;

-- Calculate distance between two points (Haversine formula)
CREATE OR REPLACE FUNCTION calculate_distance(
    lat1 FLOAT,
    lon1 FLOAT,
    lat2 FLOAT,
    lon2 FLOAT
)
RETURNS FLOAT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    R FLOAT = 6371; -- Earth's radius in kilometers
    dlat FLOAT;
    dlon FLOAT;
    a FLOAT;
    c FLOAT;
BEGIN
    dlat := radians(lat2 - lat1);
    dlon := radians(lon2 - lon1);
    a := sin(dlat/2)^2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)^2;
    c := 2 * asin(sqrt(a));
    RETURN R * c;
END;
$$;

-- Find nearby parking lots
CREATE OR REPLACE FUNCTION find_nearby_parking_lots(
    p_latitude FLOAT,
    p_longitude FLOAT,
    p_radius_km FLOAT DEFAULT 5,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    lot_id UUID,
    lot_name VARCHAR(200),
    distance_km FLOAT,
    address TEXT,
    available_spaces INTEGER,
    total_spaces INTEGER,
    has_electric BOOLEAN,
    has_handicapped BOOLEAN,
    current_rate NUMERIC(10,2)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pl.id AS lot_id,
        pl.name AS lot_name,
        calculate_distance(p_latitude, p_longitude, pl.latitude, pl.longitude) AS distance_km,
        pl.address,
        pl.available_spaces,
        pl.total_spaces,
        EXISTS(SELECT 1 FROM parking_spaces ps WHERE ps.space_type = 'electric' AND ps.level_id IN (SELECT id FROM parking_levels WHERE parking_lot_id = pl.id)) AS has_electric,
        EXISTS(SELECT 1 FROM parking_spaces ps WHERE ps.is_handicapped = true AND ps.level_id IN (SELECT id FROM parking_levels WHERE parking_lot_id = pl.id)) AS has_handicapped,
        COALESCE((
            SELECT base_rate FROM rates 
            WHERE parking_lot_id = pl.id 
              AND is_active = true 
            LIMIT 1
        ), 0) AS current_rate
    FROM parking_lots pl
    WHERE pl.latitude IS NOT NULL 
      AND pl.longitude IS NOT NULL
      AND pl.is_active = true
      AND calculate_distance(p_latitude, p_longitude, pl.latitude, pl.longitude) <= p_radius_km
    ORDER BY distance_km
    LIMIT p_limit;
END;
$$;

-- =====================================================
-- DASHBOARD AND METRICS FUNCTIONS
-- =====================================================

-- Get real-time dashboard metrics
CREATE OR REPLACE FUNCTION get_dashboard_metrics(
    p_organization_id UUID DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_result JSONB;
BEGIN
    WITH metrics AS (
        SELECT
            -- Overall stats
            (SELECT COUNT(*) FROM parking_lots WHERE (p_organization_id IS NULL OR organization_id = p_organization_id)) AS total_lots,
            (SELECT COUNT(*) FROM parking_sessions WHERE status = 'active') AS active_sessions,
            (SELECT COUNT(*) FROM vehicles) AS total_vehicles,
            (SELECT COUNT(*) FROM users WHERE is_active = true) AS active_users,
            
            -- Today's stats
            (SELECT COUNT(*) FROM parking_sessions WHERE DATE(entry_time) = CURRENT_DATE) AS today_sessions,
            (SELECT COALESCE(SUM(total_amount), 0) FROM parking_sessions WHERE DATE(exit_time) = CURRENT_DATE AND status = 'completed') AS today_revenue,
            
            -- Occupancy
            (SELECT COALESCE(AVG(available_spaces::FLOAT / NULLIF(total_spaces, 0)), 0) FROM parking_lots) AS avg_occupancy,
            
            -- Alerts
            (SELECT COUNT(*) FROM parking_sessions WHERE status = 'active' AND EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - entry_time)) > 86400) AS long_stay_alerts,
            (SELECT COUNT(*) FROM blacklisted_vehicles WHERE is_active = true AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)) AS active_blacklist,
            
            -- Revenue metrics
            (SELECT COALESCE(SUM(total_amount), 0) FROM parking_sessions WHERE DATE(entry_time) = CURRENT_DATE - 1) AS yesterday_revenue,
            (SELECT COALESCE(SUM(total_amount), 0) FROM parking_sessions WHERE DATE_TRUNC('week', entry_time) = DATE_TRUNC('week', CURRENT_DATE)) AS week_revenue,
            (SELECT COALESCE(SUM(total_amount), 0) FROM parking_sessions WHERE DATE_TRUNC('month', entry_time) = DATE_TRUNC('month', CURRENT_DATE)) AS month_revenue
    )
    SELECT jsonb_build_object(
        'overview', jsonb_build_object(
            'total_lots', total_lots,
            'active_sessions', active_sessions,
            'total_vehicles', total_vehicles,
            'active_users', active_users
        ),
        'today', jsonb_build_object(
            'sessions', today_sessions,
            'revenue', today_revenue,
            'avg_occupancy', ROUND(avg_occupancy * 100, 2)
        ),
        'alerts', jsonb_build_object(
            'long_stay', long_stay_alerts,
            'blacklisted', active_blacklist
        ),
        'revenue', jsonb_build_object(
            'today', today_revenue,
            'yesterday', yesterday_revenue,
            'week', week_revenue,
            'month', month_revenue
        ),
        'timestamp', CURRENT_TIMESTAMP
    ) INTO v_result
    FROM metrics;
    
    RETURN v_result;
END;
$$;

-- =====================================================
-- DATA EXPORT FUNCTIONS
-- =====================================================

-- Export sessions as CSV data
CREATE OR REPLACE FUNCTION export_sessions_csv(
    p_start_date DATE,
    p_end_date DATE,
    p_organization_id UUID DEFAULT NULL
)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    v_csv TEXT;
BEGIN
    WITH sessions_data AS (
        SELECT 
            ps.session_id,
            ps.ticket_number,
            ps.entry_time,
            ps.exit_time,
            ps.duration_minutes,
            v.license_plate,
            v.vehicle_type,
            pl.name AS parking_lot,
            psp.space_number,
            ps.base_amount,
            ps.tax_amount,
            ps.total_amount,
            ps.payment_status,
            ps.payment_method,
            ps.status
        FROM parking_sessions ps
        JOIN vehicles v ON ps.vehicle_id = v.id
        JOIN parking_lots pl ON ps.parking_lot_id = pl.id
        JOIN parking_spaces psp ON ps.parking_space_id = psp.id
        WHERE DATE(ps.entry_time) BETWEEN p_start_date AND p_end_date
          AND (p_organization_id IS NULL OR v.organization_id = p_organization_id)
        ORDER BY ps.entry_time DESC
    )
    SELECT string_agg(
        format(
            '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s',
            session_id,
            ticket_number,
            entry_time,
            exit_time,
            duration_minutes,
            license_plate,
            vehicle_type,
            parking_lot,
            space_number,
            base_amount,
            tax_amount,
            total_amount,
            payment_status,
            status
        ), E'\n'
    )
    INTO v_csv
    FROM sessions_data;
    
    RETURN 'session_id,ticket_number,entry_time,exit_time,duration_minutes,license_plate,vehicle_type,parking_lot,space_number,base_amount,tax_amount,total_amount,payment_status,status' || E'\n' || COALESCE(v_csv, '');
END;
$$;

-- =====================================================
-- FUNCTION DOCUMENTATION
-- =====================================================

COMMENT ON FUNCTION uuid_generate_v7() IS 'Generates time-ordered UUID v7 for better index performance';
COMMENT ON FUNCTION calculate_parking_fee(UUID, UUID, TIMESTAMPTZ, TIMESTAMPTZ, VARCHAR) IS 'Calculates parking fee based on duration and rate rules';
COMMENT ON FUNCTION end_parking_session(UUID, TIMESTAMPTZ, UUID) IS 'Completes a parking session and calculates final amount';
COMMENT ON FUNCTION get_active_sessions(UUID, UUID) IS 'Returns all active parking sessions with details';
COMMENT ON FUNCTION check_reservation_availability(UUID, TIMESTAMPTZ, TIMESTAMPTZ, VARCHAR, UUID) IS 'Checks space availability for reservations';
COMMENT ON FUNCTION get_daily_revenue(DATE, DATE, UUID, UUID) IS 'Generates daily revenue report';
COMMENT ON FUNCTION get_occupancy_stats(UUID, TIMESTAMPTZ, TIMESTAMPTZ, INTERVAL) IS 'Calculates occupancy statistics over time';
COMMENT ON FUNCTION search_vehicles(TEXT, UUID, INTEGER) IS 'Searches vehicles by partial plate number';
COMMENT ON FUNCTION cleanup_expired_records() IS 'Cleans up expired records (blacklist, reservations)';
COMMENT ON FUNCTION find_nearby_parking_lots(FLOAT, FLOAT, FLOAT, INTEGER) IS 'Finds parking lots within radius of coordinates';
COMMENT ON FUNCTION get_dashboard_metrics(UUID) IS 'Returns real-time dashboard metrics';

-- =====================================================
-- ROLLBACK INSTRUCTIONS
-- =====================================================

/*
-- To rollback this migration, run:

DROP FUNCTION IF EXISTS uuid_generate_v7();
DROP FUNCTION IF EXISTS uuid_to_timestamp(UUID);
DROP FUNCTION IF EXISTS calculate_parking_fee(TIMESTAMPTZ, TIMESTAMPTZ, UUID, VARCHAR);
DROP FUNCTION IF EXISTS end_parking_session(UUID, TIMESTAMPTZ, UUID);
DROP FUNCTION IF EXISTS get_active_sessions(UUID, UUID);
DROP FUNCTION IF EXISTS check_reservation_availability(UUID, TIMESTAMPTZ, TIMESTAMPTZ, VARCHAR, UUID);
DROP FUNCTION IF EXISTS create_reservation(UUID, UUID, TIMESTAMPTZ, TIMESTAMPTZ, VARCHAR, VARCHAR, VARCHAR, UUID, UUID);
DROP FUNCTION IF EXISTS get_daily_revenue(DATE, DATE, UUID, UUID);
DROP FUNCTION IF EXISTS get_occupancy_stats(UUID, TIMESTAMPTZ, TIMESTAMPTZ, INTERVAL);
DROP FUNCTION IF EXISTS get_monthly_performance(INTEGER, INTEGER, UUID);
DROP FUNCTION IF EXISTS search_vehicles(TEXT, UUID, INTEGER);
DROP FUNCTION IF EXISTS get_vehicle_history(UUID, INTEGER);
DROP FUNCTION IF EXISTS process_session_payment(UUID, VARCHAR, NUMERIC, UUID, VARCHAR, VARCHAR);
DROP FUNCTION IF EXISTS generate_invoice(UUID);
DROP FUNCTION IF EXISTS cleanup_expired_records();
DROP FUNCTION IF EXISTS archive_old_sessions(INTEGER, INTEGER);
DROP FUNCTION IF EXISTS normalize_license_plate(TEXT);
DROP FUNCTION IF EXISTS calculate_distance(FLOAT, FLOAT, FLOAT, FLOAT);
DROP FUNCTION IF EXISTS find_nearby_parking_lots(FLOAT, FLOAT, FLOAT, INTEGER);
DROP FUNCTION IF EXISTS get_dashboard_metrics(UUID);
DROP FUNCTION IF EXISTS export_sessions_csv(DATE, DATE, UUID);
*/

COMMIT;