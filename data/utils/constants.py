"""Constants for the parking management system.

This module defines all constant values used throughout the application,
including status codes, error codes, configuration defaults, and other
immutable values.
"""

from enum import Enum, IntEnum, auto
from typing import Dict, List, Tuple, Any, Optional
from datetime import timedelta


# ============================================================================
# Application Constants
# ============================================================================

class AppConstants:
    """Application-wide constants."""
    
    # Application info
    APP_NAME = "Parking Management System"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "Enterprise parking management system"
    
    # API settings
    API_PREFIX = "/api"
    API_V1_PREFIX = "/api/v1"
    API_V2_PREFIX = "/api/v2"
    API_DOCS_URL = "/docs"
    API_REDOC_URL = "/redoc"
    
    # Date/time formats
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    DATETIME_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
    TIME_FORMAT = "%H:%M:%S"
    TIME_FORMAT_HM = "%H:%M"
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    DEFAULT_PAGE = 1
    
    # Cache keys
    CACHE_KEY_PREFIX = "parking:"
    CACHE_KEY_SEPARATOR = ":"
    
    # File upload
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    ALLOWED_DOCUMENT_TYPES = ['application/pdf', 'text/plain']
    
    # Rate limiting
    RATE_LIMIT_WINDOW = 60  # seconds
    RATE_LIMIT_DEFAULT = 100  # requests per window
    
    # Timeouts
    DEFAULT_TIMEOUT = 30  # seconds
    LONG_TIMEOUT = 120  # seconds
    SHORT_TIMEOUT = 5  # seconds


# ============================================================================
# Environment Constants
# ============================================================================

class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all environment values."""
        return [env.value for env in cls]


# ============================================================================
# Reservation Constants
# ============================================================================

class ReservationStatus(str, Enum):
    """Reservation status types."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    EXPIRED = "expired"
    
    @classmethod
    def active_statuses(cls) -> List[str]:
        """Get active reservation statuses."""
        return [cls.CONFIRMED.value, cls.CHECKED_IN.value]
    
    @classmethod
    def completed_statuses(cls) -> List[str]:
        """Get completed reservation statuses."""
        return [cls.COMPLETED.value, cls.CANCELLED.value, cls.NO_SHOW.value, cls.EXPIRED.value]
    
    @classmethod
    def cancellable_statuses(cls) -> List[str]:
        """Get statuses that can be cancelled."""
        return [cls.PENDING.value, cls.CONFIRMED.value]
    
    @classmethod
    def checkin_allowed_statuses(cls) -> List[str]:
        """Get statuses that allow check-in."""
        return [cls.CONFIRMED.value]
    
    @classmethod
    def checkout_allowed_statuses(cls) -> List[str]:
        """Get statuses that allow check-out."""
        return [cls.CHECKED_IN.value]


class ReservationType(str, Enum):
    """Reservation type types."""
    STANDARD = "standard"
    VIP = "vip"
    EV_CHARGING = "ev_charging"
    OVERSIZE = "oversize"
    DISABLED = "disabled"
    MONTHLY = "monthly"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all reservation type values."""
        return [rt.value for rt in cls]
    
    @classmethod
    def requires_special_spot(cls) -> List[str]:
        """Get types that require special spots."""
        return [cls.VIP.value, cls.EV_CHARGING.value, cls.OVERSIZE.value, cls.DISABLED.value]


class ReservationSource(str, Enum):
    """Reservation source types."""
    WEB = "web"
    MOBILE_APP = "mobile_app"
    API = "api"
    ADMIN = "admin"
    WALK_IN = "walk_in"
    PHONE = "phone"
    PARTNER = "partner"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all source values."""
        return [src.value for src in cls]


class PaymentStatus(str, Enum):
    """Payment status types."""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    CANCELLED = "cancelled"
    
    @classmethod
    def successful_statuses(cls) -> List[str]:
        """Get successful payment statuses."""
        return [cls.PAID.value, cls.AUTHORIZED.value]
    
    @classmethod
    def failed_statuses(cls) -> List[str]:
        """Get failed payment statuses."""
        return [cls.FAILED.value, cls.CANCELLED.value]


# ============================================================================
# Parking Spot Constants
# ============================================================================

class ParkingSpotType(str, Enum):
    """Parking spot type types."""
    STANDARD = "standard"
    VIP = "vip"
    EV_CHARGING = "ev_charging"
    OVERSIZE = "oversize"
    DISABLED = "disabled"
    MOTORCYCLE = "motorcycle"
    COMPACT = "compact"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all spot type values."""
        return [st.value for st in cls]
    
    @classmethod
    def get_base_rate(cls, spot_type: str) -> float:
        """Get base hourly rate for spot type."""
        rates = {
            cls.STANDARD.value: 3.00,
            cls.VIP.value: 8.00,
            cls.EV_CHARGING.value: 3.00,
            cls.OVERSIZE.value: 5.00,
            cls.DISABLED.value: 2.50,
            cls.MOTORCYCLE.value: 2.00,
            cls.COMPACT.value: 2.50,
        }
        return rates.get(spot_type, 3.00)


class ParkingSpotStatus(str, Enum):
    """Parking spot status types."""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"
    
    @classmethod
    def available_statuses(cls) -> List[str]:
        """Get statuses that indicate availability."""
        return [cls.AVAILABLE.value]
    
    @classmethod
    def unavailable_statuses(cls) -> List[str]:
        """Get statuses that indicate unavailability."""
        return [cls.OCCUPIED.value, cls.RESERVED.value, cls.MAINTENANCE.value, cls.OUT_OF_SERVICE.value]


class ChargerType(str, Enum):
    """EV charger type types."""
    LEVEL_1 = "level_1"  # 120V, ~3-5 miles range per hour
    LEVEL_2 = "level_2"  # 240V, ~10-20 miles range per hour
    DC_FAST = "dc_fast"  # 480V+, ~60-80 miles range per 20 minutes
    TESLA = "tesla"  # Tesla supercharger
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all charger type values."""
        return [ct.value for ct in cls]
    
    @classmethod
    def get_charging_rate(cls, charger_type: str) -> float:
        """Get charging rate in kW."""
        rates = {
            cls.LEVEL_1.value: 1.4,
            cls.LEVEL_2.value: 7.2,
            cls.DC_FAST.value: 50.0,
            cls.TESLA.value: 120.0,
        }
        return rates.get(charger_type, 0)


# ============================================================================
# User Constants
# ============================================================================

class UserRole(str, Enum):
    """User role types."""
    CUSTOMER = "customer"
    VIP_CUSTOMER = "vip_customer"
    BUSINESS_CUSTOMER = "business_customer"
    ATTENDANT = "attendant"
    MANAGER = "manager"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all role values."""
        return [role.value for role in cls]
    
    @classmethod
    def customer_roles(cls) -> List[str]:
        """Get customer-type roles."""
        return [cls.CUSTOMER.value, cls.VIP_CUSTOMER.value, cls.BUSINESS_CUSTOMER.value]
    
    @classmethod
    def staff_roles(cls) -> List[str]:
        """Get staff-type roles."""
        return [cls.ATTENDANT.value, cls.MANAGER.value, cls.ADMIN.value, cls.SUPER_ADMIN.value]
    
    @classmethod
    def admin_roles(cls) -> List[str]:
        """Get admin-type roles."""
        return [cls.ADMIN.value, cls.SUPER_ADMIN.value]


class UserStatus(str, Enum):
    """User account status types."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    PENDING_VERIFICATION = "pending_verification"
    DELETED = "deleted"
    
    @classmethod
    def active_statuses(cls) -> List[str]:
        """Get statuses that indicate active account."""
        return [cls.ACTIVE.value]
    
    @classmethod
    def inactive_statuses(cls) -> List[str]:
        """Get statuses that indicate inactive account."""
        return [cls.INACTIVE.value, cls.SUSPENDED.value, cls.LOCKED.value, cls.DELETED.value]


class UserVerificationStatus(str, Enum):
    """User verification status types."""
    UNVERIFIED = "unverified"
    EMAIL_VERIFIED = "email_verified"
    PHONE_VERIFIED = "phone_verified"
    FULLY_VERIFIED = "fully_verified"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all verification status values."""
        return [vs.value for vs in cls]


# ============================================================================
# Vehicle Constants
# ============================================================================

class VehicleType(str, Enum):
    """Vehicle type types."""
    SEDAN = "sedan"
    SUV = "suv"
    TRUCK = "truck"
    VAN = "van"
    MOTORCYCLE = "motorcycle"
    RV = "rv"
    BUS = "bus"
    COMPACT = "compact"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all vehicle type values."""
        return [vt.value for vt in cls]
    
    @classmethod
    def requires_oversize(cls) -> List[str]:
        """Get vehicle types that require oversize spots."""
        return [cls.TRUCK.value, cls.RV.value, cls.BUS.value]
    
    @classmethod
    def can_use_compact(cls) -> List[str]:
        """Get vehicle types that can use compact spots."""
        return [cls.SEDAN.value, cls.COMPACT.value, cls.MOTORCYCLE.value]


# ============================================================================
# Payment Constants
# ============================================================================

class PaymentMethod(str, Enum):
    """Payment method types."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO = "crypto"
    COMPANY_ACCOUNT = "company_account"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all payment method values."""
        return [pm.value for pm in cls]
    
    @classmethod
    def digital_methods(cls) -> List[str]:
        """Get digital payment methods."""
        return [
            cls.CREDIT_CARD.value,
            cls.DEBIT_CARD.value,
            cls.PAYPAL.value,
            cls.APPLE_PAY.value,
            cls.GOOGLE_PAY.value,
            cls.CRYPTO.value,
        ]
    
    @classmethod
    def requires_online_processing(cls) -> List[str]:
        """Get methods requiring online processing."""
        return cls.digital_methods()


class PaymentProvider(str, Enum):
    """Payment provider types."""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    BRAINTREE = "braintree"
    AUTHORIZE_NET = "authorize_net"
    SQUARE = "square"
    ADYEN = "adyen"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all provider values."""
        return [pp.value for pp in cls]


class Currency(str, Enum):
    """Currency types."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    CHF = "CHF"
    CNY = "CNY"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all currency values."""
        return [c.value for c in cls]
    
    @classmethod
    def get_symbol(cls, currency: str) -> str:
        """Get currency symbol."""
        symbols = {
            cls.USD.value: "$",
            cls.EUR.value: "€",
            cls.GBP.value: "£",
            cls.JPY.value: "¥",
            cls.CAD.value: "C$",
            cls.AUD.value: "A$",
            cls.CHF.value: "Fr",
            cls.CNY.value: "¥",
        }
        return symbols.get(currency, "$")


# ============================================================================
# Waitlist Constants
# ============================================================================

class WaitlistStatus(str, Enum):
    """Waitlist entry status types."""
    ACTIVE = "active"
    NOTIFIED = "notified"
    EXPIRED = "expired"
    CONVERTED = "converted"
    CANCELLED = "cancelled"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all waitlist status values."""
        return [ws.value for ws in cls]


# ============================================================================
# Notification Constants
# ============================================================================

class NotificationType(str, Enum):
    """Notification type types."""
    RESERVATION_CONFIRMATION = "reservation_confirmation"
    RESERVATION_REMINDER = "reservation_reminder"
    RESERVATION_CANCELLATION = "reservation_cancellation"
    RESERVATION_MODIFICATION = "reservation_modification"
    RESERVATION_COMPLETED = "reservation_completed"
    PAYMENT_RECEIPT = "payment_receipt"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_REFUND = "payment_refund"
    WAITLIST_AVAILABLE = "waitlist_available"
    WAITLIST_CONFIRMATION = "waitlist_confirmation"
    ACCOUNT_VERIFICATION = "account_verification"
    PASSWORD_RESET = "password_reset"
    PROMOTIONAL = "promotional"
    SYSTEM_ALERT = "system_alert"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all notification type values."""
        return [nt.value for nt in cls]
    
    @classmethod
    def transactional_types(cls) -> List[str]:
        """Get transactional notification types."""
        return [
            cls.RESERVATION_CONFIRMATION.value,
            cls.RESERVATION_CANCELLATION.value,
            cls.PAYMENT_RECEIPT.value,
            cls.PAYMENT_FAILED.value,
            cls.ACCOUNT_VERIFICATION.value,
            cls.PASSWORD_RESET.value,
        ]


class NotificationChannel(str, Enum):
    """Notification channel types."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all channel values."""
        return [nc.value for nc in cls]


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all priority values."""
        return [np.value for np in cls]


# ============================================================================
# Audit Log Constants
# ============================================================================

class AuditAction(str, Enum):
    """Audit log action types."""
    # User actions
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    
    # Reservation actions
    RESERVATION_CREATED = "reservation_created"
    RESERVATION_UPDATED = "reservation_updated"
    RESERVATION_CANCELLED = "reservation_cancelled"
    RESERVATION_CHECKED_IN = "reservation_checked_in"
    RESERVATION_CHECKED_OUT = "reservation_checked_out"
    RESERVATION_COMPLETED = "reservation_completed"
    RESERVATION_NO_SHOW = "reservation_no_show"
    
    # Payment actions
    PAYMENT_PROCESSED = "payment_processed"
    PAYMENT_REFUNDED = "payment_refunded"
    PAYMENT_FAILED = "payment_failed"
    
    # Spot actions
    SPOT_CREATED = "spot_created"
    SPOT_UPDATED = "spot_updated"
    SPOT_DELETED = "spot_deleted"
    SPOT_MAINTENANCE = "spot_maintenance"
    
    # System actions
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    SYSTEM_ERROR = "system_error"
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all action values."""
        return [aa.value for aa in cls]


class AuditEntity(str, Enum):
    """Audit log entity types."""
    USER = "user"
    RESERVATION = "reservation"
    PARKING_SPOT = "parking_spot"
    VEHICLE = "vehicle"
    PAYMENT = "payment"
    WAITLIST = "waitlist"
    RECURRING = "recurring"
    CONFIG = "config"
    SYSTEM = "system"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all entity values."""
        return [ae.value for ae in cls]


# ============================================================================
# Error Constants
# ============================================================================

class ErrorCode(str, Enum):
    """Error code types."""
    # General errors (1000-1999)
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    
    # Validation errors (2000-2999)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"
    VALUE_TOO_LONG = "VALUE_TOO_LONG"
    VALUE_TOO_SHORT = "VALUE_TOO_SHORT"
    VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
    
    # Authentication/Authorization errors (3000-3999)
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # Resource errors (4000-4999)
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    
    # Reservation errors (5000-5999)
    RESERVATION_ERROR = "RESERVATION_ERROR"
    RESERVATION_NOT_FOUND = "RESERVATION_NOT_FOUND"
    RESERVATION_CONFLICT = "RESERVATION_CONFLICT"
    RESERVATION_CANCELLATION_ERROR = "RESERVATION_CANCELLATION_ERROR"
    RESERVATION_CHECKIN_ERROR = "RESERVATION_CHECKIN_ERROR"
    RESERVATION_CHECKOUT_ERROR = "RESERVATION_CHECKOUT_ERROR"
    RESERVATION_EXPIRED = "RESERVATION_EXPIRED"
    RESERVATION_LIMIT_EXCEEDED = "RESERVATION_LIMIT_EXCEEDED"
    INVALID_RESERVATION_TIME = "INVALID_RESERVATION_TIME"
    
    # Payment errors (6000-6999)
    PAYMENT_ERROR = "PAYMENT_ERROR"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_DECLINED = "PAYMENT_DECLINED"
    PAYMENT_REFUND_ERROR = "PAYMENT_REFUND_ERROR"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    PAYMENT_METHOD_ERROR = "PAYMENT_METHOD_ERROR"
    PAYMENT_TIMEOUT = "PAYMENT_TIMEOUT"
    
    # Parking spot errors (7000-7999)
    SPOT_ERROR = "SPOT_ERROR"
    SPOT_NOT_FOUND = "SPOT_NOT_FOUND"
    SPOT_UNAVAILABLE = "SPOT_UNAVAILABLE"
    SPOT_MAINTENANCE = "SPOT_MAINTENANCE"
    INVALID_SPOT_TYPE = "INVALID_SPOT_TYPE"
    
    # User errors (8000-8999)
    USER_ERROR = "USER_ERROR"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    PHONE_ALREADY_EXISTS = "PHONE_ALREADY_EXISTS"
    VERIFICATION_ERROR = "VERIFICATION_ERROR"
    
    # Vehicle errors (9000-9999)
    VEHICLE_ERROR = "VEHICLE_ERROR"
    VEHICLE_NOT_FOUND = "VEHICLE_NOT_FOUND"
    LICENSE_PLATE_EXISTS = "LICENSE_PLATE_EXISTS"
    INVALID_VEHICLE_TYPE = "INVALID_VEHICLE_TYPE"
    VEHICLE_NOT_AUTHORIZED = "VEHICLE_NOT_AUTHORIZED"
    
    # Integration errors (10000-10999)
    INTEGRATION_ERROR = "INTEGRATION_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    QUEUE_ERROR = "QUEUE_ERROR"
    
    # Rate limit errors (11000-11999)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    CONCURRENCY_LIMIT_EXCEEDED = "CONCURRENCY_LIMIT_EXCEEDED"
    
    # File errors (12000-12999)
    FILE_ERROR = "FILE_ERROR"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_UPLOAD_ERROR = "FILE_UPLOAD_ERROR"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    
    @classmethod
    def get_status_code(cls, error_code: str) -> int:
        """Get HTTP status code for error code."""
        status_map = {
            # 400 errors
            cls.VALIDATION_ERROR: 400,
            cls.INVALID_INPUT: 400,
            cls.MISSING_FIELD: 400,
            cls.INVALID_FORMAT: 400,
            cls.VALUE_TOO_LONG: 400,
            cls.VALUE_TOO_SHORT: 400,
            cls.VALUE_OUT_OF_RANGE: 400,
            cls.INVALID_RESERVATION_TIME: 400,
            cls.PAYMENT_METHOD_ERROR: 400,
            cls.INVALID_SPOT_TYPE: 400,
            cls.VERIFICATION_ERROR: 400,
            cls.INVALID_VEHICLE_TYPE: 400,
            cls.FILE_UPLOAD_ERROR: 400,
            cls.FILE_TOO_LARGE: 400,
            cls.INVALID_FILE_TYPE: 400,
            
            # 401 errors
            cls.AUTHENTICATION_ERROR: 401,
            cls.INVALID_CREDENTIALS: 401,
            cls.TOKEN_EXPIRED: 401,
            cls.TOKEN_INVALID: 401,
            
            # 403 errors
            cls.AUTHORIZATION_ERROR: 403,
            cls.INSUFFICIENT_PERMISSIONS: 403,
            cls.ACCOUNT_LOCKED: 403,
            cls.ACCOUNT_DISABLED: 403,
            cls.VEHICLE_NOT_AUTHORIZED: 403,
            
            # 404 errors
            cls.RESOURCE_NOT_FOUND: 404,
            cls.RESERVATION_NOT_FOUND: 404,
            cls.SPOT_NOT_FOUND: 404,
            cls.USER_NOT_FOUND: 404,
            cls.VEHICLE_NOT_FOUND: 404,
            cls.FILE_NOT_FOUND: 404,
            
            # 409 errors
            cls.RESOURCE_ALREADY_EXISTS: 409,
            cls.RESOURCE_CONFLICT: 409,
            cls.RESERVATION_CONFLICT: 409,
            cls.USER_ALREADY_EXISTS: 409,
            cls.EMAIL_ALREADY_EXISTS: 409,
            cls.PHONE_ALREADY_EXISTS: 409,
            cls.LICENSE_PLATE_EXISTS: 409,
            
            # 410 errors
            cls.RESERVATION_EXPIRED: 410,
            
            # 422 errors
            cls.RESERVATION_CANCELLATION_ERROR: 422,
            cls.RESERVATION_CHECKIN_ERROR: 422,
            cls.RESERVATION_CHECKOUT_ERROR: 422,
            
            # 429 errors
            cls.RATE_LIMIT_EXCEEDED: 429,
            cls.CONCURRENCY_LIMIT_EXCEEDED: 429,
            cls.RESERVATION_LIMIT_EXCEEDED: 429,
            
            # 500 errors
            cls.UNKNOWN_ERROR: 500,
            cls.INTERNAL_ERROR: 500,
            cls.DATABASE_ERROR: 500,
            cls.CACHE_ERROR: 500,
            cls.QUEUE_ERROR: 500,
            cls.INTEGRATION_ERROR: 500,
            
            # 501 errors
            cls.NOT_IMPLEMENTED: 501,
            
            # 503 errors
            cls.SERVICE_UNAVAILABLE: 503,
            cls.EXTERNAL_SERVICE_ERROR: 503,
            cls.SPOT_MAINTENANCE: 503,
        }
        return status_map.get(error_code, 500)


# ============================================================================
# HTTP Constants
# ============================================================================

class HTTPMethod(str, Enum):
    """HTTP method types."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all HTTP method values."""
        return [hm.value for hm in cls]


class HTTPStatus(IntEnum):
    """HTTP status codes."""
    # 2xx Success
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # 3xx Redirection
    MOVED_PERMANENTLY = 301
    FOUND = 302
    NOT_MODIFIED = 304
    
    # 4xx Client errors
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    GONE = 410
    UNPROCESSABLE_ENTITY = 422
    TOO_MANY_REQUESTS = 429
    
    # 5xx Server errors
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    
    @classmethod
    def is_success(cls, code: int) -> bool:
        """Check if status code is success."""
        return 200 <= code < 300
    
    @classmethod
    def is_redirect(cls, code: int) -> bool:
        """Check if status code is redirect."""
        return 300 <= code < 400
    
    @classmethod
    def is_client_error(cls, code: int) -> bool:
        """Check if status code is client error."""
        return 400 <= code < 500
    
    @classmethod
    def is_server_error(cls, code: int) -> bool:
        """Check if status code is server error."""
        return 500 <= code < 600


# ============================================================================
# Cache Constants
# ============================================================================

class CacheKey(str, Enum):
    """Cache key prefixes."""
    USER = "user"
    RESERVATION = "reservation"
    PARKING_SPOT = "parking_spot"
    VEHICLE = "vehicle"
    RATE_LIMIT = "rate_limit"
    SESSION = "session"
    TOKEN = "token"
    CONFIG = "config"
    STATS = "stats"
    
    @classmethod
    def get_key(cls, prefix: str, identifier: str) -> str:
        """Get full cache key."""
        return f"{AppConstants.CACHE_KEY_PREFIX}{prefix}{AppConstants.CACHE_KEY_SEPARATOR}{identifier}"


class CacheTTL:
    """Cache TTL values in seconds."""
    # Short TTLs (seconds)
    SHORT = 60  # 1 minute
    MEDIUM = 300  # 5 minutes
    LONG = 3600  # 1 hour
    
    # Specific TTLs
    RATE_LIMIT = 60  # 1 minute
    SESSION = 7200  # 2 hours
    TOKEN = 3600  # 1 hour
    USER_PROFILE = 300  # 5 minutes
    SPOT_AVAILABILITY = 30  # 30 seconds
    STATISTICS = 1800  # 30 minutes
    CONFIG = 3600  # 1 hour


# ============================================================================
# Business Rules Constants
# ============================================================================

class BusinessRules:
    """Business rules and limits."""
    
    # Reservation rules
    MIN_RESERVATION_HOURS = 1
    MAX_RESERVATION_HOURS = 24
    MAX_ADVANCE_DAYS = 30
    CANCELLATION_WINDOW_HOURS = 2
    GRACE_PERIOD_MINUTES = 30
    NO_SHOW_THRESHOLD_MINUTES = 30
    
    # Recurring reservation rules
    MAX_RECURRING_OCCURRENCES = 52
    MAX_RECURRING_MONTHS = 12
    
    # Waitlist rules
    MAX_WAITLIST_POSITION = 10
    WAITLIST_NOTIFICATION_HOURS = 2
    WAITLIST_EXPIRY_DAYS = 2
    
    # Spot management
    SPOT_MAINTENANCE_DURATION_HOURS = 2
    SPOT_CLEANUP_MINUTES = 15
    
    # Discounts
    EARLY_BIRD_DISCOUNT_PERCENT = 10.0
    EARLY_BIRD_START_HOUR = 6
    EARLY_BIRD_END_HOUR = 9
    
    EVENING_DISCOUNT_PERCENT = 15.0
    EVENING_START_HOUR = 18
    EVENING_END_HOUR = 22
    
    WEEKLY_DISCOUNT_PERCENT = 5.0
    MONTHLY_DISCOUNT_PERCENT = 10.0
    
    # Payment rules
    REFUND_WINDOW_DAYS = 30
    PAYMENT_TIMEOUT_SECONDS = 300
    MAX_RETRY_ATTEMPTS = 3
    
    # Security rules
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15


# ============================================================================
# Time Constants
# ============================================================================

class TimeConstants:
    """Time-related constants."""
    
    # Time in seconds
    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_DAY = 86400
    SECONDS_PER_WEEK = 604800
    SECONDS_PER_MONTH = 2592000  # 30 days
    SECONDS_PER_YEAR = 31536000  # 365 days
    
    # Time in minutes
    MINUTES_PER_HOUR = 60
    MINUTES_PER_DAY = 1440
    MINUTES_PER_WEEK = 10080
    
    # Time in hours
    HOURS_PER_DAY = 24
    HOURS_PER_WEEK = 168
    HOURS_PER_MONTH = 720  # 30 days
    
    # Time in days
    DAYS_PER_WEEK = 7
    DAYS_PER_MONTH = 30
    DAYS_PER_YEAR = 365
    DAYS_PER_LEAP_YEAR = 366
    
    # Business hours
    BUSINESS_HOURS_START = 9
    BUSINESS_HOURS_END = 17
    BUSINESS_DAYS = [1, 2, 3, 4, 5]  # Monday to Friday
    
    # Peak hours
    PEAK_HOURS_START = 7
    PEAK_HOURS_END = 19
    
    # Weekend
    WEEKEND_DAYS = [6, 7]  # Saturday, Sunday


# ============================================================================
# Geo Constants
# ============================================================================

class GeoConstants:
    """Geographic constants."""
    
    # Earth radius in various units
    EARTH_RADIUS_KM = 6371
    EARTH_RADIUS_MI = 3959
    EARTH_RADIUS_M = 6371000
    EARTH_RADIUS_FT = 20902230
    
    # Distance thresholds
    NEARBY_THRESHOLD_KM = 1.0
    WALKING_DISTANCE_KM = 0.5
    DRIVING_DISTANCE_KM = 5.0
    
    # Default coordinates (San Francisco)
    DEFAULT_LATITUDE = 37.7749
    DEFAULT_LONGITUDE = -122.4194
    
    # Coordinate bounds
    MIN_LATITUDE = -90
    MAX_LATITUDE = 90
    MIN_LONGITUDE = -180
    MAX_LONGITUDE = 180


# ============================================================================
# Report Constants
# ============================================================================

class ReportType(str, Enum):
    """Report type types."""
    REVENUE = "revenue"
    OCCUPANCY = "occupancy"
    UTILIZATION = "utilization"
    CUSTOMER = "customer"
    PERFORMANCE = "performance"
    AUDIT = "audit"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all report type values."""
        return [rt.value for rt in cls]


class ReportFormat(str, Enum):
    """Report format types."""
    CSV = "csv"
    JSON = "json"
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all report format values."""
        return [rf.value for rf in cls]


class TimePeriod(str, Enum):
    """Time period types."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all time period values."""
        return [tp.value for tp in cls]


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Application
    'AppConstants',
    
    # Environment
    'Environment',
    
    # Reservation
    'ReservationStatus',
    'ReservationType',
    'ReservationSource',
    'PaymentStatus',
    
    # Parking Spot
    'ParkingSpotType',
    'ParkingSpotStatus',
    'ChargerType',
    
    # User
    'UserRole',
    'UserStatus',
    'UserVerificationStatus',
    
    # Vehicle
    'VehicleType',
    
    # Payment
    'PaymentMethod',
    'PaymentProvider',
    'Currency',
    
    # Waitlist
    'WaitlistStatus',
    
    # Notification
    'NotificationType',
    'NotificationChannel',
    'NotificationPriority',
    
    # Audit
    'AuditAction',
    'AuditEntity',
    
    # Error
    'ErrorCode',
    
    # HTTP
    'HTTPMethod',
    'HTTPStatus',
    
    # Cache
    'CacheKey',
    'CacheTTL',
    
    # Business Rules
    'BusinessRules',
    
    # Time
    'TimeConstants',
    
    # Geo
    'GeoConstants',
    
    # Report
    'ReportType',
    'ReportFormat',
    'TimePeriod',
]