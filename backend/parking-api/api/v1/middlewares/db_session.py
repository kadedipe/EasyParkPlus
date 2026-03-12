"""
Database session management middleware.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ....db.session import AsyncSessionLocal
from ....utils.logger import logger


class DBSessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for managing database sessions.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Create and manage database session for the request.
        """
        # Create session
        async with AsyncSessionLocal() as session:
            # Attach session to request state
            request.state.db = session
            
            try:
                # Process request
                response = await call_next(request)
                
                # Commit if no errors
                await session.commit()
                
                return response
                
            except Exception as e:
                # Rollback on error
                await session.rollback()
                logger.error(f"Database error: {str(e)}")
                raise
                
            finally:
                # Close session
                await session.close()


class TransactionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling database transactions.
    """
    
    def __init__(self, app: ASGIApp, commit_on_end: bool = True):
        super().__init__(app)
        self.commit_on_end = commit_on_end
    
    async def dispatch(self, request: Request, call_next):
        """
        Handle transaction lifecycle.
        """
        # Skip for read-only methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return await call_next(request)
        
        # Begin transaction
        if hasattr(request.state, "db"):
            await request.state.db.begin()
        
        try:
            response = await call_next(request)
            
            # Commit if successful and method requires it
            if (
                self.commit_on_end and
                response.status_code < 400 and
                hasattr(request.state, "db")
            ):
                await request.state.db.commit()
            
            return response
            
        except Exception as e:
            # Rollback on error
            if hasattr(request.state, "db"):
                await request.state.db.rollback()
            raise


class ReadOnlyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce read-only mode for maintenance.
    """
    
    def __init__(self, app: ASGIApp, read_only_paths: list = None):
        super().__init__(app)
        self.read_only_paths = read_only_paths or ["/api/v1/admin"]
    
    async def dispatch(self, request: Request, call_next):
        """
        Check if request is allowed in read-only mode.
        """
        # Check if in maintenance mode
        if hasattr(request.app.state, "maintenance_mode") and request.app.state.maintenance_mode:
            # Allow only GET requests for non-admin paths
            if request.method != "GET" or self._is_admin_path(request.url.path):
                from starlette.responses import JSONResponse
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "error",
                        "error": {
                            "code": "MAINTENANCE_MODE",
                            "message": "System is in maintenance mode. Please try again later."
                        }
                    }
                )
        
        return await call_next(request)
    
    def _is_admin_path(self, path: str) -> bool:
        """
        Check if path is admin-only.
        """
        for admin_path in self.read_only_paths:
            if path.startswith(admin_path):
                return True
        return False