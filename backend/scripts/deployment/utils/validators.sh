# parking-management/backend/scripts/deployment/utils/validators.sh
# Validation utilities

validate_environment() {
    log_info "Validating deployment environment..."
    
    # Check required commands
    local required_commands=("node" "npm" "psql" "git")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "${cmd}" &> /dev/null; then
            log_error "Required command not found: ${cmd}"
            return 1
        fi
    done
    
    # Check Node.js version
    local node_version=$(node --version | cut -d'v' -f2)
    local required_node_version="14.0.0"
    if [ "$(printf '%s\n' "${required_node_version}" "${node_version}" | sort -V | head -n1)" != "${required_node_version}" ]; then
        log_error "Node.js version ${node_version} is less than required ${required_node_version}"
        return 1
    fi
    
    # Check npm version
    local npm_version=$(npm --version)
    log_info "npm version: ${npm_version}"
    
    # Check disk space (need at least 1GB free)
    local available_space_kb=$(df . | awk 'NR==2 {print $4}')
    if [ "${available_space_kb}" -lt 1048576 ]; then
        log_error "Insufficient disk space: ${available_space_kb}KB available (need 1GB)"
        return 1
    fi
    
    # Check memory (need at least 512MB free)
    local available_memory_kb=$(free | awk 'NR==2 {print $7}')
    if [ "${available_memory_kb}" -lt 524288 ]; then
        log_warning "Low memory: ${available_memory_kb}KB available"
    fi
    
    return 0
}

validate_required_env_vars() {
    local required_vars=(
        "DB_HOST"
        "DB_NAME"
        "DB_USER"
        "JWT_SECRET"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("${var}")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        return 1
    fi
    
    return 0
}

check_database_connection() {
    if command -v psql &> /dev/null; then
        PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1" &> /dev/null
        return $?
    fi
    return 0
}

check_port_available() {
    local port=$1
    if command -v netstat &> /dev/null; then
        netstat -tuln | grep -q ":${port} "
        return $((! $?))
    elif command -v ss &> /dev/null; then
        ss -tuln | grep -q ":${port} "
        return $((! $?))
    else
        return 0
    fi
}

is_application_running() {
    if command -v pm2 &> /dev/null; then
        pm2 list | grep -q "${APP_NAME}"
        return $?
    elif systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}