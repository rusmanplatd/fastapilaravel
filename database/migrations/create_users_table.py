from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions
from app.Traits.Notifiable import NotifiableMixin
from database.migrations.create_user_role_table import user_role_table
from database.migrations.create_user_permission_table import user_permission_table

if TYPE_CHECKING:
    from database.migrations.create_roles_table import Role
    from database.migrations.create_permissions_table import Permission
    from app.Models.OAuth2AccessToken import OAuth2AccessToken
    from app.Models.OAuth2AuthorizationCode import OAuth2AuthorizationCode
    from app.Models.OAuth2Client import OAuth2Client
    from database.migrations.create_user_mfa_settings_table import UserMFASettings
    from database.migrations.create_mfa_codes_table import MFACode
    from database.migrations.create_webauthn_credentials_table import WebAuthnCredential
    from database.migrations.create_mfa_sessions_table import MFASession
    from database.migrations.create_mfa_attempts_table import MFAAttempt
    from database.migrations.create_mfa_audit_log_table import MFAAuditLog


class User(BaseModel, LogsActivityMixin, NotifiableMixin):
    __tablename__ = "users"
    
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    remember_token: Mapped[Optional[str]] = mapped_column(nullable=True)
    
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
    
    # MFA relationships
    mfa_settings: Mapped[Optional[UserMFASettings]] = relationship(
        "UserMFASettings", back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    mfa_codes: Mapped[List[MFACode]] = relationship(
        "MFACode", back_populates="user", cascade="all, delete-orphan"
    )
    webauthn_credentials: Mapped[List[WebAuthnCredential]] = relationship(
        "WebAuthnCredential", back_populates="user", cascade="all, delete-orphan"
    )
    mfa_sessions: Mapped[List[MFASession]] = relationship(
        "MFASession", back_populates="user", cascade="all, delete-orphan"
    )
    mfa_attempts: Mapped[List[MFAAttempt]] = relationship(
        "MFAAttempt", back_populates="user", cascade="all, delete-orphan"
    )
    mfa_audit_logs: Mapped[List[MFAAuditLog]] = relationship(
        "MFAAuditLog", foreign_keys="[MFAAuditLog.user_id]", back_populates="user", cascade="all, delete-orphan"
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for User model."""
        return LogOptions(
            log_name="users",
            log_attributes=["name", "email", "is_active", "is_verified"],
            description_for_event={
                "created": "User account was created",
                "updated": "User account was updated", 
                "deleted": "User account was deleted"
            }
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
    
    # MFA Methods
    
    def has_mfa_enabled(self) -> bool:
        """Check if user has any MFA method enabled"""
        if not self.mfa_settings:
            return False
        return (
            self.mfa_settings.totp_enabled or 
            self.mfa_settings.webauthn_enabled or 
            self.mfa_settings.sms_enabled
        )
    
    def is_mfa_required(self) -> bool:
        """Check if MFA is required for this user"""
        if not self.mfa_settings:
            return False
        return self.mfa_settings.is_required
    
    def get_enabled_mfa_methods(self) -> List[str]:
        """Get list of enabled MFA methods"""
        if not self.mfa_settings:
            return []
        
        methods = []
        if self.mfa_settings.totp_enabled:
            methods.append("totp")
        if self.mfa_settings.webauthn_enabled:
            methods.append("webauthn")
        if self.mfa_settings.sms_enabled:
            methods.append("sms")
        
        return methods
    
    def has_webauthn_credentials(self) -> bool:
        """Check if user has any WebAuthn credentials registered"""
        return len(self.webauthn_credentials) > 0
    
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