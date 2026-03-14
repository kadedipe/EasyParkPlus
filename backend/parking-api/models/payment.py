"""
Payment model for processing payments.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Column, String, Float, Enum, ForeignKey, Integer,
    Boolean, JSON, DateTime, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, AuditMixin


class PaymentStatus(str, enum.Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    """Payment method enumeration."""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    BANK_TRANSFER = "bank_transfer"
    CASH = "cash"
    LOYALTY_POINTS = "loyalty_points"
    GIFT_CARD = "gift_card"


class PaymentProvider(str, enum.Enum):
    """Payment provider enumeration."""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    BRAINTREE = "braintree"
    AUTHORIZE_NET = "authorize_net"
    SQUARE = "square"
    CUSTOM = "custom"


class Payment(Base, TimestampMixin, AuditMixin):
    """
    Payment model for processing payments.
    """
    
    __tablename__ = "payments"
    
    # Foreign Keys
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    reservation_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("reservations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Payment Details
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod),
        nullable=False
    )
    payment_provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider),
        nullable=False,
        default=PaymentProvider.STRIPE
    )
    
    # Transaction Details
    transaction_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        index=True
    )
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(255))
    provider_customer_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Payment Method Details (tokenized)
    payment_method_token: Mapped[Optional[str]] = mapped_column(String(500))
    payment_method_last4: Mapped[Optional[str]] = mapped_column(String(4))
    card_brand: Mapped[Optional[str]] = mapped_column(String(50))
    card_expiry_month: Mapped[Optional[int]] = mapped_column(Integer)
    card_expiry_year: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Billing Information
    billing_name: Mapped[Optional[str]] = mapped_column(String(100))
    billing_email: Mapped[Optional[str]] = mapped_column(String(255))
    billing_phone: Mapped[Optional[str]] = mapped_column(String(20))
    billing_address: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Refund Information
    refunded_amount: Mapped[float] = mapped_column(Float, default=0.0)
    refund_reason: Mapped[Optional[str]] = mapped_column(String(255))
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    refund_transaction_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Receipt
    receipt_url: Mapped[Optional[str]] = mapped_column(String(500))
    receipt_number: Mapped[Optional[str]] = mapped_column(String(100))
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    provider_response: Mapped[Optional[dict]] = mapped_column(JSON)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payments")
    reservation: Mapped[Optional["Reservation"]] = relationship(
        "Reservation",
        back_populates="payments"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_payments_user_status", "user_id", "status"),
        Index("ix_payments_reservation", "reservation_id"),
        Index("ix_payments_created_at", "created_at"),
        Index("ix_payments_provider_id", "provider_payment_id"),
    )
    
    @property
    def is_completed(self) -> bool:
        """Check if payment is completed."""
        return self.status == PaymentStatus.COMPLETED
    
    @property
    def is_refunded(self) -> bool:
        """Check if payment is fully refunded."""
        return self.status == PaymentStatus.REFUNDED
    
    @property
    def remaining_amount(self) -> float:
        """Get remaining amount after refunds."""
        return self.amount - self.refunded_amount
    
    def __repr__(self) -> str:
        return f"<Payment {self.amount} {self.currency} - {self.status.value}>"