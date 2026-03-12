"""
Main FastAPI application factory.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from . import __version__, __api_title__, __api_description__
from .v1.api import api_router as api_v1_router
from .v1.middlewares.setup import setup_middlewares, setup_exception_handlers
from ..core.config import settings
from ..core.events import startup_handler, shutdown_handler
from ..utils.logger import logger


def create_application() -> FastAPI:
    """
    Create FastAPI application instance.
    """
    # Create FastAPI app
    app = FastAPI(
        title=__api_title__,
        description=__api_description__,
        version=__version__,
        docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
        redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
        openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json",
        contact={
            "name": "API Support",
            "email": "api-support@parking-management.com",
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
                "description": "User authentication and authorization operations"
            },
            {
                "name": "users",
                "description": "User profile and account management"
            },
            {
                "name": "vehicles",
                "description": "Vehicle registration and management"
            },
            {
                "name": "parking",
                "description": "Parking spot availability and information"
            },
            {
                "name": "reservations",
                "description": "Parking reservation management"
            },
            {
                "name": "payments",
                "description": "Payment processing and transaction history"
            },
            {
                "name": "reviews",
                "description": "Parking spot reviews and ratings"
            },
            {
                "name": "waitlist",
                "description": "Waitlist management for unavailable spots"
            },
            {
                "name": "admin",
                "description": "Administrative operations (requires admin privileges)"
            },
            {
                "name": "health",
                "description": "Health check endpoints"
            }
        ]
    )
    
    # Setup CORS
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
            "X-RateLimit-Reset"
        ]
    )
    
    # Setup all middlewares
    setup_middlewares(app)
    
    # Setup exception handlers
    setup_exception_handlers(app)
    
    # Include API routers
    app.include_router(api_v1_router, prefix="/api/v1")
    
    # Register event handlers
    app.add_event_handler("startup", startup_handler)
    app.add_event_handler("shutdown", shutdown_handler)
    
    # Custom documentation routes for production
    if settings.ENVIRONMENT == "production":
        
        @app.get("/docs", include_in_schema=False)
        async def custom_swagger_ui():
            return get_swagger_ui_html(
                openapi_url="/openapi.json",
                title=f"{__api_title__} - Documentation",
                swagger_favicon_url="/static/favicon.ico"
            )
        
        @app.get("/redoc", include_in_schema=False)
        async def custom_redoc():
            return get_redoc_html(
                openapi_url="/openapi.json",
                title=f"{__api_title__} - ReDoc",
                redoc_favicon_url="/static/favicon.ico"
            )
    
    # Root endpoint
    @app.get("/", tags=["root"])
    async def root():
        """
        API root endpoint with service information.
        """
        return {
            "service": __api_title__,
            "version": __version__,
            "environment": settings.ENVIRONMENT,
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json"
            },
            "health": "/health",
            "status": "operational"
        }
    
    # Custom OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=__api_title__,
            version=__version__,
            description=__api_description__,
            routes=app.routes,
            tags=app.openapi_tags
        )
        
        # Add security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter JWT token"
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
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    # Log application startup
    logger.info(f"Application created: {__api_title__} v{__version__}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    return app


# Create application instance
app = create_application()