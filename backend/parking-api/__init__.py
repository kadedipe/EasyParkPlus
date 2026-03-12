"""
Parking Management System API Package
=====================================

A comprehensive RESTful API for managing parking facilities, reservations, payments,
and user accounts. This package provides all the backend functionality needed for
a modern parking management system.

Features:
    - User authentication and authorization (JWT-based)
    - Parking spot management and real-time availability
    - Reservation system with conflict detection
    - Payment processing with multiple payment gateways
    - Vehicle registration and management
    - Review and rating system
    - Waitlist management for popular spots
    - Admin dashboard and analytics
    - Audit logging for compliance
    - Rate limiting and security features
    - WebSocket support for real-time updates
    - Comprehensive API documentation

Version: 1.0.0
Author: Parking Management Team
License: Proprietary
"""

__version__ = "1.0.0"
__author__ = "Parking Management Team"
__license__ = "Proprietary"
__copyright__ = "Copyright 2024 Parking Management System"

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import importlib.metadata

# Package metadata
PACKAGE_NAME = "parking-api"
PACKAGE_VERSION = __version__
PACKAGE_DESCRIPTION = "Parking Management System Backend API"
PACKAGE_URL = "https://github.com/yourcompany/parking-management"
PACKAGE_AUTHOR = __author__
PACKAGE_EMAIL = "dev@parking-management.com"

# Export public interface
__all__ = [
    # Version info
    '__version__',
    '__author__',
    '__license__',
    '__copyright__',
    
    # Package info
    'get_version',
    'get_package_info',
    'get_dependencies',
    
    # Core components
    'create_app',
    'get_settings',
    'setup_logging',
    
    # Models and schemas
    'models',
    'schemas',
    
    # Utilities
    'get_api_info',
    'health_check',
    'get_routes'
]

# Setup module-level logger
logger = logging.getLogger(__name__)


def get_version() -> str:
    """
    Get the current version of the API package.
    
    Returns:
        str: Version string in semantic versioning format
    """
    try:
        return importlib.metadata.version(PACKAGE_NAME)
    except importlib.metadata.PackageNotFoundError:
        return __version__


def get_package_info() -> Dict[str, Any]:
    """
    Get comprehensive package information.
    
    Returns:
        Dict containing package metadata and configuration
    """
    return {
        "name": PACKAGE_NAME,
        "version": get_version(),
        "description": PACKAGE_DESCRIPTION,
        "author": PACKAGE_AUTHOR,
        "author_email": PACKAGE_EMAIL,
        "url": PACKAGE_URL,
        "license": __license__,
        "copyright": __copyright__,
        "python_version": importlib.metadata.version("python"),
        "fastapi_version": importlib.metadata.version("fastapi"),
        "environment": getattr(__import__('core.config'), 'settings', {}).get('ENVIRONMENT', 'unknown'),
        "release_date": datetime.utcnow().isoformat(),
        "dependencies": get_dependencies()
    }


def get_dependencies() -> List[Dict[str, str]]:
    """
    Get list of package dependencies with versions.
    
    Returns:
        List of dictionaries with dependency names and versions
    """
    core_dependencies = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "alembic",
        "pydantic",
        "python-jose",
        "passlib",
        "python-multipart",
        "httpx",
        "redis",
        "celery",
        "prometheus-client",
        "loguru",
        "python-dotenv"
    ]
    
    dependencies = []
    for dep in core_dependencies:
        try:
            version = importlib.metadata.version(dep)
            dependencies.append({"name": dep, "version": version})
        except importlib.metadata.PackageNotFoundError:
            dependencies.append({"name": dep, "version": "not installed"})
    
    return dependencies


def create_app() -> 'FastAPI':
    """
    Factory function to create and configure a FastAPI application instance.
    
    This is the main entry point for creating the API application. It handles:
        - Loading configuration
        - Setting up middleware
        - Registering routes
        - Configuring error handlers
        - Initializing services
    
    Returns:
        FastAPI: Configured FastAPI application instance
    
    Example:
        >>> from parking_api import create_app
        >>> app = create_app()
        >>> uvicorn.run(app, host="0.0.0.0", port=8000)
    """
    from .main import app
    return app


def get_settings() -> Dict[str, Any]:
    """
    Get application settings and configuration.
    
    Returns:
        Dict containing all application settings
    """
    from .core.config import settings
    return settings.dict()


def setup_logging(level: Optional[str] = None) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Optional logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               If not provided, uses settings.LOG_LEVEL
    """
    from .core.logging import setup_logging as _setup_logging
    _setup_logging(level)


def get_api_info() -> Dict[str, Any]:
    """
    Get API information for documentation and discovery.
    
    Returns:
        Dict containing API metadata and available endpoints
    """
    from .api import __api_title__, __api_description__
    from .core.config import settings
    
    return {
        "title": __api_title__,
        "description": __api_description__,
        "version": __version__,
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs" if settings.ENVIRONMENT != "production" else "/docs",
        "openapi_url": "/openapi.json" if settings.ENVIRONMENT != "production" else "/openapi.json",
        "health_endpoint": "/health",
        "metrics_endpoint": "/metrics",
        "api_version": "v1",
        "base_url": f"https://api.parking-management.com/api/v1",
        "supported_formats": ["json"],
        "authentication": ["bearer", "api_key"],
        "rate_limits": {
            "default": "100/minute",
            "authenticated": "1000/minute",
            "admin": "5000/minute"
        }
    }


def health_check() -> Dict[str, Any]:
    """
    Quick health check for the package.
    
    Returns:
        Dict with health status and basic system information
    """
    import platform
    import sys
    
    return {
        "status": "healthy",
        "package": PACKAGE_NAME,
        "version": __version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "timestamp": datetime.utcnow().isoformat()
    }


def get_routes() -> List[Dict[str, str]]:
    """
    Get all registered API routes.
    
    Returns:
        List of dictionaries with route information
    """
    try:
        from .main import app
        routes = []
        for route in app.routes:
            route_info = {
                "path": getattr(route, "path", str(route)),
                "name": getattr(route, "name", "unknown"),
                "methods": list(getattr(route, "methods", [])) if hasattr(route, "methods") else []
            }
            routes.append(route_info)
        return routes
    except Exception as e:
        logger.error(f"Error getting routes: {str(e)}")
        return []


# Initialize logging when package is imported
try:
    setup_logging()
    logger.debug(f"Parking API package v{__version__} initialized")
except Exception as e:
    # Fallback to basic logging if setup fails
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to setup custom logging: {str(e)}")


# Package initialization message
logger.info(f"🚗 Parking Management API v{__version__} loaded")
logger.info(f"📚 Documentation available at /docs when running")


# ============================================================================
# Convenience imports for common components
# ============================================================================

# Allow direct imports from the package
# e.g., from parking_api import models, schemas, crud

def __getattr__(name):
    """
    Lazy load submodules to improve import performance.
    """
    if name == 'models':
        from . import models
        return models
    elif name == 'schemas':
        from . import schemas
        return schemas
    elif name == 'crud':
        from . import crud
        return crud
    elif name == 'core':
        from . import core
        return core
    elif name == 'api':
        from . import api
        return api
    elif name == 'services':
        from . import services
        return services
    elif name == 'utils':
        from . import utils
        return utils
    elif name == 'db':
        from . import db
        return db
    elif name == 'tests':
        from . import tests
        return tests
    else:
        raise AttributeError(f"module {__name__} has no attribute {name}")


# Define what should be available for wildcard imports
__all__ = [
    # Version and metadata
    '__version__',
    '__author__',
    '__license__',
    '__copyright__',
    
    # Main factory
    'create_app',
    
    # Utilities
    'get_version',
    'get_package_info',
    'get_dependencies',
    'get_settings',
    'get_api_info',
    'health_check',
    'get_routes',
    'setup_logging',
    
    # Submodules (will be lazy loaded)
    'models',
    'schemas',
    'crud',
    'core',
    'api',
    'services',
    'utils',
    'db',
    'tests'
]