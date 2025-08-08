from __future__ import annotations

from typing import Any, Type, Optional
from abc import ABC, abstractmethod
from .ServiceContainer import container


class Facade(ABC):
    """Base Facade class following Laravel's facade pattern."""
    
    @classmethod
    @abstractmethod
    def get_facade_accessor(cls) -> str:
        """Get the registered name of the component."""
        pass
    
    @classmethod
    def get_facade_root(cls) -> Any:
        """Get the root object behind the facade."""
        return container.make(cls.get_facade_accessor())
    
    def __class_getitem__(cls, item: Any) -> Any:
        """Support for generic facades."""
        return cls.get_facade_root()
    
    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to the facade root."""
        root = self.get_facade_root()
        return getattr(root, name)


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