"""
Tests for audit log models.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from ..models.audit import AuditLog, AuditAction
from ..utils.datetime_utils import utc_now


def test_audit_log_model_creation():
    """Test creating an audit log model instance."""
    log_id = str(uuid4())
    user_id = str(uuid4())
    now = utc_now()
    
    audit_log = AuditLog(
        id=log_id,
        user_id=user_id,
        username="testuser",
        action=AuditAction.LOGIN,
        resource="user",
        resource_id=user_id,
        old_value={"old": "value"},
        new_value={"new": "value"},
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        details={"browser": "chrome"},
        created_at=now,
        updated_at=now
    )
    
    assert audit_log.id == log_id
    assert audit_log.user_id == user_id
    assert audit_log.username == "testuser"
    assert audit_log.action == AuditAction.LOGIN
    assert audit_log.resource == "user"
    assert audit_log.resource_id == user_id
    assert audit_log.old_value == {"old": "value"}
    assert audit_log.new_value == {"new": "value"}
    assert audit_log.ip_address == "192.168.1.1"
    assert audit_log.user_agent == "Mozilla/5.0"
    assert audit_log.details == {"browser": "chrome"}
    assert audit_log.created_at == now
    assert audit_log.updated_at == now


def test_audit_log_model_defaults():
    """Test audit log model default values."""
    audit_log = AuditLog(
        action=AuditAction.CREATE,
        resource="test"
    )
    
    assert audit_log.id is not None
    assert audit_log.created_at is not None
    assert audit_log.updated_at is not None
    assert audit_log.user_id is None
    assert audit_log.username is None
    assert audit_log.resource_id is None
    assert audit_log.old_value is None
    assert audit_log.new_value is None
    assert audit_log.ip_address is None
    assert audit_log.user_agent is None
    assert audit_log.details is None


def test_audit_action_enum():
    """Test audit action enum values."""
    assert AuditAction.CREATE.value == "CREATE"
    assert AuditAction.READ.value == "READ"
    assert AuditAction.UPDATE.value == "UPDATE"
    assert AuditAction.DELETE.value == "DELETE"
    assert AuditAction.LOGIN.value == "LOGIN"
    assert AuditAction.LOGOUT.value == "LOGOUT"
    assert AuditAction.FAILED_LOGIN.value == "FAILED_LOGIN"
    assert AuditAction.PASSWORD_CHANGE.value == "PASSWORD_CHANGE"
    assert AuditAction.PASSWORD_RESET.value == "PASSWORD_RESET"
    assert AuditAction.EMAIL_VERIFY.value == "EMAIL_VERIFY"
    assert AuditAction.PHONE_VERIFY.value == "PHONE_VERIFY"
    assert AuditAction.EXPORT.value == "EXPORT"
    assert AuditAction.IMPORT.value == "IMPORT"
    assert AuditAction.API_CALL.value == "API_CALL"
    assert AuditAction.WEBHOOK.value == "WEBHOOK"
    assert AuditAction.SYSTEM.value == "SYSTEM"


def test_audit_log_repr():
    """Test audit log string representation."""
    audit_log = AuditLog(
        action=AuditAction.UPDATE,
        resource="booking",
        resource_id="123"
    )
    
    repr_str = repr(audit_log)
    assert "AuditLog" in repr_str
    assert str(audit_log.action) in repr_str
    assert audit_log.resource in repr_str
    assert audit_log.resource_id in repr_str


def test_audit_log_dict_method():
    """Test audit log dict conversion."""
    audit_log = AuditLog(
        action=AuditAction.CREATE,
        resource="user",
        username="testuser"
    )
    
    log_dict = audit_log.dict()
    
    assert isinstance(log_dict, dict)
    assert log_dict["action"] == AuditAction.CREATE
    assert log_dict["resource"] == "user"
    assert log_dict["username"] == "testuser"
    assert "id" in log_dict
    assert "created_at" in log_dict


def test_audit_log_with_all_fields():
    """Test audit log with all fields populated."""
    log_data = {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "username": "john.doe",
        "action": AuditAction.PAYMENT_PROCESSED,
        "resource": "payment",
        "resource_id": "pay_123",
        "old_value": {"status": "pending"},
        "new_value": {"status": "completed"},
        "ip_address": "10.0.0.1",
        "user_agent": "PostmanRuntime/7.26.8",
        "details": {"amount": 25.50, "method": "credit_card"},
        "created_at": utc_now(),
        "updated_at": utc_now()
    }
    
    audit_log = AuditLog(**log_data)
    
    for key, value in log_data.items():
        assert getattr(audit_log, key) == value


def test_audit_log_timestamps():
    """Test audit log timestamps."""
    audit_log = AuditLog(
        action=AuditAction.SYSTEM,
        resource="cron"
    )
    
    assert isinstance(audit_log.created_at, datetime)
    assert isinstance(audit_log.updated_at, datetime)
    assert audit_log.created_at <= audit_log.updated_at


def test_audit_log_nullable_fields():
    """Test nullable fields in audit log."""
    audit_log = AuditLog(
        action=AuditAction.API_CALL,
        resource="api"
    )
    
    assert audit_log.user_id is None
    assert audit_log.username is None
    assert audit_log.resource_id is None
    assert audit_log.old_value is None
    assert audit_log.new_value is None
    assert audit_log.ip_address is None
    assert audit_log.user_agent is None
    assert audit_log.details is None