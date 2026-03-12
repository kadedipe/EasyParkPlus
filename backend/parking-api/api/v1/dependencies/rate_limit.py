"""
Rate limiting dependencies.
"""

import time
import hashlib
from typing import Optional, Dict, Callable
from functools import wraps
from fastapi import Request, HTTPException, Depends
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from ....services.redis import redis_client
from ....core.config import settings
from ....utils.logger import logger


class RateLimiter:
    """
    Rate limiter using Redis.
    """
    
    def __init__(
        self,
        times: int = 100,
        seconds: int = 60,
        prefix: str = "rate_limit"
    ):
        self.times = times
        self.seconds = seconds
        self.prefix = prefix
    
    async def __call__(self, request: Request):
        """
        Apply rate limiting to request.
        """
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Create rate limit key
        key = f"{self.prefix}:{client_id}:{request.url.path}"
        
        if redis_client:
            await self._check_redis_rate_limit(key)
        else:
            self._check_memory_rate_limit(key)
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get unique client identifier.
        """
        # Use user ID if authenticated
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        # Use API key if provided
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{hashlib.md5(api_key.encode()).hexdigest()}"
        
        # Fallback to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return f"ip:{ip}"
    
    async def _check_redis_rate_limit(self, key: str):
        """
        Check rate limit using Redis.
        """
        now = time.time()
        window_start = now - self.seconds
        
        try:
            # Remove old requests
            await redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            current = await redis_client.zcard(key)
            
            if current >= self.times:
                # Get oldest request time for Retry-After header
                oldest = await redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + self.seconds - now)
                else:
                    retry_after = self.seconds
                
                raise HTTPException(
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "limit": self.times,
                        "remaining": 0,
                        "reset_after": retry_after
                    },
                    headers={
                        "X-RateLimit-Limit": str(self.times),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(now + retry_after)),
                        "Retry-After": str(retry_after)
                    }
                )
            
            # Add current request
            await redis_client.zadd(key, {str(now): now})
            await redis_client.expire(key, self.seconds)
            
            # Add rate limit headers to response
            request.state.rate_limit = {
                "limit": self.times,
                "remaining": self.times - current - 1,
                "reset": int(now + self.seconds)
            }
            
        except Exception as e:
            logger.error(f"Redis rate limit error: {str(e)}")
            # Fall back to memory rate limiting
            self._check_memory_rate_limit(key)
    
    def _check_memory_rate_limit(self, key: str):
        """
        Fallback in-memory rate limiting.
        """
        # This is a simplified version - in production, use a proper
        # in-memory store with cleanup
        if not hasattr(self, '_memory_store'):
            self._memory_store = {}
        
        now = time.time()
        window_start = now - self.seconds
        
        # Clean old entries
        if key in self._memory_store:
            self._memory_store[key] = [
                ts for ts in self._memory_store[key]
                if ts > window_start
            ]
        else:
            self._memory_store[key] = []
        
        # Check limit
        if len(self._memory_store[key]) >= self.times:
            retry_after = int(self._memory_store[key][0] + self.seconds - now)
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add current request
        self._memory_store[key].append(now)


class PerUserRateLimiter(RateLimiter):
    """
    Rate limiter per user.
    """
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get user ID for rate limiting.
        """
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"
        
        # Fall back to IP if not authenticated
        return super()._get_client_id(request)


class PerIPRateLimiter(RateLimiter):
    """
    Rate limiter per IP address.
    """
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get IP address for rate limiting.
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return f"ip:{ip}"


class PerEndpointRateLimiter(RateLimiter):
    """
    Rate limiter per endpoint.
    """
    
    async def __call__(self, request: Request):
        """
        Apply endpoint-specific rate limiting.
        """
        # Different limits for different endpoints
        path = request.url.path
        
        if "/auth/" in path:
            self.times = 10
            self.seconds = 300
        elif "/payments/" in path:
            self.times = 30
            self.seconds = 60
        elif "/admin/" in path:
            self.times = 200
            self.seconds = 60
        else:
            self.times = 100
            self.seconds = 60
        
        await super().__call__(request)


def rate_limit(
    times: int = 100,
    seconds: int = 60,
    by_user: bool = False,
    by_ip: bool = True
):
    """
    Decorator for rate limiting endpoints.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs
            request = None
            for key, value in kwargs.items():
                if isinstance(value, Request):
                    request = value
                    break
            
            if not request:
                # Try to find in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if request:
                # Apply rate limiting
                if by_user:
                    limiter = PerUserRateLimiter(times, seconds)
                elif by_ip:
                    limiter = PerIPRateLimiter(times, seconds)
                else:
                    limiter = RateLimiter(times, seconds)
                
                await limiter(request)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def get_rate_limiter(
    request: Request,
    times: int = 100,
    seconds: int = 60
) -> RateLimiter:
    """
    Dependency for getting rate limiter instance.
    """
    return RateLimiter(times, seconds)


class RateLimitConfig:
    """
    Configuration for different rate limits.
    """
    
    def __init__(self):
        self.limits: Dict[str, tuple] = {
            "default": (100, 60),
            "auth": (10, 300),
            "payments": (30, 60),
            "admin": (200, 60),
            "public": (1000, 3600)
        }
    
    def get_limit(self, endpoint: str) -> tuple:
        """
        Get rate limit for endpoint.
        """
        for key, limit in self.limits.items():
            if key in endpoint:
                return limit
        return self.limits["default"]


class DynamicRateLimiter:
    """
    Rate limiter that adjusts based on user tier.
    """
    
    def __init__(self):
        self.tier_limits = {
            "free": (50, 60),
            "basic": (200, 60),
            "premium": (1000, 60),
            "enterprise": (5000, 60)
        }
    
    async def get_limit_for_user(self, user_tier: str) -> tuple:
        """
        Get rate limit for user tier.
        """
        return self.tier_limits.get(user_tier, self.tier_limits["free"])
    
    async def __call__(self, request: Request):
        """
        Apply tier-based rate limiting.
        """
        # Get user tier from request state
        user_tier = "free"
        if hasattr(request.state, "user_tier"):
            user_tier = request.state.user_tier
        
        times, seconds = await self.get_limit_for_user(user_tier)
        
        limiter = RateLimiter(times, seconds)
        await limiter(request)