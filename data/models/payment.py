# parking-management/data/migrations/models/payment.py

"""
Payment model for parking management system.

This module defines the Payment model and related classes for handling
financial transactions, payment methods, refunds, subscriptions, invoices,
and payment processing.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Time,
    Text, ForeignKey, UniqueConstraint, Index, CheckConstraint,
    Numeric, JSON, Table, func, text, event, and_, or_
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, backref, validates, object_session
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declarative_base
import uuid
import enum
import hashlib
import hmac
from datetime import datetime, date, timedelta
import logging
from typing import Optional, List, Dict, Any, Tuple
import json

# Configure logging
logger = logging.getLogger(__name__)

# Create base class
Base = declarative_base()


class PaymentStatus(str, enum.Enum):
    """Enum for payment status."""
    PENDING = 'pending'
    PROCESSING = 'processing'
    AUTHORIZED = 'authorized'
    PAID = 'paid'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'
    PARTIALLY_REFUNDED = 'partially_refunded'
    DISPUTED = 'disputed'
    CHARGEBACK = 'chargeback'
    COMPLETED = 'completed'
    EXPIRED = 'expired'
    VOIDED = 'voided'


class PaymentMethodType(str, enum.Enum):
    """Enum for payment method types."""
    CREDIT_CARD = 'credit_card'
    DEBIT_CARD = 'debit_card'
    PAYPAL = 'paypal'
    APPLE_PAY = 'apple_pay'
    GOOGLE_PAY = 'google_pay'
    BANK_TRANSFER = 'bank_transfer'
    CASH = 'cash'
    CHECK = 'check'
    VOUCHER = 'voucher'
    GIFT_CARD = 'gift_card'
    CRYPTO = 'crypto'
    VENMO = 'venmo'
    ALIPAY = 'alipay'
    WECHAT_PAY = 'wechat_pay'
    KLARNA = 'klarna'
    AFTERPAY = 'afterpay'
    AFFIRM = 'affirm'
    SEPA = 'sepa'
    ACH = 'ach'
    WIRE_TRANSFER = 'wire_transfer'


class PaymentProvider(str, enum.Enum):
    """Enum for payment providers."""
    STRIPE = 'stripe'
    PAYPAL = 'paypal'
    BRAINTREE = 'braintree'
    SQUARE = 'square'
    AUTHORIZE_NET = 'authorize_net'
    ADYEN = 'adyen'
    WORLDPAY = 'worldpay'
    CHECKOUT_COM = 'checkout_com'
    RAZORPAY = 'razorpay'
    PAYU = 'payu'
    MOLLIE = 'mollie'
    TWOCHECKOUT = '2checkout'
    DWOLLA = 'dwolla'
    RECURLY = 'recurly'
    CHARGEBEE = 'chargebee'


class TransactionType(str, enum.Enum):
    """Enum for transaction types."""
    SALE = 'sale'
    AUTHORIZATION = 'authorization'
    CAPTURE = 'capture'
    VOID = 'void'
    REFUND = 'refund'
    CHARGEBACK = 'chargeback'
    SETTLEMENT = 'settlement'
    PAYOUT = 'payout'
    FEE = 'fee'
    ADJUSTMENT = 'adjustment'


class DisputeStatus(str, enum.Enum):
    """Enum for dispute status."""
    OPEN = 'open'
    UNDER_REVIEW = 'under_review'
    WON = 'won'
    LOST = 'lost'
    ACCEPTED = 'accepted'
    WAITING_FOR_BUYER_RESPONSE = 'waiting_for_buyer_response'
    WAITING_FOR_SELLER_RESPONSE = 'waiting_for_seller_response'
    APPEALED = 'appealed'
    CHARGEBACK_REVERSED = 'chargeback_reversed'


class DisputeReason(str, enum.Enum):
    """Enum for dispute reasons."""
    FRAUDULENT = 'fraudulent'
    DUPLICATE = 'duplicate'
    UNAUTHORIZED = 'unauthorized'
    PRODUCT_NOT_RECEIVED = 'product_not_received'
    PRODUCT_UNACCEPTABLE = 'product_unacceptable'
    CREDIT_NOT_PROCESSED = 'credit_not_processed'
    CANCELLED_RECURRING = 'cancelled_recurring'
    BANK_ERROR = 'bank_error'
    CUSTOMER_CLAIM = 'customer_claim'
    SERVICE_DISPUTE = 'service_dispute'


class SubscriptionStatus(str, enum.Enum):
    """Enum for subscription status."""
    ACTIVE = 'active'
    PAST_DUE = 'past_due'
    CANCELED = 'canceled'
    INCOMPLETE = 'incomplete'
    INCOMPLETE_EXPIRED = 'incomplete_expired'
    TRIALING = 'trialing'
    PAUSED = 'paused'
    UNPAID = 'unpaid'
    ENDED = 'ended'


class SubscriptionInterval(str, enum.Enum):
    """Enum for subscription intervals."""
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'


class InvoiceStatus(str, enum.Enum):
    """Enum for invoice status."""
    DRAFT = 'draft'
    OPEN = 'open'
    PAID = 'paid'
    VOID = 'void'
    UNCOLLECTIBLE = 'uncollectible'
    OVERDUE = 'overdue'
    PENDING = 'pending'
    PARTIALLY_PAID = 'partially_paid'


class DiscountType(str, enum.Enum):
    """Enum for discount types."""
    PERCENTAGE = 'percentage'
    FIXED_AMOUNT = 'fixed_amount'
    BUY_X_GET_Y = 'buy_x_get_y'
    FREE_SHIPPING = 'free_shipping'


class DiscountApplyTo(str, enum.Enum):
    """Enum for discount application."""
    ALL = 'all'
    FIRST_BOOKING = 'first_booking'
    RECURRING = 'recurring'
    SPECIFIC_SPOT = 'specific_spot'
    SPECIFIC_ZONE = 'specific_zone'


class FeeType(str, enum.Enum):
    """Enum for fee types."""
    PROCESSING = 'processing'
    CONVENIENCE = 'convenience'
    SERVICE = 'service'
    LATE = 'late'
    CANCELLATION = 'cancellation'
    FOREIGN_TRANSACTION = 'foreign_transaction'
    CROSS_BORDER = 'cross_border'
    CURRENCY_CONVERSION = 'currency_conversion'


class Currency(str, enum.Enum):
    """Enum for supported currencies."""
    USD = 'USD'
    EUR = 'EUR'
    GBP = 'GBP'
    CAD = 'CAD'
    AUD = 'AUD'
    JPY = 'JPY'
    CNY = 'CNY'
    INR = 'INR'
    MXN = 'MXN'
    BRL = 'BRL'
    CHF = 'CHF'
    HKD = 'HKD'
    SGD = 'SGD'
    NZD = 'NZD'
    KRW = 'KRW'
    SEK = 'SEK'


class Payment(Base):
    """
    Core payments table tracking all financial transactions.
    
    Supports multiple payment methods and providers, with comprehensive
    tracking of status, refunds, disputes, and metadata.
    """
    
    __tablename__ = 'payments'
    __table_args__ = (
        # Primary indexes
        Index('ix_payments_number', 'payment_number', unique=True),
        Index('ix_payments_external_id', 'external_id', unique=True),
        
        # Foreign key indexes
        Index('ix_payments_user_id', 'user_id'),
        Index('ix_payments_reservation_id', 'reservation_id'),
        Index('ix_payments_subscription_id', 'subscription_id'),
        Index('ix_payments_invoice_id', 'invoice_id'),
        Index('ix_payments_payment_method_id', 'payment_method_id'),
        
        # Provider ID indexes
        Index('ix_payments_provider_payment_id', 'provider_payment_id'),
        Index('ix_payments_provider_transaction_id', 'provider_transaction_id'),
        Index('ix_payments_provider_charge_id', 'provider_charge_id'),
        Index('ix_payments_provider_customer_id', 'provider_customer_id'),
        Index('ix_payments_provider_intent_id', 'provider_payment_intent_id'),
        
        # Status indexes
        Index('ix_payments_status', 'status'),
        Index('ix_payments_payment_method_type', 'payment_method_type'),
        Index('ix_payments_transaction_type', 'transaction_type'),
        
        # Time-based indexes
        Index('ix_payments_created_at', 'created_at'),
        Index('ix_payments_paid_at', 'paid_at'),
        Index('ix_payments_authorized_at', 'authorized_at'),
        Index('ix_payments_failed_at', 'failed_at'),
        
        # Composite indexes for common queries
        Index('ix_payments_user_reservation', 'user_id', 'reservation_id'),
        Index('ix_payments_status_date', 'status', 'paid_at'),
        Index('ix_payments_date_range', 'created_at', 'paid_at'),
        Index('ix_payments_amount_currency', 'amount', 'currency'),
        
        # Partial indexes
        Index('ix_payments_daily_revenue', func.date_trunc('day', paid_at), 'currency',
              postgresql_where=text("status = 'paid'")),
        Index('ix_payments_refunded', 'amount_refunded',
              postgresql_where=text("amount_refunded > 0")),
        Index('ix_payments_overdue', 'created_at',
              postgresql_where=text(
                  "status = 'pending' "
                  "AND created_at < CURRENT_TIMESTAMP - INTERVAL '7 days'"
              )),
        
        # Check constraints
        CheckConstraint(
            "status IN ('pending', 'processing', 'authorized', 'paid', 'failed', "
            "'cancelled', 'refunded', 'partially_refunded', 'disputed', 'chargeback', "
            "'completed', 'expired', 'voided')",
            name='ck_payments_status'
        ),
        CheckConstraint(
            "transaction_type IN ('sale', 'authorization', 'capture', 'void', 'refund', "
            "'chargeback', 'settlement', 'payout', 'fee', 'adjustment')",
            name='ck_payments_transaction_type'
        ),
        CheckConstraint(
            "amount >= 0",
            name='ck_payments_amount_positive'
        ),
        CheckConstraint(
            "amount_refunded >= 0 AND amount_refunded <= amount",
            name='ck_payments_refunded_amount'
        ),
        
        # Table comment
        {'comment': 'Core payments table tracking all financial transactions'}
    )
    
    # =========================================================================
    # PRIMARY KEY AND IDENTIFIERS
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    payment_number = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Unique human-readable payment number'
    )
    
    external_id = Column(
        String(255),
        unique=True,
        comment='External ID from payment provider'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='ID of user who made payment'
    )
    
    reservation_id = Column(
        UUID(as_uuid=True),
        ForeignKey('reservations.id', ondelete='SET NULL'),
        comment='ID of associated reservation'
    )
    
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payment_subscriptions.id', ondelete='SET NULL'),
        comment='ID of associated subscription'
    )
    
    invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payment_invoices.id', ondelete='SET NULL'),
        comment='ID of associated invoice'
    )
    
    payment_method_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payment_methods.id', ondelete='SET NULL'),
        comment='ID of payment method used'
    )
    
    # =========================================================================
    # PAYMENT DETAILS
    # =========================================================================
    amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Payment amount'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        server_default='USD',
        comment='Currency code (ISO 4217)'
    )
    
    amount_refunded = Column(
        Numeric(10, 2),
        server_default='0',
        comment='Amount refunded'
    )
    
    amount_net = Column(
        Numeric(10, 2),
        comment='Net amount after fees'
    )
    
    amount_captured = Column(
        Numeric(10, 2),
        comment='Amount captured (for authorizations)'
    )
    
    amount_authorized = Column(
        Numeric(10, 2),
        comment='Amount authorized'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    status = Column(
        String(20),
        nullable=False,
        server_default='pending',
        comment='Current payment status'
    )
    
    payment_method_type = Column(
        String(50),
        comment='Type of payment method used'
    )
    
    provider = Column(
        String(50),
        comment='Payment provider (stripe, paypal, etc.)'
    )
    
    transaction_type = Column(
        String(50),
        nullable=False,
        server_default='sale',
        comment='Type of transaction'
    )
    
    # =========================================================================
    # PROVIDER DETAILS
    # =========================================================================
    provider_payment_id = Column(
        String(255),
        comment='Provider payment ID'
    )
    
    provider_transaction_id = Column(
        String(255),
        comment='Provider transaction ID'
    )
    
    provider_charge_id = Column(
        String(255),
        comment='Provider charge ID'
    )
    
    provider_customer_id = Column(
        String(255),
        comment='Provider customer ID'
    )
    
    provider_payment_intent_id = Column(
        String(255),
        comment='Provider payment intent ID'
    )
    
    provider_payment_method_id = Column(
        String(255),
        comment='Provider payment method ID'
    )
    
    provider_setup_intent_id = Column(
        String(255),
        comment='Provider setup intent ID'
    )
    
    # =========================================================================
    # AUTHORIZATION
    # =========================================================================
    authorized_at = Column(
        DateTime(timezone=True),
        comment='When payment was authorized'
    )
    
    authorization_code = Column(
        String(255),
        comment='Authorization code'
    )
    
    authorization_expires_at = Column(
        DateTime(timezone=True),
        comment='When authorization expires'
    )
    
    # =========================================================================
    # CAPTURE
    # =========================================================================
    captured_at = Column(
        DateTime(timezone=True),
        comment='When payment was captured'
    )
    
    capture_method = Column(
        String(50),
        comment='Capture method (automatic, manual)'
    )
    
    # =========================================================================
    # PAYMENT TIMING
    # =========================================================================
    paid_at = Column(
        DateTime(timezone=True),
        comment='When payment was completed'
    )
    
    failed_at = Column(
        DateTime(timezone=True),
        comment='When payment failed'
    )
    
    cancelled_at = Column(
        DateTime(timezone=True),
        comment='When payment was cancelled'
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        comment='When payment expires'
    )
    
    # =========================================================================
    # FAILURE DETAILS
    # =========================================================================
    failure_code = Column(
        String(100),
        comment='Failure code from provider'
    )
    
    failure_message = Column(
        Text,
        comment='Failure message'
    )
    
    failure_transaction_id = Column(
        String(255),
        comment='Failed transaction ID'
    )
    
    # =========================================================================
    # RISK ASSESSMENT
    # =========================================================================
    risk_score = Column(
        Integer,
        comment='Risk score (0-100)'
    )
    
    risk_level = Column(
        String(20),
        comment='Risk level (low, medium, high)'
    )
    
    risk_factors = Column(
        JSONB,
        comment='Risk factors identified'
    )
    
    fraud_check_passed = Column(
        Boolean,
        comment='Whether fraud check passed'
    )
    
    fraud_check_details = Column(
        JSONB,
        comment='Fraud check details'
    )
    
    # =========================================================================
    # 3D SECURE
    # =========================================================================
    three_d_secure_used = Column(
        Boolean,
        server_default='false',
        comment='Whether 3D Secure was used'
    )
    
    three_d_secure_status = Column(
        String(50),
        comment='3D Secure status'
    )
    
    three_d_secure_version = Column(
        String(10),
        comment='3D Secure version'
    )
    
    # =========================================================================
    # RECEIPT
    # =========================================================================
    receipt_number = Column(
        String(255),
        comment='Receipt number'
    )
    
    receipt_url = Column(
        String(500),
        comment='URL to receipt'
    )
    
    receipt_sent = Column(
        Boolean,
        server_default='false',
        comment='Whether receipt was sent'
    )
    
    receipt_sent_at = Column(
        DateTime(timezone=True),
        comment='When receipt was sent'
    )
    
    # =========================================================================
    # DESCRIPTION AND METADATA
    # =========================================================================
    description = Column(
        String(500),
        comment='Payment description'
    )
    
    statement_descriptor = Column(
        String(255),
        comment='Statement descriptor'
    )
    
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created this record'
    )
    
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who last updated this record'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='payments',
        comment='User who made payment'
    )
    
    reservation = relationship(
        'Reservation',
        foreign_keys=[reservation_id],
        back_populates='payments',
        comment='Associated reservation'
    )
    
    subscription = relationship(
        'PaymentSubscription',
        foreign_keys=[subscription_id],
        back_populates='payments',
        comment='Associated subscription'
    )
    
    invoice = relationship(
        'PaymentInvoice',
        foreign_keys=[invoice_id],
        back_populates='payments',
        comment='Associated invoice'
    )
    
    payment_method_rel = relationship(
        'PaymentMethod',
        foreign_keys=[payment_method_id],
        comment='Payment method used'
    )
    
    refunds = relationship(
        'PaymentRefund',
        back_populates='payment',
        cascade='all, delete-orphan',
        comment='Refunds for this payment'
    )
    
    transactions = relationship(
        'PaymentTransaction',
        back_populates='payment',
        cascade='all, delete-orphan',
        comment='Detailed transactions'
    )
    
    fees = relationship(
        'PaymentFee',
        back_populates='payment',
        cascade='all, delete-orphan',
        comment='Fees for this payment'
    )
    
    taxes = relationship(
        'PaymentTax',
        back_populates='payment',
        cascade='all, delete-orphan',
        comment='Taxes for this payment'
    )
    
    disputes = relationship(
        'PaymentDispute',
        back_populates='payment',
        cascade='all, delete-orphan',
        comment='Disputes for this payment'
    )
    
    attempts = relationship(
        'PaymentAttempt',
        back_populates='payment',
        cascade='all, delete-orphan',
        comment='Payment attempts'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def is_paid(self) -> bool:
        """Check if payment is paid."""
        return self.status == 'paid'
    
    @hybrid_property
    def is_refunded(self) -> bool:
        """Check if payment is fully refunded."""
        return self.status == 'refunded'
    
    @hybrid_property
    def is_partially_refunded(self) -> bool:
        """Check if payment is partially refunded."""
        return self.status == 'partially_refunded'
    
    @hybrid_property
    def is_failed(self) -> bool:
        """Check if payment failed."""
        return self.status == 'failed'
    
    @hybrid_property
    def is_disputed(self) -> bool:
        """Check if payment is disputed."""
        return self.status in ['disputed', 'chargeback']
    
    @hybrid_property
    def remaining_balance(self) -> float:
        """Get remaining balance after refunds."""
        return float(self.amount) - float(self.amount_refunded)
    
    @hybrid_property
    def refundable_amount(self) -> float:
        """Get amount that can still be refunded."""
        return self.remaining_balance
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @validates('amount')
    def validate_amount(self, key, amount):
        """Validate amount is positive."""
        if amount < 0:
            raise ValueError('Amount must be positive')
        return amount
    
    @validates('currency')
    def validate_currency(self, key, currency):
        """Validate currency code."""
        currency = currency.upper()
        if currency not in [c.value for c in Currency]:
            raise ValueError(f'Unsupported currency: {currency}')
        return currency
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def authorize(self, authorization_code: str, expires_in_hours: int = 168) -> None:
        """
        Authorize payment (but don't capture yet).
        
        Args:
            authorization_code: Authorization code from provider
            expires_in_hours: Hours until authorization expires
        """
        self.status = 'authorized'
        self.authorized_at = datetime.now()
        self.authorization_code = authorization_code
        self.authorization_expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        self._add_transaction('authorization', self.amount)
    
    def capture(self, amount: Optional[float] = None) -> None:
        """
        Capture an authorized payment.
        
        Args:
            amount: Amount to capture (None for full amount)
        """
        if self.status != 'authorized':
            raise ValueError('Payment must be authorized before capture')
        
        capture_amount = amount or float(self.amount)
        if capture_amount > float(self.amount):
            raise ValueError('Capture amount cannot exceed authorized amount')
        
        self.status = 'paid'
        self.captured_at = datetime.now()
        self.amount_captured = capture_amount
        self.paid_at = datetime.now()
        
        self._add_transaction('capture', capture_amount)
    
    def void(self) -> None:
        """Void an authorized payment."""
        if self.status != 'authorized':
            raise ValueError('Only authorized payments can be voided')
        
        self.status = 'voided'
        self.cancelled_at = datetime.now()
        self._add_transaction('void', self.amount)
    
    def fail(self, code: str, message: str) -> None:
        """
        Mark payment as failed.
        
        Args:
            code: Failure code
            message: Failure message
        """
        self.status = 'failed'
        self.failed_at = datetime.now()
        self.failure_code = code
        self.failure_message = message
        self._add_transaction('failed', self.amount, error=message)
    
    def process_refund(
        self,
        amount: float,
        reason: str,
        user_id: Optional[uuid.UUID] = None
    ) -> 'PaymentRefund':
        """
        Process a refund for this payment.
        
        Args:
            amount: Amount to refund
            reason: Reason for refund
            user_id: ID of user processing refund
            
        Returns:
            PaymentRefund instance
        """
        if amount > self.refundable_amount:
            raise ValueError(f'Refund amount {amount} exceeds refundable amount {self.refundable_amount}')
        
        from models.payment import PaymentRefund
        
        refund = PaymentRefund(
            payment_id=self.id,
            amount=amount,
            currency=self.currency,
            reason=reason,
            status='pending',
            requested_at=datetime.now(),
            created_by=user_id
        )
        
        object_session(self).add(refund)
        
        # Update refunded amount
        self.amount_refunded = float(self.amount_refunded) + amount
        
        # Update status
        if self.amount_refunded >= float(self.amount):
            self.status = 'refunded'
        else:
            self.status = 'partially_refunded'
        
        self._add_transaction('refund', amount, reference=str(refund.id))
        
        return refund
    
    def mark_disputed(self, dispute_id: str, reason: str, amount: float) -> None:
        """
        Mark payment as disputed.
        
        Args:
            dispute_id: Dispute ID
            reason: Dispute reason
            amount: Disputed amount
        """
        self.status = 'disputed'
        self._add_transaction('chargeback', amount, reference=dispute_id)
    
    def generate_receipt(self) -> Dict[str, Any]:
        """
        Generate payment receipt data.
        
        Returns:
            Receipt data dictionary
        """
        receipt = {
            'receipt_number': self.receipt_number or f"RCP-{self.payment_number}",
            'payment_number': self.payment_number,
            'date': self.paid_at or self.created_at,
            'customer': {
                'name': self.user.display_name if self.user else None,
                'email': self.user.email if self.user else None,
            },
            'amount': float(self.amount),
            'currency': self.currency,
            'amount_refunded': float(self.amount_refunded),
            'net_amount': float(self.amount_net) if self.amount_net else float(self.amount),
            'payment_method': self.payment_method_type,
            'description': self.description,
            'items': []
        }
        
        # Add reservation details if available
        if self.reservation:
            receipt['items'].append({
                'type': 'reservation',
                'description': f"Parking reservation {self.reservation.reservation_number}",
                'amount': float(self.reservation.total_amount),
                'dates': {
                    'start': self.reservation.start_time.isoformat(),
                    'end': self.reservation.end_time.isoformat()
                }
            })
        
        # Add fee breakdown
        for fee in self.fees:
            receipt['items'].append({
                'type': 'fee',
                'description': fee.description,
                'amount': float(fee.amount)
            })
        
        # Add tax breakdown
        for tax in self.taxes:
            receipt['items'].append({
                'type': 'tax',
                'description': tax.tax_name,
                'amount': float(tax.tax_amount),
                'rate': float(tax.tax_rate)
            })
        
        self.receipt_number = receipt['receipt_number']
        
        return receipt
    
    def send_receipt(self, channel: str = 'email') -> bool:
        """
        Send payment receipt to customer.
        
        Args:
            channel: Delivery channel (email, sms)
            
        Returns:
            True if sent successfully
        """
        receipt = self.generate_receipt()
        
        # This would integrate with notification service
        self.receipt_sent = True
        self.receipt_sent_at = datetime.now()
        
        return True
    
    def _add_transaction(
        self,
        transaction_type: str,
        amount: float,
        reference: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Add a transaction record.
        
        Args:
            transaction_type: Type of transaction
            amount: Transaction amount
            reference: Reference ID
            error: Error message if applicable
        """
        from models.payment import PaymentTransaction
        
        transaction = PaymentTransaction(
            payment_id=self.id,
            transaction_type=transaction_type,
            amount=amount,
            currency=self.currency,
            provider_transaction_id=reference,
            status='completed' if not error else 'failed',
            error_message=error,
            processed_at=datetime.now()
        )
        
        object_session(self).add(transaction)
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert payment to dictionary."""
        data = {
            'id': str(self.id),
            'payment_number': self.payment_number,
            'external_id': self.external_id,
            'user_id': str(self.user_id) if self.user_id else None,
            'reservation_id': str(self.reservation_id) if self.reservation_id else None,
            'subscription_id': str(self.subscription_id) if self.subscription_id else None,
            'invoice_id': str(self.invoice_id) if self.invoice_id else None,
            'amount': float(self.amount),
            'currency': self.currency,
            'amount_refunded': float(self.amount_refunded),
            'amount_net': float(self.amount_net) if self.amount_net else None,
            'status': self.status,
            'payment_method_type': self.payment_method_type,
            'provider': self.provider,
            'transaction_type': self.transaction_type,
            'authorized_at': self.authorized_at.isoformat() if self.authorized_at else None,
            'captured_at': self.captured_at.isoformat() if self.captured_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'failure_code': self.failure_code,
            'failure_message': self.failure_message,
            'receipt_number': self.receipt_number,
            'receipt_url': self.receipt_url,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data.update({
                'risk_score': self.risk_score,
                'risk_level': self.risk_level,
                'fraud_check_passed': self.fraud_check_passed,
                'three_d_secure_used': self.three_d_secure_used,
                'provider_payment_id': self.provider_payment_id,
                'provider_transaction_id': self.provider_transaction_id,
                'metadata': self.metadata,
            })
        
        return data
    
    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, number={self.payment_number}, amount={self.amount}, status={self.status})>"


class PaymentMethod(Base):
    """
    Saved payment methods for users.
    
    Stores payment method details securely with PCI compliance considerations.
    Supports credit cards, bank accounts, digital wallets, and more.
    """
    
    __tablename__ = 'payment_methods'
    __table_args__ = (
        Index('ix_payment_methods_user', 'user_id'),
        Index('ix_payment_methods_provider_id', 'provider_payment_method_id'),
        Index('ix_payment_methods_token', 'token'),
        Index('ix_payment_methods_card_fingerprint', 'card_fingerprint'),
        Index('ix_payment_methods_is_default', 'is_default'),
        Index('ix_payment_methods_is_active', 'is_active'),
        {'comment': 'Saved payment methods for users'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    
    payment_method_type = Column(
        String(50),
        nullable=False,
        comment='Type of payment method'
    )
    
    provider = Column(
        String(50),
        nullable=False,
        comment='Payment provider'
    )
    
    provider_payment_method_id = Column(
        String(255),
        comment='Provider payment method ID'
    )
    
    provider_customer_id = Column(
        String(255),
        comment='Provider customer ID'
    )
    
    token = Column(
        String(255),
        comment='Tokenized representation'
    )
    
    # =========================================================================
    # CARD DETAILS
    # =========================================================================
    card_last4 = Column(
        String(4),
        comment='Last 4 digits of card'
    )
    
    card_brand = Column(
        String(50),
        comment='Card brand (Visa, Mastercard, etc.)'
    )
    
    card_expiry_month = Column(
        Integer,
        comment='Card expiry month'
    )
    
    card_expiry_year = Column(
        Integer,
        comment='Card expiry year'
    )
    
    card_holder_name = Column(
        String(255),
        comment='Card holder name'
    )
    
    card_fingerprint = Column(
        String(255),
        comment='Unique card fingerprint'
    )
    
    card_country = Column(
        String(2),
        comment='Card country code'
    )
    
    card_funding = Column(
        String(20),
        comment='Card funding type (credit, debit, prepaid)'
    )
    
    # =========================================================================
    # BANK ACCOUNT DETAILS
    # =========================================================================
    bank_account_last4 = Column(
        String(4),
        comment='Last 4 digits of bank account'
    )
    
    bank_account_type = Column(
        String(50),
        comment='Bank account type (checking, savings)'
    )
    
    bank_name = Column(
        String(255),
        comment='Bank name'
    )
    
    bank_routing_number = Column(
        String(50),
        comment='Bank routing number'
    )
    
    bank_country = Column(
        String(2),
        comment='Bank country code'
    )
    
    # =========================================================================
    # DIGITAL WALLET DETAILS
    # =========================================================================
    wallet_type = Column(
        String(50),
        comment='Wallet type (apple_pay, google_pay, paypal)'
    )
    
    wallet_email = Column(
        String(255),
        comment='Wallet email address'
    )
    
    # =========================================================================
    # BILLING ADDRESS
    # =========================================================================
    billing_address_line1 = Column(
        String(255),
        comment='Billing address line 1'
    )
    
    billing_address_line2 = Column(
        String(255),
        comment='Billing address line 2'
    )
    
    billing_city = Column(
        String(100),
        comment='Billing city'
    )
    
    billing_state = Column(
        String(50),
        comment='Billing state/province'
    )
    
    billing_postal_code = Column(
        String(20),
        comment='Billing postal code'
    )
    
    billing_country = Column(
        String(2),
        comment='Billing country code'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    is_default = Column(
        Boolean,
        server_default='false',
        comment='Whether this is the default payment method'
    )
    
    is_verified = Column(
        Boolean,
        server_default='false',
        comment='Whether payment method is verified'
    )
    
    verified_at = Column(
        DateTime(timezone=True),
        comment='When payment method was verified'
    )
    
    is_expired = Column(
        Boolean,
        server_default='false',
        comment='Whether payment method has expired'
    )
    
    expired_at = Column(
        DateTime(timezone=True),
        comment='When payment method expired'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether payment method is active'
    )
    
    deactivated_at = Column(
        DateTime(timezone=True),
        comment='When payment method was deactivated'
    )
    
    deactivation_reason = Column(
        String(255),
        comment='Reason for deactivation'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        comment='Soft delete timestamp'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship('User', back_populates='payment_methods')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def is_expired_card(self) -> bool:
        """Check if card is expired."""
        if not self.card_expiry_year or not self.card_expiry_month:
            return False
        
        now = datetime.now()
        if self.card_expiry_year < now.year:
            return True
        if self.card_expiry_year == now.year and self.card_expiry_month < now.month:
            return True
        return False
    
    def mask(self) -> Dict[str, Any]:
        """Return masked version of payment method for API responses."""
        data = {
            'id': str(self.id),
            'type': self.payment_method_type,
            'is_default': self.is_default,
            'is_verified': self.is_verified,
            'billing_address': {
                'line1': self.billing_address_line1,
                'city': self.billing_city,
                'state': self.billing_state,
                'postal_code': self.billing_postal_code,
                'country': self.billing_country
            } if self.billing_address_line1 else None
        }
        
        if self.payment_method_type in ['credit_card', 'debit_card']:
            data.update({
                'card': {
                    'brand': self.card_brand,
                    'last4': self.card_last4,
                    'expiry_month': self.card_expiry_month,
                    'expiry_year': self.card_expiry_year,
                    'holder_name': self.card_holder_name,
                    'is_expired': self.is_expired_card()
                }
            })
        elif self.payment_method_type == 'paypal':
            data.update({
                'paypal': {
                    'email': self.wallet_email
                }
            })
        elif self.payment_method_type == 'bank_transfer':
            data.update({
                'bank': {
                    'name': self.bank_name,
                    'account_last4': self.bank_account_last4,
                    'account_type': self.bank_account_type
                }
            })
        
        return data
    
    def __repr__(self) -> str:
        return f"<PaymentMethod(id={self.id}, user={self.user_id}, type={self.payment_method_type})>"


class PaymentRefund(Base):
    """
    Payment refunds and credits.
    
    Tracks refund requests, approvals, and processing for payments.
    """
    
    __tablename__ = 'payment_refunds'
    __table_args__ = (
        Index('ix_refunds_payment', 'payment_id'),
        Index('ix_refunds_number', 'refund_number', unique=True),
        Index('ix_refunds_provider_id', 'provider_refund_id'),
        Index('ix_refunds_status', 'status'),
        {'comment': 'Payment refunds and credits'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payments.id', ondelete='CASCADE'),
        nullable=False
    )
    
    refund_number = Column(
        String(50),
        nullable=False,
        unique=True
    )
    
    provider_refund_id = Column(
        String(255),
        comment='Provider refund ID'
    )
    
    amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Refund amount'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        comment='Currency code'
    )
    
    reason = Column(
        String(255),
        comment='Refund reason'
    )
    
    reason_code = Column(
        String(100),
        comment='Refund reason code'
    )
    
    status = Column(
        String(50),
        nullable=False,
        comment='Refund status'
    )
    
    refund_method = Column(
        String(50),
        comment='Refund method (original, balance, other)'
    )
    
    failure_reason = Column(
        Text,
        comment='Failure reason if refund failed'
    )
    
    # =========================================================================
    # TIMING
    # =========================================================================
    requested_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When refund was requested'
    )
    
    processed_at = Column(
        DateTime(timezone=True),
        comment='When refund was processed'
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        comment='When refund was completed'
    )
    
    # =========================================================================
    # APPROVAL
    # =========================================================================
    requires_approval = Column(
        Boolean,
        server_default='false',
        comment='Whether refund requires approval'
    )
    
    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who approved refund'
    )
    
    approved_at = Column(
        DateTime(timezone=True),
        comment='When refund was approved'
    )
    
    approval_notes = Column(
        Text,
        comment='Approval notes'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created refund'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    payment = relationship('Payment', back_populates='refunds')
    approver = relationship('User', foreign_keys=[approved_by])
    creator = relationship('User', foreign_keys=[created_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def approve(self, user_id: uuid.UUID, notes: Optional[str] = None) -> None:
        """Approve refund."""
        self.requires_approval = False
        self.approved_by = user_id
        self.approved_at = datetime.now()
        self.approval_notes = notes
    
    def process(self, provider_refund_id: str) -> None:
        """Process refund."""
        self.status = 'processing'
        self.provider_refund_id = provider_refund_id
        self.processed_at = datetime.now()
    
    def complete(self) -> None:
        """Complete refund."""
        self.status = 'succeeded'
        self.completed_at = datetime.now()
    
    def fail(self, reason: str) -> None:
        """Mark refund as failed."""
        self.status = 'failed'
        self.failure_reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert refund to dictionary."""
        return {
            'id': str(self.id),
            'payment_id': str(self.payment_id),
            'refund_number': self.refund_number,
            'amount': float(self.amount),
            'currency': self.currency,
            'reason': self.reason,
            'status': self.status,
            'requested_at': self.requested_at.isoformat() if self.requested_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'requires_approval': self.requires_approval,
            'approved_by': str(self.approved_by) if self.approved_by else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<PaymentRefund(id={self.id}, payment={self.payment_id}, amount={self.amount})>"


class PaymentTransaction(Base):
    """
    Detailed transaction log for each payment.
    
    Tracks all individual transactions within a payment, including
    authorizations, captures, refunds, and provider responses.
    """
    
    __tablename__ = 'payment_transactions'
    __table_args__ = (
        Index('ix_payment_transactions_payment', 'payment_id'),
        Index('ix_payment_transactions_type', 'transaction_type'),
        Index('ix_payment_transactions_provider_id', 'provider_transaction_id'),
        {'comment': 'Detailed transaction log'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payments.id', ondelete='CASCADE'),
        nullable=False
    )
    
    transaction_type = Column(
        String(50),
        nullable=False,
        comment='Type of transaction'
    )
    
    amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Transaction amount'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        comment='Currency code'
    )
    
    balance_transaction_id = Column(
        String(255),
        comment='Balance transaction ID'
    )
    
    provider_transaction_id = Column(
        String(255),
        comment='Provider transaction ID'
    )
    
    status = Column(
        String(50),
        nullable=False,
        comment='Transaction status'
    )
    
    provider_response = Column(
        JSONB,
        comment='Full provider response'
    )
    
    error_code = Column(
        String(100),
        comment='Error code if failed'
    )
    
    error_message = Column(
        Text,
        comment='Error message if failed'
    )
    
    processed_at = Column(
        DateTime(timezone=True),
        comment='When transaction was processed'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    payment = relationship('Payment', back_populates='transactions')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary."""
        return {
            'id': str(self.id),
            'payment_id': str(self.payment_id),
            'transaction_type': self.transaction_type,
            'amount': float(self.amount),
            'currency': self.currency,
            'provider_transaction_id': self.provider_transaction_id,
            'status': self.status,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<PaymentTransaction(id={self.id}, type={self.transaction_type}, amount={self.amount})>"


class PaymentFee(Base):
    """
    Fees associated with payments.
    
    Tracks processing fees, convenience fees, and other charges
    applied to payments.
    """
    
    __tablename__ = 'payment_fees'
    __table_args__ = (
        Index('ix_fees_payment', 'payment_id'),
        Index('ix_fees_type', 'fee_type'),
        {'comment': 'Payment fees'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payments.id', ondelete='CASCADE'),
        nullable=False
    )
    
    fee_type = Column(
        String(50),
        nullable=False,
        comment='Type of fee'
    )
    
    description = Column(
        String(255),
        comment='Fee description'
    )
    
    amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Fee amount'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        comment='Currency code'
    )
    
    percentage_rate = Column(
        Numeric(5, 2),
        comment='Percentage rate if applicable'
    )
    
    fixed_rate = Column(
        Numeric(10, 2),
        comment='Fixed rate if applicable'
    )
    
    provider_fee_id = Column(
        String(255),
        comment='Provider fee ID'
    )
    
    is_refundable = Column(
        Boolean,
        server_default='false',
        comment='Whether fee is refundable'
    )
    
    refunded_amount = Column(
        Numeric(10, 2),
        server_default='0',
        comment='Amount refunded'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    payment = relationship('Payment', back_populates='fees')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert fee to dictionary."""
        return {
            'id': str(self.id),
            'payment_id': str(self.payment_id),
            'fee_type': self.fee_type,
            'description': self.description,
            'amount': float(self.amount),
            'currency': self.currency,
            'percentage_rate': float(self.percentage_rate) if self.percentage_rate else None,
            'fixed_rate': float(self.fixed_rate) if self.fixed_rate else None,
            'is_refundable': self.is_refundable,
            'refunded_amount': float(self.refunded_amount) if self.refunded_amount else None,
        }
    
    def __repr__(self) -> str:
        return f"<PaymentFee(id={self.id}, type={self.fee_type}, amount={self.amount})>"


class PaymentTax(Base):
    """
    Taxes applied to payments.
    
    Tracks tax amounts, rates, and jurisdictions for tax reporting.
    """
    
    __tablename__ = 'payment_taxes'
    __table_args__ = (
        Index('ix_taxes_payment', 'payment_id'),
        {'comment': 'Payment taxes'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payments.id', ondelete='CASCADE'),
        nullable=False
    )
    
    tax_name = Column(
        String(100),
        nullable=False,
        comment='Tax name'
    )
    
    tax_rate = Column(
        Numeric(5, 2),
        nullable=False,
        comment='Tax rate percentage'
    )
    
    tax_amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Tax amount'
    )
    
    tax_jurisdiction = Column(
        String(100),
        comment='Tax jurisdiction'
    )
    
    tax_type = Column(
        String(50),
        comment='Tax type (sales, vat, gst)'
    )
    
    tax_number = Column(
        String(100),
        comment='Tax number'
    )
    
    is_recoverable = Column(
        Boolean,
        server_default='false',
        comment='Whether tax is recoverable'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    payment = relationship('Payment', back_populates='taxes')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tax to dictionary."""
        return {
            'id': str(self.id),
            'payment_id': str(self.payment_id),
            'tax_name': self.tax_name,
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'tax_jurisdiction': self.tax_jurisdiction,
            'tax_type': self.tax_type,
            'tax_number': self.tax_number,
            'is_recoverable': self.is_recoverable,
        }
    
    def __repr__(self) -> str:
        return f"<PaymentTax(id={self.id}, name={self.tax_name}, rate={self.tax_rate})>"


class PaymentDispute(Base):
    """
    Payment disputes and chargebacks.
    
    Tracks disputes filed against payments, including evidence,
    status, and resolution.
    """
    
    __tablename__ = 'payment_disputes'
    __table_args__ = (
        Index('ix_disputes_payment', 'payment_id'),
        Index('ix_disputes_provider_id', 'provider_dispute_id'),
        Index('ix_disputes_status', 'status'),
        Index('ix_disputes_reason', 'dispute_reason'),
        {'comment': 'Payment disputes'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payments.id', ondelete='CASCADE'),
        nullable=False
    )
    
    provider_dispute_id = Column(
        String(255),
        comment='Provider dispute ID'
    )
    
    dispute_reason = Column(
        String(100),
        nullable=False,
        comment='Dispute reason'
    )
    
    dispute_reason_description = Column(
        Text,
        comment='Detailed reason'
    )
    
    amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Disputed amount'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        comment='Currency code'
    )
    
    status = Column(
        String(50),
        nullable=False,
        comment='Dispute status'
    )
    
    evidence_due_by = Column(
        DateTime(timezone=True),
        comment='Evidence submission deadline'
    )
    
    evidence_submitted_at = Column(
        DateTime(timezone=True),
        comment='When evidence was submitted'
    )
    
    evidence = Column(
        JSONB,
        comment='Evidence submitted'
    )
    
    customer_communication = Column(
        Text,
        comment='Communication with customer'
    )
    
    transaction_details = Column(
        JSONB,
        comment='Transaction details'
    )
    
    # =========================================================================
    # TIMELINE
    # =========================================================================
    opened_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When dispute was opened'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    closed_at = Column(
        DateTime(timezone=True),
        comment='When dispute was closed'
    )
    
    resolved_at = Column(
        DateTime(timezone=True),
        comment='When dispute was resolved'
    )
    
    # =========================================================================
    # OUTCOME
    # =========================================================================
    outcome = Column(
        String(50),
        comment='Dispute outcome (won, lost, accepted)'
    )
    
    outcome_amount = Column(
        Numeric(10, 2),
        comment='Amount after outcome'
    )
    
    outcome_reason = Column(
        Text,
        comment='Outcome reason'
    )
    
    # =========================================================================
    # FEES
    # =========================================================================
    dispute_fee = Column(
        Numeric(10, 2),
        comment='Dispute fee'
    )
    
    dispute_fee_currency = Column(
        String(3),
        comment='Dispute fee currency'
    )
    
    dispute_fee_refunded = Column(
        Boolean,
        server_default='false',
        comment='Whether dispute fee was refunded'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created dispute record'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    payment = relationship('Payment', back_populates='disputes')
    creator = relationship('User', foreign_keys=[created_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def submit_evidence(self, evidence_data: Dict[str, Any]) -> None:
        """Submit evidence for dispute."""
        self.evidence = evidence_data
        self.evidence_submitted_at = datetime.now()
    
    def resolve(self, outcome: str, amount: Optional[float] = None) -> None:
        """Resolve dispute."""
        self.status = 'closed'
        self.outcome = outcome
        self.outcome_amount = amount
        self.resolved_at = datetime.now()
        self.closed_at = datetime.now()
        
        # Update payment status based on outcome
        if outcome in ['lost', 'accepted']:
            self.payment.status = 'chargeback'
        elif outcome == 'won':
            self.payment.status = 'paid'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert dispute to dictionary."""
        return {
            'id': str(self.id),
            'payment_id': str(self.payment_id),
            'provider_dispute_id': self.provider_dispute_id,
            'dispute_reason': self.dispute_reason,
            'amount': float(self.amount),
            'currency': self.currency,
            'status': self.status,
            'evidence_due_by': self.evidence_due_by.isoformat() if self.evidence_due_by else None,
            'evidence_submitted_at': self.evidence_submitted_at.isoformat() if self.evidence_submitted_at else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'outcome': self.outcome,
            'outcome_amount': float(self.outcome_amount) if self.outcome_amount else None,
            'dispute_fee': float(self.dispute_fee) if self.dispute_fee else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<PaymentDispute(id={self.id}, reason={self.dispute_reason}, status={self.status})>"


class PaymentAttempt(Base):
    """
    Payment retry attempts for failed payments.
    
    Tracks multiple attempts to process a payment with retry logic.
    """
    
    __tablename__ = 'payment_attempts'
    __table_args__ = (
        Index('ix_attempts_payment', 'payment_id'),
        Index('ix_attempts_status', 'status'),
        Index('ix_attempts_next', 'next_attempt_at'),
        {'comment': 'Payment retry attempts'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payments.id', ondelete='CASCADE'),
        nullable=False
    )
    
    attempt_number = Column(
        Integer,
        nullable=False,
        comment='Attempt number'
    )
    
    status = Column(
        String(50),
        nullable=False,
        comment='Attempt status'
    )
    
    amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Attempt amount'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        comment='Currency code'
    )
    
    payment_method_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payment_methods.id', ondelete='SET NULL'),
        comment='Payment method used'
    )
    
    provider_response = Column(
        JSONB,
        comment='Provider response'
    )
    
    error_code = Column(
        String(100),
        comment='Error code if failed'
    )
    
    error_message = Column(
        Text,
        comment='Error message if failed'
    )
    
    error_type = Column(
        String(100),
        comment='Error type'
    )
    
    attempted_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When attempt was made'
    )
    
    next_attempt_at = Column(
        DateTime(timezone=True),
        comment='When next attempt should be made'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    payment = relationship('Payment', back_populates='attempts')
    payment_method = relationship('PaymentMethod')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert attempt to dictionary."""
        return {
            'id': str(self.id),
            'payment_id': str(self.payment_id),
            'attempt_number': self.attempt_number,
            'status': self.status,
            'amount': float(self.amount),
            'currency': self.currency,
            'payment_method_id': str(self.payment_method_id) if self.payment_method_id else None,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'attempted_at': self.attempted_at.isoformat() if self.attempted_at else None,
            'next_attempt_at': self.next_attempt_at.isoformat() if self.next_attempt_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<PaymentAttempt(id={self.id}, attempt={self.attempt_number}, status={self.status})>"


class PaymentSubscription(Base):
    """
    Recurring subscriptions for regular parking.
    
    Manages recurring payments for monthly parking, VIP access, etc.
    """
    
    __tablename__ = 'payment_subscriptions'
    __table_args__ = (
        Index('ix_subscriptions_user', 'user_id'),
        Index('ix_subscriptions_number', 'subscription_number', unique=True),
        Index('ix_subscriptions_provider_id', 'provider_subscription_id'),
        Index('ix_subscriptions_status', 'status'),
        Index('ix_subscriptions_period_end', 'current_period_end'),
        Index('ix_subscriptions_user_active', 'user_id', 'status'),
        Index('ix_subscriptions_active_renewal', 'status', 'current_period_end'),
        {'comment': 'Recurring subscriptions'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    
    subscription_number = Column(
        String(50),
        nullable=False,
        unique=True
    )
    
    provider_subscription_id = Column(
        String(255),
        comment='Provider subscription ID'
    )
    
    plan_name = Column(
        String(255),
        nullable=False,
        comment='Plan name'
    )
    
    description = Column(
        Text,
        comment='Subscription description'
    )
    
    status = Column(
        String(50),
        nullable=False,
        comment='Subscription status'
    )
    
    interval = Column(
        String(20),
        nullable=False,
        comment='Billing interval'
    )
    
    interval_count = Column(
        Integer,
        server_default='1',
        comment='Number of intervals between billings'
    )
    
    amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Subscription amount'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        comment='Currency code'
    )
    
    # =========================================================================
    # TRIAL
    # =========================================================================
    trial_amount = Column(
        Numeric(10, 2),
        comment='Trial amount'
    )
    
    trial_period_days = Column(
        Integer,
        comment='Trial period in days'
    )
    
    trial_start = Column(
        DateTime(timezone=True),
        comment='Trial start'
    )
    
    trial_end = Column(
        DateTime(timezone=True),
        comment='Trial end'
    )
    
    # =========================================================================
    # CURRENT PERIOD
    # =========================================================================
    current_period_start = Column(
        DateTime(timezone=True),
        comment='Current period start'
    )
    
    current_period_end = Column(
        DateTime(timezone=True),
        comment='Current period end'
    )
    
    # =========================================================================
    # CANCELLATION
    # =========================================================================
    cancel_at_period_end = Column(
        Boolean,
        server_default='false',
        comment='Whether to cancel at period end'
    )
    
    canceled_at = Column(
        DateTime(timezone=True),
        comment='When subscription was canceled'
    )
    
    cancellation_reason = Column(
        Text,
        comment='Cancellation reason'
    )
    
    # =========================================================================
    # PAUSE
    # =========================================================================
    pause_mode = Column(
        String(50),
        comment='Pause mode (void, keep_as_draft)'
    )
    
    paused_at = Column(
        DateTime(timezone=True),
        comment='When subscription was paused'
    )
    
    resumed_at = Column(
        DateTime(timezone=True),
        comment='When subscription was resumed'
    )
    
    # =========================================================================
    # PAYMENT
    # =========================================================================
    past_due_count = Column(
        Integer,
        server_default='0',
        comment='Number of past due periods'
    )
    
    default_payment_method_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payment_methods.id', ondelete='SET NULL'),
        comment='Default payment method'
    )
    
    latest_invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payment_invoices.id', ondelete='SET NULL'),
        comment='Latest invoice'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship('User', back_populates='subscriptions')
    default_payment_method = relationship('PaymentMethod')
    latest_invoice = relationship('PaymentInvoice', foreign_keys=[latest_invoice_id])
    payments = relationship('Payment', back_populates='subscription')
    invoices = relationship('PaymentInvoice', back_populates='subscription')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def cancel(self, reason: Optional[str] = None, immediately: bool = False) -> None:
        """
        Cancel subscription.
        
        Args:
            reason: Cancellation reason
            immediately: Whether to cancel immediately or at period end
        """
        if immediately:
            self.status = 'canceled'
            self.canceled_at = datetime.now()
        else:
            self.cancel_at_period_end = True
        
        self.cancellation_reason = reason
    
    def pause(self, mode: str = 'void') -> None:
        """Pause subscription."""
        self.status = 'paused'
        self.pause_mode = mode
        self.paused_at = datetime.now()
    
    def resume(self) -> None:
        """Resume subscription."""
        self.status = 'active'
        self.resumed_at = datetime.now()
        self.pause_mode = None
    
    def mark_past_due(self) -> None:
        """Mark subscription as past due."""
        self.status = 'past_due'
        self.past_due_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subscription to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'subscription_number': self.subscription_number,
            'plan_name': self.plan_name,
            'description': self.description,
            'status': self.status,
            'interval': self.interval,
            'interval_count': self.interval_count,
            'amount': float(self.amount),
            'currency': self.currency,
            'trial_start': self.trial_start.isoformat() if self.trial_start else None,
            'trial_end': self.trial_end.isoformat() if self.trial_end else None,
            'current_period_start': self.current_period_start.isoformat() if self.current_period_start else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None,
            'cancel_at_period_end': self.cancel_at_period_end,
            'canceled_at': self.canceled_at.isoformat() if self.canceled_at else None,
            'paused_at': self.paused_at.isoformat() if self.paused_at else None,
            'resumed_at': self.resumed_at.isoformat() if self.resumed_at else None,
            'past_due_count': self.past_due_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<PaymentSubscription(id={self.id}, number={self.subscription_number}, status={self.status})>"


class PaymentInvoice(Base):
    """
    Invoices for billing.
    
    Represents invoices generated for payments, subscriptions, and
    one-time charges.
    """
    
    __tablename__ = 'payment_invoices'
    __table_args__ = (
        Index('ix_invoices_number', 'invoice_number', unique=True),
        Index('ix_invoices_user', 'user_id'),
        Index('ix_invoices_subscription', 'subscription_id'),
        Index('ix_invoices_status', 'status'),
        Index('ix_invoices_due_date', 'due_date'),
        {'comment': 'Invoices for billing'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    invoice_number = Column(
        String(50),
        nullable=False,
        unique=True
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payment_subscriptions.id', ondelete='SET NULL')
    )
    
    provider_invoice_id = Column(
        String(255),
        comment='Provider invoice ID'
    )
    
    status = Column(
        String(50),
        nullable=False,
        comment='Invoice status'
    )
    
    amount_due = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Amount due'
    )
    
    amount_paid = Column(
        Numeric(10, 2),
        server_default='0',
        comment='Amount paid'
    )
    
    amount_remaining = Column(
        Numeric(10, 2),
        comment='Amount remaining'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        comment='Currency code'
    )
    
    due_date = Column(
        DateTime(timezone=True),
        comment='Due date'
    )
    
    issued_date = Column(
        DateTime(timezone=True),
        comment='Issue date'
    )
    
    paid_date = Column(
        DateTime(timezone=True),
        comment='Paid date'
    )
    
    voided_date = Column(
        DateTime(timezone=True),
        comment='Voided date'
    )
    
    pdf_url = Column(
        String(500),
        comment='URL to PDF invoice'
    )
    
    invoice_data = Column(
        JSONB,
        comment='Full invoice data'
    )
    
    billing_reason = Column(
        String(100),
        comment='Reason for invoice'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship('User')
    subscription = relationship('PaymentSubscription', back_populates='invoices')
    payments = relationship('Payment', back_populates='invoice')
    lines = relationship('PaymentInvoiceLine', back_populates='invoice', cascade='all, delete-orphan')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    @hybrid_property
    def is_paid(self) -> bool:
        """Check if invoice is paid."""
        return self.status == 'paid'
    
    @hybrid_property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        if self.status == 'open' and self.due_date:
            return datetime.now(self.due_date.tzinfo) > self.due_date
        return False
    
    def mark_paid(self, paid_amount: Optional[float] = None) -> None:
        """Mark invoice as paid."""
        if paid_amount:
            self.amount_paid = paid_amount
        else:
            self.amount_paid = self.amount_due
        
        self.amount_remaining = self.amount_due - self.amount_paid
        self.status = 'paid' if self.amount_remaining <= 0 else 'partially_paid'
        self.paid_date = datetime.now()
    
    def void(self) -> None:
        """Void invoice."""
        self.status = 'void'
        self.voided_date = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert invoice to dictionary."""
        return {
            'id': str(self.id),
            'invoice_number': self.invoice_number,
            'user_id': str(self.user_id),
            'subscription_id': str(self.subscription_id) if self.subscription_id else None,
            'status': self.status,
            'amount_due': float(self.amount_due),
            'amount_paid': float(self.amount_paid),
            'amount_remaining': float(self.amount_remaining) if self.amount_remaining else None,
            'currency': self.currency,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'issued_date': self.issued_date.isoformat() if self.issued_date else None,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'voided_date': self.voided_date.isoformat() if self.voided_date else None,
            'pdf_url': self.pdf_url,
            'billing_reason': self.billing_reason,
            'is_overdue': self.is_overdue,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'lines': [line.to_dict() for line in self.lines] if self.lines else []
        }
    
    def __repr__(self) -> str:
        return f"<PaymentInvoice(id={self.id}, number={self.invoice_number}, status={self.status})>"


class PaymentInvoiceLine(Base):
    """
    Line items for invoices.
    
    Individual line items that make up an invoice total.
    """
    
    __tablename__ = 'payment_invoice_lines'
    __table_args__ = (
        Index('ix_invoice_lines_invoice', 'invoice_id'),
        {'comment': 'Invoice line items'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    invoice_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payment_invoices.id', ondelete='CASCADE'),
        nullable=False
    )
    
    description = Column(
        String(500),
        nullable=False,
        comment='Line item description'
    )
    
    quantity = Column(
        Integer,
        server_default='1',
        comment='Quantity'
    )
    
    unit_price = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Price per unit'
    )
    
    amount = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Total amount'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        comment='Currency code'
    )
    
    period_start = Column(
        DateTime(timezone=True),
        comment='Service period start'
    )
    
    period_end = Column(
        DateTime(timezone=True),
        comment='Service period end'
    )
    
    proration = Column(
        Boolean,
        server_default='false',
        comment='Whether amount is prorated'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    invoice = relationship('PaymentInvoice', back_populates='lines')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert line item to dictionary."""
        return {
            'id': str(self.id),
            'invoice_id': str(self.invoice_id),
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'amount': float(self.amount),
            'currency': self.currency,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'proration': self.proration,
        }
    
    def __repr__(self) -> str:
        return f"<PaymentInvoiceLine(id={self.id}, description={self.description}, amount={self.amount})>"


class PaymentDiscountCode(Base):
    """
    Discount codes and promotions.
    
    Manages discount codes, promotions, and their usage limits.
    """
    
    __tablename__ = 'payment_discount_codes'
    __table_args__ = (
        Index('ix_discount_codes_code', 'code', unique=True),
        Index('ix_discount_codes_valid', 'valid_from', 'valid_to'),
        Index('ix_discount_codes_active', 'is_active'),
        {'comment': 'Discount codes and promotions'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    code = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Discount code'
    )
    
    description = Column(
        Text,
        comment='Code description'
    )
    
    discount_type = Column(
        String(20),
        nullable=False,
        comment='Type of discount'
    )
    
    discount_value = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Discount value'
    )
    
    apply_to = Column(
        String(20),
        nullable=False,
        comment='What the discount applies to'
    )
    
    minimum_amount = Column(
        Numeric(10, 2),
        comment='Minimum purchase amount'
    )
    
    maximum_discount = Column(
        Numeric(10, 2),
        comment='Maximum discount amount'
    )
    
    usage_limit = Column(
        Integer,
        comment='Total usage limit'
    )
    
    usage_count = Column(
        Integer,
        server_default='0',
        comment='Current usage count'
    )
    
    per_user_limit = Column(
        Integer,
        comment='Per-user usage limit'
    )
    
    first_time_only = Column(
        Boolean,
        server_default='false',
        comment='First-time customers only'
    )
    
    valid_from = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Valid from date'
    )
    
    valid_to = Column(
        DateTime(timezone=True),
        comment='Valid to date'
    )
    
    days_of_week = Column(
        ARRAY(Integer),
        comment='Days of week allowed (0=Sunday, 6=Saturday)'
    )
    
    applicable_spots = Column(
        ARRAY(UUID(as_uuid=True)),
        comment='Specific spots discount applies to'
    )
    
    applicable_zones = Column(
        ARRAY(UUID(as_uuid=True)),
        comment='Specific zones discount applies to'
    )
    
    applicable_users = Column(
        ARRAY(UUID(as_uuid=True)),
        comment='Specific users discount applies to'
    )
    
    stackable = Column(
        Boolean,
        server_default='false',
        comment='Whether discount can be stacked'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether discount is active'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created discount'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    creator = relationship('User', foreign_keys=[created_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def is_valid(self, user_id: Optional[uuid.UUID] = None, amount: Optional[float] = None) -> Tuple[bool, str]:
        """
        Check if discount code is valid.
        
        Args:
            user_id: ID of user applying discount
            amount: Purchase amount
            
        Returns:
            Tuple of (is_valid, message)
        """
        now = datetime.now()
        
        # Check date range
        if now < self.valid_from:
            return False, "Discount code not yet active"
        
        if self.valid_to and now > self.valid_to:
            return False, "Discount code has expired"
        
        # Check usage limit
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False, "Discount code usage limit exceeded"
        
        # Check minimum amount
        if self.minimum_amount and amount and amount < self.minimum_amount:
            return False, f"Minimum purchase amount of {self.minimum_amount} required"
        
        return True, "Valid discount code"
    
    def calculate_discount(self, amount: float) -> float:
        """
        Calculate discount amount.
        
        Args:
            amount: Original amount
            
        Returns:
            Discount amount
        """
        if self.discount_type == 'percentage':
            discount = amount * (float(self.discount_value) / 100)
        else:
            discount = float(self.discount_value)
        
        # Apply maximum discount
        if self.maximum_discount and discount > float(self.maximum_discount):
            discount = float(self.maximum_discount)
        
        return discount
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert discount code to dictionary."""
        return {
            'id': str(self.id),
            'code': self.code,
            'description': self.description,
            'discount_type': self.discount_type,
            'discount_value': float(self.discount_value),
            'apply_to': self.apply_to,
            'minimum_amount': float(self.minimum_amount) if self.minimum_amount else None,
            'maximum_discount': float(self.maximum_discount) if self.maximum_discount else None,
            'usage_limit': self.usage_limit,
            'usage_count': self.usage_count,
            'per_user_limit': self.per_user_limit,
            'first_time_only': self.first_time_only,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'days_of_week': self.days_of_week,
            'stackable': self.stackable,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<PaymentDiscountCode(id={self.id}, code={self.code})>"


# =========================================================================
# EVENT LISTENERS
# =========================================================================

@event.listens_for(Payment, 'before_insert')
def payment_before_insert(mapper, connection, target):
    """Generate payment number for new payments."""
    if not target.payment_number:
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Get next sequence number
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(payment_number FROM 11)::INTEGER), 0) + 1
                FROM payments
                WHERE payment_number LIKE :pattern
            """),
            {'pattern': f'PAY-{date_str}-%'}
        )
        seq_num = result.scalar()
        
        target.payment_number = f"PAY-{date_str}-{seq_num:06d}"


@event.listens_for(PaymentRefund, 'before_insert')
def refund_before_insert(mapper, connection, target):
    """Generate refund number for new refunds."""
    if not target.refund_number:
        date_str = datetime.now().strftime('%Y%m%d')
        
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(refund_number FROM 10)::INTEGER), 0) + 1
                FROM payment_refunds
                WHERE refund_number LIKE :pattern
            """),
            {'pattern': f'REF-{date_str}-%'}
        )
        seq_num = result.scalar()
        
        target.refund_number = f"REF-{date_str}-{seq_num:06d}"


@event.listens_for(PaymentInvoice, 'before_insert')
def invoice_before_insert(mapper, connection, target):
    """Generate invoice number for new invoices."""
    if not target.invoice_number:
        date_str = datetime.now().strftime('%Y%m%d')
        
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(invoice_number FROM 10)::INTEGER), 0) + 1
                FROM payment_invoices
                WHERE invoice_number LIKE :pattern
            """),
            {'pattern': f'INV-{date_str}-%'}
        )
        seq_num = result.scalar()
        
        target.invoice_number = f"INV-{date_str}-{seq_num:06d}"


@event.listens_for(PaymentSubscription, 'before_insert')
def subscription_before_insert(mapper, connection, target):
    """Generate subscription number for new subscriptions."""
    if not target.subscription_number:
        date_str = datetime.now().strftime('%Y%m')
        
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(subscription_number FROM 11)::INTEGER), 0) + 1
                FROM payment_subscriptions
                WHERE subscription_number LIKE :pattern
            """),
            {'pattern': f'SUB-{date_str}-%'}
        )
        seq_num = result.scalar()
        
        target.subscription_number = f"SUB-{date_str}-{seq_num:06d}"


@event.listens_for(Payment, 'after_update')
def payment_after_update(mapper, connection, target):
    """Update related records when payment status changes."""
    if target.reservation_id and target.status == 'paid':
        # Update reservation payment status
        connection.execute(
            text("""
                UPDATE reservations
                SET payment_status = 'paid',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :reservation_id
            """),
            {'reservation_id': target.reservation_id}
        )


# =========================================================================
# FACTORY FUNCTIONS
# =========================================================================

def create_payment(
    amount: float,
    currency: str = 'USD',
    user_id: Optional[uuid.UUID] = None,
    reservation_id: Optional[uuid.UUID] = None,
    payment_method_type: Optional[str] = None,
    **kwargs
) -> Payment:
    """
    Factory function to create a new payment.
    
    Args:
        amount: Payment amount
        currency: Currency code
        user_id: ID of user
        reservation_id: ID of reservation
        payment_method_type: Type of payment method
        **kwargs: Additional payment attributes
        
    Returns:
        New Payment instance
    """
    payment = Payment(
        amount=amount,
        currency=currency,
        user_id=user_id,
        reservation_id=reservation_id,
        payment_method_type=payment_method_type,
        **kwargs
    )
    
    return payment


def create_subscription(
    user_id: uuid.UUID,
    plan_name: str,
    amount: float,
    interval: str,
    interval_count: int = 1,
    currency: str = 'USD',
    trial_days: Optional[int] = None,
    **kwargs
) -> PaymentSubscription:
    """
    Factory function to create a new subscription.
    
    Args:
        user_id: ID of user
        plan_name: Name of plan
        amount: Subscription amount
        interval: Billing interval
        interval_count: Number of intervals
        currency: Currency code
        trial_days: Trial period in days
        **kwargs: Additional subscription attributes
        
    Returns:
        New PaymentSubscription instance
    """
    now = datetime.now()
    
    subscription = PaymentSubscription(
        user_id=user_id,
        plan_name=plan_name,
        amount=amount,
        interval=interval,
        interval_count=interval_count,
        currency=currency,
        status='active',
        current_period_start=now,
        **kwargs
    )
    
    if trial_days:
        subscription.trial_period_days = trial_days
        subscription.trial_start = now
        subscription.trial_end = now + timedelta(days=trial_days)
        subscription.current_period_start = subscription.trial_end
        subscription.current_period_end = subscription.trial_end + timedelta(days=30)
    else:
        subscription.current_period_end = now + timedelta(days=30)
    
    return subscription


# =========================================================================
# EXPORTS
# =========================================================================

__all__ = [
    'Payment',
    'PaymentMethod',
    'PaymentRefund',
    'PaymentTransaction',
    'PaymentFee',
    'PaymentTax',
    'PaymentDispute',
    'PaymentAttempt',
    'PaymentSubscription',
    'PaymentInvoice',
    'PaymentInvoiceLine',
    'PaymentDiscountCode',
    'PaymentStatus',
    'PaymentMethodType',
    'PaymentProvider',
    'TransactionType',
    'DisputeStatus',
    'DisputeReason',
    'SubscriptionStatus',
    'SubscriptionInterval',
    'InvoiceStatus',
    'DiscountType',
    'DiscountApplyTo',
    'FeeType',
    'Currency',
    'create_payment',
    'create_subscription',
]