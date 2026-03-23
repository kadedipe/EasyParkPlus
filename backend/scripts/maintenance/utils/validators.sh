# parking-management/backend/scripts/maintenance/utils/validators.sh
# Validation utilities for maintenance

is_maintenance_running() {
    if [ -f "${MAINTENANCE_LOCK_FILE}" ]; then
        local pid=$(cat "${MAINTENANCE_LOCK_FILE}")
        if kill -0 "${pid}" 2>/dev/null; then
            return 0
        else
            rm -f "${MAINTENANCE_LOCK_FILE}"
            return 1
        fi
    fi
    return 1
}

acquire_maintenance_lock() {
    local pid=$$
    
    if is_maintenance_running; then
        return 1
    fi
    
    echo "${pid}" > "${MAINTENANCE_LOCK_FILE}"
    log_info "Maintenance lock acquired (PID: ${pid})"
    return 0
}

release_maintenance_lock() {
    rm -f "${MAINTENANCE_LOCK_FILE}"
    log_info "Maintenance lock released"
}

is_maintenance_window() {
    local current_time=$(date +%H%M)
    local start_time=$(echo "${MAINTENANCE_WINDOW_START}" | tr -d ':')
    local end_time=$(echo "${MAINTENANCE_WINDOW_END}" | tr -d ':')
    
    if [ ${current_time} -ge ${start_time} ] && [ ${current_time} -le ${end_time} ]; then
        return 0
    else
        return 1
    fi
}

is_system_busy() {
    # Check CPU load
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1 | xargs)
    local cpu_count=$(nproc)
    
    if (( $(echo "${load_avg} > ${MAX_SYSTEM_LOAD}" | bc -l) )); then
        return 0
    fi
    
    # Check active connections
    if command -v redis-cli &> /dev/null; then
        local active_conn=$(redis-cli INFO clients | grep "connected_clients" | cut -d':' -f2 | xargs)
        if [ ${active_conn} -gt 500 ]; then
            return 0
        fi
    fi
    
    # Check active database connections
    local db_conn=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -t -c "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | xargs)
    
    if [ -n "${db_conn}" ] && [ ${db_conn} -gt 50 ]; then
        return 0
    fi
    
    return 1
}

record_maintenance_start() {
    local start_file="${MAINTENANCE_LOG_DIR}/last_maintenance.txt"
    echo "START: $(date -Iseconds)" > "${start_file}"
    echo "TYPE: ${MAINTENANCE_TYPE}" >> "${start_file}"
    echo "MODE: ${MAINTENANCE_MODE}" >> "${start_file}"
}

record_maintenance_end() {
    local exit_code=$1
    local end_file="${MAINTENANCE_LOG_DIR}/last_maintenance.txt"
    echo "END: $(date -Iseconds)" >> "${end_file}"
    echo "EXIT_CODE: ${exit_code}" >> "${end_file}"
}