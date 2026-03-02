#!/bin/bash
# Deployment script for Parking Management System

set -e

echo "🚗 Deploying Parking Management System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENV_FILE=".env"
COMPOSE_FILE="deployment/docker/docker-compose.yml"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

print_step() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    print_step "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_step "Dependencies check passed"
}

load_environment() {
    if [ -f "${ENV_FILE}" ]; then
        print_step "Loading environment variables from ${ENV_FILE}"
        export $(grep -v '^#' ${ENV_FILE} | xargs)
    else
        print_warning "Environment file ${ENV_FILE} not found. Using defaults."
        cp deployment/docker/.env.example ${ENV_FILE}
        print_step "Created ${ENV_FILE} from template. Please edit it before production use."
    fi
}

backup_database() {
    print_step "Creating database backup..."
    
    mkdir -p ${BACKUP_DIR}
    
    if docker-compose -f ${COMPOSE_FILE} ps postgres-primary | grep -q "Up"; then
        docker-compose -f ${COMPOSE_FILE} exec postgres-primary /backup.sh
        docker cp $(docker-compose -f ${COMPOSE_FILE} ps -q postgres-primary):/var/lib/postgresql/backups/. ${BACKUP_DIR}/
        print_step "Database backup saved to ${BACKUP_DIR}"
    else
        print_warning "PostgreSQL is not running. Skipping backup."
    fi
}

stop_services() {
    print_step "Stopping existing services..."
    docker-compose -f ${COMPOSE_FILE} down
}

build_images() {
    print_step "Building Docker images..."
    docker-compose -f ${COMPOSE_FILE} build --pull --no-cache
}

start_services() {
    print_step "Starting services..."
    docker-compose -f ${COMPOSE_FILE} up -d
    
    # Wait for services to be healthy
    print_step "Waiting for services to be ready..."
    sleep 10
    
    # Check service status
    print_step "Checking service status..."
    docker-compose -f ${COMPOSE_FILE} ps
}

generate_ssl() {
    print_step "Generating SSL certificates..."
    
    SSL_DIR="deployment/docker/nginx/ssl"
    if [ ! -f "${SSL_DIR}/cert.pem" ] || [ ! -f "${SSL_DIR}/key.pem" ]; then
        docker run --rm -v $(pwd)/${SSL_DIR}:/ssl alpine/openssl \
            sh -c "apk add openssl && \
                   cd /ssl && \
                   openssl genrsa -out key.pem 2048 && \
                   openssl req -new -key key.pem -out csr.pem -subj '/C=US/CN=localhost' && \
                   openssl x509 -req -days 365 -in csr.pem -signkey key.pem -out cert.pem && \
                   rm csr.pem"
        print_step "SSL certificates generated"
    else
        print_step "SSL certificates already exist"
    fi
}

run_migrations() {
    print_step "Running database migrations..."
    
    # Wait for database to be ready
    until docker-compose -f ${COMPOSE_FILE} exec postgres-primary pg_isready -U parking_user; do
        print_step "Waiting for database..."
        sleep 5
    done
    
    # Run migrations if migration container exists
    if docker-compose -f ${COMPOSE_FILE} ps | grep -q "migration"; then
        docker-compose -f ${COMPOSE_FILE} run --rm migration
    else
        print_warning "No migration service found. Skipping migrations."
    fi
}

monitor_logs() {
    print_step "Monitoring logs (Ctrl+C to exit)..."
    echo -e "${YELLOW}"
    docker-compose -f ${COMPOSE_FILE} logs -f --tail=50
    echo -e "${NC}"
}

cleanup() {
    print_step "Cleaning up unused Docker resources..."
    docker system prune -f
}

show_info() {
    echo ""
    echo "========================================"
    echo "🚗 Parking Management System Deployed!"
    echo "========================================"
    echo ""
    echo "Services:"
    echo "  • API Gateway:      https://localhost"
    echo "  • Parking API:      http://localhost:3000"
    echo "  • Payment Service:  http://localhost:3001"
    echo "  • Notification Svc: http://localhost:3002"
    echo "  • PostgreSQL:       localhost:5432"
    echo "  • Redis:            localhost:6379"
    echo "  • Prometheus:       http://localhost:9090"
    echo "  • Grafana:          http://localhost:3003"
    echo "  • Kibana:           http://localhost:5601"
    echo ""
    echo "Admin Credentials:"
    echo "  • Email:    admin@parking.com"
    echo "  • Password: Admin123!"
    echo ""
    echo "Management Commands:"
    echo "  • View logs:    docker-compose -f ${COMPOSE_FILE} logs -f"
    echo "  • Stop:         docker-compose -f ${COMPOSE_FILE} down"
    echo "  • Restart:      docker-compose -f ${COMPOSE_FILE} restart"
    echo "  • Status:       docker-compose -f ${COMPOSE_FILE} ps"
    echo ""
    echo "Backup directory: ${BACKUP_DIR}"
    echo "========================================"
}

# Main execution
main() {
    print_step "Starting deployment process..."
    
    check_dependencies
    load_environment
    backup_database
    stop_services
    generate_ssl
    build_images
    start_services
    run_migrations
    cleanup
    show_info
    
    # Optional: monitor logs
    read -p "Do you want to monitor logs? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        monitor_logs
    fi
    
    print_step "Deployment completed successfully!"
}

# Handle script arguments
case "$1" in
    start)
        load_environment
        start_services
        show_info
        ;;
    stop)
        stop_services
        ;;
    restart)
        load_environment
        stop_services
        start_services
        show_info
        ;;
    backup)
        load_environment
        backup_database
        ;;
    logs)
        monitor_logs
        ;;
    status)
        docker-compose -f ${COMPOSE_FILE} ps
        ;;
    update)
        load_environment
        stop_services
        build_images
        start_services
        show_info
        ;;
    *)
        main
        ;;
esac