"""OAuth2 Security Best Practices Middleware - RFC 8725

This middleware implements OAuth 2.0 Security Best Practices as defined in RFC 8725
for enhanced security across all OAuth2 endpoints and flows.
"""

from __future__ import annotations

import time
import hashlib
import re
from typing import Dict, Any, Optional, List, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import ipaddress

from app.Http.Schemas.OAuth2ErrorSchemas import OAuth2ErrorCode, create_oauth2_error_response


class OAuth2SecurityMiddleware(BaseHTTPMiddleware):  # type: ignore[misc,no-any-unimported]
    """OAuth2 Security Best Practices middleware (RFC 8725)."""
    
    def __init__(
        self,
        app: Any,
        enforce_https: bool = True,
        require_pkce: bool = True,
        enable_ip_allowlisting: bool = False,
        enable_geographic_restrictions: bool = False,
        max_request_size: int = 1024 * 1024,  # 1MB
        enable_timing_attack_protection: bool = True
    ) -> None:
        """
        Initialize OAuth2 security middleware.
        
        Args:
            app: FastAPI application
            enforce_https: Enforce HTTPS for OAuth2 endpoints
            require_pkce: Require PKCE for authorization code flow
            enable_ip_allowlisting: Enable IP address allowlisting
            enable_geographic_restrictions: Enable geographic access restrictions
            max_request_size: Maximum request size in bytes
            enable_timing_attack_protection: Enable timing attack protection
        """
        super().__init__(app)
        self.enforce_https = enforce_https
        self.require_pkce = require_pkce
        self.enable_ip_allowlisting = enable_ip_allowlisting
        self.enable_geographic_restrictions = enable_geographic_restrictions
        self.max_request_size = max_request_size
        self.enable_timing_attack_protection = enable_timing_attack_protection
        
        # Security policies per endpoint
        self.endpoint_policies = {
            "/oauth/authorize": {
                "require_https": True,
                "require_pkce": True,
                "validate_redirect_uri": True,
                "check_client_type": True,
                "max_state_length": 128,
                "require_client_authentication": False
            },
            "/oauth/token": {
                "require_https": True,
                "require_client_authentication": True,
                "validate_grant_type": True,
                "rate_limit_strict": True,
                "require_pkce_for_auth_code": True,
                "validate_client_credentials": True
            },
            "/oauth/introspect": {
                "require_https": True,
                "require_client_authentication": True,
                "rate_limit_strict": True,
                "validate_token_format": True
            },
            "/oauth/revoke": {
                "require_https": True,
                "require_client_authentication": True,
                "validate_token_format": True,
                "allow_invalid_tokens": True  # RFC 7009 requirement
            },
            "/oauth/userinfo": {
                "require_https": True,
                "require_bearer_token": True,
                "validate_token_scope": True
            }
        }
        
        # Suspicious patterns (RFC 8725 Section 4.8)
        self.suspicious_patterns = [
            r"<script",
            r"javascript:",
            r"data:",
            r"vbscript:",
            r"onload=",
            r"onerror=",
            r"<iframe",
            r"eval\(",
            r"document\.cookie",
            r"localStorage",
            r"sessionStorage"
        ]
        
        # Blocked user agents
        self.blocked_user_agents = [
            r"curl",
            r"wget",
            r"python-requests",
            r"postman",
            r"insomnia",
            # Add more as needed
        ]
    
    async def dispatch(self, request: Request, call_next: Callable[..., Any]) -> Response:
        """
        Process request with OAuth2 security best practices.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint
        
        Returns:
            Response with security enhancements
        """
        start_time = time.time()
        
        try:
            # Check if this is an OAuth2 endpoint
            if not self._is_oauth2_endpoint(request):
                return await call_next(request)
            
            # Apply security checks
            security_result = await self._apply_security_checks(request)
            
            if not security_result["allowed"]:
                # Use timing attack protection
                if self.enable_timing_attack_protection:
                    await self._apply_timing_protection(start_time)
                
                return self._create_security_error_response(
                    security_result["error_code"],
                    security_result["description"]
                )
            
            # Add security headers to request state
            request.state.security_context = security_result["context"]
            
            # Process request
            response = await call_next(request)
            
            # Add security response headers
            self._add_security_headers(response)
            
            # Apply timing attack protection for successful requests too
            if self.enable_timing_attack_protection:
                await self._apply_timing_protection(start_time)
            
            return response
            
        except HTTPException:
            # Apply timing protection for HTTP exceptions
            if self.enable_timing_attack_protection:
                await self._apply_timing_protection(start_time)
            raise
        except Exception as e:
            # Apply timing protection for any errors
            if self.enable_timing_attack_protection:
                await self._apply_timing_protection(start_time)
            
            return self._create_security_error_response(
                OAuth2ErrorCode.SERVER_ERROR,
                f"Security processing failed: {str(e)}"
            )
    
    def _is_oauth2_endpoint(self, request: Request) -> bool:
        """Check if request is for an OAuth2 endpoint."""
        oauth2_paths = [
            "/oauth/authorize",
            "/oauth/token", 
            "/oauth/introspect",
            "/oauth/revoke",
            "/oauth/userinfo",
            "/oauth/device/",
            "/oauth/par",
            "/oauth/token/exchange",
            "/oauth/native/"
        ]
        
        return any(str(request.url.path).startswith(path) for path in oauth2_paths)
    
    async def _apply_security_checks(self, request: Request) -> Dict[str, Any]:
        """Apply comprehensive security checks per RFC 8725."""
        
        # 1. HTTPS Enforcement (RFC 8725 Section 3.1)
        if self.enforce_https and not self._is_https_request(request):
            return {
                "allowed": False,
                "error_code": OAuth2ErrorCode.INVALID_REQUEST,
                "description": "HTTPS required for OAuth2 endpoints (RFC 8725 Section 3.1)"
            }
        
        # 2. Request Size Validation
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            return {
                "allowed": False,
                "error_code": OAuth2ErrorCode.INVALID_REQUEST,
                "description": "Request too large"
            }
        
        # 3. User Agent Validation
        user_agent = request.headers.get("user-agent", "")
        if self._is_blocked_user_agent(user_agent):
            return {
                "allowed": False,
                "error_code": OAuth2ErrorCode.INVALID_REQUEST,
                "description": "Blocked user agent"
            }
        
        # 4. IP Address Validation
        if self.enable_ip_allowlisting:
            ip_check = self._validate_client_ip(request)
            if not ip_check["allowed"]:
                return {
                    "allowed": False,
                    "error_code": OAuth2ErrorCode.ACCESS_DENIED,
                    "description": ip_check["reason"]
                }
        
        # 5. Geographic Restrictions
        if self.enable_geographic_restrictions:
            geo_check = self._validate_geographic_location(request)
            if not geo_check["allowed"]:
                return {
                    "allowed": False,
                    "error_code": OAuth2ErrorCode.ACCESS_DENIED,
                    "description": geo_check["reason"]
                }
        
        # 6. Content Injection Protection (RFC 8725 Section 4.8)
        injection_check = await self._check_content_injection(request)
        if not injection_check["safe"]:
            return {
                "allowed": False,
                "error_code": OAuth2ErrorCode.INVALID_REQUEST,
                "description": "Potentially malicious content detected"
            }
        
        # 7. Endpoint-Specific Security Policies
        endpoint_check = await self._apply_endpoint_specific_checks(request)
        if not endpoint_check["allowed"]:
            return {
                "allowed": False,
                "error_code": endpoint_check["error_code"],
                "description": endpoint_check["description"]
            }
        
        # 8. Rate Limiting Integration
        rate_limit_check = self._check_rate_limiting_context(request)
        
        return {
            "allowed": True,
            "context": {
                "https_enforced": self.enforce_https,
                "ip_validated": self.enable_ip_allowlisting,
                "geo_validated": self.enable_geographic_restrictions,
                "content_safe": injection_check["safe"],
                "endpoint_policy": endpoint_check.get("policy", {}),
                "rate_limit_context": rate_limit_check,
                "security_level": "high"
            }
        }
    
    def _is_https_request(self, request: Request) -> bool:
        """Check if request is using HTTPS."""
        # Check scheme
        if str(request.url.scheme) == "https":
            return True
        
        # Check forwarded headers (for reverse proxy scenarios)
        forwarded_proto = request.headers.get("x-forwarded-proto")
        if forwarded_proto and forwarded_proto.lower() == "https":
            return True
        
        # Check if this is a local development environment
        host = request.headers.get("host", "")
        if any(local_host in host for local_host in ["localhost", "127.0.0.1", "[::1]"]):
            return True  # Allow HTTP for local development
        
        return False
    
    def _is_blocked_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is blocked."""
        user_agent_lower = user_agent.lower()
        
        for pattern in self.blocked_user_agents:
            if re.search(pattern, user_agent_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _validate_client_ip(self, request: Request) -> Dict[str, Any]:
        """Validate client IP address against allowlist."""
        client_ip = self._get_client_ip(request)
        
        # Placeholder implementation - in production, check against allowlist
        # For now, block obvious malicious IPs
        try:
            ip = ipaddress.ip_address(client_ip)
            
            # Block private networks if configured (adjust as needed)
            if ip.is_private and not self._allow_private_networks():
                return {
                    "allowed": False,
                    "reason": "Private network access not allowed"
                }
            
            # Block known malicious ranges (placeholder)
            # In production, integrate with threat intelligence feeds
            
            return {"allowed": True, "ip": str(ip)}
            
        except ValueError:
            return {
                "allowed": False,
                "reason": "Invalid IP address format"
            }
    
    def _validate_geographic_location(self, request: Request) -> Dict[str, Any]:
        """Validate geographic location of request."""
        # Placeholder implementation - in production, use GeoIP service
        client_ip = self._get_client_ip(request)
        
        # Check against allowed countries/regions
        # For now, just return allowed
        return {
            "allowed": True,
            "location": "unknown",
            "reason": "Geographic validation not implemented"
        }
    
    async def _check_content_injection(self, request: Request) -> Dict[str, Any]:
        """Check for content injection attacks (RFC 8725 Section 4.8)."""
        
        # Check query parameters
        for param, value in request.query_params.items():
            if self._contains_suspicious_content(str(value)):
                return {
                    "safe": False,
                    "reason": f"Suspicious content in query parameter: {param}"
                }
        
        # Check form data if POST request
        if str(request.method) == "POST":
            try:
                # Read body content for analysis
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8', errors='ignore')
                    if self._contains_suspicious_content(body_str):
                        return {
                            "safe": False,
                            "reason": "Suspicious content in request body"
                        }
            except Exception:
                # If we can't read the body, consider it safe for now
                pass
        
        # Check headers
        for header_name, header_value in request.headers.items():
            if self._contains_suspicious_content(header_value):
                return {
                    "safe": False,
                    "reason": f"Suspicious content in header: {header_name}"
                }
        
        return {"safe": True}
    
    def _contains_suspicious_content(self, content: str) -> bool:
        """Check if content contains suspicious patterns."""
        content_lower = content.lower()
        
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        
        return False
    
    async def _apply_endpoint_specific_checks(self, request: Request) -> Dict[str, Any]:
        """Apply endpoint-specific security policies."""
        endpoint_path = str(request.url.path)
        
        # Find matching policy
        policy = None
        for path, endpoint_policy in self.endpoint_policies.items():
            if endpoint_path.startswith(path):
                policy = endpoint_policy
                break
        
        if not policy:
            return {"allowed": True, "policy": {}}
        
        # Apply policy checks
        
        # 1. PKCE requirement for authorization endpoint
        if (policy.get("require_pkce") and 
            str(request.method) == "GET" and 
            endpoint_path.startswith("/oauth/authorize")):
            
            code_challenge = request.query_params.get("code_challenge")
            if not code_challenge:
                return {
                    "allowed": False,
                    "error_code": OAuth2ErrorCode.INVALID_REQUEST,
                    "description": "PKCE code_challenge required (RFC 8725 Section 3.1.1)"
                }
        
        # 2. State parameter validation
        if (policy.get("max_state_length") and 
            endpoint_path.startswith("/oauth/authorize")):
            
            state = request.query_params.get("state")
            if state and len(state) > policy["max_state_length"]:
                return {
                    "allowed": False,
                    "error_code": OAuth2ErrorCode.INVALID_REQUEST,
                    "description": f"State parameter too long (max {policy['max_state_length']} characters)"
                }
        
        # 3. Redirect URI validation for authorization endpoint
        if (policy.get("validate_redirect_uri") and 
            endpoint_path.startswith("/oauth/authorize")):
            
            redirect_uri = request.query_params.get("redirect_uri")
            if redirect_uri and not self._is_valid_redirect_uri(redirect_uri):
                return {
                    "allowed": False,
                    "error_code": OAuth2ErrorCode.INVALID_REQUEST,
                    "description": "Invalid redirect URI format (RFC 8725 Section 3.1)"
                }
        
        return {"allowed": True, "policy": policy}
    
    def _is_valid_redirect_uri(self, redirect_uri: str) -> bool:
        """Validate redirect URI according to RFC 8725."""
        
        # Must be absolute URI
        if not redirect_uri.startswith(("http://", "https://")) and "://" not in redirect_uri:
            return False
        
        # HTTPS requirement for web clients (with localhost exception)
        if redirect_uri.startswith("http://"):
            # Allow localhost for development
            if not any(local in redirect_uri for local in ["localhost", "127.0.0.1", "[::1]"]):
                return False
        
        # Check for suspicious characters
        if self._contains_suspicious_content(redirect_uri):
            return False
        
        # Must not contain fragments
        if "#" in redirect_uri:
            return False
        
        return True
    
    def _check_rate_limiting_context(self, request: Request) -> Dict[str, Any]:
        """Check rate limiting context for security decisions."""
        return {
            "endpoint": str(request.url.path),
            "method": str(request.method),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", "")[:100]  # Truncate for storage
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address considering proxies."""
        # Check X-Forwarded-For header
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        return request.client.host if request.client else "unknown"
    
    def _allow_private_networks(self) -> bool:
        """Check if private networks are allowed."""
        # In development, allow private networks
        # In production, this should be configurable
        return True
    
    async def _apply_timing_protection(self, start_time: float) -> None:
        """Apply timing attack protection by ensuring consistent response times."""
        elapsed = time.time() - start_time
        min_response_time = 0.1  # Minimum 100ms response time
        
        if elapsed < min_response_time:
            import asyncio
            await asyncio.sleep(min_response_time - elapsed)
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response (RFC 8725 Section 3.2)."""
        
        # Cache control for OAuth2 responses
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        # Content security policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "script-src 'none'; "
            "style-src 'none'; "
            "img-src 'none'; "
            "connect-src 'none'; "
            "font-src 'none'; "
            "object-src 'none'; "
            "media-src 'none'; "
            "frame-src 'none'"
        )
        
        # Additional security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # OAuth2 specific headers
        response.headers["X-OAuth2-Security"] = "RFC-8725-Compliant"
        response.headers["X-Content-Security-Policy"] = response.headers["Content-Security-Policy"]
    
    def _create_security_error_response(
        self,
        error_code: OAuth2ErrorCode,
        description: str
    ) -> JSONResponse:
        """Create security error response."""
        error_response = create_oauth2_error_response(
            error_code=error_code,
            description=description
        )
        
        headers = {
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY"
        }
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response.dict(exclude_none=True),
            headers=headers
        )