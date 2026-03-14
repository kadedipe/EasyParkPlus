"""
Audit log model for tracking all important actions.
"""

from typing import Optional
from sqlalchemy import (
    Column, String, Text, JSON, ForeignKey,
    DateTime, Index, Enum
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, INET
import enum

from .base import Base, TimestampMixin


class AuditAction(str, enum.Enum):
    """Audit action enumeration."""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    FAILED_LOGIN = "FAILED_LOGIN"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET = "PASSWORD_RESET"
    EMAIL_VERIFY = "EMAIL_VERIFY"
    PHONE_VERIFY = "PHONE_VERIFY"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    API_CALL = "API_CALL"
    WEBHOOK = "WEBHOOK"
    SYSTEM = "SYSTEM"


class AuditLog(Base, TimestampMixin):
    """
    Audit log model for tracking all important actions.
    """
    
    __tablename__ = "audit_logs"
    
    # Who
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True
    )
    username: Mapped[Optional[str]] = mapped_column(String(255))
    
    # What
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction),
        nullable=False,
        index=True
    )
    resource: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    
    # Details
    old_value: Mapped[Optional[JSON]] = mapped_column(JSON)
    new_value: Mapped[Optional[JSON]] = mapped_column(JSON)