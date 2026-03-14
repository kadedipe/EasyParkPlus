"""
Initial database migration.

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, INET, JSON

# revision identifiers, used by Alembic.
revision: str = '001_initial_migration'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=False), primary_key=True, index=True),
        sa.Column('user_id', UUID(as_uuid=False), nullable=True, index=True),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('action', sa.Enum('CREATE', 'READ', 'UPDATE', 'DELETE', 
                                    'LOGIN', 'LOGOUT', 'FAILED_LOGIN',
                                    'PASSWORD_CHANGE', 'PASSWORD_RESET',
                                    'EMAIL_VERIFY', 'PHONE_VERIFY',
                                    'EXPORT', 'IMPORT', 'API_CALL',
                                    'WEBHOOK', 'SYSTEM',
                                    name='auditaction'), nullable=False, index=True),
        sa.Column('resource', sa.String(50), nullable=False, index=True),
        sa.Column('resource_id', sa.String(50), nullable=True, index=True),
        sa.Column('old_value', JSON, nullable=True),
        sa.Column('new_value', JSON, nullable=True),
        sa.Column('ip_address', INET, nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
        sa.Column('details', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime, nullable=False),
        
        # Foreign key constraint
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for common queries
    op.create_index('ix_audit_logs_user_action', 'audit_logs', ['user_id', 'action'])
    op.create_index('ix_audit_logs_resource_lookup', 'audit_logs', ['resource', 'resource_id'])
    op.create_index('ix_audit_logs_created_at_action', 'audit_logs', ['created_at', 'action'])
    op.create_index('ix_audit_logs_ip_address', 'audit_logs', ['ip_address'])
    
    # Create composite index for date range queries
    op.create_index('ix_audit_logs_date_range', 'audit_logs', ['created_at', 'user_id', 'action'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_audit_logs_date_range')
    op.drop_index('ix_audit_logs_ip_address')
    op.drop_index('ix_audit_logs_created_at_action')
    op.drop_index('ix_audit_logs_resource_lookup')
    op.drop_index('ix_audit_logs_user_action')
    
    # Drop table
    op.drop_table('audit_logs')
    
    # Drop enum type
    op.execute('DROP TYPE auditaction')