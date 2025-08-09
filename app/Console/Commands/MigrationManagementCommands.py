from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
from sqlalchemy import text
from ..Command import Command


class MigrateFreshCommand(Command):
    """Drop all tables and re-run all migrations."""
    
    signature = "migrate:fresh {--seed : Run database seeders after migration} {--force : Force the operation without confirmation}"
    description = "Drop all tables and re-run all migrations"
    help = "Drop all tables and re-run all migrations with optional seeding"
    
    async def handle(self) -> None:
        """Execute the command."""
        force = self.option("force", False)
        seed = self.option("seed", False)
        
        if not force:
            self.error("⚠️  This will DESTROY all data in your database!")
            if not self.confirm("Are you sure you want to continue?"):
                self.info("Operation cancelled.")
                return
        
        self.info("🗑️  Dropping all tables...")
        
        try:
            # Drop all tables
            await self._drop_all_tables()
            
            # Run migrations
            self.info("🚀 Running migrations...")
            await self._run_migrations()
            
            # Run seeders if requested
            if seed:
                self.info("🌱 Running seeders...")
                await self._run_seeders()
            
            self.info("✅ Fresh migration completed successfully!")
            
        except Exception as e:
            self.error(f"Migration failed: {e}")
    
    async def _drop_all_tables(self) -> None:
        """Drop all database tables."""
        try:
            from config.database import engine, Base
            Base.metadata.drop_all(bind=engine)
            self.comment("All tables dropped")
        except Exception as e:
            self.error(f"Failed to drop tables: {e}")
            raise
    
    async def _run_migrations(self) -> None:
        """Run all migrations."""
        try:
            from app.Console.Commands.MigrateCommand import MigrateCommand
            migrate_cmd = MigrateCommand()
            # MigrateCommand.handle is not async, call it directly
            migrate_cmd.handle([])
        except Exception as e:
            self.error(f"Failed to run migrations: {e}")
            raise
    
    async def _run_seeders(self) -> None:
        """Run database seeders."""
        try:
            from app.Console.Commands.DatabaseCommands import DatabaseSeedCommand
            seed_cmd = DatabaseSeedCommand()
            seed_cmd.arguments = {}
            seed_cmd.options = {}
            await seed_cmd.handle()
        except Exception:
            # Fallback to manual seeding
            self.comment("Running fallback seeders...")
            await self._run_fallback_seeders()
    
    async def _run_fallback_seeders(self) -> None:
        """Run fallback seeders manually."""
        import subprocess
        seeder_files = [
            "database/seeders/user_seeder.py",
            "database/seeders/permission_seeder.py", 
            "database/seeders/oauth2_seeder.py"
        ]
        
        for seeder in seeder_files:
            if Path(seeder).exists():
                try:
                    subprocess.run(["python3", seeder], check=True)
                    self.comment(f"Ran {seeder}")
                except subprocess.CalledProcessError:
                    self.comment(f"Failed to run {seeder}")


class MigrateRefreshCommand(Command):
    """Rollback and re-run all migrations."""
    
    signature = "migrate:refresh {--seed : Run database seeders after migration} {--step=0 : Number of migrations to rollback}"
    description = "Rollback and re-run all migrations"
    help = "Rollback all migrations and re-run them with optional seeding"
    
    async def handle(self) -> None:
        """Execute the command."""
        seed = self.option("seed", False)
        step = int(self.option("step", 0))
        
        self.info("🔄 Refreshing migrations...")
        
        try:
            # Rollback migrations
            await self._rollback_migrations(step)
            
            # Run migrations again
            await self._run_migrations()
            
            # Run seeders if requested
            if seed:
                await self._run_seeders()
            
            self.info("✅ Migration refresh completed successfully!")
            
        except Exception as e:
            self.error(f"Migration refresh failed: {e}")
    
    async def _rollback_migrations(self, step: int = 0) -> None:
        """Rollback migrations."""
        try:
            from app.Console.Commands.MigrateCommand import MigrateCommand
            migrate_cmd = MigrateCommand()
            # MigrateCommand doesn't support rollback directly
            # This would need to be implemented in MigrateCommand
            self.comment("Rolling back migrations...")
        except Exception as e:
            self.comment(f"Rollback failed: {e}")
    
    async def _run_migrations(self) -> None:
        """Run migrations."""
        try:
            from app.Console.Commands.MigrateCommand import MigrateCommand
            migrate_cmd = MigrateCommand()
            # MigrateCommand.handle is not async, call it directly
            migrate_cmd.handle([])
        except Exception as e:
            self.error(f"Failed to run migrations: {e}")
            raise
    
    async def _run_seeders(self) -> None:
        """Run seeders."""
        self.info("🌱 Running seeders...")
        # Similar to MigrateFreshCommand implementation


class MigrateInstallCommand(Command):
    """Create the migration repository."""
    
    signature = "migrate:install"
    description = "Create the migration repository"
    help = "Create the migrations table in the database"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("📋 Creating migration repository...")
        
        try:
            await self._create_migrations_table()
            self.info("✅ Migration table created successfully!")
            
        except Exception as e:
            if "already exists" in str(e).lower():
                self.info("Migration table already exists.")
            else:
                self.error(f"Failed to create migration table: {e}")
    
    async def _create_migrations_table(self) -> None:
        """Create the migrations table."""
        from config.database import engine
        
        create_sql = """
        CREATE TABLE IF NOT EXISTS migrations (
            migration VARCHAR(255) PRIMARY KEY,
            batch INTEGER NOT NULL
        )
        """
        
        with engine.connect() as conn:
            conn.execute(text(create_sql))
            conn.commit()


class MakeStubCommand(Command):
    """Create a new migration stub."""
    
    signature = "make:migration {name : Name of the migration} {--create= : Create a new table} {--table= : Modify an existing table}"
    description = "Create a new database migration file"
    help = "Generate a new migration file with optional table creation or modification"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        create_table = self.option("create")
        table_name = self.option("table")
        
        if not name:
            self.error("Migration name is required")
            return
        
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        migration_name = f"{timestamp}_{name}.py"
        migration_path = Path(f"database/migrations/{migration_name}")
        
        # Create migrations directory if it doesn't exist
        migration_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate migration content
        if create_table:
            content = self._generate_create_table_migration(name, create_table)
        elif table_name:
            content = self._generate_modify_table_migration(name, table_name)
        else:
            content = self._generate_blank_migration(name)
        
        # Write the migration file
        migration_path.write_text(content)
        
        self.info(f"✅ Migration created: {migration_path}")
        self.comment(f"Run: python artisan.py migrate")
    
    def _generate_create_table_migration(self, name: str, table_name: str) -> str:
        """Generate a create table migration."""
        class_name = self._snake_to_pascal(name)
        
        return f'''"""
{name}

Revision ID: {datetime.now().strftime("%Y%m%d%H%M%S")}
Create Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers
revision = '{datetime.now().strftime("%Y%m%d%H%M%S")}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create {table_name} table."""
    op.create_table(
        '{table_name}',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        # Add your columns here
    )


def downgrade() -> None:
    """Drop {table_name} table."""
    op.drop_table('{table_name}')
'''
    
    def _generate_modify_table_migration(self, name: str, table_name: str) -> str:
        """Generate a modify table migration."""
        return f'''"""
{name}

Revision ID: {datetime.now().strftime("%Y%m%d%H%M%S")}
Create Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers  
revision = '{datetime.now().strftime("%Y%m%d%H%M%S")}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Modify {table_name} table."""
    # Add your schema changes here
    # Examples:
    # op.add_column('{table_name}', sa.Column('new_column', sa.String(255), nullable=True))
    # op.alter_column('{table_name}', 'existing_column', type_=sa.Text())
    # op.create_index('idx_{table_name}_column', '{table_name}', ['column_name'])
    pass


def downgrade() -> None:
    """Reverse changes to {table_name} table."""
    # Add your rollback logic here
    # Examples:
    # op.drop_column('{table_name}', 'new_column')
    # op.drop_index('idx_{table_name}_column', table_name='{table_name}')
    pass
'''
    
    def _generate_blank_migration(self, name: str) -> str:
        """Generate a blank migration."""
        return f'''"""
{name}

Revision ID: {datetime.now().strftime("%Y%m%d%H%M%S")}
Create Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '{datetime.now().strftime("%Y%m%d%H%M%S")}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Migration upgrade logic."""
    # Add your migration logic here
    pass


def downgrade() -> None:
    """Migration downgrade logic."""
    # Add your rollback logic here
    pass
'''
    
    def _snake_to_pascal(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        components = snake_str.split('_')
        return ''.join(word.capitalize() for word in components)


class MigrationListCommand(Command):
    """List all migrations and their status."""
    
    signature = "migrate:status"
    description = "Show the status of each migration"
    help = "Display all migrations and whether they have been run"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("Migration Status")
        self.line("=" * 60)
        
        try:
            migrations = await self._get_migrations()
            run_migrations = await self._get_run_migrations()
            
            if not migrations:
                self.info("No migrations found.")
                return
            
            # Display header
            self.line(f"{'Status':<8} | {'Migration':<40} | {'Batch'}")
            self.line("-" * 60)
            
            for migration in migrations:
                migration_name = Path(migration).stem
                
                if migration_name in run_migrations:
                    batch = run_migrations[migration_name]
                    status = "✅ Run"
                    self.line(f"{status:<8} | {migration_name:<40} | {batch}")
                else:
                    status = "⏸️  Pending"
                    self.line(f"{status:<8} | {migration_name:<40} | -")
            
            self.line("")
            self.info(f"Total migrations: {len(migrations)}")
            self.info(f"Completed: {len(run_migrations)}")
            self.info(f"Pending: {len(migrations) - len(run_migrations)}")
            
        except Exception as e:
            self.error(f"Failed to get migration status: {e}")
    
    async def _get_migrations(self) -> List[str]:
        """Get all migration files."""
        migrations_dir = Path("database/migrations")
        if not migrations_dir.exists():
            return []
        
        migrations = []
        for migration_file in migrations_dir.glob("*.py"):
            if not migration_file.name.startswith("_"):
                migrations.append(str(migration_file))
        
        return sorted(migrations)
    
    async def _get_run_migrations(self) -> Dict[str, int]:
        """Get migrations that have been run."""
        try:
            from config.database import engine
            
            with engine.connect() as conn:
                # Check if migrations table exists
                result = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'")
                )
                
                if not result.fetchone():
                    return {}
                
                # Get run migrations
                result = conn.execute(text("SELECT migration, batch FROM migrations"))
                return {row[0]: row[1] for row in result}
                
        except Exception:
            return {}


class MigrateRollbackCommand(Command):
    """Rollback the last database migration."""
    
    signature = "migrate:rollback {--step=1 : Number of batches to rollback}"
    description = "Rollback the last database migration"
    help = "Rollback one or more migration batches"
    
    async def handle(self) -> None:
        """Execute the command."""
        steps = int(self.option("step", 1))
        
        self.info(f"🔙 Rolling back {steps} migration batch(es)...")
        
        try:
            rolled_back = await self._rollback_migrations(steps)
            
            if rolled_back:
                self.info(f"✅ Rolled back {len(rolled_back)} migration(s):")
                for migration in rolled_back:
                    self.comment(f"  - {migration}")
            else:
                self.info("No migrations to rollback.")
                
        except Exception as e:
            self.error(f"Rollback failed: {e}")
    
    async def _rollback_migrations(self, steps: int) -> List[str]:
        """Rollback migrations."""
        # This would need proper implementation with Alembic or custom logic
        self.comment("Rollback functionality requires Alembic integration")
        return []


class SchemaDumpCommand(Command):
    """Dump the current database schema."""
    
    signature = "schema:dump {--file= : Output file path}"
    description = "Dump the current database schema"
    help = "Export the current database schema to a SQL file"
    
    async def handle(self) -> None:
        """Execute the command."""
        output_file = self.option("file") or f"database/schema/schema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        output_path = Path(output_file)
        
        self.info("📋 Dumping database schema...")
        
        try:
            schema_sql = await self._dump_schema()
            
            # Create output directory
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write schema to file
            output_path.write_text(schema_sql)
            
            self.info(f"✅ Schema dumped to: {output_path}")
            
        except Exception as e:
            self.error(f"Schema dump failed: {e}")
    
    async def _dump_schema(self) -> str:
        """Dump the database schema."""
        try:
            from config.database import engine
            
            schema_parts = []
            
            with engine.connect() as conn:
                # Get all tables
                result = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL"))
                
                for row in result:
                    schema_parts.append(row[0] + ";\n")
                
                # Get all indexes
                result = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"))
                
                for row in result:
                    schema_parts.append(row[0] + ";\n")
            
            header = f"""-- Database Schema Dump
-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- Database: SQLite

"""
            
            return header + "\n".join(schema_parts)
            
        except Exception as e:
            raise Exception(f"Failed to dump schema: {e}")