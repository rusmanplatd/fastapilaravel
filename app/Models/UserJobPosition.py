from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.types import Integer, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Models.JobPosition import JobPosition


class UserJobPosition(BaseModel, LogsActivityMixin):
    """
    Pivot table for User-JobPosition many-to-many relationship.
    Stores detailed employment information for each user's position assignment.
    """
    __tablename__ = "user_job_positions"
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)  # type: ignore[arg-type]
    job_position_id: Mapped[int] = mapped_column(ForeignKey("job_positions.id"), nullable=False, index=True)  # type: ignore[arg-type]
    
    # Employment status
    is_active: Mapped[bool] = mapped_column( default=True, nullable=False)
    is_primary: Mapped[bool] = mapped_column( default=False, nullable=False)  # Primary job for the user
    
    # Employment dates
    start_date: Mapped[datetime] = mapped_column( server_default=func.now(), nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    
    # Compensation
    salary: Mapped[Optional[float]] = mapped_column( nullable=True)
    hourly_rate: Mapped[Optional[float]] = mapped_column( nullable=True)
    bonus_eligible: Mapped[bool] = mapped_column( default=False, nullable=False)
    equity_eligible: Mapped[bool] = mapped_column( default=False, nullable=False)
    
    # Work arrangement
    work_arrangement: Mapped[str] = mapped_column(default="on-site", nullable=False)  # on-site, remote, hybrid
    work_location: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Employment terms
    employment_type: Mapped[str] = mapped_column(default="full-time", nullable=False)  # full-time, part-time, contract, intern
    probation_period_months: Mapped[Optional[int]] = mapped_column(nullable=True)
    probation_end_date: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    
    # Performance and evaluation
    performance_rating: Mapped[Optional[float]] = mapped_column( nullable=True)  # 1.0 to 5.0 scale
    last_review_date: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    next_review_date: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    
    # Manager and reporting
    direct_manager_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)  # type: ignore[arg-type]
    
    # Additional details
    employee_id: Mapped[Optional[str]] = mapped_column(nullable=True)  # Company employee ID
    badge_number: Mapped[Optional[str]] = mapped_column(nullable=True)
    workstation_number: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Status tracking
    status: Mapped[str] = mapped_column(default="active", nullable=False)  # active, on_leave, terminated, resigned
    termination_reason: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Notes and comments
    notes: Mapped[Optional[str]] = mapped_column(nullable=True)
    hr_notes: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Relationships
    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
    job_position: Mapped[JobPosition] = relationship(
        "JobPosition", 
        back_populates="user_job_positions"
    )
    direct_manager: Mapped[Optional[User]] = relationship(
        "User", 
        foreign_keys=[direct_manager_id]
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for UserJobPosition model."""
        return LogOptions(
            log_name="user_job_positions",
            log_attributes=["user_id", "job_position_id", "is_active", "is_primary", "salary", "status"],
            description_for_event={
                "created": "User assigned to job position",
                "updated": "User job position updated", 
                "deleted": "User removed from job position"
            }
        )
    
    def is_current(self) -> bool:
        """Check if this user-position assignment is currently active."""
        return self.is_active and self.end_date is None and self.status == "active"
    
    def get_tenure_days(self) -> int:
        """Get the number of days in this position."""
        end_date = self.end_date or datetime.now()
        return (end_date - self.start_date).days
    
    def get_tenure_months(self) -> float:
        """Get the number of months in this position."""
        return self.get_tenure_days() / 30.44  # Average days per month
    
    def get_tenure_years(self) -> float:
        """Get the number of years in this position."""
        return self.get_tenure_days() / 365.25  # Account for leap years
    
    def is_on_probation(self) -> bool:
        """Check if the user is currently on probation."""
        if not self.probation_end_date:
            return False
        return datetime.now() < self.probation_end_date
    
    def get_probation_days_remaining(self) -> int:
        """Get the number of days remaining in probation period."""
        if not self.probation_end_date or not self.is_on_probation():
            return 0
        return (self.probation_end_date - datetime.now()).days
    
    def terminate_position(self, end_date: Optional[datetime] = None, reason: Optional[str] = None) -> None:
        """Terminate the user's position."""
        self.end_date = end_date or datetime.now()
        self.is_active = False
        self.status = "terminated"
        if reason:
            self.termination_reason = reason
        if self.is_primary:
            self.is_primary = False  # Can't be primary if terminated
    
    def resign_position(self, end_date: Optional[datetime] = None) -> None:
        """Mark the position as resigned."""
        self.end_date = end_date or datetime.now()
        self.is_active = False
        self.status = "resigned"
        if self.is_primary:
            self.is_primary = False  # Can't be primary if resigned
    
    def put_on_leave(self) -> None:
        """Put the user on leave."""
        self.status = "on_leave"
        self.is_active = False
    
    def return_from_leave(self) -> None:
        """Return the user from leave."""
        self.status = "active"
        self.is_active = True
    
    def get_compensation_display(self) -> str:
        """Get formatted compensation display."""
        if self.salary:
            return f"${self.salary:,.0f}/year"
        elif self.hourly_rate:
            return f"${self.hourly_rate:.2f}/hour"
        else:
            return "Not specified"
    
    def get_performance_display(self) -> str:
        """Get formatted performance rating display."""
        if not self.performance_rating:
            return "Not rated"
        return f"{self.performance_rating:.1f}/5.0"
    
    def is_due_for_review(self) -> bool:
        """Check if the user is due for a performance review."""
        if not self.next_review_date:
            return False
        return datetime.now() >= self.next_review_date
    
    def to_dict_detailed(self) -> Dict[str, Any]:
        """Return detailed user-job position relationship data."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name,
            "user_email": self.user.email,
            "job_position_id": self.job_position_id,
            "job_position_title": self.job_position.title,
            "job_position_code": self.job_position.code,
            "job_level_name": self.job_position.job_level.name,
            "job_level_order": self.job_position.job_level.level_order,
            "department_name": self.job_position.department.name,
            "department_full_name": self.job_position.department.get_full_name(),
            "organization_name": self.job_position.department.organization.name,
            "is_active": self.is_active,
            "is_primary": self.is_primary,
            "is_current": self.is_current(),
            "start_date": self.start_date,
            "end_date": self.end_date,
            "tenure_days": self.get_tenure_days(),
            "tenure_months": round(self.get_tenure_months(), 1),
            "tenure_years": round(self.get_tenure_years(), 2),
            "salary": self.salary,
            "hourly_rate": self.hourly_rate,
            "compensation_display": self.get_compensation_display(),
            "bonus_eligible": self.bonus_eligible,
            "equity_eligible": self.equity_eligible,
            "work_arrangement": self.work_arrangement,
            "work_location": self.work_location,
            "employment_type": self.employment_type,
            "probation_period_months": self.probation_period_months,
            "probation_end_date": self.probation_end_date,
            "is_on_probation": self.is_on_probation(),
            "probation_days_remaining": self.get_probation_days_remaining(),
            "performance_rating": self.performance_rating,
            "performance_display": self.get_performance_display(),
            "last_review_date": self.last_review_date,
            "next_review_date": self.next_review_date,
            "is_due_for_review": self.is_due_for_review(),
            "direct_manager_id": self.direct_manager_id,
            "direct_manager_name": self.direct_manager.name if self.direct_manager else None,
            "employee_id": self.employee_id,
            "badge_number": self.badge_number,
            "workstation_number": self.workstation_number,
            "status": self.status,
            "termination_reason": self.termination_reason,
            "notes": self.notes,
            "hr_notes": self.hr_notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }