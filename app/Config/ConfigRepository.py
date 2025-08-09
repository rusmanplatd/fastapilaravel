from __future__ import annotations

import json
import os
import re
import time
import weakref
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Pattern,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    final,
)
import importlib.util
import threading
from collections.abc import MutableMapping

from app.Support.Arr import Arr
from app.Support.Types import validate_types
from app.Utils.Helper import collect, now

ConfigT = TypeVar('ConfigT')


class ConfigValidator(ABC):
    """Laravel 12 configuration validator."""
    
    @abstractmethod
    def validate(self, key: str, value: Any) -> bool:
        """Validate configuration value."""
        pass
    
    @abstractmethod
    def get_error_message(self, key: str, value: Any) -> str:
        """Get validation error message."""
        pass


class RequiredValidator(ConfigValidator):
    """Validator for required configuration values."""
    
    def validate(self, key: str, value: Any) -> bool:
        """Check if value is present and not None."""
        return value is not None
    
    def get_error_message(self, key: str, value: Any) -> str:
        """Get error message for missing required value."""
        return f"Configuration key '{key}' is required but not set"


class TypeValidator(ConfigValidator):
    """Validator for configuration value types."""
    
    def __init__(self, expected_type: Type) -> None:
        self.expected_type = expected_type
    
    def validate(self, key: str, value: Any) -> bool:
        """Check if value is of expected type."""
        return isinstance(value, self.expected_type)
    
    def get_error_message(self, key: str, value: Any) -> str:
        """Get error message for type mismatch."""
        return f"Configuration key '{key}' must be of type {self.expected_type.__name__}, got {type(value).__name__}"


class RangeValidator(ConfigValidator):
    """Validator for numeric range validation."""
    
    def __init__(self, min_value: Optional[Union[int, float]] = None, max_value: Optional[Union[int, float]] = None) -> None:
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, key: str, value: Any) -> bool:
        """Check if numeric value is within range."""
        if not isinstance(value, (int, float)):
            return False
        
        if self.min_value is not None and value < self.min_value:
            return False
        
        if self.max_value is not None and value > self.max_value:
            return False
        
        return True
    
    def get_error_message(self, key: str, value: Any) -> str:
        """Get error message for range validation."""
        if self.min_value is not None and self.max_value is not None:
            return f"Configuration key '{key}' must be between {self.min_value} and {self.max_value}"
        elif self.min_value is not None:
            return f"Configuration key '{key}' must be at least {self.min_value}"
        elif self.max_value is not None:
            return f"Configuration key '{key}' must be at most {self.max_value}"
        return f"Configuration key '{key}' is out of range"


class RegexValidator(ConfigValidator):
    """Validator for regular expression matching."""
    
    def __init__(self, pattern: Union[str, Pattern[str]]) -> None:
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
    
    def validate(self, key: str, value: Any) -> bool:
        """Check if string value matches pattern."""
        if not isinstance(value, str):
            return False
        
        return bool(self.pattern.match(value))
    
    def get_error_message(self, key: str, value: Any) -> str:
        """Get error message for pattern mismatch."""
        return f"Configuration key '{key}' does not match required pattern"


class ChoicesValidator(ConfigValidator):
    """Validator for choice validation."""
    
    def __init__(self, choices: List[Any]) -> None:
        self.choices = choices
    
    def validate(self, key: str, value: Any) -> bool:
        """Check if value is in allowed choices."""
        return value in self.choices
    
    def get_error_message(self, key: str, value: Any) -> str:
        """Get error message for invalid choice."""
        return f"Configuration key '{key}' must be one of {self.choices}, got '{value}'"


class ConfigObserver(ABC):
    """Laravel 12 configuration observer."""
    
    @abstractmethod
    def on_config_changed(self, key: str, old_value: Any, new_value: Any) -> None:
        """Called when configuration value changes."""
        pass
    
    def on_config_set(self, key: str, value: Any) -> None:
        """Called when configuration value is set."""
        pass
    
    def on_config_removed(self, key: str, old_value: Any) -> None:
        """Called when configuration value is removed."""
        pass


class ConfigRepository(MutableMapping[str, Any]):
    """Laravel 12 enhanced configuration repository with validation, caching, and observers."""
    
    def __init__(self, items: Optional[Dict[str, Any]] = None) -> None:
        self._items: Dict[str, Any] = items or {}
        self._loaded_files: Dict[str, bool] = {}
        self._validators: Dict[str, List[ConfigValidator]] = {}
        self._observers: List[ConfigObserver] = []
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_ttl: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._published_configs: Dict[str, Dict[str, Any]] = {}
        self._config_schemas: Dict[str, Dict[str, Any]] = {}
        self._computed_values: Dict[str, Callable[[], Any]] = {}
        self._config_metadata: Dict[str, Dict[str, Any]] = {}
    
    @validate_types
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation with caching and computed values."""
        with self._lock:
            # Check for computed values first
            if key in self._computed_values:
                return self._computed_values[key]()
            
            # Check cache
            if self._is_cached(key):
                return self._cache[key]
            
            # Get value from items
            value = Arr.get(self._items, key, default)
            
            # Apply transformations if configured
            value = self._apply_transformations(key, value)
            
            # Cache the value if TTL is set
            if key in self._cache_ttl:
                self._cache[key] = value
                self._cache_timestamps[key] = time.time()
            
            return value
    
    @validate_types
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation with validation and observers."""
        with self._lock:
            # Validate the value
            if not self._validate_value(key, value):
                return
            
            # Get old value for observers
            old_value = self.get(key)
            
            # Set the value
            Arr.set(self._items, key, value)
            
            # Clear cache for this key and related keys
            self._clear_cache(key)
            
            # Notify observers
            self._notify_observers_set(key, value)
            if old_value != value:
                self._notify_observers_changed(key, old_value, value)
    
    @validate_types
    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        with self._lock:
            return Arr.has(self._items, key) or key in self._computed_values
    
    @validate_types
    def forget(self, key: str) -> None:
        """Remove a configuration value with observer notification."""
        with self._lock:
            old_value = self.get(key)
            Arr.forget(self._items, key)
            
            # Clear cache
            self._clear_cache(key)
            
            # Remove computed value if exists
            if key in self._computed_values:
                del self._computed_values[key]
            
            # Notify observers
            self._notify_observers_removed(key, old_value)
    
    def all(self) -> Dict[str, Any]:
        """Get all configuration items including computed values."""
        with self._lock:
            result = self._items.copy()
            
            # Include computed values
            for key, func in self._computed_values.items():
                try:
                    result[key] = func()
                except Exception:
                    pass  # Skip failed computed values
            
            return result
    
    def load_file(self, file_path: str, namespace: Optional[str] = None) -> None:
        """Load configuration from a file."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        # Determine file type and load accordingly
        if path.suffix == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        elif path.suffix == '.py':
            data = self._load_python_config(str(path))
        else:
            raise ValueError(f"Unsupported configuration file type: {path.suffix}")
        
        # Set namespace or merge with root
        if namespace:
            self.set(namespace, data)
        else:
            self._items.update(data)
        
        self._loaded_files[file_path] = True
    
    def _load_python_config(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from a Python file."""
        spec = importlib.util.spec_from_file_location("config", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load config from {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Extract public attributes (not starting with _)
        config = {}
        for name in dir(module):
            if not name.startswith('_'):
                config[name] = getattr(module, name)
        
        return config
    
    def load_directory(self, directory: str) -> None:
        """Load all configuration files from a directory."""
        path = Path(directory)
        
        if not path.exists() or not path.is_dir():
            raise NotADirectoryError(f"Configuration directory not found: {directory}")
        
        # Load .py and .json files
        for file_path in path.glob('*.py'):
            if file_path.name != '__init__.py':
                namespace = file_path.stem
                self.load_file(str(file_path), namespace)
        
        for file_path in path.glob('*.json'):
            namespace = file_path.stem
            self.load_file(str(file_path), namespace)
    
    def is_loaded(self, file_path: str) -> bool:
        """Check if a configuration file has been loaded."""
        return file_path in self._loaded_files
    
    def merge(self, items: Dict[str, Any]) -> None:
        """Merge configuration items."""
        self._items = Arr.merge_recursive(self._items, items)
    
    def prepend(self, key: str, value: Any) -> None:
        """Prepend a value to an array configuration option."""
        current = self.get(key, [])
        if not isinstance(current, list):
            current = [current]
        current.insert(0, value)
        self.set(key, current)
    
    def push(self, key: str, value: Any) -> None:
        """Push a value onto an array configuration option."""
        current = self.get(key, [])
        if not isinstance(current, list):
            current = [current]
        current.append(value)
        self.set(key, current)
    
    def env(self, key: str, default: Any = None) -> Any:
        """Get an environment variable with fallback to config."""
        env_value = os.getenv(key)
        if env_value is not None:
            return self._cast_env_value(env_value)
        return self.get(key, default)
    
    def _cast_env_value(self, value: str) -> Any:
        """Cast environment variable to appropriate type."""
        # Handle boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Handle null/none values
        if value.lower() in ('null', 'none', ''):
            return None
        
        # Try to cast to number
        try:
            # Try integer first
            if '.' not in value:
                return int(value)
            # Then float
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def offsetExists(self, key: str) -> bool:
        """ArrayAccess interface - check if offset exists."""
        return self.has(key)
    
    def offsetGet(self, key: str) -> Any:
        """ArrayAccess interface - get offset."""
        return self.get(key)
    
    def offsetSet(self, key: str, value: Any) -> None:
        """ArrayAccess interface - set offset."""
        self.set(key, value)
    
    def offsetUnset(self, key: str) -> None:
        """ArrayAccess interface - unset offset."""
        self.forget(key)
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists using 'in' operator."""
        return self.has(key)
    
    def __getitem__(self, key: str) -> Any:
        """Get item using bracket notation."""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """Set item using bracket notation."""
        self.set(key, value)
    
    def __delitem__(self, key: str) -> None:
        """Delete item using del statement."""
        self.forget(key)
    
    def __len__(self) -> int:
        """Get number of configuration items."""
        return len(self._items) + len(self._computed_values)
    
    def __iter__(self) -> Iterator[str]:
        """Iterate over configuration keys."""
        return iter(list(self._items.keys()) + list(self._computed_values.keys()))
    
    def keys(self) -> List[str]:
        """Get configuration keys."""
        return list(self._items.keys()) + list(self._computed_values.keys())
    
    def values(self) -> List[Any]:
        """Get configuration values."""
        return [self.get(key) for key in self.keys()]
    
    def items(self) -> List[Tuple[str, Any]]:
        """Get configuration items."""
        return [(key, self.get(key)) for key in self.keys()]
    
    def add_validator(self, key: str, validator: ConfigValidator) -> 'ConfigRepository':
        """Add validator for configuration key."""
        if key not in self._validators:
            self._validators[key] = []
        self._validators[key].append(validator)
        return self
    
    def add_required(self, key: str) -> 'ConfigRepository':
        """Mark configuration key as required."""
        return self.add_validator(key, RequiredValidator())
    
    def add_type_validator(self, key: str, expected_type: Type) -> 'ConfigRepository':
        """Add type validator for configuration key."""
        return self.add_validator(key, TypeValidator(expected_type))
    
    def add_range_validator(self, key: str, min_value: Optional[Union[int, float]] = None, max_value: Optional[Union[int, float]] = None) -> 'ConfigRepository':
        """Add range validator for configuration key."""
        return self.add_validator(key, RangeValidator(min_value, max_value))
    
    def add_regex_validator(self, key: str, pattern: Union[str, Pattern[str]]) -> 'ConfigRepository':
        """Add regex validator for configuration key."""
        return self.add_validator(key, RegexValidator(pattern))
    
    def add_choices_validator(self, key: str, choices: List[Any]) -> 'ConfigRepository':
        """Add choices validator for configuration key."""
        return self.add_validator(key, ChoicesValidator(choices))
    
    def add_observer(self, observer: ConfigObserver) -> 'ConfigRepository':
        """Add configuration observer."""
        self._observers.append(observer)
        return self
    
    def remove_observer(self, observer: ConfigObserver) -> 'ConfigRepository':
        """Remove configuration observer."""
        if observer in self._observers:
            self._observers.remove(observer)
        return self
    
    def set_cache_ttl(self, key: str, ttl: float) -> 'ConfigRepository':
        """Set cache TTL for configuration key."""
        self._cache_ttl[key] = ttl
        return self
    
    def clear_cache(self, key: Optional[str] = None) -> 'ConfigRepository':
        """Clear configuration cache."""
        with self._lock:
            if key:
                self._clear_cache(key)
            else:
                self._cache.clear()
                self._cache_timestamps.clear()
        return self
    
    def compute(self, key: str, func: Callable[[], Any]) -> 'ConfigRepository':
        """Add computed configuration value."""
        self._computed_values[key] = func
        return self
    
    def lazy(self, key: str, func: Callable[[], Any]) -> 'ConfigRepository':
        """Add lazy-loaded configuration value."""
        computed_value = None
        computed = False
        
        def lazy_loader() -> Any:
            nonlocal computed_value, computed
            if not computed:
                computed_value = func()
                computed = True
            return computed_value
        
        return self.compute(key, lazy_loader)
    
    def publish_config(self, name: str, config: Dict[str, Any], overwrite: bool = False) -> 'ConfigRepository':
        """Publish configuration for external use."""
        if name not in self._published_configs or overwrite:
            self._published_configs[name] = config
        return self
    
    def get_published_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get published configuration."""
        return self._published_configs.get(name)
    
    def get_published_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all published configurations."""
        return self._published_configs.copy()
    
    def set_schema(self, key: str, schema: Dict[str, Any]) -> 'ConfigRepository':
        """Set configuration schema for validation."""
        self._config_schemas[key] = schema
        return self
    
    def validate_schema(self, key: str) -> bool:
        """Validate configuration against schema."""
        if key not in self._config_schemas:
            return True
        
        # Implementation would validate against JSON schema or similar
        return True
    
    def set_metadata(self, key: str, metadata: Dict[str, Any]) -> 'ConfigRepository':
        """Set metadata for configuration key."""
        self._config_metadata[key] = metadata
        return self
    
    def get_metadata(self, key: str) -> Dict[str, Any]:
        """Get metadata for configuration key."""
        return self._config_metadata.get(key, {})
    
    def freeze(self, key: str) -> 'ConfigRepository':
        """Freeze configuration key to prevent changes."""
        metadata = self.get_metadata(key)
        metadata['frozen'] = True
        self.set_metadata(key, metadata)
        return self
    
    def is_frozen(self, key: str) -> bool:
        """Check if configuration key is frozen."""
        return self.get_metadata(key).get('frozen', False)
    
    def _validate_value(self, key: str, value: Any) -> bool:
        """Validate configuration value against all validators."""
        if self.is_frozen(key):
            raise ValueError(f"Configuration key '{key}' is frozen and cannot be modified")
        
        if key not in self._validators:
            return True
        
        for validator in self._validators[key]:
            if not validator.validate(key, value):
                raise ValueError(validator.get_error_message(key, value))
        
        return True
    
    def _is_cached(self, key: str) -> bool:
        """Check if value is cached and still valid."""
        if key not in self._cache:
            return False
        
        if key not in self._cache_ttl:
            return True
        
        elapsed = time.time() - self._cache_timestamps.get(key, 0)
        return elapsed < self._cache_ttl[key]
    
    def _clear_cache(self, key: str) -> None:
        """Clear cache for key and related keys."""
        # Clear direct cache
        if key in self._cache:
            del self._cache[key]
        if key in self._cache_timestamps:
            del self._cache_timestamps[key]
        
        # Clear cache for keys that start with this key (for nested structures)
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{key}.")]
        for k in keys_to_remove:
            del self._cache[k]
            if k in self._cache_timestamps:
                del self._cache_timestamps[k]
    
    def _apply_transformations(self, key: str, value: Any) -> Any:
        """Apply transformations to configuration value."""
        # Apply any registered transformations
        return value
    
    def _notify_observers_set(self, key: str, value: Any) -> None:
        """Notify observers of value set."""
        for observer in self._observers:
            try:
                observer.on_config_set(key, value)
            except Exception:
                pass  # Don't let observer errors break config
    
    def _notify_observers_changed(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notify observers of value change."""
        for observer in self._observers:
            try:
                observer.on_config_changed(key, old_value, new_value)
            except Exception:
                pass
    
    def _notify_observers_removed(self, key: str, old_value: Any) -> None:
        """Notify observers of value removal."""
        for observer in self._observers:
            try:
                observer.on_config_removed(key, old_value)
            except Exception:
                pass


# Global config instance
config_instance: Optional[ConfigRepository] = None


def config(key: Optional[str] = None, default: Any = None) -> Union[ConfigRepository, Any]:
    """Get the configuration repository or a configuration value."""
    global config_instance
    if config_instance is None:
        config_instance = ConfigRepository()
    
    if key is None:
        return config_instance
    
    return config_instance.get(key, default)


def config_path(path: str = '') -> str:
    """Get the path to the configuration directory."""
    from app.Foundation import app
    return app().config_path(path)


# Laravel 12 configuration helpers
@validate_types
def config_cache(key: str, value: Any, ttl: float = 3600) -> Any:
    """Cache a configuration value with TTL."""
    global config_instance
    if config_instance is None:
        config_instance = ConfigRepository()
    
    config_instance.set_cache_ttl(key, ttl)
    config_instance.set(key, value)
    return value


@validate_types
def config_lazy(key: str, factory: Callable[[], Any]) -> Any:
    """Create a lazy-loaded configuration value."""
    global config_instance
    if config_instance is None:
        config_instance = ConfigRepository()
    
    config_instance.lazy(key, factory)
    return config_instance.get(key)


@validate_types
def config_compute(key: str, factory: Callable[[], Any]) -> Any:
    """Create a computed configuration value."""
    global config_instance
    if config_instance is None:
        config_instance = ConfigRepository()
    
    config_instance.compute(key, factory)
    return config_instance.get(key)


@validate_types
def config_required(key: str, message: Optional[str] = None) -> Any:
    """Get required configuration value or raise error."""
    value = config(key)
    if value is None:
        raise ValueError(message or f"Required configuration '{key}' is not set")
    return value


@validate_types
def config_validate(key: str, validator: ConfigValidator) -> ConfigRepository:
    """Add validator to configuration key."""
    global config_instance
    if config_instance is None:
        config_instance = ConfigRepository()
    
    return config_instance.add_validator(key, validator)


@validate_types
def config_freeze(key: str) -> None:
    """Freeze configuration key to prevent changes."""
    global config_instance
    if config_instance is None:
        config_instance = ConfigRepository()
    
    config_instance.freeze(key)


@validate_types
def config_publish(name: str, config_data: Dict[str, Any], overwrite: bool = False) -> None:
    """Publish configuration for external use."""
    global config_instance
    if config_instance is None:
        config_instance = ConfigRepository()
    
    config_instance.publish_config(name, config_data, overwrite)


# Export Laravel 12 configuration functionality
__all__ = [
    'ConfigRepository',
    'ConfigValidator',
    'RequiredValidator',
    'TypeValidator',
    'RangeValidator',
    'RegexValidator',
    'ChoicesValidator',
    'ConfigObserver',
    'config',
    'config_path',
    'config_cache',
    'config_lazy',
    'config_compute',
    'config_required',
    'config_validate',
    'config_freeze',
    'config_publish',
]