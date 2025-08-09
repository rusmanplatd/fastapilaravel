from __future__ import annotations

import importlib
import inspect
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Tuple
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, DateTime, Integer
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from .Migration import Migration
from app.Support.Container import container


class MigrationRunner:
    """Laravel-style migration runner for executing database migrations."""
    
    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url or container.get('config').get('database.url')
        self.engine: Engine = create_engine(self.database_url)
        self.session_maker = sessionmaker(bind=self.engine)
        self.metadata = MetaData()
        self._create_migrations_table()
    
    def _create_migrations_table(self) -> None:
        """Create the migrations tracking table if it doesn't exist."""
        migrations_table = Table(
            'migrations',
            self.metadata,
            Column('id', Integer, primary_key=True),
            Column('migration', String(255), nullable=False, unique=True),
            Column('batch', Integer, nullable=False),
            Column('executed_at', DateTime, nullable=False, default=datetime.now)
        )
        
        try:
            self.metadata.create_all(self.engine, tables=[migrations_table], checkfirst=True)
        except SQLAlchemyError as e:
            print(f"Warning: Could not create migrations table: {e}")
    
    def get_migration_files(self) -> List[str]:
        """Get all migration files from the migrations directory."""
        migrations_dir = Path(__file__).parent
        migration_files = []
        
        for file in migrations_dir.glob('create_*.py'):
            if file.name not in ['Migration.py', 'MigrationRunner.py', '__init__.py']:
                migration_files.append(file.stem)
        
        return sorted(migration_files)
    
    def load_migration_class(self, migration_name: str) -> Type[Migration]:
        """Load a migration class from its file."""
        try:
            # Import the migration module
            module_name = f"database.migrations.{migration_name}"
            spec = importlib.util.find_spec(module_name)
            
            if spec is None or spec.loader is None:
                raise ImportError(f"Migration module {module_name} not found")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find the migration class in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, Migration) and 
                    obj != Migration and 
                    not name.startswith('_')):
                    return obj
            
            raise ImportError(f"No Migration class found in {module_name}")
            
        except Exception as e:
            raise ImportError(f"Failed to load migration {migration_name}: {e}")
    
    def get_executed_migrations(self) -> List[Tuple[str, int]]:
        """Get list of executed migrations with their batch numbers."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT migration, batch FROM migrations ORDER BY id")
                )
                return [(row.migration, row.batch) for row in result]
        except SQLAlchemyError:
            return []
    
    def get_pending_migrations(self) -> List[str]:
        """Get list of migrations that haven't been executed yet."""
        all_migrations = self.get_migration_files()
        executed_migrations = [migration for migration, _ in self.get_executed_migrations()]
        
        return [migration for migration in all_migrations 
                if migration not in executed_migrations]
    
    def get_next_batch_number(self) -> int:
        """Get the next batch number for migrations."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT MAX(batch) as max_batch FROM migrations")
                )
                row = result.fetchone()
                return (row.max_batch or 0) + 1
        except SQLAlchemyError:
            return 1
    
    def record_migration(self, migration_name: str, batch: int) -> None:
        """Record a migration as executed."""
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text("INSERT INTO migrations (migration, batch, executed_at) VALUES (:migration, :batch, :executed_at)"),
                    {
                        "migration": migration_name,
                        "batch": batch,
                        "executed_at": datetime.now()
                    }
                )
                conn.commit()
        except SQLAlchemyError as e:
            print(f"Warning: Could not record migration {migration_name}: {e}")
    
    def remove_migration_record(self, migration_name: str) -> None:
        """Remove a migration record (for rollbacks)."""
        try:
            with self.engine.connect() as conn:
                conn.execute(
                    text("DELETE FROM migrations WHERE migration = :migration"),
                    {"migration": migration_name}
                )
                conn.commit()
        except SQLAlchemyError as e:
            print(f"Warning: Could not remove migration record {migration_name}: {e}")
    
    def migrate(self, steps: Optional[int] = None) -> None:
        """Run pending migrations."""
        pending_migrations = self.get_pending_migrations()
        
        if not pending_migrations:
            print("Nothing to migrate.")
            return
        
        if steps:
            pending_migrations = pending_migrations[:steps]
        
        batch = self.get_next_batch_number()
        
        print(f"Running {len(pending_migrations)} migrations (batch {batch}):")
        
        for migration_name in pending_migrations:
            self._execute_migration_up(migration_name, batch)
    
    def _execute_migration_up(self, migration_name: str, batch: int) -> None:
        """Execute a single migration's up method."""
        try:
            print(f"  Migrating: {migration_name}")
            
            # Load and execute the migration
            migration_class = self.load_migration_class(migration_name)
            migration_instance = migration_class()
            
            # Execute the up method
            migration_instance.up()
            
            # Record the migration
            self.record_migration(migration_name, batch)
            
            print(f"  Migrated:  {migration_name}")
            
        except Exception as e:
            print(f"  Failed:    {migration_name} - {e}")
            raise e
    
    def rollback(self, steps: int = 1) -> None:
        """Rollback migrations."""
        executed_migrations = self.get_executed_migrations()
        
        if not executed_migrations:
            print("Nothing to rollback.")
            return
        
        # Get migrations from the last batch(es) to rollback
        last_batch = executed_migrations[-1][1] if executed_migrations else 0
        migrations_to_rollback = []
        
        current_steps = 0
        for migration, batch in reversed(executed_migrations):
            if current_steps >= steps:
                break
            
            if batch >= (last_batch - steps + 1):
                migrations_to_rollback.append(migration)
                current_steps += 1
        
        print(f"Rolling back {len(migrations_to_rollback)} migrations:")
        
        for migration_name in migrations_to_rollback:
            self._execute_migration_down(migration_name)
    
    def _execute_migration_down(self, migration_name: str) -> None:
        """Execute a single migration's down method."""
        try:
            print(f"  Rolling back: {migration_name}")
            
            # Load and execute the migration
            migration_class = self.load_migration_class(migration_name)
            migration_instance = migration_class()
            
            # Execute the down method
            migration_instance.down()
            
            # Remove the migration record
            self.remove_migration_record(migration_name)
            
            print(f"  Rolled back:  {migration_name}")
            
        except Exception as e:
            print(f"  Failed:       {migration_name} - {e}")
            raise e
    
    def reset(self) -> None:
        """Rollback all migrations."""
        executed_migrations = self.get_executed_migrations()
        
        if not executed_migrations:
            print("Nothing to reset.")
            return
        
        print(f"Rolling back {len(executed_migrations)} migrations:")
        
        # Rollback in reverse order
        for migration_name, _ in reversed(executed_migrations):
            self._execute_migration_down(migration_name)
    
    def refresh(self) -> None:
        """Rollback all migrations and then migrate again."""
        self.reset()
        self.migrate()
    
    def status(self) -> None:
        """Show migration status."""
        all_migrations = self.get_migration_files()
        executed_migrations = dict(self.get_executed_migrations())
        
        print("Migration Status:")
        print("-" * 50)
        
        if not all_migrations:
            print("No migrations found.")
            return
        
        for migration in all_migrations:
            if migration in executed_migrations:
                batch = executed_migrations[migration]
                status = f"✓ Ran (batch {batch})"
            else:
                status = "✗ Pending"
            
            print(f"{status:<20} {migration}")
    
    def make_migration(self, name: str, create_table: Optional[str] = None) -> None:
        """Create a new migration file."""
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        
        if create_table:
            filename = f"{timestamp}_create_{create_table}_table.py"
            class_name = f"Create{create_table.replace('_', '').title()}Table"
            template = self._get_create_table_template(class_name, create_table)
        else:
            filename = f"{timestamp}_{name}.py"
            class_name = name.replace('_', '').title()
            template = self._get_migration_template(class_name)
        
        migration_path = Path(__file__).parent / filename
        
        with open(migration_path, 'w') as f:
            f.write(template)
        
        print(f"Created migration: {filename}")
    
    def _get_create_table_template(self, class_name: str, table_name: str) -> str:
        """Get template for create table migration."""
        return f'''from __future__ import annotations

from database.Schema.Blueprint import Blueprint
from .Migration import CreateTableMigration


class {class_name}(CreateTableMigration):
    """Create {table_name} table."""
    
    def up(self) -> None:
        """Run the migration."""
        def create_{table_name}_table(table: Blueprint) -> None:
            table.id()
            
            # Add your columns here
            table.string('name')
            table.text('description').nullable_column()
            table.boolean('is_active').default(True)
            
            table.timestamps()
            
            # Add indexes
            table.index(['name'])
        
        self.create_table('{table_name}', create_{table_name}_table)
'''
    
    def _get_migration_template(self, class_name: str) -> str:
        """Get template for general migration."""
        return f'''from __future__ import annotations

from database.Schema.Blueprint import Blueprint
from .Migration import Migration


class {class_name}(Migration):
    """Migration description."""
    
    def up(self) -> None:
        """Run the migration."""
        def modify_table(table: Blueprint) -> None:
            # Add your modifications here
            pass
        
        self.modify_table('table_name', modify_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        def rollback_table(table: Blueprint) -> None:
            # Add your rollback logic here
            pass
        
        self.modify_table('table_name', rollback_table)
'''


# CLI interface functions
def migrate(steps: Optional[int] = None) -> None:
    """Run migrations."""
    runner = MigrationRunner()
    runner.migrate(steps)


def rollback(steps: int = 1) -> None:
    """Rollback migrations."""
    runner = MigrationRunner()
    runner.rollback(steps)


def reset() -> None:
    """Reset all migrations."""
    runner = MigrationRunner()
    runner.reset()


def refresh() -> None:
    """Refresh all migrations."""
    runner = MigrationRunner()
    runner.refresh()


def status() -> None:
    """Show migration status."""
    runner = MigrationRunner()
    runner.status()


def make_migration(name: str, create_table: Optional[str] = None) -> None:
    """Create a new migration."""
    runner = MigrationRunner()
    runner.make_migration(name, create_table)