from __future__ import annotations

from typing import Dict, Callable, TypeVar, Type, Optional, cast, List, Union, Protocol, Awaitable, get_type_hints, get_origin, get_args, final, Literal, overload, Generator, Any
from app.Types import JsonValue, JsonObject
from contextlib import contextmanager
from abc import ABC, abstractmethod
from app.Support.Types import T, K, V, ModelT, ServiceT, validate_types, is_model, TypeConstants
import inspect
import threading
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager, asynccontextmanager
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from weakref import WeakSet, WeakValueDictionary
import gc
import functools
from types import GenericAlias

# Import from our enhanced type system
# T, K, V, ModelT, ServiceT already imported from app.Support.Types


# Laravel 12 Contextual Attributes
class ContextualAttribute:
    """Base class for contextual attributes (Laravel 12)."""
    
    def __init__(self, value: JsonValue = None):
        self.value = value
    
    def resolve(self, container: 'ServiceContainer') -> Any:
        """Resolve the contextual value."""
        return self.value


class Singleton(ContextualAttribute):
    """Mark a service as singleton (Laravel 12)."""
    pass


class Scoped(ContextualAttribute):
    """Mark a service as scoped (Laravel 12)."""
    
    def __init__(self, scope: str = "default"):
        super().__init__(scope)
        self.scope = scope


class Config(ContextualAttribute):
    """Inject configuration value (Laravel 12)."""
    
    def __init__(self, key: str, default: Any = None):
        super().__init__(key)
        self.key = key
        self.default = default
    
    def resolve(self, container: 'ServiceContainer') -> Any:
        """Resolve configuration value."""
        config = container.make('config')
        return config.get(self.key, self.default)


class Storage(ContextualAttribute):
    """Inject storage disk (Laravel 12)."""
    
    def __init__(self, disk: str = "default"):
        super().__init__(disk)
        self.disk = disk
    
    def resolve(self, container: 'ServiceContainer') -> Any:
        """Resolve storage disk."""
        storage_manager = container.make('storage')
        return storage_manager.disk(self.disk)


class Cache(ContextualAttribute):
    """Inject cache store (Laravel 12)."""
    
    def __init__(self, store: str = "default"):
        super().__init__(store)
        self.store = store
    
    def resolve(self, container: 'ServiceContainer') -> Any:
        """Resolve cache store."""
        cache_manager = container.make('cache')
        return cache_manager.store(self.store)


class Auth(ContextualAttribute):
    """Inject auth guard (Laravel 12)."""
    
    def __init__(self, guard: str = "default"):
        super().__init__(guard)
        self.guard = guard
    
    def resolve(self, container: 'ServiceContainer') -> Any:
        """Resolve auth guard."""
        auth_manager = container.make('auth')
        return auth_manager.guard(self.guard)


class CurrentUser(ContextualAttribute):
    """Inject current authenticated user (Laravel 12)."""
    
    def resolve(self, container: 'ServiceContainer') -> Any:
        """Resolve current user."""
        auth = container.make('auth')
        return auth.user()


class Tagged(ContextualAttribute):
    """Inject tagged services (Laravel 12)."""
    
    def __init__(self, tag: str):
        super().__init__(tag)
        self.tag = tag
    
    def resolve(self, container: 'ServiceContainer') -> List[Any]:
        """Resolve tagged services."""
        return container.tagged(self.tag)


class VariadicInjection:
    """Support for variadic dependency injection (Laravel 12)."""
    
    def __init__(self, type_hint: Type, services: List[str]):
        self.type_hint = type_hint
        self.services = services
    
    def resolve(self, container: 'ServiceContainer') -> List[Any]:
        """Resolve variadic dependencies."""
        return [container.make(service) for service in self.services]


class OptionalDependency:
    """Support for optional dependency injection (Laravel 12)."""
    
    def __init__(self, service: str, default: Any = None):
        self.service = service
        self.default = default
    
    def resolve(self, container: 'ServiceContainer') -> Any:
        """Resolve optional dependency."""
        try:
            return container.make(self.service)
        except Exception:
            return self.default


class ConditionalBinding:
    """Support for conditional service bindings (Laravel 12)."""
    
    def __init__(self, condition: Callable[[], bool], service: str):
        self.condition = condition
        self.service = service
    
    def should_resolve(self) -> bool:
        """Check if binding should be resolved."""
        try:
            return self.condition()
        except Exception:
            return False
    
    def resolve(self, container: 'ServiceContainer') -> Any:
        """Resolve conditional dependency."""
        if self.should_resolve():
            return container.make(self.service)
        return None


class CircularDependencyDetector:
    """Laravel 12 circular dependency detection."""
    
    def __init__(self) -> None:
        self._resolution_stack: List[str] = []
        self._lock = threading.RLock()
    
    @contextmanager
    def track_resolution(self, abstract: str) -> Generator[None, None, None]:
        """Track service resolution for circular dependency detection."""
        with self._lock:
            if abstract in self._resolution_stack:
                cycle = ' -> '.join(self._resolution_stack + [abstract])
                raise RuntimeError(f"Circular dependency detected: {cycle}")
            
            self._resolution_stack.append(abstract)
            try:
                yield
            finally:
                if self._resolution_stack and self._resolution_stack[-1] == abstract:
                    self._resolution_stack.pop()


class DependencyGraph:
    """Laravel 12 dependency graph for optimization."""
    
    def __init__(self) -> None:
        self.graph: Dict[str, List[str]] = {}
        self.resolved_order: List[str] = []
    
    def add_dependency(self, service: str, dependency: str) -> None:
        """Add a dependency relationship."""
        if service not in self.graph:
            self.graph[service] = []
        self.graph[service].append(dependency)
    
    def get_dependencies(self, service: str) -> List[str]:
        """Get dependencies for a service."""
        return self.graph.get(service, [])
    
    def topological_sort(self) -> List[str]:
        """Get services in dependency resolution order."""
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(service: str) -> None:
            if service in temp_visited:
                raise RuntimeError(f"Circular dependency detected involving {service}")
            if service in visited:
                return
            
            temp_visited.add(service)
            for dependency in self.get_dependencies(service):
                visit(dependency)
            temp_visited.remove(service)
            visited.add(service)
            result.append(service)
        
        for service in self.graph:
            if service not in visited:
                visit(service)
        
        return result


class BindingType(Enum):
    """Types of service bindings (Laravel 12 enhanced)."""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"
    INSTANCE = "instance"
    CONTEXTUAL = "contextual"
    DEFERRED = "deferred"
    ASYNC_SINGLETON = "async_singleton"
    LAZY_SINGLETON = "lazy_singleton"  # Laravel 12
    VARIADIC = "variadic"  # Laravel 12
    TAGGED = "tagged"  # Laravel 12
    CONFIG = "config"  # Laravel 12


@dataclass
class BindingMetadata:
    """Enhanced metadata for service bindings (Laravel 12)."""
    abstract: str
    concrete: Union[str, Callable[..., Any], Any]
    binding_type: BindingType
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    resolved_count: int = 0
    last_resolved: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)
    contextual: Dict[str, Any] = field(default_factory=dict)
    # Laravel 12 new fields
    is_async: bool = False
    cache_ttl: Optional[float] = None
    disposable: bool = False
    lazy_loaded: bool = False
    condition: Optional[Callable[[], bool]] = None


class ServiceScope:
    """Service scope for scoped bindings."""
    
    def __init__(self, name: str):
        self.name = name
        self.instances: Dict[str, Any] = {}
        self.created_at = time.time()
        self.active = True
    
    def get_instance(self, abstract: str) -> Optional[Any]:
        """Get instance from scope."""
        return self.instances.get(abstract)
    
    def set_instance(self, abstract: str, instance: Any) -> None:
        """Set instance in scope."""
        self.instances[abstract] = instance
    
    def dispose(self) -> None:
        """Dispose the scope and cleanup instances."""
        for instance in self.instances.values():
            if hasattr(instance, 'dispose'):
                try:
                    instance.dispose()
                except Exception:
                    pass
        
        self.instances.clear()
        self.active = False


class InjectionContext:
    """Context for dependency injection."""
    
    def __init__(self, target: str, parent: Optional['InjectionContext'] = None):
        self.target = target
        self.parent = parent
        self.depth: int = parent.depth + 1 if parent else 0
        self.injected_services: List[str] = []
    
    def add_service(self, service: str) -> None:
        """Add an injected service to context."""
        self.injected_services.append(service)
    
    def has_circular_dependency(self, service: str) -> bool:
        """Check for circular dependencies."""
        current: Optional['InjectionContext'] = self
        while current:
            if current.target == service:
                return True
            current = current.parent
        return False


class ServiceProvider(ABC):
    """Laravel 12 enhanced service provider base class."""
    
    def __init__(self, container: ServiceContainer) -> None:
        self.container = container
        self.defer: bool = False
        self.provides: List[str] = []
        self.when: List[str] = []
        self.publishes: Dict[str, str] = {}
        self.commands: List[str] = []
    
    @abstractmethod
    def register(self) -> None:
        """Register services in the container."""
        pass
    
    def boot(self) -> None:
        """Boot the service provider."""
        pass
    
    def provides_service(self, abstract: str) -> bool:
        """Check if provider provides a service."""
        return abstract in self.provides
    
    def is_deferred(self) -> bool:
        """Check if provider is deferred."""
        return self.defer
    
    def when_should_load(self, events: List[str]) -> bool:
        """Check if provider should load for events."""
        return any(event in self.when for event in events)
    
    def publish(self, from_path: str, to_path: str) -> None:
        """Add publishable assets."""
        self.publishes[from_path] = to_path
    
    def commands(self, commands: List[str]) -> None:
        """Register Artisan commands."""
        self.commands.extend(commands)


class ServiceContainer:
    """Laravel 12 enhanced service container with advanced features."""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._bindings: Dict[str, Dict[str, Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._aliases: Dict[str, str] = {}
        self._providers: List[ServiceProvider] = []
        self._deferred_providers: Dict[str, ServiceProvider] = {}
        self._loaded_providers: Dict[str, ServiceProvider] = {}
        self._contextual_bindings: Dict[str, Dict[str, Any]] = {}
        self._method_bindings: Dict[str, Callable[..., Any]] = {}
        self._tags: Dict[str, List[str]] = {}
        self._resolved_callbacks: Dict[str, List[Callable[[Any, ServiceContainer], None]]] = {}
        self._global_resolving_callbacks: List[Callable[[str, Any, ServiceContainer], None]] = []
        self._global_resolved_callbacks: List[Callable[[str, Any, ServiceContainer], None]] = []
        self._lock = threading.RLock()
        self._build_stack: List[str] = []
        self._rebound_callbacks: Dict[str, List[Callable[[], None]]] = {}
        self._refresh_instances: List[str] = []
        
        # Laravel 12 Provider Management
        self._booted: bool = False
        self._booting_callbacks: List[Callable[[], None]] = []
        self._booted_callbacks: List[Callable[[], None]] = []
        
        # Enhanced features
        self._metadata: Dict[str, BindingMetadata] = {}
        self._scopes: Dict[str, ServiceScope] = {}
        self._current_scope: Optional[str] = None
        self._before_resolving_callbacks: Dict[str, List[Callable[..., Any]]] = {}
        self._after_resolving_callbacks: Dict[str, List[Callable[..., Any]]] = {}
        self._when_callbacks: Dict[str, Dict[str, Any]] = {}
        self._extend_callbacks: Dict[str, List[Callable[..., Any]]] = {}
        self._contextual_concrete: Dict[str, Dict[str, Any]] = {}
        self._factory_bindings: Dict[str, Callable[..., Any]] = {}
        self._performance_stats: Dict[str, Dict[str, Any]] = {}
        self._injection_context: Optional[InjectionContext] = None
        
        # Laravel 12 new features
        self._async_instances: Dict[str, Any] = {}
        self._weak_instances: WeakValueDictionary = WeakValueDictionary()
        self._conditional_bindings: Dict[str, List[Callable[[], bool]]] = {}
        self._cached_instances: Dict[str, tuple[Any, float]] = {}  # (instance, expiry)
        self._thread_local_instances: threading.local = threading.local()
        self._disposable_instances: WeakSet = WeakSet()
        self._lazy_bindings: Dict[str, Callable[[], Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="container")
        self._async_lock = asyncio.Lock()
        
        # Laravel 12 enhanced features
        self._contextual_attributes: Dict[str, List[ContextualAttribute]] = {}
        self._variadic_bindings: Dict[str, VariadicInjection] = {}
        self._lazy_singletons: Dict[str, Callable[[], Any]] = {}
        self._config_bindings: Dict[str, Any] = {}
        self._attribute_resolvers: Dict[Type, Callable[[Any, 'ServiceContainer'], Any]] = {}
        self._zero_config_cache: Dict[str, Type] = {}
        self._automatic_bindings: Dict[str, bool] = {}
        self._provider_loaded_callbacks: List[Callable[[], None]] = []
        
        # Create default scope
        self.create_scope("default")
        self._current_scope = "default"
        
        # Register core Laravel 12 services
        self._register_core_services()
    
    def bind(self, abstract: str, concrete: Optional[Callable[..., Any]] = None, shared: bool = False) -> None:
        """Bind a service to the container with metadata tracking (Laravel 12 enhanced)."""
        concrete_impl: Union[str, Callable[..., Any]] = concrete if concrete is not None else abstract
        
        self._bindings[abstract] = {
            'concrete': concrete_impl,
            'shared': shared
        }
        
        binding_type = BindingType.SINGLETON if shared else BindingType.TRANSIENT
        
        self._metadata[abstract] = BindingMetadata(
            abstract=abstract,
            concrete=concrete_impl,
            binding_type=binding_type,
            is_async=inspect.iscoroutinefunction(concrete_impl) if callable(concrete_impl) else False
        )
        
        self.logger.debug(f"Bound service: {abstract} as {binding_type.value}")
        
        # Check if it's async and store appropriately
        if self._metadata[abstract].is_async and shared:
            self._metadata[abstract].binding_type = BindingType.ASYNC_SINGLETON
    
    def bindIf(self, condition: Callable[[], bool], abstract: str, concrete: Optional[Callable[..., Any]] = None, shared: bool = False) -> None:
        """Conditionally bind a service (Laravel 12)."""
        if abstract not in self._conditional_bindings:
            self._conditional_bindings[abstract] = []
        
        self._conditional_bindings[abstract].append(condition)
        
        # Only bind if condition is true
        if condition():
            self.bind(abstract, concrete, shared)
    
    def bindMethod(self, method: str, callback: Callable[..., Any]) -> None:
        """Bind a callback to resolve a method call (Laravel 12)."""
        self._method_bindings[method] = callback
        self.logger.debug(f"Bound method: {method}")
    
    def cached(self, abstract: str, concrete: Optional[Callable[..., Any]] = None, ttl: float = 3600) -> None:
        """Bind a service with TTL caching (Laravel 12)."""
        self.bind(abstract, concrete, shared=False)
        
        if abstract in self._metadata:
            self._metadata[abstract].cache_ttl = ttl
    
    def weak(self, abstract: str, concrete: Optional[Callable[..., Any]] = None) -> None:
        """Bind a service with weak references (Laravel 12)."""
        self.bind(abstract, concrete, shared=False)
        
        # Mark for weak reference storage
        if abstract in self._metadata:
            self._metadata[abstract].disposable = True
    
    def singleton(self, abstract: str, concrete: Optional[Callable[..., Any]] = None) -> None:
        """Bind a singleton service to the container."""
        self.bind(abstract, concrete, shared=True)
        
        if abstract in self._metadata:
            self._metadata[abstract].binding_type = BindingType.SINGLETON
    
    def instance(self, abstract: str, instance: Any) -> Any:
        """Register an existing instance as shared in the container."""
        self._instances[abstract] = instance
        return instance
    
    def alias(self, abstract: str, alias: str) -> None:
        """Create an alias for a service."""
        self._aliases[alias] = abstract
    
    def make(self, abstract: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Resolve a service from the container with enhanced Laravel 12 features."""
        start_time = time.time()
        
        try:
            # Check conditional bindings
            if abstract in self._conditional_bindings:
                for condition in self._conditional_bindings[abstract]:
                    if not condition():
                        raise ValueError(f"Conditional binding for '{abstract}' failed")
            
            # Check cached instances with TTL
            if abstract in self._cached_instances:
                cached_instance, expiry = self._cached_instances[abstract]
                if time.time() < expiry:
                    return cached_instance
                else:
                    del self._cached_instances[abstract]
            
            # Check for circular dependencies
            if self._injection_context and self._injection_context.has_circular_dependency(abstract):
                raise ValueError(f"Circular dependency detected for service: {abstract}")
            
            # Create injection context
            old_context = self._injection_context
            self._injection_context = InjectionContext(abstract, old_context)
            
            try:
                # Call before resolving callbacks
                self._call_before_resolving_callbacks(abstract)
                
                # Check if it's an async service
                if abstract in self._metadata and self._metadata[abstract].is_async:
                    # Handle async resolution differently
                    if abstract in self._async_instances:
                        return self._async_instances[abstract]
                
                # Resolve the service
                instance = self._resolve_service(abstract, parameters or {})
                
                # Apply extensions
                if abstract in self._extend_callbacks:
                    for callback in self._extend_callbacks[abstract]:
                        instance = callback(instance, self)
                
                # Handle caching with TTL
                if abstract in self._metadata and self._metadata[abstract].cache_ttl:
                    ttl = self._metadata[abstract].cache_ttl
                    if ttl is not None:
                        expiry = time.time() + ttl
                        self._cached_instances[abstract] = (instance, expiry)
                
                # Handle weak references
                if abstract in self._metadata and self._metadata[abstract].disposable:
                    self._weak_instances[abstract] = instance
                    self._disposable_instances.add(instance)
                
                # Call after resolving callbacks
                self._call_after_resolving_callbacks(abstract, instance)
                
                # Update metadata
                if abstract in self._metadata:
                    metadata = self._metadata[abstract]
                    metadata.resolved_count += 1
                    metadata.last_resolved = time.time()
                
                # Track performance
                duration = time.time() - start_time
                self._track_performance(abstract, duration)
                
                return instance
                
            finally:
                self._injection_context = old_context
                
        except Exception as e:
            self.logger.error(f"Error resolving service {abstract}: {e}")
            raise
    
    async def makeAsync(self, abstract: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Asynchronously resolve a service (Laravel 12)."""
        async with self._async_lock:
            # Check if we have an async instance
            if abstract in self._async_instances:
                return self._async_instances[abstract]
            
            # Resolve in thread pool if it's a synchronous service
            if abstract not in self._metadata or not self._metadata[abstract].is_async:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(self._executor, self.make, abstract, parameters)
            
            # Handle true async services
            try:
                instance = await self._resolve_async_service(abstract, parameters or {})
                
                # Store as async singleton if needed
                if abstract in self._metadata and self._metadata[abstract].binding_type == BindingType.ASYNC_SINGLETON:
                    self._async_instances[abstract] = instance
                
                return instance
            except Exception as e:
                self.logger.error(f"Error async resolving service {abstract}: {e}")
                raise
    
    async def _resolve_async_service(self, abstract: str, parameters: Dict[str, Any]) -> Any:
        """Resolve an async service."""
        if abstract not in self._bindings:
            raise ValueError(f"Async service '{abstract}' not bound")
        
        binding = self._bindings[abstract]
        concrete = binding['concrete']
        
        if inspect.iscoroutinefunction(concrete):
            return await concrete(self)
        elif inspect.isclass(concrete):
            # Async class instantiation
            instance = self._resolve_class(concrete, parameters)
            if hasattr(instance, '__ainit__'):
                await instance.__ainit__()
            return instance
        else:
            return concrete
    
    def lazy(self, abstract: str, factory: Callable[[], Any]) -> None:
        """Bind a lazy-loaded service (Laravel 12)."""
        self._lazy_bindings[abstract] = factory
        
        self._metadata[abstract] = BindingMetadata(
            abstract=abstract,
            concrete=factory,
            binding_type=BindingType.DEFERRED,
            lazy_loaded=True
        )
        
        self.logger.debug(f"Bound lazy service: {abstract}")
    
    def lazySingleton(self, abstract: str, factory: Callable[[], Any]) -> None:
        """Bind a lazy singleton service (Laravel 12)."""
        self._lazy_singletons[abstract] = factory
        
        self._metadata[abstract] = BindingMetadata(
            abstract=abstract,
            concrete=factory,
            binding_type=BindingType.LAZY_SINGLETON,
            lazy_loaded=True
        )
        
        self.logger.debug(f"Bound lazy singleton: {abstract}")
    
    def giveConfig(self, abstract: str, key: str, default: Any = None) -> None:
        """Bind a configuration value (Laravel 12)."""
        self._config_bindings[abstract] = {'key': key, 'default': default}
        
        self._metadata[abstract] = BindingMetadata(
            abstract=abstract,
            concrete=key,
            binding_type=BindingType.CONFIG
        )
        
        self.logger.debug(f"Bound config: {abstract} -> {key}")
    
    def giveTagged(self, abstract: str, tag: str) -> None:
        """Bind tagged services to an abstract (Laravel 12)."""
        if abstract not in self._variadic_bindings:
            self._variadic_bindings[abstract] = VariadicInjection(List[Any], [])
        
        # Store tag reference
        self._variadic_bindings[abstract].services = [tag]  # Store tag instead of services
        
        self._metadata[abstract] = BindingMetadata(
            abstract=abstract,
            concrete=tag,
            binding_type=BindingType.TAGGED,
            tags=[tag]
        )
        
        self.logger.debug(f"Bound tagged services: {abstract} -> tag:{tag}")
    
    def contextualAttribute(self, target: str, attribute: ContextualAttribute) -> None:
        """Register a contextual attribute for a target (Laravel 12)."""
        if target not in self._contextual_attributes:
            self._contextual_attributes[target] = []
        
        self._contextual_attributes[target].append(attribute)
        self.logger.debug(f"Registered contextual attribute for {target}: {type(attribute).__name__}")
    
    def registerAttributeResolver(self, attribute_type: Type, resolver: Callable[[Any, 'ServiceContainer'], Any]) -> None:
        """Register a custom attribute resolver (Laravel 12)."""
        self._attribute_resolvers[attribute_type] = resolver
        self.logger.debug(f"Registered attribute resolver for {attribute_type.__name__}")
    
    def autoResolve(self, abstract: str, enable: bool = True) -> None:
        """Enable/disable automatic resolution for a service (Laravel 12)."""
        self._automatic_bindings[abstract] = enable
        self.logger.debug(f"Auto-resolve for {abstract}: {'enabled' if enable else 'disabled'}")
    
    def zeroConfig(self, enable: bool = True) -> None:
        """Enable/disable zero-configuration resolution (Laravel 12)."""
        self._zero_config_enabled = enable
        self.logger.debug(f"Zero-config resolution: {'enabled' if enable else 'disabled'}")
    
    def whenProviderLoaded(self, callback: Callable[[], None]) -> None:
        """Register callback for when providers are loaded (Laravel 12)."""
        self._provider_loaded_callbacks.append(callback)
    
    def rebinding(self, abstract: str, callback: Callable[[Any, 'ServiceContainer'], None]) -> None:
        """Enhanced rebinding with callback support (Laravel 12)."""
        if abstract not in self._rebound_callbacks:
            self._rebound_callbacks[abstract] = []
        
        def wrapper() -> None:
            if abstract in self._instances:
                instance = self._instances[abstract]
                callback(instance, self)
        
        self._rebound_callbacks[abstract].append(wrapper)
        self.logger.debug(f"Registered rebinding callback for {abstract}")
    
    def call(self, method: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Call a bound method (Laravel 12)."""
        if method not in self._method_bindings:
            raise ValueError(f"Method '{method}' not bound")
        
        callback = self._method_bindings[method]
        return callback(self, parameters or {})
    
    def dispose(self) -> None:
        """Dispose container and cleanup resources (Laravel 12)."""
        # Dispose all disposable instances
        for instance in list(self._disposable_instances):
            if hasattr(instance, 'dispose'):
                try:
                    instance.dispose()
                except Exception as e:
                    self.logger.warning(f"Error disposing instance: {e}")
        
        # Clear caches
        self._cached_instances.clear()
        self._weak_instances.clear()
        self._async_instances.clear()
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        # Force garbage collection
        gc.collect()
        
        self.logger.info("Container disposed")
    
    def _resolve_class(self, cls: Type[T], parameters: Dict[str, Any]) -> T:
        """Resolve a class with enhanced Laravel 12 dependency injection."""
        # Get constructor signature
        sig = inspect.signature(cls.__init__)
        type_hints = get_type_hints(cls.__init__)
        args = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            # Use provided parameter if available
            if param_name in parameters:
                args[param_name] = parameters[param_name]
                continue
            
            # Check for contextual attributes
            resolved_value = self._resolve_contextual_attributes(cls.__name__, param_name, param)
            if resolved_value is not None:
                args[param_name] = resolved_value
                continue
            
            # Handle variadic parameters (Laravel 12)
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                variadic_value = self._resolve_variadic_parameter(cls.__name__, param, type_hints)
                if variadic_value is not None:
                    args[param_name] = variadic_value
                    continue
            
            # Try to resolve from container with zero-config support
            if param.annotation != inspect.Parameter.empty:
                try:
                    # Enhanced type resolution
                    resolved_value = self._resolve_parameter_type(param.annotation, param_name, cls)
                    if resolved_value is not None:
                        args[param_name] = resolved_value
                        continue
                except Exception as e:
                    self.logger.debug(f"Failed to resolve {param_name}: {e}")
            
            # Use default value if available
            if param.default != inspect.Parameter.empty:
                args[param_name] = param.default
            else:
                # Laravel 12: Try zero-config resolution
                if hasattr(self, '_zero_config_enabled') and self._zero_config_enabled:
                    zero_config_value = self._try_zero_config_resolution(param.annotation, param_name)
                    if zero_config_value is not None:
                        args[param_name] = zero_config_value
                    else:
                        raise ValueError(f"Cannot resolve parameter '{param_name}' for {cls.__name__}")
                else:
                    raise ValueError(f"Cannot resolve parameter '{param_name}' for {cls.__name__}")
        
        return cls(**args)
    
    def _resolve_contextual_attributes(self, class_name: str, param_name: str, param: inspect.Parameter) -> Any:
        """Resolve contextual attributes for a parameter (Laravel 12)."""
        # Check if class has contextual attributes
        if class_name in self._contextual_attributes:
            for attribute in self._contextual_attributes[class_name]:
                if isinstance(attribute, ContextualAttribute):
                    return attribute.resolve(self)
        
        # Check parameter annotations for contextual attributes
        if hasattr(param, 'annotation') and hasattr(param.annotation, '__metadata__'):
            for metadata in param.annotation.__metadata__:
                if isinstance(metadata, ContextualAttribute):
                    return metadata.resolve(self)
        
        return None
    
    def _resolve_variadic_parameter(self, class_name: str, param: inspect.Parameter, type_hints: Dict[str, Any]) -> Any:
        """Resolve variadic parameters (Laravel 12)."""
        if class_name in self._variadic_bindings:
            variadic_binding = self._variadic_bindings[class_name]
            return variadic_binding.resolve(self)
        
        return None
    
    def _resolve_parameter_type(self, annotation: Any, param_name: str, cls: Type) -> Any:
        """Enhanced parameter type resolution (Laravel 12)."""
        # Handle List types for tagged injection
        origin = get_origin(annotation)
        if origin is list or origin is List:
            args = get_args(annotation)
            if args:
                # This might be a tagged injection
                type_name = getattr(args[0], '__name__', str(args[0]))
                if type_name in self._tags:
                    return self.tagged(type_name)
        
        # Handle Union types
        elif origin is Union:
            args = get_args(annotation)
            for arg in args:
                if arg is type(None):  # Skip Optional None
                    continue
                try:
                    type_name = getattr(arg, '__name__', str(arg))
                    return self.make(type_name)
                except Exception:
                    continue
        
        # Regular type resolution
        else:
            annotation_name = getattr(annotation, '__name__', str(annotation))
            
            # Check for automatic bindings
            if annotation_name in self._automatic_bindings and self._automatic_bindings[annotation_name]:
                return self.make(annotation_name)
            
            # Try to resolve normally
            try:
                return self.make(annotation_name)
            except Exception:
                # Try with fully qualified name
                if hasattr(annotation, '__module__') and hasattr(annotation, '__name__'):
                    fqn = f"{annotation.__module__}.{annotation.__name__}"
                    try:
                        return self.make(fqn)
                    except Exception:
                        pass
        
        return None
    
    def _try_zero_config_resolution(self, annotation: Any, param_name: str) -> Any:
        """Try zero-configuration resolution (Laravel 12)."""
        if not annotation or annotation == inspect.Parameter.empty:
            return None
        
        # Cache successful resolutions
        annotation_key = str(annotation)
        if annotation_key in self._zero_config_cache:
            cached_type = self._zero_config_cache[annotation_key]
            try:
                return self.make(cached_type.__name__)
            except Exception:
                pass
        
        # Try to auto-resolve the type
        try:
            if inspect.isclass(annotation):
                # Try to instantiate the class directly
                instance = self._resolve_class(annotation, {})
                self._zero_config_cache[annotation_key] = annotation
                return instance
        except Exception:
            pass
        
        return None
    
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
        """Register a service provider with Laravel 12 enhancements."""
        # Check if provider is deferred
        if provider.is_deferred():
            # Register as deferred provider
            for service in provider.provides:
                self._deferred_providers[service] = provider
            self.logger.debug(f"Registered deferred provider: {provider.__class__.__name__}")
        else:
            # Register immediately
            self._providers.append(provider)
            provider.register()
            
            # Store loaded provider
            self._loaded_providers[provider.__class__.__name__] = provider
            self.logger.debug(f"Registered provider: {provider.__class__.__name__}")
    
    def load_deferred_provider(self, service: str) -> None:
        """Load a deferred provider when service is requested."""
        if service in self._deferred_providers:
            provider = self._deferred_providers[service]
            
            # Remove from deferred and add to loaded
            del self._deferred_providers[service]
            self._providers.append(provider)
            self._loaded_providers[provider.__class__.__name__] = provider
            
            # Register the provider
            provider.register()
            
            # Boot if container is already booted
            if self._booted:
                provider.boot()
            
            self.logger.debug(f"Loaded deferred provider: {provider.__class__.__name__}")
    
    def boot_providers(self) -> None:
        """Boot all registered service providers with Laravel 12 lifecycle."""
        if self._booted:
            return
        
        # Call booting callbacks
        for callback in self._booting_callbacks:
            callback()
        
        # Boot providers
        for provider in self._providers:
            provider.boot()
        
        self._booted = True
        
        # Call booted callbacks
        for callback in self._booted_callbacks:
            callback()
        
        # Execute provider loaded callbacks
        for callback in self._provider_loaded_callbacks:
            callback()
        
        self.logger.info("All providers booted")
    
    def booting(self, callback: Callable[[], None]) -> None:
        """Register a callback to run before booting."""
        self._booting_callbacks.append(callback)
    
    def booted(self, callback: Callable[[], None]) -> None:
        """Register a callback to run after booting."""
        if self._booted:
            callback()
        else:
            self._booted_callbacks.append(callback)
    
    def is_booted(self) -> bool:
        """Check if container is booted."""
        return self._booted
    
    def scoped(self, abstract: str, concrete: Optional[Callable[..., Any]] = None) -> None:
        """Bind a service as scoped (one instance per scope)."""
        concrete_impl = concrete if concrete is not None else abstract
        
        self._bindings[abstract] = {
            'concrete': concrete_impl,
            'shared': False,
            'scoped': True
        }
        
        self._metadata[abstract] = BindingMetadata(
            abstract=abstract,
            concrete=concrete_impl,
            binding_type=BindingType.SCOPED
        )
        
        self.logger.debug(f"Bound scoped service: {abstract}")
    
    def factory(self, abstract: str, factory: Callable[..., Any]) -> None:
        """Bind a factory function."""
        self._factory_bindings[abstract] = factory
        
        self._metadata[abstract] = BindingMetadata(
            abstract=abstract,
            concrete=factory,
            binding_type=BindingType.TRANSIENT
        )
        
        self.logger.debug(f"Bound factory: {abstract}")
    
    def when(self, concrete: str) -> 'WhenContext':
        """Set up contextual binding."""
        return WhenContext(self, concrete)
    
    def tag(self, abstracts: Union[str, List[str]], tags: Union[str, List[str]]) -> None:
        """Tag services for group resolution."""
        if isinstance(abstracts, str):
            abstracts = [abstracts]
        if isinstance(tags, str):
            tags = [tags]
        
        for abstract in abstracts:
            if abstract not in self._metadata:
                # Create empty metadata for tagging
                self._metadata[abstract] = BindingMetadata(
                    abstract=abstract,
                    concrete=abstract,
                    binding_type=BindingType.TRANSIENT
                )
            
            self._metadata[abstract].tags.extend(tags)
            
            # Update reverse lookup
            for tag in tags:
                if tag not in self._tags:
                    self._tags[tag] = []
                if abstract not in self._tags[tag]:
                    self._tags[tag].append(abstract)
    
    def tagged(self, tag: str) -> List[Any]:
        """Resolve all services with a specific tag."""
        if tag not in self._tags:
            return []
        
        return [self.make(abstract) for abstract in self._tags[tag]]
    
    def extend(self, abstract: str, closure: Callable[[Any, 'ServiceContainer'], Any]) -> None:
        """Extend a service binding."""
        if abstract not in self._extend_callbacks:
            self._extend_callbacks[abstract] = []
        
        self._extend_callbacks[abstract].append(closure)
    
    def create_scope(self, name: str) -> ServiceScope:
        """Create a new service scope."""
        scope = ServiceScope(name)
        self._scopes[name] = scope
        self.logger.debug(f"Created scope: {name}")
        return scope
    
    @contextmanager
    def scope(self, name: str) -> Any:
        """Context manager for service scopes."""
        if name not in self._scopes:
            self.create_scope(name)
        
        old_scope = self._current_scope
        self._current_scope = name
        
        try:
            yield self._scopes[name]
        finally:
            self._current_scope = old_scope
    
    def _resolve_service(self, abstract: str, parameters: Dict[str, Any]) -> Any:
        """Internal service resolution logic (Laravel 12 enhanced)."""
        # Resolve alias
        if abstract in self._aliases:
            abstract = self._aliases[abstract]
        
        # Laravel 12: Check for config bindings
        if abstract in self._config_bindings:
            config_binding = self._config_bindings[abstract]
            config = self.make('config')
            return config.get(config_binding['key'], config_binding['default'])
        
        # Laravel 12: Check for lazy singletons
        if abstract in self._lazy_singletons:
            if abstract not in self._instances:
                factory = self._lazy_singletons[abstract]
                instance = factory()
                self._instances[abstract] = instance
            return self._instances[abstract]
        
        # Laravel 12: Check for tagged bindings
        if abstract in self._variadic_bindings:
            variadic_binding = self._variadic_bindings[abstract]
            # If services contains a tag reference
            if len(variadic_binding.services) == 1 and variadic_binding.services[0] in self._tags:
                tag = variadic_binding.services[0]
                return self.tagged(tag)
            else:
                return variadic_binding.resolve(self)
        
        # Check for lazy bindings
        if abstract in self._lazy_bindings:
            factory = self._lazy_bindings[abstract]
            instance = factory()
            # Remove from lazy bindings after first resolution
            del self._lazy_bindings[abstract]
            return instance
        
        # Check for factory binding
        if abstract in self._factory_bindings:
            return self._factory_bindings[abstract](self)
        
        # Check weak instances first
        if abstract in self._weak_instances:
            weak_instance = self._weak_instances[abstract]
            if weak_instance is not None:
                return weak_instance
        
        # Check scoped instances
        if abstract in self._bindings and self._bindings[abstract].get('scoped', False):
            current_scope = self._scopes.get(self._current_scope) if self._current_scope else None
            if current_scope:
                scoped_instance = current_scope.get_instance(abstract)
                if scoped_instance is not None:
                    return scoped_instance
        
        # Return existing instance if it's a singleton
        if abstract in self._instances:
            return self._instances[abstract]
        
        # Check if service is bound
        if abstract not in self._bindings:
            # Laravel 12: Check for deferred providers first
            if abstract in self._deferred_providers:
                self.load_deferred_provider(abstract)
                # Now resolve the service
                return self._resolve_service(abstract, parameters)
            
            # Laravel 12: Try automatic bindings
            if abstract in self._automatic_bindings and self._automatic_bindings[abstract]:
                try:
                    return self._auto_resolve(abstract, parameters or {})
                except Exception:
                    pass
            
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
        
        # Store in current scope if scoped
        if abstract in self._bindings and self._bindings[abstract].get('scoped', False):
            current_scope = self._scopes.get(self._current_scope) if self._current_scope else None
            if current_scope:
                current_scope.set_instance(abstract, instance)
        
        return instance
    
    def _call_before_resolving_callbacks(self, abstract: str) -> None:
        """Call before resolving callbacks."""
        if abstract in self._before_resolving_callbacks:
            for callback in self._before_resolving_callbacks[abstract]:
                callback(abstract, self)
    
    def _call_after_resolving_callbacks(self, abstract: str, instance: Any) -> None:
        """Call after resolving callbacks."""
        if abstract in self._after_resolving_callbacks:
            for callback in self._after_resolving_callbacks[abstract]:
                callback(abstract, instance, self)
    
    def _track_performance(self, abstract: str, duration: float) -> None:
        """Track performance statistics."""
        if abstract not in self._performance_stats:
            self._performance_stats[abstract] = {
                'total_calls': 0,
                'total_time': 0.0,
                'avg_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0
            }
        
        stats = self._performance_stats[abstract]
        stats['total_calls'] += 1
        stats['total_time'] += duration
        stats['avg_time'] = stats['total_time'] / stats['total_calls']
        stats['min_time'] = min(stats['min_time'], duration)
        stats['max_time'] = max(stats['max_time'], duration)
    
    def before_resolving(self, abstract: str, callback: Callable[..., Any]) -> None:
        """Register callback to run before resolving a service."""
        if abstract not in self._before_resolving_callbacks:
            self._before_resolving_callbacks[abstract] = []
        
        self._before_resolving_callbacks[abstract].append(callback)
    
    def after_resolving(self, abstract: str, callback: Callable[..., Any]) -> None:
        """Register callback to run after resolving a service."""
        if abstract not in self._after_resolving_callbacks:
            self._after_resolving_callbacks[abstract] = []
        
        self._after_resolving_callbacks[abstract].append(callback)
    
    def flush(self) -> None:
        """Flush all bindings and instances."""
        self._bindings.clear()
        self._instances.clear()
        self._metadata.clear()
        
        # Clear all scopes
        for scope in self._scopes.values():
            scope.dispose()
        self._scopes.clear()
        
        # Recreate default scope
        self.create_scope("default")
        self._current_scope = "default"
        
        self.logger.info("Container flushed")
    
    def forget(self, abstract: str) -> None:
        """Remove a binding from the container."""
        if abstract in self._bindings:
            del self._bindings[abstract]
        
        if abstract in self._instances:
            del self._instances[abstract]
        
        if abstract in self._metadata:
            del self._metadata[abstract]
        
        # Remove from scopes
        for scope in self._scopes.values():
            if abstract in scope.instances:
                del scope.instances[abstract]
        
        self.logger.debug(f"Forgot service: {abstract}")
    
    def refresh(self, abstract: str) -> None:
        """Refresh a singleton service."""
        if abstract in self._instances:
            del self._instances[abstract]
        
        # Remove from all scopes
        for scope in self._scopes.values():
            if abstract in scope.instances:
                del scope.instances[abstract]
        
        self.logger.debug(f"Refreshed service: {abstract}")
    
    def get_bindings(self) -> Dict[str, BindingMetadata]:
        """Get all binding metadata."""
        return self._metadata.copy()
    
    def get_performance_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get performance statistics."""
        return self._performance_stats.copy()
    
    def get_container_stats(self) -> Dict[str, Any]:
        """Get comprehensive container statistics (Laravel 12 enhanced)."""
        return {
            'total_bindings': len(self._bindings),
            'total_instances': len(self._instances),
            'total_scopes': len(self._scopes),
            'current_scope': self._current_scope,
            'total_tags': len(self._tags),
            'total_providers': len(self._providers),
            'binding_types': self._get_binding_type_counts(),
            'most_resolved': self._get_most_resolved_services(5),
            'slowest_services': self._get_slowest_services(5),
            'memory_usage': self._estimate_memory_usage(),
            # Laravel 12 new stats
            'async_instances': len(self._async_instances),
            'cached_instances': len(self._cached_instances),
            'weak_instances': len(self._weak_instances),
            'lazy_bindings': len(self._lazy_bindings),
            'method_bindings': len(self._method_bindings),
            'conditional_bindings': len(self._conditional_bindings),
            'disposable_instances': len(self._disposable_instances),
            'expired_cache_count': self._count_expired_cache()
        }
    
    def _count_expired_cache(self) -> int:
        """Count expired cache entries."""
        current_time = time.time()
        expired_count = 0
        
        for abstract, (instance, expiry) in list(self._cached_instances.items()):
            if current_time >= expiry:
                expired_count += 1
                del self._cached_instances[abstract]
        
        return expired_count
    
    def health_check(self) -> Dict[str, Any]:
        """Perform container health check (Laravel 12)."""
        healthy = True
        issues = []
        
        # Check for memory leaks
        if len(self._instances) > 1000:
            healthy = False
            issues.append("High instance count - possible memory leak")
        
        # Check for performance issues
        slow_services = self._get_slowest_services(3)
        for service in slow_services:
            if service['avg_time'] > 1.0:  # 1 second threshold
                healthy = False
                issues.append(f"Slow service: {service['service']} ({service['avg_time']:.2f}s avg)")
        
        # Check circular dependencies in metadata
        for abstract, metadata in self._metadata.items():
            if len(metadata.dependencies) > 10:
                issues.append(f"Service {abstract} has many dependencies ({len(metadata.dependencies)})")
        
        return {
            'healthy': healthy,
            'timestamp': time.time(),
            'issues': issues,
            'stats': self.get_container_stats()
        }
    
    def _get_binding_type_counts(self) -> Dict[str, int]:
        """Get counts of each binding type."""
        counts = {bt.value: 0 for bt in BindingType}
        
        for metadata in self._metadata.values():
            counts[metadata.binding_type.value] += 1
        
        return counts
    
    def _get_most_resolved_services(self, limit: int) -> List[Dict[str, Any]]:
        """Get most frequently resolved services."""
        sorted_services = sorted(
            self._metadata.items(),
            key=lambda x: x[1].resolved_count,
            reverse=True
        )
        
        return [
            {
                'service': service,
                'resolved_count': metadata.resolved_count,
                'last_resolved': metadata.last_resolved
            }
            for service, metadata in sorted_services[:limit]
        ]
    
    def _get_slowest_services(self, limit: int) -> List[Dict[str, Any]]:
        """Get slowest services by average resolution time."""
        sorted_services = sorted(
            [(service, stats) for service, stats in self._performance_stats.items()],
            key=lambda x: x[1]['avg_time'],
            reverse=True
        )
        
        return [
            {
                'service': service,
                'avg_time': stats['avg_time'],
                'total_calls': stats['total_calls']
            }
            for service, stats in sorted_services[:limit]
        ]
    
    def _estimate_memory_usage(self) -> Dict[str, int]:
        """Estimate memory usage of container components."""
        return {
            'bindings': len(self._bindings),
            'instances': len(self._instances),
            'metadata': len(self._metadata),
            'scopes': sum(len(scope.instances) for scope in self._scopes.values())
        }
    
    def _register_core_services(self) -> None:
        """Register core Laravel 12 services."""
        # Register container itself
        self.instance('container', self)
        self.alias('container', 'app')
        
        # Register core facades
        self.singleton('facade.manager', lambda c: self._create_facade_manager())
        
        # Register event dispatcher
        self.singleton('events', lambda c: self._create_event_dispatcher())
        
        # Register config repository
        self.singleton('config', lambda c: self._create_config_repository())
        
        # Register cache manager
        self.singleton('cache', lambda c: self._create_cache_manager())
        
        # Register filesystem manager
        self.singleton('files', lambda c: self._create_filesystem_manager())
        
        # Register queue manager
        self.singleton('queue', lambda c: self._create_queue_manager())
        
        # Register hash manager
        self.singleton('hash', lambda c: self._create_hash_manager())
        
        # Register log manager
        self.singleton('log', lambda c: self._create_log_manager())
        
        self.logger.debug("Core Laravel 12 services registered")
    
    def _create_facade_manager(self) -> Any:
        """Create facade manager."""
        try:
            from app.Support.Facades.FacadeManager import FacadeManager
            return FacadeManager(self)
        except ImportError:
            # Fallback for missing facade manager
            return None
    
    def _create_event_dispatcher(self) -> Any:
        """Create event dispatcher."""
        try:
            from app.Events.EventDispatcher import EventDispatcher
            return EventDispatcher(self)
        except ImportError:
            # Fallback for missing event dispatcher
            return None
    
    def _create_config_repository(self) -> Any:
        """Create config repository."""
        try:
            from app.Config.ConfigRepository import ConfigRepository
            return ConfigRepository()
        except ImportError:
            # Fallback for missing config repository
            return {}
    
    def _create_cache_manager(self) -> Any:
        """Create cache manager."""
        try:
            from app.Cache.CacheManager import CacheManager
            return CacheManager(self)
        except ImportError:
            # Fallback for missing cache manager
            return None
    
    def _create_filesystem_manager(self) -> Any:
        """Create filesystem manager."""
        try:
            from app.Filesystem.FilesystemManager import FilesystemManager
            return FilesystemManager(self)
        except ImportError:
            # Fallback for missing filesystem manager
            return None
    
    def _create_queue_manager(self) -> Any:
        """Create queue manager."""
        try:
            from app.Queue.QueueManager import QueueManager
            return QueueManager(self)
        except ImportError:
            # Fallback for missing queue manager
            return None
    
    def _create_hash_manager(self) -> Any:
        """Create hash manager."""
        try:
            from app.Hash.HashManager import HashManager
            return HashManager(self)
        except ImportError:
            # Fallback for missing hash manager
            return None
    
    def _create_log_manager(self) -> Any:
        """Create log manager."""
        try:
            from app.Log.LogManager import LogManager
            return LogManager(self)
        except ImportError:
            # Fallback for missing log manager
            return logging.getLogger()

    @classmethod
    def get_instance(cls) -> ServiceContainer:
        """Get the global container instance."""
        return container


# Laravel 12 enhanced container features
class ContainerManager:
    """Manage multiple container instances (Laravel 12)."""
    
    def __init__(self) -> None:
        self._containers: Dict[str, ServiceContainer] = {}
        self._default_name = 'default'
        self._current_name = self._default_name
        
        # Create default container
        self._containers[self._default_name] = ServiceContainer()
    
    def create(self, name: str) -> ServiceContainer:
        """Create a new container instance."""
        container = ServiceContainer()
        self._containers[name] = container
        return container
    
    def get(self, name: Optional[str] = None) -> ServiceContainer:
        """Get a container by name."""
        name = name or self._current_name
        if name not in self._containers:
            raise ValueError(f"Container '{name}' not found")
        return self._containers[name]
    
    def set_default(self, name: str) -> None:
        """Set the default container."""
        if name not in self._containers:
            raise ValueError(f"Container '{name}' not found")
        self._current_name = name
    
    def destroy(self, name: str) -> None:
        """Destroy a container."""
        if name in self._containers:
            self._containers[name].dispose()
            del self._containers[name]
    
    def list_containers(self) -> List[str]:
        """List all container names."""
        return list(self._containers.keys())
    
    @contextmanager
    def swap(self, name: str) -> Any:
        """Temporarily swap to a different container."""
        old_name = self._current_name
        self.set_default(name)
        try:
            yield self.get(name)
        finally:
            self.set_default(old_name)


# Global container manager and default container
container_manager = ContainerManager()
container = container_manager.get()


def app(abstract: Optional[str] = None, container_name: Optional[str] = None) -> Any:
    """Get the application container or resolve a service (Laravel 12 enhanced)."""
    target_container = container_manager.get(container_name) if container_name else container
    
    if abstract is None:
        return target_container
    return target_container.make(abstract)


async def app_async(abstract: str, container_name: Optional[str] = None) -> Any:
    """Asynchronously resolve a service (Laravel 12)."""
    target_container = container_manager.get(container_name) if container_name else container
    return await target_container.makeAsync(abstract)


def resolve(abstract: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
    """Resolve a service using the default container (Laravel 12)."""
    return container.make(abstract, parameters)


async def resolve_async(abstract: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
    """Asynchronously resolve a service (Laravel 12)."""
    return await container.makeAsync(abstract, parameters)


def tap(instance: T, callback: Callable[[T], None]) -> T:
    """Tap into a resolved instance (Laravel 12)."""
    callback(instance)
    return instance


def rescue(callback: Callable[[], T], rescue_callback: Callable[[Exception], T]) -> T:
    """Execute callback with fallback (Laravel 12)."""
    try:
        return callback()
    except Exception as e:
        return rescue_callback(e)


class WhenContext:
    """Context for contextual binding."""
    
    def __init__(self, container: ServiceContainer, concrete: str):
        self.container = container
        self.concrete = concrete
    
    def needs(self, abstract: str) -> 'GiveContext':
        """Specify what the concrete class needs."""
        return GiveContext(self.container, self.concrete, abstract)


class GiveContext:
    """Context for providing contextual dependencies."""
    
    def __init__(self, container: ServiceContainer, concrete: str, abstract: str):
        self.container = container
        self.concrete = concrete
        self.abstract = abstract
    
    def give(self, implementation: Union[str, Callable[..., Any]]) -> None:
        """Provide the implementation for the contextual binding."""
        if self.concrete not in self.container._contextual_concrete:
            self.container._contextual_concrete[self.concrete] = {}
        
        self.container._contextual_concrete[self.concrete][self.abstract] = implementation
        
        self.container.logger.debug(
            f"Contextual binding: {self.concrete} needs {self.abstract} -> {implementation}"
        )


# Laravel 12 new context managers
@contextmanager
def container_context(container_name: str) -> Any:
    """Temporarily switch container context."""
    old_name = container_manager._current_name
    container_manager.set_default(container_name)
    try:
        yield container_manager.get(container_name)
    finally:
        container_manager.set_default(old_name)


@asynccontextmanager
async def async_container_context(container_name: str) -> Any:
    """Async container context manager."""
    old_name = container_manager._current_name
    container_manager.set_default(container_name)
    try:
        yield container_manager.get(container_name)
    finally:
        container_manager.set_default(old_name)


# Laravel 12 Enhanced Dependency Injection Decorators
def inject(*dependencies: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for explicit dependency injection."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Resolve dependencies and inject them
            resolved_deps = [container.make(dep) for dep in dependencies]
            return func(*resolved_deps, *args, **kwargs)
        return wrapper
    return decorator


def service(name: str, shared: bool = True) -> Callable[[Type[T]], Type[T]]:
    """Class decorator to auto-register a service."""
    def decorator(cls: Type[T]) -> Type[T]:
        if shared:
            container.singleton(name, cls)
        else:
            container.bind(name, cls)
        
        # Also bind by class name
        container.alias(name, cls.__name__)
        return cls
    return decorator


def tagged(*tags: str) -> Callable[[Type[T]], Type[T]]:
    """Class decorator to tag a service."""
    def decorator(cls: Type[T]) -> Type[T]:
        # Register the class and tag it
        class_name = cls.__name__
        container.bind(class_name, cls)
        container.tag(class_name, list(tags))
        return cls
    return decorator


def singleton(cls: Type[T]) -> Type[T]:
    """Class decorator to register as singleton."""
    container.singleton(cls.__name__, cls)
    return cls


def scoped(scope_name: str = "default") -> Callable[[Type[T]], Type[T]]:
    """Class decorator to register as scoped service."""
    def decorator(cls: Type[T]) -> Type[T]:
        container.scoped(cls.__name__, cls)
        return cls
    return decorator


# Laravel 12 Service Locator Pattern
class ServiceLocator:
    """Service locator for accessing container services."""
    
    def __init__(self, container_instance: ServiceContainer) -> None:
        self._container = container_instance
    
    def __getattr__(self, name: str) -> Any:
        """Dynamically resolve services."""
        try:
            return self._container.make(name)
        except Exception:
            raise AttributeError(f"Service '{name}' not found")
    
    def __call__(self, name: str) -> Any:
        """Resolve service by calling locator."""
        return self._container.make(name)
    
    @property
    def config(self) -> Any:
        """Get config service."""
        return self._container.make('config')
    
    @property
    def events(self) -> Any:
        """Get events service."""
        return self._container.make('events')
    
    @property
    def auth(self) -> Any:
        """Get auth service."""
        return self._container.make('auth')
    
    @property
    def cache(self) -> Any:
        """Get cache service."""
        return self._container.make('cache')
    
    @property
    def queue(self) -> Any:
        """Get queue service."""
        return self._container.make('queue')


# Global service locator
services = ServiceLocator(container)


# Laravel 12 Application Context
class ApplicationContext:
    """Application context for accessing services."""
    
    def __init__(self, container_instance: ServiceContainer) -> None:
        self.container = container_instance
        self.services = ServiceLocator(container_instance)
    
    def make(self, abstract: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Resolve service from context."""
        return self.container.make(abstract, parameters)
    
    async def make_async(self, abstract: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Asynchronously resolve service from context."""
        return await self.container.makeAsync(abstract, parameters)
    
    def bound(self, abstract: str) -> bool:
        """Check if service is bound."""
        return self.container.bound(abstract)
    
    def tag(self, abstracts: Union[str, List[str]], tags: Union[str, List[str]]) -> None:
        """Tag services."""
        self.container.tag(abstracts, tags)
    
    def tagged(self, tag: str) -> List[Any]:
        """Get tagged services."""
        return self.container.tagged(tag)
    
    @contextmanager
    def scope(self, name: str) -> Any:
        """Create service scope context."""
        with self.container.scope(name) as scope:
            yield scope


# Global application context
app_context = ApplicationContext(container)


# Export enhanced container functionality
__all__ = [
    'ServiceContainer',
    'ServiceProvider',
    'ContainerManager',
    'container',
    'container_manager',
    'app',
    'app_async',
    'resolve',
    'resolve_async',
    'tap',
    'rescue',
    'services',
    'app_context',
    'inject',
    'service',
    'tagged',
    'singleton',
    'scoped',
    'ServiceLocator',
    'ApplicationContext',
    'container_context',
    'async_container_context',
]