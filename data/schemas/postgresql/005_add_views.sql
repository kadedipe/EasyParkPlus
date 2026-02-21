-- 005_add_views.sql
-- Advanced PostgreSQL views for parking management system
-- Includes reporting views, materialized views for performance, and business intelligence views

-- =====================================================
-- ACTIVE OPERATIONS VIEWS
-- =====================================================

-- View for current parking status across all lots
CREATE OR REPLACE VIEW v_current_parking_status AS
SELECT 
    pl.id AS lot_id,
    pl.name AS lot_name,
    pl.code AS lot_code,
    pl.total_spaces,
    pl.available_spaces,
    pl.reserved_spaces,
    pl.occupancy_rate,
    pl.status AS lot_status,
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.status = 'active') AS active_sessions,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status IN ('confirmed', 'checked_in')) AS active_reservations,
    jsonb_agg(DISTINCT jsonb_build_object(
        'level_id', plv.id,
        'level_number', plv.level_number,
        'available_spaces', plv.available_spaces,
        'total_spaces', plv.total_spaces,
        'spaces', (
            SELECT jsonb_agg(jsonb_build_object(
                'space_id', ps2.id,
                'space_number', ps2.space_number,
                'status', ps2.status,
                'space_type', ps2.space_type,
                'is_handicapped', ps2.is_handicapped,
                'is_electric', ps2.is_electric,
                'current_vehicle', (
                    SELECT jsonb_build_object(
                        'license_plate', v.license_plate,
                        'vehicle_type', v.vehicle_type
                    )
                    FROM vehicles v
                    WHERE v.id = ps2.current_vehicle_id
                )
            )) 
            FROM parking_spaces ps2 
            WHERE ps2.level_id = plv.id
        )
    )) FILTER (WHERE plv.id IS NOT NULL) AS levels
FROM parking_lots pl
LEFT JOIN parking_levels plv ON pl.id = plv.parking_lot_id
LEFT JOIN parking_sessions ps ON pl.id = ps.parking_lot_id AND ps.status = 'active'
LEFT JOIN reservations r ON pl.id = r.parking_lot_id AND r.status IN ('confirmed', 'checked_in')
GROUP BY pl.id, pl.name, pl.code, pl.total_spaces, pl.available_spaces, pl.reserved_spaces, 
         pl.occupancy_rate, pl.status;

COMMENT ON VIEW v_current_parking_status IS 'Real-time parking status across all lots with detailed level and space information';

-- View for active parking sessions with complete details
CREATE OR REPLACE VIEW v_active_sessions AS
SELECT 
    ps.id AS session_id,
    ps.session_id AS session_number,
    ps.ticket_number,
    ps.entry_time,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ps.entry_time))::INTEGER / 60 AS duration_minutes,
    ps.expected_exit_time,
    ps.is_grace_period,
    ps.grace_period_ends,
    ps.entry_method,
    ps.entry_gate_id,
    ps.entry_camera_id,
    ps.entry_image_url,
    ps.entry_lpr_plate,
    ps.entry_lpr_confidence,
    
    -- Vehicle details
    v.id AS vehicle_id,
    v.license_plate,
    v.license_plate_normalized,
    v.make,
    v.model,
    v.color,
    v.vehicle_type,
    v.is_electric,
    v.is_handicapped,
    
    -- Owner details
    u.id AS owner_id,
    u.first_name AS owner_first_name,
    u.last_name AS owner_last_name,
    u.email AS owner_email,
    u.phone AS owner_phone,
    
    -- Location details
    pl.id AS lot_id,
    pl.name AS lot_name,
    pl.code AS lot_code,
    plv.id AS level_id,
    plv.level_number,
    ps2.id AS space_id,
    ps2.space_number,
    ps2.space_type,
    
    -- Rate and billing
    r.id AS rate_id,
    r.name AS rate_name,
    r.rate_type,
    r.base_rate,
    r.rate_unit,
    r.currency,
    ps.base_amount,
    ps.tax_amount,
    ps.discount_amount,
    ps.total_amount AS estimated_total,
    
    -- Metadata
    ps.created_by_id,
    cu.first_name AS created_by_name,
    ps.created_at
FROM parking_sessions ps
JOIN vehicles v ON ps.vehicle_id = v.id
JOIN parking_spaces ps2 ON ps.parking_space_id = ps2.id
JOIN parking_levels plv ON ps2.level_id = plv.id
JOIN parking_lots pl ON ps.parking_lot_id = pl.id
LEFT JOIN users u ON v.owner_id = u.id
LEFT JOIN rates r ON ps.rate_id = r.id
LEFT JOIN users cu ON ps.created_by_id = cu.id
WHERE ps.status = 'active';

COMMENT ON VIEW v_active_sessions IS 'Complete details of all active parking sessions';

-- View for upcoming and active reservations
CREATE OR REPLACE VIEW v_reservation_status AS
SELECT 
    r.id AS reservation_id,
    r.reservation_number,
    r.start_time,
    r.end_time,
    r.check_in_time,
    r.check_out_time,
    r.status,
    EXTRACT(EPOCH FROM (r.start_time - CURRENT_TIMESTAMP))::INTEGER / 60 AS minutes_until_start,
    CASE 
        WHEN r.check_in_time IS NULL AND r.start_time <= CURRENT_TIMESTAMP THEN 'overdue'
        WHEN r.start_time <= CURRENT_TIMESTAMP AND r.start_time > CURRENT_TIMESTAMP - INTERVAL '30 minutes' THEN 'due_now'
        WHEN r.start_time > CURRENT_TIMESTAMP THEN 'upcoming'
        ELSE 'unknown'
    END AS arrival_status,
    
    -- Customer details
    r.customer_name,
    r.customer_email,
    r.customer_phone,
    
    -- Vehicle details
    r.vehicle_license_plate,
    v.id AS vehicle_id,
    v.vehicle_type,
    
    -- Location details
    pl.id AS lot_id,
    pl.name AS lot_name,
    plv.id AS level_id,
    plv.level_number,
    ps.id AS space_id,
    ps.space_number,
    
    -- Billing details
    r.base_amount,
    r.tax_amount,
    r.total_amount,
    r.deposit_amount,
    r.currency,
    r.payment_status,
    r.payment_time,
    
    -- User details
    r.user_id,
    u.first_name || ' ' || u.last_name AS user_name,
    u.email AS user_email
FROM reservations r
LEFT JOIN vehicles v ON r.vehicle_id = v.id
LEFT JOIN parking_lots pl ON r.parking_lot_id = pl.id
LEFT JOIN parking_levels plv ON ps.level_id = plv.id
LEFT JOIN parking_spaces ps ON r.parking_space_id = ps.id
LEFT JOIN users u ON r.user_id = u.id
WHERE r.status IN ('confirmed', 'checked_in')
ORDER BY r.start_time;

COMMENT ON VIEW v_reservation_status IS 'Status of all upcoming and active reservations';

-- =====================================================
-- PARKING SPACE MANAGEMENT VIEWS
-- =====================================================

-- View for parking space inventory and status
CREATE OR REPLACE VIEW v_space_inventory AS
SELECT 
    pl.id AS lot_id,
    pl.name AS lot_name,
    plv.id AS level_id,
    plv.level_number,
    ps.id AS space_id,
    ps.space_number,
    ps.space_type,
    ps.status,
    ps.is_covered,
    ps.is_reserved,
    ps.is_handicapped,
    ps.is_electric,
    ps.charging_capacity,
    ps.width,
    ps.length,
    ps.height_limit,
    
    -- Current occupancy
    CASE 
        WHEN ps.status = 'occupied' THEN (
            SELECT jsonb_build_object(
                'session_id', ps2.session_id,
                'vehicle_plate', v.license_plate,
                'entry_time', ps2.entry_time,
                'duration', EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ps2.entry_time))::INTEGER / 60
            )
            FROM parking_sessions ps2
            JOIN vehicles v ON ps2.vehicle_id = v.id
            WHERE ps2.parking_space_id = ps.id AND ps2.status = 'active'
            LIMIT 1
        )
        ELSE NULL
    END AS current_occupancy,
    
    -- Upcoming reservations
    (
        SELECT jsonb_agg(jsonb_build_object(
            'reservation_id', r.id,
            'start_time', r.start_time,
            'end_time', r.end_time,
            'customer_name', r.customer_name,
            'vehicle_plate', r.vehicle_license_plate
        ))
        FROM reservations r
        WHERE r.parking_space_id = ps.id 
          AND r.status IN ('confirmed', 'checked_in')
          AND r.start_time <= CURRENT_TIMESTAMP + INTERVAL '2 hours'
    ) AS upcoming_reservations,
    
    -- Utilization metrics
    (
        SELECT COUNT(*) 
        FROM parking_sessions ps2 
        WHERE ps2.parking_space_id = ps.id 
          AND ps2.entry_time >= CURRENT_DATE
    ) AS today_sessions,
    
    (
        SELECT COALESCE(AVG(duration_minutes), 0)
        FROM parking_sessions ps2
        WHERE ps2.parking_space_id = ps.id 
          AND ps2.status = 'completed'
          AND ps2.exit_time >= CURRENT_DATE - INTERVAL '30 days'
    ) AS avg_duration_minutes
FROM parking_spaces ps
JOIN parking_levels plv ON ps.level_id = plv.id
JOIN parking_lots pl ON plv.parking_lot_id = pl.id;

COMMENT ON VIEW v_space_inventory IS 'Complete inventory of parking spaces with current status and utilization metrics';

-- View for space utilization analysis
CREATE OR REPLACE VIEW v_space_utilization AS
SELECT 
    pl.id AS lot_id,
    pl.name AS lot_name,
    plv.level_number,
    ps.space_type,
    COUNT(ps.id) AS total_spaces,
    COUNT(ps.id) FILTER (WHERE ps.status = 'occupied') AS occupied_spaces,
    COUNT(ps.id) FILTER (WHERE ps.status = 'available') AS available_spaces,
    COUNT(ps.id) FILTER (WHERE ps.status = 'reserved') AS reserved_spaces,
    COUNT(ps.id) FILTER (WHERE ps.status = 'maintenance') AS maintenance_spaces,
    ROUND(100.0 * COUNT(ps.id) FILTER (WHERE ps.status = 'occupied') / NULLIF(COUNT(ps.id), 0), 2) AS occupancy_rate,
    
    -- Revenue by space type
    (
        SELECT COALESCE(SUM(ps2.total_amount), 0)
        FROM parking_sessions ps2
        WHERE ps2.parking_space_id IN (
            SELECT id FROM parking_spaces WHERE space_type = ps.space_type AND level_id = plv.id
        )
        AND ps2.exit_time >= CURRENT_DATE - INTERVAL '30 days'
    ) AS monthly_revenue,
    
    -- Average sessions per day
    (
        SELECT COALESCE(COUNT(*) / 30.0, 0)
        FROM parking_sessions ps2
        WHERE ps2.parking_space_id IN (
            SELECT id FROM parking_spaces WHERE space_type = ps.space_type AND level_id = plv.id
        )
        AND ps2.exit_time >= CURRENT_DATE - INTERVAL '30 days'
    ) AS avg_daily_sessions
FROM parking_spaces ps
JOIN parking_levels plv ON ps.level_id = plv.id
JOIN parking_lots pl ON plv.parking_lot_id = pl.id
GROUP BY pl.id, pl.name, plv.level_number, ps.space_type;

COMMENT ON VIEW v_space_utilization IS 'Space utilization metrics grouped by lot, level, and space type';

-- =====================================================
-- FINANCIAL AND REVENUE VIEWS
-- =====================================================

-- View for daily revenue summary
CREATE OR REPLACE VIEW v_daily_revenue AS
SELECT 
    DATE(ps.exit_time) AS revenue_date,
    pl.id AS lot_id,
    pl.name AS lot_name,
    COUNT(DISTINCT ps.id) AS total_sessions,
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.payment_status = 'paid') AS paid_sessions,
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.payment_status = 'pending') AS pending_sessions,
    
    -- Revenue amounts
    COALESCE(SUM(ps.base_amount), 0) AS total_base_amount,
    COALESCE(SUM(ps.tax_amount), 0) AS total_tax_amount,
    COALESCE(SUM(ps.discount_amount), 0) AS total_discount_amount,
    COALESCE(SUM(ps.total_amount), 0) AS total_revenue,
    
    -- Payment method breakdown
    jsonb_object_agg(
        COALESCE(p.payment_method, 'cash'),
        COALESCE(SUM(p.total_amount), 0)
    ) FILTER (WHERE p.payment_method IS NOT NULL) AS revenue_by_payment_method,
    
    -- Hourly breakdown
    jsonb_object_agg(
        EXTRACT(HOUR FROM ps.exit_time)::TEXT,
        COUNT(*)
    ) FILTER (WHERE ps.exit_time IS NOT NULL) AS sessions_by_hour,
    
    -- Statistics
    COALESCE(AVG(ps.duration_minutes), 0) AS avg_duration_minutes,
    COALESCE(AVG(ps.total_amount), 0) AS avg_transaction_value
FROM parking_sessions ps
JOIN parking_lots pl ON ps.parking_lot_id = pl.id
LEFT JOIN payments p ON ps.id = p.parking_session_id AND p.payment_status = 'completed'
WHERE ps.status = 'completed'
GROUP BY DATE(ps.exit_time), pl.id, pl.name;

COMMENT ON VIEW v_daily_revenue IS 'Daily revenue summary by parking lot';

-- View for monthly financial performance
CREATE OR REPLACE VIEW v_monthly_financials AS
SELECT 
    DATE_TRUNC('month', ps.exit_time) AS month,
    pl.id AS lot_id,
    pl.name AS lot_name,
    pl.organization_id,
    o.name AS organization_name,
    
    -- Volume metrics
    COUNT(DISTINCT ps.id) AS total_sessions,
    COUNT(DISTINCT v.id) AS unique_vehicles,
    COUNT(DISTINCT u.id) AS unique_customers,
    
    -- Revenue metrics
    COALESCE(SUM(ps.base_amount), 0) AS base_revenue,
    COALESCE(SUM(ps.tax_amount), 0) AS tax_revenue,
    COALESCE(SUM(ps.total_amount), 0) AS gross_revenue,
    COALESCE(SUM(p.total_amount), 0) AS collected_revenue,
    COALESCE(SUM(ps.total_amount) FILTER (WHERE ps.payment_status = 'pending'), 0) AS outstanding_revenue,
    
    -- Refunds and adjustments
    COALESCE(SUM(p.refund_amount), 0) AS total_refunds,
    
    -- Performance metrics
    COALESCE(AVG(ps.duration_minutes), 0) AS avg_session_duration,
    COALESCE(AVG(ps.total_amount), 0) AS avg_revenue_per_session,
    COALESCE(SUM(ps.total_amount) / NULLIF(COUNT(DISTINCT ps.id), 0), 0) AS revenue_per_session,
    COALESCE(SUM(ps.total_amount) / NULLIF(pl.total_spaces, 0), 0) AS revenue_per_space,
    
    -- Vehicle type breakdown
    jsonb_object_agg(
        v.vehicle_type,
        COUNT(*)
    ) FILTER (WHERE v.vehicle_type IS NOT NULL) AS sessions_by_vehicle_type,
    
    -- Payment method breakdown
    jsonb_object_agg(
        COALESCE(p.payment_method, 'unknown'),
        COUNT(*)
    ) FILTER (WHERE p.id IS NOT NULL) AS payments_by_method
FROM parking_sessions ps
JOIN parking_lots pl ON ps.parking_lot_id = pl.id
JOIN organizations o ON pl.organization_id = o.id
LEFT JOIN vehicles v ON ps.vehicle_id = v.id
LEFT JOIN users u ON v.owner_id = u.id
LEFT JOIN payments p ON ps.id = p.parking_session_id AND p.payment_status = 'completed'
WHERE ps.status = 'completed'
GROUP BY DATE_TRUNC('month', ps.exit_time), pl.id, pl.name, pl.organization_id, o.name;

COMMENT ON VIEW v_monthly_financials IS 'Monthly financial performance metrics by parking lot';

-- View for revenue trends and forecasting
CREATE OR REPLACE VIEW v_revenue_trends AS
WITH daily_revenue AS (
    SELECT 
        DATE(ps.exit_time) AS date,
        pl.id AS lot_id,
        SUM(ps.total_amount) AS revenue,
        COUNT(ps.id) AS sessions
    FROM parking_sessions ps
    JOIN parking_lots pl ON ps.parking_lot_id = pl.id
    WHERE ps.status = 'completed'
    GROUP BY DATE(ps.exit_time), pl.id
),
moving_averages AS (
    SELECT 
        date,
        lot_id,
        revenue,
        sessions,
        AVG(revenue) OVER (PARTITION BY lot_id ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS revenue_ma_7d,
        AVG(revenue) OVER (PARTITION BY lot_id ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS revenue_ma_30d,
        revenue - LAG(revenue, 1) OVER (PARTITION BY lot_id ORDER BY date) AS daily_change,
        (revenue - LAG(revenue, 7) OVER (PARTITION BY lot_id ORDER BY date)) / NULLIF(LAG(revenue, 7) OVER (PARTITION BY lot_id ORDER BY date), 0) * 100 AS weekly_growth_pct
    FROM daily_revenue
)
SELECT 
    dr.*,
    pl.name AS lot_name,
    EXTRACT(DOW FROM dr.date) AS day_of_week,
    EXTRACT(WEEK FROM dr.date) AS week_number,
    EXTRACT(MONTH FROM dr.date) AS month_number,
    EXTRACT(YEAR FROM dr.date) AS year
FROM moving_averages dr
JOIN parking_lots pl ON dr.lot_id = pl.id;

COMMENT ON VIEW v_revenue_trends IS 'Revenue trends with moving averages and growth metrics';

-- =====================================================
-- CUSTOMER AND VEHICLE VIEWS
-- =====================================================

-- View for customer lifetime value and behavior
CREATE OR REPLACE VIEW v_customer_analytics AS
SELECT 
    u.id AS user_id,
    u.first_name,
    u.last_name,
    u.email,
    u.phone,
    u.created_at AS registration_date,
    
    -- Vehicle summary
    COUNT(DISTINCT v.id) AS total_vehicles,
    jsonb_agg(DISTINCT jsonb_build_object(
        'vehicle_id', v.id,
        'license_plate', v.license_plate,
        'vehicle_type', v.vehicle_type,
        'make', v.make,
        'model', v.model
    )) FILTER (WHERE v.id IS NOT NULL) AS vehicles,
    
    -- Session metrics
    COUNT(DISTINCT ps.id) AS total_sessions,
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.status = 'completed') AS completed_sessions,
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.payment_status = 'paid') AS paid_sessions,
    COUNT(DISTINCT r.id) AS total_reservations,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'no_show') AS no_show_reservations,
    
    -- Financial metrics
    COALESCE(SUM(ps.total_amount), 0) AS lifetime_value,
    COALESCE(AVG(ps.total_amount), 0) AS avg_transaction_value,
    COALESCE(MAX(ps.total_amount), 0) AS max_transaction_value,
    
    -- Temporal metrics
    MIN(ps.entry_time) AS first_visit,
    MAX(ps.entry_time) AS last_visit,
    EXTRACT(DAY FROM (CURRENT_TIMESTAMP - MAX(ps.entry_time))) AS days_since_last_visit,
    
    -- Favorite locations
    (
        SELECT jsonb_agg(jsonb_build_object(
            'lot_id', pl.id,
            'lot_name', pl.name,
            'visit_count', COUNT(*)
        ))
        FROM parking_sessions ps2
        JOIN parking_lots pl ON ps2.parking_lot_id = pl.id
        WHERE ps2.vehicle_id IN (SELECT id FROM vehicles WHERE owner_id = u.id)
        GROUP BY pl.id, pl.name
        ORDER BY COUNT(*) DESC
        LIMIT 3
    ) AS favorite_locations,
    
    -- Risk indicators
    CASE 
        WHEN COUNT(DISTINCT ps.id) FILTER (WHERE ps.payment_status = 'pending') > 3 THEN 'high_risk'
        WHEN COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'no_show') > 2 THEN 'high_risk'
        WHEN COUNT(DISTINCT ps.id) FILTER (WHERE ps.payment_status = 'pending') > 1 THEN 'medium_risk'
        ELSE 'low_risk'
    END AS risk_profile
FROM users u
LEFT JOIN vehicles v ON u.id = v.owner_id
LEFT JOIN parking_sessions ps ON v.id = ps.vehicle_id
LEFT JOIN reservations r ON u.id = r.user_id
WHERE u.is_active = true
GROUP BY u.id, u.first_name, u.last_name, u.email, u.phone, u.created_at;

COMMENT ON VIEW v_customer_analytics IS 'Customer lifetime value and behavior analytics';

-- View for vehicle analytics and history
CREATE OR REPLACE VIEW v_vehicle_analytics AS
SELECT 
    v.id AS vehicle_id,
    v.license_plate,
    v.license_plate_normalized,
    v.make,
    v.model,
    v.color,
    v.year,
    v.vehicle_type,
    v.is_electric,
    v.is_handicapped,
    
    -- Owner details
    u.id AS owner_id,
    u.first_name || ' ' || u.last_name AS owner_name,
    u.email AS owner_email,
    u.phone AS owner_phone,
    
    -- Visit statistics
    COUNT(DISTINCT ps.id) AS total_visits,
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.status = 'completed') AS completed_visits,
    COUNT(DISTINCT r.id) AS total_reservations,
    COUNT(DISTINCT bl.id) AS blacklist_count,
    
    -- Financial statistics
    COALESCE(SUM(ps.total_amount), 0) AS total_paid,
    COALESCE(AVG(ps.total_amount), 0) AS avg_payment,
    COALESCE(MIN(ps.total_amount), 0) AS min_payment,
    COALESCE(MAX(ps.total_amount), 0) AS max_payment,
    
    -- Temporal patterns
    MIN(ps.entry_time) AS first_seen,
    MAX(ps.entry_time) AS last_seen,
    MODE() WITHIN GROUP (ORDER BY EXTRACT(HOUR FROM ps.entry_time)) AS preferred_hour,
    MODE() WITHIN GROUP (ORDER BY EXTRACT(DOW FROM ps.entry_time)) AS preferred_day,
    
    -- Average duration
    COALESCE(AVG(ps.duration_minutes), 0) AS avg_duration_minutes,
    
    -- Favorite parking lots
    (
        SELECT pl.name
        FROM parking_sessions ps2
        JOIN parking_lots pl ON ps2.parking_lot_id = pl.id
        WHERE ps2.vehicle_id = v.id
        GROUP BY pl.id, pl.name
        ORDER BY COUNT(*) DESC
        LIMIT 1
    ) AS favorite_lot,
    
    -- Risk flags
    v.id IN (SELECT vehicle_id FROM blacklisted_vehicles WHERE is_active = true) AS is_blacklisted,
    EXISTS(
        SELECT 1 FROM parking_sessions ps2 
        WHERE ps2.vehicle_id = v.id 
          AND ps2.payment_status = 'pending' 
          AND ps2.exit_time < CURRENT_TIMESTAMP - INTERVAL '7 days'
    ) AS has_overdue_payments
FROM vehicles v
LEFT JOIN users u ON v.owner_id = u.id
LEFT JOIN parking_sessions ps ON v.id = ps.vehicle_id
LEFT JOIN reservations r ON v.id = r.vehicle_id
LEFT JOIN blacklisted_vehicles bl ON v.id = bl.vehicle_id AND bl.is_active = true
GROUP BY v.id, v.license_plate, v.license_plate_normalized, v.make, v.model, v.color, 
         v.year, v.vehicle_type, v.is_electric, v.is_handicapped, u.id, u.first_name, 
         u.last_name, u.email, u.phone;

COMMENT ON VIEW v_vehicle_analytics IS 'Comprehensive vehicle analytics including visit patterns and financial history';

-- =====================================================
-- PERFORMANCE AND OPERATIONS VIEWS
-- =====================================================

-- View for parking lot performance metrics
CREATE OR REPLACE VIEW v_lot_performance AS
SELECT 
    pl.id AS lot_id,
    pl.name AS lot_name,
    pl.code AS lot_code,
    pl.address,
    pl.city,
    pl.state,
    pl.country,
    pl.total_spaces,
    pl.available_spaces,
    pl.reserved_spaces,
    pl.occupancy_rate,
    pl.status,
    
    -- Today's performance
    COUNT(DISTINCT ps.id) FILTER (WHERE DATE(ps.entry_time) = CURRENT_DATE) AS today_sessions,
    COALESCE(SUM(ps.total_amount) FILTER (WHERE DATE(ps.exit_time) = CURRENT_DATE), 0) AS today_revenue,
    
    -- Weekly performance
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.entry_time >= CURRENT_DATE - INTERVAL '7 days') AS weekly_sessions,
    COALESCE(SUM(ps.total_amount) FILTER (WHERE ps.exit_time >= CURRENT_DATE - INTERVAL '7 days'), 0) AS weekly_revenue,
    
    -- Monthly performance
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.entry_time >= CURRENT_DATE - INTERVAL '30 days') AS monthly_sessions,
    COALESCE(SUM(ps.total_amount) FILTER (WHERE ps.exit_time >= CURRENT_DATE - INTERVAL '30 days'), 0) AS monthly_revenue,
    
    -- Peak hours
    (
        SELECT EXTRACT(HOUR FROM entry_time)
        FROM parking_sessions ps2
        WHERE ps2.parking_lot_id = pl.id
        GROUP BY EXTRACT(HOUR FROM entry_time)
        ORDER BY COUNT(*) DESC
        LIMIT 1
    ) AS peak_hour,
    
    -- Average occupancy by hour
    (
        SELECT jsonb_object_agg(hour, avg_occupancy)
        FROM (
            SELECT 
                EXTRACT(HOUR FROM entry_time) AS hour,
                AVG(EXTRACT(EPOCH FROM (COALESCE(exit_time, CURRENT_TIMESTAMP) - entry_time)) / 3600) AS avg_occupancy
            FROM parking_sessions ps2
            WHERE ps2.parking_lot_id = pl.id
            GROUP BY EXTRACT(HOUR FROM entry_time)
        ) hourly
    ) AS hourly_occupancy,
    
    -- Vehicle type breakdown
    (
        SELECT jsonb_object_agg(vt, cnt)
        FROM (
            SELECT v.vehicle_type, COUNT(*) AS cnt
            FROM parking_sessions ps2
            JOIN vehicles v ON ps2.vehicle_id = v.id
            WHERE ps2.parking_lot_id = pl.id
            GROUP BY v.vehicle_type
        ) vt_counts
    ) AS vehicle_type_breakdown,
    
    -- Revenue per space
    COALESCE(SUM(ps.total_amount) / NULLIF(pl.total_spaces, 0), 0) AS revenue_per_space,
    
    -- Turnover rate (sessions per space per day)
    COALESCE(COUNT(DISTINCT ps.id) / NULLIF(pl.total_spaces, 0) / 30.0, 0) AS daily_turnover_rate
FROM parking_lots pl
LEFT JOIN parking_sessions ps ON pl.id = ps.parking_lot_id
GROUP BY pl.id, pl.name, pl.code, pl.address, pl.city, pl.state, pl.country, 
         pl.total_spaces, pl.available_spaces, pl.reserved_spaces, pl.occupancy_rate, pl.status;

COMMENT ON VIEW v_lot_performance IS 'Key performance indicators for each parking lot';

-- View for gate and entrance activity
CREATE OR REPLACE VIEW v_gate_activity AS
SELECT 
    g.id AS gate_id,
    g.name AS gate_name,
    g.gate_type,
    g.status AS gate_status,
    ee.id AS entrance_id,
    ee.name AS entrance_name,
    ee.type AS entrance_type,
    pl.id AS lot_id,
    pl.name AS lot_name,
    
    -- Today's activity
    COUNT(DISTINCT ge.id) FILTER (WHERE DATE(ge.timestamp) = CURRENT_DATE) AS today_events,
    COUNT(DISTINCT ge.id) FILTER (WHERE DATE(ge.timestamp) = CURRENT_DATE AND ge.event_type = 'open') AS today_opens,
    COUNT(DISTINCT ge.id) FILTER (WHERE DATE(ge.timestamp) = CURRENT_DATE AND ge.event_type = 'close') AS today_closes,
    COUNT(DISTINCT ge.id) FILTER (WHERE DATE(ge.timestamp) = CURRENT_DATE AND ge.result = 'failure') AS today_failures,
    
    -- Recent activity
    MAX(ge.timestamp) AS last_activity,
    MODE() WITHIN GROUP (ORDER BY ge.trigger_method) AS most_common_trigger,
    
    -- Performance metrics
    AVG(EXTRACT(EPOCH FROM (ge.timestamp - LAG(ge.timestamp) OVER (PARTITION BY g.id ORDER BY ge.timestamp)))) AS avg_time_between_events,
    
    -- Uptime
    CASE 
        WHEN MAX(ge.timestamp) < CURRENT_TIMESTAMP - INTERVAL '5 minutes' THEN 'offline'
        WHEN COUNT(DISTINCT ge.id) FILTER (WHERE ge.result = 'failure') > 10 THEN 'degraded'
        ELSE 'operational'
    END AS health_status
FROM gates g
LEFT JOIN entrance_exits ee ON g.entrance_exit_id = ee.id
LEFT JOIN parking_lots pl ON g.parking_lot_id = pl.id
LEFT JOIN gate_events ge ON g.id = ge.gate_id AND ge.timestamp >= CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY g.id, g.name, g.gate_type, g.status, ee.id, ee.name, ee.type, pl.id, pl.name;

COMMENT ON VIEW v_gate_activity IS 'Gate activity and performance monitoring';

-- =====================================================
-- COMPLIANCE AND AUDIT VIEWS
-- =====================================================

-- View for audit trail with context
CREATE OR REPLACE VIEW v_audit_trail AS
SELECT 
    al.id AS audit_id,
    al.created_at AS timestamp,
    al.action,
    al.entity_type,
    al.entity_id,
    u.id AS user_id,
    u.username,
    u.email AS user_email,
    CONCAT(u.first_name, ' ', u.last_name) AS user_name,
    al.ip_address,
    al.user_agent,
    al.request_id,
    al.details,
    
    -- Before/after values
    al.old_values,
    al.new_values,
    
    -- Entity context
    CASE al.entity_type
        WHEN 'parking_sessions' THEN (SELECT license_plate FROM vehicles v JOIN parking_sessions ps ON v.id = ps.vehicle_id WHERE ps.id::TEXT = al.entity_id::TEXT)
        WHEN 'vehicles' THEN (SELECT license_plate FROM vehicles WHERE id::TEXT = al.entity_id::TEXT)
        WHEN 'users' THEN (SELECT email FROM users WHERE id::TEXT = al.entity_id::TEXT)
        ELSE NULL
    END AS entity_identifier,
    
    -- Time context
    EXTRACT(HOUR FROM al.created_at) AS hour_of_day,
    EXTRACT(DOW FROM al.created_at) AS day_of_week,
    CASE 
        WHEN EXTRACT(HOUR FROM al.created_at) BETWEEN 9 AND 17 THEN 'business_hours'
        ELSE 'after_hours'
    END AS time_category
FROM activity_logs al
LEFT JOIN users u ON al.user_id = u.id;

COMMENT ON VIEW v_audit_trail IS 'Complete audit trail with user and entity context';

-- View for compliance reporting
CREATE OR REPLACE VIEW v_compliance_report AS
SELECT 
    DATE_TRUNC('month', al.created_at) AS report_month,
    al.action,
    al.entity_type,
    COUNT(*) AS total_actions,
    COUNT(DISTINCT al.user_id) AS unique_users,
    COUNT(DISTINCT al.entity_id) AS unique_entities,
    
    -- User breakdown
    jsonb_object_agg(
        COALESCE(u.role, 'unknown'),
        COUNT(*)
    ) FILTER (WHERE u.id IS NOT NULL) AS actions_by_role,
    
    -- Time breakdown
    COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM al.created_at) BETWEEN 9 AND 17) AS business_hour_actions,
    COUNT(*) FILTER (WHERE EXTRACT(HOUR FROM al.created_at) NOT BETWEEN 9 AND 17) AS after_hour_actions,
    
    -- Success/failure
    COUNT(*) FILTER (WHERE al.details->>'error' IS NULL) AS successful_actions,
    COUNT(*) FILTER (WHERE al.details->>'error' IS NOT NULL) AS failed_actions,
    
    -- IP diversity
    COUNT(DISTINCT al.ip_address) AS unique_ip_addresses,
    
    -- Sensitive operations
    COUNT(*) FILTER (WHERE al.entity_type IN ('payments', 'users') AND al.action IN ('UPDATE', 'DELETE')) AS sensitive_operations
FROM activity_logs al
LEFT JOIN users u ON al.user_id = u.id
GROUP BY DATE_TRUNC('month', al.created_at), al.action, al.entity_type;

COMMENT ON VIEW v_compliance_report IS 'Monthly compliance and audit summary report';

-- =====================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- =====================================================

-- Materialized view for daily aggregations (refreshed nightly)
CREATE MATERIALIZED VIEW mv_daily_aggregates AS
SELECT 
    DATE(ps.exit_time) AS date,
    pl.id AS lot_id,
    pl.name AS lot_name,
    o.id AS organization_id,
    o.name AS organization_name,
    
    -- Session counts
    COUNT(DISTINCT ps.id) AS total_sessions,
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.payment_status = 'paid') AS paid_sessions,
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.payment_status = 'pending') AS pending_sessions,
    COUNT(DISTINCT v.id) AS unique_vehicles,
    COUNT(DISTINCT u.id) AS unique_customers,
    
    -- Revenue
    COALESCE(SUM(ps.total_amount), 0) AS total_revenue,
    COALESCE(AVG(ps.total_amount), 0) AS avg_revenue,
    COALESCE(MAX(ps.total_amount), 0) AS max_revenue,
    
    -- Duration
    COALESCE(AVG(ps.duration_minutes), 0) AS avg_duration,
    COALESCE(SUM(ps.duration_minutes), 0) AS total_duration,
    
    -- Vehicle types
    jsonb_object_agg(
        COALESCE(v.vehicle_type, 'unknown'),
        COUNT(*)
    ) AS sessions_by_vehicle_type,
    
    -- Hourly distribution
    jsonb_object_agg(
        EXTRACT(HOUR FROM ps.entry_time)::TEXT,
        COUNT(*)
    ) AS sessions_by_hour,
    
    -- Statistics
    COUNT(*) FILTER (WHERE ps.is_grace_period) AS grace_period_sessions,
    COUNT(*) FILTER (WHERE ps.duration_minutes > 1440) AS long_stay_sessions
FROM parking_sessions ps
JOIN parking_lots pl ON ps.parking_lot_id = pl.id
JOIN organizations o ON pl.organization_id = o.id
LEFT JOIN vehicles v ON ps.vehicle_id = v.id
LEFT JOIN users u ON v.owner_id = u.id
WHERE ps.status = 'completed'
GROUP BY DATE(ps.exit_time), pl.id, pl.name, o.id, o.name
WITH DATA;

-- Create indexes on materialized view
CREATE UNIQUE INDEX idx_mv_daily_aggregates_date_lot 
    ON mv_daily_aggregates (date, lot_id);
CREATE INDEX idx_mv_daily_aggregates_org_date 
    ON mv_daily_aggregates (organization_id, date);

COMMENT ON MATERIALIZED VIEW mv_daily_aggregates IS 'Daily aggregated metrics for reporting (refreshed nightly)';

-- Materialized view for real-time occupancy (refreshed every 5 minutes)
CREATE MATERIALIZED VIEW mv_realtime_occupancy AS
SELECT 
    pl.id AS lot_id,
    pl.name AS lot_name,
    pl.total_spaces,
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.status = 'active') AS active_sessions,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status IN ('confirmed', 'checked_in')) AS active_reservations,
    pl.total_spaces - COUNT(DISTINCT ps.id) - COUNT(DISTINCT r.id) AS available_spaces,
    ROUND(100.0 * (COUNT(DISTINCT ps.id) + COUNT(DISTINCT r.id)) / NULLIF(pl.total_spaces, 0), 2) AS occupancy_rate,
    
    -- Level breakdown
    jsonb_object_agg(
        plv.level_number::TEXT,
        jsonb_build_object(
            'total', plv.total_spaces,
            'occupied', COUNT(DISTINCT ps2.id) FILTER (WHERE ps2.status = 'active' AND ps2.parking_space_id IN (SELECT id FROM parking_spaces WHERE level_id = plv.id)),
            'reserved', COUNT(DISTINCT r2.id) FILTER (WHERE r2.status IN ('confirmed', 'checked_in') AND r2.parking_space_id IN (SELECT id FROM parking_spaces WHERE level_id = plv.id))
        )
    ) AS level_occupancy,
    
    -- Last updated
    NOW() AS last_refreshed
FROM parking_lots pl
LEFT JOIN parking_levels plv ON pl.id = plv.parking_lot_id
LEFT JOIN parking_sessions ps ON pl.id = ps.parking_lot_id AND ps.status = 'active'
LEFT JOIN reservations r ON pl.id = r.parking_lot_id AND r.status IN ('confirmed', 'checked_in')
LEFT JOIN parking_sessions ps2 ON pl.id = ps2.parking_lot_id
LEFT JOIN reservations r2 ON pl.id = r2.parking_lot_id
GROUP BY pl.id, pl.name, pl.total_spaces, plv.id, plv.level_number, plv.total_spaces
WITH DATA;

-- Create indexes on materialized view
CREATE UNIQUE INDEX idx_mv_realtime_occupancy_lot 
    ON mv_realtime_occupancy (lot_id);

COMMENT ON MATERIALIZED VIEW mv_realtime_occupancy IS 'Real-time occupancy by lot (refreshed every 5 minutes)';

-- Materialized view for customer 360 view
CREATE MATERIALIZED VIEW mv_customer_360 AS
SELECT 
    u.id AS user_id,
    u.email,
    u.first_name,
    u.last_name,
    u.phone,
    u.created_at AS registered_since,
    
    -- Vehicle summary
    COUNT(DISTINCT v.id) AS vehicle_count,
    jsonb_agg(DISTINCT jsonb_build_object(
        'plate', v.license_plate,
        'type', v.vehicle_type,
        'make', v.make,
        'model', v.model
    )) AS vehicles,
    
    -- Session summary
    COUNT(DISTINCT ps.id) AS lifetime_sessions,
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.entry_time >= CURRENT_DATE - INTERVAL '30 days') AS sessions_last_30d,
    COALESCE(SUM(ps.total_amount), 0) AS lifetime_value,
    COALESCE(SUM(ps.total_amount) FILTER (WHERE ps.entry_time >= CURRENT_DATE - INTERVAL '30 days'), 0) AS value_last_30d,
    
    -- Reservation summary
    COUNT(DISTINCT r.id) AS total_reservations,
    COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'no_show') AS no_shows,
    
    -- Risk metrics
    CASE 
        WHEN COUNT(DISTINCT ps.id) FILTER (WHERE ps.payment_status = 'pending' AND ps.exit_time < CURRENT_DATE - 7) > 0 THEN 'high_risk'
        WHEN COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'no_show' AND r.start_time > CURRENT_DATE - 30) > 2 THEN 'high_risk'
        WHEN COUNT(DISTINCT ps.id) FILTER (WHERE ps.payment_status = 'pending') > 0 THEN 'medium_risk'
        ELSE 'low_risk'
    END AS risk_level,
    
    -- Last activity
    GREATEST(
        MAX(ps.entry_time),
        MAX(r.created_at)
    ) AS last_activity,
    
    -- Preferred lot
    (
        SELECT pl.name
        FROM parking_sessions ps2
        JOIN parking_lots pl ON ps2.parking_lot_id = pl.id
        WHERE ps2.vehicle_id IN (SELECT id FROM vehicles WHERE owner_id = u.id)
        GROUP BY pl.id, pl.name
        ORDER BY COUNT(*) DESC
        LIMIT 1
    ) AS preferred_lot
FROM users u
LEFT JOIN vehicles v ON u.id = v.owner_id
LEFT JOIN parking_sessions ps ON v.id = ps.vehicle_id
LEFT JOIN reservations r ON u.id = r.user_id
WHERE u.is_active = true
GROUP BY u.id, u.email, u.first_name, u.last_name, u.phone, u.created_at
WITH DATA;

-- Create indexes on materialized view
CREATE UNIQUE INDEX idx_mv_customer_360_user ON mv_customer_360 (user_id);
CREATE INDEX idx_mv_customer_360_risk ON mv_customer_360 (risk_level);
CREATE INDEX idx_mv_customer_360_last_activity ON mv_customer_360 (last_activity);

COMMENT ON MATERIALIZED VIEW mv_customer_360 IS 'Customer 360-degree view with risk assessment';

-- =====================================================
-- VIEW DEPENDENCIES AND MAINTENANCE
-- =====================================================

-- Function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_materialized_views()
RETURNS void AS $$
BEGIN
    -- Refresh daily aggregates at 1 AM
    IF EXTRACT(HOUR FROM CURRENT_TIMESTAMP) = 1 THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_aggregates;
    END IF;
    
    -- Refresh real-time occupancy every 5 minutes
    IF EXTRACT(MINUTE FROM CURRENT_TIMESTAMP)::INTEGER % 5 = 0 THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_realtime_occupancy;
    END IF;
    
    -- Refresh customer 360 daily at 2 AM
    IF EXTRACT(HOUR FROM CURRENT_TIMESTAMP) = 2 THEN
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_customer_360;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION refresh_materialized_views() IS 'Refreshes materialized views based on schedule';

-- View to monitor materialized view refresh status
CREATE OR REPLACE VIEW v_mv_refresh_status AS
SELECT
    schemaname,
    matviewname,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) AS size,
    obj_description(c.oid) AS comment,
    now() - pg_last_auto_vacuum(c.oid) AS last_auto_vacuum,
    now() - pg_last_auto_analyze(c.oid) AS last_auto_analyze
FROM pg_matviews
JOIN pg_class c ON c.relname = matviewname
ORDER BY pg_total_relation_size(schemaname||'.'||matviewname) DESC;

COMMENT ON VIEW v_mv_refresh_status IS 'Materialized view sizes and maintenance status';

-- =====================================================
-- VIEW DOCUMENTATION
-- =====================================================

COMMENT ON VIEW v_current_parking_status IS 'Real-time parking status across all lots';
COMMENT ON VIEW v_active_sessions IS 'Complete details of all active parking sessions';
COMMENT ON VIEW v_reservation_status IS 'Status of all upcoming and active reservations';
COMMENT ON VIEW v_space_inventory IS 'Complete inventory of parking spaces with current status';
COMMENT ON VIEW v_space_utilization IS 'Space utilization metrics grouped by lot, level, and space type';
COMMENT ON VIEW v_daily_revenue IS 'Daily revenue summary by parking lot';
COMMENT ON VIEW v_monthly_financials IS 'Monthly financial performance metrics by parking lot';
COMMENT ON VIEW v_revenue_trends IS 'Revenue trends with moving averages and growth metrics';
COMMENT ON VIEW v_customer_analytics IS 'Customer lifetime value and behavior analytics';
COMMENT ON VIEW v_vehicle_analytics IS 'Comprehensive vehicle analytics including visit patterns';
COMMENT ON VIEW v_lot_performance IS 'Key performance indicators for each parking lot';
COMMENT ON VIEW v_gate_activity IS 'Gate activity and performance monitoring';
COMMENT ON VIEW v_audit_trail IS 'Complete audit trail with user and entity context';
COMMENT ON VIEW v_compliance_report IS 'Monthly compliance and audit summary report';

-- =====================================================
-- ROLLBACK INSTRUCTIONS
-- =====================================================

/*
-- To rollback this migration, run:

-- Drop materialized views first
DROP MATERIALIZED VIEW IF EXISTS mv_customer_360 CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_realtime_occupancy CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_daily_aggregates CASCADE;

-- Drop regular views
DROP VIEW IF EXISTS v_mv_refresh_status CASCADE;
DROP VIEW IF EXISTS v_compliance_report CASCADE;
DROP VIEW IF EXISTS v_audit_trail CASCADE;
DROP VIEW IF EXISTS v_gate_activity CASCADE;
DROP VIEW IF EXISTS v_lot_performance CASCADE;
DROP VIEW IF EXISTS v_vehicle_analytics CASCADE;
DROP VIEW IF EXISTS v_customer_analytics CASCADE;
DROP VIEW IF EXISTS v_revenue_trends CASCADE;
DROP VIEW IF EXISTS v_monthly_financials CASCADE;
DROP VIEW IF EXISTS v_daily_revenue CASCADE;
DROP VIEW IF EXISTS v_space_utilization CASCADE;
DROP VIEW IF EXISTS v_space_inventory CASCADE;
DROP VIEW IF EXISTS v_reservation_status CASCADE;
DROP VIEW IF EXISTS v_active_sessions CASCADE;
DROP VIEW IF EXISTS v_current_parking_status CASCADE;

-- Drop function
DROP FUNCTION IF EXISTS refresh_materialized_views();
*/

COMMIT;