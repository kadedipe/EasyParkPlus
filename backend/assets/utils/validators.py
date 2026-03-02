"""Validation utilities for the parking management system.

This module provides comprehensive validation functions for various data types
including emails, phone numbers, passwords, license plates, credit cards,
dates, numbers, and business rules.
"""

import re
import json
from datetime import datetime, date, time, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple, Pattern
from urllib.parse import urlparse
import logging

from ..constants.config import Config
from ..enums import VehicleType, ParkingSpotType, UserRole

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# Email Validation
# ============================================================================

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
EMAIL_MAX_LENGTH = 255
DOMAIN_REGEX = re.compile(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
DISPOSABLE_EMAIL_DOMAINS = {
    'tempmail.com', 'throwaway.com', 'mailinator.com', 'guerrillamail.com',
    'sharklasers.com', 'yopmail.com', 'temp-mail.org', 'fakeinbox.com'
}


def validate_email(email: str, check_disposable: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate email address format.
    
    Args:
        email: Email address to validate
        check_disposable: Whether to check for disposable email domains
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    if len(email) > EMAIL_MAX_LENGTH:
        return False, f"Email must be less than {EMAIL_MAX_LENGTH} characters"
    
    if not EMAIL_REGEX.match(email):
        return False, "Invalid email format"
    
    if check_disposable:
        domain = email.split('@')[1].lower()
        if domain in DISPOSABLE_EMAIL_DOMAINS:
            return False, "Disposable email addresses are not allowed"
    
    return True, None


def validate_email_domain(domain: str) -> Tuple[bool, Optional[str]]:
    """Validate email domain.
    
    Args:
        domain: Domain to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not domain:
        return False, "Domain is required"
    
    if not DOMAIN_REGEX.match(domain):
        return False, "Invalid domain format"
    
    # Check for valid DNS records (optional, can be expensive)
    # import dns.resolver
    # try:
    #     dns.resolver.resolve(domain, 'MX')
    # except Exception:
    #     return False, "Domain has no valid MX records"
    
    return True, None


def extract_domain_from_email(email: str) -> Optional[str]:
    """Extract domain from email address.
    
    Args:
        email: Email address
        
    Returns:
        Domain or None if invalid
    """
    try:
        return email.split('@')[1].lower()
    except (IndexError, AttributeError):
        return None


# ============================================================================
# Phone Number Validation
# ============================================================================

# International phone format: +[country code][number]
PHONE_REGEX = re.compile(r'^\+?[1-9]\d{1,14}$')
US_PHONE_REGEX = re.compile(r'^\+?1?[-.\s]?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}$')
PHONE_MIN_LENGTH = 7
PHONE_MAX_LENGTH = 15


def validate_phone(phone: str, country: str = "US") -> Tuple[bool, Optional[str]]:
    """Validate phone number.
    
    Args:
        phone: Phone number to validate
        country: Country code (US, UK, etc.)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove common separators
    cleaned = re.sub(r'[\s\-\.\(\)]', '', phone)
    
    if len(cleaned) < PHONE_MIN_LENGTH or len(cleaned) > PHONE_MAX_LENGTH:
        return False, f"Phone number must be between {PHONE_MIN_LENGTH} and {PHONE_MAX_LENGTH} digits"
    
    if country.upper() == "US":
        if not US_PHONE_REGEX.match(phone):
            return False, "Invalid US phone number format"
    else:
        if not PHONE_REGEX.match(cleaned):
            return False, "Invalid international phone number format"
    
    return True, None


def validate_phone_international(phone: str) -> Tuple[bool, Optional[str]]:
    """Validate international phone number (E.164 format).
    
    Args:
        phone: Phone number in E.164 format (+1234567890)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    if not phone.startswith('+'):
        return False, "International numbers must start with '+'"
    
    cleaned = phone[1:]  # Remove +
    if not cleaned.isdigit():
        return False, "Phone number must contain only digits after country code"
    
    if len(cleaned) < 7 or len(cleaned) > 15:
        return False, "International phone number must be between 7 and 15 digits"
    
    return True, None


def format_phone(phone: str, country: str = "US") -> str:
    """Format phone number for display.
    
    Args:
        phone: Raw phone number
        country: Country code
        
    Returns:
        Formatted phone number
    """
    # Remove non-digits
    digits = re.sub(r'\D', '', phone)
    
    if country.upper() == "US" and len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif country.upper() == "US" and len(digits) == 11 and digits.startswith('1'):
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        # International format
        return f"+{digits}"


# ============================================================================
# Password Validation
# ============================================================================

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 100
PASSWORD_PATTERNS = {
    'uppercase': r'[A-Z]',
    'lowercase': r'[a-z]',
    'digit': r'\d',
    'special': r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>/?`~]',
}
COMMON_PASSWORDS = {
    'password', 'password123', '123456', '12345678', 'qwerty',
    'abc123', 'password1', 'admin', 'letmein', 'welcome'
}


def validate_password_strength(
    password: str,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = True,
    min_length: int = PASSWORD_MIN_LENGTH,
    max_length: int = PASSWORD_MAX_LENGTH,
    check_common: bool = True
) -> Tuple[bool, List[str]]:
    """Validate password strength.
    
    Args:
        password: Password to validate
        require_uppercase: Require at least one uppercase letter
        require_lowercase: Require at least one lowercase letter
        require_digit: Require at least one digit
        require_special: Require at least one special character
        min_length: Minimum length
        max_length: Maximum length
        check_common: Check against common passwords
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    if not password:
        errors.append("Password is required")
        return False, errors
    
    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters")
    
    if len(password) > max_length:
        errors.append(f"Password must be at most {max_length} characters")
    
    if require_uppercase and not re.search(PASSWORD_PATTERNS['uppercase'], password):
        errors.append("Password must contain at least one uppercase letter")
    
    if require_lowercase and not re.search(PASSWORD_PATTERNS['lowercase'], password):
        errors.append("Password must contain at least one lowercase letter")
    
    if require_digit and not re.search(PASSWORD_PATTERNS['digit'], password):
        errors.append("Password must contain at least one number")
    
    if require_special and not re.search(PASSWORD_PATTERNS['special'], password):
        errors.append("Password must contain at least one special character")
    
    if check_common and password.lower() in COMMON_PASSWORDS:
        errors.append("Password is too common. Please choose a stronger password")
    
    return len(errors) == 0, errors


def validate_password_match(password: str, confirm_password: str) -> Tuple[bool, Optional[str]]:
    """Validate that password and confirmation match.
    
    Args:
        password: Password
        confirm_password: Password confirmation
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if password != confirm_password:
        return False, "Passwords do not match"
    return True, None


def generate_random_password(length: int = 12) -> str:
    """Generate a random strong password.
    
    Args:
        length: Password length
        
    Returns:
        Random password
    """
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Ensure password meets requirements
        valid, _ = validate_password_strength(password)
        if valid:
            return password


# ============================================================================
# License Plate Validation
# ============================================================================

# Country-specific license plate patterns
LICENSE_PLATE_PATTERNS = {
    'US': {
        'regex': r'^[A-Z0-9]{1,8}$',
        'description': '1-8 alphanumeric characters',
        'example': 'ABC123'
    },
    'UK': {
        'regex': r'^[A-Z]{2}\d{2}\s?[A-Z]{3}$',
        'description': 'Two letters, two numbers, three letters',
        'example': 'AB12 CDE'
    },
    'CA': {
        'regex': r'^[A-Z0-9]{1,7}$',
        'description': '1-7 alphanumeric characters',
        'example': 'ABC 123'
    },
    'AU': {
        'regex': r'^[A-Z0-9]{1,7}$',
        'description': '1-7 alphanumeric characters',
        'example': 'ABC123'
    },
    'DE': {
        'regex': r'^[A-Z]{1,3}\s?[A-Z]{1,2}\s?\d{1,4}$',
        'description': 'City code, letters, numbers',
        'example': 'B AB 123'
    }
}


def validate_license_plate(
    plate: str,
    country: str = 'US',
    allow_spaces: bool = True
) -> Tuple[bool, Optional[str]]:
    """Validate license plate number.
    
    Args:
        plate: License plate number
        country: Country code
        allow_spaces: Whether to allow spaces in the plate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not plate:
        return False, "License plate is required"
    
    # Remove spaces if not allowed
    if not allow_spaces:
        plate = plate.replace(' ', '')
    
    # Convert to uppercase
    plate = plate.upper()
    
    pattern_info = LICENSE_PLATE_PATTERNS.get(country.upper())
    if not pattern_info:
        return False, f"Unsupported country: {country}"
    
    if not re.match(pattern_info['regex'], plate):
        return False, f"Invalid {country} license plate format. Expected: {pattern_info['description']}"
    
    return True, None


def format_license_plate(plate: str, country: str = 'US') -> str:
    """Format license plate for display.
    
    Args:
        plate: Raw license plate
        country: Country code
        
    Returns:
        Formatted license plate
    """
    plate = plate.upper().strip()
    
    if country.upper() == 'UK':
        # Format as AB12 CDE
        if len(plate) >= 7:
            return f"{plate[:4]} {plate[4:]}"
    elif country.upper() == 'CA' and len(plate) >= 4:
        # Format as ABC 123
        letters = ''.join(c for c in plate if c.isalpha())
        numbers = ''.join(c for c in plate if c.isdigit())
        if letters and numbers:
            return f"{letters} {numbers}"
    
    return plate


def get_license_plate_country(plate: str) -> Optional[str]:
    """Guess country based on license plate format.
    
    Args:
        plate: License plate number
        
    Returns:
        Country code or None if unknown
    """
    plate = plate.upper().replace(' ', '')
    
    for country, pattern_info in LICENSE_PLATE_PATTERNS.items():
        if re.match(pattern_info['regex'], plate):
            return country
    
    return None


# ============================================================================
# Credit Card Validation
# ============================================================================

CARD_PATTERNS = {
    'visa': re.compile(r'^4[0-9]{12}(?:[0-9]{3})?$'),
    'mastercard': re.compile(r'^5[1-5][0-9]{14}$'),
    'amex': re.compile(r'^3[47][0-9]{13}$'),
    'discover': re.compile(r'^6(?:011|5[0-9]{2})[0-9]{12}$'),
    'diners': re.compile(r'^3(?:0[0-5]|[68][0-9])[0-9]{11}$'),
    'jcb': re.compile(r'^(?:2131|1800|35\d{3})\d{11}$'),
}


def validate_credit_card(number: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate credit card number using Luhn algorithm.
    
    Args:
        number: Credit card number
        
    Returns:
        Tuple of (is_valid, card_type, error_message)
    """
    # Remove non-digits
    number = re.sub(r'\D', '', number)
    
    if not number:
        return False, None, "Credit card number is required"
    
    if not number.isdigit():
        return False, None, "Credit card number must contain only digits"
    
    # Check length
    if len(number) < 13 or len(number) > 19:
        return False, None, "Credit card number must be between 13 and 19 digits"
    
    # Identify card type
    card_type = None
    for ctype, pattern in CARD_PATTERNS.items():
        if pattern.match(number):
            card_type = ctype
            break
    
    # Luhn algorithm
    total = 0
    reverse_digits = number[::-1]
    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    
    if total % 10 != 0:
        return False, card_type, "Invalid credit card number (failed Luhn check)"
    
    return True, card_type, None


def get_card_type(number: str) -> Optional[str]:
    """Get credit card type from number.
    
    Args:
        number: Credit card number
        
    Returns:
        Card type or None if unknown
    """
    number = re.sub(r'\D', '', number)
    
    for card_type, pattern in CARD_PATTERNS.items():
        if pattern.match(number):
            return card_type
    
    return None


def mask_credit_card(number: str, visible_digits: int = 4) -> str:
    """Mask credit card number for display.
    
    Args:
        number: Credit card number
        visible_digits: Number of digits to show at the end
        
    Returns:
        Masked card number
    """
    number = re.sub(r'\D', '', number)
    if len(number) <= visible_digits:
        return number
    
    masked = '*' * (len(number) - visible_digits) + number[-visible_digits:]
    # Format in groups of 4
    return ' '.join(masked[i:i+4] for i in range(0, len(masked), 4))


# ============================================================================
# Date Validation
# ============================================================================

def validate_date_range(
    start_date: Union[datetime, date],
    end_date: Union[datetime, date],
    allow_equal: bool = True,
    max_duration: Optional[timedelta] = None,
    min_duration: Optional[timedelta] = None
) -> Tuple[bool, Optional[str]]:
    """Validate date range.
    
    Args:
        start_date: Start date/datetime
        end_date: End date/datetime
        allow_equal: Whether start and end can be equal
        max_duration: Maximum allowed duration
        min_duration: Minimum allowed duration
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not start_date or not end_date:
        return False, "Start and end dates are required"
    
    if allow_equal:
        if end_date < start_date:
            return False, "End date must be after or equal to start date"
    else:
        if end_date <= start_date:
            return False, "End date must be after start date"
    
    if max_duration:
        duration = end_date - start_date
        if duration > max_duration:
            return False, f"Duration cannot exceed {max_duration}"
    
    if min_duration:
        duration = end_date - start_date
        if duration < min_duration:
            return False, f"Duration must be at least {min_duration}"
    
    return True, None


def validate_future_date(
    dt: Union[datetime, date],
    allow_today: bool = True,
    min_hours_ahead: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """Validate that date is in the future.
    
    Args:
        dt: Date/datetime to validate
        allow_today: Whether today is considered future
        min_hours_ahead: Minimum hours ahead required
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    now = datetime.utcnow()
    
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, time.min)
        now = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if allow_today:
        if dt < now:
            return False, "Date must be today or in the future"
    else:
        if dt <= now:
            return False, "Date must be in the future"
    
    if min_hours_ahead:
        min_time = now + timedelta(hours=min_hours_ahead)
        if dt < min_time:
            return False, f"Date must be at least {min_hours_ahead} hours in the future"
    
    return True, None


def validate_past_date(
    dt: Union[datetime, date],
    allow_today: bool = True
) -> Tuple[bool, Optional[str]]:
    """Validate that date is in the past.
    
    Args:
        dt: Date/datetime to validate
        allow_today: Whether today is considered past
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    now = datetime.utcnow()
    
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, time.max)
        now = now.replace(hour=23, minute=59, second=59)
    
    if allow_today:
        if dt > now:
            return False, "Date must be today or in the past"
    else:
        if dt >= now:
            return False, "Date must be in the past"
    
    return True, None


def validate_business_hours(
    dt: datetime,
    business_hours: Optional[Dict[str, Dict[str, str]]] = None
) -> Tuple[bool, Optional[str]]:
    """Validate that datetime is within business hours.
    
    Args:
        dt: Datetime to validate
        business_hours: Business hours configuration (uses Config.BUSINESS_HOURS if None)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if business_hours is None:
        from ..constants.config import Config
        business_hours = Config.BUSINESS_HOURS
    
    day_name = dt.strftime("%A").lower()
    day_hours = business_hours.get(day_name)
    
    if not day_hours:
        return False, f"Business is closed on {day_name.capitalize()}s"
    
    open_time = datetime.strptime(day_hours['open'], "%H:%M").time()
    close_time = datetime.strptime(day_hours['close'], "%H:%M").time()
    dt_time = dt.time()
    
    if dt_time < open_time or dt_time > close_time:
        return False, f"Business hours are {day_hours['open']} to {day_hours['close']}"
    
    return True, None


def validate_within_business_hours(
    start_time: datetime,
    end_time: datetime,
    business_hours: Optional[Dict[str, Dict[str, str]]] = None
) -> Tuple[bool, Optional[str]]:
    """Validate that a time range is within business hours.
    
    Args:
        start_time: Start time
        end_time: End time
        business_hours: Business hours configuration
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if whole range is within business hours
    current = start_time
    delta = timedelta(minutes=30)  # Check every 30 minutes
    
    while current <= end_time:
        valid, error = validate_business_hours(current, business_hours)
        if not valid:
            return False, f"Time {current.strftime('%Y-%m-%d %H:%M')} is outside business hours"
        current += delta
    
    return True, None


# ============================================================================
# Number Validation
# ============================================================================

def validate_positive_number(
    value: Union[int, float],
    allow_zero: bool = False
) -> Tuple[bool, Optional[str]]:
    """Validate that number is positive.
    
    Args:
        value: Number to validate
        allow_zero: Whether zero is allowed
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(value, (int, float)):
        return False, "Value must be a number"
    
    if allow_zero:
        if value < 0:
            return False, "Value must be zero or positive"
    else:
        if value <= 0:
            return False, "Value must be positive"
    
    return True, None


def validate_range(
    value: Union[int, float],
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    inclusive: bool = True
) -> Tuple[bool, Optional[str]]:
    """Validate that number is within range.
    
    Args:
        value: Number to validate
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        inclusive: Whether bounds are inclusive
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if min_value is not None:
        if inclusive and value < min_value:
            return False, f"Value must be at least {min_value}"
        elif not inclusive and value <= min_value:
            return False, f"Value must be greater than {min_value}"
    
    if max_value is not None:
        if inclusive and value > max_value:
            return False, f"Value must be at most {max_value}"
        elif not inclusive and value >= max_value:
            return False, f"Value must be less than {max_value}"
    
    return True, None


def validate_percentage(value: float, allow_zero: bool = True) -> Tuple[bool, Optional[str]]:
    """Validate percentage value.
    
    Args:
        value: Percentage value (0-100)
        allow_zero: Whether zero is allowed
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if allow_zero:
        if value < 0 or value > 100:
            return False, "Percentage must be between 0 and 100"
    else:
        if value <= 0 or value > 100:
            return False, "Percentage must be between 0 and 100 (exclusive of 0)"
    
    return True, None


def validate_currency(
    amount: float,
    min_amount: float = 0.01,
    max_amount: float = 1000000,
    currency: str = "USD"
) -> Tuple[bool, Optional[str]]:
    """Validate currency amount.
    
    Args:
        amount: Amount to validate
        min_amount: Minimum allowed amount
        max_amount: Maximum allowed amount
        currency: Currency code
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if amount < min_amount:
        return False, f"Amount must be at least {format_currency(min_amount, currency)}"
    
    if amount > max_amount:
        return False, f"Amount cannot exceed {format_currency(max_amount, currency)}"
    
    # Check for too many decimal places
    if abs(amount * 100 - round(amount * 100)) > 0.0001:
        return False, "Amount cannot have more than 2 decimal places"
    
    return True, None


# ============================================================================
# Text Validation
# ============================================================================

def validate_not_empty(value: Any) -> Tuple[bool, Optional[str]]:
    """Validate that value is not empty.
    
    Args:
        value: Value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, "Value is required"
    
    if isinstance(value, str) and not value.strip():
        return False, "Value cannot be empty"
    
    if isinstance(value, (list, dict, tuple)) and len(value) == 0:
        return False, "Value cannot be empty"
    
    return True, None


def validate_length(
    text: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None
) -> Tuple[bool, Optional[str]]:
    """Validate string length.
    
    Args:
        text: String to validate
        min_length: Minimum length
        max_length: Maximum length
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if min_length is not None and len(text) < min_length:
        return False, f"Text must be at least {min_length} characters"
    
    if max_length is not None and len(text) > max_length:
        return False, f"Text must be at most {max_length} characters"
    
    return True, None


def validate_alphanumeric(
    text: str,
    allow_spaces: bool = False,
    allow_dashes: bool = False,
    allow_underscores: bool = False
) -> Tuple[bool, Optional[str]]:
    """Validate alphanumeric string.
    
    Args:
        text: String to validate
        allow_spaces: Allow spaces
        allow_dashes: Allow dashes
        allow_underscores: Allow underscores
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    pattern = r'^[a-zA-Z0-9'
    if allow_spaces:
        pattern += r'\s'
    if allow_dashes:
        pattern += r'\-'
    if allow_underscores:
        pattern += r'_'
    pattern += r']+$'
    
    if not re.match(pattern, text):
        return False, "Text must contain only alphanumeric characters" + \
            (" and spaces" if allow_spaces else "") + \
            (" and dashes" if allow_dashes else "") + \
            (" and underscores" if allow_underscores else "")
    
    return True, None


def validate_no_special_chars(text: str, allowed: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """Validate that text contains no special characters.
    
    Args:
        text: String to validate
        allowed: Optional string of allowed special characters
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if allowed:
        pattern = f'^[a-zA-Z0-9\s{re.escape(allowed)}]+$'
    else:
        pattern = r'^[a-zA-Z0-9\s]+$'
    
    if not re.match(pattern, text):
        return False, "Text contains invalid special characters"
    
    return True, None


def validate_pattern(text: str, pattern: Union[str, Pattern], description: str) -> Tuple[bool, Optional[str]]:
    """Validate string against regex pattern.
    
    Args:
        text: String to validate
        pattern: Regex pattern
        description: Human-readable description of expected format
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    
    if not pattern.match(text):
        return False, f"Invalid format. Expected: {description}"
    
    return True, None


# ============================================================================
# URL Validation
# ============================================================================

def validate_url(url: str, require_https: bool = False) -> Tuple[bool, Optional[str]]:
    """Validate URL.
    
    Args:
        url: URL to validate
        require_https: Whether HTTPS is required
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL is required"
    
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False, "Invalid URL format"
        
        if require_https and result.scheme != 'https':
            return False, "HTTPS is required"
        
        # Check for valid domain
        if '.' not in result.netloc:
            return False, "Invalid domain"
        
        return True, None
        
    except Exception:
        return False, "Invalid URL format"


def validate_image_url(url: str, require_https: bool = True) -> Tuple[bool, Optional[str]]:
    """Validate image URL.
    
    Args:
        url: Image URL to validate
        require_https: Whether HTTPS is required
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid, error = validate_url(url, require_https)
    if not valid:
        return False, error
    
    # Check for common image extensions
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg')
    if not url.lower().endswith(image_extensions):
        return False, "URL must point to an image file (jpg, png, gif, etc.)"
    
    return True, None


# ============================================================================
# ID Validation
# ============================================================================

def validate_id(
    id_value: Any,
    id_type: str,
    min_value: int = 1,
    max_value: int = 2**31 - 1
) -> Tuple[bool, Optional[str]]:
    """Validate ID value.
    
    Args:
        id_value: ID to validate
        id_type: Type of ID (user, reservation, etc.)
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if id_value is None:
        return False, f"{id_type.capitalize()} ID is required"
    
    if not isinstance(id_value, int):
        try:
            id_value = int(id_value)
        except (ValueError, TypeError):
            return False, f"{id_type.capitalize()} ID must be an integer"
    
    if id_value < min_value or id_value > max_value:
        return False, f"{id_type.capitalize()} ID must be between {min_value} and {max_value}"
    
    return True, None


def validate_user_id(user_id: Any) -> Tuple[bool, Optional[str]]:
    """Validate user ID."""
    return validate_id(user_id, "user")


def validate_reservation_id(reservation_id: Any) -> Tuple[bool, Optional[str]]:
    """Validate reservation ID."""
    return validate_id(reservation_id, "reservation")


def validate_spot_id(spot_id: Any) -> Tuple[bool, Optional[str]]:
    """Validate parking spot ID."""
    return validate_id(spot_id, "parking spot")


def validate_vehicle_id(vehicle_id: Any) -> Tuple[bool, Optional[str]]:
    """Validate vehicle ID."""
    return validate_id(vehicle_id, "vehicle")


def validate_payment_id(payment_id: Any) -> Tuple[bool, Optional[str]]:
    """Validate payment ID."""
    return validate_id(payment_id, "payment")


# ============================================================================
# Business Rules Validation
# ============================================================================

def validate_reservation_time(
    start_time: datetime,
    end_time: datetime,
    min_duration: Optional[timedelta] = None,
    max_duration: Optional[timedelta] = None,
    min_advance: Optional[timedelta] = None,
    max_advance: Optional[timedelta] = None
) -> Tuple[bool, List[str]]:
    """Validate reservation time against business rules.
    
    Args:
        start_time: Reservation start time
        end_time: Reservation end time
        min_duration: Minimum allowed duration
        max_duration: Maximum allowed duration
        min_advance: Minimum advance booking time
        max_advance: Maximum advance booking time
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    now = datetime.utcnow()
    
    # Validate range
    valid, error = validate_date_range(start_time, end_time, allow_equal=False)
    if not valid:
        errors.append(error)
    
    # Validate duration
    if min_duration or max_duration:
        valid, error = validate_date_range(
            start_time, end_time,
            min_duration=min_duration,
            max_duration=max_duration
        )
        if not valid:
            errors.append(error)
    
    # Validate advance booking
    if min_advance:
        if start_time < now + min_advance:
            errors.append(f"Reservations must be made at least {min_advance} in advance")
    
    if max_advance:
        if start_time > now + max_advance:
            errors.append(f"Reservations cannot be made more than {max_advance} in advance")
    
    return len(errors) == 0, errors


def validate_cancellation_window(
    start_time: datetime,
    cancellation_window: timedelta,
    allow_admin_override: bool = False,
    user_role: Optional[UserRole] = None
) -> Tuple[bool, Optional[str]]:
    """Validate that cancellation is within allowed window.
    
    Args:
        start_time: Reservation start time
        cancellation_window: Allowed cancellation window before start
        allow_admin_override: Whether admin can override
        user_role: User role for override check
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    now = datetime.utcnow()
    cancellation_deadline = start_time - cancellation_window
    
    if now > cancellation_deadline:
        if allow_admin_override and user_role in [UserRole.ADMIN, UserRole.MANAGER]:
            return True, None
        return False, f"Cancellations must be made at least {cancellation_window} before start time"
    
    return True, None


def validate_spot_compatibility(
    spot_type: ParkingSpotType,
    vehicle_type: VehicleType,
    vehicle_metadata: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Optional[str]]:
    """Validate that parking spot is compatible with vehicle.
    
    Args:
        spot_type: Type of parking spot
        vehicle_type: Type of vehicle
        vehicle_metadata: Additional vehicle metadata (height, length, etc.)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Define compatibility matrix
    compatibility = {
        VehicleType.MOTORCYCLE: [ParkingSpotType.STANDARD, ParkingSpotType.MOTORCYCLE],
        VehicleType.SEDAN: [ParkingSpotType.STANDARD, ParkingSpotType.VIP],
        VehicleType.SUV: [ParkingSpotType.STANDARD, ParkingSpotType.VIP, ParkingSpotType.OVERSIZE],
        VehicleType.TRUCK: [ParkingSpotType.STANDARD, ParkingSpotType.OVERSIZE],
        VehicleType.VAN: [ParkingSpotType.STANDARD, ParkingSpotType.OVERSIZE],
        VehicleType.RV: [ParkingSpotType.OVERSIZE],
    }
    
    allowed_spots = compatibility.get(vehicle_type, [])
    if spot_type not in allowed_spots:
        return False, f"Vehicle type {vehicle_type.value} is not compatible with {spot_type.value} spots"
    
    # Check special requirements
    if spot_type == ParkingSpotType.EV_CHARGING and not vehicle_metadata.get('is_electric'):
        return False, "EV charging spots require an electric vehicle"
    
    if spot_type == ParkingSpotType.DISABLED and not vehicle_metadata.get('has_disability_permit'):
        return False, "Disabled spots require a disability permit"
    
    # Check size constraints
    if spot_type == ParkingSpotType.OVERSIZE:
        # Check if vehicle actually needs oversized spot
        if vehicle_type not in [VehicleType.TRUCK, VehicleType.VAN, VehicleType.RV]:
            length = vehicle_metadata.get('length_meters', 0)
            if length < 5.0:  # Less than 5 meters
                return False, "Vehicle does not require an oversized spot"
    
    return True, None


def validate_user_eligibility(
    user_role: UserRole,
    user_status: str,
    required_role: Optional[UserRole] = None,
    allowed_statuses: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """Validate user eligibility for action.
    
    Args:
        user_role: User's role
        user_status: User's account status
        required_role: Required role for action
        allowed_statuses: Allowed account statuses
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    from ..enums import UserStatus
    
    if allowed_statuses is None:
        allowed_statuses = [UserStatus.ACTIVE]
    
    if user_status not in allowed_statuses:
        return False, f"User account is {user_status}. Action not allowed."
    
    if required_role and user_role != required_role:
        if user_role not in [UserRole.ADMIN, UserRole.MANAGER]:  # Admins can override
            return False, f"Action requires {required_role.value} role"
    
    return True, None


# ============================================================================
# Schema Validation
# ============================================================================

def validate_json_schema(data: Dict, schema: Dict) -> Tuple[bool, List[str]]:
    """Validate data against JSON schema.
    
    Args:
        data: Data to validate
        schema: JSON schema
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    try:
        import jsonschema
        jsonschema.validate(data, schema)
        return True, []
    except ImportError:
        logger.warning("jsonschema library not available. Skipping schema validation.")
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Schema validation error: {str(e)}"]


def validate_dict_structure(
    data: Dict,
    required_fields: List[str],
    optional_fields: Optional[List[str]] = None,
    field_types: Optional[Dict[str, type]] = None
) -> Tuple[bool, List[str]]:
    """Validate dictionary structure.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        optional_fields: List of optional field names
        field_types: Dictionary mapping field names to expected types
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif data[field] is None:
            errors.append(f"Field cannot be null: {field}")
    
    # Check for unknown fields
    allowed_fields = set(required_fields + (optional_fields or []))
    unknown_fields = set(data.keys()) - allowed_fields
    if unknown_fields:
        errors.append(f"Unknown fields: {', '.join(unknown_fields)}")
    
    # Check field types
    if field_types:
        for field, expected_type in field_types.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    errors.append(
                        f"Field '{field}' must be of type {expected_type.__name__}, "
                        f"got {type(data[field]).__name__}"
                    )
    
    return len(errors) == 0, errors


def validate_required_fields(data: Dict, required_fields: List[str]) -> Tuple[bool, List[str]]:
    """Validate that all required fields are present.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    return validate_dict_structure(data, required_fields)


# ============================================================================
# Helper function for formatting currency (used in validate_currency)
# ============================================================================

def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount (simple version)."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
    symbol = symbols.get(currency, "$")
    return f"{symbol}{amount:.2f}"