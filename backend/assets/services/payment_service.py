"""Payment service for the parking management system.

This module handles all payment-related operations including processing,
refunds, webhooks, and integration with payment providers.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import logging
import json
import hmac
import hashlib
from decimal import Decimal, ROUND_HALF_UP

from ..models.payment import Payment, PaymentStatus, PaymentMethod, PaymentProvider, PaymentType, Currency
from ..models.reservation import Reservation, ReservationStatus
from ..models.user import User
from ..exceptions import (
    PaymentError,
    ResourceNotFoundError,
    ValidationError,
    ResourceConflictError
)
from ..constants.config import Config
from ..constants.error_codes import ErrorCodes
from ..services.notification_service import NotificationService
from ..services.audit_service import AuditService

# Configure logging
logger = logging.getLogger(__name__)

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logger.warning("Stripe SDK not available. Stripe payments will be disabled.")

try:
    import paypalrestsdk
    PAYPAL_AVAILABLE = True
except ImportError:
    PAYPAL_AVAILABLE = False
    logger.warning("PayPal SDK not available. PayPal payments will be disabled.")


class PaymentService:
    """Service for managing payments and transactions."""
    
    def __init__(
        self,
        db_session,
        cache_client=None,
        notification_service: Optional[NotificationService] = None,
        audit_service: Optional[AuditService] = None,
        stripe_api_key: Optional[str] = None,
        paypal_config: Optional[Dict[str, Any]] = None,
        webhook_secret: Optional[str] = None
    ):
        """Initialize payment service.
        
        Args:
            db_session: Database session
            cache_client: Optional cache client
            notification_service: Optional notification service
            audit_service: Optional audit service
            stripe_api_key: Stripe API key
            paypal_config: PayPal configuration
            webhook_secret: Webhook secret for signature verification
        """
        self.db = db_session
        self.cache = cache_client
        self.notification_service = notification_service
        self.audit_service = audit_service
        self.stripe_api_key = stripe_api_key
        self.paypal_config = paypal_config
        self.webhook_secret = webhook_secret
        
        # Initialize payment providers
        self._init_stripe()
        self._init_paypal()
    
    def _init_stripe(self) -> None:
        """Initialize Stripe client."""
        if STRIPE_AVAILABLE and self.stripe_api_key:
            stripe.api_key = self.stripe_api_key
            logger.info("Stripe client initialized")
    
    def _init_paypal(self) -> None:
        """Initialize PayPal client."""
        if PAYPAL_AVAILABLE and self.paypal_config:
            paypalrestsdk.configure(self.paypal_config)
            logger.info("PayPal client initialized")
    
    async def process_payment(
        self,
        user_id: int,
        reservation_id: int,
        amount: float,
        payment_method: str,
        payment_method_data: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Payment:
        """Process a payment for a reservation.
        
        Args:
            user_id: ID of the user making payment
            reservation_id: ID of the reservation
            amount: Payment amount
            payment_method: Payment method (credit_card, paypal, etc.)
            payment_method_data: Additional payment method data
            idempotency_key: Idempotency key for duplicate prevention
            metadata: Additional metadata
            
        Returns:
            Created payment object
            
        Raises:
            PaymentError: If payment processing fails
            ResourceNotFoundError: If reservation not found
            ValidationError: If payment data is invalid
        """
        # Check idempotency
        if idempotency_key:
            existing = await self._get_payment_by_idempotency_key(idempotency_key)
            if existing:
                logger.info(f"Returning existing payment for idempotency key: {idempotency_key}")
                return existing
        
        # Get reservation
        reservation = await self._get_reservation(reservation_id)
        if not reservation:
            raise ResourceNotFoundError("reservation", reservation_id)
        
        # Validate amount
        if amount <= 0:
            raise ValidationError({"amount": "Amount must be greater than 0"})
        
        if amount > reservation.balance_due + 0.01:  # Allow small rounding difference
            raise ValidationError({
                "amount": f"Amount exceeds balance due of {reservation.balance_due}"
            })
        
        # Create payment record
        payment = Payment(
            user_id=user_id,
            reservation_id=reservation_id,
            amount=amount,
            currency=Currency.USD,
            status=PaymentStatus.PENDING,
            payment_method=payment_method,
            payment_type=PaymentType.RESERVATION,
            metadata=metadata or {},
        )
        
        # Generate idempotency key if not provided
        if idempotency_key:
            payment.metadata['idempotency_key'] = idempotency_key
        
        self.db.add(payment)
        await self.db.flush()
        
        try:
            # Process with appropriate provider
            if payment_method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
                result = await self._process_card_payment(payment, payment_method_data)
            elif payment_method == PaymentMethod.PAYPAL:
                result = await self._process_paypal_payment(payment, payment_method_data)
            elif payment_method == PaymentMethod.CASH:
                result = await self._process_cash_payment(payment)
            else:
                raise ValidationError({"payment_method": f"Unsupported payment method: {payment_method}"})
            
            # Update payment with result
            payment.transaction_id = result.get('transaction_id')
            payment.provider_response = result
            payment.status = PaymentStatus.PAID
            payment.payment_date = datetime.utcnow()
            
            # Update reservation paid amount
            reservation.paid_amount = (reservation.paid_amount or 0) + amount
            if abs(reservation.paid_amount - reservation.total_amount) < 0.01:
                reservation.is_paid = True
            
            await self.db.commit()
            await self.db.refresh(payment)
            
            # Send notification
            if self.notification_service:
                await self.notification_service.send_payment_receipt(
                    user_id=user_id,
                    payment_id=payment.payment_id,
                    amount=amount,
                    invoice_number=payment.invoice_number
                )
            
            # Audit log
            if self.audit_service:
                await self.audit_service.log_action(
                    user_id=user_id,
                    action="payment_processed",
                    resource_type="payment",
                    resource_id=payment.payment_id,
                    details={
                        "amount": amount,
                        "reservation_id": reservation_id,
                        "payment_method": payment_method
                    }
                )
            
            logger.info(f"Payment processed successfully: {payment.payment_id}")
            return payment
            
        except Exception as e:
            # Mark payment as failed
            payment.status = PaymentStatus.FAILED
            payment.error_message = str(e)
            await self.db.commit()
            
            logger.error(f"Payment processing failed: {str(e)}")
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"Payment processing failed: {str(e)}"
            )
    
    async def _process_card_payment(
        self,
        payment: Payment,
        payment_method_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process credit/debit card payment via Stripe.
        
        Args:
            payment: Payment object
            payment_method_data: Card payment details
            
        Returns:
            Provider response
            
        Raises:
            PaymentError: If Stripe processing fails
        """
        if not STRIPE_AVAILABLE or not self.stripe_api_key:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                "Stripe payment processing is not available"
            )
        
        try:
            # Create payment intent
            intent_data = {
                'amount': int(payment.amount * 100),  # Convert to cents
                'currency': payment.currency.value.lower(),
                'metadata': {
                    'payment_id': payment.payment_id,
                    'reservation_id': payment.reservation_id,
                    'user_id': payment.user_id,
                }
            }
            
            # Add payment method if provided
            if payment_method_data and 'payment_method_id' in payment_method_data:
                intent_data['payment_method'] = payment_method_data['payment_method_id']
            
            # Add idempotency key if available
            if payment.metadata.get('idempotency_key'):
                intent_data['idempotency_key'] = payment.metadata['idempotency_key']
            
            # Create and confirm payment intent
            intent = stripe.PaymentIntent.create(**intent_data)
            
            # If requires confirmation, handle 3D Secure
            if intent.status == 'requires_confirmation':
                return {
                    'status': 'requires_action',
                    'client_secret': intent.client_secret,
                    'payment_intent_id': intent.id,
                    'requires_action': True
                }
            
            # Payment successful
            return {
                'status': 'succeeded',
                'transaction_id': intent.id,
                'charge_id': intent.charges.data[0].id if intent.charges.data else None,
                'payment_method': intent.payment_method,
                'amount': intent.amount / 100,
                'currency': intent.currency,
            }
            
        except stripe.error.CardError as e:
            raise PaymentError(
                ErrorCodes.PAYMENT_DECLINED[0],
                f"Card declined: {e.error.message}"
            )
        except stripe.error.RateLimitError:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                "Rate limit exceeded. Please try again later."
            )
        except stripe.error.InvalidRequestError as e:
            raise PaymentError(
                ErrorCodes.VALIDATION_ERROR[0],
                f"Invalid payment request: {e.error.message}"
            )
        except stripe.error.AuthenticationError:
            raise PaymentError(
                ErrorCodes.AUTHENTICATION_ERROR[0],
                "Payment provider authentication failed"
            )
        except stripe.error.APIConnectionError:
            raise PaymentError(
                ErrorCodes.SERVICE_UNAVAILABLE[0],
                "Network error connecting to payment provider"
            )
        except stripe.error.StripeError as e:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"Payment provider error: {str(e)}"
            )
    
    async def _process_paypal_payment(
        self,
        payment: Payment,
        payment_method_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process PayPal payment.
        
        Args:
            payment: Payment object
            payment_method_data: PayPal payment details
            
        Returns:
            Provider response
            
        Raises:
            PaymentError: If PayPal processing fails
        """
        if not PAYPAL_AVAILABLE or not self.paypal_config:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                "PayPal payment processing is not available"
            )
        
        try:
            # Create PayPal payment
            paypal_payment = paypalrestsdk.Payment({
                'intent': 'sale',
                'payer': {
                    'payment_method': 'paypal'
                },
                'transactions': [{
                    'amount': {
                        'total': str(payment.amount),
                        'currency': payment.currency.value
                    },
                    'description': f'Parking reservation #{payment.reservation_id}',
                    'invoice_number': payment.invoice_number,
                    'custom': json.dumps({
                        'payment_id': payment.payment_id,
                        'reservation_id': payment.reservation_id
                    })
                }],
                'redirect_urls': {
                    'return_url': payment_method_data.get('return_url', ''),
                    'cancel_url': payment_method_data.get('cancel_url', '')
                }
            })
            
            if paypal_payment.create():
                # Find approval URL
                approval_url = next(
                    (link.href for link in paypal_payment.links if link.rel == 'approval_url'),
                    None
                )
                
                return {
                    'status': 'requires_action',
                    'payment_id': paypal_payment.id,
                    'approval_url': approval_url,
                    'requires_action': True
                }
            else:
                raise PaymentError(
                    ErrorCodes.PAYMENT_FAILED[0],
                    f"PayPal error: {paypal_payment.error}"
                )
                
        except Exception as e:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"PayPal processing failed: {str(e)}"
            )
    
    async def _process_cash_payment(self, payment: Payment) -> Dict[str, Any]:
        """Process cash payment (manual).
        
        Args:
            payment: Payment object
            
        Returns:
            Provider response
        """
        return {
            'status': 'succeeded',
            'transaction_id': f"CASH-{payment.payment_id}",
            'note': 'Cash payment recorded manually'
        }
    
    async def confirm_payment(
        self,
        payment_id: int,
        provider_data: Dict[str, Any]
    ) -> Payment:
        """Confirm a payment after external action (3D Secure, PayPal approval).
        
        Args:
            payment_id: Payment ID
            provider_data: Provider confirmation data
            
        Returns:
            Updated payment
            
        Raises:
            PaymentError: If confirmation fails
            ResourceNotFoundError: If payment not found
        """
        payment = await self._get_payment(payment_id)
        if not payment:
            raise ResourceNotFoundError("payment", payment_id)
        
        if payment.status != PaymentStatus.PENDING:
            raise ResourceConflictError(
                "payment",
                {"message": f"Cannot confirm payment with status: {payment.status}"}
            )
        
        try:
            if payment.payment_method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
                result = await self._confirm_stripe_payment(payment, provider_data)
            elif payment.payment_method == PaymentMethod.PAYPAL:
                result = await self._confirm_paypal_payment(payment, provider_data)
            else:
                raise PaymentError(
                    ErrorCodes.PAYMENT_FAILED[0],
                    f"Unsupported payment method for confirmation: {payment.payment_method}"
                )
            
            # Update payment
            payment.status = PaymentStatus.PAID
            payment.payment_date = datetime.utcnow()
            payment.provider_response = result
            
            # Update reservation
            reservation = await self._get_reservation(payment.reservation_id)
            if reservation:
                reservation.paid_amount = (reservation.paid_amount or 0) + payment.amount
                if abs(reservation.paid_amount - reservation.total_amount) < 0.01:
                    reservation.is_paid = True
            
            await self.db.commit()
            await self.db.refresh(payment)
            
            logger.info(f"Payment confirmed: {payment_id}")
            return payment
            
        except Exception as e:
            payment.status = PaymentStatus.FAILED
            payment.error_message = str(e)
            await self.db.commit()
            
            logger.error(f"Payment confirmation failed: {str(e)}")
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"Payment confirmation failed: {str(e)}"
            )
    
    async def _confirm_stripe_payment(
        self,
        payment: Payment,
        provider_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Confirm Stripe payment after 3D Secure.
        
        Args:
            payment: Payment object
            provider_data: Stripe confirmation data
            
        Returns:
            Provider response
        """
        if not STRIPE_AVAILABLE:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                "Stripe is not available"
            )
        
        try:
            payment_intent_id = provider_data.get('payment_intent_id')
            if not payment_intent_id:
                raise PaymentError(
                    ErrorCodes.VALIDATION_ERROR[0],
                    "Missing payment_intent_id"
                )
            
            # Retrieve and confirm payment intent
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if intent.status == 'succeeded':
                return {
                    'status': 'succeeded',
                    'transaction_id': intent.id,
                    'charge_id': intent.charges.data[0].id if intent.charges.data else None,
                }
            elif intent.status == 'requires_confirmation':
                # Confirm the payment
                intent = stripe.PaymentIntent.confirm(payment_intent_id)
                if intent.status == 'succeeded':
                    return {
                        'status': 'succeeded',
                        'transaction_id': intent.id,
                        'charge_id': intent.charges.data[0].id if intent.charges.data else None,
                    }
            
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"Payment intent has status: {intent.status}"
            )
            
        except Exception as e:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"Stripe confirmation failed: {str(e)}"
            )
    
    async def _confirm_paypal_payment(
        self,
        payment: Payment,
        provider_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Confirm PayPal payment after approval.
        
        Args:
            payment: Payment object
            provider_data: PayPal confirmation data
            
        Returns:
            Provider response
        """
        if not PAYPAL_AVAILABLE:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                "PayPal is not available"
            )
        
        try:
            payment_id = provider_data.get('payment_id')
            payer_id = provider_data.get('payer_id')
            
            if not payment_id or not payer_id:
                raise PaymentError(
                    ErrorCodes.VALIDATION_ERROR[0],
                    "Missing payment_id or payer_id"
                )
            
            # Execute PayPal payment
            paypal_payment = paypalrestsdk.Payment.find(payment_id)
            
            if paypal_payment.execute({'payer_id': payer_id}):
                return {
                    'status': 'succeeded',
                    'transaction_id': paypal_payment.id,
                    'sale_id': paypal_payment.transactions[0].related_resources[0].sale.id
                }
            else:
                raise PaymentError(
                    ErrorCodes.PAYMENT_FAILED[0],
                    f"PayPal execution failed: {paypal_payment.error}"
                )
                
        except Exception as e:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"PayPal confirmation failed: {str(e)}"
            )
    
    async def refund_payment(
        self,
        payment_id: int,
        amount: Optional[float] = None,
        reason: Optional[str] = None,
        requested_by: Optional[int] = None
    ) -> Payment:
        """Refund a payment partially or fully.
        
        Args:
            payment_id: Payment ID
            amount: Amount to refund (None for full refund)
            reason: Reason for refund
            requested_by: User ID requesting refund
            
        Returns:
            Updated payment
            
        Raises:
            PaymentError: If refund fails
            ResourceNotFoundError: If payment not found
        """
        payment = await self._get_payment(payment_id)
        if not payment:
            raise ResourceNotFoundError("payment", payment_id)
        
        if not payment.can_refund:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                "Payment cannot be refunded"
            )
        
        refund_amount = amount if amount is not None else payment.refundable_amount
        
        if refund_amount > payment.refundable_amount:
            raise ValidationError({
                "amount": f"Refund amount exceeds refundable amount of {payment.refundable_amount}"
            })
        
        try:
            # Process refund with provider
            if payment.payment_method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
                provider_response = await self._refund_stripe_payment(payment, refund_amount)
            elif payment.payment_method == PaymentMethod.PAYPAL:
                provider_response = await self._refund_paypal_payment(payment, refund_amount)
            else:
                # Manual refund
                provider_response = {
                    'status': 'succeeded',
                    'refund_id': f"REFUND-{payment.payment_id}-{datetime.utcnow().timestamp()}"
                }
            
            # Update payment
            payment.process_refund(refund_amount, reason)
            payment.provider_response = provider_response
            
            # Update reservation
            reservation = await self._get_reservation(payment.reservation_id)
            if reservation:
                reservation.paid_amount = max(0, (reservation.paid_amount or 0) - refund_amount)
                reservation.is_paid = reservation.paid_amount >= reservation.total_amount - 0.01
            
            await self.db.commit()
            await self.db.refresh(payment)
            
            # Send notification
            if self.notification_service:
                await self.notification_service.send_refund_notification(
                    user_id=payment.user_id,
                    payment_id=payment.payment_id,
                    amount=refund_amount,
                    reason=reason
                )
            
            # Audit log
            if self.audit_service and requested_by:
                await self.audit_service.log_action(
                    user_id=requested_by,
                    action="payment_refunded",
                    resource_type="payment",
                    resource_id=payment.payment_id,
                    details={
                        "amount": refund_amount,
                        "reason": reason,
                        "original_payment_id": payment_id
                    }
                )
            
            logger.info(f"Payment refunded: {payment_id}, amount: {refund_amount}")
            return payment
            
        except Exception as e:
            logger.error(f"Refund failed: {str(e)}")
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"Refund failed: {str(e)}"
            )
    
    async def _refund_stripe_payment(
        self,
        payment: Payment,
        amount: float
    ) -> Dict[str, Any]:
        """Refund a Stripe payment.
        
        Args:
            payment: Payment object
            amount: Amount to refund
            
        Returns:
            Provider response
        """
        if not STRIPE_AVAILABLE:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                "Stripe is not available"
            )
        
        try:
            charge_id = payment.provider_response.get('charge_id')
            if not charge_id:
                # Try to get from transaction_id
                charge_id = payment.transaction_id
            
            refund_params = {
                'charge': charge_id,
                'amount': int(amount * 100),  # Convert to cents
            }
            
            if payment.metadata.get('idempotency_key'):
                refund_params['idempotency_key'] = f"refund-{payment.metadata['idempotency_key']}"
            
            refund = stripe.Refund.create(**refund_params)
            
            return {
                'status': 'succeeded',
                'refund_id': refund.id,
                'amount': refund.amount / 100,
                'currency': refund.currency,
            }
            
        except Exception as e:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"Stripe refund failed: {str(e)}"
            )
    
    async def _refund_paypal_payment(
        self,
        payment: Payment,
        amount: float
    ) -> Dict[str, Any]:
        """Refund a PayPal payment.
        
        Args:
            payment: Payment object
            amount: Amount to refund
            
        Returns:
            Provider response
        """
        if not PAYPAL_AVAILABLE:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                "PayPal is not available"
            )
        
        try:
            sale_id = payment.provider_response.get('sale_id')
            if not sale_id:
                # Try to get from transaction_id
                sale_id = payment.transaction_id
            
            sale = paypalrestsdk.Sale.find(sale_id)
            
            refund_params = {
                'amount': {
                    'total': str(amount),
                    'currency': payment.currency.value
                }
            }
            
            refund = sale.refund(refund_params)
            
            if refund.success():
                return {
                    'status': 'succeeded',
                    'refund_id': refund.id,
                    'amount': amount,
                }
            else:
                raise PaymentError(
                    ErrorCodes.PAYMENT_FAILED[0],
                    f"PayPal refund failed: {refund.error}"
                )
                
        except Exception as e:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"PayPal refund failed: {str(e)}"
            )
    
    async def handle_webhook(
        self,
        provider: str,
        payload: bytes,
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle webhook from payment provider.
        
        Args:
            provider: Payment provider (stripe, paypal)
            payload: Raw webhook payload
            signature: Webhook signature for verification
            
        Returns:
            Webhook handling result
            
        Raises:
            PaymentError: If webhook handling fails
        """
        if provider == 'stripe':
            return await self._handle_stripe_webhook(payload, signature)
        elif provider == 'paypal':
            return await self._handle_paypal_webhook(payload)
        else:
            raise PaymentError(
                ErrorCodes.VALIDATION_ERROR[0],
                f"Unsupported webhook provider: {provider}"
            )
    
    async def _handle_stripe_webhook(
        self,
        payload: bytes,
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle Stripe webhook.
        
        Args:
            payload: Raw webhook payload
            signature: Stripe signature
            
        Returns:
            Webhook handling result
        """
        if not STRIPE_AVAILABLE or not self.webhook_secret:
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                "Stripe webhook handling not configured"
            )
        
        try:
            # Verify signature
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            # Handle event types
            if event['type'] == 'payment_intent.succeeded':
                await self._handle_payment_succeeded(event['data']['object'])
            elif event['type'] == 'payment_intent.payment_failed':
                await self._handle_payment_failed(event['data']['object'])
            elif event['type'] == 'charge.refunded':
                await self._handle_charge_refunded(event['data']['object'])
            elif event['type'] == 'charge.dispute.created':
                await self._handle_dispute_created(event['data']['object'])
            
            return {
                'status': 'processed',
                'event_type': event['type'],
                'event_id': event['id']
            }
            
        except stripe.error.SignatureVerificationError:
            raise PaymentError(
                ErrorCodes.AUTHENTICATION_ERROR[0],
                "Invalid webhook signature"
            )
        except Exception as e:
            logger.error(f"Stripe webhook handling failed: {str(e)}")
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"Webhook handling failed: {str(e)}"
            )
    
    async def _handle_paypal_webhook(self, payload: bytes) -> Dict[str, Any]:
        """Handle PayPal webhook.
        
        Args:
            payload: Raw webhook payload
            
        Returns:
            Webhook handling result
        """
        try:
            data = json.loads(payload)
            event_type = data.get('event_type')
            
            if event_type == 'PAYMENT.SALE.COMPLETED':
                await self._handle_paypal_sale_completed(data)
            elif event_type == 'PAYMENT.SALE.REFUNDED':
                await self._handle_paypal_sale_refunded(data)
            
            return {
                'status': 'processed',
                'event_type': event_type,
                'event_id': data.get('id')
            }
            
        except Exception as e:
            logger.error(f"PayPal webhook handling failed: {str(e)}")
            raise PaymentError(
                ErrorCodes.PAYMENT_FAILED[0],
                f"Webhook handling failed: {str(e)}"
            )
    
    async def _handle_payment_succeeded(self, payment_intent: Dict[str, Any]) -> None:
        """Handle successful payment intent.
        
        Args:
            payment_intent: Payment intent data
        """
        payment_id = payment_intent['metadata'].get('payment_id')
        if payment_id:
            payment = await self._get_payment(int(payment_id))
            if payment and payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.PAID
                payment.payment_date = datetime.utcnow()
                await self.db.commit()
                logger.info(f"Payment marked as paid via webhook: {payment_id}")
    
    async def _handle_payment_failed(self, payment_intent: Dict[str, Any]) -> None:
        """Handle failed payment intent.
        
        Args:
            payment_intent: Payment intent data
        """
        payment_id = payment_intent['metadata'].get('payment_id')
        if payment_id:
            payment = await self._get_payment(int(payment_id))
            if payment:
                payment.status = PaymentStatus.FAILED
                payment.error_message = payment_intent.get('last_payment_error', {}).get('message')
                await self.db.commit()
                logger.info(f"Payment marked as failed via webhook: {payment_id}")
    
    async def _handle_charge_refunded(self, charge: Dict[str, Any]) -> None:
        """Handle refunded charge.
        
        Args:
            charge: Charge data
        """
        # Find payment by charge ID
        payment = await self.db.query(Payment).filter(
            Payment.provider_response['charge_id'].astext == charge['id']
        ).first()
        
        if payment:
            refund_amount = charge['amount_refunded'] / 100
            payment.refunded_amount = refund_amount
            payment.status = PaymentStatus.REFUNDED if refund_amount >= payment.amount else PaymentStatus.PARTIALLY_REFUNDED
            await self.db.commit()
            logger.info(f"Payment refunded via webhook: {payment.payment_id}")
    
    async def _handle_dispute_created(self, dispute: Dict[str, Any]) -> None:
        """Handle dispute creation.
        
        Args:
            dispute: Dispute data
        """
        # Find payment by charge ID
        charge_id = dispute['charge']
        payment = await self.db.query(Payment).filter(
            Payment.provider_response['charge_id'].astext == charge_id
        ).first()
        
        if payment:
            # Log dispute for manual handling
            if self.audit_service:
                await self.audit_service.log_action(
                    user_id=None,
                    action="payment_dispute_created",
                    resource_type="payment",
                    resource_id=payment.payment_id,
                    details={
                        "dispute_id": dispute['id'],
                        "reason": dispute['reason'],
                        "amount": dispute['amount'] / 100
                    }
                )
            logger.warning(f"Dispute created for payment: {payment.payment_id}")
    
    async def _handle_paypal_sale_completed(self, data: Dict[str, Any]) -> None:
        """Handle PayPal sale completed webhook.
        
        Args:
            data: Webhook data
        """
        # Extract payment ID from custom field
        resource = data.get('resource', {})
        custom = resource.get('custom')
        
        if custom:
            try:
                custom_data = json.loads(custom)
                payment_id = custom_data.get('payment_id')
                if payment_id:
                    payment = await self._get_payment(payment_id)
                    if payment and payment.status == PaymentStatus.PENDING:
                        payment.status = PaymentStatus.PAID
                        payment.payment_date = datetime.utcnow()
                        await self.db.commit()
                        logger.info(f"PayPal payment completed: {payment_id}")
            except Exception as e:
                logger.error(f"Error processing PayPal sale completed: {e}")
    
    async def _handle_paypal_sale_refunded(self, data: Dict[str, Any]) -> None:
        """Handle PayPal sale refunded webhook.
        
        Args:
            data: Webhook data
        """
        resource = data.get('resource', {})
        sale_id = resource.get('sale_id')
        
        if sale_id:
            payment = await self.db.query(Payment).filter(
                Payment.transaction_id == sale_id
            ).first()
            
            if payment:
                refund_amount = float(resource.get('total_amount', {}).get('value', 0))
                payment.refunded_amount = refund_amount
                payment.status = PaymentStatus.REFUNDED if refund_amount >= payment.amount else PaymentStatus.PARTIALLY_REFUNDED
                await self.db.commit()
                logger.info(f"PayPal payment refunded: {payment.payment_id}")
    
    async def get_payment(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID.
        
        Args:
            payment_id: Payment ID
            
        Returns:
            Payment if found, None otherwise
        """
        # Try cache first
        if self.cache:
            cached = await self.cache.get(f"payment:{payment_id}")
            if cached:
                return Payment.from_dict(cached)
        
        # Get from database
        payment = await self.db.query(Payment).filter(
            Payment.payment_id == payment_id
        ).first()
        
        # Cache result
        if payment and self.cache:
            await self.cache.set(
                f"payment:{payment_id}",
                payment.to_dict(),
                ex=3600  # 1 hour cache
            )
        
        return payment
    
    async def get_user_payments(
        self,
        user_id: int,
        status: Optional[PaymentStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Payment], int]:
        """Get payments for a user.
        
        Args:
            user_id: User ID
            status: Filter by status
            limit: Result limit
            offset: Result offset
            
        Returns:
            Tuple of (payments, total_count)
        """
        query = self.db.query(Payment).filter(Payment.user_id == user_id)
        
        if status:
            query = query.filter(Payment.status == status)
        
        total = await query.count()
        payments = await query.order_by(
            Payment.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        return payments, total
    
    async def get_reservation_payments(
        self,
        reservation_id: int
    ) -> List[Payment]:
        """Get all payments for a reservation.
        
        Args:
            reservation_id: Reservation ID
            
        Returns:
            List of payments
        """
        return await self.db.query(Payment).filter(
            Payment.reservation_id == reservation_id
        ).order_by(Payment.created_at.desc()).all()
    
    async def get_payment_by_transaction_id(
        self,
        transaction_id: str
    ) -> Optional[Payment]:
        """Get payment by transaction ID.
        
        Args:
            transaction_id: External transaction ID
            
        Returns:
            Payment if found, None otherwise
        """
        return await self.db.query(Payment).filter(
            Payment.transaction_id == transaction_id
        ).first()
    
    async def _get_payment(self, payment_id: int) -> Optional[Payment]:
        """Internal method to get payment by ID."""
        return await self.db.query(Payment).filter(
            Payment.payment_id == payment_id
        ).first()
    
    async def _get_reservation(self, reservation_id: int) -> Optional[Reservation]:
        """Internal method to get reservation by ID."""
        return await self.db.query(Reservation).filter(
            Reservation.reservation_id == reservation_id
        ).first()
    
    async def _get_payment_by_idempotency_key(self, key: str) -> Optional[Payment]:
        """Get payment by idempotency key."""
        return await self.db.query(Payment).filter(
            Payment.metadata['idempotency_key'].astext == key
        ).first()
    
    async def calculate_payment_summary(
        self,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate payment summary for a user.
        
        Args:
            user_id: User ID
            start_date: Start date for summary
            end_date: End date for summary
            
        Returns:
            Payment summary
        """
        query = self.db.query(Payment).filter(Payment.user_id == user_id)
        
        if start_date:
            query = query.filter(Payment.created_at >= start_date)
        if end_date:
            query = query.filter(Payment.created_at <= end_date)
        
        payments = await query.all()
        
        total_paid = sum(p.amount for p in payments if p.is_successful)
        total_refunded = sum(p.refunded_amount for p in payments)
        total_pending = sum(p.amount for p in payments if p.is_pending)
        total_failed = sum(p.amount for p in payments if p.is_failed)
        
        return {
            'user_id': user_id,
            'period': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            },
            'totals': {
                'total_paid': total_paid,
                'total_refunded': total_refunded,
                'net_paid': total_paid - total_refunded,
                'total_pending': total_pending,
                'total_failed': total_failed,
            },
            'counts': {
                'successful': len([p for p in payments if p.is_successful]),
                'pending': len([p for p in payments if p.is_pending]),
                'failed': len([p for p in payments if p.is_failed]),
                'refunded': len([p for p in payments if p.is_refunded]),
                'total': len(payments),
            }
        }
    
    async def generate_receipt(self, payment_id: int) -> Dict[str, Any]:
        """Generate a payment receipt.
        
        Args:
            payment_id: Payment ID
            
        Returns:
            Receipt data
            
        Raises:
            ResourceNotFoundError: If payment not found
        """
        payment = await self.get_payment(payment_id)
        if not payment:
            raise ResourceNotFoundError("payment", payment_id)
        
        reservation = await self._get_reservation(payment.reservation_id)
        user = await self.db.query(User).filter(User.user_id == payment.user_id).first()
        
        receipt = payment.generate_receipt()
        
        # Add additional details
        receipt.update({
            'customer': {
                'name': user.full_name if user else None,
                'email': user.email if user else None,
                'phone': user.phone if user else None,
            },
            'reservation': {
                'id': reservation.reservation_id if reservation else None,
                'start_time': reservation.start_time.isoformat() if reservation else None,
                'end_time': reservation.end_time.isoformat() if reservation else None,
            } if reservation else None,
            'company': {
                'name': Config.APP_NAME,
                'support_email': 'support@parking.com',
                'support_phone': '+1-800-PARKING',
            }
        })
        
        return receipt
    
    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: Optional[str] = None
    ) -> bool:
        """Verify webhook signature.
        
        Args:
            payload: Raw payload
            signature: Signature to verify
            secret: Secret key (uses webhook_secret if not provided)
            
        Returns:
            True if signature is valid
        """
        secret = secret or self.webhook_secret
        if not secret:
            logger.warning("No webhook secret configured")
            return False
        
        expected = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on payment service.
        
        Returns:
            Health check results
        """
        status = {
            'service': 'payment_service',
            'status': 'healthy',
            'providers': {}
        }
        
        # Check Stripe
        if STRIPE_AVAILABLE and self.stripe_api_key:
            try:
                # Simple API call to check connectivity
                stripe.Account.retrieve()
                status['providers']['stripe'] = 'healthy'
            except Exception as e:
                status['providers']['stripe'] = 'unhealthy'
                status['status'] = 'degraded'
                logger.warning(f"Stripe health check failed: {e}")
        else:
            status['providers']['stripe'] = 'not_configured'
        
        # Check PayPal
        if PAYPAL_AVAILABLE and self.paypal_config:
            try:
                # Simple API call to check connectivity
                paypalrestsdk.Webhook.all()
                status['providers']['paypal'] = 'healthy'
            except Exception as e:
                status['providers']['paypal'] = 'unhealthy'
                status['status'] = 'degraded'
                logger.warning(f"PayPal health check failed: {e}")
        else:
            status['providers']['paypal'] = 'not_configured'
        
        return status