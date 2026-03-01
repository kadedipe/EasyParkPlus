"""Error code constants with messages."""

from typing import Dict, Tuple


class ErrorCodes:
    """Error code constants with HTTP status codes and messages."""
    
    # General errors
    UNKNOWN_ERROR = ("UNKNOWN_ERROR", 500, "An unknown error occurred")
    INTERNAL_ERROR = ("INTERNAL_ERROR", 500, "Internal server error")
    SERVICE_UNAVAILABLE = ("SERVICE_UNAVAILABLE", 503, "Service temporarily unavailable")
    
    # Auth errors
    AUTHENTICATION_ERROR = ("AUTHENTICATION_ERROR", 401, "Authentication failed")
    AUTHORIZATION_ERROR = ("AUTHORIZATION_ERROR", 403, "You don't have permission to perform this action")
    INVALID_CREDENTIALS = ("INVALID_CREDENTIALS", 401, "Invalid username or password")
    TOKEN_EXPIRED = ("TOKEN_EXPIRED", 401, "Token has expired")
    TOKEN_INVALID = ("TOKEN_INVALID", 401, "Invalid token")
    
    # Validation errors
    VALIDATION_ERROR = ("VALIDATION_ERROR", 400, "Validation error")
    INVALID_INPUT = ("INVALID_INPUT", 400, "Invalid input provided")
    MISSING_FIELD = ("MISSING_FIELD", 400, "Required field is missing")
    
    # Resource errors
    RESOURCE_NOT_FOUND = ("RESOURCE_NOT_FOUND", 404, "Resource not found")
    RESOURCE_CONFLICT = ("RESOURCE_CONFLICT", 409, "Resource conflict")
    RESOURCE_UNAVAILABLE = ("RESOURCE_UNAVAILABLE", 410, "Resource is no longer available")
    
    # Reservation errors
    RESERVATION_NOT_FOUND = ("RESERVATION_NOT_FOUND", 404, "Reservation not found")
    RESERVATION_CONFLICT = ("RESERVATION_CONFLICT", 409, "Reservation time conflict")
    RESERVATION_CANCELLATION_ERROR = ("RESERVATION_CANCELLATION_ERROR", 400, "Cannot cancel this reservation")
    RESERVATION_EXPIRED = ("RESERVATION_EXPIRED", 410, "Reservation has expired")
    
    # Payment errors
    PAYMENT_FAILED = ("PAYMENT_FAILED", 402, "Payment processing failed")
    PAYMENT_DECLINED = ("PAYMENT_DECLINED", 402, "Payment was declined")
    INSUFFICIENT_FUNDS = ("INSUFFICIENT_FUNDS", 402, "Insufficient funds")
    
    # Rate limit errors
    RATE_LIMIT_EXCEEDED = ("RATE_LIMIT_EXCEEDED", 429, "Rate limit exceeded")
    
    @classmethod
    def get_error_info(cls, error_code: str) -> Tuple[str, int, str]:
        """Get error information by error code."""
        for attr_name in dir(cls):
            if attr_name.startswith('__'):
                continue
            attr_value = getattr(cls, attr_name)
            if isinstance(attr_value, tuple) and attr_value[0] == error_code:
                return attr_value
        return cls.UNKNOWN_ERROR
    
    @classmethod
    def get_http_status(cls, error_code: str) -> int:
        """Get HTTP status code for error code."""
        return cls.get_error_info(error_code)[1]
    
    @classmethod
    def get_message(cls, error_code: str) -> str:
        """Get message for error code."""
        return cls.get_error_info(error_code)[2]