"""Reservation model for the parking management system."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from ..enums import ReservationStatus, VehicleType


class Reservation:
    """Reservation model representing a parking reservation."""
    
    def __init__(
        self,
        reservation_id: Optional[int] = None,
        user_id: int = 0,
        spot_id: int = 0,
        vehicle_id: int = 0,
        vehicle_type: VehicleType = VehicleType.SEDAN,
        license_plate: str = "",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        actual_check_in: Optional[datetime] = None,
        actual_check_out: Optional[datetime] = None,
        status: ReservationStatus = ReservationStatus.PENDING,
        total_amount: float = 0.0,
        paid_amount: float = 0.0,
        is_paid: bool = False,
        cancellation_reason: Optional[str] = None,
        cancelled_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.reservation_id = reservation_id
        self.user_id = user_id
        self.spot_id = spot_id
        self.vehicle_id = vehicle_id
        self.vehicle_type = vehicle_type
        self.license_plate = license_plate
        self.start_time = start_time or datetime.utcnow()
        self.end_time = end_time or (datetime.utcnow() + timedelta(hours=1))
        self.actual_check_in = actual_check_in
        self.actual_check_out = actual_check_out
        self.status = status
        self.total_amount = total_amount
        self.paid_amount = paid_amount
        self.is_paid = is_paid
        self.cancellation_reason = cancellation_reason
        self.cancelled_at = cancelled_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at
        self.notes = notes
        self.metadata = metadata or {}
    
    @property
    def duration_hours(self) -> float:
        """Get reservation duration in hours."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds() / 3600
        return 0
    
    @property
    def is_active(self) -> bool:
        """Check if reservation is active."""
        return self.status in [
            ReservationStatus.PENDING,
            ReservationStatus.CONFIRMED,
            ReservationStatus.CHECKED_IN
        ]
    
    @property
    def can_check_in(self) -> bool:
        """Check if user can check in to this reservation."""
        now = datetime.utcnow()
        return (
            self.status == ReservationStatus.CONFIRMED and
            self.start_time <= now <= self.end_time
        )
    
    @property
    def can_check_out(self) -> bool:
        """Check if user can check out from this reservation."""
        return self.status == ReservationStatus.CHECKED_IN
    
    @property
    def can_cancel(self) -> bool:
        """Check if reservation can be cancelled."""
        return self.status in [
            ReservationStatus.PENDING,
            ReservationStatus.CONFIRMED
        ]
    
    @property
    def balance_due(self) -> float:
        """Calculate remaining balance."""
        return max(0, self.total_amount - self.paid_amount)
    
    def check_in(self) -> None:
        """Check in to the reservation."""
        if self.can_check_in:
            self.actual_check_in = datetime.utcnow()
            self.status = ReservationStatus.CHECKED_IN
            self.updated_at = datetime.utcnow()
    
    def check_out(self) -> None:
        """Check out from the reservation."""
        if self.can_check_out:
            self.actual_check_out = datetime.utcnow()
            self.status = ReservationStatus.COMPLETED
            self.updated_at = datetime.utcnow()
    
    def cancel(self, reason: str) -> None:
        """Cancel the reservation."""
        if self.can_cancel:
            self.status = ReservationStatus.CANCELLED
            self.cancellation_reason = reason
            self.cancelled_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert reservation to dictionary."""
        return {
            "reservation_id": self.reservation_id,
            "user_id": self.user_id,
            "spot_id": self.spot_id,
            "vehicle_id": self.vehicle_id,
            "vehicle_type": self.vehicle_type.value if self.vehicle_type else None,
            "license_plate": self.license_plate,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "actual_check_in": self.actual_check_in.isoformat() if self.actual_check_in else None,
            "actual_check_out": self.actual_check_out.isoformat() if self.actual_check_out else None,
            "status": self.status.value if self.status else None,
            "duration_hours": self.duration_hours,
            "total_amount": self.total_amount,
            "paid_amount": self.paid_amount,
            "balance_due": self.balance_due,
            "is_paid": self.is_paid,
            "is_active": self.is_active,
            "can_check_in": self.can_check_in,
            "can_check_out": self.can_check_out,
            "can_cancel": self.can_cancel,
            "cancellation_reason": self.cancellation_reason,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Reservation':
        """Create reservation from dictionary."""
        return cls(
            reservation_id=data.get('reservation_id'),
            user_id=data.get('user_id', 0),
            spot_id=data.get('spot_id', 0),
            vehicle_id=data.get('vehicle_id', 0),
            vehicle_type=VehicleType(data['vehicle_type']) if data.get('vehicle_type') else None,
            license_plate=data.get('license_plate', ''),
            start_time=datetime.fromisoformat(data['start_time']) if data.get('start_time') else None,
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            actual_check_in=datetime.fromisoformat(data['actual_check_in']) if data.get('actual_check_in') else None,
            actual_check_out=datetime.fromisoformat(data['actual_check_out']) if data.get('actual_check_out') else None,
            status=ReservationStatus(data['status']) if data.get('status') else None,
            total_amount=data.get('total_amount', 0.0),
            paid_amount=data.get('paid_amount', 0.0),
            is_paid=data.get('is_paid', False),
            cancellation_reason=data.get('cancellation_reason'),
            cancelled_at=datetime.fromisoformat(data['cancelled_at']) if data.get('cancelled_at') else None,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            notes=data.get('notes'),
            metadata=data.get('metadata'),
        )