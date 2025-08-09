# Laravel-Style Resource Controllers

FastAPI Laravel includes a complete implementation of Laravel-style resource controllers, providing a standardized way to build RESTful APIs with consistent patterns and conventions.

## Overview

Resource controllers handle the typical CRUD (Create, Read, Update, Delete) operations for a resource in a RESTful manner. They follow Laravel's conventions while leveraging FastAPI's async capabilities and type safety.

## Architecture

### Core Components

1. **ResourceController** - Base abstract controller with standard CRUD methods
2. **ApiResourceController** - Extended controller with API-specific features
3. **JsonResource** - Resource transformation layer (similar to Laravel API Resources)
4. **Pydantic Schemas** - Request validation and serialization

### File Structure

```
app/
├── Http/
│   ├── Controllers/
│   │   ├── ResourceController.py      # Base resource controller
│   │   ├── PostController.py          # Example concrete implementation
│   │   └── BaseController.py          # Base controller class
│   ├── Resources/
│   │   ├── JsonResource.py            # Base resource class
│   │   └── PostResource.py            # Example resource implementation
│   └── Routes/
│       └── posts.py                   # Route definitions
└── Models/
    └── Post.py                        # Model with Laravel-style features
```

## Basic Usage

### 1. Create a Resource Class

```python
from app.Http.Resources.JsonResource import JsonResource

class PostResource(JsonResource):
    def to_array(self) -> Dict[str, Any]:
        return {
            'id': self.resource.id,
            'title': self.resource.title,
            'content': self.when(
                self._should_include_full_content(),
                self.resource.content,
                self.resource.excerpt_short
            ),
            'author': self.when_loaded('author', {
                'id': self.resource.author.id,
                'name': self.resource.author.name,
            }),
            'created_at': self.resource.created_at.isoformat(),
        }
```

### 2. Create a Controller

```python
from app.Http.Controllers.ResourceController import ApiResourceController

class PostController(ApiResourceController[Post, PostResource]):
    # Configure the controller
    model_class = Post
    resource_class = PostResource
    create_schema = CreatePostRequest
    update_schema = UpdatePostRequest
    
    # Pagination settings
    per_page = 12
    max_per_page = 50
    
    def __init__(self, db: Session = Depends(get_db)):
        super().__init__()
        self.db = db
```

### 3. Define Routes

```python
from fastapi import APIRouter
from app.Http.Controllers.PostController import PostController

router = APIRouter(prefix="/api/v1/posts", tags=["posts"])

@router.get("")
async def index(request: Request, controller: PostController = Depends(get_post_controller)):
    return await controller.index(request)

@router.post("", status_code=201)
async def store(request: Request, data: CreatePostRequest, controller: PostController = Depends(get_post_controller)):
    return await controller.store(data.dict(), request)
```

## Standard Resource Routes

Resource controllers provide these standard routes out of the box:

| HTTP Verb | URI                | Action   | Route Name     |
|-----------|--------------------|-----------| --------------|
| GET       | `/posts`           | index    | posts.index   |
| POST      | `/posts`           | store    | posts.store   |
| GET       | `/posts/{id}`      | show     | posts.show    |
| PUT/PATCH | `/posts/{id}`      | update   | posts.update  |
| DELETE    | `/posts/{id}`      | destroy  | posts.destroy |

### Additional API Routes

The `ApiResourceController` adds these bulk operation routes:

| HTTP Verb | URI              | Action       |
|-----------|------------------|--------------|
| POST      | `/posts/bulk`    | bulk_store   |
| PUT       | `/posts/bulk`    | bulk_update  |
| DELETE    | `/posts/bulk`    | bulk_destroy |

## Advanced Features

### Query Parameters

Resource controllers support rich query parameters for filtering and pagination:

#### Pagination
- `page` - Page number (default: 1)
- `per_page` - Items per page (default: 15, max: 100)

#### Filtering
- `search` - Full-text search across searchable fields
- `sort_by` - Field to sort by
- `sort_order` - Sort direction (asc/desc)
- `include` - Relationships to include
- Custom filters based on model attributes

Example:
```
GET /api/v1/posts?page=2&per_page=20&search=laravel&sort_by=published_at&sort_order=desc&include=author,comments
```

### Response Format

All resource responses follow a consistent format:

```json
{
  "data": [...],
  "meta": {
    "total": 127,
    "per_page": 15,
    "current_page": 1,
    "last_page": 9,
    "from": 1,
    "to": 15,
    "api_version": "v1",
    "timestamp": "2024-01-15T12:00:00Z"
  },
  "links": {
    "first": "...",
    "last": "...",
    "prev": null,
    "next": "..."
  }
}
```

### Resource Transformations

Resources support conditional data loading and transformation:

```python
class PostResource(JsonResource):
    def to_array(self) -> Dict[str, Any]:
        return {
            'id': self.resource.id,
            'title': self.resource.title,
            
            # Conditional inclusion
            'content': self.when(
                self.request.query_params.get('include_content') == 'true',
                self.resource.content
            ),
            
            # Relationship loading
            'author': self.when_loaded('author', {
                'id': self.resource.author.id,
                'name': self.resource.author.name,
            }),
            
            # Conditional merging
            **self.merge_when(
                self._is_admin_request(),
                {'admin_notes': self.resource.admin_notes}
            )
        }
```

### Custom Actions

You can add custom actions beyond CRUD:

```python
class PostController(ApiResourceController):
    async def publish(self, id: str, request: Request):
        """Custom action to publish a post."""
        post = await self.find_or_fail(id)
        post.publish()
        # Save to database...
        
        resource = self.resource_class(post, request)
        return {
            'data': resource.to_array(),
            'message': 'Post published successfully'
        }
```

And wire it up in routes:

```python
@router.put("/{post_id}/publish")
async def publish(post_id: str, request: Request, controller: PostController = Depends(get_controller)):
    return await controller.publish(post_id, request)
```

## Database Integration

### Override Query Methods

Customize how the controller interacts with your database:

```python
class PostController(ApiResourceController):
    def build_index_query(self, request: Request):
        """Build base query for listing."""
        query = self.db.query(Post)
        
        # Apply default filters
        if not request.query_params.get('show_all'):
            query = query.filter(Post.is_published == True)
        
        return query
    
    def apply_search(self, query, search: str):
        """Apply search filters."""
        search_term = f"%{search}%"
        return query.filter(
            (Post.title.ilike(search_term)) |
            (Post.content.ilike(search_term))
        )
    
    def apply_sorting(self, query, sort_by: str, sort_order: str):
        """Apply sorting."""
        if sort_order == 'desc':
            return query.order_by(getattr(Post, sort_by).desc())
        else:
            return query.order_by(getattr(Post, sort_by).asc())
```

### CRUD Implementation

```python
async def find_or_fail(self, id: str) -> Post:
    """Find by ID or raise 404."""
    post = self.db.query(Post).filter(Post.id == id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

async def create_item(self, data: Dict[str, Any], request: Request) -> Post:
    """Create new item."""
    post = Post(**data)
    self.db.add(post)
    await self.db.commit()
    await self.db.refresh(post)
    return post
```

## Validation

### Request Schemas

Use Pydantic models for request validation:

```python
class CreatePostRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    content: str = Field(..., min_length=10)
    category: str = Field(..., max_length=100)
    tags: List[str] = Field(default_factory=list, max_items=10)
    status: str = Field(default='draft', regex='^(draft|published|archived)$')
    is_featured: bool = Field(default=False)

class UpdatePostRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    content: Optional[str] = Field(None, min_length=10)
    # ... other optional fields
```

### Mass Assignment Protection

Use Laravel-style fillable attributes:

```python
class Post(BaseModel):
    __fillable__ = [
        'title', 'content', 'category', 'tags', 
        'status', 'is_featured', 'meta_title'
    ]
```

The controller automatically filters request data based on `__fillable__`.

## Error Handling

Resource controllers provide consistent error responses:

```json
{
  "detail": "Post not found"
}
```

For validation errors:

```json
{
  "detail": [
    {
      "loc": ["body", "title"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Authorization

Integrate with your authentication system:

```python
class PostController(ApiResourceController):
    async def update(self, id: str, data: Dict[str, Any], request: Request):
        post = await self.find_or_fail(id)
        current_user = self._get_current_user(request)
        
        if not self._can_edit_post(post, current_user):
            raise HTTPException(status_code=403, detail="Forbidden")
        
        return await super().update(id, data, request)
    
    def _can_edit_post(self, post: Post, user) -> bool:
        return user.is_admin or post.author_id == user.id
```

## Testing

Resource controllers are designed to be easily testable:

```python
def test_post_index():
    response = client.get("/api/v1/posts")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert "links" in data

def test_post_create():
    post_data = {
        "title": "Test Post",
        "content": "Test content",
        "category": "test"
    }
    response = client.post("/api/v1/posts", json=post_data)
    assert response.status_code == 201
    assert response.json()["data"]["title"] == "Test Post"
```

## Performance Considerations

### Pagination

Resource controllers use offset-based pagination by default. For large datasets, consider cursor-based pagination:

```python
class PostController(ApiResourceController):
    async def index(self, request: Request):
        cursor = request.query_params.get('cursor')
        if cursor:
            return await self.cursor_paginate(request, cursor)
        return await super().index(request)
```

### N+1 Query Prevention

Use relationship eager loading:

```python
async def load_relationships(self, post: Post, relations: List[str]):
    query_options = []
    if 'author' in relations:
        query_options.append(selectinload(Post.author))
    if 'comments' in relations:
        query_options.append(selectinload(Post.comments))
    
    # Re-query with eager loading
    return self.db.query(Post).options(*query_options).filter(Post.id == post.id).first()
```

### Caching

Add caching to expensive operations:

```python
from app.Cache import cache

class PostController(ApiResourceController):
    async def index(self, request: Request):
        cache_key = self._build_cache_key(request)
        cached = await cache.get(cache_key)
        
        if cached:
            return cached
        
        result = await super().index(request)
        await cache.put(cache_key, result, 300)  # Cache for 5 minutes
        return result
```

## Best Practices

1. **Keep Controllers Thin** - Put business logic in service classes
2. **Use Resources for Transformation** - Don't return models directly
3. **Validate Early** - Use Pydantic schemas for all input
4. **Handle Permissions** - Check authorization before operations
5. **Use Transactions** - Wrap multi-step operations in database transactions
6. **Cache Appropriately** - Cache expensive queries and computations
7. **Document APIs** - Use FastAPI's automatic documentation features
8. **Test Thoroughly** - Write tests for all controller methods

This resource controller implementation brings Laravel's elegance and conventions to FastAPI while maintaining type safety and async performance.