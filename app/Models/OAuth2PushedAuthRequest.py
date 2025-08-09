"""OAuth2 Pushed Authorization Request Model - RFC 9126

This model represents pushed authorization requests for enhanced security
authorization flows as defined in RFC 9126.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.Models.BaseModel import BaseModel


class OAuth2PushedAuthRequest(BaseModel):
    """OAuth2 Pushed Authorization Request model (RFC 9126)."""
    
    __tablename__ = "oauth_pushed_auth_requests"
    
    # Request URI (RFC 9126)
    request_uri: str = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique request URI for the pushed authorization request"
    )
    
    # Client relationship
    client_id: str = Column(
        String(255),
        ForeignKey("oauth_clients.id"),
        nullable=False,
        comment="OAuth2 client identifier"
    )
    
    # Authorization request parameters
    response_type: str = Column(
        String(50),
        nullable=False,
        comment="OAuth2 response type"
    )
    
    redirect_uri: str = Column(
        String(255),
        nullable=False,
        comment="Client redirect URI"
    )
    
    scope: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Requested OAuth2 scopes"
    )
    
    state: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="State parameter for CSRF protection"
    )
    
    # PKCE parameters
    code_challenge: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="PKCE code challenge"
    )
    
    code_challenge_method: Optional[str] = Column(
        String(10),
        nullable=True,
        comment="PKCE code challenge method"
    )
    
    # OpenID Connect parameters
    nonce: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="OpenID Connect nonce parameter"
    )
    
    display: Optional[str] = Column(
        String(20),
        nullable=True,
        comment="Display parameter"
    )
    
    prompt: Optional[str] = Column(
        String(50),
        nullable=True,
        comment="Prompt parameter"
    )
    
    max_age: Optional[int] = Column(
        Integer,
        nullable=True,
        comment="Maximum authentication age in seconds"
    )
    
    ui_locales: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="UI locales"
    )
    
    id_token_hint: Optional[str] = Column(
        Text,
        nullable=True,
        comment="ID token hint"
    )
    
    login_hint: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="Login hint"
    )
    
    acr_values: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="Authentication Context Class Reference values"
    )
    
    # RFC 8707 Resource Indicators
    resource_indicators: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Resource indicators (RFC 8707)"
    )
    
    # Additional parameters
    audience: Optional[str] = Column(
        String(255),
        nullable=True,
        comment="Token audience"
    )
    
    claims: Optional[str] = Column(
        Text,
        nullable=True,
        comment="Requested claims (JSON)"
    )
    
    # Expiration
    expires_at: datetime = Column(
        DateTime,
        nullable=False,
        comment="When the pushed authorization request expires"
    )
    
    # Relationships
    client = relationship("OAuth2Client", back_populates="pushed_auth_requests")
    
    def is_expired(self) -> bool:
        """
        Check if the pushed authorization request has expired.
        
        Returns:
            True if expired, False otherwise
        """
        return datetime.utcnow() > self.expires_at
    
    def get_scopes(self) -> List[str]:
        """
        Get the list of requested scopes.
        
        Returns:
            List of scope strings
        """
        if not self.scope:
            return []
        return self.scope.split()
    
    def get_resource_indicators(self) -> List[str]:
        """
        Get the list of resource indicators.
        
        Returns:
            List of resource indicator URIs
        """
        if not self.resource_indicators:
            return []
        return self.resource_indicators.split()
    
    def get_authorization_parameters(self) -> Dict[str, Any]:
        """
        Get all authorization parameters as a dictionary.
        
        Returns:
            Dictionary of authorization parameters
        """
        params = {
            "response_type": self.response_type,
            "client_id": self.client.client_id if self.client else None,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": self.code_challenge_method,
            "nonce": self.nonce,
            "display": self.display,
            "prompt": self.prompt,
            "max_age": self.max_age,
            "ui_locales": self.ui_locales,
            "id_token_hint": self.id_token_hint,
            "login_hint": self.login_hint,
            "acr_values": self.acr_values,
            "audience": self.audience,
            "claims": self.claims
        }
        
        # Add resource indicators as list
        if self.resource_indicators:
            params["resource"] = self.get_resource_indicators()
        
        # Remove None values
        return {k: v for k, v in params.items() if v is not None}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "request_uri": self.request_uri,
            "client_id": self.client_id,
            "response_type": self.response_type,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": self.code_challenge_method,
            "nonce": self.nonce,
            "display": self.display,
            "prompt": self.prompt,
            "max_age": self.max_age,
            "ui_locales": self.ui_locales,
            "id_token_hint": self.id_token_hint,
            "login_hint": self.login_hint,
            "acr_values": self.acr_values,
            "resource_indicators": self.resource_indicators,
            "audience": self.audience,
            "claims": self.claims,
            "expires_at": self.expires_at.isoformat(),
            "is_expired": self.is_expired(),
            "scopes": self.get_scopes(),
            "resource_indicators_list": self.get_resource_indicators(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }