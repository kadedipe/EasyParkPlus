#!/usr/bin/env python3
"""
Main entry point for the Parking Management API.
This module initializes and configures the FastAPI application.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
from typing import Dict, Any
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import __version__, __api_title__, __api_description__
from api.v1.api import api_router
from core.config import settings
from core.events import startup_handler, shutdown_handler, lifespan
from core.exceptions import BaseAppException
from core.middlewares import setup_middlewares
from core.logging import setup_logging
from db.session import engine
from services.health import health_checker
from utils.logger import logger


# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan_context(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    await startup_handler()
    yield
    # Shutdown
    await shutdown_handler()


# Create FastAPI application
app = FastAPI(
    title=__api_title__,
    description=__api_description__,
    version=__version__,
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
    contact={
        "name": "Parking Management Support",
        "email": "support@parking-management.com",
        "url": "https://parking-management.com/support"
    },
    license_info={
        "name": "Proprietary",
        "url": "https://parking-management.com/license"
    },
    servers=[
        {"url": "https://api.parking-management.com", "description": "Production server"},
        {"url": "https://staging.api.parking-management.com", "description": "Staging server"},
        {"url": "http://localhost:8000", "description": "Development server"}
    ],
    root_path=settings.ROOT_PATH,
    openapi_tags=[
        {
            "name": "authentication",
            "description": "🔐 User authentication and authorization operations",
            "externalDocs": {
                "description": "Authentication Guide",
                "url": "https://docs.parking-management.com/auth"
            }
        },
        {
            "name": "users",
            "description": "👤 User profile and account management"
        },
        {
            "name": "vehicles",
            "description": "🚗 Vehicle registration and management"
        },
        {
            "name": "parking",
            "description": "🅿️ Parking spot availability and information"
        },
        {
            "name": "reservations",
            "description": "📅 Parking reservation management"
        },
        {
            "name": "payments",
            "description": "💳 Payment processing and transaction history"
        },
        {
            "name": "reviews",
            "description": "⭐ Parking spot reviews and ratings"
        },
        {
            "name": "waitlist",
            "description": "⏳ Waitlist management for unavailable spots"
        },
        {
            "name": "admin",
            "description": "👑 Administrative operations (requires admin privileges)"
        },
        {
            "name": "health",
            "description": "🏥 Health check endpoints for monitoring"
        },
        {
            "name": "metrics",
            "description": "📊 Prometheus metrics endpoint"
        }
    ],
    lifespan=lifespan_context,
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "filter": True,
        "syntaxHighlight.theme": "monokai"
    }
)


# ============================================================================
# Middleware Setup
# ============================================================================

# CORS middleware
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Content-Disposition"
        ],
        max_age=600
    )

# Trusted host middleware
if settings.TRUSTED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.TRUSTED_HOSTS
    )

# Compression middleware
if settings.ENABLE_COMPRESSION:
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1000,
        compresslevel=5
    )

# Setup custom middlewares
setup_middlewares(app)


# ============================================================================
# Include Routers
# ============================================================================

# Include API v1 router
app.include_router(api_router, prefix="/api/v1")


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["root"])
async def root() -> Dict[str, Any]:
    """
    Root endpoint with API information and navigation.
    
    Returns:
        Dict with API metadata and available endpoints
    """
    return {
        "service": __api_title__,
        "version": __version__,
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": {
            "swagger": "/docs" if settings.ENVIRONMENT != "production" else "/docs",
            "redoc": "/redoc" if settings.ENVIRONMENT != "production" else "/redoc",
            "openapi": "/openapi.json" if settings.ENVIRONMENT != "production" else "/openapi.json"
        },
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "api": "/api/v1"
        },
        "links": {
            "github": "https://github.com/yourcompany/parking-management",
            "support": "https://parking-management.com/support",
            "status": "https://status.parking-management.com"
        }
    }


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/health", tags=["health"], response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    
    Returns:
        Health status of all services
    """
    health_status = await health_checker.check_all()
    
    # Determine overall status
    overall_status = "healthy"
    for service, status in health_status.items():
        if status != "healthy":
            overall_status = "degraded"
            break
    
    response = {
        "status": overall_status,
        "version": __version__,
        "timestamp": datetime.utcnow().isoformat(),
        "services": health_status
    }
    
    # Return appropriate status code
    status_code = 200 if overall_status == "healthy" else 503
    return JSONResponse(content=response, status_code=status_code)


@app.get("/health/live", tags=["health"])
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes liveness probe endpoint.
    
    Returns:
        Simple liveness status
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@app.get("/health/ready", tags=["health"])
async def readiness_check() -> Dict[str, str]:
    """
    Kubernetes readiness probe endpoint.
    
    Returns:
        Simple readiness status
    """
    # Check if application is ready to accept traffic
    if await health_checker.is_ready():
        return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
    else:
        return JSONResponse(
            content={"status": "not ready", "timestamp": datetime.utcnow().isoformat()},
            status_code=503
        )


# ============================================================================
# Metrics Endpoint
# ============================================================================

@app.get("/metrics", tags=["metrics"])
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns:
        Prometheus formatted metrics
    """
    from prometheus_client import generate_latest, REGISTRY
    
    # Ensure content type is correct
    from starlette.responses import Response
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4"
    )


# ============================================================================
# Documentation Endpoints (for production)
# ============================================================================

if settings.ENVIRONMENT == "production":
    
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui():
        """
        Custom Swagger UI documentation.
        """
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{__api_title__} - Documentation",
            swagger_favicon_url="/static/favicon.ico",
            swagger_ui_parameters={
                "persistAuthorization": True,
                "displayRequestDuration": True,
                "filter": True
            }
        )
    
    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc():
        """
        Custom ReDoc documentation.
        """
        return get_redoc_html(
            openapi_url="/openapi.json",
            title=f"{__api_title__} - ReDoc",
            redoc_favicon_url="/static/favicon.ico"
        )
    
    @app.get("/openapi.json", include_in_schema=False)
    async def custom_openapi():
        """
        Custom OpenAPI schema with security.
        """
        return JSONResponse(app.openapi())


# ============================================================================
# Static Files (if needed)
# ============================================================================

if settings.SERVE_STATIC_FILES:
    from fastapi.staticfiles import StaticFiles
    import os
    
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============================================================================
# Custom Exception Handlers
# ============================================================================

@app.exception_handler(BaseAppException)
async def base_app_exception_handler(request, exc: BaseAppException):
    """
    Handle custom application exceptions.
    """
    logger.warning(f"Application exception: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """
    Handle 404 errors.
    """
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "NOT_FOUND",
                "message": f"Endpoint '{request.url.path}' not found",
                "status_code": 404,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


@app.exception_handler(405)
async def method_not_allowed_handler(request, exc):
    """
    Handle 405 errors.
    """
    return JSONResponse(
        status_code=405,
        content={
            "error": {
                "code": "METHOD_NOT_ALLOWED",
                "message": f"Method '{request.method}' not allowed for '{request.url.path}'",
                "status_code": 405,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )


@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    """
    Handle 500 errors.
    """
    logger.error(f"Internal server error: {str(exc)}", exc_info=True)
    
    error_response = {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    # Include error details in development
    if settings.DEBUG:
        error_response["error"]["details"] = {
            "exception": str(exc),
            "type": exc.__class__.__name__
        }
    
    return JSONResponse(
        status_code=500,
        content=error_response
    )


# ============================================================================
# Custom OpenAPI Schema
# ============================================================================

def custom_openapi():
    """
    Custom OpenAPI schema with security definitions.
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=__api_title__,
        version=__version__,
        description=__api_description__,
        routes=app.routes,
        tags=app.openapi_tags
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT token from /auth/login endpoint"
        },
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service communication"
        }
    }
    
    # Apply security globally
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    # Add server information
    openapi_schema["servers"] = [
        {
            "url": "https://api.parking-management.com",
            "description": "Production server"
        },
        {
            "url": "https://staging.api.parking-management.com",
            "description": "Staging server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ]
    
    # Add external documentation
    openapi_schema["externalDocs"] = {
        "description": "Find more info here",
        "url": "https://docs.parking-management.com"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================================
# Startup and Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Legacy startup event handler.
    """
    # Note: Using lifespan context manager instead
    pass


@app.on_event("shutdown")
async def shutdown_event():
    """
    Legacy shutdown event handler.
    """
    # Note: Using lifespan context manager instead
    pass


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    """
    Main entry point for running the application.
    """
    import uvicorn
    
    logger.info(f"Starting {__api_title__} v{__version__}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Host: {settings.HOST}:{settings.PORT}")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        proxy_headers=True,
        forwarded_allow_ips="*",
        timeout_keep_alive=30,
        limit_max_requests=1000
    )


if __name__ == "__main__":
    main()