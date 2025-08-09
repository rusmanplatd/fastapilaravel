from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING, Callable, List, Union, ClassVar, Type, TypeVar, Tuple
from datetime import datetime
from sqlalchemy import String, DateTime, func, event, ForeignKey, and_, or_, Table, Column
from sqlalchemy.sql import Select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Query, Session, selectinload, joinedload, contains_eager
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from functools import wraps
from enum import Enum
import json

from app.Utils.ULIDUtils import generate_ulid, ULID

T = TypeVar('T', bound='BaseModel')

if TYPE_CHECKING:
    from database.migrations.create_users_table import User


class RelationType(Enum):
    """Relationship type enum"""
    HAS_ONE = "has_one"
    HAS_MANY = "has_many" 
    BELONGS_TO = "belongs_to"
    BELONGS_TO_MANY = "belongs_to_many"


class RelationshipDefinition:
    """Laravel-style relationship definition"""
    
    def __init__(
        self,
        relation_type: RelationType,
        related_model: str,
        foreign_key: Optional[str] = None,
        local_key: Optional[str] = None,
        pivot_table: Optional[str] = None,
        as_name: Optional[str] = None
    ):
        self.relation_type = relation_type
        self.related_model = related_model
        self.foreign_key = foreign_key
        self.local_key = local_key or 'id'
        self.pivot_table = pivot_table
        self.as_name = as_name


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True
    
    # Laravel-style hidden/fillable attributes
    __fillable__: ClassVar[List[str]] = []
    __guarded__: ClassVar[List[str]] = ['id', 'created_at', 'updated_at']
    __hidden__: ClassVar[List[str]] = []
    __visible__: ClassVar[List[str]] = []
    __casts__: ClassVar[Dict[str, str]] = {}
    __dates__: ClassVar[List[str]] = ['created_at', 'updated_at']
    __appends__: ClassVar[List[str]] = []
    
    # Laravel-style relationships definition
    __relationships__: ClassVar[Dict[str, RelationshipDefinition]] = {}
    
    id: Mapped[ULID] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    
    # Audit columns for tracking who created/updated the record
    created_by: Mapped[Optional[ULID]] = mapped_column(String(26), ForeignKey("users.id"), nullable=True)  # type: ignore[arg-type]
    updated_by: Mapped[Optional[ULID]] = mapped_column(String(26), ForeignKey("users.id"), nullable=True)  # type: ignore[arg-type]
    
    # Audit relationships
    created_by_user: Mapped[Optional[User]] = relationship(
        "User", foreign_keys=[created_by], post_update=True
    )
    updated_by_user: Mapped[Optional[User]] = relationship(
        "User", foreign_keys=[updated_by], post_update=True
    )
    
    def __init__(self, **kwargs: Any) -> None:
        if 'id' not in kwargs:
            kwargs['id'] = generate_ulid()
        super().__init__(**kwargs)


    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary, respecting hidden/visible attributes."""
        result = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        
        # Apply hidden attributes
        if self.__hidden__:
            for attr in self.__hidden__:
                result.pop(attr, None)
        
        # Apply visible attributes (if set, only show these)
        if self.__visible__:
            result = {k: v for k, v in result.items() if k in self.__visible__}
        
        # Add appended attributes
        for attr in self.__appends__:
            if hasattr(self, attr):
                result[attr] = getattr(self, attr)
        
        return result
    
    def fill(self, attributes: Dict[str, Any]) -> BaseModel:
        """Laravel-style mass assignment with fillable/guarded protection."""
        for key, value in attributes.items():
            if self._is_fillable(key):
                setattr(self, key, value)
        return self
    
    def _is_fillable(self, key: str) -> bool:
        """Check if attribute is mass assignable."""
        if self.__fillable__:
            return key in self.__fillable__
        return key not in self.__guarded__
    
    # Laravel-style Attribute Casting
    def get_attribute(self, key: str) -> Any:
        """Get attribute value with casting."""
        value = getattr(self, key, None)
        
        # Apply casting if defined
        if key in self.__casts__:
            cast_type = self.__casts__[key]
            return self._cast_attribute(value, cast_type)
        
        return value
    
    def _cast_attribute(self, value: Any, cast_type: str) -> Any:
        """Cast attribute to specified type."""
        if value is None:
            return None
        
        cast_map = {
            'json': lambda v: json.loads(v) if isinstance(v, str) else v,
            'array': lambda v: json.loads(v) if isinstance(v, str) else v,
            'boolean': lambda v: bool(v),
            'int': lambda v: int(v),
            'float': lambda v: float(v),
            'string': lambda v: str(v),
            'datetime': lambda v: datetime.fromisoformat(v) if isinstance(v, str) else v,
        }
        
        if cast_type in cast_map:
            return cast_map[cast_type](value)
        
        return value
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set attribute value with casting."""
        # Apply reverse casting if needed
        if key in self.__casts__:
            cast_type = self.__casts__[key]
            value = self._cast_attribute_for_storage(value, cast_type)
        
        setattr(self, key, value)
    
    def _cast_attribute_for_storage(self, value: Any, cast_type: str) -> Any:
        """Cast attribute for database storage."""
        if value is None:
            return None
        
        if cast_type in ['json', 'array']:
            return json.dumps(value) if not isinstance(value, str) else value
        
        return value
    
    # Laravel-style Scopes
    @classmethod
    def scope_where_not_null(cls, query: Select[Any], column: str) -> Select[Any]:
        """Laravel-style scope for non-null values."""
        return query.where(getattr(cls, column).is_not(None))
    
    @classmethod
    def scope_where_null(cls, query: Select[Any], column: str) -> Select[Any]:
        """Laravel-style scope for null values."""
        return query.where(getattr(cls, column).is_(None))
    
    @classmethod
    def scope_where_in(cls, query: Select[Any], column: str, values: List[Any]) -> Select[Any]:
        """Laravel-style scope for IN queries."""
        return query.where(getattr(cls, column).in_(values))
    
    @classmethod
    def scope_where_not_in(cls, query: Select[Any], column: str, values: List[Any]) -> Select[Any]:
        """Laravel-style scope for NOT IN queries."""
        return query.where(~getattr(cls, column).in_(values))
    
    @classmethod
    def scope_where_between(cls, query: Select[Any], column: str, start: Any, end: Any) -> Select[Any]:
        """Laravel-style scope for BETWEEN queries."""
        return query.where(getattr(cls, column).between(start, end))
    
    @classmethod
    def scope_latest(cls, query: Select[Any], column: str = 'created_at') -> Select[Any]:
        """Laravel-style scope for latest records."""
        return query.order_by(getattr(cls, column).desc())
    
    @classmethod
    def scope_oldest(cls, query: Select[Any], column: str = 'created_at') -> Select[Any]:
        """Laravel-style scope for oldest records."""
        return query.order_by(getattr(cls, column).asc())
    
    # Model relationship methods
    def touch(self) -> None:
        """Laravel-style touch method to update timestamps."""
        self.updated_at = datetime.now()
    
    def fresh(self) -> Optional[BaseModel]:
        """Laravel-style fresh method to reload from database."""
        from sqlalchemy.orm import sessionmaker
        # This would need to be implemented with actual session
        return self
    
    def refresh(self) -> BaseModel:
        """Laravel-style refresh method."""
        # This would need to be implemented with actual session
        return self
    
    # Laravel-style Relationship Methods
    @classmethod
    def has_one(cls, related_model: str, foreign_key: Optional[str] = None, local_key: Optional[str] = None) -> RelationshipDefinition:
        """Define a has-one relationship"""
        return RelationshipDefinition(
            RelationType.HAS_ONE,
            related_model,
            foreign_key or f"{cls.__tablename__}_id",
            local_key or 'id'
        )
    
    @classmethod
    def has_many(cls, related_model: str, foreign_key: Optional[str] = None, local_key: Optional[str] = None) -> RelationshipDefinition:
        """Define a has-many relationship"""
        return RelationshipDefinition(
            RelationType.HAS_MANY,
            related_model,
            foreign_key or f"{cls.__tablename__}_id",
            local_key or 'id'
        )
    
    @classmethod
    def belongs_to(cls, related_model: str, foreign_key: Optional[str] = None, local_key: Optional[str] = None) -> RelationshipDefinition:
        """Define a belongs-to relationship"""
        return RelationshipDefinition(
            RelationType.BELONGS_TO,
            related_model,
            foreign_key or f"{related_model.lower()}_id",
            local_key or 'id'
        )
    
    @classmethod
    def belongs_to_many(cls, related_model: str, pivot_table: Optional[str] = None, foreign_key: Optional[str] = None, related_key: Optional[str] = None) -> RelationshipDefinition:
        """Define a many-to-many relationship"""
        if pivot_table is None:
            # Generate pivot table name alphabetically
            table1 = cls.__tablename__
            table2 = related_model.lower() + 's'  # Assuming plural form
            pivot_table = f"{min(table1, table2)}_{max(table1, table2)}"
        
        return RelationshipDefinition(
            RelationType.BELONGS_TO_MANY,
            related_model,
            foreign_key or f"{cls.__tablename__}_id",
            related_key or f"{related_model.lower()}_id",
            pivot_table
        )
    
    def load(self, *relations: str) -> BaseModel:
        """Laravel-style eager loading (would need session implementation)"""
        # This would be implemented with actual session
        return self
    
    def with_relations(self, *relations: str) -> BaseModel:
        """Alias for load method"""
        return self.load(*relations)
    
    @classmethod
    def with_(cls, *relations: str) -> Type[BaseModel]:
        """Class method for eager loading"""
        # This would return a query builder with eager loading
        return cls
    
    # Relationship query methods
    def has(self, relation: str, operator: str = '>=', count: int = 1) -> bool:
        """Laravel-style has relationship query"""
        # This would check if the model has the specified relationship
        # Implementation would depend on session
        return True
    
    def where_has(self, relation: str, callback: Optional[Callable] = None) -> BaseModel:
        """Laravel-style where has relationship query"""
        # This would filter based on relationship existence
        return self
    
    def where_doesnt_have(self, relation: str, callback: Optional[Callable] = None) -> BaseModel:
        """Laravel-style where doesn't have relationship query"""
        # This would filter based on relationship non-existence
        return self
    
    def with_count(self, *relations: str) -> BaseModel:
        """Laravel-style with count"""
        # This would add count columns for relationships
        return self


# Event listener to generate ULID for new instances
@event.listens_for(BaseModel, 'before_insert', propagate=True)
def generate_ulid_before_insert(mapper: Any, connection: Any, target: BaseModel) -> None:
    """Generate ULID for new instances if not provided."""
    del mapper, connection  # Unused parameters required by SQLAlchemy
    if not target.id:
        target.id = generate_ulid()