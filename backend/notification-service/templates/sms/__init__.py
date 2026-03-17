"""
SMS templates package initialization.
"""

from typing import Dict, Any, Optional
from ..base import TemplateManager

# Template versions by purpose
VERIFICATION_TEMPLATES = {
    "standard": "verification_code.txt",
    "alternative1": "verification_code_alt1.txt",
    "alternative2": "verification_code_alt2.txt",
    "alternative3": "verification_code_alt3.txt",
    "compact": "verification_code_compact.txt",
    "formal": "verification_code_formal.txt",
    "urgent": "verification_code_urgent.txt",
    "emoji": "verification_code_emoji.txt",
    "minimal": "verification_code_minimal.txt",
    "branded": "verification_code_branded.txt",
    "multilingual": "verification_code_multilingual_en_es.txt",
    "with_instructions": "verification_code_with_instructions.txt"
}

SPECIALIZED_TEMPLATES = {
    "login": "login_code.txt",
    "phone_verification": "phone_verification.txt",
    "password_reset": "password_reset_code.txt",
    "two_factor": "two_factor_code.txt",
    "email_verification": "email_verification_code.txt",
    "account_recovery": "account_recovery_code.txt",
    "security_alert": "verification_code_security.txt"
}

ALL_TEMPLATES = {**VERIFICATION_TEMPLATES, **SPECIALIZED_TEMPLATES}


def get_verification_template(
    template_type: str = "standard",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get appropriate verification template based on type and context.
    
    Args:
        template_type: Type of verification template
        context: Template context for smart selection
        
    Returns:
        str: Template filename
    """
    # Smart template selection based on context
    if context:
        # Use minimal for low-character environments
        if context.get("character_limit") and context["character_limit"] < 100:
            return VERIFICATION_TEMPLATES["minimal"]
        
        # Use urgent for time-sensitive operations
        if context.get("urgency") == "high":
            return VERIFICATION_TEMPLATES["urgent"]
        
        # Use formal for enterprise users
        if context.get("user_type") == "enterprise":
            return VERIFICATION_TEMPLATES["formal"]
        
        # Use multilingual for diverse audiences
        if context.get("preferred_language") == "multilingual":
            return VERIFICATION_TEMPLATES["multilingual"]
    
    # Return requested template or default
    return VERIFICATION_TEMPLATES.get(template_type, VERIFICATION_TEMPLATES["standard"])


def get_specialized_template(purpose: str) -> str:
    """
    Get specialized template for specific purpose.
    
    Args:
        purpose: Purpose of the verification (login, password_reset, etc.)
        
    Returns:
        str: Template filename
    """
    return SPECIALIZED_TEMPLATES.get(purpose, VERIFICATION_TEMPLATES["standard"])


def calculate_sms_segments(message: str) -> Dict[str, int]:
    """
    Calculate SMS segments and character count.
    
    Args:
        message: SMS message content
        
    Returns:
        Dict[str, int]: Character count and segments
    """
    char_count = len(message)
    
    # GSM 03.38 character set
    # Standard GSM characters: 160 per segment
    # Unicode: 70 per segment
    import re
    
    # Check if message contains non-GSM characters
    gsm_chars = r'^[@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !"#$%&\'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà^{}\[~\]|€]*$'
    
    if re.match(gsm_chars, message):
        # GSM 7-bit encoding
        if char_count <= 160:
            segments = 1
        else:
            segments = (char_count + 152) // 153  # 153 chars per segment for multi-part
    else:
        # Unicode (UCS-2) encoding
        if char_count <= 70:
            segments = 1
        else:
            segments = (char_count + 66) // 67  # 67 chars per segment for multi-part
    
    return {
        "characters": char_count,
        "segments": segments,
        "encoding": "GSM" if re.match(gsm_chars, message) else "Unicode"
    }


def optimize_sms_message(message: str, max_chars: int = 160) -> str:
    """
    Optimize SMS message to fit within character limits.
    
    Args:
        message: Original message
        max_chars: Maximum characters allowed
        
    Returns:
        str: Optimized message
    """
    if len(message) <= max_chars:
        return message
    
    # Remove extra whitespace
    message = ' '.join(message.split())
    
    if len(message) <= max_chars:
        return message
    
    # Truncate with ellipsis
    return message[:max_chars-3] + "..."

    """
SMS templates package initialization.
"""

from typing import Dict, Any, Optional
from ..base import TemplateManager

# Booking confirmation templates
BOOKING_TEMPLATES = {
    "standard": "booking_confirmation.txt",
    "detailed": "booking_confirmation_detailed.txt",
    "compact": "booking_confirmation_compact.txt",
    "with_address": "booking_confirmation_with_address.txt",
    "express": "booking_confirmation_express.txt",
    "premium": "booking_confirmation_premium.txt",
    "ev": "booking_confirmation_ev.txt",
    "monthly": "booking_confirmation_monthly.txt",
    "valet": "booking_confirmation_valet.txt",
    "airport": "booking_confirmation_airport.txt",
    "event": "booking_confirmation_event.txt",
    "overnight": "booking_confirmation_overnight.txt",
    "multiple": "booking_confirmation_multiple.txt",
    "accessibility": "booking_confirmation_accessibility.txt",
    "reservation": "booking_confirmation_reservation.txt",
    "instant": "booking_confirmation_instant.txt",
    "multilingual": "booking_confirmation_multilingual_en_es.txt"
}

# Verification templates (existing)
VERIFICATION_TEMPLATES = {
    "standard": "verification_code.txt",
    "alternative1": "verification_code_alt1.txt",
    "alternative2": "verification_code_alt2.txt",
    "alternative3": "verification_code_alt3.txt",
    "compact": "verification_code_compact.txt",
    "formal": "verification_code_formal.txt",
    "urgent": "verification_code_urgent.txt",
    "emoji": "verification_code_emoji.txt",
    "minimal": "verification_code_minimal.txt",
    "branded": "verification_code_branded.txt",
    "multilingual": "verification_code_multilingual_en_es.txt",
    "with_instructions": "verification_code_with_instructions.txt"
}

# Specialized templates (existing)
SPECIALIZED_TEMPLATES = {
    "login": "login_code.txt",
    "phone_verification": "phone_verification.txt",
    "password_reset": "password_reset_code.txt",
    "two_factor": "two_factor_code.txt",
    "email_verification": "email_verification_code.txt",
    "account_recovery": "account_recovery_code.txt",
    "security_alert": "verification_code_security.txt"
}

ALL_TEMPLATES = {**BOOKING_TEMPLATES, **VERIFICATION_TEMPLATES, **SPECIALIZED_TEMPLATES}


def get_booking_template(
    booking_type: str = "standard",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get appropriate booking confirmation template based on type and context.
    
    Args:
        booking_type: Type of booking (standard, ev, monthly, valet, etc.)
        context: Template context for smart selection
        
    Returns:
        str: Template filename
    """
    # Smart template selection based on context
    if context:
        # EV charging booking
        if context.get("is_ev"):
            return BOOKING_TEMPLATES["ev"]
        
        # Monthly pass
        if context.get("is_monthly"):
            return BOOKING_TEMPLATES["monthly"]
        
        # Valet service
        if context.get("is_valet"):
            return BOOKING_TEMPLATES["valet"]
        
        # Airport parking
        if context.get("is_airport"):
            return BOOKING_TEMPLATES["airport"]
        
        # Event parking
        if context.get("is_event"):
            return BOOKING_TEMPLATES["event"]
        
        # Overnight parking
        if context.get("is_overnight"):
            return BOOKING_TEMPLATES["overnight"]
        
        # Multiple vehicles
        if context.get("vehicle_count", 1) > 1:
            return BOOKING_TEMPLATES["multiple"]
        
        # Accessible parking
        if context.get("is_accessible"):
            return BOOKING_TEMPLATES["accessibility"]
        
        # Premium service
        if context.get("is_premium"):
            return BOOKING_TEMPLATES["premium"]
        
        # Express check-in
        if context.get("is_express"):
            return BOOKING_TEMPLATES["express"]
        
        # Character limit constraints
        if context.get("character_limit") and context["character_limit"] < 120:
            return BOOKING_TEMPLATES["compact"]
        
        # Detailed preference
        if context.get("prefer_detailed"):
            return BOOKING_TEMPLATES["detailed"]
        
        # Multilingual preference
        if context.get("preferred_language") == "multilingual":
            return BOOKING_TEMPLATES["multilingual"]
    
    # Return requested template or default
    return BOOKING_TEMPLATES.get(booking_type, BOOKING_TEMPLATES["standard"])


def get_verification_template(
    template_type: str = "standard",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get appropriate verification template based on type and context.
    
    Args:
        template_type: Type of verification template
        context: Template context for smart selection
        
    Returns:
        str: Template filename
    """
    # Smart template selection based on context
    if context:
        # Use minimal for low-character environments
        if context.get("character_limit") and context["character_limit"] < 100:
            return VERIFICATION_TEMPLATES["minimal"]
        
        # Use urgent for time-sensitive operations
        if context.get("urgency") == "high":
            return VERIFICATION_TEMPLATES["urgent"]
        
        # Use formal for enterprise users
        if context.get("user_type") == "enterprise":
            return VERIFICATION_TEMPLATES["formal"]
        
        # Use multilingual for diverse audiences
        if context.get("preferred_language") == "multilingual":
            return VERIFICATION_TEMPLATES["multilingual"]
    
    # Return requested template or default
    return VERIFICATION_TEMPLATES.get(template_type, VERIFICATION_TEMPLATES["standard"])


def get_specialized_template(purpose: str) -> str:
    """
    Get specialized template for specific purpose.
    
    Args:
        purpose: Purpose of the verification (login, password_reset, etc.)
        
    Returns:
        str: Template filename
    """
    return SPECIALIZED_TEMPLATES.get(purpose, VERIFICATION_TEMPLATES["standard"])


def calculate_sms_segments(message: str) -> Dict[str, int]:
    """
    Calculate SMS segments and character count.
    
    Args:
        message: SMS message content
        
    Returns:
        Dict[str, int]: Character count and segments
    """
    char_count = len(message)
    
    # GSM 03.38 character set
    import re
    
    # Check if message contains non-GSM characters
    gsm_chars = r'^[@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !"#$%&\'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà^{}\[~\]|€]*$'
    
    if re.match(gsm_chars, message):
        # GSM 7-bit encoding
        if char_count <= 160:
            segments = 1
        else:
            segments = (char_count + 152) // 153  # 153 chars per segment for multi-part
        encoding = "GSM"
    else:
        # Unicode (UCS-2) encoding
        if char_count <= 70:
            segments = 1
        else:
            segments = (char_count + 66) // 67  # 67 chars per segment for multi-part
        encoding = "Unicode"
    
    return {
        "characters": char_count,
        "segments": segments,
        "encoding": encoding
    }


def optimize_sms_message(message: str, max_chars: int = 160) -> str:
    """
    Optimize SMS message to fit within character limits.
    
    Args:
        message: Original message
        max_chars: Maximum characters allowed
        
    Returns:
        str: Optimized message
    """
    if len(message) <= max_chars:
        return message
    
    # Remove extra whitespace
    message = ' '.join(message.split())
    
    if len(message) <= max_chars:
        return message
    
    # Truncate with ellipsis
    return message[:max_chars-3] + "..."

    """
SMS templates package initialization.
"""

from typing import Dict, Any, Optional
from ..base import TemplateManager

# Payment success templates
PAYMENT_TEMPLATES = {
    "standard": "payment_success.txt",
    "detailed": "payment_success_detailed.txt",
    "compact": "payment_success_compact.txt",
    "booking": "payment_success_booking.txt",
    "subscription": "payment_success_subscription.txt",
    "invoice": "payment_success_invoice.txt",
    "wallet": "payment_success_wallet.txt",
    "deposit": "payment_success_deposit.txt",
    "refund": "payment_success_refund.txt",
    "credit": "payment_success_credit.txt",
    "premium": "payment_success_premium.txt",
    "express": "payment_success_express.txt",
    "card": "payment_success_card.txt",
    "cash": "payment_success_cash.txt",
    "bank_transfer": "payment_success_bank_transfer.txt",
    "multilingual": "payment_success_multilingual_en_es.txt",
    "security": "payment_success_security.txt",
    "merchant": "payment_success_merchant.txt",
    "installment": "payment_success_installment.txt"
}

# Booking confirmation templates
BOOKING_TEMPLATES = {
    "standard": "booking_confirmation.txt",
    "detailed": "booking_confirmation_detailed.txt",
    "compact": "booking_confirmation_compact.txt",
    "with_address": "booking_confirmation_with_address.txt",
    "express": "booking_confirmation_express.txt",
    "premium": "booking_confirmation_premium.txt",
    "ev": "booking_confirmation_ev.txt",
    "monthly": "booking_confirmation_monthly.txt",
    "valet": "booking_confirmation_valet.txt",
    "airport": "booking_confirmation_airport.txt",
    "event": "booking_confirmation_event.txt",
    "overnight": "booking_confirmation_overnight.txt",
    "multiple": "booking_confirmation_multiple.txt",
    "accessibility": "booking_confirmation_accessibility.txt",
    "reservation": "booking_confirmation_reservation.txt",
    "instant": "booking_confirmation_instant.txt",
    "multilingual": "booking_confirmation_multilingual_en_es.txt"
}

# Verification templates
VERIFICATION_TEMPLATES = {
    "standard": "verification_code.txt",
    "alternative1": "verification_code_alt1.txt",
    "alternative2": "verification_code_alt2.txt",
    "alternative3": "verification_code_alt3.txt",
    "compact": "verification_code_compact.txt",
    "formal": "verification_code_formal.txt",
    "urgent": "verification_code_urgent.txt",
    "emoji": "verification_code_emoji.txt",
    "minimal": "verification_code_minimal.txt",
    "branded": "verification_code_branded.txt",
    "multilingual": "verification_code_multilingual_en_es.txt",
    "with_instructions": "verification_code_with_instructions.txt"
}

# Specialized templates
SPECIALIZED_TEMPLATES = {
    "login": "login_code.txt",
    "phone_verification": "phone_verification.txt",
    "password_reset": "password_reset_code.txt",
    "two_factor": "two_factor_code.txt",
    "email_verification": "email_verification_code.txt",
    "account_recovery": "account_recovery_code.txt",
    "security_alert": "verification_code_security.txt"
}

ALL_TEMPLATES = {
    **PAYMENT_TEMPLATES,
    **BOOKING_TEMPLATES,
    **VERIFICATION_TEMPLATES,
    **SPECIALIZED_TEMPLATES
}


def get_payment_template(
    payment_type: str = "standard",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get appropriate payment confirmation template based on type and context.
    
    Args:
        payment_type: Type of payment (standard, booking, subscription, etc.)
        context: Template context for smart selection
        
    Returns:
        str: Template filename
    """
    # Smart template selection based on context
    if context:
        # Booking payment
        if context.get("is_booking_payment"):
            return PAYMENT_TEMPLATES["booking"]
        
        # Subscription payment
        if context.get("is_subscription"):
            return PAYMENT_TEMPLATES["subscription"]
        
        # Invoice payment
        if context.get("is_invoice"):
            return PAYMENT_TEMPLATES["invoice"]
        
        # Wallet top-up
        if context.get("is_wallet_topup"):
            return PAYMENT_TEMPLATES["wallet"]
        
        # Security deposit
        if context.get("is_deposit"):
            return PAYMENT_TEMPLATES["deposit"]
        
        # Refund
        if context.get("is_refund"):
            return PAYMENT_TEMPLATES["refund"]
        
        # Credit applied
        if context.get("is_credit"):
            return PAYMENT_TEMPLATES["credit"]
        
        # Premium membership
        if context.get("is_premium"):
            return PAYMENT_TEMPLATES["premium"]
        
        # Installment payment
        if context.get("is_installment"):
            return PAYMENT_TEMPLATES["installment"]
        
        # Merchant payment
        if context.get("is_merchant_payment"):
            return PAYMENT_TEMPLATES["merchant"]
        
        # Payment method specific
        payment_method = context.get("payment_method", "").lower()
        if "card" in payment_method:
            return PAYMENT_TEMPLATES["card"]
        elif "cash" in payment_method:
            return PAYMENT_TEMPLATES["cash"]
        elif "bank" in payment_method or "transfer" in payment_method:
            return PAYMENT_TEMPLATES["bank_transfer"]
        
        # Character limit constraints
        if context.get("character_limit") and context["character_limit"] < 120:
            return PAYMENT_TEMPLATES["compact"]
        
        # Detailed preference
        if context.get("prefer_detailed"):
            return PAYMENT_TEMPLATES["detailed"]
        
        # Express preference
        if context.get("prefer_express"):
            return PAYMENT_TEMPLATES["express"]
        
        # Security focus
        if context.get("high_security"):
            return PAYMENT_TEMPLATES["security"]
        
        # Multilingual preference
        if context.get("preferred_language") == "multilingual":
            return PAYMENT_TEMPLATES["multilingual"]
    
    # Return requested template or default
    return PAYMENT_TEMPLATES.get(payment_type, PAYMENT_TEMPLATES["standard"])


def get_booking_template(
    booking_type: str = "standard",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get appropriate booking confirmation template based on type and context.
    """
    # Smart template selection based on context
    if context:
        # EV charging booking
        if context.get("is_ev"):
            return BOOKING_TEMPLATES["ev"]
        
        # Monthly pass
        if context.get("is_monthly"):
            return BOOKING_TEMPLATES["monthly"]
        
        # Valet service
        if context.get("is_valet"):
            return BOOKING_TEMPLATES["valet"]
        
        # Airport parking
        if context.get("is_airport"):
            return BOOKING_TEMPLATES["airport"]
        
        # Event parking
        if context.get("is_event"):
            return BOOKING_TEMPLATES["event"]
        
        # Overnight parking
        if context.get("is_overnight"):
            return BOOKING_TEMPLATES["overnight"]
        
        # Multiple vehicles
        if context.get("vehicle_count", 1) > 1:
            return BOOKING_TEMPLATES["multiple"]
        
        # Accessible parking
        if context.get("is_accessible"):
            return BOOKING_TEMPLATES["accessibility"]
        
        # Premium service
        if context.get("is_premium"):
            return BOOKING_TEMPLATES["premium"]
        
        # Express check-in
        if context.get("is_express"):
            return BOOKING_TEMPLATES["express"]
        
        # Character limit constraints
        if context.get("character_limit") and context["character_limit"] < 120:
            return BOOKING_TEMPLATES["compact"]
        
        # Detailed preference
        if context.get("prefer_detailed"):
            return BOOKING_TEMPLATES["detailed"]
        
        # Multilingual preference
        if context.get("preferred_language") == "multilingual":
            return BOOKING_TEMPLATES["multilingual"]
    
    # Return requested template or default
    return BOOKING_TEMPLATES.get(booking_type, BOOKING_TEMPLATES["standard"])


def get_verification_template(
    template_type: str = "standard",
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Get appropriate verification template based on type and context.
    """
    # Smart template selection based on context
    if context:
        # Use minimal for low-character environments
        if context.get("character_limit") and context["character_limit"] < 100:
            return VERIFICATION_TEMPLATES["minimal"]
        
        # Use urgent for time-sensitive operations
        if context.get("urgency") == "high":
            return VERIFICATION_TEMPLATES["urgent"]
        
        # Use formal for enterprise users
        if context.get("user_type") == "enterprise":
            return VERIFICATION_TEMPLATES["formal"]
        
        # Use multilingual for diverse audiences
        if context.get("preferred_language") == "multilingual":
            return VERIFICATION_TEMPLATES["multilingual"]
    
    # Return requested template or default
    return VERIFICATION_TEMPLATES.get(template_type, VERIFICATION_TEMPLATES["standard"])


def get_specialized_template(purpose: str) -> str:
    """
    Get specialized template for specific purpose.
    
    Args:
        purpose: Purpose of the verification (login, password_reset, etc.)
        
    Returns:
        str: Template filename
    """
    return SPECIALIZED_TEMPLATES.get(purpose, VERIFICATION_TEMPLATES["standard"])


def calculate_sms_segments(message: str) -> Dict[str, int]:
    """
    Calculate SMS segments and character count.
    
    Args:
        message: SMS message content
        
    Returns:
        Dict[str, int]: Character count and segments
    """
    char_count = len(message)
    
    # GSM 03.38 character set
    import re
    
    # Check if message contains non-GSM characters
    gsm_chars = r'^[@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !"#$%&\'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà^{}\[~\]|€]*$'
    
    if re.match(gsm_chars, message):
        # GSM 7-bit encoding
        if char_count <= 160:
            segments = 1
        else:
            segments = (char_count + 152) // 153  # 153 chars per segment for multi-part
        encoding = "GSM"
    else:
        # Unicode (UCS-2) encoding
        if char_count <= 70:
            segments = 1
        else:
            segments = (char_count + 66) // 67  # 67 chars per segment for multi-part
        encoding = "Unicode"
    
    return {
        "characters": char_count,
        "segments": segments,
        "encoding": encoding
    }


def optimize_sms_message(message: str, max_chars: int = 160) -> str:
    """
    Optimize SMS message to fit within character limits.
    
    Args:
        message: Original message
        max_chars: Maximum characters allowed
        
    Returns:
        str: Optimized message
    """
    if len(message) <= max_chars:
        return message
    
    # Remove extra whitespace
    message = ' '.join(message.split())
    
    if len(message) <= max_chars:
        return message
    
    # Truncate with ellipsis
    return message[:max_chars-3] + "..."