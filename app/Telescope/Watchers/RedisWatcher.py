from __future__ import annotations

import uuid
from typing import Dict, Any, Optional, List, Union

from ..TelescopeManager import TelescopeWatcher, TelescopeEntry


class RedisWatcher(TelescopeWatcher):
    """
    Watches Redis operations.
    
    Records Redis commands, execution time, and connection info.
    """
    
    def __init__(self, telescope_manager) -> None:
        super().__init__(telescope_manager)
        
        # Don't record Redis operations for telescope itself to avoid recursion
        self.ignore_patterns.update({
            'telescope:',
            'session:',
            '_internal_',
        })
    
    def record_redis_command(
        self,
        command: str,
        arguments: Optional[List[Any]] = None,
        duration: Optional[float] = None,
        connection: str = 'default',
        database: int = 0
    ) -> None:
        """Record a Redis command execution."""
        # Check if we should ignore this command
        full_command = f"{command} {' '.join(map(str, arguments or []))}"
        if self.should_ignore(full_command):
            return
        
        content = {
            'connection': connection,
            'command': command.upper(),
            'arguments': arguments or [],
            'full_command': full_command,
            'time': duration or 0,
            'database': database,
        }
        
        # Create tags for filtering
        tags = [
            f"connection:{connection}",
            f"command:{command.upper()}",
            f"database:{database}",
        ]
        
        # Add command category tags
        if command.upper() in ['GET', 'MGET', 'HGET', 'HGETALL', 'SMEMBERS', 'LRANGE', 'ZRANGE']:
            tags.append('read')
        elif command.upper() in ['SET', 'MSET', 'HSET', 'SADD', 'LPUSH', 'ZADD']:
            tags.append('write')
        elif command.upper() in ['DEL', 'HDEL', 'SREM', 'LPOP', 'ZREM']:
            tags.append('delete')
        elif command.upper() in ['EXISTS', 'TTL', 'TYPE', 'KEYS', 'SCAN']:
            tags.append('meta')
        elif command.upper() in ['EXPIRE', 'EXPIREAT', 'PERSIST']:
            tags.append('expiry')
        elif command.upper() in ['MULTI', 'EXEC', 'DISCARD', 'WATCH', 'UNWATCH']:
            tags.append('transaction')
        elif command.upper() in ['PUBLISH', 'SUBSCRIBE', 'UNSUBSCRIBE']:
            tags.append('pubsub')
        
        # Add performance tags
        if duration and duration > 0.1:  # Slow Redis commands (> 100ms)
            tags.append('slow')
        
        # Add size tags based on arguments
        if arguments and len(arguments) > 10:
            tags.append('large_args')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_command(command),
            should_display_on_index=True,
            type='redis',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_redis_pipeline(
        self,
        commands: List[Dict[str, Any]],
        duration: Optional[float] = None,
        connection: str = 'default',
        database: int = 0
    ) -> None:
        """Record a Redis pipeline execution."""
        content = {
            'connection': connection,
            'type': 'pipeline',
            'command_count': len(commands),
            'commands': commands[:10],  # Limit to first 10 commands
            'time': duration or 0,
            'database': database,
        }
        
        # Create tags for filtering
        tags = [
            f"connection:{connection}",
            'pipeline',
            f"database:{database}",
            f"count:{len(commands)}",
        ]
        
        # Add performance tags
        if duration and duration > 0.5:  # Slow pipelines (> 500ms)
            tags.append('slow')
        
        if len(commands) > 50:
            tags.append('large_pipeline')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=None,
            should_display_on_index=True,
            type='redis',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_redis_transaction(
        self,
        commands: List[Dict[str, Any]],
        duration: Optional[float] = None,
        connection: str = 'default',
        database: int = 0,
        success: bool = True
    ) -> None:
        """Record a Redis transaction (MULTI/EXEC)."""
        content = {
            'connection': connection,
            'type': 'transaction',
            'command_count': len(commands),
            'commands': commands[:10],  # Limit to first 10 commands
            'time': duration or 0,
            'database': database,
            'success': success,
        }
        
        # Create tags for filtering
        tags = [
            f"connection:{connection}",
            'transaction',
            f"database:{database}",
            f"count:{len(commands)}",
        ]
        
        if success:
            tags.append('successful')
        else:
            tags.append('failed')
        
        # Add performance tags
        if duration and duration > 1.0:  # Slow transactions (> 1s)
            tags.append('slow')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=None,
            should_display_on_index=True,
            type='redis',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_redis_pubsub(
        self,
        action: str,  # 'publish', 'subscribe', 'unsubscribe'
        channel: str,
        message: Optional[str] = None,
        connection: str = 'default'
    ) -> None:
        """Record Redis pub/sub operations."""
        content = {
            'connection': connection,
            'action': action,
            'channel': channel,
            'message': message[:100] if message else None,  # Limit message size
            'type': 'pubsub',
        }
        
        # Create tags for filtering
        tags = [
            f"connection:{connection}",
            'pubsub',
            f"action:{action}",
            f"channel:{channel}",
        ]
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_channel(channel),
            should_display_on_index=True,
            type='redis',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_redis_lua_script(
        self,
        script: str,
        keys: Optional[List[str]] = None,
        arguments: Optional[List[Any]] = None,
        duration: Optional[float] = None,
        connection: str = 'default',
        database: int = 0
    ) -> None:
        """Record Redis Lua script execution."""
        content = {
            'connection': connection,
            'type': 'lua_script',
            'script': script[:200],  # Limit script size
            'script_hash': self._hash_script(script),
            'keys': keys or [],
            'arguments': arguments or [],
            'time': duration or 0,
            'database': database,
        }
        
        # Create tags for filtering
        tags = [
            f"connection:{connection}",
            'lua_script',
            f"database:{database}",
        ]
        
        # Add performance tags
        if duration and duration > 0.2:  # Slow scripts (> 200ms)
            tags.append('slow')
        
        if len(script) > 1000:
            tags.append('large_script')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_script(script),
            should_display_on_index=True,
            type='redis',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_redis_slow_log(
        self,
        slow_log_entry: Dict[str, Any],
        connection: str = 'default'
    ) -> None:
        """Record an entry from Redis slow log."""
        content = {
            'connection': connection,
            'type': 'slow_log',
            'id': slow_log_entry.get('id'),
            'timestamp': slow_log_entry.get('timestamp'),
            'duration_microseconds': slow_log_entry.get('duration'),
            'command': slow_log_entry.get('command', []),
            'client_address': slow_log_entry.get('client_address'),
            'client_name': slow_log_entry.get('client_name'),
        }
        
        # Create tags for filtering
        tags = [
            f"connection:{connection}",
            'slow_log',
            'performance',
        ]
        
        duration_ms = slow_log_entry.get('duration', 0) / 1000
        if duration_ms > 1000:  # Very slow (> 1s)
            tags.append('very_slow')
        elif duration_ms > 100:  # Moderately slow (> 100ms)
            tags.append('moderately_slow')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=None,
            should_display_on_index=True,
            type='redis',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def _hash_command(self, command: str) -> str:
        """Create a hash for grouping similar Redis commands."""
        import hashlib
        return hashlib.md5(command.upper().encode()).hexdigest()[:8]
    
    def _hash_channel(self, channel: str) -> str:
        """Create a hash for grouping pub/sub operations by channel."""
        import hashlib
        return hashlib.md5(channel.encode()).hexdigest()[:8]
    
    def _hash_script(self, script: str) -> str:
        """Create a hash for grouping Lua scripts."""
        import hashlib
        return hashlib.md5(script.encode()).hexdigest()[:8]