"""
Push notification templates package initialization.
"""

from typing import Dict, Any, Optional
from ..base import TemplateManager

# Push notification templates
PUSH_TEMPLATES = {
    "booking_confirmation": "booking_confirmation.json",
    "booking_confirmation_rich": "booking_confirmation_rich.json",
    "booking_confirmation_minimal": "booking_confirmation_minimal.json",
    "booking_confirmation_timer": "booking_confirmation_with_timer.json",
    "payment_success": "payment_success.json",
    "payment_failed": "payment_failed.json",
    "subscription_renewal": "subscription_renewal.json",
    "reminder": "reminder.json",
    "alert": "alert.json",
    "promotion": "promotion.json"
}


def get_push_template(
    template_type: str = "booking_confirmation",
    context: Optional[Dict[str, Any]] = None,
    platform: str = "all"
) -> str:
    """
    Get appropriate push notification template based on type and context.
    
    Args:
        template_type: Type of push notification
        context: Template context for smart selection
        platform: Target platform (android, ios, web, all)
        
    Returns:
        str: Template filename
    """
    # Smart template selection based on context
    if context:
        # Use rich template for premium users
        if context.get("is_premium"):
            return PUSH_TEMPLATES["booking_confirmation_rich"]
        
        # Use timer template for bookings with countdown
        if context.get("time_until_start") and int(context.get("time_until_start_minutes", 0)) <= 60:
            return PUSH_TEMPLATES["booking_confirmation_timer"]
        
        # Use minimal template for low bandwidth
        if context.get("low_bandwidth"):
            return PUSH_TEMPLATES["booking_confirmation_minimal"]
        
        # Use platform-specific template
        if platform == "android" and context.get("android_compatible"):
            return PUSH_TEMPLATES["booking_confirmation"]
        elif platform == "ios" and context.get("ios_compatible"):
            return PUSH_TEMPLATES["booking_confirmation_rich"]
    
    # Return requested template or default
    return PUSH_TEMPLATES.get(template_type, PUSH_TEMPLATES["booking_confirmation"])


def validate_push_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate push notification payload structure.
    
    Args:
        payload: Push notification payload
        
    Returns:
        Dict[str, Any]: Validation result
    """
    required_fields = ["title", "body", "data"]
    missing_fields = [field for field in required_fields if field not in payload]
    
    if missing_fields:
        return {
            "valid": False,
            "errors": [f"Missing required field: {field}" for field in missing_fields]
        }
    
    # Validate Android section if present
    if "android" in payload:
        android = payload["android"]
        if "notification" in android:
            android_notification = android["notification"]
            if "channel_id" not in android_notification:
                return {
                    "valid": False,
                    "errors": ["Android notification missing channel_id"]
                }
    
    # Validate APNS section if present
    if "apns" in payload:
        apns = payload["apns"]
        if "payload" in apns and "aps" in apns["payload"]:
            aps = apns["payload"]["aps"]
            if "alert" not in aps:
                return {
                    "valid": False,
                    "errors": ["APNS missing alert in aps payload"]
                }
    
    return {"valid": True, "errors": []}


def get_push_actions(template_type: str = "booking_confirmation") -> list:
    """
    Get available actions for push notification template.
    
    Args:
        template_type: Type of push notification
        
    Returns:
        list: Available actions
    """
    actions = {
        "booking_confirmation": [
            {"action": "view", "title": "View Booking"},
            {"action": "cancel", "title": "Cancel"},
            {"action": "extend", "title": "Extend"}
        ],
        "booking_confirmation_rich": [
            {"action": "view", "title": "View Details"},
            {"action": "show_qr", "title": "Show QR Code"},
            {"action": "get_directions", "title": "Directions"},
            {"action": "cancel", "title": "Cancel"}
        ],
        "booking_confirmation_minimal": [
            {"action": "view", "title": "View"}
        ],
        "booking_confirmation_timer": [
            {"action": "view", "title": "View Booking"},
            {"action": "extend", "title": "Extend"},
            {"action": "directions", "title": "Directions"}
        ]
    }
    
    return actions.get(template_type, actions["booking_confirmation"])


def get_platform_specific_config(platform: str) -> Dict[str, Any]:
    """
    Get platform-specific configuration for push notifications.
    
    Args:
        platform: Target platform (android, ios, web)
        
    Returns:
        Dict[str, Any]: Platform-specific configuration
    """
    configs = {
        "android": {
            "priority": "high",
            "channel_id": "default",
            "sound": "default",
            "vibrate": [200, 100, 200]
        },
        "ios": {
            "sound": "default",
            "badge": 1,
            "interruption_level": "active"
        },
        "web": {
            "icon": "/icons/icon-192.png",
            "badge": "/icons/badge-72.png",
            "vibrate": [200, 100, 200],
            "requireInteraction": True
        }
    }
    
    return configs.get(platform, {})


def render_push_notification(
    template_name: str,
    context: Dict[str, Any],
    platform: str = "all"
) -> Dict[str, Any]:
    """
    Render push notification for specific platform.
    
    Args:
        template_name: Template name
        context: Template context
        platform: Target platform
        
    Returns:
        Dict[str, Any]: Rendered push notification
    """
    from ..base import template_manager
    
    # Get template
    template = get_push_template(template_name, context, platform)
    
    # Render JSON
    rendered = template_manager.render("push", template, context, format="json")
    
    # Parse JSON
    import json
    payload = json.loads(rendered)
    
    # Filter for platform if needed
    if platform != "all":
        filtered_payload = {
            "title": payload.get("title"),
            "body": payload.get("body"),
            "data": payload.get("data", {})
        }
        
        # Add platform-specific section
        if platform == "android" and "android" in payload:
            filtered_payload["android"] = payload["android"]
        elif platform == "ios" and "apns" in payload:
            filtered_payload["apns"] = payload["apns"]
        elif platform == "web" and "webpush" in payload:
            filtered_payload["webpush"] = payload["webpush"]
        
        return filtered_payload
    
    return payload

    """
Push notification templates package initialization.
"""

from typing import Dict, Any, Optional
from ..base import TemplateManager

# Push notification templates
PUSH_TEMPLATES = {
    "booking_confirmation": "booking_confirmation.json",
    "booking_confirmation_rich": "booking_confirmation_rich.json",
    "booking_confirmation_minimal": "booking_confirmation_minimal.json",
    "booking_confirmation_timer": "booking_confirmation_with_timer.json",
    "payment_success": "payment_success.json",
    "payment_success_rich": "payment_success_rich.json",
    "payment_success_minimal": "payment_success_minimal.json",
    "payment_success_subscription": "payment_success_subscription.json",
    "payment_failed": "payment_failed.json",
    "subscription_renewal": "subscription_renewal.json",
    "reminder": "reminder.json",
    "alert": "alert.json",
    "promotion": "promotion.json"
}


def get_push_template(
    template_type: str = "payment_success",
    context: Optional[Dict[str, Any]] = None,
    platform: str = "all"
) -> str:
    """
    Get appropriate push notification template based on type and context.
    
    Args:
        template_type: Type of push notification
        context: Template context for smart selection
        platform: Target platform (android, ios, web, all)
        
    Returns:
        str: Template filename
    """
    # Smart template selection based on context
    if context:
        # Use rich template for premium users or large transactions
        if context.get("is_premium") or context.get("amount", 0) > 100:
            return PUSH_TEMPLATES["payment_success_rich"]
        
        # Use subscription template for recurring payments
        if context.get("is_subscription"):
            return PUSH_TEMPLATES["payment_success_subscription"]
        
        # Use minimal template for low bandwidth
        if context.get("low_bandwidth"):
            return PUSH_TEMPLATES["payment_success_minimal"]
        
        # Use platform-specific template
        if platform == "android" and context.get("android_compatible"):
            return PUSH_TEMPLATES["payment_success"]
        elif platform == "ios" and context.get("ios_compatible"):
            return PUSH_TEMPLATES["payment_success_rich"]
    
    # Return requested template or default
    return PUSH_TEMPLATES.get(template_type, PUSH_TEMPLATES["payment_success"])


def validate_push_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate push notification payload structure.
    
    Args:
        payload: Push notification payload
        
    Returns:
        Dict[str, Any]: Validation result
    """
    required_fields = ["title", "body", "data"]
    missing_fields = [field for field in required_fields if field not in payload]
    
    if missing_fields:
        return {
            "valid": False,
            "errors": [f"Missing required field: {field}" for field in missing_fields]
        }
    
    # Validate data section
    data = payload.get("data", {})
    if "type" not in data:
        return {
            "valid": False,
            "errors": ["Missing 'type' in data section"]
        }
    
    # Validate Android section if present
    if "android" in payload:
        android = payload["android"]
        if "notification" in android:
            android_notification = android["notification"]
            if "channel_id" not in android_notification:
                return {
                    "valid": False,
                    "errors": ["Android notification missing channel_id"]
                }
    
    # Validate APNS section if present
    if "apns" in payload:
        apns = payload["apns"]
        if "payload" in apns and "aps" in apns["payload"]:
            aps = apns["payload"]["aps"]
            if "alert" not in aps:
                return {
                    "valid": False,
                    "errors": ["APNS missing alert in aps payload"]
                }
    
    # Validate WebPush section if present
    if "webpush" in payload:
        webpush = payload["webpush"]
        if "notification" not in webpush:
            return {
                "valid": False,
                "errors": ["WebPush missing notification section"]
            }
    
    return {"valid": True, "errors": []}


def get_push_actions(template_type: str = "payment_success") -> list:
    """
    Get available actions for push notification template.
    
    Args:
        template_type: Type of push notification
        
    Returns:
        list: Available actions
    """
    actions = {
        "payment_success": [
            {"action": "view_receipt", "title": "View Receipt"},
            {"action": "download_receipt", "title": "Download PDF"},
            {"action": "share", "title": "Share"}
        ],
        "payment_success_rich": [
            {"action": "view_receipt", "title": "View Receipt"},
            {"action": "download_pdf", "title": "Download PDF"},
            {"action": "share", "title": "Share"},
            {"action": "view_booking", "title": "View Booking"},
            {"action": "get_invoice", "title": "Get Invoice"}
        ],
        "payment_success_minimal": [
            {"action": "view", "title": "View Receipt"}
        ],
        "payment_success_subscription": [
            {"action": "view", "title": "View Subscription"},
            {"action": "manage", "title": "Manage"},
            {"action": "receipt", "title": "Receipt"}
        ]
    }
    
    return actions.get(template_type, actions["payment_success"])


def get_payment_status_icon(status: str) -> str:
    """
    Get appropriate icon for payment status.
    
    Args:
        status: Payment status (success, failed, pending)
        
    Returns:
        str: Icon emoji or URL
    """
    icons = {
        "success": "💰",
        "failed": "❌",
        "pending": "⏳",
        "refunded": "↩️",
        "subscription": "🔄"
    }
    return icons.get(status, "💳")


def render_payment_push(
    context: Dict[str, Any],
    platform: str = "all"
) -> Dict[str, Any]:
    """
    Render payment push notification with smart template selection.
    
    Args:
        context: Template context
        platform: Target platform
        
    Returns:
        Dict[str, Any]: Rendered push notification
    """
    from ..base import template_manager
    
    # Determine template type based on context
    template_type = "payment_success"
    
    if context.get("is_subscription"):
        template_type = "payment_success_subscription"
    elif context.get("amount", 0) > 100 or context.get("is_premium"):
        template_type = "payment_success_rich"
    elif context.get("low_bandwidth"):
        template_type = "payment_success_minimal"
    
    # Get template name
    template_name = get_push_template(template_type, context, platform)
    
    # Add payment icon
    context["payment_icon"] = get_payment_status_icon(
        context.get("payment_type", "success")
    )
    
    # Render template
    rendered = template_manager.render("push", template_name, context, format="json")
    
    # Parse JSON
    import json
    payload = json.loads(rendered)
    
    # Validate payload
    validation = validate_push_payload(payload)
    if not validation["valid"]:
        # Fall back to minimal template
        fallback_payload = {
            "title": "Payment Update",
            "body": f"Payment of {context.get('amount')} {context.get('currency')}",
            "data": {"type": "payment", "status": "success"}
        }
        return fallback_payload
    
    return payload

    """
Push notification templates package initialization.
"""

from typing import Dict, Any, Optional
from ..base import TemplateManager

# Push notification templates
PUSH_TEMPLATES = {
    # Welcome templates
    "welcome": "welcome.json",
    "welcome_rich": "welcome_rich.json",
    "welcome_minimal": "welcome_minimal.json",
    "welcome_bonus": "welcome_bonus.json",
    "welcome_tips": "welcome_tips.json",
    
    # Booking templates
    "booking_confirmation": "booking_confirmation.json",
    "booking_confirmation_rich": "booking_confirmation_rich.json",
    "booking_confirmation_minimal": "booking_confirmation_minimal.json",
    "booking_confirmation_timer": "booking_confirmation_with_timer.json",
    
    # Payment templates
    "payment_success": "payment_success.json",
    "payment_success_rich": "payment_success_rich.json",
    "payment_success_minimal": "payment_success_minimal.json",
    "payment_success_subscription": "payment_success_subscription.json",
    
    # Other templates
    "payment_failed": "payment_failed.json",
    "subscription_renewal": "subscription_renewal.json",
    "reminder": "reminder.json",
    "alert": "alert.json",
    "promotion": "promotion.json"
}


def get_welcome_template(
    context: Optional[Dict[str, Any]] = None,
    platform: str = "all"
) -> str:
    """
    Get appropriate welcome notification template based on context.
    
    Args:
        context: Template context for smart selection
        platform: Target platform (android, ios, web, all)
        
    Returns:
        str: Template filename
    """
    # Smart template selection based on context
    if context:
        # Use rich template for welcome bonus
        if context.get("has_welcome_bonus") and context.get("welcome_bonus", 0) > 0:
            return PUSH_TEMPLATES["welcome_rich"]
        
        # Use bonus template for high-value bonus
        if context.get("welcome_bonus", 0) > 50:
            return PUSH_TEMPLATES["welcome_bonus"]
        
        # Use tips template for returning users
        if context.get("is_returning_user"):
            return PUSH_TEMPLATES["welcome_tips"]
        
        # Use minimal template for low bandwidth
        if context.get("low_bandwidth"):
            return PUSH_TEMPLATES["welcome_minimal"]
        
        # Use platform-specific template
        if platform == "android" and context.get("android_compatible"):
            return PUSH_TEMPLATES["welcome"]
        elif platform == "ios" and context.get("ios_compatible"):
            return PUSH_TEMPLATES["welcome_rich"]
    
    # Return default template
    return PUSH_TEMPLATES["welcome"]


def get_push_template(
    template_type: str = "welcome",
    context: Optional[Dict[str, Any]] = None,
    platform: str = "all"
) -> str:
    """
    Get appropriate push notification template based on type and context.
    
    Args:
        template_type: Type of push notification
        context: Template context for smart selection
        platform: Target platform (android, ios, web, all)
        
    Returns:
        str: Template filename
    """
    # Special handling for welcome templates
    if template_type.startswith("welcome"):
        return get_welcome_template(context, platform)
    
    # Payment templates
    if template_type.startswith("payment"):
        from . import get_push_template as get_payment_template
        return get_payment_template(template_type, context, platform)
    
    # Booking templates
    if template_type.startswith("booking"):
        from . import get_push_template as get_booking_template
        return get_booking_template(template_type, context, platform)
    
    # Return requested template or default
    return PUSH_TEMPLATES.get(template_type, PUSH_TEMPLATES["welcome"])


def validate_push_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate push notification payload structure.
    
    Args:
        payload: Push notification payload
        
    Returns:
        Dict[str, Any]: Validation result
    """
    required_fields = ["title", "body", "data"]
    missing_fields = [field for field in required_fields if field not in payload]
    
    if missing_fields:
        return {
            "valid": False,
            "errors": [f"Missing required field: {field}" for field in missing_fields]
        }
    
    # Validate data section
    data = payload.get("data", {})
    if "type" not in data:
        return {
            "valid": False,
            "errors": ["Missing 'type' in data section"]
        }
    
    # Validate Android section if present
    if "android" in payload:
        android = payload["android"]
        if "notification" in android:
            android_notification = android["notification"]
            if "channel_id" not in android_notification:
                return {
                    "valid": False,
                    "errors": ["Android notification missing channel_id"]
                }
    
    # Validate APNS section if present
    if "apns" in payload:
        apns = payload["apns"]
        if "payload" in apns and "aps" in apns["payload"]:
            aps = apns["payload"]["aps"]
            if "alert" not in aps:
                return {
                    "valid": False,
                    "errors": ["APNS missing alert in aps payload"]
                }
    
    # Validate WebPush section if present
    if "webpush" in payload:
        webpush = payload["webpush"]
        if "notification" not in webpush:
            return {
                "valid": False,
                "errors": ["WebPush missing notification section"]
            }
    
    return {"valid": True, "errors": []}


def get_welcome_actions(template_type: str = "welcome") -> list:
    """
    Get available actions for welcome notification template.
    
    Args:
        template_type: Type of welcome notification
        
    Returns:
        list: Available actions
    """
    actions = {
        "welcome": [
            {"action": "get_started", "title": "Get Started"},
            {"action": "explore", "title": "Explore"}
        ],
        "welcome_rich": [
            {"action": "get_started", "title": "Get Started"},
            {"action": "complete_profile", "title": "Complete Profile"},
            {"action": "add_vehicle", "title": "Add Vehicle"},
            {"action": "find_parking", "title": "Find Parking"},
            {"action": "invite_friends", "title": "Invite Friends"}
        ],
        "welcome_minimal": [
            {"action": "open", "title": "Open"}
        ],
        "welcome_bonus": [
            {"action": "claim", "title": "Claim Bonus"},
            {"action": "later", "title": "Remind Later"}
        ],
        "welcome_tips": [
            {"action": "view", "title": "View Tips"}
        ]
    }
    
    return actions.get(template_type, actions["welcome"])


def render_welcome_push(
    context: Dict[str, Any],
    platform: str = "all"
) -> Dict[str, Any]:
    """
    Render welcome push notification with smart template selection.
    
    Args:
        context: Template context
        platform: Target platform
        
    Returns:
        Dict[str, Any]: Rendered push notification
    """
    from ..base import template_manager
    
    # Get template name
    template_name = get_welcome_template(context, platform)
    
    # Add default context values if missing
    if "welcome_bonus" not in context:
        context["welcome_bonus"] = 0
    
    if "currency" not in context:
        context["currency"] = "USD"
    
    if "current_time" not in context:
        from datetime import datetime
        context["current_time"] = datetime.utcnow()
    
    # Render template
    rendered = template_manager.render("push", template_name, context, format="json")
    
    # Parse JSON
    import json
    payload = json.loads(rendered)
    
    # Validate payload
    validation = validate_push_payload(payload)
    if not validation["valid"]:
        # Fall back to minimal template
        fallback_payload = {
            "title": "Welcome to {{ app_name }}",
            "body": f"Thanks for joining, {context.get('user_name', 'user')}!",
            "data": {"type": "welcome"}
        }
        return fallback_payload
    
    return payload