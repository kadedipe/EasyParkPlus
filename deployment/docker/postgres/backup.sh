#!/bin/bash
# Database backup script for PostgreSQL

set -e

BACKUP_DIR="/var/lib/postgresql/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_${TIMESTAMP}.sql.gz"

# Ensure backup directory exists
mkdir -p ${BACKUP_DIR}

echo "Starting database backup at $(date)"

# Perform the backup
pg_dump -U ${POSTGRES_USER:-parking_user} ${POSTGRES_DB:-parking_db} | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

# Remove backups older than 7 days
find ${BACKUP_DIR} -name "backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}"
echo "Backup size: $(du -h ${BACKUP_DIR}/${BACKUP_FILE} | cut -f1)"