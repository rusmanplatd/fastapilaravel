from __future__ import annotations

from typing import List, Type, Dict, Any, Optional, final
import logging
import time
from sqlalchemy.orm import Session
from database.seeders.SeederManager import Seeder, SeederResult, SeederMetadata
from database.seeders.UserSeeder import UserSeeder
from database.seeders.RolePermissionSeeder import RolePermissionSeeder
from database.seeders.PostSeeder import PostSeeder
from database.seeders.OrganizationSeeder import OrganizationSeeder
from database.seeders.SettingsSeeder import SettingsSeeder
from database.seeders.EventSeeder import EventSeeder
from database.seeders.AnalyticsSeeder import AnalyticsSeeder
from database.seeders.DepartmentSeeder import DepartmentSeeder
from database.seeders.JobLevelSeeder import JobLevelSeeder
from database.seeders.JobPositionSeeder import JobPositionSeeder
from database.seeders.NotificationSeeder import NotificationSeeder


@final
class DatabaseSeeder(Seeder):
    """
    Laravel 12-style Database Seeder with enhanced orchestration and dependency management.
    
    The main seeder class that orchestrates all other seeders with proper
    dependency resolution and error handling.
    """
    
    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set metadata for this seeder
        self.set_metadata(SeederMetadata(
            name="DatabaseSeeder",
            description="Main database seeder that orchestrates all other seeders",
            dependencies=[],
            priority=1000,  # Highest priority
            environments=['development', 'testing', 'staging', 'production']
        ))
    
    def run(self) -> SeederResult:
        """
        Run the database seeders with enhanced error handling and timing.
        
        This method defines the order in which seeders should run.
        Dependencies should be seeded first.
        """
        start_time = time.time()
        total_records = 0
        
        try:
            self.logger.info("🌱 Starting Laravel 12 database seeding...")
            
            # Optionally disable foreign key checks for performance
            if self.options.get('disable_foreign_keys', False):
                self.disable_foreign_key_checks()
            
            # Seed in strict dependency order with validation
            seeder_results = self.call([
                # Core system data first (highest priority)
                RolePermissionSeeder,
                
                # Application settings (foundational)
                SettingsSeeder,
                
                # Job hierarchy (foundational for HR)
                JobLevelSeeder,
                
                # Users and authentication (depends on roles/permissions)
                UserSeeder,
                
                # Organizational structure (depends on users)
                OrganizationSeeder,
                
                # Departments within organizations (depends on organizations)
                DepartmentSeeder,
                
                # Job positions (depends on departments and job levels)
                JobPositionSeeder,
                
                # Content and posts (depends on users and organizations)
                PostSeeder,
                
                # Events and calendar (depends on users and organizations)
                EventSeeder,
                
                # User notifications (depends on users)
                NotificationSeeder,
                
                # Analytics data (depends on users, events)
                AnalyticsSeeder,
            ])
            
            # Calculate totals
            for result in seeder_results:
                if result['success']:
                    total_records += result['records_created']
            
            execution_time = time.time() - start_time
            
            self.logger.info(f"✅ Database seeding completed successfully! "
                           f"({total_records} total records in {execution_time:.2f}s)")
            
            return {
                'name': 'DatabaseSeeder',
                'success': True,
                'records_created': total_records,
                'execution_time': execution_time,
                'error': None
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Database seeding failed: {e}")
            
            return {
                'name': 'DatabaseSeeder',
                'success': False,
                'records_created': total_records,
                'execution_time': execution_time,
                'error': str(e)
            }
            
        finally:
            # Re-enable foreign key checks if they were disabled
            if self.options.get('disable_foreign_keys', False):
                self.enable_foreign_key_checks()
    
    def call(self, seeders: List[Type[Seeder]]) -> List[SeederResult]:
        """
        Call multiple seeders in order with enhanced dependency validation.
        
        @param seeders: List of seeder classes to run in dependency order
        @return: List of seeder execution results
        """
        results: List[SeederResult] = []
        
        for seeder_class in seeders:
            result = self.call_seeder(seeder_class)
            results.append(result)
            
            # Stop on first failure unless force flag is set
            if not result['success'] and not self.options.get('force', False):
                self.logger.error(f"Stopping seeding due to failure in {seeder_class.__name__}")
                break
        
        return results
    
    def call_seeder(self, seeder_class: Type[Seeder]) -> SeederResult:
        """
        Call a specific seeder class with enhanced validation and timing.
        
        @param seeder_class: The seeder class to instantiate and run
        @return: Seeder execution result
        """
        start_time = time.time()
        
        try:
            seeder = seeder_class(self.session, self.options)
            
            # Validate seeder before running
            if not hasattr(seeder, 'run'):
                raise ValueError(f"Seeder {seeder_class.__name__} does not implement run() method")
            
            self.logger.info(f"📦 Seeding {seeder_class.__name__}...")
            
            # Check if we should skip this seeder
            if not seeder.should_run():
                self.logger.info(f"⏭️  Skipping {seeder_class.__name__} (conditions not met)")
                return {
                    'name': seeder_class.__name__,
                    'success': True,
                    'records_created': 0,
                    'execution_time': time.time() - start_time,
                    'error': None
                }
            
            # Run the seeder with transaction support
            with seeder.transaction():
                result = seeder.run()
            
            self.logger.info(f"✅ {seeder_class.__name__} completed "
                           f"({result['records_created']} records in {result['execution_time']:.2f}s)")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Error running {seeder_class.__name__}: {str(e)}")
            
            return {
                'name': seeder_class.__name__,
                'success': False,
                'records_created': 0,
                'execution_time': execution_time,
                'error': str(e)
            }
    
    def call_with_condition(self, seeder_class: Type[Seeder], condition: bool) -> SeederResult:
        """
        Call a seeder only if condition is met.
        
        @param seeder_class: The seeder class to run
        @param condition: Whether to run the seeder
        @return: Seeder execution result
        """
        if not isinstance(condition, bool):
            raise ValueError(f"Condition must be a boolean, got {type(condition)}")
        
        if condition:
            return self.call_seeder(seeder_class)
        else:
            self.logger.info(f"⏭️  Skipping {seeder_class.__name__} (condition not met)")
            return {
                'name': seeder_class.__name__,
                'success': True,
                'records_created': 0,
                'execution_time': 0.0,
                'error': None
            }
    
    def truncate_tables(self, tables: List[str]) -> None:
        """
        Truncate specified tables before seeding with enhanced validation.
        
        @param tables: List of table names to truncate
        """
        if not tables or not all(isinstance(table, str) for table in tables):
            raise ValueError(f"Invalid tables list: {tables}")
        
        self.logger.info(f"🗑️  Truncating {len(tables)} tables: {', '.join(tables)}")
        
        for table in tables:
            try:
                self.truncate_table(table)
            except Exception as e:
                self.logger.warning(f"Could not truncate table {table}: {str(e)}")
                if not self.options.get('force', False):
                    raise
    
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
    
    def fresh_seed(self) -> SeederResult:
        """
        Fresh seed - truncate all tables and reseed with enhanced error handling.
        
        This is similar to Laravel's migrate:fresh --seed
        """
        start_time = time.time()
        
        try:
            self.logger.info("🔄 Running fresh seed (truncating all data)...")
            
            # Disable foreign key checks
            self.disable_foreign_key_checks()
            
            # Truncate tables in reverse dependency order
            self.truncate_tables([
                'analytics',
                'notifications',
                'events',
                'posts',
                'user_job_positions',
                'job_positions',
                'user_departments',
                'departments',
                'user_organizations',
                'organizations',
                'users',
                'user_role',
                'role_permission',
                'roles',
                'permissions',
                'job_levels',
                'settings',
                'oauth_access_tokens',
                'oauth_refresh_tokens',
                'oauth_authorization_codes',
                'oauth_clients',
                'oauth_scopes',
                'activity_log',
            ])
            
            # Run normal seeding
            result = self.run()
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ Fresh seed failed: {e}")
            
            return {
                'name': 'DatabaseSeeder.fresh_seed',
                'success': False,
                'records_created': 0,
                'execution_time': execution_time,
                'error': str(e)
            }
            
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