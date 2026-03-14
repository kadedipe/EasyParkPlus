"""
Vehicle model for user vehicles.
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .reservation import Reservation


class VehicleType(str, enum.Enum):
    """Vehicle type enumeration."""
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    TRUCK = "truck"
    SUV = "suv"
    VAN = "van"
    EV = "ev"
    HYBRID = "hybrid"


class Vehicle(Base, TimestampMixin):
    """
    Vehicle model for user vehicles.
    """
    
    __tablename__ = "vehicles"
    
    # Foreign Keys
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Vehicle Details
    license_plate: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(VehicleType),
        nullable=False,
        default=VehicleType.CAR
    )
    
    # Vehicle Information
    make: Mapped[Optional[str]] = mapped_column(String(50))
    model: Mapped[Optional[str]] = mapped_column(String(50))
    year: Mapped[Optional[int]] = mapped_column(Integer)
    color: Mapped[Optional[str]] = mapped_column(String(30))
    
    # EV Specific
    ev_connector_type: Mapped[Optional[str]] = mapped_column(String(50))
    battery_capacity: Mapped[Optional[float]] = mapped_column(Integer)  # kWh
    
    # Preferences
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Additional Info
    registration_state: Mapped[Optional[str]] = mapped_column(String(2))
    registration_country: Mapped[Optional[str]] = mapped_column(String(2), default="US")
    insurance_provider: Mapped[Optional[str]] = mapped_column(String(100))
    insurance_policy: Mapped[Optional[str]] = mapped_column(String(50))
    insurance_expiry: Mapped[Optional[str]] = mapped_column(String(10))  # YYYY-MM-DD
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="vehicles")
    reservations: Mapped[list["Reservation"]] = relationship(
        "Reservation",
        back_populates="vehicle",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_vehicles_user_default", "user_id", "is_default"),
        Index("ix_vehicles_type", "vehicle_type"),
        Index("ix_vehicles_make_model", "make", "model"),
    )
    
    @property
    def display_name(self) -> str:
        """Get display name for vehicle."""
        if self.make and self.model:
            return f"{self.make} {self.model} ({self.license_plate})"
        return self.license_plate
    
    def __repr__(self) -> str:
        return f"<Vehicle {self.license_plate}>"