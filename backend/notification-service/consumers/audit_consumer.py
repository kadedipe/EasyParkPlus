"""
Audit log consumer for notification service.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .base import BaseConsumer
from ..core.config import settings
from ..utils.logging_utils import get_logger, audit_log
from ..db.repositories.audit import AuditRepository
from ..db.session import get_db


class AuditConsumer(BaseConsumer):
    """
    Consumer for audit log messages.
    Processes audit events from various services.
    """
    
    def __init__(self):
        """Initialize audit consumer."""
        super().__init__(
            queue_name="audit_logs",
            routing_key="audit.#",
            prefetch_count=settings.AUDIT_PREFETCH_COUNT,
            max_retries=5
        )
        self.logger = get_logger(__name__)
        self.audit_repo: Optional[AuditRepository] = None
    
    async def process_message(self, message: Dict[str, Any]) -> bool:
        """
        Process audit log message.
        
        Expected message format:
        {
            "type": "audit",
            "action": "USER_LOGIN",
            "user_id": "uuid",
            "username": "john.doe",
            "resource": "user",
            "resource_id": "uuid",
            "old_value": {...},
            "new_value": {...},
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "details": {...},
            "timestamp": "2024-01-01T00:00:00Z",
            "service": "auth-service"
        }
        """
        try:
            # Get database session
            async for db_session in get_db():
                self.audit_repo = AuditRepository(db_session)
                
                # Extract message data
                audit_type = message.get("type")
                action = message.get("action")
                user_id = message.get("user_id")
                username = message.get("username")
                resource = message.get("resource")
                resource_id = message.get("resource_id")
                old_value = message.get("old_value")
                new_value = message.get("new_value")
                ip_address = message.get("ip_address")
                user_agent = message.get("user_agent")
                details = message.get("details", {})
                timestamp = message.get("timestamp")
                service = message.get("service", "unknown")
                
                # Add service info to details
                details["source_service"] = service
                details["message_id"] = message.get("_metadata", {}).get("message_id")
                
                # Prepare audit log data
                audit_data = {
                    "user_id": user_id,
                    "username": username,
                    "action": action,
                    "resource": resource,
                    "resource_id": resource_id,
                    "old_value": old_value,
                    "new_value": new_value,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "details": details
                }
                
                # Create audit log
                from ..schemas.audit import AuditLogCreate
                audit_in = AuditLogCreate(**audit_data)
                
                created_log = await self.audit_repo.create_with_context(
                    audit_in,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                self.logger.info(
                    f"Audit log created: {action} on {resource} "
                    f"from service: {service}"
                )
                
                # Check for suspicious activity
                await self.check_suspicious_activity(message)
                
                # Apply retention policy if needed
                if message.get("apply_retention", False):
                    await self.apply_retention_policy()
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to process audit message: {e}", exc_info=True)
            return False
    
    async def check_suspicious_activity(self, message: Dict[str, Any]) -> None:
        """
        Check for suspicious activity patterns.
        
        Args:
            message: Audit message
        """
        try:
            action = message.get("action")
            user_id = message.get("user_id")
            ip_address = message.get("ip_address")
            
            suspicious_patterns = []
            
            # Check for multiple failed logins
            if action == "FAILED_LOGIN" and user_id:
                recent_failures = await self.get_recent_failures(user_id)
                if recent_failures >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                    suspicious_patterns.append({
                        "type": "multiple_failed_logins",
                        "count": recent_failures,
                        "user_id": user_id
                    })
            
            # Check for unusual access times
            if action in ["LOGIN", "API_CALL"] and user_id:
                hour = datetime.utcnow().hour
                if hour < 6 or hour > 22:  # Unusual hours
                    suspicious_patterns.append({
                        "type": "unusual_access_time",
                        "hour": hour,
                        "user_id": user_id
                    })
            
            # Check for multiple actions from same IP
            if ip_address:
                recent_actions = await self.get_recent_actions_by_ip(ip_address)
                if recent_actions > 100:  # Threshold
                    suspicious_patterns.append({
                        "type": "high_volume_ip",
                        "count": recent_actions,
                        "ip_address": ip_address
                    })
            
            # Alert if suspicious patterns found
            if suspicious_patterns:
                self.logger.warning(
                    f"Suspicious activity detected: {suspicious_patterns}"
                )
                
                # Publish alert message
                await self.publish_alert(suspicious_patterns, message)
                
        except Exception as e:
            self.logger.error(f"Error checking suspicious activity: {e}")
    
    async def get_recent_failures(self, user_id: str, minutes: int = 15) -> int:
        """
        Get recent failed login attempts for user.
        
        Args:
            user_id: User ID
            minutes: Time window in minutes
            
        Returns:
            int: Number of failures
        """
        # This would query the database for recent failures
        # Implementation depends on your database schema
        return 0
    
    async def get_recent_actions_by_ip(self, ip_address: str, minutes: int = 5) -> int:
        """
        Get recent actions from IP address.
        
        Args:
            ip_address: IP address
            minutes: Time window in minutes
            
        Returns:
            int: Number of actions
        """
        # This would query the database for recent actions
        # Implementation depends on your database schema
        return 0
    
    async def apply_retention_policy(self) -> None:
        """
        Apply audit log retention policy.
        """
        try:
            # Get policy from settings
            retention_days = settings.AUDIT_RETENTION_DAYS
            
            if retention_days > 0:
                deleted = await self.audit_repo.cleanup_old_logs(retention_days)
                
                if deleted > 0:
                    self.logger.info(
                        f"Audit retention policy applied: {deleted} logs deleted"
                    )
                    
        except Exception as e:
            self.logger.error(f"Failed to apply retention policy: {e}")
    
    async def publish_alert(
        self,
        patterns: list,
        original_message: Dict[str, Any]
    ) -> None:
        """
        Publish alert for suspicious activity.
        
        Args:
            patterns: Suspicious patterns detected
            original_message: Original audit message
        """
        try:
            alert_message = {
                "type": "security_alert",
                "patterns": patterns,
                "severity": "high",
                "timestamp": datetime.utcnow().isoformat(),
                "original_audit": original_message
            }
            
            # Publish to security alerts queue
            await self.exchange.publish(
                message=Message(
                    body=json.dumps(alert_message).encode(),
                    content_type="application/json",
                    priority=9  # High priority
                ),
                routing_key="security.alert"
            )
            
            self.logger.info(f"Security alert published: {patterns}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish alert: {e}")
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        Get audit queue statistics.
        
        Returns:
            Dict[str, Any]: Queue statistics
        """
        queue_status = await self.get_queue_status()
        
        return {
            **queue_status,
            "retention_days": settings.AUDIT_RETENTION_DAYS
        }