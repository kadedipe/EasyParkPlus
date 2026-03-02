"""Notification service for the parking management system.

This module handles all notification-related operations including sending
emails, SMS, push notifications, and managing notification preferences.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union
import logging
import json
import asyncio
from enum import Enum
from string import Template

from ..models.notification import (
    Notification,
    NotificationStatus,
    NotificationChannel,
    NotificationPriority,
    NotificationType,
    NotificationTemplate
)
from ..models.user import User
from ..models.reservation import Reservation
from ..exceptions import (
    NotificationError,
    ResourceNotFoundError,
    ValidationError
)
from ..constants.config import Config

# Configure logging
logger = logging.getLogger(__name__)

# Try importing email libraries
try:
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    logger.warning("Email libraries not available. Email notifications will be disabled.")

# Try importing SMS libraries
try:
    import twilio
    from twilio.rest import Client as TwilioClient
    SMS_AVAILABLE = True
except ImportError:
    SMS_AVAILABLE = False
    logger.warning("Twilio not available. SMS notifications will be disabled.")

# Try importing push notification libraries
try:
    from firebase_admin import messaging, initialize_app
    PUSH_AVAILABLE = True
except ImportError:
    PUSH_AVAILABLE = False
    logger.warning("Firebase not available. Push notifications will be disabled.")

# Try importing template engines
try:
    import jinja2
    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False
    logger.warning("Jinja2 not available. Using string templates.")


class NotificationService:
    """Service for managing notifications."""
    
    def __init__(
        self,
        db_session,
        cache_client=None,
        email_config: Optional[Dict[str, Any]] = None,
        sms_config: Optional[Dict[str, Any]] = None,
        push_config: Optional[Dict[str, Any]] = None,
        template_dir: Optional[str] = None
    ):
        """Initialize notification service.
        
        Args:
            db_session: Database session
            cache_client: Optional cache client
            email_config: Email configuration
            sms_config: SMS configuration (Twilio)
            push_config: Push notification configuration (Firebase)
            template_dir: Directory for notification templates
        """
        self.db = db_session
        self.cache = cache_client
        self.email_config = email_config or {}
        self.sms_config = sms_config or {}
        self.push_config = push_config or {}
        self.template_dir = template_dir
        
        # Initialize providers
        self._init_email()
        self._init_sms()
        self._init_push()
        self._init_templates()
        
        # Queue for batch processing
        self._notification_queue = asyncio.Queue()
        self._batch_size = 100
        self._batch_timeout = 5  # seconds
        
        # Start background processor
        self._processor_task = None
    
    def _init_email(self) -> None:
        """Initialize email provider."""
        if not EMAIL_AVAILABLE:
            self.email_enabled = False
            return
        
        required_fields = ['host', 'port', 'username', 'password']
        self.email_enabled = all(field in self.email_config for field in required_fields)
        
        if self.email_enabled:
            logger.info("Email provider initialized")
        else:
            logger.warning("Email not fully configured")
    
    def _init_sms(self) -> None:
        """Initialize SMS provider (Twilio)."""
        if not SMS_AVAILABLE:
            self.sms_enabled = False
            return
        
        required_fields = ['account_sid', 'auth_token', 'from_number']
        self.sms_enabled = all(field in self.sms_config for field in required_fields)
        
        if self.sms_enabled:
            self.twilio_client = TwilioClient(
                self.sms_config['account_sid'],
                self.sms_config['auth_token']
            )
            logger.info("SMS provider initialized")
        else:
            logger.warning("SMS not fully configured")
    
    def _init_push(self) -> None:
        """Initialize push notification provider (Firebase)."""
        if not PUSH_AVAILABLE:
            self.push_enabled = False
            return
        
        if self.push_config.get('credentials'):
            try:
                initialize_app(self.push_config['credentials'])
                self.push_enabled = True
                logger.info("Push notification provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {e}")
                self.push_enabled = False
        else:
            logger.warning("Push notifications not configured")
            self.push_enabled = False
    
    def _init_templates(self) -> None:
        """Initialize template engine."""
        if JINJA_AVAILABLE and self.template_dir:
            try:
                self.template_env = jinja2.Environment(
                    loader=jinja2.FileSystemLoader(self.template_dir),
                    autoescape=True
                )
                self.use_jinja = True
                logger.info("Jinja2 template engine initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Jinja2: {e}")
                self.use_jinja = False
        else:
            self.use_jinja = False
    
    async def start(self) -> None:
        """Start the notification service background processor."""
        if self._processor_task is None:
            self._processor_task = asyncio.create_task(self._process_batch_queue())
            logger.info("Notification service started")
    
    async def stop(self) -> None:
        """Stop the notification service background processor."""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None
            logger.info("Notification service stopped")
    
    async def send_notification(
        self,
        user_id: int,
        notification_type: Union[NotificationType, str],
        channel: Union[NotificationChannel, str],
        subject: Optional[str] = None,
        content: Optional[str] = None,
        template: Optional[Union[NotificationTemplate, str]] = None,
        template_data: Optional[Dict[str, Any]] = None,
        priority: Union[NotificationPriority, str] = NotificationPriority.NORMAL,
        scheduled_for: Optional[datetime] = None,
        data: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        actions: Optional[List[Dict[str, str]]] = None,
        deep_link: Optional[str] = None
    ) -> Notification:
        """Send a notification to a user.
        
        Args:
            user_id: Recipient user ID
            notification_type: Type of notification
            channel: Delivery channel
            subject: Notification subject/title
            content: Notification content
            template: Template name
            template_data: Data for template rendering
            priority: Priority level
            scheduled_for: Schedule for future delivery
            data: Additional data
            attachments: List of attachments
            actions: List of action buttons
            deep_link: Deep link URL
            
        Returns:
            Created notification
            
        Raises:
            NotificationError: If notification creation fails
            ResourceNotFoundError: If user not found
        """
        # Get user
        user = await self._get_user(user_id)
        if not user:
            raise ResourceNotFoundError("user", user_id)
        
        # Convert string enums
        notification_type = self._parse_notification_type(notification_type)
        channel = self._parse_channel(channel)
        priority = self._parse_priority(priority)
        template = self._parse_template(template) if template else None
        
        # Render content from template if needed
        if template and not content:
            content = await self._render_template(
                template,
                template_data or {},
                channel
            )
        
        # Create notification record
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            channel=channel,
            priority=priority,
            status=NotificationStatus.PENDING,
            template=template,
            subject=subject,
            content=content,
            data=template_data or {},
            scheduled_for=scheduled_for,
            attachments=attachments or [],
            actions=actions or [],
            deep_link=deep_link,
            metadata={
                'user_email': user.email,
                'user_phone': user.phone,
                'user_preferences': user.preferences.get('notifications', {})
            }
        )
        
        # Validate
        is_valid, errors = notification.validate()
        if not is_valid:
            raise ValidationError({"notification": errors})
        
        # Save to database
        self.db.add(notification)
        await self.db.flush()
        
        # Send immediately if not scheduled
        if not scheduled_for or scheduled_for <= datetime.utcnow():
            await self._dispatch_notification(notification)
        else:
            # Queue for scheduled delivery
            await self._schedule_notification(notification)
        
        await self.db.commit()
        await self.db.refresh(notification)
        
        logger.info(f"Notification created: {notification.notification_id} for user {user_id}")
        return notification
    
    async def send_bulk_notifications(
        self,
        user_ids: List[int],
        notification_type: Union[NotificationType, str],
        channel: Union[NotificationChannel, str],
        subject: Optional[str] = None,
        content: Optional[str] = None,
        template: Optional[Union[NotificationTemplate, str]] = None,
        template_data: Optional[Dict[str, Any]] = None,
        priority: Union[NotificationPriority, str] = NotificationPriority.NORMAL,
        batch_size: int = 100
    ) -> List[Notification]:
        """Send bulk notifications to multiple users.
        
        Args:
            user_ids: List of user IDs
            notification_type: Type of notification
            channel: Delivery channel
            subject: Notification subject/title
            content: Notification content
            template: Template name
            template_data: Data for template rendering
            priority: Priority level
            batch_size: Batch size for processing
            
        Returns:
            List of created notifications
        """
        notifications = []
        
        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]
            batch_notifications = []
            
            for user_id in batch:
                try:
                    notification = await self.send_notification(
                        user_id=user_id,
                        notification_type=notification_type,
                        channel=channel,
                        subject=subject,
                        content=content,
                        template=template,
                        template_data=template_data,
                        priority=priority
                    )
                    batch_notifications.append(notification)
                except Exception as e:
                    logger.error(f"Failed to send notification to user {user_id}: {e}")
            
            notifications.extend(batch_notifications)
            
            # Small delay between batches
            if i + batch_size < len(user_ids):
                await asyncio.sleep(0.1)
        
        logger.info(f"Sent {len(notifications)} bulk notifications")
        return notifications
    
    async def _dispatch_notification(self, notification: Notification) -> None:
        """Dispatch notification to appropriate channel.
        
        Args:
            notification: Notification to dispatch
        """
        try:
            if notification.channel == NotificationChannel.EMAIL:
                await self._send_email(notification)
            elif notification.channel == NotificationChannel.SMS:
                await self._send_sms(notification)
            elif notification.channel == NotificationChannel.PUSH:
                await self._send_push(notification)
            elif notification.channel == NotificationChannel.IN_APP:
                await self._send_in_app(notification)
            elif notification.channel == NotificationChannel.WEBHOOK:
                await self._send_webhook(notification)
            elif notification.channel == NotificationChannel.SLACK:
                await self._send_slack(notification)
            elif notification.channel == NotificationChannel.WHATSAPP:
                await self._send_whatsapp(notification)
            else:
                logger.warning(f"Unsupported channel: {notification.channel}")
                notification.mark_as_failed(f"Unsupported channel: {notification.channel}")
                return
            
            notification.mark_as_sent()
            logger.debug(f"Notification {notification.notification_id} dispatched via {notification.channel}")
            
        except Exception as e:
            logger.error(f"Failed to dispatch notification {notification.notification_id}: {e}")
            notification.mark_as_failed(str(e))
            
            # Queue for retry if applicable
            if notification.can_retry:
                await self._queue_for_retry(notification)
    
    async def _send_email(self, notification: Notification) -> None:
        """Send email notification.
        
        Args:
            notification: Notification to send
            
        Raises:
            NotificationError: If email sending fails
        """
        if not self.email_enabled:
            raise NotificationError("Email service not configured")
        
        user = await self._get_user(notification.user_id)
        if not user or not user.email:
            raise NotificationError("User email not available")
        
        # Check user preferences
        if not self._should_send_to_user(user, NotificationChannel.EMAIL, notification.notification_type):
            logger.debug(f"Email suppressed by user preferences for user {user.user_id}")
            return
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = notification.subject or "Notification"
            msg['From'] = self.email_config.get('from_email', 'noreply@parking.com')
            msg['To'] = user.email
            
            # Add plain text version
            text_part = MIMEText(notification.content or '', 'plain')
            msg.attach(text_part)
            
            # Add HTML version if available
            if notification.metadata.get('html_content'):
                html_part = MIMEText(notification.metadata['html_content'], 'html')
                msg.attach(html_part)
            
            # Add attachments
            for attachment in notification.attachments:
                # In a real implementation, you would fetch and attach files
                pass
            
            # Send via SMTP
            await aiosmtplib.send(
                msg,
                hostname=self.email_config['host'],
                port=self.email_config['port'],
                username=self.email_config.get('username'),
                password=self.email_config.get('password'),
                use_tls=self.email_config.get('use_tls', True)
            )
            
            logger.info(f"Email sent to {user.email} for notification {notification.notification_id}")
            
        except Exception as e:
            raise NotificationError(f"Email sending failed: {str(e)}")
    
    async def _send_sms(self, notification: Notification) -> None:
        """Send SMS notification.
        
        Args:
            notification: Notification to send
            
        Raises:
            NotificationError: If SMS sending fails
        """
        if not self.sms_enabled:
            raise NotificationError("SMS service not configured")
        
        user = await self._get_user(notification.user_id)
        if not user or not user.phone:
            raise NotificationError("User phone not available")
        
        # Check user preferences
        if not self._should_send_to_user(user, NotificationChannel.SMS, notification.notification_type):
            logger.debug(f"SMS suppressed by user preferences for user {user.user_id}")
            return
        
        try:
            # Truncate content for SMS
            content = notification.content or ""
            if len(content) > 1600:
                content = content[:1597] + "..."
            
            # Send via Twilio
            message = self.twilio_client.messages.create(
                body=content,
                from_=self.sms_config['from_number'],
                to=user.phone
            )
            
            # Store message SID
            notification.provider_response = {
                'sid': message.sid,
                'status': message.status
            }
            
            logger.info(f"SMS sent to {user.phone} for notification {notification.notification_id}")
            
        except Exception as e:
            raise NotificationError(f"SMS sending failed: {str(e)}")
    
    async def _send_push(self, notification: Notification) -> None:
        """Send push notification.
        
        Args:
            notification: Notification to send
            
        Raises:
            NotificationError: If push sending fails
        """
        if not self.push_enabled:
            raise NotificationError("Push notification service not configured")
        
        user = await self._get_user(notification.user_id)
        if not user:
            raise NotificationError("User not found")
        
        # Check user preferences
        if not self._should_send_to_user(user, NotificationChannel.PUSH, notification.notification_type):
            logger.debug(f"Push suppressed by user preferences for user {user.user_id}")
            return
        
        # Get user's FCM tokens from cache or database
        fcm_tokens = await self._get_user_fcm_tokens(user.user_id)
        if not fcm_tokens:
            logger.debug(f"No FCM tokens for user {user.user_id}")
            return
        
        try:
            # Create message for each token
            for token in fcm_tokens:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=notification.subject or "Notification",
                        body=notification.content or ""
                    ),
                    data=notification.data or {},
                    token=token,
                    android=messaging.AndroidConfig(
                        priority='high' if notification.priority == NotificationPriority.HIGH else 'normal'
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(
                                sound='default',
                                badge=1
                            )
                        )
                    ),
                    webpush=messaging.WebpushConfig(
                        notification=messaging.WebpushNotification(
                            icon='/icon.png',
                            badge='/badge.png'
                        )
                    )
                )
                
                # Send message
                response = messaging.send(message)
                
                # Store response
                notification.provider_response = {
                    'message_id': response
                }
            
            logger.info(f"Push notification sent to user {user.user_id}")
            
        except Exception as e:
            raise NotificationError(f"Push notification failed: {str(e)}")
    
    async def _send_in_app(self, notification: Notification) -> None:
        """Send in-app notification.
        
        Args:
            notification: Notification to send
        """
        # In-app notifications are just stored in database
        # They can be retrieved via API
        notification.delivered_at = datetime.utcnow()
        logger.debug(f"In-app notification stored for user {notification.user_id}")
    
    async def _send_webhook(self, notification: Notification) -> None:
        """Send webhook notification.
        
        Args:
            notification: Notification to send
            
        Raises:
            NotificationError: If webhook sending fails
        """
        user = await self._get_user(notification.user_id)
        if not user:
            raise NotificationError("User not found")
        
        # Get user's webhook URL from preferences
        webhook_url = user.preferences.get('webhook_url')
        if not webhook_url:
            logger.debug(f"No webhook URL for user {user.user_id}")
            return
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook_url,
                    json={
                        'type': notification.notification_type.value,
                        'subject': notification.subject,
                        'content': notification.content,
                        'data': notification.data,
                        'actions': notification.actions,
                        'deep_link': notification.deep_link,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    timeout=10
                ) as response:
                    if response.status >= 400:
                        raise NotificationError(f"Webhook returned {response.status}")
            
            logger.info(f"Webhook sent for user {user.user_id}")
            
        except Exception as e:
            raise NotificationError(f"Webhook failed: {str(e)}")
    
    async def _send_slack(self, notification: Notification) -> None:
        """Send Slack notification.
        
        Args:
            notification: Notification to send
            
        Raises:
            NotificationError: If Slack sending fails
        """
        user = await self._get_user(notification.user_id)
        if not user:
            raise NotificationError("User not found")
        
        # Get Slack webhook from config or user preferences
        webhook_url = self.slack_config.get('webhook_url') or user.preferences.get('slack_webhook')
        if not webhook_url:
            logger.debug(f"No Slack webhook for user {user.user_id}")
            return
        
        try:
            import aiohttp
            
            # Format message for Slack
            color_map = {
                NotificationPriority.LOW: '#good',
                NotificationPriority.NORMAL: '#warning',
                NotificationPriority.HIGH: '#danger',
                NotificationPriority.URGENT: '#danger'
            }
            
            payload = {
                'attachments': [{
                    'color': color_map.get(notification.priority, '#good'),
                    'title': notification.subject or 'Notification',
                    'text': notification.content or '',
                    'fields': [
                        {'title': 'Type', 'value': notification.notification_type.value, 'short': True},
                        {'title': 'Time', 'value': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'), 'short': True}
                    ],
                    'footer': 'Parking Management System',
                    'ts': datetime.utcnow().timestamp()
                }]
            }
            
            # Add actions if any
            if notification.actions:
                payload['attachments'][0]['actions'] = [
                    {
                        'type': 'button',
                        'text': action['text'],
                        'url': action.get('url'),
                        'style': 'primary' if i == 0 else 'default'
                    }
                    for i, action in enumerate(notification.actions)
                ]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status >= 400:
                        raise NotificationError(f"Slack webhook returned {response.status}")
            
            logger.info(f"Slack notification sent for user {user.user_id}")
            
        except Exception as e:
            raise NotificationError(f"Slack notification failed: {str(e)}")
    
    async def _send_whatsapp(self, notification: Notification) -> None:
        """Send WhatsApp notification.
        
        Args:
            notification: Notification to send
            
        Raises:
            NotificationError: If WhatsApp sending fails
        """
        # Similar to SMS but using WhatsApp Business API
        # Implementation depends on provider (Twilio, etc.)
        pass
    
    async def _render_template(
        self,
        template: NotificationTemplate,
        data: Dict[str, Any],
        channel: NotificationChannel
    ) -> str:
        """Render a notification template.
        
        Args:
            template: Template name
            data: Template data
            channel: Target channel
            
        Returns:
            Rendered content
        """
        if self.use_jinja:
            try:
                template_name = f"{template.value}_{channel.value}.html"
                template_obj = self.template_env.get_template(template_name)
                return template_obj.render(**data)
            except Exception as e:
                logger.error(f"Jinja2 template rendering failed: {e}")
                # Fall back to string template
        
        # Simple string template fallback
        try:
            template_str = self._get_string_template(template, channel)
            return Template(template_str).safe_substitute(**data)
        except Exception as e:
            logger.error(f"String template rendering failed: {e}")
            return ""
    
    def _get_string_template(self, template: NotificationTemplate, channel: NotificationChannel) -> str:
        """Get string template for fallback rendering.
        
        Args:
            template: Template name
            channel: Target channel
            
        Returns:
            Template string
        """
        # This would typically load from files or database
        templates = {
            NotificationTemplate.RESERVATION_CONFIRMATION: {
                NotificationChannel.EMAIL: "Your reservation for spot $spot_number on $date has been confirmed.",
                NotificationChannel.SMS: "Reservation confirmed: spot $spot_number on $date",
                NotificationChannel.PUSH: "Reservation confirmed!",
            },
            NotificationTemplate.RESERVATION_REMINDER: {
                NotificationChannel.EMAIL: "Reminder: Your parking reservation for spot $spot_number starts in 2 hours.",
                NotificationChannel.SMS: "Reminder: Parking at spot $spot_number in 2 hours",
                NotificationChannel.PUSH: "Parking reminder in 2 hours",
            },
            # Add more templates as needed
        }
        
        return templates.get(template, {}).get(channel, "")
    
    async def mark_as_read(self, notification_id: int, user_id: int) -> Notification:
        """Mark a notification as read.
        
        Args:
            notification_id: Notification ID
            user_id: User ID
            
        Returns:
            Updated notification
            
        Raises:
            ResourceNotFoundError: If notification not found
            ValidationError: If user doesn't own notification
        """
        notification = await self.get_notification(notification_id)
        if not notification:
            raise ResourceNotFoundError("notification", notification_id)
        
        if notification.user_id != user_id:
            raise ValidationError({"user_id": "Notification does not belong to this user"})
        
        notification.mark_as_read()
        await self.db.commit()
        await self.db.refresh(notification)
        
        return notification
    
    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of notifications marked as read
        """
        result = await self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status.in_([NotificationStatus.SENT, NotificationStatus.DELIVERED])
        ).update({
            'status': NotificationStatus.READ,
            'read_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        await self.db.commit()
        logger.info(f"Marked {result} notifications as read for user {user_id}")
        return result
    
    async def get_user_notifications(
        self,
        user_id: int,
        status: Optional[NotificationStatus] = None,
        notification_type: Optional[NotificationType] = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Notification], int]:
        """Get notifications for a user.
        
        Args:
            user_id: User ID
            status: Filter by status
            notification_type: Filter by type
            unread_only: Only return unread notifications
            limit: Result limit
            offset: Result offset
            
        Returns:
            Tuple of (notifications, total_count)
        """
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        
        if status:
            query = query.filter(Notification.status == status)
        
        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)
        
        if unread_only:
            query = query.filter(
                Notification.status.in_([NotificationStatus.SENT, NotificationStatus.DELIVERED])
            )
        
        total = await query.count()
        notifications = await query.order_by(
            Notification.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        return notifications, total
    
    async def get_unread_count(self, user_id: int) -> int:
        """Get unread notification count for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of unread notifications
        """
        # Try cache first
        if self.cache:
            cached = await self.cache.get(f"user:{user_id}:unread_count")
            if cached is not None:
                return int(cached)
        
        # Query database
        count = await self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.status.in_([NotificationStatus.SENT, NotificationStatus.DELIVERED])
        ).count()
        
        # Cache for 5 minutes
        if self.cache:
            await self.cache.set(f"user:{user_id}:unread_count", count, ex=300)
        
        return count
    
    async def delete_notification(self, notification_id: int, user_id: int) -> None:
        """Delete a notification.
        
        Args:
            notification_id: Notification ID
            user_id: User ID
            
        Raises:
            ResourceNotFoundError: If notification not found
            ValidationError: If user doesn't own notification
        """
        notification = await self.get_notification(notification_id)
        if not notification:
            raise ResourceNotFoundError("notification", notification_id)
        
        if notification.user_id != user_id:
            raise ValidationError({"user_id": "Notification does not belong to this user"})
        
        await self.db.delete(notification)
        await self.db.commit()
        
        logger.info(f"Notification {notification_id} deleted")
    
    async def cleanup_expired(self) -> int:
        """Clean up expired notifications.
        
        Returns:
            Number of notifications cleaned up
        """
        result = await self.db.query(Notification).filter(
            Notification.expires_at < datetime.utcnow(),
            Notification.status != NotificationStatus.EXPIRED
        ).update({
            'status': NotificationStatus.EXPIRED,
            'updated_at': datetime.utcnow()
        })
        
        await self.db.commit()
        logger.info(f"Cleaned up {result} expired notifications")
        return result
    
    async def _schedule_notification(self, notification: Notification) -> None:
        """Schedule a notification for future delivery.
        
        Args:
            notification: Notification to schedule
        """
        # In a real implementation, you might use a task queue like Celery
        delay = (notification.scheduled_for - datetime.utcnow()).total_seconds()
        if delay > 0:
            asyncio.create_task(self._delayed_dispatch(notification, delay))
    
    async def _delayed_dispatch(self, notification: Notification, delay: float) -> None:
        """Dispatch a notification after a delay.
        
        Args:
            notification: Notification to dispatch
            delay: Delay in seconds
        """
        await asyncio.sleep(delay)
        await self._dispatch_notification(notification)
    
    async def _queue_for_retry(self, notification: Notification) -> None:
        """Queue a notification for retry.
        
        Args:
            notification: Notification to retry
        """
        await self._notification_queue.put(notification)
    
    async def _process_batch_queue(self) -> None:
        """Process notifications in batches."""
        while True:
            try:
                batch = []
                start_time = datetime.utcnow()
                
                # Collect batch
                while len(batch) < self._batch_size:
                    try:
                        timeout = self._batch_timeout - (datetime.utcnow() - start_time).total_seconds()
                        if timeout <= 0:
                            break
                        
                        notification = await asyncio.wait_for(
                            self._notification_queue.get(),
                            timeout=timeout
                        )
                        batch.append(notification)
                    except asyncio.TimeoutError:
                        break
                
                # Process batch
                if batch:
                    await self._process_retry_batch(batch)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                await asyncio.sleep(1)
    
    async def _process_retry_batch(self, notifications: List[Notification]) -> None:
        """Process a batch of retry notifications.
        
        Args:
            notifications: List of notifications to retry
        """
        for notification in notifications:
            try:
                notification.increment_retry()
                await self._dispatch_notification(notification)
                await self.db.commit()
            except Exception as e:
                logger.error(f"Retry failed for notification {notification.notification_id}: {e}")
                notification.mark_as_failed(str(e))
                await self.db.commit()
    
    async def get_notification(self, notification_id: int) -> Optional[Notification]:
        """Get notification by ID.
        
        Args:
            notification_id: Notification ID
            
        Returns:
            Notification if found, None otherwise
        """
        # Try cache first
        if self.cache:
            cached = await self.cache.get(f"notification:{notification_id}")
            if cached:
                return Notification.from_dict(cached)
        
        # Get from database
        notification = await self.db.query(Notification).filter(
            Notification.notification_id == notification_id
        ).first()
        
        # Cache result
        if notification and self.cache:
            await self.cache.set(
                f"notification:{notification_id}",
                notification.to_dict(),
                ex=3600  # 1 hour cache
            )
        
        return notification
    
    async def _get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return await self.db.query(User).filter(User.user_id == user_id).first()
    
    async def _get_user_fcm_tokens(self, user_id: int) -> List[str]:
        """Get FCM tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of FCM tokens
        """
        # Try cache first
        if self.cache:
            cached = await self.cache.get(f"user:{user_id}:fcm_tokens")
            if cached:
                return cached
        
        # In a real implementation, you would fetch from a device tokens table
        # This is a placeholder
        tokens = []
        
        # Cache for 1 hour
        if tokens and self.cache:
            await self.cache.set(f"user:{user_id}:fcm_tokens", tokens, ex=3600)
        
        return tokens
    
    def _should_send_to_user(
        self,
        user: User,
        channel: NotificationChannel,
        notification_type: NotificationType
    ) -> bool:
        """Check if notification should be sent based on user preferences.
        
        Args:
            user: User object
            channel: Notification channel
            notification_type: Notification type
            
        Returns:
            True if should send, False otherwise
        """
        preferences = user.preferences.get('notifications', {})
        
        # Check if channel is enabled
        channel_pref = preferences.get(channel.value, {})
        if not channel_pref.get('enabled', True):
            return False
        
        # Check if notification type is enabled for this channel
        types = channel_pref.get('types', [])
        if types and notification_type.value not in types:
            return False
        
        # Check quiet hours
        quiet_hours = channel_pref.get('quiet_hours', {})
        if quiet_hours:
            now = datetime.utcnow().time()
            start = datetime.strptime(quiet_hours.get('start', '22:00'), '%H:%M').time()
            end = datetime.strptime(quiet_hours.get('end', '08:00'), '%H:%M').time()
            
            if start <= end:
                if start <= now <= end:
                    return False
            else:
                if now >= start or now <= end:
                    return False
        
        return True
    
    def _parse_notification_type(self, value: Union[NotificationType, str]) -> NotificationType:
        """Parse notification type from string or enum."""
        if isinstance(value, NotificationType):
            return value
        try:
            return NotificationType(value)
        except ValueError:
            try:
                return NotificationType[value.upper()]
            except KeyError:
                return NotificationType.RESERVATION_CONFIRMATION
    
    def _parse_channel(self, value: Union[NotificationChannel, str]) -> NotificationChannel:
        """Parse channel from string or enum."""
        if isinstance(value, NotificationChannel):
            return value
        try:
            return NotificationChannel(value)
        except ValueError:
            try:
                return NotificationChannel[value.upper()]
            except KeyError:
                return NotificationChannel.IN_APP
    
    def _parse_priority(self, value: Union[NotificationPriority, str]) -> NotificationPriority:
        """Parse priority from string or enum."""
        if isinstance(value, NotificationPriority):
            return value
        try:
            return NotificationPriority(value)
        except ValueError:
            try:
                return NotificationPriority[value.upper()]
            except KeyError:
                return NotificationPriority.NORMAL
    
    def _parse_template(self, value: Union[NotificationTemplate, str]) -> NotificationTemplate:
        """Parse template from string or enum."""
        if isinstance(value, NotificationTemplate):
            return value
        try:
            return NotificationTemplate(value)
        except ValueError:
            try:
                return NotificationTemplate[value.upper()]
            except KeyError:
                return NotificationTemplate.RESERVATION_CONFIRMATION
    
    # Convenience methods for common notification types
    
    async def send_reservation_confirmation(
        self,
        user_id: int,
        reservation: Reservation
    ) -> Notification:
        """Send reservation confirmation notification.
        
        Args:
            user_id: User ID
            reservation: Reservation object
            
        Returns:
            Created notification
        """
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.RESERVATION_CONFIRMATION,
            channel=NotificationChannel.EMAIL,
            template=NotificationTemplate.RESERVATION_CONFIRMATION,
            template_data={
                'reservation_id': reservation.reservation_id,
                'spot_number': reservation.spot.spot_number if reservation.spot else 'N/A',
                'start_time': reservation.start_time.strftime('%B %d, %Y at %I:%M %p'),
                'end_time': reservation.end_time.strftime('%B %d, %Y at %I:%M %p'),
                'amount': reservation.total_amount,
                'license_plate': reservation.license_plate
            },
            priority=NotificationPriority.HIGH,
            deep_link=f"parking://reservations/{reservation.reservation_id}"
        )
    
    async def send_reservation_reminder(
        self,
        user_id: int,
        reservation: Reservation
    ) -> Notification:
        """Send reservation reminder notification.
        
        Args:
            user_id: User ID
            reservation: Reservation object
            
        Returns:
            Created notification
        """
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.RESERVATION_REMINDER,
            channel=NotificationChannel.PUSH,
            template=NotificationTemplate.RESERVATION_REMINDER,
            template_data={
                'spot_number': reservation.spot.spot_number if reservation.spot else 'N/A',
                'start_time': reservation.start_time.strftime('%I:%M %p'),
                'minutes_until': int((reservation.start_time - datetime.utcnow()).total_seconds() / 60)
            },
            priority=NotificationPriority.NORMAL,
            deep_link=f"parking://reservations/{reservation.reservation_id}"
        )
    
    async def send_payment_receipt(
        self,
        user_id: int,
        payment_id: int,
        amount: float,
        invoice_number: str
    ) -> Notification:
        """Send payment receipt notification.
        
        Args:
            user_id: User ID
            payment_id: Payment ID
            amount: Payment amount
            invoice_number: Invoice number
            
        Returns:
            Created notification
        """
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.PAYMENT_RECEIPT,
            channel=NotificationChannel.EMAIL,
            template=NotificationTemplate.PAYMENT_RECEIPT,
            template_data={
                'payment_id': payment_id,
                'amount': amount,
                'invoice_number': invoice_number,
                'date': datetime.utcnow().strftime('%B %d, %Y')
            },
            priority=NotificationPriority.HIGH,
            attachments=[{
                'filename': f'receipt_{invoice_number}.pdf',
                'url': f'/api/payments/{payment_id}/receipt',
                'mime_type': 'application/pdf'
            }]
        )
    
    async def send_waitlist_available(
        self,
        user_id: int,
        spot_id: int,
        spot_number: str
    ) -> Notification:
        """Send waitlist available notification.
        
        Args:
            user_id: User ID
            spot_id: Spot ID
            spot_number: Spot number
            
        Returns:
            Created notification
        """
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.WAITLIST_AVAILABLE,
            channel=NotificationChannel.SMS,
            template=NotificationTemplate.WAITLIST_AVAILABLE,
            template_data={
                'spot_number': spot_number,
                'expires_in': Config.WAITLIST_NOTIFICATION_HOURS
            },
            priority=NotificationPriority.HIGH,
            deep_link=f"parking://spots/{spot_id}"
        )
    
    async def send_account_verification(
        self,
        user_id: int,
        verification_code: str
    ) -> Notification:
        """Send account verification notification.
        
        Args:
            user_id: User ID
            verification_code: Verification code
            
        Returns:
            Created notification
        """
        return await self.send_notification(
            user_id=user_id,
            notification_type=NotificationType.ACCOUNT_VERIFICATION,
            channel=NotificationChannel.EMAIL,
            template=NotificationTemplate.ACCOUNT_VERIFICATION,
            template_data={
                'verification_code': verification_code,
                'expires_in': 24  # hours
            },
            priority=NotificationPriority.HIGH
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on notification service.
        
        Returns:
            Health check results
        """
        return {
            'service': 'notification_service',
            'status': 'healthy',
            'providers': {
                'email': {
                    'enabled': self.email_enabled,
                    'configured': EMAIL_AVAILABLE and bool(self.email_config)
                },
                'sms': {
                    'enabled': self.sms_enabled,
                    'configured': SMS_AVAILABLE and bool(self.sms_config)
                },
                'push': {
                    'enabled': self.push_enabled,
                    'configured': PUSH_AVAILABLE and bool(self.push_config)
                }
            },
            'queue_size': self._notification_queue.qsize(),
            'templates': {
                'jinja_enabled': self.use_jinja,
                'template_dir': self.template_dir
            }
        }