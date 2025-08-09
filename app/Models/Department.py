from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING, Union
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, Index, and_, or_, func
from sqlalchemy.orm import relationship, Mapped, mapped_column, validates
from sqlalchemy.ext.hybrid import hybrid_property
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions
import re
import json

if TYPE_CHECKING:
    from app.Models.Organization import Organization
    from app.Models.User import User
    from app.Models.UserDepartment import UserDepartment
    from app.Models.JobPosition import JobPosition


class Department(BaseModel, LogsActivityMixin):
    """
    Department model with multi-level hierarchical support and validation.
    Departments belong to organizations and can have parent-child relationships.
    Supports budget management, team structure, and performance tracking.
    """
    __tablename__ = "departments"
    
    __table_args__ = (
        Index('idx_dept_org_active', 'organization_id', 'is_active'),
        Index('idx_dept_parent_level', 'parent_id', 'level'),
        Index('idx_dept_code_org', 'code', 'organization_id', unique=True),
        Index('idx_dept_head_user', 'head_user_id'),
    )
    
    # Basic department information
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    code: Mapped[str] = mapped_column(nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column( nullable=True)
    is_active: Mapped[bool] = mapped_column( default=True, nullable=False)
    
    # Organization relationship
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)  # type: ignore[arg-type]
    
    # Hierarchical structure within the organization
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True, index=True)  # type: ignore[arg-type]
    level: Mapped[int] = mapped_column( default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column( default=0, nullable=False)
    
    # Department head/manager
    head_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)  # type: ignore[arg-type]
    
    # Budget and cost center information
    budget: Mapped[Optional[float]] = mapped_column(nullable=True)
    cost_center_code: Mapped[Optional[str]] = mapped_column(nullable=True)
    
    # Department metrics and performance
    target_headcount: Mapped[Optional[int]] = mapped_column(nullable=True)
    current_headcount: Mapped[int] = mapped_column(default=0, nullable=False)
    budget_utilization: Mapped[Optional[float]] = mapped_column(nullable=True)  # Percentage
    performance_score: Mapped[Optional[float]] = mapped_column(nullable=True)  # 0-100
    
    # Operational settings
    location: Mapped[Optional[str]] = mapped_column(nullable=True)
    floor_number: Mapped[Optional[str]] = mapped_column(nullable=True)
    office_space: Mapped[Optional[str]] = mapped_column(nullable=True)
    remote_work_policy: Mapped[str] = mapped_column(default="hybrid", nullable=False)  # on-site, hybrid, remote
    
    # Status and lifecycle
    status: Mapped[str] = mapped_column(default="active", nullable=False)  # active, inactive, restructuring, merging
    established_date: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Settings and metadata
    settings: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON string for flexible settings
    goals: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array of department goals
    kpis: Mapped[Optional[str]] = mapped_column(nullable=True)  # JSON array of key performance indicators
    
    # Relationships
    organization: Mapped[Organization] = relationship(
        "Organization", 
        back_populates="departments"
    )
    
    # Self-referencing relationship for hierarchical structure
    parent: Mapped[Optional[Department]] = relationship(
        "Department", 
        remote_side="Department.id", 
        back_populates="children"
    )
    children: Mapped[List[Department]] = relationship(
        "Department", 
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    
    # Department head relationship
    head: Mapped[Optional[User]] = relationship(
        "User",
        foreign_keys=[head_user_id]
    )
    
    # User-department relationships
    user_departments: Mapped[List[UserDepartment]] = relationship(
        "UserDepartment", 
        back_populates="department",
        cascade="all, delete-orphan"
    )
    
    # Job positions in this department
    job_positions: Mapped[List[JobPosition]] = relationship(
        "JobPosition", 
        back_populates="department",
        cascade="all, delete-orphan"
    )
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """Configure activity logging for Department model."""
        return LogOptions(
            log_name="departments",
            log_attributes=["name", "code", "is_active", "organization_id", "parent_id", "head_user_id"],
            description_for_event={
                "created": "Department was created",
                "updated": "Department was updated", 
                "deleted": "Department was deleted"
            }
        )
    
    def get_full_name(self) -> str:
        """Get the full hierarchical name of the department."""
        if self.parent:
            return f"{self.parent.get_full_name()} > {self.name}"
        return f"{self.organization.name} > {self.name}"
    
    def get_root_department(self) -> Department:
        """Get the root department in the hierarchy within the organization."""
        if self.parent:
            return self.parent.get_root_department()
        return self
    
    def get_ancestors(self) -> List[Department]:
        """Get all ancestor departments in ascending order (from root to parent)."""
        ancestors: List[Department] = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors
    
    def get_descendants(self) -> List[Department]:
        """Get all descendant departments (children, grandchildren, etc.)."""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants
    
    def get_siblings(self) -> List[Department]:
        """Get all sibling departments (same parent and organization, excluding self)."""
        from config.database import SessionLocal
        session = SessionLocal()
        
        if not self.parent:
            # Root departments - get all other root departments in the same organization
            return session.query(Department).filter(
                Department.organization_id == self.organization_id,
                Department.parent_id.is_(None),
                Department.id != self.id
            ).all()
        
        return [sibling for sibling in self.parent.children if sibling.id != self.id]
    
    def is_ancestor_of(self, department: Department) -> bool:
        """Check if this department is an ancestor of the given department."""
        return self in department.get_ancestors()
    
    def is_descendant_of(self, department: Department) -> bool:
        """Check if this department is a descendant of the given department."""
        return department in self.get_ancestors()
    
    def get_level_depth(self) -> int:
        """Get the depth level of this department in the hierarchy (0 = root within organization)."""
        return len(self.get_ancestors())
    
    def update_level(self) -> None:
        """Update the level based on the current parent relationship."""
        self.level = self.get_level_depth()
        
        # Recursively update children levels
        for child in self.children:
            child.update_level()
    
    def move_to_parent(self, new_parent: Optional[Department]) -> None:
        """Move this department to a new parent."""
        if new_parent:
            # Ensure the new parent is in the same organization
            if new_parent.organization_id != self.organization_id:
                raise ValueError("Cannot move department to a parent in a different organization")
            
            # Prevent circular relationships
            if new_parent.is_descendant_of(self):
                raise ValueError("Cannot move department to one of its descendants")
        
        self.parent = new_parent
        self.update_level()
    
    def get_users(self) -> List[User]:
        """Get all users belonging to this department."""
        return [ud.user for ud in self.user_departments]
    
    def get_all_users(self, include_descendants: bool = False) -> List[User]:
        """Get all users belonging to this department and optionally its descendants."""
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
    
    def get_positions(self) -> List[JobPosition]:
        """Get all job positions in this department."""
        return self.job_positions
    
    def get_all_positions(self, include_descendants: bool = False) -> List[JobPosition]:
        """Get all job positions in this department and optionally its descendants."""
        positions = self.get_positions()
        
        if include_descendants:
            for descendant in self.get_descendants():
                positions.extend(descendant.get_positions())
        
        return positions
    
    @hybrid_property
    def is_healthy(self) -> bool:
        """Check if department is in good health."""
        health = self.get_department_health_score()
        return health['percentage'] >= 60
    
    def get_budget_total(self, include_descendants: bool = False) -> float:
        """Get total budget for this department and optionally its descendants."""
        total = self.budget or 0.0
        
        if include_descendants:
            for descendant in self.get_descendants():
                total += descendant.budget or 0.0
        
        return total
    
    @validates('code')
    def validate_code(self, key: str, code: str) -> str:
        """Validate department code format."""
        if not code:
            raise ValueError("Department code is required")
        
        # Code should be alphanumeric with underscores/hyphens, 2-20 chars
        if not re.match(r'^[A-Za-z0-9_-]{2,20}$', code):
            raise ValueError("Department code must be 2-20 alphanumeric characters, underscores, or hyphens")
        
        return code.upper()
    
    @validates('remote_work_policy')
    def validate_remote_work_policy(self, key: str, policy: str) -> str:
        """Validate remote work policy."""
        valid_policies = ['on-site', 'hybrid', 'remote']
        if policy not in valid_policies:
            raise ValueError(f"Remote work policy must be one of: {', '.join(valid_policies)}")
        return policy
    
    @validates('status')
    def validate_status(self, key: str, status: str) -> str:
        """Validate department status."""
        valid_statuses = ['active', 'inactive', 'restructuring', 'merging', 'dissolved']
        if status not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return status
    
    @validates('budget')
    def validate_budget(self, key: str, budget: Optional[float]) -> Optional[float]:
        """Validate budget amount."""
        if budget is not None and budget < 0:
            raise ValueError("Budget cannot be negative")
        return budget
    
    def update_headcount(self) -> None:
        """Update current headcount based on active users."""
        self.current_headcount = len(self.get_users())
    
    def get_headcount_variance(self) -> Optional[int]:
        """Get variance between target and current headcount."""
        if self.target_headcount is None:
            return None
        return self.current_headcount - self.target_headcount
    
    def get_budget_utilization_percentage(self) -> Optional[float]:
        """Get budget utilization as percentage."""
        if not self.budget or not self.budget_utilization:
            return None
        return min(100.0, self.budget_utilization)
    
    def is_over_budget(self) -> bool:
        """Check if department is over budget."""
        utilization = self.get_budget_utilization_percentage()
        return utilization is not None and utilization > 100.0
    
    def is_understaffed(self) -> bool:
        """Check if department is understaffed."""
        variance = self.get_headcount_variance()
        return variance is not None and variance < 0
    
    def is_overstaffed(self) -> bool:
        """Check if department is overstaffed."""
        variance = self.get_headcount_variance()
        return variance is not None and variance > 0
    
    def to_dict_with_hierarchy(self) -> Dict[str, Any]:
        """Return department data with hierarchical information."""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "is_active": self.is_active,
            "organization_id": self.organization_id,
            "organization_name": self.organization.name,
            "parent_id": self.parent_id,
            "level": self.level,
            "sort_order": self.sort_order,
            "head_user_id": self.head_user_id,
            "head_user_name": self.head.name if self.head else None,
            "budget": self.budget,
            "cost_center_code": self.cost_center_code,
            "full_name": self.get_full_name(),
            "children_count": len(self.children),
            "users_count": len(self.get_users()),
            "positions_count": len(self.job_positions),
            "created_at": self.created_at,
            "target_headcount": self.target_headcount,
            "current_headcount": self.current_headcount,
            "budget_utilization": self.budget_utilization,
            "performance_score": self.performance_score,
            "location": self.location,
            "floor_number": self.floor_number,
            "office_space": self.office_space,
            "remote_work_policy": self.remote_work_policy,
            "status": self.status,
            "established_date": self.established_date,
            "budget_total": self.get_budget_total(),
            "budget_utilization_percentage": self.get_budget_utilization_percentage(),
            "headcount_variance": self.get_headcount_variance(),
            "is_healthy": self.is_healthy,
            "updated_at": self.updated_at
        }
    
    def get_goals(self) -> List[Dict[str, Any]]:
        """Get department goals."""
        if not self.goals:
            return []
        try:
            return json.loads(self.goals)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_goals(self, goals: List[Dict[str, Any]]) -> None:
        """Set department goals."""
        self.goals = json.dumps(goals)
    
    def add_goal(self, goal: Dict[str, Any]) -> None:
        """Add a new goal to the department."""
        current_goals = self.get_goals()
        current_goals.append({
            **goal,
            'created_at': datetime.utcnow().isoformat(),
            'id': len(current_goals) + 1
        })
        self.set_goals(current_goals)
    
    def get_kpis(self) -> List[Dict[str, Any]]:
        """Get department KPIs."""
        if not self.kpis:
            return []
        try:
            return json.loads(self.kpis)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_kpis(self, kpis: List[Dict[str, Any]]) -> None:
        """Set department KPIs."""
        self.kpis = json.dumps(kpis)
    
    def get_settings_dict(self) -> Dict[str, Any]:
        """Get settings as dictionary."""
        if not self.settings:
            return {}
        try:
            return json.loads(self.settings)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def update_settings(self, key: str, value: Any) -> None:
        """Update a specific setting."""
        settings_dict = self.get_settings_dict()
        settings_dict[key] = value
        self.settings = json.dumps(settings_dict)
    
    def get_department_health_score(self) -> Dict[str, Any]:
        """Calculate department health score based on multiple factors."""
        score = 0
        max_score = 100
        factors = {}
        
        # Headcount factor (25 points)
        headcount_variance = self.get_headcount_variance()
        if headcount_variance is not None:
            if abs(headcount_variance) <= 1:  # Within 1 person of target
                headcount_score = 25
            elif abs(headcount_variance) <= 3:  # Within 3 people
                headcount_score = 15
            else:
                headcount_score = 5
        else:
            headcount_score = 15  # No target set, give moderate score
        
        factors['headcount'] = headcount_score
        score += headcount_score
        
        # Budget factor (25 points)
        if self.budget_utilization is not None:
            if 80 <= self.budget_utilization <= 95:  # Optimal range
                budget_score = 25
            elif 70 <= self.budget_utilization <= 100:  # Good range
                budget_score = 20
            elif self.budget_utilization <= 110:  # Slightly over
                budget_score = 10
            else:
                budget_score = 0  # Significantly over budget
        else:
            budget_score = 15  # No budget tracking
        
        factors['budget'] = budget_score
        score += budget_score
        
        # Performance factor (25 points)
        if self.performance_score is not None:
            performance_factor = min(25, (self.performance_score / 100) * 25)
        else:
            performance_factor = 15  # No performance data
        
        factors['performance'] = performance_factor
        score += performance_factor
        
        # Management factor (25 points)
        has_head = self.head_user_id is not None
        active_positions = len([pos for pos in self.job_positions if pos.is_active])
        vacant_positions = len([pos for pos in self.job_positions if pos.is_available()])
        
        management_score = 0
        if has_head:
            management_score += 10
        if active_positions > 0:
            management_score += 10
            # Bonus for low vacancy rate
            if vacant_positions == 0:
                management_score += 5
            elif vacant_positions / active_positions <= 0.2:  # Less than 20% vacant
                management_score += 3
        
        factors['management'] = management_score
        score += management_score
        
        health_status = "excellent" if score >= 80 else "good" if score >= 60 else "fair" if score >= 40 else "poor"
        
        return {
            "total_score": score,
            "max_score": max_score,
            "percentage": round((score / max_score) * 100, 1),
            "status": health_status,
            "factors": factors,
            "recommendations": self._generate_health_recommendations(factors)
        }
    
    def _generate_health_recommendations(self, factors: Dict[str, float]) -> List[str]:
        """Generate recommendations based on health factors."""
        recommendations = []
        
        if factors['headcount'] < 15:
            variance = self.get_headcount_variance()
            if variance and variance < 0:
                recommendations.append("Consider hiring to meet target headcount")
            elif variance and variance > 0:
                recommendations.append("Review headcount target - department may be overstaffed")
        
        if factors['budget'] < 15:
            if self.is_over_budget():
                recommendations.append("Review budget allocation - department is over budget")
            else:
                recommendations.append("Implement budget tracking for better financial management")
        
        if factors['performance'] < 15:
            recommendations.append("Establish performance metrics and tracking")
        
        if factors['management'] < 15:
            if not self.head_user_id:
                recommendations.append("Assign a department head for better leadership")
            vacant_rate = len([pos for pos in self.job_positions if pos.is_available()]) / max(1, len(self.job_positions))
            if vacant_rate > 0.2:
                recommendations.append("Address high position vacancy rate")
        
        return recommendations
    
    def assign_head(self, user: 'User') -> None:
        """Assign a department head."""
        # Validate user belongs to this organization
        user_org_ids = [uo.organization_id for uo in user.user_organizations]
        if self.organization_id not in user_org_ids:
            raise ValueError("User must belong to the organization to be department head")
        
        self.head_user_id = user.id
        self.update_metadata('head_assigned_at', datetime.utcnow().isoformat())
    
    def remove_head(self) -> None:
        """Remove the current department head."""
        self.head_user_id = None
        self.update_metadata('head_removed_at', datetime.utcnow().isoformat())
    
    @classmethod
    def get_by_organization(cls, organization_id: int, active_only: bool = True) -> List['Department']:
        """Get all departments in an organization."""
        from config.database import SessionLocal
        session = SessionLocal()
        
        query = session.query(cls).filter(cls.organization_id == organization_id)
        if active_only:
            query = query.filter(cls.is_active == True)
        
        return query.order_by(cls.level, cls.sort_order, cls.name).all()
    
    @classmethod
    def get_root_departments(cls, organization_id: int) -> List['Department']:
        """Get all root departments in an organization."""
        from config.database import SessionLocal
        session = SessionLocal()
        
        return session.query(cls).filter(
            cls.organization_id == organization_id,
            cls.parent_id.is_(None),
            cls.is_active == True
        ).order_by(cls.sort_order, cls.name).all()
    
    @classmethod
    def get_departments_needing_heads(cls, organization_id: int) -> List['Department']:
        """Get departments without assigned heads."""
        from config.database import SessionLocal
        session = SessionLocal()
        
        return session.query(cls).filter(
            cls.organization_id == organization_id,
            cls.head_user_id.is_(None),
            cls.is_active == True
        ).all()