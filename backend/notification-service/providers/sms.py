"""
SMS provider implementations with multi-provider support and failover.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import aiohttp
import base64
import hmac
import hashlib
import urllib.parse

try:
    import boto3
    from botocore.exceptions import ClientError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    logging.warning("AWS SDK not available")

from ..core.config import settings
from ..utils.logging_utils import get_logger
from ..utils.retry import async_retry
from ..core.exceptions import SMSProviderError


class SMSProvider(ABC):
    """
    Abstract base class for SMS providers.
    """
    
    def __init__(self, name: str):
        """
        Initialize SMS provider.
        
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
            "total_characters": 0
        }
    
    @abstractmethod
    async def send_sms(
        self,
        to: str,
        message: str,
        sender_id: Optional[str] = None,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send SMS using the provider.
        
        Args:
            to: Recipient phone number
            message: SMS message content
            sender_id: Sender ID (if supported)
            priority: Message priority (high, normal, low)
            metadata: Additional metadata
            
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
    
    @abstractmethod
    async def get_balance(self) -> Optional[float]:
        """
        Get account balance (if supported).
        
        Returns:
            Optional[float]: Account balance
        """
        pass
    
    def update_stats(
        self,
        success: bool,
        delivery_time: float,
        characters: int = 0
    ) -> None:
        """
        Update provider statistics.
        
        Args:
            success: Whether SMS was sent successfully
            delivery_time: Time taken to deliver
            characters: Number of characters sent
        """
        if success:
            self.stats["sent"] += 1
            self.stats["last_success"] = datetime.utcnow().isoformat()
            self.stats["total_characters"] += characters
            
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


class TwilioProvider(SMSProvider):
    """
    Twilio SMS provider.
    """
    
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        phone_number: str,
        messaging_service_sid: Optional[str] = None
    ):
        """
        Initialize Twilio provider.
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            phone_number: Twilio phone number
            messaging_service_sid: Messaging Service SID
        """
        super().__init__("twilio")
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.phone_number = phone_number
        self.messaging_service_sid = messaging_service_sid
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def ensure_session(self) -> None:
        """Ensure HTTP session exists."""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def send_sms(
        self,
        to: str,
        message: str,
        sender_id: Optional[str] = None,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send SMS via Twilio.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            await self.ensure_session()
            
            # Prepare request data
            data = {
                "To": to,
                "Body": message,
                "StatusCallback": settings.SMS_STATUS_CALLBACK_URL
            }
            
            # Use messaging service if available
            if self.messaging_service_sid:
                data["MessagingServiceSid"] = self.messaging_service_sid
            else:
                data["From"] = sender_id or self.phone_number
            
            # Set priority (Twilio doesn't have priority, but we can set validity period)
            if priority == "high":
                data["ValidityPeriod"] = "300"  # 5 minutes
            elif priority == "low":
                data["ValidityPeriod"] = "86400"  # 24 hours
            
            # Add metadata as URL parameters
            if metadata:
                for key, value in metadata.items():
                    data[f"Metadata.{key}"] = str(value)
            
            # Prepare auth
            auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
            
            # Make request
            async with self.session.post(
                f"{self.base_url}/Messages.json",
                data=data,
                auth=auth
            ) as response:
                result = await response.json()
                
                if response.status in [200, 201]:
                    delivery_time = asyncio.get_event_loop().time() - start_time
                    
                    # Count SMS segments (Twilio charges per segment)
                    segments = result.get('num_segments', 1)
                    characters = len(message)
                    
                    self.update_stats(True, delivery_time, characters)
                    
                    return {
                        "provider": self.name,
                        "message_id": result.get('sid'),
                        "status": result.get('status'),
                        "to": to,
                        "segments": int(segments),
                        "characters": characters,
                        "price": result.get('price'),
                        "price_unit": result.get('price_unit'),
                        "delivery_time": delivery_time
                    }
                else:
                    error_message = result.get('message', 'Unknown error')
                    raise SMSProviderError(f"Twilio error: {error_message}")
                    
        except Exception as e:
            delivery_time = asyncio.get_event_loop().time() - start_time
            self.update_stats(False, delivery_time)
            
            self.logger.error(f"Twilio send failed: {e}")
            raise SMSProviderError(f"Twilio send failed: {e}")
    
    async def check_health(self) -> bool:
        """Check Twilio API health."""
        try:
            await self.ensure_session()
            auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
            
            async with self.session.get(
                f"{self.base_url}",
                auth=auth
            ) as response:
                return response.status == 200
                
        except Exception:
            return False
    
    async def get_balance(self) -> Optional[float]:
        """Get Twilio account balance."""
        try:
            await self.ensure_session()
            auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
            
            async with self.session.get(
                f"{self.base_url}/Balance.json",
                auth=auth
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data.get('balance', 0))
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get Twilio balance: {e}")
            return None


class AWSSNSProvider(SMSProvider):
    """
    AWS SNS SMS provider.
    """
    
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        region: str,
        sender_id: Optional[str] = None
    ):
        """
        Initialize AWS SNS provider.
        
        Args:
            access_key: AWS Access Key
            secret_key: AWS Secret Key
            region: AWS Region
            sender_id: Sender ID (if supported)
        """
        super().__init__("aws_sns")
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.sender_id = sender_id
        self.client = None
        
        if AWS_AVAILABLE:
            self.client = boto3.client(
                'sns',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )