"""Development environment configuration."""

from .base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    
    # Environment
    DEBUG = True
    TESTING = False
    ENV = 'development'
    
    # Database
    DB_ECHO = True
    DB_POOL_SIZE = 5
    
    # Security - less strict in development
    SECRET_KEY = 'dev-secret-key-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # CORS - allow all in development
    CORS_ALLOW_ORIGINS = ['*']
    
    # Rate Limiting - disabled in development
    RATE_LIMIT_ENABLED = False
    
    # Cache - use memory cache in development
    CACHE_TYPE = 'memory'
    
    # Logging - verbose in development
    LOG_LEVEL = 'DEBUG'
    LOG_JSON_FORMAT = False
    
    # Monitoring - disabled in development
    SENTRY_ENABLED = False
    PROMETHEUS_ENABLED = False
    
    # Feature Flags - all enabled in development
    FEATURE_RESERVATION_CONFIRMATION = True
    FEATURE_WAITLIST = True
    FEATURE_RECURRING_RESERVATIONS = True
    FEATURE_PAYMENT_REFUNDS = True
    FEATURE_NOTIFICATIONS = True
    FEATURE_ANALYTICS = True
    
    # Email - use console backend in development
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 1025  # MailHog default
    MAIL_USE_TLS = False
    MAIL_USE_SSL = False
    MAIL_USERNAME = ''
    MAIL_PASSWORD = ''
    
    # Payment - use test keys
    STRIPE_API_KEY = 'sk_test_mock'
    PAYPAL_CLIENT_ID = 'mock_client_id'
    PAYPAL_CLIENT_SECRET = 'mock_client_secret'
    PAYPAL_MODE = 'sandbox'