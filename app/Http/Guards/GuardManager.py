from __future__ import annotations

import hashlib
import logging
import secrets
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    Union,
    final,
    Protocol
)

from fastapi import HTTPException, Request, status

from app.Models.User import User
from app.Utils import JWTUtils

if TYPE_CHECKING:
    pass


class GuardInterface(Protocol):
    """Laravel 12 Guard interface."""
    
    async def authenticate(self, request: Request) -> Optional[User]:
        """Authenticate user from request."""
        ...
    
    def supports(self, request: Request) -> bool:
        """Check if this guard can handle the request."""
        ...
    
    def get_name(self) -> str:
        """Get guard name for identification."""
        ...


class AuthenticationGuard(ABC):
    """
    Laravel 12 Enhanced Authentication Guard.
    
    Base class for all authentication guards with comprehensive features
    and strict type safety.
    """
    
    def __init__(self) -> None:
        """Initialize guard with Laravel 12 enhancements."""
        self.logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self._config: Dict[str, Any] = {}
        self._events: List[Callable[..., None]] = []
    
    @abstractmethod
    async def authenticate(self, request: Request) -> Optional[User]:
        """Authenticate user from request."""
        pass
    
    @abstractmethod
    def supports(self, request: Request) -> bool:
        """Check if this guard can handle the request."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get guard name for identification."""
        pass
    
    # Laravel 12 enhanced methods
    def attempt(self, credentials: Dict[str, Any]) -> bool:
        """Attempt to authenticate with credentials (Laravel 12)."""
        return False
    
    def once(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate for a single request (Laravel 12)."""
        return False
    
    def login(self, user: User, remember: bool = False) -> None:
        """Log a user into the application (Laravel 12)."""
        pass
    
    def logout(self) -> None:
        """Log the user out of the application (Laravel 12)."""
        pass
    
    def check(self) -> bool:
        """Determine if the current user is authenticated (Laravel 12)."""
        return False
    
    def guest(self) -> bool:
        """Determine if the current user is a guest (Laravel 12)."""
        return not self.check()
    
    def id(self) -> Optional[int]:
        """Get the ID for the currently authenticated user (Laravel 12)."""
        return None
    
    def validate(self, credentials: Dict[str, Any]) -> bool:
        """Validate a user's credentials (Laravel 12)."""
        return False
    
    def has_user(self) -> bool:
        """Determine if the guard has a user instance (Laravel 12)."""
        return False
    
    def set_user(self, user: User) -> None:
        """Set the current user (Laravel 12)."""
        pass
    
    def forget_user(self) -> None:
        """Forget the current user (Laravel 12)."""
        pass
    
    def get_user(self) -> Optional[User]:
        """Get the currently authenticated user (Laravel 12)."""
        return None
    
    def configure(self, config: Dict[str, Any]) -> 'AuthenticationGuard':
        """Configure the guard (Laravel 12)."""
        self._config.update(config)
        return self
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value (Laravel 12)."""
        return self._config.get(key, default)
    
    def on_authenticated(self, callback: Callable[[User], None]) -> 'AuthenticationGuard':
        """Register authentication event callback (Laravel 12)."""
        self._events.append(callback)
        return self
    
    def fire_authenticated_event(self, user: User) -> None:
        """Fire authenticated event (Laravel 12)."""
        for callback in self._events:
            try:
                callback(user)
            except Exception as e:
                self.logger.warning(f"Authentication event callback failed: {e}")


@final
class JWTGuard(AuthenticationGuard):
    """Laravel 12 JWT-based authentication guard."""
    
    def __init__(self) -> None:
        super().__init__()
        self._current_user: Optional[User] = None
    
    async def authenticate(self, request: Request) -> Optional[User]:
        """Authenticate user using JWT token."""
        if not self.supports(request):
            return None
        
        auth_header = request.headers.get("authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            token_data = JWTUtils.verify_token(token, "access")
            if not token_data:
                return None
            
            user_id = token_data.get("user_id")
            if not user_id:
                return None
            
            # Load user (implement based on your user model)
            user = await self._load_user(user_id)
            
            if user and getattr(user, 'is_active', True):
                self.logger.info(f"JWT authentication successful for user {user_id}")
                return user
            
            return None
            
        except Exception as e:
            self.logger.warning(f"JWT authentication failed: {e}")
            return None
    
    def supports(self, request: Request) -> bool:
        """Check if request has JWT token."""
        auth_header = request.headers.get("authorization", "")
        return auth_header.startswith("Bearer ")
    
    def get_name(self) -> str:
        """Get guard name."""
        return "jwt"
    
    async def _load_user(self, user_id: int) -> Optional[User]:
        """Load user from database - implement based on your user model."""
        # Placeholder implementation
        return None


class SessionGuard(AuthenticationGuard):
    """Session-based authentication guard."""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session_store: Dict[str, Dict[str, Any]] = {}
        self.session_lifetime = timedelta(hours=2)
    
    async def authenticate(self, request: Request) -> Optional[User]:
        """Authenticate user using session."""
        if not self.supports(request):
            return None
        
        session_id = self._get_session_id(request)
        if not session_id:
            return None
        
        session_data = self.session_store.get(session_id)
        if not session_data:
            return None
        
        # Check session expiry
        if datetime.now() > session_data.get("expires_at", datetime.now()):
            self.session_store.pop(session_id, None)
            return None
        
        user_id = session_data.get("user_id")
        if not user_id:
            return None
        
        try:
            user = await self._load_user(user_id)
            if user and getattr(user, 'is_active', True):
                # Update session last accessed
                session_data["last_accessed"] = datetime.now()
                self.logger.info(f"Session authentication successful for user {user_id}")
                return user
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Session authentication failed: {e}")
            return None
    
    def supports(self, request: Request) -> bool:
        """Check if request has session cookie."""
        return self._get_session_id(request) is not None
    
    def get_name(self) -> str:
        """Get guard name."""
        return "session"
    
    def create_session(self, user: User) -> str:
        """Create a new session for user."""
        session_id = secrets.token_urlsafe(32)
        
        self.session_store[session_id] = {
            "user_id": getattr(user, 'id'),
            "created_at": datetime.now(),
            "last_accessed": datetime.now(),
            "expires_at": datetime.now() + self.session_lifetime,
            "user_agent": "unknown",  # Would be set from request
            "ip_address": "unknown"   # Would be set from request
        }
        
        return session_id
    
    def destroy_session(self, session_id: str) -> bool:
        """Destroy a session."""
        return bool(self.session_store.pop(session_id, None))
    
    def _get_session_id(self, request: Request) -> Optional[str]:
        """Get session ID from request cookies."""
        return request.cookies.get("session_id") if hasattr(request, 'cookies') else None
    
    async def _load_user(self, user_id: int) -> Optional[User]:
        """Load user from database - implement based on your user model."""
        # Placeholder implementation
        return None


class APIKeyGuard(AuthenticationGuard):
    """API Key-based authentication guard."""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.rate_limits: Dict[str, List[float]] = {}
    
    async def authenticate(self, request: Request) -> Optional[User]:
        """Authenticate user using API key."""
        if not self.supports(request):
            return None
        
        api_key = self._get_api_key(request)
        if not api_key:
            return None
        
        key_data = self.api_keys.get(api_key)
        if not key_data:
            self.logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
            return None
        
        # Check if API key is active
        if not key_data.get("active", True):
            self.logger.warning(f"Inactive API key attempted: {api_key[:8]}...")
            return None
        
        # Check expiry
        expires_at = key_data.get("expires_at")
        if expires_at and datetime.now() > expires_at:
            self.logger.warning(f"Expired API key attempted: {api_key[:8]}...")
            return None
        
        # Check rate limits
        if not self._check_rate_limit(api_key):
            raise HTTPException(
                status_code=429,  # Too Many Requests
                detail="API key rate limit exceeded"
            )
        
        user_id = key_data.get("user_id")
        if not user_id:
            # API key might not be associated with a user (service-to-service)
            return None
        
        try:
            user = await self._load_user(user_id)
            if user and getattr(user, 'is_active', True):
                # Update last used
                key_data["last_used"] = datetime.now()
                key_data["usage_count"] = key_data.get("usage_count", 0) + 1
                
                self.logger.info(f"API key authentication successful for user {user_id}")
                return user
            
            return None
            
        except Exception as e:
            self.logger.warning(f"API key authentication failed: {e}")
            return None
    
    def supports(self, request: Request) -> bool:
        """Check if request has API key."""
        return self._get_api_key(request) is not None
    
    def get_name(self) -> str:
        """Get guard name."""
        return "api_key"
    
    def create_api_key(
        self, 
        user_id: Optional[int] = None,
        name: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        scopes: Optional[List[str]] = None
    ) -> str:
        """Create a new API key."""
        api_key = f"sk-{secrets.token_urlsafe(32)}"
        
        self.api_keys[api_key] = {
            "user_id": user_id,
            "name": name or f"API Key {datetime.now().strftime('%Y-%m-%d')}",
            "created_at": datetime.now(),
            "expires_at": expires_at,
            "last_used": None,
            "usage_count": 0,
            "active": True,
            "scopes": scopes or [],
            "rate_limit": 1000  # requests per hour
        }
        
        return api_key
    
    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key."""
        if api_key in self.api_keys:
            self.api_keys[api_key]["active"] = False
            return True
        return False
    
    def _get_api_key(self, request: Request) -> Optional[str]:
        """Get API key from request headers."""
        # Check Authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer ") and auth_header[7:].startswith("sk-"):
            return auth_header[7:]
        
        # Check X-API-Key header
        api_key = request.headers.get("x-api-key")
        if api_key and api_key.startswith("sk-"):
            return api_key
        
        return None
    
    def _check_rate_limit(self, api_key: str) -> bool:
        """Check rate limit for API key."""
        key_data = self.api_keys.get(api_key, {})
        rate_limit = key_data.get("rate_limit", 1000)  # per hour
        
        now = time.time()
        hour_ago = now - 3600
        
        # Initialize rate limit tracking
        if api_key not in self.rate_limits:
            self.rate_limits[api_key] = []
        
        # Remove old requests
        self.rate_limits[api_key] = [
            timestamp for timestamp in self.rate_limits[api_key]
            if timestamp > hour_ago
        ]
        
        # Check if under limit
        if len(self.rate_limits[api_key]) >= rate_limit:
            return False
        
        # Record this request
        self.rate_limits[api_key].append(now)
        return True
    
    async def _load_user(self, user_id: int) -> Optional[User]:
        """Load user from database - implement based on your user model."""
        # Placeholder implementation
        return None


class BasicAuthGuard(AuthenticationGuard):
    """HTTP Basic Authentication guard."""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.users: Dict[str, Dict[str, Any]] = {}
    
    async def authenticate(self, request: Request) -> Optional[User]:
        """Authenticate user using HTTP Basic Auth."""
        if not self.supports(request):
            return None
        
        credentials = self._parse_basic_auth(request)
        if not credentials:
            return None
        
        username, password = credentials
        
        user_data = self.users.get(username)
        if not user_data:
            self.logger.warning(f"Basic auth failed: user not found {username}")
            return None
        
        # Verify password (in real implementation, use proper password hashing)
        if not self._verify_password(password, user_data["password_hash"]):
            self.logger.warning(f"Basic auth failed: invalid password for {username}")
            return None
        
        try:
            user_id = user_data.get("user_id")
            if user_id:
                user = await self._load_user(user_id)
                if user and getattr(user, 'is_active', True):
                    self.logger.info(f"Basic auth successful for user {username}")
                    return user
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Basic auth failed: {e}")
            return None
    
    def supports(self, request: Request) -> bool:
        """Check if request has basic auth."""
        auth_header = request.headers.get("authorization", "")
        return auth_header.startswith("Basic ")
    
    def get_name(self) -> str:
        """Get guard name."""
        return "basic"
    
    def _parse_basic_auth(self, request: Request) -> Optional[tuple[str, str]]:
        """Parse basic authentication credentials."""
        auth_header = request.headers.get("authorization", "")
        
        if not auth_header.startswith("Basic "):
            return None
        
        try:
            import base64
            encoded_credentials = auth_header[6:]  # Remove "Basic " prefix
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = decoded_credentials.split(':', 1)
            return username, password
        except Exception:
            return None
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        # Placeholder implementation - use proper password hashing in production
        return hashlib.sha256(password.encode()).hexdigest() == password_hash
    
    async def _load_user(self, user_id: int) -> Optional[User]:
        """Load user from database - implement based on your user model."""
        # Placeholder implementation
        return None


class GuardManager:
    """Manages multiple authentication guards."""
    
    def __init__(self) -> None:
        self.guards: List[AuthenticationGuard] = []
        self.default_guard: Optional[str] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Register default guards
        self._register_default_guards()
    
    def _register_default_guards(self) -> None:
        """Register default authentication guards."""
        self.add_guard(JWTGuard())
        self.add_guard(APIKeyGuard())
        self.add_guard(SessionGuard())
        self.add_guard(BasicAuthGuard())
        
        self.default_guard = "jwt"
    
    def add_guard(self, guard: AuthenticationGuard) -> None:
        """Add an authentication guard."""
        self.guards.append(guard)
        self.logger.info(f"Registered authentication guard: {guard.get_name()}")
    
    def get_guard(self, name: str) -> Optional[AuthenticationGuard]:
        """Get guard by name."""
        for guard in self.guards:
            if guard.get_name() == name:
                return guard
        return None
    
    async def authenticate(
        self, 
        request: Request, 
        guard_names: Optional[List[str]] = None
    ) -> Optional[User]:
        """Authenticate using specified guards or all guards."""
        if guard_names:
            # Try specific guards in order
            for guard_name in guard_names:
                guard = self.get_guard(guard_name)
                if guard and guard.supports(request):
                    user = await guard.authenticate(request)
                    if user:
                        return user
        else:
            # Try all guards
            for guard in self.guards:
                if guard.supports(request):
                    user = await guard.authenticate(request)
                    if user:
                        return user
        
        return None
    
    def authenticate_with_guard(self, guard_name: str) -> Callable[[Request], Awaitable[User]]:
        """Create a dependency that authenticates with a specific guard."""
        async def dependency(request: Request) -> User:
            guard = self.get_guard(guard_name)
            if not guard:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Authentication guard '{guard_name}' not found"
                )
            
            user = await guard.authenticate(request)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed"
                )
            
            return user
        
        return dependency
    
    def authenticate_with_any_guard(self, guard_names: List[str]) -> Callable[[Request], Awaitable[User]]:
        """Create a dependency that authenticates with any of the specified guards."""
        async def dependency(request: Request) -> User:
            user = await self.authenticate(request, guard_names)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Authentication failed with guards: {', '.join(guard_names)}"
                )
            
            return user
        
        return dependency
    
    def get_guard_stats(self) -> Dict[str, Any]:
        """Get statistics about registered guards."""
        return {
            "total_guards": len(self.guards),
            "guard_names": [guard.get_name() for guard in self.guards],
            "default_guard": self.default_guard
        }


# Global guard manager instance
guard_manager = GuardManager()

# Convenience functions
def authenticate_jwt() -> Callable[[Request], Awaitable[User]]:
    """Dependency for JWT authentication."""
    return guard_manager.authenticate_with_guard("jwt")

def authenticate_api_key() -> Callable[[Request], Awaitable[User]]:
    """Dependency for API key authentication."""
    return guard_manager.authenticate_with_guard("api_key")

def authenticate_session() -> Callable[[Request], Awaitable[User]]:
    """Dependency for session authentication."""
    return guard_manager.authenticate_with_guard("session")

def authenticate_basic() -> Callable[[Request], Awaitable[User]]:
    """Dependency for basic authentication."""
    return guard_manager.authenticate_with_guard("basic")

def authenticate_any() -> Callable[[Request], Awaitable[User]]:
    """Dependency for authentication with any guard."""
    return guard_manager.authenticate_with_any_guard([
        "jwt", "api_key", "session", "basic"
    ])