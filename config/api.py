"""API configuration settings."""

from typing import Dict, List, Any
from pydantic import BaseSettings, Field

from . import config


class APIConfig(BaseSettings):
    """API configuration."""
    
    # API settings
    TITLE: str = config.APP_NAME
    VERSION: str = config.APP_VERSION
    DESCRIPTION: str = config.APP_DESCRIPTION
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"
    
    # Server settings
    HOST: str = config.API_HOST
    PORT: int = config.API_PORT
    WORKERS: int = config.API_WORKERS
    TIMEOUT: int = config.API_TIMEOUT
    
    # Middleware
    MIDDLEWARE: List[str] = [
        "app.middleware.cors.CORSMiddleware",
        "app.middleware.request_id.RequestIDMiddleware",
        "app.middleware.logging.LoggingMiddleware",
        "app.middleware.rate_limit.RateLimitMiddleware",
        "app.middleware.db_session.DBSessionMiddleware",
    ]
    
    # Exception handlers
    EXCEPTION_HANDLERS: Dict[int, str] = {
        400: "app.exceptions.handlers.bad_request_handler",
        401: "app.exceptions.handlers.unauthorized_handler",
        403: "app.exceptions.handlers.forbidden_handler",
        404: "app.exceptions.handlers.not_found_handler",
        422: "app.exceptions.handlers.validation_handler",
        429: "app.exceptions.handlers.rate_limit_handler",
        500: "app.exceptions.handlers.server_error_handler",
    }
    
    # Routes
    ROUTE_PREFIXES: Dict[str, str] = {
        "auth": "/auth",
        "users": "/users",
        "reservations": "/reservations",
        "spots": "/spots",
        "vehicles": "/vehicles",
        "payments": "/payments",
        "waitlist": "/waitlist",
        "admin": "/admin",
        "webhooks": "/webhooks",
    }
    
    # Response headers
    RESPONSE_HEADERS: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
    }


api_config = APIConfig()