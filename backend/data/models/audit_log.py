# parking-management/data/migrations/models/audit_log.py

"""
Audit Log model for parking management system.

This module defines the AuditLog model and related classes for comprehensive
audit trail tracking, including user actions, data changes, security events,
and compliance monitoring.
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Time,
    Text, ForeignKey, UniqueConstraint, Index, CheckConstraint,
    Numeric, JSON, Table, func, text, event, and_, or_
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, INET, MACADDR
from sqlalchemy.orm import relationship, backref, validates, object_session
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declarative_base
import uuid
import enum
import hashlib
import hmac
import json
from datetime import datetime, date, timedelta
import logging
from typing import Optional, List, Dict, Any, Tuple
import ipaddress

# Configure logging
logger = logging.getLogger(__name__)

# Create base class
Base = declarative_base()


class AuditAction(str, enum.Enum):
    """Enum for audit actions."""
    # CRUD operations
    CREATE = 'CREATE'
    READ = 'READ'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    
    # Authentication
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'
    LOGIN_FAILED = 'LOGIN_FAILED'
    LOGIN_LOCKED = 'LOGIN_LOCKED'
    PASSWORD_CHANGE = 'PASSWORD_CHANGE'
    PASSWORD_RESET = 'PASSWORD_RESET'
    PASSWORD_RESET_REQUEST = 'PASSWORD_RESET_REQUEST'
    
    # Authorization
    PERMISSION_GRANTED = 'PERMISSION_GRANTED'
    PERMISSION_REVOKED = 'PERMISSION_REVOKED'
    ROLE_ASSIGNED = 'ROLE_ASSIGNED'
    ROLE_REMOVED = 'ROLE_REMOVED'
    ACCESS_DENIED = 'ACCESS_DENIED'
    
    # Data operations
    EXPORT = 'EXPORT'
    IMPORT = 'IMPORT'
    DOWNLOAD = 'DOWNLOAD'
    UPLOAD = 'UPLOAD'
    PRINT = 'PRINT'
    SHARE = 'SHARE'
    ARCHIVE = 'ARCHIVE'
    RESTORE = 'RESTORE'
    PURGE = 'PURGE'
    
    # Business operations
    APPROVE = 'APPROVE'
    REJECT = 'REJECT'
    SUBMIT = 'SUBMIT'
    CANCEL = 'CANCEL'
    VOID = 'VOID'
    REFUND = 'REFUND'
    PAYMENT = 'PAYMENT'
    
    # Verification
    VERIFY = 'VERIFY'
    VALIDATE = 'VALIDATE'
    AUDIT = 'AUDIT'
    REVIEW = 'REVIEW'
    ESCALATE = 'ESCALATE'
    DELEGATE = 'DELEGATE'
    ASSIGN = 'ASSIGN'
    UNASSIGN = 'UNASSIGN'
    
    # Security
    LOCK = 'LOCK'
    UNLOCK = 'UNLOCK'
    ENABLE = 'ENABLE'
    DISABLE = 'DISABLE'
    ACTIVATE = 'ACTIVATE'
    DEACTIVATE = 'DEACTIVATE'
    SUSPEND = 'SUSPEND'
    REINSTATE = 'REINSTATE'
    RESET = 'RESET'
    
    # Configuration
    CHANGE_SETTINGS = 'CHANGE_SETTINGS'
    CONFIGURE = 'CONFIGURE'
    INSTALL = 'INSTALL'
    UNINSTALL = 'UNINSTALL'
    UPDATE = 'UPDATE'
    UPGRADE = 'UPGRADE'
    
    # System
    BACKUP = 'BACKUP'
    RESTORE_SYSTEM = 'RESTORE_SYSTEM'
    SYNC = 'SYNC'
    MERGE = 'MERGE'
    SPLIT = 'SPLIT'
    TRANSFER = 'TRANSFER'


class AuditStatus(str, enum.Enum):
    """Enum for audit status."""
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'
    TIMEOUT = 'TIMEOUT'
    CANCELLED = 'CANCELLED'
    BLOCKED = 'BLOCKED'
    DENIED = 'DENIED'
    UNAUTHORIZED = 'UNAUTHORIZED'
    RATE_LIMITED = 'RATE_LIMITED'
    VALID = 'VALID'
    INVALID = 'INVALID'
    EXPIRED = 'EXPIRED'


class AuditSeverity(str, enum.Enum):
    """Enum for audit severity."""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    NOTICE = 'NOTICE'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'
    ALERT = 'ALERT'
    EMERGENCY = 'EMERGENCY'


class AuditCategory(str, enum.Enum):
    """Enum for audit categories."""
    AUTHENTICATION = 'AUTHENTICATION'
    AUTHORIZATION = 'AUTHORIZATION'
    DATA_ACCESS = 'DATA_ACCESS'
    DATA_MODIFICATION = 'DATA_MODIFICATION'
    CONFIGURATION = 'CONFIGURATION'
    SYSTEM = 'SYSTEM'
    SECURITY = 'SECURITY'
    COMPLIANCE = 'COMPLIANCE'
    FINANCIAL = 'FINANCIAL'
    USER_ACTIVITY = 'USER_ACTIVITY'
    ADMIN_ACTIVITY = 'ADMIN_ACTIVITY'
    API_ACTIVITY = 'API_ACTIVITY'
    INTEGRATION = 'INTEGRATION'
    WORKFLOW = 'WORKFLOW'
    REPORTING = 'REPORTING'
    EXPORT = 'EXPORT'
    IMPORT = 'IMPORT'
    MAINTENANCE = 'MAINTENANCE'


class AuditResourceType(str, enum.Enum):
    """Enum for audit resource types."""
    USER = 'USER'
    VEHICLE = 'VEHICLE'
    RESERVATION = 'RESERVATION'
    PARKING_SPOT = 'PARKING_SPOT'
    PARKING_ZONE = 'PARKING_ZONE'
    PAYMENT = 'PAYMENT'
    INVOICE = 'INVOICE'
    SUBSCRIPTION = 'SUBSCRIPTION'
    NOTIFICATION = 'NOTIFICATION'
    TEMPLATE = 'TEMPLATE'
    CAMPAIGN = 'CAMPAIGN'
    DEVICE = 'DEVICE'
    SENSOR = 'SENSOR'
    VIOLATION = 'VIOLATION'
    DISPUTE = 'DISPUTE'
    REFUND = 'REFUND'
    DISCOUNT = 'DISCOUNT'
    RATE = 'RATE'
    SETTINGS = 'SETTINGS'
    PERMISSION = 'PERMISSION'
    ROLE = 'ROLE'
    API_KEY = 'API_KEY'
    WEBHOOK = 'WEBHOOK'
    REPORT = 'REPORT'
    AUDIT_LOG = 'AUDIT_LOG'


class AuditIPLocation(str, enum.Enum):
    """Enum for IP location types."""
    INTERNAL = 'INTERNAL'
    EXTERNAL = 'EXTERNAL'
    VPN = 'VPN'
    PROXY = 'PROXY'
    TOR = 'TOR'
    CLOUD = 'CLOUD'
    UNKNOWN = 'UNKNOWN'


class ComplianceStandard(str, enum.Enum):
    """Enum for compliance standards."""
    GDPR = 'GDPR'
    CCPA = 'CCPA'
    PCI_DSS = 'PCI_DSS'
    HIPAA = 'HIPAA'
    SOX = 'SOX'
    ISO_27001 = 'ISO_27001'
    NIST = 'NIST'
    FISMA = 'FISMA'
    FERPA = 'FERPA'
    COPPA = 'COPPA'


class RetentionAction(str, enum.Enum):
    """Enum for retention actions."""
    ARCHIVE = 'ARCHIVE'
    DELETE = 'DELETE'
    ANONYMIZE = 'ANONYMIZE'
    PSEUDONYMIZE = 'PSEUDONYMIZE'
    EXPORT = 'EXPORT'


class ValidationStatus(str, enum.Enum):
    """Enum for validation status."""
    PASSED = 'PASSED'
    FAILED = 'FAILED'
    WARNING = 'WARNING'
    SKIPPED = 'SKIPPED'
    PENDING = 'PENDING'


class AnomalyType(str, enum.Enum):
    """Enum for anomaly types."""
    UNUSUAL_HOURS = 'UNUSUAL_HOURS'
    UNUSUAL_LOCATION = 'UNUSUAL_LOCATION'
    UNUSUAL_FREQUENCY = 'UNUSUAL_FREQUENCY'
    UNUSUAL_VOLUME = 'UNUSUAL_VOLUME'
    MULTIPLE_FAILURES = 'MULTIPLE_FAILURES'
    RAPID_ACTIONS = 'RAPID_ACTIONS'
    OUTSIDE_PATTERN = 'OUTSIDE_PATTERN'
    IMPOSSIBLE_TRAVEL = 'IMPOSSIBLE_TRAVEL'
    DATA_TAMPERING = 'DATA_TAMPERING'
    ACCESS_PATTERN = 'ACCESS_PATTERN'


class AnomalySeverity(str, enum.Enum):
    """Enum for anomaly severity."""
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'


class AuditSession(Base):
    """
    User session tracking for audit purposes.
    
    Tracks user login sessions, including duration, IP address, device info,
    and authentication methods.
    """
    
    __tablename__ = 'audit_sessions'
    __table_args__ = (
        Index('ix_audit_sessions_id', 'session_id', unique=True),
        Index('ix_audit_sessions_user', 'user_id'),
        Index('ix_audit_sessions_ip', 'ip_address'),
        Index('ix_audit_sessions_start', 'session_start'),
        Index('ix_audit_sessions_active', 'is_active'),
        Index('ix_audit_sessions_user_active', 'user_id', 'is_active'),
        Index('ix_audit_sessions_created_at', 'created_at'),
        
        # Check constraints
        CheckConstraint(
            "auth_method IN ('password', 'oauth', 'saml', 'api_key', 'certificate', 'biometric', 'magic_link')",
            name='ck_audit_sessions_auth_method'
        ),
        CheckConstraint(
            "ip_location_type IN ('INTERNAL', 'EXTERNAL', 'VPN', 'PROXY', 'TOR', 'CLOUD', 'UNKNOWN')",
            name='ck_audit_sessions_ip_location'
        ),
        
        # Table comment
        {'comment': 'User session tracking for audit purposes'}
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
    
    session_id = Column(
        String(255),
        nullable=False,
        unique=True,
        comment='Unique session identifier'
    )
    
    # =========================================================================
    # USER INFORMATION
    # =========================================================================
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='ID of the user'
    )
    
    username = Column(
        String(255),
        comment='Username at time of session'
    )
    
    email = Column(
        String(255),
        comment='Email at time of session'
    )
    
    # =========================================================================
    # SESSION TOKENS
    # =========================================================================
    session_token = Column(
        String(500),
        comment='Session token (hashed)'
    )
    
    refresh_token = Column(
        String(500),
        comment='Refresh token (hashed)'
    )
    
    # =========================================================================
    # IP AND LOCATION
    # =========================================================================
    ip_address = Column(
        String(45),
        nullable=False,
        comment='IP address (supports IPv6)'
    )
    
    ip_location = Column(
        JSONB,
        comment='GeoIP location data'
    )
    
    ip_location_type = Column(
        String(20),
        comment='Type of IP location'
    )
    
    # =========================================================================
    # DEVICE INFORMATION
    # =========================================================================
    user_agent = Column(
        String(500),
        comment='User agent string'
    )
    
    device_type = Column(
        String(50),
        comment='Type of device (desktop, mobile, tablet)'
    )
    
    device_fingerprint = Column(
        String(255),
        comment='Browser/device fingerprint'
    )
    
    browser = Column(
        String(100),
        comment='Browser name and version'
    )
    
    browser_language = Column(
        String(50),
        comment='Browser language'
    )
    
    os = Column(
        String(100),
        comment='Operating system'
    )
    
    screen_resolution = Column(
        String(20),
        comment='Screen resolution'
    )
    
    timezone = Column(
        String(50),
        comment='Client timezone'
    )
    
    # =========================================================================
    # SESSION TIMING
    # =========================================================================
    session_start = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='Session start time'
    )
    
    session_end = Column(
        DateTime(timezone=True),
        comment='Session end time'
    )
    
    duration_seconds = Column(
        Integer,
        comment='Session duration in seconds'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether session is currently active'
    )
    
    # =========================================================================
    # IMPERSONATION
    # =========================================================================
    is_impersonated = Column(
        Boolean,
        server_default='false',
        comment='Whether user is being impersonated'
    )
    
    impersonated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who is impersonating'
    )
    
    impersonated_by_username = Column(
        String(255),
        comment='Username of impersonator'
    )
    
    # =========================================================================
    # AUTHENTICATION
    # =========================================================================
    auth_method = Column(
        String(50),
        comment='Authentication method used'
    )
    
    auth_provider = Column(
        String(100),
        comment='Authentication provider (google, github, etc.)'
    )
    
    mfa_used = Column(
        Boolean,
        server_default='false',
        comment='Whether MFA was used'
    )
    
    mfa_method = Column(
        String(50),
        comment='MFA method used (totp, sms, email, backup_code)'
    )
    
    login_location = Column(
        String(255),
        comment='Location of login (city, country)'
    )
    
    # =========================================================================
    # LOGOUT
    # =========================================================================
    logout_reason = Column(
        String(100),
        comment='Reason for logout (user, timeout, forced, expired)'
    )
    
    forced_logout_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who forced logout'
    )
    
    # =========================================================================
    # RISK ASSESSMENT
    # =========================================================================
    risk_score = Column(
        Integer,
        comment='Risk score (0-100)'
    )
    
    risk_factors = Column(
        JSONB,
        comment='Risk factors identified'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT
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
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='audit_sessions',
        comment='User who owns the session'
    )
    
    impersonator = relationship(
        'User',
        foreign_keys=[impersonated_by],
        comment='User who is impersonating'
    )
    
    forced_logout_user = relationship(
        'User',
        foreign_keys=[forced_logout_by],
        comment='User who forced logout'
    )
    
    events = relationship(
        'AuditEvent',
        back_populates='session',
        cascade='all, delete-orphan',
        comment='Audit events in this session'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def is_long_running(self) -> bool:
        """Check if session is long-running (> 8 hours)."""
        if self.duration_seconds:
            return self.duration_seconds > 28800  # 8 hours
        return False
    
    @hybrid_property
    def location_city(self) -> Optional[str]:
        """Get city from IP location data."""
        if self.ip_location:
            return self.ip_location.get('city')
        return None
    
    @hybrid_property
    def location_country(self) -> Optional[str]:
        """Get country from IP location data."""
        if self.ip_location:
            return self.ip_location.get('country')
        return None
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @validates('ip_address')
    def validate_ip(self, key, ip):
        """Validate IP address format."""
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError(f'Invalid IP address: {ip}')
        return ip
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def end_session(self, reason: str = 'user') -> None:
        """
        End the session.
        
        Args:
            reason: Reason for ending session
        """
        self.session_end = datetime.now()
        self.is_active = False
        self.logout_reason = reason
        
        if self.session_start:
            delta = self.session_end - self.session_start
            self.duration_seconds = int(delta.total_seconds())
    
    def calculate_risk(self) -> int:
        """
        Calculate risk score for this session.
        
        Returns:
            Risk score (0-100)
        """
        score = 0
        factors = []
        
        # Check if using VPN/proxy
        if self.ip_location_type in ['VPN', 'PROXY', 'TOR']:
            score += 30
            factors.append('anonymous_ip')
        
        # Check if location is unusual for user
        if self.user and self.user.last_login_ip:
            if self.ip_address != self.user.last_login_ip:
                score += 20
                factors.append('new_ip')
        
        # Check if using new device
        if self.device_fingerprint:
            # Compare with previous sessions
            recent_sessions = object_session(self).query(AuditSession).filter(
                AuditSession.user_id == self.user_id,
                AuditSession.device_fingerprint != self.device_fingerprint,
                AuditSession.session_start > datetime.now() - timedelta(days=30)
            ).count()
            
            if recent_sessions == 0:
                score += 15
                factors.append('new_device')
        
        # Check if unusual hours
        hour = self.session_start.hour
        if hour < 6 or hour > 22:
            score += 10
            factors.append('unusual_hours')
        
        self.risk_score = min(score, 100)
        self.risk_factors = factors
        
        return self.risk_score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            'id': str(self.id),
            'session_id': self.session_id,
            'user_id': str(self.user_id) if self.user_id else None,
            'username': self.username,
            'email': self.email,
            'ip_address': self.ip_address,
            'location': {
                'city': self.location_city,
                'country': self.location_country,
                'type': self.ip_location_type,
            },
            'device': {
                'type': self.device_type,
                'browser': self.browser,
                'os': self.os,
                'screen_resolution': self.screen_resolution,
            },
            'timing': {
                'start': self.session_start.isoformat() if self.session_start else None,
                'end': self.session_end.isoformat() if self.session_end else None,
                'duration_seconds': self.duration_seconds,
                'is_active': self.is_active,
            },
            'authentication': {
                'method': self.auth_method,
                'provider': self.auth_provider,
                'mfa_used': self.mfa_used,
            },
            'impersonated': self.is_impersonated,
            'risk_score': self.risk_score,
            'risk_factors': self.risk_factors,
            'logout_reason': self.logout_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<AuditSession(id={self.session_id}, user={self.username}, start={self.session_start})>"


class AuditEvent(Base):
    """
    Main audit events table tracking all system actions.
    
    Provides comprehensive audit trail for all system activities,
    including user actions, API calls, data changes, and security events.
    """
    
    __tablename__ = 'audit_events'
    __table_args__ = (
        # Primary indexes
        Index('ix_audit_events_id', 'event_id', unique=True),
        Index('ix_audit_events_correlation', 'correlation_id'),
        
        # Foreign key indexes
        Index('ix_audit_events_user_id', 'user_id'),
        Index('ix_audit_events_session_id', 'session_id'),
        
        # Action indexes
        Index('ix_audit_events_action', 'action'),
        Index('ix_audit_events_category', 'category'),
        Index('ix_audit_events_status', 'status'),
        Index('ix_audit_events_severity', 'severity'),
        
        # Resource indexes
        Index('ix_audit_events_resource_type', 'resource_type'),
        Index('ix_audit_events_resource_id', 'resource_id'),
        Index('ix_audit_events_resource_parent', 'resource_parent_type', 'resource_parent_id'),
        
        # IP indexes
        Index('ix_audit_events_ip_address', 'ip_address'),
        
        # Time-based indexes
        Index('ix_audit_events_created_at', 'created_at'),
        
        # Composite indexes for common queries
        Index('ix_audit_events_composite_search', 'created_at', 'category', 'action', 'user_id'),
        Index('ix_audit_events_resource_search', 'resource_type', 'resource_id', 'created_at'),
        Index('ix_audit_events_ip_search', 'ip_address', 'created_at'),
        
        # Partial indexes
        Index('ix_audit_events_security', 'severity', 'status', 'created_at',
              postgresql_where=text("severity IN ('ERROR', 'CRITICAL', 'ALERT')")),
        Index('ix_audit_events_failed', 'status', 'created_at',
              postgresql_where=text("status IN ('FAILURE', 'ERROR', 'DENIED', 'UNAUTHORIZED')")),
        
        # GIN indexes for JSONB
        Index('ix_audit_events_changes_gin', 'changes', postgresql_using='gin'),
        Index('ix_audit_events_metadata_gin', 'metadata', postgresql_using='gin'),
        Index('ix_audit_events_request_gin', 'request_params', 'request_body', postgresql_using='gin'),
        
        # Check constraints
        CheckConstraint(
            "action IN ('CREATE', 'READ', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'LOGIN_FAILED', "
            "'PASSWORD_CHANGE', 'PASSWORD_RESET', 'PERMISSION_GRANTED', 'PERMISSION_REVOKED', "
            "'ROLE_ASSIGNED', 'ROLE_REMOVED', 'ACCESS_DENIED', 'EXPORT', 'IMPORT', 'DOWNLOAD', "
            "'UPLOAD', 'PRINT', 'SHARE', 'ARCHIVE', 'RESTORE', 'PURGE', 'APPROVE', 'REJECT', "
            "'SUBMIT', 'CANCEL', 'VOID', 'REFUND', 'PAYMENT', 'VERIFY', 'VALIDATE', 'AUDIT', "
            "'REVIEW', 'ESCALATE', 'DELEGATE', 'ASSIGN', 'UNASSIGN', 'LOCK', 'UNLOCK', 'ENABLE', "
            "'DISABLE', 'ACTIVATE', 'DEACTIVATE', 'SUSPEND', 'REINSTATE', 'RESET', 'CHANGE_SETTINGS', "
            "'CONFIGURE', 'INSTALL', 'UNINSTALL', 'UPDATE', 'UPGRADE', 'BACKUP', 'RESTORE_SYSTEM', "
            "'SYNC', 'MERGE', 'SPLIT', 'TRANSFER')",
            name='ck_audit_events_action'
        ),
        CheckConstraint(
            "category IN ('AUTHENTICATION', 'AUTHORIZATION', 'DATA_ACCESS', 'DATA_MODIFICATION', "
            "'CONFIGURATION', 'SYSTEM', 'SECURITY', 'COMPLIANCE', 'FINANCIAL', 'USER_ACTIVITY', "
            "'ADMIN_ACTIVITY', 'API_ACTIVITY', 'INTEGRATION', 'WORKFLOW', 'REPORTING', 'EXPORT', "
            "'IMPORT', 'MAINTENANCE')",
            name='ck_audit_events_category'
        ),
        CheckConstraint(
            "status IN ('SUCCESS', 'FAILURE', 'PENDING', 'PROCESSING', 'COMPLETED', 'ERROR', "
            "'TIMEOUT', 'CANCELLED', 'BLOCKED', 'DENIED', 'UNAUTHORIZED', 'RATE_LIMITED', "
            "'VALID', 'INVALID', 'EXPIRED')",
            name='ck_audit_events_status'
        ),
        CheckConstraint(
            "severity IN ('DEBUG', 'INFO', 'NOTICE', 'WARNING', 'ERROR', 'CRITICAL', 'ALERT', 'EMERGENCY')",
            name='ck_audit_events_severity'
        ),
        
        # Table comment
        {'comment': 'Main audit events table tracking all system actions'}
    )
    
    # =========================================================================
    # PRIMARY KEY AND IDENTIFIERS
    # =========================================================================
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    event_id = Column(
        String(100),
        nullable=False,
        unique=True,
        comment='Unique event identifier'
    )
    
    correlation_id = Column(
        String(100),
        comment='ID for correlating related events'
    )
    
    parent_event_id = Column(
        String(100),
        comment='Parent event ID for nested operations'
    )
    
    # =========================================================================
    # ACTOR INFORMATION
    # =========================================================================
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='ID of the user who performed the action'
    )
    
    username = Column(
        String(255),
        comment='Username at time of action'
    )
    
    email = Column(
        String(255),
        comment='Email at time of action'
    )
    
    role = Column(
        String(100),
        comment='User role at time of action'
    )
    
    permissions = Column(
        ARRAY(String(100)),
        comment='Permissions at time of action'
    )
    
    session_id = Column(
        String(255),
        ForeignKey('audit_sessions.session_id', ondelete='SET NULL'),
        comment='Session ID'
    )
    
    # =========================================================================
    # IMPERSONATION
    # =========================================================================
    impersonated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who is impersonating'
    )
    
    impersonated_by_username = Column(
        String(255),
        comment='Username of impersonator'
    )
    
    # =========================================================================
    # ACTION DETAILS
    # =========================================================================
    action = Column(
        String(50),
        nullable=False,
        comment='Action performed'
    )
    
    category = Column(
        String(50),
        nullable=False,
        comment='Category of action'
    )
    
    status = Column(
        String(20),
        nullable=False,
        comment='Status of action'
    )
    
    severity = Column(
        String(20),
        nullable=False,
        server_default='INFO',
        comment='Severity level'
    )
    
    # =========================================================================
    # RESOURCE DETAILS
    # =========================================================================
    resource_type = Column(
        String(50),
        nullable=False,
        comment='Type of resource affected'
    )
    
    resource_id = Column(
        String(255),
        comment='ID of the resource'
    )
    
    resource_name = Column(
        String(255),
        comment='Name/identifier of the resource'
    )
    
    resource_parent_type = Column(
        String(50),
        comment='Type of parent resource'
    )
    
    resource_parent_id = Column(
        String(255),
        comment='ID of parent resource'
    )
    
    resource_version = Column(
        Integer,
        comment='Version of resource (if applicable)'
    )
    
    # =========================================================================
    # REQUEST DETAILS
    # =========================================================================
    request_id = Column(
        String(100),
        comment='Request ID for tracing'
    )
    
    request_method = Column(
        String(10),
        comment='HTTP method (GET, POST, etc.)'
    )
    
    request_url = Column(
        String(1000),
        comment='Full request URL'
    )
    
    request_path = Column(
        String(500),
        comment='Request path'
    )
    
    request_headers = Column(
        JSONB,
        comment='Request headers (sanitized)'
    )
    
    request_params = Column(
        JSONB,
        comment='Request parameters'
    )
    
    request_body = Column(
        JSONB,
        comment='Request body (sanitized)'
    )
    
    request_size = Column(
        Integer,
        comment='Request size in bytes'
    )
    
    # =========================================================================
    # RESPONSE DETAILS
    # =========================================================================
    response_status = Column(
        Integer,
        comment='HTTP response status'
    )
    
    response_headers = Column(
        JSONB,
        comment='Response headers'
    )
    
    response_body = Column(
        JSONB,
        comment='Response body (sanitized)'
    )
    
    response_size = Column(
        Integer,
        comment='Response size in bytes'
    )
    
    response_time_ms = Column(
        Integer,
        comment='Response time in milliseconds'
    )
    
    # =========================================================================
    # IP AND LOCATION
    # =========================================================================
    ip_address = Column(
        String(45),
        nullable=False,
        comment='IP address'
    )
    
    ip_location = Column(
        JSONB,
        comment='GeoIP location data'
    )
    
    ip_location_type = Column(
        String(20),
        comment='Type of IP location'
    )
    
    user_agent = Column(
        String(500),
        comment='User agent'
    )
    
    device_fingerprint = Column(
        String(255),
        comment='Device fingerprint'
    )
    
    # =========================================================================
    # CHANGES
    # =========================================================================
    changes = Column(
        JSONB,
        comment='Summary of changes made'
    )
    
    change_count = Column(
        Integer,
        server_default='0',
        comment='Number of changes'
    )
    
    before_state = Column(
        JSONB,
        comment='State before change'
    )
    
    after_state = Column(
        JSONB,
        comment='State after change'
    )
    
    diff = Column(
        JSONB,
        comment='Difference between before and after'
    )
    
    # =========================================================================
    # COMPLIANCE
    # =========================================================================
    compliance_tags = Column(
        ARRAY(String(50)),
        comment='Compliance standards applicable'
    )
    
    retention_days = Column(
        Integer,
        comment='Retention period in days'
    )
    
    sensitive_data = Column(
        Boolean,
        server_default='false',
        comment='Whether event contains sensitive data'
    )
    
    pii_present = Column(
        Boolean,
        server_default='false',
        comment='Whether PII is present'
    )
    
    encrypted = Column(
        Boolean,
        server_default='false',
        comment='Whether data is encrypted'
    )
    
    # =========================================================================
    # METADATA
    # =========================================================================
    tags = Column(
        ARRAY(String(100)),
        comment='Custom tags'
    )
    
    metadata = Column(
        JSONB,
        server_default='{}',
        comment='Additional metadata'
    )
    
    # =========================================================================
    # AUDIT (self-referential)
    # =========================================================================
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when event occurred'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='audit_logs',
        comment='User who performed the action'
    )
    
    impersonator_user = relationship(
        'User',
        foreign_keys=[impersonated_by],
        comment='User who was impersonating'
    )
    
    session = relationship(
        'AuditSession',
        back_populates='events',
        comment='Session in which event occurred'
    )
    
    changes_detail = relationship(
        'AuditChange',
        back_populates='event',
        cascade='all, delete-orphan',
        comment='Detailed field-level changes'
    )
    
    # =========================================================================
    # HYBRID PROPERTIES
    # =========================================================================
    
    @hybrid_property
    def is_success(self) -> bool:
        """Check if action was successful."""
        return self.status == 'SUCCESS'
    
    @hybrid_property
    def is_failure(self) -> bool:
        """Check if action failed."""
        return self.status in ['FAILURE', 'ERROR']
    
    @hybrid_property
    def is_security_event(self) -> bool:
        """Check if this is a security-related event."""
        return self.category in ['SECURITY', 'AUTHENTICATION', 'AUTHORIZATION']
    
    @hybrid_property
    def resource_path(self) -> str:
        """Get full resource path."""
        parts = []
        if self.resource_parent_type:
            parts.append(f"{self.resource_parent_type}/{self.resource_parent_id}")
        parts.append(f"{self.resource_type}/{self.resource_id or ''}")
        return '/'.join(parts)
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @validates('ip_address')
    def validate_ip(self, key, ip):
        """Validate IP address format."""
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError(f'Invalid IP address: {ip}')
        return ip
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def add_change(
        self,
        field: str,
        old_value: Any,
        new_value: Any,
        table: Optional[str] = None,
        record_id: Optional[str] = None
    ) -> 'AuditChange':
        """
        Add a field-level change to this event.
        
        Args:
            field: Name of field that changed
            old_value: Previous value
            new_value: New value
            table: Table name (if different from resource_type)
            record_id: Record ID (if different from resource_id)
            
        Returns:
            Created AuditChange instance
        """
        from models.audit_log import AuditChange
        
        change = AuditChange(
            event_id=self.event_id,
            table_name=table or self.resource_type,
            record_id=record_id or self.resource_id,
            field_name=field,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            data_type=type(old_value).__name__ if old_value is not None else type(new_value).__name__
        )
        
        object_session(self).add(change)
        
        # Update change count
        self.change_count += 1
        
        # Update changes summary
        if not self.changes:
            self.changes = {}
        self.changes[field] = {
            'old': old_value,
            'new': new_value
        }
        
        return change
    
    def add_changes_bulk(self, changes: Dict[str, Tuple[Any, Any]]) -> List['AuditChange']:
        """
        Add multiple field-level changes.
        
        Args:
            changes: Dictionary mapping field names to (old_value, new_value) tuples
            
        Returns:
            List of created AuditChange instances
        """
        created = []
        for field, (old, new) in changes.items():
            if old != new:
                created.append(self.add_change(field, old, new))
        return created
    
    def set_before_state(self, state: Dict[str, Any]) -> None:
        """Set the before state for this event."""
        self.before_state = state
    
    def set_after_state(self, state: Dict[str, Any]) -> None:
        """Set the after state for this event."""
        self.after_state = state
    
    def compute_diff(self) -> Dict[str, Any]:
        """
        Compute difference between before and after states.
        
        Returns:
            Dictionary of changes
        """
        if not self.before_state or not self.after_state:
            return {}
        
        diff = {}
        all_keys = set(self.before_state.keys()) | set(self.after_state.keys())
        
        for key in all_keys:
            before = self.before_state.get(key)
            after = self.after_state.get(key)
            if before != after:
                diff[key] = {
                    'old': before,
                    'new': after
                }
        
        self.diff = diff
        self.change_count = len(diff)
        
        return diff
    
    def mask_sensitive_data(self, sensitive_fields: List[str]) -> None:
        """
        Mask sensitive data in the event.
        
        Args:
            sensitive_fields: List of field names to mask
        """
        if self.request_body:
            for field in sensitive_fields:
                if field in self.request_body:
                    self.request_body[field] = '***MASKED***'
        
        if self.response_body:
            for field in sensitive_fields:
                if field in self.response_body:
                    self.response_body[field] = '***MASKED***'
        
        if self.before_state:
            for field in sensitive_fields:
                if field in self.before_state:
                    self.before_state[field] = '***MASKED***'
        
        if self.after_state:
            for field in sensitive_fields:
                if field in self.after_state:
                    self.after_state[field] = '***MASKED***'
    
    def add_compliance_tag(self, standard: str) -> None:
        """Add a compliance tag to this event."""
        if not self.compliance_tags:
            self.compliance_tags = []
        if standard not in self.compliance_tags:
            self.compliance_tags.append(standard)
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert event to dictionary."""
        data = {
            'id': str(self.id),
            'event_id': self.event_id,
            'correlation_id': self.correlation_id,
            'actor': {
                'user_id': str(self.user_id) if self.user_id else None,
                'username': self.username,
                'email': self.email,
                'role': self.role,
                'session_id': self.session_id,
            },
            'action': {
                'name': self.action,
                'category': self.category,
                'status': self.status,
                'severity': self.severity,
            },
            'resource': {
                'type': self.resource_type,
                'id': self.resource_id,
                'name': self.resource_name,
                'parent_type': self.resource_parent_type,
                'parent_id': self.resource_parent_id,
                'path': self.resource_path,
            },
            'request': {
                'id': self.request_id,
                'method': self.request_method,
                'url': self.request_url,
                'path': self.request_path,
                'response_time_ms': self.response_time_ms,
                'response_status': self.response_status,
            },
            'client': {
                'ip_address': self.ip_address,
                'location': self.ip_location,
                'location_type': self.ip_location_type,
                'user_agent': self.user_agent,
            },
            'changes': {
                'count': self.change_count,
                'summary': self.changes,
            },
            'compliance': {
                'tags': self.compliance_tags,
                'sensitive_data': self.sensitive_data,
                'pii_present': self.pii_present,
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_sensitive:
            data.update({
                'request_params': self.request_params,
                'request_body': self.request_body,
                'response_body': self.response_body,
                'before_state': self.before_state,
                'after_state': self.after_state,
                'diff': self.diff,
                'metadata': self.metadata,
                'tags': self.tags,
            })
        
        return data
    
    def __repr__(self) -> str:
        return f"<AuditEvent(id={self.event_id}, action={self.action}, user={self.username})>"


class AuditChange(Base):
    """
    Detailed field-level changes for audit.
    
    Provides granular tracking of individual field changes within an audit event.
    """
    
    __tablename__ = 'audit_changes'
    __table_args__ = (
        Index('ix_audit_changes_event', 'event_id'),
        Index('ix_audit_changes_record', 'table_name', 'record_id'),
        Index('ix_audit_changes_field', 'field_name'),
        Index('ix_audit_changes_created', 'created_at'),
        
        # Table comment
        {'comment': 'Detailed field-level changes for audit'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    event_id = Column(
        String(100),
        ForeignKey('audit_events.event_id', ondelete='CASCADE'),
        nullable=False,
        comment='ID of the parent event'
    )
    
    table_name = Column(
        String(255),
        nullable=False,
        comment='Name of the table that changed'
    )
    
    record_id = Column(
        String(255),
        nullable=False,
        comment='ID of the record that changed'
    )
    
    field_name = Column(
        String(255),
        nullable=False,
        comment='Name of the field that changed'
    )
    
    old_value = Column(
        Text,
        comment='Previous value'
    )
    
    new_value = Column(
        Text,
        comment='New value'
    )
    
    data_type = Column(
        String(50),
        comment='Data type of the field'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when change occurred'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    event = relationship('AuditEvent', back_populates='changes_detail')
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert change to dictionary."""
        return {
            'id': str(self.id),
            'event_id': self.event_id,
            'table': self.table_name,
            'record_id': self.record_id,
            'field': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'data_type': self.data_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<AuditChange(id={self.id}, field={self.field_name})>"


class AuditAlert(Base):
    """
    Alerts generated from audit events.
    
    Triggers alerts based on suspicious patterns or critical events.
    """
    
    __tablename__ = 'audit_alerts'
    __table_args__ = (
        Index('ix_audit_alerts_rule', 'rule_id'),
        Index('ix_audit_alerts_severity', 'severity'),
        Index('ix_audit_alerts_status', 'status'),
        Index('ix_audit_alerts_created', 'created_at'),
        Index('ix_audit_alerts_resolved', 'resolved_at'),
        
        # Table comment
        {'comment': 'Alerts from audit events'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    rule_id = Column(
        String(100),
        comment='ID of the rule that triggered this alert'
    )
    
    rule_name = Column(
        String(255),
        comment='Name of the rule'
    )
    
    severity = Column(
        String(20),
        nullable=False,
        comment='Alert severity'
    )
    
    title = Column(
        String(255),
        nullable=False,
        comment='Alert title'
    )
    
    description = Column(
        Text,
        comment='Alert description'
    )
    
    event_ids = Column(
        ARRAY(String(100)),
        comment='IDs of related audit events'
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User associated with alert'
    )
    
    ip_address = Column(
        String(45),
        comment='IP address associated with alert'
    )
    
    status = Column(
        String(20),
        server_default='active',
        comment='Alert status (active, acknowledged, resolved, false_positive)'
    )
    
    acknowledged_at = Column(
        DateTime(timezone=True),
        comment='When alert was acknowledged'
    )
    
    acknowledged_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who acknowledged alert'
    )
    
    resolved_at = Column(
        DateTime(timezone=True),
        comment='When alert was resolved'
    )
    
    resolved_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who resolved alert'
    )
    
    resolution_notes = Column(
        Text,
        comment='Notes on resolution'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when alert was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when alert was last updated'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship('User', foreign_keys=[user_id])
    acknowledged_user = relationship('User', foreign_keys=[acknowledged_by])
    resolved_user = relationship('User', foreign_keys=[resolved_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def acknowledge(self, user_id: uuid.UUID) -> None:
        """Acknowledge alert."""
        self.status = 'acknowledged'
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = user_id
    
    def resolve(self, user_id: uuid.UUID, notes: Optional[str] = None) -> None:
        """Resolve alert."""
        self.status = 'resolved'
        self.resolved_at = datetime.now()
        self.resolved_by = user_id
        self.resolution_notes = notes
    
    def mark_false_positive(self, user_id: uuid.UUID, reason: str) -> None:
        """Mark alert as false positive."""
        self.status = 'false_positive'
        self.resolved_at = datetime.now()
        self.resolved_by = user_id
        self.resolution_notes = f"False positive: {reason}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'id': str(self.id),
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'severity': self.severity,
            'title': self.title,
            'description': self.description,
            'event_ids': self.event_ids,
            'user_id': str(self.user_id) if self.user_id else None,
            'ip_address': self.ip_address,
            'status': self.status,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_notes': self.resolution_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<AuditAlert(id={self.id}, severity={self.severity}, status={self.status})>"


class AuditRule(Base):
    """
    Rules for generating alerts from audit events.
    
    Defines conditions and actions for audit alerting.
    """
    
    __tablename__ = 'audit_rules'
    __table_args__ = (
        Index('ix_audit_rules_name', 'name', unique=True),
        Index('ix_audit_rules_severity', 'severity'),
        Index('ix_audit_rules_active', 'is_active'),
        
        # Table comment
        {'comment': 'Rules for audit alerting'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    name = Column(
        String(255),
        nullable=False,
        unique=True,
        comment='Rule name'
    )
    
    description = Column(
        Text,
        comment='Rule description'
    )
    
    severity = Column(
        String(20),
        nullable=False,
        comment='Alert severity when triggered'
    )
    
    conditions = Column(
        JSONB,
        nullable=False,
        comment='Conditions to evaluate'
    )
    
    time_window_seconds = Column(
        Integer,
        comment='Time window for aggregation (seconds)'
    )
    
    threshold = Column(
        Integer,
        comment='Threshold count for triggering'
    )
    
    actions = Column(
        JSONB,
        comment='Actions to take when triggered'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether rule is active'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when rule was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when rule was last updated'
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created rule'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    creator = relationship('User', foreign_keys=[created_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def evaluate(self, event: AuditEvent) -> bool:
        """
        Evaluate rule against an audit event.
        
        Args:
            event: Audit event to evaluate
            
        Returns:
            True if rule conditions are met
        """
        # This is a simplified evaluation - in production, use a rule engine
        conditions = self.conditions or {}
        
        for key, value in conditions.items():
            if key == 'action':
                if event.action != value:
                    return False
            elif key == 'category':
                if event.category != value:
                    return False
            elif key == 'severity':
                if event.severity != value:
                    return False
            elif key == 'status':
                if event.status != value:
                    return False
            elif key == 'resource_type':
                if event.resource_type != value:
                    return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            'id': str(self.id),
            'name': self.name,
            'description': self.description,
            'severity': self.severity,
            'conditions': self.conditions,
            'time_window_seconds': self.time_window_seconds,
            'threshold': self.threshold,
            'actions': self.actions,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<AuditRule(id={self.id}, name={self.name})>"


class AuditRetention(Base):
    """
    Data retention policies for audit logs.
    
    Defines how long different types of audit data should be retained
    and what actions to take when they expire.
    """
    
    __tablename__ = 'audit_retention'
    __table_args__ = (
        Index('ix_audit_retention_category', 'category'),
        Index('ix_audit_retention_action', 'action'),
        
        # Table comment
        {'comment': 'Data retention policies for audit logs'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    category = Column(
        String(50),
        nullable=False,
        comment='Audit category'
    )
    
    severity = Column(
        String(20),
        comment='Severity level (if applicable)'
    )
    
    retention_days = Column(
        Integer,
        nullable=False,
        comment='Number of days to retain'
    )
    
    action = Column(
        String(20),
        nullable=False,
        comment='Action to take when expired'
    )
    
    archive_location = Column(
        String(500),
        comment='Location for archived data'
    )
    
    is_active = Column(
        Boolean,
        server_default='true',
        comment='Whether policy is active'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when policy was created'
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment='Timestamp when policy was last updated'
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who created policy'
    )
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    creator = relationship('User', foreign_keys=[created_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def should_archive(self, event_date: datetime) -> bool:
        """Check if an event should be archived based on this policy."""
        age = datetime.now(event_date.tzinfo) - event_date
        return age.days >= self.retention_days
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary."""
        return {
            'id': str(self.id),
            'category': self.category,
            'severity': self.severity,
            'retention_days': self.retention_days,
            'action': self.action,
            'archive_location': self.archive_location,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<AuditRetention(id={self.id}, category={self.category})>"


class AuditAnomaly(Base):
    """
    Detected anomalies in audit data.
    
    Identifies unusual patterns or behaviors from audit analysis.
    """
    
    __tablename__ = 'audit_anomalies'
    __table_args__ = (
        Index('ix_audit_anomalies_type', 'anomaly_type'),
        Index('ix_audit_anomalies_severity', 'severity'),
        Index('ix_audit_anomalies_detected', 'detected_at'),
        Index('ix_audit_anomalies_resolved', 'resolved_at'),
        
        # Table comment
        {'comment': 'Detected anomalies in audit data'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    anomaly_type = Column(
        String(50),
        nullable=False,
        comment='Type of anomaly'
    )
    
    severity = Column(
        String(20),
        nullable=False,
        comment='Anomaly severity'
    )
    
    title = Column(
        String(255),
        nullable=False,
        comment='Anomaly title'
    )
    
    description = Column(
        Text,
        comment='Detailed description'
    )
    
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User associated with anomaly'
    )
    
    ip_address = Column(
        String(45),
        comment='IP address associated with anomaly'
    )
    
    event_ids = Column(
        ARRAY(String(100)),
        comment='Related audit event IDs'
    )
    
    baseline = Column(
        JSONB,
        comment='Baseline data for comparison'
    )
    
    actual = Column(
        JSONB,
        comment='Actual observed data'
    )
    
    score = Column(
        Float,
        comment='Anomaly score'
    )
    
    status = Column(
        String(20),
        server_default='detected',
        comment='Status (detected, investigating, resolved, false_positive)'
    )
    
    detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When anomaly was detected'
    )
    
    investigated_at = Column(
        DateTime(timezone=True),
        comment='When investigation started'
    )
    
    investigated_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User investigating'
    )
    
    resolved_at = Column(
        DateTime(timezone=True),
        comment='When anomaly was resolved'
    )
    
    resolved_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='SET NULL'),
        comment='User who resolved'
    )
    
    resolution_notes = Column(
        Text,
        comment='Notes on resolution'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
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
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    user = relationship('User', foreign_keys=[user_id])
    investigator = relationship('User', foreign_keys=[investigated_by])
    resolver = relationship('User', foreign_keys=[resolved_by])
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def investigate(self, user_id: uuid.UUID) -> None:
        """Start investigating anomaly."""
        self.status = 'investigating'
        self.investigated_at = datetime.now()
        self.investigated_by = user_id
    
    def resolve(self, user_id: uuid.UUID, notes: Optional[str] = None) -> None:
        """Resolve anomaly."""
        self.status = 'resolved'
        self.resolved_at = datetime.now()
        self.resolved_by = user_id
        self.resolution_notes = notes
    
    def mark_false_positive(self, user_id: uuid.UUID, reason: str) -> None:
        """Mark anomaly as false positive."""
        self.status = 'false_positive'
        self.resolved_at = datetime.now()
        self.resolved_by = user_id
        self.resolution_notes = f"False positive: {reason}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert anomaly to dictionary."""
        return {
            'id': str(self.id),
            'anomaly_type': self.anomaly_type,
            'severity': self.severity,
            'title': self.title,
            'description': self.description,
            'user_id': str(self.user_id) if self.user_id else None,
            'ip_address': self.ip_address,
            'event_ids': self.event_ids,
            'score': self.score,
            'status': self.status,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'investigated_at': self.investigated_at.isoformat() if self.investigated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_notes': self.resolution_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<AuditAnomaly(id={self.id}, type={self.anomaly_type}, severity={self.severity})>"


class AuditArchive(Base):
    """
    Archived audit records.
    
    Stores audit records that have been moved to long-term storage.
    """
    
    __tablename__ = 'audit_archive'
    __table_args__ = (
        Index('ix_audit_archive_date', 'archive_date'),
        Index('ix_audit_archive_source', 'source_table'),
        Index('ix_audit_archive_original_id', 'original_id'),
        
        # Table comment
        {'comment': 'Archived audit records'}
    )
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment='Primary key, auto-generated UUID'
    )
    
    original_id = Column(
        String(100),
        comment='Original record ID'
    )
    
    source_table = Column(
        String(100),
        nullable=False,
        comment='Source table name'
    )
    
    archive_date = Column(
        DateTime(timezone=True),
        nullable=False,
        comment='When record was archived'
    )
    
    data = Column(
        JSONB,
        nullable=False,
        comment='Archived data'
    )
    
    retention_policy_id = Column(
        UUID(as_uuid=True),
        comment='ID of retention policy used'
    )
    
    archive_location = Column(
        String(500),
        comment='Physical archive location'
    )
    
    file_name = Column(
        String(500),
        comment='Archive file name'
    )
    
    file_size = Column(
        Integer,
        comment='File size in bytes'
    )
    
    checksum = Column(
        String(64),
        comment='Data checksum for verification'
    )
    
    encrypted = Column(
        Boolean,
        server_default='false',
        comment='Whether data is encrypted'
    )
    
    compression = Column(
        String(20),
        comment='Compression method used'
    )
    
    metadata = Column(
        JSONB,
        comment='Additional metadata'
    )
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment='Timestamp when record was created'
    )
    
    # =========================================================================
    # METHODS
    # =========================================================================
    
    def verify_checksum(self) -> bool:
        """Verify data integrity using checksum."""
        if not self.checksum:
            return True
        
        import hashlib
        data_str = json.dumps(self.data, sort_keys=True)
        calculated = hashlib.sha256(data_str.encode()).hexdigest()
        return calculated == self.checksum
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert archive record to dictionary."""
        return {
            'id': str(self.id),
            'original_id': self.original_id,
            'source_table': self.source_table,
            'archive_date': self.archive_date.isoformat() if self.archive_date else None,
            'archive_location': self.archive_location,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'encrypted': self.encrypted,
            'compression': self.compression,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f"<AuditArchive(id={self.id}, source={self.source_table}, date={self.archive_date})>"


# =========================================================================
# EVENT LISTENERS
# =========================================================================

@event.listens_for(AuditEvent, 'before_insert')
def audit_event_before_insert(mapper, connection, target):
    """Generate event ID for new audit events."""
    if not target.event_id:
        # Generate unique event ID: AUD-YYYYMMDD-XXXXXX
        date_str = datetime.now().strftime('%Y%m%d')
        
        result = connection.execute(
            text("""
                SELECT COALESCE(MAX(SUBSTRING(event_id FROM 12)::INTEGER), 0) + 1
                FROM audit_events
                WHERE event_id LIKE :pattern
            """),
            {'pattern': f'AUD-{date_str}-%'}
        )
        seq_num = result.scalar()
        
        target.event_id = f"AUD-{date_str}-{seq_num:06d}"


@event.listens_for(AuditEvent, 'after_insert')
def audit_event_after_insert(mapper, connection, target):
    """Process audit event for alerts and anomalies."""
    # This would typically be handled by a background job
    
    # Check if event matches any alert rules
    rules = connection.execute(
        text("""
            SELECT * FROM audit_rules
            WHERE is_active = true
        """)
    ).fetchall()
    
    for rule in rules:
        # Simplified rule evaluation
        if rule.conditions.get('action') == target.action:
            # Create alert
            connection.execute(
                text("""
                    INSERT INTO audit_alerts (
                        id, rule_id, rule_name, severity, title, description,
                        event_ids, user_id, ip_address, created_at
                    ) VALUES (
                        gen_random_uuid(), :rule_id, :rule_name, :severity,
                        :title, :description, ARRAY[:event_id], :user_id,
                        :ip_address, CURRENT_TIMESTAMP
                    )
                """),
                {
                    'rule_id': rule.id,
                    'rule_name': rule.name,
                    'severity': rule.severity,
                    'title': f"Alert: {rule.name}",
                    'description': f"Rule triggered by event {target.event_id}",
                    'event_id': target.event_id,
                    'user_id': target.user_id,
                    'ip_address': target.ip_address
                }
            )


@event.listens_for(AuditSession, 'before_update')
def audit_session_before_update(mapper, connection, target):
    """Calculate duration when session ends."""
    if target.session_end and not target.duration_seconds:
        if target.session_start:
            delta = target.session_end - target.session_start
            target.duration_seconds = int(delta.total_seconds())


# =========================================================================
# FACTORY FUNCTIONS
# =========================================================================

def create_audit_event(
    action: str,
    category: str,
    resource_type: str,
    user_id: Optional[uuid.UUID] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    session_id: Optional[str] = None,
    status: str = 'SUCCESS',
    severity: str = 'INFO',
    **kwargs
) -> AuditEvent:
    """
    Factory function to create a new audit event.
    
    Args:
        action: Action performed
        category: Category of action
        resource_type: Type of resource
        user_id: ID of user
        username: Username
        ip_address: IP address
        session_id: Session ID
        status: Status of action
        severity: Severity level
        **kwargs: Additional audit event attributes
        
    Returns:
        New AuditEvent instance
    """
    event = AuditEvent(
        action=action,
        category=category,
        resource_type=resource_type,
        user_id=user_id,
        username=username,
        ip_address=ip_address or '0.0.0.0',
        session_id=session_id,
        status=status,
        severity=severity,
        **kwargs
    )
    
    return event


def create_audit_session(
    user_id: uuid.UUID,
    session_id: str,
    ip_address: str,
    user_agent: Optional[str] = None,
    auth_method: str = 'password',
    **kwargs
) -> AuditSession:
    """
    Factory function to create a new audit session.
    
    Args:
        user_id: ID of user
        session_id: Session identifier
        ip_address: IP address
        user_agent: User agent
        auth_method: Authentication method
        **kwargs: Additional session attributes
        
    Returns:
        New AuditSession instance
    """
    session = AuditSession(
        user_id=user_id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        auth_method=auth_method,
        session_start=datetime.now(),
        **kwargs
    )
    
    # Lookup user info
    user = object_session(session).get(User, user_id) if object_session(session) else None
    if user:
        session.username = user.username
        session.email = user.email
    
    return session


def create_default_retention_policies(session) -> List[AuditRetention]:
    """
    Create default retention policies.
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        List of created policies
    """
    policies = [
        AuditRetention(
            category='DEBUG',
            severity='DEBUG',
            retention_days=30,
            action='DELETE',
            is_active=True
        ),
        AuditRetention(
            category='INFO',
            severity='INFO',
            retention_days=90,
            action='ARCHIVE',
            is_active=True
        ),
        AuditRetention(
            category='WARNING',
            severity='WARNING',
            retention_days=365,
            action='ARCHIVE',
            is_active=True
        ),
        AuditRetention(
            category='ERROR',
            severity='ERROR',
            retention_days=730,
            action='ARCHIVE',
            is_active=True
        ),
        AuditRetention(
            category='CRITICAL',
            severity='CRITICAL',
            retention_days=2555,  # 7 years
            action='ARCHIVE',
            is_active=True
        ),
        AuditRetention(
            category='SECURITY',
            retention_days=2555,  # 7 years
            action='ARCHIVE',
            is_active=True
        ),
        AuditRetention(
            category='FINANCIAL',
            retention_days=2555,  # 7 years
            action='ARCHIVE',
            is_active=True
        ),
        AuditRetention(
            category='COMPLIANCE',
            retention_days=2555,  # 7 years
            action='ARCHIVE',
            is_active=True
        ),
    ]
    
    for policy in policies:
        existing = session.query(AuditRetention).filter_by(
            category=policy.category,
            severity=policy.severity
        ).first()
        if not existing:
            session.add(policy)
    
    session.commit()
    return policies


def create_default_alert_rules(session) -> List[AuditRule]:
    """
    Create default alert rules.
    
    Args:
        session: SQLAlchemy session
        
    Returns:
        List of created rules
    """
    rules = [
        AuditRule(
            name='Multiple Failed Logins',
            description='Alert on multiple failed login attempts',
            severity='HIGH',
            conditions={
                'action': 'LOGIN_FAILED',
                'category': 'AUTHENTICATION'
            },
            time_window_seconds=300,  # 5 minutes
            threshold=5,
            actions={
                'alert': True,
                'notify': ['security@example.com'],
                'block_ip': True
            },
            is_active=True
        ),
        AuditRule(
            name='Unauthorized Access Attempt',
            description='Alert on unauthorized access attempts',
            severity='CRITICAL',
            conditions={
                'status': 'UNAUTHORIZED',
                'category': 'AUTHORIZATION'
            },
            actions={
                'alert': True,
                'notify': ['security@example.com'],
                'log_review': True
            },
            is_active=True
        ),
        AuditRule(
            name='Data Export',
            description='Alert on large data exports',
            severity='MEDIUM',
            conditions={
                'action': 'EXPORT',
                'category': 'DATA_ACCESS'
            },
            time_window_seconds=3600,  # 1 hour
            threshold=10,
            actions={
                'alert': True,
                'notify': ['admin@example.com']
            },
            is_active=True
        ),
        AuditRule(
            name='Permission Changes',
            description='Alert on permission or role changes',
            severity='HIGH',
            conditions={
                'action': ['PERMISSION_GRANTED', 'PERMISSION_REVOKED', 'ROLE_ASSIGNED', 'ROLE_REMOVED']
            },
            actions={
                'alert': True,
                'notify': ['admin@example.com'],
                'require_review': True
            },
            is_active=True
        ),
        AuditRule(
            name='Payment Failures',
            description='Alert on multiple payment failures',
            severity='HIGH',
            conditions={
                'action': 'PAYMENT',
                'status': 'FAILURE',
                'category': 'FINANCIAL'
            },
            time_window_seconds=3600,
            threshold=3,
            actions={
                'alert': True,
                'notify': ['finance@example.com']
            },
            is_active=True
        ),
    ]
    
    for rule in rules:
        existing = session.query(AuditRule).filter_by(name=rule.name).first()
        if not existing:
            session.add(rule)
    
    session.commit()
    return rules


# =========================================================================
# EXPORTS
# =========================================================================

__all__ = [
    # Main models
    'AuditSession',
    'AuditEvent',
    'AuditChange',
    'AuditAlert',
    'AuditRule',
    'AuditRetention',
    'AuditAnomaly',
    'AuditArchive',
    
    # Enums
    'AuditAction',
    'AuditStatus',
    'AuditSeverity',
    'AuditCategory',
    'AuditResourceType',
    'AuditIPLocation',
    'ComplianceStandard',
    'RetentionAction',
    'ValidationStatus',
    'AnomalyType',
    'AnomalySeverity',
    
    # Factory functions
    'create_audit_event',
    'create_audit_session',
    'create_default_retention_policies',
    'create_default_alert_rules',
]