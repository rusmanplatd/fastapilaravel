from __future__ import annotations

from typing import Callable, Awaitable, Dict, List, Optional, Union, Type, TypeVar, Protocol, Any
from app.Types.JsonTypes import JsonObject, JsonValue
from fastapi import Request, Response
from abc import ABC, abstractmethod
import asyncio
import inspect
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T', bound='BaseMiddleware')


# Laravel 12 Middleware Priority System
class MiddlewarePriority(Enum):
    """Laravel 12 middleware priority levels."""
    SECURITY = 10
    AUTHENTICATION = 20
    AUTHORIZATION = 30
    VALIDATION = 40
    THROTTLING = 50
    CACHING = 60
    TRANSFORMATION = 70
    LOGGING = 80
    COMPRESSION = 90


# Laravel 12 Middleware Configuration
@dataclass
class MiddlewareConfig:
    """Laravel 12 middleware configuration."""
    enabled: bool = True
    priority: int = 50
    terminable: bool = False
    parameters: Optional[Dict[str, Any]] = None
    conditions: Optional[List[Callable[[], bool]]] = None
    except_routes: Optional[List[str]] = None
    only_routes: Optional[List[str]] = None
    
    def __post_init__(self) -> None:
        if self.parameters is None:
            self.parameters = {}
        if self.conditions is None:
            self.conditions = []
        if self.except_routes is None:
            self.except_routes = []
        if self.only_routes is None:
            self.only_routes = []


# Laravel 12 Middleware Interface
class MiddlewareInterface(Protocol):
    """Enhanced middleware interface for Laravel 12."""
    
    async def handle(self, request: Request, next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Handle the request."""
        ...
    
    def terminate(self, request: Request, response: Response) -> None:
        """Perform cleanup after response is sent."""
        ...
    
    def shouldRun(self, request: Request) -> bool:
        """Determine if middleware should run for this request."""
        ...


# Laravel 12 Enhanced Middleware Parameters
class MiddlewareParameters:
    """Laravel 12 middleware parameter handler."""
    
    def __init__(self, parameters: str = ""):
        self.raw_parameters = parameters
        self.parsed_parameters = self._parse_parameters(parameters)
    
    def _parse_parameters(self, parameters: str) -> Dict[str, Any]:
        """Parse Laravel-style middleware parameters."""
        if not parameters:
            return {}
        
        parsed = {}
        parts = parameters.split(',')
        
        for i, part in enumerate(parts):
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                parsed[key.strip()] = self._parse_value(value.strip())
            else:
                parsed[f'param_{i}'] = self._parse_value(part)
        
        return parsed
    
    def _parse_value(self, value: str) -> Any:
        """Parse parameter value to appropriate type."""
        # Handle quoted strings
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        
        # Handle booleans
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Handle numbers
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get parameter value."""
        return self.parsed_parameters.get(key, default)
    
    def has(self, key: str) -> bool:
        """Check if parameter exists."""
        return key in self.parsed_parameters
    
    def all(self) -> Dict[str, Any]:
        """Get all parameters."""
        return self.parsed_parameters.copy()


class BaseMiddleware(ABC):
    """
    Laravel 12 Enhanced Base Middleware.
    
    All middleware should extend this base class and implement the handle method.
    This provides a consistent interface similar to Laravel's middleware with
    Laravel 12 enhancements.
    """
    
    # Laravel 12 middleware configuration
    config: MiddlewareConfig
    parameters: MiddlewareParameters
    _priority: int = 0
    _skip_routes: List[str] = []
    _only_routes: List[str] = []
    
    def __init__(self, parameters: str = "", **config: Any) -> None:
        """Initialize the middleware with Laravel 12 enhancements."""
        self.parameters = MiddlewareParameters(parameters)
        self.config = MiddlewareConfig(**config)
        self._terminable_callbacks: List[Callable[[Request, Response], None]] = []
        self._setup()
    
    def _setup(self) -> None:
        """Setup method called after initialization."""
        pass
    
    @classmethod
    def priority(cls) -> int:
        """Get middleware priority (Laravel 12)."""
        return getattr(cls, '_priority', MiddlewarePriority.VALIDATION.value)
    
    @classmethod 
    def withPriority(cls, priority: int) -> Type['BaseMiddleware']:
        """Set middleware priority (Laravel 12)."""
        cls._priority = priority
        return cls
    
    async def __call__(
        self, 
        request: Request, 
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process the request with Laravel 12 enhancements.
        
        @param request: The incoming HTTP request
        @param call_next: The next middleware or route handler
        @return: The HTTP response
        """
        # Check if middleware should run
        if not self.shouldRun(request):
            return await call_next(request)
        
        # Handle the request
        response = await self.handle(request, call_next)
        
        # Handle terminable callbacks if enabled
        if self.config.terminable and self._terminable_callbacks:
            # Schedule termination callbacks to run after response
            asyncio.create_task(self._run_terminable_callbacks(request, response))
        
        return response
    
    @abstractmethod
    async def handle(
        self, 
        request: Request, 
        next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Laravel 12 handle method - implement this in your middleware.
        
        @param request: The incoming HTTP request
        @param next: The next middleware or route handler
        @return: The HTTP response
        """
        pass
    
    def shouldRun(self, request: Request) -> bool:
        """
        Determine if middleware should run for this request (Laravel 12).
        
        @param request: The incoming HTTP request
        @return: True if middleware should run
        """
        # Check route conditions
        if self.config.only_routes and not self._matches_routes(request, self.config.only_routes):
            return False
        
        if self.config.except_routes and self._matches_routes(request, self.config.except_routes):
            return False
        
        # Check custom conditions
        if self.config.conditions:
            for condition in self.config.conditions:
                try:
                    if not condition():
                        return False
                except Exception:
                    return False
        
        return True
    
    def _matches_routes(self, request: Request, patterns: List[str]) -> bool:
        """Check if request matches route patterns."""
        import re
        
        # Use ASGI scope to get path (most reliable method)
        path = getattr(request, 'path_info', None)
        if path is None:
            # Try scope access
            scope = getattr(request, 'scope', {})
            path = scope.get('path', '/')
        if not path:
            # Final fallback - try to extract from string representation
            url_str = str(getattr(request, 'url', '/'))
            if '?' in url_str:
                url_str = url_str.split('?')[0]
            if url_str.startswith(('http://', 'https://')):
                path = '/' + '/'.join(url_str.split('/')[3:])
            else:
                path = url_str or '/'
        for pattern in patterns:
            # Convert Laravel-style wildcards to regex
            regex_pattern = pattern.replace('*', '.*').replace('?', '.')
            if re.match(f"^{regex_pattern}$", path):
                return True
        return False
    
    def before(self, request: Request) -> None:
        """
        Handle the request before it goes to the route handler.
        
        Override this method to add pre-request logic.
        
        @param request: The incoming HTTP request
        """
        pass
    
    def after(self, request: Request, response: Response) -> Response:
        """
        Handle the response after it comes from the route handler.
        
        Override this method to add post-request logic.
        
        @param request: The incoming HTTP request
        @param response: The outgoing HTTP response
        @return: The modified HTTP response
        """
        return response
    
    def terminate(self, request: Request, response: Response) -> None:
        """
        Perform any final work after the response has been sent.
        
        Override this method to add cleanup logic.
        
        @param request: The HTTP request
        @param response: The HTTP response
        """
        pass
    
    def addTerminableCallback(self, callback: Callable[[Request, Response], None]) -> 'BaseMiddleware':
        """Add a terminable callback (Laravel 12)."""
        self._terminable_callbacks.append(callback)
        return self
    
    async def _run_terminable_callbacks(self, request: Request, response: Response) -> None:
        """Run all terminable callbacks."""
        for callback in self._terminable_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(request, response)
                else:
                    callback(request, response)
            except Exception as e:
                # Log but don't raise - these are background tasks
                print(f"Error in terminable callback: {e}")
    
    # Laravel 12 Fluent Interface
    def when(self, condition: Union[bool, Callable[[], bool]]) -> 'ConditionalMiddleware':
        """Create conditional middleware (Laravel 12)."""
        return ConditionalMiddleware(self, condition)
    
    def unless(self, condition: Union[bool, Callable[[], bool]]) -> 'ConditionalMiddleware':
        """Create conditional middleware (Laravel 12)."""
        inverted_condition: Union[bool, Callable[[], bool]] = (lambda: not condition()) if callable(condition) else not condition
        return ConditionalMiddleware(self, inverted_condition)
    
    def except_routes(self, *routes: str) -> 'BaseMiddleware':
        """Exclude middleware from specific routes (Laravel 12)."""
        if self.config.except_routes is not None:
            self.config.except_routes.extend(routes)
        return self
    
    def only_routes(self, *routes: str) -> 'BaseMiddleware':
        """Only run middleware on specific routes (Laravel 12)."""
        if self.config.only_routes is not None:
            self.config.only_routes.extend(routes)
        return self
    
    @classmethod
    def make(cls, parameters: str = "", **config: Any) -> 'BaseMiddleware':
        """Laravel 12 factory method."""
        return cls(parameters, **config)
    
    # Laravel 12 static configuration methods
    @classmethod
    def configure(cls, **config: Any) -> Type['BaseMiddleware']:
        """Configure middleware class (Laravel 12)."""
        for key, value in config.items():
            setattr(cls, f"_{key}", value)
        return cls
    
    @classmethod
    def skip(cls, *routes: str) -> Type['BaseMiddleware']:
        """Skip middleware for specific routes (Laravel 12)."""
        cls._skip_routes = getattr(cls, '_skip_routes', [])
        cls._skip_routes.extend(routes)
        return cls
    
    @classmethod  
    def only(cls, *routes: str) -> Type['BaseMiddleware']:
        """Only apply middleware to specific routes (Laravel 12)."""
        cls._only_routes = getattr(cls, '_only_routes', [])
        cls._only_routes.extend(routes)
        return cls
    
    def getParameters(self) -> MiddlewareParameters:
        """Get middleware parameters (Laravel 12)."""
        return self.parameters
    
    def getConfig(self) -> MiddlewareConfig:
        """Get middleware configuration (Laravel 12)."""
        return self.config


# Laravel 12 Conditional Middleware
class ConditionalMiddleware:
    """Laravel 12 conditional middleware wrapper."""
    
    def __init__(self, middleware: BaseMiddleware, condition: Union[bool, Callable[[], bool]]):
        self.middleware = middleware
        self.condition = condition
    
    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Handle request conditionally."""
        should_run = self.condition() if callable(self.condition) else self.condition
        
        if should_run:
            return await self.middleware(request, call_next)
        else:
            return await call_next(request)


class SimpleMiddleware(BaseMiddleware):
    """
    Simple middleware implementation that uses before/after hooks.
    
    Extend this class and override before() and after() methods
    for simpler middleware implementations.
    """
    
    async def handle(
        self, 
        request: Request, 
        next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request using before/after hooks."""
        
        # Call before hook
        self.before(request)
        
        # Process request
        response = await next(request)
        
        # Call after hook and get modified response
        response = self.after(request, response)
        
        return response


# Laravel 12 Middleware Decorators
def middleware_priority(priority: int) -> Callable[[Type[BaseMiddleware]], Type[BaseMiddleware]]:
    """Decorator to set middleware priority (Laravel 12)."""
    def decorator(cls: Type[BaseMiddleware]) -> Type[BaseMiddleware]:
        cls._priority = priority
        return cls
    return decorator


def terminable_middleware(cls: Type[BaseMiddleware]) -> Type[BaseMiddleware]:
    """Decorator to mark middleware as terminable (Laravel 12)."""
    if hasattr(cls, '__init__'):
        original_init = cls.__init__
        def new_init(self: BaseMiddleware, *args: Any, **kwargs: Any) -> None:
            original_init(self, *args, **kwargs)
            self.config.terminable = True
        cls.__init__ = new_init  # type: ignore[method-assign]
    return cls


def conditional_middleware(condition: Union[bool, Callable[[], bool]]) -> Callable[[Type[BaseMiddleware]], Type[BaseMiddleware]]:
    """Decorator to make middleware conditional (Laravel 12)."""
    def decorator(cls: Type[BaseMiddleware]) -> Type[BaseMiddleware]:
        if hasattr(cls, '__init__'):
            original_init = cls.__init__
            def new_init(self: BaseMiddleware, *args: Any, **kwargs: Any) -> None:
                original_init(self, *args, **kwargs)
                if self.config.conditions:
                    self.config.conditions.append(condition if callable(condition) else lambda: condition)
            cls.__init__ = new_init  # type: ignore[method-assign]
        return cls
    return decorator


# Laravel 12 Middleware Groups
class MiddlewareGroup:
    """Laravel 12 middleware group management."""
    
    def __init__(self, name: str):
        self.name = name
        self.middleware: List[Union[str, Type[BaseMiddleware]]] = []
        self.priority = 50
    
    def append(self, middleware: Union[str, Type[BaseMiddleware]]) -> 'MiddlewareGroup':
        """Append middleware to group (Laravel 12)."""
        self.middleware.append(middleware)
        return self
    
    def prepend(self, middleware: Union[str, Type[BaseMiddleware]]) -> 'MiddlewareGroup':
        """Prepend middleware to group (Laravel 12)."""
        self.middleware.insert(0, middleware)
        return self
    
    def remove(self, middleware: Union[str, Type[BaseMiddleware]]) -> 'MiddlewareGroup':
        """Remove middleware from group (Laravel 12)."""
        if middleware in self.middleware:
            self.middleware.remove(middleware)
        return self
    
    def replace(self, old: Union[str, Type[BaseMiddleware]], new: Union[str, Type[BaseMiddleware]]) -> 'MiddlewareGroup':
        """Replace middleware in group (Laravel 12)."""
        if old in self.middleware:
            index = self.middleware.index(old)
            self.middleware[index] = new
        return self
    
    def with_priority(self, priority: int) -> 'MiddlewareGroup':
        """Set group priority (Laravel 12)."""
        self.priority = priority
        return self