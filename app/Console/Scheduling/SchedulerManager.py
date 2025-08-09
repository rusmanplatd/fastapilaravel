from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable, Union, Type
from datetime import datetime, timedelta
import asyncio
import logging
import json
import signal
import sys
from pathlib import Path
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from .Schedule import Schedule, Event
from app.Jobs.Job import Job
from app.Queue.QueueManager import QueueManager


@dataclass
class ScheduleEvent:
    """Enhanced schedule event with more Laravel features."""
    
    id: str
    command: Union[str, Callable[..., Any], Type[Job]]
    cron_expression: str
    description: str = ""
    timezone: Optional[str] = None
    mutex: Optional[str] = None
    without_overlapping: bool = False
    on_one_server: bool = False
    run_in_background: bool = False
    output_file: Optional[str] = None
    email_output_to: List[str] = field(default_factory=list)
    email_on_failure: List[str] = field(default_factory=list)
    environments: List[str] = field(default_factory=list)
    filters: List[Callable[[], bool]] = field(default_factory=list)
    before_callbacks: List[Callable[[], Any]] = field(default_factory=list)
    after_callbacks: List[Callable[[], Any]] = field(default_factory=list)
    retry_after: int = 0
    max_attempts: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0


class ScheduleEventBuilder:
    """Fluent builder for schedule events."""
    
    def __init__(self, event: ScheduleEvent, scheduler: 'SchedulerManager'):
        self.event = event
        self.scheduler = scheduler
    
    def every_minute(self) -> 'ScheduleEventBuilder':
        """Run every minute."""
        self.event.cron_expression = "* * * * *"
        return self
    
    def every_five_minutes(self) -> 'ScheduleEventBuilder':
        """Run every five minutes."""
        self.event.cron_expression = "*/5 * * * *"
        return self
    
    def every_ten_minutes(self) -> 'ScheduleEventBuilder':
        """Run every ten minutes."""
        self.event.cron_expression = "*/10 * * * *"
        return self
    
    def every_fifteen_minutes(self) -> 'ScheduleEventBuilder':
        """Run every fifteen minutes."""
        self.event.cron_expression = "*/15 * * * *"
        return self
    
    def every_thirty_minutes(self) -> 'ScheduleEventBuilder':
        """Run every thirty minutes."""
        self.event.cron_expression = "0,30 * * * *"
        return self
    
    def hourly(self) -> 'ScheduleEventBuilder':
        """Run hourly."""
        self.event.cron_expression = "0 * * * *"
        return self
    
    def hourly_at(self, minute: int) -> 'ScheduleEventBuilder':
        """Run hourly at a specific minute."""
        self.event.cron_expression = f"{minute} * * * *"
        return self
    
    def daily(self) -> 'ScheduleEventBuilder':
        """Run daily at midnight."""
        self.event.cron_expression = "0 0 * * *"
        return self
    
    def daily_at(self, time: str) -> 'ScheduleEventBuilder':
        """Run daily at a specific time (HH:MM)."""
        hour, minute = map(int, time.split(":"))
        self.event.cron_expression = f"{minute} {hour} * * *"
        return self
    
    def twice_daily(self, first_hour: int = 1, second_hour: int = 13) -> 'ScheduleEventBuilder':
        """Run twice daily."""
        self.event.cron_expression = f"0 {first_hour},{second_hour} * * *"
        return self
    
    def weekly(self) -> 'ScheduleEventBuilder':
        """Run weekly on Sunday at midnight."""
        self.event.cron_expression = "0 0 * * 0"
        return self
    
    def weekly_on(self, day: int, time: str = "0:00") -> 'ScheduleEventBuilder':
        """Run weekly on a specific day and time."""
        hour, minute = map(int, time.split(":"))
        self.event.cron_expression = f"{minute} {hour} * * {day}"
        return self
    
    def monthly(self) -> 'ScheduleEventBuilder':
        """Run monthly on the first day at midnight."""
        self.event.cron_expression = "0 0 1 * *"
        return self
    
    def monthly_on(self, day: int, time: str = "0:00") -> 'ScheduleEventBuilder':
        """Run monthly on a specific day and time."""
        hour, minute = map(int, time.split(":"))
        self.event.cron_expression = f"{minute} {hour} {day} * *"
        return self
    
    def yearly(self) -> 'ScheduleEventBuilder':
        """Run yearly on January 1st at midnight."""
        self.event.cron_expression = "0 0 1 1 *"
        return self
    
    def cron(self, expression: str) -> 'ScheduleEventBuilder':
        """Set custom cron expression."""
        self.event.cron_expression = expression
        return self
    
    def weekdays(self) -> 'ScheduleEventBuilder':
        """Run on weekdays (Monday to Friday)."""
        self.event.cron_expression = f"{self._get_minute()} {self._get_hour()} * * 1-5"
        return self
    
    def weekends(self) -> 'ScheduleEventBuilder':
        """Run on weekends (Saturday and Sunday)."""
        self.event.cron_expression = f"{self._get_minute()} {self._get_hour()} * * 0,6"
        return self
    
    def between(self, start_time: str, end_time: str) -> 'ScheduleEventBuilder':
        """Run between specific times."""
        def time_filter() -> bool:
            now = datetime.now().time()
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()
            
            if start <= end:
                return start <= now <= end
            else:  # Crosses midnight
                return now >= start or now <= end
        
        self.event.filters.append(time_filter)
        return self
    
    def unless_between(self, start_time: str, end_time: str) -> 'ScheduleEventBuilder':
        """Skip execution between specific times."""
        def time_filter() -> bool:
            now = datetime.now().time()
            start = datetime.strptime(start_time, "%H:%M").time()
            end = datetime.strptime(end_time, "%H:%M").time()
            
            if start <= end:
                return not (start <= now <= end)
            else:  # Crosses midnight
                return not (now >= start or now <= end)
        
        self.event.filters.append(time_filter)
        return self
    
    def when(self, callback: Callable[[], bool]) -> 'ScheduleEventBuilder':
        """Add a filter condition."""
        self.event.filters.append(callback)
        return self
    
    def skip(self, callback: Callable[[], bool]) -> 'ScheduleEventBuilder':
        """Add a rejection condition."""
        def reject_filter() -> bool:
            return not callback()
        
        self.event.filters.append(reject_filter)
        return self
    
    def environments(self, *environments: str) -> 'ScheduleEventBuilder':
        """Only run in specific environments."""
        self.event.environments = list(environments)
        return self
    
    def name(self, description: str) -> 'ScheduleEventBuilder':
        """Set a description for the event."""
        self.event.description = description
        return self
    
    def description(self, description: str) -> 'ScheduleEventBuilder':
        """Set a description for the event."""
        return self.name(description)
    
    def without_overlapping(self, expires_at: int = 1440) -> 'ScheduleEventBuilder':
        """Prevent overlapping executions."""
        self.event.without_overlapping = True
        self.event.mutex = f"schedule_{hash(str(self.event.command))}"
        return self
    
    def on_one_server(self) -> 'ScheduleEventBuilder':
        """Run on only one server."""
        self.event.on_one_server = True
        return self
    
    def run_in_background(self) -> 'ScheduleEventBuilder':
        """Run in background."""
        self.event.run_in_background = True
        return self
    
    def before(self, callback: Callable[[], Any]) -> 'ScheduleEventBuilder':
        """Add a callback to run before the event."""
        self.event.before_callbacks.append(callback)
        return self
    
    def after(self, callback: Callable[[], Any]) -> 'ScheduleEventBuilder':
        """Add a callback to run after the event."""
        self.event.after_callbacks.append(callback)
        return self
    
    def ping_before(self, url: str) -> 'ScheduleEventBuilder':
        """Ping a URL before running."""
        def ping() -> None:
            import requests
            try:
                requests.get(url, timeout=30)
            except Exception:
                pass
        
        return self.before(ping)
    
    def then_ping(self, url: str) -> 'ScheduleEventBuilder':
        """Ping a URL after running."""
        def ping() -> None:
            import requests
            try:
                requests.get(url, timeout=30)
            except Exception:
                pass
        
        return self.after(ping)
    
    def send_output_to(self, location: str) -> 'ScheduleEventBuilder':
        """Send output to a file."""
        self.event.output_file = location
        return self
    
    def email_output_to(self, *addresses: str) -> 'ScheduleEventBuilder':
        """Email output to addresses."""
        self.event.email_output_to.extend(addresses)
        return self
    
    def email_output_on_failure(self, *addresses: str) -> 'ScheduleEventBuilder':
        """Email output on failure to addresses."""
        self.event.email_on_failure.extend(addresses)
        return self
    
    def retry_after(self, minutes: int) -> 'ScheduleEventBuilder':
        """Retry after specified minutes on failure."""
        self.event.retry_after = minutes
        return self
    
    def max_attempts(self, attempts: int) -> 'ScheduleEventBuilder':
        """Set maximum retry attempts."""
        self.event.max_attempts = attempts
        return self
    
    def timezone(self, tz: str) -> 'ScheduleEventBuilder':
        """Set timezone for the event."""
        self.event.timezone = tz
        return self
    
    def _get_minute(self) -> str:
        """Extract minute from cron expression."""
        parts = self.event.cron_expression.split()
        return parts[0] if parts else "0"
    
    def _get_hour(self) -> str:
        """Extract hour from cron expression."""
        parts = self.event.cron_expression.split()
        return parts[1] if len(parts) > 1 else "0"


class SchedulerManager:
    """Enhanced Laravel-style scheduler manager."""
    
    def __init__(self, queue_manager: Optional[QueueManager] = None):
        self.events: Dict[str, ScheduleEvent] = {}
        self.queue_manager = queue_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.is_running = False
        self.worker_task: Optional[asyncio.Task] = None
        self.mutex_path = Path("/tmp/scheduler_locks")
        self.mutex_path.mkdir(exist_ok=True)
        
        # Performance tracking
        self.stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'average_duration': 0.0,
            'last_run': None
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def command(self, command: str, arguments: Optional[List[str]] = None) -> ScheduleEventBuilder:
        """Schedule an Artisan command."""
        event_id = f"command_{hash(command)}_{len(self.events)}"
        event = ScheduleEvent(
            id=event_id,
            command=command,
            cron_expression="* * * * *",
            description=f"Artisan command: {command}"
        )
        
        self.events[event_id] = event
        return ScheduleEventBuilder(event, self)
    
    def exec(self, command: str, arguments: Optional[List[str]] = None) -> ScheduleEventBuilder:
        """Schedule a shell command."""
        event_id = f"exec_{hash(command)}_{len(self.events)}"
        event = ScheduleEvent(
            id=event_id,
            command=f"exec:{command}",
            cron_expression="* * * * *",
            description=f"Shell command: {command}"
        )
        
        self.events[event_id] = event
        return ScheduleEventBuilder(event, self)
    
    def call(self, callback: Callable[..., Any], arguments: Optional[List[str]] = None) -> ScheduleEventBuilder:
        """Schedule a callable."""
        event_id = f"call_{hash(str(callback))}_{len(self.events)}"
        event = ScheduleEvent(
            id=event_id,
            command=callback,
            cron_expression="* * * * *",
            description=f"Callable: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}"
        )
        
        self.events[event_id] = event
        return ScheduleEventBuilder(event, self)
    
    def job(self, job_class: Type[Job], *args, **kwargs) -> ScheduleEventBuilder:
        """Schedule a job."""
        event_id = f"job_{job_class.__name__}_{len(self.events)}"
        event = ScheduleEvent(
            id=event_id,
            command=job_class,
            cron_expression="* * * * *",
            description=f"Job: {job_class.__name__}"
        )
        
        self.events[event_id] = event
        builder = ScheduleEventBuilder(event, self)
        
        # Store job arguments for later use
        event.before_callbacks.append(lambda: setattr(event, '_job_args', args))
        event.before_callbacks.append(lambda: setattr(event, '_job_kwargs', kwargs))
        
        return builder
    
    def due_events(self, now: Optional[datetime] = None) -> List[ScheduleEvent]:
        """Get all events that are due to run."""
        if now is None:
            now = datetime.now()
        
        due = []
        for event in self.events.values():
            if self._is_event_due(event, now):
                due.append(event)
        
        return due
    
    async def run_due_events(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Run all due events and return results."""
        if now is None:
            now = datetime.now()
        
        due_events = self.due_events(now)
        
        if not due_events:
            return {'ran': 0, 'results': []}
        
        self.logger.info(f"Running {len(due_events)} scheduled event(s)")
        
        results = []
        for event in due_events:
            try:
                result = await self._run_event(event)
                results.append({'event_id': event.id, 'success': result, 'error': None})
                
                if result:
                    event.success_count += 1
                    self.stats['successful_runs'] += 1
                else:
                    event.failure_count += 1
                    self.stats['failed_runs'] += 1
                
                event.last_run = now
                
            except Exception as e:
                self.logger.error(f"Error running scheduled event {event.id}: {e}")
                results.append({'event_id': event.id, 'success': False, 'error': str(e)})
                event.failure_count += 1
                self.stats['failed_runs'] += 1
        
        self.stats['total_runs'] += len(due_events)
        self.stats['last_run'] = now
        
        return {'ran': len(due_events), 'results': results}
    
    async def start_worker(self, check_interval: int = 60) -> None:
        """Start the continuous scheduler worker."""
        if self.is_running:
            self.logger.warning("Scheduler worker is already running")
            return
        
        self.is_running = True
        self.logger.info(f"Starting scheduler worker (checking every {check_interval} seconds)")
        
        try:
            while self.is_running:
                await self.run_due_events()
                await asyncio.sleep(check_interval)
        except asyncio.CancelledError:
            self.logger.info("Scheduler worker cancelled")
        except Exception as e:
            self.logger.error(f"Scheduler worker error: {e}")
        finally:
            self.is_running = False
    
    def stop_worker(self) -> None:
        """Stop the scheduler worker."""
        self.is_running = False
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            **self.stats,
            'total_events': len(self.events),
            'active_events': len([e for e in self.events.values() if self._is_event_active(e)]),
            'events': [self._event_to_dict(event) for event in self.events.values()]
        }
    
    async def _run_event(self, event: ScheduleEvent) -> bool:
        """Run a single scheduled event."""
        start_time = datetime.now()
        
        # Check mutex lock
        if event.without_overlapping and self._is_event_locked(event):
            self.logger.warning(f"Event {event.id} is already running, skipping")
            return False
        
        # Create mutex lock
        lock_file = None
        if event.without_overlapping:
            lock_file = self._create_event_lock(event)
        
        try:
            # Run before callbacks
            for callback in event.before_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            
            # Execute the actual command
            success = await self._execute_command(event)
            
            # Run after callbacks
            for callback in event.after_callbacks:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"Event {event.id} completed in {duration:.2f}s")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Event {event.id} failed: {e}")
            
            # Handle failure notifications
            if event.email_on_failure:
                await self._send_failure_email(event, str(e))
            
            return False
            
        finally:
            # Remove mutex lock
            if lock_file and lock_file.exists():
                lock_file.unlink()
    
    async def _execute_command(self, event: ScheduleEvent) -> bool:
        """Execute the command for an event."""
        if isinstance(event.command, str):
            if event.command.startswith("exec:"):
                # Shell command
                command = event.command[5:]  # Remove "exec:" prefix
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                return process.returncode == 0
            else:
                # Artisan command
                from ..Kernel import artisan
                return await artisan.call(event.command, {}) == 0
        
        elif isinstance(event.command, type) and issubclass(event.command, Job):
            # Job class
            if self.queue_manager:
                # Get job arguments from before callbacks
                args = getattr(event, '_job_args', ())
                kwargs = getattr(event, '_job_kwargs', {})
                
                job_instance = event.command(*args, **kwargs)
                job_id = await self.queue_manager.dispatch_job(job_instance)
                return job_id is not None
            else:
                # Run job directly
                args = getattr(event, '_job_args', ())
                kwargs = getattr(event, '_job_kwargs', {})
                
                job_instance = event.command(*args, **kwargs)
                await job_instance.handle()
                return True
        
        elif callable(event.command):
            # Callable
            if asyncio.iscoroutinefunction(event.command):
                await event.command()
            else:
                event.command()
            return True
        
        return False
    
    def _is_event_due(self, event: ScheduleEvent, now: datetime) -> bool:
        """Check if an event is due to run."""
        try:
            from croniter import croniter
            
            # Check cron expression
            cron = croniter(event.cron_expression, now)
            prev_run = cron.get_prev(datetime)
            
            # Must be within the last minute to be considered due
            if (now - prev_run).total_seconds() > 60:
                return False
            
            # Check environment filter
            if event.environments:
                import os
                current_env = os.getenv('APP_ENV', 'production')
                if current_env not in event.environments:
                    return False
            
            # Check custom filters
            for filter_func in event.filters:
                if not filter_func():
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking if event {event.id} is due: {e}")
            return False
    
    def _is_event_active(self, event: ScheduleEvent) -> bool:
        """Check if an event is active (not disabled)."""
        return True  # Add your logic here for enabling/disabling events
    
    def _is_event_locked(self, event: ScheduleEvent) -> bool:
        """Check if an event is currently locked (running)."""
        if not event.mutex:
            return False
        
        lock_file = self.mutex_path / f"{event.mutex}.lock"
        if not lock_file.exists():
            return False
        
        try:
            # Check if the process is still running
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())
            
            import psutil
            return psutil.pid_exists(pid)
        except Exception:
            # Remove stale lock file
            lock_file.unlink(missing_ok=True)
            return False
    
    def _create_event_lock(self, event: ScheduleEvent) -> Optional[Path]:
        """Create a mutex lock for an event."""
        if not event.mutex:
            return None
        
        lock_file = self.mutex_path / f"{event.mutex}.lock"
        
        try:
            import os
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            return lock_file
        except Exception as e:
            self.logger.error(f"Failed to create lock file {lock_file}: {e}")
            return None
    
    def _event_to_dict(self, event: ScheduleEvent) -> Dict[str, Any]:
        """Convert an event to a dictionary for serialization."""
        return {
            'id': event.id,
            'description': event.description,
            'cron_expression': event.cron_expression,
            'timezone': event.timezone,
            'without_overlapping': event.without_overlapping,
            'on_one_server': event.on_one_server,
            'run_in_background': event.run_in_background,
            'environments': event.environments,
            'last_run': event.last_run.isoformat() if event.last_run else None,
            'next_run': event.next_run.isoformat() if event.next_run else None,
            'success_count': event.success_count,
            'failure_count': event.failure_count,
            'created_at': event.created_at.isoformat()
        }
    
    async def _send_failure_email(self, event: ScheduleEvent, error: str) -> None:
        """Send email notification on event failure."""
        # Implementation would integrate with your mail system
        self.logger.info(f"Would send failure email for event {event.id}: {error}")
    
    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle termination signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down scheduler...")
        self.stop_worker()


# Global scheduler instance
scheduler = SchedulerManager()