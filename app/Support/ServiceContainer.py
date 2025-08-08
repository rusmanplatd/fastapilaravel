from __future__ import annotations

from typing import Any, Dict, Callable, TypeVar, Type, Optional, cast, List, Union
from abc import ABC, abstractmethod
import inspect

T = TypeVar('T')


class ServiceProvider(ABC):
    """Base service provider class."""
    
    def __init__(self, container: ServiceContainer) -> None:
        self.container = container
    
    @abstractmethod
    def register(self) -> None:
        """Register services in the container."""
        pass
    
    def boot(self) -> None:
        """Boot the service provider."""
        pass


class ServiceContainer:
    """Laravel-style service container for dependency injection."""
    
    def __init__(self) -> None:
        self._bindings: Dict[str, Dict[str, Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._aliases: Dict[str, str] = {}
        self._providers: List[ServiceProvider] = []
    
    def bind(self, abstract: str, concrete: Optional[Callable[..., Any]] = None, shared: bool = False) -> None:
        """Bind a service to the container."""
        concrete_impl: Union[str, Callable[..., Any]] = concrete if concrete is not None else abstract
        
        self._bindings[abstract] = {
            'concrete': concrete_impl,
            'shared': shared
        }
    
    def singleton(self, abstract: str, concrete: Optional[Callable[..., Any]] = None) -> None:
        """Bind a singleton service to the container."""
        self.bind(abstract, concrete, shared=True)
    
    def instance(self, abstract: str, instance: Any) -> Any:
        """Register an existing instance as shared in the container."""
        self._instances[abstract] = instance
        return instance
    
    def alias(self, abstract: str, alias: str) -> None:
        """Create an alias for a service."""
        self._aliases[alias] = abstract
    
    def make(self, abstract: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Resolve a service from the container."""
        # Resolve alias
        if abstract in self._aliases:
            abstract = self._aliases[abstract]
        
        # Return existing instance if it's a singleton
        if abstract in self._instances:
            return self._instances[abstract]
        
        # Check if service is bound
        if abstract not in self._bindings:
            # Try to auto-resolve if it's a class
            try:
                return self._auto_resolve(abstract, parameters or {})
            except Exception:
                raise ValueError(f"Service '{abstract}' not bound in container")
        
        binding = self._bindings[abstract]
        concrete = binding['concrete']
        
        # Resolve the concrete implementation
        if isinstance(concrete, str):
            # If concrete is a string, resolve it recursively
            instance = self.make(concrete, parameters)
        elif callable(concrete):
            # If concrete is callable, call it with container
            if inspect.isclass(concrete):
                instance = self._resolve_class(concrete, parameters or {})
            else:
                instance = concrete(self)
        else:
            instance = concrete
        
        # Store as singleton if needed
        if binding['shared']:
            self._instances[abstract] = instance
        
        return instance
    
    def _resolve_class(self, cls: Type[T], parameters: Dict[str, Any]) -> T:
        """Resolve a class with dependency injection."""
        # Get constructor signature
        sig = inspect.signature(cls.__init__)
        args = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # Use provided parameter if available
            if param_name in parameters:
                args[param_name] = parameters[param_name]
            # Try to resolve from container
            elif param.annotation != inspect.Parameter.empty:
                try:
                    annotation_name = getattr(param.annotation, '__name__', str(param.annotation))
                    args[param_name] = self.make(annotation_name)
                except Exception:
                    if param.default != inspect.Parameter.empty:
                        args[param_name] = param.default
                    else:
                        raise ValueError(f"Cannot resolve parameter '{param_name}' for {cls.__name__}")
        
        return cls(**args)
    
    def _auto_resolve(self, abstract: str, parameters: Dict[str, Any]) -> Any:
        """Attempt to auto-resolve a service."""
        # Try to import and resolve the class
        try:
            # This is a simplified version - in a real implementation
            # you'd use proper module resolution
            module_parts = abstract.split('.')
            if len(module_parts) > 1:
                module_name = '.'.join(module_parts[:-1])
                class_name = module_parts[-1]
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                return self._resolve_class(cls, parameters)
        except Exception:
            pass
        
        raise ValueError(f"Cannot auto-resolve '{abstract}'")
    
    def bound(self, abstract: str) -> bool:
        """Check if a service is bound."""
        return abstract in self._bindings or abstract in self._instances
    
    def register_provider(self, provider: ServiceProvider) -> None:
        """Register a service provider."""
        self._providers.append(provider)
        provider.register()
    
    def boot_providers(self) -> None:
        """Boot all registered service providers."""
        for provider in self._providers:
            provider.boot()


# Global container instance
container = ServiceContainer()


def app(abstract: Optional[str] = None) -> Any:
    """Get the global application container or resolve a service."""
    if abstract is None:
        return container
    return container.make(abstract)