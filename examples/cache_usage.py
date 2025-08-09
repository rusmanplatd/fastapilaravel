#!/usr/bin/env python3
"""
Laravel-Style Cache System Usage Examples

This demonstrates the comprehensive cache system implemented for the FastAPI Laravel project.
"""

from typing import Dict, List, Any
import asyncio
import time

# Import cache components
from app.Cache import (
    cache_manager, cached, cache_async, cache_lock,
    CacheThrough, CacheAside, BulkCacheOperations,
    CacheMetrics, CacheWarming, CacheLock,
    configure_cache_manager, get_cache_config
)


class CacheExamples:
    """Examples showing different cache patterns and features."""
    
    def __init__(self) -> None:
        self.cache_through = CacheThrough("user_cache", ttl=300)
        self.cache_aside = CacheAside("product_cache", ttl=600)
        self.bulk_ops = BulkCacheOperations()
        self.cache_warming = CacheWarming()
        
    def basic_cache_operations(self) -> None:
        """Demonstrate basic cache operations."""
        print("=== Basic Cache Operations ===")
        
        # Store data
        cache_manager.put("user:1", {"name": "John", "email": "john@example.com"}, 300)
        print("Stored user data")
        
        # Retrieve data
        user = cache_manager.get("user:1", {})
        print(f"Retrieved user: {user}")
        
        # Check if key exists
        exists = cache_manager.store().has("user:1")
        print(f"User exists: {exists}")
        
        # Increment counter
        cache_manager.store().put("counter", 0)
        new_count = cache_manager.store().increment("counter", 5)
        print(f"Counter value: {new_count}")
        
        # Remember pattern
        def expensive_operation() -> str:
            print("Performing expensive calculation...")
            time.sleep(0.1)  # Simulate work
            return "computed_result"
        
        result = cache_manager.remember("expensive:key", 300, expensive_operation)
        print(f"First call result: {result}")
        
        # Second call should be from cache
        result = cache_manager.remember("expensive:key", 300, expensive_operation)
        print(f"Second call result (cached): {result}")
        
        print()
    
    def decorator_examples(self) -> None:
        """Show cache decorator usage."""
        print("=== Cache Decorators ===")
        
        @cached(ttl=300, key_prefix="math")
        def fibonacci(n: int) -> int:
            """Cached fibonacci function."""
            if n < 2:
                return n
            return fibonacci(n-1) + fibonacci(n-2)
        
        @cache_lock(timeout=30)
        def critical_section(data: str) -> str:
            """Function that should only run once at a time."""
            print(f"Processing {data}...")
            time.sleep(0.1)
            return f"processed_{data}"
        
        # Test cached function
        start_time = time.time()
        result = fibonacci(10)
        first_call_time = time.time() - start_time
        print(f"Fibonacci(10) = {result} (took {first_call_time:.4f}s)")
        
        start_time = time.time()
        result = fibonacci(10)  # Should be cached
        second_call_time = time.time() - start_time
        print(f"Fibonacci(10) = {result} (cached, took {second_call_time:.4f}s)")
        
        # Test locked function
        result = critical_section("test_data")
        print(f"Critical section result: {result}")
        
        print()
    
    async def async_cache_example(self) -> None:
        """Show async cache decorator."""
        print("=== Async Cache Example ===")
        
        @cache_async(ttl=300, key_prefix="async")
        async def fetch_data(user_id: int) -> Dict[str, Any]:
            """Async function with caching."""
            print(f"Fetching data for user {user_id}...")
            await asyncio.sleep(0.1)  # Simulate async work
            return {"user_id": user_id, "data": f"user_data_{user_id}"}
        
        start_time = time.time()
        result = await fetch_data(123)
        first_call_time = time.time() - start_time
        print(f"First call result: {result} (took {first_call_time:.4f}s)")
        
        start_time = time.time()
        result = await fetch_data(123)  # Should be cached
        second_call_time = time.time() - start_time
        print(f"Second call result: {result} (cached, took {second_call_time:.4f}s)")
        
        print()
    
    def cache_patterns(self) -> None:
        """Demonstrate different cache patterns."""
        print("=== Cache Patterns ===")
        
        # Cache-Through Pattern
        def load_user_profile(user_id: str) -> Dict[str, Any]:
            print(f"Loading profile for user {user_id} from database...")
            return {"id": user_id, "name": f"User {user_id}", "profile": "data"}
        
        profile = self.cache_through.get_or_set(
            "profile:123", 
            lambda: load_user_profile("123")
        )
        print(f"Cache-through result: {profile}")
        
        # Cache-Aside Pattern  
        cache_key = "product:456"
        product = self.cache_aside.get(cache_key)
        
        if product is None:
            print("Cache miss - loading from database")
            product = {"id": "456", "name": "Product 456", "price": 29.99}
            self.cache_aside.set(cache_key, product)
        else:
            print("Cache hit")
        
        print(f"Product: {product}")
        
        print()
    
    def bulk_operations(self) -> None:
        """Show bulk cache operations."""
        print("=== Bulk Operations ===")
        
        # Set multiple values
        user_data = {
            "user:100": {"name": "Alice", "role": "admin"},
            "user:200": {"name": "Bob", "role": "user"},
            "user:300": {"name": "Charlie", "role": "user"}
        }
        
        success = self.bulk_ops.set_many(user_data, ttl=300, prefix="bulk")
        print(f"Bulk set success: {success}")
        
        # Get multiple values
        keys = ["user:100", "user:200", "user:300"]
        results = self.bulk_ops.get_many(keys, prefix="bulk")
        print(f"Bulk get results: {results}")
        
        # Delete multiple values
        delete_results = self.bulk_ops.delete_many(keys[:2], prefix="bulk")
        print(f"Bulk delete results: {delete_results}")
        
        print()
    
    def locking_example(self) -> None:
        """Demonstrate cache locking."""
        print("=== Cache Locking ===")
        
        lock_key = "shared_resource"
        
        # Acquire lock
        lock = cache_manager.lock(lock_key, timeout=30)
        
        try:
            if lock.acquire(blocking=False):
                print("Lock acquired successfully")
                
                # Do some work that should be exclusive
                print("Processing shared resource...")
                time.sleep(0.1)
                
                print("Work completed")
            else:
                print("Could not acquire lock")
        finally:
            lock.release()
            print("Lock released")
        
        # Using context manager (recommended)
        with cache_manager.lock("another_resource", 30):
            print("Working with locked resource via context manager")
            time.sleep(0.05)
        
        print()
    
    def atomic_operations(self) -> None:
        """Show atomic cache transactions."""
        print("=== Atomic Operations ===")
        
        # Using atomic transaction
        with cache_manager.atomic() as transaction:
            transaction.put("atomic:key1", "value1", 300)
            transaction.put("atomic:key2", "value2", 300)
            transaction.put("atomic:key3", "value3", 300)
            
            print("Added 3 items to atomic transaction")
            # All operations will be committed when context exits
        
        # Verify all were stored
        for i in range(1, 4):
            value = cache_manager.get(f"atomic:key{i}")
            print(f"atomic:key{i} = {value}")
        
        print()
    
    def cache_warming(self) -> None:
        """Demonstrate cache warming."""
        print("=== Cache Warming ===")
        
        def load_popular_products() -> List[Dict[str, Any]]:
            print("Loading popular products...")
            return [
                {"id": "prod1", "name": "Popular Product 1"},
                {"id": "prod2", "name": "Popular Product 2"},
                {"id": "prod3", "name": "Popular Product 3"}
            ]
        
        def load_user_preferences(user_id: str) -> Dict[str, Any]:
            print(f"Loading preferences for user {user_id}")
            return {"theme": "dark", "language": "en", "notifications": True}
        
        warming_plan = [
            {
                "key": "popular_products",
                "value_func": load_popular_products,
                "ttl": 3600
            },
            {
                "key": "user:1:preferences", 
                "value_func": lambda: load_user_preferences("1"),
                "ttl": 1800
            }
        ]
        
        results = self.cache_warming.warm(warming_plan)
        print(f"Cache warming results: {results}")
        
        # Verify data was cached
        products = cache_manager.get("popular_products")
        prefs = cache_manager.get("user:1:preferences")
        print(f"Cached products: {len(products) if products else 0} items")
        print(f"Cached preferences: {prefs}")
        
        print()
    
    def tagged_cache(self) -> None:
        """Show tagged cache operations."""
        print("=== Tagged Cache ===")
        
        # Create tagged cache instances
        user_cache = cache_manager.tags("users", "profiles")
        product_cache = cache_manager.tags("products", "catalog")
        
        # Store data with tags
        user_cache.put("user:1", {"name": "John"}, 300)
        user_cache.put("profile:1", {"bio": "Developer"}, 300)
        
        product_cache.put("product:1", {"name": "Widget"}, 600)
        product_cache.put("category:electronics", ["widget", "gadget"], 600)
        
        # Retrieve tagged data
        user = user_cache.get("user:1")
        product = product_cache.get("product:1")
        
        print(f"Tagged user data: {user}")
        print(f"Tagged product data: {product}")
        
        # Tags help with organized cache invalidation
        print("Tagged cache allows organized invalidation by tag groups")
        
        print()


def show_cache_metrics() -> None:
    """Display cache metrics and statistics."""
    print("=== Cache Metrics ===")
    
    from app.Cache.CacheUtils import cache_metrics
    
    # Perform some cache operations to generate metrics
    for i in range(10):
        cache_manager.put(f"metric_test:{i}", f"value_{i}", 60)
    
    for i in range(15):
        cache_manager.get(f"metric_test:{i % 8}")  # Some hits, some misses
    
    # Get statistics
    stats = cache_metrics.get_stats()
    print("Cache Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print()


def configuration_example() -> None:
    """Show cache configuration management."""
    print("=== Cache Configuration ===")
    
    # Get different environment configs
    dev_config = get_cache_config("development")
    prod_config = get_cache_config("production")
    
    print(f"Development default store: {dev_config.default}")
    print(f"Development stores: {list(dev_config.stores.keys())}")
    
    print(f"Production default store: {prod_config.default}")
    print(f"Production stores: {list(prod_config.stores.keys())}")
    
    # You can configure the cache manager with different settings
    # configure_cache_manager(dev_config)
    
    print()


async def main() -> None:
    """Run all cache examples."""
    print("🚀 Laravel-Style Cache System Examples")
    print("=" * 50)
    
    examples = CacheExamples()
    
    # Run all examples
    examples.basic_cache_operations()
    examples.decorator_examples()
    await examples.async_cache_example()
    examples.cache_patterns()
    examples.bulk_operations()
    examples.locking_example()
    examples.atomic_operations()
    examples.cache_warming()
    examples.tagged_cache()
    
    show_cache_metrics()
    configuration_example()
    
    print("✅ All cache examples completed successfully!")
    print("\nKey Features Demonstrated:")
    print("- Basic cache operations (get, put, forget, increment)")
    print("- Cache decorators for functions (@cached, @cache_async, @cache_lock)")
    print("- Cache patterns (cache-through, cache-aside)")
    print("- Bulk operations")
    print("- Distributed locking")
    print("- Atomic transactions")
    print("- Cache warming")
    print("- Tagged cache operations")
    print("- Metrics and monitoring")
    print("- Multiple store configurations")


if __name__ == "__main__":
    asyncio.run(main())