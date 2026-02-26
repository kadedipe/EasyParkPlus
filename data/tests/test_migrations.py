"""Tests for database migrations in the parking management system."""

import pytest
from datetime import datetime, timedelta
import os
import tempfile
import shutil
from pathlib import Path
import importlib.util
import sys
import sqlite3
from contextlib import contextmanager

# Import migration tools
try:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext
    from alembic import command
    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.schema import MetaData, Table, Column
except ImportError:
    pytest.skip("Alembic/SQLAlchemy not available - skipping migration tests", allow_module_level=True)


class TestMigrationBase:
    """Base class for migration tests."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        """Set up test environment before each test."""
        # Create temporary directory for migration files
        self.temp_dir = tmp_path / "migrations_test"
        self.temp_dir.mkdir()
        
        # Set up database paths
        self.db_path = self.temp_dir / "test.db"
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Create engine
        self.engine = create_engine(self.db_url)
        
        # Find migrations directory
        self.migrations_dir = self._find_migrations_dir()
        
        # Set up Alembic configuration
        self.alembic_cfg = self._create_alembic_config()
        
        yield
        
        # Clean up
        if hasattr(self, 'engine'):
            self.engine.dispose()
    
    def _find_migrations_dir(self):
        """Find the migrations directory in the project."""
        # Try common locations
        possible_paths = [
            Path.cwd() / "migrations",
            Path.cwd() / "alembic",
            Path.cwd() / "db" / "migrations",
            Path.cwd() / "database" / "migrations",
            Path(__file__).parent.parent.parent / "migrations",
            Path(__file__).parent.parent / "migrations",
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                return path
        
        # If not found, create a mock migrations directory for testing
        return self._create_mock_migrations()
    
    def _create_mock_migrations(self):
        """Create mock migration files for testing when real ones aren't available."""
        mock_dir = self.temp_dir / "mock_migrations"
        mock_dir.mkdir()
        
        # Create versions directory
        versions_dir = mock_dir / "versions"
        versions_dir.mkdir()
        
        # Create initial migration
        self._create_initial_migration(versions_dir)
        
        # Create second migration
        self._create_second_migration(versions_dir)
        
        # Create third migration
        self._create_third_migration(versions_dir)
        
        # Create env.py
        self._create_env_py(mock_dir)
        
        # Create script.py.mako
        self._create_script_template(mock_dir)
        
        return mock_dir
    
    def _create_initial_migration(self, versions_dir):
        """Create initial migration file."""
        migration_content = '''
"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create parking_spots table
    op.create_table(
        'parking_spots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('spot_number', sa.String(length=10), nullable=False),
        sa.Column('spot_type', sa.String(length=50), nullable=False, server_default='standard'),
        sa.Column('hourly_rate', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('spot_number')
    )
    
    # Create vehicles table
    op.create_table(
        'vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('license_plate', sa.String(length=20), nullable=False),
        sa.Column('vehicle_type', sa.String(length=50), nullable=False),
        sa.Column('is_ev', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('license_plate')
    )
    
    # Create reservations table
    op.create_table(
        'reservations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('spot_id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('confirmation_code', sa.String(length=20), nullable=False),
        sa.Column('reservation_type', sa.String(length=50), nullable=False, server_default='standard'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('payment_status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('payment_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('checked_in_at', sa.DateTime(), nullable=True),
        sa.Column('checked_out_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['spot_id'], ['parking_spots.id'], ),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('confirmation_code')
    )
    
    # Create indexes
    op.create_index('ix_reservations_user_id', 'reservations', ['user_id'])
    op.create_index('ix_reservations_spot_id', 'reservations', ['spot_id'])
    op.create_index('ix_reservations_status', 'reservations', ['status'])
    op.create_index('ix_reservations_start_time', 'reservations', ['start_time'])

def downgrade():
    op.drop_table('reservations')
    op.drop_table('vehicles')
    op.drop_table('parking_spots')
    op.drop_table('users')
'''
        
        migration_file = versions_dir / "001_initial.py"
        migration_file.write_text(migration_content)
    
    def _create_second_migration(self, versions_dir):
        """Create second migration file (add waitlist)."""
        migration_content = '''
"""Add waitlist table

Revision ID: 002_add_waitlist
Revises: 001_initial
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '002_add_waitlist'
down_revision = '001_initial'
branch_labels = None
depends_on = None

def upgrade():
    # Create waitlist table
    op.create_table(
        'waitlist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('spot_id', sa.Integer(), nullable=False),
        sa.Column('date_from', sa.DateTime(), nullable=False),
        sa.Column('date_to', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('notified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['spot_id'], ['parking_spots.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_waitlist_spot_date', 'waitlist', ['spot_id', 'date_from'])
    op.create_index('ix_waitlist_status', 'waitlist', ['status'])

def downgrade():
    op.drop_table('waitlist')
'''
        
        migration_file = versions_dir / "002_add_waitlist.py"
        migration_file.write_text(migration_content)
    
    def _create_third_migration(self, versions_dir):
        """Create third migration file (add metadata column)."""
        migration_content = '''
"""Add metadata column to reservations

Revision ID: 003_add_metadata
Revises: 002_add_waitlist
Create Date: 2024-02-01 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '003_add_metadata'
down_revision = '002_add_waitlist'
branch_labels = None
depends_on = None

def upgrade():
    # Add metadata column to reservations
    op.add_column('reservations', sa.Column('metadata', sa.JSON(), nullable=True))
    
    # Add metadata column to users
    op.add_column('users', sa.Column('metadata', sa.JSON(), nullable=True))
    
    # Add cancellation_reason to reservations
    op.add_column('reservations', sa.Column('cancellation_reason', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('reservations', 'cancellation_reason')
    op.drop_column('users', 'metadata')
    op.drop_column('reservations', 'metadata')
'''
        
        migration_file = versions_dir / "003_add_metadata.py"
        migration_file.write_text(migration_content)
    
    def _create_env_py(self, migrations_dir):
        """Create env.py for Alembic."""
        env_content = '''
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here
# for 'autogenerate' support
# target_metadata = None

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=None
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
        
        env_file = migrations_dir / "env.py"
        env_file.write_text(env_content)
    
    def _create_script_template(self, migrations_dir):
        """Create script.py.mako template."""
        template_content = '''
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade():
    ${upgrades if upgrades else "pass"}

def downgrade():
    ${downgrades if downgrades else "pass"}
'''
        
        template_file = migrations_dir / "script.py.mako"
        template_file.write_text(template_content)
    
    def _create_alembic_config(self):
        """Create Alembic configuration for testing."""
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", str(self.migrations_dir))
        alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)
        return alembic_cfg


class TestMigrationHistory(TestMigrationBase):
    """Tests for migration history and version tracking."""
    
    def test_migration_history_exists(self):
        """Test that migration history table exists after migrations."""
        # Run migrations
        command.upgrade(self.alembic_cfg, "head")
        
        # Check that alembic_version table exists
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        
        assert 'alembic_version' in tables
    
    def test_current_migration_version(self):
        """Test getting current migration version."""
        # Run migrations
        command.upgrade(self.alembic_cfg, "head")
        
        # Get current version
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
        
        assert version is not None
        assert version in ['001_initial', '002_add_waitlist', '003_add_metadata']
    
    def test_migration_downgrade_upgrade_cycle(self):
        """Test downgrading and upgrading through all versions."""
        # Upgrade to head
        command.upgrade(self.alembic_cfg, "head")
        
        # Get head version
        script = ScriptDirectory.from_config(self.alembic_cfg)
        head = script.get_current_head()
        
        # Downgrade to base
        command.downgrade(self.alembic_cfg, "base")
        
        # Check that alembic_version table is empty or doesn't exist
        inspector = inspect(self.engine)
        if 'alembic_version' in inspector.get_table_names():
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM alembic_version"))
                count = result.scalar()
                assert count == 0
        
        # Upgrade back to head
        command.upgrade(self.alembic_cfg, "head")
        
        # Check version is back to head
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            assert version == head


class TestSchemaEvolution(TestMigrationBase):
    """Tests for schema evolution across migrations."""
    
    def test_initial_schema(self):
        """Test that initial migration creates correct schema."""
        # Upgrade to first migration
        command.upgrade(self.alembic_cfg, "001_initial")
        
        # Get database inspector
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        
        # Check core tables exist
        expected_tables = ['users', 'parking_spots', 'vehicles', 'reservations']
        for table in expected_tables:
            assert table in tables
        
        # Check users table columns
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        expected_user_columns = ['id', 'email', 'full_name', 'phone', 'created_at', 'updated_at']
        for col in expected_user_columns:
            assert col in user_columns
        
        # Check reservations table columns
        reservation_columns = [col['name'] for col in inspector.get_columns('reservations')]
        expected_reservation_columns = [
            'id', 'user_id', 'spot_id', 'vehicle_id', 'confirmation_code',
            'reservation_type', 'status', 'start_time', 'end_time', 'total_amount',
            'payment_status', 'payment_id', 'created_at', 'confirmed_at',
            'checked_in_at', 'checked_out_at', 'completed_at', 'cancelled_at'
        ]
        for col in expected_reservation_columns:
            assert col in reservation_columns
        
        # Check indexes
        indexes = inspector.get_indexes('reservations')
        index_names = [idx['name'] for idx in indexes]
        expected_indexes = [
            'ix_reservations_user_id',
            'ix_reservations_spot_id',
            'ix_reservations_status',
            'ix_reservations_start_time'
        ]
        for idx in expected_indexes:
            assert idx in index_names
    
    def test_second_migration_adds_waitlist(self):
        """Test that second migration adds waitlist table."""
        # Upgrade to second migration
        command.upgrade(self.alembic_cfg, "002_add_waitlist")
        
        # Check waitlist table exists
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        assert 'waitlist' in tables
        
        # Check waitlist columns
        waitlist_columns = [col['name'] for col in inspector.get_columns('waitlist')]
        expected_columns = [
            'id', 'user_id', 'spot_id', 'date_from', 'date_to',
            'status', 'position', 'notified_at', 'created_at'
        ]
        for col in expected_columns:
            assert col in waitlist_columns
        
        # Check indexes
        indexes = inspector.get_indexes('waitlist')
        index_names = [idx['name'] for idx in indexes]
        expected_indexes = ['ix_waitlist_spot_date', 'ix_waitlist_status']
        for idx in expected_indexes:
            assert idx in index_names
    
    def test_third_migration_adds_metadata(self):
        """Test that third migration adds metadata columns."""
        # Upgrade to third migration
        command.upgrade(self.alembic_cfg, "003_add_metadata")
        
        inspector = inspect(self.engine)
        
        # Check reservations table for new columns
        reservation_columns = [col['name'] for col in inspector.get_columns('reservations')]
        assert 'metadata' in reservation_columns
        assert 'cancellation_reason' in reservation_columns
        
        # Check users table for new columns
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        assert 'metadata' in user_columns


class TestDataPreservation(TestMigrationBase):
    """Tests for data preservation during migrations."""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Set up test data before migration tests."""
        # Upgrade to initial migration
        command.upgrade(self.alembic_cfg, "001_initial")
        
        # Insert test data
        with self.engine.connect() as conn:
            # Insert user
            conn.execute(
                text("""
                    INSERT INTO users (id, email, full_name, phone)
                    VALUES (1, 'test@example.com', 'Test User', '+1234567890')
                """)
            )
            
            # Insert parking spot
            conn.execute(
                text("""
                    INSERT INTO parking_spots (id, spot_number, spot_type, hourly_rate)
                    VALUES (1, 'A1', 'standard', 3.00)
                """)
            )
            
            # Insert vehicle
            conn.execute(
                text("""
                    INSERT INTO vehicles (id, user_id, license_plate, vehicle_type, is_ev)
                    VALUES (1, 1, 'ABC-123', 'sedan', 0)
                """)
            )
            
            # Insert reservation
            conn.execute(
                text("""
                    INSERT INTO reservations (
                        id, user_id, spot_id, vehicle_id, confirmation_code,
                        reservation_type, status, start_time, end_time, total_amount
                    ) VALUES (
                        1, 1, 1, 1, 'TEST-001',
                        'standard', 'confirmed', 
                        '2024-01-20 09:00:00', '2024-01-20 17:00:00',
                        24.00
                    )
                """)
            )
            
            conn.commit()
        
        yield
        
        # Clean up
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM reservations"))
            conn.execute(text("DELETE FROM vehicles"))
            conn.execute(text("DELETE FROM parking_spots"))
            conn.execute(text("DELETE FROM users"))
            conn.commit()
    
    def test_data_preserved_after_upgrade(self):
        """Test that data is preserved after upgrading to newer migration."""
        # Upgrade to second migration
        command.upgrade(self.alembic_cfg, "002_add_waitlist")
        
        # Check that data still exists
        with self.engine.connect() as conn:
            # Check user
            result = conn.execute(text("SELECT COUNT(*) FROM users WHERE id = 1"))
            assert result.scalar() == 1
            
            # Check spot
            result = conn.execute(text("SELECT COUNT(*) FROM parking_spots WHERE id = 1"))
            assert result.scalar() == 1
            
            # Check vehicle
            result = conn.execute(text("SELECT COUNT(*) FROM vehicles WHERE id = 1"))
            assert result.scalar() == 1
            
            # Check reservation
            result = conn.execute(text("SELECT COUNT(*) FROM reservations WHERE id = 1"))
            assert result.scalar() == 1
    
    def test_data_preserved_after_downgrade(self):
        """Test that data is preserved after downgrading."""
        # Upgrade to latest
        command.upgrade(self.alembic_cfg, "head")
        
        # Downgrade to initial
        command.downgrade(self.alembic_cfg, "001_initial")
        
        # Check that data still exists
        with self.engine.connect() as conn:
            # Check user
            result = conn.execute(text("SELECT COUNT(*) FROM users WHERE id = 1"))
            assert result.scalar() == 1
            
            # Check reservation
            result = conn.execute(text("SELECT COUNT(*) FROM reservations WHERE id = 1"))
            assert result.scalar() == 1
    
    def test_new_columns_have_default_values(self):
        """Test that new columns have appropriate default values."""
        # Upgrade to third migration
        command.upgrade(self.alembic_cfg, "003_add_metadata")
        
        # Check existing records have NULL in new columns
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT metadata, cancellation_reason FROM reservations WHERE id = 1")
            )
            row = result.fetchone()
            assert row[0] is None  # metadata
            assert row[1] is None  # cancellation_reason


class TestMigrationRollback(TestMigrationBase):
    """Tests for migration rollback scenarios."""
    
    def test_rollback_from_head_to_base(self):
        """Test rolling back from head to base."""
        # Upgrade to head
        command.upgrade(self.alembic_cfg, "head")
        
        # Get head version
        script = ScriptDirectory.from_config(self.alembic_cfg)
        head = script.get_current_head()
        
        # Downgrade to base
        command.downgrade(self.alembic_cfg, "base")
        
        # Check that all tables from head are gone
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        
        # Base should only have alembic_version table (or none)
        if 'alembic_version' in tables:
            assert len(tables) == 1
        else:
            assert len(tables) == 0
    
    def test_rollback_one_step(self):
        """Test rolling back one migration at a time."""
        # Upgrade to head
        command.upgrade(self.alembic_cfg, "head")
        
        # Get current version
        script = ScriptDirectory.from_config(self.alembic_cfg)
        head = script.get_current_head()
        
        # Downgrade one step
        command.downgrade(self.alembic_cfg, "-1")
        
        # Check version
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
        
        # Version should be the previous one
        assert version != head
        assert version == '002_add_waitlist'
        
        # Check that metadata column is gone
        inspector = inspect(self.engine)
        reservation_columns = [col['name'] for col in inspector.get_columns('reservations')]
        assert 'metadata' not in reservation_columns
        assert 'cancellation_reason' not in reservation_columns
    
    def test_rollback_with_data_in_new_columns(self):
        """Test rolling back when new columns contain data."""
        # Upgrade to third migration
        command.upgrade(self.alembic_cfg, "003_add_metadata")
        
        # Insert data with metadata
        with self.engine.connect() as conn:
            # Insert user with metadata
            conn.execute(
                text("""
                    INSERT INTO users (id, email, full_name, metadata)
                    VALUES (2, 'metadata@example.com', 'Metadata User', '{"preferences": {"notifications": true}}')
                """)
            )
            
            # Insert reservation with metadata
            conn.execute(
                text("""
                    INSERT INTO reservations (
                        id, user_id, spot_id, vehicle_id, confirmation_code,
                        reservation_type, status, start_time, end_time, total_amount,
                        metadata, cancellation_reason
                    ) VALUES (
                        2, 1, 1, 1, 'TEST-002',
                        'standard', 'confirmed', 
                        '2024-02-01 09:00:00', '2024-02-01 17:00:00',
                        24.00,
                        '{"source": "mobile"}',
                        'Test reason'
                    )
                """)
            )
            conn.commit()
        
        # Downgrade to second migration (should remove metadata columns)
        command.downgrade(self.alembic_cfg, "002_add_waitlist")
        
        # Check that metadata columns are gone
        inspector = inspect(self.engine)
        reservation_columns = [col['name'] for col in inspector.get_columns('reservations')]
        assert 'metadata' not in reservation_columns
        assert 'cancellation_reason' not in reservation_columns
        
        # Check that data in other columns is preserved
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM reservations WHERE id = 2")
            )
            assert result.scalar() == 1


class TestMigrationConstraints(TestMigrationBase):
    """Tests for database constraints across migrations."""
    
    def test_foreign_key_constraints(self):
        """Test that foreign key constraints are properly maintained."""
        # Upgrade to head
        command.upgrade(self.alembic_cfg, "head")
        
        inspector = inspect(self.engine)
        
        # Check foreign keys on reservations
        if self.engine.dialect.name == 'sqlite':
            # SQLite requires special handling for FK inspection
            with self.engine.connect() as conn:
                result = conn.execute(text("PRAGMA foreign_key_list(reservations)"))
                fks = result.fetchall()
                assert len(fks) >= 3  # Should have at least 3 foreign keys
        else:
            # For PostgreSQL/MySQL
            fks = inspector.get_foreign_keys('reservations')
            assert len(fks) >= 3
            
            # Check specific foreign keys
            fk_columns = [fk['constrained_columns'] for fk in fks]
            assert ['user_id'] in fk_columns
            assert ['spot_id'] in fk_columns
            assert ['vehicle_id'] in fk_columns
    
    def test_unique_constraints(self):
        """Test that unique constraints are properly maintained."""
        # Upgrade to head
        command.upgrade(self.alembic_cfg, "head")
        
        inspector = inspect(self.engine)
        
        # Check unique constraints on users
        unique_constraints = inspector.get_unique_constraints('users')
        unique_columns = []
        for constraint in unique_constraints:
            unique_columns.extend(constraint['column_names'])
        
        assert 'email' in unique_columns
        
        # Check unique constraint on parking_spots
        unique_constraints = inspector.get_unique_constraints('parking_spots')
        unique_columns = []
        for constraint in unique_constraints:
            unique_columns.extend(constraint['column_names'])
        
        assert 'spot_number' in unique_columns
        
        # Check unique constraint on reservations
        unique_constraints = inspector.get_unique_constraints('reservations')
        unique_columns = []
        for constraint in unique_constraints:
            unique_columns.extend(constraint['column_names'])
        
        assert 'confirmation_code' in unique_columns
    
    def test_not_null_constraints(self):
        """Test that NOT NULL constraints are properly applied."""
        # Upgrade to head
        command.upgrade(self.alembic_cfg, "head")
        
        inspector = inspect(self.engine)
        
        # Check NOT NULL constraints on users
        user_columns = inspector.get_columns('users')
        for col in user_columns:
            if col['name'] in ['id', 'email', 'full_name']:
                assert not col['nullable']
        
        # Check NOT NULL constraints on reservations
        reservation_columns = inspector.get_columns('reservations')
        not_null_columns = ['id', 'user_id', 'spot_id', 'vehicle_id', 
                           'confirmation_code', 'start_time', 'end_time', 'total_amount']
        for col in reservation_columns:
            if col['name'] in not_null_columns:
                assert not col['nullable']


class TestMigrationPerformance(TestMigrationBase):
    """Tests for migration performance on large datasets."""
    
    @pytest.fixture
    def large_dataset(self):
        """Create a large dataset for performance testing."""
        # Upgrade to initial migration
        command.upgrade(self.alembic_cfg, "001_initial")
        
        # Insert large amount of data
        with self.engine.connect() as conn:
            # Insert users
            for i in range(1, 101):
                conn.execute(
                    text(f"""
                        INSERT INTO users (id, email, full_name, phone)
                        VALUES ({i}, 'user{i}@example.com', 'User {i}', '+123456789{i}')
                    """)
                )
            
            # Insert parking spots
            for i in range(1, 51):
                conn.execute(
                    text(f"""
                        INSERT INTO parking_spots (id, spot_number, spot_type, hourly_rate)
                        VALUES ({i}, 'A{i}', 'standard', 3.00)
                    """)
                )
            
            # Insert vehicles
            for i in range(1, 101):
                conn.execute(
                    text(f"""
                        INSERT INTO vehicles (id, user_id, license_plate, vehicle_type)
                        VALUES ({i}, {i}, 'ABC-{i:03d}', 'sedan')
                    """)
                )
            
            # Insert reservations (1000 reservations)
            for i in range(1, 1001):
                user_id = (i % 100) + 1
                spot_id = (i % 50) + 1
                vehicle_id = (i % 100) + 1
                conn.execute(
                    text(f"""
                        INSERT INTO reservations (
                            id, user_id, spot_id, vehicle_id, confirmation_code,
                            reservation_type, status, start_time, end_time, total_amount
                        ) VALUES (
                            {i}, {user_id}, {spot_id}, {vehicle_id}, 'PERF-{i:04d}',
                            'standard', 'completed', 
                            '2024-01-{((i-1)%28)+1:02d} 09:00:00', 
                            '2024-01-{((i-1)%28)+1:02d} 17:00:00',
                            24.00
                        )
                    """)
                )
            
            conn.commit()
        
        yield
        
        # Clean up
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM reservations"))
            conn.execute(text("DELETE FROM vehicles"))
            conn.execute(text("DELETE FROM parking_spots"))
            conn.execute(text("DELETE FROM users"))
            conn.commit()
    
    def test_migration_time_with_large_dataset(self, large_dataset):
        """Test migration time with large dataset."""
        import time
        
        # Time the upgrade to second migration
        start_time = time.time()
        command.upgrade(self.alembic_cfg, "002_add_waitlist")
        upgrade_time = time.time() - start_time
        
        # Time the downgrade
        start_time = time.time()
        command.downgrade(self.alembic_cfg, "001_initial")
        downgrade_time = time.time() - start_time
        
        # Log performance metrics
        print(f"\nUpgrade time with 1000+ records: {upgrade_time:.2f} seconds")
        print(f"Downgrade time with 1000+ records: {downgrade_time:.2f} seconds")
        
        # Assert reasonable performance (adjust thresholds as needed)
        assert upgrade_time < 10  # Should complete in under 10 seconds
        assert downgrade_time < 10
    
    def test_index_creation_performance(self, large_dataset):
        """Test index creation performance on large dataset."""
        import time
        
        # Drop indexes if they exist
        with self.engine.connect() as conn:
            try:
                conn.execute(text("DROP INDEX ix_reservations_user_id"))
                conn.execute(text("DROP INDEX ix_reservations_spot_id"))
                conn.execute(text("DROP INDEX ix_reservations_status"))
                conn.execute(text("DROP INDEX ix_reservations_start_time"))
                conn.commit()
            except:
                conn.rollback()
        
        # Time index creation
        start_time = time.time()
        
        with self.engine.connect() as conn:
            conn.execute(
                text("CREATE INDEX ix_reservations_user_id ON reservations(user_id)")
            )
            conn.execute(
                text("CREATE INDEX ix_reservations_spot_id ON reservations(spot_id)")
            )
            conn.execute(
                text("CREATE INDEX ix_reservations_status ON reservations(status)")
            )
            conn.execute(
                text("CREATE INDEX ix_reservations_start_time ON reservations(start_time)")
            )
            conn.commit()
        
        index_time = time.time() - start_time
        print(f"\nIndex creation time with 1000+ records: {index_time:.2f} seconds")
        
        assert index_time < 5  # Should complete in under 5 seconds


class TestMigrationIdempotency(TestMigrationBase):
    """Tests for migration idempotency."""
    
    def test_upgrade_idempotency(self):
        """Test that running upgrade multiple times is safe."""
        # Run upgrade first time
        command.upgrade(self.alembic_cfg, "head")
        
        # Get schema state
        inspector1 = inspect(self.engine)
        tables1 = set(inspector1.get_table_names())
        
        # Run upgrade again
        command.upgrade(self.alembic_cfg, "head")
        
        # Get schema state again
        inspector2 = inspect(self.engine)
        tables2 = set(inspector2.get_table_names())
        
        # Schema should be identical
        assert tables1 == tables2
    
    def test_downgrade_idempotency(self):
        """Test that running downgrade multiple times is safe."""
        # Upgrade to head
        command.upgrade(self.alembic_cfg, "head")
        
        # Downgrade to base
        command.downgrade(self.alembic_cfg, "base")
        
        # Get schema state
        inspector1 = inspect(self.engine)
        tables1 = set(inspector1.get_table_names())
        
        # Try to downgrade again (should do nothing)
        command.downgrade(self.alembic_cfg, "base")
        
        # Get schema state again
        inspector2 = inspect(self.engine)
        tables2 = set(inspector2.get_table_names())
        
        # Schema should be identical
        assert tables1 == tables2


class TestMigrationBranching(TestMigrationBase):
    """Tests for migration branching and merging scenarios."""
    
    def test_create_branch_migration(self):
        """Test creating and applying a branch migration."""
        # Create a branch migration
        versions_dir = self.migrations_dir / "versions"
        branch_content = '''
"""Branch migration for new feature

Revision ID: 004_branch_feature
Revises: 003_add_metadata
Create Date: 2024-03-01 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004_branch_feature'
down_revision = '003_add_metadata'
branch_labels = ('feature_branch',)
depends_on = None

def upgrade():
    # Create new feature table
    op.create_table(
        'loyalty_points',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tier', sa.String(length=50), nullable=False, server_default='bronze'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('loyalty_points')
'''
        
        branch_file = versions_dir / "004_branch_feature.py"
        branch_file.write_text(branch_content)
        
        # Apply branch migration
        command.upgrade(self.alembic_cfg, "004_branch_feature")
        
        # Check that branch table exists
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        assert 'loyalty_points' in tables
        
        # Check branch label
        script = ScriptDirectory.from_config(self.alembic_cfg)
        revision = script.get_revision('004_branch_feature')
        assert revision.branch_labels == {'feature_branch'}
    
    def test_merge_branches(self):
        """Test merging two branches."""
        # Create first branch
        versions_dir = self.migrations_dir / "versions"
        branch1_content = '''
"""First branch

Revision ID: 004_branch1
Revises: 003_add_metadata
Create Date: 2024-03-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004_branch1'
down_revision = '003_add_metadata'
branch_labels = ('branch1',)
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('branch1_data', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('users', 'branch1_data')
'''
        
        branch1_file = versions_dir / "004_branch1.py"
        branch1_file.write_text(branch1_content)
        
        # Create second branch
        branch2_content = '''
"""Second branch

Revision ID: 004_branch2
Revises: 003_add_metadata
Create Date: 2024-03-01 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '004_branch2'
down_revision = '003_add_metadata'
branch_labels = ('branch2',)
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('branch2_data', sa.Integer(), nullable=True))

def downgrade():
    op.drop_column('users', 'branch2_data')
'''
        
        branch2_file = versions_dir / "004_branch2.py"
        branch2_file.write_text(branch2_content)
        
        # Create merge migration
        merge_content = '''
"""Merge branches

Revision ID: 005_merge_branches
Revises: 004_branch1, 004_branch2
Create Date: 2024-03-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '005_merge_branches'
down_revision = ('004_branch1', '004_branch2')
branch_labels = None
depends_on = None

def upgrade():
    # Merge doesn't need any operations
    pass

def downgrade():
    # Merge doesn't need any operations
    pass
'''
        
        merge_file = versions_dir / "005_merge_branches.py"
        merge_file.write_text(merge_content)
        
        # Apply merge
        command.upgrade(self.alembic_cfg, "005_merge_branches")
        
        # Check that both branches were applied
        inspector = inspect(self.engine)
        user_columns = [col['name'] for col in inspector.get_columns('users')]
        assert 'branch1_data' in user_columns
        assert 'branch2_data' in user_columns


class TestMigrationDowngrade(TestMigrationBase):
    """Tests for specific downgrade scenarios."""
    
    def test_downgrade_with_complex_schema_changes(self):
        """Test downgrading with complex schema changes."""
        # Upgrade to head
        command.upgrade(self.alembic_cfg, "head")
        
        # Insert data
        with self.engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO users (id, email, full_name)
                    VALUES (100, 'complex@example.com', 'Complex User')
                """)
            )
            conn.commit()
        
        # Downgrade one step
        command.downgrade(self.alembic_cfg, "002_add_waitlist")
        
        # Check that user still exists
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM users WHERE id = 100")
            )
            assert result.scalar() == 1
    
    def test_downgrade_below_initial(self):
        """Test attempting to downgrade below initial migration."""
        # Upgrade to head
        command.upgrade(self.alembic_cfg, "head")
        
        # Downgrade to base
        command.downgrade(self.alembic_cfg, "base")
        
        # Attempt to downgrade further (should fail gracefully)
        with pytest.raises(Exception) as exc_info:
            command.downgrade(self.alembic_cfg, "base-1")
        
        assert "Can't locate revision" in str(exc_info.value)
    
    def test_downgrade_nonexistent_revision(self):
        """Test downgrading to a nonexistent revision."""
        with pytest.raises(Exception) as exc_info:
            command.downgrade(self.alembic_cfg, "nonexistent_revision")
        
        assert "Can't locate revision" in str(exc_info.value)


class TestMigrationEnvironment(TestMigrationBase):
    """Tests for migration environment and configuration."""
    
    def test_alembic_configuration(self):
        """Test Alembic configuration loading."""
        assert self.alembic_cfg.get_main_option("script_location") == str(self.migrations_dir)
        assert self.alembic_cfg.get_main_option("sqlalchemy.url") == self.db_url
    
    def test_migration_script_detection(self):
        """Test that migration scripts are properly detected."""
        script = ScriptDirectory.from_config(self.alembic_cfg)
        
        # Get all revisions
        revisions = list(script.walk_revisions())
        
        # Should have at least 3 revisions
        assert len(revisions) >= 3
        
        # Check revision order
        revision_ids = [rev.revision for rev in revisions]
        assert '001_initial' in revision_ids
        assert '002_add_waitlist' in revision_ids
        assert '003_add_metadata' in revision_ids
    
    def test_current_revision_detection(self):
        """Test detection of current database revision."""
        # No migrations applied yet
        script = ScriptDirectory.from_config(self.alembic_cfg)
        context = MigrationContext.configure(self.engine.connect())
        current_rev = context.get_current_revision()
        assert current_rev is None
        
        # Apply migration
        command.upgrade(self.alembic_cfg, "head")
        
        # Check current revision
        context = MigrationContext.configure(self.engine.connect())
        current_rev = context.get_current_revision()
        assert current_rev is not None
        assert current_rev in ['001_initial', '002_add_waitlist', '003_add_metadata']


class TestMigrationSQLiteSpecific(TestMigrationBase):
    """Tests specific to SQLite database migrations."""
    
    @pytest.fixture
    def sqlite_engine(self):
        """Create SQLite engine with specific settings."""
        db_path = self.temp_dir / "sqlite_test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        return engine
    
    def test_sqlite_alter_table_limitations(self):
        """Test SQLite's ALTER TABLE limitations."""
        # SQLite has limited ALTER TABLE support
        # This test verifies that migrations handle SQLite limitations
        
        # Create a simple table
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL
                )
            """))
            conn.commit()
        
        # Attempt to add a column (should work in SQLite)
        with self.engine.connect() as conn:
            conn.execute(text("ALTER TABLE test_table ADD COLUMN age INTEGER"))
            conn.commit()
        
        # Check column was added
        inspector = inspect(self.engine)
        columns = [col['name'] for col in inspector.get_columns('test_table')]
        assert 'age' in columns
        
        # Attempt to drop a column (will fail in SQLite)
        with pytest.raises(OperationalError):
            with self.engine.connect() as conn:
                conn.execute(text("ALTER TABLE test_table DROP COLUMN name"))
                conn.commit()
    
    def test_sqlite_foreign_key_enforcement(self):
        """Test foreign key enforcement in SQLite."""
        # Enable foreign keys
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys = ON"))
            conn.commit()
        
        # Create tables with foreign key
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE parent (
                    id INTEGER PRIMARY KEY
                )
            """))
            conn.execute(text("""
                CREATE TABLE child (
                    id INTEGER PRIMARY KEY,
                    parent_id INTEGER,
                    FOREIGN KEY(parent_id) REFERENCES parent(id)
                )
            """))
            conn.commit()
        
        # Insert parent
        with self.engine.connect() as conn:
            conn.execute(text("INSERT INTO parent (id) VALUES (1)"))
            conn.commit()
        
        # Insert child with valid parent (should succeed)
        with self.engine.connect() as conn:
            conn.execute(text("INSERT INTO child (id, parent_id) VALUES (1, 1)"))
            conn.commit()
        
        # Insert child with invalid parent (should fail)
        with pytest.raises(Exception):
            with self.engine.connect() as conn:
                conn.execute(text("INSERT INTO child (id, parent_id) VALUES (2, 999)"))
                conn.commit()