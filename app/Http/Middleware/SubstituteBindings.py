from __future__ import annotations

from typing import Any, Dict, Optional, Callable, Awaitable, Type
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound

from app.Models.BaseModel import BaseModel


class SubstituteBindings(BaseHTTPMiddleware):
    """Laravel-style route model binding middleware."""
    
    def __init__(self, app: Any, db_session: Optional[Session] = None) -> None:
        super().__init__(app)
        self.db_session = db_session
        self.bindings: Dict[str, Type[BaseModel]] = {}
        self.custom_resolvers: Dict[str, Callable[[str, Session], Any]] = {}
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process route model binding."""
        # Get path parameters
        path_params = request.path_params
        
        if path_params and self.db_session:
            # Resolve model bindings
            resolved_models = {}
            
            for param_name, param_value in path_params.items():
                if param_name in self.bindings:
                    model_class = self.bindings[param_name]
                    try:
                        # Try to find the model by ID
                        model_instance = self._resolve_model(model_class, param_value)
                        resolved_models[param_name] = model_instance
                    except (NoResultFound, ValueError):
                        # Model not found, return 404
                        raise HTTPException(status_code=404, detail=f"{model_class.__name__} not found")
                
                elif param_name in self.custom_resolvers:
                    # Use custom resolver
                    resolver = self.custom_resolvers[param_name]
                    try:
                        resolved_models[param_name] = resolver(param_value, self.db_session)
                    except Exception:
                        raise HTTPException(status_code=404, detail="Resource not found")
            
            # Add resolved models to request state
            request.state.resolved_models = resolved_models
        
        response = await call_next(request)
        return response
    
    def _resolve_model(self, model_class: Type[BaseModel], param_value: str) -> BaseModel:
        """Resolve a model instance from a parameter value."""
        if not self.db_session:
            raise ValueError("Database session not available")
        
        # Try to get by ID (primary key)
        try:
            # Assume the parameter is the primary key
            instance = self.db_session.query(model_class).filter(
                model_class.id == param_value
            ).first()
            
            if instance:
                return instance
        except Exception:
            pass
        
        # Try to get by other unique fields if defined
        if hasattr(model_class, '__route_key_name__'):
            route_key = getattr(model_class, '__route_key_name__')
            if hasattr(model_class, route_key):
                instance = self.db_session.query(model_class).filter(
                    getattr(model_class, route_key) == param_value
                ).first()
                
                if instance:
                    return instance
        
        # Try slug if exists
        if hasattr(model_class, 'slug'):
            instance = self.db_session.query(model_class).filter(
                model_class.slug == param_value
            ).first()
            
            if instance:
                return instance
        
        raise NoResultFound(f"{model_class.__name__} with identifier '{param_value}' not found")
    
    def bind(self, parameter: str, model_class: Type[BaseModel]) -> SubstituteBindings:
        """Bind a route parameter to a model class."""
        self.bindings[parameter] = model_class
        return self
    
    def bind_custom(self, parameter: str, resolver: Callable[[str, Session], Any]) -> SubstituteBindings:
        """Bind a route parameter to a custom resolver function."""
        self.custom_resolvers[parameter] = resolver
        return self
    
    def get_binding(self, parameter: str) -> Optional[Type[BaseModel]]:
        """Get the model class bound to a parameter."""
        return self.bindings.get(parameter)
    
    def has_binding(self, parameter: str) -> bool:
        """Check if a parameter has a model binding."""
        return parameter in self.bindings or parameter in self.custom_resolvers
    
    def remove_binding(self, parameter: str) -> SubstituteBindings:
        """Remove a model binding."""
        self.bindings.pop(parameter, None)
        self.custom_resolvers.pop(parameter, None)
        return self


class RouteModelBinding:
    """Decorator for automatic route model binding setup."""
    
    @staticmethod
    def bind(parameter: str, model_class: Type[BaseModel]) -> Callable[..., Any]:
        """Decorator to automatically bind route parameters to models."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            # Store binding metadata on the function
            if not hasattr(func, '_route_bindings'):
                setattr(func, '_route_bindings', {})
            getattr(func, '_route_bindings')[parameter] = model_class
            return func
        return decorator
    
    @staticmethod
    def resolve(request: Request, parameter: str) -> Any:
        """Resolve a bound model from the request."""
        if hasattr(request.state, 'resolved_models'):
            return request.state.resolved_models.get(parameter)
        return None


def model_binding(parameter: str, model_class: Type[BaseModel]) -> Callable[..., Any]:
    """Decorator for route model binding."""
    return RouteModelBinding.bind(parameter, model_class)