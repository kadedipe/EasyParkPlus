"""
Common schemas used across different modules.
"""

from typing import Optional, Any, Dict, Generic, TypeVar
from datetime import datetime

from pydantic import BaseModel, Field


T = TypeVar('T')


class PaginationParams(BaseModel):
    """Common pagination parameters."""
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: Optional[str] = Field(None, pattern="^(asc|desc)$", description="Sort order")


class DateRangeFilter(BaseModel):
    """Common date range filter."""
    start_date: Optional[datetime] = Field(None, description="Start date")
    end_date: Optional[datetime] = Field(None, description="End date")


class ErrorResponse(BaseModel):
    """Common error response schema."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class SuccessResponse(BaseModel, Generic[T]):
    """Common success response schema."""
    success: bool = Field(True, description="Success status")
    data: Optional[T] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Success message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")