from __future__ import annotations

from typing import Optional, Dict, Any, List, TYPE_CHECKING, Union
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, Text, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.PerformanceReview import PerformanceReview
    from app.Models.Organization import Organization


class PerformanceReviewCycle(BaseModel, LogsActivityMixin):
    """
    Performance review cycle model for managing review periods.
    Defines review schedules, deadlines, and organizational settings.
    """
    __tablename__ = "performance_review_cycles"
    
    # Basic cycle information
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id"),  # type: ignore[arg-type]
        nullable=True, 
        index=True
    )
    
    # Cycle period
    cycle_start_date: Mapped[datetime] = mapped_column(nullable=False, index=True)
    cycle_end_date: Mapped[datetime] = mapped_column(nullable=False, index=True)
    
    # Review deadlines
    self_review_deadline: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    manager_review_deadline: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    hr_review_deadline: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Cycle status and settings
    status: Mapped[str] = mapped_column(nullable=False, default="draft", index=True)  # draft, active, completed, cancelled
    is_active: Mapped[bool] = mapped_column(default=False, index=True)
    requires_self_review: Mapped[bool] = mapped_column(default=True)
    requires_manager_review: Mapped[bool] = mapped_column(default=True)
    requires_hr_approval: Mapped[bool] = mapped_column(default=False)
    
    # Review settings
    review_type: Mapped[str] = mapped_column(nullable=False, default="annual")  # annual, mid_year, quarterly, project
    rating_scale: Mapped[int] = mapped_column(nullable=False, default=5)  # 1-5, 1-10, etc.
    
    # Template and configuration
    review_template_id: Mapped[Optional[int]] = mapped_column(nullable=True)  # Future: link to review templates
    competency_framework_id: Mapped[Optional[int]] = mapped_column(nullable=True)  # Future: link to competency frameworks
    
    # Automation settings
    auto_notify_employees: Mapped[bool] = mapped_column(default=True)
    auto_notify_managers: Mapped[bool] = mapped_column(default=True)
    reminder_days_before_deadline: Mapped[int] = mapped_column(default=7)
    
    # Relationships
    reviews: Mapped[Any] = relationship("PerformanceReview", back_populates="review_cycle", lazy="dynamic")
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="review_cycles")
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for PerformanceReviewCycle model."""
        return LogOptions(
            log_name="performance_review_cycles",
            log_attributes=["name", "status", "is_active", "cycle_start_date", "cycle_end_date"],
            description_for_event={
                "created": "Review cycle was created",
                "updated": "Review cycle was updated", 
                "deleted": "Review cycle was deleted",
            },
            log_only_changed=True
        )
    
    # Scopes
    @classmethod
    def scope_active(cls, query: Any) -> Any:
        """Scope to get active review cycles."""
        return query.filter(cls.is_active == True)
    
    @classmethod 
    def scope_by_status(cls, query: Any, status: str) -> Any:
        """Scope to filter by status."""
        return query.filter(cls.status == status)
    
    @classmethod
    def scope_current(cls, query: Any) -> Any:
        """Scope to get current review cycles (active and within date range)."""
        now = datetime.utcnow()
        return query.filter(
            cls.is_active == True,
            cls.cycle_start_date <= now,
            cls.cycle_end_date >= now
        )
    
    @classmethod
    def scope_by_organization(cls, query: Any, organization_id: int) -> Any:
        """Scope to filter by organization."""
        return query.filter(cls.organization_id == organization_id)
    
    # Methods
    def is_current(self) -> bool:
        """Check if the review cycle is currently active."""
        now = datetime.utcnow()
        return (self.is_active and 
                self.cycle_start_date <= now <= self.cycle_end_date)
    
    def days_remaining(self) -> Optional[int]:
        """Get the number of days remaining in the cycle."""
        if not self.is_current():
            return None
        
        now = datetime.utcnow()
        return (self.cycle_end_date - now).days
    
    def get_active_reviews_count(self) -> int:
        """Get count of active reviews in this cycle."""
        return int(self.reviews.filter_by(status="in_progress").count())
    
    def get_completed_reviews_count(self) -> int:
        """Get count of completed reviews in this cycle."""
        return int(self.reviews.filter_by(status="completed").count())
    
    def get_progress_percentage(self) -> float:
        """Get completion percentage for this cycle."""
        total = int(self.reviews.count())
        if total == 0:
            return 0.0
        
        completed = self.get_completed_reviews_count()
        return (completed / total) * 100.0
    
    def activate(self) -> None:
        """Activate this review cycle and deactivate others in the organization."""
        # This would be implemented with proper business logic
        # For now, just set this cycle as active
        self.is_active = True
        self.status = "active"
    
    def complete(self) -> None:
        """Mark this review cycle as completed."""
        self.status = "completed"
        self.is_active = False
    
    def __repr__(self) -> str:
        return f"<PerformanceReviewCycle(id={self.id}, name='{self.name}', status='{self.status}')>"