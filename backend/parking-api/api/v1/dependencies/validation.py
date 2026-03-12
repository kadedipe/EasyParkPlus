"""
Validation dependencies for request parameters.
"""

import re
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID
from fastapi import HTTPException, Query, Path, status


async def validate_uuid(
    uuid_str: str = Path(..., description="UUID to validate")
) -> str:
    """
    Validate UUID parameter.
    """
    try:
        UUID(uuid_str)
        return uuid_str
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID format: {uuid_str}"
        )


async def validate_email(
    email: str = Query(..., description="Email to validate")
) -> str:
    """
    Validate email format.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return email.lower()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid email format: {email}"
    )


async def validate_phone(
    phone: str = Query(..., description="Phone number to validate")
) -> str:
    """
    Validate phone number format.
    """
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Check if it's a valid number (10-15 digits)
    if re.match(r'^\d{10,15}$', cleaned):
        return phone
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid phone number format: {phone}"
    )


async def validate_license_plate(
    license_plate: str = Query(..., description="License plate to validate")
) -> str:
    """
    Validate license plate format.
    """
    # Basic alphanumeric validation
    cleaned = re.sub(r'[\s\-]', '', license_plate)
    
    if re.match(r'^[A-Z0-9]{2,10}$', cleaned.upper()):
        return cleaned.upper()
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid license plate format: {license_plate}"
    )


async def validate_datetime_range(
    start_time: datetime,
    end_time: datetime,
    max_duration_hours: int = 24,
    min_duration_minutes: int = 30
) -> bool:
    """
    Validate datetime range.
    """
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End time must be after start time"
        )
    
    if start_time < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start time cannot be in the past"
        )
    
    duration = end_time - start_time
    if duration > timedelta(hours=max_duration_hours):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duration cannot exceed {max_duration_hours} hours"
        )
    
    if duration < timedelta(minutes=min_duration_minutes):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Duration must be at least {min_duration_minutes} minutes"
        )
    
    return True


async def validate_date_range(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    max_days: int = 30
) -> bool:
    """
    Validate date range.
    """
    if start_date and end_date:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after or equal to start date"
            )
        
        if (end_date - start_date).days > max_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Date range cannot exceed {max_days} days"
            )
    
    return True


async def validate_pagination(
    page: int = 1,
    size: int = 20,
    max_size: int = 100
) -> tuple:
    """
    Validate pagination parameters.
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page must be greater than 0"
        )
    
    if size < 1 or size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Size must be between 1 and {max_size}"
        )
    
    return page, size


async def validate_sort_field(
    sort: Optional[str],
    allowed_fields: list,
    default: str = "created_at"
) -> str:
    """
    Validate sort field.
    """
    if not sort:
        return default
    
    # Remove leading - for descending
    field = sort.lstrip('-')
    
    if field not in allowed_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort field. Allowed: {allowed_fields}"
        )
    
    return sort


async def validate_enum(
    value: str,
    allowed_values: list,
    param_name: str = "value"
) -> str:
    """
    Validate enum value.
    """
    if value not in allowed_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {param_name}. Allowed: {allowed_values}"
        )
    
    return value


async def validate_integer_range(
    value: int,
    min_val: int,
    max_val: int,
    param_name: str = "value"
) -> int:
    """
    Validate integer range.
    """
    if value < min_val or value > max_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{param_name} must be between {min_val} and {max_val}"
        )
    
    return value


async def validate_float_range(
    value: float,
    min_val: float,
    max_val: float,
    param_name: str = "value"
) -> float:
    """
    Validate float range.
    """
    if value < min_val or value > max_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{param_name} must be between {min_val} and {max_val}"
        )
    
    return value


async def validate_password_strength(password: str) -> str:
    """
    Validate password strength.
    """
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    if not re.search(r'[A-Z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter"
        )
    
    if not re.search(r'[a-z]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter"
        )
    
    if not re.search(r'\d', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number"
        )
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one special character"
        )
    
    return password


class Validators:
    """
    Collection of validation methods.
    """
    
    @staticmethod
    def is_valid_uuid(uuid_str: str) -> bool:
        """Check if string is valid UUID."""
        try:
            UUID(uuid_str)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Check if string is valid email."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Check if string is valid phone number."""
        cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
        return bool(re.match(r'^\d{10,15}$', cleaned))
    
    @staticmethod
    def is_valid_license_plate(plate: str) -> bool:
        """Check if string is valid license plate."""
        cleaned = re.sub(r'[\s\-]', '', plate)
        return bool(re.match(r'^[A-Z0-9]{2,10}$', cleaned.upper()))
    
    @staticmethod
    def is_strong_password(password: str) -> bool:
        """Check if password is strong."""
        if len(password) < 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False
        return True