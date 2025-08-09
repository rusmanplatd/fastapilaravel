from __future__ import annotations

from typing import Dict, List, Optional, Type, Union
from datetime import datetime
from fastapi import HTTPException, status, Depends
from starlette.requests import Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.Http.Controllers.ResourceController import ApiResourceController
from app.Http.Resources.PostResource import PostResource, PostListResource, PostDetailResource
from app.Models.Post import Post
from config.database import get_db


# Pydantic schemas for validation
class CreatePostRequest(BaseModel):
    """Schema for creating new posts."""
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=10)
    excerpt: Optional[str] = Field(None, max_length=500)
    category: str = Field(..., max_length=100)
    tags: List[str] = Field(default_factory=list, max_length=10)
    status: str = Field(default='draft', pattern='^(draft|published|archived)$')
    is_featured: bool = Field(default=False)
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=500)
    meta_keywords: Optional[str] = Field(None, max_length=500)
    difficulty_level: Optional[str] = Field(default='beginner', pattern='^(beginner|intermediate|advanced)$')
    language: str = Field(default='en', max_length=10)


class UpdatePostRequest(BaseModel):
    """Schema for updating posts."""
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    content: Optional[str] = Field(None, min_length=10)
    excerpt: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = Field(None, max_length=10)
    status: Optional[str] = Field(None, pattern='^(draft|published|archived)$')
    is_featured: Optional[bool] = None
    meta_title: Optional[str] = Field(None, max_length=255)
    meta_description: Optional[str] = Field(None, max_length=500)
    meta_keywords: Optional[str] = Field(None, max_length=500)
    difficulty_level: Optional[str] = Field(None, pattern='^(beginner|intermediate|advanced)$')
    language: Optional[str] = Field(None, max_length=10)


class PostController(ApiResourceController[Post, PostResource]):
    """
    Laravel-style Post Controller.
    
    Handles CRUD operations for blog posts with full Laravel-style
    resource controller functionality including filtering, sorting,
    searching, and bulk operations.
    """
    
    # Configure the controller
    model_class = Post
    resource_class = PostResource
    create_schema = CreatePostRequest
    update_schema = UpdatePostRequest
    
    # Pagination settings
    per_page = 12
    max_per_page = 50
    
    # API settings
    api_version = 'v1'
    rate_limit = '60/minute'
    
    def __init__(self, db: Session = Depends(get_db)) -> None:  # type: ignore[assignment]
        super().__init__()
        self.db = db
    
    async def index(self, request: Request) -> Dict[str, Union[str, int, bool, List[Dict[str, Union[str, int, bool, None]]]]]:
        """
        List posts with advanced filtering and search.
        
        Query parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 12, max: 50)
        - search: Search term for title/content
        - category: Filter by category
        - status: Filter by status (draft/published/archived)
        - featured: Filter featured posts (true/false)
        - tags: Filter by tags (comma-separated)
        - author: Filter by author ID
        - sort_by: Sort field (title, created_at, published_at, views_count)
        - sort_order: Sort direction (asc/desc)
        - include: Include relationships (author,comments)
        """
        # Use list-optimized resource for performance
        self.resource_class = PostListResource
        
        return await super().index(request)
    
    async def show(self, id: str, request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]]]]:
        """
        Show a specific post with full details.
        
        Query parameters:
        - include: Include relationships (author,comments,related_posts)
        - include_seo: Include SEO metadata (true/false)
        """
        # Use detail-optimized resource
        self.resource_class = PostDetailResource
        
        result = await super().show(id, request)
        
        # Increment view count if it's a public request
        if self._should_increment_views(request):
            post = await self.find_or_fail(id)
            post.add_view()
            # In real implementation, you'd save this to database
            # await self.db.commit()
        
        return result
    
    async def store(self, data: Dict[str, Union[str, int, bool, List[str]]], request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]]]]:
        """Create a new post."""
        # Add current user as author if authenticated
        current_user = self._get_current_user(request)
        if current_user:
            data['author_id'] = current_user.id
        
        # Auto-generate excerpt if not provided
        if not data.get('excerpt') and data.get('content'):
            data['excerpt'] = self._generate_excerpt(data['content'])
        
        return await super().store(data, request)
    
    async def update(self, id: str, data: Dict[str, Union[str, int, bool, List[str]]], request: Request) -> Dict[str, Union[str, int, bool, None, Dict[str, Union[str, int, bool, None]]]]:
        """Update an existing post."""
        # Check if user can update this post
        post = await self.find_or_fail(id)
        current_user = self._get_current_user(request)
        
        if not self._can_edit_post(post, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this post"
            )
        
        # Auto-update excerpt if content changed
        if 'content' in data and not data.get('excerpt'):
            data['excerpt'] = self._generate_excerpt(data['content'])
        
        return await super().update(id, data, request)
    
    async def destroy(self, id: str, request: Request) -> Dict[str, Union[str, bool]]:
        """Delete a post."""
        # Check permissions
        post = await self.find_or_fail(id)
        current_user = self._get_current_user(request)
        
        if not self._can_delete_post(post, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this post"
            )
        
        return await super().destroy(id, request)
    
    # Custom endpoints beyond standard CRUD
    
    async def publish(self, id: str, request: Request) -> Dict[str, Union[str, bool, Dict[str, Union[str, int, bool, None]]]]:
        """Publish a post (PUT /posts/{id}/publish)."""
        post = await self.find_or_fail(id)
        current_user = self._get_current_user(request)
        
        if not self._can_edit_post(post, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to publish this post"
            )
        
        post.publish()
        # await self.db.commit()  # In real implementation
        
        resource = PostDetailResource(post, request)
        return {
            'data': resource.to_array(),
            'message': 'Post published successfully'
        }
    
    async def unpublish(self, id: str, request: Request) -> Dict[str, Union[str, bool, Dict[str, Union[str, int, bool, None]]]]:
        """Unpublish a post (PUT /posts/{id}/unpublish)."""
        post = await self.find_or_fail(id)
        current_user = self._get_current_user(request)
        
        if not self._can_edit_post(post, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to unpublish this post"
            )
        
        post.unpublish()
        # await self.db.commit()  # In real implementation
        
        resource = PostDetailResource(post, request)
        return {
            'data': resource.to_array(),
            'message': 'Post unpublished successfully'
        }
    
    async def featured(self, request: Request) -> Dict[str, Union[str, int, bool, List[Dict[str, Union[str, int, bool, None]]]]]:
        """Get featured posts (GET /posts/featured)."""
        # Build query for featured posts
        query = self.db.query(Post).filter(Post.is_featured == True, Post.is_published == True)
        
        # Apply sorting (featured posts usually by popularity or date)
        sort_by = request.query_params.get('sort_by', 'published_at')
        if sort_by == 'popularity':
            query = query.order_by(Post.views_count.desc())
        elif sort_by == 'engagement':
            # Sort by engagement score (calculated field)
            query = query.order_by((Post.likes_count + Post.comments_count).desc())  # type: ignore[operator]
        else:
            query = query.order_by(Post.published_at.desc())
        
        # Limit results
        limit = min(int(request.query_params.get('limit', 6)), 20)
        posts = query.limit(limit).all()
        
        # Transform with resources
        resource_collection = [PostListResource(post, request) for post in posts]
        
        return {
            'data': [resource.to_array() for resource in resource_collection],
            'meta': {
                'total': len(posts),
                'type': 'featured'
            }
        }
    
    async def by_category(self, category: str, request: Request) -> Dict[str, Union[str, int, bool, List[Dict[str, Union[str, int, bool, None]]]]]:
        """Get posts by category (GET /posts/category/{category})."""
        # Temporarily modify query to filter by category
        original_query_method = self.build_index_query
        
        def category_query(req: Request) -> object:
            query = original_query_method(req)
            return query.filter(Post.category == category, Post.is_published == True)
        
        setattr(self, 'build_index_query', category_query)
        
        try:
            result = await self.index(request)
            result['meta']['category'] = category
            return result
        finally:
            # Restore original method
            setattr(self, 'build_index_query', original_query_method)
    
    async def by_tag(self, tag: str, request: Request) -> Dict[str, Union[str, int, bool, List[Dict[str, Union[str, int, bool, None]]]]]:
        """Get posts by tag (GET /posts/tag/{tag})."""
        # Temporarily modify query to filter by tag
        original_query_method = self.build_index_query
        
        def tag_query(req: Request) -> object:
            query = original_query_method(req)
            return query.filter(Post.tags.contains(tag), Post.is_published == True)  # type: ignore[attr-defined]
        
        setattr(self, 'build_index_query', tag_query)
        
        try:
            result = await self.index(request)
            result['meta']['tag'] = tag
            return result
        finally:
            # Restore original method
            setattr(self, 'build_index_query', original_query_method)
    
    # Override ResourceController methods for database integration
    
    def build_index_query(self, request: Request) -> object:
        """Build the base query for listing posts."""
        query = self.db.query(Post)
        
        # Apply filters from query parameters
        category = request.query_params.get('category')
        if category:
            query = query.filter(Post.category == category)
        
        status = request.query_params.get('status')
        if status:
            query = query.filter(Post.status == status)
        elif not request.query_params.get('show_all'):
            # Default to published only for public API
            query = query.filter(Post.is_published == True)
        
        featured = request.query_params.get('featured')
        if featured and featured.lower() == 'true':
            query = query.filter(Post.is_featured == True)
        
        author = request.query_params.get('author')
        if author:
            query = query.filter(Post.author_id == author)
        
        tags = request.query_params.get('tags')
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            for tag in tag_list:
                query = query.filter(Post.tags.contains(tag))  # type: ignore[attr-defined]
        
        return query
    
    def apply_search(self, query: object, search: str) -> object:
        """Apply search filters to query."""
        if not search:
            return query
        
        # Search in title, excerpt, and content
        search_term = f"%{search}%"
        return query.filter(
            (Post.title.ilike(search_term)) |
            (Post.excerpt.ilike(search_term)) |
            (Post.content.ilike(search_term))
        )
    
    def apply_sorting(self, query: object, sort_by: str, sort_order: str) -> object:
        """Apply sorting to query."""
        from sqlalchemy import desc, asc
        if sort_order.lower() == 'desc':
            order_func = desc
        else:
            order_func = asc
        
        if sort_by == 'title':
            return query.order_by(order_func(Post.title))
        elif sort_by == 'published_at':
            return query.order_by(order_func(Post.published_at))
        elif sort_by == 'views_count':
            return query.order_by(order_func(Post.views_count))
        elif sort_by == 'likes_count':
            return query.order_by(order_func(Post.likes_count))
        else:
            # Default to created_at
            return query.order_by(order_func(Post.created_at))
    
    async def count_query(self, query: object) -> int:
        """Count total records for pagination."""
        return int(query.count())
    
    async def paginate_query(self, query: object, offset: int, limit: int) -> List[Post]:
        """Apply pagination to query."""
        return list(query.offset(offset).limit(limit).all())
    
    async def find_or_fail(self, id: str) -> Post:
        """Find post by ID or raise 404."""
        post = self.db.query(Post).filter(Post.id == id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Post not found"
            )
        return post
    
    async def load_relationships(self, post: Post, relations: List[str]) -> Post:
        """Load specified relationships."""
        # In a real implementation, you'd use SQLAlchemy's eager loading
        # For now, this is a placeholder
        return post
    
    async def create_item(self, data: Dict[str, Union[str, int, bool, List[str]]], request: Request) -> Post:
        """Create new post."""
        post = Post(**data)
        
        # Generate slug if not provided
        if not data.get('slug') and 'title' in data:
            setattr(post, 'slug', post._generate_slug(data['title']))
        
        # Calculate reading time
        post.update_reading_time()
        
        self.db.add(post)
        # await self.db.commit()  # In real implementation
        # await self.db.refresh(post)  # Refresh to get generated ID
        
        return post
    
    async def update_item(self, post: Post, data: Dict[str, Union[str, int, bool, List[str]]], request: Request) -> Post:
        """Update existing post."""
        # Update attributes
        for key, value in data.items():
            if hasattr(post, key):
                setattr(post, key, value)
        
        # Update reading time if content changed
        if 'content' in data:
            post.update_reading_time()
        
        # Update slug if title changed
        if 'title' in data and not data.get('slug'):
            setattr(post, 'slug', post._generate_slug(data['title']))
        
        # await self.db.commit()  # In real implementation
        return post
    
    async def delete_item(self, post: Post, request: Request) -> None:
        """Delete post."""
        self.db.delete(post)
        # await self.db.commit()  # In real implementation
    
    # Helper methods
    
    def _get_current_user(self, request: Request) -> Optional[object]:
        """Get current authenticated user."""
        # This would integrate with your authentication system
        # For now, return None as a placeholder
        return None
    
    def _can_edit_post(self, post: Post, user: Optional[object]) -> bool:
        """Check if user can edit the post."""
        if not user:
            return False
        
        # Admin can edit all posts
        if hasattr(user, 'is_admin') and user.is_admin:
            return True
        
        # Author can edit their own posts
        if post.author_id == user.id:
            return True
        
        return False
    
    def _can_delete_post(self, post: Post, user: Optional[object]) -> bool:
        """Check if user can delete the post."""
        return self._can_edit_post(post, user)
    
    def _should_increment_views(self, request: Request) -> bool:
        """Determine if view count should be incremented."""
        # Don't increment for admin/author requests, crawlers, etc.
        user_agent = request.headers.get('user-agent', '').lower()
        if any(bot in user_agent for bot in ['bot', 'crawl', 'spider']):
            return False
        
        return True
    
    def _generate_excerpt(self, content: str, length: int = 200) -> str:
        """Generate excerpt from content."""
        # Strip HTML and get first N characters
        import re
        clean_content = re.sub(r'<[^>]+>', '', content)
        
        if len(clean_content) <= length:
            return clean_content
        
        # Find last complete word within length limit
        excerpt = clean_content[:length]
        last_space = excerpt.rfind(' ')
        
        if last_space > 0:
            excerpt = excerpt[:last_space]
        
        return excerpt + "..."