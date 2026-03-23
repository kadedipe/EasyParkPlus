# parking-management/backend/scripts/maintenance/monitoring/health.sh
# Health monitoring and checks

run_health_checks() {
    log_info "Running health checks..."
    
    local health_status=0
    
    # Check application health
    if ! check_app_health; then
        health_status=1
    fi
    
    # Check database health
    if ! check_db_health; then
        health_status=1
    fi
    
    # Check Redis health
    if ! check_redis_health; then
        health_status=1
    fi
    
    # Check disk health
    if ! check_disk_health; then
        health_status=1
    fi
    
    # Check memory usage
    if ! check_memory_health; then
        health_status=1
    fi
    
    # Check CPU usage
    if ! check_cpu_health; then
        health_status=1
    fi
    
    # Check external services
    if ! check_external_services; then
        health_status=1
    fi
    
    # Generate health report
    generate_health_report
    
    if [ ${health_status} -eq 0 ]; then
        log_success "All health checks passed"
    else
        log_error "Health checks failed"
    fi
    
    return ${health_status}
}

check_app_health() {
    log_info "Checking application health..."
    
    local health_url="http://localhost:${APP_PORT}${HEALTH_ENDPOINT}"
    local start_time=$(date +%s%N)
    
    local response=$(curl -f -s -w "\n%{http_code}" "${health_url}" 2>/dev/null)
    local http_code=$(echo "${response}" | tail -n1)
    local end_time=$(date +%s%N)
    local response_time=$((($end_time - $start_time) / 1000000))
    
    if [ "${http_code}" = "200" ]; then
        local body=$(echo "${response}" | head -n-1)
        local status=$(echo "${body}" | jq -r '.status' 2>/dev/null || echo "unknown")
        
        log_info "Application status: ${status}, response time: ${response_time}ms"
        
        if [ ${response_time} -gt ${ALERT_THRESHOLD_RESPONSE_TIME} ]; then
            log_warning "Response time high: ${response_time}ms"
            send_alert "High response time" "API response time: ${response_time}ms"
        fi
        
        if [ "${status}" = "healthy" ] || [ "${status}" = "ok" ]; then
            return 0
        else
            log_error "Application unhealthy: ${status}"
            return 1
        fi
    else
        log_error "Application health check failed with HTTP ${http_code}"
        return 1
    fi
}

check_db_health() {
    log_info "Checking database health..."
    
    local start_time=$(date +%s%N)
    
    local result=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -c "SELECT 1 as health_check, EXTRACT(EPOCH FROM NOW()) as timestamp" -t 2>/dev/null)
    
    local end_time=$(date +%s%N)
    local response_time=$((($end_time - $start_time) / 1000000))
    
    if [ -n "${result}" ]; then
        log_info "Database response time: ${response_time}ms"
        
        if [ ${response_time} -gt 100 ]; then
            log_warning "Database response time high: ${response_time}ms"
        fi
        
        # Check active connections
        local active_conn=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
            -t -c "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | xargs)
        
        log_info "Active connections: ${active_conn}"
        
        # Check max connections
        local max_conn=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
            -t -c "SHOW max_connections;" 2>/dev/null | xargs)
        
        local usage_percent=$((active_conn * 100 / max_conn))
        if [ ${usage_percent} -gt 80 ]; then
            log_warning "High connection usage: ${usage_percent}%"
        fi
        
        return 0
    else
        log_error "Database health check failed"
        return 1
    fi
}

check_redis_health() {
    log_info "Checking Redis health..."
    
    if ! command -v redis-cli &> /dev/null; then
        log_warning "redis-cli not found"
        return 0
    fi
    
    local start_time=$(date +%s%N)
    
    if redis-cli ping 2>/dev/null | grep -q "PONG"; then
        local end_time=$(date +%s%N)
        local response_time=$((($end_time - $start_time) / 1000000))
        
        log_info "Redis response time: ${response_time}ms"
        
        # Check memory usage
        local used_memory=$(redis-cli INFO memory | grep "used_memory_human" | cut -d':' -f2 | xargs)
        local max_memory=$(redis-cli CONFIG GET maxmemory | tail -n1)
        
        if [ -n "${max_memory}" ] && [ "${max_memory}" != "0" ]; then
            log_info "Redis memory: ${used_memory} / $(numfmt --to=iec ${max_memory})"
        fi
        
        # Check connected clients
        local connected_clients=$(redis-cli INFO clients | grep "connected_clients" | cut -d':' -f2 | xargs)
        log_info "Redis clients: ${connected_clients}"
        
        return 0
    else
        log_error "Redis health check failed"
        return 1
    fi
}

check_disk_health() {
    log_info "Checking disk health..."
    
    local disk_usage=$(df -h "${PROJECT_ROOT}" | awk 'NR==2 {print $5}' | sed 's/%//')
    local disk_used=$(df -h "${PROJECT_ROOT}" | awk 'NR==2 {print $3}')
    local disk_available=$(df -h "${PROJECT_ROOT}" | awk 'NR==2 {print $4}')
    
    log_info "Disk usage: ${disk_usage}% (${disk_used} used, ${disk_available} free)"
    
    if [ ${disk_usage} -gt 90 ]; then
        log_error "Critical disk usage: ${disk_usage}%"
        send_alert "Critical disk usage" "Disk usage at ${disk_usage}%"
        return 1
    elif [ ${disk_usage} -gt 80 ]; then
        log_warning "High disk usage: ${disk_usage}%"
        send_alert "High disk usage" "Disk usage at ${disk_usage}%"
    fi
    
    # Check inode usage
    local inode_usage=$(df -i "${PROJECT_ROOT}" | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ ${inode_usage} -gt 90 ]; then
        log_warning "High inode usage: ${inode_usage}%"
    fi
    
    return 0
}

check_memory_health() {
    log_info "Checking memory usage..."
    
    local total_mem=$(free -m | awk 'NR==2 {print $2}')
    local used_mem=$(free -m | awk 'NR==2 {print $3}')
    local free_mem=$(free -m | awk 'NR==2 {print $4}')
    local usage_percent=$((used_mem * 100 / total_mem))
    
    log_info "Memory usage: ${usage_percent}% (${used_mem}MB / ${total_mem}MB)"
    
    if [ ${usage_percent} -gt 90 ]; then
        log_error "Critical memory usage: ${usage_percent}%"
        send_alert "Critical memory usage" "Memory usage at ${usage_percent}%"
        return 1
    elif [ ${usage_percent} -gt 80 ]; then
        log_warning "High memory usage: ${usage_percent}%"
        send_alert "High memory usage" "Memory usage at ${usage_percent}%"
    fi
    
    # Check swap usage
    local swap_used=$(free -m | awk 'NR==3 {print $3}')
    if [ ${swap_used} -gt 100 ]; then
        log_warning "High swap usage: ${swap_used}MB"
    fi
    
    return 0
}

check_cpu_health() {
    log_info "Checking CPU usage..."
    
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | xargs)
    
    log_info "CPU usage: ${cpu_usage}%, Load average: ${load_avg}"
    
    if [ ${cpu_usage%.*} -gt 90 ]; then
        log_error "Critical CPU usage: ${cpu_usage}%"
        send_alert "Critical CPU usage" "CPU usage at ${cpu_usage}%"
        return 1
    elif [ ${cpu_usage%.*} -gt 80 ]; then
        log_warning "High CPU usage: ${cpu_usage}%"
    fi
    
    # Check load average
    local load_1min=$(echo ${load_avg} | cut -d',' -f1 | xargs)
    local cpu_count=$(nproc)
    
    if (( $(echo "${load_1min} > ${cpu_count}" | bc -l) )); then
        log_warning "Load average (${load_1min}) exceeds CPU count (${cpu_count})"
    fi
    
    return 0
}

check_external_services() {
    log_info "Checking external services..."
    
    local services=(
        "https://api.parking.com/health"
        "https://maps.googleapis.com/maps/api/geocode"
    )
    
    local failed=0
    
    for service in "${services[@]}"; do
        log_info "Checking: ${service}"
        
        if curl -f -s -o /dev/null --connect-timeout 5 --max-time 10 "${service}" 2>/dev/null; then
            log_success "Service OK: ${service}"
        else
            log_error "Service failed: ${service}"
            failed=$((failed + 1))
        fi
    done
    
    if [ ${failed} -gt 0 ]; then
        send_alert "External service failure" "${failed} external services are unreachable"
        return 1
    fi
    
    return 0
}

generate_health_report() {
    local report_file="${MAINTENANCE_LOG_DIR}/health_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "========================================="
        echo "Health Check Report"
        echo "========================================="
        echo "Date: $(date)"
        echo "Server: $(hostname)"
        echo ""
        
        echo "System Information:"
        echo "  OS: $(uname -a)"
        echo "  Uptime: $(uptime)"
        echo "  Users: $(who | wc -l)"
        echo ""
        
        echo "Resource Usage:"
        echo "  CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
        echo "  Memory: $(free -h | awk 'NR==2 {print $3"/"$2}')"
        echo "  Disk: $(df -h "${PROJECT_ROOT}" | awk 'NR==2 {print $3"/"$2}')"
        echo "  Load: $(uptime | awk -F'load average:' '{print $2}')"
        echo ""
        
        echo "Application:"
        echo "  Status: $(check_app_health > /dev/null && echo "Healthy" || echo "Unhealthy")"
        echo "  Port: ${APP_PORT}"
        echo "  Environment: ${ENVIRONMENT}"
        echo ""
        
        echo "Database:"
        echo "  Status: $(check_db_health > /dev/null && echo "Healthy" || echo "Unhealthy")"
        echo "  Connections: $(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM pg_stat_activity;" 2>/dev/null | xargs)"
        echo ""
        
        echo "Redis:"
        echo "  Status: $(check_redis_health > /dev/null && echo "Healthy" || echo "Unhealthy")"
        if command -v redis-cli &> /dev/null; then
            echo "  Memory: $(redis-cli INFO memory | grep "used_memory_human" | cut -d':' -f2 | xargs)"
            echo "  Clients: $(redis-cli INFO clients | grep "connected_clients" | cut -d':' -f2 | xargs)"
        fi
        
        echo "========================================="
    } > "${report_file}"
    
    log_info "Health report generated: ${report_file}"
}