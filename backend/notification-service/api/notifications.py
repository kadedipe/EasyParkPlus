"""
API endpoints for sending notifications.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel

from ..consumers import (
    EmailConsumer,
    SMSConsumer,
    PushConsumer
)
from ..providers.email import get_email_provider_manager
from ..providers.sms import get_sms_provider_manager
from ..providers.push import get_push_provider_manager
from ..templates import get_template_manager, get_email_renderer, get_sms_renderer, get_push_renderer
from ..utils.logging_utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


class EmailRequest(BaseModel):
    """Email notification request."""
    to: List[str]
    subject: str
    template: str
    context: dict = {}
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    attachments: Optional[List[dict]] = None
    priority: str = "normal"
    provider: Optional[str] = None


class SMSRequest(BaseModel):
    """SMS notification request."""
    to: List[str]
    message: Optional[str] = None
    template: Optional[str] = None
    context: dict = {}
    sender_id: Optional[str] = None
    priority: str = "normal"
    provider: Optional[str] = None


class PushRequest(BaseModel):
    """Push notification request."""
    tokens: List[str]
    title: Optional[str] = None
    body: Optional[str] = None
    template: Optional[str] = None
    context: dict = {}
    data: Optional[dict] = None
    image_url: Optional[str] = None
    click_action: Optional[str] = None
    priority: str = "normal"
    platform: str = "all"
    provider: Optional[str] = None


class BulkNotificationRequest(BaseModel):
    """Bulk notification request."""
    type: str  # email, sms, push
    notifications: List[dict]
    batch_size: int = 100


@router.post("/email")
async def send_email(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    req: Request
):
    """
    Send an email notification.
    """
    try:
        # Render email template
        if request.template:
            html_content, text_content = get_email_renderer().render(
                request.template,
                request.context
            )
            subject = get_email_renderer().render_subject(
                request.template,
                request.context
            ) or request.subject
        else:
            html_content = request.context.get("html", "")
            text_content = request.context.get("text", "")
            subject = request.subject
        
        # Get provider
        provider_manager = get_email_provider_manager()
        if request.provider:
            # Use specified provider
            provider = next(
                (p for p in provider_manager.providers if p.name == request.provider),
                None
            )
            if not provider:
                raise HTTPException(status_code=400, detail=f"Provider {request.provider} not found")
            
            result = await provider.send_email(
                to=request.to,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                cc=request.cc,
                bcc=request.bcc,
                attachments=request.attachments,
                priority=request.priority
            )
        else:
            # Use provider manager with failover
            result = await provider_manager.send_email(
                to=request.to,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                cc=request.cc,
                bcc=request.bcc,
                attachments=request.attachments,
                priority=request.priority
            )
        
        return {
            "status": "success",
            "message": "Email sent successfully",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sms")
async def send_sms(
    request: SMSRequest,
    background_tasks: BackgroundTasks,
    req: Request
):
    """
    Send an SMS notification.
    """
    try:
        # Render SMS template if needed
        if request.template and not request.message:
            message = get_sms_renderer().render(
                request.template,
                request.context
            )
        else:
            message = request.message
        
        if not message:
            raise HTTPException(status_code=400, detail="Either message or template must be provided")
        
        # Get provider
        provider_manager = get_sms_provider_manager()
        results = []
        
        for recipient in request.to:
            if request.provider:
                # Use specified provider
                provider = next(
                    (p for p in provider_manager.providers if p.name == request.provider),
                    None
                )
                if not provider:
                    raise HTTPException(status_code=400, detail=f"Provider {request.provider} not found")
                
                result = await provider.send_sms(
                    to=recipient,
                    message=message,
                    sender_id=request.sender_id,
                    priority=request.priority
                )
            else:
                # Use provider manager with failover
                result = await provider_manager.send_sms(
                    to=recipient,
                    message=message,
                    sender_id=request.sender_id,
                    priority=request.priority
                )
            
            results.append(result)
        
        return {
            "status": "success",
            "message": f"SMS sent to {len(request.to)} recipients",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/push")
async def send_push(
    request: PushRequest,
    background_tasks: BackgroundTasks,
    req: Request
):
    """
    Send a push notification.
    """
    try:
        # Render push template if needed
        if request.template:
            push_data = get_push_renderer().render(
                request.template,
                request.context,
                platform=request.platform
            )
            title = push_data.get("title")
            body = push_data.get("body")
            data = push_data.get("data", {})
        else:
            title = request.title
            body = request.body
            data = request.data or {}
        
        if not title or not body:
            raise HTTPException(status_code=400, detail="Either template or title/body must be provided")
        
        # Get provider
        provider_manager = get_push_provider_manager()
        
        if request.provider:
            # Use specified provider
            provider = next(
                (p for p in provider_manager.providers if p.name == request.provider),
                None
            )
            if not provider:
                raise HTTPException(status_code=400, detail=f"Provider {request.provider} not found")
            
            result = await provider.send_push(
                tokens=request.tokens,
                title=title,
                body=body,
                data=data,
                image_url=request.image_url,
                click_action=request.click_action,
                priority=request.priority
            )
        else:
            # Use provider manager with failover
            result = await provider_manager.send_push(
                tokens=request.tokens,
                title=title,
                body=body,
                data=data,
                image_url=request.image_url,
                click_action=request.click_action,
                priority=request.priority
            )
        
        return {
            "status": "success",
            "message": f"Push notification sent to {len(request.tokens)} devices",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk")
async def send_bulk_notifications(
    request: BulkNotificationRequest,
    background_tasks: BackgroundTasks,
    req: Request
):
    """
    Send bulk notifications.
    """
    try:
        results = []
        
        # Process in batches
        for i in range(0, len(request.notifications), request.batch_size):
            batch = request.notifications[i:i + request.batch_size]
            
            if request.type == "email":
                for notification in batch:
                    email_request = EmailRequest(**notification)
                    result = await send_email(email_request, background_tasks, req)
                    results.append(result)
                    
            elif request.type == "sms":
                for notification in batch:
                    sms_request = SMSRequest(**notification)
                    result = await send_sms(sms_request, background_tasks, req)
                    results.append(result)
                    
            elif request.type == "push":
                for notification in batch:
                    push_request = PushRequest(**notification)
                    result = await send_push(push_request, background_tasks, req)
                    results.append(result)
        
        return {
            "status": "success",
            "message": f"Processed {len(request.notifications)} notifications",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to send bulk notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{notification_id}")
async def get_notification_status(notification_id: str):
    """
    Get notification status.
    """
    # This would typically query a database for notification status
    # For now, return mock data
    return {
        "notification_id": notification_id,
        "status": "delivered",
        "delivered_at": "2024-01-01T12:00:00Z"
    }