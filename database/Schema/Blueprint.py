from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.sql import func
from datetime import datetime


class ColumnDefinition:
    """Represents a column definition in Laravel style."""
    
    def __init__(self, name: str, column_type: Any) -> None:
        self.name = name
        self.column_type = column_type
        self.nullable = False
        self.default_value: Any = None
        self.primary = False
        self.unique = False
        self.index = False
        self.foreign_key: Optional[str] = None
        self.comment: Optional[str] = None
        self.auto_increment = False
        self.length: Optional[int] = None
    
    def nullable_column(self) -> ColumnDefinition:
        """Make column nullable."""
        self.nullable = True
        return self
    
    def default(self, value: Any) -> ColumnDefinition:
        """Set default value."""
        self.default_value = value
        return self
    
    def primary_key(self) -> ColumnDefinition:
        """Make column primary key."""
        self.primary = True
        return self
    
    def unique_column(self) -> ColumnDefinition:
        """Make column unique."""
        self.unique = True
        return self
    
    def index_column(self) -> ColumnDefinition:
        """Add index to column."""
        self.index = True
        return self
    
    def references(self, table_column: str) -> ColumnDefinition:
        """Add foreign key reference."""
        self.foreign_key = table_column
        return self
    
    def comment_column(self, text: str) -> ColumnDefinition:
        """Add comment to column."""
        self.comment = text
        return self
    
    def auto_increment_column(self) -> ColumnDefinition:
        """Make column auto increment."""
        self.auto_increment = True
        return self
    
    def length_column(self, length: int) -> ColumnDefinition:
        """Set column length."""
        self.length = length
        return self
    
    def to_sqlalchemy_column(self) -> Column[Any]:
        """Convert to SQLAlchemy Column."""
        kwargs = {
            'nullable': self.nullable,
            'primary_key': self.primary,
            'unique': self.unique,
            'index': self.index,
            'comment': self.comment,
            'autoincrement': self.auto_increment
        }
        
        if self.default_value is not None:
            kwargs['default'] = self.default_value
        
        if self.foreign_key:
            kwargs['ForeignKey'] = ForeignKey(self.foreign_key)
        
        # Handle column type with length
        if self.length and hasattr(self.column_type, '__call__'):
            column_type = self.column_type(self.length)
        else:
            column_type = self.column_type
        
        return Column(self.name, column_type, **kwargs)


class Blueprint:
    """Laravel-style database schema blueprint."""
    
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name
        self.columns: List[ColumnDefinition] = []
        self.indexes: List[Dict[str, Any]] = []
        self.foreign_keys: List[Dict[str, Any]] = []
        self.constraints: List[Dict[str, Any]] = []
        self.commands: List[Dict[str, Any]] = []
    
    # Column Types
    
    def id(self, name: str = "id") -> ColumnDefinition:
        """Create an auto-incrementing primary key column."""
        col = ColumnDefinition(name, String(26))  # ULID
        col.primary_key()
        self.columns.append(col)
        return col
    
    def string(self, name: str, length: int = 255) -> ColumnDefinition:
        """Create a string column."""
        col = ColumnDefinition(name, String(length))
        self.columns.append(col)
        return col
    
    def text(self, name: str) -> ColumnDefinition:
        """Create a text column."""
        col = ColumnDefinition(name, Text)
        self.columns.append(col)
        return col
    
    def integer(self, name: str) -> ColumnDefinition:
        """Create an integer column."""
        col = ColumnDefinition(name, Integer)
        self.columns.append(col)
        return col
    
    def boolean(self, name: str) -> ColumnDefinition:
        """Create a boolean column."""
        col = ColumnDefinition(name, Boolean)
        self.columns.append(col)
        return col
    
    def datetime(self, name: str) -> ColumnDefinition:
        """Create a datetime column."""
        col = ColumnDefinition(name, DateTime)
        self.columns.append(col)
        return col
    
    def timestamp(self, name: str) -> ColumnDefinition:
        """Create a timestamp column."""
        col = ColumnDefinition(name, DateTime)
        col.default(func.now())
        self.columns.append(col)
        return col
    
    def timestamps(self) -> None:
        """Add created_at and updated_at timestamps."""
        self.timestamp("created_at")
        self.timestamp("updated_at")
    
    def float_column(self, name: str, precision: int = 8, scale: int = 2) -> ColumnDefinition:
        """Create a float column."""
        col = ColumnDefinition(name, Float(precision=precision, scale=scale))
        self.columns.append(col)
        return col
    
    def json_column(self, name: str) -> ColumnDefinition:
        """Create a JSON column."""
        col = ColumnDefinition(name, JSON)
        self.columns.append(col)
        return col
    
    def foreign_id(self, name: str) -> ColumnDefinition:
        """Create a foreign ID column."""
        if not name.endswith("_id"):
            name += "_id"
        col = ColumnDefinition(name, String(26))  # ULID
        self.columns.append(col)
        return col
    
    # Indexes and Constraints
    
    def index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add an index."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'columns': columns,
            'name': name or f"idx_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def unique(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a unique constraint."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.constraints.append({
            'type': 'unique',
            'columns': columns,
            'name': name or f"unq_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def foreign(self, column: str) -> ForeignKeyDefinition:
        """Add a foreign key constraint."""
        return ForeignKeyDefinition(self, column)
    
    def drop_column(self, column: str) -> Blueprint:
        """Drop a column."""
        self.commands.append({'type': 'drop_column', 'column': column})
        return self
    
    def drop_index(self, name: str) -> Blueprint:
        """Drop an index."""
        self.commands.append({'type': 'drop_index', 'name': name})
        return self
    
    def rename_column(self, old_name: str, new_name: str) -> Blueprint:
        """Rename a column."""
        self.commands.append({'type': 'rename_column', 'old_name': old_name, 'new_name': new_name})
        return self


class ForeignKeyDefinition:
    """Foreign key constraint definition."""
    
    def __init__(self, blueprint: Blueprint, column: str) -> None:
        self.blueprint = blueprint
        self.column = column
        self.reference_table: Optional[str] = None
        self.reference_column: str = "id"
        self.on_delete_action: str = "RESTRICT"
        self.on_update_action: str = "CASCADE"
    
    def references(self, column: str) -> ForeignKeyDefinition:
        """Set the referenced column."""
        self.reference_column = column
        return self
    
    def on(self, table: str) -> ForeignKeyDefinition:
        """Set the referenced table."""
        self.reference_table = table
        return self
    
    def on_delete(self, action: str) -> ForeignKeyDefinition:
        """Set the ON DELETE action."""
        self.on_delete_action = action
        return self
    
    def on_update(self, action: str) -> ForeignKeyDefinition:
        """Set the ON UPDATE action."""
        self.on_update_action = action
        return self
    
    def cascade_on_delete(self) -> ForeignKeyDefinition:
        """Set CASCADE on delete."""
        return self.on_delete("CASCADE")
    
    def set_null_on_delete(self) -> ForeignKeyDefinition:
        """Set SET NULL on delete."""
        return self.on_delete("SET NULL")
    
    def restrict_on_delete(self) -> ForeignKeyDefinition:
        """Set RESTRICT on delete."""
        return self.on_delete("RESTRICT")
    
    def finalize(self) -> Blueprint:
        """Finalize the foreign key and add to blueprint."""
        if self.reference_table:
            self.blueprint.foreign_keys.append({
                'column': self.column,
                'reference_table': self.reference_table,
                'reference_column': self.reference_column,
                'on_delete': self.on_delete_action,
                'on_update': self.on_update_action
            })
        return self.blueprint


class Schema:
    """Laravel-style Schema facade."""
    
    @staticmethod
    def create(table_name: str, callback: Callable[[Blueprint], None]) -> Blueprint:
        """Create a new table."""
        blueprint = Blueprint(table_name)
        callback(blueprint)
        
        # Here you would execute the DDL
        print(f"Creating table: {table_name}")
        for col in blueprint.columns:
            print(f"  - Column: {col.name} ({col.column_type})")
        
        return blueprint
    
    @staticmethod
    def table(table_name: str, callback: Callable[[Blueprint], None]) -> Blueprint:
        """Modify an existing table."""
        blueprint = Blueprint(table_name)
        callback(blueprint)
        
        # Here you would execute the ALTER DDL
        print(f"Modifying table: {table_name}")
        for command in blueprint.commands:
            print(f"  - Command: {command}")
        
        return blueprint
    
    @staticmethod
    def drop(table_name: str) -> None:
        """Drop a table."""
        print(f"Dropping table: {table_name}")
    
    @staticmethod
    def drop_if_exists(table_name: str) -> None:
        """Drop a table if it exists."""
        print(f"Dropping table if exists: {table_name}")
    
    @staticmethod
    def has_table(table_name: str) -> bool:
        """Check if a table exists."""
        # This would need actual database inspection
        return True
    
    @staticmethod
    def has_column(table_name: str, column_name: str) -> bool:
        """Check if a column exists."""
        # This would need actual database inspection
        return True
    
    @staticmethod
    def rename(old_name: str, new_name: str) -> None:
        """Rename a table."""
        print(f"Renaming table: {old_name} -> {new_name}")