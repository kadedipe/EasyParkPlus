# parking-management/data/migrations/versions/6f7g8h9i0j1k_add_notifications.py

"""Add comprehensive notification system

Revision ID: 6f7g8h9i0j1k
Revises: 5e6f7g8h9i0j
Create Date: 2024-03-01 09:00:00.123456

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
revision: str = '6f7g8h9i0j1k'
down_revision: Union[str, None] = '5e6f7g8h9i0j'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define table names
NOTIFICATIONS_TABLE = 'notifications'
NOTIFICATION_TEMPLATES_TABLE = 'notification_templates'
NOTIFICATION_PREFERENCES_TABLE = 'notification_preferences'
NOTIFICATION_QUEUE_TABLE = 'notification_queue'
NOTIFICATION_LOGS_TABLE = 'notification_logs'
NOTIFICATION_ATTACHMENTS_TABLE = 'notification_attachments'
NOTIFICATION_CAMPAIGNS_TABLE = 'notification_campaigns'
NOTIFICATION_CAMPAIGN_RECIPIENTS_TABLE = 'notification_campaign_recipients'
NOTIFICATION_SUBSCRIPTIONS_TABLE = 'notification_subscriptions'
NOTIFICATION_DEVICES_TABLE = 'notification_devices'
NOTIFICATION_WEBHOOKS_TABLE = 'notification_webhooks'
NOTIFICATION_WEBHOOK_DELIVERIES_TABLE = 'notification_webhook_deliveries'
NOTIFICATION_SCHEDULES_TABLE = 'notification_schedules'
NOTIFICATION_BATCHES_TABLE = 'notification_batches'
NOTIFICATION_SUPPRESSIONS_TABLE = 'notification_suppressions'
NOTIFICATION_RULES_TABLE = 'notification_rules'
NOTIFICATION_TRIGGERS_TABLE = 'notification_triggers'

# Define ENUM types for PostgreSQL
notification_type_enum = sa.Enum(
    'reservation_confirmation',
    'reservation_reminder',
    'reservation_modification',
    'reservation_cancellation',
    'check_in_success',
    'check_out_success',
    'payment_receipt',
    'payment_failed',
    'payment_refunded',
    'violation_issued',
    'violation_paid',
    'vehicle_alert',
    'vehicle_blacklisted',
    'subscription_renewal',
    'subscription_expiring',
    'subscription_cancelled',
    'account_created',
    'password_reset',
    'email_verification',
    'phone_verification',
    'security_alert',
    'maintenance_reminder',
    'system_alert',
    'promotional',
    'survey',
    'feedback_request',
    'waitlist_confirmed',
    'spot_available',
    'rate_change',
    'policy_update',
    name='notification_type'
)

notification_channel_enum = sa.Enum(
    'email',
    'sms',
    'push',
    'whatsapp',
    'telegram',
    'slack',
    'webhook',
    'in_app',
    'voice',
    'fax',
    name='notification_channel'
)

notification_status_enum = sa.Enum(
    'pending',
    'queued',
    'processing',
    'sent',
    'delivered',
    'failed',
    'bounced',
    'opened',
    'clicked',
    'unsubscribed',
    'suppressed',
    'expired',
    'cancelled',
    name='notification_status'
)

notification_priority_enum = sa.Enum(
    'low',
    'normal',
    'high',
    'urgent',
    'critical',
    name='notification_priority'
)

template_type_enum = sa.Enum(
    'email_html',
    'email_text',
    'sms_text',
    'push_notification',
    'whatsapp_text',
    'in_app',
    name='template_type'
)

device_type_enum = sa.Enum(
    'ios',
    'android',
    'web',
    'desktop',
    'tablet',
    name='device_type'
)

subscription_tier_enum = sa.Enum(
    'free',
    'basic',
    'premium',
    'enterprise',
    name='subscription_tier'
)

campaign_status_enum = sa.Enum(
    'draft',
    'scheduled',
    'sending',
    'paused',
    'completed',
    'cancelled',
    'archived',
    name='campaign_status'
)

webhook_method_enum = sa.Enum(
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    name='webhook_method'
)

frequency_enum = sa.Enum(
    'immediate',
    'daily_digest',
    'weekly_digest',
    'monthly_digest',
    'never',
    name='frequency'
)

suppression_reason_enum = sa.Enum(
    'unsubscribed',
    'bounced',
    'complained',
    'invalid',
    'opted_out',
    'user_deleted',
    name='suppression_reason'
)


def upgrade() -> None:
    """
    Upgrade migration - creates comprehensive notification system
    """
    logger.info(f"Starting migration {revision}: Add notification system")
    
    # Create ENUM types first (PostgreSQL specific)
    if op.get_context().dialect.name == 'postgresql':
        enums = [
            notification_type_enum, notification_channel_enum, notification_status_enum,
            notification_priority_enum, template_type_enum, device_type_enum,
            subscription_tier_enum, campaign_status_enum, webhook_method_enum,
            frequency_enum, suppression_reason_enum
        ]
        for enum in enums:
            enum.create(op.get_bind(), checkfirst=True)
        logger.info("Created ENUM types")
    
    # Create notification templates table
    logger.info("Creating notification templates table")
    op.create_table(
        NOTIFICATION_TEMPLATES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('template_type', sa.String(50), nullable=False),
        
        # Template content
        sa.Column('subject', sa.String(255)),  # For email, push title
        sa.Column('preheader', sa.String(255)),  # Email preheader text
        sa.Column('content_html', sa.Text),  # HTML version
        sa.Column('content_text', sa.Text),  # Plain text version
        sa.Column('content_json', postgresql.JSONB),  # For push notifications
        sa.Column('template_data', postgresql.JSONB),  # Default template data
        
        # Template variables
        sa.Column('variables', postgresql.ARRAY(sa.String(100))),
        sa.Column('required_variables', postgresql.ARRAY(sa.String(100))),
        
        # Design
        sa.Column('design', postgresql.JSONB),  # Visual editor data
        sa.Column('thumbnail_url', sa.String(500)),
        sa.Column('preview_url', sa.String(500)),
        
        # Localization
        sa.Column('locale', sa.String(10), server_default='en'),
        sa.Column('translations', postgresql.JSONB),
        
        # Versioning
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('is_draft', sa.Boolean, server_default='true'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_system', sa.Boolean, server_default='false'),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True)),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        
        # Indexes
        sa.Index('ix_notification_templates_code', 'code', unique=True),
        sa.Index('ix_notification_templates_type', 'notification_type'),
        sa.Index('ix_notification_templates_channel', 'channel'),
        sa.Index('ix_notification_templates_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Templates for different notification types and channels'),
    )
    
    # Create notification preferences table
    logger.info("Creating notification preferences table")
    op.create_table(
        NOTIFICATION_PREFERENCES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('frequency', sa.String(20), server_default='immediate'),
        sa.Column('quiet_hours_start', sa.Time),
        sa.Column('quiet_hours_end', sa.Time),
        sa.Column('quiet_hours_timezone', sa.String(50)),
        sa.Column('max_per_day', sa.Integer),
        sa.Column('max_per_week', sa.Integer),
        sa.Column('last_sent_at', sa.DateTime(timezone=True)),
        sa.Column('last_sent_count', sa.Integer, server_default='0'),
        sa.Column('reset_date', sa.Date),
        
        # Override addresses
        sa.Column('email_override', sa.String(255)),
        sa.Column('phone_override', sa.String(20)),
        sa.Column('push_device_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_notification_prefs_user', 'user_id'),
        sa.Index('ix_notification_prefs_type', 'notification_type'),
        sa.Index('ix_notification_prefs_enabled', 'enabled'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        
        # Unique constraint
        sa.UniqueConstraint('user_id', 'notification_type', 'channel', name='uq_user_notification_channel'),
        
        # Table comments
        sa.Comment('User preferences for notification delivery'),
    )
    
    # Create notification devices table (for push notifications)
    logger.info("Creating notification devices table")
    op.create_table(
        NOTIFICATION_DEVICES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('device_type', sa.String(20), nullable=False),
        sa.Column('device_token', sa.String(500), nullable=False),
        sa.Column('device_name', sa.String(255)),
        sa.Column('device_model', sa.String(100)),
        sa.Column('os_version', sa.String(50)),
        sa.Column('app_version', sa.String(50)),
        sa.Column('push_token', sa.String(500)),
        sa.Column('voip_token', sa.String(500)),
        sa.Column('arn_endpoint', sa.String(500)),  # AWS ARN endpoint
        
        # Status
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_verified', sa.Boolean, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('last_active_at', sa.DateTime(timezone=True)),
        sa.Column('last_notification_at', sa.DateTime(timezone=True)),
        sa.Column('failed_attempts', sa.Integer, server_default='0'),
        sa.Column('last_error', sa.Text),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        
        # Indexes
        sa.Index('ix_notification_devices_user', 'user_id'),
        sa.Index('ix_notification_devices_token', 'device_token'),
        sa.Index('ix_notification_devices_active', 'is_active'),
        sa.Index('ix_notification_devices_last_active', 'last_active_at'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Registered devices for push notifications'),
    )
    
    # Create notifications table (main table)
    logger.info("Creating notifications table")
    op.create_table(
        NOTIFICATIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('notification_number', sa.String(50), nullable=False, unique=True),
        sa.Column('external_id', sa.String(255), unique=True),  # Provider message ID
        
        # Recipient
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('recipient_email', sa.String(255)),
        sa.Column('recipient_phone', sa.String(20)),
        sa.Column('recipient_device_id', postgresql.UUID(as_uuid=True)),
        sa.Column('recipient_push_token', sa.String(500)),
        
        # Content
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False, server_default='normal'),
        sa.Column('template_id', postgresql.UUID(as_uuid=True)),
        sa.Column('template_data', postgresql.JSONB),
        sa.Column('subject', sa.String(255)),
        sa.Column('preheader', sa.String(255)),
        sa.Column('content_html', sa.Text),
        sa.Column('content_text', sa.Text),
        sa.Column('content_json', postgresql.JSONB),
        
        # Related entities
        sa.Column('reservation_id', postgresql.UUID(as_uuid=True)),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True)),
        sa.Column('violation_id', postgresql.UUID(as_uuid=True)),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True)),
        
        # Status tracking
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('status_history', postgresql.JSONB),
        sa.Column('queued_at', sa.DateTime(timezone=True)),
        sa.Column('sent_at', sa.DateTime(timezone=True)),
        sa.Column('delivered_at', sa.DateTime(timezone=True)),
        sa.Column('opened_at', sa.DateTime(timezone=True)),
        sa.Column('clicked_at', sa.DateTime(timezone=True)),
        sa.Column('failed_at', sa.DateTime(timezone=True)),
        sa.Column('failure_reason', sa.Text),
        sa.Column('failure_code', sa.String(100)),
        sa.Column('retry_count', sa.Integer, server_default='0'),
        sa.Column('max_retries', sa.Integer, server_default='3'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True)),
        
        # Provider details
        sa.Column('provider', sa.String(50)),  # aws_ses, twilio, firebase, etc.
        sa.Column('provider_message_id', sa.String(255)),
        sa.Column('provider_response', postgresql.JSONB),
        sa.Column('provider_cost', sa.Numeric(10, 6)),
        
        # Tracking
        sa.Column('tracking_id', sa.String(100)),  # For open/click tracking
        sa.Column('ip_address', sa.String(45)),  # IP of recipient when opened
        sa.Column('user_agent', sa.String(500)),
        sa.Column('referrer', sa.String(500)),
        
        # Batch info
        sa.Column('batch_id', postgresql.UUID(as_uuid=True)),
        sa.Column('batch_sequence', sa.Integer),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_notifications_number', 'notification_number', unique=True),
        sa.Index('ix_notifications_user', 'user_id'),
        sa.Index('ix_notifications_recipient_email', 'recipient_email'),
        sa.Index('ix_notifications_recipient_phone', 'recipient_phone'),
        sa.Index('ix_notifications_type', 'notification_type'),
        sa.Index('ix_notifications_channel', 'channel'),
        sa.Index('ix_notifications_status', 'status'),
        sa.Index('ix_notifications_created_at', 'created_at'),
        sa.Index('ix_notifications_sent_at', 'sent_at'),
        sa.Index('ix_notifications_tracking', 'tracking_id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recipient_device_id'], [f'{NOTIFICATION_DEVICES_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['template_id'], [f'{NOTIFICATION_TEMPLATES_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reservation_id'], ['reservations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['violation_id'], ['vehicle_violations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Main notifications table tracking all outgoing notifications'),
        
        # Partition by month
        postgresql_partition_by='RANGE (created_at)',
    )
    
    # Create notification queue table
    logger.info("Creating notification queue table")
    op.create_table(
        NOTIFICATION_QUEUE_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('notification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('priority', sa.Integer, nullable=False, server_default='0'),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=False),
        sa.Column('locked_until', sa.DateTime(timezone=True)),
        sa.Column('locked_by', sa.String(255)),
        sa.Column('attempts', sa.Integer, server_default='0'),
        sa.Column('max_attempts', sa.Integer, server_default='3'),
        sa.Column('last_error', sa.Text),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_notification_queue_notification', 'notification_id'),
        sa.Index('ix_notification_queue_scheduled', 'scheduled_for'),
        sa.Index('ix_notification_queue_priority', 'priority'),
        sa.Index('ix_notification_queue_locked', 'locked_until'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['notification_id'], [f'{NOTIFICATIONS_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Queue for scheduled and pending notifications'),
    )
    
    # Create notification logs table
    logger.info("Creating notification logs table")
    op.create_table(
        NOTIFICATION_LOGS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('notification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),  # sent, delivered, opened, clicked, failed
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('provider_response', postgresql.JSONB),
        sa.Column('error_code', sa.String(100)),
        sa.Column('error_message', sa.Text),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('referrer', sa.String(500)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_notification_logs_notification', 'notification_id'),
        sa.Index('ix_notification_logs_event', 'event_type'),
        sa.Index('ix_notification_logs_timestamp', 'timestamp'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['notification_id'], [f'{NOTIFICATIONS_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Detailed logs of notification events'),
        
        # Partition by month
        postgresql_partition_by='RANGE (timestamp)',
    )
    
    # Create notification attachments table
    logger.info("Creating notification attachments table")
    op.create_table(
        NOTIFICATION_ATTACHMENTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('notification_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_type', sa.String(100)),
        sa.Column('file_size', sa.Integer),
        sa.Column('file_url', sa.String(500)),
        sa.Column('file_path', sa.String(500)),
        sa.Column('content_id', sa.String(255)),  # For inline images
        sa.Column('is_inline', sa.Boolean, server_default='false'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_notification_attachments_notification', 'notification_id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['notification_id'], [f'{NOTIFICATIONS_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Attachments for notifications'),
    )
    
    # Create notification campaigns table
    logger.info("Creating notification campaigns table")
    op.create_table(
        NOTIFICATION_CAMPAIGNS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text),
        sa.Column('campaign_type', sa.String(50), nullable=False),  # promotional, transactional, etc.
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        
        # Schedule
        sa.Column('scheduled_start', sa.DateTime(timezone=True)),
        sa.Column('scheduled_end', sa.DateTime(timezone=True)),
        sa.Column('timezone', sa.String(50), server_default='UTC'),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('cancelled_at', sa.DateTime(timezone=True)),
        sa.Column('cancelled_reason', sa.Text),
        
        # Targeting
        sa.Column('target_audience', postgresql.JSONB),  # User filters/segments
        sa.Column('target_user_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column('excluded_user_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True))),
        sa.Column('target_channels', postgresql.ARRAY(sa.String(50))),
        
        # Content
        sa.Column('template_id', postgresql.UUID(as_uuid=True)),
        sa.Column('template_data', postgresql.JSONB),
        sa.Column('subject', sa.String(255)),
        sa.Column('content_html', sa.Text),
        sa.Column('content_text', sa.Text),
        
        # A/B Testing
        sa.Column('is_ab_test', sa.Boolean, server_default='false'),
        sa.Column('test_variants', postgresql.JSONB),
        sa.Column('test_winner_criteria', sa.String(50)),
        sa.Column('test_winner_determined_at', sa.DateTime(timezone=True)),
        
        # Statistics
        sa.Column('total_recipients', sa.Integer, server_default='0'),
        sa.Column('sent_count', sa.Integer, server_default='0'),
        sa.Column('delivered_count', sa.Integer, server_default='0'),
        sa.Column('opened_count', sa.Integer, server_default='0'),
        sa.Column('clicked_count', sa.Integer, server_default='0'),
        sa.Column('converted_count', sa.Integer, server_default='0'),
        sa.Column('bounced_count', sa.Integer, server_default='0'),
        sa.Column('complained_count', sa.Integer, server_default='0'),
        sa.Column('unsubscribed_count', sa.Integer, server_default='0'),
        sa.Column('failed_count', sa.Integer, server_default='0'),
        
        # Metadata
        sa.Column('settings', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True)),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        
        # Indexes
        sa.Index('ix_notification_campaigns_code', 'code', unique=True),
        sa.Index('ix_notification_campaigns_status', 'status'),
        sa.Index('ix_notification_campaigns_scheduled', 'scheduled_start'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['template_id'], [f'{NOTIFICATION_TEMPLATES_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Marketing and notification campaigns'),
    )
    
    # Create notification campaign recipients table
    logger.info("Creating notification campaign recipients table")
    op.create_table(
        NOTIFICATION_CAMPAIGN_RECIPIENTS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(20)),
        sa.Column('notification_id', postgresql.UUID(as_uuid=True)),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('sent_at', sa.DateTime(timezone=True)),
        sa.Column('delivered_at', sa.DateTime(timezone=True)),
        sa.Column('opened_at', sa.DateTime(timezone=True)),
        sa.Column('clicked_at', sa.DateTime(timezone=True)),
        sa.Column('converted_at', sa.DateTime(timezone=True)),
        sa.Column('bounced_at', sa.DateTime(timezone=True)),
        sa.Column('complained_at', sa.DateTime(timezone=True)),
        sa.Column('unsubscribed_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_campaign_recipients_campaign', 'campaign_id'),
        sa.Index('ix_campaign_recipients_user', 'user_id'),
        sa.Index('ix_campaign_recipients_email', 'email'),
        sa.Index('ix_campaign_recipients_status', 'status'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['campaign_id'], [f'{NOTIFICATION_CAMPAIGNS_TABLE}.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['notification_id'], [f'{NOTIFICATIONS_TABLE}.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Individual recipients of campaign notifications'),
    )
    
    # Create notification subscriptions table (for newsletter, etc.)
    logger.info("Creating notification subscriptions table")
    op.create_table(
        NOTIFICATION_SUBSCRIPTIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(20)),
        sa.Column('subscription_type', sa.String(100), nullable=False),  # newsletter, alerts, etc.
        sa.Column('tier', sa.String(50), server_default='free'),
        sa.Column('verified', sa.Boolean, server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('verification_token', sa.String(255)),
        sa.Column('verification_sent_at', sa.DateTime(timezone=True)),
        sa.Column('subscribed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('unsubscribed_at', sa.DateTime(timezone=True)),
        sa.Column('unsubscribe_reason', sa.Text),
        sa.Column('unsubscribe_token', sa.String(255)),
        sa.Column('preferences', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Indexes
        sa.Index('ix_notification_subs_user', 'user_id'),
        sa.Index('ix_notification_subs_email', 'email'),
        sa.Index('ix_notification_subs_type', 'subscription_type'),
        sa.Index('ix_notification_subs_verified', 'verified'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        
        # Unique constraint
        sa.UniqueConstraint('user_id', 'subscription_type', name='uq_user_subscription_type'),
        
        # Table comments
        sa.Comment('Newsletter and marketing subscriptions'),
    )
    
    # Create notification webhooks table
    logger.info("Creating notification webhooks table")
    op.create_table(
        NOTIFICATION_WEBHOOKS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('method', sa.String(10), nullable=False, server_default='POST'),
        sa.Column('headers', postgresql.JSONB),
        sa.Column('auth_type', sa.String(50)),  # basic, bearer, api_key
        sa.Column('auth_credentials', postgresql.JSONB),  # Encrypted
        
        # Events
        sa.Column('events', postgresql.ARRAY(sa.String(100))),  # Which events trigger this webhook
        sa.Column('secret', sa.String(255)),  # For signature verification
        sa.Column('signature_header', sa.String(100)),  # Header name for signature
        
        # Retry configuration
        sa.Column('retry_count', sa.Integer, server_default='3'),
        sa.Column('retry_delay', sa.Integer, server_default='60'),  # seconds
        sa.Column('timeout', sa.Integer, server_default='30'),  # seconds
        
        # Rate limiting
        sa.Column('rate_limit', sa.Integer),  # requests per minute
        sa.Column('rate_limit_reset', sa.DateTime(timezone=True)),
        
        # Status
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True)),
        sa.Column('last_success_at', sa.DateTime(timezone=True)),
        sa.Column('last_failure_at', sa.DateTime(timezone=True)),
        sa.Column('failure_count', sa.Integer, server_default='0'),
        sa.Column('success_count', sa.Integer, server_default='0'),
        sa.Column('average_response_time_ms', sa.Float),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        
        # Indexes
        sa.Index('ix_notification_webhooks_url', 'url'),
        sa.Index('ix_notification_webhooks_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Webhook endpoints for external notifications'),
    )
    
    # Create notification webhook deliveries table
    logger.info("Creating notification webhook deliveries table")
    op.create_table(
        NOTIFICATION_WEBHOOK_DELIVERIES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('webhook_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('headers', postgresql.JSONB),
        sa.Column('response_status', sa.Integer),
        sa.Column('response_body', sa.Text),
        sa.Column('response_headers', postgresql.JSONB),
        sa.Column('response_time_ms', sa.Integer),
        sa.Column('success', sa.Boolean),
        sa.Column('error_message', sa.Text),
        sa.Column('attempt', sa.Integer, server_default='1'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_webhook_deliveries_webhook', 'webhook_id'),
        sa.Index('ix_webhook_deliveries_success', 'success'),
        sa.Index('ix_webhook_deliveries_created', 'created_at'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['webhook_id'], [f'{NOTIFICATION_WEBHOOKS_TABLE}.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Delivery attempts for notification webhooks'),
    )
    
    # Create notification schedules table
    logger.info("Creating notification schedules table")
    op.create_table(
        NOTIFICATION_SCHEDULES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True)),
        sa.Column('template_data', postgresql.JSONB),
        sa.Column('schedule_type', sa.String(50), nullable=False),  # cron, interval, fixed
        sa.Column('cron_expression', sa.String(100)),
        sa.Column('interval_seconds', sa.Integer),
        sa.Column('fixed_times', postgresql.ARRAY(sa.DateTime(timezone=True))),
        sa.Column('timezone', sa.String(50), server_default='UTC'),
        
        # Targeting
        sa.Column('target_criteria', postgresql.JSONB),  # SQL or filter criteria
        
        # Status
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('last_run_at', sa.DateTime(timezone=True)),
        sa.Column('next_run_at', sa.DateTime(timezone=True)),
        sa.Column('total_runs', sa.Integer, server_default='0'),
        sa.Column('total_notifications', sa.Integer, server_default='0'),
        sa.Column('last_error', sa.Text),
        
        # Metadata
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_notification_schedules_next', 'next_run_at'),
        sa.Index('ix_notification_schedules_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['template_id'], [f'{NOTIFICATION_TEMPLATES_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Scheduled notification jobs'),
    )
    
    # Create notification batches table
    logger.info("Creating notification batches table")
    op.create_table(
        NOTIFICATION_BATCHES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('batch_number', sa.String(50), nullable=False, unique=True),
        sa.Column('name', sa.String(255)),
        sa.Column('description', sa.Text),
        sa.Column('total_count', sa.Integer, server_default='0'),
        sa.Column('processed_count', sa.Integer, server_default='0'),
        sa.Column('success_count', sa.Integer, server_default='0'),
        sa.Column('failed_count', sa.Integer, server_default='0'),
        sa.Column('status', sa.String(20), server_default='processing'),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_notification_batches_number', 'batch_number', unique=True),
        sa.Index('ix_notification_batches_status', 'status'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Batch processing groups for notifications'),
    )
    
    # Create notification suppressions table
    logger.info("Creating notification suppressions table")
    op.create_table(
        NOTIFICATION_SUPPRESSIONS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(20)),
        sa.Column('device_token', sa.String(500)),
        sa.Column('reason', sa.String(50), nullable=False),
        sa.Column('reason_details', sa.Text),
        sa.Column('suppressed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('is_permanent', sa.Boolean, server_default='false'),
        sa.Column('source', sa.String(100)),  # system, user, provider
        sa.Column('provider_feedback', postgresql.JSONB),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_notification_suppressions_user', 'user_id'),
        sa.Index('ix_notification_suppressions_email', 'email'),
        sa.Index('ix_notification_suppressions_phone', 'phone'),
        sa.Index('ix_notification_suppressions_reason', 'reason'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        
        # Table comments
        sa.Comment('Suppressed recipients (bounces, complaints, unsubscribes)'),
    )
    
    # Create notification rules table
    logger.info("Creating notification rules table")
    op.create_table(
        NOTIFICATION_RULES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('rule_type', sa.String(50), nullable=False),  # throttle, filter, transform
        sa.Column('conditions', postgresql.JSONB),  # When to apply rule
        sa.Column('actions', postgresql.JSONB),  # What to do
        sa.Column('priority', sa.Integer, server_default='0'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_notification_rules_active', 'is_active'),
        sa.Index('ix_notification_rules_type', 'rule_type'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Rules for processing notifications (throttling, filtering, etc.)'),
    )
    
    # Create notification triggers table
    logger.info("Creating notification triggers table")
    op.create_table(
        NOTIFICATION_TRIGGERS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('trigger_event', sa.String(100), nullable=False),  # reservation.created, payment.received, etc.
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True)),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('delay_seconds', sa.Integer, server_default='0'),
        sa.Column('conditions', postgresql.JSONB),  # When to trigger
        sa.Column('template_data_map', postgresql.JSONB),  # How to map event data to template
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        
        # Indexes
        sa.Index('ix_notification_triggers_event', 'trigger_event'),
        sa.Index('ix_notification_triggers_active', 'is_active'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['template_id'], [f'{NOTIFICATION_TEMPLATES_TABLE}.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Automatic triggers for notifications based on system events'),
    )
    
    # Create functions and triggers
    logger.info("Creating database functions and triggers")
    
    # Function to generate notification number
    op.execute("""
    CREATE OR REPLACE FUNCTION generate_notification_number()
    RETURNS TRIGGER AS $$
    DECLARE
        seq_num INTEGER;
        date_prefix TEXT;
    BEGIN
        date_prefix := TO_CHAR(CURRENT_DATE, 'YYYYMMDD');
        
        SELECT COALESCE(MAX(SUBSTRING(notification_number FROM 11)::INTEGER), 0) + 1
        INTO seq_num
        FROM notifications
        WHERE notification_number LIKE 'NOT-' || date_prefix || '-%';
        
        NEW.notification_number := 'NOT-' || date_prefix || '-' || LPAD(seq_num::TEXT, 6, '0');
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for notification number
    op.execute("""
    CREATE TRIGGER generate_notification_number_trigger
        BEFORE INSERT ON notifications
        FOR EACH ROW
        WHEN (NEW.notification_number IS NULL)
        EXECUTE FUNCTION generate_notification_number();
    """)
    
    # Function to generate batch number
    op.execute("""
    CREATE OR REPLACE FUNCTION generate_batch_number()
    RETURNS TRIGGER AS $$
    DECLARE
        seq_num INTEGER;
        date_prefix TEXT;
    BEGIN
        date_prefix := TO_CHAR(CURRENT_DATE, 'YYYYMMDD');
        
        SELECT COALESCE(MAX(SUBSTRING(batch_number FROM 11)::INTEGER), 0) + 1
        INTO seq_num
        FROM notification_batches
        WHERE batch_number LIKE 'BAT-' || date_prefix || '-%';
        
        NEW.batch_number := 'BAT-' || date_prefix || '-' || LPAD(seq_num::TEXT, 6, '0');
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for batch number
    op.execute("""
    CREATE TRIGGER generate_batch_number_trigger
        BEFORE INSERT ON notification_batches
        FOR EACH ROW
        WHEN (NEW.batch_number IS NULL)
        EXECUTE FUNCTION generate_batch_number();
    """)
    
    # Function to queue notifications
    op.execute("""
    CREATE OR REPLACE FUNCTION queue_notification()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.status = 'pending' THEN
            INSERT INTO notification_queue (
                id, notification_id, priority, scheduled_for
            ) VALUES (
                gen_random_uuid(),
                NEW.id,
                CASE 
                    WHEN NEW.priority = 'critical' THEN 100
                    WHEN NEW.priority = 'urgent' THEN 75
                    WHEN NEW.priority = 'high' THEN 50
                    WHEN NEW.priority = 'normal' THEN 25
                    ELSE 10
                END,
                COALESCE(NEW.scheduled_for, NEW.created_at)
            );
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for queueing
    op.execute("""
    CREATE TRIGGER queue_notification_trigger
        AFTER INSERT ON notifications
        FOR EACH ROW
        WHEN (NEW.status = 'pending')
        EXECUTE FUNCTION queue_notification();
    """)
    
    # Function to check suppression
    op.execute("""
    CREATE OR REPLACE FUNCTION check_notification_suppression()
    RETURNS TRIGGER AS $$
    DECLARE
        v_suppression RECORD;
    BEGIN
        -- Check email suppression
        IF NEW.recipient_email IS NOT NULL THEN
            SELECT * INTO v_suppression
            FROM notification_suppressions
            WHERE email = NEW.recipient_email
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                AND is_permanent = true;
                
            IF v_suppression.id IS NOT NULL THEN
                NEW.status := 'suppressed';
                NEW.failure_reason := 'Recipient suppressed: ' || v_suppression.reason;
            END IF;
        END IF;
        
        -- Check phone suppression
        IF NEW.recipient_phone IS NOT NULL AND NEW.status != 'suppressed' THEN
            SELECT * INTO v_suppression
            FROM notification_suppressions
            WHERE phone = NEW.recipient_phone
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                AND is_permanent = true;
                
            IF v_suppression.id IS NOT NULL THEN
                NEW.status := 'suppressed';
                NEW.failure_reason := 'Recipient suppressed: ' || v_suppression.reason;
            END IF;
        END IF;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for suppression check
    op.execute("""
    CREATE TRIGGER check_notification_suppression_trigger
        BEFORE INSERT ON notifications
        FOR EACH ROW
        EXECUTE FUNCTION check_notification_suppression();
    """)
    
    # Function to update campaign statistics
    op.execute("""
    CREATE OR REPLACE FUNCTION update_campaign_statistics()
    RETURNS TRIGGER AS $$
    BEGIN
        IF NEW.campaign_id IS NOT NULL THEN
            UPDATE notification_campaigns
            SET 
                sent_count = sent_count + CASE WHEN NEW.status = 'sent' THEN 1 ELSE 0 END,
                delivered_count = delivered_count + CASE WHEN NEW.status = 'delivered' THEN 1 ELSE 0 END,
                opened_count = opened_count + CASE WHEN NEW.status = 'opened' THEN 1 ELSE 0 END,
                clicked_count = clicked_count + CASE WHEN NEW.status = 'clicked' THEN 1 ELSE 0 END,
                failed_count = failed_count + CASE WHEN NEW.status = 'failed' THEN 1 ELSE 0 END,
                bounced_count = bounced_count + CASE WHEN NEW.status = 'bounced' THEN 1 ELSE 0 END,
                complained_count = complained_count + CASE WHEN NEW.status = 'complained' THEN 1 ELSE 0 END,
                unsubscribed_count = unsubscribed_count + CASE WHEN NEW.status = 'unsubscribed' THEN 1 ELSE 0 END
            WHERE id = NEW.campaign_id;
            
            UPDATE notification_campaign_recipients
            SET 
                status = NEW.status,
                sent_at = NEW.sent_at,
                delivered_at = NEW.delivered_at,
                opened_at = NEW.opened_at,
                clicked_at = NEW.clicked_at,
                bounced_at = CASE WHEN NEW.status = 'bounced' THEN NEW.failed_at ELSE NULL END,
                complained_at = CASE WHEN NEW.status = 'complained' THEN NEW.failed_at ELSE NULL END,
                unsubscribed_at = CASE WHEN NEW.status = 'unsubscribed' THEN NEW.failed_at ELSE NULL END
            WHERE notification_id = NEW.id;
        END IF;
        
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for campaign stats
    op.execute("""
    CREATE TRIGGER update_campaign_statistics_trigger
        AFTER UPDATE OF status ON notifications
        FOR EACH ROW
        WHEN (OLD.status IS DISTINCT FROM NEW.status)
        EXECUTE FUNCTION update_campaign_statistics();
    """)
    
    # Create views
    logger.info("Creating views")
    
    # View for notification analytics
    op.execute("""
    CREATE OR REPLACE VIEW v_notification_analytics AS
    SELECT 
        DATE(created_at) as date,
        notification_type,
        channel,
        COUNT(*) as total,
        COUNT(CASE WHEN status = 'sent' THEN 1 END) as sent,
        COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered,
        COUNT(CASE WHEN status = 'opened' THEN 1 END) as opened,
        COUNT(CASE WHEN status = 'clicked' THEN 1 END) as clicked,
        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
        COUNT(CASE WHEN status = 'bounced' THEN 1 END) as bounced,
        AVG(EXTRACT(EPOCH FROM (delivered_at - sent_at))) as avg_delivery_time_seconds,
        AVG(EXTRACT(EPOCH FROM (opened_at - sent_at))) as avg_open_time_seconds
    FROM notifications
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY DATE(created_at), notification_type, channel
    ORDER BY date DESC;
    """)
    
    # View for user notification preferences summary
    op.execute("""
    CREATE OR REPLACE VIEW v_user_notification_preferences AS
    SELECT 
        u.id as user_id,
        u.email,
        u.phone,
        COUNT(np.id) as preferences_count,
        COUNT(CASE WHEN np.enabled = true THEN 1 END) as enabled_count,
        COUNT(CASE WHEN np.channel = 'email' AND np.enabled = true THEN 1 END) as email_enabled,
        COUNT(CASE WHEN np.channel = 'sms' AND np.enabled = true THEN 1 END) as sms_enabled,
        COUNT(CASE WHEN np.channel = 'push' AND np.enabled = true THEN 1 END) as push_enabled,
        COUNT(DISTINCT nd.id) as active_devices
    FROM users u
    LEFT JOIN notification_preferences np ON u.id = np.user_id
    LEFT JOIN notification_devices nd ON u.id = nd.user_id AND nd.is_active = true
    WHERE u.deleted_at IS NULL
    GROUP BY u.id, u.email, u.phone;
    """)
    
    # Create materialized view for notification performance
    op.execute("""
    CREATE MATERIALIZED VIEW mv_notification_performance AS
    SELECT 
        DATE_TRUNC('hour', created_at) as hour,
        channel,
        notification_type,
        COUNT(*) as volume,
        AVG(EXTRACT(EPOCH FROM (delivered_at - sent_at))) as avg_delivery_time,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (delivered_at - sent_at))) as p95_delivery_time,
        COUNT(CASE WHEN status = 'failed' THEN 1 END)::float / COUNT(*) * 100 as failure_rate,
        COUNT(CASE WHEN status = 'opened' THEN 1 END)::float / COUNT(*) * 100 as open_rate,
        COUNT(CASE WHEN status = 'clicked' THEN 1 END)::float / COUNT(*) * 100 as click_rate
    FROM notifications
    WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY DATE_TRUNC('hour', created_at), channel, notification_type
    ORDER BY hour DESC;
    """)
    
    # Create index on materialized view
    op.create_index('idx_mv_notification_hour', 'mv_notification_performance', ['hour'])
    
    # Insert system templates
    logger.info("Inserting notification templates")
    
    # Email templates
    templates = [
        # Reservation confirmation
        {
            'code': 'reservation_confirmation_email',
            'name': 'Reservation Confirmation Email',
            'type': 'reservation_confirmation',
            'channel': 'email',
            'template_type': 'email_html',
            'subject': 'Your Parking Reservation Confirmed - {{reservation_number}}',
            'preheader': 'Thank you for choosing our parking service',
            'content_html': '<!DOCTYPE html><html><body><h1>Reservation Confirmed</h1><p>Dear {{customer_name}},</p><p>Your parking reservation has been confirmed.</p><p><strong>Reservation Number:</strong> {{reservation_number}}</p><p><strong>Date:</strong> {{date}}</p><p><strong>Time:</strong> {{start_time}} - {{end_time}}</p><p><strong>Location:</strong> {{zone_name}}, Spot {{spot_number}}</p><p><strong>Total Amount:</strong> {{total_amount}} {{currency}}</p><p>Thank you for choosing our service!</p></body></html>',
            'content_text': 'Reservation Confirmed\n\nDear {{customer_name}},\n\nYour parking reservation has been confirmed.\n\nReservation Number: {{reservation_number}}\nDate: {{date}}\nTime: {{start_time}} - {{end_time}}\nLocation: {{zone_name}}, Spot {{spot_number}}\nTotal Amount: {{total_amount}} {{currency}}\n\nThank you for choosing our service!',
            'variables': ['customer_name', 'reservation_number', 'date', 'start_time', 'end_time', 'zone_name', 'spot_number', 'total_amount', 'currency'],
            'required_variables': ['reservation_number', 'start_time', 'end_time']
        },
        # Reservation reminder
        {
            'code': 'reservation_reminder_email',
            'name': 'Reservation Reminder Email',
            'type': 'reservation_reminder',
            'channel': 'email',
            'template_type': 'email_html',
            'subject': 'Reminder: Your Parking Reservation Tomorrow - {{reservation_number}}',
            'preheader': 'Your parking reservation is tomorrow',
            'content_html': '<!DOCTYPE html><html><body><h1>Reservation Reminder</h1><p>Dear {{customer_name}},</p><p>This is a reminder that you have a parking reservation tomorrow.</p><p><strong>Reservation Number:</strong> {{reservation_number}}</p><p><strong>Date:</strong> {{date}}</p><p><strong>Time:</strong> {{start_time}} - {{end_time}}</p><p><strong>Location:</strong> {{zone_name}}, Spot {{spot_number}}</p><p>Please arrive on time and have your QR code ready.</p><p>Thank you!</p></body></html>',
            'content_text': 'Reservation Reminder\n\nDear {{customer_name}},\n\nThis is a reminder that you have a parking reservation tomorrow.\n\nReservation Number: {{reservation_number}}\nDate: {{date}}\nTime: {{start_time}} - {{end_time}}\nLocation: {{zone_name}}, Spot {{spot_number}}\n\nPlease arrive on time and have your QR code ready.\n\nThank you!',
            'variables': ['customer_name', 'reservation_number', 'date', 'start_time', 'end_time', 'zone_name', 'spot_number'],
            'required_variables': ['reservation_number', 'start_time', 'end_time']
        },
        # Payment receipt
        {
            'code': 'payment_receipt_email',
            'name': 'Payment Receipt Email',
            'type': 'payment_receipt',
            'channel': 'email',
            'template_type': 'email_html',
            'subject': 'Payment Receipt - {{payment_number}}',
            'preheader': 'Thank you for your payment',
            'content_html': '<!DOCTYPE html><html><body><h1>Payment Receipt</h1><p>Dear {{customer_name}},</p><p>Thank you for your payment.</p><p><strong>Payment Number:</strong> {{payment_number}}</p><p><strong>Amount:</strong> {{amount}} {{currency}}</p><p><strong>Date:</strong> {{date}}</p><p><strong>Payment Method:</strong> {{payment_method}}</p><p><strong>Reservation:</strong> {{reservation_number}}</p><p>A receipt has been attached to this email.</p><p>Thank you for your business!</p></body></html>',
            'content_text': 'Payment Receipt\n\nDear {{customer_name}},\n\nThank you for your payment.\n\nPayment Number: {{payment_number}}\nAmount: {{amount}} {{currency}}\nDate: {{date}}\nPayment Method: {{payment_method}}\nReservation: {{reservation_number}}\n\nA receipt has been attached to this email.\n\nThank you for your business!',
            'variables': ['customer_name', 'payment_number', 'amount', 'currency', 'date', 'payment_method', 'reservation_number'],
            'required_variables': ['payment_number', 'amount']
        },
        # SMS templates
        {
            'code': 'check_in_success_sms',
            'name': 'Check-In Success SMS',
            'type': 'check_in_success',
            'channel': 'sms',
            'template_type': 'sms_text',
            'content_text': 'You have checked in at {{zone_name}}. Spot: {{spot_number}}. Duration: {{duration_hours}}h. Thank you!',
            'variables': ['zone_name', 'spot_number', 'duration_hours'],
            'required_variables': ['spot_number']
        },
        {
            'code': 'violation_issued_sms',
            'name': 'Violation Issued SMS',
            'type': 'violation_issued',
            'channel': 'sms',
            'template_type': 'sms_text',
            'content_text': 'Parking violation issued for vehicle {{license_plate}}. Amount: {{fine_amount}} {{currency}}. Please pay by {{due_date}}.',
            'variables': ['license_plate', 'fine_amount', 'currency', 'due_date'],
            'required_variables': ['fine_amount']
        },
        # Push notification templates
        {
            'code': 'spot_available_push',
            'name': 'Spot Available Push',
            'type': 'spot_available',
            'channel': 'push',
            'template_type': 'push_notification',
            'subject': 'Parking Spot Available!',
            'content_json': '{"body": "A {{spot_type}} spot is now available in {{zone_name}}.", "data": {"zone_id": "{{zone_id}}", "spot_type": "{{spot_type}}"}}',
            'variables': ['spot_type', 'zone_name', 'zone_id'],
            'required_variables': ['zone_name']
        }
    ]
    
    for template in templates:
        op.execute(f"""
        INSERT INTO {NOTIFICATION_TEMPLATES_TABLE} (
            id, code, name, notification_type, channel, template_type,
            subject, preheader, content_html, content_text, content_json,
            variables, required_variables, is_active, is_system, created_at, updated_at
        ) VALUES (
            gen_random_uuid(),
            '{template["code"]}',
            '{template["name"]}',
            '{template["type"]}',
            '{template["channel"]}',
            '{template["template_type"]}',
            '{template.get("subject", "")}',
            '{template.get("preheader", "")}',
            '{template.get("content_html", "")}',
            '{template.get("content_text", "")}',
            '{template.get("content_json", "{}")}'::jsonb,
            '{template.get("variables", [])}'::text[],
            '{template.get("required_variables", [])}'::text[],
            true, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        );
        """)
    
    # Insert default notification triggers
    logger.info("Inserting notification triggers")
    
    triggers = [
        # Reservation triggers
        {
            'name': 'Reservation Created - Email Confirmation',
            'trigger_event': 'reservation.created',
            'notification_type': 'reservation_confirmation',
            'channel': 'email',
            'template_code': 'reservation_confirmation_email',
            'delay_seconds': 0
        },
        {
            'name': 'Reservation Reminder - 24h Before',
            'trigger_event': 'reservation.reminder',
            'notification_type': 'reservation_reminder',
            'channel': 'email',
            'template_code': 'reservation_reminder_email',
            'delay_seconds': 86400  # 24 hours before
        },
        # Payment triggers
        {
            'name': 'Payment Received - Email Receipt',
            'trigger_event': 'payment.received',
            'notification_type': 'payment_receipt',
            'channel': 'email',
            'template_code': 'payment_receipt_email',
            'delay_seconds': 0
        },
        # Check-in/out triggers
        {
            'name': 'Check-In Success - SMS',
            'trigger_event': 'check_in.success',
            'notification_type': 'check_in_success',
            'channel': 'sms',
            'template_code': 'check_in_success_sms',
            'delay_seconds': 0
        },
        # Violation triggers
        {
            'name': 'Violation Issued - SMS',
            'trigger_event': 'violation.issued',
            'notification_type': 'violation_issued',
            'channel': 'sms',
            'template_code': 'violation_issued_sms',
            'delay_seconds': 0
        }
    ]
    
    for trigger in triggers:
        # Get template ID
        template_id = op.get_bind().execute(
            f"SELECT id FROM {NOTIFICATION_TEMPLATES_TABLE} WHERE code = '{trigger['template_code']}'"
        ).scalar()
        
        if template_id:
            op.execute(f"""
            INSERT INTO {NOTIFICATION_TRIGGERS_TABLE} (
                id, name, trigger_event, notification_type, channel,
                template_id, delay_seconds, is_active, created_at, updated_at
            ) VALUES (
                gen_random_uuid(),
                '{trigger['name']}',
                '{trigger['trigger_event']}',
                '{trigger['notification_type']}',
                '{trigger['channel']}',
                '{template_id}',
                {trigger['delay_seconds']},
                true,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            );
            """)
    
    # Create partitions for high-volume tables
    logger.info("Creating partitions for notification tables")
    
    # Create partitions for notifications (monthly for next 12 months)
    for i in range(12):
        month_date = datetime.now().replace(day=1) + timedelta(days=30*i)
        month_str = month_date.strftime('%Y_%m')
        next_month = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS notifications_{month_str} 
        PARTITION OF notifications
        FOR VALUES FROM ('{month_date.strftime('%Y-%m-%d')}') 
        TO ('{next_month.strftime('%Y-%m-%d')}');
        """)
        
        # Create partition for notification logs
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS notification_logs_{month_str} 
        PARTITION OF notification_logs
        FOR VALUES FROM ('{month_date.strftime('%Y-%m-%d')}') 
        TO ('{next_month.strftime('%Y-%m-%d')}');
        """)
    
    # Grant permissions
    if op.get_context().dialect.name == 'postgresql':
        op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;")
        op.execute("GRANT INSERT, UPDATE, DELETE ON notifications, notification_queue, notification_logs TO app_user;")
        op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;")
    
    logger.info(f"Migration {revision} completed successfully")


def downgrade() -> None:
    """
    Downgrade migration - removes notification system
    """
    logger.info(f"Starting downgrade of migration {revision}")
    
    # Drop triggers first
    logger.info("Dropping triggers")
    triggers_to_drop = [
        'generate_notification_number_trigger',
        'generate_batch_number_trigger',
        'queue_notification_trigger',
        'check_notification_suppression_trigger',
        'update_campaign_statistics_trigger'
    ]
    for trigger in triggers_to_drop:
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON notifications CASCADE;")
    
    # Drop functions
    logger.info("Dropping functions")
    functions_to_drop = [
        'generate_notification_number()',
        'generate_batch_number()',
        'queue_notification()',
        'check_notification_suppression()',
        'update_campaign_statistics()'
    ]
    for func in functions_to_drop:
        op.execute(f"DROP FUNCTION IF EXISTS {func} CASCADE;")
    
    # Drop views and materialized views
    logger.info("Dropping views")
    op.execute("DROP VIEW IF EXISTS v_notification_analytics CASCADE;")
    op.execute("DROP VIEW IF EXISTS v_user_notification_preferences CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_notification_performance CASCADE;")
    
    # Drop tables in reverse order
    tables_to_drop = [
        NOTIFICATION_TRIGGERS_TABLE,
        NOTIFICATION_RULES_TABLE,
        NOTIFICATION_SUPPRESSIONS_TABLE,
        NOTIFICATION_BATCHES_TABLE,
        NOTIFICATION_SCHEDULES_TABLE,
        NOTIFICATION_WEBHOOK_DELIVERIES_TABLE,
        NOTIFICATION_WEBHOOKS_TABLE,
        NOTIFICATION_SUBSCRIPTIONS_TABLE,
        NOTIFICATION_CAMPAIGN_RECIPIENTS_TABLE,
        NOTIFICATION_CAMPAIGNS_TABLE,
        NOTIFICATION_ATTACHMENTS_TABLE,
        NOTIFICATION_LOGS_TABLE,
        NOTIFICATION_QUEUE_TABLE,
        NOTIFICATIONS_TABLE,
        NOTIFICATION_DEVICES_TABLE,
        NOTIFICATION_PREFERENCES_TABLE,
        NOTIFICATION_TEMPLATES_TABLE,
    ]
    
    for table in tables_to_drop:
        logger.info(f"Dropping {table} table")
        op.drop_table(table)
    
    # Drop ENUM types
    if op.get_context().dialect.name == 'postgresql':
        enums_to_drop = [
            'notification_type', 'notification_channel', 'notification_status',
            'notification_priority', 'template_type', 'device_type',
            'subscription_tier', 'campaign_status', 'webhook_method',
            'frequency', 'suppression_reason'
        ]
        for enum in enums_to_drop:
            logger.info(f"Dropping {enum} enum")
            op.execute(f"DROP TYPE IF EXISTS {enum} CASCADE;")
    
    # Drop partitions
    logger.info("Dropping partitions")
    for i in range(12):
        month_date = datetime.now().replace(day=1) + timedelta(days=30*i)
        month_str = month_date.strftime('%Y_%m')
        op.execute(f"DROP TABLE IF EXISTS notifications_{month_str} CASCADE;")
        op.execute(f"DROP TABLE IF EXISTS notification_logs_{month_str} CASCADE;")
    
    logger.info(f"Downgrade of migration {revision} completed successfully")


def validate_notification_data() -> dict:
    """
    Validate notification data quality after migration
    """
    logger.info("Validating notification data quality")
    
    connection = op.get_bind()
    results = {}
    
    # Check for notifications stuck in queue
    result = connection.execute("""
        SELECT COUNT(*)
        FROM notification_queue
        WHERE scheduled_for < CURRENT_TIMESTAMP - INTERVAL '1 hour'
            AND locked_until IS NULL
    """)
    results['stuck_notifications'] = result.scalar()
    
    # Check for notifications without logs
    result = connection.execute("""
        SELECT COUNT(*)
        FROM notifications n
        LEFT JOIN notification_logs nl ON n.id = nl.notification_id
        WHERE nl.id IS NULL
            AND n.status != 'pending'
    """)
    results['notifications_without_logs'] = result.scalar()
    
    # Check for invalid template variables
    result = connection.execute("""
        SELECT COUNT(*)
        FROM notifications n
        JOIN notification_templates t ON n.template_id = t.id
        WHERE n.status = 'failed'
            AND n.failure_reason LIKE '%template%'
    """)
    results['template_variable_errors'] = result.scalar()
    
    # Check for orphaned campaign recipients
    result = connection.execute("""
        SELECT COUNT(*)
        FROM notification_campaign_recipients cr
        LEFT JOIN notification_campaigns c ON cr.campaign_id = c.id
        WHERE c.id IS NULL
    """)
    results['orphaned_campaign_recipients'] = result.scalar()
    
    logger.info(f"Validation results: {results}")
    return results


def post_upgrade_hook():
    """Hook to run after successful upgrade"""
    logger.info("Running post-upgrade hooks for notifications migration")
    
    # Validate the migration
    validation_results = validate_notification_data()
    
    # Refresh materialized view
    op.execute("REFRESH MATERIALIZED VIEW mv_notification_performance;")
    
    # Log any issues
    for key, value in validation_results.items():
        if value > 0:
            logger.warning(f"Validation issue - {key}: {value}")
    
    # Log summary statistics
    connection = op.get_bind()
    stats = connection.execute("""
        SELECT 
            COUNT(*) as total_templates,
            COUNT(DISTINCT notification_type) as notification_types,
            COUNT(DISTINCT channel) as channels,
            COUNT(CASE WHEN is_system THEN 1 END) as system_templates
        FROM notification_templates
        WHERE deleted_at IS NULL
    """).first()
    
    if stats:
        logger.info(f"Notification System Summary: {stats.total_templates} templates, "
                   f"{stats.notification_types} types, {stats.channels} channels")
    
    logger.info("Notifications system migration completed successfully")


# Register the post-upgrade hook
if hasattr(op, 'register_post_upgrade_hook'):
    op.register_post_upgrade_hook(post_upgrade_hook)


# Add table comments
def add_table_comments():
    """Add detailed comments to tables for documentation"""
    op.execute(f"""
    COMMENT ON TABLE {NOTIFICATIONS_TABLE} IS 'Core notifications table tracking all outgoing communications across multiple channels with delivery status and engagement metrics.';
    COMMENT ON TABLE {NOTIFICATION_TEMPLATES_TABLE} IS 'Reusable templates for different notification types with multi-channel and multi-language support.';
    COMMENT ON TABLE {NOTIFICATION_PREFERENCES_TABLE} IS 'User preferences for notification delivery including frequency, quiet hours, and channel selection.';
    COMMENT ON TABLE {NOTIFICATION_QUEUE_TABLE} IS 'Queue for scheduled and pending notifications with priority-based processing.';
    COMMENT ON TABLE {NOTIFICATION_LOGS_TABLE} IS 'Detailed audit trail of notification events including deliveries, opens, and clicks.';
    COMMENT ON TABLE {NOTIFICATION_ATTACHMENTS_TABLE} IS 'File attachments for notifications including receipts, invoices, and images.';
    COMMENT ON TABLE {NOTIFICATION_DEVICES_TABLE} IS 'Registered user devices for push notifications with platform-specific tokens.';
    COMMENT ON TABLE {NOTIFICATION_CAMPAIGNS_TABLE} IS 'Marketing and bulk notification campaigns with targeting and A/B testing.';
    COMMENT ON TABLE {NOTIFICATION_CAMPAIGN_RECIPIENTS_TABLE} IS 'Individual recipients of campaign notifications with engagement tracking.';
    COMMENT ON TABLE {NOTIFICATION_SUBSCRIPTIONS_TABLE} IS 'Newsletter and marketing subscription management with double opt-in.';
    COMMENT ON TABLE {NOTIFICATION_WEBHOOKS_TABLE} IS 'Webhook endpoints for external system notifications with retry logic.';
    COMMENT ON TABLE {NOTIFICATION_WEBHOOK_DELIVERIES_TABLE} IS 'Delivery attempts and responses for notification webhooks.';
    COMMENT ON TABLE {NOTIFICATION_SCHEDULES_TABLE} IS 'Scheduled notification jobs using cron expressions or intervals.';
    COMMENT ON TABLE {NOTIFICATION_BATCHES_TABLE} IS 'Batch processing groups for bulk notification sending.';
    COMMENT ON TABLE {NOTIFICATION_SUPPRESSIONS_TABLE} IS 'Suppressed recipients due to bounces, complaints, or unsubscribes.';
    COMMENT ON TABLE {NOTIFICATION_RULES_TABLE} IS 'Processing rules for throttling, filtering, and transforming notifications.';
    COMMENT ON TABLE {NOTIFICATION_TRIGGERS_TABLE} IS 'Automatic triggers for notifications based on system events.';
    """)