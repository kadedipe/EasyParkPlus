#!/bin/bash

# Health Check Script

set -e

API_URL=${1:-"http://localhost:8000"}
TIMEOUT=5
MAX_RETRIES=3

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_endpoint() {
    local endpoint=$1
    local expected_status=$2
    
    echo -n "Checking ${endpoint}... "
    
    local status=$(curl -s -o /dev/null -w "%{http_code}" --max-time ${TIMEOUT} "${API_URL}${endpoint}")
    
    if [ "${status}" -eq "${expected_status}" ]; then
        echo -e "${GREEN}OK (${status})${NC}"
        return 0
    else
        echo -e "${RED}FAILED (${status})${NC}"
        return 1
    fi
}

check_json_response() {
    local endpoint=$1
    local field=$2
    local expected_value=$3
    
    echo -n "Checking ${endpoint} JSON response... "
    
    local response=$(curl -s --max-time ${TIMEOUT} "${API_URL}${endpoint}")
    local value=$(echo "${response}" | python3 -c "import sys, json; print(json.load(sys.stdin).get('${field}', ''))" 2>/dev/null)
    
    if [ "${value}" = "${expected_value}" ]; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED (expected: ${expected_value}, got: ${value})${NC}"
        return 1
    fi
}

check_database() {
    echo -n "Checking database connection... "
    
    if docker exec parking-db pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        return 1
    fi
}

check_disk_space() {
    echo -n "Checking disk space... "
    
    local usage=$(df -h / | awk 'NR==2 {print $5}' | cut -d'%' -f1)
    if [ "${usage}" -lt 90 ]; then
        echo -e "${GREEN}OK (${usage}%)${NC}"
        return 0
    else
        echo -e "${RED}CRITICAL (${usage}%)${NC}"
        return 1
    fi
}

# Main health check
main() {
    echo "Starting health check for Parking Management API"
    echo "================================================"
    
    local failed=0
    
    # Basic health endpoint
    if ! check_endpoint "/health" 200; then
        failed=$((failed + 1))
    fi
    
    # API documentation
    if ! check_endpoint "/docs" 200; then
        failed=$((failed + 1))
    fi
    
    # Database check
    if ! check_database; then
        failed=$((failed + 1))
    fi
    
    # Disk space
    if ! check_disk_space; then
        failed=$((failed + 1))
    fi
    
    echo "================================================"
    
    if [ ${failed} -eq 0 ]; then
        echo -e "${GREEN}All health checks passed${NC}"
        exit 0
    else
        echo -e "${RED}${failed} health check(s) failed${NC}"
        exit 1
    fi
}

# Run main function
main