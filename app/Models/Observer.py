from __future__ import annotations

from typing import Any, Dict, List, Type, Optional, Callable, Coroutine
from abc import ABC, abstractmethod
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.Events import create_event_dispatcher


class ModelObserver(ABC):
    """Laravel-style Model Observer base class."""
    
    def retrieved(self, model: Any) -> None:
        """Handle the model "retrieved" event."""
        # Override this method to handle model retrieval
        # Example: self.log_retrieval(model)
        pass
    
    def creating(self, model: Any) -> Optional[bool]:
        """Handle the model "creating" event. Return False to cancel."""
        # Override this method to handle model creation
        # Return False to prevent creation
        # Example: return self.validate_creation(model)
        return True
    
    def created(self, model: Any) -> Optional[Coroutine[Any, Any, None]]:
        """Handle the model "created" event."""
        # Override this method to handle post-creation logic
        # Example: await self.send_welcome_email(model)
        pass
    
    def updating(self, model: Any) -> Optional[bool]:
        """Handle the model "updating" event. Return False to cancel."""
        # Override this method to handle model updates
        # Return False to prevent update
        # Example: return self.validate_update(model)
        return True
    
    def updated(self, model: Any) -> Optional[Coroutine[Any, Any, None]]:
        """Handle the model "updated" event."""
        # Override this method to handle post-update logic
        # Example: await self.clear_cache(model)
        pass
    
    def saving(self, model: Any) -> Optional[bool]:
        """Handle the model "saving" event. Return False to cancel."""
        # Override this method to handle pre-save logic
        # Return False to prevent save
        # Example: return self.validate_save(model)
        return True
    
    def saved(self, model: Any) -> None:
        """Handle the model "saved" event."""
        # Override this method to handle post-save logic
        # Example: self.log_save(model)
        pass
    
    def deleting(self, model: Any) -> Optional[bool]:
        """Handle the model "deleting" event. Return False to cancel."""
        # Override this method to handle pre-delete logic
        # Return False to prevent deletion
        # Example: return self.can_delete(model)
        return True
    
    def deleted(self, model: Any) -> Optional[Coroutine[Any, Any, None]]:
        """Handle the model "deleted" event."""
        # Override this method to handle post-delete logic
        # Example: await self.cleanup_related_data(model)
        pass
    
    def restoring(self, model: Any) -> Optional[bool]:
        """Handle the model "restoring" event. Return False to cancel."""
        # Override this method to handle model restoration
        # Return False to prevent restoration
        # Example: return self.can_restore(model)
        return True
    
    def restored(self, model: Any) -> None:
        """Handle the model "restored" event."""
        # Override this method to handle post-restore logic
        # Example: self.log_restoration(model)
        pass
    
    def force_deleting(self, model: Any) -> Optional[bool]:
        """Handle the model "force deleting" event. Return False to cancel."""
        # Override this method to handle permanent deletion
        # Return False to prevent force deletion
        # Example: return self.can_force_delete(model)
        return True
    
    def force_deleted(self, model: Any) -> None:
        """Handle the model "force deleted" event."""
        # Override this method to handle post-force-delete logic
        # Example: self.cleanup_permanent_deletion(model)
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