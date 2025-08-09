from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING, Type, Union, Callable
from fastapi import FastAPI
import os
from pathlib import Path
from app.Support.ServiceContainer import ServiceContainer, ServiceProvider
from app.Providers.AppServiceProvider import AppServiceProvider

if TYPE_CHECKING:
    pass


class Application(ServiceContainer):
    """Laravel-style Application class extending ServiceContainer."""
    
    def __init__(self, base_path: Optional[str] = None) -> None:
        super().__init__()
        
        self._base_path = Path(base_path) if base_path else Path.cwd()
        self._environment = os.getenv('APP_ENV', 'production')
        self._debug = os.getenv('APP_DEBUG', 'false').lower() == 'true'
        self._version = '1.0.0'
        self._locale = 'en'
        self._fallback_locale = 'en'
        self._timezone = 'UTC'
        self._key = os.getenv('APP_KEY', '')
        self._cipher = 'AES-256-CBC'
        self._providers: List[ServiceProvider] = []
        self._loaded_providers: Dict[str, ServiceProvider] = {}
        self._deferred_providers: Dict[str, ServiceProvider] = {}
        self._booted = False
        self._service_providers: List[Type[ServiceProvider]] = []
        self._fastapi_app: Optional[FastAPI] = None
        
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
        """Register a service provider."""
        if isinstance(provider, str):
            # Import provider class from string
            parts = provider.split('.')
            module_name = '.'.join(parts[:-1])
            class_name = parts[-1]
            module = __import__(module_name, fromlist=[class_name])
            provider_class = getattr(module, class_name)
            provider = provider_class(self)
        elif inspect.isclass(provider):
            provider = provider(self)
        
        if not isinstance(provider, ServiceProvider):
            raise ValueError("Provider must be an instance of ServiceProvider")
        
        if provider.__class__.__name__ in self._loaded_providers and not force:
            return self._loaded_providers[provider.__class__.__name__]
        
        provider.register()
        
        # Store provider
        self._providers.append(provider)
        self._loaded_providers[provider.__class__.__name__] = provider
        
        # Boot if application is already booted
        if self._booted:
            provider.boot()
        
        return provider
    
    def get_providers(self, provider_class: Type[ServiceProvider]) -> List[ServiceProvider]:
        """Get all providers of a specific type."""
        return [p for p in self._providers if isinstance(p, provider_class)]
    
    def load_deferred_providers(self) -> None:
        """Load all deferred providers."""
        for abstract, provider in self._deferred_providers.items():
            if not self.bound(abstract):
                self.register(provider)
    
    def boot(self) -> None:
        """Boot the application's service providers."""
        if self._booted:
            return
        
        try:
            # Boot all providers
            for provider in self._providers:
                provider.boot()
            
            self._booted = True
            
            # Execute any stored booted callbacks
            if hasattr(self, '_booted_callbacks'):
                for callback in self._booted_callbacks:
                    try:
                        callback(self)
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Error executing booted callback: {e}")
                
                # Clear callbacks after execution
                self._booted_callbacks.clear()
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error booting application: {e}")
            raise
    
    def booted(self, callback: Callable[[Application], None]) -> None:
        """Register a callback to run after the application is booted."""
        if self._booted:
            try:
                callback(self)
            except Exception as e:
                # Log the error but don't stop the application
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error executing booted callback: {e}")
        else:
            # Store callbacks to run after boot() is called
            if not hasattr(self, '_booted_callbacks'):
                self._booted_callbacks: List[Callable[[Application], None]] = []
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
                provider.terminate()
    
    def set_fastapi_app(self, app: FastAPI) -> None:
        """Set the FastAPI application instance."""
        self._fastapi_app = app
        self.instance('fastapi', app)
    
    def get_fastapi_app(self) -> Optional[FastAPI]:
        """Get the FastAPI application instance."""
        return self._fastapi_app


# Global application instance
app_instance: Optional[Application] = None


def create_application(base_path: Optional[str] = None) -> Application:
    """Create a new application instance."""
    global app_instance
    app_instance = Application(base_path)
    return app_instance


def app() -> Application:
    """Get the global application instance."""
    global app_instance
    if app_instance is None:
        app_instance = create_application()
    return app_instance


# Import for type checking
import inspect