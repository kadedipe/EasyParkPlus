#!/bin/bash
# parking-management/backend/scripts/db/backup.sh
# Database backup script for Parking Management System
# Version: 2.0

set -euo pipefail

# =====================================================
# CONFIGURATION
# =====================================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory detection (more reliable than relative paths)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

# Load environment variables from multiple possible locations
load_env_file() {
    local env_file="${1:-}"
    if [ -f "${env_file}" ]; then
        # shellcheck source=/dev/null
        source "${env_file}"
        return 0
    fi
    return 1
}

# Try to load .env from various locations
load_env_file "${PROJECT_ROOT}/.env" || \
load_env_file "${SCRIPT_DIR}/../../../.env" || \
load_env_file "../../../.env" || \
load_env_file "../../.env" || \
load_env_file "../.env" || \
load_env_file ".env" || true

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-parking_management}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-}"

# Backup configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_TYPE="${1:-full}"  # full, schema, data, pre_migration
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
COMPRESSION_LEVEL="${COMPRESSION_LEVEL:-9}"
ENABLE_ENCRYPTION="${ENABLE_ENCRYPTION:-false}"
GPG_RECIPIENT="${GPG_RECIPIENT:-}"
ENVIRONMENT="${NODE_ENV:-development}"

# Validation
VALID_BACKUP_TYPES=("full" "schema" "data" "pre_migration")
if [[ ! " ${VALID_BACKUP_TYPES[*]} " =~ " ${BACKUP_TYPE} " ]]; then
    echo -e "${RED}Error: Invalid backup type '${BACKUP_TYPE}'. Valid types: ${VALID_BACKUP_TYPES[*]}${NC}"
    exit 1
fi

# Timestamp for backup files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATE=$(date +"%Y-%m-%d")
BACKUP_NAME="${DB_NAME}_${ENVIRONMENT}_${BACKUP_TYPE}_${TIMESTAMP}"

# Create backup directory and subdirectories
mkdir -p "${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}/logs"

# Log file
LOG_FILE="${BACKUP_DIR}/logs/backup_${TIMESTAMP}.log"

# =====================================================
# LOGGING FUNCTIONS
# =====================================================

log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] [INFO]${NC} $*" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR]${NC} $*" | tee -a "${LOG_FILE}" >&2
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] [WARNING]${NC} $*" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] [SUCCESS]${NC} $*" | tee -a "${LOG_FILE}"
}

# =====================================================
# VALIDATION FUNCTIONS
# =====================================================

# Check if required tools are installed
check_dependencies() {
    log_info "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command -v pg_dump &> /dev/null; then
        missing_deps+=("postgresql-client")
    fi
    
    if ! command -v gzip &> /dev/null; then
        missing_deps+=("gzip")
    fi
    
    if [ "${ENABLE_ENCRYPTION}" = "true" ] && ! command -v gpg &> /dev/null; then
        missing_deps+=("gpg")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install them using: sudo apt-get install ${missing_deps[*]}"
        exit 1
    fi
    
    log_success "All dependencies satisfied"
}

# Set PostgreSQL password for authentication
set_postgres_password() {
    if [ -n "${DB_PASSWORD}" ]; then
        export PGPASSWORD="${DB_PASSWORD}"
    else
        log_warning "DB_PASSWORD not set in environment"
    fi
}

# Test database connection
test_connection() {
    log_info "Testing database connection to ${DB_HOST}:${DB_PORT}/${DB_NAME}"
    
    if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" &> /dev/null; then
        log_success "Database connection successful"
        return 0
    else
        log_error "Cannot connect to database"
        return 1
    fi
}

# Get database size in MB
get_db_size() {
    local size
    size=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
        "SELECT pg_database_size('${DB_NAME}')" 2>/dev/null | xargs)
    
    if [ -n "${size}" ] && [[ "${size}" =~ ^[0-9]+$ ]]; then
        echo $((size / 1024 / 1024))
    else
        echo "unknown"
    fi
}

# =====================================================
# BACKUP FUNCTIONS
# =====================================================

# Create backup metadata
create_backup_metadata() {
    local backup_file=$1
    local db_size=$2
    local backup_size=$3
    
    local metadata_file="${backup_file}.metadata.json"
    
    cat > "${metadata_file}" << EOF
{
    "backup_name": "${BACKUP_NAME}",
    "timestamp": "$(date -Iseconds)",
    "database": "${DB_NAME}",
    "environment": "${ENVIRONMENT}",
    "backup_type": "${BACKUP_TYPE}",
    "host": "${DB_HOST}",
    "port": "${DB_PORT}",
    "db_size_mb": ${db_size},
    "backup_size": "${backup_size}",
    "compression": true,
    "compression_level": ${COMPRESSION_LEVEL},
    "encryption": ${ENABLE_ENCRYPTION},
    "retention_days": ${RETENTION_DAYS},
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')",
    "hostname": "$(hostname)",
    "user": "${USER:-unknown}"
}
EOF
    
    log_info "Backup metadata created: ${metadata_file}"
}

# Perform full database backup
backup_full() {
    local backup_file="${BACKUP_DIR}/${BACKUP_NAME}.sql"
    local final_file="${backup_file}"
    
    log_info "Starting full database backup of ${DB_NAME}"
    
    # Perform backup with pg_dump
    if ! pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --verbose \
        --clean \
        --if-exists \
        --create \
        --no-owner \
        --no-privileges \
        --encoding=UTF8 \
        2> "${BACKUP_DIR}/${BACKUP_NAME}.log" > "${backup_file}"; then
        log_error "Backup failed. Check log: ${BACKUP_DIR}/${BACKUP_NAME}.log"
        return 1
    fi
    
    log_info "Database dump completed successfully"
    
    # Compress
    log_info "Compressing backup file (level ${COMPRESSION_LEVEL})"
    if ! gzip -${COMPRESSION_LEVEL} "${backup_file}"; then
        log_error "Compression failed"
        return 1
    fi
    final_file="${backup_file}.gz"
    
    # Encrypt if enabled
    if [ "${ENABLE_ENCRYPTION}" = "true" ]; then
        if [ -z "${GPG_RECIPIENT}" ]; then
            log_error "GPG_RECIPIENT not set for encryption"
            return 1
        fi
        log_info "Encrypting backup file"
        if ! gpg --batch --yes --recipient "${GPG_RECIPIENT}" --encrypt "${final_file}"; then
            log_error "Encryption failed"
            return 1
        fi
        rm -f "${final_file}"
        final_file="${final_file}.gpg"
    fi
    
    local db_size
    db_size=$(get_db_size)
    local backup_size
    backup_size=$(du -h "${final_file}" 2>/dev/null | cut -f1)
    
    log_success "Backup completed: ${final_file}"
    log_info "Database size: ${db_size} MB, Backup size: ${backup_size}"
    
    # Create backup metadata
    create_backup_metadata "${final_file}" "${db_size}" "${backup_size}"
    
    return 0
}

# Backup only schema
backup_schema() {
    local backup_file="${BACKUP_DIR}/${BACKUP_NAME}_schema.sql"
    
    log_info "Starting schema backup of ${DB_NAME}"
    
    if ! pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --schema-only \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges \
        --encoding=UTF8 \
        > "${backup_file}" 2>> "${LOG_FILE}"; then
        log_error "Schema backup failed"
        return 1
    fi
    
    if ! gzip -${COMPRESSION_LEVEL} "${backup_file}"; then
        log_error "Compression failed"
        return 1
    fi
    
    log_success "Schema backup completed: ${backup_file}.gz"
    return 0
}

# Backup only data
backup_data() {
    local backup_file="${BACKUP_DIR}/${BACKUP_NAME}_data.sql"
    
    log_info "Starting data backup of ${DB_NAME}"
    
    if ! pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --data-only \
        --column-inserts \
        --encoding=UTF8 \
        > "${backup_file}" 2>> "${LOG_FILE}"; then
        log_error "Data backup failed"
        return 1
    fi
    
    if ! gzip -${COMPRESSION_LEVEL} "${backup_file}"; then
        log_error "Compression failed"
        return 1
    fi
    
    log_success "Data backup completed: ${backup_file}.gz"
    return 0
}

# Pre-migration backup (special backup before running migrations)
backup_pre_migration() {
    local backup_file="${BACKUP_DIR}/${BACKUP_NAME}.sql"
    local final_file="${backup_file}"
    local migration_name="${MIGRATION_NAME:-unknown}"
    
    log_info "========================================="
    log_info "PRE-MIGRATION DATABASE BACKUP"
    log_info "========================================="
    log_info "Migration: ${migration_name}"
    log_info "Starting pre-migration backup of ${DB_NAME}"
    
    # Create backup with metadata header
    cat > "${backup_file}" << EOF
-- =====================================================
-- DATABASE BACKUP
-- =====================================================
-- Backup Date: $(date -Iseconds)
-- Backup Type: Pre-migration backup
-- Database: ${DB_NAME}
-- Migration: ${migration_name}
-- Purpose: Backup before applying schema changes
-- =====================================================

BEGIN;

EOF
    
    # Append schema and data
    if ! pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --verbose \
        --clean \
        --if-exists \
        --create \
        --no-owner \
        --no-privileges \
        --encoding=UTF8 \
        >> "${backup_file}" 2>> "${LOG_FILE}"; then
        log_error "Pre-migration backup failed"
        rm -f "${backup_file}"
        return 1
    fi
    
    # Add verification footer
    cat >> "${backup_file}" << EOF

-- =====================================================
-- BACKUP COMPLETION
-- =====================================================
-- Backup completed at: $(date -Iseconds)
-- Database size: $(get_db_size) MB
-- =====================================================

COMMIT;
EOF
    
    log_info "Database dump completed successfully"
    
    # Compress
    log_info "Compressing backup file (level ${COMPRESSION_LEVEL})"
    if ! gzip -${COMPRESSION_LEVEL} "${backup_file}"; then
        log_error "Compression failed"
        return 1
    fi
    final_file="${backup_file}.gz"
    
    local db_size
    db_size=$(get_db_size)
    local backup_size
    backup_size=$(du -h "${final_file}" 2>/dev/null | cut -f1)
    
    # Create metadata file
    cat > "${BACKUP_DIR}/${BACKUP_NAME}.metadata.json" << EOF
{
    "backup_name": "${BACKUP_NAME}",
    "timestamp": "$(date -Iseconds)",
    "backup_type": "pre_migration",
    "migration_name": "${migration_name}",
    "database": "${DB_NAME}",
    "database_size_mb": ${db_size},
    "compression": "gzip",
    "compression_level": ${COMPRESSION_LEVEL},
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')",
    "hostname": "$(hostname)",
    "user": "${USER:-unknown}"
}
EOF
    
    log_success "Pre-migration backup completed successfully!"
    log_info "Backup file: ${final_file}"
    log_info "Metadata file: ${BACKUP_DIR}/${BACKUP_NAME}.metadata.json"
    log_info "Database size: ${db_size} MB, Backup size: ${backup_size}"
    
    # Create a symlink for easy access
    ln -sf "${final_file}" "${BACKUP_DIR}/pre_migration_latest.sql.gz"
    ln -sf "${BACKUP_DIR}/${BACKUP_NAME}.metadata.json" "${BACKUP_DIR}/pre_migration_latest.metadata.json"
    log_info "Symlinks created: pre_migration_latest.sql.gz and pre_migration_latest.metadata.json"
    
    return 0
}

# =====================================================
# MAINTENANCE FUNCTIONS
# =====================================================

# Clean old backups based on retention policy
clean_old_backups() {
    log_info "Cleaning backups older than ${RETENTION_DAYS} days"
    
    local deleted_count=0
    local deleted_size=0
    
    while IFS= read -r file; do
        if [ -f "${file}" ]; then
            local file_size
            file_size=$(stat -f%z "${file}" 2>/dev/null || stat -c%s "${file}" 2>/dev/null || echo 0)
            deleted_size=$((deleted_size + (file_size > 0 ? file_size : 0)))
            rm -f "${file}"
            rm -f "${file}.metadata.json" 2>/dev/null || true
            deleted_count=$((deleted_count + 1))
            log_info "Deleted old backup: $(basename "${file}")"
        fi
    done < <(find "${BACKUP_DIR}" -maxdepth 1 -name "${DB_NAME}_*.sql*" -type f -mtime +${RETENTION_DAYS} 2>/dev/null || true)
    
    if [ ${deleted_count} -gt 0 ]; then
        if command -v numfmt &> /dev/null; then
            log_info "Cleaned ${deleted_count} old backup(s), freed $(numfmt --to=iec ${deleted_size})"
        else
            log_info "Cleaned ${deleted_count} old backup(s), freed ${deleted_size} bytes"
        fi
    else
        log_info "No old backups to clean"
    fi
}

# Verify backup integrity
verify_backup() {
    local latest_backup
    latest_backup=$(find "${BACKUP_DIR}" -maxdepth 1 -name "${DB_NAME}_*.sql.gz" -type f -printf "%T@ %p\n" 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2- || true)
    
    if [ -n "${latest_backup}" ] && [ -f "${latest_backup}" ]; then
        log_info "Verifying latest backup: $(basename "${latest_backup}")"
        
        if gunzip -t "${latest_backup}" 2>/dev/null; then
            log_success "Backup integrity verified (gzip check passed)"
            return 0
        else
            log_error "Backup integrity check failed"
            return 1
        fi
    else
        log_warning "No backup found to verify"
        return 1
    fi
}

# Generate backup report
generate_report() {
    local report_file="${BACKUP_DIR}/backup_report_${TIMESTAMP}.txt"
    
    {
        echo "========================================"
        echo "Parking Management System - Backup Report"
        echo "========================================"
        echo "Date: $(date)"
        echo "Environment: ${ENVIRONMENT}"
        echo "Backup Type: ${BACKUP_TYPE}"
        echo "Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
        echo ""
        echo "Backup Configuration:"
        echo "- Compression Level: ${COMPRESSION_LEVEL}"
        echo "- Encryption: ${ENABLE_ENCRYPTION}"
        echo "- Retention Days: ${RETENTION_DAYS}"
        echo ""
        echo "Backup Files:"
    } >> "${report_file}"
    
    find "${BACKUP_DIR}" -maxdepth 1 -name "${DB_NAME}_*.sql*" -type f -printf "  %f (%s bytes, %t)\n" 2>/dev/null >> "${report_file}" || true
    
    {
        echo ""
        echo "Backup Directory: ${BACKUP_DIR}"
        echo "Total Backups: $(find "${BACKUP_DIR}" -maxdepth 1 -name "${DB_NAME}_*.sql*" -type f 2>/dev/null | wc -l)"
        echo "Total Size: $(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1)"
        echo ""
        echo "========================================"
    } >> "${report_file}"
    
    log_info "Backup report generated: ${report_file}"
}

# =====================================================
# MAIN EXECUTION
# =====================================================

main() {
    log_info "========================================="
    log_info "Parking Management System - Database Backup"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Backup Type: ${BACKUP_TYPE}"
    log_info "========================================="
    
    # Check dependencies
    check_dependencies
    
    # Set PostgreSQL password
    set_postgres_password
    
    # Test database connection
    if ! test_connection; then
        exit 1
    fi
    
    # Perform backup based on type
    local backup_success=false
    
    case "${BACKUP_TYPE}" in
        full)
            if backup_full; then
                backup_success=true
            fi
            ;;
        schema)
            if backup_schema; then
                backup_success=true
            fi
            ;;
        data)
            if backup_data; then
                backup_success=true
            fi
            ;;
        pre_migration)
            if backup_pre_migration; then
                backup_success=true
            fi
            ;;
    esac
    
    if [ "${backup_success}" = true ]; then
        # Only run maintenance for full and pre_migration backups
        if [[ "${BACKUP_TYPE}" == "full" ]] || [[ "${BACKUP_TYPE}" == "pre_migration" ]]; then
            clean_old_backups
            verify_backup || true  # Don't fail if no backup to verify
            generate_report
        fi
        log_success "Backup process completed successfully"
        exit 0
    else
        log_error "Backup process failed"
        exit 1
    fi
    
    # Clean up environment variable
    unset PGPASSWORD
}

# Handle script interruption
trap 'log_warning "Backup interrupted by user"; exit 1' INT TERM

# Run main function
main "$@"