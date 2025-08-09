from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING, Union
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy import event
from sqlalchemy.inspection import inspect

if TYPE_CHECKING:
    from app.Models.User import User
    from app.Models.ActivityLog import ActivityLog


@dataclass
class LogOptions:
    """Configuration options for activity logging."""
    
    # Whether to log creates/updates/deletes
    log_on_create: bool = True
    log_on_update: bool = True
    log_on_delete: bool = True
    
    # Log name for this model
    log_name: str = "default"
    
    # Attributes to log (empty means all fillable)
    log_attributes: Optional[List[str]] = None
    log_only_changed: bool = True
    
    # Custom descriptions
    description_for_event: Optional[Dict[str, str]] = None
    
    def __post_init__(self) -> None:
        """Initialize defaults after dataclass creation."""
        if self.log_attributes is None:
            self.log_attributes = []
        if self.description_for_event is None:
            self.description_for_event = {
                "created": "created",
                "updated": "updated", 
                "deleted": "deleted"
            }


class LogsActivityMixin:
    """
    Mixin class for models that should log their activity.
    Provides Laravel-style activity logging similar to Spatie Laravel Activitylog.
    """
    
    @classmethod
    def get_activity_log_options(cls) -> LogOptions:
        """
        Override this method in your model to customize logging behavior.
        
        Example:
            @classmethod
            def get_activity_log_options(cls) -> LogOptions:
                return LogOptions(
                    log_name="users",
                    log_attributes=["name", "email"],
                    description_for_event={
                        "created": "User was created",
                        "updated": "User was updated",
                        "deleted": "User was deleted"
                    }
                )
        """
        return LogOptions()
    
    def get_activity_log_attributes(self) -> Dict[str, Any]:
        """Get attributes to log for this model instance."""
        options = self.get_activity_log_options()
        
        if options.log_attributes:
            # Log only specified attributes
            return {attr: getattr(self, attr, None) for attr in options.log_attributes if hasattr(self, attr)}
        else:
            # Log all fillable attributes
            if hasattr(self, '__table__'):
                return {c.name: getattr(self, c.name, None) for c in self.__table__.columns}
            return {}
    
    def get_activity_description(self, event: str) -> str:
        """Get description for the given event."""
        options = self.get_activity_log_options()
        if options.description_for_event:
            description = options.description_for_event.get(event, event)
        else:
            description = event
        
        # Replace placeholders
        model_name = self.__class__.__name__
        return description.replace("{model}", model_name).replace("{event}", event)
    
    def log_activity(
        self, 
        description: str, 
        event: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        causer: Optional['User'] = None
    ) -> Optional['ActivityLog']:
        """
        Log an activity for this model instance.
        
        Args:
            description: Description of the activity
            event: Event type (created, updated, deleted, etc.)
            properties: Additional properties to store
            causer: User who caused this activity
        
        Returns:
            The created ActivityLog instance
        """
        from app.Models.ActivityLog import ActivityLog
        from app.Services.ActivityLogService import ActivityLogService
        
        return ActivityLogService.log_activity(
            log_name=self.get_activity_log_options().log_name,
            description=description,
            subject=self,
            event=event,
            properties=properties,
            causer=causer
        )

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Automatically set up event listeners when a model inherits from this mixin."""
        super().__init_subclass__(**kwargs)
        setup_activity_logging_events(cls)


def setup_activity_logging_events(model_class: Type[LogsActivityMixin]) -> None:
    """
    Set up SQLAlchemy event listeners for automatic activity logging.
    This function should be called for each model that uses LogsActivityMixin.
    """
    
    @event.listens_for(model_class, 'after_insert')
    def log_created(mapper: Any, connection: Any, target: LogsActivityMixin) -> None:
        """Log when a model instance is created."""
        del mapper, connection  # Unused parameters required by SQLAlchemy
        
        options = target.get_activity_log_options()
        if not options.log_on_create:
            return
            
        from app.Services.ActivityLogService import ActivityLogService
        
        # Get current user from context if available
        causer = ActivityLogService.get_current_user()
        
        properties = {
            "attributes": target.get_activity_log_attributes()
        }
        
        ActivityLogService.log_activity(
            log_name=options.log_name,
            description=target.get_activity_description("created"),
            subject=target,
            event="created",
            properties=properties,
            causer=causer
        )
    
    @event.listens_for(model_class, 'after_update')
    def log_updated(mapper: Any, connection: Any, target: LogsActivityMixin) -> None:
        """Log when a model instance is updated."""
        del mapper, connection  # Unused parameters required by SQLAlchemy
        
        options = target.get_activity_log_options()
        if not options.log_on_update:
            return
            
        from app.Services.ActivityLogService import ActivityLogService
        
        # Get current user from context if available
        causer = ActivityLogService.get_current_user()
        
        # Get changed attributes
        state = inspect(target)
        changes = {}
        old_values = {}
        
        if state and state.attrs:
            for attr in state.attrs:
                if attr.history.has_changes():
                    if attr.history.deleted:
                        old_values[attr.key] = attr.history.deleted[0]
                    changes[attr.key] = getattr(target, attr.key)
        
        if options.log_only_changed and not changes:
            return
        
        properties = {
            "attributes": target.get_activity_log_attributes(),
            "old": old_values
        }
        
        ActivityLogService.log_activity(
            log_name=options.log_name,
            description=target.get_activity_description("updated"),
            subject=target,
            event="updated",
            properties=properties,
            causer=causer
        )
    
    @event.listens_for(model_class, 'after_delete')
    def log_deleted(mapper: Any, connection: Any, target: LogsActivityMixin) -> None:
        """Log when a model instance is deleted."""
        del mapper, connection  # Unused parameters required by SQLAlchemy
        
        options = target.get_activity_log_options()
        if not options.log_on_delete:
            return
            
        from app.Services.ActivityLogService import ActivityLogService
        
        # Get current user from context if available
        causer = ActivityLogService.get_current_user()
        
        properties = {
            "attributes": target.get_activity_log_attributes()
        }
        
        ActivityLogService.log_activity(
            log_name=options.log_name,
            description=target.get_activity_description("deleted"),
            subject=target,
            event="deleted",
            properties=properties,
            causer=causer
        )


