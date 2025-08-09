from __future__ import annotations

from typing import Dict, List, Callable, Any, Optional, TYPE_CHECKING
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

if TYPE_CHECKING:
    from app.Jobs.Job import ShouldQueue


class JobEvent(Enum):
    """Job lifecycle events."""
    BEFORE_DISPATCH = "before_dispatch"
    AFTER_DISPATCH = "after_dispatch"
    BEFORE_PROCESS = "before_process"
    AFTER_PROCESS = "after_process"
    BEFORE_HANDLE = "before_handle"
    AFTER_HANDLE = "after_handle"
    JOB_FAILED = "job_failed"
    JOB_RETRYING = "job_retrying"
    JOB_COMPLETED = "job_completed"
    JOB_DELETED = "job_deleted"


@dataclass
class JobEventData:
    """Data passed to job event handlers."""
    job: ShouldQueue
    event: JobEvent
    timestamp: datetime
    worker_id: Optional[str] = None
    attempts: int = 0
    error: Optional[Exception] = None
    duration_ms: Optional[int] = None
    memory_usage_mb: Optional[float] = None
    extra_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self) -> None:
        if self.extra_data is None:
            self.extra_data = {}


class JobEventDispatcher:
    """
    Event dispatcher for job lifecycle events.
    Allows hooking into job processing for monitoring, logging, etc.
    """
    
    def __init__(self) -> None:
        self.listeners: Dict[JobEvent, List[Callable[[JobEventData], None]]] = {
            event: [] for event in JobEvent
        }
        self.global_listeners: List[Callable[[JobEventData], None]] = []
    
    def listen(self, event: JobEvent, handler: Callable[[JobEventData], None]) -> None:
        """Register event handler for specific event."""
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(handler)
    
    def listen_all(self, handler: Callable[[JobEventData], None]) -> None:
        """Register handler for all events."""
        self.global_listeners.append(handler)
    
    def dispatch(self, event: JobEvent, job: ShouldQueue, **kwargs: Any) -> None:
        """Dispatch event to all registered handlers."""
        event_data = JobEventData(
            job=job,
            event=event,
            timestamp=datetime.now(timezone.utc),
            **kwargs
        )
        
        # Call specific event listeners
        for handler in self.listeners.get(event, []):
            try:
                handler(event_data)
            except Exception as e:
                print(f"Error in job event handler: {str(e)}")
        
        # Call global listeners
        for handler in self.global_listeners:
            try:
                handler(event_data)
            except Exception as e:
                print(f"Error in global job event handler: {str(e)}")
    
    def remove_listener(self, event: JobEvent, handler: Callable[[JobEventData], None]) -> bool:
        """Remove specific event handler."""
        if event in self.listeners and handler in self.listeners[event]:
            self.listeners[event].remove(handler)
            return True
        return False
    
    def clear_listeners(self, event: Optional[JobEvent] = None) -> None:
        """Clear event listeners."""
        if event:
            self.listeners[event] = []
        else:
            for event_type in self.listeners:
                self.listeners[event_type] = []
            self.global_listeners = []


class JobHooks:
    """
    Job hooks system for adding custom logic to job lifecycle.
    """
    
    def __init__(self) -> None:
        self.before_dispatch_hooks: List[Callable[[ShouldQueue], None]] = []
        self.after_dispatch_hooks: List[Callable[[ShouldQueue, str], None]] = []
        self.before_process_hooks: List[Callable[[ShouldQueue], None]] = []
        self.after_process_hooks: List[Callable[[ShouldQueue, bool], None]] = []
        self.failure_hooks: List[Callable[[ShouldQueue, Exception], None]] = []
        self.success_hooks: List[Callable[[ShouldQueue], None]] = []
    
    def before_dispatch(self, hook: Callable[[ShouldQueue], None]) -> None:
        """Add hook called before job dispatch."""
        self.before_dispatch_hooks.append(hook)
    
    def after_dispatch(self, hook: Callable[[ShouldQueue, str], None]) -> None:
        """Add hook called after job dispatch."""
        self.after_dispatch_hooks.append(hook)
    
    def before_process(self, hook: Callable[[ShouldQueue], None]) -> None:
        """Add hook called before job processing."""
        self.before_process_hooks.append(hook)
    
    def after_process(self, hook: Callable[[ShouldQueue, bool], None]) -> None:
        """Add hook called after job processing."""
        self.after_process_hooks.append(hook)
    
    def on_failure(self, hook: Callable[[ShouldQueue, Exception], None]) -> None:
        """Add hook called when job fails."""
        self.failure_hooks.append(hook)
    
    def on_success(self, hook: Callable[[ShouldQueue], None]) -> None:
        """Add hook called when job succeeds."""
        self.success_hooks.append(hook)
    
    def call_before_dispatch(self, job: ShouldQueue) -> None:
        """Call all before_dispatch hooks."""
        for hook in self.before_dispatch_hooks:
            try:
                hook(job)
            except Exception as e:
                print(f"Error in before_dispatch hook: {str(e)}")
    
    def call_after_dispatch(self, job: ShouldQueue, job_id: str) -> None:
        """Call all after_dispatch hooks."""
        for hook in self.after_dispatch_hooks:
            try:
                hook(job, job_id)
            except Exception as e:
                print(f"Error in after_dispatch hook: {str(e)}")
    
    def call_before_process(self, job: ShouldQueue) -> None:
        """Call all before_process hooks."""
        for hook in self.before_process_hooks:
            try:
                hook(job)
            except Exception as e:
                print(f"Error in before_process hook: {str(e)}")
    
    def call_after_process(self, job: ShouldQueue, success: bool) -> None:
        """Call all after_process hooks."""
        for hook in self.after_process_hooks:
            try:
                hook(job, success)
            except Exception as e:
                print(f"Error in after_process hook: {str(e)}")
    
    def call_on_failure(self, job: ShouldQueue, error: Exception) -> None:
        """Call all failure hooks."""
        for hook in self.failure_hooks:
            try:
                hook(job, error)
            except Exception as e:
                print(f"Error in failure hook: {str(e)}")
    
    def call_on_success(self, job: ShouldQueue) -> None:
        """Call all success hooks."""
        for hook in self.success_hooks:
            try:
                hook(job)
            except Exception as e:
                print(f"Error in success hook: {str(e)}")


class ObservableJob:
    """
    Mixin for jobs that emit lifecycle events.
    """
    
    def __init__(self) -> None:
        super().__init__()
        self._event_dispatcher = global_event_dispatcher
        self._hooks = global_job_hooks
    
    def emit_event(self, event: JobEvent, **kwargs: Any) -> None:
        """Emit job lifecycle event."""
        from app.Jobs.Job import ShouldQueue
        if isinstance(self, ShouldQueue):
            self._event_dispatcher.dispatch(event, self, **kwargs)
    
    def execute_hooks(self, hook_type: str, *args: Any) -> None:
        """Execute job hooks."""
        hook_method = getattr(self._hooks, f"call_{hook_type}", None)
        if hook_method:
            hook_method(self, *args)


# Default event handlers for common use cases

def logging_event_handler(event_data: JobEventData) -> None:
    """Log job events."""
    job_name = event_data.job.get_display_name()
    event_name = event_data.event.value
    timestamp = event_data.timestamp.isoformat()
    
    if event_data.event == JobEvent.JOB_FAILED and event_data.error:
        print(f"[{timestamp}] {event_name.upper()}: {job_name} - {str(event_data.error)}")
    elif event_data.duration_ms is not None:
        duration_s = event_data.duration_ms / 1000.0
        print(f"[{timestamp}] {event_name.upper()}: {job_name} ({duration_s:.2f}s)")
    else:
        print(f"[{timestamp}] {event_name.upper()}: {job_name}")


def metrics_event_handler(event_data: JobEventData) -> None:
    """Handle metrics collection for job events."""
    if event_data.event == JobEvent.JOB_COMPLETED:
        # Record successful job completion
        from app.Jobs.Monitor import global_job_monitor
        # Would record metrics here
        pass
    elif event_data.event == JobEvent.JOB_FAILED:
        # Record job failure
        from app.Jobs.Monitor import global_job_monitor
        # Would record failure metrics here
        pass


def notification_event_handler(event_data: JobEventData) -> None:
    """Send notifications for critical job events."""
    if event_data.event == JobEvent.JOB_FAILED:
        # Send failure notification
        job_name = event_data.job.get_display_name()
        error_message = str(event_data.error) if event_data.error else "Unknown error"
        
        print(f"ALERT: Job {job_name} failed - {error_message}")
        
        # In production, you might send email, Slack message, etc.


# Global instances
global_event_dispatcher = JobEventDispatcher()
global_job_hooks = JobHooks()

# Register default event handlers
global_event_dispatcher.listen_all(logging_event_handler)
global_event_dispatcher.listen_all(metrics_event_handler)
global_event_dispatcher.listen(JobEvent.JOB_FAILED, notification_event_handler)


# Decorator for adding event hooks to job methods
def job_event(event: JobEvent) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to emit job events."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            if hasattr(self, 'emit_event'):
                self.emit_event(event)
            
            result = func(self, *args, **kwargs)
            
            return result
        return wrapper
    return decorator


# Context manager for job execution with events
class JobExecutionContext:
    """Context manager for job execution with automatic event dispatching."""
    
    def __init__(self, job: ShouldQueue, worker_id: str = "unknown") -> None:
        self.job = job
        self.worker_id = worker_id
        self.start_time: Optional[datetime] = None
        self.error: Optional[Exception] = None
    
    def __enter__(self) -> JobExecutionContext:
        self.start_time = datetime.now(timezone.utc)
        
        if hasattr(self.job, 'emit_event'):
            self.job.emit_event(JobEvent.BEFORE_PROCESS, worker_id=self.worker_id)
        
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = None
        if self.start_time:
            duration = datetime.now(timezone.utc) - self.start_time
            duration_ms = int(duration.total_seconds() * 1000)
        
        success = exc_type is None
        
        if hasattr(self.job, 'emit_event'):
            if success:
                self.job.emit_event(
                    JobEvent.JOB_COMPLETED,
                    duration_ms=duration_ms,
                    worker_id=self.worker_id
                )
            else:
                self.job.emit_event(
                    JobEvent.JOB_FAILED,
                    error=exc_val,
                    duration_ms=duration_ms,
                    worker_id=self.worker_id
                )
            
            self.job.emit_event(
                JobEvent.AFTER_PROCESS,
                worker_id=self.worker_id,
                duration_ms=duration_ms
            )