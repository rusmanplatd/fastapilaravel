"""OAuth2 Scopes Model - Laravel Passport Style

This module defines the OAuth2 scopes model for managing API scopes
similar to Laravel Passport's oauth_scopes table.
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.Models.BaseModel import BaseModel


class OAuthScope(BaseModel):
    """OAuth2 Scope model for managing API scopes."""
    
    __tablename__ = "oauth_scopes"
    
    # Scope identification - using ULID for scope_id
    scope_id: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    
    # Scope details
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    
    def __str__(self) -> str:
        """String representation of the scope."""
        return f"OAuthScope(scope_id={self.scope_id}, name={self.name})"
    
    def __repr__(self) -> str:
        """Developer representation of the scope."""
        return (
            f"<OAuthScope(id={self.id}, scope_id='{self.scope_id}', "
            f"name='{self.name}')>"
        )