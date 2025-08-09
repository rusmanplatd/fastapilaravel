from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import pickle
import threading
import time
import weakref
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
    final,
)
import importlib.util

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    Observer = None  # type: ignore
    FileSystemEventHandler = None  # type: ignore

from .ConfigRepository import ConfigRepository, ConfigObserver
from app.Support.Arr import Arr
from app.Support.Types import validate_types
from app.Utils.Helper import collect, now

ConfigT = TypeVar('ConfigT')


@dataclass
class ConfigSource:
    """Laravel 12 enhanced configuration source definition."""
    name: str
    type: str  # file, directory, env, callable, remote
    source: str  # path or callable
    namespace: Optional[str] = None
    priority: int = 100
    enabled: bool = True
    watch: bool = False  # Watch for changes
    cache: bool = True
    reload_on_change: bool = True
    async_loading: bool = False
    encryption_key: Optional[str] = None
    validation_schema: Optional[Dict[str, Any]] = None
    transformation: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_hash(self) -> str:
        """Get hash of source configuration."""
        content = f"{self.name}:{self.type}:{self.source}:{self.priority}"
        return hashlib.md5(content.encode()).hexdigest()


class ConfigProvider(ABC):
    """Laravel 12 enhanced abstract configuration provider."""
    
    def __init__(self, source: ConfigSource) -> None:
        self.source = source
        self.logger = logging.getLogger(self.__class__.__name__)
        self._last_loaded: Optional[float] = None
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_hash: Optional[str] = None
    
    @abstractmethod
    def load(self) -> Dict[str, Any]:
        """Load configuration data."""
        pass
    
    async def load_async(self) -> Dict[str, Any]:
        """Load configuration data asynchronously."""
        return self.load()
    
    def is_cache_valid(self) -> bool:
        """Check if cached configuration is still valid."""
        if not self._cache or not self._last_loaded:
            return False
        
        # Check if source has changed
        current_hash = self.get_source_hash()
        return current_hash == self._cache_hash
    
    def get_source_hash(self) -> str:
        """Get hash of source content for cache validation."""
        return self.source.get_hash()
    
    def get_cached_config(self) -> Optional[Dict[str, Any]]:
        """Get cached configuration if valid."""
        if self.is_cache_valid():
            return self._cache
        return None
    
    def cache_config(self, config: Dict[str, Any]) -> None:
        """Cache configuration data."""
        self._cache = config
        self._cache_hash = self.get_source_hash()
        self._last_loaded = time.time()
    
    def clear_cache(self) -> None:
        """Clear cached configuration."""
        self._cache = None
        self._cache_hash = None
        self._last_loaded = None
    
    def transform_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply transformation to configuration."""
        if self.source.transformation:
            return self.source.transformation(config)
        return config
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration against schema."""
        if not self.source.validation_schema:
            return True
        
        # Implementation would validate against JSON schema
        return True
    
    def decrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt configuration if encryption key is provided."""
        if not self.source.encryption_key:
            return config
        
        # Implementation would decrypt encrypted values
        return config
    
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


class ConfigFileWatcher:
    """Laravel 12 configuration file watcher."""
    
    def __init__(self, config_manager: 'ConfigManager') -> None:
        self.config_manager = config_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.observer: Optional[Any] = None
        self.watched_paths: Set[str] = set()
        
        if Observer is None:
            self.logger.warning("Watchdog not available, file watching disabled")
    
    def start_watching(self) -> None:
        """Start watching configuration files."""
        if Observer is None:
            return
        
        self.observer = Observer()
        
        for source in self.config_manager.sources:
            if source.watch and source.type in ['file', 'directory']:
                self.add_watch(source)
        
        self.observer.start()
        self.logger.info("Configuration file watcher started")
    
    def stop_watching(self) -> None:
        """Stop watching configuration files."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.logger.info("Configuration file watcher stopped")
    
    def add_watch(self, source: ConfigSource) -> None:
        """Add watch for configuration source."""
        if Observer is None or not self.observer:
            return
        
        path = Path(source.source)
        watch_path = str(path.parent if path.is_file() else path)
        
        if watch_path not in self.watched_paths:
            event_handler = ConfigFileEventHandler(self.config_manager, source)
            self.observer.schedule(event_handler, watch_path, recursive=False)
            self.watched_paths.add(watch_path)


class ConfigFileEventHandler:
    """Configuration file change event handler."""
    
    def __init__(self, config_manager: 'ConfigManager', source: ConfigSource) -> None:
        self.config_manager = config_manager
        self.source = source
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def on_modified(self, event: Any) -> None:
        """Handle file modification event."""
        if event.is_directory:
            return
        
        if event.src_path == self.source.source:
            self.logger.info(f"Configuration file changed: {event.src_path}")
            if self.source.reload_on_change:
                self.config_manager.reload(self.source.name)


class ConfigCache:
    """Laravel 12 enhanced configuration cache manager."""
    
    def __init__(self, cache_dir: str = "storage/cache/config") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._memory_cache: Dict[str, Any] = {}
        self._cache_metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    @validate_types
    def get(self, key: str, use_memory: bool = True) -> Optional[Dict[str, Any]]:
        """Get cached configuration with memory and disk caching."""
        with self._lock:
            # Check memory cache first
            if use_memory and key in self._memory_cache:
                metadata = self._cache_metadata.get(key, {})
                if self._is_memory_cache_valid(metadata):
                    return self._memory_cache[key]
                else:
                    # Remove expired memory cache
                    del self._memory_cache[key]
                    if key in self._cache_metadata:
                        del self._cache_metadata[key]
            
            # Check disk cache
            return self._get_disk_cache(key, use_memory)
    
    def _get_disk_cache(self, key: str, load_to_memory: bool = True) -> Optional[Dict[str, Any]]:
        """Get configuration from disk cache."""
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Check if cache is still valid
            if self._is_cache_valid(data):
                result = data.get('config')
                config = cast(Dict[str, Any], result) if result is not None else None
                
                # Load to memory cache if requested
                if load_to_memory and config is not None:
                    self._memory_cache[key] = config
                    self._cache_metadata[key] = {
                        'timestamp': time.time(),
                        'ttl': data.get('ttl', 3600)
                    }
                
                return config
            
            # Remove invalid cache
            cache_file.unlink()
            return None
        except Exception as e:
            self.logger.error(f"Error reading cache {key}: {e}")
            return None
    
    @validate_types
    def put(self, key: str, config: Dict[str, Any], ttl: int = 3600, use_memory: bool = True) -> None:
        """Cache configuration to memory and/or disk."""
        with self._lock:
            # Store in memory cache
            if use_memory:
                self._memory_cache[key] = config
                self._cache_metadata[key] = {
                    'timestamp': time.time(),
                    'ttl': ttl
                }
            
            # Store in disk cache
            self._put_disk_cache(key, config, ttl)
    
    def _put_disk_cache(self, key: str, config: Dict[str, Any], ttl: int) -> None:
        """Store configuration in disk cache."""
        cache_file = self.cache_dir / f"{key}.json"
        
        cache_data = {
            'config': config,
            'timestamp': time.time(),
            'ttl': ttl,
            'version': '1.0'
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Error writing cache {key}: {e}")
    
    @validate_types
    def forget(self, key: str) -> None:
        """Remove cached configuration from memory and disk."""
        with self._lock:
            # Remove from memory cache
            if key in self._memory_cache:
                del self._memory_cache[key]
            if key in self._cache_metadata:
                del self._cache_metadata[key]
            
            # Remove from disk cache
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                cache_file.unlink()
    
    def flush(self) -> None:
        """Clear all cached configuration from memory and disk."""
        with self._lock:
            # Clear memory cache
            self._memory_cache.clear()
            self._cache_metadata.clear()
            
            # Clear disk cache
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except Exception as e:
                    self.logger.error(f"Error removing cache file {cache_file}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            disk_files = list(self.cache_dir.glob("*.json"))
            return {
                'memory_cache_size': len(self._memory_cache),
                'disk_cache_size': len(disk_files),
                'memory_cache_keys': list(self._memory_cache.keys()),
                'disk_cache_files': [f.stem for f in disk_files]
            }
    
    def _is_memory_cache_valid(self, metadata: Dict[str, Any]) -> bool:
        """Check if memory cache is still valid."""
        timestamp = metadata.get('timestamp', 0)
        ttl = metadata.get('ttl', 3600)
        return (time.time() - timestamp) < ttl
    
    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """Check if cache data is still valid."""
        import time
        timestamp = cache_data.get('timestamp', 0)
        ttl = cache_data.get('ttl', 3600)
        result = (time.time() - timestamp) < ttl
        return bool(result)


class ConfigManager(ConfigObserver):
    """Laravel 12 enhanced configuration manager with advanced features."""
    
    def __init__(self, repository: Optional[ConfigRepository] = None) -> None:
        self.repository = repository or ConfigRepository()
        self.sources: List[ConfigSource] = []
        self.providers: List[ConfigProvider] = []
        self.cache = ConfigCache()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.file_watcher: Optional[ConfigFileWatcher] = None
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix='config')
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._loading_sources: Set[str] = set()
        self._load_lock = threading.RLock()
        self._observers: List[ConfigObserver] = []
        
        # Register default providers
        self._register_default_providers()
        
        # Add self as observer to repository
        self.repository.add_observer(self)
    
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
    
    @validate_types
    def load(self, force_reload: bool = False, async_mode: bool = False) -> None:
        """Load all configuration sources with dependency resolution."""
        with self._load_lock:
            # Build dependency graph
            self._build_dependency_graph()
            
            # Resolve load order based on dependencies
            load_order = self._resolve_load_order()
            
            if async_mode:
                self._load_async(load_order, force_reload)
            else:
                self._load_sync(load_order, force_reload)
    
    def _load_sync(self, load_order: List[str], force_reload: bool) -> None:
        """Load configuration sources synchronously."""
        for source_name in load_order:
            source = self.get_source(source_name)
            if not source or not source.enabled:
                continue
            
            if source_name in self._loading_sources:
                self.logger.warning(f"Circular dependency detected for source: {source_name}")
                continue
            
            self._loading_sources.add(source_name)
            
            try:
                self._load_single_source(source, force_reload)
            except Exception as e:
                self.logger.error(f"Error loading config source {source.name}: {e}")
            finally:
                self._loading_sources.discard(source_name)
    
    def _load_async(self, load_order: List[str], force_reload: bool) -> None:
        """Load configuration sources asynchronously."""
        futures = []
        
        for source_name in load_order:
            source = self.get_source(source_name)
            if not source or not source.enabled or not source.async_loading:
                continue
            
            future = self._executor.submit(self._load_single_source, source, force_reload)
            futures.append(future)
        
        # Wait for all async loads to complete
        for future in futures:
            try:
                future.result(timeout=30)  # 30 second timeout
            except Exception as e:
                self.logger.error(f"Async config load failed: {e}")
    
    def _load_single_source(self, source: ConfigSource, force_reload: bool) -> None:
        """Load a single configuration source."""
        try:
            # Check cache first
            if source.cache and not force_reload:
                cached_config = self.cache.get(source.name)
                if cached_config is not None:
                    self._apply_config(cached_config, source)
                    return
            
            # Load from provider
            provider = self._get_provider(source)
            if provider:
                # Check provider cache
                config = provider.get_cached_config()
                if not config or force_reload:
                    config = provider.load()
                    
                    # Transform and validate
                    if config:
                        config = provider.transform_config(config)
                        config = provider.decrypt_config(config)
                        
                        if provider.validate_config(config):
                            provider.cache_config(config)
                        else:
                            self.logger.error(f"Configuration validation failed for source: {source.name}")
                            return
                
                if config:
                    self._apply_config(config, source)
                    
                    # Cache if enabled
                    if source.cache:
                        self.cache.put(source.name, config)
            
            self.logger.debug(f"Loaded config source: {source.name}")
            
        except Exception as e:
            self.logger.error(f"Error loading config source {source.name}: {e}")
            raise
    
    def _build_dependency_graph(self) -> None:
        """Build dependency graph for configuration sources."""
        self._dependency_graph.clear()
        
        for source in self.sources:
            if source.name not in self._dependency_graph:
                self._dependency_graph[source.name] = set()
            
            for dependency in source.dependencies:
                if dependency not in self._dependency_graph:
                    self._dependency_graph[dependency] = set()
                self._dependency_graph[dependency].add(source.name)
    
    def _resolve_load_order(self) -> List[str]:
        """Resolve load order based on dependencies using topological sort."""
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(source_name: str) -> None:
            if source_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving: {source_name}")
            
            if source_name in visited:
                return
            
            temp_visited.add(source_name)
            
            # Visit dependencies first
            for dependent in self._dependency_graph.get(source_name, set()):
                visit(dependent)
            
            temp_visited.remove(source_name)
            visited.add(source_name)
            result.append(source_name)
        
        # Visit all sources
        for source in self.sources:
            if source.name not in visited:
                visit(source.name)
        
        return result
    
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
    
    def start_watching(self) -> 'ConfigManager':
        """Start watching configuration files for changes."""
        if not self.file_watcher:
            self.file_watcher = ConfigFileWatcher(self)
        
        self.file_watcher.start_watching()
        return self
    
    def stop_watching(self) -> 'ConfigManager':
        """Stop watching configuration files."""
        if self.file_watcher:
            self.file_watcher.stop_watching()
        return self
    
    def add_observer(self, observer: ConfigObserver) -> 'ConfigManager':
        """Add configuration observer."""
        self._observers.append(observer)
        return self
    
    def remove_observer(self, observer: ConfigObserver) -> 'ConfigManager':
        """Remove configuration observer."""
        if observer in self._observers:
            self._observers.remove(observer)
        return self
    
    def on_config_changed(self, key: str, old_value: Any, new_value: Any) -> None:
        """Handle configuration change event."""
        self.logger.debug(f"Configuration changed: {key} = {new_value}")
        
        # Notify other observers
        for observer in self._observers:
            try:
                observer.on_config_changed(key, old_value, new_value)
            except Exception as e:
                self.logger.error(f"Observer error: {e}")
    
    def on_config_set(self, key: str, value: Any) -> None:
        """Handle configuration set event."""
        self.logger.debug(f"Configuration set: {key} = {value}")
        
        for observer in self._observers:
            try:
                observer.on_config_set(key, value)
            except Exception as e:
                self.logger.error(f"Observer error: {e}")
    
    def on_config_removed(self, key: str, old_value: Any) -> None:
        """Handle configuration removal event."""
        self.logger.debug(f"Configuration removed: {key}")
        
        for observer in self._observers:
            try:
                observer.on_config_removed(key, old_value)
            except Exception as e:
                self.logger.error(f"Observer error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive configuration manager statistics."""
        return {
            "sources_count": len(self.sources),
            "enabled_sources": len([s for s in self.sources if s.enabled]),
            "cached_sources": len([s for s in self.sources if s.cache]),
            "watched_sources": len([s for s in self.sources if s.watch]),
            "async_sources": len([s for s in self.sources if s.async_loading]),
            "providers_count": len(self.providers),
            "config_keys": len(self.repository.all()),
            "observers_count": len(self._observers),
            "cache_stats": self.cache.get_stats(),
            "dependency_graph": {k: list(v) for k, v in self._dependency_graph.items()},
            "sources": [
                {
                    "name": s.name,
                    "type": s.type,
                    "enabled": s.enabled,
                    "priority": s.priority,
                    "cached": s.cache,
                    "watched": s.watch,
                    "async": s.async_loading,
                    "dependencies": s.dependencies
                }
                for s in self.sources
            ]
        }
    
    def export_config(self, format_type: str = 'json', include_metadata: bool = False) -> str:
        """Export configuration to string format."""
        config_data = self.repository.all()
        
        if include_metadata:
            config_data = {
                'config': config_data,
                'metadata': {
                    'exported_at': now().isoformat(),
                    'sources': [s.name for s in self.sources if s.enabled],
                    'stats': self.get_stats()
                }
            }
        
        if format_type.lower() == 'json':
            return json.dumps(config_data, indent=2, default=str)
        elif format_type.lower() == 'yaml' and yaml:
            return yaml.dump(config_data, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def import_config(self, config_str: str, format_type: str = 'json', merge: bool = True) -> 'ConfigManager':
        """Import configuration from string format."""
        if format_type.lower() == 'json':
            config_data = json.loads(config_str)
        elif format_type.lower() == 'yaml' and yaml:
            config_data = yaml.safe_load(config_str)
        else:
            raise ValueError(f"Unsupported import format: {format_type}")
        
        # Extract config data if metadata is included
        if 'config' in config_data and 'metadata' in config_data:
            config_data = config_data['config']
        
        if merge:
            self.repository.merge(config_data)
        else:
            for key, value in config_data.items():
                self.repository.set(key, value)
        
        return self
    
    def shutdown(self) -> None:
        """Shutdown configuration manager and cleanup resources."""
        self.stop_watching()
        self._executor.shutdown(wait=True)
        self.logger.info("Configuration manager shutdown complete")


@validate_types
def create_default_config_manager(auto_watch: bool = True, async_loading: bool = False) -> ConfigManager:
    """Create a default Laravel 12 configuration manager with common sources."""
    manager = ConfigManager()
    
    # Environment variables (highest priority)
    env_source = ConfigSource(
        name="app_env",
        type="env",
        source="APP_",
        priority=10,
        watch=False,
        async_loading=async_loading
    )
    manager.add_source(env_source)
    
    # Configuration directory
    config_source = ConfigSource(
        name="config",
        type="directory",
        source="config",
        priority=50,
        watch=auto_watch,
        async_loading=async_loading
    )
    manager.add_source(config_source)
    
    # Local configuration overrides
    local_source = ConfigSource(
        name="local",
        type="file",
        source="config/local.py",
        priority=90,
        watch=auto_watch,
        async_loading=False  # Local config should be sync
    )
    manager.add_source(local_source)
    
    # Load all sources
    manager.load(async_mode=async_loading)
    
    # Start watching if enabled
    if auto_watch:
        manager.start_watching()
    
    return manager


# Export Laravel 12 configuration management functionality
__all__ = [
    'ConfigSource',
    'ConfigProvider',
    'FileConfigProvider',
    'DirectoryConfigProvider',
    'EnvironmentConfigProvider',
    'CallableConfigProvider',
    'ConfigCache',
    'ConfigManager',
    'ConfigFileWatcher',
    'create_default_config_manager',
]