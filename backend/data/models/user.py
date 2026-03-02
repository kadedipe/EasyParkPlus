# parking-management/data/migrations/models/user.py

"""
User model for parking management system.

This module defines the User model and related classes for authentication,
authorization, profile management, and user preferences.
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Time,
    Text, ForeignKey, UniqueConstraint, Index, CheckConstraint,
    Numeric, JSON, Table, func, text, event
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, INET
from sqlalchemy.orm import relationship, backref, validates, object_session
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declarative_base
import uuid
import re
import hashlib
import hmac
from datetime import datetime, date, timedelta
import logging
from typing import Optional, List, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

# Create base class (will be imported from common base in production)
Base = declarative_base()

# Association table for user roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('granted_by', UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL')),
    Column('granted_at', DateTime(timezone=True), server_default=func.now()),
    Column('expires_at', DateTime(timezone=True)),
    Column('is_active', Boolean, server_default='true'),
    Index('ix_user_roles_user', 'user_id'),
    Index('ix_user_roles_role', 'role_id')
)

# Association table for user permissions (direct permissions, not via roles)
user_permissions = Table(
    'user_permissions',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    Column('granted_by', UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL')),
    Column('granted_at', DateTime(timezone=True), server_default=func.now()),
    Column('expires_at', DateTime(timezone=True)),
    Column('is_active', Boolean, server_default='true')
)


class User(Base):
    """
    User model for parking management system.
    
    Handles authentication, authorization, profile management, and user preferences.
    Supports multiple authentication methods, MFA, and comprehensive security features.
    """
    
    __tablename__ = 'users'
    __table_args__ = (
        # Indexes for performance
        Index('ix_users_email_lower', func.lower('email'), unique=True),
        Index('ix_users_username_lower', func.lower('username'), unique=True),
        Index('ix_users_phone', 'phone_number'),
        Index('ix_users_status', 'status'),
        Index('ix_users_created_month', func.date_trunc('month', 'created_at')),
        Index('ix_users_last_login', 'last_login_at'),
        Index('ix_users_active_recent', 'last_login_at', 
              postgresql_where=text("status = 'active'")),
        
        # Composite indexes for common queries
        Index('ix_users_email_status', 'email', 'status'),
        Index('ix_users_name_search', 'first_name', 'last_name'),
        
        # Check constraints
        CheckConstraint(
            "status IN ('pending', 'active', 'inactive', 'suspended', 'locked', 'deleted')",
            name='ck_users_status'
        ),
        CheckConstraint(
            "role IN ('user', 'operator', 'manager', 'admin', 'super_admin')",
            name='ck_users_role'
        ),
        CheckConstraint(
            "length(email) > 5 AND email LIKE '%@%'",
            name='ck_users_email_format'
        ),
        
        # Table comment
        {'comment': 'User accounts for parking management system'}
    )
    
    # =========================================================================
    # PRIMARY KEY
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    # =========================================================================
    # AUTHENTICATION FIELDS
    # =========================================================================
    username = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment='Unique username for login'
    )
    
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment='Email address (used for login and notifications)'
    )
    
    password_hash = Column(
        String(255),
        nullable=False,
        comment='Bcrypt hash of user password'
    )
    
    password_salt = Column(
        String(255),
        comment='Salt used for password hashing (if applicable)'
    )
    
    password_reset_token = Column(
        String(255),
        unique=True,
        comment='Token for password reset'
    )
    
    password_reset_expires = Column(
        DateTime(timezone=True),
        comment='Expiration time for password reset token'
    )
    
    password_changed_at = Column(
        DateTime(timezone=True),
        comment='Timestamp of last password change'
    )
    
    # =========================================================================
    # PROFILE INFORMATION
    # =========================================================================
    first_name = Column(
        String(100),
        comment='User\'s first name'
    )
    
    last_name = Column(
        String(100),
        comment='User\'s last name'
    )
    
    middle_name = Column(
        String(100),
        comment='User\'s middle name'
    )
    
    preferred_name = Column(
        String(100),
        comment='Preferred name/nickname'
    )
    
    phone_number = Column(
        String(20),
        index=True,
        comment='Primary phone number (E.164 format)'
    )
    
    phone_number_verified = Column(
        Boolean,
        server_default='false',
        comment='Whether phone number has been verified'
    )
    
    email_verified = Column(
        Boolean,
        server_default='false',
        comment='Whether email has been verified'
    )
    
    avatar_url = Column(
        String(500),
        comment='URL to user avatar image'
    )
    
    # =========================================================================
    # ADDRESS INFORMATION
    # =========================================================================
    address_line1 = Column(
        String(255),
        comment='Street address line 1'
    )
    
    address_line2 = Column(
        String(255),
        comment='Street address line 2 (apartment, suite, etc.)'
    )
    
    city = Column(
        String(100),
        comment='City'
    )
    
    state = Column(
        String(50),
        comment='State or province'
    )
    
    postal_code = Column(
        String(20),
        comment='Postal/ZIP code'
    )
    
    country = Column(
        String(2),
        server_default='US',
        comment='ISO 3166-1 alpha-2 country code'
    )
    
    # =========================================================================
    # STATUS AND VERIFICATION
    # =========================================================================
    status = Column(
        String(20),
        nullable=False,
        server_default='pending',
        comment='Account status: pending, active, inactive, suspended, locked, deleted'
    )
    
    is_active = Column(
        Boolean,
        nullable=False,
        server_default='true',
        comment='Whether account is active'
    )
    
    is_verified = Column(
        Boolean,
        server_default='false',
        comment='Whether user identity has been verified'
    )
    
    verified_at = Column(
        DateTime(timezone=True),
        comment='When user was verified'
    )
    
    verification_token = Column(
        String(255),
        comment='Email verification token'
    )
    
    verification_sent_at = Column(
        DateTime(timezone=True),
        comment='When verification email was sent'
    )
    
    # =========================================================================
    # SECURITY FIELDS
    # =========================================================================
    two_factor_enabled = Column(
        Boolean,
        server_default='false',
        comment='Whether 2FA is enabled'
    )
    
    two_factor_secret = Column(
        String(255),
        comment='TOTP secret for 2FA'
    )
    
    two_factor_backup_codes = Column(
        ARRAY(String(10)),
        comment='Backup codes for 2FA'
    )
    
    last_login_at = Column(
        DateTime(timezone=True),
        comment='Last successful login timestamp'
    )
    
    last_login_ip = Column(
        String(45),
        comment='IP address of last login (supports IPv6)'
    )
    
    last_login_ua = Column(
        String(500),
        comment='User agent of last login'
    )
    
    login_attempts = Column(
        Integer,
        server_default='0',
        comment='Number of consecutive failed login attempts'
    )
    
    locked_until = Column(
        DateTime(timezone=True),
        comment='Account locked until this time'
    )
    
    # =========================================================================
    # API ACCESS
    # =========================================================================
    api_key = Column(
        String(255),
        unique=True,
        comment='API key for programmatic access'
    )
    
    api_key_created_at = Column(
        DateTime(timezone=True),
        comment='When API key was created'
    )
    
    api_key_expires_at = Column(
        DateTime(timezone=True),
        comment='When API key expires'
    )
    
    api_key_last_used = Column(
        DateTime(timezone=True),
        comment='Last time API key was used'
    )
    
    # =========================================================================
    # ROLE AND PERMISSIONS
    # =========================================================================
    role = Column(
        String(50),
        server_default='user',
        comment='Primary role (legacy, use roles table for multiple roles)'
    )
    
    permissions = Column(
        ARRAY(String(100)),
        server_default='{}',
        comment='Direct permissions (not via roles)'
    )
    
    # =========================================================================
    # ORGANIZATIONAL FIELDS
    # =========================================================================
    department = Column(
        String(100),
        comment='Department within organization'
    )
    
    employee_id = Column(
        String(50),
        unique=True,
        comment='Employee ID if applicable'
    )
    
    company_id = Column(
        String(100),
        comment='Company identifier for corporate accounts'
    )
    
    cost_center = Column(
        String(100),
        comment='Cost center for billing'
    )
    
    # =========================================================================
    # PREFERENCES
    # =========================================================================
    preferences = Column(
        JSONB,
        server_default='{}',
        comment='User preferences (UI, notifications, etc.)'
    )
    
    notification_preferences = Column(
        JSONB,
        server_default='{}',
        comment='Notification channel preferences'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional flexible metadata'
    )
    
    # =========================================================================
    # AUDIT TIMESTAMPS
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when record was last updated'
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created this record'
    )
    
    updated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who last updated this record'
    )
    
    deleted_at = Column(
        DateTime(timezone=True),
        comment='Soft delete timestamp'
    )
    
    deleted_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who deleted this record'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    
    # Self-referential relationships for audit
    created_by_user = relationship(
        'User',
        foreign_keys=[created_by],
        remote_side=[id],
        comment='User who created this record'
    )
    
    updated_by_user = relationship(
        'User',
        foreign_keys=[updated_by],
        remote_side=[id],
        comment='User who last updated this record'
    )
    
    deleted_by_user = relationship(
        'User',
        foreign_keys=[deleted_by],
        remote_side=[id],
        comment='User who deleted this record'
    )
    
    # Role relationships
    roles = relationship(
        'Role',
        secondary=user_roles,
        back_populates='users',
        lazy='selectin',
        comment='Roles assigned to user'
    )
    
    direct_permissions = relationship(
        'Permission',
        secondary=user_permissions,
        back_populates='users',
        lazy='select',
        comment='Direct permissions assigned to user'
    )
    
    # Vehicle relationships
    vehicles = relationship(
        'Vehicle',
        back_populates='owner',
        foreign_keys='Vehicle.user_id',
        cascade='all, delete-orphan',
        comment='Vehicles owned by user'
    )
    
    # Reservation relationships
    reservations = relationship(
        'Reservation',
        back_populates='user',
        foreign_keys='Reservation.user_id',
        cascade='all, delete-orphan',
        comment='Reservations made by user'
    )
    
    # Payment relationships
    payments = relationship(
        'Payment',
        back_populates='user',
        foreign_keys='Payment.user_id',
        cascade='all, delete-orphan',
        comment='Payments made by user'
    )
    
    payment_methods = relationship(
        'PaymentMethod',
        back_populates='user',
        cascade='all, delete-orphan',
        comment='Saved payment methods'
    )
    
    # Subscription relationships
    subscriptions = relationship(
        'PaymentSubscription',
        back_populates='user',
        cascade='all, delete-orphan',
        comment='User subscriptions'
    )
    
    # Notification relationships
    notification_prefs = relationship(
        'NotificationPreference',
        back_populates='user',
        cascade='all, delete-orphan',
        comment='Notification preferences'
    )
    
    notification_devices = relationship(
        'NotificationDevice',
        back_populates='user',
        cascade='all, delete-orphan',
        comment='Push notification devices'
    )
    
    notifications = relationship(
        'Notification',
        back_populates='user',
        foreign_keys='Notification.user_id',
        cascade='all, delete-orphan',
        comment='Notifications sent to user'
    )
    
    # Audit relationships
    audit_logs = relationship(
        'AuditEvent',
        back_populates='user',
        foreign_keys='AuditEvent.user_id',
        cascade='all, delete-orphan',
        comment='Audit events for user'
    )
    
    audit_sessions = relationship(
        'AuditSession',
        back_populates='user',
        cascade='all, delete-orphan',
        comment='User sessions'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def full_name(self) -> Optional[str]:
        """
        Get user's full name by combining first, middle, and last name.
        
        Returns:
            Combined full name string
        """
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p) or None
    
    @hybrid_property
    def display_name(self) -> str:
        """
        Get display name (preferred name, full name, username, or email).
        
        Returns:
            Best available display name
        """
        if self.preferred_name:
            return self.preferred_name
        if self.full_name:
            return self.full_name
        if self.username:
            return self.username
        return self.email.split('@')[0]
    
    @hybrid_property
    def is_locked(self) -> bool:
        """
        Check if account is currently locked.
        
        Returns:
            True if account is locked
        """
        return self.locked_until and self.locked_until > datetime.now(self.locked_until.tzinfo)
    
    @hybrid_property
    def is_deleted(self) -> bool:
        """
        Check if account is soft-deleted.
        
        Returns:
            True if account is deleted
        """
        return self.deleted_at is not None
    
    @hybrid_property
    def requires_password_change(self) -> bool:
        """
        Check if password change is required (e.g., expired).
        
        Returns:
            True if password should be changed
        """
        if not self.password_changed_at:
            return True
        
        # Check if password is older than 90 days
        password_age = datetime.now(self.password_changed_at.tzinfo) - self.password_changed_at
        return password_age.days > 90
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @validates('email')
    def validate_email(self, key: str, email: str) -> str:
        """
        Validate email format.
        
        Args:
            key: Field name
            email: Email to validate
            
        Returns:
            Validated email (lowercase)
            
        Raises:
            ValueError: If email format is invalid
        """
        if not email:
            raise ValueError('Email cannot be empty')
        
        email = email.lower().strip()
        
        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValueError('Invalid email format')
        
        return email
    
    @validates('username')
    def validate_username(self, key: str, username: str) -> str:
        """
        Validate username format.
        
        Args:
            key: Field name
            username: Username to validate
            
        Returns:
            Validated username (lowercase)
            
        Raises:
            ValueError: If username format is invalid
        """
        if not username:
            raise ValueError('Username cannot be empty')
        
        username = username.lower().strip()
        
        # Username should be alphanumeric with underscores, 3-50 characters
        if not re.match(r'^[a-z0-9_]{3,50}$', username):
            raise ValueError('Username must be 3-50 characters and contain only letters, numbers, and underscores')
        
        return username
    
    @validates('phone_number')
    def validate_phone(self, key: str, phone: Optional[str]) -> Optional[str]:
        """
        Validate phone number format (E.164).
        
        Args:
            key: Field name
            phone: Phone number to validate
            
        Returns:
            Validated phone number
            
        Raises:
            ValueError: If phone format is invalid
        """
        if not phone:
            return phone
        
        # Remove any non-digit characters except leading +
        phone = re.sub(r'[^\d+]', '', phone)
        
        # E.164 format: + followed by 1-15 digits
        if not re.match(r'^\+[1-9]\d{1,14}$', phone):
            raise ValueError('Phone number must be in E.164 format (e.g., +1234567890)')
        
        return phone
    
    @validates('country')
    def validate_country(self, key: str, country: str) -> str:
        """
        Validate country code (ISO 3166-1 alpha-2).
        
        Args:
            key: Field name
            country: Country code to validate
            
        Returns:
            Uppercase country code
        """
        if country:
            return country.upper()
        return 'US'
    
    # =========================================================================
    # PASSWORD METHODS
    # =========================================================================
    
    def set_password(self, password: str) -> None:
        """
        Set and hash user password.
        
        Args:
            password: Plain text password
        """
        # In production, use a proper password hashing library like passlib
        # This is a simplified example
        salt = hashlib.sha256(os.urandom(60)).hexdigest()
        self.password_salt = salt
        self.password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        self.password_changed_at = datetime.now()
        self.password_reset_token = None
        self.password_reset_expires = None
        self.login_attempts = 0
    
    def verify_password(self, password: str) -> bool:
        """
        Verify password against stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches
        """
        if not self.password_hash or not self.password_salt:
            return False
        
        # Simplified verification
        hash_check = hashlib.sha256((password + self.password_salt).encode()).hexdigest()
        return hmac.compare_digest(hash_check, self.password_hash)
    
    def generate_password_reset_token(self) -> str:
        """
        Generate password reset token.
        
        Returns:
            Reset token
        """
        token = hashlib.sha256(
            f"{self.id}{self.email}{datetime.utcnow().timestamp()}".encode()
        ).hexdigest()
        
        self.password_reset_token = token
        self.password_reset_expires = datetime.now() + timedelta(hours=24)
        
        return token
    
    def clear_password_reset_token(self) -> None:
        """Clear password reset token after use."""
        self.password_reset_token = None
        self.password_reset_expires = None
    
    # =========================================================================
    # 2FA METHODS
    # =========================================================================
    
    def enable_2fa(self, secret: str) -> None:
        """
        Enable two-factor authentication.
        
        Args:
            secret: TOTP secret
        """
        self.two_factor_enabled = True
        self.two_factor_secret = secret
        
        # Generate backup codes
        import secrets
        self.two_factor_backup_codes = [
            secrets.token_hex(5) for _ in range(8)
        ]
    
    def disable_2fa(self) -> None:
        """Disable two-factor authentication."""
        self.two_factor_enabled = False
        self.two_factor_secret = None
        self.two_factor_backup_codes = None
    
    def verify_2fa_code(self, code: str) -> bool:
        """
        Verify 2FA code (TOTP or backup code).
        
        Args:
            code: Code to verify
            
        Returns:
            True if code is valid
        """
        if not self.two_factor_enabled:
            return True
        
        # Check backup codes
        if self.two_factor_backup_codes and code in self.two_factor_backup_codes:
            # Remove used backup code
            self.two_factor_backup_codes.remove(code)
            return True
        
        # In production, verify TOTP using pyotp or similar
        # import pyotp
        # totp = pyotp.TOTP(self.two_factor_secret)
        # return totp.verify(code)
        
        # Simplified example
        return False
    
    # =========================================================================
    # API KEY METHODS
    # =========================================================================
    
    def generate_api_key(self, expires_in_days: int = 365) -> str:
        """
        Generate new API key.
        
        Args:
            expires_in_days: Number of days until key expires
            
        Returns:
            New API key
        """
        import secrets
        self.api_key = secrets.token_urlsafe(32)
        self.api_key_created_at = datetime.now()
        self.api_key_expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        return self.api_key
    
    def revoke_api_key(self) -> None:
        """Revoke current API key."""
        self.api_key = None
        self.api_key_created_at = None
        self.api_key_expires_at = None
    
    def is_api_key_valid(self) -> bool:
        """
        Check if API key is valid.
        
        Returns:
            True if API key exists and not expired
        """
        if not self.api_key:
            return False
        
        if self.api_key_expires_at and self.api_key_expires_at < datetime.now():
            return False
        
        return True
    
    # =========================================================================
    # LOGIN METHODS
    # =========================================================================
    
    def record_login(self, ip_address: str, user_agent: str) -> None:
        """
        Record successful login.
        
        Args:
            ip_address: Client IP address
            user_agent: Client user agent
        """
        self.last_login_at = datetime.now()
        self.last_login_ip = ip_address
        self.last_login_ua = user_agent
        self.login_attempts = 0
        self.locked_until = None
    
    def record_failed_login(self) -> None:
        """Record failed login attempt and implement lockout."""
        self.login_attempts += 1
        
        # Lock account after 5 failed attempts
        if self.login_attempts >= 5:
            self.locked_until = datetime.now() + timedelta(minutes=30)
    
    def unlock_account(self) -> None:
        """Unlock user account."""
        self.locked_until = None
        self.login_attempts = 0
    
    # =========================================================================
    # PERMISSION METHODS
    # =========================================================================
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            permission: Permission string (e.g., 'reservations:create')
            
        Returns:
            True if user has permission
        """
        # Check direct permissions
        if permission in (self.permissions or []):
            return True
        
        # Check role-based permissions
        for role in self.roles:
            if permission in (role.permissions or []):
                return True
        
        return False
    
    def has_role(self, role_name: str) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            role_name: Name of role to check
            
        Returns:
            True if user has role
        """
        return any(role.name == role_name for role in self.roles)
    
    # =========================================================================
    # PREFERENCE METHODS
    # =========================================================================
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """
        Get user preference.
        
        Args:
            key: Preference key
            default: Default value if not found
            
        Returns:
            Preference value
        """
        return self.preferences.get(key, default)
    
    def set_preference(self, key: str, value: Any) -> None:
        """
        Set user preference.
        
        Args:
            key: Preference key
            value: Preference value
        """
        if not self.preferences:
            self.preferences = {}
        self.preferences[key] = value
    
    def get_notification_preference(self, channel: str, notification_type: str, default: bool = True) -> bool:
        """
        Get notification preference for specific channel and type.
        
        Args:
            channel: Notification channel (email, sms, push)
            notification_type: Type of notification
            default: Default value if not set
            
        Returns:
            Whether notifications are enabled
        """
        if not self.notification_preferences:
            return default
        
        channel_prefs = self.notification_preferences.get(channel, {})
        return channel_prefs.get(notification_type, default)
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert user to dictionary.
        
        Args:
            include_sensitive: Whether to include sensitive fields
            
        Returns:
            User data dictionary
        """
        data = {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'preferred_name': self.preferred_name,
            'full_name': self.full_name,
            'display_name': self.display_name,
            'phone_number': self.phone_number,
            'phone_number_verified': self.phone_number_verified,
            'email_verified': self.email_verified,
            'avatar_url': self.avatar_url,
            'address': {
                'line1': self.address_line1,
                'line2': self.address_line2,
                'city': self.city,
                'state': self.state,
                'postal_code': self.postal_code,
                'country': self.country
            } if any([self.address_line1, self.city]) else None,
            'status': self.status,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'role': self.role,
            'roles': [role.name for role in self.roles],
            'department': self.department,
            'employee_id': self.employee_id,
            'company_id': self.company_id,
            'cost_center': self.cost_center,
            'preferences': self.preferences,
            'notification_preferences': self.notification_preferences,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
        }
        
        if include_sensitive:
            data.update({
                'two_factor_enabled': self.two_factor_enabled,
                'login_attempts': self.login_attempts,
                'locked_until': self.locked_until.isoformat() if self.locked_until else None,
                'api_key_exists': bool(self.api_key),
                'api_key_created_at': self.api_key_created_at.isoformat() if self.api_key_created_at else None,
                'api_key_expires_at': self.api_key_expires_at.isoformat() if self.api_key_expires_at else None,
            })
        
        return data
    
    # =========================================================================
    # MAGIC METHODS
    # =========================================================================
    
    def __repr__(self) -> str:
        """String representation of user."""
        return f"<User(id={self.id}, username={self.username}, email={self.email}, status={self.status})>"
    
    def __str__(self) -> str:
        """User-friendly string representation."""
        return self.display_name or self.email


class Role(Base):
    """
    Role model for role-based access control.
    
    Roles group permissions and can be assigned to users.
    """
    
    __tablename__ = 'roles'
    __table_args__ = (
        Index('ix_roles_name', 'name', unique=True),
        CheckConstraint(
            "name IN ('user', 'operator', 'manager', 'admin', 'super_admin')",
            name='ck_roles_name'
        ),
        {'comment': 'Roles for RBAC'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    name = Column(
        String(50),
        nullable=False,
        unique=True,
        comment='Role name'
    )
    
    description = Column(
        String(255),
        comment='Role description'
    )
    
    permissions = Column(
        ARRAY(String(100)),
        server_default='{}',
        comment='Permissions granted by this role'
    )
    
    is_system = Column(
        Boolean,
        server_default='false',
        comment='System roles cannot be modified'
    )
    
    priority = Column(
        Integer,
        server_default='0',
        comment='Priority for permission resolution'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Relationships
    users = relationship(
        'User',
        secondary=user_roles,
        back_populates='roles'
    )
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


class Permission(Base):
    """
    Permission model for fine-grained access control.
    
    Permissions represent specific actions on resources.
    """
    
    __tablename__ = 'permissions'
    __table_args__ = (
        UniqueConstraint('resource', 'action', name='uq_permission'),
        Index('ix_permissions_resource', 'resource'),
        {'comment': 'Granular permissions'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    
    resource = Column(
        String(100),
        nullable=False,
        comment='Resource type (e.g., reservation, vehicle, payment)'
    )
    
    action = Column(
        String(50),
        nullable=False,
        comment='Action on resource (create, read, update, delete, etc.)'
    )
    
    description = Column(
        String(255),
        comment='Permission description'
    )
    
    conditions = Column(
        JSONB,
        comment='Conditions for this permission (e.g., own records only)'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    users = relationship(
        'User',
        secondary=user_permissions,
        back_populates='direct_permissions'
    )
    
    @property
    def name(self) -> str:
        """Get permission name in resource:action format."""
        return f"{self.resource}:{self.action}"
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name})>"


# =========================================================================
# EVENT LISTENERS
# =========================================================================

@event.listens_for(User, 'before_insert')
def user_before_insert(mapper, connection, target):
    """
    Generate verification token for new users and set defaults.
    """
    if not target.verification_token:
        token_string = f"{target.email}{datetime.utcnow().timestamp()}{uuid.uuid4()}"
        target.verification_token = hashlib.sha256(token_string.encode()).hexdigest()
    
    # Set default notification preferences
    if not target.notification_preferences:
        target.notification_preferences = {
            'email': {
                'reservation_confirmation': True,
                'reservation_reminder': True,
                'payment_receipt': True,
                'violation_alert': True,
                'marketing': False
            },
            'sms': {
                'reservation_reminder': True,
                'check_in': True,
                'violation_alert': True
            },
            'push': {
                'check_in': True,
                'check_out': True,
                'payment_receipt': True
            }
        }


@event.listens_for(User, 'before_update')
def user_before_update(mapper, connection, target):
    """
    Update verification status if email changes.
    """
    # Get old values
    old_values = object_session(target).get_changes(target)
    
    if 'email' in old_values:
        # Email changed, require reverification
        target.email_verified = False
        
        # Generate new verification token
        token_string = f"{target.email}{datetime.utcnow().timestamp()}{uuid.uuid4()}"
        target.verification_token = hashlib.sha256(token_string.encode()).hexdigest()
        target.verification_sent_at = None


@event.listens_for(User, 'after_insert')
def user_after_insert(mapper, connection, target):
    """
    Log user creation in audit log.
    """
    # This would typically insert into audit_logs table
    logger.info(f"User created: {target.username} ({target.email})")


@event.listens_for(User, 'after_delete')
def user_after_delete(mapper, connection, target):
    """
    Log user deletion in audit log.
    """
    logger.info(f"User deleted: {target.username} ({target.email})")


# =========================================================================
# FACTORY FUNCTIONS
# =========================================================================

def create_user(
    username: str,
    email: str,
    password: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    role: str = 'user',
    **kwargs
) -> User:
    """
    Factory function to create a new user.
    
    Args:
        username: Username
        email: Email address
        password: Plain text password
        first_name: First name
        last_name: Last name
        phone_number: Phone number
        role: Primary role
        **kwargs: Additional user attributes
        
    Returns:
        New User instance
    """
    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
        role=role,
        **kwargs
    )
    
    user.set_password(password)
    
    return user


def create_system_roles(session) -> List[Role]:
    """
    Create default system roles.
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        List of created roles
    """
    roles = [
        Role(
            name='user',
            description='Regular user with basic permissions',
            permissions=[
                'reservation:create',
                'reservation:read:own',
                'reservation:update:own',
                'reservation:cancel:own',
                'vehicle:create',
                'vehicle:read:own',
                'vehicle:update:own',
                'vehicle:delete:own',
                'payment:read:own',
            ],
            is_system=True,
            priority=0
        ),
        Role(
            name='operator',
            description='Parking operator with operational permissions',
            permissions=[
                'reservation:read',
                'reservation:update',
                'reservation:checkin',
                'reservation:checkout',
                'vehicle:read',
                'vehicle:verify',
                'payment:read',
                'payment:process',
                'violation:create',
                'violation:read',
                'violation:update',
            ],
            is_system=True,
            priority=10
        ),
        Role(
            name='manager',
            description='Parking manager with administrative permissions',
            permissions=[
                'user:read',
                'user:update',
                'reservation:*',
                'vehicle:*',
                'payment:*',
                'violation:*',
                'report:read',
                'report:generate',
                'rate:read',
                'rate:update',
                'zone:read',
                'zone:update',
            ],
            is_system=True,
            priority=20
        ),
        Role(
            name='admin',
            description='System administrator with full access',
            permissions=['*'],
            is_system=True,
            priority=100
        ),
        Role(
            name='super_admin',
            description='Super administrator with system-level access',
            permissions=['*'],
            is_system=True,
            priority=1000
        ),
    ]
    
    for role in roles:
        existing = session.query(Role).filter_by(name=role.name).first()
        if not existing:
            session.add(role)
    
    session.commit()
    return roles


# =========================================================================
# EXPORTS
# =========================================================================

__all__ = [
    'User',
    'Role',
    'Permission',
    'user_roles',
    'user_permissions',
    'create_user',
    'create_system_roles',
]