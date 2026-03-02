#!/usr/bin/env python3
"""
Data cleanup script for the parking management system.

This script implements data retention policies by cleaning up old data
across all entities. It supports dry runs, archival, and comprehensive
reporting.

Usage:
    python cleanup_old_data.py [options]

Options:
    --dry-run           Show what would be deleted without actually deleting
    --archive           Archive data before deletion
    --archive-dir DIR   Directory for archived data [default: ./archives]
    --days DAYS         Override default retention periods
    --tables LIST       Specific tables to clean (comma-separated)
    --older-than DAYS   Delete records older than N days
    --batch-size N      Batch size for deletes [default: 1000]
    --vacuum            Vacuum database after cleanup
    --force             Force cleanup without confirmation
    --config FILE       Configuration file
    --verbose           Verbose output
    --help              Show this help message

Retention periods:
    User data:
        - user_sessions: 30 days
        - user_devices: 90 days (inactive)
        - user_audit_logs: 365 days
        - deleted_users: 30 days (permanent deletion)
    
    Vehicle data:
        - vehicle_history: 365 days
        - deleted_vehicles: 30 days
    
    Reservation data:
        - reservation_history: 365 days
        - completed_reservations: 90 days
        - cancelled_reservations: 30 days
    
    Payment data:
        - payment_transactions: 365 days
        - refunded_payments: 365 days
        - failed_payments: 30 days
    
    Notification data:
        - notifications: 90 days
        - notification_logs: 30 days
    
    Audit data:
        - audit_logs: 365 days (based on severity)
        - compliance_logs: 730 days
    
    Temporary data:
        - password_reset_tokens: 1 day
        - email_verification_tokens: 7 days
        - oauth_states: 1 day
        - webhook_deliveries: 30 days

Examples:
    # Dry run to see what would be deleted
    python cleanup_old_data.py --dry-run

    # Archive and delete old audit logs
    python cleanup_old_data.py --tables audit_logs --older-than 365

    # Clean up all old data with confirmation
    python cleanup_old_data.py

    # Force cleanup without confirmation
    python cleanup_old_data.py --force

    # Vacuum after cleanup
    python cleanup_old_data.py --vacuum
"""

import os
import sys
import argparse
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import shutil
import gzip

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine, text, inspect, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session

from data.migrations.models import (
    User, UserSession, UserDevice, UserAuditLog,
    Vehicle, VehicleHistory,
    Reservation, ReservationHistory,
    Payment, PaymentTransaction,
    Notification, NotificationLog,
    AuditLog, ComplianceLog,
    PasswordResetToken, EmailVerificationToken, OAuthState,
    WebhookDelivery
)
from data.migrations.models.enums import (
    UserStatus,
    VehicleStatus,
    ReservationStatus,
    PaymentStatus,
    NotificationStatus,
    AuditSeverity
)
from utils.config import Config
from utils.logging import setup_logging

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class CleanupError(Exception):
    """Base exception for cleanup errors."""
    pass


class ArchiveError(CleanupError):
    """Raised when archiving fails."""
    pass


# ============================================================================
# Cleanup Manager
# ============================================================================

class CleanupManager:
    """
    Manages data cleanup based on retention policies.
    
    Handles identification, archival, and deletion of old data
    across all entities with comprehensive reporting.
    """
    
    def __init__(
        self,
        db_url: str,
        archive_dir: str = "./archives",
        dry_run: bool = False,
        archive: bool = False,
        batch_size: int = 1000,
        config: Optional[Config] = None
    ):
        """
        Initialize the cleanup manager.
        
        Args:
            db_url: Database URL
            archive_dir: Directory for archived data
            dry_run: Show what would be deleted without actually deleting
            archive: Archive data before deletion
            batch_size: Batch size for deletes
            config: Configuration object
        """
        self.db_url = db_url
        self.archive_dir = Path(archive_dir)
        self.dry_run = dry_run
        self.archive = archive
        self.batch_size = batch_size
        self.config = config or Config()
        
        # Create engine
        self.engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=False
        )
        
        # Create session
        self.Session = sessionmaker(bind=self.engine)
        
        # Create archive directory
        if archive:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            'tables': {},
            'total_rows_deleted': 0,
            'total_rows_archived': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }
        
        # Retention periods (in days)
        self.retention = {
            # User data
            'user_sessions': self.config.get('retention.user_sessions', 30),
            'user_devices': self.config.get('retention.user_devices', 90),
            'user_audit_logs': self.config.get('retention.user_audit_logs', 365),
            'deleted_users': self.config.get('retention.deleted_users', 30),
            
            # Vehicle data
            'vehicle_history': self.config.get('retention.vehicle_history', 365),
            'deleted_vehicles': self.config.get('retention.deleted_vehicles', 30),
            
            # Reservation data
            'reservation_history': self.config.get('retention.reservation_history', 365),
            'completed_reservations': self.config.get('retention.completed_reservations', 90),
            'cancelled_reservations': self.config.get('retention.cancelled_reservations', 30),
            
            # Payment data
            'payment_transactions': self.config.get('retention.payment_transactions', 365),
            'refunded_payments': self.config.get('retention.refunded_payments', 365),
            'failed_payments': self.config.get('retention.failed_payments', 30),
            
            # Notification data
            'notifications': self.config.get('retention.notifications', 90),
            'notification_logs': self.config.get('retention.notification_logs', 30),
            
            # Audit data
            'audit_logs': self.config.get('retention.audit_logs', 365),
            'compliance_logs': self.config.get('retention.compliance_logs', 730),
            
            # Temporary data
            'password_reset_tokens': self.config.get('retention.password_reset_tokens', 1),
            'email_verification_tokens': self.config.get('retention.email_verification_tokens', 7),
            'oauth_states': self.config.get('retention.oauth_states', 1),
            'webhook_deliveries': self.config.get('retention.webhook_deliveries', 30)
        }
        
        # Severity-based retention for audit logs
        self.severity_retention = {
            AuditSeverity.DEBUG: self.config.get('retention.audit_debug', 30),
            AuditSeverity.INFO: self.config.get('retention.audit_info', 90),
            AuditSeverity.NOTICE: self.config.get('retention.audit_notice', 180),
            AuditSeverity.WARNING: self.config.get('retention.audit_warning', 365),
            AuditSeverity.ERROR: self.config.get('retention.audit_error', 730),
            AuditSeverity.CRITICAL: self.config.get('retention.audit_critical', 1460),
            AuditSeverity.ALERT: self.config.get('retention.audit_alert', 1460),
            AuditSeverity.EMERGENCY: self.config.get('retention.audit_emergency', 2555)
        }
        
        logger.info(f"CleanupManager initialized with retention periods: {self.retention}")
    
    # ========================================================================
    # Main Cleanup Methods
    # ========================================================================
    
    def cleanup(
        self,
        tables: Optional[List[str]] = None,
        older_than: Optional[int] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Perform data cleanup.
        
        Args:
            tables: Specific tables to clean (None for all)
            older_than: Override retention period (days)
            force: Skip confirmation
            
        Returns:
            Statistics dictionary
        """
        self.stats['start_time'] = datetime.utcnow()
        
        logger.info("Starting data cleanup...")
        
        if self.dry_run:
            logger.info("DRY RUN - No data will be deleted")
        
        if self.archive:
            logger.info(f"Archiving to: {self.archive_dir}")
        
        # Determine which cleanup tasks to run
        cleanup_tasks = self._get_cleanup_tasks(tables, older_than)
        
        # Show what will be cleaned
        self._show_cleanup_plan(cleanup_tasks)
        
        # Confirm if not forced and not dry run
        if not force and not self.dry_run:
            response = input("\nProceed with cleanup? [y/N]: ")
            if response.lower() != 'y':
                logger.info("Cleanup cancelled")
                return self.stats
        
        # Execute cleanup tasks
        for task in cleanup_tasks:
            self._execute_cleanup_task(task)
        
        # Vacuum if requested
        if not self.dry_run and hasattr(args, 'vacuum') and args.vacuum:
            self._vacuum_database()
        
        self.stats['end_time'] = datetime.utcnow()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info(f"Cleanup completed in {duration:.2f} seconds")
        logger.info(f"Total rows deleted: {self.stats['total_rows_deleted']}")
        logger.info(f"Total rows archived: {self.stats['total_rows_archived']}")
        
        return self.stats
    
    def _get_cleanup_tasks(
        self,
        tables: Optional[List[str]],
        older_than: Optional[int]
    ) -> List[Dict[str, Any]]:
        """Get list of cleanup tasks to execute."""
        tasks = []
        
        # User session cleanup
        if not tables or 'user_sessions' in tables:
            tasks.append({
                'name': 'user_sessions',
                'table': 'user_sessions',
                'model': UserSession,
                'query': lambda s: s.query(UserSession).filter(
                    or_(
                        UserSession.expires_at < datetime.utcnow(),
                        and_(
                            UserSession.is_active == False,
                            UserSession.terminated_at < datetime.utcnow() - timedelta(days=self.retention['user_sessions'])
                        )
                    )
                ),
                'description': 'Expired and old inactive sessions',
                'retention': self.retention['user_sessions']
            })
        
        # User devices cleanup
        if not tables or 'user_devices' in tables:
            tasks.append({
                'name': 'user_devices',
                'table': 'user_devices',
                'model': UserDevice,
                'query': lambda s: s.query(UserDevice).filter(
                    and_(
                        UserDevice.is_active == False,
                        UserDevice.unregistered_at < datetime.utcnow() - timedelta(days=self.retention['user_devices'])
                    )
                ),
                'description': 'Unregistered devices',
                'retention': self.retention['user_devices']
            })
        
        # User audit logs cleanup
        if not tables or 'user_audit_logs' in tables:
            tasks.append({
                'name': 'user_audit_logs',
                'table': 'user_audit_logs',
                'model': UserAuditLog,
                'query': lambda s: s.query(UserAuditLog).filter(
                    UserAuditLog.created_at < datetime.utcnow() - timedelta(days=self.retention['user_audit_logs'])
                ),
                'description': 'Old user audit logs',
                'retention': self.retention['user_audit_logs']
            })
        
        # Deleted users cleanup
        if not tables or 'deleted_users' in tables:
            tasks.append({
                'name': 'deleted_users',
                'table': 'users',
                'model': User,
                'query': lambda s: s.query(User).filter(
                    User.status == UserStatus.DELETED,
                    User.deleted_at < datetime.utcnow() - timedelta(days=self.retention['deleted_users'])
                ),
                'description': 'Permanently deleted users',
                'retention': self.retention['deleted_users']
            })
        
        # Vehicle history cleanup
        if not tables or 'vehicle_history' in tables:
            tasks.append({
                'name': 'vehicle_history',
                'table': 'vehicle_history',
                'model': VehicleHistory,
                'query': lambda s: s.query(VehicleHistory).filter(
                    VehicleHistory.created_at < datetime.utcnow() - timedelta(days=self.retention['vehicle_history'])
                ),
                'description': 'Old vehicle history',
                'retention': self.retention['vehicle_history']
            })
        
        # Deleted vehicles cleanup
        if not tables or 'deleted_vehicles' in tables:
            tasks.append({
                'name': 'deleted_vehicles',
                'table': 'vehicles',
                'model': Vehicle,
                'query': lambda s: s.query(Vehicle).filter(
                    Vehicle.status == VehicleStatus.DELETED,
                    Vehicle.deleted_at < datetime.utcnow() - timedelta(days=self.retention['deleted_vehicles'])
                ),
                'description': 'Permanently deleted vehicles',
                'retention': self.retention['deleted_vehicles']
            })
        
        # Reservation history cleanup
        if not tables or 'reservation_history' in tables:
            tasks.append({
                'name': 'reservation_history',
                'table': 'reservation_history',
                'model': ReservationHistory,
                'query': lambda s: s.query(ReservationHistory).filter(
                    ReservationHistory.created_at < datetime.utcnow() - timedelta(days=self.retention['reservation_history'])
                ),
                'description': 'Old reservation history',
                'retention': self.retention['reservation_history']
            })
        
        # Completed reservations cleanup
        if not tables or 'completed_reservations' in tables:
            tasks.append({
                'name': 'completed_reservations',
                'table': 'reservations',
                'model': Reservation,
                'query': lambda s: s.query(Reservation).filter(
                    Reservation.status == ReservationStatus.COMPLETED,
                    Reservation.end_time < datetime.utcnow() - timedelta(days=self.retention['completed_reservations'])
                ),
                'description': 'Old completed reservations',
                'retention': self.retention['completed_reservations']
            })
        
        # Cancelled reservations cleanup
        if not tables or 'cancelled_reservations' in tables:
            tasks.append({
                'name': 'cancelled_reservations',
                'table': 'reservations',
                'model': Reservation,
                'query': lambda s: s.query(Reservation).filter(
                    Reservation.status == ReservationStatus.CANCELLED,
                    Reservation.cancelled_at < datetime.utcnow() - timedelta(days=self.retention['cancelled_reservations'])
                ),
                'description': 'Old cancelled reservations',
                'retention': self.retention['cancelled_reservations']
            })
        
        # Payment transactions cleanup
        if not tables or 'payment_transactions' in tables:
            tasks.append({
                'name': 'payment_transactions',
                'table': 'payment_transactions',
                'model': PaymentTransaction,
                'query': lambda s: s.query(PaymentTransaction).filter(
                    PaymentTransaction.created_at < datetime.utcnow() - timedelta(days=self.retention['payment_transactions'])
                ),
                'description': 'Old payment transactions',
                'retention': self.retention['payment_transactions']
            })
        
        # Refunded payments cleanup
        if not tables or 'refunded_payments' in tables:
            tasks.append({
                'name': 'refunded_payments',
                'table': 'payments',
                'model': Payment,
                'query': lambda s: s.query(Payment).filter(
                    Payment.status == PaymentStatus.REFUNDED,
                    Payment.updated_at < datetime.utcnow() - timedelta(days=self.retention['refunded_payments'])
                ),
                'description': 'Old refunded payments',
                'retention': self.retention['refunded_payments']
            })
        
        # Failed payments cleanup
        if not tables or 'failed_payments' in tables:
            tasks.append({
                'name': 'failed_payments',
                'table': 'payments',
                'model': Payment,
                'query': lambda s: s.query(Payment).filter(
                    Payment.status.in_([PaymentStatus.FAILED, PaymentStatus.CANCELLED]),
                    Payment.updated_at < datetime.utcnow() - timedelta(days=self.retention['failed_payments'])
                ),
                'description': 'Old failed payments',
                'retention': self.retention['failed_payments']
            })
        
        # Notifications cleanup
        if not tables or 'notifications' in tables:
            tasks.append({
                'name': 'notifications',
                'table': 'notifications',
                'model': Notification,
                'query': lambda s: s.query(Notification).filter(
                    Notification.created_at < datetime.utcnow() - timedelta(days=self.retention['notifications'])
                ),
                'description': 'Old notifications',
                'retention': self.retention['notifications']
            })
        
        # Notification logs cleanup
        if not tables or 'notification_logs' in tables:
            tasks.append({
                'name': 'notification_logs',
                'table': 'notification_logs',
                'model': NotificationLog,
                'query': lambda s: s.query(NotificationLog).filter(
                    NotificationLog.created_at < datetime.utcnow() - timedelta(days=self.retention['notification_logs'])
                ),
                'description': 'Old notification logs',
                'retention': self.retention['notification_logs']
            })
        
        # Audit logs cleanup (by severity)
        if not tables or 'audit_logs' in tables:
            for severity, days in self.severity_retention.items():
                tasks.append({
                    'name': f'audit_logs_{severity.value}',
                    'table': 'audit_logs',
                    'model': AuditLog,
                    'query': lambda s, sev=severity, d=days: s.query(AuditLog).filter(
                        AuditLog.severity == sev,
                        AuditLog.created_at < datetime.utcnow() - timedelta(days=d)
                    ),
                    'description': f'Old audit logs ({severity.value})',
                    'retention': days,
                    'severity': severity
                })
        
        # Compliance logs cleanup
        if not tables or 'compliance_logs' in tables:
            tasks.append({
                'name': 'compliance_logs',
                'table': 'compliance_logs',
                'model': ComplianceLog,
                'query': lambda s: s.query(ComplianceLog).filter(
                    ComplianceLog.created_at < datetime.utcnow() - timedelta(days=self.retention['compliance_logs'])
                ),
                'description': 'Old compliance logs',
                'retention': self.retention['compliance_logs']
            })
        
        # Password reset tokens cleanup
        if not tables or 'password_reset_tokens' in tables:
            tasks.append({
                'name': 'password_reset_tokens',
                'table': 'password_reset_tokens',
                'model': PasswordResetToken,
                'query': lambda s: s.query(PasswordResetToken).filter(
                    or_(
                        PasswordResetToken.expires_at < datetime.utcnow(),
                        and_(
                            PasswordResetToken.used == True,
                            PasswordResetToken.used_at < datetime.utcnow() - timedelta(days=self.retention['password_reset_tokens'])
                        )
                    )
                ),
                'description': 'Expired and used password reset tokens',
                'retention': self.retention['password_reset_tokens']
            })
        
        # Email verification tokens cleanup
        if not tables or 'email_verification_tokens' in tables:
            tasks.append({
                'name': 'email_verification_tokens',
                'table': 'email_verification_tokens',
                'model': EmailVerificationToken,
                'query': lambda s: s.query(EmailVerificationToken).filter(
                    or_(
                        EmailVerificationToken.expires_at < datetime.utcnow(),
                        and_(
                            EmailVerificationToken.used == True,
                            EmailVerificationToken.used_at < datetime.utcnow() - timedelta(days=self.retention['email_verification_tokens'])
                        )
                    )
                ),
                'description': 'Expired and used email verification tokens',
                'retention': self.retention['email_verification_tokens']
            })
        
        # OAuth states cleanup
        if not tables or 'oauth_states' in tables:
            tasks.append({
                'name': 'oauth_states',
                'table': 'oauth_states',
                'model': OAuthState,
                'query': lambda s: s.query(OAuthState).filter(
                    OAuthState.created_at < datetime.utcnow() - timedelta(days=self.retention['oauth_states'])
                ),
                'description': 'Old OAuth states',
                'retention': self.retention['oauth_states']
            })
        
        # Webhook deliveries cleanup
        if not tables or 'webhook_deliveries' in tables:
            tasks.append({
                'name': 'webhook_deliveries',
                'table': 'webhook_deliveries',
                'model': WebhookDelivery,
                'query': lambda s: s.query(WebhookDelivery).filter(
                    WebhookDelivery.created_at < datetime.utcnow() - timedelta(days=self.retention['webhook_deliveries'])
                ),
                'description': 'Old webhook deliveries',
                'retention': self.retention['webhook_deliveries']
            })
        
        # Apply global older_than override
        if older_than:
            for task in tasks:
                task['retention'] = older_than
                # Update query for tasks without severity-based retention
                if 'severity' not in task:
                    original_query = task['query']
                    task['query'] = lambda s, orig=original_query, d=older_than: orig(s).filter(
                        task['model'].created_at < datetime.utcnow() - timedelta(days=d)
                    )
        
        return tasks
    
    def _show_cleanup_plan(self, tasks: List[Dict[str, Any]]) -> None:
        """Show what will be cleaned up."""
        with self.Session() as session:
            print("\n" + "="*80)
            print("CLEANUP PLAN")
            print("="*80)
            print(f"{'Task':<30} {'Retention':<12} {'Rows':<12} {'Description':<30}")
            print("-"*80)
            
            total_rows = 0
            
            for task in tasks:
                # Count rows to be deleted
                query = task['query'](session)
                count = query.count()
                total_rows += count
                
                retention_display = f"{task['retention']} days"
                if 'severity' in task:
                    retention_display = f"{task['retention']} days ({task['severity'].value})"
                
                print(f"{task['name']:<30} {retention_display:<12} {count:<12,} {task['description']:<30}")
            
            print("-"*80)
            print(f"{'TOTAL':<30} {'':<12} {total_rows:<12,}")
            print("="*80)
    
    def _execute_cleanup_task(self, task: Dict[str, Any]) -> None:
        """Execute a single cleanup task."""
        logger.info(f"Cleaning up: {task['name']}")
        
        with self.Session() as session:
            # Get rows to delete
            query = task['query'](session)
            rows = query.limit(self.batch_size).all()
            
            task_stats = {
                'deleted': 0,
                'archived': 0,
                'errors': 0
            }
            
            while rows:
                for row in rows:
                    try:
                        # Archive if requested
                        if self.archive and not self.dry_run:
                            self._archive_row(task['table'], row)
                            task_stats['archived'] += 1
                        
                        # Delete row
                        if not self.dry_run:
                            session.delete(row)
                        
                        task_stats['deleted'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing row: {e}")
                        task_stats['errors'] += 1
                        self.stats['errors'].append(str(e))
                        
                        if not self.dry_run:
                            session.rollback()
                            raise
                
                # Commit batch
                if not self.dry_run:
                    session.commit()
                
                logger.debug(f"  Processed {task_stats['deleted']} rows for {task['name']}")
                
                # Get next batch
                rows = query.limit(self.batch_size).all()
            
            # Update statistics
            self.stats['tables'][task['name']] = task_stats
            self.stats['total_rows_deleted'] += task_stats['deleted']
            self.stats['total_rows_archived'] += task_stats['archived']
            
            logger.info(f"  Deleted: {task_stats['deleted']}, Archived: {task_stats['archived']}, Errors: {task_stats['errors']}")
    
    def _archive_row(self, table: str, row: Any) -> None:
        """
        Archive a single row before deletion.
        
        Args:
            table: Table name
            row: Row object
        """
        # Create archive directory for this table
        table_dir = self.archive_dir / table
        table_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate archive filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        row_id = getattr(row, 'id', 'unknown')
        archive_file = table_dir / f"{row_id}_{timestamp}.json.gz"
        
        # Convert row to dictionary
        row_dict = {}
        for column in row.__table__.columns:
            value = getattr(row, column.name)
            if isinstance(value, (datetime, date)):
                value = value.isoformat()
            elif hasattr(value, 'value'):  # Enum
                value = value.value
            row_dict[column.name] = value
        
        # Add metadata
        archive_data = {
            'table': table,
            'id': row_id,
            'archived_at': datetime.utcnow().isoformat(),
            'data': row_dict
        }
        
        # Write compressed archive
        with gzip.open(archive_file, 'wt', encoding='utf-8') as f:
            json.dump(archive_data, f, indent=2)
    
    def _vacuum_database(self) -> None:
        """Vacuum the database to reclaim space."""
        logger.info("Vacuuming database...")
        
        with self.engine.connect() as conn:
            conn.execute(text("VACUUM ANALYZE"))
            conn.commit()
        
        logger.info("Vacuum completed")
    
    # ========================================================================
    # Reporting Methods
    # ========================================================================
    
    def generate_report(self, output_file: Optional[str] = None) -> None:
        """
        Generate a cleanup report.
        
        Args:
            output_file: Output file path
        """
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'dry_run': self.dry_run,
            'archive': self.archive,
            'archive_dir': str(self.archive_dir) if self.archive else None,
            'retention_periods': self.retention,
            'severity_retention': {k.value: v for k, v in self.severity_retention.items()},
            'statistics': self.stats
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to: {output_file}")
        else:
            # Print report to console
            print("\n" + "="*80)
            print("CLEANUP REPORT")
            print("="*80)
            print(f"Timestamp: {report['timestamp']}")
            print(f"Dry Run: {report['dry_run']}")
            print(f"Archive: {report['archive']}")
            if report['archive']:
                print(f"Archive Directory: {report['archive_dir']}")
            print("\nStatistics:")
            print(f"  Total Rows Deleted: {self.stats['total_rows_deleted']:,}")
            print(f"  Total Rows Archived: {self.stats['total_rows_archived']:,}")
            print(f"  Duration: {(self.stats['end_time'] - self.stats['start_time']).total_seconds():.2f}s")
            
            if self.stats['errors']:
                print(f"\nErrors ({len(self.stats['errors'])}):")
                for error in self.stats['errors'][:10]:
                    print(f"  - {error}")
            
            print("\nBy Table:")
            for table, stats in self.stats['tables'].items():
                print(f"  {table}: Deleted {stats['deleted']:,}, Archived {stats['archived']:,}, Errors {stats['errors']}")
            
            print("="*80)
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_database_size(self) -> int:
        """Get database size in bytes."""
        with self.engine.connect() as conn:
            if 'postgresql' in self.db_url:
                result = conn.execute(text("""
                    SELECT pg_database_size(current_database())
                """)).scalar()
                return result or 0
            elif 'mysql' in self.db_url:
                result = conn.execute(text("""
                    SELECT SUM(data_length + index_length) 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE()
                """)).scalar()
                return result or 0
            elif 'sqlite' in self.db_url:
                import os
                from urllib.parse import urlparse
                db_path = urlparse(self.db_url).path
                return os.path.getsize(db_path) if os.path.exists(db_path) else 0
        return 0
    
    def estimate_space_savings(self) -> Dict[str, Any]:
        """Estimate potential space savings from cleanup."""
        savings = {
            'current_size': self.get_database_size(),
            'estimated_savings': 0,
            'by_table': {}
        }
        
        with self.Session() as session:
            for table_name in ['user_sessions', 'user_devices', 'user_audit_logs',
                              'vehicle_history', 'reservation_history', 'audit_logs']:
                # This would need table size estimation logic
                # For now, just estimate based on row counts
                pass
        
        return savings


# ============================================================================
# Main Script
# ============================================================================

def parse_tables(tables_str: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated table list."""
    if not tables_str:
        return None
    return [t.strip() for t in tables_str.split(',')]


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Clean up old data from database')
    
    # Cleanup options
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--archive', action='store_true', help='Archive data before deletion')
    parser.add_argument('--archive-dir', default='./archives', help='Directory for archived data')
    parser.add_argument('--days', type=int, help='Override default retention periods')
    parser.add_argument('--tables', help='Specific tables to clean (comma-separated)')
    parser.add_argument('--older-than', type=int, help='Delete records older than N days')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for deletes')
    parser.add_argument('--vacuum', action='store_true', help='Vacuum database after cleanup')
    parser.add_argument('--force', action='store_true', help='Force cleanup without confirmation')
    
    # Output options
    parser.add_argument('--report', help='Generate report file')
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--db-url', help='Database URL')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
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
    
    # Parse tables
    tables = parse_tables(args.tables)
    
    # Create cleanup manager
    manager = CleanupManager(
        db_url=db_url,
        archive_dir=args.archive_dir,
        dry_run=args.dry_run,
        archive=args.archive,
        batch_size=args.batch_size,
        config=config
    )
    
    try:
        # Perform cleanup
        stats = manager.cleanup(
            tables=tables,
            older_than=args.older_than or args.days,
            force=args.force
        )
        
        # Generate report
        if args.report:
            manager.generate_report(args.report)
        else:
            manager.generate_report()
        
        # Show space savings
        if not args.dry_run:
            size_before = stats.get('size_before', 0)
            size_after = manager.get_database_size()
            if size_before and size_after:
                saved = size_before - size_after
                logger.info(f"Space saved: {saved / (1024*1024):.2f} MB")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()