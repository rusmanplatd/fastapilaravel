from __future__ import annotations

from typing import Optional, Callable, Union, TypeVar, Any, cast
from abc import ABC, abstractmethod  
from sqlalchemy.orm import Query
from sqlalchemy import Column, text, func, desc, asc
# SQLAlchemy nulls handling - these might not be available in all versions
try:
    from sqlalchemy import nullsfirst, nullslast  # type: ignore[attr-defined]
except (ImportError, AttributeError):
    # For older SQLAlchemy versions or when not available
    def nullsfirst(column: Any) -> Any:
        return text(f"{column} NULLS FIRST")
    
    def nullslast(column: Any) -> Any:
        return text(f"{column} NULLS LAST")
from enum import Enum

T = TypeVar('T')
SQLQuery = Query[Any]


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
        # Use default direction if not explicitly specified
        if self._default_direction == SortDirection.DESCENDING:
            descending = not descending  # Flip the direction
        
        if self.sort_class:
            return self.sort_class(query, descending, self.internal_name)
        else:
            # Default field sort behavior with proper column resolution
            column = self._get_column(model_class, self.internal_name)
            if column is not None:
                if descending:
                    return query.order_by(desc(column))
                else:
                    return query.order_by(asc(column))
            else:
                # Fallback to raw SQL ordering
                direction = "DESC" if descending else "ASC"
                return query.order_by(text(f"{self.internal_name} {direction}"))
    
    def _get_column(self, model_class: type, property_name: str) -> Optional[Column]:
        """Get column from model class, handling relationships"""
        try:
            if '.' in property_name:
                # Handle nested relationships
                parts = property_name.split('.')
                current_model = model_class
                
                for i, part in enumerate(parts[:-1]):
                    if hasattr(current_model, part):
                        relationship = getattr(current_model, part)
                        if hasattr(relationship.property, 'mapper'):
                            current_model = relationship.property.mapper.class_
                        else:
                            return None
                    else:
                        return None
                
                # Get the final column
                final_column = parts[-1]
                if hasattr(current_model, final_column):
                    attr = getattr(current_model, final_column)
                    if hasattr(attr, 'type'):  # SQLAlchemy column check
                        return cast(Column, attr)
            else:
                # Simple column access
                if hasattr(model_class, property_name):
                    attr = getattr(model_class, property_name)
                    if hasattr(attr, 'type'):  # SQLAlchemy column check
                        return cast(Column, attr)
            
            return None
        except Exception:
            return None
    
    def is_descending_by_default(self) -> bool:
        """Check if sort is descending by default"""
        return self._default_direction == SortDirection.DESCENDING


class FieldSort(SortInterface):
    """Simple field-based sort with proper column resolution"""
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        column = self._get_column_from_query(query, property_name)
        if column is not None:
            if descending:
                return query.order_by(desc(column))
            else:
                return query.order_by(asc(column))
        else:
            # Fallback to text-based ordering
            direction = "DESC" if descending else "ASC"
            return query.order_by(text(f"{property_name} {direction}"))
    
    def _get_column_from_query(self, query: SQLQuery, property_name: str) -> Optional[Column]:
        """Get column from query's model"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = query.column_descriptions
                if descriptions and descriptions[0].get('entity'):
                    model = descriptions[0]['entity']
                    if hasattr(model, property_name):
                        attr = getattr(model, property_name)
                        if hasattr(attr, 'type'):  # SQLAlchemy column check
                            return cast(Column, attr)
            return None
        except Exception:
            return None


class CallbackSort(SortInterface):
    """Callback-based sort"""
    
    def __init__(self, callback: Callable[[SQLQuery, bool, str], SQLQuery]) -> None:
        self.callback = callback
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        return self.callback(query, descending, property_name)


class StringLengthSort(SortInterface):
    """Sort by string length using SQLAlchemy func"""
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        # Get the column from the query's model
        model = self._get_model_from_query(query)
        if model and hasattr(model, property_name):
            column = getattr(model, property_name)
            length_expr = func.length(column)  # type: ignore[attr-defined]
            
            if descending:
                return query.order_by(desc(length_expr))
            else:
                return query.order_by(asc(length_expr))
        else:
            # Fallback to text-based ordering
            direction = "DESC" if descending else "ASC"
            return query.order_by(text(f"LENGTH({property_name}) {direction}"))
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = query.column_descriptions
                if descriptions and descriptions[0].get('entity'):
                    entity = descriptions[0]['entity']
                    if isinstance(entity, type):
                        return entity
            return None
        except Exception:
            return None


class RelationshipSort(SortInterface):
    """Sort by relationship field with proper SQLAlchemy joins"""
    
    def __init__(self, relationship_path: str) -> None:
        self.relationship_path = relationship_path
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        # Handle relationship sorting (e.g., "user.name")
        parts = self.relationship_path.split(".")
        
        if len(parts) == 2:
            relationship_name, column_name = parts
            
            # Get the model from query
            model = self._get_model_from_query(query)
            if model and hasattr(model, relationship_name):
                relationship = getattr(model, relationship_name)
                
                # Add join if not already present
                if hasattr(relationship.property, 'mapper'):
                    related_model = relationship.property.mapper.class_
                    
                    # Check if join already exists (simplified check)
                    query = query.join(relationship)
                    
                    # Get the column from the related model
                    if hasattr(related_model, column_name):
                        column = getattr(related_model, column_name)
                        if descending:
                            return query.order_by(desc(column))
                        else:
                            return query.order_by(asc(column))
        
        return query
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = query.column_descriptions
                if descriptions and descriptions[0].get('entity'):
                    entity = descriptions[0]['entity']
                    if isinstance(entity, type):
                        return entity
            return None
        except Exception:
            return None


class CaseInsensitiveSort(SortInterface):
    """Case-insensitive sort using SQLAlchemy func"""
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        # Get the column from the query's model
        model = self._get_model_from_query(query)
        if model and hasattr(model, property_name):
            column = getattr(model, property_name)
            lower_expr = func.lower(column)  # type: ignore[attr-defined]
            
            if descending:
                return query.order_by(desc(lower_expr))
            else:
                return query.order_by(asc(lower_expr))
        else:
            # Fallback to text-based ordering
            direction = "DESC" if descending else "ASC"
            return query.order_by(text(f"LOWER({property_name}) {direction}"))
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = query.column_descriptions
                if descriptions and descriptions[0].get('entity'):
                    entity = descriptions[0]['entity']
                    if isinstance(entity, type):
                        return entity
            return None
        except Exception:
            return None


class NullsFirstSort(SortInterface):
    """Sort with nulls first using SQLAlchemy nullsfirst"""
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        # Get the column from the query's model
        model = self._get_model_from_query(query)
        if model and hasattr(model, property_name):
            column = getattr(model, property_name)
            
            if descending:
                return query.order_by(nullsfirst(desc(column)))
            else:
                return query.order_by(nullsfirst(asc(column)))
        else:
            # Fallback to text-based ordering
            direction = "DESC" if descending else "ASC"
            return query.order_by(text(f"{property_name} {direction} NULLS FIRST"))
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = query.column_descriptions
                if descriptions and descriptions[0].get('entity'):
                    entity = descriptions[0]['entity']
                    if isinstance(entity, type):
                        return entity
            return None
        except Exception:
            return None


class NullsLastSort(SortInterface):
    """Sort with nulls last using SQLAlchemy nullslast"""
    
    def __call__(self, query: SQLQuery, descending: bool, property_name: str) -> SQLQuery:
        # Get the column from the query's model
        model = self._get_model_from_query(query)
        if model and hasattr(model, property_name):
            column = getattr(model, property_name)
            
            if descending:
                return query.order_by(nullslast(desc(column)))
            else:
                return query.order_by(nullslast(asc(column)))
        else:
            # Fallback to text-based ordering
            direction = "DESC" if descending else "ASC"
            return query.order_by(text(f"{property_name} {direction} NULLS LAST"))
    
    def _get_model_from_query(self, query: SQLQuery) -> Optional[type]:
        """Extract model class from SQLAlchemy query"""
        try:
            if hasattr(query, 'column_descriptions'):
                descriptions = query.column_descriptions
                if descriptions and descriptions[0].get('entity'):
                    entity = descriptions[0]['entity']
                    if isinstance(entity, type):
                        return entity
            return None
        except Exception:
            return None