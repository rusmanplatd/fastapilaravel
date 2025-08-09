from __future__ import annotations

from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
import ast
import re

from .MigrationManager import MigrationManager
from .DatabaseInspector import DatabaseInspector, TableInfo, ColumnInfo


@dataclass
class ValidationIssue:
    """Represents a migration validation issue."""
    severity: str  # 'error', 'warning', 'info'
    migration: str
    message: str
    suggestion: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class DryRunResult:
    """Result of a dry-run migration."""
    migration_name: str
    sql_statements: List[str]
    warnings: List[str]
    estimated_time: Optional[float] = None
    affected_rows: Optional[int] = None


class MigrationValidator:
    """Validates migrations before execution."""
    
    def __init__(self, migrations_path: str = "database/migrations") -> None:
        self.migrations_path = Path(migrations_path)
        self.inspector = DatabaseInspector()
        self.migration_manager = MigrationManager(str(migrations_path))
    
    def validate_migration(self, migration_name: str) -> List[ValidationIssue]:
        """Validate a specific migration."""
        issues = []
        migration_path = self.migrations_path / f"{migration_name}.py"
        
        if not migration_path.exists():
            issues.append(ValidationIssue(
                severity="error",
                migration=migration_name,
                message=f"Migration file not found: {migration_path}"
            ))
            return issues
        
        # Parse the migration file
        try:
            with open(migration_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            issues.extend(self._validate_syntax(tree, migration_name))
            issues.extend(self._validate_structure(tree, migration_name))
            issues.extend(self._validate_operations(tree, migration_name))
            issues.extend(self._validate_database_compatibility(tree, migration_name))
            
        except SyntaxError as e:
            issues.append(ValidationIssue(
                severity="error",
                migration=migration_name,
                message=f"Syntax error: {e.msg}",
                line_number=e.lineno
            ))
        except Exception as e:
            issues.append(ValidationIssue(
                severity="error",
                migration=migration_name,
                message=f"Error parsing migration: {e}"
            ))
        
        return issues
    
    def validate_all_migrations(self) -> Dict[str, List[ValidationIssue]]:
        """Validate all migrations."""
        results = {}
        migrations = self.migration_manager.get_migration_files()
        
        for migration in migrations:
            results[migration] = self.validate_migration(migration)
        
        return results
    
    def _validate_syntax(self, tree: ast.AST, migration_name: str) -> List[ValidationIssue]:
        """Validate Python syntax and structure."""
        issues = []
        
        # Check for required imports
        required_imports = [
            "database.Schema.Migration",
            "database.Schema.Blueprint"
        ]
        
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        
        for required_import in required_imports:
            if not any(required_import.startswith(imp) for imp in imports):
                issues.append(ValidationIssue(
                    severity="warning",
                    migration=migration_name,
                    message=f"Missing import: {required_import}",
                    suggestion=f"Add: from {required_import} import ..."
                ))
        
        return issues
    
    def _validate_structure(self, tree: ast.AST, migration_name: str) -> List[ValidationIssue]:
        """Validate migration class structure."""
        issues = []
        
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node)
        
        if not classes:
            issues.append(ValidationIssue(
                severity="error",
                migration=migration_name,
                message="No migration class found"
            ))
            return issues
        
        migration_class = classes[0]  # Assume first class is the migration
        
        # Check for required methods
        methods = {node.name for node in migration_class.body if isinstance(node, ast.FunctionDef)}
        
        if "up" not in methods:
            issues.append(ValidationIssue(
                severity="error",
                migration=migration_name,
                message="Missing up() method"
            ))
        
        if "down" not in methods:
            issues.append(ValidationIssue(
                severity="warning",
                migration=migration_name,
                message="Missing down() method",
                suggestion="Add down() method for rollback capability"
            ))
        
        return issues
    
    def _validate_operations(self, tree: ast.AST, migration_name: str) -> List[ValidationIssue]:
        """Validate migration operations."""
        issues = []
        
        # Extract table operations
        operations = self._extract_operations(tree)
        
        for operation in operations:
            issues.extend(self._validate_table_operation(operation, migration_name))
        
        return issues
    
    def _extract_operations(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract table operations from AST."""
        operations = []
        
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and
                isinstance(node.func, ast.Attribute) and
                node.func.attr in ["create_table", "modify_table", "drop_table"]):
                
                operation = {
                    "type": node.func.attr,
                    "table": self._get_string_arg(node, 0),
                    "line": node.lineno
                }
                operations.append(operation)
        
        return operations
    
    def _get_string_arg(self, call_node: ast.Call, index: int) -> Optional[str]:
        """Extract string argument from function call."""
        if len(call_node.args) > index and isinstance(call_node.args[index], ast.Constant):
            return call_node.args[index].value
        return None
    
    def _validate_table_operation(self, operation: Dict[str, Any], migration_name: str) -> List[ValidationIssue]:
        """Validate a specific table operation."""
        issues = []
        
        table_name = operation.get("table")
        op_type = operation.get("type")
        
        if not table_name:
            issues.append(ValidationIssue(
                severity="error",
                migration=migration_name,
                message=f"Missing table name for {op_type} operation",
                line_number=operation.get("line")
            ))
            return issues
        
        # Validate table naming conventions
        if not re.match(r'^[a-z][a-z0-9_]*$', table_name):
            issues.append(ValidationIssue(
                severity="warning",
                migration=migration_name,
                message=f"Table name '{table_name}' doesn't follow naming convention",
                suggestion="Use snake_case with lowercase letters",
                line_number=operation.get("line")
            ))
        
        # Check for table existence conflicts
        if op_type == "create_table":
            if self.inspector.table_exists(table_name):
                issues.append(ValidationIssue(
                    severity="warning",
                    migration=migration_name,
                    message=f"Table '{table_name}' already exists",
                    suggestion="Consider using 'create_table_if_not_exists' or check migration order",
                    line_number=operation.get("line")
                ))
        
        elif op_type in ["modify_table", "drop_table"]:
            if not self.inspector.table_exists(table_name):
                issues.append(ValidationIssue(
                    severity="error",
                    migration=migration_name,
                    message=f"Table '{table_name}' does not exist",
                    line_number=operation.get("line")
                ))
        
        return issues
    
    def _validate_database_compatibility(self, tree: ast.AST, migration_name: str) -> List[ValidationIssue]:
        """Validate database-specific features."""
        issues = []
        
        # Check for database-specific features
        db_specific_methods = {
            "mysql_": ["mysql"],
            "postgresql_": ["postgresql"],
            "geometry": ["mysql", "postgresql"],
            "jsonb": ["postgresql"],
            "fulltext": ["mysql"],
            "gin_index": ["postgresql"],
            "gist_index": ["postgresql"]
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                
                for prefix, databases in db_specific_methods.items():
                    if method_name.startswith(prefix) or method_name in db_specific_methods:
                        issues.append(ValidationIssue(
                            severity="info",
                            migration=migration_name,
                            message=f"Using database-specific feature: {method_name}",
                            suggestion=f"This feature requires: {', '.join(databases)}",
                            line_number=node.lineno
                        ))
        
        return issues
    
    def dry_run_migration(self, migration_name: str) -> DryRunResult:
        """Perform a dry-run of a migration."""
        migration_path = self.migrations_path / f"{migration_name}.py"
        
        if not migration_path.exists():
            return DryRunResult(
                migration_name=migration_name,
                sql_statements=[],
                warnings=[f"Migration file not found: {migration_path}"]
            )
        
        # Generate SQL statements that would be executed
        sql_statements = self._generate_sql_preview(migration_name)
        warnings = self._check_potential_issues(migration_name)
        
        return DryRunResult(
            migration_name=migration_name,
            sql_statements=sql_statements,
            warnings=warnings,
            estimated_time=self._estimate_execution_time(sql_statements),
            affected_rows=self._estimate_affected_rows(sql_statements)
        )
    
    def _generate_sql_preview(self, migration_name: str) -> List[str]:
        """Generate preview of SQL statements that would be executed."""
        # This would require implementing SQL generation from Blueprint operations
        # For now, return placeholder statements
        statements = [
            f"-- SQL preview for {migration_name}",
            "-- This would show the actual SQL statements to be executed"
        ]
        
        # Parse migration and extract operations
        migration_path = self.migrations_path / f"{migration_name}.py"
        try:
            with open(migration_path, 'r') as f:
                content = f.read()
            
            # Simple pattern matching for common operations
            if "create_table" in content:
                table_match = re.search(r'create_table\(["\'](\w+)["\']', content)
                if table_match:
                    table_name = table_match.group(1)
                    statements.append(f"CREATE TABLE {table_name} (...);")
            
            if "modify_table" in content:
                table_match = re.search(r'modify_table\(["\'](\w+)["\']', content)
                if table_match:
                    table_name = table_match.group(1)
                    statements.append(f"ALTER TABLE {table_name} ...;")
            
            if "drop_table" in content:
                table_match = re.search(r'drop_table\(["\'](\w+)["\']', content)
                if table_match:
                    table_name = table_match.group(1)
                    statements.append(f"DROP TABLE {table_name};")
        
        except Exception as e:
            statements.append(f"-- Error generating preview: {e}")
        
        return statements
    
    def _check_potential_issues(self, migration_name: str) -> List[str]:
        """Check for potential issues that might occur during execution."""
        warnings = []
        
        validation_issues = self.validate_migration(migration_name)
        
        for issue in validation_issues:
            if issue.severity in ["error", "warning"]:
                warnings.append(f"{issue.severity.upper()}: {issue.message}")
        
        return warnings
    
    def _estimate_execution_time(self, sql_statements: List[str]) -> Optional[float]:
        """Estimate execution time based on SQL statements."""
        # Simple heuristic based on statement types
        base_time = 0.1  # Base time per statement
        
        for statement in sql_statements:
            if "CREATE TABLE" in statement:
                base_time += 0.5
            elif "ALTER TABLE" in statement:
                base_time += 1.0
            elif "DROP TABLE" in statement:
                base_time += 0.3
            elif "CREATE INDEX" in statement:
                base_time += 2.0  # Indexes can be slow
        
        return base_time
    
    def _estimate_affected_rows(self, sql_statements: List[str]) -> Optional[int]:
        """Estimate number of rows affected by the migration."""
        # This would require analyzing the statements and checking table sizes
        # For now, return a placeholder
        return None
    
    def check_rollback_safety(self, migration_name: str) -> List[ValidationIssue]:
        """Check if a migration can be safely rolled back."""
        issues = []
        migration_path = self.migrations_path / f"{migration_name}.py"
        
        try:
            with open(migration_path, 'r') as f:
                content = f.read()
            
            # Check for destructive operations
            destructive_operations = [
                "drop_table",
                "drop_column",
                "drop_index",
                "drop_foreign"
            ]
            
            for operation in destructive_operations:
                if operation in content:
                    issues.append(ValidationIssue(
                        severity="warning",
                        migration=migration_name,
                        message=f"Destructive operation detected: {operation}",
                        suggestion="Ensure down() method can properly restore data"
                    ))
            
            # Check if down() method exists
            tree = ast.parse(content)
            has_down_method = False
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == "down":
                    has_down_method = True
                    
                    # Check if down() method is implemented
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        issues.append(ValidationIssue(
                            severity="error",
                            migration=migration_name,
                            message="down() method is not implemented",
                            suggestion="Implement rollback logic in down() method"
                        ))
            
            if not has_down_method:
                issues.append(ValidationIssue(
                    severity="error",
                    migration=migration_name,
                    message="No down() method found",
                    suggestion="Add down() method for rollback capability"
                ))
        
        except Exception as e:
            issues.append(ValidationIssue(
                severity="error",
                migration=migration_name,
                message=f"Error analyzing rollback safety: {e}"
            ))
        
        return issues
    
    def validate_migration_sequence(self, migrations: List[str]) -> List[ValidationIssue]:
        """Validate a sequence of migrations for potential conflicts."""
        issues = []
        
        table_operations = {}
        
        for migration in migrations:
            migration_path = self.migrations_path / f"{migration}.py"
            if not migration_path.exists():
                continue
            
            try:
                with open(migration_path, 'r') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                operations = self._extract_operations(tree)
                
                for operation in operations:
                    table_name = operation.get("table")
                    op_type = operation.get("type")
                    
                    if table_name:
                        if table_name not in table_operations:
                            table_operations[table_name] = []
                        
                        table_operations[table_name].append({
                            "migration": migration,
                            "operation": op_type,
                            "line": operation.get("line")
                        })
            
            except Exception:
                continue
        
        # Check for conflicts
        for table_name, ops in table_operations.items():
            # Check for multiple table creations
            create_ops = [op for op in ops if op["operation"] == "create_table"]
            if len(create_ops) > 1:
                issues.append(ValidationIssue(
                    severity="error",
                    migration="sequence",
                    message=f"Multiple create_table operations for table '{table_name}'",
                    suggestion="Ensure only one migration creates each table"
                ))
            
            # Check for operations on non-existent tables
            for i, op in enumerate(ops):
                if op["operation"] in ["modify_table", "drop_table"]:
                    # Check if table was created in a previous operation
                    previous_creates = [
                        prev_op for j, prev_op in enumerate(ops) 
                        if j < i and prev_op["operation"] == "create_table"
                    ]
                    
                    if not previous_creates and not self.inspector.table_exists(table_name):
                        issues.append(ValidationIssue(
                            severity="warning",
                            migration=op["migration"],
                            message=f"Operation on potentially non-existent table '{table_name}'",
                            suggestion="Ensure table creation migration runs first"
                        ))
        
        return issues