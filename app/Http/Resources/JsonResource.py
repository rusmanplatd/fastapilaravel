from __future__ import annotations

from typing import Dict, List, Optional, Union, Type, TYPE_CHECKING, Callable, TypeVar, Generic
from abc import ABC, abstractmethod
from datetime import datetime
from pydantic import BaseModel

if TYPE_CHECKING:
    from fastapi import Request

ResourceT = TypeVar('ResourceT')
JsonValue = Union[str, int, float, bool, None, List['JsonValue'], Dict[str, 'JsonValue']]

class JsonResource(ABC, Generic[ResourceT]):
    """Laravel-style JSON Resource for API transformations."""
    
    def __init__(self, resource: ResourceT, request: Optional[Request] = None) -> None:
        self.resource = resource
        self.request = request
        self.with_data: Dict[str, JsonValue] = {}
        self.additional_data: Dict[str, JsonValue] = {}
    
    @abstractmethod
    def to_array(self, request: Optional[Request] = None) -> Dict[str, JsonValue]:
        """Transform the resource into an array."""
        pass
    
    def with_meta(self, meta: Dict[str, JsonValue]) -> JsonResource[ResourceT]:
        """Add meta data to the resource."""
        self.additional_data.update(meta)
        return self
    
    def additional(self, data: Dict[str, JsonValue]) -> JsonResource[ResourceT]:
        """Add additional data to the resource."""
        self.additional_data.update(data)
        return self
    
    def with_wrap(self, key: str) -> JsonResource[ResourceT]:
        """Wrap the resource data under a key."""
        self.wrap_key = key
        return self
    
    def to_dict(self) -> Dict[str, JsonValue]:
        """Convert resource to dictionary."""
        data = self.to_array()
        
        # Add additional data
        if self.additional_data:
            data.update(self.additional_data)
        
        return data
    
    def to_response(self) -> Dict[str, JsonValue]:
        """Convert resource to HTTP response format."""
        return {
            "data": self.to_dict(),
            "meta": self.additional_data.get("meta", {}),
            "links": self.additional_data.get("links", {})
        }
    
    @classmethod
    def collection(cls, resources: List[ResourceT], request: Optional[Request] = None) -> ResourceCollection:
        """Create a resource collection."""
        return ResourceCollection(resources, cls, request)  # type: ignore[arg-type]
    
    def when(self, condition: bool, value: JsonValue, default: JsonValue = None) -> JsonValue:
        """Conditionally include data."""
        return value if condition else default
    
    def when_loaded(self, relationship: str, value: JsonValue, default: JsonValue = None) -> JsonValue:
        """Include data when relationship is loaded."""
        if hasattr(self.resource, relationship):
            related = getattr(self.resource, relationship)  # type: ignore[misc]
            return value if related is not None else default  # type: ignore[misc]
        return default
    
    def merge_when(self, condition: bool, data: Dict[str, JsonValue]) -> Dict[str, JsonValue]:
        """Conditionally merge data."""
        return data if condition else {}


class ResourceCollection:
    """Laravel-style resource collection."""
    
    def __init__(self, resources: List[JsonValue], resource_class: Type[JsonResource[ResourceT]], request: Optional[Request] = None) -> None:
        self.resources = resources
        self.resource_class: Type[JsonResource[ResourceT]] = resource_class
        self.request = request
        self.additional_data: Dict[str, JsonValue] = {}
    
    def additional(self, data: Dict[str, JsonValue]) -> ResourceCollection:
        """Add additional data to the collection."""
        self.additional_data.update(data)
        return self
    
    def to_dict(self) -> Dict[str, JsonValue]:
        """Convert collection to dictionary."""
        data = [
            self.resource_class(resource, self.request).to_dict()  # type: ignore[arg-type]
            for resource in self.resources
        ]
        
        result: Dict[str, JsonValue] = {"data": data}  # type: ignore[dict-item]
        
        # Add additional data
        if self.additional_data:
            result.update(self.additional_data)
        
        return result
    
    def to_response(self) -> Dict[str, JsonValue]:
        """Convert collection to HTTP response format."""
        return self.to_dict()


class AnonymousResourceCollection(ResourceCollection):
    """Anonymous resource collection for inline transformations."""
    
    def __init__(self, resources: List[JsonValue], transform: Callable[[JsonValue], Dict[str, JsonValue]], request: Optional[Request] = None) -> None:
        self.resources = resources
        self.transform = transform
        self.request = request
        self.additional_data: Dict[str, JsonValue] = {}
    
    def to_dict(self) -> Dict[str, JsonValue]:
        """Convert collection to dictionary using transform function."""
        data = [self.transform(resource) for resource in self.resources]
        
        result: Dict[str, JsonValue] = {"data": data}  # type: ignore[dict-item]
        
        # Add additional data
        if self.additional_data:
            result.update(self.additional_data)
        
        return result


def resource(resource_data: JsonValue, resource_class: Optional[Type[JsonResource[ResourceT]]] = None, request: Optional[Request] = None) -> JsonValue:
    """Helper function to create resources."""
    if resource_class:
        return resource_class(resource_data, request)  # type: ignore[return-value,arg-type]
    
    # Return anonymous resource
    if hasattr(resource_data, 'to_dict'):
        return resource_data.to_dict()  # type: ignore[no-any-return,union-attr,misc]
    
    return resource_data


def collection(resources: List[JsonValue], resource_class: Optional[Type[JsonResource[ResourceT]]] = None, request: Optional[Request] = None) -> ResourceCollection:
    """Helper function to create resource collections."""
    if resource_class:
        return ResourceCollection(resources, resource_class, request)
    
    # Return anonymous collection
    return AnonymousResourceCollection(resources, lambda x: x.to_dict() if hasattr(x, 'to_dict') else x, request)  # type: ignore[misc,union-attr]