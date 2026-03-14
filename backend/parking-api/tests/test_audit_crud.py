"""
Tests for audit log CRUD operations.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.audit import audit
from ..schemas.audit import AuditLogCreate, AuditLogFilter, AuditRetentionPolicy
from ..models.audit import AuditLog, AuditAction
from ..utils.datetime_utils import utc_now


@pytest.mark.asyncio
async def test_create_audit_log(db_session: AsyncSession, test_audit_log_data):
    """Test creating an audit log entry."""
    obj_in = AuditLogCreate(**test_audit_log_data)
    
    result = await audit.create_audit_log(
        db_session,
        obj_in=obj_in,
        ip_address="127.0.0.1",
        user_agent="pytest"
    )
    
    assert result.user_id == test_audit_log_data["user_id"]
    assert result.username == test_audit_log_data["username"]
    assert result.action == test_audit_log_data["action"]
    assert result.resource == test_audit_log_data["resource"]
    assert result.ip_address == "127.0.0.1"
    assert result.user_agent == "pytest"
    assert result.id is not None
    assert result.created_at is not None


@pytest.mark.asyncio
async def test_get_audit_log(db_session: AsyncSession, test_audit_log):
    """Test getting an audit log by ID."""
    result = await audit.get(db_session, id=test_audit_log.id)
    
    assert result is not None
    assert result.id == test_audit_log.id
    assert result.user_id == test_audit_log.user_id


@pytest.mark.asyncio
async def test_get_multi_audit_logs(db_session: AsyncSession, create_multiple_audit_logs):
    """Test getting multiple audit logs."""
    result = await audit.get_multi(db_session, skip=0, limit=10)
    
    assert len(result) == 10
    assert all(isinstance(log, AuditLog) for log in result)


@pytest.mark.asyncio
async def test_get_by_user(db_session: AsyncSession, create_multiple_audit_logs, test_user_data):
    """Test getting audit logs by user."""
    result = await audit.get_by_user(db_session, user_id=test_user_data["id"], limit=5)
    
    assert len(result) == 5
    assert all(log.user_id == test_user_data["id"] for log in result)


@pytest.mark.asyncio
async def test_get_by_resource(db_session: AsyncSession, create_multiple_audit_logs):
    """Test getting audit logs by resource."""
    result = await audit.get_by_resource(db_session, resource="user", limit=5)
    
    assert len(result) == 5
    assert all(log.resource == "user" for log in result)


@pytest.mark.asyncio
async def test_get_by_action(db_session: AsyncSession, create_multiple_audit_logs):
    """Test getting audit logs by action."""
    result = await audit.get_by_action(db_session, action=AuditAction.CREATE, limit=5)
    
    assert len(result) == 5
    assert all(log.action == AuditAction.CREATE for log in result)


@pytest.mark.asyncio
async def test_filter_audit_logs(db_session: AsyncSession, create_multiple_audit_logs, test_user_data):
    """Test filtering audit logs."""
    filter_params = AuditLogFilter(
        user_id=test_user_data["id"],
        action=AuditAction.CREATE,
        resource="user"
    )
    
    result = await audit.filter_audit_logs(db_session, filter_params=filter_params)
    
    assert all(log.user_id == test_user_data["id"] for log in result)
    assert all(log.action == AuditAction.CREATE for log in result)
    assert all(log.resource == "user" for log in result)


@pytest.mark.asyncio
async def test_count_filtered(db_session: AsyncSession, create_multiple_audit_logs, test_user_data):
    """Test counting filtered audit logs."""
    filter_params = AuditLogFilter(
        user_id=test_user_data["id"]
    )
    
    count = await audit.count_filtered(db_session, filter_params=filter_params)
    
    assert count == len(create_multiple_audit_logs)


@pytest.mark.asyncio
async def test_get_statistics(db_session: AsyncSession, create_multiple_audit_logs):
    """Test getting audit statistics."""
    stats = await audit.get_statistics(db_session)
    
    assert "total_actions" in stats
    assert "actions_by_type" in stats
    assert "actions_by_user" in stats
    assert "actions_by_resource" in stats
    assert stats["total_actions"] >= len(create_multiple_audit_logs)


@pytest.mark.asyncio
async def test_cleanup_old_logs(db_session: AsyncSession, create_multiple_audit_logs):
    """Test cleaning up old logs."""
    policy = AuditRetentionPolicy(days=10, auto_archive=True)
    
    deleted = await audit.cleanup_old_logs(db_session, policy=policy)
    
    assert deleted >= 0  # Number of logs older than 10 days


@pytest.mark.asyncio
async def test_get_user_activity_summary(db_session: AsyncSession, create_multiple_audit_logs, test_user_data):
    """Test getting user activity summary."""
    summary = await audit.get_user_activity_summary(
        db_session,
        user_id=test_user_data["id"],
        days=30
    )
    
    assert summary["user_id"] == test_user_data["id"]
    assert summary["period_days"] == 30
    assert summary["total_actions"] == len(create_multiple_audit_logs)
    assert "actions_by_type" in summary
    assert "daily_activity" in summary


@pytest.mark.asyncio
async def test_update_audit_log_not_allowed(db_session: AsyncSession, test_audit_log):
    """Test that audit logs cannot be updated."""
    from ..schemas.audit import AuditLogUpdate
    
    obj_in = AuditLogUpdate(details={"updated": True})
    
    with pytest.raises(Exception):
        await audit.update(db_session, db_obj=test_audit_log, obj_in=obj_in)


@pytest.mark.asyncio
async def test_delete_audit_log(db_session: AsyncSession, test_audit_log):
    """Test deleting an audit log."""
    deleted = await audit.remove(db_session, id=test_audit_log.id)
    
    assert deleted.id == test_audit_log.id
    
    # Verify it's gone
    result = await audit.get(db_session, id=test_audit_log.id)
    assert result is None