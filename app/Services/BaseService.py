from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError


class BaseService:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, model_class, data: Dict[str, Any]):
        try:
            instance = model_class(**data)
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def get_by_id(self, model_class, id: int):
        return self.db.query(model_class).filter(model_class.id == id).first()
    
    def get_all(self, model_class, skip: int = 0, limit: int = 100):
        return self.db.query(model_class).offset(skip).limit(limit).all()
    
    def update(self, instance, data: Dict[str, Any]):
        try:
            for key, value in data.items():
                setattr(instance, key, value)
            self.db.commit()
            self.db.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e
    
    def delete(self, instance):
        try:
            self.db.delete(instance)
            self.db.commit()
            return True
        except SQLAlchemyError as e:
            self.db.rollback()
            raise e