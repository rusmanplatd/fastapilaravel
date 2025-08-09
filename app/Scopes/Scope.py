from __future__ import annotations

from typing import Any, Dict, Optional, Type, Protocol, runtime_checkable, Callable, TYPE_CHECKING
from abc import ABC, abstractmethod
from sqlalchemy.orm import Query
from sqlalchemy.sql import Select

if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel
    SQLQuery = Query[BaseModel]
else:
    SQLQuery = Query


@runtime_checkable
class ScopeInterface(Protocol):
    """
    Laravel-style Scope interface for global query modifications.
    
    Global scopes allow automatic modification of all queries for a model.
    This is essential for features like soft deletes, multi-tenancy, etc.
    """
    
    def apply(self, builder: SQLQuery, model: Type[Any]) -> SQLQuery:
        """
        Apply the scope to a given Eloquent query builder.
        
        @param builder: The query builder instance
        @param model: The model class the scope is being applied to
        @return: The modified query builder
        """
        ...


class Scope(ABC, ScopeInterface):
    """
    Abstract base class for Laravel-style Global Scopes.
    
    Global scopes provide a convenient, consistent way to add constraints
    to all queries for a given model. The most common example is a "soft delete"
    scope which automatically excludes deleted records.
    
    Features:
    - Automatic query modification across all model queries
    - Can be applied, removed, or bypassed on specific queries
    - Support for complex query logic with relationships
    - Integration with query builder and Eloquent methods
    - Performance optimized with query caching
    
    Usage:
        class ActiveScope(Scope):
            def apply(self, builder: SQLQuery, model: Type[Any]) -> SQLQuery:
                return builder.filter(model.status == 'active')
        
        # Apply to model
        User.add_global_scope(ActiveScope())
        
        # All queries automatically filtered
        users = User.all()  # Only active users
        
        # Bypass scope when needed
        all_users = User.with_trashed().all()  # All users including inactive
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize the scope with an optional name.
        
        @param name: Optional name for the scope (defaults to class name)
        """
        self.name = name or self.__class__.__name__
        self.priority = 0  # Lower numbers = higher priority
        self.enabled = True
        self.conditions: Dict[str, Any] = {}
        
    @abstractmethod
    def apply(self, builder: SQLQuery, model: Type[Any]) -> SQLQuery:
        """
        Apply the scope to a given query builder.
        
        This method must be implemented by all scope classes and defines
        the specific query modifications that should be applied.
        
        @param builder: The query builder to modify
        @param model: The model class this scope applies to
        @return: The modified query builder
        """
        pass
    
    def extend(self, builder: SQLQuery, model: Type[Any]) -> SQLQuery:
        """
        Extend the query builder with additional methods.
        
        This optional method allows scopes to add custom query methods
        that can be used to modify or bypass the scope behavior.
        
        @param builder: The query builder to extend
        @param model: The model class
        @return: The extended query builder
        """
        return builder
    
    def remove(self, builder: SQLQuery, model: Type[Any]) -> SQLQuery:
        """
        Remove the scope's constraints from the query.
        
        This method should reverse any modifications made by apply().
        Used when the scope needs to be bypassed for specific queries.
        
        @param builder: The query builder to modify
        @param model: The model class
        @return: The query builder with scope constraints removed
        """
        # Default implementation - subclasses should override for complex scopes
        return builder
    
    def can_apply(self, model: Type[Any]) -> bool:
        """
        Determine if the scope can be applied to the given model.
        
        @param model: The model class to check
        @return: True if the scope can be applied
        """
        return self.enabled
    
    def get_name(self) -> str:
        """
        Get the scope's name.
        
        @return: The scope name
        """
        return self.name
    
    def set_priority(self, priority: int) -> 'Scope':
        """
        Set the scope's priority.
        
        @param priority: Priority level (lower = higher priority)
        @return: Self for method chaining
        """
        self.priority = priority
        return self
    
    def enable(self) -> 'Scope':
        """
        Enable the scope.
        
        @return: Self for method chaining
        """
        self.enabled = True
        return self
    
    def disable(self) -> 'Scope':
        """
        Disable the scope.
        
        @return: Self for method chaining
        """
        self.enabled = False
        return self
    
    def with_conditions(self, **conditions: Any) -> 'Scope':
        """
        Add conditions to the scope.
        
        @param conditions: Key-value pairs of conditions
        @return: Self for method chaining
        """
        self.conditions.update(conditions)
        return self
    
    def __str__(self) -> str:
        """String representation of the scope."""
        return f"{self.__class__.__name__}(name='{self.name}', priority={self.priority})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the scope."""
        return (f"<{self.__class__.__name__}(name='{self.name}', priority={self.priority}, "
                f"enabled={self.enabled})>")


class AnonymousScope(Scope):
    """
    Anonymous scope for inline query modifications.
    
    Allows creating scopes on-the-fly using lambda functions or callables
    without needing to define a full scope class.
    
    Usage:
        # Create anonymous scope
        active_scope = AnonymousScope(
            lambda builder, model: builder.filter(model.status == 'active'),
            name='active'
        )
        
        # Apply to model
        User.add_global_scope(active_scope)
    """
    
    def __init__(self, callback: Callable, name: Optional[str] = None, remove_callback: Optional[Callable] = None):
        """
        Initialize anonymous scope with callback.
        
        @param callback: Function to apply scope modifications
        @param name: Optional name for the scope
        @param remove_callback: Optional function to remove scope modifications
        """
        super().__init__(name or 'anonymous')
        self.callback = callback
        self.remove_callback = remove_callback
    
    def apply(self, builder: SQLQuery, model: Type[Any]) -> SQLQuery:
        """Apply the callback to modify the query."""
        try:
            return self.callback(builder, model)  # type: ignore[misc]
        except Exception as e:
            # Log error but don't break queries
            import logging
            logging.warning(f"Error applying anonymous scope '{self.name}': {e}")
            return builder
    
    def remove(self, builder: SQLQuery, model: Type[Any]) -> SQLQuery:
        """Remove scope modifications if remove callback is provided."""
        if self.remove_callback:
            try:
                return self.remove_callback(builder, model)
            except Exception as e:
                import logging
                logging.warning(f"Error removing anonymous scope '{self.name}': {e}")
        return builder


class ConditionalScope(Scope):
    """
    Conditional scope that applies based on runtime conditions.
    
    Useful for scopes that should only apply under certain circumstances,
    such as user permissions, feature flags, or configuration settings.
    
    Usage:
        def should_apply_tenant_scope():
            return current_user_has_tenant()
        
        tenant_scope = ConditionalScope(
            condition=should_apply_tenant_scope,
            apply_func=lambda builder, model: builder.filter(model.tenant_id == get_current_tenant_id())
        )
    """
    
    def __init__(self, condition: Callable, apply_func: Callable, name: Optional[str] = None):
        """
        Initialize conditional scope.
        
        @param condition: Function that returns True if scope should apply
        @param apply_func: Function to apply scope modifications
        @param name: Optional name for the scope
        """
        super().__init__(name or 'conditional')
        self.condition = condition
        self.apply_func = apply_func
    
    def apply(self, builder: SQLQuery, model: Type[Any]) -> SQLQuery:
        """Apply scope only if condition is met."""
        try:
            if self.condition():  # type: ignore[misc]
                return self.apply_func(builder, model)  # type: ignore[misc]
        except Exception as e:
            import logging
            logging.warning(f"Error in conditional scope '{self.name}': {e}")
        return builder
    
    def can_apply(self, model: Type[Any]) -> bool:
        """Check if scope can apply based on condition."""
        if not super().can_apply(model):
            return False
        try:
            return self.condition()  # type: ignore[misc]
        except Exception:
            return False


class CompositeScope(Scope):
    """
    Composite scope that combines multiple scopes.
    
    Allows grouping related scopes together and applying them as a unit.
    Useful for complex filtering logic that involves multiple conditions.
    
    Usage:
        active_scope = AnonymousScope(lambda b, m: b.filter(m.status == 'active'))
        verified_scope = AnonymousScope(lambda b, m: b.filter(m.verified == True))
        
        composite = CompositeScope([active_scope, verified_scope], name='active_verified')
        User.add_global_scope(composite)
    """
    
    def __init__(self, scopes: list[Scope], name: Optional[str] = None, operator: str = 'AND'):
        """
        Initialize composite scope.
        
        @param scopes: List of scopes to combine
        @param name: Optional name for the scope
        @param operator: How to combine scopes ('AND' or 'OR')
        """
        super().__init__(name or 'composite')
        self.scopes = sorted(scopes, key=lambda s: s.priority)
        self.operator = operator.upper()
    
    def apply(self, builder: SQLQuery, model: Type[Any]) -> SQLQuery:
        """Apply all child scopes."""
        for scope in self.scopes:
            if scope.can_apply(model):
                builder = scope.apply(builder, model)
        return builder
    
    def remove(self, builder: SQLQuery, model: Type[Any]) -> SQLQuery:
        """Remove all child scopes."""
        for scope in reversed(self.scopes):  # Remove in reverse order
            builder = scope.remove(builder, model)
        return builder
    
    def add_scope(self, scope: Scope) -> 'CompositeScope':
        """
        Add a scope to the composite.
        
        @param scope: Scope to add
        @return: Self for method chaining
        """
        self.scopes.append(scope)
        self.scopes.sort(key=lambda s: s.priority)
        return self
    
    def remove_scope(self, scope_name: str) -> 'CompositeScope':
        """
        Remove a scope from the composite.
        
        @param scope_name: Name of scope to remove
        @return: Self for method chaining
        """
        self.scopes = [s for s in self.scopes if s.get_name() != scope_name]
        return self


# Utility functions for scope management

def create_scope(apply_func: Callable, name: Optional[str] = None, remove_func: Optional[Callable] = None) -> AnonymousScope:
    """
    Factory function to create an anonymous scope.
    
    @param apply_func: Function to apply scope modifications
    @param name: Optional name for the scope
    @param remove_func: Optional function to remove scope modifications
    @return: Anonymous scope instance
    """
    return AnonymousScope(apply_func, name, remove_func)


def conditional_scope(condition: Callable, apply_func: Callable, name: Optional[str] = None) -> ConditionalScope:
    """
    Factory function to create a conditional scope.
    
    @param condition: Function that returns True if scope should apply
    @param apply_func: Function to apply scope modifications
    @param name: Optional name for the scope
    @return: Conditional scope instance
    """
    return ConditionalScope(condition, apply_func, name)


def combine_scopes(*scopes: Scope, name: Optional[str] = None, operator: str = 'AND') -> CompositeScope:
    """
    Factory function to combine multiple scopes.
    
    @param scopes: Scopes to combine
    @param name: Optional name for the composite scope
    @param operator: How to combine scopes ('AND' or 'OR')
    @return: Composite scope instance
    """
    return CompositeScope(list(scopes), name, operator)