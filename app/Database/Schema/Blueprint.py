from __future__ import annotations

from typing import List, Dict, Any, Optional, Union
from enum import Enum


class ColumnType(Enum):
    """Column types enum."""
    STRING = 'string'
    TEXT = 'text'
    INTEGER = 'integer'
    BIGINT = 'bigint'
    FLOAT = 'float'
    DECIMAL = 'decimal'
    BOOLEAN = 'boolean'
    DATE = 'date'
    DATETIME = 'datetime'
    TIMESTAMP = 'timestamp'
    TIME = 'time'
    JSON = 'json'
    BINARY = 'binary'
    UUID = 'uuid'


class Column:
    """Represents a database column."""
    
    def __init__(
        self, 
        name: str, 
        column_type: ColumnType, 
        length: Optional[int] = None,
        precision: Optional[int] = None,
        scale: Optional[int] = None
    ) -> None:
        self.name = name
        self.type = column_type
        self.length = length
        self.precision = precision
        self.scale = scale
        self.nullable = True
        self.default: Optional[Any] = None
        self.primary = False
        self.unique = False
        self.index = False
        self.auto_increment = False
        self.comment: Optional[str] = None
        self.references_table: Optional[str] = None
        self.references_column: Optional[str] = None
        self.on_delete: Optional[str] = None
        self.on_update: Optional[str] = None
    
    def nullable_flag(self, nullable: bool = True) -> 'Column':
        """Set nullable flag."""
        self.nullable = nullable
        return self
    
    def not_null(self) -> 'Column':
        """Set column as not nullable."""
        return self.nullable_flag(False)
    
    def default_value(self, value: Any) -> 'Column':
        """Set default value."""
        self.default = value
        return self
    
    def primary_key(self) -> 'Column':
        """Set column as primary key."""
        self.primary = True
        self.nullable = False
        return self
    
    def unique_constraint(self) -> 'Column':
        """Add unique constraint."""
        self.unique = True
        return self
    
    def index_column(self) -> 'Column':
        """Add index to column."""
        self.index = True
        return self
    
    def auto_increment_flag(self) -> 'Column':
        """Set auto increment."""
        self.auto_increment = True
        return self
    
    def comment_text(self, comment: str) -> 'Column':
        """Add comment."""
        self.comment = comment
        return self
    
    def foreign_references(
        self, 
        table: str, 
        column: str = 'id',
        on_delete: Optional[str] = None,
        on_update: Optional[str] = None
    ) -> 'Column':
        """Add foreign key reference."""
        self.references_table = table
        self.references_column = column
        self.on_delete = on_delete
        self.on_update = on_update
        return self
    
    def to_sql(self) -> str:
        """Convert column to SQL."""
        sql_parts = [self.name]
        
        # Add type
        if self.type == ColumnType.STRING:
            length = self.length or 255
            sql_parts.append(f"VARCHAR({length})")
        elif self.type == ColumnType.TEXT:
            sql_parts.append("TEXT")
        elif self.type == ColumnType.INTEGER:
            sql_parts.append("INTEGER")
        elif self.type == ColumnType.BIGINT:
            sql_parts.append("BIGINT")
        elif self.type == ColumnType.FLOAT:
            sql_parts.append("FLOAT")
        elif self.type == ColumnType.DECIMAL:
            precision = self.precision or 10
            scale = self.scale or 2
            sql_parts.append(f"DECIMAL({precision},{scale})")
        elif self.type == ColumnType.BOOLEAN:
            sql_parts.append("BOOLEAN")
        elif self.type == ColumnType.DATE:
            sql_parts.append("DATE")
        elif self.type == ColumnType.DATETIME:
            sql_parts.append("DATETIME")
        elif self.type == ColumnType.TIMESTAMP:
            sql_parts.append("TIMESTAMP")
        elif self.type == ColumnType.TIME:
            sql_parts.append("TIME")
        elif self.type == ColumnType.JSON:
            sql_parts.append("JSON")
        elif self.type == ColumnType.BINARY:
            sql_parts.append("BLOB")
        elif self.type == ColumnType.UUID:
            sql_parts.append("VARCHAR(36)")
        
        # Add constraints
        if self.primary:
            sql_parts.append("PRIMARY KEY")
        
        if self.auto_increment:
            sql_parts.append("AUTOINCREMENT")
        
        if not self.nullable:
            sql_parts.append("NOT NULL")
        
        if self.unique:
            sql_parts.append("UNIQUE")
        
        if self.default is not None:
            if isinstance(self.default, str):
                sql_parts.append(f"DEFAULT '{self.default}'")
            else:
                sql_parts.append(f"DEFAULT {self.default}")
        
        return ' '.join(sql_parts)


class Index:
    """Represents a database index."""
    
    def __init__(self, name: str, columns: List[str], unique: bool = False) -> None:
        self.name = name
        self.columns = columns
        self.unique = unique
    
    def to_sql(self, table_name: str) -> str:
        """Convert index to SQL."""
        unique_str = "UNIQUE " if self.unique else ""
        columns_str = ', '.join(self.columns)
        return f"CREATE {unique_str}INDEX {self.name} ON {table_name} ({columns_str})"


class ForeignKey:
    """Represents a foreign key constraint."""
    
    def __init__(
        self, 
        name: str,
        columns: List[str],
        references_table: str,
        references_columns: List[str],
        on_delete: Optional[str] = None,
        on_update: Optional[str] = None
    ) -> None:
        self.name = name
        self.columns = columns
        self.references_table = references_table
        self.references_columns = references_columns
        self.on_delete = on_delete
        self.on_update = on_update
    
    def to_sql(self, table_name: str) -> str:
        """Convert foreign key to SQL."""
        columns_str = ', '.join(self.columns)
        ref_columns_str = ', '.join(self.references_columns)
        
        sql = f"ALTER TABLE {table_name} ADD CONSTRAINT {self.name} FOREIGN KEY ({columns_str}) REFERENCES {self.references_table}({ref_columns_str})"
        
        if self.on_delete:
            sql += f" ON DELETE {self.on_delete}"
        if self.on_update:
            sql += f" ON UPDATE {self.on_update}"
        
        return sql


class Blueprint:
    """Laravel-style database table blueprint."""
    
    def __init__(self, table_name: str, alter: bool = False) -> None:
        self.table_name = table_name
        self.alter = alter
        self.columns: List[Column] = []
        self.indexes: List[Index] = []
        self.foreign_keys: List[ForeignKey] = []
        self.drop_columns: List[str] = []
        self.drop_indexes: List[str] = []
        self.drop_foreign_keys: List[str] = []
    
    # Column creation methods
    def id(self, name: str = 'id') -> Column:
        """Add auto-incrementing ID column."""
        column = Column(name, ColumnType.INTEGER)
        column.primary_key().auto_increment_flag()
        self.columns.append(column)
        return column
    
    def string(self, name: str, length: int = 255) -> Column:
        """Add string column."""
        column = Column(name, ColumnType.STRING, length=length)
        self.columns.append(column)
        return column
    
    def text(self, name: str) -> Column:
        """Add text column."""
        column = Column(name, ColumnType.TEXT)
        self.columns.append(column)
        return column
    
    def integer(self, name: str) -> Column:
        """Add integer column."""
        column = Column(name, ColumnType.INTEGER)
        self.columns.append(column)
        return column
    
    def big_integer(self, name: str) -> Column:
        """Add big integer column."""
        column = Column(name, ColumnType.BIGINT)
        self.columns.append(column)
        return column
    
    def float_column(self, name: str) -> Column:
        """Add float column."""
        column = Column(name, ColumnType.FLOAT)
        self.columns.append(column)
        return column
    
    def decimal(self, name: str, precision: int = 10, scale: int = 2) -> Column:
        """Add decimal column."""
        column = Column(name, ColumnType.DECIMAL, precision=precision, scale=scale)
        self.columns.append(column)
        return column
    
    def boolean(self, name: str) -> Column:
        """Add boolean column."""
        column = Column(name, ColumnType.BOOLEAN)
        self.columns.append(column)
        return column
    
    def date(self, name: str) -> Column:
        """Add date column."""
        column = Column(name, ColumnType.DATE)
        self.columns.append(column)
        return column
    
    def datetime(self, name: str) -> Column:
        """Add datetime column."""
        column = Column(name, ColumnType.DATETIME)
        self.columns.append(column)
        return column
    
    def timestamp(self, name: str) -> Column:
        """Add timestamp column."""
        column = Column(name, ColumnType.TIMESTAMP)
        self.columns.append(column)
        return column
    
    def time(self, name: str) -> Column:
        """Add time column."""
        column = Column(name, ColumnType.TIME)
        self.columns.append(column)
        return column
    
    def json(self, name: str) -> Column:
        """Add JSON column."""
        column = Column(name, ColumnType.JSON)
        self.columns.append(column)
        return column
    
    def binary(self, name: str) -> Column:
        """Add binary column."""
        column = Column(name, ColumnType.BINARY)
        self.columns.append(column)
        return column
    
    def uuid(self, name: str) -> Column:
        """Add UUID column."""
        column = Column(name, ColumnType.UUID)
        self.columns.append(column)
        return column
    
    # Special Laravel columns
    def timestamps(self, created_at: str = 'created_at', updated_at: str = 'updated_at') -> None:
        """Add created_at and updated_at timestamps."""
        self.timestamp(created_at).default_value('CURRENT_TIMESTAMP')
        self.timestamp(updated_at).default_value('CURRENT_TIMESTAMP')
    
    def soft_deletes(self, column: str = 'deleted_at') -> Column:
        """Add soft delete timestamp."""
        return self.timestamp(column).nullable_flag()
    
    def foreign_id(self, name: str) -> Column:
        """Add foreign ID column."""
        return self.big_integer(name).index_column()
    
    def morph_columns(self, name: str) -> None:
        """Add polymorphic columns."""
        self.string(f"{name}_type")
        self.big_integer(f"{name}_id")
    
    # Index methods
    def index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> None:
        """Add index."""
        if isinstance(columns, str):
            columns = [columns]
        
        if name is None:
            name = f"idx_{self.table_name}_{'_'.join(columns)}"
        
        index = Index(name, columns)
        self.indexes.append(index)
    
    def unique(self, columns: Union[str, List[str]], name: Optional[str] = None) -> None:
        """Add unique index."""
        if isinstance(columns, str):
            columns = [columns]
        
        if name is None:
            name = f"unq_{self.table_name}_{'_'.join(columns)}"
        
        index = Index(name, columns, unique=True)
        self.indexes.append(index)
    
    def foreign(self, columns: Union[str, List[str]], name: Optional[str] = None) -> 'ForeignKeyBuilder':
        """Add foreign key."""
        if isinstance(columns, str):
            columns = [columns]
        
        if name is None:
            name = f"fk_{self.table_name}_{'_'.join(columns)}"
        
        return ForeignKeyBuilder(self, name, columns)
    
    # Drop methods
    def drop_column(self, *columns: str) -> None:
        """Drop columns."""
        self.drop_columns.extend(columns)
    
    def drop_index(self, name: str) -> None:
        """Drop index."""
        self.drop_indexes.append(name)
    
    def drop_foreign(self, name: str) -> None:
        """Drop foreign key."""
        self.drop_foreign_keys.append(name)
    
    def to_sql(self) -> str:
        """Convert blueprint to SQL."""
        if self.alter:
            return self._generate_alter_sql()
        else:
            return self._generate_create_sql()
    
    def _generate_create_sql(self) -> str:
        """Generate CREATE TABLE SQL."""
        if not self.columns:
            return ""
        
        column_definitions = [col.to_sql() for col in self.columns]
        sql = f"CREATE TABLE {self.table_name} (\n    " + ",\n    ".join(column_definitions) + "\n)"
        
        return sql
    
    def _generate_alter_sql(self) -> str:
        """Generate ALTER TABLE SQL."""
        statements = []
        
        # Add columns
        for column in self.columns:
            statements.append(f"ALTER TABLE {self.table_name} ADD COLUMN {column.to_sql()}")
        
        # Drop columns
        for column_name in self.drop_columns:
            statements.append(f"ALTER TABLE {self.table_name} DROP COLUMN {column_name}")
        
        # Drop indexes
        for index_name in self.drop_indexes:
            statements.append(f"DROP INDEX {index_name}")
        
        # Drop foreign keys
        for fk_name in self.drop_foreign_keys:
            statements.append(f"ALTER TABLE {self.table_name} DROP CONSTRAINT {fk_name}")
        
        # Add indexes
        for index in self.indexes:
            statements.append(index.to_sql(self.table_name))
        
        # Add foreign keys
        for fk in self.foreign_keys:
            statements.append(fk.to_sql(self.table_name))
        
        return ";\n".join(statements)


class ForeignKeyBuilder:
    """Builder for foreign key constraints."""
    
    def __init__(self, blueprint: Blueprint, name: str, columns: List[str]) -> None:
        self.blueprint = blueprint
        self.name = name
        self.columns = columns
        self.references_table: Optional[str] = None
        self.references_columns: List[str] = []
        self.on_delete_action: Optional[str] = None
        self.on_update_action: Optional[str] = None
    
    def references(self, columns: Union[str, List[str]]) -> 'ForeignKeyBuilder':
        """Set referenced columns."""
        if isinstance(columns, str):
            columns = [columns]
        self.references_columns = columns
        return self
    
    def on(self, table: str) -> 'ForeignKeyBuilder':
        """Set referenced table."""
        self.references_table = table
        return self
    
    def on_delete(self, action: str) -> 'ForeignKeyBuilder':
        """Set on delete action."""
        self.on_delete_action = action
        return self
    
    def on_update(self, action: str) -> 'ForeignKeyBuilder':
        """Set on update action."""
        self.on_update_action = action
        return self
    
    def cascade(self) -> 'ForeignKeyBuilder':
        """Set cascade for both delete and update."""
        return self.on_delete('CASCADE').on_update('CASCADE')
    
    def restrict(self) -> 'ForeignKeyBuilder':
        """Set restrict for both delete and update."""
        return self.on_delete('RESTRICT').on_update('RESTRICT')
    
    def set_null(self) -> 'ForeignKeyBuilder':
        """Set SET NULL for delete."""
        return self.on_delete('SET NULL')
    
    def __del__(self) -> None:
        """Finalize the foreign key when builder is destroyed."""
        if self.references_table and self.references_columns:
            fk = ForeignKey(
                self.name,
                self.columns,
                self.references_table,
                self.references_columns,
                self.on_delete_action,
                self.on_update_action
            )
            self.blueprint.foreign_keys.append(fk)