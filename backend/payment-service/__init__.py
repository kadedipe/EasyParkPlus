"""
Payment Service for Parking Management System.
Handles all payment operations including processing, refunds, subscriptions, and webhooks.
"""

__version__ = "1.0.0"
__author__ = "Parking Management Team"
__description__ = "Microservice for handling all payment operations in the Parking Management System"

from typing import Dict, Any, Optional

# Import main components for easy access
from .core.config import settings
from .core.exceptions import (
    PaymentServiceError,
    PaymentGatewayError,
    PaymentValidationError,
    PaymentProcessingError,
    RefundError,
    SubscriptionError,
    WebhookError
)
from .gateways import (
    PaymentGateway,
    StripeGateway,
    PayPalGateway,
    RazorpayGateway,
    get_stripe_gateway,
    get_paypal_gateway,
    get_razorpay_gateway
)
from .services import (
    payment_service,
    subscription_service,
    invoice_service,
    dispute_service
)
from .webhooks import (
    WebhookHandler,
    StripeWebhookHandler,
    PayPalWebhookHandler,
    RazorpayWebhookHandler,
    get_webhook_handler,
    WebhookProcessor,
    get_webhook_processor,
    WebhookEvent,
    PaymentEvent,
    SubscriptionEvent,
    RefundEvent,
    CustomerEvent,
    DisputeEvent
)
from .models import (
    Payment,
    PaymentStatus,
    PaymentMethod,
    Subscription,
    SubscriptionStatus,
    Invoice,
    InvoiceStatus,
    Refund,
    Dispute
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
    "PaymentServiceError",
    "PaymentGatewayError",
    "PaymentValidationError",
    "PaymentProcessingError",
    "RefundError",
    "SubscriptionError",
    "WebhookError",
    
    # Gateways
    "PaymentGateway",
    "StripeGateway",
    "PayPalGateway",
    "RazorpayGateway",
    "get_stripe_gateway",
    "get_paypal_gateway",
    "get_razorpay_gateway",
    
    # Services
    "payment_service",
    "subscription_service",
    "invoice_service",
    "dispute_service",
    
    # Webhooks
    "WebhookHandler",
    "StripeWebhookHandler",
    "PayPalWebhookHandler",
    "RazorpayWebhookHandler",
    "get_webhook_handler",
    "WebhookProcessor",
    "get_webhook_processor",
    "WebhookEvent",
    "PaymentEvent",
    "SubscriptionEvent",
    "RefundEvent",
    "CustomerEvent",
    "DisputeEvent",
    
    # Models
    "Payment",
    "PaymentStatus",
    "PaymentMethod",
    "Subscription",
    "SubscriptionStatus",
    "Invoice",
    "InvoiceStatus",
    "Refund",
    "Dispute",
    
    # Utils
    "get_logger",
    "setup_logging"
]


# Package initialization
def initialize_service(config_overrides: Optional[Dict[str, Any]] = None) -> None:
    """
    Initialize the payment service with optional configuration overrides.
    
    Args:
        config_overrides: Dictionary of configuration overrides
    """
    # Setup logging
    setup_logging(
        app_name="payment-service",
        log_level=settings.LOG_LEVEL,
        json_format=settings.JSON_LOGS
    )
    
    logger = get_logger(__name__)
    logger.info(f"Initializing Payment Service v{__version__}")
    
    # Apply configuration overrides if provided
    if config_overrides:
        for key, value in config_overrides.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
                logger.debug(f"Applied config override: {key}={value}")
    
    logger.info("Payment Service initialized successfully")


def get_service_info() -> Dict[str, Any]:
    """
    Get service information.
    
    Returns:
        Dict[str, Any]: Service information
    """
    return {
        "name": "Payment Service",
        "version": __version__,
        "description": __description__,
        "environment": settings.ENVIRONMENT,
        "features": {
            "stripe": settings.ENABLE_STRIPE,
            "paypal": settings.ENABLE_PAYPAL,
            "razorpay": settings.ENABLE_RAZORPAY,
            "subscriptions": settings.ENABLE_SUBSCRIPTIONS,
            "invoicing": settings.ENABLE_INVOICING
        }
    }


# Export convenience functions
__all__.extend([
    "initialize_service",
    "get_service_info"
])