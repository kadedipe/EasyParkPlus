"""
Utils package initialization.
Export all utility functions for easy importing.
"""

from .datetime_utils import (
    utc_now,
    format_datetime,
    parse_datetime,
    get_date_range,
    get_week_range,
    get_month_range,
    get_quarter_range,
    get_year_range,
    days_between,
    hours_between,
    minutes_between,
    add_days,
    add_hours,
    add_minutes,
    is_weekend,
    is_business_hours
)

from .security import (
    hash_password,
    verify_password,
    generate_token,
    verify_token,
    generate_otp,
    verify_otp,
    encrypt_data,
    decrypt_data,
    generate_api_key,
    mask_sensitive_data,
    sanitize_input
)

from .validators import (
    validate_email,
    validate_phone,
    validate_password_strength,
    validate_plate_number,
    validate_vehicle_model,
    validate_price,
    validate_uuid,
    validate_json_schema,
    validate_date_range,
    validate_future_date,
    validate_past_date
)

from .formatters import (
    format_currency,
    format_phone,
    format_plate_number,
    format_duration,
    format_file_size,
    format_percentage,
    format_address,
    truncate_string,
    camel_to_snake,
    snake_to_camel,
    pluralize
)

from .logging_utils import (
    setup_logging,
    get_logger,
    log_request,
    log_response,
    log_error,
    audit_log,
    LogContext,
    RequestLogger
)

from .cache_utils import (
    cached,
    invalidate_cache,
    CacheManager,
    cache_key_builder,
    RateLimiter,
    Throttler
)

from .file_utils import (
    save_upload_file,
    delete_file,
    get_file_extension,
    get_file_size,
    is_allowed_file,
    generate_file_name,
    create_temp_file,
    read_csv_file,
    write_csv_file,
    read_json_file,
    write_json_file
)

from .pagination import (
    paginate,
    Paginator,
    pagination_links,
    calculate_pages,
    PaginatedResponse
)

from .email_utils import (
    send_email,
    send_welcome_email,
    send_password_reset_email,
    send_verification_email,
    send_notification_email,
    send_invoice_email,
    EmailTemplate
)

from .sms_utils import (
    send_sms,
    send_verification_sms,
    send_notification_sms,
    send_reminder_sms
)

from .payment_utils import (
    calculate_tax,
    calculate_discount,
    calculate_total,
    format_payment_method,
    validate_payment_amount,
    generate_invoice_number,
    PaymentStatus
)

from .geo_utils import (
    calculate_distance,
    calculate_duration,
    geocode_address,
    reverse_geocode,
    get_timezone,
    validate_coordinates,
    format_coordinates,
    calculate_bounding_box
)

from .qr_utils import (
    generate_qr_code,
    read_qr_code,
    generate_parking_qr,
    validate_qr_code,
    QRCodeGenerator
)

__all__ = [
    # Datetime utils
    "utc_now",
    "format_datetime",
    "parse_datetime",
    "get_date_range",
    "get_week_range",
    "get_month_range",
    "get_quarter_range",
    "get_year_range",
    "days_between",
    "hours_between",
    "minutes_between",
    "add_days",
    "add_hours",
    "add_minutes",
    "is_weekend",
    "is_business_hours",
    
    # Security utils
    "hash_password",
    "verify_password",
    "generate_token",
    "verify_token",
    "generate_otp",
    "verify_otp",
    "encrypt_data",
    "decrypt_data",
    "generate_api_key",
    "mask_sensitive_data",
    "sanitize_input",
    
    # Validators
    "validate_email",
    "validate_phone",
    "validate_password_strength",
    "validate_plate_number",
    "validate_vehicle_model",
    "validate_price",
    "validate_uuid",
    "validate_json_schema",
    "validate_date_range",
    "validate_future_date",
    "validate_past_date",
    
    # Formatters
    "format_currency",
    "format_phone",
    "format_plate_number",
    "format_duration",
    "format_file_size",
    "format_percentage",
    "format_address",
    "truncate_string",
    "camel_to_snake",
    "snake_to_camel",
    "pluralize",
    
    # Logging utils
    "setup_logging",
    "get_logger",
    "log_request",
    "log_response",
    "log_error",
    "audit_log",
    "LogContext",
    "RequestLogger",
    
    # Cache utils
    "cached",
    "invalidate_cache",
    "CacheManager",
    "cache_key_builder",
    "RateLimiter",
    "Throttler",
    
    # File utils
    "save_upload_file",
    "delete_file",
    "get_file_extension",
    "get_file_size",
    "is_allowed_file",
    "generate_file_name",
    "create_temp_file",
    "read_csv_file",
    "write_csv_file",
    "read_json_file",
    "write_json_file",
    
    # Pagination
    "paginate",
    "Paginator",
    "pagination_links",
    "calculate_pages",
    "PaginatedResponse",
    
    # Email utils
    "send_email",
    "send_welcome_email",
    "send_password_reset_email",
    "send_verification_email",
    "send_notification_email",
    "send_invoice_email",
    "EmailTemplate",
    
    # SMS utils
    "send_sms",
    "send_verification_sms",
    "send_notification_sms",
    "send_reminder_sms",
    
    # Payment utils
    "calculate_tax",
    "calculate_discount",
    "calculate_total",
    "format_payment_method",
    "validate_payment_amount",
    "generate_invoice_number",
    "PaymentStatus",
    
    # Geo utils
    "calculate_distance",
    "calculate_duration",
    "geocode_address",
    "reverse_geocode",
    "get_timezone",
    "validate_coordinates",
    "format_coordinates",
    "calculate_bounding_box",
    
    # QR utils
    "generate_qr_code",
    "read_qr_code",
    "generate_parking_qr",
    "validate_qr_code",
    "QRCodeGenerator"
]