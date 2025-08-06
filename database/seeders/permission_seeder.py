from sqlalchemy.orm import Session
from database.migrations.create_permissions_table import Permission
from database.migrations.create_roles_table import Role
from database.migrations.create_users_table import User
from config.database import SessionLocal


def seed_permissions():
    db: Session = SessionLocal()
    
    try:
        # Check if permissions already exist
        if db.query(Permission).first():
            print("Permissions already seeded")
            return
        
        # Default permissions similar to Spatie Laravel Permission
        default_permissions = [
            # User management
            {"name": "View Users", "slug": "view-users", "description": "Can view users list and profiles"},
            {"name": "Create Users", "slug": "create-users", "description": "Can create new users"},
            {"name": "Edit Users", "slug": "edit-users", "description": "Can edit user information"},
            {"name": "Delete Users", "slug": "delete-users", "description": "Can delete users"},
            
            # Role management
            {"name": "View Roles", "slug": "view-roles", "description": "Can view roles list"},
            {"name": "Create Roles", "slug": "create-roles", "description": "Can create new roles"},
            {"name": "Edit Roles", "slug": "edit-roles", "description": "Can edit roles"},
            {"name": "Delete Roles", "slug": "delete-roles", "description": "Can delete roles"},
            {"name": "Assign Roles", "slug": "assign-roles", "description": "Can assign roles to users"},
            
            # Permission management
            {"name": "View Permissions", "slug": "view-permissions", "description": "Can view permissions list"},
            {"name": "Create Permissions", "slug": "create-permissions", "description": "Can create new permissions"},
            {"name": "Edit Permissions", "slug": "edit-permissions", "description": "Can edit permissions"},
            {"name": "Delete Permissions", "slug": "delete-permissions", "description": "Can delete permissions"},
            {"name": "Assign Permissions", "slug": "assign-permissions", "description": "Can assign permissions to users/roles"},
            
            # Content management (example)
            {"name": "View Posts", "slug": "view-posts", "description": "Can view posts"},
            {"name": "Create Posts", "slug": "create-posts", "description": "Can create new posts"},
            {"name": "Edit Posts", "slug": "edit-posts", "description": "Can edit posts"},
            {"name": "Delete Posts", "slug": "delete-posts", "description": "Can delete posts"},
            {"name": "Publish Posts", "slug": "publish-posts", "description": "Can publish/unpublish posts"},
            
            # System management
            {"name": "View Dashboard", "slug": "view-dashboard", "description": "Can access admin dashboard"},
            {"name": "View Settings", "slug": "view-settings", "description": "Can view system settings"},
            {"name": "Edit Settings", "slug": "edit-settings", "description": "Can edit system settings"},
            {"name": "View Reports", "slug": "view-reports", "description": "Can view system reports"},
            {"name": "Export Data", "slug": "export-data", "description": "Can export data"},
            
            # File management
            {"name": "Upload Files", "slug": "upload-files", "description": "Can upload files"},
            {"name": "Delete Files", "slug": "delete-files", "description": "Can delete files"},
            {"name": "Manage Media", "slug": "manage-media", "description": "Can manage media library"},
        ]
        
        permissions = []
        for perm_data in default_permissions:
            permission = Permission(
                name=perm_data["name"],
                slug=perm_data["slug"],
                description=perm_data["description"],
                guard_name="api",
                is_active=True
            )
            db.add(permission)
            permissions.append(permission)
        
        db.commit()
        print(f"Created {len(permissions)} default permissions")
        
    except Exception as e:
        print(f"Error seeding permissions: {e}")
        db.rollback()
    finally:
        db.close()


def seed_roles():
    db: Session = SessionLocal()
    
    try:
        # Check if roles already exist
        if db.query(Role).first():
            print("Roles already seeded")
            return
        
        # Default roles
        default_roles = [
            {
                "name": "Super Admin",
                "slug": "super-admin",
                "description": "Has all permissions",
                "is_default": False,
                "permissions": "all"  # Special case for all permissions
            },
            {
                "name": "Admin",
                "slug": "admin",
                "description": "Administrative access with most permissions",
                "is_default": False,
                "permissions": [
                    "view-users", "create-users", "edit-users",
                    "view-roles", "create-roles", "edit-roles", "assign-roles",
                    "view-permissions", "assign-permissions",
                    "view-posts", "create-posts", "edit-posts", "delete-posts", "publish-posts",
                    "view-dashboard", "view-settings", "edit-settings", "view-reports",
                    "upload-files", "delete-files", "manage-media"
                ]
            },
            {
                "name": "Editor",
                "slug": "editor",
                "description": "Can manage content",
                "is_default": False,
                "permissions": [
                    "view-posts", "create-posts", "edit-posts", "publish-posts",
                    "view-dashboard", "upload-files", "manage-media"
                ]
            },
            {
                "name": "Author",
                "slug": "author",
                "description": "Can create and edit own content",
                "is_default": False,
                "permissions": [
                    "view-posts", "create-posts", "edit-posts",
                    "view-dashboard", "upload-files"
                ]
            },
            {
                "name": "User",
                "slug": "user",
                "description": "Basic user access",
                "is_default": True,
                "permissions": [
                    "view-posts", "view-dashboard"
                ]
            }
        ]
        
        # Get all permissions for reference
        all_permissions = db.query(Permission).all()
        permissions_by_slug = {perm.slug: perm for perm in all_permissions}
        
        for role_data in default_roles:
            role = Role(
                name=role_data["name"],
                slug=role_data["slug"],
                description=role_data["description"],
                guard_name="api",
                is_active=True,
                is_default=role_data["is_default"]
            )
            
            db.add(role)
            db.flush()  # Get the role ID
            
            # Assign permissions to role
            if role_data["permissions"] == "all":
                # Super Admin gets all permissions
                for permission in all_permissions:
                    role.give_permission_to(permission)
            else:
                # Assign specific permissions
                for perm_slug in role_data["permissions"]:
                    if perm_slug in permissions_by_slug:
                        role.give_permission_to(permissions_by_slug[perm_slug])
        
        db.commit()
        print(f"Created {len(default_roles)} default roles with permissions")
        
    except Exception as e:
        print(f"Error seeding roles: {e}")
        db.rollback()
    finally:
        db.close()


def assign_super_admin_role():
    """Assign Super Admin role to the first user (if exists)"""
    db: Session = SessionLocal()
    
    try:
        # Get first user (usually the admin)
        first_user = db.query(User).first()
        if not first_user:
            print("No users found to assign Super Admin role")
            return
        
        # Get Super Admin role
        super_admin_role = db.query(Role).filter(Role.slug == "super-admin").first()
        if not super_admin_role:
            print("Super Admin role not found")
            return
        
        # Check if user already has the role
        if super_admin_role in first_user.roles:
            print("User already has Super Admin role")
            return
        
        # Assign Super Admin role
        first_user.assign_role(super_admin_role)
        db.commit()
        
        print(f"Assigned Super Admin role to user: {first_user.email}")
        
    except Exception as e:
        print(f"Error assigning Super Admin role: {e}")
        db.rollback()
    finally:
        db.close()


def seed_all_permissions():
    """Seed all permissions and roles"""
    print("Starting permission and role seeding...")
    seed_permissions()
    seed_roles()
    assign_super_admin_role()
    print("Permission and role seeding completed!")


if __name__ == "__main__":
    seed_all_permissions()