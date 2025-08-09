from __future__ import annotations

from typing import Any, Dict, Optional, List, Union
import os
from pathlib import Path
import json
import importlib.util
from app.Support.Arr import Arr


class ConfigRepository:
    """Laravel-style configuration repository."""
    
    def __init__(self, items: Optional[Dict[str, Any]] = None) -> None:
        self._items: Dict[str, Any] = items or {}
        self._loaded_files: Dict[str, bool] = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation."""
        return Arr.get(self._items, key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation."""
        Arr.set(self._items, key, value)
    
    def has(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return Arr.has(self._items, key)
    
    def forget(self, key: str) -> None:
        """Remove a configuration value."""
        Arr.forget(self._items, key)
    
    def all(self) -> Dict[str, Any]:
        """Get all configuration items."""
        return self._items
    
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