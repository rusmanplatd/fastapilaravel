from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.Organization import Organization
    from app.Models.User import User
    from app.Models.UserDepartment import UserDepartment
    from app.Models.JobPosition import JobPosition


class Department(BaseModel, LogsActivityMixin):
    """
    Department model with multi-level hierarchical support.
    Departments belong to organizations and can have parent-child relationships.
    """
    __tablename__ = "departments"
    
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
    
    # Settings
    settings: Mapped[Optional[str]] = mapped_column( nullable=True)  # JSON string for flexible settings
    
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
    
    def get_budget_total(self, include_descendants: bool = False) -> float:
        """Get total budget for this department and optionally its descendants."""
        total = self.budget or 0.0
        
        if include_descendants:
            for descendant in self.get_descendants():
                total += descendant.budget or 0.0
        
        return total
    
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
            "updated_at": self.updated_at
        }