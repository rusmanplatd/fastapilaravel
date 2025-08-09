# Pagination & Query Builder System

## Overview

The pagination and query builder system provides Laravel-style data querying with advanced filtering, sorting, and pagination capabilities. It includes multiple pagination strategies and a powerful Spatie Query Builder-inspired interface.

## Pagination System

### Current Implementation
**Location:** `app/Pagination/`

**Pagination Types:**
- **Length-Aware Pagination** - Full pagination with total counts
- **Simple Pagination** - Performance-optimized without total counts
- **Cursor Pagination** - Efficient pagination for large datasets (planned)

### Length-Aware Pagination

**Features:**
- Complete pagination metadata (total items, pages, etc.)
- Laravel-style pagination links
- Customizable page parameters
- Multiple response formats (Laravel, JSON:API, custom)

**Basic Usage:**
```python
from fastapi import Depends
from app.Pagination import LengthAwarePaginator, PaginationDep

@app.get("/posts")
async def get_posts(
    pagination: PaginationDep = Depends(),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    query = db.query(Post).order_by(Post.created_at.desc())
    paginator = query_paginator.paginate(
        query, 
        pagination.page, 
        pagination.per_page, 
        request
    )
    
    return {
        "data": [post.to_dict() for post in paginator.items],
        "meta": paginator.get_pagination_meta(),
        "links": paginator.get_links()
    }
```

**Advanced Pagination:**
```python
from app.Pagination import LengthAwarePaginator

# Custom pagination configuration
paginator = LengthAwarePaginator(
    items=posts,
    total=total_count,
    per_page=20,
    current_page=page,
    path=request.url.path,
    page_name="page",
    query_params=dict(request.query_params),
    options={
        "show_first_last": True,
        "show_prev_next": True,
        "show_numbers": True,
        "adjacent_links": 3
    }
)

# Get pagination metadata
meta = {
    "current_page": paginator.current_page(),
    "from": paginator.first_item(),
    "last_page": paginator.last_page(),
    "path": paginator.path(),
    "per_page": paginator.per_page(),
    "to": paginator.last_item(),
    "total": paginator.total()
}

# Get pagination links
links = paginator.get_links()
```

### Simple Pagination

**Features:**
- Performance-optimized for large datasets
- No total count queries
- Previous/Next navigation only
- Reduced database load

**Usage:**
```python
from app.Pagination import SimplePaginator

# Simple pagination without count query
simple_paginator = SimplePaginator(
    items=posts,
    per_page=15,
    current_page=page,
    path=request.url.path
)

# Only provides has_more_pages() instead of total
return {
    "data": simple_paginator.items,
    "has_more": simple_paginator.has_more_pages(),
    "next_page_url": simple_paginator.next_page_url(),
    "prev_page_url": simple_paginator.previous_page_url()
}
```

### FastAPI Dependencies

**Basic Pagination Dependency:**
```python
from app.Pagination import PaginationDep, BasicPagination

@app.get("/users")
async def get_users(pagination: PaginationDep = Depends(BasicPagination)):
    # pagination.page, pagination.per_page automatically extracted
    pass

# Custom pagination dependency
CustomPagination = PaginationDependency(
    default_per_page=25,
    max_per_page=200,
    default_sort="created_at",
    allowed_sorts=["created_at", "name", "email"],
    default_order="desc"
)

@app.get("/posts")
async def get_posts(pagination: PaginationDep = Depends(CustomPagination)):
    # Custom pagination rules applied
    pass
```

**Model-Specific Dependencies:**
```python
from app.Pagination import create_model_pagination_dependency

# Auto-generated pagination for User model
UserPagination = create_model_pagination_dependency(
    model_class=User,
    searchable_fields=["name", "email", "username"],
    filterable_fields=["role", "status", "created_at"],
    sortable_fields=["id", "name", "email", "created_at"],
    default_per_page=20,
    relationships=["roles", "posts"]
)

@app.get("/users/auto")
async def get_users_auto(paginated_users: LengthAwarePaginator = Depends(UserPagination)):
    # Automatically handles search, filter, sort, pagination
    return {
        "users": [user.to_dict() for user in paginated_users.items],
        "meta": paginated_users.get_pagination_meta()
    }
```

### Pagination Middleware

**Features:**
- Automatic pagination headers
- Response caching
- Performance monitoring
- Request logging

**Usage:**
```python
from app.Pagination import PaginationMiddleware

@app.middleware("http")
async def pagination_middleware(request: Request, call_next):
    return await PaginationMiddleware.process(request, call_next)

# Headers added automatically:
# X-Total-Count: 150
# X-Page: 2  
# X-Per-Page: 25
# X-Total-Pages: 6
```

## Query Builder System

### Current Implementation
**Location:** `app/Utils/QueryBuilder/`

**Features:**
- Spatie Query Builder-inspired filtering
- Advanced filter operators
- Relationship includes
- Field selection
- Query optimization
- Performance metrics

### Basic Query Builder Usage

**Simple Filtering:**
```python
from app.Utils.QueryBuilder import QueryBuilder, AllowedFilter, AllowedSort

# URL: /users?filter[name]=john&sort=-created_at&include=posts
builder = QueryBuilder.for_model(User, db, request) \
    .allowed_filters([
        AllowedFilter.exact('name'),
        AllowedFilter.partial('email'), 
        AllowedFilter.scope('active'),
        AllowedFilter.date_range('created_at')
    ]) \
    .allowed_sorts(['created_at', 'name', 'email']) \
    .allowed_includes(['posts', 'roles']) \
    .paginate(15)

return {
    "users": builder.items,
    "meta": builder.pagination_meta
}
```

**Advanced Filtering:**
```python
# Complex filter example
# URL: /posts?filter[author.name]=john&filter[created_at][gte]=2024-01-01&filter[tags]=tech,python

builder = QueryBuilder.for_model(Post, db, request) \
    .allowed_filters([
        # Relationship filtering
        AllowedFilter.exact('author.name'),
        AllowedFilter.partial('author.email'),
        
        # Date filtering
        AllowedFilter.date_range('created_at'),
        AllowedFilter.date_range('updated_at'),
        
        # Array/JSON filtering
        AllowedFilter.in_array('tags'),
        AllowedFilter.json_contains('metadata.category'),
        
        # Numeric ranges
        AllowedFilter.numeric_range('view_count'),
        AllowedFilter.numeric_range('comment_count'),
        
        # Full-text search
        AllowedFilter.search(['title', 'content']),
        
        # Geographic filtering
        AllowedFilter.within_radius('location', 'lat', 'lng'),
        
        # Custom scope filters
        AllowedFilter.scope('published'),
        AllowedFilter.scope('featured'),
        AllowedFilter.scope('recent')
    ]) \
    .allowed_sorts([
        'created_at', 'updated_at', 'title',
        'view_count', 'comment_count',
        AllowedSort.field('author_name', 'author.name'),
        AllowedSort.custom('popularity', PopularitySort)
    ]) \
    .allowed_includes([
        'author', 'comments', 'tags',
        AllowedInclude.relationship('comments.author'),
        AllowedInclude.count('comments_count'),
        AllowedInclude.conditional('drafts', lambda user: user.is_admin)
    ]) \
    .allowed_fields([
        AllowedField.for_model(Post, ['id', 'title', 'content']),
        AllowedField.for_relationship('author', ['id', 'name'])
    ])

results = builder.get()
```

### Filter Types

**Basic Filters:**
```python
# Exact match
AllowedFilter.exact('status')  # ?filter[status]=published

# Partial match (LIKE)
AllowedFilter.partial('name')  # ?filter[name]=john

# Case-insensitive partial
AllowedFilter.partial('name', case_sensitive=False)
```

**Advanced Filters:**
```python
# Date range filtering
AllowedFilter.date_range('created_at')
# ?filter[created_at][gte]=2024-01-01&filter[created_at][lte]=2024-12-31

# Numeric range filtering  
AllowedFilter.numeric_range('price')
# ?filter[price][gte]=100&filter[price][lte]=500

# Array/in filtering
AllowedFilter.in_array('category')
# ?filter[category]=tech,news,sports

# JSON path filtering
AllowedFilter.json_path('metadata->category')
# ?filter[metadata.category]=technology

# Full-text search
AllowedFilter.search(['title', 'content', 'description'])
# ?filter[search]=laravel%20tutorial
```

**Relationship Filters:**
```python
# Filter by related model
AllowedFilter.relationship('author', 'name')
# ?filter[author.name]=john

# Filter by relationship existence
AllowedFilter.has_relationship('comments')
# ?filter[has_comments]=true

# Filter by relationship count
AllowedFilter.relationship_count('comments', '>', 5)
# ?filter[comments_count][gt]=5
```

**Scope Filters:**
```python
# Model scope filters
AllowedFilter.scope('published')  # Uses Post.scope_published()
AllowedFilter.scope('recent')     # Uses Post.scope_recent()

# Custom scope filters
AllowedFilter.scope('popular', lambda query, value: 
    query.where('view_count', '>', value))
```

### Sorting

**Basic Sorting:**
```python
# Simple field sorting
AllowedSort.field('created_at')
AllowedSort.field('name') 

# Custom sorting logic
AllowedSort.custom('popularity', lambda query, direction:
    query.order_by(
        func.coalesce(Post.view_count, 0).desc() if direction == 'desc'
        else func.coalesce(Post.view_count, 0).asc()
    ))

# Relationship sorting
AllowedSort.field('author_name', 'author.name')
```

**Usage:**
```python
# URL: /posts?sort=created_at,-view_count,author.name
# Sorts by created_at ASC, view_count DESC, author.name ASC
```

### Includes (Eager Loading)

**Basic Includes:**
```python
# Simple relationship includes
AllowedInclude.relationship('author')
AllowedInclude.relationship('comments')

# Nested relationship includes  
AllowedInclude.relationship('comments.author')
AllowedInclude.relationship('author.posts')

# Conditional includes
AllowedInclude.conditional('drafts', lambda user: user.is_admin)

# Count includes
AllowedInclude.count('comments_count')
AllowedInclude.count('likes_count')
```

**Usage:**
```python
# URL: /posts?include=author,comments.author,comments_count
# Includes author, comments with their authors, and comment count
```

### Field Selection

**Sparse Fields:**
```python
# Select specific fields only
AllowedField.for_model(Post, ['id', 'title', 'slug'])
AllowedField.for_relationship('author', ['id', 'name', 'email'])

# URL: /posts?fields[posts]=id,title,slug&fields[author]=id,name
# Only returns specified fields
```

### Query Optimization

**Performance Features:**
```python
from app.Utils.QueryBuilder import QueryBuilder

builder = QueryBuilder.for_model(User, db, request) \
    .with_performance_monitoring() \
    .with_query_cache(ttl=300) \
    .with_result_cache(ttl=60) \
    .optimize_includes() \
    .optimize_counts()

# Get performance metrics
metrics = builder.get_metrics()
print(f"Execution time: {metrics.execution_time}ms")
print(f"SQL Query: {metrics.sql_query}")
print(f"Filters applied: {metrics.filters_applied}")
```

### Custom Query Components

**Custom Filter Classes:**
```python
from app.Utils.QueryBuilder.Filters import FilterInterface

class PriceRangeFilter(FilterInterface):
    def apply(self, query, value, property_name):
        if isinstance(value, dict):
            if 'min' in value:
                query = query.where(property_name, '>=', value['min'])
            if 'max' in value:
                query = query.where(property_name, '<=', value['max'])
        return query

# Usage
AllowedFilter.custom('price_range', PriceRangeFilter())
```

**Custom Sort Classes:**
```python
from app.Utils.QueryBuilder import SortInterface

class PopularitySort(SortInterface):
    def apply(self, query, direction):
        # Sort by view_count * 0.7 + comment_count * 0.3
        popularity_expr = (
            func.coalesce(Post.view_count, 0) * 0.7 + 
            func.coalesce(Post.comment_count, 0) * 0.3
        )
        
        if direction == 'desc':
            return query.order_by(popularity_expr.desc())
        else:
            return query.order_by(popularity_expr.asc())

# Usage
AllowedSort.custom('popularity', PopularitySort())
```

## API Examples

### Complete API Endpoint
```python
from app.Utils.QueryBuilder import QueryBuilder
from app.Pagination import PaginationResponse

@app.get("/api/posts")
async def get_posts(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    
    # Build query with filtering, sorting, includes
    builder = QueryBuilder.for_model(Post, db, request) \
        .allowed_filters([
            AllowedFilter.exact('status'),
            AllowedFilter.partial('title'),
            AllowedFilter.search(['title', 'content']),
            AllowedFilter.date_range('published_at'),
            AllowedFilter.relationship('author', 'name'),
            AllowedFilter.scope('featured'),
            AllowedFilter.scope('recent')
        ]) \
        .allowed_sorts([
            'created_at', 'published_at', 'title',
            'view_count', 'comment_count',
            AllowedSort.field('author_name', 'author.name')
        ]) \
        .allowed_includes([
            'author', 'comments', 'tags',
            AllowedInclude.count('comments_count'),
            AllowedInclude.count('likes_count'),
            AllowedInclude.conditional('drafts', lambda: current_user and current_user.is_admin)
        ]) \
        .allowed_fields([
            AllowedField.for_model(Post, ['id', 'title', 'slug', 'excerpt', 'published_at']),
            AllowedField.for_relationship('author', ['id', 'name', 'avatar'])
        ]) \
        .with_performance_monitoring()
    
    # Paginate results
    paginator = builder.paginate(per_page=15)
    
    # Format response
    return PaginationResponse.create(
        data=[post.to_dict() for post in paginator.items],
        paginator=paginator,
        includes=builder.get_included_relations(),
        meta={
            "query_time": builder.get_metrics().execution_time,
            "filters_applied": builder.get_metrics().filters_applied
        }
    )

# Example URLs:
# /api/posts?filter[status]=published&sort=-published_at&include=author,comments_count
# /api/posts?filter[search]=laravel&filter[published_at][gte]=2024-01-01
# /api/posts?filter[author.name]=john&sort=view_count&fields[posts]=id,title,slug
```

### Frontend Integration

**JavaScript Usage:**
```javascript
// Build query URL
const queryUrl = new URLSearchParams({
    'filter[status]': 'published',
    'filter[search]': searchTerm,
    'sort': '-published_at',
    'include': 'author,comments_count',
    'page': currentPage,
    'per_page': 15
});

// Fetch data
const response = await fetch(`/api/posts?${queryUrl}`);
const data = await response.json();

// Use pagination data
console.log(`Showing ${data.meta.from} to ${data.meta.to} of ${data.meta.total} posts`);
```

## Testing

### Query Builder Testing
```python
from app.Testing.QueryBuilderTesting import QueryBuilderTest

def test_post_filtering():
    # Test query builder functionality
    test_request = MockRequest({
        'filter[status]': 'published',
        'filter[author.name]': 'john',
        'sort': '-created_at',
        'include': 'author,comments_count'
    })
    
    builder = QueryBuilder.for_model(Post, db, test_request)
    results = builder.get()
    
    # Assertions
    assert len(results) > 0
    assert all(post.status == 'published' for post in results)
    assert all(hasattr(post, 'author') for post in results)
```

### Pagination Testing
```python
from app.Testing.PaginationTesting import PaginationTest

def test_pagination():
    posts = Post.factory().count(100).create()
    
    paginator = LengthAwarePaginator(
        items=posts[:15],
        total=100,
        per_page=15,
        current_page=1
    )
    
    assert paginator.total() == 100
    assert paginator.last_page() == 7
    assert paginator.has_more_pages() == True
```

## Improvements

### Performance Optimizations
1. **Query caching**: Intelligent query result caching
2. **Index optimization**: Automatic index suggestions
3. **Query analysis**: SQL query performance monitoring
4. **Batch loading**: Efficient N+1 query prevention

### Advanced Features
1. **GraphQL integration**: GraphQL-style field selection
2. **Real-time filters**: Live filtering with WebSocket updates
3. **Saved queries**: User-defined query presets
4. **Query export**: Export query results to various formats

### Developer Experience
1. **Query debugger**: Visual query builder and debugger
2. **API documentation**: Auto-generated API documentation
3. **Type safety**: Full TypeScript/Python type definitions
4. **Performance insights**: Query performance dashboard

### Enterprise Features
1. **Access control**: Field-level permissions
2. **Audit logging**: Track query access patterns
3. **Rate limiting**: Query-based rate limiting
4. **Multi-tenancy**: Tenant-scoped query filtering