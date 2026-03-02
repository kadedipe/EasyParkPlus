"""Custom exceptions for the parking management system.

This module defines all custom exceptions used throughout the application,
including base exception classes, domain-specific exceptions, and error
handling utilities.
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import json
import traceback
from http import HTTPStatus


# ============================================================================
# Base Exception Classes
# ============================================================================

class ParkingException(Exception):
    """Base exception for all parking system exceptions."""
    
    def __init__(
        self,
        message: str,
        code: str = "PARKING_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            'error': {
                'code': self.code,
                'message': self.message,
                'details': self.details,
                'timestamp': self.timestamp.isoformat(),
                'status_code': self.status_code
            }
        }
    
    def to_json(self) -> str:
        """Convert exception to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class BusinessError(ParkingException):
    """Base exception for business logic errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "BUSINESS_ERROR",
        status_code: int = 400,
        **kwargs
    ):
        super().__init__(message, code, status_code, **kwargs)


class SystemError(ParkingException):
    """Base exception for system-level errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "SYSTEM_ERROR",
        status_code: int = 500,
        **kwargs
    ):
        super().__init__(message, code, status_code, **kwargs)


class ConfigurationError(SystemError):
    """Exception raised for configuration errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if config_key:
            details['config_key'] = config_key
        super().__init__(
            message,
            code="CONFIGURATION_ERROR",
            details=details,
            **kwargs
        )


# ============================================================================
# Domain-Specific Exceptions
# ============================================================================

# ----------------------------------------------------------------------------
# Reservation Exceptions
# ----------------------------------------------------------------------------

class ReservationError(BusinessError):
    """Base exception for reservation-related errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "RESERVATION_ERROR",
        reservation_id: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if reservation_id:
            details['reservation_id'] = reservation_id
        super().__init__(message, code, details=details, **kwargs)


class ReservationNotFoundError(ReservationError):
    """Exception raised when a reservation is not found."""
    
    def __init__(
        self,
        reservation_id: Union[int, str],
        **kwargs
    ):
        super().__init__(
            f"Reservation not found: {reservation_id}",
            code="RESERVATION_NOT_FOUND",
            status_code=404,
            reservation_id=reservation_id,
            **kwargs
        )


class ReservationConflictError(ReservationError):
    """Exception raised when there's a scheduling conflict."""
    
    def __init__(
        self,
        spot_id: int,
        start_time: datetime,
        end_time: datetime,
        conflicting_reservation_id: Optional[int] = None,
        **kwargs
    ):
        details = {
            'spot_id': spot_id,
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'conflicting_reservation_id': conflicting_reservation_id
        }
        super().__init__(
            f"Reservation conflict for spot {spot_id}",
            code="RESERVATION_CONFLICT",
            status_code=409,
            details=details,
            **kwargs
        )


class ReservationCancellationError(ReservationError):
    """Exception raised when a reservation cannot be cancelled."""
    
    def __init__(
        self,
        reservation_id: int,
        reason: str,
        **kwargs
    ):
        super().__init__(
            f"Cannot cancel reservation {reservation_id}: {reason}",
            code="RESERVATION_CANCELLATION_ERROR",
            status_code=400,
            reservation_id=reservation_id,
            details={'reason': reason},
            **kwargs
        )


class ReservationCheckInError(ReservationError):
    """Exception raised when check-in fails."""
    
    def __init__(
        self,
        reservation_id: int,
        reason: str,
        **kwargs
    ):
        super().__init__(
            f"Check-in failed for reservation {reservation_id}: {reason}",
            code="RESERVATION_CHECKIN_ERROR",
            status_code=400,
            reservation_id=reservation_id,
            details={'reason': reason},
            **kwargs
        )


class ReservationCheckOutError(ReservationError):
    """Exception raised when check-out fails."""
    
    def __init__(
        self,
        reservation_id: int,
        reason: str,
        **kwargs
    ):
        super().__init__(
            f"Check-out failed for reservation {reservation_id}: {reason}",
            code="RESERVATION_CHECKOUT_ERROR",
            status_code=400,
            reservation_id=reservation_id,
            details={'reason': reason},
            **kwargs
        )


class ReservationExpiredError(ReservationError):
    """Exception raised when a reservation has expired."""
    
    def __init__(
        self,
        reservation_id: int,
        expiry_time: datetime,
        **kwargs
    ):
        super().__init__(
            f"Reservation {reservation_id} expired at {expiry_time}",
            code="RESERVATION_EXPIRED",
            status_code=410,
            reservation_id=reservation_id,
            details={'expiry_time': expiry_time.isoformat()},
            **kwargs
        )


class ReservationModificationError(ReservationError):
    """Exception raised when a reservation cannot be modified."""
    
    def __init__(
        self,
        reservation_id: int,
        reason: str,
        **kwargs
    ):
        super().__init__(
            f"Cannot modify reservation {reservation_id}: {reason}",
            code="RESERVATION_MODIFICATION_ERROR",
            status_code=400,
            reservation_id=reservation_id,
            details={'reason': reason},
            **kwargs
        )


class InvalidReservationTimeError(ReservationError):
    """Exception raised for invalid reservation times."""
    
    def __init__(
        self,
        start_time: datetime,
        end_time: datetime,
        reason: str,
        **kwargs
    ):
        details = {
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'reason': reason
        }
        super().__init__(
            f"Invalid reservation time: {reason}",
            code="INVALID_RESERVATION_TIME",
            status_code=400,
            details=details,
            **kwargs
        )


class ReservationLimitExceededError(ReservationError):
    """Exception raised when user exceeds reservation limits."""
    
    def __init__(
        self,
        user_id: int,
        limit: int,
        period: str,
        **kwargs
    ):
        details = {
            'user_id': user_id,
            'limit': limit,
            'period': period
        }
        super().__init__(
            f"User {user_id} exceeded reservation limit of {limit} per {period}",
            code="RESERVATION_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
            **kwargs
        )


# ----------------------------------------------------------------------------
# Parking Spot Exceptions
# ----------------------------------------------------------------------------

class ParkingSpotError(BusinessError):
    """Base exception for parking spot-related errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "PARKING_SPOT_ERROR",
        spot_id: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if spot_id:
            details['spot_id'] = spot_id
        super().__init__(message, code, details=details, **kwargs)


class ParkingSpotNotFoundError(ParkingSpotError):
    """Exception raised when a parking spot is not found."""
    
    def __init__(
        self,
        spot_id: Union[int, str],
        **kwargs
    ):
        super().__init__(
            f"Parking spot not found: {spot_id}",
            code="PARKING_SPOT_NOT_FOUND",
            status_code=404,
            spot_id=spot_id,
            **kwargs
        )


class ParkingSpotUnavailableError(ParkingSpotError):
    """Exception raised when a parking spot is unavailable."""
    
    def __init__(
        self,
        spot_id: int,
        reason: str = "Spot is currently unavailable",
        **kwargs
    ):
        super().__init__(
            f"Parking spot {spot_id} is unavailable: {reason}",
            code="PARKING_SPOT_UNAVAILABLE",
            status_code=409,
            spot_id=spot_id,
            details={'reason': reason},
            **kwargs
        )


class ParkingSpotMaintenanceError(ParkingSpotError):
    """Exception raised when a spot is under maintenance."""
    
    def __init__(
        self,
        spot_id: int,
        maintenance_end: Optional[datetime] = None,
        **kwargs
    ):
        details = {'maintenance': True}
        if maintenance_end:
            details['maintenance_end'] = maintenance_end.isoformat()
        
        super().__init__(
            f"Parking spot {spot_id} is under maintenance",
            code="PARKING_SPOT_MAINTENANCE",
            status_code=503,
            spot_id=spot_id,
            details=details,
            **kwargs
        )


class InvalidSpotTypeError(ParkingSpotError):
    """Exception raised for invalid spot type."""
    
    def __init__(
        self,
        spot_type: str,
        allowed_types: List[str],
        **kwargs
    ):
        details = {
            'spot_type': spot_type,
            'allowed_types': allowed_types
        }
        super().__init__(
            f"Invalid spot type: {spot_type}. Allowed: {', '.join(allowed_types)}",
            code="INVALID_SPOT_TYPE",
            status_code=400,
            details=details,
            **kwargs
        )


# ----------------------------------------------------------------------------
# User Exceptions
# ----------------------------------------------------------------------------

class UserError(BusinessError):
    """Base exception for user-related errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "USER_ERROR",
        user_id: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if user_id:
            details['user_id'] = user_id
        super().__init__(message, code, details=details, **kwargs)


class UserNotFoundError(UserError):
    """Exception raised when a user is not found."""
    
    def __init__(
        self,
        user_id: Optional[Union[int, str]] = None,
        email: Optional[str] = None,
        **kwargs
    ):
        identifier = user_id or email or "unknown"
        details = {}
        if user_id:
            details['user_id'] = user_id
        if email:
            details['email'] = email
            
        super().__init__(
            f"User not found: {identifier}",
            code="USER_NOT_FOUND",
            status_code=404,
            details=details,
            **kwargs
        )


class UserAuthenticationError(UserError):
    """Exception raised for authentication failures."""
    
    def __init__(
        self,
        reason: str = "Authentication failed",
        **kwargs
    ):
        super().__init__(
            reason,
            code="AUTHENTICATION_ERROR",
            status_code=401,
            **kwargs
        )


class UserAuthorizationError(UserError):
    """Exception raised for authorization failures."""
    
    def __init__(
        self,
        user_id: int,
        required_permission: Optional[str] = None,
        **kwargs
    ):
        details = {'user_id': user_id}
        if required_permission:
            details['required_permission'] = required_permission
            
        super().__init__(
            f"User {user_id} is not authorized",
            code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details,
            **kwargs
        )


class UserAccountLockedError(UserError):
    """Exception raised when user account is locked."""
    
    def __init__(
        self,
        user_id: int,
        lock_reason: str = "Account locked due to multiple failed attempts",
        unlock_time: Optional[datetime] = None,
        **kwargs
    ):
        details = {
            'user_id': user_id,
            'lock_reason': lock_reason
        }
        if unlock_time:
            details['unlock_time'] = unlock_time.isoformat()
            
        super().__init__(
            f"User account {user_id} is locked",
            code="ACCOUNT_LOCKED",
            status_code=403,
            details=details,
            **kwargs
        )


class UserAccountDisabledError(UserError):
    """Exception raised when user account is disabled."""
    
    def __init__(
        self,
        user_id: int,
        **kwargs
    ):
        super().__init__(
            f"User account {user_id} is disabled",
            code="ACCOUNT_DISABLED",
            status_code=403,
            user_id=user_id,
            **kwargs
        )


class UserEmailAlreadyExistsError(UserError):
    """Exception raised when email already exists."""
    
    def __init__(
        self,
        email: str,
        **kwargs
    ):
        super().__init__(
            f"Email already exists: {email}",
            code="EMAIL_ALREADY_EXISTS",
            status_code=409,
            details={'email': email},
            **kwargs
        )


class UserPhoneAlreadyExistsError(UserError):
    """Exception raised when phone number already exists."""
    
    def __init__(
        self,
        phone: str,
        **kwargs
    ):
        super().__init__(
            f"Phone number already exists: {phone}",
            code="PHONE_ALREADY_EXISTS",
            status_code=409,
            details={'phone': phone},
            **kwargs
        )


class UserVerificationError(UserError):
    """Exception raised for verification failures."""
    
    def __init__(
        self,
        user_id: int,
        verification_type: str,
        reason: str,
        **kwargs
    ):
        details = {
            'user_id': user_id,
            'verification_type': verification_type,
            'reason': reason
        }
        super().__init__(
            f"Verification failed for user {user_id}: {reason}",
            code="VERIFICATION_ERROR",
            status_code=400,
            details=details,
            **kwargs
        )


# ----------------------------------------------------------------------------
# Payment Exceptions
# ----------------------------------------------------------------------------

class PaymentError(BusinessError):
    """Base exception for payment-related errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "PAYMENT_ERROR",
        payment_id: Optional[int] = None,
        reservation_id: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if payment_id:
            details['payment_id'] = payment_id
        if reservation_id:
            details['reservation_id'] = reservation_id
        super().__init__(message, code, details=details, **kwargs)


class PaymentFailedError(PaymentError):
    """Exception raised when payment processing fails."""
    
    def __init__(
        self,
        amount: float,
        reason: str,
        payment_method: Optional[str] = None,
        **kwargs
    ):
        details = {
            'amount': amount,
            'reason': reason
        }
        if payment_method:
            details['payment_method'] = payment_method
            
        super().__init__(
            f"Payment failed: {reason}",
            code="PAYMENT_FAILED",
            status_code=402,
            details=details,
            **kwargs
        )


class PaymentDeclinedError(PaymentError):
    """Exception raised when payment is declined."""
    
    def __init__(
        self,
        amount: float,
        decline_reason: str,
        **kwargs
    ):
        super().__init__(
            f"Payment declined: {decline_reason}",
            code="PAYMENT_DECLINED",
            status_code=402,
            details={
                'amount': amount,
                'decline_reason': decline_reason
            },
            **kwargs
        )


class PaymentRefundError(PaymentError):
    """Exception raised when refund processing fails."""
    
    def __init__(
        self,
        payment_id: int,
        amount: float,
        reason: str,
        **kwargs
    ):
        super().__init__(
            f"Refund failed for payment {payment_id}: {reason}",
            code="REFUND_FAILED",
            status_code=400,
            payment_id=payment_id,
            details={
                'amount': amount,
                'reason': reason
            },
            **kwargs
        )


class PaymentMethodError(PaymentError):
    """Exception raised for payment method issues."""
    
    def __init__(
        self,
        payment_method_id: str,
        reason: str,
        **kwargs
    ):
        super().__init__(
            f"Payment method error: {reason}",
            code="PAYMENT_METHOD_ERROR",
            status_code=400,
            details={
                'payment_method_id': payment_method_id,
                'reason': reason
            },
            **kwargs
        )


class InsufficientFundsError(PaymentError):
    """Exception raised for insufficient funds."""
    
    def __init__(
        self,
        amount: float,
        available_balance: Optional[float] = None,
        **kwargs
    ):
        details = {'amount': amount}
        if available_balance:
            details['available_balance'] = available_balance
            
        super().__init__(
            f"Insufficient funds for payment of {amount}",
            code="INSUFFICIENT_FUNDS",
            status_code=402,
            details=details,
            **kwargs
        )


class PaymentTimeoutError(PaymentError):
    """Exception raised when payment times out."""
    
    def __init__(
        self,
        payment_id: int,
        timeout_seconds: int,
        **kwargs
    ):
        super().__init__(
            f"Payment {payment_id} timed out after {timeout_seconds}s",
            code="PAYMENT_TIMEOUT",
            status_code=408,
            payment_id=payment_id,
            details={'timeout_seconds': timeout_seconds},
            **kwargs
        )


# ----------------------------------------------------------------------------
# Vehicle Exceptions
# ----------------------------------------------------------------------------

class VehicleError(BusinessError):
    """Base exception for vehicle-related errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "VEHICLE_ERROR",
        vehicle_id: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if vehicle_id:
            details['vehicle_id'] = vehicle_id
        super().__init__(message, code, details=details, **kwargs)


class VehicleNotFoundError(VehicleError):
    """Exception raised when a vehicle is not found."""
    
    def __init__(
        self,
        vehicle_id: Union[int, str],
        **kwargs
    ):
        super().__init__(
            f"Vehicle not found: {vehicle_id}",
            code="VEHICLE_NOT_FOUND",
            status_code=404,
            vehicle_id=vehicle_id,
            **kwargs
        )


class LicensePlateAlreadyExistsError(VehicleError):
    """Exception raised when license plate already exists."""
    
    def __init__(
        self,
        license_plate: str,
        **kwargs
    ):
        super().__init__(
            f"License plate already exists: {license_plate}",
            code="LICENSE_PLATE_EXISTS",
            status_code=409,
            details={'license_plate': license_plate},
            **kwargs
        )


class InvalidVehicleTypeError(VehicleError):
    """Exception raised for invalid vehicle type."""
    
    def __init__(
        self,
        vehicle_type: str,
        allowed_types: List[str],
        **kwargs
    ):
        details = {
            'vehicle_type': vehicle_type,
            'allowed_types': allowed_types
        }
        super().__init__(
            f"Invalid vehicle type: {vehicle_type}. Allowed: {', '.join(allowed_types)}",
            code="INVALID_VEHICLE_TYPE",
            status_code=400,
            details=details,
            **kwargs
        )


class VehicleNotAuthorizedError(VehicleError):
    """Exception raised when vehicle is not authorized."""
    
    def __init__(
        self,
        license_plate: str,
        reason: str = "Vehicle not authorized for this spot",
        **kwargs
    ):
        super().__init__(
            f"Vehicle {license_plate} not authorized: {reason}",
            code="VEHICLE_NOT_AUTHORIZED",
            status_code=403,
            details={
                'license_plate': license_plate,
                'reason': reason
            },
            **kwargs
        )


# ----------------------------------------------------------------------------
# Waitlist Exceptions
# ----------------------------------------------------------------------------

class WaitlistError(BusinessError):
    """Base exception for waitlist-related errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "WAITLIST_ERROR",
        waitlist_id: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if waitlist_id:
            details['waitlist_id'] = waitlist_id
        super().__init__(message, code, details=details, **kwargs)


class WaitlistEntryNotFoundError(WaitlistError):
    """Exception raised when a waitlist entry is not found."""
    
    def __init__(
        self,
        waitlist_id: int,
        **kwargs
    ):
        super().__init__(
            f"Waitlist entry not found: {waitlist_id}",
            code="WAITLIST_ENTRY_NOT_FOUND",
            status_code=404,
            waitlist_id=waitlist_id,
            **kwargs
        )


class WaitlistFullError(WaitlistError):
    """Exception raised when waitlist is full."""
    
    def __init__(
        self,
        spot_id: int,
        max_size: int,
        **kwargs
    ):
        super().__init__(
            f"Waitlist for spot {spot_id} is full (max {max_size})",
            code="WAITLIST_FULL",
            status_code=409,
            details={
                'spot_id': spot_id,
                'max_size': max_size
            },
            **kwargs
        )


class AlreadyOnWaitlistError(WaitlistError):
    """Exception raised when user is already on waitlist."""
    
    def __init__(
        self,
        user_id: int,
        spot_id: int,
        **kwargs
    ):
        super().__init__(
            f"User {user_id} is already on waitlist for spot {spot_id}",
            code="ALREADY_ON_WAITLIST",
            status_code=409,
            details={
                'user_id': user_id,
                'spot_id': spot_id
            },
            **kwargs
        )


# ----------------------------------------------------------------------------
# Recurring Reservation Exceptions
# ----------------------------------------------------------------------------

class RecurringReservationError(BusinessError):
    """Base exception for recurring reservation errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "RECURRING_ERROR",
        recurring_id: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if recurring_id:
            details['recurring_id'] = recurring_id
        super().__init__(message, code, details=details, **kwargs)


class RecurringPatternError(RecurringReservationError):
    """Exception raised for invalid recurring patterns."""
    
    def __init__(
        self,
        pattern: Dict[str, Any],
        reason: str,
        **kwargs
    ):
        super().__init__(
            f"Invalid recurring pattern: {reason}",
            code="INVALID_RECURRING_PATTERN",
            status_code=400,
            details={
                'pattern': pattern,
                'reason': reason
            },
            **kwargs
        )


class RecurringGenerationError(RecurringReservationError):
    """Exception raised when generating recurring reservations fails."""
    
    def __init__(
        self,
        recurring_id: int,
        reason: str,
        **kwargs
    ):
        super().__init__(
            f"Failed to generate recurring reservations for {recurring_id}: {reason}",
            code="RECURRING_GENERATION_ERROR",
            status_code=500,
            recurring_id=recurring_id,
            details={'reason': reason},
            **kwargs
        )


# ----------------------------------------------------------------------------
# Integration Exceptions
# ----------------------------------------------------------------------------

class IntegrationError(SystemError):
    """Base exception for integration errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "INTEGRATION_ERROR",
        service: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if service:
            details['service'] = service
        super().__init__(message, code, details=details, **kwargs)


class ExternalServiceError(IntegrationError):
    """Exception raised when an external service fails."""
    
    def __init__(
        self,
        service: str,
        endpoint: Optional[str] = None,
        response: Optional[Any] = None,
        **kwargs
    ):
        details = {
            'service': service,
            'endpoint': endpoint
        }
        if response:
            details['response'] = str(response)
            
        super().__init__(
            f"External service {service} failed",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=503,
            details=details,
            **kwargs
        )


class DatabaseError(SystemError):
    """Exception raised for database errors."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation
        if table:
            details['table'] = table
        super().__init__(
            message,
            code="DATABASE_ERROR",
            status_code=500,
            details=details,
            **kwargs
        )


class CacheError(SystemError):
    """Exception raised for cache errors."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        key: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation
        if key:
            details['key'] = key
        super().__init__(
            message,
            code="CACHE_ERROR",
            status_code=500,
            details=details,
            **kwargs
        )


class QueueError(SystemError):
    """Exception raised for message queue errors."""
    
    def __init__(
        self,
        message: str,
        queue: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if queue:
            details['queue'] = queue
        super().__init__(
            message,
            code="QUEUE_ERROR",
            status_code=500,
            details=details,
            **kwargs
        )


# ----------------------------------------------------------------------------
# Validation Exceptions
# ----------------------------------------------------------------------------

class ValidationError(BusinessError):
    """Exception raised for validation errors."""
    
    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, List[str]]] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if field_errors:
            details['field_errors'] = field_errors
        super().__init__(
            message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details,
            **kwargs
        )


class InvalidInputError(ValidationError):
    """Exception raised for invalid input."""
    
    def __init__(
        self,
        field: str,
        value: Any,
        reason: str,
        **kwargs
    ):
        super().__init__(
            f"Invalid input for field '{field}': {reason}",
            field_errors={field: [reason]},
            details={
                'field': field,
                'value': str(value),
                'reason': reason
            },
            **kwargs
        )


class MissingRequiredFieldError(ValidationError):
    """Exception raised for missing required fields."""
    
    def __init__(
        self,
        fields: List[str],
        **kwargs
    ):
        field_errors = {field: ['This field is required'] for field in fields}
        super().__init__(
            f"Missing required fields: {', '.join(fields)}",
            field_errors=field_errors,
            details={'missing_fields': fields},
            **kwargs
        )


# ----------------------------------------------------------------------------
# Rate Limit Exceptions
# ----------------------------------------------------------------------------

class RateLimitError(BusinessError):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(
        self,
        limit: int,
        window: int,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        details = {
            'limit': limit,
            'window': window
        }
        if retry_after:
            details['retry_after'] = retry_after
            
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window} seconds",
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
            **kwargs
        )


class ConcurrencyLimitError(BusinessError):
    """Exception raised when concurrency limit is exceeded."""
    
    def __init__(
        self,
        limit: int,
        resource: str,
        **kwargs
    ):
        super().__init__(
            f"Concurrency limit exceeded for {resource}: max {limit} concurrent operations",
            code="CONCURRENCY_LIMIT_EXCEEDED",
            status_code=429,
            details={
                'limit': limit,
                'resource': resource
            },
            **kwargs
        )


# ----------------------------------------------------------------------------
# File/Storage Exceptions
# ----------------------------------------------------------------------------

class FileError(SystemError):
    """Base exception for file-related errors."""
    
    def __init__(
        self,
        message: str,
        code: str = "FILE_ERROR",
        filename: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if filename:
            details['filename'] = filename
        super().__init__(message, code, details=details, **kwargs)


class FileNotFoundError(FileError):
    """Exception raised when a file is not found."""
    
    def __init__(
        self,
        filename: str,
        **kwargs
    ):
        super().__init__(
            f"File not found: {filename}",
            code="FILE_NOT_FOUND",
            status_code=404,
            filename=filename,
            **kwargs
        )


class FileUploadError(FileError):
    """Exception raised when file upload fails."""
    
    def __init__(
        self,
        filename: str,
        reason: str,
        **kwargs
    ):
        super().__init__(
            f"File upload failed for {filename}: {reason}",
            code="FILE_UPLOAD_ERROR",
            status_code=400,
            filename=filename,
            details={'reason': reason},
            **kwargs
        )


class FileTooLargeError(FileError):
    """Exception raised when file is too large."""
    
    def __init__(
        self,
        filename: str,
        size: int,
        max_size: int,
        **kwargs
    ):
        super().__init__(
            f"File {filename} too large: {size} bytes (max {max_size})",
            code="FILE_TOO_LARGE",
            status_code=400,
            filename=filename,
            details={
                'size': size,
                'max_size': max_size
            },
            **kwargs
        )


class InvalidFileTypeError(FileError):
    """Exception raised for invalid file type."""
    
    def __init__(
        self,
        filename: str,
        file_type: str,
        allowed_types: List[str],
        **kwargs
    ):
        super().__init__(
            f"Invalid file type for {filename}: {file_type}. Allowed: {', '.join(allowed_types)}",
            code="INVALID_FILE_TYPE",
            status_code=400,
            filename=filename,
            details={
                'file_type': file_type,
                'allowed_types': allowed_types
            },
            **kwargs
        )


# ============================================================================
# Error Handler Utilities
# ============================================================================

class ErrorHandler:
    """Utility class for handling exceptions."""
    
    @staticmethod
    def handle_exception(error: Exception, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Handle an exception and return error response."""
        if isinstance(error, ParkingException):
            return error.to_dict()
        
        # Handle built-in exceptions
        if isinstance(error, ValueError):
            return ParkingException(
                str(error),
                code="VALUE_ERROR",
                status_code=400,
                details=context
            ).to_dict()
        
        if isinstance(error, TypeError):
            return ParkingException(
                str(error),
                code="TYPE_ERROR",
                status_code=400,
                details=context
            ).to_dict()
        
        if isinstance(error, KeyError):
            return ParkingException(
                f"Missing key: {error}",
                code="KEY_ERROR",
                status_code=400,
                details=context
            ).to_dict()
        
        if isinstance(error, IndexError):
            return ParkingException(
                f"Index error: {error}",
                code="INDEX_ERROR",
                status_code=400,
                details=context
            ).to_dict()
        
        if isinstance(error, AttributeError):
            return ParkingException(
                f"Attribute error: {error}",
                code="ATTRIBUTE_ERROR",
                status_code=400,
                details=context
            ).to_dict()
        
        if isinstance(error, ImportError):
            return ParkingException(
                f"Import error: {error}",
                code="IMPORT_ERROR",
                status_code=500,
                details=context
            ).to_dict()
        
        if isinstance(error, NotImplementedError):
            return ParkingException(
                "Feature not implemented",
                code="NOT_IMPLEMENTED",
                status_code=501,
                details=context
            ).to_dict()
        
        if isinstance(error, PermissionError):
            return ParkingException(
                str(error),
                code="PERMISSION_ERROR",
                status_code=403,
                details=context
            ).to_dict()
        
        if isinstance(error, TimeoutError):
            return ParkingException(
                "Operation timed out",
                code="TIMEOUT_ERROR",
                status_code=408,
                details=context
            ).to_dict()
        
        if isinstance(error, ConnectionError):
            return ParkingException(
                "Connection error",
                code="CONNECTION_ERROR",
                status_code=503,
                details=context
            ).to_dict()
        
        if isinstance(error, MemoryError):
            return ParkingException(
                "Memory error",
                code="MEMORY_ERROR",
                status_code=500,
                details=context
            ).to_dict()
        
        # Unknown error
        return ParkingException(
            f"An unexpected error occurred: {str(error)}",
            code="UNKNOWN_ERROR",
            status_code=500,
            details={
                'error_type': type(error).__name__,
                'context': context
            },
            cause=error
        ).to_dict()
    
    @staticmethod
    def log_exception(logger, error: Exception, context: Optional[Dict] = None):
        """Log an exception with context."""
        error_dict = ErrorHandler.handle_exception(error, context)
        error_data = error_dict.get('error', {})
        
        logger.error(
            f"Exception: {error_data.get('code')} - {error_data.get('message')}",
            extra={
                'error_code': error_data.get('code'),
                'status_code': error_data.get('status_code'),
                'details': error_data.get('details'),
                'timestamp': error_data.get('timestamp'),
                'traceback': traceback.format_exc()
            }
        )


# ============================================================================
# Exception Factories
# ============================================================================

def create_exception(
    error_type: str,
    message: str,
    **kwargs
) -> ParkingException:
    """
    Factory function to create exceptions dynamically.
    
    Args:
        error_type: Type of exception to create
        message: Error message
        **kwargs: Additional arguments for the exception
        
    Returns:
        ParkingException instance
    """
    exception_map = {
        # Reservation errors
        'reservation_not_found': ReservationNotFoundError,
        'reservation_conflict': ReservationConflictError,
        'reservation_cancellation': ReservationCancellationError,
        'reservation_checkin': ReservationCheckInError,
        'reservation_checkout': ReservationCheckOutError,
        'reservation_expired': ReservationExpiredError,
        'reservation_modification': ReservationModificationError,
        'invalid_reservation_time': InvalidReservationTimeError,
        'reservation_limit': ReservationLimitExceededError,
        
        # Parking spot errors
        'spot_not_found': ParkingSpotNotFoundError,
        'spot_unavailable': ParkingSpotUnavailableError,
        'spot_maintenance': ParkingSpotMaintenanceError,
        'invalid_spot_type': InvalidSpotTypeError,
        
        # User errors
        'user_not_found': UserNotFoundError,
        'authentication': UserAuthenticationError,
        'authorization': UserAuthorizationError,
        'account_locked': UserAccountLockedError,
        'account_disabled': UserAccountDisabledError,
        'email_exists': UserEmailAlreadyExistsError,
        'phone_exists': UserPhoneAlreadyExistsError,
        'verification': UserVerificationError,
        
        # Payment errors
        'payment_failed': PaymentFailedError,
        'payment_declined': PaymentDeclinedError,
        'refund_failed': PaymentRefundError,
        'payment_method': PaymentMethodError,
        'insufficient_funds': InsufficientFundsError,
        'payment_timeout': PaymentTimeoutError,
        
        # Vehicle errors
        'vehicle_not_found': VehicleNotFoundError,
        'license_plate_exists': LicensePlateAlreadyExistsError,
        'invalid_vehicle_type': InvalidVehicleTypeError,
        'vehicle_not_authorized': VehicleNotAuthorizedError,
        
        # Waitlist errors
        'waitlist_not_found': WaitlistEntryNotFoundError,
        'waitlist_full': WaitlistFullError,
        'already_on_waitlist': AlreadyOnWaitlistError,
        
        # Recurring errors
        'recurring_pattern': RecurringPatternError,
        'recurring_generation': RecurringGenerationError,
        
        # Integration errors
        'external_service': ExternalServiceError,
        'database': DatabaseError,
        'cache': CacheError,
        'queue': QueueError,
        
        # Validation errors
        'validation': ValidationError,
        'invalid_input': InvalidInputError,
        'missing_field': MissingRequiredFieldError,
        
        # Rate limit errors
        'rate_limit': RateLimitError,
        'concurrency_limit': ConcurrencyLimitError,
        
        # File errors
        'file_not_found': FileNotFoundError,
        'file_upload': FileUploadError,
        'file_too_large': FileTooLargeError,
        'invalid_file_type': InvalidFileTypeError,
    }
    
    exception_class = exception_map.get(error_type, ParkingException)
    
    if exception_class == ReservationNotFoundError:
        return exception_class(kwargs.get('reservation_id', 'unknown'), **kwargs)
    elif exception_class == UserNotFoundError:
        return exception_class(
            user_id=kwargs.get('user_id'),
            email=kwargs.get('email'),
            **kwargs
        )
    elif exception_class == PaymentFailedError:
        return exception_class(
            amount=kwargs.get('amount', 0),
            reason=kwargs.get('reason', 'Unknown'),
            payment_method=kwargs.get('payment_method'),
            **kwargs
        )
    # Add more specific factory logic as needed
    
    return exception_class(message, **kwargs)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Base exceptions
    'ParkingException',
    'BusinessError',
    'SystemError',
    'ConfigurationError',
    
    # Reservation exceptions
    'ReservationError',
    'ReservationNotFoundError',
    'ReservationConflictError',
    'ReservationCancellationError',
    'ReservationCheckInError',
    'ReservationCheckOutError',
    'ReservationExpiredError',
    'ReservationModificationError',
    'InvalidReservationTimeError',
    'ReservationLimitExceededError',
    
    # Parking spot exceptions
    'ParkingSpotError',
    'ParkingSpotNotFoundError',
    'ParkingSpotUnavailableError',
    'ParkingSpotMaintenanceError',
    'InvalidSpotTypeError',
    
    # User exceptions
    'UserError',
    'UserNotFoundError',
    'UserAuthenticationError',
    'UserAuthorizationError',
    'UserAccountLockedError',
    'UserAccountDisabledError',
    'UserEmailAlreadyExistsError',
    'UserPhoneAlreadyExistsError',
    'UserVerificationError',
    
    # Payment exceptions
    'PaymentError',
    'PaymentFailedError',
    'PaymentDeclinedError',
    'PaymentRefundError',
    'PaymentMethodError',
    'InsufficientFundsError',
    'PaymentTimeoutError',
    
    # Vehicle exceptions
    'VehicleError',
    'VehicleNotFoundError',
    'LicensePlateAlreadyExistsError',
    'InvalidVehicleTypeError',
    'VehicleNotAuthorizedError',
    
    # Waitlist exceptions
    'WaitlistError',
    'WaitlistEntryNotFoundError',
    'WaitlistFullError',
    'AlreadyOnWaitlistError',
    
    # Recurring reservation exceptions
    'RecurringReservationError',
    'RecurringPatternError',
    'RecurringGenerationError',
    
    # Integration exceptions
    'IntegrationError',
    'ExternalServiceError',
    'DatabaseError',
    'CacheError',
    'QueueError',
    
    # Validation exceptions
    'ValidationError',
    'InvalidInputError',
    'MissingRequiredFieldError',
    
    # Rate limit exceptions
    'RateLimitError',
    'ConcurrencyLimitError',
    
    # File exceptions
    'FileError',
    'FileNotFoundError',
    'FileUploadError',
    'FileTooLargeError',
    'InvalidFileTypeError',
    
    # Utilities
    'ErrorHandler',
    'create_exception',
]