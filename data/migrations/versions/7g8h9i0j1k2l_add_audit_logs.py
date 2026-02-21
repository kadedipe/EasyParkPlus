# parking-management/data/migrations/versions/7g8h9i0j1k2l_add_audit_logs.py

"""Add comprehensive audit logging system

Revision ID: 7g8h9i0j1k2l
Revises: 6f7g8h9i0j1k
Create Date: 2024-03-15 10:00:00.123456

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime, timedelta
import logging

# Configure logging
logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '7g8h9i0j1k2l'
down_revision: Union[str, None] = '6f7g8h9i0j1k'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define table names
AUDIT_LOGS_TABLE = 'audit_logs'
AUDIT_SESSIONS_TABLE = 'audit_sessions'
AUDIT_EVENTS_TABLE = 'audit_events'
AUDIT_CHANGES_TABLE = 'audit_changes'
AUDIT_ACCESS_TABLE = 'audit_access'
AUDIT_SECURITY_TABLE = 'audit_security'
AUDIT_COMPLIANCE_TABLE = 'audit_compliance'
AUDIT_RETENTION_TABLE = 'audit_retention'
AUDIT_ARCHIVE_TABLE = 'audit_archive'
AUDIT_ALERTS_TABLE = 'audit_alerts'
AUDIT_REPORTS_TABLE = 'audit_reports'
AUDIT_REPORT_SCHEDULES_TABLE = 'audit_report_schedules'
AUDIT_EXEMPTIONS_TABLE = 'audit_exemptions'
AUDIT_POLICIES_TABLE = 'audit_policies'
AUDIT_VALIDATIONS_TABLE = 'audit_validations'
AUDIT_METRICS_TABLE = 'audit_metrics'
AUDIT_ANOMALIES_TABLE = 'audit_anomalies'

# Define ENUM types for PostgreSQL
audit_action_enum = sa.Enum(
    'CREATE',
    'READ',
    'UPDATE',
    'DELETE',
    'LOGIN',
    'LOGOUT',
    'LOGIN_FAILED',
    'EXPORT',
    'IMPORT',
    'DOWNLOAD',
    'UPLOAD',
    'PRINT',
    'SHARE',
    'ARCHIVE',
    'RESTORE',
    'PURGE',
    'APPROVE',
    'REJECT',
    'SUBMIT',
    'CANCEL',
    'VOID',
    'REFUND',
    'PAYMENT',
    'VERIFY',
    'VALIDATE',
    'AUDIT',
    'REVIEW',
    'ESCALATE',
    'DELEGATE',
    'ASSIGN',
    'UNASSIGN',
    'LOCK',
    'UNLOCK',
    'ENABLE',
    'DISABLE',
    'ACTIVATE',
    'DEACTIVATE',
    'SUSPEND',
    'REINSTATE',
    'RESET',
    'CHANGE_PASSWORD',
    'CHANGE_PERMISSIONS',
    'CHANGE_ROLE',
    'CHANGE_SETTINGS',
    'CONFIGURE',
    'INSTALL',
    'UNINSTALL',
    'UPDATE',
    'UPGRADE',
    'BACKUP',
    'RESTORE',
    'SYNC',
    'MERGE',
    'SPLIT',
    'TRANSFER',
    name='audit_action'
)

audit_status_enum = sa.Enum(
    'SUCCESS',
    'FAILURE',
    'PENDING',
    'PROCESSING',
    'COMPLETED',
    'ERROR',
    'TIMEOUT',
    'CANCELLED',
    'BLOCKED',
    'DENIED',
    'UNAUTHORIZED',
    'RATE_LIMITED',
    'VALID',
    'INVALID',
    'EXPIRED',
    name='audit_status'
)

audit_severity_enum = sa.Enum(
    'DEBUG',
    'INFO',
    'NOTICE',
    'WARNING',
    'ERROR',
    'CRITICAL',
    'ALERT',
    'EMERGENCY',
    name='audit_severity'
)

audit_category_enum = sa.Enum(
    'AUTHENTICATION',
    'AUTHORIZATION',
    'DATA_ACCESS',
    'DATA_MODIFICATION',
    'CONFIGURATION',
    'SYSTEM',
    'SECURITY',
    'COMPLIANCE',
    'FINANCIAL',
    'USER_ACTIVITY',
    'ADMIN_ACTIVITY',
    'API_ACTIVITY',
    'INTEGRATION',
    'WORKFLOW',
    'REPORTING',
    'EXPORT',
    'IMPORT',
    'MAINTENANCE',
    name='audit_category'
)

audit_resource_type_enum = sa.Enum(
    'USER',
    'VEHICLE',
    'RESERVATION',
    'PARKING_SPOT',
    'PARKING_ZONE',
    'PAYMENT',
    'INVOICE',
    'SUBSCRIPTION',
    'NOTIFICATION',
    'TEMPLATE',
    'CAMPAIGN',
    'DEVICE',
    'SENSOR',
    'VIOLATION',
    'DISPUTE',
    'REFUND',
    'DISCOUNT',
    'RATE',
    'SETTINGS',
    'PERMISSION',
    'ROLE',
    'API_KEY',
    'WEBHOOK',
    'REPORT',
    'AUDIT_LOG',
    name='audit_resource_type'
)

audit_ip_location_enum = sa.Enum(
    'INTERNAL',
    'EXTERNAL',
    'VPN',
    'PROXY',
    'TOR',
    'CLOUD',
    'UNKNOWN',
    name='audit_ip_location'
)

audit_compliance_standard_enum = sa.Enum(
    'GDPR',
    'CCPA',
    'PCI_DSS',
    'HIPAA',
    'SOX',
    'ISO_27001',
    'NIST',
    'FISMA',
    'FERPA',
    'COPPA',
    name='audit_compliance_standard'
)

audit_retention_action_enum = sa.Enum(
    'ARCHIVE',
    'DELETE',
    'ANONYMIZE',
    'PSEUDONYMIZE',
    'EXPORT',
    name='audit_retention_action'
)

audit_validation_status_enum = sa.Enum(
    'PASSED',
    'FAILED',
    'WARNING',
    'SKIPPED',
    'PENDING',
    name='audit_validation_status'
)

anomaly_type_enum = sa.Enum(
    'UNUSUAL_HOURS',
    'UNUSUAL_LOCATION',
    'UNUSUAL_FREQUENCY',
    'UNUSUAL_VOLUME',
    'MULTIPLE_FAILURES',
    'RAPID_ACTIONS',
    'OUTSIDE_PATTERN',
    'IMPOSSIBLE_TRAVEL',
    'DATA_TAMPERING',
    'ACCESS_PATTERN',
    name='anomaly_type'
)

anomaly_severity_enum = sa.Enum(
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL',
    name='anomaly_severity'
)


def upgrade() -> None:
    """
    Upgrade migration - creates comprehensive audit logging system
    """
    logger.info(f"Starting migration {revision}: Add audit logging system")
    
    # Create ENUM types first (PostgreSQL specific)
    if op.get_context().dialect.name == 'postgresql':
        enums = [
            audit_action_enum, audit_status_enum, audit_severity_enum,
            audit_category_enum, audit_resource_type_enum, audit_ip_location_enum,
            audit_compliance_standard_enum, audit_retention_action_enum,
            audit_validation_status_enum, anomaly_type_enum, anomaly_severity_enum
        ]
        for enum in enums:
            enum.create(op.get_bind(), checkfirst=True)
        logger.info("Created ENUM types")
    
    # Create audit sessions table
    logger.info("Creating audit sessions table")
    op.create_table(
        AUDIT_SESSIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('session_id', sa.String(255), nullable=False, unique=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('username', sa.String(255)),
        sa.Column('email', sa.String(255)),
        sa.Column('session_token', sa.String(500)),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('ip_location', postgresql.JSONB),  # GeoIP data
        sa.Column('ip_location_type', sa.String(20)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('device_type', sa.String(50)),
        sa.Column('browser', sa.String(100)),
        sa.Column('os', sa.String(100)),
        sa.Column('device_id', sa.String(255)),
        sa.Column('session_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('session_end', sa.DateTime(timezone=True)),
        sa.Column('duration_seconds', sa.Integer),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_impersonated', sa.Boolean, server_default='false'),
        sa.Column('impersonated_by', postgresql.UUID(as_uuid=True)),
        sa.Column('auth_method', sa.String(50)),  # password, oauth, saml, etc.
        sa.Column('auth_provider', sa.String(100)),
        sa.Column('mfa_used', sa.Boolean, server_default='false'),
        sa.Column('mfa_method', sa.String(50)),
        sa.Column('login_location', sa.String(255)),
        sa.Column('logout_reason', sa.String(100)),  # user, timeout, forced
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_audit_sessions_id', 'session_id'),
        sa.Index('ix_audit_sessions_user', 'user_id'),
        sa.Index('ix_audit_sessions_ip', 'ip_address'),
        sa.Index('ix_audit_sessions_start', 'session_start'),
        sa.Index('ix_audit_sessions_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['impersonated_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('User session tracking for audit purposes'),
    )
    
    # Create audit events table (main audit log)
    logger.info("Creating audit events table")
    op.create_table(
        AUDIT_EVENTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('event_id', sa.String(100), nullable=False, unique=True),
        sa.Column('correlation_id', sa.String(100)),  # For tracing related events
        sa.Column('parent_event_id', sa.String(100)),
        
        # Actor information
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('username', sa.String(255)),
        sa.Column('email', sa.String(255)),
        sa.Column('role', sa.String(100)),
        sa.Column('permissions', postgresql.ARRAY(sa.String(100))),
        sa.Column('session_id', sa.String(255)),
        sa.Column('impersonated_by', postgresql.UUID(as_uuid=True)),
        
        # Action details
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='INFO'),
        
        # Resource details
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(255)),
        sa.Column('resource_name', sa.String(255)),
        sa.Column('resource_parent_type', sa.String(50)),
        sa.Column('resource_parent_id', sa.String(255)),
        
        # Request details
        sa.Column('request_id', sa.String(100)),
        sa.Column('request_method', sa.String(10)),
        sa.Column('request_url', sa.String(1000)),
        sa.Column('request_headers', postgresql.JSONB),
        sa.Column('request_params', postgresql.JSONB),
        sa.Column('request_body', postgresql.JSONB),
        sa.Column('request_size', sa.Integer),
        
        # Response details
        sa.Column('response_status', sa.Integer),
        sa.Column('response_headers', postgresql.JSONB),
        sa.Column('response_body', postgresql.JSONB),
        sa.Column('response_size', sa.Integer),
        sa.Column('response_time_ms', sa.Integer),
        
        # IP and location
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('ip_location', postgresql.JSONB),
        sa.Column('ip_location_type', sa.String(20)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('device_fingerprint', sa.String(255)),
        
        # Changes
        sa.Column('changes', postgresql.JSONB),  # Summary of changes
        sa.Column('change_count', sa.Integer, server_default='0'),
        sa.Column('before_state', postgresql.JSONB),
        sa.Column('after_state', postgresql.JSONB),
        
        # Compliance
        sa.Column('compliance_tags', postgresql.ARRAY(sa.String(50))),
        sa.Column('retention_days', sa.Integer),
        sa.Column('sensitive_data', sa.Boolean, server_default='false'),
        sa.Column('pii_present', sa.Boolean, server_default='false'),
        sa.Column('encrypted', sa.Boolean, server_default='false'),
        
        # Metadata
        sa.Column('tags', postgresql.ARRAY(sa.String(100))),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_audit_events_id', 'event_id'),
        sa.Index('ix_audit_events_correlation', 'correlation_id'),
        sa.Index('ix_audit_events_user', 'user_id'),
        sa.Index('ix_audit_events_action', 'action'),
        sa.Index('ix_audit_events_category', 'category'),
        sa.Index('ix_audit_events_status', 'status'),
        sa.Index('ix_audit_events_severity', 'severity'),
        sa.Index('ix_audit_events_resource', 'resource_type', 'resource_id'),
        sa.Index('ix_audit_events_ip', 'ip_address'),
        sa.Index('ix_audit_events_created', 'created_at'),
        sa.Index('ix_audit_events_composite', 'created_at', 'category', 'action'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['impersonated_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], [f'{AUDIT_SESSIONS_TABLE}.session_id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Main audit events table tracking all system actions'),
        
        # Partition by month
        postgresql_partition_by='RANGE (created_at)',
    )
    
    # Create audit changes table (detailed field-level changes)
    logger.info("Creating audit changes table")
    op.create_table(
        AUDIT_CHANGES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('event_id', sa.String(100), nullable=False),
        sa.Column('table_name', sa.String(255), nullable=False),
        sa.Column