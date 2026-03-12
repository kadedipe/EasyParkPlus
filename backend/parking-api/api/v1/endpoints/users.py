"""
User management endpoints.
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.deps import get_current_user, get_current_active_superuser
from ....crud import crud_user, crud_vehicle, crud_reservation
from ....models.user import User
from ....schemas.user import (
    UserResponse,
    UserUpdate,
    UserProfileUpdate,
    UserPreferences,
    UserStats
)
from ....schemas.vehicle import VehicleResponse
from ....schemas.reservation import ReservationResponse
from ....db.session import get_db
from ....services.audit import audit_log
from ....utils.pagination import PaginatedResponse, paginate
from ....utils.cache import cache_response, invalidate_cache

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get current user information.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update current user.
    """
    user = await crud_user.update(db, db_obj=current_user, obj_in=user_in)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="UPDATE_PROFILE",
        resource="user",
        resource_id=current_user.id,
        details={"changes": user_in.dict(exclude_unset=True)},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    # Invalidate cache
    await invalidate_cache(f"user:{current_user.id}")
    
    return user


@router.patch("/me/preferences", response_model=UserPreferences)
async def update_preferences(
    *,
    db: AsyncSession = Depends(get_db),
    preferences: UserPreferences,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update user preferences.
    """
    user = await crud_user.update_preferences(db, user_id=current_user.id, preferences=preferences)
    return user.preferences


@router.get("/me/stats", response_model=UserStats)
@cache_response(expire=300)  # Cache for 5 minutes
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get user statistics.
    """
    return await crud_user.get_stats(db, user_id=current_user.id)


@router.get("/me/vehicles", response_model=List[VehicleResponse])
async def get_user_vehicles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> Any:
    """
    Get all vehicles for current user.
    """
    vehicles = await crud_vehicle.get_multi_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return vehicles


@router.get("/me/reservations", response_model=PaginatedResponse[ReservationResponse])
@cache_response(expire=60)  # Cache for 1 minute
async def get_user_reservations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, regex="^(confirmed|active|completed|cancelled)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> Any:
    """
    Get all reservations for current user with pagination.
    """
    reservations = await crud_reservation.get_multi_by_user(
        db,
        user_id=current_user.id,
        status=status,
        skip=(page - 1) * size,
        limit=size
    )
    
    total = await crud_reservation.count_by_user(db, user_id=current_user.id, status=status)
    
    return paginate(reservations, total, page, size)


@router.delete("/me", response_model=dict)
async def delete_current_user(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Delete current user account (soft delete).
    """
    await crud_user.soft_delete(db, user_id=current_user.id)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="DELETE_ACCOUNT",
        resource="user",
        resource_id=current_user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return {"message": "Account deleted successfully"}


# Admin endpoints
@router.get("/", response_model=PaginatedResponse[UserResponse])
async def read_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = Query(None, regex="^(user|admin|manager)$"),
    is_active: Optional[bool] = None,
) -> Any:
    """
    Retrieve users (admin only).
    """
    users = await crud_user.get_multi(
        db,
        skip=skip,
        limit=limit,
        search=search,
        role=role,
        is_active=is_active
    )
    
    total = await crud_user.count(db, search=search, role=role, is_active=is_active)
    
    return paginate(users, total, skip, limit)


@router.get("/{user_id}", response_model=UserResponse)
async def read_user_by_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Get a specific user by id (admin only).
    """
    user = await crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Update a user (admin only).
    """
    user = await crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user = await crud_user.update(db, db_obj=user, obj_in=user_in)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="ADMIN_UPDATE_USER",
        resource="user",
        resource_id=user_id,
        details={"changes": user_in.dict(exclude_unset=True)},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return user


@router.delete("/{user_id}", response_model=dict)
async def delete_user(
    user_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Delete a user (admin only).
    """
    user = await crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await crud_user.remove(db, id=user_id)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="ADMIN_DELETE_USER",
        resource="user",
        resource_id=user_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return {"message": "User deleted successfully"}


@router.post("/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    user_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Activate a user account (admin only).
    """
    user = await crud_user.activate(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Any:
    """
    Deactivate a user account (admin only).
    """
    user = await crud_user.deactivate(db, user_id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user