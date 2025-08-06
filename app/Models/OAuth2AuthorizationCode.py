"""OAuth2 Authorization Code Model - Laravel Passport Style

This module defines the OAuth2 Authorization Code model with strict typing,
similar to Laravel Passport's authorization code model.
"""

from __future__ import annotations

from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional, List, TYPE_CHECKING, Dict, Any
from datetime import datetime, timedelta

from app.Models.BaseModel import BaseModel
from app.Utils.ULIDUtils import ULID

if TYPE_CHECKING:
    from app.Models.OAuth2Client import OAuth2Client
    from app.Models.User import User


class OAuth2AuthorizationCode(BaseModel):
    """OAuth2 Authorization Code model with Laravel Passport compatibility."""
    
    __tablename__ = "oauth_authorization_codes"
    
    # Code identification - using ULID for code_id
    code_id: Mapped[str] = mapped_column(String(26), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Authorization details
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    
    # PKCE support
    code_challenge: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    code_challenge_method: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Associations
    user_id: Mapped[ULID] = mapped_column(String(26), ForeignKey("users.id"), nullable=False)
    client_id: Mapped[str] = mapped_column(String(26), ForeignKey("oauth_clients.client_id"), nullable=False)
    
    # Code status
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Relationships
    client = relationship("OAuth2Client", back_populates="authorization_codes")
    user = relationship("User", back_populates="oauth_authorization_codes")
    
    def __repr__(self) -> str:
        return f"<OAuth2AuthorizationCode(code_id='{self.code_id}', user_id={self.user_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if authorization code is expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if authorization code is valid (not expired and not revoked)."""
        return not self.is_expired and not self.is_revoked
    
    @property
    def expires_in(self) -> int:
        """Get seconds until code expires."""
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return int(delta.total_seconds())
    
    @property
    def uses_pkce(self) -> bool:
        """Check if authorization code uses PKCE."""
        return self.code_challenge is not None
    
    @property
    def pkce_method(self) -> str:
        """Get PKCE method, defaulting to 'plain' if not specified."""
        return self.code_challenge_method or "plain"
    
    def get_scopes(self) -> List[str]:
        """Get list of scopes."""
        if not self.scopes.strip():
            return []
        return [scope.strip() for scope in self.scopes.split(" ") if scope.strip()]
    
    def set_scopes(self, scopes: List[str]) -> None:
        """Set scopes from list."""
        self.scopes = " ".join(scopes)
    
    def has_scope(self, scope: str) -> bool:
        """Check if code has specific scope."""
        code_scopes = self.get_scopes()
        return scope in code_scopes or "*" in code_scopes
    
    def verify_pkce_challenge(self, code_verifier: str) -> bool:
        """Verify PKCE code challenge."""
        if not self.uses_pkce or not self.code_challenge:
            return True  # No PKCE required
        
        if self.pkce_method == "plain":
            return code_verifier == self.code_challenge
        
        elif self.pkce_method == "S256":
            import hashlib
            import base64
            
            # Create SHA256 hash of verifier
            hash_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
            # Base64 URL encode without padding
            computed_challenge = base64.urlsafe_b64encode(hash_bytes).decode('utf-8').rstrip('=')
            
            return computed_challenge == self.code_challenge
        
        return False
    
    def can_be_exchanged(
        self, 
        client_id: str, 
        redirect_uri: str, 
        code_verifier: Optional[str] = None
    ) -> bool:
        """Check if authorization code can be exchanged for tokens."""
        # Check if code is valid
        if not self.is_valid:
            return False
        
        # Check client ID matches
        if self.client_id != client_id:
            return False
        
        # Check redirect URI matches
        if self.redirect_uri != redirect_uri:
            return False
        
        # Verify PKCE if required
        if self.uses_pkce and not self.verify_pkce_challenge(code_verifier or ""):
            return False
        
        return True
    
    def revoke(self) -> None:
        """Revoke the authorization code."""
        self.is_revoked = True
    
    def extend_expiration(self, minutes: int) -> None:
        """Extend code expiration (rarely needed)."""
        self.expires_at = self.expires_at + timedelta(minutes=minutes)
    
    @classmethod
    def create_with_pkce(
        cls,
        user_id: int,
        client_id: str,
        redirect_uri: str,
        scopes: List[str],
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        expires_minutes: int = 10
    ) -> OAuth2AuthorizationCode:
        """Create authorization code with PKCE support."""
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
        
        code = cls(
            user_id=user_id,
            client_id=client_id,
            redirect_uri=redirect_uri,
            expires_at=expires_at,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method
        )
        code.set_scopes(scopes)
        return code
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert authorization code to dictionary."""
        return {
            "id": self.id,
            "code_id": self.code_id,
            "redirect_uri": self.redirect_uri,
            "scopes": self.get_scopes(),
            "user_id": self.user_id,
            "client_id": self.client_id,
            "uses_pkce": self.uses_pkce,
            "pkce_method": self.pkce_method,
            "is_revoked": self.is_revoked,
            "is_expired": self.is_expired,
            "is_valid": self.is_valid,
            "expires_at": self.expires_at.isoformat(),
            "expires_in": self.expires_in,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }