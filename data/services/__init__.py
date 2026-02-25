# parking-management/data/services/__init__.py
"""
Service layer module exports for the parking management system.

This module serves as the central export point for all service classes,
providing a clean interface for business logic access across the application.
Services are organized by domain and encapsulate complex business operations,
orchestrating multiple repositories and implementing business rules.
"""

from typing import Dict, Any, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Base Service Classes
# ============================================================================

from .base_service import (
    BaseService,
    CrudService,
    AuditableService,
    CacheableService,
    ServiceException,
    ValidationException,
    BusinessRuleException,
    ServiceFactory,
    get_service,
    register_service,
    transactional,
    with_audit,
    with_cache,
    with_retry
)


# ============================================================================
# User Management Services
# ============================================================================

from .user_service import (
    # Main services
    UserService,
    AuthenticationService,
    AuthorizationService,
    ProfileService,
    
    # Supporting services
    MFAService,
    SessionService,
    PasswordService,
    APIKeyService,
    UserPreferenceService,
    
    # Role management
    RoleService,
    PermissionService,
    
    # Exceptions
    UserNotFoundException,
    AuthenticationException,
    AuthorizationException,
    InvalidCredentialsException,
    AccountLockedException,
    AccountSuspendedException,
    PasswordExpiredException,
    MFACodeInvalidException,
    SessionExpiredException
)

from .user_registration_service import (
    UserRegistrationService,
    RegistrationException,
    EmailVerificationException,
    PhoneVerificationException
)

from .user_analytics_service import (
    UserAnalyticsService,
    UserActivityService,
    UserMetricsService
)


# ============================================================================
# Vehicle Management Services
# ============================================================================

from .vehicle_service import (
    # Main services
    VehicleService,
    VehicleRegistrationService,
    VehicleInspectionService,
    VehicleInsuranceService,
    
    # Supporting services
    VehicleOwnershipService,
    VehicleDocumentService,
    VehicleHistoryService,
    
    # Blacklist management
    VehicleBlacklistService,
    StolenVehicleService,
    VehicleAlertService,
    
    # Exceptions
    VehicleNotFoundException,
    DuplicateLicensePlateException,
    VehicleBlacklistedException,
    VehicleStolenException,
    RegistrationExpiredException,
    InsuranceExpiredException,
    InspectionRequiredException
)

from .vehicle_lookup_service import (
    VehicleLookupService,
    DMVLookupService,
    VINDecoderService
)

from .vehicle_compliance_service import (
    VehicleComplianceService,
    ComplianceCheckService
)


# ============================================================================
# Parking Management Services
# ============================================================================

from .parking_service import (
    # Main services
    ParkingService,
    ParkingSpotService,
    ParkingZoneService,
    ParkingAllocationService,
    
    # Spot management
    SpotAvailabilityService,
    SpotMaintenanceService,
    SpotSensorService,
    SpotOccupancyService,
    
    # Gate management
    GateService,
    AccessControlService,
    EntryExitService,
    
    # Exceptions
    ParkingSpotNotFoundException,
    SpotNotAvailableException,
    SpotAlreadyOccupiedException,
    InvalidVehicleTypeException,
    ZoneFullException,
    MaintenanceInProgressException,
    GateNotOperationalException
)

from .parking_guidance_service import (
    ParkingGuidanceService,
    SpotFinderService,
    NavigationService
)

from .valet_service import (
    ValetService,
    ValetAssignmentService
)


# ============================================================================
# Reservation Services
# ============================================================================

from .reservation_service import (
    # Main services
    ReservationService,
    ReservationBookingService,
    ReservationManagementService,
    
    # Check-in/out services
    CheckInService,
    CheckOutService,
    
    # Recurring reservations
    RecurringReservationService,
    
    # Waitlist management
    WaitlistService,
    
    # Supporting services
    ReservationModificationService,
    ReservationCancellationService,
    ReservationExtensionService,
    ReservationReminderService,
    
    # Exceptions
    ReservationNotFoundException,
    ReservationConflictException,
    InvalidReservationStateException,
    CheckInWindowException,
    CheckOutWindowException,
    MaxExtensionsExceededException,
    NoShowException
)

from .booking_engine_service import (
    BookingEngineService,
    AvailabilitySearchService,
    PricingCalculationService
)

from .overstay_service import (
    OverstayService,
    GracePeriodService
)


# ============================================================================
# Payment Services
# ============================================================================

from .payment_service import (
    # Main services
    PaymentService,
    PaymentProcessingService,
    RefundService,
    DisputeService,
    
    # Payment method management
    PaymentMethodService,
    
    # Transaction services
    TransactionService,
    ReconciliationService,
    
    # Invoice services
    InvoiceService,
    BillingService,
    
    # Subscription services
    SubscriptionService,
    SubscriptionManagementService,
    SubscriptionBillingService,
    
    # Discount services
    DiscountService,
    CouponService,
    PromotionService,
    
    # Fee services
    FeeService,
    FeeCalculationService,
    
    # Exceptions
    PaymentNotFoundException,
    PaymentFailedException,
    PaymentDeclinedException,
    InsufficientFundsException,
    InvalidPaymentMethodException,
    RefundFailedException,
    RefundAmountExceededException,
    DisputeNotFoundException,
    SubscriptionNotFoundException,
    InvoiceNotFoundException,
    InvalidDiscountException
)

from .tax_service import (
    TaxService,
    TaxCalculationService
)

from .receipt_service import (
    ReceiptService,
    ReceiptGenerationService
)

from .payout_service import (
    PayoutService,
    SettlementService
)


# ============================================================================
# Rate Management Services
# ============================================================================

from .rate_service import (
    # Main services
    RateService,
    RateCalculationService,
    PricingService,
    
    # Dynamic pricing
    DynamicPricingService,
    DemandBasedPricingService,
    TimeBasedPricingService,
    
    # Special rates
    SpecialRateService,
    PromotionalRateService,
    
    # Exceptions
    RateNotFoundException,
    InvalidRateException,
    PricingRuleViolationException
)

from .pricing_engine_service import (
    PricingEngineService,
    QuoteService
)


# ============================================================================
# Notification Services
# ============================================================================

from .notification_service import (
    # Main services
    NotificationService,
    EmailService,
    SMSService,
    PushNotificationService,
    WhatsAppService,
    
    # Template management
    TemplateService,
    TemplateRenderingService,
    
    # Campaign management
    CampaignService,
    CampaignSchedulingService,
    
    # Webhook services
    WebhookService,
    WebhookDeliveryService,
    
    # User preferences
    NotificationPreferenceService,
    
    # Exceptions
    NotificationNotFoundException,
    TemplateNotFoundException,
    CampaignNotFoundException,
    WebhookNotFoundException,
    NotificationDeliveryException,
    TemplateRenderException,
    RateLimitExceededException
)

from .digest_service import (
    DigestService,
    DigestGenerationService
)

from .alert_service import (
    AlertService,
    AlertRoutingService
)


# ============================================================================
# Audit Services
# ============================================================================

from .audit_service import (
    # Main services
    AuditService,
    AuditLoggingService,
    AuditTrailService,
    
    # Compliance services
    ComplianceService,
    ComplianceValidationService,
    ComplianceReportingService,
    
    # Data retention
    DataRetentionService,
    DataArchivalService,
    DataPurgeService,
    
    # Security audit
    SecurityAuditService,
    SecurityMonitoringService,
    
    # Exceptions
    AuditLogNotFoundException,
    ComplianceRequirementNotFoundException,
    DataRetentionPolicyNotFoundException,
    ComplianceValidationException,
    AuditIntegrityException
)

from .reporting_service import (
    ReportingService,
    ReportGenerationService,
    ReportSchedulingService
)


# ============================================================================
# Analytics Services
# ============================================================================

from .analytics_service import (
    # Main services
    AnalyticsService,
    MetricsService,
    KPIService,
    
    # Business intelligence
    RevenueAnalyticsService,
    OccupancyAnalyticsService,
    UserAnalyticsService,
    VehicleAnalyticsService,
    
    # Forecasting
    ForecastingService,
    DemandForecastingService,
    RevenueForecastingService,
    
    # Reporting
    BusinessIntelligenceService,
    DataVisualizationService,
    
    # Exceptions
    MetricNotFoundException,
    ForecastGenerationException,
    DataExportException
)

from .dashboard_service import (
    DashboardService,
    WidgetService,
    DashboardRefreshService
)


# ============================================================================
# Integration Services
# ============================================================================

from .integration_service import (
    # Main services
    IntegrationService,
    ThirdPartyService,
    APIGatewayService,
    
    # External integrations
    PaymentGatewayService,
    SMSGatewayService,
    EmailGatewayService,
    PushGatewayService,
    
    # CRM integrations
    CRMIntegrationService,
    SalesforceIntegrationService,
    HubSpotIntegrationService,
    
    # ERP integrations
    ERPIntegrationService,
    SAPIntegrationService,
    OracleIntegrationService,
    
    # Exceptions
    IntegrationException,
    ThirdPartyTimeoutException,
    ThirdPartyAuthenticationException,
    WebhookDeliveryException
)

from .sync_service import (
    SyncService,
    DataSyncService,
    ReplicationService
)

from .import_export_service import (
    ImportService,
    ExportService,
    DataMigrationService
)


# ============================================================================
# Support Services
# ============================================================================

from .support_service import (
    # Main services
    SupportService,
    TicketService,
    CustomerSupportService,
    
    # Ticket management
    TicketAssignmentService,
    TicketEscalationService,
    TicketResolutionService,
    
    # Knowledge base
    KnowledgeBaseService,
    FAQService,
    
    # Feedback
    FeedbackService,
    RatingService,
    ReviewService,
    
    # Exceptions
    TicketNotFoundException,
    AssignmentException,
    EscalationException
)

from .notification_ticket_service import (
    NotificationTicketService
)


# ============================================================================
# Violation Services
# ============================================================================

from .violation_service import (
    # Main services
    ViolationService,
    ViolationDetectionService,
    ViolationEnforcementService,
    
    # Penalty management
    PenaltyService,
    FineCalculationService,
    
    # Appeals
    AppealService,
    AppealReviewService,
    
    # Exceptions
    ViolationNotFoundException,
    AppealNotFoundException,
    PenaltyCalculationException
)

from .enforcement_service import (
    EnforcementService,
    PatrolService
)


# ============================================================================
# Configuration Services
# ============================================================================

from .config_service import (
    # Main services
    ConfigurationService,
    SystemConfigService,
    FeatureFlagService,
    
    # Settings management
    ApplicationSettingsService,
    BusinessSettingsService,
    
    # Environment management
    EnvironmentService,
    DeploymentService,
    
    # Exceptions
    ConfigurationNotFoundException,
    InvalidConfigurationException
)

from .tenant_service import (
    TenantService,
    MultiTenantService
)


# ============================================================================
# Cache Services
# ============================================================================

from .cache_service import (
    # Main services
    CacheService,
    DistributedCacheService,
    QueryCacheService,
    
    # Cache management
    CacheInvalidationService,
    CacheWarmupService,
    
    # Locking
    DistributedLockService,
    
    # Exceptions
    CacheException,
    CacheMissException,
    CacheLockException,
    CacheWarmupException
)


# ============================================================================
# Utility Services
# ============================================================================

from .utility_service import (
    # Core utilities
    DateTimeService,
    TimeZoneService,
    LocaleService,
    CurrencyService,
    
    # Formatting
    FormattingService,
    ValidationService,
    SanitizationService,
    
    # Generation
    IdGenerationService,
    TokenGenerationService,
    CodeGenerationService,
    
    # Communication
    CommunicationService
)

from .encryption_service import (
    EncryptionService,
    HashingService,
    KeyManagementService
)

from .file_service import (
    FileService,
    StorageService,
    ImageService
)


# ============================================================================
# Service Factory and Registry
# ============================================================================

class ServiceRegistry:
    """
    Central registry for all services.
    Provides access to all service instances and manages their lifecycle.
    """
    
    _instance = None
    _services: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, name: str, service: Any) -> None:
        """Register a service instance."""
        self._services[name] = service
        logger.debug(f"Registered service: {name}")
    
    def get(self, name: str, default: Any = None) -> Any:
        """Get a registered service by name."""
        return self._services.get(name, default)
    
    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services
    
    def all(self) -> Dict[str, Any]:
        """Get all registered services."""
        return self._services.copy()
    
    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        logger.debug("Cleared all service registrations")


# Global service registry instance
service_registry = ServiceRegistry()


# ============================================================================
# Service Initialization
# ============================================================================

def init_services(
    session,
    cache_repository=None,
    config: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Initialize all services with their dependencies.
    
    Args:
        session: SQLAlchemy session
        cache_repository: Optional cache repository
        config: Optional configuration dictionary
        
    Returns:
        Dictionary of initialized services
    """
    from .base_service import ServiceFactory
    
    factory = ServiceFactory(session, cache_repository, config or {})
    services = {}
    
    # Initialize all services using the factory
    service_classes = [
        # User services
        ('user_service', UserService),
        ('auth_service', AuthenticationService),
        ('role_service', RoleService),
        
        # Vehicle services
        ('vehicle_service', VehicleService),
        ('vehicle_blacklist_service', VehicleBlacklistService),
        
        # Parking services
        ('parking_service', ParkingService),
        ('spot_service', ParkingSpotService),
        ('zone_service', ParkingZoneService),
        
        # Reservation services
        ('reservation_service', ReservationService),
        ('booking_service', ReservationBookingService),
        ('waitlist_service', WaitlistService),
        
        # Payment services
        ('payment_service', PaymentService),
        ('invoice_service', InvoiceService),
        ('subscription_service', SubscriptionService),
        ('discount_service', DiscountService),
        
        # Rate services
        ('rate_service', RateService),
        ('pricing_service', PricingService),
        
        # Notification services
        ('notification_service', NotificationService),
        ('email_service', EmailService),
        ('sms_service', SMSService),
        ('webhook_service', WebhookService),
        
        # Audit services
        ('audit_service', AuditService),
        ('compliance_service', ComplianceService),
        ('retention_service', DataRetentionService),
        
        # Analytics services
        ('analytics_service', AnalyticsService),
        ('kpi_service', KPIService),
        ('forecasting_service', ForecastingService),
        
        # Integration services
        ('integration_service', IntegrationService),
        ('sync_service', SyncService),
        
        # Support services
        ('support_service', SupportService),
        ('ticket_service', TicketService),
        
        # Violation services
        ('violation_service', ViolationService),
        ('enforcement_service', EnforcementService),
        
        # Configuration services
        ('config_service', ConfigurationService),
        
        # Cache services
        ('cache_service', CacheService),
        
        # Utility services
        ('utility_service', UtilityService),
        ('encryption_service', EncryptionService),
        ('file_service', FileService),
    ]
    
    for name, service_class in service_classes:
        try:
            service = factory.create(service_class)
            services[name] = service
            service_registry.register(name, service)
            logger.info(f"Initialized service: {name}")
        except Exception as e:
            logger.error(f"Failed to initialize service {name}: {e}")
    
    return services


def get_service_by_name(name: str) -> Any:
    """
    Get a service by name from the registry.
    
    Args:
        name: Service name
        
    Returns:
        Service instance or None if not found
    """
    return service_registry.get(name)


# ============================================================================
# Convenience Functions
# ============================================================================

def get_user_service() -> UserService:
    """Get the user service instance."""
    return service_registry.get('user_service')


def get_auth_service() -> AuthenticationService:
    """Get the authentication service instance."""
    return service_registry.get('auth_service')


def get_vehicle_service() -> VehicleService:
    """Get the vehicle service instance."""
    return service_registry.get('vehicle_service')


def get_parking_service() -> ParkingService:
    """Get the parking service instance."""
    return service_registry.get('parking_service')


def get_reservation_service() -> ReservationService:
    """Get the reservation service instance."""
    return service_registry.get('reservation_service')


def get_payment_service() -> PaymentService:
    """Get the payment service instance."""
    return service_registry.get('payment_service')


def get_notification_service() -> NotificationService:
    """Get the notification service instance."""
    return service_registry.get('notification_service')


def get_audit_service() -> AuditService:
    """Get the audit service instance."""
    return service_registry.get('audit_service')


def get_analytics_service() -> AnalyticsService:
    """Get the analytics service instance."""
    return service_registry.get('analytics_service')


def get_config_service() -> ConfigurationService:
    """Get the configuration service instance."""
    return service_registry.get('config_service')


def get_cache_service() -> CacheService:
    """Get the cache service instance."""
    return service_registry.get('cache_service')


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Base Service Classes
    'BaseService',
    'CrudService',
    'AuditableService',
    'CacheableService',
    'ServiceException',
    'ValidationException',
    'BusinessRuleException',
    'ServiceFactory',
    'get_service',
    'register_service',
    'transactional',
    'with_audit',
    'with_cache',
    'with_retry',
    
    # Service Registry
    'ServiceRegistry',
    'service_registry',
    'init_services',
    'get_service_by_name',
    
    # Convenience Functions
    'get_user_service',
    'get_auth_service',
    'get_vehicle_service',
    'get_parking_service',
    'get_reservation_service',
    'get_payment_service',
    'get_notification_service',
    'get_audit_service',
    'get_analytics_service',
    'get_config_service',
    'get_cache_service',
    
    # ========================================================================
    # User Management Services
    # ========================================================================
    
    # Main services
    'UserService',
    'AuthenticationService',
    'AuthorizationService',
    'ProfileService',
    
    # Supporting services
    'MFAService',
    'SessionService',
    'PasswordService',
    'APIKeyService',
    'UserPreferenceService',
    
    # Role management
    'RoleService',
    'PermissionService',
    
    # Registration
    'UserRegistrationService',
    
    # Analytics
    'UserAnalyticsService',
    'UserActivityService',
    'UserMetricsService',
    
    # Exceptions
    'UserNotFoundException',
    'AuthenticationException',
    'AuthorizationException',
    'InvalidCredentialsException',
    'AccountLockedException',
    'AccountSuspendedException',
    'PasswordExpiredException',
    'MFACodeInvalidException',
    'SessionExpiredException',
    'RegistrationException',
    'EmailVerificationException',
    'PhoneVerificationException',
    
    # ========================================================================
    # Vehicle Management Services
    # ========================================================================
    
    # Main services
    'VehicleService',
    'VehicleRegistrationService',
    'VehicleInspectionService',
    'VehicleInsuranceService',
    
    # Supporting services
    'VehicleOwnershipService',
    'VehicleDocumentService',
    'VehicleHistoryService',
    
    # Blacklist management
    'VehicleBlacklistService',
    'StolenVehicleService',
    'VehicleAlertService',
    
    # Lookup services
    'VehicleLookupService',
    'DMVLookupService',
    'VINDecoderService',
    
    # Compliance
    'VehicleComplianceService',
    'ComplianceCheckService',
    
    # Exceptions
    'VehicleNotFoundException',
    'DuplicateLicensePlateException',
    'VehicleBlacklistedException',
    'VehicleStolenException',
    'RegistrationExpiredException',
    'InsuranceExpiredException',
    'InspectionRequiredException',
    
    # ========================================================================
    # Parking Management Services
    # ========================================================================
    
    # Main services
    'ParkingService',
    'ParkingSpotService',
    'ParkingZoneService',
    'ParkingAllocationService',
    
    # Spot management
    'SpotAvailabilityService',
    'SpotMaintenanceService',
    'SpotSensorService',
    'SpotOccupancyService',
    
    # Gate management
    'GateService',
    'AccessControlService',
    'EntryExitService',
    
    # Guidance
    'ParkingGuidanceService',
    'SpotFinderService',
    'NavigationService',
    
    # Valet
    'ValetService',
    'ValetAssignmentService',
    
    # Exceptions
    'ParkingSpotNotFoundException',
    'SpotNotAvailableException',
    'SpotAlreadyOccupiedException',
    'InvalidVehicleTypeException',
    'ZoneFullException',
    'MaintenanceInProgressException',
    'GateNotOperationalException',
    
    # ========================================================================
    # Reservation Services
    # ========================================================================
    
    # Main services
    'ReservationService',
    'ReservationBookingService',
    'ReservationManagementService',
    
    # Check-in/out
    'CheckInService',
    'CheckOutService',
    
    # Recurring
    'RecurringReservationService',
    
    # Waitlist
    'WaitlistService',
    
    # Supporting
    'ReservationModificationService',
    'ReservationCancellationService',
    'ReservationExtensionService',
    'ReservationReminderService',
    
    # Booking engine
    'BookingEngineService',
    'AvailabilitySearchService',
    'PricingCalculationService',
    
    # Overstay
    'OverstayService',
    'GracePeriodService',
    
    # Exceptions
    'ReservationNotFoundException',
    'ReservationConflictException',
    'InvalidReservationStateException',
    'CheckInWindowException',
    'CheckOutWindowException',
    'MaxExtensionsExceededException',
    'NoShowException',
    
    # ========================================================================
    # Payment Services
    # ========================================================================
    
    # Main services
    'PaymentService',
    'PaymentProcessingService',
    'RefundService',
    'DisputeService',
    
    # Payment method
    'PaymentMethodService',
    
    # Transaction
    'TransactionService',
    'ReconciliationService',
    
    # Invoice
    'InvoiceService',
    'BillingService',
    
    # Subscription
    'SubscriptionService',
    'SubscriptionManagementService',
    'SubscriptionBillingService',
    
    # Discount
    'DiscountService',
    'CouponService',
    'PromotionService',
    
    # Fee
    'FeeService',
    'FeeCalculationService',
    
    # Tax
    'TaxService',
    'TaxCalculationService',
    
    # Receipt
    'ReceiptService',
    'ReceiptGenerationService',
    
    # Payout
    'PayoutService',
    'SettlementService',
    
    # Exceptions
    'PaymentNotFoundException',
    'PaymentFailedException',
    'PaymentDeclinedException',
    'InsufficientFundsException',
    'InvalidPaymentMethodException',
    'RefundFailedException',
    'RefundAmountExceededException',
    'DisputeNotFoundException',
    'SubscriptionNotFoundException',
    'InvoiceNotFoundException',
    'InvalidDiscountException',
    
    # ========================================================================
    # Rate Management Services
    # ========================================================================
    
    # Main services
    'RateService',
    'RateCalculationService',
    'PricingService',
    
    # Dynamic pricing
    'DynamicPricingService',
    'DemandBasedPricingService',
    'TimeBasedPricingService',
    
    # Special rates
    'SpecialRateService',
    'PromotionalRateService',
    
    # Pricing engine
    'PricingEngineService',
    'QuoteService',
    
    # Exceptions
    'RateNotFoundException',
    'InvalidRateException',
    'PricingRuleViolationException',
    
    # ========================================================================
    # Notification Services
    # ========================================================================
    
    # Main services
    'NotificationService',
    'EmailService',
    'SMSService',
    'PushNotificationService',
    'WhatsAppService',
    
    # Template
    'TemplateService',
    'TemplateRenderingService',
    
    # Campaign
    'CampaignService',
    'CampaignSchedulingService',
    
    # Webhook
    'WebhookService',
    'WebhookDeliveryService',
    
    # Preferences
    'NotificationPreferenceService',
    
    # Digest
    'DigestService',
    'DigestGenerationService',
    
    # Alert
    'AlertService',
    'AlertRoutingService',
    
    # Exceptions
    'NotificationNotFoundException',
    'TemplateNotFoundException',
    'CampaignNotFoundException',
    'WebhookNotFoundException',
    'NotificationDeliveryException',
    'TemplateRenderException',
    'RateLimitExceededException',
    
    # ========================================================================
    # Audit Services
    # ========================================================================
    
    # Main services
    'AuditService',
    'AuditLoggingService',
    'AuditTrailService',
    
    # Compliance
    'ComplianceService',
    'ComplianceValidationService',
    'ComplianceReportingService',
    
    # Data retention
    'DataRetentionService',
    'DataArchivalService',
    'DataPurgeService',
    
    # Security
    'SecurityAuditService',
    'SecurityMonitoringService',
    
    # Reporting
    'ReportingService',
    'ReportGenerationService',
    'ReportSchedulingService',
    
    # Exceptions
    'AuditLogNotFoundException',
    'ComplianceRequirementNotFoundException',
    'DataRetentionPolicyNotFoundException',
    'ComplianceValidationException',
    'AuditIntegrityException',
    
    # ========================================================================
    # Analytics Services
    # ========================================================================
    
    # Main services
    'AnalyticsService',
    'MetricsService',
    'KPIService',
    
    # Business intelligence
    'RevenueAnalyticsService',
    'OccupancyAnalyticsService',
    'UserAnalyticsService',
    'VehicleAnalyticsService',
    
    # Forecasting
    'ForecastingService',
    'DemandForecastingService',
    'RevenueForecastingService',
    
    # Reporting
    'BusinessIntelligenceService',
    'DataVisualizationService',
    
    # Dashboard
    'DashboardService',
    'WidgetService',
    'DashboardRefreshService',
    
    # Exceptions
    'MetricNotFoundException',
    'ForecastGenerationException',
    'DataExportException',
    
    # ========================================================================
    # Integration Services
    # ========================================================================
    
    # Main services
    'IntegrationService',
    'ThirdPartyService',
    'APIGatewayService',
    
    # Gateway services
    'PaymentGatewayService',
    'SMSGatewayService',
    'EmailGatewayService',
    'PushGatewayService',
    
    # CRM
    'CRMIntegrationService',
    'SalesforceIntegrationService',
    'HubSpotIntegrationService',
    
    # ERP
    'ERPIntegrationService',
    'SAPIntegrationService',
    'OracleIntegrationService',
    
    # Sync
    'SyncService',
    'DataSyncService',
    'ReplicationService',
    
    # Import/Export
    'ImportService',
    'ExportService',
    'DataMigrationService',
    
    # Exceptions
    'IntegrationException',
    'ThirdPartyTimeoutException',
    'ThirdPartyAuthenticationException',
    'WebhookDeliveryException',
    
    # ========================================================================
    # Support Services
    # ========================================================================
    
    # Main services
    'SupportService',
    'TicketService',
    'CustomerSupportService',
    
    # Ticket management
    'TicketAssignmentService',
    'TicketEscalationService',
    'TicketResolutionService',
    
    # Knowledge base
    'KnowledgeBaseService',
    'FAQService',
    
    # Feedback
    'FeedbackService',
    'RatingService',
    'ReviewService',
    
    # Exceptions
    'TicketNotFoundException',
    'AssignmentException',
    'EscalationException',
    
    # ========================================================================
    # Violation Services
    # ========================================================================
    
    # Main services
    'ViolationService',
    'ViolationDetectionService',
    'ViolationEnforcementService',
    
    # Penalty
    'PenaltyService',
    'FineCalculationService',
    
    # Appeals
    'AppealService',
    'AppealReviewService',
    
    # Enforcement
    'EnforcementService',
    'PatrolService',
    
    # Exceptions
    'ViolationNotFoundException',
    'AppealNotFoundException',
    'PenaltyCalculationException',
    
    # ========================================================================
    # Configuration Services
    # ========================================================================
    
    # Main services
    'ConfigurationService',
    'SystemConfigService',
    'FeatureFlagService',
    
    # Settings
    'ApplicationSettingsService',
    'BusinessSettingsService',
    
    # Environment
    'EnvironmentService',
    'DeploymentService',
    
    # Tenant
    'TenantService',
    'MultiTenantService',
    
    # Exceptions
    'ConfigurationNotFoundException',
    'InvalidConfigurationException',
    
    # ========================================================================
    # Cache Services
    # ========================================================================
    
    # Main services
    'CacheService',
    'DistributedCacheService',
    'QueryCacheService',
    
    # Management
    'CacheInvalidationService',
    'CacheWarmupService',
    
    # Locking
    'DistributedLockService',
    
    # Exceptions
    'CacheException',
    'CacheMissException',
    'CacheLockException',
    'CacheWarmupException',
    
    # ========================================================================
    # Utility Services
    # ========================================================================
    
    # Core utilities
    'DateTimeService',
    'TimeZoneService',
    'LocaleService',
    'CurrencyService',
    
    # Formatting
    'FormattingService',
    'ValidationService',
    'SanitizationService',
    
    # Generation
    'IdGenerationService',
    'TokenGenerationService',
    'CodeGenerationService',
    
    # Communication
    'CommunicationService',
    
    # Encryption
    'EncryptionService',
    'HashingService',
    'KeyManagementService',
    
    # File
    'FileService',
    'StorageService',
    'ImageService',
    
    # ========================================================================
    # Utility Functions
    # ========================================================================
    
    # Service helpers
    'get_service_by_name',
]

# Version information
__version__ = '1.0.0'
__service_version__ = '1.0.0'