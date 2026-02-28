"""Application constants."""

from enum import Enum
from typing import Dict, List, Any
from datetime import timedelta


class ReservationStatus(str, Enum):
    """Reservation status types."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    EXPIRED = "expired"


class PaymentStatus(str, Enum):
    """Payment status types."""
    PENDING = "pending"
    AUTHORIZED = "authorized"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


class UserRole(str, Enum):
    """User role types."""
    CUSTOMER = "customer"
    VIP_CUSTOMER = "vip_customer"
    ATTENDANT = "attendant"
    MANAGER = "manager"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    LOCKED = "locked"
    DELETED = "deleted"


class ParkingSpotType(str, Enum):
    """Parking spot types."""
    STANDARD = "standard"
    VIP = "vip"
    EV_CHARGING = "ev_charging"
    OVERSIZE = "oversize"
    DISABLED = "disabled"
    MOTORCYCLE = "motorcycle"


class VehicleType(str, Enum):
    """Vehicle types."""
    SEDAN = "sedan"
    SUV = "suv"
    TRUCK = "truck"
    VAN = "van"
    MOTORCYCLE = "motorcycle"
    RV = "rv"


class NotificationType(str, Enum):
    """Notification types."""
    RESERVATION_CONFIRMATION = "reservation_confirmation"
    RESERVATION_REMINDER = "reservation_reminder"
    RESERVATION_CANCELLATION = "reservation_cancellation"
    PAYMENT_RECEIPT = "payment_receipt"
    PAYMENT_FAILED = "payment_failed"
    WAITLIST_AVAILABLE = "waitlist_available"
    ACCOUNT_VERIFICATION = "account_verification"
    PASSWORD_RESET = "password_reset"


class CacheKeys:
    """Cache key constants."""
    USER = "user:{id}"
    RESERVATION = "reservation:{id}"
    SPOT = "spot:{id}"
    VEHICLE = "vehicle:{id}"
    USER_RESERVATIONS = "user:{user_id}:reservations"
    SPOT_AVAILABILITY = "spot:{spot_id}:availability:{date}"
    STATS = "stats:{type}:{period}"
    SESSION = "session:{session_id}"


class ErrorCodes:
    """Error code constants."""
    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    
    # Auth errors
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_FIELD = "MISSING_FIELD"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    
    # Reservation errors
    RESERVATION_NOT_FOUND = "RESERVATION_NOT_FOUND"
    RESERVATION_CONFLICT = "RESERVATION_CONFLICT"
    RESERVATION_CANCELLATION_ERROR = "RESERVATION_CANCELLATION_ERROR"
    RESERVATION_EXPIRED = "RESERVATION_EXPIRED"
    
    # Payment errors
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_DECLINED = "PAYMENT_DECLINED"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    
    # Rate limit errors
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


constants = {
    "ReservationStatus": ReservationStatus,
    "PaymentStatus": PaymentStatus,
    "UserRole": UserRole,
    "UserStatus": UserStatus,
    "ParkingSpotType": ParkingSpotType,
    "VehicleType": VehicleType,
    "NotificationType": NotificationType,
    "CacheKeys": CacheKeys,
    "ErrorCodes": ErrorCodes,
}