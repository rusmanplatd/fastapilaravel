from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

T = TypeVar('T')


class BaseRepositoryInterface(ABC, Generic[T]):
    """
    Base repository interface defining common repository operations.
    
    This interface follows Laravel's repository pattern and provides
    a contract for data access layer operations.
    """
    
    @abstractmethod
    def find(self, id: Union[int, str]) -> Optional[T]:
        """Find a record by its primary key."""
        pass
    
    @abstractmethod
    def find_or_fail(self, id: Union[int, str]) -> T:
        """Find a record by its primary key or raise an exception."""
        pass
    
    @abstractmethod
    def find_many(self, ids: List[Union[int, str]]) -> List[T]:
        """Find multiple records by their primary keys."""
        pass
    
    @abstractmethod
    def all(self) -> List[T]:
        """Get all records."""
        pass
    
    @abstractmethod
    def paginate(self, page: int = 1, per_page: int = 15) -> Dict[str, Any]:
        """Paginate records."""
        pass
    
    @abstractmethod
    def create(self, data: Dict[str, Any]) -> T:
        """Create a new record."""
        pass
    
    @abstractmethod
    def update(self, id: Union[int, str], data: Dict[str, Any]) -> T:
        """Update an existing record."""
        pass
    
    @abstractmethod
    def delete(self, id: Union[int, str]) -> bool:
        """Delete a record."""
        pass
    
    @abstractmethod
    def where(self, column: str, operator: str = '=', value: Any = None) -> 'BaseRepositoryInterface[T]':
        """Add a where clause to the query."""
        pass
    
    @abstractmethod
    def where_in(self, column: str, values: List[Any]) -> 'BaseRepositoryInterface[T]':
        """Add a where in clause to the query."""
        pass
    
    @abstractmethod
    def where_not_in(self, column: str, values: List[Any]) -> 'BaseRepositoryInterface[T]':
        """Add a where not in clause to the query."""
        pass
    
    @abstractmethod
    def where_null(self, column: str) -> 'BaseRepositoryInterface[T]':
        """Add a where null clause to the query."""
        pass
    
    @abstractmethod
    def where_not_null(self, column: str) -> 'BaseRepositoryInterface[T]':
        """Add a where not null clause to the query."""
        pass
    
    @abstractmethod
    def order_by(self, column: str, direction: str = 'asc') -> 'BaseRepositoryInterface[T]':
        """Add an order by clause to the query."""
        pass
    
    @abstractmethod
    def limit(self, count: int) -> 'BaseRepositoryInterface[T]':
        """Limit the number of results."""
        pass
    
    @abstractmethod
    def offset(self, count: int) -> 'BaseRepositoryInterface[T]':
        """Offset the query results."""
        pass
    
    @abstractmethod
    def with_relations(self, relations: List[str]) -> 'BaseRepositoryInterface[T]':
        """Eager load relationships."""
        pass
    
    @abstractmethod
    def get(self) -> List[T]:
        """Execute the query and get the results."""
        pass
    
    @abstractmethod
    def first(self) -> Optional[T]:
        """Get the first result."""
        pass
    
    @abstractmethod
    def first_or_fail(self) -> T:
        """Get the first result or raise an exception."""
        pass
    
    @abstractmethod
    def count(self) -> int:
        """Count the results."""
        pass
    
    @abstractmethod
    def exists(self) -> bool:
        """Check if any records exist."""
        pass
    
    @abstractmethod
    def pluck(self, column: str, key: Optional[str] = None) -> Union[List[Any], Dict[Any, Any]]:
        """Get a list of column values."""
        pass
    
    @abstractmethod
    def chunk(self, count: int) -> Any:
        """Process records in chunks."""
        pass
    
    @abstractmethod
    def fresh_query(self) -> 'BaseRepositoryInterface[T]':
        """Get a fresh query instance."""
        pass