"""
Email template renderer with specialized email functionality.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from .base import template_manager
from ..core.config import settings
from ..utils.logging_utils import get_logger


class EmailTemplateRenderer:
    """
    Specialized email template renderer.
    """
    
    def __init__(self):
        """Initialize email template renderer."""
        self.logger = get_logger(__name__)
    
    def render(
        self,
        template_name: str,
        context: Dict[str, Any],
        locale: str = "en"
    ) -> Tuple[str, str]:
        """
        Render both HTML and text versions of email template.
        
        Args:
            template_name: Template name
            context: Template context
            locale: Locale for internationalization
            
        Returns:
            Tuple[str, str]: (html_content, text_content)
        """
        # Add common context
        enriched_context = self._enrich_context(context, locale)
        
        # Render HTML version
        html_content = template_manager.render(
            "email",
            template_name,
            enriched_context,
            format="html"
        )
        
        # Render text version
        try:
            text_content = template_manager.render(
                "email",
                template_name,
                enriched_context,
                format="txt"
            )
        except Exception:
            # If text template doesn't exist, create simple text from HTML
            text_content = self._html_to_text(html_content)
        
        return html_content, text_content
    
    def render_subject(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render email subject from template.
        
        Args:
            template_name: Template name
            context: Template context
            
        Returns:
            str: Email subject
        """
        try:
            return template_manager.render(
                "email",
                f"{template_name}_subject",
                context,
                format="txt"
            ).strip()
        except Exception:
            # Fallback to default subject
            return "Notification from Parking Management"
    
    def _enrich_context(self, context: Dict[str, Any], locale: str) -> Dict[str, Any]:
        """
        Enrich template context with common data.
        
        Args:
            context: Original context
            locale: Locale
            
        Returns:
            Dict[str, Any]: Enriched context
        """
        enriched = context.copy()
        
        # Add common data
        enriched.update({
            "app_name": settings.PROJECT_NAME,
            "app_url": settings.FRONTEND_URL,
            "support_email": settings.SUPPORT_EMAIL,
            "current_year": datetime.utcnow().year,
            "locale": locale,
            "logo_url": f"{settings.FRONTEND_URL}/logo.png",
            "facebook_url": settings.SOCIAL_FACEBOOK_URL,
            "twitter_url": settings.SOCIAL_TWITTER_URL,
            "instagram_url": settings.SOCIAL_INSTAGRAM_URL
        })
        
        # Add user name if available
        if "user" in context:
            user = context["user"]
            if isinstance(user, dict):
                enriched["user_name"] = user.get("full_name") or user.get("name") or user.get("email")
            else:
                enriched["user_name"] = str(user)
        
        return enriched
    
    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to plain text.
        
        Args:
            html: HTML content
            
        Returns:
            str: Plain text content
        """
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Decode HTML entities
        import html
        text = html.unescape(text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()


# Email templates content

# booking_confirmation.html
BOOKING_CONFIRMATION_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #4CAF50;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }
        .content {
            background-color: #f9f9f9;
            padding: 30px;
            border-radius: 0 0 5px 5px;
        }
        .booking-details {
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            margin: 20px 0;
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        .detail-label {
            font-weight: bold;
            color: #666;
        }
        .detail-value {
            color: #333;
        }
        .total-row {
            display: flex;
            justify-content: space-between;
            padding: 15px 0;
            font-size: 1.2em;
            font-weight: bold;
            border-top: 2px solid #4CAF50;
            margin-top: 10px;
        }
        .button {
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            padding: 12px 30px;
            border-radius: 5px;
            margin-top: 20px;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #999;
            font-size: 0.9em;
        }
        .qr-code {
            text-align: center;
            margin: 20px 0;
        }
        .map-link {
            color: #4CAF50;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Booking Confirmed!</h1>
        <p>Your parking spot is reserved</p>
    </div>
    
    <div class="content">
        <p>Dear {{ user_name }},</p>
        
        <p>Your booking has been confirmed. Here are the details:</p>
        
        <div class="booking-details">
            <div class="detail-row">
                <span class="detail-label">Booking ID:</span>
                <span class="detail-value">#{{ booking_id }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Parking Location:</span>
                <span class="detail-value">{{ parking_name }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Spot Number:</span>
                <span class="detail-value">{{ spot_number }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Vehicle Plate:</span>
                <span class="detail-value">{{ vehicle_plate }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Start Time:</span>
                <span class="detail-value">{{ start_time|date("%B %d, %Y at %I:%M %p") }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">End Time:</span>
                <span class="detail-value">{{ end_time|date("%B %d, %Y at %I:%M %p") }}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Duration:</span>
                <span class="detail-value">{{ duration }}</span>
            </div>
            <div class="total-row">
                <span>Total Amount:</span>
                <span>{{ amount|currency(currency) }}</span>
            </div>
        </div>
        
        <div class="qr-code">
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={{ booking_id }}" 
                 alt="QR Code" style="border-radius: 5px;">
            <p>Show this QR code at the entrance</p>
        </div>
        
        <p style="text-align: center;">
            <a href="{{ map_link }}" class="map-link">📍 View on Map</a>
        </p>
        
        <p style="text-align: center;">
            <a href="{{ cancel_link }}" class="button">Cancel Booking</a>
            <a href="{{ extend_link }}" class="button">Extend Booking</a>
        </p>
        
        <p><strong>Important Information:</strong></p>
        <ul>
            <li>Please arrive at least 15 minutes before your booking time</li>
            <li>Have your QR code ready at the entrance</li>
            <li>Free cancellation up to 1 hour before start time</li>
            <li>Contact support at {{ support_email }} if you need assistance</li>
        </ul>
    </div>
    
    <div class="footer">
        <p>Thank you for choosing {{ app_name }}!</p>
        <p>&copy; {{ current_year }} {{ app_name }}. All rights reserved.</p>
        <p>
            <a href="{{ app_url }}">Website</a> |
            <a href="{{ facebook_url }}">Facebook</a> |
            <a href="{{ twitter_url }}">Twitter</a> |
            <a href="{{ instagram_url }}">Instagram</a>
        </p>
    </div>
</body>
</html>
"""

# booking_confirmation.txt
BOOKING_CONFIRMATION_TXT = """
Booking Confirmed!
==================
Your parking spot is reserved

Dear {{ user_name }},

Your booking has been confirmed. Here are the details:

Booking ID: #{{ booking_id }}
Parking Location: {{ parking_name }}
Spot Number: {{ spot_number }}
Vehicle Plate: {{ vehicle_plate }}
Start Time: {{ start_time|date("%B %d, %Y at %I:%M %p") }}
End Time: {{ end_time|date("%B %d, %Y at %I:%M %p") }}
Duration: {{ duration }}
Total Amount: {{ amount|currency(currency) }}

Important Information:
- Please arrive at least 15 minutes before your booking time
- Have your QR code ready at the entrance
- Free cancellation up to 1 hour before start time
- Contact support at {{ support_email }} if you need assistance

Manage your booking:
- Cancel: {{ cancel_link }}
- Extend: {{ extend_link }}
- View on Map: {{ map_link }}

Thank you for choosing {{ app_name }}!

© {{ current_year }} {{ app_name }}. All rights reserved.
"""

# booking_reminder.html
BOOKING_REMINDER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #2196F3;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }
        .content {
            background-color: #f9f9f9;
            padding: 30px;
            border-radius: 0 0 5px 5px;
        }
        .reminder-box {
            background-color: #FFF3CD;
            border: 1px solid #FFE69C;
            color: #856404;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            text-align: center;
        }
        .booking-summary {
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            margin: 20px 0;
        }
        .button {
            display: inline-block;
            background-color: #2196F3;
            color: white;
            text-decoration: none;
            padding: 12px 30px;
            border-radius: 5px;
            margin: 5px;
        }
        .button-secondary {
            background-color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Booking Reminder</h1>
        <p>Your parking session starts in {{ reminder_time }}</p>
    </div>
    
    <div class="content">
        <p>Dear {{ user_name }},</p>
        
        <div class="reminder-box">
            <strong>⏰ Reminder:</strong> Your parking session starts in {{ reminder_time }}
        </div>
        
        <div class="booking-summary">
            <h3>Booking Summary</h3>
            <p><strong>Booking ID:</strong> #{{ booking_id }}</p>
            <p><strong>Location:</strong> {{ parking_name }}</p>
            <p><strong>Spot:</strong> {{ spot_number }}</p>
            <p><strong>Vehicle:</strong> {{ vehicle_plate }}</p>
            <p><strong>Start:</strong> {{ start_time|date("%I:%M %p") }}</p>
            <p><strong>End:</strong> {{ end_time|date("%I:%M %p") }}</p>
        </div>
        
        <p style="text-align: center;">
            <a href="{{ directions_link }}" class="button">Get Directions</a>
            <a href="{{ cancel_link }}" class="button button-secondary">Cancel</a>
            <a href="{{ extend_link }}" class="button button-secondary">Extend</a>
        </p>
        
        <p><strong>Quick Tips:</strong></p>
        <ul>
            <li>Have your QR code ready for quick entry</li>
            <li>The parking lot may be busy during peak hours</li>
            <li>You can extend your session remotely if needed</li>
        </ul>
    </div>
</body>
</html>
"""

# payment_success.html
PAYMENT_SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #28a745;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }
        .content {
            background-color: #f9f9f9;
            padding: 30px;
            border-radius: 0 0 5px 5px;
        }
        .payment-details {
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            margin: 20px 0;
        }
        .amount-large {
            font-size: 2em;
            color: #28a745;
            text-align: center;
            margin: 20px 0;
        }
        .receipt-link {
            text-align: center;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Payment Successful!</h1>
        <p>Thank you for your payment</p>
    </div>
    
    <div class="content">
        <p>Dear {{ user_name }},</p>
        
        <p>Your payment has been successfully processed.</p>
        
        <div class="amount-large">
            {{ amount|currency(currency) }}
        </div>
        
        <div class="payment-details">
            <h3>Payment Details</h3>
            <p><strong>Transaction ID:</strong> {{ payment_id }}</p>
            <p><strong>Date:</strong> {{ date|date("%B %d, %Y at %I:%M %p") }}</p>
            <p><strong>Payment Method:</strong> {{ payment_method }}</p>
            <p><strong>Booking ID:</strong> #{{ booking_id }}</p>
            <p><strong>Status:</strong> <span style="color: #28a745;">Completed</span></p>
        </div>
        
        <div class="receipt-link">
            <a href="{{ receipt_url }}" class="button">Download Receipt</a>
        </div>
        
        <p>If you have any questions about this payment, please contact our support team at {{ support_email }}</p>
    </div>
</body>
</html>
"""

# welcome_email.html
WELCOME_EMAIL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }
        .content {
            background-color: #f9f9f9;
            padding: 30px;
            border-radius: 0 0 5px 5px;
        }
        .features {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            margin: 30px 0;
        }
        .feature {
            flex: 1 1 45%;
            background-color: white;
            padding: 20px;
            margin: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .verify-button {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            padding: 15px 40px;
            border-radius: 25px;
            margin: 20px 0;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Welcome to {{ app_name }}!</h1>
        <p>Your premium parking solution</p>
    </div>
    
    <div class="content">
        <p>Dear {{ user_name }},</p>
        
        <p>Thank you for joining {{ app_name }}! We're excited to help you find and manage parking spaces effortlessly.</p>
        
        <div style="text-align: center;">
            <a href="{{ verify_link }}" class="verify-button">Verify Your Email</a>
        </div>
        
        <h3>What you can do with {{ app_name }}:</h3>
        
        <div class="features">
            <div class="feature">
                <h4>🔍 Find Parking</h4>
                <p>Discover available parking spots near you in real-time</p>
            </div>
            <div class="feature">
                <h4>📱 Book in Advance</h4>
                <p>Reserve your spot ahead of time and save</p>
            </div>
            <div class="feature">
                <h4>💳 Easy Payments</h4>
                <p>Secure and seamless payment options</p>
            </div>
            <div class="feature">
                <h4>⏰ Extend Remotely</h4>
                <p>Extend your parking session from anywhere</p>
            </div>
        </div>
        
        <p>Get started by verifying your email address and completing your profile.</p>
        
        <p>If you have any questions, feel free to contact our support team at {{ support_email }}</p>
        
        <p>Happy Parking!<br>The {{ app_name }} Team</p>
    </div>
</body>
</html>
"""

# password_reset.html
PASSWORD_RESET_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #dc3545;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }
        .content {
            background-color: #f9f9f9;
            padding: 30px;
            border-radius: 0 0 5px 5px;
        }
        .reset-button {
            display: inline-block;
            background-color: #dc3545;
            color: white;
            text-decoration: none;
            padding: 15px 40px;
            border-radius: 5px;
            margin: 20px 0;
            font-weight: bold;
        }
        .warning {
            background-color: #fff3cd;
            border: 1px solid #ffe69c;
            color: #856404;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Password Reset Request</h1>
    </div>
    
    <div class="content">
        <p>Hello {{ user_name }},</p>
        
        <p>We received a request to reset your password for your {{ app_name }} account.</p>
        
        <div style="text-align: center;">
            <a href="{{ reset_link }}" class="reset-button">Reset Password</a>
        </div>
        
        <div class="warning">
            <p><strong>⚠️ This link will expire in {{ expires_in }} hours.</strong></p>
            <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
        </div>
        
        <p>For security reasons, this link can only be used once. If you need to reset your password again, please request a new link.</p>
        
        <hr>
        
        <p style="color: #666; font-size: 0.9em;">
            If you're having trouble clicking the password reset button, copy and paste the URL below into your web browser:<br>
            {{ reset_link }}
        </p>
    </div>
</body>
</html>
"""


# Singleton instance
email_renderer = EmailTemplateRenderer()


def get_email_renderer() -> EmailTemplateRenderer:
    """
    Get email renderer singleton.
    
    Returns:
        EmailTemplateRenderer: Email renderer instance
    """
    return email_renderer