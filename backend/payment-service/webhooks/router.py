"""
Webhook router for handling incoming webhooks from different payment gateways.
"""

from fastapi import APIRouter, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
import json

from ..core.config import settings
from ..core.exceptions import WebhookError
from ..utils.logging_utils import get_logger
from .handlers import get_webhook_handler
from .verification import verify_webhook_signature

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger(__name__)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature")
):
    """
    Handle Stripe webhook events.
    """
    try:
        # Get raw body
        payload = await request.body()
        
        # Verify signature
        if not verify_webhook_signature(
            "stripe",
            payload,
            stripe_signature,
            request.headers
        ):
            logger.warning("Invalid Stripe webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse payload
        event_data = json.loads(payload)
        
        # Get handler and process
        handler = get_webhook_handler("stripe")
        result = await handler.handle(event_data)
        
        logger.info(f"Stripe webhook processed: {event_data.get('type', 'unknown')}")
        
        return JSONResponse(
            status_code=200,
            content={"received": True, "processed": result}
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except WebhookError as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/paypal")
async def paypal_webhook(
    request: Request,
    paypal_auth_algo: Optional[str] = Header(None, alias="paypal-auth-algo"),
    paypal_cert_url: Optional[str] = Header(None, alias="paypal-cert-url"),
    paypal_transmission_id: Optional[str] = Header(None, alias="paypal-transmission-id"),
    paypal_transmission_sig: Optional[str] = Header(None, alias="paypal-transmission-sig"),
    paypal_transmission_time: Optional[str] = Header(None, alias="paypal-transmission-time")
):
    """
    Handle PayPal webhook events.
    """
    try:
        # Get raw body
        payload = await request.body()
        
        # Prepare headers for verification
        headers = {
            "paypal-auth-algo": paypal_auth_algo,
            "paypal-cert-url": paypal_cert_url,
            "paypal-transmission-id": paypal_transmission_id,
            "paypal-transmission-sig": paypal_transmission_sig,
            "paypal-transmission-time": paypal_transmission_time
        }
        
        # Verify signature
        if not verify_webhook_signature("paypal", payload, None, headers):
            logger.warning("Invalid PayPal webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse payload
        event_data = json.loads(payload)
        
        # Get handler and process
        handler = get_webhook_handler("paypal")
        result = await handler.handle(event_data)
        
        logger.info(f"PayPal webhook processed: {event_data.get('event_type', 'unknown')}")
        
        return JSONResponse(
            status_code=200,
            content={"received": True, "processed": result}
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except WebhookError as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="x-razorpay-signature")
):
    """
    Handle Razorpay webhook events.
    """
    try:
        # Get raw body
        payload = await request.body()
        
        # Verify signature
        if not verify_webhook_signature("razorpay", payload, x_razorpay_signature, request.headers):
            logger.warning("Invalid Razorpay webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse payload
        event_data = json.loads(payload)
        
        # Get handler and process
        handler = get_webhook_handler("razorpay")
        result = await handler.handle(event_data)
        
        logger.info(f"Razorpay webhook processed: {event_data.get('event', 'unknown')}")
        
        return JSONResponse(
            status_code=200,
            content={"received": True, "processed": result}
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except WebhookError as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/generic")
async def generic_webhook(
    request: Request,
    gateway: str,
    x_signature: Optional[str] = Header(None, alias="x-signature")
):
    """
    Generic webhook endpoint for other payment gateways.
    """
    try:
        # Get raw body
        payload = await request.body()
        
        # Verify signature if provided
        if x_signature:
            if not verify_webhook_signature(gateway, payload, x_signature, request.headers):
                logger.warning(f"Invalid {gateway} webhook signature")
                raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Parse payload
        event_data = json.loads(payload)
        
        # Get handler and process
        handler = get_webhook_handler(gateway)
        result = await handler.handle(event_data)
        
        logger.info(f"Generic webhook processed for {gateway}")
        
        return JSONResponse(
            status_code=200,
            content={"received": True, "processed": result}
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except WebhookError as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")