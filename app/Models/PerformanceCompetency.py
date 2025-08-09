from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.PerformanceReview import PerformanceReview


class PerformanceCompetency(BaseModel, LogsActivityMixin):
    """
    Performance competency assessment model for evaluating specific skills and behaviors.
    Supports behavioral indicators and competency frameworks.
    """
    __tablename__ = "performance_competencies"
    
    # Competency identification
    performance_review_id: Mapped[int] = mapped_column(
        ForeignKey("performance_reviews.id"),  # type: ignore[arg-type]
        nullable=False, 
        index=True
    )
    competency_name: Mapped[str] = mapped_column(nullable=False, index=True)
    competency_category: Mapped[str] = mapped_column(nullable=False, index=True)  # technical, leadership, communication, etc.
    
    # Competency definition
    description: Mapped[str] = mapped_column( nullable=False)
    behavioral_indicators: Mapped[Optional[str]] = mapped_column( nullable=True)  # JSON array of indicators
    expected_level: Mapped[str] = mapped_column(nullable=False)  # beginner, intermediate, advanced, expert
    
    # Assessment
    rating: Mapped[Optional[float]] = mapped_column( nullable=True)  # 1.0 to 5.0 scale
    self_rating: Mapped[Optional[float]] = mapped_column( nullable=True)  # Employee self-assessment
    
    # Evidence and feedback
    evidence_provided: Mapped[Optional[str]] = mapped_column( nullable=True)
    examples_of_demonstration: Mapped[Optional[str]] = mapped_column( nullable=True)
    areas_for_improvement: Mapped[Optional[str]] = mapped_column( nullable=True)
    
    # Development planning
    development_actions: Mapped[Optional[str]] = mapped_column( nullable=True)
    training_recommendations: Mapped[Optional[str]] = mapped_column( nullable=True)
    mentoring_needs: Mapped[Optional[str]] = mapped_column( nullable=True)
    target_proficiency_date: Mapped[Optional[datetime]] = mapped_column( nullable=True)
    
    # Weight and importance
    weight: Mapped[float] = mapped_column( default=1.0, nullable=False)
    is_core_competency: Mapped[bool] = mapped_column( default=False, nullable=False)
    is_role_critical: Mapped[bool] = mapped_column( default=False, nullable=False)
    
    # Assessment metadata
    assessment_method: Mapped[Optional[str]] = mapped_column(nullable=True)  # observation, project_review, 360_feedback, etc.
    assessor_notes: Mapped[Optional[str]] = mapped_column( nullable=True)
    peer_feedback: Mapped[Optional[str]] = mapped_column( nullable=True)
    
    # Progress tracking
    previous_rating: Mapped[Optional[float]] = mapped_column( nullable=True)
    improvement_noted: Mapped[bool] = mapped_column( default=False, nullable=False)
    
    # Relationships
    performance_review: Mapped[PerformanceReview] = relationship("PerformanceReview", back_populates="competency_assessments")
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for PerformanceCompetency model."""
        return LogOptions(
            log_name="performance_competencies",
            log_attributes=["performance_review_id", "competency_name", "rating", "self_rating"],
            description_for_event={
                "created": "Performance competency assessment created",
                "updated": "Performance competency assessment updated", 
                "deleted": "Performance competency assessment deleted"
            }
        )
    
    def get_rating_label(self) -> str:
        """Get human-readable rating label."""
        if not self.rating:
            return "Not Rated"
        
        if self.rating >= 4.5:
            return "Exceptional"
        elif self.rating >= 3.5:
            return "Proficient"
        elif self.rating >= 2.5:
            return "Developing"
        elif self.rating >= 1.5:
            return "Needs Improvement"
        else:
            return "Unsatisfactory"
    
    def get_expected_level_score(self) -> int:
        """Get numeric score for expected level."""
        level_scores = {
            "beginner": 1,
            "intermediate": 2,
            "advanced": 3,
            "expert": 4
        }
        return level_scores.get(self.expected_level, 2)
    
    def is_meeting_expectations(self) -> bool:
        """Check if competency rating meets the expected level."""
        if not self.rating:
            return False
        
        expected_score = self.get_expected_level_score()
        # Map expected level to minimum rating threshold
        thresholds = {1: 2.0, 2: 3.0, 3: 4.0, 4: 4.5}
        return self.rating >= thresholds.get(expected_score, 3.0)
    
    def get_development_priority(self) -> str:
        """Get development priority based on importance and rating."""
        if self.is_role_critical and not self.is_meeting_expectations():
            return "urgent"
        elif self.is_core_competency and not self.is_meeting_expectations():
            return "high"
        elif not self.is_meeting_expectations():
            return "medium"
        else:
            return "low"
    
    def get_rating_variance(self) -> Optional[float]:
        """Get variance between self-rating and manager rating."""
        if not self.rating or not self.self_rating:
            return None
        return self.rating - self.self_rating
    
    def get_improvement_trend(self) -> Optional[str]:
        """Get improvement trend compared to previous assessment."""
        if not self.rating or not self.previous_rating:
            return None
        
        difference = self.rating - self.previous_rating
        if difference > 0.5:
            return "significant_improvement"
        elif difference > 0:
            return "improvement"
        elif difference == 0:
            return "no_change"
        elif difference > -0.5:
            return "slight_decline"
        else:
            return "significant_decline"
    
    def needs_development(self) -> bool:
        """Check if competency needs development focus."""
        return (
            not self.is_meeting_expectations() or
            (self.rating is not None and self.rating < 3.5) or
            (self.is_role_critical and self.rating is not None and self.rating < 4.0)
        )
    
    def calculate_weighted_score(self) -> float:
        """Calculate weighted score for overall review."""
        if not self.rating:
            return 0.0
        return self.rating * self.weight
    
    def get_proficiency_gap(self) -> Dict[str, Any]:
        """Analyze gap between current and expected proficiency."""
        if not self.rating:
            return {"gap_exists": True, "gap_size": "unknown", "action_needed": "assessment_required"}
        
        expected_score = self.get_expected_level_score()
        # Map expected levels to minimum ratings
        expected_rating_map = {1: 2.0, 2: 3.0, 3: 4.0, 4: 4.5}
        expected_min_rating = expected_rating_map.get(expected_score, 3.0)
        
        gap = expected_min_rating - self.rating
        
        if gap <= 0:
            return {
                "gap_exists": False,
                "gap_size": 0,
                "status": "meets_or_exceeds",
                "action_needed": "maintain_performance"
            }
        elif gap <= 0.5:
            return {
                "gap_exists": True,
                "gap_size": gap,
                "status": "minor_gap",
                "action_needed": "focused_development"
            }
        elif gap <= 1.0:
            return {
                "gap_exists": True,
                "gap_size": gap,
                "status": "moderate_gap",
                "action_needed": "structured_development_plan"
            }
        else:
            return {
                "gap_exists": True,
                "gap_size": gap,
                "status": "significant_gap",
                "action_needed": "intensive_development_required"
            }
    
    def to_dict_detailed(self) -> Dict[str, Any]:
        """Return detailed competency assessment information."""
        return {
            "id": self.id,
            "performance_review_id": self.performance_review_id,
            "competency_name": self.competency_name,
            "competency_category": self.competency_category,
            "description": self.description,
            "behavioral_indicators": self.behavioral_indicators,
            
            # Expected vs actual performance
            "expected_level": self.expected_level,
            "expected_level_score": self.get_expected_level_score(),
            "rating": self.rating,
            "rating_label": self.get_rating_label(),
            "self_rating": self.self_rating,
            "is_meeting_expectations": self.is_meeting_expectations(),
            
            # Analysis
            "rating_variance": self.get_rating_variance(),
            "improvement_trend": self.get_improvement_trend(),
            "development_priority": self.get_development_priority(),
            "proficiency_gap": self.get_proficiency_gap(),
            "needs_development": self.needs_development(),
            
            # Evidence and feedback
            "evidence_provided": self.evidence_provided,
            "examples_of_demonstration": self.examples_of_demonstration,
            "areas_for_improvement": self.areas_for_improvement,
            "assessor_notes": self.assessor_notes,
            "peer_feedback": self.peer_feedback,
            
            # Development planning
            "development_actions": self.development_actions,
            "training_recommendations": self.training_recommendations,
            "mentoring_needs": self.mentoring_needs,
            "target_proficiency_date": self.target_proficiency_date,
            
            # Importance and weight
            "weight": self.weight,
            "weighted_score": self.calculate_weighted_score(),
            "is_core_competency": self.is_core_competency,
            "is_role_critical": self.is_role_critical,
            
            # Assessment details
            "assessment_method": self.assessment_method,
            "previous_rating": self.previous_rating,
            "improvement_noted": self.improvement_noted,
            
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }