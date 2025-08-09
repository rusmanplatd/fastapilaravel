from __future__ import annotations

import json
import hashlib
import pickle
import time
from typing import Dict, Any, List, Optional, Union, Callable, TypeVar, Generic, TYPE_CHECKING
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import threading
from functools import wraps
from contextlib import asynccontextmanager

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore
    REDIS_AVAILABLE = False

try:
    import memcache  # type: ignore
    MEMCACHE_AVAILABLE = True
except ImportError:
    memcache = None  # type: ignore
    MEMCACHE_AVAILABLE = False

T = TypeVar('T')


class CacheStrategy(str, Enum):
    """Cache strategy enumeration."""
    WRITE_THROUGH = "write_through"        # Write to cache and storage simultaneously
    WRITE_BEHIND = "write_behind"          # Write to cache immediately, storage later
    WRITE_AROUND = "write_around"          # Write directly to storage, invalidate cache
    READ_THROUGH = "read_through"          # Read from cache, fetch from storage if miss
    CACHE_ASIDE = "cache_aside"            # Application manages cache explicitly
    REFRESH_AHEAD = "refresh_ahead"        # Proactively refresh before expiration


class EvictionPolicy(str, Enum):
    """Cache eviction policy enumeration."""
    LRU = "lru"                           # Least Recently Used
    LFU = "lfu"                           # Least Frequently Used
    FIFO = "fifo"                         # First In, First Out
    RANDOM = "random"                     # Random eviction
    TTL = "ttl"                           # Time To Live based


@dataclass
class CacheConfig:
    """Configuration for cache strategies."""
    strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    default_ttl: int = 3600               # Default TTL in seconds
    max_size: int = 10000                 # Maximum cache size
    compression_enabled: bool = True       # Enable data compression
    encryption_enabled: bool = False       # Enable data encryption
    tag_based_invalidation: bool = True    # Support tag-based cache invalidation
    async_writes: bool = True             # Enable asynchronous writes
    circuit_breaker_enabled: bool = True   # Enable circuit breaker pattern
    metrics_enabled: bool = True          # Enable cache metrics collection


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with metadata."""
    key: str
    value: T
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    size: int = 0
    
    def __post_init__(self) -> None:
        if isinstance(self.value, (str, bytes)):
            self.size = len(self.value)
        else:
            self.size = len(str(self.value))
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return self.expires_at is not None and datetime.utcnow() > self.expires_at
    
    def touch(self) -> None:
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for cache operations."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    success_threshold: int = 3
    
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    
    def record_success(self) -> None:
        """Record successful operation."""
        self.failure_count = 0
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.success_count = 0
    
    def record_failure(self) -> None:
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
    
    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            if (self.last_failure_time and 
                datetime.utcnow() - self.last_failure_time >= timedelta(seconds=self.recovery_timeout)):
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                return True
            return False
        
        # HALF_OPEN state
        return True


class CacheMetrics:
    """Cache metrics collector."""
    
    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.writes = 0
        self.deletes = 0
        self.errors = 0
        self.evictions = 0
        self.start_time = datetime.utcnow()
        self._lock = threading.Lock()
    
    def record_hit(self) -> None:
        """Record cache hit."""
        with self._lock:
            self.hits += 1
    
    def record_miss(self) -> None:
        """Record cache miss."""
        with self._lock:
            self.misses += 1
    
    def record_write(self) -> None:
        """Record cache write."""
        with self._lock:
            self.writes += 1
    
    def record_delete(self) -> None:
        """Record cache delete."""
        with self._lock:
            self.deletes += 1
    
    def record_error(self) -> None:
        """Record cache error."""
        with self._lock:
            self.errors += 1
    
    def record_eviction(self) -> None:
        """Record cache eviction."""
        with self._lock:
            self.evictions += 1
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.hits + self.misses
        return self.hits / total_requests if total_requests > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate."""
        return 1.0 - self.hit_rate
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        uptime = datetime.utcnow() - self.start_time
        total_requests = self.hits + self.misses
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'writes': self.writes,
            'deletes': self.deletes,
            'errors': self.errors,
            'evictions': self.evictions,
            'hit_rate': self.hit_rate,
            'miss_rate': self.miss_rate,
            'total_requests': total_requests,
            'uptime_seconds': uptime.total_seconds(),
            'requests_per_second': total_requests / uptime.total_seconds() if uptime.total_seconds() > 0 else 0
        }


class ProductionCacheManager:
    """
    Production-ready cache manager with advanced strategies and features.
    """
    
    def __init__(self, config: CacheConfig) -> None:
        self.config = config
        self.metrics = CacheMetrics() if config.metrics_enabled else None
        self.circuit_breaker = CircuitBreaker() if config.circuit_breaker_enabled else None
        
        # Initialize backend drivers
        self._drivers: Dict[str, Any] = {}
        self._setup_drivers()
        
        # Tag tracking for invalidation
        self._tag_keys: Dict[str, List[str]] = {}
        self._tag_lock = threading.Lock()
        
        # Background refresh tasks
        self._refresh_tasks: Dict[str, asyncio.Task[Any]] = {}
        
    def _setup_drivers(self) -> None:
        """Setup cache driver backends."""
        if REDIS_AVAILABLE:
            try:
                self._drivers['redis'] = redis.Redis(
                    host='localhost',
                    port=6379,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                self._drivers['redis'].ping()
            except Exception:
                self._drivers.pop('redis', None)
        
        if MEMCACHE_AVAILABLE:
            try:
                self._drivers['memcache'] = memcache.Client(['127.0.0.1:11211'])
            except Exception:
                pass
        
        # Always have in-memory fallback
        self._drivers['memory'] = {}
    
    def _get_preferred_driver(self) -> Any:
        """Get the preferred cache driver."""
        for driver_name in ['redis', 'memcache', 'memory']:
            if driver_name in self._drivers:
                return self._drivers[driver_name]
        return self._drivers['memory']
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        if self.config.compression_enabled:
            import gzip
            serialized = pickle.dumps(value)
            return gzip.compress(serialized)
        else:
            return pickle.dumps(value)
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        if self.config.compression_enabled:
            import gzip
            decompressed = gzip.decompress(data)
            return pickle.loads(decompressed)
        else:
            return pickle.loads(data)
    
    def _generate_cache_key(self, key: str, namespace: Optional[str] = None) -> str:
        """Generate prefixed cache key."""
        if namespace:
            return f"cache:{namespace}:{key}"
        return f"cache:{key}"
    
    def _can_execute_operation(self) -> bool:
        """Check if cache operation can be executed (circuit breaker)."""
        if not self.circuit_breaker:
            return True
        return self.circuit_breaker.can_execute()
    
    def _record_success(self) -> None:
        """Record successful operation."""
        if self.circuit_breaker:
            self.circuit_breaker.record_success()
    
    def _record_failure(self) -> None:
        """Record failed operation."""
        if self.circuit_breaker:
            self.circuit_breaker.record_failure()
        if self.metrics:
            self.metrics.record_error()
    
    async def get(self, key: str, namespace: Optional[str] = None) -> Optional[Any]:
        """Get value from cache."""
        if not self._can_execute_operation():
            return None
        
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            driver = self._get_preferred_driver()
            
            if isinstance(driver, dict):  # Memory cache
                entry = driver.get(cache_key)
                if entry and not entry.is_expired():
                    entry.touch()
                    if self.metrics:
                        self.metrics.record_hit()
                    self._record_success()
                    return entry.value
                elif entry and entry.is_expired():
                    del driver[cache_key]
            
            elif hasattr(driver, 'get'):  # Redis/Memcache
                cached_data = driver.get(cache_key)
                if cached_data:
                    value = self._deserialize_value(cached_data)
                    if self.metrics:
                        self.metrics.record_hit()
                    self._record_success()
                    return value
            
            if self.metrics:
                self.metrics.record_miss()
            return None
            
        except Exception as e:
            self._record_failure()
            # Fallback to direct storage access or return None
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """Set value in cache."""
        if not self._can_execute_operation():
            return False
        
        cache_key = self._generate_cache_key(key, namespace)
        ttl = ttl or self.config.default_ttl
        
        try:
            driver = self._get_preferred_driver()
            
            if isinstance(driver, dict):  # Memory cache
                expires_at = datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None
                entry = CacheEntry(
                    key=cache_key,
                    value=value,
                    created_at=datetime.utcnow(),
                    expires_at=expires_at,
                    tags=tags or []
                )
                driver[cache_key] = entry
            
            elif hasattr(driver, 'setex'):  # Redis
                serialized_value = self._serialize_value(value)
                if ttl > 0:
                    driver.setex(cache_key, ttl, serialized_value)
                else:
                    driver.set(cache_key, serialized_value)
            
            elif hasattr(driver, 'set'):  # Memcache
                serialized_value = self._serialize_value(value)
                driver.set(cache_key, serialized_value, time=ttl if ttl > 0 else 0)
            
            # Track tags for invalidation
            if tags and self.config.tag_based_invalidation:
                self._track_tags(cache_key, tags)
            
            if self.metrics:
                self.metrics.record_write()
            
            self._record_success()
            return True
            
        except Exception as e:
            self._record_failure()
            return False
    
    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """Delete value from cache."""
        cache_key = self._generate_cache_key(key, namespace)
        
        try:
            driver = self._get_preferred_driver()
            
            if isinstance(driver, dict):  # Memory cache
                if cache_key in driver:
                    del driver[cache_key]
            
            elif hasattr(driver, 'delete'):
                driver.delete(cache_key)
            
            if self.metrics:
                self.metrics.record_delete()
            
            return True
            
        except Exception:
            return False
    
    def _track_tags(self, cache_key: str, tags: List[str]) -> None:
        """Track tags for cache key."""
        with self._tag_lock:
            for tag in tags:
                if tag not in self._tag_keys:
                    self._tag_keys[tag] = []
                if cache_key not in self._tag_keys[tag]:
                    self._tag_keys[tag].append(cache_key)
    
    async def invalidate_by_tags(self, tags: List[str]) -> int:
        """Invalidate cache entries by tags."""
        invalidated_count = 0
        
        with self._tag_lock:
            keys_to_invalidate = set()
            for tag in tags:
                if tag in self._tag_keys:
                    keys_to_invalidate.update(self._tag_keys[tag])
                    del self._tag_keys[tag]
        
        for cache_key in keys_to_invalidate:
            if await self.delete(cache_key):
                invalidated_count += 1
        
        return invalidated_count
    
    async def remember(
        self,
        key: str,
        callback: Callable[[], Any],
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Any:
        """
        Get from cache or execute callback and store result.
        Classic cache-aside pattern.
        """
        # Try to get from cache first
        cached_value = await self.get(key, namespace)
        if cached_value is not None:
            return cached_value
        
        # Execute callback and cache result
        if asyncio.iscoroutinefunction(callback):
            value = await callback()
        else:
            value = callback()
        
        await self.set(key, value, ttl, namespace, tags)
        return value
    
    async def remember_forever(
        self,
        key: str,
        callback: Callable[[], Any],
        namespace: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Any:
        """Remember value forever (no TTL)."""
        return await self.remember(key, callback, ttl=0, namespace=namespace, tags=tags)
    
    def cache_decorator(
        self,
        key_generator: Optional[Callable[..., str]] = None,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        Decorator for caching function results.
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T:
                # Generate cache key
                if key_generator:
                    cache_key = key_generator(*args, **kwargs)
                else:
                    # Default key generation based on function name and args
                    args_str = str(args) + str(sorted(kwargs.items()))
                    cache_key = f"{func.__name__}:{hashlib.md5(args_str.encode()).hexdigest()}"
                
                result = await self.remember(
                    cache_key,
                    lambda: func(*args, **kwargs),
                    ttl,
                    namespace,
                    tags
                )
                return result  # type: ignore
            
            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> T:
                return asyncio.run(async_wrapper(*args, **kwargs))
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper  # type: ignore
            else:
                return sync_wrapper  # type: ignore
        
        return decorator
    
    async def flush(self, namespace: Optional[str] = None) -> bool:
        """Flush cache entries."""
        try:
            driver = self._get_preferred_driver()
            
            if isinstance(driver, dict):  # Memory cache
                if namespace:
                    keys_to_delete = [k for k in driver.keys() if k.startswith(f"cache:{namespace}:")]
                    for key in keys_to_delete:
                        del driver[key]
                else:
                    driver.clear()
            
            elif hasattr(driver, 'flushall'):  # Redis
                if namespace:
                    # Delete keys with namespace pattern
                    pattern = f"cache:{namespace}:*"
                    keys = driver.keys(pattern)
                    if keys:
                        driver.delete(*keys)
                else:
                    driver.flushall()
            
            return True
            
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {}
        
        if self.metrics:
            stats.update(self.metrics.get_stats())
        
        if self.circuit_breaker:
            stats['circuit_breaker'] = {
                'state': self.circuit_breaker.state,
                'failure_count': self.circuit_breaker.failure_count,
                'success_count': self.circuit_breaker.success_count,
            }
        
        # Add driver information
        stats['drivers'] = list(self._drivers.keys())
        stats['preferred_driver'] = type(self._get_preferred_driver()).__name__
        
        # Add configuration
        stats['config'] = {
            'strategy': self.config.strategy,
            'eviction_policy': self.config.eviction_policy,
            'default_ttl': self.config.default_ttl,
            'max_size': self.config.max_size,
            'compression_enabled': self.config.compression_enabled,
            'tag_based_invalidation': self.config.tag_based_invalidation,
        }
        
        return stats


# Global cache manager instance
_cache_manager: Optional[ProductionCacheManager] = None


def get_cache_manager() -> ProductionCacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        config = CacheConfig()  # Use default configuration
        _cache_manager = ProductionCacheManager(config)
    return _cache_manager


def cache_config(**kwargs) -> CacheConfig:
    """Create cache configuration with custom settings."""
    return CacheConfig(**kwargs)


# Convenience functions
async def cache_get(key: str, namespace: Optional[str] = None) -> Optional[Any]:
    """Get value from cache."""
    return await get_cache_manager().get(key, namespace)


async def cache_set(
    key: str,
    value: Any,
    ttl: Optional[int] = None,
    namespace: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> bool:
    """Set value in cache."""
    return await get_cache_manager().set(key, value, ttl, namespace, tags)


async def cache_remember(
    key: str,
    callback: Callable[[], Any],
    ttl: Optional[int] = None,
    namespace: Optional[str] = None,
    tags: Optional[List[str]] = None
) -> Any:
    """Remember value using cache-aside pattern."""
    return await get_cache_manager().remember(key, callback, ttl, namespace, tags)


def cached(
    key_generator: Optional[Callable[..., str]] = None,
    ttl: Optional[int] = None,
    namespace: Optional[str] = None,
    tags: Optional[List[str]] = None
):
    """Decorator for caching function results."""
    return get_cache_manager().cache_decorator(key_generator, ttl, namespace, tags)


# Example usage patterns
class UserCacheStrategy:
    """Example cache strategy for user data."""
    
    def __init__(self, cache_manager: ProductionCacheManager):
        self.cache = cache_manager
    
    @cached(
        key_generator=lambda self, user_id: f"user:{user_id}",
        ttl=3600,  # 1 hour
        tags=["users"]
    )
    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile with caching."""
        # This would be replaced with actual database query
        return {"id": user_id, "name": f"User {user_id}"}
    
    @cached(
        key_generator=lambda self, user_id: f"user_permissions:{user_id}",
        ttl=1800,  # 30 minutes
        tags=["users", "permissions"]
    )
    async def get_user_permissions(self, user_id: int) -> List[str]:
        """Get user permissions with caching."""
        # This would be replaced with actual database query
        return ["read", "write"]
    
    async def invalidate_user_cache(self, user_id: int) -> None:
        """Invalidate all cache entries for a user."""
        await self.cache.delete(f"user:{user_id}")
        await self.cache.delete(f"user_permissions:{user_id}")
        await self.cache.invalidate_by_tags(["users"])