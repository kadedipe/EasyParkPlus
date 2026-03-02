"""Staging environment configuration."""

from .base import BaseConfig
import os


class StagingConfig(BaseConfig):
    """Staging configuration."""
    
    # Environment
    DEBUG = False
    TESTING = False
    ENV = 'staging'
    
    # Database
    DB_HOST = os.getenv('DB_HOST', 'staging-db.example.com')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'parking_staging')
    DB_USER = os.getenv('DB_USER', 'parking_app')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_POOL_SIZE = 20
    DB_MAX_OVERFLOW = 10
    DB_ECHO = False
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'staging-redis.example.com')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
    REDIS_DB = 0
    
    # Elasticsearch
    ELASTICSEARCH_HOSTS = os.getenv('ELASTICSEARCH_HOSTS', 'staging-es:9200').split(',')
    ELASTICSEARCH_USER = os.getenv('ELASTICSEARCH_USER', '')
    ELASTICSEARCH_PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD', '')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'staging-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    
    # CORS
    CORS_ALLOW_ORIGINS = os.getenv('CORS_ALLOW_ORIGINS', 'https://staging.parking.com').split(',')
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_DEFAULT = '200/minute'
    
    # Cache
    CACHE_TYPE = 'redis'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_JSON_FORMAT = True
    LOGS_DIR = '/var/log/parking'
    
    # Monitoring
    SENTRY_DSN = os.getenv('SENTRY_DSN', '')
    SENTRY_ENABLED = bool(SENTRY_DSN)
    SENTRY_ENVIRONMENT = 'staging'
    SENTRY_TRACES_SAMPLE_RATE = 0.5
    
    PROMETHEUS_ENABLED = True
    PROMETHEUS_PORT = 9090
    
    # Email - use real SMTP in staging
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@staging.parking.com')
    
    # Payment - use test keys in staging
    STRIPE_API_KEY = os.getenv('STRIPE_API_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', '')
    PAYPAL_MODE = 'sandbox'