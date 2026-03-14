"""
User model for authentication and profile management.
"""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    Column, String, Boolean, DateTime, Enum, Integer,
    Float, JSON, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, SoftDeleteMixin, AuditMixin

if TYPE_CHECKING:
    from .vehicle import Vehicle
    from .reservation import Reservation
    from .payment import Payment
    from .review import Review
    from .notification import Notification
    from .waitlist import WaitlistEntry
    from .loyalty import LoyaltyProgram


class UserRole(str, enum.Enum):
    """User role enumeration."""
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"
    SUPERUSER = "superuser"


class UserStatus(str, enum.Enum):
    """User account status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BANNED = "banned"
    DELETED = "deleted"


class User(Base, TimestampMixin, SoftDeleteMixin, AuditMixin):
    """
    User model for authentication and profile management.
    """
    
    __tablename__ = "users"
    
    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Status and role
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
        index=True
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        default=UserStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Verification
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Security
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_secret: Mapped[Optional[str]] = mapped_column(String(255))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45))
    login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Preferences
    preferences: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    notification_settings: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    language: Mapped[str] = mapped_column(String(10), default="en")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Statistics
    total_reservations: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)
    average_rating: Mapped[Optional[float]] = mapped_column(Float)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0)
    
    # Additional info
    bio: Mapped[Optional[str]] = mapped_column(Text)
    company: Mapped[Optional[str]] = mapped_column(String(100))
    department: Mapped[Optional[str]] = mapped_column(String(100))
    employee_id: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Relationships
    vehicles: Mapped[List["Vehicle"]] = relationship(
        "Vehicle",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    reservations: Mapped[List["Reservation"]] = relationship(
        "Reservation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    payments: Mapped[List["Payment"]] = relationship(
        "Payment",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    waitlist_entries: Mapped[List["WaitlistEntry"]] = relationship(
        "WaitlistEntry",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    loyalty_program: Mapped[Optional["LoyaltyProgram"]] = relationship(
        "LoyaltyProgram",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_users_email_status", "email", "status"),
        Index("ix_users_role_status", "role", "status"),
        Index("ix_users_created_at", "created_at"),
        Index("ix_users_last_login", "last_login_at"),
    )
    
    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE and not self.is_deleted
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role in [UserRole.ADMIN, UserRole.SUPERUSER]
    
    @property
    def is_superuser(self) -> bool:
        """Check if user is superuser."""
        return self.role == UserRole.SUPERUSER
    
    @property
    def full_profile(self) -> dict:
        """Get full user profile."""
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "avatar_url": self.avatar_url,
            "role": self.role.value,
            "status": self.status.value,
            "email_verified": self.email_verified,
            "phone_verified": self.phone_verified,
            "two_factor_enabled": self.two_factor_enabled,
            "preferences": self.preferences,
            "notification_settings": self.notification_settings,
            "language": self.language,
            "timezone": self.timezone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"