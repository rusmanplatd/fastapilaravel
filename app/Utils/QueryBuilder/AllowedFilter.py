from __future__ import annotations

from typing import Any, Optional, Union, List, Callable, Dict
from abc import ABC, abstractmethod
from sqlalchemy.orm import Query as SQLQuery
from sqlalchemy import Column
from .FilterOperators import FilterOperator


class FilterInterface(ABC):
    """Interface for filter implementations"""
    
    @abstractmethod
    def __call__(self, query: SQLQuery, value: Any, property_name: str) -> SQLQuery:
        """Apply filter to query"""
        pass


class AllowedFilter:
    """
    Represents an allowed filter for QueryBuilder
    Inspired by Spatie Laravel Query Builder
    """
    
    def __init__(
        self,
        name: str,
        internal_name: Optional[str] = None,
        filter_class: Optional[FilterInterface] = None,
        default_value: Any = None,
        nullable: bool = False,
        ignored_values: Optional[List[Any]] = None
    ) -> None:
        self.name = name
        self.internal_name = internal_name or name
        self.filter_class = filter_class
        self.default_value = default_value
        self.nullable = nullable
        self.ignored_values = ignored_values or []
    
    @classmethod
    def partial(
        cls, 
        name: str, 
        internal_name: Optional[str] = None,
        add_relation_constraint: bool = True
    ) -> AllowedFilter:
        """Create partial match filter (LIKE/ILIKE)"""
        filter_impl = PartialFilter(add_relation_constraint)
        return cls(name, internal_name, filter_impl)
    
    @classmethod
    def exact(
        cls, 
        name: str, 
        internal_name: Optional[str] = None,
        add_relation_constraint: bool = True,
        array_delimiter: Optional[str] = None
    ) -> AllowedFilter:
        """Create exact match filter"""
        filter_impl = ExactFilter(add_relation_constraint, array_delimiter)
        return cls(name, internal_name, filter_impl)
    
    @classmethod
    def operator(
        cls, 
        name: str,
        operator: FilterOperator,
        internal_name: Optional[str] = None,
        add_relation_constraint: bool = True
    ) -> AllowedFilter:
        """Create operator-based filter"""
        filter_impl = OperatorFilter(operator, add_relation_constraint)
        return cls(name, internal_name, filter_impl)
    
    @classmethod
    def scope(
        cls, 
        name: str, 
        scope_name: Optional[str] = None
    ) -> AllowedFilter:
        """Create scope filter (calls model scope method)"""
        filter_impl = ScopeFilter(scope_name or name)
        return cls(name, name, filter_impl)
    
    @classmethod
    def callback(
        cls, 
        name: str, 
        callback: Callable[[SQLQuery, Any, str], SQLQuery]
    ) -> AllowedFilter:
        """Create callback filter"""
        filter_impl = CallbackFilter(callback)
        return cls(name, name, filter_impl)
    
    @classmethod
    def custom(
        cls, 
        name: str, 
        filter_class: FilterInterface,
        internal_name: Optional[str] = None
    ) -> AllowedFilter:
        """Create custom filter"""
        return cls(name, internal_name, filter_class)
    
    @classmethod
    def belongs_to(
        cls, 
        name: str, 
        relationship_path: Optional[str] = None
    ) -> AllowedFilter:
        """Create belongs-to relationship filter"""
        filter_impl = BelongsToFilter(relationship_path or name)
        return cls(name, name, filter_impl)
    
    @classmethod
    def trashed(cls, name: str = "trashed") -> AllowedFilter:
        """Create trashed (soft delete) filter"""
        filter_impl = TrashedFilter()
        return cls(name, name, filter_impl)
    
    def default(self, value: Any) -> AllowedFilter:
        """Set default value for filter"""
        self.default_value = value
        return self
    
    def nullable(self, nullable: bool = True) -> AllowedFilter:
        """Allow nullable values"""
        self.nullable = nullable
        return self
    
    def ignore(self, *values: Any) -> AllowedFilter:
        """Set values to ignore"""
        if len(values) == 1 and isinstance(values[0], list):
            self.ignored_values = values[0]
        else:
            self.ignored_values = list(values)
        return self
    
    def should_apply_filter(self, value: Any) -> bool:
        """Check if filter should be applied based on value and settings"""
        # Check if value should be ignored
        if value in self.ignored_values:
            return False
        
        # Check nullable
        if not self.nullable and (value is None or value == ""):
            return False
        
        return True
    
    def apply(self, query: SQLQuery, value: Any, model_class: type) -> SQLQuery:
        """Apply filter to query"""
        if not self.should_apply_filter(value):
            # Use default value if filter shouldn't apply normally
            if self.default_value is not None:
                value = self.default_value
            else:
                return query
        
        if self.filter_class:
            return self.filter_class(query, value, self.internal_name)
        else:
            # Default exact filter behavior
            column = getattr(model_class, self.internal_name)
            if isinstance(value, list):
                return query.filter(column.in_(value))
            else:
                return query.filter(column == value)


class PartialFilter(FilterInterface):
    """Partial match filter using LIKE/ILIKE"""
    
    def __init__(self, add_relation_constraint: bool = True) -> None:
        self.add_relation_constraint = add_relation_constraint
    
    def __call__(self, query: SQLQuery, value: Any, property_name: str) -> SQLQuery:
        # Handle relationship filters (e.g., "user.name")
        if "." in property_name:
            parts = property_name.split(".")
            if len(parts) == 2 and self.add_relation_constraint:
                # This would need model introspection to handle properly
                # For now, treat as simple column filter
                pass
        
        # For simple implementation, assume column exists
        # In real implementation, you'd get the column from the model
        if isinstance(value, list):
            conditions = []
            for v in value:
                # This is a simplified version - in practice you'd need to get the actual column
                conditions.append(f"column ILIKE '%{v}%'")
            return query.filter(f"({' OR '.join(conditions)})")
        else:
            return query.filter(f"column ILIKE '%{value}%'")


class ExactFilter(FilterInterface):
    """Exact match filter"""
    
    def __init__(self, add_relation_constraint: bool = True, array_delimiter: Optional[str] = None) -> None:
        self.add_relation_constraint = add_relation_constraint
        self.array_delimiter = array_delimiter or ","
    
    def __call__(self, query: SQLQuery, value: Any, property_name: str) -> SQLQuery:
        # Handle comma-separated values
        if isinstance(value, str) and self.array_delimiter in value:
            value = [v.strip() for v in value.split(self.array_delimiter)]
        
        # Handle relationship filters
        if "." in property_name:
            parts = property_name.split(".")
            if len(parts) == 2 and self.add_relation_constraint:
                # Simplified relationship handling
                pass
        
        # Apply filter
        if isinstance(value, list):
            return query.filter(f"column IN ({','.join(repr(v) for v in value)})")
        else:
            return query.filter(f"column = {repr(value)}")


class OperatorFilter(FilterInterface):
    """Operator-based filter"""
    
    def __init__(self, operator: FilterOperator, add_relation_constraint: bool = True) -> None:
        self.operator = operator
        self.add_relation_constraint = add_relation_constraint
    
    def __call__(self, query: SQLQuery, value: Any, property_name: str) -> SQLQuery:
        # Handle dynamic operators
        if self.operator == FilterOperator.DYNAMIC:
            if isinstance(value, dict) and 'operator' in value and 'value' in value:
                operator = FilterOperator.from_string(value['operator'])
                actual_value = value['value']
                return operator.apply_to_query(query, None, actual_value)  # Column would be resolved
        
        # Apply static operator
        return self.operator.apply_to_query(query, None, value)  # Column would be resolved


class ScopeFilter(FilterInterface):
    """Scope filter that calls model scope methods"""
    
    def __init__(self, scope_name: str) -> None:
        self.scope_name = scope_name
    
    def __call__(self, query: SQLQuery, value: Any, property_name: str) -> SQLQuery:
        # In practice, you'd call the scope method on the model
        # This is a placeholder implementation
        method_name = f"scope_{self.scope_name.lower()}"
        # query = getattr(model_class, method_name)(query, value)
        return query


class CallbackFilter(FilterInterface):
    """Callback-based filter"""
    
    def __init__(self, callback: Callable[[SQLQuery, Any, str], SQLQuery]) -> None:
        self.callback = callback
    
    def __call__(self, query: SQLQuery, value: Any, property_name: str) -> SQLQuery:
        return self.callback(query, value, property_name)


class BelongsToFilter(FilterInterface):
    """Belongs-to relationship filter"""
    
    def __init__(self, relationship_path: str) -> None:
        self.relationship_path = relationship_path
    
    def __call__(self, query: SQLQuery, value: Any, property_name: str) -> SQLQuery:
        # Handle nested relationships (e.g., "post.author")
        parts = self.relationship_path.split(".")
        
        # In practice, you'd use SQLAlchemy relationship joins
        # This is a simplified implementation
        if len(parts) == 1:
            # Simple belongs-to
            foreign_key = f"{parts[0]}_id"
            return query.filter(f"{foreign_key} = {value}")
        else:
            # Nested belongs-to
            # Would require proper join handling
            return query
        
        return query


class TrashedFilter(FilterInterface):
    """Trashed (soft delete) filter"""
    
    def __call__(self, query: SQLQuery, value: Any, property_name: str) -> SQLQuery:
        # Handle soft delete filtering
        # Values: 'with', 'only', 'without'
        if value == "only":
            # Only trashed records
            return query.filter("deleted_at IS NOT NULL")
        elif value == "with":
            # Include trashed records (no additional filter)
            return query
        else:
            # Default: exclude trashed (deleted_at IS NULL)
            return query.filter("deleted_at IS NULL")