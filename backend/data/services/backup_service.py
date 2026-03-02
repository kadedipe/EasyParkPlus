# parking-management/data/services/backup_service.py
"""
Backup service module for the parking management system.

This module provides comprehensive backup and restore functionality including
database backups, file backups, incremental backups, backup rotation,
encryption, and restoration capabilities.
"""

from typing import (
    List, Optional, Dict, Any, Tuple, Union, Callable, BinaryIO,
    Iterator
)
from datetime import datetime, timedelta
import logging
import os
import shutil
import json
import pickle
import hashlib
import zipfile
import tarfile
import gzip
import bz2
from pathlib import Path
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import io

from sqlalchemy.orm import Session
from sqlalchemy import inspect, text

from ..repositories import (
    UserRepository,
    VehicleRepository,
    ParkingSpotRepository,
    ReservationRepository,
    PaymentRepository,
    AuditLogRepository,
    SystemConfigRepository
)
from .base_service import BaseService, ServiceException, with_retry
from .encryption_service import EncryptionService
from .notification_service import NotificationService

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class BackupException(ServiceException):
    """Base exception for backup service."""
    pass


class BackupNotFoundException(BackupException):
    """Raised when a backup is not found."""
    pass


class RestoreException(BackupException):
    """Raised when restore operation fails."""
    pass


class BackupCorruptedException(BackupException):
    """Raised when a backup file is corrupted."""
    pass


class BackupInProgressException(BackupException):
    """Raised when a backup is already in progress."""
    pass


class InsufficientSpaceException(BackupException):
    """Raised when insufficient space for backup."""
    pass


# ============================================================================
# Backup Models
# ============================================================================

class BackupType:
    """Backup type constants."""
    FULL = 'full'
    INCREMENTAL = 'incremental'
    DIFFERENTIAL = 'differential'
    SCHEMA_ONLY = 'schema_only'
    DATA_ONLY = 'data_only'


class BackupStatus:
    """Backup status constants."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    VERIFYING = 'verifying'
    VERIFIED = 'verified'


class BackupFormat:
    """Backup format constants."""
    SQL = 'sql'
    JSON = 'json'
    CSV = 'csv'
    PICKLE = 'pickle'
    CUSTOM = 'custom'


class BackupCompression:
    """Backup compression constants."""
    NONE = 'none'
    GZIP = 'gzip'
    BZIP2 = 'bzip2'
    ZIP = 'zip'


class BackupMetadata:
    """Metadata for a backup."""
    
    def __init__(
        self,
        backup_id: str,
        backup_type: str,
        format: str,
        compression: str,
        tables: List[str],
        size: int,
        checksum: str,
        created_at: datetime,
        duration: float,
        status: str,
        encrypted: bool = False,
        parent_backup_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        self.backup_id = backup_id
        self.backup_type = backup_type
        self.format = format
        self.compression = compression
        self.tables = tables
        self.size = size
        self.checksum = checksum
        self.created_at = created_at
        self.duration = duration
        self.status = status
        self.encrypted = encrypted
        self.parent_backup_id = parent_backup_id
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'backup_id': self.backup_id,
            'backup_type': self.backup_type,
            'format': self.format,
            'compression': self.compression,
            'tables': self.tables,
            'size': self.size,
            'size_formatted': self._format_size(self.size),
            'checksum': self.checksum,
            'created_at': self.created_at.isoformat(),
            'duration': self.duration,
            'status': self.status,
            'encrypted': self.encrypted,
            'parent_backup_id': self.parent_backup_id,
            'metadata': self.metadata
        }
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"


class BackupJob:
    """Represents a backup job."""
    
    def __init__(
        self,
        backup_type: str = BackupType.FULL,
        tables: Optional[List[str]] = None,
        format: str = BackupFormat.JSON,
        compression: str = BackupCompression.GZIP,
        encrypt: bool = False,
        verify: bool = True,
        destination: Optional[str] = None,
        retention_days: int = 30
    ):
        self.job_id = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.backup_type = backup_type
        self.tables = tables or []
        self.format = format
        self.compression = compression
        self.encrypt = encrypt
        self.verify = verify
        self.destination = destination
        self.retention_days = retention_days
        self.status = BackupStatus.PENDING
        self.progress = 0.0
        self.current_table = None
        self.started_at = None
        self.completed_at = None
        self.error = None
        self.metadata = None


class RestoreJob:
    """Represents a restore job."""
    
    def __init__(
        self,
        backup_id: str,
        tables: Optional[List[str]] = None,
        restore_to: Optional[datetime] = None,
        dry_run: bool = False
    ):
        self.job_id = f"restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.backup_id = backup_id
        self.tables = tables or []
        self.restore_to = restore_to
        self.dry_run = dry_run
        self.status = BackupStatus.PENDING
        self.progress = 0.0
        self.current_table = None
        self.started_at = None
        self.completed_at = None
        self.error = None


# ============================================================================
# Backup Service
# ============================================================================

class BackupService(BaseService):
    """
    Comprehensive backup and restore service.
    
    Provides:
    - Full, incremental, and differential backups
    - Multiple backup formats (SQL, JSON, CSV, pickle)
    - Compression support (gzip, bzip2, zip)
    - Encryption support
    - Backup verification
    - Retention policy management
    - Point-in-time recovery
    - Parallel backup of tables
    - Backup monitoring and notifications
    """
    
    def __init__(
        self,
        session: Session,
        backup_dir: str = "./backups",
        encryption_service: Optional[EncryptionService] = None,
        notification_service: Optional[NotificationService] = None,
        max_workers: int = 4
    ):
        """
        Initialize the backup service.
        
        Args:
            session: SQLAlchemy session
            backup_dir: Directory to store backups
            encryption_service: Optional encryption service
            notification_service: Optional notification service
            max_workers: Maximum parallel workers for backup
        """
        super().__init__(session)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.encryption = encryption_service
        self.notifications = notification_service
        self.max_workers = max_workers
        
        # Initialize repositories
        self.user_repo = UserRepository(session)
        self.vehicle_repo = VehicleRepository(session)
        self.spot_repo = ParkingSpotRepository(session)
        self.reservation_repo = ReservationRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.audit_repo = AuditLogRepository(session)
        self.config_repo = SystemConfigRepository(session)
        
        # Active jobs
        self.active_backups: Dict[str, BackupJob] = {}
        self.active_restores: Dict[str, RestoreJob] = {}
        self._lock = threading.Lock()
        
        # Load backup history
        self.backup_history = self._load_backup_history()
        
        logger.info(f"BackupService initialized with backup directory: {backup_dir}")
    
    # ========================================================================
    # Backup Operations
    # ========================================================================
    
    def create_backup(
        self,
        backup_type: str = BackupType.FULL,
        tables: Optional[List[str]] = None,
        format: str = BackupFormat.JSON,
        compression: str = BackupCompression.GZIP,
        encrypt: bool = False,
        verify: bool = True,
        destination: Optional[str] = None,
        retention_days: int = 30
    ) -> BackupJob:
        """
        Create a new backup.
        
        Args:
            backup_type: Type of backup
            tables: Specific tables to backup (None for all)
            format: Backup format
            compression: Compression type
            encrypt: Whether to encrypt the backup
            verify: Whether to verify after backup
            destination: Custom destination path
            retention_days: Number of days to retain
            
        Returns:
            Backup job
            
        Raises:
            BackupInProgressException: If another backup is running
            InsufficientSpaceException: If insufficient disk space
        """
        # Check for existing backup
        with self._lock:
            running_backups = [
                job for job in self.active_backups.values()
                if job.status in [BackupStatus.RUNNING, BackupStatus.PENDING]
            ]
            if running_backups:
                raise BackupInProgressException(
                    f"Backup already in progress: {running_backups[0].job_id}"
                )
        
        # Check disk space
        if not self._check_disk_space():
            raise InsufficientSpaceException("Insufficient disk space for backup")
        
        # Create job
        job = BackupJob(
            backup_type=backup_type,
            tables=tables or self._get_all_tables(),
            format=format,
            compression=compression,
            encrypt=encrypt,
            verify=verify,
            destination=destination or str(self.backup_dir),
            retention_days=retention_days
        )
        
        with self._lock:
            self.active_backups[job.job_id] = job
        
        # Start backup in background
        thread = threading.Thread(
            target=self._run_backup,
            args=(job,)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started backup job {job.job_id}")
        return job
    
    def _run_backup(self, job: BackupJob) -> None:
        """Run the backup job."""
        job.status = BackupStatus.RUNNING
        job.started_at = datetime.utcnow()
        
        try:
            # Determine backup strategy
            if job.backup_type == BackupType.FULL:
                self._run_full_backup(job)
            elif job.backup_type == BackupType.INCREMENTAL:
                self._run_incremental_backup(job)
            elif job.backup_type == BackupType.DIFFERENTIAL:
                self._run_differential_backup(job)
            elif job.backup_type == BackupType.SCHEMA_ONLY:
                self._run_schema_backup(job)
            elif job.backup_type == BackupType.DATA_ONLY:
                self._run_data_backup(job)
            else:
                raise ValueError(f"Unknown backup type: {job.backup_type}")
            
            # Verify backup if requested
            if job.verify:
                job.status = BackupStatus.VERIFYING
                self._verify_backup(job)
                job.status = BackupStatus.VERIFIED
            
            job.status = BackupStatus.COMPLETED
            
            # Send notification
            self._send_backup_notification(job, success=True)
            
            # Apply retention policy
            self._apply_retention_policy(job.retention_days)
            
        except Exception as e:
            job.status = BackupStatus.FAILED
            job.error = str(e)
            logger.error(f"Backup job {job.job_id} failed: {e}")
            
            # Send failure notification
            self._send_backup_notification(job, success=False, error=str(e))
        
        finally:
            job.completed_at = datetime.utcnow()
            job.duration = (job.completed_at - job.started_at).total_seconds()
            
            # Save metadata
            if job.metadata:
                self._save_backup_metadata(job.metadata)
            
            # Remove from active jobs
            with self._lock:
                del self.active_backups[job.job_id]
    
    def _run_full_backup(self, job: BackupJob) -> None:
        """Run a full backup of all tables."""
        logger.info(f"Starting full backup: {job.job_id}")
        
        backup_data = {
            'metadata': {
                'job_id': job.job_id,
                'backup_type': job.backup_type,
                'created_at': datetime.utcnow().isoformat(),
                'tables': job.tables,
                'format': job.format,
                'compression': job.compression,
                'encrypted': job.encrypt
            },
            'data': {}
        }
        
        total_tables = len(job.tables)
        
        # Backup tables in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_table = {
                executor.submit(self._backup_table, table, job.format): table
                for table in job.tables
            }
            
            for i, future in enumerate(as_completed(future_to_table)):
                table = future_to_table[future]
                try:
                    table_data = future.result()
                    backup_data['data'][table] = table_data
                    
                    job.progress = (i + 1) / total_tables * 100
                    job.current_table = table
                    
                    logger.debug(f"Backed up table {table} ({i+1}/{total_tables})")
                    
                except Exception as e:
                    logger.error(f"Failed to backup table {table}: {e}")
                    raise
        
        # Save backup file
        filename = self._save_backup_data(job, backup_data)
        
        # Calculate checksum
        checksum = self._calculate_checksum(filename)
        
        # Create metadata
        job.metadata = BackupMetadata(
            backup_id=job.job_id,
            backup_type=job.backup_type,
            format=job.format,
            compression=job.compression,
            tables=job.tables,
            size=os.path.getsize(filename),
            checksum=checksum,
            created_at=job.started_at,
            duration=job.duration or 0,
            status=job.status,
            encrypted=job.encrypt,
            metadata={'filename': str(filename)}
        )
        
        logger.info(f"Completed full backup: {job.job_id}, size: {job.metadata.size} bytes")
    
    def _run_incremental_backup(self, job: BackupJob) -> None:
        """Run an incremental backup (only changes since last backup)."""
        # Get last backup
        last_backup = self._get_last_backup()
        if not last_backup:
            logger.warning("No previous backup found, performing full backup instead")
            job.backup_type = BackupType.FULL
            self._run_full_backup(job)
            return
        
        logger.info(f"Starting incremental backup since {last_backup.created_at}")
        
        backup_data = {
            'metadata': {
                'job_id': job.job_id,
                'backup_type': job.backup_type,
                'parent_backup': last_backup.backup_id,
                'parent_timestamp': last_backup.created_at.isoformat(),
                'created_at': datetime.utcnow().isoformat(),
                'tables': job.tables,
                'format': job.format,
                'compression': job.compression,
                'encrypted': job.encrypt
            },
            'data': {}
        }
        
        total_tables = len(job.tables)
        
        # Backup only changed records
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_table = {
                executor.submit(
                    self._backup_table_incremental,
                    table,
                    job.format,
                    last_backup.created_at
                ): table
                for table in job.tables
            }
            
            for i, future in enumerate(as_completed(future_to_table)):
                table = future_to_table[future]
                try:
                    table_data = future.result()
                    if table_data:  # Only include if there are changes
                        backup_data['data'][table] = table_data
                    
                    job.progress = (i + 1) / total_tables * 100
                    job.current_table = table
                    
                except Exception as e:
                    logger.error(f"Failed to backup table {table}: {e}")
                    raise
        
        # Save backup file
        filename = self._save_backup_data(job, backup_data)
        
        # Calculate checksum
        checksum = self._calculate_checksum(filename)
        
        # Create metadata
        job.metadata = BackupMetadata(
            backup_id=job.job_id,
            backup_type=job.backup_type,
            format=job.format,
            compression=job.compression,
            tables=job.tables,
            size=os.path.getsize(filename),
            checksum=checksum,
            created_at=job.started_at,
            duration=job.duration or 0,
            status=job.status,
            encrypted=job.encrypt,
            parent_backup_id=last_backup.backup_id,
            metadata={'filename': str(filename)}
        )
        
        logger.info(f"Completed incremental backup: {job.job_id}")
    
    def _run_differential_backup(self, job: BackupJob) -> None:
        """Run a differential backup (changes since last full backup)."""
        # Get last full backup
        last_full = self._get_last_full_backup()
        if not last_full:
            logger.warning("No full backup found, performing full backup instead")
            job.backup_type = BackupType.FULL
            self._run_full_backup(job)
            return
        
        logger.info(f"Starting differential backup since full backup {last_full.created_at}")
        
        backup_data = {
            'metadata': {
                'job_id': job.job_id,
                'backup_type': job.backup_type,
                'full_backup': last_full.backup_id,
                'full_timestamp': last_full.created_at.isoformat(),
                'created_at': datetime.utcnow().isoformat(),
                'tables': job.tables,
                'format': job.format,
                'compression': job.compression,
                'encrypted': job.encrypt
            },
            'data': {}
        }
        
        total_tables = len(job.tables)
        
        # Backup changed records since last full
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_table = {
                executor.submit(
                    self._backup_table_incremental,
                    table,
                    job.format,
                    last_full.created_at
                ): table
                for table in job.tables
            }
            
            for i, future in enumerate(as_completed(future_to_table)):
                table = future_to_table[future]
                try:
                    table_data = future.result()
                    if table_data:
                        backup_data['data'][table] = table_data
                    
                    job.progress = (i + 1) / total_tables * 100
                    job.current_table = table
                    
                except Exception as e:
                    logger.error(f"Failed to backup table {table}: {e}")
                    raise
        
        # Save backup file
        filename = self._save_backup_data(job, backup_data)
        
        # Calculate checksum
        checksum = self._calculate_checksum(filename)
        
        # Create metadata
        job.metadata = BackupMetadata(
            backup_id=job.job_id,
            backup_type=job.backup_type,
            format=job.format,
            compression=job.compression,
            tables=job.tables,
            size=os.path.getsize(filename),
            checksum=checksum,
            created_at=job.started_at,
            duration=job.duration or 0,
            status=job.status,
            encrypted=job.encrypt,
            parent_backup_id=last_full.backup_id,
            metadata={'filename': str(filename)}
        )
        
        logger.info(f"Completed differential backup: {job.job_id}")
    
    def _run_schema_backup(self, job: BackupJob) -> None:
        """Backup only database schema."""
        logger.info(f"Starting schema backup: {job.job_id}")
        
        inspector = inspect(self.session.bind)
        
        schema_data = {}
        
        for table_name in job.tables:
            # Get table schema
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            schema_data[table_name] = {
                'columns': [
                    {
                        'name': c['name'],
                        'type': str(c['type']),
                        'nullable': c['nullable'],
                        'default': str(c['default']) if c['default'] else None,
                        'primary_key': c.get('primary_key', False)
                    }
                    for c in columns
                ],
                'indexes': indexes,
                'foreign_keys': foreign_keys
            }
            
            job.progress += 100 / len(job.tables)
        
        backup_data = {
            'metadata': {
                'job_id': job.job_id,
                'backup_type': job.backup_type,
                'created_at': datetime.utcnow().isoformat(),
                'tables': job.tables,
                'format': 'json',
                'compression': job.compression,
                'encrypted': job.encrypt
            },
            'schema': schema_data
        }
        
        # Save backup file
        filename = self._save_backup_data(job, backup_data)
        
        # Calculate checksum
        checksum = self._calculate_checksum(filename)
        
        # Create metadata
        job.metadata = BackupMetadata(
            backup_id=job.job_id,
            backup_type=job.backup_type,
            format='json',
            compression=job.compression,
            tables=job.tables,
            size=os.path.getsize(filename),
            checksum=checksum,
            created_at=job.started_at,
            duration=job.duration or 0,
            status=job.status,
            encrypted=job.encrypt,
            metadata={'filename': str(filename), 'type': 'schema_only'}
        )
        
        logger.info(f"Completed schema backup: {job.job_id}")
    
    def _run_data_backup(self, job: BackupJob) -> None:
        """Backup only data (no schema)."""
        # Similar to full backup but without schema info
        self._run_full_backup(job)
    
    def _backup_table(self, table_name: str, format: str) -> List[Dict]:
        """Backup a single table."""
        # Get repository for table
        repo = self._get_repository_for_table(table_name)
        
        if repo:
            # Use repository if available
            items = repo.get_all()
            return [self._serialize_item(item) for item in items]
        else:
            # Fallback to raw SQL
            result = self.session.execute(text(f"SELECT * FROM {table_name}"))
            return [dict(row._mapping) for row in result]
    
    def _backup_table_incremental(
        self,
        table_name: str,
        format: str,
        since: datetime
    ) -> List[Dict]:
        """Backup changes in a table since a timestamp."""
        # This assumes tables have 'updated_at' or 'created_at' columns
        repo = self._get_repository_for_table(table_name)
        
        if repo and hasattr(repo.model_class, 'updated_at'):
            # Use repository with date filter
            items = self.session.query(repo.model_class).filter(
                repo.model_class.updated_at >= since
            ).all()
            return [self._serialize_item(item) for item in items]
        else:
            # Fallback - can't do incremental without timestamp
            return []
    
    def _serialize_item(self, item: Any) -> Dict:
        """Serialize a model instance to dictionary."""
        if hasattr(item, 'to_dict'):
            return item.to_dict()
        
        data = {}
        for column in item.__table__.columns:
            value = getattr(item, column.name)
            if isinstance(value, (datetime, date)):
                value = value.isoformat()
            elif isinstance(value, Enum):
                value = value.value
            elif isinstance(value, Decimal):
                value = float(value)
            data[column.name] = value
        return data
    
    def _save_backup_data(self, job: BackupJob, data: Dict) -> Path:
        """Save backup data to file."""
        # Determine filename
        filename = self.backup_dir / f"{job.job_id}.{job.format}"
        
        # Convert to appropriate format
        if job.format == BackupFormat.JSON:
            content = json.dumps(data, default=str, indent=2).encode()
        elif job.format == BackupFormat.PICKLE:
            content = pickle.dumps(data)
        elif job.format == BackupFormat.CSV:
            # Convert to CSV (simplified)
            import csv
            import io
            
            output = io.StringIO()
            if 'data' in data:
                for table, rows in data['data'].items():
                    if rows and isinstance(rows[0], dict):
                        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                        writer.writeheader()
                        writer.writerows(rows)
            content = output.getvalue().encode()
        else:
            content = str(data).encode()
        
        # Apply compression
        if job.compression == BackupCompression.GZIP:
            content = gzip.compress(content)
            filename = filename.with_suffix(filename.suffix + '.gz')
        elif job.compression == BackupCompression.BZIP2:
            content = bz2.compress(content)
            filename = filename.with_suffix(filename.suffix + '.bz2')
        elif job.compression == BackupCompression.ZIP:
            # Create zip file
            zip_filename = filename.with_suffix('.zip')
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"{job.job_id}.{job.format}", content)
            filename = zip_filename
            content = None  # Already written
        
        # Apply encryption
        if job.encrypt and self.encryption and content:
            content = self.encryption.encrypt(content)
            filename = filename.with_suffix(filename.suffix + '.enc')
        
        # Write file
        if content:  # Skip if already written (zip case)
            with open(filename, 'wb') as f:
                f.write(content)
        
        return filename
    
    def _verify_backup(self, job: BackupJob) -> bool:
        """Verify backup integrity."""
        if not job.metadata:
            logger.warning(f"No metadata for backup {job.job_id}, skipping verification")
            return False
        
        filename = self.backup_dir / job.metadata.metadata['filename']
        
        # Check file exists
        if not filename.exists():
            raise BackupCorruptedException(f"Backup file not found: {filename}")
        
        # Verify checksum
        actual_checksum = self._calculate_checksum(filename)
        if actual_checksum != job.metadata.checksum:
            raise BackupCorruptedException(
                f"Checksum mismatch. Expected: {job.metadata.checksum}, Got: {actual_checksum}"
            )
        
        # Try to read the file
        try:
            data = self._load_backup_file(filename, job)
            if not data:
                raise BackupCorruptedException("Failed to load backup data")
        except Exception as e:
            raise BackupCorruptedException(f"Failed to read backup: {e}")
        
        logger.info(f"Backup {job.job_id} verified successfully")
        return True
    
    # ========================================================================
    # Restore Operations
    # ========================================================================
    
    def restore_backup(
        self,
        backup_id: str,
        tables: Optional[List[str]] = None,
        restore_to: Optional[datetime] = None,
        dry_run: bool = False
    ) -> RestoreJob:
        """
        Restore from a backup.
        
        Args:
            backup_id: ID of backup to restore
            tables: Specific tables to restore (None for all)
            restore_to: Point-in-time to restore to (for incremental backups)
            dry_run: Perform dry run without actual restore
            
        Returns:
            Restore job
            
        Raises:
            BackupNotFoundException: If backup not found
            RestoreException: If restore fails
        """
        # Find backup metadata
        backup_meta = self._find_backup(backup_id)
        if not backup_meta:
            raise BackupNotFoundException(f"Backup not found: {backup_id}")
        
        # Create job
        job = RestoreJob(
            backup_id=backup_id,
            tables=tables or backup_meta.tables,
            restore_to=restore_to,
            dry_run=dry_run
        )
        
        with self._lock:
            self.active_restores[job.job_id] = job
        
        # Start restore in background
        thread = threading.Thread(
            target=self._run_restore,
            args=(job, backup_meta)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started restore job {job.job_id}")
        return job
    
    def _run_restore(self, job: RestoreJob, backup_meta: BackupMetadata) -> None:
        """Run the restore job."""
        job.status = BackupStatus.RUNNING
        job.started_at = datetime.utcnow()
        
        try:
            # Load backup data
            filename = self.backup_dir / backup_meta.metadata['filename']
            backup_data = self._load_backup_file(filename, backup_meta)
            
            if not backup_data:
                raise RestoreException("Failed to load backup data")
            
            # Handle incremental backups
            if backup_meta.backup_type in [BackupType.INCREMENTAL, BackupType.DIFFERENTIAL]:
                self._restore_incremental(job, backup_meta, backup_data)
            else:
                self._restore_full(job, backup_meta, backup_data)
            
            job.status = BackupStatus.COMPLETED if not job.dry_run else BackupStatus.VERIFIED
            
        except Exception as e:
            job.status = BackupStatus.FAILED
            job.error = str(e)
            logger.error(f"Restore job {job.job_id} failed: {e}")
        
        finally:
            job.completed_at = datetime.utcnow()
            
            with self._lock:
                del self.active_restores[job.job_id]
    
    def _restore_full(
        self,
        job: RestoreJob,
        backup_meta: BackupMetadata,
        backup_data: Dict
    ) -> None:
        """Perform full restore."""
        logger.info(f"Starting full restore: {job.job_id}")
        
        tables_to_restore = job.tables or list(backup_data.get('data', {}).keys())
        total_tables = len(tables_to_restore)
        
        for i, table in enumerate(tables_to_restore):
            if table not in backup_data.get('data', {}):
                logger.warning(f"Table {table} not found in backup, skipping")
                continue
            
            job.current_table = table
            table_data = backup_data['data'][table]
            
            if not job.dry_run:
                self._restore_table(table, table_data)
            
            job.progress = (i + 1) / total_tables * 100
            logger.debug(f"Restored table {table} ({i+1}/{total_tables})")
    
    def _restore_incremental(
        self,
        job: RestoreJob,
        backup_meta: BackupMetadata,
        backup_data: Dict
    ) -> None:
        """Perform incremental restore."""
        # Need to restore base backup first
        if backup_meta.parent_backup_id:
            parent_meta = self._find_backup(backup_meta.parent_backup_id)
            if parent_meta:
                parent_file = self.backup_dir / parent_meta.metadata['filename']
                parent_data = self._load_backup_file(parent_file, parent_meta)
                
                if parent_data:
                    # Apply base backup
                    self._restore_full(job, parent_meta, parent_data)
        
        # Then apply incremental changes
        logger.info(f"Applying incremental changes: {job.job_id}")
        self._restore_full(job, backup_meta, backup_data)
    
    def _restore_table(self, table_name: str, data: List[Dict]) -> None:
        """Restore a single table."""
        if not data:
            return
        
        # Get repository for table
        repo = self._get_repository_for_table(table_name)
        
        if repo:
            # Use repository if available
            for item_data in data:
                # Check if exists
                existing = repo.get(item_data.get('id'))
                if existing:
                    # Update
                    for key, value in item_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                else:
                    # Create new
                    repo.create(repo.model_class(**item_data))
        else:
            # Fallback to raw SQL
            for item_data in data:
                columns = ', '.join(item_data.keys())
                placeholders = ', '.join([f":{k}" for k in item_data.keys()])
                update_placeholders = ', '.join([f"{k}=:{k}" for k in item_data.keys()])
                
                # Upsert
                stmt = text(f"""
                    INSERT INTO {table_name} ({columns})
                    VALUES ({placeholders})
                    ON CONFLICT (id) DO UPDATE SET {update_placeholders}
                """)
                
                self.session.execute(stmt, item_data)
        
        self.session.flush()
    
    def _load_backup_file(self, filename: Path, backup_meta: BackupMetadata) -> Optional[Dict]:
        """Load backup data from file."""
        # Read file
        with open(filename, 'rb') as f:
            content = f.read()
        
        # Decrypt if needed
        if backup_meta.encrypted and self.encryption:
            content = self.encryption.decrypt(content)
        
        # Decompress
        if backup_meta.compression == BackupCompression.GZIP:
            content = gzip.decompress(content)
        elif backup_meta.compression == BackupCompression.BZIP2:
            content = bz2.decompress(content)
        elif backup_meta.compression == BackupCompression.ZIP:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Assume single file in zip
                for name in zf.namelist():
                    content = zf.read(name)
                    break
        
        # Parse based on format
        if backup_meta.format == BackupFormat.JSON:
            return json.loads(content.decode())
        elif backup_meta.format == BackupFormat.PICKLE:
            return pickle.loads(content)
        else:
            return {'data': content.decode()}
    
    # ========================================================================
    # Backup Management
    # ========================================================================
    
    def list_backups(self) -> List[BackupMetadata]:
        """List all available backups."""
        return sorted(
            self.backup_history.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
    
    def get_backup_info(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get information about a specific backup."""
        return self._find_backup(backup_id)
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a backup.
        
        Args:
            backup_id: Backup ID to delete
            
        Returns:
            True if deleted
        """
        backup_meta = self._find_backup(backup_id)
        if not backup_meta:
            return False
        
        # Delete file
        filename = self.backup_dir / backup_meta.metadata['filename']
        if filename.exists():
            filename.unlink()
        
        # Remove from history
        with self._lock:
            if backup_id in self.backup_history:
                del self.backup_history[backup_id]
        
        # Update metadata file
        self._save_backup_history()
        
        logger.info(f"Deleted backup {backup_id}")
        return True
    
    def _apply_retention_policy(self, days: int) -> None:
        """Apply retention policy - delete old backups."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        for backup_id, meta in list(self.backup_history.items()):
            if meta.created_at < cutoff:
                self.delete_backup(backup_id)
                logger.info(f"Deleted old backup {backup_id} due to retention policy")
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _get_all_tables(self) -> List[str]:
        """Get list of all database tables."""
        inspector = inspect(self.session.bind)
        return inspector.get_table_names()
    
    def _get_repository_for_table(self, table_name: str) -> Optional[Any]:
        """Get repository for a table name."""
        mapping = {
            'users': self.user_repo,
            'vehicles': self.vehicle_repo,
            'parking_spots': self.spot_repo,
            'reservations': self.reservation_repo,
            'payments': self.payment_repo,
            'audit_logs': self.audit_repo,
            'system_config': self.config_repo
        }
        return mapping.get(table_name)
    
    def _get_last_backup(self) -> Optional[BackupMetadata]:
        """Get the most recent backup."""
        backups = self.list_backups()
        return backups[0] if backups else None
    
    def _get_last_full_backup(self) -> Optional[BackupMetadata]:
        """Get the most recent full backup."""
        full_backups = [
            b for b in self.backup_history.values()
            if b.backup_type == BackupType.FULL
        ]
        return max(full_backups, key=lambda x: x.created_at) if full_backups else None
    
    def _find_backup(self, backup_id: str) -> Optional[BackupMetadata]:
        """Find backup by ID."""
        return self.backup_history.get(backup_id)
    
    def _calculate_checksum(self, filename: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        
        with open(filename, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _check_disk_space(self) -> bool:
        """Check if there's enough disk space for backup."""
        stat = shutil.disk_usage(self.backup_dir)
        free_gb = stat.free / (1024 ** 3)
        
        # Require at least 1GB free
        return free_gb >= 1
    
    def _load_backup_history(self) -> Dict[str, BackupMetadata]:
        """Load backup history from metadata file."""
        history_file = self.backup_dir / 'backup_history.json'
        
        if not history_file.exists():
            return {}
        
        try:
            with open(history_file, 'r') as f:
                data = json.load(f)
            
            history = {}
            for backup_id, meta in data.items():
                history[backup_id] = BackupMetadata(
                    backup_id=backup_id,
                    backup_type=meta['backup_type'],
                    format=meta['format'],
                    compression=meta['compression'],
                    tables=meta['tables'],
                    size=meta['size'],
                    checksum=meta['checksum'],
                    created_at=datetime.fromisoformat(meta['created_at']),
                    duration=meta['duration'],
                    status=meta['status'],
                    encrypted=meta.get('encrypted', False),
                    parent_backup_id=meta.get('parent_backup_id'),
                    metadata=meta.get('metadata', {})
                )
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to load backup history: {e}")
            return {}
    
    def _save_backup_metadata(self, metadata: BackupMetadata) -> None:
        """Save backup metadata to history."""
        with self._lock:
            self.backup_history[metadata.backup_id] = metadata
            self._save_backup_history()
    
    def _save_backup_history(self) -> None:
        """Save backup history to file."""
        history_file = self.backup_dir / 'backup_history.json'
        
        data = {}
        for backup_id, meta in self.backup_history.items():
            data[backup_id] = meta.to_dict()
        
        try:
            with open(history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backup history: {e}")
    
    def _send_backup_notification(
        self,
        job: BackupJob,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Send backup notification."""
        if not self.notifications:
            return
        
        subject = f"Backup {'Success' if success else 'Failed'}: {job.job_id}"
        
        if success:
            message = (
                f"Backup completed successfully.\n"
                f"Job ID: {job.job_id}\n"
                f"Type: {job.backup_type}\n"
                f"Size: {job.metadata.size if job.metadata else 0} bytes\n"
                f"Duration: {job.duration:.2f} seconds"
            )
        else:
            message = (
                f"Backup failed.\n"
                f"Job ID: {job.job_id}\n"
                f"Error: {error}"
            )
        
        self.notifications.send_notification(
            recipient='admin@system.com',  # Configure appropriately
            subject=subject,
            message=message,
            priority='high' if not success else 'normal'
        )
    
    # ========================================================================
    # Job Monitoring
    # ========================================================================
    
    def get_active_backups(self) -> List[Dict[str, Any]]:
        """Get list of active backup jobs."""
        return [
            {
                'job_id': job.job_id,
                'type': job.backup_type,
                'status': job.status,
                'progress': job.progress,
                'current_table': job.current_table,
                'started_at': job.started_at.isoformat() if job.started_at else None
            }
            for job in self.active_backups.values()
        ]
    
    def get_active_restores(self) -> List[Dict[str, Any]]:
        """Get list of active restore jobs."""
        return [
            {
                'job_id': job.job_id,
                'backup_id': job.backup_id,
                'status': job.status,
                'progress': job.progress,
                'current_table': job.current_table,
                'started_at': job.started_at.isoformat() if job.started_at else None
            }
            for job in self.active_restores.values()
        ]
    
    def cancel_backup(self, job_id: str) -> bool:
        """Cancel a running backup job."""
        with self._lock:
            if job_id in self.active_backups:
                job = self.active_backups[job_id]
                if job.status == BackupStatus.RUNNING:
                    job.status = BackupStatus.CANCELLED
                    logger.info(f"Cancelled backup job {job_id}")
                    return True
        return False
    
    # ========================================================================
    # Health Check
    # ========================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """Perform backup service health check."""
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'backup_directory': str(self.backup_dir),
            'total_backups': len(self.backup_history),
            'latest_backup': None,
            'disk_space': None,
            'active_jobs': len(self.active_backups)
        }
        
        # Check disk space
        try:
            stat = shutil.disk_usage(self.backup_dir)
            free_gb = stat.free / (1024 ** 3)
            total_gb = stat.total / (1024 ** 3)
            
            results['disk_space'] = {
                'free_gb': round(free_gb, 2),
                'total_gb': round(total_gb, 2),
                'free_percent': round(stat.free / stat.total * 100, 2)
            }
            
            if free_gb < 1:
                results['status'] = 'warning'
                results['warnings'] = ['Low disk space']
                
        except Exception as e:
            results['status'] = 'degraded'
            results['errors'] = [f"Disk space check failed: {e}"]
        
        # Latest backup
        backups = self.list_backups()
        if backups:
            results['latest_backup'] = backups[0].to_dict()
        
        # Check backup directory permissions
        if not os.access(self.backup_dir, os.W_OK):
            results['status'] = 'degraded'
            results['errors'] = results.get('errors', []) + ['Backup directory not writable']
        
        return results


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main service
    'BackupService',
    
    # Constants
    'BackupType',
    'BackupStatus',
    'BackupFormat',
    'BackupCompression',
    
    # Models
    'BackupMetadata',
    'BackupJob',
    'RestoreJob',
    
    # Exceptions
    'BackupException',
    'BackupNotFoundException',
    'RestoreException',
    'BackupCorruptedException',
    'BackupInProgressException',
    'InsufficientSpaceException',
]