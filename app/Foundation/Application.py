from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING, Type, Union, Callable, Any, AsyncGenerator
from app.Types import JsonValue, JsonObject, ConfigValue
from fastapi import FastAPI
import os
from pathlib import Path
from app.Support.ServiceContainer import ServiceContainer
from app.Foundation.ServiceProvider import ServiceProvider
from app.Providers.AppServiceProvider import AppServiceProvider
import logging
import asyncio
from contextlib import asynccontextmanager
import time

if TYPE_CHECKING:
    pass


class Application(ServiceContainer):
    """Laravel 12 Application class with enhanced features and strict typing."""
    
    def __init__(self, base_path: Optional[str] = None) -> None:
        super().__init__()
        
        # Laravel 12 enhanced properties with strict typing
        self._base_path: Path = Path(base_path) if base_path else Path.cwd()
        self._environment: str = os.getenv('APP_ENV', 'production')
        self._debug: bool = os.getenv('APP_DEBUG', 'false').lower() == 'true'
        self._version: str = '12.0.0'  # Laravel 12
        self._locale: str = 'en'
        self._fallback_locale: str = 'en'
        self._timezone: str = 'UTC'
        self._key: str = os.getenv('APP_KEY', '')
        self._cipher: str = 'AES-256-GCM'  # Laravel 12 enhanced encryption
        self._providers: List[ServiceProvider] = []
        self._loaded_providers: Dict[str, ServiceProvider] = {}
        self._deferred_providers: Dict[str, ServiceProvider] = {}
        self._booted: bool = False
        self._service_providers: List[Type[ServiceProvider]] = []
        self._fastapi_app: Optional[FastAPI] = None
        
        # Laravel 12 new features
        self._started: bool = False
        self._terminating: bool = False
        self._startup_callbacks: List[Callable[[], None]] = []
        self._shutdown_callbacks: List[Callable[[], None]] = []
        self._maintenance_mode: bool = False
        self._maintenance_payload: Optional[Dict[str, Any]] = None
        self._running_in_console: bool = False
        self._cached_paths: Dict[str, str] = {}
        self._environment_loaded: bool = False
        self._config_cached: bool = False
        self._routes_cached: bool = False
        self._events_cached: bool = False
        
        # Performance tracking
        self._boot_time: Optional[float] = None
        self._startup_time: Optional[float] = None
        self._memory_usage: Dict[str, int] = {}
        
        # Logger for application
        self._logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        
        # Register base paths
        self._register_base_paths()
        
        # Register core services
        self._register_core_services()
    
    def _register_base_paths(self) -> None:
        """Register base application paths."""
        paths = {
            'base': str(self._base_path),
            'app': str(self._base_path / 'app'),
            'config': str(self._base_path / 'config'),
            'database': str(self._base_path / 'database'),
            'resources': str(self._base_path / 'resources'),
            'routes': str(self._base_path / 'routes'),
            'storage': str(self._base_path / 'storage'),
            'bootstrap': str(self._base_path / 'bootstrap'),
            'public': str(self._base_path / 'public'),
        }
        
        for name, path in paths.items():
            self.instance(f'path.{name}', path)
    
    def _register_core_services(self) -> None:
        """Register core application services."""
        self.instance('app', self)
        self.instance('env', self._environment)
        self.alias('app', Application.__name__)
    
    def path(self, path: str = '') -> str:
        """Get the path to the application directory."""
        base_path = str(self._base_path / 'app')
        return os.path.join(base_path, path) if path else base_path
    
    def base_path(self, path: str = '') -> str:
        """Get the base path of the application."""
        base_path = str(self._base_path)
        return os.path.join(base_path, path) if path else base_path
    
    def config_path(self, path: str = '') -> str:
        """Get the path to the config directory."""
        config_path = str(self._base_path / 'config')
        return os.path.join(config_path, path) if path else config_path
    
    def database_path(self, path: str = '') -> str:
        """Get the path to the database directory."""
        database_path = str(self._base_path / 'database')
        return os.path.join(database_path, path) if path else database_path
    
    def resource_path(self, path: str = '') -> str:
        """Get the path to the resources directory."""
        resource_path = str(self._base_path / 'resources')
        return os.path.join(resource_path, path) if path else resource_path
    
    def storage_path(self, path: str = '') -> str:
        """Get the path to the storage directory."""
        storage_path = str(self._base_path / 'storage')
        return os.path.join(storage_path, path) if path else storage_path
    
    def bootstrap_path(self, path: str = '') -> str:
        """Get the path to the bootstrap directory."""
        bootstrap_path = str(self._base_path / 'bootstrap')
        return os.path.join(bootstrap_path, path) if path else bootstrap_path
    
    def public_path(self, path: str = '') -> str:
        """Get the path to the public directory."""
        public_path = str(self._base_path / 'public')
        return os.path.join(public_path, path) if path else public_path
    
    def environment(self, *environments: str) -> Union[str, bool]:
        """Get or check the current application environment."""
        if not environments:
            return self._environment
        return self._environment in environments
    
    def is_local(self) -> bool:
        """Determine if the application is in local environment."""
        return self._environment == 'local'
    
    def is_production(self) -> bool:
        """Determine if the application is in production."""
        return self._environment == 'production'
    
    def is_debug(self) -> bool:
        """Determine if the application is in debug mode."""
        return self._debug
    
    def version(self) -> str:
        """Get the version number of the application."""
        return self._version
    
    def locale(self) -> str:
        """Get the current application locale."""
        return self._locale
    
    def set_locale(self, locale: str) -> None:
        """Set the current application locale."""
        self._locale = locale
    
    def fallback_locale(self) -> str:
        """Get the fallback locale for the application."""
        return self._fallback_locale
    
    def set_fallback_locale(self, locale: str) -> None:
        """Set the fallback locale for the application."""
        self._fallback_locale = locale
    
    def timezone(self) -> str:
        """Get the application timezone."""
        return self._timezone
    
    def set_timezone(self, timezone: str) -> None:
        """Set the application timezone."""
        self._timezone = timezone
    
    def key(self) -> str:
        """Get the application key."""
        return self._key
    
    def cipher(self) -> str:
        """Get the encryption cipher."""
        return self._cipher
    
    def register(self, provider: Union[ServiceProvider, Type[ServiceProvider], str], force: bool = False) -> ServiceProvider:
        """Register a service provider with Laravel 12 enhancements."""
        if self._terminating:
            raise RuntimeError("Cannot register providers during application termination")
        
        resolved_provider: ServiceProvider
        
        if isinstance(provider, str):
            # Import provider class from string with enhanced error handling
            try:
                parts = provider.split('.')
                if len(parts) < 2:
                    raise ValueError(f"Invalid provider string format: {provider}")
                
                module_name = '.'.join(parts[:-1])
                class_name = parts[-1]
                module = __import__(module_name, fromlist=[class_name])
                provider_class = getattr(module, class_name)
                
                if not issubclass(provider_class, ServiceProvider):
                    raise TypeError(f"Provider class {class_name} must extend ServiceProvider")
                
                resolved_provider = provider_class(self)
            except (ImportError, AttributeError, TypeError) as e:
                self._logger.error(f"Failed to load provider {provider}: {e}")
                raise ValueError(f"Cannot load provider {provider}: {e}") from e
                
        elif isinstance(provider, type) and issubclass(provider, ServiceProvider):
            resolved_provider = provider(self)
        elif isinstance(provider, ServiceProvider):
            resolved_provider = provider
        else:
            raise TypeError("Provider must be a ServiceProvider instance, class, or string")
        
        provider_name = resolved_provider.__class__.__name__
        
        # Check for duplicate registration
        if provider_name in self._loaded_providers and not force:
            self._logger.debug(f"Provider {provider_name} already registered")
            return self._loaded_providers[provider_name]
        
        # Laravel 12: Check provider dependencies
        self._validate_provider_dependencies(resolved_provider)
        
        try:
            # Register the provider
            resolved_provider.register()
            
            # Store provider with enhanced tracking
            self._providers.append(resolved_provider)
            self._loaded_providers[provider_name] = resolved_provider
            
            # Boot if application is already booted
            if self._booted:
                resolved_provider.boot()
            
            self._logger.debug(f"Registered provider: {provider_name}")
            return resolved_provider
            
        except Exception as e:
            self._logger.error(f"Failed to register provider {provider_name}: {e}")
            # Cleanup on failure
            if resolved_provider in self._providers:
                self._providers.remove(resolved_provider)
            if provider_name in self._loaded_providers:
                del self._loaded_providers[provider_name]
            raise
    
    def get_providers(self, provider_class: Type[ServiceProvider]) -> List[ServiceProvider]:
        """Get all providers of a specific type."""
        return [p for p in self._providers if isinstance(p, provider_class)]
    
    def load_deferred_providers(self) -> None:
        """Load all deferred providers."""
        for abstract, provider in self._deferred_providers.items():
            if not self.bound(abstract):
                self.register(provider)
    
    def boot(self) -> None:
        """Boot the application's service providers with Laravel 12 enhancements."""
        if self._booted:
            self._logger.debug("Application already booted")
            return
        
        if self._terminating:
            raise RuntimeError("Cannot boot application during termination")
        
        start_time = time.time()
        
        try:
            self._logger.info("Booting application...")
            
            # Laravel 12: Boot providers in dependency order
            sorted_providers = self._sort_providers_by_dependencies()
            
            for provider in sorted_providers:
                try:
                    self._logger.debug(f"Booting provider: {provider.__class__.__name__}")
                    provider.boot()
                except Exception as e:
                    self._logger.error(f"Error booting provider {provider.__class__.__name__}: {e}")
                    raise RuntimeError(f"Failed to boot provider {provider.__class__.__name__}") from e
            
            self._booted = True
            self._boot_time = time.time() - start_time
            
            # Execute any stored booted callbacks
            if hasattr(self, '_booted_callbacks'):
                for callback in self._booted_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        self._logger.error(f"Error executing booted callback: {e}")
                
                # Clear callbacks after execution
                self._booted_callbacks.clear()
            
            self._logger.info(f"Application booted successfully in {self._boot_time:.4f}s")
                
        except Exception as e:
            self._logger.error(f"Error booting application: {e}")
            self._booted = False
            raise
    
    def booted(self, callback: Callable[[], None]) -> None:
        """Register a callback to run after the application is booted."""
        if self._booted:
            try:
                callback()
            except Exception as e:
                # Log the error but don't stop the application
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error executing booted callback: {e}")
        else:
            # Store callbacks to run after boot() is called
            if not hasattr(self, '_booted_callbacks'):
                self._booted_callbacks: List[Callable[[], None]] = []
            self._booted_callbacks.append(callback)
    
    def is_booted(self) -> bool:
        """Check if the application has been booted."""
        return self._booted
    
    def register_configured_providers(self) -> None:
        """Register all configured providers."""
        providers = [
            AppServiceProvider,
            # Add more default providers here
        ]
        
        for provider_class in providers:
            self.register(provider_class)
    
    def get_namespace(self) -> str:
        """Get the application namespace."""
        return 'App'
    
    def flush(self) -> None:
        """Flush the container of all bindings and resolved instances."""
        self._bindings.clear()
        self._instances.clear()
        self._aliases.clear()
        self._resolved_callbacks.clear()
        self._rebound_callbacks.clear()
        self._refresh_instances.clear()
    
    def terminate(self) -> None:
        """Terminate the application."""
        # Clean up resources
        self.flush()
        
        # Call terminate on all providers
        for provider in self._providers:
            if hasattr(provider, 'terminate'):
                try:
                    provider.terminate()
                except Exception as e:
                    self._logger.error(f"Error terminating provider {provider.__class__.__name__}: {e}")
    
    def set_fastapi_app(self, app: FastAPI) -> None:
        """Set the FastAPI application instance."""
        self._fastapi_app = app
        self.instance('fastapi', app)
    
    def get_fastapi_app(self) -> Optional[FastAPI]:
        """Get the FastAPI application instance."""
        return self._fastapi_app
    
    # Laravel 12 new methods
    def start(self) -> None:
        """Start the application with Laravel 12 lifecycle."""
        if self._started:
            return
        
        if self._terminating:
            raise RuntimeError("Cannot start application during termination")
        
        start_time = time.time()
        self._logger.info("Starting application...")
        
        try:
            # Execute startup callbacks
            for callback in self._startup_callbacks:
                try:
                    callback()
                except Exception as e:
                    self._logger.error(f"Error in startup callback: {e}")
                    raise
            
            self._started = True
            self._startup_time = time.time() - start_time
            self._logger.info(f"Application started successfully in {self._startup_time:.4f}s")
            
        except Exception as e:
            self._logger.error(f"Error starting application: {e}")
            raise
    
    def is_started(self) -> bool:
        """Check if the application has been started."""
        return self._started
    
    def starting(self, callback: Callable[[], None]) -> None:
        """Register a callback to run during application startup."""
        self._startup_callbacks.append(callback)
    
    def shutdown(self, callback: Callable[[], None]) -> None:
        """Register a callback to run during application shutdown."""
        self._shutdown_callbacks.append(callback)
    
    def is_maintenance_mode(self) -> bool:
        """Check if application is in maintenance mode."""
        return self._maintenance_mode
    
    def enable_maintenance_mode(self, payload: Optional[Dict[str, Any]] = None) -> None:
        """Enable maintenance mode."""
        self._maintenance_mode = True
        self._maintenance_payload = payload or {}
        self._logger.info("Maintenance mode enabled")
    
    def disable_maintenance_mode(self) -> None:
        """Disable maintenance mode."""
        self._maintenance_mode = False
        self._maintenance_payload = None
        self._logger.info("Maintenance mode disabled")
    
    def get_maintenance_payload(self) -> Optional[Dict[str, Any]]:
        """Get maintenance mode payload."""
        return self._maintenance_payload
    
    def running_in_console(self) -> bool:
        """Check if application is running in console."""
        return self._running_in_console
    
    def set_running_in_console(self, console: bool) -> None:
        """Set console mode."""
        self._running_in_console = console
    
    def cached_config_path(self) -> str:
        """Get the cached configuration file path."""
        return self.bootstrap_path('cache/config.php')
    
    def cached_routes_path(self) -> str:
        """Get the cached routes file path."""
        return self.bootstrap_path('cache/routes.php')
    
    def cached_events_path(self) -> str:
        """Get the cached events file path."""
        return self.bootstrap_path('cache/events.php')
    
    def is_config_cached(self) -> bool:
        """Check if configuration is cached."""
        return self._config_cached
    
    def is_routes_cached(self) -> bool:
        """Check if routes are cached."""
        return self._routes_cached
    
    def is_events_cached(self) -> bool:
        """Check if events are cached."""
        return self._events_cached
    
    def get_boot_time(self) -> Optional[float]:
        """Get application boot time."""
        return self._boot_time
    
    def get_startup_time(self) -> Optional[float]:
        """Get application startup time."""
        return self._startup_time
    
    def get_memory_usage(self) -> Dict[str, Union[int, float]]:
        """Get memory usage statistics."""
        try:
            import psutil
            process = psutil.Process()
            return {
                'rss': process.memory_info().rss,
                'vms': process.memory_info().vms,
                'percent': process.memory_percent()
            }
        except ImportError:
            # Fallback when psutil is not available
            import os
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {
                'rss': usage.ru_maxrss * 1024,  # Convert to bytes
                'vms': 0,
                'percent': 0.0
            }
    
    def _validate_provider_dependencies(self, provider: ServiceProvider) -> None:
        """Validate provider dependencies (Laravel 12)."""
        # Check if provider has dependency requirements
        if hasattr(provider, 'dependencies') and provider.dependencies:
            for dep in provider.dependencies:
                if not self.bound(dep):
                    self._logger.warning(f"Provider {provider.__class__.__name__} requires {dep} but it's not bound")
    
    def _sort_providers_by_dependencies(self) -> List[ServiceProvider]:
        """Sort providers by their dependencies (Laravel 12)."""
        # Simple topological sort for now
        # In a full implementation, this would use proper dependency resolution
        return self._providers.copy()
    
    async def start_async(self) -> None:
        """Start the application asynchronously."""
        await asyncio.get_event_loop().run_in_executor(None, self.start)
    
    async def boot_async(self) -> None:
        """Boot the application asynchronously."""
        await asyncio.get_event_loop().run_in_executor(None, self.boot)
    
    @asynccontextmanager
    async def lifecycle(self) -> AsyncGenerator[Application, None]:
        """Async context manager for application lifecycle."""
        try:
            self.start()
            if not self._booted:
                self.boot()
            yield self
        finally:
            self.terminate()


# Global application instance with strict typing
app_instance: Optional[Application] = None


def create_application(base_path: Optional[str] = None) -> Application:
    """Create a new application instance with Laravel 12 features."""
    global app_instance
    app_instance = Application(base_path)
    return app_instance


def app() -> Application:
    """Get the global application instance."""
    global app_instance
    if app_instance is None:
        app_instance = create_application()
    return app_instance


def app_or_none() -> Optional[Application]:
    """Get the global application instance or None if not created."""
    return app_instance


