# parking-management/backend/scripts/deployment/config/deploy.config.sh
# Deployment configuration

# Application Configuration
APP_NAME="parking-management-backend"
APP_PORT="${APP_PORT:-3000}"
NODE_ENV="${ENVIRONMENT:-production}"

# Deployment Paths
DEPLOYMENT_ROOT="/var/www/${APP_NAME}"
CURRENT_DIR="${DEPLOYMENT_ROOT}/current"
RELEASES_DIR="${DEPLOYMENT_ROOT}/releases"
SHARED_DIR="${DEPLOYMENT_ROOT}/shared"
BACKUP_DIR="${DEPLOYMENT_ROOT}/backups"
LOGS_DIR="${DEPLOYMENT_ROOT}/logs"

# Deployment Settings
MAX_RELEASES_TO_KEEP="${MAX_RELEASES_TO_KEEP:-10}"
DEPLOYMENT_TIMEOUT="${DEPLOYMENT_TIMEOUT:-300}" # seconds
HEALTH_CHECK_TIMEOUT="${HEALTH_CHECK_TIMEOUT:-60}" # seconds
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-5}" # seconds
ROLLBACK_ON_FAILURE="${ROLLBACK_ON_FAILURE:-true}"

# Blue-Green Deployment
BLUE_ENV="blue"
GREEN_ENV="green"
ACTIVE_COLOR_FILE="${SHARED_DIR}/active_color"

# Canary Deployment
CANARY_TRAFFIC_PERCENT="${CANARY_TRAFFIC_PERCENT:-10}"
CANARY_DURATION="${CANARY_DURATION:-300}" # seconds

# Load Balancer Configuration
LOAD_BALANCER_TYPE="${LOAD_BALANCER_TYPE:-nginx}" # nginx, haproxy, aws_alb
LOAD_BALANCER_CONFIG_DIR="/etc/nginx/conf.d"

# Service Management
SERVICE_MANAGER="${SERVICE_MANAGER:-systemd}" # systemd, pm2, docker
SERVICE_NAME="${APP_NAME}.service"

# Monitoring
MONITORING_ENABLED="${MONITORING_ENABLED:-true}"
METRICS_ENDPOINT="/metrics"
HEALTH_ENDPOINT="/health"

# Notification Settings
DEPLOYMENT_NOTIFICATIONS_ENABLED="${DEPLOYMENT_NOTIFICATIONS_ENABLED:-true}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
TEAMS_WEBHOOK_URL="${TEAMS_WEBHOOK_URL:-}"

# Logging
LOG_LEVEL="${LOG_LEVEL:-info}"
DEPLOYMENT_LOG_FILE="${LOGS_DIR}/deployment.log"

# Create directories if they don't exist
mkdir -p "${DEPLOYMENT_ROOT}" "${RELEASES_DIR}" "${SHARED_DIR}" "${BACKUP_DIR}" "${LOGS_DIR}"

# Export variables
export APP_NAME NODE_ENV APP_PORT DEPLOYMENT_ROOT CURRENT_DIR RELEASES_DIR
export SHARED_DIR BACKUP_DIR LOGS_DIR MAX_RELEASES_TO_KEEP DEPLOYMENT_TIMEOUT