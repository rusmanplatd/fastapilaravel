from __future__ import annotations

import importlib
import importlib.util
from typing import List, Dict, Optional, Any, Type
from pathlib import Path
from abc import ABC, abstractmethod
from sqlalchemy import create_engine
from sqlalchemy.schema import MetaData
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from config.database import DATABASE_URL


class Seeder(ABC):
    """Base seeder class similar to Laravel."""
    
    def __init__(self, session: Optional[Session] = None) -> None:
        self.engine: Optional[Engine] = None
        self.session = session
    
    def get_engine(self) -> Engine:
        """Get database engine."""
        if self.engine is None:
            self.engine = create_engine(DATABASE_URL)
        return self.engine
    
    @abstractmethod
    def run(self) -> None:
        """Run the seeder."""
        pass
    
    def call(self, seeder_classes: List[Type[Seeder]]) -> None:
        """Call other seeders."""
        for seeder_class in seeder_classes:
            seeder = seeder_class(self.session)
            print(f"Seeding: {seeder_class.__name__}")
            seeder.run()
            print(f"Seeded: {seeder_class.__name__}")


class SeederManager:
    """Manages database seeders similar to Laravel."""
    
    def __init__(self, seeders_path: str = "database/seeders") -> None:
        self.seeders_path = Path(seeders_path)
        self.engine: Optional[Engine] = None
    
    def get_engine(self) -> Engine:
        """Get database engine."""
        if self.engine is None:
            self.engine = create_engine(DATABASE_URL)
        return self.engine
    
    def get_seeder_files(self) -> List[str]:
        """Get all seeder files."""
        seeder_files = []
        
        for file_path in self.seeders_path.glob("*.py"):
            if file_path.name.endswith("_seeder.py") or file_path.name.endswith("Seeder.py"):
                # Skip manager files
                if file_path.name in ["SeederManager.py", "__init__.py"]:
                    continue
                seeder_files.append(file_path.stem)
        
        return sorted(seeder_files)
    
    def load_seeder_class(self, seeder_name: str) -> Optional[Type[Seeder]]:
        """Load seeder class dynamically."""
        try:
            module_path = self.seeders_path / f"{seeder_name}.py"
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
        except Exception as e:
            print(f"Error loading seeder {seeder_name}: {e}")
        
        return None
    
    def seed(self, seeder_classes: Optional[List[str]] = None) -> None:
        """Run database seeders."""
        if seeder_classes is None:
            seeder_files = self.get_seeder_files()
            # Always run DatabaseSeeder first if it exists
            if "DatabaseSeeder" in seeder_files:
                seeder_classes = ["DatabaseSeeder"]
            else:
                seeder_classes = seeder_files
        
        print("Running seeders...")
        
        for seeder_name in seeder_classes:
            try:
                seeder_class = self.load_seeder_class(seeder_name)
                if seeder_class:
                    seeder = seeder_class()
                    print(f"Seeding: {seeder_name}")
                    seeder.run()
                    print(f"Seeded: {seeder_name}")
                else:
                    print(f"Could not load seeder: {seeder_name}")
            except Exception as e:
                print(f"Seeding failed: {seeder_name} - {e}")
                break
    
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


class DatabaseSeeder(Seeder):
    """Main database seeder that orchestrates all other seeders."""
    
    def run(self) -> None:
        """Run all seeders in order."""
        # Import other seeders
        from database.seeders.user_seeder import seed_users
        from database.seeders.permission_seeder import seed_all_permissions
        from database.seeders.oauth2_seeder import seed_oauth2_data
        from database.seeders.organizational_seeder import seed_organizational_data
        
        # Call seeders in dependency order
        seed_all_permissions()
        seed_users()
        seed_oauth2_data()
        seed_organizational_data()


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