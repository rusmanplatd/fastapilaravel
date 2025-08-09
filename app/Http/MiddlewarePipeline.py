from __future__ import annotations

from typing import List, Dict, Any, Optional, Callable, Union, Type, Awaitable
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from dataclasses import dataclass
import asyncio
import time
import logging
from abc import ABC, abstractmethod


@dataclass
class MiddlewareContext:
    """Context passed through the middleware pipeline."""
    request: Request
    response: Optional[Response] = None
    data: Optional[Dict[str, Any]] = None
    terminated: bool = False
    
    def __post_init__(self) -> None:
        if self.data is None:
            self.data = {}


class PipelineMiddleware(ABC):
    """Base class for Laravel-style pipeline middleware."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def handle(self, context: MiddlewareContext, next_middleware: Callable[[MiddlewareContext], Any]) -> MiddlewareContext:
        """Handle the middleware logic."""
        pass
    
    def should_run(self, context: MiddlewareContext) -> bool:
        """Determine if this middleware should run."""
        return True
    
    def priority(self) -> int:
        """Return the priority of this middleware (lower = higher priority)."""
        return 100


class TerminableMiddleware(PipelineMiddleware):
    """Middleware that can terminate after response is sent."""
    
    async def terminate(self, context: MiddlewareContext) -> None:
        """Called after the response has been sent."""
        pass


class ConditionalMiddleware(PipelineMiddleware):
    """Middleware that runs based on conditions."""
    
    def __init__(self, condition: Callable[[MiddlewareContext], bool], config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config)
        self.condition = condition
    
    def should_run(self, context: MiddlewareContext) -> bool:
        """Check if the condition is met."""
        try:
            return self.condition(context)
        except Exception as e:
            self.logger.error(f"Error evaluating condition: {e}")
            return False


class LaravelPipeline:
    """Laravel-style middleware pipeline for FastAPI."""
    
    def __init__(self) -> None:
        self.middleware: List[PipelineMiddleware] = []
        self.terminable_middleware: List[TerminableMiddleware] = []
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def pipe(self, middleware: Union[PipelineMiddleware, Type[PipelineMiddleware]], config: Optional[Dict[str, Any]] = None) -> 'LaravelPipeline':
        """Add middleware to the pipeline."""
        if isinstance(middleware, type):
            middleware_instance = middleware(config)
        else:
            middleware_instance = middleware
            
        self.middleware.append(middleware_instance)
        
        if isinstance(middleware_instance, TerminableMiddleware):
            self.terminable_middleware.append(middleware_instance)
        
        # Sort by priority
        self.middleware.sort(key=lambda m: m.priority())
        
        return self
    
    async def then(self, passable: MiddlewareContext, destination: Callable[..., Any]) -> MiddlewareContext:
        """Execute the pipeline."""
        return await self._run_pipeline(passable, destination)
    
    async def _run_pipeline(self, context: MiddlewareContext, destination: Callable[..., Any]) -> MiddlewareContext:
        """Run the middleware pipeline."""
        pipeline_stack = self._build_pipeline_stack(destination)
        
        try:
            # Execute the pipeline
            result = await pipeline_stack(context)
            
            # Execute terminable middleware
            await self._execute_terminable_middleware(result)
            
            return result  # type: ignore[no-any-return]
        except Exception as e:
            self.logger.error(f"Pipeline execution error: {e}")
            raise
    
    def _build_pipeline_stack(self, destination: Callable[..., Any]) -> Callable[..., Any]:
        """Build the pipeline stack."""
        def create_layer(middleware_instance: PipelineMiddleware, next_layer: Callable[..., Any]) -> Callable[..., Any]:
            async def layer(context: MiddlewareContext) -> MiddlewareContext:
                if not middleware_instance.should_run(context):
                    return await next_layer(context)  # type: ignore[no-any-return]
                
                return await middleware_instance.handle(context, next_layer)
            
            return layer
        
        # Start with the destination
        pipeline = destination
        
        # Build the stack in reverse order
        for middleware_instance in reversed(self.middleware):
            pipeline = create_layer(middleware_instance, pipeline)
        
        return pipeline
    
    async def _execute_terminable_middleware(self, context: MiddlewareContext) -> None:
        """Execute terminable middleware after response is sent."""
        for middleware in self.terminable_middleware:
            try:
                await middleware.terminate(context)
            except Exception as e:
                self.logger.error(f"Error in terminable middleware {middleware.__class__.__name__}: {e}")


class FastAPIPipelineMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that uses Laravel-style pipeline."""
    
    def __init__(self, app: Any, pipeline: LaravelPipeline) -> None:
        super().__init__(app)
        self.pipeline = pipeline
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        """Dispatch request through the pipeline."""
        context = MiddlewareContext(request=request)
        
        async def destination(ctx: MiddlewareContext) -> MiddlewareContext:
            """Final destination - call the actual route handler."""
            if not ctx.response:
                ctx.response = await call_next(ctx.request)
            return ctx
        
        try:
            result_context = await self.pipeline._run_pipeline(context, destination)
            from fastapi.responses import JSONResponse
            return result_context.response or JSONResponse(content={"error": "No response generated"}, status_code=500)
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Pipeline middleware error: {e}")
            from fastapi.responses import JSONResponse
            return JSONResponse(content={"error": "Internal server error"}, status_code=500)


# Built-in Pipeline Middleware Classes

class AuthenticationMiddleware(PipelineMiddleware):
    """Authentication middleware for the pipeline."""
    
    def priority(self) -> int:
        return 10
    
    async def handle(self, context: MiddlewareContext, next_middleware: Callable[[MiddlewareContext], Any]) -> MiddlewareContext:
        """Handle authentication."""
        auth_header = context.request.headers.get("Authorization")
        
        if not auth_header and self._requires_auth(context.request):
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if auth_header:
            # Validate token and set user context
            user = await self._validate_token(auth_header)
            if context.data is not None:
                if context.data is not None:
                    context.data["user"] = user
        
        return await next_middleware(context)  # type: ignore[no-any-return]
    
    def _requires_auth(self, request: Request) -> bool:
        """Check if the route requires authentication."""
        excluded_paths = ["/docs", "/redoc", "/openapi.json", "/health"]
        path = getattr(getattr(request, 'url', None), 'path', '')
        return not any(path.startswith(excluded_path) for excluded_path in excluded_paths)    
    async def _validate_token(self, auth_header: str) -> Optional[Dict[str, Any]]:
        """Validate authentication token."""
        # Implement token validation logic
        return {"id": 1, "email": "user@example.com"}


class RateLimitingMiddleware(PipelineMiddleware):
    """Rate limiting middleware for the pipeline."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.max_requests = config.get("max_requests", 60) if config else 60
        self.window_minutes = config.get("window_minutes", 1) if config else 1
        self.request_counts: Dict[str, Dict[str, Any]] = {}
    
    def priority(self) -> int:
        return 20
    
    async def handle(self, context: MiddlewareContext, next_middleware: Callable[[MiddlewareContext], Any]) -> MiddlewareContext:
        """Handle rate limiting."""
        client_ip = self._get_client_ip(context.request)
        current_time = time.time()
        
        # Clean old entries
        self._cleanup_old_entries(current_time)
        
        # Check rate limit
        if self._is_rate_limited(client_ip, current_time):
            raise HTTPException(status_code=429, detail="Too many requests")
        
        # Record request
        self._record_request(client_ip, current_time)
        
        return await next_middleware(context)  # type: ignore[no-any-return]
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_ip: str, current_time: float) -> bool:
        """Check if client is rate limited."""
        if client_ip not in self.request_counts:
            return False
        
        client_data = self.request_counts[client_ip]
        window_start = current_time - (self.window_minutes * 60)
        
        # Count requests in current window
        recent_requests = [
            req_time for req_time in client_data["requests"]
            if req_time > window_start
        ]
        
        return len(recent_requests) >= self.max_requests  # type: ignore[no-any-return]
    
    def _record_request(self, client_ip: str, current_time: float) -> None:
        """Record a request for the client."""
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {"requests": []}
        
        self.request_counts[client_ip]["requests"].append(current_time)
    
    def _cleanup_old_entries(self, current_time: float) -> None:
        """Clean up old request entries."""
        window_start = current_time - (self.window_minutes * 60)
        
        for client_ip in list(self.request_counts.keys()):
            client_data = self.request_counts[client_ip]
            client_data["requests"] = [
                req_time for req_time in client_data["requests"]
                if req_time > window_start
            ]
            
            # Remove clients with no recent requests
            if not client_data["requests"]:
                del self.request_counts[client_ip]


class CacheMiddleware(PipelineMiddleware):
    """Caching middleware for the pipeline."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.cache_duration = config.get("cache_duration", 300) if config else 300
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    def priority(self) -> int:
        return 30
    
    async def handle(self, context: MiddlewareContext, next_middleware: Callable[[MiddlewareContext], Any]) -> MiddlewareContext:
        """Handle caching."""
        if context.request.method != "GET":
            return await next_middleware(context)  # type: ignore[no-any-return]
        
        cache_key = self._generate_cache_key(context.request)
        
        # Check cache
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            context.response = cached_response
            return context
        
        # Continue pipeline
        context = await next_middleware(context)
        
        # Cache response
        if context.response and getattr(context.response, "status_code", 500) == 200:
            self._cache_response(cache_key, context.response)
        
        return context
    
    def _generate_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        method = getattr(request, 'method', 'UNKNOWN')
        path = getattr(getattr(request, 'url', None), 'path', 'UNKNOWN')
        params = str(getattr(request, 'query_params', {}))
        return f"{method}:{path}:{params}"    
    def _get_cached_response(self, cache_key: str) -> Optional[Response]:
        """Get response from cache."""
        if cache_key not in self.cache:
            return None
        
        cache_entry = self.cache[cache_key]
        if time.time() - cache_entry["timestamp"] > self.cache_duration:
            del self.cache[cache_key]
            return None
        
        return cache_entry["response"]  # type: ignore[no-any-return]
    
    def _cache_response(self, cache_key: str, response: Response) -> None:
        """Cache the response."""
        self.cache[cache_key] = {
            "response": response,
            "timestamp": time.time()
        }


class LoggingMiddleware(TerminableMiddleware):
    """Logging middleware for the pipeline."""
    
    def priority(self) -> int:
        return 40
    
    async def handle(self, context: MiddlewareContext, next_middleware: Callable[[MiddlewareContext], Any]) -> MiddlewareContext:
        """Handle request logging."""
        start_time = time.time()
        if context.data is not None:
            context.data["start_time"] = start_time
        
        method = getattr(context.request, 'method', 'UNKNOWN')
        path = getattr(getattr(context.request, 'url', None), 'path', 'UNKNOWN')
        self.logger.info(f"Request started: {method} {path}")        
        context = await next_middleware(context)
        
        duration = time.time() - start_time
        status_code = getattr(context.response, "status_code", 500) if context.response else "unknown"
        
        method = getattr(context.request, 'method', 'UNKNOWN')
        path = getattr(getattr(context.request, 'url', None), 'path', 'UNKNOWN')
        self.logger.info(
            f"Request completed: {method} {path} "
            f"[{status_code}] in {duration:.2f}s"
        )
        
        return context
    
    async def terminate(self, context: MiddlewareContext) -> None:
        """Log final request details."""
        if context.data and "start_time" in context.data:
            total_duration = time.time() - context.data.get("start_time", 0)
            self.logger.info(f"Request fully processed in {total_duration:.2f}s")


class ValidationMiddleware(PipelineMiddleware):
    """Request validation middleware."""
    
    def priority(self) -> int:
        return 15
    
    async def handle(self, context: MiddlewareContext, next_middleware: Callable[[MiddlewareContext], Any]) -> MiddlewareContext:
        """Handle request validation."""
        # Validate request headers
        if not self._validate_headers(context.request):
            raise HTTPException(status_code=400, detail="Invalid headers")
        
        # Validate content type for POST/PUT requests
        method = getattr(context.request, 'method', '')
        if method in ["POST", "PUT", "PATCH"]:
            if not self._validate_content_type(context.request):
                raise HTTPException(status_code=415, detail="Unsupported media type")
        
        return await next_middleware(context)  # type: ignore[no-any-return]
    
    def _validate_headers(self, request: Request) -> bool:
        """Validate request headers."""
        # Add custom header validation logic
        return True
    
    def _validate_content_type(self, request: Request) -> bool:
        """Validate content type."""
        content_type = request.headers.get("content-type", "")
        allowed_types = ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]
        return any(allowed_type in content_type for allowed_type in allowed_types)


# Helper functions for creating pipelines

def create_web_pipeline() -> LaravelPipeline:
    """Create a pipeline for web routes."""
    pipeline = LaravelPipeline()
    
    pipeline.pipe(ValidationMiddleware)
    pipeline.pipe(AuthenticationMiddleware)
    pipeline.pipe(RateLimitingMiddleware, {"max_requests": 120, "window_minutes": 1})
    pipeline.pipe(CacheMiddleware, {"cache_duration": 600})
    pipeline.pipe(LoggingMiddleware)
    
    return pipeline


def create_api_pipeline() -> LaravelPipeline:
    """Create a pipeline for API routes."""
    pipeline = LaravelPipeline()
    
    pipeline.pipe(ValidationMiddleware)
    pipeline.pipe(AuthenticationMiddleware)
    pipeline.pipe(RateLimitingMiddleware, {"max_requests": 60, "window_minutes": 1})
    pipeline.pipe(LoggingMiddleware)
    
    return pipeline


def create_admin_pipeline() -> LaravelPipeline:
    """Create a pipeline for admin routes."""
    pipeline = LaravelPipeline()
    
    pipeline.pipe(ValidationMiddleware)
    pipeline.pipe(AuthenticationMiddleware)
    pipeline.pipe(RateLimitingMiddleware, {"max_requests": 30, "window_minutes": 1})
    pipeline.pipe(LoggingMiddleware)
    
    return pipeline


def create_public_pipeline() -> LaravelPipeline:
    """Create a pipeline for public routes."""
    pipeline = LaravelPipeline()
    
    pipeline.pipe(ValidationMiddleware)
    pipeline.pipe(CacheMiddleware, {"cache_duration": 3600})
    pipeline.pipe(LoggingMiddleware)
    
    return pipeline