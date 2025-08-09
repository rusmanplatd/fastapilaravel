"""OAuth2 Client Model - Laravel Passport Style

This module defines the OAuth2 client model for managing API clients
similar to Laravel Passport's oauth_clients table.
"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, relationship, mapped_column
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from database.migrations.create_oauth_access_tokens_table import OAuthAccessToken
    from database.migrations.create_oauth_refresh_tokens_table import OAuthRefreshToken
    from database.migrations.create_oauth_auth_codes_table import OAuthAuthCode


class OAuthClient(BaseModel):
    """OAuth2 Client model for managing API clients."""
    
    __tablename__ = "oauth_clients"
    
    # Client identification - using ULID for client_id
    client_id: Mapped[str] = mapped_column(String(26), unique=True, index=True, nullable=False)  # type: ignore[arg-type]
    client_secret: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # type: ignore[arg-type]
    
    # Client details
    name: Mapped[str] = mapped_column(String(191), nullable=False)  # type: ignore[arg-type]
    redirect: Mapped[str] = mapped_column(Text, nullable=False)  # type: ignore[arg-type]
    
    # Client configuration
    personal_access_client: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # type: ignore[arg-type]
    password_client: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # type: ignore[arg-type]
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # type: ignore[arg-type]
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)  # type: ignore[arg-type]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False  # type: ignore[arg-type]
    )
    
    # Relationships
    access_tokens: Mapped[List[OAuthAccessToken]] = relationship(
        "OAuthAccessToken", back_populates="client", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List[OAuthRefreshToken]] = relationship(
        "OAuthRefreshToken", back_populates="client", cascade="all, delete-orphan"
    )
    auth_codes: Mapped[List[OAuthAuthCode]] = relationship(
        "OAuthAuthCode", back_populates="client", cascade="all, delete-orphan"
    )
    
    def __str__(self) -> str:
        """String representation of the client."""
        return f"OAuthClient(name={self.name}, client_id={self.client_id})"
    
    def __repr__(self) -> str:
        """Developer representation of the client."""
        return (
            f"<OAuthClient(id={self.id}, name='{self.name}', "
            f"client_id='{self.client_id}', revoked={self.revoked})>"
        )
    
    def is_confidential(self) -> bool:
        """Check if client is confidential (has client secret)."""
        return self.client_secret is not None and self.client_secret != ""
    
    def is_public(self) -> bool:
        """Check if client is public (no client secret)."""
        return not self.is_confidential()
    
    def is_personal_access_client(self) -> bool:
        """Check if client is a personal access client."""
        return self.personal_access_client
    
    def is_password_client(self) -> bool:
        """Check if client supports password grant."""
        return self.password_client
    
    def is_revoked(self) -> bool:
        """Check if client is revoked."""
        return self.revoked
    
    def revoke(self) -> None:
        """Revoke the client."""
        self.revoked = True
    
    def restore(self) -> None:
        """Restore the client."""
        self.revoked = False