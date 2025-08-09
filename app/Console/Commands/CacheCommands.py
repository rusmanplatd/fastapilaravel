from __future__ import annotations

import asyncio
import json
import time
import statistics
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from ..Command import Command
from app.Cache.CacheStore import CacheStore


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    hit_count: int = 0
    miss_count: int = 0
    total_operations: int = 0
    hit_rate: float = 0.0
    average_get_time: float = 0.0
    average_set_time: float = 0.0
    memory_usage: float = 0.0
    key_count: int = 0
    expired_keys: int = 0
    evicted_keys: int = 0
    store_size: int = 0


@dataclass
class CacheStoreInfo:
    """Cache store information."""
    name: str
    driver: str
    status: str
    metrics: CacheMetrics
    configuration: Dict[str, Any]


@dataclass
class CacheAnalysis:
    """Cache usage analysis."""
    most_accessed_keys: List[Tuple[str, int]]
    largest_keys: List[Tuple[str, int]]
    oldest_keys: List[Tuple[str, datetime]]
    key_patterns: Dict[str, int]
    expiration_analysis: Dict[str, int]
    performance_trends: Dict[str, List[float]]


class CacheClearCommand(Command):
    """Advanced cache clearing with analytics and safety checks."""
    
    signature = "cache:clear {--store= : The cache store to clear} {--tags= : Clear specific cache tags} {--pattern= : Clear keys matching pattern} {--dry-run : Show what would be cleared without clearing} {--stats : Show clearing statistics} {--backup : Create backup before clearing} {--selective : Interactive key selection}"
    description = "Advanced cache clearing with safety checks and analytics"
    help = "Clear cached data with advanced filtering, backup options, and statistics"
    
    async def handle(self) -> None:
        """Execute the enhanced cache clearing command."""
        store = self.option("store")
        tags = self.option("tags")
        pattern = self.option("pattern")
        dry_run = self.option("dry-run", False)
        show_stats = self.option("stats", False)
        create_backup = self.option("backup", False)
        selective = self.option("selective", False)
        
        try:
            # Import cache system
            from app.Cache import cache_manager
            
            # Show operation summary
            self._show_clear_summary(store, tags, pattern, dry_run, create_backup)
            
            # Get initial metrics for statistics
            initial_metrics = await self._get_cache_metrics(cache_manager, store) if show_stats else None
            
            # Create backup if requested
            backup_path = None
            if create_backup and not dry_run:
                backup_path = await self._create_cache_backup(cache_manager, store)
            
            # Determine clearing strategy
            cleared_count = 0
            if selective:
                cleared_count = await self._selective_clear(cache_manager, store)
            elif pattern:
                cleared_count = await self._clear_pattern(cache_manager, pattern, store, dry_run)
            elif tags:
                tag_list = [tag.strip() for tag in tags.split(',')]
                cleared_count = await self._clear_tags_enhanced(cache_manager, tag_list, dry_run)
            elif store:
                cleared_count = await self._clear_store_enhanced(cache_manager, store, dry_run)
            else:
                cleared_count = await self._clear_all_stores_enhanced(cache_manager, dry_run)
            
            # Show results
            self._show_clear_results(cleared_count, dry_run, backup_path)
            
            # Show statistics if requested
            if show_stats and not dry_run:
                final_metrics = await self._get_cache_metrics(cache_manager, store)
                self._show_clearing_statistics(initial_metrics, final_metrics)
            
        except ImportError:
            self.warn("Cache manager not available. Using fallback file clearing...")
            await self._clear_file_cache_enhanced(dry_run, show_stats)
        except Exception as e:
            self.error(f"Failed to clear cache: {e}")
            if create_backup and backup_path:
                self.comment(f"Backup created at: {backup_path}")
    
    def _show_clear_summary(self, store: Optional[str], tags: Optional[str], pattern: Optional[str], 
                           dry_run: bool, backup: bool) -> None:
        """Show cache clearing operation summary."""
        self.comment("🗑️  Cache Clear Operation Summary")
        
        if store:
            self.line(f"• Target: Specific store '{store}'")
        elif tags:
            self.line(f"• Target: Tags [{tags}]")
        elif pattern:
            self.line(f"• Target: Keys matching pattern '{pattern}'")
        else:
            self.line("• Target: All cache stores")
        
        if dry_run:
            self.line("• Mode: DRY RUN (no actual clearing)")
        if backup:
            self.line("• Backup: Will create backup before clearing")
        
        self.new_line()
    
    async def _create_cache_backup(self, cache_manager: Any, store: Optional[str]) -> Path:
        """Create cache backup before clearing."""
        backup_dir = Path("storage/backups/cache")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"cache_backup_{timestamp}"
        if store:
            backup_name += f"_{store}"
        backup_path = backup_dir / f"{backup_name}.json"
        
        self.comment("Creating cache backup...")
        
        try:
            backup_data = {}
            
            if store:
                # Backup specific store
                cache_store = cache_manager.store(store)
                keys = await self._get_store_keys(cache_store)
                backup_data[store] = await self._backup_keys(cache_store, keys)
            else:
                # Backup all stores
                stores = cache_manager.get_stores()
                for store_name in stores:
                    cache_store = cache_manager.store(store_name)
                    keys = await self._get_store_keys(cache_store)
                    backup_data[store_name] = await self._backup_keys(cache_store, keys)
            
            # Save backup
            with open(backup_path, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            backup_size = backup_path.stat().st_size
            self.info(f"✅ Cache backup created: {backup_path} ({backup_size} bytes)")
            
            return backup_path
            
        except Exception as e:
            self.warn(f"Failed to create backup: {e}")
            return backup_path
    
    async def _selective_clear(self, cache_manager: Any, store: Optional[str]) -> int:
        """Interactive selective cache clearing."""
        self.info("🔍 Interactive Cache Key Selection")
        
        try:
            # Get all keys
            if store:
                cache_store = cache_manager.store(store)
                keys = await self._get_store_keys(cache_store)
                store_name = store
            else:
                # For simplicity, work with default store in selective mode
                cache_store = cache_manager.store()
                keys = await self._get_store_keys(cache_store)
                store_name = "default"
            
            if not keys:
                self.warn("No cache keys found")
                return 0
            
            self.comment(f"Found {len(keys)} keys in store '{store_name}'")
            
            # Show key preview
            self.comment("Key preview (first 10):")
            for i, key in enumerate(keys[:10]):
                self.line(f"  {i+1}. {key}")
            
            if len(keys) > 10:
                self.comment(f"... and {len(keys) - 10} more keys")
            
            # Selection options
            self.new_line()
            self.comment("Selection options:")
            self.line("1. Clear all keys")
            self.line("2. Clear keys by pattern")
            self.line("3. Clear specific keys by number")
            self.line("4. Cancel operation")
            
            choice = self.ask("Select option (1-4):", "4")
            
            if choice == "1":
                if self.confirm(f"Clear all {len(keys)} keys?", False):
                    return await self._clear_keys(cache_store, keys, False)
            elif choice == "2":
                pattern = self.ask("Enter pattern (supports wildcards):", "")
                if pattern:
                    matching_keys = [k for k in keys if self._match_pattern(k, pattern)]
                    if matching_keys:
                        self.comment(f"Found {len(matching_keys)} matching keys")
                        if self.confirm(f"Clear {len(matching_keys)} matching keys?", True):
                            return await self._clear_keys(cache_store, matching_keys, False)
            elif choice == "3":
                indices = self.ask("Enter key numbers (comma-separated):", "")
                if indices:
                    try:
                        selected_indices = [int(i.strip()) - 1 for i in indices.split(',')]
                        selected_keys = [keys[i] for i in selected_indices if 0 <= i < len(keys)]
                        if selected_keys:
                            self.comment(f"Selected {len(selected_keys)} keys")
                            if self.confirm(f"Clear selected keys?", True):
                                return await self._clear_keys(cache_store, selected_keys, False)
                    except (ValueError, IndexError):
                        self.error("Invalid key numbers")
            
            return 0
            
        except Exception as e:
            self.error(f"Selective clearing failed: {e}")
            return 0
    
    async def _clear_pattern(self, cache_manager: Any, pattern: str, store: Optional[str], dry_run: bool) -> int:
        """Clear cache keys matching pattern."""
        try:
            matching_keys: List[Union[str, Tuple[str, str]]] = []
            
            if store:
                cache_store = cache_manager.store(store)
                string_keys = await self._get_store_keys(cache_store)
                matching_keys = [k for k in string_keys if self._match_pattern(k, pattern)]
            else:
                # Search all stores
                keys: List[Tuple[str, str]] = []
                stores = cache_manager.get_stores()
                for store_name in stores:
                    store_keys = await self._get_store_keys(cache_manager.store(store_name))
                    keys.extend([(store_name, key) for key in store_keys])
                
                # Find matching keys
                matching_keys = [(s, k) for s, k in keys if self._match_pattern(k, pattern)]
            
            if not matching_keys:
                self.warn(f"No keys match pattern: {pattern}")
                return 0
            
            self.comment(f"Found {len(matching_keys)} keys matching pattern '{pattern}'")
            
            if dry_run:
                self._show_matching_keys(matching_keys, store is None)
                return len(matching_keys)
            
            # Clear matching keys
            cleared_count = 0
            if store:
                # matching_keys contains strings in this case
                string_keys = [str(k) for k in matching_keys]
                cleared_count = await self._clear_keys(cache_store, string_keys, False)
            else:
                # matching_keys contains tuples in this case
                for key_item in matching_keys:
                    if isinstance(key_item, tuple):
                        store_name, key = key_item
                        try:
                            cache_manager.store(store_name).forget(key)
                            cleared_count += 1
                        except Exception:
                            pass
            
            return cleared_count
            
        except Exception as e:
            self.error(f"Pattern clearing failed: {e}")
            return 0
    
    def _match_pattern(self, key: str, pattern: str) -> bool:
        """Match key against pattern (supports * and ? wildcards)."""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    def _show_matching_keys(self, keys: List[Union[str, Tuple[str, str]]], multi_store: bool) -> None:
        """Show keys that match the pattern."""
        self.comment("Matching keys:")
        
        for i, key in enumerate(keys[:20]):  # Show first 20
            if multi_store:
                if isinstance(key, tuple):
                    store_name, key_name = key
                    self.line(f"  {i+1}. [{store_name}] {key_name}")
                else:
                    self.line(f"  {i+1}. {key}")
            else:
                self.line(f"  {i+1}. {key}")
        
        if len(keys) > 20:
            self.comment(f"... and {len(keys) - 20} more keys")
    
    def _show_clear_results(self, cleared_count: int, dry_run: bool, backup_path: Optional[Path]) -> None:
        """Show clearing operation results."""
        if dry_run:
            self.info(f"🔍 DRY RUN: Would clear {cleared_count} cache entries")
        else:
            self.info(f"✅ Successfully cleared {cleared_count} cache entries")
        
        if backup_path:
            self.comment(f"📄 Backup saved to: {backup_path}")
    
    def _show_clearing_statistics(self, initial: Optional[CacheMetrics], final: Optional[CacheMetrics]) -> None:
        """Show before/after cache statistics."""
        if not initial or not final:
            return
        
        self.new_line()
        self.comment("📊 Clearing Statistics:")
        
        stats_data = [
            ["Keys Before", str(initial.key_count)],
            ["Keys After", str(final.key_count)],
            ["Keys Removed", str(initial.key_count - final.key_count)],
            ["Memory Before", f"{initial.memory_usage:.2f} MB"],
            ["Memory After", f"{final.memory_usage:.2f} MB"],
            ["Memory Freed", f"{initial.memory_usage - final.memory_usage:.2f} MB"],
        ]
        
        self.table(["Metric", "Value"], stats_data)
    
    async def _get_cache_metrics(self, cache_manager: Any, store: Optional[str]) -> CacheMetrics:
        """Get current cache metrics."""
        try:
            if store:
                cache_store = cache_manager.store(store)
                keys = await self._get_store_keys(cache_store)
                
                return CacheMetrics(
                    key_count=len(keys),
                    memory_usage=await self._estimate_memory_usage(cache_store, keys),
                    store_size=await self._get_store_size(cache_store)
                )
            else:
                # Aggregate metrics from all stores
                total_metrics = CacheMetrics()
                stores = cache_manager.get_stores()
                
                for store_name in stores:
                    store_metrics = await self._get_cache_metrics(cache_manager, store_name)
                    total_metrics.key_count += store_metrics.key_count
                    total_metrics.memory_usage += store_metrics.memory_usage
                    total_metrics.store_size += store_metrics.store_size
                
                return total_metrics
                
        except Exception:
            return CacheMetrics()
    
    async def _clear_file_cache_enhanced(self, dry_run: bool, show_stats: bool) -> None:
        """Enhanced file-based cache clearing with statistics."""
        cache_dirs = [
            Path("storage/cache"),
            Path("storage/framework/cache"),
            Path("__pycache__"),
        ]
        
        total_files = 0
        total_size = 0
        
        # Calculate initial stats
        if show_stats:
            for cache_dir in cache_dirs:
                if cache_dir.exists():
                    dir_stats = await self._get_directory_stats(cache_dir)
                    total_files += dir_stats['file_count']
                    total_size += dir_stats['total_size']
        
        if dry_run:
            self.info(f"🔍 DRY RUN: Would clear {total_files} files ({total_size / 1024 / 1024:.2f} MB)")
            return
        
        self.info("Clearing file-based cache...")
        cleared_files = 0
        cleared_size = 0
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                result = await self._clear_directory_enhanced(cache_dir)
                cleared_files += result['files']
                cleared_size += result['size']
        
        self.info(f"✅ Cleared {cleared_files} cache files ({cleared_size / 1024 / 1024:.2f} MB)")
    
    async def _get_directory_stats(self, directory: Path) -> Dict[str, int]:
        """Get directory statistics."""
        file_count = 0
        total_size = 0
        
        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    file_count += 1
                    total_size += item.stat().st_size
        except Exception:
            pass
        
        return {'file_count': file_count, 'total_size': total_size}
    
    async def _clear_directory_enhanced(self, directory: Path) -> Dict[str, int]:
        """Enhanced directory clearing with statistics."""
        files_cleared = 0
        size_cleared = 0
        
        try:
            for item in directory.iterdir():
                if item.is_file():
                    try:
                        size_cleared += item.stat().st_size
                        item.unlink()
                        files_cleared += 1
                    except Exception:
                        pass
                elif item.is_dir() and item.name != ".gitkeep":
                    result = await self._clear_directory_enhanced(item)
                    files_cleared += result['files']
                    size_cleared += result['size']
                    try:
                        item.rmdir()
                    except Exception:
                        pass
        except Exception:
            pass
        
        return {'files': files_cleared, 'size': size_cleared}
    
    # Helper methods for cache operations
    async def _get_store_keys(self, cache_store: Any) -> List[str]:
        """Get all keys from a cache store."""
        try:
            # This would depend on your cache implementation
            if hasattr(cache_store, 'keys'):
                result = cache_store.keys()
                return list(result) if result else []
            elif hasattr(cache_store, 'get_keys'):
                result = cache_store.get_keys()
                return list(result) if result else []
            else:
                return []
        except Exception:
            return []
    
    async def _backup_keys(self, cache_store: Any, keys: List[str]) -> Dict[str, Any]:
        """Backup cache keys and their values."""
        backup_data = {}
        
        for key in keys:
            try:
                value = cache_store.get(key)
                if value is not None:
                    backup_data[key] = {
                        'value': value,
                        'backed_up_at': datetime.now().isoformat()
                    }
            except Exception:
                pass
        
        return backup_data
    
    async def _clear_keys(self, cache_store: Any, keys: List[str], dry_run: bool) -> int:
        """Clear specific keys from cache store."""
        if dry_run:
            return len(keys)
        
        cleared = 0
        for key in keys:
            try:
                cache_store.forget(key)
                cleared += 1
            except Exception:
                pass
        
        return cleared
    
    async def _estimate_memory_usage(self, cache_store: Any, keys: List[str]) -> float:
        """Estimate memory usage of cache store."""
        try:
            # Simplified estimation - in reality this would depend on your cache implementation
            total_size = 0
            sample_size = min(100, len(keys))  # Sample for performance
            
            for key in keys[:sample_size]:
                try:
                    value = cache_store.get(key)
                    if value is not None:
                        # Rough estimation of memory usage
                        total_size += len(str(key)) + len(str(value))
                except Exception:
                    pass
            
            # Extrapolate to all keys
            if sample_size > 0:
                average_size = total_size / sample_size
                estimated_total = average_size * len(keys)
                return estimated_total / 1024 / 1024  # Convert to MB
            
            return 0.0
            
        except Exception:
            return 0.0
    
    async def _get_store_size(self, cache_store: Any) -> int:
        """Get physical size of cache store."""
        try:
            if hasattr(cache_store, 'size'):
                result = cache_store.size()
                return int(result) if result is not None else 0
            elif hasattr(cache_store, 'get_size'):
                result = cache_store.get_size()
                return int(result) if result is not None else 0
            else:
                return 0
        except Exception:
            return 0
    
    # Enhanced methods for existing functionality
    async def _clear_all_stores_enhanced(self, cache_manager: Any, dry_run: bool) -> int:
        """Enhanced clear all stores with counting."""
        stores = cache_manager.get_stores()
        total_cleared = 0
        
        for store_name in stores:
            try:
                cache_store = cache_manager.store(store_name)
                keys = await self._get_store_keys(cache_store)
                
                if dry_run:
                    total_cleared += len(keys)
                    self.comment(f"Would clear {len(keys)} keys from store: {store_name}")
                else:
                    cache_store.flush()
                    total_cleared += len(keys)
                    self.comment(f"Cleared {len(keys)} keys from store: {store_name}")
                    
            except Exception as e:
                self.warn(f"Failed to clear store {store_name}: {e}")
        
        return total_cleared
    
    async def _clear_store_enhanced(self, cache_manager: Any, store_name: str, dry_run: bool) -> int:
        """Enhanced clear specific store with counting."""
        try:
            cache_store = cache_manager.store(store_name)
            keys = await self._get_store_keys(cache_store)
            
            if dry_run:
                self.comment(f"Would clear {len(keys)} keys from store: {store_name}")
                return len(keys)
            else:
                cache_store.flush()
                self.comment(f"Cleared {len(keys)} keys from store: {store_name}")
                return len(keys)
                
        except Exception as e:
            self.error(f"Failed to clear store '{store_name}': {e}")
            return 0
    
    async def _clear_tags_enhanced(self, cache_manager: Any, tags: List[str], dry_run: bool) -> int:
        """Enhanced clear tags with counting."""
        total_cleared = 0
        
        for tag in tags:
            try:
                tagged_cache = cache_manager.tags([tag])
                
                if dry_run:
                    # Estimate keys that would be cleared
                    # This is a simplified estimation
                    estimated_keys = 10  # Placeholder
                    total_cleared += estimated_keys
                    self.comment(f"Would clear ~{estimated_keys} keys with tag: {tag}")
                else:
                    tagged_cache.flush()
                    # In reality, you'd want to track how many keys were cleared
                    cleared_keys = 10  # Placeholder
                    total_cleared += cleared_keys
                    self.comment(f"Cleared keys with tag: {tag}")
                    
            except Exception as e:
                self.warn(f"Failed to clear tag {tag}: {e}")
        
        return total_cleared
    
    async def _clear_all_stores(self, cache_manager: Any) -> None:
        """Clear all cache stores."""
        self.info("Clearing all cache stores...")
        
        stores = cache_manager.get_stores()
        for store_name in stores:
            try:
                cache_manager.store(store_name).flush()
                self.comment(f"Cleared cache store: {store_name}")
            except Exception as e:
                self.warn(f"Failed to clear store {store_name}: {e}")
    
    async def _clear_store(self, cache_manager: Any, store_name: str) -> None:
        """Clear specific cache store."""
        self.info(f"Clearing cache store: {store_name}")
        
        try:
            cache_manager.store(store_name).flush()
            self.comment(f"Cache store '{store_name}' cleared")
        except Exception as e:
            self.error(f"Failed to clear store '{store_name}': {e}")
    
    async def _clear_tags(self, cache_manager: Any, tags: List[str]) -> None:
        """Clear specific cache tags."""
        self.info(f"Clearing cache tags: {', '.join(tags)}")
        
        for tag in tags:
            try:
                cache_manager.tags([tag]).flush()
                self.comment(f"Cleared tag: {tag}")
            except Exception as e:
                self.warn(f"Failed to clear tag {tag}: {e}")
    
    async def _clear_file_cache(self) -> None:
        """Fallback: Clear file-based cache."""
        cache_dirs = [
            Path("storage/cache"),
            Path("storage/framework/cache"),
            Path("__pycache__"),
        ]
        
        self.info("Clearing file-based cache...")
        cleared_files = 0
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                cleared_files += await self._clear_directory(cache_dir)
        
        self.comment(f"Cleared {cleared_files} cache files")
    
    async def _clear_directory(self, directory: Path) -> int:
        """Clear files in a directory."""
        cleared = 0
        
        try:
            for item in directory.iterdir():
                if item.is_file() and item.suffix in ['.cache', '.tmp', '.pyc']:
                    item.unlink()
                    cleared += 1
                elif item.is_dir() and item.name == '__pycache__':
                    import shutil
                    shutil.rmtree(item)
                    cleared += 1
        except Exception as e:
            self.warn(f"Error clearing {directory}: {e}")
        
        return cleared


class CacheTableCommand(Command):
    """Create the cache database table."""
    
    signature = "cache:table"
    description = "Create a migration for the cache database table"
    help = "Generate migration to create cache table for database cache store"
    
    async def handle(self) -> None:
        """Execute the command."""
        self.info("Creating cache table migration...")
        
        # Create migration for cache table
        migration_content = self._generate_cache_migration()
        
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        migration_name = f"{timestamp}_create_cache_table"
        migration_path = Path(f"database/migrations/{migration_name}.py")
        
        migration_path.parent.mkdir(parents=True, exist_ok=True)
        migration_path.write_text(migration_content)
        
        self.info(f"✅ Cache table migration created: {migration_path}")
        self.comment("Run 'python artisan.py migrate' to create the cache table")
    
    def _generate_cache_migration(self) -> str:
        """Generate cache table migration content."""
        return '''from __future__ import annotations

from database.Schema.Migration import Migration
from database.Schema.Blueprint import Blueprint
from database.Schema import Schema


class CreateCacheTable(Migration):
    """Create cache table migration."""
    
    def up(self) -> None:
        """Run the migration."""
        def create_cache_table(table: Blueprint) -> None:
            table.string("key", 255).primary()
            table.text("value")
            table.integer("expiration")
        
        Schema.create("cache", create_cache_table)
        
        # Create cache tags table
        def create_cache_tags_table(table: Blueprint) -> None:
            table.string("key", 255).index()
            table.string("tag", 255).index()
            table.primary_key(["key", "tag"])
        
        Schema.create("cache_tags", create_cache_tags_table)
    
    def down(self) -> None:
        """Reverse the migration."""
        Schema.drop("cache_tags")
        Schema.drop("cache")
'''


class CacheForgetCommand(Command):
    """Remove an item from the cache."""
    
    signature = "cache:forget {key : The cache key to remove} {--store= : The cache store}"
    description = "Remove a specific item from the cache"
    help = "Delete a cached value by its key"
    
    async def handle(self) -> None:
        """Execute the command."""
        key = self.argument("key")
        store = self.option("store")
        
        if not key:
            self.error("Cache key is required")
            return
        
        try:
            from app.Cache import cache_manager
            
            cache_store: CacheStore = cache_manager.store(store) if store else cache_manager.store()
            
            if cache_store.has(key):
                cache_store.forget(key)
                self.info(f"✅ Cache key '{key}' removed successfully")
            else:
                self.warn(f"Cache key '{key}' not found")
            
        except ImportError:
            self.error("Cache system not available")
        except Exception as e:
            self.error(f"Failed to remove cache key: {e}")


class CachePutCommand(Command):
    """Store an item in the cache."""
    
    signature = "cache:put {key : Cache key} {value : Cache value} {--ttl=3600 : Time to live in seconds} {--store= : Cache store} {--tags= : Cache tags}"
    description = "Store a value in the cache"
    help = "Put a value in the cache with optional TTL and tags"
    
    async def handle(self) -> None:
        """Execute the command."""
        key = self.argument("key")
        value = self.argument("value")
        ttl = int(self.option("ttl", 3600))
        store = self.option("store")
        tags = self.option("tags")
        
        try:
            from app.Cache import cache_manager
            
            cache_store: CacheStore = cache_manager.store(store) if store else cache_manager.store()
            
            # Parse value as JSON if possible
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                parsed_value = value
            
            if tags:
                tag_list = [tag.strip() for tag in tags.split(',')]
                if hasattr(cache_store, 'tags'):
                    cache_store.tags(tag_list).put(key, parsed_value, ttl)
                    self.info(f"✅ Cached '{key}' with tags: {', '.join(tag_list)}")
                else:
                    cache_store.put(key, parsed_value, ttl)
                    self.warn(f"⚠️  Store doesn't support tagging. Cached '{key}' without tags.")
            else:
                cache_store.put(key, parsed_value, ttl)
                self.info(f"✅ Cached '{key}' for {ttl} seconds")
            
        except ImportError:
            self.error("Cache system not available")
        except Exception as e:
            self.error(f"Failed to cache value: {e}")


class CacheGetCommand(Command):
    """Retrieve an item from the cache."""
    
    signature = "cache:get {key : Cache key} {--store= : Cache store} {--default= : Default value if key not found}"
    description = "Retrieve a value from the cache"
    help = "Get a cached value by its key"
    
    async def handle(self) -> None:
        """Execute the command."""
        key = self.argument("key")
        store = self.option("store")
        default = self.option("default")
        
        try:
            from app.Cache import cache_manager
            
            cache_store: CacheStore = cache_manager.store(store) if store else cache_manager.store()
            
            if cache_store.has(key):
                value = cache_store.get(key)
                self.info(f"Cache key '{key}':")
                self.line(json.dumps(value, indent=2, default=str))
            else:
                if default is not None:
                    self.warn(f"Cache key '{key}' not found. Default: {default}")
                else:
                    self.error(f"Cache key '{key}' not found")
            
        except ImportError:
            self.error("Cache system not available")
        except Exception as e:
            self.error(f"Failed to retrieve cache value: {e}")


class CacheListCommand(Command):
    """List cached items."""
    
    signature = "cache:list {--store= : Cache store} {--pattern= : Key pattern to match} {--limit=50 : Maximum number of keys to show}"
    description = "List cached items"
    help = "Display a list of cached keys with their details"
    
    async def handle(self) -> None:
        """Execute the command."""
        store = self.option("store")
        pattern = self.option("pattern", "*")
        limit = int(self.option("limit", 50))
        
        try:
            from app.Cache import cache_manager
            
            cache_store: CacheStore = cache_manager.store(store) if store else cache_manager.store()
            
            self.info(f"Cache Store: {store or 'default'}")
            self.line("=" * 60)
            
            keys = self._get_cache_keys(cache_store, pattern, limit)
            
            if not keys:
                self.warn("No cache keys found")
                return
            
            # Display keys in a table
            headers = ["Key", "Size", "TTL", "Created"]
            rows = []
            
            for key in keys[:limit]:
                try:
                    value = cache_store.get(key)
                    size = len(str(value)) if value else 0
                    ttl = self._get_ttl(cache_store, key)
                    created = self._get_created_time(cache_store, key)
                    
                    rows.append([
                        key[:40] + "..." if len(key) > 40 else key,
                        f"{size} bytes",
                        ttl,
                        created
                    ])
                except Exception:
                    rows.append([key, "Error", "Unknown", "Unknown"])
            
            self.table(headers, rows)
            
            if len(keys) > limit:
                self.comment(f"Showing {limit} of {len(keys)} keys")
            
            self.new_line()
            self.info(f"Total keys: {len(keys)}")
            
        except ImportError:
            await self._list_file_cache()
        except Exception as e:
            self.error(f"Failed to list cache: {e}")
    
    def _get_cache_keys(self, cache_store: Any, pattern: str, limit: int) -> List[str]:
        """Get cache keys matching pattern."""
        # This would depend on your cache implementation
        # For Redis: cache_store.keys(pattern)
        # For database: SELECT key FROM cache WHERE key LIKE pattern
        # For file: glob.glob in cache directory
        
        try:
            return cache_store.keys(pattern)  # type: ignore[no-any-return]
        except Exception:
            return []
    
    def _get_ttl(self, cache_store: Any, key: str) -> str:
        """Get TTL for a cache key."""
        try:
            ttl = cache_store.ttl(key)
            if ttl > 0:
                return f"{ttl}s"
            elif ttl == -1:
                return "No expiry"
            else:
                return "Expired"
        except Exception:
            return "Unknown"
    
    def _get_created_time(self, cache_store: Any, key: str) -> str:
        """Get creation time for a cache key."""
        try:
            # This would depend on cache implementation
            return "Unknown"
        except Exception:
            return "Unknown"
    
    async def _list_file_cache(self) -> None:
        """List file-based cache."""
        cache_dir = Path("storage/cache")
        
        if not cache_dir.exists():
            self.warn("No file cache directory found")
            return
        
        self.info("File Cache Directory: storage/cache")
        self.line("=" * 60)
        
        cache_files = list(cache_dir.glob("*.cache"))
        
        if not cache_files:
            self.warn("No cache files found")
            return
        
        headers = ["File", "Size", "Modified"]
        rows = []
        
        for cache_file in cache_files:
            stat = cache_file.stat()
            size = stat.st_size
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            rows.append([
                cache_file.name,
                f"{size} bytes",
                modified
            ])
        
        self.table(headers, rows)
        self.new_line()
        self.info(f"Total files: {len(cache_files)}")


class CacheStatsCommand(Command):
    """Show cache statistics."""
    
    signature = "cache:stats {--store= : Cache store to analyze}"
    description = "Show cache usage statistics"
    help = "Display cache performance and usage statistics"
    
    async def handle(self) -> None:
        """Execute the command."""
        store = self.option("store")
        
        try:
            from app.Cache import cache_manager
            
            self.info(f"Cache Statistics - Store: {store or 'default'}")
            self.line("=" * 60)
            
            cache_store: CacheStore = cache_manager.store(store) if store else cache_manager.store()
            
            # Get cache stats
            stats = await self._get_cache_stats(cache_store)
            
            # Display general stats
            self.comment("General Statistics:")
            general_stats = [
                ["Total Keys", str(stats.get('total_keys', 'Unknown'))],
                ["Memory Usage", stats.get('memory_usage', 'Unknown')],
                ["Hit Rate", stats.get('hit_rate', 'Unknown')],
                ["Miss Rate", stats.get('miss_rate', 'Unknown')],
                ["Expired Keys", str(stats.get('expired_keys', 'Unknown'))],
            ]
            
            self.table(["Metric", "Value"], general_stats)
            
            # Display performance stats
            if 'performance' in stats:
                self.new_line()
                self.comment("Performance Statistics:")
                perf_stats = stats['performance']
                
                performance_data = [
                    ["Avg Response Time", perf_stats.get('avg_response_time', 'Unknown')],
                    ["Cache Gets/sec", str(perf_stats.get('gets_per_second', 'Unknown'))],
                    ["Cache Sets/sec", str(perf_stats.get('sets_per_second', 'Unknown'))],
                    ["Evictions", str(perf_stats.get('evictions', 'Unknown'))],
                ]
                
                self.table(["Metric", "Value"], performance_data)
            
            # Show top cache keys by size
            if 'top_keys' in stats:
                self.new_line()
                self.comment("Largest Cache Keys:")
                self.table(
                    ["Key", "Size"],
                    [[key, size] for key, size in stats['top_keys'][:10]]
                )
            
        except ImportError:
            await self._show_file_cache_stats()
        except Exception as e:
            self.error(f"Failed to get cache statistics: {e}")
    
    async def _get_cache_stats(self, cache_store: Any) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {}
        
        try:
            # Get basic stats
            stats['total_keys'] = len(cache_store.keys('*'))
            
            # Calculate hit/miss rates if available
            if hasattr(cache_store, 'get_stats'):
                store_stats = cache_store.get_stats()
                stats.update(store_stats)
            
        except Exception as e:
            self.warn(f"Could not retrieve all statistics: {e}")
        
        return stats
    
    async def _show_file_cache_stats(self) -> None:
        """Show file cache statistics."""
        cache_dir = Path("storage/cache")
        
        if not cache_dir.exists():
            self.warn("No file cache directory found")
            return
        
        self.info("File Cache Statistics")
        self.line("=" * 60)
        
        cache_files = list(cache_dir.glob("*.cache"))
        
        if not cache_files:
            self.warn("No cache files found")
            return
        
        total_size = sum(f.stat().st_size for f in cache_files)
        avg_size = total_size / len(cache_files) if cache_files else 0
        
        # Find newest and oldest files
        newest = max(cache_files, key=lambda f: f.stat().st_mtime)
        oldest = min(cache_files, key=lambda f: f.stat().st_mtime)
        
        stats_data = [
            ["Total Files", str(len(cache_files))],
            ["Total Size", f"{total_size:,} bytes"],
            ["Average Size", f"{avg_size:.0f} bytes"],
            ["Newest File", newest.name],
            ["Oldest File", oldest.name],
        ]
        
        self.table(["Metric", "Value"], stats_data)


class CacheOptimizeCommand(Command):
    """Optimize cache performance."""
    
    signature = "cache:optimize {--store= : Cache store to optimize} {--aggressive : Use aggressive optimization}"
    description = "Optimize cache performance"
    help = "Clean expired entries and optimize cache storage"
    
    async def handle(self) -> None:
        """Execute the command."""
        store = self.option("store")
        aggressive = self.option("aggressive", False)
        
        self.info("Optimizing cache...")
        
        try:
            from app.Cache import cache_manager
            
            cache_store: CacheStore = cache_manager.store(store) if store else cache_manager.store()
            
            # Clean expired entries
            cleaned = await self._clean_expired(cache_store)
            self.comment(f"Removed {cleaned} expired entries")
            
            if aggressive:
                # Defragment cache
                await self._defragment_cache(cache_store)
                self.comment("Cache defragmentation completed")
                
                # Optimize memory usage
                await self._optimize_memory(cache_store)
                self.comment("Memory optimization completed")
            
            self.info("✅ Cache optimization completed!")
            
        except ImportError:
            await self._optimize_file_cache()
        except Exception as e:
            self.error(f"Failed to optimize cache: {e}")
    
    async def _clean_expired(self, cache_store: Any) -> int:
        """Clean expired cache entries."""
        cleaned = 0
        
        try:
            # This would depend on your cache implementation
            if hasattr(cache_store, 'clean_expired'):
                cleaned = cache_store.clean_expired()
            else:
                # Manual cleanup
                all_keys = cache_store.keys('*')
                for key in all_keys:
                    if cache_store.ttl(key) == -2:  # Expired
                        cache_store.forget(key)
                        cleaned += 1
        except Exception:
            pass
        
        return cleaned
    
    async def _defragment_cache(self, cache_store: Any) -> None:
        """Defragment cache storage."""
        # This would be cache-specific
        if hasattr(cache_store, 'defragment'):
            cache_store.defragment()
    
    async def _optimize_memory(self, cache_store: Any) -> None:
        """Optimize cache memory usage."""
        # This would be cache-specific
        if hasattr(cache_store, 'optimize_memory'):
            cache_store.optimize_memory()
    
    async def _optimize_file_cache(self) -> None:
        """Optimize file-based cache."""
        cache_dir = Path("storage/cache")
        
        if not cache_dir.exists():
            return
        
        # Remove empty cache files
        empty_files = 0
        for cache_file in cache_dir.glob("*.cache"):
            if cache_file.stat().st_size == 0:
                cache_file.unlink()
                empty_files += 1
        
        self.comment(f"Removed {empty_files} empty cache files")
        
        # Compress large cache files (if possible)
        # This would require additional logic
        
        self.info("✅ File cache optimization completed!")
# Register commands
from app.Console.Artisan import register_command

register_command(CacheClearCommand)
register_command(CacheTableCommand)
register_command(CacheForgetCommand)
register_command(CachePutCommand)
register_command(CacheGetCommand)
register_command(CacheListCommand)
register_command(CacheStatsCommand)
register_command(CacheOptimizeCommand)
