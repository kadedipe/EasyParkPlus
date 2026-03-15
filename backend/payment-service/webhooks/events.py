"""
Standardized webhook event models.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from ..models.payment import PaymentStatus
from ..models.subscription import SubscriptionStatus


class WebhookEvent(BaseModel):
    """
    Base webhook event model.
    """
    event_id: str = Field(..., description="Event ID from gateway")
    event_type: str = Field(..., description="Event type")
    timestamp: datetime = Field(..., description="Event timestamp")
    gateway: str = Field(..., description="Payment gateway name")
    raw_data: Dict[str, Any] = Field(..., description="Raw event data")
    
    class Config:
        arbitrary_types_allowed = True


class PaymentEvent(WebhookEvent):
    """
    Payment-related webhook event.
    """
    payment_id: Optional[str] = Field(None, description="Payment ID")
    payment_status: Optional[PaymentStatus] = Field(None, description="Payment status")
    amount: Optional[float] = Field(None, description="Payment amount")
    currency: Optional[str] = Field(None, description="Currency code")
    customer_id: Optional[str] = Field(None, description="Customer ID")
    payment_method: Optional[str] = Field(None, description="Payment method")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SubscriptionEvent(WebhookEvent):
    """
    Subscription-related webhook event.
    """
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    subscription_status: Optional[SubscriptionStatus] = Field(None, description="Subscription status")
    customer_id: Optional[str] = Field(None, description="Customer ID")
    plan_id: Optional[str] = Field(None, description="Plan ID")
    current_period_start: Optional[datetime] = Field(None, description="Current period start")
    current_period_end: Optional[datetime] = Field(None, description="Current period end")
    cancel_at_period_end: bool = Field(False, description="Cancel at period end")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RefundEvent(WebhookEvent):
    """
    Refund-related webhook event.
    """
    refund_id: Optional[str] = Field(None, description="Refund ID")
    payment_id: Optional[str] = Field(None, description="Original payment ID")
    amount: Optional[float] = Field(None, description="Refund amount")
    currency: Optional[str] = Field(None, description="Currency code")
    refund_status: Optional[str] = Field(None, description="Refund status")
    reason: Optional[str] = Field(None, description="Refund reason")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CustomerEvent(WebhookEvent):
    """
    Customer-related webhook event.
    """
    customer_id: Optional[str] = Field(None, description="Customer ID")
    email: Optional[str] = Field(None, description="Customer email")
    name: Optional[str] = Field(None, description="Customer name")
    phone: Optional[str] = Field(None, description="Customer phone")
    address: Optional[Dict[str, Any]] = Field(None, description="Customer address")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class DisputeEvent(WebhookEvent):
    """
    Dispute-related webhook event.
    """
    dispute_id: Optional[str] = Field(None, description="Dispute ID")
    payment_id: Optional[str] = Field(None, description="Payment ID")
    amount: Optional[float] = Field(None, description="Dispute amount")
    currency: Optional[str] = Field(None, description="Currency code")
    reason: Optional[str] = Field(None, description="Dispute reason")
    status: Optional[str] = Field(None, description="Dispute status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")