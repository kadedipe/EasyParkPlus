"""Redis configuration and client management."""

import redis
from redis import Redis
from redis.connection import ConnectionPool
from typing import Optional, Any
import logging
import json

from . import config

logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis connection configuration."""
    
    def __init__(self):
        self.pool = None
        self.client = None
        self._setup_connection()
    
    def _setup_connection(self):
        """Setup Redis connection pool."""
        pool_kwargs = {
            'host': config.REDIS_HOST,
            'port': config.REDIS_PORT,
            'db': config.REDIS_DB,
            'socket_timeout': 5,
            'socket_connect_timeout': 5,
            'retry_on_timeout': True,
            'max_connections': 20,
            'health_check_interval': 30
        }
        
        if config.REDIS_PASSWORD:
            pool_kwargs['password'] = config.REDIS_PASSWORD
        
        if config.REDIS_SSL:
            pool_kwargs['ssl'] = True
            pool_kwargs['ssl_cert_reqs'] = None
        
        self.pool = ConnectionPool(**pool_kwargs)
        self.client = Redis(connection_pool=self.pool)
        
        # Test connection
        try:
            self.client.ping()
            logger.info(f"Redis connected to {config.REDIS_HOST}:{config.REDIS_PORT}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            if not config.TESTING:
                raise
    
    def get_client(self) -> Redis:
        """Get Redis client."""
        return self.client
    
    def close(self):
        """Close Redis connection."""
        if self.pool:
            self.pool.disconnect()
            logger.info("Redis connection closed")


class RedisCache:
    """Redis cache wrapper."""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.prefix = config.CACHE_KEY_PREFIX
        self.default_ttl = config.CACHE_DEFAULT_TIMEOUT
    
    def _key(self, key: str) -> str:
        """Get namespaced key."""
        return f"{self.prefix}{key}"
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        try:
            value = self.redis.get(self._key(key))
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            ttl = ttl or self.default_ttl
            return self.redis.setex(
                self._key(key),
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete from cache."""
        try:
            return bool(self.redis.delete(self._key(key)))
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        try:
            keys = self.redis.keys(self._key(pattern))
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return self.redis.exists(self._key(key)) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key."""
        try:
            return self.redis.expire(self._key(key), ttl)
        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """Get TTL for key."""
        try:
            return self.redis.ttl(self._key(key))
        except Exception as e:
            logger.error(f"Cache ttl error: {e}")
            return -2


# Global Redis instances
redis_config = RedisConfig()
redis_client = redis_config.get_client()
cache = RedisCache(redis_client)