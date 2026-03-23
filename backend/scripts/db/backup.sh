#!/bin/bash
# parking-management/backend/scripts/db/backup.sh
# Database backup script for Parking Management System
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
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_COMPRESSION="${BACKUP_COMPRESSION:-true}"
BACKUP_ENCRYPTION="${BACKUP_ENCRYPTION:-false}"
ENVIRONMENT="${NODE_ENV:-development}"
BACKUP_TYPE="${BACKUP_TYPE:-full}" # full, schema, data

# Timestamp for backup files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="${DB_NAME}_${ENVIRONMENT}_${BACKUP_TYPE}_${TIMESTAMP}"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Logging function
log() {
    local level=$1
    local message=$2
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    case $level in
        "INFO")
            echo -e "${GREEN}[${timestamp}] INFO: ${message}${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}[${timestamp}] WARNING: ${message}${NC}"
            ;;
        "ERROR")
            echo -e "${RED}[${timestamp}] ERROR: ${message}${NC}"
            ;;
        *)
            echo "[${timestamp}] ${message}"
            ;;
    esac
}

# Check if required tools are installed
check_dependencies() {
    local missing_deps=()
    
    if ! command -v pg_dump &> /dev/null; then
        missing_deps+=("postgresql-client")
    fi
    
    if [ "${BACKUP_COMPRESSION}" = true ] && ! command -v gzip &> /dev/null; then
        missing_deps+=("gzip")
    fi
    
    if [ "${BACKUP_ENCRYPTION}" = true ] && ! command -v gpg &> /dev/null; then
        missing_deps+=("gpg")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log "ERROR" "Missing dependencies: ${missing_deps[*]}"
        log "INFO" "Please install them using: sudo apt-get install ${missing_deps[*]}"
        exit 1
    fi
}

# Set PostgreSQL password for authentication
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
        log "INFO" "Database connection successful"
        return 0
    else
        log "ERROR" "Cannot connect to database"
        return 1
    fi
}

# Get database size
get_db_size() {
    local size=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT pg_database_size('${DB_NAME}')" 2>/dev/null | xargs)
    if [ -n "${size}" ]; then
        echo $((${size} / 1024 / 1024)) # Convert to MB
    else
        echo "unknown"
    fi
}

# Perform full database backup
backup_full() {
    local backup_file="${BACKUP_DIR}/${BACKUP_NAME}.sql"
    local final_file="${backup_file}"
    
    log "INFO" "Starting full database backup of ${DB_NAME}"
    
    # Perform backup with pg_dump
    pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --verbose \
        --clean \
        --if-exists \
        --create \
        --no-owner \
        --no-privileges \
        --encoding=UTF8 \
        2> "${BACKUP_DIR}/${BACKUP_NAME}.log" > "${backup_file}"
    
    if [ $? -eq 0 ]; then
        log "INFO" "Database dump completed successfully"
        
        # Compress if enabled
        if [ "${BACKUP_COMPRESSION}" = true ]; then
            log "INFO" "Compressing backup file"
            gzip -9 "${backup_file}"
            final_file="${backup_file}.gz"
        fi
        
        # Encrypt if enabled
        if [ "${BACKUP_ENCRYPTION}" = true ] && [ -f "${GPG_RECIPIENT:-}" ]; then
            log "INFO" "Encrypting backup file"
            gpg --recipient "${GPG_RECIPIENT}" --encrypt "${final_file}"
            rm -f "${final_file}"
            final_file="${final_file}.gpg"
        fi
        
        local db_size=$(get_db_size)
        local backup_size=$(du -h "${final_file}" | cut -f1)
        
        log "INFO" "Backup completed: ${final_file}"
        log "INFO" "Database size: ${db_size} MB, Backup size: ${backup_size}"
        
        # Create backup metadata
        create_backup_metadata "${final_file}" "${db_size}" "${backup_size}"
        
        return 0
    else
        log "ERROR" "Backup failed. Check log: ${BACKUP_DIR}/${BACKUP_NAME}.log"
        return 1
    fi
}

# Backup only schema
backup_schema() {
    local backup_file="${BACKUP_DIR}/${BACKUP_NAME}_schema.sql"
    
    log "INFO" "Starting schema backup of ${DB_NAME}"
    
    pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --schema-only \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges \
        --encoding=UTF8 \
        > "${backup_file}"
    
    if [ $? -eq 0 ]; then
        if [ "${BACKUP_COMPRESSION}" = true ]; then
            gzip -9 "${backup_file}"
            backup_file="${backup_file}.gz"
        fi
        log "INFO" "Schema backup completed: ${backup_file}"
        return 0
    else
        log "ERROR" "Schema backup failed"
        return 1
    fi
}

# Backup only data
backup_data() {
    local backup_file="${BACKUP_DIR}/${BACKUP_NAME}_data.sql"
    
    log "INFO" "Starting data backup of ${DB_NAME}"
    
    pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --format=plain \
        --data-only \
        --column-inserts \
        --encoding=UTF8 \
        > "${backup_file}"
    
    if [ $? -eq 0 ]; then
        if [ "${BACKUP_COMPRESSION}" = true ]; then
            gzip -9 "${backup_file}"
            backup_file="${backup_file}.gz"
        fi
        log "INFO" "Data backup completed: ${backup_file}"
        return 0
    else
        log "ERROR" "Data backup failed"
        return 1
    fi
}

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
    "compression": ${BACKUP_COMPRESSION},
    "encryption": ${BACKUP_ENCRYPTION},
    "retention_days": ${RETENTION_DAYS}
}
EOF
    
    log "INFO" "Backup metadata created: ${metadata_file}"
}

# Clean old backups based on retention policy
clean_old_backups() {
    log "INFO" "Cleaning backups older than ${RETENTION_DAYS} days"
    
    local deleted_count=0
    local deleted_size=0
    
    while IFS= read -r file; do
        if [ -f "${file}" ]; then
            local file_size=$(du -b "${file}" | cut -f1)
            deleted_size=$((deleted_size + file_size))
            rm -f "${file}"
            deleted_count=$((deleted_count + 1))
            log "INFO" "Deleted old backup: ${file}"
        fi
    done < <(find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql*" -type f -mtime +${RETENTION_DAYS})
    
    if [ ${deleted_count} -gt 0 ]; then
        log "INFO" "Cleaned ${deleted_count} old backup(s), freed $(numfmt --to=iec ${deleted_size})"
    else
        log "INFO" "No old backups to clean"
    fi
}

# Verify backup integrity
verify_backup() {
    local latest_backup=$(find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql*" -type f -printf "%T@ %p\n" | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [ -n "${latest_backup}" ]; then
        log "INFO" "Verifying latest backup: ${latest_backup}"
        
        if [[ "${latest_backup}" == *.gz ]]; then
            if gunzip -t "${latest_backup}" 2>/dev/null; then
                log "INFO" "Backup integrity verified (gzip check passed)"
                return 0
            else
                log "ERROR" "Backup integrity check failed"
                return 1
            fi
        else
            if head -n 5 "${latest_backup}" | grep -q "PostgreSQL"; then
                log "INFO" "Backup integrity verified (header check passed)"
                return 0
            else
                log "ERROR" "Backup integrity check failed"
                return 1
            fi
        fi
    else
        log "WARNING" "No backup found to verify"
        return 1
    fi
}

# Generate backup report
generate_report() {
    local report_file="${BACKUP_DIR}/backup_report_${TIMESTAMP}.txt"
    
    cat > "${report_file}" << EOF
========================================
Parking Management System - Backup Report
========================================
Date: $(date)
Environment: ${ENVIRONMENT}
Backup Type: ${BACKUP_TYPE}
Database: ${DB_NAME}@${DB_HOST}:${DB_PORT}

Backup Configuration:
- Compression: ${BACKUP_COMPRESSION}
- Encryption: ${BACKUP_ENCRYPTION}
- Retention Days: ${RETENTION_DAYS}

Backup Files:
EOF
    
    find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql*" -type f -printf "  %f (%s bytes, %t)\n" >> "${report_file}"
    
    cat >> "${report_file}" << EOF

Backup Directory: ${BACKUP_DIR}
Total Backups: $(find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql*" -type f | wc -l)
Total Size: $(du -sh "${BACKUP_DIR}" | cut -f1)

========================================
EOF
    
    log "INFO" "Backup report generated: ${report_file}"
}

# Main execution
main() {
    log "INFO" "========================================="
    log "INFO" "Parking Management System - Database Backup"
    log "INFO" "Environment: ${ENVIRONMENT}"
    log "INFO" "Backup Type: ${BACKUP_TYPE}"
    log "INFO" "========================================="
    
    # Check dependencies
    check_dependencies
    
    # Set PostgreSQL password
    set_postgres_password
    
    # Test database connection
    if ! test_connection; then
        exit 1
    fi
    
    # Perform backup based on type
    case "${BACKUP_TYPE}" in
        full)
            if backup_full; then
                clean_old_backups
                verify_backup
                generate_report
                log "INFO" "Backup process completed successfully"
            else
                log "ERROR" "Backup process failed"
                exit 1
            fi
            ;;
        schema)
            backup_schema
            ;;
        data)
            backup_data
            ;;
        *)
            log "ERROR" "Invalid backup type: ${BACKUP_TYPE}"
            log "INFO" "Valid types: full, schema, data"
            exit 1
            ;;
    esac
    
    # Clean up environment variable
    unset PGPASSWORD
}

# Handle script interruption
trap 'log "WARNING" "Backup interrupted by user"; exit 1' INT TERM

# Run main function
main "$@"