from __future__ import annotations

import os
from typing import Any, Optional, Union
from pathlib import Path


class Environment:
    """Laravel-style environment configuration loader."""
    
    def __init__(self, env_file: Optional[str] = None) -> None:
        self.env_file = env_file or ".env"
        self.loaded = False
        self._load_env_file()
    
    def _load_env_file(self) -> None:
        """Load environment variables from .env file."""
        if self.loaded:
            return
        
        env_path = Path(self.env_file)
        if not env_path.exists():
            # Try to find .env in parent directories
            current = Path.cwd()
            for parent in [current] + list(current.parents):
                env_path = parent / self.env_file
                if env_path.exists():
                    break
            else:
                # No .env file found, that's okay
                self.loaded = True
                return
        
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
            
            self.loaded = True
        except Exception:
            # Fail silently if can't load .env file
            self.loaded = True
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get environment variable with optional default."""
        value = os.getenv(key, default)
        return self._convert_type(value)
    
    def _convert_type(self, value: Any) -> Any:
        """Convert string values to appropriate types."""
        if not isinstance(value, str):
            return value
        
        # Convert boolean strings
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Convert integers
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return int(value)
        
        # Convert floats
        try:
            if '.' in value:
                return float(value)
        except ValueError:
            pass
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set environment variable."""
        os.environ[key] = str(value)
    
    def has(self, key: str) -> bool:
        """Check if environment variable exists."""
        return key in os.environ
    
    def all(self) -> dict[str, str]:
        """Get all environment variables."""
        return dict(os.environ)


# Global environment instance
env = Environment()

# Convenience functions
def env_get(key: str, default: Any = None) -> Any:
    """Get environment variable."""
    return env.get(key, default)

def env_set(key: str, value: Any) -> None:
    """Set environment variable."""
    env.set(key, value)

def env_has(key: str) -> bool:
    """Check if environment variable exists."""
    return env.has(key)