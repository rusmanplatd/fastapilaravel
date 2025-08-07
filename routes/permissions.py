from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from typing_extensions import Annotated

from app.Http.Controllers import PermissionController, get_current_user
from app.Http.Schemas import (
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
    UserPermissionAssignment,
    PermissionCheck,
    MultiplePermissionCheck
)
from app.Models import User
from config import get_database

permissions_router = APIRouter(prefix="/permissions", tags=["Permissions"])
permission_controller = PermissionController()


@permissions_router.post("/", response_model=dict)
async def create_permission(
    permission_data: PermissionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict:
    return permission_controller.create_permission(permission_data, current_user, db)


@permissions_router.get("/", response_model=dict)
async def get_permissions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)],
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    search: str = None
) -> dict:
    return permission_controller.get_permissions(skip, limit, active_only, search, current_user, db)


@permissions_router.get("/{permission_id}", response_model=dict)
async def get_permission(
    permission_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict:
    return permission_controller.get_permission(permission_id, current_user, db)


@permissions_router.put("/{permission_id}", response_model=dict)
async def update_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict:
    return permission_controller.update_permission(permission_id, permission_data, current_user, db)


@permissions_router.delete("/{permission_id}", response_model=dict)
async def delete_permission(
    permission_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict:
    return permission_controller.delete_permission(permission_id, current_user, db)


@permissions_router.post("/{permission_id}/deactivate", response_model=dict)
async def deactivate_permission(
    permission_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict:
    return permission_controller.deactivate_permission(permission_id, current_user, db)


@permissions_router.post("/{permission_id}/activate", response_model=dict)
async def activate_permission(
    permission_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict:
    return permission_controller.activate_permission(permission_id, current_user, db)


@permissions_router.post("/assign-to-user", response_model=dict)
async def assign_permissions_to_user(
    assignment_data: UserPermissionAssignment,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict:
    return permission_controller.assign_permission_to_user(assignment_data, current_user, db)


@permissions_router.post("/users/{user_id}/check", response_model=dict)
async def check_user_permission(
    user_id: int,
    permission_check: PermissionCheck,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict:
    return permission_controller.check_user_permission(user_id, permission_check, current_user, db)


@permissions_router.post("/users/{user_id}/check-multiple", response_model=dict)
async def check_user_multiple_permissions(
    user_id: int,
    permission_check: MultiplePermissionCheck,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict:
    return permission_controller.check_user_multiple_permissions(user_id, permission_check, current_user, db)


@permissions_router.get("/users/{user_id}", response_model=dict)
async def get_user_permissions(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict:
    return permission_controller.get_user_permissions(user_id, current_user, db)


@permissions_router.post("/bulk-create", response_model=dict)
async def bulk_create_permissions(
    permissions_data: List[PermissionCreate],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_database)]
) -> dict:
    return permission_controller.bulk_create_permissions(permissions_data, current_user, db)