"""
API endpoints for template management.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..templates import get_template_manager, get_email_renderer, get_sms_renderer, get_push_renderer
from ..utils.logging_utils import get_logger

router = APIRouter()
logger = get_logger(__name__)


class TemplateRenderRequest(BaseModel):
    """Template render request."""
    type: str  # email, sms, push
    name: str
    context: dict = {}
    format: str = "html"  # for email: html/txt, for push: json


class TemplatePreviewRequest(BaseModel):
    """Template preview request."""
    type: str
    name: str
    sample_data: Optional[dict] = None


@router.get("/list")
async def list_templates(
    type: Optional[str] = Query(None, description="Filter by template type")
):
    """
    List all available templates.
    """
    try:
        templates = get_template_manager().list_templates(type)
        return {
            "status": "success",
            "templates": templates
        }
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info/{type}/{name}")
async def get_template_info(type: str, name: str):
    """
    Get template information.
    """
    try:
        info = get_template_manager().get_template_info(type, name)
        return {
            "status": "success",
            "info": info
        }
    except Exception as e:
        logger.error(f"Failed to get template info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/render")
async def render_template(request: TemplateRenderRequest):
    """
    Render a template with context.
    """
    try:
        if request.type == "email":
            html, text = get_email_renderer().render(
                request.name,
                request.context
            )
            return {
                "status": "success",
                "html": html,
                "text": text
            }
            
        elif request.type == "sms":
            text = get_sms_renderer().render(
                request.name,
                request.context
            )
            return {
                "status": "success",
                "text": text
            }
            
        elif request.type == "push":
            data = get_push_renderer().render(
                request.name,
                request.context
            )
            return {
                "status": "success",
                "data": data
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown template type: {request.type}")
            
    except Exception as e:
        logger.error(f"Failed to render template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview/{type}/{name}")
async def preview_template(
    type: str,
    name: str,
    request: TemplatePreviewRequest
):
    """
    Preview a template with sample data.
    """
    try:
        # Use sample data if provided, otherwise use default sample data
        if request.sample_data:
            context = request.sample_data
        else:
            # Default sample data based on template type
            context = get_sample_data(type, name)
        
        if type == "email":
            html, text = get_email_renderer().render(name, context)
            subject = get_email_renderer().render_subject(name, context)
            
            return {
                "status": "success",
                "subject": subject,
                "html": html,
                "text": text,
                "context": context
            }
            
        elif type == "sms":
            text = get_sms_renderer().render(name, context)
            
            return {
                "status": "success",
                "text": text,
                "context": context,
                "char_count": len(text),
                "segments": (len(text) + 152) // 153  # SMS segment calculation
            }
            
        elif type == "push":
            data = get_push_renderer().render(name, context)
            
            return {
                "status": "success",
                "data": data,
                "context": context
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown template type: {type}")
            
    except Exception as e:
        logger.error(f"Failed to preview template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate/{type}/{name}")
async def validate_template(type: str, name: str):
    """
    Validate that a template exists and is properly formatted.
    """
    try:
        exists = get_template_manager().validate_template(type, name)
        
        if not exists:
            raise HTTPException(status_code=404, detail=f"Template {type}/{name} not found")
        
        return {
            "status": "success",
            "message": f"Template {type}/{name} is valid",
            "type": type,
            "name": name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_sample_data(template_type: str, template_name: str) -> dict:
    """
    Get sample data for template preview.
    """
    # Common sample data
    common_data = {
        "user_name": "John Doe",
        "user_email": "john.doe@example.com",
        "user_phone": "+1234567890",
        "app_name": "Parking Management",
        "current_year": 2024
    }
    
    # Template-specific sample data
    if "booking" in template_name:
        common_data.update({
            "booking_id": "BK-123456",
            "parking_name": "Downtown Parking Garage",
            "spot_number": "A42",
            "vehicle_plate": "ABC-1234",
            "start_time": "2024-01-15T10:00:00Z",
            "end_time": "2024-01-15T12:00:00Z",
            "amount": 25.50,
            "currency": "USD"
        })
        
    elif "payment" in template_name:
        common_data.update({
            "payment_id": "PAY-789012",
            "amount": 25.50,
            "currency": "USD",
            "payment_method": "Visa •••• 4242",
            "receipt_url": "https://example.com/receipt/123"
        })
        
    elif "verification" in template_name:
        common_data.update({
            "code": "123456",
            "expires_in": 10
        })
        
    elif "welcome" in template_name:
        common_data.update({
            "verify_link": "https://example.com/verify?token=abc123"
        })
        
    elif "reset" in template_name:
        common_data.update({
            "reset_link": "https://example.com/reset?token=abc123",
            "expires_in": 1
        })
    
    return common_data