"""Notification service configuration."""

from typing import Dict, Any, List

from . import config


class NotificationConfig:
    """Notification configuration."""
    
    # Default channels
    DEFAULT_CHANNELS: List[str] = ["email", "sms", "push"]
    
    # Email settings
    EMAIL_PROVIDER: str = "smtp"  # smtp, sendgrid, ses
    EMAIL_FROM: str = config.MAIL_DEFAULT_SENDER
    EMAIL_FROM_NAME: str = "Parking System"
    
    SMTP_HOST: str = config.MAIL_SERVER
    SMTP_PORT: int = config.MAIL_PORT
    SMTP_USER: str = config.MAIL_USERNAME
    SMTP_PASSWORD: str = config.MAIL_PASSWORD
    SMTP_USE_TLS: bool = config.MAIL_USE_TLS
    SMTP_USE_SSL: bool = config.MAIL_USE_SSL
    
    # SMS settings
    SMS_PROVIDER: str = "twilio"  # twilio, nexmo, etc.
    TWILIO_ACCOUNT_SID: str = config.TWILIO_ACCOUNT_SID
    TWILIO_AUTH_TOKEN: str = config.TWILIO_AUTH_TOKEN
    TWILIO_PHONE_NUMBER: str = config.TWILIO_PHONE_NUMBER
    
    # Push notification settings
    PUSH_PROVIDER: str = "firebase"  # firebase, onesignal, etc.
    FIREBASE_CREDENTIALS: str = config.FIREBASE_CREDENTIALS
    APNS_KEY_ID: str = config.APNS_KEY_ID
    APNS_TEAM_ID: str = config.APNS_TEAM_ID
    APNS_BUNDLE_ID: str = config.APNS_BUNDLE_ID
    
    # Notification templates
    TEMPLATES: Dict[str, Dict[str, Any]] = {
        "reservation_confirmation": {
            "subject": "Reservation Confirmed - Parking System",
            "email_template": "email/reservation_confirmation.html",
            "sms_template": "sms/reservation_confirmation.txt",
            "push_title": "Reservation Confirmed",
            "channels": ["email", "sms", "push"],
        },
        "reservation_reminder": {
            "subject": "Reminder: Your Parking Reservation",
            "email_template": "email/reservation_reminder.html",
            "sms_template": "sms/reservation_reminder.txt",
            "push_title": "Parking Reminder",
            "channels": ["email", "sms", "push"],
        },
        "reservation_cancelled": {
            "subject": "Reservation Cancelled",
            "email_template": "email/reservation_cancelled.html",
            "sms_template": "sms/reservation_cancelled.txt",
            "push_title": "Reservation Cancelled",
            "channels": ["email", "sms", "push"],
        },
        "payment_receipt": {
            "subject": "Payment Receipt - Parking System",
            "email_template": "email/payment_receipt.html",
            "channels": ["email"],
        },
        "payment_failed": {
            "subject": "Payment Failed - Action Required",
            "email_template": "email/payment_failed.html",
            "sms_template": "sms/payment_failed.txt",
            "push_title": "Payment Failed",
            "channels": ["email", "sms", "push"],
        },
        "waitlist_available": {
            "subject": "Spot Available - Parking System",
            "email_template": "email/waitlist_available.html",
            "sms_template": "sms/waitlist_available.txt",
            "push_title": "Spot Available",
            "channels": ["email", "sms", "push"],
        },
        "account_verification": {
            "subject": "Verify Your Email - Parking System",
            "email_template": "email/account_verification.html",
            "channels": ["email"],
        },
        "password_reset": {
            "subject": "Password Reset Request",
            "email_template": "email/password_reset.html",
            "channels": ["email"],
        },
    }
    
    # Rate limiting
    MAX_EMAILS_PER_MINUTE: int = 100
    MAX_SMS_PER_MINUTE: int = 50
    MAX_PUSH_PER_MINUTE: int = 200
    
    # Retry settings
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY_SECONDS: int = 60


notification_config = NotificationConfig()