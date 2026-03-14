"""
Base database classes and configurations.
"""

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
import uuid


class Base(DeclarativeBase):
    """
    Base class for all database models.
    """
    
    __abstract__ = True
    
    # Common primary key for all models
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    
    @declared_attr
    def __tablename__(cls) -> str:
        """
        Generate table name automatically from class name.
        """
        return cls.__name__.lower() + "s"
    
    def dict(self):
        """
        Convert model instance to dictionary.
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


class TimestampMixin:
    """
    Mixin for timestamp fields.
    """
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.
    """
    
    deleted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    
    def soft_delete(self):
        """
        Soft delete the record.
        """
        self.deleted_at = datetime.utcnow()
        self.is_deleted = True