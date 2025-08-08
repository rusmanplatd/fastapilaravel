from __future__ import annotations

from typing import Any, Dict, List, Type, Callable, Optional, Union
from abc import ABC, abstractmethod
from datetime import datetime
import asyncio
import inspect


class Event(ABC):
    """Base Event class following Laravel's event system."""
    
    def __init__(self) -> None:
        self.timestamp = datetime.now()
        self.propagation_stopped = False
    
    def stop_propagation(self) -> None:
        """Stop event propagation to other listeners."""
        self.propagation_stopped = True
    
    def is_propagation_stopped(self) -> bool:
        """Check if propagation is stopped."""
        return self.propagation_stopped


class ShouldQueue(ABC):
    """Interface for events that should be queued."""
    pass


class ShouldBroadcast(ABC):
    """Interface for events that should be broadcast."""
    
    @abstractmethod
    def broadcast_on(self) -> List[str]:
        """Get the channels the event should broadcast on."""
        pass
    
    def broadcast_as(self) -> Optional[str]:
        """Get the name to broadcast the event as."""
        return None
    
    def broadcast_with(self) -> Dict[str, Any]:
        """Get the data to broadcast with the event."""
        return {}


class EventDispatcher:
    """Laravel-style event dispatcher."""
    
    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable[..., Any]]] = {}
        self._wildcards: List[Callable[..., Any]] = []
    
    def listen(self, event: Union[str, Type[Event]], listener: Callable[..., Any]) -> None:
        """Register an event listener."""
        if isinstance(event, type) and issubclass(event, Event):
            event_name = event.__name__
        else:
            event_name = str(event)
        
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        
        self._listeners[event_name].append(listener)
    
    def subscribe(self, subscriber: EventSubscriber) -> None:
        """Register an event subscriber."""
        for event_method in dir(subscriber):
            if event_method.startswith('handle_'):
                event_name = event_method[7:]  # Remove 'handle_' prefix
                method = getattr(subscriber, event_method)
                self.listen(event_name, method)
    
    async def dispatch(self, event: Union[Event, str], *args: Any, **kwargs: Any) -> None:
        """Dispatch an event to all listeners."""
        if isinstance(event, Event):
            event_name = event.__class__.__name__
            event_instance = event
        else:
            event_name = str(event)
            event_instance = None
        
        # Get listeners for this specific event
        listeners = self._listeners.get(event_name, [])
        
        # Add wildcard listeners
        listeners.extend(self._wildcards)
        
        # Execute listeners
        for listener in listeners:
            if event_instance and event_instance.is_propagation_stopped():
                break
            
            try:
                if inspect.iscoroutinefunction(listener):
                    await listener(event_instance or event, *args, **kwargs)
                else:
                    listener(event_instance or event, *args, **kwargs)
            except Exception as e:
                # Log error but continue with other listeners
                print(f"Error in event listener {listener.__name__}: {e}")
    
    def until(self, event: Union[Event, str], *args: Any, **kwargs: Any) -> Any:
        """Dispatch event until first non-null response."""
        # Synchronous version - would need async implementation
        pass
    
    def forget(self, event: Union[str, Type[Event]]) -> None:
        """Remove all listeners for an event."""
        if isinstance(event, type) and issubclass(event, Event):
            event_name = event.__name__
        else:
            event_name = str(event)
        
        if event_name in self._listeners:
            del self._listeners[event_name]


class EventSubscriber(ABC):
    """Base class for event subscribers."""
    
    @abstractmethod
    def subscribe(self, dispatcher: EventDispatcher) -> None:
        """Subscribe to events."""
        pass


# Global event dispatcher instance
event_dispatcher = EventDispatcher()


# Convenience functions
def listen(event: Union[str, Type[Event]], listener: Callable[..., Any]) -> None:
    """Register an event listener."""
    event_dispatcher.listen(event, listener)


async def dispatch(event: Union[Event, str], *args: Any, **kwargs: Any) -> None:
    """Dispatch an event."""
    await event_dispatcher.dispatch(event, *args, **kwargs)


def event(event_name: str) -> Callable[..., Any]:
    """Decorator to register a function as an event listener."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        listen(event_name, func)
        return func
    return decorator