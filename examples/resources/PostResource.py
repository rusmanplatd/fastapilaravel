"""
Example Post Resource for transforming Post models
"""
from __future__ import annotations

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.Http.Resources.JsonResource import JsonResource
from examples.models.Post import Post


class PostResource(JsonResource):
    """
    Laravel-style Resource for transforming Post models
    """
    
    def __init__(self, resource: Post):
        super().__init__(resource)
        self.post = resource
    
    def to_array(self) -> Dict[str, Any]:
        """Transform the resource into an array"""
        return {
            'id': self.post.id,
            'title': self.post.title,
            'content': self.post.content,
            'excerpt': self.post.excerpt,
            'slug': self.post.slug,
            'is_published': self.post.is_published,
            'published_at': self.format_date(self.post.published_at),
            'metadata': self.post.get_attribute('metadata'),
            'created_at': self.format_date(self.post.created_at),
            'updated_at': self.format_date(self.post.updated_at),
            
            # Conditional relationships
            'author': self.when_loaded('author', lambda: self.post.author_name),
            'category': self.when_loaded('category', lambda: {
                'id': self.post.category.id,
                'name': self.post.category.name,
                'slug': self.post.category.slug
            } if self.post.category else None),
            'tags': self.when_loaded('tags', lambda: [
                {
                    'id': tag.id,
                    'name': tag.name,
                    'slug': tag.slug
                } for tag in self.post.tags
            ]),
            'comments_count': self.when_loaded('comments', lambda: self.post.comment_count),
            
            # Computed attributes
            'read_time_minutes': self.calculate_read_time(),
            'word_count': len(self.post.content.split()) if self.post.content else 0,
            'status': 'published' if self.post.is_published else 'draft',
            'excerpt_preview': self.post.excerpt or self.post.content[:150] + '...' if self.post.content else '',
            
            # URLs (would be generated based on your routing)
            'urls': {
                'view': f"/posts/{self.post.slug}",
                'edit': f"/admin/posts/{self.post.id}/edit",
                'api': f"/api/v1/posts/{self.post.id}",
            }
        }
    
    def calculate_read_time(self) -> int:
        """Calculate estimated read time in minutes"""
        if not self.post.content:
            return 0
        
        word_count = len(self.post.content.split())
        # Average reading speed is 200-250 words per minute
        read_time = max(1, word_count // 225)
        return read_time
    
    def format_date(self, date: Optional[datetime]) -> Optional[str]:
        """Format datetime for API response"""
        if date is None:
            return None
        return date.isoformat()


class PostDetailResource(PostResource):
    """
    Detailed Post Resource with additional data for single post view
    """
    
    def to_array(self) -> Dict[str, Any]:
        """Transform with additional detail data"""
        base_data = super().to_array()
        
        # Add additional detail fields
        base_data.update({
            # Always include relationships for detail view
            'author': {
                'id': self.post.author.id if self.post.author else None,
                'name': self.post.author.name if self.post.author else 'Unknown',
                'email': self.post.author.email if self.post.author else None,
            } if hasattr(self.post, 'author') else None,
            
            'category': {
                'id': self.post.category.id,
                'name': self.post.category.name,
                'slug': self.post.category.slug,
                'description': self.post.category.description,
            } if self.post.category else None,
            
            'tags': [
                {
                    'id': tag.id,
                    'name': tag.name,
                    'slug': tag.slug,
                    'description': tag.description,
                    'post_count': tag.post_count
                } for tag in self.post.tags
            ],
            
            # Include recent comments for detail view
            'recent_comments': [
                {
                    'id': comment.id,
                    'content': comment.content[:100] + '...' if len(comment.content) > 100 else comment.content,
                    'author_name': comment.author_name,
                    'created_at': self.format_date(comment.created_at),
                } for comment in self.post.comments[:5]  # Latest 5 comments
            ] if hasattr(self.post, 'comments') else [],
            
            # SEO and meta information
            'seo': {
                'meta_title': self.post.metadata.get('meta_title') if self.post.metadata else self.post.title,
                'meta_description': self.post.metadata.get('meta_description') if self.post.metadata else self.post.excerpt,
                'canonical_url': f"/posts/{self.post.slug}",
                'og_image': self.post.metadata.get('og_image') if self.post.metadata else None,
            }
        })
        
        return base_data


class PostSummaryResource(JsonResource):
    """
    Minimal Post Resource for listings and collections
    """
    
    def __init__(self, resource: Post):
        super().__init__(resource)
        self.post = resource
    
    def to_array(self) -> Dict[str, Any]:
        """Transform with minimal data for listings"""
        return {
            'id': self.post.id,
            'title': self.post.title,
            'excerpt': self.post.excerpt or self.post.content[:100] + '...' if self.post.content else '',
            'slug': self.post.slug,
            'is_published': self.post.is_published,
            'published_at': self.format_date(self.post.published_at),
            'author_name': self.post.author_name,
            'category_name': self.post.category.name if self.post.category else None,
            'tags_count': len(self.post.tags),
            'comments_count': self.post.comment_count,
            'read_time_minutes': self.calculate_read_time(),
            'created_at': self.format_date(self.post.created_at),
        }
    
    def calculate_read_time(self) -> int:
        """Calculate estimated read time in minutes"""
        if not self.post.content:
            return 0
        
        word_count = len(self.post.content.split())
        read_time = max(1, word_count // 225)
        return read_time
    
    def format_date(self, date: Optional[datetime]) -> Optional[str]:
        """Format datetime for API response"""
        if date is None:
            return None
        return date.isoformat()