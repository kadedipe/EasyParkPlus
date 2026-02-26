"""Configuration package for the parking management system.

This package contains all configuration settings, environment-specific
configurations, and helper functions for managing application configuration.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import timedelta
import warnings

# ============================================================================
# Environment Detection
# ============================================================================

class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

    @classmethod
    def from_string(cls, env_str: str) -> "Environment":
        """Convert string to Environment enum."""
        env_str = env_str.lower()
        for env in cls:
            if env.value == env_str:
                return env
        return cls.DEVELOPMENT


def get_current_environment() -> Environment:
    """Get the current application environment."""
    env_var = os.getenv("PARKING_ENV", "development").lower()
    return Environment.from_string(env_var)


def is_development() -> bool:
    """Check if current environment is development."""
    return get_current_environment() == Environment.DEVELOPMENT


def is_testing() -> bool:
    """Check if current environment is testing."""
    return get_current_environment() == Environment.TESTING


def is_staging() -> bool:
    """Check if current environment is staging."""
    return get_current_environment() == Environment.STAGING


def is_production() -> bool:
    """Check if current environment is production."""
    return get_current_environment() == Environment.PRODUCTION


# ============================================================================
# Base Configuration Classes
# ============================================================================

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str = "localhost"
    port: int = 5432
    name: str = "parking_db"
    user: str = "postgres"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    echo_pool: bool = False
    
    @property
    def url(self) -> str:
        """Get database URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    @property
    def async_url(self) -> str:
        """Get async database URL."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass
class RedisConfig:
    """Redis configuration settings."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    ssl: bool = False
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    max_connections: int = 10
    
    @property
    def url(self) -> str:
        """Get Redis URL."""
        protocol = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{protocol}://{auth}{self.host}:{self.port}/{self.db}"


@dataclass
class APIConfig:
    """API configuration settings."""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    workers: int = 4
    cors_origins: list = field(default_factory=lambda: ["*"])
    rate_limit: int = 100  # requests per minute
    rate_limit_window: int = 60  # seconds
    request_timeout: int = 30
    max_request_size: int = 10_485_760  # 10MB


@dataclass
class AuthConfig:
    """Authentication configuration settings."""
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    reset_token_expire_hours: int = 24
    verification_token_expire_days: int = 3
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_numbers: bool = True
    password_require_special: bool = True
    bcrypt_rounds: int = 12
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"


@dataclass
class ParkingConfig:
    """Parking business logic configuration."""
    # Pricing
    base_hourly_rate: float = 3.00
    vip_hourly_rate: float = 8.00
    oversize_hourly_rate: float = 5.00
    ev_charging_fee_per_hour: float = 1.00
    
    # Reservation rules
    max_reservation_days_in_advance: int = 30
    min_reservation_hours: int = 1
    max_reservation_hours: int = 24
    cancellation_window_hours: int = 2  # hours before start
    grace_period_minutes: int = 30
    no_show_threshold_minutes: int = 30
    
    # Waitlist
    waitlist_notification_hours: int = 2
    waitlist_expiry_days: int = 2
    max_waitlist_position: int = 10
    
    # Recurring reservations
    max_recurring_occurrences: int = 52
    max_recurring_months: int = 12
    
    # Spot management
    spot_maintenance_duration_hours: int = 2
    spot_cleanup_duration_minutes: int = 15
    
    # Discounts
    early_bird_discount_percent: float = 10.0
    early_bird_start_hour: int = 6
    early_bird_end_hour: int = 9
    
    evening_discount_percent: float = 15.0
    evening_start_hour: int = 18
    evening_end_hour: int = 22
    
    weekly_reservation_discount: float = 5.0  # percent
    monthly_reservation_discount: float = 10.0  # percent


@dataclass
class PaymentConfig:
    """Payment processing configuration."""
    provider: str = "stripe"  # stripe, paypal, etc.
    api_key: str = ""
    webhook_secret: str = ""
    currency: str = "usd"
    refund_window_days: int = 30
    require_receipt_email: bool = True
    payment_timeout_seconds: int = 300
    retry_attempts: int = 3
    retry_delay_seconds: int = 5
    
    # Stripe specific
    stripe_api_version: str = "2023-10-16"
    stripe_webhook_tolerance_seconds: int = 300
    
    # PayPal specific
    paypal_mode: str = "sandbox"  # sandbox or live
    paypal_client_id: str = ""
    paypal_client_secret: str = ""


@dataclass
class NotificationConfig:
    """Notification configuration settings."""
    # Email
    email_provider: str = "smtp"  # smtp, sendgrid, ses
    email_from: str = "noreply@parking.com"
    email_from_name: str = "Parking System"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    
    # SMS
    sms_provider: str = "twilio"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    
    # Push notifications
    push_provider: str = "firebase"
    fcm_server_key: str = ""
    apns_key_id: str = ""
    apns_team_id: str = ""
    apns_bundle_id: str = ""
    
    # Templates
    email_template_dir: str = "templates/email"
    sms_template_dir: str = "templates/sms"
    push_template_dir: str = "templates/push"
    
    # Rate limiting
    max_emails_per_minute: int = 100
    max_sms_per_minute: int = 50
    max_push_per_minute: int = 200


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    backend: str = "redis"  # redis, memory, null
    default_timeout: int = 300  # seconds
    key_prefix: str = "parking:"
    version: int = 1
    
    # Redis specific
    redis_url: str = "redis://localhost:6379/0"
    
    # Memory cache specific
    max_entries: int = 1000
    cleanup_interval: int = 60  # seconds


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    log_dir: str = "logs"
    max_bytes: int = 10_485_760  # 10MB
    backup_count: int = 5
    json_format: bool = False
    
    # Handlers
    console_enabled: bool = True
    file_enabled: bool = True
    syslog_enabled: bool = False
    sentry_enabled: bool = False
    
    # Sentry
    sentry_dsn: str = ""
    sentry_environment: str = ""
    sentry_traces_sample_rate: float = 0.1


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""
    metrics_enabled: bool = True
    metrics_port: int = 9090
    metrics_prefix: str = "parking"
    
    # Tracing
    tracing_enabled: bool = False
    tracing_provider: str = "jaeger"
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831
    sampling_rate: float = 0.1
    
    # Health checks
    health_check_path: str = "/health"
    readiness_check_path: str = "/ready"
    liveness_check_path: str = "/live"
    
    # Profiling
    profiling_enabled: bool = False
    profiling_path: str = "/debug/pprof"


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    # CORS
    cors_allow_origins: list = field(default_factory=list)
    cors_allow_methods: list = field(default_factory=lambda: ["*"])
    cors_allow_headers: list = field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = True
    
    # CSRF
    csrf_protection_enabled: bool = True
    csrf_token_length: int = 32
    csrf_token_expiry: int = 3600  # seconds
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"
    rate_limit_trusted_proxies: list = field(default_factory=list)
    
    # Headers
    security_headers_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    
    # Session
    session_cookie_secure: bool = True
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"
    session_max_age: int = 1209600  # 2 weeks
    
    # Encryption
    encryption_key: str = ""
    key_rotation_days: int = 90


# ============================================================================
# Environment-Specific Configurations
# ============================================================================

class DevelopmentConfig:
    """Development environment configuration."""
    
    ENV = Environment.DEVELOPMENT
    DEBUG = True
    TESTING = False
    
    DATABASE = DatabaseConfig(
        host="localhost",
        port=5432,
        name="parking_dev",
        user="postgres",
        password="postgres",
        echo=True
    )
    
    REDIS = RedisConfig(
        host="localhost",
        port=6379,
        db=0
    )
    
    API = APIConfig(
        host="127.0.0.1",
        port=8000,
        debug=True,
        workers=1,
        cors_origins=["http://localhost:3000", "http://localhost:8000"]
    )
    
    AUTH = AuthConfig(
        secret_key="dev-secret-key-change-in-production",
        session_cookie_secure=False  # Allow HTTP in development
    )
    
    PARKING = ParkingConfig()
    
    PAYMENT = PaymentConfig(
        provider="stripe",
        api_key="sk_test_..."  # Use test keys
    )
    
    NOTIFICATION = NotificationConfig(
        email_provider="smtp",
        smtp_host="localhost",
        smtp_port=1025,  # Mailhog default
        smtp_user="",
        smtp_password=""
    )
    
    CACHE = CacheConfig(
        backend="memory",
        default_timeout=60
    )
    
    LOGGING = LoggingConfig(
        level="DEBUG",
        json_format=False,
        sentry_enabled=False
    )
    
    MONITORING = MonitoringConfig(
        metrics_enabled=True,
        tracing_enabled=False,
        profiling_enabled=True
    )
    
    SECURITY = SecurityConfig(
        cors_allow_origins=["http://localhost:3000"],
        rate_limit_enabled=False,  # Disable rate limiting in development
        session_cookie_secure=False
    )


class TestingConfig(DevelopmentConfig):
    """Testing environment configuration."""
    
    ENV = Environment.TESTING
    TESTING = True
    DEBUG = False
    
    DATABASE = DatabaseConfig(
        host="localhost",
        port=5432,
        name="parking_test",
        user="postgres",
        password="postgres",
        echo=False
    )
    
    REDIS = RedisConfig(
        host="localhost",
        port=6379,
        db=1  # Use different DB for tests
    )
    
    API = APIConfig(
        host="127.0.0.1",
        port=8001,  # Different port for tests
        debug=False,
        workers=1,
        cors_origins=[]
    )
    
    AUTH = AuthConfig(
        secret_key="test-secret-key",
        session_cookie_secure=False
    )
    
    PAYMENT = PaymentConfig(
        provider="stripe",
        api_key="sk_test_mock"  # Mock key
    )
    
    NOTIFICATION = NotificationConfig(
        email_provider="memory",  # Store in memory for testing
        sms_provider="memory"
    )
    
    CACHE = CacheConfig(
        backend="memory",
        default_timeout=1  # Short timeout for testing
    )
    
    LOGGING = LoggingConfig(
        level="WARNING",
        console_enabled=False,
        file_enabled=False
    )
    
    MONITORING = MonitoringConfig(
        metrics_enabled=False,
        tracing_enabled=False
    )
    
    SECURITY = SecurityConfig(
        cors_allow_origins=[],
        rate_limit_enabled=False,
        csrf_protection_enabled=False  # Disable for API tests
    )


class StagingConfig(DevelopmentConfig):
    """Staging environment configuration."""
    
    ENV = Environment.STAGING
    DEBUG = False
    TESTING = False
    
    DATABASE = DatabaseConfig(
        host=os.getenv("DB_HOST", "staging-db.example.com"),
        port=int(os.getenv("DB_PORT", "5432")),
        name=os.getenv("DB_NAME", "parking_staging"),
        user=os.getenv("DB_USER", "parking_app"),
        password=os.getenv("DB_PASSWORD", ""),
        pool_size=20,
        echo=False
    )
    
    REDIS = RedisConfig(
        host=os.getenv("REDIS_HOST", "staging-redis.example.com"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=0,
        password=os.getenv("REDIS_PASSWORD", "")
    )
    
    API = APIConfig(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        debug=False,
        workers=4,
        cors_origins=os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []
    )
    
    AUTH = AuthConfig(
        secret_key=os.getenv("SECRET_KEY", "staging-secret-key"),
        session_cookie_secure=True
    )
    
    PAYMENT = PaymentConfig(
        provider="stripe",
        api_key=os.getenv("STRIPE_API_KEY", ""),
        webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", "")
    )
    
    LOGGING = LoggingConfig(
        level="INFO",
        json_format=True,
        sentry_enabled=True,
        sentry_dsn=os.getenv("SENTRY_DSN", "")
    )
    
    SECURITY = SecurityConfig(
        cors_allow_origins=os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [],
        rate_limit_enabled=True,
        session_cookie_secure=True
    )


class ProductionConfig(StagingConfig):
    """Production environment configuration."""
    
    ENV = Environment.PRODUCTION
    
    DATABASE = DatabaseConfig(
        host=os.getenv("DB_HOST", ""),
        port=int(os.getenv("DB_PORT", "5432")),
        name=os.getenv("DB_NAME", ""),
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
        pool_size=int(os.getenv("DB_POOL_SIZE", "50")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "100")),
        echo=False
    )
    
    API = APIConfig(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        debug=False,
        workers=int(os.getenv("WORKERS", "8")),
        rate_limit=int(os.getenv("RATE_LIMIT", "200")),
        max_request_size=int(os.getenv("MAX_REQUEST_SIZE", "10485760"))
    )
    
    AUTH = AuthConfig(
        secret_key=os.getenv("SECRET_KEY", ""),  # Must be set in production
        session_cookie_secure=True,
        bcrypt_rounds=int(os.getenv("BCRYPT_ROUNDS", "12"))
    )
    
    LOGGING = LoggingConfig(
        level="WARNING",
        json_format=True,
        sentry_enabled=True,
        sentry_dsn=os.getenv("SENTRY_DSN", "")
    )
    
    MONITORING = MonitoringConfig(
        metrics_enabled=True,
        tracing_enabled=True,
        sampling_rate=float(os.getenv("TRACING_SAMPLING_RATE", "0.1"))
    )


# ============================================================================
# Configuration Loader
# ============================================================================

class ConfigLoader:
    """Load and manage application configuration."""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load_config()
    
    def load_config(self):
        """Load configuration based on current environment."""
        env = get_current_environment()
        
        if env == Environment.DEVELOPMENT:
            self._config = DevelopmentConfig()
        elif env == Environment.TESTING:
            self._config = TestingConfig()
        elif env == Environment.STAGING:
            self._config = StagingConfig()
        elif env == Environment.PRODUCTION:
            self._config = ProductionConfig()
        else:
            self._config = DevelopmentConfig()
        
        # Override with environment variables
        self._override_from_env()
    
    def _override_from_env(self):
        """Override configuration from environment variables."""
        # Database overrides
        if os.getenv("DB_HOST"):
            self._config.DATABASE.host = os.getenv("DB_HOST")
        if os.getenv("DB_PORT"):
            self._config.DATABASE.port = int(os.getenv("DB_PORT"))
        if os.getenv("DB_NAME"):
            self._config.DATABASE.name = os.getenv("DB_NAME")
        if os.getenv("DB_USER"):
            self._config.DATABASE.user = os.getenv("DB_USER")
        if os.getenv("DB_PASSWORD"):
            self._config.DATABASE.password = os.getenv("DB_PASSWORD")
        
        # Redis overrides
        if os.getenv("REDIS_HOST"):
            self._config.REDIS.host = os.getenv("REDIS_HOST")
        if os.getenv("REDIS_PORT"):
            self._config.REDIS.port = int(os.getenv("REDIS_PORT"))
        if os.getenv("REDIS_PASSWORD"):
            self._config.REDIS.password = os.getenv("REDIS_PASSWORD")
        
        # API overrides
        if os.getenv("PORT"):
            self._config.API.port = int(os.getenv("PORT"))
        if os.getenv("WORKERS"):
            self._config.API.workers = int(os.getenv("WORKERS"))
        if os.getenv("CORS_ORIGINS"):
            self._config.API.cors_origins = os.getenv("CORS_ORIGINS").split(",")
        
        # Auth overrides
        if os.getenv("SECRET_KEY"):
            self._config.AUTH.secret_key = os.getenv("SECRET_KEY")
        if os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"):
            self._config.AUTH.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
        
        # Payment overrides
        if os.getenv("STRIPE_API_KEY"):
            self._config.PAYMENT.api_key = os.getenv("STRIPE_API_KEY")
        if os.getenv("STRIPE_WEBHOOK_SECRET"):
            self._config.PAYMENT.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        # Logging overrides
        if os.getenv("LOG_LEVEL"):
            self._config.LOGGING.level = os.getenv("LOG_LEVEL")
        if os.getenv("SENTRY_DSN"):
            self._config.LOGGING.sentry_dsn = os.getenv("SENTRY_DSN")
            self._config.LOGGING.sentry_enabled = True
    
    @property
    def config(self):
        """Get the loaded configuration."""
        return self._config
    
    def reload(self):
        """Reload configuration."""
        self.load_config()
    
    def as_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config_dict = {}
        
        for attr_name in dir(self._config):
            if not attr_name.startswith("_") and not attr_name.isupper():
                attr_value = getattr(self._config, attr_name)
                if hasattr(attr_value, "__dataclass_fields__"):
                    # Convert dataclass to dict
                    config_dict[attr_name] = {
                        k: v for k, v in attr_value.__dict__.items()
                        if not k.startswith("_")
                    }
                else:
                    config_dict[attr_name] = attr_value
        
        return config_dict
    
    def to_json(self) -> str:
        """Convert configuration to JSON string."""
        return json.dumps(self.as_dict(), default=str, indent=2)


# ============================================================================
# Global Configuration Instance
# ============================================================================

# Create global config instance
_config_loader = ConfigLoader()
config = _config_loader.config


# ============================================================================
# Convenience Functions
# ============================================================================

def get_config() -> Union[DevelopmentConfig, TestingConfig, StagingConfig, ProductionConfig]:
    """Get the current configuration."""
    return config


def reload_config():
    """Reload configuration from environment."""
    _config_loader.reload()


def config_as_dict() -> Dict[str, Any]:
    """Get configuration as dictionary."""
    return _config_loader.as_dict()


def config_as_json() -> str:
    """Get configuration as JSON string."""
    return _config_loader.to_json()


def get_database_url() -> str:
    """Get database URL for current environment."""
    return config.DATABASE.url


def get_async_database_url() -> str:
    """Get async database URL for current environment."""
    return config.DATABASE.async_url


def get_redis_url() -> str:
    """Get Redis URL for current environment."""
    return config.REDIS.url


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return config.DEBUG


def get_environment_name() -> str:
    """Get current environment name as string."""
    return get_current_environment().value


# ============================================================================
# Package Exports
# ============================================================================

__all__ = [
    # Environment
    "Environment",
    "get_current_environment",
    "is_development",
    "is_testing",
    "is_staging",
    "is_production",
    
    # Configuration classes
    "DatabaseConfig",
    "RedisConfig",
    "APIConfig",
    "AuthConfig",
    "ParkingConfig",
    "PaymentConfig",
    "NotificationConfig",
    "CacheConfig",
    "LoggingConfig",
    "MonitoringConfig",
    "SecurityConfig",
    
    # Environment-specific configs
    "DevelopmentConfig",
    "TestingConfig",
    "StagingConfig",
    "ProductionConfig",
    
    # Config loader and instance
    "ConfigLoader",
    "config",
    "get_config",
    "reload_config",
    "config_as_dict",
    "config_as_json",
    
    # Convenience functions
    "get_database_url",
    "get_async_database_url",
    "get_redis_url",
    "is_debug_mode",
    "get_environment_name",
]

# Initialize configuration on import
__version__ = "1.0.0"
__author__ = "Parking Management System Team"