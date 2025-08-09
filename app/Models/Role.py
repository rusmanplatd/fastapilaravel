from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING, Set, Union
from sqlalchemy import String, Text, Boolean, Integer, DateTime, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timezone, timedelta
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions
import json

if TYPE_CHECKING:
    from app.Models.Permission import Permission
    from app.Models.User import User


class Role(BaseModel, LogsActivityMixin):
    __tablename__ = "roles"
    
    # Enhanced table indexes for performance
    __table_args__ = (
        Index('idx_roles_name', 'name'),
        Index('idx_roles_slug', 'slug'),
        Index('idx_roles_active_default', 'is_active', 'is_default'),
        Index('idx_roles_guard_active', 'guard_name', 'is_active'),
        Index('idx_roles_hierarchy', 'parent_id', 'hierarchy_level'),
        Index('idx_roles_created_at', 'created_at'),
    )
    
    # Core fields
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    guard_name: Mapped[str] = mapped_column(String(50), default="api", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Hierarchy fields
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Parent role for hierarchy")
    hierarchy_level: Mapped[int] = mapped_column(default=0, comment="Level in role hierarchy (0=root)")
    hierarchy_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Full hierarchy path")
    
    # Metadata and configuration
    role_type: Mapped[str] = mapped_column(String(50), default="standard", comment="Role type (standard, system, temporary)")
    priority: Mapped[int] = mapped_column(default=1, comment="Role priority (higher = more important)")
    max_users: Mapped[Optional[int]] = mapped_column(nullable=True, comment="Maximum users allowed for this role")
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, comment="Role expiration date")
    
    # Advanced settings
    is_system: Mapped[bool] = mapped_column(default=False, comment="System role (cannot be deleted)")
    is_assignable: Mapped[bool] = mapped_column(default=True, comment="Can be assigned to users")
    auto_assign: Mapped[bool] = mapped_column(default=False, comment="Auto-assign to new users")
    requires_approval: Mapped[bool] = mapped_column(default=False, comment="Requires approval to assign")
    
    # Permission inheritance
    inherit_permissions: Mapped[bool] = mapped_column(default=True, comment="Inherit parent permissions")
    permission_overrides: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="JSON permission overrides")
    
    # Audit fields
    created_by_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    updated_by_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # JSON fields for flexible data
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='{}', comment="Additional role metadata")
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='{}', comment="Role-specific settings")
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='{}', comment="Assignment conditions")
    
    # Relationships
    permissions: Mapped[List["Permission"]] = relationship(
        "Permission", 
        secondary="role_permissions",
        back_populates="roles",
        lazy="select"
    )
    
    users: Mapped[List["User"]] = relationship(
        "User", 
        secondary="user_roles",
        back_populates="roles",
        lazy="select"
    )
    
    # Self-referential hierarchy relationships
    parent: Mapped[Optional["Role"]] = relationship(
        "Role",
        remote_side="Role.id",
        back_populates="children",
        foreign_keys=[parent_id]
    )
    
    children: Mapped[List["Role"]] = relationship(
        "Role",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    
    # Audit relationships
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="select"
    )
    
    updated_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[updated_by_id],
        lazy="select"
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
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for Role model."""
        return LogOptions(
            log_name="roles",
            log_attributes=["name", "slug", "is_active", "is_default", "parent_id"],
            description_for_event={
                "created": "Role was created",
                "updated": "Role was updated",
                "deleted": "Role was deleted"
            }
        )
    
    # Enhanced Role Methods
    
    def is_expired(self) -> bool:
        """Check if role has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def can_be_assigned_to_user(self, user: Optional["User"] = None) -> bool:
        """Check if role can be assigned to a user."""
        if not self.is_assignable or not self.is_active or self.is_expired():
            return False
        
        # Check max users limit
        if self.max_users is not None:
            current_user_count = len(self.users)
            if current_user_count >= self.max_users:
                return False
        
        return True
    
    def get_effective_permissions(self) -> Set["Permission"]:
        """Get all effective permissions including inherited ones."""
        effective_permissions = set(self.permissions)
        
        if self.inherit_permissions and self.parent:
            parent_permissions = self.parent.get_effective_permissions()
            effective_permissions.update(parent_permissions)
        
        return effective_permissions
    
    def get_hierarchy_path(self) -> List["Role"]:
        """Get the full hierarchy path from root to this role."""
        path = []
        current_role = self
        
        while current_role:
            path.insert(0, current_role)
            current_role = current_role.parent
        
        return path
    
    def get_hierarchy_string(self) -> str:
        """Get hierarchy as a string path."""
        path = self.get_hierarchy_path()
        return " > ".join([role.name for role in path])
    
    def get_descendants(self) -> List["Role"]:
        """Get all descendant roles."""
        descendants = []
        
        def collect_descendants(role: "Role") -> None:
            for child in role.children:
                descendants.append(child)
                collect_descendants(child)
        
        collect_descendants(self)
        return descendants
    
    def get_ancestors(self) -> List["Role"]:
        """Get all ancestor roles."""
        ancestors = []
        current = self.parent
        
        while current:
            ancestors.append(current)
            current = current.parent
        
        return ancestors
    
    def is_ancestor_of(self, role: "Role") -> bool:
        """Check if this role is an ancestor of another role."""
        return self in role.get_ancestors()
    
    def is_descendant_of(self, role: "Role") -> bool:
        """Check if this role is a descendant of another role."""
        return role in self.get_ancestors()
    
    def update_hierarchy_path(self) -> None:
        """Update the hierarchy path string."""
        path_roles = self.get_hierarchy_path()
        self.hierarchy_path = "/".join([str(role.id) for role in path_roles])
        self.hierarchy_level = len(path_roles) - 1
    
    def set_parent(self, parent: Optional["Role"]) -> bool:
        """Set parent role with validation."""
        if parent and parent.is_descendant_of(self):
            return False  # Would create circular reference
        
        self.parent = parent
        self.parent_id = parent.id if parent else None
        self.update_hierarchy_path()
        return True
    
    def get_permission_overrides(self) -> Dict[str, Any]:
        """Get permission overrides as dict."""
        if not self.permission_overrides:
            return {}
        try:
            return json.loads(self.permission_overrides)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_permission_overrides(self, overrides: Dict[str, Any]) -> None:
        """Set permission overrides."""
        self.permission_overrides = json.dumps(overrides) if overrides else None
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata as dict."""
        if not self.metadata:
            return {}
        try:
            return json.loads(self.metadata)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_metadata(self, metadata: Dict[str, Any]) -> None:
        """Set metadata."""
        self.metadata = json.dumps(metadata) if metadata else '{}'
    
    def get_settings(self) -> Dict[str, Any]:
        """Get settings as dict."""
        if not self.settings:
            return {}
        try:
            return json.loads(self.settings)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_settings(self, settings: Dict[str, Any]) -> None:
        """Set settings."""
        self.settings = json.dumps(settings) if settings else '{}'
    
    def get_conditions(self) -> Dict[str, Any]:
        """Get assignment conditions as dict."""
        if not self.conditions:
            return {}
        try:
            return json.loads(self.conditions)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_conditions(self, conditions: Dict[str, Any]) -> None:
        """Set assignment conditions."""
        self.conditions = json.dumps(conditions) if conditions else '{}'
    
    def check_assignment_conditions(self, user: "User") -> bool:
        """Check if user meets assignment conditions."""
        conditions = self.get_conditions()
        if not conditions:
            return True
        
        # Check department condition
        if 'departments' in conditions:
            user_departments = [dept.name for dept in user.get_current_departments()]
            if not any(dept in user_departments for dept in conditions['departments']):
                return False
        
        # Check organization condition
        if 'organizations' in conditions:
            user_orgs = [org.name for org in user.get_current_organizations()]
            if not any(org in user_orgs for org in conditions['organizations']):
                return False
        
        # Check tenure condition (days since user creation)
        if 'min_tenure_days' in conditions:
            user_tenure = (datetime.now(timezone.utc) - user.created_at).days
            if user_tenure < conditions['min_tenure_days']:
                return False
        
        return True
    
    @hybrid_property
    def user_count(self) -> int:
        """Get current number of users with this role."""
        return len(self.users)
    
    @hybrid_property
    def permission_count(self) -> int:
        """Get number of permissions assigned to this role."""
        return len(self.permissions)
    
    @hybrid_property
    def effective_permission_count(self) -> int:
        """Get number of effective permissions (including inherited)."""
        return len(self.get_effective_permissions())
    
    def to_dict_safe(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "guard_name": self.guard_name,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "role_type": self.role_type,
            "priority": self.priority,
            "hierarchy_level": self.hierarchy_level,
            "hierarchy_path": self.get_hierarchy_string(),
            "parent_id": self.parent_id,
            "is_system": self.is_system,
            "is_assignable": self.is_assignable,
            "user_count": self.user_count,
            "permission_count": self.permission_count,
            "effective_permission_count": self.effective_permission_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired(),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def to_dict_detailed(self) -> Dict[str, Any]:
        """Extended dictionary with full details."""
        base_dict = self.to_dict_safe()
        base_dict.update({
            "metadata": self.get_metadata(),
            "settings": self.get_settings(),
            "conditions": self.get_conditions(),
            "ancestors": [role.to_dict_safe() for role in self.get_ancestors()],
            "children": [role.to_dict_safe() for role in self.children],
            "permissions": [perm.to_dict_safe() for perm in self.permissions],
            "effective_permissions": [perm.to_dict_safe() for perm in self.get_effective_permissions()]
        })
        return base_dict


__all__ = ["Role"]