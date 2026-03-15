"""
Webhook management API endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from ..core.config import settings
from ..utils.logging_utils import get_logger
from .processor import get_webhook_processor, WebhookProcessor, WebhookStatus
from .handlers import get_webhook_handler

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger(__name__)


class WebhookResponse(BaseModel):
    """Webhook response model."""
    id: str
    gateway: str
    status: str
    received_at: str
    processed_at: Optional[str] = None
    retry_count: int = 0
    last_error: Optional[str] = None
    result: Optional[dict] = None


class WebhookListResponse(BaseModel):
    """Webhook list response model."""
    total: int
    items: List[WebhookResponse]


@router.get("/status/{webhook_id}")
async def get_webhook_status(
    webhook_id: str,
    processor: WebhookProcessor = Depends(get_webhook_processor)
):
    """
    Get webhook processing status.
    """
    status = await processor.get_webhook_status(webhook_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return WebhookResponse(
        id=status["id"],
        gateway=status["gateway"],
        status=status["status"],
        received_at=status["received_at"],
        processed_at=status.get("processed_at"),
        retry_count=status.get("retry_count", 0),
        last_error=status.get("last_error") or status.get("final_error"),
        result=status.get("result")
    )


@router.get("/failed")
async def get_failed_webhooks(
    limit: int = Query(100, ge=1, le=1000),
    processor: WebhookProcessor = Depends(get_webhook_processor)
):
    """
    Get failed webhooks.
    """
    webhooks = await processor.get_failed_webhooks(limit)
    
    return WebhookListResponse(
        total=len(webhooks),
        items=[
            WebhookResponse(
                id=w["id"],
                gateway=w["gateway"],
                status=w["status"],
                received_at=w["received_at"],
                processed_at=w.get("processed_at"),
                retry_count=w.get("retry_count", 0),
                last_error=w.get("last_error") or w.get("final_error"),
                result=w.get("result")
            )
            for w in webhooks
        ]
    )


@router.post("/failed/{webhook_id}/retry")
async def retry_failed_webhook(
    webhook_id: str,
    processor: WebhookProcessor = Depends(get_webhook_processor)
):
    """
    Retry a failed webhook.
    """
    success = await processor.retry_failed_webhook(webhook_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"status": "queued", "webhook_id": webhook_id}


@router.post("/test/{gateway}")
async def test_webhook(gateway: str):
    """
    Send a test webhook.
    """
    # Get handler
    handler = get_webhook_handler(gateway)
    
    # Create test event
    test_event = {
        "id": "test_" + gateway,
        "type": "test.event",
        "created": datetime.utcnow().timestamp(),
        "data": {"test": True}
    }
    
    # Process
    result = await handler.handle(test_event)
    
    return {
        "gateway": gateway,
        "test_event": test_event,
        "result": result
    }


@router.get("/stats")
async def get_webhook_stats(
    processor: WebhookProcessor = Depends(get_webhook_processor)
):
    """
    Get webhook processing statistics.
    """
    # Get queue sizes
    processing_count = await processor.redis_client.llen(processor.processing_queue)
    failed_count = await processor.redis_client.llen(processor.failed_queue)
    
    return {
        "processing_queue": processing_count,
        "failed_queue": failed_count,
        "max_retries": processor.max_retries,
        "retry_delays": processor.retry_delays
    }