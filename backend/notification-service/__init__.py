"""
Notification Service for Parking Management System.
Handles all communications including email, SMS, and push notifications.
"""

__version__ = "1.0.0"
__author__ = "Parking Management Team"
__description__ = "Microservice for handling all notifications in the Parking Management System"

from typing import Dict, Any, Optional

# Import main components for easy access
from .core.config import settings
from .core.exceptions import (
    NotificationServiceError,
    ProviderError,
    TemplateError,
    ConsumerError,
    EmailDeliveryError,
    SMSDeliveryError,
    PushDeliveryError
)
from .consumers import (
    EmailConsumer,
    SMSConsumer,
    PushConsumer,
    AuditConsumer,
    BookingConsumer,
    PaymentConsumer
)
from .providers.email import (
    EmailProvider,
    SMTPProvider,
    SendGridProvider,
    AWSSESProvider,
    get_email_provider_manager
)
from .providers.sms import (
    SMSProvider,
    TwilioProvider,
    AWSSNSProvider,
    VonageProvider,
    get_sms_provider_manager
)
from .providers.push import (
    PushProvider,
    FCMProvider,
    WebPushProvider,
    get_push_provider_manager
)
from .templates import (
    TemplateEngine,
    TemplateManager,
    EmailTemplateRenderer,
    SMSTemplateRenderer,
    PushTemplateRenderer,
    get_template_manager
)
from .utils.logging_utils import get_logger, setup_logging

# Package metadata
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__description__",
    
    # Core
    "settings",
    
    # Exceptions
    "NotificationServiceError",
    "ProviderError",
    "TemplateError",
    "ConsumerError",
    "EmailDeliveryError",
    "SMSDeliveryError",
    "PushDeliveryError",
    
    # Consumers
    "EmailConsumer",
    "SMSConsumer",
    "PushConsumer",
    "AuditConsumer",
    "BookingConsumer",
    "PaymentConsumer",
    
    # Email providers
    "EmailProvider",
    "SMTPProvider",
    "SendGridProvider",
    "AWSSESProvider",
    "get_email_provider_manager",
    
    # SMS providers
    "SMSProvider",
    "TwilioProvider",
    "AWSSNSProvider",
    "VonageProvider",
    "get_sms_provider_manager",
    
    # Push providers
    "PushProvider",
    "FCMProvider",
    "WebPushProvider",
    "get_push_provider_manager",
    
    # Templates
    "TemplateEngine",
    "TemplateManager",
    "EmailTemplateRenderer",
    "SMSTemplateRenderer",
    "PushTemplateRenderer",
    "get_template_manager",
    
    # Utils
    "get_logger",
    "setup_logging"
]

# Package initialization
def initialize_service(config_overrides: Optional[Dict[str, Any]] = None) -> None:
    """
    Initialize the notification service with optional configuration overrides.
    
    Args:
        config_overrides: Dictionary of configuration overrides
    """
    # Setup logging
    setup_logging(
        app_name="notification-service",
        log_level=settings.LOG_LEVEL,
        json_format=settings.JSON_LOGS
    )
    
    logger = get_logger(__name__)
    logger.info(f"Initializing Notification Service v{__version__}")
    
    # Apply configuration overrides if provided
    if config_overrides:
        for key, value in config_overrides.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
                logger.debug(f"Applied config override: {key}={value}")
    
    # Initialize providers
    from .providers.email import initialize_email_providers
    from .providers.sms import initialize_sms_providers
    from .providers.push import initialize_push_providers
    
    initialize_email_providers()
    initialize_sms_providers()
    initialize_push_providers()
    
    # Initialize template manager
    get_template_manager()
    
    logger.info("Notification Service initialized successfully")


def get_service_info() -> Dict[str, Any]:
    """
    Get service information.
    
    Returns:
        Dict[str, Any]: Service information
    """
    return {
        "name": "Notification Service",
        "version": __version__,
        "description": __description__,
        "environment": settings.ENVIRONMENT,
        "features": {
            "email": settings.ENABLE_EMAIL,
            "sms": settings.ENABLE_SMS,
            "push": settings.ENABLE_PUSH,
            "audit": settings.ENABLE_AUDIT,
            "booking_notifications": settings.ENABLE_BOOKING_NOTIFICATIONS,
            "payment_notifications": settings.ENABLE_PAYMENT_NOTIFICATIONS,
            "user_notifications": settings.ENABLE_USER_NOTIFICATIONS
        },
        "providers": {
            "email": settings.EMAIL_PROVIDER,
            "sms": settings.SMS_PROVIDER,
            "push": settings.PUSH_PROVIDER
        }
    }


# Convenience functions for common operations
async def send_email(
    to: list,
    subject: str,
    template: str,
    context: dict,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to send an email.
    
    Args:
        to: List of recipient emails
        subject: Email subject
        template: Template name
        context: Template context
        **kwargs: Additional arguments
        
    Returns:
        Dict[str, Any]: Send result
    """
    from .api.notifications import send_email as send_email_api
    from fastapi import BackgroundTasks
    
    request = type('Request', (), {'headers': {}})()
    background_tasks = BackgroundTasks()
    
    email_request = {
        "to": to,
        "subject": subject,
        "template": template,
        "context": context,
        **kwargs
    }
    
    return await send_email_api(email_request, background_tasks, request)


async def send_sms(
    to: list,
    message: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to send an SMS.
    
    Args:
        to: List of recipient numbers
        message: SMS message
        **kwargs: Additional arguments
        
    Returns:
        Dict[str, Any]: Send result
    """
    from .api.notifications import send_sms as send_sms_api
    from fastapi import BackgroundTasks
    
    request = type('Request', (), {'headers': {}})()
    background_tasks = BackgroundTasks()
    
    sms_request = {
        "to": to,
        "message": message,
        **kwargs
    }
    
    return await send_sms_api(sms_request, background_tasks, request)


async def send_push(
    tokens: list,
    title: str,
    body: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to send a push notification.
    
    Args:
        tokens: List of device tokens
        title: Notification title
        body: Notification body
        **kwargs: Additional arguments
        
    Returns:
        Dict[str, Any]: Send result
    """
    from .api.notifications import send_push as send_push_api
    from fastapi import BackgroundTasks
    
    request = type('Request', (), {'headers': {}})()
    background_tasks = BackgroundTasks()
    
    push_request = {
        "tokens": tokens,
        "title": title,
        "body": body,
        **kwargs
    }
    
    return await send_push_api(push_request, background_tasks, request)


# Export convenience functions
__all__.extend([
    "initialize_service",
    "get_service_info",
    "send_email",
    "send_sms",
    "send_push"
])