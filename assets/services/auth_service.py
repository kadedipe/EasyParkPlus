"""Authentication service for the parking management system.

This module handles all authentication-related operations including user registration,
login, token management, password reset, and OAuth integration.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
import logging
import hashlib
import secrets
import uuid
from enum import Enum

from jose import jwt, JWTError
from passlib.context import CryptContext
from ..models.user import User, UserRole, UserStatus
from ..models.audit_log import AuditLog
from ..exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
    RateLimitError
)
from ..constants.config import Config
from ..constants.error_codes import ErrorCodes
from ..services.notification_service import NotificationService
from ..services.cache_service import CacheService

# Configure logging
logger = logging.getLogger(__name__)

# Try importing OAuth libraries
try:
    from authlib.integrations.starlette_client import OAuth
    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False
    logger.warning("Authlib not available. OAuth authentication will be disabled.")

try:
    import pyotp
    import qrcode
    from io import BytesIO
    import base64
    MFA_AVAILABLE = True
except ImportError:
    MFA_AVAILABLE = False
    logger.warning("PyOTP not available. Multi-factor authentication will be disabled.")


class TokenType(str, Enum):
    """Token types for authentication."""
    ACCESS = "access"
    REFRESH = "refresh"
    EMAIL_VERIFICATION = "email_verification"
    PHONE_VERIFICATION = "phone_verification"
    PASSWORD_RESET = "password_reset"
    API_KEY = "api_key"


class AuthService:
    """Service for authentication and authorization."""
    
    def __init__(
        self,
        db_session,
        cache_client: Optional[CacheService] = None,
        notification_service: Optional[NotificationService] = None,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        oauth_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize authentication service.
        
        Args:
            db_session: Database session
            cache_client: Optional cache service
            notification_service: Optional notification service
            secret_key: JWT secret key
            algorithm: JWT algorithm
            access_token_expire_minutes: Access token expiration in minutes
            refresh_token_expire_days: Refresh token expiration in days
            oauth_config: OAuth configuration
        """
        self.db = db_session
        self.cache = cache_client
        self.notification_service = notification_service
        self.secret_key = secret_key or Config.JWT_SECRET_KEY
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        
        # Password hashing
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Rate limiting
        self._login_attempts = {}
        self._max_login_attempts = 5
        self._lockout_duration = timedelta(minutes=15)
        
        # Initialize OAuth
        self.oauth = None
        if OAUTH_AVAILABLE and oauth_config:
            self._init_oauth(oauth_config)
        
        # Token blacklist (using cache)
        self._token_blacklist_key = "auth:blacklist:"
        
        logger.info("Auth service initialized")
    
    def _init_oauth(self, config: Dict[str, Any]) -> None:
        """Initialize OAuth clients.
        
        Args:
            config: OAuth configuration
        """
        self.oauth = OAuth()
        
        # Register OAuth providers
        if 'google' in config:
            self.oauth.register(
                name='google',
                client_id=config['google']['client_id'],
                client_secret=config['google']['client_secret'],
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_kwargs={'scope': 'openid email profile'}
            )
        
        if 'facebook' in config:
            self.oauth.register(
                name='facebook',
                client_id=config['facebook']['client_id'],
                client_secret=config['facebook']['client_secret'],
                access_token_url='https://graph.facebook.com/oauth/access_token',
                access_token_params=None,
                authorize_url='https://www.facebook.com/dialog/oauth',
                authorize_params=None,
                api_base_url='https://graph.facebook.com/',
                client_kwargs={'scope': 'email'}
            )
        
        if 'apple' in config:
            self.oauth.register(
                name='apple',
                client_id=config['apple']['client_id'],
                client_secret=config['apple']['client_secret'],
                server_metadata_url='https://appleid.apple.com/.well-known/openid-configuration',
                client_kwargs={'scope': 'name email'}
            )
    
    async def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        username: Optional[str] = None,
        phone: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[User, Dict[str, str]]:
        """Register a new user.
        
        Args:
            email: User email
            password: User password
            first_name: User first name
            last_name: User last name
            username: Optional username
            phone: Optional phone number
            metadata: Optional metadata
            
        Returns:
            Tuple of (user, tokens)
            
        Raises:
            ValidationError: If registration data is invalid
        """
        # Check if user exists
        existing = await self._get_user_by_email(email)
        if existing:
            raise ValidationError({"email": "Email already registered"})
        
        if username:
            existing = await self._get_user_by_username(username)
            if existing:
                raise ValidationError({"username": "Username already taken"})
        
        # Validate password strength
        self._validate_password_strength(password)
        
        # Create user
        user = User(
            email=email,
            username=username or email.split('@')[0],
            password_hash=self._hash_password(password),
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
            email_verified=False,
            phone_verified=False,
            metadata=metadata or {}
        )
        
        self.db.add(user)
        await self.db.flush()
        
        # Generate verification token
        verification_token = self._generate_verification_token(user.user_id, TokenType.EMAIL_VERIFICATION)
        
        # Send verification email
        if self.notification_service:
            await self.notification_service.send_account_verification(
                user_id=user.user_id,
                verification_code=verification_token
            )
        
        # Generate tokens
        tokens = await self._generate_tokens(user)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        logger.info(f"User registered: {user.user_id} - {email}")
        return user, tokens
    
    async def login(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[User, Dict[str, str]]:
        """Authenticate a user.
        
        Args:
            username: Username or email
            password: User password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (user, tokens)
            
        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If too many login attempts
        """
        # Check rate limit
        await self._check_login_rate_limit(username, ip_address)
        
        # Get user
        user = await self._get_user_by_login(username)
        if not user:
            self._record_failed_attempt(username, ip_address)
            raise AuthenticationError("Invalid username or password")
        
        # Check if account is locked
        if user.status == UserStatus.LOCKED:
            raise AuthenticationError("Account is locked. Please contact support.")
        
        if user.status == UserStatus.SUSPENDED:
            raise AuthenticationError("Account is suspended. Please contact support.")
        
        if user.status == UserStatus.DELETED:
            raise AuthenticationError("Account not found")
        
        # Verify password
        if not self._verify_password(password, user.password_hash):
            self._record_failed_attempt(username, ip_address)
            
            # Lock account after too many failures
            await self._handle_failed_login(user)
            raise AuthenticationError("Invalid username or password")
        
        # Check if MFA is required
        if user.metadata.get('mfa_enabled'):
            # Return MFA required response
            mfa_token = self._generate_mfa_token(user.user_id)
            return user, {'requires_mfa': True, 'mfa_token': mfa_token}
        
        # Generate tokens
        tokens = await self._generate_tokens(user)
        
        # Update last login
        user.last_login = datetime.utcnow()
        user.metadata['last_login_ip'] = ip_address
        user.metadata['last_login_user_agent'] = user_agent
        
        # Clear failed attempts
        self._clear_failed_attempts(username)
        
        await self.db.commit()
        
        logger.info(f"User logged in: {user.user_id} - {username}")
        return user, tokens
    
    async def login_with_mfa(
        self,
        user_id: int,
        mfa_token: str,
        mfa_code: str
    ) -> Tuple[User, Dict[str, str]]:
        """Complete MFA authentication.
        
        Args:
            user_id: User ID
            mfa_token: MFA token from initial login
            mfa_code: MFA code from authenticator
            
        Returns:
            Tuple of (user, tokens)
            
        Raises:
            AuthenticationError: If MFA verification fails
        """
        # Verify MFA token
        payload = await self._verify_token(mfa_token, TokenType.ACCESS)
        if not payload or payload.get('user_id') != user_id:
            raise AuthenticationError("Invalid MFA token")
        
        # Get user
        user = await self._get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        # Verify MFA code
        if not self._verify_mfa_code(user, mfa_code):
            raise AuthenticationError("Invalid MFA code")
        
        # Generate tokens
        tokens = await self._generate_tokens(user)
        
        logger.info(f"MFA login completed for user: {user_id}")
        return user, tokens
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, str]:
        """Get new access token using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New tokens
            
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        # Check if token is blacklisted
        if await self._is_token_blacklisted(refresh_token):
            raise AuthenticationError("Token has been revoked")
        
        # Verify token
        payload = await self._verify_token(refresh_token, TokenType.REFRESH)
        if not payload:
            raise AuthenticationError("Invalid refresh token")
        
        # Get user
        user = await self._get_user_by_id(payload['user_id'])
        if not user or user.status != UserStatus.ACTIVE:
            raise AuthenticationError("User not found or inactive")
        
        # Generate new tokens
        tokens = await self._generate_tokens(user)
        
        # Blacklist old refresh token
        await self._blacklist_token(refresh_token, payload['exp'])
        
        logger.info(f"Token refreshed for user: {user.user_id}")
        return tokens
    
    async def logout(self, access_token: str, refresh_token: Optional[str] = None) -> None:
        """Logout a user by invalidating tokens.
        
        Args:
            access_token: Access token to invalidate
            refresh_token: Optional refresh token to invalidate
        """
        # Blacklist access token
        payload = await self._verify_token(access_token, TokenType.ACCESS, verify_exp=False)
        if payload:
            await self._blacklist_token(access_token, payload.get('exp'))
        
        # Blacklist refresh token if provided
        if refresh_token:
            payload = await self._verify_token(refresh_token, TokenType.REFRESH, verify_exp=False)
            if payload:
                await self._blacklist_token(refresh_token, payload.get('exp'))
        
        logger.info(f"User logged out")
    
    async def verify_email(self, token: str) -> User:
        """Verify user email using token.
        
        Args:
            token: Email verification token
            
        Returns:
            Verified user
            
        Raises:
            AuthenticationError: If token is invalid
        """
        payload = await self._verify_token(token, TokenType.EMAIL_VERIFICATION)
        if not payload:
            raise AuthenticationError("Invalid or expired verification token")
        
        user = await self._get_user_by_id(payload['user_id'])
        if not user:
            raise AuthenticationError("User not found")
        
        user.email_verified = True
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)
        
        logger.info(f"Email verified for user: {user.user_id}")
        return user
    
    async def verify_phone(self, user_id: int, code: str) -> User:
        """Verify user phone using code.
        
        Args:
            user_id: User ID
            code: Verification code
            
        Returns:
            Verified user
            
        Raises:
            AuthenticationError: If code is invalid
        """
        # Get verification code from cache
        cache_key = f"phone_verification:{user_id}"
        stored_code = await self.cache.get(cache_key) if self.cache else None
        
        if not stored_code or stored_code != code:
            raise AuthenticationError("Invalid verification code")
        
        user = await self._get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        user.phone_verified = True
        user.updated_at = datetime.utcnow()
        
        # Clear verification code
        if self.cache:
            await self.cache.delete(cache_key)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        logger.info(f"Phone verified for user: {user_id}")
        return user
    
    async def request_password_reset(self, email: str) -> None:
        """Request password reset.
        
        Args:
            email: User email
            
        Raises:
            ResourceNotFoundError: If user not found
        """
        user = await self._get_user_by_email(email)
        if not user:
            # Don't reveal that user doesn't exist
            logger.info(f"Password reset requested for non-existent email: {email}")
            return
        
        # Generate reset token
        reset_token = self._generate_verification_token(user.user_id, TokenType.PASSWORD_RESET)
        
        # Send reset email
        if self.notification_service:
            await self.notification_service.send_notification(
                user_id=user.user_id,
                notification_type="password_reset",
                channel="email",
                template="password_reset",
                template_data={
                    'reset_token': reset_token,
                    'expires_in': 24  # hours
                }
            )
        
        logger.info(f"Password reset requested for user: {user.user_id}")
    
    async def reset_password(self, token: str, new_password: str) -> None:
        """Reset password using token.
        
        Args:
            token: Password reset token
            new_password: New password
            
        Raises:
            AuthenticationError: If token is invalid
            ValidationError: If password is weak
        """
        payload = await self._verify_token(token, TokenType.PASSWORD_RESET)
        if not payload:
            raise AuthenticationError("Invalid or expired reset token")
        
        # Validate password strength
        self._validate_password_strength(new_password)
        
        user = await self._get_user_by_id(payload['user_id'])
        if not user:
            raise AuthenticationError("User not found")
        
        # Update password
        user.password_hash = self._hash_password(new_password)
        user.updated_at = datetime.utcnow()
        
        # Invalidate all user sessions
        await self._invalidate_user_sessions(user.user_id)
        
        await self.db.commit()
        
        logger.info(f"Password reset for user: {user.user_id}")
    
    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> None:
        """Change user password.
        
        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password
            
        Raises:
            AuthenticationError: If current password is incorrect
            ValidationError: If new password is weak
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        # Verify current password
        if not self._verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")
        
        # Validate new password strength
        self._validate_password_strength(new_password)
        
        # Update password
        user.password_hash = self._hash_password(new_password)
        user.updated_at = datetime.utcnow()
        
        # Invalidate all user sessions except current
        await self._invalidate_user_sessions(user_id, exclude_current=True)
        
        await self.db.commit()
        
        logger.info(f"Password changed for user: {user_id}")
    
    async def enable_mfa(self, user_id: int) -> Dict[str, Any]:
        """Enable multi-factor authentication for user.
        
        Args:
            user_id: User ID
            
        Returns:
            MFA setup data including secret and QR code
            
        Raises:
            ValidationError: If MFA is already enabled
        """
        if not MFA_AVAILABLE:
            raise ValidationError({"mfa": "Multi-factor authentication is not available"})
        
        user = await self._get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        if user.metadata.get('mfa_enabled'):
            raise ValidationError({"mfa": "MFA is already enabled"})
        
        # Generate MFA secret
        mfa_secret = pyotp.random_base32()
        totp = pyotp.TOTP(mfa_secret)
        
        # Generate QR code
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name="Parking Management System"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code = base64.b64encode(buffer.getvalue()).decode()
        
        # Store secret temporarily (not enabled yet)
        cache_key = f"mfa_setup:{user_id}"
        if self.cache:
            await self.cache.set(cache_key, mfa_secret, ex=300)  # 5 minutes
        
        return {
            'secret': mfa_secret,
            'qr_code': f"data:image/png;base64,{qr_code}",
            'provisioning_uri': provisioning_uri
        }
    
    async def verify_and_enable_mfa(self, user_id: int, code: str) -> None:
        """Verify and enable MFA for user.
        
        Args:
            user_id: User ID
            code: MFA verification code
            
        Raises:
            AuthenticationError: If code is invalid
        """
        if not MFA_AVAILABLE:
            raise ValidationError({"mfa": "Multi-factor authentication is not available"})
        
        user = await self._get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        # Get MFA secret from cache
        cache_key = f"mfa_setup:{user_id}"
        mfa_secret = await self.cache.get(cache_key) if self.cache else None
        
        if not mfa_secret:
            raise AuthenticationError("MFA setup expired. Please try again.")
        
        # Verify code
        totp = pyotp.TOTP(mfa_secret)
        if not totp.verify(code):
            raise AuthenticationError("Invalid verification code")
        
        # Enable MFA
        user.metadata['mfa_enabled'] = True
        user.metadata['mfa_secret'] = mfa_secret
        user.updated_at = datetime.utcnow()
        
        # Clear setup cache
        if self.cache:
            await self.cache.delete(cache_key)
        
        await self.db.commit()
        
        logger.info(f"MFA enabled for user: {user_id}")
    
    async def disable_mfa(self, user_id: int, password: str) -> None:
        """Disable multi-factor authentication.
        
        Args:
            user_id: User ID
            password: Current password for verification
            
        Raises:
            AuthenticationError: If password is incorrect
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        # Verify password
        if not self._verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid password")
        
        # Disable MFA
        user.metadata['mfa_enabled'] = False
        user.metadata.pop('mfa_secret', None)
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(f"MFA disabled for user: {user_id}")
    
    async def verify_token(self, token: str, required_roles: Optional[List[UserRole]] = None) -> Dict[str, Any]:
        """Verify access token and return payload.
        
        Args:
            token: JWT token
            required_roles: Optional list of required roles
            
        Returns:
            Token payload
            
        Raises:
            AuthenticationError: If token is invalid
            AuthorizationError: If user lacks required roles
        """
        # Check if token is blacklisted
        if await self._is_token_blacklisted(token):
            raise AuthenticationError("Token has been revoked")
        
        # Verify token
        payload = await self._verify_token(token, TokenType.ACCESS)
        if not payload:
            raise AuthenticationError("Invalid or expired token")
        
        # Check if user still exists and is active
        user = await self._get_user_by_id(payload['user_id'])
        if not user:
            raise AuthenticationError("User not found")
        
        if user.status != UserStatus.ACTIVE:
            raise AuthenticationError(f"User account is {user.status.value}")
        
        # Check roles if required
        if required_roles:
            user_role = UserRole(user.role) if isinstance(user.role, str) else user.role
            if user_role not in required_roles:
                raise AuthorizationError(
                    f"Required roles: {[r.value for r in required_roles]}"
                )
        
        return payload
    
    async def get_current_user(self, token: str) -> User:
        """Get current user from token.
        
        Args:
            token: Access token
            
        Returns:
            User object
            
        Raises:
            AuthenticationError: If token is invalid
        """
        payload = await self.verify_token(token)
        user = await self._get_user_by_id(payload['user_id'])
        
        if not user:
            raise AuthenticationError("User not found")
        
        return user
    
    async def create_api_key(self, user_id: int, name: str, expires_in_days: Optional[int] = None) -> Dict[str, str]:
        """Create API key for user.
        
        Args:
            user_id: User ID
            name: API key name
            expires_in_days: Expiration in days
            
        Returns:
            API key and metadata
        """
        user = await self._get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        # Generate API key
        api_key = f"pk_{secrets.token_urlsafe(32)}"
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Store in database (you'd have an APIKey model)
        # This is a placeholder - implement actual storage
        key_data = {
            'user_id': user_id,
            'name': name,
            'key_hash': api_key_hash,
            'created_at': datetime.utcnow(),
            'expires_at': expires_at,
            'last_used_at': None
        }
        
        # Return only the key once
        logger.info(f"API key created for user: {user_id}")
        
        return {
            'api_key': api_key,
            'name': name,
            'expires_at': expires_at.isoformat() if expires_at else None
        }
    
    async def validate_api_key(self, api_key: str) -> Optional[User]:
        """Validate API key and return user.
        
        Args:
            api_key: API key to validate
            
        Returns:
            User if valid, None otherwise
        """
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Look up in database (implement actual lookup)
        # This is a placeholder
        key_data = None  # await self.db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
        
        if not key_data:
            return None
        
        # Check expiration
        if key_data.expires_at and key_data.expires_at < datetime.utcnow():
            return None
        
        # Update last used
        key_data.last_used_at = datetime.utcnow()
        await self.db.commit()
        
        # Get user
        return await self._get_user_by_id(key_data.user_id)
    
    async def _generate_tokens(self, user: User) -> Dict[str, str]:
        """Generate access and refresh tokens.
        
        Args:
            user: User object
            
        Returns:
            Dictionary with tokens
        """
        # Generate access token
        access_token = self._create_token(
            user_id=user.user_id,
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(minutes=self.access_token_expire_minutes)
        )
        
        # Generate refresh token
        refresh_token = self._create_token(
            user_id=user.user_id,
            token_type=TokenType.REFRESH,
            expires_delta=timedelta(days=self.refresh_token_expire_days)
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': self.access_token_expire_minutes * 60
        }
    
    def _create_token(
        self,
        user_id: int,
        token_type: TokenType,
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create JWT token.
        
        Args:
            user_id: User ID
            token_type: Token type
            expires_delta: Expiration delta
            additional_claims: Additional claims
            
        Returns:
            JWT token
        """
        now = datetime.utcnow()
        
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=15)
        
        payload = {
            'user_id': user_id,
            'type': token_type.value,
            'iat': now,
            'exp': expire,
            'jti': str(uuid.uuid4())
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _generate_verification_token(self, user_id: int, token_type: TokenType) -> str:
        """Generate verification token.
        
        Args:
            user_id: User ID
            token_type: Token type
            
        Returns:
            Verification token
        """
        return self._create_token(
            user_id=user_id,
            token_type=token_type,
            expires_delta=timedelta(hours=24)
        )
    
    def _generate_mfa_token(self, user_id: int) -> str:
        """Generate MFA token for partial authentication.
        
        Args:
            user_id: User ID
            
        Returns:
            MFA token
        """
        return self._create_token(
            user_id=user_id,
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(minutes=5),
            additional_claims={'mfa_pending': True}
        )
    
    async def _verify_token(self, token: str, expected_type: TokenType, verify_exp: bool = True) -> Optional[Dict[str, Any]]:
        """Verify JWT token.
        
        Args:
            token: JWT token
            expected_type: Expected token type
            verify_exp: Verify expiration
            
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            options = {'verify_exp': verify_exp}
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options=options
            )
            
            if payload.get('type') != expected_type.value:
                logger.warning(f"Token type mismatch: expected {expected_type.value}, got {payload.get('type')}")
                return None
            
            return payload
            
        except JWTError as e:
            logger.debug(f"Token verification failed: {e}")
            return None
    
    async def _blacklist_token(self, token: str, exp: Optional[int] = None) -> None:
        """Add token to blacklist.
        
        Args:
            token: Token to blacklist
            exp: Token expiration timestamp
        """
        if not self.cache:
            return
        
        # Calculate TTL
        if exp:
            ttl = exp - int(datetime.utcnow().timestamp())
            if ttl > 0:
                await self.cache.set(
                    f"{self._token_blacklist_key}{token}",
                    True,
                    ex=ttl
                )
    
    async def _is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted.
        
        Args:
            token: Token to check
            
        Returns:
            True if blacklisted
        """
        if not self.cache:
            return False
        
        return await self.cache.exists(f"{self._token_blacklist_key}{token}")
    
    async def _invalidate_user_sessions(self, user_id: int, exclude_current: bool = False) -> None:
        """Invalidate all sessions for a user.
        
        Args:
            user_id: User ID
            exclude_current: Exclude current session
        """
        # This would typically involve blacklisting all refresh tokens
        # Implementation depends on how you store sessions
        pass
    
    async def _check_login_rate_limit(self, username: str, ip_address: Optional[str]) -> None:
        """Check rate limit for login attempts.
        
        Args:
            username: Username or email
            ip_address: Client IP address
            
        Raises:
            RateLimitError: If rate limit exceeded
        """
        key = f"login_attempts:{username}:{ip_address}" if ip_address else f"login_attempts:{username}"
        
        if self.cache:
            attempts = await self.cache.get(key) or 0
            if attempts >= self._max_login_attempts:
                raise RateLimitError(
                    retry_after=self._lockout_duration.seconds,
                    message="Too many login attempts. Please try again later."
                )
    
    def _record_failed_attempt(self, username: str, ip_address: Optional[str]) -> None:
        """Record failed login attempt.
        
        Args:
            username: Username or email
            ip_address: Client IP address
        """
        key = f"login_attempts:{username}:{ip_address}" if ip_address else f"login_attempts:{username}"
        
        if self.cache:
            attempts = self.cache.get(key) or 0
            self.cache.set(key, attempts + 1, ex=self._lockout_duration)
    
    def _clear_failed_attempts(self, username: str) -> None:
        """Clear failed login attempts.
        
        Args:
            username: Username or email
        """
        if self.cache:
            # Clear both username and username+ip patterns
            # This is a simplified version
            pass
    
    async def _handle_failed_login(self, user: User) -> None:
        """Handle failed login attempt.
        
        Args:
            user: User object
        """
        # Increment failed attempts counter
        failed_attempts = user.metadata.get('failed_login_attempts', 0) + 1
        user.metadata['failed_login_attempts'] = failed_attempts
        user.metadata['last_failed_login'] = datetime.utcnow().isoformat()
        
        # Lock account if too many failures
        if failed_attempts >= self._max_login_attempts:
            user.status = UserStatus.LOCKED
            user.metadata['lock_reason'] = 'Too many failed login attempts'
            logger.warning(f"User account locked due to failed attempts: {user.user_id}")
        
        await self.db.commit()
    
    def _hash_password(self, password: str) -> str:
        """Hash password.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches
        """
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def _validate_password_strength(self, password: str) -> None:
        """Validate password strength.
        
        Args:
            password: Password to validate
            
        Raises:
            ValidationError: If password is weak
        """
        errors = []
        
        if len(password) < Config.PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {Config.PASSWORD_MIN_LENGTH} characters")
        
        if len(password) > Config.PASSWORD_MAX_LENGTH:
            errors.append(f"Password must be at most {Config.PASSWORD_MAX_LENGTH} characters")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one number")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        if errors:
            raise ValidationError({"password": errors})
    
    def _verify_mfa_code(self, user: User, code: str) -> bool:
        """Verify MFA code.
        
        Args:
            user: User object
            code: MFA code
            
        Returns:
            True if code is valid
        """
        if not MFA_AVAILABLE:
            return False
        
        mfa_secret = user.metadata.get('mfa_secret')
        if not mfa_secret:
            return False
        
        totp = pyotp.TOTP(mfa_secret)
        return totp.verify(code)
    
    async def _get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return await self.db.query(User).filter(User.user_id == user_id).first()
    
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.db.query(User).filter(User.email == email).first()
    
    async def _get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return await self.db.query(User).filter(User.username == username).first()
    
    async def _get_user_by_login(self, login: str) -> Optional[User]:
        """Get user by username or email."""
        return await self.db.query(User).filter(
            (User.username == login) | (User.email == login)
        ).first()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on auth service.
        
        Returns:
            Health check results
        """
        return {
            'service': 'auth_service',
            'status': 'healthy',
            'providers': {
                'oauth': OAUTH_AVAILABLE and self.oauth is not None,
                'mfa': MFA_AVAILABLE
            },
            'config': {
                'algorithm': self.algorithm,
                'access_token_expire_minutes': self.access_token_expire_minutes,
                'refresh_token_expire_days': self.refresh_token_expire_days
            }
        }