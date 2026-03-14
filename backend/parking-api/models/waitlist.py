"""
Waitlist model for users waiting for parking spots.
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey,
    Integer, Boolean, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin
from .parking_spot import ParkingSpotType


class WaitlistStatus(str, enum.Enum):
    """Waitlist status enumeration."""
    WAITING = "waiting"
    NOTIFIED = "notified"
    RESERVED = "reserved"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WaitlistEntry(Base, TimestampMixin):
    """
    Waitlist model for users waiting for parking spots.
    """
    
    __tablename__ = "waitlist_entries"
    
    # Foreign Keys
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Waitlist Details
    spot_type: Mapped[ParkingSpotType] = mapped_column(
        Enum(ParkingSpotType),
        nullable=False,
        index=True
    )
    status: Mapped[WaitlistStatus] = mapped_column(
        Enum(WaitlistStatus),
        nullable=False,
        default=WaitlistStatus.WAITING,
        index=True
    )
    
    # Time Preferences
    preferred_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    preferred_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    preferred_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    flexible_timing: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Queue Position
    position: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    estimated_wait_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Notification
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notification_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    response_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Result
    reservation_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("reservations.id", ondelete="SET NULL")
    )
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="waitlist_entries")
    reservation: Mapped[Optional["Reservation"]] = relationship("Reservation")
    
    # Indexes
    __table_args__ = (
        Index("ix_waitlist_user_status", "user_id", "status"),
        Index("ix_waitlist_type_position", "spot_type", "position"),
        Index("ix_waitlist_preferred_date", "preferred_date"),
        UniqueConstraint("user_id", "spot_type", "status", name="uq_waitlist_active"),
    )
    
    @property
    def is_active(self) -> bool:
        """Check if waitlist entry is active."""
        return self.status == WaitlistStatus.WAITING
    
    @property
    def is_notified(self) -> bool:
        """Check if user has been notified."""
        return self.status == WaitlistStatus.NOTIFIED
    
    def __repr__(self) -> str:
        return f"<WaitlistEntry User {self.user_id} - {self.spot_type.value}>"