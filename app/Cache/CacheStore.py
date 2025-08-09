from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable
from abc import ABC, abstractmethod
import time
import json
import pickle
import hashlib
from datetime import datetime, timedelta


class CacheStore(ABC):
    """Abstract cache store following Laravel's cache interface."""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve an item from the cache."""
        pass
    
    @abstractmethod
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store an item in the cache."""
        pass
    
    @abstractmethod
    def forget(self, key: str) -> bool:
        """Remove an item from the cache."""
        pass
    
    @abstractmethod
    def flush(self) -> bool:
        """Remove all items from the cache."""
        pass
    
    @abstractmethod
    def increment(self, key: str, value: int = 1) -> int:
        """Increment the value of an item in the cache."""
        pass
    
    @abstractmethod
    def decrement(self, key: str, value: int = 1) -> int:
        """Decrement the value of an item in the cache."""
        pass
    
    def many(self, keys: List[str]) -> Dict[str, Any]:
        """Retrieve multiple items from the cache."""
        return {key: self.get(key) for key in keys}
    
    def put_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Store multiple items in the cache."""
        for key, value in items.items():
            self.put(key, value, ttl)
        return True
    
    def add(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store an item in the cache if it doesn't exist."""
        if self.get(key) is None:
            return self.put(key, value, ttl)
        return False
    
    def forever(self, key: str, value: Any) -> bool:
        """Store an item in the cache indefinitely."""
        return self.put(key, value, None)
    
    def remember(self, key: str, ttl: Optional[int], callback: Callable[[], Any]) -> Any:
        """Get an item from cache or store the result of callback."""
        value = self.get(key)
        if value is None:
            value = callback()
            self.put(key, value, ttl)
        return value
    
    def remember_forever(self, key: str, callback: Callable[[], Any]) -> Any:
        """Get an item from cache or store callback result forever."""
        return self.remember(key, None, callback)
    
    def pull(self, key: str, default: Any = None) -> Any:
        """Retrieve and delete an item from the cache."""
        value = self.get(key, default)
        self.forget(key)
        return value


class ArrayCacheStore(CacheStore):
    """In-memory array cache store."""
    
    def __init__(self) -> None:
        self.storage: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve an item from the cache."""
        if key in self.storage:
            item = self.storage[key]
            if item['expires_at'] is None or item['expires_at'] > time.time():
                return item['value']
            else:
                # Item has expired
                del self.storage[key]
        return default
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store an item in the cache."""
        expires_at = None if ttl is None else time.time() + ttl
        self.storage[key] = {
            'value': value,
            'expires_at': expires_at
        }
        return True
    
    def forget(self, key: str) -> bool:
        """Remove an item from the cache."""
        if key in self.storage:
            del self.storage[key]
            return True
        return False
    
    def flush(self) -> bool:
        """Remove all items from the cache."""
        self.storage.clear()
        return True
    
    def increment(self, key: str, value: int = 1) -> int:
        """Increment the value of an item in the cache."""
        current = self.get(key, 0)
        if not isinstance(current, (int, float)):
            current = 0
        new_value = current + value
        self.put(key, new_value)
        return int(new_value)
    
    def decrement(self, key: str, value: int = 1) -> int:
        """Decrement the value of an item in the cache."""
        return self.increment(key, -value)


class RedisCacheStore(CacheStore):
    """Redis cache store (placeholder - would need redis-py)."""
    
    def __init__(self, connection_params: Optional[Dict[str, Any]] = None) -> None:
        self.connection_params = connection_params or {}
        # In a real implementation, you'd initialize Redis connection here
        self._fallback = ArrayCacheStore()  # Fallback for demo
    
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve an item from Redis cache."""
        # Fallback to array cache for demo
        return self._fallback.get(key, default)
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store an item in Redis cache."""
        # Fallback to array cache for demo
        return self._fallback.put(key, value, ttl)
    
    def forget(self, key: str) -> bool:
        """Remove an item from Redis cache."""
        return self._fallback.forget(key)
    
    def flush(self) -> bool:
        """Remove all items from Redis cache."""
        return self._fallback.flush()
    
    def increment(self, key: str, value: int = 1) -> int:
        """Increment value in Redis."""
        return self._fallback.increment(key, value)
    
    def decrement(self, key: str, value: int = 1) -> int:
        """Decrement value in Redis."""
        return self._fallback.decrement(key, value)


class FileCacheStore(CacheStore):
    """File-based cache store."""
    
    def __init__(self, cache_path: str = "storage/cache") -> None:
        self.cache_path = cache_path
        import os
        os.makedirs(cache_path, exist_ok=True)
    
    def _get_file_path(self, key: str) -> str:
        """Get file path for cache key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return f"{self.cache_path}/{key_hash}.cache"
    
    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve an item from file cache."""
        file_path = self._get_file_path(key)
        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
                if data['expires_at'] is None or data['expires_at'] > time.time():
                    return data['value']
                else:
                    # Item has expired
                    import os
                    os.remove(file_path)
        except (FileNotFoundError, pickle.PickleError):
            pass
        return default
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store an item in file cache."""
        file_path = self._get_file_path(key)
        expires_at = None if ttl is None else time.time() + ttl
        
        data = {
            'value': value,
            'expires_at': expires_at
        }
        
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception:
            return False
    
    def forget(self, key: str) -> bool:
        """Remove an item from file cache."""
        file_path = self._get_file_path(key)
        try:
            import os
            os.remove(file_path)
            return True
        except FileNotFoundError:
            return False
    
    def flush(self) -> bool:
        """Remove all items from file cache."""
        try:
            import os
            import glob
            for file_path in glob.glob(f"{self.cache_path}/*.cache"):
                os.remove(file_path)
            return True
        except Exception:
            return False
    
    def increment(self, key: str, value: int = 1) -> int:
        """Increment the value of an item in file cache."""
        current = self.get(key, 0)
        if not isinstance(current, (int, float)):
            current = 0
        new_value = current + value
        self.put(key, new_value)
        return int(new_value)
    
    def decrement(self, key: str, value: int = 1) -> int:
        """Decrement the value of an item in file cache."""
        return self.increment(key, -value)


class CacheManager:
    """Laravel-style cache manager."""
    
    def __init__(self) -> None:
        self.stores: Dict[str, CacheStore] = {}
        self.default_store = "array"
        
        # Register default stores
        self.stores["array"] = ArrayCacheStore()
        self.stores["file"] = FileCacheStore()
        self.stores["redis"] = RedisCacheStore()
    
    def store(self, name: Optional[str] = None) -> CacheStore:
        """Get a cache store instance."""
        store_name = name or self.default_store
        if store_name not in self.stores:
            raise ValueError(f"Cache store '{store_name}' not found")
        return self.stores[store_name]
    
    def extend(self, driver: str, resolver: Callable[[], CacheStore]) -> None:
        """Register a custom cache driver."""
        self.stores[driver] = resolver()
    
    # Proxy methods to default store
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get item from default cache store."""
        return self.store().get(key, default)
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Put item in default cache store."""
        return self.store().put(key, value, ttl)
    
    def forget(self, key: str) -> bool:
        """Remove item from default cache store."""
        return self.store().forget(key)
    
    def flush(self) -> bool:
        """Clear default cache store."""
        return self.store().flush()
    
    def remember(self, key: str, ttl: Optional[int], callback: Callable[[], Any]) -> Any:
        """Remember item in default cache store."""
        return self.store().remember(key, ttl, callback)
    
    def tags(self, *tags: str) -> TaggedCache:
        """Create a tagged cache instance."""
        return TaggedCache(self.store(), list(tags))


class TaggedCache:
    """Tagged cache implementation."""
    
    def __init__(self, store: CacheStore, tags: List[str]) -> None:
        self.store = store
        self.tags = tags
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get tagged cache item."""
        tagged_key = self._tagged_key(key)
        return self.store.get(tagged_key, default)
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Put tagged cache item."""
        tagged_key = self._tagged_key(key)
        return self.store.put(tagged_key, value, ttl)
    
    def forget(self, key: str) -> bool:
        """Remove tagged cache item."""
        tagged_key = self._tagged_key(key)
        return self.store.forget(tagged_key)
    
    def flush(self) -> bool:
        """Flush all items with these tags."""
        # This is simplified - Laravel has a more complex tag invalidation system
        return True
    
    def _tagged_key(self, key: str) -> str:
        """Generate tagged cache key."""
        tag_string = ":".join(sorted(self.tags))
        return f"tags:{tag_string}:{key}"


# Global cache manager
cache_manager = CacheManager()