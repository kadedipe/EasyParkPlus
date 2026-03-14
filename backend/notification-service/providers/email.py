"""
Email provider implementations with multi-provider support and failover.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import aiosmtplib
import aiohttp
import json
import base64

from ..core.config import settings
from ..utils.logging_utils import get_logger
from ..utils.retry import async_retry
from ..core.exceptions import EmailProviderError


class EmailProvider(ABC):
    """
    Abstract base class for email providers.
    """
    
    def __init__(self, name: str):
        """
        Initialize email provider.
        
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
            "avg_delivery_time": 0.0
        }
    
    @abstractmethod
    async def send_email(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Send email using the provider.
        
        Args:
            to: List of recipient emails
            subject: Email subject
            html_content: HTML content
            text_content: Plain text content
            from_email: Sender email
            cc: Carbon copy recipients
            bcc: Blind carbon copy recipients
            attachments: List of attachments
            headers: Additional email headers
            priority: Email priority (high, normal, low)
            
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
    
    def update_stats(self, success: bool, delivery_time: float) -> None:
        """
        Update provider statistics.
        
        Args:
            success: Whether email was sent successfully
            delivery_time: Time taken to deliver
        """
        if success:
            self.stats["sent"] += 1
            self.stats["last_success"] = datetime.utcnow().isoformat()
            
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
        return {
            "name": self.name,
            **self.stats,
            "health": self.stats["failed"] < self.stats["sent"] * 0.1  # 90% success rate
        }


class SMTPProvider(EmailProvider):
    """
    SMTP email provider.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
        timeout: int = 30
    ):
        """
        Initialize SMTP provider.
        
        Args:
            host: SMTP server host
            port: SMTP server port
            username: SMTP username
            password: SMTP password
            use_tls: Use TLS
            timeout: Connection timeout
        """
        super().__init__("smtp")
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.timeout = timeout
        self.client: Optional[aiosmtplib.SMTP] = None
    
    async def connect(self) -> None:
        """
        Connect to SMTP server.
        """
        try:
            self.client = aiosmtplib.SMTP(
                hostname=self.host,
                port=self.port,
                timeout=self.timeout,
                use_tls=self.use_tls
            )
            
            await self.client.connect()
            
            if self.username and self.password:
                await self.client.login(self.username, self.password)
            
            self.logger.info(f"Connected to SMTP server {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"SMTP connection failed: {e}")
            raise EmailProviderError(f"SMTP connection failed: {e}")
    
    async def disconnect(self) -> None:
        """
        Disconnect from SMTP server.
        """
        if self.client:
            try:
                await self.client.quit()
            except Exception as e:
                self.logger.warning(f"Error disconnecting SMTP: {e}")
            finally:
                self.client = None
    
    async def ensure_connection(self) -> None:
        """
        Ensure connection is established.
        """
        if not self.client or not self.client.is_connected:
            await self.connect()
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def send_email(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Send email via SMTP.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            await self.ensure_connection()
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email or settings.EMAIL_FROM
            msg["To"] = ", ".join(to)
            
            if cc:
                msg["Cc"] = ", ".join(cc)
            
            if headers:
                for key, value in headers.items():
                    msg[key] = value
            
            # Set priority headers
            if priority == "high":
                msg["X-Priority"] = "1"
                msg["X-MSMail-Priority"] = "High"
            elif priority == "low":
                msg["X-Priority"] = "5"
                msg["X-MSMail-Priority"] = "Low"
            
            # Add text content
            if text_content:
                msg.attach(MIMEText(text_content, "plain"))
            
            # Add HTML content
            msg.attach(MIMEText(html_content, "html"))
            
            # Add attachments
            if attachments:
                await self.add_attachments(msg, attachments)
            
            # Send email
            all_recipients = to + (cc or []) + (bcc or [])
            response = await self.client.send_message(msg, recipients=all_recipients)
            
            delivery_time = asyncio.get_event_loop().time() - start_time
            self.update_stats(True, delivery_time)
            
            return {
                "provider": self.name,
                "message_id": response,
                "status": "sent",
                "to": to,
                "subject": subject,
                "delivery_time": delivery_time
            }
            
        except Exception as e:
            delivery_time = asyncio.get_event_loop().time() - start_time
            self.update_stats(False, delivery_time)
            
            self.logger.error(f"SMTP send failed: {e}")
            raise EmailProviderError(f"SMTP send failed: {e}")
    
    async def add_attachments(
        self,
        msg: MIMEMultipart,
        attachments: List[Dict[str, Any]]
    ) -> None:
        """
        Add attachments to email.
        
        Args:
            msg: Email message
            attachments: List of attachments
        """
        for attachment in attachments:
            try:
                filename = attachment.get("filename", "attachment")
                content = attachment.get("content")
                content_type = attachment.get("content_type", "application/octet-stream")
                
                if isinstance(content, str):
                    if attachment.get("encoding") == "base64":
                        content = base64.b64decode(content)
                    else:
                        content = content.encode()
                
                part = MIMEApplication(content, content_type)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={filename}"
                )
                msg.attach(part)
                
            except Exception as e:
                self.logger.error(f"Failed to add attachment {filename}: {e}")
    
    async def check_health(self) -> bool:
        """
        Check SMTP server health.
        """
        try:
            await self.ensure_connection()
            return True
        except Exception:
            return False


class SendGridProvider(EmailProvider):
    """
    SendGrid email provider.
    """
    
    def __init__(
        self,
        api_key: str,
        from_email: str,
        from_name: Optional[str] = None
    ):
        """
        Initialize SendGrid provider.
        
        Args:
            api_key: SendGrid API key
            from_email: Default from email
            from_name: Default from name
        """
        super().__init__("sendgrid")
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.base_url = "https://api.sendgrid.com/v3"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def ensure_session(self) -> None:
        """
        Ensure HTTP session exists.
        """
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    @async_retry(max_retries=3, delay=1, backoff=2)
    async def send_email(
        self,
        to: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Send email via SendGrid.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            await self.ensure_session()
            
            # Build SendGrid API request
            from_address = from_email or self.from_email
            
            # Parse from email and name
            if self.from_name:
                from_address = f"{self.from_name} <{from_address}>"
            
            # Build personalizations
            personalizations = [{"to": [{"email": email} for email in to]}]
            
            if cc:
                personalizations[0]["cc"] = [{"email": email} for email in cc]
            
            if bcc:
                personalizations[0]["bcc"] = [{"email": email} for email in bcc]
            
            # Set priority headers
            if headers is None:
                headers = {}
            
            if priority == "high":
                headers["Priority"] = "urgent"
                headers["Importance"] = "high"
            elif priority == "low":
                headers["Priority"] = "non-urgent"
                headers["Importance"] = "low"
            
            # Build content
            content = []
            if text_content:
                content.append({
                    "type": "text/plain",
                    "value": text_content
                })
            
            content.append({
                "type": "text/html",
                "value": html_content
            })
            
            # Build attachments
            attachments_data = []
            if attachments:
                for attachment in attachments:
                    attachments_data.append({
                        "filename": attachment.get("filename", "attachment"),
                        "type": attachment.get("content_type", "application/octet-stream"),
                        "content": attachment.get("content"),
                        "disposition": "attachment"
                    })
            
            # Build request payload
            payload = {
                "personalizations": personalizations,
                "from": {"email": from_address},
                "subject": subject,
                "content": content,
                "headers": headers,
                "mail_settings": {
                    "sandbox_mode": {"enable": settings.SENDGRID_SANDBOX_MODE}
                }
            }
            
            if attachments_data:
                payload["attachments"] = attachments_data
            
            # Make API request
            async with self.session.post(
                f"{self.base_url}/mail/send",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            ) as response:
                if response.status == 202:
                    delivery_time = asyncio.get_event_loop().time() - start_time
                    self.update_stats(True, delivery_time)
                    
                    # Get message ID from headers
                    message_id = response.headers.get("X-Message-Id")
                    
                    return {
                        "provider": self.name,
                        "message_id": message_id,
                        "status": "accepted",
                        "to": to,
                        "subject": subject,
                        "delivery_time": delivery_time
                    }
                else:
                    error_text = await response.text()
                    raise EmailProviderError(
                        f"SendGrid error {response.status}: {error_text}"
                    )
            
        except Exception as e:
            delivery_time = asyncio.get_event_loop().time() - start_time
            self.update_stats(False, delivery_time)
            
            self.logger.error(f"SendGrid send failed: {e}")
            raise EmailProviderError(f"SendGrid send failed: {e}")
    
    async def check_health(self) -> bool:
        """
        Check SendGrid API health.
        """
        try:
            await self.ensure_session()
            
            async with self.session.get(
                f"{self.base_url}/scopes",
                headers={"Authorization": f"Bearer {self.api_key}"}
            ) as response:
                return response.status == 200
                
        except Exception:
            return False


class AWSSESProvider(EmailProvider):
    """
    AWS SES email provider.
    """
    
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        region: str,
        from_email: str,
        from_name: Optional[str] = None
    ):
        """
        Initialize AWS SES provider.
        
        Args:
            access_key: AWS access key
            secret_key: AWS secret key
            region: AWS region
            from_email: Default from email
            from_name: Default from name
        """
        super().__init__("aws_ses")
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.from_email = from_email
        self.from_name = from_name