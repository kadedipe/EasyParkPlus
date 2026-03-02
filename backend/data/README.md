# Parking Management System - Data Layer

This directory contains all data-related components for the Parking Management System, including database schemas, models, migrations, and data access layers.

## Overview

The data layer provides a comprehensive data management solution for the parking management system, supporting:
- PostgreSQL for relational data
- Redis for caching and real-time data
- Elasticsearch for search and analytics
- Data migrations and versioning
- Backup and restore procedures
- Performance optimization

## Directory Structure
data/
├── schemas/ # Database schemas and SQL scripts
├── migrations/ # Alembic migration scripts
├── models/ # SQLAlchemy ORM models
├── repositories/ # Data access layer
├── services/ # Data services
├── scripts/ # Utility scripts
├── seed/ # Seed data
├── tests/ # Test files
├── config/ # Configuration files
├── utils/ # Utility functions
└── docs/ # Documentation

text

## Quick Start

### 1. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your database credentials
vim .env
2. Install Dependencies
bash
pip install -r requirements.txt
3. Initialize Database
bash
# Create database
python scripts/init_db.py

# Run migrations
alembic upgrade head

# Seed initial data
python scripts/seed_data.py
4. Run Tests
bash
pytest tests/
Database Schema
Core Tables
users: User accounts and profiles

parking_spots: Parking spot information

reservations: Parking reservations

payments: Payment transactions

vehicles: Vehicle information

zones: Parking zones

rates: Pricing rates

sensor_data: IoT sensor readings

audit_logs: Audit trail

Relationships
text
users 1---N reservations N---1 parking_spots
users 1---N vehicles
reservations 1---1 payments
parking_spots N---1 zones
zones 1---N rates
parking_spots 1---N sensor_data
Data Models
User Model
python
class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(Enum(UserRole))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
Parking Spot Model
python
class ParkingSpot(Base):
    __tablename__ = 'parking_spots'
    
    id = Column(UUID, primary_key=True)
    zone_id = Column(UUID, ForeignKey('zones.id'))
    spot_number = Column(String, unique=True)
    status = Column(Enum(SpotStatus))
    type = Column(Enum(SpotType))
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
Data Access Layer
Repository Pattern
python
# Example repository usage
user_repo = UserRepository(session)
user = user_repo.get_by_email("user@example.com")
active_users = user_repo.get_active_users()
Caching
python
# Example cache usage
cache_service = CacheService(redis_client)
await cache_service.set_user(user)
cached_user = await cache_service.get_user(user_id)
Migrations
Create Migration
bash
alembic revision -m "add_users_table"
Apply Migrations
bash
alembic upgrade head
Rollback
bash
alembic downgrade -1
Backup and Restore
Backup
bash
# Full backup
python scripts/backup_db.py --full

# Incremental backup
python scripts/backup_db.py --incremental
Restore
bash
python scripts/restore_db.py --backup-file backup_20240101.sql
Performance Optimization
Indexes
sql
CREATE INDEX idx_reservations_user_id ON reservations(user_id);
CREATE INDEX idx_reservations_start_time ON reservations(start_time);
CREATE INDEX idx_parking_spots_status ON parking_spots(status);
Partitioning
Tables partitioned by:

reservations: by month (start_time)

payments: by month (created_at)

audit_logs: by month (created_at)

Caching Strategy
User sessions: Redis (TTL: 24h)

Available spots: Redis (TTL: 30s)

Rate configurations: Redis (TTL: 1h)

Frequent queries: Redis (TTL: 5m)

Monitoring
Key Metrics
Query performance

Cache hit ratio

Connection pool usage

Replication lag

Disk usage

Alerts
Slow queries (> 100ms)

Connection pool exhaustion

Replication delay (> 30s)

Disk space (< 20%)

Testing
Unit Tests
bash
pytest tests/unit/
Integration Tests
bash
pytest tests/integration/
Load Tests
bash
locust -f tests/load/locustfile.py
Security
Data Encryption
Passwords: bcrypt

PII: AES-256 encryption

TLS for data in transit

Encrypted backups

Access Control
Row-level security

Role-based access

Audit logging

Data masking

Contributing
Create feature branch

Write tests

Update documentation

Submit pull request