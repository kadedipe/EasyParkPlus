"""
Health check endpoints.
"""

from fastapi import APIRouter
from datetime import datetime
import psutil
import os

from ..core.config import settings
from ..utils.logging_utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/")
async def health_check():
    """
    Basic health check endpoint.
    """
    return {
        "status": "healthy",
        "service": "notification-service",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/detailed")
async def detailed_health():
    """
    Detailed health check with system metrics.
    """
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process metrics
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent(interval=1)
        
        return {
            "status": "healthy",
            "service": "notification-service",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                }
            },
            "process": {
                "pid": os.getpid(),
                "memory_rss": process_memory.rss,
                "memory_vms": process_memory.vms,
                "cpu_percent": process_cpu,
                "connections": len(process.connections()),
                "threads": process.num_threads()
            },
            "config": {
                "host": settings.HOST,
                "port": settings.PORT,
                "workers": settings.WORKERS,
                "debug": settings.DEBUG,
                "rabbitmq_host": settings.RABBITMQ_HOST,
                "rabbitmq_port": settings.RABBITMQ_PORT
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "service": "notification-service",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe for Kubernetes/container orchestration.
    """
    # Check if service is ready to accept traffic
    # This should check dependencies (RabbitMQ, databases, etc.)
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness probe for Kubernetes/container orchestration.
    """
    # Check if service is alive
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }