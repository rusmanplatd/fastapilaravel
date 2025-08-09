from __future__ import annotations

from typing import Any, Callable, Optional, TypeVar, Union, Dict, List
from functools import wraps
import asyncio
import time
import inspect
import hashlib
import json
from datetime import datetime, timedelta

from .CacheStore import cache_manager, CacheOperation, CacheEvent

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


def cache_key(*args: Any, **kwargs: Any) -> str:
    """Generate cache key from function arguments."""
    # Create a deterministic key from arguments
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    key_string = json.dumps(key_data, default=str, sort_keys=True)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: Optional[int] = None, 
           key_prefix: str = "", 
           store: Optional[str] = None) -> Callable[[F], F]:
    """
    Cache decorator for functions.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
        store: Cache store name to use
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            func_name = f"{func.__module__}.{func.__qualname__}"
            args_key = cache_key(*args, **kwargs)
            cache_key_str = f"{key_prefix}:{func_name}:{args_key}" if key_prefix else f"{func_name}:{args_key}"
            
            # Try to get from cache
            cache_store = cache_manager.store(store)
            cached_result = cache_store.get(cache_key_str)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_store.put(cache_key_str, result, ttl)
            return result
        
        # Add cache management methods to the wrapper
        wrapper.cache_flush = lambda: cache_manager.store(store).flush()  # type: ignore
        wrapper.cache_forget = lambda *args, **kwargs: cache_manager.store(store).forget(  # type: ignore
            f"{key_prefix}:{func.__module__}.{func.__qualname__}:{cache_key(*args, **kwargs)}"
            if key_prefix else f"{func.__module__}.{func.__qualname__}:{cache_key(*args, **kwargs)}"
        )
        
        return wrapper  # type: ignore
    
    return decorator


def cache_async(ttl: Optional[int] = None,
                key_prefix: str = "",
                store: Optional[str] = None) -> Callable[[F], F]:
    """
    Cache decorator for async functions.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            func_name = f"{func.__module__}.{func.__qualname__}"
            args_key = cache_key(*args, **kwargs)
            cache_key_str = f"{key_prefix}:{func_name}:{args_key}" if key_prefix else f"{func_name}:{args_key}"
            
            # Try to get from cache
            cache_store = cache_manager.store(store)
            cached_result = cache_store.get(cache_key_str)
            
            if cached_result is not None:
                return cached_result
            
            # Execute async function and cache result
            result = await func(*args, **kwargs)
            cache_store.put(cache_key_str, result, ttl)
            return result
        
        return wrapper  # type: ignore
    
    return decorator


def cache_lock(key_func: Optional[Callable[..., str]] = None,
               timeout: int = 60) -> Callable[[F], F]:
    """
    Cache lock decorator to prevent concurrent execution.
    
    Args:
        key_func: Function to generate lock key from arguments
        timeout: Lock timeout in seconds
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Generate lock key
            if key_func:
                lock_key = key_func(*args, **kwargs)
            else:
                func_name = f"{func.__module__}.{func.__qualname__}"
                args_key = cache_key(*args, **kwargs)
                lock_key = f"lock:{func_name}:{args_key}"
            
            # Acquire lock and execute
            with cache_manager.lock(lock_key, timeout):
                return func(*args, **kwargs)
        
        return wrapper  # type: ignore
    
    return decorator


class CacheThrough:
    """Cache-through pattern implementation."""
    
    def __init__(self, prefix: str = "", ttl: Optional[int] = None, store: Optional[str] = None):
        self.prefix = prefix
        self.ttl = ttl
        self.store = store
        self.cache_store = cache_manager.store(store)
    
    def get_or_set(self, key: str, value_func: Callable[[], T], ttl: Optional[int] = None) -> T:
        """Get value from cache or set it using the provided function."""
        cache_key = f"{self.prefix}:{key}" if self.prefix else key
        ttl = ttl or self.ttl
        
        return self.cache_store.remember(cache_key, ttl, value_func)  # type: ignore
    
    def invalidate(self, key: str) -> bool:
        """Invalidate a cache entry."""
        cache_key = f"{self.prefix}:{key}" if self.prefix else key
        return self.cache_store.forget(cache_key)
    
    def invalidate_pattern(self, pattern: str) -> bool:
        """Invalidate cache entries matching a pattern (simplified)."""
        # In a real implementation, you'd need pattern matching support
        return True


class CacheAside:
    """Cache-aside pattern implementation."""
    
    def __init__(self, prefix: str = "", ttl: Optional[int] = None, store: Optional[str] = None):
        self.prefix = prefix
        self.ttl = ttl
        self.cache_store = cache_manager.store(store)
    
    def get(self, key: str) -> Any:
        """Get value from cache."""
        cache_key = f"{self.prefix}:{key}" if self.prefix else key
        return self.cache_store.get(cache_key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        cache_key = f"{self.prefix}:{key}" if self.prefix else key
        ttl = ttl or self.ttl
        return self.cache_store.put(cache_key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        cache_key = f"{self.prefix}:{key}" if self.prefix else key
        return self.cache_store.forget(cache_key)


class BulkCacheOperations:
    """Bulk cache operations utility."""
    
    def __init__(self, store: Optional[str] = None):
        self.cache_store = cache_manager.store(store)
    
    def get_many(self, keys: List[str], prefix: str = "") -> Dict[str, Any]:
        """Get multiple values from cache."""
        prefixed_keys = [f"{prefix}:{key}" if prefix else key for key in keys]
        results = self.cache_store.many(prefixed_keys)
        
        # Remove prefix from results
        if prefix:
            return {key.replace(f"{prefix}:", ""): value for key, value in results.items()}
        return results
    
    def set_many(self, data: Dict[str, Any], ttl: Optional[int] = None, prefix: str = "") -> bool:
        """Set multiple values in cache."""
        prefixed_data = {}
        for key, value in data.items():
            cache_key = f"{prefix}:{key}" if prefix else key
            prefixed_data[cache_key] = value
        
        return self.cache_store.put_many(prefixed_data, ttl)
    
    def delete_many(self, keys: List[str], prefix: str = "") -> Dict[str, bool]:
        """Delete multiple values from cache."""
        results = {}
        for key in keys:
            cache_key = f"{prefix}:{key}" if prefix else key
            results[key] = self.cache_store.forget(cache_key)
        return results


class CacheMetrics:
    """Cache metrics and monitoring."""
    
    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.start_time = time.time()
        
        # Listen to cache events
        cache_manager.listen(CacheOperation.GET, self._on_get)
        cache_manager.listen(CacheOperation.PUT, self._on_put)
        cache_manager.listen(CacheOperation.FORGET, self._on_forget)
    
    def _on_get(self, event: CacheEvent) -> None:
        """Handle cache get events."""
        if event.value is not None:
            self.hits += 1
        else:
            self.misses += 1
    
    def _on_put(self, event: CacheEvent) -> None:
        """Handle cache put events."""
        self.sets += 1
    
    def _on_forget(self, event: CacheEvent) -> None:
        """Handle cache forget events."""
        self.deletes += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        uptime = time.time() - self.start_time
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'sets': self.sets,
            'deletes': self.deletes,
            'total_requests': total_requests,
            'hit_rate': f"{hit_rate:.2f}%",
            'uptime_seconds': uptime,
            'requests_per_second': total_requests / uptime if uptime > 0 else 0
        }
    
    def reset(self) -> None:
        """Reset metrics."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.start_time = time.time()


class CacheWarming:
    """Cache warming utilities."""
    
    def __init__(self, store: Optional[str] = None):
        self.cache_store = cache_manager.store(store)
    
    def warm(self, warming_plan: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Warm cache with predefined data.
        
        Args:
            warming_plan: List of dicts with 'key', 'value_func', and optional 'ttl'
        """
        results = {}
        
        for item in warming_plan:
            key = item['key']
            value_func = item['value_func']
            ttl = item.get('ttl')
            
            try:
                value = value_func() if callable(value_func) else value_func
                results[key] = self.cache_store.put(key, value, ttl)
            except Exception as e:
                results[key] = False
        
        return results
    
    def warm_async(self, warming_plan: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Asynchronously warm cache (simplified implementation)."""
        # In a real implementation, you'd use asyncio for concurrent warming
        return self.warm(warming_plan)


# Global instances for easy access
cache_metrics = CacheMetrics()
cache_through = CacheThrough()
cache_aside = CacheAside()
bulk_cache = BulkCacheOperations()
cache_warming = CacheWarming()