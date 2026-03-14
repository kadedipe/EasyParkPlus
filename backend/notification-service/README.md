# Notification Service

Microservice for handling all notifications in the Parking Management System.

## Features

- **Multi-channel notifications**: Email, SMS, and Push notifications
- **Provider failover**: Automatic switching between providers
- **Template engine**: Jinja2-based templates with custom filters
- **Async processing**: RabbitMQ message queues for reliable delivery
- **Health monitoring**: Comprehensive health checks and metrics
- **Provider management**: Dynamic provider switching and monitoring
- **Bulk operations**: Batch processing for high-volume notifications

## Architecture

## Architecture
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ API Layer │────▶│ Consumer Layer │────▶│ Provider Layer │
│ (FastAPI) │ │ (RabbitMQ) │ │ (Email/SMS/Push)│
└─────────────────┘ └─────────────────┘ └─────────────────┘
│ │ │
▼ ▼ ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Templates │ │ Monitoring │ │ Failover │
│ (Jinja2) │ │ (Metrics) │ │ Manager │
└─────────────────┘ └─────────────────┘ └─────────────────┘

text

## Quick Start

### Prerequisites

- Python 3.9+
- RabbitMQ
- Redis (optional, for rate limiting)
- SMTP server or cloud provider accounts

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourorg/parking-management.git
cd parking-management/backend/notification-service
Create virtual environment:

bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies:

bash
pip install -r requirements.txt
Copy environment configuration:

bash
cp .env.example .env
# Edit .env with your configuration
Run the service:

bash
python -m notification_service.main
Docker
bash
# Build image
docker build -t notification-service .

# Run container
docker run -p 8001:8001 --env-file .env notification-service
API Endpoints
Notifications
POST /api/v1/notifications/email - Send email

POST /api/v1/notifications/sms - Send SMS

POST /api/v1/notifications/push - Send push notification

POST /api/v1/notifications/bulk - Bulk send

Templates
GET /api/v1/templates/list - List templates

GET /api/v1/templates/info/{type}/{name} - Template info

POST /api/v1/templates/render - Render template

POST /api/v1/templates/preview/{type}/{name} - Preview template

Providers
GET /api/v1/providers/email - List email providers

GET /api/v1/providers/sms - List SMS providers

GET /api/v1/providers/push - List push providers

POST /api/v1/providers/email/switch/{name} - Switch email provider

Health
GET /health - Basic health check

GET /health/detailed - Detailed health with metrics

GET /health/ready - Readiness probe

GET /health/live - Liveness probe

Configuration
Key environment variables:

env
# Service
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8001

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# Email
ENABLE_EMAIL=true
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-password

# SMS
ENABLE_SMS=true
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Push
ENABLE_PUSH=true
PUSH_PROVIDER=fcm
FCM_CREDENTIALS_PATH=/path/to/service-account.json
Template System
Templates are stored in the templates/ directory:

text
templates/
├── email/
│   ├── booking_confirmation.html
│   ├── booking_confirmation.txt
│   ├── payment_success.html
│   └── welcome_email.html
├── sms/
│   ├── verification_code.txt
│   ├── booking_confirmation.txt
│   └── payment_success.txt
└── push/
    ├── booking_confirmation.json
    ├── payment_success.json
    └── welcome.json
Provider System
The service supports multiple providers with automatic failover:

Email: SMTP, SendGrid, AWS SES

SMS: Twilio, AWS SNS, Vonage

Push: FCM (Firebase), WebPush

Monitoring
Metrics
The service exposes metrics at /metrics:

Messages sent/failed by type

Provider response times

Queue sizes

Error rates

Health Checks
Three levels of health checks:

Basic: Service is running

Detailed: System metrics and component status

Kubernetes: Readiness and liveness probes

Development
Running Tests
bash
pytest tests/ -v
pytest tests/ --cov=notification_service --cov-report=html
Code Quality
bash
# Format code
black notification_service/
isort notification_service/

# Type checking
mypy notification_service/

# Linting
flake8 notification_service/
Adding New Providers
Create provider class inheriting from base provider

Implement required methods

Add to provider manager

Add configuration options

Update tests

Example:

python
from .providers.email import EmailProvider

class CustomEmailProvider(EmailProvider):
    async def send_email(self, to, subject, html_content, **kwargs):
        # Implementation
        pass
    
    async def check_health(self):
        # Implementation
        pass
Deployment
Kubernetes
yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notification-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: notification-service
  template:
    metadata:
      labels:
        app: notification-service
    spec:
      containers:
      - name: notification-service
        image: notification-service:latest
        ports:
        - containerPort: 8001
        env:
        - name: RABBITMQ_HOST
          value: rabbitmq-service
        - name: REDIS_HOST
          value: redis-service
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8001
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8001
Docker Compose
yaml
version: '3.8'
services:
  notification-service:
    build: .
    ports:
      - "8001:8001"
    environment:
      - RABBITMQ_HOST=rabbitmq
      - REDIS_HOST=redis
    depends_on:
      - rabbitmq
      - redis
  
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
Troubleshooting
Common Issues
RabbitMQ connection refused

Check RabbitMQ is running: rabbitmqctl status

Verify credentials in .env

Provider failures

Check provider credentials

View provider logs: grep "provider" logs/app.log

Provider will automatically failover

Template not found

Verify template exists: ls templates/email/

Check template name in request

Logs
bash
# View all logs
tail -f logs/app.log

# Filter by level
tail -f logs/app.log | grep ERROR

# Filter by consumer
tail -f logs/app.log | grep EmailConsumer
Contributing
Fork the repository

Create a feature branch

Commit changes

Push to the branch

Create a Pull Request

License
MIT License - see LICENSE file for details

Support
For support, email support@parking.com or create an issue in the repository.

text

## `parking-management/backend/notification-service/.env.example`

```env
# Service Configuration
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8001
WORKERS=1
LOG_LEVEL=INFO
JSON_LOGS=false
ENABLE_DOCS=true
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# RabbitMQ Configuration
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/

# Consumer Configuration
ENABLE_EMAIL=true
ENABLE_SMS=true
ENABLE_PUSH=true
ENABLE_AUDIT=true
ENABLE_BOOKING_NOTIFICATIONS=true
ENABLE_PAYMENT_NOTIFICATIONS=true
ENABLE_USER_NOTIFICATIONS=true

# Email Provider Configuration
EMAIL_PROVIDER=smtp
EMAIL_PREFETCH_COUNT=10

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_USE_TLS=true
EMAIL_FROM=noreply@parking.com
EMAIL_FROM_NAME=Parking Management

# SendGrid Configuration
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_SANDBOX_MODE=false

# AWS SES Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1

# SMS Provider Configuration
SMS_PROVIDER=twilio
SMS_PREFETCH_COUNT=10
SMS_RATE_LIMIT_DELAY=0.1
SMS_STATUS_CALLBACK_URL=https://your-domain.com/sms/callback

# Twilio Configuration
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_MESSAGING_SERVICE_SID=your-messaging-service-sid

# AWS SNS Configuration
AWS_SNS_SENDER_ID=PARKING

# Vonage Configuration
VONAGE_API_KEY=your-vonage-api-key
VONAGE_API_SECRET=your-vonage-api-secret
VONAGE_PHONE_NUMBER=+1234567890

# Push Notification Configuration
PUSH_PROVIDER=fcm
PUSH_PREFETCH_COUNT=10

# FCM Configuration
FCM_CREDENTIALS_PATH=/path/to/firebase-service-account.json
FCM_PROJECT_ID=your-firebase-project-id

# WebPush Configuration
VAPID_PRIVATE_KEY=your-vapid-private-key
VAPID_PUBLIC_KEY=your-vapid-public-key
VAPID_CLAIM_EMAIL=admin@parking.com
VAPID_CLAIM_SUBJECT=Parking Management
WEB_PUSH_ICON=/icons/icon-192.png
WEB_PUSH_BADGE=/icons/badge-72.png

# Frontend URLs
FRONTEND_URL=http://localhost:3000
SUPPORT_EMAIL=support@parking.com
SUPPORT_PHONE=+1234567890

# Social Media URLs
SOCIAL_FACEBOOK_URL=https://facebook.com/parking
SOCIAL_TWITTER_URL=https://twitter.com/parking
SOCIAL_INSTAGRAM_URL=https://instagram.com/parking

# Audit Configuration
AUDIT_RETENTION_DAYS=30
AUDIT_PREFETCH_COUNT=10

# Redis Configuration (optional, for rate limiting)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Booking Configuration
BOOKING_PREFETCH_COUNT=10

# Payment Configuration
PAYMENT_PREFETCH_COUNT=10

# Receipts
RECEIPTS_URL=https://storage.parking.com/receipts
This comprehensive package initialization provides:

Package Metadata (__init__.py):

Version information

Author information

Description

Exports all main components

Convenience Functions:

initialize_service() - One-call initialization

get_service_info() - Service metadata

send_email(), send_sms(), send_push() - Direct sending functions

Project Configuration (pyproject.toml):

PEP 621 compliant project metadata

Dependencies with version pins

Development dependencies

Tool configurations (black, isort, mypy, pytest)

Requirements (requirements.txt):

Complete dependency list

Version-pinned for reproducibility

Documentation (README.md):

Comprehensive overview

Quick start guide

API documentation

Configuration guide

Development instructions

Deployment options

Troubleshooting

Environment Configuration (.env.example):

All configuration options

Clear comments

Example values

Organized by category

The package is now production-ready with:

Proper packaging for distribution

Complete documentation

Configuration management

Dependency management

Development tools configured

Testing setup