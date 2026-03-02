"""Production environment configuration."""

from .base import BaseConfig
import os


class ProductionConfig(BaseConfig):
    """Production configuration."""
    
    # Environment
    DEBUG = False
    TESTING = False
    ENV = 'production'
    
    # Database
    DB_HOST = os.getenv('DB_HOST', '')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', '')
    DB_USER = os.getenv('DB_USER', '')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '50'))
    DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    DB_POOL_TIMEOUT = 60
    DB_POOL_RECYCLE = 1800
    DB_ECHO = False
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', '')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    REDIS_SSL = True
    
    # Elasticsearch
    ELASTICSEARCH_HOSTS = os.getenv('ELASTICSEARCH_HOSTS', '').split(',')
    ELASTICSEARCH_USER = os.getenv('ELASTICSEARCH_USER', '')
    ELASTICSEARCH_PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD', '')
    ELASTICSEARCH_VERIFY_CERTS = True
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', '')  # Must be set in production
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=1)
    
    # CORS
    CORS_ALLOW_ORIGINS = os.getenv('CORS_ALLOW_ORIGINS', '').split(',')
    CORS_ALLOW_CREDENTIALS = True
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_DEFAULT = '100/minute'
    RATE_LIMIT_STRICT = '5/second'
    
    # Cache
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_KEY_PREFIX = 'parking:prod:'
    
    # Celery
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
    CELERY_TASK_TIME_LIMIT = 5 * 60
    CELERY_TASK_SOFT_TIME_LIMIT = 4 * 60
    
    # Logging
    LOG_LEVEL = 'WARNING'
    LOG_JSON_FORMAT = True
    LOGS_DIR = '/var/log/parking'
    
    # Monitoring
    SENTRY_DSN = os.getenv('SENTRY_DSN', '')
    SENTRY_ENABLED = bool(SENTRY_DSN)
    SENTRY_ENVIRONMENT = 'production'
    SENTRY_TRACES_SAMPLE_RATE = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1'))
    
    PROMETHEUS_ENABLED = True
    PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', '9090'))
    
    # Email - production email settings
    MAIL_SERVER = os.getenv('MAIL_SERVER', '')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@parking.com')
    
    # SMS
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')
    
    # Payment - live keys in production
    STRIPE_API_KEY = os.getenv('STRIPE_API_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', '')
    PAYPAL_MODE = 'live'
    
    # Storage
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET', '')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    
    # Feature Flags - all enabled in production
    FEATURE_RESERVATION_CONFIRMATION = True
    FEATURE_WAITLIST = True
    FEATURE_RECURRING_RESERVATIONS = True
    FEATURE_PAYMENT_REFUNDS = True
    FEATURE_NOTIFICATIONS = True
    FEATURE_ANALYTICS = True