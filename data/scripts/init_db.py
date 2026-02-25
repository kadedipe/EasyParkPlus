#!/usr/bin/env python3
"""
Database initialization script for the parking management system.

This script creates all database tables, indexes, constraints, and loads
initial data required for the system to function. It also sets up database
users, permissions, and performs initial migrations.

Usage:
    python init_db.py [--drop-existing] [--seed-data] [--create-admin]
                     [--db-url DATABASE_URL] [--config CONFIG_FILE]

Options:
    --drop-existing     Drop existing tables before creating new ones
    --seed-data        Load initial seed data
    --create-admin     Create default admin user
    --db-url           Database connection URL
    --config           Configuration file path
    --help             Show this help message
"""

import os
import sys
import argparse
import logging
import getpass
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import hashlib
import secrets

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import (
    create_engine, text, inspect, MetaData, Table, Column,
    Integer, String, DateTime, Boolean, Float, ForeignKey,
    Index, UniqueConstraint, event
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.orm import sessionmaker, Session

from data.migrations.models import (
    Base,
    User, UserProfile, UserPreference, UserSession, UserDevice, UserAuditLog,
    Role, Permission, RoleAssignment,
    Vehicle, VehicleRegistration, VehicleInsurance, VehicleInspection,
    VehicleOwnership, VehicleDocument, VehicleImage, VehicleHistory,
    ParkingSpot, ParkingZone, SpotMaintenance, SpotSensor,
    Reservation, RecurringReservation, Waitlist,
    Payment, Invoice, Subscription, Discount,
    Notification, NotificationTemplate, NotificationPreference,
    AuditLog, ComplianceLog,
    SystemConfig, FeatureFlag
)
from data.migrations.models.enums import (
    UserStatus, UserRole, AuthMethod,
    VehicleStatus, VehicleType, FuelType,
    SpotType, SpotStatus, ZoneType,
    ReservationStatus, ReservationType,
    PaymentStatus, PaymentMethodType, Currency,
    NotificationType, NotificationChannel,
    AuditAction, AuditCategory, AuditSeverity
)
from data.repositories import (
    UserRepository, RoleRepository, PermissionRepository,
    VehicleRepository, ParkingSpotRepository, ReservationRepository,
    PaymentRepository, NotificationRepository, AuditLogRepository,
    SystemConfigRepository
)
from data.services import (
    DataService, EncryptionService, BackupService,
    MigrationService, NotificationService
)
from utils.config import Config
from utils.logging import setup_logging

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Database Initializer
# ============================================================================

class DatabaseInitializer:
    """
    Database initialization and setup utility.
    
    Handles:
    - Database connection and validation
    - Table creation/dropping
    - Index and constraint creation
    - Initial data loading
    - Admin user creation
    - Migration execution
    """
    
    def __init__(
        self,
        db_url: str,
        config: Optional[Config] = None,
        drop_existing: bool = False,
        seed_data: bool = False,
        create_admin: bool = False
    ):
        """
        Initialize the database initializer.
        
        Args:
            db_url: Database connection URL
            config: Configuration object
            drop_existing: Whether to drop existing tables
            seed_data: Whether to load seed data
            create_admin: Whether to create admin user
        """
        self.db_url = db_url
        self.config = config or Config()
        self.drop_existing = drop_existing
        self.seed_data = seed_data
        self.create_admin = create_admin
        
        # Create engine
        self.engine = create_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=self.config.get('database.echo', False)
        )
        
        # Create session factory
        self.Session = sessionmaker(bind=self.engine)
        
        logger.info(f"Database initializer created for {db_url}")
    
    def initialize(self) -> bool:
        """
        Initialize the database.
        
        Returns:
            True if successful
        """
        try:
            # Step 1: Test connection
            self._test_connection()
            
            # Step 2: Create extensions (PostgreSQL only)
            self._create_extensions()
            
            # Step 3: Drop existing tables if requested
            if self.drop_existing:
                self._drop_tables()
            
            # Step 4: Create tables
            self._create_tables()
            
            # Step 5: Create indexes
            self._create_indexes()
            
            # Step 6: Create constraints
            self._create_constraints()
            
            # Step 7: Run initial migrations
            self._run_migrations()
            
            # Step 8: Load initial data
            self._load_initial_data()
            
            # Step 9: Create admin user if requested
            if self.create_admin:
                self._create_admin_user()
            
            # Step 10: Load seed data if requested
            if self.seed_data:
                self._load_seed_data()
            
            # Step 11: Verify initialization
            self._verify_initialization()
            
            logger.info("Database initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def _test_connection(self) -> None:
        """Test database connection."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("Database connection successful")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def _create_extensions(self) -> None:
        """Create database extensions (PostgreSQL)."""
        if 'postgresql' in self.db_url:
            with self.Session() as session:
                # Enable UUID extension
                session.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                
                # Enable full-text search
                session.execute(text('CREATE EXTENSION IF NOT EXISTS "pg_trgm"'))
                
                # Enable statistics functions
                session.execute(text('CREATE EXTENSION IF NOT EXISTS "tablefunc"'))
                
                session.commit()
                logger.info("Database extensions created")
    
    def _drop_tables(self) -> None:
        """Drop all existing tables."""
        logger.warning("Dropping all existing tables...")
        
        # Reflect existing tables
        metadata = MetaData()
        metadata.reflect(bind=self.engine)
        
        # Drop in reverse order (respect foreign keys)
        metadata.drop_all(bind=self.engine, checkfirst=True)
        
        logger.info(f"Dropped {len(metadata.tables)} tables")
    
    def _create_tables(self) -> None:
        """Create all tables."""
        logger.info("Creating database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=self.engine)
        
        # Count created tables
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        
        logger.info(f"Created {len(tables)} tables: {', '.join(tables)}")
    
    def _create_indexes(self) -> None:
        """Create additional indexes for performance."""
        logger.info("Creating indexes...")
        
        with self.Session() as session:
            # User indexes
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
                CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
            """))
            
            # Vehicle indexes
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_vehicles_license_plate ON vehicles(license_plate);
                CREATE INDEX IF NOT EXISTS idx_vehicles_vin ON vehicles(vin);
                CREATE INDEX IF NOT EXISTS idx_vehicles_user_id ON vehicles(user_id);
                CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status);
                CREATE INDEX IF NOT EXISTS idx_vehicles_type ON vehicles(vehicle_type);
            """))
            
            # Parking spot indexes
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_spots_zone_id ON parking_spots(zone_id);
                CREATE INDEX IF NOT EXISTS idx_spots_status ON parking_spots(status);
                CREATE INDEX IF NOT EXISTS idx_spots_type ON parking_spots(spot_type);
                CREATE INDEX IF NOT EXISTS idx_spots_spot_number ON parking_spots(zone_id, spot_number);
            """))
            
            # Reservation indexes
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_reservations_user_id ON reservations(user_id);
                CREATE INDEX IF NOT EXISTS idx_reservations_spot_id ON reservations(spot_id);
                CREATE INDEX IF NOT EXISTS idx_reservations_status ON reservations(status);
                CREATE INDEX IF NOT EXISTS idx_reservations_dates ON reservations(start_time, end_time);
                CREATE INDEX IF NOT EXISTS idx_reservations_confirmation ON reservations(confirmation_code);
            """))
            
            # Payment indexes
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
                CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
                CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at);
                CREATE INDEX IF NOT EXISTS idx_payments_transaction_id ON payments(transaction_id);
            """))
            
            # Audit log indexes
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_id ON audit_logs(actor_id);
                CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
                CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
                CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
            """))
            
            # Full-text search indexes
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_search ON users 
                USING gin(to_tsvector('english', coalesce(email,'') || ' ' || 
                                       coalesce(first_name,'') || ' ' || coalesce(last_name,'')));
                
                CREATE INDEX IF NOT EXISTS idx_vehicles_search ON vehicles 
                USING gin(to_tsvector('english', coalesce(license_plate,'') || ' ' || 
                                       coalesce(make,'') || ' ' || coalesce(model,'')));
            """))
            
            session.commit()
            
        logger.info("Indexes created")
    
    def _create_constraints(self) -> None:
        """Create additional constraints."""
        logger.info("Creating constraints...")
        
        with self.Session() as session:
            # Check constraints
            session.execute(text("""
                ALTER TABLE users ADD CONSTRAINT IF NOT EXISTS chk_users_email_format
                CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
                
                ALTER TABLE vehicles ADD CONSTRAINT IF NOT EXISTS chk_vehicles_year
                CHECK (year >= 1900 AND year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1);
                
                ALTER TABLE reservations ADD CONSTRAINT IF NOT EXISTS chk_reservations_dates
                CHECK (end_time > start_time);
                
                ALTER TABLE payments ADD CONSTRAINT IF NOT EXISTS chk_payments_amount
                CHECK (amount > 0);
            """))
            
            session.commit()
            
        logger.info("Constraints created")
    
    def _run_migrations(self) -> None:
        """Run initial database migrations."""
        logger.info("Running initial migrations...")
        
        with self.Session() as session:
            # Create migration service
            migration_service = MigrationService(
                session=session,
                migrations_dir="./migrations",
                backup_service=None,
                notification_service=None
            )
            
            # Run migrations to latest
            job = migration_service.migrate()
            
            if job.status == 'completed':
                logger.info(f"Migrations completed: {len(job.migrations)} applied")
            else:
                logger.error(f"Migrations failed: {job.error}")
                raise Exception(f"Migration failed: {job.error}")
    
    def _load_initial_data(self) -> None:
        """Load initial system data."""
        logger.info("Loading initial data...")
        
        with self.Session() as session:
            data_service = DataService(session)
            
            # Load default roles and permissions
            self._load_roles_and_permissions(session)
            
            # Load default system configuration
            self._load_system_config(session)
            
            # Load default notification templates
            self._load_notification_templates(session)
            
            # Load default parking rates
            self._load_default_rates(session)
            
            # Load default subscription plans
            self._load_subscription_plans(session)
            
            session.commit()
            
        logger.info("Initial data loaded")
    
    def _load_roles_and_permissions(self, session: Session) -> None:
        """Load default roles and permissions."""
        logger.info("Loading roles and permissions...")
        
        role_repo = RoleRepository(session)
        permission_repo = PermissionRepository(session)
        
        # Define roles
        roles = [
            {'name': 'user', 'description': 'Regular user'},
            {'name': 'operator', 'description': 'Parking operator'},
            {'name': 'manager', 'description': 'Parking manager'},
            {'name': 'admin', 'description': 'Administrator'},
            {'name': 'super_admin', 'description': 'Super administrator'}
        ]
        
        for role_data in roles:
            existing = role_repo.get_by_name(role_data['name'])
            if not existing:
                role = Role(**role_data)
                session.add(role)
        
        session.flush()
        
        # Define permissions
        permissions = [
            # User permissions
            {'name': 'user:view', 'resource_type': 'user', 'action': 'view', 'description': 'View users'},
            {'name': 'user:create', 'resource_type': 'user', 'action': 'create', 'description': 'Create users'},
            {'name': 'user:edit', 'resource_type': 'user', 'action': 'edit', 'description': 'Edit users'},
            {'name': 'user:delete', 'resource_type': 'user', 'action': 'delete', 'description': 'Delete users'},
            
            # Vehicle permissions
            {'name': 'vehicle:view', 'resource_type': 'vehicle', 'action': 'view', 'description': 'View vehicles'},
            {'name': 'vehicle:create', 'resource_type': 'vehicle', 'action': 'create', 'description': 'Create vehicles'},
            {'name': 'vehicle:edit', 'resource_type': 'vehicle', 'action': 'edit', 'description': 'Edit vehicles'},
            {'name': 'vehicle:delete', 'resource_type': 'vehicle', 'action': 'delete', 'description': 'Delete vehicles'},
            
            # Parking permissions
            {'name': 'parking:view', 'resource_type': 'parking', 'action': 'view', 'description': 'View parking'},
            {'name': 'parking:manage', 'resource_type': 'parking', 'action': 'manage', 'description': 'Manage parking'},
            {'name': 'parking:configure', 'resource_type': 'parking', 'action': 'configure', 'description': 'Configure parking'},
            
            # Reservation permissions
            {'name': 'reservation:view', 'resource_type': 'reservation', 'action': 'view', 'description': 'View reservations'},
            {'name': 'reservation:create', 'resource_type': 'reservation', 'action': 'create', 'description': 'Create reservations'},
            {'name': 'reservation:cancel', 'resource_type': 'reservation', 'action': 'cancel', 'description': 'Cancel reservations'},
            {'name': 'reservation:modify', 'resource_type': 'reservation', 'action': 'modify', 'description': 'Modify reservations'},
            
            # Payment permissions
            {'name': 'payment:view', 'resource_type': 'payment', 'action': 'view', 'description': 'View payments'},
            {'name': 'payment:process', 'resource_type': 'payment', 'action': 'process', 'description': 'Process payments'},
            {'name': 'payment:refund', 'resource_type': 'payment', 'action': 'refund', 'description': 'Refund payments'},
            
            # Report permissions
            {'name': 'report:view', 'resource_type': 'report', 'action': 'view', 'description': 'View reports'},
            {'name': 'report:generate', 'resource_type': 'report', 'action': 'generate', 'description': 'Generate reports'},
            {'name': 'report:export', 'resource_type': 'report', 'action': 'export', 'description': 'Export reports'},
            
            # Admin permissions
            {'name': 'admin:access', 'resource_type': 'admin', 'action': 'access', 'description': 'Access admin'},
            {'name': 'admin:configure', 'resource_type': 'admin', 'action': 'configure', 'description': 'Configure system'},
            {'name': 'admin:audit', 'resource_type': 'admin', 'action': 'audit', 'description': 'View audit logs'}
        ]
        
        for perm_data in permissions:
            existing = permission_repo.get_by_name(perm_data['name'])
            if not existing:
                permission = Permission(**perm_data)
                session.add(permission)
        
        logger.info(f"Loaded {len(roles)} roles and {len(permissions)} permissions")
    
    def _load_system_config(self, session: Session) -> None:
        """Load default system configuration."""
        logger.info("Loading system configuration...")
        
        config_repo = SystemConfigRepository(session)
        
        configs = [
            # General settings
            {'key': 'system.name', 'value': 'Parking Management System', 'type': 'string', 'category': 'general'},
            {'key': 'system.timezone', 'value': 'UTC', 'type': 'string', 'category': 'general'},
            {'key': 'system.locale', 'value': 'en_US', 'type': 'string', 'category': 'general'},
            
            # Business settings
            {'key': 'business.name', 'value': 'Parking Co.', 'type': 'string', 'category': 'business'},
            {'key': 'business.email', 'value': 'info@parking.com', 'type': 'string', 'category': 'business'},
            {'key': 'business.phone', 'value': '+1234567890', 'type': 'string', 'category': 'business'},
            {'key': 'business.address', 'value': '123 Main St', 'type': 'string', 'category': 'business'},
            
            # Payment settings
            {'key': 'payment.currency', 'value': 'USD', 'type': 'string', 'category': 'payment'},
            {'key': 'payment.tax_rate', 'value': '0.0', 'type': 'float', 'category': 'payment'},
            {'key': 'payment.deposit_required', 'value': 'false', 'type': 'boolean', 'category': 'payment'},
            {'key': 'payment.deposit_amount', 'value': '0.0', 'type': 'float', 'category': 'payment'},
            
            # Reservation settings
            {'key': 'reservation.max_duration_hours', 'value': '24', 'type': 'integer', 'category': 'reservation'},
            {'key': 'reservation.min_advance_minutes', 'value': '15', 'type': 'integer', 'category': 'reservation'},
            {'key': 'reservation.max_advance_days', 'value': '30', 'type': 'integer', 'category': 'reservation'},
            {'key': 'reservation.cancellation_window_minutes', 'value': '60', 'type': 'integer', 'category': 'reservation'},
            {'key': 'reservation.no_show_grace_minutes', 'value': '15', 'type': 'integer', 'category': 'reservation'},
            
            # Security settings
            {'key': 'security.password_min_length', 'value': '8', 'type': 'integer', 'category': 'security'},
            {'key': 'security.password_require_uppercase', 'value': 'true', 'type': 'boolean', 'category': 'security'},
            {'key': 'security.password_require_numbers', 'value': 'true', 'type': 'boolean', 'category': 'security'},
            {'key': 'security.max_login_attempts', 'value': '5', 'type': 'integer', 'category': 'security'},
            {'key': 'security.lockout_minutes', 'value': '30', 'type': 'integer', 'category': 'security'},
            {'key': 'security.session_timeout_minutes', 'value': '120', 'type': 'integer', 'category': 'security'},
            {'key': 'security.mfa_required', 'value': 'false', 'type': 'boolean', 'category': 'security'},
            
            # Notification settings
            {'key': 'notification.email_enabled', 'value': 'true', 'type': 'boolean', 'category': 'notification'},
            {'key': 'notification.sms_enabled', 'value': 'false', 'type': 'boolean', 'category': 'notification'},
            {'key': 'notification.push_enabled', 'value': 'true', 'type': 'boolean', 'category': 'notification'},
            {'key': 'notification.from_email', 'value': 'noreply@parking.com', 'type': 'string', 'category': 'notification'},
            
            # Feature flags
            {'key': 'feature.dynamic_pricing', 'value': 'false', 'type': 'boolean', 'category': 'feature'},
            {'key': 'feature.loyalty_program', 'value': 'false', 'type': 'boolean', 'category': 'feature'},
            {'key': 'feature.valet_service', 'value': 'false', 'type': 'boolean', 'category': 'feature'},
            {'key': 'feature.ev_charging', 'value': 'true', 'type': 'boolean', 'category': 'feature'},
            {'key': 'feature.biometric_auth', 'value': 'false', 'type': 'boolean', 'category': 'feature'}
        ]
        
        for config_data in configs:
            existing = config_repo.get_by_key(config_data['key'])
            if not existing:
                config = SystemConfig(**config_data)
                session.add(config)
        
        logger.info(f"Loaded {len(configs)} configuration items")
    
    def _load_notification_templates(self, session: Session) -> None:
        """Load default notification templates."""
        logger.info("Loading notification templates...")
        
        from data.models.notification_models import NotificationTemplate
        
        templates = [
            # Welcome email
            {
                'name': 'welcome_email',
                'template_type': 'email',
                'subject': 'Welcome to Parking Management System',
                'content': '''
                    <h1>Welcome {{user_name}}!</h1>
                    <p>Thank you for joining our parking management system.</p>
                    <p>Your account has been successfully created.</p>
                    <p>Get started by adding your vehicles and making your first reservation.</p>
                    <p>Best regards,<br>The Parking Team</p>
                ''',
                'channel': 'email',
                'language': 'en'
            },
            
            # Reservation confirmation
            {
                'name': 'reservation_confirmation',
                'template_type': 'email',
                'subject': 'Reservation Confirmed - {{confirmation_code}}',
                'content': '''
                    <h1>Reservation Confirmed</h1>
                    <p>Dear {{user_name}},</p>
                    <p>Your reservation has been confirmed.</p>
                    <p><strong>Confirmation Code:</strong> {{confirmation_code}}</p>
                    <p><strong>Spot:</strong> {{spot_number}}</p>
                    <p><strong>Date:</strong> {{date}}</p>
                    <p><strong>Time:</strong> {{start_time}} - {{end_time}}</p>
                    <p><strong>Vehicle:</strong> {{vehicle_info}}</p>
                    <p>Thank you for choosing us!</p>
                ''',
                'channel': 'email',
                'language': 'en'
            },
            
            # Payment receipt
            {
                'name': 'payment_receipt',
                'template_type': 'email',
                'subject': 'Payment Receipt - {{transaction_id}}',
                'content': '''
                    <h1>Payment Receipt</h1>
                    <p>Dear {{user_name}},</p>
                    <p>Thank you for your payment.</p>
                    <p><strong>Amount:</strong> {{amount}} {{currency}}</p>
                    <p><strong>Transaction ID:</strong> {{transaction_id}}</p>
                    <p><strong>Date:</strong> {{date}}</p>
                    <p><strong>Description:</strong> {{description}}</p>
                    <p>A detailed invoice is attached to this email.</p>
                ''',
                'channel': 'email',
                'language': 'en'
            },
            
            # Reminder SMS
            {
                'name': 'reservation_reminder_sms',
                'template_type': 'sms',
                'content': 'Reminder: Your parking reservation at {{spot_number}} starts in 30 minutes. Confirmation: {{confirmation_code}}',
                'channel': 'sms',
                'language': 'en'
            },
            
            # Password reset
            {
                'name': 'password_reset',
                'template_type': 'email',
                'subject': 'Password Reset Request',
                'content': '''
                    <h1>Password Reset</h1>
                    <p>Dear {{user_name}},</p>
                    <p>We received a request to reset your password.</p>
                    <p>Click the link below to reset your password:</p>
                    <p><a href="{{reset_link}}">Reset Password</a></p>
                    <p>This link will expire in 24 hours.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                ''',
                'channel': 'email',
                'language': 'en'
            }
        ]
        
        for template_data in templates:
            existing = session.query(NotificationTemplate).filter_by(
                name=template_data['name']
            ).first()
            
            if not existing:
                template = NotificationTemplate(**template_data)
                session.add(template)
        
        logger.info(f"Loaded {len(templates)} notification templates")
    
    def _load_default_rates(self, session: Session) -> None:
        """Load default parking rates."""
        logger.info("Loading default rates...")
        
        from data.models.rate_models import Rate
        
        rates = [
            # Standard rates
            {
                'name': 'Standard Hourly',
                'rate_type': 'hourly',
                'amount': 2.50,
                'currency': 'USD',
                'description': 'Standard hourly rate',
                'is_active': True
            },
            {
                'name': 'Standard Daily',
                'rate_type': 'daily',
                'amount': 20.00,
                'currency': 'USD',
                'description': 'Maximum daily rate',
                'is_active': True
            },
            {
                'name': 'Standard Weekly',
                'rate_type': 'weekly',
                'amount': 120.00,
                'currency': 'USD',
                'description': 'Weekly rate',
                'is_active': True
            },
            {
                'name': 'Standard Monthly',
                'rate_type': 'monthly',
                'amount': 400.00,
                'currency': 'USD',
                'description': 'Monthly subscription',
                'is_active': True
            },
            
            # Special rates
            {
                'name': 'Early Bird',
                'rate_type': 'special',
                'amount': 1.50,
                'currency': 'USD',
                'description': 'Early bird special (before 9 AM)',
                'conditions': {'start_hour': 0, 'end_hour': 9},
                'is_active': True
            },
            {
                'name': 'Evening Special',
                'rate_type': 'special',
                'amount': 1.50,
                'currency': 'USD',
                'description': 'Evening special (after 6 PM)',
                'conditions': {'start_hour': 18, 'end_hour': 24},
                'is_active': True
            },
            {
                'name': 'Weekend Rate',
                'rate_type': 'special',
                'amount': 15.00,
                'currency': 'USD',
                'description': 'All day weekend rate',
                'conditions': {'days': ['saturday', 'sunday']},
                'is_active': True
            },
            
            # EV charging rates
            {
                'name': 'EV Charging',
                'rate_type': 'special',
                'amount': 0.25,
                'currency': 'USD',
                'unit': 'kWh',
                'description': 'Electric vehicle charging rate',
                'is_active': True
            }
        ]
        
        for rate_data in rates:
            existing = session.query(Rate).filter_by(name=rate_data['name']).first()
            if not existing:
                rate = Rate(**rate_data)
                session.add(rate)
        
        logger.info(f"Loaded {len(rates)} default rates")
    
    def _load_subscription_plans(self, session: Session) -> None:
        """Load default subscription plans."""
        logger.info("Loading subscription plans...")
        
        from data.models.payment_models import SubscriptionPlan
        
        plans = [
            {
                'name': 'Basic',
                'description': 'Basic parking plan',
                'price': 29.99,
                'currency': 'USD',
                'interval': 'month',
                'features': {
                    'max_reservations': 10,
                    'discount_percentage': 5,
                    'free_cancellation': True,
                    'priority_support': False
                },
                'is_active': True
            },
            {
                'name': 'Premium',
                'description': 'Premium parking plan',
                'price': 49.99,
                'currency': 'USD',
                'interval': 'month',
                'features': {
                    'max_reservations': 30,
                    'discount_percentage': 10,
                    'free_cancellation': True,
                    'priority_support': True,
                    'guaranteed_spot': True
                },
                'is_active': True
            },
            {
                'name': 'Business',
                'description': 'Business parking plan',
                'price': 99.99,
                'currency': 'USD',
                'interval': 'month',
                'features': {
                    'max_reservations': 100,
                    'discount_percentage': 15,
                    'free_cancellation': True,
                    'priority_support': True,
                    'guaranteed_spot': True,
                    'dedicated_spots': True,
                    'analytics_access': True
                },
                'is_active': True
            },
            {
                'name': 'Annual Premium',
                'description': 'Annual premium subscription',
                'price': 499.99,
                'currency': 'USD',
                'interval': 'year',
                'features': {
                    'max_reservations': 30,
                    'discount_percentage': 15,
                    'free_cancellation': True,
                    'priority_support': True,
                    'guaranteed_spot': True,
                    'two_months_free': True
                },
                'is_active': True
            }
        ]
        
        for plan_data in plans:
            existing = session.query(SubscriptionPlan).filter_by(name=plan_data['name']).first()
            if not existing:
                plan = SubscriptionPlan(**plan_data)
                session.add(plan)
        
        logger.info(f"Loaded {len(plans)} subscription plans")
    
    def _create_admin_user(self) -> None:
        """Create default admin user."""
        logger.info("Creating admin user...")
        
        with self.Session() as session:
            user_repo = UserRepository(session)
            role_repo = RoleRepository(session)
            
            # Check if admin already exists
            existing = user_repo.get_by_email('admin@parking.com')
            if existing:
                logger.info("Admin user already exists")
                return
            
            # Get admin role
            admin_role = role_repo.get_by_name('admin')
            if not admin_role:
                logger.error("Admin role not found")
                return
            
            # Prompt for admin password
            print("\n" + "="*50)
            print("Create Admin User")
            print("="*50)
            
            email = input("Admin Email [admin@parking.com]: ").strip()
            if not email:
                email = 'admin@parking.com'
            
            username = input("Admin Username [admin]: ").strip()
            if not username:
                username = 'admin'
            
            first_name = input("First Name [Admin]: ").strip()
            if not first_name:
                first_name = 'Admin'
            
            last_name = input("Last Name [User]: ").strip()
            if not last_name:
                last_name = 'User'
            
            while True:
                password = getpass.getpass("Password: ")
                confirm = getpass.getpass("Confirm Password: ")
                
                if password == confirm:
                    break
                print("Passwords do not match. Please try again.")
            
            # Create user
            from utils.security import hash_password
            
            user = user_repo.create_user(
                email=email,
                username=username,
                password_hash=hash_password(password),
                first_name=first_name,
                last_name=last_name,
                role=admin_role.name,
                status=UserStatus.ACTIVE
            )
            
            session.commit()
            
            logger.info(f"Admin user created: {email}")
            print(f"\nAdmin user created successfully: {email}")
    
    def _load_seed_data(self) -> None:
        """Load seed data for development/testing."""
        logger.info("Loading seed data...")
        
        with self.Session() as session:
            # Create sample zones
            self._create_sample_zones(session)
            
            # Create sample spots
            self._create_sample_spots(session)
            
            # Create sample users
            self._create_sample_users(session)
            
            # Create sample vehicles
            self._create_sample_vehicles(session)
            
            # Create sample reservations
            self._create_sample_reservations(session)
            
            session.commit()
            
        logger.info("Seed data loaded")
    
    def _create_sample_zones(self, session: Session) -> None:
        """Create sample parking zones."""
        from data.models.parking_models import ParkingZone
        
        zones = [
            {
                'name': 'Main Lot A',
                'zone_type': 'surface',
                'total_spots': 100,
                'description': 'Main parking lot - Section A',
                'location': 'North Entrance',
                'is_active': True
            },
            {
                'name': 'Main Lot B',
                'zone_type': 'surface',
                'total_spots': 100,
                'description': 'Main parking lot - Section B',
                'location': 'South Entrance',
                'is_active': True
            },
            {
                'name': 'Garage Level 1',
                'zone_type': 'structure',
                'total_spots': 150,
                'description': 'Parking garage - Level 1',
                'location': 'West Building',
                'is_active': True
            },
            {
                'name': 'Garage Level 2',
                'zone_type': 'structure',
                'total_spots': 150,
                'description': 'Parking garage - Level 2',
                'location': 'West Building',
                'is_active': True
            },
            {
                'name': 'VIP Section',
                'zone_type': 'reserved',
                'total_spots': 20,
                'description': 'VIP reserved parking',
                'location': 'Near Entrance',
                'is_active': True
            },
            {
                'name': 'EV Charging Station',
                'zone_type': 'covered',
                'total_spots': 30,
                'description': 'Electric vehicle charging area',
                'location': 'East Side',
                'is_active': True
            }
        ]
        
        for zone_data in zones:
            existing = session.query(ParkingZone).filter_by(name=zone_data['name']).first()
            if not existing:
                zone = ParkingZone(**zone_data)
                session.add(zone)
        
        logger.info(f"Created {len(zones)} sample zones")
    
    def _create_sample_spots(self, session: Session) -> None:
        """Create sample parking spots."""
        from data.models.parking_models import ParkingZone, ParkingSpot
        
        zones = session.query(ParkingZone).all()
        
        spot_count = 0
        for zone in zones:
            # Create spots based on zone capacity
            for i in range(1, zone.total_spots + 1):
                # Determine spot type
                if 'VIP' in zone.name:
                    spot_type = SpotType.VIP
                elif 'EV' in zone.name:
                    spot_type = SpotType.ELECTRIC
                elif i <= 5:  # First 5 spots are handicapped
                    spot_type = SpotType.HANDICAPPED
                else:
                    spot_type = SpotType.STANDARD
                
                spot = ParkingSpot(
                    zone_id=zone.id,
                    spot_number=f"{zone.name[0]}{i:03d}",
                    spot_type=spot_type,
                    status=SpotStatus.AVAILABLE,
                    is_covered=zone.zone_type in ['structure', 'covered'],
                    has_ev_charging=spot_type == SpotType.ELECTRIC,
                    width=2.5,
                    length=5.0
                )
                session.add(spot)
                spot_count += 1
        
        logger.info(f"Created {spot_count} sample parking spots")
    
    def _create_sample_users(self, session: Session) -> None:
        """Create sample users."""
        user_repo = UserRepository(session)
        role_repo = RoleRepository(session)
        
        # Get roles
        user_role = role_repo.get_by_name('user')
        operator_role = role_repo.get_by_name('operator')
        manager_role = role_repo.get_by_name('manager')
        
        from utils.security import hash_password
        
        sample_users = [
            {
                'email': 'john.doe@example.com',
                'username': 'johndoe',
                'password': 'Password123!',
                'first_name': 'John',
                'last_name': 'Doe',
                'phone': '+1234567890',
                'role': user_role,
                'status': UserStatus.ACTIVE
            },
            {
                'email': 'jane.smith@example.com',
                'username': 'janesmith',
                'password': 'Password123!',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'phone': '+1234567891',
                'role': user_role,
                'status': UserStatus.ACTIVE
            },
            {
                'email': 'bob.wilson@example.com',
                'username': 'bobwilson',
                'password': 'Password123!',
                'first_name': 'Bob',
                'last_name': 'Wilson',
                'phone': '+1234567892',
                'role': user_role,
                'status': UserStatus.ACTIVE
            },
            {
                'email': 'alice.johnson@example.com',
                'username': 'alicej',
                'password': 'Password123!',
                'first_name': 'Alice',
                'last_name': 'Johnson',
                'phone': '+1234567893',
                'role': user_role,
                'status': UserStatus.ACTIVE
            },
            {
                'email': 'operator1@parking.com',
                'username': 'operator1',
                'password': 'Operator123!',
                'first_name': 'Mike',
                'last_name': 'Operator',
                'phone': '+1234567894',
                'role': operator_role,
                'status': UserStatus.ACTIVE
            },
            {
                'email': 'manager1@parking.com',
                'username': 'manager1',
                'password': 'Manager123!',
                'first_name': 'Sarah',
                'last_name': 'Manager',
                'phone': '+1234567895',
                'role': manager_role,
                'status': UserStatus.ACTIVE
            }
        ]
        
        for user_data in sample_users:
            existing = user_repo.get_by_email(user_data['email'])
            if not existing:
                role = user_data.pop('role')
                password = user_data.pop('password')
                
                user = user_repo.create_user(
                    **user_data,
                    password_hash=hash_password(password),
                    role=role.name
                )
                
                logger.debug(f"Created sample user: {user.email}")
        
        logger.info(f"Created {len(sample_users)} sample users")
    
    def _create_sample_vehicles(self, session: Session) -> None:
        """Create sample vehicles."""
        user_repo = UserRepository(session)
        vehicle_repo = VehicleRepository(session)
        
        users = user_repo.get_all()
        
        vehicles = [
            {
                'license_plate': 'ABC123',
                'make': 'Toyota',
                'model': 'Camry',
                'year': 2022,
                'color': 'Silver',
                'vehicle_type': VehicleType.CAR,
                'fuel_type': FuelType.GASOLINE
            },
            {
                'license_plate': 'XYZ789',
                'make': 'Honda',
                'model': 'Civic',
                'year': 2023,
                'color': 'Blue',
                'vehicle_type': VehicleType.CAR,
                'fuel_type': FuelType.GASOLINE
            },
            {
                'license_plate': 'EV1234',
                'make': 'Tesla',
                'model': 'Model 3',
                'year': 2023,
                'color': 'White',
                'vehicle_type': VehicleType.EV,
                'fuel_type': FuelType.ELECTRIC
            },
            {
                'license_plate': 'TRUCK1',
                'make': 'Ford',
                'model': 'F-150',
                'year': 2022,
                'color': 'Black',
                'vehicle_type': VehicleType.TRUCK,
                'fuel_type': FuelType.GASOLINE
            },
            {
                'license_plate': 'MOTO99',
                'make': 'Harley-Davidson',
                'model': 'Sportster',
                'year': 2021,
                'color': 'Red',
                'vehicle_type': VehicleType.MOTORCYCLE,
                'fuel_type': FuelType.GASOLINE
            }
        ]
        
        for i, user in enumerate(users[:3]):  # Assign to first 3 users
            for vehicle_data in vehicles[:2]:  # 2 vehicles per user
                existing = vehicle_repo.get_by_license_plate(vehicle_data['license_plate'])
                if not existing:
                    vehicle = vehicle_repo.create_vehicle(
                        **vehicle_data,
                        owner_id=user.id,
                        ownership_type='owner'
                    )
                    
                    logger.debug(f"Created sample vehicle: {vehicle.license_plate}")
        
        logger.info("Created sample vehicles")
    
    def _create_sample_reservations(self, session: Session) -> None:
        """Create sample reservations."""
        user_repo = UserRepository(session)
        spot_repo = ParkingSpotRepository(session)
        reservation_repo = ReservationRepository(session)
        
        users = user_repo.get_all()
        spots = spot_repo.get_available_spots(limit=10)
        
        from datetime import timedelta
        
        now = datetime.utcnow()
        
        # Past reservations
        for i, user in enumerate(users[:2]):
            for j in range(3):
                start_time = now - timedelta(days=j+1, hours=2)
                end_time = start_time + timedelta(hours=3)
                
                spot = spots[i * 3 + j % len(spots)]
                
                reservation = reservation_repo.create_reservation(
                    user_id=user.id,
                    spot_id=spot.id,
                    vehicle_id=user.vehicles[0].id if user.vehicles else None,
                    start_time=start_time,
                    end_time=end_time,
                    status=ReservationStatus.COMPLETED
                )
                
                logger.debug(f"Created past reservation: {reservation.confirmation_code}")
        
        # Current/active reservations
        for i, user in enumerate(users[2:4]):
            start_time = now - timedelta(hours=1)
            end_time = now + timedelta(hours=2)
            
            spot = spots[i + 5]
            
            reservation = reservation_repo.create_reservation(
                user_id=user.id,
                spot_id=spot.id,
                vehicle_id=user.vehicles[0].id if user.vehicles else None,
                start_time=start_time,
                end_time=end_time,
                status=ReservationStatus.CHECKED_IN
            )
            
            # Check in
            reservation_repo.check_in(reservation.id)
            
            logger.debug(f"Created active reservation: {reservation.confirmation_code}")
        
        # Future reservations
        for i, user in enumerate(users):
            start_time = now + timedelta(days=1, hours=10)
            end_time = start_time + timedelta(hours=4)
            
            spot = spots[i % len(spots)]
            
            reservation = reservation_repo.create_reservation(
                user_id=user.id,
                spot_id=spot.id,
                vehicle_id=user.vehicles[0].id if user.vehicles else None,
                start_time=start_time,
                end_time=end_time,
                status=ReservationStatus.CONFIRMED
            )
            
            logger.debug(f"Created future reservation: {reservation.confirmation_code}")
        
        logger.info("Created sample reservations")
    
    def _verify_initialization(self) -> None:
        """Verify database initialization."""
        logger.info("Verifying database initialization...")
        
        with self.Session() as session:
            # Check tables exist
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            
            expected_tables = [
                'users', 'roles', 'permissions',
                'vehicles', 'parking_zones', 'parking_spots',
                'reservations', 'payments', 'notifications',
                'audit_logs', 'system_config'
            ]
            
            missing_tables = [t for t in expected_tables if t not in tables]
            if missing_tables:
                logger.warning(f"Missing tables: {missing_tables}")
            else:
                logger.info("All expected tables present")
            
            # Check counts
            for table in expected_tables[:5]:  # Check first few tables
                count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                logger.info(f"Table {table}: {count} records")
        
        logger.info("Database verification completed")


# ============================================================================
# Main Script
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Initialize parking management database')
    parser.add_argument('--drop-existing', action='store_true', help='Drop existing tables')
    parser.add_argument('--seed-data', action='store_true', help='Load seed data')
    parser.add_argument('--create-admin', action='store_true', help='Create admin user')
    parser.add_argument('--db-url', help='Database connection URL')
    parser.add_argument('--config', help='Configuration file path')
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
    db_url = args.db_url or config.get('database.url', 'sqlite:///parking.db')
    
    # Create initializer
    initializer = DatabaseInitializer(
        db_url=db_url,
        config=config,
        drop_existing=args.drop_existing,
        seed_data=args.seed_data,
        create_admin=args.create_admin
    )
    
    # Initialize database
    success = initializer.initialize()
    
    if success:
        logger.info("Database initialization completed successfully")
        sys.exit(0)
    else:
        logger.error("Database initialization failed")
        sys.exit(1)


if __name__ == '__main__':
    main()