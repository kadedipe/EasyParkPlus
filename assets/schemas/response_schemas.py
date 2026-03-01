"""Response schemas for API responses."""

from typing import Optional, Dict, Any, List, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field
from ..enums import (
    ReservationStatus,
    PaymentStatus,
    UserRole,
    UserStatus,
    ParkingSpotType,
    VehicleType,
    NotificationType
)

T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """Generic API response wrapper."""
    
    success: bool = True
    data: Optional[T] = None
    error: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(ApiResponse, Generic[T]):
    """Paginated API response."""
    
    data: List[T]
    total: int
    page: int
    per_page: int
    total_pages: int


class UserResponse(BaseModel):
    """User response schema."""
    
    user_id: int
    email: str
    username: str
    first_name: str
    last_name: str
    full_name: str
    phone: Optional[str]
    role: UserRole
    status: UserStatus
    created_at: datetime
    last_login: Optional[datetime]
    email_verified: bool
    phone_verified: bool
    profile_picture: Optional[str]
    preferences: Dict[str, Any]


class VehicleResponse(BaseModel):
    """Vehicle response schema."""
    
    vehicle_id: int
    user_id: int
    make: str
    model: str
    year: int
    color: str
    license_plate: str
    vehicle_type: VehicleType
    is_default: bool
    created_at: datetime


class ParkingSpotResponse(BaseModel):
    """Parking spot response schema."""
    
    spot_id: int
    spot_number: str
    display_name: str
    spot_type: ParkingSpotType
    level: str
    section: str
    is_available: bool
    is_occupied: bool
    current_vehicle_id: Optional[int]
    current_reservation_id: Optional[int]
    hourly_rate: Optional[float]
    features: List[str]
    location_coordinates: Dict[str, float]


class ReservationResponse(BaseModel):
    """Reservation response schema."""
    
    reservation_id: int
    user_id: int
    spot_id: int
    vehicle_id: int
    license_plate: str
    start_time: datetime
    end_time: datetime
    actual_check_in: Optional[datetime]
    actual_check_out: Optional[datetime]
    status: ReservationStatus
    duration_hours: float
    total_amount: float
    paid_amount: float
    balance_due: float
    is_paid: bool
    can_check_in: bool
    can_check_out: bool
    can_cancel: bool
    created_at: datetime
    notes: Optional[str]
    
    # Nested objects
    spot: Optional[ParkingSpotResponse] = None
    vehicle: Optional[VehicleResponse] = None


class PaymentResponse(BaseModel):
    """Payment response schema."""
    
    payment_id: int
    reservation_id: int
    user_id: int
    amount: float
    status: PaymentStatus
    payment_method: str
    transaction_id: Optional[str]
    payment_date: datetime
    receipt_url: Optional[str]


class NotificationResponse(BaseModel):
    """Notification response schema."""
    
    notification_id: int
    user_id: int
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]
    data: Optional[Dict[str, Any]]


class AuthResponse(BaseModel):
    """Authentication response schema."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response schema."""
    
    total_reservations: int
    active_reservations: int
    available_spots: int
    occupied_spots: int
    total_revenue: float
    today_revenue: float
    occupancy_rate: float
    upcoming_reservations: int


class HealthCheckResponse(BaseModel):
    """Health check response schema."""
    
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]