from __future__ import annotations

from typing import Any, Dict, Optional, Union, List, Callable
import os
import json
import ast
from pathlib import Path
from functools import wraps


class ConfigRepository:
    """Laravel-style configuration repository."""
    
    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._cached: Dict[str, Any] = {}
        self._observers: Dict[str, List[Callable[[str, Any], None]]] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from files."""
        # Load from environment first
        self._load_environment_config()
        
        # Load from config files
        config_dir = Path("config")
        if not config_dir.exists():
            return
        
        for config_file in config_dir.glob("*.py"):
            if config_file.name == "__init__.py":
                continue
            
            module_name = config_file.stem
            try:
                # Import the config module
                import importlib.util
                spec = importlib.util.spec_from_file_location(module_name, config_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Get all non-private attributes
                    config_data = {
                        key: value for key, value in module.__dict__.items()
                        if not key.startswith('_') and not callable(value)
                    }
                    
                    # Process environment variables in config
                    config_data = self._process_env_variables(config_data)
                    
                    self._config[module_name] = config_data
            except Exception as e:
                print(f"Error loading config {module_name}: {e}")
    
    def _load_environment_config(self) -> None:
        """Load configuration from environment variables."""
        env_file = Path(".env")
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            # Remove quotes if present
                            value = value.strip('"\'')
                            os.environ[key.strip()] = value
            except Exception as e:
                print(f"Error loading .env file: {e}")
    
    def _process_env_variables(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process environment variables in config data."""
        def process_value(value: Any) -> Any:
            if isinstance(value, str):
                # Check for env() function calls
                if value.startswith('env(') and value.endswith(')'):
                    try:
                        # Parse the env() call
                        env_call = value[4:-1]  # Remove 'env(' and ')'
                        if ',' in env_call:
                            parts = [part.strip().strip('\'"') for part in env_call.split(',')]
                            env_key = parts[0]
                            default_value = parts[1] if len(parts) > 1 else None
                        else:
                            env_key = env_call.strip('\'"')
                            default_value = None
                        
                        # Get environment variable
                        env_value = os.getenv(env_key, default_value)
                        
                        # Try to convert to appropriate type
                        if env_value is not None:
                            return self._convert_env_value(env_value)
                        return default_value
                    except Exception:
                        return value
                return value
            elif isinstance(value, dict):
                return {k: process_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [process_value(item) for item in value]
            return value
        
        return {k: process_value(v) for k, v in config_data.items()}
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # None/null values
        if value.lower() in ('null', 'none', ''):
            return None
        
        # Numeric values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # JSON values
        if value.startswith(('{', '[')):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # String value
        return value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation."""
        # Check cache first
        if key in self._cached:
            return self._cached[key]
        
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if not isinstance(value, dict):
                return default
            try:
                value = value[k]
            except KeyError:
                return default
        
        # Cache the result
        self._cached[key] = value
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation."""
        old_value = self.get(key)
        
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final value
        config[keys[-1]] = value
        
        # Clear cache for this key and related keys
        self._clear_cache(key)
        
        # Notify observers
        self._notify_observers(key, value, old_value)
    
    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        sentinel = object()
        return self.get(key, sentinel) is not sentinel
    
    def all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return self._config.copy()
    
    def forget(self, key: str) -> None:
        """Remove a configuration value."""
        keys = key.split('.')
        config = self._config
        
        try:
            # Navigate to the parent
            for k in keys[:-1]:
                config = config[k]
            
            # Remove the final key
            if keys[-1] in config:
                del config[keys[-1]]
        except (KeyError, TypeError):
            pass
    
    def env(self, key: str, default: Any = None) -> Any:
        """Get environment variable with optional default."""
        return os.getenv(key, default)
    
    def prepend(self, key: str, value: Any) -> None:
        """Prepend a value to a configuration array."""
        current = self.get(key, [])
        if isinstance(current, list):
            current.insert(0, value)
            self.set(key, current)
    
    def push(self, key: str, value: Any) -> None:
        """Push a value onto a configuration array."""
        current = self.get(key, [])
        if isinstance(current, list):
            current.append(value)
            self.set(key, current)
    
    def _clear_cache(self, key: str) -> None:
        """Clear cache entries that start with the given key."""
        keys_to_remove = [k for k in self._cached.keys() if k.startswith(key)]
        for k in keys_to_remove:
            del self._cached[k]
    
    def _notify_observers(self, key: str, new_value: Any, old_value: Any = None) -> None:
        """Notify observers of configuration changes."""
        # Notify exact key observers
        if key in self._observers:
            for observer in self._observers[key]:
                try:
                    observer(key, new_value)
                except Exception as e:
                    print(f"Error in config observer for {key}: {e}")
        
        # Notify wildcard observers
        for observer_key, observers in self._observers.items():
            if observer_key.endswith('*') and key.startswith(observer_key[:-1]):
                for observer in observers:
                    try:
                        observer(key, new_value)
                    except Exception as e:
                        print(f"Error in wildcard config observer for {observer_key}: {e}")
    
    def observe(self, key: str, callback: Callable[[str, Any], None]) -> None:
        """Register an observer for configuration changes."""
        if key not in self._observers:
            self._observers[key] = []
        self._observers[key].append(callback)
    
    def macro(self, name: str, callback: Callable[..., Any]) -> None:
        """Register a macro for the configuration repository."""
        setattr(self.__class__, name, callback)
    
    def extend(self, driver: str, callback: Callable[..., Any]) -> None:
        """Extend the configuration repository with custom drivers."""
        # This would be used for custom configuration sources
        pass
    
    def flush(self) -> None:
        """Flush all cached configuration."""
        self._cached.clear()
    
    def getMany(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple configuration values at once."""
        return {key: self.get(key) for key in keys}
    
    def prepend_if_missing(self, key: str, value: Any) -> None:
        """Prepend a value to an array if it's not already present."""
        current = self.get(key, [])
        if isinstance(current, list) and value not in current:
            current.insert(0, value)
            self.set(key, current)
    
    def push_if_missing(self, key: str, value: Any) -> None:
        """Push a value onto an array if it's not already present."""
        current = self.get(key, [])
        if isinstance(current, list) and value not in current:
            current.append(value)
            self.set(key, current)
    
    def merge(self, key: str, values: Dict[str, Any]) -> None:
        """Merge values into a configuration array."""
        current = self.get(key, {})
        if isinstance(current, dict):
            current.update(values)
            self.set(key, current)
    
    def when(self, condition: bool, key: str, value: Any) -> None:
        """Set a configuration value conditionally."""
        if condition:
            self.set(key, value)
    
    def unless(self, condition: bool, key: str, value: Any) -> None:
        """Set a configuration value unless condition is true."""
        if not condition:
            self.set(key, value)
    
    def remember(self, key: str, callback: Callable[[], Any]) -> Any:
        """Remember the result of a callback in configuration."""
        if self.has(key):
            return self.get(key)
        
        value = callback()
        self.set(key, value)
        return value
    
    def reload(self) -> None:
        """Reload all configuration from files."""
        self._config.clear()
        self._cached.clear()
        self._load_config()


# Enhanced configuration repository with caching and observers
class EnhancedConfigRepository(ConfigRepository):
    """Enhanced configuration repository with additional Laravel features."""
    
    def __init__(self) -> None:
        super().__init__()
        self._is_cached = False
        self._cache_path = Path("bootstrap/cache/config.json")
    
    def cache(self) -> None:
        """Cache all configuration to file for faster loading."""
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self._cache_path, 'w') as f:
                json.dump(self._config, f, indent=2, default=str)
            self._is_cached = True
        except Exception as e:
            print(f"Error caching configuration: {e}")
    
    def is_cached(self) -> bool:
        """Check if configuration is cached."""
        return self._cache_path.exists() and self._is_cached
    
    def clear_cache(self) -> None:
        """Clear configuration cache."""
        if self._cache_path.exists():
            self._cache_path.unlink()
        self._is_cached = False
        self._cached.clear()
    
    def load_from_cache(self) -> bool:
        """Load configuration from cache if available."""
        if not self._cache_path.exists():
            return False
        
        try:
            with open(self._cache_path, 'r') as f:
                self._config = json.load(f)
            self._is_cached = True
            return True
        except Exception as e:
            print(f"Error loading cached configuration: {e}")
            return False
    
    def validate(self, schema: Dict[str, Any]) -> List[str]:
        """Validate configuration against a schema."""
        errors = []
        
        def validate_recursive(config: Dict[str, Any], schema_part: Dict[str, Any], path: str = "") -> None:
            for key, expected_type in schema_part.items():
                current_path = f"{path}.{key}" if path else key
                
                if key not in config:
                    errors.append(f"Missing required config key: {current_path}")
                    continue
                
                value = config[key]
                
                if isinstance(expected_type, type):
                    if not isinstance(value, expected_type):
                        errors.append(f"Config key {current_path} should be {expected_type.__name__}, got {type(value).__name__}")
                elif isinstance(expected_type, dict):
                    if isinstance(value, dict):
                        validate_recursive(value, expected_type, current_path)
                    else:
                        errors.append(f"Config key {current_path} should be a dict, got {type(value).__name__}")
        
        validate_recursive(self._config, schema)
        return errors
    
    def dump(self, format: str = 'json') -> str:
        """Dump configuration in specified format."""
        if format.lower() == 'json':
            return json.dumps(self._config, indent=2, default=str)
        elif format.lower() == 'yaml':
            try:
                import yaml  # type: ignore[import-untyped]
                result = yaml.dump(self._config, default_flow_style=False)
                return result if result is not None else ""
            except ImportError:
                return json.dumps(self._config, indent=2, default=str)
        else:
            return str(self._config)


# Global enhanced config instance
config = EnhancedConfigRepository()


# Laravel-style configuration decorators
def config_value(key: str, default: Any = None) -> Callable[..., Any]:
    """Decorator to inject configuration values."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Inject config value as first argument
            value = config.get(key, default)
            return func(value, *args, **kwargs)
        return wrapper
    return decorator


def when_config(key: str, value: Any = True) -> Callable[..., Any]:
    """Decorator to execute function only when config value matches."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if config.get(key) == value:
                return func(*args, **kwargs)
            return None
        return wrapper
    return decorator


def env(key: str, default: Any = None) -> Any:
    """Get environment variable with type conversion."""
    value = os.getenv(key, default)
    if value is None:
        return default
    
    # Convert to appropriate type if it's a string
    if isinstance(value, str):
        return config._convert_env_value(value)
    
    return value