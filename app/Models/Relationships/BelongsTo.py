from __future__ import annotations

from typing import Any, Optional, Type, TYPE_CHECKING, Generic, TypeVar
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel

T = TypeVar('T', bound='BaseModel')


class BelongsToRelation(Generic[T]):
    """Laravel-style BelongsTo relationship implementation"""
    
    def __init__(
        self, 
        child_model: BaseModel,
        related_model: Type[T],
        foreign_key: str,
        owner_key: str = 'id'
    ):
        self.child_model = child_model
        self.related_model = related_model
        self.foreign_key = foreign_key
        self.owner_key = owner_key
    
    def get(self, session: Session) -> Optional[T]:
        """Get the related parent model"""
        foreign_key_value = getattr(self.child_model, self.foreign_key)
        
        if not foreign_key_value:
            return None
        
        return session.query(self.related_model).filter(
            getattr(self.related_model, self.owner_key) == foreign_key_value
        ).first()
    
    def associate(self, session: Session, model: T) -> T:
        """Associate this model with a parent model"""
        parent_key_value = getattr(model, self.owner_key)
        setattr(self.child_model, self.foreign_key, parent_key_value)
        
        session.add(self.child_model)
        session.commit()
        session.refresh(self.child_model)
        
        return model
    
    def dissociate(self, session: Session) -> None:
        """Remove the association with the parent model"""
        setattr(self.child_model, self.foreign_key, None)
        
        session.add(self.child_model)
        session.commit()
        session.refresh(self.child_model)
    
    def is_associated(self) -> bool:
        """Check if this model is associated with a parent"""
        return getattr(self.child_model, self.foreign_key) is not None
    
    def get_foreign_key(self) -> Any:
        """Get the foreign key value"""
        return getattr(self.child_model, self.foreign_key)
    
    def set_foreign_key(self, session: Session, value: Any) -> None:
        """Set the foreign key value"""
        setattr(self.child_model, self.foreign_key, value)
        session.add(self.child_model)
        session.commit()
        session.refresh(self.child_model)