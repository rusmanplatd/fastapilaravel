from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import ForeignKey, Boolean, String, DateTime, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.Tenant import Tenant
    from app.Models.User import User


class TenantUser(BaseModel, LogsActivityMixin):
    """
    Junction model for tenant-user relationships.
    Manages user access and roles within specific tenants.
    """
    __tablename__ = "tenant_users"
    
    # Relationships
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Role and permissions within the tenant
    role: Mapped[str] = mapped_column(default="member", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_owner: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Access control
    can_manage_users: Mapped[bool] = mapped_column(default=False, nullable=False)
    can_manage_organizations: Mapped[bool] = mapped_column(default=False, nullable=False)
    can_manage_billing: Mapped[bool] = mapped_column(default=False, nullable=False)
    can_manage_settings: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Invitation and lifecycle
    invited_by_user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    invited_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    joined_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Status and suspension
    suspended_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    suspension_reason: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Custom permissions and settings
    permissions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="tenant_users"
    )
    
    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="tenant_users"
    )
    
    invited_by: Mapped[Optional[User]] = relationship(
        "User",
        foreign_keys=[invited_by_user_id]
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for TenantUser model."""
        return LogOptions(
            log_name="tenant_users",
            log_attributes=[
                "tenant_id", "user_id", "role", "is_active", "is_owner", 
                "is_admin", "suspended_at"
            ],
            description_for_event={
                "created": "User was added to tenant",
                "updated": "Tenant user relationship was updated",
                "deleted": "User was removed from tenant"
            }
        )
    
    def is_suspended(self) -> bool:
        """Check if user is suspended in this tenant."""
        return self.suspended_at is not None
    
    def can_access_tenant(self) -> bool:
        """Check if user can access the tenant."""
        return self.is_active and not self.is_suspended()
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        # Owner and admin have all permissions
        if self.is_owner or self.is_admin:
            return True
        
        # Check built-in permissions
        if permission == "manage_users" and self.can_manage_users:
            return True
        if permission == "manage_organizations" and self.can_manage_organizations:
            return True
        if permission == "manage_billing" and self.can_manage_billing:
            return True
        if permission == "manage_settings" and self.can_manage_settings:
            return True
        
        # Check custom permissions
        if self.permissions:
            return self.permissions.get(permission, False)
        
        return False
    
    def grant_permission(self, permission: str) -> None:
        """Grant a specific permission to the user."""
        if not self.permissions:
            self.permissions = {}
        self.permissions[permission] = True
    
    def revoke_permission(self, permission: str) -> None:
        """Revoke a specific permission from the user."""
        if self.permissions and permission in self.permissions:
            del self.permissions[permission]
    
    def get_role_level(self) -> int:
        """Get numeric role level for hierarchy comparison."""
        role_levels = {
            "owner": 100,
            "admin": 90,
            "manager": 70,
            "supervisor": 50,
            "member": 30,
            "viewer": 10,
            "guest": 1
        }
        return role_levels.get(self.role, 0)
    
    def can_manage_user(self, other_tenant_user: TenantUser) -> bool:
        """Check if this user can manage another user in the tenant."""
        # Owner can manage everyone except other owners
        if self.is_owner:
            return not other_tenant_user.is_owner or self.user_id == other_tenant_user.user_id
        
        # Admin can manage non-owners and non-admins
        if self.is_admin:
            return not other_tenant_user.is_owner and not other_tenant_user.is_admin
        
        # Users with manage_users permission can manage lower-level users
        if self.can_manage_users:
            return self.get_role_level() > other_tenant_user.get_role_level()
        
        return False
    
    def suspend(self, reason: str) -> None:
        """Suspend the user in this tenant."""
        self.suspended_at = datetime.utcnow()
        self.suspension_reason = reason
        self.is_active = False
    
    def unsuspend(self) -> None:
        """Unsuspend the user in this tenant."""
        self.suspended_at = None
        self.suspension_reason = None
        self.is_active = True
    
    def record_login(self) -> None:
        """Record user login timestamp."""
        self.last_login_at = datetime.utcnow()
    
    def accept_invitation(self) -> None:
        """Mark invitation as accepted."""
        self.joined_at = datetime.utcnow()
        if not self.is_active:
            self.is_active = True
    
    def to_dict_with_user(self) -> Dict[str, Any]:
        """Return tenant user data with user information."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else None,
            "user_email": self.user.email if self.user else None,
            "role": self.role,
            "is_active": self.is_active,
            "is_owner": self.is_owner,
            "is_admin": self.is_admin,
            "can_manage_users": self.can_manage_users,
            "can_manage_organizations": self.can_manage_organizations,
            "can_manage_billing": self.can_manage_billing,
            "can_manage_settings": self.can_manage_settings,
            "invited_by_user_id": self.invited_by_user_id,
            "invited_by_name": self.invited_by.name if self.invited_by else None,
            "invited_at": self.invited_at,
            "joined_at": self.joined_at,
            "last_login_at": self.last_login_at,
            "suspended_at": self.suspended_at,
            "suspension_reason": self.suspension_reason,
            "is_suspended": self.is_suspended(),
            "can_access_tenant": self.can_access_tenant(),
            "role_level": self.get_role_level(),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }