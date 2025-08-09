from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from app.Models.Permission import Permission
    from app.Models.User import User


class Role(BaseModel):
    __tablename__ = "roles"
    
    name: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    guard_name: Mapped[str] = mapped_column(default="api", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission", 
        secondary="role_permissions",
        back_populates="roles"
    )
    
    users: Mapped[List["User"]] = relationship(
        "User", 
        secondary="user_roles",
        back_populates="roles"
    )
    
    def give_permission_to(self, permission: "Permission") -> None:
        """Give a permission to this role."""
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def revoke_permission_from(self, permission: "Permission") -> None:
        """Revoke a permission from this role."""
        if permission in self.permissions:
            self.permissions.remove(permission)
    
    def revoke_permission_to(self, permission: "Permission") -> None:
        """Alias for revoke_permission_from to match service expectations."""
        self.revoke_permission_from(permission)
    
    def has_permission(self, permission: "Permission") -> bool:
        """Check if role has a specific permission."""
        return permission in self.permissions
    
    def sync_permissions(self, permissions: List["Permission"]) -> None:
        """Sync the role's permissions to match the given list."""
        self.permissions.clear()
        self.permissions.extend(permissions)
    
    def to_dict_safe(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "guard_name": self.guard_name,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


__all__ = ["Role"]