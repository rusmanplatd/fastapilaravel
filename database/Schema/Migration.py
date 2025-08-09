from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union, TypeVar, Generic, final, Literal, TypedDict
from sqlalchemy import MetaData, Table, create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateTable, DropTable
from .Blueprint import Blueprint, Schema
from datetime import datetime
import re

# Type definitions for Laravel 12 enhanced migration system
TableName = str
ColumnName = str
IndexName = str
ConstraintName = str
MigrationName = str

class MigrationOptions(TypedDict, total=False):
    """Type-safe migration options."""
    connection: Optional[str]
    batch_mode: bool
    foreign_key_checks: bool
    transaction: bool
    rollback_on_error: bool

class TableOptions(TypedDict, total=False):
    """Type-safe table options."""
    engine: str
    charset: str
    collation: str
    comment: str
    row_format: str
    auto_increment: int

T = TypeVar('T', bound='Migration')


@final
class Migration(ABC, Generic[T]):
    """Laravel 12-style migration base class with enhanced type safety."""
    
    def __init__(self) -> None:
        self.connection: Optional[str] = None
        self._metadata: MetaData = MetaData()
        self._tables_created: List[TableName] = []
        self._batch_mode: bool = False
        self._options: MigrationOptions = {
            'batch_mode': False,
            'foreign_key_checks': True,
            'transaction': True,
            'rollback_on_error': True
        }
        self._table_options: Dict[TableName, TableOptions] = {}
    
    @abstractmethod
    def up(self) -> None:
        """Run the migrations."""
        pass
    
    @abstractmethod  
    def down(self) -> None:
        """Reverse the migrations."""
        pass
    
    def get_migration_name(self) -> str:
        """Get the migration name from class name."""
        class_name = self.__class__.__name__
        # Convert CamelCase to snake_case
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    
    def get_table_name(self) -> str:
        """Extract table name from migration name."""
        name = self.get_migration_name()
        # Remove common prefixes
        for prefix in ['create_', 'modify_', 'alter_', 'add_', 'drop_']:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        
        # Remove _table suffix if present
        if name.endswith('_table'):
            name = name[:-6]
        
        return name
    
    # Schema Builder Methods (Laravel-style)
    
    def create_table(self, table_name: TableName, callback: Callable[[Blueprint], None]) -> None:
        """Create a new table using Laravel 12-style Blueprint with enhanced validation."""
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")
        
        blueprint = Blueprint(table_name)
        try:
            callback(blueprint)
        except Exception as e:
            raise RuntimeError(f"Error in table creation callback for '{table_name}': {e}") from e
        
        # Convert blueprint to SQLAlchemy table
        columns = [col.to_sqlalchemy_column() for col in blueprint.columns]
        table = Table(table_name, self._metadata, *columns)
        
        # Store for potential rollback
        self._tables_created.append(table_name)
        
        print(f"CREATE TABLE: {table_name}")
        for col in blueprint.columns:
            constraints = []
            if col.primary:
                constraints.append("PRIMARY KEY")
            if col.unique_flag:
                constraints.append("UNIQUE")
            if col.index_flag:
                constraints.append("INDEX")
            if col.foreign_key_ref:
                constraints.append(f"FOREIGN KEY -> {col.foreign_key_ref}")
            
            constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
            nullable_str = "NULL" if col.nullable_flag else "NOT NULL"
            default_str = f" DEFAULT {col.default_value}" if col.default_value is not None else ""
            
            print(f"  - {col.name}: {col.column_type}{constraint_str} {nullable_str}{default_str}")
        
        # Handle indexes
        for index in blueprint.indexes:
            print(f"  - INDEX {index['name']}: {', '.join(index['columns'])}")
        
        # Handle foreign keys
        for fk in blueprint.foreign_keys:
            print(f"  - FOREIGN KEY {fk['column']} -> {fk['reference_table']}.{fk['reference_column']} "
                  f"ON DELETE {fk['on_delete']} ON UPDATE {fk['on_update']}")
        
        # Handle unique constraints
        for constraint in blueprint.constraints:
            if constraint['type'] == 'unique':
                print(f"  - UNIQUE CONSTRAINT {constraint['name']}: {', '.join(constraint['columns'])}")
    
    def modify_table(self, table_name: TableName, callback: Callable[[Blueprint], None]) -> None:
        """Modify an existing table using Laravel 12-style Blueprint with validation."""
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")
        
        blueprint = Blueprint(table_name)
        try:
            callback(blueprint)
        except Exception as e:
            raise RuntimeError(f"Error in table modification callback for '{table_name}': {e}") from e
        
        print(f"MODIFY TABLE: {table_name}")
        
        # Handle new columns
        for col in blueprint.columns:
            print(f"  - ADD COLUMN {col.name}: {col.column_type}")
        
        # Handle commands (drop, rename, etc.)
        for command in blueprint.commands:
            if command['type'] == 'drop_column':
                print(f"  - DROP COLUMN {command['column']}")
            elif command['type'] == 'rename_column':
                print(f"  - RENAME COLUMN {command['old_name']} TO {command['new_name']}")
            elif command['type'] == 'drop_index':
                print(f"  - DROP INDEX {command['name']}")
    
    def drop_table(self, table_name: TableName) -> None:
        """Drop a table with validation."""
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")
        print(f"DROP TABLE: {table_name}")
    
    def drop_table_if_exists(self, table_name: TableName) -> None:
        """Drop a table if it exists with validation."""
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")
        print(f"DROP TABLE IF EXISTS: {table_name}")
    
    def has_table(self, table_name: TableName) -> bool:
        """Check if a table exists with type validation."""
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")
        # This would need actual database connection
        return True
    
    def has_column(self, table_name: TableName, column_name: ColumnName) -> bool:
        """Check if a column exists in a table with type validation."""
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")
        if not column_name or not isinstance(column_name, str):
            raise ValueError(f"Invalid column name: {column_name}")
        # This would need actual database connection  
        return True
    
    def rename_table(self, old_name: TableName, new_name: TableName) -> None:
        """Rename a table with validation."""
        if not old_name or not isinstance(old_name, str):
            raise ValueError(f"Invalid old table name: {old_name}")
        if not new_name or not isinstance(new_name, str):
            raise ValueError(f"Invalid new table name: {new_name}")
        if old_name == new_name:
            raise ValueError("Old and new table names cannot be the same")
        print(f"RENAME TABLE: {old_name} -> {new_name}")
    
    # Batch Operations
    
    def batch_start(self) -> None:
        """Start a batch operation."""
        self._batch_mode = True
        print("START BATCH OPERATION")
    
    def batch_end(self) -> None:
        """End a batch operation."""
        self._batch_mode = False
        print("END BATCH OPERATION")
    
    def batch_operation(self, callback: Callable[[], None]) -> None:
        """Execute operations in batch mode."""
        self.batch_start()
        try:
            callback()
        finally:
            self.batch_end()
    
    # Helper Methods
    
    def foreign_key_exists(self, table_name: TableName, foreign_key_name: str) -> bool:
        """Check if a foreign key exists with validation."""
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")
        if not foreign_key_name or not isinstance(foreign_key_name, str):
            raise ValueError(f"Invalid foreign key name: {foreign_key_name}")
        # This would need actual database inspection
        return True
    
    def index_exists(self, table_name: TableName, index_name: IndexName) -> bool:
        """Check if an index exists with validation."""
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")
        if not index_name or not isinstance(index_name, str):
            raise ValueError(f"Invalid index name: {index_name}")
        # This would need actual database inspection
        return True
    
    def get_column_type(self, table_name: TableName, column_name: ColumnName) -> str:
        """Get the type of a column with validation."""
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")
        if not column_name or not isinstance(column_name, str):
            raise ValueError(f"Invalid column name: {column_name}")
        # This would need actual database inspection
        return "unknown"
    
    def get_connection(self) -> Optional[str]:
        """Get the connection name for this migration."""
        return self.connection
    
    def set_connection(self, connection: str) -> Migration[T]:
        """Set the connection name for this migration with validation."""
        if not connection or not isinstance(connection, str):
            raise ValueError(f"Invalid connection name: {connection}")
        self.connection = connection
        return self
    
    # Laravel 12-style helper methods with enhanced validation
    
    def create(self, table_name: TableName, callback: Callable[[Blueprint], None]) -> None:
        """Laravel 12-style create method with validation."""
        self.create_table(table_name, callback)
    
    def table(self, table_name: TableName, callback: Callable[[Blueprint], None]) -> None:
        """Laravel 12-style table modification method with validation."""
        self.modify_table(table_name, callback)
    
    def drop(self, table_name: TableName) -> None:
        """Laravel 12-style drop method with validation."""
        self.drop_table(table_name)
    
    def drop_if_exists(self, table_name: TableName) -> None:
        """Laravel 12-style drop if exists method with validation."""
        self.drop_table_if_exists(table_name)
    
    def rename(self, old_name: TableName, new_name: TableName) -> None:
        """Laravel 12-style rename method with validation."""
        self.rename_table(old_name, new_name)
    
    def disable_foreign_key_checks(self) -> None:
        """Disable foreign key constraint checks."""
        print("DISABLE FOREIGN KEY CHECKS")
    
    def enable_foreign_key_checks(self) -> None:
        """Enable foreign key constraint checks."""
        print("ENABLE FOREIGN KEY CHECKS")
    
    def raw(self, sql: str) -> None:
        """Execute raw SQL."""
        print(f"RAW SQL: {sql}")
    
    def statement(self, sql: str) -> None:
        """Execute a SQL statement."""
        self.raw(sql)
    
    def unprepared(self, sql: str) -> None:
        """Execute unprepared SQL statement."""
        print(f"UNPREPARED SQL: {sql}")
    
    def seed(self, seeder_class: str) -> None:
        """Call a seeder from within migration."""
        print(f"SEEDING: {seeder_class}")
    
    def call_seeder(self, seeder: Union[str, Callable[[], None]]) -> None:
        """Call a seeder class or function."""
        if isinstance(seeder, str):
            self.seed(seeder)
        else:
            print("CALLING SEEDER FUNCTION")
            seeder()
    
    def when(self, condition: bool, callback: Callable[[], None]) -> None:
        """Conditionally execute migration operations."""
        if condition:
            callback()
    
    def unless(self, condition: bool, callback: Callable[[], None]) -> None:
        """Execute migration operations unless condition is true."""
        if not condition:
            callback()
    
    def when_environment(self, environments: Union[str, List[str]], callback: Callable[[], None]) -> None:
        """Execute operations only in specific environments with validation."""
        import os
        current_env = os.getenv('APP_ENV', 'production')
        
        if isinstance(environments, str):
            environments = [environments]
        
        if not environments or not all(isinstance(env, str) for env in environments):
            raise ValueError("Invalid environments list")
        
        if current_env in environments:
            try:
                callback()
            except Exception as e:
                raise RuntimeError(f"Error in environment-specific callback: {e}") from e
    
    def unless_environment(self, environments: Union[str, List[str]], callback: Callable[[], None]) -> None:
        """Execute operations unless in specific environments with validation."""
        import os
        current_env = os.getenv('APP_ENV', 'production')
        
        if isinstance(environments, str):
            environments = [environments]
        
        if not environments or not all(isinstance(env, str) for env in environments):
            raise ValueError("Invalid environments list")
        
        if current_env not in environments:
            try:
                callback()
            except Exception as e:
                raise RuntimeError(f"Error in environment-specific callback: {e}") from e
    
    def in_transaction(self, callback: Callable[[], None]) -> None:
        """Execute operations within a transaction."""
        print("BEGIN TRANSACTION")
        try:
            callback()
            print("COMMIT TRANSACTION")
        except Exception as e:
            print(f"ROLLBACK TRANSACTION: {e}")
            raise
    
    def without_foreign_key_checks(self, callback: Callable[[], None]) -> None:
        """Execute operations without foreign key checks."""
        self.disable_foreign_key_checks()
        try:
            callback()
        finally:
            self.enable_foreign_key_checks()


@final
class CreateTableMigration(Migration[T]):
    """Laravel 12-style base class for table creation migrations with enhanced safety."""
    
    def down(self) -> None:
        """Default down method drops the created table with validation."""
        table_name = self.get_table_name()
        if not table_name:
            raise RuntimeError("Cannot determine table name for rollback")
        self.drop_table_if_exists(table_name)


class RollbackOperation(TypedDict):
    """Type-safe rollback operation definition."""
    type: Literal['drop_added_column', 'add_dropped_column', 'rename_column_back', 'drop_index', 'add_index']
    column: Optional[ColumnName]
    old_name: Optional[str]
    new_name: Optional[str]
    definition: Optional[Dict[str, Any]]

@final
class ModifyTableMigration(Migration[T]):
    """Laravel 12-style base class for table modification migrations with enhanced rollback safety."""
    
    def __init__(self) -> None:
        super().__init__()
        self._rollback_operations: List[RollbackOperation] = []
    
    def add_rollback_operation(self, operation: RollbackOperation) -> None:
        """Add a rollback operation for the down method with validation."""
        if not isinstance(operation, dict) or 'type' not in operation:
            raise ValueError("Invalid rollback operation structure")
        self._rollback_operations.append(operation)
    
    def down(self) -> None:
        """Execute rollback operations in reverse order with enhanced error handling."""
        table_name = self.get_table_name()
        if not table_name:
            raise RuntimeError("Cannot determine table name for rollback")
        
        def rollback_callback(table: Blueprint) -> None:
            for operation in reversed(self._rollback_operations):
                try:
                    if operation['type'] == 'drop_added_column' and operation.get('column'):
                        table.drop_column(operation['column'])
                    elif operation['type'] == 'add_dropped_column':
                        # Restore the dropped column with its original definition
                        if operation.get('column_definition'):
                            col_def = operation['column_definition']
                            # Re-create the column based on its stored definition
                            if col_def.get('type') == 'string':
                                column = table.string(col_def['name'], col_def.get('length', 255))
                            elif col_def.get('type') == 'integer':
                                column = table.integer(col_def['name'])
                            elif col_def.get('type') == 'boolean':
                                column = table.boolean(col_def['name'])
                            elif col_def.get('type') == 'text':
                                column = table.text(col_def['name'])
                            elif col_def.get('type') == 'datetime':
                                column = table.datetime(col_def['name'])
                            else:
                                # Generic column type
                                column = table.add_column(col_def['name'], col_def.get('type', 'string'))
                            
                            # Apply modifiers
                            if col_def.get('nullable', True):
                                column.nullable()
                            if col_def.get('default') is not None:
                                column.default(col_def['default'])
                            if col_def.get('unique', False):
                                column.unique()
                            if col_def.get('index', False):
                                column.index()
                    elif operation['type'] == 'rename_column_back':
                        if operation.get('new_name') and operation.get('old_name'):
                            table.rename_column(operation['new_name'], operation['old_name'])
                except Exception as e:
                    raise RuntimeError(f"Error during rollback operation {operation['type']}: {e}") from e
        
        self.modify_table(table_name, rollback_callback)


# Laravel 12-style Migration Registry for tracking with enhanced type safety
class MigrationRegistry:
    """Registry to keep track of executed migrations with type safety."""
    
    _migrations: List[MigrationName] = []
    
    @classmethod
    def add_migration(cls, migration_name: MigrationName) -> None:
        """Add a migration to the registry with validation."""
        if not migration_name or not isinstance(migration_name, str):
            raise ValueError(f"Invalid migration name: {migration_name}")
        if migration_name not in cls._migrations:
            cls._migrations.append(migration_name)
    
    @classmethod
    def remove_migration(cls, migration_name: MigrationName) -> None:
        """Remove a migration from the registry with validation."""
        if not migration_name or not isinstance(migration_name, str):
            raise ValueError(f"Invalid migration name: {migration_name}")
        if migration_name in cls._migrations:
            cls._migrations.remove(migration_name)
    
    @classmethod
    def has_migration(cls, migration_name: MigrationName) -> bool:
        """Check if a migration has been executed with validation."""
        if not migration_name or not isinstance(migration_name, str):
            raise ValueError(f"Invalid migration name: {migration_name}")
        return migration_name in cls._migrations
    
    @classmethod
    def get_executed_migrations(cls) -> List[MigrationName]:
        """Get list of executed migrations."""
        return cls._migrations.copy()
    
    @classmethod
    def clear_registry(cls) -> None:
        """Clear the migration registry."""
        cls._migrations.clear()


# Laravel 12-style Migration Helpers with enhanced type safety
class MigrationHelper:
    """Helper class for common Laravel 12 migration patterns with strict typing."""
    
    @staticmethod
    def create_users_table(table: Blueprint) -> None:
        """Standard users table structure."""
        table.id()
        table.string('name')
        table.string('email').unique()
        table.timestamp('email_verified_at').nullable()
        table.string('password')
        table.remember_token()
        table.timestamps()
        
        # Add indexes
        table.index('email')
        table.index('name')
    
    @staticmethod
    def create_password_resets_table(table: Blueprint) -> None:
        """Standard password resets table."""
        table.string('email').index()
        table.string('token')
        table.timestamp('created_at').nullable()
        
        # Add composite index
        table.index(['email', 'token'])
    
    @staticmethod
    def create_failed_jobs_table(table: Blueprint) -> None:
        """Standard failed jobs table."""
        table.id()
        table.string('uuid').unique()
        table.text('connection')
        table.text('queue')
        table.text('payload')
        table.text('exception')
        table.timestamp('failed_at').default_current_timestamp()
    
    @staticmethod
    def create_personal_access_tokens_table(table: Blueprint) -> None:
        """Standard personal access tokens table (Laravel Sanctum)."""
        table.id()
        table.morphs('tokenable')
        table.string('name')
        table.string('token', 64).unique()
        table.text('abilities').nullable()
        table.timestamp('last_used_at').nullable()
        table.timestamps()
        
        # Add indexes
        table.index(['tokenable_type', 'tokenable_id'])
    
    @staticmethod
    def create_jobs_table(table: Blueprint) -> None:
        """Standard jobs queue table."""
        table.id()
        table.string('queue').index()
        table.text('payload')
        table.tiny_integer('attempts').unsigned_integer().default(0)
        table.integer('reserved_at').unsigned_integer().nullable()
        table.integer('available_at').unsigned_integer()
        table.integer('created_at').unsigned_integer()
        
        # Add indexes
        table.index(['queue'])
        table.index(['reserved_at'])
    
    @staticmethod
    def create_cache_table(table: Blueprint) -> None:
        """Standard cache table."""
        table.string('key').unique()
        table.text('value')
        table.integer('expiration')
        
        # Add index
        table.index('expiration')
    
    @staticmethod
    def create_sessions_table(table: Blueprint) -> None:
        """Standard sessions table."""
        table.string('id').unique()
        table.foreign_id('user_id').nullable().index()
        table.string('ip_address', 45).nullable()
        table.text('user_agent').nullable()
        table.text('payload')
        table.integer('last_activity').index()
    
    @staticmethod
    def add_soft_deletes(table: Blueprint) -> None:
        """Add soft delete column."""
        table.soft_deletes()
    
    @staticmethod
    def add_audit_columns(table: Blueprint) -> None:
        """Add standard audit columns."""
        table.audit_columns()
    
    @staticmethod
    def add_seo_columns(table: Blueprint) -> None:
        """Add SEO columns."""
        table.seo_columns()
    
    @staticmethod
    def add_status_columns(table: Blueprint) -> None:
        """Add status and publication columns."""
        table.status_columns()
    
    @staticmethod
    def add_tree_structure(table: Blueprint) -> None:
        """Add nested set model columns."""
        table.tree_columns()
    
    @staticmethod
    def add_polymorphic_columns(table: Blueprint, name: str) -> None:
        """Add polymorphic relationship columns."""
        table.morphs(name)
    
    @staticmethod
    def add_user_tracking(table: Blueprint) -> None:
        """Add user tracking columns."""
        table.user_stamps()
    
    @staticmethod
    def add_versioning(table: Blueprint) -> None:
        """Add version tracking columns."""
        table.versioning()
    
    @staticmethod
    def add_rating_system(table: Blueprint) -> None:
        """Add rating system columns."""
        table.rateable()
    
    @staticmethod
    def add_commenting_system(table: Blueprint) -> None:
        """Add comment system columns."""
        table.commentable()
    
    @staticmethod
    def create_pivot_table(table: Blueprint, table1: str, table2: str) -> None:
        """Create a standard pivot table."""
        # Sort table names alphabetically for consistency
        tables = sorted([table1, table2])
        singular1 = tables[0].rstrip('s')  # Simple singularization
        singular2 = tables[1].rstrip('s')
        
        table.id()
        table.foreign_id(f'{singular1}_id').constrained(tables[0]).cascade_on_delete()
        table.foreign_id(f'{singular2}_id').constrained(tables[1]).cascade_on_delete()
        table.timestamps()
        
        # Add unique constraint
        table.unique([f'{singular1}_id', f'{singular2}_id'])
    
    @staticmethod
    def create_taggables_table(table: Blueprint) -> None:
        """Create a taggables table for polymorphic tagging."""
        table.id()
        table.foreign_id('tag_id').constrained().cascade_on_delete()
        table.morphs('taggable')
        table.timestamps()
        
        # Add unique constraint
        table.unique(['tag_id', 'taggable_type', 'taggable_id'])
    
    @staticmethod
    def add_sortable_columns(table: Blueprint, column_name: str = 'sort_order') -> None:
        """Add sortable functionality."""
        table.sortable(column_name)
    
    @staticmethod
    def add_location_columns(table: Blueprint) -> None:
        """Add location-based columns."""
        table.decimal('latitude', precision=10, scale=8).nullable()
        table.decimal('longitude', precision=11, scale=8).nullable()
        table.string('address').nullable()
        table.string('city').nullable()
        table.string('state').nullable()
        table.string('country').nullable()
        table.string('postal_code').nullable()
        
        # Add spatial index for coordinates
        table.index(['latitude', 'longitude'])


# Global helper functions (Laravel 12-style) with type safety
def Schema() -> type[Schema]:
    """Get the Schema class for migrations with type safety."""
    from .Blueprint import Schema as SchemaClass
    return SchemaClass


# Laravel 12-style decorators for migrations with enhanced type safety
def migration_helper(func: Callable[..., None]) -> Callable[..., None]:
    """Decorator to add helper methods to migration with type validation."""
    def wrapper(self: Migration[T], *args: Any, **kwargs: Any) -> None:
        # Add helper methods to migration instance
        self.helper = MigrationHelper
        return func(self, *args, **kwargs)
    return wrapper


def transactional(func: Callable[..., None]) -> Callable[..., None]:
    """Decorator to run migration in transaction with error handling."""
    def wrapper(self: Migration[T], *args: Any, **kwargs: Any) -> None:
        try:
            self.in_transaction(lambda: func(self, *args, **kwargs))
        except Exception as e:
            raise RuntimeError(f"Transaction failed in {func.__name__}: {e}") from e
    return wrapper


def without_fk_checks(func: Callable[..., None]) -> Callable[..., None]:
    """Decorator to run migration without foreign key checks with validation."""
    def wrapper(self: Migration[T], *args: Any, **kwargs: Any) -> None:
        try:
            self.without_foreign_key_checks(lambda: func(self, *args, **kwargs))
        except Exception as e:
            raise RuntimeError(f"Foreign key check disable failed in {func.__name__}: {e}") from e
    return wrapper