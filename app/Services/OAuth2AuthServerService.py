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
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.Utils.ULIDUtils import ULID, ULIDUtils

from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2AccessToken import OAuth2AccessToken
from app.Models.OAuth2RefreshToken import OAuth2RefreshToken
from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode
from app.Models.OAuth2Scope import OAuth2Scope
from app.Models.User import User
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
        
        # Add ID token for OpenID Connect flows
        if "id_token" in self.additional_data:
            data["id_token"] = self.additional_data["id_token"]
        
        # Add other additional data
        for key, value in self.additional_data.items():
            if key != "id_token":  # Already handled above
                data[key] = value
        
        return data


class OAuth2AuthServerService:
    """OAuth2 Authorization Server Service for managing OAuth2 flows."""
    
    def __init__(self) -> None:
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # These should come from config
        self.access_token_expire_minutes = 60  # 1 hour
        self.refresh_token_expire_days = 30    # 30 days
        self.auth_code_expire_minutes = 10     # 10 minutes
        self.id_token_expire_minutes = 60      # 1 hour for ID tokens
        self.secret_key = "your-oauth-secret-key"  # Should be in config
        self.algorithm = "HS256"
        self.issuer = "http://localhost:8000"   # Should be in config
        
        # RSA keys for OpenID Connect (should be loaded from config)
        self.private_key = self._generate_rsa_key()
        self.public_key = self.private_key.public_key()
        self.kid = "1"  # Key ID
    
    def _generate_rsa_key(self) -> rsa.RSAPrivateKey:
        """Generate RSA private key for ID token signing."""
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
    
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
    
    def create_id_token(
        self,
        user: User,
        client: OAuth2Client,
        nonce: Optional[str] = None,
        auth_time: Optional[datetime] = None,
        acr: Optional[str] = None,
        amr: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None
    ) -> str:
        """Create OpenID Connect ID token."""
        now = datetime.utcnow()
        
        # Base required claims
        claims = {
            "iss": self.issuer,
            "sub": str(user.id),
            "aud": client.client_id,
            "exp": int((now + timedelta(minutes=self.id_token_expire_minutes)).timestamp()),
            "iat": int(now.timestamp()),
            "auth_time": int(auth_time.timestamp()) if auth_time else int(now.timestamp()),
        }
        
        # Add profile claims based on requested scopes
        if scopes and "email" in scopes:
            if hasattr(user, 'email') and user.email:
                claims["email"] = user.email
                claims["email_verified"] = getattr(user, 'email_verified', False)
        
        if scopes and "profile" in scopes:
            if hasattr(user, 'name') and user.name:
                claims["name"] = user.name
            if hasattr(user, 'given_name') and user.given_name:
                claims["given_name"] = user.given_name
            if hasattr(user, 'family_name') and user.family_name:
                claims["family_name"] = user.family_name
            if hasattr(user, 'picture') and user.picture:
                claims["picture"] = user.picture
            if hasattr(user, 'locale') and user.locale:
                claims["locale"] = user.locale
        
        # Optional claims
        if nonce:
            claims["nonce"] = nonce
        if acr:
            claims["acr"] = acr
        if amr:
            claims["amr"] = amr
        
        # Sign with RS256
        private_key_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return jwt.encode(
            claims,
            private_key_pem,
            algorithm="RS256",
            headers={"kid": self.kid}
        )
    
    def create_access_token(
        self,
        db: Session,
        client: OAuth2Client,
        user: Optional[User] = None,
        scopes: Optional[List[str]] = None,
        name: Optional[str] = None,
        nonce: Optional[str] = None,
        auth_time: Optional[datetime] = None,
        acr: Optional[str] = None,
        amr: Optional[List[str]] = None
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
        
        # Create access token record with OpenID Connect fields
        access_token = OAuth2AccessToken(
            token_id=token_id,
            user_id=user.id if user else None,
            client_id=client.id,
            name=name,
            token=jwt_token,
            scopes=" ".join(scopes or []),
            expires_at=datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes),
            nonce=nonce,
            auth_time=auth_time,
            acr=acr
        )
        
        # Set AMR if provided
        if amr:
            access_token.set_amr(amr)
        
        # Create ID token if OpenID Connect scope is requested
        if scopes and "openid" in scopes and user:
            id_token = self.create_id_token(
                user=user,
                client=client,
                nonce=nonce,
                auth_time=auth_time,
                acr=acr,
                amr=amr,
                scopes=scopes
            )
            access_token.id_token = id_token
        
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
        code_challenge_method: Optional[str] = None,
        nonce: Optional[str] = None,
        auth_time: Optional[datetime] = None,
        acr: Optional[str] = None,
        amr: Optional[List[str]] = None
    ) -> OAuth2AuthorizationCode:
        """Create authorization code for OAuth2 flow."""
        code_id = self.generate_token_id()
        
        # Store additional OIDC parameters in a JSON field for the auth code
        oidc_params = {}
        if nonce:
            oidc_params["nonce"] = nonce
        if auth_time:
            oidc_params["auth_time"] = auth_time.isoformat()
        if acr:
            oidc_params["acr"] = acr
        if amr:
            oidc_params["amr"] = amr
        
        auth_code = OAuth2AuthorizationCode(
            code_id=code_id,
            user_id=user.id,
            client_id=client.id,
            redirect_uri=redirect_uri,
            scopes=json.dumps(scopes or []),
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=datetime.utcnow() + timedelta(minutes=self.auth_code_expire_minutes),
            # Store OIDC params in additional field (would need to add this to model)
            # oidc_params=json.dumps(oidc_params) if oidc_params else None
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
        # Always allow standard OpenID Connect scopes
        standard_oidc_scopes = {"openid", "profile", "email", "address", "phone"}
        
        available_scopes = db.query(OAuth2Scope.scope_id).all()
        available_scope_ids = {scope[0] for scope in available_scopes}
        
        # Combine standard OIDC scopes with available custom scopes
        all_valid_scopes = standard_oidc_scopes.union(available_scope_ids)
        
        return [scope for scope in requested_scopes if scope in all_valid_scopes]
    
    def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set for ID token verification."""
        public_numbers = self.public_key.public_numbers()
        
        def int_to_base64url_uint(val: int) -> str:
            """Convert integer to base64url-encoded string."""
            import base64
            val_bytes = val.to_bytes((val.bit_length() + 7) // 8, 'big')
            return base64.urlsafe_b64encode(val_bytes).decode('ascii').rstrip('=')
        
        jwk = {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": self.kid,
            "n": int_to_base64url_uint(public_numbers.n),
            "e": int_to_base64url_uint(public_numbers.e),
        }
        
        return {"keys": [jwk]}
    
    def validate_id_token(self, id_token: str, client_id: str) -> Optional[Dict[str, Any]]:
        """Validate OpenID Connect ID token."""
        try:
            # Get public key for verification
            public_key_pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Decode and verify the token
            payload = jwt.decode(
                id_token,
                public_key_pem,
                algorithms=["RS256"],
                audience=client_id,
                issuer=self.issuer
            )
            
            return payload
        except JWTError:
            return None