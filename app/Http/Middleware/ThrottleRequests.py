from __future__ import annotations

import time
import hashlib
from typing import Any, Dict, Optional, Callable, Awaitable, Union
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import HTTPException


class ThrottleRequests(BaseHTTPMiddleware):
    """Laravel-style request throttling middleware."""
    
    def __init__(
        self, 
        app: Any,
        max_attempts: int = 60,
        decay_minutes: int = 1,
        prefix: str = 'throttle',
        resolver: Optional[Callable[[Request], str]] = None
    ) -> None:
        super().__init__(app)
        self.max_attempts = max_attempts
        self.decay_seconds = decay_minutes * 60
        self.prefix = prefix
        self.resolver = resolver or self._default_resolver
        self.cache: Dict[str, Dict[str, Union[int, float]]] = {}
        self.headers_enabled = True
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process request throttling."""
        key = self._resolve_request_signature(request)
        
        # Check if throttled
        if self._too_many_attempts(key):
            return self._build_exception_response(key)
        
        # Increment attempt count
        self._hit(key)
        
        # Process request
        response = await call_next(request)
        
        # Add throttle headers if enabled
        if self.headers_enabled:
            self._add_headers(response, key)
        
        return response
    
    def _resolve_request_signature(self, request: Request) -> str:
        """Resolve the request signature for throttling."""
        signature = self.resolver(request)
        return f"{self.prefix}:{signature}"
    
    def _default_resolver(self, request: Request) -> str:
        """Default request signature resolver using IP address."""
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Include route path for more granular throttling
        route_path = request.url.path
        
        # Create hash of IP + route
        signature = f"{client_ip}:{route_path}"
        return hashlib.sha256(signature.encode()).hexdigest()[:32]
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return '127.0.0.1'
    
    def _too_many_attempts(self, key: str) -> bool:
        """Check if too many attempts have been made."""
        attempts = self._attempts(key)
        return attempts >= self.max_attempts
    
    def _attempts(self, key: str) -> int:
        """Get the number of attempts for a key."""
        if key not in self.cache:
            return 0
        
        data = self.cache[key]
        expires_at = data.get('expires_at', 0)
        
        # Check if expired
        if time.time() > expires_at:
            del self.cache[key]
            return 0
        
        attempts = data.get('attempts', 0)
        return int(attempts) if attempts is not None else 0
    
    def _hit(self, key: str, decay_seconds: Optional[int] = None) -> int:
        """Increment the counter for a key."""
        decay = decay_seconds or self.decay_seconds
        now = time.time()
        expires_at = now + decay
        
        if key in self.cache:
            # Check if expired
            if now > self.cache[key].get('expires_at', 0):
                # Reset counter
                self.cache[key] = {'attempts': 1, 'expires_at': expires_at}
            else:
                # Increment counter
                self.cache[key]['attempts'] += 1
        else:
            # First attempt
            self.cache[key] = {'attempts': 1, 'expires_at': expires_at}
        
        attempts = self.cache[key]['attempts']
        return int(attempts) if attempts is not None else 0
    
    def _reset_attempts(self, key: str) -> None:
        """Reset the attempts for a key."""
        if key in self.cache:
            del self.cache[key]
    
    def _remaining_attempts(self, key: str) -> int:
        """Get the remaining attempts for a key."""
        return max(0, self.max_attempts - self._attempts(key))
    
    def _retry_after(self, key: str) -> int:
        """Get the number of seconds until the key resets."""
        if key not in self.cache:
            return 0
        
        expires_at = self.cache[key].get('expires_at', 0)
        return max(0, int(expires_at - time.time()))
    
    def _build_exception_response(self, key: str) -> Response:
        """Build the throttled response."""
        retry_after = self._retry_after(key)
        
        headers = {
            'X-RateLimit-Limit': str(self.max_attempts),
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': str(int(time.time()) + retry_after),
            'Retry-After': str(retry_after)
        }
        
        return Response(
            content='{"detail": "Too Many Requests"}',
            status_code=429,
            headers=headers,
            media_type='application/json'
        )
    
    def _add_headers(self, response: Response, key: str) -> None:
        """Add throttle headers to the response."""
        response.headers['X-RateLimit-Limit'] = str(self.max_attempts)
        response.headers['X-RateLimit-Remaining'] = str(self._remaining_attempts(key))
        
        if key in self.cache:
            expires_at = self.cache[key].get('expires_at', 0)
            response.headers['X-RateLimit-Reset'] = str(int(expires_at))
    
    def for_user(self, user_resolver: Callable[[Request], str]) -> ThrottleRequests:
        """Create throttle for authenticated users."""
        self.resolver = user_resolver
        return self
    
    def by_ip(self) -> ThrottleRequests:
        """Throttle by IP address only."""
        def ip_resolver(request: Request) -> str:
            return self._get_client_ip(request)
        
        self.resolver = ip_resolver
        return self
    
    def by_route(self) -> ThrottleRequests:
        """Throttle by route and IP."""
        self.resolver = self._default_resolver
        return self
    
    def skip_headers(self) -> ThrottleRequests:
        """Skip adding throttle headers to responses."""
        self.headers_enabled = False
        return self
    
    def clear(self, key: Optional[str] = None) -> None:
        """Clear throttle cache."""
        if key:
            self.cache.pop(key, None)
        else:
            self.cache.clear()


def throttle(
    max_attempts: int = 60,
    decay_minutes: int = 1,
    prefix: str = 'throttle'
) -> Callable[..., Any]:
    """Decorator for route-level throttling."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Store throttle metadata on the function
        if not hasattr(func, '_throttle_config'):
            setattr(func, '_throttle_config', {})
        
        throttle_config = getattr(func, '_throttle_config')
        throttle_config.update({
            'max_attempts': max_attempts,
            'decay_minutes': decay_minutes,
            'prefix': prefix
        })
        
        return func
    return decorator


class NamedThrottle:
    """Named throttle configurations."""
    
    _configurations: Dict[str, Dict[str, Any]] = {
        'api': {'max_attempts': 60, 'decay_minutes': 1},
        'uploads': {'max_attempts': 10, 'decay_minutes': 1},
        'auth': {'max_attempts': 5, 'decay_minutes': 1},
        'global': {'max_attempts': 1000, 'decay_minutes': 1},
    }
    
    @classmethod
    def configure(cls, name: str, max_attempts: int, decay_minutes: int) -> None:
        """Configure a named throttle."""
        cls._configurations[name] = {
            'max_attempts': max_attempts,
            'decay_minutes': decay_minutes
        }
    
    @classmethod
    def get(cls, name: str) -> Dict[str, Any]:
        """Get throttle configuration by name."""
        return cls._configurations.get(name, cls._configurations['api'])
    
    @classmethod
    def for_name(cls, name: str) -> ThrottleRequests:
        """Create throttle middleware for a named configuration."""
        config = cls.get(name)
        return ThrottleRequests(
            app=None,  # Will be set by middleware stack
            max_attempts=config['max_attempts'],
            decay_minutes=config['decay_minutes'],
            prefix=f"throttle:{name}"
        )