#!/usr/bin/env python3
"""
Database backup script for the parking management system.

This script provides comprehensive backup and restore functionality including:
- Full, incremental, and differential backups
- Multiple backup formats (SQL, JSON, custom)
- Compression (gzip, bzip2, zip)
- Encryption support
- Backup verification
- Automated backup scheduling
- Remote backup storage (S3, SFTP, local)
- Backup rotation and retention policies

Usage:
    python backup_db.py [command] [options]

Commands:
    backup          Create a new backup
    restore         Restore from a backup
    list            List available backups
    info            Show backup information
    verify          Verify backup integrity
    delete          Delete old backups
    schedule        Schedule automatic backups
    cleanup         Clean up old backups based on retention policy

Options:
    --type TYPE     Backup type (full, incremental, differential) [default: full]
    --format FMT    Backup format (sql, json, custom) [default: sql]
    --compress C    Compression (gzip, bzip2, zip, none) [default: gzip]
    --encrypt       Encrypt the backup
    --db-url URL    Database connection URL
    --backup-id ID  Backup ID for restore/info/verify
    --output DIR    Output directory [default: ./backups]
    --remote URL    Remote storage URL (s3://, sftp://, etc.)
    --retention N   Number of days to keep backups [default: 30]
    --keep N        Number of backups to keep [default: 10]
    --verify        Verify backup after creation
    --dry-run       Show what would be done without actually doing it
    --verbose       Verbose output
    --config FILE   Configuration file
"""

import os
import sys
import argparse
import logging
import subprocess
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import hashlib
import gzip
import bz2
import zipfile
import tarfile
import pickle
import sqlite3
from enum import Enum

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from data.services import BackupService, EncryptionService, NotificationService
from data.services.backup_service import (
    BackupType, BackupFormat, BackupCompression, BackupMetadata
)
from utils.config import Config
from utils.logging import setup_logging

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Backup Manager
# ============================================================================

class BackupManager:
    """
    Manages database backup and restore operations.
    
    Provides comprehensive backup functionality with support for multiple
    backup types, formats, compression, encryption, and remote storage.
    """
    
    def __init__(
        self,
        db_url: str,
        backup_dir: str = "./backups",
        config: Optional[Config] = None,
        encryption_service: Optional[EncryptionService] = None,
        notification_service: Optional[NotificationService] = None
    ):
        """
        Initialize the backup manager.
        
        Args:
            db_url: Database connection URL
            backup_dir: Directory to store backups
            config: Configuration object
            encryption_service: Optional encryption service
            notification_service: Optional notification service
        """
        self.db_url = db_url
        self.backup_dir = Path(backup_dir)
        self.config = config or Config()
        self.encryption = encryption_service
        self.notifications = notification_service
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create engine
        self.engine = create_engine(db_url)
        
        # Determine database type
        self.db_type = self._detect_db_type()
        
        # Initialize backup service
        from data.services.backup_service import BackupService
        self.backup_service = BackupService(
            session=None,  # Will be created per operation
            backup_dir=str(self.backup_dir),
            encryption_service=encryption_service,
            notification_service=notification_service
        )
        
        # Load backup history
        self.backup_history = self._load_backup_history()
        
        logger.info(f"BackupManager initialized for {self.db_type} database")
    
    def _detect_db_type(self) -> str:
        """Detect database type from URL."""
        if self.db_url.startswith('postgresql'):
            return 'postgresql'
        elif self.db_url.startswith('mysql'):
            return 'mysql'
        elif self.db_url.startswith('sqlite'):
            return 'sqlite'
        elif self.db_url.startswith('mssql'):
            return 'mssql'
        else:
            return 'unknown'
    
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
    
    # ========================================================================
    # Backup Operations
    # ========================================================================
    
    def create_backup(
        self,
        backup_type: str = 'full',
        format: str = 'sql',
        compression: str = 'gzip',
        encrypt: bool = False,
        verify: bool = False,
        output_dir: Optional[str] = None,
        remote_url: Optional[str] = None,
        tables: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Optional[BackupMetadata]:
        """
        Create a database backup.
        
        Args:
            backup_type: Type of backup (full, incremental, differential)
            format: Backup format (sql, json, custom)
            compression: Compression type
            encrypt: Whether to encrypt the backup
            verify: Whether to verify after creation
            output_dir: Output directory
            remote_url: Remote storage URL
            tables: Specific tables to backup
            dry_run: Show what would be done without actually doing it
            
        Returns:
            Backup metadata if successful
        """
        logger.info(f"Creating {backup_type} backup...")
        
        if dry_run:
            logger.info(f"[DRY RUN] Would create {backup_type} backup")
            return None
        
        # Set output directory
        if output_dir:
            backup_dir = Path(output_dir)
            backup_dir.mkdir(parents=True, exist_ok=True)
        else:
            backup_dir = self.backup_dir
        
        # Generate backup ID
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_id = f"backup_{timestamp}"
        
        try:
            start_time = datetime.utcnow()
            
            # Perform backup based on database type
            if self.db_type == 'postgresql':
                backup_file = self._backup_postgresql(
                    backup_id, backup_dir, format, compression, encrypt, tables
                )
            elif self.db_type == 'mysql':
                backup_file = self._backup_mysql(
                    backup_id, backup_dir, format, compression, encrypt, tables
                )
            elif self.db_type == 'sqlite':
                backup_file = self._backup_sqlite(
                    backup_id, backup_dir, format, compression, encrypt, tables
                )
            else:
                backup_file = self._backup_generic(
                    backup_id, backup_dir, format, compression, encrypt, tables
                )
            
            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Calculate checksum
            checksum = self._calculate_checksum(backup_file)
            
            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type=backup_type,
                format=format,
                compression=compression,
                tables=tables or [],
                size=backup_file.stat().st_size,
                checksum=checksum,
                created_at=start_time,
                duration=duration,
                status='completed',
                encrypted=encrypt,
                metadata={
                    'filename': backup_file.name,
                    'db_type': self.db_type,
                    'path': str(backup_file)
                }
            )
            
            # Save to history
            self.backup_history[backup_id] = metadata
            self._save_backup_history()
            
            # Verify if requested
            if verify:
                self.verify_backup(backup_id)
            
            # Upload to remote if specified
            if remote_url:
                self._upload_to_remote(backup_file, remote_url)
            
            logger.info(f"Backup created successfully: {backup_file} ({metadata.size} bytes)")
            
            # Send notification
            self._send_notification(
                'backup_success',
                f"Backup {backup_id} completed successfully",
                {'backup_id': backup_id, 'size': metadata.size}
            )
            
            return metadata
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            
            # Send notification
            self._send_notification(
                'backup_failed',
                f"Backup failed: {str(e)}",
                {'backup_id': backup_id, 'error': str(e)}
            )
            
            raise
    
    def _backup_postgresql(
        self,
        backup_id: str,
        backup_dir: Path,
        format: str,
        compression: str,
        encrypt: bool,
        tables: Optional[List[str]]
    ) -> Path:
        """Backup PostgreSQL database using pg_dump."""
        from urllib.parse import urlparse
        
        # Parse database URL
        parsed = urlparse(self.db_url)
        database = parsed.path[1:]  # Remove leading '/'
        username = parsed.username
        password = parsed.password
        hostname = parsed.hostname
        port = parsed.port or 5432
        
        # Build output filename
        if format == 'sql':
            ext = '.sql'
        elif format == 'custom':
            ext = '.dump'
        else:
            ext = '.sql'
        
        filename = backup_dir / f"{backup_id}{ext}"
        
        # Build pg_dump command
        cmd = ['pg_dump']
        
        # Add connection parameters
        cmd.extend(['-h', hostname])
        cmd.extend(['-p', str(port)])
        cmd.extend(['-U', username])
        cmd.extend(['-d', database])
        
        # Add format
        if format == 'custom':
            cmd.extend(['-Fc'])  # Custom format
        elif format == 'directory':
            cmd.extend(['-Fd'])  # Directory format
        else:
            cmd.extend(['-Fp'])  # Plain SQL
        
        # Add table filters
        if tables:
            for table in tables:
                cmd.extend(['-t', table])
        
        # Add verbose option
        cmd.append('-v')
        
        # Set password environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        # Execute command
        with open(filename, 'w') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
        
        if result.returncode != 0:
            raise Exception(f"pg_dump failed: {result.stderr}")
        
        # Apply compression
        if compression != 'none':
            filename = self._compress_file(filename, compression)
        
        # Apply encryption
        if encrypt and self.encryption:
            filename = self._encrypt_file(filename)
        
        return filename
    
    def _backup_mysql(
        self,
        backup_id: str,
        backup_dir: Path,
        format: str,
        compression: str,
        encrypt: bool,
        tables: Optional[List[str]]
    ) -> Path:
        """Backup MySQL database using mysqldump."""
        from urllib.parse import urlparse
        
        # Parse database URL
        parsed = urlparse(self.db_url)
        database = parsed.path[1:]  # Remove leading '/'
        username = parsed.username
        password = parsed.password
        hostname = parsed.hostname
        port = parsed.port or 3306
        
        # Build output filename
        filename = backup_dir / f"{backup_id}.sql"
        
        # Build mysqldump command
        cmd = ['mysqldump']
        
        # Add connection parameters
        cmd.extend(['-h', hostname])
        cmd.extend(['-P', str(port)])
        cmd.extend(['-u', username])
        
        # Add password (using --password= format)
        if password:
            cmd.append(f'--password={password}')
        
        # Add database
        cmd.append(database)
        
        # Add table filters
        if tables:
            cmd.extend(tables)
        
        # Add options
        cmd.append('--add-drop-table')
        cmd.append('--create-options')
        cmd.append('--quote-names')
        cmd.append('--routines')
        cmd.append('--triggers')
        
        # Execute command
        with open(filename, 'w') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True
            )
        
        if result.returncode != 0:
            raise Exception(f"mysqldump failed: {result.stderr}")
        
        # Apply compression
        if compression != 'none':
            filename = self._compress_file(filename, compression)
        
        # Apply encryption
        if encrypt and self.encryption:
            filename = self._encrypt_file(filename)
        
        return filename
    
    def _backup_sqlite(
        self,
        backup_id: str,
        backup_dir: Path,
        format: str,
        compression: str,
        encrypt: bool,
        tables: Optional[List[str]]
    ) -> Path:
        """Backup SQLite database."""
        from urllib.parse import urlparse
        
        # Parse database URL
        parsed = urlparse(self.db_url)
        db_path = parsed.path
        
        if not os.path.exists(db_path):
            raise Exception(f"SQLite database not found: {db_path}")
        
        # Build output filename
        if format == 'sql':
            filename = backup_dir / f"{backup_id}.sql"
            
            # Use .dump command to generate SQL
            conn = sqlite3.connect(db_path)
            with open(filename, 'w') as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n")
            conn.close()
            
        elif format == 'binary':
            # Direct copy of database file
            ext = '.db'
            if compression != 'none':
                ext += '.gz'
            if encrypt:
                ext += '.enc'
            
            filename = backup_dir / f"{backup_id}{ext}"
            shutil.copy2(db_path, filename)
            
        else:
            # Default to binary
            filename = backup_dir / f"{backup_id}.db"
            shutil.copy2(db_path, filename)
        
        # Apply compression
        if compression != 'none' and format != 'binary':
            filename = self._compress_file(filename, compression)
        
        # Apply encryption
        if encrypt and self.encryption:
            filename = self._encrypt_file(filename)
        
        return filename
    
    def _backup_generic(
        self,
        backup_id: str,
        backup_dir: Path,
        format: str,
        compression: str,
        encrypt: bool,
        tables: Optional[List[str]]
    ) -> Path:
        """Generic backup using SQLAlchemy."""
        import json
        from sqlalchemy import inspect
        
        filename = backup_dir / f"{backup_id}.json"
        data = {}
        
        # Get all tables
        inspector = inspect(self.engine)
        all_tables = tables or inspector.get_table_names()
        
        with self.engine.connect() as conn:
            for table in all_tables:
                result = conn.execute(text(f"SELECT * FROM {table}"))
                rows = [dict(row._mapping) for row in result]
                
                # Convert datetime objects to strings
                for row in rows:
                    for key, value in row.items():
                        if hasattr(value, 'isoformat'):
                            row[key] = value.isoformat()
                
                data[table] = rows
        
        # Write JSON
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Apply compression
        if compression != 'none':
            filename = self._compress_file(filename, compression)
        
        # Apply encryption
        if encrypt and self.encryption:
            filename = self._encrypt_file(filename)
        
        return filename
    
    def _compress_file(self, filepath: Path, compression: str) -> Path:
        """Compress a file."""
        if compression == 'gzip':
            compressed = filepath.with_suffix(filepath.suffix + '.gz')
            with open(filepath, 'rb') as f_in:
                with gzip.open(compressed, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            filepath.unlink()  # Remove original
            return compressed
            
        elif compression == 'bzip2':
            compressed = filepath.with_suffix(filepath.suffix + '.bz2')
            with open(filepath, 'rb') as f_in:
                with bz2.open(compressed, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            filepath.unlink()
            return compressed
            
        elif compression == 'zip':
            compressed = filepath.with_suffix(filepath.suffix + '.zip')
            with zipfile.ZipFile(compressed, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(filepath, filepath.name)
            filepath.unlink()
            return compressed
        
        return filepath
    
    def _encrypt_file(self, filepath: Path) -> Path:
        """Encrypt a file."""
        if not self.encryption:
            logger.warning("Encryption service not available, skipping encryption")
            return filepath
        
        encrypted = filepath.with_suffix(filepath.suffix + '.enc')
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        encrypted_data = self.encryption.encrypt(data)
        
        with open(encrypted, 'wb') as f:
            f.write(encrypted_data)
        
        filepath.unlink()  # Remove original
        return encrypted
    
    def _calculate_checksum(self, filepath: Path) -> str:
        """Calculate SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _upload_to_remote(self, filepath: Path, remote_url: str) -> None:
        """Upload backup to remote storage."""
        logger.info(f"Uploading to remote storage: {remote_url}")
        
        if remote_url.startswith('s3://'):
            self._upload_to_s3(filepath, remote_url)
        elif remote_url.startswith('sftp://'):
            self._upload_to_sftp(filepath, remote_url)
        elif remote_url.startswith('ftp://'):
            self._upload_to_ftp(filepath, remote_url)
        else:
            logger.warning(f"Unsupported remote URL: {remote_url}")
    
    def _upload_to_s3(self, filepath: Path, s3_url: str) -> None:
        """Upload to S3-compatible storage."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            from urllib.parse import urlparse
            
            parsed = urlparse(s3_url)
            bucket = parsed.netloc
            key = parsed.path.lstrip('/')
            
            if not key:
                key = filepath.name
            else:
                key = f"{key}/{filepath.name}"
            
            # Create S3 client
            s3_client = boto3.client('s3')
            
            # Upload file
            s3_client.upload_file(str(filepath), bucket, key)
            
            logger.info(f"Uploaded to s3://{bucket}/{key}")
            
        except ImportError:
            logger.error("boto3 not installed, cannot upload to S3")
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
    
    def _upload_to_sftp(self, filepath: Path, sftp_url: str) -> None:
        """Upload to SFTP server."""
        try:
            import paramiko
            from urllib.parse import urlparse
            
            parsed = urlparse(sftp_url)
            hostname = parsed.hostname
            port = parsed.port or 22
            username = parsed.username
            password = parsed.password
            remote_path = parsed.path
            
            # Connect to SFTP
            transport = paramiko.Transport((hostname, port))
            transport.connect(username=username, password=password)
            
            sftp = paramiko.SFTPClient.from_transport(transport)
            
            # Upload file
            remote_file = f"{remote_path}/{filepath.name}" if remote_path else filepath.name
            sftp.put(str(filepath), remote_file)
            
            sftp.close()
            transport.close()
            
            logger.info(f"Uploaded to {sftp_url}")
            
        except ImportError:
            logger.error("paramiko not installed, cannot upload to SFTP")
        except Exception as e:
            logger.error(f"SFTP upload failed: {e}")
    
    def _upload_to_ftp(self, filepath: Path, ftp_url: str) -> None:
        """Upload to FTP server."""
        try:
            from ftplib import FTP
            from urllib.parse import urlparse
            
            parsed = urlparse(ftp_url)
            hostname = parsed.hostname
            username = parsed.username or 'anonymous'
            password = parsed.password or 'anonymous@'
            remote_path = parsed.path
            
            # Connect to FTP
            ftp = FTP(hostname)
            ftp.login(username, password)
            
            # Change to remote directory
            if remote_path:
                ftp.cwd(remote_path)
            
            # Upload file
            with open(filepath, 'rb') as f:
                ftp.storbinary(f'STOR {filepath.name}', f)
            
            ftp.quit()
            
            logger.info(f"Uploaded to {ftp_url}")
            
        except Exception as e:
            logger.error(f"FTP upload failed: {e}")
    
    def _send_notification(self, notification_type: str, message: str, data: Dict) -> None:
        """Send notification about backup operation."""
        if not self.notifications:
            return
        
        # Send notification
        self.notifications.send_notification(
            recipient='admin@system.com',  # Configure appropriately
            subject=f"Backup {notification_type}",
            message=message,
            data=data,
            priority='high' if 'failed' in notification_type else 'normal'
        )
    
    # ========================================================================
    # Restore Operations
    # ========================================================================
    
    def restore_backup(
        self,
        backup_id: str,
        target_db_url: Optional[str] = None,
        tables: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> bool:
        """
        Restore from a backup.
        
        Args:
            backup_id: ID of backup to restore
            target_db_url: Target database URL (defaults to original)
            tables: Specific tables to restore
            dry_run: Show what would be done without actually doing it
            
        Returns:
            True if successful
        """
        logger.info(f"Restoring backup: {backup_id}")
        
        # Find backup metadata
        metadata = self.backup_history.get(backup_id)
        if not metadata:
            # Try to find by filename
            metadata = self._find_backup_by_id(backup_id)
        
        if not metadata:
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        backup_file = self.backup_dir / metadata.metadata['filename']
        
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_file}")
            return False
        
        if dry_run:
            logger.info(f"[DRY RUN] Would restore from {backup_file}")
            return True
        
        try:
            start_time = datetime.utcnow()
            
            # Decrypt if needed
            if metadata.encrypted and self.encryption:
                backup_file = self._decrypt_file(backup_file)
            
            # Decompress if needed
            if metadata.compression != 'none':
                backup_file = self._decompress_file(backup_file, metadata.compression)
            
            # Determine target database
            target_url = target_db_url or self.db_url
            
            # Perform restore based on database type
            if self.db_type == 'postgresql':
                success = self._restore_postgresql(backup_file, target_url, tables)
            elif self.db_type == 'mysql':
                success = self._restore_mysql(backup_file, target_url, tables)
            elif self.db_type == 'sqlite':
                success = self._restore_sqlite(backup_file, target_url, tables)
            else:
                success = self._restore_generic(backup_file, target_url, tables)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            if success:
                logger.info(f"Restore completed successfully in {duration:.2f} seconds")
                
                # Send notification
                self._send_notification(
                    'restore_success',
                    f"Restore {backup_id} completed successfully",
                    {'backup_id': backup_id, 'duration': duration}
                )
            else:
                logger.error("Restore failed")
            
            return success
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            
            # Send notification
            self._send_notification(
                'restore_failed',
                f"Restore failed: {str(e)}",
                {'backup_id': backup_id, 'error': str(e)}
            )
            
            return False
    
    def _decrypt_file(self, filepath: Path) -> Path:
        """Decrypt a file."""
        if not self.encryption:
            return filepath
        
        decrypted = filepath.with_suffix('')  # Remove .enc
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        decrypted_data = self.encryption.decrypt(data)
        
        with open(decrypted, 'wb') as f:
            f.write(decrypted_data)
        
        return decrypted
    
    def _decompress_file(self, filepath: Path, compression: str) -> Path:
        """Decompress a file."""
        if compression == 'gzip':
            decompressed = filepath.with_suffix('')  # Remove .gz
            with gzip.open(filepath, 'rb') as f_in:
                with open(decompressed, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return decompressed
            
        elif compression == 'bzip2':
            decompressed = filepath.with_suffix('')  # Remove .bz2
            with bz2.open(filepath, 'rb') as f_in:
                with open(decompressed, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            return decompressed
            
        elif compression == 'zip':
            # Assume single file in zip
            with zipfile.ZipFile(filepath, 'r') as zf:
                # Get first file
                for name in zf.namelist():
                    zf.extract(name, filepath.parent)
                    return filepath.parent / name
        
        return filepath
    
    def _restore_postgresql(
        self,
        backup_file: Path,
        target_url: str,
        tables: Optional[List[str]]
    ) -> bool:
        """Restore PostgreSQL database using psql."""
        from urllib.parse import urlparse
        
        # Parse database URL
        parsed = urlparse(target_url)
        database = parsed.path[1:]
        username = parsed.username
        password = parsed.password
        hostname = parsed.hostname
        port = parsed.port or 5432
        
        # Determine if custom format
        if backup_file.suffix == '.dump':
            # Use pg_restore for custom format
            cmd = ['pg_restore']
            cmd.extend(['-h', hostname])
            cmd.extend(['-p', str(port)])
            cmd.extend(['-U', username])
            cmd.extend(['-d', database])
            cmd.append('--clean')  # Drop existing objects
            cmd.append('--if-exists')
            cmd.append(str(backup_file))
        else:
            # Use psql for plain SQL
            cmd = ['psql']
            cmd.extend(['-h', hostname])
            cmd.extend(['-p', str(port)])
            cmd.extend(['-U', username])
            cmd.extend(['-d', database])
            cmd.extend(['-f', str(backup_file)])
        
        # Set password environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        # Execute command
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Restore failed: {result.stderr}")
            return False
        
        return True
    
    def _restore_mysql(
        self,
        backup_file: Path,
        target_url: str,
        tables: Optional[List[str]]
    ) -> bool:
        """Restore MySQL database using mysql."""
        from urllib.parse import urlparse
        
        # Parse database URL
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
        
        # Execute command with input from backup file
        with open(backup_file, 'r') as f:
            result = subprocess.run(
                cmd,
                stdin=f,
                capture_output=True,
                text=True
            )
        
        if result.returncode != 0:
            logger.error(f"Restore failed: {result.stderr}")
            return False
        
        return True
    
    def _restore_sqlite(
        self,
        backup_file: Path,
        target_url: str,
        tables: Optional[List[str]]
    ) -> bool:
        """Restore SQLite database."""
        from urllib.parse import urlparse
        
        # Parse target URL
        parsed = urlparse(target_url)
        target_db = parsed.path
        
        if backup_file.suffix == '.sql':
            # Execute SQL script
            conn = sqlite3.connect(target_db)
            with open(backup_file, 'r') as f:
                script = f.read()
            
            # Split into statements and execute
            for statement in script.split(';'):
                if statement.strip():
                    conn.execute(statement)
            
            conn.commit()
            conn.close()
            
        else:
            # Direct copy
            shutil.copy2(backup_file, target_db)
        
        return True
    
    def _restore_generic(
        self,
        backup_file: Path,
        target_url: str,
        tables: Optional[List[str]]
    ) -> bool:
        """Generic restore using SQLAlchemy."""
        import json
        
        # Create engine for target database
        target_engine = create_engine(target_url)
        
        with open(backup_file, 'r') as f:
            data = json.load(f)
        
        with target_engine.connect() as conn:
            # Disable foreign key checks
            if self.db_type == 'sqlite':
                conn.execute(text("PRAGMA foreign_keys=OFF"))
            elif self.db_type == 'mysql':
                conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
            elif self.db_type == 'postgresql':
                conn.execute(text("SET session_replication_role = 'replica'"))
            
            # Restore tables
            for table_name, rows in data.items():
                if tables and table_name not in tables:
                    continue
                
                if rows:
                    # Clear existing data
                    conn.execute(text(f"DELETE FROM {table_name}"))
                    
                    # Insert data
                    for row in rows:
                        columns = ', '.join(row.keys())
                        placeholders = ', '.join([f":{k}" for k in row.keys()])
                        conn.execute(
                            text(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"),
                            row
                        )
                
                logger.debug(f"Restored table: {table_name}")
            
            # Re-enable foreign key checks
            if self.db_type == 'sqlite':
                conn.execute(text("PRAGMA foreign_keys=ON"))
            elif self.db_type == 'mysql':
                conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
            elif self.db_type == 'postgresql':
                conn.execute(text("SET session_replication_role = 'origin'"))
            
            conn.commit()
        
        return True
    
    # ========================================================================
    # Backup Management
    # ========================================================================
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups."""
        backups = []
        
        for backup_id, metadata in self.backup_history.items():
            backups.append({
                'id': backup_id,
                'type': metadata.backup_type,
                'created_at': metadata.created_at.isoformat(),
                'size': metadata.size,
                'size_formatted': self._format_size(metadata.size),
                'format': metadata.format,
                'compression': metadata.compression,
                'encrypted': metadata.encrypted,
                'tables': metadata.tables,
                'status': metadata.status
            })
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        
        return backups
    
    def show_backup_info(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Show detailed information about a backup."""
        metadata = self.backup_history.get(backup_id)
        
        if not metadata:
            # Try to find by filename
            metadata = self._find_backup_by_id(backup_id)
        
        if not metadata:
            logger.error(f"Backup not found: {backup_id}")
            return None
        
        return {
            'id': metadata.backup_id,
            'type': metadata.backup_type,
            'created_at': metadata.created_at.isoformat(),
            'duration': metadata.duration,
            'size': metadata.size,
            'size_formatted': self._format_size(metadata.size),
            'format': metadata.format,
            'compression': metadata.compression,
            'encrypted': metadata.encrypted,
            'tables': metadata.tables,
            'checksum': metadata.checksum,
            'status': metadata.status,
            'parent_backup': metadata.parent_backup_id,
            'file': metadata.metadata.get('filename'),
            'path': metadata.metadata.get('path'),
            'db_type': metadata.metadata.get('db_type')
        }
    
    def verify_backup(self, backup_id: str) -> bool:
        """Verify backup integrity."""
        logger.info(f"Verifying backup: {backup_id}")
        
        metadata = self.backup_history.get(backup_id)
        if not metadata:
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        backup_file = self.backup_dir / metadata.metadata['filename']
        
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_file}")
            return False
        
        # Verify checksum
        actual_checksum = self._calculate_checksum(backup_file)
        if actual_checksum != metadata.checksum:
            logger.error(f"Checksum mismatch: expected {metadata.checksum}, got {actual_checksum}")
            return False
        
        # Try to read the file (basic integrity check)
        try:
            if metadata.compression == 'gzip':
                with gzip.open(backup_file, 'rb') as f:
                    f.read(1024)  # Read first 1KB
            elif metadata.compression == 'bzip2':
                with bz2.open(backup_file, 'rb') as f:
                    f.read(1024)
            elif metadata.compression == 'zip':
                with zipfile.ZipFile(backup_file, 'r') as zf:
                    # Just test the zip file
                    pass
            else:
                with open(backup_file, 'rb') as f:
                    f.read(1024)
        except Exception as e:
            logger.error(f"File integrity check failed: {e}")
            return False
        
        logger.info(f"Backup {backup_id} verified successfully")
        return True
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup."""
        logger.info(f"Deleting backup: {backup_id}")
        
        metadata = self.backup_history.get(backup_id)
        if not metadata:
            logger.error(f"Backup not found: {backup_id}")
            return False
        
        backup_file = self.backup_dir / metadata.metadata['filename']
        
        if backup_file.exists():
            backup_file.unlink()
            logger.info(f"Deleted backup file: {backup_file}")
        
        # Remove from history
        del self.backup_history[backup_id]
        self._save_backup_history()
        
        return True
    
    def cleanup_old_backups(self, days: Optional[int] = None, keep: Optional[int] = None) -> int:
        """
        Clean up old backups based on retention policy.
        
        Args:
            days: Delete backups older than N days
            keep: Keep only N most recent backups
            
        Returns:
            Number of backups deleted
        """
        logger.info(f"Cleaning up old backups (days={days}, keep={keep})")
        
        deleted = 0
        backups = self.list_backups()
        
        # Delete by age
        if days:
            cutoff = datetime.utcnow() - timedelta(days=days)
            for backup in backups:
                created_at = datetime.fromisoformat(backup['created_at'])
                if created_at < cutoff:
                    if self.delete_backup(backup['id']):
                        deleted += 1
        
        # Keep only N most recent
        if keep and len(backups) > keep:
            # Sort by date (newest first)
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Keep first 'keep', delete the rest
            to_delete = backups[keep:]
            for backup in to_delete:
                if self.delete_backup(backup['id']):
                    deleted += 1
        
        logger.info(f"Cleaned up {deleted} old backups")
        return deleted
    
    def _find_backup_by_id(self, backup_id: str) -> Optional[BackupMetadata]:
        """Find backup by ID or filename."""
        # Try to find by exact ID
        if backup_id in self.backup_history:
            return self.backup_history[backup_id]
        
        # Try to find by filename
        for meta in self.backup_history.values():
            if meta.metadata.get('filename', '').startswith(backup_id):
                return meta
        
        return None
    
    def _format_size(self, size: int) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    # ========================================================================
    # Scheduling
    # ========================================================================
    
    def schedule_backups(self, schedule_config: Dict[str, Any]) -> bool:
        """
        Schedule automatic backups using cron.
        
        Args:
            schedule_config: Schedule configuration
            
        Returns:
            True if scheduled successfully
        """
        logger.info("Scheduling automatic backups")
        
        # This would typically create a cron job or scheduled task
        # For now, just log the configuration
        logger.info(f"Schedule config: {schedule_config}")
        
        # Example: Create cron job on Linux
        if sys.platform != 'win32':
            cron_line = f"{schedule_config.get('minute', '0')} {schedule_config.get('hour', '2')} * * * cd {os.getcwd()} && python -m data.scripts.backup_db backup --type {schedule_config.get('type', 'full')} >> {self.backup_dir}/backup.log 2>&1"
            
            logger.info(f"Cron line: {cron_line}")
            
            # Check if crontab is available
            try:
                result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                current_crontab = result.stdout
                
                # Check if already scheduled
                if 'backup_db' not in current_crontab:
                    # Append to crontab
                    new_crontab = current_crontab + cron_line + '\n'
                    
                    # Write new crontab
                    with open('/tmp/crontab.txt', 'w') as f:
                        f.write(new_crontab)
                    
                    subprocess.run(['crontab', '/tmp/crontab.txt'])
                    os.unlink('/tmp/crontab.txt')
                    
                    logger.info("Backup scheduled in crontab")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to schedule backup: {e}")
                return False
        
        return True


# ============================================================================
# Main Script
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Database backup management')
    parser.add_argument('command', choices=['backup', 'restore', 'list', 'info', 'verify', 'delete', 'schedule', 'cleanup'],
                       help='Command to execute')
    
    # Common options
    parser.add_argument('--db-url', help='Database connection URL')
    parser.add_argument('--backup-id', help='Backup ID for restore/info/verify/delete')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without actually doing it')
    
    # Backup options
    parser.add_argument('--type', choices=['full', 'incremental', 'differential'], default='full',
                       help='Backup type')
    parser.add_argument('--format', choices=['sql', 'json', 'custom'], default='sql',
                       help='Backup format')
    parser.add_argument('--compress', choices=['gzip', 'bzip2', 'zip', 'none'], default='gzip',
                       help='Compression type')
    parser.add_argument('--encrypt', action='store_true', help='Encrypt the backup')
    parser.add_argument('--output', help='Output directory')
    parser.add_argument('--remote', help='Remote storage URL (s3://, sftp://, etc.)')
    parser.add_argument('--tables', nargs='+', help='Specific tables to backup')
    parser.add_argument('--verify', action='store_true', help='Verify backup after creation')
    
    # Restore options
    parser.add_argument('--target-db', help='Target database URL for restore')
    
    # Cleanup options
    parser.add_argument('--days', type=int, help='Delete backups older than N days')
    parser.add_argument('--keep', type=int, help='Keep only N most recent backups')
    
    # Schedule options
    parser.add_argument('--schedule-minute', default='0', help='Minute for scheduled backup')
    parser.add_argument('--schedule-hour', default='2', help='Hour for scheduled backup')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(level=log_level)
    
    # Load configuration
    config = None
    if args.config:
        config = Config(args.config)
    else:
        config = Config()
    
    # Get database URL
    db_url = args.db_url or config.get('database.url')
    if not db_url:
        logger.error("Database URL not specified")
        sys.exit(1)
    
    # Initialize backup manager
    manager = BackupManager(
        db_url=db_url,
        backup_dir=args.output or config.get('backup.directory', './backups'),
        config=config
    )
    
    try:
        if args.command == 'backup':
            # Create backup
            metadata = manager.create_backup(
                backup_type=args.type,
                format=args.format,
                compression=args.compress,
                encrypt=args.encrypt,
                verify=args.verify,
                output_dir=args.output,
                remote_url=args.remote,
                tables=args.tables,
                dry_run=args.dry_run
            )
            
            if metadata and not args.dry_run:
                print(f"\nBackup created successfully:")
                print(f"  ID: {metadata.backup_id}")
                print(f"  Type: {metadata.backup_type}")
                print(f"  Size: {manager._format_size(metadata.size)}")
                print(f"  Created: {metadata.created_at}")
                print(f"  File: {metadata.metadata.get('filename')}")
        
        elif args.command == 'restore':
            # Restore backup
            if not args.backup_id:
                logger.error("Backup ID required for restore")
                sys.exit(1)
            
            success = manager.restore_backup(
                backup_id=args.backup_id,
                target_db_url=args.target_db,
                tables=args.tables,
                dry_run=args.dry_run
            )
            
            if success and not args.dry_run:
                print(f"\nBackup {args.backup_id} restored successfully")
        
        elif args.command == 'list':
            # List backups
            backups = manager.list_backups()
            
            if not backups:
                print("No backups found")
            else:
                print(f"\n{'ID':<20} {'Type':<12} {'Created':<20} {'Size':<10} {'Status':<10}")
                print("-" * 80)
                
                for backup in backups:
                    print(f"{backup['id']:<20} {backup['type']:<12} "
                          f"{backup['created_at'][:19]:<20} {backup['size_formatted']:<10} "
                          f"{backup['status']:<10}")
        
        elif args.command == 'info':
            # Show backup info
            if not args.backup_id:
                logger.error("Backup ID required for info")
                sys.exit(1)
            
            info = manager.show_backup_info(args.backup_id)
            
            if info:
                print(f"\nBackup Information:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
        
        elif args.command == 'verify':
            # Verify backup
            if not args.backup_id:
                logger.error("Backup ID required for verify")
                sys.exit(1)
            
            valid = manager.verify_backup(args.backup_id)
            
            if valid:
                print(f"\nBackup {args.backup_id} is valid")
            else:
                print(f"\nBackup {args.backup_id} is corrupted")
                sys.exit(1)
        
        elif args.command == 'delete':
            # Delete backup
            if not args.backup_id:
                logger.error("Backup ID required for delete")
                sys.exit(1)
            
            if args.dry_run:
                print(f"[DRY RUN] Would delete backup {args.backup_id}")
            else:
                deleted = manager.delete_backup(args.backup_id)
                if deleted:
                    print(f"\nBackup {args.backup_id} deleted")
                else:
                    print(f"\nBackup {args.backup_id} not found")
                    sys.exit(1)
        
        elif args.command == 'cleanup':
            # Cleanup old backups
            deleted = manager.cleanup_old_backups(days=args.days, keep=args.keep)
            print(f"\nCleaned up {deleted} old backups")
        
        elif args.command == 'schedule':
            # Schedule backups
            schedule_config = {
                'minute': args.schedule_minute,
                'hour': args.schedule_hour,
                'type': args.type
            }
            
            scheduled = manager.schedule_backups(schedule_config)
            
            if scheduled:
                print(f"\nBackups scheduled successfully")
            else:
                print(f"\nFailed to schedule backups")
                sys.exit(1)
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()