from __future__ import annotations

from typing import Any, Dict, Union, Optional
from fastapi import Response
from fastapi.responses import JSONResponse
from app.Http.Cookie.CookieJar import cookie_manager, Cookie as CookieClass


class Cookie:
    """Laravel-style Cookie facade."""
    
    @staticmethod
    def make(
        name: str,
        value: str,
        minutes: Optional[int] = None,
        path: str = '/',
        domain: Optional[str] = None,
        secure: Optional[bool] = None,
        http_only: bool = True,
        raw: bool = False,
        same_site: str = 'lax'
    ) -> CookieClass:
        """Make a cookie instance."""
        return cookie_manager.make(
            name=name,
            value=value,
            minutes=minutes,
            path=path,
            domain=domain,
            secure=secure,
            http_only=http_only,
            raw=raw,
            same_site=same_site
        )
    
    @staticmethod
    def forever(
        name: str,
        value: str,
        path: str = '/',
        domain: Optional[str] = None,
        secure: Optional[bool] = None,
        http_only: bool = True,
        raw: bool = False,
        same_site: str = 'lax'
    ) -> CookieClass:
        """Make a cookie that lasts "forever" (5 years)."""
        return cookie_manager.forever(
            name=name,
            value=value,
            path=path,
            domain=domain,
            secure=secure,
            http_only=http_only,
            raw=raw,
            same_site=same_site
        )
    
    @staticmethod
    def forget(name: str, path: str = '/', domain: Optional[str] = None) -> CookieClass:
        """Create a cookie that will expire immediately."""
        return cookie_manager.forget(name=name, path=path, domain=domain)
    
    @staticmethod
    def queue(name: str, value: str, **options: Any) -> None:
        """Queue a cookie to be sent with the response."""
        cookie_manager.queue(name, value, **options)
    
    @staticmethod
    def queue_forget(name: str, **options: Any) -> None:
        """Queue a cookie to be forgotten."""
        cookie_manager.queue_forget(name, **options)
    
    @staticmethod
    def unqueue(name: str) -> None:
        """Remove a cookie from the queue."""
        cookie_manager.jar.unqueue(name)
    
    @staticmethod
    def get(request_cookies: Dict[str, str], name: str, default: Any = None) -> Any:
        """Get cookie value from request."""
        return cookie_manager.get(request_cookies, name, default)
    
    @staticmethod
    def has(request_cookies: Dict[str, str], name: str) -> bool:
        """Check if cookie exists in request."""
        return cookie_manager.has(request_cookies, name)
    
    @staticmethod
    def has_queued(name: str) -> bool:
        """Check if a cookie is queued."""
        return cookie_manager.jar.has_queued(name)
    
    @staticmethod
    def get_queued(name: str) -> Optional[CookieClass]:
        """Get a queued cookie by name."""
        return cookie_manager.jar.get_queued(name)
    
    @staticmethod
    def get_queued_cookies() -> list:
        """Get all queued cookies."""
        return cookie_manager.jar.get_queued_cookies()
    
    @staticmethod
    def flush_queued_cookies() -> None:
        """Clear all queued cookies."""
        cookie_manager.jar.flush_queued_cookies()
    
    @staticmethod
    def attach_to_response(response: Union[Response, JSONResponse]) -> None:
        """Attach queued cookies to response."""
        cookie_manager.attach_to_response(response)
    
    @staticmethod
    def configure(**config: Any) -> None:
        """Configure global cookie settings."""
        cookie_manager.configure(**config)