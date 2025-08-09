from __future__ import annotations

from typing import (
    Any, Dict, List, Optional, Union, Type, Generic, TypeVar, Callable, 
    Protocol, runtime_checkable, overload, Self, final, TYPE_CHECKING,
    Literal, cast, get_type_hints, ClassVar
)
from abc import ABC, abstractmethod
from enum import Enum, StrEnum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from sqlalchemy import (
    ForeignKey, Table, Column, Integer, String, DateTime, func,
    and_, or_
)
from sqlalchemy.sql import select, Select, exists
from sqlalchemy.orm import (
    relationship, Mapped, mapped_column, Session, 
    selectinload, joinedload, contains_eager, subqueryload
)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
import weakref

if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel
    from app.Utils.QueryBuilder.QueryBuilder import QueryBuilder

T = TypeVar('T', bound='BaseModel')
TRelated = TypeVar('TRelated', bound='BaseModel')


# Laravel 12 Relationship Types
class RelationshipType(StrEnum):
    """Enhanced relationship types for Laravel 12."""
    HAS_ONE = "has_one"
    HAS_MANY = "has_many"
    BELONGS_TO = "belongs_to"
    BELONGS_TO_MANY = "belongs_to_many"
    HAS_ONE_THROUGH = "has_one_through"
    HAS_MANY_THROUGH = "has_many_through"
    MORPH_ONE = "morph_one"
    MORPH_MANY = "morph_many"
    MORPH_TO = "morph_to"
    MORPH_TO_MANY = "morph_to_many"
    MORPH_BY_MANY = "morph_by_many"


# Laravel 12 Relationship Configuration
@dataclass(frozen=True)
class RelationshipConfig:
    """Configuration for Laravel 12 relationships with strict typing."""
    
    relationship_type: RelationshipType
    related_model: Union[Type['BaseModel'], str]
    foreign_key: Optional[str] = None
    local_key: Optional[str] = None
    pivot_table: Optional[str] = None
    pivot_foreign_key: Optional[str] = None
    pivot_related_key: Optional[str] = None
    through_model: Optional[Union[Type['BaseModel'], str]] = None
    morph_type: Optional[str] = None
    morph_id: Optional[str] = None
    inverse_relationship: Optional[str] = None
    as_name: Optional[str] = None
    with_timestamps: bool = False
    with_pivot: List[str] = field(default_factory=list)
    where_conditions: List[Callable[['QueryBuilder[Any]'], 'QueryBuilder[Any]']] = field(default_factory=list)
    order_by: Optional[str] = None
    order_direction: Literal['asc', 'desc'] = 'asc'


# Laravel 12 Relationship Protocols
@runtime_checkable
class RelationshipProtocol(Protocol[T, TRelated]):
    """Protocol for Laravel 12 relationships with strict typing."""
    
    def get_related(self) -> Union[TRelated, List[TRelated], None]:
        """Get the related model(s)."""
        ...
    
    def associate(self, related: TRelated) -> None:
        """Associate with related model."""
        ...
    
    def dissociate(self) -> None:
        """Dissociate from related model."""
        ...


@runtime_checkable
class HasManyRelationshipProtocol(Protocol[T, TRelated]):
    """Protocol for has-many relationships."""
    
    def create(self, **attributes: Any) -> TRelated:
        """Create and associate a new related model."""
        ...
    
    def save(self, related: TRelated) -> TRelated:
        """Save a related model."""
        ...
    
    def save_many(self, related_models: List[TRelated]) -> List[TRelated]:
        """Save multiple related models."""
        ...


@runtime_checkable
class BelongsToManyRelationshipProtocol(Protocol[T, TRelated]):
    """Protocol for many-to-many relationships."""
    
    def attach(self, related: Union[TRelated, List[TRelated]], pivot_data: Optional[Dict[str, Any]] = None) -> None:
        """Attach related models."""
        ...
    
    def detach(self, related: Optional[Union[TRelated, List[TRelated]]] = None) -> None:
        """Detach related models."""
        ...
    
    def sync(self, related: List[TRelated], detaching: bool = True) -> Dict[str, List[Any]]:
        """Sync related models."""
        ...


# Laravel 12 Relationship Base Classes
class BaseRelationship(Generic[T, TRelated], ABC):
    """Base class for Laravel 12 relationships with strict typing."""
    
    def __init__(
        self,
        parent: T,
        related_model: Type[TRelated],
        config: RelationshipConfig,
        session: Session
    ) -> None:
        self.parent = parent
        self.related_model = related_model
        self.config = config
        self.session = session
        self._query: Optional['QueryBuilder[TRelated]'] = None
        self._loaded_models: Optional[Union[TRelated, List[TRelated]]] = None
        self._is_loaded = False
    
    def __repr__(self) -> str:
        """String representation of the relationship."""
        return f"<{self.__class__.__name__}({self.parent.__class__.__name__} -> {self.related_model.__name__})>"
    
    @abstractmethod
    def get_results(self) -> Union[TRelated, List[TRelated], None]:
        """Get relationship results."""
        ...
    
    @abstractmethod
    def add_constraints(self, query: 'QueryBuilder[TRelated]') -> 'QueryBuilder[TRelated]':
        """Add relationship constraints to query."""
        ...
    
    def get_query(self) -> 'QueryBuilder[TRelated]':
        """Get the relationship query builder."""
        if self._query is None:
            from app.Utils.QueryBuilder.QueryBuilder import QueryBuilder
            self._query = QueryBuilder(self.related_model, self.session)
            self._query = self.add_constraints(self._query)
            
            # Apply custom where conditions
            for condition in self.config.where_conditions:
                self._query = condition(self._query)
            
            # Apply ordering
            if self.config.order_by:
                self._query = self._query.order_by(self.config.order_by, self.config.order_direction)
        
        return self._query
    
    def where(self, column: str, operator: str = '=', value: Any = None) -> 'QueryBuilder[TRelated]':
        """Add where constraint to relationship query."""
        return self.get_query().where(column, operator, value)
    
    def where_in(self, column: str, values: List[Any]) -> 'QueryBuilder[TRelated]':
        """Add where in constraint to relationship query."""
        return self.get_query().where_in(column, values)
    
    def order_by(self, column: str, direction: str = 'asc') -> 'QueryBuilder[TRelated]':
        """Add order by to relationship query."""
        return self.get_query().order_by(column, direction)
    
    def limit(self, count: int) -> 'QueryBuilder[TRelated]':
        """Add limit to relationship query."""
        return self.get_query().limit(count)
    
    def get_foreign_key_name(self) -> str:
        """Get the foreign key name for this relationship."""
        if self.config.foreign_key:
            return self.config.foreign_key
        
        # Default foreign key naming convention
        return f"{self.parent.__class__.__name__.lower()}_id"
    
    def get_local_key_name(self) -> str:
        """Get the local key name for this relationship."""
        if self.config.local_key:
            return self.config.local_key
        
        return getattr(self.parent, '__primary_key__', 'id')
    
    def is_loaded(self) -> bool:
        """Check if relationship is loaded."""
        return self._is_loaded
    
    def load(self) -> Union[TRelated, List[TRelated], None]:
        """Load the relationship if not already loaded."""
        if not self._is_loaded:
            self._loaded_models = self.get_results()
            self._is_loaded = True
        
        return self._loaded_models


@final
class HasOne(BaseRelationship[T, TRelated]):
    """Laravel 12 HasOne relationship with strict typing."""
    
    def get_results(self) -> Optional[TRelated]:
        """Get the related model."""
        return self.get_query().first()
    
    def add_constraints(self, query: 'QueryBuilder[TRelated]') -> 'QueryBuilder[TRelated]':
        """Add has-one constraints."""
        foreign_key = self.get_foreign_key_name()
        local_key_value = getattr(self.parent, self.get_local_key_name())
        
        return query.where(foreign_key, '=', local_key_value)
    
    def create(self, **attributes: Any) -> TRelated:
        """Create a new related model."""
        foreign_key = self.get_foreign_key_name()
        local_key_value = getattr(self.parent, self.get_local_key_name())
        
        attributes[foreign_key] = local_key_value
        related = self.related_model(**attributes)
        
        self.session.add(related)
        self.session.commit()
        
        return related
    
    def save(self, related: TRelated) -> TRelated:
        """Save a related model."""
        foreign_key = self.get_foreign_key_name()
        local_key_value = getattr(self.parent, self.get_local_key_name())
        
        setattr(related, foreign_key, local_key_value)
        
        self.session.add(related)
        self.session.commit()
        
        return related


@final
class HasMany(BaseRelationship[T, TRelated]):
    """Laravel 12 HasMany relationship with strict typing."""
    
    def get_results(self) -> List[TRelated]:
        """Get the related models."""
        return self.get_query().get()
    
    def add_constraints(self, query: 'QueryBuilder[TRelated]') -> 'QueryBuilder[TRelated]':
        """Add has-many constraints."""
        foreign_key = self.get_foreign_key_name()
        local_key_value = getattr(self.parent, self.get_local_key_name())
        
        return query.where(foreign_key, '=', local_key_value)
    
    def create(self, **attributes: Any) -> TRelated:
        """Create a new related model."""
        foreign_key = self.get_foreign_key_name()
        local_key_value = getattr(self.parent, self.get_local_key_name())
        
        attributes[foreign_key] = local_key_value
        related = self.related_model(**attributes)
        
        self.session.add(related)
        self.session.commit()
        
        return related
    
    def create_many(self, attributes_list: List[Dict[str, Any]]) -> List[TRelated]:
        """Create multiple related models."""
        foreign_key = self.get_foreign_key_name()
        local_key_value = getattr(self.parent, self.get_local_key_name())
        
        related_models = []
        for attributes in attributes_list:
            attributes[foreign_key] = local_key_value
            related = self.related_model(**attributes)
            related_models.append(related)
            self.session.add(related)
        
        self.session.commit()
        return related_models
    
    def save(self, related: TRelated) -> TRelated:
        """Save a related model."""
        foreign_key = self.get_foreign_key_name()
        local_key_value = getattr(self.parent, self.get_local_key_name())
        
        setattr(related, foreign_key, local_key_value)
        
        self.session.add(related)
        self.session.commit()
        
        return related
    
    def save_many(self, related_models: List[TRelated]) -> List[TRelated]:
        """Save multiple related models."""
        foreign_key = self.get_foreign_key_name()
        local_key_value = getattr(self.parent, self.get_local_key_name())
        
        for related in related_models:
            setattr(related, foreign_key, local_key_value)
            self.session.add(related)
        
        self.session.commit()
        return related_models


@final
class BelongsTo(BaseRelationship[T, TRelated]):
    """Laravel 12 BelongsTo relationship with strict typing."""
    
    def get_results(self) -> Optional[TRelated]:
        """Get the related model."""
        return self.get_query().first()
    
    def add_constraints(self, query: 'QueryBuilder[TRelated]') -> 'QueryBuilder[TRelated]':
        """Add belongs-to constraints."""
        foreign_key_value = getattr(self.parent, self.get_foreign_key_name())
        
        if foreign_key_value is None:
            # No related model
            return query.where('1', '=', '0')  # Impossible condition
        
        local_key = self.get_local_key_name()
        return query.where(local_key, '=', foreign_key_value)
    
    def associate(self, related: TRelated) -> None:
        """Associate with a related model."""
        local_key_value = getattr(related, self.get_local_key_name())
        setattr(self.parent, self.get_foreign_key_name(), local_key_value)
    
    def dissociate(self) -> None:
        """Dissociate from the related model."""
        setattr(self.parent, self.get_foreign_key_name(), None)


@final 
class BelongsToMany(BaseRelationship[T, TRelated]):
    """Laravel 12 BelongsToMany relationship with strict typing."""
    
    def __init__(
        self,
        parent: T,
        related_model: Type[TRelated],
        config: RelationshipConfig,
        session: Session
    ) -> None:
        super().__init__(parent, related_model, config, session)
        self._pivot_table = config.pivot_table
        self._pivot_foreign_key = config.pivot_foreign_key or f"{parent.__class__.__name__.lower()}_id"
        self._pivot_related_key = config.pivot_related_key or f"{related_model.__name__.lower()}_id"
    
    def get_results(self) -> List[TRelated]:
        """Get the related models."""
        return self.get_query().get()
    
    def add_constraints(self, query: 'QueryBuilder[TRelated]') -> 'QueryBuilder[TRelated]':
        """Add belongs-to-many constraints."""
        local_key_value = getattr(self.parent, self.get_local_key_name())
        
        # This would need a proper join implementation
        # For now, using a simplified approach
        pivot_query = select(getattr(self._get_pivot_table(), self._pivot_related_key)).where(
            getattr(self._get_pivot_table(), self._pivot_foreign_key) == local_key_value
        )
        
        related_ids = [row[0] for row in self.session.execute(pivot_query).fetchall()]
        
        if not related_ids:
            return query.where('1', '=', '0')  # No related models
        
        return query.where_in(self.get_local_key_name(), related_ids)
    
    def attach(self, related: Union[TRelated, List[TRelated]], pivot_data: Optional[Dict[str, Any]] = None) -> None:
        """Attach related models."""
        if not isinstance(related, list):
            related = [related]
        
        local_key_value = getattr(self.parent, self.get_local_key_name())
        
        for model in related:
            related_key_value = getattr(model, self.get_local_key_name())
            
            # Check if already attached
            existing = self.session.execute(
                select(self._get_pivot_table()).where(
                    and_(
                        getattr(self._get_pivot_table(), self._pivot_foreign_key) == local_key_value,
                        getattr(self._get_pivot_table(), self._pivot_related_key) == related_key_value
                    )
                )
            ).first()
            
            if not existing:
                pivot_record = {
                    self._pivot_foreign_key: local_key_value,
                    self._pivot_related_key: related_key_value
                }
                
                if pivot_data:
                    pivot_record.update(pivot_data)
                
                if self.config.with_timestamps:
                    now = datetime.now(timezone.utc)
                    pivot_record['created_at'] = now
                    pivot_record['updated_at'] = now
                
                self.session.execute(
                    self._get_pivot_table().insert().values(**pivot_record)
                )
        
        self.session.commit()
    
    def detach(self, related: Optional[Union[TRelated, List[TRelated]]] = None) -> None:
        """Detach related models."""
        local_key_value = getattr(self.parent, self.get_local_key_name())
        
        delete_query = self._get_pivot_table().delete().where(
            getattr(self._get_pivot_table(), self._pivot_foreign_key) == local_key_value
        )
        
        if related is not None:
            if not isinstance(related, list):
                related = [related]
            
            related_ids = [getattr(model, self.get_local_key_name()) for model in related]
            delete_query = delete_query.where(
                getattr(self._get_pivot_table(), self._pivot_related_key).in_(related_ids)
            )
        
        self.session.execute(delete_query)
        self.session.commit()
    
    def sync(self, related: List[TRelated], detaching: bool = True) -> Dict[str, List[Any]]:
        """Sync related models."""
        current_ids = [
            getattr(model, self.get_local_key_name()) 
            for model in self.get_results()
        ]
        
        new_ids = [getattr(model, self.get_local_key_name()) for model in related]
        
        to_attach = [model for model in related if getattr(model, self.get_local_key_name()) not in current_ids]
        to_detach = [id_val for id_val in current_ids if id_val not in new_ids] if detaching else []
        
        # Detach old relationships
        if to_detach and detaching:
            self.detach([model for model in self.get_results() if getattr(model, self.get_local_key_name()) in to_detach])
        
        # Attach new relationships
        if to_attach:
            self.attach(to_attach)
        
        return {
            'attached': [getattr(model, self.get_local_key_name()) for model in to_attach],
            'detached': to_detach,
            'updated': []
        }
    
    def _get_pivot_table(self) -> Table:
        """Get the pivot table."""
        if not self._pivot_table:
            raise ValueError("Pivot table not configured")
        
        # This would need proper table reflection or definition
        # For now, return a simplified table reference
        from sqlalchemy.schema import MetaData
        metadata = MetaData()
        return Table(self._pivot_table, metadata, autoload_with=self.session.bind)


# Laravel 12 Relationship Factory
class RelationshipFactory:
    """Factory for creating Laravel 12 relationships with strict typing."""
    
    @staticmethod
    def create_relationship(
        relationship_type: RelationshipType,
        parent: 'BaseModel',
        related_model: Type['BaseModel'],
        config: RelationshipConfig,
        session: Session
    ) -> BaseRelationship[Any, Any]:
        """Create a relationship instance."""
        
        if relationship_type == RelationshipType.HAS_ONE:
            return HasOne(parent, related_model, config, session)
        elif relationship_type == RelationshipType.HAS_MANY:
            return HasMany(parent, related_model, config, session)
        elif relationship_type == RelationshipType.BELONGS_TO:
            return BelongsTo(parent, related_model, config, session)
        elif relationship_type == RelationshipType.BELONGS_TO_MANY:
            return BelongsToMany(parent, related_model, config, session)
        else:
            raise ValueError(f"Unsupported relationship type: {relationship_type}")


# Laravel 12 Relationship Decorators
def has_one(
    related_model: Union[Type['BaseModel'], str],
    foreign_key: Optional[str] = None,
    local_key: Optional[str] = None
) -> Callable[[Type['BaseModel']], Any]:
    """Decorator for defining has-one relationships (Laravel 12)."""
    def decorator(cls: Type['BaseModel']) -> Any:
        config = RelationshipConfig(
            relationship_type=RelationshipType.HAS_ONE,
            related_model=related_model,
            foreign_key=foreign_key,
            local_key=local_key
        )
        
        # Store relationship configuration on the class
        if not hasattr(cls, '__relationships__'):
            cls.__relationships__ = {}
        
        relationship_name = f"_has_one_{len(cls.__relationships__)}"
        cls.__relationships__[relationship_name] = config
        
        return cls
    return decorator


def has_many(
    related_model: Union[Type['BaseModel'], str],
    foreign_key: Optional[str] = None,
    local_key: Optional[str] = None
) -> Callable[[Type['BaseModel']], Any]:
    """Decorator for defining has-many relationships (Laravel 12)."""
    def decorator(cls: Type['BaseModel']) -> Any:
        config = RelationshipConfig(
            relationship_type=RelationshipType.HAS_MANY,
            related_model=related_model,
            foreign_key=foreign_key,
            local_key=local_key
        )
        
        if not hasattr(cls, '__relationships__'):
            cls.__relationships__ = {}
        
        relationship_name = f"_has_many_{len(cls.__relationships__)}"
        cls.__relationships__[relationship_name] = config
        
        return cls
    return decorator


def belongs_to(
    related_model: Union[Type['BaseModel'], str],
    foreign_key: Optional[str] = None,
    local_key: Optional[str] = None
) -> Callable[[Type['BaseModel']], Any]:
    """Decorator for defining belongs-to relationships (Laravel 12)."""
    def decorator(cls: Type['BaseModel']) -> Any:
        config = RelationshipConfig(
            relationship_type=RelationshipType.BELONGS_TO,
            related_model=related_model,
            foreign_key=foreign_key,
            local_key=local_key
        )
        
        if not hasattr(cls, '__relationships__'):
            cls.__relationships__ = {}
        
        relationship_name = f"_belongs_to_{len(cls.__relationships__)}"
        cls.__relationships__[relationship_name] = config
        
        return cls
    return decorator


def belongs_to_many(
    related_model: Union[Type['BaseModel'], str],
    pivot_table: Optional[str] = None,
    foreign_key: Optional[str] = None,
    related_key: Optional[str] = None,
    with_timestamps: bool = False,
    with_pivot: Optional[List[str]] = None
) -> Callable[[Type['BaseModel']], Any]:
    """Decorator for defining many-to-many relationships (Laravel 12)."""
    def decorator(cls: Type['BaseModel']) -> Any:
        config = RelationshipConfig(
            relationship_type=RelationshipType.BELONGS_TO_MANY,
            related_model=related_model,
            pivot_table=pivot_table,
            pivot_foreign_key=foreign_key,
            pivot_related_key=related_key,
            with_timestamps=with_timestamps,
            with_pivot=with_pivot or []
        )
        
        if not hasattr(cls, '__relationships__'):
            cls.__relationships__ = {}
        
        relationship_name = f"_belongs_to_many_{len(cls.__relationships__)}"
        cls.__relationships__[relationship_name] = config
        
        return cls
    return decorator


# Export Laravel 12 relationship functionality
__all__ = [
    'RelationshipType',
    'RelationshipConfig', 
    'RelationshipProtocol',
    'HasManyRelationshipProtocol',
    'BelongsToManyRelationshipProtocol',
    'BaseRelationship',
    'HasOne',
    'HasMany',
    'BelongsTo',
    'BelongsToMany',
    'RelationshipFactory',
    'has_one',
    'has_many',
    'belongs_to',
    'belongs_to_many',
]