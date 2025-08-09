from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel

if TYPE_CHECKING:
    from app.Models.Role import Role
    from app.Models.User import User


class Permission(BaseModel):
    __tablename__ = "permissions"
    
    name: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    guard_name: Mapped[str] = mapped_column(default="api", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role", 
        secondary="role_permissions",
        back_populates="permissions"
    )
    
    users: Mapped[List["User"]] = relationship(
        "User", 
        secondary="user_permissions",
        back_populates="permissions"
    )
    
    def to_dict_safe(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "guard_name": self.guard_name,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


__all__ = ["Permission"]