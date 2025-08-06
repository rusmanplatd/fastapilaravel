from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.Http.Controllers import RoleController, get_current_user
from app.Http.Schemas import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    UserRoleAssignment,
    RolePermissionAssignment,
    RoleCheck,
    MultipleRoleCheck
)
from app.Models import User
from config import get_database

roles_router = APIRouter(prefix="/roles", tags=["Roles"])
role_controller = RoleController()


@roles_router.post("/", response_model=dict)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.create_role(role_data, current_user, db)


@roles_router.get("/", response_model=dict)
async def get_roles(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    search: str = None,
    include_permissions: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.get_roles(skip, limit, active_only, search, include_permissions, current_user, db)


@roles_router.get("/{role_id}", response_model=dict)
async def get_role(
    role_id: int,
    include_permissions: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.get_role(role_id, include_permissions, current_user, db)


@roles_router.put("/{role_id}", response_model=dict)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.update_role(role_id, role_data, current_user, db)


@roles_router.delete("/{role_id}", response_model=dict)
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.delete_role(role_id, current_user, db)


@roles_router.post("/{role_id}/permissions", response_model=dict)
async def assign_permissions_to_role(
    role_id: int,
    assignment_data: RolePermissionAssignment,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    # Update the assignment data with role_id
    assignment_data.role_id = role_id
    return role_controller.assign_permission_to_role(role_id, assignment_data, current_user, db)


@roles_router.post("/assign-to-user", response_model=dict)
async def assign_roles_to_user(
    assignment_data: UserRoleAssignment,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.assign_role_to_user(assignment_data, current_user, db)


@roles_router.post("/users/{user_id}/check", response_model=dict)
async def check_user_role(
    user_id: int,
    role_check: RoleCheck,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.check_user_role(user_id, role_check, current_user, db)


@roles_router.post("/users/{user_id}/check-multiple", response_model=dict)
async def check_user_multiple_roles(
    user_id: int,
    role_check: MultipleRoleCheck,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.check_user_multiple_roles(user_id, role_check, current_user, db)


@roles_router.get("/users/{user_id}", response_model=dict)
async def get_user_roles(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.get_user_roles(user_id, current_user, db)


@roles_router.get("/{role_id}/permissions", response_model=dict)
async def get_role_permissions(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.get_role_permissions(role_id, current_user, db)


@roles_router.get("/{role_id}/users", response_model=dict)
async def get_role_users(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.get_role_users(role_id, current_user, db)


@roles_router.post("/bulk-create", response_model=dict)
async def bulk_create_roles(
    roles_data: List[RoleCreate],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.bulk_create_roles(roles_data, current_user, db)


@roles_router.post("/{role_id}/activate", response_model=dict)
async def activate_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.activate_role(role_id, current_user, db)


@roles_router.post("/{role_id}/deactivate", response_model=dict)
async def deactivate_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    return role_controller.deactivate_role(role_id, current_user, db)