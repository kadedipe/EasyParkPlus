"""
Security headers middleware for hardening API responses.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to responses.
    """
    
    def __init__(self, app: ASGIApp, hsts_max_age: int = 63072000):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
    
    async def dispatch(self, request: Request, call_next):
        """
        Add security headers to response.
        """
        response = await call_next(request)
        
        # HSTS - Force HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = f"max-age={self.hsts_max_age}; includeSubDomains; preload"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = self._get_csp_policy()
        
        # Feature Policy / Permissions Policy
        response.headers["Permissions-Policy"] = self._get_permissions_policy()
        
        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]
        
        # Remove powered-by header
        response.headers["X-Powered-By"] = "Parking Management API"
        
        return response
    
    def _get_csp_policy(self) -> str:
        """
        Generate Content Security Policy header.
        """
        policies = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self'",
            "img-src 'self' data:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
            "object-src 'none'"
        ]
        
        return "; ".join(policies)
    
    def _get_permissions_policy(self) -> str:
        """
        Generate Permissions Policy header.
        """
        policies = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "accelerometer=()",
            "gyroscope=()",
            "midi=()",
            "sync-xhr=()",
            "interest-cohort=()"
        ]
        
        return ", ".join(policies)


class SecurityHeadersMiddleware:
    """
    Alternative implementation using Starlette's middleware.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        """
        ASGI callable for adding security headers.
        """
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                
                # Convert headers to list of tuples if needed
                if isinstance(headers, dict):
                    headers = [(k.encode(), v.encode()) for k, v in headers.items()]
                
                # Add security headers
                security_headers = [
                    (b"strict-transport-security", b"max-age=63072000; includeSubDomains; preload"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"x-xss-protection", b"1; mode=block"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"content-security-policy", b"default-src 'self'; frame-ancestors 'none'; form-action 'self'"),
                    (b"permissions-policy", b"geolocation=(), microphone=(), camera=(), payment=()"),
                ]
                
                headers.extend(security_headers)
                message["headers"] = headers
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)