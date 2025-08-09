from __future__ import annotations

from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, Text, Integer
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Models.JobPosition import JobPosition
    from app.Models.PerformanceReviewCycle import PerformanceReviewCycle
    from app.Models.PerformanceGoal import PerformanceGoal
    from app.Models.PerformanceCompetency import PerformanceCompetency


class PerformanceReview(BaseModel, LogsActivityMixin):
    """
    Performance review model for tracking employee evaluations.
    Supports multiple review types, competency assessments, and goal tracking.
    """
    __tablename__ = "performance_reviews"
    
    # Basic review information
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),  # type: ignore[arg-type]
        nullable=False, 
        index=True
    )
    reviewer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),  # type: ignore[arg-type]
        nullable=False, 
        index=True
    )
    review_cycle_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("performance_review_cycles.id"),  # type: ignore[arg-type]
        nullable=True, 
        index=True
    )
    job_position_id: Mapped[int] = mapped_column(
        ForeignKey("job_positions.id"),  # type: ignore[arg-type]
        nullable=False, 
        index=True
    )
    
    # Review details
    review_type: Mapped[str] = mapped_column(nullable=False, index=True)  # annual, mid_year, probation, project, 360
    review_period_start: Mapped[datetime] = mapped_column(nullable=False)
    review_period_end: Mapped[datetime] = mapped_column(nullable=False)
    
    # Status and workflow
    status: Mapped[str] = mapped_column(default="draft", nullable=False, index=True)  # draft, submitted, under_review, completed, cancelled
    submitted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Overall ratings and scores
    overall_rating: Mapped[Optional[float]] = mapped_column(nullable=True)  # 1.0 to 5.0 scale
    performance_score: Mapped[Optional[int]] = mapped_column(nullable=True)  # Percentage score
    meets_expectations: Mapped[Optional[bool]] = mapped_column(nullable=True)
    
    # Review content
    achievements: Mapped[Optional[str]] = mapped_column( nullable=True)
    areas_for_improvement: Mapped[Optional[str]] = mapped_column( nullable=True)
    strengths: Mapped[Optional[str]] = mapped_column( nullable=True)
    development_needs: Mapped[Optional[str]] = mapped_column( nullable=True)
    career_aspirations: Mapped[Optional[str]] = mapped_column( nullable=True)
    
    # Reviewer feedback
    reviewer_comments: Mapped[Optional[str]] = mapped_column( nullable=True)
    recommendations: Mapped[Optional[str]] = mapped_column( nullable=True)
    promotion_readiness: Mapped[Optional[str]] = mapped_column(nullable=True)  # ready, developing, not_ready
    
    # Employee self-assessment
    self_assessment: Mapped[Optional[str]] = mapped_column( nullable=True)
    self_rating: Mapped[Optional[float]] = mapped_column( nullable=True)
    employee_comments: Mapped[Optional[str]] = mapped_column( nullable=True)
    
    # Action items and development
    action_items: Mapped[Optional[str]] = mapped_column( nullable=True)  # JSON array
    development_plan: Mapped[Optional[str]] = mapped_column( nullable=True)
    training_recommendations: Mapped[Optional[str]] = mapped_column( nullable=True)
    
    # Next review
    next_review_date: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    review_frequency_months: Mapped[Optional[int]] = mapped_column( nullable=True)
    
    # Manager and HR sign-off
    manager_approved: Mapped[bool] = mapped_column( default=False, nullable=False)
    manager_approved_at: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    manager_approved_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),  # type: ignore[arg-type]
        nullable=True
    )
    
    hr_approved: Mapped[bool] = mapped_column(default=False, nullable=False)
    hr_approved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    hr_approved_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),  # type: ignore[arg-type]
        nullable=True
    )
    
    # Employee acknowledgment
    employee_acknowledged: Mapped[bool] = mapped_column( default=False, nullable=False)
    employee_acknowledged_at: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    employee_signature: Mapped[Optional[str]] = mapped_column(nullable=True)  # Digital signature
    
    # Additional metadata
    is_calibrated: Mapped[bool] = mapped_column( default=False, nullable=False)
    calibration_session_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Relationships
    employee: Mapped["User"] = relationship("User", foreign_keys=[employee_id])
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id])
    manager_approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[manager_approved_by_id])
    hr_approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[hr_approved_by_id])
    
    job_position: Mapped["JobPosition"] = relationship("JobPosition")
    review_cycle: Mapped[Optional["PerformanceReviewCycle"]] = relationship("PerformanceReviewCycle", back_populates="reviews")
    
    # Performance goals and competencies (one-to-many relationships)
    goals: Mapped[List["PerformanceGoal"]] = relationship(
        "PerformanceGoal", back_populates="performance_review", cascade="all, delete-orphan"
    )
    competency_assessments: Mapped[List["PerformanceCompetency"]] = relationship(
        "PerformanceCompetency", back_populates="performance_review", cascade="all, delete-orphan"
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for PerformanceReview model."""
        return LogOptions(
            log_name="performance_reviews",
            log_attributes=["employee_id", "reviewer_id", "status", "overall_rating", "review_type"],
            description_for_event={
                "created": "Performance review created",
                "updated": "Performance review updated", 
                "deleted": "Performance review deleted"
            }
        )
    
    def is_draft(self) -> bool:
        """Check if review is in draft status."""
        return self.status == "draft"
    
    def is_submitted(self) -> bool:
        """Check if review has been submitted."""
        return self.status == "submitted"
    
    def is_under_review(self) -> bool:
        """Check if review is under review."""
        return self.status == "under_review"
    
    def is_completed(self) -> bool:
        """Check if review is completed."""
        return self.status == "completed"
    
    def is_overdue(self) -> bool:
        """Check if review is overdue."""
        if not self.due_date:
            return False
        return datetime.now() > self.due_date and not self.is_completed()
    
    def submit_review(self) -> None:
        """Submit the review for approval."""
        if self.status != "draft":
            raise ValueError(f"Cannot submit review with status: {self.status}")
        
        self.status = "submitted"
        self.submitted_at = datetime.now()
    
    def start_review_process(self) -> None:
        """Start the review process."""
        if self.status != "submitted":
            raise ValueError(f"Cannot start review process with status: {self.status}")
        
        self.status = "under_review"
    
    def complete_review(self) -> None:
        """Mark review as completed."""
        if not self.manager_approved or not self.hr_approved:
            raise ValueError("Review must be approved by manager and HR before completion")
        
        self.status = "completed"
        self.completed_at = datetime.now()
        
        # Update next review date
        if self.review_frequency_months:
            self.next_review_date = datetime.now().replace(
                month=datetime.now().month + self.review_frequency_months
            )
    
    def approve_as_manager(self, manager_id: int) -> None:
        """Approve review as manager."""
        self.manager_approved = True
        self.manager_approved_at = datetime.now()
        self.manager_approved_by_id = manager_id
    
    def approve_as_hr(self, hr_id: int) -> None:
        """Approve review as HR."""
        self.hr_approved = True
        self.hr_approved_at = datetime.now()
        self.hr_approved_by_id = hr_id
    
    def acknowledge_as_employee(self, signature: Optional[str] = None) -> None:
        """Employee acknowledgment of review."""
        self.employee_acknowledged = True
        self.employee_acknowledged_at = datetime.now()
        if signature:
            self.employee_signature = signature
    
    def calculate_overall_rating(self) -> float:
        """Calculate overall rating based on competencies and goals."""
        ratings = []
        
        # Include competency ratings
        for comp in self.competency_assessments:
            if comp.rating:
                ratings.append(comp.rating)
        
        # Include goal achievement ratings
        for goal in self.goals:
            if goal.achievement_rating:
                ratings.append(goal.achievement_rating)
        
        if not ratings:
            return 0.0
        
        overall = float(sum(ratings) / len(ratings))
        self.overall_rating = overall
        return overall
    
    def get_competency_average(self) -> float:
        """Get average competency rating."""
        ratings = [c.rating for c in self.competency_assessments if c.rating]
        return float(sum(ratings) / len(ratings)) if ratings else 0.0
    
    def get_goals_achievement_rate(self) -> float:
        """Get percentage of goals achieved."""
        if not self.goals:
            return 0.0
        
        achieved = len([g for g in self.goals if g.is_achieved()])
        return (achieved / len(self.goals)) * 100
    
    def get_review_progress(self) -> Dict[str, Any]:
        """Get review completion progress."""
        progress = {
            "self_assessment_complete": bool(self.self_assessment),
            "goals_set": len(self.goals) > 0,
            "competencies_assessed": len(self.competency_assessments) > 0,
            "reviewer_feedback_complete": bool(self.reviewer_comments),
            "manager_approved": self.manager_approved,
            "hr_approved": self.hr_approved,
            "employee_acknowledged": self.employee_acknowledged
        }
        
        completed_steps = sum(progress.values())
        total_steps = len(progress)
        
        return {
            **progress,
            "completion_percentage": (completed_steps / total_steps) * 100,
            "completed_steps": completed_steps,
            "total_steps": total_steps
        }
    
    def get_rating_label(self) -> str:
        """Get human-readable rating label."""
        if not self.overall_rating:
            return "Not Rated"
        
        if self.overall_rating >= 4.5:
            return "Exceptional"
        elif self.overall_rating >= 3.5:
            return "Exceeds Expectations"
        elif self.overall_rating >= 2.5:
            return "Meets Expectations"
        elif self.overall_rating >= 1.5:
            return "Below Expectations"
        else:
            return "Does Not Meet Expectations"
    
    def days_until_due(self) -> Optional[int]:
        """Get days until review is due."""
        if not self.due_date:
            return None
        
        delta = self.due_date - datetime.now()
        return max(0, delta.days)
    
    def get_review_timeline(self) -> List[Dict[str, Any]]:
        """Get review timeline with key milestones."""
        timeline = []
        
        timeline.append({
            "event": "Review Created",
            "date": self.created_at,
            "status": "completed"
        })
        
        if self.submitted_at:
            timeline.append({
                "event": "Review Submitted",
                "date": self.submitted_at,
                "status": "completed"
            })
        
        if self.manager_approved_at:
            timeline.append({
                "event": "Manager Approval",
                "date": self.manager_approved_at,
                "status": "completed"
            })
        
        if self.hr_approved_at:
            timeline.append({
                "event": "HR Approval",
                "date": self.hr_approved_at,
                "status": "completed"
            })
        
        if self.employee_acknowledged_at:
            timeline.append({
                "event": "Employee Acknowledgment",
                "date": self.employee_acknowledged_at,
                "status": "completed"
            })
        
        if self.completed_at:
            timeline.append({
                "event": "Review Completed",
                "date": self.completed_at,
                "status": "completed"
            })
        
        return sorted(timeline, key=lambda x: x["date"])
    
    def to_dict_detailed(self) -> Dict[str, Any]:
        """Return detailed review information."""
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "employee_name": self.employee.name,
            "employee_email": self.employee.email,
            "reviewer_id": self.reviewer_id,
            "reviewer_name": self.reviewer.name,
            "job_position_title": self.job_position.title,
            "review_type": self.review_type,
            "status": self.status,
            
            # Dates
            "review_period_start": self.review_period_start,
            "review_period_end": self.review_period_end,
            "due_date": self.due_date,
            "submitted_at": self.submitted_at,
            "completed_at": self.completed_at,
            "days_until_due": self.days_until_due(),
            "is_overdue": self.is_overdue(),
            
            # Ratings and assessments
            "overall_rating": self.overall_rating,
            "rating_label": self.get_rating_label(),
            "performance_score": self.performance_score,
            "meets_expectations": self.meets_expectations,
            "self_rating": self.self_rating,
            "competency_average": self.get_competency_average(),
            "goals_achievement_rate": self.get_goals_achievement_rate(),
            
            # Content
            "achievements": self.achievements,
            "areas_for_improvement": self.areas_for_improvement,
            "strengths": self.strengths,
            "development_needs": self.development_needs,
            "career_aspirations": self.career_aspirations,
            "reviewer_comments": self.reviewer_comments,
            "recommendations": self.recommendations,
            "promotion_readiness": self.promotion_readiness,
            "self_assessment": self.self_assessment,
            "employee_comments": self.employee_comments,
            
            # Development and goals
            "goals_count": len(self.goals),
            "competencies_count": len(self.competency_assessments),
            "action_items": self.action_items,
            "development_plan": self.development_plan,
            "training_recommendations": self.training_recommendations,
            
            # Approvals
            "manager_approved": self.manager_approved,
            "manager_approved_at": self.manager_approved_at,
            "hr_approved": self.hr_approved,
            "hr_approved_at": self.hr_approved_at,
            "employee_acknowledged": self.employee_acknowledged,
            "employee_acknowledged_at": self.employee_acknowledged_at,
            
            # Progress and timeline
            "progress": self.get_review_progress(),
            "timeline": self.get_review_timeline(),
            
            # Next review
            "next_review_date": self.next_review_date,
            "review_frequency_months": self.review_frequency_months,
            
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }