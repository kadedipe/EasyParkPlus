# parking-management/backend/scripts/maintenance/backup/verify.sh
# Backup verification and maintenance

run_backup_maintenance() {
    log_info "Starting backup maintenance..."
    
    # Verify backups
    if [ "${BACKUP_VERIFICATION_ENABLED}" = "true" ]; then
        verify_backups
    fi
    
    # Check backup space
    check_backup_space
    
    # Clean old backups
    clean_old_backups
    
    # Test restore from latest backup
    if [ "${FORCE}" = "true" ]; then
        test_restore_latest
    fi
    
    # Generate backup report
    generate_backup_report
    
    log_success "Backup maintenance completed"
    return 0
}

verify_backups() {
    log_info "Verifying backups..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would verify backups"
        return 0
    fi
    
    local backup_files=$(find "${BACKUP_DIR}" -name "*.sql.gz" -type f -mtime -7 2>/dev/null)
    local verified=0
    local failed=0
    
    for backup_file in ${backup_files}; do
        log_info "Verifying: $(basename ${backup_file})"
        
        # Test integrity
        if gunzip -t "${backup_file}" 2>/dev/null; then
            # Check content
            if zcat "${backup_file}" 2>/dev/null | head -n 5 | grep -q "PostgreSQL"; then
                log_success "Verified: ${backup_file}"
                verified=$((verified + 1))
            else
                log_error "Invalid backup format: ${backup_file}"
                failed=$((failed + 1))
            fi
        else
            log_error "Corrupted backup: ${backup_file}"
            failed=$((failed + 1))
        fi
    done
    
    log_info "Backup verification: ${verified} OK, ${failed} FAILED"
    
    if [ ${failed} -gt 0 ]; then
        send_alert "Backup verification failed" "${failed} backups failed verification"
        return 1
    fi
    
    return 0
}

check_backup_space() {
    log_info "Checking backup storage space..."
    
    local available_space=$(df -BG "${BACKUP_DIR}" | awk 'NR==2 {print $4}' | sed 's/G//')
    local used_space=$(du -BG "${BACKUP_DIR}" | cut -f1 | sed 's/G//')
    
    log_info "Backup space: ${used_space}GB used, ${available_space}GB free"
    
    if [ ${available_space} -lt ${BACKUP_MIN_FREE_SPACE_GB} ]; then
        log_warning "Low backup space: ${available_space}GB free (minimum: ${BACKUP_MIN_FREE_SPACE_GB}GB)"
        send_alert "Low backup space" "Only ${available_space}GB free on backup storage"
        
        # Aggressive cleanup
        clean_old_backups "aggressive"
    fi
    
    return 0
}

clean_old_backups() {
    local mode="${1:-normal}"
    local retention_days=${BACKUP_RETENTION_DAYS}
    
    if [ "${mode}" = "aggressive" ]; then
        retention_days=$((retention_days / 2))
        log_warning "Running aggressive backup cleanup (${retention_days} days)"
    fi
    
    log_info "Cleaning backups older than ${retention_days} days..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would delete backups older than ${retention_days} days"
        return 0
    fi
    
    local deleted=0
    local deleted_size=0
    
    find "${BACKUP_DIR}" -name "*.sql.gz" -type f -mtime +${retention_days} 2>/dev/null | while read -r backup_file; do
        local file_size=$(stat -f%z "${backup_file}" 2>/dev/null || stat -c%s "${backup_file}" 2>/dev/null)
        deleted_size=$((deleted_size + file_size))
        rm -f "${backup_file}"
        rm -f "${backup_file}.metadata.json"
        deleted=$((deleted + 1))
        log_info "Deleted: $(basename ${backup_file})"
    done
    
    log_success "Cleaned ${deleted} backups, freed $(numfmt --to=iec ${deleted_size})"
    return 0
}

test_restore_latest() {
    log_info "Testing restore from latest backup..."
    
    local latest_backup=$(find "${BACKUP_DIR}" -name "*.sql.gz" -type f -printf "%T@ %p\n" | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [ -z "${latest_backup}" ]; then
        log_warning "No backups found to test"
        return 1
    fi
    
    log_info "Testing: $(basename ${latest_backup})"
    
    if [ "${DRY_RUN}" = "true" ]; then
        log_info "[DRY RUN] Would test restore from ${latest_backup}"
        return 0
    fi
    
    # Create test database
    local test_db="${DB_NAME}_test_$(date +%Y%m%d)"
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
        -c "CREATE DATABASE ${test_db} TEMPLATE template0;" 2>/dev/null || true
    
    # Restore to test database
    if gunzip -c "${latest_backup}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${test_db}" &> /dev/null; then
        log_success "Restore test successful"
        
        # Clean up test database
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
            -c "DROP DATABASE ${test_db};" &> /dev/null
        
        return 0
    else
        log_error "Restore test failed"
        send_alert "Backup restore test failed" "Failed to restore from ${latest_backup}"
        
        # Clean up
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres \
            -c "DROP DATABASE ${test_db};" &> /dev/null
        
        return 1
    fi
}

generate_backup_report() {
    local report_file="${MAINTENANCE_LOG_DIR}/backup_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "========================================="
        echo "Backup Maintenance Report"
        echo "========================================="
        echo "Date: $(date)"
        echo "Backup Directory: ${BACKUP_DIR}"
        echo ""
        
        echo "Backup Statistics:"
        echo "Total Backups: $(find "${BACKUP_DIR}" -name "*.sql.gz" -type f | wc -l)"
        echo "Total Size: $(du -sh "${BACKUP_DIR}" | cut -f1)"
        echo ""
        
        echo "Latest Backups:"
        find "${BACKUP_DIR}" -name "*.sql.gz" -type f -printf "%T@ %p\n" | \
            sort -rn | head -10 | while read timestamp file; do
            local date=$(date -d "@${timestamp%.*}" "+%Y-%m-%d %H:%M:%S")
            local size=$(du -h "${file}" | cut -f1)
            echo "  ${date} - $(basename ${file}) (${size})"
        done
        
        echo ""
        echo "Backup Age Distribution:"
        echo "  < 7 days: $(find "${BACKUP_DIR}" -name "*.sql.gz" -type f -mtime -7 | wc -l)"
        echo "  7-30 days: $(find "${BACKUP_DIR}" -name "*.sql.gz" -type f -mtime -30 -mtime +7 | wc -l)"
        echo "  > 30 days: $(find "${BACKUP_DIR}" -name "*.sql.gz" -type f -mtime +30 | wc -l)"
        
        echo "========================================="
    } > "${report_file}"
    
    log_info "Backup report generated: ${report_file}"
}