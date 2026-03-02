"""Utils package initialization for the parking management system.

This module exports all utility functions and classes and provides
a centralized interface for common utility operations.
"""

from typing import Dict, Any, List, Optional, Type, Union
import logging
from datetime import datetime, date, time

# Import all utility modules
from .datetime_utils import (
    now,
    today,
    format_datetime,
    parse_datetime,
    is_business_hours,
    get_next_business_open,
    calculate_duration_minutes,
    calculate_duration_hours,
    add_minutes,
    add_hours,
    add_days,
    get_date_range,
    get_month_dates,
    is_overlapping,
    get_overlap_duration,
    to_timezone_naive,
    get_week_start,
    get_week_end,
    get_month_start,
    get_month_end,
    get_quarter_start,
    get_quarter_end,
    get_year_start,
    get_year_end,
    get_age_from_birthdate,
    get_time_ago,
    get_relative_time_string,
)

from .validators import (
    # Email validation
    validate_email,
    validate_email_domain,
    
    # Phone validation
    validate_phone,
    validate_phone_international,
    format_phone,
    
    # Password validation
    validate_password_strength,
    validate_password_match,
    generate_random_password,
    
    # License plate validation
    validate_license_plate,
    format_license_plate,
    get_license_plate_country,
    
    # Credit card validation
    validate_credit_card,
    get_card_type,
    mask_credit_card,
    
    # Date validation
    validate_date_range,
    validate_future_date,
    validate_past_date,
    validate_business_hours,
    validate_within_business_hours,
    
    # Number validation
    validate_positive_number,
    validate_range,
    validate_percentage,
    validate_currency,
    
    # Text validation
    validate_not_empty,
    validate_length,
    validate_alphanumeric,
    validate_no_special_chars,
    validate_pattern,
    
    # URL validation
    validate_url,
    validate_image_url,
    
    # ID validation
    validate_user_id,
    validate_reservation_id,
    validate_spot_id,
    validate_vehicle_id,
    validate_payment_id,
    
    # Business rules
    validate_reservation_time,
    validate_cancellation_window,
    validate_spot_compatibility,
    validate_user_eligibility,
    
    # Schema validation
    validate_json_schema,
    validate_dict_structure,
    validate_required_fields,
)

from .helpers import (
    # String helpers
    slugify,
    truncate,
    random_string,
    random_digits,
    format_currency,
    format_percentage,
    strip_html,
    escape_markdown,
    camel_to_snake,
    snake_to_camel,
    pluralize,
    singularize,
    
    # Number helpers
    round_up,
    round_down,
    round_to_nearest,
    clamp,
    lerp,
    normalize,
    denormalize,
    
    # Collection helpers
    chunk_list,
    flatten_list,
    unique_list,
    group_by,
    key_by,
    pluck,
    sort_by,
    filter_by,
    paginate_list,
    
    # Dict helpers
    deep_get,
    deep_set,
    deep_merge,
    pick,
    omit,
    rename_key,
    flatten_dict,
    unflatten_dict,
    
    # Object helpers
    get_class_name,
    get_methods,
    has_attribute,
    copy_attributes,
    
    # File helpers
    get_file_extension,
    get_file_size_str,
    is_image_file,
    is_video_file,
    is_document_file,
    sanitize_filename,
    get_unique_filename,
    
    # Encoding helpers
    base64_encode,
    base64_decode,
    url_encode,
    url_decode,
    html_encode,
    html_decode,
    
    # Hash helpers
    md5_hash,
    sha1_hash,
    sha256_hash,
    generate_uuid,
    generate_short_uuid,
    
    # Format helpers
    format_bytes,
    format_duration,
    format_phone_display,
    format_address,
    format_name,
    truncate_middle,
    
    # Type conversion
    to_bool,
    to_int,
    to_float,
    to_str,
    to_list,
    to_dict,
    to_datetime,
    
    # Environment helpers
    is_development,
    is_production,
    is_testing,
    get_env_var,
    
    # Debug helpers
    dump_object,
    pretty_print,
    get_memory_usage,
    get_cpu_usage,
    time_function,
    async_time_function,
)

from .encryption import (
    encrypt_data,
    decrypt_data,
    encrypt_string,
    decrypt_string,
    hash_data,
    verify_hash,
    generate_salt,
    generate_key,
    encrypt_file,
    decrypt_file,
    sign_data,
    verify_signature,
    get_public_key,
    get_private_key,
)

from .logging_utils import (
    setup_logging,
    get_logger,
    log_function_call,
    log_async_function_call,
    log_exception,
    log_performance,
    LogContext,
    JsonFormatter,
    SensitiveDataFilter,
    RequestIdFilter,
    UserIdFilter,
)

from .cache_utils import (
    cached,
    async_cached,
    cache_key,
    invalidate_cache,
    CacheManager,
    LocalCache,
    RedisCache,
    NullCache,
    cache_decorator,
    memoize,
    ttl_cache,
)

from .geo_utils import (
    calculate_distance,
    calculate_bearing,
    get_lat_lng_from_address,
    get_address_from_lat_lng,
    get_timezone_from_lat_lng,
    is_point_in_polygon,
    calculate_parking_spot_area,
    get_nearest_spots,
    format_coordinates,
    parse_coordinates,
    validate_coordinates,
    EARTH_RADIUS_KM,
    EARTH_RADIUS_MILES,
)

from .price_utils import (
    calculate_hourly_price,
    calculate_daily_price,
    calculate_weekly_price,
    calculate_monthly_price,
    calculate_overnight_price,
    apply_discount,
    apply_tax,
    calculate_total,
    calculate_refund,
    calculate_penalty,
    calculate_deposit,
    round_price,
    format_price,
    PriceCalculator,
    DiscountCalculator,
    TaxCalculator,
)

from .image_utils import (
    resize_image,
    crop_image,
    rotate_image,
    add_watermark,
    get_image_dimensions,
    validate_image,
    optimize_image,
    convert_image_format,
    create_thumbnail,
    extract_exif,
    remove_exif,
    ImageProcessor,
)

from .csv_utils import (
    read_csv,
    write_csv,
    read_csv_to_dicts,
    write_dicts_to_csv,
    validate_csv,
    parse_csv_row,
    CsvReader,
    CsvWriter,
)

from .excel_utils import (
    read_excel,
    write_excel,
    read_excel_to_dicts,
    write_dicts_to_excel,
    validate_excel,
    ExcelReader,
    ExcelWriter,
)

from .pdf_utils import (
    generate_pdf,
    generate_invoice_pdf,
    generate_report_pdf,
    merge_pdfs,
    split_pdf,
    extract_text_from_pdf,
    PdfGenerator,
)

from .qr_utils import (
    generate_qr_code,
    generate_qr_code_base64,
    read_qr_code,
    generate_qr_for_payment,
    generate_qr_for_ticket,
    generate_qr_for_verification,
)

from .sms_utils import (
    format_sms_message,
    validate_phone_for_sms,
    split_long_message,
    SmsSender,
)

from .email_utils import (
    send_email,
    send_template_email,
    validate_email_address,
    format_email_address,
    EmailSender,
    EmailTemplate,
)

from .push_utils import (
    send_push_notification,
    send_bulk_push,
    format_push_message,
    PushSender,
)

from .webhook_utils import (
    send_webhook,
    verify_webhook_signature,
    parse_webhook_payload,
    WebhookClient,
)

from .export_utils import (
    export_to_csv,
    export_to_excel,
    export_to_json,
    export_to_pdf,
    export_to_xml,
    DataExporter,
)

from .import_utils import (
    import_from_csv,
    import_from_excel,
    import_from_json,
    import_from_xml,
    DataImporter,
    ImportValidator,
)

from .report_utils import (
    generate_report,
    ReportGenerator,
    ChartGenerator,
    DataAggregator,
    ReportFormatter,
)

from .analytics_utils import (
    track_event,
    track_page_view,
    track_user_action,
    AnalyticsTracker,
)

from .test_utils import (
    create_test_user,
    create_test_reservation,
    create_test_payment,
    create_test_vehicle,
    create_test_parking_spot,
    MockDatabase,
    TestClient,
    TestDataFactory,
)

# Configure module logger
logger = logging.getLogger(__name__)


# Utility class for common operations
class Utils:
    """Centralized utility class for common operations."""
    
    @staticmethod
    def now() -> datetime:
        """Get current UTC datetime."""
        return now()
    
    @staticmethod
    def today() -> date:
        """Get current UTC date."""
        return today()
    
    @staticmethod
    def format_currency(amount: float, currency: str = "USD") -> str:
        """Format amount as currency."""
        return format_currency(amount, currency)
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address."""
        return validate_email(email)
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number."""
        return validate_phone(phone)
    
    @staticmethod
    def slugify(text: str) -> str:
        """Convert text to URL-friendly slug."""
        return slugify(text)
    
    @staticmethod
    def generate_uuid() -> str:
        """Generate UUID."""
        return generate_uuid()
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate random string."""
        return random_string(length)
    
    @staticmethod
    def calculate_distance(
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float,
        unit: str = "km"
    ) -> float:
        """Calculate distance between two coordinates."""
        return calculate_distance(lat1, lng1, lat2, lng2, unit)
    
    @staticmethod
    def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
        """Split list into chunks."""
        return chunk_list(items, chunk_size)
    
    @staticmethod
    def deep_get(obj: Dict, path: str, default: Any = None) -> Any:
        """Get nested dictionary value by path."""
        return deep_get(obj, path, default)
    
    @staticmethod
    def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
        """Deep merge two dictionaries."""
        return deep_merge(dict1, dict2)
    
    @staticmethod
    def format_bytes(bytes: int) -> str:
        """Format bytes to human readable string."""
        return format_bytes(bytes)
    
    @staticmethod
    def format_duration(seconds: int) -> str:
        """Format duration to human readable string."""
        return format_duration(seconds)
    
    @staticmethod
    def get_time_ago(dt: datetime) -> str:
        """Get human readable time ago string."""
        return get_time_ago(dt)
    
    @staticmethod
    def encrypt_string(text: str, key: Optional[str] = None) -> str:
        """Encrypt string."""
        return encrypt_string(text, key)
    
    @staticmethod
    def decrypt_string(encrypted: str, key: Optional[str] = None) -> str:
        """Decrypt string."""
        return decrypt_string(encrypted, key)
    
    @staticmethod
    def hash_data(data: str, algorithm: str = "sha256") -> str:
        """Hash data."""
        return hash_data(data, algorithm)
    
    @staticmethod
    def is_development() -> bool:
        """Check if running in development environment."""
        return is_development()
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production environment."""
        return is_production()


# Convenience functions for common operations
def utc_now() -> datetime:
    """Get current UTC datetime (alias for now)."""
    return now()


def utc_today() -> date:
    """Get current UTC date (alias for today)."""
    return today()


def format_money(amount: float, currency: str = "USD") -> str:
    """Format money amount (alias for format_currency)."""
    return format_currency(amount, currency)


def is_valid_email(email: str) -> bool:
    """Check if email is valid (alias for validate_email)."""
    return validate_email(email)


def is_valid_phone(phone: str) -> bool:
    """Check if phone is valid (alias for validate_phone)."""
    return validate_phone(phone)


def generate_id() -> str:
    """Generate unique ID (alias for generate_uuid)."""
    return generate_uuid()


def make_slug(text: str) -> str:
    """Make URL slug (alias for slugify)."""
    return slugify(text)


def humanize_bytes(bytes: int) -> str:
    """Humanize bytes (alias for format_bytes)."""
    return format_bytes(bytes)


def humanize_duration(seconds: int) -> str:
    """Humanize duration (alias for format_duration)."""
    return format_duration(seconds)


def time_ago(dt: datetime) -> str:
    """Get time ago string (alias for get_time_ago)."""
    return get_time_ago(dt)


# Version information
__version__ = "1.0.0"
__author__ = "Parking Management System"
__description__ = "Utility functions for parking management system"


# Export all functions and classes
__all__ = [
    # Version info
    '__version__',
    '__author__',
    '__description__',
    
    # Utility class
    'Utils',
    
    # Convenience functions
    'utc_now',
    'utc_today',
    'format_money',
    'is_valid_email',
    'is_valid_phone',
    'generate_id',
    'make_slug',
    'humanize_bytes',
    'humanize_duration',
    'time_ago',
    
    # Datetime utilities
    'now',
    'today',
    'format_datetime',
    'parse_datetime',
    'is_business_hours',
    'get_next_business_open',
    'calculate_duration_minutes',
    'calculate_duration_hours',
    'add_minutes',
    'add_hours',
    'add_days',
    'get_date_range',
    'get_month_dates',
    'is_overlapping',
    'get_overlap_duration',
    'to_timezone_naive',
    'get_week_start',
    'get_week_end',
    'get_month_start',
    'get_month_end',
    'get_quarter_start',
    'get_quarter_end',
    'get_year_start',
    'get_year_end',
    'get_age_from_birthdate',
    'get_time_ago',
    'get_relative_time_string',
    
    # Validators
    'validate_email',
    'validate_email_domain',
    'validate_phone',
    'validate_phone_international',
    'format_phone',
    'validate_password_strength',
    'validate_password_match',
    'generate_random_password',
    'validate_license_plate',
    'format_license_plate',
    'get_license_plate_country',
    'validate_credit_card',
    'get_card_type',
    'mask_credit_card',
    'validate_date_range',
    'validate_future_date',
    'validate_past_date',
    'validate_business_hours',
    'validate_within_business_hours',
    'validate_positive_number',
    'validate_range',
    'validate_percentage',
    'validate_currency',
    'validate_not_empty',
    'validate_length',
    'validate_alphanumeric',
    'validate_no_special_chars',
    'validate_pattern',
    'validate_url',
    'validate_image_url',
    'validate_user_id',
    'validate_reservation_id',
    'validate_spot_id',
    'validate_vehicle_id',
    'validate_payment_id',
    'validate_reservation_time',
    'validate_cancellation_window',
    'validate_spot_compatibility',
    'validate_user_eligibility',
    'validate_json_schema',
    'validate_dict_structure',
    'validate_required_fields',
    
    # Helpers
    'slugify',
    'truncate',
    'random_string',
    'random_digits',
    'format_currency',
    'format_percentage',
    'strip_html',
    'escape_markdown',
    'camel_to_snake',
    'snake_to_camel',
    'pluralize',
    'singularize',
    'round_up',
    'round_down',
    'round_to_nearest',
    'clamp',
    'lerp',
    'normalize',
    'denormalize',
    'chunk_list',
    'flatten_list',
    'unique_list',
    'group_by',
    'key_by',
    'pluck',
    'sort_by',
    'filter_by',
    'paginate_list',
    'deep_get',
    'deep_set',
    'deep_merge',
    'pick',
    'omit',
    'rename_key',
    'flatten_dict',
    'unflatten_dict',
    'get_class_name',
    'get_methods',
    'has_attribute',
    'copy_attributes',
    'get_file_extension',
    'get_file_size_str',
    'is_image_file',
    'is_video_file',
    'is_document_file',
    'sanitize_filename',
    'get_unique_filename',
    'base64_encode',
    'base64_decode',
    'url_encode',
    'url_decode',
    'html_encode',
    'html_decode',
    'md5_hash',
    'sha1_hash',
    'sha256_hash',
    'generate_uuid',
    'generate_short_uuid',
    'format_bytes',
    'format_duration',
    'format_phone_display',
    'format_address',
    'format_name',
    'truncate_middle',
    'to_bool',
    'to_int',
    'to_float',
    'to_str',
    'to_list',
    'to_dict',
    'to_datetime',
    'is_development',
    'is_production',
    'is_testing',
    'get_env_var',
    'dump_object',
    'pretty_print',
    'get_memory_usage',
    'get_cpu_usage',
    'time_function',
    'async_time_function',
    
    # Encryption
    'encrypt_data',
    'decrypt_data',
    'encrypt_string',
    'decrypt_string',
    'hash_data',
    'verify_hash',
    'generate_salt',
    'generate_key',
    'encrypt_file',
    'decrypt_file',
    'sign_data',
    'verify_signature',
    'get_public_key',
    'get_private_key',
    
    # Logging
    'setup_logging',
    'get_logger',
    'log_function_call',
    'log_async_function_call',
    'log_exception',
    'log_performance',
    'LogContext',
    'JsonFormatter',
    'SensitiveDataFilter',
    'RequestIdFilter',
    'UserIdFilter',
    
    # Cache
    'cached',
    'async_cached',
    'cache_key',
    'invalidate_cache',
    'CacheManager',
    'LocalCache',
    'RedisCache',
    'NullCache',
    'cache_decorator',
    'memoize',
    'ttl_cache',
    
    # Geo
    'calculate_distance',
    'calculate_bearing',
    'get_lat_lng_from_address',
    'get_address_from_lat_lng',
    'get_timezone_from_lat_lng',
    'is_point_in_polygon',
    'calculate_parking_spot_area',
    'get_nearest_spots',
    'format_coordinates',
    'parse_coordinates',
    'validate_coordinates',
    'EARTH_RADIUS_KM',
    'EARTH_RADIUS_MILES',
    
    # Price
    'calculate_hourly_price',
    'calculate_daily_price',
    'calculate_weekly_price',
    'calculate_monthly_price',
    'calculate_overnight_price',
    'apply_discount',
    'apply_tax',
    'calculate_total',
    'calculate_refund',
    'calculate_penalty',
    'calculate_deposit',
    'round_price',
    'format_price',
    'PriceCalculator',
    'DiscountCalculator',
    'TaxCalculator',
    
    # Image
    'resize_image',
    'crop_image',
    'rotate_image',
    'add_watermark',
    'get_image_dimensions',
    'validate_image',
    'optimize_image',
    'convert_image_format',
    'create_thumbnail',
    'extract_exif',
    'remove_exif',
    'ImageProcessor',
    
    # CSV
    'read_csv',
    'write_csv',
    'read_csv_to_dicts',
    'write_dicts_to_csv',
    'validate_csv',
    'parse_csv_row',
    'CsvReader',
    'CsvWriter',
    
    # Excel
    'read_excel',
    'write_excel',
    'read_excel_to_dicts',
    'write_dicts_to_excel',
    'validate_excel',
    'ExcelReader',
    'ExcelWriter',
    
    # PDF
    'generate_pdf',
    'generate_invoice_pdf',
    'generate_report_pdf',
    'merge_pdfs',
    'split_pdf',
    'extract_text_from_pdf',
    'PdfGenerator',
    
    # QR
    'generate_qr_code',
    'generate_qr_code_base64',
    'read_qr_code',
    'generate_qr_for_payment',
    'generate_qr_for_ticket',
    'generate_qr_for_verification',
    
    # SMS
    'format_sms_message',
    'validate_phone_for_sms',
    'split_long_message',
    'SmsSender',
    
    # Email
    'send_email',
    'send_template_email',
    'validate_email_address',
    'format_email_address',
    'EmailSender',
    'EmailTemplate',
    
    # Push
    'send_push_notification',
    'send_bulk_push',
    'format_push_message',
    'PushSender',
    
    # Webhook
    'send_webhook',
    'verify_webhook_signature',
    'parse_webhook_payload',
    'WebhookClient',
    
    # Export
    'export_to_csv',
    'export_to_excel',
    'export_to_json',
    'export_to_pdf',
    'export_to_xml',
    'DataExporter',
    
    # Import
    'import_from_csv',
    'import_from_excel',
    'import_from_json',
    'import_from_xml',
    'DataImporter',
    'ImportValidator',
    
    # Report
    'generate_report',
    'ReportGenerator',
    'ChartGenerator',
    'DataAggregator',
    'ReportFormatter',
    
    # Analytics
    'track_event',
    'track_page_view',
    'track_user_action',
    'AnalyticsTracker',
    
    # Test
    'create_test_user',
    'create_test_reservation',
    'create_test_payment',
    'create_test_vehicle',
    'create_test_parking_spot',
    'MockDatabase',
    'TestClient',
    'TestDataFactory',
]