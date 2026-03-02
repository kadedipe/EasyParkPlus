"""Helper functions and utilities for the parking management system.

This module provides various helper functions for common operations,
including data transformation, formatting, calculations, and other
utility functions used throughout the application.
"""

import os
import re
import json
import hashlib
import hmac
import base64
import random
import string
import math
import time
import uuid
import secrets
from datetime import datetime, date, time, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple, Callable, TypeVar, Generic, Iterator
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps, reduce
from itertools import groupby
from collections import defaultdict, Counter
import pytz
from zoneinfo import ZoneInfo

# ============================================================================
# Type Definitions
# ============================================================================

T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# Dictionary Helpers
# ============================================================================

class DictHelper:
    """Helper functions for dictionary operations."""
    
    @staticmethod
    def get_nested(data: Dict, path: str, default: Any = None, separator: str = '.') -> Any:
        """Get a nested value from a dictionary using dot notation."""
        keys = path.split(separator)
        value = data
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    @staticmethod
    def set_nested(data: Dict, path: str, value: Any, separator: str = '.') -> Dict:
        """Set a nested value in a dictionary using dot notation."""
        keys = path.split(separator)
        current = data
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        return data
    
    @staticmethod
    def deep_merge(*dicts: Dict) -> Dict:
        """Deep merge multiple dictionaries."""
        result = {}
        
        for d in dicts:
            for key, value in d.items():
                if key in result:
                    if isinstance(result[key], dict) and isinstance(value, dict):
                        result[key] = DictHelper.deep_merge(result[key], value)
                    elif isinstance(result[key], list) and isinstance(value, list):
                        result[key] = result[key] + value
                    else:
                        result[key] = value
                else:
                    result[key] = value
        
        return result
    
    @staticmethod
    def deep_update(base: Dict, update: Dict) -> Dict:
        """Deep update a dictionary."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                DictHelper.deep_update(base[key], value)
            else:
                base[key] = value
        return base
    
    @staticmethod
    def pick(data: Dict, keys: List[str]) -> Dict:
        """Pick specific keys from a dictionary."""
        return {k: data[k] for k in keys if k in data}
    
    @staticmethod
    def omit(data: Dict, keys: List[str]) -> Dict:
        """Omit specific keys from a dictionary."""
        return {k: v for k, v in data.items() if k not in keys}
    
    @staticmethod
    def rename_keys(data: Dict, mapping: Dict[str, str]) -> Dict:
        """Rename dictionary keys according to mapping."""
        result = {}
        for key, value in data.items():
            new_key = mapping.get(key, key)
            result[new_key] = value
        return result
    
    @staticmethod
    def flatten(data: Dict, parent_key: str = '', separator: str = '.') -> Dict:
        """Flatten a nested dictionary."""
        items = []
        for key, value in data.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            if isinstance(value, dict):
                items.extend(DictHelper.flatten(value, new_key, separator).items())
            else:
                items.append((new_key, value))
        return dict(items)
    
    @staticmethod
    def unflatten(data: Dict, separator: str = '.') -> Dict:
        """Unflatten a flattened dictionary."""
        result = {}
        for key, value in data.items():
            parts = key.split(separator)
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        return result
    
    @staticmethod
    def group_by(items: List[Dict], key: str) -> Dict[Any, List[Dict]]:
        """Group a list of dictionaries by a key."""
        result = defaultdict(list)
        for item in items:
            result[item.get(key)].append(item)
        return dict(result)
    
    @staticmethod
    def sort_by(items: List[Dict], key: str, reverse: bool = False) -> List[Dict]:
        """Sort a list of dictionaries by a key."""
        return sorted(items, key=lambda x: x.get(key), reverse=reverse)
    
    @staticmethod
    def filter_by(items: List[Dict], predicate: Callable[[Dict], bool]) -> List[Dict]:
        """Filter a list of dictionaries by a predicate."""
        return [item for item in items if predicate(item)]
    
    @staticmethod
    def pluck(items: List[Dict], key: str) -> List[Any]:
        """Extract a single key from a list of dictionaries."""
        return [item.get(key) for item in items if key in item]
    
    @staticmethod
    def index_by(items: List[Dict], key: str) -> Dict[Any, Dict]:
        """Create an index of items by a key."""
        return {item[key]: item for item in items if key in item}


# ============================================================================
# List Helpers
# ============================================================================

class ListHelper:
    """Helper functions for list operations."""
    
    @staticmethod
    def chunk(items: List[T], size: int) -> Iterator[List[T]]:
        """Split a list into chunks of specified size."""
        for i in range(0, len(items), size):
            yield items[i:i + size]
    
    @staticmethod
    def unique(items: List[T], key: Optional[Callable] = None) -> List[T]:
        """Get unique items from a list."""
        if key:
            seen = set()
            result = []
            for item in items:
                k = key(item)
                if k not in seen:
                    seen.add(k)
                    result.append(item)
            return result
        else:
            return list(dict.fromkeys(items))
    
    @staticmethod
    def flatten(items: List) -> List:
        """Flatten a nested list."""
        result = []
        for item in items:
            if isinstance(item, list):
                result.extend(ListHelper.flatten(item))
            else:
                result.append(item)
        return result
    
    @staticmethod
    def intersection(*lists: List[T]) -> List[T]:
        """Get intersection of multiple lists."""
        if not lists:
            return []
        return list(set(lists[0]).intersection(*lists[1:]))
    
    @staticmethod
    def union(*lists: List[T]) -> List[T]:
        """Get union of multiple lists."""
        if not lists:
            return []
        return list(set().union(*lists))
    
    @staticmethod
    def difference(list1: List[T], list2: List[T]) -> List[T]:
        """Get difference between two lists."""
        return list(set(list1) - set(list2))
    
    @staticmethod
    def symmetric_difference(list1: List[T], list2: List[T]) -> List[T]:
        """Get symmetric difference between two lists."""
        return list(set(list1) ^ set(list2))
    
    @staticmethod
    def group_by(items: List[T], key_func: Callable[[T], K]) -> Dict[K, List[T]]:
        """Group items by a key function."""
        result = defaultdict(list)
        for item in items:
            result[key_func(item)].append(item)
        return dict(result)
    
    @staticmethod
    def sort_by(items: List[T], key_func: Callable[[T], Any], reverse: bool = False) -> List[T]:
        """Sort items by a key function."""
        return sorted(items, key=key_func, reverse=reverse)
    
    @staticmethod
    def filter_by(items: List[T], predicate: Callable[[T], bool]) -> List[T]:
        """Filter items by a predicate."""
        return [item for item in items if predicate(item)]
    
    @staticmethod
    def first(items: List[T], predicate: Optional[Callable[[T], bool]] = None, default: Optional[T] = None) -> Optional[T]:
        """Get first item matching predicate."""
        if predicate:
            for item in items:
                if predicate(item):
                    return item
            return default
        return items[0] if items else default
    
    @staticmethod
    def last(items: List[T], predicate: Optional[Callable[[T], bool]] = None, default: Optional[T] = None) -> Optional[T]:
        """Get last item matching predicate."""
        if predicate:
            for item in reversed(items):
                if predicate(item):
                    return item
            return default
        return items[-1] if items else default
    
    @staticmethod
    def take(items: List[T], n: int) -> List[T]:
        """Take first n items."""
        return items[:n]
    
    @staticmethod
    def take_last(items: List[T], n: int) -> List[T]:
        """Take last n items."""
        return items[-n:] if n > 0 else []
    
    @staticmethod
    def drop(items: List[T], n: int) -> List[T]:
        """Drop first n items."""
        return items[n:]
    
    @staticmethod
    def drop_last(items: List[T], n: int) -> List[T]:
        """Drop last n items."""
        return items[:-n] if n > 0 else items
    
    @staticmethod
    def rotate(items: List[T], n: int) -> List[T]:
        """Rotate list by n positions."""
        if not items:
            return items
        n = n % len(items)
        return items[-n:] + items[:-n]
    
    @staticmethod
    def shuffle(items: List[T]) -> List[T]:
        """Shuffle list randomly."""
        result = items.copy()
        random.shuffle(result)
        return result
    
    @staticmethod
    def sample(items: List[T], k: int) -> List[T]:
        """Get random sample of k items."""
        return random.sample(items, min(k, len(items)))


# ============================================================================
# String Helpers
# ============================================================================

class StringHelper:
    """Helper functions for string operations."""
    
    @staticmethod
    def truncate(text: str, max_length: int = 100, suffix: str = '...') -> str:
        """Truncate text to specified length."""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)].rstrip() + suffix
    
    @staticmethod
    def slugify(text: str) -> str:
        """Convert text to URL-friendly slug."""
        # Convert to lowercase
        text = text.lower()
        # Replace spaces with hyphens
        text = re.sub(r'\s+', '-', text)
        # Remove non-alphanumeric characters
        text = re.sub(r'[^a-z0-9\-]', '', text)
        # Remove multiple hyphens
        text = re.sub(r'-+', '-', text)
        # Trim hyphens from ends
        return text.strip('-')
    
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
    def to_kebab_case(text: str) -> str:
        """Convert text to kebab-case."""
        return StringHelper.slugify(text).replace('_', '-')
    
    @staticmethod
    def to_title_case(text: str) -> str:
        """Convert text to Title Case."""
        return ' '.join(word.capitalize() for word in text.split())
    
    @staticmethod
    def pluralize(word: str, count: int, plural_form: Optional[str] = None) -> str:
        """Simple pluralization."""
        if count == 1:
            return word
        if plural_form:
            return plural_form
        if word.endswith('y') and not word.endswith(('ay', 'ey', 'iy', 'oy', 'uy')):
            return word[:-1] + 'ies'
        if word.endswith(('s', 'x', 'z', 'ch', 'sh')):
            return word + 'es'
        return word + 's'
    
    @staticmethod
    def mask(text: str, visible_chars: int = 4, mask_char: str = '*') -> str:
        """Mask a string."""
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
    def extract_letters(text: str) -> str:
        """Extract only letters from string."""
        return ''.join(filter(str.isalpha, text))
    
    @staticmethod
    def extract_alphanumeric(text: str) -> str:
        """Extract only alphanumeric characters from string."""
        return ''.join(filter(str.isalnum, text))
    
    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Normalize whitespace (replace multiple spaces with single)."""
        return ' '.join(text.split())
    
    @staticmethod
    def strip_html(text: str) -> str:
        """Strip HTML tags from text."""
        return re.sub(r'<[^>]+>', '', text)
    
    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters."""
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&apos;",
            ">": "&gt;",
            "<": "&lt;",
        }
        return "".join(html_escape_table.get(c, c) for c in text)
    
    @staticmethod
    def unescape_html(text: str) -> str:
        """Unescape HTML entities."""
        html_unescape_table = {
            "&amp;": "&",
            "&quot;": '"',
            "&apos;": "'",
            "&gt;": ">",
            "&lt;": "<",
        }
        for escaped, unescaped in html_unescape_table.items():
            text = text.replace(escaped, unescaped)
        return text
    
    @staticmethod
    def generate_random(length: int = 8, charset: str = string.ascii_letters + string.digits) -> str:
        """Generate random string."""
        return ''.join(random.choice(charset) for _ in range(length))
    
    @staticmethod
    def generate_secure_random(length: int = 32) -> str:
        """Generate cryptographically secure random string."""
        return secrets.token_urlsafe(length)[:length]
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return StringHelper.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @staticmethod
    def similarity_ratio(s1: str, s2: str) -> float:
        """Calculate similarity ratio between two strings (0-1)."""
        distance = StringHelper.levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        if max_len == 0:
            return 1.0
        return 1.0 - (distance / max_len)


# ============================================================================
# Number Helpers
# ============================================================================

class NumberHelper:
    """Helper functions for number operations."""
    
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
    def format_currency(amount: Union[float, Decimal], currency: str = "USD", locale: str = "en_US") -> str:
        """Format amount as currency."""
        if isinstance(amount, Decimal):
            amount = float(amount)
        
        symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CNY": "¥",
        }
        
        symbol = symbols.get(currency, currency)
        formatted = f"{symbol}{amount:,.2f}"
        
        return formatted
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 1, include_sign: bool = False) -> str:
        """Format as percentage."""
        formatted = f"{value * 100:.{decimals}f}%"
        if include_sign and value > 0:
            formatted = "+" + formatted
        return formatted
    
    @staticmethod
    def format_number(value: float, decimals: int = 2, thousands_sep: str = ",") -> str:
        """Format number with thousands separator."""
        return f"{value:,.{decimals}f}".replace(",", thousands_sep)
    
    @staticmethod
    def to_roman(num: int) -> str:
        """Convert integer to Roman numerals."""
        if not 1 <= num <= 3999:
            raise ValueError("Number must be between 1 and 3999")
        
        val = [
            (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
            (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
            (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'),
            (1, 'I')
        ]
        
        roman = ''
        for n, r in val:
            while num >= n:
                roman += r
                num -= n
        return roman
    
    @staticmethod
    def from_roman(roman: str) -> int:
        """Convert Roman numerals to integer."""
        roman_values = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50,
            'C': 100, 'D': 500, 'M': 1000
        }
        
        result = 0
        prev_value = 0
        
        for char in roman[::-1]:
            value = roman_values[char]
            if value < prev_value:
                result -= value
            else:
                result += value
            prev_value = value
        
        return result
    
    @staticmethod
    def to_words(number: int) -> str:
        """Convert number to English words."""
        ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
                "seventeen", "eighteen", "nineteen"]
        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
        thousands = ["", "thousand", "million", "billion", "trillion"]
        
        if number == 0:
            return "zero"
        
        def _convert_less_than_thousand(n):
            if n < 20:
                return ones[n]
            elif n < 100:
                return tens[n // 10] + ("-" + ones[n % 10] if n % 10 != 0 else "")
            else:
                return ones[n // 100] + " hundred" + (" and " + _convert_less_than_thousand(n % 100) if n % 100 != 0 else "")
        
        if number < 0:
            return "negative " + NumberHelper.to_words(abs(number))
        
        result = []
        for i, unit in enumerate(thousands):
            if number == 0:
                break
            chunk = number % 1000
            if chunk != 0:
                result.append(_convert_less_than_thousand(chunk) + (" " + unit if unit else ""))
            number //= 1000
        
        return " ".join(reversed(result)).strip()
    
    @staticmethod
    def is_prime(n: int) -> bool:
        """Check if number is prime."""
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False
        
        for i in range(3, int(math.sqrt(n)) + 1, 2):
            if n % i == 0:
                return False
        return True
    
    @staticmethod
    def fibonacci(n: int) -> List[int]:
        """Generate Fibonacci sequence up to n terms."""
        if n <= 0:
            return []
        if n == 1:
            return [0]
        
        fib = [0, 1]
        for i in range(2, n):
            fib.append(fib[-1] + fib[-2])
        return fib
    
    @staticmethod
    def factorial(n: int) -> int:
        """Calculate factorial."""
        if n < 0:
            raise ValueError("Factorial not defined for negative numbers")
        if n == 0:
            return 1
        
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result


# ============================================================================
# Date/Time Helpers
# ============================================================================

class DateTimeHelper:
    """Helper functions for date and time operations."""
    
    # Timezone constants
    UTC = ZoneInfo("UTC")
    LOCAL_TZ = ZoneInfo(os.getenv("TIMEZONE", "America/New_York"))
    
    @staticmethod
    def now(tz: Optional[ZoneInfo] = None) -> datetime:
        """Get current datetime with timezone."""
        if tz is None:
            tz = DateTimeHelper.UTC
        return datetime.now(tz)
    
    @staticmethod
    def today(tz: Optional[ZoneInfo] = None) -> date:
        """Get current date."""
        return DateTimeHelper.now(tz).date()
    
    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        """Convert datetime to UTC."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=DateTimeHelper.LOCAL_TZ)
        return dt.astimezone(DateTimeHelper.UTC)
    
    @staticmethod
    def to_local(dt: datetime) -> datetime:
        """Convert datetime to local timezone."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=DateTimeHelper.UTC)
        return dt.astimezone(DateTimeHelper.LOCAL_TZ)
    
    @staticmethod
    def format_date(dt: Union[date, datetime], format: str = "%Y-%m-%d") -> str:
        """Format date to string."""
        return dt.strftime(format)
    
    @staticmethod
    def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime to string."""
        return dt.strftime(format)
    
    @staticmethod
    def format_time(dt: Union[datetime, time], format: str = "%H:%M:%S") -> str:
        """Format time to string."""
        if isinstance(dt, datetime):
            return dt.strftime(format)
        return dt.strftime(format)
    
    @staticmethod
    def parse_date(date_str: str, format: str = "%Y-%m-%d") -> Optional[date]:
        """Parse date from string."""
        try:
            return datetime.strptime(date_str, format).date()
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def parse_datetime(dt_str: str, format: str = "%Y-%m-%d %H:%M:%S") -> Optional[datetime]:
        """Parse datetime from string."""
        try:
            return datetime.strptime(dt_str, format)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def parse_time(time_str: str, format: str = "%H:%M:%S") -> Optional[time]:
        """Parse time from string."""
        try:
            return datetime.strptime(time_str, format).time()
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def parse_iso_datetime(dt_str: str) -> Optional[datetime]:
        """Parse ISO format datetime."""
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def to_iso_string(dt: datetime) -> str:
        """Convert datetime to ISO format string."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=DateTimeHelper.UTC)
        return dt.isoformat()
    
    @staticmethod
    def get_date_range(start_date: date, end_date: date) -> List[date]:
        """Get list of dates between start and end (inclusive)."""
        delta = end_date - start_date
        return [start_date + timedelta(days=i) for i in range(delta.days + 1)]
    
    @staticmethod
    def get_business_days(start_date: date, end_date: date) -> List[date]:
        """Get business days (Monday-Friday) between dates."""
        dates = DateTimeHelper.get_date_range(start_date, end_date)
        return [d for d in dates if d.weekday() < 5]
    
    @staticmethod
    def is_weekend(dt: Union[date, datetime]) -> bool:
        """Check if date is weekend."""
        if isinstance(dt, datetime):
            dt = dt.date()
        return dt.weekday() >= 5
    
    @staticmethod
    def is_business_hours(dt: datetime, start_hour: int = 9, end_hour: int = 17) -> bool:
        """Check if datetime is within business hours."""
        if DateTimeHelper.is_weekend(dt):
            return False
        return start_hour <= dt.hour < end_hour
    
    @staticmethod
    def add_business_days(start_date: date, days: int) -> date:
        """Add business days to a date."""
        current = start_date
        added = 0
        while added < days:
            current += timedelta(days=1)
            if current.weekday() < 5:
                added += 1
        return current
    
    @staticmethod
    def hours_between(start: datetime, end: datetime) -> float:
        """Calculate hours between two datetimes."""
        delta = end - start
        return delta.total_seconds() / 3600
    
    @staticmethod
    def minutes_between(start: datetime, end: datetime) -> int:
        """Calculate minutes between two datetimes."""
        delta = end - start
        return int(delta.total_seconds() / 60)
    
    @staticmethod
    def seconds_between(start: datetime, end: datetime) -> int:
        """Calculate seconds between two datetimes."""
        delta = end - start
        return int(delta.total_seconds())
    
    @staticmethod
    def days_between(start: date, end: date) -> int:
        """Calculate days between two dates."""
        return (end - start).days
    
    @staticmethod
    def get_age(birth_date: date) -> int:
        """Calculate age from birth date."""
        today = DateTimeHelper.today()
        return today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
    
    @staticmethod
    def get_week_start(dt: date) -> date:
        """Get start of week (Monday)."""
        return dt - timedelta(days=dt.weekday())
    
    @staticmethod
    def get_week_end(dt: date) -> date:
        """Get end of week (Sunday)."""
        return dt + timedelta(days=(6 - dt.weekday()))
    
    @staticmethod
    def get_month_start(dt: date) -> date:
        """Get start of month."""
        return date(dt.year, dt.month, 1)
    
    @staticmethod
    def get_month_end(dt: date) -> date:
        """Get end of month."""
        next_month = dt.replace(day=28) + timedelta(days=4)
        return next_month - timedelta(days=next_month.day)
    
    @staticmethod
    def get_quarter_start(dt: date) -> date:
        """Get start of quarter."""
        quarter = (dt.month - 1) // 3
        month = quarter * 3 + 1
        return date(dt.year, month, 1)
    
    @staticmethod
    def get_quarter_end(dt: date) -> date:
        """Get end of quarter."""
        quarter = (dt.month - 1) // 3
        month = quarter * 3 + 3
        last_day = (date(dt.year, month + 1, 1) - timedelta(days=1)).day
        return date(dt.year, month, last_day)
    
    @staticmethod
    def get_year_start(dt: date) -> date:
        """Get start of year."""
        return date(dt.year, 1, 1)
    
    @staticmethod
    def get_year_end(dt: date) -> date:
        """Get end of year."""
        return date(dt.year, 12, 31)
    
    @staticmethod
    def get_time_slots(start_time: datetime, end_time: datetime, slot_minutes: int = 60) -> List[Tuple[datetime, datetime]]:
        """Generate time slots between start and end times."""
        slots = []
        current = start_time
        while current < end_time:
            slot_end = min(current + timedelta(minutes=slot_minutes), end_time)
            slots.append((current, slot_end))
            current = slot_end
        return slots
    
    @staticmethod
    def overlapping(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and start2 < end1
    
    @staticmethod
    def overlap_duration(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> timedelta:
        """Calculate overlap duration between two time ranges."""
        if not DateTimeHelper.overlapping(start1, end1, start2, end2):
            return timedelta()
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        return overlap_end - overlap_start
    
    @staticmethod
    def humanize_time(seconds: int) -> str:
        """Convert seconds to human readable format."""
        if seconds < 60:
            return f"{seconds} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''}"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''}"
    
    @staticmethod
    def humanize_date(dt: date) -> str:
        """Convert date to human readable format."""
        today = DateTimeHelper.today()
        delta = dt - today
        
        if delta.days == 0:
            return "today"
        elif delta.days == 1:
            return "tomorrow"
        elif delta.days == -1:
            return "yesterday"
        elif -7 < delta.days < 7:
            return dt.strftime("%A")
        elif dt.year == today.year:
            return dt.strftime("%B %d")
        else:
            return dt.strftime("%B %d, %Y")


# ============================================================================
# Math Helpers
# ============================================================================

class MathHelper:
    """Helper functions for mathematical operations."""
    
    @staticmethod
    def percentage(part: Union[int, float], whole: Union[int, float]) -> float:
        """Calculate percentage."""
        if whole == 0:
            return 0.0
        return (part / whole) * 100
    
    @staticmethod
    def percentage_change(old: Union[int, float], new: Union[int, float]) -> float:
        """Calculate percentage change."""
        if old == 0:
            return 0.0
        return ((new - old) / old) * 100
    
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
    def exponential_moving_average(values: List[float], alpha: float) -> List[float]:
        """Calculate exponential moving average."""
        if not values:
            return []
        
        ema = [values[0]]
        for i in range(1, len(values)):
            ema.append(alpha * values[i] + (1 - alpha) * ema[-1])
        return ema
    
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
    
    @staticmethod
    def median(values: List[float]) -> float:
        """Calculate median."""
        return MathHelper.percentile(values, 50)
    
    @staticmethod
    def mode(values: List[Any]) -> List[Any]:
        """Calculate mode(s)."""
        if not values:
            return []
        counter = Counter(values)
        max_count = max(counter.values())
        return [k for k, v in counter.items() if v == max_count]
    
    @staticmethod
    def range_(values: List[float]) -> float:
        """Calculate range (max - min)."""
        if not values:
            return 0.0
        return max(values) - min(values)
    
    @staticmethod
    def iqr(values: List[float]) -> float:
        """Calculate interquartile range."""
        q1 = MathHelper.percentile(values, 25)
        q3 = MathHelper.percentile(values, 75)
        return q3 - q1
    
    @staticmethod
    def covariance(x: List[float], y: List[float]) -> float:
        """Calculate covariance."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        mean_x = sum(x) / len(x)
        mean_y = sum(y) / len(y)
        
        return sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / (len(x) - 1)
    
    @staticmethod
    def correlation(x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        std_x = MathHelper.standard_deviation(x)
        std_y = MathHelper.standard_deviation(y)
        
        if std_x == 0 or std_y == 0:
            return 0.0
        
        cov = MathHelper.covariance(x, y)
        return cov / (std_x * std_y)
    
    @staticmethod
    def linear_regression(x: List[float], y: List[float]) -> Tuple[float, float]:
        """Calculate linear regression (slope, intercept)."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0, 0.0
        
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
        intercept = (sum_y - slope * sum_x) / n
        
        return slope, intercept
    
    @staticmethod
    def normalize(values: List[float], min_val: Optional[float] = None, max_val: Optional[float] = None) -> List[float]:
        """Normalize values to [0, 1] range."""
        if not values:
            return []
        
        if min_val is None:
            min_val = min(values)
        if max_val is None:
            max_val = max(values)
        
        if max_val == min_val:
            return [0.0] * len(values)
        
        return [(v - min_val) / (max_val - min_val) for v in values]
    
    @staticmethod
    def standardize(values: List[float]) -> List[float]:
        """Standardize values to have mean 0 and std 1."""
        if len(values) < 2:
            return [0.0] * len(values)
        
        mean = sum(values) / len(values)
        std = MathHelper.standard_deviation(values)
        
        if std == 0:
            return [0.0] * len(values)
        
        return [(v - mean) / std for v in values]


# ============================================================================
# Geo Helpers
# ============================================================================

class GeoHelper:
    """Helper functions for geographic calculations."""
    
    # Earth radius in kilometers
    EARTH_RADIUS_KM = 6371
    EARTH_RADIUS_MI = 3959
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float, unit: str = 'km') -> float:
        """Calculate great-circle distance between two points using Haversine formula."""
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        
        # Choose radius based on unit
        if unit == 'mi':
            radius = GeoHelper.EARTH_RADIUS_MI
        else:
            radius = GeoHelper.EARTH_RADIUS_KM
        
        return radius * c
    
    @staticmethod
    def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing between two points (in degrees)."""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.atan2(y, x)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        
        return bearing
    
    @staticmethod
    def destination_point(lat: float, lon: float, distance: float, bearing: float, unit: str = 'km') -> Tuple[float, float]:
        """Calculate destination point given start point, distance, and bearing."""
        lat, lon = map(math.radians, [lat, lon])
        bearing = math.radians(bearing)
        
        # Choose radius based on unit
        if unit == 'mi':
            radius = GeoHelper.EARTH_RADIUS_MI
        else:
            radius = GeoHelper.EARTH_RADIUS_KM
        
        angular_distance = distance / radius
        
        lat2 = math.asin(
            math.sin(lat) * math.cos(angular_distance) +
            math.cos(lat) * math.sin(angular_distance) * math.cos(bearing)
        )
        
        lon2 = lon + math.atan2(
            math.sin(bearing) * math.sin(angular_distance) * math.cos(lat),
            math.cos(angular_distance) - math.sin(lat) * math.sin(lat2)
        )
        
        return math.degrees(lat2), math.degrees(lon2)
    
    @staticmethod
    def midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> Tuple[float, float]:
        """Calculate midpoint between two points."""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        
        x = math.cos(lat2) * math.cos(dlon)
        y = math.cos(lat2) * math.sin(dlon)
        
        lat3 = math.atan2(
            math.sin(lat1) + math.sin(lat2),
            math.sqrt((math.cos(lat1) + x) ** 2 + y ** 2)
        )
        
        lon3 = lon1 + math.atan2(y, math.cos(lat1) + x)
        
        return math.degrees(lat3), math.degrees(lon3)
    
    @staticmethod
    def within_radius(lat1: float, lon1: float, lat2: float, lon2: float, radius: float, unit: str = 'km') -> bool:
        """Check if point2 is within radius of point1."""
        distance = GeoHelper.haversine_distance(lat1, lon1, lat2, lon2, unit)
        return distance <= radius
    
    @staticmethod
    def decode_polyline(polyline: str) -> List[Tuple[float, float]]:
        """Decode Google Maps encoded polyline."""
        points = []
        index = 0
        lat = 0
        lng = 0
        
        while index < len(polyline):
            # Latitude
            b = 0
            shift = 0
            result = 0
            
            while True:
                b = ord(polyline[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            dlat = ~(result >> 1) if (result & 1) else (result >> 1)
            lat += dlat
            
            # Longitude
            shift = 0
            result = 0
            
            while True:
                b = ord(polyline[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break
            
            dlng = ~(result >> 1) if (result & 1) else (result >> 1)
            lng += dlng
            
            points.append((lat / 1e5, lng / 1e5))
        
        return points
    
    @staticmethod
    def encode_polyline(points: List[Tuple[float, float]]) -> str:
        """Encode points to Google Maps polyline format."""
        result = []
        prev_lat = 0
        prev_lng = 0
        
        for lat, lng in points:
            # Scale and round to 1e5
            lat5 = int(round(lat * 1e5))
            lng5 = int(round(lng * 1e5))
            
            dlat = lat5 - prev_lat
            dlng = lng5 - prev_lng
            
            prev_lat = lat5
            prev_lng = lng5
            
            # Encode latitude
            dlat = (dlat << 1) ^ (dlat >> 31)
            while dlat >= 0x20:
                result.append(chr((0x20 | (dlat & 0x1f)) + 63))
                dlat >>= 5
            result.append(chr(dlat + 63))
            
            # Encode longitude
            dlng = (dlng << 1) ^ (dlng >> 31)
            while dlng >= 0x20:
                result.append(chr((0x20 | (dlng & 0x1f)) + 63))
                dlng >>= 5
            result.append(chr(dlng + 63))
        
        return ''.join(result)


# ============================================================================
# Color Helpers
# ============================================================================

class ColorHelper:
    """Helper functions for color manipulation."""
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c * 2 for c in hex_color)
        return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB to hex color."""
        return '#{:02x}{:02x}{:02x}'.format(r, g, b)
    
    @staticmethod
    def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
        """Convert RGB to HSL."""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        delta = max_val - min_val
        
        # Hue
        if delta == 0:
            h = 0
        elif max_val == r:
            h = ((g - b) / delta) % 6
        elif max_val == g:
            h = ((b - r) / delta) + 2
        else:
            h = ((r - g) / delta) + 4
        
        h = h * 60
        
        # Lightness
        l = (max_val + min_val) / 2
        
        # Saturation
        if delta == 0:
            s = 0
        else:
            s = delta / (1 - abs(2 * l - 1))
        
        return h, s, l
    
    @staticmethod
    def hsl_to_rgb(h: float, s: float, l: float) -> Tuple[int, int, int]:
        """Convert HSL to RGB."""
        h = h / 360
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h * 6) % 2 - 1))
        m = l - c / 2
        
        if h < 1 / 6:
            r, g, b = c, x, 0
        elif h < 1 / 3:
            r, g, b = x, c, 0
        elif h < 1 / 2:
            r, g, b = 0, c, x
        elif h < 2 / 3:
            r, g, b = 0, x, c
        elif h < 5 / 6:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        return (
            int((r + m) * 255),
            int((g + m) * 255),
            int((b + m) * 255)
        )
    
    @staticmethod
    def brightness(r: int, g: int, b: int) -> float:
        """Calculate perceived brightness (0-1)."""
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255
    
    @staticmethod
    def is_light(r: int, g: int, b: int) -> bool:
        """Check if color is light."""
        return ColorHelper.brightness(r, g, b) > 0.5
    
    @staticmethod
    def is_dark(r: int, g: int, b: int) -> bool:
        """Check if color is dark."""
        return not ColorHelper.is_light(r, g, b)
    
    @staticmethod
    def blend(color1: Tuple[int, int, int], color2: Tuple[int, int, int], ratio: float = 0.5) -> Tuple[int, int, int]:
        """Blend two colors."""
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        return (r, g, b)
    
    @staticmethod
    def lighten(color: Tuple[int, int, int], factor: float = 0.2) -> Tuple[int, int, int]:
        """Lighten a color."""
        r = min(255, int(color[0] + (255 - color[0]) * factor))
        g = min(255, int(color[1] + (255 - color[1]) * factor))
        b = min(255, int(color[2] + (255 - color[2]) * factor))
        return (r, g, b)
    
    @staticmethod
    def darken(color: Tuple[int, int, int], factor: float = 0.2) -> Tuple[int, int, int]:
        """Darken a color."""
        r = max(0, int(color[0] * (1 - factor)))
        g = max(0, int(color[1] * (1 - factor)))
        b = max(0, int(color[2] * (1 - factor)))
        return (r, g, b)
    
    @staticmethod
    def complementary(color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Get complementary color."""
        r, g, b = color
        return (255 - r, 255 - g, 255 - b)
    
    @staticmethod
    def random() -> Tuple[int, int, int]:
        """Generate random color."""
        return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Dictionary helpers
    'DictHelper',
    
    # List helpers
    'ListHelper',
    
    # String helpers
    'StringHelper',
    
    # Number helpers
    'NumberHelper',
    
    # Date/Time helpers
    'DateTimeHelper',
    
    # Math helpers
    'MathHelper',
    
    # Geo helpers
    'GeoHelper',
    
    # Color helpers
    'ColorHelper',
]

# Convenience aliases
dict_helper = DictHelper()
list_helper = ListHelper()
string_helper = StringHelper()
number_helper = NumberHelper()
datetime_helper = DateTimeHelper()
math_helper = MathHelper()
geo_helper = GeoHelper()
color_helper = ColorHelper()