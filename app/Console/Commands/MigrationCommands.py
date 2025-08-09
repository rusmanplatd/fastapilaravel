from __future__ import annotations

import argparse
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from app.Console.Command import Command
from database.Schema.MigrationManager import MigrationManager


class MigrateCommand(Command):
    """Laravel-style migrate command."""
    
    signature = "migrate {--force : Force migrations in production} {--dry-run : Show migrations that would be executed} {--backup : Create database backup before migration}"
    description = "Run database migrations"
    
    async def handle(self) -> None:
        """Handle migrate command."""
        force = self.option("force", False)
        dry_run = self.option("dry-run", False)
        backup = self.option("backup", False)
        
        # Check for production environment
        import os
        is_production = os.getenv('APP_ENV', 'development') == 'production'
        
        if is_production and not force:
            self.error("⚠️  Running migrations in PRODUCTION environment!")
            if not self.confirm("This may cause data loss. Continue?", False):
                self.info("Migration cancelled for safety.")
                return
        
        manager = MigrationManager()
        
        # Validate migrations before executing
        if not await self._validate_migrations(manager):
            self.error("Migration validation failed. Aborting.")
            return
        
        # Show what would be migrated
        pending = manager.get_pending_migrations()
        if not pending:
            self.info("Nothing to migrate.")
            return
        
        self.info(f"Found {len(pending)} pending migrations:")
        for migration in pending:
            self.line(f"  • {migration}")
        
        if dry_run:
            self.info("✅ Dry run completed. No migrations were executed.")
            return
        
        # Create backup if requested
        if backup or (is_production and self.confirm("Create backup before migration?", True)):
            self.info("Creating database backup...")
            try:
                await self.call("db:backup")
                self.info("✅ Backup created successfully.")
            except Exception as e:
                self.error(f"Failed to create backup: {e}")
                if not self.confirm("Continue without backup?", False):
                    return
        
        self.info("Running migrations...")
        try:
            executed = manager.migrate()
            
            if executed:
                self.info(f"✅ Migrated {len(executed)} migrations successfully.")
                
                # Show migration summary
                self.new_line()
                self.comment("Migration Summary:")
                for migration in executed:
                    self.line(f"  ✓ {migration}")
            else:
                self.info("Nothing to migrate.")
                
        except Exception as e:
            self.error(f"Migration failed: {e}")
            self.warn("Database may be in an inconsistent state.")
            if backup:
                self.comment("Consider restoring from the backup created earlier.")
            raise
    
    async def _validate_migrations(self, manager: MigrationManager) -> bool:
        """Validate pending migrations for safety."""
        try:
            pending = manager.get_pending_migrations()
            
            # Check for dangerous operations
            dangerous_operations = []
            for migration_file in pending:
                content = self._read_migration_file(migration_file)
                if self._has_dangerous_operations(content):
                    dangerous_operations.append(migration_file)
            
            if dangerous_operations:
                self.warn("⚠️  Potentially destructive migrations detected:")
                for migration in dangerous_operations:
                    self.line(f"  • {migration}")
                
                if not self.confirm("These migrations may cause data loss. Continue?", False):
                    return False
            
            # Validate migration dependencies
            if not self._validate_dependencies(pending):
                return False
            
            return True
            
        except Exception as e:
            self.error(f"Migration validation error: {e}")
            return False
    
    def _read_migration_file(self, migration_file: str) -> str:
        """Read migration file content."""
        try:
            migration_path = Path(f"database/migrations/{migration_file}")
            return migration_path.read_text()
        except Exception:
            return ""
    
    def _has_dangerous_operations(self, content: str) -> bool:
        """Check if migration contains potentially dangerous operations."""
        dangerous_keywords = [
            'drop_table', 'drop_column', 'drop_index',
            'DROP TABLE', 'DROP COLUMN', 'DROP INDEX',
            'truncate', 'TRUNCATE', 'delete', 'DELETE'
        ]
        
        return any(keyword in content for keyword in dangerous_keywords)
    
    def _validate_dependencies(self, pending_migrations: List[str]) -> bool:
        """Validate migration dependencies."""
        # This would check for foreign key dependencies, etc.
        # For now, just ensure migrations are in chronological order
        sorted_migrations = sorted(pending_migrations)
        if sorted_migrations != pending_migrations:
            self.warn("Migrations are not in chronological order.")
            return self.confirm("Continue anyway?", False)
        
        return True


class MigrateRollbackCommand(Command):
    """Laravel-style migrate:rollback command."""
    
    signature = "migrate:rollback {--step=1 : Number of batch steps to rollback} {--force : Skip confirmation} {--dry-run : Show what would be rolled back} {--backup : Create backup before rollback}"
    description = "Rollback database migrations"
    
    async def handle(self) -> None:
        """Handle rollback command."""
        steps = int(self.option("step", 1))
        force = self.option("force", False)
        dry_run = self.option("dry-run", False)
        backup = self.option("backup", False)
        
        manager = MigrationManager()
        
        # Get migrations that would be rolled back
        migrations_to_rollback = manager.get_rollback_migrations(steps)
        
        if not migrations_to_rollback:
            self.info("Nothing to rollback.")
            return
        
        # Show what will be rolled back
        self.warn("⚠️  The following migrations will be rolled back:")
        for migration in migrations_to_rollback:
            self.line(f"  • {migration}")
        
        if dry_run:
            self.info("✅ Dry run completed. No migrations were rolled back.")
            return
        
        # Safety checks
        if not force:
            # Check for data loss potential
            if await self._has_data_loss_potential(migrations_to_rollback):
                self.error("⚠️  DANGER: These rollbacks may cause irreversible data loss!")
                self.warn("Data in dropped columns/tables will be permanently lost.")
                
                confirmation = self.ask("Type 'I UNDERSTAND THE RISK' to continue:", "")
                if confirmation != "I UNDERSTAND THE RISK":
                    self.info("Rollback cancelled for safety.")
                    return
            else:
                if not self.confirm(f"Rollback {len(migrations_to_rollback)} migrations?", False):
                    self.info("Rollback cancelled.")
                    return
        
        # Create backup if requested
        if backup or self.confirm("Create backup before rollback?", True):
            self.info("Creating database backup...")
            try:
                await self.call("db:backup")
                self.info("✅ Backup created successfully.")
            except Exception as e:
                self.error(f"Failed to create backup: {e}")
                if not self.confirm("Continue without backup?", False):
                    return
        
        # Perform rollback
        self.info(f"Rolling back {steps} batch(es)...")
        try:
            rolled_back = manager.rollback(steps)
            
            if rolled_back:
                self.info(f"✅ Rolled back {len(rolled_back)} migrations successfully.")
                
                # Show rollback summary
                self.new_line()
                self.comment("Rollback Summary:")
                for migration in rolled_back:
                    self.line(f"  ✓ {migration}")
                    
                self.new_line()
                self.comment("Database schema has been reverted.")
            else:
                self.info("Nothing was rolled back.")
                
        except Exception as e:
            self.error(f"Rollback failed: {e}")
            self.warn("Database may be in an inconsistent state.")
            self.comment("Consider restoring from backup if available.")
            raise
    
    async def _has_data_loss_potential(self, migrations: List[str]) -> bool:
        """Check if rollback migrations have data loss potential."""
        for migration_file in migrations:
            try:
                migration_path = Path(f"database/migrations/{migration_file}")
                if migration_path.exists():
                    content = migration_path.read_text()
                    
                    # Check down() method for destructive operations
                    if self._has_destructive_rollback(content):
                        return True
            except Exception:
                continue
        
        return False
    
    def _has_destructive_rollback(self, content: str) -> bool:
        """Check if migration rollback contains destructive operations."""
        # Look for destructive operations in down() method
        destructive_patterns = [
            'drop_table', 'drop_column', 'DROP TABLE', 'DROP COLUMN',
            'Schema.drop', 'table.drop_column'
        ]
        
        # Find down() method content
        lines = content.split('\n')
        in_down_method = False
        down_content = []
        
        for line in lines:
            if 'def down(' in line:
                in_down_method = True
                continue
            elif in_down_method and line.strip().startswith('def '):
                break
            elif in_down_method:
                down_content.append(line)
        
        down_code = '\n'.join(down_content)
        return any(pattern in down_code for pattern in destructive_patterns)


class MigrateResetCommand(Command):
    """Laravel-style migrate:reset command."""
    
    signature = "migrate:reset"
    description = "Rollback all database migrations"
    
    def handle(self) -> int:
        """Handle reset command."""
        manager = get_migration_manager()
        
        try:
            manager.reset()
            return 0
        except Exception as e:
            self.error(f"Reset failed: {e}")
            return 1


class MigrateFreshCommand(Command):
    """Laravel-style migrate:fresh command."""
    
    signature = "migrate:fresh {--seed : Run seeders after migration}"
    description = "Drop all tables and re-run all migrations"
    
    def handle(self) -> int:
        """Handle fresh command."""
        seed = self.option("seed", False)
        
        manager = get_migration_manager()
        
        try:
            manager.fresh()
            
            if seed:
                from database.seeders.SeederManager import SeederManager
                seeder_manager = SeederManager()
                seeder_manager.seed()
                self.info("Seeders completed.")
            
            self.info("Database freshened successfully.")
            return 0
        except Exception as e:
            self.error(f"Fresh failed: {e}")
            return 1


class MigrateRefreshCommand(Command):
    """Laravel-style migrate:refresh command."""
    
    signature = "migrate:refresh {--seed : Run seeders after migration}"
    description = "Rollback all migrations and re-run them"
    
    def handle(self) -> int:
        """Handle refresh command."""
        seed = self.option("seed", False)
        
        manager = get_migration_manager()
        
        try:
            manager.refresh()
            
            if seed:
                from database.seeders.SeederManager import SeederManager
                seeder_manager = SeederManager()
                seeder_manager.seed()
                self.info("Seeders completed.")
            
            self.info("Database refreshed successfully.")
            return 0
        except Exception as e:
            self.error(f"Refresh failed: {e}")
            return 1


class MigrateStatusCommand(Command):
    """Laravel-style migrate:status command."""
    
    signature = "migrate:status"
    description = "Show migration status"
    
    def handle(self) -> int:
        """Handle status command."""
        manager = get_migration_manager()
        
        try:
            manager.status()
            return 0
        except Exception as e:
            self.error(f"Failed to get migration status: {e}")
            return 1


class MigrateInstallCommand(Command):
    """Laravel-style migrate:install command."""
    
    signature = "migrate:install"
    description = "Create migration repository"
    
    def handle(self) -> int:
        """Handle install command."""
        manager = get_migration_manager()
        
        try:
            manager.install()
            return 0
        except Exception as e:
            self.error(f"Failed to install migration repository: {e}")
            return 1


class MakeMigrationCommand(Command):
    """Laravel-style make:migration command."""
    
    signature = "make:migration {name : Migration name} {--create= : Create table name} {--table= : Modify table name}"
    description = "Create a new migration file"
    
    def handle(self) -> int:
        """Handle make migration command."""
        migration_name = self.argument("name")
        if not migration_name:
            self.error("Migration name is required")
            return 1
        
        create_table = self.option("create")
        modify_table = self.option("table")
        
        manager = get_migration_manager()
        
        try:
            file_path = manager.make_migration(migration_name, create_table, modify_table)
            self.success(f"Migration created: {file_path}")
            return 0
        except Exception as e:
            self.error(f"Failed to create migration: {e}")
            return 1
    


class MigrationSquashCommand(Command):
    """Squash multiple migrations into a single migration."""
    
    signature = "migrate:squash {--from= : Start migration} {--to= : End migration}"
    description = "Squash migrations into a single migration"
    
    def handle(self) -> int:
        """Handle squash command."""
        from_migration = self.option("from")
        to_migration = self.option("to")
        
        if not from_migration or not to_migration:
            self.error("Both --from and --to migrations are required")
            return 1
        
        self.info(f"Squashing migrations from {from_migration} to {to_migration}...")
        
        try:
            # This would need to be implemented in the migration manager
            self.error("Migration squashing functionality needs to be implemented.")
            return 1
            
        except Exception as e:
            self.error(f"Failed to squash migrations: {e}")
            return 1


# Register migration commands
from app.Console.Artisan import register_command

register_command(MigrateCommand)
register_command(MigrateRollbackCommand)
register_command(MigrateResetCommand)
register_command(MigrateFreshCommand)
register_command(MigrateRefreshCommand)
register_command(MigrateStatusCommand)
register_command(MigrateInstallCommand)
register_command(MakeMigrationCommand)
register_command(MigrationSquashCommand)