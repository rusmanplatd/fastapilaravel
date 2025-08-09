"""
Advanced Blade Template Caching System
Provides intelligent caching with dependency tracking and invalidation
"""
from __future__ import annotations

import hashlib
import json
import os
import pickle
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Any, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import fnmatch
import weakref


@dataclass
class CacheEntry:
    """Represents a cache entry"""
    key: str
    content: str
    created_at: datetime
    expires_at: Optional[datetime]
    dependencies: Set[str]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}
        self.size = len(self.content.encode('utf-8'))
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def touch(self) -> None:
        """Update access statistics"""
        self.access_count += 1
        self.last_accessed = datetime.now()


class DependencyTracker:
    """Tracks template dependencies and relationships"""
    
    def __init__(self) -> None:
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)  # template -> dependencies
        self.dependents: Dict[str, Set[str]] = defaultdict(set)    # dependency -> templates
        self.file_mtimes: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def add_dependency(self, template: str, dependency: str) -> None:
        """Add a dependency relationship"""
        with self._lock:
            self.dependencies[template].add(dependency)
            self.dependents[dependency].add(template)
            
            # Track file modification time
            if os.path.exists(dependency):
                self.file_mtimes[dependency] = os.path.getmtime(dependency)
    
    def get_dependencies(self, template: str) -> Set[str]:
        """Get all dependencies for a template"""
        with self._lock:
            return self.dependencies.get(template, set()).copy()
    
    def get_dependents(self, dependency: str) -> Set[str]:
        """Get all templates that depend on a file"""
        with self._lock:
            return self.dependents.get(dependency, set()).copy()
    
    def check_modifications(self) -> Set[str]:
        """Check for modified files and return affected templates"""
        modified_templates = set()
        
        with self._lock:
            for file_path, stored_mtime in list(self.file_mtimes.items()):
                if os.path.exists(file_path):
                    current_mtime = os.path.getmtime(file_path)
                    if current_mtime > stored_mtime:
                        # File was modified
                        self.file_mtimes[file_path] = current_mtime
                        modified_templates.update(self.dependents.get(file_path, set()))
                else:
                    # File was deleted
                    del self.file_mtimes[file_path]
                    modified_templates.update(self.dependents.get(file_path, set()))
        
        return modified_templates
    
    def remove_template(self, template: str) -> None:
        """Remove a template from dependency tracking"""
        with self._lock:
            dependencies = self.dependencies.pop(template, set())
            for dependency in dependencies:
                self.dependents[dependency].discard(template)
    
    def get_dependency_graph(self) -> Dict[str, Any]:
        """Get the complete dependency graph for debugging"""
        with self._lock:
            return {
                'dependencies': {k: list(v) for k, v in self.dependencies.items()},
                'dependents': {k: list(v) for k, v in self.dependents.items()},
                'file_mtimes': dict(self.file_mtimes)
            }


class CacheInvalidationStrategy:
    """Base class for cache invalidation strategies"""
    
    def should_invalidate(self, entry: CacheEntry) -> bool:
        """Determine if entry should be invalidated"""
        # Override this method to implement cache invalidation logic
        # Example strategies:
        # - Time-based: check if entry is older than TTL
        # - File-based: check if source files have been modified
        # - Manual: check if entry is marked for invalidation
        # - Memory-based: check if cache size exceeds limits
        raise NotImplementedError("Subclasses must implement should_invalidate()")


class TTLInvalidationStrategy(CacheInvalidationStrategy):
    """Time-to-live based invalidation"""
    
    def __init__(self, default_ttl: timedelta = timedelta(hours=1)):
        self.default_ttl = default_ttl
    
    def should_invalidate(self, entry: CacheEntry) -> bool:
        return entry.is_expired()


class LRUInvalidationStrategy(CacheInvalidationStrategy):
    """Least Recently Used invalidation"""
    
    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
    
    def should_invalidate(self, entry: CacheEntry) -> bool:
        # This strategy is implemented at the cache level
        return False


class DependencyInvalidationStrategy(CacheInvalidationStrategy):
    """Dependency-based invalidation"""
    
    def __init__(self, dependency_tracker: DependencyTracker):
        self.dependency_tracker = dependency_tracker
        self._last_check = datetime.now()
        self._check_interval = timedelta(seconds=30)
    
    def should_invalidate(self, entry: CacheEntry) -> bool:
        # Check if any dependencies have been modified
        now = datetime.now()
        if now - self._last_check < self._check_interval:
            return False
        
        self._last_check = now
        modified = self.dependency_tracker.check_modifications()
        
        # Check if any of the entry's dependencies were modified
        return bool(entry.dependencies.intersection(modified))


class BladeTemplateCache:
    """Advanced template caching system"""
    
    def __init__(self, cache_dir: str = 'storage/cache/templates', 
                 max_memory_size: int = 100 * 1024 * 1024):  # 100MB default
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_memory_size = max_memory_size
        self.current_memory_size = 0
        
        # In-memory cache
        self.memory_cache: Dict[str, CacheEntry] = {}
        
        # Disk cache index
        self.disk_index: Dict[str, str] = {}  # key -> file_path
        
        # Dependencies and invalidation
        self.dependency_tracker = DependencyTracker()
        self.invalidation_strategies: List[CacheInvalidationStrategy] = [
            TTLInvalidationStrategy(),
            DependencyInvalidationStrategy(self.dependency_tracker)
        ]
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'evictions': 0
        }
        
        # Threading
        self._lock = threading.RLock()
        
        # Load existing cache index
        self._load_index()
        
        # Start background cleanup
        self._start_background_cleanup()
    
    def get(self, key: str) -> Optional[str]:
        """Get cached content"""
        with self._lock:
            # Check memory cache first
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                # Check if entry should be invalidated
                if self._should_invalidate(entry):
                    self._remove_entry(key)
                    self.stats['invalidations'] += 1
                    return None
                
                entry.touch()
                self.stats['hits'] += 1
                return entry.content
            
            # Check disk cache
            if key in self.disk_index:
                disk_entry: Optional[CacheEntry] = self._load_from_disk(key)
                if disk_entry is None:
                    # Remove invalid disk entry and return None
                    self._remove_from_disk(key)
                    self.stats['invalidations'] += 1
                    self.stats['misses'] += 1
                    return None
                
                # At this point, disk_entry is guaranteed to be CacheEntry
                assert disk_entry is not None  # Type assertion for mypy
                if self._should_invalidate(disk_entry):
                    # Remove invalid disk entry
                    self._remove_from_disk(key)
                    self.stats['invalidations'] += 1
                else:
                    # Move to memory cache if there's space
                    if self.current_memory_size + disk_entry.size <= self.max_memory_size:
                        self.memory_cache[key] = disk_entry
                        self.current_memory_size += disk_entry.size
                    
                    disk_entry.touch()
                    self.stats['hits'] += 1
                    return disk_entry.content
            
            self.stats['misses'] += 1
            return None
    
    def put(self, key: str, content: str, dependencies: Optional[Set[str]] = None,
            ttl: Optional[timedelta] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store content in cache"""
        with self._lock:
            dependencies = dependencies or set()
            expires_at = datetime.now() + ttl if ttl else None
            
            entry = CacheEntry(
                key=key,
                content=content,
                created_at=datetime.now(),
                expires_at=expires_at,
                dependencies=dependencies,
                metadata=metadata or {}
            )
            
            # Add dependency relationships
            for dep in dependencies:
                self.dependency_tracker.add_dependency(key, dep)
            
            # Try to store in memory first
            if entry.size <= self.max_memory_size:
                # Make room if necessary
                self._ensure_memory_space(entry.size)
                
                self.memory_cache[key] = entry
                self.current_memory_size += entry.size
            else:
                # Store on disk for large entries
                self._save_to_disk(entry)
    
    def invalidate(self, key: str) -> bool:
        """Invalidate specific cache entry"""
        with self._lock:
            removed = False
            
            if key in self.memory_cache:
                self._remove_entry(key)
                removed = True
            
            if key in self.disk_index:
                self._remove_from_disk(key)
                removed = True
            
            if removed:
                self.dependency_tracker.remove_template(key)
                self.stats['invalidations'] += 1
            
            return removed
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate entries matching a pattern"""
        with self._lock:
            count = 0
            keys_to_remove = []
            
            # Check memory cache
            for key in self.memory_cache:
                if fnmatch.fnmatch(key, pattern):
                    keys_to_remove.append(key)
            
            # Check disk cache
            for key in self.disk_index:
                if fnmatch.fnmatch(key, pattern):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                if self.invalidate(key):
                    count += 1
            
            return count
    
    def invalidate_by_dependency(self, dependency: str) -> int:
        """Invalidate all entries that depend on a file"""
        with self._lock:
            dependents = self.dependency_tracker.get_dependents(dependency)
            count = 0
            
            for template in dependents:
                if self.invalidate(template):
                    count += 1
            
            return count
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self.memory_cache.clear()
            self.current_memory_size = 0
            
            # Clear disk cache
            for file_path in self.disk_index.values():
                try:
                    os.unlink(file_path)
                except OSError:
                    pass
            
            self.disk_index.clear()
            self.dependency_tracker = DependencyTracker()
            self._save_index()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            hit_rate = self.stats['hits'] / max(self.stats['hits'] + self.stats['misses'], 1)
            
            return {
                **self.stats,
                'hit_rate': hit_rate,
                'memory_entries': len(self.memory_cache),
                'disk_entries': len(self.disk_index),
                'memory_usage': self.current_memory_size,
                'memory_usage_mb': self.current_memory_size / (1024 * 1024),
                'dependency_graph': self.dependency_tracker.get_dependency_graph()
            }
    
    def _should_invalidate(self, entry: CacheEntry) -> bool:
        """Check if entry should be invalidated"""
        return any(strategy.should_invalidate(entry) for strategy in self.invalidation_strategies)
    
    def _ensure_memory_space(self, required_size: int) -> None:
        """Ensure there's enough memory space"""
        while self.current_memory_size + required_size > self.max_memory_size:
            if not self.memory_cache:
                break
            
            # Find LRU entry
            lru_key = min(self.memory_cache.keys(),
                         key=lambda k: self.memory_cache[k].last_accessed or datetime.min)
            
            # Move to disk or remove
            entry = self.memory_cache[lru_key]
            if entry.size < self.max_memory_size // 10:  # Only save small-ish entries to disk
                self._save_to_disk(entry)
            
            self._remove_entry(lru_key)
            self.stats['evictions'] += 1
    
    def _remove_entry(self, key: str) -> None:
        """Remove entry from memory cache"""
        if key in self.memory_cache:
            entry = self.memory_cache.pop(key)
            self.current_memory_size -= entry.size
    
    def _save_to_disk(self, entry: CacheEntry) -> None:
        """Save entry to disk"""
        file_name = hashlib.md5(entry.key.encode()).hexdigest()
        file_path = self.cache_dir / f"{file_name}.cache"
        
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(entry, f)
            
            self.disk_index[entry.key] = str(file_path)
            self._save_index()
        except Exception:
            pass  # Silently fail disk operations
    
    def _load_from_disk(self, key: str) -> Optional[CacheEntry]:
        """Load entry from disk"""
        if key not in self.disk_index:
            return None
        
        file_path = self.disk_index[key]
        try:
            with open(file_path, 'rb') as f:
                result = pickle.load(f)
                if isinstance(result, CacheEntry):
                    return result
                return None
        except Exception:
            # Remove invalid disk entry
            self._remove_from_disk(key)
            return None
    
    def _remove_from_disk(self, key: str) -> None:
        """Remove entry from disk cache"""
        if key in self.disk_index:
            file_path = self.disk_index.pop(key)
            try:
                os.unlink(file_path)
            except OSError:
                pass
            self._save_index()
    
    def _load_index(self) -> None:
        """Load disk cache index"""
        index_path = self.cache_dir / 'index.json'
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    self.disk_index = json.load(f)
            except Exception:
                self.disk_index = {}
    
    def _save_index(self) -> None:
        """Save disk cache index"""
        index_path = self.cache_dir / 'index.json'
        try:
            with open(index_path, 'w') as f:
                json.dump(self.disk_index, f)
        except Exception:
            pass
    
    def _start_background_cleanup(self) -> None:
        """Start background cleanup thread"""
        def cleanup_worker() -> None:
            while True:
                time.sleep(300)  # Run every 5 minutes
                try:
                    self._cleanup_expired()
                    self._check_dependencies()
                except Exception:
                    pass  # Silently handle cleanup errors
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_expired(self) -> None:
        """Clean up expired entries"""
        with self._lock:
            expired_keys = []
            
            # Check memory cache
            for key, entry in self.memory_cache.items():
                if self._should_invalidate(entry):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self.invalidate(key)
    
    def _check_dependencies(self) -> None:
        """Check for dependency changes"""
        modified_templates = self.dependency_tracker.check_modifications()
        
        with self._lock:
            for template in modified_templates:
                self.invalidate(template)


class CacheTagManager:
    """Manages cache tags for group invalidation"""
    
    def __init__(self, cache: BladeTemplateCache):
        self.cache = cache
        self.tags: Dict[str, Set[str]] = defaultdict(set)  # tag -> cache_keys
        self.key_tags: Dict[str, Set[str]] = defaultdict(set)  # cache_key -> tags
        self._lock = threading.RLock()
    
    def tag_cache(self, key: str, tags: List[str]) -> None:
        """Associate tags with a cache key"""
        with self._lock:
            for tag in tags:
                self.tags[tag].add(key)
                self.key_tags[key].add(tag)
    
    def invalidate_tag(self, tag: str) -> int:
        """Invalidate all cache entries with a specific tag"""
        with self._lock:
            if tag not in self.tags:
                return 0
            
            keys_to_invalidate = list(self.tags[tag])
            count = 0
            
            for key in keys_to_invalidate:
                if self.cache.invalidate(key):
                    count += 1
                    # Remove from tag tracking
                    self.key_tags[key].discard(tag)
            
            self.tags[tag].clear()
            return count
    
    def get_tags_for_key(self, key: str) -> Set[str]:
        """Get all tags associated with a cache key"""
        with self._lock:
            return self.key_tags.get(key, set()).copy()
    
    def get_keys_for_tag(self, tag: str) -> Set[str]:
        """Get all cache keys associated with a tag"""
        with self._lock:
            return self.tags.get(tag, set()).copy()


class BladeSmartCache:
    """Smart caching system with multiple layers and strategies"""
    
    def __init__(self, cache_dir: str = 'storage/cache/templates'):
        self.template_cache = BladeTemplateCache(cache_dir)
        self.tag_manager = CacheTagManager(self.template_cache)
        self.compiled_cache: Dict[str, str] = {}  # In-memory compiled template cache
        self._compile_lock = threading.RLock()
    
    def get_compiled_template(self, template_path: str, compile_func: Callable[[str], str]) -> str:
        """Get compiled template with caching"""
        cache_key = f"compiled:{template_path}"
        
        # Check cache first
        cached = self.template_cache.get(cache_key)
        if cached:
            return cached
        
        # Compile and cache
        with self._compile_lock:
            # Double-check after acquiring lock
            cached = self.template_cache.get(cache_key)
            if cached:
                return cached
            
            # Read template file
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                compiled = compile_func(template_content)
                
                # Cache with dependencies
                dependencies = {template_path}
                self.template_cache.put(
                    cache_key,
                    compiled,
                    dependencies=dependencies,
                    ttl=timedelta(hours=24)
                )
                
                return compiled
                
            except Exception:
                return ""
    
    def cache_rendered_template(self, template_name: str, context_hash: str, 
                              content: str, dependencies: Optional[Set[str]] = None) -> None:
        """Cache rendered template output"""
        cache_key = f"rendered:{template_name}:{context_hash}"
        self.template_cache.put(
            cache_key,
            content,
            dependencies=dependencies,
            ttl=timedelta(minutes=30)
        )
    
    def get_rendered_template(self, template_name: str, context_hash: str) -> Optional[str]:
        """Get cached rendered template"""
        cache_key = f"rendered:{template_name}:{context_hash}"
        return self.template_cache.get(cache_key)
    
    def invalidate_template(self, template_path: str) -> int:
        """Invalidate all cache entries related to a template"""
        count = 0
        count += self.template_cache.invalidate_by_dependency(template_path)
        count += self.template_cache.invalidate_pattern(f"*{template_path}*")
        return count
    
    def tag_template_cache(self, template_name: str, context_hash: str, tags: List[str]) -> None:
        """Tag a rendered template cache entry"""
        cache_key = f"rendered:{template_name}:{context_hash}"
        self.tag_manager.tag_cache(cache_key, tags)
    
    def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate cache entries by tag"""
        return self.tag_manager.invalidate_tag(tag)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        return self.template_cache.get_stats()