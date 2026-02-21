# parking-management/data/migrations/versions/1a2b3c4d5e6f_add_users_table.py

"""Add users table for parking management system

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2024-01-15 10:30:45.123456

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define table names
USERS_TABLE = 'users'
USER_ROLES_TABLE = 'user_roles'
USER_AUDIT_TABLE = 'user_audit_log'

# Define ENUM types for PostgreSQL
user_status_enum = sa.Enum('active', 'inactive', 'suspended', 'pending', name='user_status')
user_role_enum = sa.Enum('admin', 'manager', 'operator', 'viewer', 'auditor', name='user_role')


def upgrade() -> None:
    """
    Upgrade migration - creates users and related tables
    """
    logger.info(f"Starting migration {revision}: Add users table")
    
    # Create ENUM types first (PostgreSQL specific)
    if op.get_context().dialect.name == 'postgresql':
        user_status_enum.create(op.get_bind(), checkfirst=True)
        user_role_enum.create(op.get_bind(), checkfirst=True)
        logger.info("Created ENUM types")
    
    # Create users table
    logger.info("Creating users table")
    op.create_table(
        USERS_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100)),
        sa.Column('last_name', sa.String(100)),
        sa.Column('phone_number', sa.String(20)),
        sa.Column('department', sa.String(100)),
        sa.Column('employee_id', sa.String(50), unique=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('phone_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('two_factor_secret', sa.String(255)),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.Column('last_login_ip', sa.String(45)),  # IPv6 compatible
        sa.Column('login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('locked_until', sa.DateTime(timezone=True)),
        sa.Column('password_changed_at', sa.DateTime(timezone=True)),
        sa.Column('password_reset_token', sa.String(255), unique=True),
        sa.Column('password_reset_expires', sa.DateTime(timezone=True)),
        sa.Column('api_key', sa.String(255), unique=True),
        sa.Column('api_key_created_at', sa.DateTime(timezone=True)),
        sa.Column('api_key_expires_at', sa.DateTime(timezone=True)),
        sa.Column('preferences', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', postgresql.UUID(as_uuid=True)),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True)),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        
        # Indexes and constraints
        sa.Index('ix_users_username', 'username'),
        sa.Index('ix_users_email', 'email'),
        sa.Index('ix_users_employee_id', 'employee_id'),
        sa.Index('ix_users_status', 'status'),
        sa.Index('ix_users_created_at', 'created_at'),
        sa.Index('ix_users_deleted_at', 'deleted_at'),
        
        # Foreign key constraints (self-referential for created_by/updated_by)
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('Main users table for parking management system'),
    )
    
    # Create user_roles table (many-to-many relationship)
    logger.info("Creating user_roles table")
    op.create_table(
        USER_ROLES_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True)),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('revoked_by', postgresql.UUID(as_uuid=True)),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_user_roles_user_id', 'user_id'),
        sa.Index('ix_user_roles_role', 'role'),
        sa.Index('ix_user_roles_is_active', 'is_active'),
        sa.UniqueConstraint('user_id', 'role', name='uq_user_roles_user_role'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], ondelete='SET NULL'),
        
        # Table comments
        sa.Comment('User roles mapping table'),
    )
    
    # Create user_audit_log table for tracking user activities
    logger.info("Creating user_audit_log table")
    op.create_table(
        USER_AUDIT_TABLE,
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource', sa.String(100)),
        sa.Column('resource_id', sa.String(100)),
        sa.Column('changes', postgresql.JSONB),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('session_id', sa.String(255)),
        sa.Column('request_id', sa.String(255)),
        sa.Column('status', sa.String(20), nullable=False, server_default='success'),
        sa.Column('error_message', sa.Text),
        sa.Column('execution_time_ms', sa.Integer()),
        sa.Column('metadata', postgresql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        # Indexes
        sa.Index('ix_user_audit_user_id', 'user_id'),
        sa.Index('ix_user_audit_action', 'action'),
        sa.Index('ix_user_audit_created_at', 'created_at'),
        sa.Index('ix_user_audit_resource', 'resource', 'resource_id'),
        sa.Index('ix_user_audit_session_id', 'session_id'),
        sa.Index('ix_user_audit_request_id', 'request_id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        
        # Partition by month (PostgreSQL 10+)
        postgresql_partition_by='RANGE (created_at)',
        
        # Table comments
        sa.Comment('User audit log for tracking all user activities'),
    )
    
    # Create additional indexes for performance
    logger.info("Creating additional indexes")
    op.create_index('idx_users_lookup', USERS_TABLE, ['username', 'email', 'employee_id'])
    op.create_index('idx_users_auth', USERS_TABLE, ['email', 'password_hash'])
    op.create_index('idx_users_api_key', USERS_TABLE, ['api_key'], unique=True)
    op.create_index('idx_users_password_reset', USERS_TABLE, ['password_reset_token'], unique=True)
    
    # Create function for updating updated_at timestamp
    op.execute("""
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """)
    
    # Create trigger for users table
    op.execute("""
    CREATE TRIGGER update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Create function for auditing user changes
    op.execute("""
    CREATE OR REPLACE FUNCTION audit_user_changes()
    RETURNS TRIGGER AS $$
    BEGIN
        IF TG_OP = 'INSERT' THEN
            INSERT INTO user_audit_log (user_id, action, resource, changes, ip_address)
            VALUES (NEW.id, 'CREATE', 'user', row_to_json(NEW), current_setting('request.ip_address', true));
            RETURN NEW;
        ELSIF TG_OP = 'UPDATE' THEN
            INSERT INTO user_audit_log (user_id, action, resource, changes, ip_address)
            VALUES (NEW.id, 'UPDATE', 'user', 
                    jsonb_build_object('old', row_to_json(OLD), 'new', row_to_json(NEW)),
                    current_setting('request.ip_address', true));
            RETURN NEW;
        ELSIF TG_OP = 'DELETE' THEN
            INSERT INTO user_audit_log (user_id, action, resource, changes, ip_address)
            VALUES (OLD.id, 'DELETE', 'user', row_to_json(OLD), current_setting('request.ip_address', true));
            RETURN OLD;
        END IF;
        RETURN NULL;
    END;
    $$ language 'plpgsql';
    """)
    
    # Create audit trigger
    op.execute("""
    CREATE TRIGGER audit_users
        AFTER INSERT OR UPDATE OR DELETE ON users
        FOR EACH ROW
        EXECUTE FUNCTION audit_user_changes();
    """)
    
    # Insert default admin user
    logger.info("Inserting default admin user")
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Generate UUID for admin user
    admin_id = uuid.uuid4()
    
    # Insert admin user
    op.execute(f"""
    INSERT INTO users (
        id, username, email, password_hash, first_name, last_name,
        status, email_verified, role, created_at, updated_at
    ) VALUES (
        '{admin_id}',
        'admin',
        'admin@parking-management.com',
        '{pwd_context.hash("Admin@123")}',
        'System',
        'Administrator',
        'active',
        true,
        'admin',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    );
    """)
    
    # Assign admin role
    op.execute(f"""
    INSERT INTO user_roles (user_id, role, granted_by, granted_at)
    VALUES ('{admin_id}', 'admin', '{admin_id}', CURRENT_TIMESTAMP);
    """)
    
    # Create partitions for audit log (monthly for the next 12 months)
    logger.info("Creating monthly partitions for audit log")
    for i in range(12):
        month = datetime.now().replace(day=1) + pd.DateOffset(months=i)
        month_str = month.strftime('%Y_%m')
        next_month = (month + pd.DateOffset(months=1)).strftime('%Y-%m-%d')
        
        op.execute(f"""
        CREATE TABLE IF NOT EXISTS user_audit_log_{month_str} 
        PARTITION OF user_audit_log
        FOR VALUES FROM ('{month.strftime('%Y-%m-%d')}') TO ('{next_month}');
        """)
    
    # Create view for active users with roles
    op.execute("""
    CREATE OR REPLACE VIEW v_active_users AS
    SELECT 
        u.id,
        u.username,
        u.email,
        u.first_name,
        u.last_name,
        u.status,
        u.last_login_at,
        array_agg(ur.role) as roles
    FROM users u
    LEFT JOIN user_roles ur ON u.id = ur.user_id AND ur.is_active = true
    WHERE u.deleted_at IS NULL
    GROUP BY u.id, u.username, u.email, u.first_name, u.last_name, u.status, u.last_login_at;
    """)
    
    # Create materialized view for user statistics
    op.execute("""
    CREATE MATERIALIZED VIEW mv_user_statistics AS
    SELECT 
        COUNT(*) as total_users,
        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_users,
        COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive_users,
        COUNT(CASE WHEN status = 'suspended' THEN 1 END) as suspended_users,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_users,
        COUNT(CASE WHEN email_verified THEN 1 END) as email_verified,
        COUNT(CASE WHEN two_factor_enabled THEN 1 END) as two_factor_enabled,
        COUNT(DISTINCT department) as unique_departments,
        MIN(created_at) as first_user_created,
        MAX(created_at) as last_user_created,
        CURRENT_TIMESTAMP as refreshed_at
    FROM users
    WHERE deleted_at IS NULL;
    """)
    
    # Create unique index on materialized view
    op.create_index('idx_mv_user_statistics', 'mv_user_statistics', ['refreshed_at'], unique=True)
    
    # Create function to refresh materialized view
    op.execute("""
    CREATE OR REPLACE FUNCTION refresh_user_statistics()
    RETURNS TRIGGER AS $$
    BEGIN
        REFRESH MATERIALIZED VIEW CONCURRENTLY mv_user_statistics;
        RETURN NULL;
    END;
    $$ language 'plpgsql';
    """)
    
    # Create trigger to refresh statistics on user changes
    op.execute("""
    CREATE TRIGGER refresh_stats_on_user_change
        AFTER INSERT OR UPDATE OR DELETE ON users
        FOR EACH STATEMENT
        EXECUTE FUNCTION refresh_user_statistics();
    """)
    
    # Grant permissions (adjust based on your database setup)
    if op.get_context().dialect.name == 'postgresql':
        op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;")
        op.execute("GRANT INSERT, UPDATE, DELETE ON users, user_roles TO app_user;")
        op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;")
    
    logger.info(f"Migration {revision} completed successfully")


def downgrade() -> None:
    """
    Downgrade migration - removes users and related tables
    """
    logger.info(f"Starting downgrade of migration {revision}")
    
    # Drop triggers first
    logger.info("Dropping triggers")
    op.execute("DROP TRIGGER IF EXISTS update_users_updated_at ON users;")
    op.execute("DROP TRIGGER IF EXISTS audit_users ON users;")
    op.execute("DROP TRIGGER IF EXISTS refresh_stats_on_user_change ON users;")
    
    # Drop functions
    logger.info("Dropping functions")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS audit_user_changes() CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS refresh_user_statistics() CASCADE;")
    
    # Drop views and materialized views
    logger.info("Dropping views")
    op.execute("DROP VIEW IF EXISTS v_active_users CASCADE;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_user_statistics CASCADE;")
    
    # Drop tables in reverse order
    logger.info("Dropping user_audit_log table")
    op.drop_table(USER_AUDIT_TABLE)
    
    logger.info("Dropping user_roles table")
    op.drop_table(USER_ROLES_TABLE)
    
    logger.info("Dropping users table")
    op.drop_table(USERS_TABLE)
    
    # Drop ENUM types (PostgreSQL specific)
    if op.get_context().dialect.name == 'postgresql':
        logger.info("Dropping ENUM types")
        op.execute("DROP TYPE IF EXISTS user_status CASCADE;")
        op.execute("DROP TYPE IF EXISTS user_role CASCADE;")
    
    # Drop partitions
    logger.info("Dropping audit log partitions")
    for i in range(12):
        month = datetime.now().replace(day=1) + pd.DateOffset(months=i)
        month_str = month.strftime('%Y_%m')
        op.execute(f"DROP TABLE IF EXISTS user_audit_log_{month_str} CASCADE;")
    
    logger.info(f"Downgrade of migration {revision} completed successfully")


def validate_user_data() -> dict:
    """
    Validate user data quality after migration
    This can be called after upgrade to ensure data integrity
    """
    logger.info("Validating user data quality")
    
    connection = op.get_bind()
    results = {}
    
    # Check for duplicate emails
    result = connection.execute("""
        SELECT email, COUNT(*) as count
        FROM users
        GROUP BY email
        HAVING COUNT(*) > 1
    """)
    duplicates = result.fetchall()
    results['duplicate_emails'] = len(duplicates)
    
    # Check for users without roles
    result = connection.execute("""
        SELECT COUNT(*) 
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        WHERE ur.id IS NULL AND u.deleted_at IS NULL
    """)
    results['users_without_roles'] = result.scalar()
    
    # Check for expired roles
    result = connection.execute("""
        SELECT COUNT(*)
        FROM user_roles
        WHERE expires_at < CURRENT_TIMESTAMP AND is_active = true
    """)
    results['expired_roles'] = result.scalar()
    
    # Check for locked accounts
    result = connection.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE locked_until > CURRENT_TIMESTAMP
    """)
    results['locked_accounts'] = result.scalar()
    
    # Check password age
    result = connection.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE password_changed_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
        AND status = 'active'
    """)
    results['passwords_older_than_90_days'] = result.scalar()
    
    logger.info(f"Validation results: {results}")
    return results


def create_initial_users() -> None:
    """
    Create initial set of users for the system
    """
    logger.info("Creating initial users")
    
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Define initial users
    initial_users = [
        {
            'username': 'manager1',
            'email': 'manager@parking-management.com',
            'password': 'Manager@123',
            'first_name': 'Operations',
            'last_name': 'Manager',
            'role': 'manager',
            'department': 'Operations'
        },
        {
            'username': 'operator1',
            'email': 'operator@parking-management.com',
            'password': 'Operator@123',
            'first_name': 'Parking',
            'last_name': 'Operator',
            'role': 'operator',
            'department': 'Operations'
        },
        {
            'username': 'viewer1',
            'email': 'viewer@parking-management.com',
            'password': 'Viewer@123',
            'first_name': 'Report',
            'last_name': 'Viewer',
            'role': 'viewer',
            'department': 'Management'
        }
    ]
    
    for user_data in initial_users:
        user_id = uuid.uuid4()
        
        # Insert user
        op.execute(f"""
        INSERT INTO users (
            id, username, email, password_hash, first_name, last_name,
            status, email_verified, department, created_at, updated_at
        ) VALUES (
            '{user_id}',
            '{user_data["username"]}',
            '{user_data["email"]}',
            '{pwd_context.hash(user_data["password"])}',
            '{user_data["first_name"]}',
            '{user_data["last_name"]}',
            'active',
            true,
            '{user_data["department"]}',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        );
        """)
        
        # Assign role
        op.execute(f"""
        INSERT INTO user_roles (user_id, role, granted_by, granted_at)
        SELECT '{user_id}', '{user_data["role"]}', id, CURRENT_TIMESTAMP
        FROM users WHERE username = 'admin';
        """)
        
        logger.info(f"Created user: {user_data['username']}")


# Add data migration for existing vehicle data
def link_users_to_vehicles() -> None:
    """
    Link existing vehicles to users based on ownership or assignment
    This is an example of how to handle data migration
    """
    logger.info("Linking vehicles to users")
    
    # This assumes you have a vehicles table with owner_id or similar
    # You would need to adapt this based on your actual schema
    
    # Example: Assign vehicles to operators based on some logic
    op.execute("""
    UPDATE vehicles v
    SET owner_id = u.id
    FROM users u
    WHERE u.username = 'operator1'
    AND v.owner_id IS NULL
    AND v.status = 'active';
    """)


# Run data quality checks after migration
def run_post_migration_checks():
    """
    Run post-migration quality checks
    """
    logger.info("Running post-migration quality checks")
    
    validation_results = validate_user_data()
    
    # Check if any critical issues found
    critical_issues = []
    
    if validation_results.get('duplicate_emails', 0) > 0:
        critical_issues.append(f"Found {validation_results['duplicate_emails']} duplicate emails")
    
    if validation_results.get('users_without_roles', 0) > 0:
        critical_issues.append(f"Found {validation_results['users_without_roles']} users without roles")
    
    if critical_issues:
        logger.warning("Post-migration validation found issues:")
        for issue in critical_issues:
            logger.warning(f"  - {issue}")
    else:
        logger.info("All post-migration checks passed")


# You can add custom methods to be called after upgrade
def post_upgrade_hook():
    """Hook to run after successful upgrade"""
    logger.info("Running post-upgrade hooks")
    create_initial_users()
    link_users_to_vehicles()
    run_post_migration_checks()


# Register the post-upgrade hook to run automatically
# This will be called if you run migrations with --post-upgrade
if hasattr(op, 'register_post_upgrade_hook'):
    op.register_post_upgrade_hook(post_upgrade_hook)


# Add table comments for documentation
def add_table_comments():
    """Add detailed comments to tables for documentation"""
    op.execute(f"""
    COMMENT ON TABLE {USERS_TABLE} IS 'Stores all user accounts for the parking management system. Includes authentication, profile, and security information.';
    COMMENT ON TABLE {USER_ROLES_TABLE} IS 'Many-to-many relationship between users and roles. Supports role-based access control with expiration.';
    COMMENT ON TABLE {USER_AUDIT_TABLE} IS 'Audit trail for all user-related actions. Partitioned by month for performance.';
    """)