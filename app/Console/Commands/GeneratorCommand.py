from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Type,
    final
)

from app.Console.Command import Command

if TYPE_CHECKING:
    pass


class GeneratorCommand(Command, ABC):
    """
    Laravel 12 Enhanced Generator Command.
    
    Base class for all code generation commands with comprehensive features
    and strict type safety.
    """
    
    def __init__(self) -> None:
        """Initialize generator command."""
        super().__init__()
        self._stubs_path: str = "stubs"
        self._replacements: Dict[str, str] = {}
    
    @abstractmethod
    def get_stub(self) -> str:
        """Get the stub file for the generator."""
        pass
    
    @abstractmethod
    def get_default_namespace(self, root_namespace: str) -> str:
        """Get the default namespace for the class."""
        pass
    
    def handle(self) -> int:
        """Execute the console command."""
        name = self.name_input()
        
        if self.already_exists(name):
            self.error(f"{self.type} [{name}] already exists!")
            return 1
        
        self.make_directory(self.get_path(name))
        
        self.files.put(self.get_path(name), self.sort_imports(self.build_class(name)))
        
        self.info(f"{self.type} [{name}] created successfully.")
        
        return 0
    
    def name_input(self) -> str:
        """Get the desired class name from the input."""
        return self.trim_string(self.argument('name'))
    
    def trim_string(self, name: str) -> str:
        """Trim the raw name."""
        return name.strip()
    
    def qualify_class(self, name: str) -> str:
        """Parse the class name and format according to the root namespace."""
        name = self.ltrim(name.replace('/', '\\'), '\\')
        
        root_namespace = self.get_root_namespace()
        
        if name.startswith(root_namespace):
            return name
        
        return self.get_default_namespace(root_namespace.rstrip('\\')) + '\\' + name
    
    def get_path(self, name: str) -> str:
        """Get the destination class path."""
        name = self.qualify_class(name).replace('\\', '/')
        
        return self.get_base_path() + '/' + name + '.py'
    
    def get_base_path(self) -> str:
        """Get the base path for generated files."""
        return "app"
    
    def get_root_namespace(self) -> str:
        """Get the root namespace for the application."""
        return "app"
    
    def make_directory(self, path: str) -> str:
        """Build the directory for the class if necessary."""
        directory = os.path.dirname(path)
        
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        return path
    
    def build_class(self, name: str) -> str:
        """Build the class with the given name."""
        stub = self.get_stub_contents()
        
        return self.replace_namespace(stub, name).replace(self.get_class_name_placeholder(), self.get_class_name(name))
    
    def get_stub_contents(self) -> str:
        """Get the contents of the stub file."""
        stub_path = self.resolve_stub_path(self.get_stub())
        
        try:
            with open(stub_path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Stub file not found: {stub_path}")
    
    def resolve_stub_path(self, stub: str) -> str:
        """Resolve the fully-qualified path to the stub."""
        return os.path.join(self._stubs_path, stub)
    
    def replace_namespace(self, stub: str, name: str) -> str:
        """Replace the namespace for the given stub."""
        searches = [
            ['DummyNamespace', self.get_namespace(name)],
            ['{{ namespace }}', self.get_namespace(name)],
            ['{{namespace}}', self.get_namespace(name)],
        ]
        
        for search, replace in searches:
            stub = stub.replace(search, replace)
        
        return stub
    
    def get_namespace(self, name: str) -> str:
        """Get the full namespace for a given class, without the class name."""
        qualified = self.qualify_class(name)
        return '.'.join(qualified.split('\\')[:-1])
    
    def get_class_name(self, name: str) -> str:
        """Get the class name for the given name."""
        return self.qualify_class(name).split('\\')[-1]
    
    def get_class_name_placeholder(self) -> str:
        """Get the class name placeholder."""
        return 'DummyClass'
    
    def already_exists(self, raw_name: str) -> bool:
        """Determine if the class already exists."""
        return os.path.exists(self.get_path(raw_name))
    
    def sort_imports(self, stub: str) -> str:
        """Alphabetically sort the imports in the stub."""
        # This would implement import sorting logic
        return stub
    
    def ltrim(self, string: str, character: str) -> str:
        """Remove leading character from string."""
        return string.lstrip(character)
    
    def add_replacement(self, search: str, replace: str) -> 'GeneratorCommand':
        """Add a replacement for stub generation."""
        self._replacements[search] = replace
        return self
    
    def get_replacements(self) -> Dict[str, str]:
        """Get the replacements for the stub."""
        return self._replacements
    
    def replace_placeholders(self, stub: str) -> str:
        """Replace all placeholders in the stub."""
        for search, replace in self.get_replacements().items():
            stub = stub.replace(search, replace)
        return stub


@final
class MakeControllerCommand(GeneratorCommand):
    """Laravel 12 make:controller command."""
    
    signature: str = "make:controller {name} {--resource} {--api} {--model=} {--parent=} {--requests}"
    description: str = "Create a new controller class"
    type: str = "Controller"
    
    def get_stub(self) -> str:
        """Get the stub file for the generator."""
        if self.option('api'):
            return 'controller.api.stub'
        elif self.option('resource'):
            return 'controller.resource.stub'
        return 'controller.plain.stub'
    
    def get_default_namespace(self, root_namespace: str) -> str:
        """Get the default namespace for the class."""
        return root_namespace + '\\Http\\Controllers'
    
    def build_class(self, name: str) -> str:
        """Build the controller class."""
        controller_namespace = self.get_namespace(name)
        
        replace = []
        
        if self.option('model'):
            replace.append(['{{ namespacedModel }}', self.get_model_namespace()])
            replace.append(['{{ model }}', self.option('model')])
            replace.append(['{{ modelVariable }}', self.camel_case(self.option('model'))])
        
        if self.option('parent'):
            replace.append(['{{ parentModel }}', self.option('parent')])
            replace.append(['{{ parentModelVariable }}', self.camel_case(self.option('parent'))])
        
        stub = self.get_stub_contents()
        
        for search, replacement in replace:
            stub = stub.replace(search, replacement)
        
        return self.replace_namespace(stub, name).replace(
            self.get_class_name_placeholder(), self.get_class_name(name)
        )
    
    def get_model_namespace(self) -> str:
        """Get the model namespace."""
        model = self.option('model')
        return f"app.Models.{model}"
    
    def camel_case(self, value: str) -> str:
        """Convert string to camelCase."""
        return value[0].lower() + value[1:] if value else ""


@final
class MakeModelCommand(GeneratorCommand):
    """Laravel 12 make:model command."""
    
    signature: str = "make:model {name} {--migration} {--factory} {--controller} {--resource} {--requests} {--policy} {--all}"
    description: str = "Create a new Eloquent model class"
    type: str = "Model"
    
    def handle(self) -> int:
        """Execute the console command."""
        result = super().handle()
        
        if self.option('all'):
            self._create_all_related_files()
        else:
            if self.option('migration'):
                self._create_migration()
            
            if self.option('factory'):
                self._create_factory()
            
            if self.option('controller'):
                self._create_controller()
            
            if self.option('policy'):
                self._create_policy()
        
        return result
    
    def get_stub(self) -> str:
        """Get the stub file for the generator."""
        return 'model.stub'
    
    def get_default_namespace(self, root_namespace: str) -> str:
        """Get the default namespace for the class."""
        return root_namespace + '\\Models'
    
    def _create_all_related_files(self) -> None:
        """Create all related files for the model."""
        self._create_migration()
        self._create_factory()
        self._create_controller()
        self._create_policy()
    
    def _create_migration(self) -> None:
        """Create migration for the model."""
        table = self.snake_case(self.plural(self.get_class_name(self.name_input())))
        self.call('make:migration', {'name': f'create_{table}_table', '--create': table})
    
    def _create_factory(self) -> None:
        """Create factory for the model."""
        self.call('make:factory', {'name': f'{self.get_class_name(self.name_input())}Factory'})
    
    def _create_controller(self) -> None:
        """Create controller for the model."""
        controller_name = f'{self.get_class_name(self.name_input())}Controller'
        options = {'--model': self.get_class_name(self.name_input())}
        
        if self.option('resource'):
            options['--resource'] = True
        
        if self.option('requests'):
            options['--requests'] = True
        
        self.call('make:controller', {'name': controller_name, **options})
    
    def _create_policy(self) -> None:
        """Create policy for the model."""
        self.call('make:policy', {
            'name': f'{self.get_class_name(self.name_input())}Policy',
            '--model': self.get_class_name(self.name_input())
        })
    
    def snake_case(self, value: str) -> str:
        """Convert string to snake_case."""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def plural(self, value: str) -> str:
        """Convert string to plural form."""
        # Simple pluralization - would use proper pluralization library in production
        if value.endswith('y'):
            return value[:-1] + 'ies'
        elif value.endswith(('s', 'sh', 'ch', 'x', 'z')):
            return value + 'es'
        else:
            return value + 's'


@final
class MakeMiddlewareCommand(GeneratorCommand):
    """Laravel 12 make:middleware command."""
    
    signature: str = "make:middleware {name}"
    description: str = "Create a new middleware class"
    type: str = "Middleware"
    
    def get_stub(self) -> str:
        """Get the stub file for the generator."""
        return 'middleware.stub'
    
    def get_default_namespace(self, root_namespace: str) -> str:
        """Get the default namespace for the class."""
        return root_namespace + '\\Http\\Middleware'


@final
class MakeRequestCommand(GeneratorCommand):
    """Laravel 12 make:request command."""
    
    signature: str = "make:request {name}"
    description: str = "Create a new form request class"
    type: str = "Request"
    
    def get_stub(self) -> str:
        """Get the stub file for the generator."""
        return 'request.stub'
    
    def get_default_namespace(self, root_namespace: str) -> str:
        """Get the default namespace for the class."""
        return root_namespace + '\\Http\\Requests'


@final
class MakeServiceCommand(GeneratorCommand):
    """Laravel 12 make:service command."""
    
    signature: str = "make:service {name} {--interface}"
    description: str = "Create a new service class"
    type: str = "Service"
    
    def handle(self) -> int:
        """Execute the console command."""
        result = super().handle()
        
        if self.option('interface'):
            self._create_interface()
        
        return result
    
    def get_stub(self) -> str:
        """Get the stub file for the generator."""
        return 'service.stub'
    
    def get_default_namespace(self, root_namespace: str) -> str:
        """Get the default namespace for the class."""
        return root_namespace + '\\Services'
    
    def _create_interface(self) -> None:
        """Create interface for the service."""
        interface_name = f'{self.get_class_name(self.name_input())}Interface'
        self.call('make:interface', {'name': interface_name})


@final
class MakeProviderCommand(GeneratorCommand):
    """Laravel 12 make:provider command."""
    
    signature: str = "make:provider {name}"
    description: str = "Create a new service provider class"
    type: str = "Provider"
    
    def get_stub(self) -> str:
        """Get the stub file for the generator."""
        return 'provider.stub'
    
    def get_default_namespace(self, root_namespace: str) -> str:
        """Get the default namespace for the class."""
        return root_namespace + '\\Providers'


@final
class MakePolicyCommand(GeneratorCommand):
    """Laravel 12 make:policy command."""
    
    signature: str = "make:policy {name} {--model=}"
    description: str = "Create a new policy class"
    type: str = "Policy"
    
    def get_stub(self) -> str:
        """Get the stub file for the generator."""
        if self.option('model'):
            return 'policy.model.stub'
        return 'policy.plain.stub'
    
    def get_default_namespace(self, root_namespace: str) -> str:
        """Get the default namespace for the class."""
        return root_namespace + '\\Policies'
    
    def build_class(self, name: str) -> str:
        """Build the policy class."""
        stub = self.get_stub_contents()
        
        if self.option('model'):
            model = self.option('model')
            stub = stub.replace('{{ model }}', model)
            stub = stub.replace('{{ modelVariable }}', self.camel_case(model))
            stub = stub.replace('{{ namespacedModel }}', f'app.Models.{model}')
        
        return self.replace_namespace(stub, name).replace(
            self.get_class_name_placeholder(), self.get_class_name(name)
        )


@final
class MakeEventCommand(GeneratorCommand):
    """Laravel 12 make:event command."""
    
    signature: str = "make:event {name}"
    description: str = "Create a new event class"
    type: str = "Event"
    
    def get_stub(self) -> str:
        """Get the stub file for the generator."""
        return 'event.stub'
    
    def get_default_namespace(self, root_namespace: str) -> str:
        """Get the default namespace for the class."""
        return root_namespace + '\\Events'


@final
class MakeListenerCommand(GeneratorCommand):
    """Laravel 12 make:listener command."""
    
    signature: str = "make:listener {name} {--event=} {--queued}"
    description: str = "Create a new event listener class"
    type: str = "Listener"
    
    def get_stub(self) -> str:
        """Get the stub file for the generator."""
        if self.option('queued'):
            return 'listener.queued.stub'
        return 'listener.stub'
    
    def get_default_namespace(self, root_namespace: str) -> str:
        """Get the default namespace for the class."""
        return root_namespace + '\\Listeners'
    
    def build_class(self, name: str) -> str:
        """Build the listener class."""
        stub = self.get_stub_contents()
        
        if self.option('event'):
            event = self.option('event')
            stub = stub.replace('{{ event }}', event)
            stub = stub.replace('{{ namespacedEvent }}', f'app.Events.{event}')
        
        return self.replace_namespace(stub, name).replace(
            self.get_class_name_placeholder(), self.get_class_name(name)
        )


@final
class MakeJobCommand(GeneratorCommand):
    """Laravel 12 make:job command."""
    
    signature: str = "make:job {name} {--sync}"
    description: str = "Create a new job class"
    type: str = "Job"
    
    def get_stub(self) -> str:
        """Get the stub file for the generator."""
        if self.option('sync'):
            return 'job.sync.stub'
        return 'job.stub'
    
    def get_default_namespace(self, root_namespace: str) -> str:
        """Get the default namespace for the class."""
        return root_namespace + '\\Jobs'


# Export Laravel 12 generator commands
__all__ = [
    'GeneratorCommand',
    'MakeControllerCommand',
    'MakeModelCommand',
    'MakeMiddlewareCommand',
    'MakeRequestCommand',
    'MakeServiceCommand',
    'MakeProviderCommand',
    'MakePolicyCommand',
    'MakeEventCommand',
    'MakeListenerCommand',
    'MakeJobCommand'
]