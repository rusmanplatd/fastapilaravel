"""OAuth2 Authorization Code Model - Laravel Passport Style

This module defines the OAuth2 authorization code model for managing authorization codes
similar to Laravel Passport's oauth_auth_codes table.
"""

from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, relationship
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from database.migrations.create_users_table import User
    from database.migrations.create_oauth_clients_table import OAuthClient


class OAuthAuthCode(BaseModel):
    """OAuth2 Authorization Code model for managing authorization codes."""
    
    __tablename__ = "oauth_auth_codes"
    
    # Code identification - using ULID for code_id
    code_id: Mapped[str] = Column(String(26), unique=True, index=True, nullable=False)
    
    # Relationships
    user_id: Mapped[str] = Column(
        String(26), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[str] = Column(
        String(26), ForeignKey("oauth_clients.client_id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # Code details
    scopes: Mapped[Optional[str]] = Column(Text, nullable=True)  # JSON array as text
    redirect_uri: Mapped[str] = Column(Text, nullable=False)
    code_challenge: Mapped[Optional[str]] = Column(String(128), nullable=True)  # PKCE
    code_challenge_method: Mapped[Optional[str]] = Column(String(10), nullable=True)  # PKCE
    
    # Code status
    revoked: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = Column(DateTime, nullable=False)
    
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="oauth_auth_codes")
    client: Mapped[OAuthClient] = relationship("OAuthClient", back_populates="auth_codes")
    
    def __str__(self) -> str:
        """String representation of the authorization code."""
        return f"OAuthAuthCode(code_id={self.code_id}, user_id={self.user_id})"
    
    def __repr__(self) -> str:
        """Developer representation of the authorization code."""
        return (
            f"<OAuthAuthCode(id={self.id}, code_id='{self.code_id}', "
            f"user_id={self.user_id}, client_id={self.client_id}, revoked={self.revoked})>"
        )
    
    def is_revoked(self) -> bool:
        """Check if the authorization code is revoked."""
        return self.revoked
    
    def is_expired(self) -> bool:
        """Check if the authorization code is expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if the authorization code is valid (not revoked and not expired)."""
        return not self.is_revoked() and not self.is_expired()
    
    def revoke(self) -> None:
        """Revoke the authorization code."""
        self.revoked = True
    
    def get_scopes(self) -> List[str]:
        """Get the list of scopes for this authorization code."""
        if not self.scopes:
            return []
        
        import json
        try:
            scopes_list = json.loads(self.scopes)
            return scopes_list if isinstance(scopes_list, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_scopes(self, scopes: List[str]) -> None:
        """Set the scopes for this authorization code."""
        import json
        self.scopes = json.dumps(scopes)
    
    def has_scope(self, scope: str) -> bool:
        """Check if the authorization code has a specific scope."""
        return scope in self.get_scopes()
    
    def verify_code_challenge(self, code_verifier: str) -> bool:
        """Verify PKCE code challenge."""
        if not self.code_challenge or not self.code_challenge_method:
            return True  # No PKCE required
        
        import base64
        import hashlib
        
        if self.code_challenge_method == "S256":
            # SHA256 challenge
            challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip("=")
            return challenge == self.code_challenge
        elif self.code_challenge_method == "plain":
            # Plain text challenge
            return code_verifier == self.code_challenge
        
        return False