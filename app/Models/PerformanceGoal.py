from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.PerformanceReview import PerformanceReview


class PerformanceGoal(BaseModel, LogsActivityMixin):
    """
    Performance goal model for tracking specific objectives within performance reviews.
    Supports SMART goals with measurable outcomes and progress tracking.
    """
    __tablename__ = "performance_goals"
    
    # Goal identification
    performance_review_id: Mapped[int] = mapped_column(
        ForeignKey("performance_reviews.id"),  # type: ignore[arg-type]
        nullable=False, 
        index=True
    )
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    
    # SMART criteria
    specific_description: Mapped[Optional[str]] = mapped_column( nullable=True)
    measurable_criteria: Mapped[Optional[str]] = mapped_column( nullable=True)
    achievable_plan: Mapped[Optional[str]] = mapped_column( nullable=True)
    relevant_justification: Mapped[Optional[str]] = mapped_column( nullable=True)
    time_bound_deadline: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    
    # Goal categorization
    goal_type: Mapped[str] = mapped_column(nullable=False, index=True)  # performance, development, behavior, project
    category: Mapped[Optional[str]] = mapped_column(nullable=True)  # sales, quality, leadership, etc.
    priority: Mapped[str] = mapped_column(default="medium", nullable=False)  # high, medium, low
    
    # Target and measurement
    target_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    target_unit: Mapped[Optional[str]] = mapped_column(nullable=True)  # %, $, units, etc.
    current_value: Mapped[Optional[float]] = mapped_column( nullable=True)
    measurement_method: Mapped[Optional[str]] = mapped_column( nullable=True)
    
    # Status and progress
    status: Mapped[str] = mapped_column(default="not_started", nullable=False, index=True)  # not_started, in_progress, achieved, not_achieved, cancelled
    progress_percentage: Mapped[Optional[int]] = mapped_column( nullable=True)  # 0-100
    
    # Achievement tracking
    achievement_rating: Mapped[Optional[float]] = mapped_column( nullable=True)  # 1.0 to 5.0 scale
    achieved_value: Mapped[Optional[float]] = mapped_column( nullable=True)
    achieved_at: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    achievement_notes: Mapped[Optional[str]] = mapped_column( nullable=True)
    
    # Support and resources
    required_resources: Mapped[Optional[str]] = mapped_column( nullable=True)
    support_needed: Mapped[Optional[str]] = mapped_column( nullable=True)
    obstacles: Mapped[Optional[str]] = mapped_column( nullable=True)
    
    # Weights and scoring
    weight: Mapped[float] = mapped_column( default=1.0, nullable=False)  # Importance weight in overall review
    contributes_to_rating: Mapped[bool] = mapped_column( default=True, nullable=False)
    
    # Milestone tracking
    milestones: Mapped[Optional[str]] = mapped_column( nullable=True)  # JSON array of milestones
    last_update: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    update_notes: Mapped[Optional[str]] = mapped_column( nullable=True)
    
    # Relationships
    performance_review: Mapped[PerformanceReview] = relationship("PerformanceReview", back_populates="goals")
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for PerformanceGoal model."""
        return LogOptions(
            log_name="performance_goals",
            log_attributes=["performance_review_id", "title", "status", "progress_percentage", "achievement_rating"],
            description_for_event={
                "created": "Performance goal created",
                "updated": "Performance goal updated", 
                "deleted": "Performance goal deleted"
            }
        )
    
    def is_not_started(self) -> bool:
        """Check if goal has not been started."""
        return self.status == "not_started"
    
    def is_in_progress(self) -> bool:
        """Check if goal is in progress."""
        return self.status == "in_progress"
    
    def is_achieved(self) -> bool:
        """Check if goal has been achieved."""
        return self.status == "achieved"
    
    def is_not_achieved(self) -> bool:
        """Check if goal was not achieved."""
        return self.status == "not_achieved"
    
    def is_overdue(self) -> bool:
        """Check if goal is overdue."""
        if not self.time_bound_deadline:
            return False
        return datetime.now() > self.time_bound_deadline and self.status not in ["achieved", "cancelled"]
    
    def start_goal(self) -> None:
        """Mark goal as started."""
        if self.status != "not_started":
            raise ValueError(f"Cannot start goal with status: {self.status}")
        
        self.status = "in_progress"
        self.last_update = datetime.now()
    
    def achieve_goal(self, achieved_value: Optional[float] = None, notes: Optional[str] = None) -> None:
        """Mark goal as achieved."""
        if self.status not in ["in_progress", "not_started"]:
            raise ValueError(f"Cannot achieve goal with status: {self.status}")
        
        self.status = "achieved"
        self.achieved_at = datetime.now()
        self.progress_percentage = 100
        
        if achieved_value is not None:
            self.achieved_value = achieved_value
        
        if notes:
            self.achievement_notes = notes
        
        # Calculate achievement rating based on target vs achieved
        if self.target_value and self.achieved_value:
            if self.achieved_value >= self.target_value:
                self.achievement_rating = 5.0  # Exceeded
            elif self.achieved_value >= (self.target_value * 0.9):
                self.achievement_rating = 4.0  # Met
            elif self.achieved_value >= (self.target_value * 0.7):
                self.achievement_rating = 3.0  # Partially met
            else:
                self.achievement_rating = 2.0  # Below target
        else:
            self.achievement_rating = 4.0  # Default for non-measurable goals
    
    def mark_not_achieved(self, reason: Optional[str] = None) -> None:
        """Mark goal as not achieved."""
        if self.status not in ["in_progress", "not_started"]:
            raise ValueError(f"Cannot mark goal as not achieved with status: {self.status}")
        
        self.status = "not_achieved"
        self.achievement_rating = 1.0
        
        if reason:
            self.achievement_notes = reason
    
    def update_progress(self, percentage: int, notes: Optional[str] = None, current_value: Optional[float] = None) -> None:
        """Update goal progress."""
        if not (0 <= percentage <= 100):
            raise ValueError("Progress percentage must be between 0 and 100")
        
        self.progress_percentage = percentage
        self.last_update = datetime.now()
        
        if notes:
            self.update_notes = notes
        
        if current_value is not None:
            self.current_value = current_value
        
        # Auto-start if not started
        if self.status == "not_started" and percentage > 0:
            self.status = "in_progress"
    
    def get_achievement_percentage(self) -> float:
        """Calculate achievement percentage based on target vs achieved."""
        if not self.target_value or not self.achieved_value:
            return 0.0
        
        return min(100.0, (self.achieved_value / self.target_value) * 100)
    
    def get_current_progress_percentage(self) -> float:
        """Calculate current progress percentage based on target vs current."""
        if not self.target_value or not self.current_value:
            return self.progress_percentage or 0.0
        
        return min(100.0, (self.current_value / self.target_value) * 100)
    
    def days_until_deadline(self) -> Optional[int]:
        """Get days until goal deadline."""
        if not self.time_bound_deadline:
            return None
        
        delta = self.time_bound_deadline - datetime.now()
        return max(0, delta.days)
    
    def get_priority_score(self) -> int:
        """Get numeric priority score for sorting."""
        priority_scores = {
            "high": 3,
            "medium": 2,
            "low": 1
        }
        return priority_scores.get(self.priority, 2)
    
    def get_status_label(self) -> str:
        """Get human-readable status label."""
        status_labels = {
            "not_started": "Not Started",
            "in_progress": "In Progress",
            "achieved": "Achieved",
            "not_achieved": "Not Achieved",
            "cancelled": "Cancelled"
        }
        return status_labels.get(self.status, self.status.title())
    
    def get_achievement_rating_label(self) -> str:
        """Get human-readable achievement rating label."""
        if not self.achievement_rating:
            return "Not Rated"
        
        if self.achievement_rating >= 4.5:
            return "Exceeded Expectations"
        elif self.achievement_rating >= 3.5:
            return "Met Expectations"
        elif self.achievement_rating >= 2.5:
            return "Partially Met"
        elif self.achievement_rating >= 1.5:
            return "Below Target"
        else:
            return "Not Achieved"
    
    def is_smart_complete(self) -> bool:
        """Check if all SMART criteria are defined."""
        return all([
            self.specific_description,
            self.measurable_criteria,
            self.achievable_plan,
            self.relevant_justification,
            self.time_bound_deadline
        ])
    
    def get_smart_score(self) -> Dict[str, bool]:
        """Get SMART criteria completion status."""
        return {
            "specific": bool(self.specific_description),
            "measurable": bool(self.measurable_criteria),
            "achievable": bool(self.achievable_plan),
            "relevant": bool(self.relevant_justification),
            "time_bound": bool(self.time_bound_deadline)
        }
    
    def to_dict_detailed(self) -> Dict[str, Any]:
        """Return detailed goal information."""
        return {
            "id": self.id,
            "performance_review_id": self.performance_review_id,
            "title": self.title,
            "description": self.description,
            "goal_type": self.goal_type,
            "category": self.category,
            "priority": self.priority,
            "priority_score": self.get_priority_score(),
            
            # SMART criteria
            "smart_criteria": {
                "specific_description": self.specific_description,
                "measurable_criteria": self.measurable_criteria,
                "achievable_plan": self.achievable_plan,
                "relevant_justification": self.relevant_justification,
                "time_bound_deadline": self.time_bound_deadline
            },
            "is_smart_complete": self.is_smart_complete(),
            "smart_score": self.get_smart_score(),
            
            # Targets and measurement
            "target_value": self.target_value,
            "target_unit": self.target_unit,
            "current_value": self.current_value,
            "achieved_value": self.achieved_value,
            "measurement_method": self.measurement_method,
            
            # Progress and status
            "status": self.status,
            "status_label": self.get_status_label(),
            "progress_percentage": self.progress_percentage,
            "current_progress_percentage": self.get_current_progress_percentage(),
            "achievement_percentage": self.get_achievement_percentage(),
            "is_overdue": self.is_overdue(),
            "days_until_deadline": self.days_until_deadline(),
            
            # Achievement
            "achievement_rating": self.achievement_rating,
            "achievement_rating_label": self.get_achievement_rating_label(),
            "achieved_at": self.achieved_at,
            "achievement_notes": self.achievement_notes,
            
            # Support and resources
            "required_resources": self.required_resources,
            "support_needed": self.support_needed,
            "obstacles": self.obstacles,
            
            # Weight and contribution
            "weight": self.weight,
            "contributes_to_rating": self.contributes_to_rating,
            
            # Updates
            "milestones": self.milestones,
            "last_update": self.last_update,
            "update_notes": self.update_notes,
            
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }