from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.types import Float, JSON
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.sql import func
from datetime import datetime


class ColumnDefinition:
    """Represents a column definition in Laravel style."""
    
    def __init__(self, name: str, column_type: Any) -> None:
        self.name = name
        self.column_type = column_type
        self._nullable = False
        self.default_value: Any = None
        self._primary = False
        self._unique = False
        self._index = False
        self._foreign_key: Optional[str] = None
        self.comment: Optional[str] = None
        self.auto_increment = False
        self.length: Optional[int] = None
    
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
        """Make column nullable."""
        self._nullable = nullable
        return self
    
    def default(self, value: Any) -> ColumnDefinition:
        """Set default value."""
        self.default_value = value
        return self
    
    def primary_key(self) -> ColumnDefinition:
        """Make column primary key."""
        self._primary = True
        return self
    
    def unique(self) -> ColumnDefinition:
        """Make column unique."""
        self._unique = True
        return self
    
    def index(self) -> ColumnDefinition:
        """Add index to column."""
        self._index = True
        return self
    
    def foreign_key(self, reference: str, on_delete: str = "RESTRICT") -> ColumnDefinition:
        """Add foreign key reference."""
        self._foreign_key = reference
        return self
    
    def default_current_timestamp(self) -> ColumnDefinition:
        """Set default to current timestamp."""
        self.default_value = func.now()
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
    
    def add_index(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
        """Add an index."""
        if isinstance(columns, str):
            columns = [columns]
        
        self.indexes.append({
            'columns': columns,
            'name': name or f"idx_{self.table_name}_{'_'.join(columns)}"
        })
        return self
    
    def add_unique(self, columns: Union[str, List[str]], name: Optional[str] = None) -> Blueprint:
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