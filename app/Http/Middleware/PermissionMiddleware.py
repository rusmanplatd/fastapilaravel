from __future__ import annotations

from fastapi import HTTPException, status, Depends, Request
from functools import wraps
from typing import List, Union, Callable, Any, Optional, Dict, Set
from typing_extensions import Annotated
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import asyncio
import json
import logging

from app.Models import User, Role, Permission
from app.Http.Controllers import get_current_user
from app.Services.PermissionCacheService import PermissionCacheService
from app.Services.RoleHierarchyService import RoleHierarchyService
from config import get_database


def require_permission(
    permission: Union[str, List[str]], 
    require_all: bool = True,
    allow_cache: bool = True,
    check_mfa: bool = True,
    log_access: bool = True,
    context: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Enhanced decorator to require specific permission(s) for a route.
    
    Args:
        permission: Single permission string or list of permissions
        require_all: If True and multiple permissions provided, user must have ALL permissions.
        allow_cache: Whether to use cached permission data for faster checks
        check_mfa: Whether to enforce MFA for dangerous permissions
        log_access: Whether to log permission access attempts
        context: Additional context for permission checks
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get current user and request context
            current_user = None
            request = None
            
            # Extract user and request from arguments
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Request):
                    request = arg
            
            # Look for current_user in kwargs (dependency injection)
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            if 'request' in kwargs:
                request = kwargs['request']
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Enhanced permission checking
            await _check_permissions_enhanced(
                current_user=current_user,
                required_permissions=permission,
                require_all=require_all,
                allow_cache=allow_cache,
                check_mfa=check_mfa,
                log_access=log_access,
                context=context,
                request=request
            )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_role(
    role: Union[str, List[str]], 
    require_all: bool = True,
    allow_cache: bool = True,
    check_hierarchy: bool = True,
    log_access: bool = True,
    context: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Enhanced decorator to require specific role(s) for a route.
    
    Args:
        role: Single role string or list of roles
        require_all: If True and multiple roles provided, user must have ALL roles.
        allow_cache: Whether to use cached role data for faster checks
        check_hierarchy: Whether to check role hierarchy for inheritance
        log_access: Whether to log role access attempts
        context: Additional context for role checks
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get current user and request context
            current_user = None
            request = None
            
            # Extract user and request from arguments
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Request):
                    request = arg
            
            # Look for current_user in kwargs (dependency injection)
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            if 'request' in kwargs:
                request = kwargs['request']
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Enhanced role checking
            await _check_roles_enhanced(
                current_user=current_user,
                required_roles=role,
                require_all=require_all,
                allow_cache=allow_cache,
                check_hierarchy=check_hierarchy,
                log_access=log_access,
                context=context,
                request=request
            )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_permission_or_role(permission: Union[str, List[str]], role: Union[str, List[str]]) -> Any:
    """
    Decorator that allows access if user has either the required permission(s) OR role(s).
    
    Args:
        permission: Single permission string or list of permissions
        role: Single role string or list of roles
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get current user from the endpoint dependencies
            current_user = None
            
            # Look for current_user in kwargs (dependency injection)
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            else:
                try:
                    for arg in args:
                        if isinstance(arg, User):
                            current_user = arg
                            break
                    
                    if not current_user:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Authentication required"
                        )
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
            
            # Check permissions first
            has_permission = False
            if isinstance(permission, str):
                has_permission = current_user.has_permission_to(permission)
            elif isinstance(permission, list):
                has_permission = current_user.has_any_permission(permission)
            
            # If has permission, allow access
            if has_permission:
                return await func(*args, **kwargs)
            
            # Check roles
            has_role = False
            if isinstance(role, str):
                has_role = current_user.has_role(role)
            elif isinstance(role, list):
                has_role = current_user.has_any_role(role)
            
            # If has role, allow access
            if has_role:
                return await func(*args, **kwargs)
            
            # Neither permission nor role found
            perm_str = permission if isinstance(permission, str) else ', '.join(permission)
            role_str = role if isinstance(role, str) else ', '.join(role)
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission ({perm_str}) or role ({role_str})"
            )
        
        return wrapper
    return decorator


# Dependency functions for FastAPI
def check_permission(permission_name: str) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """
    FastAPI dependency to check if current user has specific permission
    """
    def permission_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not current_user.has_permission_to(permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission_name}"
            )
        return current_user
    return permission_checker


def check_role(role_name: str) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """
    FastAPI dependency to check if current user has specific role
    """
    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not current_user.has_role(role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: {role_name}"
            )
        return current_user
    return role_checker


def check_any_permission(permission_names: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """
    FastAPI dependency to check if current user has any of the specified permissions
    """
    def permission_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not current_user.has_any_permission(permission_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing any of required permissions: {', '.join(permission_names)}"
            )
        return current_user
    return permission_checker


def check_all_permissions(permission_names: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """
    FastAPI dependency to check if current user has all of the specified permissions
    """
    def permission_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not current_user.has_all_permissions(permission_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(permission_names)}"
            )
        return current_user
    return permission_checker


def check_any_role(role_names: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """
    FastAPI dependency to check if current user has any of the specified roles
    """
    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not current_user.has_any_role(role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing any of required roles: {', '.join(role_names)}"
            )
        return current_user
    return role_checker


def check_all_roles(role_names: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """
    FastAPI dependency to check if current user has all of the specified roles
    """
    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not current_user.has_all_roles(role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required roles: {', '.join(role_names)}"
            )
        return current_user
    return role_checker


# Enhanced helper functions

async def _check_permissions_enhanced(
    current_user: User,
    required_permissions: Union[str, List[str]],
    require_all: bool = True,
    allow_cache: bool = True,
    check_mfa: bool = True,
    log_access: bool = True,
    context: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
) -> None:
    """Enhanced permission checking with caching and MFA."""
    
    # Get database session
    db = next(get_database())
    
    # Initialize services
    cache_service = PermissionCacheService(db) if allow_cache else None
    
    # Normalize permissions to list
    permissions_to_check = [required_permissions] if isinstance(required_permissions, str) else required_permissions
    
    # Check each permission
    granted_permissions = []
    denied_permissions = []
    mfa_required_permissions = []
    
    for perm in permissions_to_check:
        # Use cache if available
        if cache_service:
            has_permission = cache_service.check_user_permission_cached(current_user, perm)
        else:
            has_permission = current_user.has_permission_to(perm)
        
        if has_permission:
            granted_permissions.append(perm)
            
            # Check if MFA is required for this permission
            if check_mfa:
                perm_obj = db.query(Permission).filter(Permission.name == perm).first()
                if perm_obj and perm_obj.requires_mfa:
                    if not current_user.has_mfa_enabled() or not _is_mfa_verified(current_user):
                        mfa_required_permissions.append(perm)
        else:
            denied_permissions.append(perm)
    
    # Log access attempt
    if log_access:
        _log_permission_access(
            user=current_user,
            permissions=permissions_to_check,
            granted=granted_permissions,
            denied=denied_permissions,
            context=context,
            request=request
        )
    
    # Check MFA requirements
    if mfa_required_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"MFA required for permissions: {', '.join(mfa_required_permissions)}",
            headers={"X-MFA-Required": "true"}
        )
    
    # Evaluate permission requirements
    if require_all:
        if denied_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(denied_permissions)}"
            )
    else:
        if not granted_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing any of required permissions: {', '.join(permissions_to_check)}"
            )


async def _check_roles_enhanced(
    current_user: User,
    required_roles: Union[str, List[str]],
    require_all: bool = True,
    allow_cache: bool = True,
    check_hierarchy: bool = True,
    log_access: bool = True,
    context: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
) -> None:
    """Enhanced role checking with caching and hierarchy."""
    
    # Get database session
    db = next(get_database())
    
    # Initialize services
    cache_service = PermissionCacheService(db) if allow_cache else None
    hierarchy_service = RoleHierarchyService(db) if check_hierarchy else None
    
    # Normalize roles to list
    roles_to_check = [required_roles] if isinstance(required_roles, str) else required_roles
    
    # Check each role
    granted_roles = []
    denied_roles = []
    
    for role_name in roles_to_check:
        # Use cache if available
        if cache_service:
            has_role = cache_service.check_user_role_cached(current_user, role_name)
        else:
            has_role = current_user.has_role(role_name)
        
        # Check hierarchy if enabled and role not directly assigned
        if not has_role and check_hierarchy and hierarchy_service:
            role_obj = db.query(Role).filter(Role.name == role_name).first()
            if role_obj:
                # Check if user has any parent roles
                for user_role in current_user.roles:
                    if user_role.is_ancestor_of(role_obj):
                        has_role = True
                        break
        
        if has_role:
            granted_roles.append(role_name)
        else:
            denied_roles.append(role_name)
    
    # Log access attempt
    if log_access:
        _log_role_access(
            user=current_user,
            roles=roles_to_check,
            granted=granted_roles,
            denied=denied_roles,
            context=context,
            request=request
        )
    
    # Evaluate role requirements
    if require_all:
        if denied_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required roles: {', '.join(denied_roles)}"
            )
    else:
        if not granted_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing any of required roles: {', '.join(roles_to_check)}"
            )


def _is_mfa_verified(user: User) -> bool:
    """Check if user has completed MFA verification in current session."""
    # This would typically check session data or JWT claims
    # For now, just check if MFA is enabled
    return user.has_mfa_enabled()


def _log_permission_access(
    user: User,
    permissions: List[str],
    granted: List[str],
    denied: List[str],
    context: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
) -> None:
    """Log permission access attempts."""
    logger = logging.getLogger("rbac.permissions")
    
    log_data = {
        "user_id": user.id,
        "user_email": user.email,
        "permissions_requested": permissions,
        "permissions_granted": granted,
        "permissions_denied": denied,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": context or {}
    }
    
    if request:
        log_data.update({
            "ip_address": getattr(request.client, 'host', None),
            "user_agent": request.headers.get("user-agent"),
            "endpoint": str(request.url),
            "method": request.method
        })
    
    if denied:
        logger.warning(f"Permission denied for user {user.id}: {denied}", extra=log_data)
    else:
        logger.info(f"Permission granted for user {user.id}: {granted}", extra=log_data)


def _log_role_access(
    user: User,
    roles: List[str],
    granted: List[str],
    denied: List[str],
    context: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None
) -> None:
    """Log role access attempts."""
    logger = logging.getLogger("rbac.roles")
    
    log_data = {
        "user_id": user.id,
        "user_email": user.email,
        "roles_requested": roles,
        "roles_granted": granted,
        "roles_denied": denied,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context": context or {}
    }
    
    if request:
        log_data.update({
            "ip_address": getattr(request.client, 'host', None),
            "user_agent": request.headers.get("user-agent"),
            "endpoint": str(request.url),
            "method": request.method
        })
    
    if denied:
        logger.warning(f"Role access denied for user {user.id}: {denied}", extra=log_data)
    else:
        logger.info(f"Role access granted for user {user.id}: {granted}", extra=log_data)


# Enhanced dependency functions with caching
def check_permission_cached(permission_name: str) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """FastAPI dependency to check permission using cache."""
    def permission_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        db = next(get_database())
        cache_service = PermissionCacheService(db)
        
        if not cache_service.check_user_permission_cached(current_user, permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission_name}"
            )
        return current_user
    return permission_checker


def check_role_cached(role_name: str) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """FastAPI dependency to check role using cache."""
    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        db = next(get_database())
        cache_service = PermissionCacheService(db)
        
        if not cache_service.check_user_role_cached(current_user, role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: {role_name}"
            )
        return current_user
    return role_checker


# Convenience functions
def can(permission: str) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """Alias for check_permission"""
    return check_permission(permission)


def can_cached(permission: str) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """Alias for check_permission_cached"""
    return check_permission_cached(permission)


def is_role(role: str) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """Alias for check_role"""
    return check_role(role)


def has_any_permission(permissions: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """Alias for check_any_permission"""
    return check_any_permission(permissions)


def has_all_permissions(permissions: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """Alias for check_all_permissions"""
    return check_all_permissions(permissions)


def has_any_role(roles: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """Alias for check_any_role"""
    return check_any_role(roles)


def has_all_roles(roles: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """Alias for check_all_roles"""
    return check_all_roles(roles)


def is_role_cached(role: str) -> Callable[[Annotated[User, Depends(get_current_user)]], User]:
    """Alias for check_role_cached"""
    return check_role_cached(role)


# Advanced middleware for complex authorization scenarios
def require_permission_with_context(
    permission_check: Callable[[User, Dict[str, Any]], bool],
    context_builder: Optional[Callable[[Request], Dict[str, Any]]] = None
) -> Any:
    """Decorator for context-aware permission checking."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_user = None
            request = None
            
            # Extract user and request from arguments
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                elif isinstance(arg, Request):
                    request = arg
            
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            if 'request' in kwargs:
                request = kwargs['request']
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Build context
            context = {}
            if context_builder and request:
                context = context_builder(request)
            
            # Check permission with context
            if not permission_check(current_user, context):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied based on context"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Rate limiting decorator for sensitive permissions
def require_permission_with_rate_limit(
    permission: str,
    max_attempts: int = 5,
    window_minutes: int = 60
) -> Any:
    """Decorator that adds rate limiting to permission checks."""
    attempts_cache: Dict[str, List[datetime]] = {}
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_user = None
            
            # Extract user from arguments
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break
            
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check rate limit
            cache_key = f"{current_user.id}:{permission}"
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(minutes=window_minutes)
            
            # Clean old attempts
            if cache_key in attempts_cache:
                attempts_cache[cache_key] = [attempt for attempt in attempts_cache[cache_key] if attempt > window_start]
            else:
                attempts_cache[cache_key] = []
            
            # Check if rate limit exceeded
            if len(attempts_cache[cache_key]) >= max_attempts:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded for permission {permission}"
                )
            
            # Check permission
            if not current_user.has_permission_to(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {permission}"
                )
            
            # Record attempt
            attempts_cache[cache_key].append(now)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator