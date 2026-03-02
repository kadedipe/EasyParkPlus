"""Configuration package for the parking management system.

This package provides environment-specific configuration management
with support for development, testing, staging, and production environments.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment detection
ENVIRONMENT = os.getenv('PARKING_ENV', 'development').lower()


def get_config():
    """Get configuration based on current environment."""
    if ENVIRONMENT == 'production':
        from .production import ProductionConfig
        return ProductionConfig()
    elif ENVIRONMENT == 'staging':
        from .staging import StagingConfig
        return StagingConfig()
    elif ENVIRONMENT == 'testing':
        from .testing import TestingConfig
        return TestingConfig()
    else:
        from .development import DevelopmentConfig
        return DevelopmentConfig()


# Global config instance
config = get_config()


__all__ = [
    'config',
    'ENVIRONMENT',
    'get_config',
]