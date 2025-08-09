from __future__ import annotations

from typing import List, Dict, Set, Optional, Any
from collections import defaultdict, deque
from pathlib import Path
import importlib.util


class MigrationNode:
    """Represents a migration with its dependencies."""
    
    def __init__(self, name: str) -> None:
        self.name = name
        self.dependencies: Set[str] = set()
        self.dependents: Set[str] = set()
        self.batch: Optional[int] = None
        self.executed: bool = False
    
    def add_dependency(self, dependency: str) -> None:
        """Add a dependency to this migration."""
        self.dependencies.add(dependency)
    
    def add_dependent(self, dependent: str) -> None:
        """Add a dependent to this migration."""
        self.dependents.add(dependent)


class MigrationGraph:
    """Manages migration dependencies and execution order."""
    
    def __init__(self) -> None:
        self.nodes: Dict[str, MigrationNode] = {}
        self.migrations_path = Path("database/migrations")
    
    def add_migration(self, name: str, dependencies: Optional[List[str]] = None) -> None:
        """Add a migration to the dependency graph."""
        if name not in self.nodes:
            self.nodes[name] = MigrationNode(name)
        
        if dependencies:
            for dep in dependencies:
                if dep not in self.nodes:
                    self.nodes[dep] = MigrationNode(dep)
                
                self.nodes[name].add_dependency(dep)
                self.nodes[dep].add_dependent(name)
    
    def get_execution_order(self) -> List[str]:
        """Get migrations in topological order for execution."""
        # Kahn's algorithm for topological sorting
        in_degree = {name: len(node.dependencies) for name, node in self.nodes.items()}
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for dependent in self.nodes[current].dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        if len(result) != len(self.nodes):
            raise ValueError("Circular dependency detected in migrations")
        
        return result
    
    def get_rollback_order(self) -> List[str]:
        """Get migrations in reverse topological order for rollback."""
        return list(reversed(self.get_execution_order()))
    
    def validate_dependencies(self) -> List[str]:
        """Validate all dependencies exist and return any errors."""
        errors = []
        
        for name, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    errors.append(f"Migration '{name}' depends on non-existent migration '{dep}'")
        
        try:
            self.get_execution_order()
        except ValueError as e:
            errors.append(str(e))
        
        return errors
    
    def get_migration_batches(self, executed_migrations: Set[str]) -> Dict[int, List[str]]:
        """Organize migrations into batches for execution."""
        execution_order = self.get_execution_order()
        batches: Dict[int, List[str]] = defaultdict(list)
        
        # Mark executed migrations
        for name in executed_migrations:
            if name in self.nodes:
                self.nodes[name].executed = True
        
        # Assign batch numbers
        batch_number = 1
        for migration in execution_order:
            if not self.nodes[migration].executed:
                # Check if all dependencies are executed
                can_execute = all(
                    self.nodes[dep].executed 
                    for dep in self.nodes[migration].dependencies
                )
                
                if can_execute:
                    self.nodes[migration].batch = batch_number
                    batches[batch_number].append(migration)
        
        return dict(batches)


class DependencyResolver:
    """Resolves migration dependencies by analyzing migration files."""
    
    def __init__(self, migrations_path: str = "database/migrations") -> None:
        self.migrations_path = Path(migrations_path)
        self.graph = MigrationGraph()
    
    def analyze_migration_file(self, migration_name: str) -> List[str]:
        """Analyze a migration file to extract dependencies."""
        dependencies = []
        
        try:
            module_path = self.migrations_path / f"{migration_name}.py"
            spec = importlib.util.spec_from_file_location(migration_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Look for migration class with dependencies attribute
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        hasattr(attr, '__bases__') and
                        any('Migration' in base.__name__ for base in attr.__bases__)):
                        
                        # Check for dependencies attribute
                        if hasattr(attr, 'dependencies'):
                            dependencies = attr.dependencies
                        
                        # Analyze table dependencies from foreign keys
                        if hasattr(attr, 'get_table_dependencies'):
                            table_deps = attr.get_table_dependencies()
                            dependencies.extend(table_deps)
                        
                        break
        
        except Exception as e:
            print(f"Warning: Could not analyze dependencies for {migration_name}: {e}")
        
        return dependencies
    
    def build_dependency_graph(self, migration_files: List[str]) -> MigrationGraph:
        """Build complete dependency graph from migration files."""
        # Add implicit dependencies based on table creation order
        table_migrations = {}
        
        for migration_name in migration_files:
            dependencies = self.analyze_migration_file(migration_name)
            
            # Add table creation dependencies
            if migration_name.startswith('create_'):
                table_name = self._extract_table_name(migration_name)
                table_migrations[table_name] = migration_name
            
            # Add foreign key dependencies
            if 'foreign' in migration_name.lower() or '_table' in migration_name:
                referenced_tables = self._extract_referenced_tables(migration_name)
                for table in referenced_tables:
                    if table in table_migrations:
                        dependencies.append(table_migrations[table])
            
            self.graph.add_migration(migration_name, dependencies)
        
        return self.graph
    
    def _extract_table_name(self, migration_name: str) -> str:
        """Extract table name from migration name."""
        if migration_name.startswith('create_'):
            table_name = migration_name[7:]  # Remove 'create_'
            if table_name.endswith('_table'):
                table_name = table_name[:-6]  # Remove '_table'
            return table_name
        return migration_name
    
    def _extract_referenced_tables(self, migration_name: str) -> List[str]:
        """Extract referenced table names from migration name."""
        referenced_tables = []
        
        # Common patterns for foreign key migrations
        if 'user' in migration_name and 'users' not in migration_name:
            referenced_tables.append('users')
        
        if 'role' in migration_name and 'roles' not in migration_name:
            referenced_tables.append('roles')
        
        if 'permission' in migration_name and 'permissions' not in migration_name:
            referenced_tables.append('permissions')
        
        # Add more patterns as needed
        
        return referenced_tables


class BatchManager:
    """Manages migration batches for organized execution."""
    
    def __init__(self) -> None:
        self.batches: Dict[int, List[str]] = {}
        self.current_batch = 1
    
    def create_batch(self, migrations: List[str]) -> int:
        """Create a new batch with given migrations."""
        batch_id = self.current_batch
        self.batches[batch_id] = migrations
        self.current_batch += 1
        return batch_id
    
    def get_batch(self, batch_id: int) -> List[str]:
        """Get migrations in a specific batch."""
        return self.batches.get(batch_id, [])
    
    def get_latest_batch(self) -> Optional[int]:
        """Get the latest batch number."""
        return max(self.batches.keys()) if self.batches else None
    
    def rollback_batch(self, batch_id: int) -> List[str]:
        """Get migrations to rollback for a specific batch."""
        if batch_id in self.batches:
            return list(reversed(self.batches[batch_id]))
        return []