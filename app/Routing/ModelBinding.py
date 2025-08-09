from __future__ import annotations

from typing import Dict, Any, Type, Optional, Union, Callable, get_type_hints
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from inspect import signature, Parameter
import re

from app.Models.BaseModel import BaseModel
from config.database import get_db


class ModelResolver:
    """Laravel-style model resolver for route model binding."""
    
    def __init__(self) -> None:
        self.bindings: Dict[str, Type[BaseModel]] = {}
        self.resolvers: Dict[Type[BaseModel], Callable] = {}
        self.route_key_names: Dict[Type[BaseModel], str] = {}
    
    def bind(self, key: str, model: Type[BaseModel]) -> None:
        """Bind a route parameter to a model."""
        self.bindings[key] = model
    
    def explicit_bind(self, key: str, resolver: Callable) -> None:
        """Explicitly bind a route parameter to a custom resolver."""
        self.bindings[key] = resolver  # type: ignore
    
    def substitute_bindings(self, route_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute route parameters with model instances."""
        substituted = {}
        
        for key, value in route_parameters.items():
            if key in self.bindings:
                binding = self.bindings[key]
                
                try:
                    if isinstance(binding, type) and issubclass(binding, BaseModel):
                        # Model binding
                        substituted[key] = self._resolve_model(binding, value)
                    elif callable(binding):  # type: ignore[unreachable]
                        # Custom resolver
                        substituted[key] = binding(value)
                    else:
                        substituted[key] = value
                except Exception:
                    substituted[key] = value
            else:
                substituted[key] = value
        
        return substituted
    
    def _resolve_model(self, model: Type[BaseModel], value: Any) -> BaseModel:
        """Resolve a model instance from a route parameter."""
        if model in self.resolvers:
            return self.resolvers[model](value)  # type: ignore
        
        # Default resolution by primary key
        db = next(get_db())
        try:
            route_key = self.route_key_names.get(model, 'id')
            
            if route_key == 'id':
                # Primary key lookup
                instance = db.query(model).filter(model.id == value).first()
            else:
                # Custom route key lookup
                instance = db.query(model).filter(getattr(model, route_key) == value).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
            
            return instance
        finally:
            db.close()
    
    def set_route_key_name(self, model: Type[BaseModel], key: str) -> None:
        """Set the route key name for a model."""
        self.route_key_names[model] = key
    
    def get_route_key_name(self, model: Type[BaseModel]) -> str:
        """Get the route key name for a model."""
        return self.route_key_names.get(model, 'id')


class RouteModelBinding:
    """Laravel-style route model binding for FastAPI."""
    
    def __init__(self) -> None:
        self.resolver = ModelResolver()
    
    def bind(self, key: str, model: Type[BaseModel]) -> None:
        """Bind a route parameter to a model."""
        self.resolver.bind(key, model)
    
    def explicit_bind(self, key: str, resolver: Callable) -> None:
        """Explicitly bind a route parameter to a custom resolver."""
        self.resolver.explicit_bind(key, resolver)
    
    def create_dependency(self, model: Type[BaseModel], parameter_name: str) -> Callable:
        """Create a FastAPI dependency for model binding."""
        def dependency(
            param_value: Union[str, int],  # Will be filled by FastAPI
            db: Session = Depends(get_db)  # type: ignore[assignment]
        ) -> BaseModel:
            """Resolve model instance from route parameter."""
            route_key = self.resolver.get_route_key_name(model)
            
            if model in self.resolver.resolvers:
                from typing import cast
                return cast(BaseModel, self.resolver.resolvers[model](param_value))
            
            if route_key == 'id':
                # Primary key lookup
                instance = db.query(model).filter(model.id == param_value).first()
            else:
                # Custom route key lookup
                instance = db.query(model).filter(getattr(model, route_key) == param_value).first()
            
            if not instance:
                raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
            
            return instance
        
        return dependency
    
    def auto_bind_from_function(self, func: Callable) -> Dict[str, Callable]:
        """Automatically bind models based on function type hints."""
        type_hints = get_type_hints(func)
        dependencies = {}
        
        for param_name, param_type in type_hints.items():
            if (isinstance(param_type, type) and 
                issubclass(param_type, BaseModel) and 
                param_type != BaseModel):
                
                dependencies[param_name] = self.create_dependency(param_type, param_name)
        
        return dependencies


class ImplicitModelBinding:
    """Implicit model binding based on type hints."""
    
    @staticmethod
    def create_binding_dependency(model: Type[BaseModel]) -> Callable:
        """Create a dependency for implicit model binding."""
        def resolve_model(
            model_id: Union[str, int],
            db: Session = Depends(get_db)  # type: ignore[assignment]
        ) -> BaseModel:
            """Resolve model instance."""
            instance = db.query(model).filter(model.id == model_id).first()
            if not instance:
                raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
            return instance
        
        return resolve_model


class ScopedBinding:
    """Scoped bindings for nested resource routes."""
    
    def __init__(self) -> None:
        self.scoped_bindings: Dict[str, Dict[str, Type[BaseModel]]] = {}
    
    def scope_bindings(self, bindings: Dict[str, Type[BaseModel]]) -> None:
        """Register scoped bindings."""
        for key, model in bindings.items():
            if key not in self.scoped_bindings:
                self.scoped_bindings[key] = {}
            self.scoped_bindings[key].update({model.__name__.lower(): model})
    
    def resolve_scoped(self, parent_key: str, child_key: str, parent_id: Any, child_id: Any) -> Any:
        """Resolve scoped model binding."""
        if parent_key not in self.scoped_bindings:
            raise HTTPException(status_code=404, detail="Invalid parent resource")
        
        if child_key not in self.scoped_bindings[parent_key]:
            raise HTTPException(status_code=404, detail="Invalid child resource")
        
        parent_model = self.scoped_bindings[parent_key][parent_key]
        child_model = self.scoped_bindings[parent_key][child_key]
        
        db = next(get_db())
        try:
            # Resolve parent
            parent = db.query(parent_model).filter(parent_model.id == parent_id).first()
            if not parent:
                raise HTTPException(status_code=404, detail=f"{parent_model.__name__} not found")
            
            # Resolve child within parent scope
            child = db.query(child_model).filter(
                child_model.id == child_id,
                getattr(child_model, f"{parent_key}_id") == parent_id
            ).first()
            
            if not child:
                raise HTTPException(status_code=404, detail=f"{child_model.__name__} not found")
            
            return parent, child
        finally:
            db.close()


class BindingSubstitution:
    """Handle route parameter substitution for model bindings."""
    
    def __init__(self, resolver: ModelResolver) -> None:
        self.resolver = resolver
    
    def substitute_route_parameters(self, route: str, parameters: Dict[str, Any]) -> str:
        """Substitute route parameters with actual values."""
        # Replace {parameter} with actual values
        pattern = r'\{(\w+)\}'
        
        def replace_param(match: re.Match) -> str:
            param_name = match.group(1)
            if param_name in parameters:
                value = parameters[param_name]
                if isinstance(value, BaseModel):
                    # Use route key for model instances
                    route_key = self.resolver.get_route_key_name(type(value))
                    attr_value = getattr(value, route_key)
                    return str(attr_value)
                return str(value)
            return str(match.group(0))
        
        return re.sub(pattern, replace_param, route)


# Global model binding instance
route_model_binding = RouteModelBinding()

# Helper functions for Laravel-style binding
def model(parameter: str, model_class: Type[BaseModel]) -> None:
    """Laravel-style model binding."""
    route_model_binding.bind(parameter, model_class)

def bind(key: str, resolver: Callable) -> None:
    """Laravel-style explicit binding."""
    route_model_binding.explicit_bind(key, resolver)

def substitute_bindings(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Substitute route bindings."""
    return route_model_binding.resolver.substitute_bindings(parameters)