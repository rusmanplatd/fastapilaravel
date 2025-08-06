"""OAuth2 Scopes Model - Laravel Passport Style

This module defines the OAuth2 scopes model for managing API scopes
similar to Laravel Passport's oauth_scopes table.
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, func
from sqlalchemy.orm import Mapped
from app.Models.BaseModel import BaseModel


class OAuthScope(BaseModel):
    """OAuth2 Scope model for managing API scopes."""
    
    __tablename__ = "oauth_scopes"
    
    # Scope identification
    scope_id: Mapped[str] = Column(String(100), unique=True, index=True, nullable=False)
    
    # Scope details
    name: Mapped[str] = Column(String(191), nullable=False)
    description: Mapped[str] = Column(Text, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = Column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    
    def __str__(self) -> str:
        """String representation of the scope."""
        return f"OAuthScope(scope_id={self.scope_id}, name={self.name})"
    
    def __repr__(self) -> str:
        """Developer representation of the scope."""
        return (
            f"<OAuthScope(id={self.id}, scope_id='{self.scope_id}', "
            f"name='{self.name}')>"
        )