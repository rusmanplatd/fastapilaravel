from __future__ import annotations

from typing import Dict, Any, Optional, List, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .TelescopeManager import TelescopeManager, TelescopeEntry, TelescopeWatcher

# Global manager instance
_manager: Optional[TelescopeManager] = None


class Telescope:
    """
    Telescope facade similar to Laravel's Telescope facade.
    
    Provides static-like access to the TelescopeManager instance
    for debugging and monitoring functionality.
    """
    
    @classmethod
    def _get_manager(cls) -> TelescopeManager:
        """Get the global TelescopeManager instance."""
        global _manager
        if _manager is None:
            from .TelescopeManager import TelescopeManager
            _manager = TelescopeManager()
        return _manager
    
    @classmethod
    async def initialize(cls, redis_url: str = 'redis://localhost:6379/0') -> None:
        """Initialize Telescope with Redis connection."""
        global _manager
        from .TelescopeManager import TelescopeManager
        _manager = TelescopeManager(redis_url)
        await _manager.initialize()
    
    @classmethod
    def start_batch(cls) -> str:
        """Start a new batch for grouping related entries."""
        return cls._get_manager().start_batch()
    
    @classmethod
    async def end_batch(cls) -> None:
        """End the current batch and store entries."""
        await cls._get_manager().end_batch()
    
    @classmethod
    def record(cls, entry: TelescopeEntry) -> None:
        """Record a telescope entry."""
        cls._get_manager().record(entry)
    
    @classmethod
    async def get_entries(
        cls,
        type_filter: Optional[str] = None,
        tag_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get telescope entries with filtering."""
        return await cls._get_manager().get_entries(type_filter, tag_filter, limit, offset)
    
    @classmethod
    async def get_entry(cls, entry_uuid: str) -> Optional[Dict[str, Any]]:
        """Get a specific entry by UUID."""
        return await cls._get_manager().get_entry(entry_uuid)
    
    @classmethod
    async def clear_entries(cls, before: Optional[str] = None) -> int:
        """Clear telescope entries."""
        from datetime import datetime
        before_dt = datetime.fromisoformat(before) if before else None
        return await cls._get_manager().clear_entries(before_dt)
    
    @classmethod
    async def get_statistics(cls) -> Dict[str, Any]:
        """Get Telescope statistics."""
        return await cls._get_manager().get_statistics()
    
    @classmethod
    def enable_watcher(cls, watcher_name: str) -> None:
        """Enable a specific watcher.""" 
        cls._get_manager().enable_watcher(watcher_name)
    
    @classmethod
    def disable_watcher(cls, watcher_name: str) -> None:
        """Disable a specific watcher."""
        cls._get_manager().disable_watcher(watcher_name)
    
    @classmethod
    def get_watcher(cls, watcher_name: str) -> Optional[TelescopeWatcher]:
        """Get a specific watcher."""
        return cls._get_manager().get_watcher(watcher_name)
    
    @classmethod
    def start_recording(cls) -> None:
        """Start recording telescope entries."""
        cls._get_manager().start_recording()
    
    @classmethod
    def stop_recording(cls) -> None:
        """Stop recording telescope entries."""
        cls._get_manager().stop_recording()
    
    @classmethod
    def pause(cls) -> None:
        """Pause telescope (alias for stop_recording)."""
        cls.stop_recording()
    
    @classmethod
    def resume(cls) -> None:
        """Resume telescope (alias for start_recording)."""
        cls.start_recording()
    
    @classmethod
    def is_recording(cls) -> bool:
        """Check if Telescope is currently recording."""
        return cls._get_manager().recording
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if Telescope is enabled."""
        return cls._get_manager().enabled
    
    @classmethod
    def filter(cls, callback: Callable) -> None:
        """Add a filter callback for entries."""
        cls._get_manager().filter(callback)
    
    @classmethod
    def tag(cls, *tags: str) -> None:
        """Add tags to the next entries."""
        cls._get_manager().tag(*tags)
    
    # Convenience methods for recording different types of entries
    
    @classmethod
    def record_request(
        cls,
        request: Any,
        response: Any,
        duration: float,
        memory_peak: Optional[int] = None
    ) -> None:
        """Record an HTTP request."""
        watcher = cls.get_watcher('request')
        if watcher:
            watcher.record_request(request, response, duration, memory_peak)
    
    @classmethod
    def record_query(
        cls,
        query: str,
        bindings: Optional[List[Any]] = None,
        duration: float = 0,
        connection_name: str = 'default'
    ) -> None:
        """Record a database query."""
        watcher = cls.get_watcher('query')
        if watcher:
            watcher.record_query(query, bindings, duration, connection_name)
    
    @classmethod
    def record_exception(
        cls,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        handled: bool = False
    ) -> None:
        """Record an exception."""
        watcher = cls.get_watcher('exception')
        if watcher:
            watcher.record_exception(exception, context, handled)
    
    @classmethod
    def record_job_dispatched(
        cls,
        job_id: str,
        job_class: str,
        queue: str = 'default',
        payload: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a job being dispatched."""
        watcher = cls.get_watcher('job')
        if watcher:
            watcher.record_job_dispatched(job_id, job_class, queue, payload)
    
    @classmethod
    def record_job_completed(
        cls,
        job_id: str,
        job_class: str,
        queue: str = 'default',
        duration: Optional[float] = None
    ) -> None:
        """Record a job completing."""
        watcher = cls.get_watcher('job')
        if watcher:
            watcher.record_job_completed(job_id, job_class, queue, duration)
    
    @classmethod
    def record_job_failed(
        cls,
        job_id: str,
        job_class: str,
        queue: str = 'default',
        exception: Optional[str] = None
    ) -> None:
        """Record a job failure."""
        watcher = cls.get_watcher('job')
        if watcher:
            watcher.record_job_failed(job_id, job_class, queue, exception)
    
    @classmethod
    def record_cache_hit(
        cls,
        key: str,
        value: Any = None,
        store: str = 'default'
    ) -> None:
        """Record a cache hit."""
        watcher = cls.get_watcher('cache')
        if watcher:
            watcher.record_cache_hit(key, value, store)
    
    @classmethod
    def record_cache_miss(
        cls,
        key: str,
        store: str = 'default'
    ) -> None:
        """Record a cache miss."""
        watcher = cls.get_watcher('cache')
        if watcher:
            watcher.record_cache_miss(key, store)
    
    @classmethod
    def record_cache_write(
        cls,
        key: str,
        value: Any = None,
        ttl: Optional[int] = None,
        store: str = 'default'
    ) -> None:
        """Record a cache write."""
        watcher = cls.get_watcher('cache')
        if watcher:
            watcher.record_cache_write(key, value, ttl, store)
    
    @classmethod
    def record_redis_command(
        cls,
        command: str,
        arguments: Optional[List[Any]] = None,
        duration: Optional[float] = None,
        connection: str = 'default'
    ) -> None:
        """Record a Redis command."""
        watcher = cls.get_watcher('redis')
        if watcher:
            watcher.record_redis_command(command, arguments, duration, connection)
    
    @classmethod
    def record_mail_sent(
        cls,
        mailable_class: str,
        to_addresses: List[str],
        subject: Optional[str] = None,
        success: bool = True
    ) -> None:
        """Record an email being sent."""
        watcher = cls.get_watcher('mail')
        if watcher:
            watcher.record_mail_sent(mailable_class, to_addresses, subject=subject, success=success)
    
    @classmethod
    def record_notification_sent(
        cls,
        notification_class: str,
        notifiable_type: str,
        notifiable_id: str,
        channels: List[str],
        data: Dict[str, Any],
        success: bool = True
    ) -> None:
        """Record a notification being sent."""
        watcher = cls.get_watcher('notification')
        if watcher:
            watcher.record_notification_sent(
                notification_class, notifiable_type, notifiable_id, channels, data, success
            )
    
    @classmethod
    def record_command_started(
        cls,
        command: str,
        arguments: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record a command starting execution."""
        watcher = cls.get_watcher('command')
        if watcher:
            return watcher.record_command_started(command, arguments, options)
        return ""
    
    @classmethod
    def record_command_finished(
        cls,
        command: str,
        command_id: str,
        exit_code: int = 0,
        duration: Optional[float] = None,
        output: Optional[str] = None
    ) -> None:
        """Record a command finishing execution."""
        watcher = cls.get_watcher('command')
        if watcher:
            watcher.record_command_finished(command, command_id, exit_code, duration, output=output)