from __future__ import annotations

from typing import Optional, Callable, Union, List
from abc import ABC, abstractmethod
from sqlalchemy.orm import Query as SQLQuery


class IncludeInterface(ABC):
    """Interface for include implementations"""
    
    @abstractmethod
    def __call__(self, query: SQLQuery, relations: str) -> SQLQuery:
        """Apply include to query"""
        pass


class AllowedInclude:
    """
    Represents an allowed include for QueryBuilder
    Inspired by Spatie Laravel Query Builder
    """
    
    def __init__(
        self,
        name: str,
        internal_name: Optional[str] = None,
        include_class: Optional[IncludeInterface] = None
    ) -> None:
        self.name = name
        self.internal_name = internal_name or name
        self.include_class = include_class
    
    @classmethod
    def relationship(
        cls, 
        name: str, 
        internal_name: Optional[str] = None
    ) -> AllowedInclude:
        """Create relationship include"""
        include_impl = RelationshipInclude()
        return cls(name, internal_name, include_impl)
    
    @classmethod
    def count(
        cls, 
        name: str, 
        relationship_name: Optional[str] = None
    ) -> AllowedInclude:
        """Create count include (e.g., postsCount)"""
        # Remove 'Count' suffix to get relationship name
        rel_name = relationship_name
        if not rel_name:
            if name.endswith('Count'):
                rel_name = name[:-5]  # Remove 'Count'
            else:
                rel_name = name
        
        include_impl = CountInclude(rel_name)
        return cls(name, rel_name, include_impl)
    
    @classmethod
    def exists(
        cls, 
        name: str, 
        relationship_name: Optional[str] = None
    ) -> AllowedInclude:
        """Create exists include (e.g., postsExists)"""
        # Remove 'Exists' suffix to get relationship name
        rel_name = relationship_name
        if not rel_name:
            if name.endswith('Exists'):
                rel_name = name[:-6]  # Remove 'Exists'
            else:
                rel_name = name
        
        include_impl = ExistsInclude(rel_name)
        return cls(name, rel_name, include_impl)
    
    @classmethod
    def custom(
        cls, 
        name: str, 
        include_class: IncludeInterface,
        internal_name: Optional[str] = None
    ) -> AllowedInclude:
        """Create custom include"""
        return cls(name, internal_name, include_class)
    
    @classmethod
    def callback(
        cls, 
        name: str, 
        callback: Callable[[SQLQuery, str], SQLQuery]
    ) -> AllowedInclude:
        """Create callback include"""
        include_impl = CallbackInclude(callback)
        return cls(name, name, include_impl)
    
    def apply(self, query: SQLQuery, model_class: type) -> SQLQuery:
        """Apply include to query"""
        if self.include_class:
            return self.include_class(query, self.internal_name)
        else:
            # Default relationship include behavior
            # In SQLAlchemy, this would typically be handled with joinedload or selectinload
            try:
                # Try to get the relationship attribute
                relationship = getattr(model_class, self.internal_name, None)
                if relationship is not None:
                    # For now, we'll use a simple approach
                    # In practice, you'd use SQLAlchemy's relationship loading options
                    from sqlalchemy.orm import selectinload
                    return query.options(selectinload(relationship))
                else:
                    # Fallback: assume it's a valid relationship name
                    return query
            except Exception:
                # If anything goes wrong, return the query unchanged
                return query


class RelationshipInclude(IncludeInterface):
    """Standard relationship include"""
    
    def __call__(self, query: SQLQuery, relations: str) -> SQLQuery:
        # Handle nested relationships (e.g., "posts.comments")
        parts = relations.split(".")
        
        # In practice, you'd use SQLAlchemy's relationship loading
        # This is a simplified implementation
        try:
            from sqlalchemy.orm import selectinload, joinedload
            
            # For nested relationships, we need to build the loading path
            if len(parts) == 1:
                # Simple relationship
                return query.options(selectinload(relations))
            else:
                # Nested relationship - would need more complex handling
                # For now, just load the first level
                return query.options(selectinload(parts[0]))
        except ImportError:
            # Fallback if SQLAlchemy imports fail
            return query


class CountInclude(IncludeInterface):
    """Count include for relationship counts"""
    
    def __init__(self, relationship_name: str) -> None:
        self.relationship_name = relationship_name
    
    def __call__(self, query: SQLQuery, relations: str) -> SQLQuery:
        # Add count for the relationship
        # In SQLAlchemy, this would use func.count() with subquery or join
        try:
            from sqlalchemy import func
            
            # This is a simplified approach
            # In practice, you'd need to handle the specific relationship counting
            # For now, we'll add a placeholder that would need to be properly implemented
            return query
        except ImportError:
            return query


class ExistsInclude(IncludeInterface):
    """Exists include for relationship existence check"""
    
    def __init__(self, relationship_name: str) -> None:
        self.relationship_name = relationship_name
    
    def __call__(self, query: SQLQuery, relations: str) -> SQLQuery:
        # Add exists check for the relationship
        # In SQLAlchemy, this would use exists() subquery
        try:
            from sqlalchemy import exists, select
            
            # This is a simplified approach
            # In practice, you'd need to handle the specific relationship exists check
            return query
        except ImportError:
            return query


class CallbackInclude(IncludeInterface):
    """Callback-based include"""
    
    def __init__(self, callback: Callable[[SQLQuery, str], SQLQuery]) -> None:
        self.callback = callback
    
    def __call__(self, query: SQLQuery, relations: str) -> SQLQuery:
        return self.callback(query, relations)


class AggregateInclude(IncludeInterface):
    """Aggregate include for relationship aggregates"""
    
    def __init__(self, column: str, function: str) -> None:
        self.column = column
        self.function = function.upper()
    
    def __call__(self, query: SQLQuery, relations: str) -> SQLQuery:
        # Add aggregate for the relationship
        # This would need to be implemented based on the specific aggregate function
        try:
            from sqlalchemy import func
            
            # Example for common aggregates
            if self.function == 'SUM':
                # Add sum aggregate - implementation would depend on model structure
                pass
            elif self.function == 'AVG':
                # Add average aggregate
                pass
            elif self.function == 'MAX':
                # Add max aggregate
                pass
            elif self.function == 'MIN':
                # Add min aggregate
                pass
            
            return query
        except ImportError:
            return query


class LatestOfManyInclude(IncludeInterface):
    """Latest of many include"""
    
    def __call__(self, query: SQLQuery, relations: str) -> SQLQuery:
        # This would implement Laravel's latestOfMany() equivalent
        # In practice, this would need specific implementation based on timestamp fields
        return query


class OldestOfManyInclude(IncludeInterface):
    """Oldest of many include"""
    
    def __call__(self, query: SQLQuery, relations: str) -> SQLQuery:
        # This would implement Laravel's oldestOfMany() equivalent
        return query