from __future__ import annotations

from typing import Optional, List, Tuple, Dict, Any, Set, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_, func
from datetime import datetime, timezone
import re

from app.Models import Permission, Role, User
from app.Http.Schemas import PermissionCreate, PermissionUpdate
from app.Services.BaseService import BaseService
from app.Support.Types import validate_types


class PermissionService(BaseService):
    
    @validate_types
    def create_permission(self, permission_data: PermissionCreate) -> Tuple[bool, str, Optional[Permission]]:
        """Create a new permission with comprehensive validation."""
        validation_errors = self._validate_permission_data(permission_data)
        if validation_errors:
            return False, f"Validation failed: {', '.join(validation_errors)}", None
        try:
            # Check if permission already exists
            existing = self.db.query(Permission).filter(
                or_(  # type: ignore[arg-type]
                    Permission.name == permission_data.name,
                    Permission.slug == permission_data.slug
                )
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
    
    @validate_types
    def get_permission_by_id(self, permission_id: int) -> Optional[Permission]:
        """Get permission by ID with validation."""
        if permission_id <= 0:
            return None
        return self.db.query(Permission).filter(Permission.id == permission_id).first()
    
    @validate_types
    def get_permission_by_name(self, name: str) -> Optional[Permission]:
        """Get permission by name or slug with validation."""
        if not name or not name.strip():
            return None
        name = name.strip()
        return self.db.query(Permission).filter(
            or_(  # type: ignore[arg-type]
                Permission.name == name, Permission.slug == name
            )
        ).first()
    
    @validate_types
    def get_all_permissions(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        active_only: bool = True,
        category: Optional[str] = None,
        dangerous_only: bool = False,
        mfa_only: bool = False
    ) -> List[Permission]:
        """Get permissions with comprehensive filtering and validation."""
        # Validate parameters
        skip = max(0, skip)
        limit = max(1, min(1000, limit))  # Cap at 1000 for performance
        
        query = self.db.query(Permission)
        
        if active_only:
            query = query.filter(Permission.is_active == True)
        
        if category:
            query = query.filter(Permission.category == category)
        
        if dangerous_only:
            query = query.filter(Permission.is_dangerous == True)
        
        if mfa_only:
            query = query.filter(Permission.requires_mfa == True)
        
        # Filter expired permissions
        query = query.filter(
            or_(
                Permission.expires_at.is_(None),
                Permission.expires_at > datetime.now(timezone.utc)
            )
        )
        
        return query.order_by(Permission.category, Permission.action, Permission.name).offset(skip).limit(limit).all()
    
    def update_permission(self, permission: Permission, permission_data: PermissionUpdate) -> Tuple[bool, str, Optional[Permission]]:
        try:
            # Check for conflicts if name or slug is being updated
            if permission_data.name or permission_data.slug:
                existing = self.db.query(Permission).filter(
                    Permission.id != permission.id,
                    or_(  # type: ignore[arg-type]
                        Permission.name == (permission_data.name or permission.name),
                        Permission.slug == (permission_data.slug or permission.slug)
                    )
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
    
    @validate_types
    def assign_permission_to_user(self, user: User, permission: Permission) -> Tuple[bool, str]:
        """Assign permission to user with comprehensive validation."""
        validation_errors = self._validate_permission_assignment(user, permission)
        if validation_errors:
            return False, f"Assignment validation failed: {', '.join(validation_errors)}"
        try:
            if permission in user.direct_permissions:
                return False, "User already has this permission"
            
            # Check if permission can be granted to user
            if hasattr(permission, 'can_be_granted_to_user') and not permission.can_be_granted_to_user(user):
                return False, "Permission cannot be granted to this user based on conditions"
            
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
            
            # user.sync_permissions(permissions)  # Method not implemented
            # For now, just assign permissions directly
            for permission in permissions:
                if permission not in user.direct_permissions:
                    user.give_permission_to(permission)
            self.db.commit()
            
            return True, f"User permissions synced successfully ({len(permissions)} permissions)"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to sync user permissions: {str(e)}"
    
    def get_user_permissions(self, user: User) -> Dict[str, List[Permission]]:
        # Get permission objects instead of names for consistency
        role_permissions = []
        all_permissions = list(user.direct_permissions)
        
        # Add role-based permissions
        for role in user.roles:
            role_permissions.extend(role.permissions)
            all_permissions.extend(role.permissions)
        
        return {
            "direct_permissions": list(user.direct_permissions),
            "role_permissions": role_permissions,
            "all_permissions": all_permissions
        }
    
    def check_user_permission(self, user: User, permission_name: str) -> bool:
        return user.has_permission_to(permission_name)
    
    def check_user_permissions(self, user: User, permission_names: List[str], require_all: bool = False) -> bool:
        if require_all:
            return user.has_all_permissions(permission_names)
        else:
            return user.has_any_permission(permission_names)
    
    def search_permissions(self, query: str, skip: int = 0, limit: int = 100) -> List[Permission]:
        # Use individual filter conditions to avoid SQLAlchemy type issues
        search_conditions = [
            Permission.name.ilike(f"%{query}%"),
            Permission.slug.ilike(f"%{query}%"),
            Permission.description.ilike(f"%{query}%")
        ]
        return self.db.query(Permission).filter(or_(*search_conditions)).offset(skip).limit(limit).all()
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
                    or_(  # type: ignore[arg-type]
                        Permission.name == perm_data.name,
                        Permission.slug == perm_data.slug
                    )
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
    
    def _validate_permission_data(self, permission_data: PermissionCreate) -> List[str]:
        """Validate permission creation data."""
        errors = []
        
        # Name validation
        if not permission_data.name or not permission_data.name.strip():
            errors.append("Permission name is required")
        elif len(permission_data.name.strip()) < 3:
            errors.append("Permission name must be at least 3 characters")
        elif len(permission_data.name.strip()) > 100:
            errors.append("Permission name must not exceed 100 characters")
        elif not re.match(r'^[a-zA-Z0-9\.\-_]+$', permission_data.name.strip()):
            errors.append("Permission name contains invalid characters")
        
        # Slug validation
        if permission_data.slug:
            if not re.match(r'^[a-z0-9\-_]+$', permission_data.slug):
                errors.append("Permission slug can only contain lowercase letters, numbers, hyphens, and underscores")
            elif len(permission_data.slug) > 100:
                errors.append("Permission slug must not exceed 100 characters")
        
        # Description validation
        if permission_data.description and len(permission_data.description) > 500:
            errors.append("Permission description must not exceed 500 characters")
        
        # Category validation
        if hasattr(permission_data, 'category') and permission_data.category:
            if not re.match(r'^[a-zA-Z0-9\-_]+$', permission_data.category):
                errors.append("Permission category contains invalid characters")
        
        # Action validation
        if hasattr(permission_data, 'action') and permission_data.action:
            if not re.match(r'^[a-zA-Z0-9\-_]+$', permission_data.action):
                errors.append("Permission action contains invalid characters")
        
        # Wildcard pattern validation
        if hasattr(permission_data, 'is_wildcard') and permission_data.is_wildcard:
            if not hasattr(permission_data, 'pattern') or not permission_data.pattern:
                errors.append("Wildcard permissions must have a pattern")
        
        return errors
    
    def _validate_permission_assignment(self, user: User, permission: Permission) -> List[str]:
        """Validate permission assignment."""
        errors = []
        
        # Check if user is active
        if not user.is_active:
            errors.append("Cannot assign permission to inactive user")
        
        # Check if permission is active
        if not permission.is_active:
            errors.append("Cannot assign inactive permission")
        
        # Check permission expiration
        if hasattr(permission, 'is_expired') and permission.is_expired():
            errors.append("Cannot assign expired permission")
        
        # Check dangerous permission requirements
        if permission.is_dangerous and not user.is_email_verified():
            errors.append("Cannot assign dangerous permission to unverified user")
        
        # Check MFA requirement
        if permission.requires_mfa and not user.has_mfa_enabled():
            errors.append("Permission requires MFA but user does not have MFA enabled")
        
        return errors
    
    @validate_types
    def get_permission_statistics(self) -> Dict[str, Any]:
        """Get comprehensive permission statistics."""
        total_permissions = self.db.query(Permission).count()
        active_permissions = self.db.query(Permission).filter(Permission.is_active == True).count()
        dangerous_permissions = self.db.query(Permission).filter(Permission.is_dangerous == True).count()
        mfa_permissions = self.db.query(Permission).filter(Permission.requires_mfa == True).count()
        wildcard_permissions = self.db.query(Permission).filter(Permission.is_wildcard == True).count()
        
        # Get category distribution
        category_distribution = dict(
            self.db.query(Permission.category, func.count(Permission.id))
            .filter(Permission.is_active == True)
            .group_by(Permission.category)
            .all()
        )
        
        return {
            "total_permissions": total_permissions,
            "active_permissions": active_permissions,
            "inactive_permissions": total_permissions - active_permissions,
            "dangerous_permissions": dangerous_permissions,
            "mfa_required_permissions": mfa_permissions,
            "wildcard_permissions": wildcard_permissions,
            "category_distribution": category_distribution,
            "permissions_with_roles": self._count_permissions_with_roles(),
            "permissions_with_users": self._count_permissions_with_users()
        }
    
    def _count_permissions_with_roles(self) -> int:
        """Count permissions that are assigned to at least one role."""
        return self.db.query(Permission.id)\
            .join(Permission.roles)\
            .group_by(Permission.id)\
            .having(func.count(Role.id) > 0)\
            .count()
    
    def _count_permissions_with_users(self) -> int:
        """Count permissions that are assigned directly to at least one user."""
        return self.db.query(Permission.id)\
            .join(Permission.users)\
            .group_by(Permission.id)\
            .having(func.count(User.id) > 0)\
            .count()
    
    @validate_types
    def find_wildcard_matches(self, permission_name: str) -> List[Permission]:
        """Find wildcard permissions that match the given permission name."""
        if not permission_name or not permission_name.strip():
            return []
        
        wildcard_permissions = self.db.query(Permission).filter(
            and_(
                Permission.is_wildcard == True,
                Permission.is_active == True,
                Permission.pattern.is_not(None)
            )
        ).all()
        
        matches = []
        for perm in wildcard_permissions:
            if perm.matches_pattern(permission_name.strip()):
                matches.append(perm)
        
        return matches