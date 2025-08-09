from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING, Generic, TypeVar, Union, cast
from sqlalchemy.orm import Session
from sqlalchemy import Table, Column, ForeignKey, String, and_, or_, func
from sqlalchemy.sql import select, insert, delete, text

if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel

T = TypeVar('T', bound='BaseModel')


class BelongsToManyRelation(Generic[T]):
    """Laravel-style BelongsToMany (Many-to-Many) relationship implementation"""
    
    def __init__(
        self, 
        parent_model: BaseModel,
        related_model: Type[T],
        pivot_table: str,
        foreign_pivot_key: str,
        related_pivot_key: str,
        parent_key: str = 'id',
        related_key: str = 'id'
    ):
        self.parent_model = parent_model
        self.related_model = related_model
        self.pivot_table = pivot_table
        self.foreign_pivot_key = foreign_pivot_key
        self.related_pivot_key = related_pivot_key
        self.parent_key = parent_key
        self.related_key = related_key
    
    def get(self, session: Session) -> List[T]:
        """Get all related models through pivot table"""
        parent_key_value = getattr(self.parent_model, self.parent_key)
        
        # Query related models through pivot table
        result = session.execute(
            select(self.related_model).join(
                text(self.pivot_table),
                getattr(self.related_model, self.related_key) == text(f"{self.pivot_table}.{self.related_pivot_key}")
            ).where(
                text(f"{self.pivot_table}.{self.foreign_pivot_key}") == parent_key_value
            )
        )
        
        return list(result.scalars().all())
    
    def attach(self, session: Session, model_ids: Union[List[Any], Any], pivot_data: Optional[Dict[str, Any]] = None) -> None:
        """Attach models to the relationship through pivot table"""
        parent_key_value = getattr(self.parent_model, self.parent_key)
        
        if not isinstance(model_ids, list):
            model_ids = [model_ids]
        
        for model_id in model_ids:
            pivot_record = {
                self.foreign_pivot_key: parent_key_value,
                self.related_pivot_key: model_id
            }
            
            if pivot_data:
                pivot_record.update(pivot_data)
            
            # Insert into pivot table
            session.execute(
                text(f"""
                    INSERT OR IGNORE INTO {self.pivot_table} 
                    ({', '.join(pivot_record.keys())}) 
                    VALUES ({', '.join([':' + key for key in pivot_record.keys()])})
                """).bindparams(**pivot_record)
            )
        
        session.commit()
    
    def detach(self, session: Session, model_ids: Optional[Union[List[Any], Any]] = None) -> None:
        """Detach models from the relationship"""
        parent_key_value = getattr(self.parent_model, self.parent_key)
        
        if model_ids is None:
            # Detach all
            session.execute(
                text(f"DELETE FROM {self.pivot_table} WHERE {self.foreign_pivot_key} = :parent_id")
                .bindparams(parent_id=parent_key_value)
            )
        else:
            if not isinstance(model_ids, list):
                model_ids = [model_ids]
            
            for model_id in model_ids:
                session.execute(
                    text(f"""
                        DELETE FROM {self.pivot_table} 
                        WHERE {self.foreign_pivot_key} = :parent_id 
                        AND {self.related_pivot_key} = :model_id
                    """).bindparams(parent_id=parent_key_value, model_id=model_id)
                )
        
        session.commit()
    
    def sync(self, session: Session, model_ids: Union[List[Any], Any], pivot_data: Optional[Dict[str, Any]] = None) -> None:
        """Sync the relationship - detach all existing and attach new"""
        self.detach(session)
        if model_ids:
            self.attach(session, model_ids, pivot_data)
    
    def toggle(self, session: Session, model_ids: Union[List[Any], Any], pivot_data: Optional[Dict[str, Any]] = None) -> None:
        """Toggle the attachment status of models"""
        if not isinstance(model_ids, list):
            model_ids = [model_ids]
        
        parent_key_value = getattr(self.parent_model, self.parent_key)
        
        for model_id in model_ids:
            # Check if already attached
            result = session.execute(
                text(f"""
                    SELECT COUNT(*) FROM {self.pivot_table} 
                    WHERE {self.foreign_pivot_key} = :parent_id 
                    AND {self.related_pivot_key} = :model_id
                """).bindparams(parent_id=parent_key_value, model_id=model_id)
            )
            
            count = result.scalar() or 0
            
            if count > 0:
                self.detach(session, [model_id])
            else:
                self.attach(session, [model_id], pivot_data)
    
    def count(self, session: Session) -> int:
        """Count related models"""
        parent_key_value = getattr(self.parent_model, self.parent_key)
        
        result = session.execute(
            text(f"SELECT COUNT(*) FROM {self.pivot_table} WHERE {self.foreign_pivot_key} = :parent_id")
            .bindparams(parent_id=parent_key_value)
        )
        
        return result.scalar() or 0
    
    def exists(self, session: Session) -> bool:
        """Check if any related models exist"""
        return self.count(session) > 0
    
    def contains(self, session: Session, model_id: Any) -> bool:
        """Check if a specific model is attached"""
        parent_key_value = getattr(self.parent_model, self.parent_key)
        
        result = session.execute(
            text(f"""
                SELECT COUNT(*) FROM {self.pivot_table} 
                WHERE {self.foreign_pivot_key} = :parent_id 
                AND {self.related_pivot_key} = :model_id
            """).bindparams(parent_id=parent_key_value, model_id=model_id)
        )
        
        return (result.scalar() or 0) > 0
    
    def with_pivot(self, session: Session, *columns: str) -> List[Any]:
        """Get related models with pivot data"""
        parent_key_value = getattr(self.parent_model, self.parent_key)
        
        # Build column selection for pivot
        pivot_columns = ', '.join([f"{self.pivot_table}.{col} as pivot_{col}" for col in columns])
        related_columns = ', '.join([f"{self.related_model.__tablename__}.*"])
        
        result = session.execute(
            text(f"""
                SELECT {related_columns}, {pivot_columns}
                FROM {self.related_model.__tablename__}
                JOIN {self.pivot_table} ON {self.related_model.__tablename__}.{self.related_key} = {self.pivot_table}.{self.related_pivot_key}
                WHERE {self.pivot_table}.{self.foreign_pivot_key} = :parent_id
            """).bindparams(parent_id=parent_key_value)
        )
        
        return list(result.fetchall())
    
    def where_pivot(self, session: Session, column: str, value: Any) -> List[T]:
        """Filter by pivot table column"""
        parent_key_value = getattr(self.parent_model, self.parent_key)
        
        result = session.execute(
            select(self.related_model).join(
                text(self.pivot_table),
                getattr(self.related_model, self.related_key) == text(f"{self.pivot_table}.{self.related_pivot_key}")
            ).where(
                text(f"{self.pivot_table}.{self.foreign_pivot_key}") == parent_key_value
            ).where(
                text(f"{self.pivot_table}.{column}") == value
            )
        )
        
        return list(result.scalars().all())