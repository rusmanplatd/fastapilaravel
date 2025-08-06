from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship, Mapped
from app.Models import BaseModel
from database.migrations.create_role_permission_table import role_permission_table
from database.migrations.create_user_permission_table import user_permission_table

if TYPE_CHECKING:
    from database.migrations.create_roles_table import Role
    from database.migrations.create_users_table import User


class Permission(BaseModel):
    __tablename__ = "permissions"
    
    name: Mapped[str] = Column(String(255), unique=True, index=True, nullable=False)
    slug: Mapped[str] = Column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)
    guard_name: Mapped[str] = Column(String(255), default="api", nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    roles: Mapped[List[Role]] = relationship("Role", secondary=role_permission_table, back_populates="permissions")
    users: Mapped[List[User]] = relationship("User", secondary=user_permission_table, back_populates="direct_permissions")
    
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