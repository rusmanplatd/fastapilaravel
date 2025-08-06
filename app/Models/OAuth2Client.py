"""OAuth2 Client Model - Laravel Passport Style

This module defines the OAuth2 Client model with strict typing,
similar to Laravel Passport's client model.
"""

from __future__ import annotations

from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from datetime import datetime

from app.Models.BaseModel import BaseModel
from app.Utils.ULIDUtils import ULID

if TYPE_CHECKING:
    from app.Models.OAuth2AccessToken import OAuth2AccessToken
    from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode


class OAuth2Client(BaseModel):
    """OAuth2 Client model with Laravel Passport compatibility."""
    
    __tablename__ = "oauth_clients"
    
    # Primary identification - using ULID for client_id
    client_id: Mapped[str] = mapped_column(String(26), unique=True, index=True, nullable=False)
    client_secret: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(191), nullable=False)
    
    # Client configuration
    redirect_uris: Mapped[str] = mapped_column(Text, nullable=False, default="")
    allowed_scopes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    grant_types: Mapped[str] = mapped_column(Text, nullable=False, default="authorization_code")
    response_types: Mapped[str] = mapped_column(Text, nullable=False, default="code")
    
    # Client type and settings
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_first_party: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_password_client: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_personal_access_client: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Client status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # User association (for personal access clients)
    user_id: Mapped[Optional[ULID]] = mapped_column(String(26), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    access_tokens = relationship(
        "OAuth2AccessToken", 
        back_populates="client",
        cascade="all, delete-orphan"
    )
    
    authorization_codes = relationship(
        "OAuth2AuthorizationCode",
        back_populates="client", 
        cascade="all, delete-orphan"
    )
    
    user = relationship("User", back_populates="oauth_clients")
    
    def __repr__(self) -> str:
        return f"<OAuth2Client(client_id='{self.client_id}', name='{self.name}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if client is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property 
    def is_public(self) -> bool:
        """Check if client is public (no secret)."""
        return not self.is_confidential or self.client_secret is None
    
    def get_redirect_uris(self) -> List[str]:
        """Get list of redirect URIs."""
        if not self.redirect_uris.strip():
            return []
        return [uri.strip() for uri in self.redirect_uris.split(",") if uri.strip()]
    
    def set_redirect_uris(self, uris: List[str]) -> None:
        """Set redirect URIs from list."""
        self.redirect_uris = ",".join(uris)
    
    def get_allowed_scopes(self) -> List[str]:
        """Get list of allowed scopes."""
        if not self.allowed_scopes.strip():
            return []
        return [scope.strip() for scope in self.allowed_scopes.split(",") if scope.strip()]
    
    def set_allowed_scopes(self, scopes: List[str]) -> None:
        """Set allowed scopes from list."""
        self.allowed_scopes = ",".join(scopes)
    
    def get_grant_types(self) -> List[str]:
        """Get list of supported grant types."""
        if not self.grant_types.strip():
            return []
        return [grant.strip() for grant in self.grant_types.split(",") if grant.strip()]
    
    def set_grant_types(self, grants: List[str]) -> None:
        """Set grant types from list."""
        self.grant_types = ",".join(grants)
    
    def get_response_types(self) -> List[str]:
        """Get list of supported response types."""
        if not self.response_types.strip():
            return []
        return [response.strip() for response in self.response_types.split(",") if response.strip()]
    
    def set_response_types(self, responses: List[str]) -> None:
        """Set response types from list."""
        self.response_types = ",".join(responses)
    
    def is_redirect_uri_valid(self, redirect_uri: str) -> bool:
        """Check if redirect URI is valid for this client."""
        allowed_uris = self.get_redirect_uris()
        return redirect_uri in allowed_uris
    
    def is_scope_allowed(self, scope: str) -> bool:
        """Check if scope is allowed for this client."""
        allowed_scopes = self.get_allowed_scopes()
        return scope in allowed_scopes
    
    def is_grant_type_supported(self, grant_type: str) -> bool:
        """Check if grant type is supported by this client."""
        supported_grants = self.get_grant_types()
        return grant_type in supported_grants
    
    def is_response_type_supported(self, response_type: str) -> bool:
        """Check if response type is supported by this client."""
        supported_responses = self.get_response_types()
        return response_type in supported_responses
    
    def can_use_grant_type(self, grant_type: str) -> bool:
        """Check if client can use specific grant type based on configuration."""
        if not self.is_grant_type_supported(grant_type):
            return False
        
        # Password grant only for password clients
        if grant_type == "password" and not self.is_password_client:
            return False
            
        # Client credentials for confidential clients only
        if grant_type == "client_credentials" and not self.is_confidential:
            return False
            
        return True
    
    def revoke(self) -> None:
        """Revoke the client."""
        self.is_revoked = True
        self.is_active = False
    
    def activate(self) -> None:
        """Activate the client."""
        self.is_active = True
        self.is_revoked = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert client to dictionary."""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "name": self.name,
            "redirect_uris": self.get_redirect_uris(),
            "allowed_scopes": self.get_allowed_scopes(),
            "grant_types": self.get_grant_types(),
            "response_types": self.get_response_types(),
            "is_confidential": self.is_confidential,
            "is_first_party": self.is_first_party,
            "is_password_client": self.is_password_client,
            "is_personal_access_client": self.is_personal_access_client,
            "is_active": self.is_active,
            "is_revoked": self.is_revoked,
            "is_expired": self.is_expired,
            "user_id": self.user_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }