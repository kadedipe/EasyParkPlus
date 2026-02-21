-- 007_add_audit_triggers.sql
-- Comprehensive audit triggers for parking management system
-- Tracks all data changes with detailed context and provides audit trail functionality

-- =====================================================
-- AUDIT CONFIGURATION TABLES
-- =====================================================

-- Table to store audit configuration per table/column
CREATE TABLE audit_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100),
    audit_level VARCHAR(20) NOT NULL DEFAULT 'full', -- 'full', 'changes_only', 'minimal'
    exclude_columns TEXT[] DEFAULT ARRAY[]::TEXT[],
    include_old_values BOOLEAN DEFAULT true,
    include_new_values BOOLEAN DEFAULT true,
    sensitive_columns TEXT[] DEFAULT ARRAY[]::TEXT[],
    retention_days INTEGER DEFAULT 365,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    UNIQUE(table_name, column_name)
);

-- Table to store audit data with partitioning support
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    table_name VARCHAR(100) NOT NULL,
    operation VARCHAR(10) NOT NULL, -- INSERT, UPDATE, DELETE, TRUNCATE
    record_id UUID NOT NULL,
    old_data JSONB,
    new_data JSONB,
    changed_fields JSONB,
    user_id UUID,
    user_name VARCHAR(200),
    user_email VARCHAR(255),
    user_ip INET,
    user_agent TEXT,
    session_id VARCHAR(100),
    request_id VARCHAR(100),
    application_name VARCHAR(100),
    database_user VARCHAR(100),
    client_addr INET,
    query TEXT,
    transaction_id BIGINT,
    statement_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    commit_timestamp TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
) PARTITION BY RANGE (statement_timestamp);

-- Create monthly partitions for audit_logs
DO $$
DECLARE
    start_date DATE := '2024-01-01';
    end_date DATE := '2026-12-31';
    current_date DATE;
    partition_name TEXT;
BEGIN
    current_date := start_date;
    
    WHILE current_date <= end_date LOOP
        partition_name := 'audit_logs_' || TO_CHAR(current_date, 'YYYY_MM');
        
        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF audit_logs
            FOR VALUES FROM (%L) TO (%L)',
            partition_name,
            current_date,
            current_date + INTERVAL '1 month'
        );
        
        -- Create indexes on partition
        EXECUTE format('
            CREATE INDEX idx_%I_table_record ON %I (table_name, record_id)',
            partition_name, partition_name
        );
        
        EXECUTE format('
            CREATE INDEX idx_%I_user_time ON %I (user_id, statement_timestamp)',
            partition_name, partition_name
        );
        
        current_date := current_date + INTERVAL '1 month';
    END LOOP;
END;
$$;

-- Create indexes on audit_logs parent
CREATE INDEX idx_audit_logs_table_record ON audit_logs (table_name, record_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs (statement_timestamp);
CREATE INDEX idx_audit_logs_user ON audit_logs (user_id);
CREATE INDEX idx_audit_logs_operation ON audit_logs (operation);
CREATE INDEX idx_audit_logs_changed_fields ON audit_logs USING gin (changed_fields);
CREATE INDEX idx_audit_logs_old_data ON audit_logs USING gin (old_data);
CREATE INDEX idx_audit_logs_new_data ON audit_logs USING gin (new_data);

-- Table to store sensitive data masking rules
CREATE TABLE audit_masking_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    mask_type VARCHAR(50) NOT NULL, -- 'partial', 'full', 'email', 'credit_card', 'phone'
    mask_character CHAR(1) DEFAULT '*',
    visible_chars_start INTEGER DEFAULT 0,
    visible_chars_end INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(table_name, column_name)
);

-- Insert default masking rules
INSERT INTO audit_masking_rules (table_name, column_name, mask_type, visible_chars_start, visible_chars_end) VALUES
    ('users', 'password_hash', 'full', 0, 0),
    ('users', 'email', 'email', 2, 0),
    ('users', 'phone', 'phone', 3, 2),
    ('payments', 'card_last_four', 'partial', 0, 4),
    ('payments', 'card_expiry', 'full', 0, 0),
    ('payments', 'authorization_code', 'partial', 0, 4),
    ('users', 'first_name', 'partial', 1, 0),
    ('users', 'last_name', 'partial', 1, 0);

-- =====================================================
-- AUDIT UTILITY FUNCTIONS
-- =====================================================

-- Function to get current user context
CREATE OR REPLACE FUNCTION get_audit_context()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_context JSONB;
    v_user_id UUID;
    v_user_name TEXT;
    v_user_email TEXT;
BEGIN
    -- Try to get from session variable (set by application)
    BEGIN
        v_user_id := current_setting('app.current_user_id', true)::UUID;
        v_user_name := current_setting('app.current_user_name', true);
        v_user_email := current_setting('app.current_user_email', true);
    EXCEPTION WHEN OTHERS THEN
        v_user_id := NULL;
        v_user_name := NULL;
        v_user_email := NULL;
    END;
    
    v_context := jsonb_build_object(
        'user_id', v_user_id,
        'user_name', v_user_name,
        'user_email', v_user_email,
        'database_user', current_user,
        'client_addr', inet_client_addr(),
        'session_id', current_setting('app.session_id', true),
        'request_id', current_setting('app.request_id', true),
        'application_name', current_setting('application_name', true),
        'transaction_id', txid_current()
    );
    
    RETURN v_context;
END;
$$;

-- Function to mask sensitive data
CREATE OR REPLACE FUNCTION mask_sensitive_data(
    p_table_name TEXT,
    p_column_name TEXT,
    p_value TEXT
)
RETURNS TEXT
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_rule RECORD;
    v_result TEXT;
BEGIN
    SELECT * INTO v_rule
    FROM audit_masking_rules
    WHERE table_name = p_table_name AND column_name = p_column_name;
    
    IF NOT FOUND OR p_value IS NULL THEN
        RETURN p_value;
    END IF;
    
    CASE v_rule.mask_type
        WHEN 'full' THEN
            v_result := repeat(v_rule.mask_character, length(p_value));
            
        WHEN 'partial' THEN
            v_result := 
                repeat(v_rule.mask_character, v_rule.visible_chars_start) ||
                substring(p_value from v_rule.visible_chars_start + 1 for 
                         length(p_value) - v_rule.visible_chars_start - v_rule.visible_chars_end) ||
                repeat(v_rule.mask_character, v_rule.visible_chars_end);
            
        WHEN 'email' THEN
            SELECT 
                CASE 
                    WHEN p_value LIKE '%@%' THEN
                        substring(p_value from 1 for v_rule.visible_chars_start) ||
                        repeat(v_rule.mask_character, 
                               position('@' in p_value) - v_rule.visible_chars_start - 1) ||
                        substring(p_value from position('@' in p_value))
                    ELSE p_value
                END INTO v_result;
            
        WHEN 'credit_card' THEN
            v_result := repeat(v_rule.mask_character, length(p_value) - 4) || 
                       right(p_value, 4);
            
        WHEN 'phone' THEN
            v_result := 
                repeat(v_rule.mask_character, v_rule.visible_chars_start) ||
                regexp_replace(substring(p_value from v_rule.visible_chars_start + 1), 
                              '[0-9]', v_rule.mask_character, 'g') ||
                right(p_value, v_rule.visible_chars_end);
            
        ELSE
            v_result := p_value;
    END CASE;
    
    RETURN v_result;
END;
$$;

-- Function to compare JSONB objects and return changed fields
CREATE OR REPLACE FUNCTION get_changed_fields(
    p_old_data JSONB,
    p_new_data JSONB,
    p_table_name TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_result JSONB := '{}'::JSONB;
    v_key TEXT;
    v_old_value JSONB;
    v_new_value JSONB;
    v_excluded_columns TEXT[];
BEGIN
    -- Get excluded columns from config if table specified
    IF p_table_name IS NOT NULL THEN
        SELECT exclude_columns INTO v_excluded_columns
        FROM audit_config
        WHERE table_name = p_table_name AND column_name IS NULL;
    END IF;
    
    IF p_old_data IS NULL OR p_new_data IS NULL THEN
        RETURN v_result;
    END IF;
    
    FOR v_key IN SELECT jsonb_object_keys(p_new_data) LOOP
        -- Skip excluded columns
        IF v_excluded_columns IS NOT NULL AND v_key = ANY(v_excluded_columns) THEN
            CONTINUE;
        END IF;
        
        v_old_value := p_old_data->v_key;
        v_new_value := p_new_data->v_key;
        
        IF v_old_value IS DISTINCT FROM v_new_value THEN
            v_result := v_result || jsonb_build_object(
                v_key, jsonb_build_object(
                    'old', v_old_value,
                    'new', v_new_value
                )
            );
        END IF;
    END LOOP;
    
    RETURN v_result;
END;
$$;

-- =====================================================
-- CORE AUDIT TRIGGER FUNCTION
-- =====================================================

CREATE OR REPLACE FUNCTION audit_trigger()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_old_data JSONB;
    v_new_data JSONB;
    v_changed_fields JSONB;
    v_context JSONB;
    v_audit_level VARCHAR(20);
    v_excluded_columns TEXT[];
    v_sensitive_columns TEXT[];
    v_config RECORD;
    v_record_id UUID;
    v_operation VARCHAR(10);
    v_audit_data JSONB;
BEGIN
    -- Get audit configuration for this table
    SELECT * INTO v_config
    FROM audit_config
    WHERE table_name = TG_TABLE_NAME
    ORDER BY column_name NULLS FIRST
    LIMIT 1;
    
    -- Set audit level (default to 'full')
    v_audit_level := COALESCE(v_config.audit_level, 'full');
    
    -- Get excluded columns
    v_excluded_columns := COALESCE(v_config.exclude_columns, ARRAY[]::TEXT[]);
    
    -- Get sensitive columns
    v_sensitive_columns := COALESCE(v_config.sensitive_columns, ARRAY[]::TEXT[]);
    
    -- Get current context
    v_context := get_audit_context();
    
    -- Determine operation and record ID
    IF TG_OP = 'DELETE' THEN
        v_operation := 'DELETE';
        v_record_id := OLD.id;
        v_old_data := to_jsonb(OLD);
        v_new_data := NULL;
        v_changed_fields := NULL;
    ELSIF TG_OP = 'INSERT' THEN
        v_operation := 'INSERT';
        v_record_id := NEW.id;
        v_old_data := NULL;
        v_new_data := to_jsonb(NEW);
        v_changed_fields := NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        v_operation := 'UPDATE';
        v_record_id := NEW.id;
        v_old_data := to_jsonb(OLD);
        v_new_data := to_jsonb(NEW);
        
        -- Get changed fields
        v_changed_fields := get_changed_fields(v_old_data, v_new_data, TG_TABLE_NAME);
        
        -- If no changes, return early (unless audit_level is 'full')
        IF v_changed_fields = '{}'::JSONB AND v_audit_level != 'full' THEN
            RETURN NEW;
        END IF;
    ELSIF TG_OP = 'TRUNCATE' THEN
        v_operation := 'TRUNCATE';
        v_record_id := NULL;
        v_old_data := NULL;
        v_new_data := NULL;
        v_changed_fields := NULL;
    END IF;
    
    -- Mask sensitive data if configured
    IF v_sensitive_columns IS NOT NULL AND array_length(v_sensitive_columns, 1) > 0 THEN
        -- Mask in old_data
        IF v_old_data IS NOT NULL THEN
            FOR i IN 1..array_length(v_sensitive_columns, 1) LOOP
                IF v_old_data ? v_sensitive_columns[i] THEN
                    v_old_data := jsonb_set(
                        v_old_data,
                        ARRAY[v_sensitive_columns[i]],
                        to_jsonb(mask_sensitive_data(
                            TG_TABLE_NAME,
                            v_sensitive_columns[i],
                            v_old_data->>v_sensitive_columns[i]
                        ))
                    );
                END IF;
            END LOOP;
        END IF;
        
        -- Mask in new_data
        IF v_new_data IS NOT NULL THEN
            FOR i IN 1..array_length(v_sensitive_columns, 1) LOOP
                IF v_new_data ? v_sensitive_columns[i] THEN
                    v_new_data := jsonb_set(
                        v_new_data,
                        ARRAY[v_sensitive_columns[i]],
                        to_jsonb(mask_sensitive_data(
                            TG_TABLE_NAME,
                            v_sensitive_columns[i],
                            v_new_data->>v_sensitive_columns[i]
                        ))
                    );
                END IF;
            END LOOP;
        END IF;
        
        -- Mask in changed_fields
        IF v_changed_fields IS NOT NULL THEN
            FOR i IN 1..array_length(v_sensitive_columns, 1) LOOP
                IF v_changed_fields ? v_sensitive_columns[i] THEN
                    v_changed_fields := jsonb_set(
                        v_changed_fields,
                        ARRAY[v_sensitive_columns[i], 'old'],
                        to_jsonb(mask_sensitive_data(
                            TG_TABLE_NAME,
                            v_sensitive_columns[i],
                            v_changed_fields->v_sensitive_columns[i]->>'old'
                        ))
                    );
                    v_changed_fields := jsonb_set(
                        v_changed_fields,
                        ARRAY[v_sensitive_columns[i], 'new'],
                        to_jsonb(mask_sensitive_data(
                            TG_TABLE_NAME,
                            v_sensitive_columns[i],
                            v_changed_fields->v_sensitive_columns[i]->>'new'
                        ))
                    );
                END IF;
            END LOOP;
        END IF;
    END IF;
    
    -- Remove excluded columns from data
    IF array_length(v_excluded_columns, 1) > 0 THEN
        IF v_old_data IS NOT NULL THEN
            v_old_data := v_old_data - v_excluded_columns;
        END IF;
        IF v_new_data IS NOT NULL THEN
            v_new_data := v_new_data - v_excluded_columns;
        END IF;
        IF v_changed_fields IS NOT NULL THEN
            v_changed_fields := v_changed_fields - v_excluded_columns;
        END IF;
    END IF;
    
    -- Prepare audit data
    v_audit_data := jsonb_build_object(
        'table_name', TG_TABLE_NAME,
        'operation', v_operation,
        'record_id', v_record_id,
        'old_data', v_old_data,
        'new_data', v_new_data,
        'changed_fields', v_changed_fields,
        'user_id', v_context->>'user_id',
        'user_name', v_context->>'user_name',
        'user_email', v_context->>'user_email',
        'user_ip', v_context->>'client_addr',
        'database_user', v_context->>'database_user',
        'session_id', v_context->>'session_id',
        'request_id', v_context->>'request_id',
        'application_name', v_context->>'application_name',
        'transaction_id', v_context->>'transaction_id',
        'statement_timestamp', statement_timestamp(),
        'query', current_query()
    );
    
    -- Insert into audit_logs
    INSERT INTO audit_logs (
        table_name,
        operation,
        record_id,
        old_data,
        new_data,
        changed_fields,
        user_id,
        user_name,
        user_email,
        user_ip,
        database_user,
        session_id,
        request_id,
        application_name,
        transaction_id,
        statement_timestamp,
        query
    ) VALUES (
        v_audit_data->>'table_name',
        v_audit_data->>'operation',
        (v_audit_data->>'record_id')::UUID,
        v_audit_data->'old_data',
        v_audit_data->'new_data',
        v_audit_data->'changed_fields',
        (v_audit_data->>'user_id')::UUID,
        v_audit_data->>'user_name',
        v_audit_data->>'user_email',
        (v_audit_data->>'user_ip')::INET,
        v_audit_data->>'database_user',
        v_audit_data->>'session_id',
        v_audit_data->>'request_id',
        v_audit_data->>'application_name',
        (v_audit_data->>'transaction_id')::BIGINT,
        (v_audit_data->>'statement_timestamp')::TIMESTAMP WITH TIME ZONE,
        v_audit_data->>'query'
    );
    
    -- Return appropriate value based on operation
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$;

-- =====================================================
-- AUDIT CONFIGURATION
-- =====================================================

-- Configure audit settings for each table
INSERT INTO audit_config (table_name, audit_level, exclude_columns, sensitive_columns, retention_days) VALUES
    ('users', 'full', ARRAY['created_at', 'updated_at'], ARRAY['password_hash', 'email', 'phone'], 730),
    ('organizations', 'full', ARRAY['created_at', 'updated_at'], ARRAY['tax_id', 'email', 'phone'], 730),
    ('parking_lots', 'full', ARRAY['created_at', 'updated_at'], ARRAY['email', 'phone'], 730),
    ('parking_sessions', 'full', ARRAY['created_at', 'updated_at'], NULL, 730),
    ('payments', 'full', ARRAY['created_at', 'updated_at'], ARRAY['card_last_four', 'card_expiry', 'authorization_code'], 1095),
    ('vehicles', 'full', ARRAY['created_at', 'updated_at'], ARRAY['license_plate'], 730),
    ('reservations', 'full', ARRAY['created_at', 'updated_at'], ARRAY['customer_email', 'customer_phone'], 730),
    ('blacklisted_vehicles', 'full', ARRAY['created_at', 'updated_at'], NULL, 730),
    ('rates', 'changes_only', ARRAY['created_at', 'updated_at'], NULL, 365),
    ('sensors', 'changes_only', ARRAY['created_at', 'updated_at', 'last_reading'], NULL, 365),
    ('gates', 'changes_only', ARRAY['created_at', 'updated_at', 'last_activity'], NULL, 365),
    ('cameras', 'changes_only', ARRAY['created_at', 'updated_at', 'last_online'], NULL, 365);

-- =====================================================
-- APPLY AUDIT TRIGGERS TO ALL TABLES
-- =====================================================

-- Function to create audit trigger on a table
CREATE OR REPLACE FUNCTION create_audit_trigger(p_table_name TEXT)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    EXECUTE format('
        DROP TRIGGER IF EXISTS audit_trigger ON %I;
        
        CREATE TRIGGER audit_trigger
        AFTER INSERT OR UPDATE OR DELETE ON %I
        FOR EACH ROW EXECUTE FUNCTION audit_trigger();
    ', p_table_name, p_table_name);
END;
$$;

-- Create audit triggers on all tables
SELECT create_audit_trigger('users');
SELECT create_audit_trigger('organizations');
SELECT create_audit_trigger('parking_lots');
SELECT create_audit_trigger('parking_levels');
SELECT create_audit_trigger('parking_spaces');
SELECT create_audit_trigger('entrance_exits');
SELECT create_audit_trigger('gates');
SELECT create_audit_trigger('cameras');
SELECT create_audit_trigger('sensors');
SELECT create_audit_trigger('sensor_data');
SELECT create_audit_trigger('vehicles');
SELECT create_audit_trigger('rates');
SELECT create_audit_trigger('parking_sessions');
SELECT create_audit_trigger('reservations');
SELECT create_audit_trigger('payments');
SELECT create_audit_trigger('blacklisted_vehicles');
SELECT create_audit_trigger('notifications');
SELECT create_audit_trigger('activity_logs');
SELECT create_audit_trigger('camera_events');
SELECT create_audit_trigger('camera_images');
SELECT create_audit_trigger('gate_events');
SELECT create_audit_trigger('user_roles');
SELECT create_audit_trigger('roles');

-- =====================================================
-- SPECIALIZED AUDIT FUNCTIONS
-- =====================================================

-- Function to get audit history for a record
CREATE OR REPLACE FUNCTION get_audit_history(
    p_table_name TEXT,
    p_record_id UUID,
    p_start_date TIMESTAMPTZ DEFAULT NULL,
    p_end_date TIMESTAMPTZ DEFAULT NULL,
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    audit_id UUID,
    operation VARCHAR(10),
    changed_fields JSONB,
    old_data JSONB,
    new_data JSONB,
    user_name VARCHAR(200),
    user_email VARCHAR(255),
    changed_at TIMESTAMP WITH TIME ZONE,
    transaction_id BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        al.id,
        al.operation,
        al.changed_fields,
        al.old_data,
        al.new_data,
        al.user_name,
        al.user_email,
        al.statement_timestamp,
        al.transaction_id
    FROM audit_logs al
    WHERE al.table_name = p_table_name
      AND al.record_id = p_record_id
      AND (p_start_date IS NULL OR al.statement_timestamp >= p_start_date)
      AND (p_end_date IS NULL OR al.statement_timestamp <= p_end_date)
    ORDER BY al.statement_timestamp DESC
    LIMIT p_limit;
END;
$$;

-- Function to compare two versions of a record
CREATE OR REPLACE FUNCTION compare_record_versions(
    p_table_name TEXT,
    p_record_id UUID,
    p_version1 TIMESTAMPTZ,
    p_version2 TIMESTAMPTZ
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_data1 JSONB;
    v_data2 JSONB;
    v_diff JSONB := '{}'::JSONB;
BEGIN
    -- Get data at version1
    SELECT new_data INTO v_data1
    FROM audit_logs
    WHERE table_name = p_table_name
      AND record_id = p_record_id
      AND statement_timestamp <= p_version1
    ORDER BY statement_timestamp DESC
    LIMIT 1;
    
    -- Get data at version2
    SELECT new_data INTO v_data2
    FROM audit_logs
    WHERE table_name = p_table_name
      AND record_id = p_record_id
      AND statement_timestamp <= p_version2
    ORDER BY statement_timestamp DESC
    LIMIT 1;
    
    -- Compare and return differences
    v_diff := get_changed_fields(v_data1, v_data2);
    
    RETURN jsonb_build_object(
        'version1_timestamp', p_version1,
        'version2_timestamp', p_version2,
        'version1_data', v_data1,
        'version2_data', v_data2,
        'differences', v_diff
    );
END;
$$;

-- Function to get user activity summary
CREATE OR REPLACE FUNCTION get_user_activity_summary(
    p_user_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    table_name TEXT,
    operation_count BIGINT,
    last_activity TIMESTAMP WITH TIME ZONE,
    operations JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        al.table_name,
        COUNT(*) AS operation_count,
        MAX(al.statement_timestamp) AS last_activity,
        jsonb_object_agg(al.operation, COUNT(*)) AS operations
    FROM audit_logs al
    WHERE al.user_id = p_user_id
      AND al.statement_timestamp >= CURRENT_TIMESTAMP - (p_days || ' days')::INTERVAL
    GROUP BY al.table_name
    ORDER BY last_activity DESC;
END;
$$;

-- =====================================================
-- AUDIT REPORTS AND ANALYTICS
-- =====================================================

-- View for daily audit summary
CREATE OR REPLACE VIEW v_audit_daily_summary AS
SELECT 
    DATE(statement_timestamp) AS audit_date,
    table_name,
    operation,
    COUNT(*) AS operation_count,
    COUNT(DISTINCT user_id) AS unique_users,
    COUNT(DISTINCT record_id) AS unique_records,
    COUNT(*) FILTER (WHERE changed_fields IS NOT NULL AND changed_fields != '{}'::JSONB) AS records_changed,
    MODE() WITHIN GROUP (ORDER BY user_name) AS most_active_user,
    MIN(statement_timestamp) AS first_operation,
    MAX(statement_timestamp) AS last_operation
FROM audit_logs
GROUP BY DATE(statement_timestamp), table_name, operation
ORDER BY audit_date DESC, table_name, operation;

-- View for sensitive data access audit
CREATE OR REPLACE VIEW v_sensitive_data_access AS
SELECT 
    al.statement_timestamp,
    al.table_name,
    al.operation,
    al.record_id,
    al.user_name,
    al.user_email,
    al.user_ip,
    jsonb_object_keys(
        CASE 
            WHEN al.operation = 'UPDATE' THEN al.changed_fields
            ELSE al.new_data
        END
    ) AS accessed_column
FROM audit_logs al
WHERE al.table_name IN ('users', 'payments')
  AND (
    (al.operation = 'UPDATE' AND al.changed_fields ?| ARRAY['password_hash', 'email', 'phone', 'card_last_four'])
    OR
    (al.operation = 'SELECT' AND al.new_data ?| ARRAY['password_hash', 'email', 'phone', 'card_last_four'])
  )
ORDER BY al.statement_timestamp DESC;

-- View for anomaly detection
CREATE OR REPLACE VIEW v_audit_anomalies AS
WITH stats AS (
    SELECT 
        table_name,
        operation,
        AVG(COUNT(*)) OVER (PARTITION BY table_name, operation) AS avg_count,
        STDDEV(COUNT(*)) OVER (PARTITION BY table_name, operation) AS stddev_count
    FROM v_audit_daily_summary
    WHERE audit_date >= CURRENT_DATE - 30
    GROUP BY table_name, operation, audit_date
)
SELECT 
    v.audit_date,
    v.table_name,
    v.operation,
    v.operation_count,
    s.avg_count,
    s.stddev_count,
    CASE 
        WHEN v.operation_count > s.avg_count + 3 * s.stddev_count THEN 'HIGH_VOLUME'
        WHEN v.operation_count < s.avg_count - 3 * s.stddev_count THEN 'LOW_VOLUME'
        WHEN v.operation_count > s.avg_count + 2 * s.stddev_count THEN 'MEDIUM_VOLUME'
        ELSE 'NORMAL'
    END AS alert_level
FROM v_audit_daily_summary v
JOIN stats s ON v.table_name = s.table_name AND v.operation = s.operation
WHERE v.audit_date = CURRENT_DATE
  AND ABS(v.operation_count - s.avg_count) > 2 * s.stddev_count;

-- =====================================================
-- AUDIT DATA RETENTION AND CLEANUP
-- =====================================================

-- Function to purge old audit data
CREATE OR REPLACE FUNCTION purge_old_audit_data(
    p_retention_days INTEGER DEFAULT 365,
    p_dry_run BOOLEAN DEFAULT false
)
RETURNS TABLE (
    table_name TEXT,
    partition_name TEXT,
    rows_deleted BIGINT,
    space_freed TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_cutoff_date DATE;
    v_partition RECORD;
    v_count BIGINT;
    v_size BIGINT;
BEGIN
    v_cutoff_date := CURRENT_DATE - p_retention_days;
    
    FOR v_partition IN 
        SELECT 
            child.relname AS partition_name,
            pg_total_relation_size(child.oid) AS partition_size
        FROM pg_inherits
        JOIN pg_class child ON pg_inherits.inhrelid = child.oid
        WHERE inhparent = 'audit_logs'::regclass
          AND child.relname LIKE 'audit_logs_%'
          AND substring(child.relname from 'audit_logs_(\d{4}_\d{2})') < TO_CHAR(v_cutoff_date, 'YYYY_MM')
    LOOP
        table_name := 'audit_logs';
        partition_name := v_partition.partition_name;
        
        IF p_dry_run THEN
            EXECUTE format('SELECT COUNT(*) FROM %I', v_partition.partition_name) INTO v_count;
            rows_deleted := v_count;
            space_freed := pg_size_pretty(v_partition.partition_size);
        ELSE
            -- Detach and drop partition
            EXECUTE format('
                ALTER TABLE audit_logs DETACH PARTITION %I;
                DROP TABLE %I;
            ', v_partition.partition_name, v_partition.partition_name);
            
            rows_deleted := -1; -- Unknown after drop
            space_freed := pg_size_pretty(v_partition.partition_size);
        END IF;
        
        RETURN NEXT;
    END LOOP;
END;
$$;

-- Schedule monthly audit data purge
SELECT cron.schedule(
    'purge-audit-logs',
    '0 3 1 * *', -- Run at 3 AM on the first day of each month
    'SELECT purge_old_audit_data(365, false);'
);

-- =====================================================
-- AUDIT MONITORING AND ALERTS
-- =====================================================

-- Function to check audit integrity
CREATE OR REPLACE FUNCTION check_audit_integrity()
RETURNS TABLE (
    check_name TEXT,
    status TEXT,
    details JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_count BIGINT;
    v_last_audit TIMESTAMPTZ;
    v_missing_tables TEXT[];
BEGIN
    -- Check for missing audit records
    WITH tables_without_audit AS (
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename NOT IN ('audit_logs', 'audit_config', 'audit_masking_rules')
          AND NOT EXISTS (
              SELECT 1 FROM audit_logs 
              WHERE table_name = tablename 
              LIMIT 1
          )
    )
    SELECT array_agg(tablename) INTO v_missing_tables
    FROM tables_without_audit;
    
    check_name := 'missing_audit_records';
    IF v_missing_tables IS NULL THEN
        status := 'OK';
        details := '{}'::JSONB;
    ELSE
        status := 'WARNING';
        details := jsonb_build_object('tables', v_missing_tables);
    END IF;
    RETURN NEXT;
    
    -- Check audit log continuity
    SELECT MAX(statement_timestamp) INTO v_last_audit
    FROM audit_logs;
    
    check_name := 'audit_continuity';
    IF v_last_audit >= CURRENT_TIMESTAMP - INTERVAL '1 hour' THEN
        status := 'OK';
        details := jsonb_build_object('last_audit', v_last_audit);
    ELSE
        status := 'CRITICAL';
        details := jsonb_build_object(
            'last_audit', v_last_audit,
            'gap_hours', EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - v_last_audit))/3600
        );
    END IF;
    RETURN NEXT;
    
    -- Check for orphaned audit records
    SELECT COUNT(*) INTO v_count
    FROM audit_logs al
    WHERE NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = al.table_name
    );
    
    check_name := 'orphaned_records';
    IF v_count = 0 THEN
        status := 'OK';
        details := '{}'::JSONB;
    ELSE
        status := 'WARNING';
        details := jsonb_build_object('orphaned_count', v_count);
    END IF;
    RETURN NEXT;
END;
$$;

-- =====================================================
-- AUDIT DATA EXPORT FUNCTIONS
-- =====================================================

-- Function to export audit data for compliance
CREATE OR REPLACE FUNCTION export_audit_data(
    p_start_date DATE,
    p_end_date DATE,
    p_table_name TEXT DEFAULT NULL,
    p_user_id UUID DEFAULT NULL
)
RETURNS TABLE (
    export_data JSONB
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT jsonb_build_object(
        'export_id', uuid_generate_v7(),
        'exported_at', CURRENT_TIMESTAMP,
        'exported_by', current_user,
        'date_range', jsonb_build_object('start', p_start_date, 'end', p_end_date),
        'filters', jsonb_build_object(
            'table_name', p_table_name,
            'user_id', p_user_id
        ),
        'records', jsonb_agg(
            jsonb_build_object(
                'timestamp', al.statement_timestamp,
                'table', al.table_name,
                'operation', al.operation,
                'record_id', al.record_id,
                'user', jsonb_build_object(
                    'id', al.user_id,
                    'name', al.user_name,
                    'email', al.user_email
                ),
                'changes', al.changed_fields,
                'ip_address', al.user_ip,
                'session_id', al.session_id
            )
            ORDER BY al.statement_timestamp
        )
    )
    FROM audit_logs al
    WHERE al.statement_timestamp::DATE BETWEEN p_start_date AND p_end_date
      AND (p_table_name IS NULL OR al.table_name = p_table_name)
      AND (p_user_id IS NULL OR al.user_id = p_user_id);
END;
$$;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE audit_logs IS 'Comprehensive audit trail for all data changes';
COMMENT ON TABLE audit_config IS 'Configuration for audit logging per table';
COMMENT ON TABLE audit_masking_rules IS 'Rules for masking sensitive data in audit logs';
COMMENT ON FUNCTION audit_trigger() IS 'Main audit trigger function for all tables';
COMMENT ON FUNCTION get_audit_history(TEXT, UUID, TIMESTAMPTZ, TIMESTAMPTZ, INTEGER) IS 'Retrieves audit history for a specific record';
COMMENT ON FUNCTION compare_record_versions(TEXT, UUID, TIMESTAMPTZ, TIMESTAMPTZ) IS 'Compares two versions of a record from audit trail';
COMMENT ON VIEW v_audit_daily_summary IS 'Daily summary of audit activities';
COMMENT ON VIEW v_sensitive_data_access IS 'Tracks access to sensitive data columns';
COMMENT ON VIEW v_audit_anomalies IS 'Detects anomalies in audit patterns';
COMMENT ON FUNCTION purge_old_audit_data(INTEGER, BOOLEAN) IS 'Purges audit data older than retention period';

-- =====================================================
-- ROLLBACK INSTRUCTIONS
-- =====================================================

/*
-- To rollback this migration, run:

-- Drop triggers
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN 
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename NOT IN ('audit_logs', 'audit_config', 'audit_masking_rules')
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS audit_trigger ON %I;', t);
    END LOOP;
END;
$$;

-- Drop functions
DROP FUNCTION IF EXISTS audit_trigger() CASCADE;
DROP FUNCTION IF EXISTS get_audit_context() CASCADE;
DROP FUNCTION IF EXISTS mask_sensitive_data(TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_changed_fields(JSONB, JSONB, TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_audit_history(TEXT, UUID, TIMESTAMPTZ, TIMESTAMPTZ, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS compare_record_versions(TEXT, UUID, TIMESTAMPTZ, TIMESTAMPTZ) CASCADE;
DROP FUNCTION IF EXISTS get_user_activity_summary(UUID, INTEGER) CASCADE;
DROP FUNCTION IF EXISTS purge_old_audit_data(INTEGER, BOOLEAN) CASCADE;
DROP FUNCTION IF EXISTS check_audit_integrity() CASCADE;
DROP FUNCTION IF EXISTS export_audit_data(DATE, DATE, TEXT, UUID) CASCADE;
DROP FUNCTION IF EXISTS create_audit_trigger(TEXT) CASCADE;

-- Drop views
DROP VIEW IF EXISTS v_audit_daily_summary CASCADE;
DROP VIEW IF EXISTS v_sensitive_data_access CASCADE;
DROP VIEW IF EXISTS v_audit_anomalies CASCADE;

-- Drop tables
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS audit_config CASCADE;
DROP TABLE IF EXISTS audit_masking_rules CASCADE;

-- Unschedule cron jobs
SELECT cron.unschedule('purge-audit-logs');
*/

COMMIT;