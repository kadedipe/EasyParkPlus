"""
Dependencies package for API v1.
"""

from .auth import (
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    get_current_user_optional,
    get_current_user_ws,
    verify_token,
    get_token_payload
)
from .database import (
    get_db,
    get_redis,
    get_db_session,
    transaction,
    get_read_only_db
)
from .pagination import (
    PaginationParams,
    get_pagination,
    paginate,
    PaginatedResponse
)
from .filters import (
    FilterParams,
    get_filters,
    DateRangeFilter,
    SearchFilter,
    SortParams
)
from .permissions import (
    require_permissions,
    require_roles,
    check_ownership,
    PermissionChecker,
    RoleChecker
)
from .rate_limit import (
    rate_limit,
    RateLimiter,
    get_rate_limiter
)
from .cache import (
    cache_response,
    Cache,
    get_cache,
    invalidate_cache
)
from .validation import (
    validate_uuid,
    validate_email,
    validate_phone,
    validate_license_plate,
    validate_datetime_range
)
from .services import (
    get_email_service,
    get_payment_service,
    get_notification_service,
    get_qr_service,
    get_audit_service
)
from .config import (
    get_settings,
    Settings
)
from .version import (
    api_version,
    get_api_version
)

__all__ = [
    # Auth
    'get_current_user',
    'get_current_active_user',
    'get_current_superuser',
    'get_current_user_optional',
    'get_current_user_ws',
    'verify_token',
    'get_token_payload',
    
    # Database
    'get_db',
    'get_redis',
    'get_db_session',
    'transaction',
    'get_read_only_db',
    
    # Pagination
    'PaginationParams',
    'get_pagination',
    'paginate',
    'PaginatedResponse',
    
    # Filters
    'FilterParams',
    'get_filters',
    'DateRangeFilter',
    'SearchFilter',
    'SortParams',
    
    # Permissions
    'require_permissions',
    'require_roles',
    'check_ownership',
    'PermissionChecker',
    'RoleChecker',
    
    # Rate Limit
    'rate_limit',
    'RateLimiter',
    'get_rate_limiter',
    
    # Cache
    'cache_response',
    'Cache',
    'get_cache',
    'invalidate_cache',
    
    # Validation
    'validate_uuid',
    'validate_email',
    'validate_phone',
    'validate_license_plate',
    'validate_datetime_range',
    
    # Services
    'get_email_service',
    'get_payment_service',
    'get_notification_service',
    'get_qr_service',
    'get_audit_service',
    
    # Config
    'get_settings',
    'Settings',
    
    # Version
    'api_version',
    'get_api_version'
]