"""
API routes package initialization.
"""

from fastapi import APIRouter

from . import notifications, templates, providers, health

router = APIRouter()

router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(templates.router, prefix="/templates", tags=["templates"])
router.include_router(providers.router, prefix="/providers", tags=["providers"])
router.include_router(health.router, prefix="/health", tags=["health"])

__all__ = ["router"]