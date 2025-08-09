from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING, Set, Union
from sqlalchemy import String, Text, Boolean, Integer, DateTime, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timezone, timedelta
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions
import json
import re

if TYPE_CHECKING:
    from app.Models.Role import Role
    from app.Models.User import User


class Permission(BaseModel, LogsActivityMixin):
    __tablename__ = "permissions"
    
    # Enhanced table indexes for performance
    __table_args__ = (
        Index('idx_permissions_name', 'name'),
        Index('idx_permissions_slug', 'slug'),
        Index('idx_permissions_category_action', 'category', 'action'),
        Index('idx_permissions_guard_active', 'guard_name', 'is_active'),
        Index('idx_permissions_resource_action', 'resource_type', 'action'),
        Index('idx_permissions_created_at', 'created_at'),
    )
    
    # Core fields
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    guard_name: Mapped[str] = mapped_column(String(50), default="api", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Permission categorization
    category: Mapped[str] = mapped_column(String(50), default="general", comment="Permission category")
    action: Mapped[str] = mapped_column(String(50), nullable=False, comment="Action (create, read, update, delete, etc.)")
    resource_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="Resource type this permission applies to")
    
    # Permission hierarchy and dependencies
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Parent permission for hierarchy")
    depends_on: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="JSON list of permission IDs this depends on")
    implies: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="JSON list of permission IDs this implies")
    
    # Permission metadata
    permission_type: Mapped[str] = mapped_column(String(50), default="standard", comment="Permission type (standard, system, wildcard)")
    priority: Mapped[int] = mapped_column(default=1, comment="Permission priority for conflict resolution")
    is_dangerous: Mapped[bool] = mapped_column(default=False, comment="Mark as dangerous permission")
    requires_mfa: Mapped[bool] = mapped_column(default=False, comment="Requires MFA to use")
    
    # Permission patterns and wildcards
    pattern: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="Pattern for wildcard permissions")
    is_wildcard: Mapped[bool] = mapped_column(default=False, comment="Is this a wildcard permission")
    
    # Audit and lifecycle
    created_by_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    updated_by_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, comment="Permission expiration date")
    
    # JSON fields for flexibility
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='{}', comment="Additional permission metadata")
    conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='{}', comment="Usage conditions")
    restrictions: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default='{}', comment="Usage restrictions")
    
    # Relationships
    roles: Mapped[List["Role"]] = relationship(
        "Role", 
        secondary="role_permissions",
        back_populates="permissions",
        lazy="select"
    )
    
    users: Mapped[List["User"]] = relationship(
        "User", 
        secondary="user_permissions",
        back_populates="permissions",
        lazy="select"
    )
    
    # Self-referential hierarchy relationships
    parent: Mapped[Optional["Permission"]] = relationship(
        "Permission",
        remote_side="Permission.id",
        back_populates="children",
        foreign_keys=[parent_id]
    )
    
    children: Mapped[List["Permission"]] = relationship(
        "Permission",
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
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for Permission model."""
        return LogOptions(
            log_name="permissions",
            log_attributes=["name", "slug", "is_active", "category", "action"],
            description_for_event={
                "created": "Permission was created",
                "updated": "Permission was updated",
                "deleted": "Permission was deleted"
            }
        )
    
    # Enhanced Permission Methods
    
    def is_expired(self) -> bool:
        """Check if permission has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def get_dependencies(self) -> List[int]:
        """Get list of permission IDs this permission depends on."""
        if not self.depends_on:
            return []
        try:
            return json.loads(self.depends_on)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_dependencies(self, permission_ids: List[int]) -> None:
        """Set permission dependencies."""
        self.depends_on = json.dumps(permission_ids) if permission_ids else None
    
    def get_implied_permissions(self) -> List[int]:
        """Get list of permission IDs this permission implies."""
        if not self.implies:
            return []
        try:
            return json.loads(self.implies)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_implied_permissions(self, permission_ids: List[int]) -> None:
        """Set permissions that this permission implies."""
        self.implies = json.dumps(permission_ids) if permission_ids else None
    
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
    
    def get_conditions(self) -> Dict[str, Any]:
        """Get usage conditions as dict."""
        if not self.conditions:
            return {}
        try:
            return json.loads(self.conditions)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_conditions(self, conditions: Dict[str, Any]) -> None:
        """Set usage conditions."""
        self.conditions = json.dumps(conditions) if conditions else '{}'
    
    def get_restrictions(self) -> Dict[str, Any]:
        """Get usage restrictions as dict."""
        if not self.restrictions:
            return {}
        try:
            return json.loads(self.restrictions)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def set_restrictions(self, restrictions: Dict[str, Any]) -> None:
        """Set usage restrictions."""
        self.restrictions = json.dumps(restrictions) if restrictions else '{}'
    
    def matches_pattern(self, permission_name: str) -> bool:
        """Check if a permission name matches this permission's pattern."""
        if not self.is_wildcard or not self.pattern:
            return self.name == permission_name
        
        # Convert wildcard pattern to regex
        pattern = self.pattern.replace('*', '.*').replace('?', '.')
        return bool(re.match(f'^{pattern}$', permission_name))
    
    def can_be_granted_to_user(self, user: "User") -> bool:
        """Check if permission can be granted to a specific user."""
        if not self.is_active or self.is_expired():
            return False
        
        # Check conditions
        conditions = self.get_conditions()
        if conditions:
            # Check time-based conditions
            if 'time_restrictions' in conditions:
                current_hour = datetime.now().hour
                time_restrictions = conditions['time_restrictions']
                if 'allowed_hours' in time_restrictions:
                    if current_hour not in time_restrictions['allowed_hours']:
                        return False
            
            # Check location-based conditions
            if 'ip_restrictions' in conditions:
                # This would need IP address from context
                pass
        
        return True
    
    def get_hierarchy_path(self) -> List["Permission"]:
        """Get the full hierarchy path from root to this permission."""
        path = []
        current_perm = self
        
        while current_perm:
            path.insert(0, current_perm)
            current_perm = current_perm.parent
        
        return path
    
    def get_descendants(self) -> List["Permission"]:
        """Get all descendant permissions."""
        descendants = []
        
        def collect_descendants(perm: "Permission") -> None:
            for child in perm.children:
                descendants.append(child)
                collect_descendants(child)
        
        collect_descendants(self)
        return descendants
    
    def get_ancestors(self) -> List["Permission"]:
        """Get all ancestor permissions."""
        ancestors = []
        current = self.parent
        
        while current:
            ancestors.append(current)
            current = current.parent
        
        return ancestors
    
    def is_ancestor_of(self, permission: "Permission") -> bool:
        """Check if this permission is an ancestor of another permission."""
        return self in permission.get_ancestors()
    
    def is_descendant_of(self, permission: "Permission") -> bool:
        """Check if this permission is a descendant of another permission."""
        return permission in self.get_ancestors()
    
    def check_usage_restrictions(self, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if permission usage meets restrictions."""
        restrictions = self.get_restrictions()
        if not restrictions:
            return True
        
        context = context or {}
        
        # Check rate limiting
        if 'rate_limit' in restrictions:
            rate_limit = restrictions['rate_limit']
            # This would need to be implemented with a cache/database check
            # For now, just return True
            pass
        
        # Check concurrent usage
        if 'max_concurrent_users' in restrictions:
            # This would need to track active sessions
            pass
        
        return True
    
    @hybrid_property
    def full_name(self) -> str:
        """Get full permission name including category."""
        return f"{self.category}.{self.action}" if self.category != 'general' else self.name
    
    @hybrid_property
    def role_count(self) -> int:
        """Get number of roles that have this permission."""
        return len(self.roles)
    
    @hybrid_property
    def user_count(self) -> int:
        """Get number of users that have this permission directly."""
        return len(self.users)
    
    @classmethod
    def parse_permission_name(cls, permission_name: str) -> Dict[str, str]:
        """Parse a permission name into components."""
        parts = permission_name.split('.')
        if len(parts) >= 2:
            return {
                'category': parts[0],
                'action': parts[1],
                'resource': parts[2] if len(parts) > 2 else None
            }
        return {
            'category': 'general',
            'action': permission_name,
            'resource': None
        }
    
    @classmethod
    def create_from_name(cls, permission_name: str, **kwargs) -> "Permission":
        """Create a permission from a name, auto-parsing components."""
        components = cls.parse_permission_name(permission_name)
        
        return cls(
            name=permission_name,
            slug=permission_name.lower().replace('.', '-').replace('_', '-'),
            category=components['category'],
            action=components['action'],
            resource_type=components['resource'],
            **kwargs
        )
    
    def to_dict_safe(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "guard_name": self.guard_name,
            "is_active": self.is_active,
            "category": self.category,
            "action": self.action,
            "resource_type": self.resource_type,
            "permission_type": self.permission_type,
            "priority": self.priority,
            "is_dangerous": self.is_dangerous,
            "requires_mfa": self.requires_mfa,
            "is_wildcard": self.is_wildcard,
            "pattern": self.pattern,
            "parent_id": self.parent_id,
            "role_count": self.role_count,
            "user_count": self.user_count,
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
            "conditions": self.get_conditions(),
            "restrictions": self.get_restrictions(),
            "dependencies": self.get_dependencies(),
            "implied_permissions": self.get_implied_permissions(),
            "ancestors": [perm.to_dict_safe() for perm in self.get_ancestors()],
            "children": [perm.to_dict_safe() for perm in self.children],
            "roles": [role.to_dict_safe() for role in self.roles],
            "users": [user.to_dict_safe() for user in self.users]
        })
        return base_dict


__all__ = ["Permission"]