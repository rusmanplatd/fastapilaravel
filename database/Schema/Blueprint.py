from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic, final, Literal, TypedDict, Protocol
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.types import Float, JSON
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.sql import func
from datetime import datetime

# Laravel 12 enhanced type definitions
ColumnType = Union[str, type]
DefaultValue = Union[str, int, float, bool, None, Callable[[], Any]]
ConstraintType = Literal['unique', 'check', 'foreign_key', 'primary_key', 'index']
IndexType = Literal['btree', 'hash', 'gin', 'gist', 'spgist', 'brin', 'fulltext', 'spatial']

class ColumnModifiers(TypedDict, total=False):
    """Type-safe column modifiers for Laravel 12."""
    nullable: bool
    default: DefaultValue
    unique: bool
    index: bool
    primary: bool
    auto_increment: bool
    comment: Optional[str]
    length: Optional[int]
    precision: Optional[int]
    scale: Optional[int]

class IndexDefinition(TypedDict):
    """Type-safe index definition."""
    name: str
    columns: List[str]
    type: Optional[IndexType]
    unique: bool
    where: Optional[str]

class ConstraintDefinition(TypedDict):
    """Type-safe constraint definition."""
    name: str
    type: ConstraintType
    columns: List[str]
    expression: Optional[str]
    reference_table: Optional[str]
    reference_column: Optional[str]

T = TypeVar('T', bound='Blueprint')


@final
class ColumnDefinition:
    """Represents a column definition in Laravel 12 style with enhanced type safety."""
    
    def __init__(self, name: str, column_type: ColumnType) -> None:
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid column name: {name}")
        
        self.name: str = name
        self.column_type: ColumnType = column_type
        self._nullable: bool = False
        self.default_value: DefaultValue = None
        self._primary: bool = False
        self._unique: bool = False
        self._index: bool = False
        self._foreign_key: Optional[str] = None
        self.comment: Optional[str] = None
        self.auto_increment: bool = False
        self.length: Optional[int] = None
        self.precision: Optional[int] = None
        self.scale: Optional[int] = None
        self._modifiers: ColumnModifiers = {}
    
    @property
    def nullable_flag(self) -> bool:
        return self._nullable
    
    @property
    def primary(self) -> bool:
        return self._primary
    
    @property
    def unique_flag(self) -> bool:
        return self._unique
    
    @property
    def index_flag(self) -> bool:
        return self._index
    
    @property
    def foreign_key_ref(self) -> Optional[str]:
        return self._foreign_key
    
    def nullable(self, nullable: bool = True) -> ColumnDefinition:
        """Make column nullable with validation."""
        if not isinstance(nullable, bool):
            raise ValueError(f"Nullable must be a boolean, got {type(nullable)}")
        self._nullable = nullable
        self._modifiers['nullable'] = nullable
        return self
    
    def default(self, value: DefaultValue) -> ColumnDefinition:
        """Set default value with type validation."""
        self.default_value = value
        self._modifiers['default'] = value
        return self
    
    def primary_key(self) -> ColumnDefinition:
        """Make column primary key."""
        self._primary = True
        self._modifiers['primary'] = True
        return self
    
    def unique(self) -> ColumnDefinition:
        """Make column unique."""
        self._unique = True
        self._modifiers['unique'] = True
        return self
    
    def index(self) -> ColumnDefinition:
        """Add index to column."""
        self._index = True
        self._modifiers['index'] = True
        return self
    
    def foreign_key(self, reference: str, on_delete: Literal["RESTRICT", "CASCADE", "SET NULL", "NO ACTION"] = "RESTRICT") -> ColumnDefinition:
        """Add foreign key reference with validation."""
        if not reference or not isinstance(reference, str):
            raise ValueError(f"Invalid foreign key reference: {reference}")
        self._foreign_key = reference
        return self
    
    def default_current_timestamp(self) -> ColumnDefinition:
        """Set default to current timestamp."""
        self.default_value = func.now()
        return self
    
    def comment_column(self, text: str) -> ColumnDefinition:
        """Add comment to column with validation."""
        if not isinstance(text, str):
            raise ValueError(f"Comment must be a string, got {type(text)}")
        self.comment = text
        self._modifiers['comment'] = text
        return self
    
    def auto_increment_column(self) -> ColumnDefinition:
        """Make column auto increment."""
        self.auto_increment = True
        self._modifiers['auto_increment'] = True
        return self
    
    def length_column(self, length: int) -> ColumnDefinition:
        """Set column length with validation."""
        if not isinstance(length, int) or length <= 0:
            raise ValueError(f"Length must be a positive integer, got {length}")
        self.length = length
        self._modifiers['length'] = length
        return self
    
    def to_sqlalchemy_column(self) -> Column:
        """Convert to SQLAlchemy Column."""
        kwargs = {
            'nullable': self._nullable,
            'primary_key': self._primary,
            'unique': self._unique,
            'index': self._index,
            'comment': self.comment,
            'autoincrement': self.auto_increment
        }
        
        if self.default_value is not None:
            kwargs['default'] = self.default_value
        
        if self._foreign_key:
            kwargs['ForeignKey'] = ForeignKey(self._foreign_key)  # type: ignore[assignment]
        
        # Handle column type with length
        if self.length and hasattr(self.column_type, '__call__'):
            column_type = self.column_type(self.length)
        else:
            column_type = self.column_type
        
        return Column(self.name, column_type, **kwargs)  # type: ignore[arg-type]


@final
class Blueprint(Generic[T]):
    """Laravel 12-style database schema blueprint with enhanced type safety."""
    
    def __init__(self, table_name: str) -> None:
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")
        
        self.table_name: str = table_name
        self.columns: List[ColumnDefinition] = []
        self.indexes: List[IndexDefinition] = []
        self.foreign_keys: List[Dict[str, Any]] = []  # Will be typed later
        self.constraints: List[ConstraintDefinition] = []
        self.commands: List[Dict[str, Any]] = []  # Will be typed later
        self._table_options: Dict[str, Any] = {}
    
    # Column Types
    
    def id(self, name: str = "id") -> ColumnDefinition:
        """Create an auto-incrementing primary key column with validation."""
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid column name: {name}")
        
        col = ColumnDefinition(name, String(26))  # ULID
        col.primary_key()
        self.columns.append(col)
        return col
    
    def string(self, name: str, length: int = 255) -> ColumnDefinition:
        """Create a string column with validation."""
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid column name: {name}")
        if not isinstance(length, int) or length <= 0:
            raise ValueError(f"Length must be a positive integer, got {length}")
        
        col = ColumnDefinition(name, String(length))
        self.columns.append(col)
        return col
    
    def text(self, name: str) -> ColumnDefinition:
        """Create a text column with validation."""
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid column name: {name}")
        
        col = ColumnDefinition(name, Text)
        self.columns.append(col)
        return col
    
    def integer(self, name: str) -> ColumnDefinition:
        """Create an integer column with validation."""
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid column name: {name}")
        
        col = ColumnDefinition(name, Integer)
        self.columns.append(col)
        return col
    
    def boolean(self, name: str) -> ColumnDefinition:
        """Create a boolean column with validation."""
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid column name: {name}")
        
        col = ColumnDefinition(name, Boolean)
        self.columns.append(col)
        return col
    
    def datetime(self, name: str) -> ColumnDefinition:
        """Create a datetime column with validation."""
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid column name: {name}")
        
        col = ColumnDefinition(name, DateTime)
        self.columns.append(col)
        return col
    
    def timestamp(self, name: str) -> ColumnDefinition:
        """Create a timestamp column with validation."""
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid column name: {name}")
        
        col = ColumnDefinition(name, DateTime)
        self.columns.append(col)
        return col
    
    def timestamps(self) -> List[ColumnDefinition]:
        """Add created_at and updated_at timestamps."""
        created_at = self.timestamp("created_at").nullable().default(func.now())
        updated_at = self.timestamp("updated_at").nullable().default(func.now())
        return [created_at, updated_at]
    
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
    
    def add_index(self, columns: Union[str, List[str]], name: Optional[str] = None, index_type: Optional[IndexType] = None) -> Blueprint[T]:
        """Add an index with validation."""
        if isinstance(columns, str):
            columns = [columns]
        
        if not columns or not all(isinstance(col, str) for col in columns):
            raise ValueError(f"Invalid columns for index: {columns}")
        
        index_def: IndexDefinition = {
            'name': name or f"idx_{self.table_name}_{'_'.join(columns)}",
            'columns': columns,
            'type': index_type,
            'unique': False,
            'where': None
        }
        
        self.indexes.append(index_def)
        return self
    
    def add_unique(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint[T]:
        """Add a unique constraint with validation."""
        if isinstance(columns, str):
            columns = [columns]
        
        if not columns or not all(isinstance(col, str) for col in columns):
            raise ValueError(f"Invalid columns for unique constraint: {columns}")
        
        constraint_def: ConstraintDefinition = {
            'name': name or f"unq_{self.table_name}_{'_'.join(columns)}",
            'type': 'unique',
            'columns': columns,
            'expression': None,
            'reference_table': None,
            'reference_column': None
        }
        
        self.constraints.append(constraint_def)
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
    
    def index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add an index (method for use in table callbacks)."""
        return self.add_index(columns, name)
    
    def unique(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a unique constraint (method for use in table callbacks)."""
        return self.add_unique(columns, name)
    
    def foreign_key(self, column: str, references_table: str, references_column: str = "id", on_delete: str = "RESTRICT") -> Blueprint:
        """Add a foreign key constraint directly."""
        self.foreign_keys.append({
            'column': column,
            'reference_table': references_table,
            'reference_column': references_column,
            'on_delete': on_delete,
            'on_update': 'CASCADE'
        })
        return self
    
    # Column Modification Methods (Laravel-style)
    
    def add_column(self, column_type: str, name: str, **kwargs: Any) -> ColumnDefinition:
        """Add a column to the table."""
        if column_type == "string":
            length = kwargs.get("length", 255)
            col = ColumnDefinition(name, String(length))
        elif column_type == "integer":
            col = ColumnDefinition(name, Integer)
        elif column_type == "boolean":
            col = ColumnDefinition(name, Boolean)
        elif column_type == "text":
            col = ColumnDefinition(name, Text)
        elif column_type == "datetime":
            col = ColumnDefinition(name, DateTime)
        elif column_type == "timestamp":
            col = ColumnDefinition(name, DateTime)
        elif column_type == "json":
            col = ColumnDefinition(name, JSON)
        else:
            raise ValueError(f"Unknown column type: {column_type}")
        
        # Apply modifiers
        if kwargs.get("nullable", True):
            col.nullable()
        if kwargs.get("default") is not None:
            col.default(kwargs["default"])
        if kwargs.get("unique", False):
            col.unique()
        if kwargs.get("index", False):
            col.index()
        
        self.columns.append(col)
        return col
    
    def change_column(self, column_name: str, column_type: str, **kwargs: Any) -> Blueprint:
        """Modify an existing column."""
        self.commands.append({
            'type': 'change_column',
            'column': column_name,
            'column_type': column_type,
            'options': kwargs
        })
        return self
    
    def rename_column_to(self, old_name: str, new_name: str) -> Blueprint:
        """Rename a column."""
        return self.rename_column(old_name, new_name)
    
    def drop_column_if_exists(self, *columns: str) -> Blueprint:
        """Drop columns if they exist."""
        for column in columns:
            self.commands.append({'type': 'drop_column_if_exists', 'column': column})
        return self
    
    def modify_column(self, column_name: str) -> ColumnModifier:
        """Start modifying a column."""
        return ColumnModifier(self, column_name)
    
    # Index Management
    
    def drop_index_if_exists(self, index_name: str) -> Blueprint:
        """Drop index if it exists."""
        self.commands.append({'type': 'drop_index_if_exists', 'name': index_name})
        return self
    
    def drop_unique(self, columns: Union[str, List[str]]) -> Blueprint:
        """Drop unique constraint."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.commands.append({'type': 'drop_unique', 'columns': columns})
        return self
    
    def drop_foreign(self, column: str) -> Blueprint:
        """Drop foreign key constraint."""
        self.commands.append({'type': 'drop_foreign', 'column': column})
        return self
    
    # Laravel-specific column types
    
    def big_integer(self, name: str) -> ColumnDefinition:
        """Create a big integer column."""
        from sqlalchemy import BigInteger
        col = ColumnDefinition(name, BigInteger)
        self.columns.append(col)
        return col
    
    def small_integer(self, name: str) -> ColumnDefinition:
        """Create a small integer column."""
        from sqlalchemy import SmallInteger
        col = ColumnDefinition(name, SmallInteger)
        self.columns.append(col)
        return col
    
    def tiny_integer(self, name: str) -> ColumnDefinition:
        """Create a tiny integer column."""
        from sqlalchemy import SmallInteger  # SQLAlchemy doesn't have TinyInteger
        col = ColumnDefinition(name, SmallInteger)
        self.columns.append(col)
        return col
    
    def unsigned_integer(self, name: str) -> ColumnDefinition:
        """Create an unsigned integer column."""
        from sqlalchemy.dialects.mysql import INTEGER
        col = ColumnDefinition(name, INTEGER(unsigned=True))
        self.columns.append(col)
        return col
    
    def decimal(self, name: str, precision: int = 8, scale: int = 2) -> ColumnDefinition:
        """Create a decimal column."""
        from sqlalchemy import Numeric
        col = ColumnDefinition(name, Numeric(precision=precision, scale=scale))
        self.columns.append(col)
        return col
    
    def double(self, name: str) -> ColumnDefinition:
        """Create a double column."""
        from sqlalchemy import Float
        col = ColumnDefinition(name, Float(precision=53))
        self.columns.append(col)
        return col
    
    def char(self, name: str, length: int = 1) -> ColumnDefinition:
        """Create a char column."""
        from sqlalchemy import CHAR
        col = ColumnDefinition(name, CHAR(length))
        self.columns.append(col)
        return col
    
    def binary(self, name: str, length: Optional[int] = None) -> ColumnDefinition:
        """Create a binary column."""
        from sqlalchemy import LargeBinary
        col = ColumnDefinition(name, LargeBinary(length) if length else LargeBinary)
        self.columns.append(col)
        return col
    
    def uuid(self, name: str) -> ColumnDefinition:
        """Create a UUID column."""
        from sqlalchemy.dialects.postgresql import UUID
        col = ColumnDefinition(name, UUID(as_uuid=True))
        self.columns.append(col)
        return col
    
    def enum(self, name: str, values: List[str]) -> ColumnDefinition:
        """Create an enum column."""
        from sqlalchemy import Enum
        col = ColumnDefinition(name, Enum(*values, name=f"{name}_enum"))
        self.columns.append(col)
        return col
    
    def date(self, name: str) -> ColumnDefinition:
        """Create a date column."""
        from sqlalchemy import Date
        col = ColumnDefinition(name, Date)
        self.columns.append(col)
        return col
    
    def time(self, name: str) -> ColumnDefinition:
        """Create a time column."""
        from sqlalchemy import Time
        col = ColumnDefinition(name, Time)
        self.columns.append(col)
        return col
    
    def datetime_tz(self, name: str) -> ColumnDefinition:
        """Create a datetime with timezone column."""
        from sqlalchemy.dialects.postgresql import TIMESTAMP
        col = ColumnDefinition(name, TIMESTAMP(timezone=True))
        self.columns.append(col)
        return col
    
    def soft_deletes(self) -> ColumnDefinition:
        """Add soft delete column."""
        return self.timestamp("deleted_at").nullable()
    
    def remember_token(self) -> ColumnDefinition:
        """Add remember token column for Laravel authentication."""
        return self.string("remember_token", 100).nullable()
    
    # Advanced Laravel Column Types
    
    def morphs(self, name: str) -> List[ColumnDefinition]:
        """Add polymorphic columns (type and id)."""
        columns = []
        columns.append(self.string(f"{name}_type").nullable(False).index())
        columns.append(self.string(f"{name}_id", 36).nullable(False).index())
        
        # Add composite index for polymorphic relationship
        self.index([f"{name}_type", f"{name}_id"], f"idx_{self.table_name}_{name}")
        
        return columns
    
    def nullable_morphs(self, name: str) -> List[ColumnDefinition]:
        """Add nullable polymorphic columns."""
        columns = []
        columns.append(self.string(f"{name}_type").nullable().index())
        columns.append(self.string(f"{name}_id", 36).nullable().index())
        
        self.index([f"{name}_type", f"{name}_id"], f"idx_{self.table_name}_{name}")
        
        return columns
    
    def uuid_morphs(self, name: str) -> List[ColumnDefinition]:
        """Add UUID polymorphic columns."""
        columns = []
        columns.append(self.string(f"{name}_type").nullable(False).index())
        columns.append(self.uuid(f"{name}_id").nullable(False).index())
        
        self.index([f"{name}_type", f"{name}_id"], f"idx_{self.table_name}_{name}")
        
        return columns
    
    def nullable_uuid_morphs(self, name: str) -> List[ColumnDefinition]:
        """Add nullable UUID polymorphic columns."""
        columns = []
        columns.append(self.string(f"{name}_type").nullable().index())
        columns.append(self.uuid(f"{name}_id").nullable().index())
        
        self.index([f"{name}_type", f"{name}_id"], f"idx_{self.table_name}_{name}")
        
        return columns
    
    def ip_address(self, name: str = "ip_address") -> ColumnDefinition:
        """Create an IP address column."""
        return self.string(name, 45).nullable(False)  # IPv6 compatible
    
    def mac_address(self, name: str = "mac_address") -> ColumnDefinition:
        """Create a MAC address column."""
        return self.string(name, 17).nullable(False)
    
    def year(self, name: str) -> ColumnDefinition:
        """Create a year column."""
        from sqlalchemy.dialects.mysql import YEAR
        col = ColumnDefinition(name, YEAR)
        self.columns.append(col)
        return col
    
    def geometry(self, name: str) -> ColumnDefinition:
        """Create a geometry column."""
        from sqlalchemy.dialects.mysql import GEOMETRY
        col = ColumnDefinition(name, GEOMETRY)
        self.columns.append(col)
        return col
    
    def point(self, name: str) -> ColumnDefinition:
        """Create a point geometry column."""
        from sqlalchemy.dialects.mysql import POINT
        col = ColumnDefinition(name, POINT)
        self.columns.append(col)
        return col
    
    def line_string(self, name: str) -> ColumnDefinition:
        """Create a line string geometry column."""
        from sqlalchemy.dialects.mysql import LINESTRING
        col = ColumnDefinition(name, LINESTRING)
        self.columns.append(col)
        return col
    
    def polygon(self, name: str) -> ColumnDefinition:
        """Create a polygon geometry column."""
        from sqlalchemy.dialects.mysql import POLYGON
        col = ColumnDefinition(name, POLYGON)
        self.columns.append(col)
        return col
    
    def multi_point(self, name: str) -> ColumnDefinition:
        """Create a multi-point geometry column."""
        from sqlalchemy.dialects.mysql import MULTIPOINT
        col = ColumnDefinition(name, MULTIPOINT)
        self.columns.append(col)
        return col
    
    def multi_line_string(self, name: str) -> ColumnDefinition:
        """Create a multi-line string geometry column."""
        from sqlalchemy.dialects.mysql import MULTILINESTRING
        col = ColumnDefinition(name, MULTILINESTRING)
        self.columns.append(col)
        return col
    
    def multi_polygon(self, name: str) -> ColumnDefinition:
        """Create a multi-polygon geometry column."""
        from sqlalchemy.dialects.mysql import MULTIPOLYGON
        col = ColumnDefinition(name, MULTIPOLYGON)
        self.columns.append(col)
        return col
    
    def geometry_collection(self, name: str) -> ColumnDefinition:
        """Create a geometry collection column."""
        from sqlalchemy.dialects.mysql import GEOMETRYCOLLECTION
        col = ColumnDefinition(name, GEOMETRYCOLLECTION)
        self.columns.append(col)
        return col
    
    # Computed and Generated Columns
    
    def computed(self, name: str, expression: str) -> ColumnDefinition:
        """Create a computed column."""
        from sqlalchemy import text
        col = ColumnDefinition(name, String)  # Placeholder type
        col.computed_expression = expression
        self.columns.append(col)
        return col
    
    def virtual_as(self, name: str, expression: str) -> ColumnDefinition:
        """Create a virtual generated column."""
        return self.computed(name, expression)
    
    def stored_as(self, name: str, expression: str) -> ColumnDefinition:
        """Create a stored generated column."""
        col = self.computed(name, expression)
        col.stored = True
        return col
    
    # Advanced Index Types
    
    def fulltext(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a fulltext index."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'fulltext',
            'columns': columns,
            'name': name or f"fulltext_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def spatial_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a spatial index."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'spatial',
            'columns': columns,
            'name': name or f"spatial_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def gin_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a GIN index (PostgreSQL)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'gin',
            'columns': columns,
            'name': name or f"gin_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def gist_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a GiST index (PostgreSQL)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'gist',
            'columns': columns,
            'name': name or f"gist_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def hash_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a hash index (PostgreSQL)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'hash',
            'columns': columns,
            'name': name or f"hash_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def partial_index(self, columns: Union[str, List[str]], condition: str, name: Optional[str] = None) -> Blueprint:
        """Add a partial index with condition."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'partial',
            'columns': columns,
            'condition': condition,
            'name': name or f"partial_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    # Advanced Constraints
    
    def check(self, constraint: str, name: Optional[str] = None) -> Blueprint:
        """Add a check constraint."""
        self.constraints.append({
            'type': 'check',
            'constraint': constraint,
            'name': name or f"chk_{self.table_name}_{len(self.constraints)}"
        })
        return self
    
    def exclusion(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add an exclusion constraint (PostgreSQL)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.constraints.append({
            'type': 'exclusion',
            'columns': columns,
            'name': name or f"excl_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    # JSON and Array Columns
    
    def json_array(self, name: str) -> ColumnDefinition:
        """Create a JSON array column."""
        from sqlalchemy.dialects.postgresql import JSONB, ARRAY
        col = ColumnDefinition(name, JSONB)
        self.columns.append(col)
        return col
    
    def array(self, name: str, base_type: str = "string") -> ColumnDefinition:
        """Create an array column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import ARRAY
        
        if base_type == "string":
            array_type = ARRAY(String)
        elif base_type == "integer":
            array_type = ARRAY(Integer)
        elif base_type == "boolean":
            array_type = ARRAY(Boolean)
        else:
            array_type = ARRAY(String)  # Default fallback
        
        col = ColumnDefinition(name, array_type)
        self.columns.append(col)
        return col
    
    def jsonb(self, name: str) -> ColumnDefinition:
        """Create a JSONB column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import JSONB
        col = ColumnDefinition(name, JSONB)
        self.columns.append(col)
        return col
    
    # Laravel-specific Features
    
    def user_stamps(self) -> List[ColumnDefinition]:
        """Add created_by and updated_by columns."""
        columns = []
        columns.append(self.string("created_by", 36).nullable())
        columns.append(self.string("updated_by", 36).nullable())
        
        # Add foreign key constraints to users table
        self.foreign_key("created_by", "users", "id", on_delete="SET NULL")
        self.foreign_key("updated_by", "users", "id", on_delete="SET NULL")
        
        return columns
    
    def audit_columns(self) -> List[ColumnDefinition]:
        """Add comprehensive audit columns."""
        columns = []
        columns.extend(self.timestamps())
        columns.extend(self.user_stamps())
        columns.append(self.string("created_ip", 45).nullable())
        columns.append(self.string("updated_ip", 45).nullable())
        columns.append(self.string("user_agent").nullable())
        
        return columns
    
    def tree_columns(self) -> List[ColumnDefinition]:
        """Add nested set model columns."""
        columns = []
        columns.append(self.integer("lft").nullable(False).default(0))
        columns.append(self.integer("rgt").nullable(False).default(0))
        columns.append(self.integer("depth").nullable(False).default(0))
        columns.append(self.string("parent_id", 36).nullable().index())
        
        return columns
    
    def seo_columns(self) -> List[ColumnDefinition]:
        """Add SEO-related columns."""
        columns = []
        columns.append(self.string("slug").unique().index())
        columns.append(self.string("meta_title").nullable())
        columns.append(self.text("meta_description").nullable())
        columns.append(self.text("meta_keywords").nullable())
        columns.append(self.string("canonical_url").nullable())
        
        return columns
    
    def status_columns(self) -> List[ColumnDefinition]:
        """Add status and publication columns."""
        columns = []
        columns.append(self.enum("status", ["draft", "published", "archived"]).default("draft"))
        columns.append(self.timestamp("published_at").nullable())
        columns.append(self.timestamp("archived_at").nullable())
        columns.append(self.boolean("is_featured").default(False))
        
        return columns
    
    def sortable(self, column_name: str = "sort_order") -> ColumnDefinition:
        """Add sortable column."""
        return self.integer(column_name).default(0).nullable(False).index()
    
    def commentable(self) -> List[ColumnDefinition]:
        """Add comment-related columns."""
        columns = []
        columns.append(self.boolean("allow_comments").default(True))
        columns.append(self.integer("comments_count").default(0))
        
        return columns
    
    def rateable(self) -> List[ColumnDefinition]:
        """Add rating columns."""
        columns = []
        columns.append(self.decimal("rating_avg", precision=3, scale=2).default(0))
        columns.append(self.integer("rating_count").default(0))
        columns.append(self.integer("rating_sum").default(0))
        
        return columns
    
    def versioning(self) -> List[ColumnDefinition]:
        """Add version tracking columns."""
        columns = []
        columns.append(self.integer("version").default(1).nullable(False))
        columns.append(self.string("version_notes").nullable())
        columns.append(self.boolean("is_current_version").default(True))
        
        return columns
    
    # Database-specific Methods
    
    def mysql_engine(self, engine: str = "InnoDB") -> Blueprint:
        """Set MySQL table engine."""
        self.table_options = getattr(self, 'table_options', {})
        self.table_options['mysql_engine'] = engine
        return self
    
    def mysql_charset(self, charset: str = "utf8mb4") -> Blueprint:
        """Set MySQL table charset."""
        self.table_options = getattr(self, 'table_options', {})
        self.table_options['mysql_charset'] = charset
        return self
    
    def mysql_collation(self, collation: str = "utf8mb4_unicode_ci") -> Blueprint:
        """Set MySQL table collation."""
        self.table_options = getattr(self, 'table_options', {})
        self.table_options['mysql_collation'] = collation
        return self
    
    def comment_table(self, comment: str) -> Blueprint:
        """Add table comment."""
        self.table_options = getattr(self, 'table_options', {})
        self.table_options['comment'] = comment
        return self
    
    # Utility Methods
    
    def when(self, condition: bool, callback: Callable[[Blueprint], None]) -> Blueprint:
        """Conditionally execute blueprint operations."""
        if condition:
            callback(self)
        return self
    
    def unless(self, condition: bool, callback: Callable[[Blueprint], None]) -> Blueprint:
        """Execute blueprint operations unless condition is true."""
        if not condition:
            callback(self)
        return self
    
    def tap(self, callback: Callable[[Blueprint], None]) -> Blueprint:
        """Execute callback and return blueprint."""
        callback(self)
        return self


class ColumnModifier:
    """Provides fluent interface for column modifications."""
    
    def __init__(self, blueprint: Blueprint, column_name: str) -> None:
        self.blueprint = blueprint
        self.column_name = column_name
        self.changes: Dict[str, Any] = {}
    
    def nullable(self, nullable: bool = True) -> ColumnModifier:
        """Make column nullable."""
        self.changes['nullable'] = nullable
        return self
    
    def default(self, value: Any) -> ColumnModifier:
        """Set default value."""
        self.changes['default'] = value
        return self
    
    def change(self) -> Blueprint:
        """Apply changes to column."""
        self.blueprint.commands.append({
            'type': 'modify_column',
            'column': self.column_name,
            'changes': self.changes
        })
        return self.blueprint


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


# ========================================================================================
# Enhanced Blueprint with All Advanced Features Merged
# ========================================================================================

# Additional imports for advanced features
from typing import TypeVar, Generic, final, Literal, TypedDict, Protocol
from datetime import datetime, timedelta
from enum import Enum
import re

# Advanced type definitions
class TablePartitionType(Enum):
    """Database table partitioning types."""
    RANGE = "RANGE"
    LIST = "LIST" 
    HASH = "HASH"
    KEY = "KEY"

class DatabaseEngine(Enum):
    """Database engine types."""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    MSSQL = "mssql"

class CompressionType(Enum):
    """Table compression types."""
    NONE = "NONE"
    ROW = "ROW"
    PAGE = "PAGE"
    ZLIB = "ZLIB"
    LZ4 = "LZ4"

class EncryptionLevel(Enum):
    """Table encryption levels."""
    NONE = "NONE"
    COLUMN = "COLUMN"
    TABLESPACE = "TABLESPACE"
    TDE = "TDE"  # Transparent Data Encryption


# Enhanced Blueprint class with all advanced features
class ExtendedBlueprint(Blueprint):
    """Extended Blueprint with all database features merged."""
    
    def __init__(self, table_name: str, engine: DatabaseEngine = DatabaseEngine.MYSQL) -> None:
        super().__init__(table_name)
        self.engine = engine
        self.partitions: List[Dict[str, Any]] = []
        self.table_encryption: EncryptionLevel = EncryptionLevel.NONE
        self.compression: CompressionType = CompressionType.NONE
        self.triggers: List[Dict[str, Any]] = []
        self.views: List[Dict[str, Any]] = []
        self.procedures: List[Dict[str, Any]] = []
        self.sequences: List[Dict[str, Any]] = []
        self.materialized_views: List[Dict[str, Any]] = []
        
    # ========================================================================================
    # Advanced Column Types
    # ========================================================================================
    
    def vector(self, name: str, dimensions: int = 1536) -> ColumnDefinition:
        """Create a vector column for AI/ML embeddings (PostgreSQL pgvector)."""
        from sqlalchemy import String
        col = ColumnDefinition(name, String)
        col.vector_dimensions = dimensions
        col.comment_column(f"Vector column with {dimensions} dimensions")
        self.columns.append(col)
        return col
    
    def ltree(self, name: str) -> ColumnDefinition:
        """Create an ltree column for hierarchical data (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import LTREE
        col = ColumnDefinition(name, LTREE)
        self.columns.append(col)
        return col
    
    def citext(self, name: str) -> ColumnDefinition:
        """Create a case-insensitive text column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import CITEXT
        col = ColumnDefinition(name, CITEXT)
        self.columns.append(col)
        return col
    
    def inet(self, name: str) -> ColumnDefinition:
        """Create an IP network column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import INET
        col = ColumnDefinition(name, INET)
        self.columns.append(col)
        return col
    
    def macaddr(self, name: str) -> ColumnDefinition:
        """Create a MAC address column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import MACADDR
        col = ColumnDefinition(name, MACADDR)
        self.columns.append(col)
        return col
    
    def tsquery(self, name: str) -> ColumnDefinition:
        """Create a text search query column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import TSQUERY
        col = ColumnDefinition(name, TSQUERY)
        self.columns.append(col)
        return col
    
    def tsvector(self, name: str) -> ColumnDefinition:
        """Create a text search vector column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import TSVECTOR
        col = ColumnDefinition(name, TSVECTOR)
        self.columns.append(col)
        return col
    
    def money(self, name: str) -> ColumnDefinition:
        """Create a money column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import MONEY
        col = ColumnDefinition(name, MONEY)
        self.columns.append(col)
        return col
    
    def interval(self, name: str) -> ColumnDefinition:
        """Create an interval column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import INTERVAL
        col = ColumnDefinition(name, INTERVAL)
        self.columns.append(col)
        return col
    
    def bit(self, name: str, length: int = 1) -> ColumnDefinition:
        """Create a bit column."""
        from sqlalchemy.dialects.mysql import BIT
        col = ColumnDefinition(name, BIT(length))
        self.columns.append(col)
        return col
    
    def varbit(self, name: str, length: Optional[int] = None) -> ColumnDefinition:
        """Create a variable bit column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import BIT
        col = ColumnDefinition(name, BIT(length, varying=True))
        self.columns.append(col)
        return col
    
    def xml(self, name: str) -> ColumnDefinition:
        """Create an XML column."""
        from sqlalchemy.dialects.postgresql import XML
        col = ColumnDefinition(name, XML)
        self.columns.append(col)
        return col
    
    def hstore(self, name: str) -> ColumnDefinition:
        """Create an hstore column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import HSTORE
        col = ColumnDefinition(name, HSTORE)
        self.columns.append(col)
        return col
    
    def cidr(self, name: str) -> ColumnDefinition:
        """Create a CIDR network address column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import CIDR
        col = ColumnDefinition(name, CIDR)
        self.columns.append(col)
        return col
    
    def point(self, name: str) -> ColumnDefinition:
        """Create a geometric point column (PostgreSQL)."""
        from sqlalchemy import String
        col = ColumnDefinition(name, String)
        col.postgresql_type = "POINT"
        self.columns.append(col)
        return col
    
    def line(self, name: str) -> ColumnDefinition:
        """Create a geometric line column (PostgreSQL)."""
        from sqlalchemy import String
        col = ColumnDefinition(name, String)
        col.postgresql_type = "LINE"
        self.columns.append(col)
        return col
    
    def lseg(self, name: str) -> ColumnDefinition:
        """Create a line segment column (PostgreSQL)."""
        from sqlalchemy import String
        col = ColumnDefinition(name, String)
        col.postgresql_type = "LSEG"
        self.columns.append(col)
        return col
    
    def box(self, name: str) -> ColumnDefinition:
        """Create a rectangular box column (PostgreSQL)."""
        from sqlalchemy import String
        col = ColumnDefinition(name, String)
        col.postgresql_type = "BOX"
        self.columns.append(col)
        return col
    
    def path(self, name: str) -> ColumnDefinition:
        """Create a geometric path column (PostgreSQL)."""
        from sqlalchemy import String
        col = ColumnDefinition(name, String)
        col.postgresql_type = "PATH"
        self.columns.append(col)
        return col
    
    def polygon(self, name: str) -> ColumnDefinition:
        """Create a polygon column (PostgreSQL)."""
        from sqlalchemy import String
        col = ColumnDefinition(name, String)
        col.postgresql_type = "POLYGON"
        self.columns.append(col)
        return col
    
    def circle(self, name: str) -> ColumnDefinition:
        """Create a circle column (PostgreSQL)."""
        from sqlalchemy import String
        col = ColumnDefinition(name, String)
        col.postgresql_type = "CIRCLE"
        self.columns.append(col)
        return col
    
    def int4range(self, name: str) -> ColumnDefinition:
        """Create an integer range column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import INT4RANGE
        col = ColumnDefinition(name, INT4RANGE)
        self.columns.append(col)
        return col
    
    def int8range(self, name: str) -> ColumnDefinition:
        """Create a bigint range column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import INT8RANGE
        col = ColumnDefinition(name, INT8RANGE)
        self.columns.append(col)
        return col
    
    def numrange(self, name: str) -> ColumnDefinition:
        """Create a numeric range column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import NUMRANGE
        col = ColumnDefinition(name, NUMRANGE)
        self.columns.append(col)
        return col
    
    def tsrange(self, name: str) -> ColumnDefinition:
        """Create a timestamp range column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import TSRANGE
        col = ColumnDefinition(name, TSRANGE)
        self.columns.append(col)
        return col
    
    def tstzrange(self, name: str) -> ColumnDefinition:
        """Create a timestamp with timezone range column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import TSTZRANGE
        col = ColumnDefinition(name, TSTZRANGE)
        self.columns.append(col)
        return col
    
    def daterange(self, name: str) -> ColumnDefinition:
        """Create a date range column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import DATERANGE
        col = ColumnDefinition(name, DATERANGE)
        self.columns.append(col)
        return col
    
    def macaddr8(self, name: str) -> ColumnDefinition:
        """Create an 8-byte MAC address column (PostgreSQL)."""
        from sqlalchemy.dialects.postgresql import MACADDR8
        col = ColumnDefinition(name, MACADDR8)
        self.columns.append(col)
        return col
    
    def pg_lsn(self, name: str) -> ColumnDefinition:
        """Create a PostgreSQL Log Sequence Number column (PostgreSQL)."""
        from sqlalchemy import String
        col = ColumnDefinition(name, String)
        col.postgresql_type = "PG_LSN"
        self.columns.append(col)
        return col
    
    def txid_snapshot(self, name: str) -> ColumnDefinition:
        """Create a transaction ID snapshot column (PostgreSQL)."""
        from sqlalchemy import String
        col = ColumnDefinition(name, String)
        col.postgresql_type = "TXID_SNAPSHOT"
        self.columns.append(col)
        return col
    
    def pg_snapshot(self, name: str) -> ColumnDefinition:
        """Create a snapshot column (PostgreSQL)."""
        from sqlalchemy import String
        col = ColumnDefinition(name, String)
        col.postgresql_type = "PG_SNAPSHOT"
        self.columns.append(col)
        return col
    
    # ========================================================================================
    # Specialized Business Columns
    # ========================================================================================
    
    def currency(self, name: str, precision: int = 19, scale: int = 4) -> ColumnDefinition:
        """Create a currency column with proper precision."""
        return self.decimal(name, precision=precision, scale=scale).comment_column("Currency amount")
    
    def percentage(self, name: str) -> ColumnDefinition:
        """Create a percentage column (0-100)."""
        col = self.decimal(name, precision=5, scale=2)
        self.check(f"{name} >= 0 AND {name} <= 100", f"chk_{name}_percentage")
        return col.comment_column("Percentage value (0-100)")
    
    def email(self, name: str = "email") -> ColumnDefinition:
        """Create an email column with validation."""
        col = self.string(name, 320)  # RFC 5321 maximum length
        self.check(f"{name} LIKE '%@%'", f"chk_{name}_format")
        return col.comment_column("Email address")
    
    def phone(self, name: str = "phone") -> ColumnDefinition:
        """Create a phone number column."""
        return self.string(name, 20).comment_column("Phone number in E.164 format")
    
    def url(self, name: str = "url") -> ColumnDefinition:
        """Create a URL column."""
        col = self.string(name, 2048)  # Maximum URL length
        self.check(f"{name} LIKE 'http%'", f"chk_{name}_format")
        return col.comment_column("URL address")
    
    def country_code(self, name: str = "country_code") -> ColumnDefinition:
        """Create a country code column (ISO 3166-1 alpha-2)."""
        return self.char(name, 2).comment_column("ISO 3166-1 alpha-2 country code")
    
    def language_code(self, name: str = "language_code") -> ColumnDefinition:
        """Create a language code column (ISO 639-1)."""
        return self.char(name, 2).comment_column("ISO 639-1 language code")
    
    def timezone_name(self, name: str = "timezone") -> ColumnDefinition:
        """Create a timezone column."""
        return self.string(name, 50).comment_column("IANA timezone identifier")
    
    def color_hex(self, name: str = "color") -> ColumnDefinition:
        """Create a color hex code column."""
        col = self.char(name, 7)  # #RRGGBB
        self.check(f"{name} ~ '^#[0-9A-Fa-f]{{6}}$'", f"chk_{name}_hex")
        return col.comment_column("Hex color code (#RRGGBB)")
    
    def slug(self, name: str = "slug", max_length: int = 100) -> ColumnDefinition:
        """Create a URL-friendly slug column."""
        col = self.string(name, max_length).unique().index()
        self.check(f"{name} ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'", f"chk_{name}_format")
        return col.comment_column("URL-friendly slug")
    
    def mime_type(self, name: str = "mime_type") -> ColumnDefinition:
        """Create a MIME type column."""
        return self.string(name, 100).comment_column("MIME type")
    
    def file_hash(self, name: str, algorithm: str = "sha256") -> ColumnDefinition:
        """Create a file hash column."""
        length_map = {"md5": 32, "sha1": 40, "sha256": 64, "sha512": 128}
        length = length_map.get(algorithm, 64)
        return self.char(name, length).comment_column(f"{algorithm.upper()} file hash")
    
    # ========================================================================================
    # Business Column Groups
    # ========================================================================================
    
    def money_columns(self, base_name: str = "amount") -> List[ColumnDefinition]:
        """Add comprehensive money handling columns."""
        columns = []
        columns.append(self.currency(f"{base_name}_cents"))  # Store in smallest unit
        columns.append(self.currency(f"{base_name}_display"))  # Display amount
        columns.append(self.char("currency_code", 3))  # ISO 4217 currency code
        columns.append(self.decimal("exchange_rate", precision=10, scale=6))
        columns.append(self.string("payment_method", 50).nullable())
        return columns
    
    def accounting_columns(self) -> List[ColumnDefinition]:
        """Add accounting-specific columns."""
        columns = []
        columns.append(self.string("account_code", 20))
        columns.append(self.enum("transaction_type", ["debit", "credit"]))
        columns.append(self.currency("debit_amount").nullable())
        columns.append(self.currency("credit_amount").nullable())
        columns.append(self.string("reference_number", 100))
        columns.append(self.text("description"))
        return columns
    
    def tax_columns(self) -> List[ColumnDefinition]:
        """Add tax calculation columns."""
        columns = []
        columns.append(self.currency("subtotal"))
        columns.append(self.currency("tax_amount"))
        columns.append(self.currency("total_amount"))
        columns.append(self.percentage("tax_rate"))
        columns.append(self.string("tax_type", 50))
        return columns
    
    def product_columns(self) -> List[ColumnDefinition]:
        """Add e-commerce product columns."""
        columns = []
        columns.append(self.string("sku", 100).unique())
        columns.append(self.string("barcode", 50).nullable())
        columns.append(self.currency("price"))
        columns.append(self.currency("cost_price").nullable())
        columns.append(self.integer("stock_quantity").default(0))
        columns.append(self.integer("reserved_quantity").default(0))
        columns.append(self.decimal("weight", precision=8, scale=3).nullable())
        columns.append(self.string("weight_unit", 10).default("kg"))
        columns.append(self.json_column("dimensions").nullable())
        columns.append(self.boolean("is_digital").default(False))
        columns.append(self.boolean("track_inventory").default(True))
        return columns
    
    def order_columns(self) -> List[ColumnDefinition]:
        """Add e-commerce order columns."""
        columns = []
        columns.append(self.string("order_number", 50).unique())
        columns.append(self.enum("status", ["pending", "processing", "shipped", "delivered", "cancelled"]))
        columns.extend(self.tax_columns())
        columns.append(self.currency("shipping_amount").default(0))
        columns.append(self.currency("discount_amount").default(0))
        columns.append(self.json_column("shipping_address"))
        columns.append(self.json_column("billing_address"))
        columns.append(self.timestamp("shipped_at").nullable())
        columns.append(self.timestamp("delivered_at").nullable())
        return columns
    
    def inventory_columns(self) -> List[ColumnDefinition]:
        """Add inventory management columns."""
        columns = []
        columns.append(self.integer("quantity_on_hand").default(0))
        columns.append(self.integer("quantity_reserved").default(0))
        columns.append(self.integer("quantity_available").computed("quantity_on_hand - quantity_reserved"))
        columns.append(self.integer("reorder_point").default(0))
        columns.append(self.integer("reorder_quantity").default(0))
        columns.append(self.string("location", 100).nullable())
        columns.append(self.string("bin_location", 50).nullable())
        return columns
    
    def cms_content_columns(self) -> List[ColumnDefinition]:
        """Add CMS content columns."""
        columns = []
        columns.append(self.string("title"))
        columns.append(self.text("content"))
        columns.append(self.text("excerpt").nullable())
        columns.extend(self.seo_columns())
        columns.extend(self.status_columns())
        columns.append(self.string("template", 100).nullable())
        columns.append(self.json_column("custom_fields").nullable())
        columns.append(self.integer("view_count").default(0))
        columns.append(self.boolean("is_sticky").default(False))
        return columns
    
    def media_columns(self) -> List[ColumnDefinition]:
        """Add media file columns."""
        columns = []
        columns.append(self.string("filename"))
        columns.append(self.string("original_filename"))
        columns.append(self.mime_type("mime_type"))
        columns.append(self.big_integer("file_size"))
        columns.append(self.file_hash("file_hash"))
        columns.append(self.string("disk", 50).default("local"))
        columns.append(self.string("path"))
        columns.append(self.json_column("metadata").nullable())
        columns.append(self.integer("width").nullable())
        columns.append(self.integer("height").nullable())
        columns.append(self.integer("duration").nullable())  # For video/audio
        return columns
    
    def blog_columns(self) -> List[ColumnDefinition]:
        """Add blog-specific columns."""
        columns = []
        columns.extend(self.cms_content_columns())
        columns.append(self.string("featured_image").nullable())
        columns.append(self.text("tags").nullable())
        columns.append(self.string("category", 100).nullable())
        columns.append(self.integer("reading_time").nullable())  # minutes
        columns.append(self.boolean("allow_comments").default(True))
        columns.append(self.integer("comments_count").default(0))
        columns.append(self.integer("likes_count").default(0))
        columns.append(self.integer("shares_count").default(0))
        return columns
    
    def location_columns(self, include_elevation: bool = False) -> List[ColumnDefinition]:
        """Add location/geographic columns."""
        columns = []
        columns.append(self.decimal("latitude", precision=10, scale=8))
        columns.append(self.decimal("longitude", precision=11, scale=8))
        
        if include_elevation:
            columns.append(self.decimal("elevation", precision=8, scale=3).nullable())
        
        columns.append(self.string("address").nullable())
        columns.append(self.string("city", 100).nullable())
        columns.append(self.string("state", 100).nullable())
        columns.append(self.string("postal_code", 20).nullable())
        columns.append(self.country_code("country_code").nullable())
        columns.append(self.point("coordinates").nullable())  # PostGIS point
        
        # Add spatial index for coordinates
        self.spatial_index(["coordinates"])
        
        return columns
    
    def geofencing_columns(self) -> List[ColumnDefinition]:
        """Add geofencing columns."""
        columns = []
        columns.append(self.string("fence_name"))
        columns.append(self.polygon("fence_polygon"))
        columns.append(self.decimal("radius", precision=10, scale=2).nullable())  # meters
        columns.append(self.boolean("is_active").default(True))
        columns.append(self.enum("fence_type", ["circular", "polygon"]))
        
        self.spatial_index(["fence_polygon"])
        
        return columns
    
    def tenant_columns(self) -> List[ColumnDefinition]:
        """Add multi-tenancy columns."""
        columns = []
        columns.append(self.string("tenant_id", 36).nullable(False).index())
        columns.append(self.string("tenant_type", 50).default("organization"))
        columns.append(self.json_column("tenant_config").nullable())
        
        # Add tenant foreign key
        self.foreign_key("tenant_id", "tenants", "id", on_delete="CASCADE")
        
        return columns
    
    def organization_columns(self) -> List[ColumnDefinition]:
        """Add organization structure columns."""
        columns = []
        columns.append(self.string("organization_id", 36).index())
        columns.append(self.string("department_id", 36).nullable().index())
        columns.append(self.string("team_id", 36).nullable().index())
        columns.append(self.string("project_id", 36).nullable().index())
        
        return columns
    
    def workflow_columns(self) -> List[ColumnDefinition]:
        """Add workflow state columns."""
        columns = []
        columns.append(self.string("workflow_state", 50).index())
        columns.append(self.string("previous_state", 50).nullable())
        columns.append(self.timestamp("state_changed_at").nullable())
        columns.append(self.string("state_changed_by", 36).nullable())
        columns.append(self.text("state_change_reason").nullable())
        columns.append(self.json_column("workflow_data").nullable())
        
        return columns
    
    def approval_columns(self) -> List[ColumnDefinition]:
        """Add approval workflow columns."""
        columns = []
        columns.append(self.enum("approval_status", ["pending", "approved", "rejected", "cancelled"]))
        columns.append(self.string("approved_by", 36).nullable())
        columns.append(self.timestamp("approved_at").nullable())
        columns.append(self.text("approval_notes").nullable())
        columns.append(self.integer("approval_level").default(1))
        columns.append(self.string("next_approver", 36).nullable())
        
        return columns
    
    def analytics_columns(self) -> List[ColumnDefinition]:
        """Add analytics tracking columns."""
        columns = []
        columns.append(self.big_integer("view_count").default(0))
        columns.append(self.big_integer("unique_views").default(0))
        columns.append(self.big_integer("click_count").default(0))
        columns.append(self.decimal("bounce_rate", precision=5, scale=2).default(0))
        columns.append(self.integer("avg_session_duration").default(0))  # seconds
        columns.append(self.timestamp("last_viewed_at").nullable())
        columns.append(self.json_column("utm_parameters").nullable())
        columns.append(self.string("referrer").nullable())
        
        return columns
    
    def performance_columns(self) -> List[ColumnDefinition]:
        """Add performance tracking columns."""
        columns = []
        columns.append(self.decimal("response_time", precision=8, scale=3).nullable())  # milliseconds
        columns.append(self.integer("memory_usage").nullable())  # bytes
        columns.append(self.integer("cpu_usage").nullable())  # percentage
        columns.append(self.decimal("throughput", precision=10, scale=2).nullable())  # requests/second
        columns.append(self.integer("error_count").default(0))
        columns.append(self.timestamp("last_error_at").nullable())
        
        return columns
    
    def user_stamps(self) -> List[ColumnDefinition]:
        """Add created_by and updated_by columns."""
        columns = []
        columns.append(self.string("created_by", 36).nullable())
        columns.append(self.string("updated_by", 36).nullable())
        
        # Add foreign key constraints to users table
        self.foreign_key("created_by", "users", "id", on_delete="SET NULL")
        self.foreign_key("updated_by", "users", "id", on_delete="SET NULL")
        
        return columns
    
    def audit_columns(self) -> List[ColumnDefinition]:
        """Add comprehensive audit columns."""
        columns = []
        columns.extend(self.timestamps())
        columns.extend(self.user_stamps())
        columns.append(self.string("created_ip", 45).nullable())
        columns.append(self.string("updated_ip", 45).nullable())
        columns.append(self.string("user_agent").nullable())
        
        return columns
    
    def tree_columns(self) -> List[ColumnDefinition]:
        """Add nested set model columns."""
        columns = []
        columns.append(self.integer("lft").nullable(False).default(0))
        columns.append(self.integer("rgt").nullable(False).default(0))
        columns.append(self.integer("depth").nullable(False).default(0))
        columns.append(self.string("parent_id", 36).nullable().index())
        
        return columns
    
    def versioning(self) -> List[ColumnDefinition]:
        """Add version tracking columns."""
        columns = []
        columns.append(self.integer("version").default(1).nullable(False))
        columns.append(self.string("version_notes").nullable())
        columns.append(self.boolean("is_current_version").default(True))
        
        return columns
    
    def rateable(self) -> List[ColumnDefinition]:
        """Add rating columns."""
        columns = []
        columns.append(self.decimal("rating_avg", precision=3, scale=2).default(0))
        columns.append(self.integer("rating_count").default(0))
        columns.append(self.integer("rating_sum").default(0))
        
        return columns
    
    def commentable(self) -> List[ColumnDefinition]:
        """Add comment-related columns."""
        columns = []
        columns.append(self.boolean("allow_comments").default(True))
        columns.append(self.integer("comments_count").default(0))
        
        return columns
    
    def sortable(self, column_name: str = "sort_order") -> ColumnDefinition:
        """Add sortable column."""
        return self.integer(column_name).default(0).nullable(False).index()
    
    # ========================================================================================
    # Advanced Indexing
    # ========================================================================================
    
    def fulltext(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a fulltext index."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'fulltext',
            'columns': columns,
            'name': name or f"fulltext_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def spatial_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a spatial index."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'spatial',
            'columns': columns,
            'name': name or f"spatial_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def gin_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a GIN index (PostgreSQL)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'gin',
            'columns': columns,
            'name': name or f"gin_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def gist_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a GiST index (PostgreSQL)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'gist',
            'columns': columns,
            'name': name or f"gist_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def hash_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a hash index (PostgreSQL)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'hash',
            'columns': columns,
            'name': name or f"hash_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def partial_index(self, columns: Union[str, List[str]], condition: str, name: Optional[str] = None) -> Blueprint:
        """Add a partial index with condition."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'partial',
            'columns': columns,
            'condition': condition,
            'name': name or f"partial_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def brin_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a BRIN (Block Range INdex) index (PostgreSQL)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'brin',
            'columns': columns,
            'name': name or f"brin_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def spgist_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add an SP-GiST (Space-Partitioned GiST) index (PostgreSQL)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'spgist',
            'columns': columns,
            'name': name or f"spgist_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def bloom_index(self, columns: Union[str, List[str]], name: Optional[str] = None, 
                   length: int = 80, col1: int = 2, col2: int = 2, col3: int = 4, col4: int = 4) -> Blueprint:
        """Add a Bloom filter index (PostgreSQL extension)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'bloom',
            'columns': columns,
            'name': name or f"bloom_{self.table_name}_{'_'.join(columns)}",
            'options': {
                'length': length,
                'col1': col1,
                'col2': col2,
                'col3': col3,
                'col4': col4
            }
        })
        return self
    
    def rum_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a RUM index (PostgreSQL extension)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'rum',
            'columns': columns,
            'name': name or f"rum_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def add_covering_index(self, key_columns: List[str], include_columns: List[str], 
                          name: Optional[str] = None) -> Blueprint:
        """Add covering index with included columns."""
        self.indexes.append({
            "type": "covering",
            "key_columns": key_columns,
            "include_columns": include_columns,
            "name": name or f"covering_{self.table_name}_{'_'.join(key_columns)}"
        })
        return self
    
    def add_clustered_index(self, columns: List[str], name: Optional[str] = None) -> Blueprint:
        """Add clustered index."""
        self.indexes.append({
            "type": "clustered",
            "columns": columns,
            "name": name or f"clustered_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def add_columnstore_index(self, columns: List[str], name: Optional[str] = None) -> Blueprint:
        """Add columnstore index for analytics."""
        self.indexes.append({
            "type": "columnstore",
            "columns": columns,
            "name": name or f"columnstore_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    # ========================================================================================
    # Table Partitioning
    # ========================================================================================
    
    def partition_by_range(self, column: str, partitions: List[Dict[str, Any]]) -> Blueprint:
        """Add range partitioning."""
        self.partitions.append({
            "type": TablePartitionType.RANGE,
            "column": column,
            "partitions": partitions
        })
        return self
    
    def partition_by_list(self, column: str, partitions: List[Dict[str, Any]]) -> Blueprint:
        """Add list partitioning."""
        self.partitions.append({
            "type": TablePartitionType.LIST,
            "column": column,
            "partitions": partitions
        })
        return self
    
    def partition_by_hash(self, column: str, partition_count: int) -> Blueprint:
        """Add hash partitioning."""
        self.partitions.append({
            "type": TablePartitionType.HASH,
            "column": column,
            "partition_count": partition_count
        })
        return self
    
    def partition_by_date(self, column: str, interval: str = "MONTH") -> Blueprint:
        """Add date-based partitioning."""
        partitions = []
        if interval == "MONTH":
            # Generate monthly partitions for the current year and next year
            import datetime
            current_year = datetime.datetime.now().year
            for year in [current_year, current_year + 1]:
                for month in range(1, 13):
                    start_date = f"{year}-{month:02d}-01"
                    if month == 12:
                        end_date = f"{year + 1}-01-01"
                    else:
                        end_date = f"{year}-{month + 1:02d}-01"
                    
                    partitions.append({
                        "name": f"p_{year}_{month:02d}",
                        "values": f"VALUES LESS THAN ('{end_date}')"
                    })
        
        return self.partition_by_range(column, partitions)
    
    def partition_by_expression(self, expression: str, partitions: List[Dict[str, Any]]) -> Blueprint:
        """Add partitioning by expression (PostgreSQL)."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            if not hasattr(self, 'partitions'):
                self.partitions = []
            self.partitions.append({
                'type': 'RANGE',
                'expression': expression,
                'partitions': partitions
            })
        return self
    
    def enable_native_partitioning(self) -> Blueprint:
        """Enable PostgreSQL native partitioning (10+)."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['native_partitioning'] = True
        return self
    
    def add_partition_pruning(self, enable: bool = True) -> Blueprint:
        """Enable/disable partition pruning (PostgreSQL)."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['enable_partition_pruning'] = enable
        return self
    
    def add_partition_wise_joins(self, enable: bool = True) -> Blueprint:
        """Enable partition-wise joins (PostgreSQL)."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['enable_partitionwise_join'] = enable
        return self
    
    def create_partition_of(self, parent_table: str, partition_bound: str) -> Blueprint:
        """Create a partition of an existing partitioned table (PostgreSQL)."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['partition_of'] = parent_table
            self.table_options['partition_bound'] = partition_bound
        return self
    
    def attach_partition(self, partition_table: str, partition_bound: str) -> Blueprint:
        """Attach a partition to this table (PostgreSQL)."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            if not hasattr(self, 'attached_partitions'):
                self.attached_partitions = []
            self.attached_partitions.append({
                'table': partition_table,
                'bound': partition_bound
            })
        return self
    
    def detach_partition(self, partition_table: str) -> Blueprint:
        """Detach a partition from this table (PostgreSQL)."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            if not hasattr(self, 'detached_partitions'):
                self.detached_partitions = []
            self.detached_partitions.append(partition_table)
        return self
    
    # ========================================================================================
    # Advanced Constraints
    # ========================================================================================
    
    def check(self, constraint: str, name: Optional[str] = None) -> Blueprint:
        """Add a check constraint."""
        self.constraints.append({
            'type': 'check',
            'constraint': constraint,
            'name': name or f"chk_{self.table_name}_{len(self.constraints)}"
        })
        return self
    
    def exclusion(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add an exclusion constraint (PostgreSQL)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.constraints.append({
            'type': 'exclusion',
            'columns': columns,
            'name': name or f"excl_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    # ========================================================================================
    # Database Triggers
    # ========================================================================================
    
    def add_trigger(self, name: str, timing: str, event: str, statement: str) -> Blueprint:
        """Add a database trigger."""
        self.triggers.append({
            "name": name,
            "timing": timing,  # BEFORE, AFTER, INSTEAD OF
            "event": event,    # INSERT, UPDATE, DELETE
            "statement": statement
        })
        return self
    
    def add_audit_trigger(self) -> Blueprint:
        """Add automatic audit trail trigger."""
        trigger_sql = f"""
        BEGIN
            INSERT INTO {self.table_name}_audit (
                table_name, operation, old_values, new_values, 
                changed_by, changed_at
            ) VALUES (
                '{self.table_name}', 
                TG_OP,
                CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
                CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW) ELSE NULL END,
                current_user,
                NOW()
            );
            RETURN COALESCE(NEW, OLD);
        END;
        """
        
        return self.add_trigger(
            f"{self.table_name}_audit_trigger",
            "AFTER",
            "INSERT OR UPDATE OR DELETE",
            trigger_sql
        )
    
    def add_updated_at_trigger(self) -> Blueprint:
        """Add automatic updated_at trigger."""
        trigger_sql = """
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        """
        
        return self.add_trigger(
            f"{self.table_name}_updated_at_trigger",
            "BEFORE",
            "UPDATE",
            trigger_sql
        )
    
    # ========================================================================================
    # Performance and Security
    # ========================================================================================
    
    def encrypt_table(self, level: EncryptionLevel = EncryptionLevel.TDE) -> Blueprint:
        """Enable table encryption."""
        self.table_encryption = level
        return self
    
    def encrypt_column(self, column_name: str, key_name: str = "default") -> Blueprint:
        """Encrypt specific column."""
        for col in self.columns:
            if col.name == column_name:
                col.encryption_key = key_name
                break
        return self
    
    def add_row_level_security(self, policy_name: str, policy_expression: str) -> Blueprint:
        """Add row-level security policy."""
        self.constraints.append({
            "type": "rls_policy",
            "name": policy_name,
            "expression": policy_expression
        })
        return self
    
    def compress_table(self, compression: CompressionType = CompressionType.ROW) -> Blueprint:
        """Enable table compression."""
        self.compression = compression
        return self
    
    def add_retention_policy(self, retention_days: int, date_column: str = "created_at") -> Blueprint:
        """Add data retention policy."""
        self.table_options = getattr(self, 'table_options', {})
        self.table_options['retention_policy'] = {
            "retention_days": retention_days,
            "date_column": date_column
        }
        return self
    
    def add_archival_policy(self, archive_after_days: int, archive_table: str, 
                           date_column: str = "created_at") -> Blueprint:
        """Add data archival policy."""
        self.table_options = getattr(self, 'table_options', {})
        self.table_options['archival_policy'] = {
            "archive_after_days": archive_after_days,
            "archive_table": archive_table,
            "date_column": date_column
        }
        return self
    
    # ========================================================================================
    # Database-specific Features
    # ========================================================================================
    
    def mysql_auto_increment_start(self, start_value: int) -> Blueprint:
        """Set MySQL auto increment start value."""
        if self.engine == DatabaseEngine.MYSQL:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['mysql_auto_increment'] = start_value
        return self
    
    def postgresql_inherits(self, parent_table: str) -> Blueprint:
        """Set PostgreSQL table inheritance."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['postgresql_inherits'] = parent_table
        return self
    
    def oracle_parallel(self, degree: int = 4) -> Blueprint:
        """Set Oracle parallel processing."""
        if self.engine == DatabaseEngine.ORACLE:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['oracle_parallel'] = degree
        return self
    
    # ========================================================================================
    # PostgreSQL Extensions Support
    # ========================================================================================
    
    def enable_extension(self, extension_name: str) -> Blueprint:
        """Enable PostgreSQL extension."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            if not hasattr(self, 'extensions'):
                self.extensions = []
            self.extensions.append(extension_name)
        return self
    
    def enable_uuid_extension(self) -> Blueprint:
        """Enable uuid-ossp extension for UUID generation."""
        return self.enable_extension('uuid-ossp')
    
    def enable_postgis(self) -> Blueprint:
        """Enable PostGIS extension for geographic data."""
        return self.enable_extension('postgis')
    
    def enable_hstore(self) -> Blueprint:
        """Enable hstore extension for key-value storage."""
        return self.enable_extension('hstore')
    
    def enable_pgcrypto(self) -> Blueprint:
        """Enable pgcrypto extension for encryption functions."""
        return self.enable_extension('pgcrypto')
    
    def enable_pg_trgm(self) -> Blueprint:
        """Enable pg_trgm extension for trigram matching."""
        return self.enable_extension('pg_trgm')
    
    def enable_unaccent(self) -> Blueprint:
        """Enable unaccent extension for text search."""
        return self.enable_extension('unaccent')
    
    def enable_btree_gin(self) -> Blueprint:
        """Enable btree_gin extension for GIN indexes on btree data types."""
        return self.enable_extension('btree_gin')
    
    def enable_btree_gist(self) -> Blueprint:
        """Enable btree_gist extension for GiST indexes on btree data types."""
        return self.enable_extension('btree_gist')
    
    def enable_pg_stat_statements(self) -> Blueprint:
        """Enable pg_stat_statements for query performance tracking."""
        return self.enable_extension('pg_stat_statements')
    
    def enable_pgvector(self) -> Blueprint:
        """Enable pgvector extension for vector similarity search."""
        return self.enable_extension('vector')
    
    def enable_timescaledb(self) -> Blueprint:
        """Enable TimescaleDB extension for time-series data."""
        return self.enable_extension('timescaledb')
    
    def enable_citus(self) -> Blueprint:
        """Enable Citus extension for distributed PostgreSQL."""
        return self.enable_extension('citus')
    
    def enable_pg_partman(self) -> Blueprint:
        """Enable pg_partman extension for partition management."""
        return self.enable_extension('pg_partman')
    
    def enable_postgres_fdw(self) -> Blueprint:
        """Enable postgres_fdw for foreign data wrapper."""
        return self.enable_extension('postgres_fdw')
    
    def enable_file_fdw(self) -> Blueprint:
        """Enable file_fdw for CSV file access."""
        return self.enable_extension('file_fdw')
    
    def enable_bloom(self) -> Blueprint:
        """Enable bloom extension for bloom filter indexes."""
        return self.enable_extension('bloom')
    
    def enable_rum(self) -> Blueprint:
        """Enable RUM extension for advanced text search."""
        return self.enable_extension('rum')
    
    def enable_pg_repack(self) -> Blueprint:
        """Enable pg_repack extension for online table reorganization."""
        return self.enable_extension('pg_repack')
    
    def enable_auto_explain(self) -> Blueprint:
        """Enable auto_explain extension for automatic query planning."""
        return self.enable_extension('auto_explain')
    
    def enable_pg_buffercache(self) -> Blueprint:
        """Enable pg_buffercache extension for buffer cache inspection."""
        return self.enable_extension('pg_buffercache')
    
    def enable_pgstattuple(self) -> Blueprint:
        """Enable pgstattuple extension for tuple-level statistics."""
        return self.enable_extension('pgstattuple')
    
    # ========================================================================================
    # PostgreSQL Constraints and Features
    # ========================================================================================
    
    def add_check_constraint(self, name: str, condition: str) -> Blueprint:
        """Add a check constraint."""
        if not hasattr(self, 'check_constraints'):
            self.check_constraints = []
        self.check_constraints.append({'name': name, 'condition': condition})
        return self
    
    def add_exclude_constraint(self, name: str, elements: List[str], using: str = 'gist', 
                              condition: Optional[str] = None) -> Blueprint:
        """Add an exclusion constraint (PostgreSQL)."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            if not hasattr(self, 'exclude_constraints'):
                self.exclude_constraints = []
            constraint = {
                'name': name,
                'elements': elements,
                'using': using
            }
            if condition:
                constraint['condition'] = condition
            self.exclude_constraints.append(constraint)
        return self
    
    def add_deferrable_constraint(self, constraint_type: str, name: str, **kwargs: Any) -> Blueprint:
        """Add a deferrable constraint (PostgreSQL)."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            if not hasattr(self, 'deferrable_constraints'):
                self.deferrable_constraints = []
            constraint = {
                'type': constraint_type,
                'name': name,
                'deferrable': True,
                **kwargs
            }
            self.deferrable_constraints.append(constraint)
        return self
    
    def set_fill_factor(self, fill_factor: int) -> Blueprint:
        """Set table fill factor (PostgreSQL)."""
        if self.engine == DatabaseEngine.POSTGRESQL and 10 <= fill_factor <= 100:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['fillfactor'] = fill_factor
        return self
    
    def set_parallel_workers(self, workers: int) -> Blueprint:
        """Set parallel workers for table operations (PostgreSQL)."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['parallel_workers'] = workers
        return self
    
    # ========================================================================================
    # PostgreSQL Functions, Triggers, and Advanced Features
    # ========================================================================================
    
    def postgresql_function(self, name: str, body: str, language: str = "PLPGSQL") -> Blueprint:
        """Create a PostgreSQL function."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            if not hasattr(self, 'functions'):
                self.functions = []
            self.functions.append({
                'name': name,
                'body': body,
                'language': language
            })
        return self
    
    def postgresql_trigger(self, name: str, timing: str, definition: str) -> Blueprint:
        """Create a PostgreSQL trigger."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            if not hasattr(self, 'triggers'):
                self.triggers = []
            self.triggers.append({
                'name': name,
                'timing': timing,
                'definition': definition
            })
        return self
    
    def postgresql_hypertable(self, time_column: str, space_column: Optional[str] = None, 
                             chunk_time_interval: str = "1 day") -> Blueprint:
        """Create TimescaleDB hypertable."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['timescaledb_hypertable'] = {
                'time_column': time_column,
                'space_column': space_column,
                'chunk_time_interval': chunk_time_interval
            }
        return self
    
    def postgresql_compression_policy(self, compress_after: str) -> Blueprint:
        """Add TimescaleDB compression policy."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['compression_policy'] = compress_after
        return self
    
    def postgresql_retention_policy(self, drop_after: str) -> Blueprint:
        """Add TimescaleDB retention policy."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['retention_policy'] = drop_after
        return self
    
    def postgresql_partition_maintenance(self, interval: str = "MONTHLY", 
                                       retention: str = "1 YEAR", 
                                       advance_partitions: int = 2) -> Blueprint:
        """Add automatic partition maintenance."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['partition_maintenance'] = {
                'interval': interval,
                'retention': retention,
                'advance_partitions': advance_partitions
            }
        return self
    
    def btree_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add a B-tree index (default PostgreSQL index type)."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'type': 'btree',
            'columns': columns,
            'name': name or f"btree_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def add_row_level_security(self, policy_name: str, condition: str, 
                              command: str = "ALL", roles: Optional[List[str]] = None) -> Blueprint:
        """Add row-level security policy (PostgreSQL)."""
        if self.engine == DatabaseEngine.POSTGRESQL:
            if not hasattr(self, 'rls_policies'):
                self.rls_policies = []
            policy = {
                'name': policy_name,
                'condition': condition,
                'command': command
            }
            if roles:
                policy['roles'] = roles
            self.rls_policies.append(policy)
            
            # Enable RLS on the table
            self.table_options = getattr(self, 'table_options', {})
            self.table_options['enable_rls'] = True
        return self


# ========================================================================================
# Enhanced Schema Class
# ========================================================================================

class ExtendedSchema(Schema):
    """Extended Schema facade with all features."""
    
    @staticmethod
    def create_table_with_features(table_name: str, callback: Callable[[ExtendedBlueprint], None], 
                       engine: DatabaseEngine = DatabaseEngine.MYSQL) -> ExtendedBlueprint:
        """Create a new table with features."""
        blueprint = ExtendedBlueprint(table_name, engine)
        callback(blueprint)
        
        # Execute DDL (implementation would go here)
        print(f"Creating table: {table_name}")
        print(f"Engine: {engine.value}")
        
        return blueprint
    
    @staticmethod
    def create_tenant_table(table_name: str, callback: Callable[[ExtendedBlueprint], None]) -> ExtendedBlueprint:
        """Create a multi-tenant table."""
        def extended_callback(table: ExtendedBlueprint) -> None:
            # Add tenant columns automatically
            table.tenant_columns()
            callback(table)
            
            # Add tenant-aware indexes
            table.index(["tenant_id"])
            
        return ExtendedSchema.create_table_with_features(table_name, extended_callback)
    
    @staticmethod
    def create_audit_table(base_table_name: str) -> ExtendedBlueprint:
        """Create an audit table for another table."""
        audit_table_name = f"{base_table_name}_audit"
        
        def audit_callback(table: ExtendedBlueprint) -> None:
            table.id("audit_id")
            table.string("table_name", 100)
            table.enum("operation", ["INSERT", "UPDATE", "DELETE"])
            table.jsonb("old_values").nullable()
            table.jsonb("new_values").nullable()
            table.string("changed_by", 100)
            table.timestamp("changed_at").default("NOW()")
            table.ip_address("client_ip").nullable()
            table.string("user_agent").nullable()
            
            # Indexes for audit queries
            table.index(["table_name", "changed_at"])
            table.index(["changed_by", "changed_at"])
            table.index(["operation", "changed_at"])
            
            # Partition by month for performance
            table.partition_by_date("changed_at", "MONTH")
            
        return ExtendedSchema.create_table_with_features(audit_table_name, audit_callback)


# Make ExtendedBlueprint available as aliases
ExtendedBlueprintAlias = ExtendedBlueprint
ExtendedSchemaAlias = ExtendedSchema