from __future__ import annotations

from typing import Callable, Optional, Dict, Any, Awaitable
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.Models import User, MFASession, MFASessionStatus
from app.Services import MFAService
from config.database import get_db


class MFAMiddleware:
    """Middleware to enforce MFA verification for protected endpoints"""
    
    def __init__(self) -> None:
        pass
    
    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]], user: Optional[User] = None) -> Response:
        """
        Middleware to check MFA requirements
        
        This middleware should be applied after authentication middleware
        so that we have access to the current user
        """
        # Skip MFA check for certain paths
        skip_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/register", 
            "/api/v1/mfa/",
            "/docs",
            "/openapi.json",
            "/favicon.ico"
        ]
        
        path = request.url.path
        if any(path.startswith(skip_path) for skip_path in skip_paths):
            return await call_next(request)
        
        # If no user, let auth middleware handle it
        if not user:
            return await call_next(request)
        
        # Check if user has MFA enabled and required
        if not user.has_mfa_enabled() or not user.is_mfa_required():
            return await call_next(request)
        
        # Check for MFA session in headers
        mfa_session_token = request.headers.get("X-MFA-Session-Token")
        
        if not mfa_session_token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "success": False,
                    "message": "MFA verification required",
                    "requires_mfa": True,
                    "available_methods": user.get_enabled_mfa_methods()
                }
            )
        
        # Verify MFA session
        db: Session = next(get_db())
        try:
            mfa_service = MFAService(db)
            mfa_session = mfa_service.get_mfa_session(mfa_session_token)
            
            if not mfa_session:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "success": False,
                        "message": "Invalid or expired MFA session",
                        "requires_mfa": True,
                        "available_methods": user.get_enabled_mfa_methods()
                    }
                )
            
            if mfa_session.user_id != user.id:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "success": False,
                        "message": "MFA session does not belong to current user",
                        "requires_mfa": True
                    }
                )
            
            if mfa_session.status != MFASessionStatus.VERIFIED:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "success": False,
                        "message": "MFA session not verified",
                        "requires_mfa": True,
                        "available_methods": user.get_enabled_mfa_methods()
                    }
                )
            
            # MFA session is valid, proceed with request
            return await call_next(request)
            
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "message": f"MFA verification error: {str(e)}"
                }
            )
        finally:
            db.close()


def require_mfa(user: User, db: Session) -> Optional[JSONResponse]:
    """
    Helper function to check MFA requirements for specific endpoints
    Returns None if MFA is satisfied, otherwise returns error response
    """
    if not user.has_mfa_enabled() or not user.is_mfa_required():
        return None
    
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "success": False,
            "message": "MFA verification required",
            "requires_mfa": True,
            "available_methods": user.get_enabled_mfa_methods()
        }
    )


def verify_mfa_session(session_token: str, user: User, db: Session) -> bool:
    """
    Helper function to verify MFA session token
    """
    try:
        mfa_service = MFAService(db)
        mfa_session = mfa_service.get_mfa_session(session_token)
        
        if not mfa_session:
            return False
            
        return (
            mfa_session.user_id == user.id and
            mfa_session.status == MFASessionStatus.VERIFIED
        )
        
    except Exception:
        return False