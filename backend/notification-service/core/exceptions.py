"""
Custom exceptions for notification service.
"""

from typing import Optional, Any


class NotificationServiceError(Exception):
    """Base exception for notification service."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class ProviderError(NotificationServiceError):
    """Exception raised when a provider fails."""
    
    def __init__(self, provider: str, message: str, details: Optional[Any] = None):
        self.provider = provider
        super().__init__(f"Provider {provider} error: {message}", details)


class EmailProviderError(ProviderError):
    """Exception raised when email provider fails."""
    
    def __init__(self, provider: str, message: str, details: Optional[Any] = None):
        super().__init__(provider, f"Email provider error: {message}", details)


class SMSProviderError(ProviderError):
    """Exception raised when SMS provider fails."""
    
    def __init__(self, provider: str, message: str, details: Optional[Any] = None):
        super().__init__(provider, f"SMS provider error: {message}", details)


class PushProviderError(ProviderError):
    """Exception raised when push provider fails."""
    
    def __init__(self, provider: str, message: str, details: Optional[Any] = None):
        super().__init__(provider, f"Push provider error: {message}", details)


class TemplateError(NotificationServiceError):
    """Exception raised when template handling fails."""
    
    def __init__(self, template_name: str, message: str, details: Optional[Any] = None):
        self.template_name = template_name
        super().__init__(f"Template {template_name} error: {message}", details)


class ConsumerError(NotificationServiceError):
    """Exception raised when consumer fails."""
    
    def __init__(self, consumer: str, message: str, details: Optional[Any] = None):
        self.consumer = consumer
        super().__init__(f"Consumer {consumer} error: {message}", details)


class EmailDeliveryError(EmailProviderError):
    """Exception raised when email delivery fails."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__("email", message, details)


class SMSDeliveryError(SMSProviderError):
    """Exception raised when SMS delivery fails."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__("sms", message, details)


class PushDeliveryError(PushProviderError):
    """Exception raised when push delivery fails."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__("push", message, details)


class ConfigurationError(NotificationServiceError):
    """Exception raised when configuration is invalid."""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(f"Configuration error: {message}", details)


class RateLimitError(NotificationServiceError):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, provider: str, limit: int, reset_time: Optional[int] = None):
        self.provider = provider
        self.limit = limit
        self.reset_time = reset_time
        message = f"Rate limit exceeded for {provider}. Limit: {limit}"
        if reset_time:
            message += f", Resets in: {reset_time}s"
        super().__init__(message)