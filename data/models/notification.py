# parking-management/data/migrations/models/notification.py

"""
Notification model for parking management system.

This module defines the Notification model and related classes for managing
all types of notifications including email, SMS, push notifications, and webhooks,
with comprehensive delivery tracking, templates, user preferences, and campaign management.
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
import hashlib
import hmac
from datetime import datetime, date, timedelta
import logging
from typing import Optional, List, Dict, Any, Tuple
import jinja2
from jinja2 import Template, TemplateError

# Configure logging
logger = logging.getLogger(__name__)

# Create base class
Base = declarative_base()


class NotificationType(str, enum.Enum):
    """Enum for notification types."""
    # Reservation notifications
    RESERVATION_CONFIRMATION = 'reservation_confirmation'
    RESERVATION_REMINDER = 'reservation_reminder'
    RESERVATION_MODIFICATION = 'reservation_modification'
    RESERVATION_CANCELLATION = 'reservation_cancellation'
    
    # Check-in/out notifications
    CHECK_IN_SUCCESS = 'check_in_success'
    CHECK_OUT_SUCCESS = 'check_out_success'
    CHECK_IN_REMINDER = 'check_in_reminder'
    CHECK_OUT_REMINDER = 'check_out_reminder'
    
    # Payment notifications
    PAYMENT_RECEIPT = 'payment_receipt'
    PAYMENT_FAILED = 'payment_failed'
    PAYMENT_REFUNDED = 'payment_refunded'
    PAYMENT_DUE = 'payment_due'
    
    # Violation notifications
    VIOLATION_ISSUED = 'violation_issued'
    VIOLATION_PAID = 'violation_paid'
    VIOLATION_REMINDER = 'violation_reminder'
    
    # Vehicle notifications
    VEHICLE_ALERT = 'vehicle_alert'
    VEHICLE_BLACKLISTED = 'vehicle_blacklisted'
    VEHICLE_STOLEN = 'vehicle_stolen'
    
    # Subscription notifications
    SUBSCRIPTION_CREATED = 'subscription_created'
    SUBSCRIPTION_RENEWED = 'subscription_renewed'
    SUBSCRIPTION_EXPIRING = 'subscription_expiring'
    SUBSCRIPTION_CANCELLED = 'subscription_cancelled'
    SUBSCRIPTION_PAYMENT_FAILED = 'subscription_payment_failed'
    
    # Account notifications
    ACCOUNT_CREATED = 'account_created'
    PASSWORD_RESET = 'password_reset'
    EMAIL_VERIFICATION = 'email_verification'
    PHONE_VERIFICATION = 'phone_verification'
    ACCOUNT_LOCKED = 'account_locked'
    ACCOUNT_UNLOCKED = 'account_unlocked'
    
    # Security notifications
    SECURITY_ALERT = 'security_alert'
    LOGIN_NEW_DEVICE = 'login_new_device'
    LOGIN_FAILED = 'login_failed'
    TWO_FACTOR_DISABLED = 'two_factor_disabled'
    
    # Marketing notifications
    PROMOTIONAL = 'promotional'
    NEWSLETTER = 'newsletter'
    SURVEY = 'survey'
    FEEDBACK_REQUEST = 'feedback_request'
    
    # System notifications
    SYSTEM_ALERT = 'system_alert'
    MAINTENANCE_ALERT = 'maintenance_alert'
    POLICY_UPDATE = 'policy_update'
    
    # Waitlist notifications
    WAITLIST_CONFIRMED = 'waitlist_confirmed'
    SPOT_AVAILABLE = 'spot_available'
    
    # Rate notifications
    RATE_CHANGE = 'rate_change'
    SPECIAL_OFFER = 'special_offer'


class NotificationChannel(str, enum.Enum):
    """Enum for notification channels."""
    EMAIL = 'email'
    SMS = 'sms'
    PUSH = 'push'
    WHATSAPP = 'whatsapp'
    TELEGRAM = 'telegram'
    SLACK = 'slack'
    WEBHOOK = 'webhook'
    IN_APP = 'in_app'
    VOICE = 'voice'
    FAX = 'fax'


class NotificationStatus(str, enum.Enum):
    """Enum for notification status."""
    PENDING = 'pending'
    QUEUED = 'queued'
    PROCESSING = 'processing'
    SENT = 'sent'
    DELIVERED = 'delivered'
    FAILED = 'failed'
    BOUNCED = 'bounced'
    OPENED = 'opened'
    CLICKED = 'clicked'
    UNSUBSCRIBED = 'unsubscribed'
    SUPPRESSED = 'suppressed'
    EXPIRED = 'expired'
    CANCELLED = 'cancelled'


class NotificationPriority(str, enum.Enum):
    """Enum for notification priority."""
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    URGENT = 'urgent'
    CRITICAL = 'critical'


class TemplateType(str, enum.Enum):
    """Enum for template types."""
    EMAIL_HTML = 'email_html'
    EMAIL_TEXT = 'email_text'
    SMS_TEXT = 'sms_text'
    PUSH_NOTIFICATION = 'push_notification'
    WHATSAPP_TEXT = 'whatsapp_text'
    IN_APP = 'in_app'


class DeviceType(str, enum.Enum):
    """Enum for device types."""
    IOS = 'ios'
    ANDROID = 'android'
    WEB = 'web'
    DESKTOP = 'desktop'
    TABLET = 'tablet'


class SubscriptionTier(str, enum.Enum):
    """Enum for subscription tiers."""
    FREE = 'free'
    BASIC = 'basic'
    PREMIUM = 'premium'
    ENTERPRISE = 'enterprise'


class CampaignStatus(str, enum.Enum):
    """Enum for campaign status."""
    DRAFT = 'draft'
    SCHEDULED = 'scheduled'
    SENDING = 'sending'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    ARCHIVED = 'archived'


class WebhookMethod(str, enum.Enum):
    """Enum for webhook HTTP methods."""
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'


class Frequency(str, enum.Enum):
    """Enum for notification frequency."""
    IMMEDIATE = 'immediate'
    DAILY_DIGEST = 'daily_digest'
    WEEKLY_DIGEST = 'weekly_digest'
    MONTHLY_DIGEST = 'monthly_digest'
    NEVER = 'never'


class SuppressionReason(str, enum.Enum):
    """Enum for suppression reasons."""
    UNSUBSCRIBED = 'unsubscribed'
    BOUNCED = 'bounced'
    COMPLAINED = 'complained'
    INVALID = 'invalid'
    OPTED_OUT = 'opted_out'
    USER_DELETED = 'user_deleted'


class NotificationTemplate(Base):
    """
    Templates for different notification types.
    
    Stores reusable templates with variable substitution support
    for different channels and notification types.
    """
    
    __tablename__ = 'notification_templates'
    __table_args__ = (
        Index('ix_notification_templates_code', 'code', unique=True),
        Index('ix_notification_templates_type', 'notification_type'),
        Index('ix_notification_templates_channel', 'channel'),
        Index('ix_notification_templates_active', 'is_active'),
        {'comment': 'Notification templates'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    # =========================================================================
    # BASIC INFORMATION
    # =========================================================================
    code = Column(
        String(100),
        nullable=False,
        unique=True,
        comment='Unique template code (e.g., reservation_confirmation_email)'
    )
    
    name = Column(
        String(255),
        nullable=False,
        comment='Template name'
    )
    
    description = Column(
        Text,
        comment='Template description'
    )
    
    notification_type = Column(
        String(50),
        nullable=False,
        comment='Type of notification this template is for'
    )
    
    channel = Column(
        String(50),
        nullable=False,
        comment='Channel this template is for'
    )
    
    template_type = Column(
        String(50),
        nullable=False,
        comment='Type of template'
    )
    
    # =========================================================================
    # TEMPLATE CONTENT
    # =========================================================================
    subject = Column(
        String(255),
        comment='Subject line (for email, push title)'
    )
    
    preheader = Column(
        String(255),
        comment='Email preheader text'
    )
    
    content_html = Column(
        Text,
        comment='HTML content (for email)'
    )
    
    content_text = Column(
        Text,
        comment='Plain text content'
    )
    
    content_json = Column(
        JSONB,
        comment='JSON content (for push notifications)'
    )
    
    template_data = Column(
        JSONB,
        server_default='{}',
        comment='Default template data'
    )
    
    # =========================================================================
    # TEMPLATE VARIABLES
    # =========================================================================
    variables = Column(
        ARRAY(String(100)),
        comment='List of variables used in template'
    )
    
    required_variables = Column(
        ARRAY(String(100)),
        comment='Required variables that must be provided'
    )
    
    # =========================================================================
    # DESIGN AND PREVIEW
    # =========================================================================
    design = Column(
        JSONB,
        comment='Visual editor design data'
    )
    
    thumbnail_url = Column(
        String(500),
        comment='URL to template thumbnail'
    )
    
    preview_url = Column(
        String(500),
        comment='URL to template preview'
    )
    
    # =========================================================================
    # LOCALIZATION
    # =========================================================================
    locale = Column(
        String(10),
        server_default='en',
        comment='Locale (language/region)'
    )
    
    translations = Column(
        JSONB,
        comment='Translations for different locales'
    )
    
    # =========================================================================
    # VERSIONING
    # =========================================================================
    version = Column(
        Integer,
        nullable=False,
        server_default='1',
        comment='Template version'
    )
    
    is_draft = Column(
        Boolean,
        server_default='true',
        comment='Whether this is a draft version'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether template is active'
    )
    
    is_system = Column(
        Boolean,
        server_default='false',
        comment='Whether template is system-defined'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
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
        comment='User who created this template'
    )
    
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who last updated this template'
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        comment='Soft delete timestamp'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    creator = relationship('User', foreign_keys=[created_by])
    updater = relationship('User', foreign_keys=[updated_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def render(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render template with given context.
        
        Args:
            context: Dictionary of variables to substitute
            
        Returns:
            Rendered content dictionary
            
        Raises:
            ValueError: If required variables are missing
            TemplateError: If template rendering fails
        """
        # Check required variables
        if self.required_variables:
            missing = [v for v in self.required_variables if v not in context]
            if missing:
                raise ValueError(f"Missing required variables: {missing}")
        
        # Merge default data with context
        data = {**self.template_data, **context} if self.template_data else context
        
        result = {}
        
        # Render subject if present
        if self.subject:
            try:
                template = Template(self.subject)
                result['subject'] = template.render(**data)
            except TemplateError as e:
                logger.error(f"Error rendering subject: {e}")
                result['subject'] = self.subject
        
        # Render preheader if present
        if self.preheader:
            try:
                template = Template(self.preheader)
                result['preheader'] = template.render(**data)
            except TemplateError as e:
                logger.error(f"Error rendering preheader: {e}")
                result['preheader'] = self.preheader
        
        # Render HTML content
        if self.content_html:
            try:
                template = Template(self.content_html)
                result['content_html'] = template.render(**data)
            except TemplateError as e:
                logger.error(f"Error rendering HTML: {e}")
                result['content_html'] = self.content_html
        
        # Render text content
        if self.content_text:
            try:
                template = Template(self.content_text)
                result['content_text'] = template.render(**data)
            except TemplateError as e:
                logger.error(f"Error rendering text: {e}")
                result['content_text'] = self.content_text
        
        # Process JSON content
        if self.content_json:
            try:
                # For JSON, we need to stringify and then parse after rendering
                json_str = json.dumps(self.content_json)
                template = Template(json_str)
                rendered = template.render(**data)
                result['content_json'] = json.loads(rendered)
            except (TemplateError, json.JSONDecodeError) as e:
                logger.error(f"Error rendering JSON: {e}")
                result['content_json'] = self.content_json
        
        return result
    
    def create_version(self) -> 'NotificationTemplate':
        """
        Create a new version of this template.
        
        Returns:
            New template instance (draft)
        """
        new_template = NotificationTemplate(
            code=self.code,
            name=self.name,
            description=self.description,
            notification_type=self.notification_type,
            channel=self.channel,
            template_type=self.template_type,
            subject=self.subject,
            preheader=self.preheader,
            content_html=self.content_html,
            content_text=self.content_text,
            content_json=self.content_json,
            template_data=self.template_data,
            variables=self.variables,
            required_variables=self.required_variables,
            design=self.design,
            locale=self.locale,
            translations=self.translations,
            version=self.version + 1,
            is_draft=True,
            is_active=False,
            is_system=self.is_system,
            metadata=self.metadata,
            created_by=self.created_by
        )
        
        return new_template
    
    def publish(self) -> None:
        """Publish draft template."""
        if self.is_draft:
            # Deactivate previous active version
            object_session(self).query(NotificationTemplate).filter(
                NotificationTemplate.code == self.code,
                NotificationTemplate.is_active == True
            ).update({'is_active': False})
            
            self.is_draft = False
            self.is_active = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'notification_type': self.notification_type,
            'channel': self.channel,
            'template_type': self.template_type,
            'subject': self.subject,
            'preheader': self.preheader,
            'variables': self.variables,
            'required_variables': self.required_variables,
            'locale': self.locale,
            'version': self.version,
            'is_draft': self.is_draft,
            'is_active': self.is_active,
            'is_system': self.is_system,
            'thumbnail_url': self.thumbnail_url,
            'preview_url': self.preview_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationTemplate(id={self.id}, code={self.code}, version={self.version})>"


class NotificationDevice(Base):
    """
    Registered devices for push notifications.
    
    Tracks user devices for push notification delivery with platform-specific tokens.
    """
    
    __tablename__ = 'notification_devices'
    __table_args__ = (
        Index('ix_notification_devices_user', 'user_id'),
        Index('ix_notification_devices_token', 'device_token'),
        Index('ix_notification_devices_active', 'is_active'),
        Index('ix_notification_devices_last_active', 'last_active_at'),
        UniqueConstraint('user_id', 'device_token', name='uq_user_device_token'),
        {'comment': 'Push notification devices'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    # =========================================================================
    # USER RELATIONSHIP
    # =========================================================================
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the user'
    )
    
    # =========================================================================
    # DEVICE INFORMATION
    # =========================================================================
    device_type = Column(
        String(20),
        nullable=False,
        comment='Type of device (ios, android, web, desktop, tablet)'
    )
    
    device_token = Column(
        String(500),
        nullable=False,
        comment='Device token for push notifications'
    )
    
    device_name = Column(
        String(255),
        comment='Device name (e.g., "John\'s iPhone")'
    )
    
    device_model = Column(
        String(100),
        comment='Device model (e.g., iPhone 13 Pro)'
    )
    
    os_version = Column(
        String(50),
        comment='Operating system version'
    )
    
    app_version = Column(
        String(50),
        comment='App version'
    )
    
    # =========================================================================
    # PROVIDER TOKENS
    # =========================================================================
    push_token = Column(
        String(500),
        comment='Push notification token'
    )
    
    voip_token = Column(
        String(500),
        comment='VoIP token for VoIP pushes'
    )
    
    arn_endpoint = Column(
        String(500),
        comment='AWS ARN endpoint'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether device is active'
    )
    
    is_verified = Column(
        Boolean,
        server_default='false',
        comment='Whether device is verified'
    )
    
    verified_at = Column(
        DateTime(timezone=True),
        comment='When device was verified'
    )
    
    last_active_at = Column(
        DateTime(timezone=True),
        comment='Last time device was active'
    )
    
    last_notification_at = Column(
        DateTime(timezone=True),
        comment='Last notification sent to this device'
    )
    
    failed_attempts = Column(
        Integer,
        server_default='0',
        comment='Number of failed delivery attempts'
    )
    
    last_error = Column(
        Text,
        comment='Last error message'
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
    
    deleted_at = Column(
        DateTime(timezone=True),
        comment='Soft delete timestamp'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship('User', back_populates='notification_devices')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def mark_active(self) -> None:
        """Mark device as active."""
        self.is_active = True
        self.last_active_at = datetime.now()
        self.failed_attempts = 0
    
    def mark_inactive(self, reason: Optional[str] = None) -> None:
        """Mark device as inactive."""
        self.is_active = False
        if reason:
            self.last_error = reason
    
    def record_failure(self, error: str) -> None:
        """Record a delivery failure."""
        self.failed_attempts += 1
        self.last_error = error
        
        # Deactivate after too many failures
        if self.failed_attempts >= 10:
            self.is_active = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert device to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'device_type': self.device_type,
            'device_name': self.device_name,
            'device_model': self.device_model,
            'os_version': self.os_version,
            'app_version': self.app_version,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_active_at': self.last_active_at.isoformat() if self.last_active_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationDevice(id={self.id}, user={self.user_id}, type={self.device_type})>"


class NotificationPreference(Base):
    """
    User preferences for notification delivery.
    
    Stores per-user, per-channel, per-type preferences for notifications.
    """
    
    __tablename__ = 'notification_preferences'
    __table_args__ = (
        Index('ix_notification_prefs_user', 'user_id'),
        Index('ix_notification_prefs_type', 'notification_type'),
        Index('ix_notification_prefs_enabled', 'enabled'),
        UniqueConstraint('user_id', 'notification_type', 'channel', name='uq_user_notification_channel'),
        {'comment': 'User notification preferences'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    # =========================================================================
    # USER RELATIONSHIP
    # =========================================================================
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the user'
    )
    
    # =========================================================================
    # PREFERENCE TARGET
    # =========================================================================
    notification_type = Column(
        String(50),
        nullable=False,
        comment='Type of notification'
    )
    
    channel = Column(
        String(50),
        nullable=False,
        comment='Notification channel'
    )
    
    # =========================================================================
    # PREFERENCE SETTINGS
    # =========================================================================
    enabled = Column(
        Boolean,
        nullable=False,
        server_default='true',
        comment='Whether notifications are enabled'
    )
    
    frequency = Column(
        String(20),
        server_default='immediate',
        comment='Delivery frequency'
    )
    
    quiet_hours_start = Column(
        Time,
        comment='Quiet hours start time'
    )
    
    quiet_hours_end = Column(
        Time,
        comment='Quiet hours end time'
    )
    
    quiet_hours_timezone = Column(
        String(50),
        comment='Timezone for quiet hours'
    )
    
    max_per_day = Column(
        Integer,
        comment='Maximum notifications per day'
    )
    
    max_per_week = Column(
        Integer,
        comment='Maximum notifications per week'
    )
    
    # =========================================================================
    # USAGE TRACKING
    # =========================================================================
    last_sent_at = Column(
        DateTime(timezone=True),
        comment='Last time a notification was sent'
    )
    
    last_sent_count = Column(
        Integer,
        server_default='0',
        comment='Count for current period'
    )
    
    reset_date = Column(
        Date,
        comment='Date when counters reset'
    )
    
    # =========================================================================
    # OVERRIDE ADDRESSES
    # =========================================================================
    email_override = Column(
        String(255),
        comment='Override email address'
    )
    
    phone_override = Column(
        String(20),
        comment='Override phone number'
    )
    
    push_device_ids = Column(
        ARRAY(UUID(as_uuid=True)),
        comment='Specific devices for push notifications'
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
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship('User', back_populates='notification_prefs')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def can_send_now(self) -> bool:
        """
        Check if a notification can be sent now based on preferences.
        
        Returns:
            True if notification can be sent
        """
        now = datetime.now()
        current_time = now.time()
        
        # Check quiet hours
        if self.quiet_hours_start and self.quiet_hours_end:
            if self.quiet_hours_start <= self.quiet_hours_end:
                # Normal hours (e.g., 22:00-06:00)
                if self.quiet_hours_start <= current_time <= self.quiet_hours_end:
                    return False
            else:
                # Overnight hours
                if current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end:
                    return False
        
        # Check daily limit
        if self.max_per_day and self.last_sent_count >= self.max_per_day:
            if self.reset_date and self.reset_date == now.date():
                return False
            # Reset if new day
            if self.reset_date and self.reset_date < now.date():
                self.last_sent_count = 0
                self.reset_date = now.date()
        
        return True
    
    def record_sent(self) -> None:
        """Record that a notification was sent."""
        now = datetime.now()
        self.last_sent_at = now
        self.last_sent_count += 1
        
        if not self.reset_date or self.reset_date < now.date():
            self.reset_date = now.date()
            self.last_sent_count = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preference to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'notification_type': self.notification_type,
            'channel': self.channel,
            'enabled': self.enabled,
            'frequency': self.frequency,
            'quiet_hours': {
                'start': self.quiet_hours_start.isoformat() if self.quiet_hours_start else None,
                'end': self.quiet_hours_end.isoformat() if self.quiet_hours_end else None,
                'timezone': self.quiet_hours_timezone,
            } if self.quiet_hours_start else None,
            'limits': {
                'max_per_day': self.max_per_day,
                'max_per_week': self.max_per_week,
            },
            'overrides': {
                'email': self.email_override,
                'phone': self.phone_override,
            } if self.email_override or self.phone_override else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationPreference(id={self.id}, user={self.user_id}, type={self.notification_type})>"


class Notification(Base):
    """
    Main notifications table tracking all outgoing notifications.
    
    Comprehensive tracking of all notifications sent through the system,
    including delivery status, engagement metrics, and provider details.
    """
    
    __tablename__ = 'notifications'
    __table_args__ = (
        # Primary indexes
        Index('ix_notifications_number', 'notification_number', unique=True),
        Index('ix_notifications_external_id', 'external_id', unique=True),
        Index('ix_notifications_tracking_id', 'tracking_id'),
        
        # Foreign key indexes
        Index('ix_notifications_user_id', 'user_id'),
        Index('ix_notifications_recipient_device_id', 'recipient_device_id'),
        Index('ix_notifications_template_id', 'template_id'),
        Index('ix_notifications_reservation_id', 'reservation_id'),
        Index('ix_notifications_payment_id', 'payment_id'),
        Index('ix_notifications_vehicle_id', 'vehicle_id'),
        Index('ix_notifications_campaign_id', 'campaign_id'),
        Index('ix_notifications_batch_id', 'batch_id'),
        
        # Recipient indexes
        Index('ix_notifications_recipient_email', 'recipient_email'),
        Index('ix_notifications_recipient_phone', 'recipient_phone'),
        
        # Status indexes
        Index('ix_notifications_status', 'status'),
        Index('ix_notifications_type', 'notification_type'),
        Index('ix_notifications_channel', 'channel'),
        Index('ix_notifications_priority', 'priority'),
        
        # Time-based indexes
        Index('ix_notifications_created_at', 'created_at'),
        Index('ix_notifications_sent_at', 'sent_at'),
        Index('ix_notifications_delivered_at', 'delivered_at'),
        Index('ix_notifications_opened_at', 'opened_at'),
        Index('ix_notifications_clicked_at', 'clicked_at'),
        
        # Provider indexes
        Index('ix_notifications_provider', 'provider'),
        Index('ix_notifications_provider_message_id', 'provider_message_id'),
        
        # Composite indexes for common queries
        Index('ix_notifications_user_channel', 'user_id', 'channel', 'created_at'),
        Index('ix_notifications_recipient_email_created', 'recipient_email', 'created_at'),
        Index('ix_notifications_recipient_phone_created', 'recipient_phone', 'created_at'),
        Index('ix_notifications_status_type', 'status', 'notification_type'),
        
        # Partial indexes
        Index('ix_notifications_pending', 'status', 'priority', 'created_at',
              postgresql_where=text("status = 'pending'")),
        Index('ix_notifications_failed', 'status', 'retry_count', 'next_retry_at',
              postgresql_where=text("status = 'failed'")),
        Index('ix_notifications_opened', 'opened_at',
              postgresql_where=text("opened_at IS NOT NULL")),
        Index('ix_notifications_clicked', 'clicked_at',
              postgresql_where=text("clicked_at IS NOT NULL")),
        
        # Check constraints
        CheckConstraint(
            "status IN ('pending', 'queued', 'processing', 'sent', 'delivered', 'failed', "
            "'bounced', 'opened', 'clicked', 'unsubscribed', 'suppressed', 'expired', 'cancelled')",
            name='ck_notifications_status'
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent', 'critical')",
            name='ck_notifications_priority'
        ),
        CheckConstraint(
            "channel IN ('email', 'sms', 'push', 'whatsapp', 'telegram', 'slack', 'webhook', 'in_app', 'voice', 'fax')",
            name='ck_notifications_channel'
        ),
        
        # Table comment
        {'comment': 'Main notifications table tracking all outgoing notifications'}
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
    
    notification_number = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Unique human-readable notification number'
    )
    
    external_id = Column(
        String(255),
        unique=True,
        comment='External ID from provider'
    )
    
    # =========================================================================
    # RECIPIENT
    # =========================================================================
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='ID of recipient user (if registered)'
    )
    
    recipient_email = Column(
        String(255),
        comment='Recipient email address'
    )
    
    recipient_phone = Column(
        String(20),
        comment='Recipient phone number'
    )
    
    recipient_device_id = Column(
        UUID(as_uuid=True),
        ForeignKey('notification_devices.id', ondelete='SET NULL'),
        comment='ID of recipient device'
    )
    
    recipient_push_token = Column(
        String(500),
        comment='Push token for this specific notification'
    )
    
    # =========================================================================
    # CONTENT
    # =========================================================================
    notification_type = Column(
        String(50),
        nullable=False,
        comment='Type of notification'
    )
    
    channel = Column(
        String(50),
        nullable=False,
        comment='Delivery channel'
    )
    
    priority = Column(
        String(20),
        nullable=False,
        server_default='normal',
        comment='Notification priority'
    )
    
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey('notification_templates.id', ondelete='SET NULL'),
        comment='ID of template used'
    )
    
    template_data = Column(
        JSONB,
        comment='Data used to render template'
    )
    
    subject = Column(
        String(255),
        comment='Notification subject/title'
    )
    
    preheader = Column(
        String(255),
        comment='Email preheader'
    )
    
    content_html = Column(
        Text,
        comment='HTML content'
    )
    
    content_text = Column(
        Text,
        comment='Plain text content'
    )
    
    content_json = Column(
        JSONB,
        comment='JSON content (for push)'
    )
    
    # =========================================================================
    # RELATED ENTITIES
    # =========================================================================
    reservation_id = Column(
        UUID(as_uuid=True),
        ForeignKey('reservations.id', ondelete='SET NULL'),
        comment='Associated reservation'
    )
    
    payment_id = Column(
        UUID(as_uuid=True),
        ForeignKey('payments.id', ondelete='SET NULL'),
        comment='Associated payment'
    )
    
    vehicle_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicles.id', ondelete='SET NULL'),
        comment='Associated vehicle'
    )
    
    violation_id = Column(
        UUID(as_uuid=True),
        ForeignKey('vehicle_violations.id', ondelete='SET NULL'),
        comment='Associated violation'
    )
    
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey('notification_campaigns.id', ondelete='SET NULL'),
        comment='Associated campaign'
    )
    
    # =========================================================================
    # STATUS TRACKING
    # =========================================================================
    status = Column(
        String(20),
        nullable=False,
        server_default='pending',
        comment='Current notification status'
    )
    
    status_history = Column(
        JSONB,
        comment='History of status changes'
    )
    
    queued_at = Column(
        DateTime(timezone=True),
        comment='When notification was queued'
    )
    
    sent_at = Column(
        DateTime(timezone=True),
        comment='When notification was sent'
    )
    
    delivered_at = Column(
        DateTime(timezone=True),
        comment='When notification was delivered'
    )
    
    opened_at = Column(
        DateTime(timezone=True),
        comment='When notification was opened'
    )
    
    clicked_at = Column(
        DateTime(timezone=True),
        comment='When link was clicked'
    )
    
    failed_at = Column(
        DateTime(timezone=True),
        comment='When notification failed'
    )
    
    failure_reason = Column(
        Text,
        comment='Reason for failure'
    )
    
    failure_code = Column(
        String(100),
        comment='Failure code from provider'
    )
    
    # =========================================================================
    # RETRY LOGIC
    # =========================================================================
    retry_count = Column(
        Integer,
        server_default='0',
        comment='Number of retry attempts'
    )
    
    max_retries = Column(
        Integer,
        server_default='3',
        comment='Maximum retry attempts'
    )
    
    next_retry_at = Column(
        DateTime(timezone=True),
        comment='When to next retry'
    )
    
    # =========================================================================
    # PROVIDER DETAILS
    # =========================================================================
    provider = Column(
        String(50),
        comment='Provider used (aws_ses, twilio, firebase, etc.)'
    )
    
    provider_message_id = Column(
        String(255),
        comment='Provider message ID'
    )
    
    provider_response = Column(
        JSONB,
        comment='Full provider response'
    )
    
    provider_cost = Column(
        Numeric(10, 6),
        comment='Cost of sending (if applicable)'
    )
    
    # =========================================================================
    # TRACKING
    # =========================================================================
    tracking_id = Column(
        String(100),
        comment='Unique tracking ID for open/click tracking'
    )
    
    ip_address = Column(
        String(45),
        comment='IP address of recipient when opened'
    )
    
    user_agent = Column(
        String(500),
        comment='User agent when opened'
    )
    
    referrer = Column(
        String(500),
        comment='Referrer when clicked'
    )
    
    # =========================================================================
    # BATCH INFO
    # =========================================================================
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey('notification_batches.id', ondelete='SET NULL'),
        comment='ID of batch this notification belongs to'
    )
    
    batch_sequence = Column(
        Integer,
        comment='Sequence number within batch'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
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
        comment='User who created this notification'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='notifications',
        comment='Recipient user'
    )
    
    recipient_device = relationship(
        'NotificationDevice',
        foreign_keys=[recipient_device_id],
        comment='Recipient device'
    )
    
    template = relationship(
        'NotificationTemplate',
        foreign_keys=[template_id],
        comment='Template used'
    )
    
    reservation = relationship(
        'Reservation',
        foreign_keys=[reservation_id],
        comment='Associated reservation'
    )
    
    payment = relationship(
        'Payment',
        foreign_keys=[payment_id],
        comment='Associated payment'
    )
    
    vehicle = relationship(
        'Vehicle',
        foreign_keys=[vehicle_id],
        comment='Associated vehicle'
    )
    
    campaign = relationship(
        'NotificationCampaign',
        foreign_keys=[campaign_id],
        back_populates='notifications',
        comment='Associated campaign'
    )
    
    batch = relationship(
        'NotificationBatch',
        foreign_keys=[batch_id],
        back_populates='notifications',
        comment='Associated batch'
    )
    
    logs = relationship(
        'NotificationLog',
        back_populates='notification',
        cascade='all, delete-orphan',
        comment='Delivery logs'
    )
    
    attachments = relationship(
        'NotificationAttachment',
        back_populates='notification',
        cascade='all, delete-orphan',
        comment='Attachments'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def is_delivered(self) -> bool:
        """Check if notification was delivered."""
        return self.status == 'delivered'
    
    @hybrid_property
    def is_opened(self) -> bool:
        """Check if notification was opened."""
        return self.status == 'opened'
    
    @hybrid_property
    def is_clicked(self) -> bool:
        """Check if notification was clicked."""
        return self.status == 'clicked'
    
    @hybrid_property
    def is_failed(self) -> bool:
        """Check if notification failed."""
        return self.status == 'failed'
    
    @hybrid_property
    def delivery_time_seconds(self) -> Optional[int]:
        """Get time from sent to delivered in seconds."""
        if self.sent_at and self.delivered_at:
            delta = self.delivered_at - self.sent_at
            return int(delta.total_seconds())
        return None
    
    @hybrid_property
    def open_time_seconds(self) -> Optional[int]:
        """Get time from delivered to opened in seconds."""
        if self.delivered_at and self.opened_at:
            delta = self.opened_at - self.delivered_at
            return int(delta.total_seconds())
        return None
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @validates('recipient_email')
    def validate_email(self, key, email):
        """Validate email format."""
        if email and self.channel == 'email':
            import re
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                raise ValueError('Invalid email format')
        return email
    
    @validates('recipient_phone')
    def validate_phone(self, key, phone):
        """Validate phone number format."""
        if phone and self.channel in ['sms', 'whatsapp', 'voice']:
            import re
            if not re.match(r'^\+?[1-9]\d{1,14}$', phone):
                raise ValueError('Invalid phone number format')
        return phone
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def queue(self) -> None:
        """Queue notification for sending."""
        self.status = 'queued'
        self.queued_at = datetime.now()
        self._add_to_history('queued')
    
    def send(self) -> None:
        """Mark notification as sent."""
        self.status = 'sent'
        self.sent_at = datetime.now()
        self._add_to_history('sent')
    
    def deliver(self) -> None:
        """Mark notification as delivered."""
        self.status = 'delivered'
        self.delivered_at = datetime.now()
        self._add_to_history('delivered')
    
    def open(self, ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> None:
        """
        Mark notification as opened.
        
        Args:
            ip_address: IP address of recipient
            user_agent: User agent of recipient
        """
        self.status = 'opened'
        self.opened_at = datetime.now()
        self.ip_address = ip_address
        self.user_agent = user_agent
        self._add_to_history('opened')
    
    def click(self, referrer: Optional[str] = None) -> None:
        """
        Mark notification link as clicked.
        
        Args:
            referrer: Referrer URL
        """
        self.status = 'clicked'
        self.clicked_at = datetime.now()
        self.referrer = referrer
        self._add_to_history('clicked')
    
    def fail(self, reason: str, code: Optional[str] = None) -> None:
        """
        Mark notification as failed.
        
        Args:
            reason: Failure reason
            code: Failure code
        """
        self.status = 'failed'
        self.failed_at = datetime.now()
        self.failure_reason = reason
        self.failure_code = code
        
        # Schedule retry if under max retries
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.next_retry_at = datetime.now() + timedelta(
                minutes=5 * (2 ** (self.retry_count - 1))  # Exponential backoff
            )
        
        self._add_to_history('failed', {'reason': reason, 'code': code})
    
    def bounce(self, reason: str) -> None:
        """
        Mark notification as bounced (email hard bounce).
        
        Args:
            reason: Bounce reason
        """
        self.status = 'bounced'
        self.failed_at = datetime.now()
        self.failure_reason = reason
        self._add_to_history('bounced', {'reason': reason})
    
    def suppress(self, reason: str) -> None:
        """
        Suppress notification (unsubscribed, opted out).
        
        Args:
            reason: Suppression reason
        """
        self.status = 'suppressed'
        self.failure_reason = reason
        self._add_to_history('suppressed', {'reason': reason})
    
    def cancel(self) -> None:
        """Cancel pending notification."""
        if self.status in ['pending', 'queued']:
            self.status = 'cancelled'
            self._add_to_history('cancelled')
    
    def _add_to_history(self, event: str, data: Optional[Dict] = None) -> None:
        """
        Add entry to status history.
        
        Args:
            event: Event name
            data: Additional data
        """
        if not self.status_history:
            self.status_history = []
        
        self.status_history.append({
            'event': event,
            'status': self.status,
            'timestamp': datetime.now().isoformat(),
            'data': data
        })
    
    def generate_tracking_id(self) -> str:
        """Generate unique tracking ID for open/click tracking."""
        tracking_str = f"{self.id}{self.notification_number}{datetime.utcnow().timestamp()}"
        self.tracking_id = hashlib.sha256(tracking_str.encode()).hexdigest()[:32]
        return self.tracking_id
    
    def add_attachment(
        self,
        file_name: str,
        file_url: str,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
        is_inline: bool = False
    ) -> 'NotificationAttachment':
        """
        Add attachment to notification.
        
        Args:
            file_name: Name of file
            file_url: URL to file
            file_type: MIME type
            file_size: File size in bytes
            is_inline: Whether attachment is inline
            
        Returns:
            Created NotificationAttachment instance
        """
        from models.notification import NotificationAttachment
        
        attachment = NotificationAttachment(
            notification_id=self.id,
            file_name=file_name,
            file_url=file_url,
            file_type=file_type,
            file_size=file_size,
            is_inline=is_inline
        )
        
        object_session(self).add(attachment)
        return attachment
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert notification to dictionary."""
        data = {
            'id': str(self.id),
            'notification_number': self.notification_number,
            'notification_type': self.notification_type,
            'channel': self.channel,
            'priority': self.priority,
            'status': self.status,
            'recipient': {
                'user_id': str(self.user_id) if self.user_id else None,
                'email': self.recipient_email,
                'phone': self.recipient_phone,
            },
            'content': {
                'subject': self.subject,
                'preheader': self.preheader,
            },
            'timing': {
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'queued_at': self.queued_at.isoformat() if self.queued_at else None,
                'sent_at': self.sent_at.isoformat() if self.sent_at else None,
                'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
                'opened_at': self.opened_at.isoformat() if self.opened_at else None,
                'clicked_at': self.clicked_at.isoformat() if self.clicked_at else None,
                'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            },
            'metrics': {
                'delivery_time_seconds': self.delivery_time_seconds,
                'open_time_seconds': self.open_time_seconds,
                'retry_count': self.retry_count,
            },
            'related': {
                'reservation_id': str(self.reservation_id) if self.reservation_id else None,
                'payment_id': str(self.payment_id) if self.payment_id else None,
                'vehicle_id': str(self.vehicle_id) if self.vehicle_id else None,
                'campaign_id': str(self.campaign_id) if self.campaign_id else None,
            },
            'tracking_id': self.tracking_id,
            'attachments': [a.to_dict() for a in self.attachments] if self.attachments else [],
        }
        
        if include_sensitive:
            data.update({
                'provider': self.provider,
                'provider_message_id': self.provider_message_id,
                'provider_response': self.provider_response,
                'provider_cost': float(self.provider_cost) if self.provider_cost else None,
                'failure_reason': self.failure_reason,
                'failure_code': self.failure_code,
                'metadata': self.metadata,
                'status_history': self.status_history,
            })
        
        return data
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, number={self.notification_number}, status={self.status})>"


class NotificationLog(Base):
    """
    Detailed logs of notification events.
    
    Tracks all events related to a notification for auditing and debugging.
    """
    
    __tablename__ = 'notification_logs'
    __table_args__ = (
        Index('ix_notification_logs_notification', 'notification_id'),
        Index('ix_notification_logs_event', 'event_type'),
        Index('ix_notification_logs_timestamp', 'timestamp'),
        {'comment': 'Notification event logs'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    notification_id = Column(
        UUID(as_uuid=True),
        ForeignKey('notifications.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the notification'
    )
    
    event_type = Column(
        String(50),
        nullable=False,
        comment='Type of event (sent, delivered, opened, clicked, failed, etc.)'
    )
    
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When event occurred'
    )
    
    provider_response = Column(
        JSONB,
        comment='Provider response data'
    )
    
    error_code = Column(
        String(100),
        comment='Error code if applicable'
    )
    
    error_message = Column(
        Text,
        comment='Error message if applicable'
    )
    
    ip_address = Column(
        String(45),
        comment='IP address (for opens/clicks)'
    )
    
    user_agent = Column(
        String(500),
        comment='User agent (for opens/clicks)'
    )
    
    referrer = Column(
        String(500),
        comment='Referrer (for clicks)'
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
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    notification = relationship('Notification', back_populates='logs')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log to dictionary."""
        return {
            'id': str(self.id),
            'notification_id': str(self.notification_id),
            'event_type': self.event_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'referrer': self.referrer,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationLog(id={self.id}, event={self.event_type})>"


class NotificationAttachment(Base):
    """
    Attachments for notifications.
    
    Stores file attachments for notifications (PDF receipts, images, etc.).
    """
    
    __tablename__ = 'notification_attachments'
    __table_args__ = (
        Index('ix_notification_attachments_notification', 'notification_id'),
        {'comment': 'Notification attachments'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    notification_id = Column(
        UUID(as_uuid=True),
        ForeignKey('notifications.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the notification'
    )
    
    file_name = Column(
        String(255),
        nullable=False,
        comment='Name of file'
    )
    
    file_type = Column(
        String(100),
        comment='MIME type'
    )
    
    file_size = Column(
        Integer,
        comment='File size in bytes'
    )
    
    file_url = Column(
        String(500),
        nullable=False,
        comment='URL to file'
    )
    
    file_path = Column(
        String(500),
        comment='Local file path'
    )
    
    content_id = Column(
        String(255),
        comment='Content ID for inline images'
    )
    
    is_inline = Column(
        Boolean,
        server_default='false',
        comment='Whether attachment is inline'
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
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    notification = relationship('Notification', back_populates='attachments')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert attachment to dictionary."""
        return {
            'id': str(self.id),
            'notification_id': str(self.notification_id),
            'file_name': self.file_name,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'file_url': self.file_url,
            'is_inline': self.is_inline,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationAttachment(id={self.id}, file={self.file_name})>"


class NotificationCampaign(Base):
    """
    Marketing and notification campaigns.
    
    Manages bulk notification campaigns with targeting, scheduling, and analytics.
    """
    
    __tablename__ = 'notification_campaigns'
    __table_args__ = (
        Index('ix_notification_campaigns_code', 'code', unique=True),
        Index('ix_notification_campaigns_status', 'status'),
        Index('ix_notification_campaigns_scheduled', 'scheduled_start'),
        {'comment': 'Notification campaigns'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    name = Column(
        String(255),
        nullable=False,
        comment='Campaign name'
    )
    
    code = Column(
        String(100),
        nullable=False,
        unique=True,
        comment='Unique campaign code'
    )
    
    description = Column(
        Text,
        comment='Campaign description'
    )
    
    campaign_type = Column(
        String(50),
        nullable=False,
        comment='Type of campaign (promotional, transactional, etc.)'
    )
    
    status = Column(
        String(20),
        nullable=False,
        server_default='draft',
        comment='Campaign status'
    )
    
    # =========================================================================
    # SCHEDULE
    # =========================================================================
    scheduled_start = Column(
        DateTime(timezone=True),
        comment='Scheduled start time'
    )
    
    scheduled_end = Column(
        DateTime(timezone=True),
        comment='Scheduled end time'
    )
    
    timezone = Column(
        String(50),
        server_default='UTC',
        comment='Timezone for scheduling'
    )
    
    started_at = Column(
        DateTime(timezone=True),
        comment='Actual start time'
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        comment='Completion time'
    )
    
    cancelled_at = Column(
        DateTime(timezone=True),
        comment='Cancellation time'
    )
    
    cancelled_reason = Column(
        Text,
        comment='Cancellation reason'
    )
    
    # =========================================================================
    # TARGETING
    # =========================================================================
    target_audience = Column(
        JSONB,
        comment='User filters/segments'
    )
    
    target_user_ids = Column(
        ARRAY(UUID(as_uuid=True)),
        comment='Specific user IDs'
    )
    
    excluded_user_ids = Column(
        ARRAY(UUID(as_uuid=True)),
        comment='Users to exclude'
    )
    
    target_channels = Column(
        ARRAY(String(50)),
        comment='Channels to use'
    )
    
    # =========================================================================
    # CONTENT
    # =========================================================================
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey('notification_templates.id', ondelete='SET NULL'),
        comment='Template to use'
    )
    
    template_data = Column(
        JSONB,
        comment='Template data'
    )
    
    subject = Column(
        String(255),
        comment='Subject override'
    )
    
    content_html = Column(
        Text,
        comment='HTML content override'
    )
    
    content_text = Column(
        Text,
        comment='Text content override'
    )
    
    # =========================================================================
    # A/B TESTING
    # =========================================================================
    is_ab_test = Column(
        Boolean,
        server_default='false',
        comment='Whether this is an A/B test'
    )
    
    test_variants = Column(
        JSONB,
        comment='A/B test variants'
    )
    
    test_winner_criteria = Column(
        String(50),
        comment='Criteria to determine winner'
    )
    
    test_winner_determined_at = Column(
        DateTime(timezone=True),
        comment='When winner was determined'
    )
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    total_recipients = Column(
        Integer,
        server_default='0',
        comment='Total number of recipients'
    )
    
    sent_count = Column(
        Integer,
        server_default='0',
        comment='Number sent'
    )
    
    delivered_count = Column(
        Integer,
        server_default='0',
        comment='Number delivered'
    )
    
    opened_count = Column(
        Integer,
        server_default='0',
        comment='Number opened'
    )
    
    clicked_count = Column(
        Integer,
        server_default='0',
        comment='Number clicked'
    )
    
    converted_count = Column(
        Integer,
        server_default='0',
        comment='Number converted'
    )
    
    bounced_count = Column(
        Integer,
        server_default='0',
        comment='Number bounced'
    )
    
    complained_count = Column(
        Integer,
        server_default='0',
        comment='Number complained'
    )
    
    unsubscribed_count = Column(
        Integer,
        server_default='0',
        comment='Number unsubscribed'
    )
    
    failed_count = Column(
        Integer,
        server_default='0',
        comment='Number failed'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    settings = Column(
        JSONB,
        comment='Campaign settings'
    )
    
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
        comment='User who created this campaign'
    )
    
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who last updated this campaign'
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        comment='Soft delete timestamp'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    template = relationship('NotificationTemplate')
    creator = relationship('User', foreign_keys=[created_by])
    updater = relationship('User', foreign_keys=[updated_by])
    notifications = relationship('Notification', back_populates='campaign')
    recipients = relationship('NotificationCampaignRecipient', back_populates='campaign', cascade='all, delete-orphan')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def start(self) -> None:
        """Start campaign."""
        self.status = 'sending'
        self.started_at = datetime.now()
    
    def pause(self) -> None:
        """Pause campaign."""
        self.status = 'paused'
    
    def resume(self) -> None:
        """Resume campaign."""
        self.status = 'sending'
    
    def complete(self) -> None:
        """Complete campaign."""
        self.status = 'completed'
        self.completed_at = datetime.now()
    
    def cancel(self, reason: str) -> None:
        """Cancel campaign."""
        self.status = 'cancelled'
        self.cancelled_at = datetime.now()
        self.cancelled_reason = reason
    
    def update_statistics(self) -> None:
        """Update campaign statistics from notifications."""
        from sqlalchemy import func
        
        stats = object_session(self).query(
            func.count(Notification.id).label('total'),
            func.sum(case([(Notification.status == 'sent', 1)], else_=0)).label('sent'),
            func.sum(case([(Notification.status == 'delivered', 1)], else_=0)).label('delivered'),
            func.sum(case([(Notification.status == 'opened', 1)], else_=0)).label('opened'),
            func.sum(case([(Notification.status == 'clicked', 1)], else_=0)).label('clicked'),
            func.sum(case([(Notification.status == 'failed', 1)], else_=0)).label('failed'),
            func.sum(case([(Notification.status == 'bounced', 1)], else_=0)).label('bounced'),
        ).filter(Notification.campaign_id == self.id).first()
        
        if stats:
            self.total_recipients = stats.total or 0
            self.sent_count = stats.sent or 0
            self.delivered_count = stats.delivered or 0
            self.opened_count = stats.opened or 0
            self.clicked_count = stats.clicked or 0
            self.failed_count = stats.failed or 0
            self.bounced_count = stats.bounced or 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert campaign to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'campaign_type': self.campaign_type,
            'status': self.status,
            'schedule': {
                'scheduled_start': self.scheduled_start.isoformat() if self.scheduled_start else None,
                'scheduled_end': self.scheduled_end.isoformat() if self.scheduled_end else None,
                'timezone': self.timezone,
                'started_at': self.started_at.isoformat() if self.started_at else None,
                'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            },
            'targeting': {
                'total_recipients': self.total_recipients,
                'channels': self.target_channels,
            },
            'statistics': {
                'sent': self.sent_count,
                'delivered': self.delivered_count,
                'opened': self.opened_count,
                'clicked': self.clicked_count,
                'converted': self.converted_count,
                'bounced': self.bounced_count,
                'complained': self.complained_count,
                'unsubscribed': self.unsubscribed_count,
                'failed': self.failed_count,
            },
            'is_ab_test': self.is_ab_test,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationCampaign(id={self.id}, name={self.name}, status={self.status})>"


class NotificationCampaignRecipient(Base):
    """
    Individual recipients of campaign notifications.
    
    Tracks per-recipient status for campaign notifications.
    """
    
    __tablename__ = 'notification_campaign_recipients'
    __table_args__ = (
        Index('ix_campaign_recipients_campaign', 'campaign_id'),
        Index('ix_campaign_recipients_user', 'user_id'),
        Index('ix_campaign_recipients_email', 'email'),
        Index('ix_campaign_recipients_status', 'status'),
        {'comment': 'Campaign recipients'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    campaign_id = Column(
        UUID(as_uuid=True),
        ForeignKey('notification_campaigns.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the campaign'
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='ID of the user'
    )
    
    email = Column(
        String(255),
        comment='Recipient email'
    )
    
    phone = Column(
        String(20),
        comment='Recipient phone'
    )
    
    notification_id = Column(
        UUID(as_uuid=True),
        ForeignKey('notifications.id', ondelete='SET NULL'),
        comment='ID of sent notification'
    )
    
    status = Column(
        String(20),
        server_default='pending',
        comment='Delivery status'
    )
    
    # =========================================================================
    # TIMING
    # =========================================================================
    sent_at = Column(
        DateTime(timezone=True),
        comment='When notification was sent'
    )
    
    delivered_at = Column(
        DateTime(timezone=True),
        comment='When notification was delivered'
    )
    
    opened_at = Column(
        DateTime(timezone=True),
        comment='When notification was opened'
    )
    
    clicked_at = Column(
        DateTime(timezone=True),
        comment='When link was clicked'
    )
    
    converted_at = Column(
        DateTime(timezone=True),
        comment='When conversion occurred'
    )
    
    bounced_at = Column(
        DateTime(timezone=True),
        comment='When bounce occurred'
    )
    
    complained_at = Column(
        DateTime(timezone=True),
        comment='When complaint occurred'
    )
    
    unsubscribed_at = Column(
        DateTime(timezone=True),
        comment='When unsubscribe occurred'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
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
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    campaign = relationship('NotificationCampaign', back_populates='recipients')
    user = relationship('User')
    notification = relationship('Notification')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert recipient to dictionary."""
        return {
            'id': str(self.id),
            'campaign_id': str(self.campaign_id),
            'user_id': str(self.user_id) if self.user_id else None,
            'email': self.email,
            'phone': self.phone,
            'notification_id': str(self.notification_id) if self.notification_id else None,
            'status': self.status,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'clicked_at': self.clicked_at.isoformat() if self.clicked_at else None,
            'converted_at': self.converted_at.isoformat() if self.converted_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationCampaignRecipient(id={self.id}, campaign={self.campaign_id}, status={self.status})>"


class NotificationBatch(Base):
    """
    Batch processing groups for notifications.
    
    Groups notifications for batch sending and tracking.
    """
    
    __tablename__ = 'notification_batches'
    __table_args__ = (
        Index('ix_notification_batches_number', 'batch_number', unique=True),
        Index('ix_notification_batches_status', 'status'),
        {'comment': 'Notification batches'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    batch_number = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Unique batch number'
    )
    
    name = Column(
        String(255),
        comment='Batch name'
    )
    
    description = Column(
        Text,
        comment='Batch description'
    )
    
    total_count = Column(
        Integer,
        server_default='0',
        comment='Total notifications in batch'
    )
    
    processed_count = Column(
        Integer,
        server_default='0',
        comment='Number processed'
    )
    
    success_count = Column(
        Integer,
        server_default='0',
        comment='Number successful'
    )
    
    failed_count = Column(
        Integer,
        server_default='0',
        comment='Number failed'
    )
    
    status = Column(
        String(20),
        server_default='processing',
        comment='Batch status'
    )
    
    started_at = Column(
        DateTime(timezone=True),
        comment='When batch started'
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        comment='When batch completed'
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
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created this batch'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    creator = relationship('User', foreign_keys=[created_by])
    notifications = relationship('Notification', back_populates='batch')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert batch to dictionary."""
        return {
            'id': str(self.id),
            'batch_number': self.batch_number,
            'name': self.name,
            'description': self.description,
            'total_count': self.total_count,
            'processed_count': self.processed_count,
            'success_count': self.success_count,
            'failed_count': self.failed_count,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationBatch(id={self.id}, number={self.batch_number})>"


class NotificationWebhook(Base):
    """
    Webhook endpoints for external notifications.
    
    Configures webhooks for sending notifications to external systems.
    """
    
    __tablename__ = 'notification_webhooks'
    __table_args__ = (
        Index('ix_notification_webhooks_url', 'url'),
        Index('ix_notification_webhooks_active', 'is_active'),
        {'comment': 'Notification webhooks'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    name = Column(
        String(255),
        nullable=False,
        comment='Webhook name'
    )
    
    url = Column(
        String(500),
        nullable=False,
        comment='Webhook URL'
    )
    
    method = Column(
        String(10),
        nullable=False,
        server_default='POST',
        comment='HTTP method'
    )
    
    headers = Column(
        JSONB,
        comment='HTTP headers'
    )
    
    auth_type = Column(
        String(50),
        comment='Authentication type (basic, bearer, api_key)'
    )
    
    auth_credentials = Column(
        JSONB,
        comment='Authentication credentials (encrypted)'
    )
    
    # =========================================================================
    # EVENTS
    # =========================================================================
    events = Column(
        ARRAY(String(100)),
        comment='Events that trigger this webhook'
    )
    
    secret = Column(
        String(255),
        comment='Secret for signature verification'
    )
    
    signature_header = Column(
        String(100),
        comment='Header name for signature'
    )
    
    # =========================================================================
    # RETRY CONFIGURATION
    # =========================================================================
    retry_count = Column(
        Integer,
        server_default='3',
        comment='Number of retries'
    )
    
    retry_delay = Column(
        Integer,
        server_default='60',
        comment='Delay between retries (seconds)'
    )
    
    timeout = Column(
        Integer,
        server_default='30',
        comment='Request timeout (seconds)'
    )
    
    # =========================================================================
    # RATE LIMITING
    # =========================================================================
    rate_limit = Column(
        Integer,
        comment='Requests per minute limit'
    )
    
    rate_limit_reset = Column(
        DateTime(timezone=True),
        comment='When rate limit resets'
    )
    
    # =========================================================================
    # STATUS
    # =========================================================================
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether webhook is active'
    )
    
    last_triggered_at = Column(
        DateTime(timezone=True),
        comment='When last triggered'
    )
    
    last_success_at = Column(
        DateTime(timezone=True),
        comment='Last successful delivery'
    )
    
    last_failure_at = Column(
        DateTime(timezone=True),
        comment='Last failure'
    )
    
    failure_count = Column(
        Integer,
        server_default='0',
        comment='Number of failures'
    )
    
    success_count = Column(
        Integer,
        server_default='0',
        comment='Number of successes'
    )
    
    average_response_time_ms = Column(
        Float,
        comment='Average response time'
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
        comment='User who created this webhook'
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        comment='Soft delete timestamp'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    creator = relationship('User', foreign_keys=[created_by])
    deliveries = relationship('NotificationWebhookDelivery', back_populates='webhook', cascade='all, delete-orphan')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def generate_signature(self, payload: bytes) -> str:
        """
        Generate signature for webhook payload.
        
        Args:
            payload: Raw payload bytes
            
        Returns:
            HMAC signature
        """
        if not self.secret:
            return None
        
        signature = hmac.new(
            self.secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Raw payload bytes
            signature: Signature to verify
            
        Returns:
            True if signature is valid
        """
        if not self.secret:
            return True
        
        expected = self.generate_signature(payload)
        return hmac.compare_digest(expected, signature)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert webhook to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'url': self.url,
            'method': self.method,
            'events': self.events,
            'auth_type': self.auth_type,
            'is_active': self.is_active,
            'retry_count': self.retry_count,
            'retry_delay': self.retry_delay,
            'timeout': self.timeout,
            'rate_limit': self.rate_limit,
            'last_triggered_at': self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            'last_success_at': self.last_success_at.isoformat() if self.last_success_at else None,
            'last_failure_at': self.last_failure_at.isoformat() if self.last_failure_at else None,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'average_response_time_ms': self.average_response_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationWebhook(id={self.id}, name={self.name}, url={self.url})>"


class NotificationWebhookDelivery(Base):
    """
    Delivery attempts for notification webhooks.
    
    Tracks each webhook delivery attempt with request/response details.
    """
    
    __tablename__ = 'notification_webhook_deliveries'
    __table_args__ = (
        Index('ix_webhook_deliveries_webhook', 'webhook_id'),
        Index('ix_webhook_deliveries_success', 'success'),
        Index('ix_webhook_deliveries_created', 'created_at'),
        {'comment': 'Webhook delivery attempts'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    webhook_id = Column(
        UUID(as_uuid=True),
        ForeignKey('notification_webhooks.id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the webhook'
    )
    
    event_type = Column(
        String(100),
        nullable=False,
        comment='Event type that triggered delivery'
    )
    
    payload = Column(
        JSONB,
        nullable=False,
        comment='Payload sent'
    )
    
    headers = Column(
        JSONB,
        comment='Headers sent'
    )
    
    response_status = Column(
        Integer,
        comment='HTTP response status'
    )
    
    response_body = Column(
        Text,
        comment='Response body'
    )
    
    response_headers = Column(
        JSONB,
        comment='Response headers'
    )
    
    response_time_ms = Column(
        Integer,
        comment='Response time in milliseconds'
    )
    
    success = Column(
        Boolean,
        comment='Whether delivery was successful'
    )
    
    error_message = Column(
        Text,
        comment='Error message if failed'
    )
    
    attempt = Column(
        Integer,
        server_default='1',
        comment='Attempt number'
    )
    
    next_retry_at = Column(
        DateTime(timezone=True),
        comment='When to next retry'
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        comment='When delivery completed'
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
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    webhook = relationship('NotificationWebhook', back_populates='deliveries')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert delivery to dictionary."""
        return {
            'id': str(self.id),
            'webhook_id': str(self.webhook_id),
            'event_type': self.event_type,
            'response_status': self.response_status,
            'response_time_ms': self.response_time_ms,
            'success': self.success,
            'error_message': self.error_message,
            'attempt': self.attempt,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationWebhookDelivery(id={self.id}, webhook={self.webhook_id}, success={self.success})>"


class NotificationSubscription(Base):
    """
    Newsletter and marketing subscriptions.
    
    Manages user subscriptions to newsletters and marketing communications.
    """
    
    __tablename__ = 'notification_subscriptions'
    __table_args__ = (
        Index('ix_notification_subs_user', 'user_id'),
        Index('ix_notification_subs_email', 'email'),
        Index('ix_notification_subs_type', 'subscription_type'),
        Index('ix_notification_subs_verified', 'verified'),
        UniqueConstraint('user_id', 'subscription_type', name='uq_user_subscription_type'),
        UniqueConstraint('email', 'subscription_type', name='uq_email_subscription_type'),
        {'comment': 'Notification subscriptions'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        comment='ID of the user (if registered)'
    )
    
    email = Column(
        String(255),
        comment='Email address (for guests)'
    )
    
    phone = Column(
        String(20),
        comment='Phone number (for SMS subscriptions)'
    )
    
    subscription_type = Column(
        String(100),
        nullable=False,
        comment='Type of subscription (newsletter, promotions, etc.)'
    )
    
    tier = Column(
        String(50),
        server_default='free',
        comment='Subscription tier'
    )
    
    verified = Column(
        Boolean,
        server_default='false',
        comment='Whether subscription is verified'
    )
    
    verified_at = Column(
        DateTime(timezone=True),
        comment='When subscription was verified'
    )
    
    verification_token = Column(
        String(255),
        comment='Verification token'
    )
    
    verification_sent_at = Column(
        DateTime(timezone=True),
        comment='When verification was sent'
    )
    
    subscribed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When subscription started'
    )
    
    unsubscribed_at = Column(
        DateTime(timezone=True),
        comment='When unsubscribed'
    )
    
    unsubscribe_reason = Column(
        Text,
        comment='Reason for unsubscribing'
    )
    
    unsubscribe_token = Column(
        String(255),
        comment='One-click unsubscribe token'
    )
    
    preferences = Column(
        JSONB,
        comment='Subscription preferences'
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
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship('User')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def generate_verification_token(self) -> str:
        """Generate verification token."""
        token_str = f"{self.email or self.phone}{self.id}{datetime.utcnow().timestamp()}"
        self.verification_token = hashlib.sha256(token_str.encode()).hexdigest()
        return self.verification_token
    
    def generate_unsubscribe_token(self) -> str:
        """Generate one-click unsubscribe token."""
        token_str = f"{self.id}{self.email or self.phone}{self.subscription_type}"
        self.unsubscribe_token = hashlib.sha256(token_str.encode()).hexdigest()
        return self.unsubscribe_token
    
    def verify(self) -> None:
        """Verify subscription."""
        self.verified = True
        self.verified_at = datetime.now()
        self.verification_token = None
    
    def unsubscribe(self, reason: Optional[str] = None) -> None:
        """Unsubscribe from mailing list."""
        self.verified = False
        self.unsubscribed_at = datetime.now()
        self.unsubscribe_reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subscription to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id) if self.user_id else None,
            'email': self.email,
            'phone': self.phone,
            'subscription_type': self.subscription_type,
            'tier': self.tier,
            'verified': self.verified,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'subscribed_at': self.subscribed_at.isoformat() if self.subscribed_at else None,
            'unsubscribed_at': self.unsubscribed_at.isoformat() if self.unsubscribed_at else None,
            'preferences': self.preferences,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationSubscription(id={self.id}, type={self.subscription_type})>"


class NotificationSuppression(Base):
    """
    Suppressed recipients due to bounces, complaints, or unsubscribes.
    
    Maintains a suppression list to prevent sending to invalid or opted-out recipients.
    """
    
    __tablename__ = 'notification_suppressions'
    __table_args__ = (
        Index('ix_notification_suppressions_user', 'user_id'),
        Index('ix_notification_suppressions_email', 'email'),
        Index('ix_notification_suppressions_phone', 'phone'),
        Index('ix_notification_suppressions_reason', 'reason'),
        {'comment': 'Notification suppressions'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        comment='ID of the user'
    )
    
    email = Column(
        String(255),
        comment='Suppressed email'
    )
    
    phone = Column(
        String(20),
        comment='Suppressed phone'
    )
    
    device_token = Column(
        String(500),
        comment='Suppressed device token'
    )
    
    reason = Column(
        String(50),
        nullable=False,
        comment='Reason for suppression'
    )
    
    reason_details = Column(
        Text,
        comment='Detailed reason'
    )
    
    suppressed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When suppression was added'
    )
    
    expires_at = Column(
        DateTime(timezone=True),
        comment='When suppression expires'
    )
    
    is_permanent = Column(
        Boolean,
        server_default='false',
        comment='Whether suppression is permanent'
    )
    
    source = Column(
        String(100),
        comment='Source of suppression (system, user, provider)'
    )
    
    provider_feedback = Column(
        JSONB,
        comment='Provider feedback data'
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
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship('User')
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if suppression is active."""
        if self.is_permanent:
            return True
        if self.expires_at:
            return datetime.now(self.expires_at.tzinfo) < self.expires_at
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert suppression to dictionary."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id) if self.user_id else None,
            'email': self.email,
            'phone': self.phone,
            'reason': self.reason,
            'reason_details': self.reason_details,
            'suppressed_at': self.suppressed_at.isoformat() if self.suppressed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_permanent': self.is_permanent,
            'is_active': self.is_active,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationSuppression(id={self.id}, reason={self.reason})>"


class NotificationTrigger(Base):
    """
    Automatic triggers for notifications based on system events.
    
    Defines rules for automatically sending notifications when specific events occur.
    """
    
    __tablename__ = 'notification_triggers'
    __table_args__ = (
        Index('ix_notification_triggers_event', 'trigger_event'),
        Index('ix_notification_triggers_active', 'is_active'),
        {'comment': 'Notification triggers'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    name = Column(
        String(255),
        nullable=False,
        comment='Trigger name'
    )
    
    description = Column(
        Text,
        comment='Trigger description'
    )
    
    trigger_event = Column(
        String(100),
        nullable=False,
        comment='Event that triggers notification'
    )
    
    notification_type = Column(
        String(50),
        nullable=False,
        comment='Type of notification to send'
    )
    
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey('notification_templates.id', ondelete='SET NULL'),
        comment='Template to use'
    )
    
    channel = Column(
        String(50),
        nullable=False,
        comment='Channel to use'
    )
    
    delay_seconds = Column(
        Integer,
        server_default='0',
        comment='Delay before sending (seconds)'
    )
    
    conditions = Column(
        JSONB,
        comment='Conditions for triggering'
    )
    
    template_data_map = Column(
        JSONB,
        comment='How to map event data to template variables'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether trigger is active'
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
        comment='User who created this trigger'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    template = relationship('NotificationTemplate')
    creator = relationship('User', foreign_keys=[created_by])
    
    def evaluate(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluate whether trigger should fire and prepare template data.
        
        Args:
            event_data: Event data from system
            
        Returns:
            Template data if trigger should fire, None otherwise
        """
        # Check conditions
        if self.conditions:
            for key, value in self.conditions.items():
                if key not in event_data or event_data[key] != value:
                    return None
        
        # Map event data to template variables
        template_data = {}
        if self.template_data_map:
            for template_var, event_path in self.template_data_map.items():
                # Simple dot notation path traversal
                parts = event_path.split('.')
                current = event_data
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        current = None
                        break
                if current is not None:
                    template_data[template_var] = current
        
        return template_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trigger to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'trigger_event': self.trigger_event,
            'notification_type': self.notification_type,
            'template_id': str(self.template_id) if self.template_id else None,
            'channel': self.channel,
            'delay_seconds': self.delay_seconds,
            'conditions': self.conditions,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<NotificationTrigger(id={self.id}, event={self.trigger_event})>"


# =========================================================================
# EVENT LISTENERS
# =========================================================================

@event.listens_for(Notification, 'before_insert')
def notification_before_insert(mapper, connection, target):
    """Generate notification number and tracking ID for new notifications."""
    if not target.notification_number:
        date_str = datetime.now().strftime('%Y%m%d')
        
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(notification_number FROM 11)::INTEGER), 0) + 1
                FROM notifications
                WHERE notification_number LIKE :pattern
            """),
            {'pattern': f'NOT-{date_str}-%'}
        )
        seq_num = result.scalar()
        
        target.notification_number = f"NOT-{date_str}-{seq_num:06d}"
    
    if not target.tracking_id:
        target.generate_tracking_id()


@event.listens_for(NotificationBatch, 'before_insert')
def batch_before_insert(mapper, connection, target):
    """Generate batch number for new batches."""
    if not target.batch_number:
        date_str = datetime.now().strftime('%Y%m%d')
        
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(batch_number FROM 11)::INTEGER), 0) + 1
                FROM notification_batches
                WHERE batch_number LIKE :pattern
            """),
            {'pattern': f'BAT-{date_str}-%'}
        )
        seq_num = result.scalar()
        
        target.batch_number = f"BAT-{date_str}-{seq_num:06d}"


@event.listens_for(Notification, 'after_insert')
def notification_after_insert(mapper, connection, target):
    """Queue notification for sending."""
    # This would typically be handled by a task queue
    pass


@event.listens_for(Notification, 'after_update')
def notification_after_update(mapper, connection, target):
    """Update campaign statistics when notification status changes."""
    if target.campaign_id:
        connection.execute(
            text("""
                UPDATE notification_campaigns
                SET 
                    sent_count = (
                        SELECT COUNT(*) FROM notifications 
                        WHERE campaign_id = :campaign_id AND status = 'sent'
                    ),
                    delivered_count = (
                        SELECT COUNT(*) FROM notifications 
                        WHERE campaign_id = :campaign_id AND status = 'delivered'
                    ),
                    opened_count = (
                        SELECT COUNT(*) FROM notifications 
                        WHERE campaign_id = :campaign_id AND status = 'opened'
                    ),
                    clicked_count = (
                        SELECT COUNT(*) FROM notifications 
                        WHERE campaign_id = :campaign_id AND status = 'clicked'
                    ),
                    failed_count = (
                        SELECT COUNT(*) FROM notifications 
                        WHERE campaign_id = :campaign_id AND status = 'failed'
                    ),
                    bounced_count = (
                        SELECT COUNT(*) FROM notifications 
                        WHERE campaign_id = :campaign_id AND status = 'bounced'
                    ),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :campaign_id
            """),
            {'campaign_id': target.campaign_id}
        )


# =========================================================================
# FACTORY FUNCTIONS
# =========================================================================

def create_notification(
    notification_type: str,
    channel: str,
    recipient: Dict[str, Any],
    template_id: Optional[uuid.UUID] = None,
    template_data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Notification:
    """
    Factory function to create a new notification.
    
    Args:
        notification_type: Type of notification
        channel: Delivery channel
        recipient: Recipient information (user_id, email, phone, device_id)
        template_id: ID of template to use
        template_data: Data for template rendering
        **kwargs: Additional notification attributes
        
    Returns:
        New Notification instance
    """
    notification = Notification(
        notification_type=notification_type,
        channel=channel,
        user_id=recipient.get('user_id'),
        recipient_email=recipient.get('email'),
        recipient_phone=recipient.get('phone'),
        recipient_device_id=recipient.get('device_id'),
        template_id=template_id,
        template_data=template_data,
        **kwargs
    )
    
    return notification


def create_campaign(
    name: str,
    code: str,
    campaign_type: str,
    template_id: Optional[uuid.UUID] = None,
    **kwargs
) -> NotificationCampaign:
    """
    Factory function to create a new campaign.
    
    Args:
        name: Campaign name
        code: Campaign code
        campaign_type: Type of campaign
        template_id: ID of template to use
        **kwargs: Additional campaign attributes
        
    Returns:
        New NotificationCampaign instance
    """
    campaign = NotificationCampaign(
        name=name,
        code=code,
        campaign_type=campaign_type,
        template_id=template_id,
        **kwargs
    )
    
    return campaign


def create_system_templates(session) -> List[NotificationTemplate]:
    """
    Create default system templates.
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        List of created templates
    """
    templates = [
        # Reservation confirmation email
        NotificationTemplate(
            code='reservation_confirmation_email',
            name='Reservation Confirmation Email',
            notification_type='reservation_confirmation',
            channel='email',
            template_type='email_html',
            subject='Your Parking Reservation Confirmed - {{reservation_number}}',
            preheader='Thank you for choosing our parking service',
            content_html="""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reservation Confirmed</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #2c3e50;">Reservation Confirmed</h1>
        <p>Dear {{customer_name}},</p>
        <p>Your parking reservation has been confirmed.</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin-top: 0;">Reservation Details</h3>
            <p><strong>Reservation Number:</strong> {{reservation_number}}</p>
            <p><strong>Date:</strong> {{date}}</p>
            <p><strong>Time:</strong> {{start_time}} - {{end_time}}</p>
            <p><strong>Location:</strong> {{zone_name}}, Spot {{spot_number}}</p>
            <p><strong>Total Amount:</strong> {{total_amount}} {{currency}}</p>
        </div>
        
        <p>Please arrive on time and have your QR code ready for check-in.</p>
        <p>Thank you for choosing our service!</p>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #777;">
            If you need to modify or cancel your reservation, please visit our website.
        </p>
    </div>
</body>
</html>""",
            content_text="""Reservation Confirmed

Dear {{customer_name}},

Your parking reservation has been confirmed.

Reservation Details:
- Reservation Number: {{reservation_number}}
- Date: {{date}}
- Time: {{start_time}} - {{end_time}}
- Location: {{zone_name}}, Spot {{spot_number}}
- Total Amount: {{total_amount}} {{currency}}

Please arrive on time and have your QR code ready for check-in.

Thank you for choosing our service!""",
            variables=['customer_name', 'reservation_number', 'date', 'start_time', 'end_time', 
                      'zone_name', 'spot_number', 'total_amount', 'currency'],
            required_variables=['reservation_number', 'start_time', 'end_time'],
            is_system=True
        ),
        
        # Payment receipt email
        NotificationTemplate(
            code='payment_receipt_email',
            name='Payment Receipt Email',
            notification_type='payment_receipt',
            channel='email',
            template_type='email_html',
            subject='Payment Receipt - {{payment_number}}',
            preheader='Thank you for your payment',
            content_html="""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Payment Receipt</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h1 style="color: #2c3e50;">Payment Receipt</h1>
        <p>Dear {{customer_name}},</p>
        <p>Thank you for your payment. Your transaction has been completed successfully.</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="margin-top: 0;">Payment Details</h3>
            <p><strong>Payment Number:</strong> {{payment_number}}</p>
            <p><strong>Amount:</strong> {{amount}} {{currency}}</p>
            <p><strong>Date:</strong> {{date}}</p>
            <p><strong>Payment Method:</strong> {{payment_method}}</p>
            <p><strong>Reservation:</strong> {{reservation_number}}</p>
        </div>
        
        <p>A receipt has been attached to this email for your records.</p>
        <p>Thank you for your business!</p>
    </div>
</body>
</html>""",
            content_text="""Payment Receipt

Dear {{customer_name}},

Thank you for your payment. Your transaction has been completed successfully.

Payment Details:
- Payment Number: {{payment_number}}
- Amount: {{amount}} {{currency}}
- Date: {{date}}
- Payment Method: {{payment_method}}
- Reservation: {{reservation_number}}

A receipt has been attached to this email for your records.

Thank you for your business!""",
            variables=['customer_name', 'payment_number', 'amount', 'currency', 'date', 
                      'payment_method', 'reservation_number'],
            required_variables=['payment_number', 'amount'],
            is_system=True
        ),
        
        # SMS check-in success
        NotificationTemplate(
            code='check_in_success_sms',
            name='Check-In Success SMS',
            notification_type='check_in_success',
            channel='sms',
            template_type='sms_text',
            content_text='You have checked in at {{zone_name}}. Spot: {{spot_number}}. Duration: {{duration_hours}}h. Thank you!',
            variables=['zone_name', 'spot_number', 'duration_hours'],
            required_variables=['spot_number'],
            is_system=True
        ),
        
        # Push notification for spot available
        NotificationTemplate(
            code='spot_available_push',
            name='Spot Available Push',
            notification_type='spot_available',
            channel='push',
            template_type='push_notification',
            subject='Parking Spot Available!',
            content_json={
                'body': 'A {{spot_type}} spot is now available in {{zone_name}}.',
                'data': {
                    'zone_id': '{{zone_id}}',
                    'spot_type': '{{spot_type}}'
                }
            },
            variables=['spot_type', 'zone_name', 'zone_id'],
            required_variables=['zone_name'],
            is_system=True
        ),
    ]
    
    for template in templates:
        existing = session.query(NotificationTemplate).filter_by(code=template.code).first()
        if not existing:
            session.add(template)
    
    session.commit()
    return templates


# =========================================================================
# EXPORTS
# =========================================================================

__all__ = [
    # Main models
    'NotificationTemplate',
    'NotificationDevice',
    'NotificationPreference',
    'Notification',
    'NotificationLog',
    'NotificationAttachment',
    'NotificationCampaign',
    'NotificationCampaignRecipient',
    'NotificationBatch',
    'NotificationWebhook',
    'NotificationWebhookDelivery',
    'NotificationSubscription',
    'NotificationSuppression',
    'NotificationTrigger',
    
    # Enums
    'NotificationType',
    'NotificationChannel',
    'NotificationStatus',
    'NotificationPriority',
    'TemplateType',
    'DeviceType',
    'SubscriptionTier',
    'CampaignStatus',
    'WebhookMethod',
    'Frequency',
    'SuppressionReason',
    
    # Factory functions
    'create_notification',
    'create_campaign',
    'create_system_templates',
]