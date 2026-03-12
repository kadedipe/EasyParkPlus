"""
Middleware setup and configuration.
"""

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .auth import AuthMiddleware, OptionalAuthMiddleware
from .rate_limit import RateLimitMiddleware
from .logging import LoggingMiddleware, RequestIDMiddleware
from .error_handler import ErrorHandlerMiddleware
from .security import SecurityHeadersMiddleware
from .compression import CompressionMiddleware
from .cache import CacheMiddleware
from .metrics import MetricsMiddleware
from .db_session import DBSessionMiddleware, TransactionMiddleware
from .timeout import TimeoutMiddleware
from .audit import AuditMiddleware

from ....core.config import settings


def setup_middlewares(app: FastAPI):
    """
    Configure all middlewares for the application.
    """
    
    # 1. Request ID - should be first to have ID for all logs
    app.add_middleware(RequestIDMiddleware)
    
    # 2. CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"]
    )
    
    # 3. Security Headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 4. Compression
    app.add_middleware(CompressionMiddleware, minimum_size=500)
    
    # 5. Timeout
    app.add_middleware(TimeoutMiddleware, timeout_seconds=30)
    
    # 6. Database Session
    app.add_middleware(DBSessionMiddleware)
    
    # 7. Transaction Management
    app.add_middleware(TransactionMiddleware)
    
    # 8. Authentication (optional first, then required)
    app.add_middleware(OptionalAuthMiddleware)
    app.add_middleware(
        AuthMiddleware,
        exclude_paths=[
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/refresh",
            "/api/v1/auth/request-reset",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/verify-email",
        ]
    )
    
    # 9. Rate Limiting
    app.add_middleware(
        RateLimitMiddleware,
        default_limit=100,
        default_window=60
    )
    
    # 10. Audit Logging
    app.add_middleware(AuditMiddleware)
    
    # 11. Cache
    app.add_middleware(CacheMiddleware)
    
    # 12. Metrics
    app.add_middleware(
        MetricsMiddleware,
        exclude_paths=["/metrics", "/health"]
    )
    
    # 13. Logging - should be near the end to capture everything
    app.add_middleware(
        LoggingMiddleware,
        log_headers=settings.DEBUG,
        log_body=settings.DEBUG
    )
    
    # 14. Error Handler - should be last to catch all errors
    app.add_middleware(
        ErrorHandlerMiddleware,
        debug=settings.DEBUG
    )


def setup_exception_handlers(app: FastAPI):
    """
    Configure exception handlers.
    """
    from .error_handler import ExceptionHandlers
    from ....utils.exceptions import (
        NotFoundException,
        ValidationException,
        AuthenticationException,
        AuthorizationException,
        ConflictException,
        RateLimitException,
        ServiceUnavailableException
    )
    
    app.add_exception_handler(NotFoundException, ExceptionHandlers.not_found_handler)
    app.add_exception_handler(ValidationException, ExceptionHandlers.validation_handler)
    app.add_exception_handler(AuthenticationException, ExceptionHandlers.auth_handler)
    app.add_exception_handler(AuthorizationException, ExceptionHandlers.forbidden_handler)
    app.add_exception_handler(ConflictException, ExceptionHandlers.conflict_handler)
    app.add_exception_handler(RateLimitException, ExceptionHandlers.rate_limit_handler)
    app.add_exception_handler(ServiceUnavailableException, ExceptionHandlers.service_unavailable_handler)