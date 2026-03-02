"""Custom exceptions for the parking management system."""

from typing import Optional, Dict, Any
from ..constants.error_codes import ErrorCodes


class ParkingManagementException(Exception):
    """Base exception for parking management system."""
    
    def __init__(self, error_code: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.error_code = error_code
        self.http_status = ErrorCodes.get_http_status(error_code)
        self.message = message or ErrorCodes.get_message(error_code)
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "http_status": self.http_status
        }


class AuthenticationError(ParkingManagementException):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.AUTHENTICATION_ERROR[0], message, details)


class AuthorizationError(ParkingManagementException):
    """Exception raised for authorization errors."""
    
    def __init__(self, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.AUTHORIZATION_ERROR[0], message, details)


class ResourceNotFoundError(ParkingManagementException):
    """Exception raised when a resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: Any, message: Optional[str] = None):
        details = {"resource_type": resource_type, "resource_id": str(resource_id)}
        super().__init__(ErrorCodes.RESOURCE_NOT_FOUND[0], message, details)


class ResourceConflictError(ParkingManagementException):
    """Exception raised for resource conflicts."""
    
    def __init__(self, resource_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCodes.RESOURCE_CONFLICT[0], None, {"resource_type": resource_type, **(details or {})})


class ValidationError(ParkingManagementException):
    """Exception raised for validation errors."""
    
    def __init__(self, field_errors: Dict[str, str]):
        super().__init__(ErrorCodes.VALIDATION_ERROR[0], None, {"field_errors": field_errors})


class PaymentError(ParkingManagementException):
    """Exception raised for payment errors."""
    
    def __init__(self, error_code: str = ErrorCodes.PAYMENT_FAILED[0], message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)


class ReservationError(ParkingManagementException):
    """Exception raised for reservation errors."""
    
    def __init__(self, error_code: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(error_code, message, details)


class RateLimitError(ParkingManagementException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int, message: Optional[str] = None):
        details = {"retry_after_seconds": retry_after}
        super().__init__(ErrorCodes.RATE_LIMIT_EXCEEDED[0], message, details)