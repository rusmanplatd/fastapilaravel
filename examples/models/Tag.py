"""
Example Tag model demonstrating Laravel-style relationships
"""
from __future__ import annotations

from typing import List, TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.Models.BaseModel import BaseModel
from examples.models.Post import post_tag_table

if TYPE_CHECKING:
    from examples.models.Post import Post


class Tag(BaseModel):
    """Example Tag model with Laravel-style relationships"""
    __tablename__ = "tags"
    
    # Define Laravel-style relationships
    __relationships__ = {
        'posts': BaseModel.belongs_to_many('Post', 'post_tag'),
    }
    
    # Fillable attributes
    __fillable__ = ['name', 'slug', 'description']
    
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # SQLAlchemy relationships
    posts: Mapped[List[Post]] = relationship("Post", secondary=post_tag_table, back_populates="tags")
    
    # Laravel-style accessors
    @property
    def post_count(self) -> int:
        """Get the number of posts with this tag"""
        return len(self.posts)
    
    def is_used(self) -> bool:
        """Check if tag is used by any posts"""
        return self.post_count > 0