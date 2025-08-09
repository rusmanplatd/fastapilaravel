from __future__ import annotations

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from sqlalchemy import create_engine, MetaData, Table, Column, Index, ForeignKey
from sqlalchemy.engine import Engine
from sqlalchemy.sql import text
from sqlalchemy.exc import SQLAlchemyError
import re

from config.database import DATABASE_URL


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    type: str
    nullable: bool
    default: Optional[Any]
    primary_key: bool
    unique: bool
    foreign_key: Optional[str] = None
    comment: Optional[str] = None
    auto_increment: bool = False
    max_length: Optional[int] = None


@dataclass
class IndexInfo:
    """Information about a database index."""
    name: str
    columns: List[str]
    unique: bool
    type: str = "btree"
    condition: Optional[str] = None


@dataclass
class ForeignKeyInfo:
    """Information about a foreign key constraint."""
    name: str
    column: str
    referenced_table: str
    referenced_column: str
    on_delete: str
    on_update: str


@dataclass
class TableInfo:
    """Complete information about a database table."""
    name: str
    columns: List[ColumnInfo]
    indexes: List[IndexInfo]
    foreign_keys: List[ForeignKeyInfo]
    comment: Optional[str] = None
    engine: Optional[str] = None
    charset: Optional[str] = None
    collation: Optional[str] = None


class DatabaseInspector:
    """Inspects database structure and provides detailed information."""
    
    def __init__(self, database_url: str = DATABASE_URL) -> None:
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.metadata = MetaData()
    
    def get_tables(self) -> List[str]:
        """Get list of all table names in the database."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
                return [row[0] for row in result]
        except SQLAlchemyError:
            # Fallback to SQLAlchemy introspection
            self.metadata.reflect(bind=self.engine)
            return list(self.metadata.tables.keys())
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        return table_name in self.get_tables()
    
    def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """Get complete information about a table."""
        if not self.table_exists(table_name):
            return None
        
        try:
            # Reflect the specific table
            table = Table(table_name, self.metadata, autoload_with=self.engine)
            
            columns = self._get_column_info(table)
            indexes = self._get_index_info(table)
            foreign_keys = self._get_foreign_key_info(table)
            
            # Get table-level information
            comment = getattr(table, 'comment', None)
            engine_info = self._get_table_engine(table_name)
            charset_info = self._get_table_charset(table_name)
            
            return TableInfo(
                name=table_name,
                columns=columns,
                indexes=indexes,
                foreign_keys=foreign_keys,
                comment=comment,
                engine=engine_info.get('engine'),
                charset=engine_info.get('charset'),
                collation=engine_info.get('collation')
            )
        
        except SQLAlchemyError as e:
            print(f"Error inspecting table {table_name}: {e}")
            return None
    
    def _get_column_info(self, table: Table) -> List[ColumnInfo]:
        """Get column information from a table."""
        columns = []
        
        for column in table.columns:
            # Determine column type
            col_type = str(column.type)
            
            # Extract max length for string types
            max_length = None
            if hasattr(column.type, 'length') and column.type.length:
                max_length = column.type.length
            
            # Check for foreign key
            foreign_key = None
            if column.foreign_keys:
                fk = list(column.foreign_keys)[0]
                foreign_key = f"{fk.column.table.name}.{fk.column.name}"
            
            columns.append(ColumnInfo(
                name=column.name,
                type=col_type,
                nullable=column.nullable,
                default=column.default.arg if column.default else None,
                primary_key=column.primary_key,
                unique=column.unique,
                foreign_key=foreign_key,
                comment=getattr(column, 'comment', None),
                auto_increment=getattr(column, 'autoincrement', False),
                max_length=max_length
            ))
        
        return columns
    
    def _get_index_info(self, table: Table) -> List[IndexInfo]:
        """Get index information from a table."""
        indexes = []
        
        for index in table.indexes:
            columns = [col.name for col in index.columns]
            
            indexes.append(IndexInfo(
                name=index.name,
                columns=columns,
                unique=index.unique,
                type="btree"  # Default type
            ))
        
        return indexes
    
    def _get_foreign_key_info(self, table: Table) -> List[ForeignKeyInfo]:
        """Get foreign key information from a table."""
        foreign_keys = []
        
        for constraint in table.foreign_key_constraints:
            for element in constraint.elements:
                foreign_keys.append(ForeignKeyInfo(
                    name=constraint.name or f"fk_{table.name}_{element.parent.name}",
                    column=element.parent.name,
                    referenced_table=element.column.table.name,
                    referenced_column=element.column.name,
                    on_delete=getattr(constraint, 'ondelete', 'RESTRICT'),
                    on_update=getattr(constraint, 'onupdate', 'CASCADE')
                ))
        
        return foreign_keys
    
    def _get_table_engine(self, table_name: str) -> Dict[str, Optional[str]]:
        """Get table engine information (MySQL specific)."""
        try:
            with self.engine.connect() as conn:
                if 'mysql' in self.database_url.lower():
                    result = conn.execute(
                        text("SELECT ENGINE, TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_NAME = :table_name"),
                        {"table_name": table_name}
                    )
                    row = result.fetchone()
                    if row:
                        return {"engine": row[0], "collation": row[1]}
        except SQLAlchemyError:
            pass
        
        return {"engine": None, "collation": None}
    
    def _get_table_charset(self, table_name: str) -> Dict[str, Optional[str]]:
        """Get table charset information (MySQL specific)."""
        try:
            with self.engine.connect() as conn:
                if 'mysql' in self.database_url.lower():
                    result = conn.execute(
                        text("SELECT CCSA.character_set_name FROM information_schema.`TABLES` T, information_schema.`COLLATION_CHARACTER_SET_APPLICABILITY` CCSA WHERE CCSA.collation_name = T.table_collation AND T.table_schema = DATABASE() AND T.table_name = :table_name"),
                        {"table_name": table_name}
                    )
                    row = result.fetchone()
                    if row:
                        return {"charset": row[0]}
        except SQLAlchemyError:
            pass
        
        return {"charset": None}
    
    def get_column_info(self, table_name: str, column_name: str) -> Optional[ColumnInfo]:
        """Get information about a specific column."""
        table_info = self.get_table_info(table_name)
        if not table_info:
            return None
        
        for column in table_info.columns:
            if column.name == column_name:
                return column
        
        return None
    
    def column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        return self.get_column_info(table_name, column_name) is not None
    
    def index_exists(self, table_name: str, index_name: str) -> bool:
        """Check if an index exists on a table."""
        table_info = self.get_table_info(table_name)
        if not table_info:
            return False
        
        return any(index.name == index_name for index in table_info.indexes)
    
    def foreign_key_exists(self, table_name: str, constraint_name: str) -> bool:
        """Check if a foreign key constraint exists."""
        table_info = self.get_table_info(table_name)
        if not table_info:
            return False
        
        return any(fk.name == constraint_name for fk in table_info.foreign_keys)
    
    def get_database_schema(self) -> Dict[str, TableInfo]:
        """Get complete database schema information."""
        schema = {}
        
        for table_name in self.get_tables():
            table_info = self.get_table_info(table_name)
            if table_info:
                schema[table_name] = table_info
        
        return schema
    
    def compare_tables(self, table1: str, table2: str) -> Dict[str, Any]:
        """Compare two tables and return differences."""
        info1 = self.get_table_info(table1)
        info2 = self.get_table_info(table2)
        
        if not info1 or not info2:
            return {"error": "One or both tables do not exist"}
        
        differences = {
            "columns": {
                "added": [],
                "removed": [],
                "modified": []
            },
            "indexes": {
                "added": [],
                "removed": [],
                "modified": []
            },
            "foreign_keys": {
                "added": [],
                "removed": [],
                "modified": []
            }
        }
        
        # Compare columns
        columns1 = {col.name: col for col in info1.columns}
        columns2 = {col.name: col for col in info2.columns}
        
        for name, col in columns2.items():
            if name not in columns1:
                differences["columns"]["added"].append(col)
            elif self._columns_differ(columns1[name], col):
                differences["columns"]["modified"].append((columns1[name], col))
        
        for name, col in columns1.items():
            if name not in columns2:
                differences["columns"]["removed"].append(col)
        
        # Compare indexes
        indexes1 = {idx.name: idx for idx in info1.indexes}
        indexes2 = {idx.name: idx for idx in info2.indexes}
        
        for name, idx in indexes2.items():
            if name not in indexes1:
                differences["indexes"]["added"].append(idx)
            elif self._indexes_differ(indexes1[name], idx):
                differences["indexes"]["modified"].append((indexes1[name], idx))
        
        for name, idx in indexes1.items():
            if name not in indexes2:
                differences["indexes"]["removed"].append(idx)
        
        return differences
    
    def _columns_differ(self, col1: ColumnInfo, col2: ColumnInfo) -> bool:
        """Check if two columns are different."""
        return (
            col1.type != col2.type or
            col1.nullable != col2.nullable or
            col1.default != col2.default or
            col1.primary_key != col2.primary_key or
            col1.unique != col2.unique or
            col1.max_length != col2.max_length
        )
    
    def _indexes_differ(self, idx1: IndexInfo, idx2: IndexInfo) -> bool:
        """Check if two indexes are different."""
        return (
            idx1.columns != idx2.columns or
            idx1.unique != idx2.unique or
            idx1.type != idx2.type
        )
    
    def analyze_table_performance(self, table_name: str) -> Dict[str, Any]:
        """Analyze table performance characteristics."""
        if not self.table_exists(table_name):
            return {"error": "Table does not exist"}
        
        analysis = {
            "table_size": self._get_table_size(table_name),
            "row_count": self._get_row_count(table_name),
            "index_usage": self._analyze_index_usage(table_name),
            "missing_indexes": self._suggest_missing_indexes(table_name)
        }
        
        return analysis
    
    def _get_table_size(self, table_name: str) -> Optional[int]:
        """Get table size in bytes."""
        try:
            with self.engine.connect() as conn:
                if 'mysql' in self.database_url.lower():
                    result = conn.execute(
                        text("SELECT (data_length + index_length) as size FROM information_schema.TABLES WHERE table_name = :table_name"),
                        {"table_name": table_name}
                    )
                    row = result.fetchone()
                    return row[0] if row else None
        except SQLAlchemyError:
            pass
        
        return None
    
    def _get_row_count(self, table_name: str) -> Optional[int]:
        """Get approximate row count."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar()
        except SQLAlchemyError:
            pass
        
        return None
    
    def _analyze_index_usage(self, table_name: str) -> List[Dict[str, Any]]:
        """Analyze index usage statistics."""
        # This would require database-specific queries
        # Implementation depends on the database system
        return []
    
    def _suggest_missing_indexes(self, table_name: str) -> List[str]:
        """Suggest potentially missing indexes."""
        suggestions = []
        table_info = self.get_table_info(table_name)
        
        if not table_info:
            return suggestions
        
        # Look for foreign key columns without indexes
        indexed_columns = set()
        for index in table_info.indexes:
            indexed_columns.update(index.columns)
        
        for fk in table_info.foreign_keys:
            if fk.column not in indexed_columns:
                suggestions.append(f"Consider adding index on foreign key column: {fk.column}")
        
        # Look for columns that might benefit from indexes
        for column in table_info.columns:
            if (column.name.endswith('_id') and 
                not column.primary_key and 
                column.name not in indexed_columns):
                suggestions.append(f"Consider adding index on ID column: {column.name}")
        
        return suggestions
    
    def export_schema_sql(self, table_names: Optional[List[str]] = None) -> str:
        """Export database schema as SQL DDL."""
        if table_names is None:
            table_names = self.get_tables()
        
        sql_statements = []
        
        for table_name in table_names:
            table_info = self.get_table_info(table_name)
            if table_info:
                sql_statements.append(self._generate_create_table_sql(table_info))
        
        return "\n\n".join(sql_statements)
    
    def _generate_create_table_sql(self, table_info: TableInfo) -> str:
        """Generate CREATE TABLE SQL for a table."""
        lines = [f"CREATE TABLE {table_info.name} ("]
        
        # Add columns
        column_lines = []
        for column in table_info.columns:
            col_def = f"  {column.name} {column.type}"
            
            if not column.nullable:
                col_def += " NOT NULL"
            
            if column.default is not None:
                col_def += f" DEFAULT {column.default}"
            
            if column.primary_key:
                col_def += " PRIMARY KEY"
            
            if column.unique:
                col_def += " UNIQUE"
            
            column_lines.append(col_def)
        
        lines.extend(column_lines)
        lines.append(");")
        
        # Add indexes
        for index in table_info.indexes:
            index_type = "UNIQUE " if index.unique else ""
            columns_str = ", ".join(index.columns)
            lines.append(f"CREATE {index_type}INDEX {index.name} ON {table_info.name} ({columns_str});")
        
        return "\n".join(lines)