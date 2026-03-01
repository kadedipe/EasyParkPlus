"""Helper utility functions for the parking management system.

This module provides common helper functions for string manipulation,
number processing, collection handling, object operations, file management,
encoding, formatting, and type conversion.
"""

import re
import json
import hashlib
import secrets
import string
import uuid
import base64
import html
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Tuple, Set
from collections.abc import Iterable
import inspect
import os
import sys
import psutil
import time
import functools
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for generic functions
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

# ============================================================================
# String Helpers
# ============================================================================

def slugify(text: str, max_length: int = 100) -> str:
    """Convert text to URL-friendly slug.
    
    Args:
        text: Input text
        max_length: Maximum length of slug
        
    Returns:
        URL-friendly slug
    """
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    
    # Remove leading/trailing hyphens
    text = text.strip('-')
    
    # Truncate
    if len(text) > max_length:
        text = text[:max_length].rstrip('-')
    
    return text


def truncate(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """Truncate text to specified length.
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rstrip() + suffix


def random_string(length: int = 10, include_digits: bool = True, include_special: bool = False) -> str:
    """Generate random string.
    
    Args:
        length: Length of string
        include_digits: Include digits
        include_special: Include special characters
        
    Returns:
        Random string
    """
    chars = string.ascii_letters
    if include_digits:
        chars += string.digits
    if include_special:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    return ''.join(secrets.choice(chars) for _ in range(length))


def random_digits(length: int = 6) -> str:
    """Generate random digit string.
    
    Args:
        length: Length of digit string
        
    Returns:
        Random digits
    """
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def format_currency(amount: float, currency: str = 'USD', locale: str = 'en_US') -> str:
    """Format amount as currency.
    
    Args:
        amount: Amount to format
        currency: Currency code (USD, EUR, etc.)
        locale: Locale for formatting
        
    Returns:
        Formatted currency string
    """
    symbols = {
        'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥',
        'CAD': 'C$', 'AUD': 'A$', 'CHF': 'Fr', 'CNY': '¥'
    }
    symbol = symbols.get(currency, '$')
    
    # Simple formatting (for production, use babel or locale modules)
    if currency in ['JPY']:
        return f"{symbol}{amount:,.0f}"
    else:
        return f"{symbol}{amount:,.2f}"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """Format as percentage.
    
    Args:
        value: Value to format (0.15 = 15%)
        decimal_places: Number of decimal places
        
    Returns:
        Formatted percentage
    """
    return f"{value * 100:.{decimal_places}f}%"


def strip_html(html_text: str) -> str:
    """Remove HTML tags from text.
    
    Args:
        html_text: HTML text
        
    Returns:
        Plain text
    """
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)
    # Replace HTML entities
    text = html.unescape(text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def escape_markdown(text: str) -> str:
    """Escape Markdown special characters.
    
    Args:
        text: Text to escape
        
    Returns:
        Escaped text
    """
    special_chars = r'_*[]()~`>#+-=|{}.!'
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case.
    
    Args:
        name: camelCase string
        
    Returns:
        snake_case string
    """
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return name.lower()


def snake_to_camel(name: str, upper_first: bool = False) -> str:
    """Convert snake_case to camelCase.
    
    Args:
        name: snake_case string
        upper_first: Whether to uppercase first letter (PascalCase)
        
    Returns:
        camelCase or PascalCase string
    """
    components = name.split('_')
    if upper_first:
        return ''.join(x.title() for x in components)
    else:
        return components[0] + ''.join(x.title() for x in components[1:])


def pluralize(word: str, count: int = 2) -> str:
    """Simple pluralization (for basic cases).
    
    Args:
        word: Word to pluralize
        count: Count (1 for singular)
        
    Returns:
        Pluralized word if count != 1
    """
    if count == 1:
        return word
    
    # Simple rules (for production, use inflect library)
    if word.endswith('y') and not word.endswith(('ay', 'ey', 'iy', 'oy', 'uy')):
        return word[:-1] + 'ies'
    elif word.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return word + 'es'
    else:
        return word + 's'


def singularize(word: str) -> str:
    """Simple singularization (for basic cases).
    
    Args:
        word: Word to singularize
        
    Returns:
        Singularized word
    """
    if word.endswith('ies'):
        return word[:-3] + 'y'
    elif word.endswith(('ses', 'xes', 'zes', 'ches', 'shes')):
        return word[:-2]
    elif word.endswith('s') and not word.endswith('ss'):
        return word[:-1]
    else:
        return word


# ============================================================================
# Number Helpers
# ============================================================================

def round_up(value: float, decimals: int = 0) -> float:
    """Round up to specified decimal places.
    
    Args:
        value: Value to round
        decimals: Number of decimal places
        
    Returns:
        Rounded value
    """
    import math
    factor = 10 ** decimals
    return math.ceil(value * factor) / factor


def round_down(value: float, decimals: int = 0) -> float:
    """Round down to specified decimal places.
    
    Args:
        value: Value to round
        decimals: Number of decimal places
        
    Returns:
        Rounded value
    """
    import math
    factor = 10 ** decimals
    return math.floor(value * factor) / factor


def round_to_nearest(value: float, nearest: float = 1.0) -> float:
    """Round to nearest specified value.
    
    Args:
        value: Value to round
        nearest: Round to nearest this value
        
    Returns:
        Rounded value
    """
    return round(value / nearest) * nearest


def clamp(value: Union[int, float], min_value: Union[int, float], max_value: Union[int, float]) -> Union[int, float]:
    """Clamp value between min and max.
    
    Args:
        value: Value to clamp
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Clamped value
    """
    return max(min_value, min(value, max_value))


def lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation between start and end.
    
    Args:
        start: Start value
        end: End value
        t: Interpolation factor (0-1)
        
    Returns:
        Interpolated value
    """
    return start + (end - start) * t


def normalize(value: float, min_value: float, max_value: float) -> float:
    """Normalize value to 0-1 range.
    
    Args:
        value: Value to normalize
        min_value: Minimum possible value
        max_value: Maximum possible value
        
    Returns:
        Normalized value (0-1)
    """
    if max_value == min_value:
        return 0
    return (value - min_value) / (max_value - min_value)


def denormalize(value: float, min_value: float, max_value: float) -> float:
    """Convert normalized value back to original range.
    
    Args:
        value: Normalized value (0-1)
        min_value: Minimum possible value
        max_value: Maximum possible value
        
    Returns:
        Denormalized value
    """
    return min_value + (value * (max_value - min_value))


# ============================================================================
# Collection Helpers
# ============================================================================

def chunk_list(items: List[T], chunk_size: int) -> List[List[T]]:
    """Split list into chunks of specified size.
    
    Args:
        items: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def flatten_list(nested_list: List[Any]) -> List[Any]:
    """Flatten nested list.
    
    Args:
        nested_list: Nested list
        
    Returns:
        Flattened list
    """
    result = []
    for item in nested_list:
        if isinstance(item, list):
            result.extend(flatten_list(item))
        else:
            result.append(item)
    return result


def unique_list(items: List[T], key: Optional[Callable[[T], Any]] = None) -> List[T]:
    """Get unique items from list while preserving order.
    
    Args:
        items: List of items
        key: Optional key function for comparison
        
    Returns:
        List with unique items
    """
    seen = set()
    result = []
    
    for item in items:
        if key:
            comp = key(item)
        else:
            comp = item
        
        if comp not in seen:
            seen.add(comp)
            result.append(item)
    
    return result


def group_by(items: List[T], key_func: Callable[[T], K]) -> Dict[K, List[T]]:
    """Group items by key function.
    
    Args:
        items: List of items
        key_func: Function to generate group key
        
    Returns:
        Dictionary mapping keys to lists of items
    """
    result = {}
    for item in items:
        key = key_func(item)
        if key not in result:
            result[key] = []
        result[key].append(item)
    return result


def key_by(items: List[T], key_func: Callable[[T], K]) -> Dict[K, T]:
    """Create dictionary keyed by key function.
    
    Args:
        items: List of items
        key_func: Function to generate key
        
    Returns:
        Dictionary mapping keys to items
        
    Raises:
        ValueError: If duplicate keys found
    """
    result = {}
    for item in items:
        key = key_func(item)
        if key in result:
            raise ValueError(f"Duplicate key: {key}")
        result[key] = item
    return result


def pluck(items: List[Dict], key: str, default: Any = None) -> List[Any]:
    """Extract values by key from list of dictionaries.
    
    Args:
        items: List of dictionaries
        key: Key to extract
        default: Default value if key missing
        
    Returns:
        List of extracted values
    """
    return [item.get(key, default) for item in items]


def sort_by(
    items: List[T],
    key_func: Callable[[T], Any],
    reverse: bool = False
) -> List[T]:
    """Sort items by key function.
    
    Args:
        items: List of items
        key_func: Function to generate sort key
        reverse: Sort in reverse order
        
    Returns:
        Sorted list
    """
    return sorted(items, key=key_func, reverse=reverse)


def filter_by(
    items: List[T],
    predicate: Callable[[T], bool]
) -> List[T]:
    """Filter items by predicate.
    
    Args:
        items: List of items
        predicate: Filter function
        
    Returns:
        Filtered list
    """
    return [item for item in items if predicate(item)]


def paginate_list(
    items: List[T],
    page: int = 1,
    per_page: int = 20
) -> Tuple[List[T], int, int, int]:
    """Paginate a list.
    
    Args:
        items: List to paginate
        page: Page number (1-indexed)
        per_page: Items per page
        
    Returns:
        Tuple of (paginated_items, total_items, total_pages, current_page)
    """
    total = len(items)
    total_pages = (total + per_page - 1) // per_page
    
    start = (page - 1) * per_page
    end = start + per_page
    
    paginated = items[start:end] if start < total else []
    
    return paginated, total, total_pages, page


# ============================================================================
# Dictionary Helpers
# ============================================================================

def deep_get(obj: Dict, path: str, default: Any = None) -> Any:
    """Get nested dictionary value by dot-separated path.
    
    Args:
        obj: Dictionary to traverse
        path: Dot-separated path (e.g., "user.address.city")
        default: Default value if path not found
        
    Returns:
        Value at path or default
    """
    keys = path.split('.')
    value = obj
    
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default
        
        if value is None:
            return default
    
    return value


def deep_set(obj: Dict, path: str, value: Any) -> Dict:
    """Set nested dictionary value by dot-separated path.
    
    Args:
        obj: Dictionary to modify
        path: Dot-separated path
        value: Value to set
        
    Returns:
        Modified dictionary
    """
    keys = path.split('.')
    current = obj
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value
    return obj


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def pick(obj: Dict, keys: List[str]) -> Dict:
    """Pick specified keys from dictionary.
    
    Args:
        obj: Source dictionary
        keys: Keys to pick
        
    Returns:
        Dictionary with picked keys
    """
    return {key: obj[key] for key in keys if key in obj}


def omit(obj: Dict, keys: List[str]) -> Dict:
    """Omit specified keys from dictionary.
    
    Args:
        obj: Source dictionary
        keys: Keys to omit
        
    Returns:
        Dictionary without omitted keys
    """
    return {key: value for key, value in obj.items() if key not in keys}


def rename_key(obj: Dict, old_key: str, new_key: str) -> Dict:
    """Rename a key in dictionary.
    
    Args:
        obj: Source dictionary
        old_key: Key to rename
        new_key: New key name
        
    Returns:
        Dictionary with renamed key
    """
    if old_key in obj:
        obj[new_key] = obj.pop(old_key)
    return obj


def flatten_dict(obj: Dict, parent_key: str = '', separator: str = '.') -> Dict:
    """Flatten nested dictionary.
    
    Args:
        obj: Nested dictionary
        parent_key: Parent key for recursion
        separator: Separator for keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for key, value in obj.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, separator).items())
        else:
            items.append((new_key, value))
    
    return dict(items)


def unflatten_dict(obj: Dict, separator: str = '.') -> Dict:
    """Unflatten flattened dictionary.
    
    Args:
        obj: Flattened dictionary
        separator: Separator used in keys
        
    Returns:
        Nested dictionary
    """
    result = {}
    
    for key, value in obj.items():
        parts = key.split(separator)
        current = result
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    return result


# ============================================================================
# Object Helpers
# ============================================================================

def get_class_name(obj: Any) -> str:
    """Get class name of object.
    
    Args:
        obj: Object
        
    Returns:
        Class name
    """
    return obj.__class__.__name__


def get_methods(obj: Any, include_private: bool = False) -> List[str]:
    """Get list of method names for object.
    
    Args:
        obj: Object
        include_private: Include private methods
        
    Returns:
        List of method names
    """
    methods = []
    for name in dir(obj):
        if not include_private and name.startswith('_'):
            continue
        if callable(getattr(obj, name)):
            methods.append(name)
    return methods


def has_attribute(obj: Any, attr: str) -> bool:
    """Check if object has attribute.
    
    Args:
        obj: Object
        attr: Attribute name
        
    Returns:
        True if attribute exists
    """
    return hasattr(obj, attr)


def copy_attributes(source: Any, target: Any, attributes: List[str]) -> None:
    """Copy attributes from source to target.
    
    Args:
        source: Source object
        target: Target object
        attributes: List of attribute names to copy
    """
    for attr in attributes:
        if hasattr(source, attr):
            setattr(target, attr, getattr(source, attr))


# ============================================================================
# File Helpers
# ============================================================================

def get_file_extension(filename: str) -> str:
    """Get file extension from filename.
    
    Args:
        filename: Filename
        
    Returns:
        File extension (without dot)
    """
    return filename.split('.')[-1].lower() if '.' in filename else ''


def get_file_size_str(size_bytes: int) -> str:
    """Convert bytes to human readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def is_image_file(filename: str) -> bool:
    """Check if file is an image based on extension.
    
    Args:
        filename: Filename
        
    Returns:
        True if image file
    """
    image_extensions = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'}
    return get_file_extension(filename) in image_extensions


def is_video_file(filename: str) -> bool:
    """Check if file is a video based on extension.
    
    Args:
        filename: Filename
        
    Returns:
        True if video file
    """
    video_extensions = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm'}
    return get_file_extension(filename) in video_extensions


def is_document_file(filename: str) -> bool:
    """Check if file is a document based on extension.
    
    Args:
        filename: Filename
        
    Returns:
        True if document file
    """
    doc_extensions = {'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'xls', 'xlsx', 'ppt', 'pptx'}
    return get_file_extension(filename) in doc_extensions


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to be safe for filesystem.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove invalid characters
    filename = re.sub(r'[<>:"|?*]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:250] + (f'.{ext}' if ext else '')
    
    return filename or 'unnamed'


def get_unique_filename(filename: str) -> str:
    """Generate unique filename by adding timestamp.
    
    Args:
        filename: Original filename
        
    Returns:
        Unique filename
    """
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_name = f"{name}_{timestamp}"
    return f"{unique_name}.{ext}" if ext else unique_name


# ============================================================================
# Encoding Helpers
# ============================================================================

def base64_encode(data: Union[str, bytes]) -> str:
    """Base64 encode data.
    
    Args:
        data: Data to encode
        
    Returns:
        Base64 encoded string
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.b64encode(data).decode('utf-8')


def base64_decode(data: str) -> bytes:
    """Base64 decode data.
    
    Args:
        data: Base64 encoded string
        
    Returns:
        Decoded bytes
    """
    return base64.b64decode(data)


def url_encode(data: str) -> str:
    """URL encode string.
    
    Args:
        data: String to encode
        
    Returns:
        URL encoded string
    """
    return urllib.parse.quote(data)


def url_decode(data: str) -> str:
    """URL decode string.
    
    Args:
        data: URL encoded string
        
    Returns:
        Decoded string
    """
    return urllib.parse.unquote(data)


def html_encode(data: str) -> str:
    """HTML encode string.
    
    Args:
        data: String to encode
        
    Returns:
        HTML encoded string
    """
    return html.escape(data)


def html_decode(data: str) -> str:
    """HTML decode string.
    
    Args:
        data: HTML encoded string
        
    Returns:
        Decoded string
    """
    return html.unescape(data)


# ============================================================================
# Hash Helpers
# ============================================================================

def md5_hash(data: Union[str, bytes]) -> str:
    """Generate MD5 hash.
    
    Args:
        data: Data to hash
        
    Returns:
        MD5 hash hex digest
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.md5(data).hexdigest()


def sha1_hash(data: Union[str, bytes]) -> str:
    """Generate SHA-1 hash.
    
    Args:
        data: Data to hash
        
    Returns:
        SHA-1 hash hex digest
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha1(data).hexdigest()


def sha256_hash(data: Union[str, bytes]) -> str:
    """Generate SHA-256 hash.
    
    Args:
        data: Data to hash
        
    Returns:
        SHA-256 hash hex digest
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def generate_uuid() -> str:
    """Generate UUID v4.
    
    Returns:
        UUID string
    """
    return str(uuid.uuid4())


def generate_short_uuid(length: int = 8) -> str:
    """Generate short UUID (first N characters of UUID).
    
    Args:
        length: Length of short UUID
        
    Returns:
        Short UUID string
    """
    return generate_uuid()[:length]


# ============================================================================
# Format Helpers
# ============================================================================

def format_bytes(bytes: int) -> str:
    """Convert bytes to human readable string.
    
    Args:
        bytes: Size in bytes
        
    Returns:
        Human readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} EB"


def format_duration(seconds: int, include_seconds: bool = True) -> str:
    """Format duration in seconds to human readable string.
    
    Args:
        seconds: Duration in seconds
        include_seconds: Include seconds in output
        
    Returns:
        Human readable duration string
    """
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if include_seconds and (seconds > 0 or not parts):
        parts.append(f"{seconds}s")
    
    return ' '.join(parts)


def format_phone_display(phone: str) -> str:
    """Format phone number for display.
    
    Args:
        phone: Raw phone number
        
    Returns:
        Formatted phone number
    """
    # Remove non-digits
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        # International format
        return f"+{digits}"


def format_address(
    street: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    country: Optional[str] = None
) -> str:
    """Format address components into single string.
    
    Args:
        street: Street address
        city: City
        state: State/Province
        zip_code: ZIP/Postal code
        country: Country
        
    Returns:
        Formatted address
    """
    parts = []
    if street:
        parts.append(street)
    if city:
        parts.append(city)
    if state:
        parts.append(state)
    if zip_code:
        parts.append(zip_code)
    if country:
        parts.append(country)
    
    return ', '.join(parts)


def format_name(
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    middle_name: Optional[str] = None,
    title: Optional[str] = None,
    suffix: Optional[str] = None
) -> str:
    """Format name components into full name.
    
    Args:
        first_name: First name
        last_name: Last name
        middle_name: Middle name/initial
        title: Title (Mr., Mrs., Dr., etc.)
        suffix: Suffix (Jr., Sr., III, etc.)
        
    Returns:
        Formatted full name
    """
    parts = []
    if title:
        parts.append(title)
    if first_name:
        parts.append(first_name)
    if middle_name:
        parts.append(middle_name)
    if last_name:
        parts.append(last_name)
    if suffix:
        parts.append(suffix)
    
    return ' '.join(parts)


def truncate_middle(text: str, max_length: int = 50, separator: str = '...') -> str:
    """Truncate text in the middle.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        separator: Separator to insert in middle
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    half = (max_length - len(separator)) // 2
    return text[:half] + separator + text[-half:]


# ============================================================================
# Type Conversion Helpers
# ============================================================================

def to_bool(value: Any) -> bool:
    """Convert value to boolean.
    
    Args:
        value: Value to convert
        
    Returns:
        Boolean value
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'y', 'on')
    if isinstance(value, (list, dict, tuple)):
        return len(value) > 0
    return bool(value)


def to_int(value: Any, default: int = 0) -> int:
    """Convert value to integer.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def to_str(value: Any, default: str = '') -> str:
    """Convert value to string.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        String value
    """
    try:
        if value is None:
            return default
        return str(value)
    except Exception:
        return default


def to_list(value: Any, split_strings: bool = False) -> List:
    """Convert value to list.
    
    Args:
        value: Value to convert
        split_strings: Split strings by comma
        
    Returns:
        List value
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    if isinstance(value, str) and split_strings:
        return [item.strip() for item in value.split(',') if item.strip()]
    return [value]


def to_dict(value: Any, default: Dict = None) -> Dict:
    """Convert value to dictionary.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Dictionary value
    """
    if default is None:
        default = {}
    
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def to_datetime(value: Any) -> Optional[datetime]:
    """Convert value to datetime.
    
    Args:
        value: Value to convert
        
    Returns:
        Datetime or None if conversion fails
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            pass
    return None


# ============================================================================
# Environment Helpers
# ============================================================================

def is_development() -> bool:
    """Check if running in development environment.
    
    Returns:
        True if development
    """
    return os.getenv('ENVIRONMENT', '').lower() == 'development'


def is_production() -> bool:
    """Check if running in production environment.
    
    Returns:
        True if production
    """
    return os.getenv('ENVIRONMENT', '').lower() == 'production'


def is_testing() -> bool:
    """Check if running in testing environment.
    
    Returns:
        True if testing
    """
    return os.getenv('ENVIRONMENT', '').lower() == 'testing' or 'pytest' in sys.modules


def get_env_var(key: str, default: Any = None) -> Any:
    """Get environment variable with default.
    
    Args:
        key: Environment variable key
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default)


# ============================================================================
# Debug Helpers
# ============================================================================

def dump_object(obj: Any, max_depth: int = 3) -> str:
    """Dump object attributes for debugging.
    
    Args:
        obj: Object to dump
        max_depth: Maximum recursion depth
        
    Returns:
        String representation of object
    """
    def _dump(obj, depth):
        if depth > max_depth:
            return '...'
        
        if isinstance(obj, (str, int, float, bool, type(None))):
            return repr(obj)
        
        if isinstance(obj, (list, tuple, set)):
            items = [_dump(item, depth + 1) for item in list(obj)[:5]]
            if len(obj) > 5:
                items.append('...')
            return f"[{', '.join(items)}]"
        
        if isinstance(obj, dict):
            items = []
            for key, value in list(obj.items())[:5]:
                items.append(f"{key}: {_dump(value, depth + 1)}")
            if len(obj) > 5:
                items.append('...')
            return f"{{{', '.join(items)}}}"
        
        # For custom objects
        attrs = []
        for attr in dir(obj):
            if not attr.startswith('_') and not callable(getattr(obj, attr)):
                try:
                    value = getattr(obj, attr)
                    attrs.append(f"{attr}={_dump(value, depth + 1)}")
                except Exception:
                    attrs.append(f"{attr}=<error>")
        
        return f"{obj.__class__.__name__}({', '.join(attrs[:10])})"
    
    return _dump(obj, 0)


def pretty_print(obj: Any) -> None:
    """Pretty print object for debugging.
    
    Args:
        obj: Object to print
    """
    import pprint
    pprint.pprint(obj)


def get_memory_usage() -> Dict[str, Any]:
    """Get current memory usage.
    
    Returns:
        Dictionary with memory usage information
    """
    process = psutil.Process()
    memory_info = process.memory_info()
    
    return {
        'rss': memory_info.rss,
        'rss_human': format_bytes(memory_info.rss),
        'vms': memory_info.vms,
        'vms_human': format_bytes(memory_info.vms),
        'percent': process.memory_percent(),
    }


def get_cpu_usage() -> Dict[str, Any]:
    """Get current CPU usage.
    
    Returns:
        Dictionary with CPU usage information
    """
    process = psutil.Process()
    
    return {
        'percent': process.cpu_percent(interval=0.1),
        'num_threads': process.num_threads(),
        'times': process.cpu_times()._asdict(),
    }


def time_function(func: Callable) -> Callable:
    """Decorator to time function execution.
    
    Args:
        func: Function to time
        
    Returns:
        Wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logger.debug(f"{func.__name__} took {end - start:.3f} seconds")
        return result
    return wrapper


def async_time_function(func: Callable) -> Callable:
    """Decorator to time async function execution.
    
    Args:
        func: Async function to time
        
    Returns:
        Wrapped async function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        end = time.time()
        logger.debug(f"{func.__name__} took {end - start:.3f} seconds")
        return result
    return wrapper


# ============================================================================
# Common Constants
# ============================================================================

# Common regular expressions
REGEX_EMAIL = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
REGEX_PHONE = re.compile(r'^\+?[1-9]\d{1,14}$')
REGEX_URL = re.compile(r'^https?://[^\s/$.?#].[^\s]*$', re.I)
REGEX_ALPHANUMERIC = re.compile(r'^[a-zA-Z0-9]+$')
REGEX_SLUG = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')

# Common HTTP status codes
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_409_CONFLICT = 409
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_500_INTERNAL_SERVER_ERROR = 500