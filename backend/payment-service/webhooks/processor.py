"""
Webhook processing and queuing system.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

import redis.asyncio as redis

from ..core.config import settings
from ..utils.logging_utils import get_logger
from .handlers import get_webhook_handler
from .events import WebhookEvent

logger = get_logger(__name__)


class WebhookStatus(str, Enum):
    """Webhook processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class WebhookProcessor:
    """
    Webhook processor with queuing and retry logic.
    """
    
    def __init__(self):
        """Initialize webhook processor."""
        self.redis_client: Optional[redis.Redis] = None
        self.processing_queue = "webhooks:processing"
        self.failed_queue = "webhooks:failed"
        self.max_retries = settings.WEBHOOK_MAX_RETRIES
        self.retry_delays = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hour
        
        self.logger = get_logger(__name__)
    
    async def initialize(self):
        """Initialize Redis connection."""
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
        self.logger.info("Webhook processor initialized")
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    async def queue_webhook(
        self,
        gateway: str,
        event_data: Dict[str, Any],
        headers: Dict[str, str]
    ) -> str:
        """
        Queue webhook for processing.
        
        Args:
            gateway: Payment gateway name
            event_data: Webhook event data
            headers: Request headers
            
        Returns:
            str: Webhook ID
        """
        import uuid
        webhook_id = str(uuid.uuid4())
        
        # Prepare webhook data
        webhook_data = {
            "id": webhook_id,
            "gateway": gateway,
            "event_data": event_data,
            "headers": headers,
            "received_at": datetime.utcnow().isoformat(),
            "status": WebhookStatus.PENDING,
            "retry_count": 0
        }
        
        # Store in Redis
        await self.redis_client.setex(
            f"webhook:{webhook_id}",
            86400,  # 24 hours
            json.dumps(webhook_data)
        )
        
        # Add to processing queue
        await self.redis_client.rpush(
            self.processing_queue,
            webhook_id
        )
        
        self.logger.info(f"Webhook {webhook_id} queued for processing")
        
        return webhook_id
    
    async def process_webhook(self, webhook_id: str) -> bool:
        """
        Process a single webhook.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            bool: True if processed successfully
        """
        try:
            # Get webhook data
            data = await self.redis_client.get(f"webhook:{webhook_id}")
            if not data:
                self.logger.error(f"Webhook {webhook_id} not found")
                return False
            
            webhook_data = json.loads(data)
            
            # Update status
            webhook_data["status"] = WebhookStatus.PROCESSING
            await self.redis_client.set(
                f"webhook:{webhook_id}",
                json.dumps(webhook_data)
            )
            
            # Get handler and process
            handler = get_webhook_handler(webhook_data["gateway"])
            result = await handler.handle(webhook_data["event_data"])
            
            # Update success
            webhook_data["status"] = WebhookStatus.COMPLETED
            webhook_data["processed_at"] = datetime.utcnow().isoformat()
            webhook_data["result"] = result
            
            await self.redis_client.set(
                f"webhook:{webhook_id}",
                json.dumps(webhook_data)
            )
            
            self.logger.info(f"Webhook {webhook_id} processed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process webhook {webhook_id}: {e}")
            
            # Handle failure with retry
            await self.handle_failure(webhook_id, str(e))
            return False
    
    async def handle_failure(self, webhook_id: str, error: str):
        """
        Handle webhook processing failure.
        
        Args:
            webhook_id: Webhook ID
            error: Error message
        """
        # Get webhook data
        data = await self.redis_client.get(f"webhook:{webhook_id}")
        if not data:
            return
        
        webhook_data = json.loads(data)
        retry_count = webhook_data.get("retry_count", 0) + 1
        
        if retry_count <= self.max_retries:
            # Schedule retry
            delay = self.retry_delays[min(retry_count - 1, len(self.retry_delays) - 1)]
            
            webhook_data["status"] = WebhookStatus.RETRY
            webhook_data["retry_count"] = retry_count
            webhook_data["last_error"] = error
            webhook_data["next_retry"] = (
                datetime.utcnow().timestamp() + delay
            )
            
            await self.redis_client.set(
                f"webhook:{webhook_id}",
                json.dumps(webhook_data)
            )
            
            # Schedule retry
            await self.schedule_retry(webhook_id, delay)
            
            self.logger.info(
                f"Scheduled retry {retry_count} for webhook {webhook_id} "
                f"in {delay} seconds"
            )
            
        else:
            # Max retries exceeded
            webhook_data["status"] = WebhookStatus.FAILED
            webhook_data["final_error"] = error
            
            await self.redis_client.set(
                f"webhook:{webhook_id}",
                json.dumps(webhook_data)
            )
            
            # Add to failed queue
            await self.redis_client.rpush(
                self.failed_queue,
                webhook_id
            )
            
            self.logger.error(
                f"Webhook {webhook_id} failed after {retry_count} retries"
            )
    
    async def schedule_retry(self, webhook_id: str, delay: int):
        """
        Schedule webhook retry.
        
        Args:
            webhook_id: Webhook ID
            delay: Delay in seconds
        """
        await asyncio.sleep(delay)
        await self.redis_client.rpush(self.processing_queue, webhook_id)
    
    async def process_queue(self, batch_size: int = 10):
        """
        Process webhooks from queue.
        
        Args:
            batch_size: Number of webhooks to process in batch
        """
        while True:
            try:
                # Get batch of webhook IDs
                webhook_ids = await self.redis_client.lrange(
                    self.processing_queue,
                    0,
                    batch_size - 1
                )
                
                if not webhook_ids:
                    await asyncio.sleep(1)
                    continue
                
                # Remove from queue
                await self.redis_client.ltrim(
                    self.processing_queue,
                    len(webhook_ids),
                    -1
                )
                
                # Process webhooks concurrently
                tasks = [
                    self.process_webhook(webhook_id)
                    for webhook_id in webhook_ids
                ]
                
                await asyncio.gather(*tasks)
                
            except Exception as e:
                self.logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(5)
    
    async def get_webhook_status(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """
        Get webhook processing status.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Optional[Dict[str, Any]]: Webhook status
        """
        data = await self.redis_client.get(f"webhook:{webhook_id}")
        if data:
            return json.loads(data)
        return None
    
    async def get_failed_webhooks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get failed webhooks.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List[Dict[str, Any]]: Failed webhooks
        """
        webhook_ids = await self.redis_client.lrange(
            self.failed_queue,
            0,
            limit - 1
        )
        
        webhooks = []
        for webhook_id in webhook_ids:
            data = await self.redis_client.get(f"webhook:{webhook_id}")
            if data:
                webhooks.append(json.loads(data))
        
        return webhooks
    
    async def retry_failed_webhook(self, webhook_id: str) -> bool:
        """
        Retry a failed webhook.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            bool: True if queued for retry
        """
        # Remove from failed queue
        await self.redis_client.lrem(self.failed_queue, 0, webhook_id)
        
        # Reset retry count
        data = await self.redis_client.get(f"webhook:{webhook_id}")
        if data:
            webhook_data = json.loads(data)
            webhook_data["retry_count"] = 0
            webhook_data["status"] = WebhookStatus.PENDING
            await self.redis_client.set(
                f"webhook:{webhook_id}",
                json.dumps(webhook_data)
            )
        
        # Add to processing queue
        await self.redis_client.rpush(self.processing_queue, webhook_id)
        
        return True


# Singleton instance
webhook_processor = WebhookProcessor()


async def get_webhook_processor() -> WebhookProcessor:
    """
    Get webhook processor singleton.
    
    Returns:
        WebhookProcessor: Webhook processor instance
    """
    if not webhook_processor.redis_client:
        await webhook_processor.initialize()
    return webhook_processor