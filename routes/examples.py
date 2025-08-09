from __future__ import annotations

from typing import Dict, Any, List
from typing_extensions import Annotated
from fastapi import APIRouter, Depends
from app.Http.Controllers import get_current_user
from app.Http.Middleware import can, is_role, has_any_permission, has_all_roles
from app.Models import User

examples_router = APIRouter(prefix="/examples", tags=["Permission Examples"])


# Example 1: Using dependency injection for permission checking
@examples_router.get("/admin-only")
async def admin_only_route(current_user: Annotated[User, Depends(can("view-dashboard"))]) -> Dict[str, Any]:
    return {
        "message": "You have admin access!",
        "user": current_user.name,
        "permissions": current_user.get_permission_names()
    }


# Example 2: Using role-based access
@examples_router.get("/super-admin-only")
async def super_admin_only_route(current_user: Annotated[User, Depends(is_role("super-admin"))]) -> Dict[str, Any]:
    return {
        "message": "Welcome Super Admin!",
        "user": current_user.name,
        "roles": current_user.get_role_names()
    }


# Example 3: Multiple permissions (any of them)
@examples_router.get("/content-manager")
async def content_manager_route(
    current_user: Annotated[User, Depends(has_any_permission(["create-posts", "edit-posts", "delete-posts"]))]
) -> Dict[str, Any]:
    return {
        "message": "You can manage content!",
        "user": current_user.name,
        "permissions": current_user.get_permission_names()
    }


# Example 4: Multiple roles required (all of them)
@examples_router.get("/admin-editor")
async def admin_editor_route(
    current_user: Annotated[User, Depends(has_all_roles(["admin", "editor"]))]
) -> Dict[str, Any]:
    return {
        "message": "You are both admin and editor!",
        "user": current_user.name,
        "roles": current_user.get_role_names()
    }


# Example 5: Manual permission checking within route
@examples_router.get("/flexible-access")
async def flexible_access_route(current_user: Annotated[User, Depends(get_current_user)]) -> Dict[str, Any]:
    # Manual permission checking with custom logic
    if current_user.can("view-reports"):
        access_level = "full"
        message = "You have full access to reports"
    elif current_user.can("view-dashboard"):
        access_level = "limited"
        message = "You have limited access to dashboard"
    else:
        access_level = "none"
        message = "You have no special access"
    
    return {
        "message": message,
        "access_level": access_level,
        "user": current_user.name,
        "roles": current_user.get_role_names(),
        "permissions": current_user.get_permission_names()
    }


# Example 6: Check specific permissions programmatically
@examples_router.get("/permission-check")
async def permission_check_route(current_user: Annotated[User, Depends(get_current_user)]) -> Dict[str, Any]:
    checks = {
        "can_create_users": current_user.can("create-users"),
        "can_edit_posts": current_user.can("edit-posts"),
        "can_view_settings": current_user.can("view-settings"),
        "has_admin_role": current_user.has_role("admin"),
        "has_user_role": current_user.has_role("user"),
        "can_manage_any": current_user.has_any_permission(["create-users", "edit-users", "delete-users"]),
        "is_content_manager": current_user.has_any_role(["admin", "editor", "author"])
    }
    
    return {
        "user": current_user.name,
        "permission_checks": checks,
        "user_roles": current_user.get_role_names(),
        "user_permissions": current_user.get_permission_names()
    }


# Example 7: File upload with permission check
@examples_router.post("/upload-file")
async def upload_file_route(current_user: Annotated[User, Depends(can("upload-files"))]) -> Dict[str, Any]:
    # File upload logic would go here
    return {
        "message": "File uploaded successfully!",
        "user": current_user.name,
        "note": "This endpoint requires 'upload-files' permission"
    }