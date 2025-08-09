from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode, quote, urlparse, urlunparse
from fastapi import Request
from starlette.datastructures import URL


class RouteUrlGenerator:
    """Laravel-style URL generator for routes."""
    
    def __init__(self, routes: Optional[Dict[str, Dict[str, Any]]] = None, request: Optional[Request] = None) -> None:
        self.routes = routes or {}
        self.request = request
        self._root_url = self._get_root_url()
    
    def _get_root_url(self) -> str:
        """Get the root URL of the application."""
        if self.request:
            url: URL = self.request.url  # type: ignore[attr-defined]  # type: ignore[attr-defined]
            scheme = url.scheme or 'http'
            host = getattr(self.request.client, 'host', 'localhost') if self.request.client else 'localhost'
            port = url.port
            
            if port and port not in [80, 443]:
                return f"{scheme}://{host}:{port}"
            return f"{scheme}://{host}"
        
        return 'http://localhost:8000'  # Default fallback
    
    def to(self, path: str, parameters: Optional[Dict[str, Any]] = None, secure: Optional[bool] = None) -> str:
        """Generate a URL for the given path."""
        if path.startswith(('http://', 'https://')):
            return path
        
        # Ensure path starts with /
        if not path.startswith('/'):
            path = '/' + path
        
        url = f"{self._root_url}{path}"
        
        if parameters:
            url += '?' + urlencode(parameters)
        
        # Force HTTPS if secure is True
        if secure is True:
            url = url.replace('http://', 'https://')
        elif secure is False:
            url = url.replace('https://', 'http://')
        
        return url
    
    def route(self, name: str, parameters: Optional[Dict[str, Any]] = None, absolute: bool = True) -> str:
        """Generate a URL for a named route."""
        if name not in self.routes:
            raise ValueError(f"Route '{name}' not found")
        
        route_info = self.routes[name]
        path = route_info.get('path', '/')
        
        # Replace route parameters
        if parameters:
            path = self._replace_route_parameters(path, parameters)
        
        if absolute:
            return self.to(path)
        else:
            return str(path)
    
    def _replace_route_parameters(self, path: str, parameters: Dict[str, Any]) -> str:
        """Replace route parameters in path."""
        # Replace {param} style parameters
        for param, value in parameters.items():
            pattern = f"{{{param}}}"
            if pattern in path:
                path = path.replace(pattern, str(value))
        
        # Remove any remaining optional parameters
        path = re.sub(r'\{[^}]*\?\}', '', path)
        
        return path
    
    def action(self, action: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Generate URL for controller action."""
        # This would map controller actions to routes
        # For now, return a placeholder
        return self.to(f"/{action.lower()}", parameters)
    
    def asset(self, path: str, secure: Optional[bool] = None) -> str:
        """Generate URL for an asset."""
        if path.startswith(('http://', 'https://')):
            return path
        
        if not path.startswith('/'):
            path = '/static/' + path
        
        return self.to(path, secure=secure)
    
    def secure_url(self, path: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Generate a secure URL for the given path."""
        return self.to(path, parameters, secure=True)
    
    def secure_asset(self, path: str) -> str:
        """Generate a secure URL for an asset."""
        return self.asset(path, secure=True)
    
    def current(self, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Get the current URL."""
        if not self.request:
            return self._root_url
        
        url: URL = self.request.url  # type: ignore[attr-defined]
        current_path = url.path
        
        if parameters:
            return self.to(current_path, parameters)
        
        return str(url)
    
    def previous(self, fallback: str = '/') -> str:
        """Get the previous URL."""
        # This would typically come from session or referer header
        if self.request and 'referer' in self.request.headers:
            return self.request.headers['referer']
        
        return self.to(fallback)
    
    def is_valid_url(self, path: str) -> bool:
        """Check if the given path is a valid URL."""
        try:
            result = urlparse(path)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


class UrlManager:
    """Manager for URL generation."""
    
    def __init__(self) -> None:
        self._routes: Dict[str, Dict[str, Any]] = {}
        self._default_parameters: Dict[str, Any] = {}
        self._forced_scheme: Optional[str] = None
        self._forced_root: Optional[str] = None
    
    def register_route(self, name: str, path: str, **kwargs: Any) -> None:
        """Register a named route."""
        self._routes[name] = {
            'path': path,
            **kwargs
        }
    
    def generator(self, request: Optional[Request] = None) -> RouteUrlGenerator:
        """Create URL generator instance."""
        generator = RouteUrlGenerator(self._routes, request)
        
        if self._forced_root:
            generator._root_url = self._forced_root
        
        return generator
    
    def defaults(self, parameters: Dict[str, Any]) -> None:
        """Set default parameters for URL generation."""
        self._default_parameters.update(parameters)
    
    def force_scheme(self, scheme: str) -> None:
        """Force a specific scheme for all URLs."""
        self._forced_scheme = scheme
    
    def force_root_url(self, root: str) -> None:
        """Force a specific root URL."""
        self._forced_root = root
    
    def to(self, path: str, parameters: Optional[Dict[str, Any]] = None, secure: Optional[bool] = None) -> str:
        """Generate URL using default generator."""
        generator = self.generator()
        return generator.to(path, parameters, secure)
    
    def route(self, name: str, parameters: Optional[Dict[str, Any]] = None, absolute: bool = True) -> str:
        """Generate named route URL using default generator."""
        generator = self.generator()
        return generator.route(name, parameters, absolute)
    
    def asset(self, path: str, secure: Optional[bool] = None) -> str:
        """Generate asset URL using default generator."""
        generator = self.generator()
        return generator.asset(path, secure)


# Global URL manager
url_manager = UrlManager()


def url(path: str, parameters: Optional[Dict[str, Any]] = None, secure: Optional[bool] = None) -> str:
    """Generate a URL for the given path."""
    return url_manager.to(path, parameters, secure)


def route(name: str, parameters: Optional[Dict[str, Any]] = None, absolute: bool = True) -> str:
    """Generate a URL for a named route."""
    return url_manager.route(name, parameters, absolute)


def asset(path: str, secure: Optional[bool] = None) -> str:
    """Generate a URL for an asset."""
    return url_manager.asset(path, secure)


def secure_url(path: str, parameters: Optional[Dict[str, Any]] = None) -> str:
    """Generate a secure URL for the given path."""
    return url_manager.to(path, parameters, secure=True)


def secure_asset(path: str) -> str:
    """Generate a secure URL for an asset."""
    return url_manager.asset(path, secure=True)


def action(action: str, parameters: Optional[Dict[str, Any]] = None) -> str:
    """Generate URL for controller action."""
    generator = url_manager.generator()
    return generator.action(action, parameters)


# Helper for registering routes
def register_route(name: str, path: str, **kwargs: Any) -> None:
    """Register a named route."""
    url_manager.register_route(name, path, **kwargs)


# Common route registrations
def register_common_routes() -> None:
    """Register common application routes."""
    register_route('home', '/')
    register_route('login', '/auth/login')
    register_route('logout', '/auth/logout')
    register_route('register', '/auth/register')
    register_route('profile', '/profile')
    register_route('dashboard', '/dashboard')
    
    # API routes
    register_route('api.docs', '/docs')
    register_route('api.redoc', '/redoc')
    register_route('api.openapi', '/openapi.json')
    
    # OAuth2 routes
    register_route('oauth.authorize', '/oauth/authorize')
    register_route('oauth.token', '/oauth/token')
    register_route('oauth.introspect', '/oauth/introspect')
    register_route('oauth.metadata', '/.well-known/oauth-authorization-server')
    
    # Queue routes
    register_route('queue.dashboard', '/queue/dashboard')
    register_route('queue.stats', '/queue/stats')
    register_route('queue.failed', '/queue/failed')


# Auto-register common routes
register_common_routes()