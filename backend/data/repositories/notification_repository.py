# parking-management/data/migrations/repositories/notification_repository.py
"""
Notification repository module for the parking management system.

This module provides repository classes for managing notifications, templates,
campaigns, webhooks, and user preferences with comprehensive integration
with the enum definitions.
"""

from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
import json
import hashlib
import hmac
import secrets
from uuid import uuid4
from enum import Enum

from sqlalchemy import (
    and_, or_, not_, desc, asc, func, select,
    update, delete, between, cast, Float, Integer,
    String, DateTime, Boolean, Numeric, Interval,
    Date, Text, JSON
)
from sqlalchemy.orm import Session, Query, joinedload, selectinload
from sqlalchemy.sql import expression

from .base_repository import (
    BaseRepository,
    AuditableRepository,
    CacheableRepository,
    SearchableRepository,
    FullFeatureRepository,
    EntityNotFoundException,
    DuplicateEntityException,
    ValidationException,
    RepositoryException,
    QueryBuilder
)
from ..models.enums import (
    # Notification enums
    NotificationType,
    NotificationChannel,
    NotificationStatus,
    NotificationPriority,
    TemplateType,
    DeviceType,
    CampaignStatus,
    WebhookMethod,
    Frequency,
    SuppressionReason,
    
    # Audit enums
    AuditAction,
    AuditStatus,
    AuditSeverity,
    AuditCategory,
    AuditResourceType,
    
    # General enums
    Language
)
from ..models.notification_models import (
    # Notification models
    Notification,
    NotificationTemplate,
    NotificationLog,
    NotificationPreference,
    NotificationAttachment,
    NotificationBatch,
    NotificationSchedule,
    
    # Campaign models
    Campaign,
    CampaignRecipient,
    CampaignAnalytics,
    
    # Webhook models
    Webhook,
    WebhookDelivery,
    WebhookEndpoint,
    WebhookEvent,
    
    # Device models
    Device,
    DeviceToken,
    DevicePreference,
    
    # Subscription models
    NotificationSubscription,
    NotificationDigest,
    
    # Template models
    EmailTemplate,
    SMSTemplate,
    PushTemplate,
    
    # Queue models
    NotificationQueue,
    NotificationRetry
)
from ..models.user_models import (
    User,
    UserPreference
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class NotificationNotFoundException(EntityNotFoundException):
    """Raised when a notification is not found."""
    def __init__(self, notification_id: Any):
        super().__init__("Notification", notification_id)


class TemplateNotFoundException(EntityNotFoundException):
    """Raised when a template is not found."""
    def __init__(self, template_id: Any):
        super().__init__("NotificationTemplate", template_id)


class CampaignNotFoundException(EntityNotFoundException):
    """Raised when a campaign is not found."""
    def __init__(self, campaign_id: Any):
        super().__init__("Campaign", campaign_id)


class WebhookNotFoundException(EntityNotFoundException):
    """Raised when a webhook is not found."""
    def __init__(self, webhook_id: Any):
        super().__init__("Webhook", webhook_id)


class DeviceNotFoundException(EntityNotFoundException):
    """Raised when a device is not found."""
    def __init__(self, device_id: Any):
        super().__init__("Device", device_id)


class NotificationDeliveryException(RepositoryException):
    """Raised when notification delivery fails."""
    def __init__(self, message: str, channel: NotificationChannel):
        self.channel = channel
        super().__init__(f"Notification delivery failed via {channel.value}: {message}")


class TemplateRenderException(RepositoryException):
    """Raised when template rendering fails."""
    def __init__(self, template_id: int, error: str):
        self.template_id = template_id
        super().__init__(f"Failed to render template {template_id}: {error}")


class RateLimitExceededException(RepositoryException):
    """Raised when rate limit is exceeded."""
    def __init__(self, channel: NotificationChannel, limit: int, reset_at: datetime):
        self.channel = channel
        self.limit = limit
        self.reset_at = reset_at
        super().__init__(
            f"Rate limit exceeded for {channel.value}: {limit} per period, "
            f"resets at {reset_at.isoformat()}"
        )


class UserOptedOutException(RepositoryException):
    """Raised when a user has opted out of notifications."""
    def __init__(self, user_id: int, channel: NotificationChannel):
        self.user_id = user_id
        self.channel = channel
        super().__init__(f"User {user_id} has opted out of {channel.value} notifications")


class InvalidWebhookSignatureException(RepositoryException):
    """Raised when webhook signature is invalid."""
    def __init__(self, webhook_id: int):
        self.webhook_id = webhook_id
        super().__init__(f"Invalid signature for webhook {webhook_id}")


# ============================================================================
# Notification Repository
# ============================================================================

class NotificationRepository(FullFeatureRepository[Notification, int]):
    """
    Repository for Notification entity with comprehensive notification management features.
    
    This repository provides methods for creating, sending, and tracking notifications
    across multiple channels with templating, batching, and delivery guarantees.
    """
    
    def __init__(self, session: Session):
        super().__init__(session, Notification)
        self.searchable_fields = ['subject', 'content', 'metadata']
        
        # Rate limiting configuration (per channel)
        self.rate_limits = {
            NotificationChannel.EMAIL: {"limit": 1000, "period": 3600},  # 1000 per hour
            NotificationChannel.SMS: {"limit": 100, "period": 3600},     # 100 per hour
            NotificationChannel.PUSH: {"limit": 5000, "period": 3600},   # 5000 per hour
            NotificationChannel.WHATSAPP: {"limit": 500, "period": 3600} # 500 per hour
        }
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delays = [60, 300, 3600]  # 1 minute, 5 minutes, 1 hour
    
    # ========================================================================
    # Custom Query Methods
    # ========================================================================
    
    def get_user_notifications(
        self,
        user_id: int,
        notification_type: Optional[NotificationType] = None,
        statuses: Optional[List[NotificationStatus]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Notification]:
        """
        Get notifications for a user.
        
        Args:
            user_id: User ID
            notification_type: Optional type filter
            statuses: Optional status filter
            from_date: Optional start date
            to_date: Optional end date
            limit: Maximum number to return
            
        Returns:
            List of user's notifications
        """
        query = self.session.query(Notification).filter(
            Notification.user_id == user_id
        )
        
        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)
        
        if statuses:
            query = query.filter(Notification.status.in_(statuses))
        
        if from_date:
            query = query.filter(Notification.created_at >= from_date)
        
        if to_date:
            query = query.filter(Notification.created_at <= to_date)
        
        return query.order_by(desc(Notification.created_at)).limit(limit).all()
    
    def get_pending_notifications(
        self,
        channel: Optional[NotificationChannel] = None,
        limit: int = 100
    ) -> List[Notification]:
        """
        Get notifications pending delivery.
        
        Args:
            channel: Optional channel filter
            limit: Maximum number to return
            
        Returns:
            List of pending notifications
        """
        query = self.session.query(Notification).filter(
            Notification.status == NotificationStatus.PENDING,
            or_(
                Notification.scheduled_for.is_(None),
                Notification.scheduled_for <= datetime.utcnow()
            )
        )
        
        if channel:
            query = query.filter(Notification.channel == channel)
        
        return query.order_by(Notification.priority.desc(), Notification.created_at).limit(limit).all()
    
    def get_notifications_by_reference(
        self,
        reference_type: str,
        reference_id: int
    ) -> List[Notification]:
        """
        Get notifications by reference (e.g., all notifications for a reservation).
        
        Args:
            reference_type: Type of reference (reservation, payment, etc.)
            reference_id: ID of the reference
            
        Returns:
            List of notifications
        """
        return (
            self.session.query(Notification)
            .filter(
                Notification.reference_type == reference_type,
                Notification.reference_id == reference_id
            )
            .order_by(desc(Notification.created_at))
            .all()
        )
    
    def get_failed_notifications(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Notification]:
        """
        Get failed notifications for retry processing.
        
        Args:
            from_date: Optional start date
            to_date: Optional end date
            limit: Maximum number to return
            
        Returns:
            List of failed notifications
        """
        query = self.session.query(Notification).filter(
            Notification.status == NotificationStatus.FAILED,
            Notification.retry_count < self.max_retries
        )
        
        if from_date:
            query = query.filter(Notification.created_at >= from_date)
        
        if to_date:
            query = query.filter(Notification.created_at <= to_date)
        
        return query.order_by(Notification.created_at).limit(limit).all()
    
    def get_notification_statistics(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get notification statistics.
        
        Args:
            from_date: Optional start date
            to_date: Optional end date
            
        Returns:
            Dictionary with notification statistics
        """
        query = self.session.query(Notification)
        
        if from_date:
            query = query.filter(Notification.created_at >= from_date)
        
        if to_date:
            query = query.filter(Notification.created_at <= to_date)
        
        total = query.count()
        
        # Count by status
        status_counts = {}
        for status in NotificationStatus:
            count = query.filter(Notification.status == status).count()
            if count > 0:
                status_counts[status.value] = count
        
        # Count by channel
        channel_counts = {}
        for channel in NotificationChannel:
            count = query.filter(Notification.channel == channel).count()
            if count > 0:
                channel_counts[channel.value] = count
        
        # Count by type
        type_counts = {}
        for ntype in NotificationType:
            count = query.filter(Notification.notification_type == ntype).count()
            if count > 0:
                type_counts[ntype.value] = count
        
        # Delivery metrics
        delivered = query.filter(Notification.status.in_(
            NotificationStatus.get_success_statuses()
        )).count()
        
        failed = query.filter(Notification.status == NotificationStatus.FAILED).count()
        
        # Average delivery time
        delivered_notifications = query.filter(
            Notification.status == NotificationStatus.DELIVERED,
            Notification.sent_at.isnot(None),
            Notification.created_at.isnot(None)
        ).all()
        
        if delivered_notifications:
            avg_delivery_time = sum(
                (n.sent_at - n.created_at).total_seconds()
                for n in delivered_notifications
            ) / len(delivered_notifications)
        else:
            avg_delivery_time = 0
        
        return {
            'total': total,
            'by_status': status_counts,
            'by_channel': channel_counts,
            'by_type': type_counts,
            'delivery_rate': round(delivered / total * 100, 2) if total > 0 else 0,
            'failure_rate': round(failed / total * 100, 2) if total > 0 else 0,
            'avg_delivery_time_seconds': round(avg_delivery_time, 2)
        }
    
    # ========================================================================
    # Notification Creation and Sending
    # ========================================================================
    
    def create_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        channel: NotificationChannel,
        subject: Optional[str] = None,
        content: Optional[str] = None,
        template_id: Optional[int] = None,
        template_data: Optional[Dict] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        scheduled_for: Optional[datetime] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        **kwargs
    ) -> Notification:
        """
        Create a new notification.
        
        Args:
            user_id: Recipient user ID
            notification_type: Type of notification
            channel: Delivery channel
            subject: Optional subject (for email)
            content: Optional content
            template_id: Optional template ID
            template_data: Optional data for template rendering
            priority: Notification priority
            scheduled_for: Optional scheduled delivery time
            reference_type: Optional reference type
            reference_id: Optional reference ID
            **kwargs: Additional notification attributes
            
        Returns:
            Created notification
        """
        # Check user preferences
        if not self._check_user_preferences(user_id, notification_type, channel):
            raise UserOptedOutException(user_id, channel)
        
        # Check rate limits
        self._check_rate_limits(user_id, channel)
        
        # Generate notification ID
        notification_id = self._generate_notification_id()
        
        # Render template if provided
        if template_id and template_data:
            subject, content = self._render_template(template_id, template_data, channel)
        
        # Create notification
        notification = Notification(
            notification_id=notification_id,
            user_id=user_id,
            notification_type=notification_type,
            channel=channel,
            subject=subject,
            content=content,
            template_id=template_id,
            template_data=template_data,
            priority=priority,
            status=NotificationStatus.PENDING,
            scheduled_for=scheduled_for,
            reference_type=reference_type,
            reference_id=reference_id,
            metadata=kwargs.get('metadata', {}),
            created_at=datetime.utcnow()
        )
        
        self.session.add(notification)
        self.session.flush()
        
        # Add to queue if immediate delivery
        if not scheduled_for or scheduled_for <= datetime.utcnow():
            self._add_to_queue(notification)
        
        logger.info(f"Created notification {notification.id} for user {user_id}")
        return notification
    
    def send_notification(
        self,
        notification_id: int,
        force: bool = False
    ) -> Notification:
        """
        Send a notification immediately.
        
        Args:
            notification_id: Notification ID
            force: Force send even if user has opted out
            
        Returns:
            Updated notification
            
        Raises:
            NotificationNotFoundException: If notification not found
            NotificationDeliveryException: If delivery fails
        """
        notification = self.get_or_fail(notification_id)
        
        if notification.status != NotificationStatus.PENDING and not force:
            raise InvalidNotificationStateException(
                notification_id,
                notification.status,
                "send"
            )
        
        # Check user preferences (unless forced)
        if not force:
            if not self._check_user_preferences(
                notification.user_id,
                notification.notification_type,
                notification.channel
            ):
                notification.status = NotificationStatus.SUPPRESSED
                notification.suppression_reason = SuppressionReason.OPTED_OUT
                self.session.flush()
                raise UserOptedOutException(notification.user_id, notification.channel)
        
        # Check rate limits
        try:
            self._check_rate_limits(notification.user_id, notification.channel)
        except RateLimitExceededException as e:
            notification.status = NotificationStatus.FAILED
            notification.failure_reason = str(e)
            notification.metadata = notification.metadata or {}
            notification.metadata['rate_limit'] = {
                'limit': e.limit,
                'reset_at': e.reset_at.isoformat()
            }
            self.session.flush()
            raise
        
        # Send via appropriate channel
        try:
            provider_response = self._send_via_channel(notification)
            
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.utcnow()
            notification.provider_response = provider_response
            notification.retry_count = 0
            
            # Create log entry
            self._create_notification_log(notification, 'sent', provider_response)
            
            logger.info(f"Sent notification {notification_id} via {notification.channel.value}")
            
        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.failure_reason = str(e)
            notification.retry_count = (notification.retry_count or 0) + 1
            
            # Create log entry
            self._create_notification_log(notification, 'failed', {'error': str(e)})
            
            # Schedule retry if applicable
            if notification.retry_count < self.max_retries:
                self._schedule_retry(notification)
            
            logger.error(f"Failed to send notification {notification_id}: {e}")
            raise NotificationDeliveryException(str(e), notification.channel)
        
        self.session.flush()
        return notification
    
    def send_bulk_notifications(
        self,
        user_ids: List[int],
        notification_type: NotificationType,
        channel: NotificationChannel,
        template_id: Optional[int] = None,
        template_data: Optional[Dict] = None,
        subject: Optional[str] = None,
        content: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        batch_size: int = 100
    ) -> NotificationBatch:
        """
        Send bulk notifications to multiple users.
        
        Args:
            user_ids: List of user IDs
            notification_type: Type of notification
            channel: Delivery channel
            template_id: Optional template ID
            template_data: Optional template data
            subject: Optional subject
            content: Optional content
            priority: Notification priority
            batch_size: Size of processing batches
            
        Returns:
            Created notification batch
        """
        # Create batch record
        batch = NotificationBatch(
            batch_id=str(uuid4()),
            notification_type=notification_type,
            channel=channel,
            template_id=template_id,
            total_recipients=len(user_ids),
            status='pending',
            created_at=datetime.utcnow()
        )
        
        self.session.add(batch)
        self.session.flush()
        
        # Create notifications in batches
        for i in range(0, len(user_ids), batch_size):
            batch_user_ids = user_ids[i:i + batch_size]
            
            for user_id in batch_user_ids:
                try:
                    notification = self.create_notification(
                        user_id=user_id,
                        notification_type=notification_type,
                        channel=channel,
                        subject=subject,
                        content=content,
                        template_id=template_id,
                        template_data=template_data,
                        priority=priority,
                        metadata={'batch_id': batch.id}
                    )
                    
                    batch.processed_count += 1
                    
                except Exception as e:
                    batch.failed_count += 1
                    logger.error(f"Failed to create notification for user {user_id}: {e}")
            
            self.session.flush()
        
        batch.completed_at = datetime.utcnow()
        batch.status = 'completed'
        self.session.flush()
        
        logger.info(f"Created bulk notification batch {batch.id} for {len(user_ids)} users")
        return batch
    
    def mark_as_delivered(
        self,
        notification_id: int,
        delivery_details: Optional[Dict] = None
    ) -> Notification:
        """
        Mark a notification as delivered.
        
        Args:
            notification_id: Notification ID
            delivery_details: Optional delivery details
            
        Returns:
            Updated notification
        """
        notification = self.get_or_fail(notification_id)
        
        notification.status = NotificationStatus.DELIVERED
        notification.delivered_at = datetime.utcnow()
        notification.delivery_details = delivery_details
        
        self._create_notification_log(notification, 'delivered', delivery_details)
        
        self.session.flush()
        
        logger.info(f"Marked notification {notification_id} as delivered")
        return notification
    
    def mark_as_opened(
        self,
        notification_id: int,
        open_details: Optional[Dict] = None
    ) -> Notification:
        """
        Mark a notification as opened.
        
        Args:
            notification_id: Notification ID
            open_details: Optional open details
            
        Returns:
            Updated notification
        """
        notification = self.get_or_fail(notification_id)
        
        notification.status = NotificationStatus.OPENED
        notification.opened_at = datetime.utcnow()
        notification.open_details = open_details
        
        self._create_notification_log(notification, 'opened', open_details)
        
        self.session.flush()
        
        logger.info(f"Marked notification {notification_id} as opened")
        return notification
    
    def mark_as_clicked(
        self,
        notification_id: int,
        click_details: Optional[Dict] = None
    ) -> Notification:
        """
        Mark a notification as clicked.
        
        Args:
            notification_id: Notification ID
            click_details: Optional click details
            
        Returns:
            Updated notification
        """
        notification = self.get_or_fail(notification_id)
        
        notification.status = NotificationStatus.CLICKED
        notification.clicked_at = datetime.utcnow()
        notification.click_details = click_details
        
        self._create_notification_log(notification, 'clicked', click_details)
        
        self.session.flush()
        
        logger.info(f"Marked notification {notification_id} as clicked")
        return notification
    
    def mark_as_bounced(
        self,
        notification_id: int,
        bounce_reason: str,
        bounce_details: Optional[Dict] = None
    ) -> Notification:
        """
        Mark a notification as bounced (permanent failure).
        
        Args:
            notification_id: Notification ID
            bounce_reason: Reason for bounce
            bounce_details: Optional bounce details
            
        Returns:
            Updated notification
        """
        notification = self.get_or_fail(notification_id)
        
        notification.status = NotificationStatus.BOUNCED
        notification.bounced_at = datetime.utcnow()
        notification.bounce_reason = bounce_reason
        notification.bounce_details = bounce_details
        
        # Update user preferences to suppress future notifications
        self._update_suppression(
            notification.user_id,
            notification.channel,
            SuppressionReason.BOUNCED,
            bounce_details
        )
        
        self._create_notification_log(notification, 'bounced', {
            'reason': bounce_reason,
            'details': bounce_details
        })
        
        self.session.flush()
        
        logger.warning(f"Notification {notification_id} bounced: {bounce_reason}")
        return notification
    
    # ========================================================================
    # Template Management
    # ========================================================================
    
    def create_template(
        self,
        name: str,
        template_type: TemplateType,
        subject_template: Optional[str] = None,
        content_template: str,
        channel: NotificationChannel,
        language: Language = Language.EN,
        **kwargs
    ) -> NotificationTemplate:
        """
        Create a notification template.
        
        Args:
            name: Template name
            template_type: Type of template
            subject_template: Optional subject template (for email)
            content_template: Content template
            channel: Target channel
            language: Template language
            **kwargs: Additional template attributes
            
        Returns:
            Created template
        """
        # Check for duplicate name
        existing = (
            self.session.query(NotificationTemplate)
            .filter(NotificationTemplate.name == name)
            .first()
        )
        
        if existing:
            raise DuplicateEntityException("NotificationTemplate", "name", name)
        
        # Validate template syntax
        self._validate_template(content_template)
        if subject_template:
            self._validate_template(subject_template)
        
        template = NotificationTemplate(
            name=name,
            template_type=template_type,
            subject_template=subject_template,
            content_template=content_template,
            channel=channel,
            language=language,
            is_active=True,
            version=1,
            created_at=datetime.utcnow(),
            **kwargs
        )
        
        self.session.add(template)
        self.session.flush()
        
        logger.info(f"Created notification template {template.id}: {name}")
        return template
    
    def update_template(
        self,
        template_id: int,
        **updates
    ) -> NotificationTemplate:
        """
        Update a notification template (creates new version).
        
        Args:
            template_id: Template ID
            **updates: Fields to update
            
        Returns:
            Updated template (new version)
        """
        template = self.session.query(NotificationTemplate).get(template_id)
        if not template:
            raise TemplateNotFoundException(template_id)
        
        # Create new version
        new_template = NotificationTemplate(
            name=updates.get('name', template.name),
            template_type=updates.get('template_type', template.template_type),
            subject_template=updates.get('subject_template', template.subject_template),
            content_template=updates.get('content_template', template.content_template),
            channel=updates.get('channel', template.channel),
            language=updates.get('language', template.language),
            description=updates.get('description', template.description),
            is_active=True,
            version=template.version + 1,
            created_at=datetime.utcnow(),
            deprecated_template_id=template_id
        )
        
        # Validate templates
        self._validate_template(new_template.content_template)
        if new_template.subject_template:
            self._validate_template(new_template.subject_template)
        
        # Deactivate old template
        template.is_active = False
        template.deprecated_at = datetime.utcnow()
        
        self.session.add(new_template)
        self.session.flush()
        
        logger.info(f"Updated template {template_id} to version {new_template.version}")
        return new_template
    
    def get_template_by_name(
        self,
        name: str,
        language: Language = Language.EN,
        channel: Optional[NotificationChannel] = None
    ) -> Optional[NotificationTemplate]:
        """
        Get active template by name.
        
        Args:
            name: Template name
            language: Language
            channel: Optional channel filter
            
        Returns:
            Template if found
        """
        query = self.session.query(NotificationTemplate).filter(
            NotificationTemplate.name == name,
            NotificationTemplate.language == language,
            NotificationTemplate.is_active == True
        )
        
        if channel:
            query = query.filter(NotificationTemplate.channel == channel)
        
        return query.order_by(desc(NotificationTemplate.version)).first()
    
    def render_template(
        self,
        template_id: int,
        data: Dict[str, Any],
        channel: NotificationChannel
    ) -> Tuple[Optional[str], str]:
        """
        Render a template with data.
        
        Args:
            template_id: Template ID
            data: Template data
            channel: Target channel
            
        Returns:
            Tuple of (subject, content)
        """
        return self._render_template(template_id, data, channel)
    
    # ========================================================================
    # User Preferences
    # ========================================================================
    
    def get_user_preferences(self, user_id: int) -> NotificationPreference:
        """
        Get notification preferences for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            User's notification preferences
        """
        preferences = (
            self.session.query(NotificationPreference)
            .filter(NotificationPreference.user_id == user_id)
            .first()
        )
        
        if not preferences:
            # Create default preferences
            preferences = NotificationPreference(
                user_id=user_id,
                email_enabled=True,
                sms_enabled=False,
                push_enabled=True,
                whatsapp_enabled=False,
                notification_frequency=Frequency.IMMEDIATE,
                quiet_hours_start=None,
                quiet_hours_end=None,
                created_at=datetime.utcnow()
            )
            self.session.add(preferences)
            self.session.flush()
        
        return preferences
    
    def update_user_preferences(
        self,
        user_id: int,
        **preferences
    ) -> NotificationPreference:
        """
        Update notification preferences for a user.
        
        Args:
            user_id: User ID
            **preferences: Preference fields to update
            
        Returns:
            Updated preferences
        """
        user_prefs = self.get_user_preferences(user_id)
        
        for key, value in preferences.items():
            if hasattr(user_prefs, key):
                setattr(user_prefs, key, value)
        
        user_prefs.updated_at = datetime.utcnow()
        self.session.flush()
        
        logger.info(f"Updated notification preferences for user {user_id}")
        return user_prefs
    
    def opt_out(
        self,
        user_id: int,
        channel: NotificationChannel,
        reason: Optional[str] = None
    ) -> NotificationPreference:
        """
        Opt a user out of a notification channel.
        
        Args:
            user_id: User ID
            channel: Channel to opt out of
            reason: Optional reason
            
        Returns:
            Updated preferences
        """
        user_prefs = self.get_user_preferences(user_id)
        
        # Disable the specific channel
        channel_map = {
            NotificationChannel.EMAIL: 'email_enabled',
            NotificationChannel.SMS: 'sms_enabled',
            NotificationChannel.PUSH: 'push_enabled',
            NotificationChannel.WHATSAPP: 'whatsapp_enabled'
        }
        
        if channel in channel_map:
            setattr(user_prefs, channel_map[channel], False)
        
        # Record opt-out
        if not user_prefs.opt_outs:
            user_prefs.opt_outs = []
        
        user_prefs.opt_outs.append({
            'channel': channel.value,
            'reason': reason,
            'opted_out_at': datetime.utcnow().isoformat()
        })
        
        user_prefs.updated_at = datetime.utcnow()
        self.session.flush()
        
        logger.info(f"User {user_id} opted out of {channel.value}")
        return user_prefs
    
    # ========================================================================
    # Device Management
    # ========================================================================
    
    def register_device(
        self,
        user_id: int,
        device_type: DeviceType,
        device_token: str,
        device_name: Optional[str] = None,
        device_model: Optional[str] = None,
        os_version: Optional[str] = None,
        app_version: Optional[str] = None,
        **kwargs
    ) -> Device:
        """
        Register a device for push notifications.
        
        Args:
            user_id: User ID
            device_type: Type of device
            device_token: Device token for push notifications
            device_name: Optional device name
            device_model: Optional device model
            os_version: Optional OS version
            app_version: Optional app version
            **kwargs: Additional device attributes
            
        Returns:
            Registered device
        """
        # Check if device already exists
        device = (
            self.session.query(Device)
            .filter(
                Device.user_id == user_id,
                Device.device_token == device_token
            )
            .first()
        )
        
        if device:
            # Update existing device
            device.device_type = device_type
            device.device_name = device_name
            device.device_model = device_model
            device.os_version = os_version
            device.app_version = app_version
            device.last_active_at = datetime.utcnow()
            device.is_active = True
        else:
            # Create new device
            device = Device(
                user_id=user_id,
                device_type=device_type,
                device_token=device_token,
                device_name=device_name,
                device_model=device_model,
                os_version=os_version,
                app_version=app_version,
                last_active_at=datetime.utcnow(),
                is_active=True,
                **kwargs
            )
            self.session.add(device)
        
        self.session.flush()
        
        # Create device token record
        token = DeviceToken(
            device_id=device.id,
            token=device_token,
            is_valid=True,
            created_at=datetime.utcnow()
        )
        self.session.add(token)
        
        # Create default preferences
        prefs = DevicePreference(
            device_id=device.id,
            notifications_enabled=True,
            created_at=datetime.utcnow()
        )
        self.session.add(prefs)
        
        self.session.flush()
        
        logger.info(f"Registered device {device.id} for user {user_id}")
        return device
    
    def unregister_device(self, user_id: int, device_token: str) -> bool:
        """
        Unregister a device.
        
        Args:
            user_id: User ID
            device_token: Device token
            
        Returns:
            True if unregistered
        """
        device = (
            self.session.query(Device)
            .filter(
                Device.user_id == user_id,
                Device.device_token == device_token,
                Device.is_active == True
            )
            .first()
        )
        
        if device:
            device.is_active = False
            device.unregistered_at = datetime.utcnow()
            
            # Invalidate token
            self.session.query(DeviceToken).filter(
                DeviceToken.device_id == device.id,
                DeviceToken.is_valid == True
            ).update({'is_valid': False})
            
            self.session.flush()
            
            logger.info(f"Unregistered device {device.id} for user {user_id}")
            return True
        
        return False
    
    def get_user_devices(
        self,
        user_id: int,
        device_type: Optional[DeviceType] = None,
        active_only: bool = True
    ) -> List[Device]:
        """
        Get devices for a user.
        
        Args:
            user_id: User ID
            device_type: Optional device type filter
            active_only: Whether to return only active devices
            
        Returns:
            List of devices
        """
        query = self.session.query(Device).filter(Device.user_id == user_id)
        
        if device_type:
            query = query.filter(Device.device_type == device_type)
        
        if active_only:
            query = query.filter(Device.is_active == True)
        
        return query.order_by(desc(Device.last_active_at)).all()
    
    # ========================================================================
    # Webhook Management
    # ========================================================================
    
    def create_webhook(
        self,
        user_id: int,
        url: str,
        events: List[str],
        method: WebhookMethod = WebhookMethod.POST,
        secret: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> Webhook:
        """
        Create a webhook endpoint.
        
        Args:
            user_id: User ID
            url: Webhook URL
            events: List of events to subscribe to
            method: HTTP method
            secret: Optional secret for signature
            description: Optional description
            **kwargs: Additional webhook attributes
            
        Returns:
            Created webhook
        """
        # Generate webhook ID and secret if not provided
        webhook_id = str(uuid4())
        secret = secret or secrets.token_urlsafe(32)
        
        webhook = Webhook(
            webhook_id=webhook_id,
            user_id=user_id,
            url=url,
            events=events,
            method=method,
            secret=secret,
            description=description,
            is_active=True,
            created_at=datetime.utcnow(),
            **kwargs
        )
        
        self.session.add(webhook)
        self.session.flush()
        
        logger.info(f"Created webhook {webhook.id} for user {user_id}")
        return webhook
    
    def update_webhook(
        self,
        webhook_id: int,
        **updates
    ) -> Webhook:
        """
        Update a webhook.
        
        Args:
            webhook_id: Webhook ID
            **updates: Fields to update
            
        Returns:
            Updated webhook
        """
        webhook = self.session.query(Webhook).get(webhook_id)
        if not webhook:
            raise WebhookNotFoundException(webhook_id)
        
        for key, value in updates.items():
            if hasattr(webhook, key):
                setattr(webhook, key, value)
        
        webhook.updated_at = datetime.utcnow()
        self.session.flush()
        
        logger.info(f"Updated webhook {webhook_id}")
        return webhook
    
    def delete_webhook(self, webhook_id: int) -> bool:
        """
        Delete a webhook.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            True if deleted
        """
        webhook = self.session.query(Webhook).get(webhook_id)
        if not webhook:
            return False
        
        webhook.is_active = False
        webhook.deleted_at = datetime.utcnow()
        self.session.flush()
        
        logger.info(f"Deleted webhook {webhook_id}")
        return True
    
    def trigger_webhook(
        self,
        webhook_id: int,
        event: str,
        payload: Dict[str, Any]
    ) -> WebhookDelivery:
        """
        Trigger a webhook with an event.
        
        Args:
            webhook_id: Webhook ID
            event: Event name
            payload: Event payload
            
        Returns:
            Webhook delivery record
        """
        webhook = self.session.query(Webhook).get(webhook_id)
        if not webhook:
            raise WebhookNotFoundException(webhook_id)
        
        if not webhook.is_active:
            raise RepositoryException(f"Webhook {webhook_id} is not active")
        
        if event not in webhook.events:
            raise RepositoryException(f"Webhook {webhook_id} not subscribed to event {event}")
        
        # Create webhook event
        webhook_event = WebhookEvent(
            webhook_id=webhook_id,
            event=event,
            payload=payload,
            created_at=datetime.utcnow()
        )
        self.session.add(webhook_event)
        self.session.flush()
        
        # Generate signature
        signature = self._generate_webhook_signature(webhook.secret, payload)
        
        # Create delivery record
        delivery = WebhookDelivery(
            webhook_id=webhook_id,
            event_id=webhook_event.id,
            url=webhook.url,
            method=webhook.method,
            headers={
                'Content-Type': 'application/json',
                'X-Webhook-Signature': signature,
                'X-Webhook-ID': webhook.webhook_id,
                'X-Webhook-Event': event
            },
            payload=payload,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        self.session.add(delivery)
        self.session.flush()
        
        # Attempt delivery
        try:
            # This would call the actual webhook URL
            response = self._send_webhook(delivery)
            
            delivery.status = 'delivered'
            delivery.response_code = response.get('status_code')
            delivery.response_body = response.get('body')
            delivery.delivered_at = datetime.utcnow()
            
        except Exception as e:
            delivery.status = 'failed'
            delivery.error_message = str(e)
            delivery.failed_at = datetime.utcnow()
            
            # Schedule retry
            if delivery.attempt_count < 3:
                delivery.retry_at = datetime.utcnow() + timedelta(minutes=5 ** delivery.attempt_count)
            
            logger.error(f"Webhook delivery failed: {e}")
        
        self.session.flush()
        return delivery
    
    def get_webhook_deliveries(
        self,
        webhook_id: int,
        limit: int = 50
    ) -> List[WebhookDelivery]:
        """
        Get delivery history for a webhook.
        
        Args:
            webhook_id: Webhook ID
            limit: Maximum number to return
            
        Returns:
            List of webhook deliveries
        """
        return (
            self.session.query(WebhookDelivery)
            .filter(WebhookDelivery.webhook_id == webhook_id)
            .order_by(desc(WebhookDelivery.created_at))
            .limit(limit)
            .all()
        )
    
    # ========================================================================
    # Campaign Management
    # ========================================================================
    
    def create_campaign(
        self,
        name: str,
        notification_type: NotificationType,
        channel: NotificationChannel,
        template_id: Optional[int] = None,
        subject: Optional[str] = None,
        content: Optional[str] = None,
        target_audience: Optional[Dict] = None,
        scheduled_start: Optional[datetime] = None,
        scheduled_end: Optional[datetime] = None,
        **kwargs
    ) -> Campaign:
        """
        Create a notification campaign.
        
        Args:
            name: Campaign name
            notification_type: Type of notification
            channel: Delivery channel
            template_id: Optional template ID
            subject: Optional subject
            content: Optional content
            target_audience: Optional audience targeting rules
            scheduled_start: Optional start time
            scheduled_end: Optional end time
            **kwargs: Additional campaign attributes
            
        Returns:
            Created campaign
        """
        campaign = Campaign(
            name=name,
            notification_type=notification_type,
            channel=channel,
            template_id=template_id,
            subject=subject,
            content=content,
            target_audience=target_audience or {},
            status=CampaignStatus.DRAFT,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            created_at=datetime.utcnow(),
            **kwargs
        )
        
        self.session.add(campaign)
        self.session.flush()
        
        logger.info(f"Created campaign {campaign.id}: {name}")
        return campaign
    
    def launch_campaign(
        self,
        campaign_id: int,
        send_immediately: bool = False
    ) -> Campaign:
        """
        Launch a campaign.
        
        Args:
            campaign_id: Campaign ID
            send_immediately: Whether to send immediately
            
        Returns:
            Updated campaign
        """
        campaign = self.session.query(Campaign).get(campaign_id)
        if not campaign:
            raise CampaignNotFoundException(campaign_id)
        
        if campaign.status != CampaignStatus.DRAFT:
            raise InvalidCampaignStateException(
                campaign_id,
                campaign.status,
                "launch"
            )
        
        # Get target audience
        user_ids = self._get_target_audience(campaign.target_audience)
        
        if not user_ids:
            campaign.status = CampaignStatus.COMPLETED
            campaign.completed_at = datetime.utcnow()
            campaign.metadata = campaign.metadata or {}
            campaign.metadata['note'] = 'No recipients in target audience'
            self.session.flush()
            return campaign
        
        campaign.status = CampaignStatus.SENDING
        campaign.launched_at = datetime.utcnow()
        campaign.total_recipients = len(user_ids)
        
        self.session.flush()
        
        if send_immediately:
            # Send immediately
            self._send_campaign(campaign, user_ids)
        else:
            # Queue for sending
            self._queue_campaign(campaign, user_ids)
        
        logger.info(f"Launched campaign {campaign_id} to {len(user_ids)} recipients")
        return campaign
    
    def pause_campaign(self, campaign_id: int) -> Campaign:
        """
        Pause a campaign.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            Updated campaign
        """
        campaign = self.session.query(Campaign).get(campaign_id)
        if not campaign:
            raise CampaignNotFoundException(campaign_id)
        
        if campaign.status != CampaignStatus.SENDING:
            raise InvalidCampaignStateException(
                campaign_id,
                campaign.status,
                "pause"
            )
        
        campaign.status = CampaignStatus.PAUSED
        campaign.paused_at = datetime.utcnow()
        self.session.flush()
        
        logger.info(f"Paused campaign {campaign_id}")
        return campaign
    
    def resume_campaign(self, campaign_id: int) -> Campaign:
        """
        Resume a paused campaign.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            Updated campaign
        """
        campaign = self.session.query(Campaign).get(campaign_id)
        if not campaign:
            raise CampaignNotFoundException(campaign_id)
        
        if campaign.status != CampaignStatus.PAUSED:
            raise InvalidCampaignStateException(
                campaign_id,
                campaign.status,
                "resume"
            )
        
        campaign.status = CampaignStatus.SENDING
        campaign.resumed_at = datetime.utcnow()
        self.session.flush()
        
        logger.info(f"Resumed campaign {campaign_id}")
        return campaign
    
    def cancel_campaign(self, campaign_id: int) -> Campaign:
        """
        Cancel a campaign.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            Updated campaign
        """
        campaign = self.session.query(Campaign).get(campaign_id)
        if not campaign:
            raise CampaignNotFoundException(campaign_id)
        
        campaign.status = CampaignStatus.CANCELLED
        campaign.cancelled_at = datetime.utcnow()
        self.session.flush()
        
        logger.info(f"Cancelled campaign {campaign_id}")
        return campaign
    
    def get_campaign_analytics(self, campaign_id: int) -> CampaignAnalytics:
        """
        Get analytics for a campaign.
        
        Args:
            campaign_id: Campaign ID
            
        Returns:
            Campaign analytics
        """
        campaign = self.session.query(Campaign).get(campaign_id)
        if not campaign:
            raise CampaignNotFoundException(campaign_id)
        
        analytics = (
            self.session.query(CampaignAnalytics)
            .filter(CampaignAnalytics.campaign_id == campaign_id)
            .first()
        )
        
        if not analytics:
            # Create analytics record
            analytics = CampaignAnalytics(
                campaign_id=campaign_id,
                created_at=datetime.utcnow()
            )
            self.session.add(analytics)
            self.session.flush()
        
        # Update analytics
        self._update_campaign_analytics(analytics)
        
        return analytics
    
    # ========================================================================
    # Digest Management
    # ========================================================================
    
    def create_digest(
        self,
        user_id: int,
        frequency: Frequency,
        notifications: List[int]
    ) -> NotificationDigest:
        """
        Create a digest of notifications.
        
        Args:
            user_id: User ID
            frequency: Digest frequency
            notifications: List of notification IDs
            
        Returns:
            Created digest
        """
        digest = NotificationDigest(
            user_id=user_id,
            frequency=frequency,
            notification_ids=notifications,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        self.session.add(digest)
        self.session.flush()
        
        logger.info(f"Created digest {digest.id} for user {user_id}")
        return digest
    
    def get_pending_digests(
        self,
        frequency: Optional[Frequency] = None,
        limit: int = 100
    ) -> List[NotificationDigest]:
        """
        Get pending digests for processing.
        
        Args:
            frequency: Optional frequency filter
            limit: Maximum number to return
            
        Returns:
            List of pending digests
        """
        query = self.session.query(NotificationDigest).filter(
            NotificationDigest.status == 'pending'
        )
        
        if frequency:
            query = query.filter(NotificationDigest.frequency == frequency)
        
        return query.order_by(NotificationDigest.created_at).limit(limit).all()
    
    def mark_digest_sent(self, digest_id: int) -> NotificationDigest:
        """
        Mark a digest as sent.
        
        Args:
            digest_id: Digest ID
            
        Returns:
            Updated digest
        """
        digest = self.session.query(NotificationDigest).get(digest_id)
        if not digest:
            raise EntityNotFoundException("NotificationDigest", digest_id)
        
        digest.status = 'sent'
        digest.sent_at = datetime.utcnow()
        self.session.flush()
        
        logger.info(f"Marked digest {digest_id} as sent")
        return digest
    
    # ========================================================================
    # Queue Management
    # ========================================================================
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get notification queue statistics.
        
        Returns:
            Dictionary with queue statistics
        """
        now = datetime.utcnow()
        
        pending = self.session.query(func.count(NotificationQueue.id)).filter(
            NotificationQueue.status == 'pending',
            or_(
                NotificationQueue.scheduled_for.is_(None),
                NotificationQueue.scheduled_for <= now
            )
        ).scalar() or 0
        
        processing = self.session.query(func.count(NotificationQueue.id)).filter(
            NotificationQueue.status == 'processing'
        ).scalar() or 0
        
        failed = self.session.query(func.count(NotificationQueue.id)).filter(
            NotificationQueue.status == 'failed'
        ).scalar() or 0
        
        completed_today = self.session.query(func.count(NotificationQueue.id)).filter(
            NotificationQueue.status == 'completed',
            func.date(NotificationQueue.completed_at) == func.current_date()
        ).scalar() or 0
        
        # Average processing time
        avg_time = self.session.query(
            func.avg(
                func.extract('epoch', NotificationQueue.completed_at - NotificationQueue.started_at)
            )
        ).filter(
            NotificationQueue.status == 'completed',
            NotificationQueue.started_at.isnot(None),
            NotificationQueue.completed_at.isnot(None)
        ).scalar() or 0
        
        return {
            'pending': pending,
            'processing': processing,
            'failed': failed,
            'completed_today': completed_today,
            'avg_processing_time_seconds': round(avg_time, 2)
        }
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _generate_notification_id(self) -> str:
        """Generate a unique notification ID."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random = secrets.token_hex(4).upper()
        return f"NOT{timestamp}{random}"
    
    def _check_user_preferences(
        self,
        user_id: int,
        notification_type: NotificationType,
        channel: NotificationChannel
    ) -> bool:
        """Check if user has opted in to this notification type and channel."""
        preferences = self.get_user_preferences(user_id)
        
        # Check channel enabled
        channel_map = {
            NotificationChannel.EMAIL: preferences.email_enabled,
            NotificationChannel.SMS: preferences.sms_enabled,
            NotificationChannel.PUSH: preferences.push_enabled,
            NotificationChannel.WHATSAPP: preferences.whatsapp_enabled
        }
        
        if not channel_map.get(channel, True):
            return False
        
        # Check quiet hours
        if preferences.quiet_hours_start and preferences.quiet_hours_end:
            now = datetime.utcnow().time()
            if preferences.quiet_hours_start <= now <= preferences.quiet_hours_end:
                # In quiet hours, only allow high priority
                return False
        
        # Check if user has suppressed this channel
        if preferences.opt_outs:
            for opt_out in preferences.opt_outs:
                if opt_out.get('channel') == channel.value:
                    return False
        
        return True
    
    def _check_rate_limits(self, user_id: int, channel: NotificationChannel) -> None:
        """
        Check rate limits for a user and channel.
        
        Raises:
            RateLimitExceededException: If rate limit exceeded
        """
        limit_config = self.rate_limits.get(channel)
        if not limit_config:
            return
        
        period = limit_config['period']
        limit = limit_config['limit']
        
        # Count notifications in the last period
        since = datetime.utcnow() - timedelta(seconds=period)
        
        count = (
            self.session.query(func.count(Notification.id))
            .filter(
                Notification.user_id == user_id,
                Notification.channel == channel,
                Notification.created_at >= since
            )
            .scalar() or 0
        )
        
        if count >= limit:
            reset_at = since + timedelta(seconds=period)
            raise RateLimitExceededException(channel, limit, reset_at)
    
    def _render_template(
        self,
        template_id: int,
        data: Dict[str, Any],
        channel: NotificationChannel
    ) -> Tuple[Optional[str], str]:
        """
        Render a template with data.
        
        This is a placeholder - implement actual template rendering with Jinja2 or similar.
        """
        template = self.session.query(NotificationTemplate).get(template_id)
        if not template:
            raise TemplateNotFoundException(template_id)
        
        if template.channel != channel:
            raise ValidationException(
                "NotificationTemplate",
                {"channel": [f"Template is for {template.channel.value}, not {channel.value}"]}
            )
        
        try:
            # Placeholder for actual template rendering
            # In production, use Jinja2 or similar
            subject = template.subject_template
            content = template.content_template
            
            # Simple variable substitution
            for key, value in data.items():
                placeholder = f"{{{{ {key} }}}}"
                if subject:
                    subject = subject.replace(placeholder, str(value))
                content = content.replace(placeholder, str(value))
            
            return subject, content
            
        except Exception as e:
            raise TemplateRenderException(template_id, str(e))
    
    def _validate_template(self, template: str) -> None:
        """Validate template syntax."""
        # Placeholder - implement template validation
        # Check for balanced braces, valid syntax, etc.
        pass
    
    def _send_via_channel(self, notification: Notification) -> Dict[str, Any]:
        """
        Send notification via appropriate channel.
        
        This is a placeholder - implement actual sending logic for each channel.
        """
        # Placeholder implementation
        # In production, integrate with email/SMS/push providers
        
        channel_handlers = {
            NotificationChannel.EMAIL: self._send_email,
            NotificationChannel.SMS: self._send_sms,
            NotificationChannel.PUSH: self._send_push,
            NotificationChannel.WHATSAPP: self._send_whatsapp,
            NotificationChannel.WEBHOOK: self._send_webhook_notification
        }
        
        handler = channel_handlers.get(notification.channel)
        if handler:
            return handler(notification)
        
        return {'status': 'simulated', 'message_id': str(uuid4())}
    
    def _send_email(self, notification: Notification) -> Dict[str, Any]:
        """Send email notification."""
        # Placeholder for email sending logic
        return {
            'provider': 'ses',
            'message_id': f"email_{secrets.token_hex(8)}",
            'status': 'sent'
        }
    
    def _send_sms(self, notification: Notification) -> Dict[str, Any]:
        """Send SMS notification."""
        # Placeholder for SMS sending logic
        return {
            'provider': 'twilio',
            'message_id': f"sms_{secrets.token_hex(8)}",
            'status': 'sent'
        }
    
    def _send_push(self, notification: Notification) -> Dict[str, Any]:
        """Send push notification."""
        # Placeholder for push notification logic
        return {
            'provider': 'fcm',
            'message_id': f"push_{secrets.token_hex(8)}",
            'status': 'sent'
        }
    
    def _send_whatsapp(self, notification: Notification) -> Dict[str, Any]:
        """Send WhatsApp notification."""
        # Placeholder for WhatsApp sending logic
        return {
            'provider': 'twilio',
            'message_id': f"wa_{secrets.token_hex(8)}",
            'status': 'sent'
        }
    
    def _send_webhook_notification(self, notification: Notification) -> Dict[str, Any]:
        """Send webhook notification."""
        # Placeholder for webhook sending logic
        return {
            'provider': 'webhook',
            'message_id': f"webhook_{secrets.token_hex(8)}",
            'status': 'sent'
        }
    
    def _send_webhook(self, delivery: WebhookDelivery) -> Dict[str, Any]:
        """Send webhook HTTP request."""
        # Placeholder for actual HTTP request
        return {
            'status_code': 200,
            'body': 'OK'
        }
    
    def _generate_webhook_signature(self, secret: str, payload: Dict) -> str:
        """Generate HMAC signature for webhook payload."""
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _add_to_queue(self, notification: Notification) -> NotificationQueue:
        """Add notification to processing queue."""
        queue_item = NotificationQueue(
            notification_id=notification.id,
            status='pending',
            priority=notification.priority,
            created_at=datetime.utcnow()
        )
        
        self.session.add(queue_item)
        self.session.flush()
        
        return queue_item
    
    def _schedule_retry(self, notification: Notification) -> None:
        """Schedule a retry for failed notification."""
        if notification.retry_count >= self.max_retries:
            return
        
        delay = self.retry_delays[notification.retry_count - 1]
        retry_at = datetime.utcnow() + timedelta(seconds=delay)
        
        retry = NotificationRetry(
            notification_id=notification.id,
            attempt=notification.retry_count,
            scheduled_for=retry_at,
            created_at=datetime.utcnow()
        )
        
        self.session.add(retry)
        self.session.flush()
    
    def _create_notification_log(
        self,
        notification: Notification,
        event: str,
        details: Optional[Dict] = None
    ) -> NotificationLog:
        """Create a notification log entry."""
        log = NotificationLog(
            notification_id=notification.id,
            event=event,
            details=details or {},
            created_at=datetime.utcnow()
        )
        
        self.session.add(log)
        self.session.flush()
        
        return log
    
    def _update_suppression(
        self,
        user_id: int,
        channel: NotificationChannel,
        reason: SuppressionReason,
        details: Optional[Dict] = None
    ) -> None:
        """Update user suppression based on delivery failure."""
        preferences = self.get_user_preferences(user_id)
        
        if not preferences.suppressions:
            preferences.suppressions = []
        
        preferences.suppressions.append({
            'channel': channel.value,
            'reason': reason.value,
            'details': details,
            'suppressed_at': datetime.utcnow().isoformat()
        })
        
        # Auto-disable channel for hard bounces
        if reason in [SuppressionReason.BOUNCED, SuppressionReason.INVALID]:
            channel_map = {
                NotificationChannel.EMAIL: 'email_enabled',
                NotificationChannel.SMS: 'sms_enabled',
                NotificationChannel.PUSH: 'push_enabled',
                NotificationChannel.WHATSAPP: 'whatsapp_enabled'
            }
            if channel in channel_map:
                setattr(preferences, channel_map[channel], False)
        
        preferences.updated_at = datetime.utcnow()
        self.session.flush()
    
    def _get_target_audience(self, targeting: Dict) -> List[int]:
        """
        Get user IDs matching targeting criteria.
        
        Args:
            targeting: Targeting rules dictionary
            
        Returns:
            List of user IDs
        """
        query = self.session.query(User.id)
        
        # Apply targeting filters
        if targeting.get('user_status'):
            query = query.filter(User.status.in_(targeting['user_status']))
        
        if targeting.get('user_roles'):
            from ..models.user_models import RoleAssignment, Role
            query = query.join(RoleAssignment).join(Role).filter(
                Role.name.in_(targeting['user_roles'])
            )
        
        if targeting.get('date_joined_after'):
            query = query.filter(User.created_at >= targeting['date_joined_after'])
        
        if targeting.get('date_joined_before'):
            query = query.filter(User.created_at <= targeting['date_joined_before'])
        
        if targeting.get('has_vehicle'):
            from ..models.vehicle_models import VehicleOwnership
            if targeting['has_vehicle']:
                query = query.join(VehicleOwnership).filter(VehicleOwnership.end_date.is_(None))
            else:
                query = query.outerjoin(VehicleOwnership).filter(VehicleOwnership.id.is_(None))
        
        if targeting.get('has_reservation'):
            from ..models.reservation_models import Reservation
            if targeting['has_reservation']:
                query = query.join(Reservation).filter(
                    Reservation.status.in_(targeting.get('reservation_statuses', ['confirmed', 'checked_in']))
                )
        
        if targeting.get('last_active_after'):
            from ..models.user_models import UserSession
            query = query.join(UserSession).filter(
                UserSession.last_activity >= targeting['last_active_after']
            )
        
        return [r[0] for r in query.distinct().all()]
    
    def _send_campaign(self, campaign: Campaign, user_ids: List[int]) -> None:
        """Send campaign immediately."""
        for user_id in user_ids:
            try:
                notification = self.create_notification(
                    user_id=user_id,
                    notification_type=campaign.notification_type,
                    channel=campaign.channel,
                    subject=campaign.subject,
                    content=campaign.content,
                    template_id=campaign.template_id,
                    priority=NotificationPriority.NORMAL,
                    metadata={'campaign_id': campaign.id}
                )
                
                # Create campaign recipient record
                recipient = CampaignRecipient(
                    campaign_id=campaign.id,
                    user_id=user_id,
                    notification_id=notification.id,
                    status='sent'
                )
                self.session.add(recipient)
                
                campaign.sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send campaign to user {user_id}: {e}")
                campaign.failed_count += 1
                
                recipient = CampaignRecipient(
                    campaign_id=campaign.id,
                    user_id=user_id,
                    status='failed',
                    error_message=str(e)
                )
                self.session.add(recipient)
            
            self.session.flush()
        
        campaign.completed_at = datetime.utcnow()
        campaign.status = CampaignStatus.COMPLETED
        self.session.flush()
    
    def _queue_campaign(self, campaign: Campaign, user_ids: List[int]) -> None:
        """Queue campaign for sending."""
        for user_id in user_ids:
            recipient = CampaignRecipient(
                campaign_id=campaign.id,
                user_id=user_id,
                status='queued'
            )
            self.session.add(recipient)
            
            campaign.queued_count += 1
        
        self.session.flush()
    
    def _update_campaign_analytics(self, analytics: CampaignAnalytics) -> None:
        """Update campaign analytics."""
        campaign = analytics.campaign
        
        # Get recipient stats
        recipients = self.session.query(CampaignRecipient).filter(
            CampaignRecipient.campaign_id == campaign.id
        ).all()
        
        analytics.total_recipients = len(recipients)
        analytics.sent_count = sum(1 for r in recipients if r.status == 'sent')
        analytics.delivered_count = sum(1 for r in recipients if r.notification and r.notification.status == NotificationStatus.DELIVERED)
        analytics.opened_count = sum(1 for r in recipients if r.notification and r.notification.status == NotificationStatus.OPENED)
        analytics.clicked_count = sum(1 for r in recipients if r.notification and r.notification.status == NotificationStatus.CLICKED)
        analytics.bounced_count = sum(1 for r in recipients if r.notification and r.notification.status == NotificationStatus.BOUNCED)
        analytics.failed_count = sum(1 for r in recipients if r.status == 'failed')
        
        # Calculate rates
        if analytics.sent_count > 0:
            analytics.delivery_rate = (analytics.delivered_count / analytics.sent_count) * 100
            analytics.open_rate = (analytics.opened_count / analytics.sent_count) * 100
            analytics.click_rate = (analytics.clicked_count / analytics.sent_count) * 100
        
        analytics.updated_at = datetime.utcnow()
        self.session.flush()


# ============================================================================
# Notification Template Repository
# ============================================================================

class NotificationTemplateRepository(BaseRepository[NotificationTemplate, int]):
    """Repository for NotificationTemplate entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, NotificationTemplate)
    
    def get_templates_by_channel(
        self,
        channel: NotificationChannel,
        language: Optional[Language] = None
    ) -> List[NotificationTemplate]:
        """Get templates by channel."""
        query = self.session.query(NotificationTemplate).filter(
            NotificationTemplate.channel == channel,
            NotificationTemplate.is_active == True
        )
        
        if language:
            query = query.filter(NotificationTemplate.language == language)
        
        return query.order_by(NotificationTemplate.name).all()
    
    def get_template_versions(self, template_name: str) -> List[NotificationTemplate]:
        """Get all versions of a template."""
        return (
            self.session.query(NotificationTemplate)
            .filter(NotificationTemplate.name == template_name)
            .order_by(desc(NotificationTemplate.version))
            .all()
        )
    
    def get_templates_needing_review(self, days: int = 30) -> List[NotificationTemplate]:
        """Get templates that haven't been updated recently."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        return (
            self.session.query(NotificationTemplate)
            .filter(NotificationTemplate.updated_at <= cutoff)
            .all()
        )


# ============================================================================
# Notification Log Repository
# ============================================================================

class NotificationLogRepository(BaseRepository[NotificationLog, int]):
    """Repository for NotificationLog entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, NotificationLog)
    
    def get_notification_logs(
        self,
        notification_id: int,
        limit: int = 100
    ) -> List[NotificationLog]:
        """Get logs for a notification."""
        return (
            self.session.query(NotificationLog)
            .filter(NotificationLog.notification_id == notification_id)
            .order_by(NotificationLog.created_at)
            .limit(limit)
            .all()
        )
    
    def get_logs_by_event(
        self,
        event: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[NotificationLog]:
        """Get logs by event type."""
        query = self.session.query(NotificationLog).filter(
            NotificationLog.event == event
        )
        
        if from_date:
            query = query.filter(NotificationLog.created_at >= from_date)
        
        if to_date:
            query = query.filter(NotificationLog.created_at <= to_date)
        
        return query.order_by(desc(NotificationLog.created_at)).all()
    
    def cleanup_old_logs(self, days: int = 90) -> int:
        """Delete logs older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = (
            self.session.query(NotificationLog)
            .filter(NotificationLog.created_at <= cutoff)
            .delete()
        )
        
        self.session.flush()
        return result


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main Repository
    'NotificationRepository',
    'NotificationTemplateRepository',
    'NotificationLogRepository',
    
    # Exceptions
    'NotificationNotFoundException',
    'TemplateNotFoundException',
    'CampaignNotFoundException',
    'WebhookNotFoundException',
    'DeviceNotFoundException',
    'NotificationDeliveryException',
    'TemplateRenderException',
    'RateLimitExceededException',
    'UserOptedOutException',
    'InvalidWebhookSignatureException',
]