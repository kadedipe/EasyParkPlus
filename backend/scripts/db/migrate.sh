#!/bin/bash
# parking-management/backend/scripts/db/migrate.sh
# Database migration script for Parking Management System
# Version: 1.0

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f "../../.env" ]; then
    source "../../.env"
elif [ -f "../.env" ]; then
    source "../.env"
elif [ -f ".env" ]; then
    source ".env"
fi

# Configuration with defaults
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-parking_management}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-./migrations}"
MIGRATIONS_TABLE="${MIGRATIONS_TABLE:-schema_migrations}"
ENVIRONMENT="${NODE_ENV:-development}"
MIGRATION_COMMAND="${1:-up}" # up, down, create, status, rollback, redo, version
MIGRATION_VERSION="${2:-}" # Specific version for down/rollback
MIGRATION_NAME="${2:-}" # Name for create command
DRY_RUN="${DRY_RUN:-false}"
FORCE="${FORCE:-false}"
BACKUP_BEFORE_MIGRATE="${BACKUP_BEFORE_MIGRATE:-true}"
LOCK_TIMEOUT="${LOCK_TIMEOUT:-30}" # seconds

# Create migrations directory if it doesn't exist
mkdir -p "${MIGRATIONS_DIR}"

# Timestamp for logs
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="./migration_logs/migrate_${TIMESTAMP}.log"
mkdir -p "./migration_logs"

# Logging function
log() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    case $level in
        "INFO")
            echo -e "${GREEN}[${timestamp}] INFO: ${message}${NC}" | tee -a "${LOG_FILE}"
            ;;
        "WARNING")
            echo -e "${YELLOW}[${timestamp}] WARNING: ${message}${NC}" | tee -a "${LOG_FILE}"
            ;;
        "ERROR")
            echo -e "${RED}[${timestamp}] ERROR: ${message}${NC}" | tee -a "${LOG_FILE}"
            ;;
        "DEBUG")
            echo -e "${CYAN}[${timestamp}] DEBUG: ${message}${NC}" | tee -a "${LOG_FILE}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[${timestamp}] ✅ SUCCESS: ${message}${NC}" | tee -a "${LOG_FILE}"
            ;;
        *)
            echo "[${timestamp}] ${message}" | tee -a "${LOG_FILE}"
            ;;
    esac
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 <command> [options]

Database migration script for Parking Management System

COMMANDS:
    up [VERSION]        Migrate to latest version or specified version
    down [VERSION]      Rollback to specified version (default: -1)
    create <name>       Create a new migration file
    status              Show migration status
    rollback            Rollback last migration
    redo [VERSION]      Rollback and re-apply migration
    version             Show current migration version
    reset               Reset database (dangerous!)
    seed                Run database seeds

OPTIONS:
    --dry-run           Show what would be done without executing
    --force             Force migration even if it might be destructive
    --no-backup         Skip database backup before migration
    -h, --help          Show this help message

EXAMPLES:
    # Run all pending migrations
    $0 up
    
    # Migrate to specific version
    $0 up 20240101120000
    
    # Create new migration
    $0 create add_vehicle_type_column
    
    # Check migration status
    $0 status
    
    # Rollback last migration
    $0 rollback
    
    # Rollback to specific version
    $0 down 20240101120000
    
    # Redo last migration
    $0 redo
    
    # Show current version
    $0 version

EOF
}

# Parse command line arguments
parse_args() {
    local cmd="$1"
    
    case $cmd in
        up|down|create|status|rollback|redo|version|reset|seed)
            MIGRATION_COMMAND="$cmd"
            if [ "$cmd" = "create" ]; then
                MIGRATION_NAME="${2:-}"
                if [ -z "${MIGRATION_NAME}" ]; then
                    log "ERROR" "Migration name required for create command"
                    show_usage
                    exit 1
                fi
            elif [ "$cmd" = "up" ] || [ "$cmd" = "down" ] || [ "$cmd" = "redo" ]; then
                MIGRATION_VERSION="${2:-}"
            fi
            ;;
        --dry-run)
            DRY_RUN="true"
            MIGRATION_COMMAND="${2:-up}"
            ;;
        --help|-h)
            show_usage
            exit 0
            ;;
        *)
            log "ERROR" "Unknown command: $cmd"
            show_usage
            exit 1
            ;;
    esac
}

# Check if required tools are installed
check_dependencies() {
    local missing_deps=()
    
    if ! command -v psql &> /dev/null; then
        missing_deps+=("postgresql-client")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log "ERROR" "Missing dependencies: ${missing_deps[*]}"
        log "INFO" "Please install them using: sudo apt-get install ${missing_deps[*]}"
        exit 1
    fi
}

# Set PostgreSQL password
set_postgres_password() {
    if [ -n "${DB_PASSWORD}" ]; then
        export PGPASSWORD="${DB_PASSWORD}"
    else
        log "WARNING" "DB_PASSWORD not set in environment"
    fi
}

# Test database connection
test_connection() {
    log "INFO" "Testing database connection to ${DB_HOST}:${DB_PORT}/${DB_NAME}"
    
    if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" &> /dev/null; then
        log "SUCCESS" "Database connection successful"
        return 0
    else
        log "ERROR" "Cannot connect to database"
        return 1
    fi
}

# Create migrations table if it doesn't exist
create_migrations_table() {
    log "INFO" "Creating migrations table if not exists"
    
    local sql="
    CREATE TABLE IF NOT EXISTS ${MIGRATIONS_TABLE} (
        id SERIAL PRIMARY KEY,
        version VARCHAR(14) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        executed_by VARCHAR(100) DEFAULT CURRENT_USER,
        duration_ms INTEGER,
        checksum VARCHAR(64),
        success BOOLEAN DEFAULT true,
        rollback_version VARCHAR(14)
    );
    
    CREATE INDEX IF NOT EXISTS idx_migrations_version 
    ON ${MIGRATIONS_TABLE}(version);
    
    CREATE INDEX IF NOT EXISTS idx_migrations_applied_at 
    ON ${MIGRATIONS_TABLE}(applied_at);
    "
    
    if [ "${DRY_RUN}" = "true" ]; then
        log "INFO" "[DRY RUN] Would create migrations table"
        return 0
    fi
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}" 2>&1 | tee -a "${LOG_FILE}"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "SUCCESS" "Migrations table created/verified"
        return 0
    else
        log "ERROR" "Failed to create migrations table"
        return 1
    fi
}

# Get current migration version
get_current_version() {
    local version=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
        "SELECT version FROM ${MIGRATIONS_TABLE} WHERE success = true ORDER BY applied_at DESC LIMIT 1" 2>/dev/null | xargs)
    
    if [ -z "${version}" ]; then
        echo "0"
    else
        echo "${version}"
    fi
}

# Get all applied migrations
get_applied_migrations() {
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
        "SELECT version, name, applied_at FROM ${MIGRATIONS_TABLE} WHERE success = true ORDER BY version" 2>/dev/null
}

# Get pending migrations
get_pending_migrations() {
    local applied_versions=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
        "SELECT version FROM ${MIGRATIONS_TABLE} WHERE success = true" 2>/dev/null | xargs | tr ' ' '|')
    
    for file in $(ls -1 "${MIGRATIONS_DIR}"/*.up.sql 2>/dev/null | sort); do
        local version=$(basename "$file" | cut -d'_' -f1)
        local name=$(basename "$file" | sed 's/^[0-9]*_//' | sed 's/\.up\.sql$//')
        
        if [[ ! " ${applied_versions} " =~ " ${version} " ]]; then
            echo "${version}|${name}|${file}"
        fi
    done
}

# Generate checksum for migration file
generate_checksum() {
    local file=$1
    if [ -f "${file}" ]; then
        sha256sum "${file}" | cut -d' ' -f1
    else
        echo ""
    fi
}

# Execute migration with transaction
execute_migration() {
    local version=$1
    local name=$2
    local direction=$3 # up or down
    local migration_file=$4
    
    log "INFO" "Executing ${direction} migration: ${version}_${name}"
    
    local start_time=$(date +%s%N)
    
    if [ "${DRY_RUN}" = "true" ]; then
        log "INFO" "[DRY RUN] Would execute: psql -f ${migration_file}"
        return 0
    fi
    
    # Execute migration within transaction
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -v ON_ERROR_STOP=1 \
        --single-transaction \
        -f "${migration_file}" 2>&1 | tee -a "${LOG_FILE}"
    
    local exit_code=${PIPESTATUS[0]}
    local end_time=$(date +%s%N)
    local duration=$((($end_time - $start_time) / 1000000))
    
    if [ ${exit_code} -eq 0 ]; then
        log "SUCCESS" "Migration executed successfully (${duration}ms)"
        
        if [ "${direction}" = "up" ]; then
            # Record successful migration
            local checksum=$(generate_checksum "${migration_file}")
            local sql="
            INSERT INTO ${MIGRATIONS_TABLE} (version, name, duration_ms, checksum, success)
            VALUES ('${version}', '${name}', ${duration}, '${checksum}', true);
            "
            psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}" 2>&1 | tee -a "${LOG_FILE}"
        elif [ "${direction}" = "down" ]; then
            # Record rollback
            local sql="
            UPDATE ${MIGRATIONS_TABLE} 
            SET success = false, rollback_version = '${version}'
            WHERE version = '${version}' AND success = true;
            "
            psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}" 2>&1 | tee -a "${LOG_FILE}"
        fi
        
        return 0
    else
        log "ERROR" "Migration failed (${duration}ms)"
        return 1
    fi
}

# Run backup before migration
backup_database() {
    if [ "${BACKUP_BEFORE_MIGRATE}" != "true" ]; then
        log "INFO" "Skipping backup (BACKUP_BEFORE_MIGRATE=false)"
        return 0
    fi
    
    log "INFO" "Creating database backup before migration"
    
    local backup_file="./backups/pre_migration_${TIMESTAMP}.sql.gz"
    mkdir -p "./backups"
    
    if [ "${DRY_RUN}" = "true" ]; then
        log "INFO" "[DRY RUN] Would backup database to ${backup_file}"
        return 0
    fi
    
    pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        --format=plain \
        --clean \
        --no-owner \
        --no-privileges | gzip -9 > "${backup_file}"
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log "SUCCESS" "Database backup created: ${backup_file}"
        return 0
    else
        log "WARNING" "Database backup failed, continuing without backup"
        return 0
    fi
}

# Acquire migration lock
acquire_lock() {
    local lock_table="migration_locks"
    local lock_id=1
    
    local sql="
    CREATE TABLE IF NOT EXISTS ${lock_table} (
        id INTEGER PRIMARY KEY,
        locked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        locked_by VARCHAR(100) DEFAULT CURRENT_USER,
        lock_until TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP + INTERVAL '${LOCK_TIMEOUT} seconds')
    );
    
    DELETE FROM ${lock_table} WHERE lock_until < CURRENT_TIMESTAMP;
    
    INSERT INTO ${lock_table} (id)
    SELECT ${lock_id}
    WHERE NOT EXISTS (SELECT 1 FROM ${lock_table} WHERE id = ${lock_id});
    
    UPDATE ${lock_table} 
    SET locked_at = CURRENT_TIMESTAMP, 
        locked_by = CURRENT_USER,
        lock_until = CURRENT_TIMESTAMP + INTERVAL '${LOCK_TIMEOUT} seconds'
    WHERE id = ${lock_id} AND lock_until < CURRENT_TIMESTAMP;
    
    SELECT COUNT(*) FROM ${lock_table} WHERE id = ${lock_id} AND lock_until >= CURRENT_TIMESTAMP;
    "
    
    local acquired=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "${sql}" 2>/dev/null | xargs)
    
    if [ "${acquired}" = "1" ]; then
        log "SUCCESS" "Migration lock acquired"
        return 0
    else
        log "ERROR" "Failed to acquire migration lock. Another migration may be running."
        return 1
    fi
}

# Release migration lock
release_lock() {
    local lock_table="migration_locks"
    local sql="DELETE FROM ${lock_table} WHERE id = 1;"
    
    if [ "${DRY_RUN}" != "true" ]; then
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}" 2>&1 | tee -a "${LOG_FILE}" > /dev/null
    fi
    
    log "INFO" "Migration lock released"
}

# Run all pending migrations
migrate_up() {
    local target_version="${MIGRATION_VERSION}"
    
    log "INFO" "Starting migration up to ${target_version:-latest}"
    
    # Get current version
    local current_version=$(get_current_version)
    log "INFO" "Current version: ${current_version}"
    
    # Get pending migrations
    local pending_migrations=$(get_pending_migrations)
    
    if [ -z "${pending_migrations}" ]; then
        log "INFO" "No pending migrations"
        return 0
    fi
    
    # Process migrations in order
    echo "${pending_migrations}" | while IFS='|' read -r version name file; do
        # Check if we've reached target version
        if [ -n "${target_version}" ] && [ "${version}" -gt "${target_version}" ]; then
            log "INFO" "Stopping at target version ${target_version}"
            break
        fi
        
        # Execute migration
        if execute_migration "${version}" "${name}" "up" "${file}"; then
            log "SUCCESS" "Applied migration: ${version}_${name}"
        else
            log "ERROR" "Failed to apply migration: ${version}_${name}"
            return 1
        fi
    done
    
    local new_version=$(get_current_version)
    log "SUCCESS" "Migration completed. New version: ${new_version}"
    return 0
}

# Rollback migrations
migrate_down() {
    local target_version="${MIGRATION_VERSION}"
    
    log "INFO" "Starting rollback to ${target_version:-previous}"
    
    local current_version=$(get_current_version)
    log "INFO" "Current version: ${current_version}"
    
    if [ "${current_version}" = "0" ]; then
        log "INFO" "No migrations to rollback"
        return 0
    fi
    
    # Get applied migrations in reverse order
    local applied_migrations=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
        "SELECT version, name FROM ${MIGRATIONS_TABLE} WHERE success = true ORDER BY version DESC" 2>/dev/null)
    
    local rolled_back=false
    
    echo "${applied_migrations}" | while IFS='|' read -r version name; do
        # Check if we've reached target version
        if [ -n "${target_version}" ] && [ "${version}" -le "${target_version}" ]; then
            log "INFO" "Stopping at target version ${target_version}"
            break
        fi
        
        # Find corresponding down migration
        local down_file="${MIGRATIONS_DIR}/${version}_${name}.down.sql"
        
        if [ ! -f "${down_file}" ]; then
            log "ERROR" "Down migration not found: ${down_file}"
            log "INFO" "Please create rollback script for version ${version}"
            return 1
        fi
        
        # Execute rollback
        if execute_migration "${version}" "${name}" "down" "${down_file}"; then
            log "SUCCESS" "Rolled back migration: ${version}_${name}"
            rolled_back=true
        else
            log "ERROR" "Failed to rollback migration: ${version}_${name}"
            return 1
        fi
    done
    
    if [ "${rolled_back}" = true ]; then
        local new_version=$(get_current_version)
        log "SUCCESS" "Rollback completed. New version: ${new_version}"
    else
        log "INFO" "No migrations rolled back"
    fi
    
    return 0
}

# Create new migration
create_migration() {
    local name=$1
    local timestamp=$(date +"%Y%m%d%H%M%S")
    local filename="${timestamp}_${name}"
    local up_file="${MIGRATIONS_DIR}/${filename}.up.sql"
    local down_file="${MIGRATIONS_DIR}/${filename}.down.sql"
    
    log "INFO" "Creating migration: ${filename}"
    
    # Create up migration file
    cat > "${up_file}" << EOF
-- Migration: ${name}
-- Version: ${timestamp}
-- Direction: UP
-- Description: ${name}
-- Created: $(date)

BEGIN;

-- TODO: Add your migration SQL here
-- Example: 
-- CREATE TABLE IF NOT EXISTS new_table (
--     id SERIAL PRIMARY KEY,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- ALTER TABLE existing_table ADD COLUMN new_column VARCHAR(255);

COMMIT;

-- Rollback SQL is available in the corresponding .down.sql file
EOF
    
    # Create down migration file
    cat > "${down_file}" << EOF
-- Migration: ${name}
-- Version: ${timestamp}
-- Direction: DOWN
-- Description: Rollback ${name}
-- Created: $(date)

BEGIN;

-- TODO: Add rollback SQL here
-- Example:
-- DROP TABLE IF EXISTS new_table;

-- ALTER TABLE existing_table DROP COLUMN new_column;

COMMIT;
EOF
    
    log "SUCCESS" "Migration files created:"
    log "SUCCESS" "  - ${up_file}"
    log "SUCCESS" "  - ${down_file}"
    
    # Make files readable
    chmod 644 "${up_file}" "${down_file}"
    
    return 0
}

# Show migration status
show_status() {
    log "INFO" "Migration Status for ${DB_NAME} on ${DB_HOST}"
    echo "========================================"
    
    local current_version=$(get_current_version)
    echo "Current Version: ${current_version}"
    echo ""
    
    echo "Applied Migrations:"
    echo "------------------"
    local applied=$(get_applied_migrations)
    if [ -z "${applied}" ]; then
        echo "  No migrations applied yet"
    else
        echo "${applied}" | while IFS='|' read -r version name applied_at; do
            printf "  %-14s %-50s %s\n" "${version}" "${name}" "${applied_at}"
        done
    fi
    
    echo ""
    echo "Pending Migrations:"
    echo "------------------"
    local pending=$(get_pending_migrations)
    if [ -z "${pending}" ]; then
        echo "  No pending migrations"
    else
        echo "${pending}" | while IFS='|' read -r version name file; do
            printf "  %-14s %-50s\n" "${version}" "${name}"
        done
    fi
    
    echo "========================================"
}

# Reset database (dangerous!)
reset_database() {
    if [ "${FORCE}" != "true" ] && [ "${DRY_RUN}" != "true" ]; then
        log "WARNING" "This will DROP and recreate the database!"
        read -p "Are you sure? Type 'yes' to continue: " confirmation
        if [ "${confirmation}" != "yes" ]; then
            log "INFO" "Reset cancelled"
            return 0
        fi
    fi
    
    log "WARNING" "Resetting database..."
    
    if [ "${DRY_RUN}" = "true" ]; then
        log "INFO" "[DRY RUN] Would drop and recreate database"
        return 0
    fi
    
    # Drop and recreate database
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME}" 2>&1 | tee -a "${LOG_FILE}"
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}" 2>&1 | tee -a "${LOG_FILE}"
    
    # Recreate migrations table
    create_migrations_table
    
    # Run all migrations
    MIGRATION_VERSION="" migrate_up
    
    log "SUCCESS" "Database reset completed"
}

# Run database seeds
run_seeds() {
    local seeds_dir="./seeds"
    
    if [ ! -d "${seeds_dir}" ]; then
        log "INFO" "Seeds directory not found: ${seeds_dir}"
        return 0
    fi
    
    log "INFO" "Running database seeds..."
    
    for seed_file in $(ls -1 "${seeds_dir}"/*.sql 2>/dev/null | sort); do
        log "INFO" "Running seed: $(basename ${seed_file})"
        
        if [ "${DRY_RUN}" = "true" ]; then
            log "INFO" "[DRY RUN] Would execute: psql -f ${seed_file}"
            continue
        fi
        
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
            -v ON_ERROR_STOP=1 \
            -f "${seed_file}" 2>&1 | tee -a "${LOG_FILE}"
        
        if [ ${PIPESTATUS[0]} -ne 0 ]; then
            log "ERROR" "Seed failed: ${seed_file}"
            return 1
        fi
    done
    
    log "SUCCESS" "Seeds completed successfully"
}

# Main execution
main() {
    log "INFO" "========================================="
    log "INFO" "Parking Management System - Database Migration"
    log "INFO" "Environment: ${ENVIRONMENT}"
    log "INFO" "Command: ${MIGRATION_COMMAND}"
    log "INFO" "========================================="
    
    # Parse arguments
    parse_args "$@"
    
    # Check dependencies
    check_dependencies
    
    # Set PostgreSQL password
    set_postgres_password
    
    # Test database connection
    if ! test_connection; then
        exit 1
    fi
    
    # Create migrations table
    if ! create_migrations_table; then
        exit 1
    fi
    
    # Execute command
    case "${MIGRATION_COMMAND}" in
        up)
            if ! acquire_lock; then
                exit 1
            fi
            backup_database
            if migrate_up; then
                release_lock
                log "SUCCESS" "Migration up completed successfully"
            else
                release_lock
                log "ERROR" "Migration up failed"
                exit 1
            fi
            ;;
        down)
            if ! acquire_lock; then
                exit 1
            fi
            backup_database
            if migrate_down; then
                release_lock
                log "SUCCESS" "Migration down completed successfully"
            else
                release_lock
                log "ERROR" "Migration down failed"
                exit 1
            fi
            ;;
        create)
            create_migration "${MIGRATION_NAME}"
            ;;
        status)
            show_status
            ;;
        rollback)
            MIGRATION_VERSION="" migrate_down
            ;;
        redo)
            if ! acquire_lock; then
                exit 1
            fi
            backup_database
            if migrate_down && migrate_up; then
                release_lock
                log "SUCCESS" "Migration redo completed successfully"
            else
                release_lock
                log "ERROR" "Migration redo failed"
                exit 1
            fi
            ;;
        version)
            echo "Current version: $(get_current_version)"
            ;;
        reset)
            if [ "${FORCE}" = "true" ] || [ "${DRY_RUN}" = "true" ]; then
                reset_database
            else
                log "WARNING" "Reset command requires --force flag"
                log "INFO" "Use: $0 reset --force"
                exit 1
            fi
            ;;
        seed)
            run_seeds
            ;;
        *)
            log "ERROR" "Unknown command: ${MIGRATION_COMMAND}"
            show_usage
            exit 1
            ;;
    esac
    
    # Clean environment variable
    unset PGPASSWORD
}

# Handle script interruption
trap 'log "WARNING" "Migration interrupted by user"; release_lock; exit 1' INT TERM

# Run main function
main "$@"