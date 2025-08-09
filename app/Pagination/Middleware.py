from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Awaitable
import time
import json

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .PaginationFactory import PaginationHelper


class PaginationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic pagination handling.
    
    This middleware can automatically detect paginated responses
    and add appropriate headers and metadata.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        auto_detect: bool = True,
        add_headers: bool = True,
        add_link_header: bool = True,
        max_per_page: int = 100,
        default_per_page: int = 15
    ):
        super().__init__(app)
        self.auto_detect = auto_detect
        self.add_headers = add_headers
        self.add_link_header = add_link_header
        self.max_per_page = max_per_page
        self.default_per_page = default_per_page
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request and response."""
        
        # Validate pagination parameters
        if self.auto_detect:
            self._validate_pagination_params(request)
        
        # Process the request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add pagination headers if enabled
        if self.add_headers and self._is_paginated_response(response):
            await self._add_pagination_headers(request, response)
        
        # Add performance header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    def _validate_pagination_params(self, request: Request) -> None:
        """Validate pagination parameters in the request."""
        query_params = request.query_params
        
        # Validate page parameter
        if 'page' in query_params:
            try:
                page = int(query_params['page'])
                if page < 1:
                    # You could raise an exception here or modify the request
                    pass
            except ValueError:
                # Invalid page parameter
                pass
        
        # Validate per_page parameter
        if 'per_page' in query_params:
            try:
                per_page = int(query_params['per_page'])
                if per_page < 1:
                    pass
                elif per_page > self.max_per_page:
                    # Could cap at max_per_page
                    pass
            except ValueError:
                # Invalid per_page parameter
                pass
    
    def _is_paginated_response(self, response: Response) -> bool:
        """Check if the response contains paginated data."""
        if not isinstance(response, JSONResponse):
            return False
        
        # Check if response body contains pagination indicators
        try:
            if hasattr(response, 'body'):
                content = json.loads(response.body.decode())
                return self._has_pagination_structure(content)
        except (json.JSONDecodeError, AttributeError):
            pass
        
        return False
    
    def _has_pagination_structure(self, content: Dict[str, Any]) -> bool:
        """Check if content has pagination structure."""
        # Check for common pagination keys
        pagination_keys = ['meta', 'links', 'current_page', 'total', 'per_page']
        
        if isinstance(content, dict):
            # Check for nested pagination structure
            if 'meta' in content and isinstance(content['meta'], dict):
                meta = content['meta']
                return any(key in meta for key in ['current_page', 'total', 'last_page'])
            
            # Check for direct pagination keys
            return any(key in content for key in pagination_keys)
        
        return False
    
    async def _add_pagination_headers(self, request: Request, response: Response) -> None:
        """Add pagination-related headers to the response."""
        try:
            if hasattr(response, 'body'):
                content = json.loads(response.body.decode())
                
                # Add pagination info headers
                if isinstance(content, dict):
                    meta = content.get('meta', content)
                    
                    if 'current_page' in meta:
                        response.headers["X-Current-Page"] = str(meta['current_page'])
                    
                    if 'total' in meta:
                        response.headers["X-Total-Count"] = str(meta['total'])
                    
                    if 'per_page' in meta:
                        response.headers["X-Per-Page"] = str(meta['per_page'])
                    
                    if 'last_page' in meta:
                        response.headers["X-Last-Page"] = str(meta['last_page'])
                    
                    # Add Link header for navigation
                    if self.add_link_header:
                        self._add_link_header(content, response)
        
        except (json.JSONDecodeError, AttributeError):
            pass
    
    def _add_link_header(self, content: Dict[str, Any], response: Response) -> None:
        """Add RFC 5988 Link header for pagination navigation."""
        links = []
        
        # Extract URLs from content
        urls = {}
        if 'links' in content:
            # Laravel-style links
            for link in content['links']:
                if isinstance(link, dict) and 'url' in link and 'label' in link:
                    label = link['label'].lower()
                    if 'first' in label or link.get('label') == '1':
                        urls['first'] = link['url']
                    elif 'last' in label:
                        urls['last'] = link['url']
                    elif 'prev' in label:
                        urls['prev'] = link['url']
                    elif 'next' in label:
                        urls['next'] = link['url']
        
        # Check for direct URL keys
        url_mappings = {
            'first_page_url': 'first',
            'last_page_url': 'last',
            'prev_page_url': 'prev',
            'next_page_url': 'next'
        }
        
        for content_key, rel in url_mappings.items():
            if content_key in content and content[content_key]:
                urls[rel] = content[content_key]
        
        # Build Link header
        for rel, url in urls.items():
            if url:
                links.append(f'<{url}>; rel="{rel}"')
        
        if links:
            response.headers["Link"] = ", ".join(links)


class PaginationCacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware for caching paginated responses.
    
    This middleware can cache paginated responses to improve performance
    for frequently accessed paginated data.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        cache_duration: int = 300,  # 5 minutes
        cache_key_prefix: str = "pagination:",
        exclude_paths: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.cache_duration = cache_duration
        self.cache_key_prefix = cache_key_prefix
        self.exclude_paths = exclude_paths or []
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request with caching."""
        
        # Check if this path should be cached
        if not self._should_cache(request):
            return await call_next(request)
        
        # Generate cache key
        cache_key = self._generate_cache_key(request)
        
        # Check cache
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            response = JSONResponse(cached_response['content'])
            response.headers["X-Cache"] = "HIT"
            return response
        
        # Process request
        response = await call_next(request)
        
        # Cache response if it's paginated
        if self._should_cache_response(response):
            await self._cache_response(cache_key, response)
            response.headers["X-Cache"] = "MISS"
        
        return response
    
    def _should_cache(self, request: Request) -> bool:
        """Determine if the request should be cached."""
        # Only cache GET requests
        if request.method != "GET":  # type: ignore[attr-defined]
            return False
        
        # Check exclude paths
        path = str(request.url.path)  # type: ignore[attr-defined]
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return False
        
        return True
    
    def _should_cache_response(self, response: Response) -> bool:
        """Determine if the response should be cached."""
        # Only cache successful responses
        if response.status_code != 200:
            return False
        
        # Only cache JSON responses
        if not isinstance(response, JSONResponse):
            return False
        
        return True
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate a cache key for the request."""
        # Include path and query parameters in cache key
        path = str(request.url.path)  # type: ignore[attr-defined]
        query = str(request.url.query)  # type: ignore[attr-defined]
        
        cache_key = f"{self.cache_key_prefix}{path}"
        if query:
            cache_key += f"?{query}"
        
        return cache_key
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired."""
        if cache_key not in self._cache:
            return None
        
        cached_item = self._cache[cache_key]
        
        # Check if expired
        if time.time() - cached_item['timestamp'] > self.cache_duration:
            del self._cache[cache_key]
            return None
        
        return cached_item
    
    async def _cache_response(self, cache_key: str, response: Response) -> None:
        """Cache the response."""
        try:
            if hasattr(response, 'body'):
                content = json.loads(response.body.decode())
                
                self._cache[cache_key] = {
                    'content': content,
                    'timestamp': time.time()
                }
        except (json.JSONDecodeError, AttributeError):
            pass


class PaginationLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging pagination usage and performance.
    
    This middleware logs information about pagination usage
    for analytics and optimization purposes.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_slow_queries: bool = True,
        slow_query_threshold: float = 1.0,  # seconds
        log_large_pages: bool = True,
        large_page_threshold: int = 100
    ):
        super().__init__(app)
        self.log_slow_queries = log_slow_queries
        self.slow_query_threshold = slow_query_threshold
        self.log_large_pages = log_large_pages
        self.large_page_threshold = large_page_threshold
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request with logging."""
        
        # Extract pagination info
        pagination_info = PaginationHelper.get_pagination_info(request)
        
        # Process request
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log information
        await self._log_pagination_usage(request, response, pagination_info, process_time)
        
        return response
    
    async def _log_pagination_usage(
        self, 
        request: Request, 
        response: Response,
        pagination_info: Dict[str, Any],
        process_time: float
    ) -> None:
        """Log pagination usage information."""
        
        # Log slow queries
        if self.log_slow_queries and process_time > self.slow_query_threshold:
            print(f"SLOW PAGINATION: {request.url.path} took {process_time:.2f}s")  # type: ignore[attr-defined]
            print(f"  Page: {pagination_info['page']}, Per Page: {pagination_info['per_page']}")
        
        # Log large page requests
        if self.log_large_pages and pagination_info['per_page'] > self.large_page_threshold:
            print(f"LARGE PAGE REQUEST: {request.url.path}")  # type: ignore[attr-defined]
            print(f"  Per Page: {pagination_info['per_page']}")
        
        # You could integrate with your logging system here
        # logger.info("Pagination request", extra={
        #     "path": str(request.url.path),  # type: ignore[attr-defined]
        #     "pagination": pagination_info,
        #     "process_time": process_time,
        #     "status_code": response.status_code
        # })