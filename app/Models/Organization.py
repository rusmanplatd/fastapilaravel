from __future__ import annotations

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.Models.BaseModel import BaseModel
from app.Traits.LogsActivity import LogsActivityMixin, LogOptions

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Models.Department import Department
    from app.Models.UserOrganization import UserOrganization
    from app.Models.PerformanceReviewCycle import PerformanceReviewCycle


class Organization(BaseModel, LogsActivityMixin):
    """
    Organization model with multi-level hierarchical support.
    Organizations can have parent-child relationships for complex structures.
    """
    __tablename__ = "organizations"
    
    # Basic organization information
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    code: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
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
    
    # Settings
    settings: Mapped[Optional[str]] = mapped_column( nullable=True)  # JSON string for flexible settings
    
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
            log_attributes=["name", "code", "is_active", "parent_id"],
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
    
    def to_dict_with_hierarchy(self) -> Dict[str, Any]:
        """Return organization data with hierarchical information."""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "is_active": self.is_active,
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "postal_code": self.postal_code,
            "parent_id": self.parent_id,
            "level": self.level,
            "sort_order": self.sort_order,
            "full_name": self.get_full_name(),
            "children_count": len(self.children),
            "departments_count": len(self.departments),
            "users_count": len(self.get_users()),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }