"""Data validators for the parking management system.

This module provides comprehensive validation functions and classes for
all data types used in the application, including input validation,
business rule validation, and schema validation.
"""

import re
import json
from datetime import datetime, date, time, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from decimal import Decimal
from email_validator import validate_email, EmailNotValidError
import phonenumbers
from dateutil import parser
import uuid

# ============================================================================
# Base Validator Classes
# ============================================================================

class ValidationError(Exception):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None, code: Optional[str] = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class ValidationResult:
    """Result of a validation operation."""
    
    def __init__(self, is_valid: bool = True, errors: Optional[Dict[str, List[str]]] = None):
        self.is_valid = is_valid
        self.errors = errors or {}
    
    def add_error(self, field: str, message: str):
        """Add an error for a field."""
        if field not in self.errors:
            self.errors[field] = []
        self.errors[field].append(message)
        self.is_valid = False
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result."""
        if not other.is_valid:
            self.is_valid = False
            for field, errors in other.errors.items():
                if field not in self.errors:
                    self.errors[field] = []
                self.errors[field].extend(errors)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors
        }
    
    def __bool__(self) -> bool:
        return self.is_valid


class BaseValidator:
    """Base class for validators."""
    
    def __init__(self, field_name: Optional[str] = None, required: bool = True):
        self.field_name = field_name
        self.required = required
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        """Validate a value."""
        result = ValidationResult()
        
        # Check required
        if self.required and (value is None or value == ''):
            result.add_error(self.field_name or 'value', 'This field is required')
            return result
        
        # Skip further validation if value is None and not required
        if value is None or value == '':
            return result
        
        return result
    
    def __call__(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        return self.validate(value, context)


# ============================================================================
# Type Validators
# ============================================================================

class StringValidator(BaseValidator):
    """Validator for string values."""
    
    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        allowed_values: Optional[List[str]] = None,
        strip: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None
        self.allowed_values = allowed_values
        self.strip = strip
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Convert to string if needed
        if not isinstance(value, str):
            try:
                value = str(value)
            except:
                result.add_error(self.field_name or 'value', 'Must be a string')
                return result
        
        # Strip if requested
        if self.strip:
            value = value.strip()
        
        # Check min length
        if self.min_length is not None and len(value) < self.min_length:
            result.add_error(
                self.field_name or 'value',
                f'Must be at least {self.min_length} characters long'
            )
        
        # Check max length
        if self.max_length is not None and len(value) > self.max_length:
            result.add_error(
                self.field_name or 'value',
                f'Must be at most {self.max_length} characters long'
            )
        
        # Check pattern
        if self.pattern and not self.pattern.match(value):
            result.add_error(
                self.field_name or 'value',
                'Invalid format'
            )
        
        # Check allowed values
        if self.allowed_values and value not in self.allowed_values:
            result.add_error(
                self.field_name or 'value',
                f'Must be one of: {", ".join(self.allowed_values)}'
            )
        
        return result


class IntegerValidator(BaseValidator):
    """Validator for integer values."""
    
    def __init__(
        self,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        positive_only: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value
        self.positive_only = positive_only
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Convert to int if possible
        if not isinstance(value, int):
            try:
                value = int(value)
            except (ValueError, TypeError):
                result.add_error(self.field_name or 'value', 'Must be an integer')
                return result
        
        # Check positive only
        if self.positive_only and value <= 0:
            result.add_error(self.field_name or 'value', 'Must be a positive integer')
        
        # Check min value
        if self.min_value is not None and value < self.min_value:
            result.add_error(
                self.field_name or 'value',
                f'Must be at least {self.min_value}'
            )
        
        # Check max value
        if self.max_value is not None and value > self.max_value:
            result.add_error(
                self.field_name or 'value',
                f'Must be at most {self.max_value}'
            )
        
        return result


class FloatValidator(BaseValidator):
    """Validator for float/decimal values."""
    
    def __init__(
        self,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        positive_only: bool = False,
        allow_infinity: bool = False,
        decimal_places: Optional[int] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value
        self.positive_only = positive_only
        self.allow_infinity = allow_infinity
        self.decimal_places = decimal_places
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Convert to float if possible
        if not isinstance(value, (float, int, Decimal)):
            try:
                value = float(value)
            except (ValueError, TypeError):
                result.add_error(self.field_name or 'value', 'Must be a number')
                return result
        
        # Convert Decimal to float
        if isinstance(value, Decimal):
            value = float(value)
        
        # Check infinity
        if not self.allow_infinity and (value == float('inf') or value == float('-inf')):
            result.add_error(self.field_name or 'value', 'Infinity not allowed')
        
        # Check positive only
        if self.positive_only and value <= 0:
            result.add_error(self.field_name or 'value', 'Must be a positive number')
        
        # Check min value
        if self.min_value is not None and value < self.min_value:
            result.add_error(
                self.field_name or 'value',
                f'Must be at least {self.min_value}'
            )
        
        # Check max value
        if self.max_value is not None and value > self.max_value:
            result.add_error(
                self.field_name or 'value',
                f'Must be at most {self.max_value}'
            )
        
        # Check decimal places
        if self.decimal_places is not None:
            str_value = str(value)
            if '.' in str_value:
                places = len(str_value.split('.')[1])
                if places > self.decimal_places:
                    result.add_error(
                        self.field_name or 'value',
                        f'Must have at most {self.decimal_places} decimal places'
                    )
        
        return result


class BooleanValidator(BaseValidator):
    """Validator for boolean values."""
    
    def __init__(self, strict: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.strict = strict
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        if self.strict:
            if not isinstance(value, bool):
                result.add_error(self.field_name or 'value', 'Must be a boolean')
        else:
            # Accept common truthy/falsy values
            truthy = ['true', '1', 'yes', 'on', 1, 1.0, True]
            falsy = ['false', '0', 'no', 'off', 0, 0.0, False, None]
            
            if value in truthy:
                value = True
            elif value in falsy:
                value = False
            else:
                result.add_error(self.field_name or 'value', 'Must be a boolean value')
        
        return result


class DateValidator(BaseValidator):
    """Validator for date values."""
    
    def __init__(
        self,
        min_date: Optional[Union[date, str]] = None,
        max_date: Optional[Union[date, str]] = None,
        future_only: bool = False,
        past_only: bool = False,
        format: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.min_date = min_date
        self.max_date = max_date
        self.future_only = future_only
        self.past_only = past_only
        self.format = format
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Parse date
        if isinstance(value, str):
            try:
                if self.format:
                    value = datetime.strptime(value, self.format).date()
                else:
                    value = parser.parse(value).date()
            except (ValueError, TypeError):
                result.add_error(self.field_name or 'value', 'Invalid date format')
                return result
        elif isinstance(value, datetime):
            value = value.date()
        elif not isinstance(value, date):
            result.add_error(self.field_name or 'value', 'Must be a date')
            return result
        
        # Check future only
        if self.future_only and value <= date.today():
            result.add_error(self.field_name or 'value', 'Must be a future date')
        
        # Check past only
        if self.past_only and value >= date.today():
            result.add_error(self.field_name or 'value', 'Must be a past date')
        
        # Parse min/max dates if they're strings
        min_date = self.min_date
        if isinstance(min_date, str):
            min_date = parser.parse(min_date).date()
        
        max_date = self.max_date
        if isinstance(max_date, str):
            max_date = parser.parse(max_date).date()
        
        # Check min date
        if min_date and value < min_date:
            result.add_error(
                self.field_name or 'value',
                f'Must be on or after {min_date.isoformat()}'
            )
        
        # Check max date
        if max_date and value > max_date:
            result.add_error(
                self.field_name or 'value',
                f'Must be on or before {max_date.isoformat()}'
            )
        
        return result


class DateTimeValidator(BaseValidator):
    """Validator for datetime values."""
    
    def __init__(
        self,
        min_datetime: Optional[Union[datetime, str]] = None,
        max_datetime: Optional[Union[datetime, str]] = None,
        future_only: bool = False,
        past_only: bool = False,
        tz_aware: Optional[bool] = None,
        format: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.min_datetime = min_datetime
        self.max_datetime = max_datetime
        self.future_only = future_only
        self.past_only = past_only
        self.tz_aware = tz_aware
        self.format = format
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Parse datetime
        if isinstance(value, str):
            try:
                if self.format:
                    value = datetime.strptime(value, self.format)
                else:
                    value = parser.parse(value)
            except (ValueError, TypeError):
                result.add_error(self.field_name or 'value', 'Invalid datetime format')
                return result
        elif not isinstance(value, datetime):
            result.add_error(self.field_name or 'value', 'Must be a datetime')
            return result
        
        # Check timezone awareness
        if self.tz_aware is not None:
            is_tz_aware = value.tzinfo is not None
            if self.tz_aware and not is_tz_aware:
                result.add_error(self.field_name or 'value', 'Must be timezone-aware')
            elif not self.tz_aware and is_tz_aware:
                result.add_error(self.field_name or 'value', 'Must be timezone-naive')
        
        now = datetime.now(value.tzinfo) if value.tzinfo else datetime.now()
        
        # Check future only
        if self.future_only and value <= now:
            result.add_error(self.field_name or 'value', 'Must be a future datetime')
        
        # Check past only
        if self.past_only and value >= now:
            result.add_error(self.field_name or 'value', 'Must be a past datetime')
        
        # Parse min/max datetimes if they're strings
        min_dt = self.min_datetime
        if isinstance(min_dt, str):
            min_dt = parser.parse(min_dt)
        
        max_dt = self.max_datetime
        if isinstance(max_dt, str):
            max_dt = parser.parse(max_dt)
        
        # Check min datetime
        if min_dt and value < min_dt:
            result.add_error(
                self.field_name or 'value',
                f'Must be on or after {min_dt.isoformat()}'
            )
        
        # Check max datetime
        if max_dt and value > max_dt:
            result.add_error(
                self.field_name or 'value',
                f'Must be on or before {max_dt.isoformat()}'
            )
        
        return result


class TimeValidator(BaseValidator):
    """Validator for time values."""
    
    def __init__(
        self,
        min_time: Optional[Union[time, str]] = None,
        max_time: Optional[Union[time, str]] = None,
        format: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.min_time = min_time
        self.max_time = max_time
        self.format = format
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Parse time
        if isinstance(value, str):
            try:
                if self.format:
                    value = datetime.strptime(value, self.format).time()
                else:
                    # Try common formats
                    for fmt in ['%H:%M', '%H:%M:%S', '%I:%M %p']:
                        try:
                            value = datetime.strptime(value, fmt).time()
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError()
            except (ValueError, TypeError):
                result.add_error(self.field_name or 'value', 'Invalid time format')
                return result
        elif not isinstance(value, time):
            result.add_error(self.field_name or 'value', 'Must be a time')
            return result
        
        # Parse min/max times if they're strings
        min_time = self.min_time
        if isinstance(min_time, str):
            min_time = parser.parse(min_time).time()
        
        max_time = self.max_time
        if isinstance(max_time, str):
            max_time = parser.parse(max_time).time()
        
        # Check min time
        if min_time and value < min_time:
            result.add_error(
                self.field_name or 'value',
                f'Must be on or after {min_time.isoformat()}'
            )
        
        # Check max time
        if max_time and value > max_time:
            result.add_error(
                self.field_name or 'value',
                f'Must be on or before {max_time.isoformat()}'
            )
        
        return result


class UUIDValidator(BaseValidator):
    """Validator for UUID values."""
    
    def __init__(self, version: Optional[int] = None, **kwargs):
        super().__init__(**kwargs)
        self.version = version
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Convert string to UUID
        if isinstance(value, str):
            try:
                value = uuid.UUID(value)
            except ValueError:
                result.add_error(self.field_name or 'value', 'Invalid UUID format')
                return result
        elif not isinstance(value, uuid.UUID):
            result.add_error(self.field_name or 'value', 'Must be a UUID')
            return result
        
        # Check version
        if self.version and value.version != self.version:
            result.add_error(
                self.field_name or 'value',
                f'Must be UUID version {self.version}'
            )
        
        return result


# ============================================================================
# Collection Validators
# ============================================================================

class ListValidator(BaseValidator):
    """Validator for lists."""
    
    def __init__(
        self,
        item_validator: Optional[BaseValidator] = None,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        unique: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.item_validator = item_validator
        self.min_items = min_items
        self.max_items = max_items
        self.unique = unique
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        if not isinstance(value, (list, tuple)):
            result.add_error(self.field_name or 'value', 'Must be a list')
            return result
        
        # Check min items
        if self.min_items is not None and len(value) < self.min_items:
            result.add_error(
                self.field_name or 'value',
                f'Must have at least {self.min_items} items'
            )
        
        # Check max items
        if self.max_items is not None and len(value) > self.max_items:
            result.add_error(
                self.field_name or 'value',
                f'Must have at most {self.max_items} items'
            )
        
        # Check uniqueness
        if self.unique and len(value) != len(set(value)):
            result.add_error(self.field_name or 'value', 'Items must be unique')
        
        # Validate each item
        if self.item_validator:
            for i, item in enumerate(value):
                item_result = self.item_validator.validate(item, context)
                if not item_result:
                    for field, errors in item_result.errors.items():
                        for error in errors:
                            result.add_error(f"{self.field_name}[{i}].{field}", error)
        
        return result


class DictValidator(BaseValidator):
    """Validator for dictionaries."""
    
    def __init__(
        self,
        schema: Optional[Dict[str, BaseValidator]] = None,
        allow_extra: bool = False,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.schema = schema or {}
        self.allow_extra = allow_extra
        self.min_items = min_items
        self.max_items = max_items
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        if not isinstance(value, dict):
            result.add_error(self.field_name or 'value', 'Must be a dictionary')
            return result
        
        # Check min items
        if self.min_items is not None and len(value) < self.min_items:
            result.add_error(
                self.field_name or 'value',
                f'Must have at least {self.min_items} keys'
            )
        
        # Check max items
        if self.max_items is not None and len(value) > self.max_items:
            result.add_error(
                self.field_name or 'value',
                f'Must have at most {self.max_items} keys'
            )
        
        # Check for extra keys
        if not self.allow_extra:
            extra_keys = set(value.keys()) - set(self.schema.keys())
            if extra_keys:
                result.add_error(
                    self.field_name or 'value',
                    f'Unexpected keys: {", ".join(extra_keys)}'
                )
        
        # Validate each field
        for field, validator in self.schema.items():
            field_value = value.get(field)
            field_result = validator.validate(field_value, context)
            if not field_result:
                for subfield, errors in field_result.errors.items():
                    for error in errors:
                        if subfield == field:
                            result.add_error(f"{field}", error)
                        else:
                            result.add_error(f"{field}.{subfield}", error)
        
        return result


# ============================================================================
# Specialized Validators
# ============================================================================

class EmailValidator(StringValidator):
    """Validator for email addresses."""
    
    def __init__(self, check_deliverability: bool = False, **kwargs):
        super().__init__(
            min_length=3,
            max_length=255,
            pattern=r'^[^@]+@[^@]+\.[^@]+$',
            **kwargs
        )
        self.check_deliverability = check_deliverability
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        try:
            email_info = validate_email(
                value,
                check_deliverability=self.check_deliverability
            )
            # Normalize email
            normalized = email_info.normalized
        except EmailNotValidError as e:
            result.add_error(self.field_name or 'value', str(e))
        
        return result


class PhoneValidator(BaseValidator):
    """Validator for phone numbers."""
    
    def __init__(
        self,
        region: str = "US",
        format: str = "international",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.region = region
        self.format = format
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        try:
            phone_number = phonenumbers.parse(value, self.region)
            if not phonenumbers.is_valid_number(phone_number):
                result.add_error(self.field_name or 'value', 'Invalid phone number')
        except phonenumbers.NumberParseException as e:
            result.add_error(self.field_name or 'value', str(e))
        
        return result


class PasswordValidator(StringValidator):
    """Validator for passwords."""
    
    def __init__(
        self,
        min_length: int = 8,
        max_length: int = 128,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_numbers: bool = True,
        require_special: bool = True,
        forbidden_patterns: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(min_length=min_length, max_length=max_length, **kwargs)
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_numbers = require_numbers
        self.require_special = require_special
        self.forbidden_patterns = forbidden_patterns or []
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Check uppercase
        if self.require_uppercase and not re.search(r'[A-Z]', value):
            result.add_error(
                self.field_name or 'value',
                'Must contain at least one uppercase letter'
            )
        
        # Check lowercase
        if self.require_lowercase and not re.search(r'[a-z]', value):
            result.add_error(
                self.field_name or 'value',
                'Must contain at least one lowercase letter'
            )
        
        # Check numbers
        if self.require_numbers and not re.search(r'[0-9]', value):
            result.add_error(
                self.field_name or 'value',
                'Must contain at least one number'
            )
        
        # Check special characters
        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            result.add_error(
                self.field_name or 'value',
                'Must contain at least one special character'
            )
        
        # Check forbidden patterns
        for pattern in self.forbidden_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                result.add_error(
                    self.field_name or 'value',
                    f'Contains forbidden pattern: {pattern}'
                )
        
        return result


class CreditCardValidator(StringValidator):
    """Validator for credit card numbers."""
    
    CARD_PATTERNS = {
        'visa': r'^4[0-9]{12}(?:[0-9]{3})?$',
        'mastercard': r'^5[1-5][0-9]{14}$',
        'amex': r'^3[47][0-9]{13}$',
        'discover': r'^6(?:011|5[0-9]{2})[0-9]{12}$',
        'diners': r'^3(?:0[0-5]|[68][0-9])[0-9]{11}$',
        'jcb': r'^(?:2131|1800|35\d{3})\d{11}$',
    }
    
    def __init__(
        self,
        card_types: Optional[List[str]] = None,
        validate_luhn: bool = True,
        **kwargs
    ):
        super().__init__(
            min_length=13,
            max_length=19,
            pattern=r'^[0-9\s\-]+$',
            **kwargs
        )
        self.card_types = card_types or list(self.CARD_PATTERNS.keys())
        self.validate_luhn = validate_luhn
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        # Remove spaces and dashes
        if isinstance(value, str):
            value = re.sub(r'[\s\-]', '', value)
        
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Check card type
        card_type = self._detect_card_type(value)
        if not card_type:
            result.add_error(self.field_name or 'value', 'Unknown card type')
        elif card_type not in self.card_types:
            result.add_error(
                self.field_name or 'value',
                f'Card type {card_type} not accepted'
            )
        
        # Validate Luhn algorithm
        if self.validate_luhn and not self._luhn_check(value):
            result.add_error(self.field_name or 'value', 'Invalid card number')
        
        return result
    
    def _detect_card_type(self, card_number: str) -> Optional[str]:
        """Detect card type from number."""
        for card_type, pattern in self.CARD_PATTERNS.items():
            if re.match(pattern, card_number):
                return card_type
        return None
    
    def _luhn_check(self, card_number: str) -> bool:
        """Validate using Luhn algorithm."""
        digits = [int(d) for d in card_number if d.isdigit()]
        if len(digits) < 13:
            return False
        
        check_sum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            check_sum += digit
        
        return check_sum % 10 == 0


class LicensePlateValidator(StringValidator):
    """Validator for license plates."""
    
    # Common US license plate patterns by state
    STATE_PATTERNS = {
        'CA': r'^[0-9A-Z]{1,7}$',
        'NY': r'^[A-Z]{3}[0-9]{4}$',
        'TX': r'^[0-9A-Z]{2,7}$',
        'FL': r'^[A-Z0-9]{1,7}$',
        'IL': r'^[0-9]{1,6}$',
        'PA': r'^[A-Z]{3}[0-9]{4}$',
        'OH': r'^[A-Z]{3}[0-9]{4}$',
        'MI': r'^[A-Z0-9]{1,7}$',
        'NJ': r'^[A-Z]{3}[0-9]{3}[A-Z]?$',
        'GA': r'^[A-Z]{3}[0-9]{4}$',
        'NC': r'^[A-Z]{3}[0-9]{4}$',
        'VA': r'^[A-Z]{3}[0-9]{4}$',
    }
    
    def __init__(
        self,
        state: Optional[str] = None,
        allow_vanity: bool = True,
        **kwargs
    ):
        super().__init__(
            min_length=1,
            max_length=10,
            pattern=r'^[A-Z0-9\s\-]+$',
            **kwargs
        )
        self.state = state
        self.allow_vanity = allow_vanity
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        # Normalize
        if isinstance(value, str):
            value = value.upper().strip()
            value = re.sub(r'[\s\-]', '', value)
        
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Check state-specific pattern
        if self.state and self.state in self.STATE_PATTERNS:
            pattern = self.STATE_PATTERNS[self.state]
            if not re.match(pattern, value):
                result.add_error(
                    self.field_name or 'value',
                    f'Invalid format for {self.state} license plate'
                )
        
        return result


class URLValidator(StringValidator):
    """Validator for URLs."""
    
    def __init__(
        self,
        schemes: Optional[List[str]] = None,
        allow_local: bool = False,
        **kwargs
    ):
        super().__init__(max_length=2048, **kwargs)
        self.schemes = schemes or ['http', 'https']
        self.allow_local = allow_local
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Check scheme
        scheme = value.split('://')[0].lower() if '://' in value else None
        if scheme not in self.schemes:
            result.add_error(
                self.field_name or 'value',
                f'URL scheme must be one of: {", ".join(self.schemes)}'
            )
        
        # Basic URL validation
        pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
        if not re.match(pattern, value):
            result.add_error(self.field_name or 'value', 'Invalid URL format')
        
        # Check for local addresses
        if not self.allow_local:
            local_patterns = [
                r'localhost',
                r'127\.0\.0\.1',
                r'192\.168\.',
                r'10\.',
                r'172\.(1[6-9]|2[0-9]|3[0-1])\.',
            ]
            for pattern in local_patterns:
                if re.search(pattern, value):
                    result.add_error(self.field_name or 'value', 'Local URLs not allowed')
                    break
        
        return result


class JSONValidator(BaseValidator):
    """Validator for JSON data."""
    
    def __init__(
        self,
        schema: Optional[Dict] = None,
        validate_schema: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.schema = schema
        self.validate_schema = validate_schema
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Parse JSON string
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as e:
                result.add_error(self.field_name or 'value', f'Invalid JSON: {str(e)}')
                return result
        
        # Validate against schema
        if self.validate_schema and self.schema:
            from jsonschema import validate, ValidationError as JsonSchemaError
            try:
                validate(instance=value, schema=self.schema)
            except JsonSchemaError as e:
                result.add_error(self.field_name or 'value', f'Schema validation failed: {str(e)}')
        
        return result


# ============================================================================
# Business Rule Validators
# ============================================================================

class ReservationValidator:
    """Validator for reservation business rules."""
    
    @staticmethod
    def validate_time_range(
        start_time: datetime,
        end_time: datetime,
        min_duration: Optional[timedelta] = None,
        max_duration: Optional[timedelta] = None,
        advance_booking_limit: Optional[timedelta] = None
    ) -> ValidationResult:
        """Validate reservation time range."""
        result = ValidationResult()
        now = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
        
        # Check start before end
        if start_time >= end_time:
            result.add_error('time_range', 'End time must be after start time')
        
        # Check minimum duration
        if min_duration and (end_time - start_time) < min_duration:
            result.add_error('time_range', f'Minimum duration is {min_duration}')
        
        # Check maximum duration
        if max_duration and (end_time - start_time) > max_duration:
            result.add_error('time_range', f'Maximum duration is {max_duration}')
        
        # Check advance booking limit
        if advance_booking_limit and (start_time - now) > advance_booking_limit:
            result.add_error('time_range', f'Cannot book more than {advance_booking_limit} in advance')
        
        return result
    
    @staticmethod
    def validate_cancellation(
        start_time: datetime,
        cancellation_window: timedelta
    ) -> ValidationResult:
        """Validate if reservation can be cancelled."""
        result = ValidationResult()
        now = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
        
        if start_time - now < cancellation_window:
            result.add_error(
                'cancellation',
                f'Must cancel at least {cancellation_window} before start time'
            )
        
        return result
    
    @staticmethod
    def validate_checkin(
        start_time: datetime,
        grace_period: timedelta,
        early_checkin_allowed: bool = False
    ) -> ValidationResult:
        """Validate check-in time."""
        result = ValidationResult()
        now = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
        
        if now < start_time and not early_checkin_allowed:
            result.add_error('checkin', 'Cannot check in before start time')
        
        if now > start_time + grace_period:
            result.add_error('checkin', f'Check-in grace period of {grace_period} exceeded')
        
        return result


class PaymentValidator:
    """Validator for payment business rules."""
    
    @staticmethod
    def validate_amount(
        amount: float,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        currency: str = "USD"
    ) -> ValidationResult:
        """Validate payment amount."""
        result = ValidationResult()
        
        if amount <= 0:
            result.add_error('amount', 'Amount must be positive')
        
        if min_amount and amount < min_amount:
            result.add_error('amount', f'Minimum amount is {currency} {min_amount}')
        
        if max_amount and amount > max_amount:
            result.add_error('amount', f'Maximum amount is {currency} {max_amount}')
        
        return result
    
    @staticmethod
    def validate_refund(
        refund_amount: float,
        original_amount: float,
        max_refund_days: Optional[int] = None,
        transaction_date: Optional[datetime] = None
    ) -> ValidationResult:
        """Validate refund."""
        result = ValidationResult()
        
        if refund_amount <= 0:
            result.add_error('refund_amount', 'Refund amount must be positive')
        
        if refund_amount > original_amount:
            result.add_error('refund_amount', 'Refund amount cannot exceed original amount')
        
        if max_refund_days and transaction_date:
            days_since = (datetime.now() - transaction_date).days
            if days_since > max_refund_days:
                result.add_error(
                    'refund',
                    f'Refund window of {max_refund_days} days exceeded'
                )
        
        return result


class UserValidator:
    """Validator for user business rules."""
    
    @staticmethod
    def validate_age(
        birth_date: date,
        min_age: int = 18,
        max_age: Optional[int] = None
    ) -> ValidationResult:
        """Validate user age."""
        result = ValidationResult()
        today = date.today()
        age = today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
        
        if age < min_age:
            result.add_error('age', f'Must be at least {min_age} years old')
        
        if max_age and age > max_age:
            result.add_error('age', f'Must be at most {max_age} years old')
        
        return result
    
    @staticmethod
    def validate_membership_level(
        current_level: str,
        requested_level: str,
        allowed_upgrades: Dict[str, List[str]]
    ) -> ValidationResult:
        """Validate membership level change."""
        result = ValidationResult()
        
        if requested_level not in allowed_upgrades.get(current_level, []):
            result.add_error(
                'membership_level',
                f'Cannot upgrade from {current_level} to {requested_level}'
            )
        
        return result


class ParkingSpotValidator:
    """Validator for parking spot business rules."""
    
    @staticmethod
    def validate_spot_for_vehicle(
        spot_type: str,
        vehicle_type: str,
        is_ev: bool,
        spot_features: List[str]
    ) -> ValidationResult:
        """Validate if spot is suitable for vehicle."""
        result = ValidationResult()
        
        # EV charging check
        if is_ev and 'ev_charging' not in spot_features:
            result.add_error('spot', 'EV vehicles require charging spots')
        
        # Vehicle type compatibility
        incompatible = {
            'oversize': ['compact', 'motorcycle'],
            'compact': ['oversize'],
            'motorcycle': ['oversize']
        }
        
        if vehicle_type in incompatible and spot_type in incompatible.get(vehicle_type, []):
            result.add_error('spot', f'{vehicle_type} vehicles cannot use {spot_type} spots')
        
        return result
    
    @staticmethod
    def validate_maintenance_schedule(
        last_maintenance: Optional[date],
        maintenance_interval_days: int
    ) -> ValidationResult:
        """Validate if maintenance is needed."""
        result = ValidationResult()
        
        if last_maintenance:
            days_since = (date.today() - last_maintenance).days
            if days_since > maintenance_interval_days:
                result.add_error(
                    'maintenance',
                    f'Maintenance overdue by {days_since - maintenance_interval_days} days'
                )
        
        return result


# ============================================================================
# Composite Validators
# ============================================================================

class SchemaValidator:
    """Validator for complex schemas."""
    
    def __init__(self, schema: Dict[str, BaseValidator]):
        self.schema = schema
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate data against schema."""
        return DictValidator(schema=self.schema).validate(data)
    
    def validate_partial(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate partial data (optional fields)."""
        # Create copy of schema with all fields optional
        optional_schema = {}
        for field, validator in self.schema.items():
            validator_copy = validator.__class__(**{
                k: v for k, v in validator.__dict__.items()
                if k not in ['required', 'field_name']
            })
            validator_copy.required = False
            optional_schema[field] = validator_copy
        
        return DictValidator(schema=optional_schema, allow_extra=True).validate(data)


class ConditionalValidator(BaseValidator):
    """Validator that applies different rules based on conditions."""
    
    def __init__(
        self,
        conditions: List[Tuple[Callable, BaseValidator]],
        default_validator: Optional[BaseValidator] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.conditions = conditions
        self.default_validator = default_validator
    
    def validate(self, value: Any, context: Optional[Dict] = None) -> ValidationResult:
        result = super().validate(value, context)
        if not result or value is None:
            return result
        
        # Find first matching condition
        for condition, validator in self.conditions:
            if condition(context or {}):
                return validator.validate(value, context)
        
        # Use default validator if no condition matches
        if self.default_validator:
            return self.default_validator.validate(value, context)
        
        return result


# ============================================================================
# Utility Functions
# ============================================================================

def validate(data: Any, validator: BaseValidator) -> ValidationResult:
    """Convenience function to validate data."""
    return validator.validate(data)


def validate_schema(data: Dict[str, Any], schema: Dict[str, BaseValidator]) -> ValidationResult:
    """Convenience function to validate against a schema."""
    return SchemaValidator(schema).validate(data)


def is_valid(data: Any, validator: BaseValidator) -> bool:
    """Check if data is valid."""
    return validator.validate(data).is_valid


def clean_data(data: Dict[str, Any], schema: Dict[str, BaseValidator]) -> Dict[str, Any]:
    """Clean and validate data, returning only valid fields."""
    result = {}
    for field, validator in schema.items():
        if field in data:
            if is_valid(data[field], validator):
                result[field] = data[field]
    return result


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Exceptions
    'ValidationError',
    
    # Results
    'ValidationResult',
    
    # Base classes
    'BaseValidator',
    
    # Type validators
    'StringValidator',
    'IntegerValidator',
    'FloatValidator',
    'BooleanValidator',
    'DateValidator',
    'DateTimeValidator',
    'TimeValidator',
    'UUIDValidator',
    
    # Collection validators
    'ListValidator',
    'DictValidator',
    
    # Specialized validators
    'EmailValidator',
    'PhoneValidator',
    'PasswordValidator',
    'CreditCardValidator',
    'LicensePlateValidator',
    'URLValidator',
    'JSONValidator',
    
    # Business rule validators
    'ReservationValidator',
    'PaymentValidator',
    'UserValidator',
    'ParkingSpotValidator',
    
    # Composite validators
    'SchemaValidator',
    'ConditionalValidator',
    
    # Utility functions
    'validate',
    'validate_schema',
    'is_valid',
    'clean_data',
]