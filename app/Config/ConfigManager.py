from __future__ import annotations

from typing import Any, Dict, Optional, List, Union, Callable, Type, cast
import os
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import importlib.util
import logging

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from .ConfigRepository import ConfigRepository
from app.Support.Arr import Arr


@dataclass
class ConfigSource:
    """Configuration source definition."""
    name: str
    type: str  # file, directory, env, callable
    source: str  # path or callable
    namespace: Optional[str] = None
    priority: int = 100
    enabled: bool = True
    watch: bool = False  # Watch for changes
    cache: bool = True


class ConfigProvider(ABC):
    """Abstract configuration provider."""
    
    def __init__(self, source: ConfigSource):
        self.source = source
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """Load configuration data."""
        # Override this method to implement configuration loading
        # Example:
        # if self.source.type == "file":
        #     return self._load_from_file(self.source.source)
        # elif self.source.type == "env":
        #     return self._load_from_env()
        return {}
    
    @abstractmethod
    def supports(self, source: ConfigSource) -> bool:
        """Check if provider supports the source."""
        # Override this method to check if this provider can handle the source
        # Example:
        # return source.type in ["file", "directory"] and source.source.endswith(".json")
        return False
    
    def can_watch(self) -> bool:
        """Check if provider supports watching for changes."""
        return False


class FileConfigProvider(ConfigProvider):
    """File-based configuration provider."""
    
    def supports(self, source: ConfigSource) -> bool:
        """Check if provider supports file sources."""
        return source.type == "file"
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from file."""
        file_path = Path(self.source.source)
        
        if not file_path.exists():
            self.logger.warning(f"Config file not found: {file_path}")
            return {}
        
        try:
            if file_path.suffix == '.json':
                return self._load_json(file_path)
            elif file_path.suffix in ['.yml', '.yaml']:
                return self._load_yaml(file_path)
            elif file_path.suffix == '.py':
                return self._load_python(file_path)
            else:
                self.logger.warning(f"Unsupported file type: {file_path.suffix}")
                return {}
        except Exception as e:
            self.logger.error(f"Error loading config file {file_path}: {e}")
            return {}
    
    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON configuration file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
            return cast(Dict[str, Any], result)
    
    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if yaml is None:
            self.logger.error("PyYAML not installed, cannot load YAML files")  # type: ignore[unreachable]
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.logger.error(f"Error loading YAML file {file_path}: {e}")
            return {}
    
    def _load_python(self, file_path: Path) -> Dict[str, Any]:
        """Load Python configuration file."""
        spec = importlib.util.spec_from_file_location("config", str(file_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load config from {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Extract public attributes
        config = {}
        for name in dir(module):
            if not name.startswith('_'):
                value = getattr(module, name)
                # Skip imports and callables unless they're simple values
                if not (callable(value) and hasattr(value, '__module__')):
                    config[name] = value
        
        return config
    
    def can_watch(self) -> bool:
        """File provider can watch for changes."""
        return True


class DirectoryConfigProvider(ConfigProvider):
    """Directory-based configuration provider."""
    
    def supports(self, source: ConfigSource) -> bool:
        """Check if provider supports directory sources."""
        return source.type == "directory"
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from directory."""
        directory = Path(self.source.source)
        
        if not directory.exists() or not directory.is_dir():
            self.logger.warning(f"Config directory not found: {directory}")
            return {}
        
        config = {}
        
        # Load all supported files
        for pattern in ['*.py', '*.json', '*.yml', '*.yaml']:
            for file_path in directory.glob(pattern):
                if file_path.name.startswith('_'):
                    continue
                
                file_source = ConfigSource(
                    name=file_path.stem,
                    type="file",
                    source=str(file_path)
                )
                
                file_provider = FileConfigProvider(file_source)
                file_config = file_provider.load()
                
                if file_config:
                    config[file_path.stem] = file_config
        
        return config
    
    def can_watch(self) -> bool:
        """Directory provider can watch for changes."""
        return True


class EnvironmentConfigProvider(ConfigProvider):
    """Environment variables configuration provider."""
    
    def supports(self, source: ConfigSource) -> bool:
        """Check if provider supports environment sources."""
        return source.type == "env"
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        prefix = self.source.source
        config: Dict[str, Any] = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to nested structure
                config_key = key[len(prefix):].lower()
                if config_key.startswith('_'):
                    config_key = config_key[1:]
                
                # Convert underscores to dots for nested keys
                nested_key = config_key.replace('__', '.')
                
                # Cast value to appropriate type
                cast_value = self._cast_value(value)
                
                # Set nested value
                Arr.set(config, nested_key, cast_value)
        
        return config
    
    def _cast_value(self, value: str) -> Any:
        """Cast environment variable value to appropriate type."""
        # Handle boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Handle null/none values
        if value.lower() in ('null', 'none', ''):
            return None
        
        # Handle JSON arrays/objects
        if value.startswith('[') or value.startswith('{'):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # Try to cast to number
        try:
            if '.' not in value:
                return int(value)
            return float(value)
        except ValueError:
            pass
        
        return value


class CallableConfigProvider(ConfigProvider):
    """Callable-based configuration provider."""
    
    def supports(self, source: ConfigSource) -> bool:
        """Check if provider supports callable sources."""
        return source.type == "callable"
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from callable."""
        try:
            # Import and call the function
            module_path, function_name = self.source.source.rsplit('.', 1)
            module = importlib.import_module(module_path)
            func = getattr(module, function_name)
            
            if callable(func):
                result = func()
                return result if isinstance(result, dict) else {}
            
            return {}
        except Exception as e:
            self.logger.error(f"Error loading config from callable {self.source.source}: {e}")
            return {}


class ConfigCache:
    """Configuration cache manager."""
    
    def __init__(self, cache_dir: str = "storage/cache/config"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached configuration."""
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Check if cache is still valid
            if self._is_cache_valid(data):
                result = data.get('config')
                return cast(Dict[str, Any], result) if result is not None else None
            
            # Remove invalid cache
            cache_file.unlink()
            return None
        except Exception as e:
            self.logger.error(f"Error reading cache {key}: {e}")
            return None
    
    def put(self, key: str, config: Dict[str, Any], ttl: int = 3600) -> None:
        """Cache configuration."""
        cache_file = self.cache_dir / f"{key}.json"
        
        cache_data = {
            'config': config,
            'timestamp': time.time(),
            'ttl': ttl
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error writing cache {key}: {e}")
    
    def forget(self, key: str) -> None:
        """Remove cached configuration."""
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            cache_file.unlink()
    
    def flush(self) -> None:
        """Clear all cached configuration."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
    
    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """Check if cache data is still valid."""
        import time
        timestamp = cache_data.get('timestamp', 0)
        ttl = cache_data.get('ttl', 3600)
        result = (time.time() - timestamp) < ttl
        return bool(result)


class ConfigManager:
    """Enhanced Laravel-style configuration manager."""
    
    def __init__(self, repository: Optional[ConfigRepository] = None):
        self.repository = repository or ConfigRepository()
        self.sources: List[ConfigSource] = []
        self.providers: List[ConfigProvider] = []
        self.cache = ConfigCache()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.watchers: Dict[str, Any] = {}
        
        # Register default providers
        self._register_default_providers()
    
    def _register_default_providers(self) -> None:
        """Register default configuration providers."""
        self.providers = [
            FileConfigProvider(ConfigSource("", "file", "")),
            DirectoryConfigProvider(ConfigSource("", "directory", "")),
            EnvironmentConfigProvider(ConfigSource("", "env", "")),
            CallableConfigProvider(ConfigSource("", "callable", ""))
        ]
    
    def add_source(self, source: ConfigSource) -> 'ConfigManager':
        """Add a configuration source."""
        self.sources.append(source)
        
        # Sort by priority
        self.sources.sort(key=lambda s: s.priority)
        
        return self
    
    def file(self, name: str, path: str, namespace: Optional[str] = None, priority: int = 100) -> 'ConfigManager':
        """Add a file configuration source."""
        source = ConfigSource(
            name=name,
            type="file",
            source=path,
            namespace=namespace,
            priority=priority
        )
        return self.add_source(source)
    
    def directory(self, name: str, path: str, priority: int = 100) -> 'ConfigManager':
        """Add a directory configuration source."""
        source = ConfigSource(
            name=name,
            type="directory",
            source=path,
            priority=priority
        )
        return self.add_source(source)
    
    def env(self, name: str, prefix: str, namespace: Optional[str] = None, priority: int = 50) -> 'ConfigManager':
        """Add environment variables configuration source."""
        source = ConfigSource(
            name=name,
            type="env",
            source=prefix,
            namespace=namespace,
            priority=priority
        )
        return self.add_source(source)
    
    def callable_source(self, name: str, callable_path: str, namespace: Optional[str] = None, priority: int = 100) -> 'ConfigManager':
        """Add a callable configuration source."""
        source = ConfigSource(
            name=name,
            type="callable",
            source=callable_path,
            namespace=namespace,
            priority=priority
        )
        return self.add_source(source)
    
    def load(self, force_reload: bool = False) -> None:
        """Load all configuration sources."""
        for source in self.sources:
            if not source.enabled:
                continue
            
            try:
                # Check cache first
                if source.cache and not force_reload:
                    cached_config = self.cache.get(source.name)
                    if cached_config is not None:
                        self._apply_config(cached_config, source)
                        continue
                
                # Load from provider
                provider = self._get_provider(source)
                if provider:
                    config = provider.load()
                    
                    if config:
                        self._apply_config(config, source)
                        
                        # Cache if enabled
                        if source.cache:
                            self.cache.put(source.name, config)
                
                self.logger.debug(f"Loaded config source: {source.name}")
                
            except Exception as e:
                self.logger.error(f"Error loading config source {source.name}: {e}")
    
    def _get_provider(self, source: ConfigSource) -> Optional[ConfigProvider]:
        """Get provider for configuration source."""
        for provider in self.providers:
            if provider.supports(source):
                # Create new instance with the source
                provider_class = provider.__class__
                return provider_class(source)
        
        return None
    
    def _apply_config(self, config: Dict[str, Any], source: ConfigSource) -> None:
        """Apply configuration to repository."""
        if source.namespace:
            self.repository.set(source.namespace, config)
        else:
            self.repository.merge(config)
    
    def reload(self, source_name: Optional[str] = None) -> None:
        """Reload configuration sources."""
        if source_name:
            # Reload specific source
            source = next((s for s in self.sources if s.name == source_name), None)
            if source:
                self.cache.forget(source.name)
                provider = self._get_provider(source)
                if provider:
                    config = provider.load()
                    self._apply_config(config, source)
        else:
            # Reload all sources
            self.cache.flush()
            self.load(force_reload=True)
    
    def watch(self, source_name: str) -> None:
        """Watch a configuration source for changes."""
        source = next((s for s in self.sources if s.name == source_name), None)
        if not source:
            return
        
        provider = self._get_provider(source)
        if not provider or not provider.can_watch():
            self.logger.warning(f"Source {source_name} does not support watching")
            return
        
        # This would integrate with a file watcher like watchdog
        # For now, just log that watching would be enabled
        self.logger.info(f"Watching enabled for config source: {source_name}")
    
    def get_repository(self) -> ConfigRepository:
        """Get the configuration repository."""
        return self.repository
    
    def get_sources(self) -> List[ConfigSource]:
        """Get all configuration sources."""
        return self.sources
    
    def get_source(self, name: str) -> Optional[ConfigSource]:
        """Get a specific configuration source."""
        return next((s for s in self.sources if s.name == name), None)
    
    def disable_source(self, name: str) -> None:
        """Disable a configuration source."""
        source = self.get_source(name)
        if source:
            source.enabled = False
    
    def enable_source(self, name: str) -> None:
        """Enable a configuration source."""
        source = self.get_source(name)
        if source:
            source.enabled = True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get configuration manager statistics."""
        return {
            "sources_count": len(self.sources),
            "enabled_sources": len([s for s in self.sources if s.enabled]),
            "cached_sources": len([s for s in self.sources if s.cache]),
            "providers_count": len(self.providers),
            "config_keys": len(self.repository.all()),
            "sources": [
                {
                    "name": s.name,
                    "type": s.type,
                    "enabled": s.enabled,
                    "priority": s.priority,
                    "cached": s.cache
                }
                for s in self.sources
            ]
        }


def create_default_config_manager() -> ConfigManager:
    """Create a default configuration manager with common sources."""
    manager = ConfigManager()
    
    # Environment variables (highest priority)
    manager.env("app_env", "APP_", priority=10)
    
    # Configuration directory
    manager.directory("config", "config", priority=50)
    
    # Local configuration overrides
    manager.file("local", "config/local.py", priority=90)
    
    # Load all sources
    manager.load()
    
    return manager