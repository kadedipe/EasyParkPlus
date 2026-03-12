"""
Authentication middleware for JWT token validation.
"""

import jwt
from typing import Optional, Tuple
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ....core.config import settings
from ....core.security import decode_token
from ....services.redis import redis_client
from ....utils.logger import logger


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for authenticating requests using JWT tokens.
    """
    
    def __init__(self, app: ASGIApp, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/login/json",
            "/api/v1/auth/refresh",
            "/api/v1/auth/request-reset",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/verify-email",
        ]
        self.security = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and validate authentication.
        """
        # Skip authentication for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        # Extract and validate token
        token = await self._extract_token(request)
        if not token:
            return await self._unauthorized_response("Missing or invalid authentication token")
        
        # Check if token is blacklisted
        if await self._is_token_blacklisted(token):
            return await self._unauthorized_response("Token has been revoked")
        
        # Validate token
        payload = await self._validate_token(token)
        if not payload:
            return await self._unauthorized_response("Invalid or expired token")
        
        # Attach user info to request state
        request.state.user_id = payload.get("sub")
        request.state.user_role = payload.get("role")
        request.state.token = token
        
        # Process request
        response = await call_next(request)
        return response
    
    def _should_exclude(self, path: str) -> bool:
        """
        Check if path should be excluded from authentication.
        """
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """
        Extract JWT token from Authorization header.
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return None
            return token
        except ValueError:
            return None
    
    async def _validate_token(self, token: str) -> Optional[dict]:
        """
        Validate JWT token and return payload.
        """
        try:
            payload = decode_token(token)
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None
    
    async def _is_token_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted in Redis.
        """
        if not redis_client:
            return False
        
        # Check if token is in blacklist
        blacklisted = await redis_client.get(f"blacklist:{token}")
        return bool(blacklisted)
    
    async def _unauthorized_response(self, detail: str):
        """
        Return unauthorized response.
        """
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={
                "status": "error",
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": detail
                }
            }
        )


class OptionalAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that authenticates if token provided but doesn't require it.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and authenticate if token provided.
        """
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = decode_token(token)
                request.state.user_id = payload.get("sub")
                request.state.user_role = payload.get("role")
                request.state.is_authenticated = True
            except:
                request.state.is_authenticated = False
        else:
            request.state.is_authenticated = False
        
        return await call_next(request)