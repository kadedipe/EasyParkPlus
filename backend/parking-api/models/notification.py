"""
Notification model for user notifications.
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Column, String, Text, Boolean, Enum, ForeignKey,
    JSON, DateTime, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin


class NotificationType(str, enum.Enum):
    """Notification type enumeration."""
    RESERVATION_CONFIRMATION = "reservation_confirmation"
    RESERVATION_REMINDER = "reservation_reminder"
    RESERVATION_CANCELLED = "reservation_cancelled"
    RESERVATION_MODIFIED = "reservation_modified"
    CHECK_IN_REMINDER = "check_in_reminder"
    CHECK_OUT_REMINDER = "check_out_reminder"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    REFUND_PROCESSED = "refund_processed"
    REVIEW_REQUEST = "review_request"
    WAITLIST_AVAILABLE = "waitlist_available"
    WAITLIST_EXPIRING = "waitlist_expiring"
    PROMOTIONAL = "promotional"
    SYSTEM_ALERT = "system_alert"
    ACCOUNT_UPDATE = "account_update"
    SECURITY_ALERT = "security_alert"


class NotificationChannel(str, enum.Enum):
    """Notification channel enumeration."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WHATSAPP = "whatsapp"


class NotificationPriority(str, enum.Enum):
    """Notification priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base, TimestampMixin):
    """
    Notification model for user notifications.
    """
    
    __tablename__ = "notifications"
    
    # Foreign Keys
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Notification Details
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType),
        nullable=False,
        index=True
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel),
        nullable=False,
        default=NotificationChannel.IN_APP
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        Enum(NotificationPriority),
        nullable=False,
        default=NotificationPriority.MEDIUM
    )
    
    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    short_content: Mapped[Optional[str]] = mapped_column(String(160))
    
    # Data
    data: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    action_url: Mapped[Optional[str]] = mapped_column(String(500))
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    is_delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    is_clicked: Mapped[bool] = mapped_column(Boolean, default=False)
    clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Scheduling
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Error Handling
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    
    # Indexes
    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
        Index("ix_notifications_type_created", "type", "created_at"),
        Index("ix_notifications_scheduled", "scheduled_for"),
    )
    
    def mark_as_read(self) -> None:
        """Mark notification as read."""
        self.is_read = True
        self.read_at = func.now()
    
    def mark_as_delivered(self) -> None:
        """Mark notification as delivered."""
        self.is_delivered = True
        self.delivered_at = func.now()
    
    def mark_as_clicked(self) -> None:
        """Mark notification as clicked."""
        self.is_clicked = True
        self.clicked_at = func.now()
    
    def __repr__(self) -> str:
        return f"<Notification {self.type.value} for User {self.user_id}>"