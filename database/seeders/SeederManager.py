from __future__ import annotations

import importlib
import importlib.util
from typing import List, Dict, Optional, Any, Type, TypeVar, Generic, final, Literal, TypedDict, Protocol, runtime_checkable
from pathlib import Path
from abc import ABC, abstractmethod
from sqlalchemy import create_engine
from sqlalchemy.schema import MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import logging
from contextlib import contextmanager
from dataclasses import dataclass

from config.database import DATABASE_URL

# Laravel 12 enhanced type definitions for seeders
SeederName = str
ModelCount = int
SeederMode = Literal['normal', 'test', 'demo', 'production']

class SeederOptions(TypedDict, total=False):
    """Type-safe seeder options for Laravel 12."""
    mode: SeederMode
    batch_size: int
    truncate_before: bool
    disable_foreign_keys: bool
    transaction: bool
    quiet: bool
    force: bool

class SeederResult(TypedDict):
    """Type-safe seeder execution result."""
    name: SeederName
    success: bool
    records_created: ModelCount
    execution_time: float
    error: Optional[str]

@dataclass(frozen=True)
class SeederMetadata:
    """Immutable seeder metadata for Laravel 12."""
    name: SeederName
    description: str
    dependencies: List[SeederName]
    priority: int = 0
    environments: List[str] = None
    
    def __post_init__(self) -> None:
        if self.environments is None:
            object.__setattr__(self, 'environments', ['development', 'testing', 'staging'])

@runtime_checkable
class SeederInterface(Protocol):
    """Laravel 12-style seeder interface protocol."""
    
    def run(self) -> SeederResult:
        """Run the seeder and return result."""
        ...
    
    def should_run(self) -> bool:
        """Check if seeder should run in current environment."""
        ...
    
    def get_metadata(self) -> SeederMetadata:
        """Get seeder metadata."""
        ...

T = TypeVar('T', bound='Seeder')
S = TypeVar('S', bound='SeederManager')


@final
class Seeder(ABC, Generic[T]):
    """Laravel 12-style base seeder class with enhanced type safety and features."""
    
    def __init__(self, session: Optional[Session] = None, options: Optional[SeederOptions] = None) -> None:
        self.engine: Optional[Engine] = None
        self.session: Optional[Session] = session
        self.options: SeederOptions = options or {
            'mode': 'normal',
            'batch_size': 1000,
            'truncate_before': False,
            'disable_foreign_keys': False,
            'transaction': True,
            'quiet': False,
            'force': False
        }
        self.logger = logging.getLogger(self.__class__.__name__)
        self._metadata: Optional[SeederMetadata] = None
    
    def get_engine(self) -> Engine:
        """Get database engine with enhanced error handling."""
        if self.engine is None:
            try:
                self.engine = create_engine(DATABASE_URL)
            except Exception as e:
                raise RuntimeError(f"Failed to create database engine: {e}") from e
        return self.engine
    
    @abstractmethod
    def run(self) -> SeederResult:
        """Run the seeder and return execution result."""
        pass
    
    def should_run(self) -> bool:
        """Check if seeder should run in current environment."""
        import os
        current_env = os.getenv('APP_ENV', 'development')
        metadata = self.get_metadata()
        
        # Check if current environment is allowed
        if metadata.environments and current_env not in metadata.environments:
            return False
        
        # In production, require explicit force flag
        if current_env == 'production' and not self.options.get('force', False):
            return False
        
        return True
    
    def get_metadata(self) -> SeederMetadata:
        """Get seeder metadata."""
        if self._metadata is None:
            self._metadata = SeederMetadata(
                name=self.__class__.__name__,
                description=self.__class__.__doc__ or "No description provided",
                dependencies=[],
                priority=0
            )
        return self._metadata
    
    def set_metadata(self, metadata: SeederMetadata) -> None:
        """Set seeder metadata."""
        self._metadata = metadata
    
    def call(self, seeder_classes: List[Type[Seeder[T]]]) -> List[SeederResult]:
        """Call other seeders with enhanced error handling and result tracking."""
        results: List[SeederResult] = []
        
        for seeder_class in seeder_classes:
            try:
                seeder = seeder_class(self.session, self.options)
                
                if not seeder.should_run():
                    self.logger.info(f"Skipping {seeder_class.__name__} (conditions not met)")
                    continue
                
                if not self.options.get('quiet', False):
                    self.logger.info(f"Seeding: {seeder_class.__name__}")
                
                result = seeder.run()
                results.append(result)
                
                if not self.options.get('quiet', False):
                    self.logger.info(f"Seeded: {seeder_class.__name__} ({result['records_created']} records)")
                    
            except Exception as e:
                error_result: SeederResult = {
                    'name': seeder_class.__name__,
                    'success': False,
                    'records_created': 0,
                    'execution_time': 0.0,
                    'error': str(e)
                }
                results.append(error_result)
                self.logger.error(f"Failed to seed {seeder_class.__name__}: {e}")
                
                if not self.options.get('force', False):
                    raise
        
        return results
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        if not self.session:
            raise RuntimeError("No database session available")
        
        if not self.options.get('transaction', True):
            yield
            return
        
        try:
            self.session.begin()
            yield
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
    
    def truncate_table(self, table_name: str) -> None:
        """Truncate a table with validation."""
        if not table_name or not isinstance(table_name, str):
            raise ValueError(f"Invalid table name: {table_name}")
        
        if not self.session:
            raise RuntimeError("No database session available")
        
        try:
            self.session.execute(f"DELETE FROM {table_name}")
            self.session.commit()
            self.logger.debug(f"Truncated table: {table_name}")
        except Exception as e:
            self.logger.error(f"Failed to truncate table {table_name}: {e}")
            raise
    
    def disable_foreign_key_checks(self) -> None:
        """Disable foreign key checks."""
        if not self.session:
            return
        
        try:
            self.session.execute("PRAGMA foreign_keys = OFF")
            self.session.commit()
        except Exception as e:
            self.logger.warning(f"Could not disable foreign key checks: {e}")
    
    def enable_foreign_key_checks(self) -> None:
        """Enable foreign key checks."""
        if not self.session:
            return
        
        try:
            self.session.execute("PRAGMA foreign_keys = ON")
            self.session.commit()
        except Exception as e:
            self.logger.warning(f"Could not enable foreign key checks: {e}")


@final
class SeederManager(Generic[S]):
    """Laravel 12-style seeder manager with enhanced features and type safety."""
    
    def __init__(self, seeders_path: str = "database/seeders", options: Optional[SeederOptions] = None) -> None:
        self.seeders_path = Path(seeders_path)
        self.engine: Optional[Engine] = None
        self.options: SeederOptions = options or {
            'mode': 'normal',
            'batch_size': 1000,
            'truncate_before': False,
            'disable_foreign_keys': False,
            'transaction': True,
            'quiet': False,
            'force': False
        }
        self.logger = logging.getLogger(self.__class__.__name__)
        self._execution_results: List[SeederResult] = []
    
    def get_engine(self) -> Engine:
        """Get database engine with error handling."""
        if self.engine is None:
            try:
                self.engine = create_engine(DATABASE_URL)
            except Exception as e:
                raise RuntimeError(f"Failed to create database engine: {e}") from e
        return self.engine
    
    def get_seeder_files(self) -> List[SeederName]:
        """Get all seeder files with validation."""
        seeder_files: List[SeederName] = []
        
        if not self.seeders_path.exists():
            raise FileNotFoundError(f"Seeders directory not found: {self.seeders_path}")
        
        for file_path in self.seeders_path.glob("*.py"):
            if file_path.name.endswith("_seeder.py") or file_path.name.endswith("Seeder.py"):
                # Skip manager files
                if file_path.name in ["SeederManager.py", "__init__.py"]:
                    continue
                seeder_files.append(file_path.stem)
        
        return sorted(seeder_files)
    
    def load_seeder_class(self, seeder_name: SeederName) -> Optional[Type[Seeder[T]]]:
        """Load seeder class dynamically with enhanced error handling."""
        if not seeder_name or not isinstance(seeder_name, str):
            raise ValueError(f"Invalid seeder name: {seeder_name}")
        
        try:
            module_path = self.seeders_path / f"{seeder_name}.py"
            
            if not module_path.exists():
                self.logger.error(f"Seeder file not found: {module_path}")
                return None
            
            spec = importlib.util.spec_from_file_location(seeder_name, module_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find seeder class in module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, Seeder) and 
                        attr != Seeder):
                        return attr
            
            self.logger.error(f"No valid seeder class found in {seeder_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error loading seeder {seeder_name}: {e}")
            return None
    
    def seed(self, seeder_classes: Optional[List[SeederName]] = None) -> List[SeederResult]:
        """Run database seeders with Laravel 12 enhancements."""
        results: List[SeederResult] = []
        
        if seeder_classes is None:
            seeder_files = self.get_seeder_files()
            # Always run DatabaseSeeder first if it exists
            if "DatabaseSeeder" in seeder_files:
                seeder_classes = ["DatabaseSeeder"]
            else:
                seeder_classes = seeder_files
        
        if not self.options.get('quiet', False):
            self.logger.info(f"Running {len(seeder_classes)} seeders...")
        
        for seeder_name in seeder_classes:
            try:
                seeder_class = self.load_seeder_class(seeder_name)
                if seeder_class:
                    seeder = seeder_class(options=self.options)
                    
                    if not seeder.should_run():
                        self.logger.info(f"Skipping {seeder_name} (conditions not met)")
                        continue
                    
                    if not self.options.get('quiet', False):
                        self.logger.info(f"Seeding: {seeder_name}")
                    
                    result = seeder.run()
                    results.append(result)
                    self._execution_results.append(result)
                    
                    if not self.options.get('quiet', False):
                        self.logger.info(f"Seeded: {seeder_name} ({result['records_created']} records)")
                    
                    # Stop on failure unless force flag is set
                    if not result['success'] and not self.options.get('force', False):
                        break
                        
                else:
                    error_result: SeederResult = {
                        'name': seeder_name,
                        'success': False,
                        'records_created': 0,
                        'execution_time': 0.0,
                        'error': 'Could not load seeder class'
                    }
                    results.append(error_result)
                    self.logger.error(f"Could not load seeder: {seeder_name}")
                    
            except Exception as e:
                error_result: SeederResult = {
                    'name': seeder_name,
                    'success': False,
                    'records_created': 0,
                    'execution_time': 0.0,
                    'error': str(e)
                }
                results.append(error_result)
                self.logger.error(f"Seeding failed: {seeder_name} - {e}")
                
                if not self.options.get('force', False):
                    break
        
        return results
    
    def make_seeder(self, name: str, model: Optional[str] = None) -> str:
        """Create a new seeder file."""
        seeder_name = name if name.endswith("Seeder") else f"{name}Seeder"
        filename = f"{seeder_name}.py"
        file_path = self.seeders_path / filename
        
        if model:
            content = self._generate_model_seeder(seeder_name, model)
        else:
            content = self._generate_blank_seeder(seeder_name)
        
        with open(file_path, 'w') as f:
            f.write(content)
        
        return filename
    
    def get_execution_results(self) -> List[SeederResult]:
        """Get execution results from the last seeding run."""
        return self._execution_results.copy()
    
    def clear_execution_results(self) -> None:
        """Clear execution results."""
        self._execution_results.clear()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of seeding execution with Laravel 12 validation."""
        if not self._execution_results:
            return {
                'total_seeders': 0,
                'successful_seeders': 0,
                'failed_seeders': 0,
                'total_records_created': 0,
                'total_execution_time': 0.0,
                'success_rate': 0.0
            }
        
        total_records = sum(result['records_created'] for result in self._execution_results if result['success'])
        total_time = sum(result['execution_time'] for result in self._execution_results)
        success_count = sum(1 for result in self._execution_results if result['success'])
        failure_count = len(self._execution_results) - success_count
        
        return {
            'total_seeders': len(self._execution_results),
            'successful_seeders': success_count,
            'failed_seeders': failure_count,
            'total_records_created': total_records,
            'total_execution_time': total_time,
            'success_rate': (success_count / len(self._execution_results)) * 100
        }
    
    def _generate_model_seeder(self, seeder_name: str, model: str) -> str:
        """Generate model-specific seeder content."""
        return f'''from __future__ import annotations

from database.seeders.SeederManager import Seeder
from app.Models.{model} import {model}
from database.factories.{model}Factory import {model}Factory


class {seeder_name}(Seeder):
    """Seeder for {model} model."""
    
    def run(self) -> None:
        """Run the seeder."""
        # Create {model} records using factory
        factory = {model}Factory()
        
        # Create 10 sample records
        for _ in range(10):
            data = factory.definition()
            {model}.create(**data)
        
        print(f"Created 10 {{model}} records")
'''
    
    def _generate_blank_seeder(self, seeder_name: str) -> str:
        """Generate blank seeder content."""
        return f'''from __future__ import annotations

from database.seeders.SeederManager import Seeder


class {seeder_name}(Seeder):
    """Database seeder."""
    
    def run(self) -> None:
        """Run the seeder."""
        # Add your seeding logic here
        pass
'''


# Legacy DatabaseSeeder class removed - use DatabaseSeeder.py instead


class MigrationSeederIntegration:
    """Integrates seeders with migration system."""
    
    def __init__(self, migration_manager: Any, seeder_manager: SeederManager) -> None:
        self.migration_manager = migration_manager
        self.seeder_manager = seeder_manager
    
    def migrate_and_seed(self, run_seeders: bool = False) -> None:
        """Run migrations and optionally seed database."""
        print("Running migrations...")
        executed_migrations = self.migration_manager.migrate()
        
        if executed_migrations:
            print(f"Migrated {len(executed_migrations)} migrations successfully.")
            
            if run_seeders:
                print("Running seeders...")
                self.seeder_manager.seed()
                print("Seeding completed.")
        else:
            print("Nothing to migrate.")
            
            if run_seeders:
                print("Running seeders...")
                self.seeder_manager.seed()
                print("Seeding completed.")
    
    def fresh_and_seed(self) -> None:
        """Fresh migration with seeding."""
        print("Freshening database...")
        self.migration_manager.fresh()
        
        print("Running seeders...")
        self.seeder_manager.seed()
        print("Database refreshed and seeded.")
    
    def refresh_and_seed(self) -> None:
        """Refresh migrations and seed."""
        print("Refreshing database...")
        self.migration_manager.refresh()
        
        print("Running seeders...")
        self.seeder_manager.seed()
        print("Database refreshed and seeded.")