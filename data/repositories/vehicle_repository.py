# parking-management/data/migrations/repositories/vehicle_repository.py
"""
Vehicle repository module for the parking management system.

This module provides repository classes for managing vehicles, registrations,
insurance, inspections, and vehicle-related data with comprehensive integration
with the enum definitions.
"""

from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
import json
import re
from uuid import uuid4

from sqlalchemy import (
    and_, or_, not_, desc, asc, func, select,
    update, delete, between, cast, Float, Integer,
    String, DateTime, Boolean, Numeric, Date,
    ForeignKey
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
    # Vehicle enums
    VehicleStatus,
    VehicleType,
    VehicleClass,
    FuelType,
    TransmissionType,
    DriveType,
    RegistrationStatus,
    InsuranceStatus,
    InspectionStatus,
    OwnershipType,
    
    # Audit enums
    AuditAction,
    AuditStatus,
    AuditSeverity,
    AuditCategory,
    AuditResourceType,
    
    # Reservation enums
    ReservationStatus,
    
    # General enums
    CountryCode
)
from ..models.vehicle_models import (
    # Vehicle models
    Vehicle,
    VehicleRegistration,
    VehicleInsurance,
    VehicleInspection,
    VehicleOwnership,
    VehicleDocument,
    VehicleImage,
    VehicleHistory,
    
    # Blacklist models
    VehicleBlacklist,
    VehicleAlert,
    StolenVehicle,
    
    # Manufacturer models
    VehicleMake,
    VehicleModel,
    VehicleTrim,
    
    # Feature models
    VehicleFeature,
    VehicleSpecification
)
from ..models.user_models import (
    User
)
from ..models.reservation_models import (
    Reservation
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class VehicleNotFoundException(EntityNotFoundException):
    """Raised when a vehicle is not found."""
    def __init__(self, vehicle_id: Any):
        super().__init__("Vehicle", vehicle_id)


class DuplicateLicensePlateException(DuplicateEntityException):
    """Raised when a license plate already exists."""
    def __init__(self, license_plate: str):
        super().__init__("Vehicle", "license_plate", license_plate)


class DuplicateVINException(DuplicateEntityException):
    """Raised when a VIN already exists."""
    def __init__(self, vin: str):
        super().__init__("Vehicle", "vin", vin)


class VehicleBlacklistedException(RepositoryException):
    """Raised when a vehicle is blacklisted."""
    def __init__(self, license_plate: str, reason: Optional[str] = None):
        self.license_plate = license_plate
        self.reason = reason
        message = f"Vehicle {license_plate} is blacklisted"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class VehicleStolenException(RepositoryException):
    """Raised when a vehicle is reported as stolen."""
    def __init__(self, license_plate: str):
        self.license_plate = license_plate
        super().__init__(f"Vehicle {license_plate} has been reported as stolen")


class RegistrationExpiredException(RepositoryException):
    """Raised when vehicle registration has expired."""
    def __init__(self, vehicle_id: int, registration_id: int, expiry_date: date):
        self.vehicle_id = vehicle_id
        self.registration_id = registration_id
        self.expiry_date = expiry_date
        super().__init__(
            f"Registration for vehicle {vehicle_id} expired on {expiry_date}"
        )


class InsuranceExpiredException(RepositoryException):
    """Raised when vehicle insurance has expired."""
    def __init__(self, vehicle_id: int, insurance_id: int, expiry_date: date):
        self.vehicle_id = vehicle_id
        self.insurance_id = insurance_id
        self.expiry_date = expiry_date
        super().__init__(
            f"Insurance for vehicle {vehicle_id} expired on {expiry_date}"
        )


class InspectionRequiredException(RepositoryException):
    """Raised when vehicle inspection is required."""
    def __init__(self, vehicle_id: int, last_inspection: Optional[date] = None):
        self.vehicle_id = vehicle_id
        self.last_inspection = last_inspection
        super().__init__(
            f"Vehicle {vehicle_id} requires inspection"
        )


class InvalidLicensePlateException(ValidationException):
    """Raised when license plate format is invalid."""
    def __init__(self, license_plate: str, country: CountryCode):
        super().__init__(
            "Vehicle",
            {"license_plate": [f"Invalid license plate format for {country.value}: {license_plate"]}
        )


# ============================================================================
# Vehicle Repository
# ============================================================================

class VehicleRepository(FullFeatureRepository[Vehicle, int]):
    """
    Repository for Vehicle entity with comprehensive vehicle management features.
    
    This repository provides methods for vehicle CRUD operations,
    validation, blacklist checking, and vehicle history tracking.
    """
    
    def __init__(self, session: Session):
        super().__init__(session, Vehicle)
        self.searchable_fields = [
            'license_plate', 'vin', 'make', 'model', 
            'color', 'owner_name', 'notes'
        ]
        
        # License plate validation patterns by country
        self.license_plate_patterns = {
            CountryCode.US: r'^[A-Z0-9]{1,8}$',
            CountryCode.CA: r'^[A-Z0-9]{1,7}$',
            CountryCode.GB: r'^[A-Z]{2}[0-9]{2}[A-Z]{3}$',
            CountryCode.DE: r'^[A-Z]{1,3}[A-Z]{1,2}[0-9]{1,4}$',
            CountryCode.FR: r'^[A-Z]{2}[0-9]{3}[A-Z]{2}$',
            CountryCode.JP: r'^[0-9]{3}-[0-9]{3}$',
            CountryCode.AU: r'^[A-Z0-9]{1,6}$'
        }
    
    # ========================================================================
    # Custom Query Methods
    # ========================================================================
    
    def get_by_license_plate(
        self, 
        license_plate: str, 
        country: Optional[CountryCode] = None,
        include_inactive: bool = False
    ) -> Optional[Vehicle]:
        """
        Get vehicle by license plate.
        
        Args:
            license_plate: License plate number
            country: Optional country code for disambiguation
            include_inactive: Whether to include inactive vehicles
            
        Returns:
            Vehicle if found, None otherwise
        """
        query = self.session.query(Vehicle).filter(
            func.upper(Vehicle.license_plate) == func.upper(license_plate)
        )
        
        if country:
            query = query.filter(Vehicle.registration_country == country)
        
        if not include_inactive:
            query = query.filter(Vehicle.status.in_(VehicleStatus.get_operational_statuses()))
        
        return query.first()
    
    def get_by_vin(self, vin: str, include_inactive: bool = False) -> Optional[Vehicle]:
        """
        Get vehicle by VIN (Vehicle Identification Number).
        
        Args:
            vin: Vehicle Identification Number
            include_inactive: Whether to include inactive vehicles
            
        Returns:
            Vehicle if found, None otherwise
        """
        query = self.session.query(Vehicle).filter(
            func.upper(Vehicle.vin) == func.upper(vin)
        )
        
        if not include_inactive:
            query = query.filter(Vehicle.status.in_(VehicleStatus.get_operational_statuses()))
        
        return query.first()
    
    def get_user_vehicles(
        self,
        user_id: int,
        include_inactive: bool = False,
        ownership_type: Optional[OwnershipType] = None
    ) -> List[Vehicle]:
        """
        Get vehicles owned by a user.
        
        Args:
            user_id: User ID
            include_inactive: Whether to include inactive vehicles
            ownership_type: Optional ownership type filter
            
        Returns:
            List of user's vehicles
        """
        query = (
            self.session.query(Vehicle)
            .join(VehicleOwnership)
            .filter(VehicleOwnership.user_id == user_id)
        )
        
        if ownership_type:
            query = query.filter(VehicleOwnership.ownership_type == ownership_type)
        
        if not include_inactive:
            query = query.filter(Vehicle.status.in_(VehicleStatus.get_operational_statuses()))
        
        return query.all()
    
    def get_vehicles_by_type(
        self,
        vehicle_type: VehicleType,
        include_inactive: bool = False
    ) -> List[Vehicle]:
        """Get vehicles by type."""
        query = self.session.query(Vehicle).filter(
            Vehicle.vehicle_type == vehicle_type
        )
        
        if not include_inactive:
            query = query.filter(Vehicle.status.in_(VehicleStatus.get_operational_statuses()))
        
        return query.all()
    
    def get_vehicles_by_make_model(
        self,
        make: str,
        model: Optional[str] = None,
        year: Optional[int] = None
    ) -> List[Vehicle]:
        """Get vehicles by make, model, and year."""
        query = self.session.query(Vehicle).filter(
            func.lower(Vehicle.make) == func.lower(make)
        )
        
        if model:
            query = query.filter(func.lower(Vehicle.model) == func.lower(model))
        
        if year:
            query = query.filter(Vehicle.year == year)
        
        return query.all()
    
    def get_vehicles_needing_maintenance(
        self,
        days_before: int = 30
    ) -> List[Vehicle]:
        """
        Get vehicles needing maintenance soon.
        
        Args:
            days_before: Number of days before maintenance is due
            
        Returns:
            List of vehicles needing maintenance
        """
        cutoff_date = datetime.utcnow().date() + timedelta(days=days_before)
        
        return (
            self.session.query(Vehicle)
            .filter(
                Vehicle.status == VehicleStatus.ACTIVE,
                or_(
                    and_(
                        Vehicle.next_service_date.isnot(None),
                        Vehicle.next_service_date <= cutoff_date
                    ),
                    and_(
                        Vehicle.next_service_mileage.isnot(None),
                        Vehicle.next_service_mileage <= Vehicle.current_mileage
                    )
                )
            )
            .all()
        )
    
    def search_vehicles(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Vehicle], Dict[str, Any]]:
        """
        Search vehicles with advanced filtering.
        
        Args:
            query: Search query string
            filters: Additional filters (type, status, etc.)
            page: Page number
            per_page: Items per page
            
        Returns:
            Tuple of (vehicles, pagination_info)
        """
        qb = self.query()
        
        # Apply text search
        if query:
            qb.search(query, self.searchable_fields)
        
        # Apply filters
        if filters:
            if 'vehicle_type' in filters and filters['vehicle_type']:
                qb.filter(Vehicle.vehicle_type == filters['vehicle_type'])
            
            if 'status' in filters and filters['status']:
                qb.filter(Vehicle.status == filters['status'])
            
            if 'make' in filters and filters['make']:
                qb.filter(func.lower(Vehicle.make) == func.lower(filters['make']))
            
            if 'model' in filters and filters['model']:
                qb.filter(func.lower(Vehicle.model) == func.lower(filters['model']))
            
            if 'year_from' in filters and filters['year_from']:
                qb.filter(Vehicle.year >= filters['year_from'])
            
            if 'year_to' in filters and filters['year_to']:
                qb.filter(Vehicle.year <= filters['year_to'])
            
            if 'color' in filters and filters['color']:
                qb.filter(func.lower(Vehicle.color) == func.lower(filters['color']))
            
            if 'fuel_type' in filters and filters['fuel_type']:
                qb.filter(Vehicle.fuel_type == filters['fuel_type'])
        
        return qb.paginate(page, per_page)
    
    def get_vehicle_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get vehicle statistics.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            Dictionary with vehicle statistics
        """
        query = self.session.query(Vehicle)
        
        if user_id:
            query = query.join(VehicleOwnership).filter(VehicleOwnership.user_id == user_id)
        
        total_vehicles = query.count()
        
        # Count by status
        status_counts = {}
        for status in VehicleStatus:
            count = query.filter(Vehicle.status == status).count()
            if count > 0:
                status_counts[status.value] = count
        
        # Count by type
        type_counts = {}
        for vtype in VehicleType:
            count = query.filter(Vehicle.vehicle_type == vtype).count()
            if count > 0:
                type_counts[vtype.value] = count
        
        # Count by fuel type
        fuel_counts = {}
        for fuel in FuelType:
            count = query.filter(Vehicle.fuel_type == fuel).count()
            if count > 0:
                fuel_counts[fuel.value] = count
        
        # Average age
        current_year = datetime.utcnow().year
        avg_year = query.with_entities(func.avg(Vehicle.year)).scalar() or 0
        avg_age = current_year - avg_year if avg_year > 0 else 0
        
        # Vehicles needing attention
        needing_registration = query.filter(
            Vehicle.registration_status != RegistrationStatus.CURRENT
        ).count()
        
        needing_insurance = query.filter(
            Vehicle.insurance_status != InsuranceStatus.ACTIVE
        ).count()
        
        needing_inspection = query.filter(
            Vehicle.inspection_status != InspectionStatus.PASSED
        ).count()
        
        return {
            'total_vehicles': total_vehicles,
            'by_status': status_counts,
            'by_type': type_counts,
            'by_fuel': fuel_counts,
            'average_age': round(avg_age, 1),
            'needing_attention': {
                'registration': needing_registration,
                'insurance': needing_insurance,
                'inspection': needing_inspection
            }
        }
    
    # ========================================================================
    # Vehicle Management Methods
    # ========================================================================
    
    def create_vehicle(
        self,
        license_plate: str,
        make: str,
        model: str,
        year: int,
        vehicle_type: VehicleType,
        owner_id: int,
        ownership_type: OwnershipType = OwnershipType.OWNER,
        **kwargs
    ) -> Vehicle:
        """
        Create a new vehicle.
        
        Args:
            license_plate: License plate number
            make: Vehicle make
            model: Vehicle model
            year: Vehicle year
            vehicle_type: Type of vehicle
            owner_id: ID of the owner
            ownership_type: Type of ownership
            **kwargs: Additional vehicle attributes
            
        Returns:
            Created vehicle
            
        Raises:
            DuplicateLicensePlateException: If license plate already exists
            DuplicateVINException: If VIN already exists
            InvalidLicensePlateException: If license plate format is invalid
            ValidationException: If validation fails
        """
        # Normalize license plate
        license_plate = license_plate.upper().strip()
        
        # Validate license plate format
        country = kwargs.get('registration_country', CountryCode.US)
        self._validate_license_plate(license_plate, country)
        
        # Check for duplicate license plate
        existing = self.get_by_license_plate(license_plate, country, include_inactive=True)
        if existing:
            raise DuplicateLicensePlateException(license_plate)
        
        # Check for duplicate VIN if provided
        vin = kwargs.get('vin')
        if vin:
            vin = vin.upper().strip()
            existing_vin = self.get_by_vin(vin, include_inactive=True)
            if existing_vin:
                raise DuplicateVINException(vin)
            kwargs['vin'] = vin
        
        # Validate year
        current_year = datetime.utcnow().year
        if year < 1900 or year > current_year + 1:
            raise ValidationException(
                "Vehicle",
                {"year": [f"Year must be between 1900 and {current_year + 1}"]}
            )
        
        # Set audit context
        self.set_audit_context(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.VEHICLE,
            severity=AuditSeverity.INFO
        )
        
        # Create vehicle
        vehicle = Vehicle(
            license_plate=license_plate,
            make=make,
            model=model,
            year=year,
            vehicle_type=vehicle_type,
            status=VehicleStatus.PENDING_VERIFICATION,
            **kwargs
        )
        
        vehicle = self.create(vehicle)
        
        # Create ownership record
        ownership = VehicleOwnership(
            vehicle_id=vehicle.id,
            user_id=owner_id,
            ownership_type=ownership_type,
            is_primary=True,
            start_date=datetime.utcnow().date()
        )
        self.session.add(ownership)
        
        # Create history entry
        self._create_history_entry(
            vehicle_id=vehicle.id,
            action="CREATED",
            details={
                "license_plate": license_plate,
                "make": make,
                "model": model,
                "owner_id": owner_id
            }
        )
        
        self.session.flush()
        
        logger.info(f"Created vehicle {vehicle.id} with plate {license_plate}")
        return vehicle
    
    def update_vehicle(
        self,
        vehicle_id: int,
        **updates
    ) -> Vehicle:
        """
        Update vehicle information.
        
        Args:
            vehicle_id: Vehicle ID
            **updates: Fields to update
            
        Returns:
            Updated vehicle
            
        Raises:
            VehicleNotFoundException: If vehicle not found
            DuplicateLicensePlateException: If license plate conflict
            DuplicateVINException: If VIN conflict
        """
        vehicle = self.get_or_fail(vehicle_id)
        
        # Track changes for history
        changes = {}
        
        # Handle license plate update
        if 'license_plate' in updates and updates['license_plate'] != vehicle.license_plate:
            new_plate = updates['license_plate'].upper().strip()
            country = updates.get('registration_country', vehicle.registration_country or CountryCode.US)
            
            self._validate_license_plate(new_plate, country)
            
            existing = self.get_by_license_plate(new_plate, country, include_inactive=True)
            if existing and existing.id != vehicle_id:
                raise DuplicateLicensePlateException(new_plate)
            
            updates['license_plate'] = new_plate
            changes['license_plate'] = {
                'old': vehicle.license_plate,
                'new': new_plate
            }
        
        # Handle VIN update
        if 'vin' in updates and updates['vin'] != vehicle.vin:
            new_vin = updates['vin'].upper().strip()
            existing = self.get_by_vin(new_vin, include_inactive=True)
            if existing and existing.id != vehicle_id:
                raise DuplicateVINException(new_vin)
            updates['vin'] = new_vin
            changes['vin'] = {
                'old': vehicle.vin,
                'new': new_vin
            }
        
        # Track other changes
        for field in ['make', 'model', 'year', 'color', 'vehicle_type', 'fuel_type']:
            if field in updates and getattr(vehicle, field) != updates[field]:
                changes[field] = {
                    'old': getattr(vehicle, field),
                    'new': updates[field]
                }
        
        # Update vehicle
        for key, value in updates.items():
            if hasattr(vehicle, key):
                setattr(vehicle, key, value)
        
        vehicle = self.update_entity(vehicle)
        
        # Create history entry
        if changes:
            self._create_history_entry(
                vehicle_id=vehicle.id,
                action="UPDATED",
                details={"changes": changes}
            )
        
        logger.info(f"Updated vehicle {vehicle_id}")
        return vehicle
    
    def delete_vehicle(self, vehicle_id: int, hard_delete: bool = False) -> bool:
        """
        Delete a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            hard_delete: If True, permanently delete; if False, soft delete
            
        Returns:
            True if deleted
        """
        vehicle = self.get_or_fail(vehicle_id)
        
        # Check for active reservations
        active_reservation = (
            self.session.query(Reservation)
            .filter(
                Reservation.vehicle_id == vehicle_id,
                Reservation.status.in_(ReservationStatus.get_active_statuses())
            )
            .first()
        )
        
        if active_reservation:
            raise ValidationException(
                "Vehicle",
                {"vehicle": ["Cannot delete vehicle with active reservations"]}
            )
        
        if hard_delete:
            # Permanently delete
            result = self.delete(vehicle_id)
            action = "PERMANENTLY_DELETED"
        else:
            # Soft delete
            result = self.soft_delete(vehicle_id)
            action = "DELETED"
        
        if result:
            self._create_history_entry(
                vehicle_id=vehicle_id,
                action=action,
                details={"hard_delete": hard_delete}
            )
            
            logger.info(f"{action} vehicle {vehicle_id}")
        
        return bool(result)
    
    def update_vehicle_status(
        self,
        vehicle_id: int,
        status: VehicleStatus,
        reason: Optional[str] = None
    ) -> Vehicle:
        """
        Update vehicle status.
        
        Args:
            vehicle_id: Vehicle ID
            status: New status
            reason: Optional reason for status change
            
        Returns:
            Updated vehicle
        """
        vehicle = self.get_or_fail(vehicle_id)
        
        old_status = vehicle.status
        vehicle.status = status
        
        if reason:
            if not vehicle.metadata:
                vehicle.metadata = {}
            vehicle.metadata['last_status_change_reason'] = reason
            vehicle.metadata['last_status_change_at'] = datetime.utcnow().isoformat()
        
        vehicle = self.update_entity(vehicle)
        
        self._create_history_entry(
            vehicle_id=vehicle_id,
            action="STATUS_CHANGED",
            details={
                "old_status": old_status.value,
                "new_status": status.value,
                "reason": reason
            }
        )
        
        logger.info(f"Updated vehicle {vehicle_id} status from {old_status} to {status}")
        return vehicle
    
    def verify_vehicle(self, vehicle_id: int, verified_by: int) -> Vehicle:
        """
        Mark a vehicle as verified.
        
        Args:
            vehicle_id: Vehicle ID
            verified_by: ID of user who verified
            
        Returns:
            Updated vehicle
        """
        vehicle = self.get_or_fail(vehicle_id)
        
        vehicle.status = VehicleStatus.ACTIVE
        vehicle.verified_at = datetime.utcnow()
        vehicle.verified_by = verified_by
        
        vehicle = self.update_entity(vehicle)
        
        self._create_history_entry(
            vehicle_id=vehicle_id,
            action="VERIFIED",
            details={"verified_by": verified_by}
        )
        
        logger.info(f"Verified vehicle {vehicle_id}")
        return vehicle
    
    # ========================================================================
    # Registration Management
    # ========================================================================
    
    def add_registration(
        self,
        vehicle_id: int,
        registration_number: str,
        issue_date: date,
        expiry_date: date,
        issuing_authority: str,
        **kwargs
    ) -> VehicleRegistration:
        """
        Add a registration record for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            registration_number: Registration document number
            issue_date: Issue date
            expiry_date: Expiry date
            issuing_authority: Issuing authority
            **kwargs: Additional registration attributes
            
        Returns:
            Created registration record
        """
        vehicle = self.get_or_fail(vehicle_id)
        
        # Validate dates
        if expiry_date <= issue_date:
            raise ValidationException(
                "VehicleRegistration",
                {"expiry_date": ["Expiry date must be after issue date"]}
            )
        
        # Deactivate current registration if exists
        if vehicle.current_registration:
            vehicle.current_registration.is_current = False
        
        # Create registration
        registration = VehicleRegistration(
            vehicle_id=vehicle_id,
            registration_number=registration_number,
            issue_date=issue_date,
            expiry_date=expiry_date,
            issuing_authority=issuing_authority,
            status=RegistrationStatus.CURRENT if expiry_date >= datetime.utcnow().date() else RegistrationStatus.EXPIRED,
            is_current=True,
            **kwargs
        )
        
        self.session.add(registration)
        self.session.flush()
        
        # Update vehicle
        vehicle.registration_status = registration.status
        vehicle.current_registration_id = registration.id
        
        self.session.flush()
        
        self._create_history_entry(
            vehicle_id=vehicle_id,
            action="REGISTRATION_ADDED",
            details={
                "registration_id": registration.id,
                "expiry_date": expiry_date.isoformat()
            }
        )
        
        logger.info(f"Added registration {registration.id} for vehicle {vehicle_id}")
        return registration
    
    def update_registration_status(
        self,
        registration_id: int,
        status: RegistrationStatus
    ) -> VehicleRegistration:
        """
        Update registration status.
        
        Args:
            registration_id: Registration ID
            status: New status
            
        Returns:
            Updated registration
        """
        registration = self.session.query(VehicleRegistration).get(registration_id)
        if not registration:
            raise EntityNotFoundException("VehicleRegistration", registration_id)
        
        registration.status = status
        registration.updated_at = datetime.utcnow()
        
        # Update vehicle if this is current registration
        if registration.is_current:
            vehicle = registration.vehicle
            vehicle.registration_status = status
            vehicle.updated_at = datetime.utcnow()
        
        self.session.flush()
        
        logger.info(f"Updated registration {registration_id} status to {status}")
        return registration
    
    def get_expiring_registrations(self, days: int = 30) -> List[VehicleRegistration]:
        """
        Get registrations expiring soon.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of expiring registrations
        """
        today = datetime.utcnow().date()
        expiry_threshold = today + timedelta(days=days)
        
        return (
            self.session.query(VehicleRegistration)
            .filter(
                VehicleRegistration.is_current == True,
                VehicleRegistration.expiry_date.between(today, expiry_threshold)
            )
            .all()
        )
    
    # ========================================================================
    # Insurance Management
    # ========================================================================
    
    def add_insurance(
        self,
        vehicle_id: int,
        policy_number: str,
        provider: str,
        coverage_type: str,
        issue_date: date,
        expiry_date: date,
        **kwargs
    ) -> VehicleInsurance:
        """
        Add an insurance record for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            policy_number: Insurance policy number
            provider: Insurance provider
            coverage_type: Type of coverage
            issue_date: Issue date
            expiry_date: Expiry date
            **kwargs: Additional insurance attributes
            
        Returns:
            Created insurance record
        """
        vehicle = self.get_or_fail(vehicle_id)
        
        # Validate dates
        if expiry_date <= issue_date:
            raise ValidationException(
                "VehicleInsurance",
                {"expiry_date": ["Expiry date must be after issue date"]}
            )
        
        # Deactivate current insurance if exists
        if vehicle.current_insurance:
            vehicle.current_insurance.is_current = False
        
        # Create insurance
        insurance = VehicleInsurance(
            vehicle_id=vehicle_id,
            policy_number=policy_number,
            provider=provider,
            coverage_type=coverage_type,
            issue_date=issue_date,
            expiry_date=expiry_date,
            status=InsuranceStatus.ACTIVE if expiry_date >= datetime.utcnow().date() else InsuranceStatus.EXPIRED,
            is_current=True,
            **kwargs
        )
        
        self.session.add(insurance)
        self.session.flush()
        
        # Update vehicle
        vehicle.insurance_status = insurance.status
        vehicle.current_insurance_id = insurance.id
        
        self.session.flush()
        
        self._create_history_entry(
            vehicle_id=vehicle_id,
            action="INSURANCE_ADDED",
            details={
                "insurance_id": insurance.id,
                "expiry_date": expiry_date.isoformat()
            }
        )
        
        logger.info(f"Added insurance {insurance.id} for vehicle {vehicle_id}")
        return insurance
    
    def update_insurance_status(
        self,
        insurance_id: int,
        status: InsuranceStatus
    ) -> VehicleInsurance:
        """
        Update insurance status.
        
        Args:
            insurance_id: Insurance ID
            status: New status
            
        Returns:
            Updated insurance
        """
        insurance = self.session.query(VehicleInsurance).get(insurance_id)
        if not insurance:
            raise EntityNotFoundException("VehicleInsurance", insurance_id)
        
        insurance.status = status
        insurance.updated_at = datetime.utcnow()
        
        # Update vehicle if this is current insurance
        if insurance.is_current:
            vehicle = insurance.vehicle
            vehicle.insurance_status = status
            vehicle.updated_at = datetime.utcnow()
        
        self.session.flush()
        
        logger.info(f"Updated insurance {insurance_id} status to {status}")
        return insurance
    
    def get_expiring_insurance(self, days: int = 30) -> List[VehicleInsurance]:
        """
        Get insurance policies expiring soon.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of expiring insurance policies
        """
        today = datetime.utcnow().date()
        expiry_threshold = today + timedelta(days=days)
        
        return (
            self.session.query(VehicleInsurance)
            .filter(
                VehicleInsurance.is_current == True,
                VehicleInsurance.expiry_date.between(today, expiry_threshold)
            )
            .all()
        )
    
    # ========================================================================
    # Inspection Management
    # ========================================================================
    
    def add_inspection(
        self,
        vehicle_id: int,
        inspection_date: date,
        result: InspectionStatus,
        inspector: str,
        next_inspection_date: Optional[date] = None,
        **kwargs
    ) -> VehicleInspection:
        """
        Add an inspection record for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            inspection_date: Date of inspection
            result: Inspection result
            inspector: Inspector name/ID
            next_inspection_date: Optional next inspection date
            **kwargs: Additional inspection attributes
            
        Returns:
            Created inspection record
        """
        vehicle = self.get_or_fail(vehicle_id)
        
        # Create inspection
        inspection = VehicleInspection(
            vehicle_id=vehicle_id,
            inspection_date=inspection_date,
            result=result,
            inspector=inspector,
            next_inspection_date=next_inspection_date,
            **kwargs
        )
        
        self.session.add(inspection)
        self.session.flush()
        
        # Update vehicle
        vehicle.inspection_status = result
        vehicle.last_inspection_date = inspection_date
        vehicle.next_inspection_date = next_inspection_date
        vehicle.current_inspection_id = inspection.id
        
        self.session.flush()
        
        self._create_history_entry(
            vehicle_id=vehicle_id,
            action="INSPECTION_ADDED",
            details={
                "inspection_id": inspection.id,
                "result": result.value,
                "next_date": next_inspection_date.isoformat() if next_inspection_date else None
            }
        )
        
        logger.info(f"Added inspection {inspection.id} for vehicle {vehicle_id} with result {result}")
        return inspection
    
    def get_due_inspections(self, days: int = 30) -> List[Vehicle]:
        """
        Get vehicles due for inspection.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of vehicles due for inspection
        """
        today = datetime.utcnow().date()
        due_date = today + timedelta(days=days)
        
        return (
            self.session.query(Vehicle)
            .filter(
                Vehicle.status == VehicleStatus.ACTIVE,
                or_(
                    Vehicle.next_inspection_date <= due_date,
                    and_(
                        Vehicle.last_inspection_date.is_(None),
                        Vehicle.created_at <= today - timedelta(days=365)
                    )
                )
            )
            .all()
        )
    
    # ========================================================================
    # Ownership Management
    # ========================================================================
    
    def add_owner(
        self,
        vehicle_id: int,
        user_id: int,
        ownership_type: OwnershipType,
        is_primary: bool = False,
        start_date: Optional[date] = None
    ) -> VehicleOwnership:
        """
        Add an owner to a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            user_id: User ID
            ownership_type: Type of ownership
            is_primary: Whether this is the primary owner
            start_date: Ownership start date
            
        Returns:
            Created ownership record
        """
        vehicle = self.get_or_fail(vehicle_id)
        
        # Check if ownership already exists
        existing = (
            self.session.query(VehicleOwnership)
            .filter(
                VehicleOwnership.vehicle_id == vehicle_id,
                VehicleOwnership.user_id == user_id,
                VehicleOwnership.end_date.is_(None)
            )
            .first()
        )
        
        if existing:
            raise DuplicateEntityException(
                "VehicleOwnership",
                f"user_{user_id}_vehicle_{vehicle_id}",
                f"User {user_id} already owns vehicle {vehicle_id}"
            )
        
        # If setting as primary, clear other primary owners
        if is_primary:
            self.session.query(VehicleOwnership).filter(
                VehicleOwnership.vehicle_id == vehicle_id,
                VehicleOwnership.is_primary == True
            ).update({"is_primary": False})
        
        # Create ownership
        ownership = VehicleOwnership(
            vehicle_id=vehicle_id,
            user_id=user_id,
            ownership_type=ownership_type,
            is_primary=is_primary,
            start_date=start_date or datetime.utcnow().date()
        )
        
        self.session.add(ownership)
        self.session.flush()
        
        self._create_history_entry(
            vehicle_id=vehicle_id,
            action="OWNER_ADDED",
            details={
                "user_id": user_id,
                "ownership_type": ownership_type.value,
                "is_primary": is_primary
            }
        )
        
        logger.info(f"Added owner {user_id} to vehicle {vehicle_id}")
        return ownership
    
    def remove_owner(
        self,
        vehicle_id: int,
        user_id: int,
        end_date: Optional[date] = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Remove an owner from a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            user_id: User ID
            end_date: Ownership end date
            reason: Optional reason
            
        Returns:
            True if removed
        """
        ownership = (
            self.session.query(VehicleOwnership)
            .filter(
                VehicleOwnership.vehicle_id == vehicle_id,
                VehicleOwnership.user_id == user_id,
                VehicleOwnership.end_date.is_(None)
            )
            .first()
        )
        
        if not ownership:
            return False
        
        ownership.end_date = end_date or datetime.utcnow().date()
        ownership.end_reason = reason
        
        self.session.flush()
        
        self._create_history_entry(
            vehicle_id=vehicle_id,
            action="OWNER_REMOVED",
            details={
                "user_id": user_id,
                "reason": reason
            }
        )
        
        logger.info(f"Removed owner {user_id} from vehicle {vehicle_id}")
        return True
    
    def get_vehicle_owners(
        self,
        vehicle_id: int,
        include_past: bool = False
    ) -> List[VehicleOwnership]:
        """
        Get owners of a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            include_past: Whether to include past owners
            
        Returns:
            List of ownership records
        """
        query = self.session.query(VehicleOwnership).filter(
            VehicleOwnership.vehicle_id == vehicle_id
        )
        
        if not include_past:
            query = query.filter(VehicleOwnership.end_date.is_(None))
        
        return query.order_by(desc(VehicleOwnership.is_primary), VehicleOwnership.start_date).all()
    
    # ========================================================================
    # Document Management
    # ========================================================================
    
    def add_document(
        self,
        vehicle_id: int,
        document_type: str,
        document_url: str,
        title: str,
        **kwargs
    ) -> VehicleDocument:
        """
        Add a document to a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            document_type: Type of document
            document_url: URL to document
            title: Document title
            **kwargs: Additional document attributes
            
        Returns:
            Created document
        """
        vehicle = self.get_or_fail(vehicle_id)
        
        document = VehicleDocument(
            vehicle_id=vehicle_id,
            document_type=document_type,
            document_url=document_url,
            title=title,
            uploaded_at=datetime.utcnow(),
            **kwargs
        )
        
        self.session.add(document)
        self.session.flush()
        
        logger.info(f"Added document {document.id} to vehicle {vehicle_id}")
        return document
    
    def get_vehicle_documents(
        self,
        vehicle_id: int,
        document_type: Optional[str] = None
    ) -> List[VehicleDocument]:
        """
        Get documents for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            document_type: Optional document type filter
            
        Returns:
            List of documents
        """
        query = self.session.query(VehicleDocument).filter(
            VehicleDocument.vehicle_id == vehicle_id
        )
        
        if document_type:
            query = query.filter(VehicleDocument.document_type == document_type)
        
        return query.order_by(desc(VehicleDocument.uploaded_at)).all()
    
    # ========================================================================
    # Image Management
    # ========================================================================
    
    def add_image(
        self,
        vehicle_id: int,
        image_url: str,
        image_type: str,
        is_primary: bool = False,
        **kwargs
    ) -> VehicleImage:
        """
        Add an image to a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            image_url: URL to image
            image_type: Type of image (exterior, interior, etc.)
            is_primary: Whether this is the primary image
            **kwargs: Additional image attributes
            
        Returns:
            Created image
        """
        vehicle = self.get_or_fail(vehicle_id)
        
        # If setting as primary, clear other primary images
        if is_primary:
            self.session.query(VehicleImage).filter(
                VehicleImage.vehicle_id == vehicle_id,
                VehicleImage.is_primary == True
            ).update({"is_primary": False})
        
        image = VehicleImage(
            vehicle_id=vehicle_id,
            image_url=image_url,
            image_type=image_type,
            is_primary=is_primary,
            uploaded_at=datetime.utcnow(),
            **kwargs
        )
        
        self.session.add(image)
        self.session.flush()
        
        logger.info(f"Added image {image.id} to vehicle {vehicle_id}")
        return image
    
    def get_vehicle_images(
        self,
        vehicle_id: int,
        image_type: Optional[str] = None
    ) -> List[VehicleImage]:
        """
        Get images for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            image_type: Optional image type filter
            
        Returns:
            List of images
        """
        query = self.session.query(VehicleImage).filter(
            VehicleImage.vehicle_id == vehicle_id
        )
        
        if image_type:
            query = query.filter(VehicleImage.image_type == image_type)
        
        return query.order_by(desc(VehicleImage.is_primary), VehicleImage.sort_order).all()
    
    # ========================================================================
    # Blacklist Management
    # ========================================================================
    
    def check_blacklist(self, license_plate: str) -> Tuple[bool, Optional[VehicleBlacklist]]:
        """
        Check if a vehicle is blacklisted.
        
        Args:
            license_plate: License plate to check
            
        Returns:
            Tuple of (is_blacklisted, blacklist_entry)
        """
        license_plate = license_plate.upper().strip()
        
        blacklist_entry = (
            self.session.query(VehicleBlacklist)
            .filter(
                VehicleBlacklist.license_plate == license_plate,
                VehicleBlacklist.is_active == True,
                or_(
                    VehicleBlacklist.expires_at.is_(None),
                    VehicleBlacklist.expires_at > datetime.utcnow()
                )
            )
            .first()
        )
        
        return (blacklist_entry is not None, blacklist_entry)
    
    def add_to_blacklist(
        self,
        license_plate: str,
        reason: str,
        added_by: int,
        expires_at: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> VehicleBlacklist:
        """
        Add a vehicle to the blacklist.
        
        Args:
            license_plate: License plate
            reason: Reason for blacklisting
            added_by: ID of user adding to blacklist
            expires_at: Optional expiration date
            notes: Optional notes
            
        Returns:
            Created blacklist entry
        """
        license_plate = license_plate.upper().strip()
        
        # Check if already blacklisted
        is_blacklisted, existing = self.check_blacklist(license_plate)
        if is_blacklisted:
            raise DuplicateEntityException(
                "VehicleBlacklist",
                "license_plate",
                license_plate
            )
        
        # Deactivate any expired entries
        self.session.query(VehicleBlacklist).filter(
            VehicleBlacklist.license_plate == license_plate,
            VehicleBlacklist.is_active == True
        ).update({"is_active": False})
        
        # Create blacklist entry
        blacklist = VehicleBlacklist(
            license_plate=license_plate,
            reason=reason,
            added_by=added_by,
            added_at=datetime.utcnow(),
            expires_at=expires_at,
            notes=notes,
            is_active=True
        )
        
        self.session.add(blacklist)
        self.session.flush()
        
        # Update vehicle if exists
        vehicle = self.get_by_license_plate(license_plate)
        if vehicle:
            vehicle.status = VehicleStatus.BANNED
            vehicle.metadata = vehicle.metadata or {}
            vehicle.metadata['blacklist_reason'] = reason
            vehicle.metadata['blacklist_id'] = blacklist.id
            self.session.flush()
        
        logger.info(f"Added vehicle {license_plate} to blacklist: {reason}")
        return blacklist
    
    def remove_from_blacklist(self, license_plate: str) -> bool:
        """
        Remove a vehicle from the blacklist.
        
        Args:
            license_plate: License plate
            
        Returns:
            True if removed
        """
        license_plate = license_plate.upper().strip()
        
        blacklist = (
            self.session.query(VehicleBlacklist)
            .filter(
                VehicleBlacklist.license_plate == license_plate,
                VehicleBlacklist.is_active == True
            )
            .first()
        )
        
        if blacklist:
            blacklist.is_active = False
            blacklist.removed_at = datetime.utcnow()
            
            # Update vehicle if exists
            vehicle = self.get_by_license_plate(license_plate)
            if vehicle:
                vehicle.status = VehicleStatus.ACTIVE
                if vehicle.metadata and 'blacklist_reason' in vehicle.metadata:
                    del vehicle.metadata['blacklist_reason']
            
            self.session.flush()
            
            logger.info(f"Removed vehicle {license_plate} from blacklist")
            return True
        
        return False
    
    # ========================================================================
    # Stolen Vehicle Management
    # ========================================================================
    
    def report_stolen(
        self,
        license_plate: str,
        reported_by: int,
        report_details: Dict[str, Any],
        owner_contact: Optional[str] = None
    ) -> StolenVehicle:
        """
        Report a vehicle as stolen.
        
        Args:
            license_plate: License plate
            reported_by: ID of user reporting
            report_details: Details of the report
            owner_contact: Optional owner contact information
            
        Returns:
            Created stolen vehicle record
        """
        license_plate = license_plate.upper().strip()
        
        # Check if already reported
        existing = (
            self.session.query(StolenVehicle)
            .filter(
                StolenVehicle.license_plate == license_plate,
                StolenVehicle.is_recovered == False
            )
            .first()
        )
        
        if existing:
            raise DuplicateEntityException(
                "StolenVehicle",
                "license_plate",
                license_plate
            )
        
        # Create stolen vehicle record
        stolen = StolenVehicle(
            license_plate=license_plate,
            reported_by=reported_by,
            reported_at=datetime.utcnow(),
            report_details=report_details,
            owner_contact=owner_contact,
            is_recovered=False
        )
        
        self.session.add(stolen)
        
        # Update vehicle if exists
        vehicle = self.get_by_license_plate(license_plate)
        if vehicle:
            vehicle.status = VehicleStatus.SUSPENDED
            vehicle.metadata = vehicle.metadata or {}
            vehicle.metadata['stolen_report_id'] = stolen.id
        
        self.session.flush()
        
        # Create alert
        alert = VehicleAlert(
            vehicle_id=vehicle.id if vehicle else None,
            license_plate=license_plate,
            alert_type='stolen',
            message=f"Vehicle reported as stolen",
            severity='high',
            created_at=datetime.utcnow()
        )
        self.session.add(alert)
        
        self.session.flush()
        
        logger.info(f"Reported vehicle {license_plate} as stolen")
        return stolen
    
    def recover_vehicle(
        self,
        stolen_id: int,
        recovered_by: int,
        recovery_details: Optional[Dict] = None
    ) -> StolenVehicle:
        """
        Mark a stolen vehicle as recovered.
        
        Args:
            stolen_id: Stolen vehicle record ID
            recovered_by: ID of user marking as recovered
            recovery_details: Optional recovery details
            
        Returns:
            Updated stolen vehicle record
        """
        stolen = self.session.query(StolenVehicle).get(stolen_id)
        if not stolen:
            raise EntityNotFoundException("StolenVehicle", stolen_id)
        
        stolen.is_recovered = True
        stolen.recovered_at = datetime.utcnow()
        stolen.recovered_by = recovered_by
        stolen.recovery_details = recovery_details
        
        # Update vehicle if exists
        vehicle = self.get_by_license_plate(stolen.license_plate)
        if vehicle:
            vehicle.status = VehicleStatus.ACTIVE
            if vehicle.metadata and 'stolen_report_id' in vehicle.metadata:
                del vehicle.metadata['stolen_report_id']
        
        self.session.flush()
        
        logger.info(f"Marked vehicle {stolen.license_plate} as recovered")
        return stolen
    
    # ========================================================================
    # Vehicle History
    # ========================================================================
    
    def get_vehicle_history(
        self,
        vehicle_id: int,
        limit: int = 100
    ) -> List[VehicleHistory]:
        """
        Get history for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            limit: Maximum entries to return
            
        Returns:
            List of history entries
        """
        return (
            self.session.query(VehicleHistory)
            .filter(VehicleHistory.vehicle_id == vehicle_id)
            .order_by(desc(VehicleHistory.created_at))
            .limit(limit)
            .all()
        )
    
    def get_vehicle_by_license_history(
        self,
        license_plate: str,
        limit: int = 100
    ) -> List[VehicleHistory]:
        """
        Get history for a license plate across different vehicles.
        
        Args:
            license_plate: License plate
            limit: Maximum entries to return
            
        Returns:
            List of history entries
        """
        return (
            self.session.query(VehicleHistory)
            .filter(VehicleHistory.license_plate == license_plate.upper())
            .order_by(desc(VehicleHistory.created_at))
            .limit(limit)
            .all()
        )
    
    # ========================================================================
    # Validation Methods
    # ========================================================================
    
    def validate_vehicle_for_parking(
        self,
        vehicle_id: int,
        check_time: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if a vehicle is allowed to park.
        
        Args:
            vehicle_id: Vehicle ID
            check_time: Time to check (defaults to now)
            
        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        vehicle = self.get_or_fail(vehicle_id)
        check_time = check_time or datetime.utcnow()
        
        # Check vehicle status
        if vehicle.status not in VehicleStatus.get_operational_statuses():
            return False, f"Vehicle status is {vehicle.status.value}"
        
        # Check registration
        if vehicle.registration_status not in RegistrationStatus.get_valid_statuses():
            return False, f"Registration is {vehicle.registration_status.value}"
        
        # Check insurance
        if vehicle.insurance_status not in InsuranceStatus.get_valid_statuses():
            return False, f"Insurance is {vehicle.insurance_status.value}"
        
        # Check inspection
        if vehicle.inspection_status not in InspectionStatus.get_valid_statuses():
            return False, f"Inspection is {vehicle.inspection_status.value}"
        
        # Check if blacklisted
        is_blacklisted, blacklist = self.check_blacklist(vehicle.license_plate)
        if is_blacklisted:
            return False, f"Vehicle is blacklisted: {blacklist.reason}"
        
        return True, None
    
    def validate_license_plate_format(
        self,
        license_plate: str,
        country: CountryCode = CountryCode.US
    ) -> bool:
        """
        Validate license plate format for a country.
        
        Args:
            license_plate: License plate to validate
            country: Country code
            
        Returns:
            True if format is valid
        """
        pattern = self.license_plate_patterns.get(country)
        if not pattern:
            return True  # No pattern defined, assume valid
        
        return bool(re.match(pattern, license_plate.upper()))
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _validate_license_plate(
        self,
        license_plate: str,
        country: CountryCode
    ) -> None:
        """Validate license plate format."""
        if not self.validate_license_plate_format(license_plate, country):
            raise InvalidLicensePlateException(license_plate, country)
    
    def _create_history_entry(
        self,
        vehicle_id: int,
        action: str,
        details: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> VehicleHistory:
        """Create a history entry."""
        vehicle = self.session.query(Vehicle).get(vehicle_id)
        
        history = VehicleHistory(
            vehicle_id=vehicle_id,
            license_plate=vehicle.license_plate if vehicle else None,
            action=action,
            details=details,
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        
        self.session.add(history)
        self.session.flush()
        
        return history


# ============================================================================
# Vehicle Make/Model Repository
# ============================================================================

class VehicleMakeRepository(BaseRepository[VehicleMake, int]):
    """Repository for VehicleMake entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, VehicleMake)
    
    def get_by_name(self, name: str) -> Optional[VehicleMake]:
        """Get vehicle make by name."""
        return (
            self.session.query(VehicleMake)
            .filter(func.lower(VehicleMake.name) == func.lower(name))
            .first()
        )
    
    def get_popular_makes(self, limit: int = 20) -> List[VehicleMake]:
        """Get most popular vehicle makes."""
        return (
            self.session.query(VehicleMake)
            .order_by(desc(VehicleMake.popularity))
            .limit(limit)
            .all()
        )
    
    def search_makes(self, query: str, limit: int = 10) -> List[VehicleMake]:
        """Search vehicle makes."""
        return (
            self.session.query(VehicleMake)
            .filter(VehicleMake.name.ilike(f"%{query}%"))
            .order_by(desc(VehicleMake.popularity))
            .limit(limit)
            .all()
        )


class VehicleModelRepository(BaseRepository[VehicleModel, int]):
    """Repository for VehicleModel entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, VehicleModel)
    
    def get_by_make(
        self,
        make_id: int,
        year: Optional[int] = None
    ) -> List[VehicleModel]:
        """Get models for a make."""
        query = self.session.query(VehicleModel).filter(
            VehicleModel.make_id == make_id
        )
        
        if year:
            query = query.filter(
                VehicleModel.start_year <= year,
                or_(
                    VehicleModel.end_year.is_(None),
                    VehicleModel.end_year >= year
                )
            )
        
        return query.order_by(VehicleModel.name).all()
    
    def get_by_name_and_make(
        self,
        name: str,
        make_id: int
    ) -> Optional[VehicleModel]:
        """Get model by name and make."""
        return (
            self.session.query(VehicleModel)
            .filter(
                func.lower(VehicleModel.name) == func.lower(name),
                VehicleModel.make_id == make_id
            )
            .first()
        )
    
    def search_models(
        self,
        query: str,
        make_id: Optional[int] = None,
        limit: int = 10
    ) -> List[VehicleModel]:
        """Search vehicle models."""
        q = self.session.query(VehicleModel).filter(
            VehicleModel.name.ilike(f"%{query}%")
        )
        
        if make_id:
            q = q.filter(VehicleModel.make_id == make_id)
        
        return q.limit(limit).all()


# ============================================================================
# Vehicle Alert Repository
# ============================================================================

class VehicleAlertRepository(BaseRepository[VehicleAlert, int]):
    """Repository for VehicleAlert entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, VehicleAlert)
    
    def get_active_alerts(
        self,
        vehicle_id: Optional[int] = None,
        license_plate: Optional[str] = None
    ) -> List[VehicleAlert]:
        """Get active alerts."""
        query = self.session.query(VehicleAlert).filter(
            VehicleAlert.is_resolved == False
        )
        
        if vehicle_id:
            query = query.filter(VehicleAlert.vehicle_id == vehicle_id)
        
        if license_plate:
            query = query.filter(VehicleAlert.license_plate == license_plate.upper())
        
        return query.order_by(desc(VehicleAlert.severity), desc(VehicleAlert.created_at)).all()
    
    def create_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = 'medium',
        vehicle_id: Optional[int] = None,
        license_plate: Optional[str] = None,
        **kwargs
    ) -> VehicleAlert:
        """Create a new alert."""
        alert = VehicleAlert(
            vehicle_id=vehicle_id,
            license_plate=license_plate.upper() if license_plate else None,
            alert_type=alert_type,
            message=message,
            severity=severity,
            created_at=datetime.utcnow(),
            is_resolved=False,
            **kwargs
        )
        
        self.session.add(alert)
        self.session.flush()
        
        logger.info(f"Created alert {alert.id}: {alert_type} - {message}")
        return alert
    
    def resolve_alert(
        self,
        alert_id: int,
        resolution: str,
        resolved_by: Optional[int] = None
    ) -> VehicleAlert:
        """Resolve an alert."""
        alert = self.get_or_fail(alert_id)
        
        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = resolved_by
        alert.resolution = resolution
        
        self.session.flush()
        
        logger.info(f"Resolved alert {alert_id}")
        return alert


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main Repository
    'VehicleRepository',
    'VehicleMakeRepository',
    'VehicleModelRepository',
    'VehicleAlertRepository',
    
    # Exceptions
    'VehicleNotFoundException',
    'DuplicateLicensePlateException',
    'DuplicateVINException',
    'VehicleBlacklistedException',
    'VehicleStolenException',
    'RegistrationExpiredException',
    'InsuranceExpiredException',
    'InspectionRequiredException',
    'InvalidLicensePlateException',
]