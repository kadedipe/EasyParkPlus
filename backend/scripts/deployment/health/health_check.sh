# parking-management/backend/scripts/deployment/health/health_check.sh
# Health check functionality

verify_deployment() {
    log_info "Verifying deployment..."
    
    local max_attempts=$((HEALTH_CHECK_TIMEOUT / HEALTH_CHECK_INTERVAL))
    local attempt=1
    local healthy=false
    
    while [ ${attempt} -le ${max_attempts} ]; do
        log_info "Health check attempt ${attempt}/${max_attempts}"
        
        if check_health_endpoint; then
            healthy=true
            break
        fi
        
        if check_database_health; then
            log_warning "Database health check failed"
        fi
        
        if check_redis_health; then
            log_warning "Redis health check failed"
        fi
        
        sleep "${HEALTH_CHECK_INTERVAL}"
        attempt=$((attempt + 1))
    done
    
    if [ "${healthy}" = true ]; then
        log_success "Deployment verified successfully"
        return 0
    else
        log_error "Deployment verification failed after ${max_attempts} attempts"
        return 1
    fi
}

check_health_endpoint() {
    local health_url="http://localhost:${APP_PORT}${HEALTH_ENDPOINT}"
    
    local response=$(curl -f -s -w "\n%{http_code}" "${health_url}" 2>/dev/null)
    local http_code=$(echo "${response}" | tail -n1)
    local body=$(echo "${response}" | head -n-1)
    
    if [ "${http_code}" = "200" ]; then
        # Check if health status is 'healthy' or 'ok'
        if echo "${body}" | grep -qE '"status":"(healthy|ok)"'; then
            log_success "Health endpoint OK"
            return 0
        else
            log_warning "Health endpoint returned unhealthy status"
            return 1
        fi
    else
        log_warning "Health endpoint returned HTTP ${http_code}"
        return 1
    fi
}

check_database_health() {
    if command -v psql &> /dev/null; then
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" \
            -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1" &> /dev/null
        return $?
    fi
    return 0
}

check_redis_health() {
    if command -v redis-cli &> /dev/null; then
        redis-cli ping &> /dev/null
        return $?
    fi
    return 0
}

check_metrics_endpoint() {
    local metrics_url="http://localhost:${APP_PORT}${METRICS_ENDPOINT}"
    
    if curl -f -s "${metrics_url}" &> /dev/null; then
        log_success "Metrics endpoint OK"
        return 0
    else
        log_warning "Metrics endpoint unavailable"
        return 1
    fi
}

run_migrations() {
    log_info "Running database migrations..."
    
    if [ -f "${BACKEND_DIR}/scripts/db/migrate.sh" ]; then
        cd "${BACKEND_DIR}" || exit 1
        
        if [ "${DRY_RUN}" = "true" ]; then
            log_info "[DRY RUN] Would run migrations"
            return 0
        fi
        
        if ./scripts/db/migrate.sh up; then
            log_success "Migrations completed successfully"
            return 0
        else
            log_error "Migrations failed"
            return 1
        fi
    else
        log_warning "Migration script not found"
        return 0
    fi
}