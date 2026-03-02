"""Parking spot model for the parking management system."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from ..enums import ParkingSpotType


class ParkingSpot:
    """Parking spot model representing a physical parking spot."""
    
    def __init__(
        self,
        spot_id: Optional[int] = None,
        spot_number: str = "",
        spot_type: ParkingSpotType = ParkingSpotType.STANDARD,
        level: str = "1",
        section: str = "A",
        is_active: bool = True,
        is_occupied: bool = False,
        current_vehicle_id: Optional[int] = None,
        current_reservation_id: Optional[int] = None,
        last_occupied_at: Optional[datetime] = None,
        last_vacated_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        attributes: Optional[Dict[str, Any]] = None,
        location_coordinates: Optional[Dict[str, float]] = None,
        hourly_rate: Optional[float] = None,
        features: Optional[List[str]] = None,
        maintenance_mode: bool = False,
    ):
        self.spot_id = spot_id
        self.spot_number = spot_number
        self.spot_type = spot_type
        self.level = level
        self.section = section
        self.is_active = is_active
        self.is_occupied = is_occupied
        self.current_vehicle_id = current_vehicle_id
        self.current_reservation_id = current_reservation_id
        self.last_occupied_at = last_occupied_at
        self.last_vacated_at = last_vacated_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at
        self.attributes = attributes or {}
        self.location_coordinates = location_coordinates or {}
        self.hourly_rate = hourly_rate
        self.features = features or []
        self.maintenance_mode = maintenance_mode
    
    @property
    def is_available(self) -> bool:
        """Check if spot is available for reservation."""
        return self.is_active and not self.is_occupied and not self.maintenance_mode
    
    @property
    def display_name(self) -> str:
        """Get display name for the spot."""
        return f"{self.section}{self.spot_number}"
    
    def occupy(self, vehicle_id: int, reservation_id: int) -> None:
        """Occupy the parking spot."""
        self.is_occupied = True
        self.current_vehicle_id = vehicle_id
        self.current_reservation_id = reservation_id
        self.last_occupied_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def vacate(self) -> None:
        """Vacate the parking spot."""
        self.is_occupied = False
        self.current_vehicle_id = None
        self.current_reservation_id = None
        self.last_vacated_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert parking spot to dictionary."""
        return {
            "spot_id": self.spot_id,
            "spot_number": self.spot_number,
            "display_name": self.display_name,
            "spot_type": self.spot_type.value if self.spot_type else None,
            "level": self.level,
            "section": self.section,
            "is_active": self.is_active,
            "is_occupied": self.is_occupied,
            "is_available": self.is_available,
            "current_vehicle_id": self.current_vehicle_id,
            "current_reservation_id": self.current_reservation_id,
            "last_occupied_at": self.last_occupied_at.isoformat() if self.last_occupied_at else None,
            "last_vacated_at": self.last_vacated_at.isoformat() if self.last_vacated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "attributes": self.attributes,
            "location_coordinates": self.location_coordinates,
            "hourly_rate": self.hourly_rate,
            "features": self.features,
            "maintenance_mode": self.maintenance_mode,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParkingSpot':
        """Create parking spot from dictionary."""
        return cls(
            spot_id=data.get('spot_id'),
            spot_number=data.get('spot_number', ''),
            spot_type=ParkingSpotType(data['spot_type']) if data.get('spot_type') else None,
            level=data.get('level', '1'),
            section=data.get('section', 'A'),
            is_active=data.get('is_active', True),
            is_occupied=data.get('is_occupied', False),
            current_vehicle_id=data.get('current_vehicle_id'),
            current_reservation_id=data.get('current_reservation_id'),
            last_occupied_at=datetime.fromisoformat(data['last_occupied_at']) if data.get('last_occupied_at') else None,
            last_vacated_at=datetime.fromisoformat(data['last_vacated_at']) if data.get('last_vacated_at') else None,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            attributes=data.get('attributes'),
            location_coordinates=data.get('location_coordinates'),
            hourly_rate=data.get('hourly_rate'),
            features=data.get('features'),
            maintenance_mode=data.get('maintenance_mode', False),
        )