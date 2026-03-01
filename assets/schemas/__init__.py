"""Schemas package initialization for the parking management system.

This module exports all Pydantic schemas for request/response validation
and provides utility functions for schema management.
"""

from typing import Dict, Type, List, Any, Optional, Union, TypeVar
from datetime import datetime
from pydantic import BaseModel, create_model

# Import all request schemas
from .request_schemas import (
    # User schemas
    UserCreateSchema,
    UserUpdateSchema,
    UserLoginSchema,
    UserRegisterSchema,
    UserPreferencesSchema,
    UserPasswordChangeSchema,
    UserPasswordResetSchema,
    UserPasswordResetConfirmSchema,
    UserEmailVerificationSchema,
    UserPhoneVerificationSchema,
    
    # Vehicle schemas
    VehicleCreateSchema,
    VehicleUpdateSchema,
    VehicleSearchSchema,
    
    # Parking spot schemas
    ParkingSpotCreateSchema,
    ParkingSpotUpdateSchema,
    ParkingSpotSearchSchema,
    ParkingSpotAvailabilitySchema,
    
    # Reservation schemas
    ReservationCreateSchema,
    ReservationUpdateSchema,
    ReservationSearchSchema,
    ReservationCheckInSchema,
    ReservationCheckOutSchema,
    ReservationCancelSchema,
    ReservationExtendSchema,
    
    # Payment schemas
    PaymentCreateSchema,
    PaymentProcessSchema,
    PaymentRefundSchema,
    PaymentSearchSchema,
    PaymentMethodSchema,
    
    # Notification schemas
    NotificationCreateSchema,
    NotificationUpdateSchema,
    NotificationSearchSchema,
    NotificationMarkReadSchema,
    NotificationPreferencesSchema,
    
    # Common schemas
    DateRangeSchema,
    PaginationSchema,
    IdListSchema,
    SearchQuerySchema,
    BulkOperationSchema,
    SortSchema,
    FilterSchema,
)

# Import all response schemas
from .response_schemas import (
    # Generic responses
    ApiResponse,
    PaginatedResponse,
    ErrorResponse,
    ValidationErrorResponse,
    
    # User responses
    UserResponse,
    UserProfileResponse,
    UserListResponse,
    UserAuthResponse,
    UserTokenResponse,
    
    # Vehicle responses
    VehicleResponse,
    VehicleListResponse,
    VehicleDetailResponse,
    
    # Parking spot responses
    ParkingSpotResponse,
    ParkingSpotListResponse,
    ParkingSpotDetailResponse,
    ParkingSpotAvailabilityResponse,
    ParkingSpotOccupancyResponse,
    
    # Reservation responses
    ReservationResponse,
    ReservationListResponse,
    ReservationDetailResponse,
    ReservationHistoryResponse,
    ReservationSummaryResponse,
    
    # Payment responses
    PaymentResponse,
    PaymentListResponse,
    PaymentDetailResponse,
    PaymentReceiptResponse,
    PaymentRefundResponse,
    PaymentMethodResponse,
    
    # Notification responses
    NotificationResponse,
    NotificationListResponse,
    NotificationDetailResponse,
    NotificationCountResponse,
    NotificationPreferencesResponse,
    
    # Dashboard responses
    DashboardStatsResponse,
    RevenueReportResponse,
    OccupancyReportResponse,
    UserActivityResponse,
    
    # System responses
    HealthCheckResponse,
    VersionResponse,
    MetricsResponse,
)

# Define schema registry for dynamic access
SCHEMA_REGISTRY: Dict[str, Type[BaseModel]] = {
    # Request schemas
    'user_create': UserCreateSchema,
    'user_update': UserUpdateSchema,
    'user_login': UserLoginSchema,
    'user_register': UserRegisterSchema,
    'user_preferences': UserPreferencesSchema,
    'user_password_change': UserPasswordChangeSchema,
    'user_password_reset': UserPasswordResetSchema,
    'user_password_reset_confirm': UserPasswordResetConfirmSchema,
    'user_email_verification': UserEmailVerificationSchema,
    'user_phone_verification': UserPhoneVerificationSchema,
    
    'vehicle_create': VehicleCreateSchema,
    'vehicle_update': VehicleUpdateSchema,
    'vehicle_search': VehicleSearchSchema,
    
    'parking_spot_create': ParkingSpotCreateSchema,
    'parking_spot_update': ParkingSpotUpdateSchema,
    'parking_spot_search': ParkingSpotSearchSchema,
    'parking_spot_availability': ParkingSpotAvailabilitySchema,
    
    'reservation_create': ReservationCreateSchema,
    'reservation_update': ReservationUpdateSchema,
    'reservation_search': ReservationSearchSchema,
    'reservation_check_in': ReservationCheckInSchema,
    'reservation_check_out': ReservationCheckOutSchema,
    'reservation_cancel': ReservationCancelSchema,
    'reservation_extend': ReservationExtendSchema,
    
    'payment_create': PaymentCreateSchema,
    'payment_process': PaymentProcessSchema,
    'payment_refund': PaymentRefundSchema,
    'payment_search': PaymentSearchSchema,
    'payment_method': PaymentMethodSchema,
    
    'notification_create': NotificationCreateSchema,
    'notification_update': NotificationUpdateSchema,
    'notification_search': NotificationSearchSchema,
    'notification_mark_read': NotificationMarkReadSchema,
    'notification_preferences': NotificationPreferencesSchema,
    
    'date_range': DateRangeSchema,
    'pagination': PaginationSchema,
    'id_list': IdListSchema,
    'search_query': SearchQuerySchema,
    'bulk_operation': BulkOperationSchema,
    'sort': SortSchema,
    'filter': FilterSchema,
    
    # Response schemas
    'api_response': ApiResponse,
    'paginated_response': PaginatedResponse,
    'error_response': ErrorResponse,
    'validation_error_response': ValidationErrorResponse,
    
    'user_response': UserResponse,
    'user_profile_response': UserProfileResponse,
    'user_list_response': UserListResponse,
    'user_auth_response': UserAuthResponse,
    'user_token_response': UserTokenResponse,
    
    'vehicle_response': VehicleResponse,
    'vehicle_list_response': VehicleListResponse,
    'vehicle_detail_response': VehicleDetailResponse,
    
    'parking_spot_response': ParkingSpotResponse,
    'parking_spot_list_response': ParkingSpotListResponse,
    'parking_spot_detail_response': ParkingSpotDetailResponse,
    'parking_spot_availability_response': ParkingSpotAvailabilityResponse,
    'parking_spot_occupancy_response': ParkingSpotOccupancyResponse,
    
    'reservation_response': ReservationResponse,
    'reservation_list_response': ReservationListResponse,
    'reservation_detail_response': ReservationDetailResponse,
    'reservation_history_response': ReservationHistoryResponse,
    'reservation_summary_response': ReservationSummaryResponse,
    
    'payment_response': PaymentResponse,
    'payment_list_response': PaymentListResponse,
    'payment_detail_response': PaymentDetailResponse,
    'payment_receipt_response': PaymentReceiptResponse,
    'payment_refund_response': PaymentRefundResponse,
    'payment_method_response': PaymentMethodResponse,
    
    'notification_response': NotificationResponse,
    'notification_list_response': NotificationListResponse,
    'notification_detail_response': NotificationDetailResponse,
    'notification_count_response': NotificationCountResponse,
    'notification_preferences_response': NotificationPreferencesResponse,
    
    'dashboard_stats_response': DashboardStatsResponse,
    'revenue_report_response': RevenueReportResponse,
    'occupancy_report_response': OccupancyReportResponse,
    'user_activity_response': UserActivityResponse,
    
    'health_check_response': HealthCheckResponse,
    'version_response': VersionResponse,
    'metrics_response': MetricsResponse,
}

# Export all schemas
__all__ = [
    # Request schemas
    'UserCreateSchema',
    'UserUpdateSchema',
    'UserLoginSchema',
    'UserRegisterSchema',
    'UserPreferencesSchema',
    'UserPasswordChangeSchema',
    'UserPasswordResetSchema',
    'UserPasswordResetConfirmSchema',
    'UserEmailVerificationSchema',
    'UserPhoneVerificationSchema',
    
    'VehicleCreateSchema',
    'VehicleUpdateSchema',
    'VehicleSearchSchema',
    
    'ParkingSpotCreateSchema',
    'ParkingSpotUpdateSchema',
    'ParkingSpotSearchSchema',
    'ParkingSpotAvailabilitySchema',
    
    'ReservationCreateSchema',
    'ReservationUpdateSchema',
    'ReservationSearchSchema',
    'ReservationCheckInSchema',
    'ReservationCheckOutSchema',
    'ReservationCancelSchema',
    'ReservationExtendSchema',
    
    'PaymentCreateSchema',
    'PaymentProcessSchema',
    'PaymentRefundSchema',
    'PaymentSearchSchema',
    'PaymentMethodSchema',
    
    'NotificationCreateSchema',
    'NotificationUpdateSchema',
    'NotificationSearchSchema',
    'NotificationMarkReadSchema',
    'NotificationPreferencesSchema',
    
    'DateRangeSchema',
    'PaginationSchema',
    'IdListSchema',
    'SearchQuerySchema',
    'BulkOperationSchema',
    'SortSchema',
    'FilterSchema',
    
    # Response schemas
    'ApiResponse',
    'PaginatedResponse',
    'ErrorResponse',
    'ValidationErrorResponse',
    
    'UserResponse',
    'UserProfileResponse',
    'UserListResponse',
    'UserAuthResponse',
    'UserTokenResponse',
    
    'VehicleResponse',
    'VehicleListResponse',
    'VehicleDetailResponse',
    
    'ParkingSpotResponse',
    'ParkingSpotListResponse',
    'ParkingSpotDetailResponse',
    'ParkingSpotAvailabilityResponse',
    'ParkingSpotOccupancyResponse',
    
    'ReservationResponse',
    'ReservationListResponse',
    'ReservationDetailResponse',
    'ReservationHistoryResponse',
    'ReservationSummaryResponse',
    
    'PaymentResponse',
    'PaymentListResponse',
    'PaymentDetailResponse',
    'PaymentReceiptResponse',
    'PaymentRefundResponse',
    'PaymentMethodResponse',
    
    'NotificationResponse',
    'NotificationListResponse',
    'NotificationDetailResponse',
    'NotificationCountResponse',
    'NotificationPreferencesResponse',
    
    'DashboardStatsResponse',
    'RevenueReportResponse',
    'OccupancyReportResponse',
    'UserActivityResponse',
    
    'HealthCheckResponse',
    'VersionResponse',
    'MetricsResponse',
    
    # Registry and utilities
    'SCHEMA_REGISTRY',
    'get_schema',
    'create_dynamic_schema',
    'get_request_schemas',
    'get_response_schemas',
    'schema_to_dict',
    'validate_data',
    'get_schema_fields',
    'get_schema_example',
    'merge_schemas',
]

T = TypeVar('T', bound=BaseModel)


def get_schema(schema_name: str) -> Optional[Type[BaseModel]]:
    """Get a schema class by name (case-insensitive).
    
    Args:
        schema_name: Name of the schema (e.g., 'user_create', 'UserResponse')
        
    Returns:
        Schema class if found, None otherwise
    """
    # Convert to lowercase for case-insensitive lookup
    schema_key = schema_name.lower()
    
    # Try direct lookup
    if schema_key in SCHEMA_REGISTRY:
        return SCHEMA_REGISTRY[schema_key]
    
    # Try with common prefixes
    prefixes = ['', 'user_', 'vehicle_', 'parking_spot_', 'reservation_', 
                'payment_', 'notification_', 'api_', 'paginated_']
    
    for prefix in prefixes:
        test_key = f"{prefix}{schema_key}".lower()
        if test_key in SCHEMA_REGISTRY:
            return SCHEMA_REGISTRY[test_key]
    
    return None


def create_dynamic_schema(
    name: str,
    fields: Dict[str, tuple],
    base_class: Type[BaseModel] = BaseModel
) -> Type[BaseModel]:
    """Create a dynamic Pydantic schema.
    
    Args:
        name: Name of the schema
        fields: Dictionary of field names to (type, default_value) tuples
        base_class: Base class to inherit from
        
    Returns:
        New Pydantic model class
    """
    return create_model(name, __base__=base_class, **fields)


def get_request_schemas() -> Dict[str, Type[BaseModel]]:
    """Get all request schemas.
    
    Returns:
        Dictionary of request schema names to schema classes
    """
    request_patterns = ['create', 'update', 'login', 'register', 'search', 
                        'check_in', 'check_out', 'cancel', 'extend', 'process', 
                        'refund', 'mark_read', 'date_range', 'pagination']
    
    return {
        name: schema
        for name, schema in SCHEMA_REGISTRY.items()
        if any(pattern in name.lower() for pattern in request_patterns)
    }


def get_response_schemas() -> Dict[str, Type[BaseModel]]:
    """Get all response schemas.
    
    Returns:
        Dictionary of response schema names to schema classes
    """
    response_patterns = ['response', 'report', 'stats', 'health', 'version', 'metrics']
    
    return {
        name: schema
        for name, schema in SCHEMA_REGISTRY.items()
        if any(pattern in name.lower() for pattern in response_patterns)
    }


def schema_to_dict(schema_class: Type[BaseModel]) -> Dict[str, Any]:
    """Convert a schema class to a dictionary representation.
    
    Args:
        schema_class: Pydantic schema class
        
    Returns:
        Dictionary with schema metadata
    """
    schema = schema_class.schema()
    
    return {
        'name': schema_class.__name__,
        'title': schema.get('title', ''),
        'description': schema.get('description', ''),
        'fields': schema.get('properties', {}),
        'required': schema.get('required', []),
        'example': get_schema_example(schema_class),
    }


def validate_data(
    schema_class: Type[T],
    data: Dict[str, Any],
    partial: bool = False
) -> tuple[bool, Optional[T], Optional[Dict[str, Any]]]:
    """Validate data against a schema.
    
    Args:
        schema_class: Pydantic schema class
        data: Data to validate
        partial: Whether to allow partial data (for updates)
        
    Returns:
        Tuple of (is_valid, validated_data, errors)
    """
    try:
        if partial:
            # For partial updates, allow missing fields
            validated = schema_class.model_validate(data, strict=False)
        else:
            validated = schema_class.model_validate(data)
        return True, validated, None
    except Exception as e:
        if hasattr(e, 'errors'):
            return False, None, e.errors()
        return False, None, {'error': str(e)}


def get_schema_fields(schema_class: Type[BaseModel]) -> List[Dict[str, Any]]:
    """Get field information for a schema.
    
    Args:
        schema_class: Pydantic schema class
        
    Returns:
        List of dictionaries containing field information
    """
    fields = []
    schema = schema_class.schema()
    
    for field_name, field_info in schema.get('properties', {}).items():
        field_data = {
            'name': field_name,
            'type': field_info.get('type', 'unknown'),
            'format': field_info.get('format'),
            'description': field_info.get('description', ''),
            'required': field_name in schema.get('required', []),
            'default': field_info.get('default'),
            'example': field_info.get('example'),
        }
        
        # Handle enum fields
        if 'enum' in field_info:
            field_data['enum'] = field_info['enum']
        
        # Handle nested schemas
        if '$ref' in field_info:
            field_data['ref'] = field_info['$ref']
        
        fields.append(field_data)
    
    return fields


def get_schema_example(schema_class: Type[BaseModel]) -> Dict[str, Any]:
    """Generate an example for a schema.
    
    Args:
        schema_class: Pydantic schema class
        
    Returns:
        Example dictionary
    """
    schema = schema_class.schema()
    example = {}
    
    for field_name, field_info in schema.get('properties', {}).items():
        # Use provided example if available
        if 'example' in field_info:
            example[field_name] = field_info['example']
        # Generate example based on type
        elif field_info.get('type') == 'string':
            if field_info.get('format') == 'email':
                example[field_name] = 'user@example.com'
            elif field_info.get('format') == 'date-time':
                example[field_name] = datetime.utcnow().isoformat()
            elif field_info.get('format') == 'date':
                example[field_name] = datetime.utcnow().date().isoformat()
            elif field_info.get('enum'):
                example[field_name] = field_info['enum'][0]
            else:
                example[field_name] = f'sample_{field_name}'
        elif field_info.get('type') == 'integer':
            example[field_name] = 1
        elif field_info.get('type') == 'number':
            example[field_name] = 1.0
        elif field_info.get('type') == 'boolean':
            example[field_name] = True
        elif field_info.get('type') == 'array':
            example[field_name] = []
        elif field_info.get('type') == 'object':
            example[field_name] = {}
    
    return example


def merge_schemas(
    name: str,
    schemas: List[Type[BaseModel]],
    operation: str = 'intersection'
) -> Type[BaseModel]:
    """Merge multiple schemas into one.
    
    Args:
        name: Name for the merged schema
        schemas: List of schema classes to merge
        operation: 'intersection' (all fields) or 'union' (any field)
        
    Returns:
        Merged Pydantic schema class
    """
    if not schemas:
        raise ValueError("At least one schema is required for merging")
    
    if operation == 'intersection':
        # Take fields that exist in all schemas
        common_fields = set(schemas[0].model_fields.keys())
        for schema in schemas[1:]:
            common_fields &= set(schema.model_fields.keys())
        
        # Create merged fields
        merged_fields = {}
        for field_name in common_fields:
            # Use field info from first schema (they should be compatible)
            field_info = schemas[0].model_fields[field_name]
            merged_fields[field_name] = (field_info.annotation, field_info)
    
    elif operation == 'union':
        # Take all fields from all schemas
        merged_fields = {}
        for schema in schemas:
            for field_name, field_info in schema.model_fields.items():
                if field_name not in merged_fields:
                    merged_fields[field_name] = (field_info.annotation, field_info)
    
    else:
        raise ValueError(f"Invalid operation: {operation}. Use 'intersection' or 'union'")
    
    # Create the merged schema
    return create_model(name, **merged_fields)


def get_paginated_schema(
    item_schema: Type[BaseModel],
    name: Optional[str] = None
) -> Type[BaseModel]:
    """Create a paginated response schema for an item schema.
    
    Args:
        item_schema: Schema for individual items
        name: Name for the paginated schema (defaults to 'Paginated{item_schema.__name__}')
        
    Returns:
        Paginated response schema
    """
    if name is None:
        name = f"Paginated{item_schema.__name__}"
    
    # Import here to avoid circular imports
    from .response_schemas import PaginatedResponse
    
    # Create a new paginated schema with the item schema as the data type
    return create_model(
        name,
        __base__=PaginatedResponse[item_schema],  # type: ignore
        __module__=item_schema.__module__,
    )


def get_filtered_schema(
    base_schema: Type[BaseModel],
    include_fields: Optional[List[str]] = None,
    exclude_fields: Optional[List[str]] = None,
    name: Optional[str] = None
) -> Type[BaseModel]:
    """Create a filtered version of a schema.
    
    Args:
        base_schema: Base schema to filter
        include_fields: Fields to include (if None, include all)
        exclude_fields: Fields to exclude
        name: Name for the filtered schema
        
    Returns:
        Filtered Pydantic schema
    """
    if include_fields is not None and exclude_fields is not None:
        raise ValueError("Cannot specify both include_fields and exclude_fields")
    
    fields = {}
    
    for field_name, field_info in base_schema.model_fields.items():
        if include_fields is not None and field_name not in include_fields:
            continue
        if exclude_fields is not None and field_name in exclude_fields:
            continue
        
        fields[field_name] = (field_info.annotation, field_info)
    
    if name is None:
        suffix = 'Filtered' if include_fields is None else 'Included'
        name = f"{base_schema.__name__}{suffix}"
    
    return create_model(name, **fields)


def get_optional_schema(
    base_schema: Type[BaseModel],
    name: Optional[str] = None
) -> Type[BaseModel]:
    """Create a version of a schema with all fields optional.
    
    Args:
        base_schema: Base schema
        name: Name for the optional schema
        
    Returns:
        Schema with all fields optional
    """
    fields = {}
    
    for field_name, field_info in base_schema.model_fields.items():
        # Make field optional by using None as default
        fields[field_name] = (Optional[field_info.annotation], None)
    
    if name is None:
        name = f"Optional{base_schema.__name__}"
    
    return create_model(name, **fields)


# Initialize schema registry with all schemas
def _initialize_registry() -> None:
    """Initialize the schema registry with all schemas."""
    # This function can be used to add any dynamic schemas or
    # perform validation on the registry
    pass


# Run initialization
_initialize_registry()