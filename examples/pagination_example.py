"""
Laravel-style Pagination Example for FastAPI Laravel

This example demonstrates comprehensive pagination usage including:
- Length-aware pagination
- Simple pagination
- Cursor-based pagination
- FastAPI dependencies
- Custom pagination middleware
- Various response formats
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio

from fastapi import FastAPI, Depends, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Pagination imports
from app.Pagination.PaginationFactory import pagination_factory, query_paginator
from app.Pagination.LengthAwarePaginator import LengthAwarePaginator, CursorPaginator
from app.Pagination.Dependencies import (
    PaginationDep, SimplePaginationDep, BasicPagination, 
    create_model_pagination_dependency, PaginationResponse
)
from app.Pagination.Middleware import PaginationMiddleware, PaginationCacheMiddleware

# Database setup for example
DATABASE_URL = "sqlite:///./pagination_example.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Example models
class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    author = Column(String, index=True)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI(
    title="Pagination Example",
    description="Demonstrates Laravel-style pagination in FastAPI",
    version="1.0.0"
)

# Add pagination middleware
app.add_middleware(PaginationMiddleware, auto_detect=True, add_headers=True)
app.add_middleware(PaginationCacheMiddleware, cache_duration=300)


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create model-specific pagination dependencies
PostPagination = create_model_pagination_dependency(
    model_class=Post,
    default_per_page=10,
    max_per_page=100,
    searchable_fields=['title', 'content', 'author'],
    filterable_fields=['author', 'published'],
    sortable_fields=['id', 'title', 'author', 'created_at', 'updated_at']
)

UserPagination = create_model_pagination_dependency(
    model_class=User,
    default_per_page=15,
    searchable_fields=['username', 'email', 'full_name'],
    filterable_fields=['is_active'],
    sortable_fields=['id', 'username', 'email', 'created_at']
)


# Example 1: Basic pagination with manual implementation
@app.get("/posts/basic")
async def get_posts_basic(
    request: Request,
    db: Session = Depends(get_db),
    pagination: PaginationDep = Depends(BasicPagination)
) -> Dict[str, Any]:
    """Basic pagination example with manual query building."""
    
    # Build query
    query = db.query(Post)
    
    # Apply search
    if pagination.search:
        query = query.filter(
            Post.title.ilike(f"%{pagination.search}%") |
            Post.content.ilike(f"%{pagination.search}%")
        )
    
    # Apply filters
    if 'author' in pagination.filters:
        query = query.filter(Post.author == pagination.filters['author'])
    
    if 'published' in pagination.filters:
        published = pagination.filters['published'].lower() == 'true'
        query = query.filter(Post.published == published)
    
    # Apply sorting
    if pagination.sort == 'title':
        if pagination.order == 'desc':
            query = query.order_by(Post.title.desc())
        else:
            query = query.order_by(Post.title.asc())
    else:
        query = query.order_by(Post.created_at.desc())
    
    # Paginate
    paginator = query_paginator.paginate(
        query=query,
        page=pagination.page,
        per_page=pagination.per_page,
        request=request
    )
    
    # Transform data
    posts_data = [
        {
            "id": post.id,
            "title": post.title,
            "author": post.author,
            "published": post.published,
            "created_at": post.created_at.isoformat()
        }
        for post in paginator.items
    ]
    
    return PaginationResponse.create(posts_data, paginator)


# Example 2: Automatic model pagination using dependency
@app.get("/posts/auto")
async def get_posts_auto(
    request: Request,
    paginated_posts: LengthAwarePaginator = Depends(PostPagination)
) -> Dict[str, Any]:
    """Automatic pagination using model-specific dependency."""
    
    # Transform data
    posts_data = [
        {
            "id": post.id,
            "title": post.title,
            "author": post.author,
            "published": post.published,
            "created_at": post.created_at.isoformat(),
            "excerpt": post.content[:100] + "..." if len(post.content) > 100 else post.content
        }
        for post in paginated_posts.items
    ]
    
    return PaginationResponse.create(posts_data, paginated_posts)


# Example 3: Simple pagination (no total count)
@app.get("/posts/simple")
async def get_posts_simple(
    request: Request,
    db: Session = Depends(get_db),
    pagination: SimplePaginationDep = Depends()
) -> Dict[str, Any]:
    """Simple pagination without total count for better performance."""
    
    # Build and paginate query
    query = db.query(Post).order_by(Post.created_at.desc())
    
    paginator = query_paginator.simple_paginate(
        query=query,
        page=pagination['page'],
        per_page=pagination['per_page'],
        request=request
    )
    
    # Transform data
    posts_data = [
        {
            "id": post.id,
            "title": post.title,
            "author": post.author,
            "created_at": post.created_at.isoformat()
        }
        for post in paginator.items
    ]
    
    return PaginationResponse.create(posts_data, paginator)


# Example 4: Cursor-based pagination
@app.get("/posts/cursor")
async def get_posts_cursor(
    request: Request,
    db: Session = Depends(get_db),
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    per_page: int = Query(10, ge=1, le=50, description="Items per page")
) -> Dict[str, Any]:
    """Cursor-based pagination for large datasets."""
    
    query = db.query(Post).filter(Post.published == True)
    
    paginator = query_paginator.cursor_paginate(
        query=query,
        cursor_column='id',
        per_page=per_page,
        cursor=cursor,
        request=request,
        direction='desc'
    )
    
    # Transform data
    posts_data = [
        {
            "id": post.id,
            "title": post.title,
            "author": post.author,
            "created_at": post.created_at.isoformat()
        }
        for post in paginator.items
    ]
    
    return PaginationResponse.cursor(posts_data, paginator)


# Example 5: JSON:API compliant pagination
@app.get("/posts/jsonapi")
async def get_posts_jsonapi(
    request: Request,
    paginated_posts: LengthAwarePaginator = Depends(PostPagination)
) -> Dict[str, Any]:
    """JSON:API compliant pagination response."""
    
    # Transform data to JSON:API format
    posts_data = [
        {
            "type": "posts",
            "id": str(post.id),
            "attributes": {
                "title": post.title,
                "content": post.content,
                "author": post.author,
                "published": post.published,
                "created_at": post.created_at.isoformat(),
                "updated_at": post.updated_at.isoformat()
            }
        }
        for post in paginated_posts.items
    ]
    
    return PaginationResponse.json_api(posts_data, paginated_posts)


# Example 6: Custom pagination with transformation
@app.get("/posts/transformed")
async def get_posts_transformed(
    request: Request,
    db: Session = Depends(get_db),
    pagination: PaginationDep = Depends(BasicPagination)
) -> Dict[str, Any]:
    """Pagination with data transformation and custom response."""
    
    # Get paginated data
    query = db.query(Post).order_by(Post.created_at.desc())
    paginator = query_paginator.paginate(
        query=query,
        page=pagination.page,
        per_page=pagination.per_page,
        request=request
    )
    
    # Transform using paginator methods
    transformed_paginator = paginator.transform(lambda post: {
        "id": post.id,
        "title": post.title.upper(),  # Transform title to uppercase
        "slug": post.title.lower().replace(" ", "-"),
        "author": post.author,
        "word_count": len(post.content.split()),
        "reading_time": f"{max(1, len(post.content.split()) // 200)} min read",
        "status": "published" if post.published else "draft",
        "created_at": post.created_at.isoformat()
    })
    
    return {
        "posts": transformed_paginator.items,
        "pagination": transformed_paginator.get_meta().__dict__,
        "summary": {
            "total_posts": transformed_paginator.total,
            "current_page_count": transformed_paginator.count(),
            "showing": f"{transformed_paginator.first_item}-{transformed_paginator.last_item} of {transformed_paginator.total}"
        }
    }


# Example 7: Conditional pagination with filtering
@app.get("/posts/conditional")
async def get_posts_conditional(
    request: Request,
    db: Session = Depends(get_db),
    pagination: PaginationDep = Depends(BasicPagination),
    include_drafts: bool = Query(False, description="Include draft posts")
) -> Dict[str, Any]:
    """Conditional pagination with dynamic filtering."""
    
    # Build base query
    query = db.query(Post)
    
    # Create paginator
    paginator = query_paginator.paginate(
        query=query,
        page=pagination.page,
        per_page=pagination.per_page,
        request=request
    )
    
    # Apply conditional filtering using paginator methods
    if not include_drafts:
        paginator = paginator.filter(lambda post: post.published)
    
    # Apply search if provided
    if pagination.search:
        search_term = pagination.search.lower()
        paginator = paginator.filter(
            lambda post: search_term in post.title.lower() or 
                        search_term in post.content.lower()
        )
    
    # Transform data
    posts_data = [
        {
            "id": post.id,
            "title": post.title,
            "author": post.author,
            "published": post.published,
            "created_at": post.created_at.isoformat()
        }
        for post in paginator.items
    ]
    
    return {
        "data": posts_data,
        "meta": {
            "current_page": 1,  # Reset after filtering
            "total": len(posts_data),
            "per_page": pagination.per_page,
            "filters_applied": {
                "include_drafts": include_drafts,
                "search": pagination.search
            }
        }
    }


# Example 8: Users with different pagination settings
@app.get("/users")
async def get_users(
    request: Request,
    paginated_users: LengthAwarePaginator = Depends(UserPagination)
) -> Dict[str, Any]:
    """Users pagination with different settings."""
    
    users_data = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        }
        for user in paginated_users.items
    ]
    
    return PaginationResponse.create(users_data, paginated_users)


# Example 9: Custom pagination response format
@app.get("/posts/custom-format")
async def get_posts_custom_format(
    request: Request,
    paginated_posts: LengthAwarePaginator = Depends(PostPagination)
) -> Dict[str, Any]:
    """Custom pagination response format."""
    
    posts_data = [
        {
            "id": post.id,
            "title": post.title,
            "author": post.author,
            "created_at": post.created_at.isoformat()
        }
        for post in paginated_posts.items
    ]
    
    return {
        "success": True,
        "message": "Posts retrieved successfully",
        "results": posts_data,
        "pagination": {
            "page": paginated_posts.current_page,
            "pages": paginated_posts.last_page,
            "per_page": paginated_posts.per_page,
            "total": paginated_posts.total,
            "showing": f"Showing {paginated_posts.first_item} to {paginated_posts.last_item} of {paginated_posts.total} results",
            "navigation": {
                "first": paginated_posts.url(1),
                "previous": paginated_posts.previous_page_url,
                "next": paginated_posts.next_page_url,
                "last": paginated_posts.url(paginated_posts.last_page)
            }
        }
    }


# Example 10: Pagination with aggregations
@app.get("/posts/with-stats")
async def get_posts_with_stats(
    request: Request,
    db: Session = Depends(get_db),
    pagination: PaginationDep = Depends(BasicPagination)
) -> Dict[str, Any]:
    """Pagination with additional statistics."""
    
    # Get paginated posts
    query = db.query(Post)
    paginator = query_paginator.paginate(
        query=query,
        page=pagination.page,
        per_page=pagination.per_page,
        request=request
    )
    
    # Get additional statistics
    total_published = db.query(Post).filter(Post.published == True).count()
    total_drafts = db.query(Post).filter(Post.published == False).count()
    authors_count = db.query(Post.author).distinct().count()
    
    posts_data = [
        {
            "id": post.id,
            "title": post.title,
            "author": post.author,
            "published": post.published,
            "created_at": post.created_at.isoformat()
        }
        for post in paginator.items
    ]
    
    response = PaginationResponse.create(posts_data, paginator)
    
    # Add custom statistics
    response["statistics"] = {
        "total_published": total_published,
        "total_drafts": total_drafts,
        "unique_authors": authors_count,
        "publication_rate": f"{(total_published / paginator.total * 100):.1f}%" if paginator.total > 0 else "0%"
    }
    
    return response


# Utility endpoints for testing
@app.post("/posts/seed")
async def seed_posts(db: Session = Depends(get_db), count: int = Query(50)) -> Dict[str, Any]:
    """Seed database with sample posts for testing."""
    
    authors = ["Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Emma Brown"]
    
    for i in range(count):
        post = Post(
            title=f"Sample Post {i + 1}",
            content=f"This is the content for post {i + 1}. " * 10,
            author=authors[i % len(authors)],
            published=(i % 3 != 0),  # 2/3 published, 1/3 drafts
            created_at=datetime.utcnow()
        )
        db.add(post)
    
    db.commit()
    
    return {"message": f"Created {count} sample posts"}


@app.post("/users/seed")
async def seed_users(db: Session = Depends(get_db), count: int = Query(25)) -> Dict[str, Any]:
    """Seed database with sample users for testing."""
    
    for i in range(count):
        user = User(
            username=f"user_{i + 1}",
            email=f"user{i + 1}@example.com",
            full_name=f"User {i + 1}",
            is_active=(i % 4 != 0),  # 3/4 active, 1/4 inactive
            created_at=datetime.utcnow()
        )
        db.add(user)
    
    db.commit()
    
    return {"message": f"Created {count} sample users"}


@app.get("/")
async def root():
    """Root endpoint with API documentation."""
    return {
        "message": "Laravel-style Pagination Example API",
        "endpoints": {
            "basic_pagination": "/posts/basic",
            "auto_pagination": "/posts/auto",
            "simple_pagination": "/posts/simple",
            "cursor_pagination": "/posts/cursor",
            "jsonapi_pagination": "/posts/jsonapi",
            "transformed_pagination": "/posts/transformed",
            "conditional_pagination": "/posts/conditional",
            "users_pagination": "/users",
            "custom_format": "/posts/custom-format",
            "with_statistics": "/posts/with-stats"
        },
        "utilities": {
            "seed_posts": "/posts/seed",
            "seed_users": "/users/seed"
        },
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)