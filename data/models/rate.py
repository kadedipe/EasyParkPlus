# parking-management/data/migrations/models/rate.py

"""
Rate model for parking management system.

This module defines the Rate model and related classes for managing
parking rates, pricing rules, dynamic pricing, special rates,
and rate history.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Time,
    Text, ForeignKey, UniqueConstraint, Index, CheckConstraint,
    Numeric, JSON, Table, func, text, event, and_, or_
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TSVECTOR
from sqlalchemy.orm import relationship, backref, validates, object_session
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declarative_base
import uuid
import enum
import json
from datetime import datetime, date, timedelta
import logging
from typing import Optional, List, Dict, Any, Tuple
import calendar

# Configure logging
logger = logging.getLogger(__name__)

# Create base class
Base = declarative_base()


class RateType(str, enum.Enum):
    """Enum for rate types."""
    HOURLY = 'hourly'
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    YEARLY = 'yearly'
    EVENT = 'event'
    SPECIAL = 'special'
    PROMOTIONAL = 'promotional'
    MEMBERSHIP = 'membership'
    CORPORATE = 'corporate'
    VALET = 'valet'
    OVERNIGHT = 'overnight'
    WEEKEND = 'weekend'
    HOLIDAY = 'holiday'
    EARLY_BIRD = 'early_bird'
    NIGHT_OWL = 'night_owl'
    SEASONAL = 'seasonal'


class RateUnit(str, enum.Enum):
    """Enum for rate units."""
    HOUR = 'hour'
    HALF_HOUR = 'half_hour'
    MINUTE = 'minute'
    DAY = 'day'
    WEEK = 'week'
    MONTH = 'month'
    YEAR = 'year'
    FIXED = 'fixed'


class RateCategory(str, enum.Enum):
    """Enum for rate categories."""
    STANDARD = 'standard'
    PREMIUM = 'premium'
    ECONOMY = 'economy'
    VIP = 'vip'
    HANDICAP = 'handicap'
    EV = 'ev'
    MOTORCYCLE = 'motorcycle'
    OVERSIZE = 'oversize'
    COMMERCIAL = 'commercial'


class DayOfWeek(str, enum.Enum):
    """Enum for days of week."""
    MONDAY = 'monday'
    TUESDAY = 'tuesday'
    WEDNESDAY = 'wednesday'
    THURSDAY = 'thursday'
    FRIDAY = 'friday'
    SATURDAY = 'saturday'
    SUNDAY = 'sunday'


class Season(str, enum.Enum):
    """Enum for seasons."""
    SPRING = 'spring'
    SUMMER = 'summer'
    FALL = 'fall'
    WINTER = 'winter'


class HolidayType(str, enum.Enum):
    """Enum for holiday types."""
    FEDERAL = 'federal'
    STATE = 'state'
    LOCAL = 'local'
    RELIGIOUS = 'religious'
    SCHOOL = 'school'
    CORPORATE = 'corporate'


class RateConditionType(str, enum.Enum):
    """Enum for rate condition types."""
    TIME_OF_DAY = 'time_of_day'
    DAY_OF_WEEK = 'day_of_week'
    DATE_RANGE = 'date_range'
    DURATION = 'duration'
    VEHICLE_TYPE = 'vehicle_type'
    SPOT_TYPE = 'spot_type'
    OCCUPANCY_LEVEL = 'occupancy_level'
    MEMBERSHIP_TIER = 'membership_tier'
    BOOKING_CHANNEL = 'booking_channel'
    ADVANCE_BOOKING = 'advance_booking'
    LOYALTY_POINTS = 'loyalty_points'


class DynamicPricingModel(str, enum.Enum):
    """Enum for dynamic pricing models."""
    FIXED = 'fixed'
    DEMAND_BASED = 'demand_based'
    TIME_BASED = 'time_based'
    OCCUPANCY_BASED = 'occupancy_based'
    EVENT_BASED = 'event_based'
    COMPETITOR_BASED = 'competitor_based'
    WEATHER_BASED = 'weather_based'
    SEASONAL = 'seasonal'
    HYBRID = 'hybrid'


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


class Rate(Base):
    """
    Core rate model for parking pricing.
    
    Defines comprehensive rate structures with support for dynamic pricing,
    conditional rates, and complex pricing rules.
    """
    
    __tablename__ = 'rates'
    __table_args__ = (
        # Primary indexes
        Index('ix_rates_code', 'code', unique=True),
        Index('ix_rates_name', 'name'),
        
        # Foreign key indexes
        Index('ix_rates_zone_id', 'zone_id'),
        Index('ix_rates_spot_id', 'spot_id'),
        
        # Status indexes
        Index('ix_rates_type', 'rate_type'),
        Index('ix_rates_category', 'category'),
        Index('ix_rates_is_active', 'is_active'),
        
        # Time-based indexes
        Index('ix_rates_effective_date', 'effective_from', 'effective_to'),
        Index('ix_rates_created_at', 'created_at'),
        
        # Composite indexes for common queries
        Index('ix_rates_zone_spot_type', 'zone_id', 'spot_type'),
        Index('ix_rates_vehicle_spot', 'vehicle_type', 'spot_type'),
        
        # Partial indexes
        Index('ix_rates_current', 'effective_from', 'effective_to',
              postgresql_where=text(
                  "effective_from <= CURRENT_TIMESTAMP "
                  "AND (effective_to IS NULL OR effective_to >= CURRENT_TIMESTAMP)"
              )),
        Index('ix_rates_promotional', 'is_promotional',
              postgresql_where=text("is_promotional = true")),
        
        # Check constraints
        CheckConstraint(
            "rate_type IN ('hourly', 'daily', 'weekly', 'monthly', 'yearly', 'event', "
            "'special', 'promotional', 'membership', 'corporate', 'valet', 'overnight', "
            "'weekend', 'holiday', 'early_bird', 'night_owl', 'seasonal')",
            name='ck_rates_type'
        ),
        CheckConstraint(
            "unit IN ('hour', 'half_hour', 'minute', 'day', 'week', 'month', 'year', 'fixed')",
            name='ck_rates_unit'
        ),
        CheckConstraint(
            "base_rate >= 0",
            name='ck_rates_base_rate_positive'
        ),
        CheckConstraint(
            "minimum_amount >= 0",
            name='ck_rates_minimum_positive'
        ),
        CheckConstraint(
            "maximum_amount >= 0",
            name='ck_rates_maximum_positive'
        ),
        CheckConstraint(
            "minimum_amount <= maximum_amount",
            name='ck_rates_min_max'
        ),
        
        # Table comment
        {'comment': 'Core rate model for parking pricing'}
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
    
    code = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Unique rate code (e.g., STD-HOURLY, VIP-DAILY)'
    )
    
    name = Column(
        String(200),
        nullable=False,
        comment='Rate name (e.g., Standard Hourly Rate)'
    )
    
    description = Column(
        Text,
        comment='Rate description'
    )
    
    # =========================================================================
    # RATE CLASSIFICATION
    # =========================================================================
    rate_type = Column(
        String(20),
        nullable=False,
        comment='Type of rate'
    )
    
    category = Column(
        String(20),
        comment='Rate category'
    )
    
    priority = Column(
        Integer,
        server_default='0',
        comment='Priority for rate selection (higher = higher priority)'
    )
    
    # =========================================================================
    # APPLICABILITY
    # =========================================================================
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_zones.id', ondelete='CASCADE'),
        comment='Zone this rate applies to (null for all zones)'
    )
    
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='CASCADE'),
        comment='Specific spot this rate applies to'
    )
    
    spot_type = Column(
        String(20),
        comment='Type of spot this rate applies to'
    )
    
    vehicle_type = Column(
        String(20),
        comment='Type of vehicle this rate applies to'
    )
    
    # =========================================================================
    # BASE RATE STRUCTURE
    # =========================================================================
    base_rate = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Base rate amount'
    )
    
    unit = Column(
        String(20),
        nullable=False,
        comment='Billing unit'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        server_default='USD',
        comment='Currency code'
    )
    
    # =========================================================================
    # RATE CONSTRAINTS
    # =========================================================================
    min_units = Column(
        Integer,
        server_default='1',
        comment='Minimum number of units to charge'
    )
    
    max_units = Column(
        Integer,
        comment='Maximum number of units allowed'
    )
    
    min_duration_minutes = Column(
        Integer,
        comment='Minimum parking duration in minutes'
    )
    
    max_duration_minutes = Column(
        Integer,
        comment='Maximum parking duration in minutes'
    )
    
    grace_period_minutes = Column(
        Integer,
        server_default='15',
        comment='Grace period in minutes'
    )
    
    # =========================================================================
    # TIERED PRICING
    # =========================================================================
    tiered_pricing = Column(
        JSONB,
        comment='Tiered pricing structure (e.g., 0-2h: $5, 2-4h: $10)'
    )
    
    has_maximum_cap = Column(
        Boolean,
        server_default='false',
        comment='Whether there is a maximum cap'
    )
    
    maximum_cap_amount = Column(
        Numeric(10, 2),
        comment='Maximum amount for the period'
    )
    
    maximum_cap_period = Column(
        String(20),
        comment='Period for maximum cap (day, week, month)'
    )
    
    # =========================================================================
    # TIME-BASED RATES
    # =========================================================================
    has_peak_pricing = Column(
        Boolean,
        server_default='false',
        comment='Whether peak pricing applies'
    )
    
    peak_times = Column(
        JSONB,
        comment='Peak time definitions'
    )
    
    peak_rate_multiplier = Column(
        Numeric(3, 2),
        comment='Peak time rate multiplier'
    )
    
    has_off_peak_pricing = Column(
        Boolean,
        server_default='false',
        comment='Whether off-peak pricing applies'
    )
    
    off_peak_times = Column(
        JSONB,
        comment='Off-peak time definitions'
    )
    
    off_peak_rate_multiplier = Column(
        Numeric(3, 2),
        comment='Off-peak rate multiplier'
    )
    
    # =========================================================================
    # DAY-BASED RATES
    # =========================================================================
    weekday_rates = Column(
        JSONB,
        comment='Rates for specific weekdays'
    )
    
    weekend_rate = Column(
        Numeric(10, 2),
        comment='Weekend rate (if different)'
    )
    
    weekend_multiplier = Column(
        Numeric(3, 2),
        comment='Weekend rate multiplier'
    )
    
    # =========================================================================
    # NIGHT RATES
    # =========================================================================
    has_night_rate = Column(
        Boolean,
        server_default='false',
        comment='Whether night rate applies'
    )
    
    night_rate = Column(
        Numeric(10, 2),
        comment='Night rate amount'
    )
    
    night_rate_multiplier = Column(
        Numeric(3, 2),
        comment='Night rate multiplier'
    )
    
    night_start_time = Column(
        Time,
        comment='Night rate start time'
    )
    
    night_end_time = Column(
        Time,
        comment='Night rate end time'
    )
    
    # =========================================================================
    # HOLIDAY RATES
    # =========================================================================
    has_holiday_rate = Column(
        Boolean,
        server_default='false',
        comment='Whether holiday rate applies'
    )
    
    holiday_rate = Column(
        Numeric(10, 2),
        comment='Holiday rate amount'
    )
    
    holiday_rate_multiplier = Column(
        Numeric(3, 2),
        comment='Holiday rate multiplier'
    )
    
    holiday_dates = Column(
        ARRAY(Date),
        comment='Specific holiday dates'
    )
    
    holiday_types = Column(
        ARRAY(String(20)),
        comment='Types of holidays this rate applies to'
    )
    
    # =========================================================================
    # SEASONAL RATES
    # =========================================================================
    has_seasonal_rates = Column(
        Boolean,
        server_default='false',
        comment='Whether seasonal rates apply'
    )
    
    seasonal_rates = Column(
        JSONB,
        comment='Seasonal rate definitions'
    )
    
    seasons = Column(
        ARRAY(String(20)),
        comment='Seasons this rate applies to'
    )
    
    # =========================================================================
    # ADVANCED PRICING
    # =========================================================================
    dynamic_pricing_model = Column(
        String(20),
        comment='Dynamic pricing model used'
    )
    
    dynamic_pricing_config = Column(
        JSONB,
        comment='Dynamic pricing configuration'
    )
    
    demand_factor = Column(
        Float,
        comment='Demand-based pricing factor'
    )
    
    occupancy_thresholds = Column(
        JSONB,
        comment='Occupancy-based pricing thresholds'
    )
    
    # =========================================================================
    # MINIMUM/MAXIMUM
    # =========================================================================
    minimum_amount = Column(
        Numeric(10, 2),
        comment='Minimum charge amount'
    )
    
    maximum_amount = Column(
        Numeric(10, 2),
        comment='Maximum charge amount'
    )
    
    # =========================================================================
    # VALIDITY PERIOD
    # =========================================================================
    effective_from = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Rate effective from this time'
    )
    
    effective_to = Column(
        DateTime(timezone=True),
        comment='Rate effective until this time'
    )
    
    # =========================================================================
    # PROMOTIONAL FLAGS
    # =========================================================================
    is_promotional = Column(
        Boolean,
        server_default='false',
        comment='Whether this is a promotional rate'
    )
    
    promotion_id = Column(
        String(100),
        comment='Associated promotion ID'
    )
    
    requires_promo_code = Column(
        Boolean,
        server_default='false',
        comment='Whether promo code is required'
    )
    
    promo_codes = Column(
        ARRAY(String(50)),
        comment='Valid promo codes'
    )
    
    # =========================================================================
    # MEMBERSHIP/CORPORATE
    # =========================================================================
    requires_membership = Column(
        Boolean,
        server_default='false',
        comment='Whether membership is required'
    )
    
    membership_tiers = Column(
        ARRAY(String(50)),
        comment='Allowed membership tiers'
    )
    
    requires_corporate = Column(
        Boolean,
        server_default='false',
        comment='Whether corporate account is required'
    )
    
    corporate_ids = Column(
        ARRAY(String(100)),
        comment='Allowed corporate IDs'
    )
    
    # =========================================================================
    # BOOKING CHANNEL
    # =========================================================================
    booking_channels = Column(
        ARRAY(String(50)),
        comment='Allowed booking channels (web, mobile, api, walk-in)'
    )
    
    advance_booking_days = Column(
        Integer,
        comment='Required advance booking days'
    )
    
    advance_booking_discount = Column(
        Numeric(5, 2),
        comment='Discount for advance booking (%)'
    )
    
    # =========================================================================
    # TAXES AND FEES
    # =========================================================================
    is_tax_inclusive = Column(
        Boolean,
        server_default='true',
        comment='Whether rate includes tax'
    )
    
    tax_rate = Column(
        Numeric(5, 2),
        comment='Tax rate percentage'
    )
    
    tax_inclusive = Column(
        Boolean,
        server_default='true',
        comment='Whether price includes tax'
    )
    
    additional_fees = Column(
        JSONB,
        comment='Additional fees to apply'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    is_active = Column(
        Boolean,
        nullable=False,
        server_default='true',
        comment='Whether rate is active'
    )
    
    is_default = Column(
        Boolean,
        server_default='false',
        comment='Whether this is the default rate'
    )
    
    is_system = Column(
        Boolean,
        server_default='false',
        comment='Whether this is a system-defined rate'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    tags = Column(
        ARRAY(String(50)),
        comment='Custom tags'
    )
    
    conditions = Column(
        JSONB,
        comment='Additional conditions for rate applicability'
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
        comment='User who created this rate'
    )
    
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who last updated this rate'
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        comment='Soft delete timestamp'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    zone = relationship(
        'ParkingZone',
        foreign_keys=[zone_id],
        back_populates='rates',
        comment='Zone this rate applies to'
    )
    
    spot = relationship(
        'ParkingSpot',
        foreign_keys=[spot_id],
        back_populates='rates',
        comment='Specific spot this rate applies to'
    )
    
    history = relationship(
        'RateHistory',
        back_populates='rate',
        cascade='all, delete-orphan',
        comment='Rate change history'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def is_current(self) -> bool:
        """Check if rate is currently effective."""
        now = datetime.now()
        return (self.is_active and
                self.effective_from <= now and
                (self.effective_to is None or self.effective_to >= now))
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if rate has expired."""
        if self.effective_to:
            return datetime.now() > self.effective_to
        return False
    
    @hybrid_property
    def is_future(self) -> bool:
        """Check if rate is future-dated."""
        return datetime.now() < self.effective_from
    
    @hybrid_property
    def display_rate(self) -> str:
        """Get formatted rate display string."""
        if self.unit == 'hour':
            return f"${self.base_rate}/hr"
        elif self.unit == 'day':
            return f"${self.base_rate}/day"
        elif self.unit == 'week':
            return f"${self.base_rate}/week"
        elif self.unit == 'month':
            return f"${self.base_rate}/month"
        elif self.unit == 'year':
            return f"${self.base_rate}/year"
        else:
            return f"${self.base_rate}"
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @validates('code')
    def validate_code(self, key, code):
        """Validate rate code format."""
        if not code or len(code) < 3:
            raise ValueError('Rate code must be at least 3 characters')
        return code.upper()
    
    @validates('base_rate')
    def validate_base_rate(self, key, rate):
        """Validate base rate is positive."""
        if rate < 0:
            raise ValueError('Base rate must be positive')
        return rate
    
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
    
    def calculate_cost(
        self,
        start_time: datetime,
        end_time: datetime,
        vehicle_type: Optional[str] = None,
        apply_dynamic_pricing: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Calculate parking cost for a time range.
        
        Args:
            start_time: Parking start time
            end_time: Parking end time
            vehicle_type: Type of vehicle
            apply_dynamic_pricing: Whether to apply dynamic pricing
            **kwargs: Additional parameters for calculation
            
        Returns:
            Dictionary with cost breakdown
        """
        if start_time >= end_time:
            raise ValueError('End time must be after start time')
        
        # Calculate duration
        duration_minutes = (end_time - start_time).total_seconds() / 60
        duration_hours = duration_minutes / 60
        duration_days = duration_hours / 24
        
        # Check duration constraints
        if self.min_duration_minutes and duration_minutes < self.min_duration_minutes:
            duration_minutes = self.min_duration_minutes
            duration_hours = duration_minutes / 60
            duration_days = duration_hours / 24
        
        if self.max_duration_minutes and duration_minutes > self.max_duration_minutes:
            raise ValueError(f'Duration exceeds maximum allowed ({self.max_duration_minutes} minutes)')
        
        # Calculate base amount
        base_amount = self._calculate_base_amount(duration_hours, duration_days, start_time)
        
        # Apply time-based multipliers
        multiplier = self._get_time_multiplier(start_time, end_time)
        if multiplier != 1.0:
            base_amount *= multiplier
        
        # Apply vehicle type multiplier if applicable
        if vehicle_type and self.vehicle_type and vehicle_type != self.vehicle_type:
            # Vehicle type mismatch - rate may not apply
            pass
        
        # Apply dynamic pricing
        if apply_dynamic_pricing and self.dynamic_pricing_model:
            base_amount = self._apply_dynamic_pricing(base_amount, start_time, **kwargs)
        
        # Apply minimum amount
        if self.minimum_amount and base_amount < self.minimum_amount:
            base_amount = self.minimum_amount
        
        # Apply maximum cap
        if self.has_maximum_cap and self.maximum_cap_amount:
            if self.maximum_cap_period == 'day' and duration_days >= 1:
                base_amount = min(base_amount, self.maximum_cap_amount)
            elif self.maximum_cap_period == 'week' and duration_days >= 7:
                base_amount = min(base_amount, self.maximum_cap_amount)
            elif self.maximum_cap_period == 'month' and duration_days >= 30:
                base_amount = min(base_amount, self.maximum_cap_amount)
        
        # Apply maximum amount
        if self.maximum_amount and base_amount > self.maximum_amount:
            base_amount = self.maximum_amount
        
        # Calculate tax
        tax_amount = 0
        if not self.is_tax_inclusive and self.tax_rate:
            tax_amount = base_amount * (self.tax_rate / 100)
        
        total_amount = base_amount + tax_amount
        
        # Add any additional fees
        fees = []
        if self.additional_fees:
            for fee in self.additional_fees:
                fee_amount = fee.get('amount', 0)
                if fee.get('type') == 'percentage':
                    fee_amount = base_amount * (fee_amount / 100)
                fees.append({
                    'name': fee.get('name', 'Fee'),
                    'amount': round(fee_amount, 2)
                })
                total_amount += fee_amount
        
        return {
            'base_amount': round(base_amount, 2),
            'tax_amount': round(tax_amount, 2),
            'fees': fees,
            'total_amount': round(total_amount, 2),
            'currency': self.currency,
            'rate_applied': float(self.base_rate),
            'rate_type': self.rate_type,
            'rate_code': self.code,
            'rate_id': str(self.id),
            'duration': {
                'minutes': duration_minutes,
                'hours': round(duration_hours, 2),
                'days': round(duration_days, 2)
            },
            'multiplier': multiplier if multiplier != 1.0 else None
        }
    
    def _calculate_base_amount(
        self,
        duration_hours: float,
        duration_days: float,
        start_time: datetime
    ) -> float:
        """Calculate base amount based on rate structure."""
        base_rate = float(self.base_rate)
        
        # Check for tiered pricing first
        if self.tiered_pricing:
            for tier in sorted(self.tiered_pricing, key=lambda x: x.get('min_hours', 0)):
                if duration_hours >= tier.get('min_hours', 0):
                    if 'max_hours' not in tier or duration_hours <= tier.get('max_hours', float('inf')):
                        if 'rate' in tier:
                            return float(tier['rate'])
                        elif 'multiplier' in tier:
                            return base_rate * float(tier['multiplier'])
        
        # Standard calculation based on unit
        if self.unit == 'hour':
            # Round up to nearest hour if less than min_units
            units = max(self.min_units, int(duration_hours) + (1 if duration_hours % 1 > 0 else 0))
            return base_rate * units
        
        elif self.unit == 'half_hour':
            units = max(self.min_units, int(duration_hours * 2))
            return base_rate * units
        
        elif self.unit == 'minute':
            units = max(self.min_units, int(duration_hours * 60))
            return base_rate * units
        
        elif self.unit == 'day':
            units = max(self.min_units, int(duration_days) + (1 if duration_days % 1 > 0 else 0))
            return base_rate * units
        
        elif self.unit == 'week':
            units = max(self.min_units, int(duration_days / 7) + (1 if duration_days % 7 > 0 else 0))
            return base_rate * units
        
        elif self.unit == 'month':
            # Approximate months based on days
            units = max(self.min_units, int(duration_days / 30) + 1)
            return base_rate * units
        
        elif self.unit == 'year':
            units = max(self.min_units, int(duration_days / 365) + 1)
            return base_rate * units
        
        else:  # fixed rate
            return base_rate
    
    def _get_time_multiplier(self, start_time: datetime, end_time: datetime) -> float:
        """Get time-based multiplier for the parking period."""
        multiplier = 1.0
        
        # Check if any part of the period falls in peak times
        if self.has_peak_pricing and self.peak_times:
            current = start_time
            while current < end_time:
                if self._is_peak_time(current):
                    multiplier = max(multiplier, float(self.peak_rate_multiplier or 1.0))
                current += timedelta(minutes=30)
        
        # Check if any part falls in off-peak times
        if self.has_off_peak_pricing and self.off_peak_times:
            current = start_time
            while current < end_time:
                if self._is_off_peak_time(current):
                    multiplier = min(multiplier, float(self.off_peak_rate_multiplier or 1.0))
                current += timedelta(minutes=30)
        
        # Check if it's a weekend
        if self.weekend_rate or self.weekend_multiplier:
            if start_time.weekday() >= 5:  # Saturday or Sunday
                if self.weekend_rate:
                    # This will be handled by base calculation override
                    pass
                elif self.weekend_multiplier:
                    multiplier *= float(self.weekend_multiplier)
        
        # Check if it's a holiday
        if self.has_holiday_rate and self.holiday_dates:
            for holiday in self.holiday_dates:
                if start_time.date() == holiday:
                    if self.holiday_rate:
                        # This will be handled by base calculation override
                        pass
                    elif self.holiday_rate_multiplier:
                        multiplier *= float(self.holiday_rate_multiplier)
        
        # Check if it's night time
        if self.has_night_rate and self.night_start_time and self.night_end_time:
            time_of_day = start_time.time()
            if self.night_start_time <= self.night_end_time:
                if self.night_start_time <= time_of_day <= self.night_end_time:
                    multiplier *= float(self.night_rate_multiplier or 1.0)
            else:  # Overnight (e.g., 22:00 to 06:00)
                if time_of_day >= self.night_start_time or time_of_day <= self.night_end_time:
                    multiplier *= float(self.night_rate_multiplier or 1.0)
        
        return multiplier
    
    def _is_peak_time(self, dt: datetime) -> bool:
        """Check if given datetime is within peak times."""
        if not self.peak_times:
            return False
        
        for peak in self.peak_times:
            # Check day of week
            if 'days' in peak:
                day_name = dt.strftime('%A').lower()
                if day_name not in peak['days']:
                    continue
            
            # Check time range
            if 'start_time' in peak and 'end_time' in peak:
                start = datetime.strptime(peak['start_time'], '%H:%M').time()
                end = datetime.strptime(peak['end_time'], '%H:%M').time()
                current = dt.time()
                
                if start <= end:
                    if start <= current <= end:
                        return True
                else:  # Overnight
                    if current >= start or current <= end:
                        return True
        
        return False
    
    def _is_off_peak_time(self, dt: datetime) -> bool:
        """Check if given datetime is within off-peak times."""
        if not self.off_peak_times:
            return False
        
        for off_peak in self.off_peak_times:
            # Check day of week
            if 'days' in off_peak:
                day_name = dt.strftime('%A').lower()
                if day_name not in off_peak['days']:
                    continue
            
            # Check time range
            if 'start_time' in off_peak and 'end_time' in off_peak:
                start = datetime.strptime(off_peak['start_time'], '%H:%M').time()
                end = datetime.strptime(off_peak['end_time'], '%H:%M').time()
                current = dt.time()
                
                if start <= end:
                    if start <= current <= end:
                        return True
                else:  # Overnight
                    if current >= start or current <= end:
                        return True
        
        return False
    
    def _apply_dynamic_pricing(
        self,
        base_amount: float,
        start_time: datetime,
        **kwargs
    ) -> float:
        """
        Apply dynamic pricing adjustments.
        
        Args:
            base_amount: Base calculated amount
            start_time: Parking start time
            **kwargs: Additional parameters (occupancy, demand, etc.)
            
        Returns:
            Adjusted amount
        """
        if not self.dynamic_pricing_config:
            return base_amount
        
        config = self.dynamic_pricing_config
        factor = 1.0
        
        if self.dynamic_pricing_model == 'demand_based':
            # Adjust based on demand factor
            demand = kwargs.get('demand_factor', self.demand_factor or 1.0)
            factor *= demand
        
        elif self.dynamic_pricing_model == 'occupancy_based':
            # Adjust based on occupancy thresholds
            occupancy = kwargs.get('occupancy', 0)
            if self.occupancy_thresholds:
                for threshold in sorted(self.occupancy_thresholds, key=lambda x: x.get('threshold', 0)):
                    if occupancy >= threshold.get('threshold', 0):
                        factor *= threshold.get('multiplier', 1.0)
        
        elif self.dynamic_pricing_model == 'time_based':
            # Time-based adjustments (e.g., higher prices during busy hours)
            hour = start_time.hour
            if 'hour_multipliers' in config:
                for hour_range in config['hour_multipliers']:
                    if hour_range['start'] <= hour <= hour_range['end']:
                        factor *= hour_range.get('multiplier', 1.0)
        
        elif self.dynamic_pricing_model == 'event_based':
            # Event-based pricing
            event_factor = kwargs.get('event_factor', 1.0)
            factor *= event_factor
        
        return base_amount * factor
    
    def applies_to(
        self,
        zone_id: Optional[uuid.UUID] = None,
        spot_id: Optional[uuid.UUID] = None,
        spot_type: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        check_time: Optional[datetime] = None
    ) -> bool:
        """
        Check if rate applies to given context.
        
        Args:
            zone_id: Zone ID
            spot_id: Spot ID
            spot_type: Spot type
            vehicle_type: Vehicle type
            check_time: Time to check (defaults to now)
            
        Returns:
            True if rate applies
        """
        # Check if rate is active
        if not self.is_active:
            return False
        
        # Check time validity
        check_time = check_time or datetime.now()
        if check_time < self.effective_from:
            return False
        if self.effective_to and check_time > self.effective_to:
            return False
        
        # Check zone/spot applicability
        if self.zone_id and zone_id and self.zone_id != zone_id:
            return False
        
        if self.spot_id and spot_id and self.spot_id != spot_id:
            return False
        
        # Check spot type
        if self.spot_type and spot_type and self.spot_type != spot_type:
            return False
        
        # Check vehicle type
        if self.vehicle_type and vehicle_type and self.vehicle_type != vehicle_type:
            return False
        
        return True
    
    def get_effective_rate(
        self,
        at_time: Optional[datetime] = None
    ) -> Optional['Rate']:
        """
        Get the effective rate at a specific time (for versioned rates).
        
        Args:
            at_time: Time to check (defaults to now)
            
        Returns:
            Effective rate or None
        """
        at_time = at_time or datetime.now()
        
        if self.is_current:
            return self
        
        # Look for newer version
        if object_session(self):
            newer = object_session(self).query(Rate).filter(
                Rate.code == self.code,
                Rate.effective_from <= at_time,
                or_(
                    Rate.effective_to.is_(None),
                    Rate.effective_to >= at_time
                ),
                Rate.is_active == True
            ).order_by(Rate.effective_from.desc()).first()
            
            return newer
        
        return None
    
    def create_new_version(
        self,
        effective_from: Optional[datetime] = None,
        **changes
    ) -> 'Rate':
        """
        Create a new version of this rate.
        
        Args:
            effective_from: When new version becomes effective
            **changes: Changes to apply to new version
            
        Returns:
            New Rate instance
        """
        # Create copy of current rate
        new_rate = Rate(
            code=self.code,
            name=self.name,
            description=self.description,
            rate_type=self.rate_type,
            category=self.category,
            priority=self.priority,
            zone_id=self.zone_id,
            spot_id=self.spot_id,
            spot_type=self.spot_type,
            vehicle_type=self.vehicle_type,
            unit=self.unit,
            currency=self.currency,
            min_units=self.min_units,
            max_units=self.max_units,
            min_duration_minutes=self.min_duration_minutes,
            max_duration_minutes=self.max_duration_minutes,
            grace_period_minutes=self.grace_period_minutes,
            tiered_pricing=self.tiered_pricing,
            has_maximum_cap=self.has_maximum_cap,
            maximum_cap_amount=self.maximum_cap_amount,
            maximum_cap_period=self.maximum_cap_period,
            has_peak_pricing=self.has_peak_pricing,
            peak_times=self.peak_times,
            peak_rate_multiplier=self.peak_rate_multiplier,
            has_off_peak_pricing=self.has_off_peak_pricing,
            off_peak_times=self.off_peak_times,
            off_peak_rate_multiplier=self.off_peak_rate_multiplier,
            weekday_rates=self.weekday_rates,
            weekend_rate=self.weekend_rate,
            weekend_multiplier=self.weekend_multiplier,
            has_night_rate=self.has_night_rate,
            night_rate=self.night_rate,
            night_rate_multiplier=self.night_rate_multiplier,
            night_start_time=self.night_start_time,
            night_end_time=self.night_end_time,
            has_holiday_rate=self.has_holiday_rate,
            holiday_rate=self.holiday_rate,
            holiday_rate_multiplier=self.holiday_rate_multiplier,
            holiday_dates=self.holiday_dates,
            holiday_types=self.holiday_types,
            has_seasonal_rates=self.has_seasonal_rates,
            seasonal_rates=self.seasonal_rates,
            seasons=self.seasons,
            dynamic_pricing_model=self.dynamic_pricing_model,
            dynamic_pricing_config=self.dynamic_pricing_config,
            demand_factor=self.demand_factor,
            occupancy_thresholds=self.occupancy_thresholds,
            minimum_amount=self.minimum_amount,
            maximum_amount=self.maximum_amount,
            is_promotional=self.is_promotional,
            promotion_id=self.promotion_id,
            requires_promo_code=self.requires_promo_code,
            promo_codes=self.promo_codes,
            requires_membership=self.requires_membership,
            membership_tiers=self.membership_tiers,
            requires_corporate=self.requires_corporate,
            corporate_ids=self.corporate_ids,
            booking_channels=self.booking_channels,
            advance_booking_days=self.advance_booking_days,
            advance_booking_discount=self.advance_booking_discount,
            is_tax_inclusive=self.is_tax_inclusive,
            tax_rate=self.tax_rate,
            tax_inclusive=self.tax_inclusive,
            additional_fees=self.additional_fees,
            tags=self.tags,
            conditions=self.conditions,
            metadata=self.metadata,
            created_by=self.created_by,
            is_system=self.is_system
        )
        
        # Apply changes
        for key, value in changes.items():
            if hasattr(new_rate, key):
                setattr(new_rate, key, value)
        
        # Set new effective dates
        new_rate.effective_from = effective_from or datetime.now()
        new_rate.base_rate = changes.get('base_rate', self.base_rate)
        
        # Expire current rate
        self.effective_to = new_rate.effective_from - timedelta(microseconds=1)
        self.is_active = False
        
        return new_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rate to dictionary."""
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'rate_type': self.rate_type,
            'category': self.category,
            'priority': self.priority,
            'applicability': {
                'zone_id': str(self.zone_id) if self.zone_id else None,
                'spot_id': str(self.spot_id) if self.spot_id else None,
                'spot_type': self.spot_type,
                'vehicle_type': self.vehicle_type,
            },
            'base_rate': float(self.base_rate),
            'unit': self.unit,
            'currency': self.currency,
            'constraints': {
                'min_units': self.min_units,
                'max_units': self.max_units,
                'min_duration_minutes': self.min_duration_minutes,
                'max_duration_minutes': self.max_duration_minutes,
                'grace_period_minutes': self.grace_period_minutes,
            },
            'tiered_pricing': self.tiered_pricing,
            'maximum_cap': {
                'enabled': self.has_maximum_cap,
                'amount': float(self.maximum_cap_amount) if self.maximum_cap_amount else None,
                'period': self.maximum_cap_period,
            },
            'time_based': {
                'has_peak_pricing': self.has_peak_pricing,
                'peak_times': self.peak_times,
                'has_off_peak_pricing': self.has_off_peak_pricing,
                'off_peak_times': self.off_peak_times,
                'weekend_rate': float(self.weekend_rate) if self.weekend_rate else None,
                'weekend_multiplier': float(self.weekend_multiplier) if self.weekend_multiplier else None,
                'has_night_rate': self.has_night_rate,
                'night_rate': float(self.night_rate) if self.night_rate else None,
                'night_start_time': self.night_start_time.isoformat() if self.night_start_time else None,
                'night_end_time': self.night_end_time.isoformat() if self.night_end_time else None,
            },
            'holiday': {
                'has_holiday_rate': self.has_holiday_rate,
                'holiday_rate': float(self.holiday_rate) if self.holiday_rate else None,
                'holiday_dates': [d.isoformat() for d in self.holiday_dates] if self.holiday_dates else [],
                'holiday_types': self.holiday_types,
            },
            'seasonal': {
                'has_seasonal_rates': self.has_seasonal_rates,
                'seasons': self.seasons,
            },
            'dynamic_pricing': {
                'model': self.dynamic_pricing_model,
                'config': self.dynamic_pricing_config,
                'demand_factor': self.demand_factor,
            },
            'limits': {
                'minimum_amount': float(self.minimum_amount) if self.minimum_amount else None,
                'maximum_amount': float(self.maximum_amount) if self.maximum_amount else None,
            },
            'validity': {
                'effective_from': self.effective_from.isoformat() if self.effective_from else None,
                'effective_to': self.effective_to.isoformat() if self.effective_to else None,
                'is_current': self.is_current,
                'is_expired': self.is_expired,
                'is_future': self.is_future,
            },
            'promotional': {
                'is_promotional': self.is_promotional,
                'promotion_id': self.promotion_id,
                'requires_promo_code': self.requires_promo_code,
                'promo_codes': self.promo_codes,
            },
            'membership': {
                'requires_membership': self.requires_membership,
                'membership_tiers': self.membership_tiers,
                'requires_corporate': self.requires_corporate,
            },
            'booking': {
                'channels': self.booking_channels,
                'advance_booking_days': self.advance_booking_days,
                'advance_booking_discount': float(self.advance_booking_discount) if self.advance_booking_discount else None,
            },
            'taxes': {
                'is_tax_inclusive': self.is_tax_inclusive,
                'tax_rate': float(self.tax_rate) if self.tax_rate else None,
            },
            'fees': self.additional_fees,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'is_system': self.is_system,
            'tags': self.tags,
            'conditions': self.conditions,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<Rate(id={self.id}, code={self.code}, rate={self.base_rate})>"


class RateHistory(Base):
    """
    History of rate changes.
    
    Tracks all modifications to rates for audit and compliance.
    """
    
    __tablename__ = 'rate_history'
    __table_args__ = (
        Index('ix_rate_history_rate', 'rate_id'),
        Index('ix_rate_history_date', 'changed_at'),
        Index('ix_rate_history_user', 'changed_by'),
        
        # Table comment
        {'comment': 'History of rate changes'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    rate_id = Column(
        UUID(as_uuid=True),
        ForeignKey('rates.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the rate'
    )
    
    rate_code = Column(
        String(50),
        comment='Rate code at time of change'
    )
    
    action = Column(
        String(20),
        nullable=False,
        comment='Action performed (CREATE, UPDATE, DELETE)'
    )
    
    changed_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who made the change'
    )
    
    changed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='When change occurred'
    )
    
    old_values = Column(
        JSONB,
        comment='Values before change'
    )
    
    new_values = Column(
        JSONB,
        comment='Values after change'
    )
    
    reason = Column(
        String(255),
        comment='Reason for change'
    )
    
    effective_date = Column(
        DateTime(timezone=True),
        comment='When change becomes effective'
    )
    
    ip_address = Column(
        String(45),
        comment='IP address of user'
    )
    
    user_agent = Column(
        String(500),
        comment='User agent'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    rate = relationship('Rate', back_populates='history')
    user = relationship('User', foreign_keys=[changed_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert history entry to dictionary."""
        return {
            'id': str(self.id),
            'rate_id': str(self.rate_id),
            'rate_code': self.rate_code,
            'action': self.action,
            'changed_by': str(self.changed_by) if self.changed_by else None,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'old_values': self.old_values,
            'new_values': self.new_values,
            'reason': self.reason,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
        }
    
    def __repr__(self) -> str:
        return f"<RateHistory(id={self.id}, rate={self.rate_code}, action={self.action})>"


class RateSchedule(Base):
    """
    Scheduled rate changes.
    
    Defines future rate changes to be applied automatically.
    """
    
    __tablename__ = 'rate_schedules'
    __table_args__ = (
        Index('ix_rate_schedule_rate', 'rate_id'),
        Index('ix_rate_schedule_date', 'scheduled_date'),
        Index('ix_rate_schedule_status', 'status'),
        
        # Table comment
        {'comment': 'Scheduled rate changes'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    rate_id = Column(
        UUID(as_uuid=True),
        ForeignKey('rates.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the rate to change'
    )
    
    scheduled_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When to apply the change'
    )
    
    new_rate = Column(
        Numeric(10, 2),
        nullable=False,
        comment='New rate amount'
    )
    
    reason = Column(
        String(255),
        comment='Reason for scheduled change'
    )
    
    status = Column(
        String(20),
        server_default='pending',
        comment='Schedule status (pending, applied, cancelled)'
    )
    
    applied_at = Column(
        DateTime(timezone=True),
        comment='When change was applied'
    )
    
    applied_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who applied the change'
    )
    
    cancelled_at = Column(
        DateTime(timezone=True),
        comment='When schedule was cancelled'
    )
    
    cancelled_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who cancelled the schedule'
    )
    
    cancellation_reason = Column(
        String(255),
        comment='Reason for cancellation'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created the schedule'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    rate = relationship('Rate')
    creator = relationship('User', foreign_keys=[created_by])
    applier = relationship('User', foreign_keys=[applied_by])
    canceller = relationship('User', foreign_keys=[cancelled_by])
    
    def apply(self, user_id: Optional[uuid.UUID] = None) -> None:
        """Apply scheduled rate change."""
        if self.status != 'pending':
            raise ValueError(f'Cannot apply schedule with status: {self.status}')
        
        # Update the rate
        self.rate.base_rate = self.new_rate
        self.rate.updated_by = user_id
        self.rate.updated_at = datetime.now()
        
        # Update schedule
        self.status = 'applied'
        self.applied_at = datetime.now()
        self.applied_by = user_id
    
    def cancel(self, reason: str, user_id: Optional[uuid.UUID] = None) -> None:
        """Cancel scheduled rate change."""
        self.status = 'cancelled'
        self.cancelled_at = datetime.now()
        self.cancelled_by = user_id
        self.cancellation_reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert schedule to dictionary."""
        return {
            'id': str(self.id),
            'rate_id': str(self.rate_id),
            'rate_code': self.rate.code if self.rate else None,
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'new_rate': float(self.new_rate),
            'reason': self.reason,
            'status': self.status,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'cancellation_reason': self.cancellation_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<RateSchedule(id={self.id}, rate={self.rate_id}, date={self.scheduled_date})>"


class SpecialRate(Base):
    """
    Special rates for events, promotions, and specific dates.
    
    Defines temporary or event-specific rates that override regular rates.
    """
    
    __tablename__ = 'special_rates'
    __table_args__ = (
        Index('ix_special_rates_code', 'code', unique=True),
        Index('ix_special_rates_event', 'event_id'),
        Index('ix_special_rates_dates', 'start_date', 'end_date'),
        
        # Table comment
        {'comment': 'Special rates for events and promotions'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    code = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Unique special rate code'
    )
    
    name = Column(
        String(200),
        nullable=False,
        comment='Special rate name'
    )
    
    description = Column(
        Text,
        comment='Description'
    )
    
    # =========================================================================
    # EVENT/PROMOTION
    # =========================================================================
    event_id = Column(
        String(100),
        comment='Associated event ID'
    )
    
    event_name = Column(
        String(200),
        comment='Associated event name'
    )
    
    promotion_id = Column(
        String(100),
        comment='Associated promotion ID'
    )
    
    # =========================================================================
    # APPLICABILITY
    # =========================================================================
    zone_ids = Column(
        ARRAY(UUID(as_uuid=True)),
        comment='Zones this rate applies to'
    )
    
    spot_types = Column(
        ARRAY(String(20)),
        comment='Spot types this rate applies to'
    )
    
    vehicle_types = Column(
        ARRAY(String(20)),
        comment='Vehicle types this rate applies to'
    )
    
    # =========================================================================
    # VALIDITY PERIOD
    # =========================================================================
    start_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When special rate starts'
    )
    
    end_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When special rate ends'
    )
    
    # =========================================================================
    # RATE DEFINITION
    # =========================================================================
    rate_type = Column(
        String(20),
        nullable=False,
        comment='Type of rate'
    )
    
    rate_value = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Special rate value'
    )
    
    unit = Column(
        String(20),
        nullable=False,
        comment='Rate unit'
    )
    
    currency = Column(
        String(3),
        server_default='USD',
        comment='Currency'
    )
    
    # =========================================================================
    # OVERRIDE BEHAVIOR
    # =========================================================================
    override_type = Column(
        String(20),
        server_default='replace',
        comment='How to apply: replace, discount_percentage, discount_fixed'
    )
    
    override_value = Column(
        Numeric(10, 2),
        comment='Override value (for discount types)'
    )
    
    # =========================================================================
    # RESTRICTIONS
    # =========================================================================
    min_duration_minutes = Column(
        Integer,
        comment='Minimum duration required'
    )
    
    max_duration_minutes = Column(
        Integer,
        comment='Maximum duration allowed'
    )
    
    requires_code = Column(
        Boolean,
        server_default='false',
        comment='Whether special code is required'
    )
    
    codes = Column(
        ARRAY(String(50)),
        comment='Valid codes for this special rate'
    )
    
    # =========================================================================
    # USAGE LIMITS
    # =========================================================================
    usage_limit = Column(
        Integer,
        comment='Maximum number of uses'
    )
    
    usage_count = Column(
        Integer,
        server_default='0',
        comment='Current usage count'
    )
    
    per_user_limit = Column(
        Integer,
        comment='Maximum uses per user'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether special rate is active'
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
        comment='User who created this special rate'
    )
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def is_valid(self, check_time: Optional[datetime] = None) -> bool:
        """Check if special rate is currently valid."""
        check_time = check_time or datetime.now()
        return (self.is_active and
                self.start_date <= check_time <= self.end_date and
                (not self.usage_limit or self.usage_count < self.usage_limit))
    
    def calculate_cost(
        self,
        base_cost: float,
        **kwargs
    ) -> float:
        """Calculate cost using this special rate."""
        if self.override_type == 'replace':
            return float(self.rate_value)
        elif self.override_type == 'discount_percentage':
            return base_cost * (1 - float(self.override_value) / 100)
        elif self.override_type == 'discount_fixed':
            return max(0, base_cost - float(self.override_value))
        else:
            return base_cost
    
    def record_usage(self) -> None:
        """Record usage of this special rate."""
        self.usage_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert special rate to dictionary."""
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'event_id': self.event_id,
            'event_name': self.event_name,
            'applicability': {
                'zone_ids': [str(z) for z in self.zone_ids] if self.zone_ids else [],
                'spot_types': self.spot_types,
                'vehicle_types': self.vehicle_types,
            },
            'validity': {
                'start_date': self.start_date.isoformat() if self.start_date else None,
                'end_date': self.end_date.isoformat() if self.end_date else None,
                'is_valid': self.is_valid(),
            },
            'rate': {
                'type': self.rate_type,
                'value': float(self.rate_value),
                'unit': self.unit,
                'currency': self.currency,
            },
            'override': {
                'type': self.override_type,
                'value': float(self.override_value) if self.override_value else None,
            },
            'restrictions': {
                'min_duration_minutes': self.min_duration_minutes,
                'max_duration_minutes': self.max_duration_minutes,
                'requires_code': self.requires_code,
            },
            'usage': {
                'limit': self.usage_limit,
                'count': self.usage_count,
                'per_user_limit': self.per_user_limit,
            },
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<SpecialRate(id={self.id}, code={self.code})>"


class RateFormula(Base):
    """
    Complex rate formulas for advanced pricing.
    
    Defines mathematical formulas for calculating rates based on multiple factors.
    """
    
    __tablename__ = 'rate_formulas'
    __table_args__ = (
        Index('ix_rate_formulas_code', 'code', unique=True),
        
        # Table comment
        {'comment': 'Complex rate formulas'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    code = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Unique formula code'
    )
    
    name = Column(
        String(200),
        nullable=False,
        comment='Formula name'
    )
    
    description = Column(
        Text,
        comment='Formula description'
    )
    
    formula = Column(
        Text,
        nullable=False,
        comment='Mathematical formula (e.g., "base * hours * demand_factor")'
    )
    
    variables = Column(
        JSONB,
        comment='Variables used in formula'
    )
    
    parameters = Column(
        JSONB,
        comment='Parameter definitions'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether formula is active'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
        comment='User who created this formula'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    creator = relationship('User', foreign_keys=[created_by])
    
    def evaluate(self, **kwargs) -> float:
        """
        Evaluate formula with given parameters.
        
        Args:
            **kwargs: Variable values
            
        Returns:
            Calculated rate
        """
        # This would use a safe expression evaluator
        # For production, use a library like numexpr or a custom parser
        context = {**self.parameters, **kwargs}
        
        # Simple example - in production, use proper evaluation
        try:
            result = eval(self.formula, {"__builtins__": {}}, context)
            return float(result)
        except Exception as e:
            logger.error(f"Error evaluating formula {self.code}: {e}")
            raise ValueError(f"Formula evaluation failed: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert formula to dictionary."""
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'formula': self.formula,
            'variables': self.variables,
            'parameters': self.parameters,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<RateFormula(id={self.id}, code={self.code})>"


# =========================================================================
# EVENT LISTENERS
# =========================================================================

@event.listens_for(Rate, 'before_insert')
def rate_before_insert(mapper, connection, target):
    """Generate rate code if not provided."""
    if not target.code:
        # Generate code based on type and unit
        type_map = {
            'hourly': 'HR',
            'daily': 'DAY',
            'weekly': 'WK',
            'monthly': 'MON',
            'yearly': 'YR',
            'event': 'EVT',
            'special': 'SPC',
        }
        prefix = type_map.get(target.rate_type, 'RTE')
        
        # Get next sequence number
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(code FROM 4)::INTEGER), 0) + 1
                FROM rates
                WHERE code LIKE :pattern
            """),
            {'pattern': f'{prefix}%'}
        )
        seq_num = result.scalar()
        
        target.code = f"{prefix}{seq_num:04d}"


@event.listens_for(Rate, 'after_update')
def rate_after_update(mapper, connection, target):
    """Record rate changes in history."""
    # Get changes
    state = object_session(target).get_changes(target)
    
    if state:
        # Get user from context or session
        user_id = getattr(target, 'updated_by', None)
        
        connection.execute(
            text("""
                INSERT INTO rate_history (
                    id, rate_id, rate_code, action, changed_by, changed_at,
                    old_values, new_values, effective_date
                ) VALUES (
                    gen_random_uuid(), :rate_id, :rate_code, :action,
                    :changed_by, CURRENT_TIMESTAMP, :old_values, :new_values,
                    :effective_date
                )
            """),
            {
                'rate_id': target.id,
                'rate_code': target.code,
                'action': 'UPDATE',
                'changed_by': user_id,
                'old_values': json.dumps({k: v[0] for k, v in state.items()}, default=str),
                'new_values': json.dumps({k: v[1] for k, v in state.items()}, default=str),
                'effective_date': target.effective_from
            }
        )


# =========================================================================
# FACTORY FUNCTIONS
# =========================================================================

def create_rate(
    name: str,
    rate_type: str,
    base_rate: float,
    unit: str = 'hour',
    zone_id: Optional[uuid.UUID] = None,
    spot_type: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    **kwargs
) -> Rate:
    """
    Factory function to create a new rate.
    
    Args:
        name: Rate name
        rate_type: Type of rate
        base_rate: Base rate amount
        unit: Rate unit
        zone_id: Zone ID
        spot_type: Spot type
        vehicle_type: Vehicle type
        **kwargs: Additional rate attributes
        
    Returns:
        New Rate instance
    """
    rate = Rate(
        name=name,
        rate_type=rate_type,
        base_rate=base_rate,
        unit=unit,
        zone_id=zone_id,
        spot_type=spot_type,
        vehicle_type=vehicle_type,
        **kwargs
    )
    
    return rate


def create_standard_rates(session) -> List[Rate]:
    """
    Create standard parking rates.
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        List of created rates
    """
    rates = [
        Rate(
            code='STD-HOURLY',
            name='Standard Hourly Rate',
            description='Standard hourly parking rate',
            rate_type='hourly',
            category='standard',
            base_rate=5.00,
            unit='hour',
            min_units=1,
            max_units=24,
            grace_period_minutes=15,
            has_maximum_cap=True,
            maximum_cap_amount=30.00,
            maximum_cap_period='day',
            is_default=True,
            is_system=True
        ),
        Rate(
            code='STD-DAILY',
            name='Standard Daily Rate',
            description='Standard daily parking rate',
            rate_type='daily',
            category='standard',
            base_rate=30.00,
            unit='day',
            min_units=1,
            max_units=30,
            grace_period_minutes=30,
            is_system=True
        ),
        Rate(
            code='STD-MONTHLY',
            name='Standard Monthly Rate',
            description='Standard monthly parking rate',
            rate_type='monthly',
            category='standard',
            base_rate=300.00,
            unit='month',
            min_units=1,
            max_units=12,
            grace_period_minutes=60,
            is_system=True
        ),
        Rate(
            code='EV-HOURLY',
            name='EV Charging Hourly Rate',
            description='Hourly rate for EV charging spots',
            rate_type='hourly',
            category='ev',
            base_rate=7.50,
            unit='hour',
            spot_type='electric',
            min_units=1,
            max_units=24,
            grace_period_minutes=15,
            is_system=True
        ),
        Rate(
            code='HANDICAP-HOURLY',
            name='Handicapped Hourly Rate',
            description='Hourly rate for handicapped spots',
            rate_type='hourly',
            category='handicap',
            base_rate=3.00,
            unit='hour',
            spot_type='handicapped',
            min_units=1,
            max_units=24,
            grace_period_minutes=30,
            is_system=True
        ),
        Rate(
            code='VIP-HOURLY',
            name='VIP Hourly Rate',
            description='Hourly rate for VIP spots',
            rate_type='hourly',
            category='vip',
            base_rate=10.00,
            unit='hour',
            spot_type='vip',
            min_units=1,
            max_units=24,
            grace_period_minutes=15,
            is_system=True
        ),
        Rate(
            code='MOTO-HOURLY',
            name='Motorcycle Hourly Rate',
            description='Hourly rate for motorcycle spots',
            rate_type='hourly',
            category='motorcycle',
            base_rate=2.50,
            unit='hour',
            spot_type='motorcycle',
            min_units=1,
            max_units=24,
            grace_period_minutes=15,
            is_system=True
        ),
        Rate(
            code='WEEKEND-SPECIAL',
            name='Weekend Special Rate',
            description='Special weekend rate',
            rate_type='weekend',
            category='standard',
            base_rate=20.00,
            unit='day',
            weekend_multiplier=0.8,
            has_weekend_rate=True,
            weekend_rate=20.00,
            is_promotional=True,
            is_system=True
        ),
        Rate(
            code='EARLY-BIRD',
            name='Early Bird Special',
            description='Early bird rate (before 9 AM)',
            rate_type='early_bird',
            category='standard',
            base_rate=15.00,
            unit='day',
            has_peak_pricing=True,
            peak_times=[
                {'start_time': '06:00', 'end_time': '09:00', 'days': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']}
            ],
            off_peak_rate_multiplier=0.7,
            is_promotional=True,
            is_system=True
        ),
        Rate(
            code='NIGHT-OWL',
            name='Night Owl Rate',
            description='Overnight parking rate',
            rate_type='night_owl',
            category='standard',
            base_rate=10.00,
            unit='night',
            has_night_rate=True,
            night_rate=10.00,
            night_start_time=Time(22, 0),
            night_end_time=Time(6, 0),
            is_system=True
        ),
    ]
    
    for rate in rates:
        existing = session.query(Rate).filter_by(code=rate.code).first()
        if not existing:
            session.add(rate)
    
    session.commit()
    return rates


# =========================================================================
# EXPORTS
# =========================================================================

__all__ = [
    # Main models
    'Rate',
    'RateHistory',
    'RateSchedule',
    'SpecialRate',
    'RateFormula',
    
    # Enums
    'RateType',
    'RateUnit',
    'RateCategory',
    'DayOfWeek',
    'Season',
    'HolidayType',
    'RateConditionType',
    'DynamicPricingModel',
    'Currency',
    
    # Factory functions
    'create_rate',
    'create_standard_rates',
]