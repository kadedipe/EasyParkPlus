-- 006_add_partitions.sql
-- Table partitioning for parking management system
-- Implements partitioning for large tables to improve query performance and data management

-- =====================================================
-- ENABLE REQUIRED EXTENSIONS
-- =====================================================

CREATE EXTENSION IF NOT EXISTS pg_partman;
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- =====================================================
-- PARKING SESSIONS PARTITIONING (BY MONTH)
-- =====================================================

-- Create parent table for partitioned parking_sessions
CREATE TABLE parking_sessions_partitioned (
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    session_id VARCHAR(100) NOT NULL,
    ticket_number VARCHAR(100),
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
    parking_lot_id UUID NOT NULL,
    parking_space_id UUID,
    vehicle_id UUID,
    reservation_id UUID,
    created_by_id UUID,
    ended_by_id UUID,
    
    -- Partition by range on entry_time
    PRIMARY KEY (id, entry_time)
) PARTITION BY RANGE (entry_time);

-- Create indexes on parent table
CREATE INDEX idx_sessions_partitioned_lot_status ON parking_sessions_partitioned (parking_lot_id, status);
CREATE INDEX idx_sessions_partitioned_vehicle ON parking_sessions_partitioned (vehicle_id, entry_time);
CREATE INDEX idx_sessions_partitioned_exit_time ON parking_sessions_partitioned (exit_time);
CREATE INDEX idx_sessions_partitioned_payment_status ON parking_sessions_partitioned (payment_status);

-- Create monthly partitions
DO $$
DECLARE
    start_date DATE := '2024-01-01';
    end_date DATE := '2026-12-31';
    current_date DATE;
    partition_name TEXT;
    partition_start DATE;
    partition_end DATE;
BEGIN
    current_date := start_date;
    
    WHILE current_date <= end_date LOOP
        partition_start := current_date;
        partition_end := current_date + INTERVAL '1 month';
        partition_name := 'parking_sessions_' || TO_CHAR(current_date, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF parking_sessions_partitioned
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            partition_start,
            partition_end
        );
        
        -- Create local indexes for each partition
        EXECUTE format('
            CREATE INDEX idx_%I_entry_time ON %I (entry_time)',
            partition_name, partition_name
        );
        
        EXECUTE format('
            CREATE INDEX idx_%I_lot_status ON %I (parking_lot_id, status)',
            partition_name, partition_name
        );
        
        EXECUTE format('
            CREATE INDEX idx_%I_vehicle ON %I (vehicle_id)',
            partition_name, partition_name
        );
        
        current_date := partition_end;
    END LOOP;
END;
$$;

-- Create default partition for future dates
CREATE TABLE parking_sessions_default PARTITION OF parking_sessions_partitioned
    DEFAULT;

-- =====================================================
-- SENSOR DATA PARTITIONING (BY DAY)
-- =====================================================

-- Create parent table for partitioned sensor_data
CREATE TABLE sensor_data_partitioned (
    id UUID NOT NULL,
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
    sensor_id UUID NOT NULL,
    parking_space_id UUID,
    
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create indexes on parent
CREATE INDEX idx_sensor_data_partitioned_sensor_timestamp 
    ON sensor_data_partitioned (sensor_id, timestamp);
CREATE INDEX idx_sensor_data_partitioned_space_timestamp 
    ON sensor_data_partitioned (parking_space_id, timestamp);

-- Create daily partitions
DO $$
DECLARE
    start_date DATE := '2024-01-01';
    end_date DATE := '2026-12-31';
    current_date DATE;
    partition_name TEXT;
BEGIN
    current_date := start_date;
    
    WHILE current_date <= end_date LOOP
        partition_name := 'sensor_data_' || TO_CHAR(current_date, 'YYYY_MM_DD');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF sensor_data_partitioned
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            current_date,
            current_date + INTERVAL '1 day'
        );
        
        -- Create local indexes
        EXECUTE format('
            CREATE INDEX idx_%I_sensor ON %I (sensor_id)',
            partition_name, partition_name
        );
        
        current_date := current_date + INTERVAL '1 day';
    END LOOP;
END;
$$;

-- Create default partition
CREATE TABLE sensor_data_default PARTITION OF sensor_data_partitioned
    DEFAULT;

-- =====================================================
-- PAYMENTS PARTITIONING (BY MONTH)
-- =====================================================

-- Create parent table for partitioned payments
CREATE TABLE payments_partitioned (
    id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    version BIGINT NOT NULL DEFAULT 1,
    deleted_at TIMESTAMP WITH TIME ZONE,
    payment_number VARCHAR(100) NOT NULL,
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
    processed_by_id UUID,
    
    PRIMARY KEY (id, payment_time)
) PARTITION BY RANGE (payment_time);

-- Create indexes
CREATE INDEX idx_payments_partitioned_session ON payments_partitioned (parking_session_id);
CREATE INDEX idx_payments_partitioned_status ON payments_partitioned (payment_status);
CREATE INDEX idx_payments_partitioned_transaction ON payments_partitioned (transaction_id);

-- Create monthly partitions
DO $$
DECLARE
    start_date DATE := '2024-01-01';
    end_date DATE := '2026-12-31';
    current_date DATE;
    partition_name TEXT;
BEGIN
    current_date := start_date;
    
    WHILE current_date <= end_date LOOP
        partition_name := 'payments_' || TO_CHAR(current_date, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF payments_partitioned
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            current_date,
            current_date + INTERVAL '1 month'
        );
        
        current_date := current_date + INTERVAL '1 month';
    END LOOP;
END;
$$;

-- =====================================================
-- ACTIVITY LOGS PARTITIONING (BY MONTH)
-- =====================================================

-- Create parent table for partitioned activity_logs
CREATE TABLE activity_logs_partitioned (
    id UUID NOT NULL,
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
    user_id UUID,
    
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create indexes
CREATE INDEX idx_activity_logs_partitioned_entity 
    ON activity_logs_partitioned (entity_type, entity_id);
CREATE INDEX idx_activity_logs_partitioned_user 
    ON activity_logs_partitioned (user_id, created_at);
CREATE INDEX idx_activity_logs_partitioned_action 
    ON activity_logs_partitioned (action, created_at);

-- Create monthly partitions
DO $$
DECLARE
    start_date DATE := '2024-01-01';
    end_date DATE := '2026-12-31';
    current_date DATE;
    partition_name TEXT;
BEGIN
    current_date := start_date;
    
    WHILE current_date <= end_date LOOP
        partition_name := 'activity_logs_' || TO_CHAR(current_date, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF activity_logs_partitioned
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            current_date,
            current_date + INTERVAL '1 month'
        );
        
        current_date := current_date + INTERVAL '1 month';
    END LOOP;
END;
$$;

-- =====================================================
-- CAMERA EVENTS PARTITIONING (BY DAY)
-- =====================================================

-- Create parent table for partitioned camera_events
CREATE TABLE camera_events_partitioned (
    id UUID NOT NULL,
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
    camera_id UUID NOT NULL,
    parking_session_id UUID,
    vehicle_id UUID,
    
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create indexes
CREATE INDEX idx_camera_events_partitioned_camera 
    ON camera_events_partitioned (camera_id, timestamp);
CREATE INDEX idx_camera_events_partitioned_plate 
    ON camera_events_partitioned (detected_plate);
CREATE INDEX idx_camera_events_partitioned_session 
    ON camera_events_partitioned (parking_session_id);

-- Create daily partitions
DO $$
DECLARE
    start_date DATE := '2024-01-01';
    end_date DATE := '2026-12-31';
    current_date DATE;
    partition_name TEXT;
BEGIN
    current_date := start_date;
    
    WHILE current_date <= end_date LOOP
        partition_name := 'camera_events_' || TO_CHAR(current_date, 'YYYY_MM_DD');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF camera_events_partitioned
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            current_date,
            current_date + INTERVAL '1 day'
        );
        
        current_date := current_date + INTERVAL '1 day';
    END LOOP;
END;
$$;

-- =====================================================
-- AUTOMATIC PARTITION MANAGEMENT
-- =====================================================

-- Function to create future partitions automatically
CREATE OR REPLACE FUNCTION create_future_partitions()
RETURNS void AS $$
DECLARE
    future_months INTEGER := 3;
    next_month DATE;
    partition_name TEXT;
BEGIN
    -- Create parking sessions partitions
    FOR i IN 1..future_months LOOP
        next_month := DATE_TRUNC('month', CURRENT_DATE + (i || ' months')::INTERVAL);
        partition_name := 'parking_sessions_' || TO_CHAR(next_month, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF parking_sessions_partitioned
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            next_month,
            next_month + INTERVAL '1 month'
        );
    END LOOP;
    
    -- Create sensor data partitions
    FOR i IN 1..7 LOOP
        next_month := CURRENT_DATE + (i || ' days')::INTERVAL;
        partition_name := 'sensor_data_' || TO_CHAR(next_month, 'YYYY_MM_DD');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF sensor_data_partitioned
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            next_month,
            next_month + INTERVAL '1 day'
        );
    END LOOP;
    
    -- Create payments partitions
    FOR i IN 1..future_months LOOP
        next_month := DATE_TRUNC('month', CURRENT_DATE + (i || ' months')::INTERVAL);
        partition_name := 'payments_' || TO_CHAR(next_month, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF payments_partitioned
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            next_month,
            next_month + INTERVAL '1 month'
        );
    END LOOP;
    
    -- Create activity logs partitions
    FOR i IN 1..future_months LOOP
        next_month := DATE_TRUNC('month', CURRENT_DATE + (i || ' months')::INTERVAL);
        partition_name := 'activity_logs_' || TO_CHAR(next_month, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF activity_logs_partitioned
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            next_month,
            next_month + INTERVAL '1 month'
        );
    END LOOP;
    
    -- Create camera events partitions
    FOR i IN 1..7 LOOP
        next_month := CURRENT_DATE + (i || ' days')::INTERVAL;
        partition_name := 'camera_events_' || TO_CHAR(next_month, 'YYYY_MM_DD');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF camera_events_partitioned
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            next_month,
            next_month + INTERVAL '1 day'
        );
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Schedule automatic partition creation (requires pg_cron)
SELECT cron.schedule(
    'create-partitions',
    '0 0 1 * *', -- Run at midnight on the first day of each month
    'SELECT create_future_partitions();'
);

-- =====================================================
-- PARTITION MAINTENANCE FUNCTIONS
-- =====================================================

-- Function to archive old partitions
CREATE OR REPLACE FUNCTION archive_old_partitions(
    p_table_name TEXT,
    p_retention_months INTEGER
)
RETURNS TABLE (
    partition_name TEXT,
    rows_archived BIGINT,
    archive_file TEXT
) AS $$
DECLARE
    v_partition RECORD;
    v_cutoff_date DATE;
    v_archive_table TEXT;
    v_archive_file TEXT;
    v_count BIGINT;
BEGIN
    v_cutoff_date := DATE_TRUNC('month', CURRENT_DATE - (p_retention_months || ' months')::INTERVAL);
    
    FOR v_partition IN 
        SELECT 
            inhrelid::regclass::text as partition_name,
            pg_get_expr(partbound, inhrelid) as partition_bound
        FROM pg_inherits
        JOIN pg_class ON pg_class.oid = inhrelid
        WHERE inhparent = p_table_name::regclass
    LOOP
        -- Check if partition is older than retention period
        IF v_partition.partition_bound LIKE '%' || TO_CHAR(v_cutoff_date, 'YYYY-MM-DD') || '%' THEN
            v_archive_table := v_partition.partition_name || '_archive';
            v_archive_file := '/var/lib/postgresql/backups/partitions/' || 
                              v_partition.partition_name || '_' || 
                              TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDD_HH24MISS') || '.csv';
            
            -- Create archive table
            EXECUTE format('
                CREATE TABLE %I (LIKE %I INCLUDING ALL)',
                v_archive_table, v_partition.partition_name
            );
            
            -- Copy data to archive table
            EXECUTE format('
                INSERT INTO %I SELECT * FROM %I',
                v_archive_table, v_partition.partition_name
            );
            
            GET DIAGNOSTICS v_count = ROW_COUNT;
            
            -- Export to CSV
            EXECUTE format('
                COPY %I TO %L WITH CSV HEADER',
                v_archive_table, v_archive_file
            );
            
            -- Detach and drop original partition
            EXECUTE format('
                ALTER TABLE %s DETACH PARTITION %I',
                p_table_name, v_partition.partition_name
            );
            
            EXECUTE format('DROP TABLE %I', v_partition.partition_name);
            
            partition_name := v_partition.partition_name;
            rows_archived := v_count;
            archive_file := v_archive_file;
            RETURN NEXT;
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to attach existing data to partitions
CREATE OR REPLACE FUNCTION attach_existing_data_to_partitions(
    p_source_table TEXT,
    p_partitioned_table TEXT,
    p_date_column TEXT
)
RETURNS TABLE (
    period TEXT,
    rows_moved BIGINT
) AS $$
DECLARE
    v_min_date DATE;
    v_max_date DATE;
    v_current_date DATE;
    v_partition_name TEXT;
    v_count BIGINT;
BEGIN
    -- Get date range from source table
    EXECUTE format('
        SELECT MIN(%I::DATE), MAX(%I::DATE)
        FROM %I',
        p_date_column, p_date_column, p_source_table
    ) INTO v_min_date, v_max_date;
    
    v_current_date := DATE_TRUNC('month', v_min_date);
    
    WHILE v_current_date <= v_max_date LOOP
        v_partition_name := p_partitioned_table || '_' || TO_CHAR(v_current_date, 'YYYY_MM');
        
        -- Create partition if it doesn't exist
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF %s
            FOR VALUES FROM (%L) TO (%L)',
            v_partition_name, p_partitioned_table,
            v_current_date,
            v_current_date + INTERVAL '1 month'
        );
        
        -- Move data
        EXECUTE format('
            WITH moved AS (
                DELETE FROM %I
                WHERE %I >= %L AND %I < %L
                RETURNING *
            )
            INSERT INTO %I SELECT * FROM moved',
            p_source_table,
            p_date_column, v_current_date,
            p_date_column, v_current_date + INTERVAL '1 month',
            v_partition_name
        );
        
        GET DIAGNOSTICS v_count = ROW_COUNT;
        
        period := TO_CHAR(v_current_date, 'YYYY-MM');
        rows_moved := v_count;
        RETURN NEXT;
        
        v_current_date := v_current_date + INTERVAL '1 month';
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- PARTITION MAINTENANCE SCHEDULING
-- =====================================================

-- Create maintenance schedule for partitions
CREATE OR REPLACE FUNCTION run_partition_maintenance()
RETURNS void AS $$
BEGIN
    -- Archive old partitions (older than 2 years)
    PERFORM archive_old_partitions('parking_sessions_partitioned', 24);
    PERFORM archive_old_partitions('activity_logs_partitioned', 24);
    PERFORM archive_old_partitions('payments_partitioned', 24);
    
    -- Archive old sensor data (older than 3 months)
    PERFORM archive_old_partitions('sensor_data_partitioned', 3);
    
    -- Archive old camera events (older than 1 month)
    PERFORM archive_old_partitions('camera_events_partitioned', 1);
    
    -- Create future partitions
    PERFORM create_future_partitions();
END;
$$ LANGUAGE plpgsql;

-- Schedule monthly maintenance
SELECT cron.schedule(
    'partition-maintenance',
    '0 2 1 * *', -- Run at 2 AM on the first day of each month
    'SELECT run_partition_maintenance();'
);

-- =====================================================
-- PARTITION MONITORING VIEWS
-- =====================================================

-- View to monitor partition sizes
CREATE OR REPLACE VIEW v_partition_sizes AS
SELECT
    parent.relname AS parent_table,
    child.relname AS partition_name,
    pg_size_pretty(pg_total_relation_size(child.oid)) AS partition_size,
    pg_total_relation_size(child.oid) AS size_bytes,
    (SELECT COUNT(*) FROM ONLY child) AS row_count,
    pg_get_expr(child.relpartbound, child.oid) AS partition_bound
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname IN (
    'parking_sessions_partitioned',
    'sensor_data_partitioned',
    'payments_partitioned',
    'activity_logs_partitioned',
    'camera_events_partitioned'
)
ORDER BY parent.relname, child.relname;

-- View to monitor partition age
CREATE OR REPLACE VIEW v_partition_age AS
SELECT
    parent.relname AS parent_table,
    child.relname AS partition_name,
    MIN(entry_time) AS oldest_record,
    MAX(entry_time) AS newest_record,
    AGE(MAX(entry_time), MIN(entry_time)) AS data_age
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
LEFT JOIN parking_sessions_partitioned ON tableoid = child.oid
WHERE parent.relname = 'parking_sessions_partitioned'
GROUP BY parent.relname, child.relname
UNION ALL
SELECT
    parent.relname AS parent_table,
    child.relname AS partition_name,
    MIN(timestamp) AS oldest_record,
    MAX(timestamp) AS newest_record,
    AGE(MAX(timestamp), MIN(timestamp)) AS data_age
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
LEFT JOIN sensor_data_partitioned ON tableoid = child.oid
WHERE parent.relname = 'sensor_data_partitioned'
GROUP BY parent.relname, child.relname
UNION ALL
SELECT
    parent.relname AS parent_table,
    child.relname AS partition_name,
    MIN(payment_time) AS oldest_record,
    MAX(payment_time) AS newest_record,
    AGE(MAX(payment_time), MIN(payment_time)) AS data_age
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
LEFT JOIN payments_partitioned ON tableoid = child.oid
WHERE parent.relname = 'payments_partitioned'
GROUP BY parent.relname, child.relname
ORDER BY parent_table, partition_name;

-- View to check partition boundaries
CREATE OR REPLACE VIEW v_partition_boundaries AS
SELECT
    nmsp_parent.nspname AS parent_schema,
    parent.relname AS parent,
    nmsp_child.nspname AS child_schema,
    child.relname AS child,
    pg_get_expr(child.relpartbound, child.oid) AS partition_bound_expr
FROM pg_inherits
    JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
    JOIN pg_class child ON pg_inherits.inhrelid = child.oid
    JOIN pg_namespace nmsp_parent ON nmsp_parent.oid = parent.relnamespace
    JOIN pg_namespace nmsp_child ON nmsp_child.oid = child.relnamespace
WHERE parent.relname LIKE '%_partitioned';

-- =====================================================
-- DATA MIGRATION FUNCTIONS
-- =====================================================

-- Function to migrate existing data to partitioned tables
CREATE OR REPLACE FUNCTION migrate_to_partitioned_tables()
RETURNS TABLE (
    table_name TEXT,
    rows_migrated BIGINT,
    status TEXT
) AS $$
DECLARE
    v_count BIGINT;
BEGIN
    -- Migrate parking_sessions
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'parking_sessions') THEN
        SELECT COUNT(*) INTO v_count FROM parking_sessions;
        
        INSERT INTO parking_sessions_partitioned
        SELECT * FROM parking_sessions;
        
        table_name := 'parking_sessions';
        rows_migrated := v_count;
        status := 'migrated';
        RETURN NEXT;
        
        -- Optionally drop old table after verification
        -- DROP TABLE parking_sessions CASCADE;
    END IF;
    
    -- Migrate sensor_data
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'sensor_data') THEN
        SELECT COUNT(*) INTO v_count FROM sensor_data;
        
        INSERT INTO sensor_data_partitioned
        SELECT * FROM sensor_data;
        
        table_name := 'sensor_data';
        rows_migrated := v_count;
        status := 'migrated';
        RETURN NEXT;
    END IF;
    
    -- Migrate payments
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'payments') THEN
        SELECT COUNT(*) INTO v_count FROM payments;
        
        INSERT INTO payments_partitioned
        SELECT * FROM payments;
        
        table_name := 'payments';
        rows_migrated := v_count;
        status := 'migrated';
        RETURN NEXT;
    END IF;
    
    -- Migrate activity_logs
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'activity_logs') THEN
        SELECT COUNT(*) INTO v_count FROM activity_logs;
        
        INSERT INTO activity_logs_partitioned
        SELECT * FROM activity_logs;
        
        table_name := 'activity_logs';
        rows_migrated := v_count;
        status := 'migrated';
        RETURN NEXT;
    END IF;
    
    -- Migrate camera_events
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'camera_events') THEN
        SELECT COUNT(*) INTO v_count FROM camera_events;
        
        INSERT INTO camera_events_partitioned
        SELECT * FROM camera_events;
        
        table_name := 'camera_events';
        rows_migrated := v_count;
        status := 'migrated';
        RETURN NEXT;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- PARTITION QUERY FUNCTIONS
-- =====================================================

-- Function to query across partitions efficiently
CREATE OR REPLACE FUNCTION query_parking_sessions(
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ,
    p_lot_id UUID DEFAULT NULL,
    p_status VARCHAR DEFAULT NULL
)
RETURNS SETOF parking_sessions_partitioned
LANGUAGE plpgsql
AS $$
DECLARE
    v_partition RECORD;
    v_query TEXT;
    v_result RECORD;
BEGIN
    FOR v_partition IN 
        SELECT child.relname AS partition_name
        FROM pg_inherits
        JOIN pg_class child ON pg_inherits.inhrelid = child.oid
        WHERE inhparent = 'parking_sessions_partitioned'::regclass
        AND child.relname LIKE 'parking_sessions_%'
        AND child.relname NOT LIKE '%default'
    LOOP
        v_query := format('
            SELECT * FROM %I
            WHERE entry_time BETWEEN %L AND %L',
            v_partition.partition_name,
            p_start_date,
            p_end_date
        );
        
        IF p_lot_id IS NOT NULL THEN
            v_query := v_query || format(' AND parking_lot_id = %L', p_lot_id);
        END IF;
        
        IF p_status IS NOT NULL THEN
            v_query := v_query || format(' AND status = %L', p_status);
        END IF;
        
        FOR v_result IN EXECUTE v_query LOOP
            RETURN NEXT v_result;
        END LOOP;
    END LOOP;
    
    RETURN;
END;
$$;

-- =====================================================
-- PARTITION STATISTICS
-- =====================================================

-- View for partition usage statistics
CREATE OR REPLACE VIEW v_partition_stats AS
WITH partition_stats AS (
    SELECT
        parent.relname AS table_name,
        COUNT(child.relname) AS partition_count,
        SUM(pg_total_relation_size(child.oid)) AS total_bytes,
        MIN(pg_total_relation_size(child.oid)) AS min_partition_bytes,
        MAX(pg_total_relation_size(child.oid)) AS max_partition_bytes,
        AVG(pg_total_relation_size(child.oid)) AS avg_partition_bytes
    FROM pg_inherits
    JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
    JOIN pg_class child ON pg_inherits.inhrelid = child.oid
    WHERE parent.relname LIKE '%_partitioned'
    GROUP BY parent.relname
)
SELECT
    table_name,
    partition_count,
    pg_size_pretty(total_bytes) AS total_size,
    pg_size_pretty(min_partition_bytes) AS min_partition_size,
    pg_size_pretty(max_partition_bytes) AS max_partition_size,
    pg_size_pretty(avg_partition_bytes::BIGINT) AS avg_partition_size,
    total_bytes / 1024^3 AS total_gb
FROM partition_stats
ORDER BY total_bytes DESC;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE parking_sessions_partitioned IS 'Parking sessions table partitioned by month for better performance';
COMMENT ON TABLE sensor_data_partitioned IS 'Sensor data table partitioned by day for high-volume data';
COMMENT ON TABLE payments_partitioned IS 'Payments table partitioned by month for financial reporting';
COMMENT ON TABLE activity_logs_partitioned IS 'Activity logs table partitioned by month for audit retention';
COMMENT ON TABLE camera_events_partitioned IS 'Camera events table partitioned by day for image data management';
COMMENT ON FUNCTION create_future_partitions() IS 'Creates future partitions automatically';
COMMENT ON FUNCTION archive_old_partitions(TEXT, INTEGER) IS 'Archives and removes old partitions';
COMMENT ON FUNCTION run_partition_maintenance() IS 'Runs complete partition maintenance tasks';
COMMENT ON VIEW v_partition_sizes IS 'Monitors sizes of all partitions';
COMMENT ON VIEW v_partition_age IS 'Shows age of data in partitions';
COMMENT ON VIEW v_partition_stats IS 'Statistical summary of partition tables';

-- =====================================================
-- ROLLBACK INSTRUCTIONS
-- =====================================================

/*
-- To rollback this migration, run:

-- Drop scheduled jobs
SELECT cron.unschedule('create-partitions');
SELECT cron.unschedule('partition-maintenance');

-- Drop functions
DROP FUNCTION IF EXISTS create_future_partitions();
DROP FUNCTION IF EXISTS archive_old_partitions(TEXT, INTEGER);
DROP FUNCTION IF EXISTS attach_existing_data_to_partitions(TEXT, TEXT, TEXT);
DROP FUNCTION IF EXISTS run_partition_maintenance();
DROP FUNCTION IF EXISTS migrate_to_partitioned_tables();
DROP FUNCTION IF EXISTS query_parking_sessions(TIMESTAMPTZ, TIMESTAMPTZ, UUID, VARCHAR);

-- Drop views
DROP VIEW IF EXISTS v_partition_sizes;
DROP VIEW IF EXISTS v_partition_age;
DROP VIEW IF EXISTS v_partition_boundaries;
DROP VIEW IF EXISTS v_partition_stats;

-- Drop partitioned tables (this will drop all partitions)
DROP TABLE IF EXISTS camera_events_partitioned CASCADE;
DROP TABLE IF EXISTS activity_logs_partitioned CASCADE;
DROP TABLE IF EXISTS payments_partitioned CASCADE;
DROP TABLE IF EXISTS sensor_data_partitioned CASCADE;
DROP TABLE IF EXISTS parking_sessions_partitioned CASCADE;
*/

COMMIT;