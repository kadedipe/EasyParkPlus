# parking-management/data/migrations/repositories/payment_repository.py
"""
Payment repository module for the parking management system.

This module provides repository classes for managing payments, transactions,
invoices, refunds, disputes, and subscriptions with comprehensive integration
with the enum definitions.
"""

from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
import json
import hashlib
import hmac
import secrets
from uuid import uuid4

from sqlalchemy import (
    and_, or_, not_, desc, asc, func, select,
    update, delete, between, cast, Float, Integer,
    String, DateTime, Boolean, Numeric, Interval,
    Date
)
from sqlalchemy.orm import Session, Query, joinedload, selectinload
from sqlalchemy.sql import expression

from .base_repository import (
    BaseRepository,
    AuditableRepository,
    CacheableRepository,
    SearchableRepository,
    FullFeatureRepository,
    EntityNotFoundException,
    DuplicateEntityException,
    ValidationException,
    RepositoryException,
    QueryBuilder
)
from ..models.enums import (
    # Payment enums
    PaymentMethodType,
    PaymentProvider,
    TransactionType,
    DisputeStatus,
    DisputeReason,
    SubscriptionStatus,
    SubscriptionInterval,
    InvoiceStatus,
    DiscountType,
    DiscountApplyTo,
    FeeType,
    Currency,
    
    # Reservation enums
    PaymentStatus,
    
    # Audit enums
    AuditAction,
    AuditStatus,
    AuditSeverity,
    AuditCategory,
    AuditResourceType,
    
    # General enums
    CountryCode
)
from ..models.payment_models import (
    # Payment models
    Payment,
    PaymentMethod,
    PaymentTransaction,
    Refund,
    Dispute,
    
    # Invoice models
    Invoice,
    InvoiceItem,
    InvoiceLine,
    
    # Subscription models
    Subscription,
    SubscriptionPlan,
    SubscriptionHistory,
    
    # Discount models
    Discount,
    Coupon,
    Promotion,
    DiscountUsage,
    
    # Fee models
    Fee,
    FeeSchedule,
    FeeCalculation,
    
    # Tax models
    TaxRate,
    TaxCalculation,
    
    # Receipt models
    Receipt,
    ReceiptItem
)
from ..models.reservation_models import (
    Reservation,
    ReservationPayment
)
from ..models.user_models import (
    User
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class PaymentNotFoundException(EntityNotFoundException):
    """Raised when a payment is not found."""
    def __init__(self, payment_id: Any):
        super().__init__("Payment", payment_id)


class PaymentFailedException(RepositoryException):
    """Raised when a payment fails."""
    def __init__(self, message: str, provider_response: Optional[Dict] = None):
        self.provider_response = provider_response
        super().__init__(f"Payment failed: {message}")


class PaymentDeclinedException(RepositoryException):
    """Raised when a payment is declined."""
    def __init__(self, reason: str, decline_code: Optional[str] = None):
        self.reason = reason
        self.decline_code = decline_code
        super().__init__(f"Payment declined: {reason}")


class InsufficientFundsException(PaymentDeclinedException):
    """Raised when payment fails due to insufficient funds."""
    def __init__(self):
        super().__init__("Insufficient funds", "insufficient_funds")


class InvalidPaymentMethodException(RepositoryException):
    """Raised when payment method is invalid."""
    def __init__(self, message: str):
        super().__init__(f"Invalid payment method: {message}")


class DuplicateTransactionException(RepositoryException):
    """Raised when a duplicate transaction is detected."""
    def __init__(self, transaction_id: str):
        self.transaction_id = transaction_id
        super().__init__(f"Duplicate transaction detected: {transaction_id}")


class RefundFailedException(RepositoryException):
    """Raised when a refund fails."""
    def __init__(self, message: str):
        super().__init__(f"Refund failed: {message}")


class RefundAmountExceededException(RepositoryException):
    """Raised when refund amount exceeds payment amount."""
    def __init__(self, payment_amount: Decimal, refund_amount: Decimal):
        self.payment_amount = payment_amount
        self.refund_amount = refund_amount
        super().__init__(
            f"Refund amount {refund_amount} exceeds payment amount {payment_amount}"
        )


class DisputeNotFoundException(EntityNotFoundException):
    """Raised when a dispute is not found."""
    def __init__(self, dispute_id: Any):
        super().__init__("Dispute", dispute_id)


class SubscriptionNotFoundException(EntityNotFoundException):
    """Raised when a subscription is not found."""
    def __init__(self, subscription_id: Any):
        super().__init__("Subscription", subscription_id)


class SubscriptionAlreadyActiveException(RepositoryException):
    """Raised when trying to create an active subscription that already exists."""
    def __init__(self, user_id: int, plan_id: int):
        self.user_id = user_id
        self.plan_id = plan_id
        super().__init__(f"User {user_id} already has an active subscription to plan {plan_id}")


class InvoiceNotFoundException(EntityNotFoundException):
    """Raised when an invoice is not found."""
    def __init__(self, invoice_id: Any):
        super().__init__("Invoice", invoice_id)


class InvalidDiscountException(RepositoryException):
    """Raised when a discount is invalid."""
    def __init__(self, message: str):
        super().__init__(f"Invalid discount: {message}")


class DiscountExpiredException(InvalidDiscountException):
    """Raised when a discount has expired."""
    def __init__(self, discount_code: str):
        super().__init__(f"Discount {discount_code} has expired")


class DiscountLimitReachedException(InvalidDiscountException):
    """Raised when a discount has reached its usage limit."""
    def __init__(self, discount_code: str):
        super().__init__(f"Discount {discount_code} has reached its usage limit")


# ============================================================================
# Payment Repository
# ============================================================================

class PaymentRepository(FullFeatureRepository[Payment, int]):
    """
    Repository for Payment entity with comprehensive payment processing features.
    
    This repository provides methods for payment CRUD operations,
    transaction processing, refunds, and dispute management.
    """
    
    def __init__(self, session: Session):
        super().__init__(session, Payment)
        self.searchable_fields = ['transaction_id', 'description']
        
        # Payment provider configuration
        self.supported_providers = [
            PaymentProvider.STRIPE,
            PaymentProvider.PAYPAL,
            PaymentProvider.BRAINTREE,
            PaymentProvider.SQUARE
        ]
        
        # Retry configuration
        self.max_retry_attempts = 3
        self.retry_delay_seconds = 5
    
    # ========================================================================
    # Custom Query Methods
    # ========================================================================
    
    def get_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        """
        Get payment by transaction ID.
        
        Args:
            transaction_id: Provider transaction ID
            
        Returns:
            Payment if found, None otherwise
        """
        return (
            self.session.query(Payment)
            .filter(Payment.transaction_id == transaction_id)
            .first()
        )
    
    def get_by_invoice(self, invoice_id: int) -> Optional[Payment]:
        """
        Get payment by invoice ID.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Payment if found, None otherwise
        """
        return (
            self.session.query(Payment)
            .filter(Payment.invoice_id == invoice_id)
            .first()
        )
    
    def get_user_payments(
        self,
        user_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        statuses: Optional[List[PaymentStatus]] = None,
        limit: int = 100
    ) -> List[Payment]:
        """
        Get payments for a user.
        
        Args:
            user_id: User ID
            from_date: Optional start date
            to_date: Optional end date
            statuses: Optional status filter
            limit: Maximum number to return
            
        Returns:
            List of user's payments
        """
        query = self.session.query(Payment).filter(
            Payment.user_id == user_id
        )
        
        if from_date:
            query = query.filter(Payment.created_at >= from_date)
        
        if to_date:
            query = query.filter(Payment.created_at <= to_date)
        
        if statuses:
            query = query.filter(Payment.status.in_(statuses))
        
        return query.order_by(desc(Payment.created_at)).limit(limit).all()
    
    def get_payments_by_date_range(
        self,
        from_date: datetime,
        to_date: datetime,
        statuses: Optional[List[PaymentStatus]] = None
    ) -> List[Payment]:
        """
        Get payments within a date range.
        
        Args:
            from_date: Start date
            to_date: End date
            statuses: Optional status filter
            
        Returns:
            List of payments
        """
        query = self.session.query(Payment).filter(
            Payment.created_at.between(from_date, to_date)
        )
        
        if statuses:
            query = query.filter(Payment.status.in_(statuses))
        
        return query.order_by(Payment.created_at).all()
    
    def get_pending_payments(
        self,
        older_than_minutes: int = 30
    ) -> List[Payment]:
        """
        Get payments that have been pending for too long.
        
        Args:
            older_than_minutes: Minutes threshold
            
        Returns:
            List of pending payments
        """
        cutoff = datetime.utcnow() - timedelta(minutes=older_than_minutes)
        
        return (
            self.session.query(Payment)
            .filter(
                Payment.status == PaymentStatus.PENDING,
                Payment.created_at <= cutoff
            )
            .all()
        )
    
    def get_failed_payments(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Payment]:
        """
        Get failed payments.
        
        Args:
            from_date: Optional start date
            to_date: Optional end date
            
        Returns:
            List of failed payments
        """
        query = self.session.query(Payment).filter(
            Payment.status.in_(PaymentStatus.get_failed_statuses())
        )
        
        if from_date:
            query = query.filter(Payment.created_at >= from_date)
        
        if to_date:
            query = query.filter(Payment.created_at <= to_date)
        
        return query.order_by(desc(Payment.created_at)).all()
    
    def get_payment_statistics(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get payment statistics.
        
        Args:
            from_date: Optional start date
            to_date: Optional end date
            
        Returns:
            Dictionary with payment statistics
        """
        query = self.session.query(Payment)
        
        if from_date:
            query = query.filter(Payment.created_at >= from_date)
        
        if to_date:
            query = query.filter(Payment.created_at <= to_date)
        
        # Total amounts by status
        successful_payments = query.filter(
            Payment.status.in_(PaymentStatus.get_successful_statuses())
        ).all()
        
        total_successful = sum(p.amount for p in successful_payments)
        total_count = query.count()
        successful_count = len(successful_payments)
        
        # Amount by currency
        amounts_by_currency = {}
        for payment in successful_payments:
            currency = payment.currency.value
            if currency not in amounts_by_currency:
                amounts_by_currency[currency] = 0
            amounts_by_currency[currency] += payment.amount
        
        # Average payment amount
        avg_amount = total_successful / successful_count if successful_count > 0 else 0
        
        # Payment methods distribution
        method_counts = {}
        for payment in query.all():
            method = payment.payment_method.value
            method_counts[method] = method_counts.get(method, 0) + 1
        
        return {
            'total_amount': float(total_successful),
            'total_count': total_count,
            'successful_count': successful_count,
            'failed_count': total_count - successful_count,
            'average_amount': float(avg_amount),
            'by_currency': {k: float(v) for k, v in amounts_by_currency.items()},
            'by_method': method_counts,
            'success_rate': round(successful_count / total_count * 100, 2) if total_count > 0 else 0
        }
    
    # ========================================================================
    # Payment Processing Methods
    # ========================================================================
    
    def create_payment(
        self,
        user_id: int,
        amount: Decimal,
        currency: Currency,
        payment_method_id: int,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        **kwargs
    ) -> Payment:
        """
        Create a new payment.
        
        Args:
            user_id: User ID
            amount: Payment amount
            currency: Payment currency
            payment_method_id: Payment method ID
            description: Optional description
            metadata: Optional metadata
            **kwargs: Additional payment attributes
            
        Returns:
            Created payment
        """
        # Get payment method
        payment_method = self.session.query(PaymentMethod).get(payment_method_id)
        if not payment_method:
            raise EntityNotFoundException("PaymentMethod", payment_method_id)
        
        # Verify payment method belongs to user
        if payment_method.user_id != user_id:
            raise ValidationException(
                "Payment",
                {"payment_method_id": ["Payment method does not belong to user"]}
            )
        
        # Generate transaction ID
        transaction_id = self._generate_transaction_id()
        
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency,
            payment_method_id=payment_method_id,
            payment_method_type=payment_method.method_type,
            transaction_id=transaction_id,
            status=PaymentStatus.PENDING,
            description=description,
            metadata=metadata or {},
            **kwargs
        )
        
        payment = self.create(payment)
        
        logger.info(f"Created payment {payment.id} for user {user_id}, amount {amount} {currency.value}")
        return payment
    
    def process_payment(
        self,
        payment_id: int,
        provider: Optional[PaymentProvider] = None,
        idempotency_key: Optional[str] = None
    ) -> Payment:
        """
        Process a payment with the payment provider.
        
        Args:
            payment_id: Payment ID
            provider: Optional provider override
            idempotency_key: Optional idempotency key
            
        Returns:
            Updated payment
            
        Raises:
            PaymentNotFoundException: If payment not found
            PaymentFailedException: If payment processing fails
        """
        payment = self.get_or_fail(payment_id)
        
        if payment.status != PaymentStatus.PENDING:
            raise InvalidReservationStateException(
                payment_id,
                payment.status,
                "process"
            )
        
        # Get payment method
        payment_method = self.session.query(PaymentMethod).get(payment.payment_method_id)
        if not payment_method:
            raise InvalidPaymentMethodException("Payment method not found")
        
        # Select provider
        provider = provider or payment_method.preferred_provider or self._select_provider(payment_method)
        
        # Create idempotency key if not provided
        if not idempotency_key:
            idempotency_key = f"payment_{payment.id}_{secrets.token_hex(8)}"
        
        try:
            # Process with provider (this would call external API)
            provider_response = self._call_payment_provider(
                provider,
                payment_method,
                payment.amount,
                payment.currency,
                idempotency_key
            )
            
            # Update payment with provider response
            payment.provider = provider
            payment.provider_transaction_id = provider_response.get('transaction_id')
            payment.provider_response = provider_response
            payment.processed_at = datetime.utcnow()
            
            if provider_response.get('success'):
                payment.status = PaymentStatus.AUTHORIZED
                payment.authorization_code = provider_response.get('authorization_code')
                
                # Create transaction record
                self._create_transaction(
                    payment_id=payment.id,
                    transaction_type=TransactionType.AUTHORIZATION,
                    amount=payment.amount,
                    provider=provider,
                    provider_transaction_id=payment.provider_transaction_id,
                    response=provider_response
                )
                
                logger.info(f"Payment {payment_id} authorized successfully")
            else:
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = provider_response.get('error_message')
                payment.failure_code = provider_response.get('error_code')
                
                # Create failed transaction record
                self._create_transaction(
                    payment_id=payment.id,
                    transaction_type=TransactionType.SALE,
                    amount=payment.amount,
                    provider=provider,
                    provider_transaction_id=payment.provider_transaction_id,
                    status=PaymentStatus.FAILED,
                    response=provider_response
                )
                
                logger.warning(f"Payment {payment_id} failed: {payment.failure_reason}")
                
                raise PaymentFailedException(
                    payment.failure_reason or "Unknown error",
                    provider_response
                )
        
        except Exception as e:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = str(e)
            payment.failure_code = 'system_error'
            payment.metadata = payment.metadata or {}
            payment.metadata['error_details'] = {
                'type': type(e).__name__,
                'message': str(e)
            }
            
            self.session.flush()
            
            logger.error(f"Payment {payment_id} processing error: {e}", exc_info=True)
            raise PaymentFailedException(str(e))
        
        payment = self.update_entity(payment)
        return payment
    
    def capture_payment(
        self,
        payment_id: int,
        amount: Optional[Decimal] = None
    ) -> Payment:
        """
        Capture an authorized payment.
        
        Args:
            payment_id: Payment ID
            amount: Optional amount to capture (partial capture)
            
        Returns:
            Updated payment
        """
        payment = self.get_or_fail(payment_id)
        
        if payment.status != PaymentStatus.AUTHORIZED:
            raise InvalidReservationStateException(
                payment_id,
                payment.status,
                "capture"
            )
        
        capture_amount = amount or payment.amount
        
        if capture_amount > payment.amount:
            raise ValidationException(
                "Payment",
                {"amount": ["Capture amount cannot exceed authorized amount"]}
            )
        
        try:
            # Call provider to capture
            provider_response = self._call_provider_capture(
                payment.provider,
                payment.provider_transaction_id,
                capture_amount
            )
            
            # Update payment
            payment.status = PaymentStatus.PAID if capture_amount >= payment.amount else PaymentStatus.PARTIALLY_PAID
            payment.captured_at = datetime.utcnow()
            payment.captured_amount = (payment.captured_amount or 0) + capture_amount
            
            # Create transaction record
            self._create_transaction(
                payment_id=payment.id,
                transaction_type=TransactionType.CAPTURE,
                amount=capture_amount,
                provider=payment.provider,
                provider_transaction_id=provider_response.get('transaction_id'),
                response=provider_response
            )
            
            logger.info(f"Payment {payment_id} captured for {capture_amount}")
            
        except Exception as e:
            logger.error(f"Payment {payment_id} capture error: {e}", exc_info=True)
            raise PaymentFailedException(f"Capture failed: {str(e)}")
        
        payment = self.update_entity(payment)
        return payment
    
    def void_payment(
        self,
        payment_id: int,
        reason: Optional[str] = None
    ) -> Payment:
        """
        Void an authorized payment.
        
        Args:
            payment_id: Payment ID
            reason: Optional void reason
            
        Returns:
            Updated payment
        """
        payment = self.get_or_fail(payment_id)
        
        if payment.status not in [PaymentStatus.AUTHORIZED, PaymentStatus.PENDING]:
            raise InvalidReservationStateException(
                payment_id,
                payment.status,
                "void"
            )
        
        try:
            # Call provider to void
            provider_response = self._call_provider_void(
                payment.provider,
                payment.provider_transaction_id
            )
            
            # Update payment
            payment.status = PaymentStatus.CANCELLED
            payment.voided_at = datetime.utcnow()
            payment.void_reason = reason
            
            # Create transaction record
            self._create_transaction(
                payment_id=payment.id,
                transaction_type=TransactionType.VOID,
                amount=payment.amount,
                provider=payment.provider,
                provider_transaction_id=provider_response.get('transaction_id'),
                response=provider_response
            )
            
            logger.info(f"Payment {payment_id} voided")
            
        except Exception as e:
            logger.error(f"Payment {payment_id} void error: {e}", exc_info=True)
            raise PaymentFailedException(f"Void failed: {str(e)}")
        
        payment = self.update_entity(payment)
        return payment
    
    def refund_payment(
        self,
        payment_id: int,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Refund:
        """
        Refund a payment.
        
        Args:
            payment_id: Payment ID
            amount: Optional amount to refund (partial refund)
            reason: Optional refund reason
            metadata: Optional metadata
            
        Returns:
            Created refund record
        """
        payment = self.get_or_fail(payment_id)
        
        if payment.status not in [PaymentStatus.PAID, PaymentStatus.PARTIALLY_PAID]:
            raise InvalidReservationStateException(
                payment_id,
                payment.status,
                "refund"
            )
        
        refund_amount = amount or payment.amount
        
        # Calculate total already refunded
        total_refunded = sum(r.amount for r in payment.refunds if r.status == 'completed')
        
        if refund_amount > (payment.amount - total_refunded):
            raise RefundAmountExceededException(
                payment.amount - total_refunded,
                refund_amount
            )
        
        # Generate refund ID
        refund_id = self._generate_refund_id()
        
        refund = Refund(
            payment_id=payment_id,
            refund_id=refund_id,
            amount=refund_amount,
            currency=payment.currency,
            reason=reason,
            status='pending',
            metadata=metadata or {},
            created_at=datetime.utcnow()
        )
        
        self.session.add(refund)
        self.session.flush()
        
        try:
            # Process refund with provider
            provider_response = self._call_provider_refund(
                payment.provider,
                payment.provider_transaction_id,
                refund_amount,
                refund_id
            )
            
            # Update refund
            refund.status = 'completed'
            refund.processed_at = datetime.utcnow()
            refund.provider_response = provider_response
            refund.provider_refund_id = provider_response.get('refund_id')
            
            # Update payment
            payment.refunded_amount = (payment.refunded_amount or 0) + refund_amount
            
            if payment.refunded_amount >= payment.amount:
                payment.status = PaymentStatus.REFUNDED
            else:
                payment.status = PaymentStatus.PARTIALLY_REFUNDED
            
            # Create transaction record
            self._create_transaction(
                payment_id=payment.id,
                transaction_type=TransactionType.REFUND,
                amount=refund_amount,
                provider=payment.provider,
                provider_transaction_id=provider_response.get('transaction_id'),
                response=provider_response,
                metadata={'refund_id': refund.id}
            )
            
            logger.info(f"Refund {refund.id} processed for payment {payment_id}, amount {refund_amount}")
            
        except Exception as e:
            refund.status = 'failed'
            refund.failure_reason = str(e)
            refund.failed_at = datetime.utcnow()
            
            self.session.flush()
            
            logger.error(f"Refund {refund.id} failed: {e}", exc_info=True)
            raise RefundFailedException(str(e))
        
        self.session.flush()
        return refund
    
    # ========================================================================
    # Payment Method Management
    # ========================================================================
    
    def add_payment_method(
        self,
        user_id: int,
        method_type: PaymentMethodType,
        provider: PaymentProvider,
        token: str,
        is_default: bool = False,
        billing_details: Optional[Dict] = None,
        **kwargs
    ) -> PaymentMethod:
        """
        Add a payment method for a user.
        
        Args:
            user_id: User ID
            method_type: Type of payment method
            provider: Payment provider
            token: Provider token
            is_default: Whether to set as default
            billing_details: Optional billing details
            **kwargs: Additional method attributes
            
        Returns:
            Created payment method
        """
        # Check if user exists
        user = self.session.query(User).get(user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        
        # Create payment method
        payment_method = PaymentMethod(
            user_id=user_id,
            method_type=method_type,
            provider=provider,
            token=self._encrypt_token(token),
            last_four=kwargs.get('last_four'),
            expiry_month=kwargs.get('expiry_month'),
            expiry_year=kwargs.get('expiry_year'),
            card_brand=kwargs.get('card_brand'),
            billing_details=billing_details or {},
            is_default=is_default,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.session.add(payment_method)
        self.session.flush()
        
        # If this is the default, clear other defaults
        if is_default:
            self.session.query(PaymentMethod).filter(
                PaymentMethod.user_id == user_id,
                PaymentMethod.id != payment_method.id,
                PaymentMethod.is_default == True
            ).update({'is_default': False})
        
        logger.info(f"Added payment method {payment_method.id} for user {user_id}")
        return payment_method
    
    def update_payment_method(
        self,
        payment_method_id: int,
        **updates
    ) -> PaymentMethod:
        """
        Update a payment method.
        
        Args:
            payment_method_id: Payment method ID
            **updates: Fields to update
            
        Returns:
            Updated payment method
        """
        payment_method = self.session.query(PaymentMethod).get(payment_method_id)
        if not payment_method:
            raise EntityNotFoundException("PaymentMethod", payment_method_id)
        
        # Handle token update (re-encrypt)
        if 'token' in updates:
            updates['token'] = self._encrypt_token(updates['token'])
        
        # Update fields
        for key, value in updates.items():
            if hasattr(payment_method, key):
                setattr(payment_method, key, value)
        
        payment_method.updated_at = datetime.utcnow()
        
        # If setting as default, clear other defaults
        if updates.get('is_default'):
            self.session.query(PaymentMethod).filter(
                PaymentMethod.user_id == payment_method.user_id,
                PaymentMethod.id != payment_method_id,
                PaymentMethod.is_default == True
            ).update({'is_default': False})
        
        self.session.flush()
        
        logger.info(f"Updated payment method {payment_method_id}")
        return payment_method
    
    def delete_payment_method(self, payment_method_id: int) -> bool:
        """
        Delete a payment method.
        
        Args:
            payment_method_id: Payment method ID
            
        Returns:
            True if deleted
        """
        payment_method = self.session.query(PaymentMethod).get(payment_method_id)
        if not payment_method:
            return False
        
        # Soft delete
        payment_method.is_active = False
        payment_method.deleted_at = datetime.utcnow()
        
        self.session.flush()
        
        logger.info(f"Deleted payment method {payment_method_id}")
        return True
    
    def get_user_payment_methods(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[PaymentMethod]:
        """
        Get payment methods for a user.
        
        Args:
            user_id: User ID
            active_only: Whether to return only active methods
            
        Returns:
            List of payment methods
        """
        query = self.session.query(PaymentMethod).filter(
            PaymentMethod.user_id == user_id
        )
        
        if active_only:
            query = query.filter(PaymentMethod.is_active == True)
        
        return query.order_by(desc(PaymentMethod.is_default), desc(PaymentMethod.created_at)).all()
    
    def get_default_payment_method(self, user_id: int) -> Optional[PaymentMethod]:
        """
        Get default payment method for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Default payment method if found
        """
        return (
            self.session.query(PaymentMethod)
            .filter(
                PaymentMethod.user_id == user_id,
                PaymentMethod.is_default == True,
                PaymentMethod.is_active == True
            )
            .first()
        )
    
    # ========================================================================
    # Transaction Management
    # ========================================================================
    
    def get_transactions(
        self,
        payment_id: Optional[int] = None,
        transaction_type: Optional[TransactionType] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[PaymentTransaction]:
        """
        Get payment transactions.
        
        Args:
            payment_id: Optional payment filter
            transaction_type: Optional type filter
            from_date: Optional start date
            to_date: Optional end date
            
        Returns:
            List of transactions
        """
        query = self.session.query(PaymentTransaction)
        
        if payment_id:
            query = query.filter(PaymentTransaction.payment_id == payment_id)
        
        if transaction_type:
            query = query.filter(PaymentTransaction.transaction_type == transaction_type)
        
        if from_date:
            query = query.filter(PaymentTransaction.created_at >= from_date)
        
        if to_date:
            query = query.filter(PaymentTransaction.created_at <= to_date)
        
        return query.order_by(desc(PaymentTransaction.created_at)).all()
    
    def get_transaction_by_provider_id(
        self,
        provider: PaymentProvider,
        provider_transaction_id: str
    ) -> Optional[PaymentTransaction]:
        """
        Get transaction by provider transaction ID.
        
        Args:
            provider: Payment provider
            provider_transaction_id: Provider's transaction ID
            
        Returns:
            Transaction if found
        """
        return (
            self.session.query(PaymentTransaction)
            .filter(
                PaymentTransaction.provider == provider,
                PaymentTransaction.provider_transaction_id == provider_transaction_id
            )
            .first()
        )
    
    # ========================================================================
    # Dispute Management
    # ========================================================================
    
    def create_dispute(
        self,
        payment_id: int,
        reason: DisputeReason,
        amount: Decimal,
        evidence: Optional[Dict] = None,
        **kwargs
    ) -> Dispute:
        """
        Create a dispute for a payment.
        
        Args:
            payment_id: Payment ID
            reason: Dispute reason
            amount: Dispute amount
            evidence: Optional evidence
            **kwargs: Additional dispute attributes
            
        Returns:
            Created dispute
        """
        payment = self.get_or_fail(payment_id)
        
        # Check if dispute already exists
        existing = (
            self.session.query(Dispute)
            .filter(
                Dispute.payment_id == payment_id,
                Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW])
            )
            .first()
        )
        
        if existing:
            raise RepositoryException(f"Payment {payment_id} already has an active dispute")
        
        # Generate case number
        case_number = self._generate_case_number()
        
        dispute = Dispute(
            payment_id=payment_id,
            case_number=case_number,
            reason=reason,
            amount=amount,
            currency=payment.currency,
            status=DisputeStatus.OPEN,
            evidence=evidence or {},
            created_at=datetime.utcnow(),
            **kwargs
        )
        
        self.session.add(dispute)
        self.session.flush()
        
        # Update payment status
        payment.status = PaymentStatus.DISPUTED
        payment.dispute_id = dispute.id
        
        self.session.flush()
        
        logger.info(f"Created dispute {dispute.id} for payment {payment_id}")
        return dispute
    
    def update_dispute(
        self,
        dispute_id: int,
        status: DisputeStatus,
        resolution: Optional[str] = None,
        response: Optional[Dict] = None
    ) -> Dispute:
        """
        Update dispute status.
        
        Args:
            dispute_id: Dispute ID
            status: New status
            resolution: Optional resolution notes
            response: Optional provider response
            
        Returns:
            Updated dispute
        """
        dispute = self.session.query(Dispute).get(dispute_id)
        if not dispute:
            raise DisputeNotFoundException(dispute_id)
        
        old_status = dispute.status
        dispute.status = status
        dispute.updated_at = datetime.utcnow()
        
        if resolution:
            dispute.resolution = resolution
        
        if response:
            dispute.provider_response = response
        
        if status in [DisputeStatus.WON, DisputeStatus.LOST, DisputeStatus.ACCEPTED]:
            dispute.resolved_at = datetime.utcnow()
            
            # Update payment status based on outcome
            payment = dispute.payment
            if status == DisputeStatus.WON:
                payment.status = PaymentStatus.PAID
            elif status == DisputeStatus.LOST or status == DisputeStatus.ACCEPTED:
                payment.status = PaymentStatus.CHARGEBACK
        
        self.session.flush()
        
        logger.info(f"Updated dispute {dispute_id} status from {old_status} to {status}")
        return dispute
    
    def add_evidence(
        self,
        dispute_id: int,
        evidence_type: str,
        content: Any,
        description: Optional[str] = None
    ) -> Dispute:
        """
        Add evidence to a dispute.
        
        Args:
            dispute_id: Dispute ID
            evidence_type: Type of evidence
            content: Evidence content
            description: Optional description
            
        Returns:
            Updated dispute
        """
        dispute = self.session.query(Dispute).get(dispute_id)
        if not dispute:
            raise DisputeNotFoundException(dispute_id)
        
        if not dispute.evidence:
            dispute.evidence = {}
        
        if 'items' not in dispute.evidence:
            dispute.evidence['items'] = []
        
        dispute.evidence['items'].append({
            'type': evidence_type,
            'content': content,
            'description': description,
            'added_at': datetime.utcnow().isoformat()
        })
        
        dispute.updated_at = datetime.utcnow()
        self.session.flush()
        
        logger.info(f"Added evidence to dispute {dispute_id}")
        return dispute
    
    def get_active_disputes(self) -> List[Dispute]:
        """Get all active disputes."""
        return (
            self.session.query(Dispute)
            .filter(Dispute.status.in_([
                DisputeStatus.OPEN,
                DisputeStatus.UNDER_REVIEW,
                DisputeStatus.WAITING_FOR_BUYER_RESPONSE,
                DisputeStatus.WAITING_FOR_SELLER_RESPONSE,
                DisputeStatus.APPEALED
            ]))
            .all()
        )
    
    # ========================================================================
    # Reconciliation Methods
    # ========================================================================
    
    def reconcile_payments(
        self,
        from_date: datetime,
        to_date: datetime,
        provider: Optional[PaymentProvider] = None
    ) -> Dict[str, Any]:
        """
        Reconcile payments with provider statements.
        
        Args:
            from_date: Start date
            to_date: End date
            provider: Optional provider filter
            
        Returns:
            Reconciliation results
        """
        # Get local payments
        query = self.session.query(Payment).filter(
            Payment.created_at.between(from_date, to_date)
        )
        
        if provider:
            query = query.filter(Payment.provider == provider)
        
        local_payments = query.all()
        
        # Get provider transactions (this would call provider API)
        provider_transactions = self._get_provider_transactions(
            provider,
            from_date,
            to_date
        )
        
        # Match transactions
        matched = []
        unmatched_local = []
        unmatched_provider = []
        discrepancies = []
        
        local_dict = {p.provider_transaction_id: p for p in local_payments if p.provider_transaction_id}
        provider_dict = {t['id']: t for t in provider_transactions}
        
        # Find matches and discrepancies
        for local_id, local_payment in local_dict.items():
            if local_id in provider_dict:
                provider_txn = provider_dict[local_id]
                
                # Compare amounts
                if abs(local_payment.amount - Decimal(str(provider_txn['amount']))) < Decimal('0.01'):
                    matched.append({
                        'local_id': local_payment.id,
                        'provider_id': local_id,
                        'amount': local_payment.amount,
                        'status': 'matched'
                    })
                else:
                    discrepancies.append({
                        'local_id': local_payment.id,
                        'provider_id': local_id,
                        'local_amount': local_payment.amount,
                        'provider_amount': provider_txn['amount'],
                        'status': 'amount_mismatch'
                    })
            else:
                unmatched_local.append({
                    'id': local_payment.id,
                    'transaction_id': local_id,
                    'amount': local_payment.amount,
                    'created_at': local_payment.created_at
                })
        
        # Find provider transactions not in local
        for provider_id in provider_dict:
            if provider_id not in local_dict:
                unmatched_provider.append({
                    'id': provider_id,
                    'amount': provider_dict[provider_id]['amount'],
                    'created_at': provider_dict[provider_id]['created_at']
                })
        
        return {
            'period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat()
            },
            'summary': {
                'total_local': len(local_payments),
                'total_provider': len(provider_transactions),
                'matched': len(matched),
                'unmatched_local': len(unmatched_local),
                'unmatched_provider': len(unmatched_provider),
                'discrepancies': len(discrepancies)
            },
            'details': {
                'matched': matched,
                'unmatched_local': unmatched_local,
                'unmatched_provider': unmatched_provider,
                'discrepancies': discrepancies
            }
        }
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _generate_transaction_id(self) -> str:
        """Generate a unique transaction ID."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random = secrets.token_hex(4).upper()
        return f"TXN{timestamp}{random}"
    
    def _generate_refund_id(self) -> str:
        """Generate a unique refund ID."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random = secrets.token_hex(4).upper()
        return f"REF{timestamp}{random}"
    
    def _generate_case_number(self) -> str:
        """Generate a unique dispute case number."""
        timestamp = datetime.utcnow().strftime('%Y%m%d')
        random = secrets.token_hex(3).upper()
        return f"DIS{timestamp}-{random}"
    
    def _encrypt_token(self, token: str) -> str:
        """
        Encrypt a payment token.
        
        In production, use proper encryption like AES-256.
        """
        # Placeholder - implement proper encryption
        return hashlib.sha256(token.encode()).hexdigest()
    
    def _decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt a payment token.
        
        In production, implement proper decryption.
        """
        # Placeholder - this would decrypt the token
        return encrypted_token
    
    def _select_provider(self, payment_method: PaymentMethod) -> PaymentProvider:
        """Select the best provider for a payment."""
        # Use preferred provider if set
        if payment_method.preferred_provider:
            return payment_method.preferred_provider
        
        # Otherwise use default based on method type
        if payment_method.method_type in PaymentMethodType.get_card_methods():
            return PaymentProvider.STRIPE
        elif payment_method.method_type in PaymentMethodType.get_digital_wallets():
            return PaymentProvider.PAYPAL
        else:
            return PaymentProvider.STRIPE
    
    def _create_transaction(
        self,
        payment_id: int,
        transaction_type: TransactionType,
        amount: Decimal,
        provider: PaymentProvider,
        provider_transaction_id: Optional[str] = None,
        status: PaymentStatus = PaymentStatus.PAID,
        response: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> PaymentTransaction:
        """Create a transaction record."""
        transaction = PaymentTransaction(
            payment_id=payment_id,
            transaction_type=transaction_type,
            amount=amount,
            provider=provider,
            provider_transaction_id=provider_transaction_id,
            status=status,
            request_data=metadata,
            response_data=response,
            created_at=datetime.utcnow()
        )
        
        self.session.add(transaction)
        self.session.flush()
        
        return transaction
    
    def _call_payment_provider(
        self,
        provider: PaymentProvider,
        payment_method: PaymentMethod,
        amount: Decimal,
        currency: Currency,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """
        Call payment provider API to process payment.
        
        This is a placeholder - implement actual provider API calls.
        """
        # Placeholder implementation
        # In production, integrate with actual payment providers
        
        # Simulate success/failure
        import random
        success = random.random() > 0.1  # 90% success rate
        
        if success:
            return {
                'success': True,
                'transaction_id': f"prov_{secrets.token_hex(8)}",
                'authorization_code': secrets.token_hex(4).upper(),
                'amount': float(amount),
                'currency': currency.value,
                'timestamp': datetime.utcnow().isoformat()
            }
        else:
            return {
                'success': False,
                'error_code': 'card_declined',
                'error_message': 'Your card was declined',
                'decline_code': 'generic_decline'
            }
    
    def _call_provider_capture(
        self,
        provider: PaymentProvider,
        transaction_id: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Call provider to capture an authorization."""
        # Placeholder
        return {
            'success': True,
            'transaction_id': f"cap_{secrets.token_hex(8)}",
            'amount': float(amount),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _call_provider_void(
        self,
        provider: PaymentProvider,
        transaction_id: str
    ) -> Dict[str, Any]:
        """Call provider to void an authorization."""
        # Placeholder
        return {
            'success': True,
            'transaction_id': f"void_{secrets.token_hex(8)}",
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _call_provider_refund(
        self,
        provider: PaymentProvider,
        transaction_id: str,
        amount: Decimal,
        refund_id: str
    ) -> Dict[str, Any]:
        """Call provider to process a refund."""
        # Placeholder
        return {
            'success': True,
            'refund_id': f"ref_{secrets.token_hex(8)}",
            'transaction_id': f"txn_{secrets.token_hex(8)}",
            'amount': float(amount),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _get_provider_transactions(
        self,
        provider: Optional[PaymentProvider],
        from_date: datetime,
        to_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get transactions from provider for reconciliation.
        
        Placeholder - implement actual provider API calls.
        """
        # Placeholder
        return []


# ============================================================================
# Invoice Repository
# ============================================================================

class InvoiceRepository(FullFeatureRepository[Invoice, int]):
    """Repository for Invoice entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, Invoice)
        self.searchable_fields = ['invoice_number', 'po_number']
    
    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Get invoice by invoice number."""
        return (
            self.session.query(Invoice)
            .filter(Invoice.invoice_number == invoice_number)
            .first()
        )
    
    def get_user_invoices(
        self,
        user_id: int,
        statuses: Optional[List[InvoiceStatus]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Invoice]:
        """Get invoices for a user."""
        query = self.session.query(Invoice).filter(
            Invoice.user_id == user_id
        )
        
        if statuses:
            query = query.filter(Invoice.status.in_(statuses))
        
        if from_date:
            query = query.filter(Invoice.issue_date >= from_date)
        
        if to_date:
            query = query.filter(Invoice.issue_date <= to_date)
        
        return query.order_by(desc(Invoice.issue_date)).limit(limit).all()
    
    def get_overdue_invoices(self, as_of_date: Optional[datetime] = None) -> List[Invoice]:
        """Get overdue invoices."""
        check_date = as_of_date or datetime.utcnow()
        
        return (
            self.session.query(Invoice)
            .filter(
                Invoice.status == InvoiceStatus.OPEN,
                Invoice.due_date < check_date
            )
            .all()
        )
    
    def create_invoice(
        self,
        user_id: int,
        issue_date: datetime,
        due_date: datetime,
        items: List[Dict[str, Any]],
        **kwargs
    ) -> Invoice:
        """Create a new invoice with items."""
        # Generate invoice number
        invoice_number = self._generate_invoice_number()
        
        # Calculate totals
        subtotal = sum(item['amount'] * item.get('quantity', 1) for item in items)
        tax_total = sum(item.get('tax_amount', 0) for item in items)
        total = subtotal + tax_total
        
        invoice = Invoice(
            user_id=user_id,
            invoice_number=invoice_number,
            issue_date=issue_date,
            due_date=due_date,
            subtotal=subtotal,
            tax_total=tax_total,
            total=total,
            status=InvoiceStatus.DRAFT,
            **kwargs
        )
        
        self.session.add(invoice)
        self.session.flush()
        
        # Create invoice items
        for item_data in items:
            item = InvoiceItem(
                invoice_id=invoice.id,
                description=item_data['description'],
                quantity=item_data.get('quantity', 1),
                unit_price=item_data['amount'],
                tax_rate=item_data.get('tax_rate', 0),
                tax_amount=item_data.get('tax_amount', 0),
                total=item_data['amount'] * item_data.get('quantity', 1)
            )
            self.session.add(item)
        
        self.session.flush()
        
        logger.info(f"Created invoice {invoice.id} for user {user_id}")
        return invoice
    
    def mark_invoice_paid(
        self,
        invoice_id: int,
        payment_id: int,
        paid_at: Optional[datetime] = None
    ) -> Invoice:
        """Mark an invoice as paid."""
        invoice = self.get_or_fail(invoice_id)
        
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = paid_at or datetime.utcnow()
        invoice.payment_id = payment_id
        
        self.session.flush()
        
        logger.info(f"Marked invoice {invoice_id} as paid")
        return invoice
    
    def _generate_invoice_number(self) -> str:
        """Generate a unique invoice number."""
        year = datetime.utcnow().year
        month = datetime.utcnow().month
        
        # Get count for this month
        count = (
            self.session.query(func.count(Invoice.id))
            .filter(
                func.extract('year', Invoice.issue_date) == year,
                func.extract('month', Invoice.issue_date) == month
            )
            .scalar() or 0
        ) + 1
        
        return f"INV-{year}{month:02d}-{count:04d}"


# ============================================================================
# Subscription Repository
# ============================================================================

class SubscriptionRepository(FullFeatureRepository[Subscription, int]):
    """Repository for Subscription entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, Subscription)
    
    def get_user_subscriptions(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[Subscription]:
        """Get subscriptions for a user."""
        query = self.session.query(Subscription).filter(
            Subscription.user_id == user_id
        )
        
        if active_only:
            query = query.filter(
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING,
                    SubscriptionStatus.PAST_DUE
                ])
            )
        
        return query.all()
    
    def get_active_subscriptions(self) -> List[Subscription]:
        """Get all active subscriptions."""
        return (
            self.session.query(Subscription)
            .filter(
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING,
                    SubscriptionStatus.PAST_DUE
                ])
            )
            .all()
        )
    
    def get_subscriptions_needing_invoice(self) -> List[Subscription]:
        """Get subscriptions that need invoice generation."""
        now = datetime.utcnow()
        
        return (
            self.session.query(Subscription)
            .filter(
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
                or_(
                    Subscription.next_billing_date <= now,
                    and_(
                        Subscription.trial_end.isnot(None),
                        Subscription.trial_end <= now
                    )
                )
            )
            .all()
        )
    
    def get_expiring_subscriptions(self, days: int = 7) -> List[Subscription]:
        """Get subscriptions expiring soon."""
        now = datetime.utcnow()
        end_date = now + timedelta(days=days)
        
        return (
            self.session.query(Subscription)
            .filter(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.current_period_end.between(now, end_date)
            )
            .all()
        )
    
    def create_subscription(
        self,
        user_id: int,
        plan_id: int,
        payment_method_id: int,
        trial_days: Optional[int] = None,
        **kwargs
    ) -> Subscription:
        """Create a new subscription."""
        # Check if user already has active subscription
        existing = (
            self.session.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING,
                    SubscriptionStatus.PAST_DUE
                ])
            )
            .first()
        )
        
        if existing:
            raise SubscriptionAlreadyActiveException(user_id, plan_id)
        
        # Get plan
        plan = self.session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            raise EntityNotFoundException("SubscriptionPlan", plan_id)
        
        now = datetime.utcnow()
        
        # Calculate dates
        if trial_days or plan.trial_days:
            trial_end = now + timedelta(days=(trial_days or plan.trial_days))
            status = SubscriptionStatus.TRIALING
        else:
            trial_end = None
            status = SubscriptionStatus.ACTIVE
        
        period_end = self._calculate_period_end(now, plan.interval, plan.interval_count)
        
        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            payment_method_id=payment_method_id,
            status=status,
            current_period_start=now,
            current_period_end=period_end,
            trial_start=now if trial_end else None,
            trial_end=trial_end,
            cancel_at_period_end=False,
            **kwargs
        )
        
        self.session.add(subscription)
        self.session.flush()
        
        # Create history entry
        history = SubscriptionHistory(
            subscription_id=subscription.id,
            status=status,
            notes="Subscription created",
            created_at=now
        )
        self.session.add(history)
        
        logger.info(f"Created subscription {subscription.id} for user {user_id}")
        return subscription
    
    def cancel_subscription(
        self,
        subscription_id: int,
        cancel_immediately: bool = False,
        reason: Optional[str] = None
    ) -> Subscription:
        """Cancel a subscription."""
        subscription = self.get_or_fail(subscription_id)
        
        if cancel_immediately:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = datetime.utcnow()
            subscription.cancellation_reason = reason
        else:
            subscription.cancel_at_period_end = True
            subscription.cancellation_reason = reason
        
        # Create history entry
        history = SubscriptionHistory(
            subscription_id=subscription_id,
            status=subscription.status,
            notes=f"Subscription cancelled: {reason}",
            created_at=datetime.utcnow()
        )
        self.session.add(history)
        
        self.session.flush()
        
        logger.info(f"Cancelled subscription {subscription_id}")
        return subscription
    
    def process_renewal(self, subscription_id: int) -> Subscription:
        """Process subscription renewal."""
        subscription = self.get_or_fail(subscription_id)
        
        now = datetime.utcnow()
        
        # Update periods
        subscription.current_period_start = subscription.current_period_end
        subscription.current_period_end = self._calculate_period_end(
            subscription.current_period_start,
            subscription.plan.interval,
            subscription.plan.interval_count
        )
        
        subscription.last_invoice_date = now
        
        # Check if should be canceled
        if subscription.cancel_at_period_end:
            subscription.status = SubscriptionStatus.CANCELED
            subscription.canceled_at = now
        
        # Create history entry
        history = SubscriptionHistory(
            subscription_id=subscription_id,
            status=subscription.status,
            notes="Subscription renewed",
            created_at=now
        )
        self.session.add(history)
        
        self.session.flush()
        
        logger.info(f"Processed renewal for subscription {subscription_id}")
        return subscription
    
    def _calculate_period_end(
        self,
        start_date: datetime,
        interval: SubscriptionInterval,
        interval_count: int
    ) -> datetime:
        """Calculate period end date."""
        if interval == SubscriptionInterval.DAY:
            return start_date + timedelta(days=interval_count)
        elif interval == SubscriptionInterval.WEEK:
            return start_date + timedelta(weeks=interval_count)
        elif interval == SubscriptionInterval.MONTH:
            # Handle month addition carefully
            year = start_date.year
            month = start_date.month + interval_count
            while month > 12:
                month -= 12
                year += 1
            day = min(start_date.day, self._days_in_month(year, month))
            return datetime(year, month, day, start_date.hour, start_date.minute, start_date.second)
        elif interval == SubscriptionInterval.YEAR:
            return datetime(
                start_date.year + interval_count,
                start_date.month,
                start_date.day,
                start_date.hour,
                start_date.minute,
                start_date.second
            )
        return start_date
    
    def _days_in_month(self, year: int, month: int) -> int:
        """Get number of days in a month."""
        if month == 2:
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                return 29
            return 28
        if month in [4, 6, 9, 11]:
            return 30
        return 31


# ============================================================================
# Discount Repository
# ============================================================================

class DiscountRepository(BaseRepository[Discount, int]):
    """Repository for Discount entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, Discount)
    
    def get_by_code(self, code: str) -> Optional[Discount]:
        """Get discount by code."""
        return (
            self.session.query(Discount)
            .filter(Discount.code == code.upper())
            .first()
        )
    
    def get_active_discounts(self) -> List[Discount]:
        """Get all active discounts."""
        now = datetime.utcnow()
        
        return (
            self.session.query(Discount)
            .filter(
                Discount.is_active == True,
                or_(
                    Discount.valid_from.is_(None),
                    Discount.valid_from <= now
                ),
                or_(
                    Discount.valid_until.is_(None),
                    Discount.valid_until >= now
                )
            )
            .all()
        )
    
    def validate_discount(
        self,
        code: str,
        user_id: Optional[int] = None,
        amount: Optional[Decimal] = None,
        **context
    ) -> Tuple[bool, Optional[str], Optional[Discount]]:
        """
        Validate a discount code.
        
        Args:
            code: Discount code
            user_id: Optional user ID
            amount: Optional order amount
            **context: Additional context for validation
            
        Returns:
            Tuple of (is_valid, error_message, discount)
        """
        discount = self.get_by_code(code)
        
        if not discount:
            return False, "Invalid discount code", None
        
        if not discount.is_active:
            return False, "Discount is inactive", discount
        
        # Check date range
        now = datetime.utcnow()
        if discount.valid_from and discount.valid_from > now:
            return False, "Discount not yet valid", discount
        
        if discount.valid_until and discount.valid_until < now:
            return False, "Discount has expired", discount
        
        # Check usage limits
        if discount.max_uses:
            usage_count = self._get_usage_count(discount.id)
            if usage_count >= discount.max_uses:
                return False, "Discount usage limit reached", discount
        
        if discount.max_uses_per_user and user_id:
            user_usage = self._get_user_usage_count(discount.id, user_id)
            if user_usage >= discount.max_uses_per_user:
                return False, "You have already used this discount", discount
        
        # Check minimum amount
        if discount.minimum_amount and amount and amount < discount.minimum_amount:
            return False, f"Minimum amount of {discount.minimum_amount} required", discount
        
        return True, None, discount
    
    def apply_discount(
        self,
        discount_id: int,
        user_id: int,
        original_amount: Decimal,
        **context
    ) -> Tuple[Decimal, Dict[str, Any]]:
        """
        Apply a discount to an amount.
        
        Args:
            discount_id: Discount ID
            user_id: User ID
            original_amount: Original amount
            **context: Additional context
            
        Returns:
            Tuple of (discounted_amount, calculation_details)
        """
        discount = self.get_or_fail(discount_id)
        
        # Calculate discount
        if discount.discount_type == DiscountType.PERCENTAGE:
            discount_amount = original_amount * (discount.discount_value / 100)
            discounted_amount = original_amount - discount_amount
        elif discount.discount_type == DiscountType.FIXED_AMOUNT:
            discount_amount = min(discount.discount_value, original_amount)
            discounted_amount = original_amount - discount_amount
        else:
            discount_amount = Decimal('0')
            discounted_amount = original_amount
        
        # Create usage record
        usage = DiscountUsage(
            discount_id=discount_id,
            user_id=user_id,
            original_amount=original_amount,
            discount_amount=discount_amount,
            final_amount=discounted_amount,
            context=context,
            used_at=datetime.utcnow()
        )
        self.session.add(usage)
        self.session.flush()
        
        calculation = {
            'original_amount': float(original_amount),
            'discount_type': discount.discount_type.value,
            'discount_value': float(discount.discount_value),
            'discount_amount': float(discount_amount),
            'final_amount': float(discounted_amount)
        }
        
        return discounted_amount, calculation
    
    def _get_usage_count(self, discount_id: int) -> int:
        """Get total usage count for a discount."""
        return (
            self.session.query(func.count(DiscountUsage.id))
            .filter(DiscountUsage.discount_id == discount_id)
            .scalar() or 0
        )
    
    def _get_user_usage_count(self, discount_id: int, user_id: int) -> int:
        """Get usage count for a discount by a specific user."""
        return (
            self.session.query(func.count(DiscountUsage.id))
            .filter(
                DiscountUsage.discount_id == discount_id,
                DiscountUsage.user_id == user_id
            )
            .scalar() or 0
        )


# ============================================================================
# Fee Repository
# ============================================================================

class FeeRepository(BaseRepository[Fee, int]):
    """Repository for Fee entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, Fee)
    
    def get_applicable_fees(
        self,
        fee_type: Optional[FeeType] = None,
        context: Optional[Dict] = None
    ) -> List[Fee]:
        """Get fees applicable in current context."""
        now = datetime.utcnow()
        
        query = self.session.query(Fee).filter(
            Fee.is_active == True,
            or_(
                Fee.effective_from.is_(None),
                Fee.effective_from <= now
            ),
            or_(
                Fee.effective_until.is_(None),
                Fee.effective_until >= now
            )
        )
        
        if fee_type:
            query = query.filter(Fee.fee_type == fee_type)
        
        return query.all()
    
    def calculate_fee(
        self,
        fee_id: int,
        base_amount: Decimal,
        **context
    ) -> Tuple[Decimal, FeeCalculation]:
        """
        Calculate a fee amount.
        
        Args:
            fee_id: Fee ID
            base_amount: Base amount to calculate fee on
            **context: Additional context for calculation
            
        Returns:
            Tuple of (fee_amount, calculation_record)
        """
        fee = self.get_or_fail(fee_id)
        
        # Calculate fee based on type
        if fee.calculation_method == 'percentage':
            fee_amount = base_amount * (fee.rate_value / 100)
        elif fee.calculation_method == 'fixed':
            fee_amount = fee.rate_value
        elif fee.calculation_method == 'tiered':
            fee_amount = self._calculate_tiered_fee(fee, base_amount)
        else:
            fee_amount = Decimal('0')
        
        # Apply min/max
        if fee.min_amount and fee_amount < fee.min_amount:
            fee_amount = fee.min_amount
        if fee.max_amount and fee_amount > fee.max_amount:
            fee_amount = fee.max_amount
        
        # Create calculation record
        calculation = FeeCalculation(
            fee_id=fee_id,
            base_amount=base_amount,
            calculated_amount=fee_amount,
            context=context,
            calculated_at=datetime.utcnow()
        )
        self.session.add(calculation)
        self.session.flush()
        
        return fee_amount, calculation
    
    def _calculate_tiered_fee(self, fee: Fee, base_amount: Decimal) -> Decimal:
        """Calculate tiered fee amount."""
        if not fee.tiers:
            return Decimal('0')
        
        # Sort tiers by threshold
        tiers = sorted(fee.tiers, key=lambda x: x['threshold'])
        
        fee_amount = Decimal('0')
        remaining = base_amount
        
        for i, tier in enumerate(tiers):
            next_threshold = tiers[i + 1]['threshold'] if i + 1 < len(tiers) else None
            
            if next_threshold:
                tier_amount = min(remaining, next_threshold - tier['threshold'])
            else:
                tier_amount = remaining
            
            if tier_amount > 0:
                if tier.get('type') == 'percentage':
                    fee_amount += tier_amount * (tier['rate'] / 100)
                else:
                    fee_amount += tier['rate']
                
                remaining -= tier_amount
            
            if remaining <= 0:
                break
        
        return fee_amount


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main Repository
    'PaymentRepository',
    'InvoiceRepository',
    'SubscriptionRepository',
    'DiscountRepository',
    'FeeRepository',
    
    # Exceptions
    'PaymentNotFoundException',
    'PaymentFailedException',
    'PaymentDeclinedException',
    'InsufficientFundsException',
    'InvalidPaymentMethodException',
    'DuplicateTransactionException',
    'RefundFailedException',
    'RefundAmountExceededException',
    'DisputeNotFoundException',
    'SubscriptionNotFoundException',
    'SubscriptionAlreadyActiveException',
    'InvoiceNotFoundException',
    'InvalidDiscountException',
    'DiscountExpiredException',
    'DiscountLimitReachedException',
]