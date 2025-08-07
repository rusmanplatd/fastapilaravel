from __future__ import annotations

from typing import Optional, Callable, Union, TypeVar
from abc import ABC, abstractmethod  
from sqlalchemy.orm import Query as SQLQuery
from enum import Enum

T = TypeVar('T')


class SortDirection(Enum):
    """Sort direction enum"""
    ASCENDING = "ASC"
    DESCENDING = "DESC"


class SortInterface(ABC):
    """Interface for sort implementations"""
    
    @abstractmethod
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        """Apply sort to query"""
        pass


class AllowedSort:
    """
    Represents an allowed sort for QueryBuilder
    Inspired by Spatie Laravel Query Builder
    """
    
    def __init__(
        self,
        name: str,
        internal_name: Optional[str] = None,
        sort_class: Optional[SortInterface] = None,
        default_direction: SortDirection = SortDirection.ASCENDING
    ) -> None:
        self.name = name
        self.internal_name = internal_name or name
        self.sort_class = sort_class
        self._default_direction = default_direction
    
    @classmethod
    def field(
        cls, 
        name: str, 
        internal_name: Optional[str] = None
    ) -> AllowedSort:
        """Create field-based sort"""
        sort_impl = FieldSort()
        return cls(name, internal_name, sort_impl)
    
    @classmethod
    def custom(
        cls, 
        name: str, 
        sort_class: SortInterface,
        internal_name: Optional[str] = None
    ) -> AllowedSort:
        """Create custom sort"""
        return cls(name, internal_name, sort_class)
    
    @classmethod
    def callback(
        cls, 
        name: str, 
        callback: Callable[[SQLQuery, bool, str], SQLQuery]
    ) -> AllowedSort:
        """Create callback sort"""
        sort_impl = CallbackSort(callback)
        return cls(name, name, sort_impl)
    
    def default_direction(self, direction: SortDirection) -> AllowedSort:
        """Set default sort direction"""
        self._default_direction = direction
        return self
    
    def apply(self, query: SQLQuery, descending: bool, model_class: type) -> SQLQuery:
        """Apply sort to query"""
        if self.sort_class:
            return self.sort_class(query, descending, self.internal_name)
        else:
            # Default field sort behavior
            direction = "DESC" if descending else "ASC"
            column = getattr(model_class, self.internal_name, None)
            if column is not None:
                return query.order_by(getattr(column, 'desc' if descending else 'asc')())
            else:
                # Fallback to raw SQL ordering
                return query.order_by(f"{self.internal_name} {direction}")
    
    def is_descending_by_default(self) -> bool:
        """Check if sort is descending by default"""
        return self._default_direction == SortDirection.DESCENDING


class FieldSort(SortInterface):
    """Simple field-based sort"""
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        direction = "DESC" if descending else "ASC"
        return query.order_by(f"{property_name} {direction}")


class CallbackSort(SortInterface):
    """Callback-based sort"""
    
    def __init__(self, callback: Callable[[SQLQuery, bool, str], SQLQuery]) -> None:
        self.callback = callback
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        return self.callback(query, descending, property_name)


class StringLengthSort(SortInterface):
    """Sort by string length"""
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        direction = "DESC" if descending else "ASC"
        return query.order_by(f"LENGTH({property_name}) {direction}")


class RelationshipSort(SortInterface):
    """Sort by relationship field"""
    
    def __init__(self, relationship_path: str) -> None:
        self.relationship_path = relationship_path
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        # Handle relationship sorting (e.g., "user.name")
        parts = self.relationship_path.split(".")
        
        if len(parts) == 2:
            # Simple relationship sort
            # In practice, you'd need to join the relationship table
            # This is a simplified implementation
            relationship_table = parts[0]
            relationship_field = parts[1]
            direction = "DESC" if descending else "ASC"
            
            # Placeholder for join logic
            # query = query.join(relationship_table)
            return query.order_by(f"{relationship_table}.{relationship_field} {direction}")
        
        return query


class CaseInsensitiveSort(SortInterface):
    """Case-insensitive sort"""
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        direction = "DESC" if descending else "ASC"
        return query.order_by(f"LOWER({property_name}) {direction}")


class NullsFirstSort(SortInterface):
    """Sort with nulls first"""
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        direction = "DESC" if descending else "ASC"
        return query.order_by(f"{property_name} {direction} NULLS FIRST")


class NullsLastSort(SortInterface):
    """Sort with nulls last"""
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        direction = "DESC" if descending else "ASC"
        return query.order_by(f"{property_name} {direction} NULLS LAST")