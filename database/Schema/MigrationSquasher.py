from __future__ import annotations

import ast
import re
from typing import List, Dict, Set, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from .MigrationManager import MigrationManager
from .MigrationDependency import DependencyResolver


@dataclass
class TableOperation:
    """Represents a table operation in migrations."""
    operation_type: str  # 'create', 'modify', 'drop'
    table_name: str
    columns: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]
    foreign_keys: List[Dict[str, Any]]
    migration_name: str


class MigrationParser:
    """Parses migration files to extract table operations."""
    
    def __init__(self) -> None:
        self.operations: List[TableOperation] = []
    
    def parse_migration_file(self, migration_path: Path) -> List[TableOperation]:
        """Parse a migration file and extract operations."""
        operations = []
        
        try:
            with open(migration_path, 'r') as f:
                content = f.read()
            
            # Parse the Python AST
            tree = ast.parse(content)
            
            # Find the migration class and its up() method
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    operations.extend(self._parse_class(node, migration_path.stem))
        
        except Exception as e:
            print(f"Error parsing {migration_path}: {e}")
        
        return operations
    
    def _parse_class(self, class_node: ast.ClassDef, migration_name: str) -> List[TableOperation]:
        """Parse migration class for table operations."""
        operations = []
        
        # Find the up() method
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and node.name == "up":
                operations.extend(self._parse_up_method(node, migration_name))
        
        return operations
    
    def _parse_up_method(self, method_node: ast.FunctionDef, migration_name: str) -> List[TableOperation]:
        """Parse up() method for table operations."""
        operations = []
        
        for stmt in method_node.body:
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                if (isinstance(call.func, ast.Attribute) and 
                    call.func.attr in ["create_table", "modify_table", "drop_table"]):
                    
                    operation = self._parse_table_operation(call, migration_name)
                    if operation:
                        operations.append(operation)
        
        return operations
    
    def _parse_table_operation(self, call_node: ast.Call, migration_name: str) -> Optional[TableOperation]:
        """Parse a table operation call."""
        if not isinstance(call_node.func, ast.Attribute):
            return None
        
        operation_type = call_node.func.attr.replace("_table", "")
        
        # Get table name (first argument)
        if not call_node.args or not isinstance(call_node.args[0], ast.Constant):
            return None
        
        table_name = call_node.args[0].value
        
        return TableOperation(
            operation_type=operation_type,
            table_name=table_name,
            columns=[],
            indexes=[],
            foreign_keys=[],
            migration_name=migration_name
        )


class MigrationSquasher:
    """Squashes multiple migrations into optimized migrations."""
    
    def __init__(self, migrations_path: str = "database/migrations") -> None:
        self.migrations_path = Path(migrations_path)
        self.parser = MigrationParser()
        self.migration_manager = MigrationManager(str(migrations_path))
    
    def analyze_migrations(self, migration_names: List[str]) -> Dict[str, List[TableOperation]]:
        """Analyze migrations to extract table operations."""
        table_operations: Dict[str, List[TableOperation]] = {}
        
        for migration_name in migration_names:
            migration_path = self.migrations_path / f"{migration_name}.py"
            if migration_path.exists():
                operations = self.parser.parse_migration_file(migration_path)
                
                for op in operations:
                    if op.table_name not in table_operations:
                        table_operations[op.table_name] = []
                    table_operations[op.table_name].append(op)
        
        return table_operations
    
    def optimize_table_operations(self, operations: List[TableOperation]) -> List[TableOperation]:
        """Optimize operations for a single table."""
        # Sort operations by migration order
        operations.sort(key=lambda x: x.migration_name)
        
        optimized = []
        table_created = False
        final_columns = {}
        final_indexes = {}
        final_foreign_keys = {}
        
        for op in operations:
            if op.operation_type == "create":
                if not table_created:
                    optimized.append(op)
                    table_created = True
                    # Track columns from creation
                    for col in op.columns:
                        final_columns[col["name"]] = col
            
            elif op.operation_type == "modify":
                if table_created:
                    # Merge modifications into the create operation
                    for col in op.columns:
                        final_columns[col["name"]] = col
                    for idx in op.indexes:
                        final_indexes[idx["name"]] = idx
                    for fk in op.foreign_keys:
                        final_foreign_keys[fk["column"]] = fk
                else:
                    # Keep modify operations if table wasn't created in this batch
                    optimized.append(op)
            
            elif op.operation_type == "drop":
                if table_created:
                    # Remove the create operation
                    optimized = [o for o in optimized if o.table_name != op.table_name or o.operation_type != "create"]
                    table_created = False
                else:
                    optimized.append(op)
        
        # Update create operation with final state
        if table_created and optimized:
            create_op = next((op for op in optimized if op.operation_type == "create"), None)
            if create_op:
                create_op.columns = list(final_columns.values())
                create_op.indexes = list(final_indexes.values())
                create_op.foreign_keys = list(final_foreign_keys.values())
        
        return optimized
    
    def squash_migrations(self, from_migration: str, to_migration: str) -> str:
        """Squash migrations from one to another into a single migration."""
        # Get all migrations between the range
        all_migrations = self.migration_manager.get_migration_files()
        
        try:
            from_index = all_migrations.index(from_migration)
            to_index = all_migrations.index(to_migration)
        except ValueError as e:
            raise ValueError(f"Migration not found: {e}")
        
        if from_index > to_index:
            raise ValueError("From migration must come before to migration")
        
        migrations_to_squash = all_migrations[from_index:to_index + 1]
        
        # Analyze operations
        table_operations = self.analyze_migrations(migrations_to_squash)
        
        # Optimize operations per table
        optimized_operations = {}
        for table_name, ops in table_operations.items():
            optimized_operations[table_name] = self.optimize_table_operations(ops)
        
        # Generate squashed migration
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        squashed_name = f"{timestamp}_squashed_{from_migration}_to_{to_migration}"
        
        content = self._generate_squashed_migration(squashed_name, optimized_operations)
        
        # Write squashed migration file
        squashed_path = self.migrations_path / f"{squashed_name}.py"
        with open(squashed_path, 'w') as f:
            f.write(content)
        
        return squashed_name
    
    def _generate_squashed_migration(self, migration_name: str, operations: Dict[str, List[TableOperation]]) -> str:
        """Generate squashed migration file content."""
        class_name = self._snake_to_pascal(migration_name)
        
        content = f'''from __future__ import annotations

from .Migration import Migration
from database.Schema.Blueprint import Blueprint


class {class_name}(Migration):
    """Squashed migration combining multiple operations."""
    
    def up(self) -> None:
        """Run the migrations."""
'''
        
        # Generate up() method content
        for table_name, table_ops in operations.items():
            for op in table_ops:
                if op.operation_type == "create":
                    content += f'''
        def create_{table_name}_table(table: Blueprint) -> None:
            # Squashed table creation with all modifications
'''
                    # Add column definitions
                    for col in op.columns:
                        content += f"            table.{col.get('type', 'string')}('{col['name']}')"
                        # Add modifiers
                        if not col.get('nullable', True):
                            content += ".nullable(False)"
                        if col.get('unique'):
                            content += ".unique()"
                        if col.get('index'):
                            content += ".index()"
                        content += "\n"
                    
                    content += f"        self.create_table('{table_name}', create_{table_name}_table)\n"
                
                elif op.operation_type == "modify":
                    content += f'''
        def modify_{table_name}_table(table: Blueprint) -> None:
            # Squashed table modifications
            pass
        
        self.modify_table('{table_name}', modify_{table_name}_table)
'''
                
                elif op.operation_type == "drop":
                    content += f"        self.drop_table_if_exists('{table_name}')\n"
        
        # Generate down() method
        content += '''
    def down(self) -> None:
        """Reverse the migrations."""
'''
        
        # Reverse operations for down method
        for table_name, table_ops in reversed(operations.items()):
            for op in reversed(table_ops):
                if op.operation_type == "create":
                    content += f"        self.drop_table_if_exists('{table_name}')\n"
                elif op.operation_type == "drop":
                    # Recreate dropped table with original structure
                    content += f"        # Recreate {table_name} table that was dropped\n"
                    content += f"        self._recreate_{table_name}_table()\n"
        
        # Add helper methods for recreating dropped tables
        recreate_methods = self._generate_table_recreation_methods(operations)
        content += recreate_methods
        
        return content
    
    def _generate_table_recreation_methods(self, operations: Dict[str, List[TableOperation]]) -> str:
        """Generate helper methods for recreating dropped tables."""
        methods_content = ""
        
        for table_name, table_ops in operations.items():
            # Find drop operations to generate recreation methods
            for op in table_ops:
                if op.operation_type == "drop":
                    methods_content += f"""
    def _recreate_{table_name}_table(self) -> None:
        \"\"\"Recreate the {table_name} table with original structure.\"\"\"
        self.create_table('{table_name}', lambda table: (
            # Recreate original columns
"""
                    
                    # Add columns from the original table structure
                    if op.columns:
                        for col in op.columns:
                            col_type = col.get('type', 'String')
                            col_name = col.get('name', 'unknown')
                            nullable = col.get('nullable', True)
                            primary_key = col.get('primary_key', False)
                            default = col.get('default')
                            
                            methods_content += f"            table.{col_type.lower()}('{col_name}'"
                            
                            if primary_key:
                                methods_content += ", primary_key=True"
                            if not nullable:
                                methods_content += ", nullable=False"
                            if default is not None:
                                methods_content += f", default={repr(default)}"
                            
                            methods_content += "),\n"
                    else:
                        # Fallback if no column info available
                        methods_content += f"            table.integer('id', primary_key=True),\n"
                        methods_content += f"            table.timestamp('created_at', default='CURRENT_TIMESTAMP'),\n"
                        methods_content += f"            table.timestamp('updated_at', nullable=True),\n"
                    
                    methods_content += "        ))\n"
                    
                    # Add indexes if any
                    if op.indexes:
                        for idx in op.indexes:
                            idx_name = idx.get('name', f'{table_name}_index')
                            columns = idx.get('columns', [])
                            unique = idx.get('unique', False)
                            
                            if columns:
                                col_list = "', '".join(columns)
                                if unique:
                                    methods_content += f"        self.create_unique_index('{table_name}', ['{col_list}'], '{idx_name}')\n"
                                else:
                                    methods_content += f"        self.create_index('{table_name}', ['{col_list}'], '{idx_name}')\n"
                    
                    # Add foreign keys if any
                    if op.foreign_keys:
                        for fk in op.foreign_keys:
                            local_col = fk.get('local_column', 'id')
                            foreign_table = fk.get('foreign_table', 'related_table')
                            foreign_col = fk.get('foreign_column', 'id')
                            
                            methods_content += f"        self.add_foreign_key('{table_name}', '{local_col}', '{foreign_table}', '{foreign_col}')\n"
                    
                    methods_content += "\n"
        
        return methods_content
    
    def _snake_to_pascal(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase."""
        return ''.join(word.capitalize() for word in snake_str.split('_'))
    
    def get_squash_candidates(self) -> List[Tuple[str, str, int]]:
        """Get migration ranges that are good candidates for squashing."""
        all_migrations = self.migration_manager.get_migration_files()
        candidates = []
        
        # Look for sequences of table modifications
        table_sequences = {}
        
        for migration in all_migrations:
            # Extract table name from migration name
            if match := re.search(r'(create|modify|add|drop)_(\w+)_table', migration):
                table_name = match.group(2)
                if table_name not in table_sequences:
                    table_sequences[table_name] = []
                table_sequences[table_name].append(migration)
        
        # Find sequences with multiple operations
        for table_name, migrations in table_sequences.items():
            if len(migrations) > 2:  # More than just create + one modification
                candidates.append((migrations[0], migrations[-1], len(migrations)))
        
        return candidates