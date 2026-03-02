# parking-management/data/services/migration_service.py
"""
Migration service module for the parking management system.

This module provides comprehensive database migration management including
schema versioning, migration execution, rollback capabilities, data migrations,
and migration history tracking.
"""

from typing import (
    List, Optional, Dict, Any, Tuple, Union, Callable, 
    Iterator, Set, Type
)
from datetime import datetime
import logging
import os
import re
import hashlib
import importlib
import inspect
from pathlib import Path
import threading
import json
from enum import Enum

from sqlalchemy import (
    create_engine, text, MetaData, Table, Column, 
    Integer, String, DateTime, Boolean, inspect
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

from .base_service import BaseService, ServiceException, with_retry
from .backup_service import BackupService
from .notification_service import NotificationService

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class MigrationException(ServiceException):
    """Base exception for migration service."""
    pass


class MigrationNotFoundException(MigrationException):
    """Raised when a migration is not found."""
    pass


class MigrationConflictException(MigrationException):
    """Raised when there's a conflict in migration dependencies."""
    pass


class MigrationFailedException(MigrationException):
    """Raised when a migration fails."""
    pass


class SchemaVersionException(MigrationException):
    """Raised when there's an issue with schema versioning."""
    pass


class DataMigrationException(MigrationException):
    """Raised when a data migration fails."""
    pass


class RollbackException(MigrationException):
    """Raised when rollback fails."""
    pass


# ============================================================================
# Migration Models
# ============================================================================

class MigrationStatus(str, Enum):
    """Migration status constants."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    ROLLED_BACK = 'rolled_back'
    SKIPPED = 'skipped'


class MigrationType(str, Enum):
    """Migration type constants."""
    SCHEMA = 'schema'
    DATA = 'data'
    SEED = 'seed'
    FIX = 'fix'
    ROLLBACK = 'rollback'


class MigrationDirection(str, Enum):
    """Migration direction constants."""
    UP = 'up'
    DOWN = 'down'


class MigrationMetadata:
    """Metadata for a migration."""
    
    def __init__(
        self,
        version: str,
        name: str,
        description: str,
        migration_type: MigrationType,
        dependencies: List[str],
        created_at: datetime,
        applied_at: Optional[datetime] = None,
        duration: Optional[float] = None,
        status: MigrationStatus = MigrationStatus.PENDING,
        checksum: Optional[str] = None,
        author: Optional[str] = None,
        down_revision: Optional[str] = None
    ):
        self.version = version
        self.name = name
        self.description = description
        self.migration_type = migration_type
        self.dependencies = dependencies
        self.created_at = created_at
        self.applied_at = applied_at
        self.duration = duration
        self.status = status
        self.checksum = checksum
        self.author = author
        self.down_revision = down_revision
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'version': self.version,
            'name': self.name,
            'description': self.description,
            'migration_type': self.migration_type.value,
            'dependencies': self.dependencies,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'duration': self.duration,
            'status': self.status.value,
            'checksum': self.checksum,
            'author': self.author,
            'down_revision': self.down_revision
        }


class MigrationJob:
    """Represents a migration job."""
    
    def __init__(
        self,
        target_version: Optional[str] = None,
        migration_type: Optional[MigrationType] = None,
        dry_run: bool = False,
        create_backup: bool = True
    ):
        self.job_id = f"mig_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.target_version = target_version
        self.migration_type = migration_type
        self.dry_run = dry_run
        self.create_backup = create_backup
        self.status = MigrationStatus.PENDING
        self.current_version: Optional[str] = None
        self.migrations: List[MigrationMetadata] = []
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.backup_id: Optional[str] = None


# ============================================================================
# Base Migration Class
# ============================================================================

class BaseMigration:
    """
    Base class for all migrations.
    
    Subclasses should implement up() and down() methods.
    """
    
    # Migration metadata
    version: str = None
    name: str = None
    description: str = ""
    migration_type: MigrationType = MigrationType.SCHEMA
    dependencies: List[str] = []
    author: str = None
    
    def __init__(self, session):
        self.session = session
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def up(self) -> None:
        """Apply the migration."""
        raise NotImplementedError("Subclasses must implement up()")
    
    def down(self) -> None:
        """Rollback the migration."""
        raise NotImplementedError("Subclasses must implement down()")
    
    def pre_up(self) -> None:
        """Hook called before up migration."""
        pass
    
    def post_up(self) -> None:
        """Hook called after up migration."""
        pass
    
    def pre_down(self) -> None:
        """Hook called before down migration."""
        pass
    
    def post_down(self) -> None:
        """Hook called after down migration."""
        pass
    
    def validate(self) -> bool:
        """Validate migration prerequisites."""
        return True
    
    def get_metadata(self) -> MigrationMetadata:
        """Get migration metadata."""
        return MigrationMetadata(
            version=self.version,
            name=self.name or self.__class__.__name__,
            description=self.description,
            migration_type=self.migration_type,
            dependencies=self.dependencies,
            created_at=datetime.utcnow(),  # This should be read from file
            author=self.author,
            checksum=self._calculate_checksum()
        )
    
    def _calculate_checksum(self) -> str:
        """Calculate checksum of migration code."""
        source = inspect.getsource(self.__class__)
        return hashlib.sha256(source.encode()).hexdigest()


# ============================================================================
# Migration Service
# ============================================================================

class MigrationService(BaseService):
    """
    Comprehensive database migration service.
    
    Provides:
    - Schema versioning
    - Migration execution
    - Rollback capabilities
    - Data migrations
    - Seed data loading
    - Migration history tracking
    - Dependency resolution
    - Dry run mode
    - Pre/post migration hooks
    """
    
    def __init__(
        self,
        session,
        migrations_dir: str = "./migrations",
        alembic_ini_path: Optional[str] = None,
        backup_service: Optional[BackupService] = None,
        notification_service: Optional[NotificationService] = None
    ):
        """
        Initialize the migration service.
        
        Args:
            session: SQLAlchemy session
            migrations_dir: Directory containing migration files
            alembic_ini_path: Path to alembic.ini file
            backup_service: Optional backup service
            notification_service: Optional notification service
        """
        super().__init__(session)
        self.migrations_dir = Path(migrations_dir)
        self.alembic_ini_path = alembic_ini_path
        self.backup_service = backup_service
        self.notifications = notification_service
        
        # Ensure migrations directory exists
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize migration tables
        self._init_migration_tables()
        
        # Load migrations
        self.migrations: Dict[str, BaseMigration] = {}
        self._load_migrations()
        
        # Active jobs
        self.active_jobs: Dict[str, MigrationJob] = {}
        self._lock = threading.Lock()
        
        logger.info(f"MigrationService initialized with {len(self.migrations)} migrations")
    
    def _init_migration_tables(self) -> None:
        """Initialize migration tracking tables."""
        metadata = MetaData()
        
        # Create migrations table if not exists
        if not inspect(self.session.bind).has_table('migrations'):
            Table(
                'migrations',
                metadata,
                Column('version', String(50), primary_key=True),
                Column('name', String(255), nullable=False),
                Column('description', String(500)),
                Column('migration_type', String(50), nullable=False),
                Column('checksum', String(64), nullable=False),
                Column('dependencies', String(500)),  # JSON array
                Column('applied_at', DateTime, nullable=False),
                Column('duration', Float),
                Column('status', String(50), nullable=False),
                Column('author', String(100)),
                Column('down_revision', String(50))
            )
            
            metadata.create_all(self.session.bind)
            logger.info("Created migrations table")
    
    def _load_migrations(self) -> None:
        """Load migration classes from migrations directory."""
        # Look for Python files in migrations directory
        for file_path in self.migrations_dir.glob("*.py"):
            if file_path.name.startswith('__'):
                continue
            
            module_name = file_path.stem
            self._load_migration_module(module_name)
    
    def _load_migration_module(self, module_name: str) -> None:
        """Load migration classes from a module."""
        try:
            # Import module
            spec = importlib.util.spec_from_file_location(
                module_name,
                self.migrations_dir / f"{module_name}.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find migration classes
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseMigration) and 
                    obj != BaseMigration):
                    
                    migration = obj(self.session)
                    if migration.version:
                        self.migrations[migration.version] = migration
                        logger.debug(f"Loaded migration {migration.version}: {migration.name}")
                    
        except Exception as e:
            logger.error(f"Failed to load migration module {module_name}: {e}")
    
    # ========================================================================
    # Migration Execution
    # ========================================================================
    
    def migrate(
        self,
        target_version: Optional[str] = None,
        migration_type: Optional[MigrationType] = None,
        dry_run: bool = False,
        create_backup: bool = True
    ) -> MigrationJob:
        """
        Run migrations to target version.
        
        Args:
            target_version: Target migration version (None for latest)
            migration_type: Filter by migration type
            dry_run: Simulate migration without applying
            create_backup: Create backup before migration
            
        Returns:
            Migration job
            
        Raises:
            MigrationException: If migration fails
        """
        # Create backup if requested
        backup_id = None
        if create_backup and not dry_run and self.backup_service:
            backup_job = self.backup_service.create_backup(
                backup_type='full',
                tables=None,
                format='json',
                compression='gzip',
                verify=True
            )
            backup_id = backup_job.job_id
            logger.info(f"Created pre-migration backup: {backup_id}")
        
        # Create job
        job = MigrationJob(
            target_version=target_version,
            migration_type=migration_type,
            dry_run=dry_run,
            create_backup=create_backup
        )
        job.backup_id = backup_id
        
        with self._lock:
            self.active_jobs[job.job_id] = job
        
        try:
            # Get current version
            current_version = self.get_current_version()
            job.current_version = current_version
            
            # Determine migrations to run
            migrations_to_run = self._get_migration_plan(
                current_version,
                target_version,
                migration_type
            )
            
            if not migrations_to_run:
                logger.info("No migrations to run")
                job.status = MigrationStatus.COMPLETED
                return job
            
            job.migrations = migrations_to_run
            job.status = MigrationStatus.RUNNING
            job.started_at = datetime.utcnow()
            
            logger.info(f"Migration plan: {len(migrations_to_run)} migrations to apply")
            
            # Apply migrations in order
            for migration_meta in migrations_to_run:
                migration = self.migrations[migration_meta.version]
                
                logger.info(f"Applying migration {migration.version}: {migration.name}")
                
                if not dry_run:
                    self._apply_migration(migration, job)
                else:
                    logger.info(f"[DRY RUN] Would apply migration {migration.version}")
            
            job.status = MigrationStatus.COMPLETED
            
        except Exception as e:
            job.status = MigrationStatus.FAILED
            job.error = str(e)
            logger.error(f"Migration failed: {e}")
            
            # Attempt rollback if configured
            if not dry_run:
                self._rollback_failed_migration(job)
            
            raise MigrationFailedException(f"Migration failed: {e}")
        
        finally:
            job.completed_at = datetime.utcnow()
            
            with self._lock:
                if job.job_id in self.active_jobs:
                    del self.active_jobs[job.job_id]
        
        return job
    
    def _apply_migration(self, migration: BaseMigration, job: MigrationJob) -> None:
        """Apply a single migration."""
        start_time = datetime.utcnow()
        
        try:
            # Validate
            if not migration.validate():
                raise MigrationException(f"Migration {migration.version} validation failed")
            
            # Pre-up hook
            migration.pre_up()
            
            # Apply migration
            migration.up()
            
            # Post-up hook
            migration.post_up()
            
            # Record migration
            self._record_migration(migration, start_time)
            
            logger.info(f"Applied migration {migration.version}")
            
        except Exception as e:
            logger.error(f"Failed to apply migration {migration.version}: {e}")
            
            # Try to rollback this migration
            try:
                migration.down()
                logger.info(f"Rolled back migration {migration.version}")
            except Exception as rollback_error:
                logger.error(f"Rollback failed for migration {migration.version}: {rollback_error}")
            
            raise
    
    def _record_migration(self, migration: BaseMigration, start_time: datetime) -> None:
        """Record migration in database."""
        duration = (datetime.utcnow() - start_time).total_seconds()
        metadata = migration.get_metadata()
        
        # Insert migration record
        stmt = text("""
            INSERT INTO migrations (
                version, name, description, migration_type, checksum,
                dependencies, applied_at, duration, status, author
            ) VALUES (
                :version, :name, :description, :migration_type, :checksum,
                :dependencies, :applied_at, :duration, :status, :author
            )
        """)
        
        self.session.execute(stmt, {
            'version': metadata.version,
            'name': metadata.name,
            'description': metadata.description,
            'migration_type': metadata.migration_type.value,
            'checksum': metadata.checksum,
            'dependencies': json.dumps(metadata.dependencies),
            'applied_at': datetime.utcnow(),
            'duration': duration,
            'status': MigrationStatus.COMPLETED.value,
            'author': metadata.author
        })
        
        self.session.flush()
    
    def _rollback_failed_migration(self, job: MigrationJob) -> None:
        """Attempt to rollback a failed migration."""
        logger.info("Attempting to rollback failed migration")
        
        # Get applied migrations
        applied = self.get_applied_migrations()
        
        if applied:
            # Rollback the last successful migration
            last_migration = applied[-1]
            migration = self.migrations.get(last_migration.version)
            
            if migration:
                try:
                    migration.down()
                    logger.info(f"Rolled back to {last_migration.version}")
                except Exception as e:
                    logger.error(f"Rollback failed: {e}")
    
    def _get_migration_plan(
        self,
        current_version: Optional[str],
        target_version: Optional[str],
        migration_type: Optional[MigrationType]
    ) -> List[MigrationMetadata]:
        """
        Determine which migrations to run to reach target version.
        
        Args:
            current_version: Current database version
            target_version: Target version (None for latest)
            migration_type: Filter by type
            
        Returns:
            List of migration metadata in order
        """
        # Get all migrations sorted by version
        all_migrations = self._get_sorted_migrations()
        
        if not all_migrations:
            return []
        
        # Find indices
        current_idx = -1
        target_idx = len(all_migrations) - 1  # Default to latest
        
        for i, meta in enumerate(all_migrations):
            if meta.version == current_version:
                current_idx = i
            if meta.version == target_version:
                target_idx = i
        
        if target_version and target_idx == -1:
            raise MigrationNotFoundException(f"Target version {target_version} not found")
        
        # Determine direction
        if target_idx > current_idx:
            # Migrate up
            migrations = all_migrations[current_idx + 1:target_idx + 1]
        elif target_idx < current_idx:
            # Migrate down (rollback)
            migrations = list(reversed(all_migrations[target_idx + 1:current_idx + 1]))
            # Mark as down migrations
            for meta in migrations:
                meta.direction = MigrationDirection.DOWN
        else:
            # Already at target
            return []
        
        # Filter by type
        if migration_type:
            migrations = [m for m in migrations if m.migration_type == migration_type]
        
        # Check dependencies
        self._validate_dependencies(migrations)
        
        return migrations
    
    def _get_sorted_migrations(self) -> List[MigrationMetadata]:
        """Get all migrations sorted by version."""
        migrations = []
        
        for version, migration in self.migrations.items():
            migrations.append(migration.get_metadata())
        
        # Sort by version (assuming semantic versioning)
        migrations.sort(key=lambda m: self._parse_version(m.version))
        
        return migrations
    
    def _parse_version(self, version: str) -> Tuple:
        """Parse version string into comparable tuple."""
        # Handle common version formats
        if '.' in version:
            parts = version.split('.')
            return tuple(int(p) if p.isdigit() else p for p in parts)
        else:
            # Treat as string
            return (version,)
    
    def _validate_dependencies(self, migrations: List[MigrationMetadata]) -> None:
        """Validate migration dependencies."""
        applied_versions = {m.version for m in self.get_applied_migrations()}
        
        for meta in migrations:
            for dep in meta.dependencies:
                if dep not in applied_versions and dep not in [m.version for m in migrations]:
                    raise MigrationConflictException(
                        f"Migration {meta.version} depends on {dep} which is not applied"
                    )
    
    # ========================================================================
    # Rollback Operations
    # ========================================================================
    
    def rollback(self, steps: int = 1) -> MigrationJob:
        """
        Rollback the last N migrations.
        
        Args:
            steps: Number of migrations to rollback
            
        Returns:
            Migration job
        """
        applied = self.get_applied_migrations()
        
        if not applied:
            raise MigrationException("No migrations to rollback")
        
        # Get target version (steps back)
        target_idx = max(0, len(applied) - steps - 1)
        target_version = applied[target_idx].version if target_idx >= 0 else None
        
        return self.migrate(target_version=target_version)
    
    def rollback_to_version(self, version: str) -> MigrationJob:
        """
        Rollback to a specific version.
        
        Args:
            version: Target version to rollback to
            
        Returns:
            Migration job
        """
        return self.migrate(target_version=version)
    
    def rollback_all(self) -> MigrationJob:
        """Rollback all migrations."""
        return self.migrate(target_version=None)  # None means base
    
    # ========================================================================
    # Data Migrations
    # ========================================================================
    
    def run_data_migration(
        self,
        migration_name: str,
        data: Optional[Dict] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Run a specific data migration.
        
        Args:
            migration_name: Name of the data migration
            data: Optional input data
            dry_run: Simulate without applying
            
        Returns:
            Migration results
        """
        # Find migration
        migration = None
        for m in self.migrations.values():
            if m.name == migration_name and m.migration_type == MigrationType.DATA:
                migration = m
                break
        
        if not migration:
            raise MigrationNotFoundException(f"Data migration not found: {migration_name}")
        
        logger.info(f"Running data migration: {migration_name}")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would run data migration {migration_name}")
            return {'status': 'dry_run', 'migration': migration_name}
        
        try:
            start_time = datetime.utcnow()
            
            # Execute migration
            result = migration.up()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Record migration
            self._record_migration(migration, start_time)
            
            return {
                'status': 'completed',
                'migration': migration_name,
                'duration': duration,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Data migration failed: {e}")
            raise DataMigrationException(f"Data migration failed: {e}")
    
    # ========================================================================
    # Seed Data
    # ========================================================================
    
    def seed_data(
        self,
        seed_name: str,
        data: Optional[Dict] = None,
        truncate: bool = False
    ) -> Dict[str, Any]:
        """
        Load seed data.
        
        Args:
            seed_name: Name of the seed data
            data: Optional seed data (if not loading from file)
            truncate: Whether to truncate tables before seeding
            
        Returns:
            Seed results
        """
        # Find seed migration
        seed_migration = None
        for m in self.migrations.values():
            if m.name == seed_name and m.migration_type == MigrationType.SEED:
                seed_migration = m
                break
        
        if not seed_migration and not data:
            raise MigrationNotFoundException(f"Seed data not found: {seed_name}")
        
        logger.info(f"Loading seed data: {seed_name}")
        
        try:
            if truncate:
                self._truncate_tables(seed_migration)
            
            if seed_migration:
                result = seed_migration.up()
            else:
                result = self._load_seed_data(data)
            
            return {
                'status': 'completed',
                'seed': seed_name,
                'result': result
            }
            
        except Exception as e:
            logger.error(f"Seed data loading failed: {e}")
            raise DataMigrationException(f"Seed data loading failed: {e}")
    
    def _truncate_tables(self, migration: BaseMigration) -> None:
        """Truncate tables before seeding."""
        if hasattr(migration, 'tables'):
            for table in migration.tables:
                self.session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                logger.debug(f"Truncated table {table}")
    
    def _load_seed_data(self, data: Dict) -> Dict[str, int]:
        """Load seed data from dictionary."""
        results = {}
        
        for table_name, rows in data.items():
            if not rows:
                continue
            
            # Insert rows
            for row in rows:
                stmt = text(f"""
                    INSERT INTO {table_name} ({', '.join(row.keys())})
                    VALUES ({', '.join([f':{k}' for k in row.keys()])})
                    ON CONFLICT (id) DO NOTHING
                """)
                self.session.execute(stmt, row)
            
            results[table_name] = len(rows)
            logger.debug(f"Loaded {len(rows)} rows into {table_name}")
        
        self.session.flush()
        return results
    
    # ========================================================================
    # Version Management
    # ========================================================================
    
    def get_current_version(self) -> Optional[str]:
        """Get current database schema version."""
        result = self.session.execute(
            text("SELECT version FROM migrations ORDER BY applied_at DESC LIMIT 1")
        ).first()
        
        return result[0] if result else None
    
    def get_applied_migrations(self) -> List[MigrationMetadata]:
        """Get list of applied migrations."""
        result = self.session.execute(
            text("""
                SELECT version, name, description, migration_type, checksum,
                       dependencies, applied_at, duration, status, author
                FROM migrations
                ORDER BY applied_at
            """)
        )
        
        migrations = []
        for row in result:
            migrations.append(MigrationMetadata(
                version=row[0],
                name=row[1],
                description=row[2],
                migration_type=MigrationType(row[3]),
                dependencies=json.loads(row[4]) if row[4] else [],
                created_at=datetime.utcnow(),  # Not stored
                applied_at=row[5],
                duration=row[6],
                status=MigrationStatus(row[7]),
                checksum=row[8],
                author=row[9]
            ))
        
        return migrations
    
    def get_pending_migrations(self) -> List[MigrationMetadata]:
        """Get list of pending migrations."""
        applied = {m.version for m in self.get_applied_migrations()}
        
        pending = []
        for version, migration in self.migrations.items():
            if version not in applied:
                pending.append(migration.get_metadata())
        
        return sorted(pending, key=lambda m: self._parse_version(m.version))
    
    def get_migration_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get migration history."""
        result = self.session.execute(
            text("""
                SELECT version, name, migration_type, applied_at, duration, status
                FROM migrations
                ORDER BY applied_at DESC
                LIMIT :limit
            """),
            {'limit': limit}
        )
        
        return [
            {
                'version': row[0],
                'name': row[1],
                'type': row[2],
                'applied_at': row[3].isoformat() if row[3] else None,
                'duration': row[4],
                'status': row[5]
            }
            for row in result
        ]
    
    def verify_migration_integrity(self) -> Dict[str, Any]:
        """
        Verify integrity of applied migrations.
        
        Returns:
            Integrity check results
        """
        results = {
            'verified': True,
            'mismatches': [],
            'missing': [],
            'corrupted': []
        }
        
        applied = self.get_applied_migrations()
        
        for app in applied:
            migration = self.migrations.get(app.version)
            
            if not migration:
                results['missing'].append(app.version)
                results['verified'] = False
                continue
            
            # Verify checksum
            current_checksum = migration._calculate_checksum()
            if current_checksum != app.checksum:
                results['mismatches'].append({
                    'version': app.version,
                    'expected': app.checksum,
                    'actual': current_checksum
                })
                results['verified'] = False
        
        return results
    
    # ========================================================================
    # Alembic Integration
    # ========================================================================
    
    def init_alembic(self) -> None:
        """Initialize Alembic for schema migrations."""
        if not self.alembic_ini_path:
            raise MigrationException("Alembic ini path not configured")
        
        config = Config(self.alembic_ini_path)
        command.init(config, str(self.migrations_dir / 'alembic'))
        logger.info("Initialized Alembic")
    
    def create_alembic_migration(self, message: str) -> str:
        """Create a new Alembic migration."""
        if not self.alembic_ini_path:
            raise MigrationException("Alembic ini path not configured")
        
        config = Config(self.alembic_ini_path)
        script = command.revision(config, message=message, autogenerate=True)
        logger.info(f"Created Alembic migration: {script.revision}")
        
        return script.revision
    
    def run_alembic_migration(self, revision: str = 'head') -> None:
        """Run Alembic migrations."""
        if not self.alembic_ini_path:
            raise MigrationException("Alembic ini path not configured")
        
        config = Config(self.alembic_ini_path)
        command.upgrade(config, revision)
        logger.info(f"Ran Alembic migration to {revision}")
    
    def get_alembic_history(self) -> List[Dict[str, Any]]:
        """Get Alembic migration history."""
        if not self.alembic_ini_path:
            raise MigrationException("Alembic ini path not configured")
        
        config = Config(self.alembic_ini_path)
        script = ScriptDirectory.from_config(config)
        
        history = []
        for revision in script.walk_revisions():
            history.append({
                'revision': revision.revision,
                'down_revision': revision.down_revision,
                'date': revision.date,
                'branch_labels': revision.branch_labels
            })
        
        return history
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def create_migration_file(
        self,
        name: str,
        migration_type: MigrationType = MigrationType.SCHEMA,
        version: Optional[str] = None
    ) -> Path:
        """
        Create a new migration file from template.
        
        Args:
            name: Migration name
            migration_type: Type of migration
            version: Optional version (auto-generated if not provided)
            
        Returns:
            Path to created file
        """
        if not version:
            version = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        filename = f"{version}_{name}.py"
        filepath = self.migrations_dir / filename
        
        # Template
        template = f'''"""
Migration: {name}

Version: {version}
Type: {migration_type.value}
Created: {datetime.utcnow().isoformat()}
"""

from sqlalchemy import text
from ..services.migration_service import BaseMigration, MigrationType


class Migration(BaseMigration):
    """Migration {version}: {name}"""
    
    version = "{version}"
    name = "{name}"
    description = "Description of this migration"
    migration_type = MigrationType.{migration_type.name}
    dependencies = []  # List of dependent migration versions
    author = "system"
    
    def up(self) -> None:
        """Apply the migration."""
        # TODO: Implement migration
        pass
    
    def down(self) -> None:
        """Rollback the migration."""
        # TODO: Implement rollback
        pass
    
    def validate(self) -> bool:
        """Validate migration prerequisites."""
        return True
'''
        
        with open(filepath, 'w') as f:
            f.write(template)
        
        logger.info(f"Created migration file: {filepath}")
        
        # Reload migrations
        self._load_migration_module(filename.stem)
        
        return filepath
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get overall migration status."""
        current = self.get_current_version()
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        return {
            'current_version': current,
            'applied_count': len(applied),
            'pending_count': len(pending),
            'latest_version': pending[-1].version if pending else current,
            'applied_migrations': [m.to_dict() for m in applied[-10:]],  # Last 10
            'pending_migrations': [m.to_dict() for m in pending[:10]]  # Next 10
        }
    
    # ========================================================================
    # Job Monitoring
    # ========================================================================
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get list of active migration jobs."""
        return [
            {
                'job_id': job.job_id,
                'target_version': job.target_version,
                'status': job.status.value,
                'current_version': job.current_version,
                'migrations_count': len(job.migrations),
                'started_at': job.started_at.isoformat() if job.started_at else None
            }
            for job in self.active_jobs.values()
        ]
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running migration job."""
        with self._lock:
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                if job.status == MigrationStatus.RUNNING:
                    job.status = MigrationStatus.FAILED
                    job.error = "Cancelled by user"
                    logger.info(f"Cancelled migration job {job_id}")
                    return True
        return False
    
    # ========================================================================
    # Health Check
    # ========================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """Perform migration service health check."""
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'migrations_count': len(self.migrations),
            'applied_count': len(self.get_applied_migrations()),
            'pending_count': len(self.get_pending_migrations()),
            'current_version': self.get_current_version(),
            'active_jobs': len(self.active_jobs)
        }
        
        # Verify integrity
        try:
            integrity = self.verify_migration_integrity()
            if not integrity['verified']:
                results['status'] = 'degraded'
                results['integrity_issues'] = integrity
        except Exception as e:
            results['status'] = 'degraded'
            results['integrity_error'] = str(e)
        
        # Check if migrations directory exists
        if not self.migrations_dir.exists():
            results['status'] = 'degraded'
            results['warnings'] = results.get('warnings', []) + ['Migrations directory not found']
        
        return results


# ============================================================================
# Example Migration
# ============================================================================

class ExampleMigration(BaseMigration):
    """Example migration for demonstration."""
    
    version = "20240101_000000"
    name = "example_migration"
    description = "Example migration showing structure"
    migration_type = MigrationType.SCHEMA
    dependencies = []
    author = "system"
    
    def up(self) -> None:
        """Apply the migration."""
        # Example: Create a table
        self.session.execute(text("""
            CREATE TABLE IF NOT EXISTS example (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Example: Add a column
        self.session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS example_column VARCHAR(50)
        """))
    
    def down(self) -> None:
        """Rollback the migration."""
        # Example: Drop table
        self.session.execute(text("DROP TABLE IF EXISTS example"))
        
        # Example: Remove column
        self.session.execute(text("""
            ALTER TABLE users 
            DROP COLUMN IF EXISTS example_column
        """))


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main service
    'MigrationService',
    
    # Base classes
    'BaseMigration',
    
    # Constants
    'MigrationStatus',
    'MigrationType',
    'MigrationDirection',
    
    # Models
    'MigrationMetadata',
    'MigrationJob',
    
    # Exceptions
    'MigrationException',
    'MigrationNotFoundException',
    'MigrationConflictException',
    'MigrationFailedException',
    'SchemaVersionException',
    'DataMigrationException',
    'RollbackException',
]