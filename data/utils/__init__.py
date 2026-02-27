"""Utilities package for the parking management system.

This package contains various utility modules for common operations,
including date/time handling, encryption, validation, logging,
and helper functions used throughout the application.
"""

import os
import re
import json
import hashlib
import hmac
import base64
import random
import string
import logging
from datetime import datetime, date, time, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from decimal import Decimal
from functools import wraps
from contextlib import contextmanager
import pytz
from zoneinfo import ZoneInfo
import uuid

# ============================================================================
# Package Metadata
# ============================================================================

__version__ = "1.0.0"
__author__ = "Parking Management System Team"

# ============================================================================
# Import submodules for easier access
# ============================================================================

# This allows doing: from parking.utils import datetime_utils
# But we'll define the actual exports at the bottom

# ============================================================================
# Date and Time Utilities
# ============================================================================

class DateTimeUtils:
    """Utility class for date and time operations."""
    
    # Timezone constants
    UTC = ZoneInfo("UTC")
    LOCAL_TZ = ZoneInfo(os.getenv("TIMEZONE", "America/New_York"))
    
    @classmethod
    def now(cls, tz: Optional[ZoneInfo] = None) -> datetime:
        """Get current datetime with timezone."""
        if tz is None:
            tz = cls.UTC
        return datetime.now(tz)
    
    @classmethod
    def today(cls, tz: Optional[ZoneInfo] = None) -> date:
        """Get current date."""
        return cls.now(tz).date()
    
    @classmethod
    def to_utc(cls, dt: datetime) -> datetime:
        """Convert datetime to UTC."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=cls.LOCAL_TZ)
        return dt.astimezone(cls.UTC)
    
    @classmethod
    def to_local(cls, dt: datetime) -> datetime:
        """Convert datetime to local timezone."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=cls.UTC)
        return dt.astimezone(cls.LOCAL_TZ)
    
    @classmethod
    def format_datetime(cls, dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime to string."""
        return dt.strftime(format)
    
    @classmethod
    def parse_datetime(cls, dt_str: str, format: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
        """Parse datetime from string."""
        try:
            return datetime.strptime(dt_str, format)
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def parse_iso_datetime(cls, dt_str: str) -> Optional[datetime]:
        """Parse ISO format datetime."""
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
    
    @classmethod
    def to_iso_string(cls, dt: datetime) -> str:
        """Convert datetime to ISO format string."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=cls.UTC)
        return dt.isoformat()
    
    @classmethod
    def get_date_range(cls, start_date: date, end_date: date) -> List[date]:
        """Get list of dates between start and end (inclusive)."""
        delta = end_date - start_date
        return [start_date + timedelta(days=i) for i in range(delta.days + 1)]
    
    @classmethod
    def get_business_days(cls, start_date: date, end_date: date) -> List[date]:
        """Get business days (Monday-Friday) between dates."""
        dates = cls.get_date_range(start_date, end_date)
        return [d for d in dates if d.weekday() < 5]
    
    @classmethod
    def is_weekend(cls, dt: Union[date, datetime]) -> bool:
        """Check if date is weekend."""
        if isinstance(dt, datetime):
            dt = dt.date()
        return dt.weekday() >= 5
    
    @classmethod
    def is_business_hours(cls, dt: datetime, start_hour: int = 9, end_hour: int = 17) -> bool:
        """Check if datetime is within business hours."""
        if cls.is_weekend(dt):
            return False
        return start_hour <= dt.hour < end_hour
    
    @classmethod
    def add_business_days(cls, start_date: date, days: int) -> date:
        """Add business days to a date."""
        current = start_date
        added = 0
        while added < days:
            current += timedelta(days=1)
            if current.weekday() < 5:
                added += 1
        return current
    
    @classmethod
    def hours_between(cls, start: datetime, end: datetime) -> float:
        """Calculate hours between two datetimes."""
        delta = end - start
        return delta.total_seconds() / 3600
    
    @classmethod
    def minutes_between(cls, start: datetime, end: datetime) -> int:
        """Calculate minutes between two datetimes."""
        delta = end - start
        return int(delta.total_seconds() / 60)
    
    @classmethod
    def get_time_slots(cls, start_time: datetime, end_time: datetime, 
                      slot_minutes: int = 60) -> List[Tuple[datetime, datetime]]:
        """Generate time slots between start and end times."""
        slots = []
        current = start_time
        while current < end_time:
            slot_end = min(current + timedelta(minutes=slot_minutes), end_time)
            slots.append((current, slot_end))
            current = slot_end
        return slots
    
    @classmethod
    def overlapping(cls, start1: datetime, end1: datetime, 
                   start2: datetime, end2: datetime) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and start2 < end1
    
    @classmethod
    def get_age(cls, birth_date: date) -> int:
        """Calculate age from birth date."""
        today = cls.today()
        return today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
    
    @classmethod
    def get_week_start(cls, dt: date) -> date:
        """Get start of week (Monday)."""
        return dt - timedelta(days=dt.weekday())
    
    @classmethod
    def get_month_start(cls, dt: date) -> date:
        """Get start of month."""
        return date(dt.year, dt.month, 1)
    
    @classmethod
    def get_quarter_start(cls, dt: date) -> date:
        """Get start of quarter."""
        quarter = (dt.month - 1) // 3
        month = quarter * 3 + 1
        return date(dt.year, month, 1)
    
    @classmethod
    def get_year_start(cls, dt: date) -> date:
        """Get start of year."""
        return date(dt.year, 1, 1)


# ============================================================================
# String Utilities
# ============================================================================

class StringUtils:
    """Utility class for string operations."""
    
    @staticmethod
    def generate_confirmation_code(length: int = 12) -> str:
        """Generate a random confirmation code."""
        chars = string.ascii_uppercase + string.digits
        return 'CONF-' + ''.join(random.choices(chars, k=length))
    
    @staticmethod
    def generate_license_plate() -> str:
        """Generate a random license plate."""
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        numbers = ''.join(random.choices(string.digits, k=3))
        return f"{letters}-{numbers}"
    
    @staticmethod
    def generate_reference_id(prefix: str = "REF") -> str:
        """Generate a random reference ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"{prefix}-{timestamp}-{random_part}"
    
    @staticmethod
    def generate_booking_code() -> str:
        """Generate a booking code."""
        return StringUtils.generate_reference_id("BK")
    
    @staticmethod
    def generate_qr_data(reservation_id: int, confirmation_code: str) -> str:
        """Generate QR code data for reservation."""
        data = {
            'type': 'reservation',
            'id': reservation_id,
            'code': confirmation_code,
            'timestamp': datetime.now().isoformat()
        }
        return json.dumps(data)
    
    @staticmethod
    def slugify(text: str) -> str:
        """Convert text to URL-friendly slug."""
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')
    
    @staticmethod
    def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text to specified length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)].rsplit(' ', 1)[0] + suffix
    
    @staticmethod
    def camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case."""
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        return pattern.sub('_', name).lower()
    
    @staticmethod
    def snake_to_camel(name: str, upper_first: bool = False) -> str:
        """Convert snake_case to camelCase."""
        components = name.split('_')
        if upper_first:
            return ''.join(x.title() for x in components)
        return components[0] + ''.join(x.title() for x in components[1:])
    
    @staticmethod
    def mask_string(text: str, visible_chars: int = 4, mask_char: str = '*') -> str:
        """Mask a string (e.g., for credit cards)."""
        if len(text) <= visible_chars:
            return text
        masked_length = len(text) - visible_chars
        return mask_char * masked_length + text[-visible_chars:]
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask an email address."""
        if '@' not in email:
            return email
        local, domain = email.split('@')
        if len(local) <= 2:
            masked_local = local[0] + '***'
        else:
            masked_local = local[0] + '***' + local[-1]
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask a phone number."""
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 10:
            return f"***-***-{digits[-4:]}"
        elif len(digits) == 11:
            return f"+*-***-***-{digits[-4:]}"
        return phone
    
    @staticmethod
    def extract_digits(text: str) -> str:
        """Extract only digits from string."""
        return ''.join(filter(str.isdigit, text))
    
    @staticmethod
    def format_currency(amount: Union[float, Decimal], currency: str = "USD") -> str:
        """Format amount as currency."""
        if isinstance(amount, Decimal):
            amount = float(amount)
        return f"{currency} {amount:,.2f}"
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 1) -> str:
        """Format as percentage."""
        return f"{value * 100:.{decimals}f}%"
    
    @staticmethod
    def pluralize(word: str, count: int) -> str:
        """Simple pluralization."""
        if count == 1:
            return word
        if word.endswith('y'):
            return word[:-1] + 'ies'
        if word.endswith(('s', 'x', 'z', 'ch', 'sh')):
            return word + 'es'
        return word + 's'


# ============================================================================
# Encryption and Security Utilities
# ============================================================================

class SecurityUtils:
    """Utility class for security operations."""
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> str:
        """Hash a password with salt."""
        if salt is None:
            salt = os.urandom(32).hex()
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return f"{salt}${hash_obj.hex()}"
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, hash_value = hashed.split('$')
            new_hash = SecurityUtils.hash_password(password, salt)
            return new_hash.split('$')[1] == hash_value
        except (ValueError, IndexError):
            return False
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a random secure token."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate an API key."""
        return f"pk_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def generate_secret_key() -> str:
        """Generate a secret key."""
        return secrets.token_hex(32)
    
    @staticmethod
    def encrypt(text: str, key: str) -> str:
        """Simple encryption (use proper encryption in production)."""
        # This is a placeholder - use proper encryption library
        cipher = AES.new(key.encode()[:32], AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(text.encode())
        return base64.b64encode(cipher.nonce + tag + ciphertext).decode()
    
    @staticmethod
    def decrypt(encrypted: str, key: str) -> str:
        """Simple decryption (use proper encryption in production)."""
        # This is a placeholder - use proper encryption library
        data = base64.b64decode(encrypted)
        nonce = data[:16]
        tag = data[16:32]
        ciphertext = data[32:]
        cipher = AES.new(key.encode()[:32], AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode()
    
    @staticmethod
    def sign_data(data: str, secret: str) -> str:
        """Sign data with HMAC."""
        signature = hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{data}.{signature}"
    
    @staticmethod
    def verify_signature(signed_data: str, secret: str) -> bool:
        """Verify signed data."""
        try:
            data, signature = signed_data.rsplit('.', 1)
            expected = hmac.new(
                secret.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected)
        except (ValueError, AttributeError):
            return False
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input."""
        # Remove any potentially dangerous characters
        return re.sub(r'[<>"\']', '', text)
    
    @staticmethod
    def is_strong_password(password: str) -> Tuple[bool, str]:
        """Check if password is strong enough."""
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain an uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain a lowercase letter"
        if not re.search(r'[0-9]', password):
            return False, "Password must contain a number"
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain a special character"
        return True, "Password is strong"


# ============================================================================
# Validation Utilities
# ============================================================================

class ValidationUtils:
    """Utility class for data validation."""
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email address format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """Validate phone number format."""
        # Remove common formatting
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        return len(cleaned) >= 10 and cleaned.isdigit()
    
    @staticmethod
    def is_valid_license_plate(plate: str) -> bool:
        """Validate license plate format."""
        # Simple validation - adjust based on your region
        pattern = r'^[A-Z0-9\-]{2,10}$'
        return bool(re.match(pattern, plate.upper()))
    
    @staticmethod
    def is_valid_credit_card(card_number: str) -> bool:
        """Validate credit card using Luhn algorithm."""
        # Remove non-digits
        digits = [int(d) for d in card_number if d.isdigit()]
        if len(digits) < 13 or len(digits) > 19:
            return False
        
        # Luhn algorithm
        check_sum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            check_sum += digit
        
        return check_sum % 10 == 0
    
    @staticmethod
    def is_valid_cvv(cvv: str) -> bool:
        """Validate CVV code."""
        return len(cvv) in (3, 4) and cvv.isdigit()
    
    @staticmethod
    def is_valid_date(date_str: str, format: str = "%Y-%m-%d") -> bool:
        """Validate date string."""
        try:
            datetime.strptime(date_str, format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_valid_time(time_str: str, format: str = "%H:%M") -> bool:
        """Validate time string."""
        try:
            datetime.strptime(time_str, format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL."""
        pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
        return bool(re.match(pattern, url))
    
    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """Validate IP address."""
        # IPv4
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            parts = ip.split('.')
            for part in parts:
                if int(part) > 255:
                    return False
            return True
        # IPv6 (simplified)
        if re.match(r'^[0-9a-fA-F:]+$', ip):
            return len(ip) <= 39
        return False
    
    @staticmethod
    def validate_required_fields(data: Dict, required_fields: List[str]) -> Tuple[bool, List[str]]:
        """Validate that all required fields are present."""
        missing = [field for field in required_fields if field not in data or data[field] is None]
        return len(missing) == 0, missing
    
    @staticmethod
    def validate_length(value: str, min_length: int = 0, max_length: int = 255) -> bool:
        """Validate string length."""
        return min_length <= len(value) <= max_length
    
    @staticmethod
    def validate_range(value: Union[int, float], min_value: Optional[Union[int, float]] = None,
                      max_value: Optional[Union[int, float]] = None) -> bool:
        """Validate numeric range."""
        if min_value is not None and value < min_value:
            return False
        if max_value is not None and value > max_value:
            return False
        return True
    
    @staticmethod
    def validate_enum(value: Any, allowed_values: List[Any]) -> bool:
        """Validate value is in allowed list."""
        return value in allowed_values


# ============================================================================
# JSON Utilities
# ============================================================================

class JSONUtils:
    """Utility class for JSON operations."""
    
    @staticmethod
    def serialize(obj: Any) -> Any:
        """Serialize object to JSON-compatible format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, time):
            return obj.strftime("%H:%M:%S")
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if hasattr(obj, '__dict__'):
            return {k: JSONUtils.serialize(v) for k, v in obj.__dict__.items() 
                   if not k.startswith('_')}
        return obj
    
    @staticmethod
    def dumps(obj: Any, pretty: bool = False) -> str:
        """Dump object to JSON string."""
        if pretty:
            return json.dumps(JSONUtils.serialize(obj), indent=2, default=str)
        return json.dumps(JSONUtils.serialize(obj), default=str)
    
    @staticmethod
    def loads(json_str: str) -> Any:
        """Load object from JSON string."""
        return json.loads(json_str)
    
    @staticmethod
    def safe_dumps(obj: Any, default: str = "{}") -> str:
        """Safely dump object to JSON string."""
        try:
            return JSONUtils.dumps(obj)
        except Exception:
            return default
    
    @staticmethod
    def safe_loads(json_str: str, default: Any = None) -> Any:
        """Safely load object from JSON string."""
        try:
            return JSONUtils.loads(json_str)
        except Exception:
            return default
    
    @staticmethod
    def merge(base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = JSONUtils.merge(result[key], value)
            else:
                result[key] = value
        return result
    
    @staticmethod
    def diff(dict1: Dict, dict2: Dict) -> Dict:
        """Get differences between two dictionaries."""
        diff = {}
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        for key in all_keys:
            if key not in dict1:
                diff[key] = {'added': dict2[key]}
            elif key not in dict2:
                diff[key] = {'removed': dict1[key]}
            elif dict1[key] != dict2[key]:
                if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                    nested_diff = JSONUtils.diff(dict1[key], dict2[key])
                    if nested_diff:
                        diff[key] = nested_diff
                else:
                    diff[key] = {'old': dict1[key], 'new': dict2[key]}
        
        return diff


# ============================================================================
# Logging Utilities
# ============================================================================

class LoggingUtils:
    """Utility class for logging operations."""
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance."""
        return logging.getLogger(name)
    
    @staticmethod
    def log_function_call(logger: Optional[logging.Logger] = None):
        """Decorator to log function calls."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                nonlocal logger
                if logger is None:
                    logger = LoggingUtils.get_logger(func.__module__)
                
                logger.debug(f"Calling {func.__name__}")
                try:
                    result = func(*args, **kwargs)
                    logger.debug(f"{func.__name__} completed successfully")
                    return result
                except Exception as e:
                    logger.error(f"{func.__name__} failed: {e}")
                    raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def log_execution_time(logger: Optional[logging.Logger] = None):
        """Decorator to log function execution time."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                nonlocal logger
                if logger is None:
                    logger = LoggingUtils.get_logger(func.__module__)
                
                start = datetime.now()
                try:
                    result = func(*args, **kwargs)
                    duration = (datetime.now() - start).total_seconds() * 1000
                    logger.debug(f"{func.__name__} took {duration:.2f}ms")
                    return result
                except Exception as e:
                    duration = (datetime.now() - start).total_seconds() * 1000
                    logger.error(f"{func.__name__} failed after {duration:.2f}ms: {e}")
                    raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def get_request_logger(request_id: Optional[str] = None):
        """Get a logger with request context."""
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        class RequestLogger:
            def __init__(self, request_id):
                self.request_id = request_id
                self.logger = logging.getLogger("request")
            
            def _log(self, level, msg, *args, **kwargs):
                extra = kwargs.get('extra', {})
                extra['request_id'] = self.request_id
                kwargs['extra'] = extra
                getattr(self.logger, level)(f"[{self.request_id}] {msg}", *args, **kwargs)
            
            def debug(self, msg, *args, **kwargs):
                self._log('debug', msg, *args, **kwargs)
            
            def info(self, msg, *args, **kwargs):
                self._log('info', msg, *args, **kwargs)
            
            def warning(self, msg, *args, **kwargs):
                self._log('warning', msg, *args, **kwargs)
            
            def error(self, msg, *args, **kwargs):
                self._log('error', msg, *args, **kwargs)
            
            def critical(self, msg, *args, **kwargs):
                self._log('critical', msg, *args, **kwargs)
        
        return RequestLogger(request_id)


# ============================================================================
# File Utilities
# ============================================================================

class FileUtils:
    """Utility class for file operations."""
    
    @staticmethod
    def ensure_dir(path: str) -> bool:
        """Ensure directory exists."""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            logging.error(f"Failed to create directory {path}: {e}")
            return False
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """Convert filename to safe version."""
        # Remove path components
        filename = os.path.basename(filename)
        # Replace unsafe characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        return filename
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension."""
        return os.path.splitext(filename)[1].lower()
    
    @staticmethod
    def get_file_size(filepath: str) -> int:
        """Get file size in bytes."""
        try:
            return os.path.getsize(filepath)
        except Exception:
            return 0
    
    @staticmethod
    def read_file(filepath: str, mode: str = 'r') -> Optional[str]:
        """Read file contents."""
        try:
            with open(filepath, mode) as f:
                return f.read()
        except Exception as e:
            logging.error(f"Failed to read file {filepath}: {e}")
            return None
    
    @staticmethod
    def write_file(filepath: str, content: str, mode: str = 'w') -> bool:
        """Write content to file."""
        try:
            FileUtils.ensure_dir(os.path.dirname(filepath))
            with open(filepath, mode) as f:
                f.write(content)
            return True
        except Exception as e:
            logging.error(f"Failed to write file {filepath}: {e}")
            return False
    
    @staticmethod
    def delete_file(filepath: str) -> bool:
        """Delete file."""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            return True
        except Exception as e:
            logging.error(f"Failed to delete file {filepath}: {e}")
            return False
    
    @staticmethod
    def get_unique_filename(directory: str, filename: str) -> str:
        """Get unique filename in directory."""
        base, ext = os.path.splitext(filename)
        counter = 1
        new_filename = filename
        
        while os.path.exists(os.path.join(directory, new_filename)):
            new_filename = f"{base}_{counter}{ext}"
            counter += 1
        
        return new_filename
    
    @staticmethod
    def list_files(directory: str, pattern: Optional[str] = None) -> List[str]:
        """List files in directory."""
        try:
            files = os.listdir(directory)
            if pattern:
                files = [f for f in files if re.match(pattern, f)]
            return files
        except Exception as e:
            logging.error(f"Failed to list files in {directory}: {e}")
            return []
    
    @staticmethod
    def get_file_info(filepath: str) -> Dict[str, Any]:
        """Get file information."""
        try:
            stat = os.stat(filepath)
            return {
                'name': os.path.basename(filepath),
                'path': filepath,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'accessed': datetime.fromtimestamp(stat.st_atime),
                'extension': FileUtils.get_file_extension(filepath)
            }
        except Exception as e:
            logging.error(f"Failed to get file info for {filepath}: {e}")
            return {}


# ============================================================================
# Math Utilities
# ============================================================================

class MathUtils:
    """Utility class for mathematical operations."""
    
    @staticmethod
    def round_half_up(value: float, decimals: int = 2) -> float:
        """Round half up (away from zero)."""
        multiplier = 10 ** decimals
        return math.floor(value * multiplier + 0.5) / multiplier
    
    @staticmethod
    def round_half_down(value: float, decimals: int = 2) -> float:
        """Round half down (towards zero)."""
        multiplier = 10 ** decimals
        return math.ceil(value * multiplier - 0.5) / multiplier
    
    @staticmethod
    def round_half_even(value: float, decimals: int = 2) -> float:
        """Round half to even (bankers rounding)."""
        return round(value, decimals)
    
    @staticmethod
    def percentage(part: Union[int, float], whole: Union[int, float]) -> float:
        """Calculate percentage."""
        if whole == 0:
            return 0.0
        return (part / whole) * 100
    
    @staticmethod
    def weighted_average(values: List[float], weights: List[float]) -> float:
        """Calculate weighted average."""
        if not values or not weights or len(values) != len(weights):
            return 0.0
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0
        return sum(v * w for v, w in zip(values, weights)) / total_weight
    
    @staticmethod
    def moving_average(values: List[float], window: int) -> List[float]:
        """Calculate moving average."""
        if len(values) < window:
            return []
        averages = []
        for i in range(len(values) - window + 1):
            window_avg = sum(values[i:i + window]) / window
            averages.append(window_avg)
        return averages
    
    @staticmethod
    def standard_deviation(values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    @staticmethod
    def percentile(values: List[float], percentile: float) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        
        lower = sorted_values[int(index)]
        upper = sorted_values[int(index) + 1]
        fraction = index - int(index)
        return lower + (upper - lower) * fraction


# ============================================================================
# Decorators and Context Managers
# ============================================================================

class Decorators:
    """Collection of useful decorators."""
    
    @staticmethod
    def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
        """Retry decorator with exponential backoff."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                import time
                current_delay = delay
                
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_attempts - 1:
                            raise
                        
                        logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s")
                        time.sleep(current_delay)
                        current_delay *= backoff
                
                return None
            return wrapper
        return decorator
    
    @staticmethod
    def timeout(seconds: int):
        """Timeout decorator (Unix only)."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                import signal
                
                def handler(signum, frame):
                    raise TimeoutError(f"Function {func.__name__} timed out after {seconds}s")
                
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(seconds)
                
                try:
                    result = func(*args, **kwargs)
                    signal.alarm(0)
                    return result
                finally:
                    signal.alarm(0)
            
            return wrapper
        return decorator
    
    @staticmethod
    def singleton(cls):
        """Singleton decorator for classes."""
        instances = {}
        
        @wraps(cls)
        def wrapper(*args, **kwargs):
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
            return instances[cls]
        
        return wrapper
    
    @staticmethod
    def memoize(func):
        """Memoization decorator."""
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(sorted(kwargs.items()))
            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]
        
        return wrapper
    
    @staticmethod
    def deprecated(message: str = None):
        """Deprecation decorator."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                msg = message or f"{func.__name__} is deprecated"
                logging.warning(msg)
                return func(*args, **kwargs)
            return wrapper
        return decorator


@contextmanager
def timer(name: str = "Operation"):
    """Context manager to time operations."""
    start = datetime.now()
    try:
        yield
    finally:
        duration = (datetime.now() - start).total_seconds()
        logging.info(f"{name} took {duration:.3f}s")


@contextmanager
def temporary_environment(**env_vars):
    """Context manager for temporary environment variables."""
    old_environ = dict(os.environ)
    os.environ.update(env_vars)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Date and Time
    'DateTimeUtils',
    
    # String
    'StringUtils',
    
    # Security
    'SecurityUtils',
    
    # Validation
    'ValidationUtils',
    
    # JSON
    'JSONUtils',
    
    # Logging
    'LoggingUtils',
    
    # File
    'FileUtils',
    
    # Math
    'MathUtils',
    
    # Decorators
    'Decorators',
    'timer',
    'temporary_environment',
]

# Convenience aliases
dt_utils = DateTimeUtils
str_utils = StringUtils
security_utils = SecurityUtils
validation_utils = ValidationUtils
json_utils = JSONUtils
logging_utils = LoggingUtils
file_utils = FileUtils
math_utils = MathUtils