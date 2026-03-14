"""
Push notification consumer.
"""

import asyncio
from typing import Dict, Any, Optional, List
import json
import aiohttp

from .base import BaseConsumer
from ..core.config import settings
from ..utils.logging_utils import get_logger, audit_log
from ..utils.retry import async_retry
from ..core.exceptions import PushNotificationError

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import messaging, credentials
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning("Firebase Admin SDK not available")


class PushConsumer(BaseConsumer):
    """
    Consumer for push notifications.
    """
    
    def __init__(self):
        """Initialize push notification consumer."""
        super().__init__(
            queue_name="push_notifications",
            routing_key="notification.push.*",
            prefetch_count=settings.PUSH_PREFETCH_COUNT
        )
        self.logger = get_logger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self.fcm_app = None
        
        # Initialize FCM if available
        if FIREBASE_AVAILABLE and settings.FCM_CREDENTIALS_PATH:
            self.initialize_fcm()
    
    def initialize_fcm(self) -> None:
        """
        Initialize Firebase Cloud Messaging.
        """
        try:
            cred = credentials.Certificate(settings.FCM_CREDENTIALS_PATH)
            self.fcm_app = firebase_admin.initialize_app(cred)
            self.logger.info("Firebase Cloud Messaging initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize FCM: {e}")
    
    async def connect_http(self) -> None:
        """
        Create HTTP session.
        """
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
            self.logger.debug("HTTP session created")
    
    async def disconnect_http(self) -> None:
        """
        Close HTTP session.
        """
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.debug("HTTP session closed")
    
    async def process_message(self, message: Dict[str, Any]) -> bool:
        """
        Process push notification message.
        
        Expected message format:
        {
            "type": "push",
            "tokens": ["device_token_1", "device_token_2"],
            "topic": "all_users",
            "condition": "'stock' in topics",
            "title": "Notification Title",
            "body": "Notification body text",
            "data": {"key": "value"},
            "image_url": "https://example.com/image.jpg",
            "click_action": "OPEN_ACTIVITY",
            "priority": "high",
            "ttl": 3600,
            "platform": "all",  # all, android, ios, web
            "metadata": {...}
        }
        """
        try:
            push_type = message.get("type")
            tokens = message.get("tokens", [])
            topic = message.get("topic")
            condition = message.get("condition")
            title = message.get("title")
            body = message.get("body")
            data = message.get("data", {})
            image_url = message.get("image_url")
            click_action = message.get("click_action")
            priority = message.get("priority", "normal")
            ttl = message.get("ttl", 3600)
            platform = message.get("platform", "all")
            metadata = message.get("metadata", {})
            
            # Validate required fields
            if not title or not body:
                self.logger.error("Missing title or body for push notification")
                return False
            
            if not tokens and not topic and not condition:
                self.logger.error("No target (tokens, topic, or condition) provided")
                return False
            
            # Connect HTTP session
            await self.connect_http()
            
            # Send based on platform
            results = []
            
            if platform in ["all", "android", "ios"] and FIREBASE_AVAILABLE and self.fcm_app:
                # Use FCM for Android/iOS
                result = await self.send_fcm_notification(
                    tokens=tokens,
                    topic=topic,
                    condition=condition,
                    title=title,
                    body=body,
                    data=data,
                    image_url=image_url,
                    click_action=click_action,
                    priority=priority,
                    ttl=ttl
                )
                results.append(result)
            
            if platform in ["all", "web"]:
                # Use web push for browsers
                if tokens:
                    for token in tokens:
                        result = await self.send_web_push(
                            token=token,
                            title=title,
                            body=body,
                            data=data,
                            image_url=image_url,
                            ttl=ttl
                        )
                        results.append(result)
            
            # Calculate success rate
            success_count = sum(1 for r in results if r.get("success"))
            
            # Log results
            self.logger.info(
                f"Push notifications sent: {success_count}/{len(results)} successful"
            )
            
            # Audit log
            audit_log(
                self.logger,
                action="PUSH_SENT",
                resource="notification",
                details={
                    "type": push_type,
                    "platform": platform,
                    "targets": {
                        "tokens": len(tokens),
                        "topic": topic,
                        "condition": condition
                    },
                    "successful": success_count,
                    "total": len(results),
                    "priority": priority,
                    **metadata
                }
            )
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Failed to process push message: {e}", exc_info=True)
            message["error"] = str(e)
            return False
    
    @async_retry(max_retries=3, delay=1)
    async def send_fcm_notification(
        self,
        tokens: List[str],
        topic: Optional[str],
        condition: Optional[str],
        title: str,
        body: str,
        data: Dict[str, Any],
        image_url: Optional[str],
        click_action: Optional[str],
        priority: str,
        ttl: int
    ) -> Dict[str, Any]:
        """
        Send notification via Firebase Cloud Messaging.
        """
        try:
            # Build message
            message = messaging.Message()
            
            # Set target
            if tokens:
                if len(tokens) == 1:
                    message.token = tokens[0]
                else:
                    # Use multicast for multiple tokens
                    return await self.send_fcm_multicast(
                        tokens, title, body, data, image_url, click_action, priority, ttl
                    )
            elif topic:
                message.topic = topic
            elif condition:
                message.condition = condition
            
            # Set notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            message.notification = notification
            
            # Set data payload
            if data:
                message.data = {str(k): str(v) for k, v in data.items()}
            
            # Set Android config
            android_priority = "high" if priority == "high" else "normal"
            message.android = messaging.AndroidConfig(
                priority=android_priority,
                ttl=ttl,
                notification=messaging.AndroidNotification(
                    click_action=click_action,
                    image=image_url
                )
            )
            
            # Set APNS (iOS) config
            apns_priority = "10" if priority == "high" else "5"
            message.apns = messaging.APNSConfig(
                headers={"apns-priority": apns_priority},
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body
                        ),
                        sound="default",
                        badge=data.get("badge", 1)
                    )
                )
            )
            
            # Send message
            response = messaging.send(message)
            
            return {
                "success": True,
                "message_id": response,
                "provider": "fcm",
                "target": topic or condition or tokens[0] if tokens else None
            }
            
        except Exception as e:
            self.logger.error(f"FCM notification failed: {e}")
            raise
    
    async def send_fcm_multicast(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Dict[str, Any],
        image_url: Optional[str],
        click_action: Optional[str],
        priority: str,
        ttl: int
    ) -> Dict[str, Any]:
        """
        Send multicast notification via FCM.
        """
        try:
            # Build message
            message = messaging.MulticastMessage(
                tokens=tokens,
                notification=messaging.Notification(
                    title=title,
                    body=body,
                    image=image_url
                ),
                data={str(k): str(v) for k, v in data.items()}
            )
            
            # Send multicast
            response = messaging.send_multicast(message)
            
            return {
                "success": response.success_count > 0,
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "provider": "fcm_multicast",
                "responses": [
                    {
                        "token": tokens[i],
                        "success": resp.success,
                        "message_id": resp.message_id if resp.success else None,
                        "error": str(resp.exception) if not resp.success else None
                    }
                    for i, resp in enumerate(response.responses)
                ]
            }
            
        except Exception as e:
            self.logger.error(f"FCM multicast failed: {e}")
            raise
    
    async def send_web_push(
        self,
        token: str,
        title: str,
        body: str,
        data: Dict[str, Any],
        image_url: Optional[str],
        ttl: int
    ) -> Dict[str, Any]:
        """
        Send web push notification.
        """
        try:
            # Parse subscription info from token
            subscription = json.loads(token)
            
            # Prepare payload
            payload = {
                "title": title,
                "body": body,
                "icon": settings.WEB_PUSH_ICON,
                "image": image_url,
                "data": data,
                "badge": settings.WEB_PUSH_BADGE,
                "vibrate": [200, 100, 200],
                "requireInteraction": True
            }
            
            # Send via web push service
            headers = {
                "TTL": str(ttl),
                "Content-Type": "application/json",
                "Authorization": f"key={settings.WEB_PUSH_VAPID_PRIVATE_KEY}"
            }
            
            async with self.session.post(
                subscription["endpoint"],
                json=payload,
                headers=headers
            ) as response:
                if response.status in [201, 202]:
                    return {
                        "success": True,
                        "token": token,
                        "provider": "web_push",
                        "status": response.status
                    }
                else:
                    error_text = await response.text()
                    raise PushNotificationError(f"Web push failed: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"Web push failed: {e}")
            raise
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get push queue statistics.
        
        Returns:
            Dict[str, Any]: Queue statistics
        """
        queue_status = await self.get_queue_status()
        
        return {
            **queue_status,
            "http_connected": self.session and not self.session.closed,
            "fcm_initialized": self.fcm_app is not None,
            "fcm_available": FIREBASE_AVAILABLE
        }
    
    async def stop(self) -> None:
        """Stop consumer and disconnect HTTP."""
        await self.disconnect_http()
        await super().stop()