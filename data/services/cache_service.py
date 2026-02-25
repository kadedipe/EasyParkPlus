# parking-management/data/services/cache_service.py
"""
Cache service module for the parking management system.

This module provides business logic for caching operations, cache management
strategies, and high-level caching services for the application.
"""

from typing import (
    List, Optional, Dict, Any, Tuple, Union, Callable, TypeVar, Generic,
    Set, cast
)
from datetime import datetime, timedelta
import logging
import json
import hashlib
import pickle
from enum import Enum
from functools import wraps
import asyncio
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from ..repositories import CacheRepository
from .base_service import BaseService, ServiceException, with_retry
from ..models.enums import (
    CacheStrategy,
    CacheRegion,
    CachePriority,
    SerializationFormat
)

# Configure logging
logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============================================================================
# Custom Exceptions
# ============================================================================

class CacheServiceException(ServiceException):
    """Base exception for cache service."""
    pass


class CacheStrategyException(CacheServiceException):
    """Raised when cache strategy execution fails."""
    pass


class CacheWarmupException(CacheServiceException):
    """Raised when cache warmup fails."""
    pass


class CacheSyncException(CacheServiceException):
    """Raised when cache synchronization fails."""
    pass


# ============================================================================
# Cache Strategy Implementations
# ============================================================================

class CacheStrategyExecutor:
    """
    Executes different caching strategies.
    
    Implements various caching patterns:
    - Cache-Aside (Lazy Loading)
    - Write-Through
    - Write-Behind
    - Refresh-Ahead
    """
    
    def __init__(self, cache_repository: CacheRepository):
        self.cache = cache_repository
    
    def execute_cache_aside(
        self,
        key: str,
        loader: Callable[[], T],
        ttl: Optional[int] = None,
        region: Optional[str] = None
    ) -> T:
        """
        Execute cache-aside pattern (lazy loading).
        
        Args:
            key: Cache key
            loader: Function to load data if cache miss
            ttl: Time-to-live in seconds
            region: Cache region
            
        Returns:
            Cached or loaded value
        """
        # Try cache first
        value = self.cache.get(key, region)
        
        if value is not None:
            logger.debug(f"Cache hit: {key}")
            return value
        
        # Cache miss - load data
        logger.debug(f"Cache miss: {key}")
        value = loader()
        
        # Store in cache
        if value is not None:
            self.cache.set(key, value, ttl, region)
        
        return value
    
    def execute_write_through(
        self,
        key: str,
        value: Any,
        writer: Callable[[Any], Any],
        ttl: Optional[int] = None,
        region: Optional[str] = None
    ) -> Any:
        """
        Execute write-through pattern.
        
        Writes to database first, then cache.
        
        Args:
            key: Cache key
            value: Value to write
            writer: Function to write to database
            ttl: Time-to-live in seconds
            region: Cache region
            
        Returns:
            Written value
        """
        # Write to database first
        result = writer(value)
        
        # Then update cache
        if result is not None:
            self.cache.set(key, result, ttl, region)
        
        return result
    
    def execute_write_behind(
        self,
        key: str,
        value: Any,
        writer: Callable[[Any], Any],
        ttl: Optional[int] = None,
        region: Optional[str] = None,
        delay_seconds: int = 5
    ) -> Any:
        """
        Execute write-behind pattern.
        
        Writes to cache immediately, then asynchronously to database.
        
        Args:
            key: Cache key
            value: Value to write
            writer: Function to write to database
            ttl: Time-to-live in seconds
            region: Cache region
            delay_seconds: Delay before writing to database
            
        Returns:
            Value stored in cache
        """
        # Write to cache immediately
        self.cache.set(key, value, ttl, region)
        
        # Schedule database write
        def delayed_write():
            import time
            time.sleep(delay_seconds)
            try:
                writer(value)
                logger.debug(f"Write-behind completed for {key}")
            except Exception as e:
                logger.error(f"Write-behind failed for {key}: {e}")
        
        # Execute in background thread
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(delayed_write)
        executor.shutdown(wait=False)
        
        return value
    
    def execute_refresh_ahead(
        self,
        key: str,
        loader: Callable[[], T],
        ttl: int,
        refresh_threshold: float = 0.75,
        region: Optional[str] = None
    ) -> T:
        """
        Execute refresh-ahead pattern.
        
        Refreshes cache before expiration if frequently accessed.
        
        Args:
            key: Cache key
            loader: Function to load data
            ttl: Time-to-live in seconds
            refresh_threshold: Threshold (0-1) of TTL to trigger refresh
            region: Cache region
            
        Returns:
            Cached value (may trigger background refresh)
        """
        # Get value and TTL
        value = self.cache.get(key, region)
        remaining_ttl = self.cache.ttl(key, region)
        
        if value is None:
            # Cache miss - load and store
            value = loader()
            self.cache.set(key, value, ttl, region)
            return value
        
        # Check if we should refresh ahead
        if remaining_ttl is not None and remaining_ttl > 0:
            threshold_time = ttl * refresh_threshold
            if remaining_ttl < threshold_time:
                # Trigger background refresh
                self._refresh_in_background(key, loader, ttl, region)
        
        return value
    
    def _refresh_in_background(
        self,
        key: str,
        loader: Callable[[], Any],
        ttl: int,
        region: Optional[str]
    ) -> None:
        """Refresh cache in background thread."""
        def refresh():
            try:
                new_value = loader()
                if new_value is not None:
                    self.cache.set(key, new_value, ttl, region)
                    logger.debug(f"Background refresh completed for {key}")
            except Exception as e:
                logger.error(f"Background refresh failed for {key}: {e}")
        
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(refresh)
        executor.shutdown(wait=False)


# ============================================================================
# Cache Service
# ============================================================================

class CacheService(BaseService):
    """
    Service for managing caching operations with business logic.
    
    Provides high-level caching operations, strategy execution,
    cache warming, and cache synchronization.
    """
    
    def __init__(
        self,
        session: Session,
        cache_repository: CacheRepository
    ):
        """
        Initialize the cache service.
        
        Args:
            session: SQLAlchemy session
            cache_repository: Cache repository
        """
        super().__init__(session)
        self.cache = cache_repository
        self.strategy_executor = CacheStrategyExecutor(cache_repository)
        
        # Cache configuration
        self.default_ttl = 300  # 5 minutes
        self.warmup_enabled = True
        self.sync_enabled = True
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'writes': 0,
            'invalidations': 0,
            'warmups': 0,
            'syncs': 0
        }
        
        logger.info("CacheService initialized")
    
    # ========================================================================
    # Basic Cache Operations
    # ========================================================================
    
    def get(
        self,
        key: str,
        region: Optional[str] = None,
        default: Any = None
    ) -> Any:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            region: Cache region
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        value = self.cache.get(key, region, default)
        
        if value is not default:
            self.stats['hits'] += 1
        else:
            self.stats['misses'] += 1
        
        return value
    
    def get_many(
        self,
        keys: List[str],
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            region: Cache region
            
        Returns:
            Dictionary of key-value pairs
        """
        results = self.cache.get_many(keys, region)
        self.stats['hits'] += len(results)
        self.stats['misses'] += len(keys) - len(results)
        return results
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        region: Optional[str] = None,
        priority: CachePriority = CachePriority.NORMAL
    ) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            region: Cache region
            priority: Cache priority
            
        Returns:
            True if successful
        """
        ttl = ttl or self.default_ttl
        result = self.cache.set(key, value, ttl, region)
        
        if result:
            self.stats['writes'] += 1
            
        return result
    
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
            region: Cache region
            
        Returns:
            True if all successful
        """
        ttl = ttl or self.default_ttl
        result = self.cache.set_many(mapping, ttl, region)
        
        if result:
            self.stats['writes'] += len(mapping)
            
        return result
    
    def delete(
        self,
        key: str,
        region: Optional[str] = None
    ) -> bool:
        """
        Delete a value from cache.
        
        Args:
            key: Cache key
            region: Cache region
            
        Returns:
            True if deleted
        """
        result = self.cache.delete(key, region)
        
        if result:
            self.stats['invalidations'] += 1
            
        return result
    
    def delete_many(
        self,
        keys: List[str],
        region: Optional[str] = None
    ) -> int:
        """
        Delete multiple values from cache.
        
        Args:
            keys: List of cache keys
            region: Cache region
            
        Returns:
            Number of keys deleted
        """
        result = self.cache.delete_many(keys, region)
        self.stats['invalidations'] += result
        return result
    
    def exists(
        self,
        key: str,
        region: Optional[str] = None
    ) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            region: Cache region
            
        Returns:
            True if exists
        """
        return self.cache.exists(key, region)
    
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
            region: Cache region
            
        Returns:
            New value or None if failed
        """
        return self.cache.increment(key, amount, region)
    
    # ========================================================================
    # Strategy-based Operations
    # ========================================================================
    
    def cache_aside(
        self,
        key: str,
        loader: Callable[[], T],
        ttl: Optional[int] = None,
        region: Optional[str] = None,
        force_refresh: bool = False
    ) -> T:
        """
        Get or load value using cache-aside pattern.
        
        Args:
            key: Cache key
            loader: Function to load data on cache miss
            ttl: Time-to-live in seconds
            region: Cache region
            force_refresh: Force refresh even if cached
            
        Returns:
            Value from cache or loader
        """
        if force_refresh:
            # Skip cache, load fresh
            value = loader()
            if value is not None:
                self.set(key, value, ttl, region)
            return value
        
        return self.strategy_executor.execute_cache_aside(
            key, loader, ttl, region
        )
    
    def write_through(
        self,
        key: str,
        value: Any,
        writer: Callable[[Any], Any],
        ttl: Optional[int] = None,
        region: Optional[str] = None
    ) -> Any:
        """
        Write using write-through pattern.
        
        Args:
            key: Cache key
            value: Value to write
            writer: Function to write to database
            ttl: Time-to-live in seconds
            region: Cache region
            
        Returns:
            Written value
        """
        return self.strategy_executor.execute_write_through(
            key, value, writer, ttl, region
        )
    
    def write_behind(
        self,
        key: str,
        value: Any,
        writer: Callable[[Any], Any],
        ttl: Optional[int] = None,
        region: Optional[str] = None,
        delay_seconds: int = 5
    ) -> Any:
        """
        Write using write-behind pattern.
        
        Args:
            key: Cache key
            value: Value to write
            writer: Function to write to database
            ttl: Time-to-live in seconds
            region: Cache region
            delay_seconds: Delay before database write
            
        Returns:
            Value stored in cache
        """
        return self.strategy_executor.execute_write_behind(
            key, value, writer, ttl, region, delay_seconds
        )
    
    def refresh_ahead(
        self,
        key: str,
        loader: Callable[[], T],
        ttl: Optional[int] = None,
        refresh_threshold: float = 0.75,
        region: Optional[str] = None
    ) -> T:
        """
        Get value using refresh-ahead pattern.
        
        Args:
            key: Cache key
            loader: Function to load data
            ttl: Time-to-live in seconds
            refresh_threshold: Threshold to trigger refresh
            region: Cache region
            
        Returns:
            Cached value
        """
        ttl = ttl or self.default_ttl
        return self.strategy_executor.execute_refresh_ahead(
            key, loader, ttl, refresh_threshold, region
        )
    
    # ========================================================================
    # Cache Regions
    # ========================================================================
    
    def create_region(
        self,
        name: str,
        ttl: int = 300,
        max_size: Optional[int] = None,
        strategy: str = 'lru'
    ) -> Dict[str, Any]:
        """
        Create a cache region.
        
        Args:
            name: Region name
            ttl: Default TTL in seconds
            max_size: Maximum number of entries
            strategy: Eviction strategy
            
        Returns:
            Region configuration
        """
        region = self.cache.create_region(name, ttl, max_size, strategy)
        return {
            'id': region.id,
            'name': region.name,
            'ttl': region.ttl,
            'max_size': region.max_size,
            'strategy': region.strategy
        }
    
    def get_region_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a cache region."""
        region = self.cache.get_region(name)
        if not region:
            return None
        
        size = self.cache.get_size(name)
        
        return {
            'name': region.name,
            'ttl': region.ttl,
            'max_size': region.max_size,
            'strategy': region.strategy,
            'current_size': size,
            'utilization': (size / region.max_size * 100) if region.max_size else 0
        }
    
    def list_regions(self) -> List[str]:
        """List all cache regions."""
        regions = self.session.query(CacheRegionModel).all()
        return [r.name for r in regions]
    
    def delete_region(self, name: str) -> bool:
        """Delete a cache region and all its keys."""
        return self.cache.delete_region(name)
    
    # ========================================================================
    # Cache Warming
    # ========================================================================
    
    @with_retry(max_retries=3)
    def warmup_region(
        self,
        region: str,
        keys: Optional[List[str]] = None,
        parallel: bool = True,
        max_workers: int = 5
    ) -> Dict[str, Any]:
        """
        Warm up a cache region by pre-loading keys.
        
        Args:
            region: Region to warm up
            keys: Specific keys to warm up (None for all)
            parallel: Whether to warm up in parallel
            max_workers: Maximum parallel workers
            
        Returns:
            Warmup results
        """
        if not self.warmup_enabled:
            return {'status': 'disabled', 'region': region}
        
        start_time = datetime.utcnow()
        results = {
            'region': region,
            'total_keys': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'duration': 0
        }
        
        try:
            # Get keys to warm up
            if keys is None:
                keys = self._get_keys_for_warmup(region)
            
            results['total_keys'] = len(keys)
            
            if parallel and len(keys) > 1:
                # Parallel warmup
                import concurrent.futures
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_key = {
                        executor.submit(self._warmup_key, region, key): key
                        for key in keys
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_key):
                        key = future_to_key[future]
                        try:
                            success = future.result()
                            if success:
                                results['successful'] += 1
                            else:
                                results['failed'] += 1
                        except Exception as e:
                            logger.error(f"Warmup failed for key {key}: {e}")
                            results['failed'] += 1
            else:
                # Sequential warmup
                for key in keys:
                    if self._warmup_key(region, key):
                        results['successful'] += 1
                    else:
                        results['failed'] += 1
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            results['duration'] = round(duration, 2)
            results['skipped'] = results['total_keys'] - results['successful'] - results['failed']
            
            self.stats['warmups'] += 1
            
            logger.info(f"Warmup completed for region {region}: {results}")
            
        except Exception as e:
            logger.error(f"Warmup failed for region {region}: {e}")
            raise CacheWarmupException(f"Warmup failed: {e}")
        
        return results
    
    def _get_keys_for_warmup(self, region: str) -> List[str]:
        """
        Get list of keys to warm up for a region.
        
        This should be customized based on application needs.
        """
        # Placeholder - implement based on your data access patterns
        return []
    
    def _warmup_key(self, region: str, key: str) -> bool:
        """
        Warm up a single key.
        
        Args:
            region: Cache region
            key: Key to warm up
            
        Returns:
            True if successful
        """
        try:
            # Check if already cached
            if self.cache.exists(key, region):
                logger.debug(f"Key already cached: {key}")
                return True
            
            # Load data (this should be customized)
            value = self._load_data_for_warmup(region, key)
            
            if value is not None:
                ttl = self._get_region_ttl(region)
                self.cache.set(key, value, ttl, region)
                logger.debug(f"Warmed up key: {key}")
                return True
            else:
                logger.warning(f"No data to warm up for key: {key}")
                return False
                
        except Exception as e:
            logger.error(f"Error warming up key {key}: {e}")
            return False
    
    def _load_data_for_warmup(self, region: str, key: str) -> Any:
        """
        Load data for cache warmup.
        
        This should be customized based on your data sources.
        """
        # Placeholder - implement based on your data sources
        return None
    
    def _get_region_ttl(self, region: str) -> Optional[int]:
        """Get TTL for a region."""
        region_info = self.get_region_info(region)
        return region_info['ttl'] if region_info else self.default_ttl
    
    # ========================================================================
    # Cache Synchronization
    # ========================================================================
    
    def sync_cache(
        self,
        source_region: str,
        target_region: str,
        keys: Optional[List[str]] = None,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Synchronize cache between regions.
        
        Args:
            source_region: Source cache region
            target_region: Target cache region
            keys: Specific keys to sync (None for all)
            overwrite: Whether to overwrite existing keys
            
        Returns:
            Sync results
        """
        if not self.sync_enabled:
            return {'status': 'disabled', 'source': source_region, 'target': target_region}
        
        start_time = datetime.utcnow()
        results = {
            'source_region': source_region,
            'target_region': target_region,
            'total_keys': 0,
            'synced': 0,
            'skipped': 0,
            'failed': 0,
            'duration': 0
        }
        
        try:
            # Get keys to sync
            if keys is None:
                # Get all keys from source region
                keys = self.cache.get_keys(region=source_region)
            
            results['total_keys'] = len(keys)
            
            for key in keys:
                try:
                    # Check if already exists in target
                    if not overwrite and self.cache.exists(key, target_region):
                        results['skipped'] += 1
                        continue
                    
                    # Get from source
                    value = self.cache.get(key, source_region)
                    
                    if value is not None:
                        # Get TTL from source
                        ttl = self.cache.ttl(key, source_region)
                        
                        # Store in target
                        self.cache.set(key, value, ttl, target_region)
                        results['synced'] += 1
                    else:
                        results['failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Sync failed for key {key}: {e}")
                    results['failed'] += 1
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            results['duration'] = round(duration, 2)
            
            self.stats['syncs'] += 1
            
            logger.info(f"Cache sync completed: {results}")
            
        except Exception as e:
            logger.error(f"Cache sync failed: {e}")
            raise CacheSyncException(f"Sync failed: {e}")
        
        return results
    
    # ========================================================================
    # Cache Statistics
    # ========================================================================
    
    def get_statistics(self, reset: bool = False) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Args:
            reset: Whether to reset statistics after retrieval
            
        Returns:
            Cache statistics
        """
        stats = self.stats.copy()
        
        # Add repository statistics
        repo_stats = self.cache.get_statistics()
        
        stats.update({
            'hit_rate': self._calculate_hit_rate(),
            'miss_rate': self._calculate_miss_rate(),
            'repository': {
                'hits': repo_stats.hits if repo_stats else 0,
                'misses': repo_stats.misses if repo_stats else 0,
                'writes': repo_stats.writes if repo_stats else 0,
                'invalidations': repo_stats.invalidations if repo_stats else 0,
                'errors': repo_stats.errors if repo_stats else 0
            }
        })
        
        if reset:
            self.reset_statistics()
        
        return stats
    
    def reset_statistics(self) -> None:
        """Reset cache statistics."""
        self.stats = {
            'hits': 0,
            'misses': 0,
            'writes': 0,
            'invalidations': 0,
            'warmups': 0,
            'syncs': 0
        }
        logger.info("Cache statistics reset")
    
    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.stats['hits'] + self.stats['misses']
        if total == 0:
            return 0.0
        return round((self.stats['hits'] / total) * 100, 2)
    
    def _calculate_miss_rate(self) -> float:
        """Calculate cache miss rate."""
        total = self.stats['hits'] + self.stats['misses']
        if total == 0:
            return 0.0
        return round((self.stats['misses'] / total) * 100, 2)
    
    # ========================================================================
    # Cache Maintenance
    # ========================================================================
    
    def cleanup_expired(self) -> int:
        """Remove expired entries from cache."""
        count = self.cache.cleanup_expired()
        logger.info(f"Cleaned up {count} expired cache entries")
        return count
    
    def clear_all(self) -> int:
        """Clear all cache entries."""
        count = self.cache.clear_all()
        logger.info(f"Cleared all cache entries: {count}")
        return count
    
    def get_cache_size(self, region: Optional[str] = None) -> int:
        """Get cache size."""
        return self.cache.get_size(region)
    
    def get_keys(self, pattern: str = "*", region: Optional[str] = None) -> List[str]:
        """Get cache keys matching pattern."""
        return self.cache.get_keys(pattern, region)
    
    # ========================================================================
    # Cache Health
    # ========================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform cache health check.
        
        Returns:
            Health check results
        """
        results = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'cache': 'unknown',
            'statistics': self.get_statistics(),
            'regions': []
        }
        
        # Test cache connectivity
        try:
            test_key = "health_check"
            test_value = "ok"
            self.cache.set(test_key, test_value, ttl=5)
            retrieved = self.cache.get(test_key)
            self.cache.delete(test_key)
            
            if retrieved == test_value:
                results['cache'] = 'connected'
            else:
                results['cache'] = 'degraded'
                results['status'] = 'degraded'
                
        except Exception as e:
            results['cache'] = f'error: {e}'
            results['status'] = 'unhealthy'
        
        # Check regions
        for region in self.list_regions():
            region_info = self.get_region_info(region)
            if region_info:
                results['regions'].append(region_info)
        
        return results


# ============================================================================
# Cache Decorators
# ============================================================================

def cached(
    ttl: Optional[int] = None,
    region: Optional[str] = None,
    key_builder: Optional[Callable[..., str]] = None,
    strategy: str = 'cache_aside'
):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds
        region: Cache region
        key_builder: Function to build cache key
        strategy: Caching strategy ('cache_aside', 'refresh_ahead')
    
    Example:
        @cached(ttl=300)
        def get_user(user_id: int):
            return user_service.get_user(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache service from first argument if it's a class instance
            cache_service = None
            if args and hasattr(args[0], 'cache_service'):
                cache_service = args[0].cache_service
            
            if not cache_service:
                # Try to get from global context
                try:
                    from flask import current_app
                    cache_service = current_app.cache_service if current_app else None
                except:
                    pass
            
            if not cache_service:
                # No cache service available, just execute function
                return func(*args, **kwargs)
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend([str(a) for a in args])
                key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
                cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
            
            # Execute based on strategy
            if strategy == 'refresh_ahead':
                return cache_service.refresh_ahead(
                    cache_key,
                    lambda: func(*args, **kwargs),
                    ttl,
                    region=region
                )
            else:
                return cache_service.cache_aside(
                    cache_key,
                    lambda: func(*args, **kwargs),
                    ttl,
                    region
                )
        
        return wrapper
    return decorator


def invalidates_cache(keys: List[str], region: Optional[str] = None):
    """
    Decorator to invalidate cache keys after function execution.
    
    Args:
        keys: List of cache keys to invalidate (can include {arg} placeholders)
        region: Cache region
    
    Example:
        @invalidates_cache(['user:{user_id}', 'users:list'])
        def update_user(user_id: int, data: dict):
            return user_service.update_user(user_id, data)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Execute function
            result = func(*args, **kwargs)
            
            # Get cache service
            cache_service = None
            if args and hasattr(args[0], 'cache_service'):
                cache_service = args[0].cache_service
            
            if cache_service:
                # Process keys with argument placeholders
                processed_keys = []
                arg_dict = {}
                
                # Map positional args to names
                import inspect
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                arg_dict = bound_args.arguments
                
                for key_template in keys:
                    try:
                        # Replace placeholders like {user_id} with actual values
                        processed_key = key_template.format(**arg_dict)
                        processed_keys.append(processed_key)
                    except KeyError:
                        # If placeholder not found, use as-is
                        processed_keys.append(key_template)
                
                # Invalidate keys
                cache_service.delete_many(processed_keys, region)
                logger.debug(f"Invalidated cache keys: {processed_keys}")
            
            return result
        return wrapper
    return decorator


def rate_limited(max_calls: int, period: int, key_func: Optional[Callable] = None):
    """
    Decorator to rate limit function calls using cache.
    
    Args:
        max_calls: Maximum calls in the period
        period: Period in seconds
        key_func: Function to generate rate limit key
    
    Example:
        @rate_limited(max_calls=10, period=60)
        def api_call(user_id: int):
            return external_api.call()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache service
            cache_service = None
            if args and hasattr(args[0], 'cache_service'):
                cache_service = args[0].cache_service
            
            if not cache_service:
                return func(*args, **kwargs)
            
            # Generate rate limit key
            if key_func:
                rate_key = key_func(*args, **kwargs)
            else:
                # Default key based on function and first argument
                user_id = args[1] if len(args) > 1 else 'anonymous'
                rate_key = f"rate_limit:{func.__name__}:{user_id}"
            
            # Get current count
            count = cache_service.get(rate_key, default=0)
            
            if count >= max_calls:
                # Rate limit exceeded
                import time
                retry_after = cache_service.cache.ttl(rate_key)
                raise ServiceException(
                    f"Rate limit exceeded. Max {max_calls} calls per {period}s. "
                    f"Try again in {retry_after} seconds."
                )
            
            # Increment count
            cache_service.increment(rate_key)
            
            # Set expiry on first call
            if count == 0:
                cache_service.cache.expire(rate_key, period)
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main service
    'CacheService',
    
    # Strategy executor
    'CacheStrategyExecutor',
    
    # Exceptions
    'CacheServiceException',
    'CacheStrategyException',
    'CacheWarmupException',
    'CacheSyncException',
    
    # Decorators
    'cached',
    'invalidates_cache',
    'rate_limited',
]