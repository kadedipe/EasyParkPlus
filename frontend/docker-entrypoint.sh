#!/bin/sh
set -e

echo "==========================================="
echo "🚀 Parking Management System - Frontend"
echo "==========================================="
echo "Environment: $NODE_ENV"
echo "Version: $(node -p "require('./package.json').version")"
echo "==========================================="

# Function to check if a command exists
command_exists() {
    command -v "$@" > /dev/null 2>&1
}

# Function to wait for a service
wait_for_service() {
    local host="$1"
    local port="$2"
    local service="$3"
    
    echo "⏳ Waiting for $service..."
    while ! nc -z "$host" "$port"; do
        sleep 1
    done
    echo "✅ $service is ready"
}

# Wait for backend services if needed
if [ "$WAIT_FOR_BACKEND" = "true" ]; then
    wait_for_service "${BACKEND_HOST:-backend}" "${BACKEND_PORT:-8000}" "Backend API"
fi

# Generate runtime config if needed
if [ "$NODE_ENV" = "production" ] && command_exists envsubst; then
    echo "📝 Generating runtime configuration..."
    envsubst < /usr/share/nginx/html/config.template.js > /usr/share/nginx/html/config.js
fi

# Execute the main command
echo "🚀 Starting application..."
exec "$@"