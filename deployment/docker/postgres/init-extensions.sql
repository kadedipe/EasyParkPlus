-- PostgreSQL Extensions for Parking Management System
-- This script installs required extensions after database creation

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable statistical tracking of SQL statements
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Enable PostGIS for geospatial queries (optional)
-- CREATE EXTENSION IF NOT EXISTS "postgis";

-- Enable tablefunc for crosstab queries
CREATE EXTENSION IF NOT EXISTS "tablefunc";

-- Enable unaccent for text search
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Create monitoring user
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'monitoring_user') THEN
        CREATE USER monitoring_user WITH PASSWORD 'monitoring_password_here';
    END IF;
END
$$;

-- Grant monitoring permissions
GRANT pg_monitor TO monitoring_user;
GRANT SELECT ON pg_stat_database TO monitoring_user;
GRANT SELECT ON pg_stat_user_tables TO monitoring_user;
GRANT SELECT ON pg_stat_statements TO monitoring_user;

-- Create backup user
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'backup_user') THEN
        CREATE USER backup_user WITH PASSWORD 'backup_password_here';
    END IF;
END
$$;

-- Grant backup permissions
GRANT CONNECT ON DATABASE parking_db TO backup_user;
GRANT USAGE ON SCHEMA public TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO backup_user;

-- Enable query monitoring
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
SELECT pg_reload_conf();

-- Create function to monitor database health
CREATE OR REPLACE FUNCTION get_database_health()
RETURNS TABLE (
    metric_name TEXT,
    metric_value TEXT,
    metric_unit TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'active_connections'::TEXT,
        COUNT(*)::TEXT,
        'connections'::TEXT
    FROM pg_stat_activity 
    WHERE state = 'active'
    
    UNION ALL
    
    SELECT 
        'database_size',
        pg_size_pretty(pg_database_size(current_database())),
        'bytes'
    
    UNION ALL
    
    SELECT 
        'cache_hit_ratio',
        ROUND(blks_hit::numeric / GREATEST(blks_hit + blks_read, 1) * 100, 2)::TEXT,
        'percent'
    FROM pg_stat_database 
    WHERE datname = current_database()
    
    UNION ALL
    
    SELECT 
        'deadlocks',
        deadlocks::TEXT,
        'count'
    FROM pg_stat_database 
    WHERE datname = current_database()
    
    UNION ALL
    
    SELECT 
        'xact_commit_ratio',
        ROUND(xact_commit::numeric / GREATEST(xact_commit + xact_rollback, 1) * 100, 2)::TEXT,
        'percent'
    FROM pg_stat_database 
    WHERE datname = current_database();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to monitoring user
GRANT EXECUTE ON FUNCTION get_database_health TO monitoring_user;

-- Create view for table statistics
CREATE OR REPLACE VIEW table_statistics AS
SELECT 
    schemaname,
    relname,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_tup_hot_upd,
    n_live_tup,
    n_dead_tup,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    vacuum_count,
    autovacuum_count,
    analyze_count,
    autoanalyze_count
FROM pg_stat_user_tables;

-- Grant select on view to monitoring user
GRANT SELECT ON table_statistics TO monitoring_user;