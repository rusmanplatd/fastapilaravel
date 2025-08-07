from fastapi import HTTPException, status, Depends
from functools import wraps
from typing import List, Union, Callable, Any
from typing_extensions import Annotated
from sqlalchemy.orm import Session

from app.Models import User
from app.Http.Controllers import get_current_user
from config import get_database


def require_permission(permission: Union[str, List[str]], require_all: bool = True) -> Any:
    """
    Decorator to require specific permission(s) for a route.
    Similar to Spatie Laravel Permission middleware.
    
    Args:
        permission: Single permission string or list of permissions
        require_all: If True and multiple permissions provided, user must have ALL permissions.
                    If False, user needs ANY of the permissions.
    """
    def decorator(func) -> Any:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get current user from the endpoint dependencies
            current_user = None
            
            # Look for current_user in kwargs (dependency injection)
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            else:
                # If not in kwargs, we need to get it
                try:
                    # This assumes the route has current_user as a dependency
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
            
            # Check permissions
            if isinstance(permission, str):
                if not current_user.has_permission_to(permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required permission: {permission}"
                    )
            elif isinstance(permission, list):
                if require_all:
                    if not current_user.has_all_permissions(permission):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Missing required permissions: {', '.join(permission)}"
                        )
                else:
                    if not current_user.has_any_permission(permission):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Missing any of required permissions: {', '.join(permission)}"
                        )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_role(role: Union[str, List[str]], require_all: bool = True) -> Any:
    """
    Decorator to require specific role(s) for a route.
    
    Args:
        role: Single role string or list of roles
        require_all: If True and multiple roles provided, user must have ALL roles.
                    If False, user needs ANY of the roles.
    """
    def decorator(func) -> Any:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get current user from the endpoint dependencies
            current_user = None
            
            # Look for current_user in kwargs (dependency injection)
            if 'current_user' in kwargs:
                current_user = kwargs['current_user']
            else:
                # If not in kwargs, we need to get it
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
            
            # Check roles
            if isinstance(role, str):
                if not current_user.has_role(role):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required role: {role}"
                    )
            elif isinstance(role, list):
                if require_all:
                    if not current_user.has_all_roles(role):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Missing required roles: {', '.join(role)}"
                        )
                else:
                    if not current_user.has_any_role(role):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Missing any of required roles: {', '.join(role)}"
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
    def decorator(func) -> Any:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
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
def check_permission(permission_name: str) -> Any:
    """
    FastAPI dependency to check if current user has specific permission
    """
    def permission_checker(current_user: Annotated[User, Depends(get_current_user)]) -> None:
        if not current_user.has_permission_to(permission_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission_name}"
            )
        return current_user
    return permission_checker


def check_role(role_name: str) -> Any:
    """
    FastAPI dependency to check if current user has specific role
    """
    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> None:
        if not current_user.has_role(role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: {role_name}"
            )
        return current_user
    return role_checker


def check_any_permission(permission_names: List[str]) -> Any:
    """
    FastAPI dependency to check if current user has any of the specified permissions
    """
    def permission_checker(current_user: Annotated[User, Depends(get_current_user)]) -> None:
        if not current_user.has_any_permission(permission_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing any of required permissions: {', '.join(permission_names)}"
            )
        return current_user
    return permission_checker


def check_all_permissions(permission_names: List[str]) -> Any:
    """
    FastAPI dependency to check if current user has all of the specified permissions
    """
    def permission_checker(current_user: Annotated[User, Depends(get_current_user)]) -> None:
        if not current_user.has_all_permissions(permission_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(permission_names)}"
            )
        return current_user
    return permission_checker


def check_any_role(role_names: List[str]) -> Any:
    """
    FastAPI dependency to check if current user has any of the specified roles
    """
    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> None:
        if not current_user.has_any_role(role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing any of required roles: {', '.join(role_names)}"
            )
        return current_user
    return role_checker


def check_all_roles(role_names: List[str]) -> Any:
    """
    FastAPI dependency to check if current user has all of the specified roles
    """
    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> None:
        if not current_user.has_all_roles(role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required roles: {', '.join(role_names)}"
            )
        return current_user
    return role_checker


# Convenience functions
def can(permission: str) -> Callable[[Annotated[User, Depends(get_current_user)]], None]:
    """Alias for check_permission"""
    return check_permission(permission)


def is_role(role: str) -> Callable[[Annotated[User, Depends(get_current_user)]], None]:
    """Alias for check_role"""
    return check_role(role)


def has_any_permission(permissions: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], None]:
    """Alias for check_any_permission"""
    return check_any_permission(permissions)


def has_all_permissions(permissions: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], None]:
    """Alias for check_all_permissions"""
    return check_all_permissions(permissions)


def has_any_role(roles: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], None]:
    """Alias for check_any_role"""
    return check_any_role(roles)


def has_all_roles(roles: List[str]) -> Callable[[Annotated[User, Depends(get_current_user)]], None]:
    """Alias for check_all_roles"""
    return check_all_roles(roles)