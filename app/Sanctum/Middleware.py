from __future__ import annotations

from typing import Optional, List, Union, Callable, Any
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from functools import wraps

from .SanctumManager import SanctumManager
from .PersonalAccessToken import PersonalAccessToken


class SanctumAuthenticationMiddleware:
    """
    Sanctum authentication middleware for FastAPI.
    
    Authenticates requests using Sanctum personal access tokens.
    """
    
    def __init__(self, sanctum_manager: SanctumManager = None):
        self.sanctum = sanctum_manager or SanctumManager()
        self.bearer_scheme = HTTPBearer(auto_error=False)
    
    async def __call__(self, request: Request) -> Optional[Any]:
        """
        Authenticate the request and return the user.
        
        Args:
            request: The FastAPI request
            
        Returns:
            Authenticated user or None
        """
        user = await self.sanctum.authenticate(request)
        
        # Store the authenticated user in request state
        request.state.user = user
        request.state.sanctum_token = getattr(user, '_current_access_token', None) if user else None
        
        return user


# Global sanctum middleware instance
sanctum_middleware = SanctumAuthenticationMiddleware()


async def sanctum_user(request: Request) -> Optional[Any]:
    """
    Dependency to get the authenticated Sanctum user.
    
    Args:
        request: The FastAPI request
        
    Returns:
        Authenticated user or None
    """
    return await sanctum_middleware(request)


async def require_sanctum_auth(request: Request) -> Any:
    """
    Dependency that requires Sanctum authentication.
    
    Args:
        request: The FastAPI request
        
    Returns:
        Authenticated user
        
    Raises:
        HTTPException: If user is not authenticated
    """
    user = await sanctum_user(request)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def require_abilities(*abilities: str):
    """
    Dependency factory that requires specific token abilities.
    
    Args:
        *abilities: Required abilities
        
    Returns:
        FastAPI dependency function
    """
    async def check_abilities(request: Request) -> Any:
        user = await require_sanctum_auth(request)
        
        # Get the current token
        if not hasattr(user, 'current_access_token') or not user.current_access_token():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token required",
            )
        
        token = user.current_access_token()
        
        # Check each required ability
        for ability in abilities:
            if not token.can(ability):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Token does not have required ability: {ability}",
                )
        
        return user
    
    return check_abilities


def require_any_ability(*abilities: str):
    """
    Dependency factory that requires any of the specified abilities.
    
    Args:
        *abilities: Any of these abilities is sufficient
        
    Returns:
        FastAPI dependency function
    """
    async def check_any_ability(request: Request) -> Any:
        user = await require_sanctum_auth(request)
        
        # Get the current token
        if not hasattr(user, 'current_access_token') or not user.current_access_token():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token required",
            )
        
        token = user.current_access_token()
        
        # Check if token has any of the required abilities
        for ability in abilities:
            if token.can(ability):
                return user
        
        # No abilities matched
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Token must have one of: {', '.join(abilities)}",
        )
    
    return check_any_ability


def optional_sanctum_auth():
    """
    Dependency for optional Sanctum authentication.
    
    Returns the user if authenticated, None otherwise.
    Does not raise an exception for unauthenticated requests.
    """
    async def optional_auth(request: Request) -> Optional[Any]:
        return await sanctum_user(request)
    
    return optional_auth


# Decorator versions for easier usage
def auth_sanctum(func: Callable) -> Callable:
    """
    Decorator that requires Sanctum authentication.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract request from args/kwargs
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break
        
        if not request:
            request = kwargs.get('request')
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Request object not found in function arguments"
            )
        
        # Authenticate user
        user = await require_sanctum_auth(request)
        
        # Add user to kwargs if not already present
        if 'user' not in kwargs:
            kwargs['user'] = user
        
        return await func(*args, **kwargs)
    
    return wrapper


def abilities(*required_abilities: str):
    """
    Decorator that requires specific token abilities.
    
    Args:
        *required_abilities: Required abilities
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found in function arguments"
                )
            
            # Check abilities
            dependency = require_abilities(*required_abilities)
            user = await dependency(request)
            
            # Add user to kwargs if not already present
            if 'user' not in kwargs:
                kwargs['user'] = user
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def any_ability(*required_abilities: str):
    """
    Decorator that requires any of the specified abilities.
    
    Args:
        *required_abilities: Any of these abilities is sufficient
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                request = kwargs.get('request')
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found in function arguments"
                )
            
            # Check abilities
            dependency = require_any_ability(*required_abilities)
            user = await dependency(request)
            
            # Add user to kwargs if not already present
            if 'user' not in kwargs:
                kwargs['user'] = user
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator