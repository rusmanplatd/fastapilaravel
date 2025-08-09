"""Enhanced OAuth2 Token Introspection and Revocation Service - RFC 7662

This service handles comprehensive OAuth2 token introspection (RFC 7662) and 
revocation (RFC 7009) functionality with advanced security features and metadata.
"""

from __future__ import annotations

import time
import hashlib
from typing import Optional, Dict, Any, List, Union
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone

from app.Utils.ULIDUtils import ULID
from app.Models.OAuth2Client import OAuth2Client
from app.Models.OAuth2AccessToken import OAuth2AccessToken
from app.Models.OAuth2RefreshToken import OAuth2RefreshToken
from app.Services.OAuth2AuthServerService import OAuth2AuthServerService
from config.oauth2 import get_oauth2_settings


class OAuth2IntrospectionResponse:
    """Enhanced OAuth2 token introspection response structure (RFC 7662)."""
    
    def __init__(
        self,
        active: bool,
        scope: Optional[str] = None,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        token_type: Optional[str] = None,
        exp: Optional[int] = None,
        iat: Optional[int] = None,
        nbf: Optional[int] = None,
        sub: Optional[str] = None,
        aud: Optional[Union[str, List[str]]] = None,
        iss: Optional[str] = None,
        jti: Optional[str] = None,
        # RFC 7662 extensions
        cnf: Optional[Dict[str, Any]] = None,
        authorization_details: Optional[List[Dict[str, Any]]] = None,
        resource: Optional[List[str]] = None,
        # Security metadata
        auth_time: Optional[int] = None,
        acr: Optional[str] = None,
        amr: Optional[List[str]] = None,
        # Usage metadata
        usage_count: Optional[int] = None,
        first_used: Optional[int] = None,
        last_used: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        self.active = active
        self.scope = scope
        self.client_id = client_id
        self.username = username
        self.token_type = token_type
        self.exp = exp
        self.iat = iat
        self.nbf = nbf or iat  # Not before, defaults to issued at
        self.sub = sub
        self.aud = aud
        self.iss = iss
        self.jti = jti
        
        # RFC 7662 extensions
        self.cnf = cnf or {}  # Confirmation claim for bound tokens
        self.authorization_details = authorization_details or []
        self.resource = resource or []
        
        # Security metadata
        self.auth_time = auth_time
        self.acr = acr  # Authentication Context Class Reference
        self.amr = amr or []  # Authentication Methods References
        
        # Usage metadata
        self.usage_count = usage_count
        self.first_used = first_used
        self.last_used = last_used
        
        # Additional claims
        self.additional_claims = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response according to RFC 7662."""
        data = {"active": self.active}
        
        if not self.active:
            return data
        
        # RFC 7662 standard fields
        standard_fields = [
            "scope", "client_id", "username", "token_type",
            "exp", "iat", "nbf", "sub", "aud", "iss", "jti"
        ]
        
        for field in standard_fields:
            value = getattr(self, field)
            if value is not None:
                data[field] = value
        
        # RFC 7662 extension fields
        if self.cnf:
            data["cnf"] = self.cnf
        
        if self.authorization_details:
            data["authorization_details"] = self.authorization_details
        
        if self.resource:
            data["resource"] = self.resource
        
        # Security metadata
        security_fields = ["auth_time", "acr", "amr"]
        for field in security_fields:
            value = getattr(self, field)
            if value is not None:
                data[field] = value
        
        # Usage metadata
        usage_fields = ["usage_count", "first_used", "last_used"]
        for field in usage_fields:
            value = getattr(self, field)
            if value is not None:
                data[field] = value
        
        # Add any additional claims
        data.update(self.additional_claims)
        
        return data


class OAuth2RevocationResponse:
    """Enhanced OAuth2 token revocation response structure (RFC 7009)."""
    
    def __init__(
        self,
        success: bool,
        message: str = "",
        revoked_token_count: int = 0,
        related_tokens_revoked: int = 0,
        revocation_timestamp: Optional[int] = None,
        client_notified: bool = False
    ) -> None:
        self.success = success
        self.message = message
        self.revoked_token_count = revoked_token_count
        self.related_tokens_revoked = related_tokens_revoked
        self.revocation_timestamp = revocation_timestamp or int(time.time())
        self.client_notified = client_notified
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "success": self.success,
            "message": self.message,
            "revoked_token_count": self.revoked_token_count,
            "related_tokens_revoked": self.related_tokens_revoked,
            "revocation_timestamp": self.revocation_timestamp,
            "client_notified": self.client_notified
        }


class OAuth2IntrospectionService:
    """Enhanced service for OAuth2 token introspection and revocation (RFC 7662)."""
    
    def __init__(self) -> None:
        self.auth_server = OAuth2AuthServerService()
        self.oauth2_settings = get_oauth2_settings()
    
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
        """Enhanced access token introspection with RFC 7662 compliance."""
        try:
            # Validate JWT and get access token record
            access_token = self.auth_server.validate_access_token(db, token)
            
            if not access_token or not access_token.is_valid:
                return OAuth2IntrospectionResponse(active=False)
            
            # Extract security information
            cnf_claims = self._extract_confirmation_claims(token, access_token)
            auth_methods = self._extract_authentication_methods(access_token)
            usage_stats = self._get_token_usage_statistics(db, access_token)
            
            # Build enhanced introspection response
            return OAuth2IntrospectionResponse(
                active=True,
                scope=" ".join(access_token.get_scopes()),
                client_id=access_token.client.client_id,
                username=access_token.user.email if access_token.user else None,
                token_type="Bearer",
                exp=int(access_token.expires_at.timestamp()) if access_token.expires_at else None,
                iat=int(access_token.created_at.timestamp()),
                nbf=int(access_token.created_at.timestamp()),
                sub=access_token.user_id if access_token.user_id else None,
                aud=self._get_token_audience(access_token),
                iss=self.oauth2_settings.oauth2_issuer,
                jti=access_token.token_id,
                
                # Security metadata
                cnf=cnf_claims,
                acr="1",  # Authentication Context Class Reference
                amr=auth_methods,
                auth_time=int(access_token.created_at.timestamp()),
                
                # Usage statistics
                usage_count=usage_stats.get("usage_count"),
                first_used=usage_stats.get("first_used"),
                last_used=usage_stats.get("last_used"),
                
                # Additional metadata
                token_name=access_token.name,
                client_name=access_token.client.name,
                grant_type=getattr(access_token, "grant_type", "authorization_code"),
                resource=self._get_resource_indicators(access_token)
            )
            
        except Exception:
            return OAuth2IntrospectionResponse(active=False)
    
    def _introspect_refresh_token(self, db: Session, token: str) -> OAuth2IntrospectionResponse:
        """Introspect refresh token."""
        try:
            refresh_token = self.auth_server.find_refresh_token_by_id(db, token)
            
            if not refresh_token or not refresh_token.is_valid:
                return OAuth2IntrospectionResponse(active=False)
            
            # Get associated access token for additional info
            access_token = self.auth_server.find_access_token_by_id(
                db, refresh_token.access_token_id
            )
            
            return OAuth2IntrospectionResponse(
                active=True,
                client_id=refresh_token.client_id,
                token_type="refresh_token",
                exp=int(refresh_token.expires_at.timestamp()) if refresh_token.expires_at else None,
                iat=int(refresh_token.created_at.timestamp()),
                sub=access_token.user_id if access_token and access_token.user_id else None,
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
        client_id: str,
        token_type_hint: Optional[str] = None,
        client_secret: Optional[str] = None
    ) -> OAuth2RevocationResponse:
        """
        Enhanced OAuth2 token revocation according to RFC 7009.
        
        Args:
            db: Database session
            token: Token to revoke
            token_type_hint: Optional hint about token type
            client_id: Client ID for authentication
            client_secret: Client secret for authentication
        
        Returns:
            Enhanced OAuth2RevocationResponse with detailed information
        
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
        
        revoked_count = 0
        related_revoked = 0
        message_parts = []
        
        # Try to revoke as access token first
        if token_type_hint != "refresh_token":
            access_result = self._revoke_access_token_enhanced(db, token, client)
            if access_result["revoked"]:
                revoked_count += 1
                related_revoked += access_result["related_tokens"]
                message_parts.append("Access token revoked")
        
        # Try to revoke as refresh token
        if token_type_hint != "access_token" and revoked_count == 0:
            refresh_result = self._revoke_refresh_token_enhanced(db, token, client)
            if refresh_result["revoked"]:
                revoked_count += 1
                related_revoked += refresh_result["related_tokens"]
                message_parts.append("Refresh token revoked")
        
        # Determine final message
        if revoked_count > 0:
            message = f"{', '.join(message_parts)}. Related tokens: {related_revoked}"
        else:
            message = "Token processed (may have been already revoked or invalid)"
        
        # According to RFC 7009, always return success (even for invalid tokens)
        # This prevents token scanning attacks
        return OAuth2RevocationResponse(
            success=True,
            message=message,
            revoked_token_count=revoked_count,
            related_tokens_revoked=related_revoked,
            revocation_timestamp=int(time.time()),
            client_notified=True
        )
    
    def _revoke_access_token(self, db: Session, token: str, client: OAuth2Client) -> bool:
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
            refresh_tokens = db.query(OAuth2RefreshToken).filter(
                OAuth2RefreshToken.access_token_id == access_token.token_id,
                OAuth2RefreshToken.is_revoked == False
            ).all()
            
            for refresh_token in refresh_tokens:
                refresh_token.revoke()
            
            db.commit()
            return True
            
        except Exception:
            return False
    
    def _revoke_refresh_token(self, db: Session, token: str, client: OAuth2Client) -> bool:
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
            if access_token and not access_token.is_revoked:
                access_token.revoke()
            
            db.commit()
            return True
            
        except Exception:
            return False
    
    def revoke_all_tokens_for_user(
        self,
        db: Session,
        user_id: ULID,
        client_id: Optional[ULID] = None
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
        query = db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.user_id == user_id,
            OAuth2AccessToken.is_revoked == False
        )
        
        if client_id:
            query = query.filter(OAuth2AccessToken.client_id == client_id)
        
        access_tokens = query.all()
        revoked_count = 0
        
        for access_token in access_tokens:
            access_token.revoke()
            revoked_count += 1
            
            # Also revoke associated refresh tokens
            refresh_tokens = db.query(OAuth2RefreshToken).filter(
                OAuth2RefreshToken.access_token_id == access_token.token_id,
                OAuth2RefreshToken.is_revoked == False
            ).all()
            
            for refresh_token in refresh_tokens:
                refresh_token.revoke()
                revoked_count += 1
        
        db.commit()
        return revoked_count
    
    def revoke_all_tokens_for_client(self, db: Session, client_id: ULID) -> int:
        """
        Revoke all tokens for a client.
        
        Args:
            db: Database session
            client_id: Client ID
        
        Returns:
            Number of tokens revoked
        """
        # Revoke access tokens
        access_tokens = db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.client_id == client_id,
            OAuth2AccessToken.is_revoked == False
        ).all()
        
        # Revoke refresh tokens
        refresh_tokens = db.query(OAuth2RefreshToken).join(
            OAuth2AccessToken, OAuth2RefreshToken.access_token_id == OAuth2AccessToken.token_id
        ).filter(
            OAuth2AccessToken.client_id == client_id,
            OAuth2RefreshToken.is_revoked == False
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
        user_id: ULID,
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
        access_tokens = db.query(OAuth2AccessToken).filter(
            OAuth2AccessToken.user_id == user_id,
            OAuth2AccessToken.is_revoked == False
        ).order_by(OAuth2AccessToken.created_at.desc()).limit(limit).all()
        
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
                "is_expired": token.is_expired
            }
            token_list.append(token_info)
        
        return token_list
    
    def _extract_confirmation_claims(self, token: str, access_token: Any) -> Dict[str, Any]:
        """Extract confirmation claims for certificate-bound or DPoP-bound tokens."""
        cnf_claims = {}
        
        try:
            # Decode JWT to check for confirmation claims
            from jose import jwt
            payload = jwt.get_unverified_claims(token)
            
            # Check for certificate thumbprint (RFC 8705 mTLS)
            if "cnf" in payload:
                cnf = payload["cnf"]
                if "x5t#S256" in cnf:
                    cnf_claims["x5t#S256"] = cnf["x5t#S256"]
                
                # Check for DPoP thumbprint (RFC 9449)
                if "jkt" in cnf:
                    cnf_claims["jkt"] = cnf["jkt"]
            
        except Exception:
            pass
        
        return cnf_claims
    
    def _extract_authentication_methods(self, access_token: Any) -> List[str]:
        """Extract authentication methods used to obtain the token."""
        auth_methods = []
        
        # Determine auth methods based on token properties
        if hasattr(access_token, "grant_type"):
            grant_type = access_token.grant_type
            
            if grant_type == "authorization_code":
                auth_methods.append("pwd")  # Password authentication
                if hasattr(access_token, "pkce_used") and access_token.pkce_used:
                    auth_methods.append("pkce")  # PKCE used
            elif grant_type == "client_credentials":
                auth_methods.append("client_secret")
            elif grant_type == "password":
                auth_methods.append("pwd")
        
        # Check for multi-factor authentication
        if hasattr(access_token, "mfa_verified") and access_token.mfa_verified:
            auth_methods.append("mfa")
        
        return auth_methods or ["pwd"]  # Default to password auth
    
    def _get_token_usage_statistics(self, db: Session, access_token: Any) -> Dict[str, Optional[int]]:
        """Get token usage statistics (placeholder implementation)."""
        # In a real implementation, you would track token usage in a separate table
        # For now, return basic statistics
        return {
            "usage_count": getattr(access_token, "usage_count", 0),
            "first_used": int(access_token.created_at.timestamp()),
            "last_used": int(time.time()) if hasattr(access_token, "last_used_at") else None
        }
    
    def _get_token_audience(self, access_token: Any) -> Union[str, List[str]]:
        """Get token audience information."""
        # Check for resource indicators (RFC 8707)
        if hasattr(access_token, "resource_indicators"):
            resources = access_token.resource_indicators
            if resources:
                return resources if isinstance(resources, list) else [resources]
        
        # Default audience
        return self.oauth2_settings.oauth2_audience
    
    def _get_resource_indicators(self, access_token: Any) -> List[str]:
        """Get RFC 8707 resource indicators from token."""
        if hasattr(access_token, "resource_indicators"):
            resources = access_token.resource_indicators
            if resources:
                return resources if isinstance(resources, list) else [resources]
        
        return []
    
    def get_token_security_info(
        self,
        db: Session,
        token: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive security information about a token.
        
        Args:
            db: Database session
            token: Token to analyze
        
        Returns:
            Security information dictionary
        """
        try:
            # Basic introspection
            introspection = self.introspect_token(db, token)
            
            if not introspection.active:
                return {"active": False}
            
            # Extract security metadata
            security_info = {
                "active": True,
                "token_hash": hashlib.sha256(token.encode()).hexdigest()[:16],
                "algorithm": self.oauth2_settings.oauth2_algorithm,
                "certificate_bound": bool(introspection.cnf.get("x5t#S256")),
                "dpop_bound": bool(introspection.cnf.get("jkt")),
                "mfa_used": "mfa" in (introspection.amr or []),
                "pkce_used": "pkce" in (introspection.amr or []),
                "grant_type": introspection.additional_claims.get("grant_type", "unknown"),
                "security_level": self._calculate_security_level(introspection),
                "expires_in": introspection.exp - int(time.time()) if introspection.exp else None,
                "issued_ago": int(time.time()) - introspection.iat if introspection.iat else None
            }
            
            return security_info
            
        except Exception as e:
            return {"active": False, "error": str(e)}
    
    def _calculate_security_level(self, introspection: OAuth2IntrospectionResponse) -> str:
        """Calculate token security level based on various factors."""
        score = 0
        
        # Base score for active token
        if introspection.active:
            score += 10
        
        # Security enhancements
        if introspection.cnf.get("x5t#S256"):  # mTLS bound
            score += 30
        
        if introspection.cnf.get("jkt"):  # DPoP bound
            score += 25
        
        if "mfa" in (introspection.amr or []):  # MFA used
            score += 20
        
        if "pkce" in (introspection.amr or []):  # PKCE used
            score += 15
        
        # Time-based factors
        current_time = int(time.time())
        if introspection.exp and (introspection.exp - current_time) < 3600:  # Expires soon
            score -= 5
        
        if introspection.iat and (current_time - introspection.iat) > 86400:  # Old token
            score -= 10
        
        # Determine security level
        if score >= 70:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        else:
            return "minimal"
    
    def _revoke_access_token_enhanced(
        self,
        db: Session,
        token: str,
        client: OAuth2Client
    ) -> Dict[str, Any]:
        """Enhanced access token revocation with detailed tracking."""
        try:
            # Validate JWT and get token record
            access_token = self.auth_server.validate_access_token(db, token)
            
            if not access_token:
                # Try to find by token ID directly
                payload = self.auth_server.decode_jwt_token(token)
                if payload and payload.get("token_id"):
                    access_token = self.auth_server.find_access_token_by_id(db, payload["token_id"])
            
            if not access_token:
                return {"revoked": False, "related_tokens": 0}
            
            # Verify token belongs to this client
            if access_token.client_id != client.id:
                return {"revoked": False, "related_tokens": 0}
            
            # Check if already revoked
            if access_token.is_revoked:
                return {"revoked": False, "related_tokens": 0}
            
            # Revoke access token
            access_token.revoke()
            
            # Count and revoke associated refresh tokens
            refresh_tokens = db.query(OAuth2RefreshToken).filter(
                OAuth2RefreshToken.access_token_id == access_token.token_id,
                OAuth2RefreshToken.is_revoked == False
            ).all()
            
            related_count = 0
            for refresh_token in refresh_tokens:
                refresh_token.revoke()
                related_count += 1
            
            # Also revoke derived tokens (if any)
            # In a real implementation, you might have derived tokens for different services
            
            db.commit()
            
            return {"revoked": True, "related_tokens": related_count}
            
        except Exception:
            return {"revoked": False, "related_tokens": 0}
    
    def _revoke_refresh_token_enhanced(
        self,
        db: Session,
        token: str,
        client: OAuth2Client
    ) -> Dict[str, Any]:
        """Enhanced refresh token revocation with detailed tracking."""
        try:
            refresh_token = self.auth_server.find_refresh_token_by_id(db, token)
            
            if not refresh_token:
                return {"revoked": False, "related_tokens": 0}
            
            # Verify token belongs to this client
            if refresh_token.client_id != client.id:
                return {"revoked": False, "related_tokens": 0}
            
            # Check if already revoked
            if refresh_token.is_revoked:
                return {"revoked": False, "related_tokens": 0}
            
            # Revoke refresh token
            refresh_token.revoke()
            
            related_count = 0
            
            # Also revoke associated access token
            access_token = self.auth_server.find_access_token_by_id(
                db, refresh_token.access_token_id
            )
            if access_token and not access_token.is_revoked:
                access_token.revoke()
                related_count += 1
            
            db.commit()
            
            return {"revoked": True, "related_tokens": related_count}
            
        except Exception:
            return {"revoked": False, "related_tokens": 0}
    
    def create_revocation_notification(
        self,
        token_id: str,
        client_id: str,
        revocation_reason: str = "client_request"
    ) -> Dict[str, Any]:
        """
        Create revocation notification for third-party services (RFC 7009 extension).
        
        This method can be used to notify other services about token revocation
        for improved security coordination.
        
        Args:
            token_id: ID of the revoked token
            client_id: Client that requested revocation
            revocation_reason: Reason for revocation
        
        Returns:
            Notification details
        """
        notification = {
            "event": "token_revoked",
            "token_id": token_id,
            "client_id": client_id,
            "revocation_reason": revocation_reason,
            "timestamp": int(time.time()),
            "notification_id": hashlib.sha256(
                f"{token_id}:{client_id}:{time.time()}".encode()
            ).hexdigest()[:16]
        }
        
        # In a real implementation, you would send this to external services
        # For now, just return the notification structure
        return notification