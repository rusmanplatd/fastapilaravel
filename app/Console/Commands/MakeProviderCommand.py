from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakeProviderCommand(Command):
    """Generate a new service provider class."""
    
    signature = "make:provider {name : The name of the provider}"
    description = "Create a new service provider class"
    help = "Generate a new service provider class for registering and booting services"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if not name:
            self.error("Provider name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("ServiceProvider"):
            name += "ServiceProvider"
        
        provider_path = Path(f"app/Providers/{name}.py")
        provider_path.parent.mkdir(parents=True, exist_ok=True)
        
        if provider_path.exists():
            if not self.confirm(f"Provider {name} already exists. Overwrite?"):
                self.info("Provider creation cancelled.")
                return
        
        content = self._generate_provider_content(name)
        provider_path.write_text(content)
        
        self.info(f"✅ Provider created: {provider_path}")
        self.comment("Register the provider in your application's service container")
        self.comment("Update the register() and boot() methods as needed")
    
    def _generate_provider_content(self, provider_name: str) -> str:
        """Generate provider content."""
        return f'''from __future__ import annotations

from typing import Any
from app.Support.ServiceContainer import ServiceProvider


class {provider_name}(ServiceProvider):
    """Service provider for registering and booting services."""
    
    def register(self) -> None:
        """Register services in the container."""
        # Register your services here
        # Examples:
        
        # Register a singleton service
        # self.container.singleton("MyService", lambda c: self._create_my_service())
        
        # Register a regular binding
        # self.container.bind("MyInterface", self._create_implementation)
        
        # Register an existing instance
        # self.container.instance("MyInstance", MyClass())
        
        pass
    
    def boot(self) -> None:
        """Boot the service provider."""
        # Perform any bootstrapping logic here
        # This method is called after all providers have been registered
        # Examples:
        
        # Set up event listeners
        # event_dispatcher = self.container.make("EventDispatcher")
        # event_dispatcher.listen("UserRegistered", MyListener)
        
        # Register middleware
        # middleware_manager = self.container.make("MiddlewareManager")
        # middleware_manager.register("custom", MyMiddleware)
        
        # Configure facades
        # self._register_facades()
        
        pass
    
    # Example factory methods
    # def _create_my_service(self) -> Any:
    #     """Create an instance of MyService."""
    #     from app.Services.MyService import MyService
    #     from config.database import get_database
    #     db = next(get_database())
    #     return MyService(db)
    
    # def _create_implementation(self, container) -> Any:
    #     """Create an implementation of MyInterface."""
    #     from app.Services.MyImplementation import MyImplementation
    #     return MyImplementation()
    
    # def _register_facades(self) -> None:
    #     """Register facade mappings."""
    #     # Register any facades your provider needs
    #     pass
'''
# Register command
from app.Console.Artisan import register_command
register_command(MakeProviderCommand)
