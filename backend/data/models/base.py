"""
Base model classes for SQLAlchemy ORM.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import BigInteger, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_base, registry

from utils.helpers import generate_uuid7, get_current_time

# Create registry and base
mapper_registry = registry()
Base = declarative_base()


class BaseModel(Base):
    """Abstract base model with common fields."""
    
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls):
        """Generate table name from class name."""
        return cls.__name__.lower()
    
    # Primary key using UUID v7 (time-ordered)
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=generate_uuid7,
        unique=True,
        nullable=False,
    )
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=get_current_time,
        nullable=False,
        index=True,
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        default=get_current_time,
        onupdate=get_current_time,
        nullable=False,
        index=True,
    )
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), nullable=True)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    
    # Version for optimistic locking
    version = Column(BigInteger, default=1, nullable=False)
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, uuid.UUID):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    def update(self, **kwargs):
        """Update model attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def soft_delete(self, user_id: Optional[uuid.UUID] = None):
        """Soft delete the record."""
        self.deleted_at = get_current_time()
        if user_id:
            self.updated_by = user_id
    
    def restore(self):
        """Restore soft-deleted record."""
        self.deleted_at = None
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None
    
    def __repr__(self):
        """String representation."""
        return f"<{self.__class__.__name__} id={self.id}>"


class AuditModel(BaseModel):
    """Base model for audit logging."""
    
    __abstract__ = True
    
    # Audit fields
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(50), nullable=True)
    request_id = Column(String(100), nullable=True, index=True)


class TenantModel(BaseModel):
    """Base model for multi-tenant support."""
    
    __abstract__ = True
    
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)


class VersionedModel(BaseModel):
    """Base model with version tracking."""
    
    __abstract__ = True
    
    @declared_attr
    def __mapper_args__(cls):
        """Configure version id column."""
        return {
            "version_id_col": cls.version,
            "version_id_generator": False,
        }