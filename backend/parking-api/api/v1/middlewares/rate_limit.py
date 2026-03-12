"""
Rate limiting middleware to prevent abuse.
"""

import time
from typing import Dict, Tuple, Optional
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from ....core.config import settings
from ....services.redis import redis_client
from ....utils.logger import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis for distributed rate limiting.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        default_limit: int = 100,
        default_window: int = 60,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
        
        # Rate limit configurations for different endpoints
        self.limits = {
            "auth": {"limit": 10, "window": 300},  # 10 requests per 5 minutes
            "api": {"limit": 100, "window": 60},   # 100 requests per minute
            "admin": {"limit": 200, "window": 60}, # 200 requests per minute
        }
        
        # Local rate limiting fallback (when Redis is unavailable)
        self.local_counts: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        """
        Apply rate limiting to the request.
        """
        # Skip rate limiting for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        # Get client identifier (IP or user ID if authenticated)
        client_id = await self._get_client_id(request)
        
        # Get rate limit for this endpoint
        limit, window = self._get_rate_limit(request)
        
        # Check rate limit
        if await self._is_rate_limited(client_id, limit, window, request.url.path):
            return await self._rate_limit_exceeded_response(limit, window)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        await self._add_rate_limit_headers(response, client_id, limit, window)
        
        return response
    
    def _should_exclude(self, path: str) -> bool:
        """
        Check if path should be excluded from rate limiting.
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    async def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier (user ID if authenticated, otherwise IP).
        """
        # Use user ID if authenticated
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        # Otherwise use IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host}"
    
    def _get_rate_limit(self, request: Request) -> Tuple[int, int]:
        """
        Get rate limit for the endpoint.
        """
        path = request.url.path
        
        if "/auth/" in path:
            limit_config = self.limits["auth"]
        elif "/admin/" in path:
            limit_config = self.limits["admin"]
        else:
            limit_config = self.limits["api"]
        
        return limit_config["limit"], limit_config["window"]
    
    async def _is_rate_limited(self, client_id: str, limit: int, window: int, path: str) -> bool:
        """
        Check if client has exceeded rate limit.
        """
        # Try Redis first
        if redis_client:
            return await self._check_redis_rate_limit(client_id, limit, window, path)
        
        # Fallback to local rate limiting
        return self._check_local_rate_limit(client_id, limit, window, path)
    
    async def _check_redis_rate_limit(self, client_id: str, limit: int, window: int, path: str) -> bool:
        """
        Check rate limit using Redis.
        """
        key = f"rate_limit:{client_id}:{path}"
        
        try:
            # Use Redis Lua script for atomic operation
            lua_script = """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            
            redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
            
            local current = redis.call('ZCARD', key)
            if current < limit then
                redis.call('ZADD', key, now, now)
                redis.call('EXPIRE', key, window)
                return {current + 1, limit}
            end
            
            return {current, limit}
            """
            
            now = time.time()
            result = await redis_client.eval(
                lua_script,
                1,
                key,
                limit,
                window,
                now
            )
            
            current_count, _ = result
            return current_count > limit
            
        except Exception as e:
            logger.error(f"Redis rate limit error: {str(e)}")
            # Fallback to local
            return self._check_local_rate_limit(client_id, limit, window, path)
    
    def _check_local_rate_limit(self, client_id: str, limit: int, window: int, path: str) -> bool:
        """
        Local in-memory rate limiting fallback.
        """
        key = f"{client_id}:{path}"
        now = time.time()
        
        # Clean old entries
        self.local_counts[key] = [
            timestamp for timestamp in self.local_counts[key]
            if timestamp > now - window
        ]
        
        # Check limit
        if len(self.local_counts[key]) >= limit:
            return True
        
        # Add current request
        self.local_counts[key].append(now)
        return False
    
    async def _rate_limit_exceeded_response(self, limit: int, window: int):
        """
        Return rate limit exceeded response.
        """
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Maximum {limit} requests per {window} seconds."
                }
            },
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Reset": str(int(time.time() + window)),
                "Retry-After": str(window)
            }
        )
    
    async def _add_rate_limit_headers(self, response, client_id: str, limit: int, window: int):
        """
        Add rate limit headers to response.
        """
        if redis_client:
            key = f"rate_limit:{client_id}"
            try:
                current = await redis_client.zcard(key)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current))
                
                # Get oldest timestamp to calculate reset time
                oldest = await redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    reset_time = int(oldest[0][1]) + window
                    response.headers["X-RateLimit-Reset"] = str(reset_time)
            except:
                pass