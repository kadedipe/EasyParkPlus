"""Swagger/OpenAPI configuration."""

from typing import Dict, Any

from . import config


class SwaggerConfig:
    """Swagger/OpenAPI configuration."""
    
    # Basic info
    TITLE: str = config.APP_NAME
    VERSION: str = config.APP_VERSION
    DESCRIPTION: str = config.APP_DESCRIPTION
    
    # Contact info
    CONTACT: Dict[str, str] = {
        "name": "Parking System Team",
        "email": "support@parking.com",
        "url": "https://parking.com",
    }
    
    # License info
    LICENSE: Dict[str, str] = {
        "name": "Proprietary",
        "url": "https://parking.com/license",
    }
    
    # Server URLs
    SERVERS: List[Dict[str, str]] = [
        {
            "url": f"http://localhost:{config.API_PORT}",
            "description": "Local development server",
        },
        {
            "url": "https://api.staging.parking.com",
            "description": "Staging server",
        },
        {
            "url": "https://api.parking.com",
            "description": "Production server",
        },
    ]
    
    # Security schemes
    SECURITY_SCHEMES: Dict[str, Any] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        },
    }
    
    # Default security
    SECURITY: List[Dict[str, List[str]]] = [
        {"BearerAuth": []}
    ]
    
    # Tags
    TAGS: List[Dict[str, str]] = [
        {
            "name": "auth",
            "description": "Authentication operations",
        },
        {
            "name": "users",
            "description": "User management",
        },
        {
            "name": "reservations",
            "description": "Reservation management",
        },
        {
            "name": "spots",
            "description": "Parking spot management",
        },
        {
            "name": "vehicles",
            "description": "Vehicle management",
        },
        {
            "name": "payments",
            "description": "Payment processing",
        },
        {
            "name": "waitlist",
            "description": "Waitlist management",
        },
        {
            "name": "admin",
            "description": "Admin operations",
        },
    ]
    
    # OpenAPI documentation URLs
    DOCS_URL: str = config.DOCS_URL
    REDOC_URL: str = config.REDOC_URL
    OPENAPI_URL: str = config.OPENAPI_URL


swagger_config = SwaggerConfig()