from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.Http.Controllers.BaseController import BaseController
from app.Http.Schemas import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleWithPermissions,
    UserRoleAssignment,
    RolePermissionAssignment,
    RoleCheck,
    MultipleRoleCheck,
    PermissionResponse
)
from app.Services import RoleService, PermissionService
from app.Models import User, Role, Permission
from app.Http.Controllers import get_current_user
from config import get_database


class RoleController(BaseController):
    
    def create_role(
        self,
        role_data: RoleCreate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('create-roles'):
            self.forbidden("You don't have permission to create roles")
        
        role_service = RoleService(db)
        success, message, role = role_service.create_role(role_data)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        role_response = RoleResponse.from_orm(role)
        return self.success_response(
            data=role_response,
            message=message,
            status_code=status.HTTP_201_CREATED
        )
    
    def get_roles(
        self,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        active_only: bool = Query(True),
        search: Optional[str] = Query(None),
        include_permissions: bool = Query(False),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('view-roles'):
            self.forbidden("You don't have permission to view roles")
        
        role_service = RoleService(db)
        
        if search:
            roles = role_service.search_roles(search, skip, limit)
        else:
            roles = role_service.get_all_roles(skip, limit, active_only)
        
        if include_permissions:
            role_responses = []
            for role in roles:
                role_dict = RoleResponse.from_orm(role).dict()
                role_dict['permissions'] = [PermissionResponse.from_orm(perm) for perm in role.permissions]
                role_responses.append(role_dict)
        else:
            role_responses = [RoleResponse.from_orm(role) for role in roles]
        
        return self.success_response(
            data={
                "roles": role_responses,
                "total": role_service.get_roles_count(active_only),
                "skip": skip,
                "limit": limit
            },
            message="Roles retrieved successfully"
        )
    
    def get_role(
        self,
        role_id: int,
        include_permissions: bool = Query(False),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('view-roles'):
            self.forbidden("You don't have permission to view roles")
        
        role_service = RoleService(db)
        role = role_service.get_role_by_id(role_id)
        
        if not role:
            self.not_found("Role not found")
        
        if include_permissions:
            role_dict = RoleResponse.from_orm(role).dict()
            role_dict['permissions'] = [PermissionResponse.from_orm(perm) for perm in role.permissions]
            return self.success_response(
                data=role_dict,
                message="Role retrieved successfully"
            )
        else:
            role_response = RoleResponse.from_orm(role)
            return self.success_response(
                data=role_response,
                message="Role retrieved successfully"
            )
    
    def update_role(
        self,
        role_id: int,
        role_data: RoleUpdate,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('edit-roles'):
            self.forbidden("You don't have permission to edit roles")
        
        role_service = RoleService(db)
        role = role_service.get_role_by_id(role_id)
        
        if not role:
            self.not_found("Role not found")
        
        success, message, updated_role = role_service.update_role(role, role_data)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        role_response = RoleResponse.from_orm(updated_role)
        return self.success_response(
            data=role_response,
            message=message
        )
    
    def delete_role(
        self,
        role_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('delete-roles'):
            self.forbidden("You don't have permission to delete roles")
        
        role_service = RoleService(db)
        role = role_service.get_role_by_id(role_id)
        
        if not role:
            self.not_found("Role not found")
        
        success, message = role_service.delete_role(role)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)
    
    def assign_permission_to_role(
        self,
        role_id: int,
        assignment_data: RolePermissionAssignment,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('assign-permissions'):
            self.forbidden("You don't have permission to assign permissions")
        
        role_service = RoleService(db)
        role = role_service.get_role_by_id(role_id)
        
        if not role:
            self.not_found("Role not found")
        
        success, message = role_service.sync_role_permissions(role, assignment_data.permission_ids)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)
    
    def assign_role_to_user(
        self,
        assignment_data: UserRoleAssignment,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('assign-roles'):
            self.forbidden("You don't have permission to assign roles")
        
        role_service = RoleService(db)
        
        # Get user
        user = db.query(User).filter(User.id == assignment_data.user_id).first()
        if not user:
            self.not_found("User not found")
        
        success, message = role_service.sync_user_roles(user, assignment_data.role_ids)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)
    
    def check_user_role(
        self,
        user_id: int,
        role_check: RoleCheck,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('view-roles'):
            self.forbidden("You don't have permission to check roles")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            self.not_found("User not found")
        
        role_service = RoleService(db)
        has_role = role_service.check_user_role(user, role_check.role)
        
        return self.success_response(
            data={
                "user_id": user_id,
                "role": role_check.role,
                "has_role": has_role
            },
            message="Role check completed"
        )
    
    def check_user_multiple_roles(
        self,
        user_id: int,
        role_check: MultipleRoleCheck,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('view-roles'):
            self.forbidden("You don't have permission to check roles")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            self.not_found("User not found")
        
        role_service = RoleService(db)
        has_roles = role_service.check_user_roles(
            user, 
            role_check.roles, 
            role_check.require_all
        )
        
        return self.success_response(
            data={
                "user_id": user_id,
                "roles": role_check.roles,
                "require_all": role_check.require_all,
                "has_roles": has_roles
            },
            message="Multiple role check completed"
        )
    
    def get_user_roles(
        self,
        user_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('view-roles'):
            self.forbidden("You don't have permission to view roles")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            self.not_found("User not found")
        
        role_service = RoleService(db)
        user_roles = role_service.get_user_roles(user)
        
        return self.success_response(
            data={
                "user_id": user_id,
                "roles": [RoleResponse.from_orm(role) for role in user_roles]
            },
            message="User roles retrieved successfully"
        )
    
    def get_role_permissions(
        self,
        role_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('view-roles'):
            self.forbidden("You don't have permission to view roles")
        
        role_service = RoleService(db)
        role = role_service.get_role_by_id(role_id)
        
        if not role:
            self.not_found("Role not found")
        
        role_permissions = role_service.get_role_permissions(role)
        
        return self.success_response(
            data={
                "role_id": role_id,
                "role_name": role.name,
                "permissions": [PermissionResponse.from_orm(perm) for perm in role_permissions]
            },
            message="Role permissions retrieved successfully"
        )
    
    def get_role_users(
        self,
        role_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('view-roles'):
            self.forbidden("You don't have permission to view roles")
        
        role_service = RoleService(db)
        role = role_service.get_role_by_id(role_id)
        
        if not role:
            self.not_found("Role not found")
        
        role_users = role_service.get_role_users(role)
        
        return self.success_response(
            data={
                "role_id": role_id,
                "role_name": role.name,
                "users": [{"id": user.id, "name": user.name, "email": user.email} for user in role_users]
            },
            message="Role users retrieved successfully"
        )
    
    def bulk_create_roles(
        self,
        roles_data: List[RoleCreate],
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('create-roles'):
            self.forbidden("You don't have permission to create roles")
        
        role_service = RoleService(db)
        success, message, created_roles = role_service.bulk_create_roles(roles_data)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        role_responses = [RoleResponse.from_orm(role) for role in created_roles]
        return self.success_response(
            data=role_responses,
            message=message,
            status_code=status.HTTP_201_CREATED
        )
    
    def activate_role(
        self,
        role_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('edit-roles'):
            self.forbidden("You don't have permission to edit roles")
        
        role_service = RoleService(db)
        role = role_service.get_role_by_id(role_id)
        
        if not role:
            self.not_found("Role not found")
        
        success, message = role_service.activate_role(role)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)
    
    def deactivate_role(
        self,
        role_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_database)
    ):
        if not current_user.can('edit-roles'):
            self.forbidden("You don't have permission to edit roles")
        
        role_service = RoleService(db)
        role = role_service.get_role_by_id(role_id)
        
        if not role:
            self.not_found("Role not found")
        
        success, message = role_service.deactivate_role(role)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)