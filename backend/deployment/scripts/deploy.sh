#!/bin/bash

# Parking Management System - Deployment Script
# This script handles the complete deployment process

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="parking-management"
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEPLOYMENT_DIR="${BACKEND_DIR}/deployment"
ENVIRONMENT=${1:-"production"}  # Default to production
VERSION=$(git describe --tags --always 2>/dev/null || echo "latest")

# Load environment variables
if [ -f "${DEPLOYMENT_DIR}/.env" ]; then
    source "${DEPLOYMENT_DIR}/.env"
else
    echo -e "${RED}Error: .env file not found in deployment directory${NC}"
    exit 1
fi

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 is not installed"
        exit 1
    fi
    
    # Check required directories
    if [ ! -d "${BACKEND_DIR}" ]; then
        error "Backend directory not found: ${BACKEND_DIR}"
        exit 1
    fi
    
    log "✓ All prerequisites satisfied"
}

# Backup database
backup_database() {
    log "Backing up database..."
    
    BACKUP_DIR="${DEPLOYMENT_DIR}/backups"
    mkdir -p "${BACKUP_DIR}"
    
    TIMESTAMP=$(date +'%Y%m%d_%H%M%S')
    BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql"
    
    if [ "${ENVIRONMENT}" = "production" ]; then
        # Production database backup (PostgreSQL)
        docker exec parking-db pg_dump -U ${DB_USER} ${DB_NAME} > "${BACKUP_FILE}"
    else
        # Development database backup (SQLite)
        if [ -f "${BACKEND_DIR}/data/app.db" ]; then
            cp "${BACKEND_DIR}/data/app.db" "${BACKUP_DIR}/db_backup_${TIMESTAMP}.db"
        fi
    fi
    
    # Compress backup
    gzip "${BACKUP_FILE}" 2>/dev/null || gzip "${BACKUP_FILE}.db" 2>/dev/null
    
    # Keep only last 7 backups
    find "${BACKUP_DIR}" -name "db_backup_*.gz" -mtime +7 -delete
    
    log "✓ Database backed up to ${BACKUP_DIR}"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    cd "${BACKEND_DIR}"
    
    # Set PYTHONPATH
    export PYTHONPATH="${BACKEND_DIR}:${PYTHONPATH}"
    
    # Run migrations
    if [ "${ENVIRONMENT}" = "production" ]; then
        docker-compose -f "${DEPLOYMENT_DIR}/docker-compose.prod.yml" exec -T api alembic upgrade head
    else
        docker-compose -f "${DEPLOYMENT_DIR}/docker-compose.yml" exec -T api alembic upgrade head
    fi
    
    log "✓ Migrations completed"
}

# Load fixtures
load_fixtures() {
    log "Loading fixtures..."
    
    cd "${BACKEND_DIR}"
    
    # Set PYTHONPATH
    export PYTHONPATH="${BACKEND_DIR}:${PYTHONPATH}"
    
    # Run fixtures loading script
    if [ "${ENVIRONMENT}" = "production" ]; then
        docker-compose -f "${DEPLOYMENT_DIR}/docker-compose.prod.yml" exec -T api python -m scripts.load_fixtures
    else
        docker-compose -f "${DEPLOYMENT_DIR}/docker-compose.yml" exec -T api python -m scripts.load_fixtures
    fi
    
    log "✓ Fixtures loaded"
}

# Build and deploy containers
deploy_containers() {
    log "Building and deploying containers..."
    
    cd "${DEPLOYMENT_DIR}"
    
    # Pull latest images
    if [ "${ENVIRONMENT}" = "production" ]; then
        docker-compose -f docker-compose.prod.yml pull
    fi
    
    # Build images
    if [ "${ENVIRONMENT}" = "production" ]; then
        docker-compose -f docker-compose.prod.yml build \
            --build-arg VERSION="${VERSION}" \
            --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    else
        docker-compose -f docker-compose.yml build
    fi
    
    # Stop old containers
    if [ "${ENVIRONMENT}" = "production" ]; then
        docker-compose -f docker-compose.prod.yml down --remove-orphans
    else
        docker-compose -f docker-compose.yml down --remove-orphans
    fi
    
    # Start new containers
    if [ "${ENVIRONMENT}" = "production" ]; then
        docker-compose -f docker-compose.prod.yml up -d
    else
        docker-compose -f docker-compose.yml up -d
    fi
    
    log "✓ Containers deployed"
}

# Health check
health_check() {
    log "Performing health check..."
    
    local max_attempts=30
    local attempt=1
    local sleep_time=2
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "http://localhost:8000/health" > /dev/null; then
            log "✓ Health check passed"
            return 0
        fi
        
        info "Health check attempt $attempt/$max_attempts failed, retrying in ${sleep_time}s..."
        sleep $sleep_time
        attempt=$((attempt + 1))
    done
    
    error "Health check failed after $max_attempts attempts"
    return 1
}

# Cleanup old images
cleanup() {
    log "Cleaning up old images and containers..."
    
    # Remove unused images
    docker image prune -f
    
    # Remove unused containers
    docker container prune -f
    
    # Remove unused volumes (optional)
    if [ "${CLEANUP_VOLUMES}" = "true" ]; then
        docker volume prune -f
    fi
    
    log "✓ Cleanup completed"
}

# Notify deployment status
notify() {
    local status=$1
    
    if [ -n "${SLACK_WEBHOOK_URL}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"Deployment of ${PROJECT_NAME} (${ENVIRONMENT}) ${status} - Version: ${VERSION}\"}" \
            "${SLACK_WEBHOOK_URL}"
    fi
    
    log "Deployment ${status}"
}

# Main deployment function
main() {
    log "Starting deployment for ${PROJECT_NAME} (${ENVIRONMENT}) - Version: ${VERSION}"
    
    # Check prerequisites
    check_prerequisites
    
    # Backup database
    backup_database
    
    # Deploy containers
    deploy_containers
    
    # Run migrations
    run_migrations
    
    # Load fixtures (only for initial deployment or when specified)
    if [ "${LOAD_FIXTURES}" = "true" ] || [ ! -f "${DEPLOYMENT_DIR}/.deployed" ]; then
        load_fixtures
        touch "${DEPLOYMENT_DIR}/.deployed"
    fi
    
    # Health check
    if health_check; then
        # Cleanup
        cleanup
        
        # Notify success
        notify "succeeded"
        log "${GREEN}✓ Deployment completed successfully${NC}"
    else
        # Rollback
        error "Deployment failed, rolling back..."
        rollback
        notify "failed"
        exit 1
    fi
}

# Rollback function
rollback() {
    log "Rolling back to previous version..."
    
    cd "${DEPLOYMENT_DIR}"
    
    # Restore previous containers
    if [ "${ENVIRONMENT}" = "production" ]; then
        docker-compose -f docker-compose.prod.yml down
        docker-compose -f docker-compose.prod.yml up -d --no-build
    else
        docker-compose -f docker-compose.yml down
        docker-compose -f docker-compose.yml up -d --no-build
    fi
    
    log "✓ Rollback completed"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --load-fixtures)
            LOAD_FIXTURES="true"
            shift
            ;;
        --no-backup)
            SKIP_BACKUP="true"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --env ENV           Set environment (development/production)"
            echo "  --load-fixtures      Load fixtures after deployment"
            echo "  --no-backup          Skip database backup"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Run main function
main