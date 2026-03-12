"""
Reservation management endpoints.
"""

from typing import Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.deps import get_current_user, get_current_active_superuser
from ....crud import crud_reservation, crud_parking_spot, crud_payment
from ....models.user import User
from ....schemas.reservation import (
    ReservationResponse,
    ReservationCreate,
    ReservationUpdate,
    ReservationExtend,
    ReservationCheckIn,
    ReservationCheckOut,
    ReservationQRCode
)
from ....schemas.payment import PaymentCreate
from ....db.session import get_db
from ....services.audit import audit_log
from ....services.qr_code import generate_qr_code
from ....services.notification import send_reservation_notification
from ....utils.pagination import PaginatedResponse, paginate
from ....utils.cache import cache_response, invalidate_cache
from ....utils.exceptions import (
    ReservationNotFoundException,
    ParkingSpotNotFoundException,
    SpotNotAvailableException,
    InvalidReservationStatusException
)

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("/", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    reservation_in: ReservationCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a new parking reservation.
    """
    # Validate parking spot exists
    spot = await crud_parking_spot.get(db, id=reservation_in.spot_id)
    if not spot:
        raise ParkingSpotNotFoundException()
    
    # Check spot availability
    is_available = await crud_parking_spot.check_availability(
        db,
        spot_id=reservation_in.spot_id,
        start_time=reservation_in.start_time,
        end_time=reservation_in.end_time
    )
    if not is_available:
        raise SpotNotAvailableException()
    
    # Calculate price
    duration_hours = (reservation_in.end_time - reservation_in.start_time).total_seconds() / 3600
    total_price = spot.price_per_hour * duration_hours
    
    # Create reservation
    reservation = await crud_reservation.create_with_user(
        db,
        obj_in=reservation_in,
        user_id=current_user.id,
        total_price=total_price
    )
    
    # Generate QR code
    qr_code = await generate_qr_code(str(reservation.id))
    reservation = await crud_reservation.update_qr_code(db, reservation_id=reservation.id, qr_code=qr_code)
    
    # Send notifications
    await send_reservation_notification(
        user=current_user,
        reservation=reservation,
        notification_type="confirmation"
    )
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="CREATE_RESERVATION",
        resource="reservation",
        resource_id=reservation.id,
        details={
            "spot_id": reservation.spot_id,
            "start_time": reservation.start_time.isoformat(),
            "end_time": reservation.end_time.isoformat(),
            "total_price": total_price
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    # Invalidate cache
    await invalidate_cache(f"user:{current_user.id}:reservations")
    await invalidate_cache(f"parking:availability")
    
    return reservation


@router.get("/", response_model=PaginatedResponse[ReservationResponse])
@cache_response(expire=60)
async def read_reservations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, regex="^(pending|confirmed|active|completed|cancelled)$"),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Any:
    """
    Get reservations for current user.
    """
    reservations = await crud_reservation.get_multi_by_user(
        db,
        user_id=current_user.id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        skip=(page - 1) * size,
        limit=size
    )
    
    total = await crud_reservation.count_by_user(
        db,
        user_id=current_user.id,
        status=status,
        from_date=from_date,
        to_date=to_date
    )
    
    return paginate(reservations, total, page, size)


@router.get("/{reservation_id}", response_model=ReservationResponse)
async def read_reservation(
    reservation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get reservation by ID.
    """
    reservation = await crud_reservation.get(db, id=reservation_id)
    if not reservation or (reservation.user_id != current_user.id and not current_user.is_superuser):
        raise ReservationNotFoundException()
    return reservation


@router.put("/{reservation_id}", response_model=ReservationResponse)
async def update_reservation(
    reservation_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    reservation_in: ReservationUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update a reservation.
    """
    reservation = await crud_reservation.get(db, id=reservation_id)
    if not reservation or reservation.user_id != current_user.id:
        raise ReservationNotFoundException()
    
    # Check if reservation can be modified
    if reservation.status not in ["pending", "confirmed"]:
        raise InvalidReservationStatusException(
            detail="Only pending or confirmed reservations can be modified"
        )
    
    # Check if modification is allowed (e.g., within time window)
    if reservation.start_time - datetime.now() < timedelta(hours=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify reservation within 1 hour of start time"
        )
    
    # Update reservation
    reservation = await crud_reservation.update(db, db_obj=reservation, obj_in=reservation_in)
    
    # Recalculate price if times changed
    if reservation_in.start_time or reservation_in.end_time:
        spot = await crud_parking_spot.get(db, id=reservation.spot_id)
        duration_hours = (reservation.end_time - reservation.start_time).total_seconds() / 3600
        new_price = spot.price_per_hour * duration_hours
        reservation = await crud_reservation.update_price(db, reservation_id=reservation.id, new_price=new_price)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="UPDATE_RESERVATION",
        resource="reservation",
        resource_id=reservation_id,
        details={"changes": reservation_in.dict(exclude_unset=True)},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    # Invalidate cache
    await invalidate_cache(f"user:{current_user.id}:reservations")
    await invalidate_cache(f"reservation:{reservation_id}")
    
    return reservation


@router.delete("/{reservation_id}", response_model=dict)
async def cancel_reservation(
    reservation_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    current_user: User = Depends(get_current_user),
    reason: Optional[str] = Query(None),
) -> Any:
    """
    Cancel a reservation.
    """
    reservation = await crud_reservation.get(db, id=reservation_id)
    if not reservation or (reservation.user_id != current_user.id and not current_user.is_superuser):
        raise ReservationNotFoundException()
    
    # Check if reservation can be cancelled
    if reservation.status in ["completed", "cancelled"]:
        raise InvalidReservationStatusException(
            detail="Reservation is already completed or cancelled"
        )
    
    # Calculate cancellation fee if applicable
    cancellation_fee = 0
    time_until_start = (reservation.start_time - datetime.now()).total_seconds() / 3600
    
    if time_until_start < 1:  # Less than 1 hour
        cancellation_fee = reservation.total_price * 0.5  # 50% fee
    elif time_until_start < 24:  # Less than 24 hours
        cancellation_fee = reservation.total_price * 0.25  # 25% fee
    
    # Cancel reservation
    reservation = await crud_reservation.cancel(
        db,
        reservation_id=reservation.id,
        reason=reason,
        cancellation_fee=cancellation_fee
    )
    
    # Process refund if payment was made
    if reservation.payments and cancellation_fee < reservation.total_price:
        refund_amount = reservation.total_price - cancellation_fee
        await crud_payment.create_refund(
            db,
            payment_id=reservation.payments[0].id,
            amount=refund_amount,
            reason="Reservation cancelled"
        )
    
    # Send cancellation notification
    await send_reservation_notification(
        user=current_user,
        reservation=reservation,
        notification_type="cancellation"
    )
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="CANCEL_RESERVATION",
        resource="reservation",
        resource_id=reservation_id,
        details={"reason": reason, "cancellation_fee": cancellation_fee},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    # Invalidate cache
    await invalidate_cache(f"user:{current_user.id}:reservations")
    await invalidate_cache(f"reservation:{reservation_id}")
    await invalidate_cache(f"parking:availability")
    
    return {
        "message": "Reservation cancelled successfully",
        "cancellation_fee": cancellation_fee,
        "refund_amount": reservation.total_price - cancellation_fee if cancellation_fee < reservation.total_price else 0
    }


@router.post("/{reservation_id}/extend", response_model=ReservationResponse)
async def extend_reservation(
    reservation_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    extend_data: ReservationExtend,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Extend an active reservation.
    """
    reservation = await crud_reservation.get(db, id=reservation_id)
    if not reservation or reservation.user_id != current_user.id:
        raise ReservationNotFoundException()
    
    # Check if reservation is active
    if reservation.status != "active":
        raise InvalidReservationStatusException(
            detail="Only active reservations can be extended"
        )
    
    # Check if new end time is valid
    if extend_data.new_end_time <= reservation.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New end time must be after current end time"
        )
    
    # Check spot availability for extension
    is_available = await crud_parking_spot.check_availability(
        db,
        spot_id=reservation.spot_id,
        start_time=reservation.end_time,
        end_time=extend_data.new_end_time,
        exclude_reservation_id=reservation.id
    )
    if not is_available:
        raise SpotNotAvailableException(detail="Spot not available for the requested extension period")
    
    # Calculate additional charge
    spot = await crud_parking_spot.get(db, id=reservation.spot_id)
    extension_hours = (extend_data.new_end_time - reservation.end_time).total_seconds() / 3600
    additional_charge = spot.price_per_hour * extension_hours
    
    # Update reservation
    reservation = await crud_reservation.extend(
        db,
        reservation_id=reservation.id,
        new_end_time=extend_data.new_end_time,
        additional_charge=additional_charge
    )
    
    # Process additional payment
    if additional_charge > 0:
        await crud_payment.create(
            db,
            obj_in=PaymentCreate(
                reservation_id=reservation.id,
                amount=additional_charge,
                payment_method="same_as_original"
            )
        )
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="EXTEND_RESERVATION",
        resource="reservation",
        resource_id=reservation_id,
        details={
            "new_end_time": extend_data.new_end_time.isoformat(),
            "additional_charge": additional_charge
        },
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return reservation


@router.post("/{reservation_id}/checkin", response_model=ReservationResponse)
async def check_in(
    reservation_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    checkin_data: Optional[ReservationCheckIn] = None,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Check in to a reservation.
    """
    reservation = await crud_reservation.get(db, id=reservation_id)
    if not reservation or reservation.user_id != current_user.id:
        raise ReservationNotFoundException()
    
    # Check if reservation can be checked in
    if reservation.status != "confirmed":
        raise InvalidReservationStatusException(
            detail="Only confirmed reservations can be checked in"
        )
    
    # Check if within check-in window
    time_until_start = (reservation.start_time - datetime.now()).total_seconds() / 3600
    if time_until_start > 1:  # More than 1 hour early
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too early for check-in"
        )
    
    if datetime.now() > reservation.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reservation has expired"
        )
    
    # Verify QR code if provided
    if checkin_data and checkin_data.qr_code_data:
        # Verify QR code
        pass
    
    # Check in
    reservation = await crud_reservation.check_in(db, reservation_id=reservation.id)
    
    # Update spot status
    await crud_parking_spot.update_status(db, spot_id=reservation.spot_id, status="occupied")
    
    # Send notification
    await send_reservation_notification(
        user=current_user,
        reservation=reservation,
        notification_type="checkin"
    )
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="CHECK_IN",
        resource="reservation",
        resource_id=reservation_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return reservation


@router.post("/{reservation_id}/checkout", response_model=ReservationResponse)
async def check_out(
    reservation_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Check out from a reservation.
    """
    reservation = await crud_reservation.get(db, id=reservation_id)
    if not reservation or reservation.user_id != current_user.id:
        raise ReservationNotFoundException()
    
    # Check if reservation is active
    if reservation.status != "active":
        raise InvalidReservationStatusException(
            detail="Only active reservations can be checked out"
        )
    
    # Calculate actual duration and overage charges
    actual_duration = (datetime.now() - reservation.check_in_time).total_seconds() / 3600
    reserved_duration = (reservation.end_time - reservation.start_time).total_seconds() / 3600
    
    overage_charge = 0
    if actual_duration > reserved_duration:
        spot = await crud_parking_spot.get(db, id=reservation.spot_id)
        overage_hours = actual_duration - reserved_duration
        overage_charge = spot.price_per_hour * overage_hours * 1.5  # 50% premium for overage
    
    # Check out
    reservation = await crud_reservation.check_out(
        db,
        reservation_id=reservation.id,
        overage_charge=overage_charge
    )
    
    # Update spot status
    await crud_parking_spot.update_status(db, spot_id=reservation.spot_id, status="available")
    
    # Process overage payment if any
    if overage_charge > 0:
        await crud_payment.create(
            db,
            obj_in=PaymentCreate(
                reservation_id=reservation.id,
                amount=overage_charge,
                payment_method="same_as_original",
                description="Overage charges"
            )
        )
    
    # Send notification
    await send_reservation_notification(
        user=current_user,
        reservation=reservation,
        notification_type="checkout"
    )
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="CHECK_OUT",
        resource="reservation",
        resource_id=reservation_id,
        details={"actual_duration": actual_duration, "overage_charge": overage_charge},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return reservation


@router.get("/{reservation_id}/qr", response_model=ReservationQRCode)
async def get_qr_code(
    reservation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    format: str = Query("json", regex="^(json|png|svg)$"),
    size: int = Query(200, ge=100, le=500),
) -> Any:
    """
    Get QR code for a reservation.
    """
    reservation = await crud_reservation.get(db, id=reservation_id)
    if not reservation or (reservation.user_id != current_user.id and not current_user.is_superuser):
        raise ReservationNotFoundException()
    
    if not reservation.qr_code:
        # Generate new QR code
        qr_code = await generate_qr_code(str(reservation.id), size=size)
        reservation = await crud_reservation.update_qr_code(db, reservation_id=reservation.id, qr_code=qr_code)
    else:
        qr_code = reservation.qr_code
    
    if format != "json":
        # Return image data
        return Response(content=qr_code, media_type=f"image/{format}")
    
    return ReservationQRCode(
        qr_code=qr_code,
        reservation_id=reservation.id,
        valid_until=reservation.end_time
    )


# Admin endpoints
@router.get("/admin/all", response_model=PaginatedResponse[ReservationResponse])
async def get_all_reservations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    user_id: Optional[str] = None,
    spot_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Any:
    """
    Get all reservations with filters (admin only).
    """
    reservations = await crud_reservation.get_multi(
        db,
        status=status,
        from_date=from_date,
        to_date=to_date,
        user_id=user_id,
        spot_id=spot_id,
        skip=(page - 1) * size,
        limit=size
    )
    
    total = await crud_reservation.count(
        db,
        status=status,
        from_date=from_date,
        to_date=to_date,
        user_id=user_id,
        spot_id=spot_id
    )
    
    return paginate(reservations, total, page, size)


@router.post("/admin/{reservation_id}/force-checkout", response_model=ReservationResponse)
async def force_checkout(
    reservation_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Force checkout a reservation (admin only).
    """
    reservation = await crud_reservation.get(db, id=reservation_id)
    if not reservation:
        raise ReservationNotFoundException()
    
    reservation = await crud_reservation.check_out(db, reservation_id=reservation.id, forced=True)
    
    # Update spot status
    await crud_parking_spot.update_status(db, spot_id=reservation.spot_id, status="available")
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="FORCE_CHECKOUT",
        resource="reservation",
        resource_id=reservation_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return reservation