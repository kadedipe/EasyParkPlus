"""
Loyalty program model for user rewards.
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Enum,
    DateTime, ForeignKey, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin


class LoyaltyTier(str, enum.Enum):
    """Loyalty tier enumeration."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class LoyaltyProgram(Base, TimestampMixin):
    """
    Loyalty program model for user rewards.
    """
    
    __tablename__ = "loyalty_programs"
    
    # Foreign Keys
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Points
    points: Mapped[int] = mapped_column(Integer, default=0, index=True)
    lifetime_points: Mapped[int] = mapped_column(Integer, default=0)
    pending_points: Mapped[int] = mapped_column(Integer, default=0)
    
    # Tier
    tier: Mapped[LoyaltyTier] = mapped_column(
        Enum(LoyaltyTier),
        nullable=False,
        default=LoyaltyTier.BRONZE,
        index=True
    )
    tier_progress: Mapped[float] = mapped_column(Float, default=0.0)
    next_tier_points: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Statistics
    total_spent: Mapped[float] = mapped_column(Float, default=0.0)
    total_reservations: Mapped[int] = mapped_column(Integer, default=0)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)
    
    # Benefits
    current_benefits: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # History
    points_history: Mapped[Optional[list]] = mapped_column(JSON, default=[])
    tier_history: Mapped[Optional[list]] = mapped_column(JSON, default=[])
    
    # Dates
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    tier_achieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    tier_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="loyalty_program")
    
    # Tier thresholds
    TIER_THRESHOLDS = {
        LoyaltyTier.BRONZE: 0,
        LoyaltyTier.SILVER: 1000,
        LoyaltyTier.GOLD: 5000,
        LoyaltyTier.PLATINUM: 10000,
        LoyaltyTier.DIAMOND: 25000,
    }
    
    # Tier benefits
    TIER_BENEFITS = {
        LoyaltyTier.BRONZE: {
            "discount_percentage": 0,
            "free_hours_per_month": 0,
            "priority_support": False,
            "free_extensions": False,
        },
        LoyaltyTier.SILVER: {
            "discount_percentage": 5,
            "free_hours_per_month": 1,
            "priority_support": False,
            "free_extensions": False,
        },
        LoyaltyTier.GOLD: {
            "discount_percentage": 10,
            "free_hours_per_month": 2,
            "priority_support": True,
            "free_extensions": False,
        },
        LoyaltyTier.PLATINUM: {
            "discount_percentage": 15,
            "free_hours_per_month": 4,
            "priority_support": True,
            "free_extensions": True,
        },
        LoyaltyTier.DIAMOND: {
            "discount_percentage": 20,
            "free_hours_per_month": 8,
            "priority_support": True,
            "free_extensions": True,
        },
    }
    
    def add_points(self, points: int, reason: str) -> None:
        """Add points to user's loyalty account."""
        self.points += points
        self.lifetime_points += points
        self.points_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "points": points,
            "type": "earned",
            "reason": reason
        })
        self.last_activity = datetime.utcnow()
        self.update_tier()
    
    def redeem_points(self, points: int, reason: str) -> bool:
        """Redeem points from user's loyalty account."""
        if self.points < points:
            return False
        
        self.points -= points
        self.points_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "points": points,
            "type": "redeemed",
            "reason": reason
        })
        self.last_activity = datetime.utcnow()
        return True
    
    def update_tier(self) -> None:
        """Update user's tier based on lifetime points."""
        new_tier = LoyaltyTier.BRONZE
        for tier, threshold in sorted(
            self.TIER_THRESHOLDS.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if self.lifetime_points >= threshold:
                new_tier = tier
                break
        
        if new_tier != self.tier:
            self.tier_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "from_tier": self.tier.value,
                "to_tier": new_tier.value,
                "points": self.lifetime_points
            })
            self.tier = new_tier
            self.tier_achieved_at = datetime.utcnow()
            self.current_benefits = self.TIER_BENEFITS[new_tier]
    
    @property
    def points_to_next_tier(self) -> Optional[int]:
        """Get points needed to reach next tier."""
        tiers = list(self.TIER_THRESHOLDS.items())
        current_index = next(
            i for i, (tier, _) in enumerate(tiers)
            if tier == self.tier
        )
        if current_index < len(tiers) - 1:
            next_tier, next_threshold = tiers[current_index + 1]
            return max(0, next_threshold - self.lifetime_points)
        return None
    
    def __repr__(self) -> str:
        return f"<LoyaltyProgram User {self.user_id} - {self.tier.value}>"