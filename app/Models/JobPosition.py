from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING, Union
from datetime import datetime, timedelta
from sqlalchemy import Boolean, Text, ForeignKey, Index, and_, or_, String
from sqlalchemy.types import Integer, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column, validates
from sqlalchemy.ext.hybrid import hybrid_property
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions
import json
import re

if TYPE_CHECKING:
    from app.Models.Department import Department
    from app.Models.JobLevel import JobLevel
    from app.Models.User import User
    from app.Models.UserJobPosition import UserJobPosition


class JobPosition(BaseModel, LogsActivityMixin):
    """
    Job Position model representing specific roles within departments.
    Combines department context with job level to create specific positions.
    Examples: "Senior Software Engineer", "Marketing Manager", "HR Director", etc.
    Supports recruitment tracking, performance management, and career progression.
    """
    __tablename__ = "job_positions"
    
    __table_args__ = (
        Index('idx_position_dept_active', 'department_id', 'is_active'),
        Index('idx_position_level_status', 'job_level_id', 'status'),
        Index('idx_position_reports_to', 'reports_to_position_id'),
        Index('idx_position_code_dept', 'code', 'department_id', unique=True),
    )
    
    # Basic position information
    title: Mapped[str] = mapped_column(nullable=False, index=True)
    code: Mapped[str] = mapped_column(nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column( nullable=True)
    responsibilities: Mapped[Optional[str]] = mapped_column( nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column( nullable=True)
    is_active: Mapped[bool] = mapped_column( default=True, nullable=False)
    
    # Relationships
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False, index=True)  # type: ignore[arg-type]
    job_level_id: Mapped[int] = mapped_column(ForeignKey("job_levels.id"), nullable=False, index=True)  # type: ignore[arg-type]
    
    # Position-specific salary (can override job level defaults)
    min_salary: Mapped[Optional[float]] = mapped_column( nullable=True)
    max_salary: Mapped[Optional[float]] = mapped_column( nullable=True)
    
    # Position capacity and availability
    max_headcount: Mapped[Optional[int]] = mapped_column( nullable=True)  # Maximum people for this position
    is_remote_allowed: Mapped[bool] = mapped_column( default=False, nullable=False)
    is_hybrid_allowed: Mapped[bool] = mapped_column( default=False, nullable=False)
    
    # Reporting structure
    reports_to_position_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job_positions.id"), nullable=True, index=True)  # type: ignore[arg-type]
    
    # Employment details
    employment_type: Mapped[str] = mapped_column(default="full-time", nullable=False)  # full-time, part-time, contract, intern
    is_billable: Mapped[bool] = mapped_column( default=False, nullable=False)
    hourly_rate: Mapped[Optional[float]] = mapped_column( nullable=True)
    
    # Skills and qualifications
    required_skills: Mapped[Optional[str]] = mapped_column( nullable=True)  # JSON array
    preferred_skills: Mapped[Optional[str]] = mapped_column( nullable=True)  # JSON array
    education_requirement: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Status and lifecycle
    status: Mapped[str] = mapped_column(default="active", nullable=False)  # active, recruiting, on-hold, closed
    posted_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    closed_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Display and organization
    sort_order: Mapped[int] = mapped_column( default=0, nullable=False)
    is_public: Mapped[bool] = mapped_column( default=True, nullable=False)  # Show in public job listings
    
    # Recruitment and hiring
    job_posting_url: Mapped[Optional[str]] = mapped_column(nullable=True)
    application_deadline: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    priority_level: Mapped[str] = mapped_column(default="medium", nullable=False)  # low, medium, high, critical
    
    # Performance and evaluation
    performance_goals: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array
    success_metrics: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array
    review_template_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Work environment and conditions
    travel_requirement: Mapped[Optional[str]] = mapped_column(nullable=True)  # none, minimal, moderate, frequent
    security_clearance_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    physical_requirements: Mapped[Optional[str]] = mapped_column(nullable=True)
    work_environment: Mapped[Optional[str]] = mapped_column(nullable=True)  # office, warehouse, field, etc.
    
    # Collaboration and team
    team_size_managed: Mapped[Optional[int]] = mapped_column(nullable=True)
    stakeholder_groups: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array
    collaboration_level: Mapped[str] = mapped_column(default="team", nullable=False)  # individual, team, cross-team, organization
    
    # Budget and financial responsibility
    budget_responsibility: Mapped[Optional[float]] = mapped_column(nullable=True)
    revenue_responsibility: Mapped[Optional[float]] = mapped_column(nullable=True)
    can_approve_expenses: Mapped[bool] = mapped_column(default=False, nullable=False)
    expense_approval_limit: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Career development
    career_track: Mapped[Optional[str]] = mapped_column(nullable=True)  # technical, management, specialized
    growth_opportunities: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array
    mentorship_available: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Settings and metadata
    settings: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON string for flexible settings
    tags: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array for categorization
    
    # Relationships
    department: Mapped[Department] = relationship(
        "Department", 
        back_populates="job_positions"
    )
    
    job_level: Mapped[JobLevel] = relationship(
        "JobLevel", 
        back_populates="job_positions"
    )
    
    # Self-referencing relationship for reporting structure
    reports_to: Mapped[Optional[JobPosition]] = relationship(
        "JobPosition", 
        remote_side="JobPosition.id", 
        back_populates="direct_reports"
    )
    direct_reports: Mapped[List[JobPosition]] = relationship(
        "JobPosition", 
        back_populates="reports_to"
    )
    
    # User-position relationships
    user_job_positions: Mapped[List[UserJobPosition]] = relationship(
        "UserJobPosition", 
        back_populates="job_position",
        cascade="all, delete-orphan"
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for JobPosition model."""
        return LogOptions(
            log_name="job_positions",
            log_attributes=["title", "code", "is_active", "department_id", "job_level_id", "status"],
            description_for_event={
                "created": "Job position was created",
                "updated": "Job position was updated", 
                "deleted": "Job position was deleted"
            }
        )
    
    def get_full_title(self) -> str:
        """Get the full title including department and organization context."""
        return f"{self.title} - {self.department.name} ({self.department.organization.name})"
    
    def get_current_users(self) -> List[User]:
        """Get all users currently in this position."""
        return [ujp.user for ujp in self.user_job_positions if ujp.is_current()]
    
    def get_all_users(self, include_historical: bool = False) -> List[User]:
        """Get all users who have held this position."""
        if include_historical:
            return [ujp.user for ujp in self.user_job_positions]
        else:
            return self.get_current_users()
    
    def get_current_headcount(self) -> int:
        """Get current number of people in this position."""
        return len(self.get_current_users())
    
    def get_available_slots(self) -> int:
        """Get number of available slots for this position."""
        if not self.max_headcount:
            return 999999  # Large number to represent unlimited
        return max(0, self.max_headcount - self.get_current_headcount())
    
    def is_available(self) -> bool:
        """Check if this position has available slots."""
        return self.get_available_slots() > 0
    
    def get_effective_salary_range(self) -> Dict[str, Optional[float]]:
        """Get effective salary range (position-specific or job level default)."""
        return {
            "min_salary": self.min_salary or self.job_level.min_salary,
            "max_salary": self.max_salary or self.job_level.max_salary
        }
    
    def get_salary_range_display(self) -> str:
        """Get a formatted display of the effective salary range."""
        salary_range = self.get_effective_salary_range()
        min_sal = salary_range["min_salary"]
        max_sal = salary_range["max_salary"]
        
        if not min_sal and not max_sal:
            return "Not specified"
        
        if min_sal and max_sal:
            return f"${min_sal:,.0f} - ${max_sal:,.0f}"
        elif min_sal:
            return f"From ${min_sal:,.0f}"
        else:  # max_sal only
            return f"Up to ${max_sal:,.0f}"
    
    def get_reporting_chain(self) -> List[JobPosition]:
        """Get the complete reporting chain up to the top."""
        chain = []
        current = self.reports_to
        while current and current not in chain:  # Prevent infinite loops
            chain.append(current)
            current = current.reports_to
        return chain
    
    def get_all_direct_reports(self) -> List[JobPosition]:
        """Get all positions that report to this position (recursively)."""
        reports = list(self.direct_reports)
        for direct_report in self.direct_reports:
            reports.extend(direct_report.get_all_direct_reports())
        return reports
    
    def is_manager_position(self) -> bool:
        """Check if this position manages other positions."""
        return len(self.direct_reports) > 0 or self.job_level.is_management
    
    def is_executive_position(self) -> bool:
        """Check if this is an executive position."""
        return self.job_level.is_executive
    
    def get_work_arrangement_options(self) -> List[str]:
        """Get available work arrangement options."""
        options = ["on-site"]
        if self.is_hybrid_allowed:
            options.append("hybrid")
        if self.is_remote_allowed:
            options.append("remote")
        return options
    
    def to_dict_detailed(self) -> Dict[str, Any]:
        """Return detailed job position data."""
        return {
            "id": self.id,
            "title": self.title,
            "code": self.code,
            "description": self.description,
            "responsibilities": self.responsibilities,
            "requirements": self.requirements,
            "is_active": self.is_active,
            "department_id": self.department_id,
            "department_name": self.department.name,
            "department_full_name": self.department.get_full_name(),
            "job_level_id": self.job_level_id,
            "job_level_name": self.job_level.name,
            "job_level_order": self.job_level.level_order,
            "full_title": self.get_full_title(),
            "min_salary": self.min_salary,
            "max_salary": self.max_salary,
            "effective_salary_range": self.get_effective_salary_range(),
            "salary_range_display": self.get_salary_range_display(),
            "max_headcount": self.max_headcount,
            "current_headcount": self.get_current_headcount(),
            "available_slots": self.get_available_slots(),
            "is_available": self.is_available(),
            "is_remote_allowed": self.is_remote_allowed,
            "is_hybrid_allowed": self.is_hybrid_allowed,
            "work_arrangement_options": self.get_work_arrangement_options(),
            "reports_to_position_id": self.reports_to_position_id,
            "reports_to_title": self.reports_to.title if self.reports_to else None,
            "direct_reports_count": len(self.direct_reports),
            "employment_type": self.employment_type,
            "is_billable": self.is_billable,
            "hourly_rate": self.hourly_rate,
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "education_requirement": self.education_requirement,
            "status": self.status,
            "posted_date": self.posted_date,
            "closed_date": self.closed_date,
            "is_manager_position": self.is_manager_position(),
            "is_executive_position": self.is_executive_position(),
            "is_public": self.is_public,
            "sort_order": self.sort_order,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def get_by_department(cls, department_id: int, active_only: bool = True) -> List[JobPosition]:
        """Get all job positions in a department."""
        from config.database import SessionLocal
        session = SessionLocal()
        
        query = session.query(cls).filter(cls.department_id == department_id)
        if active_only:
            query = query.filter(cls.is_active == True)
        
        return query.order_by(cls.sort_order, cls.title).all()
    
    @classmethod
    def get_by_job_level(cls, job_level_id: int, active_only: bool = True) -> List[JobPosition]:
        """Get all positions at a specific job level."""
        from config.database import SessionLocal
        session = SessionLocal()
        
        query = session.query(cls).filter(cls.job_level_id == job_level_id)
        if active_only:
            query = query.filter(cls.is_active == True)
        
        return query.order_by(cls.sort_order, cls.title).all()
    
    @classmethod
    def get_available_positions(cls) -> List[JobPosition]:
        """Get all positions that have available slots."""
        from config.database import SessionLocal
        session = SessionLocal()
        
        positions = session.query(cls).filter(
            cls.is_active == True,
            cls.status == "active"
        ).all()
        
        return [pos for pos in positions if pos.is_available()]
    
    @validates('code')
    def validate_code(self, key: str, code: str) -> str:
        """Validate position code format."""
        if not code:
            raise ValueError("Position code is required")
        
        # Code should be alphanumeric with underscores/hyphens, 2-30 chars
        if not re.match(r'^[A-Za-z0-9_-]{2,30}$', code):
            raise ValueError("Position code must be 2-30 alphanumeric characters, underscores, or hyphens")
        
        return code.upper()
    
    @validates('status')
    def validate_status(self, key: str, status: str) -> str:
        """Validate position status."""
        valid_statuses = ['active', 'recruiting', 'on-hold', 'closed', 'filled']
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return status
    
    @validates('employment_type')
    def validate_employment_type(self, key: str, emp_type: str) -> str:
        """Validate employment type."""
        valid_types = ['full-time', 'part-time', 'contract', 'intern', 'temporary', 'consultant']
        if emp_type not in valid_types:
            raise ValueError(f"Employment type must be one of: {', '.join(valid_types)}")
        return emp_type
    
    def get_comprehensive_skills(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all skills grouped by type."""
        required = []
        preferred = []
        
        if self.required_skills:
            try:
                required = json.loads(self.required_skills)
            except (json.JSONDecodeError, TypeError):
                pass
        
        if self.preferred_skills:
            try:
                preferred = json.loads(self.preferred_skills)
            except (json.JSONDecodeError, TypeError):
                pass
        
        return {
            "required": required,
            "preferred": preferred
        }
    
    def set_required_skills(self, skills: List[Dict[str, Any]]) -> None:
        """Set required skills."""
        self.required_skills = json.dumps(skills)
    
    def set_preferred_skills(self, skills: List[Dict[str, Any]]) -> None:
        """Set preferred skills."""
        self.preferred_skills = json.dumps(skills)
    
    def get_job_posting_data(self) -> Dict[str, Any]:
        """Get data formatted for job posting."""
        return {
            "title": self.title,
            "department": self.department.name,
            "organization": self.department.organization.name,
            "level": self.job_level.name,
            "employment_type": self.employment_type,
            "location": self.department.location or "Not specified",
            "remote_allowed": self.is_remote_allowed,
            "hybrid_allowed": self.is_hybrid_allowed,
            "description": self.description,
            "responsibilities": self.responsibilities,
            "requirements": self.requirements,
            "education_requirement": self.education_requirement,
            "skills": self.get_comprehensive_skills(),
            "salary_range": self.get_salary_range_display(),
            "experience_range": self.job_level.get_experience_range_display(),
            "posted_date": self.posted_date,
            "reports_to": self.reports_to.title if self.reports_to else None,
            "team_size_managed": self.team_size_managed
        }
    
    @hybrid_property
    def is_critical_role(self) -> bool:
        """Check if this is a critical role."""
        return (
            self.job_level.is_executive or
            (self.team_size_managed and self.team_size_managed > 10)
        )
    
    def get_position_complexity_score(self) -> int:
        """Calculate position complexity score (1-10)."""
        complexity = 1
        
        # Job level complexity
        complexity += min(3, self.job_level.level_order // 2)
        
        # Management complexity
        if self.team_size_managed:
            if self.team_size_managed > 20:
                complexity += 3
            elif self.team_size_managed > 10:
                complexity += 2
            elif self.team_size_managed > 5:
                complexity += 1
        
        return min(10, complexity)
    
    @classmethod
    def scope_by_department(cls, query: Any, department_id: int) -> Any:
        """Scope positions by department."""
        return query.filter(cls.department_id == department_id)
    
    @classmethod
    def scope_active(cls, query: Any) -> Any:
        """Scope for active positions."""
        return query.filter(and_(cls.is_active == True, cls.status.in_(['active', 'recruiting'])))
    
    @classmethod
    def scope_recruiting(cls, query: Any) -> Any:
        """Scope for positions currently recruiting."""
        return query.filter(cls.status == 'recruiting')
    
    @classmethod
    def scope_vacant(cls, query: Any) -> Any:
        """Scope for vacant positions."""
        return query.filter(and_(cls.is_active == True, cls.status == 'active'))
    
    @classmethod
    def scope_management(cls, query: Any) -> Any:
        """Scope for management positions."""
        from app.Models.JobLevel import JobLevel
        return query.join(JobLevel).filter(JobLevel.is_management == True)