"""OAuth2 CORS Middleware - Google IDP Style

This middleware handles CORS headers for OAuth2 endpoints to support 
cross-origin requests similar to Google's Identity Provider.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List, Set
from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import Response as FastAPIResponse
from fastapi.types import ASGIApp
from starlette.types import RequestResponseEndpoint
import re

class OAuth2CORSMiddleware(BaseHTTPMiddleware):  # type: ignore[misc,no-any-unimported]
    """CORS middleware specifically for OAuth2 endpoints."""
    
    def __init__(
        self,
        app: ASGIApp,
        allow_origins: Optional[List[str]] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        allow_credentials: bool = True,
        max_age: int = 3600
    ) -> None:
        super().__init__(app)
        
        # Default configurations similar to Google's OAuth2 implementation
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or [
            "GET", "POST", "OPTIONS", "HEAD"
        ]
        self.allow_headers = allow_headers or [
            "Accept",
            "Accept-Language", 
            "Authorization",
            "Content-Language",
            "Content-Type",
            "Origin",
            "X-Requested-With",
            "User-Agent",
            "Cache-Control",
            "Pragma"
        ]
        self.expose_headers = expose_headers or [
            "Cache-Control",
            "Content-Language",
            "Content-Type",
            "Expires",
            "Last-Modified",
            "Pragma"
        ]
        self.allow_credentials = allow_credentials
        self.max_age = max_age
        
        # Compile origin patterns for performance
        self.origin_patterns = self._compile_origin_patterns(self.allow_origins)
    
    def _compile_origin_patterns(self, origins: List[str]) -> List[re.Pattern[str]]:
        """Compile origin patterns for efficient matching."""
        patterns = []
        for origin in origins:
            if origin == "*":
                patterns.append(re.compile(r".*"))
            else:
                # Escape special regex characters and allow wildcards
                pattern = origin.replace("*", ".*").replace(".", r"\.")
                patterns.append(re.compile(f"^{pattern}$"))
        return patterns
    
    def _is_oauth2_endpoint(self, request: Request) -> bool:
        """Check if request is for an OAuth2 endpoint."""
        path = request.url.path
        oauth2_paths = [
            "/oauth",
            "/.well-known/openid_configuration",
            "/.well-known/jwks.json"
        ]
        
        return any(path.startswith(oauth_path) for oauth_path in oauth2_paths)
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed."""
        if not origin:
            return False
            
        for pattern in self.origin_patterns:
            if pattern.match(origin):
                return True
        return False
    
    def _get_cors_headers(self, request: Request) -> Dict[str, str]:
        """Get CORS headers for the request."""
        headers = {}
        
        # Get origin from request
        origin = request.headers.get("origin", "")
        
        # Set Access-Control-Allow-Origin
        if "*" in self.allow_origins:
            headers["Access-Control-Allow-Origin"] = "*"
        elif self._is_origin_allowed(origin):
            headers["Access-Control-Allow-Origin"] = origin
            headers["Vary"] = "Origin"
        
        # Set other CORS headers
        headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        
        if self.expose_headers:
            headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        
        if self.allow_credentials and "*" not in self.allow_origins:
            headers["Access-Control-Allow-Credentials"] = "true"
        
        # Set max age for preflight requests
        if request.method == "OPTIONS":
            headers["Access-Control-Max-Age"] = str(self.max_age)
        
        # Additional security headers for OAuth2
        headers.update({
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        })
        
        return headers
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Handle CORS for OAuth2 endpoints."""
        
        # Only apply CORS to OAuth2 endpoints
        if not self._is_oauth2_endpoint(request):
            return await call_next(request)
        
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            response = FastAPIResponse(status_code=204)
            cors_headers = self._get_cors_headers(request)
            for key, value in cors_headers.items():
                response.headers[key] = value
            return response
        
        # Process the request
        response = await call_next(request)
        
        # Add CORS headers to response
        cors_headers = self._get_cors_headers(request)
        for key, value in cors_headers.items():
            response.headers[key] = value
        
        return response


class OAuth2SecurityHeaders:
    """Security headers specifically for OAuth2 endpoints."""
    
    @staticmethod
    def get_token_endpoint_headers() -> Dict[str, str]:
        """Get security headers for token endpoint."""
        return {
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Content-Type": "application/json",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
        }
    
    @staticmethod
    def get_authorization_endpoint_headers() -> Dict[str, str]:
        """Get security headers for authorization endpoint."""
        return {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",  # Allow framing from same origin for consent screen
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        }
    
    @staticmethod
    def get_userinfo_endpoint_headers() -> Dict[str, str]:
        """Get security headers for userinfo endpoint."""
        return {
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Content-Type": "application/json",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
    
    @staticmethod
    def get_jwks_endpoint_headers() -> Dict[str, str]:
        """Get security headers for JWKS endpoint."""
        return {
            "Cache-Control": "public, max-age=3600",  # Cache public keys for 1 hour
            "Content-Type": "application/json",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
    
    @staticmethod
    def get_discovery_endpoint_headers() -> Dict[str, str]:
        """Get security headers for discovery endpoint."""
        return {
            "Cache-Control": "public, max-age=86400",  # Cache discovery for 24 hours
            "Content-Type": "application/json",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }


def create_oauth2_cors_middleware(
    allowed_origins: Optional[List[str]] = None,
    development_mode: bool = False
) -> OAuth2CORSMiddleware:
    """
    Create OAuth2 CORS middleware with appropriate settings.
    
    Args:
        allowed_origins: List of allowed origins. Defaults to ["*"] in dev, specific origins in prod
        development_mode: Whether to use development-friendly settings
    
    Returns:
        Configured OAuth2CORSMiddleware instance
    """
    
    if development_mode:
        # Development settings - more permissive
        origins = allowed_origins or [
            "http://localhost:3000",
            "http://localhost:8080", 
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8000"
        ]
        allow_credentials = True
    else:
        # Production settings - more restrictive
        origins = allowed_origins or ["https://yourdomain.com"]
        allow_credentials = True
    
    return OAuth2CORSMiddleware(
        app=None,  # Will be set by FastAPI
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
        allow_headers=[
            "Accept",
            "Accept-Language", 
            "Authorization",
            "Content-Language",
            "Content-Type",
            "Origin",
            "X-Requested-With",
            "User-Agent",
            "Cache-Control",
            "Pragma"
        ],
        expose_headers=[
            "Cache-Control",
            "Content-Language",
            "Content-Type", 
            "Expires",
            "Last-Modified",
            "Pragma"
        ],
        allow_credentials=allow_credentials,
        max_age=3600
    )