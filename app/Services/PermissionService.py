from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from app.Models import Permission, Role, User
from app.Http.Schemas import PermissionCreate, PermissionUpdate
from app.Services.BaseService import BaseService


class PermissionService(BaseService):
    
    def create_permission(self, permission_data: PermissionCreate) -> Tuple[bool, str, Optional[Permission]]:
        try:
            # Check if permission already exists
            existing = self.db.query(Permission).filter(
                or_(
                    Permission.name == permission_data.name,
                    Permission.slug == permission_data.slug
                )  # type: ignore[arg-type]
            ).first()
            
            if existing:
                return False, "Permission with this name or slug already exists", None
            
            permission = Permission(
                name=permission_data.name,
                slug=permission_data.slug,
                description=permission_data.description,
                guard_name=permission_data.guard_name
            )
            
            self.db.add(permission)
            self.db.commit()
            self.db.refresh(permission)
            
            return True, "Permission created successfully", permission
            
        except IntegrityError:
            self.db.rollback()
            return False, "Permission with this name or slug already exists", None
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to create permission: {str(e)}", None
    
    def get_permission_by_id(self, permission_id: int) -> Optional[Permission]:
        return self.db.query(Permission).filter(Permission.id == permission_id).first()
    
    def get_permission_by_name(self, name: str) -> Optional[Permission]:
        return self.db.query(Permission).filter(
            or_(Permission.name == name, Permission.slug == name)  # type: ignore[arg-type]
        ).first()
    
    def get_all_permissions(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[Permission]:
        query = self.db.query(Permission)
        if active_only:
            query = query.filter(Permission.is_active == True)
        return query.offset(skip).limit(limit).all()
    
    def update_permission(self, permission: Permission, permission_data: PermissionUpdate) -> Tuple[bool, str, Optional[Permission]]:
        try:
            # Check for conflicts if name or slug is being updated
            if permission_data.name or permission_data.slug:
                existing = self.db.query(Permission).filter(
                    Permission.id != permission.id,
                    or_(
                        Permission.name == (permission_data.name or permission.name),
                        Permission.slug == (permission_data.slug or permission.slug)
                    )  # type: ignore[arg-type]
                ).first()
                
                if existing:
                    return False, "Permission with this name or slug already exists", None
            
            # Update fields
            update_data = permission_data.dict(exclude_unset=True)
            for key, value in update_data.items():
                if hasattr(permission, key):
                    setattr(permission, key, value)
            
            self.db.commit()
            self.db.refresh(permission)
            
            return True, "Permission updated successfully", permission
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to update permission: {str(e)}", None
    
    def delete_permission(self, permission: Permission) -> Tuple[bool, str]:
        try:
            # Check if permission is assigned to any roles or users
            if permission.roles or permission.users:
                return False, "Cannot delete permission that is assigned to roles or users"
            
            self.db.delete(permission)
            self.db.commit()
            
            return True, "Permission deleted successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to delete permission: {str(e)}"
    
    def deactivate_permission(self, permission: Permission) -> Tuple[bool, str]:
        try:
            permission.is_active = False
            self.db.commit()
            self.db.refresh(permission)
            
            return True, "Permission deactivated successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to deactivate permission: {str(e)}"
    
    def activate_permission(self, permission: Permission) -> Tuple[bool, str]:
        try:
            permission.is_active = True
            self.db.commit()
            self.db.refresh(permission)
            
            return True, "Permission activated successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to activate permission: {str(e)}"
    
    def assign_permission_to_user(self, user: User, permission: Permission) -> Tuple[bool, str]:
        try:
            if permission in user.direct_permissions:
                return False, "User already has this permission"
            
            user.give_permission_to(permission)
            self.db.commit()
            
            return True, "Permission assigned to user successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to assign permission to user: {str(e)}"
    
    def revoke_permission_from_user(self, user: User, permission: Permission) -> Tuple[bool, str]:
        try:
            if permission not in user.direct_permissions:
                return False, "User does not have this direct permission"
            
            user.revoke_permission_to(permission)
            self.db.commit()
            
            return True, "Permission revoked from user successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to revoke permission from user: {str(e)}"
    
    def sync_user_permissions(self, user: User, permission_ids: List[int]) -> Tuple[bool, str]:
        try:
            permissions = self.db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
            
            if len(permissions) != len(permission_ids):
                return False, "Some permissions not found"
            
            user.sync_permissions(permissions)
            self.db.commit()
            
            return True, f"User permissions synced successfully ({len(permissions)} permissions)"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to sync user permissions: {str(e)}"
    
    def get_user_permissions(self, user: User) -> Dict[str, List[Permission]]:
        return {
            "direct_permissions": list(user.direct_permissions),
            "role_permissions": user.get_all_permissions(),
            "all_permissions": user.get_all_permissions()
        }
    
    def check_user_permission(self, user: User, permission_name: str) -> bool:
        return user.has_permission_to(permission_name)
    
    def check_user_permissions(self, user: User, permission_names: List[str], require_all: bool = False) -> bool:
        if require_all:
            return user.has_all_permissions(permission_names)
        else:
            return user.has_any_permission(permission_names)
    
    def search_permissions(self, query: str, skip: int = 0, limit: int = 100) -> List[Permission]:
        search_filter = or_(
            Permission.name.ilike(f"%{query}%"),
            Permission.slug.ilike(f"%{query}%"),
            Permission.description.ilike(f"%{query}%")
        )
        
        return self.db.query(Permission).filter(search_filter).offset(skip).limit(limit).all()  # type: ignore[arg-type]
    
    def get_permissions_count(self, active_only: bool = True) -> int:
        query = self.db.query(Permission)
        if active_only:
            query = query.filter(Permission.is_active == True)
        return query.count()
    
    def bulk_create_permissions(self, permissions_data: List[PermissionCreate]) -> Tuple[bool, str, List[Permission]]:
        try:
            created_permissions = []
            
            for perm_data in permissions_data:
                # Check if permission already exists
                existing = self.db.query(Permission).filter(
                    or_(
                        Permission.name == perm_data.name,
                        Permission.slug == perm_data.slug
                    )  # type: ignore[arg-type]
                ).first()
                
                if not existing:
                    permission = Permission(
                        name=perm_data.name,
                        slug=perm_data.slug,
                        description=perm_data.description,
                        guard_name=perm_data.guard_name
                    )
                    self.db.add(permission)
                    created_permissions.append(permission)
            
            self.db.commit()
            
            for perm in created_permissions:
                self.db.refresh(perm)
            
            return True, f"Created {len(created_permissions)} permissions", created_permissions
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to create permissions: {str(e)}", []