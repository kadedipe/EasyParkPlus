"""Testing environment configuration."""

from .base import BaseConfig
from datetime import timedelta


class TestingConfig(BaseConfig):
    """Testing configuration."""
    
    # Environment
    DEBUG = False
    TESTING = True
    ENV = 'testing'
    
    # Database - use test database
    DB_NAME = 'parking_test'
    DB_ECHO = False
    DB_POOL_SIZE = 1
    
    # Security - test keys
    SECRET_KEY = 'test-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=5)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=10)
    
    # CORS
    CORS_ALLOW_ORIGINS = ['http://localhost:3000']
    
    # Rate Limiting - disabled in testing
    RATE_LIMIT_ENABLED = False
    
    # Cache - use null cache in testing
    CACHE_TYPE = 'null'
    
    # Logging - minimal in testing
    LOG_LEVEL = 'WARNING'
    LOG_JSON_FORMAT = False
    LOGS_DIR = None  # Disable file logging
    
    # Monitoring - disabled in testing
    SENTRY_ENABLED = False
    PROMETHEUS_ENABLED = False
    
    # Email - use dummy backend in testing
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 1025
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    
    # Payment - use mock keys
    STRIPE_API_KEY = 'sk_test_mock'
    PAYPAL_CLIENT_ID = 'mock_client_id'
    PAYPAL_CLIENT_SECRET = 'mock_client_secret'
    
    # Feature Flags - controlled in tests
    FEATURE_RESERVATION_CONFIRMATION = True
    FEATURE_WAITLIST = True
    FEATURE_RECURRING_RESERVATIONS = True
    FEATURE_PAYMENT_REFUNDS = True
    FEATURE_NOTIFICATIONS = True
    FEATURE_ANALYTICS = False  # Disable analytics in tests