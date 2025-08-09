from __future__ import annotations

from typing import Any, Dict, Optional, Union, List
import os
from pathlib import Path


class ConfigRepository:
    """Laravel-style configuration repository."""
    
    def __init__(self) -> None:
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from files."""
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
                    
                    self._config[module_name] = config_data
            except Exception as e:
                print(f"Error loading config {module_name}: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation."""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value[k]
                else:
                    return default
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation."""
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the final value
        config[keys[-1]] = value
    
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


# Global config instance
config = ConfigRepository()


def env(key: str, default: Any = None) -> Any:
    """Get environment variable."""
    return os.getenv(key, default)