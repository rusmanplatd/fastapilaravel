"""OAuth2 Access Token Model - Laravel Passport Style

This module defines the OAuth2 Access Token model with strict typing,
similar to Laravel Passport's access token model.
"""

from __future__ import annotations

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from datetime import datetime, timedelta

from app.Models.BaseModel import BaseModel
from app.Utils.ULIDUtils import ULID

if TYPE_CHECKING:
    from app.Models.OAuth2Client import OAuth2Client
    from app.Models.OAuth2RefreshToken import OAuth2RefreshToken
    from app.Models.User import User


class OAuth2AccessToken(BaseModel):
    """OAuth2 Access Token model with Laravel Passport compatibility."""
    
    __tablename__ = "oauth_access_tokens"
    
    # Token identification - using ULID for token_id
    token_id = Column(String(26), unique=True, index=True, nullable=False)
    token = Column(Text, nullable=False)
    
    # Token metadata
    scopes = Column(Text, nullable=False, default="")
    token_type = Column(String(50), default="Bearer", nullable=False)
    
    # Associations
    user_id: Optional[ULID] = Column(String(26), ForeignKey("users.id"), nullable=True)
    client_id = Column(String(26), ForeignKey("oauth_clients.client_id"), nullable=False)
    
    # Token status
    is_revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    
    # Personal Access Token fields
    name = Column(String(191), nullable=True)  # For personal access tokens
    abilities = Column(Text, nullable=False, default="")  # JSON array of abilities
    
    # Relationships
    client = relationship("OAuth2Client", back_populates="access_tokens")
    user = relationship("User", back_populates="oauth_access_tokens")
    refresh_token = relationship(
        "OAuth2RefreshToken", 
        back_populates="access_token",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<OAuth2AccessToken(token_id='{self.token_id}', user_id={self.user_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        return not self.is_expired and not self.is_revoked
    
    @property
    def expires_in(self) -> int:
        """Get seconds until token expires."""
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return int(delta.total_seconds())
    
    @property
    def is_personal_access_token(self) -> bool:
        """Check if this is a personal access token."""
        return self.name is not None
    
    def get_scopes(self) -> List[str]:
        """Get list of scopes."""
        if not self.scopes.strip():
            return []
        return [scope.strip() for scope in self.scopes.split(" ") if scope.strip()]
    
    def set_scopes(self, scopes: List[str]) -> None:
        """Set scopes from list."""
        self.scopes = " ".join(scopes)
    
    def get_abilities(self) -> List[str]:
        """Get list of abilities for personal access tokens."""
        if not self.abilities.strip():
            return []
        import json
        try:
            return json.loads(self.abilities)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_abilities(self, abilities: List[str]) -> None:
        """Set abilities from list."""
        import json
        self.abilities = json.dumps(abilities)
    
    def has_scope(self, scope: str) -> bool:
        """Check if token has specific scope."""
        token_scopes = self.get_scopes()
        return scope in token_scopes or "*" in token_scopes
    
    def has_ability(self, ability: str) -> bool:
        """Check if token has specific ability (for personal access tokens)."""
        if not self.is_personal_access_token:
            return False
        
        token_abilities = self.get_abilities()
        return ability in token_abilities or "*" in token_abilities
    
    def can(self, ability_or_scope: str) -> bool:
        """Check if token can perform action (scope or ability)."""
        if self.is_personal_access_token:
            return self.has_ability(ability_or_scope)
        else:
            return self.has_scope(ability_or_scope)
    
    def revoke(self) -> None:
        """Revoke the token."""
        self.is_revoked = True
        # Also revoke associated refresh token if exists
        if self.refresh_token:
            self.refresh_token.revoke()
    
    def extend_expiration(self, minutes: int) -> None:
        """Extend token expiration."""
        self.expires_at = self.expires_at + timedelta(minutes=minutes)
    
    @classmethod
    def create_personal_access_token(
        cls,
        user_id: int,
        client_id: str,
        name: str,
        abilities: List[str],
        expires_at: Optional[datetime] = None
    ) -> OAuth2AccessToken:
        """Create a personal access token."""
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(days=365)
        
        token = cls(
            user_id=user_id,
            client_id=client_id,
            name=name,
            expires_at=expires_at,
            token_type="Bearer"
        )
        token.set_abilities(abilities)
        return token
    
    def to_token_response(self) -> Dict[str, Any]:
        """Convert to OAuth2 token response format."""
        return {
            "access_token": self.token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "scope": self.scopes,
            "refresh_token": self.refresh_token.token if self.refresh_token else None,
        }
    
    def to_introspection_response(self) -> Dict[str, Any]:
        """Convert to OAuth2 introspection response format."""
        return {
            "active": self.is_valid,
            "scope": self.scopes,
            "client_id": self.client_id,
            "username": self.user.email if self.user else None,
            "token_type": self.token_type,
            "exp": int(self.expires_at.timestamp()),
            "iat": int(self.created_at.timestamp()) if self.created_at else None,
            "sub": str(self.user_id) if self.user_id else None,
            "aud": self.client_id,
            "iss": "fastapi-laravel-oauth",
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary."""
        return {
            "id": self.id,
            "token_id": self.token_id,
            "name": self.name,
            "scopes": self.get_scopes(),
            "abilities": self.get_abilities() if self.is_personal_access_token else None,
            "token_type": self.token_type,
            "user_id": self.user_id,
            "client_id": self.client_id,
            "is_revoked": self.is_revoked,
            "is_expired": self.is_expired,
            "is_valid": self.is_valid,
            "expires_at": self.expires_at.isoformat(),
            "expires_in": self.expires_in,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }