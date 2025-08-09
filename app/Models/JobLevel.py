from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING, Union
from datetime import datetime
from sqlalchemy import String, Boolean, Text, Index, and_, or_
from sqlalchemy.types import Integer, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column, validates
from sqlalchemy.ext.hybrid import hybrid_property
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions
import json

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
    
    # Career progression
    next_level_id: Mapped[Optional[int]] = mapped_column(nullable=True)  # Next level in progression
    previous_level_id: Mapped[Optional[int]] = mapped_column(nullable=True)  # Previous level
    promotion_requirements: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON requirements
    
    # Competency framework
    required_competencies: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array
    preferred_competencies: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array
    leadership_competencies: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array
    
    # Performance and review
    performance_rating_scale: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON scale definition
    review_frequency_months: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Benefits and perks
    benefit_tier: Mapped[Optional[str]] = mapped_column(nullable=True)  # basic, standard, premium, executive
    vacation_days: Mapped[Optional[int]] = mapped_column(nullable=True)
    sick_days: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Settings and metadata
    settings: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON string for flexible settings
    
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
    
    def to_dict_career_focused(self) -> Dict[str, Any]:
        """Return job level data with career progression focus."""
        return {
            **self.to_dict_detailed(),
            "career_progression": self.get_progression_path(),
            "competency_framework": self.get_all_competencies(),
            "level_statistics": self.get_level_statistics(),
            "benefit_details": self.get_benefit_package()
        }
    
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
    
    @validates('level_order')
    def validate_level_order(self, key: str, level_order: int) -> int:
        """Validate level order is positive."""
        if level_order < 1:
            raise ValueError("Level order must be a positive integer")
        return level_order
    
    @validates('min_salary', 'max_salary')
    def validate_salary_range(self, key: str, salary: Optional[float]) -> Optional[float]:
        """Validate salary amounts."""
        if salary is not None and salary < 0:
            raise ValueError("Salary cannot be negative")
        
        # Validate salary range consistency
        if key == 'min_salary' and salary is not None and self.max_salary is not None:
            if salary > self.max_salary:
                raise ValueError("Minimum salary cannot be greater than maximum salary")
        elif key == 'max_salary' and salary is not None and self.min_salary is not None:
            if salary < self.min_salary:
                raise ValueError("Maximum salary cannot be less than minimum salary")
        
        return salary
    
    @validates('benefit_tier')
    def validate_benefit_tier(self, key: str, tier: Optional[str]) -> Optional[str]:
        """Validate benefit tier."""
        if tier:
            valid_tiers = ['basic', 'standard', 'premium', 'executive']
            if tier not in valid_tiers:
                raise ValueError(f"Benefit tier must be one of: {', '.join(valid_tiers)}")
        return tier
    
    def get_progression_path(self) -> Dict[str, Any]:
        """Get career progression path for this level."""
        from config.database import SessionLocal
        session = SessionLocal()
        
        next_level = None
        previous_level = None
        
        if self.next_level_id:
            next_level = session.query(JobLevel).filter(JobLevel.id == self.next_level_id).first()
        
        if self.previous_level_id:
            previous_level = session.query(JobLevel).filter(JobLevel.id == self.previous_level_id).first()
        
        return {
            "current_level": {
                "id": self.id,
                "name": self.name,
                "level_order": self.level_order
            },
            "next_level": {
                "id": next_level.id,
                "name": next_level.name,
                "level_order": next_level.level_order,
                "requirements": self.get_promotion_requirements()
            } if next_level else None,
            "previous_level": {
                "id": previous_level.id,
                "name": previous_level.name,
                "level_order": previous_level.level_order
            } if previous_level else None
        }
    
    def get_promotion_requirements(self) -> List[Dict[str, Any]]:
        """Get promotion requirements to next level."""
        if not self.promotion_requirements:
            return []
        try:
            return json.loads(self.promotion_requirements)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_promotion_requirements(self, requirements: List[Dict[str, Any]]) -> None:
        """Set promotion requirements."""
        self.promotion_requirements = json.dumps(requirements)
    
    def get_required_competencies(self) -> List[Dict[str, Any]]:
        """Get required competencies for this level."""
        if not self.required_competencies:
            return []
        try:
            return json.loads(self.required_competencies)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def get_preferred_competencies(self) -> List[Dict[str, Any]]:
        """Get preferred competencies for this level."""
        if not self.preferred_competencies:
            return []
        try:
            return json.loads(self.preferred_competencies)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def get_leadership_competencies(self) -> List[Dict[str, Any]]:
        """Get leadership competencies for this level."""
        if not self.leadership_competencies:
            return []
        try:
            return json.loads(self.leadership_competencies)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def get_all_competencies(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all competencies grouped by type."""
        return {
            "required": self.get_required_competencies(),
            "preferred": self.get_preferred_competencies(),
            "leadership": self.get_leadership_competencies()
        }
    
    def get_benefit_package(self) -> Dict[str, Any]:
        """Get benefit package for this level."""
        package = {
            "tier": self.benefit_tier or "basic",
            "vacation_days": self.vacation_days or 15,
            "sick_days": self.sick_days or 10,
            "review_frequency": f"Every {self.review_frequency_months or 12} months"
        }
        
        # Add tier-specific benefits
        tier_benefits = {
            "basic": {
                "health_insurance": "Basic plan",
                "retirement_match": "3%",
                "professional_development": "$500/year"
            },
            "standard": {
                "health_insurance": "Standard plan + dental",
                "retirement_match": "4%",
                "professional_development": "$1000/year",
                "flexible_hours": True
            },
            "premium": {
                "health_insurance": "Premium plan + dental + vision",
                "retirement_match": "6%",
                "professional_development": "$2500/year",
                "flexible_hours": True,
                "remote_work": True,
                "bonus_eligible": True
            },
            "executive": {
                "health_insurance": "Executive plan + full family coverage",
                "retirement_match": "8%",
                "professional_development": "$5000/year",
                "flexible_hours": True,
                "remote_work": True,
                "bonus_eligible": True,
                "stock_options": True,
                "company_car": True
            }
        }
        
        package["tier_benefits"] = tier_benefits.get(package["tier"], {})
        return package
    
    @classmethod
    def get_career_ladder(cls) -> List['JobLevel']:
        """Get complete career ladder ordered by level."""
        from config.database import SessionLocal
        session = SessionLocal()
        
        return session.query(cls).filter(
            cls.is_active == True
        ).order_by(cls.level_order.asc()).all()
    
    @classmethod
    def get_individual_contributor_levels(cls) -> List['JobLevel']:
        """Get all individual contributor (non-management) levels."""
        from config.database import SessionLocal
        session = SessionLocal()
        
        return session.query(cls).filter(
            cls.is_management == False,
            cls.is_executive == False,
            cls.is_active == True
        ).order_by(cls.level_order.asc()).all()