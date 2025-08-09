from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional, Type, Callable, Union, Set, Tuple
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import inspect

from .AuthMiddleware import AuthMiddleware
from .PerformanceMiddleware import PerformanceMiddleware
from fastapi.middleware.cors import CORSMiddleware as CustomCORSMiddleware
from .ActivityLogMiddleware import ActivityLogMiddleware
from .CacheMiddleware import CacheMiddleware
from .MFAMiddleware import MFAMiddleware
from .BaseMiddleware import BaseMiddleware, MiddlewareGroup, MiddlewareConfig, MiddlewarePriority
import os


# Laravel 12 Middleware Registration
@dataclass
class MiddlewareRegistration:
    """Laravel 12 enhanced middleware registration."""
    name: str
    middleware_class: Type[Any]
    config: MiddlewareConfig = field(default_factory=MiddlewareConfig)
    parameters: str = ""
    tags: Set[str] = field(default_factory=set)
    group: Optional[str] = None
    singleton: bool = False
    instance: Optional[Any] = None


class MiddlewareManager:
    """Laravel 12 Enhanced Middleware Manager for FastAPI."""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Laravel 12 enhanced storage
        self.registrations: Dict[str, MiddlewareRegistration] = {}
        self.groups: Dict[str, MiddlewareGroup] = {}
        self.aliases: Dict[str, str] = {}
        self.global_middleware: List[str] = []
        self.route_middleware: Dict[str, Dict[str, Any]] = {}
        
        # Laravel 12 new features
        self.middleware_stack: List[str] = []
        self.terminable_middleware: List[str] = []
        self.excluded_middleware: Set[str] = set()
        self.middleware_parameters: Dict[str, str] = {}
        self.sorting_enabled: bool = True
        self._middleware_cache: Dict[str, Any] = {}
        self.conditional_middleware: List[Dict[str, Any]] = []
    
    @property
    def registered_middleware(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered middleware as a dictionary for backward compatibility."""
        return {
            name: {
                "enabled": reg.config.enabled,
                "priority": reg.config.priority,
                "terminable": reg.config.terminable,
                "class": reg.middleware_class,
                "config": reg.config.parameters
            }
            for name, reg in self.registrations.items()
        }
        
    def register(
        self,
        name: str,
        middleware_class: Type[Any],
        priority: int = 50,
        parameters: str = "",
        enabled: bool = True,
        terminable: bool = False,
        singleton: bool = False,
        tags: Optional[List[str]] = None,
        **config_options: Any
    ) -> 'MiddlewareManager':
        """Register middleware with Laravel 12 enhancements."""
        middleware_config = MiddlewareConfig(
            enabled=enabled,
            priority=priority,
            terminable=terminable,
            parameters=config_options
        )
        
        registration = MiddlewareRegistration(
            name=name,
            middleware_class=middleware_class,
            config=middleware_config,
            parameters=parameters,
            tags=set(tags or []),
            singleton=singleton
        )
        
        self.registrations[name] = registration
        
        if terminable:
            self.terminable_middleware.append(name)
        
        if parameters:
            self.middleware_parameters[name] = parameters
        
        self.logger.info(f"Registered middleware: {name} (priority: {priority})")
        return self
    
    # Laravel 12 Fluent Interface
    def append(self, *middleware: str) -> 'MiddlewareManager':
        """Append middleware to global stack (Laravel 12)."""
        for name in middleware:
            if name not in self.global_middleware:
                self.global_middleware.append(name)
        return self
    
    def prepend(self, *middleware: str) -> 'MiddlewareManager':
        """Prepend middleware to global stack (Laravel 12)."""
        for name in reversed(middleware):
            if name not in self.global_middleware:
                self.global_middleware.insert(0, name)
        return self
    
    def use(self, middleware_stack: List[str]) -> 'MiddlewareManager':
        """Manually define global middleware stack (Laravel 12)."""
        self.global_middleware = middleware_stack.copy()
        return self
    
    def group(self, name: str) -> MiddlewareGroup:
        """Get or create middleware group (Laravel 12)."""
        if name not in self.groups:
            self.groups[name] = MiddlewareGroup(name)
        return self.groups[name]
    
    def appendToGroup(self, group_name: str, *middleware: str) -> 'MiddlewareManager':
        """Append middleware to group (Laravel 12)."""
        group = self.group(group_name)
        for name in middleware:
            group.append(name)
        return self
    
    def prependToGroup(self, group_name: str, *middleware: str) -> 'MiddlewareManager':
        """Prepend middleware to group (Laravel 12)."""
        group = self.group(group_name)
        for name in reversed(middleware):
            group.prepend(name)
        return self
    
    def removeFromGroup(self, group_name: str, *middleware: str) -> 'MiddlewareManager':
        """Remove middleware from group (Laravel 12)."""
        if group_name in self.groups:
            group = self.groups[group_name]
            for name in middleware:
                group.remove(name)
        return self
    
    def replaceInGroup(self, group_name: str, old_middleware: str, new_middleware: str) -> 'MiddlewareManager':
        """Replace middleware in group (Laravel 12)."""
        if group_name in self.groups:
            self.groups[group_name].replace(old_middleware, new_middleware)
        return self
    
    # Laravel 12 Middleware Priority and Sorting
    def priority(self, middleware_priorities: Dict[str, int]) -> 'MiddlewareManager':
        """Set middleware priorities (Laravel 12)."""
        for name, priority in middleware_priorities.items():
            if name in self.registrations:
                self.registrations[name].config.priority = priority
        return self
    
    def withoutSorting(self) -> 'MiddlewareManager':
        """Disable automatic middleware sorting (Laravel 12)."""
        self.sorting_enabled = False
        return self
    
    def withSorting(self) -> 'MiddlewareManager':
        """Enable automatic middleware sorting (Laravel 12)."""
        self.sorting_enabled = True
        return self
    
    # Laravel 12 Middleware Parameters
    def withParameters(self, middleware_name: str, parameters: str) -> 'MiddlewareManager':
        """Set parameters for middleware (Laravel 12)."""
        if middleware_name in self.registrations:
            self.registrations[middleware_name].parameters = parameters
            self.middleware_parameters[middleware_name] = parameters
        return self
    
    def withoutParameters(self, middleware_name: str) -> 'MiddlewareManager':
        """Remove parameters from middleware (Laravel 12)."""
        if middleware_name in self.registrations:
            self.registrations[middleware_name].parameters = ""
            self.middleware_parameters.pop(middleware_name, None)
        return self
    
    # Laravel 12 Conditional Middleware
    def when(self, condition: Union[bool, Callable[[], bool]], *middleware: str) -> 'MiddlewareManager':
        """Register conditional middleware (Laravel 12)."""
        for name in middleware:
            if name in self.registrations:
                condition_func = condition if callable(condition) else lambda: condition
                config = self.registrations[name].config
                if config.conditions is None:
                    config.conditions = []
                config.conditions.append(condition_func)
        return self
    
    def unless(self, condition: Union[bool, Callable[[], bool]], *middleware: str) -> 'MiddlewareManager':
        """Register middleware that runs unless condition is true (Laravel 12)."""
        if callable(condition):
            inverted_condition: Callable[[], bool] = lambda: not condition()
        else:
            inverted_condition_bool: bool = not condition
            inverted_condition = lambda: inverted_condition_bool
        return self.when(inverted_condition, *middleware)
    
    # Laravel 12 Middleware Exclusion
    def except_middleware(self, *middleware: str) -> 'MiddlewareManager':
        """Exclude middleware from stack (Laravel 12)."""
        self.excluded_middleware.update(middleware)
        return self
    
    def remove(self, *middleware: str) -> 'MiddlewareManager':
        """Remove middleware from stack (Laravel 12)."""
        for name in middleware:
            if name in self.global_middleware:
                self.global_middleware.remove(name)
            self.excluded_middleware.add(name)
        return self
    
    def replace(self, old_middleware: str, new_middleware: str) -> 'MiddlewareManager':
        """Replace middleware in global stack (Laravel 12)."""
        if old_middleware in self.global_middleware:
            index = self.global_middleware.index(old_middleware)
            self.global_middleware[index] = new_middleware
        return self
    
    # Laravel 12 Middleware Aliases
    def alias(self, alias: str, middleware_name: str) -> 'MiddlewareManager':
        """Register middleware alias (Laravel 12)."""
        self.aliases[alias] = middleware_name
        return self
    
    def register_aliases(self, alias_dict: Dict[str, str]) -> 'MiddlewareManager':
        """Register multiple middleware aliases (Laravel 12)."""
        self.aliases.update(alias_dict)
        return self
    
    def register_global_middleware(self, middleware_names: List[str]) -> None:
        """Register middleware to be applied globally."""
        self.global_middleware.extend(middleware_names)
        self.logger.info(f"Registered global middleware: {middleware_names}")
    
    def register_group(self, name: str, middleware_list: List[str]) -> None:
        """Laravel-style middleware group registration."""
        group = self.group(name)
        group.middleware = list(middleware_list)  # Cast to proper type
        self.logger.info(f"Registered middleware group '{name}': {middleware_list}")
    
    
    def for_routes(self, pattern: str, middleware_names: List[str], methods: Optional[List[str]] = None) -> None:
        """Register middleware for specific route patterns."""
        self.route_middleware[pattern] = {
            "middleware": middleware_names,
            "methods": methods or ["*"]
        }
        self.logger.info(f"Registered route middleware for '{pattern}': {middleware_names}")
    
    def disable(self, middleware_name: str) -> None:
        """Disable a middleware."""
        if middleware_name in self.registrations:
            self.registrations[middleware_name].config.enabled = False
            self.logger.info(f"Disabled middleware: {middleware_name}")
    
    def enable(self, middleware_name: str) -> None:
        """Enable a middleware."""
        if middleware_name in self.registrations:
            self.registrations[middleware_name].config.enabled = True
            self.logger.info(f"Enabled middleware: {middleware_name}")
    
    def prepend_global(self, middleware_name: str) -> None:
        """Prepend middleware to global middleware list."""
        if middleware_name not in self.global_middleware:
            self.global_middleware.insert(0, middleware_name)
            self.logger.info(f"Prepended global middleware: {middleware_name}")
    
    def append_global(self, middleware_name: str) -> None:
        """Append middleware to global middleware list."""
        if middleware_name not in self.global_middleware:
            self.global_middleware.append(middleware_name)
            self.logger.info(f"Appended global middleware: {middleware_name}")
    
    def remove_global(self, middleware_name: str) -> None:
        """Remove middleware from global middleware list."""
        if middleware_name in self.global_middleware:
            self.global_middleware.remove(middleware_name)
            self.logger.info(f"Removed global middleware: {middleware_name}")
    
    def get_group_middleware(self, group_name: str) -> List[str]:
        """Get middleware list for a group."""
        group = self.groups.get(group_name)
        return [str(m) for m in group.middleware] if group else []
    
    def resolve_middleware_name(self, name: str) -> str:
        """Resolve middleware name through aliases."""
        return self.aliases.get(name, name)
    
    def get_conditional_middleware(self) -> List[str]:
        """Get middleware that should be applied based on conditions."""
        applicable_middleware = []
        
        for conditional in self.conditional_middleware:
            try:
                if conditional["condition"]():
                    applicable_middleware.extend(conditional["middleware"])
            except Exception as e:
                self.logger.error(f"Error evaluating middleware condition: {e}")
        
        return applicable_middleware
    
    def apply_middleware(self, app: FastAPI, config: Optional[Dict[str, Any]] = None) -> None:
        """Apply all registered middleware to the FastAPI app."""
        config = config or {}
        
        # Get all middleware to apply
        middleware_to_apply = self._resolve_all_middleware()
        
        # Apply middleware in reverse order (FastAPI applies them in reverse)
        for middleware_name in reversed(middleware_to_apply):
            if middleware_name not in self.registered_middleware:
                self.logger.warning(f"Middleware '{middleware_name}' not registered, skipping")
                continue
            
            middleware_info = self.registered_middleware[middleware_name]
            
            if not middleware_info["enabled"]:
                self.logger.debug(f"Skipping disabled middleware: {middleware_name}")
                continue
            
            middleware_class = middleware_info["class"]
            middleware_config = {**middleware_info["config"], **config.get(middleware_name, {})}
            
            try:
                if middleware_config:
                    app.add_middleware(middleware_class, **middleware_config)
                else:
                    app.add_middleware(middleware_class)
                
                self.logger.info(f"Applied middleware: {middleware_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to apply middleware {middleware_name}: {e}")
    
    def _resolve_all_middleware(self) -> List[str]:
        """Resolve all middleware including global, conditional, and group middleware."""
        all_middleware: set[str] = set()
        
        # Add explicitly ordered middleware
        all_middleware.update(self.registered_middleware)
        
        # Add global middleware
        all_middleware.update(self.global_middleware)
        
        # Add conditional middleware
        all_middleware.update(self.get_conditional_middleware())
        
        # Expand group middleware
        expanded_middleware = []
        for middleware_name in all_middleware:
            resolved_name = self.resolve_middleware_name(middleware_name)
            
            if resolved_name in self.groups:
                # It's a group, expand it
                group_middleware = self.get_group_middleware(resolved_name)
                expanded_middleware.extend(group_middleware)
            else:
                expanded_middleware.append(resolved_name)
        
        # Remove duplicates while preserving order
        unique_middleware = []
        seen = set()
        for middleware in expanded_middleware:
            if middleware not in seen:
                unique_middleware.append(middleware)
                seen.add(middleware)
        
        # Sort by priority
        return sorted(unique_middleware, key=lambda x: (
            self.registered_middleware.get(x, {}).get("priority", 100)
        ))
    
    def apply_route_middleware(self, router: Any, route_pattern: str) -> None:
        """Apply middleware specific to routes."""
        matching_middleware = []
        
        for pattern, route_config in self.route_middleware.items():
            if self._pattern_matches(route_pattern, pattern):
                matching_middleware.extend(route_config["middleware"])
        
        # Apply matching middleware to the router
        # This would need specific implementation based on your routing setup
        if matching_middleware:
            self.logger.info(f"Applied route middleware to '{route_pattern}': {matching_middleware}")
    
    def _pattern_matches(self, route: str, pattern: str) -> bool:
        """Check if a route matches a pattern."""
        import re
        
        # Convert pattern to regex
        pattern_regex = pattern.replace('*', '.*').replace('?', '.')
        return bool(re.match(f"^{pattern_regex}$", route))
    
    def get_middleware_info(self) -> Dict[str, Any]:
        """Get comprehensive information about registered middleware."""
        return {
            "registered_count": len(self.registered_middleware),
            "enabled_count": sum(1 for m in self.registered_middleware.values() if m["enabled"]),
            "middleware_order": list(self.registered_middleware.keys()),
            "global_middleware": self.global_middleware,
            "middleware_groups": self.groups,
            "middleware_aliases": self.aliases,
            "route_middleware": {k: v["middleware"] for k, v in self.route_middleware.items()},
            "conditional_middleware_count": len(self.conditional_middleware),
            "resolved_middleware": self._resolve_all_middleware(),
            "middleware_details": {
                name: {
                    "priority": info["priority"],
                    "enabled": info["enabled"],
                    "config_keys": list(info["config"].keys()),
                    "class_name": info["class"].__name__ if info["class"] else "Unknown"
                }
                for name, info in self.registered_middleware.items()
            }
        }


def create_default_middleware_manager() -> MiddlewareManager:
    """Create a Laravel-style middleware manager with default middleware and groups."""
    manager = MiddlewareManager()
    
    # Security and Performance Middleware (High Priority)
    manager.register(
        "trusted_host",
        TrustedHostMiddleware,
        priority=10,
        config={"allowed_hosts": ["localhost", "127.0.0.1", "*.example.com"]},
        enabled=False  # Enable in production
    )
    
    # Enhanced Performance Monitoring
    manager.register(
        "performance",
        PerformanceMiddleware,
        priority=20,
        config={
            "log_slow_requests": True,
            "slow_request_threshold": 1.0,
            "monitor_memory": True,
            "monitor_cpu": True,
            "track_database_queries": True
        }
    )
    
    # Enhanced Authentication
    manager.register(
        "enhanced_auth",
        AuthMiddleware,
        priority=30,
        config={
            "exclude_paths": [
                "/docs", "/redoc", "/openapi.json",
                "/health", "/metrics", "/favicon.ico",
                "/api/v1/auth/login", "/api/v1/auth/register"
            ]
        }
    )
    
    # TrimStrings Middleware
    from .TrimStrings import TrimStrings
    manager.register(
        "trim_strings",
        TrimStrings,
        priority=25,
        config={
            "except_keys": ["password", "password_confirmation", "current_password", "token"]
        }
    )
    
    # SubstituteBindings Middleware  
    from .SubstituteBindings import SubstituteBindings
    manager.register(
        "bindings",
        SubstituteBindings,
        priority=35,
        enabled=True
    )
    
    # ThrottleRequests Middleware
    from .ThrottleRequests import ThrottleRequests
    manager.register(
        "throttle",
        ThrottleRequests,
        priority=40,
        config={
            "max_attempts": 60,
            "decay_minutes": 1
        }
    )
    
    # RedirectIfAuthenticated Middleware
    from .RedirectIfAuthenticated import RedirectIfAuthenticated
    manager.register(
        "guest",
        RedirectIfAuthenticated,
        priority=45,
        config={
            "redirect_to": "/dashboard"
        },
        enabled=False  # Enable when needed
    )
    
    # MFA Middleware
    manager.register(
        "mfa",
        MFAMiddleware,
        priority=35,
        enabled=True
    )
    
    # Activity Logging
    manager.register(
        "activity_log",
        ActivityLogMiddleware,
        priority=40,
        config={
            "log_requests": True,
            "log_responses": True,
            "exclude_paths": ["/health", "/metrics"]
        }
    )
    
    # Custom CORS (if needed over built-in)
    manager.register(
        "custom_cors",
        CustomCORSMiddleware,
        priority=50,
        enabled=False  # Use built-in CORS by default
    )
    
    # Caching Middleware
    manager.register(
        "cache",
        CacheMiddleware,
        priority=60,
        config={
            "cache_control_max_age": 300,
            "enable_etag": True
        }
    )
    
    # Compression (Low Priority)
    manager.register(
        "gzip",
        GZipMiddleware,
        priority=90,
        config={"minimum_size": 1000}
    )
    
    # Register middleware aliases (Laravel-style)
    manager.alias("auth", "enhanced_auth")
    manager.alias("throttle", "rate_limit")
    manager.alias("cors", "custom_cors")
    manager.alias("log", "activity_log")
    
    # Register middleware groups (Laravel-style)
    web_group = manager.group("web")
    for middleware in ["trim_strings", "performance", "bindings", "enhanced_auth", "activity_log", "cache"]:
        web_group.append(middleware)
    
    api_group = manager.group("api")
    for middleware in ["trim_strings", "performance", "bindings", "enhanced_auth", "throttle", "activity_log", "cors"]:
        api_group.append(middleware)
    
    admin_group = manager.group("admin")
    for middleware in ["web", "mfa", "trusted_host"]:  # Include web group
        admin_group.append(middleware)
    
    public_group = manager.group("public")
    for middleware in ["performance", "cache", "gzip"]:
        public_group.append(middleware)
    
    # Register global middleware
    manager.register_global_middleware([
        "performance",
        "enhanced_auth"
    ])
    
    # Register conditional middleware
    manager.when(
        lambda: os.getenv("APP_DEBUG", "false").lower() == "true",
        "activity_log"
    )
    
    manager.unless(
        lambda: os.getenv("APP_ENV", "production") == "production",
        "trusted_host"
    )
    
    # Register route-specific middleware
    manager.for_routes("/api/v1/admin/*", ["admin"])
    manager.for_routes("/api/v1/auth/*", ["public"])
    manager.for_routes("/api/v1/*", ["api"])
    manager.for_routes("/docs*", ["public"])
    manager.for_routes("/health*", ["public"])
    
    return manager


def apply_cors_middleware(app: FastAPI, config: Optional[Dict[str, Any]] = None) -> None:
    """Apply CORS middleware with default configuration."""
    cors_config = {
        "allow_origins": ["http://localhost:3000", "http://localhost:8080"],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": [
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-CSRF-Token",
            "X-API-Key"
        ],
        "expose_headers": [
            "X-Response-Time",
            "X-CPU-Time",
            "X-Performance-Class",
            "X-DB-Query-Count",
            "X-DB-Query-Time"
        ]
    }
    
    if config:
        cors_config.update(config)
    
    app.add_middleware(CORSMiddleware, **cors_config)


def setup_production_middleware(app: FastAPI) -> None:
    """Setup middleware configuration optimized for production."""
    manager = create_default_middleware_manager()
    
    # Enable security middleware for production
    manager.enable("trusted_host")
    if "trusted_host" in manager.registrations:
        trusted_host_config = manager.registrations["trusted_host"].config
        if trusted_host_config.parameters is None:
            trusted_host_config.parameters = {}
        trusted_host_config.parameters["allowed_hosts"] = [
            "yourdomain.com", "*.yourdomain.com", "api.yourdomain.com"
        ]
    
    # Configure performance monitoring for production
    if "performance" in manager.registrations:
        performance_config = manager.registrations["performance"].config
        if performance_config.parameters is None:
            performance_config.parameters = {}
        performance_config.parameters.update({
        "slow_request_threshold": 2.0,  # More lenient in production
        "monitor_memory": False,  # Disable heavy monitoring in production
        "monitor_cpu": False
    })
    
    # Apply CORS for production
    apply_cors_middleware(app, {
        "allow_origins": ["https://yourdomain.com", "https://app.yourdomain.com"],
        "allow_credentials": True
    })
    
    # Apply all middleware
    manager.apply_middleware(app)


def setup_development_middleware(app: FastAPI) -> None:
    """Setup middleware configuration optimized for development."""
    manager = create_default_middleware_manager()
    
    # Disable security middleware for development
    manager.disable("trusted_host")
    
    # Enable verbose monitoring for development
    if "performance" in manager.registrations:
        performance_config = manager.registrations["performance"].config
        if performance_config.parameters is None:
            performance_config.parameters = {}
        performance_config.parameters.update({
        "log_slow_requests": True,
        "slow_request_threshold": 0.5,  # More strict in development
        "monitor_memory": True,
        "monitor_cpu": True,
        "track_database_queries": True
    })
    
    # Apply permissive CORS for development
    apply_cors_middleware(app, {
        "allow_origins": ["*"],  # Allow all origins in development
        "allow_credentials": True
    })
    
    # Apply all middleware
    manager.apply_middleware(app)


# Global middleware manager instance
middleware_manager = create_default_middleware_manager()


def get_middleware_stats() -> Dict[str, Any]:
    """Get comprehensive middleware statistics."""
    return {
        "middleware_info": middleware_manager.get_middleware_info(),
        "performance_stats": {
            # This would be populated by the PerformanceMiddleware
            "requests_processed": 0,
            "avg_response_time": 0.0,
            "slow_requests": 0
        },
        "security_stats": {
            # This would be populated by security middleware
            "auth_attempts": 0,
            "failed_auth": 0,
            "blocked_requests": 0
        }
    }


class MiddlewareHealthChecker:
    """Health checker for middleware components."""
    
    def __init__(self, manager: MiddlewareManager):
        self.manager = manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def check_middleware_health(self) -> Dict[str, Any]:
        """Check the health of all middleware components."""
        health_status: Dict[str, Any] = {
            "overall_status": "healthy",
            "middleware_status": {},
            "issues": [],
            "recommendations": []
        }
        
        for name, info in self.manager.registered_middleware.items():
            if not info["enabled"]:
                continue
                
            try:
                # Basic health check - ensure middleware class is available
                middleware_class = info["class"]
                if not middleware_class:
                    health_status["middleware_status"][name] = "error"
                    health_status["issues"].append(f"Middleware {name} class not found")
                else:
                    health_status["middleware_status"][name] = "healthy"
                    
            except Exception as e:
                health_status["middleware_status"][name] = "error"
                health_status["issues"].append(f"Middleware {name} error: {str(e)}")
        
        # Determine overall status
        if health_status["issues"]:
            health_status["overall_status"] = "degraded" if len(health_status["issues"]) < 3 else "unhealthy"
        
        # Add recommendations
        enabled_count = sum(1 for info in self.manager.registered_middleware.values() if info["enabled"])
        if enabled_count > 10:
            health_status["recommendations"].append("Consider reducing middleware count for better performance")
        
        return health_status


# Global health checker
health_checker = MiddlewareHealthChecker(middleware_manager)