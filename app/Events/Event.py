from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, Type, TypeVar, get_type_hints, Coroutine
from abc import ABC, abstractmethod
import asyncio
import inspect
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid
from contextlib import asynccontextmanager

from app.Support.ServiceContainer import ServiceContainer

T = TypeVar('T')


class EventPriority(Enum):
    """Event listener priorities."""
    HIGHEST = 1
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


@dataclass
class EventSubscription:
    """Event subscription configuration."""
    event_class: Optional[Type['Event']]
    listener: Union[Callable[..., Any], Type['EventListener']]
    priority: int = EventPriority.NORMAL.value
    queue: Optional[str] = None
    should_queue: bool = False
    halt_on_failure: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


class Event(ABC):
    """Base class for Laravel-style events."""
    
    def __init__(self) -> None:
        self.event_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        self.propagation_stopped = False
        self.broadcast_channels: List[str] = []
        self.broadcast_data: Dict[str, Any] = {}
    
    def stop_propagation(self) -> None:
        """Stop event propagation to remaining listeners."""
        self.propagation_stopped = True
    
    def should_broadcast(self) -> bool:
        """Determine if the event should be broadcast."""
        return len(self.broadcast_channels) > 0
    
    def broadcast_on(self) -> List[str]:
        """Get the channels the event should broadcast on."""
        return self.broadcast_channels
    
    def broadcast_with(self) -> Dict[str, Any]:
        """Get the data to broadcast with the event."""
        return self.broadcast_data or self.to_dict()
    
    def broadcast_as(self) -> str:
        """Get the broadcast event name."""
        return self.__class__.__name__
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        result = {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.__class__.__name__
        }
        
        # Add public attributes
        for key, value in self.__dict__.items():
            if not key.startswith('_') and key not in ['event_id', 'timestamp', 'propagation_stopped']:
                if isinstance(value, (str, int, float, bool, list, dict)):
                    result[key] = str(value) if not isinstance(value, str) else value
                else:
                    result[key] = str(value)
        
        return result
    
    def to_json(self) -> str:
        """Convert event to JSON."""
        return json.dumps(self.to_dict(), default=str)


class ShouldQueue:
    """Marker interface for events that should be queued."""
    pass


class EventListener(ABC):
    """Base class for event listeners."""
    
    def __init__(self, container: Optional[ServiceContainer] = None):
        self.container = container
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def handle(self, event: Event) -> Any:
        """Handle the event."""
        # Override this method to define your event handling logic
        # Example:
        # if isinstance(event, UserRegistered):
        #     await self.send_welcome_email(event.user)
        # return True
        
        self.logger.info(f"Handling event: {event.__class__.__name__}")
        return True
    
    def should_queue(self, event: Event) -> bool:
        """Determine if this listener should be queued."""
        return isinstance(event, ShouldQueue)
    
    def queue_name(self, event: Event) -> Optional[str]:
        """Get the queue name for this listener."""
        return None
    
    def failed(self, event: Event, exception: Exception) -> None:
        """Handle a failed event."""
        self.logger.error(f"Failed to handle event {event.__class__.__name__}: {exception}")


class BroadcastableEvent(Event):
    """Event that can be broadcast to channels."""
    
    def __init__(self) -> None:
        super().__init__()
        self._channels: List[str] = []
        self._data: Dict[str, Any] = {}
    
    def broadcast_on(self) -> List[str]:
        """Get the channels to broadcast on."""
        return self._channels
    
    def broadcast_with(self) -> Dict[str, Any]:
        """Get the data to broadcast."""
        return self._data or self.to_dict()


class EventDispatcher:
    """Enhanced Laravel-style event dispatcher."""
    
    def __init__(self, container: Optional[ServiceContainer] = None):
        self.container = container
        self.listeners: Dict[str, List[EventSubscription]] = {}
        self.wildcards: List[EventSubscription] = []
        self.pushed_listeners: Dict[str, List[Union[Callable[..., Any], Type[EventListener]]]] = {}
        self.queue_resolver: Optional[Callable[..., Any]] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self.broadcasting_enabled = True
        self.broadcast_manager: Optional[Any] = None
        
        # Event statistics
        self.stats = {
            'events_dispatched': 0,
            'listeners_executed': 0,
            'failed_listeners': 0,
            'queued_listeners': 0
        }
    
    def listen(self, event: Union[str, Type[Event]], listener: Union[Callable[..., Any], Type[EventListener]], priority: int = EventPriority.NORMAL.value) -> None:
        """Register an event listener."""
        event_name = event if isinstance(event, str) else event.__name__
        
        subscription = EventSubscription(
            event_class=event if not isinstance(event, str) else None,
            listener=listener,
            priority=priority
        )
        
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        
        self.listeners[event_name].append(subscription)
        
        # Sort by priority
        self.listeners[event_name].sort(key=lambda s: s.priority)
        
        self.logger.debug(f"Registered listener for event: {event_name}")
    
    def subscribe(self, subscriber: 'EventSubscriber') -> None:
        """Register an event subscriber."""
        if hasattr(subscriber, 'subscribe'):
            subscriber.subscribe(self)
        else:
            # Auto-discover methods
            for method_name in dir(subscriber):
                if method_name.startswith('handle_'):
                    method = getattr(subscriber, method_name)
                    if callable(method):
                        event_name = method_name[7:]  # Remove 'handle_' prefix
                        self.listen(event_name, method)
    
    def forget(self, event: Union[str, Type[Event]]) -> None:
        """Remove all listeners for an event."""
        event_name = event if isinstance(event, str) else event.__name__
        if event_name in self.listeners:
            del self.listeners[event_name]
    
    def forget_pushed(self) -> None:
        """Clear all pushed event listeners."""
        # Clear all pushed listeners that are queued for execution
        self.pushed_listeners.clear()
        self.logger.debug("Cleared all pushed event listeners")
    
    async def dispatch(self, event: Union[Event, str], payload: Optional[Dict[str, Any]] = None, halt: bool = False) -> List[Any]:
        """Dispatch an event to all listeners."""
        if isinstance(event, str):
            event_name = event
            event_obj: Event = GenericEvent(event_name, payload or {})
        else:
            event_name = event.__class__.__name__
            event_obj = event
        
        self.stats['events_dispatched'] += 1
        
        results = []
        
        # Get listeners for this event
        event_listeners = self.listeners.get(event_name, [])
        
        # Add wildcard listeners
        event_listeners.extend(self.wildcards)
        
        # Sort by priority
        event_listeners.sort(key=lambda s: s.priority)
        
        self.logger.debug(f"Dispatching event {event_name} to {len(event_listeners)} listeners")
        
        for subscription in event_listeners:
            if event_obj.propagation_stopped:
                break
            
            try:
                if subscription.should_queue:
                    await self._queue_listener(subscription, event_obj)
                    self.stats['queued_listeners'] += 1
                else:
                    result = await self._execute_listener(subscription.listener, event_obj)
                    results.append(result)
                    self.stats['listeners_executed'] += 1
                
                # Halt on first listener if requested
                if halt and result is not None:
                    break
                    
            except Exception as e:
                self.stats['failed_listeners'] += 1
                self.logger.error(f"Error executing listener for {event_name}: {e}")
                
                if subscription.halt_on_failure:
                    raise
        
        # Broadcast the event if applicable
        if self.broadcasting_enabled and hasattr(event_obj, 'should_broadcast') and event_obj.should_broadcast():
            await self._broadcast_event(event_obj)
        
        return results
    
    async def dispatch_until(self, event: Union[Event, str], payload: Optional[Dict[str, Any]] = None) -> Any:
        """Dispatch an event until the first non-null response."""
        results = await self.dispatch(event, payload, halt=True)
        return results[0] if results else None
    
    def push(self, event: Union[str, Type[Event]], listener: Union[Callable[..., Any], Type[EventListener]]) -> None:
        """Push an event listener that will be called after other listeners."""
        event_name = event if isinstance(event, str) else event.__name__
        if event_name not in self.pushed_listeners:
            self.pushed_listeners[event_name] = []
        self.pushed_listeners[event_name].append(listener)
        self.logger.debug(f"Pushed listener for event: {event_name}")
    
    def flush(self, event: str) -> None:
        """Flush a set of pushed listeners."""
        if event in self.pushed_listeners:
            # Execute all pushed listeners for this event
            listeners = self.pushed_listeners[event]
            del self.pushed_listeners[event]
            self.logger.debug(f"Flushed {len(listeners)} pushed listeners for event: {event}")
        else:
            self.logger.debug(f"No pushed listeners to flush for event: {event}")
    
    async def _execute_listener(self, listener: Union[Callable[..., Any], Type[EventListener]], event: Event) -> Any:
        """Execute a single listener."""
        if inspect.isclass(listener) and issubclass(listener, EventListener):
            # Instantiate listener class
            if self.container:
                listener_instance = self.container.make(listener.__name__)
            else:
                listener_instance = listener()
            
            return await listener_instance.handle(event)
        
        elif callable(listener):
            # Direct callable
            if asyncio.iscoroutinefunction(listener):
                return await listener(event)
            else:
                return listener(event)  # type: ignore
        
        else:
            raise ValueError(f"Invalid listener type: {type(listener)}")
    
    async def _queue_listener(self, subscription: EventSubscription, event: Event) -> None:
        """Queue a listener for background execution."""
        if self.queue_resolver:
            queue_name = subscription.queue or 'default'
            await self.queue_resolver(subscription, event, queue_name)
        else:
            self.logger.warning("Queue resolver not set, executing listener synchronously")
            await self._execute_listener(subscription.listener, event)
    
    async def _broadcast_event(self, event: Event) -> None:
        """Broadcast an event to channels."""
        if self.broadcast_manager and hasattr(event, 'broadcast_on'):
            channels = event.broadcast_on()
            data = event.broadcast_with()
            
            for channel in channels:
                try:
                    await self.broadcast_manager.broadcast(channel, data)
                except Exception as e:
                    self.logger.error(f"Failed to broadcast to channel {channel}: {e}")
    
    def set_queue_resolver(self, resolver: Callable[..., Any]) -> None:
        """Set the queue resolver for queued listeners."""
        self.queue_resolver = resolver
    
    def set_broadcast_manager(self, manager: Any) -> None:
        """Set the broadcast manager."""
        self.broadcast_manager = manager
    
    def get_listeners(self, event_name: str) -> List[EventSubscription]:
        """Get all listeners for an event."""
        return self.listeners.get(event_name, [])
    
    def has_listeners(self, event_name: str) -> bool:
        """Check if an event has listeners."""
        return event_name in self.listeners and len(self.listeners[event_name]) > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get dispatcher statistics."""
        return self.stats.copy()


class EventSubscriber(ABC):
    """Base class for event subscribers."""
    
    @abstractmethod
    def subscribe(self, dispatcher: EventDispatcher) -> None:
        """Subscribe to events."""
        # Override this method to register event listeners
        # Example:
        # dispatcher.listen('user.registered', self.handle_user_registered)
        # dispatcher.listen('user.updated', self.handle_user_updated)
        pass


class GenericEvent(Event):
    """Generic event for string-based events."""
    
    def __init__(self, name: str, data: Dict[str, Any]):
        super().__init__()
        self.name = name
        self.data = data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = super().to_dict()
        result.update(self.data)
        return result


# Common Laravel events
class ModelEvent(Event):
    """Base class for model events."""
    
    def __init__(self, model: Any):
        super().__init__()
        self.model = model


class ModelCreating(ModelEvent):
    """Event fired when a model is being created."""
    pass


class ModelCreated(ModelEvent):
    """Event fired when a model has been created."""
    pass


class ModelUpdating(ModelEvent):
    """Event fired when a model is being updated."""
    
    def __init__(self, model: Any, dirty: Dict[str, Any]):
        super().__init__(model)
        self.dirty = dirty


class ModelUpdated(ModelEvent):
    """Event fired when a model has been updated."""
    
    def __init__(self, model: Any, changes: Dict[str, Any]):
        super().__init__(model)
        self.changes = changes


class ModelDeleting(ModelEvent):
    """Event fired when a model is being deleted."""
    pass


class ModelDeleted(ModelEvent):
    """Event fired when a model has been deleted."""
    pass


# User-related events
class UserRegistered(Event, ShouldQueue):
    """Event fired when a user registers."""
    
    def __init__(self, user: Any):
        super().__init__()
        self.user = user
        self.broadcast_channels = ['users']


class UserLoggedIn(Event):
    """Event fired when a user logs in."""
    
    def __init__(self, user: Any, remember: bool = False):
        super().__init__()
        self.user = user
        self.remember = remember


class UserLoggedOut(Event):
    """Event fired when a user logs out."""
    
    def __init__(self, user: Any):
        super().__init__()
        self.user = user


# Example listeners
class SendWelcomeEmailListener(EventListener):
    """Listener to send welcome email when user registers."""
    
    async def handle(self, event: Event) -> None:
        """Send welcome email."""
        if isinstance(event, UserRegistered):
            self.logger.info(f"Sending welcome email to user: {event.user.email}")
            # Implementation would send actual email
            await asyncio.sleep(0.1)  # Simulate email sending


class LogUserActivityListener(EventListener):
    """Listener to log user activity."""
    
    async def handle(self, event: Event) -> None:
        """Log user activity."""
        if hasattr(event, 'user'):
            self.logger.info(f"User activity: {event.__class__.__name__} for user {event.user.id}")


# Example subscriber
class UserSubscriber(EventSubscriber):
    """Subscriber for user-related events."""
    
    def subscribe(self, dispatcher: EventDispatcher) -> None:
        """Subscribe to user events."""
        dispatcher.listen(UserRegistered, SendWelcomeEmailListener)
        dispatcher.listen(UserLoggedIn, LogUserActivityListener)
        dispatcher.listen(UserLoggedOut, LogUserActivityListener)


# Testing utilities
class EventFake:
    """Fake event dispatcher for testing."""
    
    def __init__(self) -> None:
        self.dispatched_events: List[Event] = []
        self.listened_events: Dict[str, List[Callable[..., Any]]] = {}
    
    async def dispatch(self, event: Union[Event, str], payload: Optional[Dict[str, Any]] = None, halt: bool = False) -> List[Any]:
        """Fake dispatch that records events."""
        if isinstance(event, str):
            event = GenericEvent(event, payload or {})
        
        self.dispatched_events.append(event)
        return []
    
    def assert_dispatched(self, event_class: Type[Event], count: Optional[int] = None) -> None:
        """Assert that an event was dispatched."""
        dispatched = [e for e in self.dispatched_events if isinstance(e, event_class)]
        
        if count is not None:
            assert len(dispatched) == count, f"Expected {count} {event_class.__name__} events, got {len(dispatched)}"
        else:
            assert len(dispatched) > 0, f"Expected {event_class.__name__} event to be dispatched"
    
    def assert_not_dispatched(self, event_class: Type[Event]) -> None:
        """Assert that an event was not dispatched."""
        dispatched = [e for e in self.dispatched_events if isinstance(e, event_class)]
        assert len(dispatched) == 0, f"Expected {event_class.__name__} event not to be dispatched"


def create_event_dispatcher(container: Optional[ServiceContainer] = None) -> EventDispatcher:
    """Create a configured event dispatcher."""
    dispatcher = EventDispatcher(container)
    
    # Register common subscribers
    user_subscriber = UserSubscriber()
    user_subscriber.subscribe(dispatcher)
    
    return dispatcher


# Context manager for testing
@asynccontextmanager
async def fake_events() -> Any:
    """Context manager for faking events in tests."""
    fake = EventFake()
    # In a real implementation, you'd replace the global dispatcher
    yield fake