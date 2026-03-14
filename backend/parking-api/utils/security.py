"""
Security utility functions.
"""

import bcrypt
import secrets
import string
import hashlib
import hmac
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
import jwt
import pyotp
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from ..core.config import settings


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def generate_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None
) -> str:
    """
    Generate JWT token.
    
    Args:
        data: Token payload
        expires_delta: Token expiration time
        secret_key: Secret key for signing
        
    Returns:
        str: JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({"exp": expire})
    
    key = secret_key or settings.SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, key, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def verify_token(
    token: str,
    secret_key: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token.
    
    Args:
        token: JWT token
        secret_key: Secret key for verification
        
    Returns:
        Optional[Dict[str, Any]]: Token payload if valid, None otherwise
    """
    try:
        key = secret_key or settings.SECRET_KEY
        payload = jwt.decode(
            token,
            key,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.PyJWTError:
        return None


def generate_otp(secret: Optional[str] = None) -> Dict[str, str]:
    """
    Generate OTP using TOTP.
    
    Args:
        secret: Optional base32 secret
        
    Returns:
        Dict[str, str]: OTP data with secret and URI
    """
    if secret is None:
        secret = pyotp.random_base32()
    
    totp = pyotp.TOTP(secret)
    otp = totp.now()
    
    # Generate provisioning URI for QR code
    uri = totp.provisioning_uri(
        name=settings.PROJECT_NAME,
        issuer_name=settings.PROJECT_NAME
    )
    
    return {
        "secret": secret,
        "otp": otp,
        "uri": uri
    }


def verify_otp(secret: str, otp: str) -> bool:
    """
    Verify OTP.
    
    Args:
        secret: Base32 secret
        otp: OTP to verify
        
    Returns:
        bool: True if OTP is valid
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(otp)


def encrypt_data(data: str, key: Optional[bytes] = None) -> str:
    """
    Encrypt data using Fernet.
    
    Args:
        data: Data to encrypt
        key: Encryption key
        
    Returns:
        str: Encrypted data
    """
    if key is None:
        key = Fernet.generate_key()
    
    f = Fernet(key)
    encrypted = f.encrypt(data.encode('utf-8'))
    
    return base64.urlsafe_b64encode(encrypted).decode('utf-8')


def decrypt_data(encrypted_data: str, key: bytes) -> str:
    """
    Decrypt data using Fernet.
    
    Args:
        encrypted_data: Encrypted data
        key: Decryption key
        
    Returns:
        str: Decrypted data
    """
    f = Fernet(key)
    decoded = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
    decrypted = f.decrypt(decoded)
    
    return decrypted.decode('utf-8')


def generate_api_key() -> str:
    """
    Generate secure API key.
    
    Returns:
        str: API key
    """
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(32))
    
    # Add prefix for identification
    return f"pk_{api_key}"


def mask_sensitive_data(
    data: str,
    visible_chars: int = 4,
    mask_char: str = '*'
) -> str:
    """
    Mask sensitive data (like credit card numbers, emails).
    
    Args:
        data: Data to mask
        visible_chars: Number of characters to keep visible
        mask_char: Character to use for masking
        
    Returns:
        str: Masked data
    """
    if len(data) <= visible_chars:
        return data
    
    masked_part = mask_char * (len(data) - visible_chars)
    visible_part = data[-visible_chars:]
    
    return masked_part + visible_part


def sanitize_input(input_str: str) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        input_str: Input string to sanitize
        
    Returns:
        str: Sanitized string
    """
    # Remove any non-printable characters
    sanitized = ''.join(char for char in input_str if char.isprintable())
    
    # Escape any potentially dangerous characters
    dangerous_chars = {'<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}
    for char, escaped in dangerous_chars.items():
        sanitized = sanitized.replace(char, escaped)
    
    return sanitized


def generate_secure_random_string(length: int = 32) -> str:
    """
    Generate cryptographically secure random string.
    
    Args:
        length: Length of string
        
    Returns:
        str: Random string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def compute_hash(data: Union[str, bytes], algorithm: str = 'sha256') -> str:
    """
    Compute hash of data.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm
        
    Returns:
        str: Hexadecimal hash
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    if algorithm == 'sha256':
        return hashlib.sha256(data).hexdigest()
    elif algorithm == 'sha512':
        return hashlib.sha512(data).hexdigest()
    elif algorithm == 'md5':
        return hashlib.md5(data).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def generate_hmac_signature(
    data: Union[str, bytes],
    secret: str
) -> str:
    """
    Generate HMAC signature.
    
    Args:
        data: Data to sign
        secret: Secret key
        
    Returns:
        str: HMAC signature
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    signature = hmac.new(
        secret.encode('utf-8'),
        data,
        hashlib.sha256
    ).hexdigest()
    
    return signature


def verify_hmac_signature(
    data: Union[str, bytes],
    secret: str,
    signature: str
) -> bool:
    """
    Verify HMAC signature.
    
    Args:
        data: Original data
        secret: Secret key
        signature: Signature to verify
        
    Returns:
        bool: True if signature is valid
    """
    expected = generate_hmac_signature(data, secret)
    return hmac.compare_digest(expected, signature)


def derive_key(
    password: str,
    salt: Optional[bytes] = None,
    length: int = 32
) -> tuple[bytes, bytes]:
    """
    Derive key from password using PBKDF2.
    
    Args:
        password: Password
        salt: Salt (generated if None)
        length: Key length
        
    Returns:
        tuple[bytes, bytes]: (derived_key, salt)
    """
    if salt is None:
        salt = secrets.token_bytes(16)
    
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        iterations=100000,
    )
    
    key = kdf.derive(password.encode('utf-8'))
    return key, salt