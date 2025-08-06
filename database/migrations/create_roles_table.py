from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship
from app.Models import BaseModel
from database.migrations.create_role_permission_table import role_permission_table
from database.migrations.create_user_role_table import user_role_table
from typing import List


class Role(BaseModel):
    __tablename__ = "roles"
    
    name = Column(String(255), unique=True, index=True, nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    guard_name = Column(String(255), default="api", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    permissions = relationship("Permission", secondary=role_permission_table, back_populates="roles")
    users = relationship("User", secondary=user_role_table, back_populates="roles")
    
    # Permission Methods
    def give_permission_to(self, permission) -> None:
        """Give permission to role"""
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def revoke_permission_to(self, permission) -> None:
        """Revoke permission from role"""
        if permission in self.permissions:
            self.permissions.remove(permission)
    
    def sync_permissions(self, permissions: List) -> None:
        """Sync role permissions"""
        self.permissions.clear()
        for permission in permissions:
            self.permissions.append(permission)
    
    def has_permission_to(self, permission_name: str) -> bool:
        """Check if role has permission"""
        return any(perm.name == permission_name or perm.slug == permission_name for perm in self.permissions)
    
    def get_permission_names(self) -> List[str]:
        """Get list of permission names for this role"""
        return [perm.name for perm in self.permissions]
    
    def to_dict_safe(self):
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