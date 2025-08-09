from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, Text
from sqlalchemy.types import Integer, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.JobPosition import JobPosition
    from app.Models.UserJobPosition import UserJobPosition


class JobLevel(BaseModel, LogsActivityMixin):
    """
    Job Level model representing hierarchical levels within an organization.
    Examples: Entry Level, Junior, Mid-Level, Senior, Lead, Manager, Director, VP, etc.
    """
    __tablename__ = "job_levels"
    
    # Basic job level information
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    code: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column( nullable=True)
    is_active: Mapped[bool] = mapped_column( default=True, nullable=False)
    
    # Hierarchical level (1 = lowest, higher numbers = higher levels)
    level_order: Mapped[int] = mapped_column( nullable=False, index=True)
    
    # Salary ranges (optional)
    min_salary: Mapped[Optional[float]] = mapped_column( nullable=True)
    max_salary: Mapped[Optional[float]] = mapped_column( nullable=True)
    
    # Experience requirements
    min_experience_years: Mapped[Optional[int]] = mapped_column( nullable=True)
    max_experience_years: Mapped[Optional[int]] = mapped_column( nullable=True)
    
    # Level attributes
    is_management: Mapped[bool] = mapped_column( default=False, nullable=False)
    is_executive: Mapped[bool] = mapped_column( default=False, nullable=False)
    can_approve_budget: Mapped[bool] = mapped_column( default=False, nullable=False)
    can_hire: Mapped[bool] = mapped_column( default=False, nullable=False)
    
    # Display properties
    color: Mapped[Optional[str]] = mapped_column(nullable=True)  # Hex color code
    icon: Mapped[Optional[str]] = mapped_column(nullable=True)
    sort_order: Mapped[int] = mapped_column( default=0, nullable=False)
    
    # Settings
    settings: Mapped[Optional[str]] = mapped_column( nullable=True)  # JSON string for flexible settings
    
    # Relationships
    job_positions: Mapped[List[JobPosition]] = relationship(
        "JobPosition", 
        back_populates="job_level"
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for JobLevel model."""
        return LogOptions(
            log_name="job_levels",
            log_attributes=["name", "code", "is_active", "level_order", "is_management", "is_executive"],
            description_for_event={
                "created": "Job level was created",
                "updated": "Job level was updated", 
                "deleted": "Job level was deleted"
            }
        )
    
    def get_positions_count(self) -> int:
        """Get the count of job positions using this level."""
        return len(self.job_positions)
    
    def get_active_positions_count(self) -> int:
        """Get the count of active job positions using this level."""
        return len([pos for pos in self.job_positions if pos.is_active])
    
    def get_users_count(self) -> int:
        """Get the count of users at this job level."""
        count = 0
        for position in self.job_positions:
            count += len(position.user_job_positions)
        return count
    
    def is_higher_than(self, other_level: JobLevel) -> bool:
        """Check if this level is higher than another level."""
        return self.level_order > other_level.level_order
    
    def is_lower_than(self, other_level: JobLevel) -> bool:
        """Check if this level is lower than another level."""
        return self.level_order < other_level.level_order
    
    def is_same_level(self, other_level: JobLevel) -> bool:
        """Check if this level is the same as another level."""
        return self.level_order == other_level.level_order
    
    def get_salary_range_display(self) -> str:
        """Get a formatted display of the salary range."""
        if not self.min_salary and not self.max_salary:
            return "Not specified"
        
        if self.min_salary and self.max_salary:
            return f"${self.min_salary:,.0f} - ${self.max_salary:,.0f}"
        elif self.min_salary:
            return f"From ${self.min_salary:,.0f}"
        else:  # max_salary only
            return f"Up to ${self.max_salary:,.0f}"
    
    def get_experience_range_display(self) -> str:
        """Get a formatted display of the experience range."""
        if not self.min_experience_years and not self.max_experience_years:
            return "Not specified"
        
        if self.min_experience_years and self.max_experience_years:
            if self.min_experience_years == self.max_experience_years:
                return f"{self.min_experience_years} year{'s' if self.min_experience_years != 1 else ''}"
            return f"{self.min_experience_years}-{self.max_experience_years} years"
        elif self.min_experience_years:
            return f"{self.min_experience_years}+ years"
        else:  # max_experience_years only
            return f"Up to {self.max_experience_years} years"
    
    def get_level_type(self) -> str:
        """Get a string representation of the level type."""
        if self.is_executive:
            return "Executive"
        elif self.is_management:
            return "Management"
        else:
            return "Individual Contributor"
    
    def to_dict_detailed(self) -> Dict[str, Any]:
        """Return detailed job level data."""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "is_active": self.is_active,
            "level_order": self.level_order,
            "min_salary": self.min_salary,
            "max_salary": self.max_salary,
            "salary_range_display": self.get_salary_range_display(),
            "min_experience_years": self.min_experience_years,
            "max_experience_years": self.max_experience_years,
            "experience_range_display": self.get_experience_range_display(),
            "is_management": self.is_management,
            "is_executive": self.is_executive,
            "can_approve_budget": self.can_approve_budget,
            "can_hire": self.can_hire,
            "level_type": self.get_level_type(),
            "color": self.color,
            "icon": self.icon,
            "sort_order": self.sort_order,
            "positions_count": self.get_positions_count(),
            "active_positions_count": self.get_active_positions_count(),
            "users_count": self.get_users_count(),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def get_by_level_order(cls, level_order: int) -> Optional[JobLevel]:
        """Get job level by level order."""
        from config.database import SessionLocal
        session = SessionLocal()
        return session.query(cls).filter(cls.level_order == level_order).first()
    
    @classmethod
    def get_management_levels(cls) -> List[JobLevel]:
        """Get all management job levels."""
        from config.database import SessionLocal
        session = SessionLocal()
        return session.query(cls).filter(
            cls.is_management == True,
            cls.is_active == True
        ).order_by(cls.level_order.desc()).all()
    
    @classmethod
    def get_executive_levels(cls) -> List[JobLevel]:
        """Get all executive job levels."""
        from config.database import SessionLocal
        session = SessionLocal()
        return session.query(cls).filter(
            cls.is_executive == True,
            cls.is_active == True
        ).order_by(cls.level_order.desc()).all()