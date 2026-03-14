"""
SMS notification consumer.
"""

import asyncio
from typing import Dict, Any, Optional, List
import aiohttp

from .base import BaseConsumer
from ..core.config import settings
from ..utils.logging_utils import get_logger, audit_log
from ..utils.retry import async_retry
from ..core.exceptions import SMSDeliveryError


class SMSConsumer(BaseConsumer):
    """
    Consumer for SMS notifications.
    """
    
    def __init__(self):
        """Initialize SMS consumer."""
        super().__init__(
            queue_name="sms_notifications",
            routing_key="notification.sms.*",
            prefetch_count=settings.SMS_PREFETCH_COUNT
        )
        self.logger = get_logger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
    
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
        Process SMS notification message.
        
        Expected message format:
        {
            "type": "sms",
            "to": ["+1234567890"],
            "message": "Your verification code is 123456",
            "template": "verification_code",
            "context": {"code": "123456"},
            "provider": "twilio",
            "priority": "normal",
            "metadata": {...}
        }
        """
        try:
            sms_type = message.get("type")
            to_numbers = message.get("to", [])
            message_text = message.get("message")
            template_name = message.get("template")
            context = message.get("context", {})
            provider = message.get("provider", settings.SMS_PROVIDER)
            priority = message.get("priority", "normal")
            metadata = message.get("metadata", {})
            
            # Validate required fields
            if not to_numbers:
                self.logger.error("No recipient numbers provided")
                return False
            
            # Generate message from template if provided
            if template_name and not message_text:
                message_text = await self.render_sms_template(template_name, context)
            
            if not message_text:
                self.logger.error("No message content provided")
                return False
            
            # Connect HTTP session
            await self.connect_http()
            
            # Send SMS based on provider
            results = []
            for to_number in to_numbers:
                try:
                    result = await self.send_sms(
                        to=to_number,
                        message=message_text,
                        provider=provider,
                        priority=priority
                    )
                    results.append(result)
                    
                    # Rate limiting
                    await asyncio.sleep(settings.SMS_RATE_LIMIT_DELAY)
                    
                except Exception as e:
                    self.logger.error(f"Failed to send SMS to {to_number}: {e}")
                    results.append({"to": to_number, "success": False, "error": str(e)})
            
            # Calculate success rate
            success_count = sum(1 for r in results if r.get("success"))
            
            # Log results
            self.logger.info(
                f"SMS sent to {success_count}/{len(to_numbers)} recipients"
            )
            
            # Audit log
            audit_log(
                self.logger,
                action="SMS_SENT",
                resource="notification",
                details={
                    "type": sms_type,
                    "template": template_name,
                    "recipients": len(to_numbers),
                    "successful": success_count,
                    "provider": provider,
                    "priority": priority,
                    "results": results,
                    **metadata
                }
            )
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Failed to process SMS message: {e}", exc_info=True)
            message["error"] = str(e)
            return False
    
    @async_retry(max_retries=3, delay=1)
    async def send_sms(
        self,
        to: str,
        message: str,
        provider: str = "twilio",
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Send SMS using configured provider.
        
        Args:
            to: Recipient phone number
            message: SMS message
            provider: SMS provider
            priority: Message priority
            
        Returns:
            Dict[str, Any]: Send result
        """
        if provider == "twilio":
            return await self.send_via_twilio(to, message, priority)
        elif provider == "aws_sns":
            return await self.send_via_aws_sns(to, message, priority)
        elif provider == "vonage":
            return await self.send_via_vonage(to, message, priority)
        else:
            raise SMSDeliveryError(f"Unsupported SMS provider: {provider}")
    
    async def send_via_twilio(
        self,
        to: str,
        message: str,
        priority: str
    ) -> Dict[str, Any]:
        """
        Send SMS via Twilio.
        """
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
            
            data = {
                "To": to,
                "From": settings.TWILIO_PHONE_NUMBER,
                "Body": message
            }
            
            auth = aiohttp.BasicAuth(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            async with self.session.post(url, data=data, auth=auth) as response:
                if response.status == 201:
                    result = await response.json()
                    return {
                        "to": to,
                        "success": True,
                        "message_id": result.get("sid"),
                        "provider": "twilio",
                        "status": result.get("status")
                    }
                else:
                    error_text = await response.text()
                    raise SMSDeliveryError(f"Twilio error: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"Twilio SMS failed: {e}")
            raise
    
    async def send_via_aws_sns(
        self,
        to: str,
        message: str,
        priority: str
    ) -> Dict[str, Any]:
        """
        Send SMS via AWS SNS.
        """
        try:
            # AWS SNS implementation
            import boto3
            from botocore.config import Config
            
            # Create SNS client
            session = boto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            
            sns = session.client('sns')
            
            # Set message attributes based on priority
            attributes = {
                'AWS.SNS.SMS.SenderID': {
                    'DataType': 'String',
                    'StringValue': settings.SMS_SENDER_ID or 'PARKING'
                }
            }
            
            if priority == "high":
                attributes['AWS.SNS.SMS.MaxPrice'] = {
                    'DataType': 'Number',
                    'StringValue': '0.50'
                }
            
            # Publish message
            response = sns.publish(
                PhoneNumber=to,
                Message=message,
                MessageAttributes=attributes
            )
            
            return {
                "to": to,
                "success": True,
                "message_id": response.get('MessageId'),
                "provider": "aws_sns"
            }
            
        except Exception as e:
            self.logger.error(f"AWS SNS SMS failed: {e}")
            raise
    
    async def send_via_vonage(
        self,
        to: str,
        message: str,
        priority: str
    ) -> Dict[str, Any]:
        """
        Send SMS via Vonage (formerly Nexmo).
        """
        try:
            url = "https://rest.nexmo.com/sms/json"
            
            data = {
                "api_key": settings.VONAGE_API_KEY,
                "api_secret": settings.VONAGE_API_SECRET,
                "to": to,
                "from": settings.VONAGE_PHONE_NUMBER,
                "text": message,
                "type": "unicode"
            }
            
            if priority == "high":
                data["priority"] = "high"
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    messages = result.get("messages", [])
                    
                    if messages and messages[0].get("status") == "0":
                        return {
                            "to": to,
                            "success": True,
                            "message_id": messages[0].get("message-id"),
                            "provider": "vonage"
                        }
                    else:
                        error = messages[0].get("error-text") if messages else "Unknown error"
                        raise SMSDeliveryError(f"Vonage error: {error}")
                else:
                    raise SMSDeliveryError(f"Vonage HTTP error: {response.status}")
                    
        except Exception as e:
            self.logger.error(f"Vonage SMS failed: {e}")
            raise
    
    async def render_sms_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render SMS template.
        
        Args:
            template_name: Template name
            context: Template context
            
        Returns:
            str: Rendered message
        """
        # Simple template rendering (can be replaced with proper template engine)
        templates = {
            "verification_code": "Your verification code is: {code}",
            "welcome": "Welcome to Parking Management, {name}!",
            "booking_confirmation": "Your booking #{booking_id} is confirmed. Vehicle: {plate_number}",
            "payment_receipt": "Payment of {amount} received. Receipt: {receipt_id}",
            "reminder": "Reminder: Your parking session expires in {minutes} minutes",
            "alert": "Alert: {message}"
        }
        
        template = templates.get(template_name, "{message}")
        return template.format(**context)
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get SMS queue statistics.
        
        Returns:
            Dict[str, Any]: Queue statistics
        """
        queue_status = await self.get_queue_status()
        
        return {
            **queue_status,
            "http_connected": self.session and not self.session.closed,
            "provider": settings.SMS_PROVIDER,
            "rate_limit": settings.SMS_RATE_LIMIT_DELAY
        }
    
    async def stop(self) -> None:
        """Stop consumer and disconnect HTTP."""
        await self.disconnect_http()
        await super().stop()