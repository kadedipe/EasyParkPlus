"""
Custom middleware setup for the application.
"""

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from .middleware import (
    RequestIDMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    TimeoutMiddleware,
    DBSessionMiddleware,
    MetricsMiddleware,
    AuditMiddleware
)
from .config import settings


def setup_middlewares(app: FastAPI):
    """
    Setup all custom middlewares in the correct order.
    """
    # Request ID must be first to have ID for all logs
    app.add_middleware(RequestIDMiddleware)
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Timeout middleware
    app.add_middleware(TimeoutMiddleware, timeout_seconds=settings.TIMEOUT_SECONDS)
    
    # Database session middleware
    app.add_middleware(DBSessionMiddleware)
    
    # Rate limiting
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimitMiddleware,
            default_limit=settings.RATE_LIMIT_DEFAULT,
            default_window=settings.RATE_LIMIT_WINDOW
        )
    
    # Metrics collection
    if settings.METRICS_ENABLED:
        app.add_middleware(MetricsMiddleware)
    
    # Audit logging
    if settings.AUDIT_ENABLED:
        app.add_middleware(AuditMiddleware)
    
    # Logging middleware should be last
    app.add_middleware(
        LoggingMiddleware,
        log_headers=settings.DEBUG,
        log_body=settings.DEBUG
    )