# parking-management/backend/scripts/maintenance/utils/helpers.sh
# Helper utilities for maintenance

check_database_connection() {
    if command -v psql &> /dev/null; then
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" \
            -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1" &> /dev/null
        return $?
    fi
    return 0
}

is_application_running() {
    if command -v pm2 &> /dev/null; then
        pm2 list | grep -q "${APP_NAME}"
        return $?
    elif systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        return 0
    else
        # Check if process is running
        pgrep -f "node.*${APP_NAME}" &> /dev/null
        return $?
    fi
}

get_database_size() {
    local sql="SELECT pg_size_pretty(pg_database_size(current_database()))"
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "${sql}" 2>/dev/null | xargs
}

get_table_count() {
    local sql="SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "${sql}" 2>/dev/null | xargs
}

format_bytes() {
    local bytes=$1
    if [ ${bytes} -lt 1024 ]; then
        echo "${bytes}B"
    elif [ ${bytes} -lt 1048576 ]; then
        echo "$((bytes / 1024))KB"
    elif [ ${bytes} -lt 1073741824 ]; then
        echo "$((bytes / 1048576))MB"
    else
        echo "$((bytes / 1073741824))GB"
    fi
}

get_timestamp() {
    date +"%Y%m%d_%H%M%S"
}