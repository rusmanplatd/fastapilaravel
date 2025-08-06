"""OAuth2 Access Token Model - Laravel Passport Style

This module defines the OAuth2 access token model for managing API access tokens
similar to Laravel Passport's oauth_access_tokens table.
"""

from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, relationship
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from database.migrations.create_users_table import User
    from database.migrations.create_oauth_clients_table import OAuthClient


class OAuthAccessToken(BaseModel):
    """OAuth2 Access Token model for managing API access tokens."""
    
    __tablename__ = "oauth_access_tokens"
    
    # Token identification
    token_id: Mapped[str] = Column(String(100), unique=True, index=True, nullable=False)
    
    # Relationships
    user_id: Mapped[Optional[int]] = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    client_id: Mapped[int] = Column(
        Integer, ForeignKey("oauth_clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Token details
    name: Mapped[Optional[str]] = Column(String(191), nullable=True)
    scopes: Mapped[Optional[str]] = Column(Text, nullable=True)  # JSON array as text
    
    # Token status
    revoked: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped[Optional[User]] = relationship("User", back_populates="oauth_access_tokens")
    client: Mapped[OAuthClient] = relationship("OAuthClient", back_populates="access_tokens")
    
    def __str__(self) -> str:
        """String representation of the access token."""
        return f"OAuthAccessToken(token_id={self.token_id}, client_id={self.client_id})"
    
    def __repr__(self) -> str:
        """Developer representation of the access token."""
        return (
            f"<OAuthAccessToken(id={self.id}, token_id='{self.token_id}', "
            f"client_id={self.client_id}, user_id={self.user_id}, revoked={self.revoked})>"
        )
    
    def is_revoked(self) -> bool:
        """Check if the token is revoked."""
        return self.revoked
    
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if the token is valid (not revoked and not expired)."""
        return not self.is_revoked() and not self.is_expired()
    
    def revoke(self) -> None:
        """Revoke the token."""
        self.revoked = True
    
    def get_scopes(self) -> List[str]:
        """Get the list of scopes for this token."""
        if not self.scopes:
            return []
        
        import json
        try:
            scopes_list = json.loads(self.scopes)
            return scopes_list if isinstance(scopes_list, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_scopes(self, scopes: List[str]) -> None:
        """Set the scopes for this token."""
        import json
        self.scopes = json.dumps(scopes)
    
    def has_scope(self, scope: str) -> bool:
        """Check if the token has a specific scope."""
        return scope in self.get_scopes()
    
    def has_any_scope(self, scopes: List[str]) -> bool:
        """Check if the token has any of the given scopes."""
        token_scopes = self.get_scopes()
        return any(scope in token_scopes for scope in scopes)
    
    def has_all_scopes(self, scopes: List[str]) -> bool:
        """Check if the token has all of the given scopes."""
        token_scopes = self.get_scopes()
        return all(scope in token_scopes for scope in scopes)