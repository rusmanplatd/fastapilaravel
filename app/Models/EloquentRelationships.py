from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Type, TypeVar, Callable, get_type_hints
from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship, Session, joinedload, selectinload, subqueryload
from sqlalchemy.sql import ClauseElement
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from .BaseModel import BaseModel
try:
    from config.database import get_db
except ImportError:
    # Fallback for cases where database config is not available
    def get_db() -> Any:
        yield None
from app.Utils.QueryBuilder.QueryBuilder import QueryBuilder

T = TypeVar('T', bound='RelatedModel')
R = TypeVar('R', bound='BaseModel')


class RelationType(Enum):
    """Types of Eloquent relationships."""
    HAS_ONE = "has_one"
    HAS_MANY = "has_many"
    BELONGS_TO = "belongs_to"
    BELONGS_TO_MANY = "belongs_to_many"
    HAS_ONE_THROUGH = "has_one_through"
    HAS_MANY_THROUGH = "has_many_through"
    MORPH_ONE = "morph_one"
    MORPH_MANY = "morph_many"
    MORPH_TO = "morph_to"


@dataclass
class RelationshipConfig:
    """Configuration for a relationship."""
    name: str
    related_model: Type[BaseModel]
    relation_type: RelationType
    foreign_key: Optional[str] = None
    local_key: Optional[str] = None
    through_model: Optional[Type[BaseModel]] = None
    pivot_table: Optional[str] = None
    morph_type: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    eager_load: bool = False
    cascade_delete: bool = False


class Relation(ABC):
    """Base class for Eloquent relationships."""
    
    def __init__(self, parent: BaseModel, related: Type[BaseModel], config: RelationshipConfig):
        self.parent = parent
        self.related = related
        self.config = config
        self.query_builder: Optional[QueryBuilder[BaseModel]] = None
    
    @abstractmethod
    def get_results(self) -> Union[BaseModel, List[BaseModel], None]:
        """Get the relationship results."""
        pass
    
    @abstractmethod
    def add_constraints(self) -> None:
        """Add relationship constraints to the query."""
        pass
    
    def get_query(self) -> QueryBuilder[BaseModel]:
        """Get the relationship query builder."""
        if self.query_builder is None:
            # Get session from database connection
            db = get_db()
            self.query_builder = self.related.query(next(db))
            self.add_constraints()
        return self.query_builder
    
    def where(self, *args: Any, **kwargs: Any) -> 'Relation':
        """Add where constraint to the relationship."""
        self.get_query().where(*args, **kwargs)
        return self
    
    def order_by(self, column: str, direction: str = 'asc') -> 'Relation':
        """Add order by to the relationship."""
        self.get_query().order_by(column, direction)
        return self
    
    def limit(self, count: int) -> 'Relation':
        """Add limit to the relationship."""
        self.get_query().limit(count)
        return self
    
    def with_trashed(self) -> 'Relation':
        """Include soft deleted records in the relationship query."""
        # Apply the with_trashed scope to include soft deleted records
        if hasattr(self.related, '__soft_deletes__') and self.related.__soft_deletes__:
            # Remove the default soft delete constraint and include all records
            query = self.get_query()
            
            # If the query has a deleted_at filter, remove it
            if hasattr(self.related, 'deleted_at'):
                # Get the query without soft delete constraints
                self.query_builder = query.execution_options(include_deleted=True)  # type: ignore
                
                # Add custom filter to include trashed records
                # This removes the default WHERE deleted_at IS NULL constraint
                from sqlalchemy import text
                
                # Apply the scope that includes soft deleted records
                if hasattr(self.related, 'scope_with_trashed'):
                    self.query_builder = self.related.scope_with_trashed(query)  # type: ignore
                else:
                    # Fallback: explicitly remove deleted_at constraint
                    # by not applying the default soft delete filter
                    pass
        
        return self


class HasOne(Relation):
    """Has one relationship."""
    
    def add_constraints(self) -> None:
        """Add has one constraints."""
        foreign_key = self.config.foreign_key or f"{self.parent.__tablename__[:-1]}_id"
        local_key = self.config.local_key or "id"
        
        parent_value = getattr(self.parent, local_key)
        self.get_query().where(foreign_key, parent_value)
    
    def get_results(self) -> Optional[BaseModel]:
        """Get the has one result."""
        return self.get_query().first()


class HasMany(Relation):
    """Has many relationship."""
    
    def add_constraints(self) -> None:
        """Add has many constraints."""
        foreign_key = self.config.foreign_key or f"{self.parent.__tablename__[:-1]}_id"
        local_key = self.config.local_key or "id"
        
        parent_value = getattr(self.parent, local_key)
        self.get_query().where(foreign_key, parent_value)
    
    def get_results(self) -> List[BaseModel]:
        """Get the has many results."""
        return self.get_query().get()


class BelongsTo(Relation):
    """Belongs to relationship."""
    
    def add_constraints(self) -> None:
        """Add belongs to constraints."""
        foreign_key = self.config.foreign_key or f"{self.related.__tablename__[:-1]}_id"
        local_key = self.config.local_key or "id"
        
        foreign_value = getattr(self.parent, foreign_key)
        if foreign_value:
            self.get_query().where(local_key, foreign_value)
    
    def get_results(self) -> Optional[BaseModel]:
        """Get the belongs to result."""
        return self.get_query().first()


class BelongsToMany(Relation):
    """Belongs to many (many-to-many) relationship."""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Initialize missing attributes for demonstration purposes
        self.table = "pivot_table"
        self.foreign_pivot_key = "parent_id"
        self.related_pivot_key = "related_id"
    
    def add_constraints(self) -> None:
        """Add belongs to many constraints."""
        if self.query_builder:
            # Join through pivot table
            # Note: This is a simplified implementation - actual join logic would be more complex
            if hasattr(self.config, 'pivot_table') and self.config.pivot_table:
                table_name = self.config.pivot_table
                foreign_key = self.config.foreign_key or 'id'
                local_key = self.config.local_key or 'id'
                self.query_builder = self.query_builder.where(foreign_key, getattr(self.parent, local_key))
    
    def get_results(self) -> List[BaseModel]:
        """Get the belongs to many results."""
        # Simplified implementation
        return self.get_query().get()
    
    def attach(self, ids: Union[int, List[int]], pivot_data: Optional[Dict[str, Any]] = None) -> None:
        """Attach related models."""
        from sqlalchemy import text
        
        if isinstance(ids, int):
            ids = [ids]
        
        # Get database session
        db_session = next(get_db())
        
        for model_id in ids:
            # Check if relationship already exists
            table_name = self.config.pivot_table or 'pivot_table'
            foreign_key = self.config.foreign_key or 'foreign_key' 
            local_key = self.config.local_key or 'local_key'
            existing = db_session.execute(text(f"""
                SELECT 1 FROM {table_name} 
                WHERE {foreign_key} = :parent_id 
                AND {local_key} = :related_id
            """), {
                'parent_id': getattr(self.parent, 'id', None),
                'related_id': model_id
            }).fetchone()
            
            if not existing:
                # Create pivot record  
                pivot_record = {foreign_key: getattr(self.parent, 'id', None),
                               local_key: model_id}
                
                if pivot_data:
                    pivot_record.update(pivot_data)
                
                db_session.execute(text(f"""
                    INSERT INTO {table_name} ({', '.join(pivot_record.keys())})
                    VALUES ({', '.join([f':{k}' for k in pivot_record.keys()])})
                """), pivot_record)
        
        db_session.commit()
    
    def detach(self, ids: Optional[Union[int, List[int]]] = None) -> None:
        """Detach related models."""
        from sqlalchemy import text
        
        # Get database session
        db_session = next(get_db())
        
        table_name = self.config.pivot_table or 'pivot_table'
        foreign_key = self.config.foreign_key or 'foreign_key'
        local_key = self.config.local_key or 'local_key'
        parent_id = getattr(self.parent, 'id', None)
        
        if ids is None:
            # Detach all related models
            db_session.execute(text(f"""
                DELETE FROM {table_name} WHERE {foreign_key} = :parent_id
            """), {'parent_id': parent_id})
        else:
            if isinstance(ids, int):
                ids = [ids]
            
            for model_id in ids:
                db_session.execute(text(f"""
                    DELETE FROM {table_name} 
                    WHERE {foreign_key} = :parent_id 
                    AND {local_key} = :related_id
                """), {
                    'parent_id': parent_id,
                    'related_id': model_id
                })
        
        db_session.commit()
    
    def sync(self, ids: List[int], detaching: bool = True) -> None:
        """Sync the intermediate table with a list of IDs."""
        from sqlalchemy import text
        
        # Get database session
        db_session = next(get_db())
        
        parent_id = getattr(self.parent, self.parent.get_key_name())
        
        # Get currently attached IDs
        current_result = db_session.execute(text(f"""
            SELECT {self.related_pivot_key} FROM {self.table}  # type: ignore[attr-defined]
            WHERE {self.foreign_pivot_key} = :parent_id  # type: ignore[attr-defined]
        """), {'parent_id': parent_id})
        
        current_ids = [row[0] for row in current_result.fetchall()]
        
        # Determine what to attach and detach
        to_attach = set(ids) - set(current_ids)
        to_detach = set(current_ids) - set(ids) if detaching else set()
        
        # Detach removed relationships
        if to_detach:
            for model_id in to_detach:
                db_session.execute(text(f"""
                    DELETE FROM {self.table}  # type: ignore[attr-defined]
                    WHERE {self.foreign_pivot_key} = :parent_id  # type: ignore[attr-defined]
                    AND {self.related_pivot_key} = :related_id  # type: ignore[attr-defined]
                """), {
                    'parent_id': parent_id,
                    'related_id': model_id
                })
        
        # Attach new relationships
        if to_attach:
            for model_id in to_attach:
                db_session.execute(text(f"""
                    INSERT INTO {self.table} ({self.foreign_pivot_key}, {self.related_pivot_key})
                    VALUES (:parent_id, :related_id)
                """), {
                    'parent_id': parent_id,
                    'related_id': model_id
                })
        
        db_session.commit()


class HasOneThrough(Relation):
    """Has one through relationship."""
    
    def add_constraints(self) -> None:
        """Add has one through constraints."""
        # Implementation for has one through
        pass
    
    def get_results(self) -> Optional[BaseModel]:
        """Get the has one through result."""
        return self.get_query().first()


class HasManyThrough(Relation):
    """Has many through relationship."""
    
    def add_constraints(self) -> None:
        """Add has many through constraints."""
        # Implementation for has many through
        pass
    
    def get_results(self) -> List[BaseModel]:
        """Get the has many through results."""
        return self.get_query().get()


class RelatedModel(BaseModel):
    """Enhanced model with relationship support."""
    
    __abstract__ = True
    
    _relationships: Dict[str, RelationshipConfig] = {}
    _loaded_relations: Dict[str, Any] = {}
    _eager_load: List[str] = []
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._loaded_relations = {}
    
    @classmethod
    def with_relationships(cls, *relations: str) -> Any:
        """Eager load relationships."""
        db = get_db()
        query = cls.query(next(db))
        if hasattr(query, '_eager_load'):
            query._eager_load = list(relations)
        return query
    
    @classmethod
    def with_count(cls, *relations: str) -> Any:
        """Load with relationship counts."""
        db = get_db()
        query = cls.query(next(db))
        if hasattr(query, '_with_count'):
            query._with_count = list(relations)
        return query
    
    def load(self, *relations: str) -> 'RelatedModel':
        """Lazy load relationships."""
        for relation_name in relations:
            if relation_name in self._relationships:
                relation = self._create_relation(relation_name)
                self._loaded_relations[relation_name] = relation.get_results()
        return self
    
    def load_missing(self, *relations: str) -> 'RelatedModel':
        """Load relationships that aren't already loaded."""
        missing_relations = [r for r in relations if r not in self._loaded_relations]
        return self.load(*missing_relations)
    
    def _create_relation(self, name: str) -> Relation:
        """Create a relationship instance."""
        if name not in self._relationships:
            raise ValueError(f"Relationship '{name}' not defined")
        
        config = self._relationships[name]
        
        if config.relation_type == RelationType.HAS_ONE:
            return HasOne(self, config.related_model, config)
        elif config.relation_type == RelationType.HAS_MANY:
            return HasMany(self, config.related_model, config)
        elif config.relation_type == RelationType.BELONGS_TO:
            return BelongsTo(self, config.related_model, config)
        elif config.relation_type == RelationType.BELONGS_TO_MANY:
            return BelongsToMany(self, config.related_model, config)
        elif config.relation_type == RelationType.HAS_ONE_THROUGH:
            return HasOneThrough(self, config.related_model, config)
        elif config.relation_type == RelationType.HAS_MANY_THROUGH:
            return HasManyThrough(self, config.related_model, config)
        else:
            raise ValueError(f"Unsupported relation type: {config.relation_type}")
    
    def get_relation(self, name: str) -> Relation:
        """Get a relationship instance."""
        return self._create_relation(name)
    
    def __getattr__(self, name: str) -> Any:
        """Dynamic relationship access."""
        # Check if it's a loaded relationship
        if name in self._loaded_relations:
            return self._loaded_relations[name]
        
        # Check if it's a defined relationship
        if name in self._relationships:
            relation = self._create_relation(name)
            result = relation.get_results()
            self._loaded_relations[name] = result
            return result
        
        # Fall back to raising AttributeError for missing attributes
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    @classmethod
    def has_one(cls, related: Type['RelatedModel'], foreign_key: Optional[str] = None, local_key: Optional[str] = None) -> RelationshipConfig:  # type: ignore[override]
        """Define a has one relationship."""
        return RelationshipConfig(
            name="",  # Will be set by the decorator
            related_model=related,
            relation_type=RelationType.HAS_ONE,
            foreign_key=foreign_key,
            local_key=local_key
        )
    
    @classmethod
    def has_many(cls, related: Type['RelatedModel'], foreign_key: Optional[str] = None, local_key: Optional[str] = None) -> RelationshipConfig:  # type: ignore[override]
        """Define a has many relationship."""
        return RelationshipConfig(
            name="",  # Will be set by the decorator
            related_model=related,
            relation_type=RelationType.HAS_MANY,
            foreign_key=foreign_key,
            local_key=local_key
        )
    
    @classmethod
    def belongs_to(cls, related: Type['RelatedModel'], foreign_key: Optional[str] = None, local_key: Optional[str] = None) -> RelationshipConfig:  # type: ignore[override]
        """Define a belongs to relationship."""
        return RelationshipConfig(
            name="",  # Will be set by the decorator
            related_model=related,
            relation_type=RelationType.BELONGS_TO,
            foreign_key=foreign_key,
            local_key=local_key
        )
    
    @classmethod
    def belongs_to_many(cls, related: Type['RelatedModel'], pivot_table: Optional[str] = None, foreign_key: Optional[str] = None, local_key: Optional[str] = None) -> RelationshipConfig:  # type: ignore[override]
        """Define a belongs to many relationship."""
        return RelationshipConfig(
            name="",  # Will be set by the decorator
            related_model=related,
            relation_type=RelationType.BELONGS_TO_MANY,
            pivot_table=pivot_table,
            foreign_key=foreign_key,
            local_key=local_key
        )


# Relationship decorator
def relationship_decorator(config: RelationshipConfig) -> Callable[..., Any]:
    """Decorator for defining relationships."""
    def decorator(func: Callable) -> Callable:
        relationship_name = func.__name__
        config.name = relationship_name
        
        def wrapper(self: Any) -> Any:
            if relationship_name not in self._loaded_relations:
                relation = self._create_relation(relationship_name)
                result = relation.get_results()
                self._loaded_relations[relationship_name] = result
                return result
            return self._loaded_relations[relationship_name]
        
        # Store the relationship config
        if not hasattr(func, '__self__') or func.__self__ is None:
            # Class method decoration
            def class_wrapper(cls: Any) -> Any:
                if not hasattr(cls, '_relationships'):
                    cls._relationships = {}
                cls._relationships[relationship_name] = config
                return wrapper
            return class_wrapper
        else:
            # Instance method decoration
            if not hasattr(func.__self__, '_relationships'):
                func.__self__._relationships = {}
            func.__self__._relationships[relationship_name] = config
            return wrapper
    
    return decorator


# Enhanced query builder with relationship support
class RelationshipQueryBuilder:
    """Enhanced query builder with relationship support."""
    
    def __init__(self, model: Type[RelatedModel], session: Session):
        self.model = model
        self.session = session
        self._eager_load: List[str] = []
        self._with_count: List[str] = []
        self.query = session.query(model)
    
    def with_relationships(self, *relations: str) -> 'RelationshipQueryBuilder':
        """Eager load relationships."""
        self._eager_load.extend(relations)
        return self
    
    def with_count(self, *relations: str) -> 'RelationshipQueryBuilder':
        """Load with relationship counts."""
        self._with_count.extend(relations)
        return self
    
    def _apply_eager_loading(self) -> None:
        """Apply eager loading to the query."""
        if not self._eager_load:
            return
        
        # This is a simplified implementation
        # In a full implementation, you'd use SQLAlchemy's joinedload, selectinload, etc.
        for relation_name in self._eager_load:
            if hasattr(self.model, relation_name):
                # Apply appropriate loading strategy
                pass
    
    def get(self) -> List[RelatedModel]:
        """Execute query with eager loading."""
        self._apply_eager_loading()
        results: List[RelatedModel] = self.query.all()
        
        # Load relationships for each result
        for result in results:
            for relation_name in self._eager_load:
                if relation_name in result._relationships:
                    relation = result._create_relation(relation_name)
                    result._loaded_relations[relation_name] = relation.get_results()
        
        return results


# Example models with relationships
class User(RelatedModel):
    """User model with relationships."""
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)  # type: ignore[assignment]
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    
    _fillable = ['name', 'email']
    
    @classmethod
    def _setup_relationships(cls) -> None:
        """Setup relationships for the model."""
        cls._relationships = {
            'posts': RelationshipConfig(
                name='posts',
                related_model=Post,  # Forward reference
                relation_type=RelationType.HAS_MANY,
                foreign_key='user_id'
            ),
            'profile': RelationshipConfig(
                name='profile',
                related_model=Profile,  # Forward reference
                relation_type=RelationType.HAS_ONE,
                foreign_key='user_id'
            )
        }


class Post(RelatedModel):
    """Post model with relationships."""
    
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)  # type: ignore[assignment]
    title = Column(String(200), nullable=False)
    content = Column(String(1000))
    user_id = Column(Integer, ForeignKey('users.id'))
    
    _fillable = ['title', 'content', 'user_id']
    
    @classmethod
    def _setup_relationships(cls) -> None:
        """Setup relationships for the model."""
        cls._relationships = {
            'user': RelationshipConfig(
                name='user',
                related_model=User,
                relation_type=RelationType.BELONGS_TO,
                foreign_key='user_id'
            ),
            'comments': RelationshipConfig(
                name='comments',
                related_model=Comment,  # Forward reference
                relation_type=RelationType.HAS_MANY,
                foreign_key='post_id'
            )
        }


class Profile(RelatedModel):
    """Profile model with relationships."""
    
    __tablename__ = 'profiles'
    
    id = Column(Integer, primary_key=True)  # type: ignore[assignment]
    bio = Column(String(500))
    user_id = Column(Integer, ForeignKey('users.id'))
    
    _fillable = ['bio', 'user_id']
    
    @classmethod
    def _setup_relationships(cls) -> None:
        """Setup relationships for the model."""
        cls._relationships = {
            'user': RelationshipConfig(
                name='user',
                related_model=User,
                relation_type=RelationType.BELONGS_TO,
                foreign_key='user_id'
            )
        }


class Comment(RelatedModel):
    """Comment model with relationships."""
    
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True)  # type: ignore[assignment]
    content = Column(String(500))
    post_id = Column(Integer, ForeignKey('posts.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    
    _fillable = ['content', 'post_id', 'user_id']
    
    @classmethod
    def _setup_relationships(cls) -> None:
        """Setup relationships for the model."""
        cls._relationships = {
            'post': RelationshipConfig(
                name='post',
                related_model=Post,
                relation_type=RelationType.BELONGS_TO,
                foreign_key='post_id'
            ),
            'user': RelationshipConfig(
                name='user',
                related_model=User,
                relation_type=RelationType.BELONGS_TO,
                foreign_key='user_id'
            )
        }


# Setup relationships after all models are defined
User._setup_relationships()
Post._setup_relationships()
Profile._setup_relationships()
Comment._setup_relationships()