"""Authentication and authorization configuration."""

from datetime import timedelta
from typing import List, Dict, Any

from . import config


class AuthConfig:
    """Authentication configuration."""
    
    # JWT settings
    JWT_SECRET_KEY: str = config.JWT_SECRET_KEY
    JWT_ALGORITHM: str = config.JWT_ALGORITHM
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = config.JWT_ACCESS_TOKEN_EXPIRES
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = config.JWT_REFRESH_TOKEN_EXPIRES
    
    # Token settings
    TOKEN_TYPE_ACCESS: str = "access"
    TOKEN_TYPE_REFRESH: str = "refresh"
    TOKEN_TYPE_RESET: str = "reset"
    TOKEN_TYPE_VERIFY: str = "verify"
    
    # Password settings
    PASSWORD_MIN_LENGTH: int = config.PASSWORD_MIN_LENGTH
    PASSWORD_MAX_LENGTH: int = config.PASSWORD_MAX_LENGTH
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    BCRYPT_ROUNDS: int = config.BCRYPT_ROUNDS
    
    # Session settings
    SESSION_COOKIE_NAME: str = "session"
    SESSION_COOKIE_SECURE: bool = not config.DEBUG
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_MAX_AGE: int = 60 * 60 * 24 * 7  # 7 days
    
    # OAuth2 settings
    OAUTH2_PROVIDERS: Dict[str, Dict[str, Any]] = {
        "google": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
            "scopes": ["openid", "email", "profile"],
        },
        "facebook": {
            "client_id": config.FACEBOOK_CLIENT_ID,
            "client_secret": config.FACEBOOK_CLIENT_SECRET,
            "authorize_url": "https://www.facebook.com/v12.0/dialog/oauth",
            "token_url": "https://graph.facebook.com/v12.0/oauth/access_token",
            "userinfo_url": "https://graph.facebook.com/me?fields=id,name,email",
            "scopes": ["email", "public_profile"],
        },
    }
    
    # Role-based access control
    ROLES: Dict[str, List[str]] = {
        "customer": [
            "reservation:create",
            "reservation:read:own",
            "reservation:update:own",
            "reservation:cancel:own",
            "vehicle:manage:own",
            "payment:read:own",
        ],
        "vip_customer": [
            "reservation:priority",
            "reservation:discount",
            "spot:vip:access",
        ],
        "attendant": [
            "reservation:checkin",
            "reservation:checkout",
            "spot:status:update",
            "spot:view",
        ],
        "manager": [
            "reservation:read:all",
            "reservation:update:all",
            "reservation:cancel:all",
            "spot:manage",
            "user:read:all",
            "report:generate",
            "audit:view",
        ],
        "admin": [
            "*",  # All permissions
        ],
    }


auth_config = AuthConfig()