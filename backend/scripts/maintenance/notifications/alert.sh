# parking-management/backend/scripts/maintenance/notifications/alert.sh
# Alert and notification system

send_alert() {
    local title=$1
    local message=$2
    local severity=${3:-warning} # warning, error, critical
    
    log_warning "ALERT: ${title} - ${message}"
    
    # Send to Slack
    if [ -n "${SLACK_WEBHOOK_URL}" ]; then
        send_slack_alert "${title}" "${message}" "${severity}"
    fi
    
    # Send to email
    if [ -n "${ALERT_EMAIL}" ]; then
        send_email_alert "${title}" "${message}" "${severity}"
    fi
    
    # Send to PagerDuty
    if [ -n "${PAGERDUTY_SERVICE_KEY}" ] && [ "${severity}" = "critical" ]; then
        send_pagerduty_alert "${title}" "${message}"
    fi
    
    # Log to file
    echo "[$(date)] ${severity}: ${title} - ${message}" >> "${MAINTENANCE_LOG_DIR}/alerts.log"
}

send_slack_alert() {
    local title=$1
    local message=$2
    local severity=$3
    
    local color="warning"
    case "${severity}" in
        error)
            color="danger"
            ;;
        critical)
            color="danger"
            ;;
        warning)
            color="warning"
            ;;
    esac
    
    curl -X POST -H 'Content-type: application/json' \
        --data "{
            \"text\": \"*${title}*\",
            \"attachments\": [{
                \"color\": \"${color}\",
                \"text\": \"${message}\",
                \"fields\": [
                    {\"title\": \"Environment\", \"value\": \"${ENVIRONMENT}\", \"short\": true},
                    {\"title\": \"Server\", \"value\": \"$(hostname)\", \"short\": true},
                    {\"title\": \"Time\", \"value\": \"$(date)\", \"short\": true}
                ],
                \"footer\": \"Parking Management System\",
                \"ts\": $(date +%s)
            }]
        }" \
        "${SLACK_WEBHOOK_URL}" &> /dev/null || true
}

send_email_alert() {
    local title=$1
    local message=$2
    local severity=$3
    
    local subject="[${severity}] ${title} - ${ENVIRONMENT}"
    local body="
    Environment: ${ENVIRONMENT}
    Server: $(hostname)
    Time: $(date)
    
    ${message}
    
    --
    Parking Management System
    "
    
    echo "${body}" | mail -s "${subject}" "${ALERT_EMAIL}" &> /dev/null || true
}

send_pagerduty_alert() {
    local title=$1
    local message=$2
    
    curl -X POST -H 'Content-type: application/json' \
        --data "{
            \"routing_key\": \"${PAGERDUTY_SERVICE_KEY}\",
            \"event_action\": \"trigger\",
            \"payload\": {
                \"summary\": \"${title}\",
                \"source\": \"$(hostname)\",
                \"severity\": \"critical\",
                \"timestamp\": \"$(date -Iseconds)\",
                \"component\": \"${APP_NAME}\",
                \"group\": \"${ENVIRONMENT}\",
                \"class\": \"maintenance\",
                \"custom_details\": {
                    \"message\": \"${message}\",
                    \"environment\": \"${ENVIRONMENT}\"
                }
            }
        }" \
        "https://events.pagerduty.com/v2/enqueue" &> /dev/null || true
}