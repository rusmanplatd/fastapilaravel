"""OAuth2 Scope Model - Laravel Passport Style

This module defines the OAuth2 Scope model with strict typing,
similar to Laravel Passport's scope model.
"""

from __future__ import annotations

from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.Models.BaseModel import BaseModel
from app.Utils.ULIDUtils import ULID


class OAuth2Scope(BaseModel):
    """OAuth2 Scope model with Laravel Passport compatibility."""
    
    __tablename__ = "oauth_scopes"
    
    # Scope identification - using ULID for scope_id
    scope_id: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    
    # Scope configuration
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_personal_access_client: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_password_client: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_client_credentials: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_authorization_code: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Scope status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    def __repr__(self) -> str:
        return f"<OAuth2Scope(scope_id='{self.scope_id}', name='{self.name}')>"
    
    @property
    def identifier(self) -> str:
        """Get scope identifier (alias for scope_id)."""
        return self.scope_id
    
    def is_allowed_for_grant_type(self, grant_type: str) -> bool:
        """Check if scope is allowed for specific grant type."""
        grant_type_mapping = {
            "authorization_code": self.is_authorization_code,
            "client_credentials": self.is_client_credentials,
            "password": self.is_password_client,
            "personal_access": self.is_personal_access_client,
        }
        
        return grant_type_mapping.get(grant_type, False)
    
    def can_be_used_by_client_type(self, client_type: str) -> bool:
        """Check if scope can be used by specific client type."""
        if client_type == "personal_access":
            return self.is_personal_access_client
        elif client_type == "password":
            return self.is_password_client
        elif client_type == "client_credentials":
            return self.is_client_credentials
        elif client_type == "authorization_code":
            return self.is_authorization_code
        
        return False
    
    def activate(self) -> None:
        """Activate the scope."""
        self.is_active = True
    
    def deactivate(self) -> None:
        """Deactivate the scope."""
        self.is_active = False
    
    def make_default(self) -> None:
        """Make this scope a default scope."""
        self.is_default = True
    
    def remove_default(self) -> None:
        """Remove default status from scope."""
        self.is_default = False
    
    def enable_for_all_grants(self) -> None:
        """Enable scope for all grant types."""
        self.is_personal_access_client = True
        self.is_password_client = True
        self.is_client_credentials = True
        self.is_authorization_code = True
    
    def disable_for_all_grants(self) -> None:
        """Disable scope for all grant types."""
        self.is_personal_access_client = False
        self.is_password_client = False
        self.is_client_credentials = False
        self.is_authorization_code = False
    
    @classmethod
    def create_default_scopes(cls) -> List[OAuth2Scope]:
        """Create default OAuth2 scopes."""
        default_scopes = [
            {
                "scope_id": "read",
                "name": "Read Access",
                "description": "Read access to basic resources",
                "is_default": True,
            },
            {
                "scope_id": "write", 
                "name": "Write Access",
                "description": "Write access to resources",
                "is_default": False,
            },
            {
                "scope_id": "admin",
                "name": "Admin Access", 
                "description": "Full administrative access",
                "is_default": False,
                "is_personal_access_client": False,  # Restrict admin scope
                "is_password_client": False,
            },
            {
                "scope_id": "users",
                "name": "User Management",
                "description": "Manage users and user data",
                "is_default": False,
            },
            {
                "scope_id": "profile",
                "name": "Profile Access",
                "description": "Access to user profile information",
                "is_default": False,
            },
            {
                "scope_id": "email",
                "name": "Email Access",
                "description": "Access to user email information",
                "is_default": False,
            },
            {
                "scope_id": "openid",
                "name": "OpenID Connect",
                "description": "OpenID Connect access for authentication",
                "is_default": False,
            },
            {
                "scope_id": "offline_access",
                "name": "Offline Access",
                "description": "Access to refresh tokens for offline access",
                "is_default": False,
            },
        ]
        
        scopes = []
        for scope_data in default_scopes:
            scope = cls(**scope_data)
            scopes.append(scope)
        
        return scopes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scope to dictionary."""
        return {
            "id": self.id,
            "scope_id": self.scope_id,
            "name": self.name,
            "description": self.description,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "grant_types": {
                "personal_access": self.is_personal_access_client,
                "password": self.is_password_client,
                "client_credentials": self.is_client_credentials,
                "authorization_code": self.is_authorization_code,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def to_oauth_scope(self) -> Dict[str, Any]:
        """Convert to OAuth2 scope format for authorization server metadata."""
        return {
            "scope": self.scope_id,
            "description": self.description,
        }