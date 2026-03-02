# parking-management/data/migrations/repositories/__init__.py
"""
Repository module exports for the parking management system.

This module serves as the central export point for all repository classes,
providing a clean interface for data access across the application.
Repositories are organized by domain and provide CRUD operations
and specialized queries for their respective entities.
"""

# ============================================================================
# User Management Repositories
# ============================================================================

from .user_repository import (
    UserRepository,
    UserSessionRepository,
    UserPreferenceRepository,
    UserDeviceRepository,
    UserAuditRepository,
)

from .auth_repository import (
    AuthProviderRepository,
    MFASettingRepository,
    PasswordResetTokenRepository,
    EmailVerificationTokenRepository,
    APIKeyRepository,
    OAuthStateRepository,
)

from .role_repository import (
    RoleRepository,
    PermissionRepository,
    RoleAssignmentRepository,
)

# ============================================================================
# Vehicle Management Repositories
# ============================================================================

from .vehicle_repository import (
    VehicleRepository,
    VehicleRegistrationRepository,
    VehicleInsuranceRepository,
    VehicleInspectionRepository,
    VehicleOwnershipRepository,
    VehicleDocumentRepository,
    VehicleImageRepository,
    VehicleHistoryRepository,
)

from .blacklist_repository import (
    VehicleBlacklistRepository,
    VehicleAlertRepository,
    StolenVehicleRepository,
)

# ============================================================================
# Parking Management Repositories
# ============================================================================

from .parking_spot_repository import (
    ParkingSpotRepository,
    SpotMaintenanceRepository,
    SpotSensorRepository,
    SpotHistoryRepository,
    SpotOccupancyRepository,
)

from .parking_zone_repository import (
    ParkingZoneRepository,
    ZoneScheduleRepository,
    ZoneRestrictionRepository,
    ZoneRateRepository,
    ZoneCapacityRepository,
)

from .gate_repository import (
    GateRepository,
    GateAccessLogRepository,
    GateControllerRepository,
    GateScheduleRepository,
)

# ============================================================================
# Reservation Repositories
# ============================================================================

from .reservation_repository import (
    ReservationRepository,
    RecurringReservationRepository,
    ReservationHistoryRepository,
    WaitlistRepository,
)

from .check_in_out_repository import (
    CheckInRepository,
    CheckOutRepository,
    CheckInHistoryRepository,
)

# ============================================================================
# Payment Repositories
# ============================================================================

from .payment_repository import (
    PaymentRepository,
    PaymentMethodRepository,
    PaymentTransactionRepository,
    RefundRepository,
    DisputeRepository,
)

from .invoice_repository import (
    InvoiceRepository,
    InvoiceItemRepository,
    InvoiceLineRepository,
)

from .subscription_repository import (
    SubscriptionRepository,
    SubscriptionPlanRepository,
    SubscriptionHistoryRepository,
)

from .discount_repository import (
    DiscountRepository,
    CouponRepository,
    PromotionRepository,
    DiscountUsageRepository,
)

from .fee_repository import (
    FeeRepository,
    FeeScheduleRepository,
    FeeCalculationRepository,
)

# ============================================================================
# Rate Management Repositories
# ============================================================================

from .rate_repository import (
    RateRepository,
    RateScheduleRepository,
    RateHistoryRepository,
    DynamicPricingRepository,
    SpecialRateRepository,
)

from .pricing_rule_repository import (
    PricingRuleRepository,
    PricingConditionRepository,
    PricingOverrideRepository,
)

# ============================================================================
# Notification Repositories
# ============================================================================

from .notification_repository import (
    NotificationRepository,
    NotificationTemplateRepository,
    NotificationLogRepository,
    NotificationPreferenceRepository,
)

from .campaign_repository import (
    CampaignRepository,
    CampaignRecipientRepository,
    CampaignAnalyticsRepository,
)

from .webhook_repository import (
    WebhookRepository,
    WebhookDeliveryRepository,
    WebhookEndpointRepository,
)

from .device_repository import (
    DeviceRepository,
    DeviceTokenRepository,
    DevicePreferenceRepository,
)

# ============================================================================
# Sensor Repositories
# ============================================================================

from .sensor_repository import (
    SensorRepository,
    SensorReadingRepository,
    SensorEventRepository,
    SensorCalibrationRepository,
    SensorMaintenanceRepository,
)

from .sensor_network_repository import (
    SensorNetworkRepository,
    SensorGatewayRepository,
    SensorCommunicationLogRepository,
)

# ============================================================================
# Audit Repositories
# ============================================================================

from .audit_repository import (
    AuditLogRepository,
    AuditEventRepository,
    DataRetentionRepository,
    ComplianceLogRepository,
)

from .audit_archive_repository import (
    AuditArchiveRepository,
    ArchivedAuditRepository,
)

# ============================================================================
# Analytics Repositories
# ============================================================================

from .analytics_repository import (
    AnalyticsRepository,
    ReportRepository,
    ReportScheduleRepository,
    DashboardRepository,
    MetricRepository,
)

from .occupancy_analytics_repository import (
    OccupancyAnalyticsRepository,
    OccupancyForecastRepository,
    PeakTimeRepository,
)

from .financial_analytics_repository import (
    RevenueAnalyticsRepository,
    PayoutAnalyticsRepository,
    TransactionAnalyticsRepository,
)

# ============================================================================
# Configuration Repositories
# ============================================================================

from .config_repository import (
    SystemConfigRepository,
    FeatureFlagRepository,
    IntegrationConfigRepository,
    EnvironmentConfigRepository,
)

from .settings_repository import (
    ApplicationSettingsRepository,
    BusinessSettingsRepository,
    NotificationSettingsRepository,
)

# ============================================================================
# Integration Repositories
# ============================================================================

from .integration_repository import (
    IntegrationRepository,
    IntegrationLogRepository,
    APICallRepository,
    SyncJobRepository,
    ExternalServiceRepository,
)

from .third_party_repository import (
    ThirdPartyCredentialsRepository,
    ThirdPartyDataRepository,
    WebhookIntegrationRepository,
)

# ============================================================================
# Support Repositories
# ============================================================================

from .support_repository import (
    TicketRepository,
    TicketCommentRepository,
    TicketAttachmentRepository,
    TicketHistoryRepository,
    FAQRepository,
    KnowledgeBaseRepository,
)

from .feedback_repository import (
    FeedbackRepository,
    RatingRepository,
    ReviewRepository,
    ComplaintRepository,
)

# ============================================================================
# Violation Repositories
# ============================================================================

from .violation_repository import (
    ViolationRepository,
    ViolationTypeRepository,
    ViolationPenaltyRepository,
    ViolationAppealRepository,
    ViolationPaymentRepository,
)

# ============================================================================
# Reporting Repositories
# ============================================================================

from .reporting_repository import (
    CustomReportRepository,
    ReportTemplateRepository,
    ScheduledReportRepository,
    ExportJobRepository,
    DataExportRepository,
)

# ============================================================================
# Base Repository
# ============================================================================

from .base_repository import (
    BaseRepository,
    SoftDeleteRepository,
    TimestampedRepository,
    AuditableRepository,
    VersionedRepository,
    CacheableRepository,
    SearchableRepository,
)

# ============================================================================
# Repository Factory
# ============================================================================

from .repository_factory import (
    RepositoryFactory,
    get_repository,
    register_repository,
    clear_repository_cache,
)

# ============================================================================
# Repository Mixins
# ============================================================================

from .mixins import (
    SoftDeleteMixin,
    TimestampMixin,
    AuditMixin,
    VersionMixin,
    CacheMixin,
    SearchMixin,
    PaginationMixin,
    FilterMixin,
    BatchOperationMixin,
    TransactionMixin,
)

# ============================================================================
# Repository Interfaces
# ============================================================================

from .interfaces import (
    IRepository,
    IReadOnlyRepository,
    IWriteOnlyRepository,
    ISoftDeleteRepository,
    ISearchableRepository,
    ICacheableRepository,
    IAuditableRepository,
)

# ============================================================================
# Repository Exceptions
# ============================================================================

from .exceptions import (
    RepositoryException,
    EntityNotFoundException,
    DuplicateEntityException,
    ValidationException,
    ConstraintViolationException,
    OptimisticLockException,
    ConcurrencyException,
    RepositoryConfigurationException,
    DataIntegrityException,
)

# ============================================================================
# Repository Decorators
# ============================================================================

from .decorators import (
    transactional,
    cacheable,
    auditable,
    retry_on_failure,
    log_execution,
    measure_time,
    check_permissions,
)

# ============================================================================
# Repository Utilities
# ============================================================================

from .utils import (
    build_query,
    apply_pagination,
    apply_sorting,
    apply_filtering,
    build_search_condition,
    parse_sort_params,
    parse_filter_params,
    validate_query_params,
    sanitize_order_by,
    create_paginated_response,
)

# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # User Management
    'UserRepository',
    'UserSessionRepository',
    'UserPreferenceRepository',
    'UserDeviceRepository',
    'UserAuditRepository',
    'AuthProviderRepository',
    'MFASettingRepository',
    'PasswordResetTokenRepository',
    'EmailVerificationTokenRepository',
    'APIKeyRepository',
    'OAuthStateRepository',
    'RoleRepository',
    'PermissionRepository',
    'RoleAssignmentRepository',
    
    # Vehicle Management
    'VehicleRepository',
    'VehicleRegistrationRepository',
    'VehicleInsuranceRepository',
    'VehicleInspectionRepository',
    'VehicleOwnershipRepository',
    'VehicleDocumentRepository',
    'VehicleImageRepository',
    'VehicleHistoryRepository',
    'VehicleBlacklistRepository',
    'VehicleAlertRepository',
    'StolenVehicleRepository',
    
    # Parking Management
    'ParkingSpotRepository',
    'SpotMaintenanceRepository',
    'SpotSensorRepository',
    'SpotHistoryRepository',
    'SpotOccupancyRepository',
    'ParkingZoneRepository',
    'ZoneScheduleRepository',
    'ZoneRestrictionRepository',
    'ZoneRateRepository',
    'ZoneCapacityRepository',
    'GateRepository',
    'GateAccessLogRepository',
    'GateControllerRepository',
    'GateScheduleRepository',
    
    # Reservation Management
    'ReservationRepository',
    'RecurringReservationRepository',
    'ReservationHistoryRepository',
    'WaitlistRepository',
    'CheckInRepository',
    'CheckOutRepository',
    'CheckInHistoryRepository',
    
    # Payment Management
    'PaymentRepository',
    'PaymentMethodRepository',
    'PaymentTransactionRepository',
    'RefundRepository',
    'DisputeRepository',
    'InvoiceRepository',
    'InvoiceItemRepository',
    'InvoiceLineRepository',
    'SubscriptionRepository',
    'SubscriptionPlanRepository',
    'SubscriptionHistoryRepository',
    'DiscountRepository',
    'CouponRepository',
    'PromotionRepository',
    'DiscountUsageRepository',
    'FeeRepository',
    'FeeScheduleRepository',
    'FeeCalculationRepository',
    
    # Rate Management
    'RateRepository',
    'RateScheduleRepository',
    'RateHistoryRepository',
    'DynamicPricingRepository',
    'SpecialRateRepository',
    'PricingRuleRepository',
    'PricingConditionRepository',
    'PricingOverrideRepository',
    
    # Notification Management
    'NotificationRepository',
    'NotificationTemplateRepository',
    'NotificationLogRepository',
    'NotificationPreferenceRepository',
    'CampaignRepository',
    'CampaignRecipientRepository',
    'CampaignAnalyticsRepository',
    'WebhookRepository',
    'WebhookDeliveryRepository',
    'WebhookEndpointRepository',
    'DeviceRepository',
    'DeviceTokenRepository',
    'DevicePreferenceRepository',
    
    # Sensor Management
    'SensorRepository',
    'SensorReadingRepository',
    'SensorEventRepository',
    'SensorCalibrationRepository',
    'SensorMaintenanceRepository',
    'SensorNetworkRepository',
    'SensorGatewayRepository',
    'SensorCommunicationLogRepository',
    
    # Audit Management
    'AuditLogRepository',
    'AuditEventRepository',
    'DataRetentionRepository',
    'ComplianceLogRepository',
    'AuditArchiveRepository',
    'ArchivedAuditRepository',
    
    # Analytics
    'AnalyticsRepository',
    'ReportRepository',
    'ReportScheduleRepository',
    'DashboardRepository',
    'MetricRepository',
    'OccupancyAnalyticsRepository',
    'OccupancyForecastRepository',
    'PeakTimeRepository',
    'RevenueAnalyticsRepository',
    'PayoutAnalyticsRepository',
    'TransactionAnalyticsRepository',
    
    # Configuration
    'SystemConfigRepository',
    'FeatureFlagRepository',
    'IntegrationConfigRepository',
    'EnvironmentConfigRepository',
    'ApplicationSettingsRepository',
    'BusinessSettingsRepository',
    'NotificationSettingsRepository',
    
    # Integration
    'IntegrationRepository',
    'IntegrationLogRepository',
    'APICallRepository',
    'SyncJobRepository',
    'ExternalServiceRepository',
    'ThirdPartyCredentialsRepository',
    'ThirdPartyDataRepository',
    'WebhookIntegrationRepository',
    
    # Support
    'TicketRepository',
    'TicketCommentRepository',
    'TicketAttachmentRepository',
    'TicketHistoryRepository',
    'FAQRepository',
    'KnowledgeBaseRepository',
    'FeedbackRepository',
    'RatingRepository',
    'ReviewRepository',
    'ComplaintRepository',
    
    # Violation
    'ViolationRepository',
    'ViolationTypeRepository',
    'ViolationPenaltyRepository',
    'ViolationAppealRepository',
    'ViolationPaymentRepository',
    
    # Reporting
    'CustomReportRepository',
    'ReportTemplateRepository',
    'ScheduledReportRepository',
    'ExportJobRepository',
    'DataExportRepository',
    
    # Base Classes
    'BaseRepository',
    'SoftDeleteRepository',
    'TimestampedRepository',
    'AuditableRepository',
    'VersionedRepository',
    'CacheableRepository',
    'SearchableRepository',
    
    # Factory
    'RepositoryFactory',
    'get_repository',
    'register_repository',
    'clear_repository_cache',
    
    # Mixins
    'SoftDeleteMixin',
    'TimestampMixin',
    'AuditMixin',
    'VersionMixin',
    'CacheMixin',
    'SearchMixin',
    'PaginationMixin',
    'FilterMixin',
    'BatchOperationMixin',
    'TransactionMixin',
    
    # Interfaces
    'IRepository',
    'IReadOnlyRepository',
    'IWriteOnlyRepository',
    'ISoftDeleteRepository',
    'ISearchableRepository',
    'ICacheableRepository',
    'IAuditableRepository',
    
    # Exceptions
    'RepositoryException',
    'EntityNotFoundException',
    'DuplicateEntityException',
    'ValidationException',
    'ConstraintViolationException',
    'OptimisticLockException',
    'ConcurrencyException',
    'RepositoryConfigurationException',
    'DataIntegrityException',
    
    # Decorators
    'transactional',
    'cacheable',
    'auditable',
    'retry_on_failure',
    'log_execution',
    'measure_time',
    'check_permissions',
    
    # Utilities
    'build_query',
    'apply_pagination',
    'apply_sorting',
    'apply_filtering',
    'build_search_condition',
    'parse_sort_params',
    'parse_filter_params',
    'validate_query_params',
    'sanitize_order_by',
    'create_paginated_response',
]

# ============================================================================
# Version Information
# ============================================================================

__version__ = '1.0.0'
__repository_version__ = '1.0.0'