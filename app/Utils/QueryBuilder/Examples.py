from __future__ import annotations

"""
QueryBuilder Usage Examples
===========================

This file demonstrates various usage patterns for the FastAPI QueryBuilder
inspired by Spatie Laravel Query Builder.
"""

from typing import List, Optional, Dict, Any, Callable
from sqlalchemy.orm import Session, Query
from starlette.requests import Request

from app.Utils.QueryBuilder import (
    QueryBuilder,
    QueryBuilderRequest,
    AllowedFilter,
    AllowedSort,
    AllowedInclude,
    AllowedField,
    FilterOperator
)
from app.Utils.QueryBuilder.AllowedSort import StringLengthSort, CaseInsensitiveSort
from app.Utils.QueryBuilder.FastAPIIntegration import (
    create_list_endpoint_dependency,
    create_show_endpoint_dependency
)
from app.Models import User


def basic_usage_example(db: Session, request: Request) -> List[User]:
    """
    Basic QueryBuilder usage example
    
    URL: GET /users?filter[name]=john&sort=-created_at
    """
    query_request = QueryBuilderRequest.from_request(request)
    
    users = QueryBuilder.for_model(User, db, query_request) \
        .allowed_filters(['name', 'email']) \
        .allowed_sorts(['name', 'created_at']) \
        .default_sort('-created_at') \
        .get()
    
    return users


def advanced_filtering_example(db: Session, request: Request) -> List[User]:
    """
    Advanced filtering with different operators
    
    URLs:
    - GET /users?filter[name]=john,jane (partial match for multiple values)
    - GET /users?filter[id]=1,2,3,4 (exact match for multiple IDs)  
    - GET /users?filter[created_at]=>2023-01-01 (date range)
    - GET /users?filter[is_active]=true (boolean)
    """
    query_request = QueryBuilderRequest.from_request(request)
    
    users = QueryBuilder.for_model(User, db, query_request) \
        .allowed_filters([
            AllowedFilter.partial('name'),
            AllowedFilter.partial('email'),
            AllowedFilter.exact('id'),
            AllowedFilter.exact('is_active'),
            AllowedFilter.operator('created_at', FilterOperator.GREATER_THAN_OR_EQUAL),
            AllowedFilter.operator('salary', FilterOperator.DYNAMIC),  # Allows ?filter[salary]=>5000
        ]) \
        .get()
    
    return users


def relationship_includes_example(db: Session, request: Request) -> List[User]:
    """
    Including relationships and relationship counts
    
    URLs:
    - GET /users?include=roles (eager load roles)
    - GET /users?include=rolesCount (add roles_count attribute)
    - GET /users?include=roles,permissions,rolesCount
    """
    query_request = QueryBuilderRequest.from_request(request)
    
    users = QueryBuilder.for_model(User, db, query_request) \
        .allowed_includes([
            'roles',
            'rolesCount',
            'direct_permissions', 
            'permissionsCount',
            'oauth_clients'
        ]) \
        .get()
    
    return users


def field_selection_example(db: Session, request: Request) -> List[User]:
    """
    Sparse fieldsets - select only specific fields
    
    URLs:
    - GET /users?fields[users]=id,name,email
    - GET /users?include=roles&fields[users]=id,name&fields[roles]=id,name
    """
    query_request = QueryBuilderRequest.from_request(request)
    
    users = QueryBuilder.for_model(User, db, query_request) \
        .allowed_fields([
            'id',
            'name',
            'email',
            'is_active',
            'created_at',
            'roles.id',
            'roles.name',
            'roles.slug'
        ]) \
        .allowed_includes(['roles']) \
        .get()
    
    return users


def custom_filters_example(db: Session, request: Request) -> List[User]:
    """
    Custom filters using callbacks and scopes
    
    URLs:
    - GET /users?filter[has_posts]=true
    - GET /users?filter[permission]=edit-users
    - GET /users?filter[active]=true (scope filter)
    """
    query_request = QueryBuilderRequest.from_request(request)
    
    # Custom filter using callback
    def filter_users_with_posts(query: Query[User], value: bool, property_name: str) -> Query[User]:
        if value:
            return query.join(User.posts).distinct()  # type: ignore[attr-defined]
        else:
            return query.filter(~User.posts.any())  # type: ignore[attr-defined]
    
    # Custom filter for users with specific permission
    def filter_by_permission(query: Query[User], value: str, property_name: str) -> Query[User]:
        return query.join(User.direct_permissions).filter(
            # Permission.name == value  # Would need proper model reference
        )
    
    users = QueryBuilder.for_model(User, db, query_request) \
        .allowed_filters([
            AllowedFilter.callback('has_posts', filter_users_with_posts),
            AllowedFilter.callback('permission', filter_by_permission),
            AllowedFilter.scope('active'),  # Calls User.scope_active()
            AllowedFilter.partial('name')
        ]) \
        .get()
    
    return users


def custom_sorts_example(db: Session, request: Request) -> List[User]:
    """
    Custom sorting implementations
    
    URLs:
    - GET /users?sort=name_length (sort by length of name)
    - GET /users?sort=case_insensitive_name
    - GET /users?sort=-posts_count (sort by relationship count)
    """
    query_request = QueryBuilderRequest.from_request(request)
    
    # Custom sort callback
    def sort_by_posts_count(query: Query[User], descending: bool, property_name: str) -> Query[User]:
        direction = "DESC" if descending else "ASC"
        # This would need proper subquery implementation
        return query.order_by(f"posts_count {direction}")
    
    users = QueryBuilder.for_model(User, db, query_request) \
        .allowed_sorts([
            AllowedSort.custom('name_length', StringLengthSort(), 'name'),
            AllowedSort.custom('case_insensitive_name', CaseInsensitiveSort(), 'name'),
            AllowedSort.callback('posts_count', sort_by_posts_count),
            'name',  # Standard field sort
            'created_at'
        ]) \
        .default_sort('name') \
        .get()
    
    return users


def chaining_with_existing_query_example(db: Session, request: Request) -> List[User]:
    """
    Using QueryBuilder with existing SQLAlchemy queries
    
    URL: GET /active-users?filter[name]=john&sort=created_at
    """
    query_request = QueryBuilderRequest.from_request(request)
    
    # Start with existing query constraints
    base_query = db.query(User).filter(User.is_active == True)
    
    users = QueryBuilder.for_query(base_query, query_request, User) \
        .allowed_filters(['name', 'email']) \
        .allowed_sorts(['name', 'created_at']) \
        .filter(User.is_verified == True) \
        .get()  # Can chain additional SQLAlchemy methods
    
    return users


def pagination_example(db: Session, request: Request) -> Dict[str, Any]:
    """
    Paginated results with QueryBuilder
    
    URL: GET /users?filter[is_active]=true&sort=name&page=2&per_page=20
    """
    query_request = QueryBuilderRequest.from_request(request)
    
    # Extract pagination params from request (in real app, use FastAPI Query params)
    page = int(request.query_params.get('page', '1'))
    per_page = int(request.query_params.get('per_page', '15'))
    
    result = QueryBuilder.for_model(User, db, query_request) \
        .allowed_filters(['name', 'email', 'is_active']) \
        .allowed_sorts(['name', 'created_at']) \
        .allowed_includes(['rolesCount']) \
        .paginate(page=page, per_page=per_page)
    
    return result  # type: ignore[no-any-return]


def configuration_example(db: Session, request: Request) -> List[User]:
    """
    QueryBuilder with configuration options
    """
    # Configure array delimiter globally
    QueryBuilderRequest.set_array_value_delimiter(';')
    
    # Or configure per-feature
    QueryBuilderRequest.set_filters_array_value_delimiter('|')
    QueryBuilderRequest.set_sorts_array_value_delimiter(',')
    
    query_request = QueryBuilderRequest.from_request(request)
    
    users = QueryBuilder.for_model(User, db, query_request) \
        .allowed_filters(['name', 'email']) \
        .allowed_sorts(['name']) \
        .disable_invalid_filter_exception() \
        .disable_invalid_sort_exception() \
        .get()
    
    return users


def fastapi_dependency_example() -> None:
    """
    Example of creating FastAPI dependencies for QueryBuilder
    """
    from config.database import get_db_session
    
    # Create a pre-configured dependency for user listing
    user_list_dependency = create_list_endpoint_dependency(
        model_class=User,
        get_db=get_db_session,  # type: ignore[arg-type]
        allowed_filters=['name', 'email', 'is_active'],
        allowed_sorts=['name', 'created_at'],
        allowed_includes=['roles', 'rolesCount'],
        allowed_fields=['id', 'name', 'email', 'is_active'],
        default_sorts=['-created_at']
    )
    
    # Create a pre-configured dependency for showing single user
    user_show_dependency = create_show_endpoint_dependency(
        model_class=User,
        get_db=get_db_session,  # type: ignore[arg-type]
        allowed_includes=['roles', 'permissions'],
        allowed_fields=['id', 'name', 'email', 'roles.name']
    )
    
    # These can be used directly in FastAPI route handlers
    # Example usage:
    # @app.get("/users")
    # async def list_users(users=Depends(user_list_dependency)):
    #     return users


# SQL Query Examples that would be generated:

"""
Basic filtering:
URL: GET /users?filter[name]=john&filter[is_active]=true
SQL: SELECT * FROM users WHERE name ILIKE '%john%' AND is_active = true

Exact matching:  
URL: GET /users?filter[id]=1,2,3
SQL: SELECT * FROM users WHERE id IN (1, 2, 3)

Sorting:
URL: GET /users?sort=name,-created_at
SQL: SELECT * FROM users ORDER BY name ASC, created_at DESC

Including relationships:
URL: GET /users?include=roles
SQL: SELECT * FROM users; SELECT * FROM roles WHERE user_id IN (...)

Field selection:
URL: GET /users?fields[users]=id,name,email
SQL: SELECT id, name, email FROM users

Complex query:
URL: GET /users?filter[name]=john&sort=-created_at&include=rolesCount&fields[users]=id,name
SQL: SELECT id, name, (SELECT COUNT(*) FROM user_roles WHERE user_id = users.id) as roles_count
     FROM users WHERE name ILIKE '%john%' ORDER BY created_at DESC
"""