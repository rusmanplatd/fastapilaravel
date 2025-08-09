from __future__ import annotations

from typing import Callable, Any, Dict, Optional
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
import logging

from app.Auth.Gate import gate_instance, AuthorizationException


class AuthorizationMiddleware(BaseHTTPMiddleware):
    """
    Laravel-style authorization middleware for FastAPI.
    
    Provides automatic authorization checking based on route metadata
    and integrates with the Gate system.
    """
    
    def __init__(self, app: Any, gate: Any = None) -> None:
        super().__init__(app)
        self.gate = gate or gate_instance
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Any:
        """
        Process request through authorization middleware.
        
        Args:
            request: The FastAPI request
            call_next: The next middleware/endpoint to call
        
        Returns:
            Response from the application or authorization error
        """
        start_time = time.time()
        
        try:
            # Get route information
            route = getattr(request, 'scope', {}).get("route")
            if not route:
                response = await call_next(request)
                return response
            
            # Check if route has authorization requirements
            auth_requirements = self._get_route_auth_requirements(route)
            if not auth_requirements:
                response = await call_next(request)
                return response
            
            # Get current user
            user = self._get_current_user(request)
            
            # Perform authorization checks
            await self._authorize_request(request, user, auth_requirements)
            
            # Continue with request
            response = await call_next(request)
            
            # Log successful authorization
            processing_time = time.time() - start_time
            self.logger.debug(
                f"Authorization passed for {getattr(request, 'method', 'UNKNOWN')} {getattr(getattr(request, 'url', {}), 'path', 'UNKNOWN')} "
                f"in {processing_time:.3f}s"
            )
            
            return response
            
        except AuthorizationException as e:
            # Handle authorization failures
            self.logger.warning(
                f"Authorization failed for {getattr(request, 'method', 'UNKNOWN')} {getattr(getattr(request, 'url', {}), 'path', 'UNKNOWN')}: {getattr(e, 'detail', str(e))}"
            )
            response = JSONResponse(
                status_code=getattr(e, 'status_code', 403),
                content={
                    "success": False,
                    "message": getattr(e, 'detail', str(e)),
                    "error_code": "AUTHORIZATION_FAILED",
                    "timestamp": time.time()
                }
            )
            return response
        except Exception as e:
            # Handle unexpected errors
            self.logger.error(f"Authorization middleware error: {e}")
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "message": "Internal authorization error",
                    "error_code": "AUTHORIZATION_ERROR"
                }
            )
            return response
    
    def _get_route_auth_requirements(self, route: Any) -> Optional[Dict[str, Any]]:
        """
        Extract authorization requirements from route metadata.
        
        Args:
            route: The FastAPI route object
        
        Returns:
            Dictionary with authorization requirements or None
        """
        # Check route dependencies for authorization metadata
        if hasattr(route, 'dependant') and route.dependant:
            dependencies = route.dependant.dependencies
            for dependency in dependencies:
                if hasattr(dependency, 'call') and hasattr(dependency.call, '_auth_requirements'):
                    return getattr(dependency.call, '_auth_requirements', None)
        
        # Check endpoint function for authorization metadata
        if hasattr(route, 'endpoint') and hasattr(route.endpoint, '_auth_requirements'):
            return getattr(route.endpoint, '_auth_requirements', None)
        
        return None
    
    def _get_current_user(self, request: Request) -> Optional[Any]:
        """
        Get the current authenticated user from the request.
        
        Args:
            request: The FastAPI request
        
        Returns:
            The current user or None
        """
        # Try to get user from request state (set by authentication middleware)
        if hasattr(request.state, 'user'):
            return request.state.user
        
        # Try to get user from session or other sources
        # This would integrate with your authentication system
        return None
    
    async def _authorize_request(
        self, 
        request: Request, 
        user: Optional[Any], 
        auth_requirements: Dict[str, Any]
    ) -> None:
        """
        Perform authorization checks based on requirements.
        
        Args:
            request: The FastAPI request
            user: The current user
            auth_requirements: Authorization requirements
        
        Raises:
            AuthorizationException: If authorization fails
        """
        # Handle different types of authorization requirements
        
        # Check required abilities
        if 'abilities' in auth_requirements:
            abilities = auth_requirements['abilities']
            if isinstance(abilities, str):
                abilities = [abilities]
            
            for ability in abilities:
                if not self.gate.allows(ability, user=user):
                    raise AuthorizationException(
                        f"Missing required ability: {ability}"
                    )
        
        # Check required roles
        if 'roles' in auth_requirements:
            if not user:
                raise AuthorizationException("Authentication required")
            
            roles = auth_requirements['roles']
            if isinstance(roles, str):
                roles = [roles]
            
            if not any(self._user_has_role(user, role) for role in roles):
                raise AuthorizationException(
                    f"Missing required role: {' or '.join(roles)}"
                )
        
        # Check required permissions
        if 'permissions' in auth_requirements:
            if not user:
                raise AuthorizationException("Authentication required")
            
            permissions = auth_requirements['permissions']
            if isinstance(permissions, str):
                permissions = [permissions]
            
            for permission in permissions:
                if not self._user_has_permission(user, permission):
                    raise AuthorizationException(
                        f"Missing required permission: {permission}"
                    )
        
        # Check custom authorization function
        if 'custom' in auth_requirements:
            custom_auth = auth_requirements['custom']
            if callable(custom_auth):
                if not await self._call_custom_authorization(custom_auth, request, user):
                    raise AuthorizationException("Custom authorization failed")
        
        # Check resource-based authorization
        if 'resource' in auth_requirements:
            resource_config = auth_requirements['resource']
            await self._authorize_resource_access(request, user, resource_config)
    
    def _user_has_role(self, user: Any, role: str) -> bool:
        """
        Check if user has a specific role.
        
        Args:
            user: The user to check
            role: The role name
        
        Returns:
            True if user has the role
        """
        if hasattr(user, 'has_role'):
            result = user.has_role(role)
            return bool(result)
        elif hasattr(user, 'roles'):
            return role in [r.name for r in user.roles]
        return False
    
    def _user_has_permission(self, user: Any, permission: str) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user: The user to check
            permission: The permission name
        
        Returns:
            True if user has the permission
        """
        if hasattr(user, 'can'):
            result = user.can(permission)
            return bool(result)
        elif hasattr(user, 'permissions'):
            return permission in [p.name for p in user.permissions]
        return False
    
    async def _call_custom_authorization(
        self, 
        custom_auth: Callable[..., Any], 
        request: Request, 
        user: Optional[Any]
    ) -> bool:
        """
        Call custom authorization function.
        
        Args:
            custom_auth: The custom authorization function
            request: The FastAPI request
            user: The current user
        
        Returns:
            True if authorized
        """
        try:
            # Handle both sync and async custom authorization functions
            if hasattr(custom_auth, '__await__'):
                result = await custom_auth(request, user)
                return bool(result)
            else:
                result = custom_auth(request, user)
                return bool(result)
        except Exception as e:
            self.logger.error(f"Custom authorization function error: {e}")
            return False
    
    async def _authorize_resource_access(
        self, 
        request: Request, 
        user: Optional[Any], 
        resource_config: Dict[str, Any]
    ) -> None:
        """
        Authorize access to a specific resource.
        
        Args:
            request: The FastAPI request
            user: The current user
            resource_config: Resource authorization configuration
        
        Raises:
            AuthorizationException: If authorization fails
        """
        # Extract resource from request (e.g., path parameters)
        resource_id = None
        resource_param = resource_config.get('param', 'id')
        
        if hasattr(request, 'path_params') and resource_param in request.path_params:
            resource_id = request.path_params[resource_param]
        
        if not resource_id:
            raise AuthorizationException("Resource ID not found")
        
        # Load the resource
        resource_loader = resource_config.get('loader')
        if not resource_loader:
            raise AuthorizationException("Resource loader not configured")
        
        resource = await self._load_resource(resource_loader, resource_id)
        if not resource:
            raise AuthorizationException("Resource not found", status.HTTP_404_NOT_FOUND)
        
        # Check authorization on the resource
        ability = resource_config.get('ability', 'view')
        if not self.gate.allows(ability, resource, user=user):
            raise AuthorizationException(
                f"Not authorized to {ability} this resource"
            )
    
    async def _load_resource(self, loader: Callable[..., Any], resource_id: str) -> Optional[Any]:
        """
        Load a resource using the provided loader function.
        
        Args:
            loader: Function to load the resource
            resource_id: ID of the resource to load
        
        Returns:
            The loaded resource or None
        """
        try:
            if hasattr(loader, '__await__'):
                return await loader(resource_id)
            else:
                return loader(resource_id)
        except Exception as e:
            self.logger.error(f"Resource loader error: {e}")
            return None


# Decorators for route authorization

def authorize(abilities: Optional[Any] = None, roles: Optional[Any] = None, 
              permissions: Optional[Any] = None, custom: Optional[Callable[..., Any]] = None) -> Callable[..., Any]:
    """
    Decorator to add authorization requirements to FastAPI routes.
    
    Args:
        abilities: Required abilities (string or list)
        roles: Required roles (string or list)
        permissions: Required permissions (string or list)
        custom: Custom authorization function
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Store authorization requirements on the function
        setattr(func, '_auth_requirements', {
            'abilities': abilities,
            'roles': roles,
            'permissions': permissions,
            'custom': custom
        })
        return func
    return decorator


def authorize_resource(model_class: Any, ability: str = 'view', param: str = 'id') -> Callable[..., Any]:
    """
    Decorator to add resource-based authorization to FastAPI routes.
    
    Args:
        model_class: The model class for the resource
        ability: The ability to check (default: 'view')
        param: The path parameter name for the resource ID
    """
    def resource_loader(resource_id: str) -> Any:
        # This would typically query your database
        # For now, it's a placeholder
        return model_class.find(resource_id)
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, '_auth_requirements', {
            'resource': {
                'model': model_class,
                'ability': ability,
                'param': param,
                'loader': resource_loader
            }
        })
        return func
    return decorator


def require_abilities(*abilities: str) -> Callable[..., Any]:
    """
    Decorator to require specific abilities.
    
    Args:
        *abilities: The abilities to require
    """
    return authorize(abilities=list(abilities))


def require_roles(*roles: str) -> Callable[..., Any]:
    """
    Decorator to require specific roles.
    
    Args:
        *roles: The roles to require
    """
    return authorize(roles=list(roles))


def require_permissions(*permissions: str) -> Callable[..., Any]:
    """
    Decorator to require specific permissions.
    
    Args:
        *permissions: The permissions to require
    """
    return authorize(permissions=list(permissions))


def require_auth() -> Callable[..., Any]:
    """
    Decorator to require authentication (any authenticated user).
    """
    def auth_check(request: Request, user: Optional[Any]) -> bool:
        return user is not None
    
    return authorize(custom=auth_check)


def admin_only() -> Callable[..., Any]:
    """
    Decorator to require admin role.
    """
    return require_roles('admin')


def super_admin_only() -> Callable[..., Any]:
    """
    Decorator to require super admin privileges.
    """
    def super_admin_check(request: Request, user: Optional[Any]) -> bool:
        return bool(user and hasattr(user, 'is_super_admin') and user.is_super_admin)
    
    return authorize(custom=super_admin_check)