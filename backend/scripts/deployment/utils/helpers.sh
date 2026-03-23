# parking-management/backend/scripts/deployment/utils/helpers.sh
# Helper utilities

acquire_deployment_lock() {
    local lock_file="/tmp/${APP_NAME}.deploy.lock"
    local pid=$$
    
    if [ -f "${lock_file}" ]; then
        local old_pid=$(cat "${lock_file}")
        if kill -0 "${old_pid}" 2>/dev/null; then
            log_error "Deployment already in progress (PID: ${old_pid})"
            return 1
        else
            log_warning "Removing stale lock file"
            rm -f "${lock_file}"
        fi
    fi
    
    echo "${pid}" > "${lock_file}"
    log_info "Deployment lock acquired (PID: ${pid})"
    return 0
}

release_deployment_lock() {
    local lock_file="/tmp/${APP_NAME}.deploy.lock"
    local pid=$$
    
    if [ -f "${lock_file}" ]; then
        local lock_pid=$(cat "${lock_file}")
        if [ "${lock_pid}" = "${pid}" ]; then
            rm -f "${lock_file}"
            log_info "Deployment lock released"
        fi
    fi
}

log_deployment_info() {
    local info_file="${SHARED_DIR}/deployment_info.json"
    
    cat > "${info_file}" << EOF
{
    "app_name": "${APP_NAME}",
    "version": "${DEPLOYMENT_TAG}",
    "environment": "${ENVIRONMENT}",
    "deployed_at": "$(date -Iseconds)",
    "deployed_by": "${USER}",
    "mode": "${DEPLOYMENT_MODE}",
    "commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
}
EOF
    
    log_info "Deployment info saved to ${info_file}"
}

update_deployment_metrics() {
    # Update Prometheus metrics if available
    if [ -f "${SHARED_DIR}/metrics.prom" ]; then
        echo "# HELP deployment_timestamp_seconds Last deployment timestamp" >> "${SHARED_DIR}/metrics.prom"
        echo "# TYPE deployment_timestamp_seconds gauge" >> "${SHARED_DIR}/metrics.prom"
        echo "deployment_timestamp_seconds{env=\"${ENVIRONMENT}\"} $(date +%s)" >> "${SHARED_DIR}/metrics.prom"
    fi
}

send_deployment_notification() {
    local status=$1
    local duration=$2
    
    if [ "${DEPLOYMENT_NOTIFICATIONS_ENABLED}" != "true" ]; then
        return 0
    fi
    
    local message="Deployment of ${APP_NAME} to ${ENVIRONMENT} completed with status: ${status} in ${duration}s"
    local color="good"
    
    if [ "${status}" != "success" ]; then
        color="danger"
    fi
    
    # Send to Slack if configured
    if [ -n "${SLACK_WEBHOOK_URL}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"text\": \"${message}\",
                \"attachments\": [{
                    \"color\": \"${color}\",
                    \"fields\": [
                        {\"title\": \"Application\", \"value\": \"${APP_NAME}\", \"short\": true},
                        {\"title\": \"Environment\", \"value\": \"${ENVIRONMENT}\", \"short\": true},
                        {\"title\": \"Version\", \"value\": \"${DEPLOYMENT_TAG}\", \"short\": true},
                        {\"title\": \"Duration\", \"value\": \"${duration}s\", \"short\": true}
                    ]
                }]
            }" \
            "${SLACK_WEBHOOK_URL}" &> /dev/null || true
    fi
    
    # Send to Microsoft Teams if configured
    if [ -n "${TEAMS_WEBHOOK_URL}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"title\": \"Deployment ${status}\",
                \"text\": \"${message}\",
                \"sections\": [{
                    \"facts\": [
                        {\"name\": \"Application\", \"value\": \"${APP_NAME}\"},
                        {\"name\": \"Environment\", \"value\": \"${ENVIRONMENT}\"},
                        {\"name\": \"Version\", \"value\": \"${DEPLOYMENT_TAG}\"},
                        {\"name\": \"Duration\", \"value\": \"${duration}s\"}
                    ]
                }]
            }" \
            "${TEAMS_WEBHOOK_URL}" &> /dev/null || true
    fi
}

cleanup_old_deployments() {
    log_info "Cleaning up old deployments (keeping last ${MAX_RELEASES_TO_KEEP})"
    
    cd "${RELEASES_DIR}" || return 1
    
    local releases=$(ls -1d * 2>/dev/null | sort -r | tail -n +$((MAX_RELEASES_TO_KEEP + 1)))
    for release in ${releases}; do
        if [ -d "${release}" ] && [ "${release}" != "$(basename "${CURRENT_DIR}")" ]; then
            log_info "Removing old release: ${release}"
            rm -rf "${release}"
        fi
    done
    
    log_success "Cleanup completed"
}