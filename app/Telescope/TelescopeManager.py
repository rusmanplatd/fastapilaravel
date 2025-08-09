from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Type, Callable, Set, cast
from dataclasses import dataclass, asdict, field
import redis.asyncio as redis


@dataclass
class TelescopeEntry:
    """Represents a single Telescope monitoring entry."""
    uuid: str
    batch_id: str
    family_hash: Optional[str]
    should_display_on_index: bool
    type: str
    content: Dict[str, Any]
    tags: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class TelescopeWatcher:
    """Base class for Telescope watchers."""
    
    def __init__(self, telescope_manager: TelescopeManager) -> None:
        self.telescope = telescope_manager
        self.enabled = True
        self.ignore_patterns: Set[str] = set()
    
    def record_entry(self, entry: TelescopeEntry) -> None:
        """Record an entry through the telescope manager."""
        if self.enabled:
            self.telescope.record(entry)
    
    def ignore(self, *patterns: str) -> None:
        """Add patterns to ignore."""
        self.ignore_patterns.update(patterns)
    
    def should_ignore(self, value: str) -> bool:
        """Check if a value should be ignored."""
        return any(pattern in value for pattern in self.ignore_patterns)


class TelescopeManager:
    """
    Laravel Telescope-style debugging and monitoring manager.
    
    Provides comprehensive application monitoring including requests,
    queries, commands, exceptions, jobs, and more.
    """
    
    def __init__(self, redis_url: str = 'redis://localhost:6379/0') -> None:
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        
        # Configuration
        self.enabled = True
        self.recording = True
        self.ignore_paths: Set[str] = {'/telescope', '/favicon.ico', '/health'}
        self.ignore_commands: Set[str] = {'telescope:*'}
        
        # Storage configuration
        self.ENTRIES_KEY = 'telescope:entries'
        self.MONITORING_KEY = 'telescope:monitoring'
        self.TAGS_KEY = 'telescope:tags'
        
        # Data retention (in seconds)
        self.retention_hours = 24
        
        # Watchers registry
        self.watchers: Dict[str, TelescopeWatcher] = {}
        self._setup_default_watchers()
        
        # Current request/batch tracking
        self.current_batch_id: Optional[str] = None
        self.current_entries: List[TelescopeEntry] = []
    
    async def initialize(self) -> None:
        """Initialize Redis connection and setup watchers."""
        self.redis = redis.from_url(self.redis_url)
        
        # Initialize all watchers
        for watcher in self.watchers.values():
            if hasattr(watcher, 'initialize'):
                await watcher.initialize()
    
    def _setup_default_watchers(self) -> None:
        """Setup default Telescope watchers."""
        from .Watchers import (
            RequestWatcher,
            QueryWatcher,
            CommandWatcher,
            ExceptionWatcher,
            JobWatcher,
            CacheWatcher,
            RedisWatcher,
            MailWatcher,
            NotificationWatcher,
        )
        
        self.watchers = {
            'request': RequestWatcher(self),
            'query': QueryWatcher(self),
            'command': CommandWatcher(self),
            'exception': ExceptionWatcher(self),
            'job': JobWatcher(self),
            'cache': CacheWatcher(self),
            'redis': RedisWatcher(self),
            'mail': MailWatcher(self),
            'notification': NotificationWatcher(self),
        }
    
    def start_batch(self) -> str:
        """Start a new batch for grouping related entries."""
        self.current_batch_id = str(uuid.uuid4())
        self.current_entries = []
        return self.current_batch_id
    
    async def end_batch(self) -> None:
        """End the current batch and store entries."""
        if self.current_batch_id and self.current_entries:
            await self._store_entries(self.current_entries)
            self.current_batch_id = None
            self.current_entries = []
    
    def record(self, entry: TelescopeEntry) -> None:
        """Record a telescope entry."""
        if not self.recording or not self.enabled:
            return
        
        # Set batch ID if we have one
        if self.current_batch_id:
            entry.batch_id = self.current_batch_id
        
        # Add to current batch
        self.current_entries.append(entry)
        
        # If no active batch, store immediately
        if not self.current_batch_id:
            import asyncio
            asyncio.create_task(self._store_entries([entry]))
    
    async def _store_entries(self, entries: List[TelescopeEntry]) -> None:
        """Store entries in Redis."""
        if not self.redis or not entries:
            return
        
        # Prepare entries for storage
        stored_entries = {}
        tags_to_store: Dict[str, Dict[str, float]] = {}
        
        for entry in entries:
            # Convert entry to storable format
            entry_data = asdict(entry)
            entry_data['created_at'] = entry.created_at.isoformat() if entry.created_at else datetime.utcnow().isoformat()
            
            # Store by UUID with timestamp for ordering
            timestamp = entry.created_at.timestamp() if entry.created_at else datetime.utcnow().timestamp()
            stored_entries[json.dumps(entry_data)] = timestamp
            
            # Index tags
            for tag in entry.tags:
                tag_key = f"{self.TAGS_KEY}:{tag}"
                if tag_key not in tags_to_store:
                    tags_to_store[tag_key] = {}
                tags_to_store[tag_key][entry.uuid] = timestamp
        
        # Store entries
        if stored_entries:
            await self.redis.zadd(self.ENTRIES_KEY, stored_entries)
        
        # Store tag indices
        for tag_key, tag_entries in tags_to_store.items():
            await self.redis.zadd(tag_key, tag_entries)
            await self.redis.expire(tag_key, self.retention_hours * 3600)
    
    async def get_entries(
        self, 
        type_filter: Optional[str] = None,
        tag_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get telescope entries with filtering."""
        if not self.redis:
            return []
        
        # If filtering by tag, get entries from tag index
        if tag_filter:
            tag_key = f"{self.TAGS_KEY}:{tag_filter}"
            entry_ids = await self.redis.zrevrange(tag_key, offset, offset + limit - 1)
            
            # Get full entries by ID
            entries: List[TelescopeEntry] = []
            for entry_id in entry_ids:
                # This would require a different storage strategy
                # For now, we'll fall back to the main query
                pass
        
        # Get entries from main index
        raw_entries = await self.redis.zrevrange(
            self.ENTRIES_KEY, 
            offset, 
            offset + limit - 1
        )
        
        entries = []
        for raw_entry in raw_entries:
            try:
                entry_data = json.loads(raw_entry.decode())
                
                # Apply type filter
                if type_filter and entry_data.get('type') != type_filter:
                    continue
                
                # Apply tag filter (if not already filtered)
                if tag_filter and not tag_filter in entry_data.get('tags', []):
                    continue
                
                entries.append(entry_data)
                
                if len(entries) >= limit:
                    break
                    
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
        
        return entries
    
    async def get_entry(self, entry_uuid: str) -> Optional[Dict[str, Any]]:
        """Get a specific entry by UUID."""
        entries = await self.get_entries(limit=1000)  # This is inefficient, would need better indexing
        
        for entry in entries:
            if entry.get('uuid') == entry_uuid:
                return entry
        
        return None
    
    async def clear_entries(self, before: Optional[datetime] = None) -> int:
        """Clear telescope entries."""
        if not self.redis:
            return 0
        
        if before:
            # Clear entries before a specific time
            timestamp = before.timestamp()
            count = await self.redis.zremrangebyscore(self.ENTRIES_KEY, 0, timestamp)
            
            # Clear tag indices
            tag_keys = await self.redis.keys(f"{self.TAGS_KEY}:*")
            for tag_key in tag_keys:
                await self.redis.zremrangebyscore(tag_key, 0, timestamp)
        else:
            # Clear all entries
            count = await self.redis.zcard(self.ENTRIES_KEY)
            await self.redis.delete(self.ENTRIES_KEY)
            
            # Clear all tag indices
            tag_keys = await self.redis.keys(f"{self.TAGS_KEY}:*")
            if tag_keys:
                await self.redis.delete(*tag_keys)
        
        return cast(int, count)
    
    async def cleanup_old_entries(self) -> int:
        """Clean up entries older than retention period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=self.retention_hours)
        return await self.clear_entries(cutoff_time)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get Telescope statistics."""
        if not self.redis:
            return {}
        
        # Count entries by type
        entries = await self.get_entries(limit=1000)
        type_counts: Dict[str, int] = {}
        tag_counts: Dict[str, int] = {}
        
        for entry in entries:
            entry_type = entry.get('type', 'unknown')
            type_counts[entry_type] = type_counts.get(entry_type, 0) + 1
            
            for tag in entry.get('tags', []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        total_entries = await self.redis.zcard(self.ENTRIES_KEY)
        
        return {
            'total_entries': total_entries,
            'entries_by_type': type_counts,
            'entries_by_tag': tag_counts,
            'retention_hours': self.retention_hours,
            'watchers': list(self.watchers.keys()),
            'recording': self.recording,
            'enabled': self.enabled,
        }
    
    def enable_watcher(self, watcher_name: str) -> None:
        """Enable a specific watcher."""
        if watcher_name in self.watchers:
            self.watchers[watcher_name].enabled = True
    
    def disable_watcher(self, watcher_name: str) -> None:
        """Disable a specific watcher."""
        if watcher_name in self.watchers:
            self.watchers[watcher_name].enabled = False
    
    def get_watcher(self, watcher_name: str) -> Optional[TelescopeWatcher]:
        """Get a specific watcher."""
        return self.watchers.get(watcher_name)
    
    def start_recording(self) -> None:
        """Start recording telescope entries."""
        self.recording = True
    
    def stop_recording(self) -> None:
        """Stop recording telescope entries."""
        self.recording = False
    
    def pause(self) -> None:
        """Pause telescope (alias for stop_recording)."""
        self.stop_recording()
    
    def resume(self) -> None:
        """Resume telescope (alias for start_recording)."""
        self.start_recording()
    
    def filter(self, callback: Callable[[TelescopeEntry], bool]) -> None:
        """Add a filter callback for entries."""
        # This would be implemented to filter entries before recording
        pass
    
    def tag(self, *tags: str) -> None:
        """Add tags to the next entries."""
        # This would be implemented to tag upcoming entries
        pass