from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from fastapi import APIRouter, Depends
from functools import wraps
import json


@dataclass
class RouteGroup:
    """Route group configuration."""
    prefix: str = ""
    middleware: List[str] = field(default_factory=list)
    name: str = ""
    namespace: str = ""
    domain: str = ""
    where: Dict[str, str] = field(default_factory=dict)


@dataclass
class MiddlewareGroup:
    """Middleware group definition."""
    name: str
    middleware: List[Union[str, Callable[..., Any]]]


class RouteManager:
    """Laravel-style route manager."""
    
    def __init__(self) -> None:
        self.middleware_groups: Dict[str, MiddlewareGroup] = {}
        self.global_middleware: List[Union[str, Callable[..., Any]]] = []
        self.route_middleware: Dict[str, Union[str, Callable[..., Any]]] = {}
        self.current_group: Optional[RouteGroup] = None
        self.routers: List[APIRouter] = []
        
        # Register default middleware groups
        self._register_default_middleware_groups()
    
    def _register_default_middleware_groups(self) -> None:
        """Register default middleware groups."""
        self.middleware_groups["web"] = MiddlewareGroup(
            name="web",
            middleware=[
                "app.Http.Middleware.CORSMiddleware",
                "app.Http.Middleware.AuthMiddleware",
            ]
        )
        
        self.middleware_groups["api"] = MiddlewareGroup(
            name="api",
            middleware=[
                "app.Http.Middleware.CORSMiddleware",
                "app.RateLimiting.ThrottleMiddleware",
            ]
        )
        
        self.middleware_groups["auth"] = MiddlewareGroup(
            name="auth",
            middleware=[
                "app.Http.Middleware.AuthMiddleware",
            ]
        )
        
        self.middleware_groups["guest"] = MiddlewareGroup(
            name="guest",
            middleware=[
                # Middleware that ensures user is not authenticated
            ]
        )
    
    def middleware_group(self, name: str, middleware: List[Union[str, Callable[..., Any]]]) -> None:
        """Register a middleware group."""
        self.middleware_groups[name] = MiddlewareGroup(name, middleware)
    
    def route_middleware_alias(self, alias: str, middleware: Union[str, Callable[..., Any]]) -> None:
        """Register route middleware alias."""
        self.route_middleware[alias] = middleware
    
    def group(self, attributes: Dict[str, Any], routes: Callable[[APIRouter], None]) -> APIRouter:
        """Create a route group."""
        router = APIRouter()
        
        # Apply group attributes
        if "prefix" in attributes:
            # FastAPI doesn't have a prefix attribute, use include_router with prefix instead
            pass  # This would be handled when including the router
        
        if "middleware" in attributes:
            # Apply middleware to router
            middleware = attributes["middleware"]
            if isinstance(middleware, str):
                middleware = [middleware]
            
            for mw in middleware:
                if isinstance(mw, str) and mw in self.middleware_groups:
                    # Apply middleware group
                    group = self.middleware_groups[mw]
                    for group_mw in group.middleware:
                        self._apply_middleware_to_router(router, group_mw)
                else:
                    self._apply_middleware_to_router(router, mw)
        
        # Execute routes callback
        routes(router)
        
        self.routers.append(router)
        return router
    
    def _apply_middleware_to_router(self, router: APIRouter, middleware: Union[str, Callable[..., Any]]) -> None:
        """Apply middleware to router."""
        # This would need proper FastAPI middleware integration
        # For now, just store the middleware reference
        if not hasattr(router, '_middleware'):
            router._middleware = []  # type: ignore[attr-defined]
        router._middleware.append(middleware)  # type: ignore[attr-defined]
    
    def prefix(self, prefix: str) -> RouteGroupBuilder:
        """Create route group with prefix."""
        return RouteGroupBuilder(self).prefix(prefix)
    
    def middleware(self, *middleware: Union[str, Callable[..., Any]]) -> RouteGroupBuilder:
        """Create route group with middleware."""
        return RouteGroupBuilder(self).middleware(*middleware)
    
    def name(self, name: str) -> RouteGroupBuilder:
        """Create route group with name prefix."""
        return RouteGroupBuilder(self).name(name)
    
    def domain(self, domain: str) -> RouteGroupBuilder:
        """Create route group with domain."""
        return RouteGroupBuilder(self).domain(domain)
    
    def namespace(self, namespace: str) -> RouteGroupBuilder:
        """Create route group with namespace."""
        return RouteGroupBuilder(self).namespace(namespace)
    
    def where(self, parameters: Dict[str, str]) -> RouteGroupBuilder:
        """Create route group with parameter constraints."""
        return RouteGroupBuilder(self).where(parameters)


class RouteGroupBuilder:
    """Builder for route groups."""
    
    def __init__(self, route_manager: RouteManager) -> None:
        self.route_manager = route_manager
        self.attributes: Dict[str, Any] = {}
    
    def prefix(self, prefix: str) -> RouteGroupBuilder:
        """Set route prefix."""
        self.attributes["prefix"] = prefix
        return self
    
    def middleware(self, *middleware: Union[str, Callable[..., Any]]) -> RouteGroupBuilder:
        """Set middleware."""
        self.attributes["middleware"] = list(middleware)
        return self
    
    def name(self, name: str) -> RouteGroupBuilder:
        """Set name prefix."""
        self.attributes["name"] = name
        return self
    
    def domain(self, domain: str) -> RouteGroupBuilder:
        """Set domain."""
        self.attributes["domain"] = domain
        return self
    
    def namespace(self, namespace: str) -> RouteGroupBuilder:
        """Set namespace."""
        self.attributes["namespace"] = namespace
        return self
    
    def where(self, parameters: Dict[str, str]) -> RouteGroupBuilder:
        """Set parameter constraints."""
        self.attributes["where"] = parameters
        return self
    
    def group(self, routes: Callable[[APIRouter], None]) -> APIRouter:
        """Execute the route group."""
        return self.route_manager.group(self.attributes, routes)


class RouteCache:
    """Laravel-style route caching."""
    
    def __init__(self) -> None:
        self.cached_routes: Optional[Dict[str, Any]] = None
        self.cache_file = "storage/cache/routes.json"
    
    def cache_routes(self, routes: List[Dict[str, Any]]) -> bool:
        """Cache route definitions."""
        try:
            import os
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            with open(self.cache_file, 'w') as f:
                json.dump(routes, f, indent=2, default=str)
            
            self.cached_routes = {route['name']: route for route in routes if 'name' in route}
            return True
        except Exception:
            return False
    
    def get_cached_routes(self) -> Optional[Dict[str, Any]]:
        """Get cached route definitions."""
        if self.cached_routes is None:
            try:
                with open(self.cache_file, 'r') as f:
                    routes = json.load(f)
                    self.cached_routes = {route['name']: route for route in routes if 'name' in route}
            except (FileNotFoundError, json.JSONDecodeError):
                return None
        
        return self.cached_routes
    
    def clear_cache(self) -> bool:
        """Clear route cache."""
        try:
            import os
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
            self.cached_routes = None
            return True
        except Exception:
            return False
    
    def route_exists(self, name: str) -> bool:
        """Check if named route exists in cache."""
        cached = self.get_cached_routes()
        return cached is not None and name in cached
    
    def get_route_url(self, name: str, parameters: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get URL for named route."""
        cached = self.get_cached_routes()
        if cached and name in cached:
            route = cached[name]
            url = route.get('path', '')
            
            # Replace route parameters
            if parameters:
                for key, value in parameters.items():
                    url = url.replace(f"{{{key}}}", str(value))
            
            return url
        
        return None


# Global instances
route_manager = RouteManager()
route_cache = RouteCache()


def route_group(attributes: Dict[str, Any]) -> RouteGroupBuilder:
    """Create a route group."""
    builder = RouteGroupBuilder(route_manager)
    for key, value in attributes.items():
        setattr(builder, key, lambda v=value: getattr(builder, key)(v))
    return builder


def middleware_group(name: str, middleware: List[Union[str, Callable[..., Any]]]) -> None:
    """Register middleware group."""
    route_manager.middleware_group(name, middleware)


def route_middleware(alias: str, middleware: Union[str, Callable[..., Any]]) -> None:
    """Register route middleware alias."""
    route_manager.route_middleware_alias(alias, middleware)