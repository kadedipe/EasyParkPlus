# parking-management/data/migrations/models/enums.py

"""
Centralized Enum definitions for the parking management system.

This module contains all enum classes used across the application to ensure
consistency and provide a single source of truth for enumerated values.
"""

from enum import Enum, unique
from typing import List, Dict, Any, Optional
import re


# ============================================================================
# USER MANAGEMENT ENUMS
# ============================================================================

@unique
class UserStatus(str, Enum):
    """User account status."""
    PENDING = 'pending'
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'
    LOCKED = 'locked'
    DELETED = 'deleted'

    @classmethod
    def get_active_statuses(cls) -> List['UserStatus']:
        """Get statuses considered active."""
        return [cls.ACTIVE]

    @classmethod
    def get_inactive_statuses(cls) -> List['UserStatus']:
        """Get statuses considered inactive."""
        return [cls.INACTIVE, cls.SUSPENDED, cls.LOCKED, cls.DELETED]


@unique
class UserRole(str, Enum):
    """User roles for authorization."""
    USER = 'user'
    OPERATOR = 'operator'
    MANAGER = 'manager'
    ADMIN = 'admin'
    SUPER_ADMIN = 'super_admin'

    @classmethod
    def get_hierarchy(cls) -> Dict['UserRole', int]:
        """Get role hierarchy for permission checking."""
        return {
            cls.USER: 0,
            cls.OPERATOR: 10,
            cls.MANAGER: 20,
            cls.ADMIN: 100,
            cls.SUPER_ADMIN: 1000
        }

    def has_permission_over(self, other: 'UserRole') -> bool:
        """Check if this role has permission over another role."""
        hierarchy = self.get_hierarchy()
        return hierarchy.get(self, 0) >= hierarchy.get(other, 0)


@unique
class AuthMethod(str, Enum):
    """Authentication methods."""
    PASSWORD = 'password'
    OAUTH = 'oauth'
    SAML = 'saml'
    API_KEY = 'api_key'
    CERTIFICATE = 'certificate'
    BIOMETRIC = 'biometric'
    MAGIC_LINK = 'magic_link'
    TWO_FACTOR = 'two_factor'


@unique
class MFAMethod(str, Enum):
    """Multi-factor authentication methods."""
    TOTP = 'totp'
    SMS = 'sms'
    EMAIL = 'email'
    BACKUP_CODE = 'backup_code'
    BIOMETRIC = 'biometric'
    HARDWARE_TOKEN = 'hardware_token'


# ============================================================================
# VEHICLE MANAGEMENT ENUMS
# ============================================================================

@unique
class VehicleStatus(str, Enum):
    """Vehicle status."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'
    BANNED = 'banned'
    PENDING_VERIFICATION = 'pending_verification'
    ARCHIVED = 'archived'
    DELETED = 'deleted'

    @classmethod
    def get_operational_statuses(cls) -> List['VehicleStatus']:
        """Get statuses where vehicle can be parked."""
        return [cls.ACTIVE]


@unique
class VehicleType(str, Enum):
    """Vehicle types."""
    CAR = 'car'
    SUV = 'suv'
    TRUCK = 'truck'
    VAN = 'van'
    MOTORCYCLE = 'motorcycle'
    SCOOTER = 'scooter'
    BICYCLE = 'bicycle'
    EV = 'ev'
    HYBRID = 'hybrid'
    LUXURY = 'luxury'
    CLASSIC = 'classic'
    COMMERCIAL = 'commercial'
    EMERGENCY = 'emergency'
    GOVERNMENT = 'government'
    DIPLOMATIC = 'diplomatic'
    RENTAL = 'rental'
    RIDESHARE = 'rideshare'

    @classmethod
    def get_passenger_vehicles(cls) -> List['VehicleType']:
        """Get passenger vehicle types."""
        return [cls.CAR, cls.SUV, cls.VAN, cls.LUXURY]

    @classmethod
    def get_commercial_vehicles(cls) -> List['VehicleType']:
        """Get commercial vehicle types."""
        return [cls.TRUCK, cls.COMMERCIAL]

    @classmethod
    def get_ev_vehicles(cls) -> List['VehicleType']:
        """Get electric vehicle types."""
        return [cls.EV, cls.HYBRID]


@unique
class VehicleClass(str, Enum):
    """Vehicle classes."""
    COMPACT = 'compact'
    MIDSIZE = 'midsize'
    FULLSIZE = 'fullsize'
    ECONOMY = 'economy'
    PREMIUM = 'premium'
    LUXURY = 'luxury'
    SPORTS = 'sports'
    OFF_ROAD = 'off_road'
    COMMERCIAL_LIGHT = 'commercial_light'
    COMMERCIAL_HEAVY = 'commercial_heavy'


@unique
class FuelType(str, Enum):
    """Fuel types."""
    GASOLINE = 'gasoline'
    DIESEL = 'diesel'
    ELECTRIC = 'electric'
    HYBRID = 'hybrid'
    PLUG_IN_HYBRID = 'plug_in_hybrid'
    HYDROGEN = 'hydrogen'
    CNG = 'cng'
    LPG = 'lpg'
    ETHANOL = 'ethanol'

    @classmethod
    def get_fossil_fuels(cls) -> List['FuelType']:
        """Get fossil fuel types."""
        return [cls.GASOLINE, cls.DIESEL]

    @classmethod
    def get_alternative_fuels(cls) -> List['FuelType']:
        """Get alternative fuel types."""
        return [cls.ELECTRIC, cls.HYBRID, cls.HYDROGEN, cls.CNG, cls.LPG, cls.ETHANOL]


@unique
class TransmissionType(str, Enum):
    """Transmission types."""
    MANUAL = 'manual'
    AUTOMATIC = 'automatic'
    CVT = 'cvt'
    SEMI_AUTOMATIC = 'semi_automatic'
    DUAL_CLUTCH = 'dual_clutch'


@unique
class DriveType(str, Enum):
    """Drive types."""
    FWD = 'fwd'
    RWD = 'rwd'
    AWD = 'awd'
    FOUR_WD = '4wd'
    FOUR_X_FOUR = '4x4'


@unique
class RegistrationStatus(str, Enum):
    """Vehicle registration status."""
    CURRENT = 'current'
    EXPIRED = 'expired'
    PENDING = 'pending'
    SUSPENDED = 'suspended'
    REVOKED = 'revoked'
    RENEWAL_DUE = 'renewal_due'

    @classmethod
    def get_valid_statuses(cls) -> List['RegistrationStatus']:
        """Get statuses considered valid."""
        return [cls.CURRENT, cls.RENEWAL_DUE]


@unique
class InsuranceStatus(str, Enum):
    """Vehicle insurance status."""
    ACTIVE = 'active'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'
    PENDING = 'pending'
    LAPSED = 'lapsed'

    @classmethod
    def get_valid_statuses(cls) -> List['InsuranceStatus']:
        """Get statuses considered valid."""
        return [cls.ACTIVE]


@unique
class InspectionStatus(str, Enum):
    """Vehicle inspection status."""
    PASSED = 'passed'
    FAILED = 'failed'
    PENDING = 'pending'
    SCHEDULED = 'scheduled'
    WAIVED = 'waived'

    @classmethod
    def get_valid_statuses(cls) -> List['InspectionStatus']:
        """Get statuses considered valid."""
        return [cls.PASSED, cls.WAIVED]


@unique
class OwnershipType(str, Enum):
    """Vehicle ownership types."""
    OWNER = 'owner'
    LESSEE = 'lessee'
    RENTER = 'renter'
    COMPANY = 'company'
    FLEET = 'fleet'
    GOVERNMENT = 'government'


# ============================================================================
# PARKING MANAGEMENT ENUMS
# ============================================================================

@unique
class SpotType(str, Enum):
    """Parking spot types."""
    STANDARD = 'standard'
    COMPACT = 'compact'
    HANDICAPPED = 'handicapped'
    ELECTRIC = 'electric'
    MOTORCYCLE = 'motorcycle'
    BUS = 'bus'
    TRUCK = 'truck'
    VIP = 'vip'
    STAFF = 'staff'
    VISITOR = 'visitor'
    RESERVED = 'reserved'
    VALET = 'valet'
    OVERSIZE = 'oversize'

    @classmethod
    def get_special_types(cls) -> List['SpotType']:
        """Get special spot types requiring additional features."""
        return [cls.HANDICAPPED, cls.ELECTRIC, cls.VIP, cls.STAFF]


@unique
class SpotStatus(str, Enum):
    """Parking spot status."""
    AVAILABLE = 'available'
    OCCUPIED = 'occupied'
    RESERVED = 'reserved'
    MAINTENANCE = 'maintenance'
    OUT_OF_SERVICE = 'out_of_service'
    BLOCKED = 'blocked'

    @classmethod
    def get_available_statuses(cls) -> List['SpotStatus']:
        """Get statuses where spot can be booked."""
        return [cls.AVAILABLE, cls.RESERVED]

    @classmethod
    def get_unavailable_statuses(cls) -> List['SpotStatus']:
        """Get statuses where spot cannot be used."""
        return [cls.OCCUPIED, cls.MAINTENANCE, cls.OUT_OF_SERVICE, cls.BLOCKED]


@unique
class ZoneType(str, Enum):
    """Parking zone types."""
    INDOOR = 'indoor'
    OUTDOOR = 'outdoor'
    COVERED = 'covered'
    ROOFTOP = 'rooftop'
    UNDERGROUND = 'underground'
    MULTI_LEVEL = 'multi_level'
    SURFACE = 'surface'
    STRUCTURE = 'structure'
    VALET = 'valet'
    RESERVED = 'reserved'


@unique
class ZoneStatus(str, Enum):
    """Parking zone status."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    MAINTENANCE = 'maintenance'
    FULL = 'full'
    CLOSED = 'closed'
    UNDER_CONSTRUCTION = 'under_construction'


@unique
class AccessType(str, Enum):
    """Access control types."""
    GATE = 'gate'
    BARRIER = 'barrier'
    RFID = 'rfid'
    LICENSE_PLATE = 'license_plate'
    TICKET = 'ticket'
    VALET = 'valet'
    RESERVATION = 'reservation'
    MEMBERSHIP = 'membership'


@unique
class GateType(str, Enum):
    """Gate types."""
    ENTRY = 'entry'
    EXIT = 'exit'
    BOTH = 'both'


# ============================================================================
# RESERVATION ENUMS
# ============================================================================

@unique
class ReservationStatus(str, Enum):
    """Reservation status."""
    DRAFT = 'draft'
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CHECKED_IN = 'checked_in'
    CHECKED_OUT = 'checked_out'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    NO_SHOW = 'no_show'
    EXPIRED = 'expired'
    MODIFIED = 'modified'
    REFUNDED = 'refunded'

    @classmethod
    def get_active_statuses(cls) -> List['ReservationStatus']:
        """Get statuses considered active."""
        return [cls.CONFIRMED, cls.CHECKED_IN]

    @classmethod
    def get_past_statuses(cls) -> List['ReservationStatus']:
        """Get statuses considered past/completed."""
        return [cls.COMPLETED, cls.CANCELLED, cls.NO_SHOW, cls.EXPIRED, cls.REFUNDED]

    @classmethod
    def get_cancellable_statuses(cls) -> List['ReservationStatus']:
        """Get statuses where reservation can be cancelled."""
        return [cls.PENDING, cls.CONFIRMED]


@unique
class ReservationType(str, Enum):
    """Reservation types."""
    STANDARD = 'standard'
    VIP = 'vip'
    EVENT = 'event'
    MONTHLY = 'monthly'
    CORPORATE = 'corporate'
    STAFF = 'staff'
    VALET = 'valet'


@unique
class PaymentStatus(str, Enum):
    """Payment status."""
    PENDING = 'pending'
    AUTHORIZED = 'authorized'
    PAID = 'paid'
    PARTIALLY_PAID = 'partially_paid'
    REFUNDED = 'refunded'
    PARTIALLY_REFUNDED = 'partially_refunded'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    DISPUTED = 'disputed'
    CHARGEBACK = 'chargeback'

    @classmethod
    def get_successful_statuses(cls) -> List['PaymentStatus']:
        """Get statuses considered successful."""
        return [cls.PAID, cls.AUTHORIZED]

    @classmethod
    def get_failed_statuses(cls) -> List['PaymentStatus']:
        """Get statuses considered failed."""
        return [cls.FAILED, cls.CANCELLED]


@unique
class RecurringFrequency(str, Enum):
    """Recurring reservation frequency."""
    DAILY = 'daily'
    WEEKLY = 'weekly'
    BI_WEEKLY = 'bi_weekly'
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    YEARLY = 'yearly'
    WEEKDAYS = 'weekdays'
    WEEKENDS = 'weekends'
    CUSTOM = 'custom'


@unique
class WaitlistStatus(str, Enum):
    """Waitlist status."""
    ACTIVE = 'active'
    NOTIFIED = 'notified'
    CONVERTED = 'converted'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'


# ============================================================================
# PAYMENT ENUMS
# ============================================================================

@unique
class PaymentMethodType(str, Enum):
    """Payment method types."""
    CREDIT_CARD = 'credit_card'
    DEBIT_CARD = 'debit_card'
    PAYPAL = 'paypal'
    APPLE_PAY = 'apple_pay'
    GOOGLE_PAY = 'google_pay'
    BANK_TRANSFER = 'bank_transfer'
    CASH = 'cash'
    CHECK = 'check'
    VOUCHER = 'voucher'
    GIFT_CARD = 'gift_card'
    CRYPTO = 'crypto'
    VENMO = 'venmo'
    ALIPAY = 'alipay'
    WECHAT_PAY = 'wechat_pay'
    KLARNA = 'klarna'
    AFTERPAY = 'afterpay'
    AFFIRM = 'affirm'
    SEPA = 'sepa'
    ACH = 'ach'
    WIRE_TRANSFER = 'wire_transfer'

    @classmethod
    def get_card_methods(cls) -> List['PaymentMethodType']:
        """Get card-based payment methods."""
        return [cls.CREDIT_CARD, cls.DEBIT_CARD]

    @classmethod
    def get_digital_wallets(cls) -> List['PaymentMethodType']:
        """Get digital wallet methods."""
        return [cls.PAYPAL, cls.APPLE_PAY, cls.GOOGLE_PAY, cls.VENMO]

    @classmethod
    def get_bank_methods(cls) -> List['PaymentMethodType']:
        """Get bank-based methods."""
        return [cls.BANK_TRANSFER, cls.SEPA, cls.ACH, cls.WIRE_TRANSFER]


@unique
class PaymentProvider(str, Enum):
    """Payment providers."""
    STRIPE = 'stripe'
    PAYPAL = 'paypal'
    BRAINTREE = 'braintree'
    SQUARE = 'square'
    AUTHORIZE_NET = 'authorize_net'
    ADYEN = 'adyen'
    WORLDPAY = 'worldpay'
    CHECKOUT_COM = 'checkout_com'
    RAZORPAY = 'razorpay'
    PAYU = 'payu'
    MOLLIE = 'mollie'
    TWOCHECKOUT = '2checkout'
    DWOLLA = 'dwolla'
    RECURLY = 'recurly'
    CHARGEBEE = 'chargebee'


@unique
class TransactionType(str, Enum):
    """Transaction types."""
    SALE = 'sale'
    AUTHORIZATION = 'authorization'
    CAPTURE = 'capture'
    VOID = 'void'
    REFUND = 'refund'
    CHARGEBACK = 'chargeback'
    SETTLEMENT = 'settlement'
    PAYOUT = 'payout'
    FEE = 'fee'
    ADJUSTMENT = 'adjustment'


@unique
class DisputeStatus(str, Enum):
    """Dispute status."""
    OPEN = 'open'
    UNDER_REVIEW = 'under_review'
    WON = 'won'
    LOST = 'lost'
    ACCEPTED = 'accepted'
    WAITING_FOR_BUYER_RESPONSE = 'waiting_for_buyer_response'
    WAITING_FOR_SELLER_RESPONSE = 'waiting_for_seller_response'
    APPEALED = 'appealed'
    CHARGEBACK_REVERSED = 'chargeback_reversed'


@unique
class DisputeReason(str, Enum):
    """Dispute reasons."""
    FRAUDULENT = 'fraudulent'
    DUPLICATE = 'duplicate'
    UNAUTHORIZED = 'unauthorized'
    PRODUCT_NOT_RECEIVED = 'product_not_received'
    PRODUCT_UNACCEPTABLE = 'product_unacceptable'
    CREDIT_NOT_PROCESSED = 'credit_not_processed'
    CANCELLED_RECURRING = 'cancelled_recurring'
    BANK_ERROR = 'bank_error'
    CUSTOMER_CLAIM = 'customer_claim'
    SERVICE_DISPUTE = 'service_dispute'


@unique
class SubscriptionStatus(str, Enum):
    """Subscription status."""
    ACTIVE = 'active'
    PAST_DUE = 'past_due'
    CANCELED = 'canceled'
    INCOMPLETE = 'incomplete'
    INCOMPLETE_EXPIRED = 'incomplete_expired'
    TRIALING = 'trialing'
    PAUSED = 'paused'
    UNPAID = 'unpaid'
    ENDED = 'ended'


@unique
class SubscriptionInterval(str, Enum):
    """Subscription intervals."""
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'


@unique
class InvoiceStatus(str, Enum):
    """Invoice status."""
    DRAFT = 'draft'
    OPEN = 'open'
    PAID = 'paid'
    VOID = 'void'
    UNCOLLECTIBLE = 'uncollectible'
    OVERDUE = 'overdue'
    PENDING = 'pending'
    PARTIALLY_PAID = 'partially_paid'


@unique
class DiscountType(str, Enum):
    """Discount types."""
    PERCENTAGE = 'percentage'
    FIXED_AMOUNT = 'fixed_amount'
    BUY_X_GET_Y = 'buy_x_get_y'
    FREE_SHIPPING = 'free_shipping'


@unique
class DiscountApplyTo(str, Enum):
    """Discount application scope."""
    ALL = 'all'
    FIRST_BOOKING = 'first_booking'
    RECURRING = 'recurring'
    SPECIFIC_SPOT = 'specific_spot'
    SPECIFIC_ZONE = 'specific_zone'


@unique
class FeeType(str, Enum):
    """Fee types."""
    PROCESSING = 'processing'
    CONVENIENCE = 'convenience'
    SERVICE = 'service'
    LATE = 'late'
    CANCELLATION = 'cancellation'
    FOREIGN_TRANSACTION = 'foreign_transaction'
    CROSS_BORDER = 'cross_border'
    CURRENCY_CONVERSION = 'currency_conversion'


@unique
class Currency(str, Enum):
    """Supported currencies (ISO 4217)."""
    USD = 'USD'
    EUR = 'EUR'
    GBP = 'GBP'
    CAD = 'CAD'
    AUD = 'AUD'
    JPY = 'JPY'
    CNY = 'CNY'
    INR = 'INR'
    MXN = 'MXN'
    BRL = 'BRL'
    CHF = 'CHF'
    HKD = 'HKD'
    SGD = 'SGD'
    NZD = 'NZD'
    KRW = 'KRW'
    SEK = 'SEK'
    NOK = 'NOK'
    DKK = 'DKK'
    PLN = 'PLN'
    RUB = 'RUB'
    ZAR = 'ZAR'
    TRY = 'TRY'
    AED = 'AED'
    SAR = 'SAR'

    @classmethod
    def get_major_currencies(cls) -> List['Currency']:
        """Get major world currencies."""
        return [cls.USD, cls.EUR, cls.GBP, cls.JPY, cls.CNY]

    @classmethod
    def get_by_region(cls, region: str) -> List['Currency']:
        """Get currencies by region."""
        region_map = {
            'north_america': [cls.USD, cls.CAD, cls.MXN],
            'europe': [cls.EUR, cls.GBP, cls.CHF, cls.SEK, cls.NOK, cls.DKK, cls.PLN],
            'asia': [cls.JPY, cls.CNY, cls.INR, cls.HKD, cls.SGD, cls.KRW],
            'oceania': [cls.AUD, cls.NZD],
            'middle_east': [cls.AED, cls.SAR, cls.TRY],
        }
        return region_map.get(region, [])


# ============================================================================
# NOTIFICATION ENUMS
# ============================================================================

@unique
class NotificationType(str, Enum):
    """Notification types."""
    # Reservation notifications
    RESERVATION_CONFIRMATION = 'reservation_confirmation'
    RESERVATION_REMINDER = 'reservation_reminder'
    RESERVATION_MODIFICATION = 'reservation_modification'
    RESERVATION_CANCELLATION = 'reservation_cancellation'
    
    # Check-in/out notifications
    CHECK_IN_SUCCESS = 'check_in_success'
    CHECK_OUT_SUCCESS = 'check_out_success'
    CHECK_IN_REMINDER = 'check_in_reminder'
    CHECK_OUT_REMINDER = 'check_out_reminder'
    
    # Payment notifications
    PAYMENT_RECEIPT = 'payment_receipt'
    PAYMENT_FAILED = 'payment_failed'
    PAYMENT_REFUNDED = 'payment_refunded'
    PAYMENT_DUE = 'payment_due'
    
    # Violation notifications
    VIOLATION_ISSUED = 'violation_issued'
    VIOLATION_PAID = 'violation_paid'
    VIOLATION_REMINDER = 'violation_reminder'
    
    # Vehicle notifications
    VEHICLE_ALERT = 'vehicle_alert'
    VEHICLE_BLACKLISTED = 'vehicle_blacklisted'
    VEHICLE_STOLEN = 'vehicle_stolen'
    
    # Subscription notifications
    SUBSCRIPTION_CREATED = 'subscription_created'
    SUBSCRIPTION_RENEWED = 'subscription_renewed'
    SUBSCRIPTION_EXPIRING = 'subscription_expiring'
    SUBSCRIPTION_CANCELLED = 'subscription_cancelled'
    
    # Account notifications
    ACCOUNT_CREATED = 'account_created'
    PASSWORD_RESET = 'password_reset'
    EMAIL_VERIFICATION = 'email_verification'
    PHONE_VERIFICATION = 'phone_verification'
    ACCOUNT_LOCKED = 'account_locked'
    
    # Security notifications
    SECURITY_ALERT = 'security_alert'
    LOGIN_NEW_DEVICE = 'login_new_device'
    LOGIN_FAILED = 'login_failed'
    
    # Marketing notifications
    PROMOTIONAL = 'promotional'
    NEWSLETTER = 'newsletter'
    SURVEY = 'survey'
    
    # System notifications
    SYSTEM_ALERT = 'system_alert'
    MAINTENANCE_ALERT = 'maintenance_alert'
    POLICY_UPDATE = 'policy_update'
    
    # Waitlist notifications
    WAITLIST_CONFIRMED = 'waitlist_confirmed'
    SPOT_AVAILABLE = 'spot_available'

    @classmethod
    def get_transactional_types(cls) -> List['NotificationType']:
        """Get transactional notification types."""
        return [
            cls.RESERVATION_CONFIRMATION,
            cls.RESERVATION_MODIFICATION,
            cls.RESERVATION_CANCELLATION,
            cls.CHECK_IN_SUCCESS,
            cls.CHECK_OUT_SUCCESS,
            cls.PAYMENT_RECEIPT,
            cls.PAYMENT_FAILED,
            cls.PAYMENT_REFUNDED,
        ]

    @classmethod
    def get_marketing_types(cls) -> List['NotificationType']:
        """Get marketing notification types."""
        return [cls.PROMOTIONAL, cls.NEWSLETTER, cls.SURVEY]


@unique
class NotificationChannel(str, Enum):
    """Notification channels."""
    EMAIL = 'email'
    SMS = 'sms'
    PUSH = 'push'
    WHATSAPP = 'whatsapp'
    TELEGRAM = 'telegram'
    SLACK = 'slack'
    WEBHOOK = 'webhook'
    IN_APP = 'in_app'
    VOICE = 'voice'
    FAX = 'fax'

    @classmethod
    def get_digital_channels(cls) -> List['NotificationChannel']:
        """Get digital notification channels."""
        return [cls.EMAIL, cls.SMS, cls.PUSH, cls.WHATSAPP, cls.IN_APP]

    @classmethod
    def get_immediate_channels(cls) -> List['NotificationChannel']:
        """Get channels suitable for immediate notifications."""
        return [cls.SMS, cls.PUSH, cls.VOICE]


@unique
class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = 'pending'
    QUEUED = 'queued'
    PROCESSING = 'processing'
    SENT = 'sent'
    DELIVERED = 'delivered'
    FAILED = 'failed'
    BOUNCED = 'bounced'
    OPENED = 'opened'
    CLICKED = 'clicked'
    UNSUBSCRIBED = 'unsubscribed'
    SUPPRESSED = 'suppressed'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'

    @classmethod
    def get_final_statuses(cls) -> List['NotificationStatus']:
        """Get final (non-retryable) statuses."""
        return [cls.DELIVERED, cls.FAILED, cls.BOUNCED, cls.UNSUBSCRIBED, 
                cls.SUPPRESSED, cls.EXPIRED, cls.CANCELLED]

    @classmethod
    def get_success_statuses(cls) -> List['NotificationStatus']:
        """Get successful delivery statuses."""
        return [cls.DELIVERED, cls.OPENED, cls.CLICKED]


@unique
class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    URGENT = 'urgent'
    CRITICAL = 'critical'


@unique
class TemplateType(str, Enum):
    """Template types."""
    EMAIL_HTML = 'email_html'
    EMAIL_TEXT = 'email_text'
    SMS_TEXT = 'sms_text'
    PUSH_NOTIFICATION = 'push_notification'
    WHATSAPP_TEXT = 'whatsapp_text'
    IN_APP = 'in_app'


@unique
class DeviceType(str, Enum):
    """Device types for push notifications."""
    IOS = 'ios'
    ANDROID = 'android'
    WEB = 'web'
    DESKTOP = 'desktop'
    TABLET = 'tablet'


@unique
class CampaignStatus(str, Enum):
    """Campaign status."""
    DRAFT = 'draft'
    SCHEDULED = 'scheduled'
    SENDING = 'sending'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    ARCHIVED = 'archived'


@unique
class WebhookMethod(str, Enum):
    """Webhook HTTP methods."""
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'


@unique
class Frequency(str, Enum):
    """Notification frequency."""
    IMMEDIATE = 'immediate'
    DAILY_DIGEST = 'daily_digest'
    WEEKLY_DIGEST = 'weekly_digest'
    MONTHLY_DIGEST = 'monthly_digest'
    NEVER = 'never'


@unique
class SuppressionReason(str, Enum):
    """Suppression reasons."""
    UNSUBSCRIBED = 'unsubscribed'
    BOUNCED = 'bounced'
    COMPLAINED = 'complained'
    INVALID = 'invalid'
    OPTED_OUT = 'opted_out'
    USER_DELETED = 'user_deleted'


# ============================================================================
# AUDIT ENUMS
# ============================================================================

@unique
class AuditAction(str, Enum):
    """Audit actions."""
    # CRUD operations
    CREATE = 'CREATE'
    READ = 'READ'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    
    # Authentication
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'
    LOGIN_FAILED = 'LOGIN_FAILED'
    LOGIN_LOCKED = 'LOGIN_LOCKED'
    PASSWORD_CHANGE = 'PASSWORD_CHANGE'
    PASSWORD_RESET = 'PASSWORD_RESET'
    
    # Authorization
    PERMISSION_GRANTED = 'PERMISSION_GRANTED'
    PERMISSION_REVOKED = 'PERMISSION_REVOKED'
    ROLE_ASSIGNED = 'ROLE_ASSIGNED'
    ROLE_REMOVED = 'ROLE_REMOVED'
    ACCESS_DENIED = 'ACCESS_DENIED'
    
    # Data operations
    EXPORT = 'EXPORT'
    IMPORT = 'IMPORT'
    DOWNLOAD = 'DOWNLOAD'
    UPLOAD = 'UPLOAD'
    PRINT = 'PRINT'
    SHARE = 'SHARE'
    ARCHIVE = 'ARCHIVE'
    RESTORE = 'RESTORE'
    PURGE = 'PURGE'
    
    # Business operations
    APPROVE = 'APPROVE'
    REJECT = 'REJECT'
    SUBMIT = 'SUBMIT'
    CANCEL = 'CANCEL'
    VOID = 'VOID'
    REFUND = 'REFUND'
    PAYMENT = 'PAYMENT'
    
    # Verification
    VERIFY = 'VERIFY'
    VALIDATE = 'VALIDATE'
    AUDIT = 'AUDIT'
    REVIEW = 'REVIEW'
    ESCALATE = 'ESCALATE'
    DELEGATE = 'DELEGATE'
    ASSIGN = 'ASSIGN'
    UNASSIGN = 'UNASSIGN'
    
    # Security
    LOCK = 'LOCK'
    UNLOCK = 'UNLOCK'
    ENABLE = 'ENABLE'
    DISABLE = 'DISABLE'
    ACTIVATE = 'ACTIVATE'
    DEACTIVATE = 'DEACTIVATE'
    SUSPEND = 'SUSPEND'
    REINSTATE = 'REINSTATE'
    RESET = 'RESET'
    
    # Configuration
    CHANGE_SETTINGS = 'CHANGE_SETTINGS'
    CONFIGURE = 'CONFIGURE'
    INSTALL = 'INSTALL'
    UNINSTALL = 'UNINSTALL'
    UPDATE = 'UPDATE'
    UPGRADE = 'UPGRADE'


@unique
class AuditStatus(str, Enum):
    """Audit status."""
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'
    TIMEOUT = 'TIMEOUT'
    CANCELLED = 'CANCELLED'
    BLOCKED = 'BLOCKED'
    DENIED = 'DENIED'
    UNAUTHORIZED = 'UNAUTHORIZED'
    RATE_LIMITED = 'RATE_LIMITED'
    VALID = 'VALID'
    INVALID = 'INVALID'
    EXPIRED = 'EXPIRED'


@unique
class AuditSeverity(str, Enum):
    """Audit severity levels."""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    NOTICE = 'NOTICE'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'
    ALERT = 'ALERT'
    EMERGENCY = 'EMERGENCY'


@unique
class AuditCategory(str, Enum):
    """Audit categories."""
    AUTHENTICATION = 'AUTHENTICATION'
    AUTHORIZATION = 'AUTHORIZATION'
    DATA_ACCESS = 'DATA_ACCESS'
    DATA_MODIFICATION = 'DATA_MODIFICATION'
    CONFIGURATION = 'CONFIGURATION'
    SYSTEM = 'SYSTEM'
    SECURITY = 'SECURITY'
    COMPLIANCE = 'COMPLIANCE'
    FINANCIAL = 'FINANCIAL'
    USER_ACTIVITY = 'USER_ACTIVITY'
    ADMIN_ACTIVITY = 'ADMIN_ACTIVITY'
    API_ACTIVITY = 'API_ACTIVITY'
    INTEGRATION = 'INTEGRATION'
    WORKFLOW = 'WORKFLOW'
    REPORTING = 'REPORTING'


@unique
class AuditResourceType(str, Enum):
    """Audit resource types."""
    USER = 'USER'
    VEHICLE = 'VEHICLE'
    RESERVATION = 'RESERVATION'
    PARKING_SPOT = 'PARKING_SPOT'
    PARKING_ZONE = 'PARKING_ZONE'
    PAYMENT = 'PAYMENT'
    INVOICE = 'INVOICE'
    SUBSCRIPTION = 'SUBSCRIPTION'
    NOTIFICATION = 'NOTIFICATION'
    TEMPLATE = 'TEMPLATE'
    CAMPAIGN = 'CAMPAIGN'
    DEVICE = 'DEVICE'
    SENSOR = 'SENSOR'
    VIOLATION = 'VIOLATION'
    DISPUTE = 'DISPUTE'
    REFUND = 'REFUND'
    DISCOUNT = 'DISCOUNT'
    RATE = 'RATE'
    SETTINGS = 'SETTINGS'
    PERMISSION = 'PERMISSION'
    ROLE = 'ROLE'
    API_KEY = 'API_KEY'
    WEBHOOK = 'WEBHOOK'
    REPORT = 'REPORT'
    AUDIT_LOG = 'AUDIT_LOG'


@unique
class ComplianceStandard(str, Enum):
    """Compliance standards."""
    GDPR = 'GDPR'
    CCPA = 'CCPA'
    PCI_DSS = 'PCI_DSS'
    HIPAA = 'HIPAA'
    SOX = 'SOX'
    ISO_27001 = 'ISO_27001'
    NIST = 'NIST'
    FISMA = 'FISMA'
    FERPA = 'FERPA'
    COPPA = 'COPPA'


@unique
class RetentionAction(str, Enum):
    """Data retention actions."""
    ARCHIVE = 'ARCHIVE'
    DELETE = 'DELETE'
    ANONYMIZE = 'ANONYMIZE'
    PSEUDONYMIZE = 'PSEUDONYMIZE'
    EXPORT = 'EXPORT'


# ============================================================================
# RATE ENUMS
# ============================================================================

@unique
class RateType(str, Enum):
    """Rate types."""
    HOURLY = 'hourly'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    YEARLY = 'yearly'
    EVENT = 'event'
    SPECIAL = 'special'
    PROMOTIONAL = 'promotional'
    MEMBERSHIP = 'membership'
    CORPORATE = 'corporate'
    VALET = 'valet'
    OVERNIGHT = 'overnight'
    WEEKEND = 'weekend'
    HOLIDAY = 'holiday'
    EARLY_BIRD = 'early_bird'
    NIGHT_OWL = 'night_owl'
    SEASONAL = 'seasonal'


@unique
class RateUnit(str, Enum):
    """Rate units."""
    HOUR = 'hour'
    HALF_HOUR = 'half_hour'
    MINUTE = 'minute'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'
    FIXED = 'fixed'


@unique
class RateCategory(str, Enum):
    """Rate categories."""
    STANDARD = 'standard'
    PREMIUM = 'premium'
    ECONOMY = 'economy'
    VIP = 'vip'
    HANDICAP = 'handicap'
    EV = 'ev'
    MOTORCYCLE = 'motorcycle'
    OVERSIZE = 'oversize'
    COMMERCIAL = 'commercial'


@unique
class DynamicPricingModel(str, Enum):
    """Dynamic pricing models."""
    FIXED = 'fixed'
    DEMAND_BASED = 'demand_based'
    TIME_BASED = 'time_based'
    OCCUPANCY_BASED = 'occupancy_based'
    EVENT_BASED = 'event_based'
    COMPETITOR_BASED = 'competitor_based'
    WEATHER_BASED = 'weather_based'
    SEASONAL = 'seasonal'
    HYBRID = 'hybrid'


# ============================================================================
# SENSOR ENUMS
# ============================================================================

@unique
class SensorType(str, Enum):
    """Sensor types."""
    ULTRASONIC = 'ultrasonic'
    INFRARED = 'infrared'
    MAGNETIC = 'magnetic'
    INDUCTIVE_LOOP = 'inductive_loop'
    RADAR = 'radar'
    LIDAR = 'lidar'
    CAMERA = 'camera'
    THERMAL = 'thermal'
    PRESSURE = 'pressure'
    PROXIMITY = 'proximity'
    LASER = 'laser'
    MICROWAVE = 'microwave'
    ACOUSTIC = 'acoustic'
    SEISMIC = 'seismic'
    ENVIRONMENTAL = 'environmental'


@unique
class SensorStatus(str, Enum):
    """Sensor status."""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    INSTALLING = 'installing'
    CALIBRATING = 'calibrating'
    MAINTENANCE = 'maintenance'
    FAULTY = 'faulty'
    OFFLINE = 'offline'
    RETIRED = 'retired'
    BATTERY_LOW = 'battery_low'
    COMMUNICATION_ERROR = 'communication_error'


@unique
class CommunicationProtocol(str, Enum):
    """Communication protocols."""
    MQTT = 'mqtt'
    HTTP = 'http'
    HTTPS = 'https'
    COAP = 'coap'
    LORAWAN = 'lorawan'
    ZIGBEE = 'zigbee'
    Z_WAVE = 'z_wave'
    BLUETOOTH = 'bluetooth'
    BLE = 'ble'
    WIFI = 'wifi'
    ETHERNET = 'ethernet'
    RS485 = 'rs485'
    RS232 = 'rs232'
    CAN_BUS = 'can_bus'
    MODBUS = 'modbus'
    PROFIBUS = 'profibus'
    PROFINET = 'profinet'


@unique
class PowerSource(str, Enum):
    """Power sources."""
    BATTERY = 'battery'
    SOLAR = 'solar'
    MAINS = 'mains'
    POE = 'poe'
    USB = 'usb'
    WIRELESS_CHARGING = 'wireless_charging'
    ENERGY_HARVESTING = 'energy_harvesting'


@unique
class MeasurementUnit(str, Enum):
    """Measurement units."""
    # Distance
    CENTIMETERS = 'cm'
    METERS = 'm'
    MILLIMETERS = 'mm'
    INCHES = 'in'
    FEET = 'ft'
    
    # Weight
    KILOGRAMS = 'kg'
    POUNDS = 'lb'
    GRAMS = 'g'
    
    # Temperature
    CELSIUS = 'c'
    FAHRENHEIT = 'f'
    KELVIN = 'k'
    
    # Electrical
    VOLTS = 'v'
    AMPS = 'a'
    WATTS = 'w'
    KWH = 'kwh'
    
    # Other
    PERCENT = '%'
    LUX = 'lux'
    DECIBEL = 'db'
    HERTZ = 'hz'
    PASCAL = 'pa'
    BAR = 'bar'
    PSI = 'psi'
    RPM = 'rpm'
    DEGREES = 'deg'


@unique
class DataQuality(str, Enum):
    """Data quality levels."""
    EXCELLENT = 'excellent'
    GOOD = 'good'
    FAIR = 'fair'
    POOR = 'poor'
    UNRELIABLE = 'unreliable'
    INVALID = 'invalid'


@unique
class CalibrationStatus(str, Enum):
    """Calibration status."""
    CALIBRATED = 'calibrated'
    NEEDS_CALIBRATION = 'needs_calibration'
    CALIBRATING = 'calibrating'
    CALIBRATION_FAILED = 'calibration_failed'
    FACTORY_CALIBRATED = 'factory_calibrated'
    FIELD_CALIBRATED = 'field_calibrated'


# ============================================================================
# GENERAL ENUMS
# ============================================================================

@unique
class DayOfWeek(str, Enum):
    """Days of week."""
    MONDAY = 'monday'
    TUESDAY = 'tuesday'
    WEDNESDAY = 'wednesday'
    THURSDAY = 'thursday'
    FRIDAY = 'friday'
    SATURDAY = 'saturday'
    SUNDAY = 'sunday'

    @classmethod
    def get_weekdays(cls) -> List['DayOfWeek']:
        """Get weekday values."""
        return [cls.MONDAY, cls.TUESDAY, cls.WEDNESDAY, cls.THURSDAY, cls.FRIDAY]

    @classmethod
    def get_weekend(cls) -> List['DayOfWeek']:
        """Get weekend values."""
        return [cls.SATURDAY, cls.SUNDAY]

    def is_weekday(self) -> bool:
        """Check if day is a weekday."""
        return self in self.get_weekdays()

    def is_weekend(self) -> bool:
        """Check if day is a weekend."""
        return self in self.get_weekend()


@unique
class Month(str, Enum):
    """Months of year."""
    JANUARY = 'january'
    FEBRUARY = 'february'
    MARCH = 'march'
    APRIL = 'april'
    MAY = 'may'
    JUNE = 'june'
    JULY = 'july'
    AUGUST = 'august'
    SEPTEMBER = 'september'
    OCTOBER = 'october'
    NOVEMBER = 'november'
    DECEMBER = 'december'


@unique
class Quarter(str, Enum):
    """Quarters of year."""
    Q1 = 'q1'
    Q2 = 'q2'
    Q3 = 'q3'
    Q4 = 'q4'


@unique
class Season(str, Enum):
    """Seasons."""
    SPRING = 'spring'
    SUMMER = 'summer'
    FALL = 'fall'
    WINTER = 'winter'


@unique
class Language(str, Enum):
    """Supported languages (ISO 639-1)."""
    EN = 'en'
    ES = 'es'
    FR = 'fr'
    DE = 'de'
    IT = 'it'
    PT = 'pt'
    RU = 'ru'
    ZH = 'zh'
    JA = 'ja'
    KO = 'ko'
    AR = 'ar'
    HI = 'hi'


@unique
class CountryCode(str, Enum):
    """Country codes (ISO 3166-1 alpha-2)."""
    US = 'US'
    CA = 'CA'
    MX = 'MX'
    GB = 'GB'
    FR = 'FR'
    DE = 'DE'
    IT = 'IT'
    ES = 'ES'
    PT = 'PT'
    NL = 'NL'
    BE = 'BE'
    CH = 'CH'
    AT = 'AT'
    SE = 'SE'
    NO = 'NO'
    DK = 'DK'
    FI = 'FI'
    PL = 'PL'
    CZ = 'CZ'
    HU = 'HU'
    JP = 'JP'
    CN = 'CN'
    KR = 'KR'
    IN = 'IN'
    AU = 'AU'
    NZ = 'NZ'
    BR = 'BR'
    AR = 'AR'
    ZA = 'ZA'


@unique
class Timezone(str, Enum):
    """Common timezones."""
    UTC = 'UTC'
    EST = 'America/New_York'
    CST = 'America/Chicago'
    MST = 'America/Denver'
    PST = 'America/Los_Angeles'
    AKST = 'America/Anchorage'
    HST = 'America/Honolulu'
    LONDON = 'Europe/London'
    PARIS = 'Europe/Paris'
    BERLIN = 'Europe/Berlin'
    MOSCOW = 'Europe/Moscow'
    DUBAI = 'Asia/Dubai'
    SINGAPORE = 'Asia/Singapore'
    TOKYO = 'Asia/Tokyo'
    SYDNEY = 'Australia/Sydney'
    AUCKLAND = 'Pacific/Auckland'


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_enum_values(enum_class) -> List[str]:
    """Get all values from an enum class."""
    return [item.value for item in enum_class]


def get_enum_names(enum_class) -> List[str]:
    """Get all names from an enum class."""
    return [item.name for item in enum_class]


def get_enum_mapping(enum_class) -> Dict[str, str]:
    """Get mapping of enum names to values."""
    return {item.name: item.value for item in enum_class}


def get_enum_by_value(enum_class, value: str):
    """Get enum member by value."""
    for item in enum_class:
        if item.value == value:
            return item
    return None


def get_enum_by_name(enum_class, name: str):
    """Get enum member by name."""
    try:
        return enum_class[name]
    except KeyError:
        return None


def validate_enum_value(enum_class, value: str) -> bool:
    """Validate if a value exists in enum."""
    return value in get_enum_values(enum_class)


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # User Management
    'UserStatus',
    'UserRole',
    'AuthMethod',
    'MFAMethod',
    
    # Vehicle Management
    'VehicleStatus',
    'VehicleType',
    'VehicleClass',
    'FuelType',
    'TransmissionType',
    'DriveType',
    'RegistrationStatus',
    'InsuranceStatus',
    'InspectionStatus',
    'OwnershipType',
    
    # Parking Management
    'SpotType',
    'SpotStatus',
    'ZoneType',
    'ZoneStatus',
    'AccessType',
    'GateType',
    
    # Reservation Management
    'ReservationStatus',
    'ReservationType',
    'PaymentStatus',
    'RecurringFrequency',
    'WaitlistStatus',
    
    # Payment Management
    'PaymentMethodType',
    'PaymentProvider',
    'TransactionType',
    'DisputeStatus',
    'DisputeReason',
    'SubscriptionStatus',
    'SubscriptionInterval',
    'InvoiceStatus',
    'DiscountType',
    'DiscountApplyTo',
    'FeeType',
    'Currency',
    
    # Notification Management
    'NotificationType',
    'NotificationChannel',
    'NotificationStatus',
    'NotificationPriority',
    'TemplateType',
    'DeviceType',
    'CampaignStatus',
    'WebhookMethod',
    'Frequency',
    'SuppressionReason',
    
    # Audit Management
    'AuditAction',
    'AuditStatus',
    'AuditSeverity',
    'AuditCategory',
    'AuditResourceType',
    'ComplianceStandard',
    'RetentionAction',
    
    # Rate Management
    'RateType',
    'RateUnit',
    'RateCategory',
    'DynamicPricingModel',
    
    # Sensor Management
    'SensorType',
    'SensorStatus',
    'CommunicationProtocol',
    'PowerSource',
    'MeasurementUnit',
    'DataQuality',
    'CalibrationStatus',
    
    # General
    'DayOfWeek',
    'Month',
    'Quarter',
    'Season',
    'Language',
    'CountryCode',
    'Timezone',
    
    # Utility Functions
    'get_enum_values',
    'get_enum_names',
    'get_enum_mapping',
    'get_enum_by_value',
    'get_enum_by_name',
    'validate_enum_value',
]