"""
Response caching middleware.
"""

import hashlib
import json
from typing import Optional, Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp

from ....services.redis import redis_client
from ....utils.logger import logger


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware for caching responses.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        cache_control: Optional[dict] = None,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.cache_control = cache_control or {
            "default": 300,  # 5 minutes
            "public": 60,    # 1 minute
            "private": 0,    # no cache
        }
        self.exclude_paths = exclude_paths or [
            "/auth",
            "/payments",
            "/admin"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Cache responses for GET requests.
        """
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Skip caching for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        # Check if client sent cache-control headers
        cache_control_header = request.headers.get("cache-control", "")
        if "no-cache" in cache_control_header or "no-store" in cache_control_header:
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to get from cache
        if redis_client:
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_response
        
        # Process request
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200:
            cache_ttl = self._get_cache_ttl(request, response)
            if cache_ttl > 0 and redis_client:
                await self._cache_response(cache_key, response, cache_ttl)
        
        return response
    
    def _should_exclude(self, path: str) -> bool:
        """
        Check if path should be excluded from caching.
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    def _generate_cache_key(self, request: Request) -> str:
        """
        Generate cache key from request.
        """
        # Include path, query params, and authorization status
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items())),
            "auth" if hasattr(request.state, "user_id") else "noauth"
        ]
        
        # Hash the key
        key_string = ":".join(key_parts)
        hashed = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"cache:{hashed}"
    
    def _get_cache_ttl(self, request: Request, response: Response) -> int:
        """
        Determine cache TTL for response.
        """
        # Check if response has cache-control header
        response_cache_control = response.headers.get("cache-control", "")
        
        if "no-cache" in response_cache_control or "no-store" in response_cache_control:
            return 0
        
        # Check for authenticated routes
        if hasattr(request.state, "user_id"):
            return self.cache_control["private"]
        
        # Check if path is public
        if request.url.path.startswith("/public"):
            return self.cache_control["public"]
        
        # Default TTL
        return self.cache_control["default"]
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Response]:
        """
        Retrieve cached response from Redis.
        """
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                
                # Reconstruct response
                return JSONResponse(
                    content=data["content"],
                    status_code=data["status_code"],
                    headers=data["headers"]
                )
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
        
        return None
    
    async def _cache_response(self, cache_key: str, response: Response, ttl: int):
        """
        Cache response in Redis.
        """
        try:
            # Get response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Parse JSON if possible
            try:
                content = json.loads(body)
            except:
                content = {"data": body.decode()}
            
            # Prepare cache data
            cache_data = {
                "content": content,
                "status_code": response.status_code,
                "headers": dict(response.headers)
            }
            
            # Store in Redis
            await redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data)
            )
            
            # Recreate response body iterator
            response.body_iterator = self._chunk_generator(body)
            
        except Exception as e:
            logger.error(f"Error caching response: {str(e)}")
    
    async def _chunk_generator(self, body: bytes):
        """
        Generate chunks from body.
        """
        yield body


class ConditionalCacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling conditional requests (If-None-Match, If-Modified-Since).
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Handle conditional requests.
        """
        # Only handle GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Check for conditional headers
        if_none_match = request.headers.get("if-none-match")
        if_modified_since = request.headers.get("if-modified-since")
        
        if not if_none_match and not if_modified_since:
            return await call_next(request)
        
        # Generate ETag for request
        etag = self._generate_etag(request)
        
        # Check if resource hasn't changed
        if if_none_match and if_none_match == etag:
            return Response(status_code=304)
        
        response = await call_next(request)
        
        # Add ETag to response
        response.headers["ETag"] = etag
        
        return response
    
    def _generate_etag(self, request: Request) -> str:
        """
        Generate ETag for request.
        """
        # Create unique identifier based on request
        etag_source = f"{request.method}:{request.url.path}:{sorted(request.query_params.items())}"
        return hashlib.md5(etag_source.encode()).hexdigest()