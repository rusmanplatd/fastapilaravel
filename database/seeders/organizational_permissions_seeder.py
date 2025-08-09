from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session
from app.Models.Permission import Permission
from app.Models.Role import Role
from config.database import SessionLocal


class OrganizationalPermissionsSeeder:
    """Seeder for organizational permissions and roles."""
    
    def __init__(self):
        self.db: Session = SessionLocal()
    
    def run(self) -> None:
        """Run the organizational permissions seeder."""
        print("Seeding organizational permissions...")
        
        try:
            self._create_organizational_permissions()
            self._create_organizational_roles()
            self._assign_permissions_to_roles()
            
            self.db.commit()
            print("Organizational permissions seeded successfully!")
            
        except Exception as e:
            self.db.rollback()
            print(f"Error seeding organizational permissions: {e}")
            raise
        
        finally:
            self.db.close()
    
    def _create_organizational_permissions(self) -> None:
        """Create organizational permissions."""
        
        organizational_permissions = [
            # Organization permissions
            {
                "name": "View Organizations",
                "slug": "view_organizations",
                "description": "Can view organization information and hierarchy"
            },
            {
                "name": "Create Organizations",
                "slug": "create_organizations",
                "description": "Can create new organizations"
            },
            {
                "name": "Edit Organizations",
                "slug": "edit_organizations",
                "description": "Can edit organization details and settings"
            },
            {
                "name": "Delete Organizations",
                "slug": "delete_organizations",
                "description": "Can delete organizations"
            },
            {
                "name": "Manage Organization Users",
                "slug": "manage_organization_users",
                "description": "Can add/remove users from organizations"
            },
            {
                "name": "View Organization Users",
                "slug": "view_organization_users",
                "description": "Can view users within an organization"
            },
            {
                "name": "View Organization Stats",
                "slug": "view_organization_stats",
                "description": "Can view organization statistics and analytics"
            },
            
            # Department permissions
            {
                "name": "View Departments",
                "slug": "view_departments",
                "description": "Can view department information and hierarchy"
            },
            {
                "name": "Create Departments",
                "slug": "create_departments",
                "description": "Can create new departments"
            },
            {
                "name": "Edit Departments",
                "slug": "edit_departments",
                "description": "Can edit department details and settings"
            },
            {
                "name": "Delete Departments",
                "slug": "delete_departments",
                "description": "Can delete departments"
            },
            {
                "name": "Manage Departments",
                "slug": "manage_departments",
                "description": "Can manage department heads and structure"
            },
            {
                "name": "Manage Department Users",
                "slug": "manage_department_users",
                "description": "Can add/remove users from departments"
            },
            {
                "name": "View Department Users",
                "slug": "view_department_users",
                "description": "Can view users within a department"
            },
            {
                "name": "View Department Stats",
                "slug": "view_department_stats",
                "description": "Can view department statistics and analytics"
            },
            
            # Job Level permissions
            {
                "name": "View Job Levels",
                "slug": "view_job_levels",
                "description": "Can view job levels and career progression"
            },
            {
                "name": "Create Job Levels",
                "slug": "create_job_levels",
                "description": "Can create new job levels"
            },
            {
                "name": "Edit Job Levels",
                "slug": "edit_job_levels",
                "description": "Can edit job level details and requirements"
            },
            {
                "name": "Delete Job Levels",
                "slug": "delete_job_levels",
                "description": "Can delete job levels"
            },
            {
                "name": "View Job Level Stats",
                "slug": "view_job_level_stats",
                "description": "Can view job level statistics and utilization"
            },
            
            # Job Position permissions
            {
                "name": "View Job Positions",
                "slug": "view_job_positions",
                "description": "Can view job positions and openings"
            },
            {
                "name": "Create Job Positions",
                "slug": "create_job_positions",
                "description": "Can create new job positions"
            },
            {
                "name": "Edit Job Positions",
                "slug": "edit_job_positions",
                "description": "Can edit job position details and requirements"
            },
            {
                "name": "Delete Job Positions",
                "slug": "delete_job_positions",
                "description": "Can delete job positions"
            },
            {
                "name": "Manage Position Assignments",
                "slug": "manage_position_assignments",
                "description": "Can assign/remove users from positions"
            },
            {
                "name": "View Position Assignments",
                "slug": "view_position_assignments",
                "description": "Can view position assignments and history"
            },
            {
                "name": "View Position Stats",
                "slug": "view_position_stats",
                "description": "Can view position statistics and utilization"
            },
            {
                "name": "View User Positions",
                "slug": "view_user_positions",
                "description": "Can view a user's position history"
            },
            {
                "name": "View Reporting Structure",
                "slug": "view_reporting_structure",
                "description": "Can view organizational reporting structure"
            },
            
            # Organizational analytics and reporting
            {
                "name": "View Organizational Analytics",
                "slug": "view_organizational_analytics",
                "description": "Can view comprehensive organizational analytics"
            },
            {
                "name": "Export Organizational Data",
                "slug": "export_organizational_data",
                "description": "Can export organizational data and reports"
            },
            {
                "name": "Manage Organizational Settings",
                "slug": "manage_organizational_settings",
                "description": "Can manage global organizational settings"
            }
        ]
        
        for perm_data in organizational_permissions:
            # Check if permission already exists
            existing = self.db.query(Permission).filter(
                Permission.slug == perm_data["slug"]
            ).first()
            
            if not existing:
                permission = Permission(
                    name=perm_data["name"],
                    slug=perm_data["slug"],
                    description=perm_data["description"],
                    guard_name="api"
                )
                self.db.add(permission)
        
        self.db.flush()  # Ensure permissions are created before roles
    
    def _create_organizational_roles(self) -> None:
        """Create organizational roles."""
        
        organizational_roles = [
            {
                "name": "Organization Admin",
                "slug": "organization_admin",
                "description": "Full access to organizational management features",
                "level": 1
            },
            {
                "name": "Organization Manager",
                "slug": "organization_manager", 
                "description": "Manage organizations and departments",
                "level": 2
            },
            {
                "name": "Department Head",
                "slug": "department_head",
                "description": "Manage specific departments and their users",
                "level": 3
            },
            {
                "name": "HR Manager",
                "slug": "hr_manager",
                "description": "Manage job positions, levels, and assignments",
                "level": 3
            },
            {
                "name": "Team Lead",
                "slug": "team_lead",
                "description": "View team structure and manage direct reports",
                "level": 4
            },
            {
                "name": "Employee",
                "slug": "employee",
                "description": "Basic employee access to organizational information",
                "level": 5
            }
        ]
        
        for role_data in organizational_roles:
            # Check if role already exists
            existing = self.db.query(Role).filter(
                Role.slug == role_data["slug"]
            ).first()
            
            if not existing:
                role = Role(
                    name=role_data["name"],
                    slug=role_data["slug"],
                    description=role_data["description"],
                    level=role_data["level"],
                    guard_name="api"
                )
                self.db.add(role)
        
        self.db.flush()
    
    def _assign_permissions_to_roles(self) -> None:
        """Assign permissions to roles."""
        
        # Define role permissions mapping
        role_permissions = {
            "organization_admin": [
                # All organizational permissions
                "view_organizations", "create_organizations", "edit_organizations", "delete_organizations",
                "manage_organization_users", "view_organization_users", "view_organization_stats",
                "view_departments", "create_departments", "edit_departments", "delete_departments",
                "manage_departments", "manage_department_users", "view_department_users", "view_department_stats",
                "view_job_levels", "create_job_levels", "edit_job_levels", "delete_job_levels", "view_job_level_stats",
                "view_job_positions", "create_job_positions", "edit_job_positions", "delete_job_positions",
                "manage_position_assignments", "view_position_assignments", "view_position_stats",
                "view_user_positions", "view_reporting_structure",
                "view_organizational_analytics", "export_organizational_data", "manage_organizational_settings"
            ],
            "organization_manager": [
                # Organization and department management
                "view_organizations", "edit_organizations", "manage_organization_users", "view_organization_users",
                "view_organization_stats", "view_departments", "create_departments", "edit_departments",
                "manage_departments", "manage_department_users", "view_department_users", "view_department_stats",
                "view_job_levels", "view_job_positions", "view_position_assignments", "view_user_positions",
                "view_reporting_structure", "view_organizational_analytics"
            ],
            "department_head": [
                # Department-specific management
                "view_organizations", "view_organization_users", "view_departments", "edit_departments",
                "manage_department_users", "view_department_users", "view_department_stats",
                "view_job_levels", "view_job_positions", "view_position_assignments", "view_user_positions",
                "view_reporting_structure"
            ],
            "hr_manager": [
                # HR-specific permissions
                "view_organizations", "view_organization_users", "view_departments", "view_department_users",
                "view_job_levels", "create_job_levels", "edit_job_levels", "view_job_level_stats",
                "view_job_positions", "create_job_positions", "edit_job_positions",
                "manage_position_assignments", "view_position_assignments", "view_position_stats",
                "view_user_positions", "view_reporting_structure", "view_organizational_analytics"
            ],
            "team_lead": [
                # Team leadership permissions
                "view_organizations", "view_departments", "view_department_users",
                "view_job_levels", "view_job_positions", "view_position_assignments",
                "view_user_positions", "view_reporting_structure"
            ],
            "employee": [
                # Basic employee permissions
                "view_organizations", "view_departments", "view_job_levels", 
                "view_job_positions", "view_reporting_structure"
            ]
        }
        
        for role_slug, permission_slugs in role_permissions.items():
            role = self.db.query(Role).filter(Role.slug == role_slug).first()
            if not role:
                continue
            
            for permission_slug in permission_slugs:
                permission = self.db.query(Permission).filter(
                    Permission.slug == permission_slug
                ).first()
                
                if permission and permission not in role.permissions:
                    role.permissions.append(permission)


def run_seeder():
    """Run the organizational permissions seeder."""
    seeder = OrganizationalPermissionsSeeder()
    seeder.run()


if __name__ == "__main__":
    run_seeder()