"""
Role Permission Seeder
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Dict, List, Any, Optional
from .SeederManager import Seeder

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

class RolePermissionSeeder(Seeder):
    """Seed roles and permissions with hierarchy and metadata"""
    
    def __init__(self):
        super().__init__()
        self.roles_created: Dict[str, Any] = {}
        self.permissions_created: Dict[str, Any] = {}
    
    def run(self, db: Session) -> None:
        """Run the seeder"""
        from app.Models.Role import Role
        from app.Models.Permission import Permission
        from app.Models.User import User
        import logging
        
        logger = logging.getLogger(__name__)
        self.db = db
        
        try:
            logger.info("🌱 Seeding roles and permissions...")
            
            # Seed permissions first
            self.seed_permissions()
            
            # Seed roles with hierarchy
            self.seed_roles()
            
            # Assign permissions to roles
            self.assign_permissions_to_roles()
            
            # Create sample users with roles
            self.create_sample_users()
            
            db.commit()
            logger.info("✅ Role and permission seeding completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error seeding roles and permissions: {str(e)}")
            db.rollback()
            raise
    
    def seed_permissions(self) -> None:
        """Seed permissions with categories, actions, and features."""
        from app.Models.Permission import Permission
        print("  📋 Creating permissions...")
        
        permissions_data = [
            # User Management
            {
                "name": "user.create",
                "category": "user",
                "action": "create",
                "resource_type": "User",
                "description": "Create new users",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "user.read",
                "category": "user",
                "action": "read",
                "resource_type": "User",
                "description": "View user information",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "user.update",
                "category": "user",
                "action": "update",
                "resource_type": "User",
                "description": "Update user information",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "user.delete",
                "category": "user",
                "action": "delete",
                "resource_type": "User",
                "description": "Delete users",
                "is_dangerous": True,
                "requires_mfa": True
            },
            {
                "name": "user.list",
                "category": "user",
                "action": "list",
                "resource_type": "User",
                "description": "List all users",
                "is_dangerous": False,
                "requires_mfa": False
            },
            
            # Admin Permissions
            {
                "name": "admin.dashboard",
                "category": "admin",
                "action": "view",
                "resource_type": "Dashboard",
                "description": "Access admin dashboard",
                "is_dangerous": False,
                "requires_mfa": True
            },
            {
                "name": "admin.settings.manage",
                "category": "admin",
                "action": "manage",
                "resource_type": "Settings",
                "description": "Manage system settings",
                "is_dangerous": True,
                "requires_mfa": True
            },
            {
                "name": "admin.logs.view",
                "category": "admin",
                "action": "view",
                "resource_type": "Logs",
                "description": "View system logs",
                "is_dangerous": False,
                "requires_mfa": False
            },
            
            # RBAC Management
            {
                "name": "rbac.roles.create",
                "category": "security",
                "action": "create",
                "resource_type": "Role",
                "description": "Create roles",
                "is_dangerous": True,
                "requires_mfa": True
            },
            {
                "name": "rbac.roles.view",
                "category": "security",
                "action": "view",
                "resource_type": "Role",
                "description": "View roles",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "rbac.roles.update",
                "category": "security",
                "action": "update",
                "resource_type": "Role",
                "description": "Update roles",
                "is_dangerous": True,
                "requires_mfa": True
            },
            {
                "name": "rbac.roles.delete",
                "category": "security",
                "action": "delete",
                "resource_type": "Role",
                "description": "Delete roles",
                "is_dangerous": True,
                "requires_mfa": True
            },
            {
                "name": "rbac.permissions.create",
                "category": "security",
                "action": "create",
                "resource_type": "Permission",
                "description": "Create permissions",
                "is_dangerous": True,
                "requires_mfa": True
            },
            {
                "name": "rbac.permissions.view",
                "category": "security",
                "action": "view",
                "resource_type": "Permission",
                "description": "View permissions",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "rbac.permissions.update",
                "category": "security",
                "action": "update",
                "resource_type": "Permission",
                "description": "Update permissions",
                "is_dangerous": True,
                "requires_mfa": True
            },
            {
                "name": "rbac.permissions.delete",
                "category": "security",
                "action": "delete",
                "resource_type": "Permission",
                "description": "Delete permissions",
                "is_dangerous": True,
                "requires_mfa": True
            },
            {
                "name": "rbac.hierarchy.view",
                "category": "security",
                "action": "view",
                "resource_type": "Hierarchy",
                "description": "View role hierarchy",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "rbac.hierarchy.manage",
                "category": "security",
                "action": "manage",
                "resource_type": "Hierarchy",
                "description": "Manage role hierarchy",
                "is_dangerous": True,
                "requires_mfa": True
            },
            {
                "name": "rbac.hierarchy.validate",
                "category": "security",
                "action": "validate",
                "resource_type": "Hierarchy",
                "description": "Validate hierarchy integrity",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "rbac.hierarchy.fix",
                "category": "security",
                "action": "fix",
                "resource_type": "Hierarchy",
                "description": "Fix hierarchy issues",
                "is_dangerous": True,
                "requires_mfa": True
            },
            {
                "name": "rbac.cache.view",
                "category": "system",
                "action": "view",
                "resource_type": "Cache",
                "description": "View cache statistics",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "rbac.cache.manage",
                "category": "system",
                "action": "manage",
                "resource_type": "Cache",
                "description": "Manage permission cache",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "rbac.statistics.view",
                "category": "reporting",
                "action": "view",
                "resource_type": "Statistics",
                "description": "View RBAC statistics",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "rbac.emergency.revoke",
                "category": "security",
                "action": "execute",
                "resource_type": "Emergency",
                "description": "Emergency permission revocation",
                "is_dangerous": True,
                "requires_mfa": True,
                "priority": 10
            },
            
            # Wildcard Permissions
            {
                "name": "admin.*",
                "category": "admin",
                "action": "manage",
                "resource_type": "All",
                "description": "All admin permissions",
                "is_dangerous": True,
                "requires_mfa": True,
                "is_wildcard": True,
                "pattern": "admin\\..*",
                "priority": 9
            },
            {
                "name": "user.*",
                "category": "user",
                "action": "manage",
                "resource_type": "User",
                "description": "All user management permissions",
                "is_dangerous": True,
                "requires_mfa": True,
                "is_wildcard": True,
                "pattern": "user\\..*",
                "priority": 8
            },
            {
                "name": "rbac.*",
                "category": "security",
                "action": "manage",
                "resource_type": "RBAC",
                "description": "All RBAC permissions",
                "is_dangerous": True,
                "requires_mfa": True,
                "is_wildcard": True,
                "pattern": "rbac\\..*",
                "priority": 10
            },
            
            # API Permissions
            {
                "name": "api.read",
                "category": "api",
                "action": "read",
                "resource_type": "API",
                "description": "Read access to API",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "api.write",
                "category": "api",
                "action": "write",
                "resource_type": "API",
                "description": "Write access to API",
                "is_dangerous": False,
                "requires_mfa": False
            },
            
            # Content Management
            {
                "name": "content.create",
                "category": "content",
                "action": "create",
                "resource_type": "Content",
                "description": "Create content",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "content.publish",
                "category": "content",
                "action": "publish",
                "resource_type": "Content",
                "description": "Publish content",
                "is_dangerous": False,
                "requires_mfa": False
            },
            {
                "name": "content.delete",
                "category": "content",
                "action": "delete",
                "resource_type": "Content",
                "description": "Delete content",
                "is_dangerous": True,
                "requires_mfa": False
            },
            
            # OAuth2 management (backwards compatibility)
            {"name": "oauth2.clients.view", "description": "View OAuth2 clients", "category": "oauth2", "action": "view", "resource_type": "OAuth2Client"},
            {"name": "oauth2.clients.create", "description": "Create OAuth2 clients", "category": "oauth2", "action": "create", "resource_type": "OAuth2Client"},
            {"name": "oauth2.clients.edit", "description": "Edit OAuth2 clients", "category": "oauth2", "action": "update", "resource_type": "OAuth2Client"},
            {"name": "oauth2.clients.delete", "description": "Delete OAuth2 clients", "category": "oauth2", "action": "delete", "resource_type": "OAuth2Client", "is_dangerous": True},
            
            # MFA management
            {"name": "mfa.manage", "description": "Manage MFA settings", "category": "security", "action": "manage", "resource_type": "MFA"},
            {"name": "mfa.bypass", "description": "Bypass MFA requirements", "category": "security", "action": "bypass", "resource_type": "MFA", "is_dangerous": True, "requires_mfa": True},
        ]
        
        for perm_data in permissions_data:
            slug = perm_data["name"].lower().replace(".", "-").replace("*", "wildcard")
            
            # Check if permission already exists
            existing = self.db.query(Permission).filter(Permission.name == perm_data["name"]).first()
            if existing:
                self.permissions_created[perm_data["name"]] = existing
                continue
            
            permission = Permission(
                name=perm_data["name"],
                slug=slug,
                description=perm_data["description"],
                guard_name=perm_data.get("guard_name", "api"),
                category=perm_data.get("category", "general"),
                action=perm_data.get("action", "execute"),
                resource_type=perm_data.get("resource_type"),
                is_dangerous=perm_data.get("is_dangerous", False),
                requires_mfa=perm_data.get("requires_mfa", False),
                is_wildcard=perm_data.get("is_wildcard", False),
                pattern=perm_data.get("pattern"),
                priority=perm_data.get("priority", 1),
                permission_type="wildcard" if perm_data.get("is_wildcard") else "standard",
                extra_data=json.dumps({"seeded": True, "seeded_at": datetime.now(timezone.utc).isoformat()}),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            self.db.add(permission)
            self.permissions_created[perm_data["name"]] = permission
            
        print(f"  ✅ Created {len(self.permissions_created)} permissions")
    
    def seed_roles(self) -> None:
        """Seed roles with hierarchy."""
        from app.Models.Role import Role
        print("  👥 Creating roles with hierarchy...")
        
        roles_data = [
            # System Roles (Root Level)
            {
                "name": "Super Admin",
                "slug": "super-admin",
                "description": "Ultimate system administrator with all permissions",
                "role_type": "system",
                "priority": 10,
                "is_system": True,
                "is_default": False,
                "conditions": {"min_tenure_days": 90}
            },
            {
                "name": "System Admin",
                "slug": "system-admin",
                "description": "System administrator with high-level permissions",
                "role_type": "system",
                "priority": 9,
                "is_system": True,
                "parent": "Super Admin"
            },
            
            # Management Roles
            {
                "name": "Manager",
                "slug": "manager",
                "description": "Management role with team oversight permissions",
                "role_type": "standard",
                "priority": 8,
                "parent": "System Admin",
                "max_users": 50,
                "conditions": {"departments": ["management", "executive"]}
            },
            {
                "name": "Team Lead",
                "slug": "team-lead",
                "description": "Team leadership role",
                "role_type": "standard",
                "priority": 7,
                "parent": "Manager",
                "max_users": 100
            },
            {
                "name": "Senior Developer",
                "slug": "senior-developer",
                "description": "Senior development role with elevated permissions",
                "role_type": "standard",
                "priority": 6,
                "parent": "Team Lead",
                "conditions": {"min_tenure_days": 365}
            },
            
            # Standard User Roles
            {
                "name": "Developer",
                "slug": "developer",
                "description": "Standard developer role",
                "role_type": "standard",
                "priority": 5,
                "parent": "Senior Developer"
            },
            {
                "name": "User",
                "slug": "user",
                "description": "Basic user role with minimal permissions",
                "role_type": "standard",
                "priority": 1,
                "is_default": True,
                "auto_assign": True
            },
            
            # Specialized Roles
            {
                "name": "Content Manager",
                "slug": "content-manager",
                "description": "Content management role",
                "role_type": "standard",
                "priority": 6,
                "parent": "Manager"
            },
            {
                "name": "Content Editor",
                "slug": "content-editor",
                "description": "Content editing role",
                "role_type": "standard",
                "priority": 4,
                "parent": "Content Manager"
            },
            {
                "name": "API Access",
                "slug": "api-access",
                "description": "API access role for external integrations",
                "role_type": "standard",
                "priority": 3,
                "conditions": {"organizations": ["api-partners", "integrations"]}
            },
            
            # Temporary Roles
            {
                "name": "Guest",
                "slug": "guest",
                "description": "Temporary guest access",
                "role_type": "temporary",
                "priority": 1,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=30)
            },
            {
                "name": "Contractor",
                "slug": "contractor",
                "description": "External contractor access",
                "role_type": "temporary",
                "priority": 3,
                "expires_at": datetime.now(timezone.utc) + timedelta(days=90),
                "max_users": 20
            },
        ]
        
        # Create roles in order (parents first)
        created_roles = {}
        
        for role_data in roles_data:
            # Check if role already exists
            existing = self.db.query(Role).filter(Role.name == role_data["name"]).first()
            if existing:
                self.roles_created[role_data["name"]] = existing
                created_roles[role_data["name"]] = existing
                continue
            
            parent_role = None
            if "parent" in role_data:
                parent_role = created_roles.get(role_data["parent"])
            
            role = Role(
                name=role_data["name"],
                slug=role_data["slug"],
                description=role_data["description"],
                guard_name="api",
                role_type=role_data.get("role_type", "standard"),
                priority=role_data.get("priority", 1),
                is_system=role_data.get("is_system", False),
                is_default=role_data.get("is_default", False),
                auto_assign=role_data.get("auto_assign", False),
                max_users=role_data.get("max_users"),
                expires_at=role_data.get("expires_at"),
                parent=parent_role,
                extra_data=json.dumps({
                    "seeded": True,
                    "seeded_at": datetime.now(timezone.utc).isoformat(),
                    "features": ["hierarchy", "inheritance", "conditions"]
                }),
                conditions=json.dumps(role_data.get("conditions", {})),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Set hierarchy information
            if parent_role:
                role.parent_id = parent_role.id
                role.hierarchy_level = parent_role.hierarchy_level + 1
            else:
                role.hierarchy_level = 0
            
            self.db.add(role)
            self.roles_created[role_data["name"]] = role
            created_roles[role_data["name"]] = role
            
        # Update hierarchy paths
        self.db.flush()  # Ensure IDs are assigned
        
        for role in self.roles_created.values():
            if hasattr(role, 'update_hierarchy_path'):
                role.update_hierarchy_path()
            
        print(f"  ✅ Created {len(self.roles_created)} roles with hierarchy")
    
    def assign_permissions_to_roles(self) -> None:
        """Assign permissions to roles based on hierarchy and function."""
        print("  🔐 Assigning permissions to roles...")
        
        permission_assignments = {
            "Super Admin": [
                "admin.*",  # Wildcard for all admin permissions
                "rbac.*",   # Wildcard for all RBAC permissions
                "user.*",   # Wildcard for all user permissions
                "rbac.emergency.revoke"
            ],
            "System Admin": [
                "admin.dashboard",
                "admin.settings.manage",
                "admin.logs.view",
                "rbac.roles.create",
                "rbac.roles.view",
                "rbac.roles.update",
                "rbac.permissions.view",
                "rbac.hierarchy.view",
                "rbac.hierarchy.manage",
                "rbac.cache.view",
                "rbac.cache.manage",
                "rbac.statistics.view",
                "user.create",
                "user.read",
                "user.update",
                "user.list",
                "oauth2.clients.view",
                "oauth2.clients.create",
                "oauth2.clients.edit",
                "oauth2.clients.delete",
                "mfa.manage"
            ],
            "Manager": [
                "admin.dashboard",
                "user.read",
                "user.list",
                "user.update",
                "rbac.roles.view",
                "rbac.permissions.view",
                "rbac.statistics.view",
                "content.create",
                "content.publish",
                "content.delete"
            ],
            "Team Lead": [
                "user.read",
                "user.list",
                "rbac.roles.view",
                "content.create",
                "content.publish"
            ],
            "Senior Developer": [
                "user.read",
                "api.read",
                "api.write",
                "content.create"
            ],
            "Developer": [
                "user.read",
                "api.read",
                "content.create"
            ],
            "User": [
                "api.read"
            ],
            "Content Manager": [
                "content.create",
                "content.publish",
                "content.delete"
            ],
            "Content Editor": [
                "content.create"
            ],
            "API Access": [
                "api.read",
                "api.write"
            ],
            "Guest": [
                "api.read"
            ],
            "Contractor": [
                "api.read",
                "content.create"
            ]
        }
        
        for role_name, permission_names in permission_assignments.items():
            role = self.roles_created.get(role_name)
            if not role:
                continue
            
            for permission_name in permission_names:
                permission = self.permissions_created.get(permission_name)
                if permission and permission not in role.permissions:
                    role.permissions.append(permission)
        
        print("  ✅ Assigned permissions to roles")
    
    def create_sample_users(self) -> None:
        """Create sample users with different roles for testing."""
        from app.Models.User import User
        print("  👤 Creating sample users...")
        
        sample_users = [
            {
                "name": "Super Admin User",
                "email": "superadmin@example.com",
                "role": "Super Admin"
            },
            {
                "name": "System Admin User",
                "email": "sysadmin@example.com",
                "role": "System Admin"
            },
            {
                "name": "Manager User",
                "email": "manager@example.com",
                "role": "Manager"
            },
            {
                "name": "Developer User",
                "email": "developer@example.com",
                "role": "Developer"
            },
            {
                "name": "Content Manager User",
                "email": "content@example.com",
                "role": "Content Manager"
            }
        ]
        
        from app.Support.Hash.HashManager import HashManager
        hash_manager = HashManager()
        
        created_count = 0
        for user_data in sample_users:
            # Check if user already exists
            existing = self.db.query(User).filter(User.email == user_data["email"]).first()
            if existing:
                continue
            
            user = User(
                name=user_data["name"],
                email=user_data["email"],
                password=hash_manager.make("password123"),
                is_active=True,
                is_verified=True,
                email_verified_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            self.db.add(user)
            self.db.flush()  # Get user ID
            
            # Assign role
            role = self.roles_created.get(user_data["role"])
            if role:
                user.roles.append(role)
            
            created_count += 1
        
        print(f"  ✅ Created {created_count} sample users")