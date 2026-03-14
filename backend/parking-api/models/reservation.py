"""
Reservation model for parking reservations.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Column, String, DateTime, Float, Enum, ForeignKey,
    Integer, Boolean, Text, Index, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, AuditMixin

if TYPE_CHECKING:
    from .user import User
    from .vehicle import Vehicle
    from .parking_spot import ParkingSpot
    from .payment import Payment
    from .review import Review


class ReservationStatus(str, enum.Enum):
    """Reservation status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    EXPIRED = "expired"


class Reservation(Base, TimestampMixin, AuditMixin):
    """
    Reservation model for parking reservations.
    """
    
    __tablename__ = "reservations"
    
    # Foreign Keys
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    spot_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("parking_spots.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    vehicle_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Time Range
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # Status
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus),
        nullable=False,
        default=ReservationStatus.PENDING,
        index=True
    )
    
    # Pricing
    base_price: Mapped[float] = mapped_column(Float, nullable=False)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    
    # Price Breakdown (JSON for audit)
    price_breakdown: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Check-in/out
    check_in_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    check_out_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # QR Code
    qr_code: Mapped[Optional[str]] = mapped_column(Text)
    qr_code_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Cancellation
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(255))
    cancellation_fee: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Extensions
    extended_count: Mapped[int] = mapped_column(Integer, default=0)
    original_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Notifications
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    reminder_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reservations")
    spot: Mapped["ParkingSpot"] = relationship("ParkingSpot", back_populates="reservations")
    vehicle: Mapped[Optional["Vehicle"]] = relationship("Vehicle", back_populates="reservations")
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="reservation",
        cascade="all, delete-orphan"
    )
    review: Mapped[Optional["Review"]] = relationship(
        "Review",
        back_populates="reservation",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_reservations_time_range", "start_time", "end_time"),
        Index("ix_reservations_user_status", "user_id", "status"),
        Index("ix_reservations_spot_status", "spot_id", "status"),
        Index("ix_reservations_created_at", "created_at"),
        CheckConstraint(
            "end_time > start_time",
            name="chk_reservation_time_range"
        ),
    )
    
    @property
    def duration_hours(self) -> float:
        """Get reservation duration in hours."""
        return (self.end_time - self.start_time).total_seconds() / 3600
    
    @property
    def actual_duration_hours(self) -> Optional[float]:
        """Get actual duration in hours if checked in."""
        if self.check_in_time and self.check_out_time:
            return (self.check_out_time - self.check_in_time).total_seconds() / 3600
        return None
    
    @property
    def is_active(self) -> bool:
        """Check if reservation is active."""
        return self.status == ReservationStatus.ACTIVE
    
    @property
    def is_cancellable(self) -> bool:
        """Check if reservation can be cancelled."""
        return self.status in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]
    
    @property
    def is_modifiable(self) -> bool:
        """Check if reservation can be modified."""
        return self.status in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]
    
    def __repr__(self) -> str:
        return f"<Reservation {self.id} - {self.status.value}>"