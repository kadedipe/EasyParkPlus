"""
Audit log schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class AuditAction(str, Enum):
    """Audit action enumeration matching the model."""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    FAILED_LOGIN = "FAILED_LOGIN"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET = "PASSWORD_RESET"
    EMAIL_VERIFY = "EMAIL_VERIFY"
    PHONE_VERIFY = "PHONE_VERIFY"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    API_CALL = "API_CALL"
    WEBHOOK = "WEBHOOK"
    SYSTEM = "SYSTEM"


# Base Audit Schema
class AuditLogBase(BaseModel):
    """Base schema for audit log."""
    user_id: Optional[str] = Field(None, description="User ID who performed the action")
    username: Optional[str] = Field(None, max_length=255, description="Username who performed the action")
    action: AuditAction = Field(..., description="Type of action performed")
    resource: str = Field(..., max_length=50, description="Resource being acted upon")
    resource_id: Optional[str] = Field(None, max_length=50, description="ID of the resource")
    old_value: Optional[Dict[str, Any]] = Field(None, description="Previous value before change")
    new_value: Optional[Dict[str, Any]] = Field(None, description="New value after change")
    ip_address: Optional[str] = Field(None, description="IP address of the client")
    user_agent: Optional[str] = Field(None, description="User agent of the client")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")


# Create Schema
class AuditLogCreate(AuditLogBase):
    """Schema for creating an audit log entry."""
    pass


# Update Schema (though audit logs typically shouldn't be updated)
class AuditLogUpdate(BaseModel):
    """Schema for updating an audit log (use with caution)."""
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "details": {"reason": "Data correction", "approved_by": "admin"}
            }
        }
    )


# Response Schema
class AuditLogResponse(AuditLogBase):
    """Schema for audit log response."""
    id: str = Field(..., description="Audit log ID")
    created_at: datetime = Field(..., description="When the audit entry was created")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "username": "john.doe",
                "action": "UPDATE",
                "resource": "user",
                "resource_id": "123e4567-e89b-12d3-a456-426614174002",
                "old_value": {"email": "old@example.com"},
                "new_value": {"email": "new@example.com"},
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "details": {"reason": "Email update"},
                "created_at": "2024-01-01T00:00:00Z"
            }
        }
    )


# List Response Schema
class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list response."""
    items: List[AuditLogResponse]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")


# Filter Schema
class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs."""
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    username: Optional[str] = Field(None, description="Filter by username")
    action: Optional[AuditAction] = Field(None, description="Filter by action type")
    resource: Optional[str] = Field(None, max_length=50, description="Filter by resource")
    resource_id: Optional[str] = Field(None, max_length=50, description="Filter by resource ID")
    start_date: Optional[datetime] = Field(None, description="Filter by start date")
    end_date: Optional[datetime] = Field(None, description="Filter by end date")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174001",
                "action": "LOGIN",
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z"
            }
        }
    )


# Statistics Schema
class AuditLogStats(BaseModel):
    """Schema for audit log statistics."""
    total_actions: int = Field(..., description="Total number of actions")
    actions_by_type: Dict[str, int] = Field(..., description="Actions grouped by type")
    actions_by_user: Dict[str, int] = Field(..., description="Actions grouped by user")
    actions_by_resource: Dict[str, int] = Field(..., description="Actions grouped by resource")
    top_users: List[Dict[str, Any]] = Field(..., description="Top users by action count")
    recent_actions: List[AuditAction] = Field(..., description="Recent action types")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_actions": 1000,
                "actions_by_type": {"CREATE": 300, "UPDATE": 200, "DELETE": 50, "LOGIN": 450},
                "actions_by_user": {"john.doe": 150, "jane.smith": 120},
                "actions_by_resource": {"user": 400, "parking": 300, "booking": 300},
                "top_users": [{"username": "john.doe", "count": 150}],
                "recent_actions": ["LOGIN", "CREATE", "UPDATE"]
            }
        }
    )


# Export Schema
class AuditLogExport(BaseModel):
    """Schema for audit log export request."""
    format: str = Field(..., pattern="^(csv|json|pdf)$", description="Export format")
    filter: Optional[AuditLogFilter] = Field(None, description="Filters to apply")
    fields: Optional[List[str]] = Field(None, description="Fields to export")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "format": "csv",
                "filter": {
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-01-31T23:59:59Z"
                },
                "fields": ["username", "action", "resource", "created_at"]
            }
        }
    )


# Retention Policy Schema
class AuditRetentionPolicy(BaseModel):
    """Schema for audit log retention policy."""
    days: int = Field(..., gt=0, description="Number of days to retain logs")
    auto_archive: bool = Field(True, description="Auto archive old logs")
    archive_format: Optional[str] = Field(None, pattern="^(json|parquet|csv)$", description="Archive format")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "days": 365,
                "auto_archive": True,
                "archive_format": "parquet"
            }
        }
    )