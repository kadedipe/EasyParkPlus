#!/bin/bash
# parking-management/backend/scripts/db/restore.sh
# Database restore script for Parking Management System
# Version: 1.0

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RESTORE_DIR="${RESTORE_DIR:-./restore_logs}"
BACKUP_FILE="${BACKUP_FILE:-}"
RESTORE_MODE="${RESTORE_MODE:-full}" # full, schema, data, selective
DROP_EXISTING="${DROP_EXISTING:-false}"
CREATE_DATABASE="${CREATE_DATABASE:-true}"
VERIFY_RESTORE="${VERIFY_RESTORE:-true}"
ENVIRONMENT="${NODE_ENV:-development}"
DRY_RUN="${DRY_RUN:-false}"
RESTORE_TABLES="${RESTORE_TABLES:-}" # Comma-separated list for selective restore

# Create restore directory if it doesn't exist
mkdir -p "${RESTORE_DIR}"

# Timestamp for logs
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${RESTORE_DIR}/restore_${TIMESTAMP}.log"

# Logging function
log() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    echo -e "${GREEN}[${timestamp}] ${level}: ${message}${NC}" | tee -a "${LOG_FILE}"
    
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
        *)
            echo "[${timestamp}] ${message}" | tee -a "${LOG_FILE}"
            ;;
    esac
}

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Database restore script for Parking Management System

OPTIONS:
    -f, --file FILE           Backup file to restore (required)
    -m, --mode MODE           Restore mode: full, schema, data, selective (default: full)
    -t, --tables TABLES       Comma-separated list of tables for selective restore
    -d, --drop-existing       Drop existing database/tables before restore
    -c, --create-db           Create database if it doesn't exist (default: true)
    --no-verify               Skip restore verification
    --dry-run                 Show what would be done without executing
    -h, --help                Show this help message

EXAMPLES:
    # Full restore from latest backup
    $0 --file backups/parking_management_20240101_120000.sql.gz
    
    # Restore only schema
    $0 --file backups/schema_backup.sql --mode schema
    
    # Selective restore of specific tables
    $0 --file backups/data_backup.sql.gz --mode selective --tables users,parking_spots,reservations
    
    # Drop and recreate database before restore
    $0 --file backups/latest.sql --drop-existing
    
    # Dry run to preview restore
    $0 --file backups/latest.sql --dry-run

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--file)
                BACKUP_FILE="$2"
                shift 2
                ;;
            -m|--mode)
                RESTORE_MODE="$2"
                shift 2
                ;;
            -t|--tables)
                RESTORE_TABLES="$2"
                shift 2
                ;;
            -d|--drop-existing)
                DROP_EXISTING="true"
                shift
                ;;
            -c|--create-db)
                CREATE_DATABASE="true"
                shift
                ;;
            --no-verify)
                VERIFY_RESTORE="false"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Validate required arguments
    if [ -z "${BACKUP_FILE}" ]; then
        log "ERROR" "Backup file is required. Use -f or --file option."
        show_usage
        exit 1
    fi
    
    # Validate restore mode
    case "${RESTORE_MODE}" in
        full|schema|data|selective)
            ;;
        *)
            log "ERROR" "Invalid restore mode: ${RESTORE_MODE}"
            log "INFO" "Valid modes: full, schema, data, selective"
            exit 1
            ;;
    esac
    
    # Validate selective restore tables
    if [ "${RESTORE_MODE}" = "selective" ] && [ -z "${RESTORE_TABLES}" ]; then
        log "ERROR" "Tables list required for selective restore mode"
        exit 1
    fi
}

# Check if required tools are installed
check_dependencies() {
    local missing_deps=()
    
    if ! command -v psql &> /dev/null; then
        missing_deps+=("postgresql-client")
    fi
    
    if ! command -v gunzip &> /dev/null && [[ "${BACKUP_FILE}" == *.gz ]]; then
        missing_deps+=("gzip")
    fi
    
    if ! command -v gpg &> /dev/null && [[ "${BACKUP_FILE}" == *.gpg ]]; then
        missing_deps+=("gpg")
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
    log "INFO" "Testing database connection to ${DB_HOST}:${DB_PORT}"
    
    if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" &> /dev/null; then
        log "INFO" "Database connection successful"
        return 0
    else
        log "ERROR" "Cannot connect to database server"
        return 1
    fi
}

# Check if database exists
database_exists() {
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -t -c "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" 2>/dev/null | grep -q 1
}

# Create database
create_database() {
    log "INFO" "Creating database ${DB_NAME}"
    
    if ! database_exists; then
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER} ENCODING 'UTF8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8'" 2>&1 | tee -a "${LOG_FILE}"
        
        if [ $? -eq 0 ]; then
            log "INFO" "Database ${DB_NAME} created successfully"
            return 0
        else
            log "ERROR" "Failed to create database ${DB_NAME}"
            return 1
        fi
    else
        log "INFO" "Database ${DB_NAME} already exists"
        return 0
    fi
}

# Drop existing database
drop_database() {
    if database_exists; then
        log "WARNING" "Dropping existing database ${DB_NAME}"
        
        if [ "${DRY_RUN}" = "true" ]; then
            log "INFO" "[DRY RUN] Would drop database ${DB_NAME}"
            return 0
        fi
        
        # Terminate all connections to the database
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid()" 2>&1 | tee -a "${LOG_FILE}"
        
        # Drop the database
        psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME}" 2>&1 | tee -a "${LOG_FILE}"
        
        if [ $? -eq 0 ]; then
            log "INFO" "Database ${DB_NAME} dropped successfully"
            return 0
        else
            log "ERROR" "Failed to drop database ${DB_NAME}"
            return 1
        fi
    else
        log "INFO" "Database ${DB_NAME} does not exist"
        return 0
    fi
}

# Prepare backup file for restore
prepare_backup_file() {
    local input_file="${BACKUP_FILE}"
    local temp_file=""
    
    # Check if backup file exists
    if [ ! -f "${input_file}" ]; then
        log "ERROR" "Backup file not found: ${input_file}"
        exit 1
    fi
    
    log "INFO" "Preparing backup file: ${input_file}"
    
    # Decrypt if encrypted
    if [[ "${input_file}" == *.gpg ]]; then
        log "INFO" "Decrypting backup file"
        temp_file="${RESTORE_DIR}/restore_${TIMESTAMP}_decrypted.sql"
        
        if [ "${DRY_RUN}" = "true" ]; then
            log "INFO" "[DRY RUN] Would decrypt ${input_file} to ${temp_file}"
            echo "${temp_file}"
            return
        fi
        
        gpg --decrypt "${input_file}" > "${temp_file}" 2>&1
        input_file="${temp_file}"
    fi
    
    # Decompress if compressed
    if [[ "${input_file}" == *.gz ]]; then
        log "INFO" "Decompressing backup file"
        temp_file="${RESTORE_DIR}/restore_${TIMESTAMP}_decompressed.sql"
        
        if [ "${DRY_RUN}" = "true" ]; then
            log "INFO" "[DRY RUN] Would decompress ${input_file} to ${temp_file}"
            echo "${temp_file}"
            return
        fi
        
        gunzip -c "${input_file}" > "${temp_file}" 2>&1
        input_file="${temp_file}"
    fi
    
    echo "${input_file}"
}

# Validate backup file
validate_backup() {
    local backup_file=$1
    local backup_type=$2
    
    log "INFO" "Validating backup file: ${backup_file}"
    
    # Check file size
    local file_size=$(stat -f%z "${backup_file}" 2>/dev/null || stat -c%s "${backup_file}" 2>/dev/null)
    if [ "${file_size}" -eq 0 ]; then
        log "ERROR" "Backup file is empty"
        return 1
    fi
    
    # Check file header
    local header=$(head -n 1 "${backup_file}")
    if [[ ! "${header}" =~ PostgreSQL|--|COPY|INSERT ]]; then
        log "ERROR" "Invalid backup file format"
        return 1
    fi
    
    # Validate based on backup type
    case "${backup_type}" in
        schema)
            if ! grep -q "CREATE TABLE\|CREATE SCHEMA" "${backup_file}"; then
                log "WARNING" "No schema definitions found in backup file"
            fi
            ;;
        data)
            if ! grep -q "COPY\|INSERT INTO" "${backup_file}"; then
                log "WARNING" "No data found in backup file"
            fi
            ;;
    esac
    
    log "INFO" "Backup file validation passed"
    return 0
}

# Full database restore
restore_full() {
    local backup_file=$1
    
    log "INFO" "Starting full database restore"
    
    if [ "${DRY_RUN}" = "true" ]; then
        log "INFO" "[DRY RUN] Would restore full database from ${backup_file}"
        return 0
    fi
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -v ON_ERROR_STOP=1 \
        -f "${backup_file}" 2>&1 | tee -a "${LOG_FILE}"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ ${exit_code} -eq 0 ]; then
        log "INFO" "Full database restore completed successfully"
        return 0
    else
        log "ERROR" "Full database restore failed with exit code ${exit_code}"
        return 1
    fi
}

# Schema only restore
restore_schema() {
    local backup_file=$1
    
    log "INFO" "Starting schema restore"
    
    if [ "${DRY_RUN}" = "true" ]; then
        log "INFO" "[DRY RUN] Would restore schema from ${backup_file}"
        return 0
    fi
    
    # Extract only schema-related statements
    local schema_file="${RESTORE_DIR}/restore_${TIMESTAMP}_schema.sql"
    
    grep -E "CREATE SCHEMA|CREATE TABLE|CREATE SEQUENCE|CREATE INDEX|CREATE VIEW|CREATE FUNCTION|CREATE TRIGGER|ALTER TABLE|ALTER SEQUENCE" \
        "${backup_file}" > "${schema_file}" 2>&1
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -v ON_ERROR_STOP=1 \
        -f "${schema_file}" 2>&1 | tee -a "${LOG_FILE}"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ ${exit_code} -eq 0 ]; then
        log "INFO" "Schema restore completed successfully"
        rm -f "${schema_file}"
        return 0
    else
        log "ERROR" "Schema restore failed with exit code ${exit_code}"
        return 1
    fi
}

# Data only restore
restore_data() {
    local backup_file=$1
    
    log "INFO" "Starting data restore"
    
    if [ "${DRY_RUN}" = "true" ]; then
        log "INFO" "[DRY RUN] Would restore data from ${backup_file}"
        return 0
    fi
    
    # Extract only data-related statements
    local data_file="${RESTORE_DIR}/restore_${TIMESTAMP}_data.sql"
    
    grep -E "COPY|INSERT INTO|UPDATE|DELETE FROM" "${backup_file}" > "${data_file}" 2>&1
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        -v ON_ERROR_STOP=1 \
        -f "${data_file}" 2>&1 | tee -a "${LOG_FILE}"
    
    local exit_code=${PIPESTATUS[0]}
    
    if [ ${exit_code} -eq 0 ]; then
        log "INFO" "Data restore completed successfully"
        rm -f "${data_file}"
        return 0
    else
        log "ERROR" "Data restore failed with exit code ${exit_code}"
        return 1
    fi
}

# Selective tables restore
restore_selective() {
    local backup_file=$1
    local tables=$2
    
    log "INFO" "Starting selective restore for tables: ${tables}"
    
    IFS=',' read -ra TABLE_ARRAY <<< "${tables}"
    
    for table in "${TABLE_ARRAY[@]}"; do
        log "INFO" "Restoring table: ${table}"
        
        if [ "${DRY_RUN}" = "true" ]; then
            log "INFO" "[DRY RUN] Would restore table ${table}"
            continue
        fi
        
        # Extract table structure and data
        local table_file="${RESTORE_DIR}/restore_${TIMESTAMP}_${table}.sql"
        
        sed -n "/CREATE TABLE ${table}/,/CREATE TABLE/p; /COPY ${table}/,/\./p; /INSERT INTO ${table}/,/;/p" \
            "${backup_file}" > "${table_file}" 2>&1
        
        if [ -s "${table_file}" ]; then
            psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
                -v ON_ERROR_STOP=1 \
                -f "${table_file}" 2>&1 | tee -a "${LOG_FILE}"
            
            local exit_code=${PIPESTATUS[0]}
            
            if [ ${exit_code} -eq 0 ]; then
                log "INFO" "Table ${table} restored successfully"
                rm -f "${table_file}"
            else
                log "ERROR" "Failed to restore table ${table}"
                return 1
            fi
        else
            log "WARNING" "No data found for table ${table} in backup file"
        fi
    done
    
    return 0
}

# Verify restore
verify_restore() {
    log "INFO" "Verifying restore..."
    
    # Get list of tables before restore (if any existed)
    local before_tables=""
    if [ "${DROP_EXISTING}" != "true" ] && database_exists; then
        before_tables=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public'" 2>/dev/null | sort)
    fi
    
    # Get table count after restore
    local after_tables=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT tablename FROM pg_tables WHERE schemaname='public'" 2>/dev/null | sort)
    local table_count=$(echo "${after_tables}" | grep -v "^$" | wc -l)
    
    log "INFO" "Tables after restore: ${table_count}"
    
    # Get row counts for major tables
    log "INFO" "Row counts for key tables:"
    
    local key_tables=("users" "parking_spots" "reservations" "payments" "vehicles")
    for table in "${key_tables[@]}"; do
        if psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM ${table}" &>/dev/null; then
            local count=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM ${table}" 2>/dev/null | xargs)
            log "INFO" "  - ${table}: ${count} rows"
        fi
    done
    
    # Check for foreign key constraints
    local fk_count=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_type='FOREIGN KEY'" 2>/dev/null | xargs)
    log "INFO" "Foreign key constraints: ${fk_count}"
    
    # Check for indexes
    local index_count=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public'" 2>/dev/null | xargs)
    log "INFO" "Indexes: ${index_count}"
    
    log "INFO" "Restore verification completed"
}

# Generate restore report
generate_report() {
    local report_file="${RESTORE_DIR}/restore_report_${TIMESTAMP}.txt"
    local restore_status=$1
    
    cat > "${report_file}" << EOF
========================================
Parking Management System - Restore Report
========================================
Date: $(date)
Environment: ${ENVIRONMENT}
Restore Mode: ${RESTORE_MODE}
Status: ${restore_status}

Database Information:
- Host: ${DB_HOST}:${DB_PORT}
- Database: ${DB_NAME}
- User: ${DB_USER}

Backup Information:
- Source File: ${BACKUP_FILE}
- Restore Time: ${TIMESTAMP}

Configuration:
- Drop Existing: ${DROP_EXISTING}
- Create Database: ${CREATE_DATABASE}
- Verify Restore: ${VERIFY_RESTORE}
- Dry Run: ${DRY_RUN}

EOF

    if [ "${RESTORE_MODE}" = "selective" ]; then
        echo "Restored Tables: ${RESTORE_TABLES}" >> "${report_file}"
    fi
    
    echo "" >> "${report_file}"
    echo "Log File: ${LOG_FILE}" >> "${report_file}"
    echo "========================================" >> "${report_file}"
    
    log "INFO" "Restore report generated: ${report_file}"
}

# Clean up temporary files
cleanup() {
    log "INFO" "Cleaning up temporary files"
    find "${RESTORE_DIR}" -name "restore_${TIMESTAMP}_*" -type f -delete 2>/dev/null || true
}

# Main execution
main() {
    log "INFO" "========================================="
    log "INFO" "Parking Management System - Database Restore"
    log "INFO" "Environment: ${ENVIRONMENT}"
    log "INFO" "Restore Mode: ${RESTORE_MODE}"
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
    
    # Handle database preparation
    if [ "${DROP_EXISTING}" = "true" ]; then
        if ! drop_database; then
            exit 1
        fi
    fi
    
    if [ "${CREATE_DATABASE}" = "true" ]; then
        if ! create_database; then
            exit 1
        fi
    fi
    
    # Prepare backup file
    local prepared_file=$(prepare_backup_file)
    
    if [ "${DRY_RUN}" != "true" ]; then
        # Validate backup file
        if ! validate_backup "${prepared_file}" "${RESTORE_MODE}"; then
            exit 1
        fi
    fi
    
    # Perform restore based on mode
    local restore_status="FAILED"
    
    case "${RESTORE_MODE}" in
        full)
            if restore_full "${prepared_file}"; then
                restore_status="SUCCESS"
            fi
            ;;
        schema)
            if restore_schema "${prepared_file}"; then
                restore_status="SUCCESS"
            fi
            ;;
        data)
            if restore_data "${prepared_file}"; then
                restore_status="SUCCESS"
            fi
            ;;
        selective)
            if restore_selective "${prepared_file}" "${RESTORE_TABLES}"; then
                restore_status="SUCCESS"
            fi
            ;;
    esac
    
    # Verify restore
    if [ "${VERIFY_RESTORE}" = "true" ] && [ "${restore_status}" = "SUCCESS" ] && [ "${DRY_RUN}" != "true" ]; then
        verify_restore
    fi
    
    # Generate report
    generate_report "${restore_status}"
    
    # Clean up
    cleanup
    
    # Clean environment variable
    unset PGPASSWORD
    
    if [ "${restore_status}" = "SUCCESS" ]; then
        log "INFO" "Restore process completed successfully"
        exit 0
    else
        log "ERROR" "Restore process failed"
        exit 1
    fi
}

# Handle script interruption
trap 'log "WARNING" "Restore interrupted by user"; cleanup; exit 1' INT TERM

# Run main function
main "$@"