from __future__ import annotations

import uuid
from typing import Dict, Any, Optional, Union

from ..TelescopeManager import TelescopeWatcher, TelescopeEntry


class CacheWatcher(TelescopeWatcher):
    """
    Watches cache operations.
    
    Records cache hits, misses, writes, and deletions.
    """
    
    def __init__(self, telescope_manager) -> None:
        super().__init__(telescope_manager)
        
        # Don't record cache operations for telescope itself to avoid recursion
        self.ignore_patterns.update({
            'telescope:',
            'session:',
            '_internal_',
        })
    
    def record_cache_hit(
        self,
        key: str,
        value: Any = None,
        store: str = 'default',
        tags: Optional[list[str]] = None
    ) -> None:
        """Record a cache hit."""
        if self.should_ignore(key):
            return
        
        content = {
            'type': 'hit',
            'key': key,
            'value': self._serialize_value(value),
            'store': store,
            'tags': tags or [],
        }
        
        entry_tags = [
            f"store:{store}",
            'cache',
            'hit',
        ]
        
        if tags:
            entry_tags.extend([f"tag:{tag}" for tag in tags])
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_key(key),
            should_display_on_index=False,  # Cache hits are usually not interesting
            type='cache',
            content=content,
            tags=entry_tags
        )
        
        self.record_entry(entry)
    
    def record_cache_miss(
        self,
        key: str,
        store: str = 'default',
        tags: Optional[list[str]] = None
    ) -> None:
        """Record a cache miss."""
        if self.should_ignore(key):
            return
        
        content = {
            'type': 'miss',
            'key': key,
            'store': store,
            'tags': tags or [],
        }
        
        entry_tags = [
            f"store:{store}",
            'cache',
            'miss',
        ]
        
        if tags:
            entry_tags.extend([f"tag:{tag}" for tag in tags])
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_key(key),
            should_display_on_index=True,  # Cache misses are more interesting
            type='cache',
            content=content,
            tags=entry_tags
        )
        
        self.record_entry(entry)
    
    def record_cache_write(
        self,
        key: str,
        value: Any = None,
        ttl: Optional[int] = None,
        store: str = 'default',
        tags: Optional[list[str]] = None
    ) -> None:
        """Record a cache write operation."""
        if self.should_ignore(key):
            return
        
        content = {
            'type': 'write',
            'key': key,
            'value': self._serialize_value(value),
            'ttl': ttl,
            'store': store,
            'tags': tags or [],
        }
        
        entry_tags = [
            f"store:{store}",
            'cache',
            'write',
        ]
        
        if ttl:
            entry_tags.append('with_ttl')
        
        if tags:
            entry_tags.extend([f"tag:{tag}" for tag in tags])
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_key(key),
            should_display_on_index=True,
            type='cache',
            content=content,
            tags=entry_tags
        )
        
        self.record_entry(entry)
    
    def record_cache_delete(
        self,
        key: str,
        store: str = 'default',
        success: bool = True
    ) -> None:
        """Record a cache delete operation."""
        if self.should_ignore(key):
            return
        
        content = {
            'type': 'delete',
            'key': key,
            'store': store,
            'success': success,
        }
        
        entry_tags = [
            f"store:{store}",
            'cache',
            'delete',
        ]
        
        if success:
            entry_tags.append('successful')
        else:
            entry_tags.append('failed')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_key(key),
            should_display_on_index=True,
            type='cache',
            content=content,
            tags=entry_tags
        )
        
        self.record_entry(entry)
    
    def record_cache_flush(
        self,
        store: str = 'default',
        tags: Optional[list[str]] = None
    ) -> None:
        """Record a cache flush operation."""
        content = {
            'type': 'flush',
            'store': store,
            'tags': tags or [],
        }
        
        entry_tags = [
            f"store:{store}",
            'cache',
            'flush',
        ]
        
        if tags:
            entry_tags.extend([f"tag:{tag}" for tag in tags])
            entry_tags.append('tagged_flush')
        else:
            entry_tags.append('full_flush')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=None,
            should_display_on_index=True,
            type='cache',
            content=content,
            tags=entry_tags
        )
        
        self.record_entry(entry)
    
    def record_cache_forget(
        self,
        keys: Union[str, list[str]],
        store: str = 'default'
    ) -> None:
        """Record forgetting multiple cache keys."""
        if isinstance(keys, str):
            keys = [keys]
        
        # Filter out ignored keys
        keys = [key for key in keys if not self.should_ignore(key)]
        
        if not keys:
            return
        
        content = {
            'type': 'forget',
            'keys': keys,
            'key_count': len(keys),
            'store': store,
        }
        
        entry_tags = [
            f"store:{store}",
            'cache',
            'forget',
            f"count:{len(keys)}",
        ]
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=None,
            should_display_on_index=True,
            type='cache',
            content=content,
            tags=entry_tags
        )
        
        self.record_entry(entry)
    
    def record_cache_remember(
        self,
        key: str,
        value: Any = None,
        ttl: Optional[int] = None,
        was_cached: bool = False,
        store: str = 'default'
    ) -> None:
        """Record a cache remember operation (get or set)."""
        if self.should_ignore(key):
            return
        
        content = {
            'type': 'remember',
            'key': key,
            'value': self._serialize_value(value),
            'ttl': ttl,
            'was_cached': was_cached,
            'store': store,
        }
        
        entry_tags = [
            f"store:{store}",
            'cache',
            'remember',
        ]
        
        if was_cached:
            entry_tags.append('hit')
        else:
            entry_tags.append('miss_and_store')
        
        if ttl:
            entry_tags.append('with_ttl')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_key(key),
            should_display_on_index=not was_cached,  # Show misses but not hits
            type='cache',
            content=content,
            tags=entry_tags
        )
        
        self.record_entry(entry)
    
    def _serialize_value(self, value: Any) -> Dict[str, Any]:
        """Safely serialize a cache value for storage."""
        if value is None:
            return {'type': 'null', 'value': None, 'size': 0}
        
        try:
            # Get type information
            value_type = type(value).__name__
            
            # Calculate approximate size
            import sys
            size = sys.getsizeof(value)
            
            # Serialize based on type
            if isinstance(value, (str, int, float, bool)):
                return {'type': value_type, 'value': value, 'size': size}
            elif isinstance(value, (list, tuple)):
                return {'type': value_type, 'length': len(value), 'size': size, 'value': '[...]'}
            elif isinstance(value, dict):
                return {'type': value_type, 'keys': len(value), 'size': size, 'value': '{...}'}
            else:
                return {'type': value_type, 'size': size, 'value': f'<{value_type} object>'}
                
        except Exception:
            return {'type': 'unknown', 'value': '<serialization failed>', 'size': 0}
    
    def _hash_key(self, key: str) -> str:
        """Create a hash for grouping cache operations by key."""
        import hashlib
        return hashlib.md5(key.encode()).hexdigest()[:8]