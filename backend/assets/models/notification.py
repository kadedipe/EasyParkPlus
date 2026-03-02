"""Notification model for the parking management system.

This module defines the Notification model which represents system notifications
sent to users via various channels (email, SMS, push, in-app).
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import json
import uuid

from ..enums import NotificationType


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    SLACK = "slack"
    WHATSAPP = "whatsapp"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class NotificationTemplate(str, Enum):
    """Pre-defined notification templates."""
    RESERVATION_CONFIRMATION = "reservation_confirmation"
    RESERVATION_REMINDER = "reservation_reminder"
    RESERVATION_CANCELLATION = "reservation_cancellation"
    RESERVATION_UPDATE = "reservation_update"
    PAYMENT_RECEIPT = "payment_receipt"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_REFUNDED = "payment_refunded"
    WAITLIST_AVAILABLE = "waitlist_available"
    WAITLIST_CONFIRMED = "waitlist_confirmed"
    ACCOUNT_VERIFICATION = "account_verification"
    ACCOUNT_WELCOME = "account_welcome"
    PASSWORD_RESET = "password_reset"
    PASSWORD_CHANGED = "password_changed"
    EMAIL_VERIFICATION = "email_verification"
    PHONE_VERIFICATION = "phone_verification"
    PROFILE_UPDATE = "profile_update"
    SECURITY_ALERT = "security_alert"
    SUSPICIOUS_LOGIN = "suspicious_login"
    MAINTENANCE_ALERT = "maintenance_alert"
    PROMOTIONAL = "promotional"
    FEEDBACK_REQUEST = "feedback_request"
    REVIEW_REMINDER = "review_reminder"


class Notification:
    """Notification model representing a message sent to a user.
    
    A notification can be delivered through multiple channels and tracks
    its entire lifecycle from creation to delivery and read status.
    
    Attributes:
        notification_id: Unique identifier for the notification
        user_id: ID of the recipient user
        notification_type: Type of notification (from constants)
        channel: Delivery channel (email, SMS, push, etc.)
        priority: Priority level of the notification
        status: Current delivery status
        template: Template name if using templates
        subject: Notification subject/title
        content: Notification body content
        data: Additional data for template rendering
        scheduled_for: When to send the notification (for scheduling)
        sent_at: When the notification was sent
        delivered_at: When the notification was delivered
        read_at: When the user read the notification
        created_at: When the notification was created
        updated_at: When the notification was last updated
        expires_at: When the notification expires
        retry_count: Number of delivery attempts
        max_retries: Maximum number of retry attempts
        error_message: Error message if delivery failed
        provider_response: Response from delivery provider
        metadata: Additional metadata
        attachments: List of attachment URLs or data
        actions: List of action buttons/links
        deep_link: Deep link URL for mobile apps
    """
    
    def __init__(
        self,
        notification_id: Optional[int] = None,
        user_id: int = 0,
        notification_type: NotificationType = NotificationType.RESERVATION_CONFIRMATION,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        status: NotificationStatus = NotificationStatus.PENDING,
        template: Optional[NotificationTemplate] = None,
        subject: Optional[str] = None,
        content: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        scheduled_for: Optional[datetime] = None,
        sent_at: Optional[datetime] = None,
        delivered_at: Optional[datetime] = None,
        read_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        retry_count: int = 0,
        max_retries: int = 3,
        error_message: Optional[str] = None,
        provider_response: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        deep_link: Optional[str] = None,
    ):
        """Initialize a new Notification instance.
        
        Args:
            notification_id: Unique identifier
            user_id: Recipient user ID
            notification_type: Type of notification
            channel: Delivery channel
            priority: Priority level
            status: Delivery status
            template: Template name
            subject: Subject/title
            content: Body content
            data: Template data
            scheduled_for: Scheduled send time
            sent_at: Sent timestamp
            delivered_at: Delivered timestamp
            read_at: Read timestamp
            created_at: Creation timestamp
            updated_at: Update timestamp
            expires_at: Expiration timestamp
            retry_count: Number of retry attempts
            max_retries: Maximum retry attempts
            error_message: Error message
            provider_response: Provider response
            metadata: Additional metadata
            attachments: List of attachments
            actions: List of action buttons
            deep_link: Deep link URL
        """
        self.notification_id = notification_id
        self.user_id = user_id
        self.notification_type = notification_type
        self.channel = channel
        self.priority = priority
        self.status = status
        self.template = template
        self.subject = subject
        self.content = content
        self.data = data or {}
        self.scheduled_for = scheduled_for
        self.sent_at = sent_at
        self.delivered_at = delivered_at
        self.read_at = read_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at
        self.expires_at = expires_at or (datetime.utcnow() + timedelta(days=7))
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.error_message = error_message
        self.provider_response = provider_response or {}
        self.metadata = metadata or {}
        self.attachments = attachments or []
        self.actions = actions or []
        self.deep_link = deep_link
        
        # Generate tracking ID for analytics
        self.tracking_id = str(uuid.uuid4())
    
    def __repr__(self) -> str:
        """String representation of the notification."""
        return f"<Notification {self.notification_id}: {self.notification_type.value} to user {self.user_id}>"
    
    def __str__(self) -> str:
        """User-friendly string representation."""
        return f"Notification: {self.subject or self.notification_type.value}"
    
    @property
    def is_pending(self) -> bool:
        """Check if notification is pending delivery."""
        return self.status == NotificationStatus.PENDING
    
    @property
    def is_sent(self) -> bool:
        """Check if notification has been sent."""
        return self.status in [NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.READ]
    
    @property
    def is_delivered(self) -> bool:
        """Check if notification has been delivered."""
        return self.status in [NotificationStatus.DELIVERED, NotificationStatus.READ]
    
    @property
    def is_read(self) -> bool:
        """Check if notification has been read."""
        return self.status == NotificationStatus.READ
    
    @property
    def is_failed(self) -> bool:
        """Check if notification delivery failed."""
        return self.status == NotificationStatus.FAILED
    
    @property
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        return (
            self.status == NotificationStatus.EXPIRED or
            (self.expires_at and datetime.utcnow() > self.expires_at)
        )
    
    @property
    def is_scheduled(self) -> bool:
        """Check if notification is scheduled for future delivery."""
        return (
            self.scheduled_for is not None and
            self.scheduled_for > datetime.utcnow() and
            self.status == NotificationStatus.PENDING
        )
    
    @property
    def time_to_live(self) -> Optional[timedelta]:
        """Get time remaining before notification expires."""
        if self.expires_at:
            remaining = self.expires_at - datetime.utcnow()
            return remaining if remaining.total_seconds() > 0 else timedelta(0)
        return None
    
    @property
    def can_retry(self) -> bool:
        """Check if notification can be retried."""
        return (
            self.status == NotificationStatus.FAILED and
            self.retry_count < self.max_retries and
            not self.is_expired
        )
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate the notification data.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        if not self.user_id:
            errors.append("User ID is required")
        
        if not self.notification_type:
            errors.append("Notification type is required")
        
        # Check content based on channel
        if self.channel == NotificationChannel.EMAIL:
            if not self.subject:
                errors.append("Subject is required for email notifications")
            if not self.content and not self.template:
                errors.append("Content or template is required for email notifications")
        
        elif self.channel == NotificationChannel.SMS:
            if not self.content:
                errors.append("Content is required for SMS notifications")
            elif len(self.content) > 1600:
                errors.append("SMS content exceeds 1600 character limit")
        
        elif self.channel == NotificationChannel.PUSH:
            if not self.subject and not self.content:
                errors.append("Title or content is required for push notifications")
        
        # Validate scheduled time
        if self.scheduled_for and self.scheduled_for < datetime.utcnow():
            errors.append("Scheduled time cannot be in the past")
        
        # Validate expiration
        if self.expires_at and self.expires_at < self.created_at:
            errors.append("Expiration date cannot be before creation date")
        
        # Validate retry count
        if self.retry_count < 0:
            errors.append("Retry count cannot be negative")
        if self.max_retries < 0:
            errors.append("Max retries cannot be negative")
        if self.retry_count > self.max_retries:
            errors.append("Retry count cannot exceed max retries")
        
        # Validate actions format
        for action in self.actions:
            if 'text' not in action:
                errors.append("Action missing required 'text' field")
            if 'url' not in action and 'action' not in action:
                errors.append("Action missing either 'url' or 'action' field")
        
        return len(errors) == 0, errors
    
    def mark_as_sent(self, provider_response: Optional[Dict[str, Any]] = None) -> None:
        """Mark notification as sent.
        
        Args:
            provider_response: Optional response from delivery provider
        """
        self.status = NotificationStatus.SENT
        self.sent_at = datetime.utcnow()
        if provider_response:
            self.provider_response = provider_response
        self.updated_at = datetime.utcnow()
    
    def mark_as_delivered(self) -> None:
        """Mark notification as delivered."""
        if self.status == NotificationStatus.SENT:
            self.status = NotificationStatus.DELIVERED
            self.delivered_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
    def mark_as_read(self) -> None:
        """Mark notification as read."""
        if self.status in [NotificationStatus.SENT, NotificationStatus.DELIVERED]:
            self.status = NotificationStatus.READ
            self.read_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
    def mark_as_failed(self, error_message: str, provider_response: Optional[Dict[str, Any]] = None) -> None:
        """Mark notification as failed.
        
        Args:
            error_message: Error message describing the failure
            provider_response: Optional provider response
        """
        self.status = NotificationStatus.FAILED
        self.error_message = error_message
        if provider_response:
            self.provider_response = provider_response
        self.updated_at = datetime.utcnow()
    
    def mark_as_expired(self) -> None:
        """Mark notification as expired."""
        self.status = NotificationStatus.EXPIRED
        self.updated_at = datetime.utcnow()
    
    def increment_retry(self) -> None:
        """Increment retry count for failed notification."""
        self.retry_count += 1
        self.updated_at = datetime.utcnow()
        
        if self.retry_count >= self.max_retries:
            self.status = NotificationStatus.FAILED
    
    def schedule(self, scheduled_time: datetime) -> None:
        """Schedule notification for future delivery.
        
        Args:
            scheduled_time: When to send the notification
        """
        if scheduled_time > datetime.utcnow():
            self.scheduled_for = scheduled_time
            self.status = NotificationStatus.PENDING
            self.updated_at = datetime.utcnow()
    
    def cancel(self) -> None:
        """Cancel a scheduled notification."""
        if self.is_pending or self.is_scheduled:
            self.status = NotificationStatus.CANCELLED
            self.updated_at = datetime.utcnow()
    
    def add_action(self, text: str, url: Optional[str] = None, action: Optional[str] = None) -> None:
        """Add an action button/link to the notification.
        
        Args:
            text: Button text
            url: URL to open (for web)
            action: Action identifier (for in-app)
        """
        action_data = {'text': text}
        if url:
            action_data['url'] = url
        if action:
            action_data['action'] = action
        self.actions.append(action_data)
        self.updated_at = datetime.utcnow()
    
    def add_attachment(self, filename: str, url: str, mime_type: str, size: Optional[int] = None) -> None:
        """Add an attachment to the notification.
        
        Args:
            filename: Name of the file
            url: URL to the attachment
            mime_type: MIME type of the attachment
            size: File size in bytes
        """
        attachment = {
            'filename': filename,
            'url': url,
            'mime_type': mime_type,
        }
        if size:
            attachment['size'] = size
        self.attachments.append(attachment)
        self.updated_at = datetime.utcnow()
    
    def get_rendered_content(self, template_engine: Optional[Any] = None) -> str:
        """Get rendered content using template if available.
        
        Args:
            template_engine: Optional template engine for rendering
            
        Returns:
            Rendered content string
        """
        if self.template and template_engine:
            try:
                template = template_engine.get_template(self.template.value)
                return template.render(**self.data)
            except Exception:
                # Fall back to stored content
                pass
        
        return self.content or ""
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert notification to dictionary.
        
        Args:
            include_sensitive: Whether to include sensitive data
            
        Returns:
            Dictionary representation of the notification
        """
        result = {
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "notification_type": self.notification_type.value if self.notification_type else None,
            "notification_type_display": self.notification_type.name.replace('_', ' ').title() if self.notification_type else None,
            "channel": self.channel.value if self.channel else None,
            "priority": self.priority.value if self.priority else None,
            "status": self.status.value if self.status else None,
            "status_display": self.status.name.replace('_', ' ').title() if self.status else None,
            "template": self.template.value if self.template else None,
            "subject": self.subject,
            "content": self.content,
            "scheduled_for": self.scheduled_for.isoformat() if self.scheduled_for else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_pending": self.is_pending,
            "is_sent": self.is_sent,
            "is_delivered": self.is_delivered,
            "is_read": self.is_read,
            "is_failed": self.is_failed,
            "is_expired": self.is_expired,
            "is_scheduled": self.is_scheduled,
            "time_to_live_seconds": self.time_to_live.total_seconds() if self.time_to_live else None,
            "can_retry": self.can_retry,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "actions": self.actions,
            "attachments": self.attachments,
            "deep_link": self.deep_link,
            "tracking_id": self.tracking_id,
        }
        
        # Include sensitive data only if requested
        if include_sensitive:
            result["data"] = self.data
            result["error_message"] = self.error_message
            result["provider_response"] = self.provider_response
            result["metadata"] = self.metadata
        
        return result
    
    def to_dict_minimal(self) -> Dict[str, Any]:
        """Convert notification to minimal dictionary (for list views).
        
        Returns:
            Minimal dictionary representation of the notification
        """
        return {
            "notification_id": self.notification_id,
            "notification_type": self.notification_type.value if self.notification_type else None,
            "subject": self.subject,
            "content": self.content[:100] + "..." if self.content and len(self.content) > 100 else self.content,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "is_read": self.is_read,
            "priority": self.priority.value if self.priority else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Notification':
        """Create notification from dictionary.
        
        Args:
            data: Dictionary containing notification data
            
        Returns:
            New Notification instance
        """
        # Handle enums
        notification_type = data.get('notification_type')
        if notification_type and isinstance(notification_type, str):
            try:
                notification_type = NotificationType(notification_type)
            except ValueError:
                try:
                    notification_type = NotificationType[notification_type.upper()]
                except KeyError:
                    notification_type = NotificationType.RESERVATION_CONFIRMATION
        
        channel = data.get('channel')
        if channel and isinstance(channel, str):
            try:
                channel = NotificationChannel(channel)
            except ValueError:
                try:
                    channel = NotificationChannel[channel.upper()]
                except KeyError:
                    channel = NotificationChannel.IN_APP
        
        priority = data.get('priority')
        if priority and isinstance(priority, str):
            try:
                priority = NotificationPriority(priority)
            except ValueError:
                try:
                    priority = NotificationPriority[priority.upper()]
                except KeyError:
                    priority = NotificationPriority.NORMAL
        
        status = data.get('status')
        if status and isinstance(status, str):
            try:
                status = NotificationStatus(status)
            except ValueError:
                try:
                    status = NotificationStatus[status.upper()]
                except KeyError:
                    status = NotificationStatus.PENDING
        
        template = data.get('template')
        if template and isinstance(template, str):
            try:
                template = NotificationTemplate(template)
            except ValueError:
                try:
                    template = NotificationTemplate[template.upper()]
                except KeyError:
                    template = None
        
        # Parse datetime fields
        scheduled_for = data.get('scheduled_for')
        if scheduled_for and isinstance(scheduled_for, str):
            try:
                scheduled_for = datetime.fromisoformat(scheduled_for.replace('Z', '+00:00'))
            except ValueError:
                scheduled_for = None
        
        sent_at = data.get('sent_at')
        if sent_at and isinstance(sent_at, str):
            try:
                sent_at = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
            except ValueError:
                sent_at = None
        
        delivered_at = data.get('delivered_at')
        if delivered_at and isinstance(delivered_at, str):
            try:
                delivered_at = datetime.fromisoformat(delivered_at.replace('Z', '+00:00'))
            except ValueError:
                delivered_at = None
        
        read_at = data.get('read_at')
        if read_at and isinstance(read_at, str):
            try:
                read_at = datetime.fromisoformat(read_at.replace('Z', '+00:00'))
            except ValueError:
                read_at = None
        
        created_at = data.get('created_at')
        if created_at and isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = None
        
        updated_at = data.get('updated_at')
        if updated_at and isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except ValueError:
                updated_at = None
        
        expires_at = data.get('expires_at')
        if expires_at and isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except ValueError:
                expires_at = None
        
        return cls(
            notification_id=data.get('notification_id'),
            user_id=data.get('user_id', 0),
            notification_type=notification_type,
            channel=channel,
            priority=priority,
            status=status,
            template=template,
            subject=data.get('subject'),
            content=data.get('content'),
            data=data.get('data'),
            scheduled_for=scheduled_for,
            sent_at=sent_at,
            delivered_at=delivered_at,
            read_at=read_at,
            created_at=created_at,
            updated_at=updated_at,
            expires_at=expires_at,
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            error_message=data.get('error_message'),
            provider_response=data.get('provider_response'),
            metadata=data.get('metadata'),
            attachments=data.get('attachments'),
            actions=data.get('actions'),
            deep_link=data.get('deep_link'),
        )
    
    @classmethod
    def create_welcome_notification(cls, user_id: int, user_name: str) -> 'Notification':
        """Create a welcome notification for new users.
        
        Args:
            user_id: User ID
            user_name: User's name
            
        Returns:
            Welcome notification
        """
        return cls(
            user_id=user_id,
            notification_type=NotificationType.ACCOUNT_VERIFICATION,
            channel=NotificationChannel.IN_APP,
            priority=NotificationPriority.NORMAL,
            template=NotificationTemplate.ACCOUNT_WELCOME,
            subject="Welcome to Parking Management System!",
            content=f"Welcome {user_name}! We're excited to have you on board.",
            data={'user_name': user_name},
        )
    
    @classmethod
    def create_reservation_confirmation(
        cls,
        user_id: int,
        reservation_id: int,
        spot_number: str,
        start_time: datetime,
        end_time: datetime,
        amount: float
    ) -> 'Notification':
        """Create a reservation confirmation notification.
        
        Args:
            user_id: User ID
            reservation_id: Reservation ID
            spot_number: Parking spot number
            start_time: Reservation start time
            end_time: Reservation end time
            amount: Total amount
            
        Returns:
            Reservation confirmation notification
        """
        return cls(
            user_id=user_id,
            notification_type=NotificationType.RESERVATION_CONFIRMATION,
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.HIGH,
            template=NotificationTemplate.RESERVATION_CONFIRMATION,
            subject=f"Reservation Confirmed - Spot {spot_number}",
            data={
                'reservation_id': reservation_id,
                'spot_number': spot_number,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'amount': amount,
            },
        )
    
    @classmethod
    def create_reservation_reminder(
        cls,
        user_id: int,
        reservation_id: int,
        spot_number: str,
        start_time: datetime
    ) -> 'Notification':
        """Create a reservation reminder notification.
        
        Args:
            user_id: User ID
            reservation_id: Reservation ID
            spot_number: Parking spot number
            start_time: Reservation start time
            
        Returns:
            Reservation reminder notification
        """
        return cls(
            user_id=user_id,
            notification_type=NotificationType.RESERVATION_REMINDER,
            channel=NotificationChannel.PUSH,
            priority=NotificationPriority.NORMAL,
            template=NotificationTemplate.RESERVATION_REMINDER,
            subject="Upcoming Reservation Reminder",
            data={
                'reservation_id': reservation_id,
                'spot_number': spot_number,
                'start_time': start_time.isoformat(),
            },
            deep_link=f"parking://reservations/{reservation_id}",
        )
    
    @classmethod
    def create_payment_receipt(
        cls,
        user_id: int,
        payment_id: int,
        amount: float,
        invoice_number: str
    ) -> 'Notification':
        """Create a payment receipt notification.
        
        Args:
            user_id: User ID
            payment_id: Payment ID
            amount: Payment amount
            invoice_number: Invoice number
            
        Returns:
            Payment receipt notification
        """
        return cls(
            user_id=user_id,
            notification_type=NotificationType.PAYMENT_RECEIPT,
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.HIGH,
            template=NotificationTemplate.PAYMENT_RECEIPT,
            subject=f"Payment Receipt - {invoice_number}",
            data={
                'payment_id': payment_id,
                'amount': amount,
                'invoice_number': invoice_number,
            },
            attachments=[{
                'filename': f'receipt_{invoice_number}.pdf',
                'url': f'/api/payments/{payment_id}/receipt',
                'mime_type': 'application/pdf',
            }],
        )
    
    @classmethod
    def create_security_alert(
        cls,
        user_id: int,
        ip_address: str,
        device: str,
        location: Optional[str] = None
    ) -> 'Notification':
        """Create a security alert notification.
        
        Args:
            user_id: User ID
            ip_address: IP address of the login
            device: Device information
            location: Geographic location
            
        Returns:
            Security alert notification
        """
        return cls(
            user_id=user_id,
            notification_type=NotificationType.ACCOUNT_VERIFICATION,
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.URGENT,
            template=NotificationTemplate.SECURITY_ALERT,
            subject="Security Alert: New Login Detected",
            data={
                'ip_address': ip_address,
                'device': device,
                'location': location,
                'time': datetime.utcnow().isoformat(),
            },
        )
    
    @classmethod
    def get_notification_types(cls) -> List[Dict[str, str]]:
        """Get list of available notification types.
        
        Returns:
            List of dictionaries with value and display name
        """
        return [
            {"value": nt.value, "display": nt.name.replace('_', ' ').title()}
            for nt in NotificationType
        ]
    
    @classmethod
    def get_channels(cls) -> List[Dict[str, str]]:
        """Get list of available notification channels.
        
        Returns:
            List of dictionaries with value and display name
        """
        return [
            {"value": nc.value, "display": nc.name.replace('_', ' ').title()}
            for nc in NotificationChannel
        ]
    
    @classmethod
    def get_templates(cls) -> List[Dict[str, str]]:
        """Get list of available notification templates.
        
        Returns:
            List of dictionaries with value and display name
        """
        return [
            {"value": nt.value, "display": nt.name.replace('_', ' ').title()}
            for nt in NotificationTemplate
        ]
    
    def __eq__(self, other: object) -> bool:
        """Check equality with another notification."""
        if not isinstance(other, Notification):
            return False
        return (
            self.notification_id is not None and 
            other.notification_id is not None and 
            self.notification_id == other.notification_id
        )
    
    def __hash__(self) -> int:
        """Hash based on notification_id."""
        return hash(self.notification_id) if self.notification_id else id(self)