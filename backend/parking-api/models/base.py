"""
Base model classes and mixins for all database models.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Boolean, JSON, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """
    Base class for all database models.
    """
    
    __abstract__ = True
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
        server_default=func.gen_random_uuid()
    )
    
    def dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def update(self, **kwargs) -> None:
        """Update model attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class TimestampMixin:
    """
    Mixin for adding created_at and updated_at timestamps.
    """
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.
    """
    
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    def soft_delete(self) -> None:
        """Mark record as deleted."""
        self.is_deleted = True
        self.deleted_at = func.now()


class AuditMixin:
    """
    Mixin for audit fields (created_by, updated_by).
    """
    
    created_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        index=True
    )
    
    updated_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        nullable=True
    )


class VersionMixin:
    """
    Mixin for optimistic locking with version number.
    """
    
    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False
    )


class JSONFieldsMixin:
    """
    Mixin for adding JSON fields support.
    """
    
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        default={}
    )


# SQLAlchemy event listeners for automatic updated_at
@event.listens_for(TimestampMixin, 'before_update', propagate=True)
def update_timestamp(mapper, connection, target):
    """Automatically update updated_at timestamp."""
    if hasattr(target, 'updated_at'):
        target.updated_at = func.now()