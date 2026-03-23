#!/bin/bash
# parking-management/backend/scripts/maintenance/maintenance.sh
# Main maintenance orchestration script

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"

# Load configuration
source "${SCRIPT_DIR}/config/maintenance.config.sh"

# Load utility functions
source "${SCRIPT_DIR}/utils/logger.sh"
source "${SCRIPT_DIR}/utils/validators.sh"
source "${SCRIPT_DIR}/utils/helpers.sh"

# Load maintenance modules
source "${SCRIPT_DIR}/database/optimize.sh"
source "${SCRIPT_DIR}/logs/rotate.sh"
source "${SCRIPT_DIR}/cache/clear.sh"
source "${SCRIPT_DIR}/backup/verify.sh"
source "${SCRIPT_DIR}/monitoring/health.sh"
source "${SCRIPT_DIR}/cleanup/clean.sh"
source "${SCRIPT_DIR}/notifications/alert.sh"

# Parse command line arguments
parse_args() {
    MAINTENANCE_TYPE="${1:-all}" # all, database, logs, cache, backup, cleanup, health
    MAINTENANCE_MODE="${MAINTENANCE_MODE:-auto}" # auto, manual, scheduled
    FORCE="${FORCE:-false}"
    DRY_RUN="${DRY_RUN:-false}"
    QUIET="${QUIET:-false}"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type)
                MAINTENANCE_TYPE="$2"
                shift 2
                ;;
            --mode)
                MAINTENANCE_MODE="$2"
                shift 2
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --quiet)
                QUIET=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                shift
                ;;
        esac
    done
}

show_help() {
    cat << EOF
Usage: $0 [TYPE] [OPTIONS]

Maintenance script for Parking Management Backend

TYPES:
    all                 Run all maintenance tasks (default)
    database           Database optimization and cleanup
    logs              Log rotation and cleanup
    cache             Clear various caches
    backup            Verify and clean backups
    cleanup           General system cleanup
    health            Run health checks

OPTIONS:
    --mode MODE        Maintenance mode: auto, manual, scheduled (default: auto)
    --force           Force maintenance even if conditions not met
    --dry-run         Show what would be done without executing
    --quiet           Suppress non-error output
    --help, -h        Show this help message

EXAMPLES:
    # Run all maintenance tasks
    $0 all
    
    # Run only database maintenance
    $0 database
    
    # Run cleanup in dry-run mode
    $0 cleanup --dry-run
    
    # Force maintenance
    $0 all --force

EOF
}

# Check if maintenance should run
should_run_maintenance() {
    # Check if maintenance is already running
    if is_maintenance_running; then
        log_warning "Maintenance already running"
        return 1
    fi
    
    # Check if in maintenance window
    if [ "${MAINTENANCE_MODE}" = "scheduled" ] && ! is_maintenance_window; then
        log_info "Outside maintenance window, skipping"
        return 1
    fi
    
    # Check system load
    if [ "${MAINTENANCE_MODE}" = "auto" ] && is_system_busy; then
        log_warning "System is busy, postponing maintenance"
        return 1
    fi
    
    return 0
}

# Main orchestration
main() {
    local start_time=$(date +%s)
    
    if [ "${QUIET}" != "true" ]; then
        log_info "========================================="
        log_info "Parking Management System - Maintenance"
        log_info "Type: ${MAINTENANCE_TYPE}"
        log_info "Mode: ${MAINTENANCE_MODE}"
        log_info "========================================="
    fi
    
    # Check if maintenance should run
    if ! should_run_maintenance && [ "${FORCE}" != "true" ]; then
        log_info "Maintenance skipped"
        exit 0
    fi
    
    # Acquire maintenance lock
    if ! acquire_maintenance_lock; then
        log_error "Failed to acquire maintenance lock"
        exit 1
    fi
    
    # Trap to release lock on exit
    trap 'release_maintenance_lock' EXIT
    
    # Record start of maintenance
    record_maintenance_start
    
    # Run maintenance tasks based on type
    local exit_code=0
    
    case "${MAINTENANCE_TYPE}" in
        all)
            run_all_maintenance || exit_code=$?
            ;;
        database)
            run_database_maintenance || exit_code=$?
            ;;
        logs)
            run_logs_maintenance || exit_code=$?
            ;;
        cache)
            run_cache_maintenance || exit_code=$?
            ;;
        backup)
            run_backup_maintenance || exit_code=$?
            ;;
        cleanup)
            run_cleanup_maintenance || exit_code=$?
            ;;
        health)
            run_health_checks || exit_code=$?
            ;;
        *)
            log_error "Unknown maintenance type: ${MAINTENANCE_TYPE}"
            exit_code=1
            ;;
    esac
    
    # Record end of maintenance
    record_maintenance_end "${exit_code}"
    
    # Release maintenance lock
    release_maintenance_lock
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ "${QUIET}" != "true" ]; then
        if [ ${exit_code} -eq 0 ]; then
            log_success "Maintenance completed successfully in ${duration} seconds"
        else
            log_error "Maintenance completed with errors in ${duration} seconds"
        fi
    fi
    
    # Send notification if needed
    if [ ${exit_code} -ne 0 ]; then
        send_alert "Maintenance failed" "Maintenance of type ${MAINTENANCE_TYPE} failed with exit code ${exit_code}"
    fi
    
    exit ${exit_code}
}

# Run all maintenance tasks
run_all_maintenance() {
    local overall_exit=0
    
    log_info "Running all maintenance tasks..."
    
    # Run in order
    run_database_maintenance || overall_exit=1
    run_logs_maintenance || overall_exit=1
    run_cache_maintenance || overall_exit=1
    run_backup_maintenance || overall_exit=1
    run_cleanup_maintenance || overall_exit=1
    run_health_checks || overall_exit=1
    
    return ${overall_exit}
}

# Parse arguments and run main
parse_args "$@"
main