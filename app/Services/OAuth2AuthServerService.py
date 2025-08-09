"""OAuth2 Authorization Server Service - Laravel Passport Style

This service handles OAuth2 authorization server functionality including
token generation, validation, and grant type processing.
"""

from __future__ import annotations

import secrets
import hashlib
import base64
import json
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.Utils.ULIDUtils import ULID, ULIDUtils

from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2AccessToken import OAuth2AccessToken
from app.Models.OAuth2RefreshToken import OAuth2RefreshToken
from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode
from app.Models.OAuth2Scope import OAuth2Scope
from database.migrations.create_users_table import User
from config.database import get_database


class OAuth2TokenResponse:
    """OAuth2 token response data structure."""
    
    def __init__(
        self,
        access_token: str,
        token_type: str = "Bearer",
        expires_in: Optional[int] = None,
        refresh_token: Optional[str] = None,
        scope: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.refresh_token = refresh_token
        self.scope = scope
        self.additional_data = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        data = {
            "access_token": self.access_token,
            "token_type": self.token_type,
        }
        
        if self.expires_in is not None:
            data["expires_in"] = self.expires_in  # type: ignore[assignment]
        
        if self.refresh_token:
            data["refresh_token"] = self.refresh_token
        
        if self.scope:
            data["scope"] = self.scope
        
        data.update(self.additional_data)
        return data


class OAuth2AuthServerService:
    """OAuth2 Authorization Server Service for managing OAuth2 flows."""
    
    def __init__(self) -> None:
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # These should come from config
        self.access_token_expire_minutes = 60  # 1 hour
        self.refresh_token_expire_days = 30    # 30 days
        self.auth_code_expire_minutes = 10     # 10 minutes
        self.secret_key = "your-oauth-secret-key"  # Should be in config
        self.algorithm = "HS256"
    
    def generate_token_id(self) -> str:
        """Generate a secure random token ID using ULID."""
        return ULIDUtils.generate_token_id()
    
    def generate_client_secret(self) -> str:
        """Generate a secure client secret."""
        return secrets.token_urlsafe(48)
    
    def hash_client_secret(self, secret: str) -> str:
        """Hash client secret for secure storage."""
        return self.pwd_context.hash(secret)
    
    def verify_client_secret(self, plain_secret: str, hashed_secret: str) -> bool:
        """Verify client secret against hash."""
        return self.pwd_context.verify(plain_secret, hashed_secret)
    
    def create_jwt_token(
        self,
        token_data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token."""
        to_encode = token_data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "iss": "fastapi-laravel-oauth",
            "aud": "api"
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def decode_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def create_access_token(
        self,
        db: Session,
        client: OAuth2Client,
        user: Optional[User] = None,
        scopes: Optional[List[str]] = None,
        name: Optional[str] = None
    ) -> OAuth2AccessToken:
        """Create new access token."""
        token_id = self.generate_token_id()
        
        # Create JWT payload
        jwt_payload = {
            "sub": user.id if user else None,
            "client_id": client.client_id,
            "token_id": token_id,
            "scopes": scopes or [],
            "type": "access_token"
        }
        
        # Generate JWT token
        jwt_token = self.create_jwt_token(jwt_payload)
        
        # Create access token record
        access_token = OAuth2AccessToken(
            token_id=token_id,
            user_id=user.id if user else None,
            client_id=client.id,
            name=name,
            scopes=json.dumps(scopes or []),
            expires_at=datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        )
        
        db.add(access_token)
        db.commit()
        db.refresh(access_token)
        
        return access_token
    
    def create_refresh_token(
        self,
        db: Session,
        access_token: OAuth2AccessToken,
        client: OAuth2Client
    ) -> OAuth2RefreshToken:
        """Create refresh token for access token."""
        token_id = self.generate_token_id()
        
        refresh_token = OAuth2RefreshToken(
            token_id=token_id,
            access_token_id=access_token.token_id,
            client_id=client.id,
            expires_at=datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        )
        
        db.add(refresh_token)
        db.commit()
        db.refresh(refresh_token)
        
        return refresh_token
    
    def create_authorization_code(
        self,
        db: Session,
        client: OAuth2Client,
        user: User,
        redirect_uri: str,
        scopes: Optional[List[str]] = None,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None
    ) -> OAuth2AuthorizationCode:
        """Create authorization code for OAuth2 flow."""
        code_id = self.generate_token_id()
        
        auth_code = OAuth2AuthorizationCode(
            code_id=code_id,
            user_id=user.id,
            client_id=client.id,
            redirect_uri=redirect_uri,
            scopes=json.dumps(scopes or []),
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=datetime.utcnow() + timedelta(minutes=self.auth_code_expire_minutes)
        )
        
        db.add(auth_code)
        db.commit()
        db.refresh(auth_code)
        
        return auth_code
    
    def validate_client_credentials(
        self,
        db: Session,
        client_id: str,
        client_secret: Optional[str] = None
    ) -> Optional[OAuth2Client]:
        """Validate client credentials."""
        client = db.query(OAuth2Client).filter(
            OAuth2Client.client_id == client_id,
            OAuth2Client.is_revoked == False
        ).first()
        
        if not client:
            return None
        
        # Public clients don't need secret verification
        if client.is_public:
            return client
        
        # Confidential clients must provide valid secret
        if not client_secret or not client.client_secret:
            return None
        
        if not self.verify_client_secret(client_secret, client.client_secret):
            return None
        
        return client
    
    def find_access_token_by_id(self, db: Session, token_id: str) -> Optional[OAuth2AccessToken]:
        """Find access token by token ID."""
        return db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.token_id == token_id
        ).first()
    
    def find_refresh_token_by_id(self, db: Session, token_id: str) -> Optional[OAuth2RefreshToken]:
        """Find refresh token by token ID."""
        return db.query(OAuth2RefreshToken).filter(
            OAuth2RefreshToken.token_id == token_id
        ).first()
    
    def find_auth_code_by_id(self, db: Session, code_id: str) -> Optional[OAuth2AuthorizationCode]:
        """Find authorization code by code ID."""
        return db.query(OAuth2AuthorizationCode).filter(
            OAuth2AuthorizationCode.code_id == code_id
        ).first()
    
    def validate_access_token(self, db: Session, token: str) -> Optional[OAuth2AccessToken]:
        """Validate JWT access token and return token record."""
        payload = self.decode_jwt_token(token)
        if not payload:
            return None
        
        token_id = payload.get("token_id")
        if not token_id:
            return None
        
        access_token = self.find_access_token_by_id(db, token_id)
        if not access_token or not access_token.is_valid:
            return None
        
        return access_token
    
    def revoke_access_token(self, db: Session, token_id: str) -> bool:
        """Revoke access token."""
        access_token = self.find_access_token_by_id(db, token_id)
        if not access_token:
            return False
        
        access_token.revoke()
        db.commit()
        return True
    
    def revoke_refresh_token(self, db: Session, token_id: str) -> bool:
        """Revoke refresh token."""
        refresh_token = self.find_refresh_token_by_id(db, token_id)
        if not refresh_token:
            return False
        
        refresh_token.revoke()
        db.commit()
        return True
    
    def introspect_token(self, db: Session, token: str) -> Optional[Dict[str, Any]]:
        """Introspect access token (RFC 7662)."""
        access_token = self.validate_access_token(db, token)
        if not access_token:
            return {"active": False}
        
        return {
            "active": True,
            "client_id": access_token.client.client_id,
            "username": access_token.user.email if access_token.user else None,
            "scope": " ".join(access_token.get_scopes()),
            "exp": int(access_token.expires_at.timestamp()) if access_token.expires_at else None,
            "iat": int(access_token.created_at.timestamp()),
            "token_type": "Bearer",
            "sub": access_token.user_id if access_token.user_id else None
        }
    
    def get_default_scopes(self, db: Session) -> List[str]:
        """Get default OAuth2 scopes."""
        scopes = db.query(OAuth2Scope).all()
        return [scope.scope_id for scope in scopes]
    
    def validate_scopes(self, db: Session, requested_scopes: List[str]) -> List[str]:
        """Validate requested scopes against available scopes."""
        available_scopes = db.query(OAuth2Scope.scope_id).all()
        available_scope_ids = [scope[0] for scope in available_scopes]
        
        return [scope for scope in requested_scopes if scope in available_scope_ids]