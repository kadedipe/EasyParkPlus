"""
API endpoints for provider management and monitoring.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

from ..providers.email import get_email_provider_manager
from ..providers.sms import get_sms_provider_manager
from ..providers.push import get_push_provider_manager
from ..utils.logging_utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/email")
async def list_email_providers():
    """
    List all email providers and their status.
    """
    try:
        manager = get_email_provider_manager()
        if not manager:
            return {"providers": [], "message": "Email providers not configured"}
        
        providers = []
        for provider in manager.providers:
            providers.append({
                "name": provider.name,
                "stats": provider.get_stats(),
                "healthy": await provider.check_health()
            })
        
        return {
            "providers": providers,
            "current_provider": manager.current_provider_index
        }
        
    except Exception as e:
        logger.error(f"Failed to list email providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sms")
async def list_sms_providers():
    """
    List all SMS providers and their status.
    """
    try:
        manager = get_sms_provider_manager()
        if not manager:
            return {"providers": [], "message": "SMS providers not configured"}
        
        providers = []
        for provider in manager.providers:
            providers.append({
                "name": provider.name,
                "stats": provider.get_stats(),
                "balance": await provider.get_balance(),
                "healthy": await provider.check_health()
            })
        
        return {
            "providers": providers,
            "current_provider": manager.current_provider_index
        }
        
    except Exception as e:
        logger.error(f"Failed to list SMS providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/push")
async def list_push_providers():
    """
    List all push notification providers and their status.
    """
    try:
        manager = get_push_provider_manager()
        if not manager:
            return {"providers": [], "message": "Push providers not configured"}
        
        providers = []
        for provider in manager.providers:
            providers.append({
                "name": provider.name,
                "stats": provider.get_stats(),
                "healthy": await provider.check_health()
            })
        
        return {
            "providers": providers,
            "current_provider": manager.current_provider_index
        }
        
    except Exception as e:
        logger.error(f"Failed to list push providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/email/switch/{provider_name}")
async def switch_email_provider(provider_name: str):
    """
    Switch to a different email provider.
    """
    try:
        manager = get_email_provider_manager()
        if not manager:
            raise HTTPException(status_code=404, detail="Email providers not configured")
        
        # Find provider index
        for i, provider in enumerate(manager.providers):
            if provider.name == provider_name:
                manager.current_provider_index = i
                return {
                    "status": "success",
                    "message": f"Switched to provider: {provider_name}"
                }
        
        raise HTTPException(status_code=404, detail=f"Provider {provider_name} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to switch email provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sms/switch/{provider_name}")
async def switch_sms_provider(provider_name: str):
    """
    Switch to a different SMS provider.
    """
    try:
        manager = get_sms_provider_manager()
        if not manager:
            raise HTTPException(status_code=404, detail="SMS providers not configured")
        
        for i, provider in enumerate(manager.providers):
            if provider.name == provider_name:
                manager.current_provider_index = i
                return {
                    "status": "success",
                    "message": f"Switched to provider: {provider_name}"
                }
        
        raise HTTPException(status_code=404, detail=f"Provider {provider_name} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to switch SMS provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/push/switch/{provider_name}")
async def switch_push_provider(provider_name: str):
    """
    Switch to a different push notification provider.
    """
    try:
        manager = get_push_provider_manager()
        if not manager:
            raise HTTPException(status_code=404, detail="Push providers not configured")
        
        for i, provider in enumerate(manager.providers):
            if provider.name == provider_name:
                manager.current_provider_index = i
                return {
                    "status": "success",
                    "message": f"Switched to provider: {provider_name}"
                }
        
        raise HTTPException(status_code=404, detail=f"Provider {provider_name} not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to switch push provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/email/stats")
async def get_email_provider_stats():
    """
    Get statistics for all email providers.
    """
    try:
        manager = get_email_provider_manager()
        if not manager:
            return {"providers": []}
        
        return {
            "providers": manager.get_stats()
        }
        
    except Exception as e:
        logger.error(f"Failed to get email provider stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sms/stats")
async def get_sms_provider_stats():
    """
    Get statistics for all SMS providers.
    """
    try:
        manager = get_sms_provider_manager()
        if not manager:
            return {"providers": []}
        
        return {
            "providers": manager.get_stats()
        }
        
    except Exception as e:
        logger.error(f"Failed to get SMS provider stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/push/stats")
async def get_push_provider_stats():
    """
    Get statistics for all push providers.
    """
    try:
        manager = get_push_provider_manager()
        if not manager:
            return {"providers": []}
        
        return {
            "providers": manager.get_stats()
        }
        
    except Exception as e:
        logger.error(f"Failed to get push provider stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))