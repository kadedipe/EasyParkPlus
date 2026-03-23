# parking-management/backend/scripts/deployment/rollback/rollback.sh
# Rollback functionality

rollback_deployment() {
    log_warning "Initiating deployment rollback..."
    
    # Get previous release
    local previous_release=$(get_previous_release)
    
    if [ -z "${previous_release}" ]; then
        log_error "No previous release found to rollback to"
        return 1
    fi
    
    log_info "Rolling back to release: ${previous_release}"
    
    # Create backup of current release
    local current_release=$(readlink "${CURRENT_DIR}")
    backup_current_release "${current_release}"
    
    # Rollback based on deployment mode
    case "${DEPLOYMENT_MODE}" in
        full|rolling)
            rollback_full "${previous_release}"
            ;;
        blue-green)
            rollback_blue_green
            ;;
        canary)
            rollback_canary
            ;;
        *)
            rollback_full "${previous_release}"
            ;;
    esac
    
    # Verify rollback
    if ! verify_rollback; then
        log_error "Rollback verification failed"
        return 1
    fi
    
    # Restart application
    restart_application
    
    # Wait for application to stabilize
    sleep "${HEALTH_CHECK_INTERVAL}"
    
    # Health check
    if ! check_application_health; then
        log_error "Application health check failed after rollback"
        return 1
    fi
    
    log_success "Rollback completed successfully"
    return 0
}

get_previous_release() {
    cd "${RELEASES_DIR}" || return 1
    
    local current_release=$(basename "$(readlink "${CURRENT_DIR}")")
    local previous_release=$(ls -1d * 2>/dev/null | grep -v "${current_release}" | sort -r | head -n1)
    
    echo "${previous_release}"
}

backup_current_release() {
    local current_release=$1
    
    if [ -n "${current_release}" ] && [ -d "${RELEASES_DIR}/${current_release}" ]; then
        local backup_dir="${BACKUP_DIR}/releases"
        mkdir -p "${backup_dir}"
        
        cp -r "${RELEASES_DIR}/${current_release}" "${backup_dir}/${current_release}_$(date +%Y%m%d_%H%M%S)"
        log_info "Current release backed up"
    fi
}

rollback_full() {
    local previous_release=$1
    
    log_info "Rolling back to previous release: ${previous_release}"
    
    # Update symlink
    update_current_symlink "${RELEASES_DIR}/${previous_release}"
    
    log_success "Full rollback completed"
}

rollback_blue_green() {
    log_info "Rolling back blue-green deployment"
    
    local active_color=$(get_active_color)
    local previous_color=""
    
    if [ "${active_color}" = "blue" ]; then
        previous_color="green"
    else
        previous_color="blue"
    fi
    
    # Switch traffic back to previous environment
    switch_traffic "${previous_color}"
    
    # Stop current environment
    stop_environment "${active_color}"
    
    # Update active color
    set_active_color "${previous_color}"
    
    log_success "Blue-green rollback completed. Active: ${previous_color}"
}

rollback_canary() {
    log_info "Rolling back canary deployment"
    
    # Remove canary traffic
    remove_canary_traffic
    
    # Ensure main application is running
    start_application
    
    log_success "Canary rollback completed"
}

verify_rollback() {
    log_info "Verifying rollback..."
    
    # Check if application is running
    if ! is_application_running; then
        log_error "Application not running after rollback"
        return 1
    fi
    
    # Check version
    local current_release=$(basename "$(readlink "${CURRENT_DIR}")")
    log_info "Current release after rollback: ${current_release}"
    
    # Run health checks
    if ! check_application_health; then
        log_error "Health check failed after rollback"
        return 1
    fi
    
    return 0
}

check_application_health() {
    local max_attempts=10
    local attempt=1
    
    while [ ${attempt} -le ${max_attempts} ]; do
        if curl -f -s "http://localhost:${APP_PORT}${HEALTH_ENDPOINT}" &> /dev/null; then
            log_success "Application health check passed"
            return 0
        fi
        
        log_info "Health check attempt ${attempt}/${max_attempts} failed"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    log_error "Application health check failed after ${max_attempts} attempts"
    return 1
}

restart_application() {
    log_info "Restarting application..."
    
    if command -v pm2 &> /dev/null; then
        pm2 restart "${APP_NAME}" || true
    elif systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        systemctl restart "${SERVICE_NAME}"
    else
        # Kill and restart
        pkill -f "node.*${APP_NAME}" || true
        sleep 2
        start_application
    fi
    
    log_success "Application restarted"
}