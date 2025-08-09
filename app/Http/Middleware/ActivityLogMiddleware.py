from __future__ import annotations

import time
from typing import Optional, Any, Dict, Callable, Awaitable, List
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.Services.ActivityLogService import ActivityLogService
from app.Services.AuthService import AuthService


class ActivityLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatically logging user activities and API requests.
    This middleware sets the current user context and optionally logs HTTP requests.
    """
    
    def __init__(
        self,
        app: Any,
        log_requests: bool = True,
        log_name: str = "api",
        exclude_paths: Optional[List[str]] = None,
        log_successful_only: bool = False
    ):
        """
        Initialize the activity log middleware.
        
        Args:
            app: FastAPI application instance
            log_requests: Whether to log HTTP requests
            log_name: Log name for HTTP request logs
            exclude_paths: List of paths to exclude from logging
            log_successful_only: Only log successful requests (2xx status codes)
        """
        super().__init__(app)
        self.log_requests = log_requests
        self.log_name = log_name
        self.exclude_paths = exclude_paths or [
            "/docs",
            "/openapi.json",
            "/health",
            "/metrics",
            "/favicon.ico"
        ]
        self.log_successful_only = log_successful_only
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """
        Process the request and set up activity logging context.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/route handler
            
        Returns:
            The HTTP response
        """
        start_time = time.time()
        
        # Set current user context for activity logging
        current_user = await self._get_current_user(request)
        ActivityLogService.set_current_user(current_user)
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Log the HTTP request if enabled
            if self._should_log_request(request, response):
                await self._log_http_request(request, response, start_time)
            
            return response
        
        except Exception as e:
            # Log failed requests if enabled
            if self.log_requests and not self.log_successful_only:
                await self._log_failed_request(request, e, start_time)
            raise
        
        finally:
            # Clear the current user context
            ActivityLogService.set_current_user(None)
    
    async def _get_current_user(self, request: Request) -> Optional[Any]:
        """
        Extract the current user from the request.
        
        Args:
            request: The HTTP request
            
        Returns:
            The current user or None if not authenticated
        """
        try:
            # Try to get user from Authorization header (JWT)
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                from config.database import get_database
                db_gen = get_database()
                db = next(db_gen)
                try:
                    auth_service = AuthService(db)
                    user = auth_service.get_current_user(token)
                finally:
                    db.close()
                return user
            
            # Try to get user from OAuth2 token (if implementing OAuth2 middleware)
            # This would be implemented based on your OAuth2 setup
            
            return None
        
        except Exception:
            # If there's any error getting the user, just return None
            return None
    
    def _should_log_request(self, request: Request, response: Response) -> bool:
        """
        Determine if the request should be logged.
        
        Args:
            request: The HTTP request
            response: The HTTP response
            
        Returns:
            True if the request should be logged
        """
        if not self.log_requests:
            return False
        
        # Check if path is in exclude list
        url_path = getattr(getattr(request, 'url', None), 'path', '')
        if any(url_path.startswith(path) for path in self.exclude_paths):
            return False
        
        # Check if we only log successful requests
        if self.log_successful_only and not (200 <= response.status_code < 300):
            return False
        
        return True
    
    async def _log_http_request(self, request: Request, response: Response, start_time: float) -> None:
        """
        Log an HTTP request.
        
        Args:
            request: The HTTP request
            response: The HTTP response
            start_time: When the request started processing
        """
        try:
            process_time = round((time.time() - start_time) * 1000, 2)  # milliseconds
            
            # Prepare request data
            properties = {
                "method": getattr(request, 'method', 'UNKNOWN'),
                "url": str(getattr(request, 'url', '')),
                "path": getattr(getattr(request, 'url', None), 'path', ''),
                "query_params": dict(request.query_params),
                "status_code": response.status_code,
                "process_time_ms": process_time,
                "user_agent": request.headers.get("user-agent"),
                "ip_address": self._get_client_ip(request),
                "referer": request.headers.get("referer")
            }
            
            # Add request body for non-GET requests (be careful with sensitive data)
            method = getattr(request, 'method', 'GET')
            if method != "GET":
                # Only log content type, not actual body for security
                properties["content_type"] = request.headers.get("content-type")
                properties["content_length"] = request.headers.get("content-length")            
            # Determine description based on status code
            if 200 <= response.status_code < 300:
                method = getattr(request, 'method', 'UNKNOWN')
                path = getattr(getattr(request, 'url', None), 'path', '')
                description = f"Successful {method} request to {path}"
            elif 400 <= response.status_code < 500:
                description = f"Client error {request.method} request to {request.url.path}"
            elif 500 <= response.status_code < 600:
                description = f"Server error {request.method} request to {request.url.path}"
            else:
                description = f"{request.method} request to {request.url.path}"
            
            ActivityLogService.log_activity(
                log_name=self.log_name,
                description=description,
                event="http_request",
                properties=properties
            )
        
        except Exception as e:
            # Don't let logging errors break the application
            # In production, you might want to use a proper logger here
            print(f"Failed to log HTTP request: {e}")
    
    async def _log_failed_request(self, request: Request, exception: Exception, start_time: float) -> None:
        """
        Log a failed HTTP request.
        
        Args:
            request: The HTTP request
            exception: The exception that occurred
            start_time: When the request started processing
        """
        try:
            process_time = round((time.time() - start_time) * 1000, 2)  # milliseconds
            
            properties = {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "exception": str(exception),
                "exception_type": exception.__class__.__name__,
                "process_time_ms": process_time,
                "user_agent": request.headers.get("user-agent"),
                "ip_address": self._get_client_ip(request),
                "referer": request.headers.get("referer")
            }
            
            description = f"Failed {request.method} request to {request.url.path}: {exception.__class__.__name__}"
            
            ActivityLogService.log_activity(
                log_name=self.log_name,
                description=description,
                event="http_request_failed",
                properties=properties
            )
        
        except Exception as log_error:
            # Don't let logging errors break the application
            print(f"Failed to log failed HTTP request: {log_error}")
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Get the client IP address from the request.
        
        Args:
            request: The HTTP request
            
        Returns:
            The client IP address or None
        """
        # Check for forwarded headers (when behind a proxy/load balancer)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        if hasattr(request, "client") and request.client:
            return request.client.host        
        return None