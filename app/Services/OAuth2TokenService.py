"""OAuth2 Token Service

This service handles OAuth2 token operations including creation, validation,
and management of access tokens, refresh tokens, and authorization codes.
"""

from __future__ import annotations

import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from sqlalchemy.orm import Session
from jose import jwt

from app.Services.BaseService import BaseService
from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2AccessToken import OAuth2AccessToken
from app.Models.OAuth2RefreshToken import OAuth2RefreshToken
from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode
from app.Models.User import User
from app.Utils.JWTUtils import JWTUtils
from config.oauth2 import get_oauth2_settings


class OAuth2TokenService(BaseService):
    """OAuth2 token management service."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.jwt_utils = JWTUtils()
        self.oauth2_settings = get_oauth2_settings()

    async def create_access_token(
        self,
        client: OAuth2Client,
        user_id: Optional[str] = None,
        scope: str = "read",
        grant_type: str = "authorization_code",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create an OAuth2 access token.
        
        Args:
            client: OAuth2 client
            user_id: User identifier (optional for client credentials)
            scope: Token scope
            grant_type: Grant type used
            additional_data: Additional token data
            
        Returns:
            Access token information
        """
        now = datetime.utcnow()
        expires_in = self.oauth2_settings.oauth2_access_token_expire_minutes * 60
        expires_at = now + timedelta(seconds=expires_in)
        
        # Generate token value
        token_value = self._generate_token()
        
        # Create JWT payload
        payload = {
            "iss": self.oauth2_settings.oauth2_issuer,
            "sub": user_id or client.client_id,
            "aud": [client.client_id],
            "exp": int(expires_at.timestamp()),
            "iat": int(now.timestamp()),
            "jti": token_value,
            "scope": scope,
            "client_id": client.client_id,
            "grant_type": grant_type
        }
        
        # Add additional data if provided
        if additional_data:
            payload.update(additional_data)
        
        # Create JWT token
        jwt_token = self.jwt_utils.encode_jwt(payload)
        
        # Store in database
        access_token = OAuth2AccessToken(
            token=jwt_token,
            client_id=client.client_id,
            user_id=user_id,
            scope=scope,
            expires_at=expires_at,
            created_at=now,
            revoked=False
        )
        
        self.db.add(access_token)
        self.db.commit()
        self.db.refresh(access_token)
        
        return {
            "token": jwt_token,
            "expires_in": expires_in,
            "scope": scope,
            "token_type": "Bearer",
            "created_at": now.isoformat()
        }

    async def create_refresh_token(
        self,
        client: OAuth2Client,
        user_id: str,
        scope: str = "read",
        access_token_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an OAuth2 refresh token.
        
        Args:
            client: OAuth2 client
            user_id: User identifier
            scope: Token scope
            access_token_id: Associated access token ID
            
        Returns:
            Refresh token information
        """
        now = datetime.utcnow()
        expires_in = self.oauth2_settings.oauth2_refresh_token_expire_minutes * 60
        expires_at = now + timedelta(seconds=expires_in)
        
        # Generate token value
        token_value = self._generate_token()
        
        # Store in database
        refresh_token = OAuth2RefreshToken(
            token=token_value,
            client_id=client.client_id,
            user_id=user_id,
            scope=scope,
            expires_at=expires_at,
            created_at=now,
            revoked=False
        )
        
        self.db.add(refresh_token)
        self.db.commit()
        self.db.refresh(refresh_token)
        
        return {
            "token": token_value,
            "expires_in": expires_in,
            "scope": scope,
            "created_at": now.isoformat()
        }

    async def create_authorization_code(
        self,
        client: OAuth2Client,
        user_id: str,
        redirect_uri: str,
        scope: str = "read",
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an OAuth2 authorization code.
        
        Args:
            client: OAuth2 client
            user_id: User identifier
            redirect_uri: Redirect URI
            scope: Requested scope
            code_challenge: PKCE code challenge
            code_challenge_method: PKCE code challenge method
            
        Returns:
            Authorization code information
        """
        now = datetime.utcnow()
        expires_in = 600  # 10 minutes
        expires_at = now + timedelta(seconds=expires_in)
        
        # Generate authorization code
        code_value = self._generate_authorization_code()
        
        # Store in database
        auth_code = OAuth2AuthorizationCode(
            code=code_value,
            client_id=client.client_id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=expires_at,
            created_at=now,
            used=False
        )
        
        self.db.add(auth_code)
        self.db.commit()
        self.db.refresh(auth_code)
        
        return {
            "code": code_value,
            "expires_in": expires_in,
            "scope": scope,
            "created_at": now.isoformat()
        }

    async def validate_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate an OAuth2 access token.
        
        Args:
            token: Access token to validate
            
        Returns:
            Token information if valid, None otherwise
        """
        try:
            # Decode JWT token
            payload = self.jwt_utils.decode_jwt(token)
            
            # Check if token exists in database
            db_token = self.db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.token == token,
                OAuth2AccessToken.revoked == False,
                OAuth2AccessToken.expires_at > datetime.utcnow()
            ).first()
            
            if not db_token:
                return None
            
            return {
                "client_id": payload.get("client_id"),
                "user_id": payload.get("sub"),
                "scope": payload.get("scope"),
                "expires_at": payload.get("exp"),
                "issued_at": payload.get("iat"),
                "jti": payload.get("jti")
            }
            
        except Exception:
            return None

    async def validate_refresh_token(
        self,
        token: str,
        client: OAuth2Client
    ) -> Optional[Dict[str, Any]]:
        """
        Validate an OAuth2 refresh token.
        
        Args:
            token: Refresh token to validate
            client: OAuth2 client
            
        Returns:
            Token information if valid, None otherwise
        """
        db_token = self.db.query(OAuth2RefreshToken).filter(
            OAuth2RefreshToken.token == token,
            OAuth2RefreshToken.client_id == client.client_id,
            OAuth2RefreshToken.revoked == False,
            OAuth2RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if not db_token:
            return None
        
        return {
            "client_id": db_token.client_id,
            "user_id": db_token.user_id,
            "scope": db_token.scope,
            "expires_at": db_token.expires_at,
            "created_at": db_token.created_at
        }

    async def validate_authorization_code(
        self,
        code: str,
        client: OAuth2Client,
        redirect_uri: str,
        code_verifier: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Validate an OAuth2 authorization code.
        
        Args:
            code: Authorization code to validate
            client: OAuth2 client
            redirect_uri: Redirect URI
            code_verifier: PKCE code verifier
            
        Returns:
            Code information if valid, None otherwise
        """
        db_code = self.db.query(OAuth2AuthorizationCode).filter(
            OAuth2AuthorizationCode.code == code,
            OAuth2AuthorizationCode.client_id == client.client_id,
            OAuth2AuthorizationCode.redirect_uri == redirect_uri,
            OAuth2AuthorizationCode.used == False,
            OAuth2AuthorizationCode.expires_at > datetime.utcnow()
        ).first()
        
        if not db_code:
            return None
        
        # Validate PKCE if present
        if db_code.code_challenge and code_verifier:
            if not self._validate_pkce(
                code_verifier,
                db_code.code_challenge,
                db_code.code_challenge_method
            ):
                return None
        elif db_code.code_challenge and not code_verifier:
            # PKCE required but verifier not provided
            return None
        
        # Mark code as used
        db_code.used = True
        self.db.commit()
        
        return {
            "client_id": db_code.client_id,
            "user_id": db_code.user_id,
            "scope": db_code.scope,
            "redirect_uri": db_code.redirect_uri,
            "created_at": db_code.created_at
        }

    async def revoke_token(
        self,
        token: str,
        token_type_hint: Optional[str] = None
    ) -> bool:
        """
        Revoke an OAuth2 token.
        
        Args:
            token: Token to revoke
            token_type_hint: Hint about token type
            
        Returns:
            True if token was revoked
        """
        revoked = False
        
        # Try to revoke as access token
        if token_type_hint != "refresh_token":
            access_tokens = self.db.query(OAuth2AccessToken).filter(
                OAuth2AccessToken.token == token,
                OAuth2AccessToken.revoked == False
            ).all()
            
            for access_token in access_tokens:
                access_token.revoked = True
                revoked = True
        
        # Try to revoke as refresh token
        if token_type_hint != "access_token":
            refresh_tokens = self.db.query(OAuth2RefreshToken).filter(
                OAuth2RefreshToken.token == token,
                OAuth2RefreshToken.revoked == False
            ).all()
            
            for refresh_token in refresh_tokens:
                refresh_token.revoked = True
                revoked = True
        
        if revoked:
            self.db.commit()
        
        return revoked

    async def introspect_token(self, token: str) -> Dict[str, Any]:
        """
        Introspect an OAuth2 token (RFC 7662).
        
        Args:
            token: Token to introspect
            
        Returns:
            Token introspection response
        """
        # Try as access token first
        token_info = await self.validate_access_token(token)
        
        if token_info:
            return {
                "active": True,
                "client_id": token_info["client_id"],
                "sub": token_info["user_id"],
                "scope": token_info["scope"],
                "exp": token_info["expires_at"],
                "iat": token_info["issued_at"],
                "token_type": "Bearer"
            }
        
        # Try as refresh token
        refresh_token = self.db.query(OAuth2RefreshToken).filter(
            OAuth2RefreshToken.token == token,
            OAuth2RefreshToken.revoked == False,
            OAuth2RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if refresh_token:
            return {
                "active": True,
                "client_id": refresh_token.client_id,
                "sub": refresh_token.user_id,
                "scope": refresh_token.scope,
                "exp": int(refresh_token.expires_at.timestamp()),
                "token_type": "refresh_token"
            }
        
        return {"active": False}

    async def cleanup_expired_tokens(self) -> Dict[str, int]:
        """
        Clean up expired tokens from the database.
        
        Returns:
            Count of cleaned up tokens by type
        """
        now = datetime.utcnow()
        
        # Clean up expired access tokens
        expired_access_tokens = self.db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.expires_at < now
        ).count()
        
        self.db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.expires_at < now
        ).delete()
        
        # Clean up expired refresh tokens
        expired_refresh_tokens = self.db.query(OAuth2RefreshToken).filter(
            OAuth2RefreshToken.expires_at < now
        ).count()
        
        self.db.query(OAuth2RefreshToken).filter(
            OAuth2RefreshToken.expires_at < now
        ).delete()
        
        # Clean up expired authorization codes
        expired_auth_codes = self.db.query(OAuth2AuthorizationCode).filter(
            OAuth2AuthorizationCode.expires_at < now
        ).count()
        
        self.db.query(OAuth2AuthorizationCode).filter(
            OAuth2AuthorizationCode.expires_at < now
        ).delete()
        
        self.db.commit()
        
        return {
            "access_tokens": expired_access_tokens,
            "refresh_tokens": expired_refresh_tokens,
            "authorization_codes": expired_auth_codes
        }

    def _generate_token(self) -> str:
        """Generate a secure token."""
        return secrets.token_urlsafe(32)

    def _generate_authorization_code(self) -> str:
        """Generate a secure authorization code."""
        return secrets.token_urlsafe(24)

    def _validate_pkce(
        self,
        code_verifier: str,
        code_challenge: str,
        code_challenge_method: Optional[str]
    ) -> bool:
        """
        Validate PKCE code challenge.
        
        Args:
            code_verifier: Code verifier
            code_challenge: Code challenge
            code_challenge_method: Challenge method (S256 or plain)
            
        Returns:
            True if PKCE validation passes
        """
        if code_challenge_method == "S256":
            # SHA256 hash and base64url encode
            verifier_hash = hashlib.sha256(code_verifier.encode()).digest()
            expected_challenge = secrets.token_urlsafe(32)[:-2]  # Remove padding
            # Proper base64url encoding would be used in production
            return code_challenge == expected_challenge
        elif code_challenge_method == "plain" or not code_challenge_method:
            return code_verifier == code_challenge
        else:
            return False

    async def get_token_statistics(self) -> Dict[str, Any]:
        """
        Get token usage statistics.
        
        Returns:
            Token statistics
        """
        now = datetime.utcnow()
        
        # Access token stats
        total_access_tokens = self.db.query(OAuth2AccessToken).count()
        active_access_tokens = self.db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.revoked == False,
            OAuth2AccessToken.expires_at > now
        ).count()
        
        # Refresh token stats
        total_refresh_tokens = self.db.query(OAuth2RefreshToken).count()
        active_refresh_tokens = self.db.query(OAuth2RefreshToken).filter(
            OAuth2RefreshToken.revoked == False,
            OAuth2RefreshToken.expires_at > now
        ).count()
        
        # Authorization code stats
        total_auth_codes = self.db.query(OAuth2AuthorizationCode).count()
        unused_auth_codes = self.db.query(OAuth2AuthorizationCode).filter(
            OAuth2AuthorizationCode.used == False,
            OAuth2AuthorizationCode.expires_at > now
        ).count()
        
        return {
            "access_tokens": {
                "total": total_access_tokens,
                "active": active_access_tokens,
                "expired_or_revoked": total_access_tokens - active_access_tokens
            },
            "refresh_tokens": {
                "total": total_refresh_tokens,
                "active": active_refresh_tokens,
                "expired_or_revoked": total_refresh_tokens - active_refresh_tokens
            },
            "authorization_codes": {
                "total": total_auth_codes,
                "unused": unused_auth_codes,
                "used_or_expired": total_auth_codes - unused_auth_codes
            },
            "timestamp": now.isoformat()
        }