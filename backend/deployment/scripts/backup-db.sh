#!/bin/bash

# Database Backup Script

set -e

BACKUP_DIR="/var/backups/parking-management"
DB_NAME="parking_db"
DB_USER="postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Perform backup
echo "Starting database backup at $(date)"
docker exec parking-db pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz"

# Verify backup
if [ -f "${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz" ]; then
    echo "Backup created successfully: backup_${TIMESTAMP}.sql.gz"
    
    # Calculate backup size
    SIZE=$(du -h "${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz" | cut -f1)
    echo "Backup size: ${SIZE}"
    
    # Clean old backups
    find "${BACKUP_DIR}" -name "backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
    echo "Cleaned backups older than ${RETENTION_DAYS} days"
else
    echo "Backup failed!"
    exit 1
fi

# Optional: Upload to S3 or other storage
if [ -n "${AWS_S3_BUCKET}" ]; then
    aws s3 cp "${BACKUP_DIR}/backup_${TIMESTAMP}.sql.gz" "s3://${AWS_S3_BUCKET}/backups/"
    echo "Backup uploaded to S3"
fi

echo "Backup completed at $(date)"