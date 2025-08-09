"""OAuth2 Userinfo Controller - Google IDP Style

This controller handles the OpenID Connect userinfo endpoint similar to Google's
Identity Provider, providing user profile information for authenticated users.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Services.OAuth2IntrospectionService import OAuth2IntrospectionService
from app.Models.User import User
from config.database import get_db_session

# OAuth2 Bearer token scheme
oauth2_scheme = HTTPBearer()


class OAuth2UserinfoController(BaseController):
    """Controller for OAuth2/OpenID Connect userinfo operations."""
    
    def __init__(self) -> None:
        super().__init__()
        self.introspection_service = OAuth2IntrospectionService()
    
    async def userinfo(
        self,
        request: Request,
        db: Session,
        credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
    ) -> Dict[str, Any]:
        """
        OpenID Connect UserInfo endpoint (RFC 6749).
        
        Returns claims about the authenticated user. The userinfo endpoint
        is an OAuth 2.0 protected resource that returns authorized information
        about the user.
        
        Args:
            request: FastAPI request object
            db: Database session
            credentials: Bearer token credentials
        
        Returns:
            User information claims
        
        Raises:
            HTTPException: If token is invalid or user not found
        """
        try:
            # Extract token from Authorization header
            access_token = credentials.credentials
            
            # Introspect the token to validate it and get token info
            introspection_response = self.introspection_service.introspect_token(
                db=db,
                token=access_token,
                token_type_hint="access_token"
            )
            
            # Check if token is active
            if not introspection_response.active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Get user information
            user_id = introspection_response.sub
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token does not contain user information",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # Fetch user from database
            user = db.get(User, user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Get token scopes to determine what information to return
            token_scopes = introspection_response.scope.split() if introspection_response.scope else []
            
            # Build userinfo response based on scopes (Google-style)
            userinfo = {
                "sub": str(user.id),  # Subject identifier
            }
            
            # Profile scope claims
            if "profile" in token_scopes:
                userinfo.update({
                    "name": self._get_user_full_name(user),
                    "given_name": getattr(user, 'first_name', None),
                    "family_name": getattr(user, 'last_name', None),
                    "picture": getattr(user, 'avatar_url', None),
                    "locale": getattr(user, 'locale', 'en'),
                })
                
                # Add username if available
                if hasattr(user, 'username') and user.username:
                    userinfo["preferred_username"] = user.username
            
            # Email scope claims
            if "email" in token_scopes:
                userinfo.update({
                    "email": user.email,
                    "email_verified": getattr(user, 'email_verified_at', None) is not None
                })
            
            # Phone scope claims (if supported)
            if "phone" in token_scopes:
                phone_number = getattr(user, 'phone_number', None)
                if phone_number:
                    userinfo.update({
                        "phone_number": phone_number,
                        "phone_number_verified": getattr(user, 'phone_verified_at', None) is not None
                    })
            
            # Address scope claims (if supported)
            if "address" in token_scopes:
                address = self._get_user_address(user)
                if address:
                    userinfo["address"] = address
            
            # Remove None values to match Google's behavior
            userinfo = {k: v for k, v in userinfo.items() if v is not None}
            
            return userinfo
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve user information: {str(e)}"
            )
    
    def _get_user_full_name(self, user: User) -> Optional[str]:
        """
        Get user's full name.
        
        Args:
            user: User model instance
        
        Returns:
            Full name or None
        """
        first_name = getattr(user, 'first_name', None)
        last_name = getattr(user, 'last_name', None)
        
        if first_name and last_name:
            return f"{first_name} {last_name}"
        elif first_name:
            return first_name
        elif last_name:
            return last_name
        elif hasattr(user, 'username') and user.username:
            return user.username
        else:
            return None
    
    def _get_user_address(self, user: User) -> Optional[Dict[str, str]]:
        """
        Get user's address information.
        
        Args:
            user: User model instance
        
        Returns:
            Address dictionary or None
        """
        address_fields = {
            'street_address': getattr(user, 'address_line_1', None),
            'locality': getattr(user, 'city', None),
            'region': getattr(user, 'state', None),
            'postal_code': getattr(user, 'postal_code', None),
            'country': getattr(user, 'country', None)
        }
        
        # Filter out None values
        address = {k: v for k, v in address_fields.items() if v is not None}
        
        # Return None if no address information is available
        return address if address else None