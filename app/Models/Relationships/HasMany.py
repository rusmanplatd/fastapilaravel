from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING, Generic, TypeVar
from sqlalchemy.orm import Session, Query, relationship, selectinload, joinedload
from sqlalchemy import select, and_, or_, func

if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel

T = TypeVar('T', bound='BaseModel')


class HasManyRelation(Generic[T]):
    """Laravel-style HasMany relationship implementation"""
    
    def __init__(
        self, 
        parent_model: BaseModel,
        related_model: Type[T],
        foreign_key: str,
        local_key: str = 'id'
    ):
        self.parent_model = parent_model
        self.related_model = related_model
        self.foreign_key = foreign_key
        self.local_key = local_key
    
    def get(self, session: Session) -> List[T]:
        """Get all related models"""
        parent_key_value = getattr(self.parent_model, self.local_key)
        
        return session.query(self.related_model).filter(
            getattr(self.related_model, self.foreign_key) == parent_key_value
        ).all()
    
    def where(self, session: Session, **conditions: Any) -> List[T]:
        """Filter related models with conditions"""
        parent_key_value = getattr(self.parent_model, self.local_key)
        
        query = session.query(self.related_model).filter(
            getattr(self.related_model, self.foreign_key) == parent_key_value
        )
        
        for key, value in conditions.items():
            query = query.filter(getattr(self.related_model, key) == value)
        
        return query.all()
    
    def create(self, session: Session, **attributes: Any) -> T:
        """Create a new related model"""
        parent_key_value = getattr(self.parent_model, self.local_key)
        attributes[self.foreign_key] = parent_key_value
        
        related_instance = self.related_model(**attributes)
        session.add(related_instance)
        session.commit()
        session.refresh(related_instance)
        
        return related_instance
    
    def count(self, session: Session) -> int:
        """Count related models"""
        parent_key_value = getattr(self.parent_model, self.local_key)
        
        return session.query(self.related_model).filter(
            getattr(self.related_model, self.foreign_key) == parent_key_value
        ).count()
    
    def exists(self, session: Session) -> bool:
        """Check if any related models exist"""
        return self.count(session) > 0
    
    def delete(self, session: Session) -> int:
        """Delete all related models"""
        parent_key_value = getattr(self.parent_model, self.local_key)
        
        deleted_count = session.query(self.related_model).filter(
            getattr(self.related_model, self.foreign_key) == parent_key_value
        ).delete()
        
        session.commit()
        return deleted_count
    
    def sync(self, session: Session, models: List[T]) -> None:
        """Sync related models (delete existing and add new)"""
        self.delete(session)
        
        for model in models:
            setattr(model, self.foreign_key, getattr(self.parent_model, self.local_key))
            session.add(model)
        
        session.commit()
    
    def attach(self, session: Session, model: T) -> T:
        """Attach a model to this relationship"""
        setattr(model, self.foreign_key, getattr(self.parent_model, self.local_key))
        session.add(model)
        session.commit()
        session.refresh(model)
        
        return model
    
    def detach(self, session: Session, model: T) -> T:
        """Detach a model from this relationship"""
        setattr(model, self.foreign_key, None)
        session.add(model)
        session.commit()
        session.refresh(model)
        
        return model
    
    def latest(self, session: Session, column: str = 'created_at') -> Optional[T]:
        """Get the latest related model"""
        parent_key_value = getattr(self.parent_model, self.local_key)
        
        return session.query(self.related_model).filter(
            getattr(self.related_model, self.foreign_key) == parent_key_value
        ).order_by(getattr(self.related_model, column).desc()).first()
    
    def oldest(self, session: Session, column: str = 'created_at') -> Optional[T]:
        """Get the oldest related model"""
        parent_key_value = getattr(self.parent_model, self.local_key)
        
        return session.query(self.related_model).filter(
            getattr(self.related_model, self.foreign_key) == parent_key_value
        ).order_by(getattr(self.related_model, column).asc()).first()