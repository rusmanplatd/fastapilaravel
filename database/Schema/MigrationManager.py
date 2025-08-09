from __future__ import annotations

import os
import importlib
import importlib.util
from typing import List, Dict, Optional, Any, Type
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, DateTime, Integer
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from .Migration import Migration
from config.database import DATABASE_URL


class MigrationBatch:
    """Represents a batch of migrations."""
    
    def __init__(self, batch_id: int, migrations: List[str]) -> None:
        self.batch_id = batch_id
        self.migrations = migrations
        self.executed_at = datetime.now()


class MigrationManager:
    """Laravel-style migration manager."""
    
    def __init__(self, migrations_path: str = "database/migrations") -> None:
        self.migrations_path = Path(migrations_path)
        self.engine: Optional[Engine] = None
        self._migrations_table = "migrations"
        self._migration_batches_table = "migration_batches"
    
    def get_engine(self) -> Engine:
        """Get database engine."""
        if self.engine is None:
            self.engine = create_engine(DATABASE_URL)
        return self.engine
    
    def ensure_migration_tables(self) -> None:
        """Ensure migration tracking tables exist."""
        engine = self.get_engine()
        metadata = MetaData()
        
        # Migrations table
        migrations_table = Table(
            self._migrations_table,
            metadata,
            Column('id', Integer, primary_key=True),
            Column('migration', String(255), unique=True, nullable=False),
            Column('batch', Integer, nullable=False),
            Column('executed_at', DateTime, nullable=False, default=datetime.now)
        )
        
        # Migration batches table  
        batches_table = Table(
            self._migration_batches_table,
            metadata,
            Column('id', Integer, primary_key=True),
            Column('batch', Integer, unique=True, nullable=False),
            Column('migrations_count', Integer, nullable=False),
            Column('executed_at', DateTime, nullable=False, default=datetime.now)
        )
        
        metadata.create_all(engine)
    
    def get_migration_files(self) -> List[str]:
        """Get all migration files sorted by timestamp."""
        migration_files = []
        
        for file_path in self.migrations_path.glob("*.py"):
            if file_path.name.startswith("create_") or file_path.name.startswith("add_") or file_path.name.startswith("modify_"):
                # Skip non-migration files
                if file_path.name in ["Migration.py", "MigrationRunner.py", "MigrationManager.py", "__init__.py"]:
                    continue
                migration_files.append(file_path.stem)
        
        return sorted(migration_files)
    
    def get_executed_migrations(self) -> List[Dict[str, Any]]:
        """Get list of executed migrations from database."""
        self.ensure_migration_tables()
        engine = self.get_engine()
        
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT migration, batch, executed_at FROM {self._migrations_table} ORDER BY id")
                )
                return [{"migration": row[0], "batch": row[1], "executed_at": row[2]} for row in result]
        except SQLAlchemyError:
            return []
    
    def get_pending_migrations(self) -> List[str]:
        """Get list of migrations that haven't been executed."""
        all_migrations = self.get_migration_files()
        executed_migrations = {m["migration"] for m in self.get_executed_migrations()}
        return [m for m in all_migrations if m not in executed_migrations]
    
    def get_next_batch_number(self) -> int:
        """Get the next batch number."""
        self.ensure_migration_tables()
        engine = self.get_engine()
        
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT MAX(batch) FROM {self._migrations_table}")
                )
                max_batch = result.scalar()
                return (max_batch or 0) + 1
        except SQLAlchemyError:
            return 1
    
    def load_migration_class(self, migration_name: str) -> Optional[Type[Migration]]:
        """Load migration class dynamically."""
        try:
            module_path = self.migrations_path / f"{migration_name}.py"
            spec = importlib.util.spec_from_file_location(migration_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find migration class in module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, Migration) and 
                        attr != Migration):
                        return attr
        except Exception as e:
            print(f"Error loading migration {migration_name}: {e}")
        
        return None
    
    def record_migration(self, migration_name: str, batch: int) -> None:
        """Record migration execution in database."""
        engine = self.get_engine()
        
        with engine.connect() as conn:
            conn.execute(
                text(f"INSERT INTO {self._migrations_table} (migration, batch, executed_at) VALUES (:migration, :batch, :executed_at)"),
                {"migration": migration_name, "batch": batch, "executed_at": datetime.now()}
            )
            conn.commit()
    
    def unrecord_migration(self, migration_name: str) -> None:
        """Remove migration record from database."""
        engine = self.get_engine()
        
        with engine.connect() as conn:
            conn.execute(
                text(f"DELETE FROM {self._migrations_table} WHERE migration = :migration"),
                {"migration": migration_name}
            )
            conn.commit()
    
    def migrate(self, steps: Optional[int] = None) -> List[str]:
        """Run pending migrations."""
        pending = self.get_pending_migrations()
        
        if steps:
            pending = pending[:steps]
        
        if not pending:
            print("Nothing to migrate.")
            return []
        
        batch = self.get_next_batch_number()
        executed = []
        
        print(f"Running batch {batch} with {len(pending)} migrations:")
        
        for migration_name in pending:
            try:
                print(f"Migrating: {migration_name}")
                
                migration_class = self.load_migration_class(migration_name)
                if migration_class:
                    migration = migration_class()
                    migration.up()
                    self.record_migration(migration_name, batch)
                    executed.append(migration_name)
                    print(f"Migrated: {migration_name}")
                else:
                    print(f"Could not load migration: {migration_name}")
            except Exception as e:
                print(f"Migration failed: {migration_name} - {e}")
                break
        
        return executed
    
    def rollback(self, steps: int = 1) -> List[str]:
        """Rollback migrations."""
        executed_migrations = self.get_executed_migrations()
        
        if not executed_migrations:
            print("Nothing to rollback.")
            return []
        
        # Group by batch
        batches = {}
        for migration in executed_migrations:
            batch = migration["batch"]
            if batch not in batches:
                batches[batch] = []
            batches[batch].append(migration)
        
        # Get the last N batches
        batch_numbers = sorted(batches.keys(), reverse=True)[:steps]
        
        rolled_back = []
        
        for batch_number in batch_numbers:
            print(f"Rolling back batch {batch_number}:")
            
            # Roll back in reverse order
            batch_migrations = reversed(batches[batch_number])
            
            for migration_info in batch_migrations:
                migration_name = migration_info["migration"]
                try:
                    print(f"Rolling back: {migration_name}")
                    
                    migration_class = self.load_migration_class(migration_name)
                    if migration_class:
                        migration = migration_class()
                        migration.down()
                        self.unrecord_migration(migration_name)
                        rolled_back.append(migration_name)
                        print(f"Rolled back: {migration_name}")
                    else:
                        print(f"Could not load migration: {migration_name}")
                except Exception as e:
                    print(f"Rollback failed: {migration_name} - {e}")
                    break
        
        return rolled_back
    
    def get_rollback_migrations(self, steps: int = 1) -> List[str]:
        """Get list of migrations that would be rolled back."""
        executed_migrations = self.get_executed_migrations()
        
        if not executed_migrations:
            return []
        
        # Group by batch
        batches = {}
        for migration in executed_migrations:
            batch = migration["batch"]
            if batch not in batches:
                batches[batch] = []
            batches[batch].append(migration)
        
        # Get the last N batches
        batch_numbers = sorted(batches.keys(), reverse=True)[:steps]
        
        migrations_to_rollback = []
        
        for batch_number in batch_numbers:
            # Get migrations in this batch
            batch_migrations = batches[batch_number]
            for migration_info in batch_migrations:
                migrations_to_rollback.append(migration_info["migration"])
        
        return migrations_to_rollback
    
    def reset(self) -> List[str]:
        """Rollback all migrations."""
        executed_migrations = self.get_executed_migrations()
        
        if not executed_migrations:
            print("Nothing to reset.")
            return []
        
        print("Rolling back all migrations:")
        
        rolled_back = []
        
        # Roll back in reverse order
        for migration_info in reversed(executed_migrations):
            migration_name = migration_info["migration"]
            try:
                print(f"Rolling back: {migration_name}")
                
                migration_class = self.load_migration_class(migration_name)
                if migration_class:
                    migration = migration_class()
                    migration.down()
                    self.unrecord_migration(migration_name)
                    rolled_back.append(migration_name)
                    print(f"Rolled back: {migration_name}")
                else:
                    print(f"Could not load migration: {migration_name}")
            except Exception as e:
                print(f"Rollback failed: {migration_name} - {e}")
                break
        
        return rolled_back
    
    def fresh(self) -> None:
        """Drop all tables and re-run all migrations."""
        print("Dropping all tables...")
        
        engine = self.get_engine()
        metadata = MetaData()
        metadata.reflect(bind=engine)
        metadata.drop_all(engine)
        
        print("All tables dropped.")
        print("Re-running all migrations...")
        
        self.migrate()
    
    def refresh(self) -> None:
        """Rollback all migrations and re-run them."""
        print("Rolling back all migrations...")
        self.reset()
        
        print("Re-running all migrations...")
        self.migrate()
    
    def status(self) -> None:
        """Show migration status."""
        all_migrations = self.get_migration_files()
        executed_migrations = {m["migration"]: m for m in self.get_executed_migrations()}
        
        if not all_migrations:
            print("No migrations found.")
            return
        
        print("Migration Status:")
        print("-" * 80)
        print(f"{'Status':<10} {'Migration':<40} {'Batch':<10} {'Executed At':<20}")
        print("-" * 80)
        
        for migration in all_migrations:
            if migration in executed_migrations:
                info = executed_migrations[migration]
                status = "✓ RAN"
                batch = str(info["batch"])
                executed_at = info["executed_at"].strftime("%Y-%m-%d %H:%M:%S")
            else:
                status = "⚠ PENDING"
                batch = "-"
                executed_at = "-"
            
            print(f"{status:<10} {migration:<40} {batch:<10} {executed_at:<20}")
    
    def install(self) -> None:
        """Install migration tables."""
        print("Installing migration tables...")
        self.ensure_migration_tables()
        print("Migration tables installed.")