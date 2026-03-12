"""
Permission and role-based access control dependencies.
"""

from typing import List, Optional, Callable, Any
from functools import wraps
from fastapi import Depends, HTTPException, status

from ....models.user import User
from .auth import get_current_active_user, get_current_superuser
from ....utils.exceptions import AuthorizationException


class PermissionChecker:
    """
    Check if user has required permissions.
    """
    
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    async def __call__(self, current_user: User = Depends(get_current_active_user)):
        user_permissions = await self.get_user_permissions(current_user)
        
        for permission in self.required_permissions:
            if permission not in user_permissions and '*' not in user_permissions:
                raise AuthorizationException(
                    f"Missing required permission: {permission}"
                )
        
        return current_user
    
    async def get_user_permissions(self, user: User) -> List[str]:
        """
        Get permissions for user based on role.
        """
        # This could be loaded from database
        role_permissions = {
            'user': [
                'reservation:create',
                'reservation:read:own',
                'reservation:update:own',
                'reservation:delete:own',
                'vehicle:create',
                'vehicle:read:own',
                'vehicle:update:own',
                'vehicle:delete:own',
                'payment:create',
                'payment:read:own',
                'review:create',
                'review:read:own',
                'review:update:own',
                'review:delete:own'
            ],
            'manager': [
                'reservation:read:any',
                'reservation:update:any',
                'parking:create',
                'parking:read:any',
                'parking:update:any',
                'parking:delete:any',
                'user:read:any',
                'report:read:any'
            ],
            'admin': [
                '*'
            ]
        }
        
        return role_permissions.get(user.role, [])


class RoleChecker:
    """
    Check if user has required role.
    """
    
    def __init__(self, required_roles: List[str]):
        self.required_roles = required_roles
    
    async def __call__(self, current_user: User = Depends(get_current_active_user)):
        if current_user.role not in self.required_roles:
            raise AuthorizationException(
                f"Role '{current_user.role}' not allowed. Required: {self.required_roles}"
            )
        return current_user


def require_permissions(permissions: List[str]):
    """
    Decorator for requiring permissions.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from kwargs or args
            current_user = None
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break
            
            if not current_user and 'current_user' in kwargs:
                current_user = kwargs['current_user']
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permissions
            checker = PermissionChecker(permissions)
            await checker(current_user)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_roles(roles: List[str]):
    """
    Decorator for requiring roles.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from kwargs or args
            current_user = None
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break
            
            if not current_user and 'current_user' in kwargs:
                current_user = kwargs['current_user']
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check roles
            if current_user.role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{current_user.role}' not allowed"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


async def check_ownership(
    resource_owner_id: str,
    current_user: User = Depends(get_current_active_user),
    allow_admin: bool = True
) -> bool:
    """
    Check if user owns the resource or is admin.
    """
    if allow_admin and current_user.role in ['admin', 'superuser']:
        return True
    
    return str(resource_owner_id) == str(current_user.id)


class OwnershipChecker:
    """
    Check if user owns the resource.
    """
    
    def __init__(
        self,
        get_owner_id_func: Callable[[Any], str],
        resource_name: str = "resource"
    ):
        self.get_owner_id_func = get_owner_id_func
        self.resource_name = resource_name
    
    async def __call__(
        self,
        resource: Any,
        current_user: User = Depends(get_current_active_user)
    ):
        owner_id = self.get_owner_id_func(resource)
        
        if not await check_ownership(owner_id, current_user):
            raise AuthorizationException(
                f"You don't have permission to access this {self.resource_name}"
            )
        
        return resource


class CompositePermission:
    """
    Combine multiple permission checks.
    """
    
    def __init__(self, *checks: Callable):
        self.checks = checks
    
    async def __call__(self, current_user: User = Depends(get_current_active_user)):
        for check in self.checks:
            if callable(check):
                await check(current_user)
        return current_user


def is_superuser(current_user: User = Depends(get_current_active_user)):
    """
    Check if user is superuser.
    """
    if current_user.role != 'superuser':
        raise AuthorizationException("Superuser access required")
    return current_user


def is_admin(current_user: User = Depends(get_current_active_user)):
    """
    Check if user is admin.
    """
    if current_user.role not in ['admin', 'superuser']:
        raise AuthorizationException("Admin access required")
    return current_user


def is_manager(current_user: User = Depends(get_current_active_user)):
    """
    Check if user is manager or higher.
    """
    if current_user.role not in ['manager', 'admin', 'superuser']:
        raise AuthorizationException("Manager access required")
    return current_user


def is_verified(current_user: User = Depends(get_current_active_user)):
    """
    Check if user email is verified.
    """
    if not current_user.email_verified:
        raise AuthorizationException("Email verification required")
    return current_user


class Permission:
    """
    Permission constants.
    """
    
    # User permissions
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Reservation permissions
    RESERVATION_CREATE = "reservation:create"
    RESERVATION_READ_OWN = "reservation:read:own"
    RESERVATION_READ_ANY = "reservation:read:any"
    RESERVATION_UPDATE_OWN = "reservation:update:own"
    RESERVATION_UPDATE_ANY = "reservation:update:any"
    RESERVATION_DELETE_OWN = "reservation:delete:own"
    RESERVATION_DELETE_ANY = "reservation:delete:any"
    
    # Parking spot permissions
    PARKING_CREATE = "parking:create"
    PARKING_READ = "parking:read"
    PARKING_UPDATE = "parking:update"
    PARKING_DELETE = "parking:delete"
    
    # Vehicle permissions
    VEHICLE_CREATE = "vehicle:create"
    VEHICLE_READ_OWN = "vehicle:read:own"
    VEHICLE_READ_ANY = "vehicle:read:any"
    VEHICLE_UPDATE_OWN = "vehicle:update:own"
    VEHICLE_UPDATE_ANY = "vehicle:update:any"
    VEHICLE_DELETE_OWN = "vehicle:delete:own"
    VEHICLE_DELETE_ANY = "vehicle:delete:any"
    
    # Payment permissions
    PAYMENT_CREATE = "payment:create"
    PAYMENT_READ_OWN = "payment:read:own"
    PAYMENT_READ_ANY = "payment:read:any"
    PAYMENT_REFUND = "payment:refund"
    
    # Review permissions
    REVIEW_CREATE = "review:create"
    REVIEW_READ = "review:read"
    REVIEW_UPDATE_OWN = "review:update:own"
    REVIEW_UPDATE_ANY = "review:update:any"
    REVIEW_DELETE_OWN = "review:delete:own"
    REVIEW_DELETE_ANY = "review:delete:any"
    
    # Admin permissions
    ADMIN_ACCESS = "admin:access"
    REPORT_READ = "report:read"
    AUDIT_READ = "audit:read"
    SETTINGS_UPDATE = "settings:update"