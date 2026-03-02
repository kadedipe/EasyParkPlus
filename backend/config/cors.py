"""CORS configuration."""

from typing import List

from . import config


class CORSConfig:
    """CORS configuration."""
    
    # Allow origins
    ALLOW_ORIGINS: List[str] = config.CORS_ALLOW_ORIGINS
    
    # Allow methods
    ALLOW_METHODS: List[str] = config.CORS_ALLOW_METHODS
    
    # Allow headers
    ALLOW_HEADERS: List[str] = config.CORS_ALLOW_HEADERS
    
    # Allow credentials
    ALLOW_CREDENTIALS: bool = config.CORS_ALLOW_CREDENTIALS
    
    # Expose headers
    EXPOSE_HEADERS: List[str] = [
        'Content-Length',
        'X-Request-ID',
        'X-RateLimit-Limit',
        'X-RateLimit-Remaining',
        'X-RateLimit-Reset',
    ]
    
    # Max age for preflight requests
    MAX_AGE: int = 600  # 10 minutes
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed."""
        if '*' in self.ALLOW_ORIGINS:
            return True
        
        return origin in self.ALLOW_ORIGINS


cors_config = CORSConfig()