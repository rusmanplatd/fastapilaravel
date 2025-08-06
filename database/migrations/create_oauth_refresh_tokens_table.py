"""OAuth2 Refresh Token Model - Laravel Passport Style

This module defines the OAuth2 refresh token model for managing API refresh tokens
similar to Laravel Passport's oauth_refresh_tokens table.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, relationship
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from database.migrations.create_oauth_access_tokens_table import OAuthAccessToken
    from database.migrations.create_oauth_clients_table import OAuthClient


class OAuthRefreshToken(BaseModel):
    """OAuth2 Refresh Token model for managing API refresh tokens."""
    
    __tablename__ = "oauth_refresh_tokens"
    
    # Token identification - using ULID for token_id
    token_id: Mapped[str] = Column(String(26), unique=True, index=True, nullable=False)
    
    # Relationships
    access_token_id: Mapped[str] = Column(String(26), ForeignKey("oauth_access_tokens.token_id", ondelete="CASCADE"), nullable=False, index=True)
    client_id: Mapped[str] = Column(
        String(26), ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Token status
    revoked: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    
    # Relationships
    client: Mapped[OAuthClient] = relationship("OAuthClient", back_populates="refresh_tokens")
    
    def __str__(self) -> str:
        """String representation of the refresh token."""
        return f"OAuthRefreshToken(token_id={self.token_id}, access_token_id={self.access_token_id})"
    
    def __repr__(self) -> str:
        """Developer representation of the refresh token."""
        return (
            f"<OAuthRefreshToken(id={self.id}, token_id='{self.token_id}', "
            f"access_token_id='{self.access_token_id}', revoked={self.revoked})>"
        )
    
    def is_revoked(self) -> bool:
        """Check if the refresh token is revoked."""
        return self.revoked
    
    def is_expired(self) -> bool:
        """Check if the refresh token is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if the refresh token is valid (not revoked and not expired)."""
        return not self.is_revoked() and not self.is_expired()
    
    def revoke(self) -> None:
        """Revoke the refresh token."""
        self.revoked = True