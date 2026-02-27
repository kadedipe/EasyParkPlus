markdown
# Parking Management System - Database Migration Guide

## Document Information
| | |
|---|---|
| **Document Version** | 1.0.0 |
| **Last Updated** | 2024-01-15 |
| **Database** | PostgreSQL 14+ |
| **Migration Tool** | Alembic |
| **Author** | Parking Management System Team |

## Document Purpose
This guide provides comprehensive instructions for managing database migrations in the Parking Management System. It covers migration strategies, version control, rollback procedures, and best practices for both development and production environments.

---

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Migration Tool Setup](#migration-tool-setup)
4. [Migration Workflow](#migration-workflow)
5. [Creating Migrations](#creating-migrations)
6. [Migration Types](#migration-types)
7. [Running Migrations](#running-migrations)
8. [Rollback Procedures](#rollback-procedures)
9. [Data Migrations](#data-migrations)
10. [Environment-Specific Strategies](#environment-specific-strategies)
11. [Testing Migrations](#testing-migrations)
12. [Troubleshooting](#troubleshooting)
13. [Best Practices](#best-practices)
14. [Migration Examples](#migration-examples)
15. [Appendix](#appendix)

---

## Introduction

### What are Migrations?
Database migrations are a controlled way to modify the database schema over time. They allow us to:
- Version control database changes
- Apply changes consistently across environments
- Roll back changes when needed
- Collaborate effectively between developers
- Deploy changes safely to production

### Migration Philosophy
Our migration strategy follows these principles:
- **Idempotency**: Migrations can be run multiple times safely
- **Reversibility**: Every migration should have a rollback strategy
- **Atomicity**: Migrations should be all-or-nothing
- **Version Control**: All migrations are stored in version control
- **Testing**: Migrations must be tested before production deployment

---

## Prerequisites

### System Requirements
- Python 3.9+
- PostgreSQL 14+
- Alembic 1.10+
- Access to database with migration privileges

### Required Permissions
| Permission | Purpose |
|------------|---------|
| `CREATE TABLE` | Create new tables |
| `ALTER TABLE` | Modify existing tables |
| `DROP TABLE` | Remove tables (for rollbacks) |
| `CREATE INDEX` | Create indexes |
| `DROP INDEX` | Remove indexes |
| `CREATE SCHEMA` | Create schemas |

### Environment Variables
```bash
# Database connection
DATABASE_URL=postgresql://user:password@localhost:5432/parking_db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Migration settings
MIGRATION_TIMEOUT=300
MIGRATION_LOCK_TIMEOUT=60
MIGRATION_AUTO_UPGRADE=false

# Environment
PARKING_ENV=development
Migration Tool Setup
Installation
bash
# Install Alembic
pip install alembic

# Initialize Alembic in your project
alembic init migrations

# Install PostgreSQL driver
pip install psycopg2-binary
Directory Structure
text
parking-management/
├── data/
│   ├── migrations/
│   │   ├── versions/
│   │   │   ├── 001_initial_schema.py
│   │   │   ├── 002_add_waitlist_table.py
│   │   │   ├── 003_add_metadata_columns.py
│   │   │   └── ...
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── alembic.ini
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── reservation.py
│   │   └── ...
│   └── config/
│       └── database.py
Alembic Configuration
alembic.ini

ini
[alembic]
script_location = migrations
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql://%(DB_USER)s:%(DB_PASSWORD)s@%(DB_HOST)s:%(DB_PORT)s/%(DB_NAME)s

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 88

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
migrations/env.py

python
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import your models
from app.models import Base
from app.config import get_database_url

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = Base.metadata

# Get database URL from environment
database_url = get_database_url()
config.set_main_option('sqlalchemy.url', database_url)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
Migration Workflow
Standard Migration Flow
















Development Workflow
Make Model Changes

python
# Add new column to User model
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20))  # New column
Generate Migration

bash
alembic revision --autogenerate -m "add_phone_column_to_users"
Review and Edit Migration

python
# migrations/versions/1234_add_phone_column_to_users.py
def upgrade():
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))

def downgrade():
    op.drop_column('users', 'phone')
Apply Migration

bash
alembic upgrade head
Commit to Version Control

bash
git add migrations/versions/
git commit -m "Add phone column to users table"
git push
Creating Migrations
Auto-generating Migrations
bash
# Generate migration from model changes
alembic revision --autogenerate -m "description_of_changes"

# Generate empty migration
alembic revision -m "description_of_changes"
Manual Migration Creation
bash
# Create empty migration with specific version
alembic revision -m "add_composite_index" --rev-id 0042
Migration File Structure
python
"""Add phone column to users table

Revision ID: 1234abcd5678
Revises: 9876efgh4321
Create Date: 2024-01-15 10:30:00.123456

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '1234abcd5678'
down_revision = '9876efgh4321'
branch_labels = None
depends_on = None

def upgrade():
    """Apply the migration."""
    # Add new column
    op.add_column('users', 
        sa.Column('phone', sa.String(20), nullable=True)
    )
    
    # Create index
    op.create_index(
        'idx_users_phone',
        'users',
        ['phone'],
        unique=True
    )
    
    # Update existing records with default value
    op.execute(
        "UPDATE users SET phone = '+1234567890' WHERE phone IS NULL"
    )
    
    # Make column not nullable after populating
    op.alter_column('users', 'phone',
        existing_type=sa.String(20),
        nullable=False
    )

def downgrade():
    """Revert the migration."""
    # Drop index
    op.drop_index('idx_users_phone', table_name='users')
    
    # Drop column
    op.drop_column('users', 'phone')
Migration Types
Schema Migrations
Adding a Table
python
def upgrade():
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(
        'idx_notifications_user_id',
        'notifications',
        ['user_id']
    )

def downgrade():
    op.drop_table('notifications')
Adding a Column
python
def upgrade():
    # Add nullable column first
    op.add_column('reservations',
        sa.Column('metadata', postgresql.JSONB(), nullable=True)
    )
    
    # Add with default value
    op.add_column('reservations',
        sa.Column('cancellation_reason', sa.Text(), 
                  server_default='', nullable=False)
    )

def downgrade():
    op.drop_column('reservations', 'cancellation_reason')
    op.drop_column('reservations', 'metadata')
Modifying Column Type
python
def upgrade():
    # Change column type with data preservation
    op.alter_column('payments', 'amount',
        existing_type=sa.NUMERIC(10, 2),
        type_=sa.NUMERIC(12, 4),
        existing_nullable=False
    )

def downgrade():
    op.alter_column('payments', 'amount',
        existing_type=sa.NUMERIC(12, 4),
        type_=sa.NUMERIC(10, 2),
        existing_nullable=False
    )
Adding Constraints
python
def upgrade():
    # Add unique constraint
    op.create_unique_constraint(
        'uq_users_email',
        'users',
        ['email']
    )
    
    # Add check constraint
    op.create_check_constraint(
        'ck_reservations_dates',
        'reservations',
        'end_time > start_time'
    )

def downgrade():
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_constraint('ck_reservations_dates', 'reservations', type_='check')
Adding Indexes
python
def upgrade():
    # Single column index
    op.create_index(
        'idx_reservations_status',
        'reservations',
        ['status']
    )
    
    # Composite index
    op.create_index(
        'idx_reservations_date_range',
        'reservations',
        ['start_time', 'end_time'],
        postgresql_using='gist'
    )
    
    # Partial index
    op.create_index(
        'idx_active_reservations',
        'reservations',
        ['user_id'],
        postgresql_where=sa.text("status IN ('confirmed', 'checked_in')")
    )

def downgrade():
    op.drop_index('idx_reservations_status', table_name='reservations')
    op.drop_index('idx_reservations_date_range', table_name='reservations')
    op.drop_index('idx_active_reservations', table_name='reservations')
Data Migrations
Backfilling Data
python
def upgrade():
    # Get connection
    connection = op.get_bind()
    
    # Backfill data for new column
    connection.execute(
        """
        UPDATE users 
        SET verification_status = 'email_verified'
        WHERE email_verified_at IS NOT NULL
        """
    )
    
    # Process in batches for large tables
    batch_size = 1000
    offset = 0
    
    while True:
        result = connection.execute(
            """
            UPDATE reservations 
            SET total_duration = EXTRACT(EPOCH FROM (end_time - start_time))/3600
            WHERE id IN (
                SELECT id FROM reservations 
                WHERE total_duration IS NULL 
                LIMIT %s OFFSET %s
            )
            RETURNING id
            """,
            (batch_size, offset)
        )
        
        if result.rowcount == 0:
            break
        
        offset += batch_size
Data Transformation
python
def upgrade():
    connection = op.get_bind()
    
    # Transform data
    connection.execute(
        """
        UPDATE parking_spots
        SET spot_type = 
            CASE 
                WHEN is_handicap THEN 'disabled'
                WHEN has_charger THEN 'ev_charging'
                ELSE spot_type
            END
        """
    )
    
    # Split combined data
    connection.execute(
        """
        INSERT INTO user_preferences (user_id, preference_key, preference_value)
        SELECT 
            id,
            'language',
            split_part(preferences::text, ',', 1)
        FROM users
        WHERE preferences IS NOT NULL
        """
    )
Multi-Step Migrations
python
def upgrade():
    # Step 1: Create new table
    op.create_table('user_preferences', ...)
    
    # Step 2: Migrate data
    op.execute("""
        INSERT INTO user_preferences (user_id, preference_key, preference_value)
        SELECT id, 'notifications', preferences->>'notifications'
        FROM users
        WHERE preferences IS NOT NULL
    """)
    
    # Step 3: Drop old column
    op.drop_column('users', 'preferences')
    
    # Step 4: Create indexes
    op.create_index('idx_user_preferences_user_id', 'user_preferences', ['user_id'])

def downgrade():
    # Reverse in opposite order
    op.add_column('users', sa.Column('preferences', postgresql.JSONB()))
    
    op.execute("""
        UPDATE users u
        SET preferences = jsonb_build_object(
            'notifications', p.preference_value
        )
        FROM user_preferences p
        WHERE u.id = p.user_id AND p.preference_key = 'notifications'
    """)
    
    op.drop_table('user_preferences')
Running Migrations
Basic Commands
bash
# Show current version
alembic current

# Show migration history
alembic history

# Upgrade to latest version
alembic upgrade head

# Upgrade to specific version
alembic upgrade 1234abcd5678

# Upgrade by number of steps
alembic upgrade +2

# Downgrade to base
alembic downgrade base

# Downgrade to specific version
alembic downgrade 9876efgh4321

# Downgrade by number of steps
alembic downgrade -1

# Show SQL without executing
alembic upgrade head --sql

# Run with transaction
alembic upgrade head --autocommit=false
Environment-Specific Commands
development.sh

bash
#!/bin/bash
export PARKING_ENV=development
export DATABASE_URL=postgresql://dev_user:dev_pass@localhost:5432/parking_dev

# Drop and recreate database
dropdb --if-exists parking_dev
createdb parking_dev

# Run all migrations
alembic upgrade head

# Seed data
python scripts/seed_data.py
staging.sh

bash
#!/bin/bash
export PARKING_ENV=staging
export DATABASE_URL=postgresql://staging_user:staging_pass@staging-db:5432/parking_staging

# Backup before migration
pg_dump $DATABASE_URL > backup_before_migration.sql

# Run migrations
alembic upgrade head

# Verify
alembic current
production.sh

bash
#!/bin/bash
export PARKING_ENV=production
export DATABASE_URL=$PRODUCTION_DATABASE_URL

# Enable maintenance mode
./scripts/maintenance_mode.sh on

# Create backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Run migrations with timeout
timeout 300 alembic upgrade head

# Verify migration
alembic current

# Disable maintenance mode
./scripts/maintenance_mode.sh off
Using Python Script
run_migrations.py

python
#!/usr/bin/env python
"""Script to run database migrations."""
import os
import sys
import time
import logging
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_db():
    """Wait for database to be available."""
    db_url = os.getenv('DATABASE_URL')
    engine = create_engine(db_url)
    
    for i in range(30):
        try:
            with engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            logger.info("Database is available")
            return True
        except Exception as e:
            logger.warning(f"Waiting for database... ({i+1}/30)")
            time.sleep(2)
    
    logger.error("Database not available")
    return False

def run_migrations():
    """Run database migrations."""
    if not wait_for_db():
        sys.exit(1)
    
    try:
        alembic_cfg = Config("alembic.ini")
        
        # Get current version
        current = command.current(alembic_cfg)
        logger.info(f"Current version: {current}")
        
        # Run migrations
        logger.info("Running migrations...")
        command.upgrade(alembic_cfg, "head")
        
        # Verify
        current = command.current(alembic_cfg)
        logger.info(f"New version: {current}")
        
        logger.info("Migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_migrations()
Rollback Procedures
Standard Rollback
bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade 9876efgh4321

# Rollback all migrations
alembic downgrade base
Emergency Rollback Script
emergency_rollback.py

python
#!/usr/bin/env python
"""Emergency rollback script."""
import os
import sys
import logging
from datetime import datetime
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def emergency_rollback(target_revision=None):
    """
    Perform emergency rollback.
    
    Args:
        target_revision: Target revision to rollback to
    """
    db_url = os.getenv('DATABASE_URL')
    backup_file = f"backup_emergency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    try:
        # Create emergency backup
        logger.info(f"Creating emergency backup: {backup_file}")
        os.system(f"pg_dump {db_url} > {backup_file}")
        
        # Set target revision
        if not target_revision:
            target_revision = 'base'
        
        # Run rollback
        logger.info(f"Rolling back to {target_revision}")
        alembic_cfg = Config("alembic.ini")
        command.downgrade(alembic_cfg, target_revision)
        
        logger.info("Emergency rollback completed")
        
    except Exception as e:
        logger.error(f"Emergency rollback failed: {e}")
        
        # Attempt to restore from backup
        logger.info(f"Attempting restore from {backup_file}")
        os.system(f"psql {db_url} < {backup_file}")
        sys.exit(1)

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else None
    emergency_rollback(target)
Rollback Strategy Decision Tree
















Data Migrations
Large Table Migrations
For tables with millions of rows, use batch processing:

python
def upgrade():
    connection = op.get_bind()
    
    # Create new column
    op.add_column('reservations', 
        sa.Column('total_hours', sa.Float())
    )
    
    # Batch update
    batch_size = 10000
    offset = 0
    
    while True:
        result = connection.execute(
            """
            UPDATE reservations 
            SET total_hours = EXTRACT(EPOCH FROM (end_time - start_time))/3600
            WHERE id IN (
                SELECT id FROM reservations 
                WHERE total_hours IS NULL 
                LIMIT %s OFFSET %s
            )
            RETURNING id
            """,
            (batch_size, offset)
        )
        
        updated = result.rowcount
        if updated == 0:
            break
        
        offset += updated
        logger.info(f"Updated {offset} rows...")
        connection.commit()
Zero-Downtime Migrations
For production systems, use a phased approach:

Phase 1: Expand (Add nullable columns)
python
def upgrade():
    # Add column as nullable
    op.add_column('reservations',
        sa.Column('new_status', sa.String(20), nullable=True)
    )
Phase 2: Migrate (Backfill data)
python
def upgrade():
    # Backfill data in batches
    connection = op.get_bind()
    connection.execute("""
        UPDATE reservations 
        SET new_status = old_status
        WHERE new_status IS NULL
    """)
Phase 3: Contract (Make not null, drop old columns)
python
def upgrade():
    # Make column not nullable
    op.alter_column('reservations', 'new_status',
        existing_type=sa.String(20),
        nullable=False
    )
    
    # Drop old column
    op.drop_column('reservations', 'old_status')
Environment-Specific Strategies
Development Environment
python
# migrations/env.py - Development specific
if os.getenv('PARKING_ENV') == 'development':
    # Auto-generate migrations
    context.configure(
        compare_type=True,
        compare_server_default=True,
        include_schemas=True
    )
    
    # Seed data after migrations
    def seed_data():
        connection = op.get_bind()
        connection.execute("""
            INSERT INTO users (email, full_name, role)
            VALUES ('admin@example.com', 'Admin User', 'admin')
            ON CONFLICT DO NOTHING
        """)
Testing Environment
python
# migrations/env.py - Testing specific
if os.getenv('PARKING_ENV') == 'testing':
    # Use transaction for test isolation
    connection = op.get_bind()
    transaction = connection.begin()
    
    try:
        context.run_migrations()
        transaction.commit()
    except:
        transaction.rollback()
        raise
Production Environment
python
# migrations/env.py - Production specific
if os.getenv('PARKING_ENV') == 'production':
    # Run within transaction
    context.configure(
        transaction_per_migration=True,
        transactional_ddl=True
    )
    
    # Log all operations
    import logging
    logging.getLogger('alembic').setLevel(logging.INFO)
Testing Migrations
Unit Testing Migrations
test_migrations.py

python
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

class TestMigrations:
    @pytest.fixture
    def alembic_config(self, tmp_path):
        config = Config()
        config.set_main_option("script_location", "migrations")
        config.set_main_option("sqlalchemy.url", "sqlite:///:memory:")
        return config
    
    def test_upgrade_downgrade_cycle(self, alembic_config):
        """Test upgrading to head and downgrading to base."""
        # Upgrade to head
        command.upgrade(alembic_config, "head")
        
        # Get head version
        script = ScriptDirectory.from_config(alembic_config)
        head = script.get_current_head()
        
        # Downgrade to base
        command.downgrade(alembic_config, "base")
        
        # Upgrade back to head
        command.upgrade(alembic_config, head)
    
    def test_migration_idempotency(self, alembic_config):
        """Test running migrations multiple times."""
        command.upgrade(alembic_config, "head")
        
        # Run upgrade again
        command.upgrade(alembic_config, "head")
        
        # Should not raise errors
    
    def test_data_preservation(self, alembic_config, test_db):
        """Test data preservation during migrations."""
        # Insert test data
        with test_db.connect() as conn:
            conn.execute(
                text("INSERT INTO users (email, full_name) VALUES ('test@test.com', 'Test User')")
            )
            conn.commit()
        
        # Run migration
        command.upgrade(alembic_config, "head")
        
        # Verify data still exists
        with test_db.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM users WHERE email = 'test@test.com'")
            )
            assert result.scalar() == 1
Migration Test Matrix
Test Case	Description	Expected Result
Upgrade from base to head	Run all migrations	All tables created
Downgrade from head to base	Reverse all migrations	All tables dropped
Upgrade then downgrade	Apply then reverse	Schema returns to original
Idempotency	Run same migration twice	No errors
Data preservation	Migrate with existing data	Data remains intact
Concurrent migrations	Run multiple migrations	Proper sequencing
Failed migration	Simulate failure	Rollback to previous state
Troubleshooting
Common Issues and Solutions
Issue 1: Migration Dependency Conflicts
bash
# Error: Can't locate revision
alembic history  # Check migration history
alembic current  # Check current version
alembic stamp head  # Stamp database as up-to-date
Issue 2: Table Already Exists
python
# Solution: Use check for existence
def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    
    if 'table_name' not in inspector.get_table_names():
        op.create_table('table_name', ...)
Issue 3: Column Already Exists
python
# Solution: Use try/except
def upgrade():
    try:
        op.add_column('table_name', sa.Column('column_name', sa.String()))
    except ProgrammingError:
        # Column already exists
        pass
Issue 4: Deadlock During Migration
python
# Solution: Use statement timeout
def upgrade():
    connection = op.get_bind()
    connection.execute(text("SET statement_timeout = '30s'"))
    
    # Run migration
    op.add_column('reservations', ...)
Issue 5: Out of Memory
python
# Solution: Batch processing
def upgrade():
    connection = op.get_bind()
    
    # Process in batches
    offset = 0
    while True:
        result = connection.execute(
            "UPDATE ... LIMIT 10000 OFFSET :offset RETURNING id",
            {"offset": offset}
        )
        if result.rowcount == 0:
            break
        offset += result.rowcount
        connection.commit()
Diagnostic Commands
bash
# Check migration history
alembic history --verbose

# Show SQL for upgrade
alembic upgrade head --sql

# Check for pending migrations
alembic check

# List all revisions
alembic list_templates

# Show current revision
alembic current

# Compare database to models
alembic check --compare-type
Best Practices
Migration Naming Convention
text
[revision_id]_[action]_[table]_[description]
Examples:

001_create_users_table.py

002_add_phone_column_to_users.py

003_add_unique_constraint_to_email.py

004_backfill_user_verification.py

Migration Checklist
Before Writing Migration
Have you backed up the database?

Have you reviewed the schema changes?

Is the migration reversible?

Have you considered performance impact?

Will this affect existing data?

During Migration Development
Test on development database

Include both upgrade and downgrade

Handle edge cases (NULLs, duplicates)

Use batch processing for large tables

Add appropriate indexes

Before Deployment
Test on staging environment

Run performance tests

Prepare rollback plan

Update documentation

Notify team members

During Deployment
Enable maintenance mode if needed

Create backup before migration

Monitor performance

Have rollback script ready

Verify after completion

Golden Rules
Always have a downgrade

Test migrations in staging first

Backup before production migrations

Make migrations idempotent

Use transactions

Batch process large tables

Consider zero-downtime for critical systems

Document complex migrations

Version control all migrations

Review migrations before merging

Migration Examples
Example 1: Initial Schema
python
"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='customer'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('verification_status', sa.String(20), nullable=False, server_default='unverified'),
        sa.Column('preferences', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create parking_spots table
    op.create_table(
        'parking_spots',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('spot_number', sa.String(10), nullable=False),
        sa.Column('spot_type', sa.String(50), nullable=False, server_default='standard'),
        sa.Column('hourly_rate', sa.Numeric(10, 2), nullable=False),
        sa.Column('charging_fee', sa.Numeric(10, 2), nullable=True),
        sa.Column('charger_type', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_covered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_handicap', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('level', sa.Integer(), nullable=True),
        sa.Column('section', sa.String(10), nullable=True),
        sa.Column('features', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('spot_number')
    )
    
    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_role', 'users', ['role'])
    op.create_index('idx_spots_spot_type', 'parking_spots', ['spot_type'])
    op.create_index('idx_spots_is_active', 'parking_spots', ['is_active'])

def downgrade():
    op.drop_table('parking_spots')
    op.drop_table('users')
Example 2: Add Waitlist Feature
python
"""Add waitlist functionality

Revision ID: 002_add_waitlist
Revises: 001_initial
Create Date: 2024-01-15 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002_add_waitlist'
down_revision = '001_initial'
branch_labels = None
depends_on = None

def upgrade():
    # Create waitlist table
    op.create_table(
        'waitlist',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('spot_id', sa.BigInteger(), nullable=False),
        sa.Column('date_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('date_to', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['spot_id'], ['parking_spots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_waitlist_user_id', 'waitlist', ['user_id'])
    op.create_index('idx_waitlist_spot_id', 'waitlist', ['spot_id'])
    op.create_index('idx_waitlist_status', 'waitlist', ['status'])
    op.create_index('idx_waitlist_spot_date', 'waitlist', ['spot_id', 'date_from'])

def downgrade():
    op.drop_table('waitlist')
Example 3: Add Payment Processing
python
"""Add payment processing tables

Revision ID: 003_add_payments
Revises: 002_add_waitlist
Create Date: 2024-02-01 09:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003_add_payments'
down_revision = '002_add_waitlist'
branch_labels = None
depends_on = None

def upgrade():
    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('reservation_id', sa.BigInteger(), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('transaction_id', sa.String(255), nullable=True, unique=True),
        sa.Column('provider_response', postgresql.JSONB(), nullable=True),
        sa.Column('card_last4', sa.String(4), nullable=True),
        sa.Column('card_brand', sa.String(20), nullable=True),
        sa.Column('refunded_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('refund_reason', sa.Text(), nullable=True),
        sa.Column('refunded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add payment_id to reservations
    op.add_column('reservations',
        sa.Column('payment_id', sa.BigInteger(), nullable=True)
    )
    op.add_column('reservations',
        sa.Column('payment_status', sa.String(20), nullable=False, server_default='pending')
    )
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_reservations_payment_id',
        'reservations', 'payments',
        ['payment_id'], ['id']
    )
    
    # Create indexes
    op.create_index('idx_payments_reservation_id', 'payments', ['reservation_id'])
    op.create_index('idx_payments_transaction_id', 'payments', ['transaction_id'])
    op.create_index('idx_payments_status', 'payments', ['status'])
    op.create_index('idx_payments_created_at', 'payments', ['created_at'])
    
    op.create_index('idx_reservations_payment_status', 'reservations', ['payment_status'])

def downgrade():
    # Drop foreign key first
    op.drop_constraint('fk_reservations_payment_id', 'reservations', type_='foreignkey')
    
    # Drop columns
    op.drop_column('reservations', 'payment_status')
    op.drop_column('reservations', 'payment_id')
    
    # Drop payments table
    op.drop_table('payments')
Example 4: Add Audit Logging
python
"""Add audit logging tables

Revision ID: 004_add_audit_logs
Revises: 003_add_payments
Create Date: 2024-02-15 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '004_add_audit_logs'
down_revision = '003_add_payments'
branch_labels = None
depends_on = None

def upgrade():
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(50), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('old_values', postgresql.JSONB(), nullable=True),
        sa.Column('new_values', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_audit_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_user_id', 'audit_logs', ['user_id'])
    
    # Add partition by timestamp (optional, for large tables)
    op.execute("""
        CREATE TABLE audit_logs_2024_q1 PARTITION OF audit_logs
        FOR VALUES FROM ('2024-01-01') TO ('2024-04-01')
    """)

def downgrade():
    op.drop_table('audit_logs')
Appendix
Migration Commands Cheat Sheet
Command	Description
alembic init migrations	Initialize Alembic
alembic revision --autogenerate -m "msg"	Auto-generate migration
alembic revision -m "msg"	Create empty migration
alembic upgrade head	Apply all migrations
alembic upgrade +1	Apply next migration
alembic downgrade -1	Revert last migration
alembic downgrade base	Revert all migrations
alembic current	Show current version
alembic history	Show migration history
alembic heads	Show head revisions
alembic branches	Show branches
alembic check	Check for issues
alembic stamp head	Stamp as up-to-date
Migration Status Codes
Code	Description
(head)	Latest migration
(current)	Currently applied
(branch)	Branch point
(merge)	Merge point
(base)	Initial state
Revision ID Generation
python
import hashlib
import time

def generate_revision_id():
    """Generate a unique revision ID."""
    timestamp = str(time.time()).encode()
    return hashlib.md5(timestamp).hexdigest()[:12]
Environment Variables Reference
Variable	Description	Default
DATABASE_URL	Database connection URL	None
DATABASE_POOL_SIZE	Connection pool size	10
DATABASE_MAX_OVERFLOW	Max overflow connections	20
MIGRATION_TIMEOUT	Migration timeout in seconds	300
MIGRATION_LOCK_TIMEOUT	Lock timeout in seconds	60
MIGRATION_AUTO_UPGRADE	Auto-upgrade on startup	false
PARKING_ENV	Environment name	development
Document Version History
Version	Date	Author	Changes
1.0.0	2024-01-15	Parking System Team	Initial version
This document is maintained by the Parking Management System development team. For questions or updates, contact the system administrator.

text

This comprehensive `migration_guide.md` provides:

1. **Introduction**: Overview of migration concepts and philosophy
2. **Prerequisites**: System requirements and permissions
3. **Migration Tool Setup**: Complete Alembic configuration
4. **Migration Workflow**: Step-by-step process with diagrams
5. **Creating Migrations**: Auto-generation and manual creation
6. **Migration Types**: Schema, data, and multi-step migrations
7. **Running Migrations**: Commands for all environments
8. **Rollback Procedures**: Standard and emergency rollback
9. **Data Migrations**: Handling large tables and zero-downtime
10. **Environment Strategies**: Development, testing, production
11. **Testing Migrations**: Unit tests and test matrix
12. **Troubleshooting**: Common issues and solutions
13. **Best Practices**: Guidelines and checklist
14. **Migration Examples**: Complete real-world examples
15. **Appendix**: Cheat sheets and references

The guide is designed to be:
- **Comprehensive**: Covers all aspects of migration management
- **Practical**: Real commands and code examples
- **Safe**: Emphasis on rollback and data preservation
- **Scalable**: Handles large tables and zero-downtime
- **Reference-ready**: Complete documentation for developers and DBAs