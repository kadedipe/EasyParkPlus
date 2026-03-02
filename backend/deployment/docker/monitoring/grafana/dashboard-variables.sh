#!/bin/bash
# Dashboard variables setup script for Parking API

set -e

echo "Setting up dashboard variables for Parking API..."

# Configuration
GRAFANA_URL=${GRAFANA_URL:-http://localhost:3000}
GRAFANA_USER=${GRAFANA_USER:-admin}
GRAFANA_PASSWORD=${GRAFANA_PASSWORD:-admin}
DASHBOARD_UID="parking-api-performance"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get API key
get_api_key() {
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
        -d '{"name":"variables-setup","role":"Admin"}' \
        "${GRAFANA_URL}/api/auth/keys")
    
    echo "$response" | jq -r '.key'
}

# Get dashboard JSON
get_dashboard() {
    local uid="$1"
    
    curl -s -X GET \
        -H "Authorization: Bearer ${API_KEY}" \
        "${GRAFANA_URL}/api/dashboards/uid/${uid}"
}

# Update dashboard
update_dashboard() {
    local uid="$1"
    local dashboard_json="$2"
    
    curl -s -X POST \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$dashboard_json" \
        "${GRAFANA_URL}/api/dashboards/db"
}

# Update variables with dynamic values
update_variables() {
    echo "Updating dashboard variables..."
    
    # Get current dashboard
    local dashboard=$(get_dashboard "$DASHBOARD_UID")
    
    # Get available endpoints from Prometheus
    local endpoints=$(curl -s "${PROMETHEUS_URL}/api/v1/series?match[]=parking_api_http_requests_total" | \
        jq -r '.data[].endpoint // empty' | sort | uniq)
    
    # Get available methods
    local methods=$(curl -s "${PROMETHEUS_URL}/api/v1/series?match[]=parking_api_http_requests_total" | \
        jq -r '.data[].method // empty' | sort | uniq)
    
    # Update dashboard JSON with dynamic options
    local updated_dashboard=$(echo "$dashboard" | jq '
        .dashboard.templating.list = [
            {
                "current": {
                    "selected": true,
                    "text": "Prometheus",
                    "value": "Prometheus"
                },
                "hide": 0,
                "includeAll": false,
                "label": "Datasource",
                "multi": false,
                "name": "datasource",
                "options": [],
                "query": "prometheus",
                "queryValue": "",
                "refresh": 1,
                "regex": "",
                "skipUrlSync": false,
                "type": "datasource"
            },
            {
                "current": {
                    "selected": true,
                    "text": "All",
                    "value": "$__all"
                },
                "hide": 0,
                "includeAll": true,
                "label": "Endpoint",
                "multi": true,
                "name": "endpoint",
                "options": [
                    {
                        "selected": true,
                        "text": "All",
                        "value": "$__all"
                    }
                ] + ($ENDPOINTS | split("\n") | map(select(. != "") | {
                    "selected": false,
                    "text": .,
                    "value": .
                })),
                "query": {
                    "query": "label_values(parking_api_http_requests_total, endpoint)",
                    "refId": "StandardVariableQuery"
                },
                "refresh": 2,
                "regex": "",
                "skipUrlSync": false,
                "type": "query"
            },
            {
                "current": {
                    "selected": true,
                    "text": "5m",
                    "value": "5m"
                },
                "hide": 0,
                "label": "Time Range",
                "multi": false,
                "name": "time_range",
                "options": [
                    {"selected": false, "text": "1m", "value": "1m"},
                    {"selected": true, "text": "5m", "value": "5m"},
                    {"selected": false, "text": "15m", "value": "15m"},
                    {"selected": false, "text": "30m", "value": "30m"},
                    {"selected": false, "text": "1h", "value": "1h"},
                    {"selected": false, "text": "6h", "value": "6h"}
                ],
                "query": "",
                "refresh": 2,
                "skipUrlSync": false,
                "type": "custom"
            },
            {
                "current": {
                    "selected": true,
                    "text": "All",
                    "value": "$__all"
                },
                "hide": 0,
                "includeAll": true,
                "label": "HTTP Method",
                "multi": true,
                "name": "method",
                "options": [
                    {
                        "selected": true,
                        "text": "All",
                        "value": "$__all"
                    }
                ] + ($METHODS | split("\n") | map(select(. != "") | {
                    "selected": false,
                    "text": .,
                    "value": .
                })),
                "query": {
                    "query": "label_values(parking_api_http_requests_total, method)",
                    "refId": "StandardVariableQuery"
                },
                "refresh": 2,
                "regex": "",
                "skipUrlSync": false,
                "type": "query"
            },
            {
                "current": {
                    "selected": true,
                    "text": "All",
                    "value": "$__all"
                },
                "hide": 0,
                "includeAll": true,
                "label": "Status Code",
                "multi": true,
                "name": "status",
                "options": [
                    {
                        "selected": true,
                        "text": "All",
                        "value": "$__all"
                    },
                    {
                        "selected": false,
                        "text": "2xx",
                        "value": "2.."
                    },
                    {
                        "selected": false,
                        "text": "3xx",
                        "value": "3.."
                    },
                    {
                        "selected": false,
                        "text": "4xx",
                        "value": "4.."
                    },
                    {
                        "selected": false,
                        "text": "5xx",
                        "value": "5.."
                    }
                ],
                "query": {
                    "query": "label_values(parking_api_http_requests_total, status)",
                    "refId": "StandardVariableQuery"
                },
                "refresh": 2,
                "regex": "",
                "skipUrlSync": false,
                "type": "query"
            }
        ]
    ' --arg ENDPOINTS "$endpoints" --arg METHODS "$methods")
    
    # Update dashboard
    local response=$(update_dashboard "$DASHBOARD_UID" "$updated_dashboard")
    
    if echo "$response" | jq -e '.status == "success"' > /dev/null; then
        echo -e "${GREEN}Dashboard variables updated successfully${NC}"
    else
        echo -e "${RED}Failed to update dashboard variables${NC}"
        echo "$response" | jq .
    fi
}

# Main execution
main() {
    # Check dependencies
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}Error: jq is required${NC}"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}Error: curl is required${NC}"
        exit 1
    fi
    
    # Get API key
    API_KEY=$(get_api_key)
    if [ -z "$API_KEY" ]; then
        echo -e "${RED}Failed to get API key${NC}"
        exit 1
    fi
    
    # Update variables
    update_variables
    
    echo -e "${GREEN}Dashboard setup completed${NC}"
}

# Run main function
main "$@"