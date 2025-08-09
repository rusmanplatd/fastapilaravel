from __future__ import annotations

from typing import List, Type, Dict, Any, Optional
from abc import ABC, abstractmethod
import logging
from sqlalchemy.orm import Session
from database.seeders.SeederManager import Seeder
from database.seeders.UserSeeder import UserSeeder
from database.seeders.RolePermissionSeeder import RolePermissionSeeder
from database.seeders.PostSeeder import PostSeeder
from database.seeders.OrganizationSeeder import OrganizationSeeder


class DatabaseSeeder(Seeder):
    """
    Laravel-style Database Seeder.
    
    The main seeder class that orchestrates all other seeders.
    This is similar to Laravel's DatabaseSeeder class.
    """
    
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def run(self) -> None:
        """
        Run the database seeders.
        
        This method defines the order in which seeders should run.
        Dependencies should be seeded first.
        """
        self.logger.info("🌱 Starting database seeding...")
        
        # Seed in dependency order
        self.call([
            # Core system data first
            RolePermissionSeeder,
            
            # Users and authentication
            UserSeeder,
            
            # Organizational structure
            OrganizationSeeder,
            
            # Content and posts
            PostSeeder,
        ])
        
        self.logger.info("✅ Database seeding completed successfully!")
    
    def call(self, seeders: List[Type[Seeder]]) -> None:
        """
        Call multiple seeders in order.
        
        @param seeders: List of seeder classes to run
        """
        for seeder_class in seeders:
            self.call_seeder(seeder_class)
    
    def call_seeder(self, seeder_class: Type[Seeder]) -> None:
        """
        Call a specific seeder class.
        
        @param seeder_class: The seeder class to instantiate and run
        """
        try:
            seeder = seeder_class(self.session)
            self.logger.info(f"📦 Seeding {seeder_class.__name__}...")
            
            # Check if we should skip this seeder
            if hasattr(seeder, 'should_run') and not seeder.should_run():
                self.logger.info(f"⏭️  Skipping {seeder_class.__name__} (conditions not met)")
                return
            
            # Run the seeder
            seeder.run()
            
            self.logger.info(f"✅ {seeder_class.__name__} completed")
            
        except Exception as e:
            self.logger.error(f"❌ Error running {seeder_class.__name__}: {str(e)}")
            raise
    
    def call_with_condition(self, seeder_class: Type[Seeder], condition: bool) -> None:
        """
        Call a seeder only if condition is met.
        
        @param seeder_class: The seeder class to run
        @param condition: Whether to run the seeder
        """
        if condition:
            self.call_seeder(seeder_class)
        else:
            self.logger.info(f"⏭️  Skipping {seeder_class.__name__} (condition not met)")
    
    def truncate_tables(self, tables: List[str]) -> None:
        """
        Truncate specified tables before seeding.
        
        @param tables: List of table names to truncate
        """
        self.logger.info(f"🗑️  Truncating tables: {', '.join(tables)}")
        
        for table in tables:
            try:
                self.session.execute(f"DELETE FROM {table}")
                self.session.commit()
                self.logger.debug(f"Truncated table: {table}")
            except Exception as e:
                self.logger.warning(f"Could not truncate table {table}: {str(e)}")
    
    def disable_foreign_key_checks(self) -> None:
        """Disable foreign key checks for faster seeding."""
        try:
            self.session.execute("PRAGMA foreign_keys = OFF")
            self.session.commit()
            self.logger.debug("Disabled foreign key checks")
        except Exception as e:
            self.logger.warning(f"Could not disable foreign key checks: {str(e)}")
    
    def enable_foreign_key_checks(self) -> None:
        """Re-enable foreign key checks after seeding."""
        try:
            self.session.execute("PRAGMA foreign_keys = ON")
            self.session.commit()
            self.logger.debug("Enabled foreign key checks")
        except Exception as e:
            self.logger.warning(f"Could not enable foreign key checks: {str(e)}")
    
    def fresh_seed(self) -> None:
        """
        Fresh seed - truncate all tables and reseed.
        
        This is similar to Laravel's migrate:fresh --seed
        """
        self.logger.info("🔄 Running fresh seed (truncating all data)...")
        
        # Disable foreign key checks
        self.disable_foreign_key_checks()
        
        try:
            # Truncate tables in reverse dependency order
            self.truncate_tables([
                'posts',
                'user_organizations',
                'user_departments', 
                'user_job_positions',
                'user_role',
                'role_permission',
                'oauth_access_tokens',
                'oauth_refresh_tokens',
                'oauth_authorization_codes',
                'notifications',
                'activity_log',
                'users',
                'roles',
                'permissions',
                'organizations',
                'departments',
                'job_levels',
                'job_positions',
                'oauth_clients',
                'oauth_scopes',
            ])
            
            # Run normal seeding
            self.run()
            
        finally:
            # Re-enable foreign key checks
            self.enable_foreign_key_checks()
    
    def seed_for_testing(self) -> None:
        """
        Seed minimal data for testing purposes.
        
        This creates a lightweight dataset suitable for automated tests.
        """
        self.logger.info("🧪 Seeding test data...")
        
        self.call([
            RolePermissionSeeder,
            UserSeeder,  # Will create fewer users in test mode
        ])
    
    def seed_for_demo(self) -> None:
        """
        Seed comprehensive demo data.
        
        This creates a full dataset for demonstration purposes.
        """
        self.logger.info("🎭 Seeding demo data...")
        
        # Set environment flag for demo mode
        import os
        os.environ['SEEDER_MODE'] = 'demo'
        
        try:
            self.run()
        finally:
            # Clean up environment
            if 'SEEDER_MODE' in os.environ:
                del os.environ['SEEDER_MODE']
    
    def get_seeding_environment(self) -> str:
        """Get the current seeding environment."""
        import os
        return os.getenv('SEEDER_MODE', 'normal')
    
    def is_production_environment(self) -> bool:
        """Check if we're in production (be cautious about seeding)."""
        import os
        return os.getenv('APP_ENV', 'production') == 'production'
    
    def confirm_production_seeding(self) -> bool:
        """
        Confirm seeding in production environment.
        
        @return: True if user confirms, False otherwise
        """
        if not self.is_production_environment():
            return True
        
        import sys
        
        print("⚠️  WARNING: You are about to seed the database in PRODUCTION!")
        print("This may overwrite existing data.")
        
        try:
            response = input("Are you sure you want to continue? (yes/no): ").lower()
            return response in ['yes', 'y']
        except (KeyboardInterrupt, EOFError):
            print("\nSeeding cancelled.")
            return False