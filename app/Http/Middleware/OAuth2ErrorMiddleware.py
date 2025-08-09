"""OAuth2 Error Middleware - Google IDP Style

This middleware handles OAuth2 errors in a consistent way similar to Google's
Identity Provider error responses and formatting.
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.types import ASGIApp
from starlette.types import RequestResponseEndpoint
import urllib.parse
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class OAuth2ErrorMiddleware(BaseHTTPMiddleware):  # type: ignore[misc,no-any-unimported]
    """Middleware for standardized OAuth2 error handling."""
    
    def __init__(self, app: ASGIApp, debug: bool = False) -> None:
        super().__init__(app)
        self.debug = debug
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Handle OAuth2 errors in a Google-style format."""
        try:
            response = await call_next(request)
            return response
        except HTTPException as exc:
            # Check if this is an OAuth2 endpoint
            if self._is_oauth2_endpoint(request):
                return self._handle_oauth2_error(request, exc)
            else:
                # Re-raise for non-OAuth2 endpoints
                raise exc
        except Exception as exc:
            logger.exception("Unexpected error in OAuth2 middleware")
            if self._is_oauth2_endpoint(request):
                return self._handle_oauth2_error(
                    request,
                    HTTPException(
                        status_code=500,
                        detail="Internal server error"
                    )
                )
            else:
                raise exc
    
    def _is_oauth2_endpoint(self, request: Request) -> bool:
        """Check if request is for an OAuth2 endpoint."""
        path = request.url.path
        oauth2_paths = [
            "/oauth/authorize",
            "/oauth/token", 
            "/oauth/introspect",
            "/oauth/revoke",
            "/oauth/userinfo",
            "/oauth/jwks",
            "/oauth/discovery",
            "/oauth/consent",
            "/.well-known/openid_configuration",
            "/.well-known/jwks.json"
        ]
        
        return any(path.startswith(oauth_path) for oauth_path in oauth2_paths)
    
    def _handle_oauth2_error(
        self,
        request: Request,
        exc: HTTPException
    ) -> Response:
        """Handle OAuth2 error with Google-style formatting."""
        
        # Extract error details
        error_detail = str(exc.detail) if exc.detail else "Invalid request"
        status_code = exc.status_code
        
        # Map HTTP status codes to OAuth2 error codes
        oauth2_error = self._map_status_to_oauth2_error(status_code, error_detail)
        
        # Check if this should be a redirect error (authorization endpoint)
        if request.url.path.startswith("/oauth/authorize"):
            return self._create_authorization_error_redirect(request, oauth2_error)
        
        # For token endpoint and other JSON endpoints
        return self._create_json_error_response(oauth2_error, status_code)
    
    def _map_status_to_oauth2_error(
        self,
        status_code: int,
        detail: str
    ) -> Dict[str, Any]:
        """Map HTTP status codes to OAuth2 error codes."""
        
        # Default error mapping
        error_map = {
            400: "invalid_request",
            401: "invalid_client", 
            403: "access_denied",
            404: "invalid_request",
            405: "unsupported_response_type",
            429: "temporarily_unavailable",
            500: "server_error",
            502: "server_error",
            503: "temporarily_unavailable"
        }
        
        # Check for specific error patterns in detail
        detail_lower = detail.lower()
        
        if "client" in detail_lower and "invalid" in detail_lower:
            error_code = "invalid_client"
        elif "grant" in detail_lower and ("unsupported" in detail_lower or "invalid" in detail_lower):
            error_code = "unsupported_grant_type"
        elif "scope" in detail_lower and "invalid" in detail_lower:
            error_code = "invalid_scope"
        elif "redirect" in detail_lower and "uri" in detail_lower:
            error_code = "invalid_request"
        elif "code" in detail_lower and ("invalid" in detail_lower or "expired" in detail_lower):
            error_code = "invalid_grant"
        elif "token" in detail_lower and ("invalid" in detail_lower or "expired" in detail_lower):
            error_code = "invalid_grant"
        elif "access" in detail_lower and "denied" in detail_lower:
            error_code = "access_denied"
        elif "user" in detail_lower and "denied" in detail_lower:
            error_code = "access_denied"
        else:
            error_code = error_map.get(status_code, "invalid_request")
        
        return {
            "error": error_code,
            "error_description": detail,
            "error_uri": f"https://docs.oauth.org/2/errors#{error_code}",
        }
    
    def _create_authorization_error_redirect(
        self,
        request: Request,
        oauth2_error: Dict[str, Any]
    ) -> RedirectResponse:
        """Create error redirect for authorization endpoint."""
        
        # Get redirect_uri from query parameters
        redirect_uri = request.query_params.get("redirect_uri")
        state = request.query_params.get("state")
        
        if not redirect_uri:
            # If no redirect_uri, return JSON error
            return self._create_json_error_response(oauth2_error, 400)
        
        # Build error redirect
        error_params = {
            "error": oauth2_error["error"],
            "error_description": oauth2_error["error_description"]
        }
        
        if state:
            error_params["state"] = state
        
        # Create redirect URL with error parameters
        parsed_url = urllib.parse.urlparse(redirect_uri)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        query_params.update(error_params)
        
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        error_redirect_url = urllib.parse.urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))
        
        return RedirectResponse(url=error_redirect_url, status_code=302)
    
    def _create_json_error_response(
        self,
        oauth2_error: Dict[str, Any],
        status_code: int
    ) -> JSONResponse:
        """Create JSON error response with Google-style formatting."""
        
        # Google-style error response format
        error_response = {
            "error": oauth2_error["error"],
            "error_description": oauth2_error["error_description"]
        }
        
        # Add error_uri if available
        if "error_uri" in oauth2_error:
            error_response["error_uri"] = oauth2_error["error_uri"]
        
        # Add debug information if in debug mode
        if self.debug:
            error_response["debug"] = {
                "timestamp": str(datetime.utcnow()),
                "status_code": status_code
            }
        
        # Set proper headers
        headers = {
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
        
        return JSONResponse(
            content=error_response,
            status_code=status_code,
            headers=headers
        )


class OAuth2ErrorHandler:
    """Helper class for creating OAuth2 errors."""
    
    @staticmethod
    def invalid_request(description: str = "The request is missing a required parameter.") -> HTTPException:
        """Create invalid_request error."""
        return HTTPException(
            status_code=400,
            detail=description
        )
    
    @staticmethod 
    def invalid_client(description: str = "Client authentication failed.") -> HTTPException:
        """Create invalid_client error."""
        return HTTPException(
            status_code=401,
            detail=description
        )
    
    @staticmethod
    def invalid_grant(description: str = "The authorization grant is invalid.") -> HTTPException:
        """Create invalid_grant error."""
        return HTTPException(
            status_code=400,
            detail=description
        )
    
    @staticmethod
    def unauthorized_client(description: str = "The client is not authorized.") -> HTTPException:
        """Create unauthorized_client error."""
        return HTTPException(
            status_code=400,
            detail=description
        )
    
    @staticmethod
    def unsupported_grant_type(description: str = "The grant type is not supported.") -> HTTPException:
        """Create unsupported_grant_type error."""
        return HTTPException(
            status_code=400,
            detail=description
        )
    
    @staticmethod
    def invalid_scope(description: str = "The requested scope is invalid.") -> HTTPException:
        """Create invalid_scope error."""
        return HTTPException(
            status_code=400,
            detail=description
        )
    
    @staticmethod
    def access_denied(description: str = "The resource owner denied the request.") -> HTTPException:
        """Create access_denied error."""
        return HTTPException(
            status_code=403,
            detail=description
        )
    
    @staticmethod
    def server_error(description: str = "The server encountered an unexpected condition.") -> HTTPException:
        """Create server_error error."""
        return HTTPException(
            status_code=500,
            detail=description
        )
    
    @staticmethod
    def temporarily_unavailable(description: str = "The service is temporarily overloaded.") -> HTTPException:
        """Create temporarily_unavailable error.""" 
        return HTTPException(
            status_code=503,
            detail=description
        )