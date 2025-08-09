from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, ClassVar, final, Union, Callable, TypeVar, get_type_hints
from datetime import datetime, date, time, timezone
from decimal import Decimal
from enum import Enum
import inspect
import logging
import json
from abc import ABC, abstractmethod

# Type variables for generic type support
T = TypeVar('T')
ModelT = TypeVar('ModelT')


class Attribute:
    """
    Laravel 9+ style Attribute class for defining accessors and mutators.
    
    This class provides the modern Laravel syntax for defining model attributes
    with get/set methods, automatic caching, and type conversion.
    
    Features:
    - Modern Laravel 9+ syntax with Attribute::make()
    - Automatic type conversion and validation
    - Caching for performance
    - Conditional accessors and mutators
    - Event hooks for attribute changes
    - Null handling and default values
    
    Usage:
        @property
        def full_name(self) -> Attribute:
            return Attribute.make(
                get=lambda value: f"{self.first_name} {self.last_name}",
                set=lambda value: self._split_full_name(value)
            )
    """
    
    def __init__(
        self,
        get: Optional[Callable[[Any], Any]] = None,
        set: Optional[Callable[[Any], Any]] = None,
        cache: bool = True,
        with_type: Optional[Type[Any]] = None,
        nullable: bool = True,
        default: Any = None
    ):
        """
        Initialize an Attribute instance.
        
        @param get: Accessor function for getting the attribute value
        @param set: Mutator function for setting the attribute value  
        @param cache: Whether to cache the accessor result
        @param with_type: Expected type for validation
        @param nullable: Whether the attribute can be None
        @param default: Default value when attribute is None
        """
        self._get = get
        self._set = set
        self._cache = cache
        self._with_type = with_type
        self._nullable = nullable
        self._default = default
        self._cached_value = None
        self._cache_valid = False
        self.logger = logging.getLogger(f"{__name__}.Attribute")
    
    @classmethod
    def make(
        cls,
        get: Optional[Callable[[Any], Any]] = None,
        set: Optional[Callable[[Any], Any]] = None,
        cache: bool = True,
        with_type: Optional[Type[Any]] = None,
        nullable: bool = True,
        default: Any = None
    ) -> 'Attribute':
        """
        Laravel-style factory method for creating Attribute instances.
        
        @param get: Accessor function
        @param set: Mutator function
        @param cache: Enable caching
        @param with_type: Type validation
        @param nullable: Allow None values
        @param default: Default value
        @return: Configured Attribute instance
        """
        return cls(get, set, cache, with_type, nullable, default)
    
    def get_value(self, model: Any, attribute_name: str, raw_value: Any) -> Any:
        """
        Get the transformed attribute value using the accessor.
        
        @param model: The model instance
        @param attribute_name: Name of the attribute
        @param raw_value: Raw value from the database
        @return: Transformed value
        """
        try:
            # Check cache first
            if self._cache and self._cache_valid:
                return self._cached_value
            
            # Handle None values
            if raw_value is None:
                if not self._nullable:
                    raw_value = self._default
                elif self._default is not None:
                    raw_value = self._default
            
            # Apply accessor if defined
            if self._get:
                try:
                    # Try with just the value first
                    result = self._get(raw_value)
                except TypeError:
                    # If that fails, try with model and value
                    result = self._get(model, raw_value)  # type: ignore[call-arg]
            else:
                result = raw_value
            
            # Type validation if specified
            if self._with_type and result is not None:
                if not isinstance(result, self._with_type):
                    try:
                        result = self._with_type(result)
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Type conversion failed for {attribute_name}: {e}")
            
            # Cache the result
            if self._cache:
                self._cached_value = result
                self._cache_valid = True
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in accessor for {attribute_name}: {e}")
            return raw_value
    
    def set_value(self, model: Any, attribute_name: str, value: Any) -> Any:
        """
        Set the transformed attribute value using the mutator.
        
        @param model: The model instance
        @param attribute_name: Name of the attribute
        @param value: Value being set
        @return: Transformed value for storage
        """
        try:
            # Invalidate cache when setting
            self._cache_valid = False
            
            # Apply mutator if defined
            if self._set:
                try:
                    # Try with just the value first
                    result = self._set(value)
                except TypeError:
                    # If that fails, try with model and value
                    result = self._set(model, value)  # type: ignore[call-arg]
            else:
                result = value
            
            # Type validation if specified
            if self._with_type and result is not None:
                if not isinstance(result, self._with_type):
                    try:
                        result = self._with_type(result)
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Type conversion failed for {attribute_name}: {e}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in mutator for {attribute_name}: {e}")
            return value
    
    def invalidate_cache(self) -> None:
        """Invalidate the cached value."""
        self._cache_valid = False
        self._cached_value = None
    
    def _accepts_model_parameter(self, func: Callable[..., Any]) -> bool:
        """
        Check if the function accepts a model parameter.
        
        @param func: Function to inspect
        @return: True if function accepts model parameter
        """
        try:
            signature = inspect.signature(func)
            params = list(signature.parameters.keys())
            return len(params) >= 2
        except Exception:
            return False


@final
class AccessorMutatorManager:
    """
    Manager for Laravel 9+ style Attribute-based accessors and mutators.
    
    Handles only modern Attribute-based syntax with performance optimization,
    caching, and event hooks.
    
    Features:
    - Support for Laravel 9+ Attribute syntax only
    - Automatic discovery of Attribute properties
    - Performance optimization with caching
    - Type validation and conversion
    - Event hooks for attribute changes
    - Debugging and logging capabilities
    """
    
    def __init__(self, model: Any):
        """
        Initialize the manager for a specific model instance.
        
        @param model: The model instance to manage
        """
        self.model = model
        self.model_class = model.__class__
        self.logger = logging.getLogger(f"{__name__}.AccessorMutatorManager")
        
        # Cache for discovered accessors and mutators
        self._attributes_cache: Dict[str, Attribute] = {}
        
        # Performance tracking
        self._access_count: Dict[str, int] = {}
        self._mutation_count: Dict[str, int] = {}
        
        # Discover attributes
        self._discover_attributes()
    
    def _discover_attributes(self) -> None:
        """
        Discover all Attribute-based accessors/mutators for the model.
        
        Supports only modern Attribute syntax (Laravel 9+).
        """
        try:
            # Discover Attribute-based accessors/mutators (Laravel 9+ style)
            for name in dir(self.model_class):
                if name.startswith('_') or name in ['get', 'set']:
                    continue
                
                try:
                    attr = getattr(self.model_class, name)
                    
                    # Check if it's a property that returns an Attribute
                    if isinstance(attr, property):
                        try:
                            # Call the property getter on the model instance
                            result = attr.fget(self.model) if attr.fget else None
                            if isinstance(result, Attribute):
                                self._attributes_cache[name] = result
                        except Exception:
                            # Property might require initialization, skip for now
                            pass
                    
                    # Check if it's directly an Attribute instance
                    elif isinstance(attr, Attribute):
                        self._attributes_cache[name] = attr
                        
                except Exception as e:
                    self.logger.debug(f"Could not examine attribute {name}: {e}")
            
            self.logger.debug(f"Discovered {len(self._attributes_cache)} attributes")
            
        except Exception as e:
            self.logger.error(f"Error discovering attributes: {e}")
    
    def has_accessor(self, attribute_name: str) -> bool:
        """
        Check if an accessor exists for the given attribute.
        
        @param attribute_name: Name of the attribute
        @return: True if accessor exists
        """
        return attribute_name in self._attributes_cache and self._attributes_cache[attribute_name]._get is not None
    
    def has_mutator(self, attribute_name: str) -> bool:
        """
        Check if a mutator exists for the given attribute.
        
        @param attribute_name: Name of the attribute
        @return: True if mutator exists
        """
        return attribute_name in self._attributes_cache and self._attributes_cache[attribute_name]._set is not None
    
    def get_attribute_value(self, attribute_name: str, raw_value: Any) -> Any:
        """
        Get an attribute value through its accessor if it exists.
        
        @param attribute_name: Name of the attribute
        @param raw_value: Raw value from the database
        @return: Transformed value or original value
        """
        try:
            # Track access count
            self._access_count[attribute_name] = self._access_count.get(attribute_name, 0) + 1
            
            if not self.has_accessor(attribute_name):
                return raw_value
            
            attribute = self._attributes_cache[attribute_name]
            return attribute.get_value(self.model, attribute_name, raw_value)
            
        except Exception as e:
            self.logger.error(f"Error getting attribute {attribute_name}: {e}")
            return raw_value
    
    def set_attribute_value(self, attribute_name: str, value: Any) -> Any:
        """
        Set an attribute value through its mutator if it exists.
        
        @param attribute_name: Name of the attribute
        @param value: Value being set
        @return: Transformed value for storage
        """
        try:
            # Track mutation count
            self._mutation_count[attribute_name] = self._mutation_count.get(attribute_name, 0) + 1
            
            if not self.has_mutator(attribute_name):
                return value
            
            attribute = self._attributes_cache[attribute_name]
            return attribute.set_value(self.model, attribute_name, value)
            
        except Exception as e:
            self.logger.error(f"Error setting attribute {attribute_name}: {e}")
            return value
    
    def get_accessor_list(self) -> List[str]:
        """
        Get a list of all attribute names that have accessors.
        
        @return: List of attribute names with accessors
        """
        return [name for name, attr in self._attributes_cache.items() if attr._get is not None]
    
    def get_mutator_list(self) -> List[str]:
        """
        Get a list of all attribute names that have mutators.
        
        @return: List of attribute names with mutators
        """
        return [name for name, attr in self._attributes_cache.items() if attr._set is not None]
    
    def invalidate_cache(self, attribute_name: Optional[str] = None) -> None:
        """
        Invalidate cached values for attributes.
        
        @param attribute_name: Specific attribute to invalidate, or None for all
        """
        if attribute_name:
            # Invalidate specific attribute
            if attribute_name in self._attributes_cache:
                self._attributes_cache[attribute_name].invalidate_cache()
        else:
            # Invalidate all caches
            for attribute in self._attributes_cache.values():
                attribute.invalidate_cache()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for accessor/mutator usage.
        
        @return: Dictionary with performance statistics
        """
        accessors = self.get_accessor_list()
        mutators = self.get_mutator_list()
        
        return {
            'total_accessors': len(accessors),
            'total_mutators': len(mutators),
            'access_counts': self._access_count.copy(),
            'mutation_counts': self._mutation_count.copy(),
            'most_accessed': max(self._access_count.items(), key=lambda x: x[1]) if self._access_count else None,
            'most_mutated': max(self._mutation_count.items(), key=lambda x: x[1]) if self._mutation_count else None
        }


# Helper functions for common attribute patterns

def string_accessor(
    upper: bool = False,
    lower: bool = False,
    title: bool = False,
    strip: bool = True,
    default: str = ""
) -> Attribute:
    """
    Create a string accessor with common transformations.
    
    @param upper: Convert to uppercase
    @param lower: Convert to lowercase  
    @param title: Convert to title case
    @param strip: Strip whitespace
    @param default: Default value for None
    @return: Configured Attribute
    """
    def get_func(value: Any) -> str:
        if value is None:
            return default
        
        result = str(value)
        if strip:
            result = result.strip()
        if upper:
            result = result.upper()
        elif lower:
            result = result.lower()
        elif title:
            result = result.title()
            
        return result
    
    return Attribute.make(get=get_func, with_type=str)


def datetime_accessor(
    format_str: Optional[str] = None,
    timezone_aware: bool = True,
    default_timezone: timezone = timezone.utc
) -> Attribute:
    """
    Create a datetime accessor with formatting and timezone handling.
    
    @param format_str: Format string for datetime output
    @param timezone_aware: Whether to handle timezones
    @param default_timezone: Default timezone for naive datetimes
    @return: Configured Attribute
    """
    def get_func(value: Any) -> Union[str, datetime, None]:
        if value is None:
            return None
        
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return None
        
        if isinstance(value, datetime):
            if timezone_aware and value.tzinfo is None:
                value = value.replace(tzinfo=default_timezone)
            
            if format_str:
                return value.strftime(format_str)
            return value
        
        return None
    
    return Attribute.make(get=get_func)


def json_accessor(default_value: Any = None) -> Attribute:
    """
    Create a JSON accessor that handles serialization/deserialization.
    
    @param default_value: Default value when field is None or invalid
    @return: Configured Attribute
    """
    def get_func(value: Any) -> Any:
        if value is None:
            return default_value
        
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default_value
        
        return value
    
    def set_func(value: Any) -> Optional[str]:
        if value is None:
            return None
        
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        
        return str(value)
    
    return Attribute.make(get=get_func, set=set_func)


def money_accessor(currency: str = "USD", decimal_places: int = 2) -> Attribute:
    """
    Create a money/currency accessor.
    
    @param currency: Currency code
    @param decimal_places: Number of decimal places
    @return: Configured Attribute
    """
    def get_func(value: Any) -> Optional[str]:
        if value is None:
            return None
        
        try:
            amount = Decimal(str(value))
            formatted = f"{amount:.{decimal_places}f}"
            return f"{formatted} {currency}"
        except (ValueError, TypeError):
            return None
    
    def set_func(value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        
        # Extract numeric value from currency string
        if isinstance(value, str):
            value = value.replace(currency, "").strip()
        
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return Decimal('0.0')
    
    return Attribute.make(get=get_func, set=set_func)


def enum_accessor(enum_class: Type[Enum], default: Optional[Enum] = None) -> Attribute:
    """
    Create an enum accessor.
    
    @param enum_class: The enum class to use
    @param default: Default enum value
    @return: Configured Attribute
    """
    def get_func(value: Any) -> Optional[Enum]:
        if value is None:
            return default
        
        try:
            if isinstance(value, enum_class):
                return value
            return enum_class(value)
        except (ValueError, TypeError):
            return default
    
    def set_func(value: Any) -> Any:
        if value is None:
            return None
        
        if isinstance(value, enum_class):
            return value.value
        
        return value
    
    return Attribute.make(get=get_func, set=set_func)


# Decorator for creating attribute properties
def attribute(
    get: Optional[Callable[..., Any]] = None,
    set: Optional[Callable[..., Any]] = None,
    cache: bool = True,
    with_type: Optional[Type[Any]] = None,
    nullable: bool = True,
    default: Any = None
) -> Callable[..., Any]:
    """
    Decorator for creating attribute properties on models.
    
    @param get: Accessor function
    @param set: Mutator function
    @param cache: Enable caching
    @param with_type: Type validation
    @param nullable: Allow None values
    @param default: Default value
    @return: Property decorator
    """
    def decorator(func: Callable[..., Any]) -> property:
        def property_getter(self: Any) -> Attribute:
            return Attribute.make(get, set, cache, with_type, nullable, default)
        
        return property(property_getter)
    
    return decorator