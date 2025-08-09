from __future__ import annotations

from typing import Any, Dict, List, Optional, TypeVar, Generic, Union, Type, Iterator, TYPE_CHECKING
from sqlalchemy.orm import Session, Query, selectinload, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.exc import NoResultFound
from app.Contracts.Repository.BaseRepositoryInterface import BaseRepositoryInterface
from app.Pagination.LengthAwarePaginator import LengthAwarePaginator

if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel

T = TypeVar('T')


class RepositoryException(Exception):
    """Repository-specific exception."""
    pass


class ModelNotFoundException(RepositoryException):
    """Exception raised when a model is not found."""
    pass


class BaseRepository(BaseRepositoryInterface[T], Generic[T]):
    """
    Base repository implementation providing common data access operations.
    
    This repository follows Laravel's repository pattern and provides
    concrete implementations for database operations.
    """
    
    def __init__(self, db: Session, model_class: Type[T]) -> None:
        self.db = db
        self.model_class = model_class
        self._query: Optional[Query[T]] = None
        self._relations: List[str] = []
        self._reset_query()
    
    def _reset_query(self) -> None:
        """Reset the internal query builder."""
        self._query = self.db.query(self.model_class)
        self._relations = []
    
    def _get_query(self) -> Query[T]:
        """Get the current query or create a new one."""
        if self._query is None:
            self._reset_query()
        return self._query
    
    def find(self, id: Union[int, str]) -> Optional[T]:
        """Find a record by its primary key."""
        query = self._get_query()
        if self._relations:
            for relation in self._relations:
                query = query.options(selectinload(getattr(self.model_class, relation)))
        return query.filter(self.model_class.id == id).first()
    
    def find_or_fail(self, id: Union[int, str]) -> T:
        """Find a record by its primary key or raise an exception."""
        result = self.find(id)
        if result is None:
            raise ModelNotFoundException(f"{self.model_class.__name__} with id {id} not found")
        return result
    
    def find_many(self, ids: List[Union[int, str]]) -> List[T]:
        """Find multiple records by their primary keys."""
        query = self._get_query()
        if self._relations:
            for relation in self._relations:
                query = query.options(selectinload(getattr(self.model_class, relation)))
        return query.filter(self.model_class.id.in_(ids)).all()
    
    def all(self) -> List[T]:
        """Get all records."""
        query = self._get_query()
        if self._relations:
            for relation in self._relations:
                query = query.options(selectinload(getattr(self.model_class, relation)))
        return query.all()
    
    def paginate(self, page: int = 1, per_page: int = 15) -> Dict[str, Any]:
        """Paginate records."""
        query = self._get_query()
        if self._relations:
            for relation in self._relations:
                query = query.options(selectinload(getattr(self.model_class, relation)))
        
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        paginator = LengthAwarePaginator(
            items=items,
            total=total,
            per_page=per_page,
            current_page=page
        )
        
        return {
            'data': items,
            'pagination': {
                'current_page': paginator.current_page,
                'last_page': paginator.last_page,
                'per_page': paginator.per_page,
                'total': paginator.total,
                'from': paginator.from_item,
                'to': paginator.to_item
            }
        }
    
    def create(self, data: Dict[str, Any]) -> T:
        """Create a new record."""
        instance = self.model_class(**data)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    def update(self, id: Union[int, str], data: Dict[str, Any]) -> T:
        """Update an existing record."""
        instance = self.find_or_fail(id)
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    def delete(self, id: Union[int, str]) -> bool:
        """Delete a record."""
        instance = self.find_or_fail(id)
        self.db.delete(instance)
        self.db.commit()
        return True
    
    def where(self, column: str, operator: str = '=', value: Any = None) -> 'BaseRepository[T]':
        """Add a where clause to the query."""
        if not hasattr(self.model_class, column):
            raise ValueError(f"Column '{column}' does not exist on model {self.model_class.__name__}")
        
        column_attr = getattr(self.model_class, column)
        
        if operator == '=':
            self._query = self._get_query().filter(column_attr == value)
        elif operator == '!=':
            self._query = self._get_query().filter(column_attr != value)
        elif operator == '>':
            self._query = self._get_query().filter(column_attr > value)
        elif operator == '>=':
            self._query = self._get_query().filter(column_attr >= value)
        elif operator == '<':
            self._query = self._get_query().filter(column_attr < value)
        elif operator == '<=':
            self._query = self._get_query().filter(column_attr <= value)
        elif operator == 'like':
            self._query = self._get_query().filter(column_attr.like(f"%{value}%"))
        elif operator == 'ilike':
            self._query = self._get_query().filter(column_attr.ilike(f"%{value}%"))
        else:
            raise ValueError(f"Unsupported operator: {operator}")
        
        return self
    
    def where_in(self, column: str, values: List[Any]) -> 'BaseRepository[T]':
        """Add a where in clause to the query."""
        if not hasattr(self.model_class, column):
            raise ValueError(f"Column '{column}' does not exist on model {self.model_class.__name__}")
        
        column_attr = getattr(self.model_class, column)
        self._query = self._get_query().filter(column_attr.in_(values))
        return self
    
    def where_not_in(self, column: str, values: List[Any]) -> 'BaseRepository[T]':
        """Add a where not in clause to the query."""
        if not hasattr(self.model_class, column):
            raise ValueError(f"Column '{column}' does not exist on model {self.model_class.__name__}")
        
        column_attr = getattr(self.model_class, column)
        self._query = self._get_query().filter(~column_attr.in_(values))
        return self
    
    def where_null(self, column: str) -> 'BaseRepository[T]':
        """Add a where null clause to the query."""
        if not hasattr(self.model_class, column):
            raise ValueError(f"Column '{column}' does not exist on model {self.model_class.__name__}")
        
        column_attr = getattr(self.model_class, column)
        self._query = self._get_query().filter(column_attr.is_(None))
        return self
    
    def where_not_null(self, column: str) -> 'BaseRepository[T]':
        """Add a where not null clause to the query."""
        if not hasattr(self.model_class, column):
            raise ValueError(f"Column '{column}' does not exist on model {self.model_class.__name__}")
        
        column_attr = getattr(self.model_class, column)
        self._query = self._get_query().filter(column_attr.isnot(None))
        return self
    
    def order_by(self, column: str, direction: str = 'asc') -> 'BaseRepository[T]':
        """Add an order by clause to the query."""
        if not hasattr(self.model_class, column):
            raise ValueError(f"Column '{column}' does not exist on model {self.model_class.__name__}")
        
        column_attr = getattr(self.model_class, column)
        if direction.lower() == 'desc':
            self._query = self._get_query().order_by(desc(column_attr))
        else:
            self._query = self._get_query().order_by(asc(column_attr))
        return self
    
    def limit(self, count: int) -> 'BaseRepository[T]':
        """Limit the number of results."""
        self._query = self._get_query().limit(count)
        return self
    
    def offset(self, count: int) -> 'BaseRepository[T]':
        """Offset the query results."""
        self._query = self._get_query().offset(count)
        return self
    
    def with_relations(self, relations: List[str]) -> 'BaseRepository[T]':
        """Eager load relationships."""
        self._relations.extend(relations)
        return self
    
    def get(self) -> List[T]:
        """Execute the query and get the results."""
        query = self._get_query()
        if self._relations:
            for relation in self._relations:
                if hasattr(self.model_class, relation):
                    query = query.options(selectinload(getattr(self.model_class, relation)))
        result = query.all()
        self._reset_query()
        return result
    
    def first(self) -> Optional[T]:
        """Get the first result."""
        query = self._get_query()
        if self._relations:
            for relation in self._relations:
                if hasattr(self.model_class, relation):
                    query = query.options(selectinload(getattr(self.model_class, relation)))
        result = query.first()
        self._reset_query()
        return result
    
    def first_or_fail(self) -> T:
        """Get the first result or raise an exception."""
        result = self.first()
        if result is None:
            raise ModelNotFoundException(f"No {self.model_class.__name__} found matching the criteria")
        return result
    
    def count(self) -> int:
        """Count the results."""
        result = self._get_query().count()
        self._reset_query()
        return result
    
    def exists(self) -> bool:
        """Check if any records exist."""
        return self.count() > 0
    
    def pluck(self, column: str, key: Optional[str] = None) -> Union[List[Any], Dict[Any, Any]]:
        """Get a list of column values."""
        if not hasattr(self.model_class, column):
            raise ValueError(f"Column '{column}' does not exist on model {self.model_class.__name__}")
        
        query = self._get_query()
        column_attr = getattr(self.model_class, column)
        
        if key is not None:
            if not hasattr(self.model_class, key):
                raise ValueError(f"Key column '{key}' does not exist on model {self.model_class.__name__}")
            key_attr = getattr(self.model_class, key)
            results = query.with_entities(key_attr, column_attr).all()
            result_dict = {row[0]: row[1] for row in results}
            self._reset_query()
            return result_dict
        else:
            results = query.with_entities(column_attr).all()
            result_list = [row[0] for row in results]
            self._reset_query()
            return result_list
    
    def chunk(self, count: int) -> Iterator[List[T]]:
        """Process records in chunks."""
        offset = 0
        while True:
            query = self._get_query().offset(offset).limit(count)
            if self._relations:
                for relation in self._relations:
                    if hasattr(self.model_class, relation):
                        query = query.options(selectinload(getattr(self.model_class, relation)))
            
            chunk_results = query.all()
            if not chunk_results:
                break
            
            yield chunk_results
            offset += count
        
        self._reset_query()
    
    def fresh_query(self) -> 'BaseRepository[T]':
        """Get a fresh query instance."""
        new_repo = self.__class__(self.db, self.model_class)
        return new_repo