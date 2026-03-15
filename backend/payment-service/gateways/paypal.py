"""
PayPal payment gateway integration.
Handles all PayPal-specific payment operations including payments, refunds, subscriptions, and webhooks.
"""

import asyncio
import json
import base64
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum

import aiohttp
from aiohttp import BasicAuth

from ..core.config import settings
from ..core.exceptions import (
    PaymentGatewayError,
    PaymentValidationError,
    PaymentProcessingError,
    RefundError,
    WebhookError
)
from ..utils.logging_utils import get_logger
from ..utils.retry import async_retry


class PayPalEnvironment(str, Enum):
    """PayPal environment."""
    SANDBOX = "sandbox"
    LIVE = "live"


class PayPalIntent(str, Enum):
    """PayPal payment intent."""
    CAPTURE = "CAPTURE"
    AUTHORIZE = "AUTHORIZE"


class PayPalLandingPage(str, Enum):
    """PayPal landing page type."""
    LOGIN = "LOGIN"
    BILLING = "BILLING"
    NO_PREFERENCE = "NO_PREFERENCE"


class PayPalPaymentStatus(str, Enum):
    """PayPal payment status."""
    CREATED = "CREATED"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    VOIDED = "VOIDED"
    PENDING = "PENDING"
    PAYER_ACTION_REQUIRED = "PAYER_ACTION_REQUIRED"


class PayPalGateway:
    """
    PayPal payment gateway implementation.
    """
    
    def __init__(self):
        """Initialize PayPal gateway."""
        self.logger = get_logger(__name__)
        
        # Set environment
        self.environment = settings.PAYPAL_ENVIRONMENT
        self.client_id = settings.PAYPAL_CLIENT_ID
        self.client_secret = settings.PAYPAL_CLIENT_SECRET
        self.webhook_id = settings.PAYPAL_WEBHOOK_ID
        
        # Set API endpoints
        if self.environment == PayPalEnvironment.SANDBOX:
            self.api_base = "https://api-m.sandbox.paypal.com"
        else:
            self.api_base = "https://api-m.paypal.com"
        
        self.auth_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        # Metrics
        self.stats = {
            "payments_processed": 0,
            "payments_succeeded": 0,
            "payments_failed": 0,
            "refunds_processed": 0,
            "refunds_succeeded": 0,
            "subscriptions_created": 0,
            "subscriptions_canceled": 0,
            "webhooks_received": 0,
            "api_calls": 0,
            "api_errors": 0,
            "total_amount": 0,
            "total_fees": 0
        }
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        self.logger.info(f"PayPal gateway initialized in {self.environment} mode")
    
    async def ensure_session(self) -> None:
        """Ensure HTTP session exists."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self) -> None:
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def get_access_token(self) -> str:
        """
        Get PayPal access token.
        
        Returns:
            str: Access token
            
        Raises:
            PaymentGatewayError: If token retrieval fails
        """
        # Return cached token if still valid
        if self.auth_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return self.auth_token
        
        try:
            await self.ensure_session()
            self.stats["api_calls"] += 1
            
            # Prepare authentication
            auth = BasicAuth(self.client_id, self.client_secret)
            
            # Prepare request
            url = f"{self.api_base}/v1/oauth2/token"
            data = {"grant_type": "client_credentials"}
            
            # Make request
            async with self.session.post(
                url,
                data=data,
                auth=auth
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    self.auth_token = result["access_token"]
                    expires_in = result.get("expires_in", 3600)
                    self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)  # Buffer 60 seconds
                    
                    self.logger.debug("Access token obtained successfully")
                    return self.auth_token
                else:
                    error_text = await response.text()
                    self.logger.error(f"Failed to get access token: {response.status} - {error_text}")
                    raise PaymentGatewayError(f"Authentication failed: {response.status}")
                    
        except Exception as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to get access token: {e}")
            raise PaymentGatewayError(f"Authentication failed: {e}")
    
    async def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to PayPal API.
        
        Args:
            method: HTTP method
            path: API path
            data: Request data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            Dict[str, Any]: Response data
        """
        await self.ensure_session()
        self.stats["api_calls"] += 1
        
        # Get access token
        token = await self.get_access_token()
        
        # Prepare headers
        request_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "PayPal-Request-Id": self._generate_idempotency_key()
        }
        
        if headers:
            request_headers.update(headers)
        
        # Prepare URL
        url = f"{self.api_base}{path}"
        
        # Make request
        async with self.session.request(
            method=method,
            url=url,
            json=data,
            params=params,
            headers=request_headers
        ) as response:
            response_data = await response.json() if response.content else {}
            
            if response.status in [200, 201, 202, 204]:
                return response_data
            else:
                self.stats["api_errors"] += 1
                error_message = self._extract_error_message(response_data)
                self.logger.error(f"PayPal API error: {response.status} - {error_message}")
                
                if response.status == 400:
                    raise PaymentValidationError(error_message)
                elif response.status == 401:
                    # Token expired, force refresh next time
                    self.auth_token = None
                    raise PaymentGatewayError("Authentication expired")
                elif response.status == 404:
                    raise PaymentValidationError("Resource not found")
                elif response.status == 422:
                    raise PaymentValidationError(f"Validation error: {error_message}")
                elif response.status == 429:
                    raise PaymentGatewayError("Rate limit exceeded")
                else:
                    raise PaymentGatewayError(f"PayPal API error: {error_message}")
    
    def _generate_idempotency_key(self) -> str:
        """Generate idempotency key."""
        import uuid
        return str(uuid.uuid4())
    
    def _extract_error_message(self, response_data: Dict[str, Any]) -> str:
        """Extract error message from response."""
        if "error_description" in response_data:
            return response_data["error_description"]
        elif "error" in response_data:
            if isinstance(response_data["error"], dict):
                return response_data["error"].get("message", str(response_data["error"]))
            return str(response_data["error"])
        elif "message" in response_data:
            return response_data["message"]
        elif "details" in response_data and response_data["details"]:
            return response_data["details"][0].get("description", json.dumps(response_data))
        else:
            return json.dumps(response_data)
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_order(
        self,
        amount: float,
        currency: str = "USD",
        intent: str = "CAPTURE",
        description: Optional[str] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        reference_id: Optional[str] = None,
        payment_method: str = "paypal",
        shipping_preference: str = "NO_SHIPPING",
        user_action: str = "PAY_NOW",
        landing_page: str = "NO_PREFERENCE",
        metadata: Optional[Dict[str, Any]] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a PayPal order.
        
        Args:
            amount: Amount to charge
            currency: Currency code (USD, EUR, GBP, etc.)
            intent: CAPTURE or AUTHORIZE
            description: Order description
            return_url: URL after successful payment
            cancel_url: URL after cancelled payment
            reference_id: Merchant reference ID
            payment_method: Payment method (paypal, card, etc.)
            shipping_preference: Shipping preference
            user_action: PAY_NOW or CONTINUE
            landing_page: Landing page type
            metadata: Additional metadata
            items: Line items
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Order response
        """
        try:
            # Convert amount to string with 2 decimals
            amount_str = f"{amount:.2f}"
            
            # Prepare purchase units
            purchase_units = [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": amount_str
                    }
                }
            ]
            
            # Add reference ID if provided
            if reference_id:
                purchase_units[0]["reference_id"] = reference_id
            
            # Add description if provided
            if description:
                purchase_units[0]["description"] = description[:127]  # PayPal limit
            
            # Add items if provided
            if items:
                purchase_units[0]["items"] = [
                    {
                        "name": item["name"][:127],
                        "unit_amount": {
                            "currency_code": currency,
                            "value": f"{item['unit_amount']:.2f}"
                        },
                        "quantity": str(item["quantity"]),
                        "description": item.get("description", "")[:127],
                        "sku": item.get("sku", "")[:127]
                    }
                    for item in items
                ]
                
                # Calculate breakdown
                item_total = sum(item["unit_amount"] * item["quantity"] for item in items)
                purchase_units[0]["amount"]["breakdown"] = {
                    "item_total": {
                        "currency_code": currency,
                        "value": f"{item_total:.2f}"
                    }
                }
            
            # Add custom metadata
            if metadata:
                purchase_units[0]["custom_id"] = json.dumps(metadata)[:127]
            
            # Prepare application context
            application_context = {
                "return_url": return_url or f"{settings.FRONTEND_URL}/payment/success",
                "cancel_url": cancel_url or f"{settings.FRONTEND_URL}/payment/cancel",
                "brand_name": settings.APP_NAME[:127],
                "landing_page": landing_page,
                "shipping_preference": shipping_preference,
                "user_action": user_action,
                "payment_method": {
                    "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED" if intent == "CAPTURE" else "UNRESTRICTED",
                    "payer_selected": payment_method
                }
            }
            
            # Prepare order data
            order_data = {
                "intent": intent,
                "purchase_units": purchase_units,
                "application_context": application_context
            }
            
            # Add payer info if payment method is card
            if payment_method == "card" and "card" in kwargs:
                order_data["payer"] = {
                    "payment_method": "PAYPAL",
                    "funding_instruments": [{
                        "credit_card": kwargs["card"]
                    }]
                }
            
            # Make request
            response = await self._make_request(
                "POST",
                "/v2/checkout/orders",
                data=order_data
            )
            
            self.stats["payments_processed"] += 1
            self.stats["total_amount"] += amount
            
            self.logger.info(
                f"Order created: {response['id']}, "
                f"amount: {amount} {currency}, "
                f"intent: {intent}"
            )
            
            return self._format_order(response)
            
        except Exception as e:
            self.stats["payments_failed"] += 1
            self.logger.error(f"Failed to create order: {e}")
            raise
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def capture_order(
        self,
        order_id: str,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        final_capture: bool = True
    ) -> Dict[str, Any]:
        """
        Capture payment for an order.
        
        Args:
            order_id: Order ID
            amount: Amount to capture (if partial)
            currency: Currency code
            final_capture: Whether this is the final capture
            
        Returns:
            Dict[str, Any]: Capture response
        """
        try:
            # Prepare capture data
            capture_data = {}
            
            if amount:
                capture_data = {
                    "amount": {
                        "currency_code": currency or "USD",
                        "value": f"{amount:.2f}"
                    },
                    "final_capture": final_capture
                }
            
            # Make request
            response = await self._make_request(
                "POST",
                f"/v2/checkout/orders/{order_id}/capture",
                data=capture_data
            )
            
            self.logger.info(f"Order captured: {order_id}")
            self.stats["payments_succeeded"] += 1
            
            return self._format_capture(response)
            
        except Exception as e:
            self.logger.error(f"Failed to capture order: {e}")
            raise PaymentProcessingError(f"Capture failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def authorize_order(
        self,
        order_id: str
    ) -> Dict[str, Any]:
        """
        Authorize payment for an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Dict[str, Any]: Authorization response
        """
        try:
            response = await self._make_request(
                "POST",
                f"/v2/checkout/orders/{order_id}/authorize"
            )
            
            self.logger.info(f"Order authorized: {order_id}")
            
            return self._format_authorization(response)
            
        except Exception as e:
            self.logger.error(f"Failed to authorize order: {e}")
            raise PaymentProcessingError(f"Authorization failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def void_order(
        self,
        order_id: str
    ) -> Dict[str, Any]:
        """
        Void an authorized order.
        
        Args:
            order_id: Order ID
            
        Returns:
            Dict[str, Any]: Void response
        """
        try:
            response = await self._make_request(
                "POST",
                f"/v2/checkout/orders/{order_id}/void"
            )
            
            self.logger.info(f"Order voided: {order_id}")
            
            return {"order_id": order_id, "status": "VOIDED"}
            
        except Exception as e:
            self.logger.error(f"Failed to void order: {e}")
            raise PaymentProcessingError(f"Void failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def get_order(
        self,
        order_id: str
    ) -> Dict[str, Any]:
        """
        Get order details.
        
        Args:
            order_id: Order ID
            
        Returns:
            Dict[str, Any]: Order details
        """
        try:
            response = await self._make_request(
                "GET",
                f"/v2/checkout/orders/{order_id}"
            )
            
            return self._format_order(response)
            
        except Exception as e:
            self.logger.error(f"Failed to get order: {e}")
            raise PaymentGatewayError(f"Order retrieval failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_refund(
        self,
        capture_id: str,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        reason: Optional[str] = None,
        invoice_number: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a refund.
        
        Args:
            capture_id: Capture ID to refund
            amount: Amount to refund (full if None)
            currency: Currency code
            reason: Refund reason
            invoice_number: Invoice number
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: Refund response
        """
        try:
            self.stats["api_calls"] += 1
            
            # Prepare refund data
            refund_data = {}
            
            if amount:
                refund_data["amount"] = {
                    "currency_code": currency or "USD",
                    "value": f"{amount:.2f}"
                }
            
            if reason:
                refund_data["note_to_payer"] = reason[:255]
            
            if invoice_number:
                refund_data["invoice_id"] = invoice_number
            
            if metadata:
                refund_data["custom_id"] = json.dumps(metadata)[:127]
            
            # Make request
            response = await self._make_request(
                "POST",
                f"/v2/payments/captures/{capture_id}/refund",
                data=refund_data
            )
            
            self.logger.info(f"Refund created for capture: {capture_id}")
            
            self.stats["refunds_processed"] += 1
            self.stats["refunds_succeeded"] += 1
            
            return self._format_refund(response)
            
        except Exception as e:
            self.stats["refunds_processed"] += 1
            self.logger.error(f"Failed to create refund: {e}")
            raise RefundError(f"Refund failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def get_refund(
        self,
        refund_id: str
    ) -> Dict[str, Any]:
        """
        Get refund details.
        
        Args:
            refund_id: Refund ID
            
        Returns:
            Dict[str, Any]: Refund details
        """
        try:
            response = await self._make_request(
                "GET",
                f"/v2/payments/refunds/{refund_id}"
            )
            
            return self._format_refund(response)
            
        except Exception as e:
            self.logger.error(f"Failed to get refund: {e}")
            raise PaymentGatewayError(f"Refund retrieval failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_payout(
        self,
        recipient_email: str,
        amount: float,
        currency: str = "USD",
        note: Optional[str] = None,
        sender_batch_id: Optional[str] = None,
        recipient_type: str = "EMAIL",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a payout to a PayPal account.
        
        Args:
            recipient_email: Recipient PayPal email
            amount: Amount to send
            currency: Currency code
            note: Note to recipient
            sender_batch_id: Sender batch ID
            recipient_type: Recipient type (EMAIL, PHONE, PAYPAL_ID)
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: Payout response
        """
        try:
            self.stats["api_calls"] += 1
            
            # Prepare payout data
            payout_data = {
                "sender_batch_header": {
                    "sender_batch_id": sender_batch_id or self._generate_idempotency_key(),
                    "email_subject": note or "Payment from Parking Management",
                    "email_message": note or "You have received a payment"
                },
                "items": [
                    {
                        "recipient_type": recipient_type,
                        "amount": {
                            "currency": currency,
                            "value": f"{amount:.2f}"
                        },
                        "receiver": recipient_email,
                        "note": note or "Payment from Parking Management"
                    }
                ]
            }
            
            if metadata:
                payout_data["items"][0]["custom"] = json.dumps(metadata)
            
            # Make request
            response = await self._make_request(
                "POST",
                "/v1/payments/payouts",
                data=payout_data
            )
            
            self.logger.info(f"Payout created: {response['batch_header']['payout_batch_id']}")
            
            return {
                "batch_id": response["batch_header"]["payout_batch_id"],
                "batch_status": response["batch_header"]["batch_status"],
                "sender_batch_id": response["batch_header"]["sender_batch_id"],
                "amount": amount,
                "currency": currency,
                "recipient": recipient_email,
                "links": response.get("links", [])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create payout: {e}")
            raise PaymentGatewayError(f"Payout failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_billing_plan(
        self,
        name: str,
        description: str,
        amount: float,
        currency: str = "USD",
        frequency: str = "MONTH",
        frequency_interval: int = 1,
        cycles: int = 0,
        trial_days: Optional[int] = None,
        trial_amount: Optional[float] = None,
        setup_fee: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a billing plan for subscriptions.
        
        Args:
            name: Plan name
            description: Plan description
            amount: Payment amount
            currency: Currency code
            frequency: Frequency (DAY, WEEK, MONTH, YEAR)
            frequency_interval: Frequency interval
            cycles: Number of cycles (0 for infinite)
            trial_days: Trial period in days
            trial_amount: Trial amount (0 for free trial)
            setup_fee: One-time setup fee
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: Billing plan
        """
        try:
            self.stats["api_calls"] += 1
            
            # Prepare payment definitions
            payment_definitions = [
                {
                    "name": "Regular Payment",
                    "type": "REGULAR",
                    "frequency": frequency,
                    "frequency_interval": frequency_interval,
                    "amount": {
                        "currency": currency,
                        "value": f"{amount:.2f}"
                    },
                    "cycles": str(cycles) if cycles > 0 else "0"
                }
            ]
            
            # Add trial if specified
            if trial_days:
                payment_definitions.insert(0, {
                    "name": "Trial Period",
                    "type": "TRIAL",
                    "frequency": "DAY",
                    "frequency_interval": 1,
                    "amount": {
                        "currency": currency,
                        "value": f"{(trial_amount or 0):.2f}"
                    },
                    "cycles": str(trial_days)
                })
            
            # Prepare plan data
            plan_data = {
                "name": name[:127],
                "description": description[:127],
                "type": "INFINITE" if cycles == 0 else "FIXED",
                "payment_definitions": payment_definitions,
                "merchant_preferences": {
                    "setup_fee": {
                        "currency": currency,
                        "value": f"{(setup_fee or 0):.2f}"
                    },
                    "max_fail_attempts": "3",
                    "return_url": f"{settings.FRONTEND_URL}/subscription/success",
                    "cancel_url": f"{settings.FRONTEND_URL}/subscription/cancel",
                    "auto_bill_amount": "YES",
                    "initial_fail_amount_action": "CONTINUE"
                }
            }
            
            if metadata:
                plan_data["merchant_preferences"]["custom"] = json.dumps(metadata)
            
            # Make request
            response = await self._make_request(
                "POST",
                "/v1/payments/billing-plans",
                data=plan_data
            )
            
            # Activate the plan
            await self._make_request(
                "PATCH",
                f"/v1/payments/billing-plans/{response['id']}",
                data=[
                    {
                        "op": "replace",
                        "path": "/state",
                        "value": "ACTIVE"
                    }
                ]
            )
            
            self.logger.info(f"Billing plan created: {response['id']}")
            
            return self._format_billing_plan(response)
            
        except Exception as e:
            self.logger.error(f"Failed to create billing plan: {e}")
            raise PaymentGatewayError(f"Billing plan creation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_subscription(
        self,
        plan_id: str,
        subscriber_email: str,
        subscriber_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        quantity: int = 1,
        shipping_address: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a subscription.
        
        Args:
            plan_id: Billing plan ID
            subscriber_email: Subscriber email
            subscriber_name: Subscriber name
            start_time: Subscription start time
            quantity: Quantity
            shipping_address: Shipping address
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: Subscription details
        """
        try:
            self.stats["api_calls"] += 1
            
            # Prepare subscriber data
            subscriber = {
                "email": subscriber_email
            }
            
            if subscriber_name:
                subscriber["name"] = {"given_name": subscriber_name}
            
            # Prepare subscription data
            subscription_data = {
                "plan_id": plan_id,
                "subscriber": subscriber,
                "quantity": quantity,
                "application_context": {
                    "brand_name": settings.APP_NAME[:127],
                    "locale": "en-US",
                    "shipping_preference": "NO_SHIPPING" if not shipping_address else "SET_PROVIDED_ADDRESS",
                    "user_action": "SUBSCRIBE_NOW",
                    "return_url": f"{settings.FRONTEND_URL}/subscription/success",
                    "cancel_url": f"{settings.FRONTEND_URL}/subscription/cancel"
                }
            }
            
            if start_time:
                subscription_data["start_time"] = start_time.isoformat()
            
            if shipping_address:
                subscription_data["shipping"] = {
                    "name": {"full_name": shipping_address.get("name", subscriber_name or "Customer")},
                    "address": {
                        "address_line_1": shipping_address["line1"],
                        "address_line_2": shipping_address.get("line2", ""),
                        "admin_area_2": shipping_address["city"],
                        "admin_area_1": shipping_address.get("state", ""),
                        "postal_code": shipping_address["postal_code"],
                        "country_code": shipping_address["country"]
                    }
                }
            
            if metadata:
                subscription_data["custom_id"] = json.dumps(metadata)[:127]
            
            # Make request
            response = await self._make_request(
                "POST",
                "/v1/billing/subscriptions",
                data=subscription_data
            )
            
            self.stats["subscriptions_created"] += 1
            
            self.logger.info(f"Subscription created: {response['id']}")
            
            return self._format_subscription(response)
            
        except Exception as e:
            self.logger.error(f"Failed to create subscription: {e}")
            raise PaymentGatewayError(f"Subscription creation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def get_subscription(
        self,
        subscription_id: str
    ) -> Dict[str, Any]:
        """
        Get subscription details.
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            Dict[str, Any]: Subscription details
        """
        try:
            response = await self._make_request(
                "GET",
                f"/v1/billing/subscriptions/{subscription_id}"
            )
            
            return self._format_subscription(response)
            
        except Exception as e:
            self.logger.error(f"Failed to get subscription: {e}")
            raise PaymentGatewayError(f"Subscription retrieval failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def cancel_subscription(
        self,
        subscription_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription ID
            reason: Cancellation reason
            
        Returns:
            Dict[str, Any]: Cancellation response
        """
        try:
            cancel_data = {}
            if reason:
                cancel_data["reason"] = reason
            
            await self._make_request(
                "POST",
                f"/v1/billing/subscriptions/{subscription_id}/cancel",
                data=cancel_data
            )
            
            self.stats["subscriptions_canceled"] += 1
            
            self.logger.info(f"Subscription canceled: {subscription_id}")
            
            return {
                "subscription_id": subscription_id,
                "status": "CANCELED",
                "reason": reason
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cancel subscription: {e}")
            raise PaymentGatewayError(f"Subscription cancellation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def activate_subscription(
        self,
        subscription_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Activate a suspended subscription.
        
        Args:
            subscription_id: Subscription ID
            reason: Activation reason
            
        Returns:
            Dict[str, Any]: Activation response
        """
        try:
            activate_data = {}
            if reason:
                activate_data["reason"] = reason
            
            await self._make_request(
                "POST",
                f"/v1/billing/subscriptions/{subscription_id}/activate",
                data=activate_data
            )
            
            self.logger.info(f"Subscription activated: {subscription_id}")
            
            return {
                "subscription_id": subscription_id,
                "status": "ACTIVE",
                "reason": reason
            }
            
        except Exception as e:
            self.logger.error(f"Failed to activate subscription: {e}")
            raise PaymentGatewayError(f"Subscription activation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def suspend_subscription(
        self,
        subscription_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suspend a subscription.
        
        Args:
            subscription_id: Subscription ID
            reason: Suspension reason
            
        Returns:
            Dict[str, Any]: Suspension response
        """
        try:
            suspend_data = {}
            if reason:
                suspend_data["reason"] = reason
            
            await self._make_request(
                "POST",
                f"/v1/billing/subscriptions/{subscription_id}/suspend",
                data=suspend_data
            )
            
            self.logger.info(f"Subscription suspended: {subscription_id}")
            
            return {
                "subscription_id": subscription_id,
                "status": "SUSPENDED",
                "reason": reason
            }
            
        except Exception as e:
            self.logger.error(f"Failed to suspend subscription: {e}")
            raise PaymentGatewayError(f"Subscription suspension failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def list_transactions(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        page_size: int = 100,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """
        List transactions.
        
        Args:
            start_date: Start date
            end_date: End date
            page_size: Page size
            page: Page number
            
        Returns:
            List[Dict[str, Any]]: List of transactions
        """
        try:
            params = {
                "start_date": start_date.isoformat(),
                "page_size": page_size,
                "page": page
            }
            
            if end_date:
                params["end_date"] = end_date.isoformat()
            
            response = await self._make_request(
                "GET",
                "/v1/reporting/transactions",
                params=params
            )
            
            return [
                {
                    "id": t["transaction_info"]["transaction_id"],
                    "amount": float(t["transaction_info"]["transaction_amount"]["value"]),
                    "currency": t["transaction_info"]["transaction_amount"]["currency_code"],
                    "status": t["transaction_info"]["transaction_status"],
                    "type": t["transaction_info"]["transaction_event_code"],
                    "time": t["transaction_info"]["transaction_initiation_date"],
                    "payer": t.get("payer_info", {}).get("email_address"),
                    "payee": t.get("payee_info", {}).get("email_address")
                }
                for t in response.get("transaction_details", [])
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to list transactions: {e}")
            raise PaymentGatewayError(f"Transaction listing failed: {e}")
    
    def handle_webhook(
        self,
        payload: Union[str, bytes],
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Handle PayPal webhook.
        
        Args:
            payload: Webhook payload
            headers: Webhook headers
            
        Returns:
            Dict[str, Any]: Processed webhook event
            
        Raises:
            WebhookError: If webhook verification fails
        """
        try:
            self.stats["webhooks_received"] += 1
            
            # Parse payload
            if isinstance(payload, (bytes, str)):
                if isinstance(payload, bytes):
                    payload = payload.decode('utf-8')
                event_data = json.loads(payload)
            else:
                event_data = payload
            
            # Verify webhook signature
            if not self._verify_webhook_signature(payload, headers):
                raise WebhookError("Invalid webhook signature")
            
            self.logger.info(f"Webhook received: {event_data['event_type']}")
            
            # Process event based on type
            result = self._process_webhook_event(event_data)
            
            return {
                "event_id": event_data["id"],
                "event_type": event_data["event_type"],
                "processed": True,
                "data": result
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid webhook payload: {e}")
            raise WebhookError("Invalid webhook payload")
            
        except Exception as e:
            self.logger.error(f"Webhook processing error: {e}")
            raise WebhookError(f"Webhook processing failed: {e}")
    
    def _verify_webhook_signature(
        self,
        payload: Union[str, bytes],
        headers: Dict[str, str]
    ) -> bool:
        """
        Verify PayPal webhook signature.
        
        Args:
            payload: Webhook payload
            headers: Webhook headers
            
        Returns:
            bool: True if signature is valid
        """
        # In production, implement PayPal webhook verification
        # This requires the webhook ID and making an API call to verify
        # For now, return True in development
        if settings.ENVIRONMENT == "development":
            return True
        
        # TODO: Implement proper webhook verification
        return True
    
    def _process_webhook_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook event.
        
        Args:
            event_data: Webhook event data
            
        Returns:
            Dict[str, Any]: Processed event data
        """
        event_type = event_data["event_type"]
        resource = event_data.get("resource", {})
        
        # Handle payment events
        if event_type.startswith("PAYMENT."):
            return self._process_payment_event(event_type, resource)
        
        # Handle checkout events
        elif event_type.startswith("CHECKOUT."):
            return self._process_checkout_event(event_type, resource)
        
        # Handle billing/subscription events
        elif event_type.startswith("BILLING."):
            return self._process_billing_event(event_type, resource)
        
        # Handle customer dispute events
        elif event_type.startswith("CUSTOMER."):
            return self._process_customer_event(event_type, resource)
        
        # Handle risk events
        elif event_type.startswith("RISK."):
            return self._process_risk_event(event_type, resource)
        
        else:
            return {"event": event_type, "data": resource}
    
    def _process_payment_event(
        self,
        event_type: str,
        resource: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process payment events."""
        result = {
            "payment_id": resource.get("id"),
            "status": resource.get("status"),
            "amount": float(resource.get("amount", {}).get("value", 0)),
            "currency": resource.get("amount", {}).get("currency_code")
        }
        
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            self.stats["payments_succeeded"] += 1
            result["message"] = "Payment completed"
        elif event_type == "PAYMENT.CAPTURE.DENIED":
            self.stats["payments_failed"] += 1
            result["message"] = "Payment denied"
        elif event_type == "PAYMENT.CAPTURE.REFUNDED":
            result["message"] = "Payment refunded"
        elif event_type == "PAYMENT.CAPTURE.REVERSED":
            result["message"] = "Payment reversed"
        
        return result
    
    def _process_checkout_event(
        self,
        event_type: str,
        resource: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process checkout events."""
        return {
            "order_id": resource.get("id"),
            "status": resource.get("status"),
            "intent": resource.get("intent"),
            "payer_email": resource.get("payer", {}).get("email_address")
        }
    
    def _process_billing_event(
        self,
        event_type: str,
        resource: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process billing/subscription events."""
        return {
            "subscription_id": resource.get("id"),
            "status": resource.get("status"),
            "plan_id": resource.get("plan_id"),
            "subscriber_email": resource.get("subscriber", {}).get("email_address"),
            "next_billing_time": resource.get("billing_info", {}).get("next_billing_time")
        }
    
    def _process_customer_event(
        self,
        event_type: str,
        resource: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process customer dispute events."""
        return {
            "dispute_id": resource.get("dispute_id"),
            "reason": resource.get("reason"),
            "status": resource.get("status"),
            "amount": float(resource.get("dispute_amount", {}).get("value", 0)),
            "currency": resource.get("dispute_amount", {}).get("currency_code")
        }
    
    def _process_risk_event(
        self,
        event_type: str,
        resource: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process risk events."""
        return {
            "fraud_assessment": resource.get("fraud_assessment"),
            "risk_score": resource.get("risk_score")
        }
    
    def _format_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Format order for response."""
        purchase_unit = order.get("purchase_units", [{}])[0]
        amount = purchase_unit.get("amount", {})
        
        return {
            "id": order["id"],
            "status": order["status"],
            "intent": order["intent"],
            "amount": float(amount.get("value", 0)),
            "currency": amount.get("currency_code"),
            "description": purchase_unit.get("description"),
            "reference_id": purchase_unit.get("reference_id"),
            "custom_id": purchase_unit.get("custom_id"),
            "invoice_id": purchase_unit.get("invoice_id"),
            "create_time": order.get("create_time"),
            "update_time": order.get("update_time"),
            "payer": order.get("payer", {}),
            "links": [
                {
                    "href": link["href"],
                    "rel": link["rel"],
                    "method": link["method"]
                }
                for link in order.get("links", [])
            ]
        }
    
    def _format_capture(self, capture: Dict[str, Any]) -> Dict[str, Any]:
        """Format capture for response."""
        return {
            "id": capture["id"],
            "status": capture["status"],
            "amount": float(capture["amount"]["value"]),
            "currency": capture["amount"]["currency_code"],
            "final_capture": capture.get("final_capture", True),
            "create_time": capture.get("create_time"),
            "update_time": capture.get("update_time"),
            "custom_id": capture.get("custom_id"),
            "invoice_id": capture.get("invoice_id"),
            "links": capture.get("links", [])
        }
    
    def _format_authorization(self, authorization: Dict[str, Any]) -> Dict[str, Any]:
        """Format authorization for response."""
        return {
            "id": authorization["id"],
            "status": authorization["status"],
            "amount": float(authorization["amount"]["value"]),
            "currency": authorization["amount"]["currency_code"],
            "expiration_time": authorization.get("expiration_time"),
            "create_time": authorization.get("create_time"),
            "update_time": authorization.get("update_time"),
            "custom_id": authorization.get("custom_id"),
            "invoice_id": authorization.get("invoice_id"),
            "links": authorization.get("links", [])
        }
    
    def _format_refund(self, refund: Dict[str, Any]) -> Dict[str, Any]:
        """Format refund for response."""
        return {
            "id": refund["id"],
            "status": refund["status"],
            "amount": float(refund["amount"]["value"]),
            "currency": refund["amount"]["currency_code"],
            "note_to_payer": refund.get("note_to_payer"),
            "invoice_id": refund.get("invoice_id"),
            "custom_id": refund.get("custom_id"),
            "create_time": refund.get("create_time"),
            "update_time": refund.get("update_time"),
            "links": refund.get("links", [])
        }
    
    def _format_billing_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Format billing plan for response."""
        return {
            "id": plan["id"],
            "name": plan["name"],
            "description": plan.get("description"),
            "state": plan.get("state"),
            "type": plan.get("type"),
            "create_time": plan.get("create_time"),
            "update_time": plan.get("update_time"),
            "payment_definitions": [
                {
                    "name": pd["name"],
                    "type": pd["type"],
                    "frequency": pd["frequency"],
                    "frequency_interval": pd["frequency_interval"],
                    "amount": float(pd["amount"]["value"]),
                    "currency": pd["amount"]["currency"],
                    "cycles": pd["cycles"]
                }
                for pd in plan.get("payment_definitions", [])
            ],
            "merchant_preferences": plan.get("merchant_preferences", {}),
            "links": plan.get("links", [])
        }
    
    def _format_subscription(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        """Format subscription for response."""
        billing_info = subscription.get("billing_info", {})
        
        return {
            "id": subscription["id"],
            "plan_id": subscription["plan_id"],
            "status": subscription["status"],
            "start_time": subscription.get("start_time"),
            "quantity": subscription.get("quantity", 1),
            "subscriber": {
                "email": subscription.get("subscriber", {}).get("email_address"),
                "name": subscription.get("subscriber", {}).get("name", {}).get("given_name"),
                "payer_id": subscription.get("subscriber", {}).get("payer_id")
            },
            "billing_info": {
                "last_payment": {
                    "amount": float(billing_info.get("last_payment", {}).get("amount", {}).get("value", 0)),
                    "currency": billing_info.get("last_payment", {}).get("amount", {}).get("currency_code"),
                    "time": billing_info.get("last_payment", {}).get("time")
                } if billing_info.get("last_payment") else None,
                "next_billing_time": billing_info.get("next_billing_time"),
                "final_payment_time": billing_info.get("final_payment_time"),
                "failed_payments_count": billing_info.get("failed_payments_count")
            },
            "create_time": subscription.get("create_time"),
            "update_time": subscription.get("update_time"),
            "custom_id": subscription.get("custom_id"),
            "links": subscription.get("links", [])
        }
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance.
        
        Returns:
            Dict[str, Any]: Balance information
        """
        try:
            response = await self._make_request(
                "GET",
                "/v1/reporting/balances"
            )
            
            return {
                "balances": [
                    {
                        "currency": balance["currency"],
                        "total": float(balance["total"]["value"]),
                        "available": float(balance["available"]["value"]),
                        "withheld": float(balance["withheld"]["value"]) if balance.get("withheld") else 0
                    }
                    for balance in response.get("balances", [])
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve balance: {e}")
            raise PaymentGatewayError(f"Balance retrieval failed: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get gateway statistics.
        
        Returns:
            Dict[str, Any]: Statistics
        """
        return {
            **self.stats,
            "environment": self.environment,
            "success_rate": (
                (self.stats["payments_succeeded"] / self.stats["payments_processed"] * 100)
                if self.stats["payments_processed"] > 0 else 0
            ),
            "error_rate": (
                (self.stats["api_errors"] / self.stats["api_calls"] * 100)
                if self.stats["api_calls"] > 0 else 0
            ),
            "average_amount": (
                self.stats["total_amount"] / self.stats["payments_processed"]
                if self.stats["payments_processed"] > 0 else 0
            )
        }
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Check gateway health.
        
        Returns:
            Dict[str, Any]: Health status
        """
        try:
            # Test API connectivity
            await self.get_access_token()
            
            return {
                "status": "healthy",
                "gateway": "paypal",
                "environment": self.environment,
                "api_connected": True
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "gateway": "paypal",
                "environment": self.environment,
                "error": str(e)
            }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_session()


# Singleton instance
paypal_gateway = PayPalGateway()


def get_paypal_gateway() -> PayPalGateway:
    """
    Get PayPal gateway singleton.
    
    Returns:
        PayPalGateway: PayPal gateway instance
    """
    return paypal_gateway