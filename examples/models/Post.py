"""
Example Post model demonstrating Laravel-style relationships
"""
from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.Models.BaseModel import BaseModel, RelationType
from app.Utils.ULIDUtils import ULID

if TYPE_CHECKING:
    from app.Models.User import User
    from examples.models.Comment import Comment
    from examples.models.Tag import Tag
    from examples.models.Category import Category


# Many-to-many pivot table for posts and tags
post_tag_table = Table(
    'post_tag',
    BaseModel.metadata,
    Column('post_id', String(26), ForeignKey('posts.id'), primary_key=True),
    Column('tag_id', String(26), ForeignKey('tags.id'), primary_key=True),
)


class Post(BaseModel):
    """Example Post model with Laravel-style relationships"""
    __tablename__ = "posts"
    
    # Define Laravel-style relationships
    __relationships__ = {
        'author': BaseModel.belongs_to('User', 'user_id'),
        'comments': BaseModel.has_many('Comment', 'post_id'),
        'tags': BaseModel.belongs_to_many('Tag', 'post_tag'),
        'category': BaseModel.belongs_to('Category', 'category_id'),
    }
    
    # Fillable attributes
    __fillable__ = ['title', 'content', 'excerpt', 'user_id', 'category_id', 'is_published']
    
    # Hidden attributes (won't show in serialization)
    __hidden__ = ['user_id']
    
    # Cast attributes
    __casts__ = {
        'metadata': 'json',
        'is_published': 'boolean'
    }
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    is_published: Mapped[bool] = mapped_column(default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON field
    
    # Foreign keys
    user_id: Mapped[ULID] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[Optional[ULID]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    
    # SQLAlchemy relationships (actual ORM relationships)
    author: Mapped[User] = relationship("User", back_populates="posts")
    comments: Mapped[List[Comment]] = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    tags: Mapped[List[Tag]] = relationship("Tag", secondary=post_tag_table, back_populates="posts")
    category: Mapped[Optional[Category]] = relationship("Category", back_populates="posts")
    
    # Laravel-style scopes
    @classmethod
    def scope_published(cls, query):
        """Scope for published posts only"""
        return query.where(cls.is_published == True)
    
    @classmethod
    def scope_draft(cls, query):
        """Scope for draft posts only"""
        return query.where(cls.is_published == False)
    
    @classmethod
    def scope_by_author(cls, query, author_id: ULID):
        """Scope for posts by specific author"""
        return query.where(cls.user_id == author_id)
    
    @classmethod
    def scope_with_category(cls, query):
        """Scope for posts that have a category"""
        return query.where(cls.category_id.is_not(None))
    
    # Laravel-style accessors and mutators
    @property
    def author_name(self) -> str:
        """Get the author's name"""
        return self.author.name if self.author else "Unknown"
    
    @property
    def comment_count(self) -> int:
        """Get the number of comments"""
        return len(self.comments)
    
    @property
    def tag_list(self) -> List[str]:
        """Get list of tag names"""
        return [tag.name for tag in self.tags]
    
    def is_authored_by(self, user: User) -> bool:
        """Check if post is authored by given user"""
        return self.user_id == user.id
    
    def publish(self) -> None:
        """Publish the post"""
        self.is_published = True
        self.published_at = datetime.now()
    
    def unpublish(self) -> None:
        """Unpublish the post"""
        self.is_published = False
        self.published_at = None
    
    def add_tag(self, tag: Tag) -> None:
        """Add a tag to the post"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: Tag) -> None:
        """Remove a tag from the post"""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def sync_tags(self, tags: List[Tag]) -> None:
        """Sync post tags (Laravel-style)"""
        self.tags.clear()
        for tag in tags:
            self.tags.append(tag)