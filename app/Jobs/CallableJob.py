from __future__ import annotations

from typing import Any, Callable, Tuple, Dict, Optional
import inspect
import traceback
from datetime import datetime

from app.Jobs.Job import ShouldQueue, JobOptions


class CallableJob(ShouldQueue):
    """
    Laravel-style callable job wrapper.
    
    Allows any function to be queued as a job.
    """
    
    def __init__(
        self, 
        callable_func: Callable[..., Any], 
        args: Tuple[Any, ...] = (), 
        kwargs: Optional[Dict[str, Any]] = None,
        options: Optional[JobOptions] = None
    ) -> None:
        super().__init__(options or JobOptions())
        
        self.callable_func = callable_func
        self.args = args
        self.kwargs = kwargs or {}
        
        # Store function metadata
        self.function_name = getattr(callable_func, '__name__', 'anonymous')
        self.function_module = getattr(callable_func, '__module__', 'unknown')
        
        # Set job display name
        self.display_name = f"{self.function_module}.{self.function_name}"
    
    def handle(self) -> Any:
        """Execute the callable function with stored arguments."""
        try:
            # Call the function with stored arguments
            if inspect.iscoroutinefunction(self.callable_func):
                import asyncio
                return asyncio.run(self.callable_func(*self.args, **self.kwargs))
            else:
                return self.callable_func(*self.args, **self.kwargs)
                
        except Exception as e:
            # Log the error with function context
            error_msg = f"CallableJob failed: {self.display_name}"
            print(f"{error_msg}: {str(e)}")
            print(traceback.format_exc())
            raise
    
    def get_display_name(self) -> str:
        """Get human-readable display name for this job."""
        return self.display_name
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize job data for storage."""
        # Note: In a production implementation, you'd need to handle
        # serialization of the callable and its arguments more carefully
        # This is a simplified version
        
        base_data = super().serialize()
        base_data.update({
            'function_name': self.function_name,
            'function_module': self.function_module,
            'args': self.args,
            'kwargs': self.kwargs,
        })
        
        return base_data
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> CallableJob:
        """Deserialize job data from storage."""
        # Note: In a production implementation, you'd need to handle
        # deserialization of callables more carefully (e.g., importing modules)
        # This is a simplified version
        
        function_name = data.get('function_name', 'unknown')
        function_module = data.get('function_module', 'unknown')
        args = data.get('args', ())
        kwargs = data.get('kwargs', {})
        
        # For now, create a placeholder function
        # In production, you'd import the actual function
        def placeholder_func(*args: Any, **kwargs: Any) -> None:
            raise NotImplementedError(
                f"Cannot deserialize callable job: {function_module}.{function_name}. "
                "Function deserialization needs to be implemented based on your needs."
            )
        
        job = cls(placeholder_func, args, kwargs)
        job.function_name = function_name
        job.function_module = function_module
        job.display_name = f"{function_module}.{function_name}"
        
        return job
    
    def tags(self) -> list[str]:
        """Get tags for this job."""
        return [
            'callable',
            f'function:{self.function_name}',
            f'module:{self.function_module}'
        ]


def callable_job(
    queue: str = "default",
    connection: str = "default", 
    delay: int = 0,
    max_attempts: int = 3,
    timeout: int = 3600
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to make a function queueable.
    
    Usage:
        @callable_job(queue="emails", delay=60)
        def send_email(to: str, subject: str, body: str):
            # Email sending logic
            pass
        
        # Queue the function
        send_email("user@example.com", "Hello", "World")
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> str:
            from app.Queue.QueueManager import global_queue_manager
            
            options = JobOptions(
                queue=queue,
                connection=connection,
                delay=delay,
                max_attempts=max_attempts,
                timeout=timeout
            )
            
            job = CallableJob(func, args, kwargs, options)
            
            if delay > 0:
                return global_queue_manager.later(delay, job, queue)
            else:
                return global_queue_manager.push(job, queue)
        
        # Preserve original function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__
        
        # Add direct execution method
        wrapper._execute_now = func
        
        return wrapper
    
    return decorator