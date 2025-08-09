from __future__ import annotations

"""
Master seeder for all organizational data.
Run this to seed the complete organizational structure with permissions, roles, and sample data.
"""

from organizational_permissions_seeder import OrganizationalPermissionsSeeder
from organizational_data_seeder import OrganizationalDataSeeder


def run_all_organizational_seeders() -> None:
    """Run all organizational seeders in the correct order."""
    
    print("=" * 60)
    print("RUNNING COMPLETE ORGANIZATIONAL SEEDING")
    print("=" * 60)
    
    try:
        # Step 1: Seed permissions and roles
        print("\n1. Seeding organizational permissions and roles...")
        permissions_seeder = OrganizationalPermissionsSeeder()
        permissions_seeder.run()
        print("✓ Permissions and roles seeded successfully")
        
        # Step 2: Seed organizational data
        print("\n2. Seeding organizational structure and sample data...")
        data_seeder = OrganizationalDataSeeder()
        data_seeder.run()
        print("✓ Organizational data seeded successfully")
        
        print("\n" + "=" * 60)
        print("ORGANIZATIONAL SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        print("\nWhat was seeded:")
        print("📋 Permissions: 30+ organizational permissions")
        print("👥 Roles: 6 organizational roles (Org Admin → Employee)")
        print("🏢 Organizations: 6 organizations with hierarchy")
        print("🏬 Departments: 10 departments with sub-departments")
        print("📊 Job Levels: 13 job levels (Intern → CEO)")
        print("💼 Job Positions: 12+ positions with reporting structure")
        print("👤 Sample Users: 10 users with complete assignments")
        print("🔗 Relationships: All organizational relationships connected")
        
        print("\nSample credentials (password: password123):")
        print("• john.smith@techcorp.com (Director of Engineering)")
        print("• sarah.johnson@techcorp.com (Engineering Manager)")
        print("• mike.davis@techcorp.com (Frontend Team Lead)")
        print("• emily.chen@techcorp.com (Senior Software Engineer)")
        
        print("\nNext steps:")
        print("1. Start the development server: make dev")
        print("2. Test organizational APIs at /api/v1/organizations")
        print("3. View the organizational directory and hierarchy")
        print("4. Test role-based permissions for different user types")
        
    except Exception as e:
        print(f"\n❌ Error during organizational seeding: {e}")
        print("Please check the error details and try again.")
        raise


if __name__ == "__main__":
    run_all_organizational_seeders()