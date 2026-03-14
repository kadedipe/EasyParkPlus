"""
Push notification provider implementations with multi-platform support.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import aiohttp
import base64
from cryptography.fernet import Fernet
import py_vapid

try:
    from firebase_admin import messaging, credentials, initialize_app
    from firebase_admin.exceptions import FirebaseError
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning("Firebase Admin SDK not available")

from ..core.config import settings
from ..utils.logging_utils import get_logger
from ..utils.retry import async_retry
from ..core.exceptions import PushProviderError


class PushProvider(ABC):
    """
    Abstract base class for push notification providers.
    """
    
    def __init__(self, name: str):
        """
        Initialize push provider.
        
        Args:
            name: Provider name
        """
        self.name = name
        self.logger = get_logger(f"{name}_provider")
        self.stats = {
            "sent": 0,
            "failed": 0,
            "last_success": None,
            "last_error": None,
            "avg_delivery_time": 0.0,
            "total_devices": 0
        }
    
    @abstractmethod
    async def send_push(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None,
        click_action: Optional[str] = None,
        priority: str = "normal",
        ttl: int = 3600,
        collapse_key: Optional[str] = None,
        mutable_content: bool = False,
        sound: Optional[str] = None,
        badge: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send push notification.
        
        Args:
            tokens: List of device tokens
            title: Notification title
            body: Notification body
            data: Custom data payload
            image_url: Image URL for rich notifications
            click_action: Action when notification is clicked
            priority: Message priority (high, normal, low)
            ttl: Time to live in seconds
            collapse_key: Collapse key for replacing messages
            mutable_content: Allow content modification
            sound: Custom sound file
            badge: Badge number
            metadata: Additional metadata
            
        Returns:
            Dict[str, Any]: Provider response
        """
        pass
    
    @abstractmethod
    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send push notification to topic.
        
        Args:
            topic: Topic name
            title: Notification title
            body: Notification body
            data: Custom data payload
            **kwargs: Additional arguments
            
        Returns:
            Dict[str, Any]: Provider response
        """
        pass
    
    @abstractmethod
    async def send_to_condition(
        self,
        condition: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send push notification based on condition.
        
        Args:
            condition: FCM condition string
            title: Notification title
            body: Notification body
            data: Custom data payload
            **kwargs: Additional arguments
            
        Returns:
            Dict[str, Any]: Provider response
        """
        pass
    
    @abstractmethod
    async def check_health(self) -> bool:
        """
        Check provider health.
        
        Returns:
            bool: True if healthy
        """
        pass
    
    def update_stats(
        self,
        success: bool,
        delivery_time: float,
        device_count: int = 1
    ) -> None:
        """
        Update provider statistics.
        
        Args:
            success: Whether push was sent successfully
            delivery_time: Time taken to deliver
            device_count: Number of devices targeted
        """
        if success:
            self.stats["sent"] += 1
            self.stats["last_success"] = datetime.utcnow().isoformat()
            self.stats["total_devices"] += device_count
            
            # Update average delivery time
            current_avg = self.stats["avg_delivery_time"]
            total_sent = self.stats["sent"]
            self.stats["avg_delivery_time"] = (
                (current_avg * (total_sent - 1) + delivery_time) / total_sent
            )
        else:
            self.stats["failed"] += 1
            self.stats["last_error"] = datetime.utcnow().isoformat()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get provider statistics.
        
        Returns:
            Dict[str, Any]: Provider stats
        """
        success_rate = 0
        if self.stats["sent"] + self.stats["failed"] > 0:
            success_rate = self.stats["sent"] / (self.stats["sent"] + self.stats["failed"])
        
        return {
            "name": self.name,
            **self.stats,
            "success_rate": success_rate,
            "health": success_rate > 0.9  # 90% success rate
        }


class FCMProvider(PushProvider):
    """
    Firebase Cloud Messaging (FCM) provider.
    """
    
    def __init__(
        self,
        credentials_path: Optional[str] = None,
        project_id: Optional[str] = None,
        credentials_dict: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize FCM provider.
        
        Args:
            credentials_path: Path to service account JSON file
            project_id: Firebase project ID
            credentials_dict: Service account credentials as dict
        """
        super().__init__("fcm")
        
        if not FIREBASE_AVAILABLE:
            self.logger.warning("Firebase Admin SDK not available. FCM provider will not work.")
            return
        
        try:
            if credentials_dict:
                cred = credentials.Certificate(credentials_dict)
            elif credentials_path:
                cred = credentials.Certificate(credentials_path)
            else:
                # Use application default credentials
                cred = credentials.ApplicationDefault()
            
            if project_id:
                self.app = initialize_app(cred, {'projectId': project_id})
            else:
                self.app = initialize_app(cred)
            
            self.logger.info("FCM provider initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize FCM: {e}")
            self.app = None
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def send_push(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None,
        click_action: Optional[str] = None,
        priority: str = "normal",
        ttl: int = 3600,
        collapse_key: Optional[str] = None,
        mutable_content: bool = False,
        sound: Optional[str] = None,
        badge: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send push notification via FCM.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self.app:
                raise PushProviderError("FCM not initialized")
            
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Build APNS config for iOS
            apns_config = self._build_apns_config(
                title=title,
                body=body,
                sound=sound,
                badge=badge,
                mutable_content=mutable_content,
                priority=priority
            )
            
            # Build Android config
            android_config = self._build_android_config(
                priority=priority,
                ttl=ttl,
                collapse_key=collapse_key,
                click_action=click_action,
                sound=sound
            )
            
            # Build WebPush config
            webpush_config = self._build_webpush_config(
                title=title,
                body=body,
                icon=metadata.get('icon') if metadata else None,
                click_action=click_action
            )
            
            # Prepare data payload
            data_payload = {}
            if data:
                data_payload = {str(k): str(v) for k, v in data.items()}
            
            if metadata:
                data_payload['_metadata'] = json.dumps(metadata)
            
            if len(tokens) == 1:
                # Single message
                message = messaging.Message(
                    token=tokens[0],
                    notification=notification,
                    data=data_payload,
                    android=android_config,
                    apns=apns_config,
                    webpush=webpush_config
                )
                
                response = messaging.send(message)
                
                delivery_time = asyncio.get_event_loop().time() - start_time
                self.update_stats(True, delivery_time, 1)
                
                return {
                    "provider": self.name,
                    "message_id": response,
                    "status": "sent",
                    "target": "single",
                    "tokens_count": 1,
                    "delivery_time": delivery_time
                }
                
            else:
                # Multicast message
                message = messaging.MulticastMessage(
                    tokens=tokens,
                    notification=notification,
                    data=data_payload,
                    android=android_config,
                    apns=apns_config,
                    webpush=webpush_config
                )
                
                response = messaging.send_multicast(message)
                
                delivery_time = asyncio.get_event_loop().time() - start_time
                self.update_stats(response.success_count > 0, delivery_time, len(tokens))
                
                return {
                    "provider": self.name,
                    "success_count": response.success_count,
                    "failure_count": response.failure_count,
                    "status": "sent" if response.success_count > 0 else "failed",
                    "target": "multicast",
                    "tokens_count": len(tokens),
                    "responses": [
                        {
                            "token": tokens[i],
                            "success": resp.success,
                            "message_id": resp.message_id if resp.success else None,
                            "error": str(resp.exception) if not resp.success else None
                        }
                        for i, resp in enumerate(response.responses)
                    ],
                    "delivery_time": delivery_time
                }
                
        except FirebaseError as e:
            delivery_time = asyncio.get_event_loop().time() - start_time
            self.update_stats(False, delivery_time, len(tokens))
            
            self.logger.error(f"FCM send failed: {e}")
            raise PushProviderError(f"FCM error: {e}")
        
        except Exception as e:
            delivery_time = asyncio.get_event_loop().time() - start_time
            self.update_stats(False, delivery_time, len(tokens))
            
            self.logger.error(f"FCM send failed: {e}")
            raise PushProviderError(f"FCM send failed: {e}")
    
    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send push notification to FCM topic.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self.app:
                raise PushProviderError("FCM not initialized")
            
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=kwargs.get('image_url')
            )
            
            # Prepare data payload
            data_payload = {}
            if data:
                data_payload = {str(k): str(v) for k, v in data.items()}
            
            # Build message
            message = messaging.Message(
                topic=topic,
                notification=notification,
                data=data_payload,
                android=self._build_android_config(**kwargs),
                apns=self._build_apns_config(title=title, body=body, **kwargs),
                webpush=self._build_webpush_config(title=title, body=body, **kwargs)
            )
            
            response = messaging.send(message)
            
            delivery_time = asyncio.get_event_loop().time() - start_time
            self.update_stats(True, delivery_time)
            
            return {
                "provider": self.name,
                "message_id": response,
                "status": "sent",
                "target": "topic",
                "topic": topic,
                "delivery_time": delivery_time
            }
            
        except Exception as e:
            delivery_time = asyncio.get_event_loop().time() - start_time
            self.update_stats(False, delivery_time)
            
            self.logger.error(f"FCM topic send failed: {e}")
            raise PushProviderError(f"FCM topic send failed: {e}")
    
    async def send_to_condition(
        self,
        condition: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send push notification based on condition.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self.app:
                raise PushProviderError("FCM not initialized")
            
            # Build notification
            notification = messaging.Notification(
                title=title,
                body=body,
                image=kwargs.get('image_url')
            )
            
            # Prepare data payload
            data_payload = {}
            if data:
                data_payload = {str(k): str(v) for k, v in data.items()}
            
            # Build message
            message = messaging.Message(
                condition=condition,
                notification=notification,
                data=data_payload,
                android=self._build_android_config(**kwargs),
                apns=self._build_apns_config(title=title, body=body, **kwargs),
                webpush=self._build_webpush_config(title=title, body=body, **kwargs)
            )
            
            response = messaging.send(message)
            
            delivery_time = asyncio.get_event_loop().time() - start_time
            self.update_stats(True, delivery_time)
            
            return {
                "provider": self.name,
                "message_id": response,
                "status": "sent",
                "target": "condition",
                "condition": condition,
                "delivery_time": delivery_time
            }
            
        except Exception as e:
            delivery_time = asyncio.get_event_loop().time() - start_time
            self.update_stats(False, delivery_time)
            
            self.logger.error(f"FCM condition send failed: {e}")
            raise PushProviderError(f"FCM condition send failed: {e}")
    
    def _build_android_config(
        self,
        priority: str = "normal",
        ttl: int = 3600,
        collapse_key: Optional[str] = None,
        click_action: Optional[str] = None,
        sound: Optional[str] = None,
        **kwargs
    ) -> messaging.AndroidConfig:
        """Build Android configuration."""
        android_priority = "high" if priority == "high" else "normal"
        
        # Build notification
        android_notification = messaging.AndroidNotification(
            click_action=click_action,
            sound=sound,
            priority=android_priority,
            default_vibrate_timings=True,
            default_sound=True
        )
        
        return messaging.AndroidConfig(
            priority=android_priority,
            ttl=ttl,
            collapse_key=collapse_key,
            notification=android_notification
        )
    
    def _build_apns_config(
        self,
        title: str,
        body: str,
        sound: Optional[str] = None,
        badge: Optional[int] = None,
        mutable_content: bool = False,
        priority: str = "normal",
        **kwargs
    ) -> messaging.APNSConfig:
        """Build APNS (iOS) configuration."""
        apns_priority = "10" if priority == "high" else "5"
        
        # Build APS payload
        aps = messaging.Aps(
            alert=messaging.ApsAlert(
                title=title,
                body=body
            ),
            sound=sound or "default",
            badge=badge,
            mutable_content=mutable_content,
            content_available=True if priority == "high" else False
        )
        
        return messaging.APNSConfig(
            headers={"apns-priority": apns_priority},
            payload=messaging.APNSPayload(
                aps=aps
            )
        )
    
    def _build_webpush_config(
        self,
        title: str,
        body: str,
        icon: Optional[str] = None,
        click_action: Optional[str] = None,
        **kwargs
    ) -> messaging.WebpushConfig:
        """Build WebPush configuration."""
        return messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                title=title,
                body=body,
                icon=icon,
                click_action=click_action
            )
        )
    
    async def check_health(self) -> bool:
        """Check FCM health."""
        return self.app is not None
    
    async def get_balance(self) -> Optional[float]:
        """FCM doesn't have balance (pay per use)."""
        return None


class WebPushProvider(PushProvider):
    """
    Web Push notification provider (VAPID).
    """
    
    def __init__(
        self,
        vapid_private_key: str,
        vapid_public_key: str,
        vapid_claim_email: str,
        vapid_claim_subject: Optional[str] = None
    ):
        """
        Initialize WebPush provider.
        
        Args:
            vapid_private_key: VAPID private key
            vapid_public_key: VAPID public key
            vapid_claim_email: VAPID claim email
            vapid_claim_subject: VAPID claim subject
        """
        super().__init__("webpush")
        self.vapid_private_key = vapid_private_key
        self.vapid_public_key = vapid_public_key
        self.vapid_claim_email = vapid_claim_email
        self.vapid_claim_subject = vapid_claim_subject or "Parking Management System"
        
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Initialize VAPID
        try:
            self.vapid = py_vapid.VAPID()
            self.vapid.from_pem(vapid_private_key.encode() if isinstance(vapid_private_key, str) else vapid_private_key)
            self.logger.info("WebPush provider initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebPush: {e}")
            self.vapid = None
    
    async def ensure_session(self) -> None:
        """Ensure HTTP session exists."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def send_push(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None,
        click_action: Optional[str] = None,
        priority: str = "normal",
        ttl: int = 3600,
        collapse_key: Optional[str] = None,
        mutable_content: bool = False,
        sound: Optional[str] = None,
        badge: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send Web Push notification.
        
        Note: For Web Push, tokens should be subscription objects as JSON strings.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            await self.ensure_session()
            
            if not self.vapid:
                raise PushProviderError("WebPush not initialized")
            
            results = []
            
            for token in tokens:
                try:
                    # Parse subscription
                    if isinstance(token, str):
                        subscription = json.loads(token)
                    else:
                        subscription = token
                    
                    # Prepare payload
                    payload = {
                        "title": title,
                        "body": body,
                        "icon": metadata.get('icon') if metadata else settings.WEB_PUSH_ICON,
                        "badge": badge or settings.WEB_PUSH_BADGE,
                        "image": image_url,
                        "data": data or {},
                        "vibrate": [200, 100, 200],
                        "requireInteraction": priority == "high",
                        "renotify": True,
                        "tag": collapse_key,
                        "timestamp": int(datetime.utcnow().timestamp() * 1000)
                    }
                    
                    if click_action:
                        payload["actions"] = [{"action": click_action, "title": "View"}]
                    
                    # Prepare headers
                    vapid_headers = self._get_vapid_headers(
                        endpoint=subscription["endpoint"],
                        audience=subscription.get("origin", "*")
                    )
                    
                    headers = {
                        "TTL": str(ttl),
                        "Content-Type": "application/json",
                        "Urgency": "high" if priority == "high" else "normal",
                        **vapid_headers
                    }
                    
                    # Add encryption if needed
                    if "keys" in subscription:
                        # TODO: Implement payload encryption for WebPush
                        # This would require using webpush-encryption libraries
                        pass
                    
                    # Send notification
                    async with self.session.post(
                        subscription["endpoint"],
                        json=payload,
                        headers=headers
                    ) as response:
                        if response.status in [201, 202]:
                            results.append({
                                "token": token[:50] + "...",  # Truncate for logging
                                "success": True,
                                "status_code": response.status
                            })
                        else:
                            results.append({
                                "token": token[:50] + "...",
                                "success": False,
                                "status_code": response.status,
                                "error": await response.text()
                            })
                            
                except Exception as e:
                    results.append({
                        "token": token[:50] + "...",
                        "success": False,
                        "error": str(e)
                    })
            
            delivery_time = asyncio.get_event_loop().time() - start_time
            success_count = sum(1 for r in results if r["success"])
            
            self.update_stats(success_count > 0, delivery_time, len(tokens))
            
            return {
                "provider": self.name,
                "success_count": success_count,
                "failure_count": len(tokens) - success_count,
                "status": "sent" if success_count > 0 else "failed",
                "results": results,
                "delivery_time": delivery_time
            }
            
        except Exception as e:
            delivery_time = asyncio.get_event_loop().time() - start_time
            self.update_stats(False, delivery_time, len(tokens))
            
            self.logger.error(f"WebPush send failed: {e}")
            raise PushProviderError(f"WebPush send failed: {e}")
    
    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        WebPush doesn't support topics directly.
        This would require a subscription store.
        """
        raise PushProviderError("WebPush does not support topics directly")
    
    async def send_to_condition(
        self,
        condition: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        WebPush doesn't support conditions directly.
        """
        raise PushProviderError("WebPush does not support conditions directly")
    
    def _get_vapid_headers(self, endpoint: str, audience: str) -> Dict[str, str]:
        """
        Generate VAPID headers for WebPush.
        
        Args:
            endpoint: Push endpoint
            audience: Audience (origin)
            
        Returns:
            Dict[str, str]: VAPID headers
        """
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        import jwt
        
        # Create VAPID JWT token
        token = jwt.encode(
            {
                "aud": audience,
                "exp": datetime.utcnow().timestamp() + 43200,  # 12 hours
                "sub": f"mailto:{self.vapid_claim_email}"
            },
            self.vapid.private_key,
            algorithm="ES256"
        )
        
        # Get public key in format
        public_key = self.vapid.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        return {
            "Authorization": f"vapid t={token}, k={base64.urlsafe_b64encode(public_key).decode().rstrip('=')}"
        }
    
    async def check_health(self) -> bool:
        """Check WebPush health."""
        return self.vapid is not None


class PushProviderFactory:
    """
    Factory class for creating push providers.
    """
    
    @staticmethod
    def create_provider(
        provider_type: str,
        config: Dict[str, Any]
    ) -> PushProvider:
        """
        Create a push provider instance.
        
        Args:
            provider_type: Type of provider (fcm, webpush)
            config: Provider configuration
            
        Returns:
            PushProvider: Provider instance
            
        Raises:
            ValueError: If provider type is unknown
        """
        if provider_type == "fcm":
            return FCMProvider(
                credentials_path=config.get("credentials_path"),
                project_id=config.get("project_id"),
                credentials_dict=config.get("credentials_dict")
            )
        elif provider_type == "webpush":
            return WebPushProvider(
                vapid_private_key=config["vapid_private_key"],
                vapid_public_key=config["vapid_public_key"],
                vapid_claim_email=config["vapid_claim_email"],
                vapid_claim_subject=config.get("vapid_claim_subject")
            )
        else:
            raise ValueError(f"Unknown push provider type: {provider_type}")


class PushProviderManager:
    """
    Manager class for handling multiple push providers with failover.
    """
    
    def __init__(self, providers: List[PushProvider]):
        """
        Initialize push provider manager.
        
        Args:
            providers: List of push providers
        """
        self.providers = providers
        self.current_provider_index = 0
        self.logger = get_logger("push_provider_manager")
    
    async def send_push(
        self,
        tokens: List[str],
        title: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send push notification with automatic failover.
        
        Args:
            tokens: List of device tokens
            title: Notification title
            body: Notification body
            **kwargs: Additional arguments
            
        Returns:
            Dict[str, Any]: Provider response
        """
        errors = []
        
        # Try providers in order
        for i in range(len(self.providers)):
            provider_index = (self.current_provider_index + i) % len(self.providers)
            provider = self.providers[provider_index]
            
            try:
                # Check provider health
                if not await provider.check_health():
                    self.logger.warning(f"Provider {provider.name} is unhealthy, skipping")
                    continue
                
                # Send push
                result = await provider.send_push(tokens, title, body, **kwargs)
                
                # Update current provider index on success
                self.current_provider_index = provider_index
                
                # Add provider info to result
                result["provider_used"] = provider.name
                
                return result
                
            except Exception as e:
                self.logger.error(f"Provider {provider.name} failed: {e}")
                errors.append({
                    "provider": provider.name,
                    "error": str(e)
                })
        
        # All providers failed
        raise PushProviderError(
            f"All push providers failed: {errors}"
        )
    
    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send push notification to topic with failover.
        
        Args:
            topic: Topic name
            title: Notification title
            body: Notification body
            **kwargs: Additional arguments
            
        Returns:
            Dict[str, Any]: Provider response
        """
        errors = []
        
        for i in range(len(self.providers)):
            provider_index = (self.current_provider_index + i) % len(self.providers)
            provider = self.providers[provider_index]
            
            try:
                if not await provider.check_health():
                    continue
                
                result = await provider.send_to_topic(topic, title, body, **kwargs)
                
                self.current_provider_index = provider_index
                result["provider_used"] = provider.name
                
                return result
                
            except Exception as e:
                self.logger.error(f"Provider {provider.name} topic send failed: {e}")
                errors.append({
                    "provider": provider.name,
                    "error": str(e)
                })
        
        raise PushProviderError(
            f"All providers failed for topic: {errors}"
        )
    
    async def get_healthy_providers(self) -> List[str]:
        """
        Get list of healthy providers.
        
        Returns:
            List[str]: Names of healthy providers
        """
        healthy = []
        for provider in self.providers:
            if await provider.check_health():
                healthy.append(provider.name)
        return healthy
    
    def get_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all providers.
        
        Returns:
            List[Dict[str, Any]]: Provider statistics
        """
        return [provider.get_stats() for provider in self.providers]


# Singleton instances
fcm_provider = None
webpush_provider = None
provider_manager = None


def initialize_push_providers():
    """
    Initialize push providers based on settings.
    """
    global fcm_provider, webpush_provider, provider_manager
    
    providers = []
    
    # Initialize FCM if configured
    if settings.FCM_CREDENTIALS_PATH or settings.FCM_CREDENTIALS_DICT:
        fcm_provider = FCMProvider(
            credentials_path=settings.FCM_CREDENTIALS_PATH,
            project_id=settings.FCM_PROJECT_ID,
            credentials_dict=settings.FCM_CREDENTIALS_DICT
        )
        providers.append(fcm_provider)
    
    # Initialize WebPush if configured
    if settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY:
        webpush_provider = WebPushProvider(
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_public_key=settings.VAPID_PUBLIC_KEY,
            vapid_claim_email=settings.VAPID_CLAIM_EMAIL,
            vapid_claim_subject=settings.VAPID_CLAIM_SUBJECT
        )
        providers.append(webpush_provider)
    
    # Create provider manager
    if providers:
        provider_manager = PushProviderManager(providers)
    
    return provider_manager