from __future__ import annotations

from pathlib import Path
from ..Command import Command


class MakeInterfaceCommand(Command):
    """Generate a new interface (abstract base class)."""
    
    signature = "make:interface {name : The name of the interface}"
    description = "Create a new interface (abstract base class)"
    help = "Generate a new interface using Python's Abstract Base Class (ABC)"
    
    async def handle(self) -> None:
        """Execute the command."""
        name = self.argument("name")
        
        if not name:
            self.error("Interface name is required")
            return
        
        # Ensure proper naming
        if not name.endswith("Interface"):
            name += "Interface"
        
        interface_path = Path(f"app/Contracts/{name}.py")
        interface_path.parent.mkdir(parents=True, exist_ok=True)
        
        if interface_path.exists():
            if not self.confirm(f"Interface {name} already exists. Overwrite?"):
                self.info("Interface creation cancelled.")
                return
        
        content = self._generate_interface_content(name)
        interface_path.write_text(content)
        
        self.info(f"✅ Interface created: {interface_path}")
        self.comment("Update the interface with your abstract methods")
        self.comment("Implement this interface in your concrete classes")
    
    def _generate_interface_content(self, interface_name: str) -> str:
        """Generate interface content."""
        return f'''from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class {interface_name}(ABC):
    """Interface defining the contract for implementations."""
    
    @abstractmethod
    def method_name(self, parameter: Any) -> Any:
        """Abstract method that must be implemented."""
        pass
    
    @abstractmethod
    async def async_method(self, parameter: Any) -> Any:
        """Abstract async method that must be implemented."""
        pass
    
    # Example interface methods:
    
    # @abstractmethod
    # def get_all(self) -> List[Dict[str, Any]]:
    #     """Get all items."""
    #     pass
    # 
    # @abstractmethod
    # def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
    #     """Get item by ID."""
    #     pass
    # 
    # @abstractmethod
    # def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
    #     """Create a new item."""
    #     pass
    # 
    # @abstractmethod
    # def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    #     """Update an existing item."""
    #     pass
    # 
    # @abstractmethod
    # def delete(self, id: int) -> bool:
    #     """Delete an item."""
    #     pass
    
    # Non-abstract methods (default implementations)
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate data (default implementation)."""
        # Provide a default implementation that can be overridden
        return bool(data)
    
    def transform(self, data: Any) -> Any:
        """Transform data (default implementation)."""
        # Provide a default implementation that can be overridden
        return data


# Example implementation:
#
# class Concrete{interface_name.replace("Interface", "")}({interface_name}):
#     """Concrete implementation of the interface."""
#     
#     def method_name(self, parameter: Any) -> Any:
#         """Implementation of the abstract method."""
#         # Your implementation here
#         return parameter
#     
#     async def async_method(self, parameter: Any) -> Any:
#         """Implementation of the abstract async method."""
#         # Your async implementation here
#         return parameter
#     
#     # Optionally override non-abstract methods
#     def validate(self, data: Dict[str, Any]) -> bool:
#         """Custom validation logic."""
#         # Custom implementation
#         return super().validate(data) and len(data) > 0


# Usage with dependency injection:
#
# from app.Support.ServiceContainer import ServiceContainer
#
# # Register the implementation
# container = ServiceContainer()
# container.bind("{interface_name}", Concrete{interface_name.replace("Interface", "")})
#
# # Use the interface
# service: {interface_name} = container.make("{interface_name}")
# result = service.method_name("example")


# Type hints usage:
#
# def process_data(handler: {interface_name}, data: Any) -> Any:
#     """Function that accepts any implementation of the interface."""
#     if handler.validate(data):
#         return handler.transform(handler.method_name(data))
#     return None
'''
# Register command
from app.Console.Artisan import register_command
register_command(MakeInterfaceCommand)
