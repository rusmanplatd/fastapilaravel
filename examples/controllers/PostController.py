"""
Example Post Resource Controller demonstrating Laravel-style RESTful operations
"""
from __future__ import annotations

from typing import Dict, Any, List
from fastapi import Request, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import or_

from app.Http.Controllers.ResourceController import ApiResourceController
from examples.models.Post import Post
from examples.resources.PostResource import PostResource


class CreatePostSchema(BaseModel):
    """Schema for creating posts"""
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    excerpt: str | None = Field(None, max_length=500)
    category_id: str | None = None
    tag_ids: List[str] = Field(default_factory=list)
    is_published: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdatePostSchema(BaseModel):
    """Schema for updating posts"""
    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = Field(None, min_length=1)
    excerpt: str | None = Field(None, max_length=500)
    category_id: str | None = None
    tag_ids: List[str] | None = None
    is_published: bool | None = None
    metadata: Dict[str, Any] | None = None


class PostController(ApiResourceController):
    """
    Laravel-style Resource Controller for Posts
    Provides full CRUD operations with RESTful endpoints
    """
    
    # Required class attributes
    model_class = Post
    resource_class = PostResource
    create_schema = CreatePostSchema
    update_schema = UpdatePostSchema
    
    # Controller configuration
    per_page = 10
    max_per_page = 50
    middleware = ['auth', 'throttle:60,1']
    
    def apply_search(self, query, search: str):
        """Apply search filters to posts"""
        # Search in title, content, and excerpt
        search_term = f"%{search}%"
        return query.where(
            or_(
                Post.title.ilike(search_term),
                Post.content.ilike(search_term),
                Post.excerpt.ilike(search_term)
            )
        )
    
    def apply_sorting(self, query, sort_by: str, sort_order: str):
        """Apply sorting to posts"""
        # Allowed sort fields
        allowed_sorts = ['title', 'created_at', 'updated_at', 'published_at']
        
        if sort_by not in allowed_sorts:
            sort_by = 'created_at'
        
        sort_column = getattr(Post, sort_by)
        
        if sort_order.lower() == 'asc':
            return query.order_by(sort_column.asc())
        else:
            return query.order_by(sort_column.desc())
    
    async def create_item(self, data: Dict[str, Any], request: Request) -> Post:
        """Create new post with tags"""
        # Extract tag IDs
        tag_ids = data.pop('tag_ids', [])
        
        # Create post
        post = await super().create_item(data, request)
        
        # Attach tags if provided
        if tag_ids:
            from examples.models.Tag import Tag
            tags = await Tag.find_by_ids(tag_ids)
            post.sync_tags(tags)
            await post.save()
        
        return post
    
    async def update_item(self, post: Post, data: Dict[str, Any], request: Request) -> Post:
        """Update post with tags"""
        # Extract tag IDs
        tag_ids = data.pop('tag_ids', None)
        
        # Update post
        updated_post = await super().update_item(post, data, request)
        
        # Update tags if provided
        if tag_ids is not None:
            from examples.models.Tag import Tag
            tags = await Tag.find_by_ids(tag_ids)
            updated_post.sync_tags(tags)
            await updated_post.save()
        
        return updated_post
    
    async def published(self, request: Request) -> Dict[str, Any]:
        """Get only published posts (GET /posts/published)"""
        # Build query with published scope
        query = self.build_index_query(request)
        query = Post.scope_published(query)
        
        # Apply pagination
        page = int(request.query_params.get('page', 1))
        per_page = min(int(request.query_params.get('per_page', self.per_page)), self.max_per_page)
        
        total = await self.count_query(query)
        offset = (page - 1) * per_page
        items = await self.paginate_query(query, offset, per_page)
        
        # Transform with resource
        resource_collection = [self.resource_class(item) for item in items]
        
        return {
            'data': [resource.to_dict() for resource in resource_collection],
            'meta': {
                'total': total,
                'per_page': per_page,
                'current_page': page,
                'last_page': (total + per_page - 1) // per_page,
            }
        }
    
    async def drafts(self, request: Request) -> Dict[str, Any]:
        """Get only draft posts (GET /posts/drafts)"""
        # Build query with draft scope
        query = self.build_index_query(request)
        query = Post.scope_draft(query)
        
        # Apply pagination (similar to published method)
        page = int(request.query_params.get('page', 1))
        per_page = min(int(request.query_params.get('per_page', self.per_page)), self.max_per_page)
        
        total = await self.count_query(query)
        offset = (page - 1) * per_page
        items = await self.paginate_query(query, offset, per_page)
        
        resource_collection = [self.resource_class(item) for item in items]
        
        return {
            'data': [resource.to_dict() for resource in resource_collection],
            'meta': {
                'total': total,
                'per_page': per_page,
                'current_page': page,
                'last_page': (total + per_page - 1) // per_page,
            }
        }
    
    async def by_author(self, author_id: str, request: Request) -> Dict[str, Any]:
        """Get posts by specific author (GET /posts/author/{author_id})"""
        # Build query with author scope
        query = self.build_index_query(request)
        query = Post.scope_by_author(query, author_id)
        
        # Apply pagination
        page = int(request.query_params.get('page', 1))
        per_page = min(int(request.query_params.get('per_page', self.per_page)), self.max_per_page)
        
        total = await self.count_query(query)
        offset = (page - 1) * per_page
        items = await self.paginate_query(query, offset, per_page)
        
        resource_collection = [self.resource_class(item) for item in items]
        
        return {
            'data': [resource.to_dict() for resource in resource_collection],
            'meta': {
                'total': total,
                'per_page': per_page,
                'current_page': page,
                'last_page': (total + per_page - 1) // per_page,
            }
        }
    
    async def publish(self, id: str, request: Request) -> Dict[str, Any]:
        """Publish a post (POST /posts/{id}/publish)"""
        post = await self.find_or_fail(id)
        
        # Check if user can publish this post
        current_user = request.state.user
        if not post.is_authored_by(current_user) and not current_user.can('publish-posts'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to publish this post"
            )
        
        post.publish()
        await post.save()
        
        resource = self.resource_class(post)
        return {
            'data': resource.to_dict(),
            'message': 'Post published successfully'
        }
    
    async def unpublish(self, id: str, request: Request) -> Dict[str, Any]:
        """Unpublish a post (POST /posts/{id}/unpublish)"""
        post = await self.find_or_fail(id)
        
        # Check if user can unpublish this post
        current_user = request.state.user
        if not post.is_authored_by(current_user) and not current_user.can('publish-posts'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to unpublish this post"
            )
        
        post.unpublish()
        await post.save()
        
        resource = self.resource_class(post)
        return {
            'data': resource.to_dict(),
            'message': 'Post unpublished successfully'
        }
    
    async def duplicate(self, id: str, request: Request) -> Dict[str, Any]:
        """Duplicate a post (POST /posts/{id}/duplicate)"""
        original_post = await self.find_or_fail(id)
        
        # Create duplicate data
        duplicate_data = {
            'title': f"{original_post.title} (Copy)",
            'content': original_post.content,
            'excerpt': original_post.excerpt,
            'category_id': original_post.category_id,
            'is_published': False,  # Duplicates start as drafts
            'metadata': original_post.get_attribute('metadata') or {}
        }
        
        # Create duplicate
        duplicate_post = await self.create_item(duplicate_data, request)
        
        # Copy tags
        if original_post.tags:
            duplicate_post.sync_tags(original_post.tags)
            await duplicate_post.save()
        
        resource = self.resource_class(duplicate_post)
        return {
            'data': resource.to_dict(),
            'message': 'Post duplicated successfully'
        }