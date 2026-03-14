"""
Validation utility functions.
"""

import re
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from uuid import UUID
from email_validator import validate_email as validate_email_lib, EmailNotValidError
import phonenumbers
from jsonschema import validate, ValidationError


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email address.
    
    Args:
        email: Email to validate
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    try:
        valid = validate_email_lib(email)
        return True, None
    except EmailNotValidError as e:
        return False, str(e)


def validate_phone(phone: str, region: str = "US") -> tuple[bool, Optional[str]]:
    """
    Validate phone number.
    
    Args:
        phone: Phone number to validate
        region: Region code (ISO 3166-1 alpha-2)
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    try:
        parsed = phonenumbers.parse(phone, region)
        if phonenumbers.is_valid_number(parsed):
            return True, None
        else:
            return False, "Invalid phone number"
    except phonenumbers.NumberParseException as e:
        return False, str(e)


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    
    Args:
        password: Password to validate
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, None


def validate_plate_number(plate: str, country: str = "US") -> tuple[bool, Optional[str]]:
    """
    Validate vehicle license plate number.
    
    Args:
        plate: Plate number to validate
        country: Country code
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Basic validation - can be extended with country-specific patterns
    if not plate or len(plate) < 2:
        return False, "Plate number is too short"
    
    if len(plate) > 15:
        return False, "Plate number is too long"
    
    # Check for valid characters (alphanumeric, spaces, hyphens)
    if not re.match(r"^[A-Z0-9\s\-]+$", plate.upper()):
        return False, "Plate number contains invalid characters"
    
    return True, None


def validate_vehicle_model(model: str) -> tuple[bool, Optional[str]]:
    """
    Validate vehicle model.
    
    Args:
        model: Vehicle model to validate
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not model or len(model) < 2:
        return False, "Model name is too short"
    
    if len(model) > 50:
        return False, "Model name is too long"
    
    if not re.match(r"^[A-Za-z0-9\s\-]+$", model):
        return False, "Model name contains invalid characters"
    
    return True, None


def validate_price(price: float) -> tuple[bool, Optional[str]]:
    """
    Validate price amount.
    
    Args:
        price: Price to validate
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if price < 0:
        return False, "Price cannot be negative"
    
    if price > 1000000:
        return False, "Price exceeds maximum allowed"
    
    # Check for too many decimal places
    if abs(price - round(price, 2)) > 0.001:
        return False, "Price can only have up to 2 decimal places"
    
    return True, None


def validate_uuid(uuid_str: str) -> bool:
    """
    Validate UUID string.
    
    Args:
        uuid_str: UUID string to validate
        
    Returns:
        bool: True if valid UUID
    """
    try:
        UUID(uuid_str)
        return True
    except ValueError:
        return False


def validate_json_schema(
    data: Dict[str, Any],
    schema: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """
    Validate data against JSON schema.
    
    Args:
        data: Data to validate
        schema: JSON schema
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    try:
        validate(instance=data, schema=schema)
        return True, None
    except ValidationError as e:
        return False, str(e)


def validate_date_range(
    start_date: Union[datetime, date],
    end_date: Union[datetime, date],
    max_days: Optional[int] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate date range.
    
    Args:
        start_date: Start date
        end_date: End date
        max_days: Maximum allowed days in range
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if start_date >= end_date:
        return False, "Start date must be before end date"
    
    if max_days:
        days_diff = (end_date - start_date).days
        if days_diff > max_days:
            return False, f"Date range cannot exceed {max_days} days"
    
    return True, None


def validate_future_date(
    dt: Union[datetime, date],
    allow_today: bool = False
) -> tuple[bool, Optional[str]]:
    """
    Validate date is in future.
    
    Args:
        dt: Date to validate
        allow_today: Allow today as future
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    now = datetime.now().date() if isinstance(dt, date) else datetime.now()
    
    if isinstance(dt, datetime):
        dt = dt.replace(tzinfo=None)
        now = now.replace(tzinfo=None)
    
    if dt < now:
        return False, "Date must be in the future"
    
    if not allow_today and dt == now:
        return False, "Date must be in the future (not today)"
    
    return True, None


def validate_past_date(
    dt: Union[datetime, date],
    allow_today: bool = False
) -> tuple[bool, Optional[str]]:
    """
    Validate date is in past.
    
    Args:
        dt: Date to validate
        allow_today: Allow today as past
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    now = datetime.now().date() if isinstance(dt, date) else datetime.now()
    
    if isinstance(dt, datetime):
        dt = dt.replace(tzinfo=None)
        now = now.replace(tzinfo=None)
    
    if dt > now:
        return False, "Date must be in the past"
    
    if not allow_today and dt == now:
        return False, "Date must be in the past (not today)"
    
    return True, None


def validate_time_format(time_str: str) -> tuple[bool, Optional[str]]:
    """
    Validate time format (HH:MM).
    
    Args:
        time_str: Time string to validate
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    pattern = r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
    if not re.match(pattern, time_str):
        return False, "Invalid time format. Use HH:MM"
    
    return True, None


def validate_url(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate URL.
    
    Args:
        url: URL to validate
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    pattern = r"^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$"
    if not re.match(pattern, url):
        return False, "Invalid URL format"
    
    return True, None


def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address (IPv4 or IPv6).
    
    Args:
        ip: IP address to validate
        
    Returns:
        bool: True if valid IP
    """
    # IPv4 pattern
    ipv4_pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    
    # IPv6 pattern (simplified)
    ipv6_pattern = r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$"
    
    return bool(re.match(ipv4_pattern, ip) or re.match(ipv6_pattern, ip))


def validate_coordinates(lat: float, lng: float) -> tuple[bool, Optional[str]]:
    """
    Validate geographic coordinates.
    
    Args:
        lat: Latitude
        lng: Longitude
        
    Returns:
        tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not -90 <= lat <= 90:
        return False, "Latitude must be between -90 and 90"
    
    if not -180 <= lng <= 180:
        return False, "Longitude must be between -180 and 180"
    
    return True, None