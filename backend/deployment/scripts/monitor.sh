#!/bin/bash

# System Monitoring Script

set -e

# Configuration
LOG_FILE="/var/log/parking-monitor.log"
ALERT_EMAIL="admin@parking-management.com"
CPU_THRESHOLD=80
MEMORY_THRESHOLD=80
DISK_THRESHOLD=90

# Function to send alert
send_alert() {
    local message="$1"
    echo "$(date): $message" | mail -s "Parking Management Alert" "${ALERT_EMAIL}"
    echo "$(date): $message" >> "${LOG_FILE}"
}

# Check CPU usage
check_cpu() {
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    if (( $(echo "$cpu_usage > $CPU_THRESHOLD" | bc -l) )); then
        send_alert "High CPU usage: ${cpu_usage}%"
    fi
}

# Check memory usage
check_memory() {
    local memory_usage=$(free | grep Mem | awk '{print $3/$2 * 100.0}')
    if (( $(echo "$memory_usage > $MEMORY_THRESHOLD" | bc -l) )); then
        send_alert "High memory usage: ${memory_usage}%"
    fi
}

# Check disk usage
check_disk() {
    local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | cut -d'%' -f1)
    if [ "${disk_usage}" -gt "${DISK_THRESHOLD}" ]; then
        send_alert "High disk usage: ${disk_usage}%"
    fi
}

# Check Docker containers
check_containers() {
    local unhealthy=$(docker ps --filter "health=unhealthy" --format "table {{.Names}}" | tail -n +2)
    if [ -n "${unhealthy}" ]; then
        send_alert "Unhealthy containers detected:\n${unhealthy}"
    fi
}

# Check API health
check_api() {
    if ! curl -s -f "http://localhost:8000/health" > /dev/null; then
        send_alert "API health check failed"
    fi
}

# Main monitoring loop
main() {
    echo "Starting monitoring at $(date)"
    
    check_cpu
    check_memory
    check_disk
    check_containers
    check_api
    
    echo "Monitoring completed at $(date)"
}

# Run main function
main