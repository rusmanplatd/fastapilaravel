from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from app.Models import Permission, Role, User
from app.Http.Schemas import RoleCreate, RoleUpdate
from app.Services.BaseService import BaseService


class RoleService(BaseService):
    
    def create_role(self, role_data: RoleCreate) -> Tuple[bool, str, Optional[Role]]:
        try:
            # Check if role already exists
            existing = self.db.query(Role).filter(
                or_(
                    Role.name == role_data.name,
                    Role.slug == role_data.slug
                )  # type: ignore[arg-type]
            ).first()
            
            if existing:
                return False, "Role with this name or slug already exists", None
            
            role = Role(
                name=role_data.name,
                slug=role_data.slug,
                description=role_data.description,
                guard_name=role_data.guard_name,
                is_default=role_data.is_default
            )
            
            self.db.add(role)
            self.db.commit()
            self.db.refresh(role)
            
            return True, "Role created successfully", role
            
        except IntegrityError:
            self.db.rollback()
            return False, "Role with this name or slug already exists", None
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to create role: {str(e)}", None
    
    def get_role_by_id(self, role_id: int) -> Optional[Role]:
        return self.db.query(Role).filter(Role.id == role_id).first()
    
    def get_role_by_name(self, name: str) -> Optional[Role]:
        return self.db.query(Role).filter(
            or_(Role.name == name, Role.slug == name)  # type: ignore[arg-type]
        ).first()
    
    def get_all_roles(self, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[Role]:
        query = self.db.query(Role)
        if active_only:
            query = query.filter(Role.is_active == True)
        return query.offset(skip).limit(limit).all()
    
    def get_default_role(self) -> Optional[Role]:
        return self.db.query(Role).filter(Role.is_default == True, Role.is_active == True).first()
    
    def update_role(self, role: Role, role_data: RoleUpdate) -> Tuple[bool, str, Optional[Role]]:
        try:
            # Check for conflicts if name or slug is being updated
            if role_data.name or role_data.slug:
                existing = self.db.query(Role).filter(
                    Role.id != role.id,
                    or_(
                        Role.name == (role_data.name or role.name),
                        Role.slug == (role_data.slug or role.slug)
                    )  # type: ignore[arg-type]
                ).first()
                
                if existing:
                    return False, "Role with this name or slug already exists", None
            
            # Update fields
            update_data = role_data.dict(exclude_unset=True)
            for key, value in update_data.items():
                if hasattr(role, key):
                    setattr(role, key, value)
            
            self.db.commit()
            self.db.refresh(role)
            
            return True, "Role updated successfully", role
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to update role: {str(e)}", None
    
    def delete_role(self, role: Role) -> Tuple[bool, str]:
        try:
            # Check if role is assigned to any users
            if role.users:
                return False, "Cannot delete role that is assigned to users"
            
            self.db.delete(role)
            self.db.commit()
            
            return True, "Role deleted successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to delete role: {str(e)}"
    
    def deactivate_role(self, role: Role) -> Tuple[bool, str]:
        try:
            role.is_active = False
            self.db.commit()
            self.db.refresh(role)
            
            return True, "Role deactivated successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to deactivate role: {str(e)}"
    
    def activate_role(self, role: Role) -> Tuple[bool, str]:
        try:
            role.is_active = True
            self.db.commit()
            self.db.refresh(role)
            
            return True, "Role activated successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to activate role: {str(e)}"
    
    # Role-Permission Management
    
    def assign_permission_to_role(self, role: Role, permission: Permission) -> Tuple[bool, str]:
        try:
            if permission in role.permissions:
                return False, "Role already has this permission"
            
            role.give_permission_to(permission)
            self.db.commit()
            
            return True, "Permission assigned to role successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to assign permission to role: {str(e)}"
    
    def revoke_permission_from_role(self, role: Role, permission: Permission) -> Tuple[bool, str]:
        try:
            if permission not in role.permissions:
                return False, "Role does not have this permission"
            
            role.revoke_permission_to(permission)
            self.db.commit()
            
            return True, "Permission revoked from role successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to revoke permission from role: {str(e)}"
    
    def sync_role_permissions(self, role: Role, permission_ids: List[int]) -> Tuple[bool, str]:
        try:
            permissions = self.db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
            
            if len(permissions) != len(permission_ids):
                return False, "Some permissions not found"
            
            role.sync_permissions(permissions)
            self.db.commit()
            
            return True, f"Role permissions synced successfully ({len(permissions)} permissions)"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to sync role permissions: {str(e)}"
    
    # User-Role Management
    
    def assign_role_to_user(self, user: User, role: Role) -> Tuple[bool, str]:
        try:
            if role in user.roles:
                return False, "User already has this role"
            
            user.assign_role(role)
            self.db.commit()
            
            return True, "Role assigned to user successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to assign role to user: {str(e)}"
    
    def remove_role_from_user(self, user: User, role: Role) -> Tuple[bool, str]:
        try:
            if role not in user.roles:
                return False, "User does not have this role"
            
            user.remove_role(role)
            self.db.commit()
            
            return True, "Role removed from user successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to remove role from user: {str(e)}"
    
    def sync_user_roles(self, user: User, role_ids: List[int]) -> Tuple[bool, str]:
        try:
            roles = self.db.query(Role).filter(Role.id.in_(role_ids)).all()
            
            if len(roles) != len(role_ids):
                return False, "Some roles not found"
            
            user.sync_roles(roles)
            self.db.commit()
            
            return True, f"User roles synced successfully ({len(roles)} roles)"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to sync user roles: {str(e)}"
    
    def assign_default_role_to_user(self, user: User) -> Tuple[bool, str]:
        default_role = self.get_default_role()
        if not default_role:
            return False, "No default role configured"
        
        return self.assign_role_to_user(user, default_role)
    
    # Role Checking
    
    def check_user_role(self, user: User, role_name: str) -> bool:
        return user.has_role(role_name)
    
    def check_user_roles(self, user: User, role_names: List[str], require_all: bool = False) -> bool:
        if require_all:
            return user.has_all_roles(role_names)
        else:
            return user.has_any_role(role_names)
    
    def get_user_roles(self, user: User) -> List[Role]:
        return list(user.roles)
    
    def get_role_permissions(self, role: Role) -> List[Permission]:
        return list(role.permissions)
    
    def get_role_users(self, role: Role) -> List[User]:
        return list(role.users)
    
    # Search and Utility
    
    def search_roles(self, query: str, skip: int = 0, limit: int = 100) -> List[Role]:
        search_filter = or_(
            Role.name.ilike(f"%{query}%"),
            Role.slug.ilike(f"%{query}%"),
            Role.description.ilike(f"%{query}%")
        )
        
        return self.db.query(Role).filter(search_filter).offset(skip).limit(limit).all()  # type: ignore[arg-type]
    
    def get_roles_count(self, active_only: bool = True) -> int:
        query = self.db.query(Role)
        if active_only:
            query = query.filter(Role.is_active == True)
        return query.count()
    
    def bulk_create_roles(self, roles_data: List[RoleCreate]) -> Tuple[bool, str, List[Role]]:
        try:
            created_roles = []
            
            for role_data in roles_data:
                # Check if role already exists
                existing = self.db.query(Role).filter(
                    or_(
                        Role.name == role_data.name,
                        Role.slug == role_data.slug
                    )  # type: ignore[arg-type]
                ).first()
                
                if not existing:
                    role = Role(
                        name=role_data.name,
                        slug=role_data.slug,
                        description=role_data.description,
                        guard_name=role_data.guard_name,
                        is_default=role_data.is_default
                    )
                    self.db.add(role)
                    created_roles.append(role)
            
            self.db.commit()
            
            for role in created_roles:
                self.db.refresh(role)
            
            return True, f"Created {len(created_roles)} roles", created_roles
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to create roles: {str(e)}", []
    
    def get_role_with_permissions(self, role_id: int) -> Optional[Role]:
        return self.db.query(Role).filter(Role.id == role_id).first()