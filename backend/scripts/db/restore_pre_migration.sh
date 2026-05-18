#!/bin/bash
# parking-management/backend/scripts/db/restore_pre_migration.sh
# Restore from pre-migration backup

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_FILE="${1:-${BACKUP_DIR}/pre_migration_latest.sql.gz}"
DB_NAME="${DB_NAME:-parking_management}"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" >&2
}

# Confirm restore
confirm_restore() {
    log_warning "========================================="
    log_warning "DANGER: This will restore the database"
    log_warning "from a pre-migration backup!"
    log_warning "Current database will be OVERWRITTEN!"
    log_warning "========================================="
    
    read -p "Are you sure you want to continue? (yes/no): " confirmation
    if [ "${confirmation}" != "yes" ]; then
        log_info "Restore cancelled"
        exit 0
    fi
    
    read -p "Type 'RESTORE' to confirm: " final_confirmation
    if [ "${final_confirmation}" != "RESTORE" ]; then
        log_info "Restore cancelled"
        exit 0
    fi
}

# Restore database
restore_database() {
    log_info "Starting database restore from pre-migration backup"
    log_info "Backup file: ${BACKUP_FILE}"
    
    if [ ! -f "${BACKUP_FILE}" ]; then
        log_error "Backup file not found: ${BACKUP_FILE}"
        exit 1
    fi
    
    # Verify backup integrity
    log_info "Verifying backup integrity..."
    if ! gunzip -t "${BACKUP_FILE}" 2>/dev/null; then
        log_error "Backup file is corrupted"
        exit 1
    fi
    
    # Restore
    log_info "Restoring database..."
    gunzip -c "${BACKUP_FILE}" | psql -d "${DB_NAME}" -v ON_ERROR_STOP=1
    
    if [ $? -eq 0 ]; then
        log_success "Database restored successfully from pre-migration backup"
        return 0
    else
        log_error "Database restore failed"
        return 1
    fi
}

# Main execution
main() {
    confirm_restore
    restore_database
}

main "$@"