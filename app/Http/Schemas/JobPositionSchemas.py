from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
import re


class EmploymentType(str, Enum):
    """Employment type enumeration."""
    FULL_TIME = "full-time"
    PART_TIME = "part-time"
    CONTRACT = "contract"
    INTERN = "intern"
    CONSULTANT = "consultant"


class PositionStatus(str, Enum):
    """Position status enumeration."""
    ACTIVE = "active"
    RECRUITING = "recruiting"
    ON_HOLD = "on-hold"
    CLOSED = "closed"
    FILLED = "filled"


class PriorityLevel(str, Enum):
    """Priority level enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TravelRequirement(str, Enum):
    """Travel requirement enumeration."""
    NONE = "none"
    MINIMAL = "minimal"
    MODERATE = "moderate"
    FREQUENT = "frequent"


class CollaborationLevel(str, Enum):
    """Collaboration level enumeration."""
    INDIVIDUAL = "individual"
    TEAM = "team"
    CROSS_TEAM = "cross-team"
    ORGANIZATION = "organization"


class CareerTrack(str, Enum):
    """Career track enumeration."""
    TECHNICAL = "technical"
    MANAGEMENT = "management"
    SPECIALIZED = "specialized"


class CreateJobPositionRequest(BaseModel):
    """Create job position request schema."""
    
    title: str = Field(..., min_length=1, max_length=255, description="Position title")
    code: str = Field(..., min_length=2, max_length=50, description="Position code")
    description: Optional[str] = Field(None, max_length=2000, description="Position description")
    department_id: int = Field(..., description="Department ID")
    job_level_id: int = Field(..., description="Job level ID")
    
    # Basic position details
    employment_type: EmploymentType = Field(EmploymentType.FULL_TIME, description="Employment type")
    status: PositionStatus = Field(PositionStatus.ACTIVE, description="Position status")
    max_headcount: Optional[int] = Field(1, ge=1, description="Maximum headcount")
    is_remote_allowed: bool = Field(False, description="Remote work allowed")
    is_hybrid_allowed: bool = Field(True, description="Hybrid work allowed")
    
    # Reporting structure
    reports_to_position_id: Optional[int] = Field(None, description="Reports to position ID")
    
    # Job details
    responsibilities: Optional[str] = Field(None, description="Job responsibilities")
    requirements: Optional[str] = Field(None, description="Job requirements")
    qualifications: Optional[str] = Field(None, description="Required qualifications")
    
    # Recruitment and hiring
    job_posting_url: Optional[str] = Field(None, max_length=500, description="Job posting URL")
    application_deadline: Optional[datetime] = Field(None, description="Application deadline")
    priority_level: PriorityLevel = Field(PriorityLevel.MEDIUM, description="Priority level")
    
    # Performance and evaluation
    performance_goals: Optional[List[Dict[str, Any]]] = Field(None, description="Performance goals")
    success_metrics: Optional[List[Dict[str, Any]]] = Field(None, description="Success metrics")
    review_template_id: Optional[int] = Field(None, description="Review template ID")
    
    # Work environment and conditions
    travel_requirement: Optional[TravelRequirement] = Field(None, description="Travel requirement")
    security_clearance_required: bool = Field(False, description="Security clearance required")
    physical_requirements: Optional[str] = Field(None, description="Physical requirements")
    work_environment: Optional[str] = Field(None, max_length=50, description="Work environment")
    
    # Collaboration and team
    team_size_managed: Optional[int] = Field(None, ge=0, description="Team size managed")
    stakeholder_groups: Optional[List[str]] = Field(None, description="Stakeholder groups")
    collaboration_level: CollaborationLevel = Field(CollaborationLevel.TEAM, description="Collaboration level")
    
    # Budget and financial responsibility
    budget_responsibility: Optional[float] = Field(None, ge=0, description="Budget responsibility")
    revenue_responsibility: Optional[float] = Field(None, ge=0, description="Revenue responsibility")
    can_approve_expenses: bool = Field(False, description="Can approve expenses")
    expense_approval_limit: Optional[float] = Field(None, ge=0, description="Expense approval limit")
    
    # Career development
    career_track: Optional[CareerTrack] = Field(None, description="Career track")
    growth_opportunities: Optional[List[str]] = Field(None, description="Growth opportunities")
    mentorship_available: bool = Field(False, description="Mentorship available")
    
    # Tags and categorization
    tags: Optional[List[str]] = Field(None, description="Position tags")
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not re.match(r'^[A-Z0-9_-]+$', v):
            raise ValueError('Position code must contain only uppercase letters, numbers, underscores, and hyphens')
        return v
    
    @field_validator('job_posting_url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^https?://.+', v):
            raise ValueError('Job posting URL must be a valid HTTP/HTTPS URL')
        return v


class UpdateJobPositionRequest(BaseModel):
    """Update job position request schema."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    employment_type: Optional[EmploymentType] = Field(None)
    status: Optional[PositionStatus] = Field(None)
    max_headcount: Optional[int] = Field(None, ge=1)
    is_remote_allowed: Optional[bool] = Field(None)
    is_hybrid_allowed: Optional[bool] = Field(None)
    reports_to_position_id: Optional[int] = Field(None)
    responsibilities: Optional[str] = Field(None)
    requirements: Optional[str] = Field(None)
    qualifications: Optional[str] = Field(None)
    job_posting_url: Optional[str] = Field(None, max_length=500)
    application_deadline: Optional[datetime] = Field(None)
    priority_level: Optional[PriorityLevel] = Field(None)
    performance_goals: Optional[List[Dict[str, Any]]] = Field(None)
    success_metrics: Optional[List[Dict[str, Any]]] = Field(None)
    review_template_id: Optional[int] = Field(None)
    travel_requirement: Optional[TravelRequirement] = Field(None)
    security_clearance_required: Optional[bool] = Field(None)
    physical_requirements: Optional[str] = Field(None)
    work_environment: Optional[str] = Field(None, max_length=50)
    team_size_managed: Optional[int] = Field(None, ge=0)
    stakeholder_groups: Optional[List[str]] = Field(None)
    collaboration_level: Optional[CollaborationLevel] = Field(None)
    budget_responsibility: Optional[float] = Field(None, ge=0)
    revenue_responsibility: Optional[float] = Field(None, ge=0)
    can_approve_expenses: Optional[bool] = Field(None)
    expense_approval_limit: Optional[float] = Field(None, ge=0)
    career_track: Optional[CareerTrack] = Field(None)
    growth_opportunities: Optional[List[str]] = Field(None)
    mentorship_available: Optional[bool] = Field(None)
    tags: Optional[List[str]] = Field(None)


class RecruitmentDetailsRequest(BaseModel):
    """Recruitment details update request schema."""
    
    job_posting_url: Optional[str] = Field(None, max_length=500, description="Job posting URL")
    application_deadline: Optional[datetime] = Field(None, description="Application deadline")
    priority_level: Optional[PriorityLevel] = Field(None, description="Priority level")
    
    @field_validator('job_posting_url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^https?://.+', v):
            raise ValueError('Job posting URL must be a valid HTTP/HTTPS URL')
        return v


class WorkEnvironmentRequest(BaseModel):
    """Work environment update request schema."""
    
    travel_requirement: Optional[TravelRequirement] = Field(None, description="Travel requirement")
    security_clearance_required: Optional[bool] = Field(None, description="Security clearance required")
    physical_requirements: Optional[str] = Field(None, description="Physical requirements")
    work_environment: Optional[str] = Field(None, max_length=50, description="Work environment")


class FinancialResponsibilityRequest(BaseModel):
    """Financial responsibility update request schema."""
    
    budget_responsibility: Optional[float] = Field(None, ge=0, description="Budget responsibility")
    revenue_responsibility: Optional[float] = Field(None, ge=0, description="Revenue responsibility")
    can_approve_expenses: Optional[bool] = Field(None, description="Can approve expenses")
    expense_approval_limit: Optional[float] = Field(None, ge=0, description="Expense approval limit")


class TeamCollaborationRequest(BaseModel):
    """Team collaboration update request schema."""
    
    team_size_managed: Optional[int] = Field(None, ge=0, description="Team size managed")
    stakeholder_groups: Optional[List[str]] = Field(None, description="Stakeholder groups")
    collaboration_level: Optional[CollaborationLevel] = Field(None, description="Collaboration level")


class CareerDevelopmentRequest(BaseModel):
    """Career development update request schema."""
    
    career_track: Optional[CareerTrack] = Field(None, description="Career track")
    growth_opportunities: Optional[List[str]] = Field(None, description="Growth opportunities")
    mentorship_available: Optional[bool] = Field(None, description="Mentorship available")


class PerformanceGoalsRequest(BaseModel):
    """Performance goals update request schema."""
    
    performance_goals: Optional[List[Dict[str, Any]]] = Field(None, description="Performance goals")
    success_metrics: Optional[List[Dict[str, Any]]] = Field(None, description="Success metrics")
    review_template_id: Optional[int] = Field(None, description="Review template ID")
    
    @field_validator('performance_goals', 'success_metrics')
    @classmethod
    def validate_goals_metrics(cls, v: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        if v:
            for item in v:
                if 'name' not in item or not item['name']:
                    raise ValueError('Each goal/metric must have a name')
                if 'target_value' in item and item['target_value'] is not None:
                    if not isinstance(item['target_value'], (int, float)):
                        raise ValueError('Target value must be a number')
        return v


class JobPositionResponse(BaseModel):
    """Job position response schema."""
    
    id: int
    title: str
    code: str
    description: Optional[str]
    department_id: int
    job_level_id: int
    employment_type: str
    status: str
    max_headcount: Optional[int]
    is_remote_allowed: bool
    is_hybrid_allowed: bool
    reports_to_position_id: Optional[int]
    priority_level: str
    travel_requirement: Optional[str]
    security_clearance_required: bool
    career_track: Optional[str]
    mentorship_available: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime