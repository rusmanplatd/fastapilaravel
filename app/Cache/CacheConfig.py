from __future__ import annotations

from typing import Any, Dict, Optional, List, Type
from dataclasses import dataclass, field
from enum import Enum

from .CacheStore import CacheStore, ArrayCacheStore, RedisCacheStore, FileCacheStore


class CacheDriver(Enum):
    """Supported cache drivers."""
    ARRAY = "array"
    FILE = "file"
    REDIS = "redis"
    DATABASE = "database"
    MEMCACHED = "memcached"


@dataclass
class CacheStoreConfig:
    """Configuration for a cache store."""
    driver: CacheDriver
    host: Optional[str] = None
    port: Optional[int] = None
    password: Optional[str] = None
    database: Optional[int] = None
    prefix: str = ""
    path: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheConfig:
    """Main cache configuration."""
    default: str = "array"
    prefix: str = "laravel_cache"
    stores: Dict[str, CacheStoreConfig] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Initialize default stores if not provided."""
        if not self.stores:
            self.stores = {
                "array": CacheStoreConfig(
                    driver=CacheDriver.ARRAY
                ),
                "file": CacheStoreConfig(
                    driver=CacheDriver.FILE,
                    path="storage/cache"
                ),
                "redis": CacheStoreConfig(
                    driver=CacheDriver.REDIS,
                    host="localhost",
                    port=6379,
                    database=0
                )
            }


class CacheDriverFactory:
    """Factory for creating cache store instances."""
    
    _drivers: Dict[CacheDriver, Type[CacheStore]] = {
        CacheDriver.ARRAY: ArrayCacheStore,
        CacheDriver.FILE: FileCacheStore,
        CacheDriver.REDIS: RedisCacheStore,
    }
    
    @classmethod
    def register_driver(cls, driver: CacheDriver, store_class: Type[CacheStore]) -> None:
        """Register a custom cache driver."""
        cls._drivers[driver] = store_class
    
    @classmethod
    def create(cls, config: CacheStoreConfig) -> CacheStore:
        """Create a cache store instance from configuration."""
        if config.driver not in cls._drivers:
            raise ValueError(f"Unsupported cache driver: {config.driver}")
        
        store_class = cls._drivers[config.driver]
        
        # Create instance based on driver type
        if config.driver == CacheDriver.ARRAY:
            return store_class()
        
        elif config.driver == CacheDriver.FILE:
            return FileCacheStore(
                cache_path=config.path or "storage/cache"
            )
        
        elif config.driver == CacheDriver.REDIS:
            connection_params = {
                'host': config.host or 'localhost',
                'port': config.port or 6379,
                'db': config.database or 0
            }
            if config.password:
                connection_params['password'] = config.password
            
            return RedisCacheStore(connection_params)
        
        else:
            # Fallback for custom drivers
            return store_class()


# Default cache configurations
DEFAULT_CONFIG = CacheConfig(
    default="array",
    prefix="fastapi_laravel",
    stores={
        "array": CacheStoreConfig(CacheDriver.ARRAY),
        "file": CacheStoreConfig(
            driver=CacheDriver.FILE,
            path="storage/cache"
        ),
        "redis": CacheStoreConfig(
            driver=CacheDriver.REDIS,
            host="localhost",
            port=6379,
            database=0
        )
    }
)

# Environment-specific configurations
DEVELOPMENT_CONFIG = CacheConfig(
    default="array",
    prefix="dev_cache",
    stores={
        "array": CacheStoreConfig(CacheDriver.ARRAY),
        "file": CacheStoreConfig(
            driver=CacheDriver.FILE,
            path="storage/cache/dev"
        )
    }
)

PRODUCTION_CONFIG = CacheConfig(
    default="redis",
    prefix="prod_cache", 
    stores={
        "redis": CacheStoreConfig(
            driver=CacheDriver.REDIS,
            host="redis",
            port=6379,
            database=0
        ),
        "redis_sessions": CacheStoreConfig(
            driver=CacheDriver.REDIS,
            host="redis",
            port=6379,
            database=1
        ),
        "file": CacheStoreConfig(
            driver=CacheDriver.FILE,
            path="/var/cache/app"
        )
    }
)

TESTING_CONFIG = CacheConfig(
    default="array",
    prefix="test_cache",
    stores={
        "array": CacheStoreConfig(CacheDriver.ARRAY)
    }
)


# Cache configuration presets
CACHE_CONFIGS = {
    "default": DEFAULT_CONFIG,
    "development": DEVELOPMENT_CONFIG,
    "production": PRODUCTION_CONFIG,
    "testing": TESTING_CONFIG
}


def get_cache_config(environment: str = "default") -> CacheConfig:
    """Get cache configuration for environment."""
    return CACHE_CONFIGS.get(environment, DEFAULT_CONFIG)


def configure_cache_manager(config: CacheConfig) -> None:
    """Configure the global cache manager with the given configuration."""
    from .CacheStore import cache_manager
    
    # Clear existing stores
    cache_manager.stores.clear()
    
    # Set default store
    cache_manager.default_store = config.default
    
    # Create and register stores
    for name, store_config in config.stores.items():
        store = CacheDriverFactory.create(store_config)
        cache_manager.stores[name] = store


# Tagged cache configurations
class TaggedCacheConfig:
    """Configuration for tagged cache operations."""
    
    def __init__(self, namespace: str = "tags", separator: str = ":"):
        self.namespace = namespace
        self.separator = separator
    
    def generate_tag_key(self, tag: str) -> str:
        """Generate a key for a cache tag."""
        return f"{self.namespace}{self.separator}{tag}"
    
    def generate_tagged_key(self, key: str, tags: List[str]) -> str:
        """Generate a cache key with tags."""
        if not tags:
            return key
        
        tag_string = self.separator.join(sorted(tags))
        return f"{self.namespace}{self.separator}{tag_string}{self.separator}{key}"


# Global tagged cache configuration
tagged_cache_config = TaggedCacheConfig()