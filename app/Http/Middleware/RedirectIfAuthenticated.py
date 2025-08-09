from __future__ import annotations

from typing import Any, Optional, Callable, Awaitable, List
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RedirectIfAuthenticated(BaseHTTPMiddleware):
    """Laravel-style middleware to redirect authenticated users."""
    
    def __init__(
        self, 
        app: Any,
        redirect_to: str = '/dashboard',
        guards: Optional[List[str]] = None
    ) -> None:
        super().__init__(app)
        self.redirect_to = redirect_to
        self.guards = guards or ['web']
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Redirect authenticated users."""
        # Check if user is authenticated
        if self._is_authenticated(request):
            return RedirectResponse(url=self.redirect_to, status_code=302)
        
        response = await call_next(request)
        return response
    
    def _is_authenticated(self, request: Request) -> bool:
        """Check if the user is authenticated."""
        # Check session-based authentication
        if hasattr(request, 'session'):
            user_id = request.session.get('user_id')
            if user_id:
                return True
        
        # Check JWT token in headers
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if self._validate_jwt_token(token):
                return True
        
        # Check for user in request state (set by auth middleware)
        if hasattr(request.state, 'user') and request.state.user:
            return True
        
        return False
    
    def _validate_jwt_token(self, token: str) -> bool:
        """Validate JWT token."""
        try:
            from app.Utils.JWTUtils import JWTManager
            jwt_manager = JWTManager()
            payload = jwt_manager.decode_token(token)
            return payload is not None and 'user_id' in payload
        except Exception:
            return False
    
    def to(self, url: str) -> RedirectIfAuthenticated:
        """Set the redirect URL."""
        self.redirect_to = url
        return self
    
    def except_on(self, paths: List[str]) -> RedirectIfAuthenticated:
        """Skip redirect for specific paths."""
        # This would be implemented by checking request path
        # For now, just store the paths
        self.except_paths = getattr(self, 'except_paths', [])
        self.except_paths.extend(paths)
        return self
    
    def for_guards(self, guards: List[str]) -> RedirectIfAuthenticated:
        """Set authentication guards to check."""
        self.guards = guards
        return self