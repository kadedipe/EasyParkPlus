# parking-management/backend/scripts/deployment/utils/logger.sh
# Logging utilities

LOG_FILE="${DEPLOYMENT_LOG_FILE:-/tmp/deployment.log}"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "${LOG_FILE}")"

log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] [INFO]${NC} $*" | tee -a "${LOG_FILE}"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] [WARNING]${NC} $*" | tee -a "${LOG_FILE}" >&2
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR]${NC} $*" | tee -a "${LOG_FILE}" >&2
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] [SUCCESS]${NC} $*" | tee -a "${LOG_FILE}"
}

log_debug() {
    if [ "${LOG_LEVEL}" = "debug" ]; then
        echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] [DEBUG]${NC} $*" | tee -a "${LOG_FILE}"
    fi
}