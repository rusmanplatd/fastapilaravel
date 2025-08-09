#!/usr/bin/env python3
"""
Demo script showcasing the enhanced RBAC features.

This script demonstrates the new role & permission system capabilities
including hierarchy, caching, wildcards, and advanced middleware.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Setup path for imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import get_session
from app.Models import Role, Permission, User
from app.Services.RoleService import RoleService
from app.Services.PermissionService import PermissionService
from app.Services.RoleHierarchyService import RoleHierarchyService
from app.Services.PermissionCacheService import PermissionCacheService
from app.Http.Schemas.PermissionSchemas import RoleCreate, PermissionCreate


class RBACFeaturesDemo:
    """Demonstration of enhanced RBAC features."""
    
    def __init__(self):
        self.db = next(get_session())
        self.role_service = RoleService(self.db)
        self.permission_service = PermissionService(self.db)
        self.hierarchy_service = RoleHierarchyService(self.db)
        self.cache_service = PermissionCacheService(self.db)
    
    def run_all_demos(self) -> None:
        """Run all RBAC feature demonstrations."""
        print("🚀 Starting RBAC Features Demo")
        print("=" * 50)
        
        try:
            self.demo_enhanced_roles()
            print()
            self.demo_enhanced_permissions()
            print()
            self.demo_role_hierarchy()
            print()
            self.demo_permission_caching()
            print()
            self.demo_wildcard_permissions()
            print()
            self.demo_conditional_assignments()
            print()
            self.demo_statistics_and_analytics()
            print()
            
            print("✅ All RBAC feature demos completed successfully!")
            
        except Exception as e:
            print(f"❌ Demo failed: {str(e)}")
            raise
    
    def demo_enhanced_roles(self) -> None:
        """Demonstrate enhanced role features."""
        print("🎭 Enhanced Role Features Demo")
        print("-" * 30)
        
        # Create role with advanced features
        role_data = RoleCreate(
            name="Demo Senior Manager",
            slug="demo-senior-manager",
            description="Demonstration of enhanced role features",
            role_type="standard",
            priority=8,
            max_users=5,
            expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            is_assignable=True,
            requires_approval=True,
            conditions={
                "departments": ["management", "operations"],
                "min_tenure_days": 180
            },
            metadata={
                "demo": True,
                "created_by": "rbac_demo",
                "features": ["expiration", "conditions", "user_limits"]
            }
        )
        
        success, message, role = self.role_service.create_role(role_data)
        
        if success and role:
            print(f"✅ Created enhanced role: {role.name}")
            print(f"   - Type: {role.role_type}")
            print(f"   - Priority: {role.priority}")
            print(f"   - Max Users: {role.max_users}")
            print(f"   - Expires: {role.expires_at}")
            print(f"   - Assignable: {role.is_assignable}")
            print(f"   - Metadata: {role.get_metadata()}")
            
            # Demonstrate role validation
            print(f"   - Is Expired: {role.is_expired()}")
            print(f"   - Can be assigned: {role.can_be_assigned_to_user()}")
            
        else:
            print(f"❌ Failed to create role: {message}")
    
    def demo_enhanced_permissions(self) -> None:
        """Demonstrate enhanced permission features."""
        print("🔐 Enhanced Permission Features Demo")
        print("-" * 30)
        
        # Create permission with advanced features
        perm_data = PermissionCreate(
            name="demo.advanced.manage",
            slug="demo-advanced-manage",
            description="Demonstration of enhanced permission features",
            category="demo",
            action="manage",
            resource_type="DemoResource",
            is_dangerous=True,
            requires_mfa=True,
            priority=9,
            expires_at=datetime.now(timezone.utc) + timedelta(days=60),
            metadata={
                "demo": True,
                "risk_level": "high",
                "audit_required": True
            },
            conditions={
                "time_restrictions": {
                    "allowed_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17]  # Business hours
                }
            },
            restrictions={
                "rate_limit": {
                    "max_uses_per_hour": 10
                }
            }
        )
        
        success, message, permission = self.permission_service.create_permission(perm_data)
        
        if success and permission:
            print(f"✅ Created enhanced permission: {permission.name}")
            print(f"   - Category: {permission.category}")
            print(f"   - Action: {permission.action}")
            print(f"   - Resource: {permission.resource_type}")
            print(f"   - Dangerous: {permission.is_dangerous}")
            print(f"   - Requires MFA: {permission.requires_mfa}")
            print(f"   - Priority: {permission.priority}")
            print(f"   - Expires: {permission.expires_at}")
            print(f"   - Metadata: {permission.get_metadata()}")
            print(f"   - Conditions: {permission.get_conditions()}")
            
            # Demonstrate permission validation
            print(f"   - Is Expired: {permission.is_expired()}")
            
        else:
            print(f"❌ Failed to create permission: {message}")
        
        # Create wildcard permission
        wildcard_perm_data = PermissionCreate(
            name="demo.*",
            slug="demo-wildcard",
            description="Wildcard permission for all demo actions",
            category="demo",
            action="manage",
            is_wildcard=True,
            pattern="demo\\..*",
            is_dangerous=True,
            requires_mfa=True,
            priority=10
        )
        
        success, message, wildcard_perm = self.permission_service.create_permission(wildcard_perm_data)
        
        if success and wildcard_perm:
            print(f"✅ Created wildcard permission: {wildcard_perm.name}")
            print(f"   - Pattern: {wildcard_perm.pattern}")
            print(f"   - Is Wildcard: {wildcard_perm.is_wildcard}")
            
            # Test wildcard matching
            test_permissions = ["demo.test", "demo.advanced.manage", "demo.create", "other.test"]
            for test_perm in test_permissions:
                matches = wildcard_perm.matches_pattern(test_perm)
                print(f"   - '{test_perm}' matches: {matches}")
    
    def demo_role_hierarchy(self) -> None:
        """Demonstrate role hierarchy features."""
        print("🏗️ Role Hierarchy Features Demo")
        print("-" * 30)
        
        # Find existing roles or create simple ones for demo
        try:
            parent_role = self.role_service.get_role_by_name("Manager")
            child_role = self.role_service.get_role_by_name("Team Lead")
            
            if not parent_role or not child_role:
                print("   Creating demo hierarchy roles...")
                
                parent_data = RoleCreate(name="Demo Parent", slug="demo-parent", description="Parent role for hierarchy demo")
                success, _, parent_role = self.role_service.create_role(parent_data)
                
                child_data = RoleCreate(name="Demo Child", slug="demo-child", description="Child role for hierarchy demo")
                success, _, child_role = self.role_service.create_role(child_data)
            
            if parent_role and child_role:
                # Create hierarchy relationship
                success, message = self.hierarchy_service.create_role_hierarchy(parent_role, child_role)
                
                if success:
                    print(f"✅ Created hierarchy: {parent_role.name} -> {child_role.name}")
                    
                    # Demonstrate hierarchy methods
                    hierarchy_path = child_role.get_hierarchy_path()
                    print(f"   - Hierarchy Path: {' -> '.join([r.name for r in hierarchy_path])}")
                    print(f"   - Hierarchy String: {child_role.get_hierarchy_string()}")
                    print(f"   - Hierarchy Level: {child_role.hierarchy_level}")
                    
                    # Show ancestors and descendants
                    ancestors = child_role.get_ancestors()
                    descendants = parent_role.get_descendants()
                    print(f"   - Child ancestors: {[r.name for r in ancestors]}")
                    print(f"   - Parent descendants: {[r.name for r in descendants]}")
                    
                    # Validate hierarchy
                    issues = self.hierarchy_service.validate_hierarchy_integrity()
                    print(f"   - Hierarchy issues found: {len(issues)}")
                    
                    # Get hierarchy statistics
                    stats = self.hierarchy_service.get_hierarchy_statistics()
                    print(f"   - Max hierarchy depth: {stats['max_hierarchy_depth']}")
                    print(f"   - Root roles: {stats['root_roles']}")
                    
                else:
                    print(f"❌ Failed to create hierarchy: {message}")
                    
        except Exception as e:
            print(f"❌ Hierarchy demo failed: {str(e)}")
    
    def demo_permission_caching(self) -> None:
        """Demonstrate permission caching features."""
        print("⚡ Permission Caching Features Demo")
        print("-" * 30)
        
        # Find a user for testing
        user = self.db.query(User).first()
        if not user:
            print("❌ No users found for caching demo")
            return
        
        print(f"Testing cache with user: {user.email}")
        
        # Get cache statistics before
        stats_before = self.cache_service.get_cache_statistics()
        print(f"   - Cache entries before: {stats_before['total_entries']}")
        
        # Warm cache for user
        self.cache_service.warm_cache_for_user(user)
        print("✅ Warmed cache for user")
        
        # Get cached permissions
        cached_data = self.cache_service.get_user_permission_cache(user)
        print(f"   - Cached roles: {len(cached_data['roles'])}")
        print(f"   - Cached permissions: {cached_data['permission_count']}")
        print(f"   - Dangerous permissions: {len(cached_data['dangerous_permissions'])}")
        print(f"   - MFA required permissions: {len(cached_data['mfa_required_permissions'])}")
        
        # Test cached permission check
        if cached_data['all_permissions']:
            test_permission = list(cached_data['all_permissions'])[0]
            has_permission = self.cache_service.check_user_permission_cached(user, test_permission)
            print(f"   - User has '{test_permission}': {has_permission}")
        
        # Get cache statistics after
        stats_after = self.cache_service.get_cache_statistics()
        print(f"   - Cache entries after: {stats_after['total_entries']}")
        print(f"   - Memory usage: {stats_after['memory_usage_mb']} MB")
        
        # Get optimization suggestions
        optimization = self.cache_service.optimize_cache_settings()
        print(f"   - Recommendations: {len(optimization['recommendations'])}")
        for rec in optimization['recommendations']:
            print(f"     * {rec}")
        
        # Clean up expired cache
        expired_count = self.cache_service.cleanup_expired_cache()
        print(f"   - Cleaned up {expired_count} expired entries")
    
    def demo_wildcard_permissions(self) -> None:
        """Demonstrate wildcard permission matching."""
        print("🎯 Wildcard Permission Features Demo")
        print("-" * 30)
        
        test_permissions = [
            "user.create",
            "user.update", 
            "user.delete",
            "admin.settings",
            "admin.logs",
            "demo.test",
            "demo.advanced.manage",
            "other.permission"
        ]
        
        print("Testing wildcard matches:")
        for test_perm in test_permissions:
            matches = self.permission_service.find_wildcard_matches(test_perm)
            if matches:
                print(f"   - '{test_perm}' matches {len(matches)} wildcard(s):")
                for match in matches:
                    print(f"     * {match.name} (pattern: {match.pattern})")
            else:
                print(f"   - '{test_perm}' has no wildcard matches")
    
    def demo_conditional_assignments(self) -> None:
        """Demonstrate conditional role assignments."""
        print("🎯 Conditional Assignment Features Demo")
        print("-" * 30)
        
        # Find or create a test user
        test_user = self.db.query(User).filter(User.email == "developer@example.com").first()
        
        if not test_user:
            print("❌ Test user not found for conditional assignment demo")
            return
        
        # Find role with conditions
        role_with_conditions = None
        for role in self.db.query(Role).all():
            conditions = role.get_conditions()
            if conditions:
                role_with_conditions = role
                break
        
        if role_with_conditions:
            print(f"Testing conditions for role: {role_with_conditions.name}")
            conditions = role_with_conditions.get_conditions()
            print(f"   - Role conditions: {conditions}")
            
            # Test assignment validation
            can_assign = role_with_conditions.can_be_assigned_to_user(test_user)
            print(f"   - Can assign to {test_user.email}: {can_assign}")
            
            meets_conditions = role_with_conditions.check_assignment_conditions(test_user)
            print(f"   - Meets conditions: {meets_conditions}")
            
        else:
            print("   - No roles with conditions found")
    
    def demo_statistics_and_analytics(self) -> None:
        """Demonstrate statistics and analytics features."""
        print("📊 Statistics & Analytics Features Demo")
        print("-" * 30)
        
        # Role statistics
        role_stats = self.role_service.get_role_statistics()
        print("Role Statistics:")
        print(f"   - Total roles: {role_stats['total_roles']}")
        print(f"   - Active roles: {role_stats['active_roles']}")
        print(f"   - Inactive roles: {role_stats['inactive_roles']}")
        
        # Permission statistics
        perm_stats = self.permission_service.get_permission_statistics()
        print("Permission Statistics:")
        print(f"   - Total permissions: {perm_stats['total_permissions']}")
        print(f"   - Active permissions: {perm_stats['active_permissions']}")
        print(f"   - Dangerous permissions: {perm_stats['dangerous_permissions']}")
        print(f"   - MFA required permissions: {perm_stats['mfa_required_permissions']}")
        print(f"   - Wildcard permissions: {perm_stats['wildcard_permissions']}")
        print(f"   - Category distribution: {perm_stats['category_distribution']}")
        
        # Hierarchy statistics
        hierarchy_stats = self.hierarchy_service.get_hierarchy_statistics()
        print("Hierarchy Statistics:")
        print(f"   - Max depth: {hierarchy_stats['max_hierarchy_depth']}")
        print(f"   - Root roles: {hierarchy_stats['root_roles']}")
        print(f"   - Roles with inheritance: {hierarchy_stats['roles_with_inheritance']}")
        
        # Cache statistics
        cache_stats = self.cache_service.get_cache_statistics()
        print("Cache Statistics:")
        print(f"   - Total entries: {cache_stats['total_entries']}")
        print(f"   - Memory usage: {cache_stats['memory_usage_mb']} MB")
        print(f"   - Hit ratio: {cache_stats['cache_hit_ratio']:.2%}")


def main():
    """Main function to run the RBAC features demo."""
    demo = RBACFeaturesDemo()
    demo.run_all_demos()


if __name__ == "__main__":
    main()


__all__ = ["RBACFeaturesDemo", "main"]