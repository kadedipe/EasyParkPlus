"""
SMS template renderer with specialized SMS functionality.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base import template_manager
from ..core.config import settings
from ..utils.logging_utils import get_logger


class SMSTemplateRenderer:
    """
    Specialized SMS template renderer.
    """
    
    def __init__(self):
        """Initialize SMS template renderer."""
        self.logger = get_logger(__name__)
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render SMS template.
        
        Args:
            template_name: Template name
            context: Template context
            
        Returns:
            str: Rendered SMS text
        """
        # Add common context
        enriched_context = self._enrich_context(context)
        
        # Render template
        sms_text = template_manager.render(
            "sms",
            template_name,
            enriched_context,
            format="txt"
        )
        
        # Ensure SMS doesn't exceed character limit
        if len(sms_text) > 160:
            self.logger.warning(
                f"SMS template {template_name} exceeds 160 characters "
                f"({len(sms_text)} chars)"
            )
        
        return sms_text.strip()
    
    def _enrich_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich template context with common data.
        
        Args:
            context: Original context
            
        Returns:
            Dict[str, Any]: Enriched context
        """
        enriched = context.copy()
        
        # Add common data
        enriched.update({
            "app_name": settings.PROJECT_NAME_SHORT,
            "support_phone": settings.SUPPORT_PHONE,
            "current_time": datetime.utcnow().strftime("%I:%M %p")
        })
        
        return enriched


# SMS templates content

# verification_code.txt
VERIFICATION_CODE_TXT = """
Your {{ app_name }} verification code is: {{ code }}
Valid for {{ expires_in }} minutes.
"""

# booking_confirmation.txt
BOOKING_CONFIRMATION_TXT = """
Booking confirmed! {{ parking_name }} - Spot {{ spot_number }}
{{ start_time|date("%I:%M %p") }} to {{ end_time|date("%I:%M %p") }}
Amount: {{ amount|currency(currency) }}
Show QR code at entrance
"""

# booking_reminder.txt
BOOKING_REMINDER_TXT = """
Reminder: Your parking at {{ parking_name }} starts in {{ reminder_time }}
Spot: {{ spot_number }}
Vehicle: {{ vehicle_plate }}
"""

# booking_cancellation.txt
BOOKING_CANCELLATION_TXT = """
Booking cancelled: {{ parking_name }} - Spot {{ spot_number }}
Refund of {{ amount|currency(currency) }} will be processed in 3-5 business days.
"""

# payment_success.txt
PAYMENT_SUCCESS_TXT = """
Payment successful: {{ amount|currency(currency) }}
Transaction: {{ payment_id }}
Receipt: {{ receipt_url }}
"""

# payment_failed.txt
PAYMENT_FAILED_TXT = """
Payment failed: {{ amount|currency(currency) }}
Reason: {{ reason }}
Please update payment method in app.
"""

# welcome.txt
WELCOME_TXT = """
Welcome to {{ app_name }}! Verify your account: {{ verify_link }}
Enjoy hassle-free parking!
"""

# password_reset.txt
PASSWORD_RESET_TXT = """
Password reset link: {{ reset_link }}
Valid for {{ expires_in }} hours.
If you didn't request this, ignore this message.
"""

# low_balance.txt
LOW_BALANCE_TXT = """
Your {{ app_name }} wallet balance is low: {{ balance|currency(currency) }}
Add funds to continue using our services.
"""

# exit_reminder.txt
EXIT_REMINDER_TXT = """
Your parking session ends in {{ minutes_left }} minutes at {{ parking_name }}
Extend via app if needed.
"""


# Singleton instance
sms_renderer = SMSTemplateRenderer()


def get_sms_renderer() -> SMSTemplateRenderer:
    """
    Get SMS renderer singleton.
    
    Returns:
        SMSTemplateRenderer: SMS renderer instance
    """
    return sms_renderer