"""Reservation service for business logic."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from ..models.reservation import Reservation
from ..models.parking_spot import ParkingSpot
from ..models.user import User
from ..enums import ReservationStatus, ParkingSpotType
from ..exceptions import (
    ReservationError,
    ResourceNotFoundError,
    ResourceConflictError,
    ValidationError
)
from ..constants.config import Config
from ..utils.datetime_utils import is_overlapping, calculate_duration_hours


class ReservationService:
    """Service for managing reservations."""
    
    def __init__(self, db_session, cache_client=None):
        self.db = db_session
        self.cache = cache_client
    
    async def create_reservation(
        self,
        user_id: int,
        spot_id: int,
        vehicle_id: int,
        license_plate: str,
        start_time: datetime,
        end_time: datetime,
        vehicle_type: str,
        notes: Optional[str] = None
    ) -> Reservation:
        """Create a new reservation."""
        # Validate inputs
        await self._validate_reservation_inputs(
            user_id, spot_id, vehicle_id, start_time, end_time
        )
        
        # Check spot availability
        if not await self._is_spot_available(spot_id, start_time, end_time):
            raise ResourceConflictError(
                "parking_spot",
                {"message": "Spot is not available for the selected time period"}
            )
        
        # Calculate total amount
        total_amount = await self._calculate_price(
            spot_id, start_time, end_time, vehicle_type
        )
        
        # Create reservation
        reservation = Reservation(
            user_id=user_id,
            spot_id=spot_id,
            vehicle_id=vehicle_id,
            license_plate=license_plate,
            start_time=start_time,
            end_time=end_time,
            vehicle_type=vehicle_type,
            total_amount=total_amount,
            status=ReservationStatus.PENDING,
            notes=notes
        )
        
        # Save to database
        self.db.add(reservation)
        await self.db.commit()
        await self.db.refresh(reservation)
        
        # Invalidate cache
        await self._invalidate_reservation_cache(user_id, spot_id)
        
        return reservation
    
    async def get_reservation(self, reservation_id: int) -> Reservation:
        """Get reservation by ID."""
        # Try cache first
        if self.cache:
            cached = await self.cache.get(f"reservation:{reservation_id}")
            if cached:
                return Reservation.from_dict(cached)
        
        # Get from database
        reservation = await self.db.query(Reservation).filter(
            Reservation.reservation_id == reservation_id
        ).first()
        
        if not reservation:
            raise ResourceNotFoundError("reservation", reservation_id)
        
        # Cache result
        if self.cache:
            await self.cache.set(
                f"reservation:{reservation_id}",
                reservation.to_dict(),
                ex=Config.CACHE_TTL["reservation"]
            )
        
        return reservation
    
    async def get_user_reservations(
        self,
        user_id: int,
        status: Optional[ReservationStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Reservation], int]:
        """Get reservations for a user."""
        query = self.db.query(Reservation).filter(Reservation.user_id == user_id)
        
        if status:
            query = query.filter(Reservation.status == status)
        
        total = await query.count()
        reservations = await query.order_by(
            Reservation.start_time.desc()
        ).limit(limit).offset(offset).all()
        
        return reservations, total
    
    async def update_reservation(
        self,
        reservation_id: int,
        user_id: int,
        **updates
    ) -> Reservation:
        """Update an existing reservation."""
        reservation = await self.get_reservation(reservation_id)
        
        # Check if user owns the reservation
        if reservation.user_id != user_id:
            raise ReservationError(
                "AUTHORIZATION_ERROR",
                "You don't have permission to update this reservation"
            )
        
        # Check if reservation can be updated
        if not reservation.is_active:
            raise ReservationError(
                "RESERVATION_CANCELLATION_ERROR",
                "Cannot update a non-active reservation"
            )
        
        # Update fields
        for key, value in updates.items():
            if hasattr(reservation, key) and value is not None:
                setattr(reservation, key, value)
        
        reservation.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(reservation)
        
        # Invalidate cache
        await self._invalidate_reservation_cache(reservation.user_id, reservation.spot_id)
        
        return reservation
    
    async def cancel_reservation(
        self,
        reservation_id: int,
        user_id: int,
        reason: str
    ) -> Reservation:
        """Cancel a reservation."""
        reservation = await self.get_reservation(reservation_id)
        
        # Check if user owns the reservation
        if reservation.user_id != user_id:
            # Check if user is admin
            user = await self.db.query(User).filter(User.user_id == user_id).first()
            if not user or not user.is_admin:
                raise ReservationError(
                    "AUTHORIZATION_ERROR",
                    "You don't have permission to cancel this reservation"
                )
        
        # Check if reservation can be cancelled
        if not reservation.can_cancel:
            raise ReservationError(
                "RESERVATION_CANCELLATION_ERROR",
                "This reservation cannot be cancelled"
            )
        
        # Check cancellation window
        now = datetime.utcnow()
        cancellation_deadline = reservation.start_time - timedelta(
            hours=Config.RESERVATION_CANCELLATION_WINDOW_HOURS
        )
        
        if now > cancellation_deadline and not user.is_admin:
            raise ReservationError(
                "RESERVATION_CANCELLATION_ERROR",
                f"Reservations must be cancelled at least {Config.RESERVATION_CANCELLATION_WINDOW_HOURS} hours before start time"
            )
        
        reservation.cancel(reason)
        
        await self.db.commit()
        await self.db.refresh(reservation)
        
        # Invalidate cache
        await self._invalidate_reservation_cache(reservation.user_id, reservation.spot_id)
        
        return reservation
    
    async def check_in(self, reservation_id: int, user_id: int) -> Reservation:
        """Check in to a reservation."""
        reservation = await self.get_reservation(reservation_id)
        
        # Check if user owns the reservation
        if reservation.user_id != user_id:
            raise ReservationError(
                "AUTHORIZATION_ERROR",
                "You don't have permission to check in to this reservation"
            )
        
        # Check if reservation can be checked in
        if not reservation.can_check_in:
            raise ReservationError(
                "RESERVATION_CANCELLATION_ERROR",
                "Cannot check in to this reservation at this time"
            )
        
        # Check grace period
        now = datetime.utcnow()
        grace_deadline = reservation.start_time + timedelta(
            minutes=Config.RESERVATION_GRACE_PERIOD_MINUTES
        )
        
        if now > grace_deadline:
            reservation.status = ReservationStatus.EXPIRED
            await self.db.commit()
            raise ReservationError(
                "RESERVATION_EXPIRED",
                f"Reservation expired after {Config.RESERVATION_GRACE_PERIOD_MINUTES} minutes grace period"
            )
        
        reservation.check_in()
        
        # Update parking spot
        spot = await self.db.query(ParkingSpot).filter(
            ParkingSpot.spot_id == reservation.spot_id
        ).first()
        if spot:
            spot.occupy(reservation.vehicle_id, reservation.reservation_id)
        
        await self.db.commit()
        await self.db.refresh(reservation)
        
        # Invalidate cache
        await self._invalidate_reservation_cache(reservation.user_id, reservation.spot_id)
        
        return reservation
    
    async def check_out(self, reservation_id: int, user_id: int) -> Reservation:
        """Check out from a reservation."""
        reservation = await self.get_reservation(reservation_id)
        
        # Check if user owns the reservation
        if reservation.user_id != user_id:
            raise ReservationError(
                "AUTHORIZATION_ERROR",
                "You don't have permission to check out from this reservation"
            )
        
        # Check if reservation can be checked out
        if not reservation.can_check_out:
            raise ReservationError(
                "RESERVATION_CANCELLATION_ERROR",
                "Cannot check out from this reservation"
            )
        
        # Calculate actual duration and adjust price if needed
        actual_duration = calculate_duration_hours(
            reservation.actual_check_in or reservation.start_time,
            datetime.utcnow()
        )
        
        # Adjust total amount based on actual duration if different from planned
        if abs(actual_duration - reservation.duration_hours) > 0.5:  # More than 30 min difference
            spot = await self.db.query(ParkingSpot).filter(
                ParkingSpot.spot_id == reservation.spot_id
            ).first()
            
            if spot:
                adjusted_amount = actual_duration * (spot.hourly_rate or Config.HOURLY_RATE)
                reservation.total_amount = max(reservation.total_amount, adjusted_amount)
        
        reservation.check_out()
        
        # Update parking spot
        spot = await self.db.query(ParkingSpot).filter(
            ParkingSpot.spot_id == reservation.spot_id
        ).first()
        if spot:
            spot.vacate()
        
        await self.db.commit()
        await self.db.refresh(reservation)
        
        # Invalidate cache
        await self._invalidate_reservation_cache(reservation.user_id, reservation.spot_id)
        
        return reservation
    
    async def _validate_reservation_inputs(
        self,
        user_id: int,
        spot_id: int,
        vehicle_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> None:
        """Validate reservation inputs."""
        # Validate user exists
        user = await self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise ResourceNotFoundError("user", user_id)
        
        # Validate spot exists
        spot = await self.db.query(ParkingSpot).filter(
            ParkingSpot.spot_id == spot_id
        ).first()
        if not spot:
            raise ResourceNotFoundError("parking_spot", spot_id)
        
        # Validate time range
        now = datetime.utcnow()
        
        if start_time < now + timedelta(hours=Config.RESERVATION_MIN_ADVANCE_HOURS):
            raise ValidationError({
                "start_time": f"Reservations must be made at least {Config.RESERVATION_MIN_ADVANCE_HOURS} hours in advance"
            })
        
        if start_time > now + timedelta(days=Config.RESERVATION_MAX_ADVANCE_DAYS):
            raise ValidationError({
                "start_time": f"Reservations cannot be made more than {Config.RESERVATION_MAX_ADVANCE_DAYS} days in advance"
            })
        
        duration = calculate_duration_hours(start_time, end_time)
        if duration > Config.RESERVATION_MAX_DURATION_HOURS:
            raise ValidationError({
                "end_time": f"Reservation duration cannot exceed {Config.RESERVATION_MAX_DURATION_HOURS} hours"
            })
    
    async def _is_spot_available(
        self,
        spot_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> bool:
        """Check if parking spot is available for given time period."""
        # Check for overlapping reservations
        overlapping = await self.db.query(Reservation).filter(
            Reservation.spot_id == spot_id,
            Reservation.status.in_([
                ReservationStatus.PENDING,
                ReservationStatus.CONFIRMED,
                ReservationStatus.CHECKED_IN
            ]),
            Reservation.start_time < end_time,
            Reservation.end_time > start_time
        ).first()
        
        return overlapping is None
    
    async def _calculate_price(
        self,
        spot_id: int,
        start_time: datetime,
        end_time: datetime,
        vehicle_type: str
    ) -> float:
        """Calculate price for reservation."""
        spot = await self.db.query(ParkingSpot).filter(
            ParkingSpot.spot_id == spot_id
        ).first()
        
        if not spot:
            raise ResourceNotFoundError("parking_spot", spot_id)
        
        duration = calculate_duration_hours(start_time, end_time)
        
        # Get base rate
        hourly_rate = spot.hourly_rate or Config.HOURLY_RATE
        
        # Apply spot type multiplier
        multiplier = Config.SPOT_TYPE_PRICE_MULTIPLIER.get(
            spot.spot_type.value if spot.spot_type else "standard",
            1.0
        )
        
        # Calculate total
        total = duration * hourly_rate * multiplier
        
        # Apply daily max if applicable
        daily_max = Config.DAILY_MAX_RATE * multiplier
        if total > daily_max:
            total = daily_max
        
        return round(total, 2)
    
    async def _invalidate_reservation_cache(self, user_id: int, spot_id: int) -> None:
        """Invalidate reservation caches."""
        if self.cache:
            await self.cache.delete_pattern(f"user:{user_id}:reservations:*")
            await self.cache.delete_pattern(f"spot:{spot_id}:availability:*")