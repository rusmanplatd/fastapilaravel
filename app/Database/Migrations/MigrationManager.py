from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Type, Callable
from datetime import datetime
import importlib.util
import inspect
from sqlalchemy import create_engine, text, Table
from sqlalchemy.schema import MetaData
from sqlalchemy.orm import sessionmaker
from abc import ABC, abstractmethod


class Migration(ABC):
    """Base migration class."""
    
    def __init__(self) -> None:
        self.connection: Optional[Any] = None
    
    @abstractmethod
    def up(self) -> None:
        """Run the migration."""
        pass
    
    @abstractmethod
    def down(self) -> None:
        """Reverse the migration."""
        pass
    
    def execute(self, sql: str) -> None:
        """Execute raw SQL."""
        if self.connection:
            self.connection.execute(text(sql))
    
    def create_table(self, table_name: str, callback: Callable[[Any], None]) -> None:
        """Create a new table."""
        from app.Database.Schema.Blueprint import Blueprint
        blueprint = Blueprint(table_name)
        callback(blueprint)
        sql = blueprint.to_sql()
        self.execute(sql)
    
    def drop_table(self, table_name: str) -> None:
        """Drop a table."""
        self.execute(f"DROP TABLE IF EXISTS {table_name}")
    
    def drop_table_if_exists(self, table_name: str) -> None:
        """Drop table if it exists."""
        self.drop_table(table_name)
    
    def alter_table(self, table_name: str, callback: Callable[[Any], None]) -> None:
        """Alter an existing table."""
        from app.Database.Schema.Blueprint import Blueprint
        blueprint = Blueprint(table_name, alter=True)
        callback(blueprint)
        sql = blueprint.to_sql()
        self.execute(sql)
    
    def rename_table(self, old_name: str, new_name: str) -> None:
        """Rename a table."""
        self.execute(f"ALTER TABLE {old_name} RENAME TO {new_name}")
    
    def drop_column(self, table_name: str, column_name: str) -> None:
        """Drop a column."""
        self.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")
    
    def add_column(self, table_name: str, column_name: str, column_type: str) -> None:
        """Add a column."""
        self.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
    
    def add_index(self, table_name: str, columns: List[str], index_name: Optional[str] = None) -> None:
        """Add an index."""
        if index_name is None:
            index_name = f"idx_{table_name}_{'_'.join(columns)}"
        columns_str = ', '.join(columns)
        self.execute(f"CREATE INDEX {index_name} ON {table_name} ({columns_str})")
    
    def drop_index(self, index_name: str) -> None:
        """Drop an index."""
        self.execute(f"DROP INDEX {index_name}")
    
    def add_foreign_key(self, table_name: str, column: str, references_table: str, references_column: str = 'id') -> None:
        """Add a foreign key constraint."""
        constraint_name = f"fk_{table_name}_{column}"
        self.execute(f"""
            ALTER TABLE {table_name} 
            ADD CONSTRAINT {constraint_name} 
            FOREIGN KEY ({column}) REFERENCES {references_table}({references_column})
        """)
    
    def drop_foreign_key(self, table_name: str, constraint_name: str) -> None:
        """Drop a foreign key constraint."""
        self.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}")


class MigrationRecord:
    """Represents a migration record."""
    
    def __init__(self, migration: str, batch: int = 1) -> None:
        self.migration = migration
        self.batch = batch


class MigrationManager:
    """Laravel-style migration manager."""
    
    def __init__(self, database_url: str, migrations_path: str = 'database/migrations') -> None:
        self.database_url = database_url
        self.migrations_path = Path(migrations_path)
        self.engine = create_engine(database_url)
        self.session_maker = sessionmaker(bind=self.engine)
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self) -> None:
        """Ensure the migrations table exists."""
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration VARCHAR(255) NOT NULL,
                    batch INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
    
    def get_migration_files(self) -> List[str]:
        """Get all migration files."""
        if not self.migrations_path.exists():
            return []
        
        files = []
        for file_path in self.migrations_path.glob('*.py'):
            if not file_path.name.startswith('_'):
                files.append(file_path.stem)
        
        return sorted(files)
    
    def get_ran_migrations(self) -> List[str]:
        """Get migrations that have been run."""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT migration FROM migrations ORDER BY migration"))
            return [row[0] for row in result]
    
    def get_pending_migrations(self) -> List[str]:
        """Get migrations that haven't been run."""
        all_migrations = self.get_migration_files()
        ran_migrations = self.get_ran_migrations()
        return [m for m in all_migrations if m not in ran_migrations]
    
    def get_last_batch_number(self) -> int:
        """Get the last batch number."""
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT MAX(batch) FROM migrations"))
            batch = result.scalar()
            return int(batch) if batch is not None else 0
    
    def load_migration_class(self, migration_name: str) -> Type[Migration]:
        """Load a migration class from file."""
        file_path = self.migrations_path / f"{migration_name}.py"
        
        if not file_path.exists():
            raise FileNotFoundError(f"Migration file not found: {file_path}")
        
        spec = importlib.util.spec_from_file_location(migration_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load migration: {migration_name}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the migration class
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Migration) and obj != Migration:
                return obj
        
        raise ValueError(f"No migration class found in {migration_name}")
    
    def run_migration(self, migration_name: str, direction: str = 'up') -> None:
        """Run a single migration."""
        migration_class = self.load_migration_class(migration_name)
        migration_instance = migration_class()
        
        with self.engine.connect() as conn:
            migration_instance.connection = conn
            
            try:
                if direction == 'up':
                    migration_instance.up()
                    # Record the migration
                    batch = self.get_last_batch_number() + 1
                    conn.execute(text("INSERT INTO migrations (migration, batch) VALUES (:migration, :batch)"), 
                               {"migration": migration_name, "batch": batch})
                elif direction == 'down':
                    migration_instance.down()
                    # Remove the migration record
                    conn.execute(text("DELETE FROM migrations WHERE migration = :migration"), 
                               {"migration": migration_name})
                
                conn.commit()
                print(f"✅ Migrated: {migration_name}")
            except Exception as e:
                conn.rollback()
                print(f"❌ Failed to migrate {migration_name}: {e}")
                raise
    
    def migrate(self, steps: Optional[int] = None) -> None:
        """Run pending migrations."""
        pending = self.get_pending_migrations()
        
        if not pending:
            print("✅ Nothing to migrate.")
            return
        
        if steps is not None:
            pending = pending[:steps]
        
        print(f"🔄 Running {len(pending)} migrations...")
        
        for migration_name in pending:
            self.run_migration(migration_name, 'up')
        
        print(f"✅ Migrated {len(pending)} migrations.")
    
    def rollback(self, steps: int = 1) -> None:
        """Rollback migrations."""
        with self.engine.connect() as conn:
            # Get the last batch
            result = conn.execute(text("SELECT MAX(batch) FROM migrations"))
            last_batch = result.scalar()
            
            if last_batch is None:
                print("✅ Nothing to rollback.")
                return
            
            # Get migrations from the last batch(es)
            batches_to_rollback = list(range(last_batch - steps + 1, last_batch + 1))
            batches_str = ','.join(map(str, batches_to_rollback))
            
            result = conn.execute(text(f"SELECT migration FROM migrations WHERE batch IN ({batches_str}) ORDER BY migration DESC"))
            migrations_to_rollback = [row[0] for row in result]
        
        if not migrations_to_rollback:
            print("✅ Nothing to rollback.")
            return
        
        print(f"🔄 Rolling back {len(migrations_to_rollback)} migrations...")
        
        for migration_name in migrations_to_rollback:
            self.run_migration(migration_name, 'down')
        
        print(f"✅ Rolled back {len(migrations_to_rollback)} migrations.")
    
    def reset(self) -> None:
        """Rollback all migrations."""
        ran_migrations = self.get_ran_migrations()
        
        if not ran_migrations:
            print("✅ Nothing to reset.")
            return
        
        print(f"🔄 Rolling back all {len(ran_migrations)} migrations...")
        
        # Rollback in reverse order
        for migration_name in reversed(ran_migrations):
            self.run_migration(migration_name, 'down')
        
        print("✅ All migrations rolled back.")
    
    def refresh(self) -> None:
        """Rollback all migrations and run them again."""
        print("🔄 Refreshing migrations...")
        self.reset()
        self.migrate()
        print("✅ Migrations refreshed.")
    
    def status(self) -> None:
        """Show migration status."""
        all_migrations = self.get_migration_files()
        ran_migrations = self.get_ran_migrations()
        
        print("Migration Status:")
        print("=" * 50)
        
        if not all_migrations:
            print("No migrations found.")
            return
        
        for migration in all_migrations:
            status = "✅ Ran" if migration in ran_migrations else "❌ Pending"
            print(f"{status} {migration}")
        
        pending_count = len(all_migrations) - len(ran_migrations)
        print(f"\nTotal: {len(all_migrations)}, Ran: {len(ran_migrations)}, Pending: {pending_count}")
    
    def make_migration(self, name: str, create_table: Optional[str] = None, table: Optional[str] = None) -> str:
        """Create a new migration file."""
        timestamp = datetime.now().strftime('%Y_%m_%d_%H%M%S')
        
        if create_table:
            filename = f"{timestamp}_create_{create_table}_table.py"
            template = self._get_create_table_template(name, create_table)
        elif table:
            filename = f"{timestamp}_{name}.py"
            template = self._get_table_template(name, table)
        else:
            filename = f"{timestamp}_{name}.py"
            template = self._get_basic_template(name)
        
        file_path = self.migrations_path / filename
        
        # Ensure migrations directory exists
        self.migrations_path.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(template)
        
        print(f"✅ Created migration: {filename}")
        return str(file_path)
    
    def _get_basic_template(self, name: str) -> str:
        """Get basic migration template."""
        class_name = self._to_class_name(name)
        return f'''from __future__ import annotations

from app.Database.Migrations.MigrationManager import Migration


class {class_name}(Migration):
    """Migration: {name}"""
    
    def up(self) -> None:
        """Run the migration."""
        pass
    
    def down(self) -> None:
        """Reverse the migration."""
        pass
'''
    
    def _get_create_table_template(self, name: str, table_name: str) -> str:
        """Get create table migration template."""
        class_name = self._to_class_name(f"create_{table_name}_table")
        return f'''from __future__ import annotations

from app.Database.Migrations.MigrationManager import Migration


class {class_name}(Migration):
    """Create {table_name} table"""
    
    def up(self) -> None:
        """Run the migration."""
        def create_{table_name}_table(table) -> None:
            table.id()
            table.timestamps()
        
        self.create_table('{table_name}', create_{table_name}_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        self.drop_table_if_exists('{table_name}')
'''
    
    def _get_table_template(self, name: str, table_name: str) -> str:
        """Get table modification migration template."""
        class_name = self._to_class_name(name)
        return f'''from __future__ import annotations

from app.Database.Migrations.MigrationManager import Migration
from app.Database.Schema.Blueprint import Blueprint


class {class_name}(Migration):
    """Modify {table_name} table"""
    
    def up(self) -> None:
        """Run the migration."""
        def modify_{table_name}_table(table: Blueprint) -> None:
            # Add your columns here
            pass
        
        self.alter_table('{table_name}', modify_{table_name}_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        def reverse_{table_name}_table(table: Blueprint) -> None:
            # Reverse your changes here
            pass
        
        self.alter_table('{table_name}', reverse_{table_name}_table)
'''
    
    def _to_class_name(self, name: str) -> str:
        """Convert name to class name."""
        # Remove non-alphanumeric characters and convert to PascalCase
        words = re.findall(r'[a-zA-Z0-9]+', name)
        return ''.join(word.capitalize() for word in words)


# Global migration manager instance
migration_manager: Optional[MigrationManager] = None


def get_migration_manager() -> MigrationManager:
    """Get the global migration manager instance."""
    global migration_manager
    if migration_manager is None:
        # This would typically come from config
        database_url = "sqlite:///database.db"
        migration_manager = MigrationManager(database_url)
    return migration_manager