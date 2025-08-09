"""
Example Category model demonstrating Laravel-style relationships
"""
from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.Models.BaseModel import BaseModel
from app.Utils.ULIDUtils import ULID

if TYPE_CHECKING:
    from examples.models.Post import Post


class Category(BaseModel):
    """Example Category model with Laravel-style relationships"""
    __tablename__ = "categories"
    
    # Define Laravel-style relationships
    __relationships__ = {
        'posts': BaseModel.has_many('Post', 'category_id'),
        'parent': BaseModel.belongs_to('Category', 'parent_id'),
        'children': BaseModel.has_many('Category', 'parent_id'),
    }
    
    # Fillable attributes
    __fillable__ = ['name', 'slug', 'description', 'parent_id']
    
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Self-referencing foreign key for hierarchical categories
    parent_id: Mapped[Optional[ULID]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    
    # SQLAlchemy relationships
    posts: Mapped[List[Post]] = relationship("Post", back_populates="category")
    parent: Mapped[Optional[Category]] = relationship("Category", remote_side="Category.id", back_populates="children")
    children: Mapped[List[Category]] = relationship("Category", back_populates="parent", cascade="all, delete-orphan")
    
    # Laravel-style scopes
    @classmethod
    def scope_root_categories(cls, query):
        """Scope for root categories (no parent)"""
        return query.where(cls.parent_id.is_(None))
    
    @classmethod
    def scope_sub_categories(cls, query):
        """Scope for subcategories (has parent)"""
        return query.where(cls.parent_id.is_not(None))
    
    @classmethod
    def scope_with_posts(cls, query):
        """Scope for categories that have posts"""
        from examples.models.Post import Post
        return query.join(Post).group_by(cls.id)
    
    # Laravel-style accessors
    @property
    def post_count(self) -> int:
        """Get the number of posts in this category"""
        return len(self.posts)
    
    @property
    def child_count(self) -> int:
        """Get the number of child categories"""
        return len(self.children)
    
    def is_root(self) -> bool:
        """Check if this is a root category"""
        return self.parent_id is None
    
    def is_child(self) -> bool:
        """Check if this is a child category"""
        return self.parent_id is not None
    
    def has_children(self) -> bool:
        """Check if category has children"""
        return self.child_count > 0
    
    def has_posts(self) -> bool:
        """Check if category has any posts"""
        return self.post_count > 0
    
    def get_ancestors(self) -> List[Category]:
        """Get all ancestor categories (Laravel-style)"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors
    
    def get_descendants(self) -> List[Category]:
        """Get all descendant categories (Laravel-style)"""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants