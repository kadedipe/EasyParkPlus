"""
Global error handling middleware.
"""

import traceback
from typing import Union, Dict, Any
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from ....core.config import settings
from ....utils.logger import logger
from ....utils.exceptions import (
    AppException,
    NotFoundException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ConflictException,
    RateLimitException,
    ServiceUnavailableException
)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling errors and formatting error responses.
    """
    
    def __init__(self, app: ASGIApp, debug: bool = False):
        super().__init__(app)
        self.debug = debug
    
    async def dispatch(self, request: Request, call_next):
        """
        Handle errors and format responses.
        """
        try:
            return await call_next(request)
            
        except HTTPException as e:
            return await self._handle_http_exception(request, e)
            
        except RequestValidationError as e:
            return await self._handle_validation_error(request, e)
            
        except AppException as e:
            return await self._handle_app_exception(request, e)
            
        except Exception as e:
            return await self._handle_unexpected_error(request, e)
    
    async def _handle_http_exception(self, request: Request, exc: HTTPException) -> JSONResponse:
        """
        Handle FastAPI HTTP exceptions.
        """
        error_response = self._build_error_response(
            code="HTTP_ERROR",
            message=exc.detail,
            status_code=exc.status_code
        )
        
        # Log error
        logger.error(f"HTTP {exc.status_code}: {exc.detail}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers=exc.headers
        )
    
    async def _handle_validation_error(self, request: Request, exc: RequestValidationError) -> JSONResponse:
        """
        Handle request validation errors.
        """
        errors = []
        for error in exc.errors():
            errors.append({
                "loc": " -> ".join(str(loc) for loc in error["loc"]),
                "msg": error["msg"],
                "type": error["type"]
            })
        
        error_response = self._build_error_response(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=422,
            details={"errors": errors}
        )
        
        # Log validation error
        logger.warning(f"Validation error: {errors}")
        
        return JSONResponse(
            status_code=422,
            content=error_response
        )
    
    async def _handle_app_exception(self, request: Request, exc: AppException) -> JSONResponse:
        """
        Handle custom application exceptions.
        """
        error_response = self._build_error_response(
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            details=exc.details
        )
        
        # Log app exception
        log_level = logger.error if exc.status_code >= 500 else logger.warning
        log_level(f"App exception: {exc.code} - {exc.message}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response
        )
    
    async def _handle_unexpected_error(self, request: Request, exc: Exception) -> JSONResponse:
        """
        Handle unexpected errors.
        """
        # Log full traceback for debugging
        logger.error(f"Unexpected error: {str(exc)}")
        logger.error(traceback.format_exc())
        
        # Build error response
        error_response = self._build_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            status_code=500
        )
        
        # Include traceback in debug mode
        if self.debug or settings.ENVIRONMENT == "development":
            error_response["error"]["traceback"] = traceback.format_exc().split("\n")
        
        return JSONResponse(
            status_code=500,
            content=error_response
        )
    
    def _build_error_response(
        self,
        code: str,
        message: str,
        status_code: int,
        details: Union[Dict, list, None] = None
    ) -> Dict[str, Any]:
        """
        Build standardized error response.
        """
        response = {
            "status": "error",
            "error": {
                "code": code,
                "message": message,
                "status_code": status_code
            }
        }
        
        if details:
            response["error"]["details"] = details
        
        return response


class ExceptionHandlers:
    """
    Collection of exception handlers for FastAPI.
    """
    
    @staticmethod
    async def not_found_handler(request: Request, exc: NotFoundException):
        """Handle not found exceptions."""
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "error": {
                    "code": exc.code,
                    "message": exc.message
                }
            }
        )
    
    @staticmethod
    async def validation_handler(request: Request, exc: ValidationException):
        """Handle validation exceptions."""
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details
                }
            }
        )
    
    @staticmethod
    async def auth_handler(request: Request, exc: AuthenticationException):
        """Handle authentication exceptions."""
        return JSONResponse(
            status_code=401,
            content={
                "status": "error",
                "error": {
                    "code": exc.code,
                    "message": exc.message
                }
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    @staticmethod
    async def forbidden_handler(request: Request, exc: AuthorizationException):
        """Handle authorization exceptions."""
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "error": {
                    "code": exc.code,
                    "message": exc.message
                }
            }
        )
    
    @staticmethod
    async def conflict_handler(request: Request, exc: ConflictException):
        """Handle conflict exceptions."""
        return JSONResponse(
            status_code=409,
            content={
                "status": "error",
                "error": {
                    "code": exc.code,
                    "message": exc.message
                }
            }
        )
    
    @staticmethod
    async def rate_limit_handler(request: Request, exc: RateLimitException):
        """Handle rate limit exceptions."""
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "error": {
                    "code": exc.code,
                    "message": exc.message
                }
            },
            headers={
                "X-RateLimit-Limit": str(exc.details.get("limit", "unknown")),
                "X-RateLimit-Reset": str(exc.details.get("reset", "unknown")),
                "Retry-After": str(exc.details.get("retry_after", "unknown"))
            }
        )
    
    @staticmethod
    async def service_unavailable_handler(request: Request, exc: ServiceUnavailableException):
        """Handle service unavailable exceptions."""
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": {
                    "code": exc.code,
                    "message": exc.message
                }
            }
        )