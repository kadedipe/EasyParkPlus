"""Configuration constants for the parking management system."""

from datetime import timedelta
from typing import Dict, Any


class Config:
    """System configuration constants."""
    
    # Application settings
    APP_NAME = "Parking Management System"
    API_VERSION = "v1"
    API_PREFIX = f"/api/{API_VERSION}"
    
    # Database settings
    DB_POOL_SIZE = 20
    DB_MAX_OVERFLOW = 40
    DB_POOL_TIMEOUT = 30
    
    # Authentication settings
    JWT_SECRET_KEY = "your-secret-key-here"  # Should be in environment variables
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # Password settings
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 100
    PASSWORD_HASH_ALGORITHM = "bcrypt"
    
    # Reservation settings
    RESERVATION_MAX_DURATION_HOURS = 24
    RESERVATION_MIN_ADVANCE_HOURS = 1
    RESERVATION_MAX_ADVANCE_DAYS = 30
    RESERVATION_GRACE_PERIOD_MINUTES = 15
    RESERVATION_CANCELLATION_WINDOW_HOURS = 2
    RESERVATION_PENDING_EXPIRY_MINUTES = 30
    
    # Parking spot settings
    SPOT_TYPE_CAPACITY: Dict[str, int] = {
        "standard": 1,
        "vip": 1,
        "ev_charging": 1,
        "oversize": 2,
        "disabled": 1,
        "motorcycle": 0.5
    }
    
    SPOT_TYPE_PRICE_MULTIPLIER: Dict[str, float] = {
        "standard": 1.0,
        "vip": 1.5,
        "ev_charging": 1.2,
        "oversize": 1.3,
        "disabled": 1.0,
        "motorcycle": 0.7
    }
    
    # Payment settings
    PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "apple_pay", "google_pay"]
    CURRENCY = "USD"
    TAX_RATE = 0.1  # 10%
    
    # Notification settings
    NOTIFICATION_TYPES = [
        "reservation_confirmation",
        "reservation_reminder",
        "reservation_cancellation",
        "payment_receipt",
        "payment_failed",
        "waitlist_available",
        "account_verification",
        "password_reset"
    ]
    
    REMINDER_TIME_BEFORE_HOURS = 2
    WAITLIST_NOTIFICATION_HOURS = 1
    
    # Cache settings
    CACHE_TTL: Dict[str, int] = {
        "user": 3600,  # 1 hour
        "reservation": 300,  # 5 minutes
        "spot": 600,  # 10 minutes
        "stats": 1800,  # 30 minutes
        "session": 86400,  # 24 hours
    }
    
    # Rate limiting
    RATE_LIMIT_DEFAULT = "100/hour"
    RATE_LIMIT_AUTH = "5/minute"
    RATE_LIMIT_PAYMENT = "10/minute"
    RATE_LIMIT_ADMIN = "1000/hour"
    
    # Business hours
    BUSINESS_HOURS = {
        "monday": {"open": "08:00", "close": "22:00"},
        "tuesday": {"open": "08:00", "close": "22:00"},
        "wednesday": {"open": "08:00", "close": "22:00"},
        "thursday": {"open": "08:00", "close": "22:00"},
        "friday": {"open": "08:00", "close": "23:00"},
        "saturday": {"open": "09:00", "close": "23:00"},
        "sunday": {"open": "09:00", "close": "21:00"},
    }
    
    # Pricing
    HOURLY_RATE = 5.0  # Base hourly rate in USD
    DAILY_MAX_RATE = 30.0  # Maximum daily rate
    WEEKLY_RATE = 150.0  # Weekly flat rate
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            key: value for key, value in cls.__dict__.items()
            if not key.startswith('__') and not callable(value)
        }