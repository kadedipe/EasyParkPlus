"""Base configuration class with common settings."""

import os
from typing import List, Optional, Dict, Any
from datetime import timedelta
from pathlib import Path


class BaseConfig:
    """Base configuration with common settings."""
    
    # Application
    APP_NAME = "Parking Management System"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "Enterprise parking management system"
    
    # Paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    LOGS_DIR = BASE_DIR / 'logs'
    DATA_DIR = BASE_DIR / 'data'
    UPLOAD_DIR = BASE_DIR / 'uploads'
    TEMP_DIR = BASE_DIR / 'tmp'
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_ALGORITHM = 'HS256'
    
    # Password hashing
    BCRYPT_ROUNDS = 12
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    
    # Database
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'parking_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '20'))
    DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))
    DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))
    DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))
    DB_ECHO = False
    
    @property
    def DATABASE_URL(self) -> str:
        """Get database URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """Get async database URL."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
    REDIS_SSL = os.getenv('REDIS_SSL', 'false').lower() == 'true'
    
    @property
    def REDIS_URL(self) -> str:
        """Get Redis URL."""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Elasticsearch
    ELASTICSEARCH_HOSTS = os.getenv('ELASTICSEARCH_HOSTS', 'localhost:9200').split(',')
    ELASTICSEARCH_USER = os.getenv('ELASTICSEARCH_USER', '')
    ELASTICSEARCH_PASSWORD = os.getenv('ELASTICSEARCH_PASSWORD', '')
    ELASTICSEARCH_VERIFY_CERTS = os.getenv('ELASTICSEARCH_VERIFY_CERTS', 'true').lower() == 'true'
    
    # API
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '8000'))
    API_WORKERS = int(os.getenv('API_WORKERS', '4'))
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))
    API_MAX_REQUEST_SIZE = int(os.getenv('API_MAX_REQUEST_SIZE', '10485760'))  # 10MB
    
    # CORS
    CORS_ALLOW_ORIGINS = os.getenv('CORS_ALLOW_ORIGINS', '*').split(',')
    CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
    CORS_ALLOW_HEADERS = ['*']
    CORS_ALLOW_CREDENTIALS = True
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_DEFAULT = '100/minute'
    RATE_LIMIT_STRICT = '5/second'
    
    # Cache
    CACHE_TYPE = 'redis'  # redis, memory, null
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    CACHE_KEY_PREFIX = 'parking:'
    
    # Celery
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True
    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_TIME_LIMIT = 30 * 60
    CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    LOG_JSON_FORMAT = False
    
    # Monitoring
    SENTRY_DSN = os.getenv('SENTRY_DSN', '')
    SENTRY_ENABLED = bool(SENTRY_DSN)
    SENTRY_ENVIRONMENT = os.getenv('SENTRY_ENVIRONMENT', 'development')
    SENTRY_TRACES_SAMPLE_RATE = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1'))
    
    # Prometheus
    PROMETHEUS_ENABLED = True
    PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', '9090'))
    PROMETHEUS_METRICS_PATH = '/metrics'
    
    # Feature Flags
    FEATURE_RESERVATION_CONFIRMATION = True
    FEATURE_WAITLIST = True
    FEATURE_RECURRING_RESERVATIONS = True
    FEATURE_PAYMENT_REFUNDS = True
    FEATURE_NOTIFICATIONS = True
    FEATURE_ANALYTICS = True
    
    # Pagination
    PAGINATION_DEFAULT_PAGE = 1
    PAGINATION_DEFAULT_PER_PAGE = 20
    PAGINATION_MAX_PER_PAGE = 100
    
    # File Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    UPLOAD_FOLDER = 'uploads'
    
    # Timezone
    TIMEZONE = 'UTC'
    
    # Email
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@parking.com')
    
    # SMS
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')
    
    # Push Notifications
    FIREBASE_CREDENTIALS = os.getenv('FIREBASE_CREDENTIALS', '')
    APNS_KEY_ID = os.getenv('APNS_KEY_ID', '')
    APNS_TEAM_ID = os.getenv('APNS_TEAM_ID', '')
    APNS_BUNDLE_ID = os.getenv('APNS_BUNDLE_ID', '')
    
    # Payment Gateway
    STRIPE_API_KEY = os.getenv('STRIPE_API_KEY', '')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
    STRIPE_API_VERSION = '2023-10-16'
    
    PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
    PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_CLIENT_SECRET', '')
    PAYPAL_MODE = os.getenv('PAYPAL_MODE', 'sandbox')  # sandbox or live
    
    # Parking Rules
    MIN_RESERVATION_HOURS = 1
    MAX_RESERVATION_HOURS = 24
    MAX_ADVANCE_DAYS = 30
    CANCELLATION_WINDOW_HOURS = 2
    GRACE_PERIOD_MINUTES = 30
    NO_SHOW_THRESHOLD_MINUTES = 30
    
    # Pricing
    BASE_HOURLY_RATE = 3.00
    VIP_HOURLY_RATE = 8.00
    OVERSIZE_HOURLY_RATE = 5.00
    EV_CHARGING_FEE_PER_HOUR = 1.00
    
    # Discounts
    EARLY_BIRD_DISCOUNT = 10.0  # percent
    EARLY_BIRD_START_HOUR = 6
    EARLY_BIRD_END_HOUR = 9
    
    EVENING_DISCOUNT = 15.0  # percent
    EVENING_START_HOUR = 18
    EVENING_END_HOUR = 22
    
    WEEKLY_DISCOUNT = 5.0  # percent
    MONTHLY_DISCOUNT = 10.0  # percent
    
    # Waitlist
    MAX_WAITLIST_POSITION = 10
    WAITLIST_NOTIFICATION_HOURS = 2
    WAITLIST_EXPIRY_DAYS = 2
    
    # Recurring Reservations
    MAX_RECURRING_OCCURRENCES = 52
    MAX_RECURRING_MONTHS = 12
    
    # Spot Management
    SPOT_MAINTENANCE_DURATION_HOURS = 2
    SPOT_CLEANUP_MINUTES = 15