# parking-management/data/migrations/models/reservation.py

"""
Reservation model for parking management system.

This module defines the Reservation model and related classes for managing
parking spot reservations, including recurring reservations, group bookings,
waitlist management, and blackout dates.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Time,
    Text, ForeignKey, UniqueConstraint, Index, CheckConstraint,
    Numeric, JSON, Table, func, text, event, and_, or_
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, backref, validates, object_session
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declarative_base
import uuid
import enum
import json
from datetime import datetime, date, timedelta
import logging
from typing import Optional, List, Dict, Any, Tuple
import qrcode
import io
import base64

# Configure logging
logger = logging.getLogger(__name__)

# Create base class
Base = declarative_base()


class ReservationStatus(str, enum.Enum):
    """Enum for reservation status."""
    DRAFT = 'draft'
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CHECKED_IN = 'checked_in'
    CHECKED_OUT = 'checked_out'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    NO_SHOW = 'no_show'
    EXPIRED = 'expired'
    MODIFIED = 'modified'
    REFUNDED = 'refunded'


class ReservationType(str, enum.Enum):
    """Enum for reservation types."""
    STANDARD = 'standard'
    VIP = 'vip'
    EVENT = 'event'
    MONTHLY = 'monthly'
    CORPORATE = 'corporate'
    STAFF = 'staff'
    VALET = 'valet'


class PaymentStatus(str, enum.Enum):
    """Enum for payment status."""
    PENDING = 'pending'
    AUTHORIZED = 'authorized'
    PAID = 'paid'
    PARTIALLY_PAID = 'partially_paid'
    REFUNDED = 'refunded'
    PARTIALLY_REFUNDED = 'partially_refunded'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class RecurringFrequency(str, enum.Enum):
    """Enum for recurring reservation frequency."""
    DAILY = 'daily'
    WEEKLY = 'weekly'
    BI_WEEKLY = 'bi_weekly'
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    YEARLY = 'yearly'
    WEEKDAYS = 'weekdays'
    WEEKENDS = 'weekends'
    CUSTOM = 'custom'


class WaitlistStatus(str, enum.Enum):
    """Enum for waitlist status."""
    ACTIVE = 'active'
    NOTIFIED = 'notified'
    CONVERTED = 'converted'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'


class Reservation(Base):
    """
    Parking spot reservations made by users.
    
    Supports recurring, group, and guest reservations with comprehensive
    tracking of status, payments, modifications, and check-in/out.
    """
    
    __tablename__ = 'reservations'
    __table_args__ = (
        # Primary indexes
        Index('ix_reservations_number', 'reservation_number', unique=True),
        Index('ix_reservations_external_ref', 'external_reference', unique=True),
        Index('ix_reservations_qr_code', 'qr_code'),
        
        # Foreign key indexes
        Index('ix_reservations_spot_id', 'spot_id'),
        Index('ix_reservations_user_id', 'user_id'),
        Index('ix_reservations_vehicle_id', 'vehicle_id'),
        Index('ix_reservations_rate_id', 'rate_id'),
        
        # Status indexes
        Index('ix_reservations_status', 'status'),
        Index('ix_reservations_payment_status', 'payment_status'),
        
        # Time-based indexes
        Index('ix_reservations_time_range', 'start_time', 'end_time'),
        Index('ix_reservations_start_time', 'start_time'),
        Index('ix_reservations_end_time', 'end_time'),
        Index('ix_reservations_created_at', 'created_at'),
        
        # Composite indexes for common queries
        Index('ix_reservations_active_times', 'spot_id', 'start_time', 'end_time',
              postgresql_where=text("status IN ('confirmed', 'checked_in')")),
        Index('ix_reservations_user_status', 'user_id', 'status', 'start_time'),
        Index('ix_reservations_vehicle_status', 'vehicle_id', 'status'),
        
        # Check-in/out indexes
        Index('ix_reservations_check_in', 'actual_check_in', 'status'),
        Index('ix_reservations_check_out', 'actual_check_out', 'status'),
        
        # Guest reservation indexes
        Index('ix_reservations_guest_email', 'guest_email'),
        Index('ix_reservations_guest_phone', 'guest_phone'),
        
        # Payment related indexes
        Index('ix_reservations_unpaid', 'payment_status', 'end_time',
              postgresql_where=text("payment_status != 'paid'")),
        
        # Group reservation indexes
        Index('ix_reservations_group_id', 'group_id'),
        
        # Recurring reservation indexes
        Index('ix_reservations_recurring_id', 'recurring_id'),
        
        # Partial indexes for active reservations
        Index('ix_reservations_current', 'spot_id', 'end_time',
              postgresql_where=text(
                  "status IN ('confirmed', 'checked_in') "
                  "AND start_time <= CURRENT_TIMESTAMP "
                  "AND end_time >= CURRENT_TIMESTAMP"
              )),
        Index('ix_reservations_upcoming_24h', 'start_time', 'status',
              postgresql_where=text(
                  "status = 'confirmed' "
                  "AND start_time BETWEEN CURRENT_TIMESTAMP AND CURRENT_TIMESTAMP + INTERVAL '24 hours'"
              )),
        
        # Check constraints
        CheckConstraint(
            "status IN ('draft', 'pending', 'confirmed', 'checked_in', 'checked_out', "
            "'completed', 'cancelled', 'no_show', 'expired', 'modified', 'refunded')",
            name='ck_reservations_status'
        ),
        CheckConstraint(
            "reservation_type IN ('standard', 'vip', 'event', 'monthly', 'corporate', 'staff', 'valet')",
            name='ck_reservations_type'
        ),
        CheckConstraint(
            "payment_status IN ('pending', 'authorized', 'paid', 'partially_paid', "
            "'refunded', 'partially_refunded', 'failed', 'cancelled')",
            name='ck_reservations_payment_status'
        ),
        CheckConstraint(
            "end_time > start_time",
            name='ck_reservations_time_range'
        ),
        
        # Table comment
        {'comment': 'Parking spot reservations'}
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
    
    reservation_number = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Unique human-readable reservation number'
    )
    
    external_reference = Column(
        String(100),
        unique=True,
        comment='External reference ID (from third-party booking)'
    )
    
    qr_code = Column(
        Text,
        comment='QR code data for check-in'
    )
    
    barcode = Column(
        String(255),
        comment='Barcode for check-in'
    )
    
    # =========================================================================
    # CORE RELATIONSHIPS
    # =========================================================================
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='RESTRICT'),
        nullable=False,
        comment='ID of reserved parking spot'
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='ID of user who made reservation (null for guest)'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='SET NULL'),
        comment='ID of vehicle for this reservation'
    )
    
    rate_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_rates.id', ondelete='SET NULL'),
        comment='ID of rate applied'
    )
    
    # =========================================================================
    # GUEST INFORMATION
    # =========================================================================
    is_guest = Column(
        Boolean,
        nullable=False,
        server_default='false',
        comment='Whether this is a guest reservation'
    )
    
    guest_email = Column(
        String(255),
        comment='Guest email address'
    )
    
    guest_phone = Column(
        String(20),
        comment='Guest phone number'
    )
    
    guest_first_name = Column(
        String(100),
        comment='Guest first name'
    )
    
    guest_last_name = Column(
        String(100),
        comment='Guest last name'
    )
    
    guest_company = Column(
        String(200),
        comment='Guest company name'
    )
    
    # =========================================================================
    # RESERVATION DETAILS
    # =========================================================================
    status = Column(
        String(20),
        nullable=False,
        server_default='pending',
        comment='Current reservation status'
    )
    
    reservation_type = Column(
        String(50),
        nullable=False,
        server_default='standard',
        comment='Type of reservation'
    )
    
    start_time = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Reservation start time'
    )
    
    end_time = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Reservation end time'
    )
    
    flexible_timing = Column(
        Boolean,
        server_default='false',
        comment='Whether timing is flexible'
    )
    
    flexible_window_minutes = Column(
        Integer,
        comment='Flexible window in minutes'
    )
    
    buffer_time_before = Column(
        Integer,
        server_default='0',
        comment='Buffer time before reservation (minutes)'
    )
    
    buffer_time_after = Column(
        Integer,
        server_default='0',
        comment='Buffer time after reservation (minutes)'
    )
    
    # =========================================================================
    # VEHICLE INFORMATION (SNAPSHOT)
    # =========================================================================
    license_plate = Column(
        String(20),
        comment='License plate at time of booking'
    )
    
    vehicle_make = Column(
        String(100),
        comment='Vehicle make at time of booking'
    )
    
    vehicle_model = Column(
        String(100),
        comment='Vehicle model at time of booking'
    )
    
    vehicle_color = Column(
        String(50),
        comment='Vehicle color at time of booking'
    )
    
    vehicle_type = Column(
        String(20),
        comment='Vehicle type at time of booking'
    )
    
    vehicle_length_cm = Column(
        Integer,
        comment='Vehicle length at time of booking'
    )
    
    vehicle_height_cm = Column(
        Integer,
        comment='Vehicle height at time of booking'
    )
    
    vehicle_notes = Column(
        Text,
        comment='Additional vehicle notes'
    )
    
    # =========================================================================
    # CHECK-IN/OUT TRACKING
    # =========================================================================
    actual_check_in = Column(
        DateTime(timezone=True),
        comment='Actual check-in time'
    )
    
    actual_check_out = Column(
        DateTime(timezone=True),
        comment='Actual check-out time'
    )
    
    duration_minutes = Column(
        Integer,
        comment='Actual duration in minutes'
    )
    
    check_in_code = Column(
        String(50),
        comment='Check-in code'
    )
    
    check_in_method = Column(
        String(50),
        comment='Method used for check-in (qr, manual, app, gate)'
    )
    
    check_in_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who performed check-in'
    )
    
    check_in_gate = Column(
        String(50),
        comment='Gate used for entry'
    )
    
    check_in_image_url = Column(
        String(500),
        comment='Image URL of vehicle at entry'
    )
    
    check_out_method = Column(
        String(50),
        comment='Method used for check-out'
    )
    
    check_out_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who performed check-out'
    )
    
    check_out_gate = Column(
        String(50),
        comment='Gate used for exit'
    )
    
    check_out_image_url = Column(
        String(500),
        comment='Image URL of vehicle at exit'
    )
    
    # =========================================================================
    # PRICING
    # =========================================================================
    base_amount = Column(
        Numeric(10, 2),
        nullable=False,
        server_default='0',
        comment='Base amount before taxes/fees'
    )
    
    tax_amount = Column(
        Numeric(10, 2),
        server_default='0',
        comment='Tax amount'
    )
    
    discount_amount = Column(
        Numeric(10, 2),
        server_default='0',
        comment='Discount amount'
    )
    
    addons_amount = Column(
        Numeric(10, 2),
        server_default='0',
        comment='Add-ons amount'
    )
    
    fees_amount = Column(
        Numeric(10, 2),
        server_default='0',
        comment='Additional fees amount'
    )
    
    total_amount = Column(
        Numeric(10, 2),
        nullable=False,
        server_default='0',
        comment='Total amount'
    )
    
    currency = Column(
        String(3),
        nullable=False,
        server_default='USD',
        comment='Currency code'
    )
    
    tax_rate = Column(
        Numeric(5, 2),
        comment='Tax rate applied'
    )
    
    tax_details = Column(
        JSONB,
        comment='Detailed tax breakdown'
    )
    
    # =========================================================================
    # DISCOUNTS
    # =========================================================================
    discount_code = Column(
        String(50),
        comment='Discount code applied'
    )
    
    discount_type = Column(
        String(20),
        comment='Type of discount (percentage, fixed)'
    )
    
    discount_value = Column(
        Numeric(10, 2),
        comment='Discount value'
    )
    
    promotion_id = Column(
        String(100),
        comment='ID of applied promotion'
    )
    
    # =========================================================================
    # PAYMENT
    # =========================================================================
    payment_status = Column(
        String(20),
        nullable=False,
        server_default='pending',
        comment='Payment status'
    )
    
    payment_method = Column(
        String(50),
        comment='Payment method used'
    )
    
    payment_token = Column(
        String(255),
        comment='Payment token'
    )
    
    payment_intent_id = Column(
        String(255),
        comment='Payment intent ID from provider'
    )
    
    payment_receipt_url = Column(
        String(500),
        comment='URL to payment receipt'
    )
    
    requires_deposit = Column(
        Boolean,
        server_default='false',
        comment='Whether deposit is required'
    )
    
    deposit_amount = Column(
        Numeric(10, 2),
        comment='Deposit amount'
    )
    
    deposit_paid = Column(
        Boolean,
        server_default='false',
        comment='Whether deposit has been paid'
    )
    
    balance_due = Column(
        Numeric(10, 2),
        comment='Balance due'
    )
    
    balance_due_date = Column(
        DateTime(timezone=True),
        comment='Date when balance is due'
    )
    
    # =========================================================================
    # CANCELLATION
    # =========================================================================
    cancellation_reason = Column(
        Text,
        comment='Reason for cancellation'
    )
    
    cancelled_at = Column(
        DateTime(timezone=True),
        comment='When reservation was cancelled'
    )
    
    cancelled_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who cancelled'
    )
    
    cancellation_fee = Column(
        Numeric(10, 2),
        comment='Cancellation fee charged'
    )
    
    refund_amount = Column(
        Numeric(10, 2),
        comment='Amount refunded'
    )
    
    refund_id = Column(
        String(255),
        comment='Refund transaction ID'
    )
    
    refunded_at = Column(
        DateTime(timezone=True),
        comment='When refund was processed'
    )
    
    # =========================================================================
    # MODIFICATION TRACKING
    # =========================================================================
    modified_count = Column(
        Integer,
        server_default='0',
        comment='Number of times reservation was modified'
    )
    
    last_modified_at = Column(
        DateTime(timezone=True),
        comment='When reservation was last modified'
    )
    
    original_start_time = Column(
        DateTime(timezone=True),
        comment='Original start time before modifications'
    )
    
    original_end_time = Column(
        DateTime(timezone=True),
        comment='Original end time before modifications'
    )
    
    modification_history = Column(
        JSONB,
        comment='History of modifications'
    )
    
    # =========================================================================
    # ADDITIONAL SERVICES
    # =========================================================================
    addons = Column(
        JSONB,
        comment='Add-on services selected'
    )
    
    special_requests = Column(
        Text,
        comment='Special requests from customer'
    )
    
    access_instructions = Column(
        Text,
        comment='Access instructions for the spot'
    )
    
    has_valet = Column(
        Boolean,
        server_default='false',
        comment='Whether valet service is requested'
    )
    
    valet_key_location = Column(
        String(255),
        comment='Location where valet key is kept'
    )
    
    # =========================================================================
    # RECURRING RESERVATIONS
    # =========================================================================
    is_recurring = Column(
        Boolean,
        server_default='false',
        comment='Whether this is part of a recurring series'
    )
    
    recurring_id = Column(
        UUID(as_uuid=True),
        comment='ID of recurring series'
    )
    
    recurring_sequence = Column(
        Integer,
        comment='Sequence number in recurring series'
    )
    
    # =========================================================================
    # GROUP RESERVATIONS
    # =========================================================================
    is_group_reservation = Column(
        Boolean,
        server_default='false',
        comment='Whether this is a group reservation'
    )
    
    group_id = Column(
        String(100),
        comment='Group identifier'
    )
    
    group_name = Column(
        String(200),
        comment='Group name'
    )
    
    group_size = Column(
        Integer,
        comment='Total size of group'
    )
    
    # =========================================================================
    # CORPORATE/COMPANY
    # =========================================================================
    is_corporate = Column(
        Boolean,
        server_default='false',
        comment='Whether this is a corporate reservation'
    )
    
    company_name = Column(
        String(200),
        comment='Company name'
    )
    
    company_id = Column(
        String(100),
        comment='Company ID'
    )
    
    cost_center = Column(
        String(100),
        comment='Cost center for billing'
    )
    
    po_number = Column(
        String(100),
        comment='Purchase order number'
    )
    
    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================
    reminder_sent = Column(
        Boolean,
        server_default='false',
        comment='Whether reminder has been sent'
    )
    
    reminder_sent_at = Column(
        DateTime(timezone=True),
        comment='When reminder was sent'
    )
    
    reminder_count = Column(
        Integer,
        server_default='0',
        comment='Number of reminders sent'
    )
    
    confirmation_sent = Column(
        Boolean,
        server_default='false',
        comment='Whether confirmation was sent'
    )
    
    confirmation_sent_at = Column(
        DateTime(timezone=True),
        comment='When confirmation was sent'
    )
    
    # =========================================================================
    # SOURCE TRACKING
    # =========================================================================
    source = Column(
        String(50),
        comment='Booking source (web, mobile, api, walk-in)'
    )
    
    source_channel = Column(
        String(50),
        comment='Source channel'
    )
    
    campaign_source = Column(
        String(100),
        comment='Marketing campaign source'
    )
    
    booking_agent = Column(
        String(200),
        comment='Booking agent name'
    )
    
    booking_agent_id = Column(
        String(100),
        comment='Booking agent ID'
    )
    
    commission_rate = Column(
        Numeric(5, 2),
        comment='Commission rate for agent'
    )
    
    commission_amount = Column(
        Numeric(10, 2),
        comment='Commission amount'
    )
    
    # =========================================================================
    # NOTES
    # =========================================================================
    internal_notes = Column(
        Text,
        comment='Internal notes (staff only)'
    )
    
    customer_notes = Column(
        Text,
        comment='Notes visible to customer'
    )
    
    staff_notes = Column(
        Text,
        comment='Notes between staff'
    )
    
    # =========================================================================
    # FLEXIBLE FIELDS
    # =========================================================================
    custom_fields = Column(
        JSONB,
        comment='Custom fields for flexible data'
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
        comment='User who created this record'
    )
    
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who last updated this record'
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        comment='Soft delete timestamp'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    spot = relationship(
        'ParkingSpot',
        foreign_keys=[spot_id],
        back_populates='current_reservation',
        comment='Reserved parking spot'
    )
    
    user = relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='reservations',
        comment='User who made reservation'
    )
    
    vehicle = relationship(
        'Vehicle',
        foreign_keys=[vehicle_id],
        comment='Vehicle for this reservation'
    )
    
    rate = relationship(
        'ParkingRate',
        foreign_keys=[rate_id],
        comment='Rate applied'
    )
    
    check_in_user = relationship(
        'User',
        foreign_keys=[check_in_by],
        comment='User who performed check-in'
    )
    
    check_out_user = relationship(
        'User',
        foreign_keys=[check_out_by],
        comment='User who performed check-out'
    )
    
    cancelled_by_user = relationship(
        'User',
        foreign_keys=[cancelled_by],
        comment='User who cancelled'
    )
    
    created_by_user = relationship(
        'User',
        foreign_keys=[created_by],
        comment='User who created'
    )
    
    updated_by_user = relationship(
        'User',
        foreign_keys=[updated_by],
        comment='User who last updated'
    )
    
    attendees = relationship(
        'ReservationAttendee',
        back_populates='reservation',
        cascade='all, delete-orphan',
        comment='Attendees for group reservations'
    )
    
    addon_items = relationship(
        'ReservationAddon',
        back_populates='reservation',
        cascade='all, delete-orphan',
        comment='Add-on services'
    )
    
    payments = relationship(
        'Payment',
        back_populates='reservation',
        cascade='all, delete-orphan',
        comment='Payments for this reservation'
    )
    
    history = relationship(
        'ReservationHistory',
        back_populates='reservation',
        cascade='all, delete-orphan',
        comment='History of changes'
    )
    
    feedback = relationship(
        'ReservationFeedback',
        back_populates='reservation',
        uselist=False,
        cascade='all, delete-orphan',
        comment='Customer feedback'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if reservation is currently active."""
        now = datetime.now(self.start_time.tzinfo if self.start_time else None)
        return (self.status in ['confirmed', 'checked_in'] and
                self.start_time <= now <= self.end_time)
    
    @hybrid_property
    def is_upcoming(self) -> bool:
        """Check if reservation is upcoming."""
        now = datetime.now(self.start_time.tzinfo if self.start_time else None)
        return self.status == 'confirmed' and self.start_time > now
    
    @hybrid_property
    def is_past(self) -> bool:
        """Check if reservation is past."""
        now = datetime.now(self.end_time.tzinfo if self.end_time else None)
        return self.end_time < now
    
    @hybrid_property
    def is_cancellable(self) -> bool:
        """Check if reservation can be cancelled."""
        return self.status in ['pending', 'confirmed'] and not self.is_active
    
    @hybrid_property
    def is_modifiable(self) -> bool:
        """Check if reservation can be modified."""
        return self.status in ['pending', 'confirmed'] and not self.is_active
    
    @hybrid_property
    def duration_hours(self) -> float:
        """Get scheduled duration in hours."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() / 3600
        return 0
    
    @hybrid_property
    def actual_duration_hours(self) -> Optional[float]:
        """Get actual duration in hours."""
        if self.actual_check_in and self.actual_check_out:
            delta = self.actual_check_out - self.actual_check_in
            return delta.total_seconds() / 3600
        return None
    
    @hybrid_property
    def customer_name(self) -> Optional[str]:
        """Get customer name (registered user or guest)."""
        if self.user:
            return self.user.display_name
        elif self.guest_first_name:
            return f"{self.guest_first_name} {self.guest_last_name or ''}".strip()
        return None
    
    @hybrid_property
    def customer_email(self) -> Optional[str]:
        """Get customer email."""
        if self.user:
            return self.user.email
        return self.guest_email
    
    @hybrid_property
    def customer_phone(self) -> Optional[str]:
        """Get customer phone."""
        if self.user:
            return self.user.phone_number
        return self.guest_phone
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @validates('start_time', 'end_time')
    def validate_times(self, key, value):
        """Validate time range."""
        if key == 'start_time' and hasattr(self, 'end_time') and self.end_time:
            if value >= self.end_time:
                raise ValueError('start_time must be before end_time')
        elif key == 'end_time' and hasattr(self, 'start_time') and self.start_time:
            if value <= self.start_time:
                raise ValueError('end_time must be after start_time')
        return value
    
    @validates('guest_email')
    def validate_guest_email(self, key, email):
        """Validate guest email format."""
        if email and not self.user_id:
            import re
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                raise ValueError('Invalid email format')
        return email
    
    @validates('guest_phone')
    def validate_guest_phone(self, key, phone):
        """Validate guest phone format."""
        if phone and not self.user_id:
            import re
            if not re.match(r'^\+?[1-9]\d{1,14}$', phone):
                raise ValueError('Invalid phone number format')
        return phone
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def confirm(self) -> None:
        """Confirm the reservation."""
        if self.status == 'pending':
            self.status = 'confirmed'
            self._add_history('confirm', 'pending', 'confirmed')
    
    def check_in(self, method: str = 'manual', gate: Optional[str] = None, 
                 user_id: Optional[uuid.UUID] = None) -> None:
        """
        Check in to the reservation.
        
        Args:
            method: Check-in method
            gate: Gate used
            user_id: ID of user performing check-in
        """
        if self.status in ['confirmed', 'reserved']:
            old_status = self.status
            self.status = 'checked_in'
            self.actual_check_in = datetime.now()
            self.check_in_method = method
            self.check_in_gate = gate
            self.check_in_by = user_id
            
            # Update spot occupancy
            if self.spot:
                self.spot.occupy(
                    vehicle_id=self.vehicle_id,
                    session_id=None,  # Will be created by session service
                    reservation_id=self.id
                )
            
            self._add_history('check_in', old_status, 'checked_in')
    
    def check_out(self, method: str = 'manual', gate: Optional[str] = None,
                  user_id: Optional[uuid.UUID] = None) -> None:
        """
        Check out from the reservation.
        
        Args:
            method: Check-out method
            gate: Gate used
            user_id: ID of user performing check-out
        """
        if self.status == 'checked_in':
            old_status = self.status
            self.status = 'checked_out'
            self.actual_check_out = datetime.now()
            self.check_out_method = method
            self.check_out_gate = gate
            self.check_out_by = user_id
            
            # Calculate actual duration
            if self.actual_check_in:
                delta = self.actual_check_out - self.actual_check_in
                self.duration_minutes = int(delta.total_seconds() / 60)
            
            # Update spot occupancy
            if self.spot:
                self.spot.vacate()
            
            self._add_history('check_out', old_status, 'checked_out')
    
    def cancel(self, reason: str, user_id: Optional[uuid.UUID] = None,
               apply_fee: bool = False) -> None:
        """
        Cancel the reservation.
        
        Args:
            reason: Cancellation reason
            user_id: ID of user performing cancellation
            apply_fee: Whether to apply cancellation fee
        """
        if self.is_cancellable:
            old_status = self.status
            self.status = 'cancelled'
            self.cancellation_reason = reason
            self.cancelled_at = datetime.now()
            self.cancelled_by = user_id
            
            if apply_fee:
                # Calculate cancellation fee (e.g., 10% of total)
                self.cancellation_fee = self.total_amount * 0.1
            
            # Release the spot if it was reserved
            if self.spot and self.spot.current_reservation_id == self.id:
                self.spot.release_reservation()
            
            self._add_history('cancel', old_status, 'cancelled', {
                'reason': reason,
                'apply_fee': apply_fee
            })
    
    def modify_times(self, new_start: datetime, new_end: datetime,
                     user_id: Optional[uuid.UUID] = None) -> bool:
        """
        Modify reservation times.
        
        Args:
            new_start: New start time
            new_end: New end time
            user_id: ID of user performing modification
            
        Returns:
            True if modification was successful
        """
        if not self.is_modifiable:
            raise ValueError('Reservation cannot be modified')
        
        # Check availability
        if self.spot and not self.spot.check_availability(
            new_start, new_end, exclude_reservation_id=self.id
        ):
            raise ValueError('Spot not available for requested times')
        
        # Store original times for history
        if not self.original_start_time:
            self.original_start_time = self.start_time
            self.original_end_time = self.end_time
        
        # Update times
        old_start = self.start_time
        old_end = self.end_time
        self.start_time = new_start
        self.end_time = new_end
        self.modified_count += 1
        self.last_modified_at = datetime.now()
        self.updated_by = user_id
        
        # Recalculate price if needed
        if self.rate:
            cost = self.spot.calculate_parking_cost(
                new_start, new_end, self.vehicle_type
            )
            self.base_amount = cost['base_amount']
            self.tax_amount = cost['tax_amount']
            self.total_amount = cost['total_amount']
        
        self._add_history('modify', None, None, {
            'old_start': old_start.isoformat(),
            'old_end': old_end.isoformat(),
            'new_start': new_start.isoformat(),
            'new_end': new_end.isoformat()
        })
        
        return True
    
    def generate_qr_code(self) -> str:
        """
        Generate QR code for check-in.
        
        Returns:
            Base64 encoded QR code image
        """
        data = {
            'id': str(self.id),
            'number': self.reservation_number,
            'spot': self.spot.spot_number if self.spot else None,
            'start': self.start_time.isoformat(),
            'end': self.end_time.isoformat()
        }
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(json.dumps(data))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        self.qr_code = base64.b64encode(buffer.getvalue()).decode()
        
        return self.qr_code
    
    def process_payment(self, payment_method: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """
        Process payment for reservation.
        
        Args:
            payment_method: Payment method to use
            amount: Amount to charge (None for full amount)
            
        Returns:
            Payment result
        """
        from models.payment import Payment
        
        amount_to_charge = amount or float(self.total_amount - (self.deposit_amount or 0))
        
        # Create payment record
        payment = Payment(
            user_id=self.user_id,
            reservation_id=self.id,
            amount=amount_to_charge,
            currency=self.currency,
            payment_method=payment_method,
            status='pending'
        )
        
        # In production, integrate with payment gateway here
        # payment_result = payment_gateway.charge(amount_to_charge, payment_method)
        
        # Mock successful payment
        payment.status = 'paid'
        payment.paid_at = datetime.now()
        
        object_session(self).add(payment)
        
        if amount_to_charge >= float(self.total_amount):
            self.payment_status = 'paid'
        else:
            self.payment_status = 'partially_paid'
            self.balance_due = float(self.total_amount) - amount_to_charge
        
        return {
            'success': True,
            'payment_id': str(payment.id),
            'amount': amount_to_charge,
            'status': payment.status
        }
    
    def send_confirmation(self) -> bool:
        """
        Send confirmation notification.
        
        Returns:
            True if sent successfully
        """
        # This would integrate with notification service
        self.confirmation_sent = True
        self.confirmation_sent_at = datetime.now()
        return True
    
    def send_reminder(self) -> bool:
        """
        Send reminder notification.
        
        Returns:
            True if sent successfully
        """
        self.reminder_sent = True
        self.reminder_sent_at = datetime.now()
        self.reminder_count += 1
        return True
    
    def _add_history(self, action: str, old_status: Optional[str], 
                    new_status: Optional[str], details: Optional[Dict] = None) -> None:
        """
        Add entry to reservation history.
        
        Args:
            action: Action performed
            old_status: Previous status
            new_status: New status
            details: Additional details
        """
        history = ReservationHistory(
            reservation_id=self.id,
            action=action,
            previous_status=old_status,
            new_status=new_status,
            changes=details,
            performed_by=self.updated_by or self.created_by,
            performed_at=datetime.now()
        )
        object_session(self).add(history)
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert reservation to dictionary."""
        data = {
            'id': str(self.id),
            'reservation_number': self.reservation_number,
            'external_reference': self.external_reference,
            'spot_id': str(self.spot_id),
            'spot_number': self.spot.spot_number if self.spot else None,
            'zone_name': self.spot.zone.name if self.spot and self.spot.zone else None,
            'user_id': str(self.user_id) if self.user_id else None,
            'vehicle_id': str(self.vehicle_id) if self.vehicle_id else None,
            'status': self.status,
            'reservation_type': self.reservation_type,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'actual_check_in': self.actual_check_in.isoformat() if self.actual_check_in else None,
            'actual_check_out': self.actual_check_out.isoformat() if self.actual_check_out else None,
            'duration_hours': self.duration_hours,
            'actual_duration_hours': self.actual_duration_hours,
            'is_active': self.is_active,
            'is_upcoming': self.is_upcoming,
            'is_past': self.is_past,
            
            # Customer info
            'is_guest': self.is_guest,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_phone': self.customer_phone,
            
            # Vehicle info
            'license_plate': self.license_plate,
            'vehicle_make': self.vehicle_make,
            'vehicle_model': self.vehicle_model,
            'vehicle_color': self.vehicle_color,
            'vehicle_type': self.vehicle_type,
            
            # Pricing
            'base_amount': float(self.base_amount) if self.base_amount else None,
            'tax_amount': float(self.tax_amount) if self.tax_amount else None,
            'discount_amount': float(self.discount_amount) if self.discount_amount else None,
            'addons_amount': float(self.addons_amount) if self.addons_amount else None,
            'fees_amount': float(self.fees_amount) if self.fees_amount else None,
            'total_amount': float(self.total_amount) if self.total_amount else None,
            'currency': self.currency,
            
            # Payment
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'requires_deposit': self.requires_deposit,
            'deposit_amount': float(self.deposit_amount) if self.deposit_amount else None,
            'deposit_paid': self.deposit_paid,
            'balance_due': float(self.balance_due) if self.balance_due else None,
            
            # Cancellation
            'is_cancellable': self.is_cancellable,
            'cancellation_reason': self.cancellation_reason,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'cancellation_fee': float(self.cancellation_fee) if self.cancellation_fee else None,
            'refund_amount': float(self.refund_amount) if self.refund_amount else None,
            
            # Group info
            'is_group_reservation': self.is_group_reservation,
            'group_id': self.group_id,
            'group_name': self.group_name,
            'group_size': self.group_size,
            
            # Recurring
            'is_recurring': self.is_recurring,
            'recurring_id': str(self.recurring_id) if self.recurring_id else None,
            'recurring_sequence': self.recurring_sequence,
            
            # Corporate
            'is_corporate': self.is_corporate,
            'company_name': self.company_name,
            'po_number': self.po_number,
            
            # Source
            'source': self.source,
            'booking_agent': self.booking_agent,
            
            # Notes
            'special_requests': self.special_requests,
            'customer_notes': self.customer_notes,
            
            # Timestamps
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data.update({
                'qr_code': self.qr_code,
                'check_in_code': self.check_in_code,
                'internal_notes': self.internal_notes,
                'staff_notes': self.staff_notes,
                'modification_history': self.modification_history,
                'custom_fields': self.custom_fields,
                'metadata': self.metadata,
            })
        
        return data
    
    def __repr__(self) -> str:
        return f"<Reservation(id={self.id}, number={self.reservation_number}, status={self.status})>"


class ReservationAttendee(Base):
    """
    Attendees for group reservations.
    
    Tracks individual attendees within a group reservation, including
    their check-in/out status and assigned spots.
    """
    
    __tablename__ = 'reservation_attendees'
    __table_args__ = (
        Index('ix_attendees_reservation', 'reservation_id'),
        Index('ix_attendees_email', 'email'),
        Index('ix_attendees_license', 'license_plate'),
        Index('ix_attendees_status', 'status'),
        {'comment': 'Attendees for group reservations'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    reservation_id = Column(
        UUID(as_uuid=True),
        ForeignKey('reservations.id', ondelete='CASCADE'),
        nullable=False
    )
    
    first_name = Column(
        String(100),
        nullable=False,
        comment='Attendee first name'
    )
    
    last_name = Column(
        String(100),
        comment='Attendee last name'
    )
    
    email = Column(
        String(255),
        comment='Attendee email'
    )
    
    phone = Column(
        String(20),
        comment='Attendee phone'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='SET NULL'),
        comment='Attendee vehicle ID'
    )
    
    license_plate = Column(
        String(20),
        comment='Attendee license plate'
    )
    
    vehicle_make = Column(
        String(100),
        comment='Attendee vehicle make'
    )
    
    vehicle_model = Column(
        String(100),
        comment='Attendee vehicle model'
    )
    
    vehicle_color = Column(
        String(50),
        comment='Attendee vehicle color'
    )
    
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='SET NULL'),
        comment='Assigned spot for this attendee'
    )
    
    status = Column(
        String(20),
        nullable=False,
        server_default='confirmed',
        comment='Attendee status'
    )
    
    checked_in_at = Column(
        DateTime(timezone=True),
        comment='When attendee checked in'
    )
    
    checked_out_at = Column(
        DateTime(timezone=True),
        comment='When attendee checked out'
    )
    
    qr_code = Column(
        Text,
        comment='QR code for attendee check-in'
    )
    
    access_code = Column(
        String(50),
        comment='Access code for attendee'
    )
    
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    reservation = relationship('Reservation', back_populates='attendees')
    vehicle = relationship('Vehicle')
    spot = relationship('ParkingSpot')
    
    @hybrid_property
    def full_name(self) -> str:
        """Get attendee full name."""
        if self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name
    
    def check_in(self) -> None:
        """Check in attendee."""
        self.status = 'checked_in'
        self.checked_in_at = datetime.now()
    
    def check_out(self) -> None:
        """Check out attendee."""
        self.status = 'checked_out'
        self.checked_out_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert attendee to dictionary."""
        return {
            'id': str(self.id),
            'reservation_id': str(self.reservation_id),
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'email': self.email,
            'phone': self.phone,
            'vehicle_id': str(self.vehicle_id) if self.vehicle_id else None,
            'license_plate': self.license_plate,
            'vehicle_make': self.vehicle_make,
            'vehicle_model': self.vehicle_model,
            'vehicle_color': self.vehicle_color,
            'spot_id': str(self.spot_id) if self.spot_id else None,
            'status': self.status,
            'checked_in_at': self.checked_in_at.isoformat() if self.checked_in_at else None,
            'checked_out_at': self.checked_out_at.isoformat() if self.checked_out_at else None,
            'access_code': self.access_code,
            'notes': self.notes,
        }
    
    def __repr__(self) -> str:
        return f"<ReservationAttendee(id={self.id}, name={self.full_name})>"


class ReservationAddon(Base):
    """
    Add-on services for reservations.
    
    Tracks additional services purchased with the reservation,
    such as EV charging, car wash, valet, etc.
    """
    
    __tablename__ = 'reservation_addons'
    __table_args__ = (
        Index('ix_addons_reservation', 'reservation_id'),
        Index('ix_addons_type', 'addon_type'),
        Index('ix_addons_status', 'status'),
        {'comment': 'Add-on services for reservations'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    reservation_id = Column(
        UUID(as_uuid=True),
        ForeignKey('reservations.id', ondelete='CASCADE'),
        nullable=False
    )
    
    addon_type = Column(
        String(50),
        nullable=False,
        comment='Type of add-on service'
    )
    
    name = Column(
        String(200),
        nullable=False,
        comment='Add-on name'
    )
    
    description = Column(
        Text,
        comment='Add-on description'
    )
    
    quantity = Column(
        Integer,
        nullable=False,
        server_default='1',
        comment='Quantity'
    )
    
    unit_price = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Price per unit'
    )
    
    total_price = Column(
        Numeric(10, 2),
        nullable=False,
        comment='Total price'
    )
    
    tax_amount = Column(
        Numeric(10, 2),
        server_default='0',
        comment='Tax amount'
    )
    
    currency = Column(
        String(3),
        server_default='USD',
        comment='Currency'
    )
    
    scheduled_time = Column(
        DateTime(timezone=True),
        comment='Scheduled time for service'
    )
    
    completed_time = Column(
        DateTime(timezone=True),
        comment='When service was completed'
    )
    
    status = Column(
        String(20),
        server_default='pending',
        comment='Service status'
    )
    
    provider = Column(
        String(200),
        comment='Service provider'
    )
    
    provider_contact = Column(
        String(100),
        comment='Provider contact'
    )
    
    provider_notes = Column(
        Text,
        comment='Notes from provider'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    reservation = relationship('Reservation', back_populates='addon_items')
    
    def complete(self) -> None:
        """Mark add-on as completed."""
        self.status = 'completed'
        self.completed_time = datetime.now()
    
    def cancel(self) -> None:
        """Cancel add-on service."""
        self.status = 'cancelled'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert add-on to dictionary."""
        return {
            'id': str(self.id),
            'reservation_id': str(self.reservation_id),
            'addon_type': self.addon_type,
            'name': self.name,
            'description': self.description,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'total_price': float(self.total_price),
            'tax_amount': float(self.tax_amount) if self.tax_amount else None,
            'currency': self.currency,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'completed_time': self.completed_time.isoformat() if self.completed_time else None,
            'status': self.status,
            'provider': self.provider,
        }
    
    def __repr__(self) -> str:
        return f"<ReservationAddon(id={self.id}, type={self.addon_type}, name={self.name})>"


class ReservationHistory(Base):
    """
    History of changes to reservations.
    
    Tracks all status changes, modifications, and actions performed on reservations
    for audit and compliance purposes.
    """
    
    __tablename__ = 'reservation_history'
    __table_args__ = (
        Index('ix_res_history_reservation', 'reservation_id'),
        Index('ix_res_history_performed_at', 'performed_at'),
        Index('ix_res_history_action', 'action'),
        {'comment': 'Audit history for reservations'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    reservation_id = Column(
        UUID(as_uuid=True),
        ForeignKey('reservations.id', ondelete='CASCADE'),
        nullable=False
    )
    
    action = Column(
        String(50),
        nullable=False,
        comment='Action performed'
    )
    
    previous_status = Column(
        String(20),
        comment='Previous status'
    )
    
    new_status = Column(
        String(20),
        comment='New status'
    )
    
    changes = Column(
        JSONB,
        comment='Detailed changes'
    )
    
    ip_address = Column(
        String(45),
        comment='IP address of actor'
    )
    
    user_agent = Column(
        String(500),
        comment='User agent of actor'
    )
    
    performed_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who performed action'
    )
    
    performed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='When action was performed'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    # Relationships
    reservation = relationship('Reservation', back_populates='history')
    user = relationship('User', foreign_keys=[performed_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert history entry to dictionary."""
        return {
            'id': str(self.id),
            'reservation_id': str(self.reservation_id),
            'action': self.action,
            'previous_status': self.previous_status,
            'new_status': self.new_status,
            'changes': self.changes,
            'performed_by': str(self.performed_by) if self.performed_by else None,
            'performed_at': self.performed_at.isoformat() if self.performed_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ReservationHistory(id={self.id}, action={self.action}, time={self.performed_at})>"


class ReservationFeedback(Base):
    """
    Customer feedback and ratings for reservations.
    
    Collects post-parking feedback, ratings, and reviews from customers.
    """
    
    __tablename__ = 'reservation_feedback'
    __table_args__ = (
        Index('ix_feedback_reservation', 'reservation_id'),
        Index('ix_feedback_user', 'user_id'),
        Index('ix_feedback_rating', 'rating'),
        Index('ix_feedback_created', 'created_at'),
        {'comment': 'Customer feedback for reservations'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    reservation_id = Column(
        UUID(as_uuid=True),
        ForeignKey('reservations.id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL')
    )
    
    rating = Column(
        Integer,
        nullable=False,
        comment='Rating (1-5)'
    )
    
    review_title = Column(
        String(200),
        comment='Review title'
    )
    
    review_text = Column(
        Text,
        comment='Review text'
    )
    
    pros = Column(
        Text,
        comment='What the customer liked'
    )
    
    cons = Column(
        Text,
        comment='What the customer disliked'
    )
    
    would_recommend = Column(
        Boolean,
        comment='Whether customer would recommend'
    )
    
    would_return = Column(
        Boolean,
        comment='Whether customer would return'
    )
    
    categories = Column(
        JSONB,
        comment='Ratings by category'
    )
    
    tags = Column(
        ARRAY(String(50)),
        comment='Feedback tags'
    )
    
    images = Column(
        ARRAY(String(500)),
        comment='Feedback images'
    )
    
    staff_response = Column(
        Text,
        comment='Response from staff'
    )
    
    staff_responded_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='Staff who responded'
    )
    
    staff_responded_at = Column(
        DateTime(timezone=True),
        comment='When staff responded'
    )
    
    is_public = Column(
        Boolean,
        server_default='true',
        comment='Whether feedback is public'
    )
    
    is_verified = Column(
        Boolean,
        server_default='false',
        comment='Whether feedback is verified'
    )
    
    helpful_count = Column(
        Integer,
        server_default='0',
        comment='Number of people who found this helpful'
    )
    
    reported_count = Column(
        Integer,
        server_default='0',
        comment='Number of times reported'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    reservation = relationship('Reservation', back_populates='feedback')
    user = relationship('User')
    staff_responder = relationship('User', foreign_keys=[staff_responded_by])
    
    @validates('rating')
    def validate_rating(self, key, rating):
        """Validate rating is between 1 and 5."""
        if rating < 1 or rating > 5:
            raise ValueError('Rating must be between 1 and 5')
        return rating
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feedback to dictionary."""
        return {
            'id': str(self.id),
            'reservation_id': str(self.reservation_id),
            'user_id': str(self.user_id) if self.user_id else None,
            'rating': self.rating,
            'review_title': self.review_title,
            'review_text': self.review_text,
            'pros': self.pros,
            'cons': self.cons,
            'would_recommend': self.would_recommend,
            'would_return': self.would_return,
            'categories': self.categories,
            'tags': self.tags,
            'images': self.images,
            'staff_response': self.staff_response,
            'staff_responded_at': self.staff_responded_at.isoformat() if self.staff_responded_at else None,
            'is_public': self.is_public,
            'is_verified': self.is_verified,
            'helpful_count': self.helpful_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ReservationFeedback(id={self.id}, rating={self.rating})>"


class ReservationWaitlist(Base):
    """
    Waitlist for unavailable parking spots.
    
    Allows customers to join a waitlist for specific spots, dates, or zones,
    and get notified when availability opens up.
    """
    
    __tablename__ = 'reservation_waitlist'
    __table_args__ = (
        Index('ix_waitlist_user', 'user_id'),
        Index('ix_waitlist_spot', 'spot_id'),
        Index('ix_waitlist_zone', 'zone_id'),
        Index('ix_waitlist_dates', 'start_date', 'end_date'),
        Index('ix_waitlist_status', 'status'),
        {'comment': 'Waitlist for unavailable parking'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        comment='User on waitlist'
    )
    
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='CASCADE'),
        comment='Specific spot requested'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_zones.id', ondelete='CASCADE'),
        comment='Zone requested'
    )
    
    spot_type = Column(
        String(20),
        comment='Type of spot requested'
    )
    
    start_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Desired start date/time'
    )
    
    end_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Desired end date/time'
    )
    
    flexible_dates = Column(
        Boolean,
        server_default='false',
        comment='Whether dates are flexible'
    )
    
    flexible_window_days = Column(
        Integer,
        comment='Flexible window in days'
    )
    
    preferred_times = Column(
        JSONB,
        comment='Preferred times of day'
    )
    
    contact_email = Column(
        String(255),
        nullable=False,
        comment='Contact email'
    )
    
    contact_phone = Column(
        String(20),
        comment='Contact phone'
    )
    
    status = Column(
        String(20),
        server_default='active',
        comment='Waitlist status'
    )
    
    priority = Column(
        Integer,
        server_default='0',
        comment='Priority level'
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        comment='When waitlist entry expires'
    )
    
    notified_at = Column(
        DateTime(timezone=True),
        comment='When user was notified'
    )
    
    converted_reservation_id = Column(
        UUID(as_uuid=True),
        ForeignKey('reservations.id', ondelete='SET NULL'),
        comment='Reservation created from waitlist'
    )
    
    notes = Column(
        Text,
        comment='Additional notes'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    user = relationship('User')
    spot = relationship('ParkingSpot')
    zone = relationship('ParkingZone')
    converted_reservation = relationship('Reservation')
    
    def notify(self) -> None:
        """Mark as notified."""
        self.status = 'notified'
        self.notified_at = datetime.now()
    
    def convert(self, reservation_id: uuid.UUID) -> None:
        """Convert waitlist to reservation."""
        self.status = 'converted'
        self.converted_reservation_id = reservation_id
    
    def expire(self) -> None:
        """Expire waitlist entry."""
        self.status = 'expired'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert waitlist entry to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id) if self.user_id else None,
            'spot_id': str(self.spot_id) if self.spot_id else None,
            'zone_id': str(self.zone_id) if self.zone_id else None,
            'spot_type': self.spot_type,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'flexible_dates': self.flexible_dates,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'status': self.status,
            'priority': self.priority,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'notified_at': self.notified_at.isoformat() if self.notified_at else None,
            'converted_reservation_id': str(self.converted_reservation_id) if self.converted_reservation_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ReservationWaitlist(id={self.id}, user={self.user_id}, status={self.status})>"


class ReservationBlackout(Base):
    """
    Blackout dates when parking is unavailable.
    
    Defines periods when specific spots, zones, or the entire facility
    are unavailable for booking (maintenance, events, holidays, etc.).
    """
    
    __tablename__ = 'reservation_blackout_dates'
    __table_args__ = (
        Index('ix_blackout_spot', 'spot_id'),
        Index('ix_blackout_zone', 'zone_id'),
        Index('ix_blackout_dates', 'start_date', 'end_date'),
        {'comment': 'Blackout dates for parking'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    spot_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_spots.id', ondelete='CASCADE'),
        comment='Specific spot affected'
    )
    
    zone_id = Column(
        UUID(as_uuid=True),
        ForeignKey('parking_zones.id', ondelete='CASCADE'),
        comment='Zone affected'
    )
    
    reason = Column(
        String(200),
        nullable=False,
        comment='Reason for blackout'
    )
    
    description = Column(
        Text,
        comment='Detailed description'
    )
    
    start_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Blackout start'
    )
    
    end_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Blackout end'
    )
    
    is_recurring = Column(
        Boolean,
        server_default='false',
        comment='Whether blackout recurs'
    )
    
    recurring_pattern = Column(
        JSONB,
        comment='Recurrence pattern'
    )
    
    affects_reservations = Column(
        Boolean,
        server_default='true',
        comment='Whether this affects existing reservations'
    )
    
    affected_reservations = Column(
        JSONB,
        comment='IDs of affected reservations'
    )
    
    notification_sent = Column(
        Boolean,
        server_default='false',
        comment='Whether notifications were sent'
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created blackout'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    spot = relationship('ParkingSpot')
    zone = relationship('ParkingZone')
    creator = relationship('User', foreign_keys=[created_by])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert blackout entry to dictionary."""
        return {
            'id': str(self.id),
            'spot_id': str(self.spot_id) if self.spot_id else None,
            'zone_id': str(self.zone_id) if self.zone_id else None,
            'reason': self.reason,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_recurring': self.is_recurring,
            'recurring_pattern': self.recurring_pattern,
            'affects_reservations': self.affects_reservations,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<ReservationBlackout(id={self.id}, reason={self.reason})>"


# =========================================================================
# EVENT LISTENERS
# =========================================================================

@event.listens_for(Reservation, 'before_insert')
def reservation_before_insert(mapper, connection, target):
    """
    Generate reservation number and QR code for new reservations.
    """
    if not target.reservation_number:
        # Generate reservation number: RES-YYYYMMDD-XXXXXX
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Get next sequence number
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(reservation_number FROM 15)::INTEGER), 0) + 1
                FROM reservations
                WHERE reservation_number LIKE :pattern
            """),
            {'pattern': f'RES-{date_str}-%'}
        )
        seq_num = result.scalar()
        
        target.reservation_number = f"RES-{date_str}-{seq_num:06d}"
    
    if not target.qr_code:
        target.generate_qr_code()


@event.listens_for(Reservation, 'before_update')
def reservation_before_update(mapper, connection, target):
    """
    Track modifications and update timestamps.
    """
    # Get changed fields
    state = object_session(target).get_changes(target)
    
    if state and 'status' not in state:
        # Non-status change counts as modification
        target.modified_count += 1
        target.last_modified_at = datetime.now()


@event.listens_for(Reservation, 'after_insert')
@event.listens_for(Reservation, 'after_update')
def reservation_after_save(mapper, connection, target):
    """
    Update spot status when reservation status changes.
    """
    if target.spot:
        if target.status == 'confirmed' and target.spot.status == 'available':
            connection.execute(
                text("""
                    UPDATE parking_spots
                    SET status = 'reserved',
                        current_reservation_id = :reservation_id,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :spot_id
                """),
                {'spot_id': target.spot_id, 'reservation_id': target.id}
            )
        elif target.status in ['cancelled', 'completed', 'no_show', 'expired']:
            if target.spot.current_reservation_id == target.id:
                connection.execute(
                    text("""
                        UPDATE parking_spots
                        SET status = 'available',
                            current_reservation_id = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :spot_id
                    """),
                    {'spot_id': target.spot_id}
                )


# =========================================================================
# FACTORY FUNCTIONS
# =========================================================================

def create_reservation(
    spot_id: uuid.UUID,
    start_time: datetime,
    end_time: datetime,
    user_id: Optional[uuid.UUID] = None,
    vehicle_id: Optional[uuid.UUID] = None,
    guest_info: Optional[Dict[str, Any]] = None,
    reservation_type: str = 'standard',
    **kwargs
) -> Reservation:
    """
    Factory function to create a new reservation.
    
    Args:
        spot_id: ID of parking spot
        start_time: Start time
        end_time: End time
        user_id: ID of user (if registered)
        vehicle_id: ID of vehicle (if registered)
        guest_info: Guest information dict (for guest bookings)
        reservation_type: Type of reservation
        **kwargs: Additional reservation attributes
        
    Returns:
        New Reservation instance
    """
    reservation = Reservation(
        spot_id=spot_id,
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        vehicle_id=vehicle_id,
        reservation_type=reservation_type,
        **kwargs
    )
    
    if guest_info and not user_id:
        reservation.is_guest = True
        reservation.guest_first_name = guest_info.get('first_name')
        reservation.guest_last_name = guest_info.get('last_name')
        reservation.guest_email = guest_info.get('email')
        reservation.guest_phone = guest_info.get('phone')
        reservation.guest_company = guest_info.get('company')
    
    # Calculate initial price
    from models.parking_spot import ParkingSpot
    spot = object_session(reservation).get(ParkingSpot, spot_id)
    if spot:
        cost = spot.calculate_parking_cost(
            start_time, end_time,
            kwargs.get('vehicle_type')
        )
        reservation.base_amount = cost['base_amount']
        reservation.tax_amount = cost['tax_amount']
        reservation.total_amount = cost['total_amount']
        reservation.rate_id = uuid.UUID(cost['rate_id']) if cost['rate_id'] else None
    
    return reservation


# =========================================================================
# EXPORTS
# =========================================================================

__all__ = [
    'Reservation',
    'ReservationAttendee',
    'ReservationAddon',
    'ReservationHistory',
    'ReservationFeedback',
    'ReservationWaitlist',
    'ReservationBlackout',
    'ReservationStatus',
    'ReservationType',
    'PaymentStatus',
    'RecurringFrequency',
    'WaitlistStatus',
    'create_reservation',
]