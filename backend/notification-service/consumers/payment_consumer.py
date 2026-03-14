"""
Payment notification consumer.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base import BaseConsumer
from ..core.config import settings
from ..utils.logging_utils import get_logger, audit_log
from ..producers.email_producer import email_producer
from ..producers.sms_producer import sms_producer
from ..producers.push_producer import push_producer


class PaymentConsumer(BaseConsumer):
    """
    Consumer for payment-related notifications.
    """
    
    def __init__(self):
        """Initialize payment consumer."""
        super().__init__(
            queue_name="payment_notifications",
            routing_key="payment.#",
            prefetch_count=settings.PAYMENT_PREFETCH_COUNT
        )
        self.logger = get_logger(__name__)
    
    async def process_message(self, message: Dict[str, Any]) -> bool:
        """
        Process payment notification message.
        
        Expected message format:
        {
            "type": "payment_success",
            "payment_id": "uuid",
            "user_id": "uuid",
            "user_email": "user@example.com",
            "user_phone": "+1234567890",
            "amount": 25.50,
            "currency": "USD",
            "payment_method": "credit_card",
            "booking_id": "uuid",
            "receipt_url": "https://example.com/receipt/123",
            "notify_by": ["email", "sms", "push"],
            "metadata": {...}
        }
        """
        try:
            payment_type = message.get("type")
            payment_id = message.get("payment_id")
            user_id = message.get("user_id")
            user_email = message.get("user_email")
            user_phone = message.get("user_phone")
            amount = message.get("amount")
            currency = message.get("currency", "USD")
            payment_method = message.get("payment_method")
            booking_id = message.get("booking_id")
            notify_by = message.get("notify_by", ["email"])
            metadata = message.get("metadata", {})
            
            self.logger.info(
                f"Processing payment {payment_type}: {payment_id}, "
                f"amount: {currency} {amount}"
            )
            
            # Process based on payment type
            if payment_type == "payment_success":
                await self.process_payment_success(message)
                
            elif payment_type == "payment_failed":
                await self.process_payment_failed(message)
                
            elif payment_type == "payment_refunded":
                await self.process_payment_refunded(message)
                
            elif payment_type == "payment_pending":
                await self.process_payment_pending(message)
            
            # Send notifications
            tasks = []
            
            if "email" in notify_by and user_email:
                tasks.append(self.send_email_notification(payment_type, message))
            
            if "sms" in notify_by and user_phone:
                tasks.append(self.send_sms_notification(payment_type, message))
            
            if "push" in notify_by and user_id:
                tasks.append(self.send_push_notification(payment_type, message))
            
            if tasks:
                await asyncio.gather(*tasks)
            
            # Generate receipt if needed
            if payment_type == "payment_success" and message.get("generate_receipt"):
                await self.generate_receipt(message)
            
            # Audit log
            audit_log(
                self.logger,
                action=f"PAYMENT_{payment_type.upper()}",
                resource="payment",
                resource_id=payment_id,
                user_id=user_id,
                details={
                    "amount": amount,
                    "currency": currency,
                    "payment_method": payment_method,
                    "booking_id": booking_id,
                    **metadata
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process payment message: {e}", exc_info=True)
            return False
    
    async def process_payment_success(self, data: Dict[str, Any]) -> None:
        """
        Process successful payment.
        """
        self.logger.info(f"Payment success: {data['payment_id']}")
        
        # Update payment statistics
        # Trigger loyalty points calculation
        # Update booking status
        # etc.
    
    async def process_payment_failed(self, data: Dict[str, Any]) -> None:
        """
        Process failed payment.
        """
        self.logger.info(f"Payment failed: {data['payment_id']}")
        
        # Check for retry eligibility
        if data.get("retry_eligible", True):
            await self.schedule_payment_retry(data)
    
    async def process_payment_refunded(self, data: Dict[str, Any]) -> None:
        """
        Process refunded payment.
        """
        self.logger.info(f"Payment refunded: {data['payment_id']}")
        
        # Update booking status
        # Reverse loyalty points
        # etc.
    
    async def process_payment_pending(self, data: Dict[str, Any]) -> None:
        """
        Process pending payment.
        """
        self.logger.info(f"Payment pending: {data['payment_id']}")
    
    async def send_email_notification(self, payment_type: str, data: Dict[str, Any]) -> None:
        """
        Send email notification for payment.
        """
        template_map = {
            "payment_success": "payment_success",
            "payment_failed": "payment_failed",
            "payment_refunded": "payment_refunded",
            "payment_pending": "payment_pending"
        }
        
        template = template_map.get(payment_type)
        if not template:
            return
        
        # Prepare email data
        email_data = {
            "type": "email",
            "to": [data["user_email"]],
            "subject": self.get_email_subject(payment_type, data),
            "template": f"payment/{template}",
            "context": {
                "user_name": data.get("user_name", "Valued Customer"),
                "payment_id": data["payment_id"],
                "amount": data["amount"],
                "currency": data["currency"],
                "payment_method": data.get("payment_method", "Unknown"),
                "booking_id": data.get("booking_id"),
                "receipt_url": data.get("receipt_url"),
                "date": datetime.utcnow().strftime("%B %d, %Y"),
                "support_email": settings.SUPPORT_EMAIL
            },
            "priority": "high",
            "metadata": {
                "payment_id": data["payment_id"],
                "type": payment_type
            }
        }
        
        # Add failure reason if applicable
        if payment_type == "payment_failed":
            email_data["context"]["failure_reason"] = data.get("failure_reason", "Unknown error")
        
        # Publish to email queue
        await email_producer.publish_email(email_data)
    
    async def send_sms_notification(self, payment_type: str, data: Dict[str, Any]) -> None:
        """
        Send SMS notification for payment.
        """
        messages = {
            "payment_success": f"Payment successful: {data['currency']} {data['amount']} for booking {data.get('booking_id', 'N/A')}",
            "payment_failed": f"Payment failed: {data['currency']} {data['amount']}. Please update payment method.",
            "payment_refunded": f"Payment refunded: {data['currency']} {data['amount']}",
            "payment_pending": f"Payment pending: {data['currency']} {data['amount']}"
        }
        
        message = messages.get(payment_type)
        if not message:
            return
        
        # Prepare SMS data
        sms_data = {
            "type": "sms",
            "to": [data["user_phone"]],
            "message": message,
            "priority": "high",
            "metadata": {
                "payment_id": data["payment_id"],
                "type": payment_type
            }
        }
        
        # Publish to SMS queue
        await sms_producer.publish_sms(sms_data)
    
    async def send_push_notification(self, payment_type: str, data: Dict[str, Any]) -> None:
        """
        Send push notification for payment.
        """
        titles = {
            "payment_success": "Payment Successful",
            "payment_failed": "Payment Failed",
            "payment_refunded": "Payment Refunded",
            "payment_pending": "Payment Pending"
        }
        
        messages = {
            "payment_success": f"Your payment of {data['currency']} {data['amount']} was successful",
            "payment_failed": f"Your payment of {data['currency']} {data['amount']} failed. Please update your payment method",
            "payment_refunded": f"Your payment of {data['currency']} {data['amount']} has been refunded",
            "payment_pending": f"Your payment of {data['currency']} {data['amount']} is pending"
        }
        
        # Prepare push data
        push_data = {
            "type": "push",
            "tokens": [],  # Would need to get user's device tokens
            "title": titles.get(payment_type, "Payment Update"),
            "body": messages.get(payment_type, ""),
            "data": {
                "payment_id": data["payment_id"],
                "type": payment_type,
                "click_action": "OPEN_PAYMENT"
            },
            "priority": "high",
            "metadata": {
                "payment_id": data["payment_id"],
                "type": payment_type
            }
        }
        
        # Publish to push queue
        await push_producer.publish_push(push_data)
    
    async def generate_receipt(self, data: Dict[str, Any]) -> None:
        """
        Generate payment receipt.
        """
        try:
            # Generate PDF receipt
            receipt_data = {
                "receipt_number": f"RCP-{data['payment_id'][:8].upper()}",
                "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "customer": {
                    "name": data.get("user_name", "Valued Customer"),
                    "email": data["user_email"]
                },
                "payment": {
                    "id": data["payment_id"],
                    "method": data.get("payment_method"),
                    "amount": data["amount"],
                    "currency": data["currency"],
                    "status": "completed"
                },
                "booking": {
                    "id": data.get("booking_id"),
                    "details": data.get("booking_details", {})
                }
            }
            
            # Store receipt
            receipt_url = await self.store_receipt(receipt_data)
            
            # Send receipt via email
            receipt_email = {
                "type": "email",
                "to": [data["user_email"]],
                "subject": f"Receipt for Payment {data['payment_id']}",
                "template": "payment/receipt",
                "context": {
                    "user_name": data.get("user_name", "Valued Customer"),
                    "receipt_url": receipt_url
                },
                "metadata": {
                    "payment_id": data["payment_id"],
                    "type": "receipt"
                }
            }
            
            await email_producer.publish_email(receipt_email)
            
            self.logger.info(f"Receipt generated for payment {data['payment_id']}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate receipt: {e}")
    
    async def store_receipt(self, receipt_data: Dict[str, Any]) -> str:
        """
        Store receipt and return URL.
        
        Args:
            receipt_data: Receipt data
            
        Returns:
            str: Receipt URL
        """
        # Implementation would store receipt in cloud storage
        # and return accessible URL
        return f"{settings.RECEIPTS_URL}/{receipt_data['receipt_number']}.pdf"
    
    async def schedule_payment_retry(self, data: Dict[str, Any]) -> None:
        """
        Schedule payment retry.
        """
        # Schedule retry after 1 hour
        await asyncio.sleep(3600)
        
        # Send retry notification
        retry_data = {
            "type": "payment_retry",
            "original_payment_id": data["payment_id"],
            "user_email": data["user_email"],
            "user_phone": data["user_phone"],
            "amount": data["amount"],
            "currency": data["currency"]
        }
        
        await self.process_message(retry_data)
    
    def get_email_subject(self, payment_type: str, data: Dict[str, Any]) -> str:
        """
        Get email subject for payment type.
        """
        subjects = {
            "payment_success": f"Payment Confirmed: {data['currency']} {data['amount']}",
            "payment_failed": f"Payment Failed: {data['currency']} {data['amount']}",
            "payment_refunded": f"Payment Refunded: {data['currency']} {data['amount']}",
            "payment_pending": f"Payment Pending: {data['currency']} {data['amount']}"
        }
        
        return subjects.get(payment_type, "Payment Update")