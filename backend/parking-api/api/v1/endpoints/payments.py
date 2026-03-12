"""
Payment processing endpoints.
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.deps import get_current_user, get_current_active_superuser
from ....crud import crud_payment, crud_reservation
from ....models.user import User
from ....schemas.payment import (
    PaymentResponse,
    PaymentCreate,
    PaymentMethodResponse,
    PaymentMethodCreate,
    RefundCreate,
    ReceiptResponse
)
from ....db.session import get_db