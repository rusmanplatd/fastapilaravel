from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship
from app.Models import BaseModel
from database.migrations.create_role_permission_table import role_permission_table
from database.migrations.create_user_permission_table import user_permission_table


class Permission(BaseModel):
    __tablename__ = "permissions"
    
    name = Column(String(255), unique=True, index=True, nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    guard_name = Column(String(255), default="api", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    roles = relationship("Role", secondary=role_permission_table, back_populates="permissions")
    users = relationship("User", secondary=user_permission_table, back_populates="direct_permissions")
    
    def to_dict_safe(self):
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