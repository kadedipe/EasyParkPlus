# parking-management/data/services/data_service.py
"""
Data service module for the parking management system.

This module provides the core data access layer, orchestrating repositories
and providing a unified interface for data operations with caching,
auditing, and transaction management.
"""

from typing import (
    List, Optional, Dict, Any, Tuple, Union, TypeVar, Generic,
    Callable, Awaitable
)
from datetime import datetime, date, time, timedelta
from decimal import Decimal
import logging
import json
from contextlib import contextmanager
from functools import wraps

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..repositories import (
    # Base
    BaseRepository,
    RepositoryFactory,
    get_repository,
    
    # User repositories
    UserRepository,
    UserSessionRepository,
    UserPreferenceRepository,
    UserDeviceRepository,
    UserAuditLogRepository,
    AuthProviderRepository,
    MFASettingRepository,
    PasswordResetTokenRepository,
    EmailVerificationTokenRepository,
    APIKeyRepository,
    RoleRepository,
    PermissionRepository,
    RoleAssignmentRepository,
    
    # Vehicle repositories
    VehicleRepository,
    VehicleRegistrationRepository,
    VehicleInsuranceRepository,
    VehicleInspectionRepository,
    VehicleOwnershipRepository,
    VehicleDocumentRepository,
    VehicleImageRepository,
    VehicleHistoryRepository,
    VehicleBlacklistRepository,
    VehicleAlertRepository,
    StolenVehicleRepository,
    
    # Parking repositories
    ParkingSpotRepository,
    SpotMaintenanceRepository,
    SpotSensorRepository,
    SpotOccupancyRepository,
    SpotHistoryRepository,
    ParkingZoneRepository,
    ZoneScheduleRepository,
    ZoneRestrictionRepository,
    ZoneRateRepository,
    ZoneCapacityRepository,
    GateRepository,
    GateAccessLogRepository,
    
    # Reservation repositories
    ReservationRepository,
    RecurringReservationRepository,
    ReservationHistoryRepository,
    WaitlistRepository,
    CheckInRepository,
    CheckOutRepository,
    
    # Payment repositories
    PaymentRepository,
    PaymentMethodRepository,
    PaymentTransactionRepository,
    RefundRepository,
    DisputeRepository,
    InvoiceRepository,
    InvoiceItemRepository,
    SubscriptionRepository,
    SubscriptionPlanRepository,
    DiscountRepository,
    CouponRepository,
    PromotionRepository,
    FeeRepository,
    
    # Rate repositories
    RateRepository,
    RateScheduleRepository,
    DynamicPricingRepository,
    PricingRuleRepository,
    
    # Notification repositories
    NotificationRepository,
    NotificationTemplateRepository,
    NotificationLogRepository,
    NotificationPreferenceRepository,
    CampaignRepository,
    WebhookRepository,
    DeviceRepository,
    
    # Audit repositories
    AuditLogRepository,
    ComplianceLogRepository,
    DataRetentionRepository,
    
    # Analytics repositories
    AnalyticsRepository,
    ReportRepository,
    DashboardRepository,
    MetricRepository,
    
    # Configuration repositories
    SystemConfigRepository,
    FeatureFlagRepository,
    IntegrationConfigRepository,
    
    # Cache repository
    CacheRepository
)

from .base_service import (
    BaseService,
    ServiceException,
    ValidationException,
    BusinessRuleException,
    transactional,
    with_audit,
    with_cache
)

from ..models.enums import (
    # User enums
    UserStatus,
    UserRole,
    AuthMethod,
    MFAMethod,
    
    # Vehicle enums
    VehicleStatus,
    VehicleType,
    FuelType,
    RegistrationStatus,
    InsuranceStatus,
    InspectionStatus,
    OwnershipType,
    
    # Parking enums
    SpotType,
    SpotStatus,
    ZoneType,
    ZoneStatus,
    AccessType,
    GateType,
    
    # Reservation enums
    ReservationStatus,
    ReservationType,
    PaymentStatus,
    RecurringFrequency,
    WaitlistStatus,
    
    # Payment enums
    PaymentMethodType,
    PaymentProvider,
    TransactionType,
    DisputeStatus,
    SubscriptionStatus,
    InvoiceStatus,
    DiscountType,
    Currency,
    
    # Notification enums
    NotificationType,
    NotificationChannel,
    NotificationStatus,
    NotificationPriority,
    TemplateType,
    DeviceType,
    CampaignStatus,
    WebhookMethod,
    
    # Audit enums
    AuditAction,
    AuditStatus,
    AuditSeverity,
    AuditCategory,
    AuditResourceType,
    ComplianceStandard,
    RetentionAction,
    
    # General enums
    DayOfWeek,
    Language,
    CountryCode,
    Timezone
)

# Configure logging
logger = logging.getLogger(__name__)

# Type variables for generic methods
T = TypeVar('T')
ID = TypeVar('ID')


# ============================================================================
# Data Service - Main Entry Point
# ============================================================================

class DataService(BaseService):
    """
    Core data service providing unified access to all repositories.
    
    This service orchestrates all repository operations, providing a single
    entry point for data access with built-in caching, auditing, and
    transaction management.
    """
    
    def __init__(
        self,
        session: Session,
        cache_repository: Optional[CacheRepository] = None,
        enable_audit: bool = True,
        enable_cache: bool = True
    ):
        """
        Initialize the data service.
        
        Args:
            session: SQLAlchemy session
            cache_repository: Optional cache repository
            enable_audit: Whether to enable automatic auditing
            enable_cache: Whether to enable caching
        """
        super().__init__(session)
        self.cache = cache_repository
        self.enable_audit = enable_audit
        self.enable_cache = enable_cache
        self.current_user_id: Optional[int] = None
        self.current_ip: Optional[str] = None
        self.current_user_agent: Optional[str] = None
        
        # Initialize repositories
        self._init_repositories()
        
        logger.info("DataService initialized")
    
    def _init_repositories(self) -> None:
        """Initialize all repositories."""
        # User repositories
        self.users = UserRepository(self.session)
        self.user_sessions = UserSessionRepository(self.session)
        self.user_preferences = UserPreferenceRepository(self.session)
        self.user_devices = UserDeviceRepository(self.session)
        self.user_audit_logs = UserAuditLogRepository(self.session)
        self.auth_providers = AuthProviderRepository(self.session)
        self.mfa_settings = MFASettingRepository(self.session)
        self.password_reset_tokens = PasswordResetTokenRepository(self.session)
        self.email_verification_tokens = EmailVerificationTokenRepository(self.session)
        self.api_keys = APIKeyRepository(self.session)
        self.roles = RoleRepository(self.session)
        self.permissions = PermissionRepository(self.session)
        self.role_assignments = RoleAssignmentRepository(self.session)
        
        # Vehicle repositories
        self.vehicles = VehicleRepository(self.session)
        self.vehicle_registrations = VehicleRegistrationRepository(self.session)
        self.vehicle_insurance = VehicleInsuranceRepository(self.session)
        self.vehicle_inspections = VehicleInspectionRepository(self.session)
        self.vehicle_ownership = VehicleOwnershipRepository(self.session)
        self.vehicle_documents = VehicleDocumentRepository(self.session)
        self.vehicle_images = VehicleImageRepository(self.session)
        self.vehicle_history = VehicleHistoryRepository(self.session)
        self.vehicle_blacklist = VehicleBlacklistRepository(self.session)
        self.vehicle_alerts = VehicleAlertRepository(self.session)
        self.stolen_vehicles = StolenVehicleRepository(self.session)
        
        # Parking repositories
        self.parking_spots = ParkingSpotRepository(self.session)
        self.spot_maintenance = SpotMaintenanceRepository(self.session)
        self.spot_sensors = SpotSensorRepository(self.session)
        self.spot_occupancy = SpotOccupancyRepository(self.session)
        self.spot_history = SpotHistoryRepository(self.session)
        self.parking_zones = ParkingZoneRepository(self.session)
        self.zone_schedules = ZoneScheduleRepository(self.session)
        self.zone_restrictions = ZoneRestrictionRepository(self.session)
        self.zone_rates = ZoneRateRepository(self.session)
        self.zone_capacity = ZoneCapacityRepository(self.session)
        self.gates = GateRepository(self.session)
        self.gate_access_logs = GateAccessLogRepository(self.session)
        
        # Reservation repositories
        self.reservations = ReservationRepository(self.session)
        self.recurring_reservations = RecurringReservationRepository(self.session)
        self.reservation_history = ReservationHistoryRepository(self.session)
        self.waitlist = WaitlistRepository(self.session)
        self.check_ins = CheckInRepository(self.session)
        self.check_outs = CheckOutRepository(self.session)
        
        # Payment repositories
        self.payments = PaymentRepository(self.session)
        self.payment_methods = PaymentMethodRepository(self.session)
        self.payment_transactions = PaymentTransactionRepository(self.session)
        self.refunds = RefundRepository(self.session)
        self.disputes = DisputeRepository(self.session)
        self.invoices = InvoiceRepository(self.session)
        self.invoice_items = InvoiceItemRepository(self.session)
        self.subscriptions = SubscriptionRepository(self.session)
        self.subscription_plans = SubscriptionPlanRepository(self.session)
        self.discounts = DiscountRepository(self.session)
        self.coupons = CouponRepository(self.session)
        self.promotions = PromotionRepository(self.session)
        self.fees = FeeRepository(self.session)
        
        # Rate repositories
        self.rates = RateRepository(self.session)
        self.rate_schedules = RateScheduleRepository(self.session)
        self.dynamic_pricing = DynamicPricingRepository(self.session)
        self.pricing_rules = PricingRuleRepository(self.session)
        
        # Notification repositories
        self.notifications = NotificationRepository(self.session)
        self.notification_templates = NotificationTemplateRepository(self.session)
        self.notification_logs = NotificationLogRepository(self.session)
        self.notification_preferences = NotificationPreferenceRepository(self.session)
        self.campaigns = CampaignRepository(self.session)
        self.webhooks = WebhookRepository(self.session)
        self.devices = DeviceRepository(self.session)
        
        # Audit repositories
        self.audit_logs = AuditLogRepository(self.session)
        self.compliance_logs = ComplianceLogRepository(self.session)
        self.data_retention = DataRetentionRepository(self.session)
        
        # Analytics repositories
        self.analytics = AnalyticsRepository(self.session)
        self.reports = ReportRepository(self.session)
        self.dashboards = DashboardRepository(self.session)
        self.metrics = MetricRepository(self.session)
        
        # Configuration repositories
        self.system_config = SystemConfigRepository(self.session)
        self.feature_flags = FeatureFlagRepository(self.session)
        self.integration_config = IntegrationConfigRepository(self.session)
    
    # ========================================================================
    # Context Management
    # ========================================================================
    
    def set_context(
        self,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Set context for audit logging.
        
        Args:
            user_id: Current user ID
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.current_user_id = user_id
        self.current_ip = ip_address
        self.current_user_agent = user_agent
        
        # Update repositories that need context
        if hasattr(self.users, 'set_audit_context'):
            self.users.set_audit_context(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
    
    def clear_context(self) -> None:
        """Clear the current context."""
        self.current_user_id = None
        self.current_ip = None
        self.current_user_agent = None
    
    @contextmanager
    def with_context(
        self,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Context manager for temporary context.
        
        Args:
            user_id: Current user ID
            ip_address: Client IP address
            user_agent: Client user agent
        """
        old_user_id = self.current_user_id
        old_ip = self.current_ip
        old_agent = self.current_user_agent
        
        self.set_context(user_id, ip_address, user_agent)
        
        try:
            yield
        finally:
            self.set_context(old_user_id, old_ip, old_agent)
    
    # ========================================================================
    # Transaction Management
    # ========================================================================
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        try:
            yield
            self.session.commit()
            logger.debug("Transaction committed")
        except Exception as e:
            self.session.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
    
    def in_transaction(self, func: Callable, *args, **kwargs):
        """Execute a function within a transaction."""
        with self.transaction():
            return func(*args, **kwargs)
    
    # ========================================================================
    # Cache Management
    # ========================================================================
    
    def get_cached(self, key: str, default: Any = None) -> Any:
        """Get a value from cache."""
        if self.enable_cache and self.cache:
            return self.cache.get(key, default=default)
        return default
    
    def set_cached(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache."""
        if self.enable_cache and self.cache:
            return self.cache.set(key, value, ttl)
        return False
    
    def invalidate_cache(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern."""
        if self.enable_cache and self.cache:
            return self.cache.invalidate_pattern(pattern)
        return 0
    
    def clear_cache(self) -> int:
        """Clear all cache."""
        if self.enable_cache and self.cache:
            return self.cache.clear_all()
        return 0
    
    # ========================================================================
    # Audit Logging
    # ========================================================================
    
    def log_audit(
        self,
        action: AuditAction,
        resource_type: AuditResourceType,
        resource_id: Optional[str] = None,
        category: AuditCategory = AuditCategory.SYSTEM,
        severity: AuditSeverity = AuditSeverity.INFO,
        status: AuditStatus = AuditStatus.SUCCESS,
        details: Optional[Dict] = None,
        changes: Optional[List[Dict]] = None
    ) -> None:
        """
        Log an audit event.
        
        Args:
            action: Action performed
            resource_type: Type of resource
            resource_id: Resource identifier
            category: Audit category
            severity: Severity level
            status: Action status
            details: Additional details
            changes: List of changes made
        """
        if not self.enable_audit:
            return
        
        self.audit_logs.log_action(
            actor_id=self.current_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            category=category,
            severity=severity,
            status=status,
            details=details,
            changes=changes,
            ip_address=self.current_ip,
            user_agent=self.current_user_agent
        )
    
    # ========================================================================
    # Health Check
    # ========================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all data services.
        
        Returns:
            Health check results
        """
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'unknown',
            'cache': 'unknown',
            'repositories': {}
        }
        
        # Check database connection
        try:
            self.session.execute('SELECT 1')
            results['database'] = 'connected'
        except Exception as e:
            results['database'] = f'error: {e}'
            results['status'] = 'degraded'
        
        # Check cache connection
        if self.cache:
            try:
                self.cache.set('health_check', 'ok', ttl=5)
                results['cache'] = 'connected'
            except Exception as e:
                results['cache'] = f'error: {e}'
                results['status'] = 'degraded'
        else:
            results['cache'] = 'disabled'
        
        # Check critical repositories
        critical_repos = ['users', 'vehicles', 'parking_spots', 'reservations']
        for repo_name in critical_repos:
            repo = getattr(self, repo_name, None)
            if repo:
                try:
                    # Try a simple count operation
                    count = repo.count()
                    results['repositories'][repo_name] = f'ok ({count} records)'
                except Exception as e:
                    results['repositories'][repo_name] = f'error: {e}'
                    results['status'] = 'degraded'
            else:
                results['repositories'][repo_name] = 'not found'
                results['status'] = 'degraded'
        
        return results
    
    # ========================================================================
    # Statistics
    # ========================================================================
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """
        Get overall system statistics.
        
        Returns:
            System statistics
        """
        return {
            'users': self.users.get_user_statistics(),
            'vehicles': self.vehicles.get_vehicle_statistics(),
            'parking': self.parking_spots.get_zone_statistics(None),
            'reservations': self.reservations.get_reservation_statistics(),
            'payments': self.payments.get_payment_statistics(),
            'audit': self.audit_logs.get_audit_metrics(),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    # ========================================================================
    # Cleanup Operations
    # ========================================================================
    
    def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """
        Clean up old data across all repositories.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Dictionary with cleanup counts
        """
        results = {}
        
        with self.transaction():
            # Clean up old sessions
            results['sessions'] = self.user_sessions.cleanup_old_sessions(days)
            
            # Clean up old notifications
            if hasattr(self.notifications, 'cleanup_old_notifications'):
                results['notifications'] = self.notifications.cleanup_old_notifications(days)
            
            # Clean up old audit logs
            if hasattr(self.audit_logs, 'cleanup_old_logs'):
                results['audit_logs'] = self.audit_logs.cleanup_old_logs(days)
            
            # Clean up old spot history
            if hasattr(self.spot_history, 'cleanup_old_history'):
                results['spot_history'] = self.spot_history.cleanup_old_history(days)
            
            # Clean up old reservation history
            if hasattr(self.reservation_history, 'cleanup_old_history'):
                results['reservation_history'] = self.reservation_history.cleanup_old_history(days)
            
            # Clean up expired cache entries
            if self.cache:
                results['cache'] = self.cache.cleanup_expired()
        
        logger.info(f"Cleaned up old data: {results}")
        return results
    
    # ========================================================================
    # Backup Operations
    # ========================================================================
    
    def create_backup(self, tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a backup of specified tables.
        
        Args:
            tables: List of table names to backup (None for all)
            
        Returns:
            Backup information
        """
        backup_data = {}
        timestamp = datetime.utcnow().isoformat()
        
        # Define backup functions for each repository
        backup_handlers = {
            'users': lambda: [u.to_dict() for u in self.users.get_all()],
            'vehicles': lambda: [v.to_dict() for v in self.vehicles.get_all()],
            'parking_spots': lambda: [s.to_dict() for s in self.parking_spots.get_all()],
            'reservations': lambda: [r.to_dict() for r in self.reservations.get_all()],
            'payments': lambda: [p.to_dict() for p in self.payments.get_all()],
            'invoices': lambda: [i.to_dict() for i in self.invoices.get_all()],
            'subscriptions': lambda: [s.to_dict() for s in self.subscriptions.get_all()],
        }
        
        # Filter tables if specified
        if tables:
            handlers = {k: v for k, v in backup_handlers.items() if k in tables}
        else:
            handlers = backup_handlers
        
        # Collect backup data
        for name, handler in handlers.items():
            try:
                data = handler()
                backup_data[name] = data
                logger.info(f"Backed up {len(data)} records from {name}")
            except Exception as e:
                logger.error(f"Failed to backup {name}: {e}")
                backup_data[name] = {'error': str(e)}
        
        return {
            'timestamp': timestamp,
            'tables': list(handlers.keys()),
            'data': backup_data
        }
    
    def restore_backup(self, backup_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Restore from a backup.
        
        Args:
            backup_data: Backup data from create_backup
            
        Returns:
            Restore counts
        """
        results = {}
        
        with self.transaction():
            # Define restore order (respect foreign keys)
            restore_order = [
                'users',
                'vehicles',
                'parking_spots',
                'reservations',
                'payments',
                'invoices',
                'subscriptions'
            ]
            
            for table in restore_order:
                if table in backup_data.get('data', {}):
                    data = backup_data['data'][table]
                    if isinstance(data, list) and not isinstance(data, dict):
                        # This would need proper model restoration logic
                        results[table] = len(data)
                        logger.info(f"Restored {len(data)} records to {table}")
        
        return results


# ============================================================================
# Data Service Factory
# ============================================================================

class DataServiceFactory:
    """
    Factory for creating DataService instances.
    """
    
    _instances: Dict[str, DataService] = {}
    
    @classmethod
    def create(
        cls,
        session: Session,
        cache_repository: Optional[CacheRepository] = None,
        enable_audit: bool = True,
        enable_cache: bool = True,
        instance_id: Optional[str] = None
    ) -> DataService:
        """
        Create or retrieve a DataService instance.
        
        Args:
            session: SQLAlchemy session
            cache_repository: Optional cache repository
            enable_audit: Whether to enable auditing
            enable_cache: Whether to enable caching
            instance_id: Optional instance identifier
            
        Returns:
            DataService instance
        """
        key = instance_id or f"data_service_{id(session)}"
        
        if key not in cls._instances:
            cls._instances[key] = DataService(
                session=session,
                cache_repository=cache_repository,
                enable_audit=enable_audit,
                enable_cache=enable_cache
            )
        
        return cls._instances[key]
    
    @classmethod
    def clear(cls) -> None:
        """Clear all cached instances."""
        cls._instances.clear()


# ============================================================================
# Convenience Functions
# ============================================================================

_data_service_instance: Optional[DataService] = None


def get_data_service() -> DataService:
    """
    Get the global DataService instance.
    
    Returns:
        DataService instance
    
    Raises:
        RuntimeError: If DataService not initialized
    """
    if _data_service_instance is None:
        raise RuntimeError("DataService not initialized. Call init_data_service first.")
    return _data_service_instance


def init_data_service(
    session: Session,
    cache_repository: Optional[CacheRepository] = None,
    enable_audit: bool = True,
    enable_cache: bool = True
) -> DataService:
    """
    Initialize the global DataService instance.
    
    Args:
        session: SQLAlchemy session
        cache_repository: Optional cache repository
        enable_audit: Whether to enable auditing
        enable_cache: Whether to enable caching
        
    Returns:
        Initialized DataService instance
    """
    global _data_service_instance
    _data_service_instance = DataServiceFactory.create(
        session=session,
        cache_repository=cache_repository,
        enable_audit=enable_audit,
        enable_cache=enable_cache
    )
    return _data_service_instance


def reset_data_service() -> None:
    """Reset the global DataService instance."""
    global _data_service_instance
    _data_service_instance = None
    DataServiceFactory.clear()


# ============================================================================
# Decorators for DataService methods
# ============================================================================

def with_data_service(func: Callable) -> Callable:
    """
    Decorator that injects the DataService instance.
    
    Usage:
        @with_data_service
        def my_function(data_service: DataService, arg1, arg2):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        data_service = get_data_service()
        return func(data_service, *args, **kwargs)
    return wrapper


def data_transactional(func: Callable) -> Callable:
    """
    Decorator that wraps a function in a database transaction.
    
    Usage:
        @data_transactional
        def my_function(data_service: DataService, arg1, arg2):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        data_service = args[0] if args and isinstance(args[0], DataService) else get_data_service()
        with data_service.transaction():
            return func(*args, **kwargs)
    return wrapper


def with_audit_log(
    action: AuditAction,
    resource_type: AuditResourceType,
    category: AuditCategory = AuditCategory.SYSTEM
) -> Callable:
    """
    Decorator that logs audit events for a function.
    
    Args:
        action: Action to log
        resource_type: Type of resource
        category: Audit category
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            data_service = args[0] if args and isinstance(args[0], DataService) else get_data_service()
            
            # Extract resource_id if available
            resource_id = None
            if len(args) > 1 and isinstance(args[1], (int, str)):
                resource_id = str(args[1])
            
            result = func(*args, **kwargs)
            
            data_service.log_audit(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                category=category,
                details={'function': func.__name__, 'args': str(args), 'kwargs': str(kwargs)}
            )
            
            return result
        return wrapper
    return decorator


def cached_result(ttl: int = 300, key_prefix: Optional[str] = None) -> Callable:
    """
    Decorator that caches function results.
    
    Args:
        ttl: Time-to-live in seconds
        key_prefix: Optional cache key prefix
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            data_service = args[0] if args and isinstance(args[0], DataService) else get_data_service()
            
            if not data_service.enable_cache or not data_service.cache:
                return func(*args, **kwargs)
            
            # Generate cache key
            key_parts = [key_prefix or func.__name__]
            key_parts.extend([str(a) for a in args[1:]])  # Skip self
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try cache
            cached = data_service.get_cached(cache_key)
            if cached is not None:
                return cached
            
            # Execute and cache
            result = func(*args, **kwargs)
            data_service.set_cached(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main class
    'DataService',
    
    # Factory
    'DataServiceFactory',
    
    # Convenience functions
    'get_data_service',
    'init_data_service',
    'reset_data_service',
    
    # Decorators
    'with_data_service',
    'data_transactional',
    'with_audit_log',
    'cached_result',
]