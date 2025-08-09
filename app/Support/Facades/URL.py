from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import Request
from app.Routing.UrlGenerator import url_manager


class URL:
    """Laravel-style URL facade."""
    
    @staticmethod
    def to(path: str, parameters: Optional[Dict[str, Any]] = None, secure: Optional[bool] = None) -> str:
        """Generate a URL for the given path."""
        return url_manager.to(path, parameters, secure)
    
    @staticmethod
    def route(name: str, parameters: Optional[Dict[str, Any]] = None, absolute: bool = True) -> str:
        """Generate a URL for a named route."""
        return url_manager.route(name, parameters, absolute)
    
    @staticmethod
    def action(action: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Generate URL for controller action."""
        generator = url_manager.generator()
        return generator.action(action, parameters)
    
    @staticmethod
    def asset(path: str, secure: Optional[bool] = None) -> str:
        """Generate a URL for an asset."""
        return url_manager.asset(path, secure)
    
    @staticmethod
    def secure_url(path: str, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Generate a secure URL for the given path."""
        return url_manager.to(path, parameters, secure=True)
    
    @staticmethod
    def secure_asset(path: str) -> str:
        """Generate a secure URL for an asset."""
        return url_manager.asset(path, secure=True)
    
    @staticmethod
    def current(parameters: Optional[Dict[str, Any]] = None, request: Optional[Request] = None) -> str:
        """Get the current URL."""
        generator = url_manager.generator(request)
        return generator.current(parameters)
    
    @staticmethod
    def previous(fallback: str = '/', request: Optional[Request] = None) -> str:
        """Get the previous URL."""
        generator = url_manager.generator(request)
        return generator.previous(fallback)
    
    @staticmethod
    def is_valid_url(path: str) -> bool:
        """Check if the given path is a valid URL."""
        generator = url_manager.generator()
        return generator.is_valid_url(path)
    
    @staticmethod
    def defaults(parameters: Dict[str, Any]) -> None:
        """Set default parameters for URL generation."""
        url_manager.defaults(parameters)
    
    @staticmethod
    def force_scheme(scheme: str) -> None:
        """Force a specific scheme for all URLs."""
        url_manager.force_scheme(scheme)
    
    @staticmethod
    def force_root_url(root: str) -> None:
        """Force a specific root URL."""
        url_manager.force_root_url(root)
    
    @staticmethod
    def signed(name: str, parameters: Optional[Dict[str, Any]] = None, expiration: Optional[int] = None) -> str:
        """Create a signed route URL."""
        # This would implement signed URL generation
        # For now, return regular route URL
        return URL.route(name, parameters)
    
    @staticmethod
    def temporary_signed(name: str, expiration: int, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Create a temporary signed route URL."""
        # This would implement temporary signed URL generation
        # For now, return regular route URL
        return URL.route(name, parameters)
    
    @staticmethod
    def has_valid_signature(request: Request) -> bool:
        """Check if the current request has a valid signature."""
        # This would implement signature validation
        # For now, return True
        return True