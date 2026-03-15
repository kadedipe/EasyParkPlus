"""
Razorpay payment gateway integration.
Handles all Razorpay-specific payment operations including payments, refunds, subscriptions, and webhooks.
"""

import asyncio
import json
import hmac
import hashlib
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


class RazorpayCurrency(str, Enum):
    """Razorpay supported currencies."""
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    SGD = "SGD"
    AED = "AED"
    AUD = "AUD"
    CAD = "CAD"
    HKD = "HKD"
    MYR = "MYR"
    SAR = "SAR"
    JPY = "JPY"


class RazorpayPaymentStatus(str, Enum):
    """Razorpay payment status."""
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    REFUNDED = "refunded"
    FAILED = "failed"


class RazorpaySubscriptionStatus(str, Enum):
    """Razorpay subscription status."""
    CREATED = "created"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    PENDING = "pending"
    HALTED = "halted"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RazorpayGateway:
    """
    Razorpay payment gateway implementation.
    """
    
    def __init__(self):
        """Initialize Razorpay gateway."""
        self.logger = get_logger(__name__)
        
        # Configuration
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        
        # API endpoints
        self.api_base = "https://api.razorpay.com/v1"
        
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
            "total_amount_inr": 0  # Track INR equivalent
        }
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        self.logger.info("Razorpay gateway initialized")
    
    async def ensure_session(self) -> None:
        """Ensure HTTP session exists."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self) -> None:
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _generate_signature(self, payload: Union[str, bytes]) -> str:
        """Generate signature for webhook verification."""
        if isinstance(payload, str):
            payload = payload.encode('utf-8')
        return hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
    
    def _generate_idempotency_key(self) -> str:
        """Generate idempotency key."""
        import uuid
        return str(uuid.uuid4())
    
    async def _make_request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Razorpay API.
        
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
        
        # Prepare authentication
        auth = BasicAuth(self.key_id, self.key_secret)
        
        # Prepare headers
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Razorpay-Idempotency-Key": self._generate_idempotency_key()
        }
        
        if headers:
            request_headers.update(headers)
        
        # Prepare URL
        url = f"{self.api_base}{path}"
        
        # Make request
        try:
            async with self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=request_headers,
                auth=auth
            ) as response:
                response_data = await response.json() if response.content else {}
                
                if response.status in [200, 201, 202]:
                    return response_data
                else:
                    self.stats["api_errors"] += 1
                    error_message = self._extract_error_message(response_data)
                    self.logger.error(f"Razorpay API error: {response.status} - {error_message}")
                    
                    if response.status == 400:
                        raise PaymentValidationError(error_message)
                    elif response.status == 401:
                        raise PaymentGatewayError("Authentication failed")
                    elif response.status == 404:
                        raise PaymentValidationError("Resource not found")
                    elif response.status == 422:
                        raise PaymentValidationError(f"Validation error: {error_message}")
                    elif response.status == 429:
                        raise PaymentGatewayError("Rate limit exceeded")
                    else:
                        raise PaymentGatewayError(f"Razorpay API error: {error_message}")
                        
        except aiohttp.ClientError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"HTTP request failed: {e}")
            raise PaymentGatewayError(f"HTTP request failed: {e}")
    
    def _extract_error_message(self, response_data: Dict[str, Any]) -> str:
        """Extract error message from response."""
        if "error" in response_data:
            error = response_data["error"]
            if isinstance(error, dict):
                return error.get("description", json.dumps(error))
            return str(error)
        elif "message" in response_data:
            return response_data["message"]
        else:
            return json.dumps(response_data)
    
    def _convert_amount(self, amount: float, currency: str) -> int:
        """
        Convert amount to smallest currency unit (paise for INR).
        
        Args:
            amount: Amount in standard unit
            currency: Currency code
            
        Returns:
            int: Amount in smallest currency unit
        """
        # Most currencies use 2 decimal places
        # INR uses paise (100 paise = 1 rupee)
        return int(amount * 100)
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_order(
        self,
        amount: float,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
        payment_capture: bool = True,
        partial_payment: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a Razorpay order.
        
        Args:
            amount: Amount to charge
            currency: Currency code (INR, USD, etc.)
            receipt: Receipt ID for your reference
            notes: Additional notes
            payment_capture: Auto capture payment
            partial_payment: Allow partial payments
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Order response
        """
        try:
            # Convert amount to paise (smallest currency unit)
            amount_paise = self._convert_amount(amount, currency)
            
            # Prepare order data
            order_data = {
                "amount": amount_paise,
                "currency": currency,
                "payment_capture": 1 if payment_capture else 0,
                "partial_payment": partial_payment
            }
            
            if receipt:
                order_data["receipt"] = receipt[:40]  # Razorpay limit
            
            if notes:
                order_data["notes"] = notes
            
            # Make request
            response = await self._make_request(
                "POST",
                "/orders",
                data=order_data
            )
            
            self.stats["payments_processed"] += 1
            self.stats["total_amount"] += amount
            if currency == "INR":
                self.stats["total_amount_inr"] += amount
            
            self.logger.info(
                f"Order created: {response['id']}, "
                f"amount: {amount} {currency}"
            )
            
            return self._format_order(response)
            
        except Exception as e:
            self.stats["payments_failed"] += 1
            self.logger.error(f"Failed to create order: {e}")
            raise
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def fetch_order(
        self,
        order_id: str
    ) -> Dict[str, Any]:
        """
        Fetch order details.
        
        Args:
            order_id: Order ID
            
        Returns:
            Dict[str, Any]: Order details
        """
        try:
            response = await self._make_request(
                "GET",
                f"/orders/{order_id}"
            )
            
            return self._format_order(response)
            
        except Exception as e:
            self.logger.error(f"Failed to fetch order: {e}")
            raise PaymentGatewayError(f"Order fetch failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def fetch_all_orders(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        count: int = 10,
        skip: int = 0,
        authorized: Optional[bool] = None,
        receipt: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all orders with filters.
        
        Args:
            from_date: Start date
            to_date: End date
            count: Number of orders to fetch
            skip: Number of orders to skip
            authorized: Filter by authorized status
            receipt: Filter by receipt
            
        Returns:
            List[Dict[str, Any]]: List of orders
        """
        try:
            params = {
                "count": count,
                "skip": skip
            }
            
            if from_date:
                params["from"] = int(from_date.timestamp())
            if to_date:
                params["to"] = int(to_date.timestamp())
            if authorized is not None:
                params["authorized"] = authorized
            if receipt:
                params["receipt"] = receipt
            
            response = await self._make_request(
                "GET",
                "/orders",
                params=params
            )
            
            return [self._format_order(item) for item in response.get("items", [])]
            
        except Exception as e:
            self.logger.error(f"Failed to fetch orders: {e}")
            raise PaymentGatewayError(f"Orders fetch failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_payment(
        self,
        order_id: str,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        method: Optional[str] = None,
        email: Optional[str] = None,
        contact: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a payment (for order).
        
        Args:
            order_id: Order ID
            amount: Amount to pay (if partial)
            currency: Currency code
            method: Payment method (card, netbanking, wallet, etc.)
            email: Customer email
            contact: Customer contact number
            notes: Additional notes
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Payment response
        """
        try:
            # Prepare payment data
            payment_data = {
                "order_id": order_id
            }
            
            if amount:
                payment_data["amount"] = self._convert_amount(amount, currency or "INR")
            
            if method:
                payment_data["method"] = method
            
            if email:
                payment_data["email"] = email
            
            if contact:
                payment_data["contact"] = contact
            
            if notes:
                payment_data["notes"] = notes
            
            # Make request
            response = await self._make_request(
                "POST",
                "/payments",
                data=payment_data
            )
            
            self.logger.info(f"Payment created: {response['id']} for order: {order_id}")
            
            return self._format_payment(response)
            
        except Exception as e:
            self.logger.error(f"Failed to create payment: {e}")
            raise PaymentProcessingError(f"Payment creation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def capture_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None,
        currency: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Capture an authorized payment.
        
        Args:
            payment_id: Payment ID
            amount: Amount to capture (full if None)
            currency: Currency code
            
        Returns:
            Dict[str, Any]: Captured payment
        """
        try:
            # Prepare capture data
            capture_data = {}
            
            if amount:
                capture_data["amount"] = self._convert_amount(amount, currency or "INR")
            
            # Make request
            response = await self._make_request(
                "POST",
                f"/payments/{payment_id}/capture",
                data=capture_data
            )
            
            self.logger.info(f"Payment captured: {payment_id}")
            self.stats["payments_succeeded"] += 1
            
            return self._format_payment(response)
            
        except Exception as e:
            self.logger.error(f"Failed to capture payment: {e}")
            raise PaymentProcessingError(f"Capture failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def fetch_payment(
        self,
        payment_id: str
    ) -> Dict[str, Any]:
        """
        Fetch payment details.
        
        Args:
            payment_id: Payment ID
            
        Returns:
            Dict[str, Any]: Payment details
        """
        try:
            response = await self._make_request(
                "GET",
                f"/payments/{payment_id}"
            )
            
            return self._format_payment(response)
            
        except Exception as e:
            self.logger.error(f"Failed to fetch payment: {e}")
            raise PaymentGatewayError(f"Payment fetch failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def fetch_payments_for_order(
        self,
        order_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch all payments for an order.
        
        Args:
            order_id: Order ID
            
        Returns:
            List[Dict[str, Any]]: List of payments
        """
        try:
            response = await self._make_request(
                "GET",
                f"/orders/{order_id}/payments"
            )
            
            return [self._format_payment(item) for item in response.get("items", [])]
            
        except Exception as e:
            self.logger.error(f"Failed to fetch order payments: {e}")
            raise PaymentGatewayError(f"Order payments fetch failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_refund(
        self,
        payment_id: str,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        speed: str = "normal",
        notes: Optional[Dict[str, Any]] = None,
        receipt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a refund.
        
        Args:
            payment_id: Payment ID
            amount: Amount to refund (full if None)
            currency: Currency code
            speed: Refund speed (normal, optimum, instant)
            notes: Additional notes
            receipt: Receipt reference
            
        Returns:
            Dict[str, Any]: Refund response
        """
        try:
            self.stats["api_calls"] += 1
            
            # Prepare refund data
            refund_data = {}
            
            if amount:
                refund_data["amount"] = self._convert_amount(amount, currency or "INR")
            
            if speed:
                refund_data["speed"] = speed
            
            if notes:
                refund_data["notes"] = notes
            
            if receipt:
                refund_data["receipt"] = receipt
            
            # Make request
            response = await self._make_request(
                "POST",
                f"/payments/{payment_id}/refund",
                data=refund_data
            )
            
            self.logger.info(f"Refund created: {response['id']} for payment: {payment_id}")
            
            self.stats["refunds_processed"] += 1
            self.stats["refunds_succeeded"] += 1
            
            return self._format_refund(response)
            
        except Exception as e:
            self.stats["refunds_processed"] += 1
            self.logger.error(f"Failed to create refund: {e}")
            raise RefundError(f"Refund failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def fetch_refund(
        self,
        refund_id: str
    ) -> Dict[str, Any]:
        """
        Fetch refund details.
        
        Args:
            refund_id: Refund ID
            
        Returns:
            Dict[str, Any]: Refund details
        """
        try:
            response = await self._make_request(
                "GET",
                f"/refunds/{refund_id}"
            )
            
            return self._format_refund(response)
            
        except Exception as e:
            self.logger.error(f"Failed to fetch refund: {e}")
            raise PaymentGatewayError(f"Refund fetch failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def fetch_all_refunds(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        count: int = 10,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Fetch all refunds.
        
        Args:
            from_date: Start date
            to_date: End date
            count: Number of refunds to fetch
            skip: Number of refunds to skip
            
        Returns:
            List[Dict[str, Any]]: List of refunds
        """
        try:
            params = {
                "count": count,
                "skip": skip
            }
            
            if from_date:
                params["from"] = int(from_date.timestamp())
            if to_date:
                params["to"] = int(to_date.timestamp())
            
            response = await self._make_request(
                "GET",
                "/refunds",
                params=params
            )
            
            return [self._format_refund(item) for item in response.get("items", [])]
            
        except Exception as e:
            self.logger.error(f"Failed to fetch refunds: {e}")
            raise PaymentGatewayError(f"Refunds fetch failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_subscription(
        self,
        plan_id: str,
        customer_id: Optional[str] = None,
        customer_notify: bool = True,
        quantity: int = 1,
        total_count: int = 0,
        start_at: Optional[datetime] = None,
        expire_by: Optional[datetime] = None,
        addons: Optional[List[Dict[str, Any]]] = None,
        notes: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a subscription.
        
        Args:
            plan_id: Plan ID
            customer_id: Customer ID
            customer_notify: Notify customer
            quantity: Quantity
            total_count: Total number of billing cycles (0 for infinite)
            start_at: Start time
            expire_by: Expiry time
            addons: Addons to include
            notes: Additional notes
            **kwargs: Additional parameters
            
        Returns:
            Dict[str, Any]: Subscription details
        """
        try:
            self.stats["api_calls"] += 1
            
            # Prepare subscription data
            subscription_data = {
                "plan_id": plan_id,
                "total_count": total_count,
                "quantity": quantity,
                "customer_notify": 1 if customer_notify else 0
            }
            
            if customer_id:
                subscription_data["customer_id"] = customer_id
            
            if start_at:
                subscription_data["start_at"] = int(start_at.timestamp())
            
            if expire_by:
                subscription_data["expire_by"] = int(expire_by.timestamp())
            
            if addons:
                subscription_data["addons"] = addons
            
            if notes:
                subscription_data["notes"] = notes
            
            # Make request
            response = await self._make_request(
                "POST",
                "/subscriptions",
                data=subscription_data
            )
            
            self.stats["subscriptions_created"] += 1
            
            self.logger.info(f"Subscription created: {response['id']}")
            
            return self._format_subscription(response)
            
        except Exception as e:
            self.logger.error(f"Failed to create subscription: {e}")
            raise PaymentGatewayError(f"Subscription creation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def fetch_subscription(
        self,
        subscription_id: str
    ) -> Dict[str, Any]:
        """
        Fetch subscription details.
        
        Args:
            subscription_id: Subscription ID
            
        Returns:
            Dict[str, Any]: Subscription details
        """
        try:
            response = await self._make_request(
                "GET",
                f"/subscriptions/{subscription_id}"
            )
            
            return self._format_subscription(response)
            
        except Exception as e:
            self.logger.error(f"Failed to fetch subscription: {e}")
            raise PaymentGatewayError(f"Subscription fetch failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_at_cycle_end: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription ID
            cancel_at_cycle_end: Cancel at current cycle end
            
        Returns:
            Dict[str, Any]: Cancellation response
        """
        try:
            params = {}
            if cancel_at_cycle_end:
                params["cancel_at_cycle_end"] = 1
            
            response = await self._make_request(
                "POST",
                f"/subscriptions/{subscription_id}/cancel",
                params=params
            )
            
            self.stats["subscriptions_canceled"] += 1
            
            self.logger.info(f"Subscription canceled: {subscription_id}")
            
            return self._format_subscription(response)
            
        except Exception as e:
            self.logger.error(f"Failed to cancel subscription: {e}")
            raise PaymentGatewayError(f"Subscription cancellation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def pause_subscription(
        self,
        subscription_id: str,
        pause_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Pause a subscription.
        
        Args:
            subscription_id: Subscription ID
            pause_at: When to pause
            
        Returns:
            Dict[str, Any]: Paused subscription
        """
        try:
            pause_data = {}
            if pause_at:
                pause_data["pause_at"] = int(pause_at.timestamp())
            
            response = await self._make_request(
                "POST",
                f"/subscriptions/{subscription_id}/pause",
                data=pause_data
            )
            
            self.logger.info(f"Subscription paused: {subscription_id}")
            
            return self._format_subscription(response)
            
        except Exception as e:
            self.logger.error(f"Failed to pause subscription: {e}")
            raise PaymentGatewayError(f"Subscription pause failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def resume_subscription(
        self,
        subscription_id: str,
        resume_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Resume a paused subscription.
        
        Args:
            subscription_id: Subscription ID
            resume_at: When to resume
            
        Returns:
            Dict[str, Any]: Resumed subscription
        """
        try:
            resume_data = {}
            if resume_at:
                resume_data["resume_at"] = int(resume_at.timestamp())
            
            response = await self._make_request(
                "POST",
                f"/subscriptions/{subscription_id}/resume",
                data=resume_data
            )
            
            self.logger.info(f"Subscription resumed: {subscription_id}")
            
            return self._format_subscription(response)
            
        except Exception as e:
            self.logger.error(f"Failed to resume subscription: {e}")
            raise PaymentGatewayError(f"Subscription resume failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_plan(
        self,
        period: str,
        interval: int,
        item_name: str,
        amount: float,
        currency: str = "INR",
        description: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a subscription plan.
        
        Args:
            period: Period (daily, weekly, monthly, yearly)
            interval: Interval (1, 2, 3, etc.)
            item_name: Plan item name
            amount: Amount per billing cycle
            currency: Currency code
            description: Plan description
            notes: Additional notes
            
        Returns:
            Dict[str, Any]: Plan details
        """
        try:
            # Convert amount to paise
            amount_paise = self._convert_amount(amount, currency)
            
            # Prepare plan data
            plan_data = {
                "period": period,
                "interval": interval,
                "item": {
                    "name": item_name[:30], # Razorpay limit
                    "description": description,
                    "notes": notes
                },
                "amount": amount_paise,
                "currency": currency
            }

            response = await self._make_request(
                "POST",
                "/plans",
                data=plan_data
            )

            self.logger.info(f"Plan created: {response['id']}")

            return self._format_plan(response)

        except Exception as e:
            self.logger.error(f"Failed to create plan: {e}")
            raise PaymentGatewayError(f"Plan creation failed: {e}")