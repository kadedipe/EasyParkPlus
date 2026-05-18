#!/bin/bash
# parking-management/backend/scripts/db/pre_migration_backup.sh
# Automatic backup before running migrations

set -euo pipefail

# Load environment variables
source .env 2>/dev/null || true

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
MIGRATIONS_DIR="${MIGRATIONS_DIR:-./migrations}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
MIGRATION_NAME="${1:-}"

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

# Create pre-migration backup
create_pre_migration_backup() {
    log_info "========================================="
    log_info "Creating pre-migration backup"
    log_info "Migration: ${MIGRATION_NAME:-'Unknown'}"
    log_info "========================================="
    
    # Set migration name for metadata
    export MIGRATION_NAME="${MIGRATION_NAME}"
    
    # Run backup with pre_migration type
    if ./scripts/db/backup.sh pre_migration; then
        log_info "Pre-migration backup created successfully"
        
        # Find the latest backup
        local latest_backup=$(find "${BACKUP_DIR}" -name "*pre_migration*.sql.gz" -type f -printf "%T@ %p\n" 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
        
        if [ -n "${latest_backup}" ]; then
            log_info "Backup location: ${latest_backup}"
            
            # Create a symlink for easy access
            ln -sf "${latest_backup}" "${BACKUP_DIR}/pre_migration_latest.sql.gz"
            log_info "Symlink created: ${BACKUP_DIR}/pre_migration_latest.sql.gz"
        fi
        
        return 0
    else
        log_error "Failed to create pre-migration backup"
        return 1
    fi
}

# Verify backup exists
verify_backup() {
    local backup_file="${BACKUP_DIR}/pre_migration_latest.sql.gz"
    
    if [ ! -f "${backup_file}" ]; then
        log_error "No pre-migration backup found"
        return 1
    fi
    
    # Verify file integrity
    if gunzip -t "${backup_file}" 2>/dev/null; then
        log_info "Backup file integrity verified"
        return 0
    else
        log_error "Backup file is corrupted"
        return 1
    fi
}

# Main execution
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --migration|-m)
                MIGRATION_NAME="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  -m, --migration NAME    Migration name for metadata"
                echo "  -h, --help              Show this help message"
                exit 0
                ;;
            *)
                MIGRATION_NAME="$1"
                shift
                ;;
        esac
    done
    
    # Create backup
    if create_pre_migration_backup; then
        if verify_backup; then
            log_info "Pre-migration backup is ready"
            exit 0
        else
            log_error "Backup verification failed"
            exit 1
        fi
    else
        log_error "Backup creation failed"
        exit 1
    fi
}

main "$@"