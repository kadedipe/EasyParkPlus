"""
Health check service for monitoring application health.
"""

from typing import Dict, Any
import psutil
import platform
from datetime import datetime

from ..core.config import settings
from ..db.session import engine
from ..services.redis import redis_client
from ..utils.logger import logger


class HealthChecker:
    """
    Health check service for monitoring all application components.
    """
    
    def __init__(self):
        self.services = {}
    
    async def check_all(self) -> Dict[str, Any]:
        """
        Check health of all services.
        """
        health_status = {
            "database": await self.check_database(),
            "redis": await self.check_redis(),
            "disk": await self.check_disk(),
            "memory": await self.check_memory(),
            "cpu": await self.check_cpu(),
            "system": self.check_system()
        }
        
        return health_status
    
    async def check_database(self) -> str:
        """
        Check database connectivity.
        """
        try:
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")
            return "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return "unhealthy"
    
    async def check_redis(self) -> str:
        """
        Check Redis connectivity.
        """
        if not redis_client:
            return "disabled"
        
        try:
            await redis_client.ping()
            return "healthy"
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return "unhealthy"
    
    async def check_disk(self) -> Dict[str, Any]:
        """
        Check disk usage.
        """
        try:
            disk = psutil.disk_usage('/')
            usage_percent = disk.percent
            
            status = "healthy"
            if usage_percent > 90:
                status = "critical"
            elif usage_percent > 80:
                status = "warning"
            
            return {
                "status": status,
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3),
                "usage_percent": usage_percent
            }
        except Exception as e:
            logger.error(f"Disk health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_memory(self) -> Dict[str, Any]:
        """
        Check memory usage.
        """
        try:
            memory = psutil.virtual_memory()
            usage_percent = memory.percent
            
            status = "healthy"
            if usage_percent > 90:
                status = "critical"
            elif usage_percent > 80:
                status = "warning"
            
            return {
                "status": status,
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_gb": memory.used / (1024**3),
                "usage_percent": usage_percent
            }
        except Exception as e:
            logger.error(f"Memory health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def check_cpu(self) -> Dict[str, Any]:
        """
        Check CPU usage.
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            status = "healthy"
            if cpu_percent > 90:
                status = "critical"
            elif cpu_percent > 80:
                status = "warning"
            
            return {
                "status": status,
                "usage_percent": cpu_percent,
                "cpu_count": cpu_count,
                "cpu_freq_mhz": cpu_freq.current if cpu_freq else None
            }
        except Exception as e:
            logger.error(f"CPU health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
    
    def check_system(self) -> Dict[str, Any]:
        """
        Get system information.
        """
        return {
            "status": "healthy",
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
            "environment": settings.ENVIRONMENT,
            "version": settings.VERSION
        }
    
    async def is_ready(self) -> bool:
        """
        Check if application is ready to accept traffic.
        """
        health = await self.check_all()
        
        # Check critical services
        if health["database"] != "healthy":
            return False
        
        if health.get("redis", {}).get("status") == "unhealthy":
            return False
        
        return True


# Create singleton instance
health_checker = HealthChecker()