#!/bin/bash
# Dashboard manager for Grafana - Import/Export/Backup

set -e

# Configuration
GRAFANA_URL=${GRAFANA_URL:-http://localhost:3000}
GRAFANA_USER=${GRAFANA_USER:-admin}
GRAFANA_PASSWORD=${GRAFANA_PASSWORD:-admin}
BACKUP_DIR=${BACKUP_DIR:-/var/lib/grafana/backups}
DATE=$(date +%Y%m%d_%H%M%S)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Log function
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check dependencies
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        log "${RED}Error: jq is required but not installed${NC}"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log "${RED}Error: curl is required but not installed${NC}"
        exit 1
    fi
}

# Test Grafana connection
test_connection() {
    log "Testing connection to Grafana..."
    if curl -s -f "${GRAFANA_URL}/api/health" > /dev/null; then
        log "${GREEN}Connected to Grafana successfully${NC}"
        return 0
    else
        log "${RED}Failed to connect to Grafana${NC}"
        return 1
    fi
}

# Get API key or create one
get_api_key() {
    if [ -n "$GRAFANA_API_KEY" ]; then
        echo "$GRAFANA_API_KEY"
        return
    fi
    
    # Try to get existing API key
    local response=$(curl -s -X GET \
        -H "Content-Type: application/json" \
        -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
        "${GRAFANA_URL}/api/auth/keys")
    
    local key_id=$(echo "$response" | jq -r '.[] | select(.name=="dashboard-manager") | .id // empty')
    
    if [ -n "$key_id" ]; then
        # Delete existing key
        curl -s -X DELETE \
            -H "Content-Type: application/json" \
            -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
            "${GRAFANA_URL}/api/auth/keys/${key_id}" > /dev/null
    fi
    
    # Create new API key
    local key_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
        -d '{"name":"dashboard-manager","role":"Admin"}' \
        "${GRAFANA_URL}/api/auth/keys")
    
    echo "$key_response" | jq -r '.key'
}

# Export all dashboards
export_dashboards() {
    local output_dir="${BACKUP_DIR}/dashboards_${DATE}"
    
    log "Exporting dashboards to ${output_dir}..."
    mkdir -p "$output_dir"
    
    # Get all dashboards
    local dashboards=$(curl -s -X GET \
        -H "Authorization: Bearer ${API_KEY}" \
        "${GRAFANA_URL}/api/search?type=dash-db")
    
    local count=$(echo "$dashboards" | jq length)
    log "Found ${count} dashboards"
    
    for i in $(seq 0 $((count - 1))); do
        local uid=$(echo "$dashboards" | jq -r ".[$i].uid")
        local title=$(echo "$dashboards" | jq -r ".[$i].title")
        
        log "Exporting: ${title}"
        
        # Get dashboard JSON
        local dashboard_json=$(curl -s -X GET \
            -H "Authorization: Bearer ${API_KEY}" \
            "${GRAFANA_URL}/api/dashboards/uid/${uid}")
        
        # Extract dashboard data
        local dashboard_data=$(echo "$dashboard_json" | jq '.dashboard')
        
        # Save to file
        local filename=$(echo "$title" | tr ' ' '_' | tr '/' '_' | tr ':' '_')
        echo "$dashboard_data" | jq '.' > "${output_dir}/${filename}.json"
        
        # Add metadata
        echo "$dashboard_json" | jq '{meta: .meta}' > "${output_dir}/${filename}.meta.json"
    done
    
    log "${GREEN}Exported ${count} dashboards to ${output_dir}${NC}"
    
    # Create archive
    tar -czf "${BACKUP_DIR}/dashboards_${DATE}.tar.gz" -C "$output_dir" .
    log "Created archive: ${BACKUP_DIR}/dashboards_${DATE}.tar.gz"
    
    # Cleanup
    rm -rf "$output_dir"
}

# Import dashboards from directory
import_dashboards() {
    local import_dir="$1"
    
    if [ ! -d "$import_dir" ]; then
        log "${RED}Import directory not found: ${import_dir}${NC}"
        exit 1
    fi
    
    log "Importing dashboards from ${import_dir}..."
    
    local imported=0
    local failed=0
    
    for file in "${import_dir}"/*.json; do
        if [[ "$file" == *".meta.json" ]]; then
            continue
        fi
        
        local filename=$(basename "$file" .json)
        local title="$filename"
        
        log "Importing: ${title}"
        
        # Read dashboard JSON
        local dashboard_data=$(cat "$file" | jq '.')
        
        # Prepare payload
        local payload=$(jq -n \
            --argjson dashboard "$dashboard_data" \
            '{
                dashboard: $dashboard,
                overwrite: true,
                message: "Imported via dashboard-manager",
                folderId: 0
            }')
        
        # Import dashboard
        local response=$(curl -s -X POST \
            -H "Authorization: Bearer ${API_KEY}" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "${GRAFANA_URL}/api/dashboards/db")
        
        local status=$(echo "$response" | jq -r '.status // "error"')
        
        if [ "$status" = "success" ]; then
            log "${GREEN}  ✓ Successfully imported${NC}"
            ((imported++))
        else
            log "${RED}  ✗ Failed to import${NC}"
            ((failed++))
        fi
    done
    
    log "Import completed: ${imported} successful, ${failed} failed"
}

# Backup datasources
backup_datasources() {
    local output_file="${BACKUP_DIR}/datasources_${DATE}.json"
    
    log "Backing up datasources to ${output_file}..."
    
    # Get all datasources
    local datasources=$(curl -s -X GET \
        -H "Authorization: Bearer ${API_KEY}" \
        "${GRAFANA_URL}/api/datasources")
    
    echo "$datasources" | jq '.' > "$output_file"
    
    log "${GREEN}Backed up datasources to ${output_file}${NC}"
}

# Restore datasources
restore_datasources() {
    local input_file="$1"
    
    if [ ! -f "$input_file" ]; then
        log "${RED}Input file not found: ${input_file}${NC}"
        exit 1
    fi
    
    log "Restoring datasources from ${input_file}..."
    
    # Read datasources
    local datasources=$(cat "$input_file" | jq -c '.[]')
    
    local restored=0
    local failed=0
    
    echo "$datasources" | while read -r ds; do
        local name=$(echo "$ds" | jq -r '.name')
        
        log "Restoring datasource: ${name}"
        
        # Check if datasource exists
        local existing_id=$(curl -s -X GET \
            -H "Authorization: Bearer ${API_KEY}" \
            "${GRAFANA_URL}/api/datasources/name/${name}" | jq -r '.id // empty')
        
        if [ -n "$existing_id" ]; then
            # Update existing
            local response=$(curl -s -X PUT \
                -H "Authorization: Bearer ${API_KEY}" \
                -H "Content-Type: application/json" \
                -d "$ds" \
                "${GRAFANA_URL}/api/datasources/${existing_id}")
        else
            # Create new
            local response=$(curl -s -X POST \
                -H "Authorization: Bearer ${API_KEY}" \
                -H "Content-Type: application/json" \
                -d "$ds" \
                "${GRAFANA_URL}/api/datasources")
        fi
        
        local id=$(echo "$response" | jq -r '.id // empty')
        
        if [ -n "$id" ]; then
            log "${GREEN}  ✓ Successfully restored${NC}"
            ((restored++))
        else
            log "${RED}  ✗ Failed to restore${NC}"
            ((failed++))
        fi
    done
    
    log "Restore completed: ${restored} successful, ${failed} failed"
}

# List all dashboards
list_dashboards() {
    log "Listing all dashboards..."
    
    local dashboards=$(curl -s -X GET \
        -H "Authorization: Bearer ${API_KEY}" \
        "${GRAFANA_URL}/api/search?type=dash-db")
    
    echo "$dashboards" | jq -r '.[] | "\(.title) (UID: \(.uid), ID: \(.id))"' | sort
}

# Delete dashboard by UID
delete_dashboard() {
    local uid="$1"
    
    if [ -z "$uid" ]; then
        log "${RED}Dashboard UID is required${NC}"
        exit 1
    fi
    
    log "Deleting dashboard with UID: ${uid}"
    
    local response=$(curl -s -X DELETE \
        -H "Authorization: Bearer ${API_KEY}" \
        "${GRAFANA_URL}/api/dashboards/uid/${uid}")
    
    if echo "$response" | jq -e '.message' > /dev/null; then
        log "${GREEN}Dashboard deleted successfully${NC}"
    else
        log "${RED}Failed to delete dashboard${NC}"
    fi
}

# Main function
main() {
    check_dependencies
    
    if ! test_connection; then
        exit 1
    fi
    
    # Get API key
    API_KEY=$(get_api_key)
    if [ -z "$API_KEY" ]; then
        log "${RED}Failed to obtain API key${NC}"
        exit 1
    fi
    
    # Ensure backup directory exists
    mkdir -p "$BACKUP_DIR"
    
    case "${1:-}" in
        export)
            export_dashboards
            ;;
        import)
            import_dashboards "${2:-/etc/grafana/provisioning/dashboards}"
            ;;
        backup-datasources)
            backup_datasources
            ;;
        restore-datasources)
            restore_datasources "$2"
            ;;
        list)
            list_dashboards
            ;;
        delete)
            delete_dashboard "$2"
            ;;
        setup)
            # Initial setup
            export_dashboards
            backup_datasources
            ;;
        *)
            echo "Usage: $0 {export|import [dir]|backup-datasources|restore-datasources [file]|list|delete [uid]|setup}"
            echo ""
            echo "Examples:"
            echo "  $0 export                          # Export all dashboards"
            echo "  $0 import /path/to/dashboards     # Import dashboards from directory"
            echo "  $0 backup-datasources             # Backup datasources"
            echo "  $0 restore-datasources file.json  # Restore datasources from file"
            echo "  $0 list                           # List all dashboards"
            echo "  $0 delete abc123                  # Delete dashboard by UID"
            echo "  $0 setup                          # Initial setup (export + backup)"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"