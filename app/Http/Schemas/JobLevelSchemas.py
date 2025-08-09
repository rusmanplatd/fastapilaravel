from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import re


class BenefitTier(str, Enum):
    """Benefit tier enumeration."""
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    EXECUTIVE = "executive"


class CreateJobLevelRequest(BaseModel):
    """Create job level request schema."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Job level name")
    code: str = Field(..., min_length=2, max_length=50, description="Job level code")
    description: Optional[str] = Field(None, max_length=2000, description="Job level description")
    level_order: int = Field(..., ge=1, description="Level order (1=lowest)")
    
    # Authority and management
    is_management: bool = Field(False, description="Is management level")
    is_executive: bool = Field(False, description="Is executive level")
    can_approve_budget: bool = Field(False, description="Can approve budget")
    can_hire: bool = Field(False, description="Can hire employees")
    
    # Salary and experience
    min_salary: Optional[float] = Field(None, ge=0, description="Minimum salary")
    max_salary: Optional[float] = Field(None, ge=0, description="Maximum salary")
    min_experience_years: Optional[int] = Field(None, ge=0, description="Minimum experience years")
    max_experience_years: Optional[int] = Field(None, ge=0, description="Maximum experience years")
    
    # Career progression
    next_level_id: Optional[int] = Field(None, description="Next level in progression")
    previous_level_id: Optional[int] = Field(None, description="Previous level in progression")
    promotion_requirements: Optional[Dict[str, Any]] = Field(None, description="Promotion requirements")
    
    # Competency framework
    required_competencies: Optional[List[Dict[str, Any]]] = Field(None, description="Required competencies")
    preferred_competencies: Optional[List[Dict[str, Any]]] = Field(None, description="Preferred competencies")
    leadership_competencies: Optional[List[Dict[str, Any]]] = Field(None, description="Leadership competencies")
    
    # Performance and review
    performance_rating_scale: Optional[Dict[str, Any]] = Field(None, description="Performance rating scale")
    review_frequency_months: Optional[int] = Field(None, ge=1, le=12, description="Review frequency in months")
    
    # Benefits and perks
    benefit_tier: Optional[BenefitTier] = Field(None, description="Benefit tier")
    vacation_days: Optional[int] = Field(None, ge=0, description="Vacation days")
    sick_days: Optional[int] = Field(None, ge=0, description="Sick days")
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not re.match(r'^[A-Z0-9_-]+$', v):
            raise ValueError('Job level code must contain only uppercase letters, numbers, underscores, and hyphens')
        return v
    
    @field_validator('min_salary', 'max_salary')
    @classmethod
    def validate_salary_range(cls, v: Optional[float], info: ValidationInfo) -> Optional[float]:
        if v is not None and info.data:
            if 'min_salary' in info.data and 'max_salary' in info.data:
                min_sal = info.data.get('min_salary')
                max_sal = info.data.get('max_salary')
                if min_sal is not None and max_sal is not None and min_sal > max_sal:
                    raise ValueError('Minimum salary cannot be greater than maximum salary')
        return v


class UpdateJobLevelRequest(BaseModel):
    """Update job level request schema."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    level_order: Optional[int] = Field(None, ge=1)
    is_management: Optional[bool] = Field(None)
    is_executive: Optional[bool] = Field(None)
    can_approve_budget: Optional[bool] = Field(None)
    can_hire: Optional[bool] = Field(None)
    min_salary: Optional[float] = Field(None, ge=0)
    max_salary: Optional[float] = Field(None, ge=0)
    min_experience_years: Optional[int] = Field(None, ge=0)
    max_experience_years: Optional[int] = Field(None, ge=0)
    next_level_id: Optional[int] = Field(None)
    previous_level_id: Optional[int] = Field(None)
    promotion_requirements: Optional[Dict[str, Any]] = Field(None)
    required_competencies: Optional[List[Dict[str, Any]]] = Field(None)
    preferred_competencies: Optional[List[Dict[str, Any]]] = Field(None)
    leadership_competencies: Optional[List[Dict[str, Any]]] = Field(None)
    performance_rating_scale: Optional[Dict[str, Any]] = Field(None)
    review_frequency_months: Optional[int] = Field(None, ge=1, le=12)
    benefit_tier: Optional[BenefitTier] = Field(None)
    vacation_days: Optional[int] = Field(None, ge=0)
    sick_days: Optional[int] = Field(None, ge=0)


class CompetencyFrameworkRequest(BaseModel):
    """Competency framework update request schema."""
    
    required_competencies: Optional[List[Dict[str, Any]]] = Field(None, description="Required competencies")
    preferred_competencies: Optional[List[Dict[str, Any]]] = Field(None, description="Preferred competencies")
    leadership_competencies: Optional[List[Dict[str, Any]]] = Field(None, description="Leadership competencies")
    
    @field_validator('required_competencies', 'preferred_competencies', 'leadership_competencies')
    @classmethod
    def validate_competencies(cls, v: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        if v:
            for competency in v:
                if 'name' not in competency or not competency['name']:
                    raise ValueError('Each competency must have a name')
                if 'level' in competency and competency['level'] not in ['beginner', 'intermediate', 'advanced', 'expert']:
                    raise ValueError('Competency level must be one of: beginner, intermediate, advanced, expert')
        return v


class BenefitPackageRequest(BaseModel):
    """Benefit package update request schema."""
    
    benefit_tier: Optional[BenefitTier] = Field(None, description="Benefit tier")
    vacation_days: Optional[int] = Field(None, ge=0, le=365, description="Vacation days")
    sick_days: Optional[int] = Field(None, ge=0, le=365, description="Sick days")


class JobLevelResponse(BaseModel):
    """Job level response schema."""
    
    id: int
    name: str
    code: str
    description: Optional[str]
    level_order: int
    is_management: bool
    is_executive: bool
    can_approve_budget: bool
    can_hire: bool
    min_salary: Optional[float]
    max_salary: Optional[float]
    min_experience_years: Optional[int]
    max_experience_years: Optional[int]
    benefit_tier: Optional[str]
    vacation_days: Optional[int]
    sick_days: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime