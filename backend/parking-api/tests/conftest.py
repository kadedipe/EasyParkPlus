"""
Pytest configuration and fixtures.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from ..main import app
from ..db.base import Base
from ..db.session import get_db, DatabaseSessionManager
from ..models.audit import AuditLog, AuditAction
from ..schemas.audit import AuditLogCreate
from ..crud.audit import audit
from ..core.config import settings
from ..utils.security import hash_password, generate_token
from ..utils.datetime_utils import utc_now


# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/parking_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Override database dependency."""
    async def _override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """Test user data."""
    return {
        "id": str(uuid4()),
        "email": "test@example.com",
        "username": "testuser",
        "password": hash_password("TestPassword123!"),
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
        "created_at": utc_now(),
        "updated_at": utc_now()
    }


@pytest.fixture
def test_superuser_data() -> Dict[str, Any]:
    """Test superuser data."""
    return {
        "id": str(uuid4()),
        "email": "admin@example.com",
        "username": "admin",
        "password": hash_password("AdminPassword123!"),
        "full_name": "Admin User",
        "is_active": True,
        "is_superuser": True,
        "created_at": utc_now(),
        "updated_at": utc_now()
    }


@pytest.fixture
def test_audit_log_data(test_user_data) -> Dict[str, Any]:
    """Test audit log data."""
    return {
        "user_id": test_user_data["id"],
        "username": test_user_data["username"],
        "action": AuditAction.CREATE,
        "resource": "user",
        "resource_id": test_user_data["id"],
        "old_value": None,
        "new_value": {"email": test_user_data["email"]},
        "ip_address": "127.0.0.1",
        "user_agent": "pytest",
        "details": {"test": True}
    }


@pytest.fixture
async def test_audit_log(db_session: AsyncSession, test_audit_log_data) -> AuditLog:
    """Create test audit log entry."""
    audit_log = AuditLog(**test_audit_log_data)
    db_session.add(audit_log)
    await db_session.commit()
    await db_session.refresh(audit_log)
    return audit_log


@pytest.fixture
def auth_headers(test_user_data) -> Dict[str, str]:
    """Create authentication headers."""
    token = generate_token(
        data={"sub": test_user_data["id"], "username": test_user_data["username"]}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def superuser_auth_headers(test_superuser_data) -> Dict[str, str]:
    """Create superuser authentication headers."""
    token = generate_token(
        data={"sub": test_superuser_data["id"], "username": test_superuser_data["username"], "is_superuser": True}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def create_multiple_audit_logs(db_session: AsyncSession, test_user_data):
    """Create multiple audit logs for testing."""
    logs = []
    actions = list(AuditAction)
    resources = ["user", "parking", "booking", "payment", "vehicle"]
    
    for i in range(20):
        action = actions[i % len(actions)]
        resource = resources[i % len(resources)]
        
        log = AuditLog(
            user_id=test_user_data["id"],
            username=test_user_data["username"],
            action=action,
            resource=resource,
            resource_id=str(uuid4()),
            old_value={"test": f"old_{i}"},
            new_value={"test": f"new_{i}"},
            ip_address=f"192.168.1.{i}",
            user_agent="pytest",
            details={"index": i},
            created_at=utc_now() - timedelta(days=i)
        )
        logs.append(log)
        db_session.add(log)
    
    await db_session.commit()
    
    for log in logs:
        await db_session.refresh(log)
    
    return logs