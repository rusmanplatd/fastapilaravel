"""
Laravel 9+ Modern Model Attributes module.

This module provides Laravel 9+ style Attribute support for model accessors and mutators.
Clean, modern implementation without legacy cruft.

Classes:
- Attribute: Main class for defining accessors/mutators
- AccessorMutatorManager: Manages attribute transformations for models

Helper Functions:
- string_accessor: Common string transformations
- datetime_accessor: Datetime formatting and timezone handling
- json_accessor: JSON serialization/deserialization
- money_accessor: Currency formatting
- enum_accessor: Enum value handling
- attribute: Decorator for creating attribute properties

Examples:
    # Modern Laravel 9+ Attribute syntax
    @property
    def full_name(self) -> Attribute:
        return Attribute.make(
            get=lambda value: f"{self.first_name} {self.last_name}",
            set=lambda value: self._split_full_name(value)
        )
    
    # Using helper functions
    @property
    def formatted_price(self) -> Attribute:
        return money_accessor(currency="USD", decimal_places=2)
"""

from .AccessorMutator import (
    Attribute,
    AccessorMutatorManager,
    string_accessor,
    datetime_accessor,
    json_accessor,
    money_accessor,
    enum_accessor,
    attribute
)

__all__ = [
    'Attribute',
    'AccessorMutatorManager',
    'string_accessor',
    'datetime_accessor', 
    'json_accessor',
    'money_accessor',
    'enum_accessor',
    'attribute'
]