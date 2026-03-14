"""
Tests for audit log API endpoints.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from uuid import uuid4

from ..utils.datetime_utils import utc_now


@pytest.mark.asyncio
async def test_create_audit_log_api(client: AsyncClient, auth_headers, test_user_data):
    """Test creating an audit log via API."""
    audit_data = {
        "user_id": test_user_data["id"],
        "username": test_user_data["username"],
        "action": "LOGIN",
        "resource": "user",
        "resource_id": test_user_data["id"],
        "details": {"login_method": "password"}
    }
    
    response = await client.post(
        "/api/v1/audit/",
        json=audit_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == test_user_data["id"]
    assert data["action"] == "LOGIN"
    assert data["resource"] == "user"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_audit_log_api(client: AsyncClient, auth_headers, test_audit_log):
    """Test getting an audit log by ID via API."""
    response = await client.get(
        f"/api/v1/audit/{test_audit_log.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_audit_log.id
    assert data["user_id"] == test_audit_log.user_id
    assert data["action"] == test_audit_log.action.value


@pytest.mark.asyncio
async def test_get_audit_log_not_found(client: AsyncClient, auth_headers):
    """Test getting non-existent audit log."""
    response = await client.get(
        f"/api/v1/audit/{uuid4()}",
        headers=auth_headers
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_audit_logs_api(client: AsyncClient, auth_headers, create_multiple_audit_logs):
    """Test listing audit logs via API."""
    response = await client.get(
        "/api/v1/audit/",
        headers=auth_headers,
        params={"skip": 0, "limit": 10}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data
    assert len(data["items"]) == 10


@pytest.mark.asyncio
async def test_filter_audit_logs_api(
    client: AsyncClient,
    auth_headers,
    create_multiple_audit_logs,
    test_user_data
):
    """Test filtering audit logs via API."""
    response = await client.get(
        "/api/v1/audit/filter",
        headers=auth_headers,
        params={
            "user_id": test_user_data["id"],
            "action": "CREATE",
            "start_date": (utc_now() - timedelta(days=30)).isoformat(),
            "end_date": utc_now().isoformat()
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_audit_statistics_api(
    client: AsyncClient,
    superuser_auth_headers,
    create_multiple_audit_logs
):
    """Test getting audit statistics via API."""
    response = await client.get(
        "/api/v1/audit/statistics",
        headers=superuser_auth_headers,
        params={
            "start_date": (utc_now() - timedelta(days=30)).isoformat(),
            "end_date": utc_now().isoformat()
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_actions" in data
    assert "actions_by_type" in data
    assert "actions_by_user" in data
    assert "actions_by_resource" in data


@pytest.mark.asyncio
async def test_get_user_activity_api(
    client: AsyncClient,
    auth_headers,
    create_multiple_audit_logs,
    test_user_data
):
    """Test getting user activity via API."""
    response = await client.get(
        f"/api/v1/audit/user/{test_user_data['id']}/activity",
        headers=auth_headers,
        params={"days": 30}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == test_user_data["id"]
    assert data["period_days"] == 30
    assert data["total_actions"] >= len(create_multiple_audit_logs)


@pytest.mark.asyncio
async def test_get_resource_history_api(
    client: AsyncClient,
    auth_headers,
    create_multiple_audit_logs,
    test_user_data
):
    """Test getting resource history via API."""
    response = await client.get(
        f"/api/v1/audit/resource/user/{test_user_data['id']}/history",
        headers=auth_headers,
        params={"limit": 10}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


@pytest.mark.asyncio
async def test_export_audit_logs_api(
    client: AsyncClient,
    superuser_auth_headers,
    create_multiple_audit_logs
):
    """Test exporting audit logs via API."""
    export_data = {
        "format": "csv",
        "filter": {
            "start_date": (utc_now() - timedelta(days=30)).isoformat(),
            "end_date": utc_now().isoformat()
        },
        "fields": ["username", "action", "resource", "created_at"]
    }
    
    response = await client.post(
        "/api/v1/audit/export",
        json=export_data,
        headers=superuser_auth_headers
    )
    
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert response.content is not None


@pytest.mark.asyncio
async def test_cleanup_audit_logs_api(
    client: AsyncClient,
    superuser_auth_headers
):
    """Test cleaning up old audit logs via API."""
    policy_data = {
        "days": 30,
        "auto_archive": True,
        "archive_format": "json"
    }
    
    response = await client.post(
        "/api/v1/audit/cleanup",
        json=policy_data,
        headers=superuser_auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "deleted_count" in data


@pytest.mark.asyncio
async def test_audit_log_unauthorized_access(client: AsyncClient, test_audit_log):
    """Test unauthorized access to audit logs."""
    response = await client.get(f"/api/v1/audit/{test_audit_log.id}")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_audit_log_forbidden_access(
    client: AsyncClient,
    auth_headers,
    test_superuser_data
):
    """Test forbidden access to admin-only endpoints."""
    # Try to access admin-only endpoint with regular user
    response = await client.get(
        "/api/v1/audit/statistics",
        headers=auth_headers
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_invalid_audit_log_creation(client: AsyncClient, auth_headers):
    """Test creating audit log with invalid data."""
    invalid_data = {
        "action": "INVALID_ACTION",  # Invalid action
        "resource": ""  # Empty resource
    }
    
    response = await client.post(
        "/api/v1/audit/",
        json=invalid_data,
        headers=auth_headers
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pagination_audit_logs(client: AsyncClient, auth_headers, create_multiple_audit_logs):
    """Test pagination for audit logs."""
    # Test different page sizes
    response1 = await client.get(
        "/api/v1/audit/",
        headers=auth_headers,
        params={"skip": 0, "limit": 5}
    )
    data1 = response1.json()
    assert len(data1["items"]) == 5
    
    # Test second page
    response2 = await client.get(
        "/api/v1/audit/",
        headers=auth_headers,
        params={"skip": 5, "limit": 5}
    )
    data2 = response2.json()
    assert len(data2["items"]) == 5
    
    # Ensure different items on different pages
    assert data1["items"][0]["id"] != data2["items"][0]["id"]


@pytest.mark.asyncio
async def test_sorting_audit_logs(client: AsyncClient, auth_headers, create_multiple_audit_logs):
    """Test sorting for audit logs."""
    # Sort by created_at desc (default)
    response_desc = await client.get(
        "/api/v1/audit/",
        headers=auth_headers,
        params={"sort_by": "created_at", "sort_order": "desc"}
    )
    data_desc = response_desc.json()
    
    # Sort by created_at asc
    response_asc = await client.get(
        "/api/v1/audit/",
        headers=auth_headers,
        params={"sort_by": "created_at", "sort_order": "asc"}
    )
    data_asc = response_asc.json()
    
    # Compare first items
    if data_desc["items"] and data_asc["items"]:
        assert data_desc["items"][0]["created_at"] != data_asc["items"][0]["created_at"]


@pytest.mark.asyncio
async def test_date_range_filtering(client: AsyncClient, auth_headers, create_multiple_audit_logs):
    """Test date range filtering for audit logs."""
    now = utc_now()
    week_ago = now - timedelta(days=7)
    
    response = await client.get(
        "/api/v1/audit/filter",
        headers=auth_headers,
        params={
            "start_date": week_ago.isoformat(),
            "end_date": now.isoformat()
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify dates are within range
    for item in data["items"]:
        created_at = datetime.fromisoformat(item["created_at"].replace('Z', '+00:00'))
        assert week_ago <= created_at <= now