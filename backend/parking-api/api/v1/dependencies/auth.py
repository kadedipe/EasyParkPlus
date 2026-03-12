"""
Authentication dependencies for FastAPI.
"""

from typing import Optional, Union
from fastapi import Depends, HTTPException, status, Request, WebSocket
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.security import decode_token, verify_token as verify_jwt_token
from ....core.config import settings
from ....crud import crud_user
from ....models.user import User
from ....db.session import get_db
from ....utils.exceptions import (
    AuthenticationException,
    AuthorizationException,
    InvalidTokenException,
    AccountDisabledException
)

# OAuth2 scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False
)

# HTTP Bearer for custom token handling
security = HTTPBearer(auto_error=False)


async def get_token_payload(
    token: Optional[str] = Depends(oauth2_scheme),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Extract and validate token payload from request.
    """
    # Get token from either OAuth2 or HTTP Bearer
    token_value = token
    if not token_value and credentials:
        token_value = credentials.credentials
    
    if not token_value:
        raise AuthenticationException("Not authenticated")
    
    # Verify token
    payload = verify_jwt_token(token_value)
    if not payload:
        raise InvalidTokenException("Invalid or expired token")
    
    return payload


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(get_token_payload)
) -> User:
    """
    Get current authenticated user.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenException("Invalid token payload")
    
    user = await crud_user.get(db, id=user_id)
    if not user:
        raise AuthenticationException("User not found")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (ensures user is active).
    """
    if not current_user.is_active:
        raise AccountDisabledException("User account is disabled")
    
    if not current_user.email_verified:
        raise AuthenticationException("Email not verified")
    
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current superuser (admin).
    """
    if current_user.role not in ["admin", "superuser"]:
        raise AuthorizationException("Insufficient permissions")
    
    return current_user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.replace("Bearer ", "")
    try:
        payload = verify_jwt_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                user = await crud_user.get(db, id=user_id)
                return user if user and user.is_active else None
    except:
        pass
    
    return None


async def get_current_user_ws(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from WebSocket connection.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing authentication token")
        return None
    
    try:
        payload = verify_jwt_token(token)
        if not payload:
            await websocket.close(code=1008, reason="Invalid token")
            return None
        
        user_id = payload.get("sub")
        user = await crud_user.get(db, id=user_id)
        
        if not user or not user.is_active:
            await websocket.close(code=1008, reason="User not found or inactive")
            return None
        
        return user
        
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return None


async def verify_token(token: str) -> bool:
    """
    Verify if a token is valid.
    """
    try:
        payload = verify_jwt_token(token)
        return payload is not None
    except:
        return False


class RoleBasedAccess:
    """
    Role-based access control dependency.
    """
    
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
    
    async def __call__(self, current_user: User = Depends(get_current_active_user)):
        if current_user.role not in self.allowed_roles:
            raise AuthorizationException(
                f"Role '{current_user.role}' not allowed. Required: {self.allowed_roles}"
            )
        return current_user


class PermissionBasedAccess:
    """
    Permission-based access control dependency.
    """
    
    def __init__(self, required_permissions: list):
        self.required_permissions = required_permissions
    
    async def __call__(self, current_user: User = Depends(get_current_active_user)):
        user_permissions = await self.get_user_permissions(current_user)
        
        missing_permissions = [
            perm for perm in self.required_permissions
            if perm not in user_permissions
        ]
        
        if missing_permissions:
            raise AuthorizationException(
                f"Missing permissions: {missing_permissions}"
            )
        
        return current_user
    
    async def get_user_permissions(self, user: User) -> list:
        """
        Get user permissions based on role.
        """
        # This could be loaded from database or configuration
        role_permissions = {
            "user": ["read:own", "create:reservation", "update:own"],
            "manager": ["read:any", "create:any", "update:any", "delete:own"],
            "admin": ["read:any", "create:any", "update:any", "delete:any"],
            "superuser": ["*"]
        }
        
        return role_permissions.get(user.role, [])


class ResourceOwnerCheck:
    """
    Check if user owns the resource.
    """
    
    def __init__(self, resource_id_param: str, resource_type: str):
        self.resource_id_param = resource_id_param
        self.resource_type = resource_type
    
    async def __call__(
        self,
        resource_id: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db)
    ):
        # This would need specific implementation per resource type
        # Example implementation for reservations:
        if self.resource_type == "reservation":
            from ....crud import crud_reservation
            reservation = await crud_reservation.get(db, id=resource_id)
            if not reservation:
                raise HTTPException(status_code=404, detail="Reservation not found")
            if reservation.user_id != current_user.id and current_user.role not in ["admin", "superuser"]:
                raise AuthorizationException("Not the owner of this reservation")
            return reservation
        
        return True