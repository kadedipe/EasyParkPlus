"""
Authentication endpoints for user registration, login, and token management.
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ....core import security
from ....core.config import settings
from ....core.deps import get_current_user
from ....crud import crud_user
from ....models.user import User
from ....schemas.auth import (
    Token,
    LoginRequest,
    RegisterRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    RefreshTokenRequest,
    LogoutResponse
)
from ....schemas.user import UserResponse
from ....db.session import get_db
from ....services.email import send_reset_password_email
from ....services.audit import audit_log
from ....utils.rate_limiter import rate_limit
from ....utils.exceptions import (
    InvalidCredentialsException,
    UserAlreadyExistsException,
    InvalidTokenException,
    AccountDisabledException
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=5, window_seconds=3600)  # 5 requests per hour
async def register(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    user_in: RegisterRequest,
) -> Any:
    """
    Register a new user.
    
    - **email**: User's email address (must be unique)
    - **password**: Strong password (min 8 chars, with numbers and special chars)
    - **full_name**: User's full name
    - **phone**: Optional phone number
    """
    # Check if user exists
    existing_user = await crud_user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise UserAlreadyExistsException()
    
    # Create new user
    user = await crud_user.create(db, obj_in=user_in)
    
    # Create access token
    access_token = security.create_access_token(
        user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = security.create_refresh_token(user.id)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=user.id,
        action="REGISTER",
        resource="user",
        resource_id=user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": UserResponse.from_orm(user)
    }


@router.post("/login", response_model=Token)
@rate_limit(max_requests=10, window_seconds=300)  # 10 requests per 5 minutes
async def login(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    OAuth2 compatible token login.
    
    - **username**: User's email
    - **password**: User's password
    """
    # Authenticate user
    user = await crud_user.authenticate(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise InvalidCredentialsException()
    
    if not user.is_active:
        raise AccountDisabledException()
    
    # Update last login
    await crud_user.update_last_login(db, user_id=user.id)
    
    # Create tokens
    access_token = security.create_access_token(user.id)
    refresh_token = security.create_refresh_token(user.id)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=user.id,
        action="LOGIN",
        resource="user",
        resource_id=user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": UserResponse.from_orm(user)
    }


@router.post("/login/json", response_model=Token)
@rate_limit(max_requests=10, window_seconds=300)
async def login_json(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    login_data: LoginRequest,
) -> Any:
    """
    JSON-based login (alternative to form-based).
    """
    user = await crud_user.authenticate(
        db, email=login_data.email, password=login_data.password
    )
    if not user:
        raise InvalidCredentialsException()
    
    if not user.is_active:
        raise AccountDisabledException()
    
    await crud_user.update_last_login(db, user_id=user.id)
    
    access_token = security.create_access_token(user.id)
    refresh_token = security.create_refresh_token(user.id)
    
    await audit_log(
        db=db,
        user_id=user.id,
        action="LOGIN",
        resource="user",
        resource_id=user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": UserResponse.from_orm(user)
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    refresh_data: RefreshTokenRequest,
) -> Any:
    """
    Get new access token using refresh token.
    """
    # Verify refresh token
    token_data = security.verify_refresh_token(refresh_data.refresh_token)
    if not token_data:
        raise InvalidTokenException()
    
    # Get user
    user = await crud_user.get(db, id=token_data.user_id)
    if not user or not user.is_active:
        raise InvalidCredentialsException()
    
    # Create new tokens
    access_token = security.create_access_token(user.id)
    refresh_token = security.create_refresh_token(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Logout current user (blacklist token).
    """
    # Get token from header
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    
    # Blacklist token
    await security.blacklist_token(db, token)
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="LOGOUT",
        resource="user",
        resource_id=current_user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return {"message": "Successfully logged out"}


@router.post("/change-password", response_model=dict)
async def change_password(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Change user password.
    """
    # Verify current password
    if not security.verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Update password
    await crud_user.update_password(
        db, user_id=current_user.id, password=password_data.new_password
    )
    
    # Audit log
    await audit_log(
        db=db,
        user_id=current_user.id,
        action="CHANGE_PASSWORD",
        resource="user",
        resource_id=current_user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return {"message": "Password changed successfully"}


@router.post("/request-reset", response_model=dict)
@rate_limit(max_requests=3, window_seconds=3600)  # 3 requests per hour
async def request_password_reset(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    reset_data: PasswordResetRequest,
) -> Any:
    """
    Request password reset email.
    """
    user = await crud_user.get_by_email(db, email=reset_data.email)
    if user and user.is_active:
        # Generate reset token
        reset_token = security.create_password_reset_token(user.id)
        
        # Send email
        await send_reset_password_email(
            email_to=user.email,
            token=reset_token,
            full_name=user.full_name
        )
        
        # Audit log
        await audit_log(
            db=db,
            user_id=user.id,
            action="REQUEST_PASSWORD_RESET",
            resource="user",
            resource_id=user.id,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
    
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password", response_model=dict)
async def reset_password(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    reset_data: PasswordResetConfirmRequest,
) -> Any:
    """
    Reset password using token.
    """
    # Verify token
    user_id = security.verify_password_reset_token(reset_data.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Update password
    user = await crud_user.get(db, id=user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user"
        )
    
    await crud_user.update_password(
        db, user_id=user.id, password=reset_data.new_password
    )
    
    # Audit log
    await audit_log(
        db=db,
        user_id=user.id,
        action="RESET_PASSWORD",
        resource="user",
        resource_id=user.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    return {"message": "Password reset successfully"}


@router.get("/verify-email/{token}", response_model=dict)
async def verify_email(
    *,
    db: AsyncSession = Depends(get_db),
    token: str,
) -> Any:
    """
    Verify user email address.
    """
    user_id = security.verify_email_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user = await crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    await crud_user.verify_email(db, user_id=user.id)
    
    return {"message": "Email verified successfully"}


@router.post("/resend-verification", response_model=dict)
@rate_limit(max_requests=3, window_seconds=3600)
async def resend_verification(
    *,
    db: AsyncSession = Depends(get_db),
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Resend email verification link.
    """
    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    # Generate verification token
    verify_token = security.create_email_verification_token(current_user.id)
    
    # Send email
    await send_verification_email(
        email_to=current_user.email,
        token=verify_token,
        full_name=current_user.full_name
    )
    
    return {"message": "Verification email sent"}