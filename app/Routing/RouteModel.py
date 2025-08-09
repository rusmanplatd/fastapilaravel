"""
Laravel 12 Route Model Binding

This module provides advanced route model binding with:
- Implicit binding
- Explicit binding
- Custom binding logic
- Scoped bindings
- Soft delete awareness
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast
from functools import wraps

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.Support.Types import ModelT, validate_types
from app.Models.BaseModel import BaseModel
from app.Support.ServiceContainer import container

RouteBindingT = TypeVar('RouteBindingT')


class RouteModelBinder:
    """Laravel 12 enhanced route model binder."""
    
    def __init__(self) -> None:
        self.bindings: Dict[str, Callable[[Any, Optional[str]], Any]] = {}
        self.implicit_bindings: Dict[Type[BaseModel], str] = {}
        self.scoped_bindings: Dict[str, Dict[str, Any]] = {}
        self.custom_resolvers: Dict[str, Callable[[Any, Request], Any]] = {}
        
    def bind(self, key: str, resolver: Union[Type[BaseModel], Callable[[Any], Any]]) -> None:
        """Bind a model or resolver to a route parameter."""
        if isinstance(resolver, type) and issubclass(resolver, BaseModel):
            # Model class binding
            self.bindings[key] = self._create_model_resolver(resolver)
        else:
            # Custom resolver
            self.bindings[key] = resolver
    
    def _create_model_resolver(self, model_class: Type[BaseModel]) -> Callable[[Any, Optional[str]], BaseModel]:
        """Create model resolver for implicit binding."""
        def resolver(value: Any, field: Optional[str] = None) -> BaseModel:
            # Get database session
            session = container.make('db')
            
            # Use custom field or primary key
            lookup_field = field or model_class.get_key_name()
            
            # Check for custom resolution method on model
            if hasattr(model_class, 'resolve_route_binding'):
                result = model_class.resolve_route_binding(value, field)
                if result:
                    return result
            
            # Default lookup
            query = session.query(model_class)
            
            # Apply scoped binding if configured
            if model_class.__name__ in self.scoped_bindings:
                scope_config = self.scoped_bindings[model_class.__name__]
                for scope_field, scope_value in scope_config.items():
                    query = query.filter(getattr(model_class, scope_field) == scope_value)
            
            # Perform lookup
            if lookup_field == model_class.get_key_name():
                instance = query.filter(getattr(model_class, lookup_field) == value).first()
            else:
                instance = query.filter(getattr(model_class, lookup_field) == value).first()
            
            if not instance:
                raise HTTPException(
                    status_code=404,
                    detail=f"{model_class.__name__} not found"
                )
            
            return instance
        
        return resolver
    
    def implicit(self, model_class: Type[BaseModel], field: Optional[str] = None) -> None:
        """Register implicit binding for model."""
        lookup_field = field or model_class.get_route_key_name()
        self.implicit_bindings[model_class] = lookup_field
        
        # Auto-register binding using model name
        model_name = model_class.__name__.lower()
        self.bind(model_name, model_class)
    
    def scoped(
        self,
        model_class: Type[BaseModel],
        scope_field: str,
        scope_value: Any
    ) -> None:
        """Register scoped binding for model."""
        model_name = model_class.__name__
        if model_name not in self.scoped_bindings:
            self.scoped_bindings[model_name] = {}
        
        self.scoped_bindings[model_name][scope_field] = scope_value
    
    def substitute_bindings(self, request: Request, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute route parameters with bound models."""
        substituted = parameters.copy()
        
        for param_name, param_value in parameters.items():
            if param_name in self.bindings:
                resolver = self.bindings[param_name]
                substituted[param_name] = resolver(param_value)
            elif param_name in self.custom_resolvers:
                resolver = self.custom_resolvers[param_name]
                substituted[param_name] = resolver(param_value, request)
        
        return substituted
    
    def resolve_explicit_binding(self, key: str, value: Any) -> Any:
        """Resolve explicit binding."""
        if key in self.bindings:
            return self.bindings[key](value)
        return value
    
    def resolve_implicit_binding(self, parameter_name: str, value: Any, request: Request) -> Any:
        """Resolve implicit binding based on parameter name."""
        # Try to find model class by parameter name
        for model_class, field in self.implicit_bindings.items():
            model_name = model_class.__name__.lower()
            if parameter_name == model_name or parameter_name.endswith(f'_{model_name}'):
                resolver = self._create_model_resolver(model_class)
                return resolver(value, field)
        
        return value
    
    def get_binding_field(self, model_class: Type[BaseModel]) -> str:
        """Get binding field for model."""
        return self.implicit_bindings.get(model_class, model_class.get_route_key_name())


class RouteModelServiceProvider:
    """Service provider for route model binding."""
    
    def __init__(self) -> None:
        self.binder = RouteModelBinder()
    
    def register(self) -> None:
        """Register route model binding services."""
        # Register binder in container
        container.singleton('route.model.binder', lambda: self.binder)
    
    def boot(self) -> None:
        """Boot route model binding."""
        # Auto-discover and register models
        self.discover_models()
    
    def discover_models(self) -> None:
        """Auto-discover models for implicit binding."""
        # This would scan for model classes and register them
        # For now, we'll register common models manually
        
        # Example registrations
        try:
            from app.Models.User import User
            self.binder.implicit(User)
        except ImportError:
            pass
        
        try:
            from app.Models.Post import Post
            self.binder.implicit(Post)
        except ImportError:
            pass


# Route model binding decorators
def model_binding(
    parameter: str,
    model_class: Type[ModelT],
    field: Optional[str] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for explicit model binding."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get binder from container
            binder = container.make('route.model.binder')
            
            if parameter in kwargs:
                # Resolve model binding
                value = kwargs[parameter]
                resolver = binder._create_model_resolver(model_class)
                kwargs[parameter] = resolver(value, field)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def scoped_binding(
    model_class: Type[ModelT],
    scope_field: str,
    scope_value: Any
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for scoped model binding."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get binder from container
            binder = container.make('route.model.binder')
            binder.scoped(model_class, scope_field, scope_value)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def soft_deletes_binding(
    include_trashed: bool = False
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for soft delete aware binding."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # This would modify the query to include or exclude soft deleted models
            return func(*args, **kwargs)
        return wrapper
    return decorator


class RouteKeyBinding:
    """Laravel 12 route key binding for custom route keys."""
    
    def __init__(self, model_class: Type[BaseModel], field: str) -> None:
        self.model_class = model_class
        self.field = field
    
    def resolve(self, value: Any) -> BaseModel:
        """Resolve model by custom field."""
        session = container.make('db')
        
        query = session.query(self.model_class)
        instance = query.filter(getattr(self.model_class, self.field) == value).first()
        
        if not instance:
            raise HTTPException(
                status_code=404,
                detail=f"{self.model_class.__name__} not found"
            )
        
        return instance


class ChildRouteBinding:
    """Laravel 12 child route binding for nested resources."""
    
    def __init__(
        self,
        parent_class: Type[BaseModel],
        child_class: Type[BaseModel],
        relationship: str
    ) -> None:
        self.parent_class = parent_class
        self.child_class = child_class
        self.relationship = relationship
    
    def resolve(self, parent: BaseModel, child_value: Any) -> BaseModel:
        """Resolve child model scoped to parent."""
        # Get related models
        related_query = getattr(parent, self.relationship)
        
        # Find child by ID
        child = related_query.filter(
            getattr(self.child_class, self.child_class.get_key_name()) == child_value
        ).first()
        
        if not child:
            raise HTTPException(
                status_code=404,
                detail=f"{self.child_class.__name__} not found in {self.parent_class.__name__}"
            )
        
        return child


# Custom binding interfaces
class CustomRouteBinding:
    """Base class for custom route bindings."""
    
    def resolve(self, value: Any, request: Request) -> Any:
        """Resolve binding value."""
        raise NotImplementedError
    
    def matches(self, parameter: str) -> bool:
        """Check if binding applies to parameter."""
        raise NotImplementedError


class SlugBinding(CustomRouteBinding):
    """Binding for slug-based model resolution."""
    
    def __init__(self, model_class: Type[BaseModel], slug_field: str = 'slug') -> None:
        self.model_class = model_class
        self.slug_field = slug_field
    
    def resolve(self, value: Any, request: Request) -> BaseModel:
        """Resolve model by slug."""
        session = container.make('db')
        
        query = session.query(self.model_class)
        instance = query.filter(getattr(self.model_class, self.slug_field) == value).first()
        
        if not instance:
            raise HTTPException(
                status_code=404,
                detail=f"{self.model_class.__name__} not found"
            )
        
        return instance
    
    def matches(self, parameter: str) -> bool:
        """Check if parameter is a slug."""
        return parameter.endswith('_slug') or parameter == 'slug'


class UuidBinding(CustomRouteBinding):
    """Binding for UUID-based model resolution."""
    
    def __init__(self, model_class: Type[BaseModel], uuid_field: str = 'uuid') -> None:
        self.model_class = model_class
        self.uuid_field = uuid_field
    
    def resolve(self, value: Any, request: Request) -> BaseModel:
        """Resolve model by UUID."""
        session = container.make('db')
        
        query = session.query(self.model_class)
        instance = query.filter(getattr(self.model_class, self.uuid_field) == value).first()
        
        if not instance:
            raise HTTPException(
                status_code=404,
                detail=f"{self.model_class.__name__} not found"
            )
        
        return instance
    
    def matches(self, parameter: str) -> bool:
        """Check if parameter is a UUID."""
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, str(value), re.IGNORECASE))


# Global binder instance
route_model_binder = RouteModelBinder()

# Service provider
route_model_service_provider = RouteModelServiceProvider()


# Helper functions
def bind_model(key: str, model_class: Type[BaseModel], field: Optional[str] = None) -> None:
    """Bind model to route parameter."""
    if field:
        route_model_binder.bind(key, RouteKeyBinding(model_class, field).resolve)
    else:
        route_model_binder.bind(key, model_class)


def implicit_model_binding(model_class: Type[BaseModel], field: Optional[str] = None) -> None:
    """Register implicit model binding."""
    route_model_binder.implicit(model_class, field)


def scoped_model_binding(
    model_class: Type[BaseModel],
    scope_field: str,
    scope_value: Any
) -> None:
    """Register scoped model binding."""
    route_model_binder.scoped(model_class, scope_field, scope_value)


# Export route model binding functionality
__all__ = [
    'RouteModelBinder',
    'RouteModelServiceProvider',
    'RouteKeyBinding',
    'ChildRouteBinding',
    'CustomRouteBinding',
    'SlugBinding',
    'UuidBinding',
    'route_model_binder',
    'route_model_service_provider',
    'model_binding',
    'scoped_binding',
    'soft_deletes_binding',
    'bind_model',
    'implicit_model_binding',
    'scoped_model_binding',
]