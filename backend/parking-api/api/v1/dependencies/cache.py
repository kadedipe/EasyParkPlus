"""
Caching dependencies.
"""

import json
import hashlib
from typing import Optional, Any, Callable, TypeVar, Union
from functools import wraps
from fastapi import Request, Response
from starlette.responses import JSONResponse

from ....services.redis import redis_client
from ....utils.logger import logger

T = TypeVar('T')


class Cache:
    """
    Cache manager for API responses.
    """
    
    def __init__(self, prefix: str = "cache"):
        self.prefix = prefix
        self.default_ttl = 300  # 5 minutes
    
    def _make_key(self, key: str) -> str:
        """
        Create full cache key with prefix.
        """
        return f"{self.prefix}:{key}"
    
    def _hash_key(self, data: Any) -> str:
        """
        Create hash from data for cache key.
        """
        if isinstance(data, (dict, list)):
            data = json.dumps(data, sort_keys=True)
        elif not isinstance(data, str):
            data = str(data)
        
        return hashlib.md5(data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        """
        if not redis_client:
            return None
        
        try:
            full_key = self._make_key(key)
            data = await redis_client.get(full_key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.
        """
        if not redis_client:
            return
        
        try:
            full_key = self._make_key(key)
            ttl = ttl or self.default_ttl
            await redis_client.setex(
                full_key,
                ttl,
                json.dumps(value, default=str)
            )
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
    
    async def delete(self, key: str):
        """
        Delete value from cache.
        """
        if not redis_client:
            return
        
        try:
            full_key = self._make_key(key)
            await redis_client.delete(full_key)
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
    
    async def delete_pattern(self, pattern: str):
        """
        Delete all keys matching pattern.
        """
        if not redis_client:
            return
        
        try:
            full_pattern = self._make_key(pattern)
            keys = await redis_client.keys(full_pattern)
            if keys:
                await redis_client.delete(*keys)
        except Exception as e:
            logger.error(f"Cache delete pattern error: {str(e)}")
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        """
        if not redis_client:
            return False
        
        try:
            full_key = self._make_key(key)
            return await redis_client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {str(e)}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment counter in cache.
        """
        if not redis_client:
            return None
        
        try:
            full_key = self._make_key(key)
            return await redis_client.incrby(full_key, amount)
        except Exception as e:
            logger.error(f"Cache increment error: {str(e)}")
            return None


def cache_response(
    ttl: Optional[int] = None,
    key_func: Optional[Callable] = None,
    vary_on_user: bool = True,
    vary_on_headers: Optional[list] = None
):
    """
    Decorator for caching API responses.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs
            request = None
            for value in kwargs.values():
                if isinstance(value, Request):
                    request = value
                    break
            
            if not request:
                # Try to find in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request or request.method != "GET":
                # Only cache GET requests
                return await func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = await generate_cache_key(
                    request,
                    vary_on_user,
                    vary_on_headers
                )
            
            # Try to get from cache
            cache = Cache()
            cached_response = await cache.get(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for {cache_key}")
                return JSONResponse(
                    content=cached_response,
                    headers={"X-Cache": "HIT"}
                )
            
            # Execute function
            response = await func(*args, **kwargs)
            
            # Cache response
            if isinstance(response, Response):
                # Extract response data
                if hasattr(response, 'body'):
                    try:
                        data = json.loads(response.body)
                        await cache.set(cache_key, data, ttl)
                    except:
                        pass
            elif isinstance(response, dict):
                await cache.set(cache_key, response, ttl)
            
            return response
        return wrapper
    return decorator


async def generate_cache_key(
    request: Request,
    vary_on_user: bool = True,
    vary_on_headers: Optional[list] = None
) -> str:
    """
    Generate cache key from request.
    """
    parts = [
        request.method,
        request.url.path,
        str(sorted(request.query_params.items()))
    ]
    
    if vary_on_user and hasattr(request.state, "user_id"):
        parts.append(f"user:{request.state.user_id}")
    
    if vary_on_headers:
        for header in vary_on_headers:
            value = request.headers.get(header)
            if value:
                parts.append(f"{header}:{value}")
    
    # Hash the key
    key_string = ":".join(parts)
    return hashlib.md5(key_string.encode()).hexdigest()


async def invalidate_cache(pattern: str):
    """
    Invalidate cache keys matching pattern.
    """
    cache = Cache()
    await cache.delete_pattern(pattern)


def cache_invalidator(pattern: str):
    """
    Decorator to invalidate cache after function execution.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await invalidate_cache(pattern)
            return result
        return wrapper
    return decorator


class CacheManager:
    """
    Cache manager for different resource types.
    """
    
    def __init__(self):
        self.cache = Cache()
    
    async def get_user_cache(self, user_id: str, key: str) -> Optional[Any]:
        """
        Get user-specific cache.
        """
        return await self.cache.get(f"user:{user_id}:{key}")
    
    async def set_user_cache(self, user_id: str, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set user-specific cache.
        """
        await self.cache.set(f"user:{user_id}:{key}", value, ttl)
    
    async def clear_user_cache(self, user_id: str):
        """
        Clear all cache for user.
        """
        await self.cache.delete_pattern(f"user:{user_id}:*")
    
    async def get_resource_cache(self, resource_type: str, resource_id: str) -> Optional[Any]:
        """
        Get resource-specific cache.
        """
        return await self.cache.get(f"{resource_type}:{resource_id}")
    
    async def set_resource_cache(
        self,
        resource_type: str,
        resource_id: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """
        Set resource-specific cache.
        """
        await self.cache.set(f"{resource_type}:{resource_id}", value, ttl)
    
    async def clear_resource_cache(self, resource_type: str, resource_id: str):
        """
        Clear resource cache.
        """
        await self.cache.delete(f"{resource_type}:{resource_id}")


async def get_cache() -> Cache:
    """
    Dependency for getting cache instance.
    """
    return Cache()


class CacheControl:
    """
    Cache-Control header builder.
    """
    
    def __init__(self):
        self.directives = []
    
    def public(self):
        """Make response public."""
        self.directives.append("public")
        return self
    
    def private(self):
        """Make response private."""
        self.directives.append("private")
        return self
    
    def max_age(self, seconds: int):
        """Set max-age directive."""
        self.directives.append(f"max-age={seconds}")
        return self
    
    def s_maxage(self, seconds: int):
        """Set s-maxage directive."""
        self.directives.append(f"s-maxage={seconds}")
        return self
    
    def no_cache(self):
        """Add no-cache directive."""
        self.directives.append("no-cache")
        return self
    
    def no_store(self):
        """Add no-store directive."""
        self.directives.append("no-store")
        return self
    
    def must_revalidate(self):
        """Add must-revalidate directive."""
        self.directives.append("must-revalidate")
        return self
    
    def proxy_revalidate(self):
        """Add proxy-revalidate directive."""
        self.directives.append("proxy-revalidate")
        return self
    
    def build(self) -> str:
        """
        Build Cache-Control header value.
        """
        return ", ".join(self.directives)