"""OAuth2 Middleware - Laravel Passport Style

This middleware provides OAuth2 authentication and scope-based authorization
for FastAPI similar to Laravel Passport middleware.
"""

from __future__ import annotations

from typing import Optional, List, Callable, Any, Union
from typing_extensions import Annotated
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.Models.OAuth2AccessToken import OAuth2AccessToken
from database.migrations.create_users_table import User
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from config.database import get_db_session


# OAuth2 Bearer token scheme
oauth2_scheme = HTTPBearer(auto_error=False)


class OAuth2TokenData:
    """OAuth2 token data container."""
    
    def __init__(
        self,
        access_token: OAuth2AccessToken,
        user: Optional[User] = None,
        scopes: List[str] = None
    ) -> None:
        self.access_token = access_token
        self.user = user
        self.scopes = scopes or []
        self.client = access_token.client
    
    def has_scope(self, scope: str) -> bool:
        """Check if token has specific scope."""
        return scope in self.scopes
    
    def has_any_scope(self, scopes: List[str]) -> bool:
        """Check if token has any of the specified scopes."""
        return any(scope in self.scopes for scope in scopes)
    
    def has_all_scopes(self, scopes: List[str]) -> bool:
        """Check if token has all of the specified scopes."""
        return all(scope in self.scopes for scope in scopes)
    
    def is_personal_access_token(self) -> bool:
        """Check if this is a personal access token."""
        return self.client.is_personal_access_client()
    
    def is_client_credentials_token(self) -> bool:
        """Check if this is a client credentials token."""
        return self.user is None


class OAuth2Middleware:
    """OAuth2 authentication and authorization middleware."""
    
    def __init__(self) -> None:
        self.auth_server = OAuth2AuthServerService()
    
    def authenticate_token(
        self,
        db: Annotated[Session, Depends(get_db_session)],
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(oauth2_scheme)]
    ) -> Optional[OAuth2TokenData]:
        """
        Authenticate OAuth2 bearer token.
        
        Args:
            db: Database session
            credentials: HTTP authorization credentials
        
        Returns:
            OAuth2TokenData if valid, None if no token provided
        
        Raises:
            HTTPException: If token is invalid
        """
        if not credentials:
            return None
        
        if credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme. Expected Bearer token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validate access token
        access_token = self.auth_server.validate_access_token(db, credentials.credentials)
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get token scopes
        scopes = access_token.get_scopes()
        
        # Create token data
        return OAuth2TokenData(
            access_token=access_token,
            user=access_token.user,
            scopes=scopes
        )
    
    def require_authentication(
        self,
        db: Annotated[Session, Depends(get_db_session)],
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(oauth2_scheme)]
    ) -> OAuth2TokenData:
        """
        Require OAuth2 authentication.
        
        Args:
            db: Database session
            credentials: HTTP authorization credentials
        
        Returns:
            OAuth2TokenData for valid token
        
        Raises:
            HTTPException: If no token or invalid token
        """
        token_data = self.authenticate_token(db, credentials)
        
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return token_data
    
    def require_scope(self, required_scope: str) -> Callable[..., OAuth2TokenData]:
        """
        Create a dependency that requires specific OAuth2 scope.
        
        Args:
            required_scope: Required scope
        
        Returns:
            Dependency function
        """
        def scope_dependency(
            token_data: Annotated[OAuth2TokenData, Depends(self.require_authentication)]
        ) -> OAuth2TokenData:
            if not token_data.has_scope(required_scope):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient scope. Required: {required_scope}",
                    headers={"WWW-Authenticate": f'Bearer scope="{required_scope}"'},
                )
            return token_data
        
        return scope_dependency
    
    def require_any_scope(self, required_scopes: List[str]) -> Callable[..., OAuth2TokenData]:
        """
        Create a dependency that requires any of the specified scopes.
        
        Args:
            required_scopes: List of acceptable scopes
        
        Returns:
            Dependency function
        """
        def scope_dependency(
            token_data: Annotated[OAuth2TokenData, Depends(self.require_authentication)]
        ) -> OAuth2TokenData:
            if not token_data.has_any_scope(required_scopes):
                scope_list = " ".join(required_scopes)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient scope. Required any of: {', '.join(required_scopes)}",
                    headers={"WWW-Authenticate": f'Bearer scope="{scope_list}"'},
                )
            return token_data
        
        return scope_dependency
    
    def require_all_scopes(self, required_scopes: List[str]) -> Callable[..., OAuth2TokenData]:
        """
        Create a dependency that requires all of the specified scopes.
        
        Args:
            required_scopes: List of required scopes
        
        Returns:
            Dependency function
        """
        def scope_dependency(
            token_data: Annotated[OAuth2TokenData, Depends(self.require_authentication)]
        ) -> OAuth2TokenData:
            if not token_data.has_all_scopes(required_scopes):
                scope_list = " ".join(required_scopes)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient scope. Required all of: {', '.join(required_scopes)}",
                    headers={"WWW-Authenticate": f'Bearer scope="{scope_list}"'},
                )
            return token_data
        
        return scope_dependency
    
    def require_user_token(
        self,
        token_data: Annotated[OAuth2TokenData, Depends(oauth2_middleware.require_authentication)]
    ) -> tuple[OAuth2TokenData, User]:
        """
        Require a user-associated token (not client credentials).
        
        Args:
            token_data: OAuth2 token data
        
        Returns:
            Tuple of token data and user
        
        Raises:
            HTTPException: If token is not user-associated
        """
        if token_data.is_client_credentials_token():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User token required. Client credentials token not allowed.",
            )
        
        if not token_data.user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User token required.",
            )
        
        return token_data, token_data.user
    
    def optional_authentication(
        self,
        db: Annotated[Session, Depends(get_db_session)],
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(oauth2_scheme)]
    ) -> Optional[OAuth2TokenData]:
        """
        Optional OAuth2 authentication (doesn't raise error if no token).
        
        Args:
            db: Database session
            credentials: HTTP authorization credentials
        
        Returns:
            OAuth2TokenData if valid token provided, None otherwise
        """
        try:
            return self.authenticate_token(db, credentials)
        except HTTPException:
            return None


# Create middleware instance
oauth2_middleware = OAuth2Middleware()


# Convenience functions for common use cases
def require_oauth2() -> Callable[..., OAuth2TokenData]:
    """Require OAuth2 authentication."""
    return oauth2_middleware.require_authentication


def require_scope(scope: str) -> Callable[..., OAuth2TokenData]:
    """Require specific OAuth2 scope."""
    return oauth2_middleware.require_scope(scope)


def require_any_scope(scopes: List[str]) -> Callable[..., OAuth2TokenData]:
    """Require any of the specified OAuth2 scopes."""
    return oauth2_middleware.require_any_scope(scopes)


def require_all_scopes(scopes: List[str]) -> Callable[..., OAuth2TokenData]:
    """Require all of the specified OAuth2 scopes."""
    return oauth2_middleware.require_all_scopes(scopes)


def require_user_token() -> Callable[..., tuple[OAuth2TokenData, User]]:
    """Require user-associated OAuth2 token."""
    return oauth2_middleware.require_user_token


def optional_oauth2() -> Callable[..., Optional[OAuth2TokenData]]:
    """Optional OAuth2 authentication."""
    return oauth2_middleware.optional_authentication


# Scope-specific shortcuts
def can_read() -> Callable[..., OAuth2TokenData]:
    """Require 'read' scope."""
    return require_scope("read")


def can_write() -> Callable[..., OAuth2TokenData]:
    """Require 'write' scope."""
    return require_scope("write")


def can_admin() -> Callable[..., OAuth2TokenData]:
    """Require 'admin' scope."""
    return require_scope("admin")


def can_manage_users() -> Callable[..., OAuth2TokenData]:
    """Require 'users' scope."""
    return require_scope("users")


def can_manage_roles() -> Callable[..., OAuth2TokenData]:
    """Require 'roles' scope."""
    return require_scope("roles")


def can_manage_oauth_clients() -> Callable[..., OAuth2TokenData]:
    """Require 'oauth-clients' scope."""
    return require_scope("oauth-clients")


def can_read_or_write() -> Callable[..., OAuth2TokenData]:
    """Require either 'read' or 'write' scope."""
    return require_any_scope(["read", "write"])


def can_full_access() -> Callable[..., OAuth2TokenData]:
    """Require both 'read' and 'write' scopes."""
    return require_all_scopes(["read", "write"])


# User context helpers
async def get_current_user_from_token(
    token_data: Annotated[OAuth2TokenData, Depends(require_user_token)]
) -> User:
    """
    Get current user from OAuth2 token.
    
    Args:
        token_data: OAuth2 token data and user
    
    Returns:
        Current user
    """
    _, user = token_data
    return user


async def get_current_user_optional(
    token_data: Annotated[Optional[OAuth2TokenData], Depends(optional_oauth2)]
) -> Optional[User]:
    """
    Get current user from OAuth2 token (optional).
    
    Args:
        token_data: Optional OAuth2 token data
    
    Returns:
        Current user or None
    """
    return token_data.user if token_data else None


# Example usage decorators for controllers
def protected(scopes: Optional[Union[str, List[str]]] = None) -> Callable[..., Any]:
    """
    Decorator for protecting endpoints with OAuth2.
    
    Args:
        scopes: Required scope(s)
    
    Returns:
        Dependency function
    
    Usage:
        @app.get("/protected", dependencies=[Depends(protected("read"))])
        async def protected_endpoint():
            return {"message": "This is protected"}
        
        @app.get("/admin", dependencies=[Depends(protected(["admin", "write"]))])
        async def admin_endpoint():
            return {"message": "Admin only"}
    """
    if scopes is None:
        return require_oauth2()
    elif isinstance(scopes, str):
        return require_scope(scopes)
    elif isinstance(scopes, list):
        return require_all_scopes(scopes)
    else:
        raise ValueError("Scopes must be string, list of strings, or None")


# Advanced scope checks
def check_scope_permission(
    token_data: OAuth2TokenData,
    resource_scope: str,
    action: str = "read"
) -> bool:
    """
    Check if token has permission for resource and action.
    
    Args:
        token_data: OAuth2 token data
        resource_scope: Resource scope (e.g., "users", "posts")
        action: Action (e.g., "read", "write", "delete")
    
    Returns:
        True if has permission
    """
    # Check direct scope
    full_scope = f"{resource_scope}:{action}"
    if token_data.has_scope(full_scope):
        return True
    
    # Check resource-wide scope
    if token_data.has_scope(resource_scope):
        return True
    
    # Check admin scope
    if token_data.has_scope("admin"):
        return True
    
    # Check action-wide scope for backwards compatibility
    if token_data.has_scope(action):
        return True
    
    return False