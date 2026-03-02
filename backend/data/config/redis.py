"""Redis configuration and client management for the parking management system.

This module provides Redis connection management, client factories, and
specialized Redis clients for different use cases (caching, rate limiting,
session storage, etc.).
"""

import os
import json
import pickle
import logging
from typing import Any, Optional, Union, Dict, List, Callable
from datetime import timedelta, datetime
from contextlib import contextmanager
from functools import wraps
import hashlib

import redis
from redis import Redis
from redis.cluster import RedisCluster
from redis.sentinel import Sentinel
from redis.connection import ConnectionPool
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from . import config, get_current_environment, is_testing

# Set up logging
logger = logging.getLogger(__name__)


# ============================================================================
# Redis Connection Configuration
# ============================================================================

class RedisConfig:
    """Redis connection configuration."""
    
    def __init__(self, **kwargs):
        """Initialize Redis configuration with defaults from main config."""
        self.host = kwargs.get('host', config.REDIS.host)
        self.port = kwargs.get('port', config.REDIS.port)
        self.db = kwargs.get('db', config.REDIS.db)
        self.password = kwargs.get('password', config.REDIS.password)
        self.ssl = kwargs.get('ssl', config.REDIS.ssl)
        self.socket_timeout = kwargs.get('socket_timeout', config.REDIS.socket_timeout)
        self.socket_connect_timeout = kwargs.get('socket_connect_timeout', 
                                                config.REDIS.socket_connect_timeout)
        self.retry_on_timeout = kwargs.get('retry_on_timeout', config.REDIS.retry_on_timeout)
        self.max_connections = kwargs.get('max_connections', config.REDIS.max_connections)
        
        # Additional options
        self.decode_responses = kwargs.get('decode_responses', False)
        self.health_check_interval = kwargs.get('health_check_interval', 30)
        self.ssl_certfile = kwargs.get('ssl_certfile', None)
        self.ssl_keyfile = kwargs.get('ssl_keyfile', None)
        self.ssl_ca_certs = kwargs.get('ssl_ca_certs', None)
        
        # Cluster/Sentinel options
        self.use_cluster = kwargs.get('use_cluster', False)
        self.use_sentinel = kwargs.get('use_sentinel', False)
        self.sentinel_hosts = kwargs.get('sentinel_hosts', [])
        self.sentinel_master_name = kwargs.get('sentinel_master_name', 'mymaster')
        self.cluster_nodes = kwargs.get('cluster_nodes', [])
        
        # Connection pool options
        self.pool_class = kwargs.get('pool_class', ConnectionPool)
        self.connection_class = kwargs.get('connection_class', None)
        
    @property
    def url(self) -> str:
        """Get Redis URL."""
        if self.use_cluster or self.use_sentinel:
            return "redis://{host}:{port}/{db}".format(
                host=self.host,
                port=self.port,
                db=self.db
            )
        
        protocol = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{protocol}://{auth}{self.host}:{self.port}/{self.db}"
    
    def get_connection_kwargs(self) -> Dict[str, Any]:
        """Get connection keyword arguments for Redis client."""
        kwargs = {
            'host': self.host,
            'port': self.port,
            'db': self.db,
            'socket_timeout': self.socket_timeout,
            'socket_connect_timeout': self.socket_connect_timeout,
            'socket_keepalive': True,
            'retry_on_timeout': self.retry_on_timeout,
            'health_check_interval': self.health_check_interval,
            'max_connections': self.max_connections,
        }
        
        if self.password:
            kwargs['password'] = self.password
        
        if self.ssl:
            kwargs['ssl'] = True
            kwargs['ssl_certfile'] = self.ssl_certfile
            kwargs['ssl_keyfile'] = self.ssl_keyfile
            kwargs['ssl_ca_certs'] = self.ssl_ca_certs
        
        if self.decode_responses:
            kwargs['decode_responses'] = True
        
        if self.connection_class:
            kwargs['connection_class'] = self.connection_class
        
        return kwargs


# ============================================================================
# Connection Pool Management
# ============================================================================

class RedisConnectionPool:
    """Singleton manager for Redis connection pools."""
    
    _instances: Dict[str, ConnectionPool] = {}
    _clients: Dict[str, Redis] = {}
    
    @classmethod
    def get_pool(cls, config: Optional[RedisConfig] = None, name: str = "default") -> ConnectionPool:
        """Get or create a connection pool."""
        if name not in cls._instances:
            if config is None:
                config = RedisConfig()
            
            cls._instances[name] = ConnectionPool(**config.get_connection_kwargs())
            logger.info(f"Created Redis connection pool '{name}'")
        
        return cls._instances[name]
    
    @classmethod
    def get_client(cls, config: Optional[RedisConfig] = None, name: str = "default") -> Redis:
        """Get or create a Redis client."""
        if name not in cls._clients:
            pool = cls.get_pool(config, name)
            cls._clients[name] = Redis(connection_pool=pool)
            logger.info(f"Created Redis client '{name}'")
        
        return cls._clients[name]
    
    @classmethod
    def close_all(cls):
        """Close all connection pools."""
        for name, pool in cls._instances.items():
            try:
                pool.disconnect()
                logger.info(f"Disconnected Redis pool '{name}'")
            except Exception as e:
                logger.error(f"Error disconnecting Redis pool '{name}': {e}")
        
        cls._instances.clear()
        cls._clients.clear()


# ============================================================================
# Specialized Redis Clients
# ============================================================================

class CacheClient:
    """Redis client for caching operations."""
    
    def __init__(self, client: Optional[Redis] = None, namespace: str = "cache"):
        """Initialize cache client."""
        self.client = client or RedisConnectionPool.get_client(name="cache")
        self.namespace = namespace
        self.default_ttl = config.CACHE.default_timeout
    
    def _key(self, key: str) -> str:
        """Get namespaced key."""
        return f"{config.CACHE.key_prefix}{self.namespace}:{key}"
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache."""
        try:
            value = self.client.get(self._key(key))
            if value is None:
                return default
            
            # Try to deserialize
            try:
                return pickle.loads(value)
            except (pickle.PickleError, TypeError):
                return value.decode('utf-8') if isinstance(value, bytes) else value
                
        except RedisError as e:
            logger.warning(f"Redis get error for key '{key}': {e}")
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            # Serialize if needed
            if not isinstance(value, (str, bytes, int, float)):
                value = pickle.dumps(value)
            
            ttl = ttl or self.default_ttl
            return bool(self.client.setex(self._key(key), ttl, value))
            
        except RedisError as e:
            logger.warning(f"Redis set error for key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            return bool(self.client.delete(self._key(key)))
        except RedisError as e:
            logger.warning(f"Redis delete error for key '{key}': {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(self.client.exists(self._key(key)))
        except RedisError as e:
            logger.warning(f"Redis exists error for key '{key}': {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter."""
        try:
            return self.client.incrby(self._key(key), amount)
        except RedisError as e:
            logger.warning(f"Redis increment error for key '{key}': {e}")
            return None
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key."""
        try:
            return bool(self.client.expire(self._key(key), ttl))
        except RedisError as e:
            logger.warning(f"Redis expire error for key '{key}': {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """Get TTL for key."""
        try:
            return self.client.ttl(self._key(key))
        except RedisError as e:
            logger.warning(f"Redis ttl error for key '{key}': {e}")
            return -2
    
    def clear_namespace(self) -> bool:
        """Clear all keys in namespace."""
        try:
            pattern = f"{config.CACHE.key_prefix}{self.namespace}:*"
            keys = self.client.keys(pattern)
            if keys:
                return bool(self.client.delete(*keys))
            return True
        except RedisError as e:
            logger.warning(f"Redis clear namespace error: {e}")
            return False
    
    def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        try:
            pipe = self.client.pipeline()
            for key in keys:
                pipe.get(self._key(key))
            values = pipe.execute()
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = pickle.loads(value)
                    except (pickle.PickleError, TypeError):
                        result[key] = value.decode('utf-8') if isinstance(value, bytes) else value
            return result
            
        except RedisError as e:
            logger.warning(f"Redis get_many error: {e}")
            return {}
    
    def set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache."""
        try:
            pipe = self.client.pipeline()
            ttl = ttl or self.default_ttl
            
            for key, value in mapping.items():
                if not isinstance(value, (str, bytes, int, float)):
                    value = pickle.dumps(value)
                pipe.setex(self._key(key), ttl, value)
            
            results = pipe.execute()
            return all(results)
            
        except RedisError as e:
            logger.warning(f"Redis set_many error: {e}")
            return False


class RateLimiter:
    """Redis-based rate limiter."""
    
    def __init__(self, client: Optional[Redis] = None):
        """Initialize rate limiter."""
        self.client = client or RedisConnectionPool.get_client(name="rate_limiter")
    
    def _key(self, identifier: str, limit_type: str) -> str:
        """Get rate limiter key."""
        return f"{config.CACHE.key_prefix}ratelimit:{limit_type}:{identifier}"
    
    def check(self, identifier: str, limit_type: str, max_requests: int, window: int) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            identifier: Unique identifier (IP, user ID, etc.)
            limit_type: Type of limit (api, login, etc.)
            max_requests: Maximum requests allowed in window
            window: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        key = self._key(identifier, limit_type)
        
        try:
            # Use pipeline for atomic operation
            pipe = self.client.pipeline()
            now = datetime.now().timestamp()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, now - window)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Count requests in window
            pipe.zcard(key)
            
            # Set expiry
            pipe.expire(key, window)
            
            _, _, count, _ = pipe.execute()
            
            return count <= max_requests
            
        except RedisError as e:
            logger.warning(f"Rate limiter check error: {e}")
            # Fail open in case of Redis error
            return True
    
    def remaining(self, identifier: str, limit_type: str, max_requests: int, window: int) -> int:
        """Get remaining requests allowed."""
        key = self._key(identifier, limit_type)
        
        try:
            now = datetime.now().timestamp()
            self.client.zremrangebyscore(key, 0, now - window)
            count = self.client.zcard(key)
            return max(0, max_requests - count)
            
        except RedisError as e:
            logger.warning(f"Rate limiter remaining error: {e}")
            return max_requests
    
    def reset(self, identifier: str, limit_type: str) -> bool:
        """Reset rate limit for identifier."""
        key = self._key(identifier, limit_type)
        
        try:
            return bool(self.client.delete(key))
        except RedisError as e:
            logger.warning(f"Rate limiter reset error: {e}")
            return False
    
    def get_window_stats(self, identifier: str, limit_type: str, window: int) -> Dict[str, Any]:
        """Get statistics for current window."""
        key = self._key(identifier, limit_type)
        
        try:
            now = datetime.now().timestamp()
            self.client.zremrangebyscore(key, 0, now - window)
            
            count = self.client.zcard(key)
            
            # Get oldest request in window
            oldest = self.client.zrange(key, 0, 0, withscores=True)
            reset_time = None
            if oldest:
                reset_time = oldest[0][1] + window
            
            return {
                'count': count,
                'window_start': now - window,
                'window_end': now,
                'reset_time': reset_time,
                'remaining': max(0, window - count)
            }
            
        except RedisError as e:
            logger.warning(f"Rate limiter stats error: {e}")
            return {}


class SessionStore:
    """Redis-based session storage."""
    
    def __init__(self, client: Optional[Redis] = None):
        """Initialize session store."""
        self.client = client or RedisConnectionPool.get_client(name="sessions")
        self.default_ttl = config.AUTH.session_max_age
    
    def _key(self, session_id: str) -> str:
        """Get session key."""
        return f"{config.CACHE.key_prefix}session:{session_id}"
    
    def create(self, session_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Create a new session."""
        try:
            key = self._key(session_id)
            value = json.dumps(data)
            ttl = ttl or self.default_ttl
            return bool(self.client.setex(key, ttl, value))
        except RedisError as e:
            logger.warning(f"Session create error: {e}")
            return False
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        try:
            value = self.client.get(self._key(session_id))
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Session get error: {e}")
            return None
    
    def update(self, session_id: str, data: Dict[str, Any]) -> bool:
        """Update session data."""
        try:
            key = self._key(session_id)
            ttl = self.client.ttl(key)
            if ttl > 0:
                value = json.dumps(data)
                return bool(self.client.setex(key, ttl, value))
            return False
        except RedisError as e:
            logger.warning(f"Session update error: {e}")
            return False
    
    def delete(self, session_id: str) -> bool:
        """Delete session."""
        try:
            return bool(self.client.delete(self._key(session_id)))
        except RedisError as e:
            logger.warning(f"Session delete error: {e}")
            return False
    
    def touch(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """Extend session expiration."""
        try:
            key = self._key(session_id)
            ttl = ttl or self.default_ttl
            return bool(self.client.expire(key, ttl))
        except RedisError as e:
            logger.warning(f"Session touch error: {e}")
            return False
    
    def exists(self, session_id: str) -> bool:
        """Check if session exists."""
        try:
            return bool(self.client.exists(self._key(session_id)))
        except RedisError as e:
            logger.warning(f"Session exists error: {e}")
            return False


class MessageQueue:
    """Redis-based message queue for background jobs."""
    
    def __init__(self, client: Optional[Redis] = None, queue_name: str = "default"):
        """Initialize message queue."""
        self.client = client or RedisConnectionPool.get_client(name="queue")
        self.queue_name = queue_name
        self.processing_queue = f"{queue_name}:processing"
    
    def _key(self, queue: str) -> str:
        """Get queue key."""
        return f"{config.CACHE.key_prefix}queue:{queue}"
    
    def push(self, message: Any, delay: int = 0) -> bool:
        """Push message to queue."""
        try:
            data = pickle.dumps(message)
            if delay > 0:
                # Delayed message
                score = datetime.now().timestamp() + delay
                return bool(self.client.zadd(self._key(f"{self.queue_name}:delayed"), {data: score}))
            else:
                # Immediate message
                return bool(self.client.lpush(self._key(self.queue_name), data))
        except RedisError as e:
            logger.warning(f"Queue push error: {e}")
            return False
    
    def pop(self, timeout: int = 0) -> Optional[Any]:
        """Pop message from queue."""
        try:
            # Move delayed messages to main queue
            self._process_delayed()
            
            # Pop from queue
            result = self.client.brpoplpush(
                self._key(self.queue_name),
                self._key(self.processing_queue),
                timeout=timeout
            )
            
            if result:
                return pickle.loads(result)
            return None
            
        except (RedisError, pickle.PickleError) as e:
            logger.warning(f"Queue pop error: {e}")
            return None
    
    def ack(self, message: Any) -> bool:
        """Acknowledge message processing (remove from processing queue)."""
        try:
            data = pickle.dumps(message)
            return bool(self.client.lrem(self._key(self.processing_queue), 1, data))
        except (RedisError, pickle.PickleError) as e:
            logger.warning(f"Queue ack error: {e}")
            return False
    
    def _process_delayed(self):
        """Move delayed messages to main queue."""
        try:
            now = datetime.now().timestamp()
            delayed_key = self._key(f"{self.queue_name}:delayed")
            
            # Get ready messages
            ready = self.client.zrangebyscore(delayed_key, 0, now)
            
            if ready:
                pipe = self.client.pipeline()
                for message in ready:
                    pipe.lpush(self._key(self.queue_name), message)
                    pipe.zrem(delayed_key, message)
                pipe.execute()
                
        except RedisError as e:
            logger.warning(f"Process delayed error: {e}")
    
    def size(self) -> int:
        """Get queue size."""
        try:
            return self.client.llen(self._key(self.queue_name))
        except RedisError as e:
            logger.warning(f"Queue size error: {e}")
            return 0
    
    def clear(self) -> bool:
        """Clear queue."""
        try:
            self.client.delete(
                self._key(self.queue_name),
                self._key(self.processing_queue),
                self._key(f"{self.queue_name}:delayed")
            )
            return True
        except RedisError as e:
            logger.warning(f"Queue clear error: {e}")
            return False


class PubSubManager:
    """Redis pub/sub manager."""
    
    def __init__(self, client: Optional[Redis] = None):
        """Initialize pub/sub manager."""
        self.client = client or RedisConnectionPool.get_client(name="pubsub")
        self.pubsub = self.client.pubsub()
        self.handlers: Dict[str, List[Callable]] = {}
    
    def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel."""
        try:
            data = json.dumps(message) if isinstance(message, (dict, list)) else str(message)
            return self.client.publish(channel, data)
        except (RedisError, TypeError) as e:
            logger.warning(f"Publish error: {e}")
            return 0
    
    def subscribe(self, channel: str, handler: Callable):
        """Subscribe to channel with handler."""
        if channel not in self.handlers:
            self.handlers[channel] = []
            self.pubsub.subscribe(**{channel: self._message_handler})
        
        self.handlers[channel].append(handler)
    
    def _message_handler(self, message):
        """Handle incoming messages."""
        channel = message['channel'].decode('utf-8')
        data = message['data']
        
        # Decode data
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            try:
                data = data.decode('utf-8')
            except (AttributeError, UnicodeDecodeError):
                pass
        
        # Call handlers
        for handler in self.handlers.get(channel, []):
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in pubsub handler for {channel}: {e}")
    
    def unsubscribe(self, channel: str, handler: Optional[Callable] = None):
        """Unsubscribe from channel."""
        if channel in self.handlers:
            if handler:
                self.handlers[channel].remove(handler)
                if not self.handlers[channel]:
                    del self.handlers[channel]
                    self.pubsub.unsubscribe(channel)
            else:
                del self.handlers[channel]
                self.pubsub.unsubscribe(channel)
    
    def run_in_thread(self, daemon: bool = True):
        """Run pubsub in background thread."""
        return self.pubsub.run_in_thread(daemon=daemon)


# ============================================================================
# Decorators and Utilities
# ============================================================================

def cached(ttl: Optional[int] = None, namespace: str = "default"):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Get cache client
            cache = CacheClient(namespace=namespace)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


def rate_limit(limit_type: str, max_requests: int, window: int):
    """Decorator to rate limit function calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract identifier from args/kwargs (customize as needed)
            identifier = kwargs.get('user_id') or kwargs.get('ip_address') or 'anonymous'
            
            limiter = RateLimiter()
            if not limiter.check(identifier, limit_type, max_requests, window):
                raise Exception(f"Rate limit exceeded for {limit_type}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def with_redis_retry(max_retries: int = 3, retry_delay: int = 1):
    """Decorator to retry Redis operations on failure."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                    logger.warning(f"Redis retry {attempt + 1}/{max_retries} for {func.__name__}")
            
            raise last_error
        return wrapper
    return decorator


@contextmanager
def redis_lock(lock_name: str, timeout: int = 10, blocking: bool = True):
    """Context manager for Redis-based distributed lock."""
    client = RedisConnectionPool.get_client(name="locks")
    lock_key = f"{config.CACHE.key_prefix}lock:{lock_name}"
    
    try:
        # Acquire lock
        acquired = False
        if blocking:
            # Blocking acquire
            start = datetime.now()
            while not acquired:
                acquired = client.setnx(lock_key, "locked")
                if acquired:
                    client.expire(lock_key, timeout)
                    break
                if (datetime.now() - start).seconds > timeout:
                    raise TimeoutError(f"Could not acquire lock '{lock_name}'")
                time.sleep(0.1)
        else:
            # Non-blocking acquire
            acquired = client.setnx(lock_key, "locked")
            if acquired:
                client.expire(lock_key, timeout)
        
        if not acquired:
            raise Exception(f"Could not acquire lock '{lock_name}'")
        
        yield
        
    finally:
        # Release lock
        client.delete(lock_key)


# ============================================================================
# Health Check and Monitoring
# ============================================================================

class RedisHealthCheck:
    """Redis health check utilities."""
    
    def __init__(self):
        self.clients = {
            'default': RedisConnectionPool.get_client(name="default"),
            'cache': RedisConnectionPool.get_client(name="cache"),
            'sessions': RedisConnectionPool.get_client(name="sessions"),
            'rate_limiter': RedisConnectionPool.get_client(name="rate_limiter"),
            'queue': RedisConnectionPool.get_client(name="queue"),
            'pubsub': RedisConnectionPool.get_client(name="pubsub"),
        }
    
    def check_all(self) -> Dict[str, Any]:
        """Check health of all Redis clients."""
        results = {}
        
        for name, client in self.clients.items():
            results[name] = self._check_client(client)
        
        return results
    
    def _check_client(self, client: Redis) -> Dict[str, Any]:
        """Check health of a single Redis client."""
        try:
            # Test connection
            start = datetime.now()
            pong = client.ping()
            latency = (datetime.now() - start).total_seconds() * 1000
            
            # Get info
            info = client.info()
            
            return {
                'status': 'healthy' if pong else 'unhealthy',
                'latency_ms': round(latency, 2),
                'version': info.get('redis_version'),
                'used_memory': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'uptime_days': info.get('uptime_in_days'),
                'total_commands_processed': info.get('total_commands_processed')
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics."""
        stats = {}
        
        for name, client in self.clients.items():
            try:
                info = client.info()
                stats[name] = {
                    'used_memory': info.get('used_memory_human'),
                    'used_memory_peak': info.get('used_memory_peak_human'),
                    'connected_clients': info.get('connected_clients'),
                    'blocked_clients': info.get('blocked_clients'),
                    'total_connections_received': info.get('total_connections_received'),
                    'total_commands_processed': info.get('total_commands_processed'),
                    'keyspace_hits': info.get('keyspace_hits'),
                    'keyspace_misses': info.get('keyspace_misses'),
                    'evicted_keys': info.get('evicted_keys'),
                    'expired_keys': info.get('expired_keys')
                }
            except Exception as e:
                stats[name] = {'error': str(e)}
        
        return stats


# ============================================================================
# Initialization and Cleanup
# ============================================================================

def init_redis():
    """Initialize Redis connections."""
    logger.info("Initializing Redis connections...")
    
    # Test connections
    clients = {
        'default': RedisConnectionPool.get_client(name="default"),
        'cache': RedisConnectionPool.get_client(name="cache"),
        'sessions': RedisConnectionPool.get_client(name="sessions"),
    }
    
    for name, client in clients.items():
        try:
            client.ping()
            logger.info(f"Redis client '{name}' connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect Redis client '{name}': {e}")
            if not is_testing():
                raise


def close_redis():
    """Close all Redis connections."""
    logger.info("Closing Redis connections...")
    RedisConnectionPool.close_all()


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Configuration
    'RedisConfig',
    
    # Connection management
    'RedisConnectionPool',
    'init_redis',
    'close_redis',
    
    # Specialized clients
    'CacheClient',
    'RateLimiter',
    'SessionStore',
    'MessageQueue',
    'PubSubManager',
    
    # Decorators and utilities
    'cached',
    'rate_limit',
    'with_redis_retry',
    'redis_lock',
    
    # Health check
    'RedisHealthCheck',
]

# Initialize on import (but not during testing)
if not is_testing():
    init_redis()