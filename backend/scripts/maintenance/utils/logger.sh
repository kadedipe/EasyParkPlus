# parking-management/backend/scripts/maintenance/utils/logger.sh
# Logging utilities for maintenance

MAINTENANCE_LOG_FILE="${MAINTENANCE_LOG_DIR}/maintenance_$(date +%Y%m%d).log"

log_info() {
    if [ "${QUIET}" != "true" ]; then
        echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] [INFO]${NC} $*" | tee -a "${MAINTENANCE_LOG_FILE}"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $*" >> "${MAINTENANCE_LOG_FILE}"
    fi
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] [WARNING]${NC} $*" | tee -a "${MAINTENANCE_LOG_FILE}" >&2
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR]${NC} $*" | tee -a "${MAINTENANCE_LOG_FILE}" >&2
}

log_success() {
    if [ "${QUIET}" != "true" ]; then
        echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] [SUCCESS]${NC} $*" | tee -a "${MAINTENANCE_LOG_FILE}"
    else
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] [SUCCESS] $*" >> "${MAINTENANCE_LOG_FILE}"
    fi
}