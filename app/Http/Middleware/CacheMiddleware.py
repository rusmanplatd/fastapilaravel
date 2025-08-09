from __future__ import annotations

from typing import Any, Optional, Dict, Callable, Awaitable, List, Union
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import hashlib
import json

from app.Cache import cache_manager


class CacheMiddleware(BaseHTTPMiddleware):
    """HTTP response caching middleware."""
    
    def __init__(
        self,
        app: Any,
        default_ttl: int = 300,  # 5 minutes
        cache_store: Optional[str] = None,
        cache_key_prefix: str = "http_cache",
        cacheable_methods: Optional[List[str]] = None,
        ignore_query_params: Optional[List[str]] = None
    ) -> None:
        super().__init__(app)
        self.default_ttl = default_ttl
        self.cache_store = cache_manager.store(cache_store)
        self.cache_key_prefix = cache_key_prefix
        self.cacheable_methods = cacheable_methods or ["GET", "HEAD"]
        self.ignore_query_params = set(ignore_query_params or [])
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process the request with caching."""
        # Only cache specific HTTP methods
        method = getattr(request, 'method', 'GET')
        if method not in self.cacheable_methods:
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Try to get from cache
        cached_response = self.cache_store.get(cache_key)
        if cached_response:
            return self._restore_response(cached_response)
        
        # Execute request
        response = await call_next(request)
        
        # Cache successful responses
        if self._should_cache_response(response):
            self._cache_response(cache_key, response)
        
        return response
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key from request."""
        # Build key components
        path = getattr(getattr(request, 'url', None), 'path', '/')
        
        # Filter query parameters
        query_params = {}
        for key, value in request.query_params.items():
            if key not in self.ignore_query_params:
                query_params[key] = value
        
        key_data = {
            'path': path,
            'method': getattr(request, 'method', 'GET'),
            'query': sorted(query_params.items()),
            'headers': self._get_cache_headers(request)
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"{self.cache_key_prefix}:{key_hash}"
    
    def _get_cache_headers(self, request: Request) -> Dict[str, str]:
        """Get headers that should be part of cache key."""
        cache_headers = {}
        
        # Common headers that affect response content
        relevant_headers = [
            'accept',
            'accept-language',
            'accept-encoding',
            'authorization',
            'user-agent'
        ]
        
        for header in relevant_headers:
            if header in request.headers:
                cache_headers[header] = request.headers[header]
        
        return cache_headers
    
    def _should_cache_response(self, response: Response) -> bool:
        """Determine if response should be cached."""
        # Only cache successful responses
        if response.status_code < 200 or response.status_code >= 300:
            return False
        
        # Check cache control headers
        cache_control = response.headers.get('cache-control', '')
        if 'no-cache' in cache_control or 'no-store' in cache_control:
            return False
        
        return True
    
    def _cache_response(self, cache_key: str, response: Response) -> None:
        """Cache the response."""
        try:
            # Extract TTL from response headers
            ttl = self.default_ttl
            
            cache_control = response.headers.get('cache-control', '')
            if 'max-age=' in cache_control:
                try:
                    cache_control_str = str(cache_control)
                    max_age = int(cache_control_str.split('max-age=')[1].split(',')[0])
                    ttl = max_age
                except (ValueError, IndexError):
                    pass
            
            # Prepare response data for caching
            cached_data = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': None,
                'timestamp': time.time()
            }
            
            # Get response body (this is simplified - in production you'd handle streaming)
            if hasattr(response, 'body'):
                cached_data['body'] = response.body.decode() if isinstance(response.body, bytes) else response.body
            
            self.cache_store.put(cache_key, cached_data, ttl)
            
        except Exception:
            # Don't let caching errors affect the response
            pass
    
    def _restore_response(self, cached_data: Dict[str, Any]) -> Union[JSONResponse, Response]:
        """Restore response from cached data."""
        headers = cached_data.get('headers', {})
        
        # Add cache hit header
        headers['X-Cache'] = 'HIT'
        headers['X-Cache-Timestamp'] = str(cached_data.get('timestamp', 0))
        
        body = cached_data.get('body', '')
        status_code = cached_data.get('status_code', 200)
        
        # Determine response type based on content-type
        content_type = headers.get('content-type', 'application/json')
        
        if 'application/json' in content_type:
            try:
                return JSONResponse(
                    content=json.loads(body) if isinstance(body, str) else body,
                    status_code=status_code,
                    headers=headers
                )
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Fallback to plain response
        from starlette.responses import Response as StarletteResponse
        return StarletteResponse(
            content=body,
            status_code=status_code,
            headers=headers
        )


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """Simple response caching middleware with configurable rules."""
    
    def __init__(
        self,
        app: Any,
        cache_rules: Optional[Dict[str, Dict[str, Any]]] = None,
        default_store: Optional[str] = None
    ) -> None:
        super().__init__(app)
        self.cache_rules = cache_rules or {}
        self.cache_store = cache_manager.store(default_store)
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process request with rule-based caching."""
        cache_rule = self._get_cache_rule(request)
        
        if not cache_rule:
            return await call_next(request)
        
        cache_key = self._generate_rule_cache_key(request, cache_rule)
        
        # Try cache first
        cached = self.cache_store.get(cache_key)
        if cached:
            return self._build_cached_response(cached)
        
        # Execute and cache
        response = await call_next(request)
        
        if response.status_code == 200:
            self._cache_rule_response(cache_key, response, cache_rule)
        
        return response
    
    def _get_cache_rule(self, request: Request) -> Optional[Dict[str, Any]]:
        """Get caching rule for request."""
        path = getattr(getattr(request, 'url', None), 'path', '/')
        method = getattr(request, 'method', 'GET')
        
        for pattern, rule in self.cache_rules.items():
            if self._matches_pattern(path, pattern) and method in rule.get('methods', ['GET']):
                return rule
        
        return None
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches pattern (simplified)."""
        if pattern == '*':
            return True
        
        if pattern.endswith('*'):
            return path.startswith(pattern[:-1])
        
        return path == pattern
    
    def _generate_rule_cache_key(self, request: Request, rule: Dict[str, Any]) -> str:
        """Generate cache key based on rule."""
        path = getattr(getattr(request, 'url', None), 'path', '/')
        method = getattr(request, 'method', 'GET')
        key_parts = [path, method]
        
        # Include specific query parameters if specified
        if 'include_params' in rule:
            for param in rule['include_params']:
                if param in request.query_params:
                    key_parts.append(f"{param}={request.query_params[param]}")
        
        key_string = ':'.join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _cache_rule_response(self, cache_key: str, response: Response, rule: Dict[str, Any]) -> None:
        """Cache response according to rule."""
        ttl = rule.get('ttl', 300)
        
        try:
            # Simple body extraction (would need improvement for streaming responses)
            if hasattr(response, 'body'):
                body = response.body
            else:
                body = b""
            
            cached_data = {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'body': body.decode() if isinstance(body, bytes) else str(body)
            }
            
            self.cache_store.put(cache_key, cached_data, ttl)
            
        except Exception:
            pass
    
    def _build_cached_response(self, cached_data: Dict[str, Any]) -> Response:
        """Build response from cached data."""
        headers = cached_data.get('headers', {})
        headers['X-Cache'] = 'HIT'
        
        from starlette.responses import Response as StarletteResponse
        return StarletteResponse(
            content=cached_data.get('body', ''),
            status_code=cached_data.get('status_code', 200),
            headers=headers
        )


class CacheTagMiddleware(BaseHTTPMiddleware):
    """Middleware for managing cache tags."""
    
    def __init__(self, app: Any, default_tags: Optional[List[str]] = None) -> None:
        super().__init__(app)
        self.default_tags = default_tags or []
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Add cache tag support to requests."""
        # Add cache tags to request state
        request.state.cache_tags = self.default_tags.copy()
        
        response = await call_next(request)
        
        # Add cache tags header for debugging
        if hasattr(request.state, 'cache_tags') and request.state.cache_tags:
            response.headers['X-Cache-Tags'] = ','.join(request.state.cache_tags)
        
        return response


# Cache middleware configurations
DEFAULT_CACHE_RULES = {
    '/api/v1/public/*': {
        'ttl': 300,  # 5 minutes
        'methods': ['GET'],
        'include_params': []
    },
    '/api/v1/users/*/profile': {
        'ttl': 600,  # 10 minutes
        'methods': ['GET'],
        'include_params': ['include']
    },
    '/api/v1/static/*': {
        'ttl': 3600,  # 1 hour
        'methods': ['GET', 'HEAD'],
        'include_params': []
    }
}