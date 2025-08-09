from __future__ import annotations

from fastapi import Depends, Query as QueryParam
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from typing_extensions import Annotated

from app.Http.Controllers.BaseController import BaseController
from app.Models import User
from app.Http.Controllers import get_current_user
from config import get_database
from app.Utils.QueryBuilder import (
    QueryBuilder,
    QueryBuilderRequest,
    AllowedFilter,
    AllowedSort,
    AllowedInclude,
    AllowedField,
    FilterOperator
)
from app.Utils.QueryBuilder.FastAPIIntegration import (
    get_query_builder_request,
    handle_query_builder_exceptions,
    query_builder_response_formatter,
    paginated_response_formatter
)


class UserQueryController(BaseController):
    """
    Example controller demonstrating QueryBuilder usage
    
    Example URLs:
    GET /api/users/query?filter[name]=john&sort=-created_at&include=roles&fields[users]=id,name,email
    GET /api/users/query?filter[is_active]=true&filter[created_at]=>2023-01-01
    GET /api/users/query?sort=name,-created_at&include=rolesCount
    """
    
    @handle_query_builder_exceptions
    async def index(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
        query_request: Annotated[QueryBuilderRequest, Depends(get_query_builder_request)],
        db: Annotated[Session, Depends(get_database)],
        page: Annotated[int, QueryParam(1, ge=1)],
        per_page: Annotated[int, QueryParam(15, ge=1, le=100)]
    ) -> Dict[str, Any]:
        """
        List users with QueryBuilder support
        
        Supports:
        - Filtering by name, email, is_active, created_at
        - Sorting by name, email, created_at
        - Including roles, permissions relationships
        - Field selection for users table
        """
        if not current_user.can('view-users'):
            self.forbidden("You don't have permission to view users")
        
        # Build query with QueryBuilder
        query_builder = QueryBuilder.for_model(User, db, query_request)
        
        # Configure allowed operations
        query_builder.allowed_filters([
            AllowedFilter.partial('name'),
            AllowedFilter.partial('email'),
            AllowedFilter.exact('is_active'),
            AllowedFilter.operator('created_at', FilterOperator.GREATER_THAN_OR_EQUAL),
            AllowedFilter.scope('active')  # Assumes User model has scopeActive method
        ]).allowed_sorts([
            AllowedSort.field('name'),
            AllowedSort.field('email'),
            AllowedSort.field('created_at'),
            'is_active'  # String shorthand
        ]).allowed_includes([
            'roles',
            'rolesCount',
            'direct_permissions',
            'permissionsCount'
        ]).allowed_fields([
            'id',
            'name', 
            'email',
            'is_active',
            'created_at',
            'roles.id',
            'roles.name'
        ]).default_sort('-created_at')
        
        # Get paginated results
        pagination_result = query_builder.paginate(page, per_page)
        
        return paginated_response_formatter(
            pagination_result.model_dump() if hasattr(pagination_result, 'model_dump') else dict(pagination_result),  # type: ignore
            "Users retrieved successfully"
        )
    
    @handle_query_builder_exceptions
    async def show(
        self,
        user_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        query_request: Annotated[QueryBuilderRequest, Depends(get_query_builder_request)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        """
        Get single user with QueryBuilder support for includes and fields
        
        Example: GET /api/users/1?include=roles,permissions&fields[users]=id,name,email
        """
        if not current_user.can('view-users'):
            self.forbidden("You don't have permission to view users")
        
        # Start with filtered base query
        base_query = db.query(User).filter(User.id == user_id)
        
        # Build query with QueryBuilder
        query_builder = QueryBuilder.for_query(base_query, query_request, User)
        
        # Configure allowed operations (more limited for single resource)
        query_builder.allowed_includes([
            'roles',
            'direct_permissions',
            'oauth_clients'
        ]).allowed_fields([
            'id',
            'name',
            'email', 
            'is_active',
            'is_verified',
            'created_at',
            'roles.id',
            'roles.name',
            'direct_permissions.id',
            'direct_permissions.name'
        ])
        
        user = query_builder.first()
        
        if not user:
            self.not_found("User not found")
        
        return query_builder_response_formatter(
            user.to_dict_safe() if hasattr(user, 'to_dict_safe') else user,
            "User retrieved successfully"
        )
    
    @handle_query_builder_exceptions
    async def search(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
        query_request: Annotated[QueryBuilderRequest, Depends(get_query_builder_request)],
        db: Annotated[Session, Depends(get_database)],
        q: Annotated[str, QueryParam(..., description="Search query")]
    ) -> Dict[str, Any]:
        """
        Search users with additional QueryBuilder features
        
        Example: GET /api/users/search?q=john&sort=name&include=rolesCount
        """
        if not current_user.can('view-users'):
            self.forbidden("You don't have permission to search users")
        
        # Base search query
        base_query = db.query(User).filter(
            User.name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%")
        )
        
        # Build query with QueryBuilder
        query_builder = QueryBuilder.for_query(base_query, query_request, User)
        
        # Configure allowed operations
        query_builder.allowed_sorts([
            'name',
            'email',
            'created_at'
        ]).allowed_includes([
            'rolesCount',
            'permissionsCount'
        ]).allowed_fields([
            'id',
            'name',
            'email',
            'is_active'
        ]).default_sort('name')
        
        users = query_builder.get()
        
        return query_builder_response_formatter(
            [user.to_dict_safe() if hasattr(user, 'to_dict_safe') else user for user in users],
            f"Found {len(users)} users matching '{q}'"
        )
    
    async def advanced_example(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
        query_request: Annotated[QueryBuilderRequest, Depends(get_query_builder_request)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        """
        Advanced QueryBuilder example with custom filters and sorts
        
        Example: GET /api/users/advanced?filter[permission]=edit-users&sort=role_priority&include=latestPost
        """
        from app.Utils.QueryBuilder.AllowedSort import StringLengthSort
        from app.Utils.QueryBuilder.AllowedFilter import CallbackFilter
        
        if not current_user.can('view-users'):
            self.forbidden("You don't have permission to view users")
        
        # Custom filter for users with specific permission
        def filter_by_permission(query: Any, value: Any, property_name: str) -> Any:
            return query.join(User.direct_permissions).filter(
                # Permission.name == value  # Would need proper relationship handling
            )
        
        # Custom sort by name length  
        def sort_by_name_length(query: Any, descending: bool, property_name: str) -> Any:
            direction = "DESC" if descending else "ASC"
            return query.order_by(f"LENGTH(users.name) {direction}")
        
        # Build advanced query
        query_builder = QueryBuilder.for_model(User, db, query_request)
        
        query_builder.allowed_filters([
            AllowedFilter.callback('permission', filter_by_permission),
            AllowedFilter.partial('name'),
            AllowedFilter.exact('is_active')
        ]).allowed_sorts([
            AllowedSort.custom('name_length', StringLengthSort(), 'name'),
            AllowedSort.callback('custom_sort', sort_by_name_length),
            'name',
            'created_at'
        ]).allowed_includes([
            # Custom includes would be defined here
            'roles',
            'rolesCount'
        ]).default_sort('name')
        
        users = query_builder.get()
        
        return query_builder_response_formatter(
            [user.to_dict_safe() if hasattr(user, 'to_dict_safe') else user for user in users],
            "Advanced query executed successfully"
        )