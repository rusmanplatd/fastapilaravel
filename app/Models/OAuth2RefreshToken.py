"""OAuth2 Refresh Token Model - Laravel Passport Style

This module defines the OAuth2 Refresh Token model with strict typing,
similar to Laravel Passport's refresh token model.
"""

from __future__ import annotations

from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional, TYPE_CHECKING, Dict, Any, cast
from datetime import datetime, timedelta

from app.Models.BaseModel import BaseModel
from app.Utils.ULIDUtils import ULID

if TYPE_CHECKING:
    from app.Models.OAuth2AccessToken import OAuth2AccessToken


class OAuth2RefreshToken(BaseModel):
    """OAuth2 Refresh Token model with Laravel Passport compatibility."""
    
    __tablename__ = "oauth_refresh_tokens"
    
    # Token identification - using ULID for token_id
    token_id: Mapped[str] = mapped_column(String(26), unique=True, index=True, nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Associated access token
    access_token_id: Mapped[str] = mapped_column(
        String(26), 
        ForeignKey("oauth_access_tokens.token_id"), 
        nullable=False,
        unique=True  # One refresh token per access token
    )
    
    # Token status
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationships
    access_token = relationship(
        "OAuth2AccessToken", 
        back_populates="refresh_token"
    )
    
    def __repr__(self) -> str:
        return f"<OAuth2RefreshToken(token_id='{self.token_id}', access_token_id='{self.access_token_id}')>"
    
    @property
    def is_expired(self) -> bool:
        """Check if refresh token is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if refresh token is valid (not expired and not revoked)."""
        return not self.is_expired and not self.is_revoked
    
    @property
    def expires_in(self) -> int:
        """Get seconds until token expires."""
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return int(delta.total_seconds())
    
    @property
    def client_id(self) -> Optional[str]:
        """Get client ID through access token."""
        if self.access_token:
            return cast(str, self.access_token.client_id)
        return None
    
    @property
    def user_id(self) -> Optional[ULID]:
        """Get user ID through access token."""
        if self.access_token:
            return cast(Optional[ULID], self.access_token.user_id)
        return None
    
    @property
    def scopes(self) -> str:
        """Get scopes through access token."""
        if self.access_token:
            return cast(str, self.access_token.scopes)
        return ""
    
    def revoke(self) -> None:
        """Revoke the refresh token."""
        self.is_revoked = True
    
    def extend_expiration(self, days: int) -> None:
        """Extend token expiration."""
        self.expires_at = self.expires_at + timedelta(days=days)
    
    def can_be_used_to_refresh(self) -> bool:
        """Check if token can be used to refresh access token."""
        if not self.is_valid:
            return False
            
        # Check if associated access token exists and is from same client
        if not self.access_token:
            return False
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert refresh token to dictionary."""
        return {
            "id": self.id,
            "token_id": self.token_id,
            "access_token_id": self.access_token_id,
            "client_id": self.client_id,
            "user_id": self.user_id,
            "scopes": self.scopes,
            "is_revoked": self.is_revoked,
            "is_expired": self.is_expired,
            "is_valid": self.is_valid,
            "expires_at": self.expires_at.isoformat(),
            "expires_in": self.expires_in,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }