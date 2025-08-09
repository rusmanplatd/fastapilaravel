from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Text, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.Organization import Organization
    from app.Models.User import User
    from app.Models.TenantUser import TenantUser


class Tenant(BaseModel, LogsActivityMixin):
    """
    Tenant model for multi-tenant architecture.
    Each tenant represents a separate organization/company instance.
    """
    __tablename__ = "tenants"
    
    # Basic tenant information
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    subdomain: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(unique=True, nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Subscription and billing
    subscription_plan: Mapped[str] = mapped_column(default="free", nullable=False)
    subscription_status: Mapped[str] = mapped_column(default="active", nullable=False)
    max_users: Mapped[Optional[int]] = mapped_column(nullable=True)
    max_organizations: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Contact information
    primary_email: Mapped[Optional[str]] = mapped_column(nullable=True)
    primary_phone: Mapped[Optional[str]] = mapped_column(nullable=True)
    website: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Address information
    address: Mapped[Optional[str]] = mapped_column(nullable=True)
    city: Mapped[Optional[str]] = mapped_column(nullable=True)
    state: Mapped[Optional[str]] = mapped_column(nullable=True)
    country: Mapped[Optional[str]] = mapped_column(nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(nullable=True)
    timezone: Mapped[str] = mapped_column(default="UTC", nullable=False)
    
    # Features and settings
    features: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    branding: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Status and lifecycle
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    suspended_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    suspension_reason: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Relationships
    organizations: Mapped[List[Organization]] = relationship(
        "Organization",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    
    tenant_users: Mapped[List[TenantUser]] = relationship(
        "TenantUser",
        back_populates="tenant",
        cascade="all, delete-orphan"
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for Tenant model."""
        return LogOptions(
            log_name="tenants",
            log_attributes=["name", "subdomain", "domain", "is_active", "subscription_plan", "subscription_status"],
            description_for_event={
                "created": "Tenant was created",
                "updated": "Tenant was updated",
                "deleted": "Tenant was deleted"
            }
        )
    
    def get_primary_organization(self) -> Optional[Organization]:
        """Get the primary/root organization for this tenant."""
        # Return the first organization or the one marked as primary
        if not self.organizations:
            return None
        
        # Look for organization with primary flag or first one
        for org in self.organizations:
            if org.settings and isinstance(org.settings, str):
                import json
                try:
                    settings = json.loads(org.settings)
                    if settings.get("is_primary", False):
                        return org
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Return first organization if no primary found
        return self.organizations[0] if self.organizations else None
    
    def get_total_users(self) -> int:
        """Get total number of users across all organizations."""
        return len(self.tenant_users)
    
    def get_active_users(self) -> int:
        """Get number of active users."""
        return len([tu for tu in self.tenant_users if tu.is_active])
    
    def get_total_organizations(self) -> int:
        """Get total number of organizations."""
        return len(self.organizations)
    
    def get_active_organizations(self) -> int:
        """Get number of active organizations."""
        return len([org for org in self.organizations if org.is_active])
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled for this tenant."""
        if not self.features:
            return False
        return self.features.get(feature_name, False)
    
    def get_setting(self, setting_name: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        if not self.settings:
            return default
        return self.settings.get(setting_name, default)
    
    def update_setting(self, setting_name: str, value: Any) -> None:
        """Update a specific setting value."""
        if not self.settings:
            self.settings = {}
        self.settings[setting_name] = value
    
    def is_trial(self) -> bool:
        """Check if tenant is in trial period."""
        return (
            self.trial_ends_at is not None and 
            self.trial_ends_at > datetime.utcnow()
        )
    
    def is_suspended(self) -> bool:
        """Check if tenant is suspended."""
        return self.suspended_at is not None
    
    def can_add_users(self) -> bool:
        """Check if tenant can add more users."""
        if not self.max_users:
            return True
        return self.get_total_users() < self.max_users
    
    def can_add_organizations(self) -> bool:
        """Check if tenant can add more organizations."""
        if not self.max_organizations:
            return True
        return self.get_total_organizations() < self.max_organizations
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get tenant usage statistics."""
        return {
            "total_users": self.get_total_users(),
            "active_users": self.get_active_users(),
            "max_users": self.max_users,
            "total_organizations": self.get_total_organizations(),
            "active_organizations": self.get_active_organizations(),
            "max_organizations": self.max_organizations,
            "is_trial": self.is_trial(),
            "is_suspended": self.is_suspended(),
            "subscription_plan": self.subscription_plan,
            "subscription_status": self.subscription_status,
        }
    
    def to_dict_with_stats(self) -> Dict[str, Any]:
        """Return tenant data with usage statistics."""
        return {
            "id": self.id,
            "name": self.name,
            "subdomain": self.subdomain,
            "domain": self.domain,
            "description": self.description,
            "is_active": self.is_active,
            "subscription_plan": self.subscription_plan,
            "subscription_status": self.subscription_status,
            "primary_email": self.primary_email,
            "primary_phone": self.primary_phone,
            "website": self.website,
            "timezone": self.timezone,
            "trial_ends_at": self.trial_ends_at,
            "suspended_at": self.suspended_at,
            "suspension_reason": self.suspension_reason,
            "usage_stats": self.get_usage_stats(),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def get_by_subdomain(cls, subdomain: str) -> Optional[Tenant]:
        """Get tenant by subdomain."""
        from config.database import SessionLocal
        session = SessionLocal()
        return session.query(cls).filter(cls.subdomain == subdomain).first()
    
    @classmethod
    def get_by_domain(cls, domain: str) -> Optional[Tenant]:
        """Get tenant by custom domain."""
        from config.database import SessionLocal
        session = SessionLocal()
        return session.query(cls).filter(cls.domain == domain).first()