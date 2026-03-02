# parking-management/data/migrations/versions/9i0j1k2l3m4n_add_partitions.py

"""Add table partitioning for large tables

Revision ID: 9i0j1k2l3m4n
Revises: 8h9i0j1k2l3m
Create Date: 2024-04-15 12:00:00.123456

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '9i0j1k2l3m4n'
down_revision: Union[str, None] = '8h9i0j1k2l3m'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define partition configuration
PARTITION_CONFIG = {
    'audit_events': {
        'type': 'range',
        'column': 'created_at',
        'interval': 'month',
        'retention_months': 24,
        'archive_after_months': 12
    },
    'notifications': {
        'type': 'range',
        'column': 'created_at',
        'interval': 'month',
        'retention_months': 12,
        'archive_after_months': 6
    },
    'notification_logs': {
        'type': 'range',
        'column': 'timestamp',
        'interval': 'month',
        'retention_months': 6,
        'archive_after_months': 3
    },
    'parking_sessions': {
        'type': 'range',
        'column': 'start_time',
        'interval': 'month',
        'retention_months': 24,
        'archive_after_months': 12
    },
    'reservations': {
        'type': 'range',
        'column': 'start_time',
        'interval': 'month',
        'retention_months': 24,
        'archive_after_months': 12
    },
    'payments': {
        'type': 'range',
        'column': 'created_at',
        'interval': 'month',
        'retention_months': 36,
        'archive_after_months': 24
    },
    'vehicle_access_history': {
        'type': 'range',
        'column': 'timestamp',
        'interval': 'month',
        'retention_months': 12,
        'archive_after_months': 6
    },
    'vehicle_location_history': {
        'type': 'range',
        'column': 'timestamp',
        'interval': 'day',
        'retention_months': 3,
        'archive_after_months': 1
    },
    'audit_changes': {
        'type': 'range',
        'column': 'created_at',
        'interval': 'month',
        'retention_months': 24,
        'archive_after_months': 12
    }
}


def create_range_partitions(table_name: str, partition_column: str, interval: str, months_ahead: int = 12) -> None:
    """
    Create range partitions for a table
    
    Args:
        table_name: Name of the table to partition
        partition_column: Column to partition on
        interval: Partition interval (day, month, year)
        months_ahead: Number of months to create partitions ahead
    """
    logger.info(f"Creating range partitions for {table_name} on {partition_column}")
    
    current_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Create partitions for the last 6 months and next 12 months
    for i in range(-6, months_ahead + 1):
        if interval == 'month':
            partition_date = current_date + timedelta(days=30 * i)
            next_date = (partition_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            partition_name = f"{table_name}_{partition_date.strftime('%Y_%m')}"
            from_value = partition_date.strftime('%Y-%m-%d')
            to_value = next_date.strftime('%Y-%m-%d')
        elif interval == 'day':
            partition_date = current_date + timedelta(days=i)
            next_date = partition_date + timedelta(days=1)
            partition_name = f"{table_name}_{partition_date.strftime('%Y_%m_%d')}"
            from_value = partition_date.strftime('%Y-%m-%d')
            to_value = next_date.strftime('%Y-%m-%d')
        elif interval == 'year':
            partition_date = current_date.replace(year=current_date.year + i, month=1, day=1)
            next_date = partition_date.replace(year=partition_date.year + 1)
            partition_name = f"{table_name}_{partition_date.strftime('%Y')}"
            from_value = partition_date.strftime('%Y-%m-%d')
            to_value = next_date.strftime('%Y-%m-%d')
        else:
            raise ValueError(f"Unsupported interval: {interval}")
        
        # Create partition if it doesn't exist
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS {partition_name} 
        PARTITION OF {table_name}
        FOR VALUES FROM ('{from_value}') TO ('{to_value}');
        """)


def create_hash_partitions(table_name: str, partition_column: str, num_partitions: int = 8) -> None:
    """
    Create hash partitions for a table
    
    Args:
        table_name: Name of the table to partition
        partition_column: Column to partition on
        num_partitions: Number of hash partitions
    """
    logger.info(f"Creating hash partitions for {table_name} on {partition_column}")
    
    for i in range(num_partitions):
        partition_name = f"{table_name}_p{i}"
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS {partition_name} 
        PARTITION OF {table_name}
        FOR VALUES WITH (MODULUS {num_partitions}, REMAINDER {i});
        """)


def create_list_partitions(table_name: str, partition_column: str, values_list: list) -> None:
    """
    Create list partitions for a table
    
    Args:
        table_name: Name of the table to partition
        partition_column: Column to partition on
        values_list: List of values for each partition
    """
    logger.info(f"Creating list partitions for {table_name} on {partition_column}")
    
    for values in values_list:
        partition_name = f"{table_name}_{'_'.join(str(v) for v in values)}"
        values_str = ', '.join(f"'{v}'" if isinstance(v, str) else str(v) for v in values)
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS {partition_name} 
        PARTITION OF {table_name}
        FOR VALUES IN ({values_str});
        """)


def create_partition_functions() -> None:
    """Create partition management functions"""
    logger.info("Creating partition management functions")
    
    # Function to create future partitions automatically
    op.execute("""
    CREATE OR REPLACE FUNCTION create_future_partitions()
    RETURNS void AS $$
    DECLARE
        partition_record RECORD;
        next_month DATE;
        partition_name TEXT;
        from_date TEXT;
        to_date TEXT;
    BEGIN
        next_month := date_trunc('month', CURRENT_DATE + INTERVAL '2 months')::DATE;
        
        FOR partition_record IN 
            SELECT 
                inhparent::regclass::text as parent_table,
                pg_get_expr(partbound, inhparent) as partition_bound
            FROM pg_inherits
            WHERE inhparent IN (
                'audit_events'::regclass,
                'notifications'::regclass,
                'parking_sessions'::regclass,
                'reservations'::regclass,
                'payments'::regclass
            )
            GROUP BY inhparent, partition_bound
        LOOP
            -- Check if partition for next month exists
            partition_name := partition_record.parent_table || '_' || to_char(next_month, 'YYYY_MM');
            
            EXECUTE format('
                CREATE TABLE IF NOT EXISTS %I 
                PARTITION OF %I
                FOR VALUES FROM (%L) TO (%L)',
                partition_name,
                partition_record.parent_table,
                next_month,
                next_month + INTERVAL '1 month'
            );
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Function to detach old partitions
    op.execute("""
    CREATE OR REPLACE FUNCTION detach_old_partitions(
        p_table_name TEXT,
        p_retention_months INTEGER
    )
    RETURNS TABLE(
        partition_name TEXT,
        detached_at TIMESTAMP
    ) AS $$
    DECLARE
        partition_record RECORD;
        cutoff_date DATE;
    BEGIN
        cutoff_date := date_trunc('month', CURRENT_DATE - (p_retention_months || ' months')::INTERVAL)::DATE;
        
        FOR partition_record IN 
            SELECT 
                inhrelid::regclass::text as partition_name,
                pg_get_expr(partbound, inhrelid) as partition_bound
            FROM pg_inherits
            WHERE inhparent = p_table_name::regclass
        LOOP
            -- Parse partition bound to get the from date
            -- This is simplified; actual implementation would need to parse the bound expression
            IF partition_record.partition_name LIKE '%' || to_char(cutoff_date, 'YYYY_MM') || '%' THEN
                RETURN QUERY
                EXECUTE format('
                    ALTER TABLE %I DETACH PARTITION %I;
                    SELECT %L, CURRENT_TIMESTAMP;
                ', p_table_name, partition_record.partition_name, partition_record.partition_name);
            END IF;
        END LOOP;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Function to attach old partitions from archive
    op.execute("""
    CREATE OR REPLACE FUNCTION attach_archived_partition(
        p_table_name TEXT,
        p_archive_table TEXT,
        p_from_date DATE,
        p_to_date DATE
    )
    RETURNS void AS $$
    BEGIN
        EXECUTE format('
            ALTER TABLE %I ATTACH PARTITION %I
            FOR VALUES FROM (%L) TO (%L);
        ', p_table_name, p_archive_table, p_from_date, p_to_date);
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Function to get partition info
    op.execute("""
    CREATE OR REPLACE FUNCTION get_partition_info(p_table_name TEXT)
    RETURNS TABLE(
        partition_name TEXT,
        partition_type TEXT,
        partition_bound TEXT,
        table_size TEXT,
        row_count BIGINT
    ) AS $$
    BEGIN
        RETURN QUERY
        SELECT 
            inhrelid::regclass::text as partition_name,
            CASE 
                WHEN pg_get_expr(partbound, inhrelid) LIKE '%RANGE%' THEN 'RANGE'
                WHEN pg_get_expr(partbound, inhrelid) LIKE '%LIST%' THEN 'LIST'
                WHEN pg_get_expr(partbound, inhrelid) LIKE '%HASH%' THEN 'HASH'
            END as partition_type,
            pg_get_expr(partbound, inhrelid) as partition_bound,
            pg_size_pretty(pg_total_relation_size(inhrelid)) as table_size,
            (SELECT reltuples::BIGINT FROM pg_class WHERE oid = inhrelid) as row_count
        FROM pg_inherits
        WHERE inhparent = p_table_name::regclass
        ORDER BY partition_name;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Function to archive old partition
    op.execute("""
    CREATE OR REPLACE FUNCTION archive_partition(
        p_partition_name TEXT,
        p_archive_schema TEXT DEFAULT 'archive'
    )
    RETURNS void AS $$
    DECLARE
        archive_table TEXT;
    BEGIN
        -- Create archive schema if it doesn't exist
        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', p_archive_schema);
        
        archive_table := p_archive_schema || '.' || p_partition_name;
        
        -- Move partition to archive schema
        EXECUTE format('
            ALTER TABLE %I SET SCHEMA %I;
        ', p_partition_name, p_archive_schema);
        
        -- Compress the archived table
        EXECUTE format('
            ALTER TABLE %I SET (autovacuum_enabled = false, toast.autovacuum_enabled = false);
        ', archive_table);
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Function to restore archived partition
    op.execute("""
    CREATE OR REPLACE FUNCTION restore_archived_partition(
        p_archive_table TEXT,
        p_target_schema TEXT DEFAULT 'public'
    )
    RETURNS void AS $$
    BEGIN
        EXECUTE format('
            ALTER TABLE %I SET SCHEMA %I;
            ALTER TABLE %I SET (autovacuum_enabled = true, toast.autovacuum_enabled = true);
        ', p_archive_table, p_target_schema, p_archive_table);
    END;
    $$ LANGUAGE plpgsql;
    """)


def create_partition_management_jobs() -> None:
    """Create scheduled jobs for partition management"""
    logger.info("Creating partition management jobs")
    
    # Create a scheduled job to create future partitions (if pg_cron is available)
    try:
        op.execute("""
        SELECT cron.schedule(
            'create-future-partitions',
            '0 0 1 * *',  -- First day of every month at midnight
            $$SELECT create_future_partitions()$$
        );
        """)
        logger.info("Created scheduled job for partition creation")
    except Exception as e:
        logger.warning(f"Could not create scheduled job (pg_cron may not be installed): {e}")
    
    # Create a job to check partition sizes and report
    try:
        op.execute("""
        SELECT cron.schedule(
            'check-partition-sizes',
            '0 */6 * * *',  -- Every 6 hours
            $$INSERT INTO partition_metrics (table_name, partition_name, row_count, size_bytes, checked_at)
              SELECT 
                  inhparent::regclass::text,
                  inhrelid::regclass::text,
                  (SELECT reltuples FROM pg_class WHERE oid = inhrelid),
                  pg_total_relation_size(inhrelid),
                  CURRENT_TIMESTAMP
              FROM pg_inherits;$$
        );
        """)
        logger.info("Created scheduled job for partition monitoring")
    except Exception as e:
        logger.warning(f"Could not create monitoring job: {e}")


def create_partition_metrics_table() -> None:
    """Create table to store partition metrics"""
    logger.info("Creating partition metrics table")
    
    op.execute("""
    CREATE TABLE IF NOT EXISTS partition_metrics (
        id BIGSERIAL PRIMARY KEY,
        table_name TEXT NOT NULL,
        partition_name TEXT NOT NULL,
        row_count BIGINT,
        size_bytes BIGINT,
        checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX idx_partition_metrics_table ON partition_metrics(table_name, checked_at);
    """)


def upgrade() -> None:
    """
    Upgrade migration - adds partitioning to large tables
    """
    logger.info(f"Starting migration {revision}: Add table partitioning")
    
    # Create partition management functions
    create_partition_functions()
    
    # Create metrics table
    create_partition_metrics_table()
    
    # ==================== AUDIT EVENTS PARTITIONING ====================
    logger.info("Partitioning audit_events table")
    
    # Convert to partitioned table (requires table rebuild for existing data)
    # For existing tables, we need to create a new partitioned table and migrate data
    
    # Create new partitioned table
    op.execute("""
    CREATE TABLE audit_events_new (
        LIKE audit_events INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
    ) PARTITION BY RANGE (created_at);
    """)
    
    # Create partitions for audit_events
    create_range_partitions('audit_events_new', 'created_at', 'month', months_ahead=12)
    
    # Migrate existing data (this could be batched for large tables)
    op.execute("""
    INSERT INTO audit_events_new SELECT * FROM audit_events;
    """)
    
    # Drop old table and rename new one
    op.execute("DROP TABLE audit_events CASCADE;")
    op.execute("ALTER TABLE audit_events_new RENAME TO audit_events;")
    
    # Recreate indexes on partitioned table
    op.create_index('idx_audit_events_created_at', 'audit_events', ['created_at'])
    op.create_index('idx_audit_events_composite', 'audit_events', 
                   ['created_at', 'category', 'action'])
    
    # ==================== NOTIFICATIONS PARTITIONING ====================
    logger.info("Partitioning notifications table")
    
    op.execute("""
    CREATE TABLE notifications_new (
        LIKE notifications INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
    ) PARTITION BY RANGE (created_at);
    """)
    
    create_range_partitions('notifications_new', 'created_at', 'month', months_ahead=12)
    
    # Batch migrate data to avoid timeout
    batch_size = 10000
    op.execute(f"""
    DO $$
    DECLARE
        batch_start INTEGER := 0;
        rows_migrated INTEGER;
    BEGIN
        LOOP
            INSERT INTO notifications_new 
            SELECT * FROM notifications 
            ORDER BY created_at 
            LIMIT {batch_size} OFFSET batch_start;
            
            GET DIAGNOSTICS rows_migrated = ROW_COUNT;
            EXIT WHEN rows_migrated = 0;
            
            batch_start := batch_start + {batch_size};
            COMMIT;
        END LOOP;
    END $$;
    """)
    
    op.execute("DROP TABLE notifications CASCADE;")
    op.execute("ALTER TABLE notifications_new RENAME TO notifications;")
    
    op.create_index('idx_notifications_created_at', 'notifications', ['created_at'])
    op.create_index('idx_notifications_status_created', 'notifications', ['status', 'created_at'])
    
    # ==================== NOTIFICATION LOGS PARTITIONING ====================
    logger.info("Partitioning notification_logs table")
    
    op.execute("""
    CREATE TABLE notification_logs_new (
        LIKE notification_logs INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
    ) PARTITION BY RANGE (timestamp);
    """)
    
    create_range_partitions('notification_logs_new', 'timestamp', 'month', months_ahead=6)
    
    op.execute("""
    INSERT INTO notification_logs_new SELECT * FROM notification_logs;
    """)
    
    op.execute("DROP TABLE notification_logs CASCADE;")
    op.execute("ALTER TABLE notification_logs_new RENAME TO notification_logs;")
    
    op.create_index('idx_notification_logs_timestamp', 'notification_logs', ['timestamp'])
    op.create_index('idx_notification_logs_notification', 'notification_logs', ['notification_id'])
    
    # ==================== PARKING SESSIONS PARTITIONING ====================
    logger.info("Partitioning parking_sessions table")
    
    op.execute("""
    CREATE TABLE parking_sessions_new (
        LIKE parking_sessions INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
    ) PARTITION BY RANGE (start_time);
    """)
    
    create_range_partitions('parking_sessions_new', 'start_time', 'month', months_ahead=12)
    
    # Migrate data in batches by month
    current_date = datetime.now().replace(day=1)
    for i in range(-24, 12):  # Last 24 months, next 12 months
        month_date = current_date + timedelta(days=30 * i)
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        op.execute(f"""
        INSERT INTO parking_sessions_new 
        SELECT * FROM parking_sessions 
        WHERE start_time >= '{month_date.strftime('%Y-%m-%d')}'
        AND start_time < '{next_month.strftime('%Y-%m-%d')}';
        """)
    
    op.execute("DROP TABLE parking_sessions CASCADE;")
    op.execute("ALTER TABLE parking_sessions_new RENAME TO parking_sessions;")
    
    op.create_index('idx_parking_sessions_start_time', 'parking_sessions', ['start_time'])
    op.create_index('idx_parking_sessions_spot_start', 'parking_sessions', ['spot_id', 'start_time'])
    
    # ==================== RESERVATIONS PARTITIONING ====================
    logger.info("Partitioning reservations table")
    
    op.execute("""
    CREATE TABLE reservations_new (
        LIKE reservations INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
    ) PARTITION BY RANGE (start_time);
    """)
    
    create_range_partitions('reservations_new', 'start_time', 'month', months_ahead=12)
    
    # Migrate data in batches
    for i in range(-24, 12):
        month_date = current_date + timedelta(days=30 * i)
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        op.execute(f"""
        INSERT INTO reservations_new 
        SELECT * FROM reservations 
        WHERE start_time >= '{month_date.strftime('%Y-%m-%d')}'
        AND start_time < '{next_month.strftime('%Y-%m-%d')}';
        """)
    
    op.execute("DROP TABLE reservations CASCADE;")
    op.execute("ALTER TABLE reservations_new RENAME TO reservations;")
    
    op.create_index('idx_reservations_start_time', 'reservations', ['start_time'])
    op.create_index('idx_reservations_spot_start', 'reservations', ['spot_id', 'start_time'])
    
    # ==================== PAYMENTS PARTITIONING ====================
    logger.info("Partitioning payments table")
    
    op.execute("""
    CREATE TABLE payments_new (
        LIKE payments INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
    ) PARTITION BY RANGE (created_at);
    """)
    
    create_range_partitions('payments_new', 'created_at', 'month', months_ahead=12)
    
    for i in range(-36, 12):  # Last 36 months, next 12 months
        month_date = current_date + timedelta(days=30 * i)
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        op.execute(f"""
        INSERT INTO payments_new 
        SELECT * FROM payments 
        WHERE created_at >= '{month_date.strftime('%Y-%m-%d')}'
        AND created_at < '{next_month.strftime('%Y-%m-%d')}';
        """)
    
    op.execute("DROP TABLE payments CASCADE;")
    op.execute("ALTER TABLE payments_new RENAME TO payments;")
    
    op.create_index('idx_payments_created_at', 'payments', ['created_at'])
    op.create_index('idx_payments_paid_at', 'payments', ['paid_at'])
    
    # ==================== VEHICLE ACCESS HISTORY PARTITIONING ====================
    logger.info("Partitioning vehicle_access_history table")
    
    op.execute("""
    CREATE TABLE vehicle_access_history_new (
        LIKE vehicle_access_history INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
    ) PARTITION BY RANGE (timestamp);
    """)
    
    create_range_partitions('vehicle_access_history_new', 'timestamp', 'month', months_ahead=6)
    
    for i in range(-12, 6):
        month_date = current_date + timedelta(days=30 * i)
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        op.execute(f"""
        INSERT INTO vehicle_access_history_new 
        SELECT * FROM vehicle_access_history 
        WHERE timestamp >= '{month_date.strftime('%Y-%m-%d')}'
        AND timestamp < '{next_month.strftime('%Y-%m-%d')}';
        """)
    
    op.execute("DROP TABLE vehicle_access_history CASCADE;")
    op.execute("ALTER TABLE vehicle_access_history_new RENAME TO vehicle_access_history;")
    
    op.create_index('idx_vehicle_access_timestamp', 'vehicle_access_history', ['timestamp'])
    op.create_index('idx_vehicle_access_vehicle_time', 'vehicle_access_history', ['vehicle_id', 'timestamp'])
    
    # ==================== VEHICLE LOCATION HISTORY PARTITIONING ====================
    logger.info("Partitioning vehicle_location_history table")
    
    op.execute("""
    CREATE TABLE vehicle_location_history_new (
        LIKE vehicle_location_history INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
    ) PARTITION BY RANGE (timestamp);
    """)
    
    create_range_partitions('vehicle_location_history_new', 'timestamp', 'day', months_ahead=1)
    
    for i in range(-90, 30):  # Last 90 days, next 30 days
        day_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=i)
        next_day = day_date + timedelta(days=1)
        
        op.execute(f"""
        INSERT INTO vehicle_location_history_new 
        SELECT * FROM vehicle_location_history 
        WHERE timestamp >= '{day_date.strftime('%Y-%m-%d')}'
        AND timestamp < '{next_day.strftime('%Y-%m-%d')}';
        """)
    
    op.execute("DROP TABLE vehicle_location_history CASCADE;")
    op.execute("ALTER TABLE vehicle_location_history_new RENAME TO vehicle_location_history;")
    
    op.create_index('idx_vehicle_location_timestamp', 'vehicle_location_history', ['timestamp'])
    op.create_index('idx_vehicle_location_vehicle_time', 'vehicle_location_history', ['vehicle_id', 'timestamp'])
    
    # ==================== CREATE ADDITIONAL PARTITIONS FOR OTHER TABLES ====================
    
    # Create hash partitions for users table if needed (for sharding)
    if False:  # Disabled by default, enable if you need sharding
        logger.info("Creating hash partitions for users table")
        op.execute("""
        CREATE TABLE users_new (
            LIKE users INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
        ) PARTITION BY HASH (id);
        """)
        create_hash_partitions('users_new', 'id', 8)
        op.execute("INSERT INTO users_new SELECT * FROM users;")
        op.execute("DROP TABLE users CASCADE;")
        op.execute("ALTER TABLE users_new RENAME TO users;")
    
    # Create list partitions for vehicle_types
    logger.info("Creating list partitions for vehicle_types table")
    op.execute("""
    CREATE TABLE vehicle_types_new (
        LIKE vehicle_types INCLUDING DEFAULTS INCLUDING CONSTRAINTS INCLUDING INDEXES
    ) PARTITION BY LIST (category);
    """)
    
    create_list_partitions('vehicle_types_new', 'category', 
                          [['passenger'], ['commercial'], ['motorcycle'], ['ev']])
    
    op.execute("INSERT INTO vehicle_types_new SELECT * FROM vehicle_types;")
    op.execute("DROP TABLE vehicle_types CASCADE;")
    op.execute("ALTER TABLE vehicle_types_new RENAME TO vehicle_types;")
    
    # Create default partition for vehicle_types
    op.execute("""
    CREATE TABLE vehicle_types_default PARTITION OF vehicle_types DEFAULT;
    """)
    
    # ==================== CREATE ARCHIVE SCHEMA ====================
    logger.info("Creating archive schema")
    op.execute("CREATE SCHEMA IF NOT EXISTS archive;")
    
    # ==================== SET UP PARTITION MANAGEMENT ====================
    create_partition_management_jobs()
    
    # ==================== CREATE PARTITION VIEWS ====================
    logger.info("Creating partition helper views")
    
    # View to show partition sizes
    op.execute("""
    CREATE OR REPLACE VIEW v_partition_sizes AS
    SELECT 
        inhparent::regclass::text as parent_table,
        inhrelid::regclass::text as partition_name,
        pg_size_pretty(pg_total_relation_size(inhrelid)) as size,
        pg_total_relation_size(inhrelid) as size_bytes,
        (SELECT reltuples::bigint FROM pg_class WHERE oid = inhrelid) as row_estimate,
        pg_get_expr(partbound, inhrelid) as partition_bound
    FROM pg_inherits
    ORDER BY parent_table, partition_name;
    """)
    
    # View to show partition usage over time
    op.execute("""
    CREATE OR REPLACE VIEW v_partition_usage AS
    SELECT 
        'audit_events' as table_name,
        date_trunc('month', created_at) as month,
        COUNT(*) as record_count
    FROM audit_events
    GROUP BY date_trunc('month', created_at)
    UNION ALL
    SELECT 
        'notifications',
        date_trunc('month', created_at),
        COUNT(*)
    FROM notifications
    GROUP BY date_trunc('month', created_at)
    UNION ALL
    SELECT 
        'parking_sessions',
        date_trunc('month', start_time),
        COUNT(*)
    FROM parking_sessions
    GROUP BY date_trunc('month', start_time)
    ORDER BY 1, 2 DESC;
    """)
    
    # Create materialized view for partition statistics
    op.execute("""
    CREATE MATERIALIZED VIEW mv_partition_stats AS
    SELECT 
        parent_table,
        COUNT(*) as partition_count,
        SUM(size_bytes) as total_size_bytes,
        pg_size_pretty(SUM(size_bytes)) as total_size,
        AVG(size_bytes) as avg_partition_size_bytes,
        MIN(size_bytes) as min_partition_size_bytes,
        MAX(size_bytes) as max_partition_size_bytes
    FROM v_partition_sizes
    GROUP BY parent_table;
    """)
    
    op.create_index('idx_mv_partition_stats_table', 'mv_partition_stats', ['parent_table'])
    
    # Analyze tables to update statistics
    logger.info("Analyzing partitioned tables")
    op.execute("ANALYZE audit_events;")
    op.execute("ANALYZE notifications;")
    op.execute("ANALYZE notification_logs;")
    op.execute("ANALYZE parking_sessions;")
    op.execute("ANALYZE reservations;")
    op.execute("ANALYZE payments;")
    op.execute("ANALYZE vehicle_access_history;")
    op.execute("ANALYZE vehicle_location_history;")
    op.execute("ANALYZE vehicle_types;")
    
    logger.info(f"Migration {revision} completed successfully")


def downgrade() -> None:
    """
    Downgrade migration - removes partitioning and reverts to regular tables
    """
    logger.info(f"Starting downgrade of migration {revision}")
    
    # For downgrade, we need to convert partitioned tables back to regular tables
    
    # Function to convert partitioned table to regular table
    def convert_to_regular(table_name: str) -> None:
        """Convert a partitioned table back to a regular table"""
        logger.info(f"Converting {table_name} to regular table")
        
        # Create a new regular table
        op.execute(f"""
        CREATE TABLE {table_name}_new (LIKE {table_name} INCLUDING ALL);
        """)
        
        # Insert data from all partitions
        op.execute(f"""
        INSERT INTO {table_name}_new SELECT * FROM ONLY {table_name};
        """)
        
        # Get all partitions and insert their data
        partitions = op.get_bind().execute(f"""
        SELECT inhrelid::regclass::text 
        FROM pg_inherits 
        WHERE inhparent = '{table_name}'::regclass;
        """).fetchall()
        
        for partition in partitions:
            op.execute(f"""
            INSERT INTO {table_name}_new SELECT * FROM {partition[0]};
            """)
        
        # Drop the partitioned table and rename the new one
        op.execute(f"DROP TABLE {table_name} CASCADE;")
        op.execute(f"ALTER TABLE {table_name}_new RENAME TO {table_name};")
    
    # Convert each partitioned table back
    convert_to_regular('audit_events')
    convert_to_regular('notifications')
    convert_to_regular('notification_logs')
    convert_to_regular('parking_sessions')
    convert_to_regular('reservations')
    convert_to_regular('payments')
    convert_to_regular('vehicle_access_history')
    convert_to_regular('vehicle_location_history')
    convert_to_regular('vehicle_types')
    
    # Drop partition management functions
    logger.info("Dropping partition management functions")
    functions_to_drop = [
        'create_future_partitions()',
        'detach_old_partitions(text, integer)',
        'attach_archived_partition(text, text, date, date)',
        'get_partition_info(text)',
        'archive_partition(text, text)',
        'restore_archived_partition(text, text)'
    ]
    
    for func in functions_to_drop:
        op.execute(f"DROP FUNCTION IF EXISTS {func} CASCADE;")
    
    # Drop views and materialized views
    logger.info("Dropping partition views")
    op.execute("DROP VIEW IF EXISTS v_partition_sizes CASCADE;")
    op.execute("DROP VIEW IF EXISTS v_partition_usage CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_partition_stats CASCADE;")
    
    # Drop partition metrics table
    op.execute("DROP TABLE IF EXISTS partition_metrics CASCADE;")
    
    # Drop archive schema (if empty)
    op.execute("DROP SCHEMA IF EXISTS archive CASCADE;")
    
    logger.info(f"Downgrade of migration {revision} completed successfully")


def validate_partitions() -> dict:
    """
    Validate that partitions were created correctly
    """
    logger.info("Validating partitions")
    
    connection = op.get_bind()
    results = {}
    
    # Check partition counts
    for table_name in PARTITION_CONFIG.keys():
        try:
            count = connection.execute(f"""
            SELECT COUNT(*) 
            FROM pg_inherits 
            WHERE inhparent = '{table_name}'::regclass;
            """).scalar()
            
            results[f'{table_name}_partitions'] = count
        except Exception as e:
            logger.warning(f"Could not check partitions for {table_name}: {e}")
    
    # Check for data distribution
    for table_name in ['audit_events', 'notifications', 'parking_sessions']:
        try:
            # Get min and max dates
            result = connection.execute(f"""
            SELECT 
                MIN(created_at) as min_date,
                MAX(created_at) as max_date,
                COUNT(*) as total_rows
            FROM {table_name};
            """).first()
            
            if result:
                results[f'{table_name}_date_range'] = {
                    'min': result.min_date,
                    'max': result.max_date,
                    'total': result.total_rows
                }
        except Exception as e:
            logger.warning(f"Could not get date range for {table_name}: {e}")
    
    # Check for default partitions (should be empty ideally)
    for table_name in PARTITION_CONFIG.keys():
        try:
            count = connection.execute(f"""
            SELECT COUNT(*) 
            FROM ONLY {table_name};
            """).scalar()
            
            if count > 0:
                results[f'{table_name}_default_data'] = count
                logger.warning(f"Table {table_name} has {count} rows in default partition")
        except:
            pass
    
    logger.info(f"Validation results: {results}")
    return results


def post_upgrade_hook():
    """Hook to run after successful upgrade"""
    logger.info("Running post-upgrade hooks for partitions migration")
    
    # Validate partitions
    validation_results = validate_partitions()
    
    # Create initial future partitions
    try:
        op.execute("SELECT create_future_partitions();")
        logger.info("Created future partitions")
    except Exception as e:
        logger.warning(f"Could not create future partitions: {e}")
    
    # Refresh materialized view
    op.execute("REFRESH MATERIALIZED VIEW mv_partition_stats;")
    
    # Log partition statistics
    connection = op.get_bind()
    stats = connection.execute("""
    SELECT * FROM mv_partition_stats ORDER BY total_size_bytes DESC;
    """).fetchall()
    
    for stat in stats:
        logger.info(f"  - {stat.parent_table}: {stat.partition_count} partitions, {stat.total_size}")
    
    # Check for any issues
    if validation_results:
        issues = [k for k, v in validation_results.items() if 'default_data' in k and v > 0]
        if issues:
            logger.warning(f"Found data in default partitions: {issues}")
    
    logger.info("Partitions migration completed successfully")


# Register the post-upgrade hook
if hasattr(op, 'register_post_upgrade_hook'):
    op.register_post_upgrade_hook(post_upgrade_hook)


def add_partition_comments():
    """Add comments to partitions for documentation"""
    # Example comments for partitions
    op.execute("COMMENT ON TABLE audit_events IS 'Main audit table partitioned by month for performance and data retention';")
    op.execute("COMMENT ON TABLE notifications IS 'Notifications table partitioned by month for efficient querying and cleanup';")
    op.execute("COMMENT ON TABLE parking_sessions IS 'Parking sessions partitioned by month for faster time-based queries';")