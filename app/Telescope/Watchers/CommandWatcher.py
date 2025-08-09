from __future__ import annotations

import uuid
import time
from typing import Dict, Any, Optional, List

from ..TelescopeManager import TelescopeWatcher, TelescopeEntry


class CommandWatcher(TelescopeWatcher):
    """
    Watches console command execution.
    
    Records command execution, arguments, output, and timing.
    """
    
    def __init__(self, telescope_manager) -> None:
        super().__init__(telescope_manager)
        
        # Don't record telescope commands to avoid recursion
        self.ignore_patterns.update({
            'telescope:',
            'tinker',
            'help',
            'list',
        })
    
    def record_command_started(
        self,
        command: str,
        arguments: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
        command_id: Optional[str] = None
    ) -> str:
        """Record a command starting execution."""
        if self.should_ignore(command):
            return ""
        
        if command_id is None:
            command_id = str(uuid.uuid4())
        
        content = {
            'command': command,
            'arguments': arguments or {},
            'options': options or {},
            'status': 'started',
            'command_id': command_id,
            'started_at': time.time(),
        }
        
        # Create tags for filtering
        tags = [
            f"command:{command}",
            'started',
            'console',
        ]
        
        # Add argument-based tags
        if arguments:
            tags.append('with_arguments')
        
        if options:
            tags.append('with_options')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=command_id,
            should_display_on_index=False,  # Start events usually not interesting
            type='command',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
        return command_id
    
    def record_command_finished(
        self,
        command: str,
        command_id: str,
        exit_code: int = 0,
        duration: Optional[float] = None,
        memory_peak: Optional[int] = None,
        output: Optional[str] = None,
        error_output: Optional[str] = None
    ) -> None:
        """Record a command finishing execution."""
        if self.should_ignore(command):
            return
        
        content = {
            'command': command,
            'command_id': command_id,
            'status': 'finished',
            'exit_code': exit_code,
            'duration': duration,
            'memory_peak': memory_peak,
            'output': self._truncate_output(output),
            'error_output': self._truncate_output(error_output),
            'success': exit_code == 0,
        }
        
        # Create tags for filtering
        tags = [
            f"command:{command}",
            'finished',
            'console',
        ]
        
        # Add result tags
        if exit_code == 0:
            tags.append('successful')
        else:
            tags.append('failed')
            tags.append(f"exit_code:{exit_code}")
        
        # Add performance tags
        if duration and duration > 60:  # Long running commands (> 1 minute)
            tags.append('long_running')
        elif duration and duration > 10:  # Medium commands (> 10 seconds)
            tags.append('medium_duration')
        
        if memory_peak and memory_peak > 100 * 1024 * 1024:  # > 100MB
            tags.append('memory_intensive')
        
        # Add output tags
        if error_output:
            tags.append('has_errors')
        
        if output and len(output) > 10000:
            tags.append('verbose_output')
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=command_id,
            should_display_on_index=True,
            type='command',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_command_output(
        self,
        command: str,
        command_id: str,
        output_type: str,  # 'stdout', 'stderr'
        content: str,
        timestamp: Optional[float] = None
    ) -> None:
        """Record command output in real-time."""
        if self.should_ignore(command):
            return
        
        entry_content = {
            'command': command,
            'command_id': command_id,
            'type': 'output',
            'output_type': output_type,
            'content': self._truncate_output(content),
            'timestamp': timestamp or time.time(),
        }
        
        # Create tags for filtering
        tags = [
            f"command:{command}",
            'output',
            f"output_type:{output_type}",
            'console',
        ]
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=command_id,
            should_display_on_index=False,  # Individual output lines usually not interesting
            type='command',
            content=entry_content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_scheduled_command(
        self,
        command: str,
        schedule: str,  # cron expression or description
        next_run: Optional[str] = None,
        last_run: Optional[str] = None,
        status: str = 'scheduled'
    ) -> None:
        """Record scheduled command information."""
        if self.should_ignore(command):
            return
        
        content = {
            'command': command,
            'schedule': schedule,
            'next_run': next_run,
            'last_run': last_run,
            'status': status,
            'type': 'scheduled',
        }
        
        # Create tags for filtering
        tags = [
            f"command:{command}",
            'scheduled',
            'console',
            f"status:{status}",
        ]
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_command(command),
            should_display_on_index=status in ['failed', 'overdue'],
            type='command',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_command_error(
        self,
        command: str,
        command_id: Optional[str] = None,
        error: str = "",
        exception_class: Optional[str] = None,
        trace: Optional[List[str]] = None
    ) -> None:
        """Record a command error or exception."""
        if self.should_ignore(command):
            return
        
        content = {
            'command': command,
            'command_id': command_id,
            'error': error,
            'exception_class': exception_class,
            'trace': trace or [],
            'type': 'error',
        }
        
        # Create tags for filtering
        tags = [
            f"command:{command}",
            'error',
            'console',
        ]
        
        if exception_class:
            tags.append(f"exception:{exception_class}")
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=command_id or self._hash_command(command),
            should_display_on_index=True,
            type='command',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def record_artisan_command(
        self,
        signature: str,
        description: str,
        arguments: Optional[Dict[str, str]] = None,
        options: Optional[Dict[str, str]] = None
    ) -> None:
        """Record custom Artisan command registration."""
        content = {
            'signature': signature,
            'description': description,
            'arguments': arguments or {},
            'options': options or {},
            'type': 'registration',
        }
        
        # Create tags for filtering
        tags = [
            f"signature:{signature}",
            'registration',
            'artisan',
            'console',
        ]
        
        entry = TelescopeEntry(
            uuid=str(uuid.uuid4()),
            batch_id=self.telescope.current_batch_id or str(uuid.uuid4()),
            family_hash=self._hash_command(signature),
            should_display_on_index=False,  # Registration events usually not interesting
            type='command',
            content=content,
            tags=tags
        )
        
        self.record_entry(entry)
    
    def _truncate_output(self, output: Optional[str], max_length: int = 5000) -> Optional[str]:
        """Truncate command output to prevent excessive storage usage."""
        if not output:
            return output
        
        if len(output) <= max_length:
            return output
        
        return output[:max_length] + f"\n... (truncated from {len(output)} characters)"
    
    def _hash_command(self, command: str) -> str:
        """Create a hash for grouping similar commands."""
        import hashlib
        return hashlib.md5(command.encode()).hexdigest()[:8]