"""
Request timeout middleware.
"""

import asyncio
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from ....utils.logger import logger


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling request timeouts.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        timeout_seconds: int = 30,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.timeout_seconds = timeout_seconds
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next):
        """
        Apply timeout to request processing.
        """
        # Skip timeout for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        try:
            # Process request with timeout
            return await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds
            )
            
        except asyncio.TimeoutError:
            # Log timeout
            logger.warning(
                f"Request timeout after {self.timeout_seconds}s: "
                f"{request.method} {request.url.path}"
            )
            
            # Return timeout response
            return JSONResponse(
                status_code=504,
                content={
                    "status": "error",
                    "error": {
                        "code": "TIMEOUT_ERROR",
                        "message": f"Request timeout after {self.timeout_seconds} seconds"
                    }
                }
            )
    
    def _should_exclude(self, path: str) -> bool:
        """
        Check if path should be excluded from timeout.
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False


class SlowRequestMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detecting and logging slow requests.
    """
    
    def __init__(self, app: ASGIApp, slow_threshold: float = 1.0):
        super().__init__(app)
        self.slow_threshold = slow_threshold
    
    async def dispatch(self, request: Request, call_next):
        """
        Detect slow requests and log them.
        """
        start_time = time.time()
        
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log if request is slow
        if duration > self.slow_threshold:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {duration:.2f}s (threshold: {self.slow_threshold}s)"
            )
            
            # Add warning header
            response.headers["X-Slow-Request"] = str(duration)
        
        return response