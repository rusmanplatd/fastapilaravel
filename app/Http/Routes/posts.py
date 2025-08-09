from __future__ import annotations

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request
from sqlalchemy.orm import Session

from app.Http.Controllers.PostController import PostController, CreatePostRequest, UpdatePostRequest
from config.database import get_db


# Create the posts router
router = APIRouter(
    prefix="/api/v1/posts",
    tags=["posts"],
    responses={404: {"description": "Not found"}},
)


# Initialize controller dependency
def get_post_controller(db: Session = Depends(get_db)) -> PostController:  # type: ignore[assignment]
    """Dependency to get PostController instance."""
    return PostController(db=db)


# Laravel-style Resource Routes
# These map to the standard ResourceController methods

@router.get("", summary="List all posts")
async def index(
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """
    List all posts with pagination, filtering, and search.
    
    Query Parameters:
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
    """
    return await controller.index(request)


@router.post("", summary="Create a new post", status_code=status.HTTP_201_CREATED)
async def store(
    request: Request,
    data: CreatePostRequest,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Create a new post."""
    return await controller.store(data.dict(), request)


@router.get("/{post_id}", summary="Get a specific post")
async def show(
    post_id: str,
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """
    Get a specific post by ID.
    
    Query Parameters:
    - include: Include relationships (author,comments,related_posts)
    - include_seo: Include SEO metadata (true/false)
    """
    return await controller.show(post_id, request)


@router.put("/{post_id}", summary="Update a post")
async def update(
    post_id: str,
    request: Request,
    data: UpdatePostRequest,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Update an existing post."""
    return await controller.update(post_id, data.dict(exclude_unset=True), request)


@router.put("/{post_id}/patch", summary="Partially update a post")
async def patch(
    post_id: str,
    request: Request,
    data: UpdatePostRequest,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Partially update an existing post."""
    return await controller.update(post_id, data.dict(exclude_unset=True), request)


@router.delete("/{post_id}", summary="Delete a post")
async def destroy(
    post_id: str,
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Delete a post."""
    return await controller.destroy(post_id, request)


# Custom Resource Routes
# These go beyond standard CRUD operations

@router.get("/featured", summary="Get featured posts")
async def featured(
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """
    Get featured posts.
    
    Query Parameters:
    - sort_by: Sort by (published_at, popularity, engagement)
    - limit: Maximum number of posts (default: 6, max: 20)
    """
    return await controller.featured(request)


@router.get("/category/{category}", summary="Get posts by category")
async def by_category(
    category: str,
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Get all posts in a specific category."""
    return await controller.by_category(category, request)


@router.get("/tag/{tag}", summary="Get posts by tag")
async def by_tag(
    tag: str,
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Get all posts with a specific tag."""
    return await controller.by_tag(tag, request)


@router.put("/{post_id}/publish", summary="Publish a post")
async def publish(
    post_id: str,
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Publish a draft post."""
    return await controller.publish(post_id, request)


@router.put("/{post_id}/unpublish", summary="Unpublish a post")
async def unpublish(
    post_id: str,
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Unpublish a published post."""
    return await controller.unpublish(post_id, request)


# Bulk Operations (from ApiResourceController)

@router.post("/bulk", summary="Bulk create posts")
async def bulk_store(
    request: Request,
    data: List[CreatePostRequest],
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Create multiple posts at once."""
    data_dicts = [item.dict() for item in data]
    return await controller.bulk_store(data_dicts, request)


@router.put("/bulk", summary="Bulk update posts")
async def bulk_update(
    request: Request,
    data: List[Dict[str, Any]],  # Each dict should include 'id' field
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Update multiple posts at once."""
    return await controller.bulk_update(data, request)


@router.delete("/bulk", summary="Bulk delete posts")
async def bulk_destroy(
    request: Request,
    ids: List[str],
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Delete multiple posts at once."""
    return await controller.bulk_destroy(ids, request)


# Additional API endpoints that might be useful

@router.get("/{post_id}/related", summary="Get related posts")
async def related(
    post_id: str,
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Get posts related to the specified post."""
    # This would be implemented as a custom method in the controller
    # For now, we'll use a placeholder
    post = await controller.find_or_fail(post_id)
    
    # In a real implementation, you'd find related posts by tags, category, etc.
    related_posts: List[Dict[str, Any]] = []
    
    return {
        'data': related_posts,
        'meta': {
            'related_to': post.id,
            'total': len(related_posts)
        }
    }


@router.post("/{post_id}/like", summary="Like a post")
async def like_post(
    post_id: str,
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Like a post (increment like count)."""
    post = await controller.find_or_fail(post_id)
    post.add_like()
    # await db.commit()  # In real implementation
    
    return {
        'message': 'Post liked successfully',
        'data': {
            'id': post.id,
            'likes_count': post.likes_count
        }
    }


@router.delete("/{post_id}/like", summary="Unlike a post")
async def unlike_post(
    post_id: str,
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Unlike a post (decrement like count)."""
    post = await controller.find_or_fail(post_id)
    post.remove_like()
    # await db.commit()  # In real implementation
    
    return {
        'message': 'Post unliked successfully',
        'data': {
            'id': post.id,
            'likes_count': post.likes_count
        }
    }


@router.get("/{post_id}/stats", summary="Get post statistics")
async def stats(
    post_id: str,
    request: Request,
    controller: PostController = Depends(get_post_controller)  # type: ignore[assignment]
) -> Dict[str, Any]:
    """Get detailed statistics for a post."""
    post = await controller.find_or_fail(post_id)
    
    return {
        'data': {
            'id': post.id,
            'title': post.title,
            'views_count': post.views_count,
            'likes_count': post.likes_count,
            'comments_count': post.comments_count,
            'engagement_score': post.engagement_score,
            'reading_time': post.reading_time,
            'word_count': post.word_count,
            'published_at': post.published_at.isoformat() if post.published_at and hasattr(post.published_at, 'isoformat') else str(post.published_at) if post.published_at else None,
        }
    }