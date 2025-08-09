"""OpenID Connect Utilities - Google IDP Style

This module provides utilities for OpenID Connect ID token generation and validation,
following Google's Identity Provider implementation patterns.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
import hashlib
import base64
from jose import jwt, JWTError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.Models.User import User
from app.Models.OAuth2Client import OAuth2Client
from config.oauth2 import get_oauth2_settings
from config.settings import settings


class OpenIDConnectUtils:
    """OpenID Connect utilities for ID token generation and validation."""
    
    @staticmethod
    def create_id_token(
        user: User,
        client: OAuth2Client,
        scopes: List[str],
        nonce: Optional[str] = None,
        auth_time: Optional[datetime] = None,
        max_age: Optional[int] = None,
        acr: Optional[str] = None,
        access_token: Optional[str] = None
    ) -> str:
        """
        Create OpenID Connect ID token (Google-style).
        
        Args:
            user: User model instance
            client: OAuth2 client
            scopes: List of granted scopes
            nonce: Nonce value from authorization request
            auth_time: Authentication time
            max_age: Maximum authentication age in seconds
            acr: Authentication Context Class Reference
            access_token: Access token for at_hash claim
        
        Returns:
            JWT ID token
        """
        oauth2_settings = get_oauth2_settings()
        now = datetime.utcnow()
        
        # Base claims (always included)
        claims = {
            "iss": oauth2_settings.oauth2_openid_connect_issuer,
            "sub": str(user.id),  # Subject identifier
            "aud": client.client_id,  # Audience (client ID)
            "exp": int((now + timedelta(minutes=oauth2_settings.oauth2_access_token_expire_minutes)).timestamp()),
            "iat": int(now.timestamp()),  # Issued at
            "auth_time": int((auth_time or now).timestamp()),  # Authentication time
        }
        
        # Add nonce if provided (CSRF protection)
        if nonce:
            claims["nonce"] = nonce
        
        # Add ACR (Authentication Context Class Reference)
        if acr:
            claims["acr"] = acr
        else:
            claims["acr"] = "1"  # Default ACR level
        
        # Add AMR (Authentication Methods References)
        claims["amr"] = ["pwd"]  # Password authentication
        
        # Add azp (Authorized party) if different from audience
        claims["azp"] = client.client_id
        
        # Add profile scope claims
        if "profile" in scopes:
            claims.update({
                "name": OpenIDConnectUtils._get_user_full_name(user),
                "given_name": getattr(user, 'first_name', None),
                "family_name": getattr(user, 'last_name', None),
                "picture": getattr(user, 'avatar_url', None),
                "locale": getattr(user, 'locale', 'en'),
            })
            
            # Add preferred_username if available
            if hasattr(user, 'username') and user.username:
                claims["preferred_username"] = user.username
        
        # Add email scope claims
        if "email" in scopes:
            claims.update({
                "email": user.email,
                "email_verified": getattr(user, 'email_verified_at', None) is not None
            })
        
        # Add phone scope claims (if available)
        if "phone" in scopes:
            phone_number = getattr(user, 'phone_number', None)
            if phone_number:
                claims.update({
                    "phone_number": phone_number,
                    "phone_number_verified": getattr(user, 'phone_verified_at', None) is not None
                })
        
        # Add at_hash (access token hash) if access token provided
        if access_token:
            claims["at_hash"] = OpenIDConnectUtils._create_token_hash(access_token)
        
        # Remove None values
        claims = {k: v for k, v in claims.items() if v is not None}
        
        # Sign the token
        return jwt.encode(
            claims,
            oauth2_settings.oauth2_secret_key,
            algorithm=oauth2_settings.oauth2_algorithm
        )
    
    @staticmethod
    def validate_id_token(
        id_token: str,
        client_id: str,
        nonce: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Validate OpenID Connect ID token.
        
        Args:
            id_token: JWT ID token to validate
            client_id: Expected client ID (audience)
            nonce: Expected nonce value
        
        Returns:
            Token payload if valid, None otherwise
        """
        oauth2_settings = get_oauth2_settings()
        
        try:
            # Decode and verify token
            payload = jwt.decode(
                id_token,
                oauth2_settings.oauth2_secret_key,
                algorithms=[oauth2_settings.oauth2_algorithm],
                audience=client_id,
                issuer=oauth2_settings.oauth2_openid_connect_issuer
            )
            
            # Validate nonce if provided
            if nonce and payload.get("nonce") != nonce:
                return None
            
            # Check token expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                return None
            
            return payload
            
        except JWTError:
            return None
    
    @staticmethod
    def get_public_keys() -> Dict[str, Any]:
        """
        Get public keys for JWT verification (JWKS format).
        
        Returns:
            JWKS document with public keys
        """
        # For development, return a minimal JWKS
        # In production, you should use RSA keys
        return {
            "keys": [
                {
                    "kty": "oct",  # Symmetric key for HS256
                    "alg": "HS256",
                    "use": "sig",
                    "kid": "1",
                    "k": base64.urlsafe_b64encode(
                        get_oauth2_settings().oauth2_secret_key.encode()
                    ).decode().rstrip("=")
                }
            ]
        }
    
    @staticmethod
    def _get_user_full_name(user: User) -> Optional[str]:
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
    
    @staticmethod
    def _create_token_hash(token: str) -> str:
        """
        Create token hash for at_hash claim.
        
        Args:
            token: Token to hash
        
        Returns:
            Base64URL-encoded hash
        """
        # For HS256/RS256, use SHA-256 and take left-most 128 bits
        hash_bytes = hashlib.sha256(token.encode()).digest()
        hash_half = hash_bytes[:16]  # Left-most 128 bits
        return base64.urlsafe_b64encode(hash_half).decode().rstrip('=')


class IDTokenGenerator:
    """Google-style ID token generator."""
    
    def __init__(self) -> None:
        self.oauth2_settings = get_oauth2_settings()
    
    def generate_id_token(
        self,
        user: User,
        client: OAuth2Client,
        scopes: List[str],
        **kwargs: Any
    ) -> str:
        """
        Generate ID token using OpenIDConnectUtils.
        
        Args:
            user: User model instance
            client: OAuth2 client
            scopes: List of granted scopes
            **kwargs: Additional token parameters
        
        Returns:
            JWT ID token
        """
        return OpenIDConnectUtils.create_id_token(
            user=user,
            client=client,
            scopes=scopes,
            **kwargs
        )
    
    def validate_id_token(
        self,
        id_token: str,
        client_id: str,
        **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Validate ID token.
        
        Args:
            id_token: JWT ID token to validate
            client_id: Expected client ID
            **kwargs: Additional validation parameters
        
        Returns:
            Token payload if valid, None otherwise
        """
        return OpenIDConnectUtils.validate_id_token(
            id_token=id_token,
            client_id=client_id,
            **kwargs
        )