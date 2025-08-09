from __future__ import annotations

from typing import Any, Dict, Type, Optional, Callable, cast, Generator
from abc import ABC, abstractmethod
import threading
from contextlib import contextmanager

from app.Support.ServiceContainer import ServiceContainer


class Facade(ABC):
    """Base class for Laravel-style facades."""
    
    _resolved_instances: Dict[str, Any] = {}
    _app: Optional[ServiceContainer] = None
    _lock = threading.RLock()
    
    @classmethod
    @abstractmethod
    def get_facade_accessor(cls) -> str:
        """Get the registered name of the component."""
        pass
    
    @classmethod
    def get_facade_root(cls) -> Any:
        """Get the root object behind the facade."""
        return cls.resolve_facade_instance(cls.get_facade_accessor())
    
    @classmethod
    def resolve_facade_instance(cls, name: str) -> Any:
        """Resolve the facade root instance from the container."""
        if cls._app is None:
            raise RuntimeError("A facade root has not been set.")
        
        return cls._app.make(name)
    
    @classmethod
    def clear_resolved_instance(cls, name: str) -> None:
        """Clear a resolved facade instance."""
        with cls._lock:
            if name in cls._resolved_instances:
                del cls._resolved_instances[name]
    
    @classmethod
    def clear_resolved_instances(cls) -> None:
        """Clear all resolved facade instances."""
        with cls._lock:
            cls._resolved_instances.clear()
    
    @classmethod
    def get_facade_application(cls) -> Optional[ServiceContainer]:
        """Get the application instance behind the facade."""
        return cls._app
    
    @classmethod
    def set_facade_application(cls, app: ServiceContainer) -> None:
        """Set the application instance."""
        cls._app = app
    
    @classmethod
    def __getattr__(cls, item: str) -> Any:
        """Dynamically pass methods to the facade root."""
        instance = cls.get_facade_root()
        
        if not hasattr(instance, item):
            raise AttributeError(f"'{cls.__name__}' object has no attribute '{item}'")
        
        attr = getattr(instance, item)
        
        if callable(attr):
            def facade_method(*args: Any, **kwargs: Any) -> Any:
                return attr(*args, **kwargs)
            return facade_method
        
        return attr


class FacadeManager:
    """Manager for Laravel-style facades."""
    
    def __init__(self, container: ServiceContainer):
        self.container = container
        self.facades: Dict[str, Type[Facade]] = {}
        self.aliases: Dict[str, str] = {}
        self._lock = threading.RLock()
    
    def register(self, facade_class: Type[Facade], alias: Optional[str] = None) -> None:
        """Register a facade."""
        accessor = facade_class.get_facade_accessor()
        
        with self._lock:
            self.facades[accessor] = facade_class
            
            if alias:
                self.aliases[alias] = accessor
        
        # Set the application instance
        facade_class.set_facade_application(self.container)
    
    def get_facade(self, name: str) -> Optional[Type[Facade]]:
        """Get a facade by name or alias."""
        # Check if it's an alias
        if name in self.aliases:
            name = self.aliases[name]
        
        return self.facades.get(name)
    
    def make_facade(self, name: str) -> Any:
        """Make a facade instance."""
        facade_class = self.get_facade(name)
        if facade_class:
            return facade_class.get_facade_root()
        
        raise ValueError(f"Facade '{name}' not found")
    
    def clear_all(self) -> None:
        """Clear all facade instances."""
        with self._lock:
            for facade_class in self.facades.values():
                facade_class.clear_resolved_instances()
    
    def set_container(self, container: ServiceContainer) -> None:
        """Set the container for all facades."""
        self.container = container
        
        with self._lock:
            for facade_class in self.facades.values():
                facade_class.set_facade_application(container)


# Common Laravel Facades

class App(Facade):
    """Application facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'app'


class Config(Facade):
    """Configuration facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'config'


class Cache(Facade):
    """Cache facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'cache'


class DB(Facade):
    """Database facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'db'


class Event(Facade):
    """Event facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'events'


class Hash(Facade):
    """Hash facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'hash'


class Log(Facade):
    """Log facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'log'


class Queue(Facade):
    """Queue facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'queue'


class Storage(Facade):
    """Storage facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'filesystem'


class Mail(Facade):
    """Mail facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'mail'


class Notification(Facade):
    """Notification facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'notification'


class Auth(Facade):
    """Auth facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'auth'


class Session(Facade):
    """Session facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'session'


class Cookie(Facade):
    """Cookie facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'cookie'


class Crypt(Facade):
    """Encryption facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'encrypter'


class Validator(Facade):
    """Validator facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'validator'


class Artisan(Facade):
    """Artisan facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'artisan'


class Route(Facade):
    """Route facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'router'


class View(Facade):
    """View facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'view'


# Real-time facade for testing
class FacadeTester:
    """Testing utilities for facades."""
    
    def __init__(self, facade_manager: FacadeManager):
        self.facade_manager = facade_manager
        self.original_instances: Dict[str, Any] = {}
    
    @contextmanager
    def fake(self, facade_name: str, fake_instance: Any) -> Generator[Any, None, None]:
        """Temporarily replace a facade with a fake."""
        facade_class = self.facade_manager.get_facade(facade_name)
        if not facade_class:
            raise ValueError(f"Facade '{facade_name}' not found")
        
        # Store original
        accessor = facade_class.get_facade_accessor()
        original = self.facade_manager.container.make(accessor) if self.facade_manager.container.bound(accessor) else None
        
        # Replace with fake
        self.facade_manager.container.instance(accessor, fake_instance)
        
        try:
            yield fake_instance
        finally:
            # Restore original
            if original:
                self.facade_manager.container.instance(accessor, original)
            else:
                self.facade_manager.container.forget(accessor)
            
            # Clear resolved facade instance
            facade_class.clear_resolved_instance(accessor)


def create_facade_manager(container: ServiceContainer) -> FacadeManager:
    """Create and configure a facade manager with common facades."""
    manager = FacadeManager(container)
    
    # Register common facades
    manager.register(App, 'App')
    manager.register(Config, 'Config')
    manager.register(Cache, 'Cache')
    manager.register(DB, 'DB')
    manager.register(Event, 'Event')
    manager.register(Hash, 'Hash')
    manager.register(Log, 'Log')
    manager.register(Queue, 'Queue')
    manager.register(Storage, 'Storage')
    manager.register(Mail, 'Mail')
    manager.register(Notification, 'Notification')
    manager.register(Auth, 'Auth')
    manager.register(Session, 'Session')
    manager.register(Cookie, 'Cookie')
    manager.register(Crypt, 'Crypt')
    manager.register(Validator, 'Validator')
    manager.register(Artisan, 'Artisan')
    manager.register(Route, 'Route')
    manager.register(View, 'View')
    
    return manager


# Testing facade functionality
class TestFacade(Facade):
    """Test facade for demonstration."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return 'test_service'


class TestService:
    """Test service for facade demonstration."""
    
    def __init__(self, name: str = "TestService"):
        self.name = name
        self.call_count = 0
    
    def hello(self, message: str = "Hello") -> str:
        """Test method."""
        self.call_count += 1
        return f"{self.name}: {message} (call #{self.call_count})"
    
    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        return {
            'name': self.name,
            'call_count': self.call_count,
            'status': 'active'
        }