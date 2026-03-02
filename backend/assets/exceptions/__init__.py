"""Exceptions package initialization."""

from .custom_exceptions import (
    ParkingManagementException,
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ResourceConflictError,
    ValidationError,
    PaymentError,
    ReservationError,
    RateLimitError,
)

__all__ = [
    'ParkingManagementException',
    'AuthenticationError',
    'AuthorizationError',
    'ResourceNotFoundError',
    'ResourceConflictError',
    'ValidationError',
    'PaymentError',
    'ReservationError',
    'RateLimitError',
]