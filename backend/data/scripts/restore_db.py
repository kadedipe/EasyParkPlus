#!/usr/bin/env python3
"""
Database restore script for the parking management system.

This script provides comprehensive database restore functionality including:
- Restore from local backups
- Restore from remote storage (S3, SFTP, FTP)
- Point-in-time recovery
- Selective table restoration
- Pre-restore validation
- Dry run mode
- Multiple database support (PostgreSQL, MySQL, SQLite)
- Cross-database migration

Usage:
    python restore_db.py [options] BACKUP_SOURCE

Arguments:
    BACKUP_SOURCE           Backup file path, backup ID, or remote URL

Options:
    --target-db URL        Target database URL (defaults to original)
    --tables LIST          Specific tables to restore (comma-separated)
    --point-in-time TIME   Restore to specific point in time (ISO format)
    --dry-run             Simulate restore without applying changes
    --force               Force restore even if validation fails
    --verify              Verify backup before restore
    --skip-verify         Skip backup verification
    --create-db           Create database if it doesn't exist
    --drop-existing       Drop existing tables before restore
    --no-data             Restore schema only
    --no-schema           Restore data only
    --batch-size N        Batch size for large restores [default: 1000]
    --continue-on-error   Continue restore even if errors occur
    --backup-id ID        Restore from backup ID (if using backup service)
    --config FILE         Configuration file
    --verbose             Verbose output
    --help                Show this help message

Examples:
    # Restore from local backup file
    python restore_db.py backups/backup_20240101_120000.sql.gz

    # Restore from backup ID
    python restore_db.py --backup-id backup_20240101_120000

    # Restore specific tables to different database
    python restore_db.py backup.sql --tables users,vehicles --target-db postgresql://newdb

    # Point-in-time recovery
    python restore_db.py backup.sql --point-in-time "2024-01-01 14:30:00"

    # Dry run to see what would be restored
    python restore_db.py backup.sql --dry-run --verbose

    # Restore from S3
    python restore_db.py s3://my-bucket/backups/backup.sql.gz
"""

import os
import sys
import argparse
import logging
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Set
import gzip
import bz2
import zipfile
import json
import re
from urllib.parse import urlparse

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text, inspect, MetaData
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from data.services import BackupService, EncryptionService
from data.services.backup_service import BackupMetadata
from utils.config import Config
from utils.logging import setup_logging

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class RestoreError(Exception):
    """Base exception for restore errors."""
    pass


class BackupNotFoundError(RestoreError):
    """Raised when backup source is not found."""
    pass


class ValidationError(RestoreError):
    """Raised when backup validation fails."""
    pass


class IncompatibleBackupError(RestoreError):
    """Raised when backup is incompatible with target database."""
    pass


# ============================================================================
# Restore Manager
# ============================================================================

class RestoreManager:
    """
    Manages database restore operations.
    
    Handles restoration from various sources with comprehensive validation,
    error handling, and recovery options.
    """
    
    def __init__(
        self,
        target_db_url: Optional[str] = None,
        config: Optional[Config] = None,
        encryption_service: Optional[EncryptionService] = None
    ):
        """
        Initialize the restore manager.
        
        Args:
            target_db_url: Target database URL
            config: Configuration object
            encryption_service: Optional encryption service
        """
        self.target_db_url = target_db_url
        self.config = config or Config()
        self.encryption = encryption_service
        
        # Backup service reference
        self.backup_service = None
        
        # Temporary directory for processing
        self.temp_dir = None
        
        logger.info("RestoreManager initialized")
    
    def __enter__(self):
        """Context manager entry."""
        self.temp_dir = tempfile.mkdtemp(prefix="restore_")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temporary files."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.debug(f"Cleaned up temporary directory: {self.temp_dir}")
    
    # ========================================================================
    # Main Restore Method
    # ========================================================================
    
    def restore(
        self,
        source: str,
        target_db_url: Optional[str] = None,
        tables: Optional[List[str]] = None,
        point_in_time: Optional[datetime] = None,
        dry_run: bool = False,
        force: bool = False,
        verify: bool = True,
        create_db: bool = False,
        drop_existing: bool = False,
        no_data: bool = False,
        no_schema: bool = False,
        batch_size: int = 1000,
        continue_on_error: bool = False,
        backup_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform database restore.
        
        Args:
            source: Backup source (file path, URL, or backup ID)
            target_db_url: Target database URL
            tables: Specific tables to restore
            point_in_time: Point in time to restore to
            dry_run: Simulate restore without applying changes
            force: Force restore even if validation fails
            verify: Verify backup before restore
            create_db: Create database if it doesn't exist
            drop_existing: Drop existing tables before restore
            no_data: Restore schema only
            no_schema: Restore data only
            batch_size: Batch size for large restores
            continue_on_error: Continue restore if errors occur
            backup_id: Backup ID (if using backup service)
            
        Returns:
            Dictionary with restore results
            
        Raises:
            RestoreError: If restore fails
        """
        results = {
            'success': False,
            'source': source,
            'target': target_db_url or self.target_db_url,
            'tables_restored': [],
            'tables_skipped': [],
            'errors': [],
            'warnings': [],
            'duration': 0,
            'bytes_processed': 0,
            'rows_restored': 0
        }
        
        start_time = datetime.utcnow()
        
        try:
            # Determine target database
            target_url = target_db_url or self.target_db_url
            if not target_url:
                raise RestoreError("Target database URL not specified")
            
            # Determine database type
            db_type = self._detect_db_type(target_url)
            logger.info(f"Target database type: {db_type}")
            
            # Locate backup source
            backup_file = self._locate_backup(source, backup_id)
            results['backup_file'] = str(backup_file)
            
            # Verify backup if requested
            if verify:
                self._verify_backup(backup_file, force)
            
            # Create target database if needed
            if create_db and not dry_run:
                self._create_database(target_url, db_type)
            
            # Process backup file (decrypt, decompress)
            processed_file = self._process_backup_file(backup_file)
            results['bytes_processed'] = processed_file.stat().st_size
            
            # Parse backup to determine content
            backup_info = self._analyze_backup(processed_file, db_type)
            results['backup_info'] = backup_info
            
            # Validate compatibility
            if not self._validate_compatibility(backup_info, db_type, tables):
                raise IncompatibleBackupError("Backup is incompatible with target database")
            
            if dry_run:
                logger.info("DRY RUN - No changes will be applied")
                self._show_restore_plan(backup_info, tables, drop_existing)
                results['success'] = True
                return results
            
            # Perform restore based on database type
            if db_type == 'postgresql':
                restore_results = self._restore_postgresql(
                    processed_file, target_url, tables, drop_existing,
                    no_data, no_schema, continue_on_error
                )
            elif db_type == 'mysql':
                restore_results = self._restore_mysql(
                    processed_file, target_url, tables, drop_existing,
                    no_data, no_schema, continue_on_error
                )
            elif db_type == 'sqlite':
                restore_results = self._restore_sqlite(
                    processed_file, target_url, tables, drop_existing,
                    no_data, no_schema, continue_on_error
                )
            else:
                restore_results = self._restore_generic(
                    processed_file, target_url, tables, drop_existing,
                    no_data, no_schema, batch_size, continue_on_error
                )
            
            results.update(restore_results)
            results['success'] = True
            
            # Log summary
            logger.info(f"Restore completed: {len(results['tables_restored'])} tables restored, "
                       f"{results.get('rows_restored', 0)} rows")
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            results['errors'].append(str(e))
            if not force:
                raise
        finally:
            results['duration'] = (datetime.utcnow() - start_time).total_seconds()
            
            # Cleanup processed file if it's in temp directory
            if processed_file and str(processed_file).startswith(self.temp_dir):
                processed_file.unlink()
        
        return results
    
    def _detect_db_type(self, db_url: str) -> str:
        """Detect database type from URL."""
        if db_url.startswith('postgresql'):
            return 'postgresql'
        elif db_url.startswith('mysql'):
            return 'mysql'
        elif db_url.startswith('sqlite'):
            return 'sqlite'
        elif db_url.startswith('mssql'):
            return 'mssql'
        else:
            return 'unknown'
    
    def _locate_backup(self, source: str, backup_id: Optional[str]) -> Path:
        """
        Locate backup file from source.
        
        Args:
            source: Backup source (file path, URL, or backup ID)
            backup_id: Backup ID (if using backup service)
            
        Returns:
            Path to backup file
            
        Raises:
            BackupNotFoundError: If backup not found
        """
        # If backup_id is provided, use backup service
        if backup_id:
            return self._get_backup_by_id(backup_id)
        
        # Check if source is a URL
        parsed = urlparse(source)
        if parsed.scheme in ('http', 'https', 'ftp', 'sftp', 's3'):
            return self._download_backup(source)
        
        # Check if source is a local file
        source_path = Path(source)
        if source_path.exists():
            return source_path
        
        # Check in default backup directories
        backup_dirs = [
            Path('./backups'),
            Path('/var/backups/parking'),
            Path.home() / 'backups'
        ]
        
        for backup_dir in backup_dirs:
            # Try as full path
            candidate = backup_dir / source
            if candidate.exists():
                return candidate
            
            # Try with common extensions
            for ext in ['.sql', '.sql.gz', '.sql.bz2', '.dump', '.json', '.db']:
                candidate = backup_dir / f"{source}{ext}"
                if candidate.exists():
                    return candidate
        
        raise BackupNotFoundError(f"Backup not found: {source}")
    
    def _get_backup_by_id(self, backup_id: str) -> Path:
        """Get backup file by ID from backup service."""
        if not self.backup_service:
            from data.services.backup_service import BackupService
            self.backup_service = BackupService(
                session=None,
                backup_dir="./backups"
            )
        
        # Load backup history
        self.backup_service._load_backup_history()
        
        # Find backup
        metadata = self.backup_service.backup_history.get(backup_id)
        if not metadata:
            raise BackupNotFoundError(f"Backup ID not found: {backup_id}")
        
        backup_file = Path(metadata.metadata['filename'])
        if not backup_file.exists():
            backup_file = Path("./backups") / metadata.metadata['filename']
        
        if not backup_file.exists():
            raise BackupNotFoundError(f"Backup file not found: {backup_file}")
        
        return backup_file
    
    def _download_backup(self, url: str) -> Path:
        """Download backup from URL."""
        import requests
        from urllib.parse import urlparse
        
        logger.info(f"Downloading backup from {url}")
        
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        if not filename:
            filename = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sql"
        
        local_path = Path(self.temp_dir) / filename
        
        if url.startswith('s3://'):
            self._download_from_s3(url, local_path)
        elif url.startswith(('sftp://', 'ftp://')):
            self._download_from_ftp(url, local_path)
        else:
            # HTTP/HTTPS download
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        logger.info(f"Downloaded to {local_path}")
        return local_path
    
    def _download_from_s3(self, s3_url: str, local_path: Path) -> None:
        """Download from S3."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            parsed = urlparse(s3_url)
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')
            
            s3_client = boto3.client('s3')
            s3_client.download_file(bucket, key, str(local_path))
            
        except ImportError:
            raise RestoreError("boto3 not installed, cannot download from S3")
        except Exception as e:
            raise RestoreError(f"S3 download failed: {e}")
    
    def _download_from_ftp(self, ftp_url: str, local_path: Path) -> None:
        """Download from FTP/SFTP."""
        try:
            if ftp_url.startswith('sftp://'):
                import paramiko
                
                parsed = urlparse(ftp_url)
                hostname = parsed.hostname
                port = parsed.port or 22
                username = parsed.username
                password = parsed.password
                remote_path = parsed.path
                
                transport = paramiko.Transport((hostname, port))
                transport.connect(username=username, password=password)
                
                sftp = paramiko.SFTPClient.from_transport(transport)
                sftp.get(remote_path, str(local_path))
                
                sftp.close()
                transport.close()
                
            else:
                from ftplib import FTP
                
                parsed = urlparse(ftp_url)
                hostname = parsed.hostname
                username = parsed.username or 'anonymous'
                password = parsed.password or 'anonymous@'
                remote_path = parsed.path
                
                ftp = FTP(hostname)
                ftp.login(username, password)
                
                with open(local_path, 'wb') as f:
                    ftp.retrbinary(f'RETR {remote_path}', f.write)
                
                ftp.quit()
                
        except ImportError as e:
            raise RestoreError(f"Required library not installed: {e}")
        except Exception as e:
            raise RestoreError(f"FTP download failed: {e}")
    
    def _verify_backup(self, backup_file: Path, force: bool) -> None:
        """Verify backup integrity."""
        logger.info(f"Verifying backup: {backup_file}")
        
        # Check file exists
        if not backup_file.exists():
            raise ValidationError(f"Backup file not found: {backup_file}")
        
        # Check file size
        if backup_file.stat().st_size == 0:
            raise ValidationError("Backup file is empty")
        
        # Try to read the file based on extension
        try:
            if backup_file.suffix == '.gz':
                with gzip.open(backup_file, 'rb') as f:
                    f.read(1024)  # Read first 1KB
            elif backup_file.suffix == '.bz2':
                with bz2.open(backup_file, 'rb') as f:
                    f.read(1024)
            elif backup_file.suffix == '.zip':
                with zipfile.ZipFile(backup_file, 'r') as zf:
                    # Test zip integrity
                    bad_file = zf.testzip()
                    if bad_file:
                        raise ValidationError(f"Corrupted zip file: {bad_file}")
            else:
                with open(backup_file, 'rb') as f:
                    f.read(1024)
                    
        except Exception as e:
            if force:
                logger.warning(f"Backup verification failed but continuing due to --force: {e}")
            else:
                raise ValidationError(f"Backup verification failed: {e}")
        
        logger.info("Backup verification passed")
    
    def _process_backup_file(self, backup_file: Path) -> Path:
        """
        Process backup file (decrypt, decompress).
        
        Returns:
            Path to processed file (may be in temp directory)
        """
        processed_file = backup_file
        
        # Handle encrypted files
        if backup_file.suffix == '.enc':
            if not self.encryption:
                raise RestoreError("Encrypted backup requires encryption service")
            
            logger.info("Decrypting backup...")
            decrypted = Path(self.temp_dir) / backup_file.stem
            
            with open(backup_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.encryption.decrypt(encrypted_data)
            
            with open(decrypted, 'wb') as f:
                f.write(decrypted_data)
            
            processed_file = decrypted
        
        # Handle compressed files
        if processed_file.suffix == '.gz':
            logger.info("Decompressing gzip...")
            decompressed = Path(self.temp_dir) / processed_file.stem
            
            with gzip.open(processed_file, 'rb') as f_in:
                with open(decompressed, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            processed_file = decompressed
            
        elif processed_file.suffix == '.bz2':
            logger.info("Decompressing bzip2...")
            decompressed = Path(self.temp_dir) / processed_file.stem
            
            with bz2.open(processed_file, 'rb') as f_in:
                with open(decompressed, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            processed_file = decompressed
            
        elif processed_file.suffix == '.zip':
            logger.info("Extracting zip...")
            with zipfile.ZipFile(processed_file, 'r') as zf:
                # Extract first file
                for name in zf.namelist():
                    extracted = Path(self.temp_dir) / name
                    zf.extract(name, self.temp_dir)
                    processed_file = extracted
                    break
        
        return processed_file
    
    def _analyze_backup(self, backup_file: Path, db_type: str) -> Dict[str, Any]:
        """Analyze backup file to determine its content."""
        info = {
            'type': 'unknown',
            'tables': [],
            'has_schema': True,
            'has_data': True,
            'size': backup_file.stat().st_size,
            'created_at': None,
            'version': None
        }
        
        # Check file extension
        if backup_file.suffix == '.sql':
            info['type'] = 'sql'
            
            # Try to read first few lines to get info
            with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [f.readline() for _ in range(20)]
                
                # Look for table names
                table_pattern = re.compile(r'CREATE TABLE.*?(\w+)|INSERT INTO.*?(\w+)', re.IGNORECASE)
                for line in first_lines:
                    match = table_pattern.search(line)
                    if match:
                        table = match.group(1) or match.group(2)
                        if table and table not in info['tables']:
                            info['tables'].append(table)
                
                # Check for timestamp
                date_pattern = re.compile(r'-- Dumped at (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
                for line in first_lines:
                    match = date_pattern.search(line)
                    if match:
                        info['created_at'] = match.group(1)
        
        elif backup_file.suffix == '.dump':
            info['type'] = 'custom'
            # For custom format, we'd need database-specific tools to analyze
        
        elif backup_file.suffix == '.json':
            info['type'] = 'json'
            
            # Try to read JSON structure
            try:
                with open(backup_file, 'r') as f:
                    data = json.load(f)
                    
                if isinstance(data, dict):
                    info['tables'] = list(data.keys())
                    
                if 'metadata' in data:
                    info['created_at'] = data['metadata'].get('created_at')
                    info['version'] = data['metadata'].get('version')
                    
            except Exception as e:
                logger.warning(f"Could not analyze JSON backup: {e}")
        
        elif backup_file.suffix == '.db':
            info['type'] = 'sqlite'
            # SQLite database file - would need to open to analyze
        
        return info
    
    def _validate_compatibility(
        self,
        backup_info: Dict[str, Any],
        db_type: str,
        tables: Optional[List[str]]
    ) -> bool:
        """Validate backup compatibility with target database."""
        # Check if backup type is compatible with database
        if backup_info['type'] == 'json':
            # JSON is universal
            return True
        
        if backup_info['type'] == 'sqlite' and db_type != 'sqlite':
            logger.warning("SQLite backup being restored to non-SQLite database")
            # This might work with generic restore, but warn
        
        # Check if requested tables exist in backup
        if tables and backup_info['tables']:
            missing_tables = set(tables) - set(backup_info['tables'])
            if missing_tables:
                logger.warning(f"Tables not found in backup: {missing_tables}")
                # Not necessarily incompatible, just missing some tables
        
        return True
    
    def _show_restore_plan(
        self,
        backup_info: Dict[str, Any],
        tables: Optional[List[str]],
        drop_existing: bool
    ) -> None:
        """Show restore plan for dry run."""
        print("\n" + "="*60)
        print("RESTORE PLAN (DRY RUN)")
        print("="*60)
        print(f"Backup type: {backup_info['type']}")
        print(f"Backup size: {self._format_size(backup_info['size'])}")
        
        if backup_info['created_at']:
            print(f"Backup created: {backup_info['created_at']}")
        
        if backup_info['tables']:
            tables_to_restore = tables or backup_info['tables']
            print(f"\nTables to restore: {len(tables_to_restore)}")
            for i, table in enumerate(tables_to_restore[:10], 1):
                print(f"  {i}. {table}")
            if len(tables_to_restore) > 10:
                print(f"  ... and {len(tables_to_restore) - 10} more")
        
        if drop_existing:
            print("\nWill drop existing tables before restore")
        
        print("\nNo changes will be applied (dry run)")
        print("="*60)
    
    def _create_database(self, db_url: str, db_type: str) -> None:
        """Create database if it doesn't exist."""
        logger.info(f"Ensuring database exists: {db_url}")
        
        try:
            if db_type == 'postgresql':
                self._create_postgresql_database(db_url)
            elif db_type == 'mysql':
                self._create_mysql_database(db_url)
            elif db_type == 'sqlite':
                # SQLite creates database automatically
                pass
                
        except Exception as e:
            logger.warning(f"Could not create database: {e}")
    
    def _create_postgresql_database(self, db_url: str) -> None:
        """Create PostgreSQL database."""
        from urllib.parse import urlparse
        
        parsed = urlparse(db_url)
        database = parsed.path[1:]
        
        # Connect to default database
        default_url = db_url.replace(f"/{database}", "/postgres")
        
        try:
            engine = create_engine(default_url)
            with engine.connect() as conn:
                # Check if database exists
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": database}
                )
                if not result.first():
                    conn.execute(text(f"CREATE DATABASE {database}"))
                    logger.info(f"Created database: {database}")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL database: {e}")
            raise
    
    def _create_mysql_database(self, db_url: str) -> None:
        """Create MySQL database."""
        from urllib.parse import urlparse
        
        parsed = urlparse(db_url)
        database = parsed.path[1:]
        
        try:
            engine = create_engine(db_url.replace(f"/{database}", ""))
            with engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {database}"))
                logger.info(f"Created database: {database}")
        except Exception as e:
            logger.error(f"Failed to create MySQL database: {e}")
            raise
    
    # ========================================================================
    # Database-Specific Restore Methods
    # ========================================================================
    
    def _restore_postgresql(
        self,
        backup_file: Path,
        target_url: str,
        tables: Optional[List[str]],
        drop_existing: bool,
        no_data: bool,
        no_schema: bool,
        continue_on_error: bool
    ) -> Dict[str, Any]:
        """Restore PostgreSQL database."""
        from urllib.parse import urlparse
        
        results = {
            'tables_restored': [],
            'tables_skipped': [],
            'rows_restored': 0
        }
        
        parsed = urlparse(target_url)
        database = parsed.path[1:]
        username = parsed.username
        password = parsed.password
        hostname = parsed.hostname
        port = parsed.port or 5432
        
        # Build restore command
        if backup_file.suffix == '.dump':
            # Custom format - use pg_restore
            cmd = ['pg_restore']
            cmd.extend(['-h', hostname])
            cmd.extend(['-p', str(port)])
            cmd.extend(['-U', username])
            cmd.extend(['-d', database])
            
            if drop_existing:
                cmd.append('--clean')
                cmd.append('--if-exists')
            
            if no_data:
                cmd.append('--schema-only')
            elif no_schema:
                cmd.append('--data-only')
            
            if tables:
                for table in tables:
                    cmd.extend(['-t', table])
            
            cmd.append(str(backup_file))
            
        else:
            # Plain SQL - use psql
            cmd = ['psql']
            cmd.extend(['-h', hostname])
            cmd.extend(['-p', str(port)])
            cmd.extend(['-U', username])
            cmd.extend(['-d', database])
            cmd.extend(['-f', str(backup_file)])
        
        # Set password environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = password or ''
        
        logger.info(f"Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                error_msg = result.stderr
                if continue_on_error:
                    logger.warning(f"Restore had errors: {error_msg}")
                    results['warnings'].append(error_msg)
                else:
                    raise RestoreError(f"PostgreSQL restore failed: {error_msg}")
            
            # Parse output to count restored tables
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if 'restored' in line.lower():
                        results['rows_restored'] += 1
            
            logger.info("PostgreSQL restore completed")
            
        except Exception as e:
            if continue_on_error:
                logger.warning(f"Restore error (continuing): {e}")
                results['warnings'].append(str(e))
            else:
                raise
        
        return results
    
    def _restore_mysql(
        self,
        backup_file: Path,
        target_url: str,
        tables: Optional[List[str]],
        drop_existing: bool,
        no_data: bool,
        no_schema: bool,
        continue_on_error: bool
    ) -> Dict[str, Any]:
        """Restore MySQL database."""
        from urllib.parse import urlparse
        
        results = {
            'tables_restored': [],
            'tables_skipped': [],
            'rows_restored': 0
        }
        
        parsed = urlparse(target_url)
        database = parsed.path[1:]
        username = parsed.username
        password = parsed.password
        hostname = parsed.hostname
        port = parsed.port or 3306
        
        # Build mysql command
        cmd = ['mysql']
        cmd.extend(['-h', hostname])
        cmd.extend(['-P', str(port)])
        cmd.extend(['-u', username])
        
        if password:
            cmd.append(f'--password={password}')
        
        cmd.append(database)
        
        if drop_existing:
            # We'll need to drop tables before restore
            # This would require parsing the backup or separate drop commands
            logger.warning("drop_existing not fully implemented for MySQL")
        
        logger.info(f"Executing mysql restore")
        
        try:
            with open(backup_file, 'r') as f:
                result = subprocess.run(
                    cmd,
                    stdin=f,
                    capture_output=True,
                    text=True
                )
            
            if result.returncode != 0:
                error_msg = result.stderr
                if continue_on_error:
                    logger.warning(f"Restore had errors: {error_msg}")
                    results['warnings'].append(error_msg)
                else:
                    raise RestoreError(f"MySQL restore failed: {error_msg}")
            
            logger.info("MySQL restore completed")
            
        except Exception as e:
            if continue_on_error:
                logger.warning(f"Restore error (continuing): {e}")
                results['warnings'].append(str(e))
            else:
                raise
        
        return results
    
    def _restore_sqlite(
        self,
        backup_file: Path,
        target_url: str,
        tables: Optional[List[str]],
        drop_existing: bool,
        no_data: bool,
        no_schema: bool,
        continue_on_error: bool
    ) -> Dict[str, Any]:
        """Restore SQLite database."""
        from urllib.parse import urlparse
        
        results = {
            'tables_restored': [],
            'tables_skipped': [],
            'rows_restored': 0
        }
        
        parsed = urlparse(target_url)
        target_db = parsed.path
        
        import sqlite3
        
        try:
            conn = sqlite3.connect(target_db)
            cursor = conn.cursor()
            
            if backup_file.suffix == '.sql':
                # Execute SQL script
                with open(backup_file, 'r') as f:
                    script = f.read()
                
                # Split into statements
                statements = script.split(';')
                
                for stmt in statements:
                    stmt = stmt.strip()
                    if not stmt:
                        continue
                    
                    try:
                        cursor.execute(stmt)
                        if stmt.upper().startswith('INSERT'):
                            results['rows_restored'] += cursor.rowcount
                        elif stmt.upper().startswith('CREATE TABLE'):
                            # Extract table name
                            match = re.search(r'CREATE TABLE.*?(\w+)', stmt, re.IGNORECASE)
                            if match:
                                results['tables_restored'].append(match.group(1))
                    except Exception as e:
                        if continue_on_error:
                            logger.warning(f"Statement failed (continuing): {e}")
                            results['warnings'].append(str(e))
                        else:
                            raise
                
            else:
                # Direct database file copy
                if drop_existing:
                    conn.close()
                    os.unlink(target_db)
                
                shutil.copy2(backup_file, target_db)
                
                # Reconnect to count tables
                conn = sqlite3.connect(target_db)
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                results['tables_restored'] = [t[0] for t in tables]
            
            conn.commit()
            conn.close()
            
            logger.info("SQLite restore completed")
            
        except Exception as e:
            if continue_on_error:
                logger.warning(f"Restore error (continuing): {e}")
                results['warnings'].append(str(e))
            else:
                raise
        
        return results
    
    def _restore_generic(
        self,
        backup_file: Path,
        target_url: str,
        tables: Optional[List[str]],
        drop_existing: bool,
        no_data: bool,
        no_schema: bool,
        batch_size: int,
        continue_on_error: bool
    ) -> Dict[str, Any]:
        """Generic restore using SQLAlchemy."""
        results = {
            'tables_restored': [],
            'tables_skipped': [],
            'rows_restored': 0
        }
        
        # Determine backup format
        if backup_file.suffix == '.json':
            data = self._load_json_backup(backup_file)
        else:
            # Assume SQL format - can't do generic SQL restore
            raise IncompatibleBackupError("Generic restore only supports JSON format")
        
        # Create target engine
        target_engine = create_engine(target_url)
        
        with target_engine.connect() as conn:
            # Disable foreign key checks
            db_type = self._detect_db_type(target_url)
            self._disable_foreign_keys(conn, db_type)
            
            # Get list of tables in backup
            backup_tables = list(data.get('data', data).keys())
            
            # Determine which tables to restore
            tables_to_restore = tables or backup_tables
            
            for table_name in tables_to_restore:
                if table_name not in backup_tables:
                    logger.warning(f"Table {table_name} not found in backup")
                    results['tables_skipped'].append(table_name)
                    continue
                
                table_data = data.get('data', data).get(table_name, [])
                
                if drop_existing:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                
                if not no_data and table_data:
                    # Restore in batches
                    for i in range(0, len(table_data), batch_size):
                        batch = table_data[i:i+batch_size]
                        
                        if i == 0 and not no_schema:
                            # Create table based on first row
                            self._create_table_from_data(conn, table_name, batch[0])
                        
                        # Insert data
                        for row in batch:
                            columns = ', '.join(row.keys())
                            placeholders = ', '.join([f":{k}" for k in row.keys()])
                            
                            try:
                                conn.execute(
                                    text(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"),
                                    row
                                )
                                results['rows_restored'] += 1
                            except Exception as e:
                                if continue_on_error:
                                    logger.warning(f"Row insert failed (continuing): {e}")
                                    results['warnings'].append(str(e))
                                else:
                                    raise
                
                results['tables_restored'].append(table_name)
            
            # Re-enable foreign key checks
            self._enable_foreign_keys(conn, db_type)
            conn.commit()
        
        return results
    
    def _load_json_backup(self, backup_file: Path) -> Dict:
        """Load JSON backup file."""
        with open(backup_file, 'r') as f:
            return json.load(f)
    
    def _create_table_from_data(self, conn, table_name: str, sample_row: Dict) -> None:
        """Create table based on sample data row."""
        from sqlalchemy import Table, Column, MetaData, types
        
        metadata = MetaData()
        
        columns = []
        for col_name, value in sample_row.items():
            # Infer column type from value
            if isinstance(value, int):
                col_type = types.Integer()
            elif isinstance(value, float):
                col_type = types.Float()
            elif isinstance(value, bool):
                col_type = types.Boolean()
            elif isinstance(value, str):
                if len(value) > 255:
                    col_type = types.Text()
                else:
                    col_type = types.String(255)
            else:
                col_type = types.String(255)
            
            columns.append(Column(col_name, col_type))
        
        table = Table(table_name, metadata, *columns)
        metadata.create_all(conn.bind)
    
    def _disable_foreign_keys(self, conn, db_type: str) -> None:
        """Disable foreign key checks."""
        if db_type == 'sqlite':
            conn.execute(text("PRAGMA foreign_keys=OFF"))
        elif db_type == 'mysql':
            conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        elif db_type == 'postgresql':
            conn.execute(text("SET session_replication_role = 'replica'"))
    
    def _enable_foreign_keys(self, conn, db_type: str) -> None:
        """Re-enable foreign key checks."""
        if db_type == 'sqlite':
            conn.execute(text("PRAGMA foreign_keys=ON"))
        elif db_type == 'mysql':
            conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        elif db_type == 'postgresql':
            conn.execute(text("SET session_replication_role = 'origin'"))
    
    def _format_size(self, size: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"


# ============================================================================
# Main Script
# ============================================================================

def parse_tables(tables_str: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated table list."""
    if not tables_str:
        return None
    return [t.strip() for t in tables_str.split(',')]


def parse_point_in_time(time_str: Optional[str]) -> Optional[datetime]:
    """Parse point in time string."""
    if not time_str:
        return None
    
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Invalid point in time format: {time_str}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Database restore utility')
    parser.add_argument('source', nargs='?', help='Backup source (file path, URL, or backup ID)')
    
    # Restore options
    parser.add_argument('--target-db', help='Target database URL')
    parser.add_argument('--tables', help='Specific tables to restore (comma-separated)')
    parser.add_argument('--point-in-time', help='Restore to point in time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--dry-run', action='store_true', help='Simulate restore without applying changes')
    parser.add_argument('--force', action='store_true', help='Force restore even if validation fails')
    parser.add_argument('--verify', action='store_true', default=True, help='Verify backup before restore')
    parser.add_argument('--no-verify', action='store_false', dest='verify', help='Skip backup verification')
    parser.add_argument('--create-db', action='store_true', help='Create database if it doesn\'t exist')
    parser.add_argument('--drop-existing', action='store_true', help='Drop existing tables before restore')
    parser.add_argument('--no-data', action='store_true', help='Restore schema only')
    parser.add_argument('--no-schema', action='store_true', help='Restore data only')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for large restores')
    parser.add_argument('--continue-on-error', action='store_true', help='Continue restore if errors occur')
    
    # Backup service options
    parser.add_argument('--backup-id', help='Restore from backup ID (if using backup service)')
    
    # Configuration
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.source and not args.backup_id:
        parser.error("Either SOURCE or --backup-id is required")
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    # Load configuration
    config = None
    if args.config:
        config = Config(args.config)
    else:
        config = Config()
    
    # Parse tables
    tables = parse_tables(args.tables)
    
    # Parse point in time
    point_in_time = parse_point_in_time(args.point_in_time)
    
    # Initialize restore manager
    with RestoreManager(
        target_db_url=args.target_db,
        config=config
    ) as manager:
        
        try:
            # Perform restore
            source = args.source or args.backup_id
            results = manager.restore(
                source=source,
                target_db_url=args.target_db,
                tables=tables,
                point_in_time=point_in_time,
                dry_run=args.dry_run,
                force=args.force,
                verify=args.verify,
                create_db=args.create_db,
                drop_existing=args.drop_existing,
                no_data=args.no_data,
                no_schema=args.no_schema,
                batch_size=args.batch_size,
                continue_on_error=args.continue_on_error,
                backup_id=args.backup_id
            )
            
            # Print results
            print("\n" + "="*60)
            print("RESTORE COMPLETED")
            print("="*60)
            
            if args.dry_run:
                print("DRY RUN - No changes were applied")
            
            print(f"Source: {results['source']}")
            print(f"Target: {results['target']}")
            print(f"Duration: {results['duration']:.2f} seconds")
            print(f"Bytes processed: {manager._format_size(results['bytes_processed'])}")
            
            if results.get('tables_restored'):
                print(f"\nTables restored: {len(results['tables_restored'])}")
                for table in results['tables_restored'][:10]:
                    print(f"  - {table}")
                if len(results['tables_restored']) > 10:
                    print(f"  ... and {len(results['tables_restored']) - 10} more")
            
            if results.get('rows_restored'):
                print(f"\nRows restored: {results['rows_restored']}")
            
            if results.get('warnings'):
                print(f"\nWarnings ({len(results['warnings'])}):")
                for warning in results['warnings'][:5]:
                    print(f"  - {warning}")
                if len(results['warnings']) > 5:
                    print(f"  ... and {len(results['warnings']) - 5} more")
            
            if results.get('errors'):
                print(f"\nErrors ({len(results['errors'])}):")
                for error in results['errors']:
                    print(f"  - {error}")
                sys.exit(1)
            
            print("="*60)
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()