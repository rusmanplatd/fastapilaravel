from __future__ import annotations

from typing import Any, List, Optional, Type
from app.Validation.Validator import ValidationRule
from app.Enums.BaseEnum import BaseEnum


class EnumRule(ValidationRule):
    """
    Validate that a field is a valid enum value.
    
    Similar to Laravel's Enum validation rule.
    """
    
    def __init__(self, enum_class: Type[BaseEnum]) -> None:
        self.enum_class = enum_class
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if value is None:
            return False
        
        try:
            self.enum_class.from_value(value)
            return True
        except (ValueError, KeyError):
            return False
    
    def message(self) -> str:
        valid_values = ', '.join(str(v) for v in self.enum_class.values())
        return f"The {{attribute}} field must be one of: {valid_values}."


class EnumKeyRule(ValidationRule):
    """
    Validate that a field is a valid enum name/key.
    """
    
    def __init__(self, enum_class: Type[BaseEnum]) -> None:
        self.enum_class = enum_class
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not isinstance(value, str):
            return False
        
        valid_names = self.enum_class.names()
        return value in valid_names
    
    def message(self) -> str:
        valid_names = ', '.join(self.enum_class.names())
        return f"The {{attribute}} field must be one of: {valid_names}."


class EnumExistsRule(ValidationRule):
    """
    Validate that an enum value exists and optionally meets additional criteria.
    """
    
    def __init__(self, enum_class: Type[BaseEnum], condition_method: Optional[str] = None) -> None:
        self.enum_class = enum_class
        self.condition_method = condition_method
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if value is None:
            return False
        
        try:
            enum_instance = self.enum_class.from_value(value)
            
            # Check additional condition if specified
            if self.condition_method:
                if hasattr(enum_instance, self.condition_method):
                    condition_method = getattr(enum_instance, self.condition_method)
                    if callable(condition_method):
                        return condition_method()
                return False
            
            return True
        except (ValueError, KeyError):
            return False
    
    def message(self) -> str:
        if self.condition_method:
            return f"The {{attribute}} field must be a valid {self.enum_class.__name__} that satisfies the condition."
        return f"The {{attribute}} field must be a valid {self.enum_class.__name__}."


class NullableEnumRule(ValidationRule):
    """
    Validate that a field is either null or a valid enum value.
    """
    
    def __init__(self, enum_class: Type[BaseEnum]) -> None:
        self.enum_class = enum_class
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if value is None or value == '':
            return True
        
        try:
            self.enum_class.from_value(value)
            return True
        except (ValueError, KeyError):
            return False
    
    def message(self) -> str:
        valid_values = ', '.join(str(v) for v in self.enum_class.values())
        return f"The {{attribute}} field must be null or one of: {valid_values}."


class EnumArrayRule(ValidationRule):
    """
    Validate that a field is an array of valid enum values.
    """
    
    def __init__(self, enum_class: Type[BaseEnum], min_items: Optional[int] = None, 
                 max_items: Optional[int] = None) -> None:
        self.enum_class = enum_class
        self.min_items = min_items
        self.max_items = max_items
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if not isinstance(value, list):
            return False
        
        # Check array size constraints
        if self.min_items is not None and len(value) < self.min_items:
            return False
        
        if self.max_items is not None and len(value) > self.max_items:
            return False
        
        # Validate each item
        for item in value:
            try:
                self.enum_class.from_value(item)
            except (ValueError, KeyError):
                return False
        
        return True
    
    def message(self) -> str:
        valid_values = ', '.join(str(v) for v in self.enum_class.values())
        size_constraint = ""
        
        if self.min_items is not None and self.max_items is not None:
            size_constraint = f" with {self.min_items}-{self.max_items} items"
        elif self.min_items is not None:
            size_constraint = f" with at least {self.min_items} items"
        elif self.max_items is not None:
            size_constraint = f" with at most {self.max_items} items"
        
        return f"The {{attribute}} field must be an array{size_constraint} containing only: {valid_values}."


class EnumSubsetRule(ValidationRule):
    """
    Validate that enum values are a subset of allowed values.
    """
    
    def __init__(self, enum_class: Type[BaseEnum], allowed_values: List[Any]) -> None:
        self.enum_class = enum_class
        self.allowed_values = allowed_values
    
    def passes(self, attribute: str, value: Any, parameters: Optional[List[str]] = None) -> bool:
        if value is None:
            return False
        
        # Handle array values
        if isinstance(value, list):
            for item in value:
                try:
                    enum_instance = self.enum_class.from_value(item)
                    if enum_instance.value not in self.allowed_values:
                        return False
                except (ValueError, KeyError):
                    return False
            return True
        
        # Handle single value
        try:
            enum_instance = self.enum_class.from_value(value)
            return enum_instance.value in self.allowed_values
        except (ValueError, KeyError):
            return False
    
    def message(self) -> str:
        allowed_values = ', '.join(str(v) for v in self.allowed_values)
        return f"The {{attribute}} field must be one of the allowed values: {allowed_values}."


# Helper functions for creating enum validation rules
def enum_rule(enum_class: Type[BaseEnum]) -> EnumRule:
    """Create an enum validation rule."""
    return EnumRule(enum_class)


def enum_key_rule(enum_class: Type[BaseEnum]) -> EnumKeyRule:
    """Create an enum key validation rule."""
    return EnumKeyRule(enum_class)


def enum_exists_rule(enum_class: Type[BaseEnum], condition_method: Optional[str] = None) -> EnumExistsRule:
    """Create an enum exists validation rule with optional condition."""
    return EnumExistsRule(enum_class, condition_method)


def nullable_enum_rule(enum_class: Type[BaseEnum]) -> NullableEnumRule:
    """Create a nullable enum validation rule."""
    return NullableEnumRule(enum_class)


def enum_array_rule(enum_class: Type[BaseEnum], min_items: Optional[int] = None, 
                   max_items: Optional[int] = None) -> EnumArrayRule:
    """Create an enum array validation rule."""
    return EnumArrayRule(enum_class, min_items, max_items)


def enum_subset_rule(enum_class: Type[BaseEnum], allowed_values: List[Any]) -> EnumSubsetRule:
    """Create an enum subset validation rule."""
    return EnumSubsetRule(enum_class, allowed_values)