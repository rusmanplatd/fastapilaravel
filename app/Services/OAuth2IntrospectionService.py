"""OAuth2 Token Introspection and Revocation Service - Laravel Passport Style

This service handles OAuth2 token introspection (RFC 7662) and revocation (RFC 7009)
functionality similar to Laravel Passport.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from database.migrations.create_oauth_clients_table import OAuthClient
from database.migrations.create_oauth_access_tokens_table import OAuthAccessToken
from database.migrations.create_oauth_refresh_tokens_table import OAuthRefreshToken
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService


class OAuth2IntrospectionResponse:
    """OAuth2 token introspection response structure."""
    
    def __init__(
        self,
        active: bool,
        scope: Optional[str] = None,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        token_type: Optional[str] = None,
        exp: Optional[int] = None,
        iat: Optional[int] = None,
        sub: Optional[str] = None,
        aud: Optional[str] = None,
        iss: Optional[str] = None,
        jti: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        self.active = active
        self.scope = scope
        self.client_id = client_id
        self.username = username
        self.token_type = token_type
        self.exp = exp
        self.iat = iat
        self.sub = sub
        self.aud = aud
        self.iss = iss
        self.jti = jti
        self.additional_claims = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        data = {"active": self.active}
        
        if not self.active:
            return data
        
        # Add optional fields only if they exist
        optional_fields = [
            "scope", "client_id", "username", "token_type",
            "exp", "iat", "sub", "aud", "iss", "jti"
        ]
        
        for field in optional_fields:
            value = getattr(self, field)
            if value is not None:
                data[field] = value
        
        # Add any additional claims
        data.update(self.additional_claims)
        
        return data


class OAuth2RevocationResponse:
    """OAuth2 token revocation response structure."""
    
    def __init__(self, success: bool, message: str = "") -> None:
        self.success = success
        self.message = message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "success": self.success,
            "message": self.message
        }


class OAuth2IntrospectionService:
    """Service for OAuth2 token introspection and revocation."""
    
    def __init__(self) -> None:
        self.auth_server = OAuth2AuthServerService()
    
    def introspect_token(
        self,
        db: Session,
        token: str,
        token_type_hint: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> OAuth2IntrospectionResponse:
        """
        Introspect OAuth2 token according to RFC 7662.
        
        Args:
            db: Database session
            token: Token to introspect
            token_type_hint: Optional hint about token type (access_token, refresh_token)
            client_id: Client ID for authentication (optional)
            client_secret: Client secret for authentication (optional)
        
        Returns:
            OAuth2IntrospectionResponse with token information
        
        Raises:
            HTTPException: If client authentication fails
        """
        # If client credentials provided, validate them
        if client_id:
            client = self.auth_server.validate_client_credentials(db, client_id, client_secret)
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid client credentials"
                )
        
        # Try to introspect as access token first (most common)
        if token_type_hint != "refresh_token":
            access_token_info = self._introspect_access_token(db, token)
            if access_token_info.active:
                return access_token_info
        
        # Try to introspect as refresh token
        if token_type_hint != "access_token":
            refresh_token_info = self._introspect_refresh_token(db, token)
            if refresh_token_info.active:
                return refresh_token_info
        
        # Token is not active or not found
        return OAuth2IntrospectionResponse(active=False)
    
    def _introspect_access_token(self, db: Session, token: str) -> OAuth2IntrospectionResponse:
        """Introspect access token."""
        try:
            # Validate JWT and get access token record
            access_token = self.auth_server.validate_access_token(db, token)
            
            if not access_token or not access_token.is_valid():
                return OAuth2IntrospectionResponse(active=False)
            
            # Build introspection response
            return OAuth2IntrospectionResponse(
                active=True,
                scope=" ".join(access_token.get_scopes()),
                client_id=access_token.client.client_id,
                username=access_token.user.email if access_token.user else None,
                token_type="Bearer",
                exp=int(access_token.expires_at.timestamp()) if access_token.expires_at else None,
                iat=int(access_token.created_at.timestamp()),
                sub=str(access_token.user_id) if access_token.user_id else None,
                aud="api",
                iss="fastapi-laravel-oauth",
                jti=access_token.token_id,
                token_name=access_token.name
            )
            
        except Exception:
            return OAuth2IntrospectionResponse(active=False)
    
    def _introspect_refresh_token(self, db: Session, token: str) -> OAuth2IntrospectionResponse:
        """Introspect refresh token."""
        try:
            refresh_token = self.auth_server.find_refresh_token_by_id(db, token)
            
            if not refresh_token or not refresh_token.is_valid():
                return OAuth2IntrospectionResponse(active=False)
            
            # Get associated access token for additional info
            access_token = self.auth_server.find_access_token_by_id(
                db, refresh_token.access_token_id
            )
            
            return OAuth2IntrospectionResponse(
                active=True,
                client_id=refresh_token.client.client_id,
                token_type="refresh_token",
                exp=int(refresh_token.expires_at.timestamp()) if refresh_token.expires_at else None,
                iat=int(refresh_token.created_at.timestamp()),
                sub=str(access_token.user_id) if access_token and access_token.user_id else None,
                aud="api",
                iss="fastapi-laravel-oauth",
                jti=refresh_token.token_id
            )
            
        except Exception:
            return OAuth2IntrospectionResponse(active=False)
    
    def revoke_token(
        self,
        db: Session,
        token: str,
        token_type_hint: Optional[str] = None,
        client_id: str,
        client_secret: Optional[str] = None
    ) -> OAuth2RevocationResponse:
        """
        Revoke OAuth2 token according to RFC 7009.
        
        Args:
            db: Database session
            token: Token to revoke
            token_type_hint: Optional hint about token type
            client_id: Client ID for authentication
            client_secret: Client secret for authentication
        
        Returns:
            OAuth2RevocationResponse indicating success or failure
        
        Raises:
            HTTPException: If client authentication fails
        """
        # Validate client credentials
        client = self.auth_server.validate_client_credentials(db, client_id, client_secret)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid client credentials"
            )
        
        revoked = False
        
        # Try to revoke as access token first
        if token_type_hint != "refresh_token":
            if self._revoke_access_token(db, token, client):
                revoked = True
        
        # Try to revoke as refresh token
        if token_type_hint != "access_token" and not revoked:
            if self._revoke_refresh_token(db, token, client):
                revoked = True
        
        # According to RFC 7009, always return success (even for invalid tokens)
        # This prevents token scanning attacks
        return OAuth2RevocationResponse(
            success=True,
            message="Token revoked successfully" if revoked else "Token processed"
        )
    
    def _revoke_access_token(self, db: Session, token: str, client: OAuthClient) -> bool:
        """Revoke access token."""
        try:
            # Validate JWT and get token record
            access_token = self.auth_server.validate_access_token(db, token)
            
            if not access_token:
                # Try to find by token ID directly
                payload = self.auth_server.decode_jwt_token(token)
                if payload and payload.get("token_id"):
                    access_token = self.auth_server.find_access_token_by_id(db, payload["token_id"])
            
            if not access_token:
                return False
            
            # Verify token belongs to this client
            if access_token.client_id != client.id:
                return False
            
            # Revoke access token
            access_token.revoke()
            
            # Also revoke associated refresh tokens
            refresh_tokens = db.query(OAuthRefreshToken).filter(
                OAuthRefreshToken.access_token_id == access_token.token_id,
                OAuthRefreshToken.revoked == False
            ).all()
            
            for refresh_token in refresh_tokens:
                refresh_token.revoke()
            
            db.commit()
            return True
            
        except Exception:
            return False
    
    def _revoke_refresh_token(self, db: Session, token: str, client: OAuthClient) -> bool:
        """Revoke refresh token."""
        try:
            refresh_token = self.auth_server.find_refresh_token_by_id(db, token)
            
            if not refresh_token:
                return False
            
            # Verify token belongs to this client
            if refresh_token.client_id != client.id:
                return False
            
            # Revoke refresh token
            refresh_token.revoke()
            
            # Also revoke associated access token
            access_token = self.auth_server.find_access_token_by_id(
                db, refresh_token.access_token_id
            )
            if access_token and not access_token.is_revoked():
                access_token.revoke()
            
            db.commit()
            return True
            
        except Exception:
            return False
    
    def revoke_all_tokens_for_user(
        self,
        db: Session,
        user_id: int,
        client_id: Optional[int] = None
    ) -> int:
        """
        Revoke all tokens for a user (optionally filtered by client).
        
        Args:
            db: Database session
            user_id: User ID
            client_id: Optional client ID filter
        
        Returns:
            Number of tokens revoked
        """
        query = db.query(OAuthAccessToken).filter(
            OAuthAccessToken.user_id == user_id,
            OAuthAccessToken.revoked == False
        )
        
        if client_id:
            query = query.filter(OAuthAccessToken.client_id == client_id)
        
        access_tokens = query.all()
        revoked_count = 0
        
        for access_token in access_tokens:
            access_token.revoke()
            revoked_count += 1
            
            # Also revoke associated refresh tokens
            refresh_tokens = db.query(OAuthRefreshToken).filter(
                OAuthRefreshToken.access_token_id == access_token.token_id,
                OAuthRefreshToken.revoked == False
            ).all()
            
            for refresh_token in refresh_tokens:
                refresh_token.revoke()
                revoked_count += 1
        
        db.commit()
        return revoked_count
    
    def revoke_all_tokens_for_client(self, db: Session, client_id: int) -> int:
        """
        Revoke all tokens for a client.
        
        Args:
            db: Database session
            client_id: Client ID
        
        Returns:
            Number of tokens revoked
        """
        # Revoke access tokens
        access_tokens = db.query(OAuthAccessToken).filter(
            OAuthAccessToken.client_id == client_id,
            OAuthAccessToken.revoked == False
        ).all()
        
        # Revoke refresh tokens
        refresh_tokens = db.query(OAuthRefreshToken).filter(
            OAuthRefreshToken.client_id == client_id,
            OAuthRefreshToken.revoked == False
        ).all()
        
        revoked_count = 0
        
        for token in access_tokens + refresh_tokens:
            token.revoke()
            revoked_count += 1
        
        db.commit()
        return revoked_count
    
    def get_active_tokens_for_user(
        self,
        db: Session,
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get active tokens for a user.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of tokens to return
        
        Returns:
            List of active token information
        """
        access_tokens = db.query(OAuthAccessToken).filter(
            OAuthAccessToken.user_id == user_id,
            OAuthAccessToken.revoked == False
        ).order_by(OAuthAccessToken.created_at.desc()).limit(limit).all()
        
        token_list = []
        for token in access_tokens:
            token_info = {
                "id": token.id,
                "name": token.name,
                "scopes": token.get_scopes(),
                "client": {
                    "id": token.client.id,
                    "name": token.client.name,
                    "client_id": token.client.client_id
                },
                "created_at": token.created_at,
                "expires_at": token.expires_at,
                "is_expired": token.is_expired()
            }
            token_list.append(token_info)
        
        return token_list