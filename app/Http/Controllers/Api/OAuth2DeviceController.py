"""OAuth2 Device Authorization Controller - RFC 8628

This controller implements the Device Authorization Grant flow as defined in RFC 8628,
allowing OAuth2 authorization on devices with limited input capabilities.
"""

from __future__ import annotations

import secrets
import string
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends, Form, Request
from sqlalchemy.orm import Session

from app.Http.Controllers.BaseController import BaseController
from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2DeviceCode import OAuth2DeviceCode
from app.Models.User import User
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from config.database import get_db_session
from config.oauth2 import get_oauth2_settings


class OAuth2DeviceController(BaseController):
    """Controller for OAuth2 Device Authorization Grant (RFC 8628)."""
    
    def __init__(self) -> None:
        super().__init__()
        self.oauth2_settings = get_oauth2_settings()
        self.auth_server = OAuth2AuthServerService()
        
        # RFC 8628 recommended values
        self.device_code_lifetime = 1800  # 30 minutes
        self.user_code_lifetime = 1800    # 30 minutes
        self.verification_uri = "http://localhost:8000/device"
        self.verification_uri_complete_template = "http://localhost:8000/device?user_code={user_code}"
        self.interval = 5  # Minimum polling interval in seconds
    
    async def device_authorization(
        self,
        request: Request,
        db: Session = Depends(get_db_session),
        client_id: str = Form(..., description="OAuth2 client identifier"),
        scope: Optional[str] = Form(None, description="Requested scope")
    ) -> Dict[str, Any]:
        """
        Device Authorization Endpoint (RFC 8628 Section 3.1).
        
        Issues a device verification code and user code for the device
        authorization grant flow.
        
        Args:
            request: FastAPI request
            db: Database session
            client_id: OAuth2 client identifier
            scope: Requested scope
        
        Returns:
            Device authorization response
        
        Raises:
            HTTPException: If client is invalid or request is malformed
        """
        try:
            # Validate client
            client = db.query(OAuth2Client).filter(
                OAuth2Client.client_id == client_id,
                OAuth2Client.is_active == True
            ).first()
            
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="invalid_client"
                )
            
            # Check if client supports device authorization grant
            if not self._client_supports_device_grant(client):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="unauthorized_client"
                )
            
            # Validate and filter scopes
            requested_scopes = scope.split() if scope else ["read"]
            valid_scopes = self._validate_scopes(db, requested_scopes, client)
            
            # Generate device code and user code
            device_code = self._generate_device_code()
            user_code = self._generate_user_code()
            
            # Calculate expiration times
            expires_in = self.device_code_lifetime
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Store device authorization
            device_auth = OAuth2DeviceCode(
                device_code=device_code,
                user_code=user_code,
                client_id=client.id,
                scope=" ".join(valid_scopes),
                expires_at=expires_at,
                interval=self.interval,
                verification_uri=self.verification_uri,
                verification_uri_complete=self.verification_uri_complete_template.format(
                    user_code=user_code
                )
            )
            
            db.add(device_auth)
            db.commit()
            db.refresh(device_auth)
            
            # Return device authorization response
            response = {
                "device_code": device_code,
                "user_code": user_code,
                "verification_uri": self.verification_uri,
                "verification_uri_complete": device_auth.verification_uri_complete,
                "expires_in": expires_in,
                "interval": self.interval
            }
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Device authorization failed: {str(e)}"
            )
    
    async def device_token(
        self,
        db: Session = Depends(get_db_session),
        grant_type: str = Form(..., description="Must be 'urn:ietf:params:oauth:grant-type:device_code'"),
        device_code: str = Form(..., description="Device verification code"),
        client_id: str = Form(..., description="OAuth2 client identifier")
    ) -> Dict[str, Any]:
        """
        Device Token Endpoint (RFC 8628 Section 3.4).
        
        Exchanges a device code for access tokens after user authorization.
        
        Args:
            db: Database session
            grant_type: Must be the device code grant type
            device_code: Device verification code
            client_id: OAuth2 client identifier
        
        Returns:
            Token response or error
        
        Raises:
            HTTPException: For various error conditions
        """
        try:
            # Validate grant type
            if grant_type != "urn:ietf:params:oauth:grant-type:device_code":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="unsupported_grant_type"
                )
            
            # Find device authorization
            device_auth = db.query(OAuth2DeviceCode).filter(
                OAuth2DeviceCode.device_code == device_code
            ).first()
            
            if not device_auth:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="invalid_grant"
                )
            
            # Check if expired
            if device_auth.is_expired():
                db.delete(device_auth)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="expired_token"
                )
            
            # Check client match
            if device_auth.client.client_id != client_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="invalid_client"
                )
            
            # Check authorization status
            if not device_auth.user_id:
                # User hasn't authorized yet
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="authorization_pending"
                )
            
            if device_auth.denied:
                # User denied authorization
                db.delete(device_auth)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="access_denied"
                )
            
            # Check polling interval
            if device_auth.last_polled_at:
                time_since_last_poll = (datetime.utcnow() - device_auth.last_polled_at).total_seconds()
                if time_since_last_poll < device_auth.interval:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="slow_down"
                    )
            
            # Update last polled time
            device_auth.last_polled_at = datetime.utcnow()
            db.commit()
            
            # Generate tokens
            user = db.get(User, device_auth.user_id)
            scopes = device_auth.scope.split() if device_auth.scope else []
            
            access_token = self.auth_server.create_access_token(
                db=db,
                client=device_auth.client,
                user=user,
                scopes=scopes,
                name="Device Authorization Grant"
            )
            
            # Create refresh token if supported
            refresh_token = None
            if "offline_access" in scopes:
                refresh_token = self.auth_server.create_refresh_token(db, access_token, device_auth.client)
            
            # Delete device authorization (one-time use)
            db.delete(device_auth)
            db.commit()
            
            # Create token response
            response = {
                "access_token": access_token.token,
                "token_type": "Bearer",
                "expires_in": self.oauth2_settings.oauth2_access_token_expire_minutes * 60,
                "scope": " ".join(scopes)
            }
            
            if refresh_token:
                response["refresh_token"] = refresh_token.token_id
            
            # Add ID token for OpenID Connect
            if "openid" in scopes and access_token.id_token:
                response["id_token"] = access_token.id_token
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Device token request failed: {str(e)}"
            )
    
    async def device_verification(
        self,
        request: Request,
        db: Session = Depends(get_db_session),
        user_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Device Verification Page.
        
        Shows the user code verification page where users can enter
        their user code and authorize the device.
        
        Args:
            request: FastAPI request
            db: Database session
            user_code: Pre-filled user code
        
        Returns:
            Verification page data
        """
        try:
            device_auth = None
            
            if user_code:
                # Validate user code format
                if not self._validate_user_code_format(user_code):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid user code format"
                    )
                
                # Find device authorization by user code
                device_auth = db.query(OAuth2DeviceCode).filter(
                    OAuth2DeviceCode.user_code == user_code.upper(),
                    OAuth2DeviceCode.user_id.is_(None),  # Not yet authorized
                    OAuth2DeviceCode.denied == False
                ).first()
                
                if device_auth and device_auth.is_expired():
                    db.delete(device_auth)
                    db.commit()
                    device_auth = None
            
            verification_data = {
                "user_code": user_code,
                "device_auth": {
                    "client_name": device_auth.client.name,
                    "scope": device_auth.scope.split() if device_auth.scope else [],
                    "expires_at": device_auth.expires_at.isoformat()
                } if device_auth else None,
                "verification_uri": self.verification_uri,
                "requires_authentication": True
            }
            
            return self.success_response(
                data=verification_data,
                message="Device verification page data"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Device verification failed: {str(e)}"
            )
    
    async def authorize_device(
        self,
        db: Session = Depends(get_db_session),
        user_code: str = Form(..., description="User code"),
        authorized: bool = Form(..., description="User authorization decision"),
        user_id: str = Form(..., description="Authenticated user ID")
    ) -> Dict[str, Any]:
        """
        Authorize Device.
        
        Processes user authorization decision for device authorization.
        
        Args:
            db: Database session
            user_code: User code
            authorized: Whether user authorized the device
            user_id: Authenticated user ID
        
        Returns:
            Authorization result
        """
        try:
            # Find device authorization
            device_auth = db.query(OAuth2DeviceCode).filter(
                OAuth2DeviceCode.user_code == user_code.upper(),
                OAuth2DeviceCode.user_id.is_(None)  # Not yet processed
            ).first()
            
            if not device_auth or device_auth.is_expired():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired user code"
                )
            
            # Update device authorization
            if authorized:
                device_auth.user_id = user_id
                device_auth.authorized_at = datetime.utcnow()
                message = "Device authorized successfully"
            else:
                device_auth.denied = True
                device_auth.denied_at = datetime.utcnow()
                message = "Device authorization denied"
            
            db.commit()
            
            return self.success_response(
                data={"authorized": authorized},
                message=message
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Device authorization failed: {str(e)}"
            )
    
    def _generate_device_code(self) -> str:
        """Generate a cryptographically secure device code."""
        # RFC 8628: device_code should be opaque and unguessable
        return secrets.token_urlsafe(32)
    
    def _generate_user_code(self) -> str:
        """Generate a user-friendly user code."""
        # RFC 8628: user_code should be short and user-friendly
        # Use uppercase letters and numbers, avoid confusing characters
        charset = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # No 0, O, I, 1
        return ''.join(secrets.choice(charset) for _ in range(8))
    
    def _validate_user_code_format(self, user_code: str) -> bool:
        """Validate user code format."""
        if not user_code or len(user_code) != 8:
            return False
        
        # Check if contains only valid characters
        valid_chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        return all(c in valid_chars for c in user_code.upper())
    
    def _client_supports_device_grant(self, client: OAuth2Client) -> bool:
        """Check if client supports device authorization grant."""
        # Check if device grant is in allowed grant types
        allowed_grants = getattr(client, 'grant_types', '').split()
        return "urn:ietf:params:oauth:grant-type:device_code" in allowed_grants
    
    def _validate_scopes(
        self,
        db: Session,
        requested_scopes: list[str],
        client: OAuth2Client
    ) -> list[str]:
        """Validate and filter requested scopes."""
        # Get client's allowed scopes
        client_scopes = client.get_allowed_scopes()
        
        # Filter to only allowed scopes
        valid_scopes = [
            scope for scope in requested_scopes 
            if scope in client_scopes and scope in self.oauth2_settings.oauth2_supported_scopes
        ]
        
        return valid_scopes or ["read"]  # Default to read scope