"""Cache configuration."""

from typing import Optional, Any
from . import config


class CacheConfig:
    """Cache configuration."""
    
    # Cache type: redis, memory, null
    TYPE: str = config.CACHE_TYPE
    
    # Default TTL in seconds
    DEFAULT_TIMEOUT: int = config.CACHE_DEFAULT_TIMEOUT
    
    # Key prefix
    KEY_PREFIX: str = config.CACHE_KEY_PREFIX
    
    # Redis specific settings
    REDIS_URL: str = config.REDIS_URL
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    REDIS_RETRY_ON_TIMEOUT: bool = True
    REDIS_MAX_CONNECTIONS: int = 20
    REDIS_HEALTH_CHECK_INTERVAL: int = 30
    
    # Memory cache settings
    MEMORY_MAX_ENTRIES: int = 1000
    MEMORY_CLEANUP_INTERVAL: int = 60
    
    # Cache key patterns
    KEYS: dict = {
        'user': 'user:{id}',
        'reservation': 'reservation:{id}',
        'spot': 'spot:{id}',
        'vehicle': 'vehicle:{id}',
        'user_reservations': 'user:{user_id}:reservations',
        'spot_availability': 'spot:{spot_id}:availability:{date}',
        'stats': 'stats:{type}:{period}',
        'session': 'session:{session_id}',
        'rate_limit': 'rate_limit:{key}:{type}',
    }
    
    # Cache TTLs by key type (in seconds)
    TTL: dict = {
        'user': 3600,  # 1 hour
        'reservation': 300,  # 5 minutes
        'spot': 300,  # 5 minutes
        'vehicle': 1800,  # 30 minutes
        'user_reservations': 300,  # 5 minutes
        'spot_availability': 60,  # 1 minute
        'stats': 1800,  # 30 minutes
        'session': 7200,  # 2 hours
        'rate_limit': 60,  # 1 minute
    }
    
    def get_key(self, key_type: str, **kwargs) -> str:
        """Get cache key with prefix."""
        if key_type not in self.KEYS:
            raise ValueError(f"Unknown key type: {key_type}")
        
        key = self.KEYS[key_type].format(**kwargs)
        return f"{self.KEY_PREFIX}{key}"
    
    def get_ttl(self, key_type: str) -> int:
        """Get TTL for key type."""
        return self.TTL.get(key_type, self.DEFAULT_TIMEOUT)


cache_config = CacheConfig()