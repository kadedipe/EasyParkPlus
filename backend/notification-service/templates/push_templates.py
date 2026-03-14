"""
Push notification template renderer with specialized push functionality.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime

from .base import template_manager
from ..core.config import settings
from ..utils.logging_utils import get_logger


class PushTemplateRenderer:
    """
    Specialized push notification template renderer.
    """
    
    def __init__(self):
        """Initialize push template renderer."""
        self.logger = get_logger(__name__)
    
    def render(
        self,
        template_name: str,
        context: Dict[str, Any],
        platform: str = "all"
    ) -> Dict[str, Any]:
        """
        Render push notification template.
        
        Args:
            template_name: Template name
            context: Template context
            platform: Target platform (all, android, ios, web)
            
        Returns:
            Dict[str, Any]: Rendered push notification data
        """
        # Add common context
        enriched_context = self._enrich_context(context, platform)
        
        # Render template (push templates are JSON)
        rendered = template_manager.render(
            "push",
            template_name,
            enriched_context,
            format="json"
        )
        
        # Parse JSON
        try:
            push_data = json.loads(rendered)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse push template JSON: {e}")
            push_data = {
                "title": context.get("title", "Notification"),
                "body": context.get("body", ""),
                "data": {}
            }
        
        # Add platform-specific modifications
        push_data = self._apply_platform_modifications(push_data, platform)
        
        return push_data
    
    def _enrich_context(self, context: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """
        Enrich template context with common data.
        
        Args:
            context: Original context
            platform: Target platform
            
        Returns:
            Dict[str, Any]: Enriched context
        """
        enriched = context.copy()
        
        # Add common data
        enriched.update({
            "app_name": settings.PROJECT_NAME,
            "current_time": datetime.utcnow().isoformat(),
            "platform": platform
        })
        
        return enriched
    
    def _apply_platform_modifications(
        self,
        push_data: Dict[str, Any],
        platform: str
    ) -> Dict[str, Any]:
        """
        Apply platform-specific modifications.
        
        Args:
            push_data: Push notification data
            platform: Target platform
            
        Returns:
            Dict[str, Any]: Modified push data
        """
        if platform == "android":
            # Android-specific modifications
            if "android" not in push_data:
                push_data["android"] = {}
            push_data["android"]["priority"] = "high"
            
        elif platform == "ios":
            # iOS-specific modifications
            if "apns" not in push_data:
                push_data["apns"] = {}
            push_data["apns"]["headers"] = {"apns-priority": "10"}
            
        elif platform == "web":
            # Web-specific modifications
            if "webpush" not in push_data:
                push_data["webpush"] = {}
            push_data["webpush"]["headers"] = {"Urgency": "high"}
        
        return push_data


# Push templates content

# booking_confirmation.json
BOOKING_CONFIRMATION_JSON = """
{
    "title": "Booking Confirmed",
    "body": "Your parking at {{ parking_name }} (Spot {{ spot_number }}) is confirmed",
    "data": {
        "type": "booking_confirmation",
        "booking_id": "{{ booking_id }}",
        "parking_name": "{{ parking_name }}",
        "spot_number": "{{ spot_number }}",
        "start_time": "{{ start_time }}",
        "end_time": "{{ end_time }}",
        "amount": "{{ amount }}",
        "currency": "{{ currency }}",
        "click_action": "OPEN_BOOKING"
    },
    "android": {
        "notification": {
            "click_action": "OPEN_BOOKING",
            "sound": "default",
            "priority": "high",
            "default_vibrate_timings": true
        }
    },
    "apns": {
        "payload": {
            "aps": {
                "sound": "default",
                "badge": 1,
                "content-available": 1
            }
        }
    },
    "webpush": {
        "notification": {
            "icon": "{{ app_url }}/icons/icon-192.png",
            "badge": "{{ app_url }}/icons/badge-72.png",
            "vibrate": [200, 100, 200],
            "requireInteraction": true
        }
    }
}
"""

# booking_reminder.json
BOOKING_REMINDER_JSON = """
{
    "title": "Booking Reminder",
    "body": "Your parking at {{ parking_name }} starts in {{ reminder_time }}",
    "data": {
        "type": "booking_reminder",
        "booking_id": "{{ booking_id }}",
        "parking_name": "{{ parking_name }}",
        "spot_number": "{{ spot_number }}",
        "reminder_time": "{{ reminder_time }}",
        "click_action": "OPEN_BOOKING"
    }
}
"""

# payment_success.json
PAYMENT_SUCCESS_JSON = """
{
    "title": "Payment Successful",
    "body": "{{ amount|currency(currency) }} - Transaction completed",
    "data": {
        "type": "payment_success",
        "payment_id": "{{ payment_id }}",
        "amount": "{{ amount }}",
        "currency": "{{ currency }}",
        "click_action": "OPEN_PAYMENT"
    }
}
"""

# payment_failed.json
PAYMENT_FAILED_JSON = """
{
    "title": "Payment Failed",
    "body": "{{ amount|currency(currency) }} - {{ reason }}",
    "data": {
        "type": "payment_failed",
        "payment_id": "{{ payment_id }}",
        "amount": "{{ amount }}",
        "currency": "{{ currency }}",
        "reason": "{{ reason }}",
        "click_action": "UPDATE_PAYMENT"
    }
}
"""

# welcome.json
WELCOME_JSON = """
{
    "title": "Welcome to {{ app_name }}!",
    "body": "Thanks for joining. Verify your account to get started.",
    "data": {
        "type": "welcome",
        "click_action": "VERIFY_ACCOUNT"
    }
}
"""

# vehicle_detected.json
VEHICLE_DETECTED_JSON = """
{
    "title": "Vehicle Detected",
    "body": "Vehicle {{ plate_number }} entering {{ parking_name }}",
    "data": {
        "type": "vehicle_detected",
        "plate_number": "{{ plate_number }}",
        "parking_name": "{{ parking_name }}",
        "click_action": "OPEN_SESSION"
    }
}
"""

# vehicle_exited.json
VEHICLE_EXITED_JSON = """
{
    "title": "Vehicle Exited",
    "body": "Vehicle {{ plate_number }} has left. Total: {{ amount|currency(currency) }}",
    "data": {
        "type": "vehicle_exited",
        "plate_number": "{{ plate_number }}",
        "amount": "{{ amount }}",
        "currency": "{{ currency }}",
        "click_action": "OPEN_RECEIPT"
    }
}
"""

# low_balance.json
LOW_BALANCE_JSON = """
{
    "title": "Low Balance",
    "body": "Your wallet balance is {{ balance|currency(currency) }}. Add funds to continue.",
    "data": {
        "type": "low_balance",
        "balance": "{{ balance }}",
        "currency": "{{ currency }}",
        "click_action": "ADD_FUNDS"
    }
}
"""

# parking_nearby.json
PARKING_NEARBY_JSON = """
{
    "title": "Parking Nearby",
    "body": "Available spots found near {{ location }}. Book now!",
    "data": {
        "type": "parking_nearby",
        "location": "{{ location }}",
        "spots_available": "{{ spots_available }}",
        "click_action": "VIEW_PARKING"
    }
}
"""

# session_expiring.json
SESSION_EXPIRING_JSON = """
{
    "title": "Session Expiring",
    "body": "Your parking session ends in {{ minutes_left }} minutes",
    "data": {
        "type": "session_expiring",
        "booking_id": "{{ booking_id }}",
        "minutes_left": "{{ minutes_left }}",
        "click_action": "EXTEND_SESSION"
    }
}
"""

# promo_offer.json
PROMO_OFFER_JSON = """
{
    "title": "Special Offer!",
    "body": "{{ discount }}% off your next booking. Use code: {{ promo_code }}",
    "data": {
        "type": "promo_offer",
        "promo_code": "{{ promo_code }}",
        "discount": "{{ discount }}",
        "expires": "{{ expires }}",
        "click_action": "VIEW_OFFER"
    }
}
"""


# Singleton instance
push_renderer = PushTemplateRenderer()


def get_push_renderer() -> PushTemplateRenderer:
    """
    Get push renderer singleton.
    
    Returns:
        PushTemplateRenderer: Push renderer instance
    """
    return push_renderer