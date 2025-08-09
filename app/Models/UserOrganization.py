from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Models.Organization import Organization


class UserOrganization(BaseModel, LogsActivityMixin):
    """
    Pivot table for User-Organization many-to-many relationship.
    Stores additional metadata about the user's relationship with an organization.
    """
    __tablename__ = "user_organizations"
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)  # type: ignore[arg-type]
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)  # type: ignore[arg-type]
    
    # Relationship metadata
    role_in_organization: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_primary: Mapped[bool] = mapped_column( default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column( default=True, nullable=False)
    
    # Dates
    joined_at: Mapped[datetime] = mapped_column( server_default=func.now(), nullable=False)
    left_at: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    
    # Access and permissions within organization
    can_manage_departments: Mapped[bool] = mapped_column( default=False, nullable=False)
    can_manage_users: Mapped[bool] = mapped_column( default=False, nullable=False)
    can_view_reports: Mapped[bool] = mapped_column( default=False, nullable=False)
    
    # Employee/contractor information
    employee_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    cost_center: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Additional metadata
    notes: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Relationships
    user: Mapped[User] = relationship("User")
    organization: Mapped[Organization] = relationship(
        "Organization", 
        back_populates="user_organizations"
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for UserOrganization model."""
        return LogOptions(
            log_name="user_organizations",
            log_attributes=["user_id", "organization_id", "role_in_organization", "is_primary", "is_active"],
            description_for_event={
                "created": "User joined organization",
                "updated": "User-organization relationship updated", 
                "deleted": "User left organization"
            }
        )
    
    def is_current(self) -> bool:
        """Check if this user-organization relationship is currently active."""
        return self.is_active and self.left_at is None
    
    def get_duration_days(self) -> Optional[int]:
        """Get the duration of the relationship in days."""
        end_date = self.left_at or datetime.now()
        return (end_date - self.joined_at).days
    
    def leave_organization(self, leave_date: Optional[datetime] = None) -> None:
        """Mark the user as having left the organization."""
        self.left_at = leave_date or datetime.now()
        self.is_active = False
        if self.is_primary:
            self.is_primary = False  # Can't be primary if left
    
    def rejoin_organization(self) -> None:
        """Mark the user as rejoining the organization."""
        self.left_at = None
        self.is_active = True
        self.joined_at = datetime.now()
    
    def to_dict_detailed(self) -> Dict[str, Any]:
        """Return detailed user-organization relationship data."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name,
            "user_email": self.user.email,
            "organization_id": self.organization_id,
            "organization_name": self.organization.name,
            "organization_code": self.organization.code,
            "role_in_organization": self.role_in_organization,
            "is_primary": self.is_primary,
            "is_active": self.is_active,
            "is_current": self.is_current(),
            "joined_at": self.joined_at,
            "left_at": self.left_at,
            "duration_days": self.get_duration_days(),
            "can_manage_departments": self.can_manage_departments,
            "can_manage_users": self.can_manage_users,
            "can_view_reports": self.can_view_reports,
            "employee_id": self.employee_id,
            "cost_center": self.cost_center,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }