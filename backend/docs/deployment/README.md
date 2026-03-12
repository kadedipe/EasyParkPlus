# Parking Management System - Deployment Guide

## Overview
This guide provides comprehensive instructions for deploying the Parking Management System backend in various environments.

## Deployment Options

- [Production Deployment](production.md) - Complete production setup
- [Development Deployment](development.md) - Local development setup
- [Docker Deployment](docker.md) - Container-based deployment
- [Cloud Deployment](cloud.md) - AWS/Azure/GCP deployment
- [Kubernetes Deployment](kubernetes.md) - K8s orchestration

## Quick Start

### Prerequisites
```bash
# Check required tools
docker --version
docker-compose --version
python --version
node --version
One-Command Deployment
bash
# Clone repository
git clone https://github.com/yourcompany/parking-management.git
cd parking-management/backend

# Run deployment script
./deployment/scripts/deploy.sh --env production
Architecture Overview
text
┌─────────────────────────────────────────────────────┐
│                    Load Balancer                      │
│                    (Nginx/HAProxy)                    │
└─────────────────────┬─────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼───────┐           ┌───────▼───────┐
│   API Server  │           │   API Server  │
│   (FastAPI)   │           │   (FastAPI)   │
└───────┬───────┘           └───────┬───────┘
        │                           │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │         PostgreSQL         │
        │        (Primary/Replica)    │
        └─────────────┬─────────────┘
                      │
        ┌─────────────┴─────────────┐
        │          Redis             │
        │      (Cache/Session)       │
        └───────────────────────────┘
Environment Matrix
Environment	Purpose	URL	SSL	Auto-scaling
Production	Live system	api.parking-management.com	Yes	Yes
Staging	Pre-production testing	staging.api.parking-management.com	Yes	No
Development	Development testing	dev.api.parking-management.com	Optional	No
Local	Local development	localhost:8000	No	No
Configuration Management
Environment Variables
bash
# Core Configuration
APP_NAME=parking-management
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-secret-key-here

# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=parking_db
DB_USER=postgres
DB_PASSWORD=secure-password
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# API Configuration
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["https://app.parking-management.com"]
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Payment Gateway
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=notifications@parking-management.com
SMTP_PASSWORD=...

# Monitoring
SENTRY_DSN=https://...
NEW_RELIC_LICENSE_KEY=...
DATADOG_API_KEY=...
Deployment Checklist
Pre-Deployment
Run all tests: pytest tests/ -v

Check test coverage: pytest --cov=. tests/

Run security scan: bandit -r .

Check dependencies: safety check

Update version number

Update CHANGELOG.md

Create database backup

Review migration scripts

Deployment
Pull latest code

Install dependencies

Run database migrations

Load fixtures (if needed)

Clear cache

Start new containers

Run health checks

Monitor logs

Post-Deployment
Verify API endpoints

Check error rates

Monitor performance

Update documentation

Notify stakeholders

Security Considerations
SSL/TLS Configuration
nginx
# Nginx SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
Firewall Rules
bash
# Allow only necessary ports
ufw allow 22/tcp        # SSH
ufw allow 80/tcp        # HTTP
ufw allow 443/tcp       # HTTPS
ufw allow 5432/tcp      # PostgreSQL (internal only)
ufw allow 6379/tcp      # Redis (internal only)
ufw default deny incoming
ufw enable
Database Encryption
sql
-- Enable encryption at rest
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt sensitive data
UPDATE users 
SET encrypted_phone = pgp_sym_encrypt(phone, 'encryption-key')
WHERE phone IS NOT NULL;
Monitoring & Alerting
Health Check Endpoints
bash
# API Health
curl https://api.parking-management.com/health

# Database Health
curl https://api.parking-management.com/health/db

# Cache Health
curl https://api.parking-management.com/health/cache
Prometheus Metrics
yaml
# prometheus.yml
scrape_configs:
  - job_name: 'parking-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
Grafana Dashboards
API Performance Dashboard

Database Dashboard

Business Metrics Dashboard

Error Tracking Dashboard

Backup & Recovery
Automated Backups
bash
#!/bin/bash
# Daily backup script

# Database backup
pg_dump -U postgres parking_db | gzip > /backups/db_$(date +%Y%m%d).sql.gz

# Upload to S3
aws s3 cp /backups/db_$(date +%Y%m%d).sql.gz s3://backups/parking/

# Keep only last 30 days
find /backups -name "*.sql.gz" -mtime +30 -delete
Disaster Recovery
Restore database from latest backup

Replay WAL logs for point-in-time recovery

Verify data integrity

Restart services

Validate application functionality

Scaling Strategies
Horizontal Scaling
yaml
# docker-compose.scale.yml
version: '3.8'
services:
  api:
    image: parking-api:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
Database Scaling
Read replicas for query offloading

Connection pooling with PgBouncer

Partitioning for large tables

Archival of old records

Caching Strategy
python
# Redis cache configuration
CACHE_CONFIG = {
    'default': {
        'backend': 'redis',
        'location': 'redis://redis:6379/0',
        'options': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_CLASS': 'redis.BlockingConnectionPool',
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 50,
                'timeout': 20,
            },
            'MAX_CONNECTIONS': 1000,
            'PICKLE_VERSION': -1,
        }
    }
}
Troubleshooting
Common Issues
Database Connection Issues
bash
# Check database status
docker exec parking-db pg_isready -U postgres

# View database logs
docker logs parking-db --tail 100

# Check connection pool
SELECT * FROM pg_stat_activity WHERE datname = 'parking_db';
API Performance Issues
bash
# Check API logs
docker logs parking-api --tail 100

# Monitor resource usage
docker stats parking-api

# Profile slow endpoints
curl -X GET "https://api.parking-management.com/api/v1/reservations?profile=true"
Redis Issues
bash
# Check Redis connectivity
redis-cli -h redis ping

# Monitor Redis commands
redis-cli -h redis monitor

# Check memory usage
redis-cli -h redis info memory
Rollback Procedures
Quick Rollback
bash
# Revert to previous version
./deployment/scripts/rollback.sh --version 1.2.3

# Restore database
./deployment/scripts/restore-db.sh --backup latest

# Verify rollback
./deployment/scripts/health-check.sh
Database Rollback
sql
-- Revert last migration
ALTER TABLE reservations DROP COLUMN new_column;

-- Restore from backup
pg_restore -U postgres -d parking_db /backups/pre_deploy_backup.sql
Performance Tuning
PostgreSQL Tuning
conf
# postgresql.conf
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 64MB
min_wal_size = 4GB
max_wal_size = 16GB
Nginx Tuning
nginx
# nginx.conf
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    keepalive_timeout 65;
    keepalive_requests 100000;
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    
    client_body_buffer_size 128k;
    client_max_body_size 10m;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;
    
    open_file_cache max=1000 inactive=20s;
    open_file_cache_valid 30s;
    open_file_cache_min_uses 2;
    open_file_cache_errors on;
}
Compliance & Auditing
GDPR Compliance
Data encryption at rest

Audit logs for data access

User data export capability

Right to be forgotten implementation

Consent management

PCI DSS Compliance
No storage of CVV

Tokenization of card data

Encryption in transit

Regular security scans

Access logging

Audit Logging
sql
-- Audit log table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(50),
    resource VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sample audit query
SELECT * FROM audit_logs 
WHERE resource = 'user' 
AND created_at > NOW() - INTERVAL '24 hours';
Deployment Automation
CI/CD Pipeline (GitHub Actions)
yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          docker-compose -f docker-compose.test.yml up --abort-on-container-exit

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          ssh deploy@server "cd /app && ./deploy.sh --version ${GITHUB_REF##*/}"
Infrastructure as Code (Terraform)
hcl
# main.tf
resource "aws_instance" "app_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.medium"
  
  user_data = <<-EOF
    #!/bin/bash
    docker-compose -f /app/docker-compose.prod.yml up -d
  EOF
  
  tags = {
    Name = "ParkingManagementServer"
    Environment = "production"
  }
}
Emergency Procedures
Service Outage
Identify issue: Check monitoring dashboards

Assess impact: Determine affected services

Communicate: Update status page

Mitigate: Apply emergency fixes

Resolve: Restore service

Post-mortem: Document root cause

Security Breach
Isolate affected systems

Rotate all credentials

Analyze breach scope

Notify affected users

Implement security patches

Update security protocols

Data Corruption
Stop write operations

Identify corruption extent

Restore from clean backup

Replay transactions

Verify data integrity

Resume operations

Contact & Support
Emergency Contacts
DevOps Team: +1-555-0123 (24/7)

Security Team: security@parking-management.com

Database Admin: dba@parking-management.com

Escalation Matrix
Level	Response Time	Contact
P1 (Critical)	15 minutes	DevOps Lead
P2 (High)	1 hour	Senior Engineer
P3 (Medium)	4 hours	Team Lead
P4 (Low)	24 hours	Support Team
Status Page
URL: https://status.parking-management.com

RSS Feed: https://status.parking-management.com/feed.rss

Twitter: @parkingstatus

text

## 2. Production Deployment Guide

**`parking-management/backend/docs/deployment/production.md`**

```markdown
# Production Deployment Guide

## Prerequisites

### System Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+ minimum, 16GB recommended
- **Disk**: 50GB+ SSD
- **OS**: Ubuntu 20.04 LTS or newer
- **Network**: Static IP, domain name

### Software Requirements
```bash
# Install required packages
sudo apt update
sudo apt install -y \
    docker.io \
    docker-compose \
    nginx \
    certbot \
    python3-certbot-nginx \
    postgresql-client \
    redis-tools \
    fail2ban \
    ufw
Step-by-Step Deployment
1. Server Preparation
bash
# Create deployment user
sudo useradd -m -s /bin/bash deploy
sudo usermod -aG docker deploy

# Set up SSH key
sudo mkdir -p /home/deploy/.ssh
sudo cp ~/.ssh/authorized_keys /home/deploy/.ssh/
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Set up fail2ban
sudo cp /etc/fail2ban/jail.{conf,local}
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
2. Application Setup
bash
# Clone repository
cd /opt
sudo git clone https://github.com/yourcompany/parking-management.git
sudo chown -R deploy:deploy parking-management
cd parking-management/backend

# Create environment file
cp .env.example .env
# Edit .env with production values
nano .env

# Run deployment script
./deployment/scripts/deploy.sh --env production
3. SSL Certificate Setup
bash
# Obtain SSL certificate
sudo certbot --nginx -d api.parking-management.com

# Auto-renewal setup
sudo crontab -e
# Add: 0 0 1 * * /usr/bin/certbot renew --quiet
4. Database Setup
bash
# Initialize database
docker exec -it parking-db psql -U postgres -c "CREATE DATABASE parking_db;"
docker exec -it parking-db psql -U postgres -c "CREATE USER parking_user WITH PASSWORD 'secure-password';"
docker exec -it parking-db psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE parking_db TO parking_user;"

# Run migrations
docker exec -it parking-api python -m alembic upgrade head

# Load initial data
docker exec -it parking-api python -m scripts.load_fixtures
5. Monitoring Setup
bash
# Install Prometheus node exporter
docker run -d \
  --name node-exporter \
  --restart always \
  --net="host" \
  --pid="host" \
  -v "/:/host:ro,rslave" \
  prom/node-exporter \
  --path.rootfs=/host

# Set up log rotation
sudo tee /etc/logrotate.d/parking-management << EOF
/var/log/parking-management/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 deploy deploy
    sharedscripts
    postrotate
        docker exec parking-api kill -USR1 1 2>/dev/null || true
    endscript
}
EOF
6. Load Balancer Setup (Optional)
nginx
# /etc/nginx/sites-available/load-balancer
upstream backend {
    least_conn;
    server 10.0.1.10:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:8000 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.parking-management.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.parking-management.com;
    
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
7. Performance Testing
bash
# Install benchmarking tools
sudo apt install -y apache2-utils wrk

# Run load tests
ab -n 10000 -c 100 https://api.parking-management.com/health
wrk -t12 -c400 -d30s https://api.parking-management.com/api/v1/parking/spots
8. Go-Live Checklist
DNS records configured

SSL certificates valid

Database backups configured

Monitoring alerts set up

Error tracking (Sentry) configured

Rate limiting enabled

CORS configured correctly

API documentation updated

Support team notified

Rollback plan in place

text

## 3. Docker Deployment Guide

**`parking-management/backend/docs/deployment/docker.md`**

```markdown
# Docker Deployment Guide

## Docker Compose Configuration

### Production Docker Compose
**`docker-compose.prod.yml`**
```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - VERSION=${VERSION}
        - BUILD_DATE=${BUILD_DATE}
    image: parking-api:${VERSION}
    container_name: parking-api
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - DB_HOST=postgres
      - REDIS_HOST=redis
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./static:/app/static
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - parking-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  postgres:
    image: postgres:15-alpine
    container_name: parking-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./backups:/backups
      - ./init-db:/docker-entrypoint-initdb.d
    networks:
      - parking-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    container_name: parking-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    networks:
      - parking-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  nginx:
    image: nginx:alpine
    container_name: parking-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/sites-available:/etc/nginx/sites-available:ro
      - ./nginx/sites-enabled:/etc/nginx/sites-enabled:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./static:/usr/share/nginx/html/static:ro
    depends_on:
      - api
    networks:
      - parking-network
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

  backup:
    image: alpine:latest
    container_name: parking-backup
    restart: unless-stopped
    volumes:
      - ./backups:/backups
      - ./scripts:/scripts
    entrypoint: |
      sh -c "
      apk add --no-cache postgresql-client aws-cli
      echo '0 2 * * * /scripts/backup-db.sh' > /etc/crontabs/root
      crond -f
      "
    depends_on:
      - postgres
    networks:
      - parking-network

  monitoring:
    image: prom/prometheus
    container_name: parking-prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - parking-network

  grafana:
    image: grafana/grafana
    container_name: parking-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"
    networks:
      - parking-network
    depends_on:
      - monitoring

volumes:
  postgres-data:
    driver: local
  redis-data:
    driver: local
  prometheus-data:
    driver: local
  grafana-data:
    driver: local

networks:
  parking-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
Development Docker Compose
docker-compose.yml

yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: parking-api-dev
    restart: unless-stopped
    environment:
      - ENVIRONMENT=development
      - DB_HOST=postgres
      - REDIS_HOST=redis
    env_file:
      - .env
    volumes:
      - .:/app
      - /app/__pycache__
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    networks:
      - parking-network-dev
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: postgres:15-alpine
    container_name: parking-db-dev
    restart: unless-stopped
    environment:
      - POSTGRES_DB=parking_db
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres-data-dev:/var/lib/postgresql/data
    networks:
      - parking-network-dev

  redis:
    image: redis:7-alpine
    container_name: parking-redis-dev
    restart: unless-stopped
    ports:
      - "6379:6379"
    networks:
      - parking-network-dev

  pgadmin:
    image: dpage/pgadmin4
    container_name: parking-pgadmin
    restart: unless-stopped
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@parking-management.com
      - PGADMIN_DEFAULT_PASSWORD=admin
    ports:
      - "5050:80"
    volumes:
      - pgadmin-data:/var/lib/pgadmin
    depends_on:
      - postgres
    networks:
      - parking-network-dev

  mailhog:
    image: mailhog/mailhog
    container_name: parking-mailhog
    restart: unless-stopped
    ports:
      - "1025:1025"
      - "8025:8025"
    networks:
      - parking-network-dev

volumes:
  postgres-data-dev:
  pgadmin-data:

networks:
  parking-network-dev:
    driver: bridge
Docker Commands
Build Images
bash
# Production build
docker build -t parking-api:latest .
docker build -t parking-api:1.2.3 .

# Development build
docker-compose build

# Multi-stage build
docker build --target production -t parking-api:prod .
Run Containers
bash
# Production
docker-compose -f docker-compose.prod.yml up -d

# Development
docker-compose up -d

# Scale services
docker-compose up -d --scale api=3
Container Management
bash
# View logs
docker logs parking-api --tail 100 -f

# Execute commands
docker exec -it parking-api bash
docker exec -it parking-db psql -U postgres

# Copy files
docker cp backup.sql parking-db:/backups/
docker cp parking-api:/app/logs/app.log ./logs/

# Container stats
docker stats parking-api
Docker Optimization
Multi-stage Dockerfile

dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Production stage
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser

WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY . .

ENV PATH=/home/appuser/.local/bin:$PATH
USER appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
Docker Security
dockerfile
# Security best practices
FROM python:3.11-slim

# Run as non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=appuser:appgroup . /app
WORKDIR /app

# Security headers
RUN echo "Secure" > /etc/security

# Drop capabilities
USER appuser

# Read-only root filesystem
VOLUME ["/tmp", "/var/tmp", "/run"]

EXPOSE 8000
CMD ["python", "main.py"]
text

## 4. Cloud Deployment Guide

**`parking-management/backend/docs/deployment/cloud.md`**

```markdown
# Cloud Deployment Guide

## AWS Deployment

### Infrastructure Setup (Terraform)

**`terraform/main.tf`**
```hcl
provider "aws" {
  region = var.aws_region
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "parking-management-vpc"
    Environment = var.environment
  }
}

# Subnets
resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name        = "parking-management-public-${count.index}"
    Environment = var.environment
  }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name        = "parking-management-private-${count.index}"
    Environment = var.environment
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "parking-management-igw"
    Environment = var.environment
  }
}

# NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  tags = {
    Name        = "parking-management-nat"
    Environment = var.environment
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name        = "parking-management-public-rt"
    Environment = var.environment
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name        = "parking-management-private-rt"
    Environment = var.environment
  }
}

# Security Groups
resource "aws_security_group" "alb" {
  name        = "parking-management-alb-sg"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "parking-management-alb-sg"
    Environment = var.environment
  }
}

resource "aws_security_group" "ecs" {
  name        = "parking-management-ecs-sg"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "parking-management-ecs-sg"
    Environment = var.environment
  }
}

resource "aws_security_group" "rds" {
  name        = "parking-management-rds-sg"
  description = "Security group for RDS"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  tags = {
    Name        = "parking-management-rds-sg"
    Environment = var.environment
  }
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier     = "parking-management-${var.environment}"
  engine         = "postgres"
  engine_version = "15.3"
  instance_class = "db.t3.medium"

  allocated_storage     = 100
  storage_encrypted     = true
  storage_type          = "gp3"
  
  db_name  = "parking_db"
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  multi_az               = var.environment == "production" ? true : false
  deletion_protection    = var.environment == "production" ? true : false
  skip_final_snapshot    = var.environment != "production"

  tags = {
    Name        = "parking-management-rds"
    Environment = var.environment
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "parking-management-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECR Repository
resource "aws_ecr_repository" "api" {
  name = "parking-management-api"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "parking-management-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "api"
      image = "${aws_ecr_repository.api.repository_url}:latest"
      
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]
      
      environment = [
        {
          name  = "ENVIRONMENT"
          value = var.environment
        }
      ]
      
      secrets = [
        {
          name      = "DB_PASSWORD"
          valueFrom = aws_secretsmanager_secret.db_password.arn
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "api"
        }
      }
      
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "parking-management-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = aws_subnet.public[*].id

  enable_deletion_protection = var.environment == "production"

  tags = {
    Environment = var.environment
  }
}

resource "aws_lb_target_group" "api" {
  name        = "parking-management-api-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 10
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.main.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# ECS Service
resource "aws_ecs_service" "api" {
  name            = "parking-management-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.environment == "production" ? 3 : 1
  launch_type     = "FARGATE"

  network_configuration {
    security_groups  = [aws_security_group.ecs.id]
    subnets         = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_controller {
    type = "ECS"
  }

  tags = {
    Environment = var.environment
  }
}

# Auto Scaling
resource "aws_appautoscaling_target" "api" {
  max_capacity       = var.environment == "production" ? 10 : 2
  min_capacity       = var.environment == "production" ? 3 : 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "api-cpu-autoscaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 300
  }
}
Deployment Script (AWS)
deploy-aws.sh

bash
#!/bin/bash

# AWS Deployment Script

set -e

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="parking-management-api"
ECS_CLUSTER="parking-management-production"
ECS_SERVICE="parking-management-api"
TASK_FAMILY="parking-management-api"

# Get version
VERSION=$(git describe --tags --always)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and tag Docker image
docker build -t $ECR_REPOSITORY:$VERSION .
docker tag $ECR_REPOSITORY:$VERSION \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$VERSION
docker tag $ECR_REPOSITORY:$VERSION \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# Push to ECR
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$VERSION
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# Register new task definition
aws ecs register-task-definition \
    --family $TASK_FAMILY \
    --execution-role-arn arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole \
    --network-mode awsvpc \
    --requires-compatibilities FARGATE \
    --cpu "1024" \
    --memory "2048" \
    --container-definitions '[
        {
            "name": "api",
            "image": "'$AWS_ACCOUNT_ID'.dkr.ecr.'$AWS_REGION'.amazonaws.com/'$ECR_REPOSITORY':'$VERSION'",
            "portMappings": [
                {
                    "containerPort": 8000,
                    "protocol": "tcp"
                }
            ],
            "environment": [
                {
                    "name": "ENVIRONMENT",
                    "value": "production"
                }
            ],
            "logConfiguration": {
                "logDriver": "awslogs",
                "options": {
                    "awslogs-group": "/ecs/parking-management-api",
                    "awslogs-region": "'$AWS_REGION'",
                    "awslogs-stream-prefix": "ecs"
                }
            }
        }
    ]'

# Update service
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --task-definition $TASK_FAMILY \
    --force-new-deployment

# Wait for deployment to complete
aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE

echo "Deployment completed successfully!"
Azure Deployment
deploy-azure.sh

bash
#!/bin/bash

# Azure Deployment Script

# Variables
RESOURCE_GROUP="parking-management-rg"
APP_NAME="parking-management-api"
REGISTRY_NAME="parkingregistry"
VERSION=$(git describe --tags --always)

# Login to Azure
az login

# Create resource group
az group create --name $RESOURCE_GROUP --location eastus

# Create Container Registry
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $REGISTRY_NAME \
    --sku Basic \
    --admin-enabled true

# Build and push image
az acr build \
    --registry $REGISTRY_NAME \
    --image $APP_NAME:$VERSION \
    --file Dockerfile .

# Create App Service plan
az appservice plan create \
    --name parking-management-plan \
    --resource-group $RESOURCE_GROUP \
    --sku P1V2 \
    --is-linux

# Create Web App for Containers
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan parking-management-plan \
    --name $APP_NAME \
    --deployment-container-image-name \
    $REGISTRY_NAME.azurecr.io/$APP_NAME:$VERSION

# Configure environment variables
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings \
        ENVIRONMENT=production \
        DB_HOST=$DB_HOST \
        DB_NAME=$DB_NAME \
        DB_USER=$DB_USER \
        DB_PASSWORD=$DB_PASSWORD

# Enable managed identity
az webapp identity assign \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME

# Configure SSL
az webapp config ssl upload \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --certificate-file ./ssl/certificate.pfx \
    --certificate-password $CERT_PASSWORD

echo "Deployment to Azure completed!"
Google Cloud Platform (GCP)
deploy-gcp.sh

bash
#!/bin/bash

# GCP Deployment Script

# Variables
PROJECT_ID="parking-management"
REGION="us-central1"
CLUSTER_NAME="parking-cluster"
VERSION=$(git describe --tags --always)

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
    container.googleapis.com \
    containerregistry.googleapis.com \
    cloudbuild.googleapis.com

# Create GKE cluster
gcloud container clusters create $CLUSTER_NAME \
    --region $REGION \
    --num-nodes 3 \
    --machine-type n1-standard-2 \
    --enable-autoscaling \
    --min-nodes 1 \
    --max-nodes 5

# Get credentials
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION

# Build and push image
gcloud builds submit \
    --tag gcr.io/$PROJECT_ID/parking-api:$VERSION

# Deploy to GKE
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Configure Ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Set up SSL with Let's Encrypt
kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.12.0/cert-manager.yaml

echo "Deployment to GCP completed!"
This comprehensive deployment documentation covers:

Production deployment with detailed steps

Docker containerization

Cloud deployment (AWS, Azure, GCP)

Monitoring and alerting

Security best practices

Backup and recovery

Scaling strategies

Troubleshooting guides

CI/CD integration

Infrastructure as Code (Terraform)