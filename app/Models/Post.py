from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func
from sqlalchemy import DateTime
from sqlalchemy.orm import relationship
from app.Models.BaseModel import BaseModel


class Post(BaseModel):
    """
    Laravel-style Post Model.
    
    Represents blog posts with Laravel-like features including
    scopes, relationships, and attribute casting.
    """
    
    __tablename__ = 'posts'
    
    # Laravel-style configuration
    __fillable__ = [
        'title', 'slug', 'content', 'excerpt', 'category', 'tags',
        'status', 'is_published', 'is_featured', 'meta_title', 
        'meta_description', 'meta_keywords', 'published_at',
        'author_id', 'difficulty_level', 'language', 'author_notes'
    ]
    
    __hidden__ = ['author_notes']
    
    __casts__ = {
        'tags': 'json',
        'is_published': 'boolean',
        'is_featured': 'boolean',
        'published_at': 'datetime',
        'views_count': 'int',
        'likes_count': 'int',
        'comments_count': 'int',
        'read_time_minutes': 'int'
    }
    
    __dates__ = ['published_at', 'created_at', 'updated_at']
    
    __appends__ = ['reading_time', 'is_recent', 'excerpt_short']
    
    # Database columns
    title = Column(String(255), nullable=False, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False)
    excerpt = Column(Text)
    category = Column(String(100), index=True)
    tags = Column(JSON)  # Array of tags
    status = Column(String(20), default='draft', index=True)
    is_published = Column(Boolean, default=False, index=True)
    is_featured = Column(Boolean, default=False, index=True)
    
    # SEO fields
    meta_title = Column(String(255))
    meta_description = Column(String(500))
    meta_keywords = Column(String(500))
    
    # Publishing
    published_at = Column(DateTime)
    author_id = Column(String(26))  # ULID foreign key
    
    # Engagement metrics
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)  
    comments_count = Column(Integer, default=0)
    
    # Content metadata
    read_time_minutes = Column(Integer)
    difficulty_level = Column(String(20))  # beginner, intermediate, advanced
    language = Column(String(10), default='en')
    
    # Author notes (hidden from public)
    author_notes = Column(Text)
    
    # Relationships
    # author = relationship("User", foreign_keys=[author_id])
    # comments = relationship("Comment", back_populates="post")
    
    def __repr__(self) -> str:
        return f"<Post(id='{self.id}', title='{self.title}', status='{self.status}')>"
    
    # Laravel-style Accessors (Computed Properties)
    @property
    def reading_time(self) -> str:
        """Get formatted reading time."""
        read_time_val = getattr(self, 'read_time_minutes', None)
        if read_time_val is not None:
            if read_time_val < 60:
                return f"{read_time_val} min read"
            else:
                read_time = int(read_time_val) if read_time_val else 0
                hours = read_time // 60
                minutes = read_time % 60
                return f"{hours}h {minutes}m read"
        else:
            return "Quick read"
    
    @property
    def is_recent(self) -> bool:
        """Check if post was published recently (within 7 days)."""
        published_val = getattr(self, 'published_at', None)
        if not published_val:
            return False
        from datetime import timedelta
        now = datetime.now()
        if hasattr(published_val, 'replace'):
            # Handle timezone-aware datetime
            if hasattr(published_val, 'tzinfo') and published_val.tzinfo is not None:
                import pytz
                now = now.replace(tzinfo=pytz.utc)
        time_diff = now - published_val
        return time_diff.days <= 7
    
    @property
    def excerpt_short(self) -> str:
        """Get shortened excerpt for previews."""
        from sqlalchemy import Column
        excerpt_value = getattr(self, 'excerpt', None)
        if not excerpt_value or isinstance(excerpt_value, Column):
            return ""
        excerpt_str = str(excerpt_value)
        return excerpt_str[:150] + "..." if len(excerpt_str) > 150 else excerpt_str
    
    @property
    def word_count(self) -> int:
        """Get approximate word count of content."""
        content_val = getattr(self, 'content', None)
        if not content_val:
            return 0
        return len(str(content_val).split())
    
    @property
    def tag_list(self) -> List[str]:
        """Get tags as a list."""
        from sqlalchemy import Column
        tags_value = getattr(self, 'tags', None)
        if isinstance(tags_value, Column):
            return []
        if isinstance(tags_value, list):
            return tags_value
        elif isinstance(tags_value, str):
            try:
                import json
                return json.loads(tags_value)
            except:
                return []
        return []
    
    @property
    def published_date_formatted(self) -> str:
        """Get formatted published date."""
        published_val = getattr(self, 'published_at', None)
        if published_val:
            return published_val.strftime("%B %d, %Y")
        return ""
    
    @property
    def engagement_score(self) -> float:
        """Calculate engagement score based on metrics."""
        views = int(getattr(self, 'views_count', 0) or 0)
        likes = int(getattr(self, 'likes_count', 0) or 0)
        comments = int(getattr(self, 'comments_count', 0) or 0)
        
        if views == 0:
            return 0.0
        
        # Weighted engagement score
        score = ((likes * 2) + (comments * 3)) / views * 100
        return round(score, 2)
    
    @property
    def url(self) -> str:
        """Get post URL."""
        return f"/posts/{self.slug}"
    
    # Laravel-style Mutators (Setters)
    def set_title_attribute(self, value: str) -> None:
        """Auto-generate slug when title is set."""
        if hasattr(self, '_title_column'):
            setattr(self, '_title_column', value)
        if not hasattr(self, '_slug_column') or not getattr(self, '_slug_column', None):
            if hasattr(self, '_slug_column'):
                setattr(self, '_slug_column', self._generate_slug(value))
    
    def set_tags_attribute(self, value: Any) -> None:
        """Ensure tags are stored as JSON."""
        if isinstance(value, str):
            # Convert comma-separated string to list
            setattr(self, 'tags', [tag.strip() for tag in value.split(',') if tag.strip()])
        elif isinstance(value, list):
            setattr(self, 'tags', value)
        else:
            setattr(self, 'tags', [])
    
    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug from title."""
        import re
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_-]+', '-', slug)
        return slug.strip('-')[:100]
    
    # Laravel-style Scopes
    @classmethod
    def scope_published(cls, query: Any) -> Any:
        """Scope to only published posts."""
        return query.where(cls.is_published == True)
    
    @classmethod  
    def scope_draft(cls, query: Any) -> Any:
        """Scope to only draft posts."""
        return query.where(cls.status == 'draft')
    
    @classmethod
    def scope_featured(cls, query: Any) -> Any:
        """Scope to only featured posts."""
        return query.where(cls.is_featured == True)
    
    @classmethod
    def scope_category(cls, query: Any, category: str) -> Any:
        """Scope to posts in specific category."""
        return query.where(cls.category == category)
    
    @classmethod
    def scope_recent(cls, query: Any, days: int = 30) -> Any:
        """Scope to recent posts."""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        return query.where(cls.published_at >= cutoff_date)
    
    @classmethod
    def scope_popular(cls, query: Any, min_views: int = 100) -> Any:
        """Scope to popular posts."""
        return query.where(cls.views_count >= min_views)
    
    @classmethod
    def scope_with_tag(cls, query: Any, tag: str) -> Any:
        """Scope to posts with specific tag."""
        # Use proper JSON querying for PostgreSQL
        from sqlalchemy.dialects.postgresql import JSON
        return query.filter(cls.tags.op('@>')([tag]))  # type: ignore[attr-defined]
    
    @classmethod
    def scope_by_author(cls, query: Any, author_id: str) -> Any:
        """Scope to posts by specific author."""
        return query.where(cls.author_id == author_id)
    
    @classmethod
    def scope_difficulty(cls, query: Any, level: str) -> Any:
        """Scope to posts of specific difficulty level."""
        return query.where(cls.difficulty_level == level)
    
    # Laravel-style Methods
    def publish(self) -> None:
        """Publish the post."""
        setattr(self, 'is_published', True)
        setattr(self, 'status', 'published')
        if not self.published_at:
            setattr(self, 'published_at', datetime.now())
    
    def unpublish(self) -> None:
        """Unpublish the post."""
        setattr(self, 'is_published', False)
        setattr(self, 'status', 'draft')
    
    def feature(self) -> None:
        """Mark post as featured."""
        setattr(self, 'is_featured', True)
    
    def unfeature(self) -> None:
        """Remove featured status."""
        setattr(self, 'is_featured', False)
    
    def add_view(self) -> None:
        """Increment view count."""
        current_views = getattr(self, 'views_count', 0) or 0
        setattr(self, 'views_count', current_views + 1)
    
    def add_like(self) -> None:
        """Increment like count."""
        current_likes = getattr(self, 'likes_count', 0) or 0
        setattr(self, 'likes_count', current_likes + 1)
    
    def remove_like(self) -> None:
        """Decrement like count."""
        current_likes = getattr(self, 'likes_count', 0) or 0
        setattr(self, 'likes_count', max(0, current_likes - 1))
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the post."""
        current_tags = self.tag_list
        if tag not in current_tags:
            current_tags.append(tag)
            setattr(self, 'tags', current_tags)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the post."""
        current_tags = self.tag_list
        if tag in current_tags:
            current_tags.remove(tag)
            setattr(self, 'tags', current_tags)
    
    def has_tag(self, tag: str) -> bool:
        """Check if post has a specific tag."""
        return tag in self.tag_list
    
    def update_reading_time(self) -> None:
        """Calculate and update reading time based on content."""
        content_val = getattr(self, 'content', None)
        if content_val:
            # Average reading speed is ~200 words per minute
            word_count = len(str(content_val).split())
            setattr(self, 'read_time_minutes', max(1, round(word_count / 200)))
    
    def generate_excerpt(self, length: int = 200) -> str:
        """Generate excerpt from content if not set."""
        from sqlalchemy import Column
        excerpt_value = getattr(self, 'excerpt', None)
        if excerpt_value and not isinstance(excerpt_value, Column):
            return str(excerpt_value)
        
        content_val = getattr(self, 'content', None)
        if not content_val:
            return ""
        
        # Strip HTML tags and get first N characters
        import re
        clean_content = re.sub(r'<[^>]+>', '', str(content_val))
        
        if len(clean_content) <= length:
            return clean_content
        
        # Find last complete word within length limit
        excerpt = clean_content[:length]
        last_space = excerpt.rfind(' ')
        
        if last_space > 0:
            excerpt = excerpt[:last_space]
        
        return excerpt + "..."
    
    def to_dict(self) -> Dict[str, Any]:
        """Override to include computed properties."""
        data = super().to_dict()
        
        # Add computed properties
        data.update({
            'reading_time': self.reading_time,
            'is_recent': self.is_recent,
            'excerpt_short': self.excerpt_short,
            'word_count': self.word_count,
            'tag_list': self.tag_list,
            'published_date_formatted': self.published_date_formatted,
            'engagement_score': self.engagement_score,
            'url': self.url,
        })
        
        return data