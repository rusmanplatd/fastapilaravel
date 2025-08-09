from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, Self, ClassVar, final, Union, TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, event, and_, or_, select, func, inspect as sa_inspect
from sqlalchemy.orm import Session, Query, declared_attr, class_mapper
from sqlalchemy.sql import Select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.inspection import inspect
import logging

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import BooleanClauseList
    from app.Models.BaseModel import BaseModel


class SoftDeletingScope:
    """
    Laravel-style soft deleting scope that automatically excludes deleted records.
    
    This scope is automatically applied to all queries on models that use SoftDeletes,
    unless explicitly overridden using withTrashed() or onlyTrashed().
    """
    
    def __init__(self) -> None:
        self.name = 'soft_deleting'
    
    def apply(self, query: Query, model_class: Type[BaseModel]) -> Query:
        """
        Apply the soft deleting scope to filter out deleted records.
        
        @param query: The SQLAlchemy query to modify
        @param model_class: The model class the query is for
        @return: Modified query excluding soft deleted records
        """
        if hasattr(model_class, 'deleted_at'):
            return query.filter(model_class.deleted_at.is_(None))
        return query
    
    def remove(self, query: Query, model_class: Type[BaseModel]) -> Query:
        """
        Remove the soft deleting scope from the query.
        
        @param query: The query to modify
        @param model_class: The model class
        @return: Query without soft delete filtering
        """
        # Remove any deleted_at is None filters
        if hasattr(query, 'whereclause') and query.whereclause is not None:
            # This is a simplified implementation
            # In a real implementation, you'd need more sophisticated filter removal
            pass
        return query


@final
class SoftDeletes:
    """
    Laravel-style SoftDeletes trait for logical deletion of records.
    
    This trait adds soft delete functionality to any model, allowing records
    to be "deleted" without actually removing them from the database.
    
    Features:
    - Automatic deleted_at timestamp column
    - Scope to exclude deleted records from queries
    - Methods to restore, force delete, and query deleted records
    - Event hooks for soft delete lifecycle
    - Cascade soft delete support
    - Batch soft delete operations
    
    Usage:
        class MyModel(BaseModel, SoftDeletes):
            pass
        
        # Soft delete
        instance.delete()  # Sets deleted_at timestamp
        
        # Query including soft deleted
        MyModel.with_trashed().all()
        
        # Query only soft deleted
        MyModel.only_trashed().all()
        
        # Restore soft deleted
        instance.restore()
        
        # Permanently delete
        instance.force_delete()
    """
    
    # Class variables for configuration
    _soft_delete_enabled: ClassVar[bool] = True
    _cascade_soft_deletes: ClassVar[bool] = True
    _soft_delete_date_format: ClassVar[str] = '%Y-%m-%d %H:%M:%S'
    _restore_callbacks: ClassVar[List[str]] = []
    _soft_delete_callbacks: ClassVar[List[str]] = []
    
    @declared_attr
    def deleted_at(cls) -> Column:
        """
        The deleted_at timestamp column for soft deletes.
        
        @return: SQLAlchemy Column for deleted_at timestamp
        """
        return Column(
            DateTime(timezone=True),
            nullable=True,
            default=None,
            index=True,  # Index for performance on soft delete queries
            doc="Soft delete timestamp - null means not deleted"
        )
    
    @hybrid_property
    def trashed(self) -> bool:
        """
        Check if the model instance is soft deleted.
        
        @return: True if soft deleted, False otherwise
        """
        return self.deleted_at is not None
    
    @trashed.expression  # type: ignore
    def trashed(cls) -> BooleanClauseList:
        """Expression version for database queries."""
        return cls.deleted_at.is_not(None)
    
    def delete(self, force: bool = False) -> bool:
        """
        Delete the model instance (soft delete by default).
        
        @param force: If True, permanently delete instead of soft delete
        @return: True if deletion was successful
        """
        if force:
            return self.force_delete()
        
        # Check if already soft deleted
        if self.trashed:
            logging.warning(f"Attempted to soft delete already deleted {self.__class__.__name__} id={self.id}")
            return False
        
        try:
            # Set deleted_at timestamp
            self.deleted_at = datetime.now(timezone.utc)
            
            # Fire soft deleting event
            self._fire_model_event('soft_deleting')
            
            # Handle cascade soft deletes
            if self._cascade_soft_deletes:
                self._cascade_soft_delete()
            
            # Save the model
            if hasattr(self, '_session') and self._session:
                self._session.flush()
            
            # Fire soft deleted event
            self._fire_model_event('soft_deleted')
            
            logging.info(f"Soft deleted {self.__class__.__name__} id={self.id}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to soft delete {self.__class__.__name__} id={self.id}: {e}")
            return False
    
    def restore(self) -> bool:
        """
        Restore a soft deleted model instance.
        
        @return: True if restore was successful
        """
        if not self.trashed:
            logging.warning(f"Attempted to restore non-deleted {self.__class__.__name__} id={self.id}")
            return False
        
        try:
            # Fire restoring event
            self._fire_model_event('restoring')
            
            # Clear deleted_at timestamp
            self.deleted_at = None
            
            # Handle cascade restores
            if self._cascade_soft_deletes:
                self._cascade_restore()
            
            # Save the model
            if hasattr(self, '_session') and self._session:
                self._session.flush()
            
            # Fire restored event
            self._fire_model_event('restored')
            
            logging.info(f"Restored {self.__class__.__name__} id={self.id}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to restore {self.__class__.__name__} id={self.id}: {e}")
            return False
    
    def force_delete(self) -> bool:
        """
        Permanently delete the model instance from the database.
        
        @return: True if permanent deletion was successful
        """
        try:
            # Fire force deleting event
            self._fire_model_event('force_deleting')
            
            # Handle cascade force deletes
            if self._cascade_soft_deletes:
                self._cascade_force_delete()
            
            # Actually delete from database
            if hasattr(self, '_session') and self._session:
                self._session.delete(self)
                self._session.flush()
            
            # Fire force deleted event
            self._fire_model_event('force_deleted')
            
            logging.info(f"Force deleted {self.__class__.__name__} id={self.id}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to force delete {self.__class__.__name__} id={self.id}: {e}")
            return False
    
    @classmethod
    def with_trashed(cls) -> Query:
        """
        Get a query builder that includes soft deleted records.
        
        @return: Query builder including soft deleted records
        """
        # This would need to be implemented in the actual query builder
        # For now, return a basic query - this needs integration with the ORM
        if hasattr(cls, '_create_query'):
            query = cls._create_query()
            # Remove the soft deleting scope
            return query.filter()  # Return unfiltered query
        raise NotImplementedError("with_trashed requires ORM query builder integration")
    
    @classmethod
    def only_trashed(cls) -> Query:
        """
        Get a query builder that only includes soft deleted records.
        
        @return: Query builder with only soft deleted records
        """
        if hasattr(cls, '_create_query'):
            query = cls._create_query()
            return query.filter(cls.deleted_at.is_not(None))
        raise NotImplementedError("only_trashed requires ORM query builder integration")
    
    @classmethod
    def without_trashed(cls) -> Query:
        """
        Get a query builder that excludes soft deleted records (default behavior).
        
        @return: Query builder excluding soft deleted records
        """
        if hasattr(cls, '_create_query'):
            query = cls._create_query()
            return query.filter(cls.deleted_at.is_(None))
        raise NotImplementedError("without_trashed requires ORM query builder integration")
    
    def get_deleted_at_column(self) -> str:
        """
        Get the name of the deleted at column.
        
        @return: Column name for deleted_at
        """
        return 'deleted_at'
    
    def get_qualified_deleted_at_column(self) -> str:
        """
        Get the qualified name of the deleted at column.
        
        @return: Table-qualified column name
        """
        return f"{self.__tablename__}.deleted_at"
    
    def _cascade_soft_delete(self) -> None:
        """
        Handle cascading soft deletes to related models.
        
        This method looks for relationships marked with cascade_delete=True
        and soft deletes related records.
        """
        if not hasattr(self, '__mapper__'):
            return
        
        try:
            mapper = class_mapper(self.__class__)
            
            for relationship in mapper.relationships:
                # Check if relationship should cascade soft deletes
                cascade_info = getattr(relationship, '_cascade', None)
                if cascade_info and 'delete' in cascade_info:
                    related_models = getattr(self, relationship.key)
                    
                    if related_models:
                        if hasattr(related_models, '__iter__'):
                            # Collection relationship
                            for related in related_models:
                                if hasattr(related, 'delete') and hasattr(related, 'deleted_at'):
                                    related.delete()
                        else:
                            # Single relationship
                            if hasattr(related_models, 'delete') and hasattr(related_models, 'deleted_at'):
                                related_models.delete()
                                
        except Exception as e:
            logging.warning(f"Error in cascade soft delete for {self.__class__.__name__}: {e}")
    
    def _cascade_restore(self) -> None:
        """
        Handle cascading restores to related models.
        
        This method looks for relationships and attempts to restore
        related records that were soft deleted with this record.
        """
        if not hasattr(self, '__mapper__'):
            return
        
        try:
            mapper = class_mapper(self.__class__)
            
            for relationship in mapper.relationships:
                # Only restore if cascade was configured
                cascade_info = getattr(relationship, '_cascade', None)
                if cascade_info and 'delete' in cascade_info:
                    # For restoration, we need to find soft deleted related records
                    # This is more complex and would need specific implementation
                    pass
                    
        except Exception as e:
            logging.warning(f"Error in cascade restore for {self.__class__.__name__}: {e}")
    
    def _cascade_force_delete(self) -> None:
        """
        Handle cascading force deletes to related models.
        
        This permanently deletes related records when force deleting.
        """
        if not hasattr(self, '__mapper__'):
            return
        
        try:
            mapper = class_mapper(self.__class__)
            
            for relationship in mapper.relationships:
                cascade_info = getattr(relationship, '_cascade', None)
                if cascade_info and 'delete' in cascade_info:
                    related_models = getattr(self, relationship.key)
                    
                    if related_models:
                        if hasattr(related_models, '__iter__'):
                            # Collection relationship
                            for related in related_models:
                                if hasattr(related, 'force_delete'):
                                    related.force_delete()
                        else:
                            # Single relationship
                            if hasattr(related_models, 'force_delete'):
                                related_models.force_delete()
                                
        except Exception as e:
            logging.warning(f"Error in cascade force delete for {self.__class__.__name__}: {e}")
    
    def _fire_model_event(self, event_name: str) -> None:
        """
        Fire model events for soft delete lifecycle.
        
        @param event_name: Name of the event to fire
        """
        try:
            # Check if the model has event firing capability
            if hasattr(self, 'fire_model_event'):
                self.fire_model_event(event_name, self)
            
            # Call registered callbacks
            callback_list = []
            if event_name in ['soft_deleting', 'soft_deleted']:
                callback_list = self._soft_delete_callbacks
            elif event_name in ['restoring', 'restored']:
                callback_list = self._restore_callbacks
            
            for callback_name in callback_list:
                if hasattr(self, callback_name):
                    callback = getattr(self, callback_name)
                    if callable(callback):
                        callback()
                        
        except Exception as e:
            logging.warning(f"Error firing {event_name} event for {self.__class__.__name__}: {e}")
    
    @classmethod
    def bootSoftDeletes(cls) -> None:
        """
        Boot the soft deletes trait for the model.
        
        This method is called when the model is initialized and sets up
        the necessary scopes and event listeners.
        """
        # Add global scope to exclude soft deleted records
        if hasattr(cls, 'add_global_scope'):
            cls.add_global_scope(SoftDeletingScope())
        
        # Register event listeners
        if hasattr(cls, '__mapper__'):
            @event.listens_for(cls, 'before_delete')
            def before_delete_listener(mapper, connection, target):
                """Prevent accidental hard deletes when soft deletes are enabled."""
                if cls._soft_delete_enabled and not getattr(target, '_force_delete', False):
                    # Instead of hard delete, do soft delete
                    target._force_delete = False
                    target.delete()
                    # Prevent the actual delete
                    return False
    
    @classmethod 
    def disable_soft_deletes(cls) -> None:
        """
        Temporarily disable soft deletes for this model class.
        """
        cls._soft_delete_enabled = False
    
    @classmethod
    def enable_soft_deletes(cls) -> None:
        """
        Re-enable soft deletes for this model class.
        """
        cls._soft_delete_enabled = True
    
    @classmethod
    def is_soft_delete_enabled(cls) -> bool:
        """
        Check if soft deletes are enabled for this model.
        
        @return: True if soft deletes are enabled
        """
        return cls._soft_delete_enabled


# Helper functions for working with soft deletes
def get_soft_deleted_models(session: Session, model_class: Type[BaseModel]) -> List[BaseModel]:
    """
    Get all soft deleted instances of a model.
    
    @param session: Database session
    @param model_class: Model class to query
    @return: List of soft deleted model instances
    """
    if not hasattr(model_class, 'deleted_at'):
        return []
    
    return session.query(model_class).filter(
        model_class.deleted_at.is_not(None)
    ).all()


def restore_all_soft_deleted(session: Session, model_class: Type[BaseModel]) -> int:
    """
    Restore all soft deleted instances of a model.
    
    @param session: Database session  
    @param model_class: Model class to restore
    @return: Number of records restored
    """
    if not hasattr(model_class, 'deleted_at'):
        return 0
    
    try:
        soft_deleted = get_soft_deleted_models(session, model_class)
        count = 0
        
        for instance in soft_deleted:
            if hasattr(instance, 'restore') and instance.restore():
                count += 1
        
        session.commit()
        return count
        
    except Exception as e:
        session.rollback()
        logging.error(f"Failed to restore soft deleted {model_class.__name__} records: {e}")
        return 0


def force_delete_all_soft_deleted(session: Session, model_class: Type[BaseModel]) -> int:
    """
    Permanently delete all soft deleted instances of a model.
    
    @param session: Database session
    @param model_class: Model class to purge
    @return: Number of records permanently deleted
    """
    if not hasattr(model_class, 'deleted_at'):
        return 0
    
    try:
        count = session.query(model_class).filter(
            model_class.deleted_at.is_not(None)
        ).count()
        
        session.query(model_class).filter(
            model_class.deleted_at.is_not(None)
        ).delete()
        
        session.commit()
        return count
        
    except Exception as e:
        session.rollback()
        logging.error(f"Failed to force delete soft deleted {model_class.__name__} records: {e}")
        return 0