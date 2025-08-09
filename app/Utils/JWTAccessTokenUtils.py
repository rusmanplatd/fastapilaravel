"""JWT Access Token Utilities - RFC 9068

This module implements JWT-based access tokens following RFC 9068
"JSON Web Token (JWT) Profile for OAuth 2.0 Access Tokens".
"""

from __future__ import annotations

import time
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from jose import jwt, JWTError

from app.Models.User import User
from app.Models.OAuth2Client import OAuth2Client
from config.oauth2 import get_oauth2_settings


class JWTAccessTokenProfile:
    """JWT Access Token Profile implementation (RFC 9068)."""
    
    def __init__(self) -> None:
        self.oauth2_settings = get_oauth2_settings()
    
    def create_jwt_access_token(
        self,
        client: OAuth2Client,
        user: Optional[User] = None,
        scopes: Optional[List[str]] = None,
        audience: Optional[Union[str, List[str]]] = None,
        resource_indicators: Optional[List[str]] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
        expires_in: Optional[int] = None
    ) -> str:
        """
        Create JWT access token according to RFC 9068.
        
        Args:
            client: OAuth2 client
            user: Resource owner (optional for client credentials)
            scopes: Granted scopes
            audience: Token audience
            resource_indicators: RFC 8707 resource indicators
            additional_claims: Additional custom claims
            expires_in: Token lifetime in seconds
        
        Returns:
            JWT access token
        """
        now = datetime.utcnow()
        exp_time = expires_in or (self.oauth2_settings.oauth2_access_token_expire_minutes * 60)
        exp = now + timedelta(seconds=exp_time)
        
        # RFC 9068: Required claims
        claims = {
            "iss": self.oauth2_settings.oauth2_openid_connect_issuer,  # Issuer
            "exp": int(exp.timestamp()),  # Expiration time
            "iat": int(now.timestamp()),  # Issued at
            "jti": self._generate_jti(),  # JWT ID
            "client_id": client.client_id,  # Client identifier
        }
        
        # RFC 9068: Subject claim
        if user:
            claims["sub"] = str(user.id)
        else:
            # For client credentials flow, subject is the client
            claims["sub"] = client.client_id
        
        # RFC 9068: Audience claim
        if audience:
            claims["aud"] = audience
        elif resource_indicators:
            # Use resource indicators as audience
            claims["aud"] = resource_indicators
        else:
            # Default audience
            claims["aud"] = "api"
        
        # RFC 9068: Scope claim
        if scopes:
            claims["scope"] = " ".join(scopes)
        
        # RFC 8707: Resource indicators
        if resource_indicators:
            claims["resource"] = resource_indicators
        
        # Authentication context claims
        if user:
            claims["auth_time"] = int(now.timestamp())
            claims["amr"] = ["pwd"]  # Authentication methods
        
        # Client-specific claims
        claims["azp"] = client.client_id  # Authorized party
        claims["client_name"] = client.name
        
        # Token type indicator (RFC 9068)
        claims["typ"] = "at+jwt"  # Access token JWT type
        
        # Add custom claims
        if additional_claims:
            # Ensure we don't override standard claims
            for key, value in additional_claims.items():
                if key not in claims:
                    claims[key] = value
        
        # Sign the token
        return jwt.encode(
            claims,
            self.oauth2_settings.oauth2_secret_key,
            algorithm=self.oauth2_settings.oauth2_algorithm,
            headers={"typ": "at+jwt"}  # RFC 9068: JWT type in header
        )
    
    def validate_jwt_access_token(
        self,
        token: str,
        audience: Optional[Union[str, List[str]]] = None,
        required_scopes: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Validate JWT access token according to RFC 9068.
        
        Args:
            token: JWT access token to validate
            audience: Expected audience
            required_scopes: Required scopes for authorization
        
        Returns:
            Token payload if valid, None otherwise
        """
        try:
            # Decode without verification first to check type
            unverified_payload = jwt.get_unverified_claims(token)
            unverified_header = jwt.get_unverified_header(token)
            
            # RFC 9068: Check JWT type
            if unverified_header.get("typ") != "at+jwt":
                return None
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                self.oauth2_settings.oauth2_secret_key,
                algorithms=[self.oauth2_settings.oauth2_algorithm],
                issuer=self.oauth2_settings.oauth2_openid_connect_issuer
            )
            
            # RFC 9068: Validate required claims
            required_claims = ["iss", "exp", "iat", "client_id"]
            for claim in required_claims:
                if claim not in payload:
                    return None
            
            # Validate audience if specified
            if audience:
                token_aud = payload.get("aud")
                if not token_aud:
                    return None
                
                # Handle both string and list audiences
                if isinstance(audience, str):
                    audience = [audience]
                
                if isinstance(token_aud, str):
                    token_aud = [token_aud]
                
                if not any(aud in token_aud for aud in audience):
                    return None
            
            # Validate scopes if required
            if required_scopes:
                token_scope = payload.get("scope", "")
                token_scopes = token_scope.split() if token_scope else []
                
                if not all(scope in token_scopes for scope in required_scopes):
                    return None
            
            # Check expiration (already done by jwt.decode, but explicit check)
            if payload.get("exp", 0) < time.time():
                return None
            
            return payload
            
        except JWTError:
            return None
    
    def introspect_jwt_access_token(
        self,
        token: str,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Introspect JWT access token (RFC 7662 compatible).
        
        Args:
            token: JWT access token to introspect
            client_id: Client making the introspection request
        
        Returns:
            Introspection response
        """
        payload = self.validate_jwt_access_token(token)
        
        if not payload:
            return {"active": False}
        
        # Check client authorization for introspection
        if client_id and payload.get("client_id") != client_id:
            # Client can only introspect its own tokens (or implement broader policy)
            return {"active": False}
        
        # RFC 7662: Active token response
        response = {
            "active": True,
            "scope": payload.get("scope"),
            "client_id": payload.get("client_id"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
            "sub": payload.get("sub"),
            "aud": payload.get("aud"),
            "iss": payload.get("iss"),
            "jti": payload.get("jti"),
            "token_type": "Bearer"
        }
        
        # Add resource indicators if present
        if "resource" in payload:
            response["resource"] = payload["resource"]
        
        # Add authentication context
        if "auth_time" in payload:
            response["auth_time"] = payload["auth_time"]
        
        if "amr" in payload:
            response["amr"] = payload["amr"]
        
        # Remove None values
        return {k: v for k, v in response.items() if v is not None}
    
    def extract_claims(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Extract claims from JWT access token without validation.
        
        Args:
            token: JWT access token
        
        Returns:
            Token claims if parseable, None otherwise
        """
        try:
            return jwt.get_unverified_claims(token)
        except JWTError:
            return None
    
    def is_jwt_access_token(self, token: str) -> bool:
        """
        Check if a token is a JWT access token.
        
        Args:
            token: Token to check
        
        Returns:
            True if JWT access token, False otherwise
        """
        try:
            header = jwt.get_unverified_header(token)
            return header.get("typ") == "at+jwt"
        except JWTError:
            return False
    
    def _generate_jti(self) -> str:
        """Generate a unique JWT ID."""
        import secrets
        return secrets.token_urlsafe(16)
    
    def create_structured_access_token(
        self,
        client: OAuth2Client,
        user: Optional[User] = None,
        scopes: Optional[List[str]] = None,
        resource_server: Optional[str] = None,
        permissions: Optional[List[str]] = None
    ) -> str:
        """
        Create structured access token with fine-grained permissions.
        
        This extends RFC 9068 with structured authorization data
        for fine-grained access control.
        
        Args:
            client: OAuth2 client
            user: Resource owner
            scopes: OAuth2 scopes
            resource_server: Target resource server
            permissions: Fine-grained permissions
        
        Returns:
            Structured JWT access token
        """
        additional_claims = {}
        
        # Add resource server claim
        if resource_server:
            additional_claims["rs"] = resource_server
        
        # Add fine-grained permissions
        if permissions:
            additional_claims["permissions"] = permissions
        
        # Add user context if available
        if user:
            additional_claims["user_context"] = {
                "email": getattr(user, 'email', None),
                "roles": getattr(user, 'roles', []) if hasattr(user, 'roles') else [],
                "tenant": getattr(user, 'tenant_id', None)
            }
        
        return self.create_jwt_access_token(
            client=client,
            user=user,
            scopes=scopes,
            audience=resource_server,
            additional_claims=additional_claims
        )