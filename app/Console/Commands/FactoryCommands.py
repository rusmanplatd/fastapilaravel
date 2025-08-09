from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from app.Console.Artisan import Command
import re


class MakeFactoryCommand(Command):
    """Create a new model factory."""
    
    signature = 'make:factory {name} {--model=}'
    description = 'Create a new model factory class'
    help = '''Create a new model factory class.
    
Examples:
    make:factory UserFactory
    make:factory PostFactory --model=Post
    make:factory CommentFactory --model=Comment
    '''
    
    def handle(self) -> int:
        name = self.argument('name')
        model = self.option('model')
        
        if not name:
            self.error("Factory name is required")
            return 1
        
        # Ensure name ends with 'Factory'
        if not name.endswith('Factory'):
            name += 'Factory'
        
        # Derive model name from factory name if not provided
        if not model:
            model = name.replace('Factory', '')
        
        try:
            file_path = self._create_factory(name, model)
            self.success(f"Factory created: {file_path}")
            return 0
        except Exception as e:
            self.error(f"Failed to create factory: {e}")
            return 1
    
    def _create_factory(self, name: str, model: str) -> str:
        """Create factory file."""
        factories_dir = Path('app/Database/Factories')
        factories_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = factories_dir / f"{name}.py"
        
        if file_path.exists():
            if not self.confirm(f"Factory {name} already exists. Overwrite?"):
                raise ValueError("Factory creation cancelled")
        
        template = self._get_factory_template(name, model)
        
        with open(file_path, 'w') as f:
            f.write(template)
        
        return str(file_path)
    
    def _get_factory_template(self, name: str, model: str) -> str:
        """Get factory template."""
        return f'''from __future__ import annotations

from typing import Dict, Any
from app.Database.Factories.Factory import Factory, faker
from app.Models.{model} import {model}


class {name}(Factory):
    """Factory for creating {model} instances."""
    
    model = {model}
    
    def definition(self) -> Dict[str, Any]:
        """Define the model's default state."""
        return {{
            # Add your default attributes here
            # Example:
            # 'name': faker.fake.name(),
            # 'email': faker.safe_email(),
            # 'created_at': faker.random_date(),
        }}


# Register the factory
from app.Database.Factories import register_factory
register_factory('{model}', {name})
'''


class TinkerCommand(Command):
    """Interact with your application."""
    
    signature = 'tinker'
    description = 'Interact with your application'
    help = 'Open an interactive Python shell with your application loaded'
    
    def handle(self) -> int:
        self.info("Laravel FastAPI Tinker")
        self.info("Python Interactive Shell")
        self.comment("Use factory('ModelName') to access factories")
        self.comment("Use make(), create() methods to generate data")
        self.line()
        
        # Import common modules
        try:
            import code
            
            # Prepare namespace
            namespace = {
                'factory': self._get_factory_function(),
                'fake': self._get_faker(),
                'User': self._get_user_model(),
            }
            
            # Add factory examples
            self._show_examples()
            
            # Start interactive shell
            code.interact(local=namespace)
            return 0
        except KeyboardInterrupt:
            self.line("\nGoodbye!")
            return 0
        except Exception as e:
            self.error(f"Failed to start tinker: {e}")
            return 1
    
    def _get_factory_function(self) -> Callable:
        """Get factory function."""
        try:
            from app.Database.Factories import factory
            return factory
        except ImportError:
            return lambda x: None
    
    def _get_faker(self) -> Any:
        """Get faker instance."""
        try:
            from app.Database.Factories import faker
            return faker
        except ImportError:
            return None
    
    def _get_user_model(self) -> Any:
        """Get User model."""
        try:
            from app.Models.User import User
            return User
        except ImportError:
            return None
    
    def _show_examples(self) -> None:
        """Show usage examples."""
        self.comment("Examples:")
        self.line("  factory('User').make()          # Create user instance (not saved)")
        self.line("  factory('User').create()        # Create and save user")
        self.line("  factory('User').count_instances(5).make()  # Create 5 users")
        self.line("  factory('User').state(name='John').create()  # Custom attributes")
        self.line("  fake.fake.name()                # Generate fake name")
        self.line("  fake.safe_email()               # Generate fake email")
        self.line()


# Register factory commands
from app.Console.Artisan import register_command

register_command(MakeFactoryCommand)
register_command(TinkerCommand)