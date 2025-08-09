from __future__ import annotations

from typing import List, Dict, Any, Callable, Optional, Union, TYPE_CHECKING
from app.Support.Facades.Facade import Facade

if TYPE_CHECKING:
    from app.Routing.RouteManager import RouteManager


class Route(Facade):
    """
    Laravel-style Route Facade.
    
    Provides static-like access to routing functionality,
    similar to Laravel's Route facade.
    """
    
    _group_context: Dict[str, Any] = {}
    
    @staticmethod
    def get_facade_accessor() -> str:
        """Get the registered name of the component."""
        return 'route_manager'
    
    @classmethod
    def _register_with_context(cls, path: str, method: str, handler: Callable[..., Any], name: Optional[str] = None) -> 'Route':
        """Helper method to register route with group context."""
        group_context = getattr(cls, '_group_context', {})
        final_path = group_context.get('prefix', '') + path
        final_name = name or f"{method.lower()}.{path}"
        if group_context.get('name'):
            final_name = group_context['name'] + '.' + final_name
        
        cls.get_facade_root().register_route(
            name=final_name,
            path=final_path,
            method=method,
            handler=handler,
            middleware=group_context.get('middleware', [])
        )
        return cls  # type: ignore

    @classmethod
    def get(cls, path: str, handler: Callable[..., Any], name: Optional[str] = None) -> 'Route':
        """
        Register a GET route.
        
        @param path: The route path
        @param handler: The route handler
        @param name: The route name
        @return: Route instance for chaining
        """
        cls._register_with_context(path, "GET", handler, name)
        return cls  # type: ignore
    
    @classmethod
    def post(cls, path: str, handler: Callable[..., Any], name: Optional[str] = None) -> 'Route':
        """
        Register a POST route.
        
        @param path: The route path
        @param handler: The route handler
        @param name: The route name
        @return: Route instance for chaining
        """
        return cls._register_with_context(path, "POST", handler, name)
    
    @classmethod
    def put(cls, path: str, handler: Callable[..., Any], name: Optional[str] = None) -> 'Route':
        """
        Register a PUT route.
        
        @param path: The route path  
        @param handler: The route handler
        @param name: The route name
        @return: Route instance for chaining
        """
        return cls._register_with_context(path, "PUT", handler, name)
    
    @classmethod  
    def patch(cls, path: str, handler: Callable[..., Any], name: Optional[str] = None) -> 'Route':
        """
        Register a PATCH route.
        
        @param path: The route path
        @param handler: The route handler
        @param name: The route name
        @return: Route instance for chaining
        """
        return cls._register_with_context(path, "PATCH", handler, name)
    
    @classmethod
    def delete(cls, path: str, handler: Callable[..., Any], name: Optional[str] = None) -> 'Route':
        """
        Register a DELETE route.
        
        @param path: The route path
        @param handler: The route handler  
        @param name: The route name
        @return: Route instance for chaining
        """
        return cls._register_with_context(path, "DELETE", handler, name)
    
    @classmethod
    def options(cls, path: str, handler: Callable[..., Any], name: Optional[str] = None) -> 'Route':
        """
        Register an OPTIONS route.
        
        @param path: The route path
        @param handler: The route handler
        @param name: The route name
        @return: Route instance for chaining
        """
        cls.get_facade_root().register_route(
            name=name or f"options.{path}",
            path=path,
            method="OPTIONS",
            handler=handler
        )
        return cls  # type: ignore
    
    @classmethod
    def any(cls, path: str, handler: Callable[..., Any], name: Optional[str] = None) -> 'Route':
        """
        Register a route that responds to any HTTP verb.
        
        @param path: The route path
        @param handler: The route handler
        @param name: The route name
        @return: Route instance for chaining
        """
        methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
        for method in methods:
            cls.get_facade_root().register_route(
                name=name or f"any.{path}",
                path=path,
                method=method,
                handler=handler
            )
        return cls  # type: ignore
    
    @classmethod
    def match(cls, methods: List[str], path: str, handler: Callable[..., Any], name: Optional[str] = None) -> 'Route':
        """
        Register a route that responds to multiple HTTP verbs.
        
        @param methods: List of HTTP methods
        @param path: The route path
        @param handler: The route handler
        @param name: The route name
        @return: Route instance for chaining
        """
        for method in methods:
            cls.get_facade_root().register_route(
                name=name or f"{method.lower()}.{path}",
                path=path,
                method=method.upper(),
                handler=handler
            )
        return cls  # type: ignore
    
    @classmethod
    def redirect(cls, path: str, destination: str, status: int = 301) -> 'Route':
        """
        Register a redirect route.
        
        @param path: The route path
        @param destination: The destination URL
        @param status: The HTTP status code
        @return: Route instance for chaining
        """
        def redirect_handler() -> Any:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=destination, status_code=status)
        
        cls.get(path, redirect_handler)
        return cls  # type: ignore
    
    @classmethod
    def permanent_redirect(cls, path: str, destination: str) -> 'Route':
        """
        Register a permanent redirect route.
        
        @param path: The route path
        @param destination: The destination URL
        @return: Route instance for chaining
        """
        cls.redirect(path, destination, 301)
        return cls  # type: ignore
    
    @classmethod
    def view(cls, path: str, template: str, data: Optional[Dict[str, Any]] = None) -> 'Route':
        """
        Register a route that returns a view.
        
        @param path: The route path
        @param template: The template name
        @param data: Data to pass to the template
        @return: Route instance for chaining
        """
        data = data or {}
        
        def view_handler() -> Any:
            # Implement basic view rendering
            try:
                # Try to use Jinja2 template engine if available
                from jinja2 import Environment, FileSystemLoader, select_autoescape
                import os
                
                # Set up template environment
                template_dir = os.path.join(os.getcwd(), 'resources', 'views')
                if not os.path.exists(template_dir):
                    template_dir = os.path.join(os.getcwd(), 'templates')
                
                if os.path.exists(template_dir):
                    env = Environment(
                        loader=FileSystemLoader(template_dir),
                        autoescape=select_autoescape(['html', 'xml'])
                    )
                    
                    template_obj = env.get_template(template)
                    rendered = template_obj.render(**data)
                    
                    from fastapi.responses import HTMLResponse
                    return HTMLResponse(content=rendered)
                else:
                    # Fallback to simple template rendering
                    return {"template": template, "data": data, "rendered": True}
                    
            except ImportError:
                # Jinja2 not available, return basic template info
                return {"template": template, "data": data, "engine": "basic"}
            except Exception as e:
                # Template rendering failed
                return {"error": f"Template rendering failed: {str(e)}", "template": template}
        
        cls.get(path, view_handler)
        return cls  # type: ignore
    
    @classmethod
    def group(cls, attributes: Dict[str, Any], routes: Callable[[], None]) -> None:
        """
        Create a route group with shared attributes.
        
        @param attributes: Group attributes (prefix, middleware, etc.)
        @param routes: Function that defines the routes
        """
        # Store previous context
        previous_context = getattr(cls, '_group_context', {})
        
        # Merge attributes with current context
        current_context = {
            'prefix': previous_context.get('prefix', '') + attributes.get('prefix', ''),
            'middleware': previous_context.get('middleware', []) + attributes.get('middleware', []),
            'name': attributes.get('name', previous_context.get('name', '')),
            'namespace': attributes.get('namespace', previous_context.get('namespace', '')),
        }
        
        # Set group context
        cls._group_context = current_context
        
        try:
            # Execute routes with group context
            routes()
        finally:
            # Restore previous context
            cls._group_context = previous_context
    
    @classmethod
    def prefix(cls, prefix: str) -> 'RouteGroup':
        """
        Create a route group with a URL prefix.
        
        @param prefix: The URL prefix
        @return: RouteGroup for chaining
        """
        return RouteGroup(prefix=prefix)
    
    @classmethod  
    def middleware(cls, middleware: Union[str, List[str]]) -> 'RouteGroup':
        """
        Create a route group with middleware.
        
        @param middleware: Middleware name(s)
        @return: RouteGroup for chaining
        """
        if isinstance(middleware, str):
            middleware = [middleware]
        return RouteGroup(middleware=middleware)
    
    @classmethod
    def name(cls, name: str) -> 'RouteGroup':
        """
        Create a route group with a name prefix.
        
        @param name: The name prefix
        @return: RouteGroup for chaining
        """
        return RouteGroup(name_prefix=name)
    
    @classmethod
    def namespace(cls, namespace: str) -> 'RouteGroup':
        """
        Create a route group with a namespace.
        
        @param namespace: The namespace
        @return: RouteGroup for chaining
        """
        return RouteGroup(namespace=namespace)
    
    @classmethod
    def current(cls) -> Optional[Dict[str, Any]]:
        """
        Get the current route.
        
        @return: Current route information or None
        """
        return cls.get_facade_root().get_current_route()
    
    @classmethod
    def current_route_name(cls) -> Optional[str]:
        """
        Get the current route name.
        
        @return: Current route name or None
        """
        current = cls.current()
        return current.get('name') if current else None
    
    @classmethod
    def has(cls, name: str) -> bool:
        """
        Check if a route exists.
        
        @param name: The route name
        @return: True if route exists
        """
        return cls.get_facade_root().has_route(name)
    
    @classmethod
    def url(cls, name: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a URL for a named route.
        
        @param name: The route name
        @param parameters: Route parameters
        @return: The generated URL
        """
        parameters = parameters or {}
        return cls.get_facade_root().generate_url(name, parameters)


class RouteGroup:
    """
    Laravel-style Route Group.
    
    Allows for fluent route group definition.
    """
    
    def __init__(
        self, 
        prefix: Optional[str] = None,
        middleware: Optional[List[str]] = None,
        name_prefix: Optional[str] = None,
        namespace: Optional[str] = None
    ) -> None:
        self.attributes: Dict[str, Any] = {}
        if prefix:
            self.attributes['prefix'] = prefix
        if middleware:
            self.attributes['middleware'] = middleware  
        if name_prefix:
            self.attributes['name'] = name_prefix
        if namespace:
            self.attributes['namespace'] = namespace
    
    def prefix(self, prefix: str) -> 'RouteGroup':
        """Add a prefix to the group."""
        self.attributes['prefix'] = prefix
        return self
    
    def middleware(self, middleware: Union[str, List[str]]) -> 'RouteGroup':
        """Add middleware to the group."""
        if isinstance(middleware, str):
            middleware = [middleware]
        self.attributes['middleware'] = middleware
        return self
    
    def name(self, name: str) -> 'RouteGroup':
        """Add a name prefix to the group."""
        self.attributes['name'] = name
        return self
    
    def namespace(self, namespace: str) -> 'RouteGroup':
        """Add a namespace to the group."""
        self.attributes['namespace'] = namespace
        return self
    
    def group(self, routes: Callable[[], None]) -> None:
        """Define the routes in this group."""
        Route.group(self.attributes, routes)


# Alias for easier imports (similar to Laravel)
route = Route