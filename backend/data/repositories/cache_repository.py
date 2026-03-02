# parking-management/data/migrations/repositories/cache_repository.py
"""
Cache repository module for the parking management system.

This module provides repository classes for managing cached data, query results,
and distributed caching with comprehensive integration with the enum definitions.
"""

from typing import List, Optional, Dict, Any, Tuple, Union, Callable
from datetime import datetime, timedelta
import logging
import json
import pickle
import hashlib
import zlib
from enum import Enum
import redis
from redis.exceptions import RedisError
from functools import wraps

from sqlalchemy.orm import Session

from .base_repository import (
    BaseRepository,
    RepositoryException,
    EntityNotFoundException
)
from ..models.enums import (
    # Cache related (if you have cache enums)
    CacheStrategy,
    CacheRegion,
    CachePriority,
    SerializationFormat,
    
    # Audit enums
    AuditAction,
    AuditSeverity
)
from ..models.cache_models import (
    CacheEntry,
    CacheStatistics,
    CacheInvalidationLog,
    CacheWarmupTask,
    CacheDependency,
    QueryCache,
    DistributedLock,
    CacheRegion as CacheRegionModel,
    CacheConfiguration
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class CacheException(RepositoryException):
    """Base exception for cache operations."""
    def __init__(self, message: str, key: Optional[str] = None):
        self.key = key
        super().__init__(f"Cache error: {message}")


class CacheMissException(CacheException):
    """Raised when a cache key is not found."""
    def __init__(self, key: str):
        super().__init__(f"Cache miss for key: {key}", key)


class CacheConnectionException(CacheException):
    """Raised when unable to connect to cache server."""
    def __init__(self, message: str = "Unable to connect to cache server"):
        super().__init__(message)


class CacheSerializationException(CacheException):
    """Raised when serialization/deserialization fails."""
    def __init__(self, message: str, key: Optional[str] = None):
        super().__init__(f"Serialization error: {message}", key)


class CacheLockException(CacheException):
    """Raised when unable to acquire a distributed lock."""
    def __init__(self, lock_key: str, message: str = "Unable to acquire lock"):
        self.lock_key = lock_key
        super().__init__(f"{message}: {lock_key}")


class CacheWarmupException(CacheException):
    """Raised when cache warmup fails."""
    def __init__(self, task_id: int, message: str):
        self.task_id = task_id
        super().__init__(f"Cache warmup task {task_id} failed: {message}")


# ============================================================================
# Cache Repository
# ============================================================================

class CacheRepository:
    """
    Repository for managing cached data with support for multiple backends,
    serialization strategies, and distributed caching patterns.
    
    This repository provides a unified interface for caching operations
    with support for Redis, in-memory caching, and database-backed caching.
    """
    
    def __init__(
        self,
        session: Session,
        redis_client: Optional[redis.Redis] = None,
        default_ttl: int = 300,
        enable_compression: bool = True,
        compression_threshold: int = 1024  # 1KB
    ):
        """
        Initialize the cache repository.
        
        Args:
            session: SQLAlchemy session for database operations
            redis_client: Optional Redis client for distributed caching
            default_ttl: Default time-to-live in seconds
            enable_compression: Whether to enable compression for large values
            compression_threshold: Size threshold for compression in bytes
        """
        self.session = session
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.enable_compression = enable_compression
        self.compression_threshold = compression_threshold
        self._local_cache = {}  # Simple in-memory cache for fallback
        
        # Cache configuration
        self.config = self._load_configuration()
        
        logger.info(f"CacheRepository initialized with Redis: {redis_client is not None}")
    
    # ========================================================================
    # Basic Cache Operations
    # ========================================================================
    
    def get(
        self,
        key: str,
        region: Optional[str] = None,
        default: Any = None,
        deserialize: bool = True
    ) -> Any:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            region: Optional cache region
            default: Default value if key not found
            deserialize: Whether to deserialize the value
            
        Returns:
            Cached value or default
            
        Raises:
            CacheException: If cache operation fails
        """
        try:
            full_key = self._build_key(key, region)
            
            # Try Redis first if available
            if self.redis:
                value = self.redis.get(full_key)
                if value is not None:
                    self._record_hit(region)
                    return self._deserialize(value) if deserialize else value
            
            # Fall back to database cache
            db_cache = self._get_from_database(full_key)
            if db_cache:
                if db_cache.expires_at and db_cache.expires_at < datetime.utcnow():
                    # Expired, delete it
                    self.delete(key, region)
                else:
                    self._record_hit(region)
                    value = db_cache.cached_value
                    return self._deserialize(value) if deserialize else value
            
            # Try local cache as last resort
            if full_key in self._local_cache:
                value, expires_at = self._local_cache[full_key]
                if expires_at and expires_at < datetime.utcnow():
                    del self._local_cache[full_key]
                else:
                    self._record_hit(region)
                    return value
            
            self._record_miss(region)
            return default
            
        except RedisError as e:
            logger.error(f"Redis error getting key {key}: {e}")
            self._record_error(region)
            # Fall back to database cache
            return self._get_from_database_fallback(key, region, default, deserialize)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self._record_error(region)
            return default
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        region: Optional[str] = None,
        serialize: bool = True,
        compress: Optional[bool] = None
    ) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None for no expiry)
            region: Optional cache region
            serialize: Whether to serialize the value
            compress: Whether to compress (None for auto based on size)
            
        Returns:
            True if successful
            
        Raises:
            CacheException: If cache operation fails
        """
        try:
            full_key = self._build_key(key, region)
            ttl = ttl or self._get_region_ttl(region) or self.default_ttl
            
            # Serialize value
            if serialize:
                value = self._serialize(value)
            
            # Determine if compression should be used
            should_compress = compress
            if should_compress is None and self.enable_compression:
                should_compress = len(value) > self.compression_threshold
            
            if should_compress:
                value = self._compress(value)
            
            # Store in Redis if available
            if self.redis:
                try:
                    if ttl:
                        result = self.redis.setex(full_key, ttl, value)
                    else:
                        result = self.redis.set(full_key, value)
                    
                    if result:
                        self._record_write(region)
                        return True
                except RedisError as e:
                    logger.error(f"Redis error setting key {key}: {e}")
                    # Fall through to database cache
            
            # Store in database cache
            return self._set_in_database(full_key, value, ttl, region)
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            self._record_error(region)
            return False
    
    def delete(
        self,
        key: str,
        region: Optional[str] = None
    ) -> bool:
        """
        Delete a value from cache.
        
        Args:
            key: Cache key
            region: Optional cache region
            
        Returns:
            True if deleted
        """
        try:
            full_key = self._build_key(key, region)
            deleted = False
            
            # Delete from Redis
            if self.redis:
                try:
                    result = self.redis.delete(full_key)
                    deleted = deleted or (result > 0)
                except RedisError as e:
                    logger.error(f"Redis error deleting key {key}: {e}")
            
            # Delete from database
            db_deleted = self._delete_from_database(full_key)
            deleted = deleted or db_deleted
            
            # Delete from local cache
            if full_key in self._local_cache:
                del self._local_cache[full_key]
                deleted = True
            
            if deleted:
                self._record_invalidation(region)
                self._log_invalidation(key, region, 'delete')
            
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def exists(
        self,
        key: str,
        region: Optional[str] = None
    ) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            region: Optional cache region
            
        Returns:
            True if key exists
        """
        try:
            full_key = self._build_key(key, region)
            
            # Check Redis
            if self.redis:
                try:
                    if self.redis.exists(full_key):
                        return True
                except RedisError:
                    pass
            
            # Check database
            db_cache = self._get_from_database(full_key)
            if db_cache:
                if db_cache.expires_at and db_cache.expires_at < datetime.utcnow():
                    self.delete(key, region)
                    return False
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    def increment(
        self,
        key: str,
        amount: int = 1,
        region: Optional[str] = None
    ) -> Optional[int]:
        """
        Increment a numeric value in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment
            region: Optional cache region
            
        Returns:
            New value or None if operation failed
        """
        try:
            full_key = self._build_key(key, region)
            
            if self.redis:
                try:
                    result = self.redis.incrby(full_key, amount)
                    return result
                except RedisError as e:
                    logger.error(f"Redis error incrementing key {key}: {e}")
            
            # Fall back to database
            current = self.get(key, region, default=0)
            new_value = current + amount
            self.set(key, new_value, region=region)
            return new_value
            
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    def expire(
        self,
        key: str,
        ttl: int,
        region: Optional[str] = None
    ) -> bool:
        """
        Set expiration on a key.
        
        Args:
            key: Cache key
            ttl: Time-to-live in seconds
            region: Optional cache region
            
        Returns:
            True if successful
        """
        try:
            full_key = self._build_key(key, region)
            
            if self.redis:
                try:
                    return bool(self.redis.expire(full_key, ttl))
                except RedisError as e:
                    logger.error(f"Redis error setting expiry for key {key}: {e}")
            
            # Update database
            db_cache = self._get_from_database(full_key)
            if db_cache:
                db_cache.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
                self.session.flush()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False
    
    def ttl(
        self,
        key: str,
        region: Optional[str] = None
    ) -> Optional[int]:
        """
        Get remaining TTL for a key.
        
        Args:
            key: Cache key
            region: Optional cache region
            
        Returns:
            Remaining TTL in seconds, None if no expiry, -1 if key doesn't exist
        """
        try:
            full_key = self._build_key(key, region)
            
            if self.redis:
                try:
                    return self.redis.ttl(full_key)
                except RedisError:
                    pass
            
            db_cache = self._get_from_database(full_key)
            if db_cache and db_cache.expires_at:
                remaining = (db_cache.expires_at - datetime.utcnow()).total_seconds()
                return max(0, int(remaining))
            
            return -1
            
        except Exception as e:
            logger.error(f"Cache ttl error for key {key}: {e}")
            return -1
    
    # ========================================================================
    # Multi-key Operations
    # ========================================================================
    
    def get_many(
        self,
        keys: List[str],
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            region: Optional cache region
            
        Returns:
            Dictionary of key-value pairs
        """
        result = {}
        
        if not keys:
            return result
        
        try:
            full_keys = [self._build_key(k, region) for k in keys]
            
            # Try Redis first
            if self.redis:
                try:
                    values = self.redis.mget(full_keys)
                    for key, value in zip(keys, values):
                        if value is not None:
                            result[key] = self._deserialize(value)
                            self._record_hit(region)
                        else:
                            self._record_miss(region)
                    
                    # Return what we found
                    if result:
                        return result
                except RedisError:
                    pass
            
            # Fall back to database
            for key in keys:
                value = self.get(key, region)
                if value is not None:
                    result[key] = value
            
            return result
            
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[int] = None,
        region: Optional[str] = None
    ) -> bool:
        """
        Set multiple values in cache.
        
        Args:
            mapping: Dictionary of key-value pairs
            ttl: Time-to-live in seconds
            region: Optional cache region
            
        Returns:
            True if all successful
        """
        if not mapping:
            return True
        
        try:
            success = True
            
            # Prepare data
            pipe_data = {}
            for key, value in mapping.items():
                full_key = self._build_key(key, region)
                serialized = self._serialize(value)
                
                if self.enable_compression and len(serialized) > self.compression_threshold:
                    serialized = self._compress(serialized)
                
                pipe_data[full_key] = serialized
            
            # Try Redis pipeline
            if self.redis:
                try:
                    pipe = self.redis.pipeline()
                    for full_key, value in pipe_data.items():
                        if ttl:
                            pipe.setex(full_key, ttl, value)
                        else:
                            pipe.set(full_key, value)
                    results = pipe.execute()
                    success = all(results)
                    
                    if success:
                        self._record_write(region, len(mapping))
                        return True
                except RedisError as e:
                    logger.error(f"Redis error in set_many: {e}")
                    success = False
            
            # Fall back to individual database sets
            for key, value in mapping.items():
                if not self.set(key, value, ttl, region):
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    def delete_many(
        self,
        keys: List[str],
        region: Optional[str] = None
    ) -> int:
        """
        Delete multiple keys from cache.
        
        Args:
            keys: List of cache keys
            region: Optional cache region
            
        Returns:
            Number of keys deleted
        """
        if not keys:
            return 0
        
        try:
            deleted_count = 0
            
            # Delete from Redis
            if self.redis:
                try:
                    full_keys = [self._build_key(k, region) for k in keys]
                    deleted_count = self.redis.delete(*full_keys)
                except RedisError as e:
                    logger.error(f"Redis error in delete_many: {e}")
            
            # Delete from database
            for key in keys:
                if self.delete(key, region):
                    deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cache delete_many error: {e}")
            return 0
    
    # ========================================================================
    # Cache Invalidation
    # ========================================================================
    
    def invalidate_pattern(
        self,
        pattern: str,
        region: Optional[str] = None
    ) -> int:
        """
        Invalidate all keys matching a pattern.
        
        Args:
            pattern: Key pattern (supports * wildcard)
            region: Optional cache region
            
        Returns:
            Number of keys invalidated
        """
        try:
            invalidated = 0
            
            # Redis pattern invalidation
            if self.redis:
                try:
                    full_pattern = self._build_key(pattern, region)
                    keys = self.redis.keys(full_pattern)
                    if keys:
                        invalidated = self.redis.delete(*keys)
                except RedisError as e:
                    logger.error(f"Redis error in invalidate_pattern: {e}")
            
            # Database pattern invalidation
            like_pattern = pattern.replace('*', '%')
            db_keys = (
                self.session.query(CacheEntry)
                .filter(CacheEntry.cache_key.like(like_pattern))
                .all()
            )
            
            for entry in db_keys:
                self.session.delete(entry)
                invalidated += 1
            
            self.session.flush()
            
            if invalidated > 0:
                self._log_invalidation(pattern, region, 'pattern', count=invalidated)
            
            logger.info(f"Invalidated {invalidated} keys matching pattern: {pattern}")
            return invalidated
            
        except Exception as e:
            logger.error(f"Cache invalidate_pattern error: {e}")
            return 0
    
    def invalidate_region(self, region: str) -> int:
        """
        Invalidate an entire cache region.
        
        Args:
            region: Cache region to invalidate
            
        Returns:
            Number of keys invalidated
        """
        return self.invalidate_pattern(f"{region}:*")
    
    def invalidate_dependent(
        self,
        dependency_key: str
    ) -> int:
        """
        Invalidate all cache entries that depend on a key.
        
        Args:
            dependency_key: Dependency key
            
        Returns:
            Number of keys invalidated
        """
        try:
            dependencies = (
                self.session.query(CacheDependency)
                .filter(CacheDependency.dependency_key == dependency_key)
                .all()
            )
            
            keys_to_invalidate = [d.cache_key for d in dependencies]
            
            if keys_to_invalidate:
                self.delete_many(keys_to_invalidate)
                
                # Remove dependencies
                for dep in dependencies:
                    self.session.delete(dep)
                
                self.session.flush()
                
                logger.info(f"Invalidated {len(keys_to_invalidate)} keys dependent on {dependency_key}")
                return len(keys_to_invalidate)
            
            return 0
            
        except Exception as e:
            logger.error(f"Cache invalidate_dependent error: {e}")
            return 0
    
    # ========================================================================
    # Cache Regions
    # ========================================================================
    
    def get_region(self, name: str) -> Optional[CacheRegionModel]:
        """Get cache region configuration."""
        return (
            self.session.query(CacheRegionModel)
            .filter(CacheRegionModel.name == name)
            .first()
        )
    
    def create_region(
        self,
        name: str,
        ttl: int = 300,
        max_size: Optional[int] = None,
        strategy: str = 'lru'
    ) -> CacheRegionModel:
        """
        Create a cache region.
        
        Args:
            name: Region name
            ttl: Default TTL in seconds
            max_size: Maximum number of entries
            strategy: Eviction strategy
            
        Returns:
            Created region
        """
        region = CacheRegionModel(
            name=name,
            ttl=ttl,
            max_size=max_size,
            strategy=strategy,
            created_at=datetime.utcnow()
        )
        
        self.session.add(region)
        self.session.flush()
        
        logger.info(f"Created cache region: {name}")
        return region
    
    def update_region(
        self,
        name: str,
        **updates
    ) -> Optional[CacheRegionModel]:
        """
        Update cache region configuration.
        
        Args:
            name: Region name
            **updates: Fields to update
            
        Returns:
            Updated region
        """
        region = self.get_region(name)
        if not region:
            return None
        
        for key, value in updates.items():
            if hasattr(region, key):
                setattr(region, key, value)
        
        region.updated_at = datetime.utcnow()
        self.session.flush()
        
        logger.info(f"Updated cache region: {name}")
        return region
    
    def delete_region(self, name: str) -> bool:
        """
        Delete a cache region and all its keys.
        
        Args:
            name: Region name
            
        Returns:
            True if deleted
        """
        # Invalidate all keys in region
        self.invalidate_region(name)
        
        # Delete region
        region = self.get_region(name)
        if region:
            self.session.delete(region)
            self.session.flush()
            logger.info(f"Deleted cache region: {name}")
            return True
        
        return False
    
    def _get_region_ttl(self, region: Optional[str]) -> Optional[int]:
        """Get TTL for a region."""
        if not region:
            return None
        
        region_config = self.get_region(region)
        return region_config.ttl if region_config else None
    
    # ========================================================================
    # Query Caching
    # ========================================================================
    
    def cache_query(
        self,
        query_key: str,
        query_func: Callable,
        ttl: Optional[int] = None,
        region: Optional[str] = None,
        dependencies: Optional[List[str]] = None
    ) -> Any:
        """
        Cache the result of a query.
        
        This method implements the cache-aside pattern with automatic
        invalidation based on dependencies.
        
        Args:
            query_key: Unique key for the query
            query_func: Function that executes the query
            ttl: Time-to-live in seconds
            region: Optional cache region
            dependencies: List of dependency keys
            
        Returns:
            Query result (from cache or fresh)
        """
        # Try to get from cache
        cached_result = self.get(query_key, region)
        
        if cached_result is not None:
            logger.debug(f"Query cache hit: {query_key}")
            return cached_result
        
        # Cache miss - execute query
        logger.debug(f"Query cache miss: {query_key}")
        result = query_func()
        
        # Store in cache
        if result is not None:
            self.set(query_key, result, ttl, region)
            
            # Register dependencies
            if dependencies:
                for dep in dependencies:
                    self.add_dependency(query_key, dep)
        
        return result
    
    def add_dependency(
        self,
        cache_key: str,
        dependency_key: str
    ) -> bool:
        """
        Register a dependency between cache keys.
        
        When the dependency key is invalidated, all dependent keys
        will also be invalidated.
        
        Args:
            cache_key: Cache key that depends on another
            dependency_key: Key that, when invalidated, triggers invalidation
            
        Returns:
            True if dependency registered
        """
        try:
            # Check if dependency already exists
            existing = (
                self.session.query(CacheDependency)
                .filter(
                    CacheDependency.cache_key == cache_key,
                    CacheDependency.dependency_key == dependency_key
                )
                .first()
            )
            
            if not existing:
                dependency = CacheDependency(
                    cache_key=cache_key,
                    dependency_key=dependency_key,
                    created_at=datetime.utcnow()
                )
                self.session.add(dependency)
                self.session.flush()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding dependency: {e}")
            return False
    
    def remove_dependencies(
        self,
        cache_key: str
    ) -> int:
        """
        Remove all dependencies for a cache key.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Number of dependencies removed
        """
        try:
            result = (
                self.session.query(CacheDependency)
                .filter(CacheDependency.cache_key == cache_key)
                .delete()
            )
            self.session.flush()
            return result
        except Exception as e:
            logger.error(f"Error removing dependencies: {e}")
            return 0
    
    # ========================================================================
    # Distributed Locks
    # ========================================================================
    
    def acquire_lock(
        self,
        lock_key: str,
        ttl: int = 30,
        wait_timeout: int = 10,
        retry_interval: float = 0.1
    ) -> Optional[str]:
        """
        Acquire a distributed lock.
        
        Args:
            lock_key: Lock identifier
            ttl: Lock TTL in seconds (auto-release after this time)
            wait_timeout: Maximum time to wait for lock in seconds
            retry_interval: Time between retry attempts in seconds
            
        Returns:
            Lock token if acquired, None if timeout
            
        Raises:
            CacheLockException: If lock operation fails
        """
        import time
        
        token = self._generate_lock_token()
        start_time = time.time()
        full_key = f"lock:{lock_key}"
        
        while (time.time() - start_time) < wait_timeout:
            try:
                # Try Redis first
                if self.redis:
                    acquired = self.redis.set(
                        full_key,
                        token,
                        nx=True,  # Only set if not exists
                        ex=ttl
                    )
                    if acquired:
                        self._record_lock_acquired(lock_key)
                        return token
                else:
                    # Fall back to database lock
                    acquired = self._acquire_db_lock(lock_key, token, ttl)
                    if acquired:
                        return token
                
                # Wait before retry
                time.sleep(retry_interval)
                
            except Exception as e:
                logger.error(f"Error acquiring lock {lock_key}: {e}")
                time.sleep(retry_interval)
        
        raise CacheLockException(lock_key, f"Timeout after {wait_timeout}s")
    
    def release_lock(
        self,
        lock_key: str,
        token: str
    ) -> bool:
        """
        Release a distributed lock.
        
        Args:
            lock_key: Lock identifier
            token: Lock token from acquire_lock
            
        Returns:
            True if released
        """
        try:
            full_key = f"lock:{lock_key}"
            
            # Try Redis first
            if self.redis:
                # Lua script to ensure we only delete if token matches
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                released = self.redis.eval(lua_script, 1, full_key, token)
                if released:
                    self._record_lock_released(lock_key)
                    return True
            else:
                # Fall back to database
                released = self._release_db_lock(lock_key, token)
                if released:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error releasing lock {lock_key}: {e}")
            return False
    
    def _acquire_db_lock(
        self,
        lock_key: str,
        token: str,
        ttl: int
    ) -> bool:
        """Acquire a database-backed lock."""
        try:
            # Try to insert lock
            lock = DistributedLock(
                lock_key=lock_key,
                lock_token=token,
                acquired_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(seconds=ttl)
            )
            self.session.add(lock)
            self.session.flush()
            return True
        except Exception:
            # Lock already exists, check if expired
            existing = (
                self.session.query(DistributedLock)
                .filter(DistributedLock.lock_key == lock_key)
                .first()
            )
            
            if existing and existing.expires_at < datetime.utcnow():
                # Lock expired, can acquire
                existing.lock_token = token
                existing.acquired_at = datetime.utcnow()
                existing.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
                self.session.flush()
                return True
            
            return False
    
    def _release_db_lock(
        self,
        lock_key: str,
        token: str
    ) -> bool:
        """Release a database-backed lock."""
        result = (
            self.session.query(DistributedLock)
            .filter(
                DistributedLock.lock_key == lock_key,
                DistributedLock.lock_token == token
            )
            .delete()
        )
        self.session.flush()
        return result > 0
    
    # ========================================================================
    # Cache Statistics
    # ========================================================================
    
    def get_statistics(
        self,
        region: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> CacheStatistics:
        """
        Get cache statistics.
        
        Args:
            region: Optional region filter
            since: Optional start time for statistics
            
        Returns:
            Cache statistics
        """
        query = self.session.query(CacheStatistics)
        
        if region:
            query = query.filter(CacheStatistics.region == region)
        
        if since:
            query = query.filter(CacheStatistics.created_at >= since)
        
        stats = query.order_by(desc(CacheStatistics.created_at)).first()
        
        if not stats:
            # Create default statistics
            stats = CacheStatistics(
                region=region,
                hits=0,
                misses=0,
                writes=0,
                invalidations=0,
                errors=0,
                created_at=datetime.utcnow()
            )
            self.session.add(stats)
            self.session.flush()
        
        return stats
    
    def _record_hit(self, region: Optional[str]) -> None:
        """Record a cache hit."""
        self._update_stats(region, hits=1)
    
    def _record_miss(self, region: Optional[str]) -> None:
        """Record a cache miss."""
        self._update_stats(region, misses=1)
    
    def _record_write(self, region: Optional[str], count: int = 1) -> None:
        """Record a cache write."""
        self._update_stats(region, writes=count)
    
    def _record_error(self, region: Optional[str]) -> None:
        """Record a cache error."""
        self._update_stats(region, errors=1)
    
    def _record_invalidation(self, region: Optional[str]) -> None:
        """Record a cache invalidation."""
        self._update_stats(region, invalidations=1)
    
    def _record_lock_acquired(self, lock_key: str) -> None:
        """Record a lock acquisition."""
        logger.debug(f"Lock acquired: {lock_key}")
    
    def _record_lock_released(self, lock_key: str) -> None:
        """Record a lock release."""
        logger.debug(f"Lock released: {lock_key}")
    
    def _update_stats(
        self,
        region: Optional[str],
        hits: int = 0,
        misses: int = 0,
        writes: int = 0,
        invalidations: int = 0,
        errors: int = 0
    ) -> None:
        """Update cache statistics."""
        try:
            # Get or create today's stats
            today = datetime.utcnow().date()
            
            stats = (
                self.session.query(CacheStatistics)
                .filter(
                    CacheStatistics.region == region,
                    func.date(CacheStatistics.created_at) == today
                )
                .first()
            )
            
            if not stats:
                stats = CacheStatistics(
                    region=region,
                    hits=0,
                    misses=0,
                    writes=0,
                    invalidations=0,
                    errors=0,
                    created_at=datetime.utcnow()
                )
                self.session.add(stats)
            
            stats.hits += hits
            stats.misses += misses
            stats.writes += writes
            stats.invalidations += invalidations
            stats.errors += errors
            stats.updated_at = datetime.utcnow()
            
            self.session.flush()
            
        except Exception as e:
            logger.error(f"Error updating cache stats: {e}")
    
    def reset_statistics(self, region: Optional[str] = None) -> int:
        """
        Reset cache statistics.
        
        Args:
            region: Optional region filter
            
        Returns:
            Number of statistics records reset
        """
        query = self.session.query(CacheStatistics)
        
        if region:
            query = query.filter(CacheStatistics.region == region)
        
        result = query.delete()
        self.session.flush()
        
        logger.info(f"Reset {result} cache statistics records")
        return result
    
    # ========================================================================
    # Cache Warmup
    # ========================================================================
    
    def warmup_region(
        self,
        region: str,
        priority: str = 'normal'
    ) -> CacheWarmupTask:
        """
        Start a cache warmup task for a region.
        
        Args:
            region: Region to warm up
            priority: Task priority
            
        Returns:
            Created warmup task
        """
        task = CacheWarmupTask(
            region=region,
            priority=priority,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        self.session.add(task)
        self.session.flush()
        
        logger.info(f"Created cache warmup task {task.id} for region {region}")
        return task
    
    def execute_warmup(self, task_id: int) -> Dict[str, Any]:
        """
        Execute a cache warmup task.
        
        Args:
            task_id: Warmup task ID
            
        Returns:
            Warmup results
        """
        task = self.session.query(CacheWarmupTask).get(task_id)
        if not task:
            raise EntityNotFoundException("CacheWarmupTask", task_id)
        
        task.status = 'running'
        task.started_at = datetime.utcnow()
        self.session.flush()
        
        results = {
            'keys_warmed': 0,
            'keys_failed': 0,
            'total_time': 0
        }
        
        try:
            start_time = datetime.utcnow()
            
            # Get region configuration
            region_config = self.get_region(task.region)
            if not region_config:
                raise CacheWarmupException(task_id, f"Region {task.region} not found")
            
            # Get keys to warm up (this would be customized based on your data)
            keys_to_warm = self._get_keys_for_warmup(task.region)
            
            for key_info in keys_to_warm:
                try:
                    # Execute warmup function
                    value = self._execute_warmup_function(key_info)
                    
                    # Store in cache
                    self.set(
                        key_info['key'],
                        value,
                        ttl=region_config.ttl,
                        region=task.region
                    )
                    
                    results['keys_warmed'] += 1
                    
                except Exception as e:
                    logger.error(f"Warmup failed for key {key_info.get('key')}: {e}")
                    results['keys_failed'] += 1
            
            end_time = datetime.utcnow()
            results['total_time'] = (end_time - start_time).total_seconds()
            
            task.status = 'completed'
            task.completed_at = end_time
            task.results = results
            
            logger.info(f"Cache warmup task {task_id} completed: {results}")
            
        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)
            logger.error(f"Cache warmup task {task_id} failed: {e}")
            raise CacheWarmupException(task_id, str(e))
        
        self.session.flush()
        return results
    
    def _get_keys_for_warmup(self, region: str) -> List[Dict]:
        """
        Get list of keys to warm up for a region.
        
        This should be customized based on your application's needs.
        """
        # Placeholder implementation
        return []
    
    def _execute_warmup_function(self, key_info: Dict) -> Any:
        """
        Execute the warmup function for a key.
        
        This should be customized based on your application's needs.
        """
        # Placeholder implementation
        return None
    
    # ========================================================================
    # Serialization and Compression
    # ========================================================================
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize a value for caching."""
        try:
            if isinstance(value, (str, int, float, bool, type(None))):
                return pickle.dumps(value)
            elif isinstance(value, (dict, list)):
                return pickle.dumps(value)
            else:
                # For custom objects, try pickle
                return pickle.dumps(value)
        except Exception as e:
            raise CacheSerializationException(f"Failed to serialize: {e}")
    
    def _deserialize(self, value: bytes) -> Any:
        """Deserialize a cached value."""
        try:
            # Check if value is compressed
            if value.startswith(b'\x78\x9c'):  # zlib header
                value = self._decompress(value)
            
            return pickle.loads(value)
        except Exception as e:
            raise CacheSerializationException(f"Failed to deserialize: {e}")
    
    def _compress(self, value: bytes) -> bytes:
        """Compress a value."""
        try:
            return zlib.compress(value)
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return value
    
    def _decompress(self, value: bytes) -> bytes:
        """Decompress a value."""
        try:
            return zlib.decompress(value)
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return value
    
    # ========================================================================
    # Database Cache Operations
    # ========================================================================
    
    def _set_in_database(
        self,
        key: str,
        value: bytes,
        ttl: Optional[int],
        region: Optional[str]
    ) -> bool:
        """Store value in database cache."""
        try:
            # Check if entry exists
            entry = (
                self.session.query(CacheEntry)
                .filter(CacheEntry.cache_key == key)
                .first()
            )
            
            if entry:
                entry.cached_value = value
                entry.expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl else None
                entry.updated_at = datetime.utcnow()
            else:
                entry = CacheEntry(
                    cache_key=key,
                    cached_value=value,
                    region=region,
                    expires_at=datetime.utcnow() + timedelta(seconds=ttl) if ttl else None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.session.add(entry)
            
            self.session.flush()
            
            # Also store in local cache
            expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl else None
            self._local_cache[key] = (value, expires_at)
            
            return True
            
        except Exception as e:
            logger.error(f"Database cache set error for key {key}: {e}")
            return False
    
    def _get_from_database(self, key: str) -> Optional[CacheEntry]:
        """Get value from database cache."""
        try:
            entry = (
                self.session.query(CacheEntry)
                .filter(CacheEntry.cache_key == key)
                .first()
            )
            return entry
        except Exception as e:
            logger.error(f"Database cache get error for key {key}: {e}")
            return None
    
    def _get_from_database_fallback(
        self,
        key: str,
        region: Optional[str],
        default: Any,
        deserialize: bool
    ) -> Any:
        """Fallback to database cache."""
        db_cache = self._get_from_database(self._build_key(key, region))
        if db_cache:
            if db_cache.expires_at and db_cache.expires_at < datetime.utcnow():
                self._delete_from_database(key)
            else:
                value = db_cache.cached_value
                return self._deserialize(value) if deserialize else value
        return default
    
    def _delete_from_database(self, key: str) -> bool:
        """Delete value from database cache."""
        try:
            result = (
                self.session.query(CacheEntry)
                .filter(CacheEntry.cache_key == key)
                .delete()
            )
            self.session.flush()
            return result > 0
        except Exception as e:
            logger.error(f"Database cache delete error for key {key}: {e}")
            return False
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def _build_key(self, key: str, region: Optional[str] = None) -> str:
        """Build a full cache key with region prefix."""
        if region:
            return f"{region}:{key}"
        return key
    
    def _generate_lock_token(self) -> str:
        """Generate a unique lock token."""
        import uuid
        return str(uuid.uuid4())
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load cache configuration from database."""
        configs = self.session.query(CacheConfiguration).all()
        return {c.config_key: c.config_value for c in configs}
    
    def _log_invalidation(
        self,
        key: str,
        region: Optional[str],
        reason: str,
        count: int = 1
    ) -> None:
        """Log cache invalidation for audit purposes."""
        log = CacheInvalidationLog(
            cache_key=key,
            region=region,
            reason=reason,
            count=count,
            created_at=datetime.utcnow()
        )
        self.session.add(log)
        self.session.flush()
    
    # ========================================================================
    # Cache Cleanup
    # ========================================================================
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from database cache.
        
        Returns:
            Number of entries removed
        """
        try:
            # Remove from database
            result = (
                self.session.query(CacheEntry)
                .filter(CacheEntry.expires_at < datetime.utcnow())
                .delete()
            )
            
            # Remove from local cache
            expired_keys = [
                key for key, (_, expires_at) in self._local_cache.items()
                if expires_at and expires_at < datetime.utcnow()
            ]
            for key in expired_keys:
                del self._local_cache[key]
            
            self.session.flush()
            
            logger.info(f"Cleaned up {result} expired cache entries")
            return result
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            return 0
    
    def clear_all(self) -> int:
        """
        Clear all cache entries.
        
        Returns:
            Number of entries cleared
        """
        cleared = 0
        
        # Clear Redis
        if self.redis:
            try:
                cleared += self.redis.flushdb()
            except RedisError as e:
                logger.error(f"Redis clear error: {e}")
        
        # Clear database
        try:
            cleared += self.session.query(CacheEntry).delete()
            cleared += self.session.query(CacheDependency).delete()
            cleared += self.session.query(DistributedLock).delete()
            self.session.flush()
        except Exception as e:
            logger.error(f"Database cache clear error: {e}")
        
        # Clear local cache
        self._local_cache.clear()
        
        logger.info(f"Cleared all cache entries: {cleared}")
        return cleared
    
    def get_size(self, region: Optional[str] = None) -> int:
        """
        Get approximate size of cache.
        
        Args:
            region: Optional region filter
            
        Returns:
            Number of entries
        """
        query = self.session.query(CacheEntry)
        
        if region:
            query = query.filter(CacheEntry.region == region)
        
        return query.count()
    
    def get_keys(self, pattern: str = "*", region: Optional[str] = None) -> List[str]:
        """
        Get cache keys matching pattern.
        
        Args:
            pattern: Key pattern (supports * wildcard)
            region: Optional region filter
            
        Returns:
            List of matching keys
        """
        keys = []
        
        # Get from Redis
        if self.redis:
            try:
                full_pattern = self._build_key(pattern, region)
                redis_keys = self.redis.keys(full_pattern)
                keys.extend([k.decode() if isinstance(k, bytes) else k for k in redis_keys])
            except RedisError:
                pass
        
        # Get from database
        like_pattern = pattern.replace('*', '%')
        query = self.session.query(CacheEntry.cache_key)
        
        if region:
            query = query.filter(CacheEntry.region == region)
        
        query = query.filter(CacheEntry.cache_key.like(like_pattern))
        db_keys = query.all()
        keys.extend([k[0] for k in db_keys])
        
        return list(set(keys))  # Remove duplicates


# ============================================================================
# Cache Decorators
# ============================================================================

def cached(
    ttl: Optional[int] = None,
    region: Optional[str] = None,
    key_func: Optional[Callable] = None
):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds
        region: Cache region
        key_func: Function to generate cache key from args/kwargs
        
    Example:
        @cached(ttl=300)
        def expensive_function(arg1, arg2):
            return result
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache repository from first argument if it's a class instance
            cache_repo = None
            if args and hasattr(args[0], 'cache_repository'):
                cache_repo = args[0].cache_repository
            
            if not cache_repo:
                # Fall back to global cache instance
                from flask import current_app
                cache_repo = current_app.cache_repository if current_app else None
            
            if not cache_repo:
                # No cache available, just execute function
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend([str(a) for a in args])
                key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached_result = cache_repo.get(cache_key, region)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_repo.set(cache_key, result, ttl, region)
            
            return result
        return wrapper
    return decorator


def invalidates(keys: List[str], region: Optional[str] = None):
    """
    Decorator to invalidate cache keys after function execution.
    
    Args:
        keys: List of cache keys to invalidate
        region: Cache region
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute function
            result = func(*args, **kwargs)
            
            # Get cache repository
            cache_repo = None
            if args and hasattr(args[0], 'cache_repository'):
                cache_repo = args[0].cache_repository
            
            if cache_repo:
                # Invalidate keys
                for key in keys:
                    cache_repo.delete(key, region)
            
            return result
        return wrapper
    return decorator


def rate_limit(
    max_calls: int,
    period: int,
    key_func: Optional[Callable] = None
):
    """
    Decorator to rate limit function calls using cache.
    
    Args:
        max_calls: Maximum number of calls in the period
        period: Period in seconds
        key_func: Function to generate rate limit key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache repository
            cache_repo = None
            if args and hasattr(args[0], 'cache_repository'):
                cache_repo = args[0].cache_repository
            
            if not cache_repo:
                return func(*args, **kwargs)
            
            # Generate rate limit key
            if key_func:
                rate_key = key_func(*args, **kwargs)
            else:
                # Default key based on function and first argument (usually user_id)
                user_id = args[1] if len(args) > 1 else 'anonymous'
                rate_key = f"rate_limit:{func.__name__}:{user_id}"
            
            # Get current count
            count = cache_repo.get(rate_key, default=0)
            
            if count >= max_calls:
                # Rate limit exceeded
                import time
                retry_after = cache_repo.ttl(rate_key)
                raise Exception(f"Rate limit exceeded. Try again in {retry_after} seconds")
            
            # Increment count
            cache_repo.increment(rate_key)
            
            # Set expiry on first call
            if count == 0:
                cache_repo.expire(rate_key, period)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    'CacheRepository',
    'cached',
    'invalidates',
    'rate_limit',
    
    # Exceptions
    'CacheException',
    'CacheMissException',
    'CacheConnectionException',
    'CacheSerializationException',
    'CacheLockException',
    'CacheWarmupException',
]