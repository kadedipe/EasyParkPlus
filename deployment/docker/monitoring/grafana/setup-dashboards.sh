#!/bin/bash
# Setup script for Grafana dashboards and datasources

set -e

echo "Setting up Grafana monitoring dashboards..."

DASHBOARDS_DIR="/etc/grafana/provisioning/dashboards"
DATASOURCES_DIR="/etc/grafana/provisioning/datasources"
PLUGINS_DIR="/var/lib/grafana/plugins"

# Create necessary directories
mkdir -p "$DASHBOARDS_DIR/databases"
mkdir -p "$DASHBOARDS_DIR/caching"
mkdir -p "$DASHBOARDS_DIR/apis"
mkdir -p "$DASHBOARDS_DIR/infrastructure"
mkdir -p "$DATASOURCES_DIR"

# Function to download a dashboard from Grafana.com
download_dashboard() {
    local dashboard_id="$1"
    local output_file="$2"
    
    echo "Downloading dashboard $dashboard_id..."
    curl -s "https://grafana.com/api/dashboards/$dashboard_id/revisions/latest/download" \
        -o "$output_file" 2>/dev/null || true
    
    if [ -f "$output_file" ] && [ -s "$output_file" ]; then
        echo "Downloaded dashboard to $output_file"
    else
        echo "Failed to download dashboard $dashboard_id, using fallback"
    fi
}

# Download community dashboards if not present
if [ ! -f "$DASHBOARDS_DIR/databases/postgresql-overview.json" ]; then
    download_dashboard "9628" "$DASHBOARDS_DIR/databases/postgresql-overview.json"
fi

if [ ! -f "$DASHBOARDS_DIR/caching/redis-overview.json" ]; then
    download_dashboard "763" "$DASHBOARDS_DIR/caching/redis-overview.json"
fi

if [ ! -f "$DASHBOARDS_DIR/infrastructure/docker-overview.json" ]; then
    download_dashboard "893" "$DASHBOARDS_DIR/infrastructure/docker-overview.json"
fi

# Install Grafana plugins
echo "Installing Grafana plugins..."
grafana-cli plugins install grafana-piechart-panel
grafana-cli plugins install vonage-status-panel
grafana-cli plugins install marcusolsson-hourly-heatmap-panel

# Set proper permissions
chown -R grafana:grafana "$DASHBOARDS_DIR"
chown -R grafana:grafana "$DATASOURCES_DIR"
chown -R grafana:grafana "$PLUGINS_DIR"

echo "Grafana setup completed successfully!"

# Wait for Grafana to be ready
echo "Waiting for Grafana to be ready..."
until curl -s http://localhost:3000/api/health > /dev/null; do
    echo "Grafana not ready yet, waiting..."
    sleep 5
done

# Create API key for automation (optional)
if [ -n "$GRAFANA_ADMIN_PASSWORD" ]; then
    echo "Creating API key for automation..."
    
    # Wait for Grafana to be fully initialized
    sleep 10
    
    API_KEY_RESPONSE=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"name":"automation","role":"Admin"}' \
        "http://admin:${GRAFANA_ADMIN_PASSWORD}@localhost:3000/api/auth/keys")
    
    API_KEY=$(echo "$API_KEY_RESPONSE" | jq -r '.key // empty')
    
    if [ -n "$API_KEY" ]; then
        echo "API Key created: $API_KEY"
        echo "GRAFANA_API_KEY=$API_KEY" > /etc/grafana/api.env
        chmod 600 /etc/grafana/api.env
    fi
fi

echo "Grafana is ready! Access at http://localhost:3000"
echo "Default credentials: admin / ${GRAFANA_ADMIN_PASSWORD:-admin}"