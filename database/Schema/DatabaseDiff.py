from __future__ import annotations

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

from .DatabaseInspector import DatabaseInspector, TableInfo, ColumnInfo, IndexInfo, ForeignKeyInfo
from .MigrationTemplates import MigrationTemplateEngine


@dataclass
class SchemaDifference:
    """Represents a difference between two database schemas."""
    type: str  # 'table', 'column', 'index', 'foreign_key'
    action: str  # 'add', 'drop', 'modify'
    table_name: str
    name: str
    old_definition: Optional[Any] = None
    new_definition: Optional[Any] = None
    migration_code: Optional[str] = None
    priority: int = 0  # Higher priority = execute first


class DatabaseDiff:
    """Compares database schemas and generates migrations."""
    
    def __init__(self, source_db_url: Optional[str] = None, target_db_url: Optional[str] = None) -> None:
        self.source_inspector = DatabaseInspector(source_db_url) if source_db_url else None
        self.target_inspector = DatabaseInspector(target_db_url) if target_db_url else None
        self.template_engine = MigrationTemplateEngine()
    
    def compare_schemas(self, source_schema: Dict[str, TableInfo], target_schema: Dict[str, TableInfo]) -> List[SchemaDifference]:
        """Compare two database schemas and return differences."""
        differences = []
        
        # Compare tables
        source_tables = set(source_schema.keys())
        target_tables = set(target_schema.keys())
        
        # Tables to add
        for table_name in target_tables - source_tables:
            differences.append(SchemaDifference(
                type="table",
                action="add",
                table_name=table_name,
                name=table_name,
                new_definition=target_schema[table_name],
                priority=100  # Tables should be created first
            ))
        
        # Tables to drop
        for table_name in source_tables - target_tables:
            differences.append(SchemaDifference(
                type="table",
                action="drop",
                table_name=table_name,
                name=table_name,
                old_definition=source_schema[table_name],
                priority=1  # Tables should be dropped last
            ))
        
        # Compare existing tables
        for table_name in source_tables & target_tables:
            table_diffs = self._compare_tables(source_schema[table_name], target_schema[table_name])
            differences.extend(table_diffs)
        
        # Sort by priority (higher first)
        return sorted(differences, key=lambda d: d.priority, reverse=True)
    
    def _compare_tables(self, source_table: TableInfo, target_table: TableInfo) -> List[SchemaDifference]:
        """Compare two tables and return differences."""
        differences = []
        
        # Compare columns
        differences.extend(self._compare_columns(source_table, target_table))
        
        # Compare indexes
        differences.extend(self._compare_indexes(source_table, target_table))
        
        # Compare foreign keys
        differences.extend(self._compare_foreign_keys(source_table, target_table))
        
        return differences
    
    def _compare_columns(self, source_table: TableInfo, target_table: TableInfo) -> List[SchemaDifference]:
        """Compare columns between two tables."""
        differences = []
        
        source_columns = {col.name: col for col in source_table.columns}
        target_columns = {col.name: col for col in target_table.columns}
        
        # Columns to add
        for col_name, col_info in target_columns.items():
            if col_name not in source_columns:
                differences.append(SchemaDifference(
                    type="column",
                    action="add",
                    table_name=target_table.name,
                    name=col_name,
                    new_definition=col_info,
                    priority=80
                ))
        
        # Columns to drop
        for col_name, col_info in source_columns.items():
            if col_name not in target_columns:
                differences.append(SchemaDifference(
                    type="column",
                    action="drop",
                    table_name=source_table.name,
                    name=col_name,
                    old_definition=col_info,
                    priority=20
                ))
        
        # Columns to modify
        for col_name in source_columns.keys() & target_columns.keys():
            source_col = source_columns[col_name]
            target_col = target_columns[col_name]
            
            if self._columns_differ(source_col, target_col):
                differences.append(SchemaDifference(
                    type="column",
                    action="modify",
                    table_name=target_table.name,
                    name=col_name,
                    old_definition=source_col,
                    new_definition=target_col,
                    priority=60
                ))
        
        return differences
    
    def _compare_indexes(self, source_table: TableInfo, target_table: TableInfo) -> List[SchemaDifference]:
        """Compare indexes between two tables."""
        differences = []
        
        source_indexes = {idx.name: idx for idx in source_table.indexes}
        target_indexes = {idx.name: idx for idx in target_table.indexes}
        
        # Indexes to add
        for idx_name, idx_info in target_indexes.items():
            if idx_name not in source_indexes:
                differences.append(SchemaDifference(
                    type="index",
                    action="add",
                    table_name=target_table.name,
                    name=idx_name,
                    new_definition=idx_info,
                    priority=40
                ))
        
        # Indexes to drop
        for idx_name, idx_info in source_indexes.items():
            if idx_name not in target_indexes:
                differences.append(SchemaDifference(
                    type="index",
                    action="drop",
                    table_name=source_table.name,
                    name=idx_name,
                    old_definition=idx_info,
                    priority=30
                ))
        
        # Indexes to modify
        for idx_name in source_indexes.keys() & target_indexes.keys():
            source_idx = source_indexes[idx_name]
            target_idx = target_indexes[idx_name]
            
            if self._indexes_differ(source_idx, target_idx):
                differences.append(SchemaDifference(
                    type="index",
                    action="modify",
                    table_name=target_table.name,
                    name=idx_name,
                    old_definition=source_idx,
                    new_definition=target_idx,
                    priority=35
                ))
        
        return differences
    
    def _compare_foreign_keys(self, source_table: TableInfo, target_table: TableInfo) -> List[SchemaDifference]:
        """Compare foreign keys between two tables."""
        differences = []
        
        source_fks = {fk.name: fk for fk in source_table.foreign_keys}
        target_fks = {fk.name: fk for fk in target_table.foreign_keys}
        
        # Foreign keys to add
        for fk_name, fk_info in target_fks.items():
            if fk_name not in source_fks:
                differences.append(SchemaDifference(
                    type="foreign_key",
                    action="add",
                    table_name=target_table.name,
                    name=fk_name,
                    new_definition=fk_info,
                    priority=10
                ))
        
        # Foreign keys to drop
        for fk_name, fk_info in source_fks.items():
            if fk_name not in target_fks:
                differences.append(SchemaDifference(
                    type="foreign_key",
                    action="drop",
                    table_name=source_table.name,
                    name=fk_name,
                    old_definition=fk_info,
                    priority=90
                ))
        
        return differences
    
    def _columns_differ(self, col1: ColumnInfo, col2: ColumnInfo) -> bool:
        """Check if two columns are different."""
        return (
            col1.type != col2.type or
            col1.nullable != col2.nullable or
            col1.default != col2.default or
            col1.max_length != col2.max_length
        )
    
    def _indexes_differ(self, idx1: IndexInfo, idx2: IndexInfo) -> bool:
        """Check if two indexes are different."""
        return (
            idx1.columns != idx2.columns or
            idx1.unique != idx2.unique or
            idx1.type != idx2.type
        )
    
    def generate_migration_from_diff(self, differences: List[SchemaDifference], migration_name: str) -> str:
        """Generate migration code from schema differences."""
        if not differences:
            return self._generate_empty_migration(migration_name)
        
        # Group differences by table
        table_diffs = {}
        table_creates = []
        table_drops = []
        
        for diff in differences:
            if diff.action == "add" and diff.type == "table":
                table_creates.append(diff)
            elif diff.action == "drop" and diff.type == "table":
                table_drops.append(diff)
            else:
                table_name = diff.table_name
                if table_name not in table_diffs:
                    table_diffs[table_name] = []
                table_diffs[table_name].append(diff)
        
        return self._generate_comprehensive_migration(
            migration_name, table_creates, table_drops, table_diffs
        )
    
    def _generate_empty_migration(self, migration_name: str) -> str:
        """Generate empty migration when no differences found."""
        return f'''from __future__ import annotations

from .Migration import Migration


class {self._snake_to_pascal(migration_name)}(Migration):
    """{migration_name} migration."""
    
    def up(self) -> None:
        """Run the migrations."""
        # No changes needed
        pass
    
    def down(self) -> None:
        """Reverse the migrations."""
        # No changes needed
        pass
'''
    
    def _generate_comprehensive_migration(
        self, 
        migration_name: str, 
        table_creates: List[SchemaDifference],
        table_drops: List[SchemaDifference],
        table_diffs: Dict[str, List[SchemaDifference]]
    ) -> str:
        """Generate comprehensive migration with all changes."""
        
        class_name = self._snake_to_pascal(migration_name)
        
        migration_code = f'''from __future__ import annotations

from .Migration import Migration
from database.Schema.Blueprint import Blueprint


class {class_name}(Migration):
    """{migration_name} migration."""
    
    def up(self) -> None:
        """Run the migrations."""
'''
        
        # Add table creations
        for diff in table_creates:
            migration_code += self._generate_create_table_code(diff)
        
        # Add table modifications
        for table_name, diffs in table_diffs.items():
            migration_code += self._generate_modify_table_code(table_name, diffs)
        
        # Add table drops
        for diff in table_drops:
            migration_code += f'''
        self.drop_table_if_exists("{diff.table_name}")
'''
        
        # Generate down method
        migration_code += '''
    def down(self) -> None:
        """Reverse the migrations."""
'''
        
        # Reverse order for down method
        for diff in reversed(table_drops):
            if diff.old_definition:
                migration_code += self._generate_create_table_code(diff, for_rollback=True)
        
        for table_name, diffs in reversed(table_diffs.items()):
            migration_code += self._generate_rollback_table_code(table_name, diffs)
        
        for diff in reversed(table_creates):
            migration_code += f'''
        self.drop_table_if_exists("{diff.table_name}")
'''
        
        return migration_code
    
    def _generate_create_table_code(self, diff: SchemaDifference, for_rollback: bool = False) -> str:
        """Generate create table code from table info."""
        table_info = diff.new_definition or diff.old_definition
        if not isinstance(table_info, TableInfo):
            return ""
        
        code = f'''
        def create_{table_info.name}_table(table: Blueprint) -> None:
'''
        
        # Add columns
        for column in table_info.columns:
            col_code = self._generate_column_code(column)
            code += f"            {col_code}\n"
        
        # Add indexes
        for index in table_info.indexes:
            if index.unique:
                code += f'            table.unique({index.columns}, "{index.name}")\n'
            else:
                code += f'            table.index({index.columns}, "{index.name}")\n'
        
        # Add foreign keys
        for fk in table_info.foreign_keys:
            code += f'            table.foreign_key("{fk.column}", "{fk.referenced_table}", "{fk.referenced_column}", on_delete="{fk.on_delete}")\n'
        
        code += f'''
        self.create_table("{table_info.name}", create_{table_info.name}_table)
'''
        
        return code
    
    def _generate_modify_table_code(self, table_name: str, diffs: List[SchemaDifference]) -> str:
        """Generate modify table code from differences."""
        code = f'''
        def modify_{table_name}_table(table: Blueprint) -> None:
'''
        
        for diff in diffs:
            if diff.type == "column" and diff.action == "add":
                col_code = self._generate_column_code(diff.new_definition)
                code += f"            {col_code}\n"
            elif diff.type == "column" and diff.action == "drop":
                code += f'            table.drop_column("{diff.name}")\n'
            elif diff.type == "column" and diff.action == "modify":
                # Generate column change code
                col_code = self._generate_column_change_code(diff.old_definition, diff.new_definition)
                code += f"            {col_code}\n"
            elif diff.type == "index" and diff.action == "add":
                idx_info = diff.new_definition
                if idx_info.unique:
                    code += f'            table.unique({idx_info.columns}, "{idx_info.name}")\n'
                else:
                    code += f'            table.index({idx_info.columns}, "{idx_info.name}")\n'
            elif diff.type == "index" and diff.action == "drop":
                code += f'            table.drop_index("{diff.name}")\n'
            elif diff.type == "foreign_key" and diff.action == "add":
                fk_info = diff.new_definition
                code += f'            table.foreign_key("{fk_info.column}", "{fk_info.referenced_table}", "{fk_info.referenced_column}", on_delete="{fk_info.on_delete}")\n'
            elif diff.type == "foreign_key" and diff.action == "drop":
                code += f'            table.drop_foreign("{diff.old_definition.column}")\n'
        
        code += f'''
        self.modify_table("{table_name}", modify_{table_name}_table)
'''
        
        return code
    
    def _generate_rollback_table_code(self, table_name: str, diffs: List[SchemaDifference]) -> str:
        """Generate rollback code for table modifications."""
        code = f'''
        def rollback_{table_name}_table(table: Blueprint) -> None:
'''
        
        # Reverse the operations
        for diff in reversed(diffs):
            if diff.type == "column" and diff.action == "add":
                code += f'            table.drop_column("{diff.name}")\n'
            elif diff.type == "column" and diff.action == "drop":
                col_code = self._generate_column_code(diff.old_definition)
                code += f"            {col_code}\n"
            elif diff.type == "column" and diff.action == "modify":
                col_code = self._generate_column_change_code(diff.new_definition, diff.old_definition)
                code += f"            {col_code}\n"
            elif diff.type == "index" and diff.action == "add":
                code += f'            table.drop_index("{diff.name}")\n'
            elif diff.type == "index" and diff.action == "drop":
                idx_info = diff.old_definition
                if idx_info.unique:
                    code += f'            table.unique({idx_info.columns}, "{idx_info.name}")\n'
                else:
                    code += f'            table.index({idx_info.columns}, "{idx_info.name}")\n'
        
        code += f'''
        self.modify_table("{table_name}", rollback_{table_name}_table)
'''
        
        return code
    
    def _generate_column_code(self, column: ColumnInfo) -> str:
        """Generate Blueprint column code."""
        # Map SQLAlchemy types to Blueprint methods
        type_mapping = {
            'VARCHAR': 'string',
            'TEXT': 'text',
            'INTEGER': 'integer',
            'BOOLEAN': 'boolean',
            'DATETIME': 'datetime',
            'TIMESTAMP': 'timestamp',
            'DECIMAL': 'decimal',
            'FLOAT': 'float_column',
            'JSON': 'json_column'
        }
        
        col_type = column.type.upper()
        blueprint_method = type_mapping.get(col_type, 'string')
        
        # Start with method call
        code = f'table.{blueprint_method}("{column.name}"'
        
        # Add length for string types
        if blueprint_method == 'string' and column.max_length:
            code += f', {column.max_length}'
        
        code += ')'
        
        # Add modifiers
        if not column.nullable:
            code += '.nullable(False)'
        
        if column.default is not None:
            code += f'.default({repr(column.default)})'
        
        if column.unique:
            code += '.unique()'
        
        if column.primary_key:
            code += '.primary_key()'
        
        return code
    
    def _generate_column_change_code(self, old_col: ColumnInfo, new_col: ColumnInfo) -> str:
        """Generate column change code."""
        changes = []
        
        # Check if type changed
        if old_col.type != new_col.type:
            changes.append(f"op.alter_column('{old_col.table}', '{old_col.name}', type_=sa.{new_col.type}())")
        
        # Check if nullable changed
        if old_col.nullable != new_col.nullable:
            nullable_str = 'True' if new_col.nullable else 'False'
            changes.append(f"op.alter_column('{old_col.table}', '{old_col.name}', nullable={nullable_str})")
        
        # Check if default changed
        if old_col.default != new_col.default:
            if new_col.default:
                changes.append(f"op.alter_column('{old_col.table}', '{old_col.name}', server_default='{new_col.default}')")
            else:
                changes.append(f"op.alter_column('{old_col.table}', '{old_col.name}', server_default=None)")
        
        return '\n    '.join(changes) if changes else f'# No changes needed for column {old_col.name}'
    
    def _snake_to_pascal(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        return ''.join(word.capitalize() for word in snake_str.split('_'))
    
    def create_migration_from_databases(self, migration_name: str) -> str:
        """Create migration by comparing two database instances."""
        if not self.source_inspector or not self.target_inspector:
            raise ValueError("Both source and target database inspectors must be configured")
        
        source_schema = self.source_inspector.get_database_schema()
        target_schema = self.target_inspector.get_database_schema()
        
        differences = self.compare_schemas(source_schema, target_schema)
        return self.generate_migration_from_diff(differences, migration_name)
    
    def generate_diff_report(self, differences: List[SchemaDifference]) -> str:
        """Generate human-readable diff report."""
        if not differences:
            return "No differences found between schemas."
        
        report = "Database Schema Differences\n"
        report += "=" * 50 + "\n\n"
        
        # Group by action
        actions = {}
        for diff in differences:
            action_key = f"{diff.action}_{diff.type}"
            if action_key not in actions:
                actions[action_key] = []
            actions[action_key].append(diff)
        
        for action_key, diffs in actions.items():
            action, obj_type = action_key.split('_', 1)
            report += f"{action.upper()} {obj_type.upper()}S:\n"
            report += "-" * 30 + "\n"
            
            for diff in diffs:
                if obj_type == "table":
                    report += f"  • {diff.table_name}\n"
                else:
                    report += f"  • {diff.table_name}.{diff.name}\n"
            
            report += "\n"
        
        return report
    
    def estimate_migration_impact(self, differences: List[SchemaDifference]) -> Dict[str, Any]:
        """Estimate the impact of applying the migration."""
        impact = {
            "total_changes": len(differences),
            "tables_affected": len(set(diff.table_name for diff in differences)),
            "destructive_operations": 0,
            "data_loss_risk": "low",
            "estimated_time": 0.0,
            "rollback_complexity": "simple"
        }
        
        destructive_ops = ["drop_table", "drop_column", "modify_column"]
        
        for diff in differences:
            if diff.action in ["drop"] or (diff.action == "modify" and diff.type == "column"):
                impact["destructive_operations"] += 1
        
        # Assess risk levels
        if impact["destructive_operations"] > 0:
            impact["data_loss_risk"] = "high" if impact["destructive_operations"] > 5 else "medium"
        
        if impact["destructive_operations"] > 3:
            impact["rollback_complexity"] = "complex"
        elif impact["destructive_operations"] > 0:
            impact["rollback_complexity"] = "moderate"
        
        # Estimate time (simple heuristic)
        impact["estimated_time"] = len(differences) * 0.5  # 0.5 seconds per operation
        
        return impact