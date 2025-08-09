# FastAPI QueryBuilder

A comprehensive query building library for FastAPI applications inspired by [Spatie Laravel Query Builder](https://github.com/spatie/laravel-query-builder).

## Overview

The FastAPI QueryBuilder allows you to build complex database queries using URL parameters, providing filtering, sorting, field selection, and relationship inclusion capabilities similar to JSON:API specifications.

## Features

- **Filtering**: Partial, exact, operator-based, and custom filters
- **Sorting**: Field-based, custom, and relationship sorting  
- **Includes**: Eager loading relationships with counts and existence checks
- **Field Selection**: Sparse fieldsets for response optimization
- **Type Safety**: Full mypy compatibility with strict typing
- **FastAPI Integration**: Native dependency injection support
- **Flexible Configuration**: Customizable parameter names and delimiters

## Basic Usage

### Simple Query Building

```python
from app.Utils.QueryBuilder import QueryBuilder, QueryBuilderRequest
from app.Models import User

# In your FastAPI route handler
def get_users(request: Request, db: Session = Depends(get_database)):
    query_request = QueryBuilderRequest.from_request(request)
    
    users = QueryBuilder.for_model(User, db, query_request) \
        .allowed_filters(['name', 'email']) \
        .allowed_sorts(['name', 'created_at']) \
        .default_sort('-created_at') \
        .get()
    
    return users
```

### URL Examples

```bash
# Filter by name and email
GET /users?filter[name]=john&filter[email]=gmail

# Sort by multiple fields
GET /users?sort=name,-created_at

# Include relationships
GET /users?include=roles,permissions

# Select specific fields
GET /users?fields[users]=id,name,email

# Combined query
GET /users?filter[is_active]=true&sort=-created_at&include=rolesCount&fields[users]=id,name,email
```

## Filtering

### Basic Filters

```python
QueryBuilder.for_model(User, db, query_request) \
    .allowed_filters([
        'name',          # Partial match (ILIKE)
        'email',         # Partial match (ILIKE)
        'is_active'      # Exact match
    ])
```

### Advanced Filters

```python
from app.Utils.QueryBuilder import AllowedFilter, FilterOperator

QueryBuilder.for_model(User, db, query_request) \
    .allowed_filters([
        AllowedFilter.partial('name'),                                    # ILIKE '%value%'
        AllowedFilter.exact('id'),                                       # Exact match
        AllowedFilter.operator('created_at', FilterOperator.GREATER_THAN), # created_at > value
        AllowedFilter.operator('salary', FilterOperator.DYNAMIC),         # Allows ?filter[salary]=>5000
    ])
```

### Custom Filters

```python
def filter_by_permission(query, value, property_name):
    return query.join(User.permissions).filter(Permission.name == value)

QueryBuilder.for_model(User, db, query_request) \
    .allowed_filters([
        AllowedFilter.callback('permission', filter_by_permission),
        AllowedFilter.scope('active')  # Calls User.scope_active() method
    ])
```

## Sorting

### Basic Sorting

```python
QueryBuilder.for_model(User, db, query_request) \
    .allowed_sorts(['name', 'created_at', 'email']) \
    .default_sort('-created_at')
```

### Custom Sorting

```python
from app.Utils.QueryBuilder import AllowedSort
from app.Utils.QueryBuilder.AllowedSort import StringLengthSort

def sort_by_posts_count(query, descending, property_name):
    direction = "DESC" if descending else "ASC"
    return query.order_by(f"posts_count {direction}")

QueryBuilder.for_model(User, db, query_request) \
    .allowed_sorts([
        AllowedSort.custom('name_length', StringLengthSort(), 'name'),
        AllowedSort.callback('posts_count', sort_by_posts_count),
        'name'
    ])
```

## Including Relationships

### Basic Includes

```python
QueryBuilder.for_model(User, db, query_request) \
    .allowed_includes([
        'roles',            # Load roles relationship
        'rolesCount',       # Add roles_count attribute
        'rolesExists',      # Add roles_exists boolean
        'permissions'
    ])
```

### Custom Includes

```python
from app.Utils.QueryBuilder import AllowedInclude

def include_latest_post(query, relations):
    # Custom logic to include latest post
    return query.options(selectinload('latest_post'))

QueryBuilder.for_model(User, db, query_request) \
    .allowed_includes([
        AllowedInclude.callback('latest_post', include_latest_post),
        AllowedInclude.count('postsCount', 'posts'),
        'roles'
    ])
```

## Field Selection

### Sparse Fieldsets

```python
QueryBuilder.for_model(User, db, query_request) \
    .allowed_fields([
        'id',
        'name', 
        'email',
        'roles.id',
        'roles.name'
    ])
```

**URL**: `GET /users?fields[users]=id,name&fields[roles]=name`

## FastAPI Integration

### Using Dependencies

```python
from app.Utils.QueryBuilder.FastAPIIntegration import (
    get_query_builder_request,
    handle_query_builder_exceptions
)

@router.get("/users")
@handle_query_builder_exceptions
async def list_users(
    query_request: QueryBuilderRequest = Depends(get_query_builder_request),
    db: Session = Depends(get_database)
):
    users = QueryBuilder.for_model(User, db, query_request) \
        .allowed_filters(['name', 'email']) \
        .allowed_sorts(['name', 'created_at']) \
        .get()
    
    return {"users": users}
```

### Pre-configured Dependencies

```python
from app.Utils.QueryBuilder.FastAPIIntegration import create_list_endpoint_dependency

# Create reusable dependency
user_query_dependency = create_list_endpoint_dependency(
    model_class=User,
    get_db=get_database,
    allowed_filters=['name', 'email', 'is_active'],
    allowed_sorts=['name', 'created_at'],
    allowed_includes=['roles', 'rolesCount'],
    default_sorts=['-created_at']
)

@router.get("/users")
async def list_users(query_builder: QueryBuilder = Depends(user_query_dependency)):
    users = query_builder.get()
    return {"users": users}
```

## Pagination

```python
from fastapi import Query

@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(15, ge=1, le=100),
    query_request: QueryBuilderRequest = Depends(get_query_builder_request),
    db: Session = Depends(get_database)
):
    result = QueryBuilder.for_model(User, db, query_request) \
        .allowed_filters(['name', 'email']) \
        .allowed_sorts(['name', 'created_at']) \
        .paginate(page=page, per_page=per_page)
    
    return {
        "users": result["items"],
        "pagination": {
            "total": result["total"],
            "page": result["page"],
            "per_page": result["per_page"],
            "pages": result["pages"]
        }
    }
```

## Configuration

### Global Configuration

```python
from app.Utils.QueryBuilder.QueryBuilderRequest import QueryBuilderRequest
from app.Utils.QueryBuilder.FastAPIIntegration import QueryBuilderConfig, configure_query_builder

# Configure globally
config = QueryBuilderConfig(
    array_value_delimiter=";",
    convert_field_names_to_snake_case=True,
    disable_invalid_filter_query_exception=False
)

configure_query_builder(config)
```

### Per-Feature Configuration

```python
# Set different delimiters for different features
QueryBuilderRequest.set_filters_array_value_delimiter('|')
QueryBuilderRequest.set_sorts_array_value_delimiter(',')
QueryBuilderRequest.set_includes_array_value_delimiter(';')
```

## Error Handling

```python
from app.Utils.QueryBuilder.Exceptions import (
    InvalidFilterQueryException,
    InvalidSortQueryException,
    InvalidIncludeQueryException,
    InvalidFieldQueryException
)

# Automatic error handling with decorator
@handle_query_builder_exceptions
async def my_endpoint():
    # QueryBuilder exceptions automatically converted to HTTP 400 responses
    pass

# Manual error handling
try:
    users = QueryBuilder.for_model(User, db, query_request) \
        .allowed_filters(['name']) \
        .get()
except InvalidFilterQueryException as e:
    return {"error": str(e), "allowed_filters": e.allowed_filters}
```

## Filter Operators

| Operator | Description | Example URL |
|----------|-------------|-------------|
| `EQUAL` | Exact match | `?filter[id]=1` |
| `NOT_EQUAL` | Not equal | `?filter[status]!=active` |
| `GREATER_THAN` | Greater than | `?filter[age]>18` |
| `LESS_THAN` | Less than | `?filter[price]<100` |
| `LIKE` | Pattern match | `?filter[name]=john` |
| `IN` | In array | `?filter[id]=1,2,3` |
| `BETWEEN` | Between values | `?filter[age]=18,65` |
| `IS_NULL` | Is null | `?filter[deleted_at]=null` |
| `DYNAMIC` | User-specified operator | `?filter[price]=>100` |

## Advanced Examples

### Complex Filtering

```python
# URL: GET /users?filter[name]=john,jane&filter[created_at]=>2023-01-01&filter[is_active]=true
QueryBuilder.for_model(User, db, query_request) \
    .allowed_filters([
        AllowedFilter.partial('name'),     # Matches "john" OR "jane"
        AllowedFilter.operator('created_at', FilterOperator.GREATER_THAN_OR_EQUAL),
        AllowedFilter.exact('is_active')
    ])
```

### Relationship Filtering

```python
# URL: GET /posts?filter[author.name]=john&filter[category.slug]=tech
QueryBuilder.for_model(Post, db, query_request) \
    .allowed_filters([
        AllowedFilter.partial('author.name'),      # Filter by author's name
        AllowedFilter.exact('category.slug')       # Filter by category slug
    ])
```

### Custom Sorts with Default Direction

```python
from app.Utils.QueryBuilder.AllowedSort import SortDirection

custom_sort = AllowedSort.custom('priority', PrioritySort()) \
    .default_direction(SortDirection.DESCENDING)

QueryBuilder.for_model(Task, db, query_request) \
    .allowed_sorts([custom_sort, 'created_at']) \
    .default_sort(custom_sort)
```

## Best Practices

1. **Security**: Always use `allowed_filters()`, `allowed_sorts()`, etc. to prevent unauthorized data access
2. **Performance**: Use field selection to reduce payload size
3. **Validation**: Use the exception handling decorator for consistent error responses
4. **Documentation**: Document your API endpoints with example URLs
5. **Pagination**: Always implement pagination for list endpoints
6. **Caching**: Consider caching frequently used queries
7. **Relationships**: Be mindful of N+1 queries when including relationships

## Comparison with Laravel Query Builder

| Feature | FastAPI QueryBuilder | Laravel Query Builder |
|---------|---------------------|----------------------|
| Filtering | ✅ All operators | ✅ All operators |
| Sorting | ✅ Custom sorts | ✅ Custom sorts |
| Includes | ✅ With counts/exists | ✅ With counts/exists |
| Field Selection | ✅ Sparse fieldsets | ✅ Sparse fieldsets |
| Type Safety | ✅ Full mypy support | ❌ Limited |
| Async Support | ✅ Native | ❌ Not applicable |
| Configuration | ✅ Global + per-feature | ✅ Global |
| Error Handling | ✅ Exception-based | ✅ Exception-based |

## Contributing

The QueryBuilder follows the same patterns as the existing codebase:
- Strict type checking with mypy
- Laravel-style architecture (Controllers, Services, Models)
- Comprehensive documentation and examples

For issues or feature requests, please refer to the project's issue tracker.