from __future__ import annotations

from typing import Any, Type, Optional, Dict, Callable
from abc import ABC, abstractmethod
from .ServiceContainer import container


class Facade(ABC):
    """Base Facade class following Laravel's facade pattern."""
    
    _resolved_instances: Dict[str, Any] = {}
    
    @classmethod
    @abstractmethod
    def get_facade_accessor(cls) -> str:
        """Get the registered name of the component."""
        pass
    
    @classmethod
    def get_facade_root(cls) -> Any:
        """Get the root object behind the facade."""
        accessor = cls.get_facade_accessor()
        
        # Use cached instance if available (singleton-like behavior)
        if accessor in cls._resolved_instances:
            return cls._resolved_instances[accessor]
        
        instance = container.make(accessor)
        cls._resolved_instances[accessor] = instance
        return instance
    
    @classmethod
    def clear_resolved_instance(cls) -> None:
        """Clear the resolved facade instance."""
        accessor = cls.get_facade_accessor()
        if accessor in cls._resolved_instances:
            del cls._resolved_instances[accessor]
    
    @classmethod
    def clear_resolved_instances(cls) -> None:
        """Clear all resolved facade instances."""
        cls._resolved_instances.clear()
    
    @classmethod
    def __getattr__(cls, name: str) -> Any:
        """Proxy attribute access to the facade root."""
        root = cls.get_facade_root()
        attr = getattr(root, name)
        
        # If it's a method, return a callable that binds to the root
        if callable(attr):
            return attr
        return attr


# Example Facades

class Auth(Facade):
    """Auth facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "AuthService"


class Queue(Facade):
    """Queue facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "QueueService"


class Event(Facade):
    """Event facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "EventDispatcher"


class Notification(Facade):
    """Notification facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "NotificationService"


class Log(Facade):
    """Log facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "ActivityLogService"


class Cache(Facade):
    """Cache facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "CacheManager"


class Mail(Facade):
    """Mail facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "MailManager"


class Storage(Facade):
    """Storage facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "FilesystemAdapter"


class Gate(Facade):
    """Gate facade for authorization."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "Gate"


class Broadcast(Facade):
    """Broadcast facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "BroadcastManager"


class Config(Facade):
    """Config facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "ConfigRepository"


class DB(Facade):
    """Database facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "Database"


class Validator(Facade):
    """Validator facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "Validator"


class Hash(Facade):
    """Hash facade."""
    
    @classmethod
    def get_facade_accessor(cls) -> str:
        return "PasswordUtils"