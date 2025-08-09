from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Models.Department import Department


class UserDepartment(BaseModel, LogsActivityMixin):
    """
    Pivot table for User-Department many-to-many relationship.
    Stores additional metadata about the user's relationship with a department.
    """
    __tablename__ = "user_departments"
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)  # type: ignore[arg-type]
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False, index=True)  # type: ignore[arg-type]
    
    # Relationship metadata
    role_in_department: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_primary: Mapped[bool] = mapped_column( default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column( default=True, nullable=False)
    
    # Dates
    joined_at: Mapped[datetime] = mapped_column( server_default=func.now(), nullable=False)
    left_at: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    
    # Department-specific permissions
    can_approve_requests: Mapped[bool] = mapped_column( default=False, nullable=False)
    can_manage_budget: Mapped[bool] = mapped_column( default=False, nullable=False)
    can_hire: Mapped[bool] = mapped_column( default=False, nullable=False)
    
    # Work allocation (percentage of time spent in this department)
    allocation_percentage: Mapped[Optional[float]] = mapped_column(nullable=True)  # 0.0 to 100.0
    
    # Cost and billing information
    cost_center: Mapped[Optional[str]] = mapped_column(nullable=True)
    billing_rate: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Additional metadata
    notes: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Relationships
    user: Mapped[User] = relationship("User")
    department: Mapped[Department] = relationship(
        "Department", 
        back_populates="user_departments"
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for UserDepartment model."""
        return LogOptions(
            log_name="user_departments",
            log_attributes=["user_id", "department_id", "role_in_department", "is_primary", "is_active"],
            description_for_event={
                "created": "User joined department",
                "updated": "User-department relationship updated", 
                "deleted": "User left department"
            }
        )
    
    def is_current(self) -> bool:
        """Check if this user-department relationship is currently active."""
        return self.is_active and self.left_at is None
    
    def get_duration_days(self) -> Optional[int]:
        """Get the duration of the relationship in days."""
        end_date = self.left_at or datetime.now()
        return (end_date - self.joined_at).days
    
    def leave_department(self, leave_date: Optional[datetime] = None) -> None:
        """Mark the user as having left the department."""
        self.left_at = leave_date or datetime.now()
        self.is_active = False
        if self.is_primary:
            self.is_primary = False  # Can't be primary if left
    
    def rejoin_department(self) -> None:
        """Mark the user as rejoining the department."""
        self.left_at = None
        self.is_active = True
        self.joined_at = datetime.now()
    
    def get_allocation_display(self) -> str:
        """Get formatted allocation percentage display."""
        if self.allocation_percentage is None:
            return "Not specified"
        return f"{self.allocation_percentage:.1f}%"
    
    def is_full_time_in_department(self) -> bool:
        """Check if user is allocated full-time to this department."""
        return self.allocation_percentage is not None and self.allocation_percentage >= 100.0
    
    def is_part_time_in_department(self) -> bool:
        """Check if user is allocated part-time to this department."""
        return self.allocation_percentage is not None and 0 < self.allocation_percentage < 100.0
    
    def to_dict_detailed(self) -> Dict[str, Any]:
        """Return detailed user-department relationship data."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name,
            "user_email": self.user.email,
            "department_id": self.department_id,
            "department_name": self.department.name,
            "department_code": self.department.code,
            "department_full_name": self.department.get_full_name(),
            "organization_id": self.department.organization_id,
            "organization_name": self.department.organization.name,
            "role_in_department": self.role_in_department,
            "is_primary": self.is_primary,
            "is_active": self.is_active,
            "is_current": self.is_current(),
            "joined_at": self.joined_at,
            "left_at": self.left_at,
            "duration_days": self.get_duration_days(),
            "can_approve_requests": self.can_approve_requests,
            "can_manage_budget": self.can_manage_budget,
            "can_hire": self.can_hire,
            "allocation_percentage": self.allocation_percentage,
            "allocation_display": self.get_allocation_display(),
            "is_full_time": self.is_full_time_in_department(),
            "is_part_time": self.is_part_time_in_department(),
            "cost_center": self.cost_center,
            "billing_rate": self.billing_rate,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }