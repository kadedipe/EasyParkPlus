"""
Service dependencies for external services.
"""

from typing import Optional
from fastapi import Request, Depends

from ....services.email import EmailService
from ....services.payment import PaymentService
from ....services.notification import NotificationService
from ....services.qr_code import QRService
from ....services.audit import AuditService
from ....services.geocoding import GeocodingService
from ....services.sms import SMSService
from ....services.storage import StorageService
from ....services.analytics import AnalyticsService
from ....services.reporting import ReportingService
from ....core.config import settings
from ....db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession


async def get_email_service() -> EmailService:
    """
    Get email service instance.
    """
    return EmailService()


async def get_payment_service() -> PaymentService:
    """
    Get payment service instance.
    """
    return PaymentService()