# Parking Management System - Configuration Guide

## Overview
This directory contains all configuration files for the Parking Management System. The configuration is environment-aware and supports development, testing, staging, and production environments.

## Directory Structure

config/
├── init.py # Main configuration loader
├── base.py # Base configuration class
├── development.py # Development environment
├── testing.py # Testing environment
├── staging.py # Staging environment
├── production.py # Production environment
├── database.py # Database configuration
├── redis.py # Redis configuration
├── elasticsearch.py # Elasticsearch configuration
├── celery.py # Celery task queue
├── logging.py # Logging configuration
├── api.py # API configuration
├── auth.py # Authentication
├── payments.py # Payment processing
├── notifications.py # Notifications
├── storage.py # File storage
├── cache.py # Caching
├── rate_limiter.py # Rate limiting
├── cors.py # CORS settings
├── swagger.py # API documentation
├── monitoring.py # Monitoring & observability
├── feature_flags.py # Feature flags
├── constants.py # Application constants
├── .env.example # Example environment variables
├── .env.development # Development environment
├── .env.testing # Testing environment
├── .env.staging # Staging environment
├── .env.production # Production environment
└── README.md # This file

text

## Usage

### Basic Usage
```python
from config import config

# Access configuration
db_url = config.DATABASE_URL
debug_mode = config.DEBUG
api_port = config.API_PORT

# Environment detection
from config import ENVIRONMENT
if ENVIRONMENT == 'production':
    # Production-specific code
    pass
Database Connection
python
from config.database import db

# Get database session
with db.session() as session:
    users = session.query(User).all()

# Get connection pool stats
stats = db.get_stats()
Redis Cache
python
from config.redis import cache

# Cache operations
cache.set('key', 'value', ttl=300)
value = cache.get('key')
cache.delete('key')
Celery Tasks
python
from config.celery import celery

@celery.task
def my_background_task():
    # Task implementation
    pass
Logging
python
from config.logging import logger

logger.info("Application started")
logger.error("An error occurred", exc_info=True)
Environment Variables
Required Variables
SECRET_KEY: Application secret key

JWT_SECRET_KEY: JWT signing key

DB_PASSWORD: Database password

Optional Variables
DB_HOST: Database host (default: localhost)

DB_PORT: Database port (default: 5432)

REDIS_HOST: Redis host (default: localhost)

SENTRY_DSN: Sentry DSN for error tracking

Environment Setup
Development
bash
# Copy development environment file
cp config/.env.development .env

# Start services
docker-compose up -d postgres redis elasticsearch

# Run application
python -m app.main
Production
bash
# Copy production environment file
cp config/.env.production .env

# Set secure permissions
chmod 600 .env

# Run with production server
gunicorn -c config/gunicorn.conf.py app.main:app
Feature Flags
Checking Feature Availability
python
from config.feature_flags import feature_flags

if feature_flags.is_enabled('qr_code_checkin', user_id=123):
    # Enable QR code check-in for this user
    pass

# Get all enabled features for a user
enabled = feature_flags.get_enabled_features(user_id=123)
Adding New Features
Add feature to BETA_FEATURES in feature_flags.py

Set rollout percentage if needed

Add to environment availability lists

Update dependencies if any

Performance Tuning
Database Connection Pool
python
# Adjust in .env
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=20
Redis Cache
python
# Adjust TTLs in cache.py
TTL = {
    'user': 3600,  # 1 hour
    'reservation': 300,  # 5 minutes
}
Rate Limiting
python
# Adjust limits in rate_limiter.py
ENDPOINT_LIMITS = {
    '/api/reservations': '100/minute',
    '/api/auth/login': '5/minute',
}
Monitoring
Prometheus Metrics
Metrics are available at /metrics endpoint:

HTTP request count and duration

Database query performance

Cache hit/miss ratios

Active reservations

Payment processing stats

Sentry Error Tracking
Configure Sentry DSN in environment file:

text
SENTRY_DSN=https://key@sentry.io/project
SENTRY_TRACES_SAMPLE_RATE=0.1
Health Checks
/health: Basic health check

/ready: Readiness probe

/live: Liveness probe

Security Considerations
Production Checklist
Change all default secrets

Enable HTTPS

Set secure CORS origins

Enable rate limiting

Configure database SSL

Set up database backups

Enable audit logging

Configure firewall rules

Environment Variables
Never commit .env files to version control

Use different secrets per environment

Rotate secrets regularly

Use secrets management in production (AWS Secrets Manager, HashiCorp Vault)

Troubleshooting
Common Issues
Database Connection Failures
bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1"

# Check connection pool
python -c "from config.database import db; print(db.get_stats())"
Redis Connection Issues
bash
# Test Redis connection
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping

# Check Redis info
redis-cli -h $REDIS_HOST -p $REDIS_PORT info stats
Celery Tasks Not Running
bash
# Check Celery worker
celery -A config.celery status

# View Celery logs
tail -f /var/log/celery/worker.log
Support
For configuration issues, contact:

Email: devops@parking.com
Slack: #parking-devops