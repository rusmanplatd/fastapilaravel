from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Callable, Union, Type, get_type_hints, final
from dataclasses import dataclass, field
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.routing import APIRoute
from functools import wraps
import json
import time
import hashlib
import asyncio
from pathlib import Path


@dataclass
class RouteGroup:
    """Enhanced route group configuration."""
    prefix: str = ""
    middleware: List[str] = field(default_factory=list)
    name: str = ""
    namespace: str = ""
    domain: str = ""
    where: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    rate_limit: Optional[Dict[str, Any]] = None
    cache_ttl: Optional[int] = None
    auth_required: bool = False
    permissions: List[str] = field(default_factory=list)


@dataclass
class MiddlewareGroup:
    """Middleware group definition."""
    name: str
    middleware: List[Union[str, Callable[..., Any]]]


@dataclass
class RouteInfo:
    """Enhanced route information for caching and analysis."""
    name: str
    path: str
    method: str
    handler: Callable[..., Any]
    middleware: List[str]
    auth_required: bool
    permissions: List[str]
    rate_limit: Optional[Dict[str, Any]]
    cache_ttl: Optional[int]
    tags: List[str]
    created_at: float
    last_accessed: float
    access_count: int = 0
    avg_response_time: float = 0.0


class RouteMetrics:
    """Route performance and usage metrics."""
    
    def __init__(self) -> None:
        self.route_stats: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def track_route_access(self, route_name: str, response_time: float) -> None:
        """Track route access and performance."""
        if route_name not in self.route_stats:
            self.route_stats[route_name] = {
                "access_count": 0,
                "total_response_time": 0.0,
                "avg_response_time": 0.0,
                "min_response_time": float('inf'),
                "max_response_time": 0.0,
                "last_accessed": time.time()
            }
        
        stats = self.route_stats[route_name]
        stats["access_count"] += 1
        stats["total_response_time"] += response_time
        stats["avg_response_time"] = stats["total_response_time"] / stats["access_count"]
        stats["min_response_time"] = min(stats["min_response_time"], response_time)
        stats["max_response_time"] = max(stats["max_response_time"], response_time)
        stats["last_accessed"] = time.time()
    
    def get_route_stats(self, route_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific route."""
        return self.route_stats.get(route_name)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get all route statistics."""
        return self.route_stats.copy()
    
    def get_top_routes(self, by: str = "access_count", limit: int = 10) -> List[Dict[str, Any]]:
        """Get top routes by specified metric."""
        if by not in ["access_count", "avg_response_time", "max_response_time"]:
            by = "access_count"
        
        sorted_routes = sorted(
            [(name, stats) for name, stats in self.route_stats.items()],
            key=lambda x: x[1][by],
            reverse=True
        )
        
        return [
            {"route_name": name, **stats}
            for name, stats in sorted_routes[:limit]
        ]


@final
class RouteManager:
    """Enhanced Laravel-style route manager with advanced features."""
    
    def __init__(self) -> None:
        self.middleware_groups: Dict[str, MiddlewareGroup] = {}
        self.global_middleware: List[Union[str, Callable[..., Any]]] = []
        self.route_middleware: Dict[str, Union[str, Callable[..., Any]]] = {}
        self.current_group: Optional[RouteGroup] = None
        self.routers: List[APIRouter] = []
        self.routes: Dict[str, RouteInfo] = {}
        self.route_metrics = RouteMetrics()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Enhanced features
        self.route_cache: Dict[str, Any] = {}
        self.auto_route_discovery = True
        self.route_versioning = True
        self.api_documentation = True
        
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
    
    def register_route(
        self, 
        name: str, 
        path: str, 
        method: str, 
        handler: Callable[..., Any],
        **kwargs: Any
    ) -> None:
        """Register a route with enhanced metadata."""
        route_info = RouteInfo(
            name=name,
            path=path,
            method=method,
            handler=handler,
            middleware=kwargs.get('middleware', []),
            auth_required=kwargs.get('auth_required', False),
            permissions=kwargs.get('permissions', []),
            rate_limit=kwargs.get('rate_limit'),
            cache_ttl=kwargs.get('cache_ttl'),
            tags=kwargs.get('tags', []),
            created_at=time.time(),
            last_accessed=time.time()
        )
        
        self.routes[name] = route_info
        self.logger.info(f"Registered route: {method} {path} -> {name}")
    
    def get_route(self, name: str) -> Optional[RouteInfo]:
        """Get route information by name."""
        return self.routes.get(name)
    
    def get_routes_by_tag(self, tag: str) -> List[RouteInfo]:
        """Get all routes with a specific tag."""
        return [route for route in self.routes.values() if tag in route.tags]
    
    
    def get_routes_requiring_auth(self) -> List[RouteInfo]:
        """Get all routes that require authentication."""
        return [route for route in self.routes.values() if route.auth_required]
    
    def get_deprecated_routes(self) -> List[RouteInfo]:
        """Get all deprecated routes."""
        return [route for route in self.routes.values() if getattr(route, 'deprecated', False)]
    
    def create_route_decorator(
        self, 
        method: str, 
        path: str, 
        name: Optional[str] = None,
        **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Create a route decorator with enhanced features."""
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            route_name = name or f"{func.__name__}_{method.lower()}"
            
            # Register the route
            self.register_route(route_name, path, method, func, **kwargs)
            
            # Create wrapper with metrics tracking
            @wraps(func)
            async def wrapper(*args: Any, **func_kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    result = await func(*args, **func_kwargs)
                    response_time = time.time() - start_time
                    self.route_metrics.track_route_access(route_name, response_time)
                    return result
                except Exception as e:
                    response_time = time.time() - start_time
                    self.route_metrics.track_route_access(route_name, response_time)
                    raise
            
            return wrapper
        return decorator
    
    def auto_discover_routes(self, module_path: str) -> None:
        """Automatically discover routes from a module path."""
        if not self.auto_route_discovery:
            return
            
        try:
            # This would implement automatic route discovery
            # from controller classes and methods
            self.logger.info(f"Auto-discovering routes from: {module_path}")
            # Implementation would scan for controller classes and methods
            # with route decorators or annotations
        except Exception as e:
            self.logger.error(f"Failed to auto-discover routes: {e}")
    
    def generate_route_map(self) -> Dict[str, Any]:
        """Generate a comprehensive route map."""
        return {
            "routes": {
                name: {
                    "path": route.path,
                    "method": route.method,
                    "auth_required": route.auth_required,
                    "permissions": route.permissions,
                    "tags": route.tags,
                    "middleware": route.middleware,
                    "cache_ttl": route.cache_ttl,
                    "rate_limit": route.rate_limit
                }
                for name, route in self.routes.items()
            },
            "middleware_groups": {
                name: {
                    "middleware": [str(mw) for mw in group.middleware]
                }
                for name, group in self.middleware_groups.items()
            },
            "metrics": self.route_metrics.get_all_stats()
        }
    
    def get_route_url(self, name: str, **params: Any) -> Optional[str]:
        """Get URL for named route with parameters."""
        route = self.get_route(name)
        if not route:
            return None
        
        url = route.path
        
        # Replace route parameters
        for param_name, param_value in params.items():
            url = url.replace(f"{{{param_name}}}", str(param_value))
        
        return url
    
    def validate_routes(self) -> List[Dict[str, Any]]:
        """Validate all registered routes for common issues."""
        issues = []
        
        for name, route in self.routes.items():
            
            # Check for routes without authentication that might need it
            if any(perm in route.path for perm in ["/admin", "/management", "/settings"]):
                if not route.auth_required:
                    issues.append({
                        "type": "security",
                        "route": name,
                        "message": f"Route {name} appears to need authentication but doesn't require it",
                        "severity": "warning"
                    })
            
            # Check for missing rate limits on public endpoints
            if not route.auth_required and not route.rate_limit:
                issues.append({
                    "type": "performance",
                    "route": name,
                    "message": f"Public route {name} has no rate limiting",
                    "severity": "info"
                })
        
        return issues
    
    def export_openapi_spec(self) -> Dict[str, Any]:
        """Export routes as OpenAPI specification."""
        if not self.api_documentation:
            return {}
        
        spec: Dict[str, Any] = {
            "openapi": "3.0.0",
            "info": {
                "title": "API Documentation",
                "version": "1.0.0",
                "description": "Auto-generated API documentation"
            },
            "paths": {}
        }
        
        for name, route in self.routes.items():
            if route.path not in spec["paths"]:
                spec["paths"][route.path] = {}
            
            spec["paths"][route.path][route.method.lower()] = {
                "operationId": name,
                "tags": route.tags,
                "security": [{"bearerAuth": []}] if route.auth_required else [],
                "summary": f"{route.method} {route.path}",
                "responses": {
                    "200": {"description": "Successful response"}
                }
            }
        
        return spec


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
            url = str(route.get('path', ''))
            
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