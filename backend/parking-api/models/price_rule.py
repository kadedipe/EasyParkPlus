"""
Price rule model for dynamic pricing.
"""

from typing import Optional
from sqlalchemy import (
    Column, String, Float, Boolean, Enum, JSON,
    DateTime, Integer, Index
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, AuditMixin


class RuleType(str, enum.Enum):
    """Rule type enumeration."""
    TIME_BASED = "time_based"
    DEMAND_BASED = "demand_based"
    EVENT_BASED = "event_based"
    SEASONAL = "seasonal"
    LOYALTY = "loyalty"
    PROMOTIONAL = "promotional"


class AdjustmentType(str, enum.Enum):
    """Adjustment type enumeration."""
    MULTIPLIER = "multiplier"
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE = "percentage"
    TIERED = "tiered"


class PriceRule(Base, TimestampMixin, AuditMixin):
    """
    Price rule model for dynamic pricing.
    """
    
    __tablename__ = "price_rules"
    
    # Rule Details
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    rule_type: Mapped[RuleType] = mapped_column(
        Enum(RuleType),
        nullable=False,
        index=True
    )
    
    # Conditions (JSON format)
    conditions: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    
    # Adjustment
    adjustment_type: Mapped[AdjustmentType] = mapped_column(
        Enum(AdjustmentType),
        nullable=False
    )
    adjustment_value: Mapped[float] = mapped_column(Float, nullable=False)
    min_adjustment: Mapped[Optional[float]] = mapped_column(Float)
    max_adjustment: Mapped[Optional[float]] = mapped_column(Float)
    
    # Applicability
    applicable_spot_types: Mapped[Optional[list]] = mapped_column(JSON, default=[])
    applicable_days: Mapped[Optional[list]] = mapped_column(JSON, default=[])  # 0-6, 0=Monday
    applicable_hours: Mapped[Optional[dict]] = mapped_column(JSON, default={})  # {"start": 9, "end": 17}
    
    # Priority and Execution
    priority: Mapped[int] = mapped_column(Integer, default=0)
    execution_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Time Range
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_stackable: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Usage Limits
    usage_limit: Mapped[Optional[int]] = mapped_column(Integer)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    per_user_limit: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Indexes
    __table_args__ = (
        Index("ix_price_rules_active_dates", "is_active", "start_date", "end_date"),
        Index("ix_price_rules_priority", "priority"),
    )
    
    def apply_to_price(self, base_price: float, **context) -> float:
        """
        Apply rule to calculate adjusted price.
        """
        if not self.is_active:
            return base_price
        
        if self.adjustment_type == AdjustmentType.MULTIPLIER:
            new_price = base_price * self.adjustment_value
        elif self.adjustment_type == AdjustmentType.PERCENTAGE:
            new_price = base_price * (1 + self.adjustment_value / 100)
        elif self.adjustment_type == AdjustmentType.FIXED_AMOUNT:
            new_price = base_price + self.adjustment_value
        else:
            new_price = base_price
        
        # Apply limits
        if self.min_adjustment is not None:
            new_price = max(new_price, base_price + self.min_adjustment)
        if self.max_adjustment is not None:
            new_price = min(new_price, base_price + self.max_adjustment)
        
        return new_price
    
    def __repr__(self) -> str:
        return f"<PriceRule {self.name}>"