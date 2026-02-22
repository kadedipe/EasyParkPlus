# parking-management/data/migrations/repositories/parking_spot_repository.py
"""
Parking spot repository module for the parking management system.

This module provides repository classes for managing parking spots, sensors,
maintenance schedules, and spot-related operations with comprehensive
integration with the enum definitions.
"""

from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
import json
from geopy.distance import distance as geopy_distance
from sqlalchemy import (
    and_, or_, not_, desc, asc, func, select,
    update, delete, between, cast, Float, Integer,
    String, DateTime, Boolean, Numeric
)
from sqlalchemy.orm import Session, Query, joinedload, selectinload
from sqlalchemy.sql import expression

from .base_repository import (
    BaseRepository,
    AuditableRepository,
    CacheableRepository,
    SearchableRepository,
    FullFeatureRepository,
    EntityNotFoundException,
    DuplicateEntityException,
    ValidationException,
    RepositoryException,
    QueryBuilder
)
from ..models.enums import (
    # Parking enums
    SpotType,
    SpotStatus,
    ZoneType,
    ZoneStatus,
    AccessType,
    GateType,
    
    # Vehicle enums
    VehicleType,
    VehicleClass,
    
    # Sensor enums
    SensorType,
    SensorStatus,
    CommunicationProtocol,
    PowerSource,
    MeasurementUnit,
    DataQuality,
    CalibrationStatus,
    
    # Reservation enums
    ReservationStatus,
    
    # Audit enums
    AuditAction,
    AuditStatus,
    AuditSeverity,
    AuditCategory,
    AuditResourceType
)
from ..models.parking_models import (
    # Parking spot models
    ParkingSpot,
    SpotMaintenance,
    SpotSensor,
    SpotHistory,
    SpotOccupancy,
    SpotFeature,
    SpotRestriction,
    SpotRate,
    
    # Parking zone models
    ParkingZone,
    ZoneSchedule,
    ZoneRestriction,
    ZoneRate,
    ZoneCapacity,
    
    # Gate models
    Gate,
    GateAccessLog,
    GateController,
    GateSchedule,
    
    # Reservation models
    Reservation,
    
    # Vehicle models
    Vehicle
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class ParkingSpotNotFoundException(EntityNotFoundException):
    """Raised when a parking spot is not found."""
    def __init__(self, spot_id: Any):
        super().__init__("ParkingSpot", spot_id)


class SpotNotAvailableException(RepositoryException):
    """Raised when a parking spot is not available."""
    def __init__(self, spot_id: int, status: SpotStatus):
        self.spot_id = spot_id
        self.status = status
        super().__init__(
            f"Parking spot {spot_id} is not available (status: {status.value})"
        )


class SpotAlreadyOccupiedException(RepositoryException):
    """Raised when attempting to occupy an already occupied spot."""
    def __init__(self, spot_id: int, current_vehicle: Optional[str] = None):
        self.spot_id = spot_id
        self.current_vehicle = current_vehicle
        message = f"Parking spot {spot_id} is already occupied"
        if current_vehicle:
            message += f" by vehicle {current_vehicle}"
        super().__init__(message)


class InvalidVehicleTypeException(RepositoryException):
    """Raised when a vehicle type is not allowed in a spot."""
    def __init__(self, spot_id: int, vehicle_type: VehicleType, allowed_types: List[VehicleType]):
        self.spot_id = spot_id
        self.vehicle_type = vehicle_type
        self.allowed_types = allowed_types
        super().__init__(
            f"Vehicle type {vehicle_type.value} not allowed in spot {spot_id}. "
            f"Allowed types: {[t.value for t in allowed_types]}"
        )


class ZoneFullException(RepositoryException):
    """Raised when a parking zone is full."""
    def __init__(self, zone_id: int, zone_name: str, capacity: int, available: int):
        self.zone_id = zone_id
        self.zone_name = zone_name
        self.capacity = capacity
        self.available = available
        super().__init__(
            f"Zone {zone_name} is full. Capacity: {capacity}, Available: {available}"
        )


class MaintenanceInProgressException(RepositoryException):
    """Raised when a spot is under maintenance."""
    def __init__(self, spot_id: int, maintenance_end: Optional[datetime] = None):
        self.spot_id = spot_id
        self.maintenance_end = maintenance_end
        message = f"Parking spot {spot_id} is under maintenance"
        if maintenance_end:
            message += f" until {maintenance_end.isoformat()}"
        super().__init__(message)


class SensorCommunicationException(RepositoryException):
    """Raised when there's an error communicating with a sensor."""
    def __init__(self, sensor_id: int, message: str):
        self.sensor_id = sensor_id
        super().__init__(f"Sensor {sensor_id} communication error: {message}")


# ============================================================================
# Parking Spot Repository
# ============================================================================

class ParkingSpotRepository(FullFeatureRepository[ParkingSpot, int]):
    """
    Repository for ParkingSpot entity with comprehensive spot management features.
    
    This repository provides methods for parking spot CRUD operations,
    availability checking, occupancy management, and spot allocation.
    """
    
    def __init__(self, session: Session):
        super().__init__(session, ParkingSpot)
        self.searchable_fields = ['spot_number', 'location_description', 'notes']
    
    # ========================================================================
    # Custom Query Methods
    # ========================================================================
    
    def get_by_spot_number(self, zone_id: int, spot_number: str) -> Optional[ParkingSpot]:
        """
        Get parking spot by zone and spot number.
        
        Args:
            zone_id: Zone ID
            spot_number: Spot number within the zone
            
        Returns:
            Parking spot if found, None otherwise
        """
        return (
            self.session.query(ParkingSpot)
            .filter(
                ParkingSpot.zone_id == zone_id,
                ParkingSpot.spot_number == spot_number
            )
            .first()
        )
    
    def get_available_spots(
        self,
        zone_id: Optional[int] = None,
        spot_type: Optional[SpotType] = None,
        vehicle_type: Optional[VehicleType] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ParkingSpot]:
        """
        Get available parking spots based on criteria.
        
        Args:
            zone_id: Optional zone filter
            spot_type: Optional spot type filter
            vehicle_type: Optional vehicle type (for compatibility)
            from_time: Start time for availability
            to_time: End time for availability
            limit: Maximum number of spots to return
            
        Returns:
            List of available parking spots
        """
        query = self.session.query(ParkingSpot).filter(
            ParkingSpot.status.in_(SpotStatus.get_available_statuses())
        )
        
        if zone_id:
            query = query.filter(ParkingSpot.zone_id == zone_id)
        
        if spot_type:
            query = query.filter(ParkingSpot.spot_type == spot_type)
        
        # Filter by vehicle type compatibility
        if vehicle_type:
            # Get spots that allow this vehicle type
            query = query.filter(
                or_(
                    ParkingSpot.allowed_vehicle_types.is_(None),
                    ~ParkingSpot.has_restrictions  # No restrictions means all types allowed
                )
            )
        
        # Check for existing reservations in the time period
        if from_time and to_time:
            # Subquery to find spots with conflicting reservations
            conflicting_spots = (
                self.session.query(Reservation.spot_id)
                .filter(
                    Reservation.status.in_(ReservationStatus.get_active_statuses()),
                    Reservation.start_time < to_time,
                    Reservation.end_time > from_time
                )
                .subquery()
            )
            
            query = query.filter(~ParkingSpot.id.in_(conflicting_spots))
        
        return query.limit(limit).all()
    
    def get_spots_by_type(
        self,
        spot_type: SpotType,
        zone_id: Optional[int] = None,
        include_unavailable: bool = False
    ) -> List[ParkingSpot]:
        """
        Get parking spots by type.
        
        Args:
            spot_type: Spot type to filter by
            zone_id: Optional zone filter
            include_unavailable: Whether to include unavailable spots
            
        Returns:
            List of parking spots
        """
        query = self.session.query(ParkingSpot).filter(
            ParkingSpot.spot_type == spot_type
        )
        
        if zone_id:
            query = query.filter(ParkingSpot.zone_id == zone_id)
        
        if not include_unavailable:
            query = query.filter(
                ParkingSpot.status.in_(SpotStatus.get_available_statuses())
            )
        
        return query.all()
    
    def get_spots_by_zone(self, zone_id: int, include_unavailable: bool = False) -> List[ParkingSpot]:
        """
        Get all parking spots in a zone.
        
        Args:
            zone_id: Zone ID
            include_unavailable: Whether to include unavailable spots
            
        Returns:
            List of parking spots in the zone
        """
        query = self.session.query(ParkingSpot).filter(
            ParkingSpot.zone_id == zone_id
        )
        
        if not include_unavailable:
            query = query.filter(
                ParkingSpot.status.in_(SpotStatus.get_available_statuses())
            )
        
        return query.order_by(ParkingSpot.spot_number).all()
    
    def get_nearby_spots(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 500,
        spot_type: Optional[SpotType] = None,
        limit: int = 50
    ) -> List[Tuple[ParkingSpot, float]]:
        """
        Get parking spots near a geographic location.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius_meters: Search radius in meters
            spot_type: Optional spot type filter
            limit: Maximum number of spots to return
            
        Returns:
            List of (spot, distance_in_meters) tuples
        """
        # This is a simplified version - in production, use PostGIS or similar
        query = self.session.query(ParkingSpot).filter(
            ParkingSpot.latitude.isnot(None),
            ParkingSpot.longitude.isnot(None),
            ParkingSpot.status.in_(SpotStatus.get_available_statuses())
        )
        
        if spot_type:
            query = query.filter(ParkingSpot.spot_type == spot_type)
        
        spots = query.limit(limit * 2).all()  # Get more for filtering
        
        # Calculate distances and filter
        result = []
        for spot in spots:
            if spot.latitude and spot.longitude:
                dist = geopy_distance(
                    (latitude, longitude),
                    (spot.latitude, spot.longitude)
                ).meters
                
                if dist <= radius_meters:
                    result.append((spot, dist))
        
        # Sort by distance and limit
        result.sort(key=lambda x: x[1])
        return result[:limit]
    
    def get_handicapped_spots(self, zone_id: Optional[int] = None) -> List[ParkingSpot]:
        """Get handicapped parking spots."""
        return self.get_spots_by_type(SpotType.HANDICAPPED, zone_id)
    
    def get_electric_vehicle_spots(self, zone_id: Optional[int] = None) -> List[ParkingSpot]:
        """Get electric vehicle charging spots."""
        return self.get_spots_by_type(SpotType.ELECTRIC, zone_id)
    
    def get_vip_spots(self, zone_id: Optional[int] = None) -> List[ParkingSpot]:
        """Get VIP parking spots."""
        return self.get_spots_by_type(SpotType.VIP, zone_id)
    
    def get_available_count_by_type(
        self,
        zone_id: Optional[int] = None
    ) -> Dict[SpotType, int]:
        """
        Get count of available spots by type.
        
        Args:
            zone_id: Optional zone filter
            
        Returns:
            Dictionary mapping spot type to available count
        """
        query = self.session.query(
            ParkingSpot.spot_type,
            func.count(ParkingSpot.id)
        ).filter(
            ParkingSpot.status.in_(SpotStatus.get_available_statuses())
        )
        
        if zone_id:
            query = query.filter(ParkingSpot.zone_id == zone_id)
        
        results = query.group_by(ParkingSpot.spot_type).all()
        
        return {spot_type: count for spot_type, count in results}
    
    def get_occupancy_history(
        self,
        spot_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[SpotHistory]:
        """
        Get occupancy history for a spot.
        
        Args:
            spot_id: Spot ID
            from_date: Optional start date
            to_date: Optional end date
            limit: Maximum records to return
            
        Returns:
            List of spot history records
        """
        query = self.session.query(SpotHistory).filter(
            SpotHistory.spot_id == spot_id
        )
        
        if from_date:
            query = query.filter(SpotHistory.occupancy_start >= from_date)
        
        if to_date:
            query = query.filter(
                or_(
                    SpotHistory.occupancy_end <= to_date,
                    SpotHistory.occupancy_end.is_(None)
                )
            )
        
        return query.order_by(desc(SpotHistory.occupancy_start)).limit(limit).all()
    
    # ========================================================================
    # Spot Management Methods
    # ========================================================================
    
    def create_spot(
        self,
        zone_id: int,
        spot_number: str,
        spot_type: SpotType = SpotType.STANDARD,
        **kwargs
    ) -> ParkingSpot:
        """
        Create a new parking spot.
        
        Args:
            zone_id: Zone ID
            spot_number: Spot number within zone
            spot_type: Type of parking spot
            **kwargs: Additional spot attributes
            
        Returns:
            Created parking spot
            
        Raises:
            DuplicateEntityException: If spot number already exists in zone
            ValidationException: If validation fails
        """
        # Check for duplicate spot number in zone
        existing = self.get_by_spot_number(zone_id, spot_number)
        if existing:
            raise DuplicateEntityException(
                "ParkingSpot",
                f"zone_{zone_id}_spot_{spot_number}",
                spot_number
            )
        
        # Set audit context
        self.set_audit_context(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.PARKING_SPOT,
            severity=AuditSeverity.INFO
        )
        
        # Create spot
        spot = ParkingSpot(
            zone_id=zone_id,
            spot_number=spot_number,
            spot_type=spot_type,
            status=SpotStatus.AVAILABLE,
            **kwargs
        )
        
        spot = self.create(spot)
        
        logger.info(f"Created parking spot {spot.id} in zone {zone_id}: {spot_number}")
        return spot
    
    def update_spot_status(
        self,
        spot_id: int,
        status: SpotStatus,
        reason: Optional[str] = None
    ) -> ParkingSpot:
        """
        Update parking spot status.
        
        Args:
            spot_id: Spot ID
            status: New status
            reason: Optional reason for status change
            
        Returns:
            Updated parking spot
        """
        spot = self.get_or_fail(spot_id)
        
        old_status = spot.status
        spot.status = status
        
        # Record status change reason if provided
        if reason:
            if not spot.metadata:
                spot.metadata = {}
            spot.metadata['last_status_change_reason'] = reason
            spot.metadata['last_status_change_at'] = datetime.utcnow().isoformat()
        
        spot = self.update_entity(spot)
        
        logger.info(f"Updated spot {spot_id} status from {old_status} to {status}")
        return spot
    
    def mark_spot_maintenance(
        self,
        spot_id: int,
        maintenance_type: str,
        scheduled_end: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> Tuple[ParkingSpot, SpotMaintenance]:
        """
        Mark a spot for maintenance.
        
        Args:
            spot_id: Spot ID
            maintenance_type: Type of maintenance
            scheduled_end: Expected end time
            notes: Additional notes
            
        Returns:
            Tuple of (updated spot, maintenance record)
        """
        spot = self.get_or_fail(spot_id)
        
        # Update spot status
        spot.status = SpotStatus.MAINTENANCE
        
        # Create maintenance record
        maintenance = SpotMaintenance(
            spot_id=spot_id,
            maintenance_type=maintenance_type,
            started_at=datetime.utcnow(),
            scheduled_end=scheduled_end,
            notes=notes,
            status='in_progress'
        )
        
        self.session.add(maintenance)
        
        if not spot.metadata:
            spot.metadata = {}
        spot.metadata['current_maintenance_id'] = maintenance.id
        
        spot = self.update_entity(spot)
        
        logger.info(f"Marked spot {spot_id} for maintenance: {maintenance_type}")
        return spot, maintenance
    
    def complete_maintenance(
        self,
        spot_id: int,
        maintenance_id: int,
        resolution_notes: Optional[str] = None
    ) -> Tuple[ParkingSpot, SpotMaintenance]:
        """
        Complete maintenance for a spot.
        
        Args:
            spot_id: Spot ID
            maintenance_id: Maintenance record ID
            resolution_notes: Notes about resolution
            
        Returns:
            Tuple of (updated spot, completed maintenance record)
        """
        spot = self.get_or_fail(spot_id)
        
        maintenance = (
            self.session.query(SpotMaintenance)
            .filter(
                SpotMaintenance.id == maintenance_id,
                SpotMaintenance.spot_id == spot_id,
                SpotMaintenance.status == 'in_progress'
            )
            .first()
        )
        
        if not maintenance:
            raise EntityNotFoundException("SpotMaintenance", maintenance_id)
        
        # Complete maintenance
        maintenance.completed_at = datetime.utcnow()
        maintenance.resolution_notes = resolution_notes
        maintenance.status = 'completed'
        
        # Restore spot status
        if spot.status == SpotStatus.MAINTENANCE:
            spot.status = SpotStatus.AVAILABLE
        
        if spot.metadata and 'current_maintenance_id' in spot.metadata:
            del spot.metadata['current_maintenance_id']
        
        spot = self.update_entity(spot)
        
        logger.info(f"Completed maintenance {maintenance_id} for spot {spot_id}")
        return spot, maintenance
    
    def assign_vehicle_to_spot(
        self,
        spot_id: int,
        vehicle_id: int,
        reservation_id: Optional[int] = None
    ) -> ParkingSpot:
        """
        Assign a vehicle to a parking spot.
        
        Args:
            spot_id: Spot ID
            vehicle_id: Vehicle ID
            reservation_id: Optional reservation ID
            
        Returns:
            Updated parking spot
            
        Raises:
            SpotNotAvailableException: If spot is not available
            SpotAlreadyOccupiedException: If spot is already occupied
            InvalidVehicleTypeException: If vehicle type not allowed
        """
        spot = self.get_or_fail(spot_id)
        
        # Check spot availability
        if spot.status not in SpotStatus.get_available_statuses():
            raise SpotNotAvailableException(spot_id, spot.status)
        
        if spot.current_vehicle_id:
            raise SpotAlreadyOccupiedException(spot_id)
        
        # Get vehicle
        vehicle = (
            self.session.query(Vehicle)
            .filter(Vehicle.id == vehicle_id)
            .first()
        )
        
        if not vehicle:
            raise EntityNotFoundException("Vehicle", vehicle_id)
        
        # Check vehicle type compatibility
        if not self._is_vehicle_compatible(spot, vehicle):
            raise InvalidVehicleTypeException(
                spot_id,
                vehicle.vehicle_type,
                self._get_allowed_vehicle_types(spot)
            )
        
        # Assign vehicle
        spot.current_vehicle_id = vehicle_id
        spot.current_reservation_id = reservation_id
        spot.occupied_since = datetime.utcnow()
        spot.status = SpotStatus.OCCUPIED
        
        # Create occupancy record
        occupancy = SpotOccupancy(
            spot_id=spot_id,
            vehicle_id=vehicle_id,
            reservation_id=reservation_id,
            start_time=datetime.utcnow()
        )
        self.session.add(occupancy)
        
        spot = self.update_entity(spot)
        
        logger.info(f"Assigned vehicle {vehicle_id} to spot {spot_id}")
        return spot
    
    def release_spot(
        self,
        spot_id: int,
        vehicle_id: Optional[int] = None
    ) -> ParkingSpot:
        """
        Release a vehicle from a parking spot.
        
        Args:
            spot_id: Spot ID
            vehicle_id: Optional vehicle ID for verification
            
        Returns:
            Updated parking spot
        """
        spot = self.get_or_fail(spot_id)
        
        # Verify vehicle if provided
        if vehicle_id and spot.current_vehicle_id != vehicle_id:
            raise ValidationException(
                "ParkingSpot",
                {"vehicle_id": [f"Spot is occupied by different vehicle"]}
            )
        
        if spot.current_vehicle_id:
            # Update current occupancy
            current_occupancy = (
                self.session.query(SpotOccupancy)
                .filter(
                    SpotOccupancy.spot_id == spot_id,
                    SpotOccupancy.end_time.is_(None)
                )
                .first()
            )
            
            if current_occupancy:
                current_occupancy.end_time = datetime.utcnow()
        
        # Clear spot
        old_vehicle_id = spot.current_vehicle_id
        spot.current_vehicle_id = None
        spot.current_reservation_id = None
        spot.occupied_since = None
        spot.status = SpotStatus.AVAILABLE
        
        spot = self.update_entity(spot)
        
        # Create history record
        if old_vehicle_id:
            history = SpotHistory(
                spot_id=spot_id,
                vehicle_id=old_vehicle_id,
                occupancy_start=spot.occupied_since or datetime.utcnow(),
                occupancy_end=datetime.utcnow()
            )
            self.session.add(history)
        
        logger.info(f"Released spot {spot_id}")
        return spot
    
    def reserve_spot(
        self,
        spot_id: int,
        reservation_id: int,
        from_time: datetime,
        to_time: datetime
    ) -> ParkingSpot:
        """
        Reserve a parking spot.
        
        Args:
            spot_id: Spot ID
            reservation_id: Reservation ID
            from_time: Reservation start time
            to_time: Reservation end time
            
        Returns:
            Updated parking spot
        """
        spot = self.get_or_fail(spot_id)
        
        # Check if spot can be reserved
        if spot.status not in [SpotStatus.AVAILABLE, SpotStatus.RESERVED]:
            raise SpotNotAvailableException(spot_id, spot.status)
        
        # Update spot status if not already reserved
        if spot.status == SpotStatus.AVAILABLE:
            spot.status = SpotStatus.RESERVED
        
        # Add to reservations list
        if not spot.upcoming_reservations:
            spot.upcoming_reservations = []
        
        spot.upcoming_reservations.append({
            'reservation_id': reservation_id,
            'from': from_time.isoformat(),
            'to': to_time.isoformat()
        })
        
        spot = self.update_entity(spot)
        
        logger.info(f"Reserved spot {spot_id} for reservation {reservation_id}")
        return spot
    
    def cancel_reservation(self, spot_id: int, reservation_id: int) -> ParkingSpot:
        """
        Cancel a reservation for a spot.
        
        Args:
            spot_id: Spot ID
            reservation_id: Reservation ID
            
        Returns:
            Updated parking spot
        """
        spot = self.get_or_fail(spot_id)
        
        if spot.upcoming_reservations:
            # Remove the reservation
            spot.upcoming_reservations = [
                r for r in spot.upcoming_reservations
                if r.get('reservation_id') != reservation_id
            ]
        
        # Update status if no other reservations
        if not spot.upcoming_reservations and spot.status == SpotStatus.RESERVED:
            spot.status = SpotStatus.AVAILABLE
        
        spot = self.update_entity(spot)
        
        logger.info(f"Cancelled reservation {reservation_id} for spot {spot_id}")
        return spot
    
    # ========================================================================
    # Spot Features and Restrictions
    # ========================================================================
    
    def add_spot_feature(
        self,
        spot_id: int,
        feature_name: str,
        feature_value: Any
    ) -> SpotFeature:
        """
        Add a feature to a parking spot.
        
        Args:
            spot_id: Spot ID
            feature_name: Feature name
            feature_value: Feature value
            
        Returns:
            Created spot feature
        """
        spot = self.get_or_fail(spot_id)
        
        feature = SpotFeature(
            spot_id=spot_id,
            feature_name=feature_name,
            feature_value=feature_value,
            created_at=datetime.utcnow()
        )
        
        self.session.add(feature)
        self.session.flush()
        
        logger.info(f"Added feature {feature_name} to spot {spot_id}")
        return feature
    
    def add_spot_restriction(
        self,
        spot_id: int,
        restriction_type: str,
        restriction_value: Any,
        applies_from: Optional[datetime] = None,
        applies_until: Optional[datetime] = None
    ) -> SpotRestriction:
        """
        Add a restriction to a parking spot.
        
        Args:
            spot_id: Spot ID
            restriction_type: Type of restriction
            restriction_value: Restriction value
            applies_from: When restriction starts
            applies_until: When restriction ends
            
        Returns:
            Created spot restriction
        """
        spot = self.get_or_fail(spot_id)
        
        restriction = SpotRestriction(
            spot_id=spot_id,
            restriction_type=restriction_type,
            restriction_value=restriction_value,
            applies_from=applies_from,
            applies_until=applies_until,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.session.add(restriction)
        self.session.flush()
        
        logger.info(f"Added restriction {restriction_type} to spot {spot_id}")
        return restriction
    
    def get_active_restrictions(self, spot_id: int, at_time: Optional[datetime] = None) -> List[SpotRestriction]:
        """
        Get active restrictions for a spot.
        
        Args:
            spot_id: Spot ID
            at_time: Time to check (defaults to now)
            
        Returns:
            List of active restrictions
        """
        check_time = at_time or datetime.utcnow()
        
        return (
            self.session.query(SpotRestriction)
            .filter(
                SpotRestriction.spot_id == spot_id,
                SpotRestriction.is_active == True,
                or_(
                    SpotRestriction.applies_from.is_(None),
                    SpotRestriction.applies_from <= check_time
                ),
                or_(
                    SpotRestriction.applies_until.is_(None),
                    SpotRestriction.applies_until >= check_time
                )
            )
            .all()
        )
    
    def set_spot_rate(
        self,
        spot_id: int,
        rate_id: int,
        applies_from: datetime,
        applies_until: Optional[datetime] = None
    ) -> SpotRate:
        """
        Set a rate for a specific spot.
        
        Args:
            spot_id: Spot ID
            rate_id: Rate ID
            applies_from: When rate applies from
            applies_until: When rate applies until (optional)
            
        Returns:
            Created spot rate
        """
        spot = self.get_or_fail(spot_id)
        
        # Deactivate current rates
        self.session.query(SpotRate).filter(
            SpotRate.spot_id == spot_id,
            SpotRate.is_active == True
        ).update({"is_active": False, "deactivated_at": datetime.utcnow()})
        
        # Create new rate
        spot_rate = SpotRate(
            spot_id=spot_id,
            rate_id=rate_id,
            applies_from=applies_from,
            applies_until=applies_until,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        self.session.add(spot_rate)
        self.session.flush()
        
        logger.info(f"Set rate {rate_id} for spot {spot_id}")
        return spot_rate
    
    # ========================================================================
    # Zone Management Integration
    # ========================================================================
    
    def get_zone_statistics(self, zone_id: int) -> Dict[str, Any]:
        """
        Get statistics for a parking zone.
        
        Args:
            zone_id: Zone ID
            
        Returns:
            Dictionary with zone statistics
        """
        total_spots = self.session.query(func.count(ParkingSpot.id)).filter(
            ParkingSpot.zone_id == zone_id
        ).scalar() or 0
        
        available_spots = self.session.query(func.count(ParkingSpot.id)).filter(
            ParkingSpot.zone_id == zone_id,
            ParkingSpot.status.in_(SpotStatus.get_available_statuses())
        ).scalar() or 0
        
        occupied_spots = self.session.query(func.count(ParkingSpot.id)).filter(
            ParkingSpot.zone_id == zone_id,
            ParkingSpot.status == SpotStatus.OCCUPIED
        ).scalar() or 0
        
        reserved_spots = self.session.query(func.count(ParkingSpot.id)).filter(
            ParkingSpot.zone_id == zone_id,
            ParkingSpot.status == SpotStatus.RESERVED
        ).scalar() or 0
        
        maintenance_spots = self.session.query(func.count(ParkingSpot.id)).filter(
            ParkingSpot.zone_id == zone_id,
            ParkingSpot.status == SpotStatus.MAINTENANCE
        ).scalar() or 0
        
        # Statistics by spot type
        by_type = {}
        for spot_type in SpotType:
            count = self.session.query(func.count(ParkingSpot.id)).filter(
                ParkingSpot.zone_id == zone_id,
                ParkingSpot.spot_type == spot_type
            ).scalar() or 0
            
            available = self.session.query(func.count(ParkingSpot.id)).filter(
                ParkingSpot.zone_id == zone_id,
                ParkingSpot.spot_type == spot_type,
                ParkingSpot.status.in_(SpotStatus.get_available_statuses())
            ).scalar() or 0
            
            by_type[spot_type.value] = {
                'total': count,
                'available': available,
                'occupied': count - available
            }
        
        # Current occupancy rate
        occupancy_rate = round(
            (occupied_spots / total_spots * 100) if total_spots > 0 else 0,
            2
        )
        
        return {
            'zone_id': zone_id,
            'total_spots': total_spots,
            'available_spots': available_spots,
            'occupied_spots': occupied_spots,
            'reserved_spots': reserved_spots,
            'maintenance_spots': maintenance_spots,
            'occupancy_rate': occupancy_rate,
            'by_spot_type': by_type
        }
    
    def get_zone_occupancy_trend(
        self,
        zone_id: int,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get occupancy trend for a zone.
        
        Args:
            zone_id: Zone ID
            days: Number of days to look back
            
        Returns:
            List of daily occupancy statistics
        """
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            
            # Get occupancy for this day
            occupancy_count = (
                self.session.query(func.count(SpotHistory.id))
                .join(ParkingSpot)
                .filter(
                    ParkingSpot.zone_id == zone_id,
                    SpotHistory.occupancy_start < next_date,
                    or_(
                        SpotHistory.occupancy_end.is_(None),
                        SpotHistory.occupancy_end > current_date
                    )
                )
                .scalar() or 0
            )
            
            total_spots = self.session.query(func.count(ParkingSpot.id)).filter(
                ParkingSpot.zone_id == zone_id
            ).scalar() or 1
            
            results.append({
                'date': current_date.isoformat(),
                'occupancy_count': occupancy_count,
                'occupancy_rate': round(occupancy_count / total_spots * 100, 2),
                'total_spots': total_spots
            })
            
            current_date = next_date
        
        return results
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def find_optimal_spot(
        self,
        vehicle_type: VehicleType,
        preferred_zone: Optional[int] = None,
        preferred_type: Optional[SpotType] = None,
        requires_ev_charging: bool = False,
        requires_handicap: bool = False,
        max_distance_to_elevator: Optional[float] = None
    ) -> Optional[ParkingSpot]:
        """
        Find the optimal parking spot based on preferences.
        
        Args:
            vehicle_type: Vehicle type
            preferred_zone: Preferred zone ID
            preferred_type: Preferred spot type
            requires_ev_charging: Whether EV charging is needed
            requires_handicap: Whether handicap access is needed
            max_distance_to_elevator: Maximum distance to elevator in meters
            
        Returns:
            Optimal parking spot if found, None otherwise
        """
        # Build base query
        query = self.session.query(ParkingSpot).filter(
            ParkingSpot.status.in_(SpotStatus.get_available_statuses())
        )
        
        # Apply required filters
        if requires_ev_charging:
            query = query.filter(ParkingSpot.spot_type == SpotType.ELECTRIC)
        
        if requires_handicap:
            query = query.filter(ParkingSpot.spot_type == SpotType.HANDICAPPED)
        
        # Apply preferences
        if preferred_zone:
            query = query.filter(ParkingSpot.zone_id == preferred_zone)
        
        if preferred_type and not (requires_ev_charging or requires_handicap):
            query = query.filter(ParkingSpot.spot_type == preferred_type)
        
        # Filter by vehicle compatibility
        spots = query.all()
        compatible_spots = [
            spot for spot in spots
            if self._is_vehicle_compatible(spot, vehicle_type)
        ]
        
        if not compatible_spots:
            return None
        
        # Score and sort spots
        scored_spots = []
        for spot in compatible_spots:
            score = self._calculate_spot_score(spot, {
                'preferred_zone': preferred_zone,
                'preferred_type': preferred_type,
                'max_distance_to_elevator': max_distance_to_elevator
            })
            scored_spots.append((spot, score))
        
        # Return highest scored spot
        scored_spots.sort(key=lambda x: x[1], reverse=True)
        return scored_spots[0][0] if scored_spots else None
    
    def check_spot_availability(
        self,
        spot_id: int,
        from_time: datetime,
        to_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a spot is available for a time period.
        
        Args:
            spot_id: Spot ID
            from_time: Start time
            to_time: End time
            
        Returns:
            Tuple of (is_available, reason_if_not)
        """
        spot = self.get_or_fail(spot_id)
        
        # Check spot status
        if spot.status not in SpotStatus.get_available_statuses():
            return False, f"Spot status is {spot.status.value}"
        
        # Check for conflicting reservations
        conflict = (
            self.session.query(Reservation)
            .filter(
                Reservation.spot_id == spot_id,
                Reservation.status.in_(ReservationStatus.get_active_statuses()),
                Reservation.start_time < to_time,
                Reservation.end_time > from_time
            )
            .first()
        )
        
        if conflict:
            return False, f"Conflicting reservation from {conflict.start_time} to {conflict.end_time}"
        
        # Check maintenance schedule
        maintenance = (
            self.session.query(SpotMaintenance)
            .filter(
                SpotMaintenance.spot_id == spot_id,
                SpotMaintenance.status == 'scheduled',
                SpotMaintenance.scheduled_start < to_time,
                or_(
                    SpotMaintenance.scheduled_end.is_(None),
                    SpotMaintenance.scheduled_end > from_time
                )
            )
            .first()
        )
        
        if maintenance:
            return False, f"Scheduled maintenance from {maintenance.scheduled_start} to {maintenance.scheduled_end}"
        
        return True, None
    
    def get_spot_utilization_rate(
        self,
        spot_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> float:
        """
        Calculate utilization rate for a spot.
        
        Args:
            spot_id: Spot ID
            from_date: Start date for calculation
            to_date: End date for calculation
            
        Returns:
            Utilization rate as percentage (0-100)
        """
        end = to_date or datetime.utcnow()
        start = from_date or (end - timedelta(days=30))
        
        total_seconds = (end - start).total_seconds()
        
        # Get occupancy periods within the range
        occupancies = (
            self.session.query(SpotHistory)
            .filter(
                SpotHistory.spot_id == spot_id,
                SpotHistory.occupancy_start < end,
                or_(
                    SpotHistory.occupancy_end.is_(None),
                    SpotHistory.occupancy_end > start
                )
            )
            .all()
        )
        
        occupied_seconds = 0
        for occ in occupancies:
            occ_start = max(occ.occupancy_start, start)
            occ_end = min(occ.occupancy_end or end, end)
            occupied_seconds += (occ_end - occ_start).total_seconds()
        
        return round((occupied_seconds / total_seconds) * 100, 2) if total_seconds > 0 else 0
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _is_vehicle_compatible(self, spot: ParkingSpot, vehicle: Vehicle) -> bool:
        """Check if a vehicle is compatible with a spot."""
        return self._is_vehicle_compatible_by_type(spot, vehicle.vehicle_type)
    
    def _is_vehicle_compatible_by_type(self, spot: ParkingSpot, vehicle_type: VehicleType) -> bool:
        """Check if a vehicle type is compatible with a spot."""
        # Check spot type compatibility
        if spot.spot_type == SpotType.MOTORCYCLE:
            return vehicle_type in [VehicleType.MOTORCYCLE, VehicleType.SCOOTER]
        
        if spot.spot_type == SpotType.COMPACT:
            return vehicle_type in [VehicleType.CAR, VehicleType.HYBRID, VehicleType.SCOOTER]
        
        if spot.spot_type == SpotType.ELECTRIC:
            return vehicle_type in [VehicleType.EV, VehicleType.HYBRID]
        
        if spot.spot_type == SpotType.HANDICAPPED:
            # Any vehicle type can use handicapped spots if properly marked
            return True
        
        if spot.spot_type == SpotType.TRUCK:
            return vehicle_type in [VehicleType.TRUCK, VehicleType.VAN, VehicleType.COMMERCIAL]
        
        # Standard spots - most vehicles allowed
        return True
    
    def _get_allowed_vehicle_types(self, spot: ParkingSpot) -> List[VehicleType]:
        """Get allowed vehicle types for a spot."""
        if spot.spot_type == SpotType.MOTORCYCLE:
            return [VehicleType.MOTORCYCLE, VehicleType.SCOOTER]
        
        if spot.spot_type == SpotType.COMPACT:
            return [VehicleType.CAR, VehicleType.HYBRID, VehicleType.SCOOTER]
        
        if spot.spot_type == SpotType.ELECTRIC:
            return [VehicleType.EV, VehicleType.HYBRID]
        
        if spot.spot_type == SpotType.TRUCK:
            return [VehicleType.TRUCK, VehicleType.VAN, VehicleType.COMMERCIAL]
        
        # Default - all types
        return list(VehicleType)
    
    def _calculate_spot_score(
        self,
        spot: ParkingSpot,
        preferences: Dict[str, Any]
    ) -> float:
        """Calculate a score for spot ranking."""
        score = 100.0  # Base score
        
        # Bonus for preferred zone
        if preferences.get('preferred_zone') and spot.zone_id == preferences['preferred_zone']:
            score += 20
        
        # Bonus for preferred type
        if preferences.get('preferred_type') and spot.spot_type == preferences['preferred_type']:
            score += 15
        
        # Bonus for proximity to elevator
        if preferences.get('max_distance_to_elevator') and spot.distance_to_elevator:
            if spot.distance_to_elevator <= preferences['max_distance_to_elevator']:
                score += 10
            else:
                score -= (spot.distance_to_elevator - preferences['max_distance_to_elevator']) / 10
        
        # Bonus for covered spots
        if spot.is_covered:
            score += 5
        
        # Bonus for wider spots
        if spot.width and spot.width > 2.5:  # Wider than standard
            score += 5
        
        return score


# ============================================================================
# Spot Maintenance Repository
# ============================================================================

class SpotMaintenanceRepository(BaseRepository[SpotMaintenance, int]):
    """Repository for SpotMaintenance entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, SpotMaintenance)
    
    def get_active_maintenance(self, spot_id: Optional[int] = None) -> List[SpotMaintenance]:
        """Get active maintenance records."""
        query = self.session.query(SpotMaintenance).filter(
            SpotMaintenance.status == 'in_progress'
        )
        
        if spot_id:
            query = query.filter(SpotMaintenance.spot_id == spot_id)
        
        return query.all()
    
    def get_scheduled_maintenance(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[SpotMaintenance]:
        """Get scheduled maintenance."""
        query = self.session.query(SpotMaintenance).filter(
            SpotMaintenance.status == 'scheduled'
        )
        
        if from_date:
            query = query.filter(SpotMaintenance.scheduled_start >= from_date)
        
        if to_date:
            query = query.filter(
                or_(
                    SpotMaintenance.scheduled_start <= to_date,
                    SpotMaintenance.scheduled_end <= to_date
                )
            )
        
        return query.order_by(SpotMaintenance.scheduled_start).all()
    
    def get_maintenance_history(
        self,
        spot_id: int,
        limit: int = 50
    ) -> List[SpotMaintenance]:
        """Get maintenance history for a spot."""
        return (
            self.session.query(SpotMaintenance)
            .filter(SpotMaintenance.spot_id == spot_id)
            .order_by(desc(SpotMaintenance.started_at))
            .limit(limit)
            .all()
        )
    
    def get_upcoming_maintenance(self, days: int = 7) -> List[SpotMaintenance]:
        """Get maintenance scheduled in the next N days."""
        now = datetime.utcnow()
        end = now + timedelta(days=days)
        
        return (
            self.session.query(SpotMaintenance)
            .filter(
                SpotMaintenance.status.in_(['scheduled', 'in_progress']),
                SpotMaintenance.scheduled_start <= end
            )
            .order_by(SpotMaintenance.scheduled_start)
            .all()
        )


# ============================================================================
# Spot Sensor Repository
# ============================================================================

class SpotSensorRepository(BaseRepository[SpotSensor, int]):
    """Repository for SpotSensor entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, SpotSensor)
    
    def get_by_spot(self, spot_id: int, active_only: bool = True) -> List[SpotSensor]:
        """Get sensors for a spot."""
        query = self.session.query(SpotSensor).filter(
            SpotSensor.spot_id == spot_id
        )
        
        if active_only:
            query = query.filter(SpotSensor.is_active == True)
        
        return query.all()
    
    def get_by_sensor_type(
        self,
        sensor_type: SensorType,
        zone_id: Optional[int] = None
    ) -> List[SpotSensor]:
        """Get sensors by type."""
        query = (
            self.session.query(SpotSensor)
            .join(ParkingSpot)
            .filter(SpotSensor.sensor_type == sensor_type)
        )
        
        if zone_id:
            query = query.filter(ParkingSpot.zone_id == zone_id)
        
        return query.all()
    
    def get_faulty_sensors(self) -> List[SpotSensor]:
        """Get sensors with faults."""
        return (
            self.session.query(SpotSensor)
            .filter(SpotSensor.status.in_([
                SensorStatus.FAULTY,
                SensorStatus.COMMUNICATION_ERROR,
                SensorStatus.BATTERY_LOW
            ]))
            .all()
        )
    
    def update_sensor_reading(
        self,
        sensor_id: int,
        reading_value: Any,
        reading_unit: MeasurementUnit,
        quality: DataQuality = DataQuality.GOOD
    ) -> SpotSensor:
        """Update sensor with latest reading."""
        sensor = self.get_or_fail(sensor_id)
        
        sensor.last_reading_value = reading_value
        sensor.last_reading_unit = reading_unit
        sensor.last_reading_time = datetime.utcnow()
        sensor.last_reading_quality = quality
        sensor.reading_count = (sensor.reading_count or 0) + 1
        
        # Update battery level if provided
        if hasattr(reading_value, 'battery_level'):
            sensor.battery_level = reading_value.battery_level
        
        sensor = self.update_entity(sensor)
        
        # Check if occupancy status changed
        if sensor.sensor_type == SensorType.ULTRASONIC:
            self._update_spot_occupancy_from_sensor(sensor)
        
        return sensor
    
    def calibrate_sensor(
        self,
        sensor_id: int,
        calibration_data: Dict[str, Any]
    ) -> SpotSensor:
        """Calibrate a sensor."""
        sensor = self.get_or_fail(sensor_id)
        
        sensor.calibration_status = CalibrationStatus.CALIBRATING
        
        # Store calibration data
        if not sensor.calibration_history:
            sensor.calibration_history = []
        
        sensor.calibration_history.append({
            'timestamp': datetime.utcnow().isoformat(),
            'data': calibration_data,
            'previous_status': sensor.calibration_status.value
        })
        
        sensor.last_calibration = datetime.utcnow()
        sensor.calibration_status = CalibrationStatus.CALIBRATED
        
        sensor = self.update_entity(sensor)
        
        logger.info(f"Calibrated sensor {sensor_id}")
        return sensor
    
    def _update_spot_occupancy_from_sensor(self, sensor: SpotSensor) -> None:
        """Update spot occupancy based on sensor reading."""
        if not sensor.last_reading_value:
            return
        
        # Determine if spot is occupied based on sensor type
        is_occupied = False
        
        if sensor.sensor_type == SensorType.ULTRASONIC:
            # Ultrasonic sensors return distance - shorter distance means occupied
            try:
                distance = float(sensor.last_reading_value)
                is_occupied = distance < 50  # Less than 50cm means occupied
            except (ValueError, TypeError):
                return
        
        elif sensor.sensor_type == SensorType.MAGNETIC:
            # Magnetic sensors detect vehicle presence
            try:
                presence = bool(sensor.last_reading_value)
                is_occupied = presence
            except (ValueError, TypeError):
                return
        
        # Update spot status if needed
        spot = sensor.spot
        current_occupied = spot.status == SpotStatus.OCCUPIED
        
        if is_occupied != current_occupied:
            if is_occupied:
                # Spot became occupied - mark as occupied if available
                if spot.status in SpotStatus.get_available_statuses():
                    spot.status = SpotStatus.OCCUPIED
                    spot.occupied_since = datetime.utcnow()
                    
                    # Create occupancy record
                    occupancy = SpotOccupancy(
                        spot_id=spot.id,
                        start_time=datetime.utcnow(),
                        detected_by_sensor_id=sensor.id
                    )
                    self.session.add(occupancy)
            else:
                # Spot became empty - mark as available if occupied
                if spot.status == SpotStatus.OCCUPIED:
                    # End current occupancy
                    current_occupancy = (
                        self.session.query(SpotOccupancy)
                        .filter(
                            SpotOccupancy.spot_id == spot.id,
                            SpotOccupancy.end_time.is_(None)
                        )
                        .first()
                    )
                    
                    if current_occupancy:
                        current_occupancy.end_time = datetime.utcnow()
                    
                    spot.status = SpotStatus.AVAILABLE
                    spot.current_vehicle_id = None
                    spot.current_reservation_id = None
                    spot.occupied_since = None
            
            self.session.flush()


# ============================================================================
# Spot Occupancy Repository
# ============================================================================

class SpotOccupancyRepository(BaseRepository[SpotOccupancy, int]):
    """Repository for SpotOccupancy entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, SpotOccupancy)
    
    def get_current_occupancy(self, spot_id: Optional[int] = None) -> List[SpotOccupancy]:
        """Get current occupancy records."""
        query = self.session.query(SpotOccupancy).filter(
            SpotOccupancy.end_time.is_(None)
        )
        
        if spot_id:
            query = query.filter(SpotOccupancy.spot_id == spot_id)
        
        return query.all()
    
    def get_occupancy_for_period(
        self,
        spot_id: Optional[int] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None
    ) -> List[SpotOccupancy]:
        """Get occupancy for a time period."""
        query = self.session.query(SpotOccupancy)
        
        if spot_id:
            query = query.filter(SpotOccupancy.spot_id == spot_id)
        
        if from_time:
            query = query.filter(
                or_(
                    SpotOccupancy.start_time >= from_time,
                    and_(
                        SpotOccupancy.start_time < from_time,
                        or_(
                            SpotOccupancy.end_time.is_(None),
                            SpotOccupancy.end_time > from_time
                        )
                    )
                )
            )
        
        if to_time:
            query = query.filter(SpotOccupancy.start_time < to_time)
        
        return query.order_by(SpotOccupancy.start_time).all()
    
    def get_occupancy_statistics(
        self,
        zone_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get occupancy statistics."""
        query = self.session.query(SpotOccupancy).join(ParkingSpot)
        
        if zone_id:
            query = query.filter(ParkingSpot.zone_id == zone_id)
        
        if from_date:
            query = query.filter(SpotOccupancy.start_time >= from_date)
        
        if to_date:
            query = query.filter(SpotOccupancy.start_time <= to_date)
        
        occupancies = query.all()
        
        if not occupancies:
            return {
                'total_occupancies': 0,
                'average_duration_minutes': 0,
                'peak_hour': None,
                'occupancy_by_hour': {}
            }
        
        # Calculate statistics
        total_duration = 0
        completed = 0
        hourly_counts = {i: 0 for i in range(24)}
        
        for occ in occupancies:
            if occ.end_time:
                duration = (occ.end_time - occ.start_time).total_seconds() / 60
                total_duration += duration
                completed += 1
            
            hour = occ.start_time.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        avg_duration = total_duration / completed if completed > 0 else 0
        peak_hour = max(hourly_counts.items(), key=lambda x: x[1])[0] if hourly_counts else None
        
        return {
            'total_occupancies': len(occupancies),
            'average_duration_minutes': round(avg_duration, 2),
            'peak_hour': peak_hour,
            'occupancy_by_hour': hourly_counts
        }


# ============================================================================
# Spot History Repository
# ============================================================================

class SpotHistoryRepository(BaseRepository[SpotHistory, int]):
    """Repository for SpotHistory entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, SpotHistory)
    
    def get_spot_history(
        self,
        spot_id: int,
        days: int = 30
    ) -> List[SpotHistory]:
        """Get history for a spot."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        return (
            self.session.query(SpotHistory)
            .filter(
                SpotHistory.spot_id == spot_id,
                SpotHistory.occupancy_start >= cutoff
            )
            .order_by(desc(SpotHistory.occupancy_start))
            .all()
        )
    
    def get_vehicle_history(
        self,
        vehicle_id: int,
        limit: int = 50
    ) -> List[SpotHistory]:
        """Get parking history for a vehicle."""
        return (
            self.session.query(SpotHistory)
            .filter(SpotHistory.vehicle_id == vehicle_id)
            .order_by(desc(SpotHistory.occupancy_start))
            .limit(limit)
            .all()
        )
    
    def cleanup_old_history(self, days: int = 365) -> int:
        """Delete history older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = (
            self.session.query(SpotHistory)
            .filter(SpotHistory.occupancy_end <= cutoff)
            .delete()
        )
        
        self.session.flush()
        return result


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main Repository
    'ParkingSpotRepository',
    'SpotMaintenanceRepository',
    'SpotSensorRepository',
    'SpotOccupancyRepository',
    'SpotHistoryRepository',
    
    # Exceptions
    'ParkingSpotNotFoundException',
    'SpotNotAvailableException',
    'SpotAlreadyOccupiedException',
    'InvalidVehicleTypeException',
    'ZoneFullException',
    'MaintenanceInProgressException',
    'SensorCommunicationException',
]