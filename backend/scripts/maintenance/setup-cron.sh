# parking-management/backend/scripts/maintenance/setup-cron.sh
# Setup cron jobs for maintenance

#!/bin/bash

setup_maintenance_cron() {
    local cron_file="/etc/cron.d/${APP_NAME}-maintenance"
    
    cat > "${cron_file}" << EOF
# Daily maintenance at 2 AM
0 2 * * * ${USER} ${SCRIPT_DIR}/maintenance.sh --type all --mode scheduled >> ${MAINTENANCE_LOG_DIR}/cron.log 2>&1

# Hourly cache cleanup
0 * * * * ${USER} ${SCRIPT_DIR}/maintenance.sh --type cache --mode auto >> ${MAINTENANCE_LOG_DIR}/cache.log 2>&1

# Daily database optimization at 3 AM
0 3 * * * ${USER} ${SCRIPT_DIR}/maintenance.sh --type database --mode scheduled >> ${MAINTENANCE_LOG_DIR}/database.log 2>&1

# Weekly backup verification at 4 AM on Sunday
0 4 * * 0 ${USER} ${SCRIPT_DIR}/maintenance.sh --type backup --mode scheduled >> ${MAINTENANCE_LOG_DIR}/backup.log 2>&1

# Every 6 hours log rotation
0 */6 * * * ${USER} ${SCRIPT_DIR}/maintenance.sh --type logs --mode auto >> ${MAINTENANCE_LOG_DIR}/logs.log 2>&1

# Daily cleanup at 5 AM
0 5 * * * ${USER} ${SCRIPT_DIR}/maintenance.sh --type cleanup --mode scheduled >> ${MAINTENANCE_LOG_DIR}/cleanup.log 2>&1

# Health check every 5 minutes
*/5 * * * * ${USER} ${SCRIPT_DIR}/maintenance.sh --type health --mode auto >> ${MAINTENANCE_LOG_DIR}/health.log 2>&1
EOF
    
    chmod 644 "${cron_file}"
    log_info "Cron jobs configured: ${cron_file}"
    
    # Reload cron
    if command -v systemctl &> /dev/null; then
        systemctl reload cron
    else
        service cron reload
    fi
}

# Run setup
setup_maintenance_cron