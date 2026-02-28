"""Payment gateway configuration."""

from typing import Dict, Any, List

from . import config


class PaymentConfig:
    """Payment processing configuration."""
    
    # Provider selection
    PRIMARY_PROVIDER: str = "stripe"  # stripe, paypal, etc.
    
    # Stripe settings
    STRIPE_API_KEY: str = config.STRIPE_API_KEY
    STRIPE_WEBHOOK_SECRET: str = config.STRIPE_WEBHOOK_SECRET
    STRIPE_API_VERSION: str = config.STRIPE_API_VERSION
    
    # PayPal settings
    PAYPAL_CLIENT_ID: str = config.PAYPAL_CLIENT_ID
    PAYPAL_CLIENT_SECRET: str = config.PAYPAL_CLIENT_SECRET
    PAYPAL_MODE: str = config.PAYPAL_MODE  # sandbox or live
    PAYPAL_API_URL: str = "https://api-m.paypal.com" if PAYPAL_MODE == "live" else "https://api-m.sandbox.paypal.com"
    
    # Currency settings
    CURRENCY: str = "USD"
    SUPPORTED_CURRENCIES: List[str] = ["USD", "EUR", "GBP", "CAD"]
    
    # Payment methods
    PAYMENT_METHODS: List[str] = [
        "credit_card",
        "debit_card",
        "paypal",
        "apple_pay",
        "google_pay",
    ]
    
    # Transaction settings
    TRANSACTION_TIMEOUT: int = 300  # 5 minutes
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY: int = 5  # seconds
    
    # Refund settings
    REFUND_WINDOW_DAYS: int = 30
    REFUND_REQUIRE_APPROVAL: bool = True
    
    # Webhook settings
    WEBHOOK_TOLERANCE: int = 300  # 5 minutes
    WEBHOOK_MAX_ATTEMPTS: int = 5
    
    # Fee settings
    SERVICE_FEE_PERCENT: float = 2.9  # 2.9%
    SERVICE_FEE_FIXED: float = 0.30  # $0.30
    MINIMUM_PAYMENT: float = 0.50
    MAXIMUM_PAYMENT: float = 10000.00
    
    # Payment status mapping
    STATUS_MAPPING: Dict[str, str] = {
        "succeeded": "paid",
        "paid": "paid",
        "pending": "pending",
        "requires_payment_method": "pending",
        "requires_confirmation": "pending",
        "requires_action": "pending",
        "processing": "processing",
        "failed": "failed",
        "requires_capture": "authorized",
        "canceled": "cancelled",
        "refunded": "refunded",
    }


payment_config = PaymentConfig()