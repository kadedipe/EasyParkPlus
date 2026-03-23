# parking-management/backend/scripts/maintenance/cleanup/clean.sh
# System cleanup tasks

run_cleanup_maintenance() {
    log_info "Starting system cleanup..."
    
    # Clean temporary files
    clean_temp_files
    
    # Clean orphaned uploads
    clean_orphaned_uploads
    
    # Clean failed jobs
    clean_failed_jobs
    
    # Clean expired sessions
    clean_expired_sessions
    
    # Clean old cache files
    clean_cache_files
    
    # Clean npm cache
    clean_npm_cache
    
    # Generate cleanup report
    generate_cleanup_report
    
    log_success "System cleanup completed"
    return 0
}

clean_temp_files() {
    log_info "Cleaning temporary files..."
    
    local temp_dirs=(
        "/tmp/${APP_NAME}"
        "${CURRENT_DIR}/tmp"
        "${CURRENT_DIR}/.temp"
    )
    
    for temp_dir in "${temp_dirs[@]}"; do
        if [ -d "${temp_dir}" ]; then
            log_info "Cleaning: ${temp_dir}"
            
            if [ "${DRY_RUN}" = "true" ]; then
                log_info "[DRY RUN] Would clean ${temp_dir}"
                continue
            fi
            
            find "${temp_dir}" -type f -mmin +${TEMP_FILE_AGE_HOURS} -delete 2>/dev/null
            find "${temp_dir}" -type d -empty -delete 2>/dev/null
        fi
    done
    
    # Clean system temp files
    find "/tmp" -name "${APP_NAME}_*" -mtime +1 -delete 2>/dev/null || true
    
    log_success "Temporary files cleaned"
    return 0
}

clean_orphaned_uploads() {
    log_info "Cleaning orphaned uploads..."
    
    local uploads_dir="${SHARED_DIR}/uploads"
    
    if [ ! -d "${uploads_dir}" ]; then
        log_warning "Uploads directory not found: ${uploads_dir}"
        return 0
    fi
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would clean orphaned uploads older than ${ORPHANED_UPLOADS_AGE_DAYS} days"
        return 0
    fi
    
    # Get list of files not referenced in database
    local orphaned_files=$(find "${uploads_dir}" -type f -mtime +${ORPHANED_UPLOADS_AGE_DAYS} -printf "%f\n" 2>/dev/null)
    local deleted=0
    
    for file in ${orphaned_files}; do
        # Check if file exists in database
        local exists=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
            -t -c "SELECT COUNT(*) FROM uploads WHERE file_path LIKE '%${file}'" 2>/dev/null | xargs)
        
        if [ "${exists}" = "0" ]; then
            rm -f "${uploads_dir}/${file}"
            deleted=$((deleted + 1))
            log_info "Deleted orphaned upload: ${file}"
        fi
    done
    
    log_success "Cleaned ${deleted} orphaned uploads"
    return 0
}

clean_failed_jobs() {
    log_info "Cleaning failed jobs..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would clean failed jobs older than ${FAILED_JOBS_CLEANUP_DAYS} days"
        return 0
    fi
    
    # Clean failed jobs from queue
    local sql="
    DELETE FROM failed_jobs 
    WHERE failed_at < NOW() - INTERVAL '${FAILED_JOBS_CLEANUP_DAYS} days';
    
    DELETE FROM job_batches 
    WHERE created_at < NOW() - INTERVAL '${FAILED_JOBS_CLEANUP_DAYS} days';
    
    DELETE FROM jobs 
    WHERE reserved_at IS NULL 
    AND created_at < NOW() - INTERVAL '7 days';
    "
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}" 2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/cleanup.log"
    
    log_success "Failed jobs cleaned"
    return 0
}

clean_expired_sessions() {
    log_info "Cleaning expired sessions..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would clean expired sessions"
        return 0
    fi
    
    # Clean database sessions
    local sql="
    DELETE FROM sessions 
    WHERE expires_at < NOW();
    
    DELETE FROM login_attempts 
    WHERE created_at < NOW() - INTERVAL '1 day';
    
    DELETE FROM password_resets 
    WHERE created_at < NOW() - INTERVAL '1 day';
    "
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}" 2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/cleanup.log"
    
    log_success "Expired sessions cleaned"
    return 0
}

clean_cache_files() {
    log_info "Cleaning cache files..."
    
    local cache_dirs=(
        "${CURRENT_DIR}/node_modules/.cache"
        "${CURRENT_DIR}/.cache"
        "/tmp/${APP_NAME}-cache"
    )
    
    for cache_dir in "${cache_dirs[@]}"; do
        if [ -d "${cache_dir}" ]; then
            log_info "Cleaning: ${cache_dir}"
            
            if [ "${DRY_RUN}" = "true" ]; then
                log_info "[DRY RUN] Would clean ${cache_dir}"
                continue
            fi
            
            rm -rf "${cache_dir:?}"/* 2>/dev/null || true
        fi
    done
    
    log_success "Cache files cleaned"
    return 0
}

clean_npm_cache() {
    log_info "Cleaning npm cache..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would clean npm cache"
        return 0
    fi
    
    if command -v npm &> /dev/null; then
        # Clean npm cache if it's large
        local cache_size=$(du -sm ~/.npm 2>/dev/null | cut -f1)
        if [ -n "${cache_size}" ] && [ ${cache_size} -gt 1000 ]; then
            log_info "npm cache size: ${cache_size}MB, cleaning..."
            npm cache clean --force 2>&1 | tee -a "${MAINTENANCE_LOG_DIR}/cleanup.log"
        else
            log_info "npm cache size: ${cache_size}MB, skipping"
        fi
    fi
    
    return 0
}

generate_cleanup_report() {
    local report_file="${MAINTENANCE_LOG_DIR}/cleanup_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "========================================="
        echo "System Cleanup Report"
        echo "========================================="
        echo "Date: $(date)"
        echo ""
        
        echo "Disk Usage Before Cleanup:"
        df -h "${PROJECT_ROOT}"
        
        echo ""
        echo "Directory Sizes:"
        du -sh "${CURRENT_DIR}/logs" 2>/dev/null || echo "logs: N/A"
        du -sh "${CURRENT_DIR}/tmp" 2>/dev/null || echo "tmp: N/A"
        du -sh "${SHARED_DIR}/uploads" 2>/dev/null || echo "uploads: N/A"
        
        echo ""
        echo "File Counts:"
        echo "Temporary files: $(find /tmp -name "${APP_NAME}_*" -type f 2>/dev/null | wc -l)"
        echo "Old log files: $(find "${LOGS_DIR}" -name "*.log.*" -type f 2>/dev/null | wc -l)"
        
        echo ""
        echo "Database Statistics:"
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "
            SELECT 
                'Sessions' as table_name,
                COUNT(*) as row_count
            FROM sessions
            UNION ALL
            SELECT 
                'Failed Jobs',
                COUNT(*)
            FROM failed_jobs
            UNION ALL
            SELECT 
                'Login Attempts',
                COUNT(*)
            FROM login_attempts
            WHERE created_at > NOW() - INTERVAL '7 days';
        "
        
        echo "========================================="
    } > "${report_file}"
    
    log_info "Cleanup report generated: ${report_file}"
}