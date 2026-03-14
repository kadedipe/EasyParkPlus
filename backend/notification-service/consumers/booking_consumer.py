"""
Booking notification consumer.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .base import BaseConsumer
from ..core.config import settings
from ..utils.logging_utils import get_logger, audit_log
from ..utils.templates import render_template
from ..producers.email_producer import email_producer
from ..producers.sms_producer import sms_producer
from ..producers.push_producer import push_producer


class BookingConsumer(BaseConsumer):
    """
    Consumer for booking-related notifications.
    """
    
    def __init__(self):
        """Initialize booking consumer."""
        super().__init__(
            queue_name="booking_notifications",
            routing_key="booking.#",
            prefetch_count=settings.BOOKING_PREFETCH_COUNT
        )
        self.logger = get_logger(__name__)
        self.booking_reminders = {}
    
    async def process_message(self, message: Dict[str, Any]) -> bool:
        """
        Process booking notification message.
        
        Expected message format:
        {
            "type": "booking_confirmation",
            "booking_id": "uuid",
            "user_id": "uuid",
            "user_email": "user@example.com",
            "user_phone": "+1234567890",
            "vehicle_plate": "ABC123",
            "parking_name": "Downtown Parking",
            "spot_number": "A12",
            "start_time": "2024-01-01T10:00:00Z",
            "end_time": "2024-01-01T12:00:00Z",
            "amount": 25.50,
            "currency": "USD",
            "notify_by": ["email", "sms", "push"]
        }
        """
        try:
            booking_type = message.get("type")
            booking_id = message.get("booking_id")
            user_id = message.get("user_id")
            user_email = message.get("user_email")
            user_phone = message.get("user_phone")
            notify_by = message.get("notify_by", ["email"])
            
            self.logger.info(f"Processing booking {booking_type}: {booking_id}")
            
            # Process based on notification type
            if booking_type == "booking_confirmation":
                await self.process_booking_confirmation(message)
                
            elif booking_type == "booking_reminder":
                await self.process_booking_reminder(message)
                
            elif booking_type == "booking_cancellation":
                await self.process_booking_cancellation(message)
                
            elif booking_type == "booking_extension":
                await self.process_booking_extension(message)
                
            elif booking_type == "booking_completion":
                await self.process_booking_completion(message)
            
            # Send notifications based on user preferences
            tasks = []
            
            if "email" in notify_by and user_email:
                tasks.append(self.send_email_notification(booking_type, message))
            
            if "sms" in notify_by and user_phone:
                tasks.append(self.send_sms_notification(booking_type, message))
            
            if "push" in notify_by and user_id:
                tasks.append(self.send_push_notification(booking_type, message))
            
            if tasks:
                await asyncio.gather(*tasks)
            
            # Schedule reminders for future bookings
            if booking_type == "booking_confirmation":
                await self.schedule_reminders(message)
            
            # Audit log
            audit_log(
                self.logger,
                action=f"BOOKING_{booking_type.upper()}",
                resource="booking",
                resource_id=booking_id,
                user_id=user_id,
                details={
                    "notification_channels": notify_by,
                    "parking": message.get("parking_name"),
                    "amount": message.get("amount")
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process booking message: {e}", exc_info=True)
            return False
    
    async def process_booking_confirmation(self, data: Dict[str, Any]) -> None:
        """
        Process booking confirmation.
        """
        self.logger.info(f"Booking confirmed: {data['booking_id']}")
        
        # Additional business logic for confirmed bookings
        # e.g., update analytics, send to CRM, etc.
    
    async def process_booking_reminder(self, data: Dict[str, Any]) -> None:
        """
        Process booking reminder.
        """
        self.logger.info(f"Booking reminder: {data['booking_id']}")
    
    async def process_booking_cancellation(self, data: Dict[str, Any]) -> None:
        """
        Process booking cancellation.
        """
        self.logger.info(f"Booking cancelled: {data['booking_id']}")
        
        # Cancel any scheduled reminders
        await self.cancel_reminders(data['booking_id'])
    
    async def process_booking_extension(self, data: Dict[str, Any]) -> None:
        """
        Process booking extension.
        """
        self.logger.info(f"Booking extended: {data['booking_id']}")
        
        # Reschedule reminders
        await self.cancel_reminders(data['booking_id'])
        await self.schedule_reminders(data)
    
    async def process_booking_completion(self, data: Dict[str, Any]) -> None:
        """
        Process booking completion.
        """
        self.logger.info(f"Booking completed: {data['booking_id']}")
        
        # Send feedback request
        await self.schedule_feedback_request(data)
    
    async def send_email_notification(self, notification_type: str, data: Dict[str, Any]) -> None:
        """
        Send email notification for booking.
        """
        template_map = {
            "booking_confirmation": "booking_confirmation",
            "booking_reminder": "booking_reminder",
            "booking_cancellation": "booking_cancellation",
            "booking_extension": "booking_extension",
            "booking_completion": "booking_completion"
        }
        
        template = template_map.get(notification_type)
        if not template:
            self.logger.warning(f"No email template for {notification_type}")
            return
        
        # Prepare email data
        email_data = {
            "type": "email",
            "to": [data["user_email"]],
            "subject": self.get_email_subject(notification_type, data),
            "template": f"booking/{template}",
            "context": {
                "user_name": data.get("user_name", "Valued Customer"),
                "booking_id": data["booking_id"],
                "parking_name": data["parking_name"],
                "spot_number": data["spot_number"],
                "vehicle_plate": data["vehicle_plate"],
                "start_time": data["start_time"],
                "end_time": data["end_time"],
                "amount": data.get("amount"),
                "currency": data.get("currency", "USD"),
                "cancel_link": self.generate_cancel_link(data),
                "extend_link": self.generate_extend_link(data)
            },
            "priority": "high" if notification_type == "booking_confirmation" else "normal",
            "metadata": {
                "booking_id": data["booking_id"],
                "type": notification_type
            }
        }
        
        # Publish to email queue
        await email_producer.publish_email(email_data)
    
    async def send_sms_notification(self, notification_type: str, data: Dict[str, Any]) -> None:
        """
        Send SMS notification for booking.
        """
        template_map = {
            "booking_confirmation": "booking_confirmation",
            "booking_reminder": "booking_reminder",
            "booking_cancellation": "booking_cancellation",
            "booking_extension": "booking_extension",
            "booking_completion": "booking_completion"
        }
        
        template = template_map.get(notification_type)
        if not template:
            return
        
        # Prepare SMS data
        sms_data = {
            "type": "sms",
            "to": [data["user_phone"]],
            "template": f"booking/{template}",
            "context": {
                "parking_name": data["parking_name"],
                "spot_number": data["spot_number"],
                "vehicle_plate": data["vehicle_plate"],
                "start_time": self.format_time(data["start_time"]),
                "end_time": self.format_time(data["end_time"]),
                "amount": data.get("amount")
            },
            "priority": "high" if notification_type == "booking_confirmation" else "normal",
            "metadata": {
                "booking_id": data["booking_id"],
                "type": notification_type
            }
        }
        
        # Publish to SMS queue
        await sms_producer.publish_sms(sms_data)
    
    async def send_push_notification(self, notification_type: str, data: Dict[str, Any]) -> None:
        """
        Send push notification for booking.
        """
        titles = {
            "booking_confirmation": "Booking Confirmed",
            "booking_reminder": "Booking Reminder",
            "booking_cancellation": "Booking Cancelled",
            "booking_extension": "Booking Extended",
            "booking_completion": "Booking Complete"
        }
        
        messages = {
            "booking_confirmation": f"Your booking at {data['parking_name']} (Spot {data['spot_number']}) is confirmed",
            "booking_reminder": f"Reminder: Your parking session starts in 30 minutes at {data['parking_name']}",
            "booking_cancellation": f"Your booking at {data['parking_name']} has been cancelled",
            "booking_extension": f"Your booking at {data['parking_name']} has been extended",
            "booking_completion": f"Your parking session at {data['parking_name']} is complete"
        }
        
        # Prepare push data
        push_data = {
            "type": "push",
            "tokens": [],  # Would need to get user's device tokens
            "title": titles.get(notification_type, "Booking Update"),
            "body": messages.get(notification_type, ""),
            "data": {
                "booking_id": data["booking_id"],
                "type": notification_type,
                "click_action": "OPEN_BOOKING"
            },
            "priority": "high",
            "metadata": {
                "booking_id": data["booking_id"],
                "type": notification_type
            }
        }
        
        # Publish to push queue
        await push_producer.publish_push(push_data)
    
    async def schedule_reminders(self, data: Dict[str, Any]) -> None:
        """
        Schedule reminders for booking.
        """
        try:
            start_time = datetime.fromisoformat(data["start_time"].replace('Z', '+00:00'))
            booking_id = data["booking_id"]
            
            # Schedule 30-minute reminder
            reminder_time = start_time - timedelta(minutes=30)
            if reminder_time > datetime.utcnow():
                delay = (reminder_time - datetime.utcnow()).total_seconds()
                
                # Store reminder for cancellation if needed
                if booking_id not in self.booking_reminders:
                    self.booking_reminders[booking_id] = []
                
                # Schedule task
                task = asyncio.create_task(
                    self.send_reminder_after_delay(delay, data, "30_minutes")
                )
                self.booking_reminders[booking_id].append(task)
                
                self.logger.info(f"Scheduled 30-minute reminder for booking {booking_id}")
            
            # Schedule 5-minute reminder
            reminder_time = start_time - timedelta(minutes=5)
            if reminder_time > datetime.utcnow():
                delay = (reminder_time - datetime.utcnow()).total_seconds()
                
                task = asyncio.create_task(
                    self.send_reminder_after_delay(delay, data, "5_minutes")
                )
                self.booking_reminders[booking_id].append(task)
                
                self.logger.info(f"Scheduled 5-minute reminder for booking {booking_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to schedule reminders: {e}")
    
    async def send_reminder_after_delay(
        self,
        delay: float,
        data: Dict[str, Any],
        reminder_type: str
    ) -> None:
        """
        Send reminder after specified delay.
        """
        try:
            await asyncio.sleep(delay)
            
            # Send reminder notification
            data["type"] = "booking_reminder"
            data["reminder_type"] = reminder_type
            
            await self.process_message(data)
            
        except asyncio.CancelledError:
            self.logger.info(f"Reminder cancelled for booking {data['booking_id']}")
        except Exception as e:
            self.logger.error(f"Failed to send reminder: {e}")
    
    async def cancel_reminders(self, booking_id: str) -> None:
        """
        Cancel scheduled reminders for booking.
        """
        if booking_id in self.booking_reminders:
            for task in self.booking_reminders[booking_id]:
                task.cancel()
            
            del self.booking_reminders[booking_id]
            self.logger.info(f"Cancelled reminders for booking {booking_id}")
    
    async def schedule_feedback_request(self, data: Dict[str, Any]) -> None:
        """
        Schedule feedback request after booking completion.
        """
        try:
            # Schedule feedback request 1 hour after completion
            delay = 3600  # 1 hour in seconds
            
            async def send_feedback():
                await asyncio.sleep(delay)
                
                # Send feedback request notification
                feedback_data = data.copy()
                feedback_data["type"] = "feedback_request"
                
                await self.process_message(feedback_data)
            
            asyncio.create_task(send_feedback())
            self.logger.info(f"Scheduled feedback request for booking {data['booking_id']}")
            
        except Exception as e:
            self.logger.error(f"Failed to schedule feedback request: {e}")
    
    def get_email_subject(self, notification_type: str, data: Dict[str, Any]) -> str:
        """
        Get email subject for notification type.
        """
        subjects = {
            "booking_confirmation": f"Booking Confirmed - {data['parking_name']}",
            "booking_reminder": f"Reminder: Your parking session at {data['parking_name']}",
            "booking_cancellation": f"Booking Cancelled - {data['parking_name']}",
            "booking_extension": f"Booking Extended - {data['parking_name']}",
            "booking_completion": f"Booking Complete - {data['parking_name']}"
        }
        
        return subjects.get(notification_type, "Booking Update")
    
    def format_time(self, time_str: str) -> str:
        """
        Format time string for SMS.
        """
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.strftime("%I:%M %p")  # e.g., "10:30 AM"
        except:
            return time_str
    
    def generate_cancel_link(self, data: Dict[str, Any]) -> str:
        """
        Generate cancellation link for booking.
        """
        base_url = settings.FRONTEND_URL
        return f"{base_url}/bookings/{data['booking_id']}/cancel"
    
    def generate_extend_link(self, data: Dict[str, Any]) -> str:
        """
        Generate extension link for booking.
        """
        base_url = settings.FRONTEND_URL
        return f"{base_url}/bookings/{data['booking_id']}/extend"