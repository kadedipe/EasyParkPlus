# Payment Service

Microservice for handling all payment operations in the Parking Management System.

## Features

- **Multi-gateway support**: Stripe, PayPal, Razorpay
- **Payment processing**: Create, capture, refund payments
- **Subscription management**: Plans, subscriptions, renewals
- **Invoice generation**: Automated invoicing
- **Webhook handling**: Event processing with verification
- **Dispute management**: Handle chargebacks and disputes
- **Idempotency**: Prevent duplicate processing
- **Retry logic**: Automatic retries with backoff

## Architecture
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ API Layer │────▶│ Service Layer │────▶│ Gateway Layer │
│ (FastAPI) │ │ │ │ (Stripe/PayPal) │
└─────────────────┘ └─────────────────┘ └─────────────────┘
│ │ │
▼ ▼ ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ Webhooks │ │ Database │ │ Background │
│ (Processing) │ │ (PostgreSQL) │ │ Tasks │
└─────────────────┘ └─────────────────┘ └─────────────────┘

text

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL
- Redis
- RabbitMQ
- Stripe/PayPal/Razorpay accounts

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourorg/parking-management.git
cd parking-management/backend/payment-service
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
Run database migrations:

bash
alembic upgrade head
Run the service:

bash
python -m payment_service.main
Docker
bash
# Build image
docker build -t payment-service .

# Run container
docker run -p 8002:8002 --env-file .env payment-service
API Endpoints
Payments
POST /api/v1/payments/create - Create payment

POST /api/v1/payments/{id}/capture - Capture payment

POST /api/v1/payments/{id}/refund - Refund payment

GET /api/v1/payments/{id} - Get payment details

GET /api/v1/payments - List payments

Subscriptions
POST /api/v1/subscriptions/create - Create subscription

POST /api/v1/subscriptions/{id}/cancel - Cancel subscription

POST /api/v1/subscriptions/{id}/pause - Pause subscription

POST /api/v1/subscriptions/{id}/resume - Resume subscription

GET /api/v1/subscriptions/{id} - Get subscription details

Invoices
GET /api/v1/invoices/{id} - Get invoice

POST /api/v1/invoices/{id}/send - Send invoice

GET /api/v1/invoices - List invoices

Webhooks (External)
POST /webhooks/stripe - Stripe webhook endpoint

POST /webhooks/paypal - PayPal webhook endpoint

POST /webhooks/razorpay - Razorpay webhook endpoint

Webhook Management (Internal)
GET /api/v1/webhooks/status/{id} - Get webhook status

GET /api/v1/webhooks/failed - List failed webhooks

POST /api/v1/webhooks/failed/{id}/retry - Retry failed webhook

Configuration
Key environment variables:

env
# Service
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=8002

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=payment_db
DB_USER=postgres
DB_PASSWORD=postgres

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# Stripe
ENABLE_STRIPE=true
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# PayPal
ENABLE_PAYPAL=true
PAYPAL_CLIENT_ID=your-client-id
PAYPAL_CLIENT_SECRET=your-client-secret
PAYPAL_ENVIRONMENT=sandbox

# Razorpay
ENABLE_RAZORPAY=true
RAZORPAY_KEY_ID=your-key-id
RAZORPAY_KEY_SECRET=your-key-secret
Webhook Processing
The service includes a robust webhook processing system:

Verification: Signature validation for each gateway

Queue: Redis-based queue for reliable processing

Retry: Automatic retries with exponential backoff

Monitoring: Track webhook status and failures

Idempotency: Prevent duplicate processing

Background Tasks
Webhook processing: Continuous queue processing

Subscription renewal: Check and process renewals

Invoice generation: Generate pending invoices

Dispute monitoring: Check for new disputes

Metrics aggregation: Collect service metrics

Monitoring
Health Checks
/health - Comprehensive health check

/health/live - Liveness probe

/health/ready - Readiness probe

Metrics
/metrics - Service and gateway metrics

Payment counts and amounts

Gateway response times

Error rates

Queue sizes

Development
Running Tests
bash
pytest tests/ -v
pytest tests/ --cov=payment_service --cov-report=html
Database Migrations
bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
Code Quality
bash
# Format code
black payment_service/
isort payment_service/

# Type checking
mypy payment_service/

# Linting
flake8 payment_service/
Deployment
Kubernetes
yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: payment-service
  template:
    metadata:
      labels:
        app: payment-service
    spec:
      containers:
      - name: payment-service
        image: payment-service:latest
        ports:
        - containerPort: 8002
        env:
        - name: DB_HOST
          value: postgres-service
        - name: REDIS_HOST
          value: redis-service
        - name: RABBITMQ_HOST
          value: rabbitmq-service
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8002
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8002
Docker Compose
yaml
version: '3.8'
services:
  payment-service:
    build: .
    ports:
      - "8002:8002"
    environment:
      - DB_HOST=postgres
      - REDIS_HOST=redis
      - RABBITMQ_HOST=rabbitmq
    depends_on:
      - postgres
      - redis
      - rabbitmq
  
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: payment_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
  
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"

volumes:
  postgres_data:
Troubleshooting
Common Issues
Database connection failed

Check PostgreSQL is running

Verify credentials in .env

Run migrations: alembic upgrade head

Payment gateway errors

Verify API keys are correct

Check gateway is enabled

View gateway logs

Webhook verification failing

Verify webhook secret is correct

Check signature headers

Ensure timestamp is within tolerance

Logs
bash
# View all logs
tail -f logs/app.log

# Filter by level
tail -f logs/app.log | grep ERROR

# Filter by gateway
tail -f logs/app.log | grep stripe
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

## `parking-management/backend/payment-service/.env.example`

```env
# Service Configuration
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8002
WORKERS=1
LOG_LEVEL=INFO
JSON_LOGS=false
ENABLE_DOCS=true
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# SSL Configuration (optional)
ENABLE_SSL=false
SSL_KEY_FILE=/path/to/key.pem
SSL_CERT_FILE=/path/to/cert.pem

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=payment_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=10

# RabbitMQ Configuration
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/

# Stripe Configuration
ENABLE_STRIPE=true
STRIPE_API_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_API_VERSION=2023-10-16

# PayPal Configuration
ENABLE_PAYPAL=true
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_secret
PAYPAL_ENVIRONMENT=sandbox  # sandbox or live
PAYPAL_WEBHOOK_ID=your_webhook_id

# Razorpay Configuration
ENABLE_RAZORPAY=true
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Feature Flags
ENABLE_SUBSCRIPTIONS=true
ENABLE_INVOICING=true
ENABLE_DISPUTES=true

# Webhook Configuration
WEBHOOK_MAX_RETRIES=3
WEBHOOK_BATCH_SIZE=10
WEBHOOK_RETRY_DELAYS=60,300,900,3600

# Currency Configuration
DEFAULT_CURRENCY=USD
SUPPORTED_CURRENCIES=USD,EUR,GBP,INR,SGD,AED

# Tax Configuration
ENABLE_TAX=true
DEFAULT_TAX_RATE=0.0
TAX_PROVIDER=  # stripe, avalara, etc.

# Notification Service (for sending payment notifications)
NOTIFICATION_SERVICE_URL=http://notification-service:8001
NOTIFICATION_API_KEY=your_api_key

# Frontend URLs
FRONTEND_URL=http://localhost:3000
PAYMENT_SUCCESS_URL=http://localhost:3000/payment/success
PAYMENT_CANCEL_URL=http://localhost:3000/payment/cancel
SUBSCRIPTION_SUCCESS_URL=http://localhost:3000/subscription/success
SUBSCRIPTION_CANCEL_URL=http://localhost:3000/subscription/cancel

# Monitoring
SENTRY_DSN=  # Optional error tracking
PROMETHEUS_MULTIPROC_DIR=/tmp
This comprehensive payment service implementation includes:

Key Features
1. Service Architecture
FastAPI application with lifespan management

Multi-gateway support (Stripe, PayPal, Razorpay)

Background task processing

Health checks and monitoring

2. API Layer
RESTful endpoints for payments, subscriptions, invoices

Webhook endpoints for external gateways

Webhook management API

Comprehensive error handling

3. Database Integration
PostgreSQL with asyncpg

Connection pooling

Migration management with Alembic

Repository pattern

4. Caching
Redis for session storage

Rate limiting

Idempotency keys

Webhook deduplication

5. Message Queue
RabbitMQ for async processing

Event-driven architecture

Service-to-service communication

6. Background Tasks
Webhook queue processing

Subscription renewal checks

Invoice generation

Dispute monitoring

Metrics aggregation

7. Webhook System
Multi-gateway support

Signature verification

Retry with exponential backoff

Queue-based processing

Status tracking

8. Monitoring & Observability
Prometheus metrics

Health checks (basic, detailed, liveness, readiness)

Request tracking with correlation IDs

Structured logging

9. Security
CORS configuration

API key authentication

Webhook signature verification

Idempotency protection

Input validation

10. Deployment Ready
Docker support

Kubernetes manifests

Environment-based configuration

Graceful shutdown

