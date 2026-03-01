"""Vehicle model for the parking management system.

This module defines the Vehicle model which represents vehicles owned by users
that can be used for parking reservations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from ..enums import VehicleType


class Vehicle:
    """Vehicle model representing a user's vehicle.
    
    A vehicle belongs to a user and contains information such as make, model,
    license plate, and vehicle type. Vehicles can be marked as default for
    quicker reservations.
    
    Attributes:
        vehicle_id: Unique identifier for the vehicle
        user_id: ID of the user who owns this vehicle
        make: Vehicle manufacturer (e.g., Toyota, Honda)
        model: Vehicle model (e.g., Camry, Civic)
        year: Manufacturing year
        color: Vehicle color
        license_plate: License plate number (unique)
        vehicle_type: Type of vehicle (sedan, SUV, etc.)
        is_default: Whether this is the user's default vehicle
        is_active: Whether the vehicle is active (not deleted)
        created_at: Timestamp when the vehicle was added
        updated_at: Timestamp when the vehicle was last updated
        last_used_at: Timestamp when the vehicle was last used for a reservation
        notes: Additional notes about the vehicle
        metadata: Additional metadata (insurance info, etc.)
    """
    
    # Valid years range
    MIN_YEAR = 1900
    MAX_YEAR = datetime.now().year + 1  # Allow next year's models
    
    def __init__(
        self,
        vehicle_id: Optional[int] = None,
        user_id: int = 0,
        make: str = "",
        model: str = "",
        year: int = datetime.now().year,
        color: str = "",
        license_plate: str = "",
        vehicle_type: VehicleType = VehicleType.SEDAN,
        is_default: bool = False,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_used_at: Optional[datetime] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a new Vehicle instance.
        
        Args:
            vehicle_id: Unique identifier for the vehicle
            user_id: ID of the user who owns this vehicle
            make: Vehicle manufacturer
            model: Vehicle model
            year: Manufacturing year
            color: Vehicle color
            license_plate: License plate number
            vehicle_type: Type of vehicle
            is_default: Whether this is the user's default vehicle
            is_active: Whether the vehicle is active
            created_at: Creation timestamp
            updated_at: Last update timestamp
            last_used_at: Last used timestamp
            notes: Additional notes
            metadata: Additional metadata
        """
        self.vehicle_id = vehicle_id
        self.user_id = user_id
        self.make = make.strip() if make else ""
        self.model = model.strip() if model else ""
        self.year = year
        self.color = color.strip() if color else ""
        self.license_plate = license_plate.strip().upper() if license_plate else ""
        self.vehicle_type = vehicle_type
        self.is_default = is_default
        self.is_active = is_active
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at
        self.last_used_at = last_used_at
        self.notes = notes
        self.metadata = metadata or {}
    
    def __repr__(self) -> str:
        """String representation of the vehicle."""
        return f"<Vehicle {self.vehicle_id}: {self.make} {self.model} ({self.license_plate})>"
    
    def __str__(self) -> str:
        """User-friendly string representation."""
        return f"{self.year} {self.make} {self.model} - {self.license_plate}"
    
    @property
    def full_name(self) -> str:
        """Get the full vehicle name.
        
        Returns:
            Formatted string with year, make, and model
        """
        return f"{self.year} {self.make} {self.model}".strip()
    
    @property
    def display_name(self) -> str:
        """Get a display-friendly name for the vehicle.
        
        Returns:
            Short display name (e.g., "2019 Toyota Camry (ABC123)")
        """
        return f"{self.full_name} ({self.license_plate})"
    
    @property
    def age_years(self) -> float:
        """Calculate the age of the vehicle in years.
        
        Returns:
            Vehicle age in years (float)
        """
        current_year = datetime.now().year
        return current_year - self.year
    
    @property
    def is_new(self) -> bool:
        """Check if the vehicle is considered new (less than 3 years old).
        
        Returns:
            True if vehicle is less than 3 years old
        """
        return self.age_years < 3
    
    @property
    def requires_oversize_spot(self) -> bool:
        """Check if the vehicle requires an oversize parking spot.
        
        Returns:
            True for trucks, vans, and RVs
        """
        return self.vehicle_type in [
            VehicleType.TRUCK,
            VehicleType.VAN,
            VehicleType.RV
        ]
    
    @property
    def requires_ev_charging(self) -> bool:
        """Check if the vehicle requires EV charging.
        
        Returns:
            False by default - would need additional data to determine
        """
        # This would typically check metadata for EV status
        return self.metadata.get('is_electric', False)
    
    @property
    def height_clearance_required(self) -> Optional[float]:
        """Get the height clearance required in meters.
        
        Returns:
            Height in meters if specified in metadata
        """
        return self.metadata.get('height_meters')
    
    @property
    def length_meters(self) -> Optional[float]:
        """Get the vehicle length in meters.
        
        Returns:
            Length in meters if specified in metadata
        """
        return self.metadata.get('length_meters')
    
    @property
    def width_meters(self) -> Optional[float]:
        """Get the vehicle width in meters.
        
        Returns:
            Width in meters if specified in metadata
        """
        return self.metadata.get('width_meters')
    
    @property
    def weight_kg(self) -> Optional[float]:
        """Get the vehicle weight in kilograms.
        
        Returns:
            Weight in kg if specified in metadata
        """
        return self.metadata.get('weight_kg')
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate the vehicle data.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        if not self.make:
            errors.append("Make is required")
        
        if not self.model:
            errors.append("Model is required")
        
        if not self.year:
            errors.append("Year is required")
        elif self.year < self.MIN_YEAR or self.year > self.MAX_YEAR:
            errors.append(f"Year must be between {self.MIN_YEAR} and {self.MAX_YEAR}")
        
        if not self.color:
            errors.append("Color is required")
        
        if not self.license_plate:
            errors.append("License plate is required")
        elif len(self.license_plate) < 2 or len(self.license_plate) > 20:
            errors.append("License plate must be between 2 and 20 characters")
        
        if not self.vehicle_type:
            errors.append("Vehicle type is required")
        
        # Validate metadata if present
        if self.metadata:
            if 'height_meters' in self.metadata:
                height = self.metadata['height_meters']
                if not isinstance(height, (int, float)) or height <= 0:
                    errors.append("Height must be a positive number")
            
            if 'length_meters' in self.metadata:
                length = self.metadata['length_meters']
                if not isinstance(length, (int, float)) or length <= 0:
                    errors.append("Length must be a positive number")
            
            if 'width_meters' in self.metadata:
                width = self.metadata['width_meters']
                if not isinstance(width, (int, float)) or width <= 0:
                    errors.append("Width must be a positive number")
            
            if 'weight_kg' in self.metadata:
                weight = self.metadata['weight_kg']
                if not isinstance(weight, (int, float)) or weight <= 0:
                    errors.append("Weight must be a positive number")
        
        return len(errors) == 0, errors
    
    def update_last_used(self) -> None:
        """Update the last_used_at timestamp to now."""
        self.last_used_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_as_default(self) -> None:
        """Mark this vehicle as the default vehicle."""
        self.is_default = True
        self.updated_at = datetime.utcnow()
    
    def unmark_as_default(self) -> None:
        """Unmark this vehicle as the default vehicle."""
        self.is_default = False
        self.updated_at = datetime.utcnow()
    
    def soft_delete(self) -> None:
        """Soft delete the vehicle by marking as inactive."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore a soft-deleted vehicle."""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def to_dict(self, include_metadata: bool = True) -> Dict[str, Any]:
        """Convert vehicle to dictionary.
        
        Args:
            include_metadata: Whether to include metadata in the output
            
        Returns:
            Dictionary representation of the vehicle
        """
        result = {
            "vehicle_id": self.vehicle_id,
            "user_id": self.user_id,
            "make": self.make,
            "model": self.model,
            "year": self.year,
            "color": self.color,
            "license_plate": self.license_plate,
            "vehicle_type": self.vehicle_type.value if self.vehicle_type else None,
            "vehicle_type_display": self.vehicle_type.name if self.vehicle_type else None,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "age_years": self.age_years,
            "is_new": self.is_new,
            "requires_oversize_spot": self.requires_oversize_spot,
            "requires_ev_charging": self.requires_ev_charging,
            "height_clearance_required": self.height_clearance_required,
            "length_meters": self.length_meters,
            "width_meters": self.width_meters,
            "weight_kg": self.weight_kg,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "notes": self.notes,
        }
        
        if include_metadata:
            result["metadata"] = self.metadata
        
        return result
    
    def to_dict_minimal(self) -> Dict[str, Any]:
        """Convert vehicle to minimal dictionary (for list views).
        
        Returns:
            Minimal dictionary representation of the vehicle
        """
        return {
            "vehicle_id": self.vehicle_id,
            "display_name": self.display_name,
            "license_plate": self.license_plate,
            "vehicle_type": self.vehicle_type.value if self.vehicle_type else None,
            "is_default": self.is_default,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Vehicle':
        """Create vehicle from dictionary.
        
        Args:
            data: Dictionary containing vehicle data
            
        Returns:
            New Vehicle instance
        """
        # Handle vehicle_type enum
        vehicle_type = data.get('vehicle_type')
        if vehicle_type and isinstance(vehicle_type, str):
            try:
                vehicle_type = VehicleType(vehicle_type)
            except ValueError:
                # Try to match by name
                try:
                    vehicle_type = VehicleType[vehicle_type.upper()]
                except KeyError:
                    vehicle_type = VehicleType.SEDAN
        elif isinstance(vehicle_type, VehicleType):
            vehicle_type = vehicle_type
        else:
            vehicle_type = VehicleType.SEDAN
        
        # Parse datetime fields
        created_at = data.get('created_at')
        if created_at and isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = None
        
        updated_at = data.get('updated_at')
        if updated_at and isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except ValueError:
                updated_at = None
        
        last_used_at = data.get('last_used_at')
        if last_used_at and isinstance(last_used_at, str):
            try:
                last_used_at = datetime.fromisoformat(last_used_at.replace('Z', '+00:00'))
            except ValueError:
                last_used_at = None
        
        return cls(
            vehicle_id=data.get('vehicle_id'),
            user_id=data.get('user_id', 0),
            make=data.get('make', ''),
            model=data.get('model', ''),
            year=data.get('year', datetime.now().year),
            color=data.get('color', ''),
            license_plate=data.get('license_plate', ''),
            vehicle_type=vehicle_type,
            is_default=data.get('is_default', False),
            is_active=data.get('is_active', True),
            created_at=created_at,
            updated_at=updated_at,
            last_used_at=last_used_at,
            notes=data.get('notes'),
            metadata=data.get('metadata', {}),
        )
    
    @classmethod
    def get_vehicle_types(cls) -> List[Dict[str, str]]:
        """Get list of available vehicle types.
        
        Returns:
            List of dictionaries with value and display name
        """
        return [
            {"value": vt.value, "display": vt.name.replace('_', ' ').title()}
            for vt in VehicleType
        ]
    
    @classmethod
    def get_compatible_spot_types(cls, vehicle_type: VehicleType) -> List[str]:
        """Get compatible parking spot types for a vehicle type.
        
        Args:
            vehicle_type: Type of vehicle
            
        Returns:
            List of compatible parking spot types
        """
        compatibility_map = {
            VehicleType.SEDAN: ["standard", "vip", "ev_charging", "disabled"],
            VehicleType.SUV: ["standard", "vip", "ev_charging", "oversize", "disabled"],
            VehicleType.TRUCK: ["standard", "vip", "oversize"],
            VehicleType.VAN: ["standard", "vip", "oversize"],
            VehicleType.MOTORCYCLE: ["standard", "motorcycle", "vip"],
            VehicleType.RV: ["oversize"],
        }
        return compatibility_map.get(vehicle_type, ["standard"])
    
    def is_compatible_with_spot(self, spot_type: str) -> bool:
        """Check if this vehicle is compatible with a spot type.
        
        Args:
            spot_type: Type of parking spot
            
        Returns:
            True if compatible, False otherwise
        """
        compatible_types = self.get_compatible_spot_types(self.vehicle_type)
        return spot_type.lower() in compatible_types
    
    def get_estimated_space_required(self) -> float:
        """Get estimated parking space required in square meters.
        
        Returns:
            Estimated area in square meters
        """
        # Default space requirements by vehicle type (in sq meters)
        space_map = {
            VehicleType.MOTORCYCLE: 3.0,
            VehicleType.SEDAN: 10.0,
            VehicleType.SUV: 12.0,
            VehicleType.TRUCK: 18.0,
            VehicleType.VAN: 16.0,
            VehicleType.RV: 25.0,
        }
        return space_map.get(self.vehicle_type, 10.0)
    
    def get_weight_category(self) -> str:
        """Get weight category for the vehicle.
        
        Returns:
            Weight category: 'light', 'medium', 'heavy', or 'unknown'
        """
        if not self.weight_kg:
            # Estimate based on vehicle type
            weight_map = {
                VehicleType.MOTORCYCLE: 'light',
                VehicleType.SEDAN: 'medium',
                VehicleType.SUV: 'heavy',
                VehicleType.TRUCK: 'heavy',
                VehicleType.VAN: 'heavy',
                VehicleType.RV: 'heavy',
            }
            return weight_map.get(self.vehicle_type, 'medium')
        
        if self.weight_kg < 1500:
            return 'light'
        elif self.weight_kg < 2500:
            return 'medium'
        else:
            return 'heavy'
    
    def __eq__(self, other: object) -> bool:
        """Check equality with another vehicle."""
        if not isinstance(other, Vehicle):
            return False
        return (
            self.vehicle_id is not None and 
            other.vehicle_id is not None and 
            self.vehicle_id == other.vehicle_id
        )
    
    def __hash__(self) -> int:
        """Hash based on vehicle_id."""
        return hash(self.vehicle_id) if self.vehicle_id else id(self)