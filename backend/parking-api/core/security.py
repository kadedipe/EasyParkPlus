"""
Security module for authentication, encryption, and token management.
"""

import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union, Tuple
from uuid import UUID

import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import os

from .config import settings
from ..utils.logger import logger
from ..services.redis import redis_client

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS
)

# JWT algorithms
JWT_ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# Encryption key for sensitive data
ENCRYPTION_KEY = None
if settings.ENCRYPTION_SECRET_KEY:
    # Derive encryption key from secret
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=settings.ENCRYPTION_SALT.encode() if settings.ENCRYPTION_SALT else b'salt',
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.ENCRYPTION_SECRET_KEY.encode()))
    ENCRYPTION_KEY = Fernet(key)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: The plain text password
        hashed_password: The hashed password
        
    Returns:
        bool: True if password matches, False otherwise
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password
        
    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def create_access_token(
    user_id: Union[str, UUID],
    expires_delta: Optional[timedelta] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: The user ID
        expires_delta: Optional expiration time delta
        additional_data: Additional data to include in token
        
    Returns:
        str: The JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow()
    }
    
    if additional_data:
        to_encode.update(additional_data)
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {str(e)}")
        raise


def create_refresh_token(
    user_id: Union[str, UUID],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: The user ID
        expires_delta: Optional expiration time delta
        
    Returns:
        str: The JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "iat": datetime.utcnow()
    }
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_REFRESH_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating refresh token: {str(e)}")
        raise


def create_email_verification_token(user_id: Union[str, UUID]) -> str:
    """
    Create a token for email verification.
    
    Args:
        user_id: The user ID
        
    Returns:
        str: The verification token
    """
    expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "email_verification",
        "iat": datetime.utcnow()
    }
    
    try:
        return jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )
    except Exception as e:
        logger.error(f"Error creating email verification token: {str(e)}")
        raise


def create_password_reset_token(user_id: Union[str, UUID]) -> str:
    """
    Create a token for password reset.
    
    Args:
        user_id: The user ID
        
    Returns:
        str: The reset token
    """
    expire = datetime.utcnow() + timedelta(hours=1)
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "type": "password_reset",
        "iat": datetime.utcnow()
    }
    
    try:
        return jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )
    except Exception as e:
        logger.error(f"Error creating password reset token: {str(e)}")
        raise


def decode_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token
        token_type: Type of token ("access", "refresh", "email_verification", "password_reset")
        
    Returns:
        Optional[Dict[str, Any]]: The token payload if valid, None otherwise
    """
    try:
        # Choose secret key based on token type
        if token_type == "refresh":
            secret_key = settings.JWT_REFRESH_SECRET_KEY
        else:
            secret_key = settings.JWT_SECRET_KEY
        
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[JWT_ALGORITHM]
        )
        
        # Verify token type
        if payload.get("type") != token_type:
            logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
            return None
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.debug(f"Token expired: {token_type}")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error decoding token: {str(e)}")
        return None


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a token without specifying type (tries all types).
    
    Args:
        token: The JWT token
        
    Returns:
        Optional[Dict[str, Any]]: The token payload if valid, None otherwise
    """
    # Try access token first
    payload = decode_token(token, "access")
    if payload:
        return payload
    
    # Try refresh token
    payload = decode_token(token, "refresh")
    if payload:
        return payload
    
    # Try email verification token
    payload = decode_token(token, "email_verification")
    if payload:
        return payload
    
    # Try password reset token
    payload = decode_token(token, "password_reset")
    if payload:
        return payload
    
    return None


def verify_email_token(token: str) -> Optional[str]:
    """
    Verify an email verification token and return user ID.
    
    Args:
        token: The verification token
        
    Returns:
        Optional[str]: The user ID if valid, None otherwise
    """
    payload = decode_token(token, "email_verification")
    if payload:
        return payload.get("sub")
    return None


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token and return user ID.
    
    Args:
        token: The reset token
        
    Returns:
        Optional[str]: The user ID if valid, None otherwise
    """
    payload = decode_token(token, "password_reset")
    if payload:
        return payload.get("sub")
    return None


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a refresh token.
    
    Args:
        token: The refresh token
        
    Returns:
        Optional[Dict[str, Any]]: The token payload if valid, None otherwise
    """
    return decode_token(token, "refresh")


async def blacklist_token(token: str, expires_in: Optional[int] = None):
    """
    Blacklist a token so it can't be used again.
    
    Args:
        token: The token to blacklist
        expires_in: Time in seconds until token expires (auto-calculated if not provided)
    """
    if not redis_client:
        logger.warning("Redis not available, token blacklisting disabled")
        return
    
    try:
        # Decode token to get expiration
        payload = verify_token(token)
        if payload:
            exp = payload.get("exp")
            if exp:
                # Calculate time until expiration
                now = datetime.utcnow().timestamp()
                expires_in = int(exp - now)
        
        if expires_in and expires_in > 0:
            await redis_client.setex(
                f"blacklist:{token}",
                expires_in,
                "blacklisted"
            )
            logger.debug(f"Token blacklisted for {expires_in} seconds")
    except Exception as e:
        logger.error(f"Error blacklisting token: {str(e)}")


async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token is blacklisted.
    
    Args:
        token: The token to check
        
    Returns:
        bool: True if token is blacklisted, False otherwise
    """
    if not redis_client:
        return False
    
    try:
        result = await redis_client.get(f"blacklist:{token}")
        return result is not None
    except Exception as e:
        logger.error(f"Error checking token blacklist: {str(e)}")
        return False


def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        str: A secure random API key
    """
    return f"pk_{secrets.token_urlsafe(32)}"


def generate_secret_key() -> str:
    """
    Generate a secure secret key.
    
    Returns:
        str: A secure random secret key
    """
    return secrets.token_hex(32)


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.
    
    Args:
        api_key: The API key to hash
        
    Returns:
        str: The hashed API key
    """
    salt = secrets.token_hex(16)
    key_hash = hashlib.pbkdf2_hmac(
        'sha256',
        api_key.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${base64.b64encode(key_hash).decode('utf-8')}"


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.
    
    Args:
        api_key: The API key to verify
        hashed_key: The stored hash
        
    Returns:
        bool: True if key matches, False otherwise
    """
    try:
        salt, key_hash = hashed_key.split('$')
        new_hash = hashlib.pbkdf2_hmac(
            'sha256',
            api_key.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return hmac.compare_digest(
            base64.b64encode(new_hash).decode('utf-8'),
            key_hash
        )
    except Exception as e:
        logger.error(f"Error verifying API key: {str(e)}")
        return False


def encrypt_sensitive_data(data: str) -> str:
    """
    Encrypt sensitive data (e.g., credit card numbers, personal info).
    
    Args:
        data: The data to encrypt
        
    Returns:
        str: The encrypted data as base64 string
    """
    if not ENCRYPTION_KEY:
        raise ValueError("Encryption key not configured")
    
    try:
        encrypted = ENCRYPTION_KEY.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode('utf-8')
    except Exception as e:
        logger.error(f"Encryption error: {str(e)}")
        raise


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    Decrypt sensitive data.
    
    Args:
        encrypted_data: The encrypted data as base64 string
        
    Returns:
        str: The decrypted data
    """
    if not ENCRYPTION_KEY:
        raise ValueError("Encryption key not configured")
    
    try:
        encrypted = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = ENCRYPTION_KEY.decrypt(encrypted)
        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Decryption error: {str(e)}")
        raise


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data (e.g., credit card numbers) for display.
    
    Args:
        data: The data to mask
        visible_chars: Number of characters to leave visible at the end
        
    Returns:
        str: The masked data
    """
    if len(data) <= visible_chars:
        return "*" * len(data)
    
    masked = "*" * (len(data) - visible_chars) + data[-visible_chars:]
    return masked


def generate_secure_random_string(length: int = 32) -> str:
    """
    Generate a cryptographically secure random string.
    
    Args:
        length: Length of the string
        
    Returns:
        str: Random string
    """
    return secrets.token_urlsafe(length)


def generate_otp(length: int = 6) -> str:
    """
    Generate a one-time password (numeric).
    
    Args:
        length: Number of digits
        
    Returns:
        str: OTP code
    """
    return ''.join(str(secrets.randrange(10)) for _ in range(length))


def verify_otp(provided_otp: str, stored_otp: str, max_age_seconds: int = 300) -> bool:
    """
    Verify a one-time password.
    
    Args:
        provided_otp: The OTP provided by user
        stored_otp: The stored OTP (format: "code:timestamp")
        max_age_seconds: Maximum age of OTP in seconds
        
    Returns:
        bool: True if OTP is valid and not expired
    """
    try:
        code, timestamp = stored_otp.split(':')
        otp_time = datetime.fromtimestamp(float(timestamp))
        
        # Check if OTP is expired
        if datetime.utcnow() - otp_time > timedelta(seconds=max_age_seconds):
            return False
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(provided_otp, code)
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        return False


def generate_csrf_token() -> str:
    """
    Generate a CSRF token.
    
    Returns:
        str: CSRF token
    """
    return secrets.token_urlsafe(32)


def generate_session_id() -> str:
    """
    Generate a unique session ID.
    
    Returns:
        str: Session ID
    """
    return f"sess_{secrets.token_urlsafe(24)}"


def sanitize_input(input_str: str) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        input_str: Raw input string
        
    Returns:
        str: Sanitized string
    """
    # Remove any non-printable characters
    sanitized = ''.join(char for char in input_str if char.isprintable())
    
    # Escape any HTML/JavaScript
    sanitized = sanitized.replace('<', '&lt;').replace('>', '&gt;')
    
    return sanitized


def is_password_strong(password: str) -> Tuple[bool, str]:
    """
    Check if password meets strength requirements.
    
    Args:
        password: The password to check
        
    Returns:
        Tuple[bool, str]: (is_strong, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    if not any(c in '!@#$%^&*(),.?":{}|<>' for c in password):
        return False, "Password must contain at least one special character"
    
    # Check for common patterns
    common_patterns = ['123456', 'password', 'qwerty', 'abc123']
    if any(pattern in password.lower() for pattern in common_patterns):
        return False, "Password contains common patterns"
    
    return True, "Password is strong"


def rate_limit_key_for_user(user_id: Union[str, UUID]) -> str:
    """
    Generate a rate limit key for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        str: Rate limit key
    """
    return f"rate_limit:user:{user_id}"


def rate_limit_key_for_ip(ip_address: str) -> str:
    """
    Generate a rate limit key for an IP address.
    
    Args:
        ip_address: The IP address
        
    Returns:
        str: Rate limit key
    """
    return f"rate_limit:ip:{ip_address}"


def rate_limit_key_for_endpoint(endpoint: str, identifier: str) -> str:
    """
    Generate a rate limit key for an endpoint.
    
    Args:
        endpoint: The API endpoint
        identifier: User or IP identifier
        
    Returns:
        str: Rate limit key
    """
    return f"rate_limit:{endpoint}:{identifier}"


class SecurityHeaders:
    """
    Security headers for HTTP responses.
    """
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """
        Get security headers.
        
        Returns:
            Dict[str, str]: Security headers
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache"
        }


# Export commonly used functions
__all__ = [
    # Password handling
    'verify_password',
    'get_password_hash',
    'is_password_strong',
    
    # Token management
    'create_access_token',
    'create_refresh_token',
    'create_email_verification_token',
    'create_password_reset_token',
    'decode_token',
    'verify_token',
    'verify_email_token',
    'verify_password_reset_token',
    'verify_refresh_token',
    'blacklist_token',
    'is_token_blacklisted',
    
    # API keys
    'generate_api_key',
    'generate_secret_key',
    'hash_api_key',
    'verify_api_key',
    
    # Encryption
    'encrypt_sensitive_data',
    'decrypt_sensitive_data',
    'mask_sensitive_data',
    
    # OTP and random strings
    'generate_secure_random_string',
    'generate_otp',
    'verify_otp',
    'generate_csrf_token',
    'generate_session_id',
    
    # Input validation
    'sanitize_input',
    
    # Rate limiting keys
    'rate_limit_key_for_user',
    'rate_limit_key_for_ip',
    'rate_limit_key_for_endpoint',
    
    # Security headers
    'SecurityHeaders'
]