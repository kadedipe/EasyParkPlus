"""Request schemas for API validation."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
from ..enums import (
    UserRole, 
    ParkingSpotType, 
    VehicleType, 
    ReservationStatus,
    PaymentStatus
)


class UserCreateSchema(BaseModel):
    """Schema for creating a new user."""
    
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    role: UserRole = UserRole.CUSTOMER
    preferences: Optional[Dict[str, Any]] = None


class UserUpdateSchema(BaseModel):
    """Schema for updating user information."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = Field(None, pattern=r'^\+?[1-9]\d{1,14}$')
    preferences: Optional[Dict[str, Any]] = None
    profile_picture: Optional[str] = None


class UserLoginSchema(BaseModel):
    """Schema for user login."""
    
    username: str
    password: str


class VehicleCreateSchema(BaseModel):
    """Schema for creating a new vehicle."""
    
    make: str = Field(..., min_length=1, max_length=50)
    model: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=1900, le=2100)
    color: str = Field(..., min_length=1, max_length=30)
    license_plate: str = Field(..., min_length=1, max_length=20)
    vehicle_type: VehicleType
    is_default: bool = False


class ReservationCreateSchema(BaseModel):
    """Schema for creating a new reservation."""
    
    spot_id: int
    vehicle_id: int
    license_plate: str
    start_time: datetime
    end_time: datetime
    vehicle_type: VehicleType
    notes: Optional[str] = None
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validate that end time is after start time."""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class ReservationUpdateSchema(BaseModel):
    """Schema for updating a reservation."""
    
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    vehicle_id: Optional[int] = None
    license_plate: Optional[str] = None
    notes: Optional[str] = None
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Validate that end time is after start time if both provided."""
        if v and 'start_time' in values and values['start_time'] and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class ParkingSpotCreateSchema(BaseModel):
    """Schema for creating a new parking spot."""
    
    spot_number: str
    spot_type: ParkingSpotType
    level: str = "1"
    section: str = "A"
    hourly_rate: Optional[float] = None
    features: Optional[List[str]] = None
    location_coordinates: Optional[Dict[str, float]] = None


class PaymentCreateSchema(BaseModel):
    """Schema for creating a payment."""
    
    reservation_id: int
    amount: float = Field(..., gt=0)
    payment_method: str
    card_token: Optional[str] = None


class NotificationCreateSchema(BaseModel):
    """Schema for creating a notification."""
    
    user_id: int
    notification_type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None


class DateRangeSchema(BaseModel):
    """Schema for date range queries."""
    
    start_date: datetime
    end_date: datetime
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        """Validate that end date is after start date."""
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class PaginationSchema(BaseModel):
    """Schema for pagination parameters."""
    
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field("asc", regex="^(asc|desc)$")