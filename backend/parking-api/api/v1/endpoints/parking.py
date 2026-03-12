"""
Parking spot management endpoints.
"""

from typing import List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.deps import get_current_user, get_current_active_superuser
from ....crud import crud_parking_spot, crud_reservation
from ....models.user import User
from ....schemas.parking import (
    ParkingSpotResponse,
    ParkingSpotCreate,
    ParkingSpotUpdate,
    ParkingSpotStatus,
    ParkingSpotAvailability,
    ParkingSpotMap,
    ParkingSpotFeatures
)
from ....schemas.reservation import ReservationCreate
from ....db.session import get_db
from ....services.audit import audit_log
from ....utils.pagination import PaginatedResponse, paginate
from ....utils.cache import cache_response, invalidate_cache
from ....utils.exceptions import ParkingSpotNotFoundException, SpotNotAvailableException

router = APIRouter(prefix="/parking", tags=["parking"])


@router.get("/spots", response_model=PaginatedResponse[ParkingSpotResponse])
@cache_response(expire=30)  # Cache for 30 seconds
async def list_parking_spots(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    spot_type: Optional[str] = Query(None, regex="^(standard|handicapped|ev|motorcycle)$"),
    status: Optional[str] = Query(None, regex="^(available|occupied|reserved|maintenance)$"),
    floor: Optional[int] = Query(None, ge=1, le=10),
    section: Optional[str] = None,
    available: Optional[bool] = False,
    features: Optional[str] = None,
    sort: Optional[str] = Query("spot_number", regex="^(spot_number|price_per_hour|floor)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Any:
    """
    List parking spots with optional filtering.
    """
    # Parse features if provided
    feature_list = features.split(",") if features else None
    
    spots = await crud_parking_spot.get_multi(
        db,
        spot_type=spot_type,
        status=status if not available else "available",
        floor=floor,
        section=section,
        features=feature_list,
        sort=sort,
        skip=(page - 1) * size,
        limit=size
    )
    
    total = await crud_parking_spot.count(
        db,
        spot_type=spot_type,
        status=status if not available else "available",
        floor=floor,
        section=section,
        features=feature_list
    )
    
    return paginate(spots, total, page, size)


@router.get("/spots/{spot_id}", response_model=ParkingSpotResponse)
@cache_response(expire=30)
async def get_parking_spot(
    spot_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get detailed information about a specific parking spot.
    """
    spot = await crud_parking_spot.get(db, id=spot_id)
    if not spot:
        raise ParkingSpotNotFoundException()
    return spot


@router.get("/availability", response_model=ParkingSpotAvailability)
async def check_availability(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_time: datetime = Query(..., description="Start time (ISO format)"),
    end_time: datetime = Query(..., description="End time (ISO format)"),
    spot_type: Optional[str] = Query(None, regex="^(standard|handicapped|ev|motorcycle)$"),
    features: Optional[str] = None,
) -> Any:
    """
    Check spot availability for a specific time period.
    """
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    # Parse features
    feature_list = features.split(",") if features else None
    
    # Find available spots
    available_spots = await crud_parking_spot.get_available_spots(
        db,
        start_time=start_time,
        end_time=end_time,
        spot_type=spot_type,
        features=feature_list
    )
    
    # Calculate total price for each spot
    duration_hours = (end_time - start_time).total_seconds() / 3600
    for spot in available_spots:
        spot.total_price = spot.price_per_hour * duration_hours
    
    # Get summary statistics
    total_spots = await crud_parking_spot.count(db, spot_type=spot_type)
    total_available = len(available_spots)
    
    return ParkingSpotAvailability(
        available_spots=available_spots,
        total_available=total_available,
        total_spots=total_spots,
        requested_period={
            "start_time": start_time,
            "end_time": end_time,
            "duration_hours": duration_hours
        }
    )


@router.get("/status", response_model=dict)
@cache_response(expire=10)  # Cache for 10 seconds
async def get_parking_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    floor: Optional[int] = Query(None, ge=1, le=10),
) -> Any:
    """
    Get real-time status of parking spots.
    """
    status_data = await crud_parking_spot.get_status_summary(db, floor=floor)
    return status_data


@router.get("/map", response_model=ParkingSpotMap)
@cache_response(expire=300)  # Cache for 5 minutes
async def get_parking_map(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    floor: int = Query(1, ge=1, le=10),
) -> Any:
    """
    Get visual representation of parking layout.
    """
    spots = await crud_parking_spot.get_multi(db, floor=floor, limit=1000)
    
    # Group spots by section
    sections = {}
    for spot in spots:
        if spot.section not in sections:
            sections[spot.section] = []
        sections[spot.section].append(spot)
    
    # Build map data
    map_data = {
        "floor": floor,
        "dimensions": {
            "width": 100,
            "height": 80
        },
        "sections": [
            {
                "id": section,
                "name": f"Section {section}",
                "bounds": {
                    "x": i * 25,
                    "y": 0,
                    "width": 25,
                    "height": 40
                }
            }
            for i, section in enumerate(sections.keys())
        ],
        "spots": [
            {
                "id": spot.id,
                "number": spot.spot_number,
                "type": spot.spot_type,
                "status": spot.status,
                "coordinates": spot.coordinates or {
                    "x": (i % 10) * 10,
                    "y": (i // 10) * 8
                },
                "width": 5,
                "height": 2.5,
                "rotation": 0
            }
            for i, spot in enumerate(spots)
        ],
        "legend": {
            "available": "#10b981",
            "occupied": "#ef4444",
            "reserved": "#f59e0b",
            "maintenance": "#6b7280"
        }
    }
    
    return ParkingSpotMap(**map_data)


# Admin endpoints
@router.post("/spots", response_model=ParkingSpotResponse, status_code=status.HTTP_201_CREATED)
async def create_parking_spot(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    spot_in: ParkingSpotCreate,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Create a new parking spot (admin only).
    """
    # Check if spot number already exists
    existing = await crud_parking_spot.get_by_spot_number(db, spot_number=spot_in.spot_number)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spot number already exists"
        )
    
    spot = await crud_parking_spot.create(db, obj_in=spot_in)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="CREATE_PARKING_SPOT",
        resource="parking_spot",
        resource_id=spot.id,
        details={"spot_number": spot.spot_number},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    # Invalidate cache
    await invalidate_cache("parking:*")
    
    return spot


@router.put("/spots/{spot_id}", response_model=ParkingSpotResponse)
async def update_parking_spot(
    spot_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    spot_in: ParkingSpotUpdate,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Update a parking spot (admin only).
    """
    spot = await crud_parking_spot.get(db, id=spot_id)
    if not spot:
        raise ParkingSpotNotFoundException()
    
    spot = await crud_parking_spot.update(db, db_obj=spot, obj_in=spot_in)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="UPDATE_PARKING_SPOT",
        resource="parking_spot",
        resource_id=spot_id,
        details={"changes": spot_in.dict(exclude_unset=True)},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    # Invalidate cache
    await invalidate_cache(f"parking:*")
    
    return spot


@router.delete("/spots/{spot_id}", response_model=dict)
async def delete_parking_spot(
    spot_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Delete a parking spot (admin only).
    """
    spot = await crud_parking_spot.get(db, id=spot_id)
    if not spot:
        raise ParkingSpotNotFoundException()
    
    # Check if spot has active reservations
    has_active = await crud_reservation.check_active_for_spot(db, spot_id=spot_id)
    if has_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete spot with active reservations"
        )
    
    await crud_parking_spot.remove(db, id=spot_id)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="DELETE_PARKING_SPOT",
        resource="parking_spot",
        resource_id=spot_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    # Invalidate cache
    await invalidate_cache("parking:*")
    
    return {"message": "Parking spot deleted successfully"}


@router.post("/spots/{spot_id}/maintenance", response_model=ParkingSpotResponse)
async def set_maintenance_mode(
    spot_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    maintenance_data: dict,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Set parking spot to maintenance mode (admin only).
    """
    spot = await crud_parking_spot.get(db, id=spot_id)
    if not spot:
        raise ParkingSpotNotFoundException()
    
    # Update spot status
    spot = await crud_parking_spot.update(
        db,
        db_obj=spot,
        obj_in={"status": "maintenance"}
    )
    
    # Create maintenance record
    await crud_parking_spot.create_maintenance_record(
        db,
        spot_id=spot_id,
        reported_by=current_user.id,
        **maintenance_data
    )
    
    # Cancel any upcoming reservations
    await crud_reservation.cancel_for_spot(
        db,
        spot_id=spot_id,
        reason="Spot under maintenance"
    )
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="MAINTENANCE_MODE",
        resource="parking_spot",
        resource_id=spot_id,
        details=maintenance_data,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return spot