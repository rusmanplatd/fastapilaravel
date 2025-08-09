from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Type, cast
from app.Support.ServiceContainer import ServiceContainer

T = TypeVar('T')


class Facade(ABC):
    """
    Base facade class similar to Laravel's Facade.
    
    Provides static-like access to services registered in the container.
    """
    
    _resolved_instances: Dict[str, Any] = {}
    
    @classmethod
    @abstractmethod
    def get_facade_accessor(cls) -> str:
        """
        Get the registered name of the component.
        
        Returns:
            The binding name in the service container
        """
        pass
    
    @classmethod
    def resolve_facade_instance(cls, name: str) -> Any:
        """
        Resolve the facade root instance from the container.
        
        Args:
            name: The service binding name
            
        Returns:
            The resolved service instance
        """
        if name in cls._resolved_instances:
            return cls._resolved_instances[name]
        
        # Get container instance
        container = ServiceContainer.get_instance()
        
        if container and container.bound(name):
            instance = container.make(name)
            cls._resolved_instances[name] = instance
            return instance
        
        raise RuntimeError(f"A facade root has not been set for '{name}'")
    
    @classmethod
    def get_facade_root(cls) -> Any:
        """
        Get the root object behind the facade.
        
        Returns:
            The service instance
        """
        return cls.resolve_facade_instance(cls.get_facade_accessor())
    
    @classmethod
    def clear_resolved_instance(cls, name: Optional[str] = None) -> None:
        """
        Clear a resolved facade instance.
        
        Args:
            name: The specific facade name to clear, or None to clear all
        """
        if name:
            cls._resolved_instances.pop(name, None)
        else:
            cls._resolved_instances.clear()
    
    @classmethod
    def clear_resolved_instances(cls) -> None:
        """Clear all resolved facade instances."""
        cls._resolved_instances.clear()
    
    def __getattr__(self, name: str) -> Any:
        """
        Dynamically handle calls to the class.
        
        Args:
            name: Method or attribute name
            
        Returns:
            The method or attribute from the facade root
        """
        instance = self.get_facade_root()
        return getattr(instance, name)
    
    @classmethod
    def __class_getitem__(cls, item: Type[T]) -> Type[T]:
        """Support for type hints like Facade[SomeClass]."""
        return cast(Type[T], cls)