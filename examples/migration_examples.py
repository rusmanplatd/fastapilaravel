#!/usr/bin/env python3
"""
Examples demonstrating the enhanced Laravel-style migration system.

This script shows how to use the new migration features.
"""

from __future__ import annotations

from database.Schema.MigrationManager import MigrationManager
from database.Schema.MigrationDependency import DependencyResolver
from database.Schema.MigrationSquasher import MigrationSquasher
from database.seeders.SeederManager import SeederManager


def main() -> None:
    """Demonstrate migration capabilities."""
    print("🚀 FastAPI Laravel Migration System Demo")
    print("=" * 50)
    
    # Initialize managers
    migration_manager = MigrationManager()
    dependency_resolver = DependencyResolver()
    squasher = MigrationSquasher()
    seeder_manager = SeederManager()
    
    # Show available migrations
    print("\n📁 Available Migration Files:")
    migrations = migration_manager.get_migration_files()
    for migration in migrations[:5]:  # Show first 5
        print(f"  • {migration}")
    if len(migrations) > 5:
        print(f"  ... and {len(migrations) - 5} more")
    
    # Show migration status
    print("\n📊 Migration Status:")
    migration_manager.status()
    
    # Analyze dependencies
    print("\n🔍 Dependency Analysis:")
    try:
        graph = dependency_resolver.build_dependency_graph(migrations[:10])
        execution_order = graph.get_execution_order()
        print(f"✅ {len(execution_order)} migrations in correct dependency order")
        
        errors = graph.validate_dependencies()
        if errors:
            print("❌ Dependency errors found:")
            for error in errors:
                print(f"  • {error}")
        else:
            print("✅ All dependencies are valid")
    except Exception as e:
        print(f"❌ Error analyzing dependencies: {e}")
    
    # Show squash candidates
    print("\n🔧 Optimization Opportunities:")
    try:
        candidates = squasher.get_squash_candidates()
        if candidates:
            for from_migration, to_migration, count in candidates[:3]:
                print(f"  • Squash {count} migrations: {from_migration} → {to_migration}")
        else:
            print("  ✅ No obvious squashing opportunities found")
    except Exception as e:
        print(f"❌ Error finding squash candidates: {e}")
    
    # Show available seeders
    print("\n🌱 Available Seeders:")
    try:
        seeders = seeder_manager.get_seeder_files()
        for seeder in seeders:
            print(f"  • {seeder}")
        
        if not seeders:
            print("  📝 No seeders found - run 'python migrate.py make:seeder ExampleSeeder' to create one")
    except Exception as e:
        print(f"❌ Error listing seeders: {e}")
    
    print("\n" + "=" * 50)
    print("💡 Try these commands:")
    print("  python migrate.py migrate:status")
    print("  python migrate.py migrate:analyze")
    print("  python migrate.py migrate:optimize")
    print("  python migrate.py make:migration create_posts_table --create posts")
    print("  python migrate.py make:seeder PostSeeder --model Post")
    print("  python migrate.py migrate --help")


if __name__ == "__main__":
    main()