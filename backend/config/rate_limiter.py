"""Rate limiting configuration."""

from typing import Dict, Any

from . import config


class RateLimiterConfig:
    """Rate limiting configuration."""
    
    # Global settings
    ENABLED: bool = config.RATE_LIMIT_ENABLED
    DEFAULT_LIMIT: str = config.RATE_LIMIT_DEFAULT
    STRICT_LIMIT: str = config.RATE_LIMIT_STRICT
    
    # Storage backend
    STORAGE: str = 'redis'  # redis, memory
    
    # Redis settings
    REDIS_URL: str = config.REDIS_URL
    REDIS_KEY_PREFIX: str = 'ratelimit:'
    
    # Memory cache settings
    MEMORY_MAX_ENTRIES: int = 10000
    MEMORY_CLEANUP_INTERVAL: int = 60
    
    # Rate limits by endpoint
    ENDPOINT_LIMITS: Dict[str, str] = {
        # Auth endpoints
        '/auth/login': '5/minute',
        '/auth/register': '3/minute',
        '/auth/refresh': '10/minute',
        '/auth/logout': '10/minute',
        '/auth/verify': '5/minute',
        '/auth/reset-password': '3/hour',
        
        # API endpoints
        '/api/reservations': '100/minute',
        '/api/reservations/{id}': '100/minute',
        '/api/spots': '200/minute',
        '/api/spots/search': '100/minute',
        '/api/users/me': '100/minute',
        '/api/vehicles': '100/minute',
        '/api/payments': '50/minute',
        '/api/waitlist': '50/minute',
        
        # Admin endpoints
        '/api/admin/*': '20/minute',
        
        # Public endpoints
        '/health': '1000/minute',
        '/metrics': '10/minute',
    }
    
    # Rate limits by user role
    ROLE_LIMITS: Dict[str, str] = {
        'anonymous': '10/minute',
        'customer': '100/minute',
        'vip_customer': '200/minute',
        'attendant': '300/minute',
        'manager': '500/minute',
        'admin': '1000/minute',
    }
    
    # Rate limit headers
    HEADERS: Dict[str, str] = {
        'limit': 'X-RateLimit-Limit',
        'remaining': 'X-RateLimit-Remaining',
        'reset': 'X-RateLimit-Reset',
    }
    
    def get_limit_for_endpoint(self, endpoint: str) -> str:
        """Get rate limit for endpoint."""
        # Check exact match
        if endpoint in self.ENDPOINT_LIMITS:
            return self.ENDPOINT_LIMITS[endpoint]
        
        # Check wildcard patterns
        for pattern, limit in self.ENDPOINT_LIMITS.items():
            if pattern.endswith('*') and endpoint.startswith(pattern[:-1]):
                return limit
        
        return self.DEFAULT_LIMIT
    
    def get_limit_for_role(self, role: str) -> str:
        """Get rate limit for role."""
        return self.ROLE_LIMITS.get(role, self.ROLE_LIMITS['anonymous'])


rate_limiter_config = RateLimiterConfig()