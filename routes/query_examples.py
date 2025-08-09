from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Dict, Any
from typing_extensions import Annotated
from sqlalchemy.orm import Session
from app.Http.Controllers.UserQueryController import UserQueryController
from app.Models import User
from app.Http.Controllers import get_current_user
from config import get_database
from app.Utils.QueryBuilder import QueryBuilderRequest
from app.Utils.QueryBuilder.FastAPIIntegration import get_query_builder_request

# Create router for QueryBuilder examples
router = APIRouter(
    prefix="/api/users",
    tags=["Users with QueryBuilder"],
    responses={404: {"description": "Not found"}}
)

# Initialize controller
user_query_controller = UserQueryController()

# Routes demonstrating QueryBuilder usage
@router.get(
    "/query",
    summary="List users with QueryBuilder",
    description="""
    List users with advanced querying capabilities:
    
    **Filtering Examples:**
    - `?filter[name]=john` - Users with "john" in name
    - `?filter[email]=gmail` - Users with "gmail" in email  
    - `?filter[is_active]=true` - Only active users
    - `?filter[created_at]=>2023-01-01` - Users created after date
    
    **Sorting Examples:**
    - `?sort=name` - Sort by name ascending
    - `?sort=-created_at` - Sort by creation date descending
    - `?sort=name,-created_at` - Multi-column sort
    
    **Including Relationships:**
    - `?include=roles` - Include user roles
    - `?include=rolesCount` - Include role count
    - `?include=roles,permissions` - Include multiple relationships
    
    **Field Selection:**
    - `?fields[users]=id,name,email` - Select specific user fields
    - `?fields[roles]=id,name` - Select specific role fields when included
    
    **Combined Example:**
    ```
    ?filter[is_active]=true&sort=-created_at&include=rolesCount&fields[users]=id,name,email
    ```
    """
)
async def list_users_with_query_builder(
    current_user: Annotated[User, Depends(get_current_user)],
    query_request: Annotated[QueryBuilderRequest, Depends(get_query_builder_request)],
    db: Annotated[Session, Depends(get_database)],
    page: Annotated[int, Depends(lambda: 1)],
    per_page: Annotated[int, Depends(lambda: 15)]
) -> Any:
    return await user_query_controller.index(current_user, query_request, db, page, per_page)

@router.get(
    "/{user_id}",
    summary="Get user with QueryBuilder",
    description="""
    Get single user with includes and field selection:
    
    **Examples:**
    - `GET /api/users/1?include=roles,permissions`
    - `GET /api/users/1?fields[users]=id,name,email&fields[roles]=name`
    """
)
async def get_user_with_query_builder(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    query_request: Annotated[QueryBuilderRequest, Depends(get_query_builder_request)],
    db: Annotated[Session, Depends(get_database)]
) -> Any:
    return await user_query_controller.show(user_id, current_user, query_request, db)

@router.get(
    "/search",
    summary="Search users with QueryBuilder",
    description="""
    Search users by name or email with additional QueryBuilder features:
    
    **Examples:**
    - `GET /api/users/search?q=john&sort=name`
    - `GET /api/users/search?q=admin&include=rolesCount&sort=-created_at`
    """
)
async def search_users_with_query_builder(
    q: str,
    current_user: Annotated[User, Depends(get_current_user)],
    query_request: Annotated[QueryBuilderRequest, Depends(get_query_builder_request)],
    db: Annotated[Session, Depends(get_database)]
) -> Any:
    return await user_query_controller.search(current_user, query_request, db, q)

@router.get(
    "/advanced",
    summary="Advanced QueryBuilder example",
    description="""
    Demonstrates advanced QueryBuilder features:
    - Custom filters and sorts
    - Complex relationship filtering
    - Custom include implementations
    
    **Examples:**
    - `GET /api/users/advanced?filter[permission]=edit-users`
    - `GET /api/users/advanced?sort=name_length&include=latestPost`
    """
)
async def advanced_query_builder_example(
    current_user: Annotated[User, Depends(get_current_user)],
    query_request: Annotated[QueryBuilderRequest, Depends(get_query_builder_request)],
    db: Annotated[Session, Depends(get_database)]
) -> Any:
    return await user_query_controller.advanced_example(current_user, query_request, db)