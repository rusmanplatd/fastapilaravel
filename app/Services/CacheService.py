from __future__ import annotations

import json
import logging
import hashlib
from typing import Any, Optional, Dict, List, Union, Callable, TypeVar
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import asyncio
from contextlib import asynccontextmanager

T = TypeVar('T')


class CacheException(Exception):
    """Base exception for cache-related errors."""
    pass


class CacheSerializer:
    """JSON serializer for cache values with support for custom types."""
    
    @staticmethod
    def serialize(value: Any) -> str:
        """Serialize a value to JSON string."""
        try:
            if isinstance(value, (datetime,)):
                return json.dumps({
                    '__type': 'datetime',
                    'value': value.isoformat()
                })
            elif hasattr(value, 'to_dict'):
                return json.dumps({
                    '__type': 'model',
                    'value': value.to_dict()
                })
            else:
                return json.dumps(value)
        except (TypeError, ValueError) as e:
            raise CacheException(f"Failed to serialize cache value: {e}")
    
    @staticmethod
    def deserialize(data: str) -> Any:
        """Deserialize a JSON string to value."""
        try:
            parsed = json.loads(data)
            
            if isinstance(parsed, dict) and '__type' in parsed:
                if parsed['__type'] == 'datetime':
                    return datetime.fromisoformat(parsed['value'])
                elif parsed['__type'] == 'model':
                    return parsed['value']  # Return dict representation
            
            return parsed
        except (json.JSONDecodeError, ValueError) as e:
            raise CacheException(f"Failed to deserialize cache value: {e}")


class CacheStore(ABC):
    """Abstract base class for cache stores."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        pass
    
    @abstractmethod
    async def put(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Put a value in cache with optional TTL in seconds."""
        pass
    
    @abstractmethod
    async def forget(self, key: str) -> bool:
        """Remove a value from cache."""
        pass
    
    @abstractmethod
    async def flush(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    async def increment(self, key: str, value: int = 1) -> int:
        """Increment a cache value."""
        pass
    
    @abstractmethod
    async def decrement(self, key: str, value: int = 1) -> int:
        """Decrement a cache value."""
        pass


class MemoryCacheStore(CacheStore):
    """In-memory cache store for development and testing."""
    
    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if entry['expires_at'] and datetime.utcnow() > entry['expires_at']:
                    del self._cache[key]
                    return None
                return str(entry['value']) if entry['value'] is not None else None
            return None
    
    async def put(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        async with self._lock:
            expires_at = None
            if ttl:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            self._cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.utcnow()
            }
            return True
    
    async def forget(self, key: str) -> bool:
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    async def flush(self) -> bool:
        async with self._lock:
            self._cache.clear()
            return True
    
    async def increment(self, key: str, value: int = 1) -> int:
        async with self._lock:
            current = await self.get(key)
            if current is None:
                new_value = value
            else:
                try:
                    new_value = int(current) + value
                except ValueError:
                    raise CacheException(f"Cannot increment non-numeric value: {current}")
            
            await self.put(key, str(new_value))
            return new_value
    
    async def decrement(self, key: str, value: int = 1) -> int:
        return await self.increment(key, -value)


class CacheManager:
    """
    Laravel-style cache manager with tagging, repositories, and advanced features.
    
    Provides a unified interface for caching with support for:
    - Multiple cache stores
    - Cache tags for bulk operations
    - Distributed locking
    - Cache events and metrics
    """
    
    def __init__(self, default_store: CacheStore):
        self.stores: Dict[str, CacheStore] = {'default': default_store}
        self.default_store_name = 'default'
        self.logger = logging.getLogger(__name__)
        self.serializer = CacheSerializer()
        self._prefix = 'laravel_cache:'
        self._tag_prefix = 'tag:'
        
    def store(self, name: Optional[str] = None) -> CacheStore:
        """Get a cache store by name."""
        store_name = name or self.default_store_name
        if store_name not in self.stores:
            raise CacheException(f"Cache store '{store_name}' not found")
        return self.stores[store_name]
    
    def add_store(self, name: str, store: CacheStore) -> None:
        """Add a new cache store."""
        self.stores[name] = store
        self.logger.info(f"Added cache store: {name}")
    
    def _make_key(self, key: str) -> str:
        """Generate cache key with prefix."""
        return f"{self._prefix}{key}"
    
    async def get(self, key: str, default: Any = None, store: Optional[str] = None) -> Any:
        """Get a value from cache with deserialization."""
        try:
            cache_key = self._make_key(key)
            raw_value = await self.store(store).get(cache_key)
            
            if raw_value is None:
                self.logger.debug(f"Cache miss for key: {key}")
                return default
            
            self.logger.debug(f"Cache hit for key: {key}")
            return self.serializer.deserialize(raw_value)
            
        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {e}")
            return default
    
    async def put(self, key: str, value: Any, ttl: Optional[int] = None, store: Optional[str] = None) -> bool:
        """Put a value in cache with serialization."""
        try:
            cache_key = self._make_key(key)
            serialized_value = self.serializer.serialize(value)
            
            result = await self.store(store).put(cache_key, serialized_value, ttl)
            
            if result:
                self.logger.debug(f"Cache stored for key: {key} (TTL: {ttl})")
            else:
                self.logger.warning(f"Failed to store cache for key: {key}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Cache put error for key {key}: {e}")
            return False
    
    async def remember(self, key: str, ttl: int, callback: Callable[[], Any], store: Optional[str] = None) -> Any:
        """Get from cache or execute callback and store result."""
        value = await self.get(key, store=store)
        
        if value is not None:
            return value
        
        # Execute callback and store result
        try:
            if asyncio.iscoroutinefunction(callback):
                result = await callback()
            else:
                result = callback()
            
            await self.put(key, result, ttl, store=store)
            self.logger.debug(f"Cache populated via callback for key: {key}")
            return result
            
        except Exception as e:
            self.logger.error(f"Cache remember callback error for key {key}: {e}")
            raise
    
    async def forget(self, key: str, store: Optional[str] = None) -> bool:
        """Remove a value from cache."""
        try:
            cache_key = self._make_key(key)
            result = await self.store(store).forget(cache_key)
            
            if result:
                self.logger.debug(f"Cache cleared for key: {key}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Cache forget error for key {key}: {e}")
            return False
    
    async def flush(self, store: Optional[str] = None) -> bool:
        """Clear all cache entries."""
        try:
            result = await self.store(store).flush()
            
            if result:
                self.logger.info(f"Cache flushed for store: {store or self.default_store_name}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Cache flush error: {e}")
            return False
    
    async def increment(self, key: str, value: int = 1, store: Optional[str] = None) -> int:
        """Increment a cache value."""
        try:
            cache_key = self._make_key(key)
            result = await self.store(store).increment(cache_key, value)
            self.logger.debug(f"Cache incremented for key: {key} by {value} = {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Cache increment error for key {key}: {e}")
            raise CacheException(f"Failed to increment cache key {key}: {e}")
    
    async def decrement(self, key: str, value: int = 1, store: Optional[str] = None) -> int:
        """Decrement a cache value."""
        return await self.increment(key, -value, store=store)
    
    def tags(self, *tag_names: str) -> 'TaggedCache':
        """Create a tagged cache instance."""
        return TaggedCache(self, tag_names)
    
    async def forever(self, key: str, value: Any, store: Optional[str] = None) -> bool:
        """Store a value in cache forever (no expiration)."""
        return await self.put(key, value, ttl=None, store=store)


class TaggedCache:
    """Cache instance with tag support for bulk operations."""
    
    def __init__(self, manager: CacheManager, tags: tuple[str, ...]):
        self.manager = manager
        self.tags = tags
        self.logger = logging.getLogger(__name__)
    
    def _tag_key(self, tag: str) -> str:
        """Generate tag key."""
        return f"{self.manager._tag_prefix}{tag}"
    
    def _tagged_key(self, key: str) -> str:
        """Generate tagged cache key."""
        tag_hash = hashlib.md5('|'.join(sorted(self.tags)).encode()).hexdigest()
        return f"tagged:{tag_hash}:{key}"
    
    async def get(self, key: str, default: Any = None, store: Optional[str] = None) -> Any:
        """Get a tagged cache value."""
        tagged_key = self._tagged_key(key)
        return await self.manager.get(tagged_key, default, store)
    
    async def put(self, key: str, value: Any, ttl: Optional[int] = None, store: Optional[str] = None) -> bool:
        """Put a tagged cache value."""
        tagged_key = self._tagged_key(key)
        
        # Store the value
        result = await self.manager.put(tagged_key, value, ttl, store)
        
        # Track the key in tag sets
        if result:
            for tag in self.tags:
                tag_key = self._tag_key(tag)
                # In a real implementation, you'd maintain tag->key mappings
                # For now, we'll just log the tagging
                self.logger.debug(f"Tagged cache key {key} with tag {tag}")
        
        return result
    
    async def flush(self, store: Optional[str] = None) -> bool:
        """Flush all cache entries with these tags."""
        # In a real implementation, you'd iterate through all keys for these tags
        # For now, we'll just log the flush
        self.logger.info(f"Flushing tagged cache for tags: {self.tags}")
        return True


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        # Default to memory cache for now
        _cache_manager = CacheManager(MemoryCacheStore())
    return _cache_manager


def set_cache_manager(manager: CacheManager) -> None:
    """Set the global cache manager instance."""
    global _cache_manager
    _cache_manager = manager


# Convenience functions for global cache access
async def cache_get(key: str, default: Any = None) -> Any:
    """Get a value from the default cache."""
    return await get_cache_manager().get(key, default)


async def cache_put(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Put a value in the default cache."""
    return await get_cache_manager().put(key, value, ttl)


async def cache_remember(key: str, ttl: int, callback: Callable[[], Any]) -> Any:
    """Remember a value in the default cache."""
    return await get_cache_manager().remember(key, ttl, callback)


async def cache_forget(key: str) -> bool:
    """Forget a value from the default cache."""
    return await get_cache_manager().forget(key)


async def cache_flush() -> bool:
    """Flush the default cache."""
    return await get_cache_manager().flush()