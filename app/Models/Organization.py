from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING, Union
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, JSON, Index, and_, or_
from sqlalchemy.orm import relationship, Mapped, mapped_column, validates
from sqlalchemy.ext.hybrid import hybrid_property
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions
import re

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Models.Department import Department
    from app.Models.UserOrganization import UserOrganization
    from app.Models.PerformanceReviewCycle import PerformanceReviewCycle
    from app.Models.Tenant import Tenant


class Organization(BaseModel, LogsActivityMixin):
    """
    Organization model with multi-level hierarchical support and tenant integration.
    Organizations can have parent-child relationships for complex structures.
    Supports multi-tenant architecture with data isolation and validation.
    """
    __tablename__ = "organizations"
    
    __table_args__ = (
        Index('idx_org_tenant_active', 'tenant_id', 'is_active'),
        Index('idx_org_parent_level', 'parent_id', 'level'),
        Index('idx_org_code_tenant', 'code', 'tenant_id', unique=True),
        Index('idx_org_hierarchy', 'tenant_id', 'parent_id', 'level'),
    )
    
    # Basic organization information
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    code: Mapped[str] = mapped_column(nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Multi-tenant support (required for data isolation)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Organization type and classification
    organization_type: Mapped[str] = mapped_column(default="company", nullable=False)  # company, division, subsidiary, branch
    industry: Mapped[Optional[str]] = mapped_column(nullable=True)
    size_category: Mapped[Optional[str]] = mapped_column(nullable=True)  # startup, small, medium, large, enterprise
    
    # Contact information
    email: Mapped[Optional[str]] = mapped_column(nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(nullable=True)
    website: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Address information
    address: Mapped[Optional[str]] = mapped_column(nullable=True)
    city: Mapped[Optional[str]] = mapped_column(nullable=True)
    state: Mapped[Optional[str]] = mapped_column(nullable=True)
    country: Mapped[Optional[str]] = mapped_column(nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Hierarchical structure
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.id"),  # type: ignore[arg-type]
        nullable=True, 
        index=True
    )
    level: Mapped[int] = mapped_column( default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column( default=0, nullable=False)
    
    # Business information
    tax_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    registration_number: Mapped[Optional[str]] = mapped_column(nullable=True)
    founded_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    employee_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    annual_revenue: Mapped[Optional[float]] = mapped_column(nullable=True)
    
    # Financial and operational metrics
    fiscal_year_end: Mapped[Optional[str]] = mapped_column(nullable=True)  # MM-DD format
    default_currency: Mapped[str] = mapped_column(default="USD", nullable=False)
    time_zone: Mapped[str] = mapped_column(default="UTC", nullable=False)
    working_hours_start: Mapped[Optional[str]] = mapped_column(nullable=True)  # HH:MM format
    working_hours_end: Mapped[Optional[str]] = mapped_column(nullable=True)  # HH:MM format
    working_days: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array of weekdays
    
    # Status and lifecycle
    status: Mapped[str] = mapped_column(default="active", nullable=False)  # active, inactive, suspended, archived
    verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    archive_reason: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Settings and metadata
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # Self-referencing relationship for hierarchical structure
    parent: Mapped[Optional[Organization]] = relationship(
        "Organization", 
        remote_side="Organization.id", 
        back_populates="children"
    )
    children: Mapped[List[Organization]] = relationship(
        "Organization", 
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    
    # Relationships with other models
    tenant: Mapped[Optional[Tenant]] = relationship(
        "Tenant",
        back_populates="organizations"
    )
    
    departments: Mapped[List[Department]] = relationship(
        "Department", 
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    user_organizations: Mapped[List[UserOrganization]] = relationship(
        "UserOrganization", 
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    review_cycles: Mapped[List["PerformanceReviewCycle"]] = relationship(
        "PerformanceReviewCycle",
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for Organization model."""
        return LogOptions(
            log_name="organizations",
            log_attributes=["name", "code", "is_active", "parent_id", "tenant_id", "organization_type"],
            description_for_event={
                "created": "Organization was created",
                "updated": "Organization was updated", 
                "deleted": "Organization was deleted"
            }
        )
    
    def get_full_name(self) -> str:
        """Get the full hierarchical name of the organization."""
        if self.parent:
            return f"{self.parent.get_full_name()} > {self.name}"
        return self.name
    
    def get_root_organization(self) -> Organization:
        """Get the root organization in the hierarchy."""
        if self.parent:
            return self.parent.get_root_organization()
        return self
    
    def get_ancestors(self) -> List[Organization]:
        """Get all ancestor organizations in ascending order (from root to parent)."""
        ancestors: List[Organization] = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors
    
    def get_descendants(self) -> List[Organization]:
        """Get all descendant organizations (children, grandchildren, etc.)."""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    def get_siblings(self) -> List[Organization]:
        """Get all sibling organizations (same parent, excluding self)."""
        if not self.parent:
            # Root organizations - get all other root organizations
            from config.database import SessionLocal
            session = SessionLocal()
            return session.query(Organization).filter(
                Organization.parent_id.is_(None),
                Organization.id != self.id
            ).all()
        
        return [sibling for sibling in self.parent.children if sibling.id != self.id]
    
    def is_ancestor_of(self, organization: Organization) -> bool:
        """Check if this organization is an ancestor of the given organization."""
        return self in organization.get_ancestors()
    
    def is_descendant_of(self, organization: Organization) -> bool:
        """Check if this organization is a descendant of the given organization."""
        return organization in self.get_ancestors()
    
    def get_level_depth(self) -> int:
        """Get the depth level of this organization in the hierarchy (0 = root)."""
        return len(self.get_ancestors())
    
    def update_level(self) -> None:
        """Update the level based on the current parent relationship."""
        self.level = self.get_level_depth()
        
        # Recursively update children levels
        for child in self.children:
            child.update_level()
    
    def move_to_parent(self, new_parent: Optional[Organization]) -> None:
        """Move this organization to a new parent."""
        if new_parent and new_parent.is_descendant_of(self):
            raise ValueError("Cannot move organization to one of its descendants")
        
        self.parent = new_parent
        self.update_level()
    
    def get_users(self) -> List[User]:
        """Get all users belonging to this organization."""
        return [uo.user for uo in self.user_organizations]
    
    def get_all_users(self, include_descendants: bool = False) -> List[User]:
        """Get all users belonging to this organization and optionally its descendants."""
        users = self.get_users()
        
        if include_descendants:
            for descendant in self.get_descendants():
                users.extend(descendant.get_users())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_users = []
        for user in users:
            if user.id not in seen:
                seen.add(user.id)
                unique_users.append(user)
        
        return unique_users
    
    def get_tenant_organizations(self) -> List[Organization]:
        """Get all organizations within the same tenant."""
        from config.database import SessionLocal
        session = SessionLocal()
        return session.query(Organization).filter(
            Organization.tenant_id == self.tenant_id,
            Organization.is_active == True
        ).all()
    
    def get_organization_stats(self) -> Dict[str, Any]:
        """Get comprehensive organization statistics."""
        stats = {
            "total_departments": len(self.departments),
            "active_departments": len([d for d in self.departments if d.is_active]),
            "total_users": len(self.get_users()),
            "active_users": len([u for u in self.get_users() if hasattr(u, 'is_active') and u.is_active]),
            "children_count": len(self.children),
            "descendants_count": len(self.get_descendants()),
            "level_depth": self.get_level_depth(),
            "total_positions": sum(len(dept.job_positions) for dept in self.departments),
            "active_positions": sum(len([pos for pos in dept.job_positions if pos.is_active]) for dept in self.departments),
            "total_job_levels": len(self.get_unique_job_levels()),
            "management_positions": len(self.get_management_positions()),
            "executive_positions": len(self.get_executive_positions()),
            "vacant_positions": len(self.get_vacant_positions()),
            "recruitment_active": len(self.get_recruiting_positions()),
        }
        
        # Add financial metrics if available
        if self.annual_revenue:
            stats["annual_revenue"] = self.annual_revenue
        
        # Add hierarchy metrics
        if self.children:
            stats["max_child_depth"] = max(child.get_level_depth() for child in self.get_descendants()) + 1
        
        return stats
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific setting value."""
        if not self.settings:
            return default
        return self.settings.get(key, default)
    
    def update_setting(self, key: str, value: Any) -> None:
        """Update a specific setting value."""
        if not self.settings:
            self.settings = {}
        self.settings[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a specific metadata value."""
        if not self.extra_metadata:
            return default
        return self.extra_metadata.get(key, default)
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update a specific metadata value."""
        if not self.extra_metadata:
            self.extra_metadata = {}
        self.extra_metadata[key] = value
    
    @validates('code')
    def validate_code(self, key: str, code: str) -> str:
        """Validate organization code format."""
        if not code:
            raise ValueError("Organization code is required")
        
        # Code should be alphanumeric with underscores/hyphens, 2-20 chars
        if not re.match(r'^[A-Za-z0-9_-]{2,20}$', code):
            raise ValueError("Organization code must be 2-20 alphanumeric characters, underscores, or hyphens")
        
        return code.upper()
    
    @validates('email')
    def validate_email(self, key: str, email: Optional[str]) -> Optional[str]:
        """Validate organization email format."""
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            raise ValueError("Invalid email format")
        return email
    
    @validates('website')
    def validate_website(self, key: str, website: Optional[str]) -> Optional[str]:
        """Validate website URL format."""
        if website and not re.match(r'^https?://', website):
            website = f"https://{website}"
        return website
    
    @validates('organization_type')
    def validate_organization_type(self, key: str, org_type: str) -> str:
        """Validate organization type."""
        valid_types = ['company', 'division', 'subsidiary', 'branch', 'department', 'unit', 'team']
        if org_type not in valid_types:
            raise ValueError(f"Organization type must be one of: {', '.join(valid_types)}")
        return org_type
    
    @validates('size_category')
    def validate_size_category(self, key: str, size: Optional[str]) -> Optional[str]:
        """Validate organization size category."""
        if size:
            valid_sizes = ['startup', 'small', 'medium', 'large', 'enterprise']
            if size not in valid_sizes:
                raise ValueError(f"Size category must be one of: {', '.join(valid_sizes)}")
        return size
    
    @validates('status')
    def validate_status(self, key: str, status: str) -> str:
        """Validate organization status."""
        valid_statuses = ['active', 'inactive', 'suspended', 'archived']
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return status
    
    @hybrid_property
    def is_verified(self) -> bool:
        """Check if organization is verified."""
        return self.verified
    
    @hybrid_property
    def is_archived(self) -> bool:
        """Check if organization is archived."""
        return self.archived_at is not None
    
    def get_unique_job_levels(self) -> List['JobLevel']:
        """Get all unique job levels used in this organization."""
        from app.Models.JobLevel import JobLevel
        levels = set()
        for dept in self.departments:
            for position in dept.job_positions:
                levels.add(position.job_level_id)
        
        from config.database import SessionLocal
        session = SessionLocal()
        return session.query(JobLevel).filter(JobLevel.id.in_(levels)).all()
    
    def get_management_positions(self) -> List['JobPosition']:
        """Get all management positions in this organization."""
        positions = []
        for dept in self.departments:
            for position in dept.job_positions:
                if position.is_manager_position():
                    positions.append(position)
        return positions
    
    def get_executive_positions(self) -> List['JobPosition']:
        """Get all executive positions in this organization."""
        positions = []
        for dept in self.departments:
            for position in dept.job_positions:
                if position.is_executive_position():
                    positions.append(position)
        return positions
    
    def get_vacant_positions(self) -> List['JobPosition']:
        """Get all vacant positions in this organization."""
        positions = []
        for dept in self.departments:
            for position in dept.job_positions:
                if position.is_available() and position.is_active:
                    positions.append(position)
        return positions
    
    def get_recruiting_positions(self) -> List['JobPosition']:
        """Get all positions currently recruiting."""
        positions = []
        for dept in self.departments:
            for position in dept.job_positions:
                if position.status == "recruiting" and position.is_active:
                    positions.append(position)
        return positions
    
    def verify_organization(self, verified_by: Optional[str] = None) -> None:
        """Mark organization as verified."""
        self.verified = True
        self.verified_at = datetime.utcnow()
        if verified_by:
            self.update_metadata('verified_by', verified_by)
    
    def archive_organization(self, reason: str, archived_by: Optional[str] = None) -> None:
        """Archive the organization."""
        self.status = "archived"
        self.is_active = False
        self.archived_at = datetime.utcnow()
        self.archive_reason = reason
        if archived_by:
            self.update_metadata('archived_by', archived_by)
    
    def restore_organization(self, restored_by: Optional[str] = None) -> None:
        """Restore archived organization."""
        self.status = "active"
        self.is_active = True
        self.archived_at = None
        self.archive_reason = None
        if restored_by:
            self.update_metadata('restored_by', restored_by)
            self.update_metadata('restored_at', datetime.utcnow().isoformat())
    
    def get_organizational_chart(self) -> Dict[str, Any]:
        """Get organizational chart data for visualization."""
        def build_chart_node(org: 'Organization') -> Dict[str, Any]:
            return {
                "id": org.id,
                "name": org.name,
                "code": org.code,
                "type": org.organization_type,
                "level": org.level,
                "is_active": org.is_active,
                "employee_count": org.employee_count,
                "children": [build_chart_node(child) for child in org.children if child.is_active]
            }
        
        return build_chart_node(self)
    
    def get_departments_hierarchy(self) -> Dict[str, Any]:
        """Get complete departments hierarchy for this organization."""
        def build_dept_tree(dept: 'Department') -> Dict[str, Any]:
            return {
                "id": dept.id,
                "name": dept.name,
                "code": dept.code,
                "level": dept.level,
                "head_name": dept.head.name if dept.head else None,
                "users_count": len(dept.get_users()),
                "positions_count": len(dept.job_positions),
                "children": [build_dept_tree(child) for child in dept.children if child.is_active]
            }
        
        root_departments = [dept for dept in self.departments if dept.parent_id is None and dept.is_active]
        return {
            "organization_id": self.id,
            "organization_name": self.name,
            "departments": [build_dept_tree(dept) for dept in root_departments]
        }
    
    def can_add_child_organization(self, max_depth: int = 5) -> bool:
        """Check if organization can have child organizations."""
        current_depth = self.get_level_depth()
        return current_depth < max_depth and self.is_active and self.status == "active"
    
    def validate_tenant_consistency(self) -> bool:
        """Validate that all related entities belong to the same tenant."""
        # Check departments
        for dept in self.departments:
            if hasattr(dept, 'tenant_id') and dept.tenant_id != self.tenant_id:
                return False
        
        # Check users through user_organizations
        for user_org in self.user_organizations:
            if hasattr(user_org.user, 'tenant_users'):
                user_tenant_ids = [tu.tenant_id for tu in user_org.user.tenant_users]
                if self.tenant_id not in user_tenant_ids:
                    return False
        
        return True
    
    def to_dict_with_hierarchy(self) -> Dict[str, Any]:
        """Return organization data with hierarchical information."""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "is_active": self.is_active,
            "tenant_id": self.tenant_id,
            "organization_type": self.organization_type,
            "industry": self.industry,
            "size_category": self.size_category,
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "postal_code": self.postal_code,
            "tax_id": self.tax_id,
            "registration_number": self.registration_number,
            "founded_date": self.founded_date,
            "employee_count": self.employee_count,
            "annual_revenue": self.annual_revenue,
            "parent_id": self.parent_id,
            "level": self.level,
            "sort_order": self.sort_order,
            "full_name": self.get_full_name(),
            "children_count": len(self.children),
            "departments_count": len(self.departments),
            "users_count": len(self.get_users()),
            "fiscal_year_end": self.fiscal_year_end,
            "default_currency": self.default_currency,
            "time_zone": self.time_zone,
            "working_hours_start": self.working_hours_start,
            "working_hours_end": self.working_hours_end,
            "working_days": self.working_days,
            "status": self.status,
            "verified": self.verified,
            "verified_at": self.verified_at,
            "archived_at": self.archived_at,
            "archive_reason": self.archive_reason,
            "stats": self.get_organization_stats(),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }