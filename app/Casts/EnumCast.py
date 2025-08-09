from __future__ import annotations

from typing import Any, Optional, Type, TypeVar, Union, TYPE_CHECKING, Protocol
from app.Enums.BaseEnum import BaseEnum

if TYPE_CHECKING:
    from app.Models.BaseModel import BaseModel


class CastInterface(Protocol):
    """Interface for Laravel-style attribute casting."""
    
    def get(self, model: 'BaseModel', key: str, value: Any, attributes: dict[str, Any]) -> Any:
        """Convert database value to Python value."""
        ...
    
    def set(self, model: 'BaseModel', key: str, value: Any, attributes: dict[str, Any]) -> Any:
        """Convert Python value to database value."""
        ...

E = TypeVar('E', bound=BaseEnum)


class EnumCast(CastInterface):
    """
    Cast for Laravel-style enum values.
    
    Automatically converts between database values and enum instances,
    similar to Laravel's enum casting functionality.
    """
    
    def __init__(self, enum_class: Type[BaseEnum]) -> None:
        self.enum_class = enum_class
    
    def get(self, model: 'BaseModel', key: str, value: Any, attributes: dict[str, Any]) -> Optional[BaseEnum]:
        """Convert database value to enum instance."""
        if value is None:
            return None
        
        try:
            return self.enum_class.from_value(value)
        except (ValueError, KeyError):
            # Return None for invalid values instead of raising exception
            return None
    
    def set(self, model: 'BaseModel', key: str, value: Any, attributes: dict[str, Any]) -> Any:
        """Convert enum instance to database value."""
        if value is None:
            return None
        
        if isinstance(value, BaseEnum):
            return value.value
        
        # Try to create enum from value
        try:
            enum_instance = self.enum_class.from_value(value)
            return enum_instance.value
        except (ValueError, KeyError):
            # Return the original value if it can't be converted
            return value


class NullableEnumCast(EnumCast):
    """
    Enum cast that explicitly handles null values.
    """
    
    def get(self, model: 'BaseModel', key: str, value: Any, attributes: dict[str, Any]) -> Optional[BaseEnum]:
        """Convert database value to enum instance, allowing null."""
        if value is None or value == '':
            return None
        
        return super().get(model, key, value, attributes)
    
    def set(self, model: 'BaseModel', key: str, value: Any, attributes: dict[str, Any]) -> Any:
        """Convert enum instance to database value, handling null."""
        if value is None or value == '':
            return None
        
        return super().set(model, key, value, attributes)


class EnumCollectionCast(CastInterface):
    """
    Cast for collections/arrays of enum values.
    """
    
    def __init__(self, enum_class: Type[BaseEnum]) -> None:
        self.enum_class = enum_class
    
    def get(self, model: 'BaseModel', key: str, value: Any, attributes: dict[str, Any]) -> list[BaseEnum]:
        """Convert database value to list of enum instances."""
        if value is None:
            return []
        
        # Handle JSON string
        if isinstance(value, str):
            import json
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return []
        
        if not isinstance(value, list):
            return []
        
        enums = []
        for item in value:
            try:
                enum_instance = self.enum_class.from_value(item)
                enums.append(enum_instance)
            except (ValueError, KeyError):
                # Skip invalid values
                continue
        
        return enums
    
    def set(self, model: 'BaseModel', key: str, value: Any, attributes: dict[str, Any]) -> str:
        """Convert list of enum instances to JSON string."""
        if value is None:
            return '[]'
        
        if not isinstance(value, list):
            return '[]'
        
        import json
        enum_values = []
        for item in value:
            if isinstance(item, BaseEnum):
                enum_values.append(item.value)
            else:
                # Try to convert to enum first
                try:
                    enum_instance = self.enum_class.from_value(item)
                    enum_values.append(enum_instance.value)
                except (ValueError, KeyError):
                    # Include raw value if conversion fails
                    enum_values.append(item)
        
        return json.dumps(enum_values)


def enum_cast(enum_class: Type[BaseEnum]) -> EnumCast:
    """Helper function to create enum cast."""
    return EnumCast(enum_class)


def nullable_enum_cast(enum_class: Type[BaseEnum]) -> NullableEnumCast:
    """Helper function to create nullable enum cast."""
    return NullableEnumCast(enum_class)


def enum_collection_cast(enum_class: Type[BaseEnum]) -> EnumCollectionCast:
    """Helper function to create enum collection cast."""
    return EnumCollectionCast(enum_class)