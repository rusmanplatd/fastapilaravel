from __future__ import annotations

from typing import Optional, List, Dict, Any, Type, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.Models.BaseModel import BaseModel

T = TypeVar('T', bound=BaseModel)


class BaseService:
    def __init__(self, db: Session) -> None:
        self.db = db
    
    def create(self, model_class: Type[T], data: Dict[str, Any]) -> T:
        try:
            instance = model_class(**data)
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_by_id(self, model_class: Type[T], id: int) -> Optional[T]:
        return self.db.query(model_class).filter(model_class.id == id).first()
    
    def get_all(self, model_class: Type[T], skip: int = 0, limit: int = 100) -> List[T]:
        return self.db.query(model_class).offset(skip).limit(limit).all()
    
    def update(self, instance: T, data: Dict[str, Any]) -> T:
        try:
            for key, value in data.items():
                setattr(instance, key, value)
            self.db.commit()
            self.db.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete(self, instance: T) -> bool:
        try:
            self.db.delete(instance)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e