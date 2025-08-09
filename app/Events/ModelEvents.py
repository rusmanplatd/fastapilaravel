from __future__ import annotations

from typing import (
    Any, Dict, List, Optional, Union, Type, Generic, TypeVar, Callable, 
    Protocol, runtime_checkable, overload, Self, final, TYPE_CHECKING,
    Literal, ClassVar, Set, Awaitable
)
from abc import ABC, abstractmethod
from enum import Enum, StrEnum
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import inspect
import weakref
from concurrent.futures import ThreadPoolExecutor
import logging
from contextlib import contextmanager

if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel

T = TypeVar('T', bound='BaseModel')
TEvent = TypeVar('TEvent', bound='ModelEvent')


# Laravel 12 Model Event Types
class ModelEventType(StrEnum):
    """Enhanced model event types for Laravel 12."""
    RETRIEVED = "retrieved"
    CREATING = "creating"
    CREATED = "created"
    UPDATING = "updating"
    UPDATED = "updated"
    SAVING = "saving"
    SAVED = "saved"
    DELETING = "deleting"
    DELETED = "deleted"
    RESTORING = "restoring"
    RESTORED = "restored"
    REPLICATING = "replicating"
    FORCE_DELETING = "force_deleting"
    FORCE_DELETED = "force_deleted"
    # Laravel 12 enhanced events
    BOOTING = "booting"
    BOOTED = "booted"
    INITIALIZING = "initializing"
    INITIALIZED = "initialized"
    VALIDATING = "validating"
    VALIDATED = "validated"
    CACHING = "caching"
    CACHED = "cached"
    INVALIDATING = "invalidating"
    INVALIDATED = "invalidated"


# Laravel 12 Event Priority Levels
class EventPriority(Enum):
    """Event priority levels for Laravel 12."""
    HIGHEST = 1000
    HIGH = 100
    NORMAL = 0
    LOW = -100
    LOWEST = -1000


# Laravel 12 Model Event Base Class
@dataclass(frozen=True)
class ModelEvent(Generic[T]):
    """Base class for Laravel 12 model events with strict typing."""
    
    model: T
    event_type: ModelEventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: Dict[str, Any] = field(default_factory=dict)
    can_cancel: bool = False
    
    def __post_init__(self) -> None:
        """Post-initialization validation."""
        if not hasattr(self.model, '__class__'):
            raise ValueError("Event model must be a valid model instance")
    
    def get_model_type(self) -> str:
        """Get the model type name."""
        return self.model.__class__.__name__
    
    def get_model_id(self) -> Any:
        """Get the model ID if available."""
        return getattr(self.model, 'id', None)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'event_type': self.event_type,
            'model_type': self.get_model_type(),
            'model_id': self.get_model_id(),
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'can_cancel': self.can_cancel
        }


# Laravel 12 Specific Model Events
@final
@dataclass(frozen=True)
class ModelRetrieved(ModelEvent[T]):
    """Event fired when a model is retrieved from database."""
    event_type: ModelEventType = field(default=ModelEventType.RETRIEVED, init=False)
    can_cancel: bool = field(default=False, init=False)


@final
@dataclass(frozen=True)
class ModelCreating(ModelEvent[T]):
    """Event fired before a model is created."""
    event_type: ModelEventType = field(default=ModelEventType.CREATING, init=False)
    can_cancel: bool = field(default=True, init=False)


@final
@dataclass(frozen=True)
class ModelCreated(ModelEvent[T]):
    """Event fired after a model is created."""
    event_type: ModelEventType = field(default=ModelEventType.CREATED, init=False)
    can_cancel: bool = field(default=False, init=False)


@final
@dataclass(frozen=True)
class ModelUpdating(ModelEvent[T]):
    """Event fired before a model is updated."""
    event_type: ModelEventType = field(default=ModelEventType.UPDATING, init=False)
    can_cancel: bool = field(default=True, init=False)
    changes: Dict[str, Any] = field(default_factory=dict)


@final
@dataclass(frozen=True)
class ModelUpdated(ModelEvent[T]):
    """Event fired after a model is updated."""
    event_type: ModelEventType = field(default=ModelEventType.UPDATED, init=False)
    can_cancel: bool = field(default=False, init=False)
    changes: Dict[str, Any] = field(default_factory=dict)


@final
@dataclass(frozen=True)
class ModelSaving(ModelEvent[T]):
    """Event fired before a model is saved (create or update)."""
    event_type: ModelEventType = field(default=ModelEventType.SAVING, init=False)
    can_cancel: bool = field(default=True, init=False)
    is_creating: bool = False


@final
@dataclass(frozen=True)
class ModelSaved(ModelEvent[T]):
    """Event fired after a model is saved."""
    event_type: ModelEventType = field(default=ModelEventType.SAVED, init=False)
    can_cancel: bool = field(default=False, init=False)
    was_creating: bool = False


@final
@dataclass(frozen=True)
class ModelDeleting(ModelEvent[T]):
    """Event fired before a model is deleted."""
    event_type: ModelEventType = field(default=ModelEventType.DELETING, init=False)
    can_cancel: bool = field(default=True, init=False)
    is_force_delete: bool = False


@final
@dataclass(frozen=True)
class ModelDeleted(ModelEvent[T]):
    """Event fired after a model is deleted."""
    event_type: ModelEventType = field(default=ModelEventType.DELETED, init=False)
    can_cancel: bool = field(default=False, init=False)
    was_force_delete: bool = False


@final
@dataclass(frozen=True)
class ModelRestoring(ModelEvent[T]):
    """Event fired before a soft-deleted model is restored."""
    event_type: ModelEventType = field(default=ModelEventType.RESTORING, init=False)
    can_cancel: bool = field(default=True, init=False)


@final
@dataclass(frozen=True)
class ModelRestored(ModelEvent[T]):
    """Event fired after a soft-deleted model is restored."""
    event_type: ModelEventType = field(default=ModelEventType.RESTORED, init=False)
    can_cancel: bool = field(default=False, init=False)


# Laravel 12 Event Listener Protocols
@runtime_checkable
class EventListenerProtocol(Protocol[TEvent]):
    """Protocol for Laravel 12 event listeners with strict typing."""
    
    def handle(self, event: TEvent) -> Union[None, bool, Awaitable[Union[None, bool]]]:
        """Handle the event. Return False to cancel (if cancellable)."""
        ...
    
    def should_handle(self, event: TEvent) -> bool:
        """Check if this listener should handle the event."""
        return True
    
    def get_priority(self) -> EventPriority:
        """Get the priority of this listener."""
        return EventPriority.NORMAL


@runtime_checkable
class AsyncEventListenerProtocol(Protocol[TEvent]):
    """Protocol for async event listeners."""
    
    async def handle(self, event: TEvent) -> Union[None, bool]:
        """Handle the event asynchronously."""
        ...


# Laravel 12 Event Listener Registry
class EventListenerRegistry:
    """Registry for managing event listeners with Laravel 12 enhancements."""
    
    def __init__(self) -> None:
        self._listeners: Dict[ModelEventType, List[EventListenerInfo]] = {}
        self._global_listeners: List[EventListenerInfo] = []
        self._wildcard_listeners: List[EventListenerInfo] = []
        self._async_executor = ThreadPoolExecutor(max_workers=4)
        self._logger = logging.getLogger(__name__)
    
    @dataclass
    class EventListenerInfo:
        """Information about a registered event listener."""
        listener: EventListenerProtocol[Any]
        priority: EventPriority
        model_types: Optional[Set[str]] = None
        is_async: bool = False
        once: bool = False
        executed: bool = False
    
    def register(
        self,
        event_type: Union[ModelEventType, str],
        listener: EventListenerProtocol[Any],
        priority: EventPriority = EventPriority.NORMAL,
        model_types: Optional[Set[str]] = None,
        once: bool = False
    ) -> None:
        """Register an event listener."""
        if isinstance(event_type, str):
            if event_type == '*':
                self._wildcard_listeners.append(
                    self.EventListenerInfo(
                        listener=listener,
                        priority=priority,
                        model_types=model_types,
                        is_async=self._is_async_listener(listener),
                        once=once
                    )
                )
                return
            event_type = ModelEventType(event_type)
        
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        
        listener_info = self.EventListenerInfo(
            listener=listener,
            priority=priority,
            model_types=model_types,
            is_async=self._is_async_listener(listener),
            once=once
        )
        
        self._listeners[event_type].append(listener_info)
        
        # Sort by priority (highest first)
        self._listeners[event_type].sort(key=lambda x: x.priority.value, reverse=True)
    
    def unregister(self, event_type: ModelEventType, listener: EventListenerProtocol[Any]) -> None:
        """Unregister an event listener."""
        if event_type in self._listeners:
            self._listeners[event_type] = [
                info for info in self._listeners[event_type] 
                if info.listener != listener
            ]
    
    def get_listeners(self, event: ModelEvent[Any]) -> List[EventListenerInfo]:
        """Get all listeners for an event."""
        listeners = []
        
        # Get specific event type listeners
        if event.event_type in self._listeners:
            listeners.extend(self._listeners[event.event_type])
        
        # Add wildcard listeners
        listeners.extend(self._wildcard_listeners)
        
        # Filter by model type if specified
        model_type = event.get_model_type()
        filtered_listeners = []
        
        for listener_info in listeners:
            # Skip if already executed and is 'once' listener
            if listener_info.once and listener_info.executed:
                continue
            
            # Check model type filter
            if (listener_info.model_types is None or 
                model_type in listener_info.model_types):
                
                # Check if listener should handle this specific event
                if listener_info.listener.should_handle(event):
                    filtered_listeners.append(listener_info)
        
        # Sort by priority
        filtered_listeners.sort(key=lambda x: x.priority.value, reverse=True)
        
        return filtered_listeners
    
    def _is_async_listener(self, listener: EventListenerProtocol[Any]) -> bool:
        """Check if listener is async."""
        if hasattr(listener, 'handle'):
            return inspect.iscoroutinefunction(listener.handle)
        return False


# Laravel 12 Enhanced Event Dispatcher
@final
class ModelEventDispatcher:
    """Enhanced event dispatcher for Laravel 12 model events."""
    
    def __init__(self) -> None:
        self.registry = EventListenerRegistry()
        self._logger = logging.getLogger(__name__)
        self._event_history: List[ModelEvent[Any]] = []
        self._max_history = 1000
        self._dispatching = False
        self._queue_events_when_dispatching = True
        self._queued_events: List[ModelEvent[Any]] = []
    
    def listen(
        self,
        event_type: Union[ModelEventType, str],
        listener: EventListenerProtocol[Any],
        priority: EventPriority = EventPriority.NORMAL,
        model_types: Optional[Set[str]] = None,
        once: bool = False
    ) -> None:
        """Register an event listener."""
        self.registry.register(event_type, listener, priority, model_types, once)
    
    def unlisten(self, event_type: ModelEventType, listener: EventListenerProtocol[Any]) -> None:
        """Unregister an event listener."""
        self.registry.unregister(event_type, listener)
    
    def dispatch(self, event: ModelEvent[Any]) -> bool:
        """Dispatch an event to all registered listeners."""
        # Add to history
        self._add_to_history(event)
        
        # Queue events if currently dispatching to prevent recursive dispatch
        if self._dispatching and self._queue_events_when_dispatching:
            self._queued_events.append(event)
            return True
        
        try:
            self._dispatching = True
            return self._dispatch_event(event)
        finally:
            self._dispatching = False
            self._process_queued_events()
    
    def _dispatch_event(self, event: ModelEvent[Any]) -> bool:
        """Internal method to dispatch a single event."""
        listeners = self.registry.get_listeners(event)
        
        if not listeners:
            self._logger.debug(f"No listeners found for event {event.event_type}")
            return True
        
        cancelled = False
        
        for listener_info in listeners:
            try:
                # Mark as executed if 'once' listener
                if listener_info.once:
                    listener_info.executed = True
                
                # Handle async listeners
                if listener_info.is_async:
                    # Run async listener in thread pool
                    future = self.registry._async_executor.submit(
                        self._run_async_listener, listener_info.listener, event
                    )
                    result = future.result(timeout=30)  # 30 second timeout
                else:
                    # Handle sync listener
                    result = listener_info.listener.handle(event)
                
                # Check if event was cancelled
                if event.can_cancel and result is False:
                    cancelled = True
                    self._logger.info(f"Event {event.event_type} was cancelled by listener {listener_info.listener}")
                    break
                
            except Exception as e:
                self._logger.error(
                    f"Error in event listener {listener_info.listener} "
                    f"for event {event.event_type}: {e}",
                    exc_info=True
                )
                # Continue with other listeners even if one fails
        
        return not cancelled
    
    def _run_async_listener(self, listener: EventListenerProtocol[Any], event: ModelEvent[Any]) -> Union[None, bool]:
        """Run an async listener in a new event loop."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(listener.handle(event))
        finally:
            loop.close()
    
    def _process_queued_events(self) -> None:
        """Process any queued events."""
        while self._queued_events:
            queued_event = self._queued_events.pop(0)
            self._dispatch_event(queued_event)
    
    def _add_to_history(self, event: ModelEvent[Any]) -> None:
        """Add event to history."""
        self._event_history.append(event)
        
        # Trim history if it gets too large
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
    
    def get_event_history(self, limit: Optional[int] = None) -> List[ModelEvent[Any]]:
        """Get event history."""
        if limit:
            return self._event_history[-limit:]
        return self._event_history.copy()
    
    def clear_history(self) -> None:
        """Clear event history."""
        self._event_history.clear()
    
    def flush(self) -> None:
        """Flush all queued events."""
        self._process_queued_events()
    
    @contextmanager
    def halt_events(self):
        """Context manager to temporarily halt event dispatching."""
        original_value = self._queue_events_when_dispatching
        self._queue_events_when_dispatching = False
        try:
            yield
        finally:
            self._queue_events_when_dispatching = original_value


# Laravel 12 Event Listener Base Classes
class ModelEventListener(Generic[TEvent]):
    """Base class for model event listeners with Laravel 12 enhancements."""
    
    def handle(self, event: TEvent) -> Union[None, bool]:
        """Handle the event."""
        pass
    
    def should_handle(self, event: TEvent) -> bool:
        """Check if this listener should handle the event."""
        return True
    
    def get_priority(self) -> EventPriority:
        """Get the priority of this listener."""
        return EventPriority.NORMAL


class AsyncModelEventListener(Generic[TEvent]):
    """Base class for async model event listeners."""
    
    async def handle(self, event: TEvent) -> Union[None, bool]:
        """Handle the event asynchronously."""
        pass
    
    def should_handle(self, event: TEvent) -> bool:
        """Check if this listener should handle the event."""
        return True
    
    def get_priority(self) -> EventPriority:
        """Get the priority of this listener."""
        return EventPriority.NORMAL


# Laravel 12 Event Decorators
def listen_to(
    event_type: Union[ModelEventType, str],
    priority: EventPriority = EventPriority.NORMAL,
    model_types: Optional[Set[str]] = None,
    once: bool = False
) -> Callable[[Type[ModelEventListener[Any]]], Type[ModelEventListener[Any]]]:
    """Decorator for automatically registering event listeners (Laravel 12)."""
    def decorator(listener_class: Type[ModelEventListener[Any]]) -> Type[ModelEventListener[Any]]:
        # Store registration info on the class
        if not hasattr(listener_class, '__event_registrations__'):
            listener_class.__event_registrations__ = []
        
        listener_class.__event_registrations__.append({
            'event_type': event_type,
            'priority': priority,
            'model_types': model_types,
            'once': once
        })
        
        return listener_class
    return decorator


def handle_model_event(
    event_type: Union[ModelEventType, str],
    priority: EventPriority = EventPriority.NORMAL
) -> Callable[[Callable], Callable]:
    """Decorator for marking methods as event handlers (Laravel 12)."""
    def decorator(func: Callable[[Any, ModelEvent[Any]], Union[None, bool]]) -> Callable:
        if not hasattr(func, '__event_handlers__'):
            func.__event_handlers__ = []
        
        func.__event_handlers__.append({
            'event_type': event_type,
            'priority': priority
        })
        
        return func
    return decorator


# Global event dispatcher instance
_global_dispatcher: Optional[ModelEventDispatcher] = None


def get_event_dispatcher() -> ModelEventDispatcher:
    """Get the global event dispatcher instance."""
    global _global_dispatcher
    if _global_dispatcher is None:
        _global_dispatcher = ModelEventDispatcher()
    return _global_dispatcher


def set_event_dispatcher(dispatcher: ModelEventDispatcher) -> None:
    """Set the global event dispatcher instance."""
    global _global_dispatcher
    _global_dispatcher = dispatcher


# Export Laravel 12 model event functionality
__all__ = [
    'ModelEventType',
    'EventPriority',
    'ModelEvent',
    'ModelRetrieved',
    'ModelCreating',
    'ModelCreated',
    'ModelUpdating',
    'ModelUpdated',
    'ModelSaving',
    'ModelSaved',
    'ModelDeleting',
    'ModelDeleted',
    'ModelRestoring',
    'ModelRestored',
    'EventListenerProtocol',
    'AsyncEventListenerProtocol',
    'EventListenerRegistry',
    'ModelEventDispatcher',
    'ModelEventListener',
    'AsyncModelEventListener',
    'listen_to',
    'handle_model_event',
    'get_event_dispatcher',
    'set_event_dispatcher',
]