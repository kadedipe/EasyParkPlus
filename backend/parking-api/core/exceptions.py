"""
Custom exceptions and error handling utilities for the application.
Defines a hierarchy of exception classes for different error types.
"""

from typing import Any, Dict, List, Optional, Union
from fastapi import status
from datetime import datetime


class BaseAppException(Exception):
    """
    Base exception class for all application exceptions.
    """
    
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Union[Dict[str, Any], List[Any]]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary format for API responses.
        """
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "status_code": self.status_code,
                "timestamp": self.timestamp,
                "details": self.details
            }
        }
    
    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ============================================================================
# Authentication & Authorization Exceptions
# ============================================================================

class AuthenticationException(BaseAppException):
    """
    Base class for authentication-related exceptions.
    """
    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = "AUTHENTICATION_ERROR",
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class InvalidCredentialsException(AuthenticationException):
    """
    Exception raised when invalid credentials are provided.
    """
    def __init__(self, details: Optional[Any] = None):
        super().__init__(
            message="Invalid email or password",
            code="INVALID_CREDENTIALS",
            details=details
        )


class InvalidTokenException(AuthenticationException):
    """
    Exception raised when an invalid token is provided.
    """
    def __init__(self, details: Optional[Any] = None):
        super().__init__(
            message="Invalid or malformed token",
            code="INVALID_TOKEN",
            details=details
        )


class ExpiredTokenException(AuthenticationException):
    """
    Exception raised when a token has expired.
    """
    def __init__(self, details: Optional[Any] = None):
        super().__init__(
            message="Token has expired",
            code="EXPIRED_TOKEN",
            details=details
        )


class TokenRevokedException(AuthenticationException):
    """
    Exception raised when a token has been revoked.
    """
    def __init__(self, details: Optional[Any] = None):
        super().__init__(
            message="Token has been revoked",
            code="TOKEN_REVOKED",
            details=details
        )


class AccountDisabledException(AuthenticationException):
    """
    Exception raised when a user account is disabled.
    """
    def __init__(self, details: Optional[Any] = None):
        super().__init__(
            message="Account is disabled",
            code="ACCOUNT_DISABLED",
            details=details
        )


class AccountLockedException(AuthenticationException):
    """
    Exception raised when a user account is locked.
    """
    def __init__(self, details: Optional[Any] = None):
        super().__init__(
            message="Account is locked due to too many failed attempts",
            code="ACCOUNT_LOCKED",
            details=details
        )


class EmailNotVerifiedException(AuthenticationException):
    """
    Exception raised when email is not verified.
    """
    def __init__(self, details: Optional[Any] = None):
        super().__init__(
            message="Email address not verified",
            code="EMAIL_NOT_VERIFIED",
            details=details
        )


class PhoneNotVerifiedException(AuthenticationException):
    """
    Exception raised when phone number is not verified.
    """
    def __init__(self, details: Optional[Any] = None):
        super().__init__(
            message="Phone number not verified",
            code="PHONE_NOT_VERIFIED",
            details=details
        )


class AuthorizationException(BaseAppException):
    """
    Base class for authorization-related exceptions.
    """
    def __init__(
        self,
        message: str = "Access denied",
        code: str = "AUTHORIZATION_ERROR",
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class InsufficientPermissionsException(AuthorizationException):
    """
    Exception raised when user lacks required permissions.
    """
    def __init__(self, required_permissions: Optional[List[str]] = None):
        message = "Insufficient permissions to perform this action"
        details = {"required_permissions": required_permissions} if required_permissions else None
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            details=details
        )


class RoleRequiredException(AuthorizationException):
    """
    Exception raised when user lacks required role.
    """
    def __init__(self, required_roles: Optional[List[str]] = None):
        message = "Role required to perform this action"
        details = {"required_roles": required_roles} if required_roles else None
        super().__init__(
            message=message,
            code="ROLE_REQUIRED",
            details=details
        )


class ResourceOwnershipException(AuthorizationException):
    """
    Exception raised when user does not own the resource.
    """
    def __init__(self, resource_type: str = "resource"):
        super().__init__(
            message=f"You do not own this {resource_type}",
            code="RESOURCE_OWNERSHIP",
            details={"resource_type": resource_type}
        )


# ============================================================================
# Resource Exceptions
# ============================================================================

class ResourceNotFoundException(BaseAppException):
    """
    Base class for resource not found exceptions.
    """
    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "RESOURCE_NOT_FOUND",
        resource_type: Optional[str] = None,
        resource_id: Optional[Any] = None,
        details: Optional[Any] = None
    ):
        if resource_type and resource_id:
            message = f"{resource_type} with id '{resource_id}' not found"
            details = details or {}
            details.update({"resource_type": resource_type, "resource_id": str(resource_id)})
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )


class UserNotFoundException(ResourceNotFoundException):
    """
    Exception raised when a user is not found.
    """
    def __init__(self, user_id: Optional[Any] = None, email: Optional[str] = None):
        if email:
            message = f"User with email '{email}' not found"
            details = {"email": email}
        elif user_id:
            message = f"User with id '{user_id}' not found"
            details = {"user_id": str(user_id)}
        else:
            message = "User not found"
            details = None
        
        super().__init__(
            message=message,
            code="USER_NOT_FOUND",
            resource_type="User",
            resource_id=user_id,
            details=details
        )


class VehicleNotFoundException(ResourceNotFoundException):
    """
    Exception raised when a vehicle is not found.
    """
    def __init__(self, vehicle_id: Optional[Any] = None, license_plate: Optional[str] = None):
        if license_plate:
            message = f"Vehicle with license plate '{license_plate}' not found"
            details = {"license_plate": license_plate}
        elif vehicle_id:
            message = f"Vehicle with id '{vehicle_id}' not found"
            details = {"vehicle_id": str(vehicle_id)}
        else:
            message = "Vehicle not found"
            details = None
        
        super().__init__(
            message=message,
            code="VEHICLE_NOT_FOUND",
            resource_type="Vehicle",
            resource_id=vehicle_id,
            details=details
        )


class ParkingSpotNotFoundException(ResourceNotFoundException):
    """
    Exception raised when a parking spot is not found.
    """
    def __init__(self, spot_id: Optional[Any] = None, spot_number: Optional[str] = None):
        if spot_number:
            message = f"Parking spot '{spot_number}' not found"
            details = {"spot_number": spot_number}
        elif spot_id:
            message = f"Parking spot with id '{spot_id}' not found"
            details = {"spot_id": str(spot_id)}
        else:
            message = "Parking spot not found"
            details = None
        
        super().__init__(
            message=message,
            code="PARKING_SPOT_NOT_FOUND",
            resource_type="ParkingSpot",
            resource_id=spot_id,
            details=details
        )


class ReservationNotFoundException(ResourceNotFoundException):
    """
    Exception raised when a reservation is not found.
    """
    def __init__(self, reservation_id: Optional[Any] = None):
        if reservation_id:
            message = f"Reservation with id '{reservation_id}' not found"
            details = {"reservation_id": str(reservation_id)}
        else:
            message = "Reservation not found"
            details = None
        
        super().__init__(
            message=message,
            code="RESERVATION_NOT_FOUND",
            resource_type="Reservation",
            resource_id=reservation_id,
            details=details
        )


class PaymentNotFoundException(ResourceNotFoundException):
    """
    Exception raised when a payment is not found.
    """
    def __init__(self, payment_id: Optional[Any] = None, transaction_id: Optional[str] = None):
        if transaction_id:
            message = f"Payment with transaction id '{transaction_id}' not found"
            details = {"transaction_id": transaction_id}
        elif payment_id:
            message = f"Payment with id '{payment_id}' not found"
            details = {"payment_id": str(payment_id)}
        else:
            message = "Payment not found"
            details = None
        
        super().__init__(
            message=message,
            code="PAYMENT_NOT_FOUND",
            resource_type="Payment",
            resource_id=payment_id,
            details=details
        )


class ReviewNotFoundException(ResourceNotFoundException):
    """
    Exception raised when a review is not found.
    """
    def __init__(self, review_id: Optional[Any] = None):
        if review_id:
            message = f"Review with id '{review_id}' not found"
            details = {"review_id": str(review_id)}
        else:
            message = "Review not found"
            details = None
        
        super().__init__(
            message=message,
            code="REVIEW_NOT_FOUND",
            resource_type="Review",
            resource_id=review_id,
            details=details
        )


# ============================================================================
# Conflict Exceptions
# ============================================================================

class ConflictException(BaseAppException):
    """
    Base class for conflict exceptions (HTTP 409).
    """
    def __init__(
        self,
        message: str = "Conflict with existing resource",
        code: str = "CONFLICT",
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class DuplicateEntryException(ConflictException):
    """
    Exception raised when trying to create a duplicate entry.
    """
    def __init__(self, field: str, value: Any, resource: str = "Resource"):
        super().__init__(
            message=f"{resource} with {field} '{value}' already exists",
            code="DUPLICATE_ENTRY",
            details={"field": field, "value": str(value), "resource": resource}
        )


class UserAlreadyExistsException(DuplicateEntryException):
    """
    Exception raised when trying to register with existing email.
    """
    def __init__(self, email: str):
        super().__init__("email", email, "User")


class LicensePlateExistsException(DuplicateEntryException):
    """
    Exception raised when license plate already exists.
    """
    def __init__(self, license_plate: str):
        super().__init__("license_plate", license_plate, "Vehicle")


class SpotNumberExistsException(DuplicateEntryException):
    """
    Exception raised when spot number already exists.
    """
    def __init__(self, spot_number: str):
        super().__init__("spot_number", spot_number, "ParkingSpot")


class ReservationConflictException(ConflictException):
    """
    Exception raised when reservation conflicts with existing one.
    """
    def __init__(self, spot_id: str, start_time: datetime, end_time: datetime):
        super().__init__(
            message="Reservation conflicts with an existing reservation",
            code="RESERVATION_CONFLICT",
            details={
                "spot_id": spot_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        )


class AlreadyReviewedException(ConflictException):
    """
    Exception raised when user already reviewed a spot.
    """
    def __init__(self, spot_id: str):
        super().__init__(
            message="You have already reviewed this parking spot",
            code="ALREADY_REVIEWED",
            details={"spot_id": spot_id}
        )


class AlreadyOnWaitlistException(ConflictException):
    """
    Exception raised when user is already on waitlist.
    """
    def __init__(self, spot_type: str):
        super().__init__(
            message=f"You are already on the waitlist for {spot_type} spots",
            code="ALREADY_ON_WAITLIST",
            details={"spot_type": spot_type}
        )


# ============================================================================
# Validation Exceptions
# ============================================================================

class ValidationException(BaseAppException):
    """
    Base class for validation exceptions (HTTP 422).
    """
    def __init__(
        self,
        message: str = "Validation error",
        code: str = "VALIDATION_ERROR",
        details: Optional[Union[Dict[str, Any], List[Any]]] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class InvalidInputException(ValidationException):
    """
    Exception raised for invalid input.
    """
    def __init__(self, field: str, reason: str, value: Optional[Any] = None):
        details = {
            "field": field,
            "reason": reason
        }
        if value is not None:
            details["value"] = str(value)
        
        super().__init__(
            message=f"Invalid input for field '{field}': {reason}",
            code="INVALID_INPUT",
            details=details
        )


class MissingFieldException(ValidationException):
    """
    Exception raised for missing required fields.
    """
    def __init__(self, fields: List[str]):
        super().__init__(
            message=f"Missing required fields: {', '.join(fields)}",
            code="MISSING_FIELDS",
            details={"fields": fields}
        )


class InvalidDateFormatException(ValidationException):
    """
    Exception raised for invalid date format.
    """
    def __init__(self, field: str, value: str):
        super().__init__(
            message=f"Invalid date format for '{field}': {value}",
            code="INVALID_DATE_FORMAT",
            details={"field": field, "value": value}
        )


class InvalidTimeRangeException(ValidationException):
    """
    Exception raised for invalid time range.
    """
    def __init__(self, start_time: datetime, end_time: datetime, reason: str):
        super().__init__(
            message=f"Invalid time range: {reason}",
            code="INVALID_TIME_RANGE",
            details={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "reason": reason
            }
        )


class InvalidEnumValueException(ValidationException):
    """
    Exception raised for invalid enum value.
    """
    def __init__(self, field: str, value: str, allowed_values: List[str]):
        super().__init__(
            message=f"Invalid value for '{field}': {value}",
            code="INVALID_ENUM_VALUE",
            details={
                "field": field,
                "value": value,
                "allowed_values": allowed_values
            }
        )


# ============================================================================
# Business Logic Exceptions
# ============================================================================

class BusinessException(BaseAppException):
    """
    Base class for business logic exceptions (HTTP 400).
    """
    def __init__(
        self,
        message: str,
        code: str = "BUSINESS_ERROR",
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class SpotNotAvailableException(BusinessException):
    """
    Exception raised when parking spot is not available.
    """
    def __init__(self, spot_id: Optional[str] = None):
        message = "Parking spot is not available"
        details = {"spot_id": spot_id} if spot_id else None
        super().__init__(
            message=message,
            code="SPOT_NOT_AVAILABLE",
            details=details
        )


class InvalidReservationStatusException(BusinessException):
    """
    Exception raised when reservation status is invalid for operation.
    """
    def __init__(self, current_status: str, required_status: Optional[str] = None):
        message = f"Cannot perform operation on reservation with status '{current_status}'"
        details = {"current_status": current_status}
        if required_status:
            details["required_status"] = required_status
        
        super().__init__(
            message=message,
            code="INVALID_RESERVATION_STATUS",
            details=details
        )


class ReservationTooLateException(BusinessException):
    """
    Exception raised when trying to modify reservation too late.
    """
    def __init__(self, hours_before_start: int):
        super().__init__(
            message=f"Reservations can only be modified up to {hours_before_start} hours before start time",
            code="RESERVATION_TOO_LATE",
            details={"hours_before_start": hours_before_start}
        )


class ReservationTooEarlyException(BusinessException):
    """
    Exception raised when trying to check in too early.
    """
    def __init__(self, minutes_early: int):
        super().__init__(
            message=f"Check-in is only allowed within {minutes_early} minutes of start time",
            code="RESERVATION_TOO_EARLY",
            details={"minutes_early": minutes_early}
        )


class PaymentFailedException(BusinessException):
    """
    Exception raised when payment processing fails.
    """
    def __init__(self, reason: str, transaction_id: Optional[str] = None):
        details = {"reason": reason}
        if transaction_id:
            details["transaction_id"] = transaction_id
        
        super().__init__(
            message=f"Payment failed: {reason}",
            code="PAYMENT_FAILED",
            details=details
        )


class InsufficientBalanceException(BusinessException):
    """
    Exception raised when user has insufficient balance.
    """
    def __init__(self, required: float, available: float, currency: str = "USD"):
        super().__init__(
            message=f"Insufficient balance. Required: {required} {currency}, Available: {available} {currency}",
            code="INSUFFICIENT_BALANCE",
            details={
                "required": required,
                "available": available,
                "currency": currency
            }
        )


class RefundFailedException(BusinessException):
    """
    Exception raised when refund processing fails.
    """
    def __init__(self, payment_id: str, reason: str):
        super().__init__(
            message=f"Refund failed for payment {payment_id}: {reason}",
            code="REFUND_FAILED",
            details={"payment_id": payment_id, "reason": reason}
        )


class MaximumReservationsReachedException(BusinessException):
    """
    Exception raised when user reaches maximum active reservations.
    """
    def __init__(self, max_reservations: int):
        super().__init__(
            message=f"Maximum active reservations ({max_reservations}) reached",
            code="MAX_RESERVATIONS_REACHED",
            details={"max_reservations": max_reservations}
        )


# ============================================================================
# Rate Limiting Exceptions
# ============================================================================

class RateLimitException(BaseAppException):
    """
    Exception raised when rate limit is exceeded (HTTP 429).
    """
    def __init__(
        self,
        limit: int,
        window_seconds: int,
        retry_after: Optional[int] = None
    ):
        message = f"Rate limit exceeded. Maximum {limit} requests per {window_seconds} seconds."
        details = {
            "limit": limit,
            "window_seconds": window_seconds
        }
        if retry_after:
            details["retry_after"] = retry_after
        
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


# ============================================================================
# Service Exceptions
# ============================================================================

class ServiceException(BaseAppException):
    """
    Base class for service-related exceptions (HTTP 503).
    """
    def __init__(
        self,
        message: str,
        code: str = "SERVICE_ERROR",
        service_name: Optional[str] = None,
        details: Optional[Any] = None
    ):
        if service_name and not details:
            details = {"service": service_name}
        
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


class ServiceUnavailableException(ServiceException):
    """
    Exception raised when a service is unavailable.
    """
    def __init__(self, service_name: str, reason: Optional[str] = None):
        message = f"Service '{service_name}' is currently unavailable"
        if reason:
            message += f": {reason}"
        
        super().__init__(
            message=message,
            code="SERVICE_UNAVAILABLE",
            service_name=service_name,
            details={"service": service_name, "reason": reason}
        )


class ExternalServiceException(ServiceException):
    """
    Exception raised when an external service call fails.
    """
    def __init__(self, service_name: str, status_code: Optional[int] = None, response: Optional[str] = None):
        message = f"External service '{service_name}' returned an error"
        details = {"service": service_name}
        if status_code:
            details["status_code"] = status_code
        if response:
            details["response"] = response
        
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            details=details
        )


class DatabaseException(ServiceException):
    """
    Exception raised for database errors.
    """
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Database error during {operation}: {reason}",
            code="DATABASE_ERROR",
            service_name="database",
            details={"operation": operation, "reason": reason}
        )


class CacheException(ServiceException):
    """
    Exception raised for cache errors.
    """
    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Cache error during {operation}: {reason}",
            code="CACHE_ERROR",
            service_name="cache",
            details={"operation": operation, "reason": reason}
        )


# ============================================================================
# File Upload Exceptions
# ============================================================================

class FileUploadException(BaseAppException):
    """
    Base class for file upload exceptions (HTTP 400).
    """
    def __init__(
        self,
        message: str,
        code: str = "FILE_UPLOAD_ERROR",
        details: Optional[Any] = None
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class FileTooLargeException(FileUploadException):
    """
    Exception raised when uploaded file is too large.
    """
    def __init__(self, max_size_mb: int, actual_size_mb: float):
        super().__init__(
            message=f"File too large. Maximum size: {max_size_mb}MB, Uploaded: {actual_size_mb:.2f}MB",
            code="FILE_TOO_LARGE",
            details={
                "max_size_mb": max_size_mb,
                "actual_size_mb": actual_size_mb
            }
        )


class InvalidFileTypeException(FileUploadException):
    """
    Exception raised when file type is not allowed.
    """
    def __init__(self, file_type: str, allowed_types: List[str]):
        super().__init__(
            message=f"File type '{file_type}' not allowed",
            code="INVALID_FILE_TYPE",
            details={
                "file_type": file_type,
                "allowed_types": allowed_types
            }
        )


class FileUploadFailedException(FileUploadException):
    """
    Exception raised when file upload fails.
    """
    def __init__(self, reason: str):
        super().__init__(
            message=f"File upload failed: {reason}",
            code="FILE_UPLOAD_FAILED",
            details={"reason": reason}
        )


# ============================================================================
# Utility Functions
# ============================================================================

def handle_exception(e: Exception) -> BaseAppException:
    """
    Convert any exception to a BaseAppException.
    """
    if isinstance(e, BaseAppException):
        return e
    
    # Convert common exceptions
    if isinstance(e, ValueError):
        return InvalidInputException("value", str(e))
    
    if isinstance(e, KeyError):
        return InvalidInputException("key", f"Missing key: {str(e)}")
    
    if isinstance(e, TypeError):
        return InvalidInputException("type", str(e))
    
    if isinstance(e, ConnectionError):
        return ServiceUnavailableException("network", str(e))
    
    # Default to internal error
    return BaseAppException(
        message=f"An unexpected error occurred: {str(e)}",
        code="INTERNAL_ERROR"
    )


def is_client_error(exception: BaseAppException) -> bool:
    """
    Check if exception is a client error (4xx).
    """
    return 400 <= exception.status_code < 500


def is_server_error(exception: BaseAppException) -> bool:
    """
    Check if exception is a server error (5xx).
    """
    return exception.status_code >= 500


# Export all exceptions
__all__ = [
    # Base
    'BaseAppException',
    'handle_exception',
    'is_client_error',
    'is_server_error',
    
    # Authentication & Authorization
    'AuthenticationException',
    'InvalidCredentialsException',
    'InvalidTokenException',
    'ExpiredTokenException',
    'TokenRevokedException',
    'AccountDisabledException',
    'AccountLockedException',
    'EmailNotVerifiedException',
    'PhoneNotVerifiedException',
    'AuthorizationException',
    'InsufficientPermissionsException',
    'RoleRequiredException',
    'ResourceOwnershipException',
    
    # Resource Not Found
    'ResourceNotFoundException',
    'UserNotFoundException',
    'VehicleNotFoundException',
    'ParkingSpotNotFoundException',
    'ReservationNotFoundException',
    'PaymentNotFoundException',
    'ReviewNotFoundException',
    
    # Conflict
    'ConflictException',
    'DuplicateEntryException',
    'UserAlreadyExistsException',
    'LicensePlateExistsException',
    'SpotNumberExistsException',
    'ReservationConflictException',
    'AlreadyReviewedException',
    'AlreadyOnWaitlistException',
    
    # Validation
    'ValidationException',
    'InvalidInputException',
    'MissingFieldException',
    'InvalidDateFormatException',
    'InvalidTimeRangeException',
    'InvalidEnumValueException',
    
    # Business Logic
    'BusinessException',
    'SpotNotAvailableException',
    'InvalidReservationStatusException',
    'ReservationTooLateException',
    'ReservationTooEarlyException',
    'PaymentFailedException',
    'InsufficientBalanceException',
    'RefundFailedException',
    'MaximumReservationsReachedException',
    
    # Rate Limiting
    'RateLimitException',
    
    # Service
    'ServiceException',
    'ServiceUnavailableException',
    'ExternalServiceException',
    'DatabaseException',
    'CacheException',
    
    # File Upload
    'FileUploadException',
    'FileTooLargeException',
    'InvalidFileTypeException',
    'FileUploadFailedException'
]