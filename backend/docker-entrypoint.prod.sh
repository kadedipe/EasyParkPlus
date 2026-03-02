#!/bin/sh
set -e

echo "🚀 Parking Management System - Backend Production Container"

# Run database migrations
echo "🔄 Running database migrations..."
alembic upgrade head

# Start application with proper settings
echo "🚀 Starting application..."
exec "$@"