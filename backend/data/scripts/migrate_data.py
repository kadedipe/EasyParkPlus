#!/usr/bin/env python3
"""
Data migration script for the parking management system.

This script provides comprehensive data migration capabilities including:
- Environment to environment migration (dev -> staging -> prod)
- Database to database migration
- Schema version migration
- Data transformation and cleaning
- Validation and verification
- Rollback support
- Parallel processing for large datasets
- Progress tracking and reporting

Usage:
    python migrate_data.py [command] [options]

Commands:
    migrate         Perform data migration
    validate        Validate data without migrating
    rollback        Rollback last migration
    status          Show migration status
    plan            Show migration plan
    transform       Apply data transformations
    cleanup         Clean up temporary/migration data

Options:
    --source URL    Source database URL
    --target URL    Target database URL
    --config FILE   Configuration file
    --tables LIST   Specific tables to migrate (comma-separated)
    --where COND    WHERE clause for filtering data
    --limit N       Limit number of records
    --batch-size N  Batch size for processing [default: 1000]
    --parallel N    Number of parallel workers [default: 4]
    --transform     Apply transformations during migration
    --validate      Validate data after migration
    --dry-run       Show what would be done without actually doing it
    --force         Force migration even if validation fails
    --continue-on-error  Continue migration if errors occur
    --verbose       Verbose output
    --help          Show this help message

Examples:
    # Migrate all data from dev to staging
    python migrate_data.py migrate --source dev_db --target staging_db

    # Migrate specific tables with filtering
    python migrate_data.py migrate --source old.db --target new.db \
        --tables users,vehicles --where "created_at > '2024-01-01'"

    # Validate data without migrating
    python migrate_data.py validate --source prod_db --target staging_db

    # Show migration plan
    python migrate_data.py plan --source dev_db --target prod_db

    # Apply transformations during migration
    python migrate_data.py migrate --source old --target new --transform

    # Parallel migration with 8 workers
    python migrate_data.py migrate --source big.db --target new.db \
        --parallel 8 --batch-size 5000
"""

import os
import sys
import argparse
import logging
import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Set, Callable
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import signal
import atexit

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import (
    create_engine, text, inspect, MetaData, Table, Column,
    Integer, String, DateTime, Boolean, Float, and_, or_, not_
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker, Session

from data.migrations.models import Base
from data.migrations.models.enums import (
    UserStatus, UserRole,
    VehicleStatus, VehicleType,
    ReservationStatus,
    PaymentStatus
)
from data.repositories import (
    UserRepository, VehicleRepository, ReservationRepository,
    PaymentRepository
)
from utils.config import Config
from utils.logging import setup_logging

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class MigrationError(Exception):
    """Base exception for migration errors."""
    pass


class SourceNotFoundError(MigrationError):
    """Raised when source database is not found."""
    pass


class TargetNotFoundError(MigrationError):
    """Raised when target database is not found."""
    pass


class ValidationError(MigrationError):
    """Raised when data validation fails."""
    pass


class TransformationError(MigrationError):
    """Raised when data transformation fails."""
    pass


class RollbackError(MigrationError):
    """Raised when rollback fails."""
    pass


# ============================================================================
# Migration Models
# ============================================================================

class MigrationStatus:
    """Migration status constants."""
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    VALIDATED = 'validated'
    ROLLED_BACK = 'rolled_back'


class MigrationRecord:
    """Record of a migration operation."""
    
    def __init__(
        self,
        migration_id: str,
        source: str,
        target: str,
        tables: List[str],
        status: str,
        started_at: datetime,
        completed_at: Optional[datetime] = None,
        records_migrated: int = 0,
        errors: List[str] = None,
        warnings: List[str] = None
    ):
        self.migration_id = migration_id
        self.source = source
        self.target = target
        self.tables = tables
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.records_migrated = records_migrated
        self.errors = errors or []
        self.warnings = warnings or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'migration_id': self.migration_id,
            'source': self.source,
            'target': self.target,
            'tables': self.tables,
            'status': self.status,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'records_migrated': self.records_migrated,
            'errors': self.errors,
            'warnings': self.warnings
        }


class TableMigrationPlan:
    """Plan for migrating a single table."""
    
    def __init__(
        self,
        table_name: str,
        row_count: int,
        columns: List[str],
        dependencies: List[str] = None,
        transform_needed: bool = False,
        validation_rules: List[str] = None
    ):
        self.table_name = table_name
        self.row_count = row_count
        self.columns = columns
        self.dependencies = dependencies or []
        self.transform_needed = transform_needed
        self.validation_rules = validation_rules or []
        self.processed = 0
        self.estimated_time = 0


# ============================================================================
# Data Transformer
# ============================================================================

class DataTransformer:
    """
    Transforms data during migration.
    
    Applies various transformations to ensure data compatibility
    between different schema versions or database types.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.transformations = self._register_transformations()
    
    def _register_transformations(self) -> Dict[str, Callable]:
        """Register available transformations."""
        return {
            # User transformations
            'user_status': self._transform_user_status,
            'user_role': self._transform_user_role,
            'user_password': self._transform_user_password,
            
            # Vehicle transformations
            'vehicle_type': self._transform_vehicle_type,
            'vehicle_status': self._transform_vehicle_status,
            'license_plate': self._transform_license_plate,
            
            # Reservation transformations
            'reservation_status': self._transform_reservation_status,
            'datetime_format': self._transform_datetime,
            
            # Payment transformations
            'payment_status': self._transform_payment_status,
            'currency': self._transform_currency,
            'amount': self._transform_amount,
            
            # Generic transformations
            'null_to_empty': self._transform_null_to_empty,
            'strip_whitespace': self._transform_strip_whitespace,
            'lowercase': self._transform_lowercase,
            'uppercase': self._transform_uppercase,
            'boolean_to_int': self._transform_boolean_to_int,
            'int_to_boolean': self._transform_int_to_boolean,
            'date_format': self._transform_date_format
        }
    
    def transform_row(
        self,
        table: str,
        row: Dict[str, Any],
        transformations: List[str]
    ) -> Dict[str, Any]:
        """
        Apply transformations to a single row.
        
        Args:
            table: Table name
            row: Row data
            transformations: List of transformations to apply
            
        Returns:
            Transformed row
        """
        result = row.copy()
        
        for transform_name in transformations:
            if transform_name in self.transformations:
                try:
                    transformer = self.transformations[transform_name]
                    result = transformer(table, result)
                except Exception as e:
                    raise TransformationError(
                        f"Failed to apply {transform_name} to {table}: {e}"
                    )
            else:
                logger.warning(f"Unknown transformation: {transform_name}")
        
        return result
    
    # ========================================================================
    # User Transformations
    # ========================================================================
    
    def _transform_user_status(self, table: str, row: Dict) -> Dict:
        """Transform user status enum values."""
        if table != 'users' or 'status' not in row:
            return row
        
        # Map old status values to new ones
        status_map = {
            '1': UserStatus.ACTIVE.value,
            '2': UserStatus.INACTIVE.value,
            '3': UserStatus.SUSPENDED.value,
            '4': UserStatus.LOCKED.value,
            '5': UserStatus.DELETED.value,
            'active': UserStatus.ACTIVE.value,
            'inactive': UserStatus.INACTIVE.value,
            'suspended': UserStatus.SUSPENDED.value,
            'locked': UserStatus.LOCKED.value,
            'deleted': UserStatus.DELETED.value
        }
        
        old_status = str(row['status']).lower()
        row['status'] = status_map.get(old_status, UserStatus.PENDING.value)
        
        return row
    
    def _transform_user_role(self, table: str, row: Dict) -> Dict:
        """Transform user role enum values."""
        if table != 'users' or 'role' not in row:
            return row
        
        role_map = {
            '1': UserRole.USER.value,
            '2': UserRole.OPERATOR.value,
            '3': UserRole.MANAGER.value,
            '4': UserRole.ADMIN.value,
            '5': UserRole.SUPER_ADMIN.value,
            'user': UserRole.USER.value,
            'operator': UserRole.OPERATOR.value,
            'manager': UserRole.MANAGER.value,
            'admin': UserRole.ADMIN.value,
            'super_admin': UserRole.SUPER_ADMIN.value
        }
        
        old_role = str(row['role']).lower()
        row['role'] = role_map.get(old_role, UserRole.USER.value)
        
        return row
    
    def _transform_user_password(self, table: str, row: Dict) -> Dict:
        """Transform password hashing if needed."""
        if table != 'users' or 'password_hash' not in row:
            return row
        
        # Check if password needs rehashing
        password = row['password_hash']
        if password and not password.startswith('$2b$'):  # Not bcrypt
            # This would rehash with new algorithm
            # For now, just pass through
            pass
        
        return row
    
    # ========================================================================
    # Vehicle Transformations
    # ========================================================================
    
    def _transform_vehicle_type(self, table: str, row: Dict) -> Dict:
        """Transform vehicle type enum values."""
        if table != 'vehicles' or 'vehicle_type' not in row:
            return row
        
        type_map = {
            '1': VehicleType.CAR.value,
            '2': VehicleType.SUV.value,
            '3': VehicleType.TRUCK.value,
            '4': VehicleType.MOTORCYCLE.value,
            '5': VehicleType.EV.value,
            '6': VehicleType.HYBRID.value,
            'car': VehicleType.CAR.value,
            'suv': VehicleType.SUV.value,
            'truck': VehicleType.TRUCK.value,
            'motorcycle': VehicleType.MOTORCYCLE.value,
            'ev': VehicleType.EV.value,
            'hybrid': VehicleType.HYBRID.value
        }
        
        old_type = str(row['vehicle_type']).lower()
        row['vehicle_type'] = type_map.get(old_type, VehicleType.CAR.value)
        
        return row
    
    def _transform_vehicle_status(self, table: str, row: Dict) -> Dict:
        """Transform vehicle status enum values."""
        if table != 'vehicles' or 'status' not in row:
            return row
        
        status_map = {
            '1': VehicleStatus.ACTIVE.value,
            '2': VehicleStatus.INACTIVE.value,
            '3': VehicleStatus.SUSPENDED.value,
            '4': VehicleStatus.BANNED.value,
            'active': VehicleStatus.ACTIVE.value,
            'inactive': VehicleStatus.INACTIVE.value,
            'suspended': VehicleStatus.SUSPENDED.value,
            'banned': VehicleStatus.BANNED.value
        }
        
        old_status = str(row['status']).lower()
        row['status'] = status_map.get(old_status, VehicleStatus.ACTIVE.value)
        
        return row
    
    def _transform_license_plate(self, table: str, row: Dict) -> Dict:
        """Normalize license plate format."""
        if table != 'vehicles' or 'license_plate' not in row:
            return row
        
        plate = row['license_plate']
        if plate:
            # Remove spaces and convert to uppercase
            plate = ''.join(plate.split()).upper()
            row['license_plate'] = plate
        
        return row
    
    # ========================================================================
    # Reservation Transformations
    # ========================================================================
    
    def _transform_reservation_status(self, table: str, row: Dict) -> Dict:
        """Transform reservation status enum values."""
        if table != 'reservations' or 'status' not in row:
            return row
        
        status_map = {
            '1': ReservationStatus.PENDING.value,
            '2': ReservationStatus.CONFIRMED.value,
            '3': ReservationStatus.CHECKED_IN.value,
            '4': ReservationStatus.COMPLETED.value,
            '5': ReservationStatus.CANCELLED.value,
            '6': ReservationStatus.NO_SHOW.value,
            'pending': ReservationStatus.PENDING.value,
            'confirmed': ReservationStatus.CONFIRMED.value,
            'checked_in': ReservationStatus.CHECKED_IN.value,
            'completed': ReservationStatus.COMPLETED.value,
            'cancelled': ReservationStatus.CANCELLED.value,
            'no_show': ReservationStatus.NO_SHOW.value
        }
        
        old_status = str(row['status']).lower()
        row['status'] = status_map.get(old_status, ReservationStatus.PENDING.value)
        
        return row
    
    def _transform_datetime(self, table: str, row: Dict) -> Dict:
        """Transform datetime fields to ISO format."""
        datetime_fields = ['created_at', 'updated_at', 'start_time', 'end_time',
                          'checked_in_at', 'checked_out_at', 'cancelled_at']
        
        for field in datetime_fields:
            if field in row and row[field]:
                if isinstance(row[field], str):
                    try:
                        # Try to parse and reformat
                        dt = datetime.fromisoformat(row[field].replace('Z', '+00:00'))
                        row[field] = dt.isoformat()
                    except ValueError:
                        # Try other formats
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S', '%m/%d/%Y %H:%M']:
                            try:
                                dt = datetime.strptime(row[field], fmt)
                                row[field] = dt.isoformat()
                                break
                            except ValueError:
                                continue
        
        return row
    
    # ========================================================================
    # Payment Transformations
    # ========================================================================
    
    def _transform_payment_status(self, table: str, row: Dict) -> Dict:
        """Transform payment status enum values."""
        if table not in ['payments', 'invoices'] or 'status' not in row:
            return row
        
        status_map = {
            '1': PaymentStatus.PENDING.value,
            '2': PaymentStatus.PAID.value,
            '3': PaymentStatus.FAILED.value,
            '4': PaymentStatus.REFUNDED.value,
            '5': PaymentStatus.CANCELLED.value,
            'pending': PaymentStatus.PENDING.value,
            'paid': PaymentStatus.PAID.value,
            'failed': PaymentStatus.FAILED.value,
            'refunded': PaymentStatus.REFUNDED.value,
            'cancelled': PaymentStatus.CANCELLED.value
        }
        
        old_status = str(row['status']).lower()
        row['status'] = status_map.get(old_status, PaymentStatus.PENDING.value)
        
        return row
    
    def _transform_currency(self, table: str, row: Dict) -> Dict:
        """Transform currency codes."""
        if 'currency' not in row:
            return row
        
        currency_map = {
            '$': 'USD',
            'US$': 'USD',
            'USD': 'USD',
            '€': 'EUR',
            'EUR': 'EUR',
            '£': 'GBP',
            'GBP': 'GBP',
            '¥': 'JPY',
            'JPY': 'JPY',
            'CAD': 'CAD',
            'AUD': 'AUD'
        }
        
        old_currency = str(row['currency']).strip()
        row['currency'] = currency_map.get(old_currency, old_currency)
        
        return row
    
    def _transform_amount(self, table: str, row: Dict) -> Dict:
        """Transform amount to decimal."""
        if 'amount' not in row:
            return row
        
        amount = row['amount']
        if isinstance(amount, str):
            # Remove currency symbols and commas
            amount = amount.replace('$', '').replace('€', '').replace('£', '')
            amount = amount.replace(',', '')
            try:
                row['amount'] = float(amount)
            except ValueError:
                row['amount'] = 0.0
        elif isinstance(amount, int):
            row['amount'] = float(amount)
        
        return row
    
    # ========================================================================
    # Generic Transformations
    # ========================================================================
    
    def _transform_null_to_empty(self, table: str, row: Dict) -> Dict:
        """Convert null values to empty strings."""
        for key, value in row.items():
            if value is None:
                row[key] = ''
        return row
    
    def _transform_strip_whitespace(self, table: str, row: Dict) -> Dict:
        """Strip whitespace from string fields."""
        for key, value in row.items():
            if isinstance(value, str):
                row[key] = value.strip()
        return row
    
    def _transform_lowercase(self, table: str, row: Dict) -> Dict:
        """Convert string fields to lowercase."""
        for key, value in row.items():
            if isinstance(value, str):
                row[key] = value.lower()
        return row
    
    def _transform_uppercase(self, table: str, row: Dict) -> Dict:
        """Convert string fields to uppercase."""
        for key, value in row.items():
            if isinstance(value, str):
                row[key] = value.upper()
        return row
    
    def _transform_boolean_to_int(self, table: str, row: Dict) -> Dict:
        """Convert boolean to integer (0/1)."""
        for key, value in row.items():
            if isinstance(value, bool):
                row[key] = 1 if value else 0
        return row
    
    def _transform_int_to_boolean(self, table: str, row: Dict) -> Dict:
        """Convert integer (0/1) to boolean."""
        for key, value in row.items():
            if isinstance(value, int) and value in (0, 1):
                row[key] = bool(value)
        return row
    
    def _transform_date_format(self, table: str, row: Dict) -> Dict:
        """Transform date format to ISO."""
        date_fields = ['date_of_birth', 'issue_date', 'expiry_date', 'inspection_date']
        
        for field in date_fields:
            if field in row and row[field]:
                if isinstance(row[field], str):
                    try:
                        # Try to parse date
                        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']:
                            try:
                                d = datetime.strptime(row[field], fmt).date()
                                row[field] = d.isoformat()
                                break
                            except ValueError:
                                continue
                    except Exception:
                        pass
        
        return row


# ============================================================================
# Data Validator
# ============================================================================

class DataValidator:
    """
    Validates data during and after migration.
    
    Ensures data integrity, referential integrity, and business rules.
    """
    
    def __init__(self):
        self.validation_rules = self._register_rules()
    
    def _register_rules(self) -> Dict[str, Callable]:
        """Register validation rules."""
        return {
            # Required fields
            'required': self._validate_required,
            'not_null': self._validate_not_null,
            
            # Data types
            'email': self._validate_email,
            'phone': self._validate_phone,
            'license_plate': self._validate_license_plate,
            'date': self._validate_date,
            'datetime': self._validate_datetime,
            
            # Value ranges
            'positive': self._validate_positive,
            'range': self._validate_range,
            'min_length': self._validate_min_length,
            'max_length': self._validate_max_length,
            
            # Business rules
            'future_date': self._validate_future_date,
            'past_date': self._validate_past_date,
            'unique': self._validate_unique,
            'foreign_key': self._validate_foreign_key
        }
    
    def validate_row(
        self,
        table: str,
        row: Dict[str, Any],
        rules: List[str],
        context: Optional[Dict] = None
    ) -> List[str]:
        """
        Validate a single row against rules.
        
        Args:
            table: Table name
            row: Row data
            rules: List of validation rules to apply
            context: Additional context for validation
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        context = context or {}
        
        for rule_name in rules:
            if rule_name in self.validation_rules:
                try:
                    validator = self.validation_rules[rule_name]
                    rule_errors = validator(table, row, context)
                    errors.extend(rule_errors)
                except Exception as e:
                    errors.append(f"Validation rule {rule_name} failed: {e}")
            else:
                logger.warning(f"Unknown validation rule: {rule_name}")
        
        return errors
    
    # ========================================================================
    # Required Field Validators
    # ========================================================================
    
    def _validate_required(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate required fields are present."""
        errors = []
        required_fields = context.get('required_fields', [])
        
        for field in required_fields:
            if field not in row or row[field] is None or row[field] == '':
                errors.append(f"Required field missing: {field}")
        
        return errors
    
    def _validate_not_null(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate fields are not null."""
        errors = []
        not_null_fields = context.get('not_null_fields', [])
        
        for field in not_null_fields:
            if field in row and row[field] is None:
                errors.append(f"Field cannot be null: {field}")
        
        return errors
    
    # ========================================================================
    # Data Type Validators
    # ========================================================================
    
    def _validate_email(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate email format."""
        errors = []
        email_fields = context.get('email_fields', ['email'])
        
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        for field in email_fields:
            if field in row and row[field]:
                if not email_pattern.match(row[field]):
                    errors.append(f"Invalid email format in {field}: {row[field]}")
        
        return errors
    
    def _validate_phone(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate phone number format."""
        errors = []
        phone_fields = context.get('phone_fields', ['phone'])
        
        import re
        # Simple phone validation - at least 10 digits
        phone_pattern = re.compile(r'^[\d\-\+\(\)\s]{10,}$')
        
        for field in phone_fields:
            if field in row and row[field]:
                digits = re.sub(r'\D', '', str(row[field]))
                if len(digits) < 10:
                    errors.append(f"Invalid phone number in {field}: {row[field]}")
        
        return errors
    
    def _validate_license_plate(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate license plate format."""
        errors = []
        
        if table == 'vehicles' and 'license_plate' in row and row['license_plate']:
            plate = row['license_plate']
            # Basic license plate validation - alphanumeric, 2-8 characters
            import re
            if not re.match(r'^[A-Z0-9]{2,8}$', plate.upper()):
                errors.append(f"Invalid license plate format: {plate}")
        
        return errors
    
    def _validate_date(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate date fields."""
        errors = []
        date_fields = context.get('date_fields', [])
        
        for field in date_fields:
            if field in row and row[field]:
                if isinstance(row[field], str):
                    try:
                        datetime.fromisoformat(row[field])
                    except ValueError:
                        errors.append(f"Invalid date format in {field}: {row[field]}")
        
        return errors
    
    def _validate_datetime(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate datetime fields."""
        errors = []
        datetime_fields = context.get('datetime_fields', [])
        
        for field in datetime_fields:
            if field in row and row[field]:
                if isinstance(row[field], str):
                    try:
                        datetime.fromisoformat(row[field].replace('Z', '+00:00'))
                    except ValueError:
                        errors.append(f"Invalid datetime format in {field}: {row[field]}")
        
        return errors
    
    # ========================================================================
    # Value Range Validators
    # ========================================================================
    
    def _validate_positive(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate numeric fields are positive."""
        errors = []
        positive_fields = context.get('positive_fields', [])
        
        for field in positive_fields:
            if field in row and row[field] is not None:
                try:
                    value = float(row[field])
                    if value <= 0:
                        errors.append(f"Field {field} must be positive: {value}")
                except (ValueError, TypeError):
                    errors.append(f"Field {field} is not a number: {row[field]}")
        
        return errors
    
    def _validate_range(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate fields are within range."""
        errors = []
        ranges = context.get('ranges', {})
        
        for field, (min_val, max_val) in ranges.items():
            if field in row and row[field] is not None:
                try:
                    value = float(row[field])
                    if value < min_val or value > max_val:
                        errors.append(
                            f"Field {field} out of range [{min_val}, {max_val}]: {value}"
                        )
                except (ValueError, TypeError):
                    errors.append(f"Field {field} is not a number: {row[field]}")
        
        return errors
    
    def _validate_min_length(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate minimum string length."""
        errors = []
        min_lengths = context.get('min_lengths', {})
        
        for field, min_len in min_lengths.items():
            if field in row and row[field] is not None:
                if len(str(row[field])) < min_len:
                    errors.append(
                        f"Field {field} too short (min {min_len}): {row[field]}"
                    )
        
        return errors
    
    def _validate_max_length(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate maximum string length."""
        errors = []
        max_lengths = context.get('max_lengths', {})
        
        for field, max_len in max_lengths.items():
            if field in row and row[field] is not None:
                if len(str(row[field])) > max_len:
                    errors.append(
                        f"Field {field} too long (max {max_len}): {row[field]}"
                    )
        
        return errors
    
    # ========================================================================
    # Business Rule Validators
    # ========================================================================
    
    def _validate_future_date(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate date is in the future."""
        errors = []
        future_date_fields = context.get('future_date_fields', [])
        
        now = datetime.utcnow()
        
        for field in future_date_fields:
            if field in row and row[field]:
                if isinstance(row[field], str):
                    try:
                        dt = datetime.fromisoformat(row[field])
                        if dt <= now:
                            errors.append(f"Field {field} must be in the future: {row[field]}")
                    except ValueError:
                        pass
        
        return errors
    
    def _validate_past_date(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate date is in the past."""
        errors = []
        past_date_fields = context.get('past_date_fields', [])
        
        now = datetime.utcnow()
        
        for field in past_date_fields:
            if field in row and row[field]:
                if isinstance(row[field], str):
                    try:
                        dt = datetime.fromisoformat(row[field])
                        if dt >= now:
                            errors.append(f"Field {field} must be in the past: {row[field]}")
                    except ValueError:
                        pass
        
        return errors
    
    def _validate_unique(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate field uniqueness (requires database access)."""
        # This would need to query the target database
        # Implementation depends on having access to the target session
        return []
    
    def _validate_foreign_key(self, table: str, row: Dict, context: Dict) -> List[str]:
        """Validate foreign key references (requires database access)."""
        # This would need to query the target database
        # Implementation depends on having access to the target session
        return []


# ============================================================================
# Migration Manager
# ============================================================================

class MigrationManager:
    """
    Manages data migration between databases.
    
    Handles the entire migration process including planning, execution,
    validation, and rollback.
    """
    
    def __init__(
        self,
        source_url: str,
        target_url: str,
        config: Optional[Config] = None,
        transformer: Optional[DataTransformer] = None,
        validator: Optional[DataValidator] = None
    ):
        """
        Initialize the migration manager.
        
        Args:
            source_url: Source database URL
            target_url: Target database URL
            config: Configuration object
            transformer: Data transformer
            validator: Data validator
        """
        self.source_url = source_url
        self.target_url = target_url
        self.config = config or Config()
        self.transformer = transformer or DataTransformer()
        self.validator = validator or DataValidator()
        
        # Create engines
        self.source_engine = self._create_engine(source_url)
        self.target_engine = self._create_engine(target_url)
        
        # Create sessions
        self.SourceSession = sessionmaker(bind=self.source_engine)
        self.TargetSession = sessionmaker(bind=self.target_engine)
        
        # Migration state
        self.migration_id = None
        self.migration_record = None
        self.stop_requested = False
        
        # Statistics
        self.stats = {
            'tables': {},
            'total_rows': 0,
            'migrated_rows': 0,
            'errors': 0,
            'warnings': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"MigrationManager initialized: {source_url} -> {target_url}")
    
    def _create_engine(self, db_url: str) -> Engine:
        """Create SQLAlchemy engine."""
        return create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=self.config.get('database.echo', False)
        )
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals."""
        logger.warning("Received interrupt signal, stopping migration...")
        self.stop_requested = True
    
    # ========================================================================
    # Planning Methods
    # ========================================================================
    
    def create_plan(
        self,
        tables: Optional[List[str]] = None,
        where: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[TableMigrationPlan]:
        """
        Create a migration plan.
        
        Args:
            tables: Specific tables to migrate
            where: WHERE clause for filtering
            limit: Maximum number of records per table
            
        Returns:
            List of table migration plans
        """
        logger.info("Creating migration plan...")
        
        source_inspector = inspect(self.source_engine)
        
        # Get all tables if not specified
        if not tables:
            tables = source_inspector.get_table_names()
        
        plans = []
        
        for table_name in tables:
            # Get table info
            columns = [c['name'] for c in source_inspector.get_columns(table_name)]
            
            # Count rows
            with self.SourceSession() as session:
                query = f"SELECT COUNT(*) FROM {table_name}"
                if where:
                    query += f" WHERE {where}"
                
                result = session.execute(text(query))
                row_count = result.scalar() or 0
                
                if limit and limit > 0:
                    row_count = min(row_count, limit)
            
            # Determine dependencies (simplified - would need foreign key analysis)
            dependencies = self._get_table_dependencies(table_name)
            
            # Determine if transformation needed
            transform_needed = self._is_transform_needed(table_name)
            
            # Get validation rules
            validation_rules = self._get_validation_rules(table_name)
            
            plan = TableMigrationPlan(
                table_name=table_name,
                row_count=row_count,
                columns=columns,
                dependencies=dependencies,
                transform_needed=transform_needed,
                validation_rules=validation_rules
            )
            
            plans.append(plan)
            
            logger.debug(f"Plan for {table_name}: {row_count} rows")
        
        # Sort by dependencies
        plans.sort(key=lambda p: len(p.dependencies))
        
        return plans
    
    def _get_table_dependencies(self, table_name: str) -> List[str]:
        """Get table dependencies based on foreign keys."""
        # This would need to analyze foreign key relationships
        # Simplified version
        dependencies = {
            'vehicles': ['users'],
            'reservations': ['users', 'vehicles', 'parking_spots'],
            'payments': ['users', 'reservations'],
            'notifications': ['users']
        }
        
        return dependencies.get(table_name, [])
    
    def _is_transform_needed(self, table_name: str) -> bool:
        """Determine if table needs transformation."""
        # Check if schemas are different
        source_columns = set(self._get_table_columns(self.source_engine, table_name))
        target_columns = set(self._get_table_columns(self.target_engine, table_name))
        
        return source_columns != target_columns
    
    def _get_table_columns(self, engine: Engine, table_name: str) -> List[str]:
        """Get column names for a table."""
        inspector = inspect(engine)
        return [c['name'] for c in inspector.get_columns(table_name)]
    
    def _get_validation_rules(self, table_name: str) -> List[str]:
        """Get validation rules for a table."""
        # This would be configured per table
        default_rules = ['required', 'not_null']
        
        table_rules = {
            'users': ['email', 'phone'],
            'vehicles': ['license_plate'],
            'reservations': ['datetime', 'future_date'],
            'payments': ['positive', 'range']
        }
        
        return default_rules + table_rules.get(table_name, [])
    
    # ========================================================================
    # Migration Methods
    # ========================================================================
    
    def migrate(
        self,
        tables: Optional[List[str]] = None,
        where: Optional[str] = None,
        limit: Optional[int] = None,
        batch_size: int = 1000,
        parallel: int = 4,
        transform: bool = False,
        validate: bool = False,
        dry_run: bool = False,
        force: bool = False,
        continue_on_error: bool = False
    ) -> MigrationRecord:
        """
        Perform data migration.
        
        Args:
            tables: Specific tables to migrate
            where: WHERE clause for filtering
            limit: Maximum number of records per table
            batch_size: Batch size for processing
            parallel: Number of parallel workers
            transform: Apply transformations
            validate: Validate after migration
            dry_run: Show what would be done without actually doing it
            force: Force migration even if validation fails
            continue_on_error: Continue migration if errors occur
            
        Returns:
            Migration record
        """
        self.migration_id = f"mig_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        self.stats['start_time'] = datetime.utcnow()
        
        logger.info(f"Starting migration {self.migration_id}")
        
        if dry_run:
            logger.info("DRY RUN - No changes will be applied")
        
        # Create migration plan
        plans = self.create_plan(tables, where, limit)
        
        # Show plan
        self._show_migration_plan(plans)
        
        if dry_run:
            return self._create_migration_record(plans, dry_run=True)
        
        # Initialize migration record
        self.migration_record = MigrationRecord(
            migration_id=self.migration_id,
            source=self.source_url,
            target=self.target_url,
            tables=[p.table_name for p in plans],
            status=MigrationStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        try:
            # Create target tables if they don't exist
            self._create_target_tables(plans)
            
            # Migrate tables in dependency order
            for plan in plans:
                if self.stop_requested:
                    logger.warning("Migration stopped by user")
                    break
                
                self._migrate_table(
                    plan,
                    where,
                    limit,
                    batch_size,
                    parallel,
                    transform,
                    validate,
                    dry_run,
                    continue_on_error
                )
            
            # Validate after migration if requested
            if validate and not dry_run:
                self._validate_migration(plans, continue_on_error)
            
            self.migration_record.status = MigrationStatus.COMPLETED
            self.migration_record.records_migrated = self.stats['migrated_rows']
            
            logger.info(f"Migration completed: {self.stats['migrated_rows']} rows migrated")
            
        except Exception as e:
            self.migration_record.status = MigrationStatus.FAILED
            self.migration_record.errors.append(str(e))
            logger.error(f"Migration failed: {e}")
            
            if not force:
                raise
        
        finally:
            self.migration_record.completed_at = datetime.utcnow()
            self.stats['end_time'] = datetime.utcnow()
            
            # Save migration record
            self._save_migration_record()
        
        return self.migration_record
    
    def _show_migration_plan(self, plans: List[TableMigrationPlan]) -> None:
        """Show migration plan."""
        total_rows = sum(p.row_count for p in plans)
        
        print("\n" + "="*60)
        print("MIGRATION PLAN")
        print("="*60)
        print(f"Total tables: {len(plans)}")
        print(f"Total rows: {total_rows:,}")
        print("\nTables:")
        
        for plan in plans:
            status = "✓" if plan.transform_needed else " "
            print(f"  [{status}] {plan.table_name}: {plan.row_count:,} rows")
            if plan.dependencies:
                print(f"      Depends on: {', '.join(plan.dependencies)}")
        
        print("="*60)
    
    def _create_target_tables(self, plans: List[TableMigrationPlan]) -> None:
        """Create target tables if they don't exist."""
        logger.info("Ensuring target tables exist...")
        
        # Get existing tables in target
        target_inspector = inspect(self.target_engine)
        existing_tables = set(target_inspector.get_table_names())
        
        for plan in plans:
            if plan.table_name not in existing_tables:
                logger.info(f"Creating table: {plan.table_name}")
                
                # Get table schema from source
                source_inspector = inspect(self.source_engine)
                columns = source_inspector.get_columns(plan.table_name)
                
                # Build CREATE TABLE statement
                col_defs = []
                for col in columns:
                    col_type = self._get_sqlalchemy_type(col)
                    nullable = "NOT NULL" if not col['nullable'] else ""
                    default = f"DEFAULT {col['default']}" if col['default'] else ""
                    col_defs.append(f"{col['name']} {col_type} {nullable} {default}".strip())
                
                create_stmt = f"""
                    CREATE TABLE IF NOT EXISTS {plan.table_name} (
                        {', '.join(col_defs)}
                    )
                """
                
                with self.TargetSession() as session:
                    session.execute(text(create_stmt))
                    session.commit()
    
    def _get_sqlalchemy_type(self, column_info: Dict) -> str:
        """Get SQLAlchemy type string from column info."""
        type_map = {
            'INTEGER': 'INTEGER',
            'VARCHAR': f"VARCHAR({column_info.get('length', 255)})",
            'TEXT': 'TEXT',
            'BOOLEAN': 'BOOLEAN',
            'DATETIME': 'TIMESTAMP',
            'DATE': 'DATE',
            'FLOAT': 'FLOAT',
            'DECIMAL': f"DECIMAL({column_info.get('precision', 10)},{column_info.get('scale', 2)})"
        }
        
        col_type = str(column_info['type']).upper()
        for key, value in type_map.items():
            if key in col_type:
                return value
        
        return 'TEXT'
    
    def _migrate_table(
        self,
        plan: TableMigrationPlan,
        where: Optional[str],
        limit: Optional[int],
        batch_size: int,
        parallel: int,
        transform: bool,
        validate: bool,
        dry_run: bool,
        continue_on_error: bool
    ) -> None:
        """Migrate a single table."""
        logger.info(f"Migrating table: {plan.table_name} ({plan.row_count} rows)")
        
        if plan.row_count == 0:
            logger.info(f"Table {plan.table_name} has no data, skipping")
            return
        
        # Determine which columns to migrate
        source_columns = plan.columns
        target_columns = self._get_table_columns(self.target_engine, plan.table_name)
        
        # Find common columns
        common_columns = set(source_columns) & set(target_columns)
        
        if not common_columns:
            logger.warning(f"No common columns for {plan.table_name}, skipping")
            return
        
        columns_list = list(common_columns)
        columns_str = ', '.join(columns_list)
        placeholders = ', '.join([f':{col}' for col in columns_list])
        
        # Build SELECT query
        select_query = f"SELECT {columns_str} FROM {plan.table_name}"
        if where:
            select_query += f" WHERE {where}"
        
        if limit and limit > 0:
            select_query += f" LIMIT {limit}"
        
        # Determine transformations
        transformations = []
        if transform and plan.transform_needed:
            transformations = self._get_table_transformations(plan.table_name)
        
        # Determine validation rules
        validation_rules = []
        if validate:
            validation_rules = plan.validation_rules
        
        # Process in parallel
        if parallel > 1 and plan.row_count > batch_size * 2:
            self._migrate_table_parallel(
                plan, select_query, columns_list, placeholders,
                transformations, validation_rules, batch_size, parallel,
                dry_run, continue_on_error
            )
        else:
            self._migrate_table_sequential(
                plan, select_query, columns_list, placeholders,
                transformations, validation_rules, batch_size,
                dry_run, continue_on_error
            )
        
        logger.info(f"Table {plan.table_name} migration completed: {plan.processed} rows")
    
    def _migrate_table_sequential(
        self,
        plan: TableMigrationPlan,
        select_query: str,
        columns: List[str],
        placeholders: str,
        transformations: List[str],
        validation_rules: List[str],
        batch_size: int,
        dry_run: bool,
        continue_on_error: bool
    ) -> None:
        """Migrate table sequentially."""
        offset = 0
        
        with self.SourceSession() as source_session:
            while not self.stop_requested:
                # Fetch batch
                query = f"{select_query} ORDER BY id LIMIT {batch_size} OFFSET {offset}"
                result = source_session.execute(text(query))
                rows = [dict(row._mapping) for row in result]
                
                if not rows:
                    break
                
                if not dry_run:
                    self._process_batch(
                        plan, rows, columns, placeholders,
                        transformations, validation_rules,
                        continue_on_error
                    )
                
                plan.processed += len(rows)
                offset += batch_size
                
                logger.debug(f"  Processed {plan.processed}/{plan.row_count} rows")
    
    def _migrate_table_parallel(
        self,
        plan: TableMigrationPlan,
        select_query: str,
        columns: List[str],
        placeholders: str,
        transformations: List[str],
        validation_rules: List[str],
        batch_size: int,
        parallel: int,
        dry_run: bool,
        continue_on_error: bool
    ) -> None:
        """Migrate table in parallel using multiple workers."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Calculate number of batches
        num_batches = (plan.row_count + batch_size - 1) // batch_size
        
        # Create batch queue
        batch_queue = queue.Queue()
        for batch_num in range(num_batches):
            offset = batch_num * batch_size
            batch_queue.put({
                'batch_num': batch_num,
                'offset': offset,
                'limit': batch_size
            })
        
        # Progress tracking
        processed = 0
        lock = threading.Lock()
        
        def worker():
            """Worker function for parallel processing."""
            local_processed = 0
            
            with self.SourceSession() as source_session:
                while not batch_queue.empty() and not self.stop_requested:
                    try:
                        batch_info = batch_queue.get(timeout=1)
                        
                        # Fetch batch
                        query = f"{select_query} ORDER BY id LIMIT {batch_info['limit']} OFFSET {batch_info['offset']}"
                        result = source_session.execute(text(query))
                        rows = [dict(row._mapping) for row in result]
                        
                        if rows and not dry_run:
                            self._process_batch(
                                plan, rows, columns, placeholders,
                                transformations, validation_rules,
                                continue_on_error,
                                session_maker=self.TargetSession
                            )
                        
                        local_processed += len(rows)
                        
                        # Update progress
                        with lock:
                            nonlocal processed
                            processed += len(rows)
                            if processed % (batch_size * 10) == 0:
                                logger.debug(f"  Progress: {processed}/{plan.row_count} rows")
                        
                    except queue.Empty:
                        break
                    except Exception as e:
                        logger.error(f"Worker error: {e}")
                        if not continue_on_error:
                            raise
            
            return local_processed
        
        # Start workers
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            futures = [executor.submit(worker) for _ in range(parallel)]
            
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
                    if not continue_on_error:
                        raise
        
        plan.processed = processed
    
    def _process_batch(
        self,
        plan: TableMigrationPlan,
        rows: List[Dict],
        columns: List[str],
        placeholders: str,
        transformations: List[str],
        validation_rules: List[str],
        continue_on_error: bool,
        session_maker: Optional[sessionmaker] = None
    ) -> None:
        """Process a batch of rows."""
        session_maker = session_maker or self.TargetSession
        
        with session_maker() as target_session:
            for row in rows:
                try:
                    # Apply transformations
                    if transformations:
                        row = self.transformer.transform_row(
                            plan.table_name,
                            row,
                            transformations
                        )
                    
                    # Validate
                    if validation_rules:
                        context = {
                            'required_fields': columns,
                            'not_null_fields': columns
                        }
                        errors = self.validator.validate_row(
                            plan.table_name,
                            row,
                            validation_rules,
                            context
                        )
                        
                        if errors:
                            self.migration_record.warnings.extend(errors)
                            self.stats['warnings'] += 1
                            if not continue_on_error:
                                raise ValidationError(f"Validation failed: {errors}")
                    
                    # Insert
                    insert_stmt = text(
                        f"INSERT INTO {plan.table_name} ({', '.join(columns)}) "
                        f"VALUES ({placeholders}) "
                        f"ON CONFLICT (id) DO UPDATE SET "
                        f"{', '.join([f'{c}=EXCLUDED.{c}' for c in columns])}"
                    )
                    
                    target_session.execute(insert_stmt, row)
                    
                    self.stats['migrated_rows'] += 1
                    
                except Exception as e:
                    self.migration_record.errors.append(str(e))
                    self.stats['errors'] += 1
                    
                    if not continue_on_error:
                        raise
            
            target_session.commit()
    
    def _get_table_transformations(self, table_name: str) -> List[str]:
        """Get transformations for a table."""
        # This would be configured per table
        transformations = {
            'users': ['user_status', 'user_role', 'strip_whitespace'],
            'vehicles': ['vehicle_type', 'vehicle_status', 'license_plate'],
            'reservations': ['reservation_status', 'datetime_format'],
            'payments': ['payment_status', 'currency', 'amount']
        }
        
        return transformations.get(table_name, ['strip_whitespace'])
    
    def _validate_migration(
        self,
        plans: List[TableMigrationPlan],
        continue_on_error: bool
    ) -> None:
        """Validate migration by comparing row counts."""
        logger.info("Validating migration...")
        
        with self.SourceSession() as source_session:
            with self.TargetSession() as target_session:
                for plan in plans:
                    # Count rows in source
                    source_count = source_session.execute(
                        text(f"SELECT COUNT(*) FROM {plan.table_name}")
                    ).scalar() or 0
                    
                    # Count rows in target
                    target_count = target_session.execute(
                        text(f"SELECT COUNT(*) FROM {plan.table_name}")
                    ).scalar() or 0
                    
                    if source_count != target_count:
                        msg = f"Row count mismatch for {plan.table_name}: source={source_count}, target={target_count}"
                        self.migration_record.warnings.append(msg)
                        self.stats['warnings'] += 1
                        
                        if not continue_on_error:
                            raise ValidationError(msg)
                    else:
                        logger.info(f"✓ {plan.table_name}: {source_count} rows")
    
    def _create_migration_record(
        self,
        plans: List[TableMigrationPlan],
        dry_run: bool = False
    ) -> MigrationRecord:
        """Create a migration record."""
        return MigrationRecord(
            migration_id=self.migration_id,
            source=self.source_url,
            target=self.target_url,
            tables=[p.table_name for p in plans],
            status=MigrationStatus.VALIDATED if dry_run else MigrationStatus.COMPLETED,
            started_at=self.stats['start_time'],
            completed_at=datetime.utcnow(),
            records_migrated=self.stats['migrated_rows']
        )
    
    def _save_migration_record(self) -> None:
        """Save migration record to file."""
        records_dir = Path('./migration_records')
        records_dir.mkdir(exist_ok=True)
        
        record_file = records_dir / f"{self.migration_id}.json"
        
        with open(record_file, 'w') as f:
            json.dump(self.migration_record.to_dict(), f, indent=2)
        
        logger.info(f"Migration record saved: {record_file}")
    
    # ========================================================================
    # Validation Methods
    # ========================================================================
    
    def validate(
        self,
        tables: Optional[List[str]] = None,
        where: Optional[str] = None,
        limit: Optional[int] = None,
        batch_size: int = 1000,
        continue_on_error: bool = False
    ) -> Dict[str, Any]:
        """
        Validate data without migrating.
        
        Args:
            tables: Specific tables to validate
            where: WHERE clause for filtering
            limit: Maximum number of records per table
            batch_size: Batch size for processing
            continue_on_error: Continue validation if errors occur
            
        Returns:
            Validation results
        """
        logger.info("Starting data validation...")
        
        results = {
            'valid': True,
            'tables': {},
            'total_rows': 0,
            'errors': 0,
            'warnings': 0
        }
        
        plans = self.create_plan(tables, where, limit)
        
        for plan in plans:
            logger.info(f"Validating table: {plan.table_name}")
            
            table_results = self._validate_table(
                plan, where, limit, batch_size, continue_on_error
            )
            
            results['tables'][plan.table_name] = table_results
            results['total_rows'] += table_results['rows_checked']
            results['errors'] += table_results['errors']
            results['warnings'] += table_results['warnings']
            
            if table_results['errors'] > 0:
                results['valid'] = False
        
        logger.info(f"Validation complete: {results['total_rows']} rows checked, "
                   f"{results['errors']} errors, {results['warnings']} warnings")
        
        return results
    
    def _validate_table(
        self,
        plan: TableMigrationPlan,
        where: Optional[str],
        limit: Optional[int],
        batch_size: int,
        continue_on_error: bool
    ) -> Dict[str, Any]:
        """Validate a single table."""
        results = {
            'rows_checked': 0,
            'errors': 0,
            'warnings': 0,
            'error_details': []
        }
        
        # Build SELECT query
        columns_str = ', '.join(plan.columns)
        select_query = f"SELECT {columns_str} FROM {plan.table_name}"
        if where:
            select_query += f" WHERE {where}"
        
        if limit and limit > 0:
            select_query += f" LIMIT {limit}"
        
        # Get validation rules
        validation_rules = plan.validation_rules
        
        offset = 0
        
        with self.SourceSession() as source_session:
            while True:
                # Fetch batch
                query = f"{select_query} ORDER BY id LIMIT {batch_size} OFFSET {offset}"
                result = source_session.execute(text(query))
                rows = [dict(row._mapping) for row in result]
                
                if not rows:
                    break
                
                # Validate each row
                for row in rows:
                    context = {
                        'required_fields': plan.columns,
                        'not_null_fields': plan.columns
                    }
                    
                    errors = self.validator.validate_row(
                        plan.table_name,
                        row,
                        validation_rules,
                        context
                    )
                    
                    if errors:
                        results['errors'] += len(errors)
                        results['error_details'].extend(errors)
                        results['valid'] = False
                
                results['rows_checked'] += len(rows)
                offset += batch_size
        
        return results
    
    # ========================================================================
    # Rollback Methods
    # ========================================================================
    
    def rollback(self, migration_id: Optional[str] = None) -> bool:
        """
        Rollback a migration.
        
        Args:
            migration_id: Migration ID to rollback (defaults to last)
            
        Returns:
            True if rollback successful
        """
        logger.info(f"Rolling back migration: {migration_id or 'last'}")
        
        # Find migration record
        record = self._find_migration_record(migration_id)
        
        if not record:
            logger.error(f"Migration record not found: {migration_id}")
            return False
        
        # Rollback tables in reverse order
        for table_name in reversed(record.tables):
            logger.info(f"Rolling back table: {table_name}")
            
            try:
                with self.TargetSession() as session:
                    # Delete all rows from this migration
                    # This assumes we have a way to identify rows from this migration
                    # For now, truncate the table (simplified)
                    session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                    session.commit()
                    
            except Exception as e:
                logger.error(f"Rollback failed for {table_name}: {e}")
                raise RollbackError(f"Rollback failed: {e}")
        
        logger.info("Rollback completed")
        return True
    
    def _find_migration_record(self, migration_id: Optional[str]) -> Optional[MigrationRecord]:
        """Find migration record by ID."""
        records_dir = Path('./migration_records')
        
        if not records_dir.exists():
            return None
        
        if migration_id:
            record_file = records_dir / f"{migration_id}.json"
            if record_file.exists():
                with open(record_file, 'r') as f:
                    data = json.load(f)
                    return MigrationRecord(**data)
        else:
            # Find most recent
            record_files = list(records_dir.glob('*.json'))
            if record_files:
                latest = max(record_files, key=lambda p: p.stat().st_mtime)
                with open(latest, 'r') as f:
                    data = json.load(f)
                    return MigrationRecord(**data)
        
        return None
    
    # ========================================================================
    # Status Methods
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get migration status."""
        return {
            'current_migration': self.migration_id,
            'stats': self.stats,
            'stop_requested': self.stop_requested
        }
    
    def list_migrations(self) -> List[Dict[str, Any]]:
        """List all migrations."""
        records_dir = Path('./migration_records')
        migrations = []
        
        if records_dir.exists():
            for record_file in sorted(records_dir.glob('*.json'), reverse=True):
                with open(record_file, 'r') as f:
                    data = json.load(f)
                    migrations.append(data)
        
        return migrations
    
    # ========================================================================
    # Cleanup Methods
    # ========================================================================
    
    def cleanup(self, days: int = 30) -> int:
        """
        Clean up old migration records.
        
        Args:
            days: Delete records older than N days
            
        Returns:
            Number of records deleted
        """
        records_dir = Path('./migration_records')
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = 0
        
        if records_dir.exists():
            for record_file in records_dir.glob('*.json'):
                # Check file modification time
                mtime = datetime.fromtimestamp(record_file.stat().st_mtime)
                if mtime < cutoff:
                    record_file.unlink()
                    deleted += 1
                    logger.info(f"Deleted old migration record: {record_file}")
        
        return deleted


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
    parser = argparse.ArgumentParser(description='Data migration utility')
    parser.add_argument('command', choices=['migrate', 'validate', 'rollback', 'status', 'plan', 'transform', 'cleanup'],
                       help='Command to execute')
    
    # Database options
    parser.add_argument('--source', help='Source database URL')
    parser.add_argument('--target', help='Target database URL')
    parser.add_argument('--config', help='Configuration file path')
    
    # Migration options
    parser.add_argument('--tables', help='Specific tables to migrate (comma-separated)')
    parser.add_argument('--where', help='WHERE clause for filtering data')
    parser.add_argument('--limit', type=int, help='Maximum number of records per table')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for processing')
    parser.add_argument('--parallel', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--transform', action='store_true', help='Apply transformations')
    parser.add_argument('--validate', action='store_true', help='Validate after migration')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--force', action='store_true', help='Force migration even if validation fails')
    parser.add_argument('--continue-on-error', action='store_true', help='Continue if errors occur')
    
    # Rollback options
    parser.add_argument('--migration-id', help='Migration ID for rollback')
    
    # Cleanup options
    parser.add_argument('--days', type=int, default=30, help='Delete records older than N days')
    
    # General options
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
    
    # Parse tables
    tables = parse_tables(args.tables)
    
    try:
        if args.command in ['migrate', 'validate', 'plan']:
            # These commands require source and target
            if not args.source or not args.target:
                parser.error(f"{args.command} requires --source and --target")
            
            # Create migration manager
            manager = MigrationManager(
                source_url=args.source,
                target_url=args.target,
                config=config
            )
            
            if args.command == 'migrate':
                # Perform migration
                record = manager.migrate(
                    tables=tables,
                    where=args.where,
                    limit=args.limit,
                    batch_size=args.batch_size,
                    parallel=args.parallel,
                    transform=args.transform,
                    validate=args.validate,
                    dry_run=args.dry_run,
                    force=args.force,
                    continue_on_error=args.continue_on_error
                )
                
                if not args.dry_run:
                    print(f"\nMigration {record.migration_id} completed:")
                    print(f"  Rows migrated: {record.records_migrated}")
                    print(f"  Duration: {(record.completed_at - record.started_at).total_seconds():.2f}s")
                    
                    if record.warnings:
                        print(f"  Warnings: {len(record.warnings)}")
                    
                    if record.errors:
                        print(f"  Errors: {len(record.errors)}")
                        sys.exit(1)
            
            elif args.command == 'validate':
                # Validate data
                results = manager.validate(
                    tables=tables,
                    where=args.where,
                    limit=args.limit,
                    batch_size=args.batch_size,
                    continue_on_error=args.continue_on_error
                )
                
                print(f"\nValidation {'PASSED' if results['valid'] else 'FAILED'}:")
                print(f"  Rows checked: {results['total_rows']}")
                print(f"  Errors: {results['errors']}")
                print(f"  Warnings: {results['warnings']}")
                
                if not results['valid']:
                    print("\nFirst 10 errors:")
                    for table, table_results in results['tables'].items():
                        for error in table_results.get('error_details', [])[:10]:
                            print(f"  {table}: {error}")
                    
                    sys.exit(1)
            
            elif args.command == 'plan':
                # Show migration plan
                plans = manager.create_plan(tables, args.where, args.limit)
                # Plan already printed by create_plan
        
        elif args.command == 'rollback':
            # Rollback requires target
            if not args.target:
                parser.error("rollback requires --target")
            
            manager = MigrationManager(
                source_url='',  # Not needed for rollback
                target_url=args.target,
                config=config
            )
            
            success = manager.rollback(args.migration_id)
            
            if success:
                print(f"\nRollback {'completed' if success else 'failed'}")
                sys.exit(0 if success else 1)
        
        elif args.command == 'status':
            # Show migration status
            manager = MigrationManager(
                source_url='',  # Not needed for status
                target_url='',
                config=config
            )
            
            migrations = manager.list_migrations()
            
            print(f"\nRecent migrations ({len(migrations)}):")
            for mig in migrations[:10]:
                print(f"  {mig['migration_id']}: {mig['status']} - {mig['started_at']} - {mig['records_migrated']} rows")
        
        elif args.command == 'cleanup':
            # Clean up old records
            manager = MigrationManager(
                source_url='',
                target_url='',
                config=config
            )
            
            deleted = manager.cleanup(args.days)
            print(f"\nDeleted {deleted} old migration records")
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()