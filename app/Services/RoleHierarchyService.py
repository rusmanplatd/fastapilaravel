from __future__ import annotations

from typing import List, Optional, Dict, Any, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_

from app.Models import Role, Permission, User
from app.Services.BaseService import BaseService


class RoleHierarchyService(BaseService):
    """Service for managing role hierarchies and inheritance."""
    
    def create_role_hierarchy(self, parent_role: Role, child_role: Role) -> Tuple[bool, str]:
        """Create a parent-child relationship between roles."""
        try:
            # Validation checks
            if parent_role.id == child_role.id:
                return False, "Role cannot be its own parent"
            
            if child_role.is_ancestor_of(parent_role):
                return False, "Would create circular hierarchy"
            
            if child_role.parent_id == parent_role.id:
                return False, "Hierarchy already exists"
            
            # Set the parent
            success = child_role.set_parent(parent_role)
            if not success:
                return False, "Failed to set parent role"
            
            # Update hierarchy for all descendants
            self._update_descendant_hierarchy(child_role)
            
            self.db.commit()
            return True, "Role hierarchy created successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to create role hierarchy: {str(e)}"
    
    def remove_role_hierarchy(self, role: Role) -> Tuple[bool, str]:
        """Remove a role from its parent, making it a root role."""
        try:
            if not role.parent:
                return False, "Role is already a root role"
            
            # Store children before removing parent
            children = list(role.children)
            
            # Remove from parent
            role.set_parent(None)
            
            # Update hierarchy for this role and descendants
            self._update_descendant_hierarchy(role)
            
            self.db.commit()
            return True, "Role hierarchy removed successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to remove role hierarchy: {str(e)}"
    
    def move_role_in_hierarchy(self, role: Role, new_parent: Optional[Role]) -> Tuple[bool, str]:
        """Move a role to a different position in the hierarchy."""
        try:
            # Validation
            if new_parent and role.is_ancestor_of(new_parent):
                return False, "Cannot move role under its own descendant"
            
            if new_parent and role.id == new_parent.id:
                return False, "Role cannot be its own parent"
            
            # Set new parent
            success = role.set_parent(new_parent)
            if not success:
                return False, "Failed to set new parent role"
            
            # Update hierarchy for all descendants
            self._update_descendant_hierarchy(role)
            
            self.db.commit()
            return True, "Role moved in hierarchy successfully"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to move role in hierarchy: {str(e)}"
    
    def get_role_tree(self, root_role_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get hierarchical tree structure of roles."""
        if root_role_id:
            root_roles = [self.db.query(Role).filter(Role.id == root_role_id).first()]
            if not root_roles[0]:
                return []
        else:
            root_roles = self.db.query(Role).filter(Role.parent_id.is_(None)).all()
        
        def build_tree(role: Role) -> Dict[str, Any]:
            return {
                "role": role.to_dict_safe(),
                "children": [build_tree(child) for child in role.children if child.is_active]
            }
        
        return [build_tree(role) for role in root_roles if role.is_active]
    
    def get_role_hierarchy_path(self, role: Role) -> List[Role]:
        """Get the complete hierarchy path from root to the specified role."""
        return role.get_hierarchy_path()
    
    def get_role_descendants(self, role: Role, include_inactive: bool = False) -> List[Role]:
        """Get all descendant roles."""
        descendants = role.get_descendants()
        if not include_inactive:
            descendants = [desc for desc in descendants if desc.is_active]
        return descendants
    
    def get_role_ancestors(self, role: Role, include_inactive: bool = False) -> List[Role]:
        """Get all ancestor roles."""
        ancestors = role.get_ancestors()
        if not include_inactive:
            ancestors = [anc for anc in ancestors if anc.is_active]
        return ancestors
    
    def get_inherited_permissions(self, role: Role) -> Set[Permission]:
        """Get all permissions inherited from parent roles."""
        inherited = set()
        
        for ancestor in role.get_ancestors():
            if ancestor.is_active:
                inherited.update(ancestor.permissions)
        
        return inherited
    
    def get_effective_permissions(self, role: Role) -> Set[Permission]:
        """Get all effective permissions (direct + inherited)."""
        return role.get_effective_permissions()
    
    def validate_hierarchy_integrity(self) -> List[Dict[str, Any]]:
        """Validate the integrity of the role hierarchy."""
        issues = []
        
        # Check for circular references
        all_roles = self.db.query(Role).all()
        
        for role in all_roles:
            if self._has_circular_reference(role):
                issues.append({
                    "type": "circular_reference",
                    "role_id": role.id,
                    "role_name": role.name,
                    "message": "Role has circular reference in hierarchy"
                })
        
        # Check hierarchy level consistency
        for role in all_roles:
            expected_level = len(role.get_ancestors())
            if role.hierarchy_level != expected_level:
                issues.append({
                    "type": "inconsistent_level",
                    "role_id": role.id,
                    "role_name": role.name,
                    "expected_level": expected_level,
                    "actual_level": role.hierarchy_level,
                    "message": "Hierarchy level is inconsistent"
                })
        
        # Check for orphaned roles (parent_id points to non-existent role)
        for role in all_roles:
            if role.parent_id:
                parent = self.db.query(Role).filter(Role.id == role.parent_id).first()
                if not parent:
                    issues.append({
                        "type": "orphaned_role",
                        "role_id": role.id,
                        "role_name": role.name,
                        "parent_id": role.parent_id,
                        "message": "Role has non-existent parent"
                    })
        
        return issues
    
    def fix_hierarchy_integrity(self) -> Tuple[bool, str, List[str]]:
        """Attempt to fix hierarchy integrity issues."""
        try:
            fixes_applied = []
            issues = self.validate_hierarchy_integrity()
            
            for issue in issues:
                role = self.db.query(Role).filter(Role.id == issue["role_id"]).first()
                if not role:
                    continue
                
                if issue["type"] == "circular_reference":
                    # Break circular reference by removing parent
                    role.set_parent(None)
                    fixes_applied.append(f"Removed parent from role '{role.name}' to break circular reference")
                
                elif issue["type"] == "inconsistent_level":
                    # Fix hierarchy level
                    role.update_hierarchy_path()
                    fixes_applied.append(f"Fixed hierarchy level for role '{role.name}'")
                
                elif issue["type"] == "orphaned_role":
                    # Remove orphaned parent reference
                    role.parent_id = None
                    role.update_hierarchy_path()
                    fixes_applied.append(f"Removed orphaned parent reference from role '{role.name}'")
            
            self.db.commit()
            return True, f"Applied {len(fixes_applied)} fixes", fixes_applied
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to fix hierarchy integrity: {str(e)}", []
    
    def get_role_permission_inheritance_map(self, role: Role) -> Dict[str, Any]:
        """Get detailed map of permission inheritance for a role."""
        direct_permissions = set(role.permissions)
        inherited_permissions = self.get_inherited_permissions(role)
        
        # Group permissions by source
        inheritance_map = {
            "role_id": role.id,
            "role_name": role.name,
            "direct_permissions": [p.to_dict_safe() for p in direct_permissions],
            "inherited_permissions": [],
            "total_effective_permissions": len(direct_permissions | inherited_permissions)
        }
        
        # Map each inherited permission to its source
        for permission in inherited_permissions:
            sources = []
            for ancestor in role.get_ancestors():
                if permission in ancestor.permissions:
                    sources.append({
                        "role_id": ancestor.id,
                        "role_name": ancestor.name,
                        "hierarchy_level": ancestor.hierarchy_level
                    })
            
            inheritance_map["inherited_permissions"].append({
                "permission": permission.to_dict_safe(),
                "inherited_from": sources
            })
        
        return inheritance_map
    
    def bulk_update_hierarchy(self, hierarchy_updates: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Perform bulk updates to role hierarchy."""
        try:
            for update in hierarchy_updates:
                role_id = update.get("role_id")
                parent_id = update.get("parent_id")
                
                role = self.db.query(Role).filter(Role.id == role_id).first()
                if not role:
                    continue
                
                parent = None
                if parent_id:
                    parent = self.db.query(Role).filter(Role.id == parent_id).first()
                    if not parent:
                        continue
                
                # Validate before applying
                if parent and (role.is_ancestor_of(parent) or role.id == parent.id):
                    continue
                
                role.set_parent(parent)
            
            # Update hierarchy for all affected roles
            all_roles = self.db.query(Role).all()
            for role in all_roles:
                role.update_hierarchy_path()
            
            self.db.commit()
            return True, f"Successfully updated hierarchy for {len(hierarchy_updates)} roles"
            
        except Exception as e:
            self.db.rollback()
            return False, f"Failed to bulk update hierarchy: {str(e)}"
    
    def _has_circular_reference(self, role: Role, visited: Optional[Set[int]] = None) -> bool:
        """Check if a role has circular references in its hierarchy."""
        if visited is None:
            visited = set()
        
        if role.id in visited:
            return True
        
        visited.add(role.id)
        
        if role.parent:
            return self._has_circular_reference(role.parent, visited)
        
        return False
    
    def _update_descendant_hierarchy(self, role: Role) -> None:
        """Update hierarchy path for role and all its descendants."""
        role.update_hierarchy_path()
        
        for child in role.children:
            self._update_descendant_hierarchy(child)
    
    def get_hierarchy_statistics(self) -> Dict[str, Any]:
        """Get statistics about the role hierarchy."""
        all_roles = self.db.query(Role).all()
        active_roles = [r for r in all_roles if r.is_active]
        
        root_roles = [r for r in active_roles if not r.parent_id]
        max_depth = max([r.hierarchy_level for r in active_roles]) if active_roles else 0
        
        # Count roles by level
        level_counts = {}
        for role in active_roles:
            level = role.hierarchy_level
            level_counts[level] = level_counts.get(level, 0) + 1
        
        return {
            "total_roles": len(all_roles),
            "active_roles": len(active_roles),
            "root_roles": len(root_roles),
            "max_hierarchy_depth": max_depth,
            "roles_by_level": level_counts,
            "average_permissions_per_role": sum(len(r.permissions) for r in active_roles) / len(active_roles) if active_roles else 0,
            "roles_with_inheritance": len([r for r in active_roles if r.inherit_permissions and r.parent]),
        }


__all__ = ["RoleHierarchyService"]