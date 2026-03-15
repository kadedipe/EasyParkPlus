"""
Stripe payment gateway integration.
Handles all Stripe-specific payment operations including payments, refunds, subscriptions, and webhooks.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from enum import Enum

import stripe
from stripe.error import StripeError

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


class PaymentMethod(str, Enum):
    """Stripe payment method types."""
    CARD = "card"
    BANK_ACCOUNT = "bank_account"
    IDEAL = "ideal"
    SOFORT = "sofort"
    GIROPAY = "giropay"
    BANCONTACT = "bancontact"
    EPS = "eps"
    P24 = "p24"
    SEPA_DEBIT = "sepa_debit"
    WECHAT_PAY = "wechat_pay"
    ALIPAY = "alipay"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"


class PaymentIntentStatus(str, Enum):
    """Payment intent status."""
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_ACTION = "requires_action"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"


class StripeGateway:
    """
    Stripe payment gateway implementation.
    """
    
    def __init__(self):
        """Initialize Stripe gateway."""
        self.logger = get_logger(__name__)
        
        # Configure Stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.api_version = settings.STRIPE_API_VERSION
        
        if settings.STRIPE_WEBHOOK_SECRET:
            self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        
        # Metrics
        self.stats = {
            "payments_processed": 0,
            "payments_succeeded": 0,
            "payments_failed": 0,
            "refunds_processed": 0,
            "refunds_succeeded": 0,
            "webhooks_received": 0,
            "api_calls": 0,
            "api_errors": 0,
            "total_amount": 0,
            "total_fees": 0
        }
        
        self.logger.info("Stripe gateway initialized")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_payment_intent(
        self,
        amount: float,
        currency: str = "usd",
        payment_method_types: Optional[List[str]] = None,
        customer_id: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        capture_method: str = "automatic",
        confirmation_method: str = "automatic",
        setup_future_usage: Optional[str] = None,
        statement_descriptor: Optional[str] = None,
        receipt_email: Optional[str] = None,
        return_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a payment intent.
        
        Args:
            amount: Amount to charge
            currency: Currency code
            payment_method_types: Allowed payment methods
            customer_id: Stripe customer ID
            payment_method_id: Payment method to use
            description: Payment description
            metadata: Additional metadata
            capture_method: automatic or manual
            confirmation_method: automatic or manual
            setup_future_usage: Setup future usage (on_session, off_session)
            statement_descriptor: Statement descriptor
            receipt_email: Email for receipt
            return_url: Return URL after payment
            **kwargs: Additional Stripe parameters
            
        Returns:
            Dict[str, Any]: Payment intent response
            
        Raises:
            PaymentGatewayError: If payment intent creation fails
        """
        try:
            self.stats["api_calls"] += 1
            
            # Convert amount to cents
            amount_cents = int(amount * 100)
            
            # Prepare parameters
            params = {
                "amount": amount_cents,
                "currency": currency.lower(),
                "payment_method_types": payment_method_types or ["card"],
                "capture_method": capture_method,
                "confirmation_method": confirmation_method,
                "description": description or f"Payment for {amount} {currency}",
                "metadata": metadata or {}
            }
            
            # Add optional parameters
            if customer_id:
                params["customer"] = customer_id
            
            if payment_method_id:
                params["payment_method"] = payment_method_id
            
            if setup_future_usage:
                params["setup_future_usage"] = setup_future_usage
            
            if statement_descriptor:
                params["statement_descriptor"] = statement_descriptor[:22]  # Stripe limit
            
            if receipt_email:
                params["receipt_email"] = receipt_email
            
            if return_url:
                params["return_url"] = return_url
            
            # Add any additional parameters
            params.update(kwargs)
            
            # Create payment intent
            intent = await asyncio.to_thread(
                stripe.PaymentIntent.create,
                **params
            )
            
            self.logger.info(
                f"Payment intent created: {intent.id}, "
                f"amount: {amount} {currency}"
            )
            
            self.stats["payments_processed"] += 1
            self.stats["total_amount"] += amount
            
            return self._format_payment_intent(intent)
            
        except stripe.error.CardError as e:
            self.stats["api_errors"] += 1
            self.stats["payments_failed"] += 1
            self.logger.error(f"Card error: {e.error.message}")
            raise PaymentProcessingError(
                message=e.error.message,
                code=e.error.code,
                payment_intent_id=e.error.payment_intent.get('id') if e.error.payment_intent else None
            )
            
        except stripe.error.RateLimitError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Rate limit error: {e}")
            raise PaymentGatewayError("Rate limit exceeded. Please try again.")
            
        except stripe.error.InvalidRequestError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Invalid request: {e}")
            raise PaymentValidationError(f"Invalid payment request: {e}")
            
        except stripe.error.AuthenticationError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Authentication error: {e}")
            raise PaymentGatewayError("Payment gateway authentication failed")
            
        except stripe.error.APIConnectionError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"API connection error: {e}")
            raise PaymentGatewayError("Failed to connect to payment gateway")
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.stats["payments_failed"] += 1
            self.logger.error(f"Stripe error: {e}")
            raise PaymentGatewayError(f"Payment gateway error: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def confirm_payment_intent(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Confirm a payment intent.
        
        Args:
            payment_intent_id: Payment intent ID
            payment_method_id: Payment method to use
            return_url: Return URL after confirmation
            
        Returns:
            Dict[str, Any]: Confirmed payment intent
            
        Raises:
            PaymentGatewayError: If confirmation fails
        """
        try:
            self.stats["api_calls"] += 1
            
            params = {}
            if payment_method_id:
                params["payment_method"] = payment_method_id
            if return_url:
                params["return_url"] = return_url
            
            intent = await asyncio.to_thread(
                stripe.PaymentIntent.confirm,
                payment_intent_id,
                **params
            )
            
            self.logger.info(f"Payment intent confirmed: {payment_intent_id}")
            
            if intent.status == "succeeded":
                self.stats["payments_succeeded"] += 1
            
            return self._format_payment_intent(intent)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to confirm payment intent: {e}")
            raise PaymentGatewayError(f"Payment confirmation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def capture_payment_intent(
        self,
        payment_intent_id: str,
        amount_to_capture: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Capture a previously authorized payment intent.
        
        Args:
            payment_intent_id: Payment intent ID
            amount_to_capture: Amount to capture (if partial)
            
        Returns:
            Dict[str, Any]: Captured payment intent
        """
        try:
            self.stats["api_calls"] += 1
            
            params = {}
            if amount_to_capture:
                params["amount_to_capture"] = int(amount_to_capture * 100)
            
            intent = await asyncio.to_thread(
                stripe.PaymentIntent.capture,
                payment_intent_id,
                **params
            )
            
            self.logger.info(
                f"Payment intent captured: {payment_intent_id}"
            )
            
            self.stats["payments_succeeded"] += 1
            
            return self._format_payment_intent(intent)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to capture payment intent: {e}")
            raise PaymentGatewayError(f"Payment capture failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def cancel_payment_intent(
        self,
        payment_intent_id: str,
        cancellation_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a payment intent.
        
        Args:
            payment_intent_id: Payment intent ID
            cancellation_reason: Reason for cancellation
            
        Returns:
            Dict[str, Any]: Canceled payment intent
        """
        try:
            self.stats["api_calls"] += 1
            
            intent = await asyncio.to_thread(
                stripe.PaymentIntent.cancel,
                payment_intent_id,
                cancellation_reason=cancellation_reason
            )
            
            self.logger.info(f"Payment intent canceled: {payment_intent_id}")
            
            return self._format_payment_intent(intent)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to cancel payment intent: {e}")
            raise PaymentGatewayError(f"Payment cancellation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def retrieve_payment_intent(
        self,
        payment_intent_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve a payment intent.
        
        Args:
            payment_intent_id: Payment intent ID
            
        Returns:
            Dict[str, Any]: Payment intent details
        """
        try:
            self.stats["api_calls"] += 1
            
            intent = await asyncio.to_thread(
                stripe.PaymentIntent.retrieve,
                payment_intent_id
            )
            
            return self._format_payment_intent(intent)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to retrieve payment intent: {e}")
            raise PaymentGatewayError(f"Failed to retrieve payment: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_refund(
        self,
        payment_intent_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
        refund_application_fee: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a refund.
        
        Args:
            payment_intent_id: Payment intent to refund
            amount: Amount to refund (full if None)
            reason: Refund reason (duplicate, fraudulent, requested_by_customer)
            refund_application_fee: Refund application fee
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: Refund details
        """
        try:
            self.stats["api_calls"] += 1
            
            params = {
                "payment_intent": payment_intent_id,
                "refund_application_fee": refund_application_fee
            }
            
            if amount:
                params["amount"] = int(amount * 100)
            
            if reason:
                params["reason"] = reason
            
            if metadata:
                params["metadata"] = metadata
            
            refund = await asyncio.to_thread(
                stripe.Refund.create,
                **params
            )
            
            self.logger.info(
                f"Refund created: {refund.id} for payment: {payment_intent_id}"
            )
            
            self.stats["refunds_processed"] += 1
            self.stats["refunds_succeeded"] += 1
            
            return self._format_refund(refund)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to create refund: {e}")
            raise RefundError(f"Refund failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        description: Optional[str] = None,
        payment_method_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        address: Optional[Dict[str, Any]] = None,
        tax_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe customer.
        
        Args:
            email: Customer email
            name: Customer name
            phone: Customer phone
            description: Customer description
            payment_method_id: Payment method to attach
            metadata: Additional metadata
            address: Customer address
            tax_id: Tax ID
            
        Returns:
            Dict[str, Any]: Customer details
        """
        try:
            self.stats["api_calls"] += 1
            
            params = {
                "email": email,
                "metadata": metadata or {}
            }
            
            if name:
                params["name"] = name
            
            if phone:
                params["phone"] = phone
            
            if description:
                params["description"] = description
            
            if address:
                params["address"] = address
            
            customer = await asyncio.to_thread(
                stripe.Customer.create,
                **params
            )
            
            # Attach payment method if provided
            if payment_method_id:
                await self.attach_payment_method_to_customer(
                    customer.id,
                    payment_method_id
                )
            
            self.logger.info(f"Customer created: {customer.id}")
            
            return self._format_customer(customer)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to create customer: {e}")
            raise PaymentGatewayError(f"Customer creation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def retrieve_customer(
        self,
        customer_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve a Stripe customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Dict[str, Any]: Customer details
        """
        try:
            self.stats["api_calls"] += 1
            
            customer = await asyncio.to_thread(
                stripe.Customer.retrieve,
                customer_id
            )
            
            return self._format_customer(customer)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to retrieve customer: {e}")
            raise PaymentGatewayError(f"Customer retrieval failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def update_customer(
        self,
        customer_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a Stripe customer.
        
        Args:
            customer_id: Customer ID
            **kwargs: Fields to update
            
        Returns:
            Dict[str, Any]: Updated customer
        """
        try:
            self.stats["api_calls"] += 1
            
            customer = await asyncio.to_thread(
                stripe.Customer.modify,
                customer_id,
                **kwargs
            )
            
            self.logger.info(f"Customer updated: {customer_id}")
            
            return self._format_customer(customer)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to update customer: {e}")
            raise PaymentGatewayError(f"Customer update failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def attach_payment_method_to_customer(
        self,
        customer_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """
        Attach a payment method to a customer.
        
        Args:
            customer_id: Customer ID
            payment_method_id: Payment method ID
            
        Returns:
            Dict[str, Any]: Payment method details
        """
        try:
            self.stats["api_calls"] += 1
            
            # Attach payment method
            payment_method = await asyncio.to_thread(
                stripe.PaymentMethod.attach,
                payment_method_id,
                customer=customer_id
            )
            
            # Set as default payment method
            await asyncio.to_thread(
                stripe.Customer.modify,
                customer_id,
                invoice_settings={
                    "default_payment_method": payment_method_id
                }
            )
            
            self.logger.info(
                f"Payment method {payment_method_id} attached to customer {customer_id}"
            )
            
            return self._format_payment_method(payment_method)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to attach payment method: {e}")
            raise PaymentGatewayError(f"Failed to attach payment method: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def detach_payment_method(
        self,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """
        Detach a payment method.
        
        Args:
            payment_method_id: Payment method ID
            
        Returns:
            Dict[str, Any]: Detached payment method
        """
        try:
            self.stats["api_calls"] += 1
            
            payment_method = await asyncio.to_thread(
                stripe.PaymentMethod.detach,
                payment_method_id
            )
            
            self.logger.info(f"Payment method detached: {payment_method_id}")
            
            return self._format_payment_method(payment_method)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to detach payment method: {e}")
            raise PaymentGatewayError(f"Failed to detach payment method: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def list_payment_methods(
        self,
        customer_id: str,
        payment_method_type: str = "card",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        List payment methods for a customer.
        
        Args:
            customer_id: Customer ID
            payment_method_type: Type of payment method
            limit: Maximum number to return
            
        Returns:
            List[Dict[str, Any]]: List of payment methods
        """
        try:
            self.stats["api_calls"] += 1
            
            payment_methods = await asyncio.to_thread(
                stripe.PaymentMethod.list,
                customer=customer_id,
                type=payment_method_type,
                limit=limit
            )
            
            return [
                self._format_payment_method(pm)
                for pm in payment_methods.data
            ]
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to list payment methods: {e}")
            raise PaymentGatewayError(f"Failed to list payment methods: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_setup_intent(
        self,
        customer_id: str,
        payment_method_types: Optional[List[str]] = None,
        usage: str = "off_session",
        metadata: Optional[Dict[str, Any]] = None,
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a setup intent for saving payment methods.
        
        Args:
            customer_id: Customer ID
            payment_method_types: Allowed payment methods
            usage: on_session or off_session
            metadata: Additional metadata
            return_url: Return URL after setup
            
        Returns:
            Dict[str, Any]: Setup intent
        """
        try:
            self.stats["api_calls"] += 1
            
            params = {
                "customer": customer_id,
                "payment_method_types": payment_method_types or ["card"],
                "usage": usage,
                "metadata": metadata or {}
            }
            
            if return_url:
                params["return_url"] = return_url
            
            setup_intent = await asyncio.to_thread(
                stripe.SetupIntent.create,
                **params
            )
            
            self.logger.info(f"Setup intent created: {setup_intent.id}")
            
            return self._format_setup_intent(setup_intent)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to create setup intent: {e}")
            raise PaymentGatewayError(f"Setup intent creation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        payment_method_id: Optional[str] = None,
        trial_period_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        coupon_id: Optional[str] = None,
        collection_method: str = "charge_automatically",
        days_until_due: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a subscription.
        
        Args:
            customer_id: Customer ID
            price_id: Price ID
            payment_method_id: Payment method ID
            trial_period_days: Trial period in days
            metadata: Additional metadata
            coupon_id: Coupon ID
            collection_method: charge_automatically or send_invoice
            days_until_due: Days until due for invoices
            
        Returns:
            Dict[str, Any]: Subscription details
        """
        try:
            self.stats["api_calls"] += 1
            
            # Set default payment method if provided
            if payment_method_id:
                await asyncio.to_thread(
                    stripe.Customer.modify,
                    customer_id,
                    invoice_settings={
                        "default_payment_method": payment_method_id
                    }
                )
            
            params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "collection_method": collection_method,
                "metadata": metadata or {}
            }
            
            if trial_period_days:
                params["trial_period_days"] = trial_period_days
            
            if coupon_id:
                params["coupon"] = coupon_id
            
            if days_until_due:
                params["days_until_due"] = days_until_due
            
            subscription = await asyncio.to_thread(
                stripe.Subscription.create,
                **params
            )
            
            self.logger.info(f"Subscription created: {subscription.id}")
            
            return self._format_subscription(subscription)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to create subscription: {e}")
            raise PaymentGatewayError(f"Subscription creation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_at_period_end: bool = False,
        invoice_now: bool = True,
        prorate: bool = True
    ) -> Dict[str, Any]:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Subscription ID
            cancel_at_period_end: Cancel at period end
            invoice_now: Invoice immediately
            prorate: Prorate charges
            
        Returns:
            Dict[str, Any]: Canceled subscription
        """
        try:
            self.stats["api_calls"] += 1
            
            if cancel_at_period_end:
                # Update to cancel at period end
                subscription = await asyncio.to_thread(
                    stripe.Subscription.modify,
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                # Cancel immediately
                subscription = await asyncio.to_thread(
                    stripe.Subscription.delete,
                    subscription_id,
                    invoice_now=invoice_now,
                    prorate=prorate
                )
            
            self.logger.info(f"Subscription canceled: {subscription_id}")
            
            return self._format_subscription(subscription)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to cancel subscription: {e}")
            raise PaymentGatewayError(f"Subscription cancellation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_invoice(
        self,
        customer_id: str,
        payment_method_id: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        days_until_due: Optional[int] = None,
        collection_method: str = "charge_automatically"
    ) -> Dict[str, Any]:
        """
        Create an invoice.
        
        Args:
            customer_id: Customer ID
            payment_method_id: Payment method ID
            description: Invoice description
            metadata: Additional metadata
            days_until_due: Days until due
            collection_method: charge_automatically or send_invoice
            
        Returns:
            Dict[str, Any]: Invoice details
        """
        try:
            self.stats["api_calls"] += 1
            
            params = {
                "customer": customer_id,
                "collection_method": collection_method,
                "metadata": metadata or {}
            }
            
            if description:
                params["description"] = description
            
            if days_until_due:
                params["days_until_due"] = days_until_due
            
            invoice = await asyncio.to_thread(
                stripe.Invoice.create,
                **params
            )
            
            self.logger.info(f"Invoice created: {invoice.id}")
            
            return self._format_invoice(invoice)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to create invoice: {e}")
            raise PaymentGatewayError(f"Invoice creation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def finalize_invoice(
        self,
        invoice_id: str
    ) -> Dict[str, Any]:
        """
        Finalize an invoice.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Dict[str, Any]: Finalized invoice
        """
        try:
            self.stats["api_calls"] += 1
            
            invoice = await asyncio.to_thread(
                stripe.Invoice.finalize_invoice,
                invoice_id
            )
            
            self.logger.info(f"Invoice finalized: {invoice_id}")
            
            return self._format_invoice(invoice)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to finalize invoice: {e}")
            raise PaymentGatewayError(f"Invoice finalization failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def pay_invoice(
        self,
        invoice_id: str,
        payment_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pay an invoice.
        
        Args:
            invoice_id: Invoice ID
            payment_method_id: Payment method ID
            
        Returns:
            Dict[str, Any]: Paid invoice
        """
        try:
            self.stats["api_calls"] += 1
            
            params = {}
            if payment_method_id:
                params["payment_method"] = payment_method_id
            
            invoice = await asyncio.to_thread(
                stripe.Invoice.pay,
                invoice_id,
                **params
            )
            
            self.logger.info(f"Invoice paid: {invoice_id}")
            
            return self._format_invoice(invoice)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to pay invoice: {e}")
            raise PaymentGatewayError(f"Invoice payment failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_product(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        active: bool = True
    ) -> Dict[str, Any]:
        """
        Create a product.
        
        Args:
            name: Product name
            description: Product description
            metadata: Additional metadata
            active: Whether product is active
            
        Returns:
            Dict[str, Any]: Product details
        """
        try:
            self.stats["api_calls"] += 1
            
            params = {
                "name": name,
                "active": active,
                "metadata": metadata or {}
            }
            
            if description:
                params["description"] = description
            
            product = await asyncio.to_thread(
                stripe.Product.create,
                **params
            )
            
            self.logger.info(f"Product created: {product.id}")
            
            return self._format_product(product)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to create product: {e}")
            raise PaymentGatewayError(f"Product creation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_price(
        self,
        product_id: str,
        unit_amount: float,
        currency: str = "usd",
        recurring: Optional[Dict[str, Any]] = None,
        nickname: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        active: bool = True
    ) -> Dict[str, Any]:
        """
        Create a price.
        
        Args:
            product_id: Product ID
            unit_amount: Unit amount
            currency: Currency code
            recurring: Recurring interval (e.g., {"interval": "month"})
            nickname: Price nickname
            metadata: Additional metadata
            active: Whether price is active
            
        Returns:
            Dict[str, Any]: Price details
        """
        try:
            self.stats["api_calls"] += 1
            
            params = {
                "product": product_id,
                "unit_amount": int(unit_amount * 100),
                "currency": currency,
                "active": active,
                "metadata": metadata or {}
            }
            
            if recurring:
                params["recurring"] = recurring
            
            if nickname:
                params["nickname"] = nickname
            
            price = await asyncio.to_thread(
                stripe.Price.create,
                **params
            )
            
            self.logger.info(f"Price created: {price.id}")
            
            return self._format_price(price)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to create price: {e}")
            raise PaymentGatewayError(f"Price creation failed: {e}")
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def create_coupon(
        self,
        percent_off: Optional[float] = None,
        amount_off: Optional[float] = None,
        currency: str = "usd",
        duration: str = "once",
        duration_in_months: Optional[int] = None,
        max_redemptions: Optional[int] = None,
        redeem_by: Optional[datetime] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a coupon.
        
        Args:
            percent_off: Percentage off
            amount_off: Fixed amount off
            currency: Currency code
            duration: once, repeating, forever
            duration_in_months: Months if duration is repeating
            max_redemptions: Maximum number of redemptions
            redeem_by: Redemption deadline
            name: Coupon name
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: Coupon details
        """
        try:
            self.stats["api_calls"] += 1
            
            params = {
                "duration": duration,
                "metadata": metadata or {}
            }
            
            if percent_off:
                params["percent_off"] = percent_off
            elif amount_off:
                params["amount_off"] = int(amount_off * 100)
                params["currency"] = currency
            
            if duration_in_months:
                params["duration_in_months"] = duration_in_months
            
            if max_redemptions:
                params["max_redemptions"] = max_redemptions
            
            if redeem_by:
                params["redeem_by"] = int(redeem_by.timestamp())
            
            if name:
                params["name"] = name
            
            coupon = await asyncio.to_thread(
                stripe.Coupon.create,
                **params
            )
            
            self.logger.info(f"Coupon created: {coupon.id}")
            
            return self._format_coupon(coupon)
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to create coupon: {e}")
            raise PaymentGatewayError(f"Coupon creation failed: {e}")
    
    def handle_webhook(
        self,
        payload: Union[str, bytes],
        signature: str
    ) -> Dict[str, Any]:
        """
        Handle Stripe webhook.
        
        Args:
            payload: Webhook payload
            signature: Stripe signature
            
        Returns:
            Dict[str, Any]: Processed webhook event
            
        Raises:
            WebhookError: If webhook verification fails
        """
        try:
            self.stats["webhooks_received"] += 1
            
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.webhook_secret
            )
            
            self.logger.info(f"Webhook received: {event['type']}")
            
            # Process event based on type
            result = self._process_webhook_event(event)
            
            return {
                "event_id": event["id"],
                "event_type": event["type"],
                "processed": True,
                "data": result
            }
            
        except stripe.error.SignatureVerificationError as e:
            self.logger.error(f"Invalid webhook signature: {e}")
            raise WebhookError("Invalid webhook signature")
            
        except Exception as e:
            self.logger.error(f"Webhook processing error: {e}")
            raise WebhookError(f"Webhook processing failed: {e}")
    
    def _process_webhook_event(self, event: stripe.Event) -> Dict[str, Any]:
        """
        Process webhook event.
        
        Args:
            event: Stripe event
            
        Returns:
            Dict[str, Any]: Processed event data
        """
        event_type = event["type"]
        data = event["data"]["object"]
        
        # Handle different event types
        if event_type.startswith("payment_intent."):
            return self._process_payment_intent_event(event_type, data)
        elif event_type.startswith("invoice."):
            return self._process_invoice_event(event_type, data)
        elif event_type.startswith("customer."):
            return self._process_customer_event(event_type, data)
        elif event_type.startswith("subscription."):
            return self._process_subscription_event(event_type, data)
        elif event_type.startswith("charge."):
            return self._process_charge_event(event_type, data)
        elif event_type.startswith("refund."):
            return self._process_refund_event(event_type, data)
        else:
            return {"event": event_type, "data": data}
    
    def _process_payment_intent_event(
        self,
        event_type: str,
        data: stripe.PaymentIntent
    ) -> Dict[str, Any]:
        """Process payment intent events."""
        result = {
            "payment_intent_id": data["id"],
            "status": data["status"],
            "amount": data["amount"] / 100,
            "currency": data["currency"]
        }
        
        if event_type == "payment_intent.succeeded":
            self.stats["payments_succeeded"] += 1
            result["message"] = "Payment succeeded"
        elif event_type == "payment_intent.payment_failed":
            self.stats["payments_failed"] += 1
            result["message"] = "Payment failed"
            result["error"] = data.get("last_payment_error")
        elif event_type == "payment_intent.canceled":
            result["message"] = "Payment canceled"
        elif event_type == "payment_intent.processing":
            result["message"] = "Payment processing"
        
        return result
    
    def _process_invoice_event(
        self,
        event_type: str,
        data: stripe.Invoice
    ) -> Dict[str, Any]:
        """Process invoice events."""
        return {
            "invoice_id": data["id"],
            "customer_id": data["customer"],
            "status": data["status"],
            "amount_due": data["amount_due"] / 100,
            "amount_paid": data["amount_paid"] / 100,
            "currency": data["currency"]
        }
    
    def _process_customer_event(
        self,
        event_type: str,
        data: stripe.Customer
    ) -> Dict[str, Any]:
        """Process customer events."""
        return {
            "customer_id": data["id"],
            "email": data["email"],
            "name": data.get("name")
        }
    
    def _process_subscription_event(
        self,
        event_type: str,
        data: stripe.Subscription
    ) -> Dict[str, Any]:
        """Process subscription events."""
        return {
            "subscription_id": data["id"],
            "customer_id": data["customer"],
            "status": data["status"],
            "current_period_start": data["current_period_start"],
            "current_period_end": data["current_period_end"]
        }
    
    def _process_charge_event(
        self,
        event_type: str,
        data: stripe.Charge
    ) -> Dict[str, Any]:
        """Process charge events."""
        return {
            "charge_id": data["id"],
            "payment_intent_id": data.get("payment_intent"),
            "amount": data["amount"] / 100,
            "currency": data["currency"],
            "status": data["status"],
            "outcome": data.get("outcome")
        }
    
    def _process_refund_event(
        self,
        event_type: str,
        data: stripe.Refund
    ) -> Dict[str, Any]:
        """Process refund events."""
        return {
            "refund_id": data["id"],
            "payment_intent_id": data.get("payment_intent"),
            "amount": data["amount"] / 100,
            "currency": data["currency"],
            "status": data["status"],
            "reason": data.get("reason")
        }
    
    def _format_payment_intent(self, intent: stripe.PaymentIntent) -> Dict[str, Any]:
        """Format payment intent for response."""
        return {
            "id": intent.id,
            "amount": intent.amount / 100,
            "currency": intent.currency,
            "status": intent.status,
            "client_secret": intent.client_secret,
            "customer_id": intent.customer,
            "payment_method_id": intent.payment_method,
            "description": intent.description,
            "metadata": intent.metadata,
            "created": datetime.fromtimestamp(intent.created).isoformat(),
            "charges": [
                {
                    "id": charge.id,
                    "amount": charge.amount / 100,
                    "status": charge.status,
                    "payment_method_details": charge.payment_method_details
                }
                for charge in intent.charges.data
            ] if intent.charges else []
        }
    
    def _format_refund(self, refund: stripe.Refund) -> Dict[str, Any]:
        """Format refund for response."""
        return {
            "id": refund.id,
            "payment_intent_id": refund.payment_intent,
            "amount": refund.amount / 100,
            "currency": refund.currency,
            "status": refund.status,
            "reason": refund.reason,
            "metadata": refund.metadata,
            "created": datetime.fromtimestamp(refund.created).isoformat()
        }
    
    def _format_customer(self, customer: stripe.Customer) -> Dict[str, Any]:
        """Format customer for response."""
        return {
            "id": customer.id,
            "email": customer.email,
            "name": customer.name,
            "phone": customer.phone,
            "description": customer.description,
            "metadata": customer.metadata,
            "created": datetime.fromtimestamp(customer.created).isoformat(),
            "default_payment_method": customer.invoice_settings.default_payment_method if customer.invoice_settings else None,
            "address": customer.address
        }
    
    def _format_payment_method(self, payment_method: stripe.PaymentMethod) -> Dict[str, Any]:
        """Format payment method for response."""
        return {
            "id": payment_method.id,
            "customer_id": payment_method.customer,
            "type": payment_method.type,
            "card": payment_method.card if hasattr(payment_method, 'card') else None,
            "billing_details": payment_method.billing_details,
            "metadata": payment_method.metadata,
            "created": datetime.fromtimestamp(payment_method.created).isoformat()
        }
    
    def _format_setup_intent(self, setup_intent: stripe.SetupIntent) -> Dict[str, Any]:
        """Format setup intent for response."""
        return {
            "id": setup_intent.id,
            "customer_id": setup_intent.customer,
            "client_secret": setup_intent.client_secret,
            "status": setup_intent.status,
            "payment_method_types": setup_intent.payment_method_types,
            "metadata": setup_intent.metadata,
            "created": datetime.fromtimestamp(setup_intent.created).isoformat()
        }
    
    def _format_subscription(self, subscription: stripe.Subscription) -> Dict[str, Any]:
        """Format subscription for response."""
        return {
            "id": subscription.id,
            "customer_id": subscription.customer,
            "status": subscription.status,
            "current_period_start": datetime.fromtimestamp(subscription.current_period_start).isoformat(),
            "current_period_end": datetime.fromtimestamp(subscription.current_period_end).isoformat(),
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "items": [
                {
                    "id": item.id,
                    "price_id": item.price.id,
                    "quantity": item.quantity
                }
                for item in subscription.items.data
            ],
            "metadata": subscription.metadata,
            "created": datetime.fromtimestamp(subscription.created).isoformat()
        }
    
    def _format_invoice(self, invoice: stripe.Invoice) -> Dict[str, Any]:
        """Format invoice for response."""
        return {
            "id": invoice.id,
            "customer_id": invoice.customer,
            "status": invoice.status,
            "amount_due": invoice.amount_due / 100,
            "amount_paid": invoice.amount_paid / 100,
            "amount_remaining": invoice.amount_remaining / 100,
            "currency": invoice.currency,
            "due_date": datetime.fromtimestamp(invoice.due_date).isoformat() if invoice.due_date else None,
            "paid": invoice.paid,
            "lines": [
                {
                    "id": line.id,
                    "description": line.description,
                    "amount": line.amount / 100
                }
                for line in invoice.lines.data
            ],
            "metadata": invoice.metadata,
            "created": datetime.fromtimestamp(invoice.created).isoformat()
        }
    
    def _format_product(self, product: stripe.Product) -> Dict[str, Any]:
        """Format product for response."""
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "active": product.active,
            "metadata": product.metadata,
            "created": datetime.fromtimestamp(product.created).isoformat()
        }
    
    def _format_price(self, price: stripe.Price) -> Dict[str, Any]:
        """Format price for response."""
        return {
            "id": price.id,
            "product_id": price.product,
            "unit_amount": price.unit_amount / 100,
            "currency": price.currency,
            "recurring": price.recurring,
            "nickname": price.nickname,
            "active": price.active,
            "metadata": price.metadata,
            "created": datetime.fromtimestamp(price.created).isoformat()
        }
    
    def _format_coupon(self, coupon: stripe.Coupon) -> Dict[str, Any]:
        """Format coupon for response."""
        return {
            "id": coupon.id,
            "name": coupon.name,
            "percent_off": coupon.percent_off,
            "amount_off": coupon.amount_off / 100 if coupon.amount_off else None,
            "currency": coupon.currency,
            "duration": coupon.duration,
            "duration_in_months": coupon.duration_in_months,
            "max_redemptions": coupon.max_redemptions,
            "redeem_by": datetime.fromtimestamp(coupon.redeem_by).isoformat() if coupon.redeem_by else None,
            "metadata": coupon.metadata,
            "created": datetime.fromtimestamp(coupon.created).isoformat()
        }
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance.
        
        Returns:
            Dict[str, Any]: Balance information
        """
        try:
            self.stats["api_calls"] += 1
            
            balance = await asyncio.to_thread(stripe.Balance.retrieve)
            
            return {
                "available": [
                    {
                        "amount": b["amount"] / 100,
                        "currency": b["currency"]
                    }
                    for b in balance.available
                ],
                "pending": [
                    {
                        "amount": b["amount"] / 100,
                        "currency": b["currency"]
                    }
                    for b in balance.pending
                ]
            }
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to retrieve balance: {e}")
            raise PaymentGatewayError(f"Balance retrieval failed: {e}")
    
    async def get_payouts(
        self,
        limit: int = 10,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get payouts.
        
        Args:
            limit: Maximum number of payouts
            status: Filter by status
            
        Returns:
            List[Dict[str, Any]]: List of payouts
        """
        try:
            self.stats["api_calls"] += 1
            
            params = {"limit": limit}
            if status:
                params["status"] = status
            
            payouts = await asyncio.to_thread(
                stripe.Payout.list,
                **params
            )
            
            return [
                {
                    "id": payout.id,
                    "amount": payout.amount / 100,
                    "currency": payout.currency,
                    "status": payout.status,
                    "arrival_date": datetime.fromtimestamp(payout.arrival_date).isoformat(),
                    "destination": payout.destination,
                    "description": payout.description
                }
                for payout in payouts.data
            ]
            
        except stripe.error.StripeError as e:
            self.stats["api_errors"] += 1
            self.logger.error(f"Failed to retrieve payouts: {e}")
            raise PaymentGatewayError(f"Payout retrieval failed: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get gateway statistics.
        
        Returns:
            Dict[str, Any]: Statistics
        """
        return {
            **self.stats,
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
            await self.get_balance()
            
            return {
                "status": "healthy",
                "gateway": "stripe",
                "api_connected": True
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "gateway": "stripe",
                "error": str(e)
            }


# Singleton instance
stripe_gateway = StripeGateway()


def get_stripe_gateway() -> StripeGateway:
    """
    Get Stripe gateway singleton.
    
    Returns:
        StripeGateway: Stripe gateway instance
    """
    return stripe_gateway