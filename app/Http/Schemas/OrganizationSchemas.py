from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
import re


class OrganizationType(str, Enum):
    """Organization type enumeration."""
    COMPANY = "company"
    CORPORATION = "corporation"
    LLC = "llc"
    PARTNERSHIP = "partnership"
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    NON_PROFIT = "non_profit"
    GOVERNMENT = "government"
    STARTUP = "startup"


class OrganizationStatus(str, Enum):
    """Organization status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class SizeCategory(str, Enum):
    """Organization size category enumeration."""
    STARTUP = "startup"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


class CreateOrganizationRequest(BaseModel):
    """Create organization request schema."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    code: str = Field(..., min_length=2, max_length=50, description="Organization code")
    description: Optional[str] = Field(None, max_length=2000, description="Organization description")
    parent_id: Optional[int] = Field(None, description="Parent organization ID")
    tenant_id: Optional[int] = Field(None, description="Tenant ID")
    
    # Organization classification
    organization_type: OrganizationType = Field(OrganizationType.COMPANY, description="Organization type")
    size_category: Optional[SizeCategory] = Field(None, description="Size category")
    industry: Optional[str] = Field(None, max_length=100, description="Industry")
    
    # Business information
    tax_id: Optional[str] = Field(None, max_length=50, description="Tax ID")
    registration_number: Optional[str] = Field(None, max_length=50, description="Registration number")
    founded_date: Optional[date] = Field(None, description="Founded date")
    employee_count: Optional[int] = Field(None, ge=0, description="Employee count")
    annual_revenue: Optional[float] = Field(None, ge=0, description="Annual revenue")
    
    # Contact information
    email: Optional[str] = Field(None, max_length=255, description="Email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    website: Optional[str] = Field(None, max_length=255, description="Website URL")
    
    # Address information
    address: Optional[str] = Field(None, description="Address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=100, description="State")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    postal_code: Optional[str] = Field(None, max_length=20, description="Postal code")
    
    # Financial and operational metrics
    fiscal_year_end: Optional[str] = Field(None, max_length=5, description="Fiscal year end (MM-DD)")
    default_currency: Optional[str] = Field("USD", max_length=3, description="Default currency")
    time_zone: Optional[str] = Field("UTC", max_length=50, description="Time zone")
    working_hours_start: Optional[str] = Field(None, max_length=5, description="Working hours start (HH:MM)")
    working_hours_end: Optional[str] = Field(None, max_length=5, description="Working hours end (HH:MM)")
    working_days: Optional[List[str]] = Field(None, description="Working days")
    
    # Metadata
    extra_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not re.match(r'^[A-Z0-9_-]+$', v):
            raise ValueError('Organization code must contain only uppercase letters, numbers, underscores, and hyphens')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v
    
    @field_validator('fiscal_year_end')
    @classmethod
    def validate_fiscal_year_end(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^\d{2}-\d{2}$', v):
            raise ValueError('Fiscal year end must be in MM-DD format')
        return v
    
    @field_validator('working_hours_start', 'working_hours_end')
    @classmethod
    def validate_working_hours(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^\d{2}:\d{2}$', v):
            raise ValueError('Working hours must be in HH:MM format')
        return v


class UpdateOrganizationRequest(BaseModel):
    """Update organization request schema."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    parent_id: Optional[int] = Field(None)
    organization_type: Optional[OrganizationType] = Field(None)
    size_category: Optional[SizeCategory] = Field(None)
    industry: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    registration_number: Optional[str] = Field(None, max_length=50)
    founded_date: Optional[date] = Field(None)
    employee_count: Optional[int] = Field(None, ge=0)
    annual_revenue: Optional[float] = Field(None, ge=0)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    website: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    fiscal_year_end: Optional[str] = Field(None, max_length=5)
    default_currency: Optional[str] = Field(None, max_length=3)
    time_zone: Optional[str] = Field(None, max_length=50)
    working_hours_start: Optional[str] = Field(None, max_length=5)
    working_hours_end: Optional[str] = Field(None, max_length=5)
    working_days: Optional[List[str]] = Field(None)
    extra_metadata: Optional[Dict[str, Any]] = Field(None)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v


class VerifyOrganizationRequest(BaseModel):
    """Verify organization request schema."""
    
    verified_by: Optional[str] = Field(None, description="Verified by user")
    verification_notes: Optional[str] = Field(None, description="Verification notes")


class ArchiveOrganizationRequest(BaseModel):
    """Archive organization request schema."""
    
    reason: str = Field(..., min_length=1, max_length=500, description="Archive reason")
    archived_by: Optional[str] = Field(None, description="Archived by user")


class OrganizationResponse(BaseModel):
    """Organization response schema."""
    
    id: int
    name: str
    code: str
    description: Optional[str]
    is_active: bool
    organization_type: str
    size_category: Optional[str]
    industry: Optional[str]
    employee_count: Optional[int]
    annual_revenue: Optional[float]
    verified: bool
    status: str
    created_at: datetime
    updated_at: datetime