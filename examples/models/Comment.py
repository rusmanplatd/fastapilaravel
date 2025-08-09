"""
Example Comment model demonstrating Laravel-style relationships
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.Models.BaseModel import BaseModel
from app.Utils.ULIDUtils import ULID

if TYPE_CHECKING:
    from database.migrations.create_users_table import User
    from examples.models.Post import Post


class Comment(BaseModel):
    """Example Comment model with Laravel-style relationships"""
    __tablename__ = "comments"
    
    # Define Laravel-style relationships
    __relationships__ = {
        'user': BaseModel.belongs_to('User', 'user_id'),
        'post': BaseModel.belongs_to('Post', 'post_id'),
        'parent': BaseModel.belongs_to('Comment', 'parent_id'),
        'replies': BaseModel.has_many('Comment', 'parent_id'),
    }
    
    # Fillable attributes
    __fillable__ = ['content', 'user_id', 'post_id', 'parent_id']
    
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Foreign keys
    user_id: Mapped[ULID] = mapped_column(ForeignKey("users.id"), nullable=False)
    post_id: Mapped[ULID] = mapped_column(ForeignKey("posts.id"), nullable=False)
    parent_id: Mapped[Optional[ULID]] = mapped_column(ForeignKey("comments.id"), nullable=True)
    
    # SQLAlchemy relationships
    user: Mapped[User] = relationship("User", back_populates="comments")
    post: Mapped[Post] = relationship("Post", back_populates="comments")
    parent: Mapped[Optional[Comment]] = relationship("Comment", remote_side="Comment.id", back_populates="replies")
    replies: Mapped[list[Comment]] = relationship("Comment", back_populates="parent", cascade="all, delete-orphan")
    
    # Laravel-style scopes
    @classmethod
    def scope_top_level(cls, query):
        """Scope for top-level comments (no parent)"""
        return query.where(cls.parent_id.is_(None))
    
    @classmethod
    def scope_replies(cls, query):
        """Scope for reply comments (has parent)"""
        return query.where(cls.parent_id.is_not(None))
    
    @classmethod
    def scope_for_post(cls, query, post_id: ULID):
        """Scope for comments on specific post"""
        return query.where(cls.post_id == post_id)
    
    # Laravel-style accessors
    @property
    def author_name(self) -> str:
        """Get the comment author's name"""
        return self.user.name if self.user else "Anonymous"
    
    @property
    def reply_count(self) -> int:
        """Get the number of replies"""
        return len(self.replies)
    
    def is_reply(self) -> bool:
        """Check if this comment is a reply"""
        return self.parent_id is not None
    
    def is_authored_by(self, user: User) -> bool:
        """Check if comment is authored by given user"""
        return self.user_id == user.id