from __future__ import annotations

from typing import Any, Dict, List, Type, Optional, Callable
from abc import ABC, abstractmethod
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.Events import dispatch


class ModelObserver(ABC):
    """Laravel-style Model Observer base class."""
    
    def retrieved(self, model: Any) -> None:
        """Handle the model "retrieved" event."""
        pass
    
    def creating(self, model: Any) -> Optional[bool]:
        """Handle the model "creating" event. Return False to cancel."""
        pass
    
    def created(self, model: Any) -> None:
        """Handle the model "created" event."""
        pass
    
    def updating(self, model: Any) -> Optional[bool]:
        """Handle the model "updating" event. Return False to cancel."""
        pass
    
    def updated(self, model: Any) -> None:
        """Handle the model "updated" event."""
        pass
    
    def saving(self, model: Any) -> Optional[bool]:
        """Handle the model "saving" event. Return False to cancel."""
        pass
    
    def saved(self, model: Any) -> None:
        """Handle the model "saved" event."""
        pass
    
    def deleting(self, model: Any) -> Optional[bool]:
        """Handle the model "deleting" event. Return False to cancel."""
        pass
    
    def deleted(self, model: Any) -> None:
        """Handle the model "deleted" event."""
        pass
    
    def restoring(self, model: Any) -> Optional[bool]:
        """Handle the model "restoring" event. Return False to cancel."""
        pass
    
    def restored(self, model: Any) -> None:
        """Handle the model "restored" event."""
        pass
    
    def force_deleting(self, model: Any) -> Optional[bool]:
        """Handle the model "force deleting" event. Return False to cancel."""
        pass
    
    def force_deleted(self, model: Any) -> None:
        """Handle the model "force deleted" event."""
        pass


class ObserverRegistry:
    """Registry for model observers."""
    
    def __init__(self) -> None:
        self._observers: Dict[Type[Any], List[ModelObserver]] = {}
        self._global_observers: List[ModelObserver] = []
        self._registered_models: set[Type[Any]] = set()
    
    def observe(self, model_class: Type[Any], observer: ModelObserver) -> None:
        """Register an observer for a model."""
        if model_class not in self._observers:
            self._observers[model_class] = []
        
        self._observers[model_class].append(observer)
        
        # Register SQLAlchemy events if not already done
        if model_class not in self._registered_models:
            self._register_sqlalchemy_events(model_class)
            self._registered_models.add(model_class)
    
    def observe_global(self, observer: ModelObserver) -> None:
        """Register a global observer for all models."""
        self._global_observers.append(observer)
    
    def _register_sqlalchemy_events(self, model_class: Type[Any]) -> None:
        """Register SQLAlchemy event listeners."""
        
        @event.listens_for(model_class, 'before_insert')
        def before_insert(mapper: Any, connection: Any, target: Any) -> None:
            self._fire_event('creating', target)
            self._fire_event('saving', target)
        
        @event.listens_for(model_class, 'after_insert')
        def after_insert(mapper: Any, connection: Any, target: Any) -> None:
            self._fire_event('created', target)
            self._fire_event('saved', target)
        
        @event.listens_for(model_class, 'before_update')
        def before_update(mapper: Any, connection: Any, target: Any) -> None:
            self._fire_event('updating', target)
            self._fire_event('saving', target)
        
        @event.listens_for(model_class, 'after_update')
        def after_update(mapper: Any, connection: Any, target: Any) -> None:
            self._fire_event('updated', target)
            self._fire_event('saved', target)
        
        @event.listens_for(model_class, 'before_delete')
        def before_delete(mapper: Any, connection: Any, target: Any) -> None:
            self._fire_event('deleting', target)
        
        @event.listens_for(model_class, 'after_delete')
        def after_delete(mapper: Any, connection: Any, target: Any) -> None:
            self._fire_event('deleted', target)
    
    def _fire_event(self, event_name: str, model: Any) -> None:
        """Fire an observer event."""
        model_class = type(model)
        
        # Fire observers for this specific model
        if model_class in self._observers:
            for observer in self._observers[model_class]:
                method = getattr(observer, event_name, None)
                if method and callable(method):
                    result = method(model)
                    # If method returns False, we could cancel the operation
                    # but SQLAlchemy events don't support cancellation
        
        # Fire global observers
        for observer in self._global_observers:
            method = getattr(observer, event_name, None)
            if method and callable(method):
                method(model)


# Global observer registry
observer_registry = ObserverRegistry()


def observe(model_class: Type[Any], observer: ModelObserver) -> None:
    """Register a model observer."""
    observer_registry.observe(model_class, observer)