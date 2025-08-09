from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING, Callable, List, ClassVar, Type, TypeVar, Tuple, Union, cast as type_cast, get_type_hints, Protocol, final
from datetime import datetime, date, time
from decimal import Decimal
from sqlalchemy import func, event, desc, asc, String, Integer, Boolean, DateTime, Text
from sqlalchemy.types import Date, Time, Float, JSON
from sqlalchemy.sql import select, exists, not_, Select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, validates
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.inspection import inspect as sa_inspect
from enum import Enum
import json
import uuid
from dataclasses import dataclass, field
import logging
from abc import ABC, abstractmethod

from app.Utils.ULIDUtils import generate_ulid, ULID

T = TypeVar('T', bound='BaseModel')

if TYPE_CHECKING:
    pass  # User imports handled dynamically


# Laravel 12 Strict Mode Configuration
@dataclass
class StrictConfig:
    """Laravel 12 strict mode configuration."""
    enabled: bool = False
    fail_on_mass_assignment: bool = True
    fail_on_unknown_attributes: bool = True
    validate_casts: bool = True
    prevent_lazy_loading: bool = False
    prevent_silently_discarding_attributes: bool = True
    strict_type_checking: bool = True


# Laravel 12 Enhanced Cast Types
class CastType(Enum):
    """Enhanced cast types for Laravel 12."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float" 
    BOOLEAN = "boolean"
    ARRAY = "array"
    JSON = "json"
    OBJECT = "object"
    COLLECTION = "collection"
    DATE = "date"
    DATETIME = "datetime"
    TIME = "time"
    TIMESTAMP = "timestamp"
    DECIMAL = "decimal"
    UUID = "uuid"
    ULID = "ulid"
    ENCRYPTED = "encrypted"
    HASHED = "hashed"
    ENUM = "enum"
    # Laravel 12 new casts
    IMMUTABLE_DATE = "immutable_date"
    IMMUTABLE_DATETIME = "immutable_datetime"
    AS_ARRAY_OBJECT = "AsArrayObject"
    AS_COLLECTION = "AsCollection"
    AS_ENUM_COLLECTION = "AsEnumCollection"


# Laravel 12 Cast Interface
from typing import runtime_checkable

@runtime_checkable
class CastInterface(Protocol):
    """Interface for custom casts (Laravel 12)."""
    
    def get(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> Any:
        """Transform the attribute from the underlying model values."""
        ...
    
    def set(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> Any:
        """Transform the attribute to its underlying representation."""
        ...


# Laravel 12 Built-in Custom Casts
class AsArrayObject(CastInterface):
    """Cast to array-like object (Laravel 12)."""
    
    def get(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        if value is None:
            return {}
        return json.loads(value) if isinstance(value, str) else value
    
    def set(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> str:
        return json.dumps(value) if value is not None else '{}'


class AsCollection(CastInterface):
    """Cast to Collection object (Laravel 12)."""
    
    def get(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> Any:
        from app.Support.Collection import Collection
        if value is None:
            return Collection([])
        data = json.loads(value) if isinstance(value, str) else value
        return Collection(data if isinstance(data, list) else [])
    
    def set(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> str:
        from app.Support.Collection import Collection
        if isinstance(value, Collection):
            return json.dumps(value.all())
        elif isinstance(value, list):
            return json.dumps(value)
        return json.dumps([])


class EncryptedCast(CastInterface):
    """Cast to encrypted value (Laravel 12)."""
    
    def get(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> Optional[str]:
        if value is None:
            return None
        # Implementation would use Laravel's encryption
        return value  # Placeholder - would decrypt here
    
    def set(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> Optional[str]:
        if value is None:
            return None
        # Implementation would use Laravel's encryption
        return str(value)  # Placeholder - would encrypt here


# Laravel 12 Attribute Accessors/Mutators
class AttributeAccessor:
    """Laravel 12 attribute accessor."""
    
    def __init__(self, callback: Callable[['BaseModel', Any], Any]):
        self.callback = callback
    
    def __call__(self, model: 'BaseModel', value: Any) -> Any:
        return self.callback(model, value)


class AttributeMutator:
    """Laravel 12 attribute mutator."""
    
    def __init__(self, callback: Callable[['BaseModel', Any], Any]):
        self.callback = callback
    
    def __call__(self, model: 'BaseModel', value: Any) -> Any:
        return self.callback(model, value)


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


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    
    def delete(self) -> None:
        """Soft delete the model."""
        self.deleted_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore a soft deleted model."""
        self.deleted_at = None
    
    def force_delete(self) -> None:
        """Permanently delete the model."""
        # This would need to be implemented by the actual ORM session
        pass
    
    @property
    def is_deleted(self) -> bool:
        """Check if the model is soft deleted."""
        return self.deleted_at is not None


class TimestampMixin:
    """Mixin for automatic timestamps."""
    
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class BaseModel(Base, TimestampMixin):
    __abstract__ = True
    
    # Laravel 12 strict mode configuration
    __strict_config__: ClassVar[StrictConfig] = StrictConfig()
    
    # Laravel-style hidden/fillable attributes
    __fillable__: ClassVar[List[str]] = []
    __guarded__: ClassVar[List[str]] = ['id', 'created_at', 'updated_at']
    __hidden__: ClassVar[List[str]] = []
    __visible__: ClassVar[List[str]] = []
    __casts__: ClassVar[Dict[str, Union[str, Type[CastInterface], CastInterface]]] = {}
    __dates__: ClassVar[List[str]] = ['created_at', 'updated_at']
    __appends__: ClassVar[List[str]] = []
    
    # Laravel 12 enhanced attributes
    __accessors__: ClassVar[Dict[str, AttributeAccessor]] = {}
    __mutators__: ClassVar[Dict[str, AttributeMutator]] = {}
    __serializable__: ClassVar[List[str]] = []
    __read_only__: ClassVar[List[str]] = ['id', 'created_at']
    __with_default__: ClassVar[List[str]] = []
    
    # Laravel-style relationships definition
    __relationships__: ClassVar[Dict[str, RelationshipDefinition]] = {}
    
    # Laravel-style observers
    __observers__: ClassVar[List[str]] = []
    
    # Query builder attribute
    _query: Optional[Select[Any]]
    
    # Laravel-style soft deletes
    __soft_deletes__: ClassVar[bool] = False
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Laravel-style global scopes
    __global_scopes__: ClassVar[Dict[str, Callable[[Select[Any]], Select[Any]]]] = {}
    
    # Laravel 12 internal tracking
    _original_attributes: Dict[str, Any]
    _dirty_attributes: Dict[str, Any]
    _exists: bool
    _was_recently_created: bool
    _changes: Dict[str, Tuple[Any, Any]]  # old_value, new_value
    
    id: Mapped[ULID] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    
    # Audit columns for tracking who created/updated the record
    created_by: Mapped[Optional[ULID]] = mapped_column(nullable=True)
    updated_by: Mapped[Optional[ULID]] = mapped_column(nullable=True)
    
    # Audit relationships
    created_by_user: Mapped[Optional[Any]] = relationship(
        "User", foreign_keys=[created_by], post_update=True
    )
    updated_by_user: Mapped[Optional[Any]] = relationship(
        "User", foreign_keys=[updated_by], post_update=True
    )
    
    def __init__(self, **kwargs: Any) -> None:
        # Initialize tracking attributes
        self._original_attributes = {}
        self._dirty_attributes = {}
        self._exists = False
        self._was_recently_created = True
        self._changes = {}
        
        if 'id' not in kwargs:
            kwargs['id'] = generate_ulid()
        
        # Laravel 12 strict mode validation
        if self.__strict_config__.enabled and self.__strict_config__.fail_on_unknown_attributes:
            self._validate_attributes(kwargs)
        
        # Apply mutators before setting attributes
        kwargs = self._apply_mutators_to_kwargs(kwargs)
        
        super().__init__(**kwargs)
        
        # Store original values for change tracking
        self._sync_original()
    
    def _validate_attributes(self, attributes: Dict[str, Any]) -> None:
        """Validate attributes in strict mode (Laravel 12)."""
        valid_attributes = {col.name for col in self.__table__.columns}
        valid_attributes.update(self.__appends__)
        
        for key in attributes:
            if key not in valid_attributes:
                if self.__strict_config__.fail_on_unknown_attributes:
                    raise ValueError(f"Unknown attribute '{key}' for {self.__class__.__name__}")
    
    def _apply_mutators_to_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply mutators to kwargs (Laravel 12)."""
        result = kwargs.copy()
        for key, value in kwargs.items():
            if key in self.__mutators__:
                mutator = self.__mutators__[key]
                result[key] = mutator(self, value)
        return result
    
    def _sync_original(self) -> None:
        """Sync original attributes for change tracking (Laravel 12)."""
        self._original_attributes = {}
        for column in self.__table__.columns:
            if hasattr(self, column.name):
                self._original_attributes[column.name] = getattr(self, column.name)
        self._dirty_attributes = {}
        self._changes = {}


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
    
    # Laravel 12 Enhanced Attribute Casting
    def get_attribute(self, key: str) -> Any:
        """Get attribute value with enhanced casting and accessors (Laravel 12)."""
        # Check for accessor
        if key in self.__accessors__:
            accessor = self.__accessors__[key]
            raw_value = getattr(self, key, None)
            return accessor(self, raw_value)
        
        value = getattr(self, key, None)
        
        # Apply casting if defined
        if key in self.__casts__:
            cast_type = self.__casts__[key]
            return self._cast_attribute(value, cast_type, key)
        
        return value
    
    def _cast_attribute(self, value: Any, cast_type: Union[str, Type[CastInterface], CastInterface], key: str) -> Any:
        """Enhanced cast attribute with custom casts (Laravel 12)."""
        if value is None:
            return None
        
        # Handle custom cast interfaces
        if isinstance(cast_type, CastInterface):
            return cast_type.get(self, key, value, self.to_dict())
        elif isinstance(cast_type, type) and issubclass(cast_type, CastInterface):
            cast_instance = cast_type()
            return cast_instance.get(self, key, value, self.to_dict())
        elif isinstance(cast_type, str):
            # Handle string cast types
            return self._cast_built_in_type(value, cast_type)
        else:
            # Fallback for unknown cast types
            return value  # type: ignore
    
    def _cast_built_in_type(self, value: Any, cast_type: str) -> Any:
        """Cast to built-in types (Laravel 12 enhanced)."""
        cast_map: Dict[str, Callable[[Any], Any]] = {
            'string': lambda v: str(v) if v is not None else None,
            'integer': lambda v: int(v) if v is not None else None,
            'float': lambda v: float(v) if v is not None else None,
            'boolean': lambda v: bool(v) if v is not None else None,
            'json': lambda v: json.loads(v) if isinstance(v, str) else v,
            'array': lambda v: json.loads(v) if isinstance(v, str) else v,
            'object': lambda v: json.loads(v) if isinstance(v, str) else v,
            'collection': self._cast_to_collection,
            'date': lambda v: datetime.fromisoformat(v).date() if isinstance(v, str) else v,
            'datetime': lambda v: datetime.fromisoformat(v) if isinstance(v, str) else v,
            'time': lambda v: datetime.fromisoformat(v).time() if isinstance(v, str) else v,
            'timestamp': lambda v: datetime.fromtimestamp(v) if isinstance(v, (int, float)) else v,
            'decimal': lambda v: Decimal(str(v)) if v is not None else None,
            'uuid': lambda v: uuid.UUID(v) if isinstance(v, str) else v,
            'ulid': lambda v: ULID(v) if isinstance(v, str) else v,
            # Laravel 12 immutable casts
            'immutable_date': lambda v: datetime.fromisoformat(v).date() if isinstance(v, str) else v,
            'immutable_datetime': lambda v: datetime.fromisoformat(v) if isinstance(v, str) else v,
        }
        
        if cast_type in cast_map:
            cast_func = cast_map.get(cast_type)
            if cast_func is not None:
                try:
                    return cast_func(value)
                except (ValueError, TypeError) as e:
                    if self.__strict_config__.enabled and self.__strict_config__.validate_casts:
                        raise ValueError(f"Failed to cast '{value}' to {cast_type}: {e}")
                    return value
        
        return value
    
    def _cast_to_collection(self, value: Any) -> Any:
        """Cast to Collection object."""
        from app.Support.Collection import Collection
        if isinstance(value, str):
            try:
                data = json.loads(value)
                return Collection(data if isinstance(data, list) else [])
            except json.JSONDecodeError:
                return Collection([])
        elif isinstance(value, list):
            return Collection(value)
        return Collection([])
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Enhanced set attribute with mutators and strict mode (Laravel 12)."""
        # Check read-only attributes
        if key in self.__read_only__ and self._exists:
            if self.__strict_config__.enabled:
                raise ValueError(f"Attribute '{key}' is read-only")
            return
        
        # Apply mutator if defined
        if key in self.__mutators__:
            mutator = self.__mutators__[key]
            value = mutator(self, value)
        
        # Track changes
        old_value = getattr(self, key, None) if hasattr(self, key) else None
        
        # Apply reverse casting if needed
        if key in self.__casts__:
            cast_type = self.__casts__[key]
            value = self._cast_attribute_for_storage(value, cast_type, key)
        
        # Set the attribute
        setattr(self, key, value)
        
        # Track dirty state
        if key in self._original_attributes:
            if self._original_attributes[key] != value:
                self._dirty_attributes[key] = value
                self._changes[key] = (old_value, value)
            elif key in self._dirty_attributes:
                # Value was changed back to original
                del self._dirty_attributes[key]
                if key in self._changes:
                    del self._changes[key]
    
    def _cast_attribute_for_storage(self, value: Any, cast_type: Union[str, Type[CastInterface], CastInterface], key: str) -> Any:
        """Enhanced cast attribute for storage (Laravel 12)."""
        if value is None:
            return None
        
        # Handle custom cast interfaces
        if isinstance(cast_type, CastInterface):
            return cast_type.set(self, key, value, self.to_dict())
        elif isinstance(cast_type, type) and issubclass(cast_type, CastInterface):
            cast_instance = cast_type()
            return cast_instance.set(self, key, value, self.to_dict())
        elif isinstance(cast_type, str):
            # Handle string cast types
            return self._cast_for_storage_built_in(value, cast_type)
        else:
            # Fallback for unknown cast types
            return value  # type: ignore
    
    def _cast_for_storage_built_in(self, value: Any, cast_type: str) -> Any:
        """Cast for storage to built-in types."""
        if cast_type in ['json', 'array', 'object']:
            return json.dumps(value) if not isinstance(value, str) else value
        elif cast_type == 'collection':
            from app.Support.Collection import Collection
            if isinstance(value, Collection):
                return json.dumps(value.all())
            elif isinstance(value, list):
                return json.dumps(value)
            return json.dumps([])
        elif cast_type in ['date', 'datetime', 'time', 'immutable_date', 'immutable_datetime']:
            return value.isoformat() if hasattr(value, 'isoformat') else str(value)
        elif cast_type == 'decimal':
            return str(value) if isinstance(value, Decimal) else value
        elif cast_type in ['uuid', 'ulid']:
            return str(value)
        
        return value
    
    # Laravel 12 Accessor/Mutator decorators
    @classmethod
    def accessor(cls, attribute: str) -> Callable[[Callable[['BaseModel', Any], Any]], Callable[['BaseModel', Any], Any]]:
        """Decorator for defining attribute accessors (Laravel 12)."""
        def decorator(func: Callable[['BaseModel', Any], Any]) -> Callable[['BaseModel', Any], Any]:
            cls.__accessors__[attribute] = AttributeAccessor(func)
            return func
        return decorator
    
    @classmethod
    def mutator(cls, attribute: str) -> Callable[[Callable[['BaseModel', Any], Any]], Callable[['BaseModel', Any], Any]]:
        """Decorator for defining attribute mutators (Laravel 12)."""
        def decorator(func: Callable[['BaseModel', Any], Any]) -> Callable[['BaseModel', Any], Any]:
            cls.__mutators__[attribute] = AttributeMutator(func)
            return func
        return decorator
    
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
        return query.order_by(desc(getattr(cls, column)))
    
    @classmethod
    def scope_oldest(cls, query: Select[Any], column: str = 'created_at') -> Select[Any]:
        """Laravel-style scope for oldest records."""
        return query.order_by(asc(getattr(cls, column)))
    
    @classmethod
    def scope_active(cls, query: Select[Any]) -> Select[Any]:
        """Laravel-style scope for active records."""
        if hasattr(cls, 'is_active'):
            return query.where(getattr(cls, 'is_active') == True)
        return query
    
    @classmethod
    def scope_inactive(cls, query: Select[Any]) -> Select[Any]:
        """Laravel-style scope for inactive records."""
        if hasattr(cls, 'is_active'):
            return query.where(getattr(cls, 'is_active') == False)
        return query
    
    @classmethod
    def scope_with_trashed(cls, query: Select[Any]) -> Select[Any]:
        """Laravel-style scope to include soft deleted records."""
        # Remove the global soft delete scope if it exists
        return query
    
    @classmethod
    def scope_only_trashed(cls, query: Select[Any]) -> Select[Any]:
        """Laravel-style scope for only soft deleted records."""
        if cls.__soft_deletes__:
            return query.where(getattr(cls, 'deleted_at').is_not(None))
        return query
    
    @classmethod
    def scope_without_trashed(cls, query: Select[Any]) -> Select[Any]:
        """Laravel-style scope to exclude soft deleted records."""
        if cls.__soft_deletes__:
            return query.where(getattr(cls, 'deleted_at').is_(None))
        return query
    
    # Model relationship methods
    def touch(self) -> None:
        """Laravel-style touch method to update timestamps."""
        self.updated_at = datetime.now()
    
    def fresh(self, session: Optional[Session] = None) -> Optional[BaseModel]:
        """Laravel-style fresh method to reload from database."""
        if session is None:
            return self  # Would need session management
        return session.get(self.__class__, self.id)
    
    def refresh(self, session: Optional[Session] = None) -> BaseModel:
        """Laravel-style refresh method."""
        if session is not None:
            session.refresh(self)
        return self
    
    def save(self, session: Optional[Session] = None) -> BaseModel:
        """Laravel-style save method."""
        if session is not None:
            session.add(self)
            session.commit()
        return self
    
    def delete(self, session: Optional[Session] = None) -> bool:
        """Laravel-style delete method."""
        if self.__soft_deletes__:
            self.deleted_at = datetime.now()
            return self.save(session) is not None
        else:
            if session is not None:
                session.delete(self)
                session.commit()
                return True
        return False
    
    def force_delete(self, session: Optional[Session] = None) -> bool:
        """Laravel-style force delete (bypass soft deletes)."""
        if session is not None:
            session.delete(self)
            session.commit()
            return True
        return False
    
    def restore(self, session: Optional[Session] = None) -> BaseModel:
        """Laravel-style restore soft deleted record."""
        if self.__soft_deletes__:
            self.deleted_at = None
            self.save(session)
        return self
    
    def is_soft_deleted(self) -> bool:
        """Check if the model is soft deleted."""
        return self.__soft_deletes__ and self.deleted_at is not None
    
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
    
    def where_has(self, relation: str, callback: Optional[Callable[..., Any]] = None) -> BaseModel:
        """Laravel-style where has relationship query"""
        from sqlalchemy.orm import aliased
        
        if not hasattr(self.__class__, relation):
            raise AttributeError(f"Relationship '{relation}' not found on {self.__class__.__name__}")
        
        relationship_attr = getattr(self.__class__, relation)
        related_class = relationship_attr.property.mapper.class_
        
        # Initialize _query if not set
        if not hasattr(self, '_query') or self._query is None:
            self._query = select(self.__class__)
        
        if callback:
            # Create subquery with callback conditions
            subquery = callback(related_class.query).subquery()
            assert self._query is not None  # Type assertion
            self._query = self._query.filter(
                exists().where(subquery.c.id == self.__class__.id)
            )
        else:
            # Simple existence check
            assert self._query is not None  # Type assertion
            self._query = self._query.filter(
                exists().where(related_class.query.filter(
                    getattr(related_class, self._get_foreign_key(relation)) == self.__class__.id
                ).exists())
            )
        
        return self
    
    def where_doesnt_have(self, relation: str, callback: Optional[Callable[..., Any]] = None) -> BaseModel:
        """Laravel-style where doesn't have relationship query"""
        from sqlalchemy.orm import aliased
        
        if not hasattr(self.__class__, relation):
            raise AttributeError(f"Relationship '{relation}' not found on {self.__class__.__name__}")
        
        relationship_attr = getattr(self.__class__, relation)
        related_class = relationship_attr.property.mapper.class_
        
        # Initialize _query if not set
        if not hasattr(self, '_query') or self._query is None:
            self._query = select(self.__class__)
        
        if callback:
            # Create subquery with callback conditions
            subquery = callback(related_class.query).subquery()
            assert self._query is not None  # Type assertion
            self._query = self._query.filter(
                not_(exists().where(subquery.c.id == self.__class__.id))
            )
        else:
            # Simple non-existence check
            assert self._query is not None  # Type assertion
            self._query = self._query.filter(
                not_(exists().where(related_class.query.filter(
                    getattr(related_class, self._get_foreign_key(relation)) == self.__class__.id
                ).exists()))
            )
        
        return self
    
    def _get_foreign_key(self, relation: str) -> str:
        """Get foreign key name for relationship"""
        # This is a simplified implementation - in practice this would
        # inspect the relationship configuration to determine the correct foreign key
        relationship_attr = getattr(self.__class__, relation)
        
        if hasattr(relationship_attr.property, 'local_columns'):
            # For many-to-one relationships
            local_column = next(iter(relationship_attr.property.local_columns))
            return local_column.name
        elif hasattr(relationship_attr.property, 'remote_side'):
            # For one-to-many relationships
            remote_column = next(iter(relationship_attr.property.remote_side))
            return remote_column.name
        else:
            # Default convention: {model_name}_id
            return f"{self.__class__.__name__.lower()}_id"
    
    def with_count(self, *relations: str) -> BaseModel:
        """Laravel-style with count"""
        from sqlalchemy import func
        from sqlalchemy.sql import select, Select
        from sqlalchemy.orm import aliased
        
        # Initialize _query if not set
        if not hasattr(self, '_query'):
            setattr(self, '_query', select(self.__class__))
        
        for relation in relations:
            if not hasattr(self.__class__, relation):
                raise AttributeError(f"Relationship '{relation}' not found on {self.__class__.__name__}")
            
            relationship_attr = getattr(self.__class__, relation)
            related_class = relationship_attr.property.mapper.class_
            
            # Create count subquery
            count_alias = f"{relation}_count"
            foreign_key = self._get_foreign_key(relation)
            
            count_subquery = select(func.count(getattr(related_class, 'id'))).where(
                getattr(related_class, foreign_key) == self.__class__.id
            ).scalar_subquery()
            
            # Add count column to query
            if self._query is not None:
                self._query = self._query.add_columns(count_subquery.label(count_alias))
        
        return self
    
    @classmethod
    def find(cls, id_value: Any, session: Optional[Session] = None) -> Optional[BaseModel]:
        """Laravel-style find method."""
        if session is None:
            return None  # Would need session management
        return session.get(cls, id_value)
    
    @classmethod
    def find_or_fail(cls, id_value: Any, session: Optional[Session] = None) -> BaseModel:
        """Laravel-style find or fail method."""
        result = cls.find(id_value, session)
        if result is None:
            raise ValueError(f"{cls.__name__} with id {id_value} not found")
        return result
    
    @classmethod
    def first_or_create(cls, attributes: Dict[str, Any], session: Optional[Session] = None) -> Tuple[BaseModel, bool]:
        """Laravel-style first or create method."""
        if session is None:
            # Would need session management
            instance = cls(**attributes)
            return instance, True
        
        # Try to find existing
        query = session.query(cls)
        for key, value in attributes.items():
            query = query.filter(getattr(cls, key) == value)
        
        existing = query.first()
        if existing:
            return existing, False
        
        # Create new
        instance = cls(**attributes)
        session.add(instance)
        session.commit()
        return instance, True
    
    @classmethod
    def first_or_new(cls, attributes: Dict[str, Any], session: Optional[Session] = None) -> Tuple[BaseModel, bool]:
        """Laravel-style first or new method."""
        if session is None:
            instance = cls(**attributes)
            return instance, True
        
        # Try to find existing
        query = session.query(cls)
        for key, value in attributes.items():
            query = query.filter(getattr(cls, key) == value)
        
        existing = query.first()
        if existing:
            return existing, False
        
        # Create new (but don't save)
        instance = cls(**attributes)
        return instance, True
    
    @classmethod
    def update_or_create(cls, attributes: Dict[str, Any], values: Optional[Dict[str, Any]] = None, session: Optional[Session] = None) -> Tuple[BaseModel, bool]:
        """Laravel-style update or create method."""
        if values is None:
            values = {}
        
        if session is None:
            instance = cls(**{**attributes, **values})
            return instance, True
        
        # Try to find existing
        query = session.query(cls)
        for key, value in attributes.items():
            query = query.filter(getattr(cls, key) == value)
        
        existing = query.first()
        if existing:
            # Update existing
            for key, value in values.items():
                setattr(existing, key, value)
            session.commit()
            return existing, False
        
        # Create new
        instance = cls(**{**attributes, **values})
        session.add(instance)
        session.commit()
        return instance, True
    
    def replicate(self, except_columns: Optional[List[str]] = None) -> BaseModel:
        """Laravel-style replicate method."""
        if except_columns is None:
            except_columns = ['id', 'created_at', 'updated_at']
        
        attributes = {}
        for column in self.__table__.columns:
            if column.name not in except_columns:
                attributes[column.name] = getattr(self, column.name)
        
        return self.__class__(**attributes)
    
    @hybrid_property
    def exists(self) -> bool:
        """Laravel-style exists property."""
        return self.id is not None
    
    def was_recently_created(self) -> bool:
        """Laravel-style check if model was recently created."""
        if not self.created_at:
            return False
        return (datetime.now() - self.created_at).total_seconds() < 60  # Within last minute
    
    # Laravel 12 Enhanced Change Tracking
    def get_dirty(self) -> Dict[str, Any]:
        """Get dirty attributes (Laravel 12 enhanced)."""
        return self._dirty_attributes.copy()
    
    def is_dirty(self, *attributes: str) -> bool:
        """Check if model is dirty (Laravel 12 enhanced)."""
        if not attributes:
            return len(self._dirty_attributes) > 0
        return any(attr in self._dirty_attributes for attr in attributes)
    
    def get_original(self, key: Optional[str] = None) -> Any:
        """Get original attribute values (Laravel 12 enhanced)."""
        if key is not None:
            return self._original_attributes.get(key)
        return self._original_attributes.copy()
    
    def get_changes(self) -> Dict[str, Tuple[Any, Any]]:
        """Get all changes (old_value, new_value) (Laravel 12)."""
        return self._changes.copy()
    
    def was_changed(self, *attributes: str) -> bool:
        """Check if attributes were changed (Laravel 12)."""
        if not attributes:
            return len(self._changes) > 0
        return any(attr in self._changes for attr in attributes)
    
    def only_dirty(self, *attributes: str) -> Dict[str, Any]:
        """Get only specified dirty attributes (Laravel 12)."""
        if not attributes:
            return self.get_dirty()
        return {k: v for k, v in self._dirty_attributes.items() if k in attributes}
    
    def sync_changes(self) -> Dict[str, Any]:
        """Sync changes and return what was dirty (Laravel 12)."""
        changes = self.get_dirty()
        self._sync_original()
        return changes
    
    def sync_original_attribute(self, attribute: str) -> 'BaseModel':
        """Sync a single original attribute (Laravel 12)."""
        if hasattr(self, attribute):
            self._original_attributes[attribute] = getattr(self, attribute)
            if attribute in self._dirty_attributes:
                del self._dirty_attributes[attribute]
            if attribute in self._changes:
                del self._changes[attribute]
        return self
    
    def is_clean(self, *attributes: str) -> bool:
        """Check if model is clean (Laravel 12)."""
        return not self.is_dirty(*attributes)
    
    def original_is_equivalent(self, key: str) -> bool:
        """Check if current value is equivalent to original (Laravel 12)."""
        current = getattr(self, key, None)
        original = self._original_attributes.get(key)
        return current == original
    
    # Laravel 12 Strict Mode Methods
    @classmethod
    def enable_strict_mode(cls, config: Optional[StrictConfig] = None) -> None:
        """Enable strict mode with optional configuration (Laravel 12)."""
        if config is None:
            config = StrictConfig(enabled=True)
        else:
            config.enabled = True
        cls.__strict_config__ = config
    
    @classmethod
    def disable_strict_mode(cls) -> None:
        """Disable strict mode (Laravel 12)."""
        cls.__strict_config__.enabled = False
    
    @classmethod
    def is_strict_mode_enabled(cls) -> bool:
        """Check if strict mode is enabled (Laravel 12)."""
        return cls.__strict_config__.enabled
    
    def prevent_lazy_loading(self, value: bool = True) -> 'BaseModel':
        """Prevent lazy loading for this instance (Laravel 12)."""
        self.__strict_config__.prevent_lazy_loading = value
        return self
    
    def prevent_accessing_missing_attributes(self, value: bool = True) -> 'BaseModel':
        """Prevent accessing missing attributes (Laravel 12)."""
        self.__strict_config__.fail_on_unknown_attributes = value
        return self
    
    def prevent_silently_discarding_attributes(self, value: bool = True) -> 'BaseModel':
        """Prevent silently discarding attributes (Laravel 12)."""
        self.__strict_config__.prevent_silently_discarding_attributes = value
        return self
    
    @classmethod
    def query(cls, session: Session) -> Any:
        """Laravel-style query method."""
        from app.Database.QueryBuilder import QueryBuilder
        return QueryBuilder(cls, session)


# Event listener to generate ULID for new instances
@event.listens_for(BaseModel, 'before_insert', propagate=True)
def generate_ulid_before_insert(mapper: Any, connection: Any, target: BaseModel) -> None:
    """Generate ULID for new instances if not provided."""
    del mapper, connection  # Unused parameters required by SQLAlchemy
    if not target.id:
        target.id = generate_ulid()