from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, func, Text
from sqlalchemy.orm import relationship, Mapped
from app.Models import BaseModel
from database.migrations.create_user_role_table import user_role_table
from database.migrations.create_user_permission_table import user_permission_table

if TYPE_CHECKING:
    from database.migrations.create_roles_table import Role
    from database.migrations.create_permissions_table import Permission
    from app.Models.OAuth2AccessToken import OAuth2AccessToken
    from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode
    from app.Models.OAuth2Client import OAuth2Client


class User(BaseModel):
    __tablename__ = "users"
    
    name: Mapped[str] = Column(String(255), nullable=False)
    email: Mapped[str] = Column(String(255), unique=True, index=True, nullable=False)
    password: Mapped[str] = Column(String(255), nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True)
    is_verified: Mapped[bool] = Column(Boolean, default=False)
    email_verified_at: Mapped[Optional[datetime]] = Column(DateTime, nullable=True)
    remember_token: Mapped[Optional[str]] = Column(String(100), nullable=True)
    
    # Relationships
    roles: Mapped[List[Role]] = relationship("Role", secondary=user_role_table, back_populates="users")
    direct_permissions: Mapped[List[Permission]] = relationship("Permission", secondary=user_permission_table, back_populates="users")
    
    # OAuth2 relationships
    oauth_access_tokens: Mapped[List[OAuth2AccessToken]] = relationship(
        "OAuth2AccessToken", back_populates="user", cascade="all, delete-orphan"
    )
    oauth_authorization_codes: Mapped[List[OAuth2AuthorizationCode]] = relationship(
        "OAuth2AuthorizationCode", back_populates="user", cascade="all, delete-orphan"
    )
    oauth_clients: Mapped[List[OAuth2Client]] = relationship(
        "OAuth2Client", back_populates="user", cascade="all, delete-orphan"
    )
    
    def verify_password(self, password: str) -> bool:
        from app.Services.AuthService import AuthService
        return AuthService.verify_password(password, self.password)
    
    def is_email_verified(self) -> bool:
        return self.email_verified_at is not None
    
    # Role and Permission Methods (similar to Spatie Laravel Permission)
    
    def assign_role(self, role: Role) -> None:
        """Assign a role to the user"""
        if role not in self.roles:
            self.roles.append(role)
    
    def remove_role(self, role: Role) -> None:
        """Remove a role from the user"""
        if role in self.roles:
            self.roles.remove(role)
    
    def sync_roles(self, roles: List[Role]) -> None:
        """Sync user roles (remove all existing and add new ones)"""
        self.roles.clear()
        for role in roles:
            self.roles.append(role)
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role"""
        return any(role.name == role_name or role.slug == role_name for role in self.roles)
    
    def has_any_role(self, role_names: List[str]) -> bool:
        """Check if user has any of the specified roles"""
        return any(self.has_role(role_name) for role_name in role_names)
    
    def has_all_roles(self, role_names: List[str]) -> bool:
        """Check if user has all of the specified roles"""
        return all(self.has_role(role_name) for role_name in role_names)
    
    def give_permission_to(self, permission: Permission) -> None:
        """Give direct permission to user"""
        if permission not in self.direct_permissions:
            self.direct_permissions.append(permission)
    
    def revoke_permission_to(self, permission: Permission) -> None:
        """Revoke direct permission from user"""
        if permission in self.direct_permissions:
            self.direct_permissions.remove(permission)
    
    def sync_permissions(self, permissions: List[Permission]) -> None:
        """Sync user direct permissions"""
        self.direct_permissions.clear()
        for permission in permissions:
            self.direct_permissions.append(permission)
    
    def has_permission_to(self, permission_name: str) -> bool:
        """Check if user has permission (either direct or through roles)"""
        # Check direct permissions
        if any(perm.name == permission_name or perm.slug == permission_name for perm in self.direct_permissions):
            return True
        
        # Check permissions through roles
        for role in self.roles:
            if any(perm.name == permission_name or perm.slug == permission_name for perm in role.permissions):
                return True
        
        return False
    
    def has_any_permission(self, permission_names: List[str]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(self.has_permission_to(perm_name) for perm_name in permission_names)
    
    def has_all_permissions(self, permission_names: List[str]) -> bool:
        """Check if user has all of the specified permissions"""
        return all(self.has_permission_to(perm_name) for perm_name in permission_names)
    
    def get_all_permissions(self) -> List[Permission]:
        """Get all permissions (direct + through roles)"""
        all_permissions = list(self.direct_permissions)
        
        for role in self.roles:
            for permission in role.permissions:
                if permission not in all_permissions:
                    all_permissions.append(permission)
        
        return all_permissions
    
    def get_role_names(self) -> List[str]:
        """Get list of role names"""
        return [role.name for role in self.roles]
    
    def get_permission_names(self) -> List[str]:
        """Get list of all permission names"""
        return [perm.name for perm in self.get_all_permissions()]
    
    def can(self, permission_name: str) -> bool:
        """Alias for has_permission_to"""
        return self.has_permission_to(permission_name)
    
    def cannot(self, permission_name: str) -> bool:
        """Opposite of can"""
        return not self.has_permission_to(permission_name)
    
    def to_dict_safe(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "email_verified_at": self.email_verified_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }