"""
Tests for audit log schemas.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from pydantic import ValidationError

from ..schemas.audit import (
    AuditAction,
    AuditLogBase,
    AuditLogCreate,
    AuditLogUpdate,
    AuditLogResponse,
    AuditLogListResponse,
    AuditLogFilter,
    AuditLogStats,
    AuditLogExport,
    AuditRetentionPolicy
)
from ..utils.datetime_utils import utc_now


def test_audit_action_enum():
    """Test audit action enum."""
    assert AuditAction.CREATE == "CREATE"
    assert AuditAction.READ == "READ"
    assert AuditAction.UPDATE == "UPDATE"
    assert AuditAction.DELETE == "DELETE"
    assert AuditAction.LOGIN == "LOGIN"
    assert AuditAction.LOGOUT == "LOGOUT"
    assert AuditAction.FAILED_LOGIN == "FAILED_LOGIN"
    assert AuditAction.PASSWORD_CHANGE == "PASSWORD_CHANGE"
    assert AuditAction.PASSWORD_RESET == "PASSWORD_RESET"
    assert AuditAction.EMAIL_VERIFY == "EMAIL_VERIFY"
    assert AuditAction.PHONE_VERIFY == "PHONE_VERIFY"
    assert AuditAction.EXPORT == "EXPORT"
    assert AuditAction.IMPORT == "IMPORT"
    assert AuditAction.API_CALL == "API_CALL"
    assert AuditAction.WEBHOOK == "WEBHOOK"
    assert AuditAction.SYSTEM == "SYSTEM"


def test_audit_log_base_valid():
    """Test valid audit log base schema."""
    data = {
        "user_id": str(uuid4()),
        "username": "testuser",
        "action": AuditAction.LOGIN,
        "resource": "user",
        "resource_id": str(uuid4()),
        "old_value": {"email": "old@test.com"},
        "new_value": {"email": "new@test.com"},
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0",
        "details": {"browser": "chrome"}
    }
    
    schema = AuditLogBase(**data)
    
    assert schema.user_id == data["user_id"]
    assert schema.username == data["username"]
    assert schema.action == data["action"]
    assert schema.resource == data["resource"]
    assert schema.resource_id == data["resource_id"]
    assert schema.old_value == data["old_value"]
    assert schema.new_value == data["new_value"]
    assert schema.ip_address == data["ip_address"]
    assert schema.user_agent == data["user_agent"]
    assert schema.details == data["details"]


def test_audit_log_base_minimal():
    """Test audit log base schema with minimal fields."""
    data = {
        "action": AuditAction.SYSTEM,
        "resource": "cron"
    }
    
    schema = AuditLogBase(**data)
    
    assert schema.action == data["action"]
    assert schema.resource == data["resource"]
    assert schema.user_id is None
    assert schema.username is None
    assert schema.resource_id is None
    assert schema.old_value is None
    assert schema.new_value is None
    assert schema.ip_address is None
    assert schema.user_agent is None
    assert schema.details is None


def test_audit_log_base_invalid():
    """Test invalid audit log base schema."""
    # Missing required fields
    with pytest.raises(ValidationError):
        AuditLogBase()
    
    # Invalid action
    with pytest.raises(ValidationError):
        AuditLogBase(
            action="INVALID",
            resource="test"
        )
    
    # Empty resource
    with pytest.raises(ValidationError):
        AuditLogBase(
            action=AuditAction.CREATE,
            resource=""
        )
    
    # Resource too long
    with pytest.raises(ValidationError):
        AuditLogBase(
            action=AuditAction.CREATE,
            resource="a" * 51
        )


def test_audit_log_create():
    """Test audit log create schema."""
    data = {
        "user_id": str(uuid4()),
        "username": "testuser",
        "action": AuditAction.CREATE,
        "resource": "booking",
        "resource_id": str(uuid4()),
        "new_value": {"status": "confirmed"}
    }
    
    schema = AuditLogCreate(**data)
    
    assert schema.user_id == data["user_id"]
    assert schema.action == data["action"]
    assert schema.resource == data["resource"]
    assert schema.new_value == data["new_value"]


def test_audit_log_update():
    """Test audit log update schema."""
    data = {
        "details": {"reason": "data correction"}
    }
    
    schema = AuditLogUpdate(**data)
    
    assert schema.details == data["details"]


def test_audit_log_update_extra_forbidden():
    """Test that extra fields are forbidden in update schema."""
    with pytest.raises(ValidationError):
        AuditLogUpdate(
            details={"reason": "test"},
            extra_field="should not be allowed"
        )


def test_audit_log_response():
    """Test audit log response schema."""
    now = utc_now()
    data = {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "username": "testuser",
        "action": AuditAction.UPDATE,
        "resource": "payment",
        "resource_id": str(uuid4()),
        "old_value": {"status": "pending"},
        "new_value": {"status": "completed"},
        "ip_address": "10.0.0.1",
        "user_agent": "curl/7.68.0",
        "details": {"amount": 100.50},
        "created_at": now
    }
    
    schema = AuditLogResponse(**data)
    
    assert schema.id == data["id"]
    assert schema.created_at == data["created_at"]
    assert schema.model_dump()["action"] == data["action"].value


def test_audit_log_list_response():
    """Test audit log list response schema."""
    items = [
        AuditLogResponse(
            id=str(uuid4()),
            action=AuditAction.CREATE,
            resource="user",
            created_at=utc_now()
        )
        for _ in range(3)
    ]
    
    data = {
        "items": items,
        "total": 10,
        "page": 1,
        "size": 3,
        "pages": 4
    }
    
    schema = AuditLogListResponse(**data)
    
    assert len(schema.items) == 3
    assert schema.total == 10
    assert schema.page == 1
    assert schema.size == 3
    assert schema.pages == 4


def test_audit_log_filter():
    """Test audit log filter schema."""
    now = utc_now()
    week_ago = now - timedelta(days=7)
    
    data = {
        "user_id": str(uuid4()),
        "username": "test",
        "action": AuditAction.LOGIN,
        "resource": "auth",
        "resource_id": str(uuid4()),
        "start_date": week_ago,
        "end_date": now,
        "ip_address": "192.168.1.1"
    }
    
    schema = AuditLogFilter(**data)
    
    assert schema.user_id == data["user_id"]
    assert schema.username == data["username"]
    assert schema.action == data["action"]
    assert schema.resource == data["resource"]
    assert schema.start_date == data["start_date"]
    assert schema.end_date == data["end_date"]


def test_audit_log_filter_optional():
    """Test audit log filter with optional fields."""
    data = {
        "start_date": utc_now() - timedelta(days=1),
        "end_date": utc_now()
    }
    
    schema = AuditLogFilter(**data)
    
    assert schema.start_date is not None
    assert schema.end_date is not None
    assert schema.user_id is None
    assert schema.action is None


def test_audit_log_stats():
    """Test audit log statistics schema."""
    data = {
        "total_actions": 1000,
        "actions_by_type": {
            "CREATE": 300,
            "UPDATE": 200,
            "DELETE": 50,
            "LOGIN": 450
        },
        "actions_by_user": {
            "john": 150,
            "jane": 120
        },
        "actions_by_resource": {
            "user": 400,
            "parking": 300,
            "booking": 300
        },
        "top_users": [
            {"username": "john", "count": 150},
            {"username": "jane", "count": 120}
        ],
        "recent_actions": ["LOGIN", "CREATE", "UPDATE"]
    }
    
    schema = AuditLogStats(**data)
    
    assert schema.total_actions == 1000
    assert len(schema.actions_by_type) == 4
    assert len(schema.top_users) == 2
    assert len(schema.recent_actions) == 3


def test_audit_log_export():
    """Test audit log export schema."""
    data = {
        "format": "csv",
        "filter": {
            "start_date": utc_now() - timedelta(days=7),
            "end_date": utc_now()
        },
        "fields": ["username", "action", "created_at"]
    }
    
    schema = AuditLogExport(**data)
    
    assert schema.format == "csv"
    assert schema.filter is not None
    assert len(schema.fields) == 3


def test_audit_log_export_invalid_format():
    """Test audit log export with invalid format."""
    with pytest.raises(ValidationError):
        AuditLogExport(
            format="excel",  # Invalid format
            filter=None
        )


def test_audit_retention_policy():
    """Test audit retention policy schema."""
    data = {
        "days": 365,
        "auto_archive": True,
        "archive_format": "parquet"
    }
    
    schema = AuditRetentionPolicy(**data)
    
    assert schema.days == 365
    assert schema.auto_archive is True
    assert schema.archive_format == "parquet"


def test_audit_retention_policy_minimal():
    """Test audit retention policy with minimal fields."""
    data = {
        "days": 90
    }
    
    schema = AuditRetentionPolicy(**data)
    
    assert schema.days == 90
    assert schema.auto_archive is True  # Default value
    assert schema.archive_format is None


def test_audit_retention_policy_invalid_days():
    """Test audit retention policy with invalid days."""
    with pytest.raises(ValidationError):
        AuditRetentionPolicy(days=0)  # Should be > 0
    
    with pytest.raises(ValidationError):
        AuditRetentionPolicy(days=-30)  # Should be > 0