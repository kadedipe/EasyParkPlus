"""
Review model for parking spot reviews.
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Column, String, Integer, Float, Text, ForeignKey,
    Boolean, Enum, Index, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, AuditMixin

if TYPE_CHECKING:
    from .user import User
    from .parking_spot import ParkingSpot
    from .reservation import Reservation


class RatingScore(int, enum.Enum):
    """Rating score enumeration."""
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


class Review(Base, TimestampMixin, AuditMixin):
    """
    Review model for parking spot reviews.
    """
    
    __tablename__ = "reviews"
    
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
    reservation_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("reservations.id", ondelete="SET NULL"),
        nullable=True,
        unique=True
    )
    
    # Review Content
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    title: Mapped[Optional[str]] = mapped_column(String(200))
    comment: Mapped[Optional[str]] = mapped_column(Text)
    
    # Detailed Ratings
    cleanliness_rating: Mapped[Optional[int]] = mapped_column(Integer)
    security_rating: Mapped[Optional[int]] = mapped_column(Integer)
    accessibility_rating: Mapped[Optional[int]] = mapped_column(Integer)
    lighting_rating: Mapped[Optional[int]] = mapped_column(Integer)
    value_rating: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True))
    
    # Helpfulness
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    not_helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    report_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Response
    response_comment: Mapped[Optional[str]] = mapped_column(Text)
    responded_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    responded_at: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True))
    
    # Status
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Photos
    photos: Mapped[Optional[list]] = mapped_column(JSON, default=[])
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reviews")
    spot: Mapped["ParkingSpot"] = relationship("ParkingSpot", back_populates="reviews")
    reservation: Mapped[Optional["Reservation"]] = relationship(
        "Reservation",
        back_populates="review"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_reviews_spot_rating", "spot_id", "rating"),
        Index("ix_reviews_user_spot", "user_id", "spot_id", unique=True),
        Index("ix_reviews_created_at", "created_at"),
        Index("ix_reviews_helpful", "helpful_count"),
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="chk_review_rating_range"
        ),
    )
    
    @property
    def average_detailed_rating(self) -> Optional[float]:
        """Calculate average of detailed ratings."""
        ratings = [
            self.cleanliness_rating,
            self.security_rating,
            self.accessibility_rating,
            self.lighting_rating,
            self.value_rating
        ]
        valid_ratings = [r for r in ratings if r is not None]
        if valid_ratings:
            return sum(valid_ratings) / len(valid_ratings)
        return None
    
    def __repr__(self) -> str:
        return f"<Review {self.rating}⭐ by User {self.user_id}>"