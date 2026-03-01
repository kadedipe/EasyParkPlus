"""Services package initialization for the parking management system.

This module exports all service classes and provides utility functions
for service management, dependency injection, and service registry.
"""

from typing import Dict, Type, Any, Optional, List, Union, Callable
from functools import wraps
import inspect
import logging

# Import all services
from .auth_service import AuthService
from .user_service import UserService
from .vehicle_service import VehicleService
from .parking_spot_service import ParkingSpotService
from .reservation_service import ReservationService
from .payment_service import PaymentService
from .notification_service import NotificationService
from .waitlist_service import WaitlistService
from .reporting_service import ReportingService
from .analytics_service import AnalyticsService
from .admin_service import AdminService
from .webhook_service import WebhookService
from .email_service import EmailService
from .sms_service import SMSService
from .push_notification_service import PushNotificationService
from .cache_service import CacheService
from .queue_service import QueueService
from .search_service import SearchService
from .validation_service import ValidationService
from .audit_service import AuditService
from .maintenance_service import MaintenanceService
from .price_calculation_service import PriceCalculationService
from .discount_service import DiscountService
from .loyalty_service import LoyaltyService
from .integration_service import IntegrationService
from .export_service import ExportService
from .import_service import ImportService
from .backup_service import BackupService
from .monitoring_service import MonitoringService
from .alert_service import AlertService
from .config_service import ConfigService
from .feature_flag_service import FeatureFlagService

# Configure logging
logger = logging.getLogger(__name__)


# Service registry for dependency injection
class ServiceRegistry:
    """Registry for managing service instances and dependencies."""
    
    _instance = None
    _services: Dict[str, Any] = {}
    _factories: Dict[str, Callable] = {}
    _singletons: Dict[str, Any] = {}
    
    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, name: str, service: Any, singleton: bool = True) -> None:
        """Register a service instance.
        
        Args:
            name: Service name
            service: Service instance or class
            singleton: Whether to treat as singleton
        """
        if singleton:
            cls._singletons[name] = service
        else:
            cls._services[name] = service
        logger.debug(f"Registered service: {name}")
    
    @classmethod
    def register_factory(cls, name: str, factory: Callable) -> None:
        """Register a factory function for creating services.
        
        Args:
            name: Service name
            factory: Factory function that returns service instance
        """
        cls._factories[name] = factory
        logger.debug(f"Registered factory for: {name}")
    
    @classmethod
    def get(cls, name: str, **kwargs) -> Optional[Any]:
        """Get a service instance by name.
        
        Args:
            name: Service name
            **kwargs: Additional arguments for factory creation
            
        Returns:
            Service instance or None if not found
        """
        # Check singletons first
        if name in cls._singletons:
            return cls._singletons[name]
        
        # Check regular services
        if name in cls._services:
            return cls._services[name]
        
        # Try factory
        if name in cls._factories:
            service = cls._factories[name](**kwargs)
            # Cache as singleton by default
            cls._singletons[name] = service
            return service
        
        logger.warning(f"Service not found: {name}")
        return None
    
    @classmethod
    def has(cls, name: str) -> bool:
        """Check if a service is registered.
        
        Args:
            name: Service name
            
        Returns:
            True if service exists
        """
        return name in cls._singletons or name in cls._services or name in cls._factories
    
    @classmethod
    def remove(cls, name: str) -> None:
        """Remove a service from registry.
        
        Args:
            name: Service name
        """
        cls._singletons.pop(name, None)
        cls._services.pop(name, None)
        cls._factories.pop(name, None)
        logger.debug(f"Removed service: {name}")
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered services."""
        cls._singletons.clear()
        cls._services.clear()
        cls._factories.clear()
        logger.debug("Cleared all services")
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all registered services.
        
        Returns:
            Dictionary of all services
        """
        return {
            **cls._singletons,
            **cls._services,
        }
    
    @classmethod
    def get_service_names(cls) -> List[str]:
        """Get list of all registered service names.
        
        Returns:
            List of service names
        """
        return list(cls._singletons.keys()) + list(cls._services.keys()) + list(cls._factories.keys())


# Create global service registry instance
service_registry = ServiceRegistry()


# Dependency injection decorator
def inject(*service_names: str):
    """Decorator for injecting services into functions/methods.
    
    Args:
        *service_names: Names of services to inject
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get services from registry
            for service_name in service_names:
                if service_name not in kwargs:
                    service = service_registry.get(service_name)
                    if service is not None:
                        kwargs[service_name] = service
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Service lifecycle decorator
def service_lifecycle(on_init: Optional[Callable] = None, on_destroy: Optional[Callable] = None):
    """Decorator for managing service lifecycle.
    
    Args:
        on_init: Function to call on initialization
        on_destroy: Function to call on destruction
        
    Returns:
        Decorated class
    """
    def decorator(cls):
        original_init = cls.__init__
        
        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            if on_init:
                on_init(self)
        
        cls.__init__ = new_init
        
        # Add destroy method if not exists
        if not hasattr(cls, 'destroy') and on_destroy:
            def destroy(self):
                on_destroy(self)
            cls.destroy = destroy
        
        return cls
    return decorator


# Service base class
class BaseService:
    """Base class for all services with common functionality."""
    
    def __init__(self, service_name: Optional[str] = None):
        """Initialize base service.
        
        Args:
            service_name: Name of the service (defaults to class name)
        """
        self.service_name = service_name or self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.service_name}")
        self._initialized = False
        self._dependencies: List[str] = []
    
    def initialize(self) -> None:
        """Initialize the service."""
        if not self._initialized:
            self.logger.info(f"Initializing service: {self.service_name}")
            self._initialized = True
    
    def destroy(self) -> None:
        """Clean up service resources."""
        if self._initialized:
            self.logger.info(f"Destroying service: {self.service_name}")
            self._initialized = False
    
    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized
    
    def add_dependency(self, service_name: str) -> None:
        """Add a service dependency.
        
        Args:
            service_name: Name of dependent service
        """
        if service_name not in self._dependencies:
            self._dependencies.append(service_name)
    
    def get_dependencies(self) -> List[str]:
        """Get list of service dependencies.
        
        Returns:
            List of dependency names
        """
        return self._dependencies.copy()
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the service.
        
        Returns:
            Health check results
        """
        return {
            'service': self.service_name,
            'initialized': self._initialized,
            'status': 'healthy' if self._initialized else 'unhealthy',
        }


# Service factory functions
def create_auth_service(db_session=None, cache_client=None, **kwargs) -> AuthService:
    """Create an authentication service instance.
    
    Args:
        db_session: Database session
        cache_client: Cache client
        **kwargs: Additional arguments
        
    Returns:
        AuthService instance
    """
    return AuthService(db_session=db_session, cache_client=cache_client, **kwargs)


def create_user_service(db_session=None, cache_client=None, **kwargs) -> UserService:
    """Create a user service instance.
    
    Args:
        db_session: Database session
        cache_client: Cache client
        **kwargs: Additional arguments
        
    Returns:
        UserService instance
    """
    return UserService(db_session=db_session, cache_client=cache_client, **kwargs)


def create_reservation_service(db_session=None, cache_client=None, **kwargs) -> ReservationService:
    """Create a reservation service instance.
    
    Args:
        db_session: Database session
        cache_client: Cache client
        **kwargs: Additional arguments
        
    Returns:
        ReservationService instance
    """
    return ReservationService(db_session=db_session, cache_client=cache_client, **kwargs)


def create_payment_service(
    db_session=None,
    cache_client=None,
    stripe_api_key=None,
    **kwargs
) -> PaymentService:
    """Create a payment service instance.
    
    Args:
        db_session: Database session
        cache_client: Cache client
        stripe_api_key: Stripe API key
        **kwargs: Additional arguments
        
    Returns:
        PaymentService instance
    """
    return PaymentService(
        db_session=db_session,
        cache_client=cache_client,
        stripe_api_key=stripe_api_key,
        **kwargs
    )


def create_notification_service(
    db_session=None,
    email_service=None,
    sms_service=None,
    push_service=None,
    **kwargs
) -> NotificationService:
    """Create a notification service instance.
    
    Args:
        db_session: Database session
        email_service: Email service instance
        sms_service: SMS service instance
        push_service: Push notification service
        **kwargs: Additional arguments
        
    Returns:
        NotificationService instance
    """
    return NotificationService(
        db_session=db_session,
        email_service=email_service,
        sms_service=sms_service,
        push_service=push_service,
        **kwargs
    )


# Register factory functions
service_registry.register_factory('auth_service', create_auth_service)
service_registry.register_factory('user_service', create_user_service)
service_registry.register_factory('reservation_service', create_reservation_service)
service_registry.register_factory('payment_service', create_payment_service)
service_registry.register_factory('notification_service', create_notification_service)


# Service initialization function
def initialize_services(config: Optional[Dict[str, Any]] = None) -> None:
    """Initialize all registered services.
    
    Args:
        config: Configuration dictionary
    """
    logger.info("Initializing services...")
    
    # Initialize core services first
    core_services = ['config_service', 'cache_service', 'db_service']
    
    for service_name in core_services:
        service = service_registry.get(service_name)
        if service and hasattr(service, 'initialize'):
            service.initialize()
    
    # Initialize remaining services
    for service_name in service_registry.get_service_names():
        if service_name not in core_services:
            service = service_registry.get(service_name)
            if service and hasattr(service, 'initialize'):
                service.initialize()
    
    logger.info("All services initialized")


# Service cleanup function
def cleanup_services() -> None:
    """Clean up all services."""
    logger.info("Cleaning up services...")
    
    # Clean up in reverse order
    for service_name in reversed(service_registry.get_service_names()):
        service = service_registry.get(service_name)
        if service and hasattr(service, 'destroy'):
            try:
                service.destroy()
            except Exception as e:
                logger.error(f"Error destroying service {service_name}: {e}")
    
    logger.info("All services cleaned up")


# Service dependency resolver
def resolve_dependencies(service_name: str, visited: Optional[set] = None) -> List[str]:
    """Resolve service dependencies in order.
    
    Args:
        service_name: Name of the service
        visited: Set of visited services (for cycle detection)
        
    Returns:
        List of service names in dependency order
        
    Raises:
        ValueError: If circular dependency detected
    """
    if visited is None:
        visited = set()
    
    if service_name in visited:
        raise ValueError(f"Circular dependency detected: {service_name}")
    
    visited.add(service_name)
    
    service = service_registry.get(service_name)
    dependencies = []
    
    if service and hasattr(service, 'get_dependencies'):
        for dep in service.get_dependencies():
            deps = resolve_dependencies(dep, visited.copy())
            dependencies.extend(deps)
    
    dependencies.append(service_name)
    
    # Remove duplicates while preserving order
    seen = set()
    return [x for x in dependencies if not (x in seen or seen.add(x))]


# Service health check
def check_services_health() -> Dict[str, Any]:
    """Perform health check on all services.
    
    Returns:
        Health check results
    """
    results = {}
    all_healthy = True
    
    for service_name in service_registry.get_service_names():
        service = service_registry.get(service_name)
        if service and hasattr(service, 'health_check'):
            try:
                health = service.health_check()
                results[service_name] = health
                if health.get('status') != 'healthy':
                    all_healthy = False
            except Exception as e:
                results[service_name] = {
                    'service': service_name,
                    'status': 'error',
                    'error': str(e)
                }
                all_healthy = False
    
    return {
        'overall_status': 'healthy' if all_healthy else 'unhealthy',
        'services': results,
        'timestamp': datetime.utcnow().isoformat(),
    }


# Export all services and utilities
__all__ = [
    # Service classes
    'AuthService',
    'UserService',
    'VehicleService',
    'ParkingSpotService',
    'ReservationService',
    'PaymentService',
    'NotificationService',
    'WaitlistService',
    'ReportingService',
    'AnalyticsService',
    'AdminService',
    'WebhookService',
    'EmailService',
    'SMSService',
    'PushNotificationService',
    'CacheService',
    'QueueService',
    'SearchService',
    'ValidationService',
    'AuditService',
    'MaintenanceService',
    'PriceCalculationService',
    'DiscountService',
    'LoyaltyService',
    'IntegrationService',
    'ExportService',
    'ImportService',
    'BackupService',
    'MonitoringService',
    'AlertService',
    'ConfigService',
    'FeatureFlagService',
    
    # Base classes
    'BaseService',
    'ServiceRegistry',
    
    # Registry instance
    'service_registry',
    
    # Decorators
    'inject',
    'service_lifecycle',
    
    # Factory functions
    'create_auth_service',
    'create_user_service',
    'create_reservation_service',
    'create_payment_service',
    'create_notification_service',
    
    # Utility functions
    'initialize_services',
    'cleanup_services',
    'resolve_dependencies',
    'check_services_health',
]

# Import datetime for health check
from datetime import datetime