# parking-management/backend/scripts/maintenance/database/optimize.sh
# Database optimization and maintenance

run_database_maintenance() {
    log_info "Starting database maintenance..."
    
    # Check database connection
    if ! check_database_connection; then
        log_error "Cannot connect to database"
        return 1
    fi
    
    # Get database statistics
    local db_stats=$(get_database_stats)
    log_info "Database statistics: ${db_stats}"
    
    # Run maintenance tasks
    local tasks=(
        "vacuum_analyze"
        "reindex_if_needed"
        "update_statistics"
        "cleanup_dead_tuples"
        "check_index_bloat"
        "check_table_bloat"
        "archive_old_data"
    )
    
    local exit_code=0
    
    for task in "${tasks[@]}"; do
        if ! "${task}"; then
            log_error "Task failed: ${task}"
            exit_code=1
        fi
    done
    
    # Generate report
    generate_database_report
    
    log_success "Database maintenance completed"
    return ${exit_code}
}

# Vacuum and analyze tables
vacuum_analyze() {
    log_info "Running VACUUM ANALYZE..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would run VACUUM ANALYZE"
        return 0
    fi
    
    # Get list of tables with high dead tuple ratio
    local tables=$(get_tables_needing_vacuum)
    
    if [ -z "${tables}" ]; then
        log_info "No tables need vacuuming"
        return 0
    fi
    
    log_info "Tables needing vacuum: ${tables}"
    
    # Vacuum each table
    for table in ${tables}; do
        log_info "Vacuuming table: ${table}"
        
        local start_time=$(date +%s)
        
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
            -c "VACUUM (VERBOSE, ANALYZE) ${table};" 2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/vacuum.log"
        
        if [ ${PIPESTATUS[0]} -eq 0 ]; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            log_success "Vacuumed ${table} in ${duration}s"
        else
            log_error "Failed to vacuum ${table}"
            return 1
        fi
    done
    
    return 0
}

# Get tables needing vacuum
get_tables_needing_vacuum() {
    local sql="
    SELECT schemaname || '.' || tablename
    FROM pg_stat_user_tables
    WHERE n_dead_tup > n_live_tup * ${VACUUM_THRESHOLD} / 100
    AND n_dead_tup > 1000
    ORDER BY n_dead_tup DESC;
    "
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "${sql}" 2>/dev/null | xargs
}

# Reindex if needed
reindex_if_needed() {
    log_info "Checking indexes for reindexing..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would reindex if needed"
        return 0
    fi
    
    # Get indexes with high bloat
    local indexes=$(get_bloated_indexes)
    
    if [ -z "${indexes}" ]; then
        log_info "No indexes need reindexing"
        return 0
    fi
    
    log_info "Indexes needing reindex: ${indexes}"
    
    for index in ${indexes}; do
        log_info "Reindexing: ${index}"
        
        local start_time=$(date +%s)
        
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
            -c "REINDEX INDEX CONCURRENTLY ${index};" 2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/reindex.log"
        
        if [ ${PIPESTATUS[0]} -eq 0 ]; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            log_success "Reindexed ${index} in ${duration}s"
        else
            log_error "Failed to reindex ${index}"
            return 1
        fi
    done
    
    return 0
}

# Get bloated indexes
get_bloated_indexes() {
    local sql="
    SELECT schemaname || '.' || indexname
    FROM pg_stat_user_indexes
    WHERE idx_scan > 0
    AND (idx_bloat_estimate > ${INDEX_BLOAT_THRESHOLD})
    ORDER BY idx_bloat_estimate DESC;
    "
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "${sql}" 2>/dev/null | xargs
}

# Update statistics
update_statistics() {
    log_info "Updating database statistics..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would update statistics"
        return 0
    fi
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -c "ANALYZE VERBOSE;" 2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/analyze.log"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_success "Statistics updated"
        return 0
    else
        log_error "Failed to update statistics"
        return 1
    fi
}

# Cleanup dead tuples
cleanup_dead_tuples() {
    log_info "Cleaning up dead tuples..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would cleanup dead tuples"
        return 0
    fi
    
    # VACUUM FULL on tables with many dead tuples
    local tables=$(get_tables_with_many_dead_tuples)
    
    for table in ${tables}; do
        log_warning "Running VACUUM FULL on ${table} (may take time)"
        
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
            -c "VACUUM FULL VERBOSE ${table};" 2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/vacuum_full.log"
    done
    
    return 0
}

# Get tables with many dead tuples
get_tables_with_many_dead_tuples() {
    local sql="
    SELECT schemaname || '.' || tablename
    FROM pg_stat_user_tables
    WHERE n_dead_tup > 100000
    ORDER BY n_dead_tup DESC
    LIMIT 10;
    "
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "${sql}" 2>/dev/null | xargs
}

# Check index bloat
check_index_bloat() {
    log_info "Checking index bloat..."
    
    local sql="
    SELECT 
        schemaname,
        indexname,
        pg_size_pretty(pg_relation_size(indexrelid)) as size,
        ROUND(100 * (1 - (pg_relation_size(indexrelid)::float / 
            (pg_relation_size(indexrelid) + bloat_size))), 2) as bloat_percent
    FROM pg_stat_user_indexes,
    LATERAL (
        SELECT GREATEST(0, pg_relation_size(indexrelid) - 
            (SELECT pg_relation_size(indexrelid) / 1.1)) as bloat_size
    ) bloat
    WHERE bloat_size > 0
    ORDER BY bloat_percent DESC
    LIMIT 10;
    "
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}" 2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/bloat_report.log"
}

# Check table bloat
check_table_bloat() {
    log_info "Checking table bloat..."
    
    local sql="
    SELECT 
        schemaname,
        tablename,
        pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as size,
        ROUND(100 * (n_dead_tup::float / NULLIF(n_live_tup + n_dead_tup, 0)), 2) as dead_tuple_percent
    FROM pg_stat_user_tables
    WHERE n_dead_tup > 1000
    ORDER BY dead_tuple_percent DESC
    LIMIT 10;
    "
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}" 2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/bloat_report.log"
}

# Archive old data
archive_old_data() {
    log_info "Archiving old data..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would archive old data"
        return 0
    fi
    
    # Archive old logs table data
    local archive_sql="
    -- Archive old audit logs (older than 90 days)
    INSERT INTO audit_logs_archive 
    SELECT * FROM audit_logs 
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    DELETE FROM audit_logs 
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    -- Archive old notifications
    UPDATE notifications 
    SET archived = true 
    WHERE created_at < NOW() - INTERVAL '30 days'
    AND archived = false;
    "
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "${archive_sql}" 2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/archive.log"
    
    log_success "Data archiving completed"
}

# Generate database maintenance report
generate_database_report() {
    local report_file="${MAINTENANCE_LOG_DIR}/database_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "========================================="
        echo "Database Maintenance Report"
        echo "========================================="
        echo "Date: $(date)"
        echo "Database: ${DB_NAME}"
        echo "Host: ${DB_HOST}:${DB_PORT}"
        echo ""
        
        echo "Database Size:"
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "
            SELECT 
                pg_database_size(current_database()) as size_bytes,
                pg_size_pretty(pg_database_size(current_database())) as size_pretty;
        "
        
        echo ""
        echo "Table Statistics:"
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "
            SELECT 
                schemaname,
                tablename,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size
            FROM pg_stat_user_tables
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 20;
        "
        
        echo ""
        echo "Index Statistics:"
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "
            SELECT 
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch,
                pg_size_pretty(pg_relation_size(indexrelid)) as index_size
            FROM pg_stat_user_indexes
            ORDER BY pg_relation_size(indexrelid) DESC
            LIMIT 20;
        "
        
        echo "========================================="
    } > "${report_file}"
    
    log_info "Database report generated: ${report_file}"
}

# Get database statistics
get_database_stats() {
    local sql="
    SELECT 
        'Size: ' || pg_size_pretty(pg_database_size(current_database())) || 
        ', Tables: ' || (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public') ||
        ', Indexes: ' || (SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public')
    "
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "${sql}" 2>/dev/null | xargs
}