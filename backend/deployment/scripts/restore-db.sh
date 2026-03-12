#!/bin/bash

# Database Restore Script

set -e

BACKUP_DIR="/var/backups/parking-management"
DB_NAME="parking_db"
DB_USER="postgres"

# List available backups
echo "Available backups:"
ls -lh "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || echo "No backups found"

# Get backup file from user
read -p "Enter backup filename to restore: " BACKUP_FILE

if [ ! -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    echo "Backup file not found!"
    exit 1
fi

# Confirm restore
echo "WARNING: This will overwrite the current database!"
read -p "Are you sure you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Stop the application
echo "Stopping application..."
docker-compose -f ../docker-compose.prod.yml stop api

# Drop and recreate database
echo "Dropping existing database..."
docker exec parking-db dropdb -U "${DB_USER}" --if-exists "${DB_NAME}"
docker exec parking-db createdb -U "${DB_USER}" "${DB_NAME}"

# Restore from backup
echo "Restoring from backup..."
gunzip -c "${BACKUP_DIR}/${BACKUP_FILE}" | docker exec -i parking-db psql -U "${DB_USER}" "${DB_NAME}"

# Start the application
echo "Starting application..."
docker-compose -f ../docker-compose.prod.yml start api

echo "Database restore completed successfully"