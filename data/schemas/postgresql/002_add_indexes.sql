-- 002_add_indexes.sql
-- Additional indexes for performance optimization
-- Based on query patterns and reporting requirements

-- =====================================================
-- COMPOSITE INDEXES FOR COMMON QUERY PATTERNS
-- =====================================================

-- Parking sessions composite indexes for reporting
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_lot_date_status 
    ON parking_sessions(parking_lot_id, entry_time, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_vehicle_date 
    ON parking_sessions(vehicle_id, entry_time, exit_time);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_duration_status 
    ON parking_sessions(duration_minutes, status) 
    WHERE duration_minutes IS NOT NULL;

-- Reservations composite indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_reservations_lot_date_range 
    ON reservations(parking_lot_id, start_time, end_time, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_reservations_user_date 
    ON reservations(user_id, start_time, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_reservations_space_date 
    ON reservations(parking_space_id, start_time, end_time, status);

-- Payments composite indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_payments_session_status 
    ON payments(parking_session_id, payment_status, payment_time);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_payments_date_method_status 
    ON payments(payment_time, payment_method, payment_status) 
    WHERE payment_status = 'completed';

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_payments_processor_date 
    ON payments(processed_by_id, payment_time);

-- Vehicles composite indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_vehicles_org_plate_type 
    ON vehicles(organization_id, license_plate_normalized, vehicle_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_vehicles_owner_status 
    ON vehicles(owner_id, is_electric, is_handicapped, is_resident);

-- =====================================================
-- PARTIAL INDEXES FOR FREQUENT FILTERS
-- =====================================================

-- Active parking sessions (most frequent query)
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_active 
    ON parking_sessions(parking_lot_id, entry_time, parking_space_id) 
    WHERE status = 'active';

-- Active reservations
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_reservations_active 
    ON reservations(parking_lot_id, start_time, end_time, parking_space_id) 
    WHERE status IN ('confirmed', 'checked_in');

-- Available parking spaces
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_spaces_available 
    ON parking_spaces(level_id, space_type, is_handicapped, is_electric) 
    WHERE status = 'available';

-- Recent sensor readings
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sensor_data_recent 
    ON sensor_data(sensor_id, timestamp DESC) 
    WHERE timestamp > NOW() - INTERVAL '7 days';

-- Unpaid parking sessions
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_unpaid 
    ON parking_sessions(parking_lot_id, exit_time, total_amount) 
    WHERE payment_status = 'pending' AND status = 'completed';

-- Failed payment attempts
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_payments_failed 
    ON payments(payment_time, payment_method) 
    WHERE payment_status = 'failed';

-- Unprocessed notifications
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_notifications_pending 
    ON notifications(user_id, priority, created_at) 
    WHERE status = 'pending';

-- Active blacklisted vehicles
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_blacklisted_vehicles_active 
    ON blacklisted_vehicles(organization_id, license_plate_normalized, expires_at) 
    WHERE is_active = true;

-- =====================================================
-- JSONB INDEXES FOR CONFIGURATION TABLES
-- =====================================================

-- GIN indexes for JSONB columns
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_organizations_settings 
    ON organizations USING gin(settings);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_lots_settings 
    ON parking_lots USING gin(settings);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_preferences 
    ON users USING gin(preferences);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_roles_permissions 
    ON roles USING gin(permissions);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rates_vehicle_types 
    ON rates USING gin(vehicle_types);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rates_time_rules 
    ON rates USING gin(time_rules);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rates_tiers 
    ON rates USING gin(tiers);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_rate_applied 
    ON parking_sessions USING gin(rate_applied);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_cameras_settings 
    ON cameras USING gin(settings);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sensors_settings 
    ON sensors USING gin(settings);

-- =====================================================
-- EXPRESSION INDEXES FOR FUNCTION-BASED QUERIES
-- =====================================================

-- Date-based queries without time component
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_entry_date 
    ON parking_sessions(DATE(entry_time)) 
    WHERE status = 'completed';

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_exit_date 
    ON parking_sessions(DATE(exit_time)) 
    WHERE exit_time IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_reservations_start_date 
    ON reservations(DATE(start_time));

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_payments_date 
    ON payments(DATE(payment_time)) 
    WHERE payment_status = 'completed';

-- Case-insensitive searches
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_vehicles_license_plate_ci 
    ON vehicles(LOWER(license_plate));

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_email_ci 
    ON users(LOWER(email));

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_username_ci 
    ON users(LOWER(username));

-- Time-based calculations
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_duration_hours 
    ON parking_sessions((duration_minutes / 60)) 
    WHERE duration_minutes IS NOT NULL;

-- =====================================================
-- COVERING INDEXES FOR FREQUENT QUERIES
-- =====================================================

-- Covering index for parking session details
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_covering 
    ON parking_sessions(id, parking_lot_id, parking_space_id, vehicle_id, 
                        entry_time, exit_time, total_amount, payment_status) 
    INCLUDE (session_id, ticket_number, status);

-- Covering index for vehicle lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_vehicles_covering 
    ON vehicles(id, organization_id, license_plate_normalized, vehicle_type) 
    INCLUDE (make, model, color, owner_id);

-- Covering index for payment processing
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_payments_covering 
    ON payments(id, parking_session_id, payment_status, total_amount) 
    INCLUDE (payment_number, transaction_id, payment_time);

-- =====================================================
-- SPATIAL INDEXES (if PostGIS is available)
-- =====================================================

-- Note: These require PostGIS extension
-- Uncomment if you have PostGIS installed

/*
-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Add geometry column to parking_lots
ALTER TABLE parking_lots 
    ADD COLUMN IF NOT EXISTS location geometry(Point, 4326);

-- Update location from latitude/longitude
UPDATE parking_lots 
SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) 
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;

-- Create spatial index
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_lots_location 
    ON parking_lots USING gist(location);

-- Trigger to maintain location column
CREATE OR REPLACE FUNCTION update_parking_lot_location()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        NEW.location = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    ELSE
        NEW.location = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_parking_lots_location ON parking_lots;
CREATE TRIGGER trg_parking_lots_location
    BEFORE INSERT OR UPDATE OF latitude, longitude
    ON parking_lots
    FOR EACH ROW
    EXECUTE FUNCTION update_parking_lot_location();
*/

-- =====================================================
-- FULL-TEXT SEARCH INDEXES
-- =====================================================

-- Add tsvector columns for full-text search
ALTER TABLE vehicles 
    ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Create function to update search vector
CREATE OR REPLACE FUNCTION vehicles_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector = 
        setweight(to_tsvector('english', COALESCE(NEW.license_plate, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.make, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.model, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.color, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.vehicle_type, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for search vector updates
DROP TRIGGER IF EXISTS trg_vehicles_search_update ON vehicles;
CREATE TRIGGER trg_vehicles_search_update
    BEFORE INSERT OR UPDATE OF license_plate, make, model, color, vehicle_type
    ON vehicles
    FOR EACH ROW
    EXECUTE FUNCTION vehicles_search_vector_update();

-- Update existing records
UPDATE vehicles SET search_vector = NULL;
UPDATE vehicles SET license_plate = license_plate;

-- Create GIN index on search vector
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_vehicles_search 
    ON vehicles USING gin(search_vector);

-- Similar for parking lots
ALTER TABLE parking_lots 
    ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE OR REPLACE FUNCTION parking_lots_search_vector_update()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector = 
        setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.code, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.address, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.city, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_parking_lots_search_update ON parking_lots;
CREATE TRIGGER trg_parking_lots_search_update
    BEFORE INSERT OR UPDATE OF name, code, address, city, description
    ON parking_lots
    FOR EACH ROW
    EXECUTE FUNCTION parking_lots_search_vector_update();

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_lots_search 
    ON parking_lots USING gin(search_vector);

-- =====================================================
-- TIME-BASED PARTITIONING INDEXES
-- =====================================================

-- Create indexes on partitioned tables (if using partitioning)
-- Note: These are examples if you decide to partition large tables

/*
-- For partitioned parking_sessions by month
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_partition_entry 
    ON ONLY parking_sessions (entry_time);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_parking_sessions_partition_lot_entry 
    ON ONLY parking_sessions (parking_lot_id, entry_time);

-- For partitioned sensor_data by day
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sensor_data_partition_timestamp 
    ON ONLY sensor_data (timestamp);

CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_sensor_data_partition_sensor_timestamp 
    ON ONLY sensor_data (sensor_id, timestamp);
*/

-- =====================================================
-- STATISTICS FOR QUERY OPTIMIZER
-- =====================================================

-- Increase statistics target for columns with skewed data
ALTER TABLE parking_sessions ALTER COLUMN status SET STATISTICS 1000;
ALTER TABLE parking_sessions ALTER COLUMN payment_status SET STATISTICS 1000;
ALTER TABLE parking_spaces ALTER COLUMN status SET STATISTICS 1000;
ALTER TABLE parking_spaces ALTER COLUMN space_type SET STATISTICS 1000;
ALTER TABLE vehicles ALTER COLUMN vehicle_type SET STATISTICS 1000;
ALTER TABLE vehicles ALTER COLUMN license_plate_normalized SET STATISTICS 1000;

-- =====================================================
-- INDEX MAINTENANCE FUNCTIONS
-- =====================================================

-- Create function to analyze index usage
CREATE OR REPLACE FUNCTION analyze_index_usage()
RETURNS TABLE (
    table_name text,
    index_name text,
    index_size text,
    index_scans bigint,
    tuples_read bigint,
    tuples_fetched bigint
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        schemaname || '.' || tablename as table_name,
        indexrelname as index_name,
        pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
        idx_scan as index_scans,
        idx_tup_read as tuples_read,
        idx_tup_fetch as tuples_fetched
    FROM pg_stat_user_indexes
    JOIN pg_index USING (indexrelid)
    WHERE schemaname = 'public'
    ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC;
END;
$$ LANGUAGE plpgsql;

-- Create function to recommend unused indexes
CREATE OR REPLACE FUNCTION recommend_unused_indexes(threshold_scans bigint DEFAULT 100)
RETURNS TABLE (
    table_name text,
    index_name text,
    index_size text,
    index_scans bigint,
    drop_statement text
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        schemaname || '.' || tablename as table_name,
        indexrelname as index_name,
        pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
        idx_scan as index_scans,
        'DROP INDEX CONCURRENTLY IF EXISTS ' || indexrelname || ';' as drop_statement
    FROM pg_stat_user_indexes
    JOIN pg_index USING (indexrelid)
    WHERE schemaname = 'public'
        AND idx_scan < threshold_scans
        AND NOT indisprimary
        AND indexrelid NOT IN (
            SELECT conindid FROM pg_constraint WHERE contype IN ('p', 'u')
        )
    ORDER BY pg_relation_size(indexrelid) DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- INDEX MONITORING VIEWS
-- =====================================================

-- Create view for index size information
CREATE OR REPLACE VIEW v_index_sizes AS
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    pg_relation_size(indexrelid) as index_size_bytes,
    idx_scan as number_of_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Create view for duplicate indexes
CREATE OR REPLACE VIEW v_duplicate_indexes AS
WITH index_info AS (
    SELECT
        indexrelid::regclass as index_name,
        indrelid::regclass as table_name,
        array_agg(attname ORDER BY attnum) as index_columns
    FROM pg_index i
    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
    WHERE i.indisprimary = false
    GROUP BY indexrelid, indrelid
)
SELECT
    a.table_name,
    a.index_name as index1,
    b.index_name as index2,
    a.index_columns
FROM index_info a
JOIN index_info b ON a.table_name = b.table_name 
    AND a.index_columns = b.index_columns 
    AND a.index_name > b.index_name
ORDER BY a.table_name, a.index_columns;

-- =====================================================
-- REINDEX RECOMMENDATIONS
-- =====================================================

-- Create function to check index bloat
CREATE OR REPLACE FUNCTION check_index_bloat(threshold_percent integer DEFAULT 30)
RETURNS TABLE (
    index_name text,
    index_size text,
    bloat_percent numeric,
    recommendation text
) AS $$
BEGIN
    RETURN QUERY
    WITH bloat_info AS (
        SELECT
            indexrelid::regclass as index_name,
            pg_relation_size(indexrelid) as index_size,
            CASE WHEN relpages = 0 THEN 0
                ELSE 100 * (1 - (relpages::numeric / (4 * (pg_relation_size(indexrelid) / 8192))))
            END as bloat_pct
        FROM pg_stat_user_indexes
        JOIN pg_class ON pg_class.oid = indexrelid
        WHERE schemaname = 'public'
    )
    SELECT
        index_name::text,
        pg_size_pretty(index_size) as index_size,
        round(bloat_pct, 2) as bloat_percent,
        CASE 
            WHEN bloat_pct > threshold_percent 
            THEN 'REINDEX INDEX CONCURRENTLY ' || index_name || ';'
            ELSE 'No action needed'
        END as recommendation
    FROM bloat_info
    WHERE bloat_pct > threshold_percent
    ORDER BY bloat_pct DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- MAINTENANCE JOBS (COMMENTED OUT - RUN MANUALLY)
-- =====================================================

/*
-- Recreate indexes with high bloat
SELECT check_index_bloat(30);

-- Drop unused indexes (after careful review)
SELECT * FROM recommend_unused_indexes(10);

-- Analyze tables to update statistics
ANALYZE parking_sessions;
ANALYZE vehicles;
ANALYZE reservations;
ANALYZE payments;
*/

-- =====================================================
-- INDEX USAGE STATISTICS COLLECTION
-- =====================================================

-- Create table to store index usage history
CREATE TABLE IF NOT EXISTS index_usage_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    table_name TEXT,
    index_name TEXT,
    index_scans BIGINT,
    tuples_read BIGINT,
    tuples_fetched BIGINT,
    index_size_bytes BIGINT
);

-- Create function to collect index usage stats
CREATE OR REPLACE FUNCTION collect_index_usage_stats()
RETURNS void AS $$
BEGIN
    INSERT INTO index_usage_history (
        table_name,
        index_name,
        index_scans,
        tuples_read,
        tuples_fetched,
        index_size_bytes
    )
    SELECT
        schemaname || '.' || tablename,
        indexrelname,
        idx_scan,
        idx_tup_read,
        idx_tup_fetch,
        pg_relation_size(indexrelid)
    FROM pg_stat_user_indexes
    WHERE schemaname = 'public';
END;
$$ LANGUAGE plpgsql;

-- Create a scheduled job to collect stats daily (if pg_cron is available)
-- Note: This requires pg_cron extension
/*
CREATE EXTENSION IF NOT EXISTS pg_cron;

SELECT cron.schedule(
    'collect-index-stats',
    '0 2 * * *',  -- Run at 2 AM every day
    'SELECT collect_index_usage_stats();'
);
*/

COMMENT ON TABLE index_usage_history IS 'Historical index usage statistics for performance analysis';

-- =====================================================
-- FINAL ANALYZE
-- =====================================================

-- Update statistics after adding indexes
ANALYZE;

-- =====================================================
-- ROLLBACK INSTRUCTIONS (COMMENTED)
-- =====================================================

/*
-- To rollback this migration, run:

-- Drop all indexes created in this file
DO $$
DECLARE
    idx_record RECORD;
BEGIN
    FOR idx_record IN 
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND indexname LIKE 'ix_%'
        AND indexname NOT IN (
            -- Keep primary key and unique constraint indexes
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND indexname LIKE '%_pkey'
        )
    LOOP
        EXECUTE 'DROP INDEX CONCURRENTLY IF EXISTS ' || idx_record.indexname;
    END LOOP;
END;
$$;

-- Drop functions and views
DROP FUNCTION IF EXISTS analyze_index_usage();
DROP FUNCTION IF EXISTS recommend_unused_indexes(bigint);
DROP FUNCTION IF EXISTS check_index_bloat(integer);
DROP FUNCTION IF EXISTS collect_index_usage_stats();
DROP VIEW IF EXISTS v_index_sizes;
DROP VIEW IF EXISTS v_duplicate_indexes;
DROP TABLE IF EXISTS index_usage_history;

-- Drop search vector columns and triggers
DROP TRIGGER IF EXISTS trg_vehicles_search_update ON vehicles;
DROP FUNCTION IF EXISTS vehicles_search_vector_update();
ALTER TABLE vehicles DROP COLUMN IF EXISTS search_vector;

DROP TRIGGER IF EXISTS trg_parking_lots_search_update ON parking_lots;
DROP FUNCTION IF EXISTS parking_lots_search_vector_update();
ALTER TABLE parking_lots DROP COLUMN IF EXISTS search_vector;

-- Drop spatial column if exists
ALTER TABLE parking_lots DROP COLUMN IF EXISTS location;
*/

COMMIT;