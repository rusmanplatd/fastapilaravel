from __future__ import annotations

from typing import Callable, Any, Union, Literal
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.responses import Response as StarletteResponse
import json
from app.Session import session_manager


class SessionMiddleware:
    """Laravel-style session middleware for FastAPI."""
    
    def __init__(
        self,
        driver: str = 'file',
        cookie_name: str = 'laravel_session',
        lifetime: int = 7200,
        secure: bool = False,
        http_only: bool = True,
        same_site: str = 'lax'
    ) -> None:
        self.driver = driver
        self.cookie_name = cookie_name
        self.lifetime = lifetime
        self.secure = secure
        self.http_only = http_only
        self.same_site = same_site
    
    async def __call__(self, request: Request, call_next: Callable[..., Any]) -> Any:
        """Process request with session handling."""
        # Get session ID from cookie
        session_id = getattr(request, 'cookies', {}).get(self.cookie_name)
        
        # Create session instance
        session_instance = session_manager.driver(self.driver)
        if session_id:
            session_instance.set_id(session_id)
        
        # Start session
        session_instance.start()
        
        # Add session to request state
        request.state.session = session_instance
        
        # Age flash data
        session_instance._age_flash_data()
        
        # Process request
        response = await call_next(request)
        
        # Save session
        session_instance.save()
        
        # Set session cookie
        if hasattr(response, 'set_cookie'):
            samesite_value: Literal['lax', 'strict', 'none'] | None = None
            if self.same_site in ["strict", "lax", "none"]:
                samesite_value = self.same_site  # type: ignore[assignment]
            else:
                samesite_value = "lax"
            
            response.set_cookie(
                key=self.cookie_name,
                value=session_instance.get_id(),
                max_age=self.lifetime,
                secure=self.secure,
                httponly=self.http_only,
                samesite=samesite_value
            )
        
        return response


# Helper function to get session from request
def get_session(request: Request) -> Any:
    """Get session from request."""
    # Use Starlette's built-in session support
    return getattr(request, 'session', {})


# Middleware factory
def create_session_middleware(
    driver: str = 'file',
    cookie_name: str = 'laravel_session',
    lifetime: int = 7200,
    secure: bool = False,
    http_only: bool = True,
    same_site: str = 'lax'
) -> SessionMiddleware:
    """Create session middleware with configuration."""
    return SessionMiddleware(
        driver=driver,
        cookie_name=cookie_name,
        lifetime=lifetime,
        secure=secure,
        http_only=http_only,
        same_site=same_site
    )