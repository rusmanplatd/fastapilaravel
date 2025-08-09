from __future__ import annotations

import logging
import time
from typing import Optional, Any, Dict, List, Callable
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response as StarletteResponse

from app.Utils import JWTUtils
from app.Models.User import User


class AuthMiddleware(BaseHTTPMiddleware):
    """Enhanced authentication middleware with comprehensive logging and monitoring."""
    
    def __init__(self, app: Any, exclude_paths: Optional[List[str]] = None) -> None:
        super().__init__(app)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.security = HTTPBearer(auto_error=False)
        self.exclude_paths = exclude_paths or [
            "/docs", "/redoc", "/openapi.json", 
            "/health", "/metrics", "/favicon.ico"
        ]
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> StarletteResponse:
        """Enhanced middleware dispatch with performance tracking and security logging."""
        start_time = time.time()
        
        # Skip authentication for excluded paths
        if self._should_skip_auth(request):
            response: StarletteResponse = await call_next(request)
            self._log_request(request, response, time.time() - start_time, skipped=True)
            return response
        
        try:
            # Extract and validate token
            user = await self._authenticate_request(request)
            
            # Set user in request state
            setattr(request.state, 'user', user)
            setattr(request.state, 'authenticated', user is not None)
            
            # Process request
            auth_response: StarletteResponse = await call_next(request)
            
            # Log successful request
            duration = time.time() - start_time
            self._log_request(request, auth_response, duration, user=user)
            
            # Add security headers
            self._add_security_headers(auth_response)
            
            return auth_response
            
        except HTTPException as e:
            # Log authentication failure
            duration = time.time() - start_time
            self._log_auth_failure(request, e, duration)
            
            return JSONResponse(
                status_code=getattr(e, 'status_code', 500),
                content=getattr(e, 'detail', 'Authentication failed')
            )
        except Exception as e:
            # Log unexpected error
            duration = time.time() - start_time
            self._log_unexpected_error(request, e, duration)
            
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Internal server error during authentication",
                    "error_code": "AUTH_SYSTEM_ERROR"
                }
            )
    
    def _should_skip_auth(self, request: Request) -> bool:
        """Check if authentication should be skipped for this path."""
        path = request.url.path if hasattr(request, 'url') else getattr(request.scope, 'path', '/') if hasattr(request, 'scope') else '/'
        
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        
        # Skip for OPTIONS requests (CORS preflight)
        if hasattr(request, 'method') and request.method == "OPTIONS":
            return True
            
        return False
    
    async def _authenticate_request(self, request: Request) -> Optional[User]:
        """Authenticate the request and return user if valid."""
        auth_header = getattr(request, 'headers', {}).get("authorization")
        
        if not auth_header:
            # No authentication provided - this is OK for optional auth
            return None
        
        if not auth_header.startswith("Bearer "):
            self._log_invalid_auth_format(request, auth_header)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "message": "Invalid authorization header format",
                    "error_code": "INVALID_AUTH_FORMAT"
                }
            )
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        # Verify JWT token
        token_data = JWTUtils.verify_token(token, "access")
        
        if not token_data:
            self._log_invalid_token(request, token)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "message": "Invalid or expired token",
                    "error_code": "INVALID_TOKEN"
                }
            )
        
        # Extract user information
        user_id = token_data.get("user_id")
        if not user_id:
            self._log_missing_user_id(request, token_data)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "message": "Token missing user information",
                    "error_code": "INVALID_TOKEN_DATA"
                }
            )
        
        # Load user (you would implement this based on your user model)
        try:
            user = await self._load_user(user_id)
            if not user:
                self._log_user_not_found(request, user_id)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "success": False,
                        "message": "User not found",
                        "error_code": "USER_NOT_FOUND"
                    }
                )
            
            # Check if user is active
            if not getattr(user, 'is_active', True):
                self._log_inactive_user(request, user_id)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={
                        "success": False,
                        "message": "User account is inactive",
                        "error_code": "USER_INACTIVE"
                    }
                )
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            self._log_user_load_error(request, user_id, e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "success": False,
                    "message": "Error loading user information",
                    "error_code": "USER_LOAD_ERROR"
                }
            )
    
    async def _load_user(self, user_id: int) -> Optional[User]:
        """Load user from database - implement based on your user model."""
        # Placeholder implementation - you would replace this with actual user loading
        # from sqlalchemy.orm import Session
        # from app.database import get_db
        # 
        # db = next(get_db())
        # user = db.query(User).filter(User.id == user_id).first()
        # return user
        return None
    
    def _add_security_headers(self, response: StarletteResponse) -> None:
        """Add security headers to response."""
        if hasattr(response, 'headers'):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    def _log_request(self, request: Request, response: StarletteResponse, duration: float, 
                    user: Optional[User] = None, skipped: bool = False) -> None:
        """Log successful request with performance metrics."""
        log_data = {
            "method": getattr(request, 'method', 'UNKNOWN'),
            "path": str(getattr(request, 'url', type('MockURL', (), {'path': '/'})()).path),
            "status_code": getattr(response, 'status_code', 0),
            "duration_ms": round(duration * 1000, 2),
            "client_ip": self._get_client_ip(request),
            "user_agent": getattr(request, 'headers', {}).get("user-agent", "unknown")
        }
        
        if user:
            log_data["user_id"] = getattr(user, 'id', None)
            log_data["user_email"] = getattr(user, 'email', None)
        
        if skipped:
            log_data["auth_skipped"] = True
        
        self.logger.info("Request processed", extra=log_data)
    
    def _log_auth_failure(self, request: Request, exception: HTTPException, duration: float) -> None:
        """Log authentication failure with security context."""
        self.logger.warning("Authentication failed", extra={
            "method": getattr(request, 'method', 'UNKNOWN'),
            "path": str(getattr(request, 'url', type('MockURL', (), {'path': '/'})()).path),
            "status_code": getattr(exception, 'status_code', 0),
            "error_detail": getattr(exception, 'detail', 'Unknown error'),
            "duration_ms": round(duration * 1000, 2),
            "client_ip": self._get_client_ip(request),
            "user_agent": getattr(request, 'headers', {}).get("user-agent", "unknown")
        })
    
    def _log_unexpected_error(self, request: Request, exception: Exception, duration: float) -> None:
        """Log unexpected errors during authentication."""
        self.logger.error("Unexpected authentication error", extra={
            "method": getattr(request, 'method', 'UNKNOWN'),
            "path": str(getattr(request, 'url', type('MockURL', (), {'path': '/'})()).path),
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "duration_ms": round(duration * 1000, 2),
            "client_ip": self._get_client_ip(request),
        }, exc_info=True)
    
    def _log_invalid_auth_format(self, request: Request, auth_header: str) -> None:
        """Log invalid authorization header format."""
        self.logger.warning("Invalid authorization header format", extra={
            "method": getattr(request, 'method', 'UNKNOWN'),
            "path": str(getattr(request, 'url', type('MockURL', (), {'path': '/'})()).path),
            "auth_header_prefix": auth_header[:20] if auth_header else "None",
            "client_ip": self._get_client_ip(request)
        })
    
    def _log_invalid_token(self, request: Request, token: str) -> None:
        """Log invalid token attempt."""
        self.logger.warning("Invalid or expired token", extra={
            "method": getattr(request, 'method', 'UNKNOWN'),
            "path": str(getattr(request, 'url', type('MockURL', (), {'path': '/'})()).path),
            "token_prefix": token[:10] if token else "None",
            "client_ip": self._get_client_ip(request)
        })
    
    def _log_missing_user_id(self, request: Request, token_data: Dict[str, Any]) -> None:
        """Log token missing user ID."""
        self.logger.warning("Token missing user ID", extra={
            "method": getattr(request, 'method', 'UNKNOWN'),
            "path": str(getattr(request, 'url', type('MockURL', (), {'path': '/'})()).path),
            "token_claims": list(token_data.keys()) if token_data else [],
            "client_ip": self._get_client_ip(request)
        })
    
    def _log_user_not_found(self, request: Request, user_id: int) -> None:
        """Log user not found during authentication."""
        self.logger.warning("User not found during authentication", extra={
            "method": getattr(request, 'method', 'UNKNOWN'),
            "path": str(getattr(request, 'url', type('MockURL', (), {'path': '/'})()).path),
            "user_id": user_id,
            "client_ip": self._get_client_ip(request)
        })
    
    def _log_inactive_user(self, request: Request, user_id: int) -> None:
        """Log inactive user authentication attempt."""
        self.logger.warning("Inactive user authentication attempt", extra={
            "method": getattr(request, 'method', 'UNKNOWN'),
            "path": str(getattr(request, 'url', type('MockURL', (), {'path': '/'})()).path),
            "user_id": user_id,
            "client_ip": self._get_client_ip(request)
        })
    
    def _log_user_load_error(self, request: Request, user_id: int, exception: Exception) -> None:
        """Log error loading user during authentication."""
        self.logger.error("Error loading user during authentication", extra={
            "method": getattr(request, 'method', 'UNKNOWN'),
            "path": str(getattr(request, 'url', type('MockURL', (), {'path': '/'})()).path),
            "user_id": user_id,
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "client_ip": self._get_client_ip(request)
        }, exc_info=True)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proxy support."""
        # Check for forwarded IP (from proxy/load balancer)
        forwarded_for = getattr(request, 'headers', {}).get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return str(forwarded_for.split(",")[0].strip())
        
        # Check for real IP (from proxy)
        real_ip = getattr(request, 'headers', {}).get("x-real-ip")
        if real_ip:
            return str(real_ip.strip())
        
        # Fallback to client host
        client = getattr(request, 'client', None)
        if client and hasattr(client, 'host'):
            return str(client.host)
        return "unknown"


# Enhanced middleware functions for dependency injection
class RequireAuth:
    """Dependency to require authentication."""
    
    def __init__(self, permissions: Optional[List[str]] = None):
        self.permissions = permissions or []
    
    async def __call__(self, request: Request) -> User:
        user: Optional[User] = getattr(request.state, 'user', None)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "success": False,
                    "message": "Authentication required",
                    "error_code": "AUTHENTICATION_REQUIRED"
                }
            )
        
        # Check permissions if specified
        if self.permissions:
            missing_permissions = []
            for permission in self.permissions:
                if not user.can(permission):
                    missing_permissions.append(permission)
            
            if missing_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "success": False,
                        "message": f"Missing required permissions: {', '.join(missing_permissions)}",
                        "error_code": "INSUFFICIENT_PERMISSIONS",
                        "context": {"missing_permissions": missing_permissions}
                    }
                )
        
        # At this point, user is guaranteed to be a User instance due to the check above
        assert user is not None
        return user


class OptionalAuth:
    """Dependency for optional authentication."""
    
    async def __call__(self, request: Request) -> Optional[User]:
        return getattr(request.state, 'user', None)


# Convenience instances
require_auth = RequireAuth()
optional_auth = OptionalAuth()


def require_permissions(*permissions: str) -> RequireAuth:
    """Create a dependency that requires specific permissions."""
    return RequireAuth(permissions=list(permissions))


# Legacy function for backwards compatibility
async def verify_token(credentials: HTTPAuthorizationCredentials) -> str:
    """Legacy verify_token function for backwards compatibility."""
    token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token_data = JWTUtils.verify_token(token, "access")
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = token_data.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user information"
        )
    
    return str(user_id)