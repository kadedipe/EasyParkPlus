"""
Core package initialization.
"""

from .config import settings
from .exceptions import (
    NotificationServiceError,
    ProviderError,
    TemplateError,
    ConsumerError
)

__all__ = [
    "settings",
    "NotificationServiceError",
    "ProviderError",
    "TemplateError",
    "ConsumerError"
]