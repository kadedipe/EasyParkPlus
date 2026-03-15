"""
Webhook signature verification utilities.
"""

import hmac
import hashlib
import base64
from typing import Dict, Any, Optional, Union
from datetime import datetime

from ..core.config import settings
from ..utils.logging_utils import get_logger

logger = get_logger(__name__)


async def verify_webhook_signature(
    gateway: str,
    payload: Union[str, bytes],
    signature: Optional[str],
    headers: Dict[str, str]
) -> bool:
    """
    Verify webhook signature based on gateway.
    
    Args:
        gateway: Payment gateway name
        payload: Raw webhook payload
        signature: Signature header value
        headers: All request headers
        
    Returns:
        bool: True if signature is valid
    """
    if settings.ENVIRONMENT == "development":
        # Skip verification in development
        return True
    
    if gateway == "stripe":
        return verify_stripe_signature(payload, signature, headers)
    elif gateway == "paypal":
        return verify_paypal_signature(payload, headers)
    elif gateway == "razorpay":
        return verify_razorpay_signature(payload, signature)
    else:
        # For unknown gateways, verify with generic method
        return verify_generic_signature(payload, signature, gateway)


def verify_stripe_signature(
    payload: Union[str, bytes],
    signature: Optional[str],
    headers: Dict[str, str]
) -> bool:
    """
    Verify Stripe webhook signature.
    """
    if not signature or not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Missing Stripe signature or webhook secret")
        return False
    
    try:
        import stripe
        from stripe.error import SignatureVerificationError
        
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8')
        
        stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET
        )
        return True
        
    except SignatureVerificationError as e:
        logger.error(f"Stripe signature verification failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Stripe verification error: {e}")
        return False


def verify_paypal_signature(
    payload: Union[str, bytes],
    headers: Dict[str, str]
) -> bool:
    """
    Verify PayPal webhook signature.
    
    Note: PayPal signature verification requires an API call to their verification endpoint.
    This is a simplified version. In production, implement the full verification.
    """
    # Extract PayPal headers
    auth_algo = headers.get("paypal-auth-algo")
    cert_url = headers.get("paypal-cert-url")
    transmission_id = headers.get("paypal-transmission-id")
    transmission_sig = headers.get("paypal-transmission-sig")
    transmission_time = headers.get("paypal-transmission-time")
    
    if not all([auth_algo, cert_url, transmission_id, transmission_sig, transmission_time]):
        logger.warning("Missing PayPal webhook headers")
        return False
    
    # In production, you would:
    # 1. Download certificate from cert_url
    # 2. Verify signature using the certificate
    # 3. Check transmission time is within acceptable range
    
    # For now, return True in development
    logger.info("PayPal signature verification skipped (implement in production)")
    return True


def verify_razorpay_signature(
    payload: Union[str, bytes],
    signature: Optional[str]
) -> bool:
    """
    Verify Razorpay webhook signature.
    """
    if not signature or not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.warning("Missing Razorpay signature or webhook secret")
        return False
    
    try:
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8')
        
        # Generate expected signature
        expected_signature = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
        
    except Exception as e:
        logger.error(f"Razorpay signature verification failed: {e}")
        return False


def verify_generic_signature(
    payload: Union[str, bytes],
    signature: Optional[str],
    gateway: str
) -> bool:
    """
    Verify signature for generic gateways.
    """
    if not signature:
        logger.warning(f"No signature provided for {gateway}")
        return False
    
    # Get webhook secret for gateway
    secret = getattr(settings, f"{gateway.upper()}_WEBHOOK_SECRET", None)
    if not secret:
        logger.warning(f"No webhook secret configured for {gateway}")
        return False
    
    try:
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8')
        
        # Try HMAC-SHA256
        expected = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
        
    except Exception as e:
        logger.error(f"Generic signature verification failed: {e}")
        return False


def verify_timestamp(timestamp: Union[str, int], max_age: int = 300) -> bool:
    """
    Verify that webhook timestamp is not too old.
    
    Args:
        timestamp: Timestamp from webhook
        max_age: Maximum age in seconds
        
    Returns:
        bool: True if timestamp is valid
    """
    try:
        if isinstance(timestamp, str):
            # Parse ISO format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            ts = dt.timestamp()
        else:
            ts = timestamp
        
        now = datetime.utcnow().timestamp()
        return abs(now - ts) <= max_age
        
    except Exception as e:
        logger.error(f"Timestamp verification failed: {e}")
        return False