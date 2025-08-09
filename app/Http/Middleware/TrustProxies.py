from __future__ import annotations

from typing import List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class TrustProxies(BaseHTTPMiddleware):
    """Laravel-style middleware for trusting proxies."""
    
    # List of trusted proxies
    proxies: List[str] = ["127.0.0.1"]
    
    # Headers to trust from proxies
    headers = {
        "forwarded": "FORWARDED",
        "x_forwarded_for": "X-FORWARDED-FOR",
        "x_forwarded_host": "X-FORWARDED-HOST",
        "x_forwarded_port": "X-FORWARDED-PORT",
        "x_forwarded_proto": "X-FORWARDED-PROTO",
    }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request."""
        # Trust proxy headers if request comes from trusted proxy
        if self._is_trusted_proxy(request):
            self._set_trusted_headers(request)
        
        response = await call_next(request)
        return response
    
    def _is_trusted_proxy(self, request: Request) -> bool:
        """Check if request comes from a trusted proxy."""
        client_ip = getattr(request.client, 'host', None) if hasattr(request, 'client') and request.client else None
        return client_ip in self.proxies if client_ip else False
    
    def _set_trusted_headers(self, request: Request) -> None:
        """Set trusted proxy headers."""
        # This would implement the logic to trust and process proxy headers
        # For now, this is a placeholder
        pass