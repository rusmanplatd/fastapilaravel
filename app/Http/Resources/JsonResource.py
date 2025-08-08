from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Type, TYPE_CHECKING, Callable
from abc import ABC, abstractmethod
from datetime import datetime
from pydantic import BaseModel

if TYPE_CHECKING:
    from fastapi import Request


class JsonResource(ABC):
    """Laravel-style JSON Resource for API transformations."""
    
    def __init__(self, resource: Any, request: Optional[Request] = None) -> None:
        self.resource = resource
        self.request = request
        self.with_data: Dict[str, Any] = {}
        self.additional_data: Dict[str, Any] = {}
    
    @abstractmethod
    def to_array(self) -> Dict[str, Any]:
        """Transform the resource into an array."""
        pass
    
    def with_meta(self, meta: Dict[str, Any]) -> JsonResource:
        """Add meta data to the resource."""
        self.additional_data.update(meta)
        return self
    
    def additional(self, data: Dict[str, Any]) -> JsonResource:
        """Add additional data to the resource."""
        self.additional_data.update(data)
        return self
    
    def with_wrap(self, key: str) -> JsonResource:
        """Wrap the resource data under a key."""
        self.wrap_key = key
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert resource to dictionary."""
        data = self.to_array()
        
        # Add additional data
        if self.additional_data:
            data.update(self.additional_data)
        
        return data
    
    def to_response(self) -> Dict[str, Any]:
        """Convert resource to HTTP response format."""
        return {
            "data": self.to_dict(),
            "meta": self.additional_data.get("meta", {}),
            "links": self.additional_data.get("links", {})
        }
    
    @classmethod
    def collection(cls, resources: List[Any], request: Optional[Request] = None) -> ResourceCollection:
        """Create a resource collection."""
        return ResourceCollection(resources, cls, request)
    
    def when(self, condition: bool, value: Any, default: Any = None) -> Any:
        """Conditionally include data."""
        return value if condition else default
    
    def when_loaded(self, relationship: str, value: Any, default: Any = None) -> Any:
        """Include data when relationship is loaded."""
        if hasattr(self.resource, relationship):
            related = getattr(self.resource, relationship)
            return value if related is not None else default
        return default
    
    def merge_when(self, condition: bool, data: Dict[str, Any]) -> Dict[str, Any]:
        """Conditionally merge data."""
        return data if condition else {}


class ResourceCollection:
    """Laravel-style resource collection."""
    
    def __init__(self, resources: List[Any], resource_class: Type[JsonResource], request: Optional[Request] = None) -> None:
        self.resources = resources
        self.resource_class = resource_class
        self.request = request
        self.additional_data: Dict[str, Any] = {}
    
    def additional(self, data: Dict[str, Any]) -> ResourceCollection:
        """Add additional data to the collection."""
        self.additional_data.update(data)
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert collection to dictionary."""
        data = [
            self.resource_class(resource, self.request).to_dict()
            for resource in self.resources
        ]
        
        result = {"data": data}
        
        # Add additional data
        if self.additional_data:
            result.update(self.additional_data)
        
        return result
    
    def to_response(self) -> Dict[str, Any]:
        """Convert collection to HTTP response format."""
        return self.to_dict()


class AnonymousResourceCollection(ResourceCollection):
    """Anonymous resource collection for inline transformations."""
    
    def __init__(self, resources: List[Any], transform: Callable[[Any], Dict[str, Any]], request: Optional[Request] = None) -> None:
        self.resources = resources
        self.transform = transform
        self.request = request
        self.additional_data: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert collection to dictionary using transform function."""
        data = [self.transform(resource) for resource in self.resources]
        
        result = {"data": data}
        
        # Add additional data
        if self.additional_data:
            result.update(self.additional_data)
        
        return result


def resource(resource_data: Any, resource_class: Optional[Type[JsonResource]] = None, request: Optional[Request] = None) -> Union[JsonResource, Dict[str, Any]]:
    """Helper function to create resources."""
    if resource_class:
        return resource_class(resource_data, request)
    
    # Return anonymous resource
    if hasattr(resource_data, 'to_dict'):
        return resource_data.to_dict()  # type: ignore[no-any-return]
    
    return resource_data  # type: ignore[no-any-return]


def collection(resources: List[Any], resource_class: Optional[Type[JsonResource]] = None, request: Optional[Request] = None) -> ResourceCollection:
    """Helper function to create resource collections."""
    if resource_class:
        return ResourceCollection(resources, resource_class, request)
    
    # Return anonymous collection
    return AnonymousResourceCollection(resources, lambda x: x.to_dict() if hasattr(x, 'to_dict') else x, request)