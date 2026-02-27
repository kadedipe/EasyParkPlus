markdown
# Parking Management System - Backup and Restore Guide

## Document Information
| | |
|---|---|
| **Document Version** | 1.0.0 |
| **Last Updated** | 2024-01-15 |
| **Database** | PostgreSQL 14+ |
| **Backup Tool** | pg_dump, pg_basebackup, WAL archiving |
| **Author** | Parking Management System Team |

## Document Purpose
This guide provides comprehensive instructions for backing up and restoring the Parking Management System database. It covers backup strategies, procedures, automation, disaster recovery, and best practices for both routine operations and emergency situations.

---

## Table of Contents
1. [Introduction](#introduction)
2. [Backup Strategies](#backup-strategies)
3. [Prerequisites](#prerequisites)
4. [Backup Methods](#backup-methods)
   - [Logical Backups (pg_dump)](#logical-backups-pgdump)
   - [Physical Backups (pg_basebackup)](#physical-backups-pgbasebackup)
   - [Continuous Archiving (WAL)](#continuous-archiving-wal)
   - [Cloud Backups](#cloud-backups)
5. [Automated Backup Procedures](#automated-backup-procedures)
6. [Restore Procedures](#restore-procedures)
   - [Point-in-Time Recovery](#point-in-time-recovery)
   - [Full Database Restore](#full-database-restore)
   - [Partial Restore](#partial-restore)
7. [Disaster Recovery](#disaster-recovery)
8. [Verification and Testing](#verification-and-testing)
9. [Monitoring and Alerts](#monitoring-and-alerts)
10. [Retention Policy](#retention-policy)
11. [Security Considerations](#security-considerations)
12. [Troubleshooting](#troubleshooting)
13. [Appendix](#appendix)

---

## Introduction

### Why Backup is Critical
The Parking Management System contains critical business data including:
- User accounts and personal information
- Reservation history and financial transactions
- Parking spot availability and schedules
- Audit logs for compliance
- Configuration and business rules

### Backup Philosophy
Our backup strategy follows these principles:
- **3-2-1 Rule**: At least 3 copies, on 2 different media, 1 off-site
- **RPO (Recovery Point Objective)**: Maximum 1 hour data loss
- **RTO (Recovery Time Objective)**: Maximum 4 hours recovery time
- **Encryption**: All backups must be encrypted
- **Verification**: Regular restore testing
- **Automation**: Minimal manual intervention

### Recovery Objectives
| Metric | Target | Description |
|--------|--------|-------------|
| RPO | 1 hour | Maximum acceptable data loss |
| RTO | 4 hours | Maximum time to restore |
| Backup Frequency | Hourly | How often backups are taken |
| Retention | 30 days | How long backups are kept |
| Testing Frequency | Monthly | How often restore is tested |

---

## Prerequisites

### System Requirements
- PostgreSQL 14+ with WAL archiving enabled
- Sufficient disk space (at least 2x database size)
- Backup storage location (local and remote)
- Monitoring and alerting system
- Encryption keys for secure backups

### Required Permissions
```sql
-- Create backup user with minimal privileges
CREATE USER backup_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE parking_db TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO backup_user;
GRANT USAGE ON SCHEMA public TO backup_user;
GRANT pg_read_all_settings TO backup_user;
GRANT pg_read_all_stats TO backup_user;

-- For WAL archiving
GRANT EXECUTE ON FUNCTION pg_start_backup(text) TO backup_user;
GRANT EXECUTE ON FUNCTION pg_stop_backup() TO backup_user;
PostgreSQL Configuration
conf
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'test ! -f /backup/wal/%f && cp %p /backup/wal/%f'
archive_timeout = 300
max_wal_senders = 10
wal_keep_segments = 32
Directory Structure
text
/backup/
├── daily/
│   ├── parking_db_20240115_0000.sql.gz
│   ├── parking_db_20240115_1200.sql.gz
│   └── ...
├── weekly/
│   ├── parking_db_2024_week02.sql.gz
│   └── ...
├── monthly/
│   ├── parking_db_2024_01.sql.gz
│   └── ...
├── wal/
│   ├── 000000010000000000000001
│   ├── 000000010000000000000002
│   └── ...
├── basebackup/
│   ├── base_20240115_0000.tar
│   └── ...
└── encrypted/
    └── [encrypted backups]
Backup Methods
Logical Backups (pg_dump)
Full Database Backup
bash
#!/bin/bash
# full_backup.sh - Full database backup using pg_dump

DB_NAME="parking_db"
DB_USER="backup_user"
BACKUP_DIR="/backup/daily"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${DATE}.sql"

# Set PGPASSWORD environment variable
export PGPASSWORD="secure_password"

# Perform backup
pg_dump -h localhost -U $DB_USER -d $DB_NAME \
    --format=custom \
    --verbose \
    --file="${BACKUP_FILE}.dump" \
    --no-owner \
    --no-privileges \
    2> "${BACKUP_DIR}/backup_${DATE}.log"

# Compress backup
gzip "${BACKUP_FILE}.dump"

# Create checksum
sha256sum "${BACKUP_FILE}.dump.gz" > "${BACKUP_FILE}.dump.gz.sha256"

# Cleanup old backups (keep last 48 hours)
find $BACKUP_DIR -name "*.dump.gz" -type f -mtime +2 -delete
find $BACKUP_DIR -name "*.log" -type f -mtime +2 -delete

echo "Backup completed: ${BACKUP_FILE}.dump.gz"
Selective Backup (Specific Tables)
bash
#!/bin/bash
# selective_backup.sh - Backup specific tables

# Backup critical tables
pg_dump -h localhost -U backup_user -d parking_db \
    --table=users \
    --table=reservations \
    --table=payments \
    --format=custom \
    --file=/backup/selective/critical_tables_$(date +%Y%m%d).dump

# Backup configuration tables
pg_dump -h localhost -U backup_user -d parking_db \
    --table=parking_spots \
    --table=rates \
    --table=configuration \
    --format=custom \
    --file=/backup/selective/config_tables_$(date +%Y%m%d).dump
Schema-Only Backup
bash
#!/bin/bash
# schema_backup.sh - Backup database schema only

pg_dump -h localhost -U backup_user -d parking_db \
    --schema-only \
    --format=plain \
    --file=/backup/schema/parking_schema_$(date +%Y%m%d).sql
Physical Backups (pg_basebackup)
Full Physical Backup
bash
#!/bin/bash
# physical_backup.sh - Physical backup using pg_basebackup

BACKUP_DIR="/backup/basebackup"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/base_${DATE}"

# Create physical backup
pg_basebackup -h localhost -U backup_user \
    -D $BACKUP_PATH \
    -Ft -z -P \
    --wal-method=stream \
    --label="parking_full_backup_${DATE}" \
    2> "${BACKUP_DIR}/backup_${DATE}.log"

# Create backup metadata
cat > "${BACKUP_PATH}/backup_info.json" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "database": "parking_db",
    "version": "$(psql -h localhost -U backup_user -d parking_db -t -c 'SELECT version()')",
    "size": "$(du -sh $BACKUP_PATH | cut -f1)",
    "wal_start": "$(cat $BACKUP_PATH/backup_label | grep 'START WAL' | cut -d' ' -f3)"
}
EOF

# Create checksum
tar -tzf "${BACKUP_PATH}.tar.gz" | xargs sha256sum > "${BACKUP_PATH}.sha256"

echo "Physical backup completed: ${BACKUP_PATH}.tar.gz"
Continuous Archiving (WAL)
WAL Archiving Script
bash
#!/bin/bash
# archive_wal.sh - Archive WAL files

WAL_SOURCE="/var/lib/postgresql/14/main/pg_wal"
WAL_ARCHIVE="/backup/wal"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Archive current WAL
psql -h localhost -U backup_user -d parking_db -c "SELECT pg_switch_wal();"

# Copy WAL files to archive
rsync -av --remove-source-files ${WAL_SOURCE}/archive_status/ ${WAL_ARCHIVE}/archive_status/
rsync -av --remove-source-files ${WAL_SOURCE}/*.partial ${WAL_ARCHIVE}/ 2>/dev/null
rsync -av --remove-source-files ${WAL_SOURCE}/*.backup ${WAL_ARCHIVE}/

# Compress old WAL files
find $WAL_ARCHIVE -name "00*" -type f -mtime +1 -exec gzip {} \;

# Clean up WAL files older than 7 days
find $WAL_ARCHIVE -name "*.gz" -type f -mtime +7 -delete

# Log archive status
echo "$TIMESTAMP: WAL archive completed" >> /var/log/wal_archive.log
WAL Archive Monitoring
python
#!/usr/bin/env python3
# monitor_wal.py - Monitor WAL archiving

import os
import time
import smtplib
from datetime import datetime, timedelta
from pathlib import Path

WAL_DIR = "/backup/wal"
THRESHOLD_MINUTES = 15
ALERT_EMAIL = "dba@example.com"

def get_latest_wal():
    """Get timestamp of latest WAL file."""
    wal_files = sorted(Path(WAL_DIR).glob("00*"))
    if not wal_files:
        return None
    
    latest = max(wal_files, key=lambda f: f.stat().st_mtime)
    return datetime.fromtimestamp(latest.stat().st_mtime)

def send_alert(message):
    """Send alert email."""
    # Implementation depends on your email system
    print(f"ALERT: {message}")

def main():
    latest = get_latest_wal()
    if not latest:
        send_alert("No WAL files found!")
        return
    
    age = datetime.now() - latest
    if age > timedelta(minutes=THRESHOLD_MINUTES):
        send_alert(f"WAL archiving delayed: last WAL {age.total_seconds()/60:.1f} minutes ago")

if __name__ == "__main__":
    main()
Cloud Backups
AWS S3 Backup Script
bash
#!/bin/bash
# s3_backup.sh - Upload backups to S3

BACKUP_DIR="/backup/daily"
S3_BUCKET="s3://parking-system-backups"
DATE=$(date +%Y%m%d)

# Upload daily backups
aws s3 sync $BACKUP_DIR $S3_BUCKET/daily/ \
    --exclude "*.log" \
    --storage-class STANDARD_IA \
    --metadata "backup-date=${DATE},environment=production"

# Upload WAL archives
aws s3 sync /backup/wal $S3_BUCKET/wal/ \
    --storage-class DEEP_ARCHIVE \
    --metadata "backup-date=${DATE}"

# Upload base backups
aws s3 sync /backup/basebackup $S3_BUCKET/base/ \
    --storage-class STANDARD_IA

# Verify uploads
aws s3 ls $S3_BUCKET/daily/ --recursive --human-readable --summarize

# Set lifecycle policy (optional)
aws s3api put-bucket-lifecycle-configuration \
    --bucket parking-system-backups \
    --lifecycle-configuration file://lifecycle.json
lifecycle.json

json
{
    "Rules": [
        {
            "Id": "DailyBackupRetention",
            "Status": "Enabled",
            "Prefix": "daily/",
            "Expiration": {
                "Days": 30
            }
        },
        {
            "Id": "WALRetention",
            "Status": "Enabled",
            "Prefix": "wal/",
            "Transitions": [
                {
                    "Days": 7,
                    "StorageClass": "GLACIER"
                }
            ],
            "Expiration": {
                "Days": 90
            }
        }
    ]
}
Google Cloud Storage Backup
bash
#!/bin/bash
# gcs_backup.sh - Upload backups to Google Cloud Storage

BACKUP_FILE="/backup/daily/parking_db_$(date +%Y%m%d_%H%M%S).dump.gz"
BUCKET="gs://parking-system-backups"

# Upload to GCS
gsutil cp $BACKUP_FILE $BUCKET/daily/
gsutil cp /backup/wal/* $BUCKET/wal/

# Set retention policy
gsutil retention set 30d $BUCKET/daily/

# Encrypt backup
gcloud kms encrypt \
    --location=global \
    --keyring=backup-keyring \
    --key=backup-key \
    --plaintext-file=$BACKUP_FILE \
    --ciphertext-file=$BACKUP_FILE.enc
Automated Backup Procedures
Cron Jobs
bash
# /etc/cron.d/parking-backups

# Hourly WAL archiving
0 * * * * backup_user /usr/local/bin/archive_wal.sh >> /var/log/wal_archive.log 2>&1

# Daily logical backup at midnight
0 0 * * * backup_user /usr/local/bin/full_backup.sh >> /var/log/backup.log 2>&1

# Weekly physical backup on Sunday at 2 AM
0 2 * * 0 backup_user /usr/local/bin/physical_backup.sh >> /var/log/backup.log 2>&1

# Upload to cloud daily at 3 AM
0 3 * * * backup_user /usr/local/bin/s3_backup.sh >> /var/log/cloud_backup.log 2>&1

# Verify backups daily at 4 AM
0 4 * * * backup_user /usr/local/bin/verify_backups.sh >> /var/log/verify.log 2>&1

# Clean up old backups daily at 5 AM
0 5 * * * backup_user find /backup/daily -name "*.dump.gz" -mtime +2 -delete
0 5 * * * backup_user find /backup/wal -name "*.gz" -mtime +7 -delete
Systemd Timer (Alternative to Cron)
/etc/systemd/system/backup.service

ini
[Unit]
Description=Database Backup Service
After=network.target postgresql.service

[Service]
Type=oneshot
User=backup_user
Group=backup_user
ExecStart=/usr/local/bin/full_backup.sh
StandardOutput=journal
StandardError=journal
/etc/systemd/system/backup.timer

ini
[Unit]
Description=Database Backup Timer
Requires=backup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
Ansible Playbook for Backup Automation
backup-playbook.yml

yaml
---
- name: Configure backup system
  hosts: database_servers
  become: yes
  vars:
    backup_dir: /backup
    retention_days: 30
    s3_bucket: parking-system-backups
    
  tasks:
    - name: Create backup directories
      file:
        path: "{{ item }}"
        state: directory
        owner: backup_user
        group: backup_user
        mode: '0750'
      loop:
        - "{{ backup_dir }}/daily"
        - "{{ backup_dir }}/weekly"
        - "{{ backup_dir }}/wal"
        - "{{ backup_dir }}/basebackup"
    
    - name: Copy backup scripts
      template:
        src: "{{ item }}.j2"
        dest: "/usr/local/bin/{{ item }}"
        mode: '0755'
        owner: backup_user
        group: backup_user
      loop:
        - full_backup.sh
        - archive_wal.sh
        - s3_backup.sh
        - verify_backups.sh
    
    - name: Setup cron jobs
      cron:
        name: "{{ item.name }}"
        minute: "{{ item.minute }}"
        hour: "{{ item.hour }}"
        weekday: "{{ item.weekday | default('*') }}"
        job: "{{ item.job }}"
        user: backup_user
        state: present
      loop:
        - name: Hourly WAL archive
          minute: "0"
          hour: "*"
          job: "/usr/local/bin/archive_wal.sh"
        - name: Daily full backup
          minute: "0"
          hour: "0"
          job: "/usr/local/bin/full_backup.sh"
        - name: Cloud upload
          minute: "0"
          hour: "3"
          job: "/usr/local/bin/s3_backup.sh"
Restore Procedures
Point-in-Time Recovery
Recovery Script
bash
#!/bin/bash
# pitr_recovery.sh - Point-in-time recovery

RESTORE_DIR="/restore/pitr_$(date +%Y%m%d_%H%M%S)"
BASE_BACKUP="/backup/basebackup/base_20240115_0000.tar.gz"
WAL_ARCHIVE="/backup/wal"
TARGET_TIME="2024-01-15 14:30:00 EST"

# Create restore directory
mkdir -p $RESTORE_DIR
cd $RESTORE_DIR

# Extract base backup
tar -xzf $BASE_BACKUP

# Create recovery.conf
cat > recovery.conf << EOF
restore_command = 'cp /backup/wal/%f %p'
recovery_target_time = '$TARGET_TIME'
recovery_target_timeline = 'latest'
pause_at_recovery_target = true
EOF

# Start PostgreSQL with recovery
pg_ctl -D $RESTORE_DIR start

# Wait for recovery to complete
sleep 10

# Check recovery status
psql -d parking_db -c "SELECT pg_is_in_recovery();"
psql -d parking_db -c "SELECT pg_last_xact_replay_timestamp();"

# Promote to master when ready
psql -d parking_db -c "SELECT pg_wal_replay_resume();"
psql -d parking_db -c "SELECT pg_promote();"

echo "Recovery completed to $TARGET_TIME"
Automated Recovery Script
python
#!/usr/bin/env python3
# automated_recovery.py - Automated point-in-time recovery

import os
import sys
import subprocess
import argparse
from datetime import datetime
import shutil

class PITRRecovery:
    def __init__(self, target_time, base_backup=None):
        self.target_time = target_time
        self.base_backup = base_backup or self.find_latest_base_backup()
        self.restore_dir = f"/restore/pitr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def find_latest_base_backup(self):
        """Find the most recent base backup."""
        base_dir = "/backup/basebackup"
        backups = sorted([f for f in os.listdir(base_dir) if f.startswith("base_")])
        return os.path.join(base_dir, backups[-1]) if backups else None
    
    def prepare_recovery(self):
        """Prepare recovery directory."""
        os.makedirs(self.restore_dir, exist_ok=True)
        print(f"Extracting base backup: {self.base_backup}")
        subprocess.run(f"tar -xzf {self.base_backup} -C {self.restore_dir}", shell=True, check=True)
    
    def create_recovery_conf(self):
        """Create recovery.conf file."""
        conf = f"""restore_command = 'cp /backup/wal/%f %p'
recovery_target_time = '{self.target_time}'
recovery_target_timeline = 'latest'
recovery_target_action = 'promote'
"""
        with open(f"{self.restore_dir}/recovery.conf", 'w') as f:
            f.write(conf)
    
    def start_postgres(self):
        """Start PostgreSQL with recovery."""
        cmd = f"pg_ctl -D {self.restore_dir} -l {self.restore_dir}/logfile start"
        subprocess.run(cmd, shell=True, check=True)
    
    def wait_for_recovery(self, timeout=300):
        """Wait for recovery to complete."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            result = subprocess.run(
                "psql -d parking_db -t -c 'SELECT pg_is_in_recovery()'",
                shell=True, capture_output=True, text=True
            )
            if 'f' in result.stdout:
                print("Recovery completed")
                return True
            time.sleep(5)
        return False
    
    def verify_recovery(self):
        """Verify recovered database."""
        checks = [
            "SELECT COUNT(*) FROM users",
            "SELECT COUNT(*) FROM reservations",
            "SELECT MAX(created_at) FROM reservations",
            "SELECT pg_last_xact_replay_timestamp()"
        ]
        
        for check in checks:
            result = subprocess.run(
                f"psql -d parking_db -t -c \"{check}\"",
                shell=True, capture_output=True, text=True
            )
            print(f"{check}: {result.stdout.strip()}")
    
    def run(self):
        """Execute recovery process."""
        print(f"Starting PITR recovery to {self.target_time}")
        self.prepare_recovery()
        self.create_recovery_conf()
        self.start_postgres()
        
        if self.wait_for_recovery():
            self.verify_recovery()
            print(f"Recovery successful to {self.restore_dir}")
        else:
            print("Recovery timeout or failed")
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Point-in-time recovery")
    parser.add_argument("target_time", help="Target time for recovery")
    parser.add_argument("--base-backup", help="Specific base backup to use")
    args = parser.parse_args()
    
    recovery = PITRRecovery(args.target_time, args.base_backup)
    recovery.run()
Full Database Restore
Restore from Logical Backup
bash
#!/bin/bash
# restore_logical.sh - Restore from logical backup

BACKUP_FILE="$1"
DB_NAME="parking_db"
TEMP_DB="parking_db_restore"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Stop application
systemctl stop parking-api

# Create temporary database
dropdb --if-exists $TEMP_DB
createdb $TEMP_DB

# Restore backup
if [[ $BACKUP_FILE == *.dump.gz ]]; then
    gunzip -c $BACKUP_FILE | pg_restore -d $TEMP_DB --verbose
elif [[ $BACKUP_FILE == *.dump ]]; then
    pg_restore -d $TEMP_DB $BACKUP_FILE --verbose
elif [[ $BACKUP_FILE == *.sql ]]; then
    psql -d $TEMP_DB -f $BACKUP_FILE
fi

# Verify restore
psql -d $TEMP_DB -c "SELECT COUNT(*) FROM users;"
psql -d $TEMP_DB -c "SELECT COUNT(*) FROM reservations;"

# Swap databases
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME';"
psql -c "ALTER DATABASE $DB_NAME RENAME TO ${DB_NAME}_old;"
psql -c "ALTER DATABASE $TEMP_DB RENAME TO $DB_NAME;"

# Start application
systemctl start parking-api

# Drop old database after verification
# dropdb ${DB_NAME}_old

echo "Restore completed successfully"
Restore from Physical Backup
bash
#!/bin/bash
# restore_physical.sh - Restore from physical backup

BACKUP_FILE="$1"
RESTORE_DIR="/var/lib/postgresql/14/main_restore"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <base_backup_file>"
    exit 1
fi

# Stop PostgreSQL
systemctl stop postgresql

# Backup current data directory
mv /var/lib/postgresql/14/main /var/lib/postgresql/14/main_backup_$(date +%Y%m%d)

# Create new data directory
mkdir -p /var/lib/postgresql/14/main
chown postgres:postgres /var/lib/postgresql/14/main
chmod 700 /var/lib/postgresql/14/main

# Extract base backup
tar -xzf $BACKUP_FILE -C /var/lib/postgresql/14/main

# Configure recovery
cat > /var/lib/postgresql/14/main/recovery.conf << EOF
restore_command = 'cp /backup/wal/%f %p'
recovery_target_timeline = 'latest'
EOF

# Start PostgreSQL
systemctl start postgresql

# Wait for recovery
sleep 30

# Verify recovery
psql -d parking_db -c "SELECT pg_is_in_recovery();"
psql -d parking_db -c "SELECT pg_last_xact_replay_timestamp();"

echo "Physical restore completed"
Partial Restore
Restore Single Table
bash
#!/bin/bash
# restore_table.sh - Restore a single table

TABLE_NAME="$1"
BACKUP_FILE="$2"
TEMP_DB="temp_restore_$(date +%s)"

if [ -z "$TABLE_NAME" ] || [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <table_name> <backup_file>"
    exit 1
fi

# Create temporary database
createdb $TEMP_DB

# Restore only the specified table
pg_restore -d $TEMP_DB \
    --table=$TABLE_NAME \
    --data-only \
    $BACKUP_FILE

# Dump the table data
pg_dump -d $TEMP_DB \
    --table=$TABLE_NAME \
    --data-only \
    --file="${TABLE_NAME}_restore.sql"

# Apply to main database
psql -d parking_db -f "${TABLE_NAME}_restore.sql"

# Cleanup
dropdb $TEMP_DB
rm "${TABLE_NAME}_restore.sql"

echo "Table $TABLE_NAME restored successfully"
Restore Specific Records
sql
-- restore_records.sql - Restore specific records from backup

-- Create temporary table from backup
CREATE TEMP TABLE reservations_restore AS
SELECT * FROM dblink('dbname=backup_db', 
    'SELECT * FROM reservations WHERE id IN (201, 202, 203)')
AS t(
    id integer, user_id integer, spot_id integer,
    start_time timestamp, end_time timestamp, total_amount numeric
);

-- Update existing records
UPDATE reservations r
SET 
    user_id = rr.user_id,
    spot_id = rr.spot_id,
    start_time = rr.start_time,
    end_time = rr.end_time,
    total_amount = rr.total_amount
FROM reservations_restore rr
WHERE r.id = rr.id;

-- Insert missing records
INSERT INTO reservations (id, user_id, spot_id, start_time, end_time, total_amount)
SELECT id, user_id, spot_id, start_time, end_time, total_amount
FROM reservations_restore rr
WHERE NOT EXISTS (SELECT 1 FROM reservations r WHERE r.id = rr.id);
Disaster Recovery
Disaster Recovery Plan


















DR Site Setup
dr_site_config.sh

bash
#!/bin/bash
# dr_site_config.sh - Configure disaster recovery site

DR_HOST="dr-site.example.com"
DR_DB_NAME="parking_db_dr"
PRIMARY_HOST="primary.example.com"

# Setup streaming replication
cat > setup_replication.sql << EOF
-- On primary server
CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE parking_db TO replicator;

-- Add to pg_hba.conf
host replication replicator $DR_HOST/32 md5
EOF

# On DR server
cat > recovery.conf << EOF
standby_mode = on
primary_conninfo = 'host=$PRIMARY_HOST port=5432 user=replicator password=secure_password'
trigger_file = '/tmp/failover.trigger'
EOF

# Test replication
psql -h $DR_HOST -d $DR_DB_NAME -c "SELECT pg_is_in_recovery();"
psql -h $DR_HOST -d $DR_DB_NAME -c "SELECT pg_last_xlog_receive_location();"
Failover Procedure
failover.sh

bash
#!/bin/bash
# failover.sh - Automatic failover procedure

DR_HOST="dr-site.example.com"
PRIMARY_HOST="primary.example.com"
ALERT_EMAIL="dba@example.com"

# Check if primary is down
if ! pg_isready -h $PRIMARY_HOST -q; then
    echo "$(date): Primary database is down, initiating failover" | mail -s "Failover Started" $ALERT_EMAIL
    
    # Trigger failover on DR
    ssh $DR_HOST "touch /tmp/failover.trigger"
    
    # Wait for promotion
    sleep 30
    
    # Verify DR is now primary
    if ssh $DR_HOST "psql -c 'SELECT pg_is_in_recovery();'" | grep -q 'f'; then
        echo "$(date): DR promoted to primary successfully" | mail -s "Failover Complete" $ALERT_EMAIL
        
        # Update application configuration
        ./update_app_config.sh $DR_HOST
        
        # Redirect traffic
        ./update_load_balancer.sh $DR_HOST
        
        # Start replication from new primary
        ssh $PRIMARY_HOST "pg_basebackup -h $DR_HOST -U replicator -D /var/lib/postgresql/14/main -P -R"
    else
        echo "$(date): Failover failed!" | mail -s "Failover Failed" $ALERT_EMAIL
    fi
fi
Verification and Testing
Backup Verification Script
verify_backups.sh

bash
#!/bin/bash
# verify_backups.sh - Verify backup integrity

BACKUP_DIR="/backup/daily"
LOG_FILE="/var/log/backup_verify.log"
TEST_DB="verify_test_$(date +%s)"

echo "$(date): Starting backup verification" >> $LOG_FILE

# Check recent backups
LATEST_BACKUP=$(ls -t $BACKUP_DIR/*.dump.gz | head -1)
echo "Verifying: $LATEST_BACKUP" >> $LOG_FILE

# Verify checksum
sha256sum -c "${LATEST_BACKUP}.sha256" >> $LOG_FILE 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Checksum verification failed" >> $LOG_FILE
    exit 1
fi

# Create test database
createdb $TEST_DB

# Restore backup to test database
gunzip -c $LATEST_BACKUP | pg_restore -d $TEST_DB >> $LOG_FILE 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Restore verification failed" >> $LOG_FILE
    dropdb $TEST_DB
    exit 1
fi

# Run integrity checks
psql -d $TEST_DB << EOF >> $LOG_FILE 2>&1
-- Check foreign keys
DO \$\$
DECLARE
    rec record;
BEGIN
    FOR rec IN SELECT conname, conrelid::regclass AS table_name
               FROM pg_constraint
               WHERE contype = 'f' AND convalidated = false
    LOOP
        RAISE EXCEPTION 'Unvalidated foreign key: % on %', rec.conname, rec.table_name;
    END LOOP;
END;
\$\$;

-- Check for orphaned records
SELECT COUNT(*) FROM reservations r
WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = r.user_id);

-- Check date constraints
SELECT COUNT(*) FROM reservations WHERE end_time <= start_time;

-- Run analyze
ANALYZE;
EOF

if [ $? -ne 0 ]; then
    echo "ERROR: Integrity checks failed" >> $LOG_FILE
    dropdb $TEST_DB
    exit 1
fi

# Get statistics
echo "Backup Statistics:" >> $LOG_FILE
psql -d $TEST_DB -c "SELECT COUNT(*) as users FROM users;" >> $LOG_FILE
psql -d $TEST_DB -c "SELECT COUNT(*) as reservations FROM reservations;" >> $LOG_FILE
psql -d $TEST_DB -c "SELECT COUNT(*) as payments FROM payments;" >> $LOG_FILE

# Cleanup
dropdb $TEST_DB

echo "$(date): Backup verification completed successfully" >> $LOG_FILE
Automated Testing Schedule
python
#!/usr/bin/env python3
# backup_test_scheduler.py - Schedule backup tests

import schedule
import time
import subprocess
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/backup_test.log'),
        logging.StreamHandler()
    ]
)

def test_daily_backup():
    """Test daily backup integrity."""
    logging.info("Starting daily backup test")
    result = subprocess.run(['/usr/local/bin/verify_backups.sh'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        logging.info("Daily backup test passed")
    else:
        logging.error(f"Daily backup test failed: {result.stderr}")
        # Send alert
        subprocess.run(['mail', '-s', 'Backup Test Failed', 'dba@example.com'],
                      input=result.stderr, text=True)

def test_weekly_restore():
    """Perform full restore test weekly."""
    logging.info("Starting weekly restore test")
    
    # Restore to test environment
    result = subprocess.run([
        '/usr/local/bin/restore_logical.sh',
        '/backup/weekly/latest.dump'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        logging.info("Weekly restore test passed")
        
        # Run application tests on restored data
        subprocess.run(['pytest', 'tests/test_restored_data.py'])
    else:
        logging.error(f"Weekly restore test failed: {result.stderr}")
        # Send alert
        subprocess.run(['mail', '-s', 'Restore Test Failed', 'dba@example.com'],
                      input=result.stderr, text=True)

def test_monthly_dr():
    """Test disaster recovery procedures monthly."""
    logging.info("Starting monthly DR test")
    
    # Simulate failover
    result = subprocess.run(['/usr/local/bin/test_failover.sh'],
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        logging.info("Monthly DR test passed")
    else:
        logging.error(f"Monthly DR test failed: {result.stderr}")
        # Send alert
        subprocess.run(['mail', '-s', 'DR Test Failed', 'dba@example.com'],
                      input=result.stderr, text=True)

# Schedule tests
schedule.every().day.at("01:00").do(test_daily_backup)
schedule.every().sunday.at("02:00").do(test_weekly_restore)
schedule.every().month.at("03:00").do(test_monthly_dr)

logging.info("Backup test scheduler started")

while True:
    schedule.run_pending()
    time.sleep(60)
Monitoring and Alerts
Backup Monitoring Script
monitor_backups.py

python
#!/usr/bin/env python3
# monitor_backups.py - Monitor backup status

import os
import time
import json
import smtplib
import requests
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

class BackupMonitor:
    def __init__(self):
        self.backup_dir = "/backup/daily"
        self.wal_dir = "/backup/wal"
        self.alert_webhook = os.getenv("ALERT_WEBHOOK")
        self.thresholds = {
            'backup_age_hours': 25,  # Alert if backup older than 25 hours
            'wal_age_minutes': 20,    # Alert if no new WAL for 20 minutes
            'backup_size_mb': 100,    # Alert if backup size < 100MB
            'success_rate': 95         # Alert if success rate < 95%
        }
    
    def check_backup_age(self):
        """Check if latest backup is within threshold."""
        backups = sorted(Path(self.backup_dir).glob("*.dump.gz"))
        if not backups:
            return False, "No backups found"
        
        latest = max(backups, key=lambda f: f.stat().st_mtime)
        age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
        
        if age > timedelta(hours=self.thresholds['backup_age_hours']):
            return False, f"Latest backup is {age.total_seconds()/3600:.1f} hours old"
        return True, f"Backup age: {age.total_seconds()/3600:.1f} hours"
    
    def check_wal_age(self):
        """Check WAL archiving activity."""
        wal_files = sorted(Path(self.wal_dir).glob("*"))
        if not wal_files:
            return False, "No WAL files found"
        
        latest = max(wal_files, key=lambda f: f.stat().st_mtime)
        age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
        
        if age > timedelta(minutes=self.thresholds['wal_age_minutes']):
            return False, f"No new WAL for {age.total_seconds()/60:.1f} minutes"
        return True, f"Last WAL: {age.total_seconds()/60:.1f} minutes ago"
    
    def check_backup_size(self):
        """Check backup file sizes."""
        backups = list(Path(self.backup_dir).glob("*.dump.gz"))
        if not backups:
            return False, "No backups to check"
        
        small_backups = []
        for backup in backups[-5:]:  # Check last 5 backups
            size_mb = backup.stat().st_size / (1024 * 1024)
            if size_mb < self.thresholds['backup_size_mb']:
                small_backups.append(f"{backup.name}: {size_mb:.1f}MB")
        
        if small_backups:
            return False, f"Small backups detected: {', '.join(small_backups)}"
        return True, "Backup sizes OK"
    
    def check_success_rate(self):
        """Calculate backup success rate from logs."""
        log_file = Path("/var/log/backup.log")
        if not log_file.exists():
            return False, "No backup log found"
        
        with open(log_file) as f:
            logs = f.readlines()[-1000:]  # Last 1000 lines
        
        total = 0
        failed = 0
        for line in logs:
            if "Backup completed" in line:
                total += 1
            elif "ERROR" in line:
                failed += 1
        
        if total > 0:
            success_rate = ((total - failed) / total) * 100
            if success_rate < self.thresholds['success_rate']:
                return False, f"Success rate: {success_rate:.1f}%"
            return True, f"Success rate: {success_rate:.1f}%"
        return False, "No backup records found"
    
    def send_alert(self, message):
        """Send alert via webhook/email."""
        alert_data = {
            "text": f"🚨 Backup Alert\n{message}\nTime: {datetime.now().isoformat()}"
        }
        
        if self.alert_webhook:
            try:
                requests.post(self.alert_webhook, json=alert_data)
            except Exception as e:
                logging.error(f"Failed to send webhook: {e}")
        
        # Also log to file
        with open("/var/log/backup_alerts.log", "a") as f:
            f.write(f"{datetime.now().isoformat()}: {message}\n")
    
    def run_checks(self):
        """Run all checks and report."""
        results = []
        all_passed = True
        
        checks = [
            ("Backup Age", self.check_backup_age),
            ("WAL Age", self.check_wal_age),
            ("Backup Size", self.check_backup_size),
            ("Success Rate", self.check_success_rate)
        ]
        
        for name, check_func in checks:
            passed, message = check_func()
            status = "✅" if passed else "❌"
            results.append(f"{status} {name}: {message}")
            if not passed:
                all_passed = False
        
        # Send alert if any check failed
        if not all_passed:
            alert_message = "\n".join(results)
            self.send_alert(alert_message)
        
        # Log results
        for result in results:
            logging.info(result)
        
        return all_passed, results

if __name__ == "__main__":
    monitor = BackupMonitor()
    passed, results = monitor.run_checks()
    exit(0 if passed else 1)
Prometheus Metrics Exporter
backup_metrics.py

python
#!/usr/bin/env python3
# backup_metrics.py - Export backup metrics to Prometheus

from prometheus_client import start_http_server, Gauge, Counter
import time
import os
from pathlib import Path
from datetime import datetime

# Define metrics
backup_age = Gauge('backup_age_hours', 'Age of latest backup in hours')
backup_size = Gauge('backup_size_bytes', 'Size of latest backup in bytes')
backup_count = Counter('backup_total', 'Total number of backups')
backup_success = Counter('backup_success_total', 'Number of successful backups')
backup_failed = Counter('backup_failed_total', 'Number of failed backups')
wal_age = Gauge('wal_age_minutes', 'Age of latest WAL file in minutes')
wal_count = Gauge('wal_files_total', 'Total number of WAL files')

class BackupMetrics:
    def __init__(self):
        self.backup_dir = "/backup/daily"
        self.wal_dir = "/backup/wal"
    
    def collect_metrics(self):
        """Collect and update metrics."""
        # Latest backup metrics
        backups = sorted(Path(self.backup_dir).glob("*.dump.gz"))
        if backups:
            latest = max(backups, key=lambda f: f.stat().st_mtime)
            age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
            backup_age.set(age.total_seconds() / 3600)
            backup_size.set(latest.stat().st_size)
        
        # WAL metrics
        wal_files = list(Path(self.wal_dir).glob("*"))
        if wal_files:
            latest = max(wal_files, key=lambda f: f.stat().st_mtime)
            age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
            wal_age.set(age.total_seconds() / 60)
            wal_count.set(len(wal_files))
        
        # Parse backup log for counts
        log_file = Path("/var/log/backup.log")
        if log_file.exists():
            with open(log_file) as f:
                logs = f.readlines()[-10000:]
            
            success = sum(1 for line in logs if "Backup completed" in line)
            failed = sum(1 for line in logs if "ERROR" in line and "Backup" in line)
            
            backup_count.inc(success)
            backup_success.inc(success)
            backup_failed.inc(failed)

if __name__ == "__main__":
    # Start HTTP server
    start_http_server(9101)
    metrics = BackupMetrics()
    
    while True:
        metrics.collect_metrics()
        time.sleep(60)
Retention Policy
Backup Retention Schedule
Backup Type	Frequency	Retention	Storage Class	Purpose
WAL Archives	Continuous	7 days	Hot	Point-in-time recovery
Daily Full	Daily	30 days	Warm	Recent recovery
Weekly Full	Weekly	3 months	Cool	Weekly restore points
Monthly Full	Monthly	1 year	Cold	Long-term archive
Yearly Full	Yearly	7 years	Archive	Compliance
Automated Cleanup Script
cleanup_backups.py

python
#!/usr/bin/env python3
# cleanup_backups.py - Automated backup cleanup

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

class BackupCleanup:
    def __init__(self):
        self.retention = {
            'daily': timedelta(days=30),
            'weekly': timedelta(days=90),
            'monthly': timedelta(days=365),
            'yearly': timedelta(days=365*7),
            'wal': timedelta(days=7)
        }
        
        self.dirs = {
            'daily': '/backup/daily',
            'weekly': '/backup/weekly',
            'monthly': '/backup/monthly',
            'yearly': '/backup/yearly',
            'wal': '/backup/wal'
        }
    
    def cleanup_directory(self, dir_type):
        """Clean up old backups in a directory."""
        dir_path = self.dirs[dir_type]
        retention = self.retention[dir_type]
        cutoff = datetime.now() - retention
        
        if not os.path.exists(dir_path):
            return
        
        count = 0
        size = 0
        
        for file in Path(dir_path).glob("*"):
            if file.is_file():
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if mtime < cutoff:
                    size += file.stat().st_size
                    file.unlink()
                    count += 1
        
        if count > 0:
            logging.info(f"Cleaned {count} files ({size/1024/1024:.2f}MB) from {dir_type}")
    
    def cleanup_all(self):
        """Clean up all backup directories."""
        for dir_type in self.dirs:
            self.cleanup_directory(dir_type)
        
        # Keep weekly backups (one per week)
        self.keep_weekly_backups()
        
        # Keep monthly backups (one per month)
        self.keep_monthly_backups()
    
    def keep_weekly_backups(self):
        """Keep only the latest backup per week."""
        weekly_dir = self.dirs['weekly']
        if not os.path.exists(weekly_dir):
            return
        
        # Group by week
        backups = {}
        for file in Path(weekly_dir).glob("*.dump.gz"):
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            week_key = mtime.strftime("%Y-%W")
            
            if week_key not in backups or mtime > backups[week_key][1]:
                backups[week_key] = (file, mtime)
        
        # Remove files not in keep list
        keep_files = {b[0] for b in backups.values()}
        for file in Path(weekly_dir).glob("*.dump.gz"):
            if file not in keep_files:
                file.unlink()
                logging.info(f"Removed duplicate weekly backup: {file.name}")
    
    def keep_monthly_backups(self):
        """Keep only the latest backup per month."""
        monthly_dir = self.dirs['monthly']
        if not os.path.exists(monthly_dir):
            return
        
        # Group by month
        backups = {}
        for file in Path(monthly_dir).glob("*.dump.gz"):
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            month_key = mtime.strftime("%Y-%m")
            
            if month_key not in backups or mtime > backups[month_key][1]:
                backups[month_key] = (file, mtime)
        
        # Remove files not in keep list
        keep_files = {b[0] for b in backups.values()}
        for file in Path(monthly_dir).glob("*.dump.gz"):
            if file not in keep_files:
                file.unlink()
                logging.info(f"Removed duplicate monthly backup: {file.name}")

if __name__ == "__main__":
    cleanup = BackupCleanup()
    cleanup.cleanup_all()
Retention Cron Job
bash
# /etc/cron.d/backup-retention

# Daily cleanup at 2 AM
0 2 * * * backup_user /usr/local/bin/cleanup_backups.py >> /var/log/backup_cleanup.log 2>&1

# Weekly summary on Sunday
0 3 * * 0 backup_user /usr/local/bin/backup_summary.py >> /var/log/backup_summary.log 2>&1

# Monthly archive on 1st
0 4 1 * * backup_user /usr/local/bin/archive_monthly.sh >> /var/log/backup_archive.log 2>&1
Security Considerations
Encryption
Backup Encryption Script
bash
#!/bin/bash
# encrypt_backup.sh - Encrypt backup files

BACKUP_FILE="$1"
ENCRYPTION_KEY="/etc/backup/keys/backup.key"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Generate random IV
openssl rand -out "${BACKUP_FILE}.iv" 16

# Encrypt backup
openssl enc -aes-256-cbc \
    -in $BACKUP_FILE \
    -out "${BACKUP_FILE}.enc" \
    -pass file:$ENCRYPTION_KEY \
    -iv $(cat "${BACKUP_FILE}.iv" | xxd -p)

# Encrypt IV with public key
openssl rsautl -encrypt \
    -inkey /etc/backup/keys/public.pem \
    -pubin \
    -in "${BACKUP_FILE}.iv" \
    -out "${BACKUP_FILE}.iv.enc"

# Cleanup
rm "${BACKUP_FILE}.iv"
rm $BACKUP_FILE

echo "Encrypted backup: ${BACKUP_FILE}.enc"
Decryption Script
bash
#!/bin/bash
# decrypt_backup.sh - Decrypt backup files

ENCRYPTED_FILE="$1"
PRIVATE_KEY="/etc/backup/keys/private.pem"

if [ -z "$ENCRYPTED_FILE" ]; then
    echo "Usage: $0 <encrypted_file>"
    exit 1
fi

# Decrypt IV
openssl rsautl -decrypt \
    -inkey $PRIVATE_KEY \
    -in "${ENCRYPTED_FILE%.enc}.iv.enc" \
    -out "${ENCRYPTED_FILE%.enc}.iv"

# Decrypt backup
openssl enc -d -aes-256-cbc \
    -in $ENCRYPTED_FILE \
    -out "${ENCRYPTED_FILE%.enc}" \
    -pass file:/etc/backup/keys/backup.key \
    -iv $(cat "${ENCRYPTED_FILE%.enc}.iv" | xxd -p)

# Cleanup
rm "${ENCRYPTED_FILE%.enc}.iv"

echo "Decrypted backup: ${ENCRYPTED_FILE%.enc}"
Access Control
backup_permissions.sh

bash
#!/bin/bash
# backup_permissions.sh - Set secure permissions

BACKUP_DIR="/backup"

# Set ownership
chown -R backup_user:backup_group $BACKUP_DIR

# Set directory permissions
find $BACKUP_DIR -type d -exec chmod 750 {} \;

# Set file permissions
find $BACKUP_DIR -type f -exec chmod 640 {} \;

# Set special permissions for encryption keys
chmod 600 /etc/backup/keys/*
chmod 700 /etc/backup/keys

# Restrict access to backup scripts
chmod 750 /usr/local/bin/*backup*.sh
chown root:backup_group /usr/local/bin/*backup*.sh

# Audit log permissions
touch /var/log/backup.log /var/log/backup_alerts.log
chmod 640 /var/log/backup*.log
chown backup_user:backup_group /var/log/backup*.log

echo "Backup permissions configured"
Troubleshooting
Common Issues and Solutions
Issue 1: Backup Fails with "Connection refused"
bash
# Check PostgreSQL is running
systemctl status postgresql

# Check pg_hba.conf
grep backup_user /etc/postgresql/14/main/pg_hba.conf

# Test connection
psql -h localhost -U backup_user -d parking_db -c "SELECT 1"
Issue 2: Insufficient Disk Space
bash
# Check disk usage
df -h /backup

# Find large files
du -sh /backup/* | sort -h

# Clean up old backups
find /backup/daily -name "*.dump.gz" -mtime +30 -delete

# Compress old WAL files
find /backup/wal -name "00*" -mtime +1 -exec gzip {} \;
Issue 3: WAL Archiving Failed
bash
# Check archive command
psql -c "SHOW archive_command;"

# Test archive command manually
cp /var/lib/postgresql/14/main/pg_wal/000000010000000000000001 /backup/wal/test

# Check permissions
ls -la /backup/wal
ls -la /var/lib/postgresql/14/main/pg_wal

# View WAL archiver log
tail -f /var/log/postgresql/postgresql-14-main.log | grep archive
Issue 4: Restore Fails with "Missing WAL"
bash
# Check WAL availability
ls -la /backup/wal/ | grep $(cat /restore/pitr/backup_label | grep 'START WAL')

# Find required WAL range
cat /restore/pitr/backup_label
cat /restore/pitr/recovery.conf

# Copy missing WAL from archive
cp /backup/wal/0000000100000000000000* /restore/pitr/pg_wal/
Issue 5: Backup Verification Fails
bash
# Check backup integrity
pg_verifybackup /backup/basebackup/base_20240115_0000

# Test restore to temporary database
createdb test_restore
pg_restore -d test_restore /backup/daily/latest.dump
dropdb test_restore

# Check backup log for errors
tail -100 /var/log/backup.log | grep -i error
Diagnostic Commands
bash
# Backup status
ls -lh /backup/daily/
ls -lh /backup/wal/ | tail -20

# Database size
psql -d parking_db -c "SELECT pg_database_size('parking_db')/1024/1024/1024 as size_gb;"

# WAL statistics
psql -d parking_db -c "SELECT * FROM pg_stat_archiver;"

# Backup history
grep "Backup completed" /var/log/backup.log | tail -10

# Recovery status
psql -d parking_db -c "SELECT pg_is_in_recovery();"
psql -d parking_db -c "SELECT pg_last_xact_replay_timestamp();"
Appendix
Quick Reference Card
Operation	Command
Full backup	pg_dump -Fc parking_db > backup.dump
Compressed backup	pg_dump -Fc parking_db | gzip > backup.dump.gz
Restore backup	pg_restore -d parking_db backup.dump
Physical backup	pg_basebackup -D /backup/base -Ft -z
Show current LSN	SELECT pg_current_wal_lsn();
Show backup history	SELECT * FROM pg_stat_archiver;
Verify backup	pg_verifybackup /backup/base
Point-in-time recovery	recovery_target_time = '2024-01-15 14:30:00'
Environment Variables
Variable	Description	Default
BACKUP_DIR	Backup directory	/backup
DB_NAME	Database name	parking_db
DB_USER	Backup user	backup_user
WAL_ARCHIVE	WAL archive directory	/backup/wal
RETENTION_DAYS	Backup retention days	30
ALERT_WEBHOOK	Alert webhook URL	None
ENCRYPTION_KEY	Encryption key path	/etc/backup/key
Useful Queries
sql
-- Database size
SELECT 
    pg_database.datname,
    pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database
WHERE datname = 'parking_db';

-- Table sizes
SELECT
    relname as table_name,
    pg_size_pretty(pg_total_relation_size(relid)) As total_size,
    pg_size_pretty(pg_relation_size(relid)) As data_size,
    pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) As index_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- WAL statistics
SELECT * FROM pg_stat_archiver;

-- Last backup time
SELECT
    last_time,
    last_action
FROM pg_stat_archiver;

-- Recovery status
SELECT 
    pg_is_in_recovery(),
    pg_last_wal_receive_lsn(),
    pg_last_wal_replay_lsn(),
    pg_last_xact_replay_timestamp();
Emergency Contacts
Role	Contact	Responsibility
DBA Team	dba@example.com	Database recovery
System Admin	sysadmin@example.com	Server recovery
Security Team	security@example.com	Security incidents
Management	management@example.com	Escalation
Document Version History
Version	Date	Author	Changes
1.0.0	2024-01-15	Parking System Team	Initial version
This document is maintained by the Parking Management System development team. For questions or updates, contact the system administrator.

text

This comprehensive `backup_restore.md` provides:

1. **Introduction**: Backup philosophy, RPO/RTO objectives
2. **Prerequisites**: System requirements, permissions, PostgreSQL configuration
3. **Backup Methods**: Logical backups (pg_dump), physical backups (pg_basebackup), WAL archiving, cloud backups
4. **Automated Procedures**: Cron jobs, systemd timers, Ansible automation
5. **Restore Procedures**: Point-in-time recovery, full restore, partial restore
6. **Disaster Recovery**: DR site setup, failover procedures
7. **Verification**: Backup integrity testing, automated testing
8. **Monitoring**: Prometheus metrics, alerting, health checks
9. **Retention Policy**: Multi-tier retention, automated cleanup
10. **Security**: Encryption, access control, secure permissions
11. **Troubleshooting**: Common issues and solutions
12. **Appendix**: Quick reference, useful queries, emergency contacts

The guide is designed to be:
- **Comprehensive**: Covers all backup and restore scenarios
- **Practical**: Ready-to-use scripts and configurations
- **Secure**: Encryption and access control included
- **Automated**: Minimal manual intervention
- **Tested**: Verification and monitoring built-in