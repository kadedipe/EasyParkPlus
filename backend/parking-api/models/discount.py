"""
Discount model for promotional discounts and codes.
"""

from typing import Optional
from sqlalchemy import (
    Column, String, Text, Float, Boolean, Enum, JSON,
    DateTime, Integer, Index
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, AuditMixin


class DiscountType(str, enum.Enum):
    """Discount type enumeration."""
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    BUY_X_GET_Y = "buy_x_get_y"
    FREE_PARKING = "free_parking"
    LOYALTY_POINTS = "loyalty_points"


class Discount(Base, TimestampMixin, AuditMixin):
    """
    Discount model for promotional discounts and codes.
    """
    
    __tablename__ = "discounts"
    
    # Discount Code
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Discount Details
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType),
        nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Restrictions
    min_purchase_amount: Mapped[Optional[float]] = mapped_column(Float)
    max_discount_amount: Mapped[Optional[float]] = mapped_column(Float)
    
    # Usage Limits
    usage_limit: Mapped[Optional[int]] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    per_user_limit: Mapped[int] = mapped_column(Integer, default=1)
    
    # Applicability
    applicable_spot_types: Mapped[Optional[list]] = mapped_column(JSON, default=[])
    applicable_user_roles: Mapped[Optional[list]] = mapped_column(JSON, default=[])
    first_time_only: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Time Range
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Indexes
    __table_args__ = (
        Index("ix_discounts_code_active", "code", "is_active"),
        Index("ix_discounts_dates", "start_date", "end_date"),
    )
    
    @property
    def is_valid(self) -> bool:
        """Check if discount is currently valid."""
        now = datetime.utcnow()
        return (
            self.is_active and
            (self.start_date is None or self.start_date <= now) and
            (self.end_date is None or self.end_date >= now) and
            (self.usage_limit is None or self.used_count < self.usage_limit)
        )
    
    def calculate_discount(self, amount: float) -> float:
        """
        Calculate discount amount.
        """
        if not self.is_valid:
            return 0.0
        
        if self.discount_type == DiscountType.PERCENTAGE:
            discount = amount * (self.value / 100)
        elif self.discount_type == DiscountType.FIXED_AMOUNT:
            discount = min(self.value, amount)
        else:
            discount = 0.0
        
        # Apply max discount limit
        if self.max_discount_amount:
            discount = min(discount, self.max_discount_amount)
        
        return discount
    
    def __repr__(self) -> str:
        return f"<Discount {self.code}>"