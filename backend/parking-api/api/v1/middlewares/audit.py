"""
Audit logging middleware for tracking user actions.
"""

import json
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ....services.audit import audit_log
from ....utils.logger import logger


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for auditing user actions.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list] = None,
        sensitive_fields: Optional[list] = None
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        self.sensitive_fields = sensitive_fields or [
            "password",
            "token",
            "secret",
            "authorization",
            "cookie"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Audit the request if applicable.
        """
        # Skip audit for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        # Only audit modifying operations
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return await call_next(request)
        
        # Capture request body for audit
        body = await self._get_request_body(request)
        
        # Process request
        response = await call_next(request)
        
        # Log audit if user is authenticated
        if hasattr(request.state, "user_id"):
            await self._log_audit(request, response, body)
        
        return response
    
    def _should_exclude(self, path: str) -> bool:
        """
        Check if path should be excluded from audit.
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    async def _get_request_body(self, request: Request) -> Optional[dict]:
        """
        Get and sanitize request body.
        """
        try:
            body = await request.json()
            return self._sanitize_data(body)
        except:
            return None
    
    def _sanitize_data(self, data: dict) -> dict:
        """
        Remove sensitive fields from data.
        """
        if not isinstance(data, dict):
            return data
        
        sanitized = {}
        for key, value in data.items():
            # Check if key contains sensitive information
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    async def _log_audit(self, request: Request, response, body: Optional[dict]):
        """
        Create audit log entry.
        """
        # Determine resource from path
        resource = self._get_resource_from_path(request.url.path)
        resource_id = request.path_params.get(f"{resource}_id") if request.path_params else None
        
        # Create audit log
        await audit_log(
            db=request.state.db if hasattr(request.state, "db") else None,
            user_id=request.state.user_id,
            action=f"{request.method}_{resource.upper()}",
            resource=resource,
            resource_id=resource_id,
            details={
                "path": request.url.path,
                "method": request.method,
                "query_params": dict(request.query_params),
                "body": body,
                "response_status": response.status_code
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
    
    def _get_resource_from_path(self, path: str) -> str:
        """
        Extract resource name from path.
        """
        parts = path.strip("/").split("/")
        # API version is usually first part, resource is second
        if len(parts) >= 3 and parts[0] == "api" and parts[1].startswith("v"):
            return parts[2]
        return parts[-1] if parts else "unknown"


class IPFilterMiddleware(BaseHTTPMiddleware):
    """
    Middleware for filtering requests by IP address.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        whitelist: Optional[list] = None,
        blacklist: Optional[list] = None
    ):
        super().__init__(app)
        self.whitelist = whitelist or []
        self.blacklist = blacklist or []
    
    async def dispatch(self, request: Request, call_next):
        """
        Check if IP is allowed.
        """
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check whitelist first
        if self.whitelist and client_ip not in self.whitelist:
            return await self._forbidden_response("IP not whitelisted")
        
        # Check blacklist
        if client_ip in self.blacklist:
            return await self._forbidden_response("IP is blacklisted")
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get real client IP considering proxies.
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _forbidden_response(self, message: str):
        """
        Return forbidden response.
        """
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "error": {
                    "code": "ACCESS_DENIED",
                    "message": message
                }
            }
        )