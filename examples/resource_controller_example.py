from __future__ import annotations

"""
Laravel-style Resource Controller Example for FastAPI Laravel

This example demonstrates how to use the ResourceController pattern
to create a complete REST API with Laravel-style conventions.
"""

from fastapi import FastAPI
from app.Http.Routes.posts import router as posts_router

# Create FastAPI app
app = FastAPI(
    title="FastAPI Laravel - Resource Controller Example",
    description="Demonstrates Laravel-style resource controllers in FastAPI",
    version="1.0.0"
)

# Include the posts router
app.include_router(posts_router)

# Example of how the API endpoints map to Laravel resource controller methods:
"""
Laravel Resource Routes Mapping:

GET    /api/v1/posts           -> PostController@index    (List all posts)
POST   /api/v1/posts           -> PostController@store    (Create new post)
GET    /api/v1/posts/{id}      -> PostController@show     (Show specific post)
PUT    /api/v1/posts/{id}      -> PostController@update   (Update post)
DELETE /api/v1/posts/{id}      -> PostController@destroy  (Delete post)

Custom Routes:
GET    /api/v1/posts/featured           -> PostController@featured
GET    /api/v1/posts/category/{cat}     -> PostController@by_category
GET    /api/v1/posts/tag/{tag}          -> PostController@by_tag
PUT    /api/v1/posts/{id}/publish       -> PostController@publish
PUT    /api/v1/posts/{id}/unpublish     -> PostController@unpublish

Bulk Operations (ApiResourceController):
POST   /api/v1/posts/bulk      -> PostController@bulk_store
PUT    /api/v1/posts/bulk      -> PostController@bulk_update
DELETE /api/v1/posts/bulk      -> PostController@bulk_destroy
"""

# Example usage with curl commands:
"""
# List posts with pagination and filtering
curl "http://localhost:8000/api/v1/posts?page=1&per_page=10&category=technology&featured=true"

# Create a new post
curl -X POST "http://localhost:8000/api/v1/posts" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Getting Started with FastAPI Laravel",
    "content": "This is a comprehensive guide to using FastAPI Laravel...",
    "category": "technology",
    "tags": ["fastapi", "laravel", "python"],
    "status": "published",
    "is_featured": true
  }'

# Get a specific post with relationships
curl "http://localhost:8000/api/v1/posts/123?include=author,comments&include_seo=true"

# Update a post
curl -X PUT "http://localhost:8000/api/v1/posts/123" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "is_featured": true
  }'

# Get featured posts
curl "http://localhost:8000/api/v1/posts/featured?sort_by=popularity&limit=5"

# Get posts by category
curl "http://localhost:8000/api/v1/posts/category/technology?sort_by=published_at&sort_order=desc"

# Publish a post
curl -X PUT "http://localhost:8000/api/v1/posts/123/publish"

# Bulk create posts
curl -X POST "http://localhost:8000/api/v1/posts/bulk" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "title": "Post 1",
      "content": "Content for post 1...",
      "category": "tech"
    },
    {
      "title": "Post 2", 
      "content": "Content for post 2...",
      "category": "tutorial"
    }
  ]'

# Search posts
curl "http://localhost:8000/api/v1/posts?search=fastapi&sort_by=relevance"
"""

# Example response format:
"""
{
  "data": [
    {
      "id": "01H8XYZ123",
      "title": "Getting Started with FastAPI Laravel",
      "slug": "getting-started-with-fastapi-laravel",
      "excerpt": "Discover how FastAPI Laravel combines...",
      "content": "Full content here...",
      "category": "technology",
      "tags": ["fastapi", "laravel", "python"],
      "status": "published",
      "is_published": true,
      "is_featured": true,
      "reading_time": "5 min read",
      "word_count": 1250,
      "engagement_score": 8.5,
      "is_recent": true,
      "url": "/posts/getting-started-with-fastapi-laravel",
      "stats": {
        "views": 152,
        "likes": 23,
        "comments": 5
      },
      "author": {
        "id": "01H8ABC123",
        "name": "John Doe",
        "avatar": "https://example.com/avatars/john.jpg"
      },
      "published_at": "2024-01-15T10:30:00Z",
      "published_date_formatted": "January 15, 2024",
      "created_at": "2024-01-15T09:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z"
    }
  ],
  "meta": {
    "total": 127,
    "per_page": 10,
    "current_page": 1,
    "last_page": 13,
    "from": 1,
    "to": 10,
    "api_version": "v1",
    "timestamp": "2024-01-15T12:00:00Z"
  },
  "links": {
    "first": "http://localhost:8000/api/v1/posts?page=1&per_page=10",
    "last": "http://localhost:8000/api/v1/posts?page=13&per_page=10",
    "prev": null,
    "next": "http://localhost:8000/api/v1/posts?page=2&per_page=10"
  }
}
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)