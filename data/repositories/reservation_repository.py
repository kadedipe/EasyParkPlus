# parking-management/data/migrations/repositories/reservation_repository.py
"""
Reservation repository module for the parking management system.

This module provides repository classes for managing reservations, check-in/out,
waitlist, and recurring bookings with comprehensive integration with the enum definitions.
"""

from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
import json
import secrets
from uuid import uuid4

from sqlalchemy import (
    and_, or_, not_, desc, asc, func, select,
    update, delete, between, cast, Float, Integer,
    String, DateTime, Boolean, Numeric, Interval
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
from .parking_spot_repository import ParkingSpotRepository
from ..models.enums import (
    # Reservation enums
    ReservationStatus,
    ReservationType,
    PaymentStatus,
    RecurringFrequency,
    WaitlistStatus,
    
    # Parking enums
    SpotType,
    SpotStatus,
    
    # Payment enums
    PaymentMethodType,
    
    # Notification enums
    NotificationType,
    NotificationPriority,
    
    # Audit enums
    AuditAction,
    AuditStatus,
    AuditSeverity,
    AuditCategory,
    AuditResourceType
)
from ..models.reservation_models import (
    Reservation,
    RecurringReservation,
    ReservationHistory,
    Waitlist,
    ReservationPayment,
    ReservationVehicle,
    ReservationAddon,
    ReservationNote,
    ReservationReminder,
    ReservationExtension,
    ReservationCancellation,
    ReservationNoShow,
    ReservationCheckIn,
    ReservationCheckOut
)
from ..models.parking_models import (
    ParkingSpot,
    ParkingZone
)
from ..models.user_models import (
    User
)
from ..models.vehicle_models import (
    Vehicle
)
from ..models.payment_models import (
    Payment,
    Invoice
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class ReservationNotFoundException(EntityNotFoundException):
    """Raised when a reservation is not found."""
    def __init__(self, reservation_id: Any):
        super().__init__("Reservation", reservation_id)


class ReservationConflictException(RepositoryException):
    """Raised when a reservation conflicts with an existing one."""
    def __init__(self, spot_id: int, start_time: datetime, end_time: datetime):
        self.spot_id = spot_id
        self.start_time = start_time
        self.end_time = end_time
        super().__init__(
            f"Reservation conflict for spot {spot_id} between "
            f"{start_time.isoformat()} and {end_time.isoformat()}"
        )


class InvalidReservationStateException(RepositoryException):
    """Raised when an operation is invalid for the current reservation state."""
    def __init__(self, reservation_id: int, current_status: ReservationStatus, operation: str):
        self.reservation_id = reservation_id
        self.current_status = current_status
        self.operation = operation
        super().__init__(
            f"Cannot {operation} reservation {reservation_id} "
            f"in status {current_status.value}"
        )


class CheckInWindowException(RepositoryException):
    """Raised when checking in outside the allowed window."""
    def __init__(self, reservation_id: int, check_in_time: datetime, allowed_from: datetime):
        self.reservation_id = reservation_id
        self.check_in_time = check_in_time
        self.allowed_from = allowed_from
        super().__init__(
            f"Check-in for reservation {reservation_id} at {check_in_time.isoformat()} "
            f"is before allowed time {allowed_from.isoformat()}"
        )


class CheckOutWindowException(RepositoryException):
    """Raised when checking out outside the allowed window."""
    def __init__(self, reservation_id: int, check_out_time: datetime, allowed_until: datetime):
        self.reservation_id = reservation_id
        self.check_out_time = check_out_time
        self.allowed_until = allowed_until
        super().__init__(
            f"Check-out for reservation {reservation_id} at {check_out_time.isoformat()} "
            f"is after allowed time {allowed_until.isoformat()}"
        )


class MaxExtensionsExceededException(RepositoryException):
    """Raised when maximum number of extensions has been reached."""
    def __init__(self, reservation_id: int, max_extensions: int):
        self.reservation_id = reservation_id
        self.max_extensions = max_extensions
        super().__init__(
            f"Reservation {reservation_id} has reached maximum extensions ({max_extensions})"
        )


class WaitlistAlreadyExistsException(RepositoryException):
    """Raised when a user is already on the waitlist for a spot/time."""
    def __init__(self, user_id: int, spot_id: int, date_from: datetime):
        self.user_id = user_id
        self.spot_id = spot_id
        self.date_from = date_from
        super().__init__(
            f"User {user_id} is already on waitlist for spot {spot_id} from {date_from.isoformat()}"
        )


class NoShowException(RepositoryException):
    """Raised when a reservation becomes a no-show."""
    def __init__(self, reservation_id: int, grace_period_minutes: int):
        self.reservation_id = reservation_id
        self.grace_period_minutes = grace_period_minutes
        super().__init__(
            f"Reservation {reservation_id} is a no-show after {grace_period_minutes} minutes grace period"
        )


# ============================================================================
# Reservation Repository
# ============================================================================

class ReservationRepository(FullFeatureRepository[Reservation, int]):
    """
    Repository for Reservation entity with comprehensive reservation management features.
    
    This repository provides methods for reservation CRUD operations,
    availability checking, check-in/out, and waitlist management.
    """
    
    def __init__(self, session: Session):
        super().__init__(session, Reservation)
        self.searchable_fields = ['confirmation_code', 'notes']
        self.spot_repository = ParkingSpotRepository(session)
        
        # Configuration
        self.max_extensions_per_reservation = 3
        self.max_extension_minutes = 120
        self.check_in_grace_period_minutes = 15
        self.check_out_grace_period_minutes = 15
        self.no_show_minutes = 30
        self.minimum_notice_minutes = 30
        self.cancellation_fee_minutes = 60
    
    # ========================================================================
    # Custom Query Methods
    # ========================================================================
    
    def get_by_confirmation_code(self, confirmation_code: str) -> Optional[Reservation]:
        """
        Get reservation by confirmation code.
        
        Args:
            confirmation_code: Unique confirmation code
            
        Returns:
            Reservation if found, None otherwise
        """
        return (
            self.session.query(Reservation)
            .filter(Reservation.confirmation_code == confirmation_code)
            .first()
        )
    
    def get_user_reservations(
        self,
        user_id: int,
        statuses: Optional[List[ReservationStatus]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Reservation]:
        """
        Get reservations for a user.
        
        Args:
            user_id: User ID
            statuses: Optional list of statuses to filter by
            from_date: Optional start date
            to_date: Optional end date
            limit: Maximum number of reservations to return
            
        Returns:
            List of user's reservations
        """
        query = self.session.query(Reservation).filter(
            Reservation.user_id == user_id
        )
        
        if statuses:
            query = query.filter(Reservation.status.in_(statuses))
        
        if from_date:
            query = query.filter(Reservation.start_time >= from_date)
        
        if to_date:
            query = query.filter(Reservation.start_time <= to_date)
        
        return query.order_by(desc(Reservation.start_time)).limit(limit).all()
    
    def get_spot_reservations(
        self,
        spot_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        statuses: Optional[List[ReservationStatus]] = None
    ) -> List[Reservation]:
        """
        Get reservations for a specific spot.
        
        Args:
            spot_id: Spot ID
            from_date: Optional start date
            to_date: Optional end date
            statuses: Optional list of statuses to filter by
            
        Returns:
            List of spot reservations
        """
        query = self.session.query(Reservation).filter(
            Reservation.spot_id == spot_id
        )
        
        if from_date:
            query = query.filter(Reservation.end_time >= from_date)
        
        if to_date:
            query = query.filter(Reservation.start_time <= to_date)
        
        if statuses:
            query = query.filter(Reservation.status.in_(statuses))
        
        return query.order_by(Reservation.start_time).all()
    
    def get_upcoming_reservations(
        self,
        user_id: Optional[int] = None,
        minutes_ahead: int = 60,
        limit: int = 100
    ) -> List[Reservation]:
        """
        Get upcoming reservations within the next N minutes.
        
        Args:
            user_id: Optional user ID filter
            minutes_ahead: Minutes ahead to look
            limit: Maximum number to return
            
        Returns:
            List of upcoming reservations
        """
        now = datetime.utcnow()
        cutoff = now + timedelta(minutes=minutes_ahead)
        
        query = self.session.query(Reservation).filter(
            Reservation.status.in_([ReservationStatus.CONFIRMED]),
            Reservation.start_time.between(now, cutoff)
        )
        
        if user_id:
            query = query.filter(Reservation.user_id == user_id)
        
        return query.order_by(Reservation.start_time).limit(limit).all()
    
    def get_active_reservations(
        self,
        spot_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> List[Reservation]:
        """
        Get currently active reservations.
        
        Args:
            spot_id: Optional spot ID filter
            user_id: Optional user ID filter
            
        Returns:
            List of active reservations
        """
        now = datetime.utcnow()
        
        query = self.session.query(Reservation).filter(
            Reservation.status.in_(ReservationStatus.get_active_statuses()),
            Reservation.start_time <= now,
            Reservation.end_time >= now
        )
        
        if spot_id:
            query = query.filter(Reservation.spot_id == spot_id)
        
        if user_id:
            query = query.filter(Reservation.user_id == user_id)
        
        return query.all()
    
    def get_reservations_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        spot_id: Optional[int] = None,
        zone_id: Optional[int] = None,
        statuses: Optional[List[ReservationStatus]] = None
    ) -> List[Reservation]:
        """
        Get reservations within a time range.
        
        Args:
            start_time: Range start
            end_time: Range end
            spot_id: Optional spot filter
            zone_id: Optional zone filter
            statuses: Optional status filter
            
        Returns:
            List of reservations in the range
        """
        query = self.session.query(Reservation).filter(
            Reservation.start_time < end_time,
            Reservation.end_time > start_time
        )
        
        if spot_id:
            query = query.filter(Reservation.spot_id == spot_id)
        
        if zone_id:
            query = query.join(ParkingSpot).filter(ParkingSpot.zone_id == zone_id)
        
        if statuses:
            query = query.filter(Reservation.status.in_(statuses))
        
        return query.order_by(Reservation.start_time).all()
    
    def get_reservations_by_date(
        self,
        date: date,
        zone_id: Optional[int] = None
    ) -> List[Reservation]:
        """
        Get reservations for a specific date.
        
        Args:
            date: The date to query
            zone_id: Optional zone filter
            
        Returns:
            List of reservations on that date
        """
        start_of_day = datetime.combine(date, time.min)
        end_of_day = datetime.combine(date, time.max)
        
        return self.get_reservations_in_range(start_of_day, end_of_day, zone_id=zone_id)
    
    def get_overdue_checkouts(
        self,
        grace_minutes: int = 15
    ) -> List[Reservation]:
        """
        Get reservations that are overdue for checkout.
        
        Args:
            grace_minutes: Grace period minutes
            
        Returns:
            List of overdue reservations
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=grace_minutes)
        
        return (
            self.session.query(Reservation)
            .filter(
                Reservation.status == ReservationStatus.CHECKED_IN,
                Reservation.end_time <= cutoff
            )
            .all()
        )
    
    def get_no_show_candidates(
        self,
        grace_minutes: int = 30
    ) -> List[Reservation]:
        """
        Get reservations that are candidates for no-show.
        
        Args:
            grace_minutes: Grace period after start time
            
        Returns:
            List of no-show candidates
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=grace_minutes)
        
        return (
            self.session.query(Reservation)
            .filter(
                Reservation.status == ReservationStatus.CONFIRMED,
                Reservation.start_time <= cutoff
            )
            .all()
        )
    
    def get_reservation_statistics(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        zone_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get reservation statistics.
        
        Args:
            from_date: Start date
            to_date: End date
            zone_id: Optional zone filter
            
        Returns:
            Dictionary with statistics
        """
        query = self.session.query(Reservation)
        
        if zone_id:
            query = query.join(ParkingSpot).filter(ParkingSpot.zone_id == zone_id)
        
        if from_date:
            query = query.filter(Reservation.created_at >= from_date)
        
        if to_date:
            query = query.filter(Reservation.created_at <= to_date)
        
        # Total counts by status
        status_counts = {}
        for status in ReservationStatus:
            count = query.filter(Reservation.status == status).count()
            if count > 0:
                status_counts[status.value] = count
        
        # Completed reservations
        completed = query.filter(
            Reservation.status.in_(ReservationStatus.get_past_statuses())
        ).all()
        
        # Average duration
        if completed:
            total_duration = sum(
                (r.end_time - r.start_time).total_seconds() / 3600
                for r in completed
            )
            avg_duration = total_duration / len(completed)
        else:
            avg_duration = 0
        
        # Cancellation rate
        total_reservations = query.count()
        cancelled = query.filter(Reservation.status == ReservationStatus.CANCELLED).count()
        cancellation_rate = (cancelled / total_reservations * 100) if total_reservations > 0 else 0
        
        # No-show rate
        no_show = query.filter(Reservation.status == ReservationStatus.NO_SHOW).count()
        no_show_rate = (no_show / total_reservations * 100) if total_reservations > 0 else 0
        
        # Peak hours
        peak_hours = {}
        for r in completed:
            hour = r.start_time.hour
            peak_hours[hour] = peak_hours.get(hour, 0) + 1
        
        return {
            'total_reservations': total_reservations,
            'by_status': status_counts,
            'average_duration_hours': round(avg_duration, 2),
            'cancellation_rate': round(cancellation_rate, 2),
            'no_show_rate': round(no_show_rate, 2),
            'peak_hours': peak_hours,
            'completed_count': len(completed)
        }
    
    # ========================================================================
    # Reservation Management Methods
    # ========================================================================
    
    def create_reservation(
        self,
        user_id: int,
        spot_id: int,
        vehicle_id: int,
        start_time: datetime,
        end_time: datetime,
        reservation_type: ReservationType = ReservationType.STANDARD,
        **kwargs
    ) -> Reservation:
        """
        Create a new reservation.
        
        Args:
            user_id: User ID
            spot_id: Spot ID
            vehicle_id: Vehicle ID
            start_time: Reservation start time
            end_time: Reservation end time
            reservation_type: Type of reservation
            **kwargs: Additional reservation attributes
            
        Returns:
            Created reservation
            
        Raises:
            ReservationConflictException: If spot is not available
            ValidationException: If validation fails
        """
        # Validate times
        self._validate_reservation_times(start_time, end_time)
        
        # Check spot availability
        spot = self.spot_repository.get_or_fail(spot_id)
        
        is_available, reason = self.spot_repository.check_spot_availability(
            spot_id, start_time, end_time
        )
        
        if not is_available:
            raise ReservationConflictException(spot_id, start_time, end_time)
        
        # Generate confirmation code
        confirmation_code = self._generate_confirmation_code()
        
        # Set audit context
        self.set_audit_context(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.RESERVATION,
            severity=AuditSeverity.INFO
        )
        
        # Create reservation
        reservation = Reservation(
            user_id=user_id,
            spot_id=spot_id,
            vehicle_id=vehicle_id,
            confirmation_code=confirmation_code,
            start_time=start_time,
            end_time=end_time,
            reservation_type=reservation_type,
            status=ReservationStatus.PENDING,
            **kwargs
        )
        
        reservation = self.create(reservation)
        
        # Update spot reservation status
        self.spot_repository.reserve_spot(spot_id, reservation.id, start_time, end_time)
        
        # Create history entry
        self._create_history_entry(
            reservation.id,
            ReservationStatus.PENDING,
            {"created": True}
        )
        
        # Schedule reminders
        self._schedule_reminders(reservation)
        
        logger.info(
            f"Created reservation {reservation.id} for user {user_id} "
            f"at spot {spot_id} from {start_time} to {end_time}"
        )
        
        return reservation
    
    def confirm_reservation(
        self,
        reservation_id: int,
        payment_id: Optional[int] = None
    ) -> Reservation:
        """
        Confirm a pending reservation.
        
        Args:
            reservation_id: Reservation ID
            payment_id: Optional payment ID
            
        Returns:
            Confirmed reservation
            
        Raises:
            ReservationNotFoundException: If reservation not found
            InvalidReservationStateException: If reservation not in pending state
        """
        reservation = self.get_or_fail(reservation_id)
        
        if reservation.status != ReservationStatus.PENDING:
            raise InvalidReservationStateException(
                reservation_id,
                reservation.status,
                "confirm"
            )
        
        old_status = reservation.status
        reservation.status = ReservationStatus.CONFIRMED
        reservation.confirmed_at = datetime.utcnow()
        
        if payment_id:
            reservation.payment_id = payment_id
        
        reservation = self.update_entity(reservation)
        
        # Create history entry
        self._create_history_entry(
            reservation_id,
            ReservationStatus.CONFIRMED,
            {
                "old_status": old_status.value,
                "payment_id": payment_id
            }
        )
        
        logger.info(f"Confirmed reservation {reservation_id}")
        return reservation
    
    def cancel_reservation(
        self,
        reservation_id: int,
        reason: Optional[str] = None,
        cancelled_by: Optional[int] = None,
        refund_amount: Optional[Decimal] = None
    ) -> Reservation:
        """
        Cancel a reservation.
        
        Args:
            reservation_id: Reservation ID
            reason: Optional cancellation reason
            cancelled_by: Optional ID of user cancelling
            refund_amount: Optional refund amount
            
        Returns:
            Cancelled reservation
            
        Raises:
            ReservationNotFoundException: If reservation not found
            InvalidReservationStateException: If reservation cannot be cancelled
        """
        reservation = self.get_or_fail(reservation_id)
        
        if reservation.status not in ReservationStatus.get_cancellable_statuses():
            raise InvalidReservationStateException(
                reservation_id,
                reservation.status,
                "cancel"
            )
        
        old_status = reservation.status
        reservation.status = ReservationStatus.CANCELLED
        reservation.cancelled_at = datetime.utcnow()
        
        # Create cancellation record
        cancellation = ReservationCancellation(
            reservation_id=reservation_id,
            cancelled_by=cancelled_by,
            cancelled_at=datetime.utcnow(),
            reason=reason,
            refund_amount=refund_amount,
            original_status=old_status
        )
        self.session.add(cancellation)
        
        # Update spot
        self.spot_repository.cancel_reservation(reservation.spot_id, reservation_id)
        
        reservation = self.update_entity(reservation)
        
        # Create history entry
        self._create_history_entry(
            reservation_id,
            ReservationStatus.CANCELLED,
            {
                "old_status": old_status.value,
                "reason": reason,
                "cancelled_by": cancelled_by,
                "refund_amount": str(refund_amount) if refund_amount else None
            }
        )
        
        logger.info(f"Cancelled reservation {reservation_id}: {reason}")
        return reservation
    
    def modify_reservation(
        self,
        reservation_id: int,
        **modifications
    ) -> Reservation:
        """
        Modify an existing reservation.
        
        Args:
            reservation_id: Reservation ID
            **modifications: Fields to modify (start_time, end_time, vehicle_id, etc.)
            
        Returns:
            Modified reservation
            
        Raises:
            ReservationNotFoundException: If reservation not found
            InvalidReservationStateException: If reservation cannot be modified
            ReservationConflictException: If new times conflict
        """
        reservation = self.get_or_fail(reservation_id)
        
        if reservation.status not in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]:
            raise InvalidReservationStateException(
                reservation_id,
                reservation.status,
                "modify"
            )
        
        # Track changes
        changes = {}
        
        # Handle time modifications
        if 'start_time' in modifications or 'end_time' in modifications:
            new_start = modifications.get('start_time', reservation.start_time)
            new_end = modifications.get('end_time', reservation.end_time)
            
            self._validate_reservation_times(new_start, new_end)
            
            # Check availability for new times (excluding current reservation)
            is_available, reason = self._check_availability_excluding_current(
                reservation.spot_id,
                new_start,
                new_end,
                reservation_id
            )
            
            if not is_available:
                raise ReservationConflictException(
                    reservation.spot_id,
                    new_start,
                    new_end
                )
            
            changes['times'] = {
                'old': {
                    'start': reservation.start_time.isoformat(),
                    'end': reservation.end_time.isoformat()
                },
                'new': {
                    'start': new_start.isoformat(),
                    'end': new_end.isoformat()
                }
            }
            
            reservation.start_time = new_start
            reservation.end_time = new_end
        
        # Handle vehicle modification
        if 'vehicle_id' in modifications and modifications['vehicle_id'] != reservation.vehicle_id:
            changes['vehicle'] = {
                'old': reservation.vehicle_id,
                'new': modifications['vehicle_id']
            }
            reservation.vehicle_id = modifications['vehicle_id']
        
        # Update other fields
        for field in ['notes', 'reservation_type']:
            if field in modifications:
                changes[field] = {
                    'old': getattr(reservation, field),
                    'new': modifications[field]
                }
                setattr(reservation, field, modifications[field])
        
        reservation.modified_at = datetime.utcnow()
        reservation.modification_count = (reservation.modification_count or 0) + 1
        reservation.status = ReservationStatus.MODIFIED
        
        reservation = self.update_entity(reservation)
        
        # Create history entry
        self._create_history_entry(
            reservation_id,
            ReservationStatus.MODIFIED,
            {
                "changes": changes,
                "modification_count": reservation.modification_count
            }
        )
        
        logger.info(f"Modified reservation {reservation_id}: {changes}")
        return reservation
    
    def extend_reservation(
        self,
        reservation_id: int,
        extension_minutes: int,
        reason: Optional[str] = None
    ) -> Reservation:
        """
        Extend a reservation's end time.
        
        Args:
            reservation_id: Reservation ID
            extension_minutes: Minutes to extend
            reason: Optional reason for extension
            
        Returns:
            Extended reservation
            
        Raises:
            ReservationNotFoundException: If reservation not found
            InvalidReservationStateException: If reservation cannot be extended
            MaxExtensionsExceededException: If max extensions reached
            ReservationConflictException: If extension conflicts
        """
        reservation = self.get_or_fail(reservation_id)
        
        if reservation.status != ReservationStatus.CHECKED_IN:
            raise InvalidReservationStateException(
                reservation_id,
                reservation.status,
                "extend"
            )
        
        # Check extension limits
        current_extensions = len(reservation.extensions or [])
        if current_extensions >= self.max_extensions_per_reservation:
            raise MaxExtensionsExceededException(
                reservation_id,
                self.max_extensions_per_reservation
            )
        
        if extension_minutes > self.max_extension_minutes:
            raise ValidationException(
                "Reservation",
                {"extension_minutes": [f"Cannot extend more than {self.max_extension_minutes} minutes"]}
            )
        
        new_end = reservation.end_time + timedelta(minutes=extension_minutes)
        
        # Check availability for extension
        is_available, reason = self._check_availability_excluding_current(
            reservation.spot_id,
            reservation.start_time,
            new_end,
            reservation_id
        )
        
        if not is_available:
            raise ReservationConflictException(
                reservation.spot_id,
                reservation.start_time,
                new_end
            )
        
        old_end = reservation.end_time
        reservation.end_time = new_end
        
        # Create extension record
        extension = ReservationExtension(
            reservation_id=reservation_id,
            extended_by_minutes=extension_minutes,
            old_end_time=old_end,
            new_end_time=new_end,
            reason=reason,
            extended_at=datetime.utcnow()
        )
        self.session.add(extension)
        
        if not reservation.extensions:
            reservation.extensions = []
        reservation.extensions.append(extension)
        
        reservation = self.update_entity(reservation)
        
        # Create history entry
        self._create_history_entry(
            reservation_id,
            reservation.status,
            {
                "extended": True,
                "minutes": extension_minutes,
                "old_end": old_end.isoformat(),
                "new_end": new_end.isoformat(),
                "reason": reason
            }
        )
        
        logger.info(f"Extended reservation {reservation_id} by {extension_minutes} minutes")
        return reservation
    
    # ========================================================================
    # Check-in/Check-out Methods
    # ========================================================================
    
    def check_in(
        self,
        reservation_id: int,
        license_plate: Optional[str] = None,
        check_in_method: str = "app",
        notes: Optional[str] = None
    ) -> Reservation:
        """
        Check in to a reservation.
        
        Args:
            reservation_id: Reservation ID
            license_plate: Optional license plate for verification
            check_in_method: Method of check-in (app, gate, kiosk, etc.)
            notes: Optional check-in notes
            
        Returns:
            Updated reservation
            
        Raises:
            ReservationNotFoundException: If reservation not found
            InvalidReservationStateException: If cannot check in
            CheckInWindowException: If checking in too early
        """
        reservation = self.get_or_fail(reservation_id)
        
        if reservation.status not in [ReservationStatus.CONFIRMED, ReservationStatus.PENDING]:
            raise InvalidReservationStateException(
                reservation_id,
                reservation.status,
                "check in"
            )
        
        now = datetime.utcnow()
        
        # Check if within check-in window
        earliest_check_in = reservation.start_time - timedelta(minutes=self.check_in_grace_period_minutes)
        if now < earliest_check_in:
            raise CheckInWindowException(reservation_id, now, earliest_check_in)
        
        # Verify license plate if provided
        if license_plate:
            vehicle = reservation.vehicle
            if vehicle and vehicle.license_plate != license_plate:
                raise ValidationException(
                    "Reservation",
                    {"license_plate": ["License plate does not match reservation"]}
                )
        
        old_status = reservation.status
        reservation.status = ReservationStatus.CHECKED_IN
        reservation.checked_in_at = now
        
        # Create check-in record
        check_in = ReservationCheckIn(
            reservation_id=reservation_id,
            checked_in_at=now,
            method=check_in_method,
            notes=notes,
            verified_license_plate=license_plate
        )
        self.session.add(check_in)
        
        # Update spot
        spot = self.spot_repository.get_or_fail(reservation.spot_id)
        self.spot_repository.assign_vehicle_to_spot(
            spot.id,
            reservation.vehicle_id,
            reservation_id
        )
        
        reservation = self.update_entity(reservation)
        
        # Create history entry
        self._create_history_entry(
            reservation_id,
            ReservationStatus.CHECKED_IN,
            {
                "old_status": old_status.value,
                "method": check_in_method,
                "time": now.isoformat()
            }
        )
        
        logger.info(f"Checked in to reservation {reservation_id} at {now}")
        return reservation
    
    def check_out(
        self,
        reservation_id: int,
        check_out_method: str = "app",
        notes: Optional[str] = None
    ) -> Reservation:
        """
        Check out from a reservation.
        
        Args:
            reservation_id: Reservation ID
            check_out_method: Method of check-out
            notes: Optional check-out notes
            
        Returns:
            Updated reservation
            
        Raises:
            ReservationNotFoundException: If reservation not found
            InvalidReservationStateException: If cannot check out
        """
        reservation = self.get_or_fail(reservation_id)
        
        if reservation.status != ReservationStatus.CHECKED_IN:
            raise InvalidReservationStateException(
                reservation_id,
                reservation.status,
                "check out"
            )
        
        now = datetime.utcnow()
        
        old_status = reservation.status
        reservation.status = ReservationStatus.COMPLETED
        reservation.checked_out_at = now
        
        # Create check-out record
        check_out = ReservationCheckOut(
            reservation_id=reservation_id,
            checked_out_at=now,
            method=check_out_method,
            notes=notes
        )
        self.session.add(check_out)
        
        # Release spot
        self.spot_repository.release_spot(reservation.spot_id, reservation.vehicle_id)
        
        # Calculate actual duration
        actual_duration = (now - (reservation.checked_in_at or reservation.start_time)).total_seconds() / 60
        reservation.actual_duration_minutes = actual_duration
        
        reservation = self.update_entity(reservation)
        
        # Create history entry
        self._create_history_entry(
            reservation_id,
            ReservationStatus.COMPLETED,
            {
                "old_status": old_status.value,
                "method": check_out_method,
                "time": now.isoformat(),
                "actual_duration_minutes": actual_duration
            }
        )
        
        logger.info(f"Checked out from reservation {reservation_id} at {now}")
        return reservation
    
    def mark_no_show(
        self,
        reservation_id: int,
        reason: Optional[str] = None
    ) -> Reservation:
        """
        Mark a reservation as no-show.
        
        Args:
            reservation_id: Reservation ID
            reason: Optional reason
            
        Returns:
            Updated reservation
        """
        reservation = self.get_or_fail(reservation_id)
        
        if reservation.status != ReservationStatus.CONFIRMED:
            raise InvalidReservationStateException(
                reservation_id,
                reservation.status,
                "mark no-show"
            )
        
        old_status = reservation.status
        reservation.status = ReservationStatus.NO_SHOW
        reservation.no_show_at = datetime.utcnow()
        
        # Create no-show record
        no_show = ReservationNoShow(
            reservation_id=reservation_id,
            occurred_at=datetime.utcnow(),
            reason=reason
        )
        self.session.add(no_show)
        
        # Release spot reservation
        self.spot_repository.cancel_reservation(reservation.spot_id, reservation_id)
        
        reservation = self.update_entity(reservation)
        
        # Create history entry
        self._create_history_entry(
            reservation_id,
            ReservationStatus.NO_SHOW,
            {
                "old_status": old_status.value,
                "reason": reason
            }
        )
        
        logger.info(f"Marked reservation {reservation_id} as no-show")
        return reservation
    
    # ========================================================================
    # Payment Methods
    # ========================================================================
    
    def add_payment(
        self,
        reservation_id: int,
        amount: Decimal,
        payment_method: PaymentMethodType,
        transaction_id: Optional[str] = None,
        **kwargs
    ) -> ReservationPayment:
        """
        Add a payment to a reservation.
        
        Args:
            reservation_id: Reservation ID
            amount: Payment amount
            payment_method: Payment method
            transaction_id: Optional transaction ID
            **kwargs: Additional payment data
            
        Returns:
            Created payment record
        """
        reservation = self.get_or_fail(reservation_id)
        
        payment = ReservationPayment(
            reservation_id=reservation_id,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id,
            status=PaymentStatus.PENDING,
            payment_data=kwargs,
            created_at=datetime.utcnow()
        )
        
        self.session.add(payment)
        self.session.flush()
        
        # Update reservation total
        if not reservation.total_paid:
            reservation.total_paid = amount
        else:
            reservation.total_paid += amount
        
        if reservation.total_paid >= (reservation.total_amount or 0):
            reservation.payment_status = PaymentStatus.PAID
        else:
            reservation.payment_status = PaymentStatus.PARTIALLY_PAID
        
        self.session.flush()
        
        logger.info(f"Added payment {payment.id} of {amount} to reservation {reservation_id}")
        return payment
    
    def confirm_payment(
        self,
        payment_id: int,
        transaction_data: Optional[Dict] = None
    ) -> ReservationPayment:
        """
        Confirm a payment.
        
        Args:
            payment_id: Payment ID
            transaction_data: Optional transaction data
            
        Returns:
            Updated payment
        """
        payment = self.session.query(ReservationPayment).get(payment_id)
        if not payment:
            raise EntityNotFoundException("ReservationPayment", payment_id)
        
        payment.status = PaymentStatus.PAID
        payment.confirmed_at = datetime.utcnow()
        payment.transaction_data = transaction_data
        
        self.session.flush()
        
        logger.info(f"Confirmed payment {payment_id}")
        return payment
    
    def refund_payment(
        self,
        payment_id: int,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None
    ) -> ReservationPayment:
        """
        Refund a payment.
        
        Args:
            payment_id: Payment ID
            amount: Amount to refund (None for full)
            reason: Refund reason
            
        Returns:
            Updated payment
        """
        payment = self.session.query(ReservationPayment).get(payment_id)
        if not payment:
            raise EntityNotFoundException("ReservationPayment", payment_id)
        
        refund_amount = amount or payment.amount
        
        if refund_amount > payment.amount:
            raise ValidationException(
                "ReservationPayment",
                {"amount": ["Refund amount cannot exceed payment amount"]}
            )
        
        payment.refunded_amount = (payment.refunded_amount or 0) + refund_amount
        payment.refund_reason = reason
        payment.refunded_at = datetime.utcnow()
        
        if payment.refunded_amount >= payment.amount:
            payment.status = PaymentStatus.REFUNDED
        else:
            payment.status = PaymentStatus.PARTIALLY_REFUNDED
        
        self.session.flush()
        
        logger.info(f"Refunded {refund_amount} from payment {payment_id}")
        return payment
    
    # ========================================================================
    # Recurring Reservations
    # ========================================================================
    
    def create_recurring_reservation(
        self,
        user_id: int,
        spot_id: int,
        vehicle_id: int,
        frequency: RecurringFrequency,
        start_date: date,
        end_date: Optional[date],
        start_time: time,
        end_time: time,
        days_of_week: Optional[List[int]] = None,
        **kwargs
    ) -> RecurringReservation:
        """
        Create a recurring reservation pattern.
        
        Args:
            user_id: User ID
            spot_id: Spot ID
            vehicle_id: Vehicle ID
            frequency: Recurring frequency
            start_date: Start date
            end_date: Optional end date
            start_time: Daily start time
            end_time: Daily end time
            days_of_week: Days of week (0-6, Monday=0) for weekly frequency
            **kwargs: Additional attributes
            
        Returns:
            Created recurring reservation
        """
        # Validate pattern
        self._validate_recurring_pattern(
            frequency, start_date, end_date, start_time, end_time, days_of_week
        )
        
        # Generate pattern ID
        pattern_id = str(uuid4())
        
        recurring = RecurringReservation(
            pattern_id=pattern_id,
            user_id=user_id,
            spot_id=spot_id,
            vehicle_id=vehicle_id,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            days_of_week=days_of_week,
            is_active=True,
            **kwargs
        )
        
        self.session.add(recurring)
        self.session.flush()
        
        # Generate initial reservations
        self._generate_recurring_instances(recurring, days_ahead=90)
        
        logger.info(
            f"Created recurring reservation {recurring.id} for user {user_id} "
            f"at spot {spot_id} with frequency {frequency.value}"
        )
        
        return recurring
    
    def generate_recurring_instances(
        self,
        pattern_id: int,
        days_ahead: int = 30
    ) -> List[Reservation]:
        """
        Generate future instances of a recurring reservation.
        
        Args:
            pattern_id: Recurring reservation ID
            days_ahead: Number of days ahead to generate
            
        Returns:
            List of created reservations
        """
        recurring = self.session.query(RecurringReservation).get(pattern_id)
        if not recurring:
            raise EntityNotFoundException("RecurringReservation", pattern_id)
        
        return self._generate_recurring_instances(recurring, days_ahead)
    
    def pause_recurring_reservation(
        self,
        pattern_id: int,
        pause_until: Optional[date] = None
    ) -> RecurringReservation:
        """
        Pause a recurring reservation.
        
        Args:
            pattern_id: Recurring reservation ID
            pause_until: Date until which to pause
            
        Returns:
            Updated recurring reservation
        """
        recurring = self.session.query(RecurringReservation).get(pattern_id)
        if not recurring:
            raise EntityNotFoundException("RecurringReservation", pattern_id)
        
        recurring.is_active = False
        recurring.paused_at = datetime.utcnow()
        recurring.paused_until = pause_until
        
        self.session.flush()
        
        logger.info(f"Paused recurring reservation {pattern_id}")
        return recurring
    
    def resume_recurring_reservation(self, pattern_id: int) -> RecurringReservation:
        """
        Resume a paused recurring reservation.
        
        Args:
            pattern_id: Recurring reservation ID
            
        Returns:
            Updated recurring reservation
        """
        recurring = self.session.query(RecurringReservation).get(pattern_id)
        if not recurring:
            raise EntityNotFoundException("RecurringReservation", pattern_id)
        
        recurring.is_active = True
        recurring.paused_at = None
        recurring.paused_until = None
        recurring.resumed_at = datetime.utcnow()
        
        self.session.flush()
        
        logger.info(f"Resumed recurring reservation {pattern_id}")
        return recurring
    
    # ========================================================================
    # Waitlist Methods
    # ========================================================================
    
    def add_to_waitlist(
        self,
        user_id: int,
        spot_id: int,
        date_from: datetime,
        date_to: Optional[datetime] = None,
        preferences: Optional[Dict] = None
    ) -> Waitlist:
        """
        Add a user to the waitlist for a spot.
        
        Args:
            user_id: User ID
            spot_id: Spot ID
            date_from: Desired start time
            date_to: Optional desired end time
            preferences: Optional preferences
            
        Returns:
            Created waitlist entry
            
        Raises:
            WaitlistAlreadyExistsException: If user already on waitlist
        """
        # Check if already on waitlist
        existing = (
            self.session.query(Waitlist)
            .filter(
                Waitlist.user_id == user_id,
                Waitlist.spot_id == spot_id,
                Waitlist.date_from == date_from,
                Waitlist.status == WaitlistStatus.ACTIVE
            )
            .first()
        )
        
        if existing:
            raise WaitlistAlreadyExistsException(user_id, spot_id, date_from)
        
        waitlist = Waitlist(
            user_id=user_id,
            spot_id=spot_id,
            date_from=date_from,
            date_to=date_to,
            preferences=preferences or {},
            status=WaitlistStatus.ACTIVE,
            position=self._get_next_waitlist_position(spot_id, date_from),
            created_at=datetime.utcnow()
        )
        
        self.session.add(waitlist)
        self.session.flush()
        
        logger.info(f"Added user {user_id} to waitlist for spot {spot_id}")
        return waitlist
    
    def process_waitlist(
        self,
        spot_id: int,
        available_from: datetime,
        available_to: datetime
    ) -> List[Waitlist]:
        """
        Process waitlist when a spot becomes available.
        
        Args:
            spot_id: Spot ID
            available_from: Available from time
            available_to: Available to time
            
        Returns:
            List of waitlist entries that can be notified
        """
        # Get active waitlist entries for this spot
        waitlist_entries = (
            self.session.query(Waitlist)
            .filter(
                Waitlist.spot_id == spot_id,
                Waitlist.status == WaitlistStatus.ACTIVE,
                Waitlist.date_from <= available_to,
                or_(
                    Waitlist.date_to.is_(None),
                    Waitlist.date_to >= available_from
                )
            )
            .order_by(Waitlist.position)
            .all()
        )
        
        # Mark entries as notified
        for entry in waitlist_entries:
            entry.status = WaitlistStatus.NOTIFIED
            entry.notified_at = datetime.utcnow()
        
        self.session.flush()
        
        logger.info(f"Processed waitlist for spot {spot_id}, notified {len(waitlist_entries)} users")
        return waitlist_entries
    
    def remove_from_waitlist(self, waitlist_id: int) -> bool:
        """
        Remove an entry from waitlist.
        
        Args:
            waitlist_id: Waitlist entry ID
            
        Returns:
            True if removed
        """
        waitlist = self.session.query(Waitlist).get(waitlist_id)
        if not waitlist:
            return False
        
        waitlist.status = WaitlistStatus.CANCELLED
        waitlist.cancelled_at = datetime.utcnow()
        
        self.session.flush()
        
        logger.info(f"Removed waitlist entry {waitlist_id}")
        return True
    
    def convert_waitlist_to_reservation(
        self,
        waitlist_id: int,
        reservation_id: int
    ) -> Waitlist:
        """
        Mark a waitlist entry as converted to reservation.
        
        Args:
            waitlist_id: Waitlist entry ID
            reservation_id: Created reservation ID
            
        Returns:
            Updated waitlist entry
        """
        waitlist = self.session.query(Waitlist).get(waitlist_id)
        if not waitlist:
            raise EntityNotFoundException("Waitlist", waitlist_id)
        
        waitlist.status = WaitlistStatus.CONVERTED
        waitlist.converted_at = datetime.utcnow()
        waitlist.converted_to_reservation_id = reservation_id
        
        self.session.flush()
        
        logger.info(f"Converted waitlist {waitlist_id} to reservation {reservation_id}")
        return waitlist
    
    # ========================================================================
    # Reminder Methods
    # ========================================================================
    
    def get_reservations_needing_reminders(self) -> List[Reservation]:
        """
        Get reservations that need reminders sent.
        
        Returns:
            List of reservations needing reminders
        """
        now = datetime.utcnow()
        reminder_times = [
            now + timedelta(hours=24),  # 24 hours before
            now + timedelta(hours=2),    # 2 hours before
            now + timedelta(minutes=30)   # 30 minutes before
        ]
        
        return (
            self.session.query(Reservation)
            .filter(
                Reservation.status == ReservationStatus.CONFIRMED,
                Reservation.start_time.in_(reminder_times),
                ~Reservation.id.in_(
                    self.session.query(ReservationReminder.reservation_id)
                    .filter(ReservationReminder.sent_at.isnot(None))
                )
            )
            .all()
        )
    
    def mark_reminder_sent(
        self,
        reservation_id: int,
        reminder_type: str,
        channel: str
    ) -> ReservationReminder:
        """
        Mark a reminder as sent.
        
        Args:
            reservation_id: Reservation ID
            reminder_type: Type of reminder
            channel: Channel used
            
        Returns:
            Created reminder record
        """
        reminder = ReservationReminder(
            reservation_id=reservation_id,
            reminder_type=reminder_type,
            channel=channel,
            sent_at=datetime.utcnow()
        )
        
        self.session.add(reminder)
        self.session.flush()
        
        return reminder
    
    # ========================================================================
    # Note Methods
    # ========================================================================
    
    def add_note(
        self,
        reservation_id: int,
        user_id: int,
        note: str,
        is_private: bool = False
    ) -> ReservationNote:
        """
        Add a note to a reservation.
        
        Args:
            reservation_id: Reservation ID
            user_id: User adding the note
            note: Note content
            is_private: Whether note is private (staff only)
            
        Returns:
            Created note
        """
        reservation_note = ReservationNote(
            reservation_id=reservation_id,
            user_id=user_id,
            note=note,
            is_private=is_private,
            created_at=datetime.utcnow()
        )
        
        self.session.add(reservation_note)
        self.session.flush()
        
        logger.info(f"Added note to reservation {reservation_id}")
        return reservation_note
    
    def get_notes(
        self,
        reservation_id: int,
        include_private: bool = False
    ) -> List[ReservationNote]:
        """
        Get notes for a reservation.
        
        Args:
            reservation_id: Reservation ID
            include_private: Whether to include private notes
            
        Returns:
            List of notes
        """
        query = self.session.query(ReservationNote).filter(
            ReservationNote.reservation_id == reservation_id
        )
        
        if not include_private:
            query = query.filter(ReservationNote.is_private == False)
        
        return query.order_by(desc(ReservationNote.created_at)).all()
    
    # ========================================================================
    # Add-on Methods
    # ========================================================================
    
    def add_addon(
        self,
        reservation_id: int,
        addon_type: str,
        quantity: int = 1,
        unit_price: Optional[Decimal] = None,
        **kwargs
    ) -> ReservationAddon:
        """
        Add an add-on to a reservation.
        
        Args:
            reservation_id: Reservation ID
            addon_type: Type of add-on
            quantity: Quantity
            unit_price: Unit price
            **kwargs: Additional add-on data
            
        Returns:
            Created add-on
        """
        addon = ReservationAddon(
            reservation_id=reservation_id,
            addon_type=addon_type,
            quantity=quantity,
            unit_price=unit_price,
            total_price=unit_price * quantity if unit_price else None,
            addon_data=kwargs,
            created_at=datetime.utcnow()
        )
        
        self.session.add(addon)
        self.session.flush()
        
        # Update reservation total
        if addon.total_price:
            if not reservation.total_amount:
                reservation.total_amount = addon.total_price
            else:
                reservation.total_amount += addon.total_price
        
        self.session.flush()
        
        logger.info(f"Added add-on {addon_type} to reservation {reservation_id}")
        return addon
    
    # ========================================================================
    # History Methods
    # ========================================================================
    
    def get_reservation_history(
        self,
        reservation_id: int,
        limit: int = 100
    ) -> List[ReservationHistory]:
        """
        Get history for a reservation.
        
        Args:
            reservation_id: Reservation ID
            limit: Maximum entries to return
            
        Returns:
            List of history entries
        """
        return (
            self.session.query(ReservationHistory)
            .filter(ReservationHistory.reservation_id == reservation_id)
            .order_by(desc(ReservationHistory.created_at))
            .limit(limit)
            .all()
        )
    
    # ========================================================================
    # Analytics Methods
    # ========================================================================
    
    def get_occupancy_forecast(
        self,
        zone_id: Optional[int] = None,
        days_ahead: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get occupancy forecast for future days.
        
        Args:
            zone_id: Optional zone filter
            days_ahead: Number of days to forecast
            
        Returns:
            List of daily occupancy forecasts
        """
        today = datetime.utcnow().date()
        forecasts = []
        
        for day in range(days_ahead):
            forecast_date = today + timedelta(days=day)
            start_of_day = datetime.combine(forecast_date, time.min)
            end_of_day = datetime.combine(forecast_date, time.max)
            
            # Get reservations for this day
            reservations = self.get_reservations_in_range(
                start_of_day, end_of_day, zone_id=zone_id
            )
            
            # Get total spots in zone
            spots_query = self.session.query(ParkingSpot)
            if zone_id:
                spots_query = spots_query.filter(ParkingSpot.zone_id == zone_id)
            total_spots = spots_query.count()
            
            # Calculate hourly occupancy
            hourly_occupancy = {}
            for hour in range(24):
                hour_start = datetime.combine(forecast_date, time(hour, 0))
                hour_end = hour_start + timedelta(hours=1)
                
                occupied = sum(
                    1 for r in reservations
                    if r.start_time < hour_end and r.end_time > hour_start
                )
                
                hourly_occupancy[hour] = {
                    'occupied': occupied,
                    'available': total_spots - occupied,
                    'rate': round(occupied / total_spots * 100, 2) if total_spots > 0 else 0
                }
            
            forecasts.append({
                'date': forecast_date.isoformat(),
                'total_reservations': len(reservations),
                'total_spots': total_spots,
                'peak_hour': max(hourly_occupancy.items(), key=lambda x: x[1]['occupied'])[0],
                'hourly_occupancy': hourly_occupancy
            })
        
        return forecasts
    
    def get_revenue_forecast(
        self,
        zone_id: Optional[int] = None,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get revenue forecast for future days.
        
        Args:
            zone_id: Optional zone filter
            days_ahead: Number of days to forecast
            
        Returns:
            List of daily revenue forecasts
        """
        today = datetime.utcnow().date()
        forecasts = []
        
        for day in range(days_ahead):
            forecast_date = today + timedelta(days=day)
            start_of_day = datetime.combine(forecast_date, time.min)
            end_of_day = datetime.combine(forecast_date, time.max)
            
            # Get confirmed reservations for this day
            reservations = self.get_reservations_in_range(
                start_of_day, end_of_day,
                zone_id=zone_id,
                statuses=[ReservationStatus.CONFIRMED, ReservationStatus.CHECKED_IN]
            )
            
            # Calculate revenue
            total_revenue = sum(r.total_amount or 0 for r in reservations)
            estimated_revenue = sum(r.estimated_amount or r.total_amount or 0 for r in reservations)
            
            forecasts.append({
                'date': forecast_date.isoformat(),
                'reservation_count': len(reservations),
                'total_revenue': float(total_revenue),
                'estimated_revenue': float(estimated_revenue),
                'average_per_reservation': float(total_revenue / len(reservations)) if reservations else 0
            })
        
        return forecasts
    
    # ========================================================================
    # Maintenance and Cleanup
    # ========================================================================
    
    def process_expired_reservations(self) -> Dict[str, int]:
        """
        Process expired reservations (mark as no-show, etc.).
        
        Returns:
            Dictionary with counts of processed reservations
        """
        now = datetime.utcnow()
        results = {
            'marked_no_show': 0,
            'expired': 0,
            'cancelled': 0
        }
        
        # Mark no-shows
        no_show_candidates = self.get_no_show_candidates(self.no_show_minutes)
        for reservation in no_show_candidates:
            self.mark_no_show(reservation.id, "Auto no-show after grace period")
            results['marked_no_show'] += 1
        
        # Expire old pending reservations
        pending_expired = (
            self.session.query(Reservation)
            .filter(
                Reservation.status == ReservationStatus.PENDING,
                Reservation.created_at < now - timedelta(hours=24)
            )
            .update({
                'status': ReservationStatus.EXPIRED,
                'expired_at': now
            })
        )
        results['expired'] = pending_expired
        
        # Auto-cancel old confirmed reservations (older than 7 days past end)
        old_cancelled = (
            self.session.query(Reservation)
            .filter(
                Reservation.status == ReservationStatus.CONFIRMED,
                Reservation.end_time < now - timedelta(days=7)
            )
            .update({
                'status': ReservationStatus.CANCELLED,
                'cancelled_at': now,
                'cancellation_reason': 'Auto-cancelled - reservation too old'
            })
        )
        results['cancelled'] = old_cancelled
        
        self.session.flush()
        
        logger.info(f"Processed expired reservations: {results}")
        return results
    
    def cleanup_old_reservations(self, days: int = 365) -> int:
        """
        Delete old completed/cancelled reservations.
        
        Args:
            days: Age in days to delete
            
        Returns:
            Number of deleted reservations
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get IDs of reservations to delete
        old_reservations = (
            self.session.query(Reservation.id)
            .filter(
                Reservation.status.in_([
                    ReservationStatus.COMPLETED,
                    ReservationStatus.CANCELLED,
                    ReservationStatus.NO_SHOW,
                    ReservationStatus.EXPIRED,
                    ReservationStatus.REFUNDED
                ]),
                Reservation.end_time < cutoff
            )
            .all()
        )
        
        reservation_ids = [r.id for r in old_reservations]
        
        if not reservation_ids:
            return 0
        
        # Delete related records first
        self.session.query(ReservationHistory).filter(
            ReservationHistory.reservation_id.in_(reservation_ids)
        ).delete(synchronize_session=False)
        
        self.session.query(ReservationNote).filter(
            ReservationNote.reservation_id.in_(reservation_ids)
        ).delete(synchronize_session=False)
        
        self.session.query(ReservationReminder).filter(
            ReservationReminder.reservation_id.in_(reservation_ids)
        ).delete(synchronize_session=False)
        
        self.session.query(ReservationPayment).filter(
            ReservationPayment.reservation_id.in_(reservation_ids)
        ).delete(synchronize_session=False)
        
        self.session.query(ReservationAddon).filter(
            ReservationAddon.reservation_id.in_(reservation_ids)
        ).delete(synchronize_session=False)
        
        # Delete reservations
        deleted = (
            self.session.query(Reservation)
            .filter(Reservation.id.in_(reservation_ids))
            .delete(synchronize_session=False)
        )
        
        self.session.flush()
        
        logger.info(f"Cleaned up {deleted} old reservations")
        return deleted
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _validate_reservation_times(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> None:
        """Validate reservation times."""
        now = datetime.utcnow()
        
        if start_time >= end_time:
            raise ValidationException(
                "Reservation",
                {"end_time": ["End time must be after start time"]}
            )
        
        if start_time < now - timedelta(minutes=5):
            raise ValidationException(
                "Reservation",
                {"start_time": ["Start time cannot be in the past"]}
            )
        
        min_duration = timedelta(minutes=15)
        if end_time - start_time < min_duration:
            raise ValidationException(
                "Reservation",
                {"duration": ["Reservation must be at least 15 minutes"]}
            )
        
        max_duration = timedelta(days=30)
        if end_time - start_time > max_duration:
            raise ValidationException(
                "Reservation",
                {"duration": ["Reservation cannot exceed 30 days"]}
            )
    
    def _validate_recurring_pattern(
        self,
        frequency: RecurringFrequency,
        start_date: date,
        end_date: Optional[date],
        start_time: time,
        end_time: time,
        days_of_week: Optional[List[int]]
    ) -> None:
        """Validate recurring reservation pattern."""
        if start_date < date.today():
            raise ValidationException(
                "RecurringReservation",
                {"start_date": ["Start date cannot be in the past"]}
            )
        
        if end_date and end_date <= start_date:
            raise ValidationException(
                "RecurringReservation",
                {"end_date": ["End date must be after start date"]}
            )
        
        if start_time >= end_time:
            raise ValidationException(
                "RecurringReservation",
                {"end_time": ["End time must be after start time"]}
            )
        
        if frequency == RecurringFrequency.WEEKLY and not days_of_week:
            raise ValidationException(
                "RecurringReservation",
                {"days_of_week": ["Days of week required for weekly frequency"]}
            )
    
    def _check_availability_excluding_current(
        self,
        spot_id: int,
        start_time: datetime,
        end_time: datetime,
        exclude_reservation_id: int
    ) -> Tuple[bool, Optional[str]]:
        """Check availability excluding current reservation."""
        # Check for conflicting reservations
        conflict = (
            self.session.query(Reservation)
            .filter(
                Reservation.spot_id == spot_id,
                Reservation.id != exclude_reservation_id,
                Reservation.status.in_(ReservationStatus.get_active_statuses()),
                Reservation.start_time < end_time,
                Reservation.end_time > start_time
            )
            .first()
        )
        
        if conflict:
            return False, f"Conflicts with reservation {conflict.id}"
        
        return True, None
    
    def _generate_confirmation_code(self) -> str:
        """Generate a unique confirmation code."""
        while True:
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()
            
            # Check if unique
            existing = self.session.query(Reservation).filter(
                Reservation.confirmation_code == code
            ).first()
            
            if not existing:
                return code
    
    def _get_next_waitlist_position(
        self,
        spot_id: int,
        date_from: datetime
    ) -> int:
        """Get next position in waitlist."""
        max_position = (
            self.session.query(func.max(Waitlist.position))
            .filter(
                Waitlist.spot_id == spot_id,
                Waitlist.date_from == date_from,
                Waitlist.status == WaitlistStatus.ACTIVE
            )
            .scalar()
        )
        
        return (max_position or 0) + 1
    
    def _create_history_entry(
        self,
        reservation_id: int,
        status: ReservationStatus,
        data: Dict[str, Any]
    ) -> ReservationHistory:
        """Create a history entry."""
        history = ReservationHistory(
            reservation_id=reservation_id,
            status=status,
            data=data,
            created_at=datetime.utcnow()
        )
        
        self.session.add(history)
        self.session.flush()
        
        return history
    
    def _schedule_reminders(self, reservation: Reservation) -> None:
        """Schedule reminders for a reservation."""
        reminder_times = [
            (reservation.start_time - timedelta(hours=24), "24h_before"),
            (reservation.start_time - timedelta(hours=2), "2h_before"),
            (reservation.start_time - timedelta(minutes=30), "30m_before")
        ]
        
        for reminder_time, reminder_type in reminder_times:
            if reminder_time > datetime.utcnow():
                reminder = ReservationReminder(
                    reservation_id=reservation.id,
                    reminder_type=reminder_type,
                    scheduled_for=reminder_time
                )
                self.session.add(reminder)
        
        self.session.flush()
    
    def _generate_recurring_instances(
        self,
        recurring: RecurringReservation,
        days_ahead: int
    ) -> List[Reservation]:
        """Generate future instances of a recurring reservation."""
        if not recurring.is_active:
            return []
        
        today = datetime.utcnow().date()
        end_generation = today + timedelta(days=days_ahead)
        end_date = min(recurring.end_date or end_generation, end_generation)
        
        created_reservations = []
        current_date = max(recurring.start_date, today)
        
        while current_date <= end_date:
            # Check if this date should have a reservation
            if self._should_generate_for_date(recurring, current_date):
                start_datetime = datetime.combine(current_date, recurring.start_time)
                end_datetime = datetime.combine(current_date, recurring.end_time)
                
                # Check if start time is in the future
                if start_datetime > datetime.utcnow():
                    try:
                        # Check availability
                        is_available, _ = self.spot_repository.check_spot_availability(
                            recurring.spot_id,
                            start_datetime,
                            end_datetime
                        )
                        
                        if is_available:
                            # Create reservation
                            reservation = self.create_reservation(
                                user_id=recurring.user_id,
                                spot_id=recurring.spot_id,
                                vehicle_id=recurring.vehicle_id,
                                start_time=start_datetime,
                                end_time=end_datetime,
                                reservation_type=ReservationType.RECURRING,
                                recurring_pattern_id=recurring.id
                            )
                            
                            created_reservations.append(reservation)
                    except Exception as e:
                        logger.error(f"Failed to create recurring instance for {current_date}: {e}")
            
            # Move to next date based on frequency
            current_date = self._next_recurring_date(recurring, current_date)
        
        return created_reservations
    
    def _should_generate_for_date(
        self,
        recurring: RecurringReservation,
        date: date
    ) -> bool:
        """Check if a reservation should be generated for a date."""
        if recurring.frequency == RecurringFrequency.DAILY:
            return True
        elif recurring.frequency == RecurringFrequency.WEEKLY:
            return recurring.days_of_week and date.weekday() in recurring.days_of_week
        elif recurring.frequency == RecurringFrequency.WEEKDAYS:
            return date.weekday() < 5
        elif recurring.frequency == RecurringFrequency.WEEKENDS:
            return date.weekday() >= 5
        elif recurring.frequency == RecurringFrequency.MONTHLY:
            # Generate on the same day of month
            return date.day == recurring.start_date.day
        return False
    
    def _next_recurring_date(
        self,
        recurring: RecurringReservation,
        current_date: date
    ) -> date:
        """Get the next date for a recurring reservation."""
        if recurring.frequency == RecurringFrequency.DAILY:
            return current_date + timedelta(days=1)
        elif recurring.frequency in [RecurringFrequency.WEEKLY, RecurringFrequency.WEEKDAYS, RecurringFrequency.WEEKENDS]:
            return current_date + timedelta(days=1)
        elif recurring.frequency == RecurringFrequency.MONTHLY:
            # Move to next month
            year = current_date.year
            month = current_date.month + 1
            if month > 12:
                month = 1
                year += 1
            # Handle different month lengths
            day = min(current_date.day, self._days_in_month(year, month))
            return date(year, month, day)
        return current_date + timedelta(days=1)
    
    def _days_in_month(self, year: int, month: int) -> int:
        """Get number of days in a month."""
        if month == 2:
            if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                return 29
            return 28
        if month in [4, 6, 9, 11]:
            return 30
        return 31


# ============================================================================
# Recurring Reservation Repository
# ============================================================================

class RecurringReservationRepository(BaseRepository[RecurringReservation, int]):
    """Repository for RecurringReservation entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, RecurringReservation)
    
    def get_by_user(
        self,
        user_id: int,
        active_only: bool = True
    ) -> List[RecurringReservation]:
        """Get recurring reservations for a user."""
        query = self.session.query(RecurringReservation).filter(
            RecurringReservation.user_id == user_id
        )
        
        if active_only:
            query = query.filter(RecurringReservation.is_active == True)
        
        return query.all()
    
    def get_by_spot(
        self,
        spot_id: int,
        active_only: bool = True
    ) -> List[RecurringReservation]:
        """Get recurring reservations for a spot."""
        query = self.session.query(RecurringReservation).filter(
            RecurringReservation.spot_id == spot_id
        )
        
        if active_only:
            query = query.filter(RecurringReservation.is_active == True)
        
        return query.all()
    
    def get_active_patterns(self) -> List[RecurringReservation]:
        """Get all active recurring patterns."""
        return (
            self.session.query(RecurringReservation)
            .filter(RecurringReservation.is_active == True)
            .all()
        )
    
    def get_patterns_needing_generation(self, days_ahead: int = 7) -> List[RecurringReservation]:
        """
        Get patterns that need future instances generated.
        
        Args:
            days_ahead: How many days ahead to check
            
        Returns:
            List of patterns needing generation
        """
        future_date = datetime.utcnow().date() + timedelta(days=days_ahead)
        
        return (
            self.session.query(RecurringReservation)
            .filter(
                RecurringReservation.is_active == True,
                or_(
                    RecurringReservation.end_date.is_(None),
                    RecurringReservation.end_date >= datetime.utcnow().date()
                )
            )
            .all()
        )


# ============================================================================
# Waitlist Repository
# ============================================================================

class WaitlistRepository(BaseRepository[Waitlist, int]):
    """Repository for Waitlist entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, Waitlist)
    
    def get_active_waitlist(
        self,
        spot_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> List[Waitlist]:
        """Get active waitlist entries."""
        query = self.session.query(Waitlist).filter(
            Waitlist.status == WaitlistStatus.ACTIVE
        )
        
        if spot_id:
            query = query.filter(Waitlist.spot_id == spot_id)
        
        if user_id:
            query = query.filter(Waitlist.user_id == user_id)
        
        return query.order_by(Waitlist.position).all()
    
    def get_waitlist_by_spot_and_time(
        self,
        spot_id: int,
        date_from: datetime
    ) -> List[Waitlist]:
        """Get waitlist for a specific spot and time."""
        return (
            self.session.query(Waitlist)
            .filter(
                Waitlist.spot_id == spot_id,
                Waitlist.date_from == date_from,
                Waitlist.status == WaitlistStatus.ACTIVE
            )
            .order_by(Waitlist.position)
            .all()
        )
    
    def get_user_waitlist_history(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Waitlist]:
        """Get waitlist history for a user."""
        return (
            self.session.query(Waitlist)
            .filter(Waitlist.user_id == user_id)
            .order_by(desc(Waitlist.created_at))
            .limit(limit)
            .all()
        )
    
    def cleanup_expired_waitlist(self, days: int = 30) -> int:
        """Delete old waitlist entries."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = (
            self.session.query(Waitlist)
            .filter(Waitlist.created_at <= cutoff)
            .delete()
        )
        
        self.session.flush()
        return result


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main Repository
    'ReservationRepository',
    'RecurringReservationRepository',
    'WaitlistRepository',
    
    # Exceptions
    'ReservationNotFoundException',
    'ReservationConflictException',
    'InvalidReservationStateException',
    'CheckInWindowException',
    'CheckOutWindowException',
    'MaxExtensionsExceededException',
    'WaitlistAlreadyExistsException',
    'NoShowException',
]