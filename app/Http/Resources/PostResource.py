from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING, Union
from datetime import datetime
from fastapi import Request
from app.Http.Resources.JsonResource import JsonResource

if TYPE_CHECKING:
    from app.Models.Post import Post


class PostResource(JsonResource):
    """
    Laravel-style Post Resource for API transformations.
    
    Transforms Post model instances into standardized API responses
    with conditional data loading and relationship handling.
    """
    
    def __init__(self, resource: Post, request: Optional[Request] = None) -> None:
        super().__init__(resource, request)
        self.post = resource  # Type hint for better IDE support
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Transform the post into an array."""
        return {
            # Basic post data
            'id': self.post.id,
            'title': self.post.title,
            'slug': self.post.slug,
            'excerpt': self.post.excerpt,
            'content': self.when(
                self._should_include_full_content(),
                self.post.content,
                self.post.excerpt_short
            ),
            
            # Metadata
            'category': self.post.category,
            'tags': self.post.tag_list,
            'status': self.post.status,
            'is_published': self.post.is_published,
            'is_featured': self.post.is_featured,
            
            # Computed attributes
            'reading_time': self.post.reading_time,
            'word_count': self.post.word_count,
            'engagement_score': self.post.engagement_score,
            'is_recent': self.post.is_recent,
            'url': self.post.url,
            
            # Engagement metrics
            'stats': {
                'views': self.post.views_count or 0,
                'likes': self.post.likes_count or 0,
                'comments': self.post.comments_count or 0,
            },
            
            # SEO data (conditional)
            **self.merge_when(
                self._should_include_seo(),
                {
                    'seo': {
                        'meta_title': self.post.meta_title,
                        'meta_description': self.post.meta_description,
                        'meta_keywords': self.post.meta_keywords,
                    }
                }
            ),
            
            # Publishing info
            'published_at': self.post.published_at.isoformat() if self.post.published_at and hasattr(self.post.published_at, 'isoformat') else str(self.post.published_at) if self.post.published_at else None,
            'published_date_formatted': self.post.published_date_formatted,
            
            # Author info (when loaded)
            'author': self.when_loaded(
                'author',
                lambda: {
                    'id': self.post.author.id,
                    'name': self.post.author.name,
                    'avatar': getattr(self.post.author, 'avatar_url', None),
                } if hasattr(self.post, 'author') and self.post.author else None
            ),
            
            # Relationships (conditional loading)
            'comments': self.when_loaded(
                'comments',
                lambda: [
                    {
                        'id': comment.id,
                        'content': comment.content,
                        'author': comment.author_name,
                        'created_at': comment.created_at.isoformat(),
                    }
                    for comment in (self.post.comments if hasattr(self.post, 'comments') else [])
                ]
            ),
            
            # Timestamps
            'created_at': self.post.created_at.isoformat() if self.post.created_at else None,
            'updated_at': self.post.updated_at.isoformat() if self.post.updated_at else None,
        }
    
    def _should_include_full_content(self) -> bool:
        """Determine if full content should be included."""
        if not self.request:
            return True
        
        # Include full content for single post requests or when explicitly requested
        include_content = self.request.query_params.get('include_content', '').lower()
        return (
            include_content in ['true', '1', 'yes'] or
            str(self.request.url.path).count('/') > 4  # type: ignore[attr-defined] # Assume single post if deep path
        )
    
    def _should_include_seo(self) -> bool:
        """Determine if SEO data should be included."""
        if not self.request:
            return False
        
        # Include SEO data when explicitly requested
        include_seo = self.request.query_params.get('include_seo', '').lower()
        return include_seo in ['true', '1', 'yes']
    
    def minimal(self) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Return minimal post data for listings."""
        return {
            'id': self.post.id,
            'title': self.post.title,
            'slug': self.post.slug,
            'excerpt': self.post.excerpt_short,
            'category': self.post.category,
            'tags': self.post.tag_list[:3],  # Only first 3 tags
            'reading_time': self.post.reading_time,
            'is_featured': self.post.is_featured,
            'stats': {
                'views': self.post.views_count or 0,
                'likes': self.post.likes_count or 0,
            },
            'published_at': self.post.published_at.isoformat() if self.post.published_at and hasattr(self.post.published_at, 'isoformat') else str(self.post.published_at) if self.post.published_at else None,
            'url': self.post.url,
        }


class PostListResource(PostResource):
    """
    Specialized resource for post listings.
    
    Provides optimized data structure for list views with minimal data.
    """
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Transform post for list view."""
        return self.minimal()


class PostDetailResource(PostResource):
    """
    Specialized resource for post detail views.
    
    Includes comprehensive data and relationships.
    """
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Transform post for detail view."""
        data = super().to_array()
        
        # Always include full content for detail view
        data['content'] = self.post.content
        
        # Include additional detail-specific data
        data.update({
            'difficulty_level': self.post.difficulty_level,
            'language': self.post.language,
            
            # Admin-only fields (when appropriate)
            **self.merge_when(
                self._is_admin_or_author(),
                {
                    'author_notes': self.post.author_notes,
                    'internal_stats': {
                        'total_revisions': getattr(self.post, 'revision_count', 0),
                        'last_modified_by': getattr(self.post, 'last_modified_by', None),
                    }
                }
            ),
            
            # Related posts (when available)
            'related_posts': self.when_loaded(
                'related_posts',
                lambda: [
                    PostListResource(post).to_array()
                    for post in (getattr(self.post, 'related_posts', [])[:5])
                ]
            ),
        })
        
        return data
    
    def _is_admin_or_author(self) -> bool:
        """Check if current user is admin or the post author."""
        # This would integrate with your authentication system
        # For now, return False as a placeholder
        return False


class PostSitemapResource(PostResource):
    """
    Minimal resource for sitemap generation.
    """
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Transform post for sitemap."""
        return {
            'url': self.post.url,
            'last_modified': self.post.updated_at.isoformat() if self.post.updated_at else None,
            'priority': 0.8 if self.post.is_featured else 0.6,
            'change_frequency': 'monthly',
        }


class PostSearchResource(PostResource):
    """
    Optimized resource for search results.
    """
    
    def to_array(self, request: Optional[Request] = None) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]], List[Union[str, int, bool, None]]]]:
        """Transform post for search results."""
        return {
            'id': self.post.id,
            'title': self.post.title,
            'slug': self.post.slug,
            'excerpt': self.post.excerpt_short,
            'category': self.post.category,
            'tags': self.post.tag_list,
            'reading_time': self.post.reading_time,
            'published_at': self.post.published_at.isoformat() if self.post.published_at and hasattr(self.post.published_at, 'isoformat') else str(self.post.published_at) if self.post.published_at else None,
            'url': self.post.url,
            'relevance_score': getattr(self.post, 'search_score', 0.0),
            'highlight': getattr(self.post, 'search_highlight', None),
        }