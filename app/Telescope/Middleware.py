from __future__ import annotations

import time
import uuid
import psutil
import os
from typing import Callable, Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .TelescopeManager import TelescopeManager
from .Facades import Telescope


class TelescopeMiddleware:
    """
    FastAPI middleware for capturing request data for Telescope.
    
    This middleware captures HTTP requests, responses, and performance
    metrics for debugging and monitoring purposes.
    """
    
    def __init__(self, app: Callable) -> None:
        self.app = app
        self.process = psutil.Process(os.getpid())
    
    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        """Process HTTP requests through Telescope monitoring."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Skip telescope routes to avoid infinite loops
        path = scope.get("path", "")
        if path.startswith("/telescope") or not Telescope.is_recording():
            await self.app(scope, receive, send)
            return
        
        # Start timing
        start_time = time.time()
        memory_start = self._get_memory_usage()
        
        # Create request object for easier access
        request = Request(scope, receive)
        
        # Start a new Telescope batch for this request
        batch_id = Telescope.start_batch()
        
        # Store request body if it exists (for POST/PUT requests)
        request_body = None
        if scope.get("method") in ["POST", "PUT", "PATCH"]:
            try:
                request_body = await self._capture_request_body(request)
            except Exception:
                request_body = "[Could not capture request body]"
        
        # Response capture setup
        response_data = {"status_code": 200, "headers": {}, "body": None}
        
        async def send_wrapper(message: Dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                response_data["status_code"] = message["status"]
                response_data["headers"] = dict(message.get("headers", []))
            
            elif message["type"] == "http.response.body":
                if message.get("body"):
                    # Capture response body (limit size)
                    body = message["body"]
                    if len(body) > 10000:  # Limit to 10KB
                        response_data["body"] = body[:10000] + b"... [truncated]"
                    else:
                        response_data["body"] = body
            
            await send(message)
        
        try:
            # Process the request
            await self.app(scope, receive, send_wrapper)
            
        except Exception as e:
            # Record the exception
            Telescope.record_exception(e, {
                "request": {
                    "method": scope.get("method"),
                    "path": path,
                    "query_string": scope.get("query_string", b"").decode(),
                }
            })
            
            # Re-raise the exception
            raise
        
        finally:
            # Calculate timing and memory
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # Convert to milliseconds
            memory_peak = self._get_memory_usage()
            memory_usage = memory_peak - memory_start
            
            # Create response object
            response = Response(
                status_code=response_data["status_code"],
                headers=response_data["headers"]
            )
            
            # Record the request through Telescope
            await self._record_request(
                request,
                response,
                duration,
                memory_peak,
                request_body,
                response_data.get("body")
            )
            
            # End the Telescope batch
            await Telescope.end_batch()
    
    async def _capture_request_body(self, request: Request) -> str:
        """Safely capture request body."""
        try:
            # Get raw body
            body = await request.body()
            
            # Try to decode as text
            if body:
                try:
                    return body.decode('utf-8')
                except UnicodeDecodeError:
                    return f"[Binary data: {len(body)} bytes]"
            
            return ""
            
        except Exception:
            return "[Could not read request body]"
    
    async def _record_request(
        self,
        request: Request,
        response: Response,
        duration: float,
        memory_peak: int,
        request_body: str = None,
        response_body: bytes = None
    ) -> None:
        """Record request data in Telescope."""
        request_watcher = Telescope.get_watcher('request')
        if request_watcher:
            # Add request body to the request object for the watcher
            if request_body is not None:
                setattr(request, '_telescope_body', request_body)
            
            # Add response body to the response object
            if response_body is not None:
                setattr(response, '_telescope_body', response_body)
            
            request_watcher.record_request(
                request,
                response, 
                duration,
                memory_peak
            )
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            return self.process.memory_info().rss
        except Exception:
            return 0


class TelescopeExceptionMiddleware:
    """
    Exception handling middleware for Telescope.
    
    Captures unhandled exceptions for debugging purposes.
    """
    
    def __init__(self, app: Callable) -> None:
        self.app = app
    
    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        """Capture exceptions in Telescope."""
        try:
            await self.app(scope, receive, send)
        except Exception as e:
            # Record the exception in Telescope
            if Telescope.is_recording():
                context = {
                    "scope": {
                        "type": scope.get("type"),
                        "method": scope.get("method"),
                        "path": scope.get("path"),
                        "query_string": scope.get("query_string", b"").decode(),
                    }
                }
                
                Telescope.record_exception(e, context)
            
            # Re-raise the exception
            raise


def add_telescope_middleware(app) -> None:
    """Add Telescope middleware to FastAPI app."""
    # Add exception middleware first (outer layer)
    app.middleware("http")(TelescopeExceptionMiddleware)
    
    # Add request middleware (inner layer)
    app.middleware("http")(TelescopeMiddleware)