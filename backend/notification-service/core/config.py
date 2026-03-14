"""
Configuration management for notification service.
"""

from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    SERVICE_NAME: str = "notification-service"
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(False, env="DEBUG")
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8001, env="PORT")
    WORKERS: int = Field(1, env="WORKERS")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    JSON_LOGS: bool = Field(True, env="JSON_LOGS")
    ENABLE_DOCS: bool = Field(True, env="ENABLE_DOCS")
    ALLOWED_ORIGINS: List[str] = Field(["*"], env="ALLOWED_ORIGINS")
    
    # RabbitMQ configuration
    RABBITMQ_HOST: str = Field("localhost", env="RABBITMQ_HOST")
    RABBITMQ_PORT: int = Field(5672, env="RABBITMQ_PORT")
    RABBITMQ_USER: str = Field("guest", env="RABBITMQ_USER")
    RABBITMQ_PASSWORD: str = Field("guest", env="RABBITMQ_PASSWORD")
    RABBITMQ_VHOST: str = Field("/", env="RABBITMQ_VHOST")
    
    # Consumer configuration
    ENABLE_EMAIL: bool = Field(True, env="ENABLE_EMAIL")
    ENABLE_SMS: bool = Field(True, env="ENABLE_SMS")
    ENABLE_PUSH: bool = Field(True, env="ENABLE_PUSH")
    ENABLE_AUDIT: bool = Field(True, env="ENABLE_AUDIT")
    ENABLE_BOOKING_NOTIFICATIONS: bool = Field(True, env="ENABLE_BOOKING_NOTIFICATIONS")
    ENABLE_PAYMENT_NOTIFICATIONS: bool = Field(True, env="ENABLE_PAYMENT_NOTIFICATIONS")
    ENABLE_USER_NOTIFICATIONS: bool = Field(True, env="ENABLE_USER_NOTIFICATIONS")
    
    # Email provider configuration
    EMAIL_PROVIDER: str = Field("smtp", env="EMAIL_PROVIDER")  # smtp, sendgrid, aws_ses
    SMTP_HOST: str = Field("smtp.gmail.com", env="SMTP_HOST")
    SMTP_PORT: int = Field(587, env="SMTP_PORT")
    SMTP_USERNAME: Optional[str] = Field(None, env="SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = Field(None, env="SMTP_PASSWORD")
    SMTP_USE_TLS: bool = Field(True, env="SMTP_USE_TLS")
    EMAIL_FROM: str = Field("noreply@parking.com", env="EMAIL_FROM")
    EMAIL_FROM_NAME: str = Field("Parking Management", env="EMAIL_FROM_NAME")
    EMAIL_PREFETCH_COUNT: int = Field(10, env="EMAIL_PREFETCH_COUNT")
    
    # SendGrid configuration
    SENDGRID_API_KEY: Optional[str] = Field(None, env="SENDGRID_API_KEY")
    SENDGRID_SANDBOX_MODE: bool = Field(False, env="SENDGRID_SANDBOX_MODE")
    
    # AWS SES configuration
    AWS_ACCESS_KEY_ID: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field("us-east-1", env="AWS_REGION")
    
    # SMS provider configuration
    SMS_PROVIDER: str = Field("twilio", env="SMS_PROVIDER")  # twilio, aws_sns, vonage
    SMS_PREFETCH_COUNT: int = Field(10, env="SMS_PREFETCH_COUNT")
    SMS_RATE_LIMIT_DELAY: float = Field(0.1, env="SMS_RATE_LIMIT_DELAY")
    SMS_STATUS_CALLBACK_URL: Optional[str] = Field(None, env="SMS_STATUS_CALLBACK_URL")
    
    # Twilio configuration
    TWILIO_ACCOUNT_SID: Optional[str] = Field(None, env="TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN: Optional[str] = Field(None, env="TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER: Optional[str] = Field(None, env="TWILIO_PHONE_NUMBER")
    TWILIO_MESSAGING_SERVICE_SID: Optional[str] = Field(None, env="TWILIO_MESSAGING_SERVICE_SID")
    
    # Vonage configuration
    VONAGE_API_KEY: Optional[str] = Field(None, env="VONAGE_API_KEY")
    VONAGE_API_SECRET: Optional[str] = Field(None, env="VONAGE_API_SECRET")
    VONAGE_PHONE_NUMBER: Optional[str] = Field(None, env="VONAGE_PHONE_NUMBER")
    
    # Push notification configuration
    PUSH_PROVIDER: str = Field("fcm", env="PUSH_PROVIDER")  # fcm, webpush
    PUSH_PREFETCH_COUNT: int = Field(10, env="PUSH_PREFETCH_COUNT")
    
    # FCM configuration
    FCM_CREDENTIALS_PATH: Optional[str] = Field(None, env="FCM_CREDENTIALS_PATH")
    FCM_PROJECT_ID: Optional[str] = Field(None, env="FCM_PROJECT_ID")
    FCM_CREDENTIALS_DICT: Optional[Dict[str, Any]] = Field(None, env="FCM_CREDENTIALS_DICT")
    
    # WebPush configuration
    VAPID_PRIVATE_KEY: Optional[str] = Field(None, env="VAPID_PRIVATE_KEY")
    VAPID_PUBLIC_KEY: Optional[str] = Field(None, env="VAPID_PUBLIC_KEY")
    VAPID_CLAIM_EMAIL: Optional[str] = Field(None, env="VAPID_CLAIM_EMAIL")
    VAPID_CLAIM_SUBJECT: Optional[str] = Field(None, env="VAPID_CLAIM_SUBJECT")
    WEB_PUSH_ICON: str = Field("/icons/icon-192.png", env="WEB_PUSH_ICON")
    WEB_PUSH_BADGE: str = Field("/icons/badge-72.png", env="WEB_PUSH_BADGE")
    
    # Template configuration
    TEMPLATE_DIR: str = Field("templates", env="TEMPLATE_DIR")
    
    # Frontend URLs
    FRONTEND_URL: str = Field("http://localhost:3000", env="FRONTEND_URL")
    SUPPORT_EMAIL: str = Field("support@parking.com", env="SUPPORT_EMAIL")
    SUPPORT_PHONE: str = Field("+1234567890", env="SUPPORT_PHONE")
    
    # Social media URLs
    SOCIAL_FACEBOOK_URL: Optional[str] = Field(None, env="SOCIAL_FACEBOOK_URL")
    SOCIAL_TWITTER_URL: Optional[str] = Field(None, env="SOCIAL_TWITTER_URL")
    SOCIAL_INSTAGRAM_URL: Optional[str] = Field(None, env="SOCIAL_INSTAGRAM_URL")
    
    # Audit configuration
    AUDIT_RETENTION_DAYS: int = Field(30, env="AUDIT_RETENTION_DAYS")
    AUDIT_PREFETCH_COUNT: int = Field(10, env="AUDIT_PREFETCH_COUNT")
    
    # Booking configuration
    BOOKING_PREFETCH_COUNT: int = Field(10, env="BOOKING_PREFETCH_COUNT")
    
    # Payment configuration
    PAYMENT_PREFETCH_COUNT: int = Field(10, env="PAYMENT_PREFETCH_COUNT")
    
    # Receipts
    RECEIPTS_URL: str = Field("https://storage.parking.com/receipts", env="RECEIPTS_URL")
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_allowed_origins(cls, v):
        """Parse allowed origins from string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()