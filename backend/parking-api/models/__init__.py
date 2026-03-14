"""
Database models for the Parking Management System.
All models inherit from Base and use SQLAlchemy 2.0 style.
"""

from .base import Base, TimestampMixin, SoftDeleteMixin, AuditMixin
from .user import User
from .vehicle import Vehicle
from .parking_spot import ParkingSpot, ParkingSpotStatus, ParkingSpotType
from .reservation import Reservation, ReservationStatus
from .payment import Payment, PaymentStatus, PaymentMethod
from .review import Review
from .notification import Notification, NotificationType
from .waitlist import WaitlistEntry, WaitlistStatus
from .maintenance import MaintenanceRecord, MaintenanceStatus, MaintenanceType
from .price_rule import PriceRule, RuleType, AdjustmentType
from .discount import Discount, DiscountType
from .loyalty import LoyaltyProgram, LoyaltyTier
from .audit_log import AuditLog
from .blacklisted_token import BlacklistedToken

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    
    # User related
    "User",
    "Vehicle",
    
    # Parking related
    "ParkingSpot",
    "ParkingSpotStatus",
    "ParkingSpotType",
    "MaintenanceRecord",
    "MaintenanceStatus",
    "MaintenanceType",
    
    # Reservation related
    "Reservation",
    "ReservationStatus",
    
    # Payment related
    "Payment",
    "PaymentStatus",
    "PaymentMethod",
    
    # Reviews
    "Review",
    
    # Notifications
    "Notification",
    "NotificationType",
    
    # Waitlist
    "WaitlistEntry",
    "WaitlistStatus",
    
    # Pricing
    "PriceRule",
    "RuleType",
    "AdjustmentType",
    "Discount",
    "DiscountType",
    
    # Loyalty
    "LoyaltyProgram",
    "LoyaltyTier",
    
    # Audit
    "AuditLog",
    "BlacklistedToken",
]