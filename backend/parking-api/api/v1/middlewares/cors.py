"""
CORS middleware configuration.
"""

from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware
from starlette.types import ASGIApp

from ....core.config import settings


class CORSMiddleware:
    """
    Configure CORS for the application.
    """
    
    def __init__(self, app: ASGIApp):
        self.app = app
    
    def __call__(self, scope, receive, send):
        """
        ASGI callable.
        """
        # This is a wrapper - actual CORS handling is done by FastAPI's middleware
        return self.app(scope, receive, send)


def setup_cors(app):
    """
    Setup CORS middleware with configuration.
    """
    origins = settings.CORS_ORIGINS
    
    # Allow all origins in development
    if settings.ENVIRONMENT == "development":
        origins = ["*"]
    
    app.add_middleware(
        FastAPICORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "Content-Length",
            "Content-Range",
            "X-Total-Count",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset"
        ],
        max_age=600,  # 10 minutes
    )