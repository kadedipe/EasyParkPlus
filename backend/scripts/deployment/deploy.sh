#!/bin/bash
# parking-management/backend/scripts/deployment/deploy.sh
# Main deployment orchestration script

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"

# Load configuration
source "${SCRIPT_DIR}/config/deploy.config.sh"

# Load utility functions
source "${SCRIPT_DIR}/utils/logger.sh"
source "${SCRIPT_DIR}/utils/validators.sh"
source "${SCRIPT_DIR}/utils/helpers.sh"

# Load deployment modules
source "${SCRIPT_DIR}/build/build.sh"
source "${SCRIPT_DIR}/deploy/deploy.sh"
source "${SCRIPT_DIR}/rollback/rollback.sh"
source "${SCRIPT_DIR}/health/health_check.sh"

# Parse command line arguments
parse_args() {
    DEPLOYMENT_MODE="${1:-full}"
    SKIP_BUILD="${SKIP_BUILD:-false}"
    SKIP_MIGRATIONS="${SKIP_MIGRATIONS:-false}"
    SKIP_HEALTH_CHECK="${SKIP_HEALTH_CHECK:-false}"
    FORCE_DEPLOY="${FORCE_DEPLOY:-false}"
    DEPLOYMENT_TAG="${DEPLOYMENT_TAG:-$(date +%Y%m%d_%H%M%S)}"
    ENVIRONMENT="${ENVIRONMENT:-production}"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --mode)
                DEPLOYMENT_MODE="$2"
                shift 2
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-migrations)
                SKIP_MIGRATIONS=true
                shift
                ;;
            --skip-health-check)
                SKIP_HEALTH_CHECK=true
                shift
                ;;
            --force)
                FORCE_DEPLOY=true
                shift
                ;;
            --tag)
                DEPLOYMENT_TAG="$2"
                shift 2
                ;;
            --env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Deployment script for Parking Management Backend

OPTIONS:
    --mode MODE             Deployment mode: full, rolling, blue-green, canary (default: full)
    --skip-build           Skip build process
    --skip-migrations      Skip database migrations
    --skip-health-check    Skip health check after deployment
    --force                Force deployment even if checks fail
    --tag TAG              Deployment tag/version (default: timestamp)
    --env ENV              Environment: development, staging, production (default: production)
    --help, -h             Show this help message

EXAMPLES:
    # Full deployment
    $0 --mode full
    
    # Rolling deployment to production
    $0 --mode rolling --env production
    
    # Blue-green deployment with specific tag
    $0 --mode blue-green --tag v1.2.3
    
    # Canary deployment with 10% traffic
    CANARY_TRAFFIC_PERCENT=10 $0 --mode canary

EOF
}

# Main deployment orchestration
main() {
    local start_time=$(date +%s)
    
    log_info "========================================="
    log_info "Parking Management System - Deployment"
    log_info "Environment: ${ENVIRONMENT}"
    log_info "Mode: ${DEPLOYMENT_MODE}"
    log_info "Tag: ${DEPLOYMENT_TAG}"
    log_info "========================================="
    
    # Validate environment
    if ! validate_environment; then
        log_error "Environment validation failed"
        exit 1
    fi
    
    # Create deployment lock
    if ! acquire_deployment_lock; then
        log_error "Failed to acquire deployment lock"
        exit 1
    fi
    
    # Trap to release lock on exit
    trap 'release_deployment_lock' EXIT
    
    # Pre-deployment checks
    if ! run_pre_deployment_checks; then
        log_error "Pre-deployment checks failed"
        exit 1
    fi
    
    # Build phase
    if [ "${SKIP_BUILD}" != "true" ]; then
        if ! build_application; then
            log_error "Build failed"
            exit 1
        fi
    else
        log_warning "Skipping build process"
    fi
    
    # Database migrations
    if [ "${SKIP_MIGRATIONS}" != "true" ]; then
        if ! run_migrations; then
            log_error "Database migrations failed"
            exit 1
        fi
    else
        log_warning "Skipping database migrations"
    fi
    
    # Execute deployment based on mode
    case "${DEPLOYMENT_MODE}" in
        full)
            deploy_full
            ;;
        rolling)
            deploy_rolling
            ;;
        blue-green)
            deploy_blue_green
            ;;
        canary)
            deploy_canary
            ;;
        *)
            log_error "Unknown deployment mode: ${DEPLOYMENT_MODE}"
            exit 1
            ;;
    esac
    
    # Health check
    if [ "${SKIP_HEALTH_CHECK}" != "true" ]; then
        if ! verify_deployment; then
            log_error "Health check failed"
            if [ "${FORCE_DEPLOY}" != "true" ]; then
                log_error "Rolling back due to health check failure"
                rollback_deployment
                exit 1
            else
                log_warning "Continuing despite health check failure (--force)"
            fi
        fi
    fi
    
    # Post-deployment tasks
    run_post_deployment_tasks
    
    # Cleanup old deployments
    cleanup_old_deployments
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_success "Deployment completed successfully in ${duration} seconds"
    
    # Send deployment notification
    send_deployment_notification "success" "${duration}"
    
    # Release deployment lock
    release_deployment_lock
}

# Run pre-deployment checks
run_pre_deployment_checks() {
    log_info "Running pre-deployment checks..."
    
    # Check disk space
    local available_space=$(df -h . | awk 'NR==2 {print $4}')
    log_info "Available disk space: ${available_space}"
    
    # Check memory
    local available_memory=$(free -h | awk 'NR==2 {print $7}')
    log_info "Available memory: ${available_memory}"
    
    # Check if application is running
    if is_application_running; then
        log_info "Application is currently running"
    else
        log_warning "Application is not running"
    fi
    
    # Check database connection
    if check_database_connection; then
        log_success "Database connection OK"
    else
        log_error "Database connection failed"
        return 1
    fi
    
    # Check required ports
    local required_ports=(${APP_PORT:-3000} ${DB_PORT:-5432} ${REDIS_PORT:-6379})
    for port in "${required_ports[@]}"; do
        if check_port_available "${port}"; then
            log_info "Port ${port} is available"
        else
            log_error "Port ${port} is already in use"
            return 1
        fi
    done
    
    # Check environment variables
    if ! validate_required_env_vars; then
        return 1
    fi
    
    log_success "Pre-deployment checks passed"
    return 0
}

# Run post-deployment tasks
run_post_deployment_tasks() {
    log_info "Running post-deployment tasks..."
    
    # Clear cache
    if command -v redis-cli &> /dev/null; then
        log_info "Clearing Redis cache"
        redis-cli FLUSHALL || log_warning "Failed to clear Redis cache"
    fi
    
    # Restart queue workers
    if command -v pm2 &> /dev/null; then
        log_info "Restarting queue workers"
        pm2 restart worker-queue || log_warning "Failed to restart workers"
    fi
    
    # Update deployment metrics
    update_deployment_metrics
    
    # Log deployment info
    log_deployment_info
    
    log_success "Post-deployment tasks completed"
}

# Parse arguments and run main
parse_args "$@"
main