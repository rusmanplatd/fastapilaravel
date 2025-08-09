from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any, Type, TypeVar, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.Models.BaseModel import BaseModel

T = TypeVar('T', bound=BaseModel)


class ServiceException(Exception):
    """Base exception for service-level errors."""
    pass


class ValidationException(ServiceException):
    """Exception for validation errors."""
    pass


class NotFoundException(ServiceException):
    """Exception for resource not found errors."""
    pass


class BaseService:
    """
    Base service class providing common CRUD operations with enhanced error handling.
    
    All service classes should inherit from this to get consistent error handling,
    logging, and transaction management.
    """
    
    def __init__(self, db: Session) -> None:
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create(self, model_class: Type[T], data: Dict[str, Any]) -> T:
        """Create a new model instance with validation and error handling."""
        try:
            self.logger.debug(f"Creating {model_class.__name__} with data: {data}")
            
            # Validate required fields if model has validation
            if hasattr(model_class, 'validate_data'):
                getattr(model_class, 'validate_data')(data)
            
            instance = model_class(**data)
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            
            self.logger.info(f"Successfully created {model_class.__name__} with id: {instance.id}")
            return instance
            
        except IntegrityError as e:
            self.db.rollback()
            self.logger.error(f"Integrity constraint violation creating {model_class.__name__}: {e}")
            raise ValidationException(f"Data integrity error: {str(e)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Database error creating {model_class.__name__}: {e}")
            raise ServiceException(f"Failed to create {model_class.__name__}: {str(e)}")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Unexpected error creating {model_class.__name__}: {e}")
            raise ServiceException(f"Unexpected error: {str(e)}")
    
    def get_by_id(self, model_class: Type[T], id: int) -> Optional[T]:
        """Get a model instance by ID with error handling."""
        try:
            self.logger.debug(f"Fetching {model_class.__name__} with id: {id}")
            instance = self.db.query(model_class).filter(model_class.id == id).first()
            
            if instance:
                self.logger.debug(f"Found {model_class.__name__} with id: {id}")
            else:
                self.logger.debug(f"No {model_class.__name__} found with id: {id}")
            
            return instance
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error fetching {model_class.__name__} with id {id}: {e}")
            raise ServiceException(f"Failed to fetch {model_class.__name__}: {str(e)}")
    
    def get_by_id_or_fail(self, model_class: Type[T], id: int) -> T:
        """Get a model instance by ID or raise NotFoundException."""
        instance = self.get_by_id(model_class, id)
        if not instance:
            raise NotFoundException(f"{model_class.__name__} with id {id} not found")
        return instance
    
    def get_all(self, model_class: Type[T], skip: int = 0, limit: int = 100) -> List[T]:
        """Get all model instances with pagination and error handling."""
        try:
            # Validate pagination parameters
            if skip < 0:
                raise ValidationException("Skip parameter must be non-negative")
            if limit <= 0 or limit > 1000:
                raise ValidationException("Limit must be between 1 and 1000")
            
            self.logger.debug(f"Fetching {model_class.__name__} instances (skip={skip}, limit={limit})")
            instances = self.db.query(model_class).offset(skip).limit(limit).all()
            
            self.logger.debug(f"Found {len(instances)} {model_class.__name__} instances")
            return instances
            
        except SQLAlchemyError as e:
            self.logger.error(f"Database error fetching {model_class.__name__} instances: {e}")
            raise ServiceException(f"Failed to fetch {model_class.__name__} instances: {str(e)}")
    
    def update(self, instance: T, data: Dict[str, Any]) -> T:
        """Update a model instance with validation and error handling."""
        try:
            self.logger.debug(f"Updating {instance.__class__.__name__} id {instance.id} with data: {data}")
            
            # Validate update data if model has validation
            if hasattr(instance.__class__, 'validate_update_data'):
                getattr(instance.__class__, 'validate_update_data')(data)
            
            # Track changes for logging
            changes = {}
            for key, value in data.items():
                if hasattr(instance, key):
                    old_value = getattr(instance, key)
                    if old_value != value:
                        changes[key] = {'old': old_value, 'new': value}
                        setattr(instance, key, value)
            
            if changes:
                self.db.commit()
                self.db.refresh(instance)
                self.logger.info(f"Successfully updated {instance.__class__.__name__} id {instance.id}. Changes: {changes}")
            else:
                self.logger.debug(f"No changes detected for {instance.__class__.__name__} id {instance.id}")
            
            return instance
            
        except IntegrityError as e:
            self.db.rollback()
            self.logger.error(f"Integrity constraint violation updating {instance.__class__.__name__} id {instance.id}: {e}")
            raise ValidationException(f"Data integrity error: {str(e)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Database error updating {instance.__class__.__name__} id {instance.id}: {e}")
            raise ServiceException(f"Failed to update {instance.__class__.__name__}: {str(e)}")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Unexpected error updating {instance.__class__.__name__} id {instance.id}: {e}")
            raise ServiceException(f"Unexpected error: {str(e)}")
    
    def delete(self, instance: T) -> bool:
        """Delete a model instance with error handling and logging."""
        try:
            instance_id = instance.id
            instance_class = instance.__class__.__name__
            
            self.logger.debug(f"Deleting {instance_class} id {instance_id}")
            
            self.db.delete(instance)
            self.db.commit()
            
            self.logger.info(f"Successfully deleted {instance_class} id {instance_id}")
            return True
            
        except IntegrityError as e:
            self.db.rollback()
            self.logger.error(f"Cannot delete {instance_class} id {instance_id} due to foreign key constraint: {e}")
            raise ValidationException(f"Cannot delete: {str(e)}")
        except SQLAlchemyError as e:
            self.db.rollback()
            self.logger.error(f"Database error deleting {instance_class} id {instance_id}: {e}")
            raise ServiceException(f"Failed to delete {instance_class}: {str(e)}")
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"Unexpected error deleting {instance_class} id {instance_id}: {e}")
            raise ServiceException(f"Unexpected error: {str(e)}")
    
    def count(self, model_class: Type[T]) -> int:
        """Get the total count of model instances."""
        try:
            count = self.db.query(model_class).count()
            self.logger.debug(f"Total {model_class.__name__} count: {count}")
            return count
        except SQLAlchemyError as e:
            self.logger.error(f"Database error counting {model_class.__name__} instances: {e}")
            raise ServiceException(f"Failed to count {model_class.__name__} instances: {str(e)}")
    
    def exists(self, model_class: Type[T], id: int) -> bool:
        """Check if a model instance exists by ID."""
        try:
            exists = self.db.query(model_class).filter(model_class.id == id).first() is not None
            self.logger.debug(f"{model_class.__name__} id {id} exists: {exists}")
            return exists
        except SQLAlchemyError as e:
            self.logger.error(f"Database error checking if {model_class.__name__} id {id} exists: {e}")
            raise ServiceException(f"Failed to check existence: {str(e)}")