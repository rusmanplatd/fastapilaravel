from __future__ import annotations

from fastapi import APIRouter
from app.Http.Controllers.UserQueryController import UserQueryController

# Create router for QueryBuilder examples
router = APIRouter(
    prefix="/api/users",
    tags=["Users with QueryBuilder"],
    responses={404: {"description": "Not found"}}
)

# Initialize controller
user_query_controller = UserQueryController()

# Routes demonstrating QueryBuilder usage
router.add_api_route(
    "/query",
    user_query_controller.index,
    methods=["GET"],
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

router.add_api_route(
    "/{user_id}",
    user_query_controller.show,
    methods=["GET"],
    summary="Get user with QueryBuilder",
    description="""
    Get single user with includes and field selection:
    
    **Examples:**
    - `GET /api/users/1?include=roles,permissions`
    - `GET /api/users/1?fields[users]=id,name,email&fields[roles]=name`
    """
)

router.add_api_route(
    "/search",
    user_query_controller.search,
    methods=["GET"],
    summary="Search users with QueryBuilder",
    description="""
    Search users by name or email with additional QueryBuilder features:
    
    **Examples:**
    - `GET /api/users/search?q=john&sort=name`
    - `GET /api/users/search?q=admin&include=rolesCount&sort=-created_at`
    """
)

router.add_api_route(
    "/advanced",
    user_query_controller.advanced_example,
    methods=["GET"],
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