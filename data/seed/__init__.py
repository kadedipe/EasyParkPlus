# parking-management/data/seed/__init__.py
"""
Seed data module for the parking management system.

This module provides comprehensive seed data generation and management
capabilities for development, testing, and demonstration environments.
It includes predefined datasets, factories, and utilities for creating
realistic test data with proper relationships.

Usage:
    from data.seed import (
        SeedManager, SeedFactory, SeedLoader,
        DevelopmentSeed, TestSeed, DemoSeed,
        seed_database, reset_database
    )
"""

from typing import (
    List, Optional, Dict, Any, Tuple, Union, Callable, TypeVar, Generic
)
from datetime import datetime, date, timedelta
import logging
import json
from pathlib import Path
import importlib
import pkgutil

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Seed Constants and Configuration
# ============================================================================

DEFAULT_SEED_SIZE = 'small'  # small, medium, large, custom
DEFAULT_ENVIRONMENT = 'development'  # development, test, staging, production

# Seed data paths
SEED_DATA_DIR = Path(__file__).parent / 'data'
SEED_FIXTURES_DIR = SEED_DATA_DIR / 'fixtures'
SEED_FACTORIES_DIR = SEED_DATA_DIR / 'factories'
SEED_TEMPLATES_DIR = SEED_DATA_DIR / 'templates'


# ============================================================================
# Seed Manager
# ============================================================================

class SeedManager:
    """
    Central manager for all seed data operations.
    
    Coordinates seed data loading, factory usage, and database seeding
    across different environments and seed sizes.
    """
    
    def __init__(self, session=None, environment: str = DEFAULT_ENVIRONMENT):
        """
        Initialize the seed manager.
        
        Args:
            session: SQLAlchemy session (optional)
            environment: Target environment
        """
        self.session = session
        self.environment = environment
        self.loaders = {}
        self.factories = {}
        self.fixtures = {}
        self._initialized = False
        
        logger.info(f"SeedManager initialized for {environment} environment")
    
    def initialize(self) -> None:
        """Initialize seed components."""
        if self._initialized:
            return
        
        # Discover and register seed components
        self._discover_loaders()
        self._discover_factories()
        self._discover_fixtures()
        
        self._initialized = True
        logger.info(f"SeedManager initialized with {len(self.loaders)} loaders, "
                   f"{len(self.factories)} factories, {len(self.fixtures)} fixtures")
    
    def _discover_loaders(self) -> None:
        """Discover and register seed loaders."""
        loaders_module = 'data.seed.loaders'
        try:
            loader_module = importlib.import_module(loaders_module)
            for _, name, _ in pkgutil.iter_modules(loader_module.__path__):
                if name.endswith('_loader'):
                    module = importlib.import_module(f"{loaders_module}.{name}")
                    if hasattr(module, 'Loader'):
                        loader_class = getattr(module, 'Loader')
                        loader = loader_class(self.session)
                        self.loaders[loader.table_name] = loader
                        logger.debug(f"Registered loader: {loader.table_name}")
        except ImportError as e:
            logger.warning(f"Could not discover loaders: {e}")
    
    def _discover_factories(self) -> None:
        """Discover and register seed factories."""
        factories_module = 'data.seed.factories'
        try:
            factory_module = importlib.import_module(factories_module)
            for _, name, _ in pkgutil.iter_modules(factory_module.__path__):
                if name.endswith('_factory'):
                    module = importlib.import_module(f"{factories_module}.{name}")
                    if hasattr(module, 'Factory'):
                        factory_class = getattr(module, 'Factory')
                        factory = factory_class()
                        self.factories[factory.model_name] = factory
                        logger.debug(f"Registered factory: {factory.model_name}")
        except ImportError as e:
            logger.warning(f"Could not discover factories: {e}")
    
    def _discover_fixtures(self) -> None:
        """Discover and register seed fixtures."""
        if SEED_FIXTURES_DIR.exists():
            for fixture_file in SEED_FIXTURES_DIR.glob('*.json'):
                fixture_name = fixture_file.stem
                try:
                    with open(fixture_file, 'r') as f:
                        self.fixtures[fixture_name] = json.load(f)
                    logger.debug(f"Loaded fixture: {fixture_name}")
                except Exception as e:
                    logger.error(f"Failed to load fixture {fixture_name}: {e}")
    
    # ========================================================================
    # Seed Execution Methods
    # ========================================================================
    
    def seed_all(
        self,
        size: str = DEFAULT_SEED_SIZE,
        environment: Optional[str] = None,
        **kwargs
    ) -> Dict[str, int]:
        """
        Seed all data with specified size and environment.
        
        Args:
            size: Seed size (small, medium, large, custom)
            environment: Target environment (overrides instance)
            **kwargs: Additional seed parameters
            
        Returns:
            Dictionary with seed counts per table
        """
        self.initialize()
        
        env = environment or self.environment
        logger.info(f"Seeding all data (size={size}, environment={env})")
        
        # Get appropriate seed class based on environment
        seed_class = self._get_seed_class(env)
        seeder = seed_class(self.session, size=size, **kwargs)
        
        # Execute seed in correct order
        results = {}
        
        # Seed base/reference data first
        results.update(seeder.seed_reference_data())
        
        # Seed core entities
        results.update(seeder.seed_core_data())
        
        # Seed transactional data
        results.update(seeder.seed_transactional_data())
        
        # Seed supporting data
        results.update(seeder.seed_supporting_data())
        
        logger.info(f"Seeding complete: {results}")
        return results
    
    def seed_tables(
        self,
        tables: List[str],
        size: str = DEFAULT_SEED_SIZE,
        **kwargs
    ) -> Dict[str, int]:
        """
        Seed specific tables.
        
        Args:
            tables: List of table names to seed
            size: Seed size
            **kwargs: Additional seed parameters
            
        Returns:
            Dictionary with seed counts per table
        """
        self.initialize()
        
        results = {}
        for table in tables:
            if table in self.loaders:
                loader = self.loaders[table]
                count = loader.load(size=size, **kwargs)
                results[table] = count
                logger.info(f"Seeded {table}: {count} rows")
            else:
                logger.warning(f"No loader found for table: {table}")
        
        return results
    
    def seed_with_factory(
        self,
        model_name: str,
        count: int = 1,
        **overrides
    ) -> List[Any]:
        """
        Seed using a factory.
        
        Args:
            model_name: Name of the model to create
            count: Number of instances to create
            **overrides: Field overrides
            
        Returns:
            List of created model instances
        """
        self.initialize()
        
        if model_name not in self.factories:
            raise ValueError(f"No factory found for model: {model_name}")
        
        factory = self.factories[model_name]
        instances = factory.create_batch(count, **overrides)
        
        logger.info(f"Created {count} {model_name} instances using factory")
        return instances
    
    def load_fixture(
        self,
        fixture_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Load a predefined fixture.
        
        Args:
            fixture_name: Name of the fixture
            **kwargs: Additional parameters
            
        Returns:
            Loaded fixture data
        """
        self.initialize()
        
        if fixture_name not in self.fixtures:
            raise ValueError(f"Fixture not found: {fixture_name}")
        
        fixture_data = self.fixtures[fixture_name]
        
        # Process fixture data (resolve references, etc.)
        processed = self._process_fixture(fixture_data, **kwargs)
        
        logger.info(f"Loaded fixture: {fixture_name}")
        return processed
    
    def _process_fixture(
        self,
        data: Any,
        **kwargs
    ) -> Any:
        """Process fixture data (resolve references, etc.)."""
        if isinstance(data, dict):
            return {k: self._process_fixture(v, **kwargs) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._process_fixture(item, **kwargs) for item in data]
        elif isinstance(data, str) and data.startswith('$ref:'):
            # Handle references like $ref:users.1.email
            ref_path = data[5:].split('.')
            # This would need to resolve against loaded data
            return data
        else:
            return data
    
    def _get_seed_class(self, environment: str):
        """Get seed class for environment."""
        from .development import DevelopmentSeed
        from .test import TestSeed
        from .demo import DemoSeed
        
        seed_classes = {
            'development': DevelopmentSeed,
            'test': TestSeed,
            'staging': DemoSeed,
            'demo': DemoSeed
        }
        
        return seed_classes.get(environment, DevelopmentSeed)
    
    # ========================================================================
    # Reset Methods
    # ========================================================================
    
    def reset_database(self, confirm: bool = False) -> bool:
        """
        Reset database by truncating all tables.
        
        Args:
            confirm: Require confirmation
            
        Returns:
            True if reset successful
        """
        if not self.session:
            logger.error("No database session available")
            return False
        
        if confirm:
            response = input("This will delete ALL data. Are you sure? [y/N]: ")
            if response.lower() != 'y':
                logger.info("Reset cancelled")
                return False
        
        logger.warning("Resetting database - all data will be deleted")
        
        # Disable foreign key checks
        db_type = self._get_db_type()
        self._disable_foreign_keys(db_type)
        
        # Get all tables
        from sqlalchemy import inspect
        inspector = inspect(self.session.bind)
        tables = inspector.get_table_names()
        
        # Truncate in reverse order
        for table in reversed(tables):
            self.session.execute(f"TRUNCATE TABLE {table} CASCADE")
            logger.debug(f"Truncated table: {table}")
        
        # Re-enable foreign keys
        self._enable_foreign_keys(db_type)
        
        self.session.commit()
        logger.info("Database reset complete")
        return True
    
    def _get_db_type(self) -> str:
        """Get database type from connection."""
        url = str(self.session.bind.url)
        if 'postgresql' in url:
            return 'postgresql'
        elif 'mysql' in url:
            return 'mysql'
        elif 'sqlite' in url:
            return 'sqlite'
        return 'unknown'
    
    def _disable_foreign_keys(self, db_type: str) -> None:
        """Disable foreign key checks."""
        if db_type == 'postgresql':
            self.session.execute("SET session_replication_role = 'replica'")
        elif db_type == 'mysql':
            self.session.execute("SET FOREIGN_KEY_CHECKS = 0")
        elif db_type == 'sqlite':
            self.session.execute("PRAGMA foreign_keys = OFF")
    
    def _enable_foreign_keys(self, db_type: str) -> None:
        """Re-enable foreign key checks."""
        if db_type == 'postgresql':
            self.session.execute("SET session_replication_role = 'origin'")
        elif db_type == 'mysql':
            self.session.execute("SET FOREIGN_KEY_CHECKS = 1")
        elif db_type == 'sqlite':
            self.session.execute("PRAGMA foreign_keys = ON")


# ============================================================================
# Seed Factory Base Classes
# ============================================================================

class SeedFactory:
    """
    Base class for all seed factories.
    
    Provides common functionality for generating model instances
    with realistic test data.
    """
    
    model = None
    model_name = None
    
    def __init__(self, session=None):
        self.session = session
    
    def create(self, **overrides) -> Any:
        """
        Create a single model instance.
        
        Args:
            **overrides: Field overrides
            
        Returns:
            Created model instance
        """
        data = self.definition()
        data.update(overrides)
        
        instance = self.model(**data)
        
        if self.session:
            self.session.add(instance)
            self.session.flush()
        
        return instance
    
    def create_batch(self, count: int, **overrides) -> List[Any]:
        """
        Create multiple model instances.
        
        Args:
            count: Number of instances to create
            **overrides: Field overrides
            
        Returns:
            List of created instances
        """
        return [self.create(**overrides) for _ in range(count)]
    
    def definition(self) -> Dict[str, Any]:
        """
        Define the default data for the model.
        
        Returns:
            Dictionary of field values
        """
        raise NotImplementedError("Subclasses must implement definition()")
    
    def sequence(self, field: str, start: int = 1) -> Callable:
        """
        Create a sequence generator for a field.
        
        Args:
            field: Field name
            start: Starting value
            
        Returns:
            Function that generates sequential values
        """
        counter = start - 1
        
        def generator():
            nonlocal counter
            counter += 1
            return counter
        
        return generator


# ============================================================================
# Seed Loader Base Classes
# ============================================================================

class SeedLoader:
    """
    Base class for all seed loaders.
    
    Handles loading seed data from various sources (JSON, YAML, etc.)
    into the database.
    """
    
    table_name = None
    model = None
    
    def __init__(self, session=None):
        self.session = session
    
    def load(self, source: Optional[Union[str, Path, List[Dict]]] = None,
             size: str = 'small', **kwargs) -> int:
        """
        Load seed data.
        
        Args:
            source: Data source (file path, URL, or data list)
            size: Seed size
            **kwargs: Additional parameters
            
        Returns:
            Number of records loaded
        """
        # Get data
        if source is None:
            data = self.get_default_data(size)
        elif isinstance(source, (str, Path)):
            data = self.load_from_file(source)
        else:
            data = source
        
        # Process data
        processed_data = self.process_data(data, **kwargs)
        
        # Insert data
        count = self.insert_data(processed_data)
        
        return count
    
    def get_default_data(self, size: str) -> List[Dict[str, Any]]:
        """
        Get default seed data for this table.
        
        Args:
            size: Seed size
            
        Returns:
            List of data dictionaries
        """
        # Try to load from JSON file
        json_file = SEED_DATA_DIR / f"{self.table_name}.json"
        if json_file.exists():
            return self.load_from_file(json_file)
        
        # Fall back to empty list
        return []
    
    def load_from_file(self, file_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Load data from file.
        
        Args:
            file_path: Path to data file
            
        Returns:
            List of data dictionaries
        """
        path = Path(file_path)
        
        if path.suffix == '.json':
            with open(path, 'r') as f:
                return json.load(f)
        elif path.suffix in ('.yaml', '.yml'):
            try:
                import yaml
                with open(path, 'r') as f:
                    return yaml.safe_load(f)
            except ImportError:
                logger.error("PyYAML not installed, cannot load YAML file")
                return []
        else:
            logger.error(f"Unsupported file format: {path.suffix}")
            return []
    
    def process_data(self, data: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        Process data before insertion.
        
        Args:
            data: Raw data
            **kwargs: Processing parameters
            
        Returns:
            Processed data
        """
        # Handle size scaling
        size_factor = kwargs.get('size_factor', 1)
        if size_factor > 1 and len(data) > 0:
            # Duplicate data for larger size
            original = data.copy()
            while len(data) < size_factor * len(original):
                data.extend(original)
        
        # Handle date/datetime conversions
        for row in data:
            for key, value in row.items():
                if isinstance(value, str):
                    if value.endswith('Z') and 'T' in value:
                        try:
                            row[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except ValueError:
                            pass
                    elif '-' in value and ':' in value:
                        try:
                            row[key] = datetime.fromisoformat(value)
                        except ValueError:
                            pass
                    elif '-' in value and len(value) == 10:
                        try:
                            row[key] = date.fromisoformat(value)
                        except ValueError:
                            pass
        
        return data
    
    def insert_data(self, data: List[Dict[str, Any]]) -> int:
        """
        Insert data into database.
        
        Args:
            data: Processed data
            
        Returns:
            Number of records inserted
        """
        if not self.session or not self.model:
            logger.warning("No session or model, skipping insert")
            return 0
        
        count = 0
        for row in data:
            instance = self.model(**row)
            self.session.add(instance)
            count += 1
        
        self.session.flush()
        logger.debug(f"Inserted {count} records into {self.table_name}")
        return count


# ============================================================================
# Environment-Specific Seed Classes
# ============================================================================

class BaseSeed:
    """Base class for environment-specific seeders."""
    
    def __init__(self, session=None, size: str = 'small', **kwargs):
        self.session = session
        self.size = size
        self.kwargs = kwargs
        self.size_multipliers = {
            'small': 1,
            'medium': 5,
            'large': 25,
            'xlarge': 100
        }
    
    def get_size_multiplier(self) -> int:
        """Get size multiplier for current size."""
        return self.size_multipliers.get(self.size, 1)
    
    def seed_reference_data(self) -> Dict[str, int]:
        """Seed reference/lookup data."""
        return {}
    
    def seed_core_data(self) -> Dict[str, int]:
        """Seed core entity data."""
        return {}
    
    def seed_transactional_data(self) -> Dict[str, int]:
        """Seed transactional data."""
        return {}
    
    def seed_supporting_data(self) -> Dict[str, int]:
        """Seed supporting data."""
        return {}


class DevelopmentSeed(BaseSeed):
    """Development environment seed data."""
    
    def seed_reference_data(self) -> Dict[str, int]:
        """Seed reference data for development."""
        from .loaders.role_loader import RoleLoader
        from .loaders.permission_loader import PermissionLoader
        
        results = {}
        
        # Seed roles
        role_loader = RoleLoader(self.session)
        results['roles'] = role_loader.load(size=self.size)
        
        # Seed permissions
        perm_loader = PermissionLoader(self.session)
        results['permissions'] = perm_loader.load(size=self.size)
        
        return results
    
    def seed_core_data(self) -> Dict[str, int]:
        """Seed core data for development."""
        from .loaders.user_loader import UserLoader
        from .loaders.zone_loader import ZoneLoader
        from .loaders.spot_loader import SpotLoader
        
        results = {}
        
        # Seed users
        user_loader = UserLoader(self.session)
        results['users'] = user_loader.load(
            size=self.size,
            count=100 * self.get_size_multiplier()
        )
        
        # Seed parking zones
        zone_loader = ZoneLoader(self.session)
        results['zones'] = zone_loader.load(size=self.size)
        
        # Seed parking spots
        spot_loader = SpotLoader(self.session)
        results['spots'] = spot_loader.load(size=self.size)
        
        return results
    
    def seed_transactional_data(self) -> Dict[str, int]:
        """Seed transactional data for development."""
        from .loaders.vehicle_loader import VehicleLoader
        from .loaders.reservation_loader import ReservationLoader
        from .loaders.payment_loader import PaymentLoader
        
        results = {}
        
        # Seed vehicles
        vehicle_loader = VehicleLoader(self.session)
        results['vehicles'] = vehicle_loader.load(
            size=self.size,
            vehicles_per_user=(1, 3)
        )
        
        # Seed reservations
        reservation_loader = ReservationLoader(self.session)
        results['reservations'] = reservation_loader.load(
            size=self.size,
            reservations_per_user=(5, 20),
            history_days=180,
            future_days=90
        )
        
        # Seed payments
        payment_loader = PaymentLoader(self.session)
        results['payments'] = payment_loader.load(size=self.size)
        
        return results
    
    def seed_supporting_data(self) -> Dict[str, int]:
        """Seed supporting data for development."""
        from .loaders.notification_loader import NotificationLoader
        from .loaders.audit_loader import AuditLoader
        
        results = {}
        
        # Seed notifications
        notification_loader = NotificationLoader(self.session)
        results['notifications'] = notification_loader.load(
            size=self.size,
            notifications_per_user=10
        )
        
        # Seed audit logs
        audit_loader = AuditLoader(self.session)
        results['audit_logs'] = audit_loader.load(
            size=self.size,
            logs_per_user=20
        )
        
        return results


class TestSeed(BaseSeed):
    """Test environment seed data."""
    
    def seed_reference_data(self) -> Dict[str, int]:
        """Seed minimal reference data for testing."""
        from .loaders.role_loader import RoleLoader
        from .loaders.permission_loader import PermissionLoader
        
        results = {}
        
        # Seed essential roles only
        role_loader = RoleLoader(self.session)
        results['roles'] = role_loader.load(minimal=True)
        
        # Seed essential permissions
        perm_loader = PermissionLoader(self.session)
        results['permissions'] = perm_loader.load(minimal=True)
        
        return results
    
    def seed_core_data(self) -> Dict[str, int]:
        """Seed minimal core data for testing."""
        from .loaders.user_loader import UserLoader
        from .loaders.zone_loader import ZoneLoader
        from .loaders.spot_loader import SpotLoader
        
        results = {}
        
        # Seed test users
        user_loader = UserLoader(self.session)
        results['users'] = user_loader.load(
            count=10,
            include_test_users=True
        )
        
        # Seed test zones
        zone_loader = ZoneLoader(self.session)
        results['zones'] = zone_loader.load(minimal=True)
        
        # Seed test spots
        spot_loader = SpotLoader(self.session)
        results['spots'] = spot_loader.load(
            spots_per_zone=5
        )
        
        return results


class DemoSeed(BaseSeed):
    """Demo environment seed data."""
    
    def seed_reference_data(self) -> Dict[str, int]:
        """Seed comprehensive reference data for demos."""
        from .loaders.role_loader import RoleLoader
        from .loaders.permission_loader import PermissionLoader
        from .loaders.rate_loader import RateLoader
        
        results = {}
        
        # Seed all roles
        role_loader = RoleLoader(self.session)
        results['roles'] = role_loader.load(include_all=True)
        
        # Seed all permissions
        perm_loader = PermissionLoader(self.session)
        results['permissions'] = perm_loader.load(include_all=True)
        
        # Seed rate configurations
        rate_loader = RateLoader(self.session)
        results['rates'] = rate_loader.load(include_promotions=True)
        
        return results
    
    def seed_core_data(self) -> Dict[str, int]:
        """Seed impressive core data for demos."""
        from .loaders.user_loader import UserLoader
        from .loaders.zone_loader import ZoneLoader
        from .loaders.spot_loader import SpotLoader
        
        results = {}
        
        # Seed diverse users
        user_loader = UserLoader(self.session)
        results['users'] = user_loader.load(
            count=50,
            include_demo_users=True,
            include_vip_users=True
        )
        
        # Seed multiple zones
        zone_loader = ZoneLoader(self.session)
        results['zones'] = zone_loader.load(
            include_all_types=True,
            include_premium_zones=True
        )
        
        # Seed various spot types
        spot_loader = SpotLoader(self.session)
        results['spots'] = spot_loader.load(
            include_handicapped=True,
            include_ev=True,
            include_vip=True,
            include_motorcycle=True
        )
        
        return results


# ============================================================================
# Convenience Functions
# ============================================================================

_seed_manager_instance: Optional[SeedManager] = None


def get_seed_manager(session=None, environment: str = DEFAULT_ENVIRONMENT) -> SeedManager:
    """
    Get the global SeedManager instance.
    
    Args:
        session: SQLAlchemy session
        environment: Target environment
        
    Returns:
        SeedManager instance
    """
    global _seed_manager_instance
    if _seed_manager_instance is None:
        _seed_manager_instance = SeedManager(session, environment)
        _seed_manager_instance.initialize()
    return _seed_manager_instance


def seed_database(
    session,
    size: str = DEFAULT_SEED_SIZE,
    environment: str = DEFAULT_ENVIRONMENT,
    **kwargs
) -> Dict[str, int]:
    """
    Convenience function to seed the database.
    
    Args:
        session: SQLAlchemy session
        size: Seed size
        environment: Target environment
        **kwargs: Additional seed parameters
        
    Returns:
        Dictionary with seed counts
    """
    manager = get_seed_manager(session, environment)
    return manager.seed_all(size=size, environment=environment, **kwargs)


def reset_database(session, confirm: bool = False) -> bool:
    """
    Convenience function to reset the database.
    
    Args:
        session: SQLAlchemy session
        confirm: Require confirmation
        
    Returns:
        True if reset successful
    """
    manager = get_seed_manager(session)
    return manager.reset_database(confirm)


def load_fixture(fixture_name: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to load a fixture.
    
    Args:
        fixture_name: Name of the fixture
        **kwargs: Additional parameters
        
    Returns:
        Loaded fixture data
    """
    manager = get_seed_manager()
    return manager.load_fixture(fixture_name, **kwargs)


def create_factory(model_name: str, session=None) -> SeedFactory:
    """
    Get a factory for a model.
    
    Args:
        model_name: Name of the model
        session: SQLAlchemy session
        
    Returns:
        SeedFactory instance
    """
    manager = get_seed_manager(session)
    if model_name not in manager.factories:
        # Try to create factory on the fly
        factory_class = _get_factory_class(model_name)
        if factory_class:
            factory = factory_class(session)
            manager.factories[model_name] = factory
            return factory
        raise ValueError(f"No factory found for model: {model_name}")
    return manager.factories[model_name]


def _get_factory_class(model_name: str):
    """Get factory class for model name."""
    try:
        module = importlib.import_module(f"data.seed.factories.{model_name}_factory")
        if hasattr(module, 'Factory'):
            return getattr(module, 'Factory')
    except (ImportError, AttributeError):
        pass
    return None


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main classes
    'SeedManager',
    'SeedFactory',
    'SeedLoader',
    
    # Environment-specific seeders
    'BaseSeed',
    'DevelopmentSeed',
    'TestSeed',
    'DemoSeed',
    
    # Convenience functions
    'get_seed_manager',
    'seed_database',
    'reset_database',
    'load_fixture',
    'create_factory',
    
    # Constants
    'DEFAULT_SEED_SIZE',
    'DEFAULT_ENVIRONMENT',
    'SEED_DATA_DIR',
    'SEED_FIXTURES_DIR',
    'SEED_FACTORIES_DIR',
    'SEED_TEMPLATES_DIR',
]

# Version information
__version__ = '1.0.0'
__seed_version__ = '1.0.0'