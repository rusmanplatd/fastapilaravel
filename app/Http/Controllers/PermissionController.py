from fastapi import Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from typing_extensions import Annotated

from app.Http.Controllers.BaseController import BaseController
from app.Http.Schemas import (
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
    UserPermissionAssignment,
    PermissionCheck,
    MultiplePermissionCheck
)
from app.Services import PermissionService
from app.Models import User, Permission
from app.Http.Controllers import get_current_user
from config import get_database


class PermissionController(BaseController):
    
    def create_permission(
        self,
        permission_data: PermissionCreate,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        # Check if user has permission to create permissions
        if not current_user.can('create-permissions'):
            self.forbidden("You don't have permission to create permissions")
        
        permission_service = PermissionService(db)
        success, message, permission = permission_service.create_permission(permission_data)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        permission_response = PermissionResponse.model_validate(permission)  # type: ignore[attr-defined]
        return self.success_response(
            data=permission_response,
            message=message,
            status_code=status.HTTP_201_CREATED
        )
    
    def get_permissions(
        self,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)],
        skip: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=1000)] = 100,
        active_only: Annotated[bool, Query()] = True,
        search: Annotated[Optional[str], Query()] = None
    ) -> Dict[str, Any]:
        if not current_user.can('view-permissions'):
            self.forbidden("You don't have permission to view permissions")
        
        permission_service = PermissionService(db)
        
        if search:
            permissions = permission_service.search_permissions(search, skip, limit)
        else:
            permissions = permission_service.get_all_permissions(skip, limit, active_only)
        
        permission_responses = [PermissionResponse.model_validate(perm) for perm in permissions]  # type: ignore[attr-defined]
        
        return self.success_response(
            data={
                "permissions": permission_responses,
                "total": permission_service.get_permissions_count(active_only),
                "skip": skip,
                "limit": limit
            },
            message="Permissions retrieved successfully"
        )
    
    def get_permission(
        self,
        permission_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        if not current_user.can('view-permissions'):
            self.forbidden("You don't have permission to view permissions")
        
        permission_service = PermissionService(db)
        permission = permission_service.get_permission_by_id(permission_id)
        
        if not permission:
            self.not_found("Permission not found")
        
        permission_response = PermissionResponse.model_validate(permission)  # type: ignore[attr-defined]
        return self.success_response(
            data=permission_response,
            message="Permission retrieved successfully"
        )
    
    def update_permission(
        self,
        permission_id: int,
        permission_data: PermissionUpdate,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        if not current_user.can('edit-permissions'):
            self.forbidden("You don't have permission to edit permissions")
        
        permission_service = PermissionService(db)
        permission = permission_service.get_permission_by_id(permission_id)
        
        if not permission:
            self.not_found("Permission not found")
        
        success, message, updated_permission = permission_service.update_permission(permission, permission_data)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        permission_response = PermissionResponse.model_validate(updated_permission)  # type: ignore[attr-defined]
        return self.success_response(
            data=permission_response,
            message=message
        )
    
    def delete_permission(
        self,
        permission_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        if not current_user.can('delete-permissions'):
            self.forbidden("You don't have permission to delete permissions")
        
        permission_service = PermissionService(db)
        permission = permission_service.get_permission_by_id(permission_id)
        
        if not permission:
            self.not_found("Permission not found")
        
        success, message = permission_service.delete_permission(permission)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)
    
    def deactivate_permission(
        self,
        permission_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        if not current_user.can('edit-permissions'):
            self.forbidden("You don't have permission to edit permissions")
        
        permission_service = PermissionService(db)
        permission = permission_service.get_permission_by_id(permission_id)
        
        if not permission:
            self.not_found("Permission not found")
        
        success, message = permission_service.deactivate_permission(permission)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)
    
    def activate_permission(
        self,
        permission_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        if not current_user.can('edit-permissions'):
            self.forbidden("You don't have permission to edit permissions")
        
        permission_service = PermissionService(db)
        permission = permission_service.get_permission_by_id(permission_id)
        
        if not permission:
            self.not_found("Permission not found")
        
        success, message = permission_service.activate_permission(permission)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)
    
    def assign_permission_to_user(
        self,
        assignment_data: UserPermissionAssignment,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        if not current_user.can('assign-permissions'):
            self.forbidden("You don't have permission to assign permissions")
        
        permission_service = PermissionService(db)
        
        # Get user
        user = db.query(User).filter(User.id == assignment_data.user_id).first()
        if not user:
            self.not_found("User not found")
        
        permission_ids = [int(pid) for pid in assignment_data.permission_ids]
        success, message = permission_service.sync_user_permissions(user, permission_ids)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        return self.success_response(message=message)
    
    def check_user_permission(
        self,
        user_id: int,
        permission_check: PermissionCheck,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        if not current_user.can('view-permissions'):
            self.forbidden("You don't have permission to check permissions")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            self.not_found("User not found")
        
        permission_service = PermissionService(db)
        has_permission = permission_service.check_user_permission(user, permission_check.permission)
        
        return self.success_response(
            data={
                "user_id": user_id,
                "permission": permission_check.permission,
                "has_permission": has_permission
            },
            message="Permission check completed"
        )
    
    def check_user_multiple_permissions(
        self,
        user_id: int,
        permission_check: MultiplePermissionCheck,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        if not current_user.can('view-permissions'):
            self.forbidden("You don't have permission to check permissions")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            self.not_found("User not found")
        
        permission_service = PermissionService(db)
        has_permissions = permission_service.check_user_permissions(
            user, 
            permission_check.permissions, 
            permission_check.require_all
        )
        
        return self.success_response(
            data={
                "user_id": user_id,
                "permissions": permission_check.permissions,
                "require_all": permission_check.require_all,
                "has_permissions": has_permissions
            },
            message="Multiple permission check completed"
        )
    
    def get_user_permissions(
        self,
        user_id: int,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        if not current_user.can('view-permissions'):
            self.forbidden("You don't have permission to view permissions")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            self.not_found("User not found")
        
        permission_service = PermissionService(db)
        user_permissions = permission_service.get_user_permissions(user)
        
        return self.success_response(
            data={
                "user_id": user_id,
                "direct_permissions": [PermissionResponse.model_validate(perm) for perm in user_permissions["direct_permissions"]],  # type: ignore[attr-defined]
                "all_permissions": [PermissionResponse.model_validate(perm) for perm in user_permissions["all_permissions"]]  # type: ignore[attr-defined]
            },
            message="User permissions retrieved successfully"
        )
    
    def bulk_create_permissions(
        self,
        permissions_data: List[PermissionCreate],
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_database)]
    ) -> Dict[str, Any]:
        if not current_user.can('create-permissions'):
            self.forbidden("You don't have permission to create permissions")
        
        permission_service = PermissionService(db)
        success, message, created_permissions = permission_service.bulk_create_permissions(permissions_data)
        
        if not success:
            self.error_response(message, status.HTTP_400_BAD_REQUEST)
        
        permission_responses = [PermissionResponse.model_validate(perm) for perm in created_permissions]  # type: ignore[attr-defined]
        return self.success_response(
            data=permission_responses,
            message=message,
            status_code=status.HTTP_201_CREATED
        )