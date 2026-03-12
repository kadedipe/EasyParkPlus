"""
Vehicle management endpoints.
"""

from typing import List, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.deps import get_current_user
from ....crud import crud_vehicle
from ....models.user import User
from ....schemas.vehicle import (
    VehicleResponse,
    VehicleCreate,
    VehicleUpdate
)
from ....db.session import get_db
from ....services.audit import audit_log
from ....utils.exceptions import VehicleNotFoundException, LicensePlateExistsException

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("/", response_model=List[VehicleResponse])
async def read_vehicles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve vehicles for current user.
    """
    vehicles = await crud_vehicle.get_multi_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return vehicles


@router.post("/", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    vehicle_in: VehicleCreate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create new vehicle for current user.
    """
    # Check if license plate already exists
    existing = await crud_vehicle.get_by_license_plate(db, license_plate=vehicle_in.license_plate)
    if existing:
        raise LicensePlateExistsException()
    
    # If this is the first vehicle or marked as default, handle default logic
    user_vehicles = await crud_vehicle.get_multi_by_user(db, user_id=current_user.id, limit=1)
    if not user_vehicles:
        vehicle_in.is_default = True
    
    vehicle = await crud_vehicle.create_with_user(
        db, obj_in=vehicle_in, user_id=current_user.id
    )
    
    # If this vehicle is set as default, unset others
    if vehicle_in.is_default:
        await crud_vehicle.set_default(db, user_id=current_user.id, vehicle_id=vehicle.id)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="CREATE_VEHICLE",
        resource="vehicle",
        resource_id=vehicle.id,
        details={"license_plate": vehicle.license_plate},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return vehicle


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def read_vehicle(
    vehicle_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get vehicle by ID.
    """
    vehicle = await crud_vehicle.get(db, id=vehicle_id)
    if not vehicle or vehicle.user_id != current_user.id:
        raise VehicleNotFoundException()
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    vehicle_in: VehicleUpdate,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update vehicle.
    """
    vehicle = await crud_vehicle.get(db, id=vehicle_id)
    if not vehicle or vehicle.user_id != current_user.id:
        raise VehicleNotFoundException()
    
    # Check license plate uniqueness if being updated
    if vehicle_in.license_plate and vehicle_in.license_plate != vehicle.license_plate:
        existing = await crud_vehicle.get_by_license_plate(db, license_plate=vehicle_in.license_plate)
        if existing and existing.id != vehicle_id:
            raise LicensePlateExistsException()
    
    vehicle = await crud_vehicle.update(db, db_obj=vehicle, obj_in=vehicle_in)
    
    # Handle default vehicle logic
    if vehicle_in.is_default:
        await crud_vehicle.set_default(db, user_id=current_user.id, vehicle_id=vehicle.id)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="UPDATE_VEHICLE",
        resource="vehicle",
        resource_id=vehicle_id,
        details={"changes": vehicle_in.dict(exclude_unset=True)},
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return vehicle


@router.delete("/{vehicle_id}", response_model=dict)
async def delete_vehicle(
    vehicle_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Delete vehicle.
    """
    vehicle = await crud_vehicle.get(db, id=vehicle_id)
    if not vehicle or vehicle.user_id != current_user.id:
        raise VehicleNotFoundException()
    
    # Check if this is the only vehicle or default
    user_vehicles = await crud_vehicle.get_multi_by_user(db, user_id=current_user.id, limit=2)
    if len(user_vehicles) == 1:
        # This is the only vehicle
        pass
    elif vehicle.is_default:
        # Need to set another vehicle as default
        other_vehicle = next(v for v in user_vehicles if v.id != vehicle_id)
        await crud_vehicle.set_default(db, user_id=current_user.id, vehicle_id=other_vehicle.id)
    
    await crud_vehicle.remove(db, id=vehicle_id)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="DELETE_VEHICLE",
        resource="vehicle",
        resource_id=vehicle_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return {"message": "Vehicle deleted successfully"}


@router.post("/{vehicle_id}/set-default", response_model=VehicleResponse)
async def set_default_vehicle(
    vehicle_id: str,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Set vehicle as default.
    """
    vehicle = await crud_vehicle.get(db, id=vehicle_id)
    if not vehicle or vehicle.user_id != current_user.id:
        raise VehicleNotFoundException()
    
    vehicle = await crud_vehicle.set_default(db, user_id=current_user.id, vehicle_id=vehicle_id)
    return vehicle