from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING, Callable, List, ClassVar, Type, TypeVar, Tuple, Union, cast as type_cast, get_type_hints, Protocol, final, Literal, Self, Generic, overload, NewType, NoReturn, Awaitable, Coroutine
from app.Support.Types import T, ModelT, UserId, validate_types, is_model, TypeConstants
from datetime import datetime, date, time, timezone
from decimal import Decimal
from sqlalchemy import func, event, desc, asc, String, Integer, Boolean, DateTime, Text, and_, or_
from sqlalchemy.types import Date, Time, Float, JSON
from sqlalchemy.sql import select, exists, not_, Select, Insert, Update, Delete
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, validates, Query, selectinload, joinedload, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.inspection import inspect as sa_inspect
from enum import Enum, StrEnum
import json
import uuid
from dataclasses import dataclass, field
import logging
from abc import ABC, abstractmethod
import weakref
from collections.abc import Iterable, Iterator, MutableSequence
import inspect
from contextlib import contextmanager
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.Utils.ULIDUtils import generate_ulid, ULID


@dataclass
class RelationshipConfig:
    """Enhanced relationship configuration"""
    relation_type: RelationType
    related_model: str
    foreign_key: Optional[str] = None
    local_key: Optional[str] = None
    pivot_table: Optional[str] = None
    as_name: Optional[str] = None
    eager_load: bool = False
    cascade_delete: bool = False
    cascade_update: bool = True
    lazy_loading: str = 'select'  # select, joined, subquery, immediate, noload
    back_populates: Optional[str] = None
    join_condition: Optional[str] = None
    order_by: Optional[str] = None
    where_clause: Optional[str] = None
    polymorphic: bool = False
    polymorphic_identity: Optional[str] = None


@dataclass 
class ScopeConfig:
    """Configuration for model scopes"""
    name: str
    description: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    cacheable: bool = True
    cache_ttl: int = 300
    auto_apply: bool = False
    global_scope: bool = False
    conditional: Optional[Callable[[], bool]] = None

# Import T from enhanced type system
# T already imported from app.Support.Types

if TYPE_CHECKING:
    pass  # User imports handled dynamically


# Laravel 12 Strict Mode Configuration (Enhanced)
@dataclass(frozen=True)
class StrictConfig:
    """Laravel 12 strict mode configuration with enhanced type safety."""
    enabled: bool = True  # Default to strict mode in Laravel 12
    fail_on_mass_assignment: bool = True
    fail_on_unknown_attributes: bool = True
    validate_casts: bool = True
    prevent_lazy_loading: bool = True  # Enabled by default in Laravel 12
    prevent_silently_discarding_attributes: bool = True
    strict_type_checking: bool = True
    prevent_accessing_missing_attributes: bool = True
    prevent_silent_attribute_mutation: bool = True  # New in Laravel 12
    enforce_immutable_attributes: bool = True  # New in Laravel 12
    require_explicit_casts: bool = True  # New in Laravel 12
    validate_relationship_types: bool = True  # New in Laravel 12
    prevent_n_plus_one_queries: bool = True  # New in Laravel 12
    enforce_fillable_whitelist: bool = True  # New in Laravel 12


# Laravel 12 Enhanced Cast Types (Strict Enum)
class CastType(StrEnum):
    """Enhanced cast types for Laravel 12 with strict typing."""
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
    # Laravel 12 immutable casts
    IMMUTABLE_DATE = "immutable_date"
    IMMUTABLE_DATETIME = "immutable_datetime"
    # Laravel 12 advanced casts
    AS_ARRAY_OBJECT = "AsArrayObject"
    AS_COLLECTION = "AsCollection"
    AS_ENUM_COLLECTION = "AsEnumCollection"
    AS_STRINGABLE = "AsStringable"
    AS_VALUE_OBJECT = "AsValueObject"
    # Laravel 12 database casts
    AS_JSON_COLUMN = "AsJsonColumn"
    AS_COMPOSITE = "AsComposite"
    AS_ENCRYPTED_OBJECT = "AsEncryptedObject"


# Laravel 12 Enhanced Cast Interface with Strict Typing
from typing import runtime_checkable

@runtime_checkable
class CastInterface(Protocol):
    """Enhanced interface for custom casts (Laravel 12) with strict typing."""
    
    def get(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> Any:
        """Transform the attribute from the underlying model values."""
        ...
    
    def set(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> Any:
        """Transform the attribute to its underlying representation."""
        ...
    
    def serialize(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> Any:
        """Serialize the attribute for array/JSON representation (Laravel 12)."""
        return self.get(model, key, value, attributes)
    
    def is_cacheable(self) -> bool:
        """Whether this cast result can be cached (Laravel 12)."""
        return True


@runtime_checkable  
class InboundCastInterface(Protocol):
    """Interface for inbound-only casts (Laravel 12)."""
    
    def set(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> Any:
        """Transform the attribute to its underlying representation."""
        ...


@runtime_checkable
class CastsInboundAttributes(Protocol):
    """Interface for complex inbound attribute casting (Laravel 12)."""
    
    def set(self, model: 'BaseModel', key: str, value: Any, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Transform inbound attributes."""
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


# Import Base from config.database to avoid circular imports
from config.database import Base


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    @declared_attr
    def deleted_at(cls) -> Mapped[Optional[datetime]]:
        return mapped_column(DateTime, default=None)
    
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
    
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(DateTime, default=datetime.utcnow)
    
    @declared_attr  
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Laravel 12 Model Factory Protocol
@runtime_checkable
class ModelFactoryProtocol(Protocol[T]):
    """Protocol for Laravel 12 model factories with strict typing."""
    
    def definition(self) -> Dict[str, Any]:
        """Define the default attribute values."""
        ...
    
    def make(self, attributes: Optional[Dict[str, Any]] = None, count: int = 1) -> Union[T, List[T]]:
        """Make model instances without persisting."""
        ...
    
    def create(self, attributes: Optional[Dict[str, Any]] = None, count: int = 1) -> Union[T, List[T]]:
        """Create and persist model instances."""
        ...
    
    def state(self, state: str, *states: str) -> Self:
        """Apply factory states."""
        ...


# Laravel 12 Model Builder Protocol
@runtime_checkable
class ModelBuilderProtocol(Protocol[T]):
    """Protocol for Laravel 12 model builders with strict typing."""
    
    def where(self, column: str, operator: str = '=', value: Any = None) -> Self:
        """Add a where clause."""
        ...
    
    def get(self) -> List[T]:
        """Execute the query and get results."""
        ...
    
    def first(self) -> Optional[T]:
        """Get the first result."""
        ...
    
    def find(self, id_value: Any) -> Optional[T]:
        """Find by ID."""
        ...


class BaseModel(Base, TimestampMixin):
    __abstract__ = True
    
    # Laravel 12 strict mode configuration (enabled by default)
    __strict_config__: ClassVar[StrictConfig] = StrictConfig(enabled=True)
    
    # Laravel-style hidden/fillable attributes
    __fillable__: ClassVar[List[str]] = []
    __guarded__: ClassVar[List[str]] = ['id', 'created_at', 'updated_at']
    __hidden__: ClassVar[List[str]] = []
    __visible__: ClassVar[List[str]] = []
    __casts__: ClassVar[Dict[str, Union[str, Type[CastInterface], CastInterface]]] = {}
    __dates__: ClassVar[List[str]] = ['created_at', 'updated_at']
    __appends__: ClassVar[List[str]] = []
    
    # Laravel 12 enhanced attributes (modern Attribute-based only)
    __serializable__: ClassVar[List[str]] = []
    __read_only__: ClassVar[List[str]] = ['id', 'created_at']
    __with_default__: ClassVar[List[str]] = []
    
    # Laravel 12 Enhanced Attributes
    __with__: ClassVar[List[str]] = []  # Default relationships to load
    __with_count__: ClassVar[List[str]] = []  # Default relationship counts
    __touches__: ClassVar[List[str]] = []  # Parent models to touch when updated
    __primary_key__: ClassVar[str] = 'id'
    __key_type__: ClassVar[str] = 'string'  # ULID is string-based
    __incrementing__: ClassVar[bool] = False  # ULID is not auto-incrementing
    __per_page__: ClassVar[int] = 15  # Default pagination count
    __connection__: ClassVar[Optional[str]] = None  # Database connection name
    __table__: ClassVar[Optional[str]] = None  # Explicit table name
    __morphs__: ClassVar[Dict[str, str]] = {}  # Polymorphic relationships
    __attribute_casting__: ClassVar[Dict[str, Callable[[Any], Any]]] = {}
    __lazy_accessors__: ClassVar[Dict[str, Callable[['BaseModel'], Any]]] = {}
    __computed_accessors__: ClassVar[Dict[str, Callable[['BaseModel'], Any]]] = {}
    
    # Laravel-style relationships definition
    __relationships__: ClassVar[Dict[str, RelationshipDefinition]] = {}
    
    # Enhanced relationship and scope configuration
    __relationship_configs__: ClassVar[Dict[str, 'RelationshipConfig']] = {}
    __scope_configs__: ClassVar[Dict[str, 'ScopeConfig']] = {}
    __auto_load_relationships__: ClassVar[List[str]] = []
    __relationship_strategies__: ClassVar[Dict[str, str]] = {}
    
    # Laravel-style observers
    __observers__: ClassVar[List[str]] = []
    
    # Query builder attribute
    _query: Optional[Select[Any]]
    
    # Laravel-style soft deletes
    __soft_deletes__: ClassVar[bool] = False
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    # Laravel-style global scopes
    __global_scopes__: ClassVar[Dict[str, Callable[[Select[Any]], Select[Any]]]] = {}
    _scope_manager: ClassVar[Optional['GlobalScopeManager']] = None
    
    # Laravel 12 internal tracking (enhanced with strict typing)
    _original_attributes: Dict[str, Any]
    _dirty_attributes: Dict[str, Any]
    _exists: bool
    _was_recently_created: bool
    _changes: Dict[str, Tuple[Any, Any]]  # old_value, new_value
    _relations: Dict[str, Any]  # Loaded relationships
    _relations_cache: Dict[str, Any]  # Cached relationship data
    _touched: bool = False  # Whether model has been touched
    _guards: Dict[str, bool] = {}  # Attribute guards
    _mutations: Dict[str, Any] = {}  # Pending mutations
    _cast_cache: Dict[str, Any] = {}  # Laravel 12: Cast result cache
    _attribute_cast_cache: Dict[str, Any] = {}  # Laravel 12: Attribute cast cache
    _prevent_accessing_missing_attributes: bool = False  # Laravel 12: Instance-level control
    _prevent_silently_discarding_attributes: bool = False  # Laravel 12: Instance-level control
    _factory: Optional['ModelFactoryProtocol[Self]'] = None  # Laravel 12: Associated factory
    _query_builder: Optional['ModelBuilderProtocol[Self]'] = None  # Laravel 12: Query builder
    
    id: Mapped[ULID] = mapped_column(primary_key=True, index=True)
    
    # Audit columns for tracking who created/updated the record
    created_by: Mapped[Optional[ULID]] = mapped_column(nullable=True)
    updated_by: Mapped[Optional[ULID]] = mapped_column(nullable=True)
    
    # Audit relationships
    @declared_attr
    def created_by_user(cls) -> Mapped[Optional[Any]]:
        return relationship("User", foreign_keys=[cls.created_by], post_update=True)
    
    @declared_attr
    def updated_by_user(cls) -> Mapped[Optional[Any]]:
        return relationship("User", foreign_keys=[cls.updated_by], post_update=True)
    
    def __init__(self, **kwargs: Any) -> None:
        # Initialize Laravel 12 enhanced tracking attributes
        self._original_attributes = {}
        self._dirty_attributes = {}
        self._exists = False
        self._was_recently_created = True
        self._changes = {}
        self._relations = {}
        self._relations_cache = {}
        self._touched = False
        self._guards = {}
        
        # Initialize AccessorMutatorManager for Laravel-style attribute handling
        self._accessor_mutator_manager = None
        self._mutations = {}
        self._cast_cache = {}
        self._attribute_cast_cache = {}
        self._prevent_accessing_missing_attributes = self.__strict_config__.prevent_accessing_missing_attributes
        self._prevent_silently_discarding_attributes = self.__strict_config__.prevent_silently_discarding_attributes
        self._factory = None
        self._query_builder = None
        
        if 'id' not in kwargs:
            kwargs['id'] = generate_ulid()
        
        # Laravel 12 strict mode validation
        if self.__strict_config__.enabled and self.__strict_config__.fail_on_unknown_attributes:
            self._validate_attributes(kwargs)
        
        # Modern attribute handling will be done through AccessorMutatorManager
        
        super().__init__(**kwargs)
        
        # Store original values for change tracking
        self._sync_original()
        
        # Auto-load default relationships
        if self.__with__:
            self._load_default_relationships()
    
    def _load_default_relationships(self) -> None:
        """Load default relationships specified in __with__ (Laravel 12)."""
        # This would be implemented with actual session management
        # For now, it's a placeholder
        pass
    
    def _validate_attributes(self, attributes: Dict[str, Any]) -> None:
        """Validate attributes in strict mode (Laravel 12)."""
        valid_attributes = {col.name for col in self.__table__.columns}
        valid_attributes.update(self.__appends__)
        
        for key in attributes:
            if key not in valid_attributes:
                if self.__strict_config__.fail_on_unknown_attributes:
                    raise ValueError(f"Unknown attribute '{key}' for {self.__class__.__name__}")
    
    
    def _sync_original(self) -> None:
        """Sync original attributes for change tracking (Laravel 12)."""
        self._original_attributes = {}
        for column in self.__table__.columns:
            if hasattr(self, column.name):
                self._original_attributes[column.name] = getattr(self, column.name)
        self._dirty_attributes = {}
        self._changes = {}
    
    def __getattribute__(self, name: str) -> Any:
        """
        Override attribute access to use accessors and maintain Laravel behavior.
        
        This method integrates seamlessly with SQLAlchemy while providing
        Laravel-style accessor functionality.
        """
        # Special handling for internal attributes and methods
        if name.startswith('_') or name in ['get_attribute', 'set_attribute', 'to_dict', 'fill', 'save', 'delete']:
            return super().__getattribute__(name)
        
        # For regular attributes, use the get_attribute method which handles accessors
        try:
            # First check if this is a regular object attribute
            value = super().__getattribute__(name)
            
            # If it's a SQLAlchemy column or relationship, apply accessors
            if hasattr(self.__class__, name) and hasattr(getattr(self.__class__, name), 'property'):
                return self.get_attribute(name)
            
            return value
        except AttributeError:
            # If attribute doesn't exist, let the default behavior handle it
            return super().__getattribute__(name)
    
    def __setattr__(self, name: str, value: Any) -> None:
        """
        Override attribute setting to use mutators and maintain Laravel behavior.
        
        This method integrates seamlessly with SQLAlchemy while providing
        Laravel-style mutator functionality.
        """
        # Special handling for internal attributes
        if name.startswith('_') or not hasattr(self, '_accessor_mutator_manager'):
            super().__setattr__(name, value)
            return
        
        # For regular attributes, use the set_attribute method which handles mutators
        if hasattr(self.__class__, name) and hasattr(getattr(self.__class__, name), 'property'):
            self.set_attribute(name, value)
        else:
            super().__setattr__(name, value)

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
        # Initialize AccessorMutatorManager if needed
        if self._accessor_mutator_manager is None:
            from app.Attributes import AccessorMutatorManager
            self._accessor_mutator_manager = AccessorMutatorManager(self)
        
        # Get raw value from the model
        raw_value = super().__getattribute__(key) if hasattr(super(), key) else None
        
        # Apply accessor through the manager
        transformed_value = self._accessor_mutator_manager.get_attribute_value(key, raw_value)
        
        # Apply casting if defined
        if key in self.__casts__:
            cast_type = self.__casts__[key]
            transformed_value = self._cast_attribute(transformed_value, cast_type, key)
        
        return transformed_value
    
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
        
        # Initialize AccessorMutatorManager if needed
        if self._accessor_mutator_manager is None:
            from app.Attributes import AccessorMutatorManager
            self._accessor_mutator_manager = AccessorMutatorManager(self)
        
        # Apply mutator through the manager
        value = self._accessor_mutator_manager.set_attribute_value(key, value)
        
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
    
    
    # Laravel 12 Enhanced Scopes with Strict Typing
    @classmethod
    def scope_where_not_null(cls, query: Select[Any], column: str) -> Select[Any]:
        """Laravel 12 enhanced scope for non-null values."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        return query.where(getattr(cls, column).is_not(None))
    
    @classmethod
    def scope_where_null(cls, query: Select[Any], column: str) -> Select[Any]:
        """Laravel 12 enhanced scope for null values."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        return query.where(getattr(cls, column).is_(None))
    
    @classmethod
    def scope_where_like(cls, query: Select[Any], column: str, pattern: str) -> Select[Any]:
        """Laravel 12 scope for LIKE queries."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        return query.where(getattr(cls, column).like(pattern))
    
    @classmethod
    def scope_where_ilike(cls, query: Select[Any], column: str, pattern: str) -> Select[Any]:
        """Laravel 12 scope for case-insensitive LIKE queries."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        return query.where(getattr(cls, column).ilike(pattern))
    
    @classmethod 
    def scope_where_starts_with(cls, query: Select[Any], column: str, prefix: str) -> Select[Any]:
        """Laravel 12 scope for prefix matching."""
        return cls.scope_where_like(query, column, f"{prefix}%")
    
    @classmethod
    def scope_where_ends_with(cls, query: Select[Any], column: str, suffix: str) -> Select[Any]:
        """Laravel 12 scope for suffix matching."""
        return cls.scope_where_like(query, column, f"%{suffix}")
    
    @classmethod
    def scope_where_contains(cls, query: Select[Any], column: str, substring: str) -> Select[Any]:
        """Laravel 12 scope for substring matching."""
        return cls.scope_where_like(query, column, f"%{substring}%")
    
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
        """Laravel 12 enhanced scope to exclude soft deleted records."""
        if cls.__soft_deletes__:
            return query.where(getattr(cls, 'deleted_at').is_(None))
        return query
    
    # Laravel 12 Advanced Scopes
    @classmethod
    def scope_where_date(cls, query: Select[Any], column: str, date_value: Union[date, str]) -> Select[Any]:
        """Laravel 12 scope for date matching."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        if isinstance(date_value, str):
            date_value = datetime.fromisoformat(date_value).date()
        return query.where(func.date(getattr(cls, column)) == date_value)
    
    @classmethod
    def scope_where_month(cls, query: Select[Any], column: str, month: int) -> Select[Any]:
        """Laravel 12 scope for month matching."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        return query.where(func.extract('month', getattr(cls, column)) == month)
    
    @classmethod
    def scope_where_year(cls, query: Select[Any], column: str, year: int) -> Select[Any]:
        """Laravel 12 scope for year matching."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        return query.where(func.extract('year', getattr(cls, column)) == year)
    
    @classmethod
    def scope_where_day(cls, query: Select[Any], column: str, day: int) -> Select[Any]:
        """Laravel 12 scope for day matching."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        return query.where(func.extract('day', getattr(cls, column)) == day)
    
    @classmethod
    def scope_where_time(cls, query: Select[Any], column: str, time_value: Union[time, str]) -> Select[Any]:
        """Laravel 12 scope for time matching."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        if isinstance(time_value, str):
            time_value = datetime.fromisoformat(f"2000-01-01T{time_value}").time()
        return query.where(func.time(getattr(cls, column)) == time_value)
    
    @classmethod
    def scope_where_column(cls, query: Select[Any], first_column: str, operator: str, second_column: str) -> Select[Any]:
        """Laravel 12 scope for column comparisons."""
        if not hasattr(cls, first_column):
            raise AttributeError(f"Column '{first_column}' does not exist on {cls.__name__}")
        if not hasattr(cls, second_column):
            raise AttributeError(f"Column '{second_column}' does not exist on {cls.__name__}")
        
        first_col = getattr(cls, first_column)
        second_col = getattr(cls, second_column)
        
        if operator == '=':
            return query.where(first_col == second_col)
        elif operator == '!=':
            return query.where(first_col != second_col)
        elif operator == '>':
            return query.where(first_col > second_col)
        elif operator == '>=':
            return query.where(first_col >= second_col)
        elif operator == '<':
            return query.where(first_col < second_col)
        elif operator == '<=':
            return query.where(first_col <= second_col)
        else:
            raise ValueError(f"Unsupported operator: {operator}")
    
    @classmethod
    def scope_where_json(cls, query: Select[Any], column: str, path: str, value: Any) -> Select[Any]:
        """Laravel 12 scope for JSON path queries."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        json_column = getattr(cls, column)
        return query.where(json_column[path].as_string() == str(value))
    
    @classmethod
    def scope_where_json_contains(cls, query: Select[Any], column: str, value: Any) -> Select[Any]:
        """Laravel 12 scope for JSON containment queries."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        json_column = getattr(cls, column)
        return query.where(json_column.contains(json.dumps(value)))
    
    @classmethod
    def scope_where_json_length(cls, query: Select[Any], column: str, length: int, path: Optional[str] = None) -> Select[Any]:
        """Laravel 12 scope for JSON array length queries."""
        if not hasattr(cls, column):
            raise AttributeError(f"Column '{column}' does not exist on {cls.__name__}")
        json_column = getattr(cls, column)
        if path:
            return query.where(func.json_array_length(json_column[path]) == length)
        else:
            return query.where(func.json_array_length(json_column) == length)
    
    # Laravel 12 Global Scope Methods
    @classmethod
    def get_scope_manager(cls) -> 'GlobalScopeManager':
        """Get the global scope manager for this model."""
        if cls._scope_manager is None:
            from app.Scopes.GlobalScopeManager import GlobalScopeManager
            cls._scope_manager = GlobalScopeManager(cls)
        return cls._scope_manager
    
    @classmethod
    def add_global_scope(cls, name: str, scope: Union[Callable[[Select[Any]], Select[Any]], 'Scope']) -> None:
        """Add a global scope to the model (Laravel 12)."""
        # Support both legacy callable scopes and new Scope classes
        cls.__global_scopes__[name] = scope
        
        # Also add to the new scope manager
        manager = cls.get_scope_manager()
        manager.add_scope(name, scope)
    
    @classmethod
    def remove_global_scope(cls, name: str) -> None:
        """Remove a global scope from the model (Laravel 12)."""
        if name in cls.__global_scopes__:
            del cls.__global_scopes__[name]
        
        # Also remove from the new scope manager
        manager = cls.get_scope_manager()
        manager.remove_scope(name)
    
    @classmethod
    def without_global_scope(cls, name: str, query: Select[Any]) -> Select[Any]:
        """Execute query without a specific global scope (Laravel 12)."""
        manager = cls.get_scope_manager()
        return manager.remove_scope_from_query(query, name)
    
    @classmethod
    def without_global_scopes(cls, query: Select[Any], scopes: Optional[List[str]] = None) -> Select[Any]:
        """Execute query without global scopes (Laravel 12)."""
        manager = cls.get_scope_manager()
        return manager.without_scopes(query, scopes)
    
    @classmethod
    def apply_global_scopes(cls, query: Select[Any]) -> Select[Any]:
        """Apply all global scopes to a query (Laravel 12)."""
        # Apply legacy scopes
        for scope_name, scope in cls.__global_scopes__.items():
            query = scope(query)
        
        # Apply new scope manager scopes
        manager = cls.get_scope_manager()
        query = manager.apply_scopes(query)
        
        return query
    
    @classmethod
    def with_global_scope(cls, name: str, scope: Union[Callable, 'Scope']) -> Type['BaseModel']:
        """Add a temporary global scope for this query session."""
        cls.add_global_scope(name, scope)
        return cls
    
    @classmethod
    def only_global_scopes(cls, scope_names: List[str], query: Select[Any]) -> Select[Any]:
        """Execute query with only specified global scopes."""
        manager = cls.get_scope_manager()
        return manager.with_only_scopes(query, scope_names)
    
    # Model relationship methods
    def touch(self) -> None:
        """Laravel-style touch method to update timestamps."""
        self.updated_at = datetime.now(timezone.utc)
    
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
        """Laravel-style delete method with observer support (Laravel 12)."""
        # Fire deleting event
        result = ObserverRegistry.fire_event(self, 'deleting')
        if result is False:
            return False  # Deletion was cancelled
        
        if self.__soft_deletes__:
            self.deleted_at = datetime.now(timezone.utc)
            success = self.save(session) is not None
        else:
            if session is not None:
                session.delete(self)
                session.commit()
                success = True
            else:
                success = False
        
        if success:
            # Fire deleted event
            ObserverRegistry.fire_event(self, 'deleted')
        
        return success
    
    def force_delete(self, session: Optional[Session] = None) -> bool:
        """Laravel-style force delete (bypass soft deletes)."""
        if session is not None:
            session.delete(self)
            session.commit()
            return True
        return False
    
    def restore(self, session: Optional[Session] = None) -> 'BaseModel':
        """Laravel-style restore soft deleted record with observer support (Laravel 12)."""
        if self.__soft_deletes__:
            # Fire restoring event
            result = ObserverRegistry.fire_event(self, 'restoring')
            if result is False:
                raise ValueError("Model restoration was cancelled by observer")
            
            self.deleted_at = None
            self.save(session)
            
            # Fire restored event
            ObserverRegistry.fire_event(self, 'restored')
        return self
    
    def is_soft_deleted(self) -> bool:
        """Check if the model is soft deleted."""
        return self.__soft_deletes__ and self.deleted_at is not None
    
    # Laravel 12 Enhanced Scope Registration
    @classmethod
    def scope(cls, name: str) -> Callable[[Callable], Callable]:
        """Decorator for registering custom scopes (Laravel 12)."""
        def decorator(func: Callable[[Any, Select[Any], ...], Select[Any]]) -> Callable:
            scope_method_name = f"scope_{name}"
            setattr(cls, scope_method_name, classmethod(func))
            return func
        return decorator
    
    @classmethod
    def local_scope(cls, name: str, scope_func: Callable[[Select[Any], ...], Select[Any]]) -> None:
        """Register a local scope dynamically (Laravel 12)."""
        scope_method_name = f"scope_{name}"
        setattr(cls, scope_method_name, classmethod(scope_func))
    
    def scope_for_model(self, name: str, *args: Any) -> Select[Any]:
        """Apply a scope to this model instance (Laravel 12)."""
        scope_method_name = f"scope_{name}"
        if hasattr(self.__class__, scope_method_name):
            scope_method = getattr(self.__class__, scope_method_name)
            query = select(self.__class__)
            return scope_method(query, *args)
        else:
            raise AttributeError(f"Scope '{name}' not found on {self.__class__.__name__}")
    
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
    
    def replicate(self, except_columns: Optional[List[str]] = None) -> 'BaseModel':
        """Laravel-style replicate method with observer support (Laravel 12)."""
        if except_columns is None:
            except_columns = ['id', 'created_at', 'updated_at']
        
        # Fire replicating event
        ObserverRegistry.fire_event(self, 'replicating')
        
        attributes = {}
        for column in self.__table__.columns:
            if column.name not in except_columns:
                attributes[column.name] = getattr(self, column.name)
        
        replica = self.__class__(**attributes)
        replica._exists = False
        replica._was_recently_created = True
        
        return replica
    
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
    def query(cls, session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Laravel 12 enhanced query method with strict typing."""
        from app.Utils.QueryBuilder.QueryBuilder import QueryBuilder
        if session is None:
            from app.Support.ServiceContainer import container
            session = container.make('db.session')
        return QueryBuilder(cls, session)
    
    @classmethod
    def factory(cls) -> 'ModelFactoryProtocol[Self]':
        """Get the model factory (Laravel 12)."""
        if not hasattr(cls, '_factory_class'):
            # Dynamically import factory class
            factory_name = f"{cls.__name__}Factory"
            try:
                from importlib import import_module
                factory_module = import_module(f"database.factories.{factory_name}")
                factory_class = getattr(factory_module, factory_name)
                cls._factory_class = factory_class
            except (ImportError, AttributeError):
                raise ValueError(f"Factory {factory_name} not found for {cls.__name__}")
        
        return cls._factory_class()
    
    @classmethod
    def make_factory(cls) -> 'ModelFactory[Self]':
        """Create a new factory instance (Laravel 12)."""
        return ModelFactory(cls)
    
    @classmethod  
    def new_factory(cls, count: Optional[int] = None) -> 'ModelFactory[Self]':
        """Create a new factory with optional count (Laravel 12)."""
        factory = cls.make_factory()
        if count is not None:
            factory = factory.count(count)
        return factory
    
    # Laravel 12 Enhanced Builder Methods
    @classmethod
    def where(cls, column: str, operator: str = '=', value: Any = None, session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Start a query with where clause (Laravel 12)."""
        return cls.query(session).where(column, operator, value)
    
    @classmethod
    def where_in(cls, column: str, values: List[Any], session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Start a query with where in clause (Laravel 12)."""
        return cls.query(session).where_in(column, values)
    
    @classmethod
    def where_not_in(cls, column: str, values: List[Any], session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Start a query with where not in clause (Laravel 12)."""
        return cls.query(session).where_not_in(column, values)
    
    @classmethod
    def where_null(cls, column: str, session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Start a query with where null clause (Laravel 12)."""
        return cls.query(session).where_null(column)
    
    @classmethod
    def where_not_null(cls, column: str, session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Start a query with where not null clause (Laravel 12)."""
        return cls.query(session).where_not_null(column)
    
    @classmethod
    def order_by(cls, column: str, direction: str = 'asc', session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Start a query with order by clause (Laravel 12)."""
        return cls.query(session).order_by(column, direction)
    
    @classmethod
    def latest(cls, column: str = 'created_at', session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Order by latest (Laravel 12)."""
        return cls.query(session).latest(column)
    
    @classmethod
    def oldest(cls, column: str = 'created_at', session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Order by oldest (Laravel 12)."""
        return cls.query(session).oldest(column)
    
    @classmethod
    def limit(cls, count: int, session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Limit query results (Laravel 12)."""
        return cls.query(session).limit(count)
    
    @classmethod
    def take(cls, count: int, session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Take specific number of results (Laravel 12)."""
        return cls.query(session).take(count)
    
    @classmethod
    def skip(cls, count: int, session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Skip specific number of results (Laravel 12)."""
        return cls.query(session).skip(count)
    
    @classmethod
    def offset(cls, count: int, session: Optional[Session] = None) -> 'QueryBuilder[Self]':
        """Offset query results (Laravel 12)."""
        return cls.query(session).offset(count)
    
    @classmethod
    def all(cls, session: Optional[Session] = None) -> List[Self]:
        """Get all model instances (Laravel 12)."""
        return cls.query(session).get()
    
    # Laravel 12 Enhanced Methods
    def get_key_name(self) -> str:
        """Get the primary key name (Laravel 12)."""
        return self.__primary_key__
    
    def get_key_type(self) -> str:
        """Get the primary key type (Laravel 12)."""
        return self.__key_type__
    
    def get_incrementing(self) -> bool:
        """Get whether the key is incrementing (Laravel 12)."""
        return self.__incrementing__
    
    def get_connection_name(self) -> Optional[str]:
        """Get the database connection name (Laravel 12)."""
        return self.__connection__
    
    def get_table(self) -> str:
        """Get the table name (Laravel 12)."""
        return self.__table__ or self.__tablename__
    
    def get_per_page(self) -> int:
        """Get the default pagination count (Laravel 12)."""
        return self.__per_page__
    
    def set_per_page(self, per_page: int) -> 'BaseModel':
        """Set the default pagination count (Laravel 12)."""
        self.__per_page__ = per_page
        return self
    
    def get_morph_class(self) -> str:
        """Get the morph class name (Laravel 12)."""
        return self.__class__.__name__
    
    def get_foreign_key(self) -> str:
        """Get the default foreign key name (Laravel 12)."""
        return f"{self.__class__.__name__.lower()}_id"
    
    def resolve_relation_using_name(self, name: str) -> Any:
        """Resolve relationship using name (Laravel 12)."""
        if name in self._relations:
            return self._relations[name]
        
        # Check for computed accessor
        if name in self.__lazy_accessors__:
            accessor = self.__lazy_accessors__[name]
            value = accessor(self)
            self._relations[name] = value
            return value
        
        return None
    
    def set_relation(self, relation: str, value: Any) -> 'BaseModel':
        """Set a relationship value (Laravel 12)."""
        self._relations[relation] = value
        return self
    
    def unset_relation(self, relation: str) -> 'BaseModel':
        """Unset a relationship (Laravel 12)."""
        if relation in self._relations:
            del self._relations[relation]
        return self
    
    def get_relations(self) -> Dict[str, Any]:
        """Get all loaded relationships (Laravel 12)."""
        return self._relations.copy()
    
    def set_relations(self, relations: Dict[str, Any]) -> 'BaseModel':
        """Set multiple relationships (Laravel 12)."""
        self._relations.update(relations)
        return self
    
    def without_relations(self) -> 'BaseModel':
        """Create a copy without relationships (Laravel 12)."""
        copy = self.replicate()
        copy._relations = {}
        return copy
    
    def touches(self, *relations: str) -> None:
        """Touch related models (Laravel 12)."""
        for relation in relations:
            if relation in self._relations:
                related = self._relations[relation]
                if hasattr(related, 'touch'):
                    related.touch()
    
    def is_guarded(self, key: str) -> bool:
        """Check if attribute is guarded (Laravel 12)."""
        return key in self._guards and self._guards[key]
    
    def guard(self, *attributes: str) -> 'BaseModel':
        """Guard attributes from mass assignment (Laravel 12)."""
        for attr in attributes:
            self._guards[attr] = True
        return self
    
    def unguard(self, *attributes: str) -> 'BaseModel':
        """Unguard attributes (Laravel 12)."""
        for attr in attributes:
            self._guards[attr] = False
        return self
    
    def totally_guarded(self) -> bool:
        """Check if model is totally guarded (Laravel 12)."""
        return len(self.__fillable__) == 0 and len(self.__guarded__) > 0
    
    @classmethod
    def unguarded(cls, callback: Callable[[], T]) -> T:
        """Execute callback without guards (Laravel 12)."""
        # Temporarily disable guards
        original_fillable = cls.__fillable__.copy()
        original_guarded = cls.__guarded__.copy()
        
        cls.__fillable__.clear()
        cls.__guarded__.clear()
        
        try:
            return callback()
        finally:
            cls.__fillable__.extend(original_fillable)
            cls.__guarded__.extend(original_guarded)
    
    def get_route_key(self) -> Any:
        """Get the route key value (Laravel 12)."""
        return getattr(self, self.get_route_key_name())
    
    def get_route_key_name(self) -> str:
        """Get the route key name (Laravel 12)."""
        return self.get_key_name()
    
    def resolve_route_binding(self, value: Any, field: Optional[str] = None) -> Optional['BaseModel']:
        """Resolve route model binding (Laravel 12)."""
        # This would be implemented with actual session management
        return None
    
    def resolve_child_route_binding(self, child_type: str, value: Any, field: Optional[str] = None) -> Optional['BaseModel']:
        """Resolve child route model binding (Laravel 12)."""
        # This would be implemented with actual session management
        return None
    
    # Laravel 12 Observer Methods
    @classmethod
    def observe(cls, observer: Union[ModelObserver, Type[ModelObserver], str]) -> None:
        """Register an observer for this model (Laravel 12)."""
        if isinstance(observer, str):
            # Import observer by string name
            from importlib import import_module
            module_path, class_name = observer.rsplit('.', 1)
            module = import_module(module_path)
            observer_class = getattr(module, class_name)
            observer_instance = observer_class()
        elif isinstance(observer, type) and issubclass(observer, ModelObserver):
            observer_instance = observer()
        elif isinstance(observer, ModelObserver):
            observer_instance = observer
        else:
            raise ValueError(f"Invalid observer type: {type(observer)}")
        
        ObserverRegistry.register(cls, observer_instance)
    
    @classmethod
    def get_observers(cls) -> List[ModelObserver]:
        """Get all observers for this model (Laravel 12)."""
        return ObserverRegistry.get_observers(cls)
    
    @classmethod
    def fire_model_event(cls, event: str, instance: 'BaseModel', *args: Any) -> Optional[bool]:
        """Fire a model event (Laravel 12)."""
        return ObserverRegistry.fire_event(instance, event, *args)
    
    @classmethod
    def retrieved(cls, instance: 'BaseModel') -> None:
        """Fire the retrieved event (Laravel 12)."""
        ObserverRegistry.fire_event(instance, 'retrieved')
    
    def fire_retrieved_event(self) -> None:
        """Fire the retrieved event for this instance (Laravel 12)."""
        self.__class__.retrieved(self)
    
    @validate_types
    def append(self, *attributes: str) -> 'BaseModel':
        """Append attributes to the appends list (Laravel 12)."""
        self.__appends__.extend(attributes)
        return self
    
    def hide(self, *attributes: str) -> 'BaseModel':
        """Hide attributes from serialization (Laravel 12)."""
        self.__hidden__.extend(attributes)
        return self
    
    def visible(self, *attributes: str) -> 'BaseModel':
        """Make only specified attributes visible (Laravel 12)."""
        self.__visible__.extend(attributes)
        return self
    
    def make_hidden(self, *attributes: str) -> 'BaseModel':
        """Make attributes hidden for this instance (Laravel 12)."""
        hidden = list(self.__hidden__)
        hidden.extend(attributes)
        self.__hidden__ = hidden
        return self
    
    def make_visible(self, *attributes: str) -> 'BaseModel':
        """Make attributes visible for this instance (Laravel 12)."""
        for attr in attributes:
            if attr in self.__hidden__:
                self.__hidden__.remove(attr)
        return self
    
    def set_hidden(self, hidden: List[str]) -> 'BaseModel':
        """Set the hidden attributes (Laravel 12)."""
        self.__hidden__ = hidden
        return self
    
    def set_visible(self, visible: List[str]) -> 'BaseModel':
        """Set the visible attributes (Laravel 12)."""
        self.__visible__ = visible
        return self
    
    def set_appends(self, appends: List[str]) -> 'BaseModel':
        """Set the appended attributes (Laravel 12)."""
        self.__appends__ = appends
        return self
    
    def get_fillable(self) -> List[str]:
        """Get the fillable attributes (Laravel 12)."""
        return self.__fillable__.copy()
    
    def set_fillable(self, fillable: List[str]) -> 'BaseModel':
        """Set the fillable attributes (Laravel 12)."""
        self.__fillable__ = fillable
        return self
    
    def get_guarded(self) -> List[str]:
        """Get the guarded attributes (Laravel 12)."""
        return self.__guarded__.copy()
    
    def set_guarded(self, guarded: List[str]) -> 'BaseModel':
        """Set the guarded attributes (Laravel 12)."""
        self.__guarded__ = guarded
        return self
    
    # Enhanced relationship and scope methods
    @classmethod
    def define_relationship(cls, name: str, config: RelationshipConfig) -> None:
        """Define an enhanced relationship"""
        cls.__relationship_configs__[name] = config
    
    @classmethod
    def define_scope(cls, name: str, config: ScopeConfig, scope_func: Callable[..., Any]) -> None:
        """Define an enhanced scope"""
        cls.__scope_configs__[name] = config
        # Add scope method to model class
        scope_method_name = f"scope_{name}"
        setattr(cls, scope_method_name, classmethod(scope_func))
    
    @classmethod
    def scope(cls, name: str, description: Optional[str] = None, **kwargs: Any) -> Callable[[Callable], Callable]:
        """Decorator for defining scopes"""
        def decorator(func: Callable) -> Callable:
            config = ScopeConfig(name=name, description=description, **kwargs)
            cls.define_scope(name, config, func)
            return func
        return decorator
    
    @classmethod
    def global_scope(cls, name: str, description: Optional[str] = None, **kwargs: Any) -> Callable[[Callable], Callable]:
        """Decorator for defining global scopes"""
        def decorator(func: Callable) -> Callable:
            config = ScopeConfig(name=name, description=description, global_scope=True, **kwargs)
            cls.define_scope(name, config, func)
            return func
        return decorator
    
    @classmethod
    def get_available_scopes(cls) -> List[str]:
        """Get list of available scopes"""
        return list(cls.__scope_configs__.keys())
    
    @classmethod
    def get_global_scopes(cls) -> List[str]:
        """Get list of global scopes"""
        return [name for name, config in cls.__scope_configs__.items() if config.global_scope]
    
    def get_relationship_metadata(self, relationship_name: str) -> Dict[str, Any]:
        """Get metadata about a relationship"""
        if relationship_name in self.__relationship_configs__:
            config = self.__relationship_configs__[relationship_name]
            return {
                'name': relationship_name,
                'type': config.relation_type.value,
                'related_model': config.related_model,
                'foreign_key': config.foreign_key,
                'local_key': config.local_key,
                'eager_load': config.eager_load,
                'cascade_delete': config.cascade_delete
            }
        return {}
    
    def to_dict_with_relationships(self, include_relationships: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary including relationships"""
        result = self.to_dict()
        
        if include_relationships:
            for rel_name in include_relationships:
                if hasattr(self, rel_name):
                    rel_data = getattr(self, rel_name)
                    if rel_data is not None:
                        if hasattr(rel_data, 'to_dict'):
                            result[rel_name] = rel_data.to_dict()
                        elif isinstance(rel_data, list):
                            result[rel_name] = [item.to_dict() if hasattr(item, 'to_dict') else item for item in rel_data]
                        else:
                            result[rel_name] = rel_data
        
        return result
    
    @hybrid_property
    def relationship_metadata(self) -> Dict[str, Any]:
        """Get enhanced metadata about the model"""
        return {
            'model_class': self.__class__.__name__,
            'relationships': list(self.__relationship_configs__.keys()),
            'scopes': list(self.__scope_configs__.keys()),
            'auto_load_relationships': self.__auto_load_relationships__,
            'relationship_strategies': self.__relationship_strategies__
        }


# Laravel 12 Enhanced Observer System
class ModelObserver(ABC):
    """Base class for Laravel 12 model observers with strict typing."""
    
    def retrieved(self, model: 'BaseModel') -> None:
        """Handle the retrieved event."""
        pass
    
    def creating(self, model: 'BaseModel') -> Optional[bool]:
        """Handle the creating event. Return False to cancel."""
        return None
    
    def created(self, model: 'BaseModel') -> None:
        """Handle the created event."""
        pass
    
    def updating(self, model: 'BaseModel') -> Optional[bool]:
        """Handle the updating event. Return False to cancel."""
        return None
    
    def updated(self, model: 'BaseModel') -> None:
        """Handle the updated event."""
        pass
    
    def saving(self, model: 'BaseModel') -> Optional[bool]:
        """Handle the saving event. Return False to cancel."""
        return None
    
    def saved(self, model: 'BaseModel') -> None:
        """Handle the saved event."""
        pass
    
    def deleting(self, model: 'BaseModel') -> Optional[bool]:
        """Handle the deleting event. Return False to cancel."""
        return None
    
    def deleted(self, model: 'BaseModel') -> None:
        """Handle the deleted event."""
        pass
    
    def restoring(self, model: 'BaseModel') -> Optional[bool]:
        """Handle the restoring event. Return False to cancel."""
        return None
    
    def restored(self, model: 'BaseModel') -> None:
        """Handle the restored event."""
        pass
    
    def replicating(self, model: 'BaseModel') -> None:
        """Handle the replicating event."""
        pass


# Laravel 12 Observer Registry
class ObserverRegistry:
    """Registry for model observers (Laravel 12)."""
    
    _observers: ClassVar[Dict[Type['BaseModel'], List[ModelObserver]]] = {}
    
    @classmethod
    def register(cls, model_class: Type['BaseModel'], observer: ModelObserver) -> None:
        """Register an observer for a model class."""
        if model_class not in cls._observers:
            cls._observers[model_class] = []
        cls._observers[model_class].append(observer)
    
    @classmethod
    def get_observers(cls, model_class: Type['BaseModel']) -> List[ModelObserver]:
        """Get observers for a model class."""
        observers = []
        # Check for observers registered for this class and its parents
        for registered_class, class_observers in cls._observers.items():
            if issubclass(model_class, registered_class):
                observers.extend(class_observers)
        return observers
    
    @classmethod
    def fire_event(cls, model: 'BaseModel', event: str, *args: Any) -> Optional[bool]:
        """Fire an event to all observers."""
        observers = cls.get_observers(type(model))
        for observer in observers:
            if hasattr(observer, event):
                method = getattr(observer, event)
                result = method(model, *args)
                # If any observer returns False, cancel the operation
                if result is False:
                    return False
        return None


# Laravel 12 Enhanced Event Listeners with Observers
@event.listens_for(BaseModel, 'before_insert', propagate=True)
def generate_ulid_before_insert(mapper: Any, connection: Any, target: BaseModel) -> None:
    """Generate ULID for new instances if not provided."""
    del mapper, connection  # Unused parameters required by SQLAlchemy
    
    # Fire creating event
    result = ObserverRegistry.fire_event(target, 'creating')
    if result is False:
        raise ValueError("Model creation was cancelled by observer")
    
    # Fire saving event
    result = ObserverRegistry.fire_event(target, 'saving')
    if result is False:
        raise ValueError("Model saving was cancelled by observer")
    
    if not target.id:
        target.id = generate_ulid()
    
    # Laravel 12: Mark as recently created
    target._was_recently_created = True
    target._exists = True


@event.listens_for(BaseModel, 'before_update', propagate=True)
def sync_changes_before_update(mapper: Any, connection: Any, target: BaseModel) -> None:
    """Sync changes before update (Laravel 12)."""
    del mapper, connection  # Unused parameters
    
    # Fire updating event
    result = ObserverRegistry.fire_event(target, 'updating')
    if result is False:
        raise ValueError("Model update was cancelled by observer")
    
    # Fire saving event
    result = ObserverRegistry.fire_event(target, 'saving')
    if result is False:
        raise ValueError("Model saving was cancelled by observer")
    
    target._was_recently_created = False
    
    # Touch parent models if configured
    if target.__touches__:
        target.touches(*target.__touches__)


@event.listens_for(BaseModel, 'after_insert', propagate=True)
def sync_original_after_insert(mapper: Any, connection: Any, target: BaseModel) -> None:
    """Sync original attributes after insert (Laravel 12)."""
    del mapper, connection  # Unused parameters
    target._sync_original()
    
    # Fire created event
    ObserverRegistry.fire_event(target, 'created')
    
    # Fire saved event  
    ObserverRegistry.fire_event(target, 'saved')


@event.listens_for(BaseModel, 'after_update', propagate=True)
def sync_original_after_update(mapper: Any, connection: Any, target: BaseModel) -> None:
    """Sync original attributes after update (Laravel 12)."""
    del mapper, connection  # Unused parameters
    target._sync_original()
    
    # Fire updated event
    ObserverRegistry.fire_event(target, 'updated')
    
    # Fire saved event
    ObserverRegistry.fire_event(target, 'saved')


@event.listens_for(BaseModel, 'before_delete', propagate=True)
def handle_before_delete(mapper: Any, connection: Any, target: BaseModel) -> None:
    """Handle before delete event (Laravel 12)."""
    del mapper, connection  # Unused parameters
    
    # Fire deleting event
    result = ObserverRegistry.fire_event(target, 'deleting')
    if result is False:
        raise ValueError("Model deletion was cancelled by observer")


@event.listens_for(BaseModel, 'after_delete', propagate=True)
def handle_after_delete(mapper: Any, connection: Any, target: BaseModel) -> None:
    """Handle after delete event (Laravel 12)."""
    del mapper, connection  # Unused parameters
    
    # Fire deleted event
    ObserverRegistry.fire_event(target, 'deleted')


# Laravel 12 Custom Decorators for Models
def computed_accessor(func: Callable[['BaseModel'], Any]) -> Callable[['BaseModel'], Any]:
    """Decorator for computed accessors (Laravel 12)."""
    def wrapper(self: 'BaseModel') -> Any:
        # Cache computed values
        cache_key = f"computed_{func.__name__}"
        if cache_key not in self._relations_cache:
            self._relations_cache[cache_key] = func(self)
        return self._relations_cache[cache_key]
    
    # Register the accessor
    def register_accessor(cls: Type['BaseModel']) -> None:
        cls.__computed_accessors__[func.__name__] = wrapper
    
    # This would be called during class creation
    register_accessor(BaseModel)
    return wrapper


def lazy_accessor(func: Callable[['BaseModel'], Any]) -> Callable[['BaseModel'], Any]:
    """Decorator for lazy accessors (Laravel 12)."""
    def wrapper(self: 'BaseModel') -> Any:
        cache_key = f"lazy_{func.__name__}"
        if cache_key not in self._relations_cache:
            self._relations_cache[cache_key] = func(self)
        return self._relations_cache[cache_key]
    
    # Register the lazy accessor
    def register_lazy_accessor(cls: Type['BaseModel']) -> None:
        cls.__lazy_accessors__[func.__name__] = wrapper
    
    register_lazy_accessor(BaseModel)
    return wrapper


def model_cast(cast_type: Union[str, Type[CastInterface]]) -> Callable[[Callable], Callable]:
    """Decorator for model attribute casting (Laravel 12)."""
    def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
        def wrapper(value: Any) -> Any:
            if isinstance(cast_type, str):
                # Use built-in casting
                model = BaseModel()
                return model._cast_built_in_type(value, cast_type)
            elif isinstance(cast_type, type) and issubclass(cast_type, CastInterface):
                # Use custom cast interface
                cast_instance = cast_type()
                model = BaseModel()
                return cast_instance.get(model, func.__name__, value, {})
            else:
                return func(value)
        return wrapper
    return decorator


# Laravel 12 Model Factory Implementation
class ModelFactory(Generic[T]):
    """Laravel 12 model factory with strict typing."""
    
    def __init__(self, model_class: Type[T]) -> None:
        self.model_class = model_class
        self._count = 1
        self._states: List[str] = []
        self._attributes: Dict[str, Any] = {}
        self._after_making: List[Callable[[T], None]] = []
        self._after_creating: List[Callable[[T], None]] = []
    
    def definition(self) -> Dict[str, Any]:
        """Define the default attribute values."""
        return {}
    
    def count(self, count: int) -> Self:
        """Set the number of instances to create."""
        self._count = count
        return self
    
    def state(self, state: str, *states: str) -> Self:
        """Apply factory states."""
        self._states.extend([state] + list(states))
        return self
    
    def with_attributes(self, **attributes: Any) -> Self:
        """Override specific attributes."""
        self._attributes.update(attributes)
        return self
    
    def after_making(self, callback: Callable[[T], None]) -> Self:
        """Add callback to run after making."""
        self._after_making.append(callback)
        return self
    
    def after_creating(self, callback: Callable[[T], None]) -> Self:
        """Add callback to run after creating."""
        self._after_creating.append(callback)
        return self
    
    def make(self, attributes: Optional[Dict[str, Any]] = None) -> Union[T, List[T]]:
        """Make model instances without persisting."""
        if attributes is None:
            attributes = {}
        
        instances = []
        for _ in range(self._count):
            # Combine definition, states, and override attributes
            instance_attributes = {}
            instance_attributes.update(self.definition())
            
            # Apply states
            for state in self._states:
                if hasattr(self, f"state_{state}"):
                    state_method = getattr(self, f"state_{state}")
                    instance_attributes.update(state_method())
            
            instance_attributes.update(self._attributes)
            instance_attributes.update(attributes)
            
            # Create instance
            instance = self.model_class(**instance_attributes)
            
            # Run after making callbacks
            for callback in self._after_making:
                callback(instance)
            
            instances.append(instance)
        
        return instances[0] if self._count == 1 else instances
    
    def create(self, attributes: Optional[Dict[str, Any]] = None, session: Optional[Session] = None) -> Union[T, List[T]]:
        """Create and persist model instances."""
        instances = self.make(attributes)
        if not isinstance(instances, list):
            instances = [instances]
        
        if session is None:
            from app.Support.ServiceContainer import container
            session = container.make('db.session')
        
        for instance in instances:
            session.add(instance)
            # Run after creating callbacks
            for callback in self._after_creating:
                callback(instance)
        
        session.commit()
        
        return instances[0] if self._count == 1 else instances


# Laravel 12 Enhanced Query Builder Forward Declaration
class QueryBuilder(Generic[T]):
    """Enhanced query builder for Laravel 12 with strict typing."""
    pass  # Implementation would be in separate file


# Export Laravel 12 enhanced model functionality
__all__ = [
    'BaseModel',
    'StrictConfig',
    'CastType',
    'CastInterface',
    'InboundCastInterface',
    'CastsInboundAttributes',
    'AsArrayObject',
    'AsCollection',
    'EncryptedCast',
    'RelationType',
    'RelationshipDefinition',
    'SoftDeleteMixin',
    'TimestampMixin',
    'computed_accessor',
    'lazy_accessor',
    'model_cast',
    'ModelFactory',
    'ModelFactoryProtocol',
    'ModelBuilderProtocol',
    'QueryBuilder',
    'ModelObserver',
    'ObserverRegistry',
    'AsStringable',
    'AsValueObject', 
    'AsEnumCollection',
    'RelationshipConfig',
    'ScopeConfig',
    'has_one',
    'has_many',
    'belongs_to',
    'belongs_to_many',
]


# Convenience functions for common relationship patterns
def has_one(related_model: str, foreign_key: Optional[str] = None, local_key: Optional[str] = None, **kwargs: Any) -> RelationshipConfig:
    """Create a has-one relationship configuration"""
    return RelationshipConfig(
        relation_type=RelationType.HAS_ONE,
        related_model=related_model,
        foreign_key=foreign_key,
        local_key=local_key,
        **kwargs
    )


def has_many(related_model: str, foreign_key: Optional[str] = None, local_key: Optional[str] = None, **kwargs: Any) -> RelationshipConfig:
    """Create a has-many relationship configuration"""
    return RelationshipConfig(
        relation_type=RelationType.HAS_MANY,
        related_model=related_model,
        foreign_key=foreign_key,
        local_key=local_key,
        **kwargs
    )


def belongs_to(related_model: str, foreign_key: Optional[str] = None, local_key: Optional[str] = None, **kwargs: Any) -> RelationshipConfig:
    """Create a belongs-to relationship configuration"""
    return RelationshipConfig(
        relation_type=RelationType.BELONGS_TO,
        related_model=related_model,
        foreign_key=foreign_key,
        local_key=local_key,
        **kwargs
    )


def belongs_to_many(related_model: str, pivot_table: Optional[str] = None, foreign_key: Optional[str] = None, local_key: Optional[str] = None, **kwargs: Any) -> RelationshipConfig:
    """Create a belongs-to-many relationship configuration"""
    return RelationshipConfig(
        relation_type=RelationType.BELONGS_TO_MANY,
        related_model=related_model,
        pivot_table=pivot_table,
        foreign_key=foreign_key,
        local_key=local_key,
        **kwargs
    )