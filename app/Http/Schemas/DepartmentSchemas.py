from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
import re


class DepartmentStatus(str, Enum):
    """Department status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    RESTRUCTURING = "restructuring"
    MERGING = "merging"


class RemoteWorkPolicy(str, Enum):
    """Remote work policy enumeration."""
    ON_SITE = "on-site"
    HYBRID = "hybrid"
    REMOTE = "remote"


class CreateDepartmentRequest(BaseModel):
    """Create department request schema."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Department name")
    code: str = Field(..., min_length=2, max_length=50, description="Department code")
    description: Optional[str] = Field(None, max_length=2000, description="Department description")
    organization_id: int = Field(..., description="Organization ID")
    parent_id: Optional[int] = Field(None, description="Parent department ID")
    head_user_id: Optional[int] = Field(None, description="Department head user ID")
    
    # Budget and costs
    budget: Optional[float] = Field(None, ge=0, description="Department budget")
    cost_center_code: Optional[str] = Field(None, max_length=50, description="Cost center code")
    
    # Department metrics and performance
    target_headcount: Optional[int] = Field(None, ge=0, description="Target headcount")
    current_headcount: Optional[int] = Field(0, ge=0, description="Current headcount")
    budget_utilization: Optional[float] = Field(None, ge=0, le=100, description="Budget utilization percentage")
    performance_score: Optional[float] = Field(None, ge=0, le=100, description="Performance score")
    
    # Operational settings
    location: Optional[str] = Field(None, max_length=255, description="Department location")
    floor_number: Optional[str] = Field(None, max_length=10, description="Floor number")
    office_space: Optional[str] = Field(None, max_length=100, description="Office space")
    remote_work_policy: RemoteWorkPolicy = Field(RemoteWorkPolicy.HYBRID, description="Remote work policy")
    
    # Status and lifecycle
    status: DepartmentStatus = Field(DepartmentStatus.ACTIVE, description="Department status")
    established_date: Optional[date] = Field(None, description="Established date")
    
    # Goals and KPIs
    goals: Optional[List[Dict[str, Any]]] = Field(None, description="Department goals")
    kpis: Optional[List[Dict[str, Any]]] = Field(None, description="Key performance indicators")
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not re.match(r'^[A-Z0-9_-]+$', v):
            raise ValueError('Department code must contain only uppercase letters, numbers, underscores, and hyphens')
        return v


class UpdateDepartmentRequest(BaseModel):
    """Update department request schema."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    parent_id: Optional[int] = Field(None)
    head_user_id: Optional[int] = Field(None)
    budget: Optional[float] = Field(None, ge=0)
    cost_center_code: Optional[str] = Field(None, max_length=50)
    target_headcount: Optional[int] = Field(None, ge=0)
    current_headcount: Optional[int] = Field(None, ge=0)
    budget_utilization: Optional[float] = Field(None, ge=0, le=100)
    performance_score: Optional[float] = Field(None, ge=0, le=100)
    location: Optional[str] = Field(None, max_length=255)
    floor_number: Optional[str] = Field(None, max_length=10)
    office_space: Optional[str] = Field(None, max_length=100)
    remote_work_policy: Optional[RemoteWorkPolicy] = Field(None)
    status: Optional[DepartmentStatus] = Field(None)
    established_date: Optional[date] = Field(None)
    goals: Optional[List[Dict[str, Any]]] = Field(None)
    kpis: Optional[List[Dict[str, Any]]] = Field(None)


class DepartmentGoalsRequest(BaseModel):
    """Department goals update request schema."""
    
    goals: List[Dict[str, Any]] = Field(..., description="Department goals")
    
    @field_validator('goals')
    @classmethod
    def validate_goals(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for goal in v:
            if 'title' not in goal or not goal['title']:
                raise ValueError('Each goal must have a title')
            if 'target_date' in goal and goal['target_date']:
                try:
                    datetime.fromisoformat(goal['target_date'].replace('Z', '+00:00'))
                except ValueError:
                    raise ValueError('Invalid target_date format in goal')
        return v


class DepartmentKPIsRequest(BaseModel):
    """Department KPIs update request schema."""
    
    kpis: List[Dict[str, Any]] = Field(..., description="Key performance indicators")
    
    @field_validator('kpis')
    @classmethod
    def validate_kpis(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for kpi in v:
            if 'name' not in kpi or not kpi['name']:
                raise ValueError('Each KPI must have a name')
            if 'target_value' in kpi and kpi['target_value'] is not None:
                if not isinstance(kpi['target_value'], (int, float)):
                    raise ValueError('KPI target_value must be a number')
        return v


class DepartmentResponse(BaseModel):
    """Department response schema."""
    
    id: int
    name: str
    code: str
    description: Optional[str]
    organization_id: int
    parent_id: Optional[int]
    head_user_id: Optional[int]
    is_active: bool
    budget: Optional[float]
    cost_center_code: Optional[str]
    target_headcount: Optional[int]
    current_headcount: Optional[int]
    budget_utilization: Optional[float]
    performance_score: Optional[float]
    location: Optional[str]
    remote_work_policy: str
    status: str
    established_date: Optional[date]
    created_at: datetime
    updated_at: datetime