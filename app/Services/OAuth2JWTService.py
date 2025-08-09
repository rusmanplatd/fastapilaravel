"""OAuth2 JWT Access Token Service - RFC 9068

This service implements RFC 9068: JSON Web Token (JWT) Profile for OAuth 2.0 Access Tokens.
This specification defines a profile for issuing access tokens in JWT format.
"""

from __future__ import annotations

import json
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import jwt

from app.Services.BaseService import BaseService
from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2AccessToken import OAuth2AccessToken
from app.Models.User import User
from app.Utils.ULIDUtils import ULID
from config.oauth2 import get_oauth2_settings


class OAuth2JWTService(BaseService):
    """OAuth2 JWT Access Token service implementing RFC 9068."""
    
    def __init__(self) -> None:
        super().__init__()
        self.oauth2_settings = get_oauth2_settings()
    
    def create_jwt_access_token(
        self,
        client: OAuth2Client,
        user: Optional[User] = None,
        scope: Optional[str] = None,
        audience: Optional[List[str]] = None,
        resource: Optional[List[str]] = None,
        authorization_details: Optional[List[Dict[str, Any]]] = None,
        expires_in: Optional[int] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a JWT access token according to RFC 9068.
        
        Args:
            client: OAuth2 client
            user: Optional user
            scope: Token scope
            audience: Token audience
            resource: Resource indicators (RFC 8707)
            authorization_details: Rich authorization details (RFC 9396)
            expires_in: Token expiration in seconds
            additional_claims: Additional claims to include
        
        Returns:
            JWT access token
        """
        now = int(time.time())
        expires_at = now + (expires_in or self.oauth2_settings.oauth2_access_token_expire_minutes * 60)
        
        # Core claims per RFC 9068
        claims = {
            # Standard JWT claims
            "iss": self.oauth2_settings.oauth2_openid_connect_issuer,  # Issuer
            "sub": str(user.id) if user else client.id.str,  # Subject
            "aud": audience or [client.id.str],  # Audience
            "exp": expires_at,  # Expiration time
            "iat": now,  # Issued at
            "jti": ULID().str,  # JWT ID
            
            # OAuth 2.0 specific claims
            "client_id": client.id.str,  # Client identifier
            "scope": scope or "",  # Granted scope
            
            # Token type
            "token_type": "access_token+jwt",
            "token_use": "access_token"
        }
        
        # Add user information if present
        if user:
            claims.update({
                "username": user.email,
                "email": user.email,
                "email_verified": user.email_verified_at is not None,
                "name": f"{user.first_name} {user.last_name}".strip(),
                "given_name": user.first_name,
                "family_name": user.last_name,
                "preferred_username": user.email,
                "sub_jwk": None  # Could add user's public key if available
            })
        
        # Add resource indicators (RFC 8707)
        if resource:
            claims["resource"] = resource
        
        # Add rich authorization details (RFC 9396)
        if authorization_details:
            claims["authorization_details"] = authorization_details
        
        # Add client authentication method and time
        claims.update({
            "auth_time": now,
            "acr": "1",  # Authentication context class reference
            "amr": ["pwd"] if user else ["client_credentials"]  # Authentication methods
        })
        
        # Add additional claims
        if additional_claims:
            # Filter out reserved claims
            reserved_claims = {
                "iss", "sub", "aud", "exp", "iat", "jti", "client_id", 
                "scope", "token_type", "token_use", "resource", 
                "authorization_details", "auth_time", "acr", "amr"
            }
            filtered_claims = {
                k: v for k, v in additional_claims.items() 
                if k not in reserved_claims
            }
            claims.update(filtered_claims)
        
        # Create JWT
        return jwt.encode(
            payload=claims,
            key=self.oauth2_settings.oauth2_secret_key,
            algorithm=self.oauth2_settings.oauth2_algorithm,
            headers={
                "typ": "at+jwt",  # RFC 9068 token type
                "alg": self.oauth2_settings.oauth2_algorithm
            }
        )
    
    def validate_jwt_access_token(
        self,
        token: str,
        expected_audience: Optional[List[str]] = None,
        expected_scope: Optional[str] = None,
        verify_expiration: bool = True
    ) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate a JWT access token.
        
        Args:
            token: JWT access token
            expected_audience: Expected audience
            expected_scope: Expected scope
            verify_expiration: Whether to verify expiration
        
        Returns:
            Tuple of (is_valid, claims, error_message)
        """
        try:
            # Decode and verify JWT
            claims = jwt.decode(
                token,
                key=self.oauth2_settings.oauth2_secret_key,
                algorithms=[self.oauth2_settings.oauth2_algorithm],
                options={
                    "verify_exp": verify_expiration,
                    "verify_aud": expected_audience is not None
                },
                audience=expected_audience
            )
            
            # Validate RFC 9068 specific requirements
            validation_error = self._validate_jwt_claims(claims, expected_scope)
            if validation_error:
                return False, None, validation_error
            
            return True, claims, None
            
        except jwt.ExpiredSignatureError:
            return False, None, "Token has expired"
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            return False, None, f"Token validation failed: {str(e)}"
    
    def introspect_jwt_access_token(
        self,
        token: str,
        client_id: str
    ) -> Dict[str, Any]:
        """
        Introspect a JWT access token.
        
        Args:
            token: JWT access token
            client_id: Client ID performing introspection
        
        Returns:
            Introspection response
        """
        is_valid, claims, error = self.validate_jwt_access_token(token)
        
        if not is_valid:
            return {
                "active": False,
                "error": error
            }
        
        # Build introspection response per RFC 7662
        response = {
            "active": True,
            "scope": claims.get("scope", ""),
            "client_id": claims.get("client_id"),
            "username": claims.get("username"),
            "token_type": "Bearer",
            "exp": claims.get("exp"),
            "iat": claims.get("iat"),
            "sub": claims.get("sub"),
            "aud": claims.get("aud"),
            "iss": claims.get("iss"),
            "jti": claims.get("jti"),
            "auth_time": claims.get("auth_time"),
            "acr": claims.get("acr"),
            "amr": claims.get("amr")
        }
        
        # Add RFC 9068 specific claims
        response.update({
            "token_use": claims.get("token_use"),
            "token_format": "jwt"
        })
        
        # Add resource indicators if present
        if "resource" in claims:
            response["resource"] = claims["resource"]
        
        # Add authorization details if present
        if "authorization_details" in claims:
            response["authorization_details"] = claims["authorization_details"]
        
        # Filter None values
        return {k: v for k, v in response.items() if v is not None}
    
    def create_structured_access_token(
        self,
        client: OAuth2Client,
        user: Optional[User] = None,
        scope: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a structured access token with additional context.
        
        Args:
            client: OAuth2 client
            user: Optional user
            scope: Token scope
            permissions: List of specific permissions
            context: Additional context information
        
        Returns:
            Structured JWT access token
        """
        additional_claims = {}
        
        # Add permission-based claims
        if permissions:
            additional_claims["permissions"] = permissions
            additional_claims["perm"] = permissions  # Short form
        
        # Add context information
        if context:
            # Namespace context claims to avoid conflicts
            additional_claims["ctx"] = context
        
        # Add application-specific claims
        additional_claims.update({
            "app_version": "1.0.0",
            "token_version": "2",
            "features": ["jwt", "structured", "permissions"]
        })
        
        return self.create_jwt_access_token(
            client=client,
            user=user,
            scope=scope,
            additional_claims=additional_claims
        )
    
    def refresh_jwt_access_token(
        self,
        old_token: str,
        client: OAuth2Client,
        new_scope: Optional[str] = None
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Refresh a JWT access token.
        
        Args:
            old_token: Current JWT access token
            client: OAuth2 client
            new_scope: Optional new scope
        
        Returns:
            Tuple of (success, new_token, error_message)
        """
        # Validate old token (allow expired for refresh)
        is_valid, claims, error = self.validate_jwt_access_token(
            old_token, verify_expiration=False
        )
        
        if not is_valid:
            return False, None, f"Invalid token for refresh: {error}"
        
        # Verify client ownership
        if claims.get("client_id") != client.id.str:
            return False, None, "Token does not belong to this client"
        
        # Create new token with same claims but new expiration
        user = None
        if claims.get("sub") and claims.get("username"):
            # Token has user context - in real implementation, fetch from DB
            pass
        
        scope = new_scope or claims.get("scope", "")
        
        # Preserve additional claims
        additional_claims = {
            k: v for k, v in claims.items()
            if k not in {
                "iss", "sub", "aud", "exp", "iat", "jti", "client_id", 
                "scope", "token_type", "token_use", "auth_time"
            }
        }
        
        new_token = self.create_jwt_access_token(
            client=client,
            user=user,
            scope=scope,
            additional_claims=additional_claims
        )
        
        return True, new_token, None
    
    def _validate_jwt_claims(
        self,
        claims: Dict[str, Any],
        expected_scope: Optional[str] = None
    ) -> Optional[str]:
        """Validate JWT claims per RFC 9068."""
        # Check required claims
        required_claims = ["iss", "exp", "aud", "client_id"]
        for claim in required_claims:
            if claim not in claims:
                return f"Missing required claim: {claim}"
        
        # Validate token type
        token_use = claims.get("token_use")
        if token_use != "access_token":
            return f"Invalid token_use: {token_use}"
        
        # Validate scope if specified
        if expected_scope:
            token_scope = claims.get("scope", "")
            token_scopes = set(token_scope.split()) if token_scope else set()
            expected_scopes = set(expected_scope.split())
            
            if not expected_scopes.issubset(token_scopes):
                return f"Insufficient scope: expected {expected_scope}, got {token_scope}"
        
        # Validate issuer
        expected_issuer = self.oauth2_settings.oauth2_openid_connect_issuer
        if claims.get("iss") != expected_issuer:
            return f"Invalid issuer: expected {expected_issuer}"
        
        return None
    
    def get_jwt_token_metadata(self, token: str) -> Dict[str, Any]:
        """
        Get metadata about a JWT token without validation.
        
        Args:
            token: JWT access token
        
        Returns:
            Token metadata
        """
        try:
            # Decode without verification
            header = jwt.get_unverified_header(token)
            claims = jwt.decode(token, options={"verify_signature": False})
            
            return {
                "format": "jwt",
                "type": header.get("typ"),
                "algorithm": header.get("alg"),
                "issued_at": claims.get("iat"),
                "expires_at": claims.get("exp"),
                "issuer": claims.get("iss"),
                "subject": claims.get("sub"),
                "audience": claims.get("aud"),
                "client_id": claims.get("client_id"),
                "scope": claims.get("scope"),
                "token_use": claims.get("token_use"),
                "jti": claims.get("jti"),
                "has_user_context": "username" in claims,
                "has_resource_indicators": "resource" in claims,
                "has_authorization_details": "authorization_details" in claims,
                "custom_claims": [
                    k for k in claims.keys()
                    if k not in {
                        "iss", "sub", "aud", "exp", "iat", "jti", "client_id",
                        "scope", "token_type", "token_use", "username", "email",
                        "auth_time", "acr", "amr"
                    }
                ]
            }
            
        except Exception as e:
            return {
                "format": "unknown",
                "error": f"Failed to parse token: {str(e)}"
            }