from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Callable, TypeVar, Generic
from abc import ABC, abstractmethod
import time
import json
import pickle
import hashlib
import threading
from datetime import datetime, timedelta
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')


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
    
    def has(self, key: str) -> bool:
        """Determine if an item exists in the cache."""
        return self.get(key) is not None
    
    def missing(self, key: str) -> bool:
        """Determine if an item is missing from the cache."""
        return not self.has(key)
    
    def get_or_put(self, key: str, value: Any, ttl: Optional[int] = None) -> Any:
        """Get an item from cache or store the given value."""
        cached = self.get(key)
        if cached is not None:
            return cached
        
        if callable(value):
            value = value()
        
        self.put(key, value, ttl)
        return value
    
    def lock(self, key: str, timeout: Optional[int] = None) -> 'CacheLock':
        """Get a lock instance for the given key."""
        return CacheLock(self, key, timeout)
    
    def atomic(self) -> 'AtomicCacheTransaction':
        """Begin an atomic cache transaction."""
        return AtomicCacheTransaction(self)
    
    @contextmanager
    def disable_cache(self) -> Any:
        """Temporarily disable cache operations."""
        original_get = self.get
        original_put = self.put
        original_forget = self.forget
        
        self.get = lambda key, default=None: default  # type: ignore
        self.put = lambda key, value, ttl=None: True  # type: ignore
        self.forget = lambda key: True  # type: ignore
        
        try:
            yield
        finally:
            self.get = original_get  # type: ignore
            self.put = original_put  # type: ignore
            self.forget = original_forget  # type: ignore


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
    """Laravel-style cache manager with enhanced features."""
    
    def __init__(self) -> None:
        self.stores: Dict[str, CacheStore] = {}
        self.default_store = "array"
        self.event_listener = CacheEventListener()
        self.serializer = JsonCacheSerializer()
        
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
        """Get item from default cache store with event firing."""
        result = self.store().get(key, default)
        self.event_listener.fire(CacheEvent(CacheOperation.GET, key, result))
        return result
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Put item in default cache store with event firing."""
        result = self.store().put(key, value, ttl)
        self.event_listener.fire(CacheEvent(CacheOperation.PUT, key, value, ttl))
        return result
    
    def forget(self, key: str) -> bool:
        """Remove item from default cache store with event firing."""
        result = self.store().forget(key)
        self.event_listener.fire(CacheEvent(CacheOperation.FORGET, key))
        return result
    
    def flush(self) -> bool:
        """Clear default cache store."""
        return self.store().flush()
    
    def remember(self, key: str, ttl: Optional[int], callback: Callable[[], Any]) -> Any:
        """Remember item in default cache store."""
        return self.store().remember(key, ttl, callback)
    
    def tags(self, *tags: str) -> TaggedCache:
        """Create a tagged cache instance."""
        return TaggedCache(self.store(), list(tags))
    
    def repository(self, prefix: str = "", store_name: Optional[str] = None) -> RepositoryCache:
        """Create a repository cache instance."""
        store = self.store(store_name)
        return RepositoryCache(store, prefix, self.serializer)
    
    def lock(self, key: str, timeout: Optional[int] = None, store_name: Optional[str] = None) -> CacheLock:
        """Create a cache lock."""
        store = self.store(store_name)
        return CacheLock(store, key, timeout)
    
    def atomic(self, store_name: Optional[str] = None) -> AtomicCacheTransaction:
        """Create an atomic transaction."""
        store = self.store(store_name)
        return AtomicCacheTransaction(store)
    
    def flexible(self, key: str, callback: Callable[[], T], ttl: Optional[int] = None, 
                lock_timeout: Optional[int] = None) -> T:
        """Flexible cache with automatic locking for expensive operations."""
        # Try to get from cache first
        value = self.get(key)
        if value is not None:
            return value  # type: ignore
        
        # Use lock to prevent cache stampede
        lock_key = f"lock:{key}"
        with self.lock(lock_key, lock_timeout):
            # Double-check after acquiring lock
            value = self.get(key)
            if value is not None:
                return value  # type: ignore
            
            # Generate and cache the value
            fresh_value = callback()
            self.put(key, fresh_value, ttl)
            return fresh_value
    
    def listen(self, operation: CacheOperation, callback: Callable[[CacheEvent], None]) -> None:
        """Listen to cache events."""
        self.event_listener.listen(operation, callback)


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


class CacheOperation(Enum):
    """Cache operation types for events."""
    GET = "get"
    PUT = "put"
    FORGET = "forget"
    FLUSH = "flush"
    INCREMENT = "increment"
    DECREMENT = "decrement"


@dataclass
class CacheEvent:
    """Cache event data."""
    operation: CacheOperation
    key: Optional[str]
    value: Any = None
    ttl: Optional[int] = None
    store_name: str = "default"
    timestamp: Optional[float] = None
    
    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = time.time()


class CacheSerializer(ABC):
    """Abstract cache serializer."""
    
    @abstractmethod
    def serialize(self, value: Any) -> str:
        """Serialize a value for storage."""
        pass
    
    @abstractmethod
    def unserialize(self, data: str) -> Any:
        """Unserialize data from storage."""
        pass


class JsonCacheSerializer(CacheSerializer):
    """JSON cache serializer."""
    
    def serialize(self, value: Any) -> str:
        """Serialize value to JSON."""
        return json.dumps(value, default=str)
    
    def unserialize(self, data: str) -> Any:
        """Unserialize JSON data."""
        return json.loads(data)


class PickleCacheSerializer(CacheSerializer):
    """Pickle cache serializer."""
    
    def serialize(self, value: Any) -> str:
        """Serialize value using pickle."""
        return pickle.dumps(value).hex()
    
    def unserialize(self, data: str) -> Any:
        """Unserialize pickle data."""
        return pickle.loads(bytes.fromhex(data))


class CacheLock:
    """Cache-based lock implementation."""
    
    def __init__(self, store: CacheStore, key: str, timeout: Optional[int] = None) -> None:
        self.store = store
        self.key = f"lock:{key}"
        self.timeout = timeout or 60
        self.acquired = False
        self.owner = id(self)
    
    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """Acquire the lock."""
        if self.acquired:
            return True
        
        end_time = time.time() + (timeout or 0) if timeout else float('inf')
        
        while time.time() <= end_time:
            if self.store.add(self.key, self.owner, self.timeout):
                self.acquired = True
                return True
            
            if not blocking:
                return False
            
            time.sleep(0.1)
        
        return False
    
    def release(self) -> bool:
        """Release the lock."""
        if not self.acquired:
            return False
        
        # Only release if we own the lock
        current_owner = self.store.get(self.key)
        if current_owner == self.owner:
            self.store.forget(self.key)
            self.acquired = False
            return True
        
        return False
    
    def __enter__(self) -> 'CacheLock':
        """Context manager entry."""
        if not self.acquire():
            raise TimeoutError(f"Could not acquire lock: {self.key}")
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.release()
    
    def is_owned_by_current_process(self) -> bool:
        """Check if lock is owned by current process."""
        return bool(self.store.get(self.key) == self.owner)


class AtomicCacheTransaction:
    """Atomic cache transaction for batch operations."""
    
    def __init__(self, store: CacheStore) -> None:
        self.store = store
        self.operations: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self.committed = False
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> 'AtomicCacheTransaction':
        """Add a put operation to the transaction."""
        with self._lock:
            self.operations.append({
                'operation': 'put',
                'key': key,
                'value': value,
                'ttl': ttl
            })
        return self
    
    def forget(self, key: str) -> 'AtomicCacheTransaction':
        """Add a forget operation to the transaction."""
        with self._lock:
            self.operations.append({
                'operation': 'forget',
                'key': key
            })
        return self
    
    def commit(self) -> bool:
        """Execute all operations atomically."""
        if self.committed:
            return False
        
        with self._lock:
            try:
                # Execute all operations
                for op in self.operations:
                    if op['operation'] == 'put':
                        self.store.put(op['key'], op['value'], op.get('ttl'))
                    elif op['operation'] == 'forget':
                        self.store.forget(op['key'])
                self.committed = True
                return True
            except Exception:
                # In a real implementation, you'd rollback operations
                return False
    
    def rollback(self) -> None:
        """Rollback the transaction."""
        with self._lock:
            self.operations.clear()
    
    def __enter__(self) -> 'AtomicCacheTransaction':
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        if exc_type is None:
            self.commit()
        else:
            self.rollback()


class CacheEventListener:
    """Cache event listener for monitoring."""
    
    def __init__(self) -> None:
        self.listeners: Dict[CacheOperation, List[Callable[[CacheEvent], None]]] = {
            op: [] for op in CacheOperation
        }
    
    def listen(self, operation: CacheOperation, callback: Callable[[CacheEvent], None]) -> None:
        """Add event listener."""
        self.listeners[operation].append(callback)
    
    def fire(self, event: CacheEvent) -> None:
        """Fire cache event to all listeners."""
        for callback in self.listeners.get(event.operation, []):
            try:
                callback(event)
            except Exception:
                pass  # Don't let listener errors affect cache operations


class RepositoryCache:
    """Repository-pattern cache wrapper."""
    
    def __init__(self, store: CacheStore, prefix: str = "", serializer: Optional[CacheSerializer] = None) -> None:
        self.store = store
        self.prefix = prefix
        self.serializer = serializer or JsonCacheSerializer()
        self.event_listener = CacheEventListener()
    
    def _key(self, key: str) -> str:
        """Generate prefixed cache key."""
        return f"{self.prefix}:{key}" if self.prefix else key
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get item with optional deserialization."""
        cache_key = self._key(key)
        raw_value = self.store.get(cache_key)
        
        if raw_value is None:
            self.event_listener.fire(CacheEvent(CacheOperation.GET, cache_key))
            return default
        
        try:
            value = self.serializer.unserialize(raw_value) if isinstance(raw_value, str) else raw_value
            self.event_listener.fire(CacheEvent(CacheOperation.GET, cache_key, value))
            return value
        except Exception:
            return default
    
    def put(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Put item with serialization."""
        cache_key = self._key(key)
        
        try:
            serialized_value = self.serializer.serialize(value)
            result = self.store.put(cache_key, serialized_value, ttl)
            self.event_listener.fire(CacheEvent(CacheOperation.PUT, cache_key, value, ttl))
            return result
        except Exception:
            return False
    
    def remember(self, key: str, ttl: Optional[int], callback: Callable[[], T]) -> T:
        """Remember value with type safety."""
        value = self.get(key)
        if value is not None:
            return value  # type: ignore
        
        fresh_value = callback()
        self.put(key, fresh_value, ttl)
        return fresh_value
    
    def flush_prefix(self) -> bool:
        """Flush all keys with this prefix (simplified implementation)."""
        # In a real implementation, you'd need to track keys or use pattern matching
        return True


# Enhanced cache manager with additional features
# Global cache manager
cache_manager = CacheManager()