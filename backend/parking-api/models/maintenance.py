"""
Maintenance model for parking spot maintenance records.
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import (
    Column, String, Text, DateTime, Enum, ForeignKey,
    Float, Boolean, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, AuditMixin


class MaintenanceType(str, enum.Enum):
    """Maintenance type enumeration."""
    ROUTINE = "routine"
    REPAIR = "repair"
    EMERGENCY = "emergency"
    CLEANING = "cleaning"
    INSPECTION = "inspection"
    UPGRADE = "upgrade"
    SENSOR_CALIBRATION = "sensor_calibration"


class MaintenanceStatus(str, enum.Enum):
    """Maintenance status enumeration."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DELAYED = "delayed"


class SeverityLevel(str, enum.Enum):
    """Severity level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MaintenanceRecord(Base, TimestampMixin, AuditMixin):
    """
    Maintenance model for parking spot maintenance records.
    """
    
    __tablename__ = "maintenance_records"
    
    # Foreign Keys
    spot_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("parking_spots.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    reported_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Maintenance Details
    type: Mapped[MaintenanceType] = mapped_column(
        Enum(MaintenanceType),
        nullable=False
    )
    status: Mapped[MaintenanceStatus] = mapped_column(
        Enum(MaintenanceStatus),
        nullable=False,
        default=MaintenanceStatus.SCHEDULED,
        index=True
    )
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel),
        nullable=False,
        default=SeverityLevel.MEDIUM
    )
    
    # Description
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Schedule
    scheduled_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    estimated_duration_hours: Mapped[Optional[float]] = mapped_column(Float)
    
    # Cost
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float)
    actual_cost: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    
    # Parts and Materials
    parts_used: Mapped[Optional[list]] = mapped_column(JSON, default=[])
    
    # Vendor
    vendor_name: Mapped[Optional[str]] = mapped_column(String(100))
    vendor_contact: Mapped[Optional[str]] = mapped_column(String(100))
    vendor_invoice: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Impact
    spot_unavailable: Mapped[bool] = mapped_column(Boolean, default=True)
    affected_reservations: Mapped[Optional[list]] = mapped_column(JSON, default=[])
    
    # Completion
    completed_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    completed_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Quality Assurance
    qa_check_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    qa_checked_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False))
    qa_checked_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    qa_notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Attachments
    attachments: Mapped[Optional[list]] = mapped_column(JSON, default=[])
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Relationships
    spot: Mapped["ParkingSpot"] = relationship(
        "ParkingSpot",
        back_populates="maintenance_records"
    )
    reporter: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reported_by]
    )
    assignee: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_to]
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_maintenance_spot_status", "spot_id", "status"),
        Index("ix_maintenance_scheduled", "scheduled_date"),
        Index("ix_maintenance_type_severity", "type", "severity"),
    )
    
    @property
    def is_overdue(self) -> bool:
        """Check if maintenance is overdue."""
        if self.status in [MaintenanceStatus.COMPLETED, MaintenanceStatus.CANCELLED]:
            return False
        if self.scheduled_date and self.scheduled_date < datetime.utcnow():
            return True
        return False
    
    def __repr__(self) -> str:
        return f"<MaintenanceRecord {self.id} - {self.status.value}>"