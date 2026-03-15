"""
Webhook handlers for different payment gateways.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime

from ..core.config import settings
from ..core.exceptions import WebhookError
from ..utils.logging_utils import get_logger
from ..services.payment_service import payment_service
from ..services.subscription_service import subscription_service
from ..services.notification_service import notification_service
from ..db.repositories.payment_repository import payment_repository
from ..db.repositories.subscription_repository import subscription_repository
from ..models.payment import PaymentStatus, PaymentMethod
from ..models.subscription import SubscriptionStatus
from .events import (
    WebhookEvent,
    PaymentEvent,
    SubscriptionEvent,
    RefundEvent,
    CustomerEvent,
    DisputeEvent
)


class WebhookHandler(ABC):
    """
    Abstract base class for webhook handlers.
    """
    
    def __init__(self, gateway: str):
        """
        Initialize webhook handler.
        
        Args:
            gateway: Payment gateway name
        """
        self.gateway = gateway
        self.logger = get_logger(f"{gateway}_webhook")
        
        # Register event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        self._register_default_handlers()
    
    @abstractmethod
    async def handle(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming webhook event.
        
        Args:
            event_data: Raw webhook event data
            
        Returns:
            Dict[str, Any]: Processing result
        """
        pass
    
    @abstractmethod
    def extract_event_type(self, event_data: Dict[str, Any]) -> str:
        """
        Extract event type from event data.
        
        Args:
            event_data: Event data
            
        Returns:
            str: Event type
        """
        pass
    
    @abstractmethod
    def extract_event_id(self, event_data: Dict[str, Any]) -> str:
        """
        Extract event ID from event data.
        
        Args:
            event_data: Event data
            
        Returns:
            str: Event ID
        """
        pass
    
    @abstractmethod
    def extract_timestamp(self, event_data: Dict[str, Any]) -> datetime:
        """
        Extract timestamp from event data.
        
        Args:
            event_data: Event data
            
        Returns:
            datetime: Event timestamp
        """
        pass
    
    @abstractmethod
    def transform_event(self, event_data: Dict[str, Any]) -> WebhookEvent:
        """
        Transform raw event data to standardized event.
        
        Args:
            event_data: Raw event data
            
        Returns:
            WebhookEvent: Standardized event
        """
        pass
    
    def _register_default_handlers(self):
        """Register default event handlers."""
        self.register_handler("payment.*", self.handle_payment_event)
        self.register_handler("subscription.*", self.handle_subscription_event)
        self.register_handler("refund.*", self.handle_refund_event)
        self.register_handler("customer.*", self.handle_customer_event)
        self.register_handler("dispute.*", self.handle_dispute_event)
    
    def register_handler(self, event_type: str, handler: Callable):
        """
        Register handler for event type.
        
        Args:
            event_type: Event type (can use wildcards)
            handler: Handler function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        self.logger.debug(f"Registered handler for {event_type}")
    
    async def dispatch_event(self, event: WebhookEvent) -> List[Any]:
        """
        Dispatch event to registered handlers.
        
        Args:
            event: Webhook event
            
        Returns:
            List[Any]: Handler results
        """
        results = []
        
        # Find matching handlers
        for pattern, handlers in self.event_handlers.items():
            if self._event_type_matches(event.event_type, pattern):
                for handler in handlers:
                    try:
                        result = await handler(event)
                        results.append(result)
                    except Exception as e:
                        self.logger.error(
                            f"Handler {handler.__name__} failed for event {event.event_type}: {e}",
                            exc_info=True
                        )
        
        return results
    
    def _event_type_matches(self, event_type: str, pattern: str) -> bool:
        """
        Check if event type matches pattern.
        
        Args:
            event_type: Event type
            pattern: Pattern (can contain *)
            
        Returns:
            bool: True if matches
        """
        if pattern == "*":
            return True
        
        if pattern.endswith(".*"):
            return event_type.startswith(pattern[:-2])
        
        return event_type == pattern
    
    async def handle_payment_event(self, event: PaymentEvent) -> Dict[str, Any]:
        """
        Handle payment event.
        
        Args:
            event: Payment event
            
        Returns:
            Dict[str, Any]: Handling result
        """
        self.logger.info(f"Handling payment event: {event.event_type}")
        
        result = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "handled": True
        }
        
        # Update payment in database
        if event.payment_id:
            await payment_repository.update_status(
                payment_id=event.payment_id,
                status=event.payment_status,
                gateway_response=event.raw_data
            )
            
            result["payment_id"] = event.payment_id
            result["payment_status"] = event.payment_status
        
        # Send notification
        await notification_service.send_payment_notification(event)
        
        return result
    
    async def handle_subscription_event(self, event: SubscriptionEvent) -> Dict[str, Any]:
        """
        Handle subscription event.
        
        Args:
            event: Subscription event
            
        Returns:
            Dict[str, Any]: Handling result
        """
        self.logger.info(f"Handling subscription event: {event.event_type}")
        
        result = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "handled": True
        }
        
        # Update subscription in database
        if event.subscription_id:
            await subscription_repository.update_status(
                subscription_id=event.subscription_id,
                status=event.subscription_status,
                gateway_response=event.raw_data
            )
            
            result["subscription_id"] = event.subscription_id
            result["subscription_status"] = event.subscription_status
        
        # Send notification
        await notification_service.send_subscription_notification(event)
        
        return result
    
    async def handle_refund_event(self, event: RefundEvent) -> Dict[str, Any]:
        """
        Handle refund event.
        
        Args:
            event: Refund event
            
        Returns:
            Dict[str, Any]: Handling result
        """
        self.logger.info(f"Handling refund event: {event.event_type}")
        
        result = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "handled": True
        }
        
        # Update refund in database
        if event.refund_id:
            await payment_repository.update_refund_status(
                refund_id=event.refund_id,
                status=event.refund_status,
                gateway_response=event.raw_data
            )
            
            result["refund_id"] = event.refund_id
            result["refund_status"] = event.refund_status
        
        # Send notification
        await notification_service.send_refund_notification(event)
        
        return result
    
    async def handle_customer_event(self, event: CustomerEvent) -> Dict[str, Any]:
        """
        Handle customer event.
        
        Args:
            event: Customer event
            
        Returns:
            Dict[str, Any]: Handling result
        """
        self.logger.info(f"Handling customer event: {event.event_type}")
        
        result = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "handled": True
        }
        
        # Update customer in database
        if event.customer_id:
            # Update customer data
            result["customer_id"] = event.customer_id
        
        return result
    
    async def handle_dispute_event(self, event: DisputeEvent) -> Dict[str, Any]:
        """
        Handle dispute event.
        
        Args:
            event: Dispute event
            
        Returns:
            Dict[str, Any]: Handling result
        """
        self.logger.info(f"Handling dispute event: {event.event_type}")
        
        result = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "handled": True
        }
        
        # Log dispute for manual review
        self.logger.warning(
            f"Dispute {event.dispute_id} filed for payment {event.payment_id}: {event.reason}"
        )
        
        # Send alert to admin
        await notification_service.send_admin_alert({
            "type": "dispute",
            "dispute_id": event.dispute_id,
            "payment_id": event.payment_id,
            "amount": event.amount,
            "currency": event.currency,
            "reason": event.reason
        })
        
        result["dispute_id"] = event.dispute_id
        result["payment_id"] = event.payment_id
        
        return result
    
    async def handle_unknown_event(self, event: WebhookEvent) -> Dict[str, Any]:
        """
        Handle unknown event type.
        
        Args:
            event: Webhook event
            
        Returns:
            Dict[str, Any]: Handling result
        """
        self.logger.warning(f"Unknown event type: {event.event_type}")
        
        return {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "handled": False,
            "reason": "Unknown event type"
        }


class StripeWebhookHandler(WebhookHandler):
    """
    Stripe-specific webhook handler.
    """
    
    def __init__(self):
        """Initialize Stripe webhook handler."""
        super().__init__("stripe")
    
    async def handle(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Stripe webhook event.
        """
        try:
            # Extract event info
            event_type = self.extract_event_type(event_data)
            event_id = self.extract_event_id(event_data)
            
            self.logger.info(f"Processing Stripe event: {event_type} ({event_id})")
            
            # Check for duplicate processing
            if await self._is_duplicate_event(event_id):
                self.logger.info(f"Duplicate event {event_id}, skipping")
                return {"status": "skipped", "reason": "duplicate"}
            
            # Transform to standard event
            event = self.transform_event(event_data)
            
            # Dispatch to handlers
            results = await self.dispatch_event(event)
            
            # Mark as processed
            await self._mark_event_processed(event_id)
            
            return {
                "event_id": event_id,
                "event_type": event_type,
                "status": "processed",
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Failed to handle Stripe event: {e}", exc_info=True)
            raise WebhookError(f"Stripe webhook handling failed: {e}")
    
    def extract_event_type(self, event_data: Dict[str, Any]) -> str:
        """Extract event type from Stripe event."""
        return event_data.get("type", "unknown")
    
    def extract_event_id(self, event_data: Dict[str, Any]) -> str:
        """Extract event ID from Stripe event."""
        return event_data.get("id", "")
    
    def extract_timestamp(self, event_data: Dict[str, Any]) -> datetime:
        """Extract timestamp from Stripe event."""
        created = event_data.get("created", 0)
        return datetime.fromtimestamp(created) if created else datetime.utcnow()
    
    def transform_event(self, event_data: Dict[str, Any]) -> WebhookEvent:
        """
        Transform Stripe event to standard format.
        """
        event_type = self.extract_event_type(event_data)
        event_id = self.extract_event_id(event_data)
        timestamp = self.extract_timestamp(event_data)
        data = event_data.get("data", {}).get("object", {})
        
        # Payment events
        if event_type.startswith("payment_intent."):
            return PaymentEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="stripe",
                raw_data=event_data,
                payment_id=data.get("id"),
                payment_status=self._map_payment_status(data.get("status")),
                amount=data.get("amount", 0) / 100,  # Convert from cents
                currency=data.get("currency", "").upper(),
                customer_id=data.get("customer"),
                payment_method=data.get("payment_method"),
                metadata=data.get("metadata", {})
            )
        
        # Subscription events
        elif event_type.startswith("customer.subscription"):
            return SubscriptionEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="stripe",
                raw_data=event_data,
                subscription_id=data.get("id"),
                subscription_status=self._map_subscription_status(data.get("status")),
                customer_id=data.get("customer"),
                plan_id=data.get("plan", {}).get("id"),
                current_period_start=datetime.fromtimestamp(data.get("current_period_start", 0)),
                current_period_end=datetime.fromtimestamp(data.get("current_period_end", 0)),
                cancel_at_period_end=data.get("cancel_at_period_end", False),
                metadata=data.get("metadata", {})
            )
        
        # Refund events
        elif event_type.startswith("charge.refunded"):
            return RefundEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="stripe",
                raw_data=event_data,
                refund_id=data.get("refunds", {}).get("data", [{}])[0].get("id"),
                payment_id=data.get("payment_intent"),
                amount=data.get("amount_refunded", 0) / 100,
                currency=data.get("currency", "").upper(),
                refund_status="succeeded",
                reason=data.get("refund_reason")
            )
        
        # Customer events
        elif event_type.startswith("customer."):
            return CustomerEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="stripe",
                raw_data=event_data,
                customer_id=data.get("id"),
                email=data.get("email"),
                name=data.get("name"),
                phone=data.get("phone"),
                address=data.get("address")
            )
        
        # Dispute events
        elif event_type.startswith("charge.dispute"):
            return DisputeEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="stripe",
                raw_data=event_data,
                dispute_id=data.get("id"),
                payment_id=data.get("charge"),
                amount=data.get("amount", 0) / 100,
                currency=data.get("currency", "").upper(),
                reason=data.get("reason"),
                status=data.get("status")
            )
        
        # Unknown event
        else:
            return WebhookEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="stripe",
                raw_data=event_data
            )
    
    def _map_payment_status(self, status: Optional[str]) -> Optional[PaymentStatus]:
        """Map Stripe payment status to internal status."""
        if not status:
            return None
        
        mapping = {
            "requires_payment_method": PaymentStatus.PENDING,
            "requires_confirmation": PaymentStatus.PENDING,
            "requires_action": PaymentStatus.PENDING,
            "processing": PaymentStatus.PROCESSING,
            "succeeded": PaymentStatus.SUCCEEDED,
            "canceled": PaymentStatus.CANCELED
        }
        return mapping.get(status)
    
    def _map_subscription_status(self, status: Optional[str]) -> Optional[SubscriptionStatus]:
        """Map Stripe subscription status to internal status."""
        if not status:
            return None
        
        mapping = {
            "incomplete": SubscriptionStatus.PENDING,
            "incomplete_expired": SubscriptionStatus.EXPIRED,
            "trialing": SubscriptionStatus.ACTIVE,
            "active": SubscriptionStatus.ACTIVE,
            "past_due": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELED,
            "unpaid": SubscriptionStatus.UNPAID
        }
        return mapping.get(status)
    
    async def _is_duplicate_event(self, event_id: str) -> bool:
        """Check if event was already processed."""
        # Implement duplicate check (e.g., using Redis)
        return False
    
    async def _mark_event_processed(self, event_id: str) -> None:
        """Mark event as processed."""
        # Implement marking (e.g., store in Redis)
        pass


class PayPalWebhookHandler(WebhookHandler):
    """
    PayPal-specific webhook handler.
    """
    
    def __init__(self):
        """Initialize PayPal webhook handler."""
        super().__init__("paypal")
    
    async def handle(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle PayPal webhook event.
        """
        try:
            # Extract event info
            event_type = self.extract_event_type(event_data)
            event_id = self.extract_event_id(event_data)
            
            self.logger.info(f"Processing PayPal event: {event_type} ({event_id})")
            
            # Check for duplicate processing
            if await self._is_duplicate_event(event_id):
                self.logger.info(f"Duplicate event {event_id}, skipping")
                return {"status": "skipped", "reason": "duplicate"}
            
            # Transform to standard event
            event = self.transform_event(event_data)
            
            # Dispatch to handlers
            results = await self.dispatch_event(event)
            
            # Mark as processed
            await self._mark_event_processed(event_id)
            
            return {
                "event_id": event_id,
                "event_type": event_type,
                "status": "processed",
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Failed to handle PayPal event: {e}", exc_info=True)
            raise WebhookError(f"PayPal webhook handling failed: {e}")
    
    def extract_event_type(self, event_data: Dict[str, Any]) -> str:
        """Extract event type from PayPal event."""
        return event_data.get("event_type", "unknown")
    
    def extract_event_id(self, event_data: Dict[str, Any]) -> str:
        """Extract event ID from PayPal event."""
        return event_data.get("id", "")
    
    def extract_timestamp(self, event_data: Dict[str, Any]) -> datetime:
        """Extract timestamp from PayPal event."""
        create_time = event_data.get("create_time", "")
        if create_time:
            try:
                return datetime.fromisoformat(create_time.replace('Z', '+00:00'))
            except:
                pass
        return datetime.utcnow()
    
    def transform_event(self, event_data: Dict[str, Any]) -> WebhookEvent:
        """
        Transform PayPal event to standard format.
        """
        event_type = self.extract_event_type(event_data)
        event_id = self.extract_event_id(event_data)
        timestamp = self.extract_timestamp(event_data)
        resource = event_data.get("resource", {})
        
        # Payment events
        if "PAYMENT" in event_type:
            amount = resource.get("amount", {})
            return PaymentEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="paypal",
                raw_data=event_data,
                payment_id=resource.get("id"),
                payment_status=self._map_payment_status(event_type),
                amount=float(amount.get("value", 0)),
                currency=amount.get("currency_code", ""),
                customer_id=resource.get("payer", {}).get("payer_id"),
                payment_method="paypal",
                metadata={"invoice_id": resource.get("invoice_id")}
            )
        
        # Subscription events
        elif "BILLING.SUBSCRIPTION" in event_type:
            return SubscriptionEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="paypal",
                raw_data=event_data,
                subscription_id=resource.get("id"),
                subscription_status=self._map_subscription_status(event_type),
                customer_id=resource.get("subscriber", {}).get("payer_id"),
                plan_id=resource.get("plan_id"),
                current_period_start=datetime.utcnow(),  # PayPal doesn't provide these directly
                current_period_end=datetime.utcnow(),
                metadata=resource.get("custom_id", {})
            )
        
        # Refund events
        elif "PAYMENT.CAPTURE.REFUNDED" in event_type:
            amount = resource.get("amount", {})
            return RefundEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="paypal",
                raw_data=event_data,
                refund_id=resource.get("id"),
                payment_id=resource.get("parent_payment"),
                amount=float(amount.get("value", 0)),
                currency=amount.get("currency_code", ""),
                refund_status="succeeded",
                reason=resource.get("note_to_payer")
            )
        
        # Customer events
        elif "CUSTOMER" in event_type:
            return CustomerEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="paypal",
                raw_data=event_data,
                customer_id=resource.get("id"),
                email=resource.get("email_address"),
                name=resource.get("name", {}).get("given_name"),
                phone=resource.get("phone", {}).get("phone_number", {}).get("national_number")
            )
        
        # Dispute events
        elif "CUSTOMER.DISPUTE" in event_type:
            amount = resource.get("dispute_amount", {})
            return DisputeEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="paypal",
                raw_data=event_data,
                dispute_id=resource.get("dispute_id"),
                payment_id=resource.get("transaction_id"),
                amount=float(amount.get("value", 0)),
                currency=amount.get("currency_code", ""),
                reason=resource.get("reason"),
                status=resource.get("status")
            )
        
        # Unknown event
        else:
            return WebhookEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="paypal",
                raw_data=event_data
            )
    
    def _map_payment_status(self, event_type: str) -> Optional[PaymentStatus]:
        """Map PayPal event type to payment status."""
        if "COMPLETED" in event_type:
            return PaymentStatus.SUCCEEDED
        elif "DENIED" in event_type:
            return PaymentStatus.FAILED
        elif "PENDING" in event_type:
            return PaymentStatus.PENDING
        return None
    
    def _map_subscription_status(self, event_type: str) -> Optional[SubscriptionStatus]:
        """Map PayPal event type to subscription status."""
        if "ACTIVATED" in event_type or "RE-ACTIVATED" in event_type:
            return SubscriptionStatus.ACTIVE
        elif "CANCELLED" in event_type:
            return SubscriptionStatus.CANCELED
        elif "SUSPENDED" in event_type:
            return SubscriptionStatus.PAST_DUE
        elif "EXPIRED" in event_type:
            return SubscriptionStatus.EXPIRED
        return None
    
    async def _is_duplicate_event(self, event_id: str) -> bool:
        """Check if event was already processed."""
        # Implement duplicate check
        return False
    
    async def _mark_event_processed(self, event_id: str) -> None:
        """Mark event as processed."""
        pass


class RazorpayWebhookHandler(WebhookHandler):
    """
    Razorpay-specific webhook handler.
    """
    
    def __init__(self):
        """Initialize Razorpay webhook handler."""
        super().__init__("razorpay")
    
    async def handle(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Razorpay webhook event.
        """
        try:
            # Extract event info
            event_type = self.extract_event_type(event_data)
            event_id = self.extract_event_id(event_data)
            
            self.logger.info(f"Processing Razorpay event: {event_type} ({event_id})")
            
            # Check for duplicate processing
            if await self._is_duplicate_event(event_id):
                self.logger.info(f"Duplicate event {event_id}, skipping")
                return {"status": "skipped", "reason": "duplicate"}
            
            # Transform to standard event
            event = self.transform_event(event_data)
            
            # Dispatch to handlers
            results = await self.dispatch_event(event)
            
            # Mark as processed
            await self._mark_event_processed(event_id)
            
            return {
                "event_id": event_id,
                "event_type": event_type,
                "status": "processed",
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Failed to handle Razorpay event: {e}", exc_info=True)
            raise WebhookError(f"Razorpay webhook handling failed: {e}")
    
    def extract_event_type(self, event_data: Dict[str, Any]) -> str:
        """Extract event type from Razorpay event."""
        return event_data.get("event", "unknown")
    
    def extract_event_id(self, event_data: Dict[str, Any]) -> str:
        """Extract event ID from Razorpay event."""
        return event_data.get("id", "")
    
    def extract_timestamp(self, event_data: Dict[str, Any]) -> datetime:
        """Extract timestamp from Razorpay event."""
        created_at = event_data.get("created_at", 0)
        return datetime.fromtimestamp(created_at) if created_at else datetime.utcnow()
    
    def transform_event(self, event_data: Dict[str, Any]) -> WebhookEvent:
        """
        Transform Razorpay event to standard format.
        """
        event_type = self.extract_event_type(event_data)
        event_id = self.extract_event_id(event_data)
        timestamp = self.extract_timestamp(event_data)
        payload = event_data.get("payload", {})
        
        # Payment events
        if "payment" in event_type:
            payment = payload.get("payment", {}).get("entity", {})
            amount = payment.get("amount", 0) / 100  # Convert from paise
            return PaymentEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="razorpay",
                raw_data=event_data,
                payment_id=payment.get("id"),
                payment_status=self._map_payment_status(event_type),
                amount=amount,
                currency=payment.get("currency", "INR"),
                customer_id=payment.get("customer_id"),
                payment_method=payment.get("method"),
                metadata=payment.get("notes", {})
            )
        
        # Subscription events
        elif "subscription" in event_type:
            subscription = payload.get("subscription", {}).get("entity", {})
            return SubscriptionEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="razorpay",
                raw_data=event_data,
                subscription_id=subscription.get("id"),
                subscription_status=self._map_subscription_status(event_type),
                customer_id=subscription.get("customer_id"),
                plan_id=subscription.get("plan_id"),
                current_period_start=datetime.fromtimestamp(subscription.get("current_start", 0)),
                current_period_end=datetime.fromtimestamp(subscription.get("current_end", 0)),
                metadata=subscription.get("notes", {})
            )
        
        # Refund events
        elif "refund" in event_type:
            refund = payload.get("refund", {}).get("entity", {})
            amount = refund.get("amount", 0) / 100
            return RefundEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="razorpay",
                raw_data=event_data,
                refund_id=refund.get("id"),
                payment_id=refund.get("payment_id"),
                amount=amount,
                currency=refund.get("currency", "INR"),
                refund_status="succeeded" if event_type == "refund.created" else "pending",
                reason=refund.get("notes", {}).get("reason")
            )
        
        # Customer events
        elif "customer" in event_type:
            customer = payload.get("customer", {}).get("entity", {})
            return CustomerEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="razorpay",
                raw_data=event_data,
                customer_id=customer.get("id"),
                email=customer.get("email"),
                name=customer.get("name"),
                phone=customer.get("contact"),
                address=customer.get("notes", {}).get("address")
            )
        
        # Dispute events
        elif "dispute" in event_type:
            dispute = payload.get("dispute", {}).get("entity", {})
            amount = dispute.get("amount", 0) / 100
            return DisputeEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="razorpay",
                raw_data=event_data,
                dispute_id=dispute.get("id"),
                payment_id=dispute.get("payment_id"),
                amount=amount,
                currency=dispute.get("currency", "INR"),
                reason=dispute.get("reason"),
                status=dispute.get("status")
            )
        
        # Unknown event
        else:
            return WebhookEvent(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                gateway="razorpay",
                raw_data=event_data
            )
    
    def _map_payment_status(self, event_type: str) -> Optional[PaymentStatus]:
        """Map Razorpay event type to payment status."""
        if "paid" in event_type or "captured" in event_type:
            return PaymentStatus.SUCCEEDED
        elif "failed" in event_type:
            return PaymentStatus.FAILED
        elif "pending" in event_type:
            return PaymentStatus.PENDING
        return None
    
    def _map_subscription_status(self, event_type: str) -> Optional[SubscriptionStatus]:
        """Map Razorpay event type to subscription status."""
        if "activated" in event_type:
            return SubscriptionStatus.ACTIVE
        elif "completed" in event_type:
            return SubscriptionStatus.COMPLETED
        elif "halted" in event_type or "paused" in event_type:
            return SubscriptionStatus.PAUSED
        elif "cancelled" in event_type:
            return SubscriptionStatus.CANCELED
        elif "expired" in event_type:
            return SubscriptionStatus.EXPIRED
        return None
    
    async def _is_duplicate_event(self, event_id: str) -> bool:
        """Check if event was already processed."""
        # Implement duplicate check
        return False
    
    async def _mark_event_processed(self, event_id: str) -> None:
        """Mark event as processed."""
        pass


# Factory function to get webhook handler
_handlers: Dict[str, WebhookHandler] = {}


def get_webhook_handler(gateway: str) -> WebhookHandler:
    """
    Get webhook handler for gateway.
    
    Args:
        gateway: Payment gateway name
        
    Returns:
        WebhookHandler: Webhook handler instance
        
    Raises:
        ValueError: If gateway not supported
    """
    if gateway not in _handlers:
        if gateway == "stripe":
            _handlers[gateway] = StripeWebhookHandler()
        elif gateway == "paypal":
            _handlers[gateway] = PayPalWebhookHandler()
        elif gateway == "razorpay":
            _handlers[gateway] = RazorpayWebhookHandler()
        else:
            # Generic handler for other gateways
            _handlers[gateway] = type(
                f"{gateway.capitalize()}WebhookHandler",
                (WebhookHandler,),
                {
                    "handle": lambda self, data: self._handle_generic(data),
                    "extract_event_type": lambda self, data: data.get("type", "unknown"),
                    "extract_event_id": lambda self, data: data.get("id", ""),
                    "extract_timestamp": lambda self, data: datetime.utcnow(),
                    "transform_event": lambda self, data: WebhookEvent(
                        event_id=data.get("id", ""),
                        event_type=data.get("type", "unknown"),
                        timestamp=datetime.utcnow(),
                        gateway=gateway,
                        raw_data=data
                    )
                }
            )(gateway)
    
    return _handlers[gateway]