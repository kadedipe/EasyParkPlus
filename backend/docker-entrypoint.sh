#!/bin/bash
set -e

echo "🚀 Parking Management System - Backend Development Container"
echo "=========================================================="

# Wait for database
echo "⏳ Waiting for database..."
while ! nc -z ${DB_HOST:-postgres} ${DB_PORT:-5432}; do
    sleep 1
done
echo "✅ Database is ready!"

# Wait for Redis
echo "⏳ Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-redis} ${REDIS_PORT:-6379}; do
    sleep 1
done
echo "✅ Redis is ready!"

# Wait for RabbitMQ
echo "⏳ Waiting for RabbitMQ..."
while ! nc -z ${RABBITMQ_HOST:-rabbitmq} ${RABBITMQ_PORT:-5672}; do
    sleep 1
done
echo "✅ RabbitMQ is ready!"

# Run database migrations
echo "🔄 Running database migrations..."
alembic upgrade head

# Create initial data
echo "📦 Creating initial data..."
python scripts/init_db.py

# Start application
echo "🚀 Starting application..."
exec "$@"