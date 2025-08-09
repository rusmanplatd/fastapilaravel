from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import List, Optional
from .BaseMakeCommand import BaseMakeCommand
from ..Command import Command


class MakeModelCommand(BaseMakeCommand):
    """Generate a new Eloquent model."""
    
    file_type = "Model"
    
    signature = "make:model {name : The name of the model} {--migration : Create a migration file for the model} {--controller : Create a controller for the model} {--resource : Create resource controller methods} {--factory : Create a model factory} {--seeder : Create a seeder for the model} {--policy : Create a policy for the model} {--observer : Create an observer for the model} {--pivot : Create a pivot model} {--all : Create all associated files (migration, controller, factory, seeder, policy, observer)}"
    description = "Create a new Eloquent model class"
    help = "Generate a new model class with optional migration, controller, factory, and seeder"
    
    aliases = ["make:m"]
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        create_all = self.option("all", False)
        create_migration = self.option("migration", False) or create_all
        create_controller = self.option("controller", False) or create_all
        create_resource = self.option("resource", False) or create_all
        create_factory = self.option("factory", False) or create_all
        create_seeder = self.option("seeder", False) or create_all
        create_policy = self.option("policy", False) or create_all
        create_observer = self.option("observer", False) or create_all
        is_pivot = self.option("pivot", False)
        
        if not name:
            self.error("Model name is required")
            return
        
        # Ensure proper naming
        model_name = self._format_model_name(name)
        
        # Check if model exists
        model_path = Path(f"app/Models/{model_name}.py")
        if model_path.exists():
            if not self.confirm(f"Model {model_name} already exists. Overwrite?"):
                self.info("Model creation cancelled.")
                return
        
        # Generate model
        await self._create_model(model_name, is_pivot)
        
        # Generate migration if requested
        if create_migration:
            await self._create_migration(model_name, is_pivot)
        
        # Generate controller if requested
        if create_controller:
            await self._create_controller(model_name, create_resource)
        
        # Generate factory if requested
        if create_factory:
            await self._create_factory(model_name)
        
        # Generate seeder if requested
        if create_seeder:
            await self._create_seeder(model_name)
        
        # Generate policy if requested
        if create_policy:
            await self._create_policy(model_name)
        
        # Generate observer if requested
        if create_observer:
            await self._create_observer(model_name)
        
        model_type = "Pivot model" if is_pivot else "Model"
        self.info(f"✅ {model_type} {model_name} created successfully!")
        
        # Show summary of created files
        created_files = ["Model"]
        if create_migration: created_files.append("Migration")
        if create_controller: created_files.append("Controller") 
        if create_factory: created_files.append("Factory")
        if create_seeder: created_files.append("Seeder")
        if create_policy: created_files.append("Policy")
        if create_observer: created_files.append("Observer")
        
        if len(created_files) > 1:
            self.comment(f"Created: {', '.join(created_files)}")
    
    def _format_model_name(self, name: str) -> str:
        """Format model name to proper case."""
        # Remove any file extension
        name = name.replace('.py', '')
        # Capitalize first letter of each word
        return ''.join(word.capitalize() for word in name.split('_'))
    
    async def _create_model(self, model_name: str, is_pivot: bool = False) -> None:
        """Create the model file."""
        model_path = Path(f"app/Models/{model_name}.py")
        
        # Ask for table name
        table_name = self.ask(f"Table name for {model_name}", self._get_table_name(model_name))
        
        # Ask for common fields
        has_timestamps = self.confirm("Include timestamps (created_at, updated_at)?", True)
        has_soft_deletes = self.confirm("Include soft deletes (deleted_at)?", False)
        
        # Validate dependencies
        dependencies = ["app/Models/BaseModel.py"]
        if not await self._validate_dependencies(dependencies):
            return
        
        content = self._generate_model_content(model_name, table_name, has_timestamps, has_soft_deletes, is_pivot)
        
        # Use standardized file creation
        success = await self.create_file(model_name, content, model_path)
        
        if success:
            # Show additional next steps for models
            additional_steps = [
                f"Define the {table_name} table structure in a migration",
                "Add model relationships if needed",
                "Configure fillable/hidden attributes"
            ]
            self._show_next_steps(model_path, additional_steps)
    
    async def _create_migration(self, model_name: str, is_pivot: bool = False) -> None:
        """Create migration for the model."""
        table_name = self._get_table_name(model_name)
        migration_name = f"create_{table_name}_table"
        
        await self.call("make:migration", {
            "name": migration_name,
            "--create": table_name
        })
    
    async def _create_controller(self, model_name: str, is_resource: bool) -> None:
        """Create controller for the model."""
        controller_name = f"{model_name}Controller"
        
        args = {"name": controller_name}
        if is_resource:
            args["--resource"] = "true"
            
        await self.call("make:controller", args)
    
    async def _create_factory(self, model_name: str) -> None:
        """Create factory for the model."""
        factory_path = Path(f"database/factories/{model_name}Factory.py")
        factory_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = self._generate_factory_content(model_name)
        factory_path.write_text(content)
        
        self.comment(f"Created factory: {factory_path}")
    
    async def _create_seeder(self, model_name: str) -> None:
        """Create seeder for the model."""
        seeder_path = Path(f"database/seeders/{model_name}Seeder.py")
        seeder_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = self._generate_seeder_content(model_name)
        seeder_path.write_text(content)
        
        self.comment(f"Created seeder: {seeder_path}")
    
    async def _create_policy(self, model_name: str) -> None:
        """Create policy for the model."""
        policy_name = f"{model_name}Policy"
        
        await self.call("make:policy", {
            "name": policy_name,
            "--model": model_name
        })
    
    async def _create_observer(self, model_name: str) -> None:
        """Create observer for the model."""
        observer_name = f"{model_name}Observer"
        
        await self.call("make:observer", {
            "name": observer_name,
            "--model": model_name
        })
    
    def _get_table_name(self, model_name: str) -> str:
        """Convert model name to table name."""
        # Convert CamelCase to snake_case and pluralize
        import re
        table_name = re.sub(r'(?<!^)(?=[A-Z])', '_', model_name).lower()
        
        # Simple pluralization
        if table_name.endswith('y'):
            return table_name[:-1] + 'ies'
        elif table_name.endswith(('s', 'sh', 'ch', 'x', 'z')):
            return table_name + 'es'
        else:
            return table_name + 's'
    
    def _generate_model_content(self, model_name: str, table_name: str, 
                              has_timestamps: bool, has_soft_deletes: bool, is_pivot: bool = False) -> str:
        """Generate model file content."""
        imports = [
            "from __future__ import annotations",
            "",
            "from typing import Optional, List",
            "from sqlalchemy import Column, Integer, String, DateTime, Boolean",
            "from sqlalchemy.orm import relationship",
        ]
        
        if has_timestamps or has_soft_deletes:
            imports.append("from datetime import datetime")
        
        imports.extend([
            "",
            "from app.Models.BaseModel import BaseModel",
            "from app.Traits.HasFactory import HasFactory",
        ])
        
        if has_timestamps:
            imports.append("from app.Traits.HasTimestamps import HasTimestamps")
        
        if has_soft_deletes:
            imports.append("from app.Traits.SoftDeletes import SoftDeletes")
        
        # Model class
        mixins = ["BaseModel", "HasFactory"]
        if has_timestamps:
            mixins.append("HasTimestamps")
        if has_soft_deletes:
            mixins.append("SoftDeletes")
        
        model_class = f"""

class {model_name}({', '.join(mixins)}):
    \"\"\"
    {model_name} model.
    
    Represents {table_name} in the database.
    \"\"\"
    
    __tablename__ = "{table_name}"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Add your model fields here
    # Example:
    # name = Column(String(100), nullable=False, index=True)
    # email = Column(String(255), unique=True, nullable=False, index=True)
    # is_active = Column(Boolean, default=True)
    
    # Fillable fields (for mass assignment protection)
    __fillable__ = [
        # Add field names here
        # "name", "email", "is_active"
    ]
    
    # Hidden fields (not included in serialization)
    __hidden__ = [
        # Add sensitive field names here
        # "password", "api_key"
    ]
    
    # Relationships
    # Example:
    # posts = relationship("Post", back_populates="user")
    
    def __repr__(self) -> str:
        return f"<{model_name}(id={{self.id}})>"
    
    @classmethod
    def create(cls, **kwargs) -> '{model_name}':
        \"\"\"Create a new {model_name} instance.\"\"\"
        return cls(**kwargs)
    
    # Add your custom methods here
    # Example:
    # def get_full_name(self) -> str:
    #     return f"{{self.first_name}} {{self.last_name}}"
"""
        
        return '\n'.join(imports) + model_class
    
    def _generate_factory_content(self, model_name: str) -> str:
        """Generate factory file content."""
        return f'''from __future__ import annotations

from typing import Dict, Any
from faker import Faker
from app.Models.{model_name} import {model_name}
from database.factories.Factory import Factory

fake = Faker()


class {model_name}Factory(Factory):
    """Factory for creating {model_name} instances."""
    
    model = {model_name}
    
    @classmethod
    def definition(cls) -> Dict[str, Any]:
        """Define the model's default state."""
        return {{
            # Add your factory definitions here
            # Example:
            # "name": fake.name(),
            # "email": fake.email(),
            # "is_active": fake.boolean(chance_of_getting_true=80),  # type: ignore[attr-defined]
            # "created_at": fake.date_time_this_year(),  # type: ignore[attr-defined]
        }}
    
    @classmethod
    def active(cls) -> '{model_name}Factory':
        """Factory state for active records."""
        return cls.state({{
            "is_active": True,
        }})
    
    @classmethod
    def inactive(cls) -> '{model_name}Factory':
        """Factory state for inactive records."""
        return cls.state({{
            "is_active": False,
        }})
'''
    
    def _generate_seeder_content(self, model_name: str) -> str:
        """Generate seeder file content."""
        return f'''from __future__ import annotations

from database.seeders.Seeder import Seeder
from app.Models.{model_name} import {model_name}
from database.factories.{model_name}Factory import {model_name}Factory


class {model_name}Seeder(Seeder):
    """Seeder for {model_name} model."""
    
    def run(self) -> None:
        """Run the database seeds."""
        # Create sample {model_name} records
        {model_name}Factory.create_batch(10)
        
        # Or create specific records
        # {model_name}.create(
        #     name="Example {model_name}",
        #     # Add other fields...
        # )
        
        self.command.info(f"Created sample {{model_name}} records")
'''
    
    def _show_summary(self, model_name: str, migration: bool, controller: bool, 
                     factory: bool, seeder: bool) -> None:
        """Show summary of created files."""
        self.new_line()
        self.comment("Files created:")
        
        files = [f"app/Models/{model_name}.py"]
        
        if migration:
            files.append(f"database/migrations/create_{self._get_table_name(model_name)}_table.py")
        if controller:
            files.append(f"app/Http/Controllers/{model_name}Controller.py")
        if factory:
            files.append(f"database/factories/{model_name}Factory.py")
        if seeder:
            files.append(f"database/seeders/{model_name}Seeder.py")
        
        for file in files:
            self.line(f"  • {file}")
        
        self.new_line()
        self.comment("Next steps:")
        self.line("1. Update the model with your specific fields")
        if migration:
            self.line("2. Edit the migration file to define your table structure")
            self.line("3. Run 'python artisan.py migrate' to create the table")
        if factory:
            self.line("4. Update the factory definition with realistic fake data")
        if seeder:
            self.line("5. Run the seeder with 'python artisan.py db:seed --class={model_name}Seeder'")


class MakeMigrationCommand(Command):
    """Generate a new database migration."""
    
    signature = "make:migration {name : The name of the migration} {--create= : Create a new table} {--table= : Modify an existing table}"
    description = "Create a new database migration file"
    help = "Generate a new migration file for database schema changes"
    
    aliases = ["make:mig"]
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        create_table = self.option("create")
        modify_table = self.option("table")
        
        if not name:
            self.error("Migration name is required")
            return
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        migration_name = f"{timestamp}_{name}"
        
        migration_path = Path(f"database/migrations/{migration_name}.py")
        migration_path.parent.mkdir(parents=True, exist_ok=True)
        
        if create_table:
            content = self._generate_create_migration(name, create_table, migration_name)
        elif modify_table:
            content = self._generate_modify_migration(name, modify_table, migration_name)
        else:
            # Ask user what type of migration
            migration_type = self.choice(
                "What type of migration?",
                ["Create table", "Modify table", "Custom"],
                "Custom"
            )
            
            if migration_type == "Create table":
                table_name = self.ask("Table name to create:", "")
                content = self._generate_create_migration(name, table_name, migration_name)
            elif migration_type == "Modify table":
                table_name = self.ask("Table name to modify:", "")
                content = self._generate_modify_migration(name, table_name, migration_name)
            else:
                content = self._generate_custom_migration(name, migration_name)
        
        migration_path.write_text(content)
        
        self.info(f"✅ Migration created: {migration_path}")
        self.comment("Edit the migration file to define your database changes")
        self.comment("Run 'python artisan.py migrate' to execute the migration")
    
    def _generate_create_migration(self, name: str, table_name: str, class_name: str) -> str:
        """Generate a create table migration."""
        formatted_class_name = ''.join(word.capitalize() for word in class_name.split('_'))
        
        return f'''from __future__ import annotations

from database.Schema.Migration import Migration
from database.Schema.Blueprint import Blueprint
from database.Schema import Schema


class {formatted_class_name}(Migration):
    """
    Create {table_name} table migration.
    """
    
    def up(self) -> None:
        """Run the migration."""
        def create_table(table: Blueprint) -> None:
            table.id()
            
            # Add your table columns here
            # Examples:
            # table.string("name", 100).nullable(False).index()
            # table.string("email", 255).unique().nullable(False)
            # table.text("description").nullable()
            # table.boolean("is_active").default(True)
            # table.integer("user_id").foreign_key("users", "id")
            
            table.timestamps()  # created_at, updated_at
            # table.soft_deletes()  # deleted_at (uncomment if needed)
        
        Schema.create("{table_name}", create_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        Schema.drop("{table_name}")
'''
    
    def _generate_modify_migration(self, name: str, table_name: str, class_name: str) -> str:
        """Generate a modify table migration."""
        formatted_class_name = ''.join(word.capitalize() for word in class_name.split('_'))
        
        return f'''from __future__ import annotations

from database.Schema.Migration import Migration
from database.Schema.Blueprint import Blueprint
from database.Schema import Schema


class {formatted_class_name}(Migration):
    """
    Modify {table_name} table migration.
    """
    
    def up(self) -> None:
        """Run the migration."""
        def modify_table(table: Blueprint) -> None:
            # Add your table modifications here
            # Examples:
            # table.string("new_column", 255).nullable()
            # table.rename_column("old_name", "new_name")
            # table.drop_column("unwanted_column")
            # table.index("column_name")
            # table.drop_index("index_name")
            pass
        
        Schema.table("{table_name}", modify_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        def reverse_changes(table: Blueprint) -> None:
            # Reverse the changes made in up()
            # Examples:
            # table.drop_column("new_column")
            # table.rename_column("new_name", "old_name")
            pass
        
        Schema.table("{table_name}", reverse_changes)
'''
    
    def _generate_custom_migration(self, name: str, class_name: str) -> str:
        """Generate a custom migration."""
        formatted_class_name = ''.join(word.capitalize() for word in class_name.split('_'))
        
        return f'''from __future__ import annotations

from database.Schema.Migration import Migration
from database.Schema.Blueprint import Blueprint
from database.Schema import Schema


class {formatted_class_name}(Migration):
    """
    {name} migration.
    """
    
    def up(self) -> None:
        """Run the migration."""
        # Add your migration logic here
        # Examples:
        # Schema.raw("CREATE INDEX CONCURRENTLY idx_name ON table_name (column_name)")
        # Schema.create("table_name", lambda t: t.id().string("name"))
        pass
    
    def down(self) -> None:
        """Reverse the migration."""
        # Add rollback logic here
        pass
'''


class MakeFactoryCommand(Command):
    """Generate a new model factory."""
    
    signature = "make:factory {name : The name of the factory} {--model= : The name of the model}"
    description = "Create a new model factory class"
    help = "Generate a new factory for creating fake model data"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        model_name = self.option("model")
        
        if not name:
            self.error("Factory name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Factory"):
            name += "Factory"
        
        # Determine model name
        if not model_name:
            model_name = name.replace("Factory", "")
        
        factory_path = Path(f"database/factories/{name}.py")
        factory_path.parent.mkdir(parents=True, exist_ok=True)
        
        if factory_path.exists():
            if not self.confirm(f"Factory {name} already exists. Overwrite?"):
                self.info("Factory creation cancelled.")
                return
        
        content = self._generate_factory_content(name, model_name)
        factory_path.write_text(content)
        
        self.info(f"✅ Factory created: {factory_path}")
        self.comment("Update the definition() method with appropriate fake data")
    
    def _generate_factory_content(self, factory_name: str, model_name: str) -> str:
        """Generate factory content."""
        return f'''from __future__ import annotations

from typing import Dict, Any
from faker import Faker
from app.Models.{model_name} import {model_name}
from database.factories.Factory import Factory

fake = Faker()


class {factory_name}(Factory):
    """Factory for creating {model_name} instances."""
    
    model = {model_name}
    
    @classmethod
    def definition(cls) -> Dict[str, Any]:
        """Define the model's default state."""
        return {{
            # Add your factory definitions here using Faker
            # Examples:
            # "name": fake.name(),
            # "email": fake.unique().email(),
            # "phone": fake.phone_number(),
            # "address": fake.address(),
            # "created_at": fake.date_time_this_year(),  # type: ignore[attr-defined]
        }}
    
    @classmethod
    def active(cls) -> '{factory_name}':
        """Create an active {model_name}."""
        return cls.state({{
            "is_active": True,
        }})
    
    @classmethod
    def inactive(cls) -> '{factory_name}':
        """Create an inactive {model_name}."""
        return cls.state({{
            "is_active": False,
        }})
    
    # Add more factory states as needed
'''


class MakeSeederCommand(Command):
    """Generate a new database seeder."""
    
    signature = "make:seeder {name : The name of the seeder}"
    description = "Create a new database seeder class"
    help = "Generate a new seeder for populating database tables with sample data"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if not name:
            self.error("Seeder name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Seeder"):
            name += "Seeder"
        
        seeder_path = Path(f"database/seeders/{name}.py")
        seeder_path.parent.mkdir(parents=True, exist_ok=True)
        
        if seeder_path.exists():
            if not self.confirm(f"Seeder {name} already exists. Overwrite?"):
                self.info("Seeder creation cancelled.")
                return
        
        # Ask for model name if creating a model seeder
        if name.replace("Seeder", "") and name != "DatabaseSeeder":
            model_name = name.replace("Seeder", "")
            has_factory = self.confirm(f"Does {model_name} have a factory?", True)
        else:
            model_name = None
            has_factory = False
        
        content = self._generate_seeder_content(name, model_name, has_factory)
        seeder_path.write_text(content)
        
        self.info(f"✅ Seeder created: {seeder_path}")
        self.comment("Update the run() method to seed your data")
        self.comment(f"Run with: python artisan.py db:seed --class={name}")
    
    def _generate_seeder_content(self, seeder_name: str, model_name: Optional[str] = None, has_factory: bool = False) -> str:
        """Generate seeder content."""
        imports = [
            "from __future__ import annotations",
            "",
            "from database.seeders.Seeder import Seeder",
        ]
        
        if model_name:
            imports.append(f"from app.Models.{model_name} import {model_name}")
            
            if has_factory:
                imports.append(f"from database.factories.{model_name}Factory import {model_name}Factory")
        
        run_method = """    def run(self) -> None:
        \"\"\"Run the database seeds.\"\"\"
        # Add your seeding logic here
        
        # Example with factory:
        # UserFactory.create_batch(50)
        
        # Example with direct creation:
        # User.create(
        #     name="Admin User",
        #     email="admin@example.com",
        #     is_admin=True
        # )
        
        self.command.info("Seeder completed")"""
        
        if model_name and has_factory:
            run_method = f"""    def run(self) -> None:
        \"\"\"Run the database seeds.\"\"\"
        # Create sample {model_name} records using factory
        {model_name}Factory.create_batch(10)
        
        # Create specific records if needed
        # {model_name}.create(
        #     name="Specific {model_name}",
        #     # Add other fields...
        # )
        
        self.command.info(f"Created sample {model_name} records")"""
        
        return '\n'.join(imports) + f'''


class {seeder_name}(Seeder):
    """Database seeder for {model_name or 'sample data'}."""
    
{run_method}
'''


# Register the command
from app.Console.Artisan import register_command
register_command(MakeModelCommand)