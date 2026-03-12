"""
Request/response logging middleware.
"""

import time
import uuid
import json
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ....utils.logger import logger
from ....core.config import settings


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging requests and responses.
    """
    
    def __init__(self, app: ASGIApp, log_headers: bool = False, log_body: bool = False):
        super().__init__(app)
        self.log_headers = log_headers
        self.log_body = log_body
        
        # Paths to exclude from logging
        self.exclude_paths = [
            "/health",
            "/metrics",
            "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """
        Log request and response details.
        """
        # Skip logging for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        await self._log_request(request)
        
        # Process request and measure time
        start_time = time.time()
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            await self._log_response(request, response, process_time)
            
            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Log exception
            process_time = time.time() - start_time
            await self._log_exception(request, e, process_time)
            raise
    
    def _should_exclude(self, path: str) -> bool:
        """
        Check if path should be excluded from logging.
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    async def _log_request(self, request: Request):
        """
        Log request details.
        """
        log_data = {
            "type": "request",
            "request_id": getattr(request.state, "request_id", None),
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
        }
        
        # Add headers if configured
        if self.log_headers:
            log_data["headers"] = dict(request.headers)
        
        # Add user ID if authenticated
        if hasattr(request.state, "user_id"):
            log_data["user_id"] = request.state.user_id
        
        logger.info(f"Request: {json.dumps(log_data)}")
    
    async def _log_response(self, request: Request, response, process_time: float):
        """
        Log response details.
        """
        log_data = {
            "type": "response",
            "request_id": getattr(request.state, "request_id", None),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
        }
        
        # Add response size if available
        content_length = response.headers.get("content-length")
        if content_length:
            log_data["content_length"] = int(content_length)
        
        log_level = logger.info if response.status_code < 400 else logger.error
        log_level(f"Response: {json.dumps(log_data)}")
    
    async def _log_exception(self, request: Request, exc: Exception, process_time: float):
        """
        Log exception details.
        """
        log_data = {
            "type": "exception",
            "request_id": getattr(request.state, "request_id", None),
            "method": request.method,
            "path": request.url.path,
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
            "process_time_ms": round(process_time * 1000, 2),
        }
        
        logger.error(f"Exception: {json.dumps(log_data)}", exc_info=True)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding request ID to each request.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Add request ID to request state and response headers.
        """
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Store in request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response