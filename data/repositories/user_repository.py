# parking-management/data/migrations/repositories/user_repository.py
"""
User repository module for the parking management system.

This module provides repository classes for managing users, authentication,
sessions, and user-related data with comprehensive audit trails and
integration with the enum definitions.
"""

from typing import (
    List, Optional, Dict, Any, Tuple, Union
)
from datetime import datetime, timedelta
import logging
import hashlib
import secrets
from uuid import uuid4

from sqlalchemy import (
    and_, or_, not_, desc, asc, func, select,
    update, delete, Boolean, Integer, String, DateTime
)
from sqlalchemy.orm import Session, Query, joinedload, selectinload
from sqlalchemy.exc import IntegrityError, NoResultFound

from .base_repository import (
    BaseRepository,
    AuditableRepository,
    CacheableRepository,
    SearchableRepository,
    FullFeatureRepository,
    EntityNotFoundException,
    DuplicateEntityException,
    ValidationException,
    RepositoryException
)
from ..models.enums import (
    # User enums
    UserStatus,
    UserRole,
    AuthMethod,
    MFAMethod,
    
    # Audit enums
    AuditAction,
    AuditStatus,
    AuditSeverity,
    AuditCategory,
    AuditResourceType,
    
    # Notification enums
    NotificationType,
    NotificationChannel,
    
    # General enums
    Language,
    CountryCode,
    Timezone
)
from ..models.user_models import (
    # User models
    User,
    UserProfile,
    UserSession,
    UserPreference,
    UserDevice,
    UserAuditLog,
    
    # Auth models
    AuthProvider,
    MFASetting,
    PasswordResetToken,
    EmailVerificationToken,
    APIKey,
    OAuthState,
    
    # Role models
    Role,
    Permission,
    RoleAssignment
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exceptions
# ============================================================================

class UserNotFoundException(EntityNotFoundException):
    """Raised when a user is not found."""
    def __init__(self, user_id: Any):
        super().__init__("User", user_id)


class UserAuthenticationException(RepositoryException):
    """Raised when user authentication fails."""
    def __init__(self, message: str, username: Optional[str] = None):
        self.username = username
        super().__init__(f"Authentication failed: {message}")


class AccountLockedException(RepositoryException):
    """Raised when a user account is locked."""
    def __init__(self, user_id: int, locked_until: Optional[datetime] = None):
        self.user_id = user_id
        self.locked_until = locked_until
        message = f"Account {user_id} is locked"
        if locked_until:
            message += f" until {locked_until.isoformat()}"
        super().__init__(message)


class AccountSuspendedException(RepositoryException):
    """Raised when a user account is suspended."""
    def __init__(self, user_id: int, reason: Optional[str] = None):
        self.user_id = user_id
        self.reason = reason
        message = f"Account {user_id} is suspended"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class InsufficientPermissionsException(RepositoryException):
    """Raised when a user lacks required permissions."""
    def __init__(self, user_id: int, required_permission: str):
        self.user_id = user_id
        self.required_permission = required_permission
        super().__init__(
            f"User {user_id} lacks required permission: {required_permission}"
        )


class InvalidMFACodeException(RepositoryException):
    """Raised when an invalid MFA code is provided."""
    def __init__(self, user_id: int, method: MFAMethod):
        self.user_id = user_id
        self.method = method
        super().__init__(f"Invalid MFA code for user {user_id} using {method.value}")


class PasswordExpiredException(RepositoryException):
    """Raised when a user's password has expired."""
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"Password expired for user {user_id}")


# ============================================================================
# User Repository
# ============================================================================

class UserRepository(FullFeatureRepository[User, int]):
    """
    Repository for User entity with comprehensive user management features.
    
    This repository provides methods for user CRUD operations, authentication,
    profile management, and user status management with full audit trail.
    """
    
    def __init__(self, session: Session):
        super().__init__(session, User)
        self.searchable_fields = ['email', 'username', 'first_name', 'last_name', 'phone']
        
        # Password policy configuration
        self.password_min_length = 8
        self.password_require_uppercase = True
        self.password_require_lowercase = True
        self.password_require_numbers = True
        self.password_require_special = True
        self.password_expiry_days = 90
        self.max_login_attempts = 5
        self.lockout_duration_minutes = 30
    
    # ========================================================================
    # Custom Query Methods
    # ========================================================================
    
    def get_by_email(self, email: str, include_inactive: bool = False) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: Email address to search for
            include_inactive: Whether to include inactive users
            
        Returns:
            User if found, None otherwise
        """
        query = self.session.query(User).filter(User.email == email.lower())
        
        if not include_inactive:
            query = query.filter(User.status.in_(UserStatus.get_active_statuses()))
        
        return query.first()
    
    def get_by_username(self, username: str, include_inactive: bool = False) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username to search for
            include_inactive: Whether to include inactive users
            
        Returns:
            User if found, None otherwise
        """
        query = self.session.query(User).filter(User.username == username.lower())
        
        if not include_inactive:
            query = query.filter(User.status.in_(UserStatus.get_active_statuses()))
        
        return query.first()
    
    def get_by_phone(self, phone: str, include_inactive: bool = False) -> Optional[User]:
        """
        Get user by phone number.
        
        Args:
            phone: Phone number to search for
            include_inactive: Whether to include inactive users
            
        Returns:
            User if found, None otherwise
        """
        query = self.session.query(User).filter(User.phone == phone)
        
        if not include_inactive:
            query = query.filter(User.status.in_(UserStatus.get_active_statuses()))
        
        return query.first()
    
    def get_by_auth_provider(
        self,
        provider: AuthMethod,
        provider_user_id: str
    ) -> Optional[User]:
        """
        Get user by authentication provider details.
        
        Args:
            provider: Authentication provider
            provider_user_id: User ID from the provider
            
        Returns:
            User if found, None otherwise
        """
        auth_provider = (
            self.session.query(AuthProvider)
            .filter(
                AuthProvider.provider == provider,
                AuthProvider.provider_user_id == provider_user_id
            )
            .first()
        )
        
        return auth_provider.user if auth_provider else None
    
    def get_users_by_role(self, role: UserRole, active_only: bool = True) -> List[User]:
        """
        Get all users with a specific role.
        
        Args:
            role: Role to filter by
            active_only: Whether to return only active users
            
        Returns:
            List of users with the specified role
        """
        query = (
            self.session.query(User)
            .join(RoleAssignment)
            .join(Role)
            .filter(Role.name == role.value)
        )
        
        if active_only:
            query = query.filter(User.status.in_(UserStatus.get_active_statuses()))
        
        return query.all()
    
    def get_users_by_permission(
        self,
        permission: str,
        resource_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[User]:
        """
        Get all users with a specific permission.
        
        Args:
            permission: Permission name
            resource_type: Optional resource type filter
            active_only: Whether to return only active users
            
        Returns:
            List of users with the specified permission
        """
        query = (
            self.session.query(User)
            .join(RoleAssignment)
            .join(Role)
            .join(Role.permissions)
            .filter(Permission.name == permission)
        )
        
        if resource_type:
            query = query.filter(Permission.resource_type == resource_type)
        
        if active_only:
            query = query.filter(User.status.in_(UserStatus.get_active_statuses()))
        
        return query.all()
    
    def get_users_by_status(
        self,
        statuses: List[UserStatus],
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get users by status.
        
        Args:
            statuses: List of statuses to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of users with the specified statuses
        """
        return (
            self.session.query(User)
            .filter(User.status.in_(statuses))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_recently_active_users(
        self,
        minutes: int = 30,
        limit: int = 100
    ) -> List[User]:
        """
        Get users active within the last N minutes.
        
        Args:
            minutes: Number of minutes to look back
            limit: Maximum number of records to return
            
        Returns:
            List of recently active users
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        return (
            self.session.query(User)
            .join(UserSession)
            .filter(UserSession.last_activity >= cutoff)
            .filter(UserSession.is_active == True)
            .distinct()
            .limit(limit)
            .all()
        )
    
    def search_users(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[User], Dict[str, Any]]:
        """
        Search users with advanced filtering.
        
        Args:
            query: Search query string
            filters: Additional filters (status, role, etc.)
            page: Page number
            per_page: Items per page
            
        Returns:
            Tuple of (users, pagination_info)
        """
        qb = self.query()
        
        # Apply text search
        if query:
            qb.search(query, self.searchable_fields)
        
        # Apply filters
        if filters:
            if 'status' in filters and filters['status']:
                qb.filter(User.status == filters['status'])
            
            if 'role' in filters and filters['role']:
                qb.join(RoleAssignment).join(Role).filter(Role.name == filters['role'])
            
            if 'created_after' in filters and filters['created_after']:
                qb.filter(User.created_at >= filters['created_after'])
            
            if 'created_before' in filters and filters['created_before']:
                qb.filter(User.created_at <= filters['created_before'])
            
            if 'email_verified' in filters:
                if filters['email_verified']:
                    qb.filter(User.email_verified_at.isnot(None))
                else:
                    qb.filter(User.email_verified_at.is_(None))
            
            if 'phone_verified' in filters:
                if filters['phone_verified']:
                    qb.filter(User.phone_verified_at.isnot(None))
                else:
                    qb.filter(User.phone_verified_at.is_(None))
        
        # Apply pagination
        return qb.paginate(page, per_page)
    
    # ========================================================================
    # User Management Methods
    # ========================================================================
    
    def create_user(
        self,
        email: str,
        username: Optional[str] = None,
        password_hash: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        role: UserRole = UserRole.USER,
        status: UserStatus = UserStatus.PENDING,
        **kwargs
    ) -> User:
        """
        Create a new user with comprehensive validation.
        
        Args:
            email: User's email address
            username: Optional username
            password_hash: Optional password hash
            first_name: Optional first name
            last_name: Optional last name
            phone: Optional phone number
            role: User role
            status: Initial user status
            **kwargs: Additional user attributes
            
        Returns:
            Created user
            
        Raises:
            DuplicateEntityException: If email or username already exists
            ValidationException: If validation fails
        """
        # Normalize email and username
        email = email.lower().strip()
        if username:
            username = username.lower().strip()
        
        # Check for duplicates
        if self.get_by_email(email, include_inactive=True):
            raise DuplicateEntityException("User", "email", email)
        
        if username and self.get_by_username(username, include_inactive=True):
            raise DuplicateEntityException("User", "username", username)
        
        if phone and self.get_by_phone(phone, include_inactive=True):
            raise DuplicateEntityException("User", "phone", phone)
        
        # Set audit context
        self.set_audit_context(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.USER,
            severity=AuditSeverity.INFO
        )
        
        # Create user
        user = User(
            email=email,
            username=username,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            status=status,
            **kwargs
        )
        
        # Create user profile
        user.profile = UserProfile()
        
        # Create default preferences
        user.preferences = UserPreference()
        
        # Assign role
        self._assign_role(user, role)
        
        # Save user
        user = self.create(user)
        
        # Create audit log
        self._create_audit_log(
            user_id=user.id,
            action=AuditAction.CREATE,
            details={"role": role.value, "status": status.value}
        )
        
        logger.info(f"Created user {user.id} with email {email}")
        return user
    
    def update_user(
        self,
        user_id: int,
        **updates
    ) -> User:
        """
        Update user information.
        
        Args:
            user_id: User ID
            **updates: Fields to update
            
        Returns:
            Updated user
            
        Raises:
            UserNotFoundException: If user not found
            DuplicateEntityException: If email or username conflict
            ValidationException: If validation fails
        """
        user = self.get_or_fail(user_id)
        
        # Check for email uniqueness if being updated
        if 'email' in updates and updates['email'] != user.email:
            updates['email'] = updates['email'].lower().strip()
            existing = self.get_by_email(updates['email'], include_inactive=True)
            if existing and existing.id != user_id:
                raise DuplicateEntityException("User", "email", updates['email'])
        
        # Check for username uniqueness if being updated
        if 'username' in updates and updates['username'] != user.username:
            if updates['username']:
                updates['username'] = updates['username'].lower().strip()
                existing = self.get_by_username(updates['username'], include_inactive=True)
                if existing and existing.id != user_id:
                    raise DuplicateEntityException("User", "username", updates['username'])
        
        # Check for phone uniqueness if being updated
        if 'phone' in updates and updates['phone'] != user.phone:
            if updates['phone']:
                existing = self.get_by_phone(updates['phone'], include_inactive=True)
                if existing and existing.id != user_id:
                    raise DuplicateEntityException("User", "phone", updates['phone'])
        
        # Set audit context
        self.set_audit_context(
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.USER,
            resource_id=user_id,
            severity=AuditSeverity.INFO
        )
        
        # Track changes for audit
        changes = {}
        for key, value in updates.items():
            if hasattr(user, key) and getattr(user, key) != value:
                changes[key] = {"old": getattr(user, key), "new": value}
        
        # Update user
        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user = self.update_entity(user)
        
        # Create audit log
        if changes:
            self._create_audit_log(
                user_id=user_id,
                action=AuditAction.UPDATE,
                details={"changes": changes}
            )
        
        logger.info(f"Updated user {user_id}")
        return user
    
    def delete_user(self, user_id: int, hard_delete: bool = False) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: User ID
            hard_delete: If True, permanently delete; if False, soft delete
            
        Returns:
            True if deleted
            
        Raises:
            UserNotFoundException: If user not found
        """
        user = self.get_or_fail(user_id)
        
        if hard_delete:
            # Permanently delete
            result = self.delete(user_id)
            logger.info(f"Permanently deleted user {user_id}")
        else:
            # Soft delete
            result = self.soft_delete(user_id)
            logger.info(f"Soft deleted user {user_id}")
        
        if result:
            self._create_audit_log(
                user_id=user_id,
                action=AuditAction.DELETE if hard_delete else AuditAction.ARCHIVE,
                details={"hard_delete": hard_delete}
            )
        
        return bool(result)
    
    def update_user_status(
        self,
        user_id: int,
        status: UserStatus,
        reason: Optional[str] = None
    ) -> User:
        """
        Update user status.
        
        Args:
            user_id: User ID
            status: New status
            reason: Optional reason for status change
            
        Returns:
            Updated user
        """
        user = self.get_or_fail(user_id)
        
        old_status = user.status
        user.status = status
        
        # If suspending or locking, record reason
        if status in [UserStatus.SUSPENDED, UserStatus.LOCKED] and reason:
            if not hasattr(user, 'metadata'):
                user.metadata = {}
            user.metadata['status_reason'] = reason
            user.metadata['status_changed_at'] = datetime.utcnow().isoformat()
        
        user = self.update_entity(user)
        
        # Create audit log
        self._create_audit_log(
            user_id=user_id,
            action=AuditAction.UPDATE,
            details={
                "status_change": {
                    "from": old_status.value,
                    "to": status.value,
                    "reason": reason
                }
            }
        )
        
        logger.info(f"Updated user {user_id} status from {old_status} to {status}")
        return user
    
    def update_user_role(
        self,
        user_id: int,
        role: UserRole,
        assigned_by: Optional[int] = None
    ) -> User:
        """
        Update user role.
        
        Args:
            user_id: User ID
            role: New role
            assigned_by: ID of user making the assignment
            
        Returns:
            Updated user
        """
        user = self.get_or_fail(user_id)
        
        old_roles = [ra.role.name for ra in user.role_assignments]
        self._assign_role(user, role, assigned_by)
        
        user = self.refresh(user)
        
        # Create audit log
        self._create_audit_log(
            user_id=user_id,
            action=AuditAction.ROLE_ASSIGNED,
            details={
                "old_roles": old_roles,
                "new_role": role.value,
                "assigned_by": assigned_by
            }
        )
        
        logger.info(f"Updated user {user_id} role to {role}")
        return user
    
    # ========================================================================
    # Authentication Methods
    # ========================================================================
    
    def authenticate(
        self,
        identifier: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[User, UserSession]:
        """
        Authenticate a user with password.
        
        Args:
            identifier: Email or username
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (user, session)
            
        Raises:
            UserNotFoundException: If user not found
            AccountLockedException: If account is locked
            AccountSuspendedException: If account is suspended
            UserAuthenticationException: If authentication fails
            PasswordExpiredException: If password has expired
        """
        # Find user by email or username
        user = self.get_by_email(identifier) or self.get_by_username(identifier)
        
        if not user:
            self._log_failed_attempt(None, identifier, ip_address, user_agent)
            raise UserAuthenticationException("Invalid credentials", identifier)
        
        # Check account status
        self._check_account_status(user)
        
        # Check if account is locked
        if user.is_locked():
            raise AccountLockedException(user.id, user.locked_until)
        
        # Verify password
        if not self._verify_password(password, user.password_hash):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            user.last_failed_login = datetime.utcnow()
            
            # Lock account if too many failures
            if user.failed_login_attempts >= self.max_login_attempts:
                user.locked_until = datetime.utcnow() + timedelta(minutes=self.lockout_duration_minutes)
                user.status = UserStatus.LOCKED
                
                self.update_entity(user)
                
                self._create_audit_log(
                    user_id=user.id,
                    action=AuditAction.LOCK,
                    details={
                        "reason": "max_login_attempts",
                        "attempts": user.failed_login_attempts
                    },
                    severity=AuditSeverity.WARNING
                )
                
                raise AccountLockedException(user.id, user.locked_until)
            
            self.update_entity(user)
            
            self._log_failed_attempt(user.id, identifier, ip_address, user_agent)
            raise UserAuthenticationException("Invalid credentials", identifier)
        
        # Check password expiry
        if user.password_changed_at:
            password_age = datetime.utcnow() - user.password_changed_at
            if password_age.days > self.password_expiry_days:
                raise PasswordExpiredException(user.id)
        
        # Successful authentication
        user.failed_login_attempts = 0
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        user.locked_until = None
        
        # Create session
        session = self._create_session(user, ip_address, user_agent)
        
        user = self.update_entity(user)
        
        # Create audit log
        self._create_audit_log(
            user_id=user.id,
            action=AuditAction.LOGIN,
            details={"ip_address": ip_address, "user_agent": user_agent},
            severity=AuditSeverity.INFO
        )
        
        logger.info(f"User {user.id} authenticated successfully")
        return user, session
    
    def authenticate_with_mfa(
        self,
        user_id: int,
        session_id: str,
        mfa_code: str,
        method: MFAMethod
    ) -> Tuple[User, UserSession]:
        """
        Complete MFA authentication.
        
        Args:
            user_id: User ID
            session_id: Session ID from initial authentication
            mfa_code: MFA code
            method: MFA method
            
        Returns:
            Tuple of (user, session)
            
        Raises:
            UserNotFoundException: If user not found
            InvalidMFACodeException: If MFA code is invalid
        """
        user = self.get_or_fail(user_id)
        
        # Get session
        session = (
            self.session.query(UserSession)
            .filter(
                UserSession.session_id == session_id,
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
            .first()
        )
        
        if not session:
            raise UserAuthenticationException("Invalid session")
        
        # Get MFA setting
        mfa_setting = (
            self.session.query(MFASetting)
            .filter(
                MFASetting.user_id == user_id,
                MFASetting.method == method,
                MFASetting.is_enabled == True
            )
            .first()
        )
        
        if not mfa_setting:
            raise UserAuthenticationException("MFA not configured")
        
        # Verify MFA code
        if not self._verify_mfa_code(mfa_code, mfa_setting):
            # Log failed attempt
            self._create_audit_log(
                user_id=user_id,
                action=AuditAction.LOGIN_FAILED,
                details={"reason": "invalid_mfa", "method": method.value},
                severity=AuditSeverity.WARNING
            )
            
            raise InvalidMFACodeException(user_id, method)
        
        # Mark session as MFA verified
        session.mfa_verified = True
        session.mfa_method = method
        session.mfa_verified_at = datetime.utcnow()
        
        self.session.flush()
        
        # Create audit log
        self._create_audit_log(
            user_id=user_id,
            action=AuditAction.LOGIN,
            details={"mfa_method": method.value},
            severity=AuditSeverity.INFO
        )
        
        logger.info(f"User {user_id} completed MFA authentication")
        return user, session
    
    def logout(self, user_id: int, session_id: str) -> bool:
        """
        Log out a user by ending their session.
        
        Args:
            user_id: User ID
            session_id: Session ID
            
        Returns:
            True if logged out successfully
        """
        session = (
            self.session.query(UserSession)
            .filter(
                UserSession.session_id == session_id,
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
            .first()
        )
        
        if session:
            session.is_active = False
            session.logged_out_at = datetime.utcnow()
            self.session.flush()
            
            self._create_audit_log(
                user_id=user_id,
                action=AuditAction.LOGOUT,
                details={"session_id": session_id}
            )
            
            logger.info(f"User {user_id} logged out")
            return True
        
        return False
    
    def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> User:
        """
        Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Returns:
            Updated user
            
        Raises:
            UserNotFoundException: If user not found
            UserAuthenticationException: If current password is incorrect
            ValidationException: If new password doesn't meet requirements
        """
        user = self.get_or_fail(user_id)
        
        # Verify current password
        if not self._verify_password(current_password, user.password_hash):
            raise UserAuthenticationException("Current password is incorrect")
        
        # Validate new password
        self._validate_password_strength(new_password)
        
        # Update password
        user.password_hash = self._hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        user.require_password_change = False
        
        # Invalidate all other sessions
        self._invalidate_other_sessions(user_id, current_session_id=None)
        
        user = self.update_entity(user)
        
        # Create audit log
        self._create_audit_log(
            user_id=user_id,
            action=AuditAction.PASSWORD_CHANGE,
            severity=AuditSeverity.INFO
        )
        
        logger.info(f"Password changed for user {user_id}")
        return user
    
    def reset_password(
        self,
        token: str,
        new_password: str
    ) -> User:
        """
        Reset password using a reset token.
        
        Args:
            token: Password reset token
            new_password: New password
            
        Returns:
            Updated user
            
        Raises:
            RepositoryException: If token is invalid or expired
            ValidationException: If new password doesn't meet requirements
        """
        # Find valid token
        reset_token = (
            self.session.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token == token,
                PasswordResetToken.used == False,
                PasswordResetToken.expires_at > datetime.utcnow()
            )
            .first()
        )
        
        if not reset_token:
            raise RepositoryException("Invalid or expired password reset token")
        
        # Validate new password
        self._validate_password_strength(new_password)
        
        # Update password
        user = reset_token.user
        user.password_hash = self._hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        user.require_password_change = False
        
        # Mark token as used
        reset_token.used = True
        reset_token.used_at = datetime.utcnow()
        
        # Invalidate all sessions
        self._invalidate_all_sessions(user.id)
        
        user = self.update_entity(user)
        
        # Create audit log
        self._create_audit_log(
            user_id=user.id,
            action=AuditAction.PASSWORD_RESET,
            severity=AuditSeverity.INFO
        )
        
        logger.info(f"Password reset for user {user.id}")
        return user
    
    # ========================================================================
    # Session Management
    # ========================================================================
    
    def get_active_sessions(self, user_id: int) -> List[UserSession]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of active sessions
        """
        return (
            self.session.query(UserSession)
            .filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            )
            .order_by(desc(UserSession.last_activity))
            .all()
        )
    
    def validate_session(self, session_id: str) -> Optional[User]:
        """
        Validate a session and return the associated user.
        
        Args:
            session_id: Session ID
            
        Returns:
            User if session is valid, None otherwise
        """
        session = (
            self.session.query(UserSession)
            .filter(
                UserSession.session_id == session_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            )
            .first()
        )
        
        if session:
            # Update last activity
            session.last_activity = datetime.utcnow()
            self.session.flush()
            
            return session.user
        
        return None
    
    def terminate_session(self, user_id: int, session_id: str) -> bool:
        """
        Terminate a specific session.
        
        Args:
            user_id: User ID
            session_id: Session ID
            
        Returns:
            True if terminated
        """
        session = (
            self.session.query(UserSession)
            .filter(
                UserSession.session_id == session_id,
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
            .first()
        )
        
        if session:
            session.is_active = False
            session.terminated_at = datetime.utcnow()
            self.session.flush()
            
            self._create_audit_log(
                user_id=user_id,
                action=AuditAction.LOGOUT,
                details={"session_id": session_id, "reason": "terminated"}
            )
            
            return True
        
        return False
    
    def terminate_all_sessions(self, user_id: int, except_session_id: Optional[str] = None) -> int:
        """
        Terminate all sessions for a user.
        
        Args:
            user_id: User ID
            except_session_id: Optional session ID to keep active
            
        Returns:
            Number of sessions terminated
        """
        query = self.session.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        )
        
        if except_session_id:
            query = query.filter(UserSession.session_id != except_session_id)
        
        sessions = query.all()
        
        for session in sessions:
            session.is_active = False
            session.terminated_at = datetime.utcnow()
        
        self.session.flush()
        
        if sessions:
            self._create_audit_log(
                user_id=user_id,
                action=AuditAction.LOGOUT,
                details={"reason": "all_sessions_terminated", "count": len(sessions)}
            )
        
        return len(sessions)
    
    # ========================================================================
    # MFA Management
    # ========================================================================
    
    def enable_mfa(
        self,
        user_id: int,
        method: MFAMethod,
        secret: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> MFASetting:
        """
        Enable MFA for a user.
        
        Args:
            user_id: User ID
            method: MFA method
            secret: Secret for TOTP (if applicable)
            phone_number: Phone number for SMS (if applicable)
            
        Returns:
            MFA setting
        """
        user = self.get_or_fail(user_id)
        
        # Check if already enabled
        existing = (
            self.session.query(MFASetting)
            .filter(
                MFASetting.user_id == user_id,
                MFASetting.method == method
            )
            .first()
        )
        
        if existing:
            existing.is_enabled = True
            existing.secret = secret
            existing.phone_number = phone_number
            existing.enabled_at = datetime.utcnow()
            mfa_setting = existing
        else:
            mfa_setting = MFASetting(
                user_id=user_id,
                method=method,
                secret=secret,
                phone_number=phone_number,
                is_enabled=True,
                enabled_at=datetime.utcnow()
            )
            self.session.add(mfa_setting)
        
        user.mfa_enabled = True
        
        self.session.flush()
        
        self._create_audit_log(
            user_id=user_id,
            action=AuditAction.UPDATE,
            details={"mfa_enabled": True, "method": method.value}
        )
        
        logger.info(f"MFA {method.value} enabled for user {user_id}")
        return mfa_setting
    
    def disable_mfa(self, user_id: int, method: MFAMethod) -> bool:
        """
        Disable MFA for a user.
        
        Args:
            user_id: User ID
            method: MFA method
            
        Returns:
            True if disabled
        """
        user = self.get_or_fail(user_id)
        
        mfa_setting = (
            self.session.query(MFASetting)
            .filter(
                MFASetting.user_id == user_id,
                MFASetting.method == method,
                MFASetting.is_enabled == True
            )
            .first()
        )
        
        if mfa_setting:
            mfa_setting.is_enabled = False
            mfa_setting.disabled_at = datetime.utcnow()
            
            # Check if any MFA methods are still enabled
            any_enabled = (
                self.session.query(MFASetting)
                .filter(
                    MFASetting.user_id == user_id,
                    MFASetting.is_enabled == True
                )
                .first()
            )
            
            user.mfa_enabled = any_enabled is not None
            
            self.session.flush()
            
            self._create_audit_log(
                user_id=user_id,
                action=AuditAction.UPDATE,
                details={"mfa_disabled": True, "method": method.value}
            )
            
            logger.info(f"MFA {method.value} disabled for user {user_id}")
            return True
        
        return False
    
    def get_mfa_settings(self, user_id: int) -> List[MFASetting]:
        """
        Get MFA settings for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of MFA settings
        """
        return (
            self.session.query(MFASetting)
            .filter(MFASetting.user_id == user_id)
            .all()
        )
    
    # ========================================================================
    # Token Management
    # ========================================================================
    
    def create_password_reset_token(self, email: str) -> Optional[PasswordResetToken]:
        """
        Create a password reset token for a user.
        
        Args:
            email: User's email address
            
        Returns:
            Password reset token if user exists, None otherwise
        """
        user = self.get_by_email(email)
        if not user:
            return None
        
        # Invalidate any existing unused tokens
        self.session.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > datetime.utcnow()
        ).update({"used": True, "used_at": datetime.utcnow()})
        
        # Create new token
        token = PasswordResetToken(
            user_id=user.id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            created_at=datetime.utcnow()
        )
        
        self.session.add(token)
        self.session.flush()
        
        logger.info(f"Password reset token created for user {user.id}")
        return token
    
    def create_email_verification_token(self, user_id: int) -> EmailVerificationToken:
        """
        Create an email verification token for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Email verification token
        """
        user = self.get_or_fail(user_id)
        
        # Invalidate any existing tokens
        self.session.query(EmailVerificationToken).filter(
            EmailVerificationToken.user_id == user_id,
            EmailVerificationToken.used == False
        ).update({"used": True, "used_at": datetime.utcnow()})
        
        # Create new token
        token = EmailVerificationToken(
            user_id=user_id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(days=7),
            created_at=datetime.utcnow()
        )
        
        self.session.add(token)
        self.session.flush()
        
        logger.info(f"Email verification token created for user {user_id}")
        return token
    
    def verify_email(self, token: str) -> Optional[User]:
        """
        Verify a user's email using a token.
        
        Args:
            token: Verification token
            
        Returns:
            Verified user if successful, None otherwise
        """
        verification = (
            self.session.query(EmailVerificationToken)
            .filter(
                EmailVerificationToken.token == token,
                EmailVerificationToken.used == False,
                EmailVerificationToken.expires_at > datetime.utcnow()
            )
            .first()
        )
        
        if verification:
            user = verification.user
            user.email_verified_at = datetime.utcnow()
            
            # If user was pending, activate them
            if user.status == UserStatus.PENDING:
                user.status = UserStatus.ACTIVE
            
            verification.used = True
            verification.used_at = datetime.utcnow()
            
            self.session.flush()
            
            self._create_audit_log(
                user_id=user.id,
                action=AuditAction.VERIFY,
                details={"type": "email"}
            )
            
            logger.info(f"Email verified for user {user.id}")
            return user
        
        return None
    
    # ========================================================================
    # API Key Management
    # ========================================================================
    
    def create_api_key(
        self,
        user_id: int,
        name: str,
        expires_at: Optional[datetime] = None,
        permissions: Optional[List[str]] = None
    ) -> APIKey:
        """
        Create an API key for a user.
        
        Args:
            user_id: User ID
            name: Key name
            expires_at: Optional expiration date
            permissions: Optional list of permissions
            
        Returns:
            Created API key
        """
        user = self.get_or_fail(user_id)
        
        # Generate key and hash
        key = f"pk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_preview=key[:8] + "...",
            expires_at=expires_at,
            permissions=permissions or [],
            created_at=datetime.utcnow()
        )
        
        self.session.add(api_key)
        self.session.flush()
        
        # Store the plain key to return (won't be stored in DB)
        api_key.plain_key = key
        
        self._create_audit_log(
            user_id=user_id,
            action=AuditAction.CREATE,
            details={"api_key_name": name}
        )
        
        logger.info(f"API key created for user {user_id}")
        return api_key
    
    def validate_api_key(self, key: str) -> Optional[User]:
        """
        Validate an API key and return the associated user.
        
        Args:
            key: API key
            
        Returns:
            User if key is valid, None otherwise
        """
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        api_key = (
            self.session.query(APIKey)
            .filter(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,
                or_(
                    APIKey.expires_at.is_(None),
                    APIKey.expires_at > datetime.utcnow()
                )
            )
            .first()
        )
        
        if api_key:
            # Update last used
            api_key.last_used_at = datetime.utcnow()
            self.session.flush()
            
            return api_key.user
        
        return None
    
    def revoke_api_key(self, user_id: int, key_id: int) -> bool:
        """
        Revoke an API key.
        
        Args:
            user_id: User ID
            key_id: API key ID
            
        Returns:
            True if revoked
        """
        api_key = (
            self.session.query(APIKey)
            .filter(
                APIKey.id == key_id,
                APIKey.user_id == user_id,
                APIKey.is_active == True
            )
            .first()
        )
        
        if api_key:
            api_key.is_active = False
            api_key.revoked_at = datetime.utcnow()
            self.session.flush()
            
            self._create_audit_log(
                user_id=user_id,
                action=AuditAction.UPDATE,
                details={"api_key_revoked": api_key.name}
            )
            
            logger.info(f"API key {key_id} revoked for user {user_id}")
            return True
        
        return False
    
    # ========================================================================
    # User Profile Methods
    # ========================================================================
    
    def update_profile(
        self,
        user_id: int,
        **profile_data
    ) -> UserProfile:
        """
        Update user profile.
        
        Args:
            user_id: User ID
            **profile_data: Profile fields to update
            
        Returns:
            Updated profile
        """
        user = self.get_or_fail(user_id)
        
        if not user.profile:
            user.profile = UserProfile(user_id=user_id)
        
        # Track changes
        changes = {}
        for key, value in profile_data.items():
            if hasattr(user.profile, key) and getattr(user.profile, key) != value:
                changes[key] = {"old": getattr(user.profile, key), "new": value}
                setattr(user.profile, key, value)
        
        user.profile.updated_at = datetime.utcnow()
        
        self.session.flush()
        
        if changes:
            self._create_audit_log(
                user_id=user_id,
                action=AuditAction.UPDATE,
                details={"profile_changes": changes}
            )
        
        logger.info(f"Profile updated for user {user_id}")
        return user.profile
    
    def update_preferences(
        self,
        user_id: int,
        **preferences
    ) -> UserPreference:
        """
        Update user preferences.
        
        Args:
            user_id: User ID
            **preferences: Preference fields to update
            
        Returns:
            Updated preferences
        """
        user = self.get_or_fail(user_id)
        
        if not user.preferences:
            user.preferences = UserPreference(user_id=user_id)
        
        for key, value in preferences.items():
            if hasattr(user.preferences, key):
                setattr(user.preferences, key, value)
        
        user.preferences.updated_at = datetime.utcnow()
        
        self.session.flush()
        
        logger.info(f"Preferences updated for user {user_id}")
        return user.preferences
    
    # ========================================================================
    # Device Management
    # ========================================================================
    
    def register_device(
        self,
        user_id: int,
        device_type: str,
        device_token: str,
        device_name: Optional[str] = None,
        device_model: Optional[str] = None,
        os_version: Optional[str] = None,
        app_version: Optional[str] = None
    ) -> UserDevice:
        """
        Register a user device for push notifications.
        
        Args:
            user_id: User ID
            device_type: Type of device (ios, android, web)
            device_token: Device token for push notifications
            device_name: Optional device name
            device_model: Optional device model
            os_version: Optional OS version
            app_version: Optional app version
            
        Returns:
            Registered device
        """
        # Check if device already exists
        device = (
            self.session.query(UserDevice)
            .filter(
                UserDevice.user_id == user_id,
                UserDevice.device_token == device_token
            )
            .first()
        )
        
        if device:
            # Update existing device
            device.device_type = device_type
            device.device_name = device_name
            device.device_model = device_model
            device.os_version = os_version
            device.app_version = app_version
            device.last_active_at = datetime.utcnow()
            device.is_active = True
        else:
            # Create new device
            device = UserDevice(
                user_id=user_id,
                device_type=device_type,
                device_token=device_token,
                device_name=device_name,
                device_model=device_model,
                os_version=os_version,
                app_version=app_version,
                last_active_at=datetime.utcnow(),
                is_active=True
            )
            self.session.add(device)
        
        self.session.flush()
        
        logger.info(f"Device registered for user {user_id}")
        return device
    
    def unregister_device(self, user_id: int, device_token: str) -> bool:
        """
        Unregister a user device.
        
        Args:
            user_id: User ID
            device_token: Device token
            
        Returns:
            True if unregistered
        """
        device = (
            self.session.query(UserDevice)
            .filter(
                UserDevice.user_id == user_id,
                UserDevice.device_token == device_token,
                UserDevice.is_active == True
            )
            .first()
        )
        
        if device:
            device.is_active = False
            device.unregistered_at = datetime.utcnow()
            self.session.flush()
            
            logger.info(f"Device unregistered for user {user_id}")
            return True
        
        return False
    
    def get_user_devices(self, user_id: int, active_only: bool = True) -> List[UserDevice]:
        """
        Get devices for a user.
        
        Args:
            user_id: User ID
            active_only: Whether to return only active devices
            
        Returns:
            List of devices
        """
        query = self.session.query(UserDevice).filter(UserDevice.user_id == user_id)
        
        if active_only:
            query = query.filter(UserDevice.is_active == True)
        
        return query.all()
    
    # ========================================================================
    # Audit Methods
    # ========================================================================
    
    def get_user_audit_logs(
        self,
        user_id: int,
        actions: Optional[List[AuditAction]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[UserAuditLog]:
        """
        Get audit logs for a user.
        
        Args:
            user_id: User ID
            actions: Optional list of actions to filter by
            from_date: Optional start date
            to_date: Optional end date
            limit: Maximum number of logs to return
            
        Returns:
            List of audit logs
        """
        query = self.session.query(UserAuditLog).filter(
            UserAuditLog.user_id == user_id
        )
        
        if actions:
            query = query.filter(UserAuditLog.action.in_(actions))
        
        if from_date:
            query = query.filter(UserAuditLog.created_at >= from_date)
        
        if to_date:
            query = query.filter(UserAuditLog.created_at <= to_date)
        
        return query.order_by(desc(UserAuditLog.created_at)).limit(limit).all()
    
    # ========================================================================
    # Statistics Methods
    # ========================================================================
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get user statistics.
        
        Returns:
            Dictionary with user statistics
        """
        total_users = self.session.query(func.count(User.id)).scalar() or 0
        
        status_counts = {}
        for status in UserStatus:
            count = (
                self.session.query(func.count(User.id))
                .filter(User.status == status)
                .scalar() or 0
            )
            status_counts[status.value] = count
        
        role_counts = {}
        for role in UserRole:
            count = (
                self.session.query(func.count(User.id))
                .join(RoleAssignment)
                .join(Role)
                .filter(Role.name == role.value)
                .scalar() or 0
            )
            role_counts[role.value] = count
        
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        
        new_users_today = (
            self.session.query(func.count(User.id))
            .filter(func.date(User.created_at) == today)
            .scalar() or 0
        )
        
        new_users_yesterday = (
            self.session.query(func.count(User.id))
            .filter(func.date(User.created_at) == yesterday)
            .scalar() or 0
        )
        
        active_today = (
            self.session.query(func.count(User.id))
            .join(UserSession)
            .filter(
                UserSession.is_active == True,
                func.date(UserSession.last_activity) == today
            )
            .distinct()
            .scalar() or 0
        )
        
        mfa_enabled = (
            self.session.query(func.count(User.id))
            .filter(User.mfa_enabled == True)
            .scalar() or 0
        )
        
        email_verified = (
            self.session.query(func.count(User.id))
            .filter(User.email_verified_at.isnot(None))
            .scalar() or 0
        )
        
        return {
            "total_users": total_users,
            "by_status": status_counts,
            "by_role": role_counts,
            "new_users_today": new_users_today,
            "new_users_yesterday": new_users_yesterday,
            "active_today": active_today,
            "mfa_enabled": mfa_enabled,
            "email_verified": email_verified,
            "verification_rate": round(email_verified / total_users * 100, 2) if total_users > 0 else 0
        }
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _check_account_status(self, user: User) -> None:
        """Check if account is in a usable state."""
        if user.status == UserStatus.SUSPENDED:
            reason = user.metadata.get('status_reason') if user.metadata else None
            raise AccountSuspendedException(user.id, reason)
        
        if user.status == UserStatus.DELETED:
            raise UserNotFoundException(user.id)
        
        if user.status == UserStatus.INACTIVE:
            raise AccountSuspendedException(user.id, "Account is inactive")
    
    def _create_session(
        self,
        user: User,
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> UserSession:
        """Create a new user session."""
        session = UserSession(
            user_id=user.id,
            session_id=str(uuid4()),
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True
        )
        
        self.session.add(session)
        self.session.flush()
        
        return session
    
    def _invalidate_other_sessions(self, user_id: int, current_session_id: Optional[str]) -> int:
        """Invalidate all other sessions for a user."""
        query = self.session.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        )
        
        if current_session_id:
            query = query.filter(UserSession.session_id != current_session_id)
        
        sessions = query.all()
        
        for session in sessions:
            session.is_active = False
            session.terminated_at = datetime.utcnow()
        
        self.session.flush()
        return len(sessions)
    
    def _invalidate_all_sessions(self, user_id: int) -> int:
        """Invalidate all sessions for a user."""
        return self._invalidate_other_sessions(user_id, None)
    
    def _assign_role(self, user: User, role: UserRole, assigned_by: Optional[int] = None) -> None:
        """Assign a role to a user."""
        # Get or create role
        db_role = self.session.query(Role).filter(Role.name == role.value).first()
        if not db_role:
            db_role = Role(name=role.value, description=f"{role.value} role")
            self.session.add(db_role)
            self.session.flush()
        
        # Remove existing role assignments
        self.session.query(RoleAssignment).filter(
            RoleAssignment.user_id == user.id
        ).delete()
        
        # Create new assignment
        assignment = RoleAssignment(
            user_id=user.id,
            role_id=db_role.id,
            assigned_by=assigned_by,
            assigned_at=datetime.utcnow()
        )
        
        self.session.add(assignment)
    
    def _create_audit_log(
        self,
        user_id: int,
        action: AuditAction,
        details: Optional[Dict] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Create an audit log entry."""
        log = UserAuditLog(
            user_id=user_id,
            action=action,
            category=AuditCategory.USER_ACTIVITY,
            resource_type=AuditResourceType.USER,
            resource_id=str(user_id),
            details=details or {},
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        
        self.session.add(log)
        self.session.flush()
    
    def _log_failed_attempt(
        self,
        user_id: Optional[int],
        identifier: str,
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> None:
        """Log a failed authentication attempt."""
        self._create_audit_log(
            user_id=user_id if user_id else 0,
            action=AuditAction.LOGIN_FAILED,
            details={"identifier": identifier, "ip_address": ip_address},
            severity=AuditSeverity.WARNING,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def _hash_password(self, password: str) -> str:
        """
        Hash a password using a secure algorithm.
        
        In production, use a proper password hashing library like bcrypt or argon2.
        """
        # Placeholder - replace with actual password hashing
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        In production, use a proper password hashing library.
        """
        # Placeholder - replace with actual password verification
        return self._hash_password(plain_password) == hashed_password
    
    def _validate_password_strength(self, password: str) -> None:
        """
        Validate password strength against policy.
        
        Args:
            password: Password to validate
            
        Raises:
            ValidationException: If password doesn't meet requirements
        """
        errors = []
        
        if len(password) < self.password_min_length:
            errors.append(f"Password must be at least {self.password_min_length} characters")
        
        if self.password_require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.password_require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.password_require_numbers and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        if self.password_require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        if errors:
            raise ValidationException("Password", {"password": errors})
    
    def _verify_mfa_code(self, code: str, mfa_setting: MFASetting) -> bool:
        """
        Verify an MFA code.
        
        In production, implement proper TOTP verification for TOTP method,
        or SMS verification for SMS method.
        """
        # Placeholder - replace with actual MFA verification
        if mfa_setting.method == MFAMethod.TOTP:
            # Implement TOTP verification
            return code == "123456"  # Placeholder
        elif mfa_setting.method == MFAMethod.SMS:
            # Implement SMS code verification
            return code == "123456"  # Placeholder
        elif mfa_setting.method == MFAMethod.EMAIL:
            # Implement email code verification
            return code == "123456"  # Placeholder
        elif mfa_setting.method == MFAMethod.BACKUP_CODE:
            # Implement backup code verification
            return code in (mfa_setting.backup_codes or [])
        
        return False


# ============================================================================
# User Session Repository
# ============================================================================

class UserSessionRepository(BaseRepository[UserSession, int]):
    """Repository for UserSession entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, UserSession)
    
    def get_active_sessions(self, user_id: int) -> List[UserSession]:
        """Get active sessions for a user."""
        return (
            self.session.query(UserSession)
            .filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            )
            .order_by(desc(UserSession.last_activity))
            .all()
        )
    
    def cleanup_expired_sessions(self) -> int:
        """Mark expired sessions as inactive."""
        result = (
            self.session.query(UserSession)
            .filter(
                UserSession.expires_at <= datetime.utcnow(),
                UserSession.is_active == True
            )
            .update({
                "is_active": False,
                "terminated_at": datetime.utcnow()
            })
        )
        
        self.session.flush()
        return result
    
    def cleanup_old_sessions(self, days: int = 30) -> int:
        """Delete old inactive sessions."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = (
            self.session.query(UserSession)
            .filter(
                UserSession.is_active == False,
                UserSession.terminated_at <= cutoff
            )
            .delete()
        )
        
        self.session.flush()
        return result


# ============================================================================
# User Preference Repository
# ============================================================================

class UserPreferenceRepository(BaseRepository[UserPreference, int]):
    """Repository for UserPreference entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, UserPreference)
    
    def get_by_user(self, user_id: int) -> Optional[UserPreference]:
        """Get preferences for a user."""
        return (
            self.session.query(UserPreference)
            .filter(UserPreference.user_id == user_id)
            .first()
        )
    
    def update_notification_preferences(
        self,
        user_id: int,
        preferences: Dict[NotificationType, bool]
    ) -> UserPreference:
        """Update notification preferences."""
        user_prefs = self.get_by_user(user_id)
        
        if not user_prefs:
            user_prefs = UserPreference(user_id=user_id)
            self.session.add(user_prefs)
        
        # Update notification preferences
        if not hasattr(user_prefs, 'notification_preferences'):
            user_prefs.notification_preferences = {}
        
        user_prefs.notification_preferences.update(preferences)
        user_prefs.updated_at = datetime.utcnow()
        
        self.session.flush()
        return user_prefs


# ============================================================================
# User Device Repository
# ============================================================================

class UserDeviceRepository(BaseRepository[UserDevice, int]):
    """Repository for UserDevice entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, UserDevice)
    
    def get_user_devices(self, user_id: int, active_only: bool = True) -> List[UserDevice]:
        """Get devices for a user."""
        query = self.session.query(UserDevice).filter(UserDevice.user_id == user_id)
        
        if active_only:
            query = query.filter(UserDevice.is_active == True)
        
        return query.all()
    
    def get_device_by_token(self, device_token: str) -> Optional[UserDevice]:
        """Get device by token."""
        return (
            self.session.query(UserDevice)
            .filter(UserDevice.device_token == device_token)
            .first()
        )
    
    def get_devices_for_notification(
        self,
        user_ids: List[int],
        device_types: Optional[List[str]] = None
    ) -> List[UserDevice]:
        """Get active devices for push notifications."""
        query = self.session.query(UserDevice).filter(
            UserDevice.user_id.in_(user_ids),
            UserDevice.is_active == True
        )
        
        if device_types:
            query = query.filter(UserDevice.device_type.in_(device_types))
        
        return query.all()
    
    def cleanup_inactive_devices(self, days: int = 90) -> int:
        """Delete devices that have been inactive for a long time."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = (
            self.session.query(UserDevice)
            .filter(
                UserDevice.last_active_at <= cutoff,
                UserDevice.is_active == False
            )
            .delete()
        )
        
        self.session.flush()
        return result


# ============================================================================
# User Audit Log Repository
# ============================================================================

class UserAuditLogRepository(BaseRepository[UserAuditLog, int]):
    """Repository for UserAuditLog entity."""
    
    def __init__(self, session: Session):
        super().__init__(session, UserAuditLog)
    
    def get_user_audit_trail(
        self,
        user_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[UserAuditLog]:
        """Get audit trail for a user."""
        query = self.session.query(UserAuditLog).filter(
            UserAuditLog.user_id == user_id
        )
        
        if from_date:
            query = query.filter(UserAuditLog.created_at >= from_date)
        
        if to_date:
            query = query.filter(UserAuditLog.created_at <= to_date)
        
        return query.order_by(desc(UserAuditLog.created_at)).limit(limit).all()
    
    def get_actions_by_user(
        self,
        user_id: int,
        action: AuditAction,
        limit: int = 50
    ) -> List[UserAuditLog]:
        """Get specific actions by a user."""
        return (
            self.session.query(UserAuditLog)
            .filter(
                UserAuditLog.user_id == user_id,
                UserAuditLog.action == action
            )
            .order_by(desc(UserAuditLog.created_at))
            .limit(limit)
            .all()
        )
    
    def cleanup_old_logs(self, days: int = 365) -> int:
        """Delete audit logs older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = (
            self.session.query(UserAuditLog)
            .filter(UserAuditLog.created_at <= cutoff)
            .delete()
        )
        
        self.session.flush()
        return result


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    # Main Repository
    'UserRepository',
    'UserSessionRepository',
    'UserPreferenceRepository',
    'UserDeviceRepository',
    'UserAuditLogRepository',
    
    # Exceptions
    'UserNotFoundException',
    'UserAuthenticationException',
    'AccountLockedException',
    'AccountSuspendedException',
    'InsufficientPermissionsException',
    'InvalidMFACodeException',
    'PasswordExpiredException',
]