# parking-management/backend/scripts/deployment/setup-environment.sh
# Environment setup script

#!/bin/bash

setup_environment() {
    local env=$1
    
    log_info "Setting up ${env} environment..."
    
    # Create environment directories
    mkdir -p "${DEPLOYMENT_ROOT}"
    mkdir -p "${RELEASES_DIR}"
    mkdir -p "${SHARED_DIR}"
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "${LOGS_DIR}"
    
    # Set permissions
    chmod 755 "${DEPLOYMENT_ROOT}"
    chown -R "${USER}:${GROUP:-${USER}}" "${DEPLOYMENT_ROOT}"
    
    # Create environment-specific configuration
    create_env_config "${env}"
    
    # Setup log rotation
    setup_log_rotation
    
    # Setup monitoring
    setup_monitoring
    
    # Setup backup cron
    setup_backup_cron
    
    log_success "Environment setup completed"
}

create_env_config() {
    local env=$1
    local config_file="${SHARED_DIR}/.env.${env}"
    
    if [ ! -f "${config_file}" ]; then
        cat > "${config_file}" << EOF
# ${env} environment configuration
NODE_ENV=${env}
APP_PORT=${APP_PORT}
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
JWT_SECRET=${JWT_SECRET}
LOG_LEVEL=${LOG_LEVEL}
EOF
        
        chmod 600 "${config_file}"
        log_info "Environment configuration created: ${config_file}"
    else
        log_info "Environment configuration already exists: ${config_file}"
    fi
}

setup_log_rotation() {
    local logrotate_config="/etc/logrotate.d/${APP_NAME}"
    
    cat > "${logrotate_config}" << EOF
${LOGS_DIR}/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 ${USER} ${GROUP:-${USER}}
    sharedscripts
    postrotate
        [ -f ${CURRENT_DIR}/.pid ] && kill -USR1 \$(cat ${CURRENT_DIR}/.pid) 2>/dev/null || true
    endscript
}
EOF
    
    log_info "Log rotation configured: ${logrotate_config}"
}

setup_monitoring() {
    # Setup Prometheus node exporter if needed
    if command -v node_exporter &> /dev/null; then
        log_info "Node exporter found"
    fi
    
    # Create metrics directory
    mkdir -p "${SHARED_DIR}/metrics"
}

setup_backup_cron() {
    local cron_file="/etc/cron.d/${APP_NAME}-backup"
    
    cat > "${cron_file}" << EOF
# Daily backup at 2 AM
0 2 * * * ${USER} ${BACKEND_DIR}/scripts/db/backup.sh >> ${LOGS_DIR}/backup.log 2>&1

# Weekly cleanup at 3 AM on Sunday
0 3 * * 0 ${USER} find ${BACKUP_DIR} -name "*.sql.gz" -mtime +30 -delete >> ${LOGS_DIR}/cleanup.log 2>&1
EOF
    
    log_info "Backup cron configured: ${cron_file}"
}