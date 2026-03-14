"""
Email notification consumer.
"""

import asyncio
from typing import Dict, Any, Optional, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib

from .base import BaseConsumer
from ..core.config import settings
from ..utils.logging_utils import get_logger, audit_log
from ..utils.templates import render_template
from ..utils.retry import async_retry
from ..core.exceptions import EmailDeliveryError


class EmailConsumer(BaseConsumer):
    """
    Consumer for email notifications.
    """
    
    def __init__(self):
        """Initialize email consumer."""
        super().__init__(
            queue_name="email_notifications",
            routing_key="notification.email.*",
            prefetch_count=settings.EMAIL_PREFETCH_COUNT
        )
        self.logger = get_logger(__name__)
        self.smtp_client: Optional[aiosmtplib.SMTP] = None
    
    async def connect_smtp(self) -> None:
        """
        Connect to SMTP server.
        """
        try:
            self.smtp_client = aiosmtplib.SMTP(
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                use_tls=settings.SMTP_USE_TLS
            )
            
            await self.smtp_client.connect()
            
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                await self.smtp_client.login(
                    settings.SMTP_USERNAME,
                    settings.SMTP_PASSWORD
                )
            
            self.logger.info("Connected to SMTP server")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to SMTP server: {e}")
            raise EmailDeliveryError(f"SMTP connection failed: {e}")
    
    async def disconnect_smtp(self) -> None:
        """
        Disconnect from SMTP server.
        """
        if self.smtp_client:
            try:
                await self.smtp_client.quit()
            except Exception as e:
                self.logger.warning(f"Error disconnecting SMTP: {e}")
    
    async def process_message(self, message: Dict[str, Any]) -> bool:
        """
        Process email notification message.
        
        Expected message format:
        {
            "type": "email",
            "to": ["user@example.com"],
            "cc": ["cc@example.com"],
            "bcc": ["bcc@example.com"],
            "subject": "Email Subject",
            "template": "welcome_email",
            "context": {"name": "John", "link": "..."},
            "attachments": [...],
            "priority": "high",
            "metadata": {...}
        }
        """
        try:
            email_type = message.get("type")
            to_emails = message.get("to", [])
            cc_emails = message.get("cc", [])
            bcc_emails = message.get("bcc", [])
            subject = message.get("subject")
            template_name = message.get("template")
            context = message.get("context", {})
            attachments = message.get("attachments", [])
            priority = message.get("priority", "normal")
            metadata = message.get("metadata", {})
            
            # Validate required fields
            if not to_emails:
                self.logger.error("No recipient emails provided")
                return False
            
            if not subject:
                self.logger.error("No email subject provided")
                return False
            
            if not template_name:
                self.logger.error("No email template provided")
                return False
            
            # Connect to SMTP if not connected
            if not self.smtp_client or not self.smtp_client.is_connected:
                await self.connect_smtp()
            
            # Render email content
            html_content = await render_template(f"emails/{template_name}.html", context)
            text_content = await render_template(f"emails/{template_name}.txt", context)
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.EMAIL_FROM
            msg["To"] = ", ".join(to_emails)
            
            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)
            
            # Add priority header
            if priority == "high":
                msg["X-Priority"] = "1"
                msg["X-MSMail-Priority"] = "High"
            
            # Attach parts
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            # Handle attachments
            for attachment in attachments:
                await self.add_attachment(msg, attachment)
            
            # Send email
            all_recipients = to_emails + cc_emails + bcc_emails
            result = await self.smtp_client.send_message(msg, recipients=all_recipients)
            
            # Log success
            self.logger.info(
                f"Email sent successfully to {len(to_emails)} recipients. "
                f"Message ID: {result}"
            )
            
            # Audit log
            audit_log(
                self.logger,
                action="EMAIL_SENT",
                resource="notification",
                details={
                    "type": email_type,
                    "template": template_name,
                    "recipients": len(to_emails),
                    "priority": priority,
                    "message_id": result,
                    **metadata
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process email message: {e}", exc_info=True)
            message["error"] = str(e)
            return False
    
    async def add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]) -> None:
        """
        Add attachment to email.
        
        Args:
            msg: Email message
            attachment: Attachment data
        """
        try:
            attachment_type = attachment.get("type")
            
            if attachment_type == "file":
                # Read file and attach
                with open(attachment["path"], "rb") as f:
                    file_data = f.read()
                
                part = MIMEText(file_data, "base64")
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment['filename']}"
                )
                msg.attach(part)
                
            elif attachment_type == "data":
                # Attach data directly
                part = MIMEText(attachment["content"], attachment.get("mime", "text/plain"))
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment['filename']}"
                )
                msg.attach(part)
                
        except Exception as e:
            self.logger.error(f"Failed to add attachment: {e}")
            raise
    
    @async_retry(max_retries=3, delay=1)
    async def send_bulk_emails(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send bulk emails efficiently.
        
        Args:
            emails: List of email data
            
        Returns:
            Dict[str, Any]: Bulk send results
        """
        results = {
            "total": len(emails),
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        # Group by template for efficiency
        for email in emails:
            try:
                success = await self.process_message(email)
                if success:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "email": email.get("to"),
                    "error": str(e)
                })
        
        return results
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get email queue statistics.
        
        Returns:
            Dict[str, Any]: Queue statistics
        """
        queue_status = await self.get_queue_status()
        
        return {
            **queue_status,
            "smtp_connected": self.smtp_client and self.smtp_client.is_connected,
            "smtp_host": settings.SMTP_HOST,
            "smtp_port": settings.SMTP_PORT
        }
    
    async def stop(self) -> None:
        """Stop consumer and disconnect from SMTP."""
        await self.disconnect_smtp()
        await super().stop()