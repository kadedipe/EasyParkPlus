"""
Parking spot model for managing parking spaces.
"""

from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Enum, JSON,
    ForeignKey, Index, UniqueConstraint, Text, ARRAY
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from .base import Base, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from .reservation import Reservation
    from .review import Review
    from .maintenance import MaintenanceRecord


class ParkingSpotType(str, enum.Enum):
    """Parking spot type enumeration."""
    STANDARD = "standard"
    HANDICAPPED = "handicapped"
    EV = "ev"
    MOTORCYCLE = "motorcycle"
    COMPACT = "compact"
    LARGE = "large"
    VIP = "vip"
    STAFF = "staff"
    VISITOR = "visitor"


class ParkingSpotStatus(str, enum.Enum):
    """Parking spot status enumeration."""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"


class ParkingSpot(Base, TimestampMixin, SoftDeleteMixin):
    """
    Parking spot model for managing parking spaces.
    """
    
    __tablename__ = "parking_spots"
    
    # Spot Identification
    spot_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )
    spot_type: Mapped[ParkingSpotType] = mapped_column(
        Enum(ParkingSpotType),
        nullable=False,
        default=ParkingSpotType.STANDARD,
        index=True
    )
    
    # Location
    floor: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    row: Mapped[Optional[str]] = mapped_column(String(5))
    column: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Status
    status: Mapped[ParkingSpotStatus] = mapped_column(
        Enum(ParkingSpotStatus),
        nullable=False,
        default=ParkingSpotStatus.AVAILABLE,
        index=True
    )
    
    # Pricing
    base_price_per_hour: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=2.50
    )
    dynamic_price_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    current_price_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    
    # Features
    features: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        default=[]
    )
    
    # EV Charging
    has_ev_charger: Mapped[bool] = mapped_column(Boolean, default=False)
    ev_charger_type: Mapped[Optional[str]] = mapped_column(String(50))
    ev_charger_power: Mapped[Optional[int]] = mapped_column(Integer)  # kW
    
    # Dimensions (in meters)
    length: Mapped[Optional[float]] = mapped_column(Float)
    width: Mapped[Optional[float]] = mapped_column(Float)
    height_limit: Mapped[Optional[float]] = mapped_column(Float)
    
    # Location on map
    coordinates: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Sensor Information
    has_sensor: Mapped[bool] = mapped_column(Boolean, default=True)
    sensor_id: Mapped[Optional[str]] = mapped_column(String(50))
    last_sensor_reading: Mapped[Optional[dict]] = mapped_column(JSON)
    last_sensor_update: Mapped[Optional[str]] = mapped_column(DateTime(timezone=True))
    
    # Camera Information
    has_camera: Mapped[bool] = mapped_column(Boolean, default=False)
    camera_id: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Restrictions
    min_height_required: Mapped[Optional[float]] = mapped_column(Float)
    max_weight_kg: Mapped[Optional[float]] = mapped_column(Float)
    restricted_to_roles: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String))
    
    # Statistics
    total_reservations: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    average_rating: Mapped[Optional[float]] = mapped_column(Float)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    
    # Relationships
    reservations: Mapped[List["Reservation"]] = relationship(
        "Reservation",
        back_populates="spot",
        cascade="all, delete-orphan"
    )
    
    reviews: Mapped[List["Review"]] = relationship(
        "Review",
        back_populates="spot",
        cascade="all, delete-orphan"
    )
    
    maintenance_records: Mapped[List["MaintenanceRecord"]] = relationship(
        "MaintenanceRecord",
        back_populates="spot",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_parking_spots_location", "floor", "section"),
        Index("ix_parking_spots_type_status", "spot_type", "status"),
        Index("ix_parking_spots_features", "features", postgresql_using="gin"),
        UniqueConstraint("floor", "section", "spot_number", name="uq_parking_spot_location"),
    )
    
    @property
    def current_price(self) -> float:
        """Get current price per hour."""
        return self.base_price_per_hour * self.current_price_multiplier
    
    @property
    def is_available(self) -> bool:
        """Check if spot is available."""
        return self.status == ParkingSpotStatus.AVAILABLE
    
    @property
    def display_name(self) -> str:
        """Get display name for spot."""
        return f"{self.section}{self.spot_number}"
    
    def __repr__(self) -> str:
        return f"<ParkingSpot {self.spot_number}>"