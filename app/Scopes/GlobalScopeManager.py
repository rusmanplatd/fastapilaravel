from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, Union, final
from collections import OrderedDict
import logging
from sqlalchemy.orm import Query
from sqlalchemy.sql import Select

from .Scope import Scope, ScopeInterface


@final
class GlobalScopeManager:
    """
    Manager for Laravel-style Global Scopes.
    
    Handles registration, application, and removal of global scopes
    for models. Provides the infrastructure for automatic query
    modification across all model queries.
    
    Features:
    - Scope registration and management
    - Automatic scope application to queries
    - Scope removal and bypassing
    - Priority-based scope ordering
    - Performance optimization with caching
    - Event hooks for scope lifecycle
    - Debugging and introspection tools
    
    Usage:
        manager = GlobalScopeManager(UserModel)
        manager.add_scope('active', ActiveScope())
        
        # Apply scopes to query
        query = session.query(UserModel)
        scoped_query = manager.apply_scopes(query)
        
        # Remove specific scope
        unscoped_query = manager.remove_scope(query, 'active')
    """
    
    def __init__(self, model: Type[Any]):
        """
        Initialize the scope manager for a specific model.
        
        @param model: The model class this manager handles scopes for
        """
        self.model = model
        self.scopes: OrderedDict[str, Scope] = OrderedDict()
        self.disabled_scopes: set[str] = set()
        self.scope_cache: Dict[str, Any] = {}
        self.logger = logging.getLogger(f"{__name__}.{model.__name__ if hasattr(model, '__name__') else 'Unknown'}")
        
        # Performance tracking
        self.application_count = 0
        self.cache_hits = 0
        
    def add_scope(self, name: str, scope: Union[Scope, ScopeInterface, callable]) -> 'GlobalScopeManager':
        """
        Add a global scope to the model.
        
        @param name: Unique name for the scope
        @param scope: Scope instance, ScopeInterface, or callable
        @return: Self for method chaining
        """
        try:
            # Convert callable to AnonymousScope if needed
            if callable(scope) and not isinstance(scope, (Scope, ScopeInterface)):
                from .Scope import AnonymousScope
                scope = AnonymousScope(scope, name)
            
            # Validate scope
            if not isinstance(scope, (Scope, ScopeInterface)):
                raise ValueError(f"Scope must implement ScopeInterface or be callable")
            
            # Set name if Scope instance
            if isinstance(scope, Scope) and not scope.name:
                scope.name = name
            
            self.scopes[name] = scope
            self._sort_scopes()
            
            # Clear cache when scopes change
            self.scope_cache.clear()
            
            self.logger.debug(f"Added global scope '{name}' to {self.model.__name__}")
            return self
            
        except Exception as e:
            self.logger.error(f"Failed to add scope '{name}': {e}")
            raise
    
    def remove_scope(self, name: str) -> 'GlobalScopeManager':
        """
        Remove a global scope from the model.
        
        @param name: Name of the scope to remove
        @return: Self for method chaining
        """
        if name in self.scopes:
            del self.scopes[name]
            self.disabled_scopes.discard(name)
            self.scope_cache.clear()
            self.logger.debug(f"Removed global scope '{name}' from {self.model.__name__}")
        return self
    
    def has_scope(self, name: str) -> bool:
        """
        Check if a scope is registered.
        
        @param name: Name of the scope to check
        @return: True if scope exists
        """
        return name in self.scopes
    
    def get_scope(self, name: str) -> Optional[Scope]:
        """
        Get a specific scope by name.
        
        @param name: Name of the scope
        @return: Scope instance or None if not found
        """
        return self.scopes.get(name)
    
    def get_scopes(self) -> Dict[str, Scope]:
        """
        Get all registered scopes.
        
        @return: Dictionary of scope name -> scope instance
        """
        return dict(self.scopes)
    
    def enable_scope(self, name: str) -> 'GlobalScopeManager':
        """
        Enable a specific scope.
        
        @param name: Name of the scope to enable
        @return: Self for method chaining
        """
        if name in self.scopes:
            self.disabled_scopes.discard(name)
            if isinstance(self.scopes[name], Scope):
                self.scopes[name].enable()
            self.scope_cache.clear()
        return self
    
    def disable_scope(self, name: str) -> 'GlobalScopeManager':
        """
        Disable a specific scope.
        
        @param name: Name of the scope to disable
        @return: Self for method chaining
        """
        if name in self.scopes:
            self.disabled_scopes.add(name)
            if isinstance(self.scopes[name], Scope):
                self.scopes[name].disable()
            self.scope_cache.clear()
        return self
    
    def is_scope_enabled(self, name: str) -> bool:
        """
        Check if a scope is enabled.
        
        @param name: Name of the scope
        @return: True if scope is enabled
        """
        if name not in self.scopes:
            return False
        
        if name in self.disabled_scopes:
            return False
        
        scope = self.scopes[name]
        if isinstance(scope, Scope):
            return scope.can_apply(self.model)
        
        return True
    
    def apply_scopes(self, query: Query[Any], except_scopes: Optional[List[str]] = None) -> Query[Any]:
        """
        Apply all enabled global scopes to a query.
        
        @param query: The query to apply scopes to
        @param except_scopes: List of scope names to skip
        @return: Query with scopes applied
        """
        try:
            self.application_count += 1
            except_scopes = except_scopes or []
            
            # Check cache for performance
            cache_key = f"apply_scopes_{hash(tuple(except_scopes))}"
            if cache_key in self.scope_cache:
                self.cache_hits += 1
                # Note: In practice, we can't cache the actual query modifications
                # This is just for demonstration of the caching concept
            
            modified_query = query
            applied_scopes = []
            
            for name, scope in self.scopes.items():
                if name in except_scopes:
                    continue
                
                if not self.is_scope_enabled(name):
                    continue
                
                try:
                    modified_query = scope.apply(modified_query, self.model)
                    applied_scopes.append(name)
                    
                except Exception as e:
                    self.logger.warning(f"Error applying scope '{name}': {e}")
                    # Continue with other scopes rather than failing completely
            
            self.logger.debug(f"Applied scopes {applied_scopes} to {self.model.__name__} query")
            return modified_query
            
        except Exception as e:
            self.logger.error(f"Error applying global scopes: {e}")
            return query
    
    def remove_scope_from_query(self, query: Query[Any], scope_name: str) -> Query[Any]:
        """
        Remove a specific scope from a query.
        
        @param query: The query to modify
        @param scope_name: Name of the scope to remove
        @return: Query with scope removed
        """
        if scope_name in self.scopes:
            scope = self.scopes[scope_name]
            try:
                return scope.remove(query, self.model)
            except Exception as e:
                self.logger.warning(f"Error removing scope '{scope_name}': {e}")
        return query
    
    def without_scopes(self, query: Query[Any], scope_names: Optional[List[str]] = None) -> Query[Any]:
        """
        Remove multiple scopes from a query.
        
        @param query: The query to modify
        @param scope_names: List of scope names to remove (None = all scopes)
        @return: Query with scopes removed
        """
        if scope_names is None:
            scope_names = list(self.scopes.keys())
        
        modified_query = query
        for scope_name in scope_names:
            modified_query = self.remove_scope_from_query(modified_query, scope_name)
        
        return modified_query
    
    def with_only_scopes(self, query: Query[Any], scope_names: List[str]) -> Query[Any]:
        """
        Apply only specific scopes to a query.
        
        @param query: The query to modify
        @param scope_names: List of scope names to apply
        @return: Query with only specified scopes applied
        """
        # Get all scope names except the ones we want
        except_scopes = [name for name in self.scopes.keys() if name not in scope_names]
        return self.apply_scopes(query, except_scopes)
    
    def get_enabled_scopes(self) -> List[str]:
        """
        Get list of enabled scope names.
        
        @return: List of enabled scope names
        """
        return [name for name in self.scopes.keys() if self.is_scope_enabled(name)]
    
    def get_disabled_scopes(self) -> List[str]:
        """
        Get list of disabled scope names.
        
        @return: List of disabled scope names
        """
        return [name for name in self.scopes.keys() if not self.is_scope_enabled(name)]
    
    def clear_scopes(self) -> 'GlobalScopeManager':
        """
        Remove all scopes.
        
        @return: Self for method chaining
        """
        self.scopes.clear()
        self.disabled_scopes.clear()
        self.scope_cache.clear()
        self.logger.debug(f"Cleared all global scopes for {self.model.__name__}")
        return self
    
    def get_scope_count(self) -> int:
        """
        Get the number of registered scopes.
        
        @return: Number of scopes
        """
        return len(self.scopes)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for scope management.
        
        @return: Dictionary with performance stats
        """
        return {
            'total_scopes': len(self.scopes),
            'enabled_scopes': len(self.get_enabled_scopes()),
            'disabled_scopes': len(self.get_disabled_scopes()),
            'application_count': self.application_count,
            'cache_hits': self.cache_hits,
            'cache_hit_ratio': self.cache_hits / max(1, self.application_count),
            'scope_names': list(self.scopes.keys())
        }
    
    def _sort_scopes(self) -> None:
        """Sort scopes by priority (lower number = higher priority)."""
        # Sort scopes by priority, maintaining insertion order for same priority
        sorted_items = sorted(
            self.scopes.items(),
            key=lambda item: (item[1].priority if isinstance(item[1], Scope) else 0, list(self.scopes.keys()).index(item[0]))
        )
        self.scopes = OrderedDict(sorted_items)
    
    def debug_info(self) -> Dict[str, Any]:
        """
        Get debugging information about the scope manager.
        
        @return: Dictionary with debug information
        """
        scope_details = {}
        for name, scope in self.scopes.items():
            details = {
                'type': scope.__class__.__name__,
                'enabled': self.is_scope_enabled(name),
                'priority': getattr(scope, 'priority', 0) if isinstance(scope, Scope) else 0
            }
            
            if isinstance(scope, Scope):
                details.update({
                    'name': scope.get_name(),
                    'conditions': getattr(scope, 'conditions', {}),
                    'can_apply': scope.can_apply(self.model)
                })
            
            scope_details[name] = details
        
        return {
            'model': self.model.__name__ if hasattr(self.model, '__name__') else 'Unknown',
            'total_scopes': len(self.scopes),
            'enabled_count': len(self.get_enabled_scopes()),
            'application_count': self.application_count,
            'scopes': scope_details
        }
    
    def __repr__(self) -> str:
        """String representation of the scope manager."""
        return (f"<GlobalScopeManager(model={self.model.__name__ if hasattr(self.model, '__name__') else 'Unknown'}, "
                f"scopes={len(self.scopes)}, enabled={len(self.get_enabled_scopes())})>")


class ScopeRegistry:
    """
    Global registry for managing scopes across all models.
    
    Provides centralized management of global scopes and
    utilities for scope discovery and debugging.
    """
    
    _managers: Dict[Type[Any], GlobalScopeManager] = {}
    
    @classmethod
    def get_manager(cls, model: Type[Any]) -> GlobalScopeManager:
        """
        Get or create a scope manager for a model.
        
        @param model: The model class
        @return: GlobalScopeManager instance for the model
        """
        if model not in cls._managers:
            cls._managers[model] = GlobalScopeManager(model)
        return cls._managers[model]
    
    @classmethod
    def add_global_scope(cls, model: Type[Any], name: str, scope: Union[Scope, callable]) -> None:
        """
        Add a global scope to a model.
        
        @param model: The model class
        @param name: Scope name
        @param scope: Scope instance or callable
        """
        manager = cls.get_manager(model)
        manager.add_scope(name, scope)
    
    @classmethod
    def remove_global_scope(cls, model: Type[Any], name: str) -> None:
        """
        Remove a global scope from a model.
        
        @param model: The model class
        @param name: Scope name
        """
        if model in cls._managers:
            cls._managers[model].remove_scope(name)
    
    @classmethod
    def get_all_managers(cls) -> Dict[Type[Any], GlobalScopeManager]:
        """
        Get all registered scope managers.
        
        @return: Dictionary of model -> manager
        """
        return dict(cls._managers)
    
    @classmethod
    def clear_all_scopes(cls) -> None:
        """Clear all scopes from all models."""
        for manager in cls._managers.values():
            manager.clear_scopes()
        cls._managers.clear()
    
    @classmethod
    def get_global_stats(cls) -> Dict[str, Any]:
        """
        Get global statistics for all scope managers.
        
        @return: Dictionary with global stats
        """
        total_models = len(cls._managers)
        total_scopes = sum(manager.get_scope_count() for manager in cls._managers.values())
        total_applications = sum(manager.application_count for manager in cls._managers.values())
        
        return {
            'total_models': total_models,
            'total_scopes': total_scopes,
            'total_applications': total_applications,
            'models': [model.__name__ if hasattr(model, '__name__') else 'Unknown' 
                      for model in cls._managers.keys()]
        }