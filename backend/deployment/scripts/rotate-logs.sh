#!/bin/bash

# Log Rotation Script

set -e

LOG_DIR="../logs"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d)

# Rotate nginx logs
rotate_nginx_logs() {
    if [ -d "${LOG_DIR}/nginx" ]; then
        cd "${LOG_DIR}/nginx"
        
        # Compress old logs
        for log in *.log; do
            if [ -f "${log}" ]; then
                gzip -c "${log}" > "${log}.${DATE}.gz"
                > "${log}"  # Truncate original file
            fi
        done
        
        # Remove old compressed logs
        find . -name "*.gz" -mtime +${RETENTION_DAYS} -delete
    fi
}

# Rotate application logs
rotate_app_logs() {
    if [ -d "${LOG_DIR}/app" ]; then
        cd "${LOG_DIR}/app"
        
        # Rotate application logs
        for log in *.log; do
            if [ -f "${log}" ] && [ -s "${log}" ]; then
                mv "${log}" "${log}.${DATE}"
                touch "${log}"
            fi
        done
        
        # Compress rotated logs
        find . -name "*.log.*" -not -name "*.gz" -exec gzip {} \;
        
        # Remove old logs
        find . -name "*.gz" -mtime +${RETENTION_DAYS} -delete
    fi
}

# Rotate database logs
rotate_db_logs() {
    if [ -d "${LOG_DIR}/db" ]; then
        cd "${LOG_DIR}/db"
        
        # Rotate PostgreSQL logs if using custom logging
        find . -name "postgresql-*.log" -mtime +${RETENTION_DAYS} -delete
    fi
}

# Main rotation function
main() {
    echo "Starting log rotation at $(date)"
    
    rotate_nginx_logs
    rotate_app_logs
    rotate_db_logs
    
    # Reload nginx to apply new log files
    if command -v docker &> /dev/null; then
        docker exec parking-nginx nginx -s reopen 2>/dev/null || true
    fi
    
    echo "Log rotation completed at $(date)"
}

# Run main function
main