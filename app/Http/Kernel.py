from __future__ import annotations

from typing import Dict, List, Any, Optional, Callable, Union, Type
from fastapi import FastAPI, Request, Response
from app.Http.Middleware.MiddlewareManager import MiddlewareManager, create_default_middleware_manager
from app.Http.Middleware.AuthMiddleware import AuthMiddleware
from app.Http.Middleware.PerformanceMiddleware import PerformanceMiddleware
from app.Http.Middleware.ActivityLogMiddleware import ActivityLogMiddleware
from app.Http.Middleware.CacheMiddleware import CacheMiddleware
from app.Http.Middleware.MFAMiddleware import MFAMiddleware
try:
    from app.Http.Middleware.CORSMiddleware import FastAPICORSMiddleware
except ImportError:
    from fastapi.middleware.cors import CORSMiddleware as FastAPICORSMiddleware  
from app.Http.Middleware.ThrottleRequests import ThrottleRequests
from app.Http.Middleware.TrimStrings import TrimStrings
from app.Http.Middleware.TrustProxies import TrustProxies
from app.Http.Middleware.EncryptCookies import EncryptCookies
from app.Http.Middleware.SessionMiddleware import SessionMiddleware
from app.Support.Config import config
import logging


class HttpKernel:
    """
    Laravel-style HTTP Kernel.
    
    The HTTP kernel defines the middleware stack for the application,
    similar to Laravel's app/Http/Kernel.php.
    """
    
    # The application's global HTTP middleware stack
    # These middleware are run during every request to your application
    middleware: List[str] = [
        'trusted_host',
        'cors',
        'trim_strings',
        'performance',
    ]
    
    # The application's route middleware groups
    middleware_groups: Dict[str, List[str]] = {
        'web': [
            'encrypt_cookies',
            'session',
            'auth',
        ],
        
        'api': [
            'throttle',
            'auth',
            'log',
        ]
    }
    
    # The application's route middleware
    # These middleware may be assigned to groups or used individually
    route_middleware: Dict[str, str] = {
        'auth': 'auth',
        'throttle': 'throttle',
        'mfa': 'mfa',
        'cache': 'cache',
        'log': 'log',
    }
    
    # The priority-sorted list of middleware
    # This forces non-global middleware to always be in the given order
    middleware_priority: List[str] = [
        'trusted_host',
        'cors',
        'session',
        'auth',
        'throttle',
        'mfa',
    ]
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.middleware_manager = create_default_middleware_manager()
        self.middleware_priority: List[str] = []
        self.route_middleware: Dict[str, str] = {}
        self.middleware_groups: Dict[str, List[str]] = {}
        
        # Initialize default configurations
        self._setup_default_middleware()
        self._setup_middleware_groups()
        self._setup_route_middleware()
    
    def _setup_default_middleware(self) -> None:
        """Setup Laravel-style default middleware configuration."""
        
        # The global middleware stack that runs on every request
        self.middleware = [
            'performance',
            'trusted_host',
            'cors'
        ]
        
        # Middleware priority (lower number = higher priority)
        self.middleware_priority = [
            'trusted_host',      # 10 - Security first
            'cors',              # 20 - CORS handling
            'performance',       # 30 - Performance monitoring
            'throttle',          # 40 - Rate limiting
            'auth',              # 50 - Authentication
            'mfa',               # 60 - Multi-factor authentication
            'verified',          # 70 - Email verification
            'cache',             # 80 - Response caching
            'log',               # 90 - Activity logging
            'gzip'               # 100 - Compression (last)
        ]
    
    def _setup_middleware_groups(self) -> None:
        """Setup Laravel-style middleware groups."""
        
        self.middleware_groups = {
            'web': [
                'performance',
                'auth',
                'cache'
            ],
            
            'api': [
                'performance',
                'throttle:60,1',  # 60 requests per minute
                'auth:sanctum',
                'log'
            ],
            
            'admin': [
                'web',  # Inherit from web group
                'auth:admin',
                'mfa',
                'verified'
            ],
            
            'public': [
                'performance',
                'cache',
                'gzip'
            ],
            
            'secure': [
                'trusted_host',
                'auth',
                'mfa',
                'verified'
            ]
        }
    
    def _setup_route_middleware(self) -> None:
        """Setup Laravel-style route middleware aliases."""
        
        self.route_middleware = {
            # Authentication
            'auth': 'enhanced_auth',
            'auth.basic': 'auth:basic',
            'auth.session': 'auth:session',
            
            # Authorization
            'can': 'permission',
            'role': 'role',
            
            # Multi-factor authentication
            'mfa': 'mfa',
            'mfa.required': 'mfa:required',
            
            # Rate limiting
            'throttle': 'rate_limit',
            'throttle.login': 'rate_limit:login',
            
            # Caching
            'cache': 'cache',
            'cache.headers': 'cache:headers',
            
            # Content
            'cors': 'custom_cors',
            'gzip': 'gzip',
            
            # Security
            'verified': 'email.verified',
            'signed': 'signed.route',
            
            # Logging
            'log': 'activity_log',
            
            # Performance
            'monitor': 'performance'
        }
    
    def middleware_groups_list(self) -> Dict[str, List[str]]:
        """Get all middleware groups."""
        return self.middleware_groups.copy()
    
    def route_middleware_map(self) -> Dict[str, Any]:
        """Get route middleware mappings."""
        return self.route_middleware.copy()
    
    def global_middleware_list(self) -> List[str]:
        """Get global middleware stack."""
        return self.middleware.copy()
    
    def priority_sorted_middleware(self) -> List[str]:
        """Get middleware sorted by priority."""
        return self.middleware_priority.copy()
    
    def register_middleware(self, name: str, middleware: Union[Type[Any], str], priority: int = 50) -> None:
        """Register a new middleware."""
        if isinstance(middleware, str):
            # String reference - register as alias
            self.middleware_manager.alias(name, middleware)
        else:
            # Class reference - register as middleware
            self.middleware_manager.register(
                name=name,
                middleware_class=middleware,
                priority=priority
            )
        
        if name not in self.middleware_priority:
            # Insert at appropriate position based on priority
            inserted = False
            for i, existing_middleware in enumerate(self.middleware_priority):
                existing_priority = self.get_middleware_priority(existing_middleware)
                if priority < existing_priority:
                    self.middleware_priority.insert(i, name)
                    inserted = True
                    break
            
            if not inserted:
                self.middleware_priority.append(name)
    
    def get_middleware_priority(self, middleware_name: str) -> int:
        """Get priority for a middleware."""
        middleware_info = self.middleware_manager.registered_middleware.get(middleware_name)
        if middleware_info:
            priority = middleware_info.get('priority', 50)
            return int(priority) if priority is not None else 50
        return 50
    
    def add_middleware_group(self, name: str, middleware: List[str]) -> None:
        """Add a middleware group."""
        self.middleware_groups[name] = middleware
        self.middleware_manager.register_group(name, middleware)
    
    def prepend_middleware_group(self, group: str, middleware: str) -> None:
        """Prepend middleware to a group."""
        if group in self.middleware_groups:
            if middleware not in self.middleware_groups[group]:
                self.middleware_groups[group].insert(0, middleware)
                self.middleware_manager.register_group(group, self.middleware_groups[group])
    
    def append_middleware_group(self, group: str, middleware: str) -> None:
        """Append middleware to a group."""
        if group in self.middleware_groups:
            if middleware not in self.middleware_groups[group]:
                self.middleware_groups[group].append(middleware)
                self.middleware_manager.register_group(group, self.middleware_groups[group])
    
    def replace_middleware_in_group(self, group: str, old_middleware: str, new_middleware: str) -> None:
        """Replace middleware in a group."""
        if group in self.middleware_groups and old_middleware in self.middleware_groups[group]:
            index = self.middleware_groups[group].index(old_middleware)
            self.middleware_groups[group][index] = new_middleware
            self.middleware_manager.register_group(group, self.middleware_groups[group])
    
    def remove_middleware_from_group(self, group: str, middleware: str) -> None:
        """Remove middleware from a group."""
        if group in self.middleware_groups and middleware in self.middleware_groups[group]:
            self.middleware_groups[group].remove(middleware)
            self.middleware_manager.register_group(group, self.middleware_groups[group])
    
    def alias_middleware(self, alias: str, middleware: str) -> None:
        """Create an alias for middleware."""
        self.route_middleware[alias] = middleware
        self.middleware_manager.alias(alias, middleware)
    
    def prepend_global_middleware(self, middleware: str) -> None:
        """Prepend to global middleware."""
        if middleware not in self.middleware:
            self.middleware.insert(0, middleware)
            self.middleware_manager.prepend_global(middleware)
    
    def append_global_middleware(self, middleware: str) -> None:
        """Append to global middleware."""
        if middleware not in self.middleware:
            self.middleware.append(middleware)
            self.middleware_manager.append_global(middleware)
    
    def remove_global_middleware(self, middleware: str) -> None:
        """Remove from global middleware."""
        if middleware in self.middleware:
            self.middleware.remove(middleware)
            self.middleware_manager.remove_global(middleware)
    
    def disable_middleware(self, middleware: str) -> None:
        """Disable a middleware."""
        self.middleware_manager.disable(middleware)
    
    def enable_middleware(self, middleware: str) -> None:
        """Enable a middleware."""
        self.middleware_manager.enable(middleware)
    
    def when_environment(self, environments: Union[str, List[str]], middleware: List[str]) -> None:
        """Register middleware for specific environments."""
        if isinstance(environments, str):
            environments = [environments]
        
        current_env = config.get('app.environment', 'production')
        
        if current_env in environments:
            for mw in middleware:
                self.append_global_middleware(mw)
    
    def unless_environment(self, environments: Union[str, List[str]], middleware: List[str]) -> None:
        """Register middleware unless in specific environments."""
        if isinstance(environments, str):
            environments = [environments]
        
        current_env = config.get('app.environment', 'production')
        
        if current_env not in environments:
            for mw in middleware:
                self.append_global_middleware(mw)
    
    def when_config(self, config_key: str, middleware: List[str], value: Any = True) -> None:
        """Register middleware based on configuration."""
        if config.get(config_key) == value:
            for mw in middleware:
                self.append_global_middleware(mw)
    
    def bootstrap(self, app: FastAPI) -> None:
        """Bootstrap the HTTP kernel with the FastAPI app."""
        # Apply environment-specific middleware
        self._apply_environment_middleware()
        
        # Apply configuration-based middleware
        self._apply_config_middleware()
        
        # Apply all middleware to the app
        self.middleware_manager.apply_middleware(app)
        
        self.logger.info("HTTP Kernel bootstrapped successfully")
    
    def _apply_environment_middleware(self) -> None:
        """Apply middleware based on environment."""
        # Development-specific middleware
        self.when_environment('local', ['log', 'monitor'])
        self.when_environment('development', ['log', 'monitor'])
        
        # Production-specific middleware
        self.when_environment('production', ['trusted_host', 'cache'])
        
        # Testing-specific middleware
        self.unless_environment('testing', ['throttle'])
    
    def _apply_config_middleware(self) -> None:
        """Apply middleware based on configuration."""
        # Enable middleware based on config
        self.when_config('app.debug', ['log'], True)
        self.when_config('auth.mfa.enabled', ['mfa'], True)
        self.when_config('cache.enabled', ['cache'], True)
        self.when_config('cors.enabled', ['cors'], True)
    
    def get_kernel_info(self) -> Dict[str, Any]:
        """Get comprehensive kernel information."""
        return {
            'global_middleware': self.middleware,
            'middleware_groups': self.middleware_groups,
            'route_middleware': list(self.route_middleware.keys()),
            'middleware_priority': self.middleware_priority,
            'manager_info': self.middleware_manager.get_middleware_info()
        }
    
    def validate_middleware_stack(self) -> Dict[str, Any]:
        """Validate the middleware stack configuration."""
        validation_result: Dict[str, Any] = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        # Check for duplicate middleware in global stack
        seen = set()
        for middleware in self.middleware:
            if middleware in seen:
                validation_result['warnings'].append(f"Duplicate middleware '{middleware}' in global stack")
            seen.add(middleware)
        
        # Check for missing middleware references
        all_referenced = set(self.middleware)
        for group_middleware in self.middleware_groups.values():
            all_referenced.update(group_middleware)
        
        for middleware in all_referenced:
            if middleware not in self.middleware_manager.registered_middleware:
                validation_result['errors'].append(f"Referenced middleware '{middleware}' not registered")
                validation_result['valid'] = False
        
        # Performance recommendations
        if len(self.middleware) > 15:
            validation_result['recommendations'].append(
                "Consider reducing global middleware count for better performance"
            )
        
        # Security recommendations
        if 'trusted_host' not in self.middleware:
            validation_result['recommendations'].append(
                "Consider adding 'trusted_host' middleware for production security"
            )
        
        return validation_result


# Global HTTP Kernel instance
kernel = HttpKernel()


def get_kernel() -> HttpKernel:
    """Get the global HTTP kernel instance."""
    return kernel


# Laravel-style middleware decorators
def middleware(*middleware_list: str) -> Callable[..., Any]:
    """Decorator to apply middleware to a route function."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # This would need to be integrated with your routing system
        func.middleware = list(middleware_list)  # type: ignore
        return func
    return decorator


def middleware_group(group: str) -> Callable[..., Any]:
    """Decorator to apply a middleware group to a route function."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        group_middleware = kernel.middleware_groups.get(group, [])
        func.middleware = group_middleware  # type: ignore
        return func
    return decorator