"""User model for the parking management system."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from ..enums import UserRole, UserStatus


class User:
    """User model representing a system user."""
    
    def __init__(
        self,
        user_id: Optional[int] = None,
        email: str = "",
        username: str = "",
        password_hash: str = "",
        first_name: str = "",
        last_name: str = "",
        phone: str = "",
        role: UserRole = UserRole.CUSTOMER,
        status: UserStatus = UserStatus.ACTIVE,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_login: Optional[datetime] = None,
        email_verified: bool = False,
        phone_verified: bool = False,
        profile_picture: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.username = username
        self.password_hash = password_hash
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.role = role
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at
        self.last_login = last_login
        self.email_verified = email_verified
        self.phone_verified = phone_verified
        self.profile_picture = profile_picture
        self.preferences = preferences or {}
        self.metadata = metadata or {}
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role in [UserRole.ADMIN, UserRole.MANAGER]
    
    @property
    def is_vip(self) -> bool:
        """Check if user is VIP."""
        return self.role == UserRole.VIP_CUSTOMER
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role.value if self.role else None,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "email_verified": self.email_verified,
            "phone_verified": self.phone_verified,
            "profile_picture": self.profile_picture,
            "preferences": self.preferences,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user from dictionary."""
        return cls(
            user_id=data.get('user_id'),
            email=data.get('email', ''),
            username=data.get('username', ''),
            password_hash=data.get('password_hash', ''),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            phone=data.get('phone', ''),
            role=UserRole(data['role']) if data.get('role') else None,
            status=UserStatus(data['status']) if data.get('status') else None,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            last_login=datetime.fromisoformat(data['last_login']) if data.get('last_login') else None,
            email_verified=data.get('email_verified', False),
            phone_verified=data.get('phone_verified', False),
            profile_picture=data.get('profile_picture'),
            preferences=data.get('preferences'),
            metadata=data.get('metadata'),
        )